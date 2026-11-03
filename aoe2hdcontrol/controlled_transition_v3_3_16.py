"""v3.3.16 — controlled manual A/B/C unit transition experiment.

A: isolated stationary unit. B: manual unit movement. C: manual return.
Every snapshot is independently camera guarded and human reviewed.
This observes correlation but does not prove visual Object ID by itself.
"""
from __future__ import annotations
from datetime import datetime, timezone
import math
from pathlib import Path

from .camera_robust_v3_3_11 import detect_robust_camera_motion
from .calibration_camera_v3_3_14 import sha256_file
from .guarded_projection_v3_3_13 import _ready_capture
from .visual_identity_v3_3_15 import SCHEMA as REVIEW_SCHEMA, _numeric, _image_path

SCHEMA="hd-controlled-transition-audit-v3.3.16"


def audit_transition(stages, *, minimum_world_move=1.0,
                     return_world_tolerance=0.10,
                     return_cursor_tolerance_px=20.0,
                     minimum_cursor_move_px=15.0,
                     detector=None):
    """Stages A, B and C contain review, capture and exact source image paths."""
    from PIL import Image
    detector=detector or detect_robust_camera_motion
    limits=(minimum_world_move,return_world_tolerance,
            return_cursor_tolerance_px,minimum_cursor_move_px)
    if any(not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in limits):
        raise ValueError("invalid_tolerances")
    if not isinstance(stages,dict) or set(stages)!={"A","B","C"}:
        raise ValueError("exactly_stages_A_B_C_required")
    reasons=[];measurements={};ids=set();pids=set();refs=set()
    captures=set();screens=set()
    camera_checks={}
    for phase in ("A","B","C"):
        entry=stages[phase]
        review,cap=entry["review"],entry["capture"]
        cp=Path(entry["capture_path"]);image=Path(entry["image_path"])
        if review.get("schema")!=REVIEW_SCHEMA or review.get("status")!="operator_confirmed_candidate":
            reasons.append(f"{phase}:manual_review_not_confirmed")
        flags=review.get("review",{})
        if (flags.get("identity")!="confirmed" or flags.get("isolated") is not True or
                flags.get("cursor_on_target") is not True or
                not str(flags.get("reviewer","")).strip() or not str(flags.get("note","")).strip()):
            reasons.append(f"{phase}:manual_review_incomplete")
        if not _ready_capture(cap):
            reasons.append(f"{phase}:capture_not_accepted")
        if cp.resolve()!=Path(review.get("capture_file","")).resolve() or (
                sha256_file(cp)!=review.get("capture_sha256")):
            reasons.append(f"{phase}:capture_hash_mismatch")
        if (image.resolve()!=Path(review.get("screenshot_file","")).resolve() or
                image.resolve()!=_image_path(cap).resolve() or
                sha256_file(image)!=review.get("screenshot_sha256")):
            reasons.append(f"{phase}:image_hash_mismatch")
        reference=cap.get("reference_image")
        if (not reference or not Path(reference).is_file() or
                Path(reference).resolve()!=Path(review.get("reference_image","")).resolve() or
                sha256_file(reference)!=review.get("reference_sha256")):
            reasons.append(f"{phase}:camera_reference_hash_mismatch")
        ids.add(cap.get("object_id"));pids.add(cap.get("pid"))
        refs.add(review.get("reference_sha256"))
        captures.add(cp.resolve());screens.add(image.resolve())
        if review.get("object_id")!=cap.get("object_id") or review.get("pid")!=cap.get("pid"):
            reasons.append(f"{phase}:object_or_pid_review_mismatch")
        world,cursor=_numeric(cap)
        rw=review.get("world",{});rc=review.get("cursor",{})
        if (abs(world[0]-float(rw.get("x",float("nan"))))>1e-6 or
                abs(world[1]-float(rw.get("y",float("nan"))))>1e-6 or
                abs(cursor[0]-float(rc.get("x",float("nan"))))>1e-6 or
                abs(cursor[1]-float(rc.get("y",float("nan"))))>1e-6 or
                any(not math.isfinite(v) for v in (float(rw.get("x",float("nan"))),
                    float(rw.get("y",float("nan"))),float(rc.get("x",float("nan"))),
                    float(rc.get("y",float("nan")))))):
            reasons.append(f"{phase}:review_coordinates_mismatch")
        measurements[phase]={"world":list(world),"cursor":list(cursor),
                             "object_id":cap.get("object_id"),"pid":cap.get("pid"),
                             "capture_sha256":review.get("capture_sha256"),
                             "screenshot_sha256":review.get("screenshot_sha256")}
    if len(ids)!=1 or len(pids)!=1:
        reasons.append("object_or_process_changed")
    if len(refs)!=1 or None in refs:
        reasons.append("camera_reference_changed")
    if len(captures)!=3 or len(screens)!=3:
        reasons.append("non_independent_captures")
    w={k:measurements[k]["world"] for k in ("A","B","C")}
    cursor={k:measurements[k]["cursor"] for k in ("A","B","C")}
    dw_ab=math.dist(w["A"],w["B"]);dw_ac=math.dist(w["A"],w["C"])
    dc_ab=math.dist(cursor["A"],cursor["B"])
    dc_ac=math.dist(cursor["A"],cursor["C"])
    if dw_ab<minimum_world_move:reasons.append("no_verified_world_displacement")
    if dw_ac>return_world_tolerance:reasons.append("world_not_returned")
    if dc_ab<minimum_cursor_move_px:reasons.append("cursor_did_not_follow_movement")
    if dc_ac>return_cursor_tolerance_px:reasons.append("cursor_not_returned")
    # Camera comparisons are independent of any coordinate model.
    for phase1,phase2 in (("A","B"),("A","C"),("B","C")):
        key=f"{phase1}_to_{phase2}"
        try:
            with Image.open(stages[phase1]["image_path"]) as a, Image.open(stages[phase2]["image_path"]) as b:
                info=detector(a,b)
            camera_checks[key]=info
            if (not isinstance(info,dict) or info.get("schema")!="hd-camera-robust-v3.3.11" or
                    info.get("status")!="candidate_camera_static" or
                    info.get("selection_dispatch")!="not_dispatched" or info.get("memory_write") is not False):
                reasons.append(f"camera_not_static:{key}")
        except (OSError,ValueError,RuntimeError,TypeError) as exc:
            camera_checks[key]={"status":"camera_unverified","reason":str(exc)}
            reasons.append(f"camera_check_failed:{key}")
    return {"schema":SCHEMA,"timestamp_utc":datetime.now(timezone.utc).isoformat(),
            "status":"candidate_manual_transition_correlated" if not reasons else "transition_blocked",
            "reasons":sorted(set(reasons)),
            "object_id":next(iter(ids)) if len(ids)==1 else None,
            "pid":next(iter(pids)) if len(pids)==1 else None,
            "world_AB_distance":dw_ab,"world_AC_return_distance":dw_ac,
            "cursor_AB_distance_px":dc_ab,"cursor_AC_return_distance_px":dc_ac,
            "limits":{"min_world_AB":minimum_world_move,
                      "max_world_AC":return_world_tolerance,
                      "min_cursor_AB_px":minimum_cursor_move_px,
                      "max_cursor_AC_px":return_cursor_tolerance_px},
            "measurements":measurements,"camera_checks":camera_checks,
            "visual_object_identity":"operator_asserted_not_proven",
            "validated_for_selection":False,"eligible_for_calibration":False,
            "selection_dispatch":"not_dispatched","memory_write":False,
            "note":"A/B/C manual intervention evidence only; same moving physical sprite must be inspected by operator. This is not machine identity verification."}
