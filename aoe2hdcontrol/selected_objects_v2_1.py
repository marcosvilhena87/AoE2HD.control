"""Selected Objects API v2.1 — capture bounded candidate selection slots.

Read-only, no global traversal. Player+0x150..+0x1AC inclusive
captures raw 32-bit words and associates them with known Object IDs.
"""
from __future__ import annotations
import json
import struct
from pathlib import Path
from .object_api import ObjectAPIError
from .selected_objects_v2_0 import _ids, MASK

PHASES=("clear","single","pair","trio","four_plus","clear_after")
START=0x150
STOP=0x1B0

def capture(api, ids, phase, session):
    if not getattr(api,"allow_candidates",False):
        raise ObjectAPIError("Exige allow_candidates")
    if phase not in PHASES or not session or len(session)>96:
        raise ValueError("Fase ou sessao invalida")
    ids=_ids(ids)
    player=api.get_assigned_player()
    objects=[]
    errors=[]
    for oid in ids:
        try:
            obj=api.get_object_by_id(oid)
            if obj is None:
                errors.append({"id":oid,"reason":"not_found"})
                continue
            word=api._read(obj.address+0x38,"I")
            objects.append({"id":oid,"address":obj.address,"class_id":obj.class_id,
                            "type_id":obj.genie_type_id,"selection_word":word,
                            "selected_candidate":bool(word & MASK)})
        except (ObjectAPIError,OSError,ValueError) as ex:
            errors.append({"id":oid,"reason":str(ex)})
    raw=api.reader.read(player.address+START,STOP-START)
    address_ids={item["address"]:item["id"] for item in objects}
    slots=[]
    for index in range(0,len(raw),4):
        value=struct.unpack_from("<I",raw,index)[0]
        slots.append({"offset":f"0x{START+index:03X}","value":value,
                      "value_hex":f"0x{value:08X}",
                      "known_object_id":address_ids.get(value)})
    return {"schema":"hd-selection-v2.1","session":session,"phase":phase,"ids":ids,
            "player_address":player.address,"local_slot":player.slot,
            "region_start":START,"region_stop":STOP,
            "slots":slots,"objects":objects,"errors":errors,
            "note":"Matching a pointer only identifies known objects; no global enumeration."}

def append(path, shot):
    p=Path(path)
    series=json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    if not isinstance(series,list):raise ValueError("Expected JSON list")
    if series and (series[0].get("session")!=shot["session"] or series[0].get("ids")!=shot["ids"]):
        raise ValueError("Session/IDs mismatch")
    if any(x.get("phase")==shot["phase"] for x in series):
        raise ValueError("Duplicate phase")
    series.append(shot)
    p.write_text(json.dumps(series,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return series

def compare(series):
    if not isinstance(series,list) or len(series)<2:
        raise ValueError("Need 2+ snapshots")
    if any(not isinstance(x,dict) or x.get("schema")!="hd-selection-v2.1" for x in series):
        raise ValueError("Invalid snapshot schema")
    if len({x["session"] for x in series})!=1 or len({tuple(x["ids"]) for x in series})!=1:
        raise ValueError("Incompatible session or ids")
    if len({x["phase"] for x in series})!=len(series):
        raise ValueError("Duplicate phase")
    phases={}
    all_offsets=[s["offset"] for s in series[0]["slots"]]
    if any([x["offset"] for x in snap["slots"]]!=all_offsets for snap in series):
        raise ValueError("Different scan region")
    for s in series:
        phases[s["phase"]]={
            "selected_ids_among_probed":[o["id"] for o in s["objects"] if o["selected_candidate"]],
            "slots_with_known_objects":[slot for slot in s["slots"] if slot["known_object_id"] is not None],
            "errors":s["errors"]
        }
    changes=[]
    for offset in all_offsets:
        vals=[next(slot["value"] for slot in snap["slots"] if slot["offset"]==offset) for snap in series]
        if len(set(vals))>1:
            changes.append({"offset":offset,"values_by_phase":{s["phase"]:f"0x{v:08X}" for s,v in zip(series,vals)}})
    return {"schema":"hd-selection-comparison-v2.1","session":series[0]["session"],
            "phases":phases,"changed_slots":changes,
            "limitations":"No selection count or list boundaries confirmed; raw slots only."}
