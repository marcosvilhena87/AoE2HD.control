"""v2.9: auditable unit ID -> selection -> command -> observation contract.

This module deliberately contains NO process-write or input-simulation backend.
The HD mapping has not validated a command dispatcher or unit position getter.
A caller may inject a *verified* offline/local transport in future; the default
transport refuses every request. No observed selection implies causality.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

from .object_api import ObjectAPIError
from .selected_objects_v2_7 import inspect_selection
from .selected_objects_v2_8 import make_selection_intent

SCHEMA = "hd-unit-cycle-v2.9"


@dataclass(frozen=True)
class MoveRequest:
    object_ids: tuple[int, ...]
    destination: tuple[float, float]
    session: str


class CommandTransport(Protocol):
    def dispatch_move(self, request: MoveRequest) -> bool: ...


class DisabledTransport:
    """Safe default: no validated HD command dispatcher exists."""

    def dispatch_move(self, request: MoveRequest) -> bool:
        raise ObjectAPIError("HD movement dispatch is not validated; command refused")


def make_move_request(object_ids, destination, *, session: str) -> MoveRequest:
    ids = tuple(make_selection_intent(object_ids)["object_ids"])
    if not isinstance(session, str) or not session.strip() or len(session) > 128:
        raise ValueError("A nonempty session name (up to 128 chars) is required")
    if (not isinstance(destination, (list, tuple)) or len(destination) != 2
            or any(type(x) not in (int, float) or not math.isfinite(x) for x in destination)):
        raise ValueError("Destination requires two finite numeric coordinates")
    return MoveRequest(ids, (float(destination[0]), float(destination[1])), session)


def identify(api, request: MoveRequest) -> dict:
    """Read only; verify every ID and owner candidate, fail closed."""
    if not getattr(api, "allow_candidates", False):
        raise ObjectAPIError("Candidate readings require explicit opt-in")
    player = api.get_assigned_player()
    records = []
    for object_id in request.object_ids:
        obj = api.get_object_by_id(object_id)
        if obj is None:
            raise ObjectAPIError(f"Object {object_id} not found")
        if obj.owner_address != player.address:
            raise ObjectAPIError(f"Object {object_id} owner not confirmed as local player")
        records.append({"object_id": object_id, "address_candidate": obj.address,
                        "genie_type_id_candidate": obj.genie_type_id,
                        "class_id": obj.class_id})
    return {"schema": SCHEMA, "stage": "identified_candidate",
            "session": request.session, "objects": records,
            "local_player_address_candidate": player.address,
            "completeness": "unknown"}


def observe_selection(api, request: MoveRequest) -> dict:
    """Observe selected IDs; never claim this function selected them."""
    report = inspect_selection(api)
    observed = [item["object_id"] for item in report["selected_objects"]]
    stable = report["consistency"] == "stable_with_candidate_count"
    matches = stable and len(observed) == len(request.object_ids) and (
        set(observed) == set(request.object_ids))
    return {"schema": SCHEMA, "stage": "selection_observed",
            "session": request.session, "requested_ids": list(request.object_ids),
            "observed_ids": observed if stable else [],
            "snapshot_consistency": report["consistency"],
            "matches": bool(matches), "selection_dispatched": False,
            "causality": "not_established", "completeness": "unknown"}


def dispatch_move(request: MoveRequest, *, transport: CommandTransport | None = None,
                  offline_confirmed: bool = False, selection: dict | None = None) -> dict:
    """Fail closed until an explicitly supplied, validated local transport exists.

    A transport's True return is an ACK only; it cannot establish movement.
    """
    if not offline_confirmed:
        raise ObjectAPIError("Movement requires explicit offline/local confirmation")
    if (not isinstance(selection, dict) or selection.get("schema") != SCHEMA
            or selection.get("session") != request.session
            or selection.get("requested_ids") != list(request.object_ids)
            or selection.get("matches") is not True
            or selection.get("snapshot_consistency") != "stable_with_candidate_count"):
        raise ObjectAPIError("Current matching selection observation is required")
    driver = transport if transport is not None else DisabledTransport()
    accepted = driver.dispatch_move(request)
    if type(accepted) is not bool:
        raise ObjectAPIError("Transport must return explicit boolean acknowledgment")
    return {"schema": SCHEMA, "stage": "command_submitted",
            "session": request.session, "requested_ids": list(request.object_ids),
            "destination": list(request.destination), "accepted": accepted,
            "executed": "unverified", "movement": "unverified"}


def verify_observed_movement(request: MoveRequest, command: dict,
                             before: dict, after: dict, *, tolerance: float = 0.5) -> dict:
    """Compare independent position readings keyed by session Object ID.

    Positions are external evidence, NOT provided by current HDObjectAPI.
    The result demonstrates observed displacement, never command causality.
    """
    if (not isinstance(command, dict) or command.get("schema") != SCHEMA
            or command.get("session") != request.session
            or command.get("requested_ids") != list(request.object_ids)
            or command.get("destination") != list(request.destination)
            or command.get("accepted") is not True):
        raise ValueError("Matching accepted command receipt required")
    if type(tolerance) not in (int, float) or not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("Invalid tolerance")
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise ValueError("Position snapshots must be mappings")
    observed = []
    for oid in request.object_ids:
        p, q = before.get(oid), after.get(oid)
        if p is None or q is None:
            return {"schema": SCHEMA, "status": "unverified",
                    "reason": "missing_position_evidence", "executed": "unverified"}
        for v in (p, q):
            if (not isinstance(v, (tuple, list)) or len(v) != 2
                    or any(type(c) not in (int, float) or not math.isfinite(c) for c in v)):
                raise ValueError("Invalid position evidence")
        displacement = math.dist(p, q)
        distance_to_target = math.dist(q, request.destination)
        observed.append({"object_id": oid, "displacement": displacement,
                         "distance_to_target": distance_to_target,
                         "arrived_near_target": distance_to_target <= tolerance})
    return {"schema": SCHEMA, "status": "arrival_observed" if all(
        o["arrived_near_target"] for o in observed) else "not_yet_observed",
            "objects": observed, "executed": "unverified",
            "causality": "not_established", "position_source": "external_unverified"}
