"""v3.3.14 — camera-bound calibration and reviewable annotated projection.

Offline and fail-closed. A camera binding has an immutable hash of the fit and
reference image, plus explicit provenance. It never proves Object ID identity.
"""
from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from pathlib import Path

from .guarded_projection_v3_3_13 import project_guarded
from .camera_robust_v3_3_11 import detect_robust_camera_motion

SCHEMA="hd-calibration-camera-binding-v3.3.14"
REPORT_SCHEMA="hd-camera-bound-projection-v3.3.14"


def sha256_file(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576),b""):
            digest.update(block)
    return digest.hexdigest()


def bind_calibration(fit_path, reference_path, *, provenance, operator_note):
    """Hash-only link. Never silently assume a legacy image shares fit camera."""
    from PIL import Image
    if provenance not in {"contemporaneous_operator_attested","legacy_unverified"}:
        raise ValueError("invalid_provenance")
    if provenance=="contemporaneous_operator_attested" and not str(operator_note).strip():
        raise ValueError("operator_note_required")
    fit=__import__("json").loads(Path(fit_path).read_text(encoding="utf-8-sig"))
    if fit.get("schema")!="hd-synchronized-calibration-v3.3.2" or fit.get("status")!="candidate_fit_passed_threshold":
        raise ValueError("unaccepted_fit")
    with Image.open(reference_path) as im:
        im.verify()
    with Image.open(reference_path) as im:
        w,h=im.size
    return {"schema":SCHEMA,"created_utc":datetime.now(timezone.utc).isoformat(),
            "fit_sha256":sha256_file(fit_path),
            "reference_sha256":sha256_file(reference_path),
            "fit_file":str(fit_path),"reference_file":str(reference_path),
            "reference_size":{"width":w,"height":h},
            "provenance":provenance,"operator_note":str(operator_note),
            "verification":"operator_asserted_only" if provenance=="contemporaneous_operator_attested" else "unverified",
            "selection_dispatch":"not_dispatched","memory_write":False,
            "note":"Attestation is not proof of contemporaneous camera, identity or sensor timestamp."}


def camera_bound_projection(capture, fit, binding, *, fit_path,
                            reference_path, capture_reference_path,
                            capture_before_path, client_width, client_height,
                            threshold_px=25.0, detector=None):
    from PIL import Image
    detector=detector or detect_robust_camera_motion
    reasons=[]
    if not isinstance(binding,dict) or binding.get("schema")!=SCHEMA:
        raise ValueError("invalid_binding_schema")
    if sha256_file(fit_path)!=binding.get("fit_sha256"):
        reasons.append("fit_hash_mismatch")
    if sha256_file(reference_path)!=binding.get("reference_sha256"):
        reasons.append("calibration_reference_hash_mismatch")
    if binding.get("provenance")!="contemporaneous_operator_attested":
        reasons.append("calibration_camera_unverified")
    if (binding.get("selection_dispatch")!="not_dispatched" or
            binding.get("memory_write") is not False):
        reasons.append("unsafe_binding")
    if capture.get("reference_image") is None or (
            Path(capture["reference_image"]).resolve()!=Path(capture_reference_path).resolve()):
        reasons.append("capture_reference_path_mismatch")
    image_info=capture.get("before_image")
    if not isinstance(image_info,dict) or not image_info.get("path") or (
            Path(image_info["path"]).resolve()!=Path(capture_before_path).resolve()):
        reasons.append("capture_before_path_mismatch")
    # Calculate source result for diagnostics only; do not allow a candidate
    # through if calibration camera is unknown or mismatch is detected.
    base=project_guarded(capture,fit,client_width=client_width,
                         client_height=client_height,threshold_px=threshold_px)
    camera=None
    if not any(x in reasons for x in ("calibration_reference_hash_mismatch",
                                      "capture_before_path_mismatch",
                                      "capture_reference_path_mismatch")):
        try:
            with Image.open(reference_path) as old, Image.open(capture_before_path) as current:
                if old.size!=(client_width,client_height) or current.size!=old.size:
                    reasons.append("reference_dimensions_mismatch")
                else:
                    camera=detector(old,current)
                    if camera.get("schema")!="hd-camera-robust-v3.3.11" or (
                            camera.get("status")!="candidate_camera_static"):
                        reasons.append("calibration_camera_mismatch_or_unverified")
        except (OSError,ValueError,RuntimeError,TypeError) as exc:
            reasons.append("camera_detection_error:"+str(exc))
    if base["status"]!="candidate_guarded_projection":
        reasons.append("guarded_projection_blocked")
    accepted=not reasons
    out={"schema":REPORT_SCHEMA,"timestamp_utc":datetime.now(timezone.utc).isoformat(),
         "pid":capture.get("pid"),"object_id":capture.get("object_id"),
         "status":"candidate_bound_projection" if accepted else "calibration_camera_blocked",
         "reasons":reasons,"calibration_camera_check":camera,
         "calibration_binding_provenance":binding.get("provenance"),
         "base_projection":base,
         "predicted_client":base.get("predicted_client"),
         "measured_client":base.get("measured_client"),
         "error_px":base.get("error_px"),"within_threshold":base.get("within_threshold"),
         "eligible_for_numeric_batch":accepted,
         "visual_correspondence":"operator_review_required",
         "validated_for_selection":False,"selection_dispatch":"not_dispatched",
         "memory_write":False,
         "note":"Operator-asserted provenance is not automatic proof. Camera checks apply only to sampled images."}
    return out


def render_overlay(report, screenshot_path, output_path):
    """Create evidence overlay; does not infer unit identity from the BMP."""
    from PIL import Image, ImageDraw
    if Path(screenshot_path).resolve()==Path(output_path).resolve():
        raise ValueError("never_overwrite_source_image")
    with Image.open(screenshot_path) as im:
        image=im.convert("RGB")
    draw=ImageDraw.Draw(image)
    pred=report.get("predicted_client");observed=report.get("measured_client")
    if pred and observed:
        px,py=float(pred["x"]),float(pred["y"])
        mx,my=float(observed["x"]),float(observed["y"])
        if all(math.isfinite(v) for v in (px,py,mx,my)):
            for x,y,col in ((px,py,"red"),(mx,my,"lime")):
                draw.ellipse((x-9,y-9,x+9,y+9),outline=col,width=3)
                draw.line((x-14,y,x+14,y),fill=col,width=2)
                draw.line((x,y-14,x,y+14),fill=col,width=2)
            draw.line((px,py,mx,my),fill="yellow",width=3)
    label=f"Object ID: {report.get('object_id')} | {report.get('status')} | error: {report.get('error_px')} px"
    draw.rectangle((0,0,min(image.width, max(250,len(label)*8)),33),fill="black")
    draw.text((6,9),label[:130],fill="white")
    image.save(output_path)
    return {"image":str(output_path),"status":"annotated_not_verified",
            "visual_object_correspondence":"operator_review_required"}
