"""v3.8: read-only candidate world-space pair tracking across camera changes.

No mouse events, memory writes, command dispatch or validated world coordinates.
Three operator-confirmed stages, eight-second return-to-game delay each.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from .catalog import mapping_dir
from .movement_v3_4 import _identity_position, _selection_id
from .object_api import HDObjectAPI, ObjectAPIError, WindowsProcessReader

SCHEMA = "hd-global-pair-probe-v3.8"
STAGES = {"1": "both_visible", "2": "reference_offscreen", "3": "both_visible_again"}
IDENTITY = ("address", "owner_address", "genie_type_id", "class_id")


def _valid_id(value):
    return type(value) is int and 0 <= value <= 1_000_000


def pair_geometry(a, b):
    """Candidate X/Y deltas only; angle is mathematical, NOT a game heading."""
    x1, y1 = a["candidate_world_x"], a["candidate_world_y"]
    x2, y2 = b["candidate_world_x"], b["candidate_world_y"]
    if any(type(n) not in (int, float) or not math.isfinite(n)
           for n in (x1, y1, x2, y2)):
        raise ValueError("Nonfinite or invalid candidate coordinates")
    dx, dy = float(x2 - x1), float(y2 - y1)
    distance = math.hypot(dx, dy)
    return {"dx_candidate": dx, "dy_candidate": dy,
            "distance_candidate": distance,
            "unit_vector_candidate": ({"x": dx / distance, "y": dy / distance}
                                      if distance > 0 else None),
            "angle_math_degrees_candidate": (math.degrees(math.atan2(dy, dx))
                                             if distance > 0 else None),
            "game_heading_validated": False}


def _signature(obj):
    return {key: getattr(obj, key) for key in IDENTITY}


def _position(api, oid, obj):
    position = _identity_position(api, oid, obj)
    return {"candidate_world_x": position["candidate_world_x"],
            "candidate_world_y": position["candidate_world_y"],
            "finite": position["finite"]}


def sample_pair(api, a_id, b_id, *, expected=None, position_reader=None):
    """Identity + A/B/A reread; a moved-during-read flag prevents false precision."""
    if not getattr(api, "allow_candidates", False):
        raise ObjectAPIError("Candidate opt-in required")
    if not _valid_id(a_id) or not _valid_id(b_id) or a_id == b_id:
        raise ValueError("Two distinct Object IDs required")
    _selection_id(api, a_id)  # A selected, B need not be visible or selected
    a_obj = api.get_object_by_id(a_id)
    b_obj = api.get_object_by_id(b_id)
    if a_obj is None or b_obj is None or a_obj.address == b_obj.address:
        raise ObjectAPIError("One or both objects unavailable")
    sa, sb = _signature(a_obj), _signature(b_obj)
    if sa["owner_address"] is None or sa["owner_address"] != sb["owner_address"]:
        raise ObjectAPIError("Candidate ownership inconsistent")
    if expected is not None and (expected.get("a") != sa or expected.get("b") != sb):
        raise ObjectAPIError("Object identity differs from stage 1")
    read = _position if position_reader is None else position_reader
    a = read(api, a_id, a_obj)
    b = read(api, b_id, b_obj)
    a_again = read(api, a_id, a_obj)
    # Reconfirm identities and selection after the paired capture.
    for oid, previous in ((a_id, sa), (b_id, sb)):
        obj = api.get_object_by_id(oid)
        if obj is None or _signature(obj) != previous:
            raise ObjectAPIError("Object identity changed during pair snapshot")
    _selection_id(api, a_id)
    internal_drift = math.hypot(
        a_again["candidate_world_x"] - a["candidate_world_x"],
        a_again["candidate_world_y"] - a["candidate_world_y"])
    return {"a": a, "b": b, "geometry": pair_geometry(a, b),
            "a_read_drift_candidate": internal_drift,
            "atomic_snapshot": False,
            "identity": {"a": sa, "b": sb},
            "consistent_within_read": internal_drift <= 0.03}


def stage_update(report, *, stage, pid, a_id, b_id, snapshot):
    """Pure stage state machine; no side effects, no game access."""
    if stage not in STAGES:
        raise ValueError("stage must be 1, 2 or 3")
    if type(pid) is not int or pid <= 0 or not _valid_id(a_id) or not _valid_id(b_id):
        raise ValueError("Invalid pid or object IDs")
    if stage == "1":
        report = {"schema": SCHEMA, "pid": pid, "a_id": a_id, "b_id": b_id,
                  "identity": snapshot["identity"], "samples": [],
                  "candidate_offsets": ["Object+0x3C", "Object+0x40"],
                  "camera_position_verified": False, "offscreen_status": "operator_reported",
                  "world_coordinates_validated": False, "memory_write": False,
                  "command_dispatched": False}
    elif (report is None or report.get("schema") != SCHEMA or
          report.get("pid") != pid or report.get("a_id") != a_id or
          report.get("b_id") != b_id or
          report.get("identity") != snapshot["identity"] or
          [s["stage"] for s in report.get("samples", [])] !=
          [STAGES[str(i)] for i in range(1, int(stage))]):
        raise ValueError("Previous stages, PID or identity inconsistent")
    if not snapshot["consistent_within_read"]:
        raise ValueError("A moved during A/B/A snapshot; recapture stage")
    if len(report["samples"]) != int(stage) - 1:
        raise ValueError("Unexpected sample count")
    updated = dict(report)
    updated["samples"] = list(report["samples"]) + [
        {"stage": STAGES[stage], "timestamp_utc": datetime.now(timezone.utc).isoformat(),
         **{k: snapshot[k] for k in ("a", "b", "geometry",
                                     "a_read_drift_candidate", "consistent_within_read")}}]
    if stage == "3":
        first = updated["samples"][0]
        comparisons = []
        for s in updated["samples"][1:]:
            def drift(name):
                return math.hypot(
                    s[name]["candidate_world_x"] - first[name]["candidate_world_x"],
                    s[name]["candidate_world_y"] - first[name]["candidate_world_y"])
            comparisons.append({
                "stage": s["stage"], "a_drift_candidate": drift("a"),
                "b_drift_candidate": drift("b"),
                "pair_distance_change_candidate":
                    s["geometry"]["distance_candidate"] - first["geometry"]["distance_candidate"]})
        updated["comparisons"] = comparisons
        updated["interpretation"] = "camera_independence_candidate_only"
    return updated


def run_stage(stage, *, a_id, b_id, output, pid=None, delay_seconds=8):
    """Operator must set camera scene manually; do not infer onscreen visibility."""
    if stage not in STAGES:
        raise ValueError("Invalid stage")
    if not _valid_id(a_id) or not _valid_id(b_id) or a_id == b_id:
        raise ValueError("Two distinct IDs required")
    if type(delay_seconds) is not int or not 0 <= delay_seconds <= 30:
        raise ValueError("Invalid delay")
    if pid is None:
        pid = int(subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "(Get-Process 'AoK HD').Id"],
            text=True).strip())
    report = None
    if stage != "1":
        if not output.exists():
            raise ValueError("Run stage 1 first")
        report = json.loads(output.read_text(encoding="utf-8"))
        if report.get("pid") != pid or report.get("a_id") != a_id or report.get("b_id") != b_id:
            raise ValueError("PID/IDs differ from stage 1")
    print(f"Etapa {stage}: {STAGES[stage]}. A selecionado; B nao selecionado.")
    print("Volte ao jogo. Captura em 8 segundos." if delay_seconds == 8
          else f"Volte ao jogo. Captura em {delay_seconds} segundos.")
    time.sleep(delay_seconds)
    with WindowsProcessReader(pid) as reader:
        api = HDObjectAPI(reader, mapping_dir(), allow_candidates=True)
        snap = sample_pair(api, a_id, b_id,
                           expected=report["identity"] if report else None)
    result = stage_update(report, stage=stage, pid=pid, a_id=a_id, b_id=b_id,
                          snapshot=snap)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False),
                      encoding="utf-8")
    print(json.dumps(result["samples"][-1], indent=2, ensure_ascii=False))
    if stage == "3":
        print("Comparacoes:", json.dumps(result["comparisons"], indent=2))
    print("Relatorio:", output)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="v3.8: leitura de dois aldeoes independente da camera")
    parser.add_argument("stage", choices=STAGES)
    parser.add_argument("--a", type=int, required=True, help="Object ID de A (selecionado)")
    parser.add_argument("--b", type=int, required=True, help="Object ID de B (referencia)")
    parser.add_argument("--pid", type=int, default=None)
    parser.add_argument("--output", type=Path, default=Path("json/global_pair_v3_8.json"))
    args = parser.parse_args(argv)
    run_stage(args.stage, a_id=args.a, b_id=args.b,
              pid=args.pid, output=args.output)


if __name__ == "__main__":
    main()
