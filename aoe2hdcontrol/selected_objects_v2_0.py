"""Selected Objects API v2.0 — seleção limitada a IDs e investigação de referências.

Somente leitura; offsets candidatos NÃO são promovidos ao catálogo.
"""
from __future__ import annotations
import struct
from .object_api import ObjectAPIError

MASK = 0x00010000
MAX_IDS = 64
PLAYER_SCAN_BYTES = 512

def _ids(ids):
    if not ids or len(ids)>MAX_IDS or len(set(ids)) != len(ids) or any(not isinstance(i,int) or not 0<=i<=1000000 for i in ids):
        raise ValueError("Informe de 1 a 64 Object IDs inteiros, distintos e válidos")
    return list(ids)

def is_object_selected(api, object_id):
    """Estado experimental de um objeto conhecido. Não enumera seleção global."""
    if not api.allow_candidates:
        raise ObjectAPIError("Seleção experimental exige --allow-candidates")
    _ids([object_id])
    obj=api.get_object_by_id(object_id)
    if obj is None:
        return None
    word=api._read(obj.address+0x38, "I")
    return bool(word & MASK)

def get_selected_objects(api, candidate_ids):
    """Retorna somente objetos sinalizados dentre candidate_ids, nunca seleção global."""
    if not api.allow_candidates:
        raise ObjectAPIError("Seleção experimental exige --allow-candidates")
    found=[]
    for oid in _ids(candidate_ids):
        obj=api.get_object_by_id(oid)
        if obj is not None and api._read(obj.address+0x38,"I") & MASK:
            found.append(obj)
    return tuple(found)

def get_selected_count(api, candidate_ids):
    """Quantidade sinalizada dentre IDs fornecidos (não total global)."""
    return len(get_selected_objects(api,candidate_ids))

def diagnose(api, candidate_ids, *, player_scan_bytes=PLAYER_SCAN_BYTES):
    """Sondagem limitada da memória do jogador local: offsets de ponteiros para objetos conhecidos."""
    ids=_ids(candidate_ids)
    if not api.allow_candidates:
        raise ObjectAPIError("Seleção experimental exige --allow-candidates")
    if player_scan_bytes % 4 or not 16<=player_scan_bytes<=PLAYER_SCAN_BYTES:
        raise ValueError("player_scan_bytes deve ser múltiplo de 4 entre 16 e 512")
    player=api.get_assigned_player()
    objects=[]
    errors=[]
    for oid in ids:
        try:
            obj=api.get_object_by_id(oid)
            if obj is None:
                errors.append({"object_id":oid,"error":"objeto ausente"})
                continue
            word=api._read(obj.address+0x38,"I")
            objects.append({"object_id":oid,"address":obj.address,
                            "class_id":obj.class_id,"genie_type_id":obj.genie_type_id,
                            "selection_word":word,"selected_candidate":bool(word & MASK)})
        except (ObjectAPIError,ValueError,OSError) as exc:
            errors.append({"object_id":oid,"error":str(exc)})
    raw=api.reader.read(player.address,player_scan_bytes)
    addresses={o["address"]:o["object_id"] for o in objects}
    matches=[]
    for offset in range(0,len(raw),4):
        ptr=struct.unpack_from("<I",raw,offset)[0]
        if ptr in addresses:
            matches.append({"player_offset":f"0x{offset:03X}","object_id":addresses[ptr],
                            "object_address":ptr})
    selected=[o["object_id"] for o in objects if o["selected_candidate"]]
    return {"schema":"hd-selected-v2.0","local_slot":player.slot,
            "player_address":player.address,"probed_ids":ids,
            "flagged_ids_among_probed":selected,
            "flagged_count_among_probed":len(selected),
            "object_observations":objects,"player_pointer_matches":matches,
            "scanned_player_bytes":player_scan_bytes,"errors":errors,
            "limitations":"Leitura limitada; não determina lista global, count global ou semântica dos offsets."}
