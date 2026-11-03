"""v3.3.12 guarded visual evidence: reference/pre/post camera checks.

This is a read-only capture protocol. It does not authorize visual identity,
projection, unit selection or camera stability between sampled frames.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def evaluate_capture_gate(reference_pre, reference_post, pre_post,
                          *, anchor_usable, cursor_stable, image_errors=()):
    checks={"reference_to_before":reference_pre,
            "reference_to_after":reference_post,
            "before_to_after":pre_post}
    approved=(bool(anchor_usable) and bool(cursor_stable) and not image_errors
              and all(isinstance(v,dict) and
                      v.get("schema")=="hd-camera-robust-v3.3.11" and
                      v.get("status")=="candidate_camera_static" and
                      v.get("selection_dispatch")=="not_dispatched" and
                      v.get("memory_write") is False
                      for v in checks.values()))
    # Never label the entire session 'verified': this is sparse sampling.
    return {"schema":"hd-guarded-capture-v3.3.12",
            "timestamp_utc":datetime.now(timezone.utc).isoformat(),
            "status":"candidate_capture_accepted" if approved else "capture_blocked",
            "camera_consistency":"sampled_frames_only" if approved else "unverified",
            "camera_checks":checks,
            "anchor_usable":bool(anchor_usable),"cursor_stable":bool(cursor_stable),
            "image_errors":list(image_errors),
            "visual_object_correspondence":"unverified",
            "validated_for_selection":False,
            "selection_dispatch":"not_dispatched","memory_write":False,
            "note":"Non-atomic captures: sampled-frame comparisons cannot rule out movement between frames. Operator must review identity and camera."}


def capture_guarded(*, pid, object_id, delay, reference, before_path, after_path,
                    mapping_path, allow_candidates=True,
                    screenshot=None, cursor_reader=None, anchor_reader=None,
                    detector=None, sleep=None):
    """Injectable I/O for tests; CLI supplies actual Windows read-only primitives."""
    if not allow_candidates:
        raise ValueError("explicit_allow_candidates_required")
    if not (0<=delay<=120 and pid>0 and object_id>=0):
        raise ValueError("invalid_capture_arguments")
    from PIL import Image
    from .camera_robust_v3_3_11 import detect_robust_camera_motion
    from .screenshot_v3_3_5 import screenshot_client
    from .position_cursor_probe_v3_2 import read_cursor_coordinates
    from .synchronized_calibration_v3_3_2 import synchronized_anchor
    from .object_api import HDObjectAPI, WindowsProcessReader
    from .catalog import mapping_dir
    import time
    screenshot=screenshot or screenshot_client
    cursor_reader=cursor_reader or read_cursor_coordinates
    detector=detector or detect_robust_camera_motion
    sleep=sleep or time.sleep

    # Validate paths before touching the reference.
    files=[Path(reference),Path(before_path),Path(after_path)]
    if len({p.resolve() for p in files})!=3:
        raise ValueError("reference_before_after_paths_must_be_distinct")
    if not files[0].is_file():
        raise ValueError("reference_image_missing")
    # Preflight reference validity; BMP may still be stale, requiring manual inspection.
    with Image.open(reference) as img:
        img.verify()
    sleep(delay)
    errors=[]
    meta_pre=meta_post=None
    cam_pre=cam_post=cam_around=None
    anchor=None
    cursor_pre=cursor_post=None
    try:
        meta_pre=screenshot(pid,before_path)
        cursor_pre=cursor_reader(pid)
        # The only game process access is read-only anchor acquisition.
        if anchor_reader is not None:
            anchor=anchor_reader(pid,object_id,mapping_path)
        else:
            with WindowsProcessReader(pid) as reader:
                api=HDObjectAPI(reader,mapping_dir(mapping_path),allow_candidates=True)
                anchor=synchronized_anchor(api,pid=pid,object_id=object_id)
        cursor_post=cursor_reader(pid)
        meta_post=screenshot(pid,after_path)
        with Image.open(reference) as ref, Image.open(before_path) as pre, Image.open(after_path) as post:
            cam_pre=detector(ref,pre)
            cam_post=detector(ref,post)
            cam_around=detector(pre,post)
    except (OSError,ValueError,RuntimeError,TypeError,KeyError) as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
    stable_cursor=(isinstance(cursor_pre,dict) and isinstance(cursor_post,dict)
                   and cursor_pre.get("game_foreground") is True
                   and cursor_post.get("game_foreground") is True
                   and cursor_pre.get("client")==cursor_post.get("client")
                   and isinstance(anchor,dict) and
                   isinstance(anchor.get("cursor_after"),dict) and
                   anchor["cursor_after"].get("client")==cursor_pre.get("client"))
    gate=evaluate_capture_gate(cam_pre,cam_post,cam_around,
                                anchor_usable=bool(isinstance(anchor,dict) and anchor.get("usable")),
                                cursor_stable=stable_cursor,
                                image_errors=errors)
    gate.update(pid=pid,object_id=object_id,reference_image=str(reference),
                before_image=meta_pre,after_image=meta_post,
                cursor_before=cursor_pre,cursor_after=cursor_post,anchor=anchor,
                delay_seconds=delay)
    return gate
