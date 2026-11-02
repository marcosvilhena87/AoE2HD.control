"""v3.0 — experimental single-process selection transition observation.

This is a manual-action investigation, not a selection dispatcher.
"""
from __future__ import annotations

from datetime import datetime, timezone
from .selected_objects_v2_7 import inspect_selection
from .selected_objects_v2_8 import make_selection_intent
from .selected_objects_v2_9 import evaluate_external_transition


def investigate_manual_selection(api, object_ids, *, pause_for_manual_action, pid):
    """Capture before/after on one open process, with an explicit human pause.

    pause_for_manual_action MUST only prompt/wait; no input is emitted by this module.
    """
    if not getattr(api, "allow_candidates", False):
        raise ValueError("v3.0 requires allow_candidates")
    if type(pid) is not int or pid <= 0:
        raise ValueError("explicit positive PID required")
    if not callable(pause_for_manual_action):
        raise TypeError("pause_for_manual_action must be callable")
    intent = make_selection_intent(object_ids)
    before = inspect_selection(api)
    first_time = datetime.now(timezone.utc).isoformat()
    pause_for_manual_action()
    after = inspect_selection(api)
    second_time = datetime.now(timezone.utc).isoformat()

    same_player = (before.get("player_address") == after.get("player_address")
                   and before.get("local_slot") == after.get("local_slot")
                   and before.get("player_address") is not None)
    if same_player:
        transition = evaluate_external_transition(intent, before, after)
        status = transition["status"]
    else:
        transition = None
        status = "player_context_changed"

    return {"schema": "hd-selection-investigation-v3.0",
            "pid": pid, "before_time_utc": first_time, "after_time_utc": second_time,
            "context_same_player": same_player, "status": status,
            "intent": intent, "transition": transition,
            "before": before, "after": after,
            "dispatch": "unavailable", "execution": "not_dispatched",
            "manual_action": "operator_responsibility",
            "causality": "unproven", "completeness": "unknown",
            "note": "Single-process observational experiment; PID reuse/build validation and non-atomic snapshots remain limitations."}
