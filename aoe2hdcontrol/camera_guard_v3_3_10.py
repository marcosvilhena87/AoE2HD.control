"""v3.3.10 — conservative offline camera-motion guard.

Operates on two screenshots and explicitly operator-chosen static landmarks.
No clicks, process access, or memory writes. A pass means only that the two
endpoint screenshots look aligned at the chosen landmarks.
"""
from __future__ import annotations
import math
from datetime import datetime, timezone
from pathlib import Path

def _patch(img, x, y, r=12, stride=3):
    return [img.getpixel((x+dx,y+dy)) for dy in range(-r,r+1,stride)
            for dx in range(-r,r+1,stride)]

def _mad(a,b):
    return sum(abs(x-y) for x,y in zip(a,b))/len(a)

def detect_camera_motion(before, after, anchors, *, search_px=60,
                         static_tolerance_px=2, agreement_px=3):
    if before.size != after.size:
        raise ValueError("screenshot_dimensions_differ")
    if not (3 <= len(anchors) <= 12):
        raise ValueError("three_to_twelve_static_anchors_required")
    if not (0 <= static_tolerance_px <= 10 and 0 < agreement_px <= 20 and
            4 <= search_px <= 120):
        raise ValueError("invalid_threshold")
    if len({(a.get("x"),a.get("y")) for a in anchors}) != len(anchors):
        raise ValueError("duplicate_anchors")
    a=before.convert("L");b=after.convert("L")
    w,h=a.size
    margin=12+search_px+2
    observations=[]
    for index,anchor in enumerate(anchors):
        x,y=anchor.get("x"),anchor.get("y")
        if not isinstance(x,int) or isinstance(x,bool) or not isinstance(y,int) or isinstance(y,bool):
            raise ValueError("anchor_coordinates_must_be_integers")
        if not (margin<=x<w-margin and margin<=y<h-margin):
            raise ValueError(f"anchor_outside_safe_area:{index}")
        template=_patch(a,x,y)
        mean=sum(template)/len(template)
        std=math.sqrt(sum((v-mean)**2 for v in template)/len(template))
        if std<8:
            observations.append({"index":index,"x":x,"y":y,"status":"low_texture","std":std})
            continue
        candidates=[]
        # A coarse step keeps this offline check reasonably fast without numpy.
        for dy in range(-search_px,search_px+1,2):
            for dx in range(-search_px,search_px+1,2):
                score=_mad(template,_patch(b,x+dx,y+dy))
                candidates.append((score,dx,dy))
        candidates.sort()
        best=candidates[0]
        # Different displacement basins, not adjacent near-equal offsets.
        runner=next((v for v in candidates if abs(v[1]-best[1])>=7 or
                    abs(v[2]-best[2])>=7),None)
        unique=runner is not None and runner[0]-best[0]>=2.0
        strong=best[0]<=22 and unique
        observations.append({"index":index,"x":x,"y":y,
            "status":"matched" if strong else "ambiguous_match",
            "dx":best[1],"dy":best[2],"mad":best[0],
            "second_basin_mad":runner[0] if runner else None,
            "std":std})
    good=[x for x in observations if x["status"]=="matched"]
    if len(good)!=len(anchors):
        status="camera_unverified";median_dx=median_dy=None
    else:
        from statistics import median
        median_dx=median(x["dx"] for x in good);median_dy=median(x["dy"] for x in good)
        coherent=all(math.hypot(x["dx"]-median_dx,x["dy"]-median_dy)<=agreement_px for x in good)
        if not coherent:
            status="camera_unverified"
        elif math.hypot(median_dx,median_dy)>static_tolerance_px:
            status="camera_moved"
        else:
            status="candidate_camera_static"
    return {"schema":"hd-camera-motion-v3.3.10",
            "timestamp_utc":datetime.now(timezone.utc).isoformat(),
            "status":status,"image_size":{"width":w,"height":h},
            "n_anchors":len(anchors),"n_matches":len(good),
            "median_dx_px":median_dx,"median_dy_px":median_dy,
            "static_tolerance_px":static_tolerance_px,
            "agreement_px":agreement_px,"observations":observations,
            "camera_consistency":"candidate_endpoints_only" if status=="candidate_camera_static" else "not_verified",
            "selection_dispatch":"not_dispatched","memory_write":False,
            "note":"Only two screenshot endpoints; moving units, zoom, parallax, changing HUD and camera movement between frames may invalidate results. Choose static terrain/buildings, manually review; no selection enabled."}

def gate_batch(camera, batch):
    if camera.get("schema")!="hd-camera-motion-v3.3.10" or batch.get("schema")!="hd-projection-batch-validation-v3.3.7":
        raise ValueError("unexpected_report_schema")
    if camera.get("selection_dispatch")!="not_dispatched" or camera.get("memory_write") is not False:
        raise ValueError("camera_report_not_read_only")
    numeric=batch.get("status")=="candidate_batch_passed"
    # A static endpoint image pair is not enough to prove camera stability
    # throughout an extended multi-capture batch. Fail closed.
    return {"schema":"hd-camera-gated-batch-v3.3.10",
            "status":"blocked" if camera.get("status")!="candidate_camera_static" else "manual_intermediate_review_required",
            "numeric_batch_passed":numeric,
            "camera_endpoint_status":camera.get("status"),
            "validated_for_selection":False,
            "selection_dispatch":"not_dispatched",
            "note":"Never infer whole-batch camera consistency from two endpoints. Review each capture/camera segment before proceeding."}
