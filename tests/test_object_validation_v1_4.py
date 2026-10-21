"""Testes offline da descoberta estrutural v1.4."""
import unittest
from unittest.mock import patch
from aoe2hdcontrol.object_api import ObjectAPIError
from aoe2hdcontrol.object_validation_v1_4 import capture, capture_series

DATA = {
    "objects": [
        {"object_id": 2180, "object_address": 0x100000, "owner_slot": 1,
         "genie_type_id": 109, "class_id": 3, "candidate_position": [66, 124]},
        {"object_id": 2181, "object_address": 0x101000, "owner_slot": 1,
         "genie_type_id": 618, "class_id": 3, "candidate_position": [67, 123]},
        {"object_id": 2185, "object_address": 0x102000, "owner_slot": 2,
         "genie_type_id": 109, "class_id": 3, "candidate_position": [53, 25]},
    ],
    "errors": [],
}
class Dummy:
    allow_candidates = True
    def _ptr(self, addr):
        if addr == 0x100010:
            return 0x101000
        if addr == 0x101014:
            return 2180
        return 0

class ValidationTests(unittest.TestCase):
    @patch("aoe2hdcontrol.object_validation_v1_4.collect", return_value=DATA)
    def test_pointer_and_id_candidate_are_distinct(self, mocked):
        shot = capture(Dummy(), 2180, 2185, pointer_window=0x20)
        self.assertIn({"source_id": 2180, "target_id": 2181,
                       "offset": "0x10", "kind": "direct_object_pointer_candidate"},
                      shot["candidate_links"])
        self.assertIn({"source_id": 2181, "target_id": 2180,
                       "offset": "0x14", "kind": "id_value_coincidence"},
                      shot["candidate_links"])
        self.assertEqual(shot["errors"], [])

    @patch("aoe2hdcontrol.object_validation_v1_4.collect", return_value=DATA)
    def test_persistence(self, mocked):
        result = capture_series(Dummy(), 2180, 2185, samples=2, interval=0,
                                pointer_window=0x20, sleep=lambda _: None)
        self.assertEqual(len(result["snapshots"]), 2)
        self.assertTrue(all(l["observed_samples"] == 2 for l in result["link_persistence"]))

    def test_limits(self):
        with self.assertRaises(ValueError):
            capture(Dummy(), 2180, 2185, pointer_window=3)
        with self.assertRaises(ValueError):
            capture_series(Dummy(), 2180, 2185, samples=21)
        d = Dummy()
        d.allow_candidates = False
        with self.assertRaises(ObjectAPIError):
            capture(d, 2180, 2185)

if __name__ == "__main__":
    unittest.main()
