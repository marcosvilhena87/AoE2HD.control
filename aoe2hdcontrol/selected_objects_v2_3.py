"""v2.3: bounded selection capacity and nearby counter-candidate survey."""
from __future__ import annotations
import json
import struct
from pathlib import Path
from .object_api import ObjectAPIError
from .selected_objects_v2_2 import enumerate_selected

PHASES=("clear","four","eight","twelve","sixteen","over_sixteen","clear_after")
SCAN_START=0x120
SCAN_END=0x160
LIMITS=(4,8,12,16,32)

def capture(api, phase, session, *, max_entries=32):
    if phase not in PHASES or not session or len(session)>96:
        raise ValueError("invalid phase/session")
    if not getattr(api,"allow_candidates",False):
        raise ObjectAPIError("v2.3 requires allow_candidates")
    if not isinstance(max_entries,int) or not 1<=max_entries<=32:
        raise ValueError("max_entries must be 1..32")
    report=enumerate_selected(api,max_entries=max_entries)
    raw=api.reader.read(report["player_address"]+SCAN_START,SCAN_END-SCAN_START)
    words=[{"offset":f"0x{x:03X}","value":struct.unpack_from("<I",raw,x-SCAN_START)[0]}
           for x in range(SCAN_START,SCAN_END,4)]
    return {"schema":"hd-selection-v2.3","session":session,"phase":phase,
            "player_address":report["player_address"],"local_slot":report["local_slot"],
            "enumeration":report,"nearby_words":words}

def append(path,shot):
    p=Path(path)
    arr=json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    if not isinstance(arr,list):raise ValueError("Expected JSON array")
    if arr and (arr[0].get("session")!=shot["session"] or arr[0].get("player_address")!=shot["player_address"]):
        raise ValueError("Different session or player address")
    if any(x.get("phase")==shot["phase"] for x in arr):
        raise ValueError("Duplicate phase")
    arr.append(shot)
    p.write_text(json.dumps(arr,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return arr

def compare(shots):
    if not isinstance(shots,list) or len(shots)<2 or any(
        not isinstance(x,dict) or x.get("schema")!="hd-selection-v2.3" for x in shots):
        raise ValueError("Need 2+ v2.3 snapshots")
    if len({x["session"] for x in shots})!=1 or len({x["player_address"] for x in shots})!=1:
        raise ValueError("Incompatible session or player address")
    if len({x["phase"] for x in shots})!=len(shots):
        raise ValueError("Duplicate phases")
    phases={}
    for x in shots:
        e=x["enumeration"]
        phases[x["phase"]]={"verified_count":e["selected_count_verified"],
           "selected_ids":[o["object_id"] for o in e["selected_objects"]],
           "first_zero_index":e["first_zero_index"],"truncated_at_limit":e["truncated_at_limit"],
           "anomalies":e["anomalies"]}
    targets={x["phase"]:x["enumeration"]["selected_count_verified"] for x in shots}
    offsets=[w["offset"] for w in shots[0]["nearby_words"]]
    if any([w["offset"] for w in x["nearby_words"]]!=offsets for x in shots):
        raise ValueError("Different survey region")
    candidates=[]
    for offset in offsets:
        vals=[next(w["value"] for w in x["nearby_words"] if w["offset"]==offset) for x in shots]
        if len(set(vals))>1:
            matches=sum(v==targets[x["phase"]] for v,x in zip(vals,shots))
            candidates.append({"offset":offset,"values_by_phase":{x["phase"]:v for x,v in zip(shots,vals)},
                               "equal_verified_count_phases":matches,
                               "total_phases":len(shots)})
    return {"schema":"hd-selection-comparison-v2.3","session":shots[0]["session"],
      "phases":phases,"nearby_changing_words":candidates,
      "limitations":"Count candidates are correlations only. No proven global count, terminator, or maximum capacity."}
