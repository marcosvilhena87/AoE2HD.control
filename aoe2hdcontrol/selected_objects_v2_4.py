"""Selected Objects API v2.4: double-read consistency, bounded diagnostic confidence.

Read-only. Two complete enumerations must agree on player, pointer slots,
object identities and statuses. This never proves global completeness.
"""
from __future__ import annotations
from .object_api import ObjectAPIError
from .selected_objects_v2_2 import enumerate_selected

def inspect_consistency(api, *, max_entries=32):
    if not getattr(api,"allow_candidates",False):
        raise ObjectAPIError("v2.4 requires allow_candidates")
    first=enumerate_selected(api,max_entries=max_entries)
    second=enumerate_selected(api,max_entries=max_entries)
    keys=("player_address","local_slot","selection_region_start","max_entries")
    metadata_equal=all(first[k]==second[k] for k in keys)
    def signature(report):
        return [(s["pointer"],s["status"],s.get("object_id_candidate"),
                 s.get("selection_word")) for s in report["slots"]]
    slots_equal=signature(first)==signature(second)
    ids_first=[o["object_id"] for o in first["selected_objects"]]
    ids_second=[o["object_id"] for o in second["selected_objects"]]
    objects_equal=first["selected_objects"]==second["selected_objects"]
    anomalies=bool(first["anomalies"] or second["anomalies"])
    gap=first["nonzero_after_first_zero"] or second["nonzero_after_first_zero"]
    limited=first["truncated_at_limit"] or second["truncated_at_limit"]
    stable=metadata_equal and slots_equal and objects_equal
    if not stable:
        confidence="unstable"
    elif anomalies or gap:
        confidence="inconsistent"
    elif limited:
        confidence="bounded_unterminated"
    else:
        confidence="stable_within_window"
    return {"schema":"hd-selected-v2.4","consistency":confidence,
            "stable_double_read":stable,"metadata_equal":metadata_equal,
            "slots_equal":slots_equal,"selected_objects_equal":objects_equal,
            "selected_ids_first":ids_first,"selected_ids_second":ids_second,
            "selected_count_verified":len(ids_second) if stable else None,
            "selected_objects":second["selected_objects"] if stable else [],
            "anomalies_present":anomalies,"gap_after_zero":gap,
            "window_exhausted":limited,"max_entries":max_entries,
            "completeness":"unknown",
            "observations":[first,second],
            "limitations":"Two sequential reads are not atomic; stable_within_window does not prove global completeness."}
