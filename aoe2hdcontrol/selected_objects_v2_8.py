"""v2.8 — read-only selection intent and observed-result verification.

No selection dispatch, process writes, mouse simulation or Lua bridge.
"""
from __future__ import annotations

from .object_api import ObjectAPIError
from .selected_objects_v2_7 import inspect_selection

MAX_REQUESTED = 60


def make_selection_intent(object_ids, *, mode="replace"):
    if mode != "replace":
        raise ValueError("Only replace intent is supported")
    if isinstance(object_ids, (str, bytes)) or not isinstance(object_ids, (list, tuple)):
        raise ValueError("object_ids must be a list or tuple")
    if not 1 <= len(object_ids) <= MAX_REQUESTED:
        raise ValueError("Selection request requires 1..60 IDs")
    if any(type(oid) is not int or not 0 <= oid <= 1000000 for oid in object_ids):
        raise ValueError("Invalid Object ID")
    if len(set(object_ids)) != len(object_ids):
        raise ValueError("Duplicate Object ID")
    return {"schema": "hd-selection-intent-v2.8", "mode": mode,
            "object_ids": list(object_ids), "execution": "not_dispatched"}


def verify_selection(api, intent, *, ordered=False):
    if not getattr(api, "allow_candidates", False):
        raise ObjectAPIError("v2.8 requires allow_candidates")
    if not isinstance(intent, dict):
        raise ValueError("Invalid selection intent")
    expected = make_selection_intent(intent.get("object_ids"), mode=intent.get("mode"))
    if intent.get("schema") != expected["schema"] or intent.get("execution") != "not_dispatched":
        raise ValueError("Selection intent is not an undispatched v2.8 intent")
    snapshot = inspect_selection(api)
    observed = [o["object_id"] for o in snapshot["selected_objects"]]
    stable = snapshot["consistency"] == "stable_with_candidate_count"
    matches = observed == expected["object_ids"] if ordered else set(observed) == set(expected["object_ids"])
    matches = stable and matches and len(observed) == len(expected["object_ids"])
    return {"schema": "hd-selection-verification-v2.8",
            "intent": expected, "snapshot_consistency": snapshot["consistency"],
            "observed_ids": observed if stable else [],
            "match": matches, "order_sensitive": bool(ordered),
            "status": "observed_match" if matches else "unverified",
            "execution": "not_dispatched", "completeness": "unknown",
            "note": "An observed match does not establish causality or prove a selection command ran.",
            "observation": snapshot}
