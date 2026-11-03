"""v3.3.4 — assisted visual confirmation and repeated-anchor screening.

Manual declaration is evidence of operator confirmation, not machine vision.
All operations are offline/read-only. No camera position is inferred.
"""
from __future__ import annotations
import math

def confirm_anchor(anchor, *, confirmed_id, target="unit_base_center",
                   operator_confirmed=False, window=None):
    if anchor.get("schema") != "hd-synchronized-anchor-v3.3.2":
        raise ValueError("expected v3.3.2 anchor")
    if not anchor.get("usable"):
        raise ValueError("unusable anchor")
    if not isinstance(confirmed_id,int) or confirmed_id != anchor.get("object_id"):
        raise ValueError("confirmed Object ID must match anchor")
    if target != "unit_base_center":
        raise ValueError("unsupported visual target")
    if operator_confirmed is not True:
        raise ValueError("explicit operator confirmation required")
    if not isinstance(window,dict):
        raise ValueError("window geometry is required")
    keys=("left","top","width","height","client_origin_x","client_origin_y","client_width","client_height")
    try:
        geom={k:int(window[k]) for k in keys}
    except (KeyError,TypeError,ValueError) as exc:
        raise ValueError("incomplete window geometry") from exc
    if any(geom[k]<=0 for k in ("width","height","client_width","client_height")):
        raise ValueError("invalid window dimensions")
    return {"schema":"hd-assisted-visual-anchor-v3.3.4",
            "anchor":anchor,"operator_confirmed_id":confirmed_id,
            "operator_confirmed":True,"target":target,
            "window_geometry":geom,"camera_stationary_verified":False,
            "status":"operator_confirmed_unverified",
            "note":"Manual ID confirmation is not automated detection; camera movement remains unknown."}

def compare_recaptures(first,last,*,cursor_tolerance_px=15.,world_tolerance=.02):
    if not math.isfinite(cursor_tolerance_px) or cursor_tolerance_px<0:
        raise ValueError("invalid cursor tolerance")
    if not math.isfinite(world_tolerance) or world_tolerance<0:
        raise ValueError("invalid world tolerance")
    for x in (first,last):
        if x.get("schema")!="hd-assisted-visual-anchor-v3.3.4" or not x.get("operator_confirmed"):
            raise ValueError("both anchors need operator confirmation")
    a,b=first["anchor"],last["anchor"]
    if a.get("object_id")!=b.get("object_id") or a.get("pid")!=b.get("pid"):
        raise ValueError("different object or PID")
    def pair(d,k1,k2):
        v=(float(d[k1]),float(d[k2]))
        if not all(math.isfinite(n) for n in v):raise ValueError("nonfinite coordinates")
        return v
    wa=pair(a["unit"],"candidate_world_x","candidate_world_y")
    wb=pair(b["unit"],"candidate_world_x","candidate_world_y")
    ca=pair(a["cursor_after"]["client"],"x","y")
    cb=pair(b["cursor_after"]["client"],"x","y")
    wd=math.dist(wa,wb);cd=math.dist(ca,cb)
    same_geometry=first["window_geometry"]==last["window_geometry"]
    flags=[]
    if not same_geometry:flags.append("window_geometry_changed")
    if wd>world_tolerance:flags.append("unit_world_position_changed")
    if cd>cursor_tolerance_px:flags.append("visual_point_not_repeatable")
    flags.append("camera_stationarity_unverified")
    return {"schema":"hd-assisted-recapture-audit-v3.3.4",
            "object_id":a["object_id"],"pid":a["pid"],
            "world_distance":wd,"cursor_distance_px":cd,
            "window_geometry_identical":same_geometry,
            "flags":flags,"camera_movement":"unknown",
            "status":"candidate_repeatable" if len(flags)==1 else "rejected",
            "dispatch":"not_dispatched",
            "note":"Candidate repeatability is not proof of visual association or camera stability."}
