"""v3.3.15 adapter: guarded v3.3.12 captures -> offline session manifest.

Only reads pre-existing files. Never asserts visual Object ID identity.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .calibration_camera_v3_3_14 import sha256_file
from .calibration_session_v3_3_15 import SCHEMA

TRAIN_IDS = (2187, 2188, 2189, 2513, 2515, 2517)


def _resolve(path, root):
    p = Path(path)
    return (p if p.is_absolute() else root / p).resolve()


def build_manifest(*, reference, training, holdouts, session, note, minimum=10):
    """Prepare manifest, blocking invalid captures instead of dropping them."""
    if not session.strip() or not note.strip():
        raise ValueError("session_and_note_required")
    if len(training) != 6:
        raise ValueError("exactly_six_frozen_training_files_required")
    if len(holdouts) > minimum:
        raise ValueError("unexpected_holdout_count")
    reference = Path(reference).resolve()
    if not reference.is_file():
        raise ValueError("reference_missing")
    reference_hash = sha256_file(reference)
    entries, errors, seen = [], [], set()
    pid_set = set()
    for role, paths in (("train", training), ("holdout", holdouts)):
        for position, source in enumerate(paths):
            source = Path(source).resolve()
            report = json.loads(source.read_text(encoding="utf-8-sig"))
            rid = report.get("object_id")
            reasons = []
            if report.get("schema") != "hd-guarded-capture-v3.3.12" or report.get("status") != "candidate_capture_accepted":
                reasons.append("capture_not_accepted")
            if report.get("camera_consistency") != "sampled_frames_only" or report.get("anchor_usable") is not True or report.get("cursor_stable") is not True:
                reasons.append("camera_or_anchor_gate_invalid")
            if report.get("selection_dispatch") != "not_dispatched" or report.get("memory_write") is not False or report.get("validated_for_selection") is not False:
                reasons.append("unsafe_capture")
            if role == "train" and rid != TRAIN_IDS[position]:
                reasons.append("training_order_or_id_mismatch")
            if type(rid) is not int or rid in seen:
                reasons.append("duplicate_or_invalid_object_id")
            seen.add(rid)
            anchor = report.get("anchor")
            if not isinstance(anchor, dict) or anchor.get("schema") != "hd-synchronized-anchor-v3.3.2" or anchor.get("object_id") != rid or anchor.get("pid") != report.get("pid") or anchor.get("usable") is not True:
                reasons.append("anchor_schema_or_identity_mismatch")
            if type(report.get("pid")) is not int or report.get("pid") <= 0:
                reasons.append("invalid_pid")
            pid_set.add(report.get("pid"))
            for check in ("reference_to_before", "reference_to_after", "before_to_after"):
                state = (report.get("camera_checks") or {}).get(check) or {}
                if state.get("schema") != "hd-camera-robust-v3.3.11" or state.get("status") != "candidate_camera_static" or state.get("selection_dispatch") != "not_dispatched" or state.get("memory_write") is not False:
                    reasons.append("camera_check_invalid:" + check)
            ref_path = _resolve(report.get("reference_image", ""), source.parent.parent if source.parent.name == "json" else source.parent)
            # Most legacy captures store 'json/foo.bmp' while the JSON itself lives in ./json.
            # Resolve relative to working project root first, then JSON directory.
            if not ref_path.is_file() or ref_path != reference:
                alternatives = [_resolve(report.get("reference_image", ""), source.parent),
                                _resolve(report.get("reference_image", ""), Path.cwd())]
                if reference not in alternatives:
                    reasons.append("capture_reference_mismatch")
            image_info = report.get("before_image")
            image_name = image_info.get("path") if isinstance(image_info, dict) else None
            image_candidates = []
            if image_name:
                image_candidates = [_resolve(image_name, Path.cwd()),
                                    _resolve(image_name, source.parent),
                                    _resolve(image_name, source.parent.parent)]
            image_path = next((candidate for candidate in image_candidates if candidate.is_file()), None)
            if image_path is None:
                reasons.append("before_image_missing")
            else:
                if image_path == reference or image_path == source:
                    reasons.append("source_image_overlap")
            if reasons:
                errors.append({"file":str(source), "object_id":rid, "reasons":reasons})
            else:
                entries.append({"role":role, "anchor":anchor,
                                "camera_image":str(image_path),
                                "camera_sha256":sha256_file(image_path),
                                "guarded_source_file":str(source),
                                "guarded_source_sha256":sha256_file(source)})
    if len(pid_set) != 1:
        errors.append({"reasons":["mixed_pids"]})
    manifest = {"schema":SCHEMA, "session":session, "note":note,
                "reference_image":str(reference), "reference_sha256":reference_hash,
                "anchors":entries}
    return {"status":"ready_for_evaluation" if not errors and len(holdouts)==minimum else "blocked_or_incomplete",
            "manifest":manifest, "errors":errors, "training_count":len(training),
            "holdout_count":len(holdouts), "required_holdouts":minimum,
            "validated_for_selection":False,"selection_dispatch":"not_dispatched",
            "memory_write":False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--train", nargs="+", required=True)
    parser.add_argument("--holdout", nargs="*", default=[])
    parser.add_argument("--session", required=True)
    parser.add_argument("--note", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    result = build_manifest(reference=args.reference, training=args.train,
                            holdouts=args.holdout, session=args.session, note=args.note)
    output = Path(args.output)
    if output.exists():
        raise FileExistsError("output_exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({key:result[key] for key in ("status","errors","training_count","holdout_count")},
                     indent=2, ensure_ascii=False))
    # Wrapper contains manifest plus diagnostic metadata. Use .manifest only
    # with calibration_session_v3_3_15 after all 10 holdouts are accepted.
    return 0 if result["status"] == "ready_for_evaluation" else 2


if __name__ == "__main__":
    raise SystemExit(main())
