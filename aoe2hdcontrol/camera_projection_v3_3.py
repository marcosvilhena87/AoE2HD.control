"""v3.3 — read-only empirical world-to-client projection calibration.

A calibration is valid only for the stationary camera/window configuration
that produced the corresponding samples. No memory offsets are introduced.
"""
from __future__ import annotations
import math

def _solve3(matrix, values):
    m = [list(map(float,row)) + [float(v)] for row,v in zip(matrix,values)]
    for col in range(3):
        pivot=max(range(col,3),key=lambda i:abs(m[i][col]))
        if abs(m[pivot][col]) < 1e-10:raise ValueError("degenerate/collinear calibration anchors")
        m[col],m[pivot]=m[pivot],m[col]
        t=m[col][col]
        m[col]=[x/t for x in m[col]]
        for i in range(3):
            if i!=col:
                t=m[i][col]
                m[i]=[a-t*b for a,b in zip(m[i],m[col])]
    return [m[i][3] for i in range(3)]

def calibrate_projection(pairs):
    """Least squares affine projection of world coordinates to window client px."""
    if not isinstance(pairs,list) or len(pairs)<3 or len(pairs)>100:
        raise ValueError("expected 3..100 anchor pairs")
    values=[]
    for item in pairs:
        if not isinstance(item,dict):raise ValueError("invalid anchor")
        try:
            row=[float(item[k]) for k in ("world_x","world_y","client_x","client_y")]
        except (KeyError,TypeError,ValueError) as exc:
            raise ValueError("each anchor requires world_x/world_y/client_x/client_y") from exc
        if not all(math.isfinite(v) for v in row):raise ValueError("nonfinite anchor")
        values.append(row)
    features=[[x,y,1.] for x,y,_,_ in values]
    gram=[[sum(f[i]*f[j] for f in features) for j in range(3)] for i in range(3)]
    xcoef=_solve3(gram,[sum(f[i]*v[2] for f,v in zip(features,values)) for i in range(3)])
    ycoef=_solve3(gram,[sum(f[i]*v[3] for f,v in zip(features,values)) for i in range(3)])
    residuals=[]
    for wx,wy,cx,cy in values:
        px=xcoef[0]*wx+xcoef[1]*wy+xcoef[2]
        py=ycoef[0]*wx+ycoef[1]*wy+ycoef[2]
        residuals.append(round(math.hypot(px-cx,py-cy),4))
    rms=math.sqrt(sum(e*e for e in residuals)/len(residuals))
    return {"schema":"hd-affine-projection-v3.3","x_coefficients":xcoef,
            "y_coefficients":ycoef,"anchors":len(values),
            "residuals_px":residuals,"rmse_px":round(rms,4),
            "camera":"assumed_stationary_not_measured",
            "game_cursor_world":"unknown",
            "status":"empirical_fit_only","dispatch":"not_dispatched",
            "note":"Requires matching world/client positions for stationary camera; never substitute for a validated engine transform."}

def project(calibration, world_x, world_y):
    if calibration.get("schema")!="hd-affine-projection-v3.3":
        raise ValueError("invalid calibration")
    x,y=float(world_x),float(world_y)
    if not math.isfinite(x) or not math.isfinite(y):raise ValueError("nonfinite position")
    a,b=calibration["x_coefficients"],calibration["y_coefficients"]
    return {"client_x":a[0]*x+a[1]*y+a[2],
            "client_y":b[0]*x+b[1]*y+b[2],
            "validated":False}
