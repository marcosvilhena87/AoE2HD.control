"""Selected Objects API v2.7: repeated identity-aware, read-only observations.

Two successful v2.6 observations must agree on ordered (ID, address) pairs.
Not an atomic snapshot and not proof of global completeness.
"""
from __future__ import annotations

from .object_api import ObjectAPIError
from .selected_objects_v2_6 import inspect_selection as inspect_v26


def inspect_selection(api):
    if not getattr(api, "allow_candidates", False):
        raise ObjectAPIError("v2.7 requires allow_candidates")
    first = inspect_v26(api)
    second = inspect_v26(api)
    reports = (first, second)
    valid = all(r["consistency"] == "consistent_with_candidate_count" for r in reports)
    def fingerprint(report):
        return tuple((obj["object_id"], obj["address"]) for obj in report["selected_objects"])
    same = valid and fingerprint(first) == fingerprint(second)
    if not valid:
        consistency = "unstable_or_invalid_observation"
    elif not same:
        consistency = "selection_changed_same_or_different_count"
    else:
        consistency = "repeated_observations_agree"
    return {
        "schema": "hd-selected-v2.7",
        "consistency": consistency,
        "selected_objects": first["selected_objects"] if same else [],
        "selected_count_verified": len(first["selected_objects"]) if same else None,
        "observed_counts": [r.get("count_before") for r in reports],
        "observations": list(reports),
        "completeness": "unknown",
        "atomic": False,
        "note": "Agreement in two sequential reads is not an atomic snapshot; ABA changes may go undetected. Candidate offsets only.",
    }


def get_selected_objects(api):
    return tuple(inspect_selection(api)["selected_objects"])


def get_selected_count(api):
    return inspect_selection(api)["selected_count_verified"]
