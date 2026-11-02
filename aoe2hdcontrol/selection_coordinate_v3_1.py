"""v3.1: explicit screen-coordinate assisted selection; never memory writes.

The given Object ID is an expected outcome, NOT a mapped screen position.
"""
from __future__ import annotations
import ctypes
import os
from ctypes import wintypes
from .selected_objects_v2_7 import inspect_selection
from .selected_objects_v2_8 import make_selection_intent

class DispatchGuardError(RuntimeError):
    pass

def click_at(x, y, pid):
    if os.name != "nt":
        raise DispatchGuardError("Windows only")
    user = ctypes.WinDLL("user32", use_last_error=True)
    hwnd = user.GetForegroundWindow()
    owner = wintypes.DWORD(0)
    user.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
    if not hwnd or owner.value != pid:
        raise DispatchGuardError("AoK HD is not the foreground process")
    point = wintypes.POINT(x, y)
    if not user.ScreenToClient(hwnd, ctypes.byref(point)):
        raise DispatchGuardError("ScreenToClient failed")
    rect = wintypes.RECT()
    if not user.GetClientRect(hwnd, ctypes.byref(rect)):
        raise DispatchGuardError("GetClientRect failed")
    if not (0 <= point.x < rect.right and 0 <= point.y < rect.bottom):
        raise DispatchGuardError("Click point is outside foreground client area")
    if not user.SetCursorPos(x, y):
        raise DispatchGuardError("SetCursorPos failed")
    # Mouse input through normal Windows input pipeline, not game memory.
    INPUT_MOUSE = 0
    DOWN, UP = 0x0002, 0x0004
    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]
    class INPUTUNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]
    class INPUT(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = [("type", wintypes.DWORD), ("u", INPUTUNION)]
    presses = (INPUT * 2)(
        INPUT(INPUT_MOUSE, INPUTUNION(mi=MOUSEINPUT(0,0,0,DOWN,0,0))),
        INPUT(INPUT_MOUSE, INPUTUNION(mi=MOUSEINPUT(0,0,0,UP,0,0))))
    if user.SendInput(2, ctypes.byref(presses), ctypes.sizeof(INPUT)) != 2:
        raise DispatchGuardError("SendInput did not deliver both mouse events")

def select_by_screen_point(api, *, pid, object_id, x, y, armed=False, click=None):
    """Attempt one left click and independently verify the selection.

    No retry, no coordinate prediction, no claim of a general Object ID selector.
    """
    make_selection_intent([object_id])
    if not getattr(api, "allow_candidates", False):
        raise DispatchGuardError("candidate opt-in required")
    if type(pid) is not int or pid <= 0:
        raise ValueError("positive PID required")
    if type(x) is not int or type(y) is not int or x < 0 or y < 0:
        raise ValueError("screen x/y must be nonnegative integers")
    if armed is not True:
        raise DispatchGuardError("explicit arm required")
    before = inspect_selection(api)
    if before.get("consistency") != "stable_with_candidate_count":
        raise DispatchGuardError("unstable initial selection")
    sender = click_at if click is None else click
    sender(x,y,pid)
    after = inspect_selection(api)
    stable = after.get("consistency") == "stable_with_candidate_count"
    objects = after.get("selected_objects",[]) if stable else []
    ids = [obj["object_id"] for obj in objects]
    matched = stable and ids == [object_id]
    return {"schema":"hd-coordinate-selection-v3.1","pid":pid,
            "requested_object_id":object_id,"screen_point":{"x":x,"y":y},
            "dispatch":"windows_mouse_click_attempted",
            "before":before,"after":after,"observed_ids":ids,
            "status":"observed_match" if matched else "target_not_observed",
            "match":matched,"causality":"not_proven",
            "completeness":"unknown",
            "note":"A one-time screen click is not Object ID addressing; no game memory write."}
