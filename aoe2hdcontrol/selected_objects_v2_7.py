"""v2.7: read-only, candidate-guided selection consistency snapshots.

Compares complete pointer vectors before/after object validation. This is not an
atomic transaction and cannot prove completeness or absence of ABA changes.
"""
from __future__ import annotations
import struct
from .object_api import ObjectAPIError
from .selected_objects_v2_6 import LIST_OFFSET, COUNT_OFFSET, MAX_SELECTED, FLAG


def inspect_selection(api):
    if not getattr(api, "allow_candidates", False):
        raise ObjectAPIError("v2.7 requires allow_candidates")
    player = api.get_assigned_player()
    counts, snapshots = [], []

    def count():
        value = api._read(player.address + COUNT_OFFSET, "I")
        counts.append(value)
        if type(value) is not int or not 0 <= value <= MAX_SELECTED:
            return None
        return value

    def vector(n):
        raw = api.reader.read(player.address + LIST_OFFSET, n * 4) if n else b""
        if len(raw) != n * 4:
            raise ObjectAPIError("Short selection vector read")
        result = list(struct.unpack("<" + "I" * n, raw)) if n else []
        snapshots.append(result)
        return result

    n = count()
    if n is None:
        return _report(player, counts, snapshots, "invalid_count")
    first = vector(n)
    middle = count()
    if middle is None:
        return _report(player, counts, snapshots, "invalid_count")
    if middle != n:
        return _report(player, counts, snapshots, "counter_changed")
    second = vector(n)
    before_validation = count()
    if before_validation is None:
        return _report(player, counts, snapshots, "invalid_count")
    if before_validation != n:
        return _report(player, counts, snapshots, "counter_changed")
    if first != second:
        return _report(player, counts, snapshots, "selection_changed")

    entries, objects, anomalies, seen = [], [], [], set()
    for i, pointer in enumerate(second):
        item = {"index": i, "offset": f"0x{LIST_OFFSET + 4*i:03X}",
                "pointer": pointer, "status": "unverified"}
        if pointer < 0x10000 or pointer > 0xFFFFFFC0 or pointer % 4:
            item["status"] = "invalid_pointer"
        else:
            try:
                oid = api._read(pointer + 0x08, "I")
                item["object_id_candidate"] = oid
                if type(oid) is not int or not 0 <= oid <= 1000000:
                    item["status"] = "invalid_id"
                else:
                    obj = api.get_object_by_id(oid)
                    if obj is None or obj.address != pointer:
                        item["status"] = "object_table_mismatch"
                    else:
                        word = api._read(pointer + 0x38, "I")
                        item["selection_word"] = word
                        if not word & FLAG:
                            item["status"] = "selection_bit_inactive"
                        elif oid in seen:
                            item["status"] = "duplicate"
                        else:
                            item["status"] = "selected_verified"
                            seen.add(oid)
                            objects.append({"object_id": oid, "address": pointer,
                                            "class_id": obj.class_id,
                                            "genie_type_id": obj.genie_type_id})
            except (ObjectAPIError, OSError, ValueError) as exc:
                item["status"] = "read_error"
                item["error"] = str(exc)
        entries.append(item)
        if item["status"] != "selected_verified":
            anomalies.append(item)
    after_validation = count()
    if after_validation is None:
        return _report(player, counts, snapshots, "invalid_count", entries, anomalies)
    if after_validation != n:
        return _report(player, counts, snapshots, "counter_changed", entries, anomalies)
    final = vector(n)
    final_count = count()
    if final_count is None:
        return _report(player, counts, snapshots, "invalid_count", entries, anomalies)
    if final_count != n:
        return _report(player, counts, snapshots, "counter_changed", entries, anomalies)
    if final != first:
        return _report(player, counts, snapshots, "selection_changed", entries, anomalies)
    if anomalies or len(objects) != n:
        return _report(player, counts, snapshots, "invalid_entries", entries, anomalies)
    return _report(player, counts, snapshots, "stable_with_candidate_count",
                   entries, anomalies, objects)


def _report(player, counts, snapshots, consistency, entries=None, anomalies=None, objects=None):
    valid = consistency == "stable_with_candidate_count"
    return {"schema": "hd-selected-v2.7", "consistency": consistency,
            "player_address": player.address, "local_slot": player.slot,
            "counter_observations": counts, "pointer_snapshots": snapshots,
            "pointer_vectors_stable": len(snapshots) == 3 and all(s == snapshots[0] for s in snapshots),
            "selected_count_verified": len(objects) if valid else None,
            "selected_objects": objects if valid else [],
            "entries": entries or [], "anomalies": anomalies or [],
            "completeness": "unknown",
            "note": "Candidate offsets; non-atomic reads; same-length ABA changes may be missed."}


def get_selected_objects(api):
    return tuple(inspect_selection(api)["selected_objects"])


def get_selected_count(api):
    return inspect_selection(api)["selected_count_verified"]
