"""v3.3.18: offline multi-session, multi-direction dynamic repeatability audit.

Consumes v3.3.15 and v3.3.17 reports, never sends commands. Does not
prove a restart or identity merely from operator-supplied metadata.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path

from .calibration_camera_v3_3_14 import sha256_file

SCHEMA = "hd-multisession-dynamic-v3.3.18"
SESSION_SCHEMA = "hd-camera-session-v3.3.15-report"
DYNAMIC_SCHEMA = "hd-dynamic-identity-v3.3.17-report"
MANIFEST_SCHEMA = "hd-dynamic-identity-v3.3.17"
HEX = re.compile(r"^[a-f0-9]{64}$")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def valid_sha(v):
    return isinstance(v, str) and bool(HEX.fullmatch(v))


def checked_file(base, item, reasons, label):
    """Require a local file and a committed expected digest; retain failures."""
    if not isinstance(item, dict) or not valid_sha(item.get("sha256")):
        reasons.append(label + "_missing_hash")
        return None
    p = (base / str(item.get("path", ""))).resolve()
    try:
        if not p.is_file() or sha256_file(p) != item["sha256"]:
            reasons.append(label + "_hash_mismatch")
            return None
    except (OSError, ValueError):
        reasons.append(label + "_unreadable")
        return None
    return p


def numeric(v):
    if isinstance(v, bool):
        raise ValueError("bool_not_number")
    n = float(v)
    if not math.isfinite(n):
        raise ValueError("nonfinite")
    return n


def quadrant(dx, dy):
    if dx == 0 or dy == 0:
        return "axis"
    return ("E" if dx > 0 else "W") + ("S" if dy > 0 else "N")


def audit(manifest_path, output_dir, *, min_sessions=3,
          min_trials_per_session=2, min_quadrants=4, max_rmse_px=12.):
    if (type(min_sessions) is not int or min_sessions < 2
            or type(min_trials_per_session) is not int or min_trials_per_session < 2
            or type(min_quadrants) is not int or not 1 <= min_quadrants <= 4
            or not math.isfinite(max_rmse_px) or max_rmse_px <= 0):
        raise ValueError("invalid_audit_thresholds")
    manifest_path = Path(manifest_path)
    m = read_json(manifest_path)
    if (m.get("schema") != SCHEMA or not isinstance(m.get("sessions"), list)
            or not str(m.get("operator_note", "")).strip()):
        raise ValueError("invalid_manifest")
    root = manifest_path.resolve().parent
    reasons, session_results, accepted = [], [], []
    session_keys, pids, boot_tokens, exe_hashes = set(), set(), set(), set()
    reused_reports, reused_captures = set(), set()
    for i, entry in enumerate(m["sessions"]):
        issues = []
        if not isinstance(entry, dict):
            reasons.append(f"session_{i}_invalid")
            continue
        key = entry.get("session_id")
        boot = entry.get("boot_id")
        pid = entry.get("pid")
        exe = entry.get("executable", {})
        version = entry.get("game_version")
        note = entry.get("restart_attestation")
        if not isinstance(key, str) or not key.strip() or key in session_keys:
            issues.append("missing_or_duplicate_session_id")
        session_keys.add(key)
        if not isinstance(boot, str) or not boot.strip() or boot in boot_tokens:
            issues.append("missing_or_duplicate_boot_id")
        boot_tokens.add(boot)
        if type(pid) is not int or pid <= 0 or pid in pids:
            issues.append("invalid_or_reused_pid")
        pids.add(pid)
        if (not isinstance(note, str) or not note.strip()
                or not isinstance(version, str) or not version.strip()):
            issues.append("missing_version_or_restart_attestation")
        exe_path = checked_file(root, exe, issues, "executable")
        if exe_path:
            exe_hashes.add(exe["sha256"])
        calibration_path = checked_file(root, entry.get("calibration_report"), issues, "calibration")
        fit_path = checked_file(root, entry.get("fit_file"), issues, "fit")
        calibration = fit = None
        try:
            if calibration_path:
                calibration = read_json(calibration_path)
                if (calibration.get("schema") != SESSION_SCHEMA or
                        calibration.get("status") != "candidate_session_numeric_passed" or
                        calibration.get("pid") != pid or
                        calibration.get("validated_for_selection") is not False or
                        calibration.get("selection_dispatch") != "not_dispatched" or
                        calibration.get("memory_write") is not False or
                        len(calibration.get("holdout_ids", [])) < 10):
                    issues.append("calibration_session_not_accepted")
            if fit_path:
                fit = read_json(fit_path)
                if (fit.get("schema") != "hd-synchronized-calibration-v3.3.2"
                        or fit.get("status") != "candidate_fit_passed_threshold"
                        or (calibration and calibration.get("fit") != fit)):
                    issues.append("calibration_fit_mismatch")
        except (OSError, ValueError, AttributeError, TypeError):
            issues.append("invalid_calibration_json")
        trials = entry.get("trials", [])
        if not isinstance(trials, list) or len(trials) < min_trials_per_session:
            issues.append("insufficient_trials")
            trials = trials if isinstance(trials, list) else []
        local_ids, trial_rows = set(), []
        for j, trial in enumerate(trials):
            errors = []
            if not isinstance(trial, dict):
                issues.append(f"trial_{j}_invalid")
                continue
            report_path = checked_file(root, trial.get("report"), errors, "dynamic_report")
            m_path = checked_file(root, trial.get("manifest"), errors, "dynamic_manifest")
            report = dyn_manifest = None
            try:
                if report_path:
                    report = read_json(report_path)
                if m_path:
                    dyn_manifest = read_json(m_path)
            except (OSError, ValueError, TypeError):
                errors.append("invalid_dynamic_json")
            target = control = None
            q = None
            error = None
            if report is not None and dyn_manifest is not None:
                target, control = report.get("target_id"), report.get("control_id")
                if (report.get("schema") != DYNAMIC_SCHEMA or
                        report.get("status") != "candidate_dynamic_consistency_passed" or
                        report.get("reasons") != [] or
                        report.get("validated_for_selection") is not False or
                        report.get("selection_dispatch") != "not_dispatched" or
                        report.get("memory_write") is not False or
                        report.get("pid") != pid or
                        report.get("movement_method") != "manual_in_game" or
                        report.get("camera_consistency") != "sampled_images_only" or
                        report.get("visual_object_identity") != "dynamic_correspondence_candidate_only"):
                    errors.append("dynamic_status_or_safety_invalid")
                if (dyn_manifest.get("schema") != MANIFEST_SCHEMA or
                        dyn_manifest.get("pid") != pid or
                        dyn_manifest.get("target_id") != target or
                        dyn_manifest.get("control_id") != control or
                        dyn_manifest.get("fit_sha256") != (sha256_file(fit_path) if fit_path else None) or
                        report.get("fit_sha256") != dyn_manifest.get("fit_sha256") or
                        report.get("manifest_sha256") != sha256_file(m_path) or
                        dyn_manifest.get("movement_method") != "manual_in_game"):
                    errors.append("dynamic_manifest_or_fit_mismatch")
                if not (type(target) is int and type(control) is int and
                        target != control and target >= 0 and control >= 0):
                    errors.append("invalid_object_ids")
                if target in local_ids or control in local_ids:
                    errors.append("reused_object_id_within_session")
                local_ids.update((target, control))
                if report_path in reused_reports or m_path in reused_reports:
                    errors.append("reused_report_or_manifest")
                reused_reports.update((report_path, m_path))
                capture_rows = report.get("captures")
                if not isinstance(capture_rows, dict) or set(capture_rows) != {
                        "target_before", "target_after", "control_before", "control_after"}:
                    errors.append("missing_capture_provenance")
                else:
                    for state, capture in capture_rows.items():
                        if not isinstance(capture, dict):
                            errors.append(state+"_invalid")
                            continue
                        for field, sha_field in (("capture_file", "capture_sha256"),
                                                 ("image", "image_sha256")):
                            file_path = checked_file(Path.cwd(), {
                                "path": capture.get(field), "sha256": capture.get(sha_field)
                            }, errors, state+"_"+field)
                            if file_path is not None:
                                if field == "capture_file" and file_path in reused_captures:
                                    errors.append("reused_capture_between_trials")
                                if field == "capture_file":
                                    reused_captures.add(file_path)
                        if capture.get("pid") != pid or capture.get("object_id") != (
                                target if state.startswith("target") else control):
                            errors.append(state+"_identity_mismatch")
                try:
                    t = report["measurements"]["target"]
                    c = report["measurements"]["control"]
                    world = [numeric(z) for z in t["world_delta"]]
                    observed = [numeric(z) for z in t["screen_delta"]]
                    predicted = [numeric(z) for z in t["predicted_screen_delta"]]
                    ctrl_world = [numeric(z) for z in c["world_delta"]]
                    ctrl_observed = [numeric(z) for z in c["screen_delta"]]
                    ctrl_predicted = [numeric(z) for z in c["predicted_screen_delta"]]
                    if any(len(v) != 2 for v in (world, observed, predicted,
                                                   ctrl_world, ctrl_observed, ctrl_predicted)):
                        raise ValueError("invalid_vector")
                    error = math.dist(observed, predicted)
                    ctrl_error = math.dist(ctrl_observed, ctrl_predicted)
                    if (abs(error - numeric(t["delta_residual_px"])) > 1e-5 or
                            abs(ctrl_error - numeric(c["delta_residual_px"])) > 1e-5 or
                            math.hypot(*observed) < 30 or
                            math.hypot(*world) < 0.25 or
                            math.hypot(*ctrl_observed) > 8 or
                            math.hypot(*ctrl_world) > 0.2 or
                            error > max_rmse_px or ctrl_error > max_rmse_px):
                        errors.append("dynamic_metrics_threshold_or_consistency_failed")
                    q = quadrant(*observed)
                    if q == "axis":
                        errors.append("axis_not_quadrant")
                except (TypeError, KeyError, ValueError, OverflowError):
                    errors.append("invalid_dynamic_metrics")
            trial_row = {"index": j, "target_id": target, "control_id": control,
                         "quadrant": q, "delta_error_px": error,
                         "status": "candidate_replicated_trial" if not errors else "blocked",
                         "reasons": errors}
            trial_rows.append(trial_row)
            if errors:
                issues.append(f"trial_{j}_blocked")
            else:
                accepted.append({"session_id": key, "pid": pid, **trial_row})
        if issues:
            reasons.append(f"session_{i}_blocked")
        session_results.append({"session_id": key, "boot_id": boot,
                                "pid": pid, "game_version": version,
                                "executable_sha256": exe.get("sha256") if isinstance(exe, dict) else None,
                                "status": "candidate_session_passed" if not issues else "blocked",
                                "reasons": issues, "trials": trial_rows})
    if len(session_results) < min_sessions:
        reasons.append("insufficient_sessions")
    if len(pids) != len(session_results) or len(boot_tokens) != len(session_results):
        reasons.append("session_independence_not_attested")
    if len(exe_hashes) != 1:
        reasons.append("inconsistent_or_missing_executable_hash")
    if len({s.get("game_version") for s in session_results}) != 1:
        reasons.append("mixed_game_versions")
    quadrants = sorted({x["quadrant"] for x in accepted})
    if len(quadrants) < min_quadrants:
        reasons.append("insufficient_directional_coverage")
    if len(accepted) < min_sessions * min_trials_per_session:
        reasons.append("insufficient_accepted_trials")
    errors = [x["delta_error_px"] for x in accepted]
    stats = {"accepted_trials": len(accepted), "total_trials": sum(
                len(s["trials"]) for s in session_results),
             "accepted_sessions": sum(s["status"] == "candidate_session_passed" for s in session_results),
             "quadrants": quadrants,
             "rmse_delta_px": math.sqrt(sum(x*x for x in errors)/len(errors)) if errors else None,
             "max_delta_error_px": max(errors) if errors else None}
    if stats["rmse_delta_px"] is not None and stats["rmse_delta_px"] > max_rmse_px:
        reasons.append("pooled_rmse_exceeds_limit")
    report = {"schema": SCHEMA+"-report",
              "created_utc": datetime.now(timezone.utc).isoformat(),
              "status": "candidate_multisession_repeatability_passed" if not reasons else "blocked",
              "reasons": reasons, "manifest_sha256": sha256_file(manifest_path),
              "operator_note": m["operator_note"],
              "sessions": session_results, "metrics": stats,
              "criteria": {"min_sessions": min_sessions,
                           "min_trials_per_session": min_trials_per_session,
                           "min_quadrants": min_quadrants,
                           "max_rmse_px": max_rmse_px},
              "session_independence": "operator_attested_not_process_verified",
              "visual_object_identity": "dynamic_correspondence_candidate_only",
              "validated_for_selection": False,
              "selection_dispatch": "not_dispatched", "memory_write": False,
              "note": "Different PIDs/boot labels and executable hashes do not independently prove process restart, Object ID identity, or camera stability between sampled images."}
    outdir = Path(output_dir)
    if outdir.exists() and any(outdir.iterdir()):
        raise FileExistsError("output_directory_must_be_empty")
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir/"multisession_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--min-sessions", type=int, default=3)
    parser.add_argument("--min-trials-per-session", type=int, default=2)
    parser.add_argument("--min-quadrants", type=int, default=4)
    parser.add_argument("--max-rmse-px", type=float, default=12.)
    a = parser.parse_args(argv)
    result = audit(a.manifest, a.output_dir,
                   min_sessions=a.min_sessions,
                   min_trials_per_session=a.min_trials_per_session,
                   min_quadrants=a.min_quadrants,
                   max_rmse_px=a.max_rmse_px)
    print(json.dumps({"status": result["status"],
                      "reasons": result["reasons"],
                      "metrics": result["metrics"],
                      "validated_for_selection": False}, indent=2))
    return 0 if result["status"] == "candidate_multisession_repeatability_passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
