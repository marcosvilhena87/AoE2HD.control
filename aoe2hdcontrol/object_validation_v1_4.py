"""HD Object Validation v1.4 — vínculos estruturais, somente leitura.

Compara proximidade, referências diretas nas estruturas de objetos e amostras temporais.
Resultados de varredura são *candidatos*, nunca prova de relação pai/filho.
"""
from __future__ import annotations
import time
from .object_api import HDObjectAPI, ObjectAPIError
from .object_validation_v1_3 import collect

def capture(api: HDObjectAPI, start_id: int, end_id: int, *,
            pointer_window: int = 0x100, positions: bool = True) -> dict:
    if not api.allow_candidates:
        raise ObjectAPIError("v1.4 exige allow_candidates=True")
    if pointer_window < 0 or pointer_window > 0x200 or pointer_window % 4:
        raise ValueError("pointer_window deve ser múltiplo de quatro, de 0 até 512")
    snap = collect(api, start_id, end_id, positions=positions)
    objects = snap["objects"]
    addresses = {o["object_address"]: o["object_id"] for o in objects}
    ids = {o["object_id"] for o in objects}
    links, errors = [], list(snap["errors"])
    for obj in objects:
        for offset in range(0, pointer_window, 4):
            try:
                value = api._ptr(obj["object_address"] + offset)
            except (ObjectAPIError, OSError, ValueError) as exc:
                if len(errors) < 30:
                    errors.append({"object_id": obj["object_id"], "offset": hex(offset), "error": str(exc)})
                continue
            target = addresses.get(value)
            if target is not None and target != obj["object_id"]:
                links.append({"source_id": obj["object_id"], "target_id": target,
                              "offset": hex(offset), "kind": "direct_object_pointer_candidate"})
            # Interpretar uint32 como Object ID só é exploratório e não constitui referência.
            if value in ids and value != obj["object_id"]:
                links.append({"source_id": obj["object_id"], "target_id": value,
                              "offset": hex(offset), "kind": "id_value_coincidence"})
    groups = {}
    for o in objects:
        groups.setdefault(str(o["owner_slot"]), []).append(o["object_id"])
    return {"version": "1.4", "range": [start_id, end_id],
            "pointer_window": pointer_window, "objects": objects,
            "owner_groups": groups, "candidate_links": links, "errors": errors,
            "limits": "Somente offsets diretos dentro do objeto; sem ponteiros aninhados, sem leitura fora do conjunto e sem prova de vínculo estrutural."}


def capture_series(api: HDObjectAPI, start_id: int, end_id: int, *,
                   samples: int = 3, interval: float = 2.0, pointer_window: int = 0x100,
                   positions: bool = True, sleep=time.sleep) -> dict:
    if not 1 <= samples <= 20 or not 0 <= interval <= 30:
        raise ValueError("samples 1..20 e interval 0..30")
    snapshots = []
    for i in range(samples):
        shot = capture(api, start_id, end_id, pointer_window=pointer_window, positions=positions)
        shot["sample"] = i + 1
        snapshots.append(shot)
        if i < samples - 1:
            sleep(interval)
    all_links = {}
    for shot in snapshots:
        for link in shot["candidate_links"]:
            key = (link["source_id"], link["target_id"], link["offset"], link["kind"])
            all_links[key] = all_links.get(key, 0) + 1
    persistence = [
        {"source_id": k[0], "target_id": k[1], "offset": k[2],
         "kind": k[3], "observed_samples": v, "total_samples": samples}
        for k, v in sorted(all_links.items())
    ]
    return {"version": "1.4", "snapshots": snapshots,
            "link_persistence": persistence,
            "hypothesis": "Associação espacial e coincidência de referências são indícios; vínculo estrutural não validado."}
