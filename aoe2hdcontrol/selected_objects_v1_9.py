"""v1.9: experimento de selecao 3+ e ordem. Somente leitura, universo limitado a IDs."""
from __future__ import annotations
import json
from pathlib import Path
from .selected_objects_v1_8 import inspect

PHASES = ("clear", "single_a", "single_b", "single_c", "multi_abc",
          "multi_cba", "clear_after")

def capture(api, ids, session, phase):
    if phase not in PHASES or not session or len(session)>96:
        raise ValueError("Fase ou sessao invalida")
    if len(ids)<3:
        raise ValueError("v1.9 exige pelo menos 3 Object IDs")
    result=inspect(api,ids)
    return {"schema":"hd-selected-v1.9","session":session,"phase":phase,
            "ids":list(ids),"observation":result}

def append(path, shot):
    p=Path(path)
    shots=json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    if not isinstance(shots,list):
        raise ValueError("Arquivo nao contem lista JSON")
    if shots and (shots[0].get("session")!=shot["session"] or shots[0].get("ids")!=shot["ids"]):
        raise ValueError("Sessao ou IDs incompativeis")
    if any(s.get("phase")==shot["phase"] for s in shots):
        raise ValueError("Fase duplicada; utilize outro arquivo ou sessao")
    shots.append(shot)
    p.write_text(json.dumps(shots,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return shots

def compare(shots):
    if not isinstance(shots,list) or len(shots)<2 or any(
        not isinstance(s,dict) or s.get("schema")!="hd-selected-v1.9" for s in shots
    ):
        raise ValueError("Necessarias 2+ capturas v1.9")
    if len({s["session"] for s in shots})!=1 or len({tuple(s["ids"]) for s in shots})!=1:
        raise ValueError("IDs ou sessoes diferentes")
    if len({s["phase"] for s in shots})!=len(shots):
        raise ValueError("Fases duplicadas")
    phase_results={}
    for s in shots:
        o=s["observation"]
        addr_to_id={x["address"]:x["object_id"] for x in o["objects"]}
        pointers=o["candidate_pointers"]
        phase_results[s["phase"]]={
            "flagged_ids":o["flagged_ids_among_probed"],
            "flagged_count_among_probed":len(o["flagged_ids_among_probed"]),
            "candidate_pointers":pointers,
            "pointer_ids_among_probed":{k:addr_to_id.get(v) for k,v in pointers.items()},
            "errors":o["errors"]
        }
    abc=phase_results.get("multi_abc")
    cba=phase_results.get("multi_cba")
    comparison=None
    if abc and cba:
        comparison={
            "same_flagged_ids":set(abc["flagged_ids"])==set(cba["flagged_ids"]),
            "same_pointer_ids":abc["pointer_ids_among_probed"]==cba["pointer_ids_among_probed"],
            "note":"Diferenca entre capturas nao prova, isoladamente, ordem interna da lista"
        }
    return {"schema":"hd-selected-comparison-v1.9","session":shots[0]["session"],
            "phases":phase_results,"order_comparison":comparison,
            "scope":"Somente IDs monitorados; selecao global e enumeracao ainda desconhecidas"}
