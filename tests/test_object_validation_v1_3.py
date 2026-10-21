"""Testes offline da observacao temporal v1.3."""
import unittest
from unittest.mock import patch
from aoe2hdcontrol.object_api import HDObject, ObjectAPIError
from aoe2hdcontrol.object_validation_v1_3 import collect, capture_series


class Stub:
    allow_candidates = True
    def __init__(self):
        self.objects = {
            2180: HDObject(2180, 0x150000, 3, 109, 0x200000, None, ()),
            2181: HDObject(2181, 0x151000, 3, 618, 0x200000, None, ()),
            2188: HDObject(2188, 0x152000, 3, 620, 0x210000, None, ()),
            2190: HDObject(2190, 0x153000, 4, 83, 0x200000, None, ()),
        }
    def get_object_by_id(self, oid):
        return self.objects.get(oid)
    def _read(self, addr, fmt):
        return {0x15003C: 10.0, 0x150040: 20.0,
                0x15103C: 11.0, 0x151040: 20.0,
                0x15203C: 40.0, 0x152040: 50.0}[addr]


class TestV13(unittest.TestCase):
    @patch("aoe2hdcontrol.object_validation_v1_3._players",
           return_value=(1, {0x200000: 1, 0x210000: 2}))
    def test_owner_type_position_and_distances(self, unused):
        result = collect(Stub(), 2180, 2190, positions=True)
        self.assertEqual([o["object_id"] for o in result["objects"]], [2180, 2181, 2188])
        self.assertEqual(result["objects"][0]["distances"]["2181"], 1)
        self.assertEqual(result["objects"][2]["owner_slot"], 2)
        self.assertEqual(result["errors"], [])

    @patch("aoe2hdcontrol.object_validation_v1_3._players",
           return_value=(1, {0x200000: 1, 0x210000: 2}))
    def test_temporal_snapshots(self, unused):
        result = capture_series(Stub(), 2180, 2188, samples=2, interval=0, sleep=lambda _: None)
        self.assertEqual(len(result["samples"]), 2)
        self.assertEqual(len(result["by_object_id"]["2180"]), 2)
        self.assertIsNone(result["samples"][0]["objects"][0]["candidate_position"])

    def test_reject_bad_arguments(self):
        with self.assertRaises(ValueError):
            collect(Stub(), 0, 512)
        with self.assertRaises(ValueError):
            capture_series(Stub(), 1, 2, samples=21)
        obj = Stub()
        obj.allow_candidates = False
        with self.assertRaises(ObjectAPIError):
            collect(obj, 2180, 2180)

if __name__ == "__main__":
    unittest.main()
