"""Validação experimental v1.2: localizar construções por proprietário sem escrita."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from .object_api import HDObjectAPI, ObjectAPIError


@dataclass(frozen=True)
class BuildingMatch:
    object_id: int
    address: int
    class_id: int
    genie_type_id: int | None
    owner_address: int
    owner_slot: int | None
    is_local: bool


def _players(api: HDObjectAPI) -> tuple[int, dict[int, int]]:
    """Captura índice do jogador local e tabela de ponteiros numa passagem."""
    world = api.world()
    local_slot = api._read(world + api._offset("World", "0x174"), "I")
    begin = api._ptr(world + api._offset("World", "0x184"))
    end = api._ptr(world + api._offset("World", "0x188"))
    if not begin or end < begin or (end - begin) % 8 or (end - begin) > 9 * 8:
        raise ObjectAPIError("Tabela de jogadores inconsistente")
    count = (end - begin) // 8
    if local_slot >= count:
        raise ObjectAPIError("Slot local fora da tabela")
    slot_ptr = api._offset("PlayerEntry", "0x00")
    players = {}
    for slot in range(count):
        ptr = api._ptr(begin + slot * 8 + slot_ptr)
        if ptr:
            players[ptr] = slot
    return local_slot, players


def scan_buildings(
    api: HDObjectAPI, start_id: int, end_id: int, *,
    only_local: bool = True, target_type: int | None = None,
    max_ids: int = 512,
) -> dict:
    """Busca faixa limitada [start_id,end_id]; não promete enumeração global.

    Leituras falhas são contadas sem abortar a inspeção dos outros IDs.
    O campo Object+0x10 continua candidato; correspondência de proprietário
    indica evidência, não prova semântica definitiva.
    """
    if not api.allow_candidates:
        raise ObjectAPIError("Validação v1.2 requer allow_candidates=True")
    if not (0 <= start_id <= end_id <= 1_000_000):
        raise ValueError("Faixa de IDs inválida")
    if end_id - start_id + 1 > max_ids:
        raise ValueError(f"Faixa excede limite de {max_ids} IDs")
    local_slot, player_by_ptr = _players(api)
    if local_slot not in player_by_ptr.values():
        raise ObjectAPIError("Jogador local sem ponteiro")
    matches = []
    counters = {"empty": 0, "read_errors": 0, "id_mismatches": 0, "other_classes": 0, "other_owners": 0, "other_types": 0}
    errors = []
    for oid in range(start_id, end_id + 1):
        try:
            obj = api.get_object_by_id(oid)
        except (ObjectAPIError, OSError, ValueError) as exc:
            counters["read_errors"] += 1
            if "ID inconsistente" in str(exc):
                counters["id_mismatches"] += 1
            if len(errors) < 12:
                errors.append({"id": oid, "error": str(exc)})
            continue
        if obj is None:
            counters["empty"] += 1
            continue
        if obj.class_id != 3:
            counters["other_classes"] += 1
            continue
        slot = player_by_ptr.get(obj.owner_address)
        if only_local and slot != local_slot:
            counters["other_owners"] += 1
            continue
        if target_type is not None and obj.genie_type_id != target_type:
            counters["other_types"] += 1
            continue
        matches.append(asdict(BuildingMatch(obj.object_id, obj.address, obj.class_id,
                                           obj.genie_type_id, obj.owner_address or 0,
                                           slot, slot == local_slot)))
    return {"version": "1.2", "start_id": start_id, "end_id": end_id,
            "scanned": end_id - start_id + 1, "local_slot": local_slot,
            "players_by_pointer": {f"0x{ptr:08X}": slot for ptr, slot in player_by_ptr.items()},
            "class_filter": 3, "only_local": only_local, "target_type": target_type,
            "matches": matches, "counters": counters, "error_samples": errors,
            "note": "Object+0x10 ainda é campo candidato; resultados não validam semântica nem completude."}
