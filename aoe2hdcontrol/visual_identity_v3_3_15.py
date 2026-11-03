"""v3.3.15 — assisted, auditable correspondence of Object ID and cursor.

Human declarations are explicit; stable camera frames plus repeatability are
necessary but not sufficient for automated visual identity proof.
"""
from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from pathlib import Path

from .guarded_projection_v3_3_13 import _ready_capture
from .calibration_camera_v3_3_14 import sha256_file

SCHEMA="hd-visual-object-review-v3.3.15"
AUDIT_SCHEMA="hd-visual-object-repeat-audit-v3.3.15"
REVIEW_STATES={"confirmed","rejected","uncertain"}
TARGET="unit_base_center"


def _positive_int(value):
    return type(value) is int and value>0


def _image_path(capture):
    image=capture.get("before_image")
    if not isinstance(image,dict) or not image.get("path"):
        raise ValueError("capture_has_no_before_image")
    return Path(image["path"])


def _numeric(capture):
    anchor=capture.get("anchor")
    if not isinstance(anchor,dict) or not isinstance(anchor.get("unit"),dict):
        raise ValueError("capture_anchor_missing")
    a=anchor["unit"]
    if a.get("finite") is not True:
        raise ValueError("nonfinite_object_position")
    cursor=anchor.get("cursor_after",{}).get("client")
    if not isinstance(cursor,dict):
        raise ValueError("cursor_missing")
    world=(float(a["candidate_world_x"]),float(a["candidate_world_y"]))
    client=(float(cursor["x"]),float(cursor["y"]))
    if not all(math.isfinite(v) for v in (*world,*client)):
        raise ValueError("nonfinite_coordinates")
    return world,client


def prepare_review(capture, *, capture_path, screenshot_path, output_image,
                   crop_radius=160):
    """Generate visual evidence: source frame with cursor crosshair and inset."""
    from PIL import Image,ImageDraw
    if not _positive_int(capture.get("pid")) or type(capture.get("object_id")) is not int:
        raise ValueError("invalid_identity")
    if not (32<=crop_radius<=512):
        raise ValueError("invalid_crop_radius")
    source=_image_path(capture)
    if source.resolve()!=Path(screenshot_path).resolve():
        raise ValueError("screenshot_capture_path_mismatch")
    if Path(output_image).resolve() in {source.resolve(),Path(capture_path).resolve()}:
        raise ValueError("output_overlaps_source")
    world,cursor=_numeric(capture)
    with Image.open(source) as im:
        im.verify()
    with Image.open(source) as im:
        picture=im.convert("RGB")
    w,h=picture.size
    if not (0<=cursor[0]<w and 0<=cursor[1]<h):
        raise ValueError("cursor_out_of_bounds")
    if not isinstance(capture.get("before_image"),dict) or (
            capture["before_image"].get("width")!=w or capture["before_image"].get("height")!=h):
        raise ValueError("screenshot_dimensions_mismatch")
    original=picture.copy()
    cx,cy=cursor
    draw=ImageDraw.Draw(picture)
    draw.ellipse((cx-11,cy-11,cx+11,cy+11),outline="yellow",width=3)
    draw.line((cx-22,cy,cx+22,cy),fill="yellow",width=2)
    draw.line((cx,cy-22,cx,cy+22),fill="yellow",width=2)
    # Crop without modifying the source image; scale in nearest-neighbor
    # to preserve sharp unit sprites for operator scrutiny.
    left=max(0,round(cx)-crop_radius)
    top=max(0,round(cy)-crop_radius)
    right=min(w,round(cx)+crop_radius)
    bottom=min(h,round(cy)+crop_radius)
    inset=original.crop((left,top,right,bottom))
    inset=inset.resize((min(600,inset.width*2),min(600,inset.height*2)),Image.Resampling.NEAREST)
    out=Image.new("RGB",(w+inset.width,max(h,inset.height+52)),(12,18,26))
    out.paste(picture,(0,0))
    out.paste(inset,(w,52))
    label=f"ID {capture['object_id']} | cursor ({cx:.1f},{cy:.1f}) | manual review only"
    ImageDraw.Draw(out).text((w+8,12),label[:100],fill="white")
    out.save(output_image)
    return {"schema":SCHEMA,
            "created_utc":datetime.now(timezone.utc).isoformat(),
            "object_id":capture["object_id"],"pid":capture["pid"],
            "capture_file":str(capture_path),"capture_sha256":sha256_file(capture_path),
            "screenshot_file":str(source),"screenshot_sha256":sha256_file(source),
            "reference_image":capture.get("reference_image"),
            "reference_sha256":sha256_file(capture["reference_image"]) if
              capture.get("reference_image") and Path(capture["reference_image"]).is_file() else None,
            "annotated_image":str(output_image),
            "world":{"x":world[0],"y":world[1]},
            "cursor":{"x":cx,"y":cy},
            "camera_capture_status":capture.get("status"),
            "camera_checks_passed":bool(_ready_capture(capture)),
            "target":TARGET,
            "review":{"identity":"uncertain","isolated":False,
                      "cursor_on_target":False,"reviewer":"","note":""},
            "status":"pending_manual_review",
            "visual_identity_automatically_verified":False,
            "validated_for_selection":False,
            "selection_dispatch":"not_dispatched","memory_write":False,
            "note":"Operator must inspect sprite at cursor and independently verify Object ID. An image alone cannot reveal Object ID."}


