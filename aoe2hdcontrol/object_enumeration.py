"""Bounded experimental ID probing, independent from GUI selection.

The object table's capacity is NOT established. A user-supplied ID interval is
a probe window, never an assertion that the table contains those entries.
Read-only; suspicious entries are rejected rather than used as objects.
"""
from __future__ import annotations

from dataclasses import asdict
from .object_api import ObjectAPIError

MAX_WINDOW = 256
SUPPORTED_CLASSES = frozenset((3, 4, 6))


def enumerate_known_id_window(api, *, start_id: int, stop_id: int,
                              class_id: int | None = None,
                              genie_type_id: int | None = None,
                              own_only: bool = True) -> dict:
    """Probe [start_id, stop_id) with strict bounds and candidate opt-in.

    Fail closed on unresolved ownership when own_only=True. Results are
    snapshots and may become stale immediately.
    """
    if not getattr(api, "allow_candidates", False):
        raise ObjectAPIError("ID probing requires allow_candidates=True")
    if (type(start_id) is not int or type(stop_id) is not int
            or start_id < 0 or stop_id <= start_id
            or stop_id > 1_000_001 or stop_id - start_id > MAX_WINDOW):
        raise ValueError("Invalid ID window; maximum 256 IDs per probe")
    if class_id is not None and class_id not in SUPPORTED_CLASSES:
        raise ValueError("Unsupported class filter")
    if genie_type_id is not None and (type(genie_type_id) is not int
                                      or not 0 <= genie_type_id <= 65535):
        raise ValueError("Invalid Genie Type ID")

    player = api.get_assigned_player() if own_only else None
    objects, rejected = [], []
    for oid in range(start_id, stop_id):
        try:
            obj = api.get_object_by_id(oid)
        except (ObjectAPIError, OSError, ValueError) as exc:
            rejected.append({"object_id": oid, "reason": type(exc).__name__})
            continue
        if obj is None:
            continue
        if obj.class_id not in SUPPORTED_CLASSES:
            rejected.append({"object_id": oid, "reason": "unknown_class"})
            continue
        if obj.genie_type_id is None:
            rejected.append({"object_id": oid, "reason": "unresolved_type"})
            continue
        if own_only and obj.owner_address != player.address:
            rejected.append({"object_id": oid, "reason": "owner_mismatch_or_unknown"})
            continue
        if class_id is not None and obj.class_id != class_id:
            continue
        if genie_type_id is not None and obj.genie_type_id != genie_type_id:
            continue
        objects.append({"object_id": obj.object_id, "class_id": obj.class_id,
                        "genie_type_id": obj.genie_type_id,
                        "owner_address": obj.owner_address})
    return {"schema": "hd-object-id-window-v1", "start_id": start_id,
            "stop_id_exclusive": stop_id, "own_only": own_only,
            "objects": objects, "rejected": rejected,
            "coverage": "explicit_id_window_only",
            "completeness": "unknown",
            "read_only": True,
            "warning": "Global table capacity and ID reuse are unverified; "
                       "do not treat this as global enumeration."}
