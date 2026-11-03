"""v3.4 — one guarded screen-target movement experiment for AoE II HD.

This is NOT a direct UnitsMove API. It verifies a candidate-selected Object ID,
sends one ordinary Windows right-click and samples candidate position offsets.
Never writes game memory and never promotes movement or causality to validated.
"""
from __future__ import annotations

import ctypes
import math
import os
import time
from ctypes import wintypes

from .object_api import ObjectAPIError
from .position_cursor_probe_v3_2 import probe_unit_position
from .selected_objects_v2_7 import inspect_selection
from .selection_coordinate_v3_1 import DispatchGuardError

SCHEMA = "hd-guarded-movement-v3.4"


def _foreground_client(pid, x, y):
    if os.name != "nt":
        raise DispatchGuardError("Windows only")
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.GetForegroundWindow.restype = wintypes.HWND
    hwnd = user.GetForegroundWindow()
    owner = wintypes.DWORD()
    if not hwnd or not user.GetWindowThreadProcessId(hwnd, ctypes.byref(owner)) or owner.value != pid:
        raise DispatchGuardError("AoK HD is not the foreground process")
    rect = wintypes.RECT()
    if not user.GetClientRect(hwnd, ctypes.byref(rect)):
        raise DispatchGuardError("GetClientRect failed")
    if not (0 <= x < rect.right and 0 <= y < rect.bottom):
        raise DispatchGuardError("Target outside game client")
    point = wintypes.POINT(x, y)
    if not user.ClientToScreen(hwnd, ctypes.byref(point)):
        raise DispatchGuardError("ClientToScreen failed")
    return user, hwnd, point


def right_click_client(pid, x, y):
    """Exactly one paired right-click via SendInput; (x,y) are CLIENT pixels."""
    user, hwnd, point = _foreground_client(pid, x, y)
    if not user.SetCursorPos(point.x, point.y):
        raise DispatchGuardError("SetCursorPos failed")
    # Protect against focus changes between coordinate lookup and dispatch.
    if user.GetForegroundWindow() != hwnd:
        raise DispatchGuardError("Foreground changed before dispatch")
    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]
    class INPUTUNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]
    class INPUT(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = [("type", wintypes.DWORD), ("u", INPUTUNION)]
    RIGHTDOWN, RIGHTUP = 0x0008, 0x0010
    events = (INPUT * 2)(
        INPUT(0, INPUTUNION(mi=MOUSEINPUT(0, 0, 0, RIGHTDOWN, 0, 0))),
        INPUT(0, INPUTUNION(mi=MOUSEINPUT(0, 0, 0, RIGHTUP, 0, 0))))
    if user.SendInput(2, ctypes.byref(events), ctypes.sizeof(INPUT)) != 2:
        raise DispatchGuardError("SendInput did not deliver both right-button events")


def _selection_id(api, object_id):
    snapshot = inspect_selection(api)
    ids = [item["object_id"] for item in snapshot.get("selected_objects", [])]
    if snapshot.get("consistency") != "stable_with_candidate_count" or ids != [object_id]:
        raise DispatchGuardError("Expected sole selected Object ID is not stable")
    return snapshot


def _identity_position(api, object_id, original):
    current = api.get_object_by_id(object_id)
    if current is None or current.address != original.address or (
        current.owner_address != original.owner_address or
        current.genie_type_id != original.genie_type_id or
        current.class_id != original.class_id
    ):
        raise ObjectAPIError("Object identity changed during experiment")
    position = probe_unit_position(api, object_id)
    if not position["finite"] or position["candidate_world_x"] is None or position["candidate_world_y"] is None:
        raise ObjectAPIError("Candidate position is not finite")
    return position


def experiment(api, *, pid, object_id, client_x, client_y, armed=False,
               offline_confirmed=False, intervals_ms=(200, 500, 1000),
               threshold=0.25, sender=None, clock=None, sleep=None):
    """One order attempt and independent observations; no retries.

    The caller must explicitly attest local/offline mode. In-game proof of
    single-player status, target tile legality and actual command acceptance
    remain unavailable. Production-like automation must not use this result.
    """
    if type(pid) is not int or pid <= 0:
        raise ValueError("positive PID required")
    if type(object_id) is not int or not 0 <= object_id <= 1000000:
        raise ValueError("invalid Object ID")
    if any(type(v) is not int or v < 0 for v in (client_x, client_y)):
        raise ValueError("nonnegative integer client coordinates required")
    if not isinstance(intervals_ms, (tuple, list)) or not intervals_ms or len(intervals_ms) > 20 or (
        any(type(v) is not int or not 1 <= v <= 10000 for v in intervals_ms)
    ) or list(intervals_ms) != sorted(set(intervals_ms)):
        raise ValueError("invalid observation deadlines")
    if not isinstance(threshold, (float, int)) or isinstance(threshold, bool) or (
        not math.isfinite(threshold) or threshold <= 0
    ):
        raise ValueError("invalid movement threshold")
    if armed is not True or offline_confirmed is not True:
        raise DispatchGuardError("Explicit arm and offline confirmation required")
    if not getattr(api, "allow_candidates", False):
        raise DispatchGuardError("Candidate opt-in required")
    # Simulated senders are reserved for tests. The real sender checks foreground
    # and client bounds before dispatch.
    sender = right_click_client if sender is None else sender
    clock = time.monotonic if clock is None else clock
    sleep = time.sleep if sleep is None else sleep

    before_selection = _selection_id(api, object_id)
    original = api.get_object_by_id(object_id)
    if original is None or original.owner_address is None:
        raise DispatchGuardError("Object missing or candidate owner unknown")
    before = _identity_position(api, object_id, original)
    # Re-read selection immediately before attempting input.
    _selection_id(api, object_id)
    sender(pid, client_x, client_y)
    dispatched_at = clock()
    readings = []
    for deadline in intervals_ms:
        remaining = deadline / 1000 - (clock() - dispatched_at)
        if remaining > 0:
            sleep(remaining)
        elapsed = round((clock() - dispatched_at) * 1000, 3)
        try:
            selection = _selection_id(api, object_id)
            position = _identity_position(api, object_id, original)
            dx = position["candidate_world_x"] - before["candidate_world_x"]
            dy = position["candidate_world_y"] - before["candidate_world_y"]
            distance = math.hypot(dx, dy)
            readings.append({"deadline_ms": deadline, "elapsed_ms": elapsed,
                             "selection_consistency": selection["consistency"],
                             "position": position, "distance_candidate": distance,
                             "movement_candidate": distance >= threshold,
                             "status": "candidate_observed"})
        except (ObjectAPIError, DispatchGuardError, OSError, ValueError) as exc:
            readings.append({"deadline_ms": deadline, "elapsed_ms": elapsed,
                             "status": "observation_blocked", "reason": str(exc)})
            break
    moved = any(r.get("movement_candidate") for r in readings)
    interrupted = any(r["status"] == "observation_blocked" for r in readings)
    return {"schema": SCHEMA, "pid": pid, "object_id": object_id,
            "target_client": {"x": client_x, "y": client_y},
            "selected_before": before_selection, "position_before": before,
            "observations": readings,
            "status": ("observation_blocked" if interrupted else
                       "candidate_displacement_observed" if moved else "no_displacement_observed"),
            "dispatch": "one_windows_right_click_attempted",
            "direct_object_id_command": False, "game_command_accepted": "unknown",
            "causality": "unproven", "world_destination": "unknown",
            "validated_world_position": False, "memory_write": False,
            "note": "Selection and position use candidate memory layouts; movement may be unrelated to click."}
