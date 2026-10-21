"""Validação v1.3: observação temporal dos tipos 109/618/619/620.

Os offsets posicionais 0x3C e 0x40 são candidatos da evidência v9.13
e só podem ser lidos com opt-in. Sem escrita, sem enumeração global.
"""
from __future__ import annotations
import math
import time
from dataclasses import asdict
from .object_api import HDObjectAPI, ObjectAPIError
from .object_validation_v1_2 import _players

TARGET_TYPES = frozenset((109, 618, 619, 620))


def collect(api: HDObjectAPI, start_id: int, end_id: int, *, positions: bool = False) -> dict:
    if not api.allow_candidates:
        raise ObjectAPIError("v1.3 requer allow_candidates=True")
    if start_id < 0 or end_id < start_id or end_id > 1_000_000 or end_id-start_id+1 > 512:
        raise ValueError("Faixa invalida: máximo 512 IDs")
    local_slot, player_by_ptr = _players(api)
    objects, errors = [], []
    for oid in range(start_id, end_id+1):
        try:
            obj = api.get_object_by_id(oid)
            if obj is None or obj.class_id != 3 or obj.genie_type_id not in TARGET_TYPES:
                continue
            pos = None
            if positions:
                # Posição deliberadamente experimental; offsets não promovidos.
                x = api._read(obj.address + 0x3C, "f")
                y = api._read(obj.address + 0x40, "f")
                if not math.isfinite(x) or not math.isfinite(y):
                    raise ObjectAPIError("Posicao nao finita")
                pos = [round(x, 5), round(y, 5)]
            objects.append({"object_id": oid, "object_address": obj.address,
                            "class_id": obj.class_id, "genie_type_id": obj.genie_type_id,
                            "owner_address": obj.owner_address,
                            "owner_slot": player_by_ptr.get(obj.owner_address),
                            "is_local": player_by_ptr.get(obj.owner_address) == local_slot,
                            "candidate_position": pos})
        except (ObjectAPIError, OSError, ValueError) as exc:
            if len(errors) < 25:
                errors.append({"object_id": oid, "error": str(exc)})
    by_id = {o["object_id"]: o for o in objects}
    for obj in objects:
        peers = [p for p in objects if p["object_id"] != obj["object_id"]
                 and p["owner_slot"] is not None and p["owner_slot"] == obj["owner_slot"]]
        obj["same_owner_ids"] = [p["object_id"] for p in peers]
        if obj["candidate_position"] is not None:
            obj["distances"] = {
                str(p["object_id"]): round(math.dist(obj["candidate_position"], p["candidate_position"]), 4)
                for p in peers if p["candidate_position"] is not None
            }
        else:
            obj["distances"] = None
    return {"local_slot": local_slot, "players": {hex(k): v for k, v in player_by_ptr.items()},
            "objects": objects, "errors": errors, "range": [start_id, end_id],
            "positions_are_candidates": positions}


def capture_series(api: HDObjectAPI, start_id: int, end_id: int, *,
                   samples: int = 3, interval: float = 1.0, positions: bool = False,
                   sleep=time.sleep) -> dict:
    if samples < 1 or samples > 20 or not 0 <= interval <= 30:
        raise ValueError("Amostras 1..20; intervalo 0..30s")
    snapshots = []
    for index in range(samples):
        shot = collect(api, start_id, end_id, positions=positions)
        shot["sample"] = index + 1
        snapshots.append(shot)
        if index + 1 < samples:
            sleep(interval)
    signatures = {}
    for snap in snapshots:
        for obj in snap["objects"]:
            signatures.setdefault(str(obj["object_id"]), []).append(
                {"sample": snap["sample"], "type": obj["genie_type_id"],
                 "owner_slot": obj["owner_slot"], "address": obj["object_address"],
                 "candidate_position": obj["candidate_position"]})
    return {"version": "1.3", "samples": snapshots, "by_object_id": signatures,
            "scope": "Somente IDs consultados; tipo/classe/proprietario experimentais; sem afirmacao de equivalencia funcional."}
