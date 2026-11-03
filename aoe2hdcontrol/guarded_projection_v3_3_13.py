"""v3.3.13: offline guarded-capture -> calibrated projection -> audit.

Never treats a blocked camera capture as a projection validation observation.
No game process, input dispatch, calibration fitting or file mutation here.
"""
from __future__ import annotations
import math
import statistics
from datetime import datetime, timezone
from .camera_projection_v3_3 import project

GUARD_SCHEMA="hd-guarded-capture-v3.3.12"
FIT_SCHEMA="hd-synchronized-calibration-v3.3.2"
PROJECTION_SCHEMA="hd-guarded-projection-v3.3.13"


def _ready_capture(capture):
    checks=capture.get("camera_checks")
    return (capture.get("schema")==GUARD_SCHEMA
        and capture.get("status")=="candidate_capture_accepted"
        and capture.get("camera_consistency")=="sampled_frames_only"
        and capture.get("anchor_usable") is True
        and capture.get("cursor_stable") is True
        and capture.get("validated_for_selection") is False
        and capture.get("selection_dispatch")=="not_dispatched"
        and capture.get("memory_write") is False
        and capture.get("visual_object_correspondence")=="unverified"
        and not capture.get("image_errors")
        and isinstance(checks,dict)
        and all(isinstance(checks.get(k),dict)
            and checks[k].get("schema")=="hd-camera-robust-v3.3.11"
            and checks[k].get("status")=="candidate_camera_static"
            and checks[k].get("selection_dispatch")=="not_dispatched"
            and checks[k].get("memory_write") is False
            for k in ("reference_to_before","reference_to_after","before_to_after")))


def project_guarded(capture, fit, *, client_width, client_height,
                    threshold_px=25.0):
    """Returns an auditable blocked result without accepting camera outliers."""
    if not isinstance(capture,dict) or capture.get("schema")!=GUARD_SCHEMA:
        raise ValueError("expected guarded capture v3.3.12")
    if not isinstance(fit,dict) or fit.get("schema")!=FIT_SCHEMA:
        raise ValueError("expected synchronized calibration v3.3.2")
    if fit.get("status")!="candidate_fit_passed_threshold":
        raise ValueError("refusing unaccepted calibration")
    if type(client_width) is not int or type(client_height) is not int or not (
        0<client_width<=8192 and 0<client_height<=8192):
        raise ValueError("invalid client dimensions")
    if not math.isfinite(threshold_px) or threshold_px<=0:
        raise ValueError("invalid threshold")
    reasons=[]
    if not _ready_capture(capture):
        reasons.append("camera_or_capture_not_accepted")
    pid=capture.get("pid");oid=capture.get("object_id")
    if type(pid) is not int or pid<=0 or type(oid) is not int or oid<0:
        reasons.append("invalid_identity")
    anchor=capture.get("anchor")
    unit=anchor.get("unit") if isinstance(anchor,dict) else None
    cursor=anchor.get("cursor_after") if isinstance(anchor,dict) else None
    if not isinstance(unit,dict) or not isinstance(cursor,dict):
        reasons.append("missing_anchor_unit_or_cursor")
    if isinstance(anchor,dict) and (anchor.get("pid")!=pid or anchor.get("object_id")!=oid):
        reasons.append("anchor_identity_mismatch")
    if isinstance(capture.get("cursor_after"),dict) and isinstance(cursor,dict):
        if capture["cursor_after"].get("client")!=cursor.get("client"):
            reasons.append("cursor_after_mismatch")
    if isinstance(capture.get("before_image"),dict) and isinstance(capture.get("after_image"),dict):
        for key in ("before_image","after_image"):
            info=capture[key]
            if info.get("width")!=client_width or info.get("height")!=client_height:
                reasons.append("image_dimensions_mismatch")
    else:
        reasons.append("missing_image_metadata")
    values=None
    try:
        if not isinstance(unit,dict) or unit.get("finite") is not True:
            raise ValueError("nonfinite_unit")
        wx,wy=float(unit["candidate_world_x"]),float(unit["candidate_world_y"])
        cx,cy=float(cursor["client"]["x"]),float(cursor["client"]["y"])
        values=(wx,wy,cx,cy)
        if not all(math.isfinite(v) for v in values):
            raise ValueError("nonfinite_coordinates")
        if not (0<=cx<client_width and 0<=cy<client_height):
            raise ValueError("cursor_out_of_bounds")
    except (KeyError,TypeError,ValueError,OverflowError) as exc:
        reasons.append(f"invalid_measurement:{exc}")
    result={"schema":PROJECTION_SCHEMA,
            "timestamp_utc":datetime.now(timezone.utc).isoformat(),
            "pid":pid,"object_id":oid,"status":"projection_blocked",
            "reasons":reasons,"camera_capture_status":capture.get("status"),
            "camera_consistency":"sampled_frames_only_not_session_verified",
            "calibration_status":fit["status"],
            "visual_correspondence":"operator_review_required",
            "reference_camera_alignment_with_calibration":"unverified",
            "threshold_px":threshold_px,"predicted_client":None,
            "measured_client":None,"residual":None,"error_px":None,
            "within_threshold":None,"inside_client":None,
            "eligible_for_numeric_batch":False,
            "validated_for_selection":False,
            "selection_dispatch":"not_dispatched","memory_write":False,
            "note":"Same-camera alignment with calibration and visual target identity remain unverified; no selection authorized."}
    if reasons:
        return result
    wx,wy,cx,cy=values
    prediction=project(fit["calibration"],wx,wy)
    px,py=prediction["client_x"],prediction["client_y"]
    if not all(math.isfinite(v) for v in (px,py)):
        result["reasons"].append("nonfinite_projection")
        return result
    inside=0<=px<client_width and 0<=py<client_height
    if not inside:
        result["reasons"].append("predicted_out_of_bounds")
        return result
    # Residual = measured - predicted, unlike legacy v3.3.6 dx/dy.
    dx,dy=cx-px,cy-py
    error=math.hypot(dx,dy)
    result.update(status="candidate_guarded_projection",reasons=[],
        predicted_client={"x":px,"y":py},
        measured_client={"x":cx,"y":cy},
        residual={"dx_px":dx,"dy_px":dy},error_px=error,
        within_threshold=error<=threshold_px,inside_client=True,
        eligible_for_numeric_batch=True)
    return result


