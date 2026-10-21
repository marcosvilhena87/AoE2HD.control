"""Selected Objects API v2.6 — selection enumeration using a *candidate* count.

Read-only; Player+0x254 is not a canonical/confirmed counter.
"""
from __future__ import annotations
import struct
from .object_api import ObjectAPIError

LIST_OFFSET = 0x160
COUNT_OFFSET = 0x254
MAX_SELECTED = 60
FLAG = 0x10000

def inspect_selection(api):
    if not getattr(api, "allow_candidates", False):
        raise ObjectAPIError("v2.6 requires allow_candidates")
    player = api.get_assigned_player()
    # Read counter and only that many list entries; verify count afterwards.
    count_before = api._read(player.address + COUNT_OFFSET, "I")
    if not isinstance(count_before, int) or not 0 <= count_before <= MAX_SELECTED:
        return {"schema":"hd-selected-v2.6","consistency":"invalid_count",
                "count_before":count_before,"count_after":None,
                "selected_count_verified":None,"selected_objects":[],
                "entries":[],"anomalies":["counter_outside_observed_ui_limit"],
                "completeness":"unknown"}
    raw = api.reader.read(player.address + LIST_OFFSET, count_before*4) if count_before else b""
    # First verify the complete pointer sequence; then compare candidate counter.
    pointers = struct.unpack("<" + "I"*count_before, raw) if count_before else ()
    count_after = api._read(player.address + COUNT_OFFSET, "I")
    entries, objects, errors = [], [], []
    seen=set()
    for i,pointer in enumerate(pointers):
        entry={"index":i,"offset":f"0x{LIST_OFFSET+4*i:03X}",
               "pointer":pointer,"status":"unverified"}
        if pointer < 0x10000 or pointer > 0xFFFFFFC0 or pointer % 4:
            entry["status"]="invalid_pointer"
        else:
            try:
                oid=api._read(pointer+0x08,"I")
                entry["object_id_candidate"]=oid
                if not 0 <= oid <= 1000000:
                    entry["status"]="invalid_id"
                else:
                    obj=api.get_object_by_id(oid)
                    if obj is None or obj.address!=pointer:
                        entry["status"]="object_table_mismatch"
                    else:
                        word=api._read(pointer+0x38,"I")
                        entry["selection_word"]=word
                        if not word & FLAG:
                            entry["status"]="selection_bit_inactive"
                        elif oid in seen:
                            entry["status"]="duplicate"
                        else:
                            entry["status"]="selected_verified"
                            seen.add(oid)
                            objects.append({"object_id":oid,"address":pointer,
                                            "class_id":obj.class_id,
                                            "genie_type_id":obj.genie_type_id})
            except (ObjectAPIError,OSError,ValueError) as exc:
                entry["status"]="read_error"
                entry["error"]=str(exc)
        entries.append(entry)
        if entry["status"]!="selected_verified":errors.append(entry)
    # Recheck after object validation, too: detecting concurrent state changes.
    count_final = api._read(player.address + COUNT_OFFSET, "I")
    stable_count = count_before == count_after == count_final
    valid = stable_count and not errors and len(objects)==count_before
    status=("counter_changed" if not stable_count else
            "invalid_entries" if errors else "consistent_with_candidate_count")
    return {"schema":"hd-selected-v2.6","consistency":status,
            "player_address":player.address,"local_slot":player.slot,
            "count_before":count_before,"count_after":count_after,
            "count_final":count_final,"counter_stable":stable_count,
            "selected_objects":objects if valid else [],
            "selected_count_verified":len(objects) if valid else None,
            "entries":entries,"anomalies":errors,
            "completeness":"unknown",
            "note":"Candidate counter matches scanned entries; not proof of global completeness. Non-atomic read."}

def get_selected_objects(api):
    return tuple(inspect_selection(api)["selected_objects"])

def get_selected_count(api):
    return inspect_selection(api)["selected_count_verified"]
