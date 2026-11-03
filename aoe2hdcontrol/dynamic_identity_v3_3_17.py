"""v3.3.17 — Read-only dynamic identity experiment using operator movement.

Compares a moving target and a stationary negative control before/after a
manual action. The camera is checked on four sampled screenshots. No input
dispatch, memory writes, offset promotion, or selection authorization.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw

from .calibration_camera_v3_3_14 import sha256_file
from .camera_robust_v3_3_11 import detect_robust_camera_motion

SCHEMA = "hd-dynamic-identity-v3.3.17"
STATES = ("target_before", "control_before", "target_after", "control_after")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def finite_point(x, y):
    a, b = float(x), float(y)
    if not math.isfinite(a) or not math.isfinite(b):
        raise ValueError("nonfinite_coordinate")
    return a, b


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def displacement(before, after):
    return (after[0] - before[0], after[1] - before[1])


def _guarded_capture(path, oid):
    data = load_json(path)
    checks = data.get("camera_checks")
    anchor = data.get("anchor")
    if (data.get("schema") != "hd-guarded-capture-v3.3.12"
            or data.get("status") != "candidate_capture_accepted"
            or data.get("object_id") != oid
            or data.get("anchor_usable") is not True
            or data.get("cursor_stable") is not True
            or data.get("camera_consistency") != "sampled_frames_only"
            or data.get("validated_for_selection") is not False
            or data.get("selection_dispatch") != "not_dispatched"
            or data.get("memory_write") is not False
            or data.get("image_errors")
            or not isinstance(anchor, dict)
            or anchor.get("schema") != "hd-synchronized-anchor-v3.3.2"
            or anchor.get("object_id") != oid
            or anchor.get("pid") != data.get("pid")
            or anchor.get("usable") is not True
            or not isinstance(checks, dict)
            or any(not isinstance(checks.get(k), dict)
                   or checks[k].get("schema") != "hd-camera-robust-v3.3.11"
                   or checks[k].get("status") != "candidate_camera_static"
                   for k in ("reference_to_before", "reference_to_after", "before_to_after"))):
        raise ValueError("guarded_capture_not_accepted")
    unit = anchor["unit"]
    if unit.get("finite") is not True:
        raise ValueError("world_position_not_finite")
    world = finite_point(unit["candidate_world_x"], unit["candidate_world_y"])
    client = anchor["cursor_after"]["client"]
    screen = finite_point(client["x"], client["y"])
    if data.get("cursor_after", {}).get("client") != client:
        raise ValueError("anchor_cursor_mismatch")
    image_info = data.get("before_image")
    if not isinstance(image_info, dict) or not image_info.get("path"):
        raise ValueError("missing_image_provenance")
    return data, world, screen, Path(image_info["path"])


def analyze(manifest_path, output_dir, *, detector=None):
    """Fail closed on incomplete/mixed captures, camera shifts, or weak motion.

    Paths in the dynamic manifest are resolved relative to the manifest's
    directory. Captured image paths are resolved relative to the working dir
    (as emitted by the v3.3.12 capture command).
    """
    manifest_path = Path(manifest_path)
    m = load_json(manifest_path)
    if m.get("schema") != SCHEMA or not str(m.get("operator_note", "")).strip():
        raise ValueError("invalid_manifest_or_missing_operator_note")
    if m.get("movement_method") != "manual_in_game":
        raise ValueError("only_manual_movement_allowed")
    target, control = m.get("target_id"), m.get("control_id")
    if (type(target) is not int or type(control) is not int or
            target < 0 or control < 0 or target == control):
        raise ValueError("invalid_target_control_ids")
    thresholds = m.get("thresholds", {})
    try:
        min_move = float(thresholds.get("target_min_client_px", 30))
        min_world = float(thresholds.get("target_min_world", 0.25))
        max_control = float(thresholds.get("control_max_client_px", 8))
        max_world_control = float(thresholds.get("control_max_world", 0.2))
        max_delta_error = float(thresholds.get("delta_max_error_px", 12))
        if not (all(math.isfinite(x) and x > 0 for x in
                    (min_move, min_world, max_control, max_world_control, max_delta_error))):
            raise ValueError
    except (AttributeError, TypeError, ValueError):
        raise ValueError("invalid_thresholds")
    root = manifest_path.resolve().parent
    fit_path = root / str(m["fit_file"])
    reference_path = root / str(m["reference_image"])
    captures = m.get("captures", {})
    if not isinstance(captures, dict) or set(captures) != set(STATES):
        raise ValueError("four_required_capture_states")
    if len({str(v) for v in captures.values()}) != 4:
        raise ValueError("duplicate_capture_paths")
    fit = load_json(fit_path)
    if (fit.get("schema") != "hd-synchronized-calibration-v3.3.2"
            or fit.get("status") != "candidate_fit_passed_threshold"
            or sha256_file(fit_path) != m.get("fit_sha256")):
        raise ValueError("fit_hash_or_status_invalid")
    matrix = fit.get("calibration", {})
    if matrix.get("schema") != "hd-affine-projection-v3.3":
        raise ValueError("invalid_affine_fit")
    ax, ay = matrix["x_coefficients"], matrix["y_coefficients"]
    if not (len(ax) == len(ay) == 3 and all(
            math.isfinite(float(q)) for q in list(ax) + list(ay))):
        raise ValueError("invalid_projection_coefficients")
    detector = detector or detect_robust_camera_motion
    items, reasons, pids, files = {}, [], set(), []
    for state in STATES:
        oid = target if state.startswith("target_") else control
        path = (root / captures[state]).resolve()
        try:
            data, world, client, image_path = _guarded_capture(path, oid)
            if not image_path.is_absolute():
                image_path = image_path.resolve()
            image_hash = sha256_file(image_path)
            with Image.open(image_path) as im:
                im.verify()
            items[state] = {"object_id": oid, "pid": data["pid"],
                            "world": world, "client": client,
                            "capture_file": str(path),
                            "capture_sha256": sha256_file(path),
                            "image": str(image_path), "image_sha256": image_hash}
            pids.add(data["pid"])
            files.append(image_path)
        except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError) as exc:
            reasons.append(f"{state}_invalid:{type(exc).__name__}:{exc}")
    if len(pids) != 1 or not pids:
        reasons.append("mixed_or_missing_pid")
    expected_pid = m.get("pid")
    if type(expected_pid) is not int or pids != {expected_pid}:
        reasons.append("session_pid_mismatch")
    if not reference_path.is_file() or sha256_file(reference_path) != m.get("reference_sha256"):
        reasons.append("reference_hash_mismatch")
    camera_checks = []
    if not reasons:
        try:
            with Image.open(reference_path) as ref:
                reference_size = ref.size
            for state in STATES:
                image_path = Path(items[state]["image"])
                with Image.open(reference_path) as ref, Image.open(image_path) as shot:
                    if shot.size != reference_size:
                        result = {"status": "dimensions_mismatch"}
                    else:
                        result = detector(ref, shot)
                camera_checks.append({"state": state, "status": result.get("status"),
                                      "result": result})
                if (result.get("schema") != "hd-camera-robust-v3.3.11"
                        or result.get("status") != "candidate_camera_static"):
                    reasons.append(state + "_camera_shift_or_unverified")
        except (OSError, RuntimeError, ValueError, TypeError) as exc:
            reasons.append("camera_validation_failed:" + type(exc).__name__)
    measurements = {}
    if not reasons:
        for role in ("target", "control"):
            before, after = items[role+"_before"], items[role+"_after"]
            world_delta = displacement(before["world"], after["world"])
            screen_delta = displacement(before["client"], after["client"])
            predicted_delta = (float(ax[0])*world_delta[0] + float(ax[1])*world_delta[1],
                               float(ay[0])*world_delta[0] + float(ay[1])*world_delta[1])
            measurements[role] = {"object_id": before["object_id"],
                                   "world_delta": world_delta,
                                   "screen_delta": screen_delta,
                                   "predicted_screen_delta": predicted_delta,
                                   "world_distance": math.hypot(*world_delta),
                                   "screen_distance_px": math.hypot(*screen_delta),
                                   "delta_residual_px": distance(predicted_delta, screen_delta)}
        t, c = measurements["target"], measurements["control"]
        if t["world_distance"] < min_world:
            reasons.append("target_world_movement_too_small")
        if t["screen_distance_px"] < min_move:
            reasons.append("target_visual_movement_too_small")
        if t["delta_residual_px"] > max_delta_error:
            reasons.append("target_delta_prediction_mismatch")
        if c["world_distance"] > max_world_control:
            reasons.append("negative_control_world_moved")
        if c["screen_distance_px"] > max_control:
            reasons.append("negative_control_visual_moved")
        if c["delta_residual_px"] > max_delta_error:
            reasons.append("negative_control_projection_mismatch")
    out = {"schema": SCHEMA+"-report",
           "created_utc": datetime.now(timezone.utc).isoformat(),
           "status": "candidate_dynamic_consistency_passed" if not reasons else "blocked",
           "reasons": reasons, "pid": expected_pid, "target_id": target,
           "control_id": control, "movement_method": "manual_in_game",
           "fit_sha256": m["fit_sha256"],
           "reference_sha256": m.get("reference_sha256"),
           "manifest_sha256": sha256_file(manifest_path),
           "camera_consistency": "sampled_images_only",
           "camera_checks": camera_checks, "captures": items,
           "measurements": measurements, "thresholds": thresholds,
           "visual_object_identity": "dynamic_correspondence_candidate_only",
           "validated_for_selection": False,
           "selection_dispatch": "not_dispatched", "memory_write": False,
           "note": "Motion correspondence depends on operator pointing at the correct object; candidate success is not independent identity proof. No active control."}
    outdir = Path(output_dir)
    if outdir.exists() and any(outdir.iterdir()):
        raise FileExistsError("output_directory_must_be_empty")
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "dynamic_report.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    if not reasons:
        with Image.open(items["target_after"]["image"]) as im:
            canvas = im.convert("RGB")
        d = ImageDraw.Draw(canvas)
        before = items["target_before"]["client"]
        after = items["target_after"]["client"]
        d.line((*before, *after), fill="yellow", width=4)
        for (x, y), color in ((before, "red"), (after, "lime")):
            d.ellipse((x-9, y-9, x+9, y+9), outline=color, width=3)
        d.rectangle((0, 0, min(canvas.width, 560), 32), fill="black")
        d.text((8, 9), f"target {target}: before RED after GREEN; operator evidence only", fill="white")
        canvas.save(outdir / "target_motion_review.png")
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    result = analyze(args.manifest, args.output_dir)
    print(json.dumps({k: result[k] for k in
                      ("status", "reasons", "target_id", "control_id",
                       "measurements", "validated_for_selection")}, indent=2))
    return 0 if result["status"] == "candidate_dynamic_consistency_passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
