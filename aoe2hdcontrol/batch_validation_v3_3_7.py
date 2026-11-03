"""v3.3.7: offline audit of independent observation reports. No process access."""
from __future__ import annotations
import math
import statistics
from datetime import datetime,timezone

def validate_batch(reports, *, excluded_ids, min_samples=10, threshold_px=25.0):
    if not isinstance(min_samples,int) or min_samples<1: raise ValueError("min_samples must be positive")
    if not math.isfinite(threshold_px) or threshold_px<=0:raise ValueError("invalid threshold")
    excluded=set(int(x) for x in excluded_ids)
    accepted=[]; rejected=[]; ids=set(); pids=set()
    for name, report in reports:
        why=[]
        try:
            if report.get("schema")!="hd-observation-projection-v3.3.6":why.append("schema")
            oid=int(report["object_id"]);pid=int(report["pid"])
            if oid in excluded:why.append("calibration_or_previous_validation_id")
            if oid in ids:why.append("duplicate_object_id")
            if report.get("status")!="candidate_inside_client" or report.get("inside_client") is not True:why.append("outside_client")
            if report.get("selection_dispatch")!="not_dispatched" or report.get("memory_write") is not False:why.append("non_observation_record")
            m=report.get("measurement_comparison")
            if not isinstance(m,dict):why.append("missing_measurement")
            else:
                error=float(m["error_px"])
                if not math.isfinite(error) or error<0:why.append("invalid_error")
                if m.get("correspondence")!="operator_review_required":why.append("unexpected_correspondence")
            if not why:
                accepted.append({"file":name,"object_id":oid,"pid":pid,"error_px":error,
                                 "predicted_client":report.get("predicted_client"),
                                 "measurement_comparison":m})
                ids.add(oid);pids.add(pid)
        except (KeyError,TypeError,ValueError,OverflowError) as e:
            why.append("invalid_fields")
        if why:rejected.append({"file":name,"reasons":why})
    errors=[r["error_px"] for r in accepted];n=len(errors)
    ordered=sorted(errors)
    percentile95=ordered[math.ceil(.95*n)-1] if n else None
    metrics={"count":n,"mean_error_px":statistics.mean(errors) if n else None,
             "rmse_px":math.sqrt(sum(x*x for x in errors)/n) if n else None,
             "max_error_px":max(errors) if n else None,"p95_error_px":percentile95,
             "within_threshold_count":sum(e<=threshold_px for e in errors),
             "within_threshold_fraction":sum(e<=threshold_px for e in errors)/n if n else None}
    gates={"minimum_samples":n>=min_samples,"single_pid":len(pids)==1,
           "all_under_threshold":bool(n) and all(e<=threshold_px for e in errors),
           "no_rejected_reports":not rejected}
    return {"schema":"hd-projection-batch-validation-v3.3.7",
            "timestamp_utc":datetime.now(timezone.utc).isoformat(),
            "status":"candidate_batch_passed" if all(gates.values()) else "inconclusive",
            "excluded_object_ids":sorted(excluded),"min_samples":min_samples,
            "threshold_px":threshold_px,"pids":sorted(pids),"metrics":metrics,
            "gates":gates,"accepted":accepted,"rejected":rejected,
            "camera_consistency":"unverified",
            "note":"Offline numeric validation only; operator must visually verify each BMP/target and unchanged camera. No selection dispatch."}
