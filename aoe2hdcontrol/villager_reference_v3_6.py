"""v3.6: compare moving villager A against static villager B, candidate coordinates.

Uses one guarded v3.5 screen click, not a native move-to-object command.
"""
from __future__ import annotations
import math
from .movement_v3_4 import _identity_position, _selection_id
from .movement_v3_5 import monitor, _point
from .object_api import ObjectAPIError
from .selection_coordinate_v3_1 import DispatchGuardError

SCHEMA = "hd-villager-reference-v3.6"


def compare_reference(result, before_a, before_b, after_b, *,
                      tolerance=1.0, reference_stability=0.10):
    """Compare reference target against final observed A, never certify arrival."""
    if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool) or not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("invalid tolerance")
    if not isinstance(reference_stability, (int, float)) or isinstance(reference_stability, bool) or not math.isfinite(reference_stability) or reference_stability < 0:
        raise ValueError("invalid reference_stability")
    a0 = _point(before_a)
    b0 = _point(before_b)
    b1 = _point(after_b)
    samples = (result.get("metrics") or {}).get("samples") or []
    if not samples:
        return {"status":"observation_blocked","reason":"no_valid_mover_samples",
                "arrival_status":"arrival_unverified"}
    last = samples[-1]
    a1 = (float(last["x"]),float(last["y"]))
    initial = math.dist(a0,b0)
    final = math.dist(a1,b1)
    drift = math.dist(b0,b1)
    reference_stationary = drift <= reference_stability
    observations_complete = result.get("status") != "observation_blocked"
    near = final <= tolerance
    stopped = bool((result.get("metrics") or {}).get("stationary_observed"))
    return {"status": ("candidate_proximity_observed" if
                       observations_complete and reference_stationary and near and stopped
                       else "reference_moved" if not reference_stationary
                       else "observation_blocked" if not observations_complete
                       else "proximity_not_observed"),
            "initial_distance_candidate":initial,
            "final_distance_candidate":final,
            "reference_displacement_candidate":drift,
            "distance_reduction_candidate":initial-final,
            "candidate_proximity":near,
            "reference_stationary_candidate":reference_stationary,
            "mover_stationary_candidate":stopped,
            "tolerance_candidate":float(tolerance),
            "arrival_status":"arrival_unverified",
            "note":"Object proximity is not proof of arrival at the clicked screen position."}


def experiment(api, *, pid, mover_id, reference_id, client_x, client_y,
               armed=False, offline_confirmed=False, tolerance=1.0,
               reference_stability=0.10, **monitor_options):
    """Target B is measured by ID; operator chooses free client ground near B.

    Both must have the same candidate owner. B is never selected or commanded.
    Returns a report even when post-command observations are blocked.
    """
    if type(mover_id) is not int or type(reference_id) is not int or (
        mover_id == reference_id or not 0 <= mover_id <= 1_000_000 or
        not 0 <= reference_id <= 1_000_000
    ):
        raise ValueError("two distinct valid Object IDs required")
    if armed is not True or offline_confirmed is not True:
        raise DispatchGuardError("Explicit arm and offline confirmation required")
    if not getattr(api,"allow_candidates",False):
        raise DispatchGuardError("Candidate opt-in required")
    # Fail before dispatch if configuration is invalid.
    if not isinstance(tolerance,(int,float)) or isinstance(tolerance,bool) or not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("invalid tolerance")
    if not isinstance(reference_stability,(int,float)) or isinstance(reference_stability,bool) or not math.isfinite(reference_stability) or reference_stability < 0:
        raise ValueError("invalid reference_stability")
    _selection_id(api,mover_id)
    a = api.get_object_by_id(mover_id)
    b = api.get_object_by_id(reference_id)
    if a is None or b is None or a.address == b.address or (
        a.owner_address is None or a.owner_address != b.owner_address
    ):
        raise DispatchGuardError("Distinct owned objects with matching candidate owners required")
    # Only villagers (Genie ID 83) for this bounded experiment.
    if a.genie_type_id != 83 or b.genie_type_id != 83:
        raise DispatchGuardError("Only Genie Type ID 83 tested by this experiment")
    a0 = _identity_position(api,mover_id,a)
    b0 = _identity_position(api,reference_id,b)
    if math.dist(_point(a0),_point(b0)) <= tolerance:
        raise DispatchGuardError("Mover already near reference; choose farther apart units")
    report = monitor(api,pid=pid,object_id=mover_id,client_x=client_x,
                     client_y=client_y,armed=armed,
                     offline_confirmed=offline_confirmed,**monitor_options)
    try:
        b1 = _identity_position(api,reference_id,b)
        comparison = compare_reference(report,a0,b0,b1,tolerance=tolerance,
                                       reference_stability=reference_stability)
    except (ObjectAPIError,DispatchGuardError,OSError,ValueError,KeyError) as exc:
        b1 = None
        comparison = {"status":"observation_blocked","reason":str(exc),
                      "arrival_status":"arrival_unverified"}
    return {"schema":SCHEMA,"pid":pid,"mover_id":mover_id,"reference_id":reference_id,
            "reference_before":b0,"reference_after":b1,
            "movement":report,"comparison":comparison,
            "direct_move_to_object":False,"world_target_verified":False,
            "arrival_status":"arrival_unverified","memory_write":False}
