"""v2.9: fail-closed dispatch gate and external-transition audit.

No Windows memory writes or game input. A caller cannot mistake a manually
observed transition for an internally dispatched selection.
"""
from __future__ import annotations

from .selected_objects_v2_8 import make_selection_intent

SCHEMA = "hd-selection-transition-v2.9"


class DispatchUnavailable(RuntimeError):
    """No verified HD selection dispatcher is installed."""


def dispatch_selection(intent, *, backend=None):
    """Fail closed: real dispatch requires a separately validated HD backend.

    The optional backend is intentionally NOT invoked. Before enabling it,
    a future revision must define an explicit capability/authorization contract.
    """
    validate_intent(intent)
    raise DispatchUnavailable("HD selection dispatch is not validated; no input sent")


def validate_intent(intent):
    if not isinstance(intent, dict):
        raise ValueError("invalid intent")
    expected = make_selection_intent(intent.get("object_ids"), mode=intent.get("mode"))
    if intent != expected:
        raise ValueError("intent differs from canonical undispatched v2.8 intent")
    return expected


def _observed(report):
    if not isinstance(report, dict) or report.get("schema") != "hd-selected-v2.7":
        raise ValueError("expected a v2.7 snapshot")
    stable = report.get("consistency") == "stable_with_candidate_count"
    objects = report.get("selected_objects")
    if not stable or not isinstance(objects, list):
        return None
    ids = [x.get("object_id") for x in objects if isinstance(x, dict)]
    n = report.get("selected_count_verified")
    if (type(n) is not int or len(ids) != len(objects) or len(ids) != n
            or any(type(i) is not int for i in ids) or len(set(ids)) != len(ids)):
        return None
    return ids


def evaluate_external_transition(intent, before, after):
    """Audit two separate observations; NEVER claim a programmatic dispatch."""
    expected = validate_intent(intent)["object_ids"]
    old, new = _observed(before), _observed(after)
    if old is None or new is None:
        state = "inconclusive_snapshot"
    elif set(new) != set(expected) or len(new) != len(expected):
        state = "target_not_observed"
    elif set(old) == set(expected) and len(old) == len(expected):
        state = "already_selected_before"
    else:
        state = "external_transition_observed"
    return {"schema": SCHEMA, "status": state, "requested_ids": expected,
            "before_ids": old, "after_ids": new,
            "dispatch": "not_available", "execution": "not_dispatched",
            "causality": "unproven", "completeness": "unknown",
            "note": "Two non-atomic captures cannot prove which external action caused a change."}
