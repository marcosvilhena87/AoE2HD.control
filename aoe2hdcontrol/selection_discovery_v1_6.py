"""Selection Memory Discovery v1.6 — leituras limitadas de regiões conhecidas.

Não faz varredura de todo o processo; captura janelas dos objetos e do jogador
local nas fases declaradas pelo operador. Não infere seleção automaticamente.
"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
from .object_api import HDObjectAPI, ObjectAPIError

PHASES = ("baseline", "tc_selected", "deselected", "villager_selected")

def capture(api: HDObjectAPI, phase: str, session: str, ids: list[int], *,
            object_bytes: int = 256, player_bytes: int = 512) -> dict:
    if not api.allow_candidates:
        raise ObjectAPIError("Selection Discovery exige --allow-candidates")
    if phase not in PHASES or not session or len(session) > 96:
        raise ValueError("fase ou sessão inválida")
    if len(ids) > 16 or len(set(ids)) != len(ids) or any(i < 0 for i in ids):
        raise ValueError("Use até 16 IDs únicos e não negativos")
    if not (0 <= object_bytes <= 1024 and 0 <= player_bytes <= 1024):
        raise ValueError("Janelas máximas de 1024 bytes")
    local = api.get_assigned_player()
    targets = [("player_local", local.address, player_bytes)]
    errors = []
    for oid in ids:
        try:
            obj = api.get_object_by_id(oid)
            if obj:
                targets.append((f"object_{oid}", obj.address, object_bytes))
            else:
                errors.append({"target": f"object_{oid}", "error": "não encontrado"})
        except (ObjectAPIError, ValueError, OSError) as exc:
            errors.append({"target": f"object_{oid}", "error": str(exc)})
    regions = {}
    for name, address, size in targets:
        if not size:
            continue
        try:
            raw = api.reader.read(address, size)
            regions[name] = {"address": address, "size": size, "hex": raw.hex()}
        except (ObjectAPIError, OSError, ValueError) as exc:
            errors.append({"target": name, "error": str(exc)})
    return {"schema": "hd-selection-v1.6", "session": session, "phase": phase,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "local_slot": local.slot, "ids": ids, "regions": regions, "errors": errors,
            "note": "Fases manuais; offsets detectados apenas como candidatos."}


def append(path: str | Path, snapshot: dict) -> list[dict]:
    p = Path(path)
    series = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    if not isinstance(series, list):
        raise ValueError("Arquivo existente não contém uma lista JSON")
    if series and (series[0]["session"] != snapshot["session"] or
                   series[0]["ids"] != snapshot["ids"] or
                   {k: r["size"] for k, r in series[0]["regions"].items()} !=
                   {k: r["size"] for k, r in snapshot["regions"].items()}):
        raise ValueError("Sessão, IDs ou regiões divergentes; use outro arquivo")
    series.append(snapshot)
    p.write_text(json.dumps(series, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return series


def compare(series: list[dict]) -> dict:
    phases = [s["phase"] for s in series]
    if len(series) < 3 or any(s.get("schema") != "hd-selection-v1.6" for s in series):
        raise ValueError("Mínimo três capturas no formato v1.6")
    if len({s["session"] for s in series}) != 1 or len({tuple(s["ids"]) for s in series}) != 1:
        raise ValueError("Sessões ou IDs incompatíveis")
    diffs = []
    for a, b in zip(series, series[1:]):
        changed = []
        for name in sorted(set(a["regions"]) & set(b["regions"])):
            before, after = a["regions"][name], b["regions"][name]
            if before["address"] != after["address"] or before["size"] != after["size"]:
                continue
            x, y = bytes.fromhex(before["hex"]), bytes.fromhex(after["hex"])
            for offset in range(0, min(len(x), len(y)), 4):
                lhs, rhs = x[offset:offset+4], y[offset:offset+4]
                if lhs != rhs:
                    changed.append({"region": name, "offset": f"0x{offset:X}",
                                    "before": lhs.hex(), "after": rhs.hex()})
        diffs.append({"from": a["phase"], "to": b["phase"], "changed_words": changed})
    # Ciclo baseline -> TC -> deselected: apenas diferenças revertidas são candidatas.
    patterns = []
    for i in range(len(series)-2):
        a,b,c = series[i:i+3]
        if (a["phase"],b["phase"],c["phase"]) != ("baseline","tc_selected","deselected"):
            continue
        for name in sorted(set(a["regions"]) & set(b["regions"]) & set(c["regions"])):
            regs = [s["regions"][name] for s in (a,b,c)]
            if len({r["address"] for r in regs}) != 1 or len({r["size"] for r in regs}) != 1:
                continue
            raws = [bytes.fromhex(r["hex"]) for r in regs]
            for offset in range(0, len(raws[0]), 4):
                words = [r[offset:offset+4] for r in raws]
                if len(words[0]) == 4 and words[0] == words[2] and words[0] != words[1]:
                    patterns.append({"region": name, "offset": f"0x{offset:X}",
                                     "baseline_hex": words[0].hex(), "selected_hex": words[1].hex(),
                                     "deselected_hex": words[2].hex()})
    return {"schema": "hd-selection-comparison-v1.6", "phases": phases,
            "transitions": diffs, "reversible_candidates": patterns,
            "errors": [s["errors"] for s in series],
            "limits": "Comparação de palavras de 4 bytes em regiões limitadas; coincidência temporal não é prova de seleção."}
