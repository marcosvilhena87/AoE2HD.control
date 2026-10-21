"""Selected Objects API v2.5: bounded 64-slot, double-read experimental selection.

60 mobile units is an observed UI limit, NOT proven memory capacity.
No writes. No automatic promotion to canonical mappings.
"""
from __future__ import annotations
import struct
from .object_api import ObjectAPIError

START=0x160
MAX_ENTRIES=64
UI_MOBILE_LIMIT_OBSERVED=60
FLAG=0x10000

def _snapshot(api, count):
    player=api.get_assigned_player()
    raw=api.reader.read(player.address+START,count*4)
    slots=[]; objects=[]; issues=[]; seen=set(); first_zero=None
    for i in range(count):
        p=struct.unpack_from("<I",raw,i*4)[0]
        item={"index":i,"offset":f"0x{START+4*i:03X}","pointer":p,"status":"unverified"}
        if p==0:
            item["status"]="zero"
            if first_zero is None:first_zero=i
        elif p<0x10000 or p>0xFFFFFFC0 or p%4:
            item["status"]="invalid_pointer"
        else:
            try:
                oid=api._read(p+0x08,"I")
                item["object_id_candidate"]=oid
                if not isinstance(oid,int) or not 0<=oid<=1000000:
                    item["status"]="invalid_id"
                else:
                    obj=api.get_object_by_id(oid)
                    if obj is None or obj.address!=p:
                        item["status"]="object_table_mismatch"
                    else:
                        flag=api._read(p+0x38,"I")
                        item["selection_word"]=flag
                        if not flag & FLAG:item["status"]="not_selected"
                        elif oid in seen:item["status"]="duplicate"
                        else:
                            item["status"]="selected_verified"
                            seen.add(oid)
                            objects.append({"object_id":oid,"address":p,
                                            "class_id":obj.class_id,
                                            "genie_type_id":obj.genie_type_id})
            except (ObjectAPIError,OSError,ValueError) as ex:
                item["status"]="read_error"
                item["error"]=str(ex)
        slots.append(item)
        if item["status"] not in ("zero","selected_verified"):issues.append(item)
    return {"player_address":player.address,"local_slot":player.slot,
            "slots":slots,"selected_objects":objects,"selected_count_verified":len(objects),
            "anomalies":issues,"first_zero_index":first_zero,
            "nonzero_after_zero":first_zero is not None and any(
                s["pointer"]!=0 for s in slots[first_zero+1:]),
            "window_exhausted":first_zero is None}

def inspect_selection(api, *, max_entries=64):
    if not getattr(api,"allow_candidates",False):
        raise ObjectAPIError("v2.5 requires allow_candidates")
    if type(max_entries) is not int or not 1<=max_entries<=MAX_ENTRIES:
        raise ValueError("max_entries must be 1..64")
    a=_snapshot(api,max_entries)
    b=_snapshot(api,max_entries)
    stable=(a["player_address"]==b["player_address"]
            and a["local_slot"]==b["local_slot"]
            and a["slots"]==b["slots"]
            and a["selected_objects"]==b["selected_objects"])
    anomalies=bool(a["anomalies"] or b["anomalies"])
    gap=a["nonzero_after_zero"] or b["nonzero_after_zero"]
    limit=a["window_exhausted"] or b["window_exhausted"]
    state=("unstable" if not stable else
           "inconsistent" if anomalies or gap else
           "bounded_unterminated" if limit else "stable_within_window")
    return {"schema":"hd-selected-v2.5","consistency":state,
            "stable_double_read":stable,"max_entries":max_entries,
            "mobile_ui_limit_observed":UI_MOBILE_LIMIT_OBSERVED,
            "selected_objects":b["selected_objects"] if stable and not anomalies and not gap else [],
            "selected_count_verified":b["selected_count_verified"] if stable and not anomalies and not gap else None,
            "first_zero_index":b["first_zero_index"] if stable else None,
            "window_exhausted":limit,"anomalies_present":anomalies,
            "nonzero_after_zero":gap,"completeness":"unknown",
            "observations":[a,b],
            "limitations":"Non-atomic reads; zero terminator, capacity and global completeness unproven."}

def get_selected_objects(api, *, max_entries=64):
    return tuple(inspect_selection(api,max_entries=max_entries)["selected_objects"])

def get_selected_count(api, *, max_entries=64):
    return inspect_selection(api,max_entries=max_entries)["selected_count_verified"]
