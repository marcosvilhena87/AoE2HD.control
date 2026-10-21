"""Validação comportamental v1.5: snapshots anotados pelo operador.

Não envia comandos nem afirma conhecer campos de seleção. Capturas antes/depois
permitem medir aparecimento, desaparecimento e mudanças em IDs já observados.
"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
from .object_api import HDObjectAPI, ObjectAPIError
from .object_validation_v1_3 import collect

PHASES = frozenset(("baseline", "selected", "deselected", "built", "destroyed", "other"))


def phase_capture(api: HDObjectAPI, start_id: int, end_id: int, *,
                  phase: str, session: str, positions: bool = True) -> dict:
    if phase not in PHASES:
        raise ValueError("Fase desconhecida")
    if not session or len(session) > 96:
        raise ValueError("Sessão deve ter 1..96 caracteres")
    shot = collect(api, start_id, end_id, positions=positions)
    return {"schema": "hd-object-behavior-v1.5", "session": session,
            "phase": phase, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "capture": shot, "operator_action": "Fase declarada pelo operador; sem observação direta da interface."}


def compare_phases(captures: list[dict]) -> dict:
    if len(captures) < 2:
        raise ValueError("São necessárias pelo menos duas capturas")
    if any(c.get("schema") != "hd-object-behavior-v1.5" for c in captures):
        raise ValueError("Arquivo não pertence ao esquema v1.5")
    sessions = {c["session"] for c in captures}
    if len(sessions) != 1:
        raise ValueError("Não comparar sessões distintas por IDs absolutos")
    spans = {tuple(c["capture"]["range"]) for c in captures}
    if len(spans) != 1:
        raise ValueError("Faixas de ID divergentes")
    transitions = []
    for before, after in zip(captures, captures[1:]):
        old = {x["object_id"]: x for x in before["capture"]["objects"]}
        new = {x["object_id"]: x for x in after["capture"]["objects"]}
        changed = []
        keys = ("object_address", "genie_type_id", "class_id", "owner_slot",
                "owner_address", "candidate_position")
        for oid in sorted(old.keys() & new.keys()):
            changes = {k: {"before": old[oid].get(k), "after": new[oid].get(k)}
                       for k in keys if old[oid].get(k) != new[oid].get(k)}
            if changes:
                changed.append({"object_id": oid, "fields": changes})
        transitions.append({
            "from": before["phase"], "to": after["phase"],
            "appeared_ids": sorted(new.keys() - old.keys()),
            "disappeared_ids": sorted(old.keys() - new.keys()),
            "changed": changed,
            "before_errors": before["capture"]["errors"],
            "after_errors": after["capture"]["errors"],
            "complete": not before["capture"]["errors"] and not after["capture"]["errors"],
        })
    return {"schema": "hd-object-behavior-comparison-v1.5",
            "session": captures[0]["session"], "phases": [c["phase"] for c in captures],
            "transitions": transitions,
            "caution": "Sem leitura de seleção na UI; diferenças são correlações, e ausências podem resultar do filtro de tipo ou da faixa incompleta."}


def append_capture(path: str | Path, shot: dict) -> list[dict]:
    file = Path(path)
    if file.exists():
        data = json.loads(file.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("Arquivo existente deve conter lista JSON")
        if data and data[0].get("session") != shot["session"]:
            raise ValueError("O arquivo já contém outra sessão")
        if data and tuple(data[0]["capture"]["range"]) != tuple(shot["capture"]["range"]):
            raise ValueError("Faixa de IDs diferente do arquivo")
    else:
        data = []
    data.append(shot)
    file.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data
