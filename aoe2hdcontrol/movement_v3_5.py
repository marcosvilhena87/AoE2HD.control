"""v3.5: telemetry of ONE guarded movement attempt, using candidate HD fields.

Not a native UnitsMove API; does not prove the clicked point's world position,
command acceptance, causality or arrival. No writes to process memory.
"""
from __future__ import annotations

import math
import time
from datetime import datetime, timezone

from .movement_v3_4 import (
    _identity_position, _selection_id, right_click_client,
)
from .object_api import ObjectAPIError
from .selection_coordinate_v3_1 import DispatchGuardError

SCHEMA = "hd-movement-telemetry-v3.5"


def _positive_number(value, name, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be finite numeric")
    value = float(value)
    if not math.isfinite(value) or (value < 0 if allow_zero else value <= 0):
        raise ValueError(f"{name} out of range")
    return value


def _point(sample):
    x = sample["candidate_world_x"]
    y = sample["candidate_world_y"]
    if any(isinstance(v, bool) or not isinstance(v, (float, int)) or
           not math.isfinite(v) for v in (x, y)):
        raise ObjectAPIError("Non-finite candidate coordinate")
    return float(x), float(y)


def movement_metrics(samples, *, movement_threshold=0.25, stationary_epsilon=0.03,
                     stationary_samples=3):
    """Pure analysis: samples [{elapsed_ms, x, y}], including t=0.

    Movement and stationary evidence can coexist (unit walked, then stopped).
    Stationary means only no observed movement above epsilon for consecutive
    intervals, NEVER arrival at the click destination.
    """
    threshold = _positive_number(movement_threshold, "movement_threshold")
    epsilon = _positive_number(stationary_epsilon, "stationary_epsilon", allow_zero=True)
    if type(stationary_samples) is not int or not 2 <= stationary_samples <= 25:
        raise ValueError("stationary_samples must be between 2 and 25")
    if not isinstance(samples, (list, tuple)) or not samples:
        raise ValueError("At least one sample required")
    prior = None
    origin = None
    total_path = 0.0
    stationary_run = 0
    rows = []
    for sample in samples:
        x, y = _point(sample)
        t = _positive_number(sample["elapsed_ms"], "elapsed_ms", allow_zero=True)
        if prior is not None and t <= prior[0]:
            raise ValueError("Sample timestamps must increase strictly")
        if prior is None:
            origin = (x, y)
            step = 0.0
            velocity = None
        else:
            step = math.hypot(x - prior[1], y - prior[2])
            velocity = step / ((t - prior[0]) / 1000.0)
            total_path += step
            stationary_run = stationary_run + 1 if step <= epsilon else 0
        radial = math.hypot(x - origin[0], y - origin[1])
        rows.append({"elapsed_ms": t, "x": x, "y": y,
                     "step_distance_candidate": step,
                     "net_distance_candidate": radial,
                     "path_distance_candidate": total_path,
                     "speed_candidate_units_s": velocity,
                     "stationary_intervals": stationary_run,
                     "stationary_candidate": stationary_run >= stationary_samples})
        prior = (t, x, y)
    movement_observed = total_path >= threshold
    stationary_observed = stationary_run >= stationary_samples
    return {"samples": rows, "path_distance_candidate": total_path,
            "net_distance_candidate": rows[-1]["net_distance_candidate"],
            "movement_observed": movement_observed,
            "stationary_observed": stationary_observed,
            "arrival_verified": False, "arrival_status": "arrival_unverified",
            "movement_threshold": threshold, "stationary_epsilon": epsilon,
            "stationary_samples": stationary_samples}


def monitor(api, *, pid, object_id, client_x, client_y, armed=False,
            offline_confirmed=False, interval_ms=200, duration_ms=5000,
            movement_threshold=0.25, stationary_epsilon=0.03,
            stationary_samples=3, sender=None, clock=None, sleep=None):
    """Send one guarded right click; monitor until duration or first read failure.

    Only the dispatch path uses Windows. Unit tests pass fake callbacks; every
    real dispatch goes through v3.4 right_click_client foreground/client guards.
    """
    if type(pid) is not int or pid <= 0:
        raise ValueError("positive PID required")
    if type(object_id) is not int or not 0 <= object_id <= 1_000_000:
        raise ValueError("invalid Object ID")
    if type(client_x) is not int or type(client_y) is not int or min(client_x, client_y) < 0:
        raise ValueError("nonnegative client coordinates required")
    if type(interval_ms) is not int or not 50 <= interval_ms <= 1000:
        raise ValueError("interval_ms must be 50..1000")
    if type(duration_ms) is not int or not interval_ms <= duration_ms <= 5000:
        raise ValueError("duration_ms must be between interval_ms and 5000")
    # Validate all thresholds before any input.
    movement_threshold = _positive_number(movement_threshold, "movement_threshold")
    stationary_epsilon = _positive_number(stationary_epsilon, "stationary_epsilon", allow_zero=True)
    if type(stationary_samples) is not int or not 2 <= stationary_samples <= 25:
        raise ValueError("stationary_samples must be between 2 and 25")
    if armed is not True or offline_confirmed is not True:
        raise DispatchGuardError("Explicit arm and offline confirmation required")
    if not getattr(api, "allow_candidates", False):
        raise DispatchGuardError("Candidate opt-in required")

    clock = time.monotonic if clock is None else clock
    sleep = time.sleep if sleep is None else sleep
    sender = right_click_client if sender is None else sender
    selected = _selection_id(api, object_id)
    original = api.get_object_by_id(object_id)
    if original is None or original.owner_address is None:
        raise DispatchGuardError("Object missing or candidate owner unknown")
    initial = _identity_position(api, object_id, original)
    x0, y0 = _point(initial)
    _selection_id(api, object_id)  # pre-dispatch guard
    sender(pid, client_x, client_y)
    start = clock()

    samples = [{"elapsed_ms": 0.0, "candidate_world_x": x0,
                "candidate_world_y": y0}]
    observations = []
    deadlines = list(range(interval_ms, duration_ms + 1, interval_ms))
    if deadlines[-1] != duration_ms:
        deadlines.append(duration_ms)
    blocked = None
    for deadline in deadlines:
        remaining = deadline / 1000.0 - (clock() - start)
        if remaining > 0:
            sleep(remaining)
        elapsed = (clock() - start) * 1000
        try:
            selection = _selection_id(api, object_id)
            position = _identity_position(api, object_id, original)
            x, y = _point(position)
            samples.append({"elapsed_ms": elapsed, "candidate_world_x": x,
                            "candidate_world_y": y})
            observations.append({"deadline_ms": deadline, "elapsed_ms": elapsed,
                                 "selection_consistency": selection["consistency"],
                                 "status": "candidate_observed"})
        except (ObjectAPIError, DispatchGuardError, OSError, ValueError, KeyError) as exc:
            blocked = str(exc)
            observations.append({"deadline_ms": deadline, "elapsed_ms": elapsed,
                                 "status": "observation_blocked", "reason": blocked})
            break
    # Under injected/test clocks, rejecting non-increasing time is preferable
    # to fabricating velocities; a real monotonic clock is strictly progressing.
    try:
        metrics = movement_metrics(samples, movement_threshold=movement_threshold,
                                   stationary_epsilon=stationary_epsilon,
                                   stationary_samples=stationary_samples)
    except ValueError as exc:
        blocked = str(exc)
        metrics = None
    status = ("observation_blocked" if blocked else
              "movement_observed" if metrics["movement_observed"] else
              "stationary_observed" if metrics["stationary_observed"] else
              "no_significant_movement_observed")
    return {"schema": SCHEMA, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "pid": pid, "object_id": object_id,
            "target_client": {"x": client_x, "y": client_y},
            "initial_selection": selected, "position_before": initial,
            "observations": observations, "metrics": metrics,
            "status": status, "observation_error": blocked,
            "dispatch": "one_windows_right_click_attempted",
            "game_command_accepted": "unknown",
            "direct_object_id_command": False, "causality": "unproven",
            "arrival_status": "arrival_unverified", "memory_write": False,
            "candidate_fields": ["Object+0x3C", "Object+0x40"],
            "note": "No validated screen-to-world target. Stop is not arrival; movement is not proof of command acceptance."}
