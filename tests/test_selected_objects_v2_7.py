import struct
import unittest
from aoe2hdcontrol.selected_objects_v2_7 import inspect_selection
from aoe2hdcontrol.object_api import ObjectAPIError

BASE = 0x200000
PLAYER = 0x300000

class Reader:
    def __init__(self, vectors):
        self.vectors = iter(vectors)
    def read(self, address, size):
        vector = next(self.vectors)
        assert len(vector) * 4 == size
        return struct.pack("<" + "I" * len(vector), *vector)

class API:
    allow_candidates = True
    def __init__(self, counts, vectors, bad=False):
        self.counts = iter(counts)
        self.reader = Reader(vectors)
        self.bad = bad
    def get_assigned_player(self):
        return type("Player", (), {"address": PLAYER, "slot": 1})()
    def _read(self, address, fmt):
        if address == PLAYER + 0x254:
            return next(self.counts)
        delta = address - BASE
        if delta % 0x100 == 8:
            return delta // 0x100
        if delta % 0x100 == 0x38:
            return 0 if self.bad else 0x10000
        raise ObjectAPIError("bad read")
    def get_object_by_id(self, oid):
        return type("Obj", (), {"address": BASE + 0x100 * oid,
                                "class_id": 4, "genie_type_id": 83})()

def pointers(*ids):
    return [BASE + 0x100 * i for i in ids]

class Tests(unittest.TestCase):
    def test_empty(self):
        r = inspect_selection(API([0]*5, [[], [], []]))
        self.assertEqual(r["selected_count_verified"], 0)
        self.assertEqual(r["consistency"], "stable_with_candidate_count")
    def test_sixty(self):
        v = pointers(*range(60))
        r = inspect_selection(API([60]*5, [v, v, v]))
        self.assertEqual(r["selected_count_verified"], 60)
        self.assertEqual(r["entries"][-1]["offset"], "0x24C")
    def test_same_count_swap_before_validation(self):
        r = inspect_selection(API([2]*3, [pointers(1,2), pointers(1,3)]))
        self.assertEqual(r["consistency"], "selection_changed")
        self.assertIsNone(r["selected_count_verified"])
    def test_same_count_swap_during_validation(self):
        r = inspect_selection(API([2]*5, [pointers(1,2), pointers(1,2), pointers(1,3)]))
        self.assertEqual(r["consistency"], "selection_changed")
    def test_counter_change(self):
        r = inspect_selection(API([2,3], [pointers(1,2)]))
        self.assertEqual(r["consistency"], "counter_changed")
    def test_invalid_count(self):
        r = inspect_selection(API([61], []))
        self.assertEqual(r["consistency"], "invalid_count")
    def test_flag(self):
        v = pointers(1)
        r = inspect_selection(API([1]*5, [v,v,v], bad=True))
        self.assertEqual(r["consistency"], "invalid_entries")
        self.assertEqual(r["selected_objects"], [])
    def test_opt_in(self):
        api = API([0]*5, [[],[],[]])
        api.allow_candidates = False
        with self.assertRaises(ObjectAPIError):
            inspect_selection(api)
    def test_completeness_unknown(self):
        r = inspect_selection(API([0]*5, [[],[],[]]))
        self.assertEqual(r["completeness"], "unknown")

if __name__ == "__main__":
    unittest.main()
