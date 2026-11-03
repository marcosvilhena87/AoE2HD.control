"""v3.3.15: offline, fail-closed camera-session calibration and independent holdout.

No process reads, clicks, or memory writes. Operator evidence is not sensor proof.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from .camera_robust_v3_3_11 import detect_robust_camera_motion
from .calibration_camera_v3_3_14 import sha256_file, bind_calibration
from .synchronized_calibration_v3_3_2 import fit_and_holdout

SCHEMA = "hd-camera-session-v3.3.15"


def evaluate_session(manifest, *, detector=None, min_holdouts=10, threshold_px=25.0):
    """Validate unique independent IDs, source-image evidence, and camera motion.

    Manifest: {session, reference_image, anchors:[{anchor:<v3.3.2>,
    camera_image:<bmp>, camera_sha256:<sha256>, role:train|holdout}], note}.
    All images must be captured contemporaneously by the operator.
    """
    from PIL import Image
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        raise ValueError("invalid_manifest")
    if not isinstance(min_holdouts, int) or min_holdouts < 10:
        raise ValueError("min_holdouts_must_be_at_least_10")
    if not isinstance(threshold_px, (int, float)) or not math.isfinite(threshold_px) or threshold_px <= 0:
        raise ValueError("invalid_threshold")
    if not str(manifest.get("session", "")).strip() or not str(manifest.get("note", "")).strip():
        raise ValueError("session_and_operator_note_required")
    records = manifest.get("anchors")
    if not isinstance(records, list):
        raise ValueError("invalid_anchors")
    reasons = []
    reference = Path(manifest["reference_image"])
    expected_hash = manifest.get("reference_sha256")
    if not isinstance(expected_hash, str) or sha256_file(reference) != expected_hash:
        reasons.append("reference_hash_mismatch")
    with Image.open(reference) as im:
        size = im.size
        im.verify()
    detector = detector or detect_robust_camera_motion
    ids, pids, train, holdout, normalized, checks = set(), set(), [], [], [], []
    for index, record in enumerate(records):
        item_reasons = []
        if not isinstance(record, dict):
            raise ValueError("invalid_anchor_record")
        anchor = record.get("anchor")
        if not isinstance(anchor, dict) or anchor.get("schema") != "hd-synchronized-anchor-v3.3.2":
            raise ValueError("invalid_anchor_schema")
        oid, pid = anchor.get("object_id"), anchor.get("pid")
        if type(oid) is not int or oid < 0 or oid in ids:
            item_reasons.append("invalid_or_duplicate_id")
        ids.add(oid)
        if type(pid) is not int or pid <= 0:
            item_reasons.append("invalid_pid")
        pids.add(pid)
        if anchor.get("usable") is not True or anchor.get("camera_verified_stationary") is True:
            # This flag cannot be upgraded solely from a human assertion.
            if anchor.get("usable") is not True:
                item_reasons.append("anchor_not_usable")
        role = record.get("role")
        if role not in ("train", "holdout"):
            item_reasons.append("invalid_role")
        if not isinstance(record.get("camera_sha256"), str):
            item_reasons.append("missing_image_hash")
        try:
            pic = Path(record["camera_image"])
            if sha256_file(pic) != record.get("camera_sha256"):
                item_reasons.append("image_hash_mismatch")
            with Image.open(pic) as probe:
                if probe.size != size:
                    item_reasons.append("camera_dimensions_mismatch")
                else:
                    with Image.open(reference) as base:
                        result = detector(base, probe)
                    if not isinstance(result, dict) or result.get("schema") != "hd-camera-robust-v3.3.11" or result.get("status") != "candidate_camera_static":
                        item_reasons.append("camera_not_verified_static")
        except (KeyError, OSError, ValueError, TypeError, RuntimeError) as exc:
            item_reasons.append("camera_check_failed:" + type(exc).__name__)
        checks.append({"index":index, "object_id":oid, "role":role, "reasons":item_reasons})
        if item_reasons:
            reasons.append("anchor_" + str(index) + "_blocked")
        else:
            normalized.append(anchor)
            (train if role == "train" else holdout).append(oid)
    if len(pids) != 1:
        reasons.append("mixed_pids")
    if len(train) < 3:
        reasons.append("insufficient_training_anchors")
    if len(holdout) < min_holdouts:
        reasons.append("insufficient_independent_holdouts")
    fit = None
    if not reasons:
        try:
            fit = fit_and_holdout(normalized, holdout_ids=holdout, max_rmse_px=threshold_px)
        except (ValueError, KeyError, TypeError, ZeroDivisionError) as exc:
            reasons.append("fit_failed:" + type(exc).__name__)
        else:
            if fit["status"] != "candidate_fit_passed_threshold":
                reasons.append("holdout_numeric_or_geometry_failure")
            errors = fit["audit"]
            if errors.get("holdout_rmse_px") is None or not math.isfinite(errors["holdout_rmse_px"]):
                reasons.append("nonfinite_holdout_rmse")
    return {"schema":SCHEMA + "-report",
            "created_utc":datetime.now(timezone.utc).isoformat(),
            "session":manifest["session"], "pid":next(iter(pids)) if len(pids)==1 else None,
            "reference_sha256":expected_hash, "camera_checks":checks,
            "training_ids":train, "holdout_ids":holdout, "threshold_px":threshold_px,
            "min_holdouts":min_holdouts, "fit":fit, "reasons":reasons,
            "status":"candidate_session_numeric_passed" if not reasons else "blocked",
            "camera_verified_stationary":"sampled_images_only",
            "visual_object_identity":"unverified",
            "validated_for_selection":False, "selection_dispatch":"not_dispatched",
            "memory_write":False,
            "note":"Image matching and operator attestation are not atomic camera or Object ID proof."}


def run_manifest(manifest_path, output_dir, *, min_holdouts=10, threshold_px=25.0):
    """Create a fit, camera binding and report without overwriting earlier evidence."""
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    # Relative paths in manifest are relative to manifest directory.
    base = manifest_path.resolve().parent
    manifest["reference_image"] = str((base / manifest["reference_image"]).resolve())
    for record in manifest.get("anchors", []):
        record["camera_image"] = str((base / record["camera_image"]).resolve())
    report = evaluate_session(manifest, min_holdouts=min_holdouts, threshold_px=threshold_px)
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError("output_directory_must_be_empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "session_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if report["status"] == "candidate_session_numeric_passed":
        fit_file = output_dir / "fit_v3_3_15.json"
        fit_file.write_text(json.dumps(report["fit"], indent=2), encoding="utf-8")
        binding = bind_calibration(fit_file, manifest["reference_image"],
                                   provenance="contemporaneous_operator_attested",
                                   operator_note=manifest["note"])
        binding["source_session_report_sha256"] = sha256_file(output_dir / "session_report.json")
        (output_dir / "camera_binding_v3_3_15.json").write_text(
            json.dumps(binding, indent=2), encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--threshold-px", type=float, default=25.0)
    parser.add_argument("--min-holdouts", type=int, default=10)
    args = parser.parse_args(argv)
    result = run_manifest(args.manifest, args.output_dir,
                          min_holdouts=args.min_holdouts, threshold_px=args.threshold_px)
    print(json.dumps({key:result[key] for key in ("status","reasons","training_ids","holdout_ids",
                                                  "validated_for_selection")}, indent=2))
    return 0 if result["status"] == "candidate_session_numeric_passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
