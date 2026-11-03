"""v3.9 experimental world-candidate -> client-pixel affine calibration.

Read-only. Four distinct stationary reference objects: 3 noncollinear to fit,
4th held out for validation. Pixels are manually pointed at unit ground feet.
Camera stability is OPERATOR-REPORTED, never asserted from game memory.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import time
from pathlib import Path
from datetime import datetime, timezone

from .catalog import mapping_dir
from .movement_v3_4 import _identity_position, _selection_id
from .object_api import HDObjectAPI, WindowsProcessReader
from .position_cursor_probe_v3_2 import read_cursor_coordinates

SCHEMA = "hd-world-client-affine-v3.9"


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _xy(record, prefix):
    xy = record[prefix]
    if not isinstance(xy, dict) or not all(_finite(xy.get(k)) for k in ("x", "y")):
        raise ValueError("Missing/invalid coordinate pair")
    return float(xy["x"]), float(xy["y"])


def _solve3(matrix, values):
    """Gaussian elimination with relative pivot guard: pure Python, no numpy."""
    augmented = [list(map(float, row)) + [float(v)]
                 for row, v in zip(matrix, values)]
    scale = max(abs(v) for row in matrix for v in row)
    for col in range(3):
        pivot = max(range(col, 3), key=lambda i: abs(augmented[i][col]))
        if scale == 0 or abs(augmented[pivot][col]) < 1e-9 * scale:
            raise ValueError("Calibration points are collinear/degenerate")
        augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        div = augmented[col][col]
        for j in range(col, 4):
            augmented[col][j] /= div
        for row in range(3):
            if row == col:
                continue
            factor = augmented[row][col]
            for j in range(col, 4):
                augmented[row][j] -= factor * augmented[col][j]
    return [augmented[i][3] for i in range(3)]


def predict(coefficients, world):
    x, y = world
    if len(coefficients) != 2 or any(len(v) != 3 for v in coefficients):
        raise ValueError("Expected two affine coefficient triplets")
    return {"x": sum(c * u for c, u in zip(coefficients[0], (x, y, 1.0))),
            "y": sum(c * u for c, u in zip(coefficients[1], (x, y, 1.0)))}


def calibrate(samples, *, max_validation_error_px=20.0):
    """3 points fit + independent fourth validation; no automatic command use."""
    if len(samples) != 4:
        raise ValueError("Exactly 4 samples required: 3 fit + 1 validation")
    if not _finite(max_validation_error_px) or max_validation_error_px <= 0:
        raise ValueError("Invalid pixel tolerance")
    ids = [s["object_id"] for s in samples]
    if any(type(i) is not int or not 0 <= i <= 1_000_000 for i in ids) or len(set(ids)) != 4:
        raise ValueError("Four distinct valid Object IDs required")
    world = [_xy(s, "world_candidate") for s in samples]
    client = [_xy(s, "client") for s in samples]
    # Normalize world coordinates to reduce conditioning error.
    cx = sum(x for x, _ in world[:3]) / 3
    cy = sum(y for _, y in world[:3]) / 3
    span = max(max(abs(x - cx), abs(y - cy)) for x, y in world[:3])
    if span <= 1e-8:
        raise ValueError("Calibration points collapsed")
    M = [[(x-cx)/span, (y-cy)/span, 1.0] for x,y in world[:3]]
    norm_coeffs = [_solve3(M, [p[k] for p in client[:3]]) for k in (0,1)]
    coefficients = [
        [co[0]/span,co[1]/span,co[2]-(co[0]*cx+co[1]*cy)/span]
        for co in norm_coeffs]
    # Reject near-collinearity relative to the calibration's world-space span.
    area = abs((M[1][0]-M[0][0])*(M[2][1]-M[0][1]) -
               (M[1][1]-M[0][1])*(M[2][0]-M[0][0]))
    if area < 0.02:
        raise ValueError("Reference triangle too narrow; spread objects in two axes")
    predicted = [predict(coefficients, p) for p in world]
    errors = [math.hypot(p["x"]-c[0],p["y"]-c[1])
              for p,c in zip(predicted,client)]
    heldout = errors[3]
    return {"schema": SCHEMA, "coefficients_candidate": coefficients,
            "training_error_px": errors[:3],
            "validation_error_px": heldout,
            "validation_threshold_px": max_validation_error_px,
            "validation_within_threshold": heldout <= max_validation_error_px,
            "validation_point_id": ids[3],
            "predictions": predicted,
            "reference_ids": ids[:3],
            "camera_stability": "operator_reported_only",
            "world_coordinates_validated": False,
            "world_to_client_validated": False,
            "command_dispatched": False,
            "memory_write": False,
            "status": ("candidate_fit_passed_heldout" if heldout <= max_validation_error_px
                       else "candidate_fit_failed_heldout"),
            "note": "Four manual foot-point pixels in one camera view; fit is not evidence of native command or cross-camera applicability."}


def append_capture(report, *, object_id, position, client, identity, pid):
    """Pure persistence transition; never replace an existing calibration silently."""
    if type(pid) is not int or pid <= 0:
        raise ValueError("Invalid PID")
    if type(object_id) is not int or not 0 <= object_id <= 1_000_000:
        raise ValueError("Invalid Object ID")
    if report is None:
        report = {"schema": SCHEMA,"pid":pid,"samples":[],
                  "camera_stability":"operator_reported_only",
                  "command_dispatched":False,"memory_write":False}
    if report["schema"] != SCHEMA or report["pid"] != pid:
        raise ValueError("Wrong schema or changed PID; begin new calibration")
    if len(report["samples"]) >= 4:
        raise ValueError("Already captured four points; use fit")
    if object_id in [s["object_id"] for s in report["samples"]]:
        raise ValueError("Use four different Object IDs")
    _xy({"world_candidate":position}, "world_candidate")
    _xy({"client":client}, "client")
    if identity.get("address") is None or identity.get("owner_address") is None:
        raise ValueError("Invalid object identity")
    if report["samples"] and report["samples"][0]["identity"]["owner_address"] != identity["owner_address"]:
        raise ValueError("Different candidate owner")
    next_report = dict(report)
    next_report["samples"] = list(report["samples"]) + [
        {"object_id":object_id,"world_candidate":position,"client":client,
         "identity":identity,"timestamp_utc":datetime.now(timezone.utc).isoformat(),
         "point_description":"operator_pointed_ground_feet"}]
    return next_report


def capture(output, *, pid=None, delay=8):
    """Interactive manual landmark; Windows cursor observation, no clicks."""
    if pid is None:
        pid = int(subprocess.check_output(
            ["powershell","-NoProfile","-Command","(Get-Process 'AoK HD').Id"],
            text=True).strip())
    report = json.loads(output.read_text(encoding="utf-8")) if output.exists() else None
    if report is not None and (report.get("schema") != SCHEMA or report.get("pid") != pid):
        raise ValueError("Existing report has incompatible schema/PID; use new output")
    count = len(report["samples"]) if report else 0
    if count >= 4:
        raise ValueError("Four points already captured")
    print(f"Referência {count+1}/4: selecione uma unidade parada distinta.")
    print("Mantenha a CAMERA IMOVEL em todas as capturas.")
    print("Posicione o mouse NO PE da unidade (ponto de contato com solo); NAO CLIQUE.")
    print(f"Retorne ao jogo. Captura em {delay} segundos.", flush=True)
    time.sleep(delay)
    with WindowsProcessReader(pid) as reader:
        api = HDObjectAPI(reader, mapping_dir(), allow_candidates=True)
        sel = _selection_id_for_any(api)
        oid = sel["selected_objects"][0]["object_id"]
        obj = api.get_object_by_id(oid)
        first = _identity_position(api,oid,obj)
        cursor = read_cursor_coordinates(pid)
        second = _identity_position(api,oid,obj)
        if not cursor["game_foreground"] or cursor["client"] is None:
            raise ValueError("Game not foreground at capture")
        if math.hypot(first["candidate_world_x"]-second["candidate_world_x"],
                      first["candidate_world_y"]-second["candidate_world_y"]) > 0.03:
            raise ValueError("Unit moved during capture")
        _selection_id_for_any(api, expected_id=oid)
        signature = {"address":obj.address,"owner_address":obj.owner_address,
                     "class_id":obj.class_id,"genie_type_id":obj.genie_type_id}
        sample = {"x":first["candidate_world_x"],"y":first["candidate_world_y"]}
        new = append_capture(report, object_id=oid, position=sample,
                             client=cursor["client"],identity=signature,pid=pid)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(new,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(new["samples"][-1],indent=2,ensure_ascii=False))
    print("Salvo:",output)


def _selection_id_for_any(api, expected_id=None):
    from .selected_objects_v2_7 import inspect_selection
    sel = inspect_selection(api)
    objs = sel.get("selected_objects",[])
    if sel.get("consistency") != "stable_with_candidate_count" or len(objs) != 1:
        raise ValueError("Exactly one stable selected object required")
    if expected_id is not None and objs[0]["object_id"] != expected_id:
        raise ValueError("Selection changed during capture")
    return sel


def main(argv=None):
    p=argparse.ArgumentParser(description="v3.9 camera-fixed affine calibration; read-only")
    p.add_argument("action",choices=("capture","fit"))
    p.add_argument("--output",type=Path,default=Path("json/world_client_v3_9.json"))
    p.add_argument("--pid",type=int)
    p.add_argument("--threshold-px",type=float,default=20.0)
    a=p.parse_args(argv)
    if a.action=="capture":
        capture(a.output,pid=a.pid)
    else:
        data=json.loads(a.output.read_text(encoding="utf-8"))
        result=calibrate(data["samples"],max_validation_error_px=a.threshold_px)
        data["calibration"]=result
        a.output.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
        print(json.dumps(result,indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
