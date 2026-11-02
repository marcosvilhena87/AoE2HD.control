"""v3.3.1 — independent holdout validation and geometric diagnostics.

No clicks, no game memory access, no assumed camera model.
"""
from __future__ import annotations
import math
from .camera_projection_v3_3 import project

def audit_projection(calibration, holdouts):
    if not isinstance(holdouts,list) or not 1<=len(holdouts)<=100:
        raise ValueError("At least one independent holdout is required")
    if calibration.get("schema")!="hd-affine-projection-v3.3":
        raise ValueError("Invalid calibration schema")
    a,b=calibration["x_coefficients"],calibration["y_coefficients"]
    if any(not math.isfinite(float(v)) for v in a+b):
        raise ValueError("Non-finite coefficients")
    ux=(float(a[0]),float(b[0]));uy=(float(a[1]),float(b[1]))
    sx=math.hypot(*ux);sy=math.hypot(*uy)
    det=ux[0]*uy[1]-ux[1]*uy[0]
    cosine=((ux[0]*uy[0]+ux[1]*uy[1])/(sx*sy)
            if sx>1e-9 and sy>1e-9 else None)
    angle=math.degrees(math.acos(max(-1.,min(1.,cosine)))) if cosine is not None else None
    flags=[]
    if sx<1e-9 or sy<1e-9:flags.append("degenerate_scale")
    if cosine is not None and abs(cosine)>0.95:flags.append("nearly_parallel_world_axes")
    if abs(det)<1e-6:flags.append("near_singular_transform")
    if calibration.get("anchors",0)==3:flags.append("three_anchor_exact_fit_not_validation")
    rows=[]
    for h in holdouts:
        if not isinstance(h,dict):raise ValueError("Invalid holdout")
        try:
            wx,wy,cx,cy=[float(h[k]) for k in ("world_x","world_y","client_x","client_y")]
        except (ValueError,KeyError,TypeError) as exc:
            raise ValueError("Invalid holdout coordinates") from exc
        if not all(map(math.isfinite,(wx,wy,cx,cy))):raise ValueError("Non-finite holdout")
        pred=project(calibration,wx,wy)
        dx=pred["client_x"]-cx;dy=pred["client_y"]-cy
        rows.append({"object_id":h.get("object_id"),
                     "world_x":wx,"world_y":wy,
                     "measured_client_x":cx,"measured_client_y":cy,
                     "predicted_client_x":pred["client_x"],
                     "predicted_client_y":pred["client_y"],
                     "dx_px":dx,"dy_px":dy,"error_px":math.hypot(dx,dy)})
    rmse=math.sqrt(sum(row["error_px"]**2 for row in rows)/len(rows))
    return {"schema":"hd-projection-audit-v3.3.1",
            "holdouts":rows,"holdout_count":len(rows),
            "holdout_rmse_px":rmse,"holdout_max_error_px":max(r["error_px"] for r in rows),
            "geometry":{"world_x_scale_px":sx,"world_y_scale_px":sy,
                        "axis_angle_degrees":angle,"determinant":det,"flags":flags},
            "status":"audit_only_not_validated",
            "camera":"not_observed","selection_dispatch":"not_dispatched",
            "note":"Holdouts must be independent, matched in time, with fixed camera/window/zoom. Geometry flags are heuristics."}
