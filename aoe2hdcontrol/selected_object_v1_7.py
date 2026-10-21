"""Selected Object Identification v1.7: hipóteses de seleção, somente leitura.

Offsets observados em uma sessão: Player+0x15C/+0x160 e Object+0x38.
Não afirma suporte de seleção múltipla nem promove offsets ao catálogo.
"""
from __future__ import annotations
from .object_api import HDObjectAPI, ObjectAPIError

def inspect(api: HDObjectAPI, ids: list[int]) -> dict:
    if not api.allow_candidates:
        raise ObjectAPIError("v1.7 requer --allow-candidates")
    if not ids or len(ids) > 16 or len(set(ids)) != len(ids) or any(x < 0 or x > 1_000_000 for x in ids):
        raise ValueError("Forneça 1..16 Object IDs únicos da sessão atual")
    player = api.get_assigned_player()
    refs = {hex(offset): api._ptr(player.address + offset) for offset in (0x15C, 0x160)}
    objects = []
    errors = []
    for oid in ids:
        try:
            obj = api.get_object_by_id(oid)
            if obj is None:
                errors.append({"id": oid, "error": "objeto ausente"})
                continue
            flag = api._read(obj.address + 0x38, "I")
            objects.append({"object_id": oid, "address": obj.address, "type": obj.genie_type_id,
                            "class_id": obj.class_id, "owner_address": obj.owner_address,
                            "selection_word_0x38": flag,
                            "selection_bit_16_candidate": bool(flag & 0x10000),
                            "matches_player_0x15C": refs["0x15c"] == obj.address,
                            "matches_player_0x160": refs["0x160"] == obj.address})
        except (ObjectAPIError, OSError, ValueError) as exc:
            errors.append({"id": oid, "error": str(exc)})
    return {"version": "1.7", "local_slot": player.slot, "player_address": player.address,
            "player_candidate_pointers": refs, "objects": objects, "errors": errors,
            "interpretation": "Campos e bit 16 candidatos. Ponteiros coincidentes não estabelecem seleção múltipla."}
