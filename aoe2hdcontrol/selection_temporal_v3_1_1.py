"""v3.1.1 — temporal observation after exactly one opt-in screen click."""
from __future__ import annotations

import time
from .selected_objects_v2_7 import inspect_selection
from .selected_objects_v2_8 import make_selection_intent
from .selection_coordinate_v3_1 import click_at, DispatchGuardError

DEFAULT_INTERVALS_MS = (50, 100, 200, 350, 500)


def select_with_temporal_verification(api, *, pid, object_id, x, y,
                                      armed=False, intervals_ms=DEFAULT_INTERVALS_MS,
                                      click=None, clock=None, sleep=None):
    """Return observations at scheduled deadlines relative to click completion.

    A positive outcome establishes temporal association, not causality.
    """
    make_selection_intent([object_id])
    if not getattr(api, "allow_candidates", False):
        raise DispatchGuardError("candidate opt-in required")
    if type(pid) is not int or pid <= 0:
        raise ValueError("positive PID required")
    if type(x) is not int or type(y) is not int or x < 0 or y < 0:
        raise ValueError("screen coordinates must be nonnegative integers")
    if armed is not True:
        raise DispatchGuardError("explicit arm required")
    if (not isinstance(intervals_ms, (list, tuple)) or not intervals_ms
            or len(intervals_ms) > 20
            or any(type(v) is not int or not 1 <= v <= 10000 for v in intervals_ms)
            or list(intervals_ms) != sorted(set(intervals_ms))):
        raise ValueError("intervals_ms must be sorted unique integers from 1 to 10000")

    clock = time.monotonic if clock is None else clock
    sleep = time.sleep if sleep is None else sleep
    before = inspect_selection(api)
    if before.get("consistency") != "stable_with_candidate_count":
        raise DispatchGuardError("unstable initial selection")
    before_ids = [o["object_id"] for o in before["selected_objects"]]
    if before_ids == [object_id]:
        raise DispatchGuardError("target already selected before click")

    (click_at if click is None else click)(x, y, pid)
    start = clock()
    observations = []
    success_at_ms = None
    for deadline_ms in intervals_ms:
        remaining = deadline_ms / 1000 - (clock() - start)
        if remaining > 0:
            sleep(remaining)
        report = inspect_selection(api)
        elapsed_ms = round((clock() - start) * 1000, 3)
        stable = report.get("consistency") == "stable_with_candidate_count"
        observed = [o["object_id"] for o in report.get("selected_objects", [])] if stable else None
        match = stable and observed == [object_id]
        observations.append({"deadline_ms": deadline_ms, "elapsed_ms": elapsed_ms,
                             "consistency": report.get("consistency"),
                             "observed_ids": observed, "match": bool(match),
                             "snapshot": report})
        if match:
            success_at_ms = elapsed_ms
            break
    matched = success_at_ms is not None
    return {"schema":"hd-coordinate-selection-v3.1.1",
            "pid":pid, "requested_object_id":object_id,
            "screen_point":{"x":x,"y":y}, "before":before,
            "before_ids":before_ids,"observations":observations,
            "status":"observed_match" if matched else "target_not_observed",
            "match":matched,"first_match_elapsed_ms":success_at_ms,
            "dispatch":"windows_mouse_click_attempted",
            "execution":"single_click_attempted",
            "causality":"unproven","completeness":"unknown",
            "note":"Single click followed by timed read-only observations; does not prove click caused the selection."}