def adjudicate_review(review, *, identity, isolated, cursor_on_target,
                      reviewer, note):
    """Human approval, *not* machine-verified identity."""
    if review.get("schema")!=SCHEMA:
        raise ValueError("invalid_review_schema")
    if identity not in REVIEW_STATES:
        raise ValueError("invalid_identity_state")
    if type(isolated) is not bool or type(cursor_on_target) is not bool:
        raise ValueError("boolean_flags_required")
    if not str(reviewer).strip() or not str(note).strip():
        raise ValueError("reviewer_and_note_required")
    if identity=="confirmed" and not (isolated and cursor_on_target):
        raise ValueError("confirmation_requires_isolation_and_cursor_target")
    result=dict(review)
    result["review"]={"identity":identity,"isolated":isolated,
                      "cursor_on_target":cursor_on_target,
                      "reviewer":str(reviewer),"note":str(note)}
    result["status"]="operator_confirmed_candidate" if identity=="confirmed" else "manual_review_rejected_or_uncertain"
    result["visual_identity_automatically_verified"]=False
    result["validated_for_selection"]=False
    return result


def audit_repeat(first,second,*,first_capture,second_capture,
                 first_image,second_image,world_tolerance=0.02,
                 cursor_tolerance_px=15.0):
    """Two independent captures, hash-bound source, matched camera reference."""
    from .camera_robust_v3_3_11 import detect_robust_camera_motion
    from PIL import Image
    if any(not math.isfinite(v) or v<0 for v in (world_tolerance,cursor_tolerance_px)):
        raise ValueError("invalid_tolerance")
    reasons=[]
    for review,cap,path,image in ((first,first_capture,first.get("capture_file"),first_image),
                                  (second,second_capture,second.get("capture_file"),second_image)):
        if review.get("schema")!=SCHEMA or review.get("status")!="operator_confirmed_candidate":
            reasons.append("manual_review_not_confirmed")
        if (not isinstance(review.get("review"),dict) or
                review["review"].get("identity")!="confirmed" or
                review["review"].get("isolated") is not True or
                review["review"].get("cursor_on_target") is not True or
                not str(review["review"].get("reviewer","")).strip()):
            reasons.append("manual_review_incomplete")
        if not _ready_capture(cap):
            reasons.append("camera_capture_blocked")
        if sha256_file(path)!=review.get("capture_sha256"):
            reasons.append("capture_hash_mismatch")
        if Path(_image_path(cap)).resolve()!=Path(image).resolve() or (
                sha256_file(image)!=review.get("screenshot_sha256")):
            reasons.append("screenshot_hash_mismatch")
        if cap.get("pid")!=review.get("pid") or cap.get("object_id")!=review.get("object_id"):
            reasons.append("review_identity_mismatch")
    if first.get("capture_sha256")==second.get("capture_sha256") or (
            Path(first.get("capture_file","")).resolve()==Path(second.get("capture_file","")).resolve()):
        reasons.append("captures_not_independent")
    if first.get("object_id")!=second.get("object_id") or first.get("pid")!=second.get("pid"):
        reasons.append("object_or_pid_mismatch")
    if (not first.get("reference_sha256") or
            first.get("reference_sha256")!=second.get("reference_sha256")):
        reasons.append("camera_reference_mismatch")
    for cap,review in ((first_capture,first),(second_capture,second)):
        world,cursor=_numeric(cap)
        if any(abs(a-b)>1e-6 for a,b in zip(world,(review["world"]["x"],review["world"]["y"]))):
            reasons.append("review_world_mismatch")
        if any(abs(a-b)>1e-6 for a,b in zip(cursor,(review["cursor"]["x"],review["cursor"]["y"]))):
            reasons.append("review_cursor_mismatch")
    world_delta=math.dist((first["world"]["x"],first["world"]["y"]),
                           (second["world"]["x"],second["world"]["y"]))
    cursor_delta=math.dist((first["cursor"]["x"],first["cursor"]["y"]),
                            (second["cursor"]["x"],second["cursor"]["y"]))
    if world_delta>world_tolerance:reasons.append("unit_position_changed")
    if cursor_delta>cursor_tolerance_px:reasons.append("cursor_not_repeatable")
    camera=None
    try:
        with Image.open(first_image) as a,Image.open(second_image) as b:
            camera=detect_robust_camera_motion(a,b)
        if camera.get("status")!="candidate_camera_static":
            reasons.append("camera_changed_between_captures")
    except (OSError,ValueError,RuntimeError) as exc:
        reasons.append("camera_comparison_error:"+str(exc))
    return {"schema":AUDIT_SCHEMA,
            "timestamp_utc":datetime.now(timezone.utc).isoformat(),
            "status":"candidate_operator_correspondence_repeatable" if not reasons else "correspondence_blocked",
            "reasons":sorted(set(reasons)),
            "pid":first.get("pid"),"object_id":first.get("object_id"),
            "world_distance":world_delta,"cursor_distance_px":cursor_delta,
            "camera_check":camera,
            "visual_identity_automatically_verified":False,
            "manual_identity_review":"two_operator_assertions_not_independent_id_proof",
            "validated_for_selection":False,
            "eligible_for_calibration":"manual_review_required",
            "selection_dispatch":"not_dispatched","memory_write":False,
            "note":"Repeatable operator assertions do not prove unit identity; never auto-dispatch game commands."}
