"""v3.3.16: offline visual review of v3.3.15 independent holdouts.

Fail closed. Never adjusts the fit, reads process memory, clicks or selects.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw

from .calibration_camera_v3_3_14 import sha256_file

SCHEMA = "hd-visual-identity-audit-v3.3.16"
DECISIONS = {"confirmed", "rejected", "inconclusive"}


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _resolve(base, path):
    return (base / str(path)).resolve()


def _point(x, y):
    a, b = float(x), float(y)
    if not all(map(math.isfinite, (a, b))):
        raise ValueError("nonfinite_point")
    return a, b


def _annotate(source, destination, oid, predicted, measured, error):
    if source.resolve() == destination.resolve():
        raise ValueError("source_overlay_collision")
    with Image.open(source) as original:
        image = original.convert("RGB")
    draw = ImageDraw.Draw(image)
    for (x, y), color in ((predicted, "red"), (measured, "lime")):
        draw.ellipse((x-9, y-9, x+9, y+9), outline=color, width=3)
        draw.line((x-13, y, x+13, y), fill=color, width=2)
        draw.line((x, y-13, x, y+13), fill=color, width=2)
    draw.line((*predicted, *measured), fill="yellow", width=3)
    draw.rectangle((0, 0, min(image.width, 610), 34), fill="black")
    draw.text((8, 10), f"ID {oid} | error {error:.3f}px | red=predicted green=observed", fill="white")
    image.save(destination)


def prepare(session_report_path, manifest_path, capture_dir, output_dir, *,
            fit_path=None, binding_path=None):
    """Build overlays and a review template, retaining blocked records.

    Requires the exact v3.3.15 fit, manifest and v3.3.12 capture for each holdout.
    Image and captured anchor provenance must agree. No automatic visual identity.
    """
    session_report_path, manifest_path = Path(session_report_path), Path(manifest_path)
    capture_dir, output_dir = Path(capture_dir), Path(output_dir)
    session = _load(session_report_path)
    manifest = _load(manifest_path)
    if (session.get("schema") != "hd-camera-session-v3.3.15-report"
            or session.get("status") != "candidate_session_numeric_passed"
            or session.get("validated_for_selection") is not False
            or session.get("selection_dispatch") != "not_dispatched"
            or session.get("memory_write") is not False):
        raise ValueError("unaccepted_or_unsafe_session")
    if manifest.get("schema") != "hd-camera-session-v3.3.15" or manifest.get("session") != session.get("session"):
        raise ValueError("manifest_session_mismatch")
    fit = session.get("fit")
    if not isinstance(fit, dict) or fit.get("status") != "candidate_fit_passed_threshold":
        raise ValueError("unaccepted_fit")
    if fit_path is not None and _load(fit_path) != fit:
        raise ValueError("fit_file_mismatch")
    if binding_path is not None:
        binding = _load(binding_path)
        if (binding.get("schema") != "hd-calibration-camera-binding-v3.3.14"
                or fit_path is None
                or binding.get("fit_sha256") != sha256_file(fit_path)
                or binding.get("source_session_report_sha256") != sha256_file(session_report_path)
                or binding.get("reference_sha256") != manifest.get("reference_sha256")
                or binding.get("selection_dispatch") != "not_dispatched"
                or binding.get("memory_write") is not False):
            raise ValueError("binding_mismatch")
    expected = session.get("holdout_ids")
    if (not isinstance(expected, list) or len(expected) < 10 or
            any(type(x) is not int for x in expected) or len(set(expected)) != len(expected)):
        raise ValueError("invalid_holdout_ids")
    if set(expected) & set(session.get("training_ids", [])):
        raise ValueError("training_holdout_overlap")
    audits = fit.get("audit", {}).get("holdouts", [])
    if not isinstance(audits, list) or len(audits) != len(expected):
        raise ValueError("holdout_audit_incomplete")
    by_id = {x.get("object_id"): x for x in audits}
    if len(by_id) != len(expected) or set(by_id) != set(expected):
        raise ValueError("holdout_audit_identity_mismatch")
    records = manifest.get("anchors", [])
    rows = {x["anchor"]["object_id"]: x for x in records
            if isinstance(x, dict) and isinstance(x.get("anchor"), dict)
            and x.get("role") == "holdout"}
    if len(rows) != len(expected) or set(rows) != set(expected):
        raise ValueError("holdout_manifest_mismatch")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError("output_directory_must_be_empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    report_rows = []
    manifest_base = manifest_path.resolve().parent
    for oid in expected:
        reasons = []
        record = rows[oid]
        anchor = record["anchor"]
        image = _resolve(manifest_base, record.get("camera_image", ""))
        capture_path = capture_dir / f"{oid}_guard_v3_3_15.json"
        capture = None
        try:
            capture = _load(capture_path)
            checks = capture.get("camera_checks", {})
            if (capture.get("schema") != "hd-guarded-capture-v3.3.12"
                    or capture.get("status") != "candidate_capture_accepted"
                    or capture.get("camera_consistency") != "sampled_frames_only"
                    or capture.get("anchor_usable") is not True
                    or capture.get("cursor_stable") is not True
                    or capture.get("validated_for_selection") is not False
                    or capture.get("selection_dispatch") != "not_dispatched"
                    or capture.get("memory_write") is not False
                    or capture.get("image_errors")
                    or capture.get("pid") != session.get("pid")
                    or capture.get("object_id") != oid
                    or capture.get("anchor") != anchor):
                reasons.append("capture_or_anchor_mismatch")
            if not isinstance(checks, dict) or any(
                    not isinstance(checks.get(k), dict) or
                    checks[k].get("status") != "candidate_camera_static"
                    for k in ("reference_to_before", "reference_to_after", "before_to_after")):
                reasons.append("camera_checks_not_static")
            before = capture.get("before_image", {})
            if not isinstance(before, dict) or _resolve(Path.cwd(), before.get("path", "")) != image:
                reasons.append("capture_image_path_mismatch")
        except (OSError, ValueError, TypeError, AttributeError):
            reasons.append("capture_unreadable")
        if not image.is_file() or sha256_file(image) != record.get("camera_sha256"):
            reasons.append("image_hash_mismatch")
        audit = by_id[oid]
        try:
            pred = _point(audit["predicted_client_x"], audit["predicted_client_y"])
            meas = _point(audit["measured_client_x"], audit["measured_client_y"])
            error = float(audit["error_px"])
            cx, cy = _point(anchor["cursor_after"]["client"]["x"],
                            anchor["cursor_after"]["client"]["y"])
            if (not math.isfinite(error) or error < 0 or
                    math.hypot(pred[0]-meas[0], pred[1]-meas[1]) - error > 1e-5 or
                    math.hypot(pred[0]-meas[0], pred[1]-meas[1]) - error < -1e-5 or
                    math.hypot(cx-meas[0], cy-meas[1]) > 1e-5):
                reasons.append("audit_coordinates_mismatch")
        except (KeyError, ValueError, TypeError, OverflowError):
            pred, meas, error = None, None, None
            reasons.append("invalid_audit_coordinates")
        overlay = None
        if not reasons:
            try:
                with Image.open(image) as check_image:
                    w, h = check_image.size
                    check_image.verify()
                if not all(0 <= x < w and 0 <= y < h for x, y in (pred, meas)):
                    reasons.append("point_out_of_bounds")
                else:
                    overlay = output_dir / f"{oid}_review.png"
                    _annotate(image, overlay, oid, pred, meas, error)
            except (OSError, ValueError, TypeError):
                reasons.append("overlay_generation_failed")
        report_rows.append({
            "object_id": oid, "status": "pending_review" if not reasons else "blocked",
            "reasons": reasons, "error_px": error, "predicted_client": pred,
            "measured_client": meas, "source_image": str(image),
            "source_sha256": record.get("camera_sha256"),
            "capture_file": str(capture_path),
            "capture_sha256": sha256_file(capture_path) if capture_path.is_file() else None,
            "overlay": str(overlay) if overlay else None,
            "overlay_sha256": sha256_file(overlay) if overlay else None})
    out = {"schema": SCHEMA + "-prepared",
           "created_utc": datetime.now(timezone.utc).isoformat(),
           "session": session["session"], "pid": session["pid"],
           "session_report_sha256": sha256_file(session_report_path),
           "manifest_sha256": sha256_file(manifest_path),
           "fit_sha256": sha256_file(fit_path) if fit_path else None,
           "holdout_ids": expected, "records": report_rows,
           "status": "ready_for_human_review" if all(x["status"] == "pending_review" for x in report_rows) else "blocked",
           "validated_for_selection": False, "selection_dispatch": "not_dispatched",
           "memory_write": False}
    (output_dir / "prepared_report.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    with (output_dir / "reviews.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["object_id", "decision", "reviewer", "reason",
                                               "overlay_sha256"])
        writer.writeheader()
        for row in report_rows:
            writer.writerow({"object_id": row["object_id"], "decision": "inconclusive",
                             "reviewer": "", "reason": "not_reviewed",
                             "overlay_sha256": row["overlay_sha256"] or ""})
    return out


def finalize(prepared_path, reviews_path, output_path):
    """Every holdout must be reviewed explicitly. Never implies selection readiness."""
    prepared_path, reviews_path, output_path = map(Path, (prepared_path, reviews_path, output_path))
    if output_path.exists() or output_path.resolve() in (
            prepared_path.resolve(), reviews_path.resolve()):
        raise FileExistsError("output_must_be_new")
    prepared = _load(prepared_path)
    if (prepared.get("schema") != SCHEMA + "-prepared"
            or prepared.get("validated_for_selection") is not False
            or prepared.get("selection_dispatch") != "not_dispatched"
            or prepared.get("memory_write") is not False):
        raise ValueError("invalid_prepared_report")
    with reviews_path.open(encoding="utf-8-sig", newline="") as f:
        entries = list(csv.DictReader(f))
    expected = prepared["holdout_ids"]
    reviews = {}
    duplicates = []
    for item in entries:
        try:
            oid = int(item["object_id"])
        except (TypeError, ValueError, KeyError):
            raise ValueError("invalid_review_id")
        if oid in reviews:
            duplicates.append(oid)
        reviews[oid] = item
    if duplicates or set(reviews) != set(expected):
        raise ValueError("review_ids_missing_or_duplicate")
    outcomes = []
    for record in prepared["records"]:
        oid = record["object_id"]
        row = reviews[oid]
        reasons = list(record["reasons"])
        decision = row.get("decision", "").strip().lower()
        reviewer, reason = row.get("reviewer", "").strip(), row.get("reason", "").strip()
        if (decision not in DECISIONS or not reviewer or not reason or reason == "not_reviewed"):
            reasons.append("review_incomplete")
        if record["status"] != "pending_review":
            reasons.append("source_blocked")
        overlay = record.get("overlay")
        if not overlay or not Path(overlay).is_file() or sha256_file(overlay) != record["overlay_sha256"] or row.get("overlay_sha256") != record["overlay_sha256"]:
            reasons.append("overlay_hash_mismatch")
        outcomes.append({"object_id": oid, "decision": decision if decision in DECISIONS else "invalid",
                         "reviewer": reviewer, "reason": reason, "reasons": reasons,
                         "error_px": record.get("error_px"), "overlay_sha256": record.get("overlay_sha256")})
    counts = {k: sum(x["decision"] == k and not x["reasons"] for x in outcomes) for k in DECISIONS}
    status = ("operator_visual_review_complete" if not any(x["reasons"] for x in outcomes)
              and counts["inconclusive"] == 0 else "inconclusive")
    result = {"schema": SCHEMA + "-final",
              "created_utc": datetime.now(timezone.utc).isoformat(),
              "session": prepared["session"], "pid": prepared["pid"],
              "prepared_report_sha256": sha256_file(prepared_path),
              "review_csv_sha256": sha256_file(reviews_path),
              "status": status, "counts": counts, "records": outcomes,
              "visual_identity_evidence": "manual_operator_review_only",
              "validated_for_selection": False, "selection_dispatch": "not_dispatched",
              "memory_write": False,
              "note": "Human review does not independently prove Object ID identity or authorize selection."}
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    a = sub.add_parser("prepare")
    a.add_argument("--session-report", required=True)
    a.add_argument("--manifest", required=True)
    a.add_argument("--capture-dir", required=True)
    a.add_argument("--output-dir", required=True)
    a.add_argument("--fit")
    a.add_argument("--binding")
    b = sub.add_parser("finalize")
    b.add_argument("--prepared", required=True)
    b.add_argument("--reviews", required=True)
    b.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        result = prepare(args.session_report, args.manifest, args.capture_dir,
                         args.output_dir, fit_path=args.fit, binding_path=args.binding)
    else:
        result = finalize(args.prepared, args.reviews, args.output)
    print(json.dumps({"status": result["status"], "validated_for_selection": False,
                      "counts": result.get("counts"), "records": len(result["records"])}, indent=2))
    return 0 if result["status"] in ("ready_for_human_review", "operator_visual_review_complete") else 2


if __name__ == "__main__":
    raise SystemExit(main())
