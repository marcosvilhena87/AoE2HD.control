import unittest
from types import SimpleNamespace
from unittest.mock import patch

from aoe2hdcontrol.global_pair_v3_8 import pair_geometry, sample_pair, stage_update
from aoe2hdcontrol.object_api import ObjectAPIError


def point(x, y):
    return {"candidate_world_x": x, "candidate_world_y": y, "finite": True}


class GlobalPairTests(unittest.TestCase):
    def setUp(self):
        self.obj_a = SimpleNamespace(address=111, owner_address=999,
                                     genie_type_id=83, class_id=4)
        self.obj_b = SimpleNamespace(address=222, owner_address=999,
                                     genie_type_id=293, class_id=4)
        self.api = SimpleNamespace(
            allow_candidates=True,
            get_object_by_id=lambda oid: {1: self.obj_a, 2: self.obj_b}.get(oid))

    def read(self, a=(0, 0), b=(3, 4)):
        def fake(api, oid, obj):
            x, y = a if oid == 1 else b
            return point(x, y)
        with patch("aoe2hdcontrol.global_pair_v3_8._selection_id") as selected:
            s = sample_pair(self.api, 1, 2, position_reader=fake)
        self.assertEqual(selected.call_count, 2)
        return s

    def test_geometry(self):
        d = pair_geometry(point(1, 2), point(4, 6))
        self.assertEqual(d["distance_candidate"], 5)
        self.assertEqual(d["unit_vector_candidate"], {"x": 0.6, "y": 0.8})
        self.assertFalse(d["game_heading_validated"])

    def test_zero_direction(self):
        d = pair_geometry(point(1, 1), point(1, 1))
        self.assertIsNone(d["unit_vector_candidate"])

    def test_three_camera_stages(self):
        s = self.read()
        report = None
        for stage in ("1", "2", "3"):
            report = stage_update(report, stage=stage, pid=123,
                                  a_id=1, b_id=2, snapshot=s)
        self.assertEqual(len(report["samples"]), 3)
        self.assertEqual(report["comparisons"][0]["a_drift_candidate"], 0)
        self.assertEqual(report["comparisons"][0]["b_drift_candidate"], 0)
        self.assertFalse(report["world_coordinates_validated"])
        self.assertFalse(report["command_dispatched"])

    def test_out_of_order(self):
        with self.assertRaises(ValueError):
            stage_update(None, stage="2", pid=123, a_id=1, b_id=2,
                         snapshot=self.read())

    def test_drift_between_stages(self):
        a = self.read()
        b = self.read(a=(1,0), b=(3,4))
        r = stage_update(None, stage="1", pid=123, a_id=1, b_id=2, snapshot=a)
        r = stage_update(r, stage="2", pid=123, a_id=1, b_id=2, snapshot=b)
        r = stage_update(r, stage="3", pid=123, a_id=1, b_id=2, snapshot=b)
        self.assertEqual(r["comparisons"][0]["a_drift_candidate"], 1)
        self.assertAlmostEqual(r["comparisons"][0]["pair_distance_change_candidate"],
                               (20 ** 0.5) - 5)

    def test_selection_identity_change(self):
        s = self.read()
        self.obj_b.owner_address = 77
        with patch("aoe2hdcontrol.global_pair_v3_8._selection_id"):
            with self.assertRaises(ObjectAPIError):
                sample_pair(self.api, 1, 2, expected=s["identity"],
                            position_reader=lambda *args: point(0,0))

    def test_non_atomic_drift_rejected(self):
        calls = iter([point(0,0), point(3,4), point(1,0)])
        with patch("aoe2hdcontrol.global_pair_v3_8._selection_id"):
            s = sample_pair(self.api, 1, 2,
                            position_reader=lambda *args: next(calls))
        self.assertFalse(s["consistent_within_read"])
        with self.assertRaises(ValueError):
            stage_update(None, stage="1", pid=123, a_id=1, b_id=2, snapshot=s)

    def test_untrusted_candidates_blocked(self):
        self.api.allow_candidates = False
        with self.assertRaises(ObjectAPIError):
            sample_pair(self.api, 1, 2)


if __name__ == "__main__":
    unittest.main()
