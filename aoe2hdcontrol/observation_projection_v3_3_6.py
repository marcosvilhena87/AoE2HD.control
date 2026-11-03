"""v3.3.6 — world-to-client projection in observation-only mode.

The fitted calibration is session/camera specific. Never sends input.
"""
from __future__ import annotations
import math
from datetime import datetime,timezone
from .position_cursor_probe_v3_2 import probe_unit_position
from .camera_projection_v3_3 import project

def observe_projection(api, *, pid, object_id, fit, client_width, client_height,
                       measurement=None):
    if not isinstance(fit,dict) or fit.get("schema")!="hd-synchronized-calibration-v3.3.2":
        raise ValueError("expected v3.3.2 fit report")
    if fit.get("status")!="candidate_fit_passed_threshold":
        raise ValueError("refusing unaccepted calibration")
    if not isinstance(client_width,int) or not isinstance(client_height,int) or not (0<client_width<=8192 and 0<client_height<=8192):
        raise ValueError("invalid client dimensions")
    unit=probe_unit_position(api,object_id)
    if not unit["finite"]:raise ValueError("nonfinite unit position")
    x,y=unit["candidate_world_x"],unit["candidate_world_y"]
    predicted=project(fit["calibration"],x,y)
    px,py=predicted["client_x"],predicted["client_y"]
    if not math.isfinite(px) or not math.isfinite(py):raise ValueError("nonfinite projection")
    inside=(0<=px<client_width and 0<=py<client_height)
    residual=None
    if measurement is not None:
        if measurement.get("schema")!="hd-visual-evidence-v3.3.5" or measurement.get("status")!="candidate_visual_evidence" or measurement.get("cursor_stable_across_image") is not True:
            raise ValueError("measurement must be candidate visual evidence v3.3.5")
        if measurement.get("pid")!=pid or measurement.get("object_id")!=object_id:
            raise ValueError("measurement PID/Object ID mismatch")
        seen=measurement["anchor"]["unit"]
        if math.hypot(float(seen["candidate_world_x"])-x,float(seen["candidate_world_y"])-y)>0.02:
            raise ValueError("unit changed world position since measurement")
        cursor=measurement["anchor"]["cursor_after"]["client"]
        dx=px-float(cursor["x"]);dy=py-float(cursor["y"])
        residual={"measured_client_x":cursor["x"],"measured_client_y":cursor["y"],
                  "dx_px":dx,"dy_px":dy,"error_px":math.hypot(dx,dy),
                  "correspondence":"operator_review_required"}
    return {"schema":"hd-observation-projection-v3.3.6",
            "timestamp_utc":datetime.now(timezone.utc).isoformat(),
            "pid":pid,"object_id":object_id,"unit":unit,
            "predicted_client":{"x":px,"y":py},
            "client_bounds":{"width":client_width,"height":client_height},
            "inside_client":inside,"measurement_comparison":residual,
            "calibration_status":fit["status"],
            "camera_consistency":"unverified",
            "status":"candidate_inside_client" if inside else "outside_client",
            "selection_dispatch":"not_dispatched","memory_write":False,
            "note":"Prediction only. Visual target and camera stationarity are not automatically verified."}
