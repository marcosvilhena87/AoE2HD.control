"""v3.2 — read-only unit candidate position and cursor coordinate observations.

Mouse client coordinates are NOT game-world coordinates. Do not infer any
in-game cursor pointer without a separately validated mapping.
"""
from __future__ import annotations
import ctypes
import math
import os
import time
from ctypes import wintypes
from .object_api import ObjectAPIError

def probe_unit_position(api, object_id):
    if not getattr(api, "allow_candidates", False):
        raise ObjectAPIError("allow_candidates required for candidate offsets")
    obj = api.get_object_by_id(object_id)
    if obj is None:
        raise ObjectAPIError("object not found")
    x = api._read(obj.address + 0x3C, "f")
    y = api._read(obj.address + 0x40, "f")
    finite = math.isfinite(x) and math.isfinite(y)
    return {"object_id": object_id, "address":obj.address,
            "class_id":obj.class_id, "genie_type_id":obj.genie_type_id,
            "candidate_world_x":x if finite else None,
            "candidate_world_y":y if finite else None,
            "finite":finite, "candidate_offsets":["Object+0x3C","Object+0x40"],
            "validated_world_position":False}

def read_cursor_coordinates(pid):
    """Inspect Windows cursor and active game's client-space coordinates."""
    if os.name != "nt":
        raise RuntimeError("Windows required")
    u = ctypes.WinDLL("user32", use_last_error=True)
    hwnd = u.GetForegroundWindow()
    owner = wintypes.DWORD()
    u.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
    if not hwnd or owner.value != pid:
        return {"game_foreground": False, "screen":None, "client":None}
    pos = wintypes.POINT()
    if not u.GetCursorPos(ctypes.byref(pos)):
        raise OSError(ctypes.get_last_error(), "GetCursorPos failed")
    screen = {"x":pos.x,"y":pos.y}
    if not u.ScreenToClient(hwnd, ctypes.byref(pos)):
        raise OSError(ctypes.get_last_error(), "ScreenToClient failed")
    return {"game_foreground":True, "screen":screen,
            "client":{"x":pos.x,"y":pos.y}}

def capture_position_cursor_series(api, *, pid, object_id,
                                   samples=12, interval=0.5,
                                   cursor_reader=None, sleep=None):
    if type(pid) is not int or pid <= 0:
        raise ValueError("positive PID required")
    if type(samples) is not int or not 1 <= samples <= 60:
        raise ValueError("samples must be 1..60")
    if not isinstance(interval,(int,float)) or not 0.05 <= interval <= 5:
        raise ValueError("interval must be between 0.05 and 5 seconds")
    if type(object_id) is not int or not 0 <= object_id <= 1000000:
        raise ValueError("invalid object id")
    cursor_reader = cursor_reader or read_cursor_coordinates
    sleep = sleep or time.sleep
    readings=[]
    for i in range(samples):
        unit=probe_unit_position(api,object_id)
        cursor=cursor_reader(pid)
        readings.append({"sample":i+1,"unit":unit,"cursor":cursor})
        if i+1 < samples:
            sleep(interval)
    return {"schema":"hd-position-cursor-probe-v3.2","pid":pid,
            "object_id":object_id,"readings":readings,
            "game_cursor_world_coordinates":"unknown",
            "selection_dispatch":"not_dispatched","memory_write":False,
            "note":"Windows cursor screen/client position is not a game-world pointer. Candidate unit offsets remain unvalidated."}