def validate_guarded_batch(records, *, excluded_ids=(), min_samples=10,
                           threshold_px=25.0):
    """Retain blocked/outlier/duplicate reports; do not silently cherry-pick."""
    if type(min_samples) is not int or min_samples<1:
        raise ValueError("invalid minimum samples")
    if not math.isfinite(threshold_px) or threshold_px<=0:
        raise ValueError("invalid threshold")
    excluded=set(int(i) for i in excluded_ids)
    accepted=[];excluded_records=[];seen=set();pids=set()
    for path,row in records:
        reason=[]
        if not isinstance(row,dict) or row.get("schema")!=PROJECTION_SCHEMA:
            reason.append("unexpected_schema")
        elif row.get("status")!="candidate_guarded_projection" or row.get("eligible_for_numeric_batch") is not True:
            reason.append("capture_or_projection_blocked")
        if isinstance(row,dict) and row.get("selection_dispatch")!="not_dispatched":
            reason.append("dispatch_not_observational")
        if isinstance(row,dict) and row.get("memory_write") is not False:
            reason.append("memory_write_not_false")
        if not reason:
            try:
                oid=int(row["object_id"]);pid=int(row["pid"])
                err=float(row["error_px"])
                if oid in excluded:reason.append("calibration_or_prior_holdout_id")
                if oid in seen:reason.append("duplicate_object_id")
                if not math.isfinite(err) or err<0:reason.append("invalid_error")
                if row.get("within_threshold") is not (err<=threshold_px):
                    reason.append("inconsistent_threshold_flag")
                if row.get("camera_consistency")!="sampled_frames_only_not_session_verified":
                    reason.append("unexpected_camera_label")
            except (KeyError,TypeError,ValueError,OverflowError):
                reason.append("invalid_numeric_fields")
        if reason:
            excluded_records.append({"file":str(path),"reasons":reason,
                "object_id":row.get("object_id") if isinstance(row,dict) else None,
                "error_px":row.get("error_px") if isinstance(row,dict) else None})
        else:
            accepted.append({"file":str(path),"object_id":oid,"pid":pid,"error_px":err})
            seen.add(oid);pids.add(pid)
    errors=[x["error_px"] for x in accepted];n=len(errors)
    stats={"count":n,"mean_error_px":statistics.mean(errors) if n else None,
           "rmse_px":math.sqrt(sum(e*e for e in errors)/n) if n else None,
           "max_error_px":max(errors) if n else None,
           "within_threshold_count":sum(e<=threshold_px for e in errors)}
    gates={"minimum_samples":n>=min_samples,"single_pid":len(pids)==1,
           "all_under_threshold":bool(n) and all(e<=threshold_px for e in errors),
           "no_exclusions":not excluded_records}
    return {"schema":"hd-guarded-projection-batch-v3.3.13",
            "timestamp_utc":datetime.now(timezone.utc).isoformat(),
            "status":"candidate_numeric_batch_passed" if all(gates.values()) else "inconclusive",
            "metrics":stats,"gates":gates,
            "accepted":accepted,"excluded":excluded_records,
            "camera_consistency":"sampled_frames_only_not_session_verified",
            "visual_correspondence":"operator_review_required",
            "validated_for_selection":False,
            "selection_dispatch":"not_dispatched",
            "note":"Blocked records are preserved but do not contribute to numeric metrics. Identity and calibration camera alignment unverified."}
