"""v3.3.3 — read-only A-B-A visual correspondence diagnostics."""
from __future__ import annotations
import math

def _xy(mapping, keys):
    try:
        values = [float(mapping[k]) for k in keys]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("missing or invalid coordinates") from exc
    if not all(math.isfinite(v) for v in values):
        raise ValueError("nonfinite coordinates")
    return values

def _distance(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

def audit_aba(first, middle, last, *, cursor_tolerance_px=15.0, world_tolerance=0.02):
    """Compare A-B-A with no inferred camera movement or object association."""
    if not 0 <= cursor_tolerance_px <= 1000 or not 0 <= world_tolerance <= 100:
        raise ValueError("invalid tolerances")
    records = (first, middle, last)
    for record in records:
        if record.get("schema") != "hd-synchronized-anchor-v3.3.2":
            raise ValueError("expected synchronized anchor v3.3.2")
        if not record.get("usable"):
            raise ValueError("inconclusive input anchor")
    if first.get("object_id") != last.get("object_id"):
        raise ValueError("first and last Object ID must match")
    if len({r.get("pid") for r in records}) != 1:
        raise ValueError("different process IDs")
    def world(r):
        return _xy(r["unit"], ("candidate_world_x", "candidate_world_y"))
    def screen(r):
        return _xy(r["cursor_after"]["client"], ("x", "y"))
    world_change = _distance(world(first), world(last))
    cursor_change = _distance(screen(first), screen(last))
    camera_known = all(r.get("camera_verified_stationary") is True for r in records)
    warnings = []
    if world_change > world_tolerance:
        warnings.append("world_position_changed")
    if cursor_change > cursor_tolerance_px:
        warnings.append("cursor_position_changed_between_A_captures")
    if not camera_known:
        warnings.append("camera_stationarity_not_verified")
    warnings.append("cursor_to_object_visual_correspondence_not_verified")
    # A stationary world object with cursor drift does not prove camera movement.
    return {"schema":"hd-visual-correspondence-audit-v3.3.3",
            "object_id":first["object_id"],"middle_object_id":middle["object_id"],
            "pid":first["pid"],
            "world_delta":{"x":world(last)[0]-world(first)[0],
                           "y":world(last)[1]-world(first)[1],
                           "distance":world_change},
            "cursor_delta_px":{"x":screen(last)[0]-screen(first)[0],
                               "y":screen(last)[1]-screen(first)[1],
                               "distance":cursor_change},
            "tolerances":{"cursor_px":cursor_tolerance_px,"world":world_tolerance},
            "window_context":{"first_ms":first.get("observation_window_ms"),
                              "middle_ms":middle.get("observation_window_ms"),
                              "last_ms":last.get("observation_window_ms")},
            "warnings":warnings,
            "camera_movement":"unknown",
            "visual_correspondence":"unverified",
            "status":"inconclusive" if warnings else "candidate_repeatable",
            "dispatch":"not_dispatched",
            "note":"Cursor positions cannot establish camera movement or object identity; inspect screenshots/manual target confirmation."}
