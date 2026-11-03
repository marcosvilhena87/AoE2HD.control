"""v3.10 camera translation experiment; read-only, never dispatches game input.

Uses v3.9's fitted linear transform and two independent observations after one
operator-reported camera shift: one to estimate translation, one held out.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from .catalog import mapping_dir
from .movement_v3_4 import _identity_position
from .object_api import HDObjectAPI, WindowsProcessReader
from .position_cursor_probe_v3_2 import read_cursor_coordinates
from .world_client_v3_9 import _selection_id_for_any, _xy, predict

SCHEMA = "hd-camera-translation-v3.10"
BASE_SCHEMA = "hd-world-client-affine-v3.9"


def validate_base(base):
    """Reject unfit, failed, or incomplete v3.9 calibration."""
    if base.get("schema") != BASE_SCHEMA or type(base.get("pid")) is not int:
        raise ValueError("Invalid v3.9 baseline")
    samples = base.get("samples")
    cal = base.get("calibration")
    if not isinstance(samples, list) or len(samples) != 4 or not isinstance(cal, dict):
        raise ValueError("Baseline must contain 4 points and fitted calibration")
    if (cal.get("status") != "candidate_fit_passed_heldout" or
        cal.get("validation_within_threshold") is not True):
        raise ValueError("Baseline independent validation must have passed")
    coefficients = cal.get("coefficients_candidate")
    if (not isinstance(coefficients, list) or len(coefficients) != 2 or
        any(not isinstance(v, list) or len(v) != 3 or
            any(type(c) not in (int,float) or not math.isfinite(c) for c in v)
            for v in coefficients)):
        raise ValueError("Invalid affine coefficients")
    ids = [sample.get("object_id") for sample in samples]
    if any(type(i) is not int for i in ids) or len(set(ids)) != 4:
        raise ValueError("Invalid distinct baseline IDs")
    for sample in samples:
        _xy(sample, "world_candidate")
        _xy(sample, "client")
        identity = sample.get("identity") or {}
        if identity.get("address") is None or identity.get("owner_address") is None:
            raise ValueError("Missing baseline identity")
    return coefficients


def compare_camera(base, anchor, check, *, max_error_px=20.0,
                   world_stability=0.03, minimum_shift_px=3.0):
    """Translation from anchor, validation on check; no calibration re-fit."""
    coeffs = validate_base(base)
    for name,value,zero_ok in (("max_error_px",max_error_px,False),
                               ("world_stability",world_stability,True),
                               ("minimum_shift_px",minimum_shift_px,True)):
        if type(value) not in (float,int) or not math.isfinite(value) or (value < 0 if zero_ok else value <= 0):
            raise ValueError("Invalid " + name)
    if anchor["object_id"] == check["object_id"]:
        raise ValueError("Anchor and check must be different objects")
    by_id = {s["object_id"]:s for s in base["samples"]}
    for sample in (anchor,check):
        oid = sample["object_id"]
        if oid not in by_id or sample.get("identity") != by_id[oid]["identity"]:
            raise ValueError("Unrecognized or changed baseline object identity")
        current = _xy(sample,"world_candidate")
        previous = _xy(by_id[oid],"world_candidate")
        if math.dist(current,previous) > world_stability:
            raise ValueError(f"Object {oid} moved; invalid camera experiment")
    # Use original projected world coordinates, plus anchor observed translation.
    anchor_expected = predict(coeffs,_xy(anchor,"world_candidate"))
    check_expected = predict(coeffs,_xy(check,"world_candidate"))
    anchor_client = _xy(anchor,"client")
    check_client = _xy(check,"client")
    shift = {"x":anchor_client[0]-anchor_expected["x"],
             "y":anchor_client[1]-anchor_expected["y"]}
    predicted = {"x":check_expected["x"]+shift["x"],
                 "y":check_expected["y"]+shift["y"]}
    error = math.hypot(predicted["x"]-check_client[0],
                       predicted["y"]-check_client[1])
    magnitude = math.hypot(shift["x"],shift["y"])
    return {"schema": SCHEMA,"translation_candidate_px": shift,
            "translation_magnitude_px":magnitude,
            "check_prediction_client":predicted,
            "check_observed_client":{"x":check_client[0],"y":check_client[1]},
            "independent_error_px":error,"validation_threshold_px":float(max_error_px),
            "validation_within_threshold":error <= max_error_px,
            "camera_shift_observed_candidate":magnitude >= minimum_shift_px,
            "status":("candidate_translation_passed_heldout" if
                      error <= max_error_px and magnitude >= minimum_shift_px else
                      "candidate_no_measurable_shift" if magnitude < minimum_shift_px else
                      "candidate_translation_failed_heldout"),
            "camera_position_verified":False,
            "world_to_client_validated":False,
            "command_dispatched":False,"memory_write":False,
            "note":"Camera change is operator-reported. Anchor fit is not validation; second object is held out. No command capability."}


def append_observation(report, base, *, role, object_id, world_candidate,
                       client, identity, pid, base_digest):
    """Capture one baseline-known object per role, preserving previous observations."""
    validate_base(base)
    if role not in ("anchor","check") or type(pid) is not int or pid != base["pid"]:
        raise ValueError("Wrong role or changed PID")
    baseline = {s["object_id"]:s for s in base["samples"]}
    if object_id not in baseline or identity != baseline[object_id]["identity"]:
        raise ValueError("Object must match v3.9 reference and identity")
    if math.dist(_xy({"world_candidate":world_candidate},"world_candidate"),
                 _xy(baseline[object_id],"world_candidate")) > 0.03:
        raise ValueError("Object moved since calibration")
    _xy({"client":client},"client")
    if report is None:
        report = {"schema":SCHEMA,"pid":pid,"base_sha256":base_digest,
                  "observations":[],"camera_state":"operator_reported_changed_then_fixed",
                  "memory_write":False,"command_dispatched":False}
    if (report.get("schema") != SCHEMA or report.get("pid") != pid or
        report.get("base_sha256") != base_digest):
        raise ValueError("Baseline/PID changed. Use a new output")
    observations = report["observations"]
    if len(observations) != (0 if role == "anchor" else 1) or (
        role == "check" and observations[0]["role"] != "anchor"):
        raise ValueError("Capture anchor first, then check exactly once")
    if any(item["object_id"] == object_id for item in observations):
        raise ValueError("Check must be an independent Object ID")
    updated = dict(report)
    updated["observations"] = list(observations) + [
        {"role":role,"object_id":object_id,"world_candidate":world_candidate,
         "client":client,"identity":identity,
         "timestamp_utc":datetime.now(timezone.utc).isoformat(),
         "point_description":"operator_pointed_ground_feet"}]
    return updated


def capture(*, base_path, output, role, pid=None, delay=8):
    if type(delay) is not int or not 0 <= delay <= 30:
        raise ValueError("Invalid delay")
    raw = base_path.read_bytes()
    base = json.loads(raw.decode("utf-8-sig"))
    validate_base(base)
    digest = hashlib.sha256(raw).hexdigest()
    if pid is None:
        pid = int(subprocess.check_output(
            ["powershell","-NoProfile","-Command","(Get-Process 'AoK HD').Id"],
            text=True).strip())
    if pid != base["pid"]:
        raise ValueError("Game PID differs from baseline; recalibrate v3.9")
    report = json.loads(output.read_text(encoding="utf-8")) if output.exists() else None
    if report is not None and (report.get("base_sha256") != digest or report.get("pid") != pid):
        raise ValueError("Baseline modified or PID changed; choose new output")
    if role == "check" and (report is None or len(report.get("observations",[])) != 1):
        raise ValueError("Capture anchor first")
    if role == "anchor" and report is not None:
        raise ValueError("Anchor already captured; choose a new output")
    print("Camera alterada em relacao a v3.9; mantenha-a IMOVEL durante ambas capturas.")
    print("Selecione um aldeao original parado; a unidade check deve ser DIFERENTE da anchor.")
    print(f"Posicione cursor nos PES da unidade e NAO clique. Captura em {delay} segundos.",flush=True)
    time.sleep(delay)
    with WindowsProcessReader(pid) as reader:
        api = HDObjectAPI(reader,mapping_dir(),allow_candidates=True)
        selected = _selection_id_for_any(api)
        oid = selected["selected_objects"][0]["object_id"]
        if oid not in {s["object_id"] for s in base["samples"]}:
            raise ValueError("Selected unit not included in v3.9 calibration")
        obj = api.get_object_by_id(oid)
        first = _identity_position(api,oid,obj)
        cursor = read_cursor_coordinates(pid)
        second = _identity_position(api,oid,obj)
        _selection_id_for_any(api,expected_id=oid)
        if not cursor["game_foreground"] or not cursor["client"]:
            raise ValueError("Game not foreground")
        if math.hypot(second["candidate_world_x"]-first["candidate_world_x"],
                      second["candidate_world_y"]-first["candidate_world_y"]) > 0.03:
            raise ValueError("Object moving during capture")
        identity = {"address":obj.address,"owner_address":obj.owner_address,
                    "class_id":obj.class_id,"genie_type_id":obj.genie_type_id}
        pos = {"x":first["candidate_world_x"],"y":first["candidate_world_y"]}
        result = append_observation(report,base,role=role,object_id=oid,
                                    world_candidate=pos,client=cursor["client"],
                                    identity=identity,pid=pid,base_digest=digest)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(result["observations"][-1],indent=2,ensure_ascii=False))
    print("Relatorio:",output)


def evaluate(*, base_path, output, threshold_px=20):
    raw = base_path.read_bytes()
    base = json.loads(raw.decode("utf-8-sig"))
    report = json.loads(output.read_text(encoding="utf-8"))
    if report.get("base_sha256") != hashlib.sha256(raw).hexdigest():
        raise ValueError("Baseline changed since capture")
    if len(report.get("observations",[])) != 2:
        raise ValueError("Need one anchor and one independent check")
    anchor,check = report["observations"]
    if (anchor["role"],check["role"]) != ("anchor","check"):
        raise ValueError("Invalid stage sequence")
    result=compare_camera(base,anchor,check,max_error_px=threshold_px)
    report["comparison"]=result
    output.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(result,indent=2,ensure_ascii=False))


def main(argv=None):
    p=argparse.ArgumentParser(description="v3.10 camera translation test (read-only)")
    p.add_argument("action",choices=("anchor","check","evaluate"))
    p.add_argument("--base",type=Path,default=Path("json/world_client_v3_9.json"))
    p.add_argument("--output",type=Path,default=Path("json/camera_translation_v3_10.json"))
    p.add_argument("--threshold-px",type=float,default=20.0)
    p.add_argument("--pid",type=int)
    a=p.parse_args(argv)
    if a.action=="evaluate":
        evaluate(base_path=a.base,output=a.output,threshold_px=a.threshold_px)
    else:
        capture(base_path=a.base,output=a.output,role=a.action,pid=a.pid)


if __name__=="__main__":
    main()
