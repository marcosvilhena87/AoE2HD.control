"""Selected Objects API v2.2 — bounded experimental enumeration from Player+0x160.

No global memory scan, no writes. Pointer candidates must resolve through
the existing object table and the object's selection flag.
"""
from __future__ import annotations
import struct
from .object_api import ObjectAPIError

START = 0x160
MAX_ENTRIES = 32
FLAG = 0x10000

def enumerate_selected(api, *, max_entries=16):
    if not getattr(api, "allow_candidates", False):
        raise ObjectAPIError("v2.2 requires allow_candidates")
    if not isinstance(max_entries, int) or not 1 <= max_entries <= MAX_ENTRIES:
        raise ValueError("max_entries must be 1..32")
    player = api.get_assigned_player()
    raw = api.reader.read(player.address + START, max_entries * 4)
    entries, valid, diagnostics = [], [], []
    first_zero = None
    seen = set()
    for i in range(max_entries):
        offset = START + i*4
        ptr = struct.unpack_from("<I", raw, i*4)[0]
        item = {"index":i,"player_offset":f"0x{offset:03X}","pointer":ptr,
                "pointer_hex":f"0x{ptr:08X}","status":"unknown"}
        if not ptr:
            item["status"]="zero"
            if first_zero is None: first_zero=i
        elif ptr < 0x10000 or ptr > 0xFFFFFFF0 or ptr % 4:
            item["status"]="invalid_pointer"
        else:
            try:
                oid = api._read(ptr + 0x08, "I")
                item["object_id_candidate"]=oid
                if not 0 <= oid <= 1000000:
                    item["status"]="invalid_id"
                else:
                    obj=api.get_object_by_id(oid)
                    if obj is None or obj.address != ptr:
                        item["status"]="object_table_mismatch"
                    else:
                        word=api._read(ptr+0x38,"I")
                        item.update({"selection_word":word,"class_id":obj.class_id,
                                     "genie_type_id":obj.genie_type_id})
                        if word & FLAG:
                            if oid in seen:
                                item["status"]="duplicate_selected"
                            else:
                                item["status"]="selected_verified"
                                valid.append(obj)
                                seen.add(oid)
                        else:
                            item["status"]="selection_bit_inactive"
            except (ObjectAPIError,ValueError,OSError) as exc:
                item["status"]="read_error"
                item["error"]=str(exc)
        entries.append(item)
        if item["status"] not in ("zero","selected_verified"):
            diagnostics.append(item)
    after_zero_nonzero=first_zero is not None and any(
        x["pointer"] != 0 for x in entries[first_zero+1:])
    return {"schema":"hd-selected-v2.2","local_slot":player.slot,
            "player_address":player.address,"selection_region_start":START,
            "max_entries":max_entries,"selected_objects": [
                {"object_id":o.object_id,"address":o.address,"class_id":o.class_id,
                 "genie_type_id":o.genie_type_id} for o in valid],
            "selected_count_verified":len(valid),
            "slots":entries,"anomalies":diagnostics,
            "first_zero_index":first_zero,"nonzero_after_first_zero":after_zero_nonzero,
            "truncated_at_limit":first_zero is None,
            "completeness":"unknown",
            "note":"Zero is observed, not proven terminator; max_entries is a bound, not capacity."}

def get_selected_objects(api, *, max_entries=16):
    """Experimental enumerator. Returns only table-and-bit verified objects."""
    report=enumerate_selected(api,max_entries=max_entries)
    return tuple(report["selected_objects"])

def get_selected_count(api, *, max_entries=16):
    """Count verified in scanned slots; not guaranteed global total."""
    return enumerate_selected(api,max_entries=max_entries)["selected_count_verified"]
