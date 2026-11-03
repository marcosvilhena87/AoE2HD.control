"""v3.3.11 — conservative, read-only ORB + RANSAC camera-motion evidence.

Detects translation between TWO screenshots. It cannot establish camera
stability throughout a multi-capture session or verify object identities.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone


def classify_motion(*, matches, inliers, inlier_ratio, dx, dy,
                    median_residual, coverage_cells, scale, rotation_deg,
                    min_inliers=30, min_ratio=0.55, static_tolerance_px=2.0):
    """Pure fail-closed decision, separate from OpenCV extraction."""
    values=(inlier_ratio,dx,dy,median_residual,scale,rotation_deg)
    valid=all(v is not None and math.isfinite(float(v)) for v in values)
    strong=(valid and matches>=min_inliers and inliers>=min_inliers
            and 0<=inlier_ratio<=1 and inlier_ratio>=min_ratio
            and median_residual<=3.0 and coverage_cells>=4
            and abs(scale-1.0)<=0.015 and abs(rotation_deg)<=1.5)
    if not strong:
        return "camera_unverified"
    return ("candidate_camera_static" if math.hypot(dx,dy)<=static_tolerance_px
            else "camera_moved")


def detect_robust_camera_motion(before, after, *,
                                max_features=5000, ratio_test=0.75,
                                ransac_threshold_px=3.0,
                                static_tolerance_px=2.0):
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("opencv-python and numpy required") from exc
    if before.size != after.size:
        raise ValueError("screenshot_dimensions_differ")
    if not (500<=max_features<=20000 and 0.5<=ratio_test<=0.9
            and 1<=ransac_threshold_px<=8 and 0<=static_tolerance_px<=10):
        raise ValueError("invalid_options")
    w,h=before.size
    if w<160 or h<160:
        raise ValueError("images_too_small")

    left=np.asarray(before.convert("L"),dtype=np.uint8)
    right=np.asarray(after.convert("L"),dtype=np.uint8)
    orb=cv2.ORB_create(nfeatures=max_features)
    kp1,d1=orb.detectAndCompute(left,None)
    kp2,d2=orb.detectAndCompute(right,None)
    info={"schema":"hd-camera-robust-v3.3.11",
          "timestamp_utc":datetime.now(timezone.utc).isoformat(),
          "image_size":{"width":w,"height":h},
          "keypoints_before":len(kp1),"keypoints_after":len(kp2),
          "good_matches":0,"inliers":0,"inlier_ratio":0.0,
          "dx_px":None,"dy_px":None,"median_residual_px":None,
          "coverage_cells":0,"scale":None,"rotation_deg":None,
          "status":"camera_unverified",
          "camera_consistency":"not_verified",
          "selection_dispatch":"not_dispatched","memory_write":False,
          "note":"Two screenshots only. Requires manual inspection of static scenery; no game input, camera tracking across whole batch, or selection."}
    if d1 is None or d2 is None or len(d1)<2 or len(d2)<2:
        info["reason"]="too_few_descriptors"
        return info
    matcher=cv2.BFMatcher(cv2.NORM_HAMMING)
    forward=matcher.knnMatch(d1,d2,k=2)
    # Mutual nearest neighbor removes many repetitive terrain matches.
    backward=matcher.match(d2,d1)
    reverse={m.queryIdx:m.trainIdx for m in backward}
    good=[]
    for pair in forward:
        if len(pair)<2:continue
        a,b=pair
        if a.distance<ratio_test*b.distance and reverse.get(a.trainIdx)==a.queryIdx:
            good.append(a)
    info["good_matches"]=len(good)
    if len(good)<30:
        info["reason"]="too_few_unique_matches"
        return info
    source=np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1,1,2)
    target=np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1,1,2)
    # Similarity estimation is used as a consistency check. We report median
    # translation of inlier feature displacements, not an arbitrary warp.
    mat,mask=cv2.estimateAffinePartial2D(source,target,method=cv2.RANSAC,
        ransacReprojThreshold=ransac_threshold_px,maxIters=5000,
        confidence=0.995,refineIters=10)
    if mat is None or mask is None:
        info["reason"]="ransac_failed"
        return info
    selected=mask.ravel().astype(bool)
    ni=int(selected.sum())
    info["inliers"]=ni
    info["inlier_ratio"]=ni/len(good)
    if ni<3:
        info["reason"]="too_few_inliers"
        return info
    aa=float(mat[0,0]);bb=float(mat[1,0])
    scale=math.hypot(aa,bb)
    rotation=math.degrees(math.atan2(bb,aa))
    src=source.reshape(-1,2)[selected]
    dst=target.reshape(-1,2)[selected]
    translations=dst-src
    dx=float(np.median(translations[:,0]));dy=float(np.median(translations[:,1]))
    # Residual is evaluated against median TRANSLATION to reject motion due to
    # geometry changes, animations or incompatible camera movement.
    residuals=np.linalg.norm(translations-np.array([dx,dy]),axis=1)
    median_res=float(np.median(residuals))
    # Spatial coverage: 4x3 screen grid (>=4 occupied cells required).
    cells=set()
    for x,y in src:
        gx=min(3,max(0,int(float(x)*4/w)))
        gy=min(2,max(0,int(float(y)*3/h)))
        cells.add((gx,gy))
    info.update(dx_px=dx,dy_px=dy,median_residual_px=median_res,
                coverage_cells=len(cells),scale=scale,rotation_deg=rotation)
    info["status"]=classify_motion(matches=len(good),inliers=ni,
        inlier_ratio=info["inlier_ratio"],dx=dx,dy=dy,
        median_residual=median_res,coverage_cells=len(cells),
        scale=scale,rotation_deg=rotation,
        static_tolerance_px=static_tolerance_px)
    info["reason"]="sufficient_two_frame_evidence" if info["status"]!="camera_unverified" else "insufficient_or_inconsistent_evidence"
    info["camera_consistency"]=("candidate_endpoints_only"
        if info["status"]=="candidate_camera_static" else "not_verified")
    return info


def gate_robust_camera(camera, batch):
    if camera.get("schema")!="hd-camera-robust-v3.3.11":
        raise ValueError("unexpected_camera_schema")
    if batch.get("schema")!="hd-projection-batch-validation-v3.3.7":
        raise ValueError("unexpected_batch_schema")
    if camera.get("selection_dispatch")!="not_dispatched" or camera.get("memory_write") is not False:
        raise ValueError("non_observation_record")
    cs=camera.get("status")
    if cs not in {"camera_moved","candidate_camera_static","camera_unverified"}:
        raise ValueError("invalid_camera_status")
    return {"schema":"hd-camera-gated-batch-v3.3.11",
            "camera_status":cs,"numeric_batch_status":batch.get("status"),
            "status":"manual_intermediate_review_required" if cs=="candidate_camera_static" else "blocked",
            "validated_for_selection":False,
            "selection_dispatch":"not_dispatched",
            "note":"Never treat two-frame agreement as whole-batch camera validation."}
