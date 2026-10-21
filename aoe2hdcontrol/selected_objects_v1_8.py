"""Selected Objects API v1.8 — identificação experimental de seleção múltipla.

Consulta somente os IDs informados, jamais presume enumeração global.
"""
from __future__ import annotations
import json
from pathlib import Path
from .object_api import HDObjectAPI, ObjectAPIError

PHASES = ("clear", "single_first", "single_second", "multi", "clear_after")

def inspect(api: HDObjectAPI, ids: list[int]) -> dict:
    if not api.allow_candidates:
        raise ObjectAPIError("v1.8 requer --allow-candidates")
    if not 1 <= len(ids) <= 32 or len(set(ids)) != len(ids) or any(i < 0 or i > 1000000 for i in ids):
        raise ValueError("Informe 1..32 IDs únicos da partida atual")
    player = api.get_assigned_player()
    pointers = {"0x15c": api._ptr(player.address + 0x15C),
                "0x160": api._ptr(player.address + 0x160)}
    objects, errors = [], []
    for oid in ids:
        try:
            obj = api.get_object_by_id(oid)
            if obj is None:
                errors.append({"id": oid, "error": "objeto ausente"})
                continue
            word = api._read(obj.address + 0x38, "I")
            objects.append({"object_id": oid, "address": obj.address,
                            "class_id": obj.class_id, "genie_type_id": obj.genie_type_id,
                            "owner_address": obj.owner_address,
                            "selection_word_0x38": word,
                            "selection_bit_0x10000": bool(word & 0x10000),
                            "matches_pointer_0x15c": pointers["0x15c"] == obj.address,
                            "matches_pointer_0x160": pointers["0x160"] == obj.address})
        except (ObjectAPIError, ValueError, OSError) as exc:
            errors.append({"id": oid, "error": str(exc)})
    return {"version": "1.8", "local_slot": player.slot, "player_address": player.address,
            "candidate_pointers": pointers, "objects": objects,
            "flagged_ids_among_probed": [o["object_id"] for o in objects if o["selection_bit_0x10000"]],
            "errors": errors, "scope": "Apenas IDs fornecidos; nao e lista global de selecionados"}


def append(path: str | Path, snapshot: dict) -> list[dict]:
    p = Path(path)
    series = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    if not isinstance(series, list):
        raise ValueError("Esperada lista JSON no arquivo")
    if series and (series[0]["session"] != snapshot["session"] or series[0]["ids"] != snapshot["ids"]):
        raise ValueError("Sessão ou IDs diferentes: use outro arquivo")
    series.append(snapshot)
    p.write_text(json.dumps(series, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return series


def capture(api: HDObjectAPI, ids: list[int], phase: str, session: str) -> dict:
    if phase not in PHASES or not session or len(session) > 96:
        raise ValueError("Fase ou sessão inválida")
    return {"schema": "hd-selected-v1.8", "session": session, "phase": phase,
            "ids": ids, "observation": inspect(api, ids)}


def compare(series: list[dict]) -> dict:
    if len(series) < 2 or any(s.get("schema") != "hd-selected-v1.8" for s in series):
        raise ValueError("Requer pelo menos duas capturas v1.8")
    if len({s["session"] for s in series}) != 1 or len({tuple(s["ids"]) for s in series}) != 1:
        raise ValueError("Sessões ou IDs incompatíveis")
    phases = {}
    for snap in series:
        obs = snap["observation"]
        phases.setdefault(snap["phase"], []).append({
            "flagged_ids": obs["flagged_ids_among_probed"],
            "pointers": obs["candidate_pointers"],
            "pointer_matches": {key: [o["object_id"] for o in obs["objects"]
                         if o["address"] == ptr] for key, ptr in obs["candidate_pointers"].items()},
            "errors": obs["errors"]})
    return {"version": "1.8", "session": series[0]["session"], "phases": phases,
            "limitations": "Bit 0x10000 e ponteiros sao candidatos; flags nao garantem cobertura global nem semantica de lista."}
