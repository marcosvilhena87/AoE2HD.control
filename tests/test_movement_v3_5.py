import unittest
from types import SimpleNamespace
from unittest.mock import patch

from aoe2hdcontrol.movement_v3_5 import movement_metrics, monitor
from aoe2hdcontrol.selection_coordinate_v3_1 import DispatchGuardError


class MetricsTests(unittest.TestCase):
    def test_path_and_speed_not_radial_speed(self):
        m = movement_metrics([
            {"elapsed_ms": 0, "candidate_world_x": 0, "candidate_world_y": 0},
            {"elapsed_ms": 200, "candidate_world_x": 1, "candidate_world_y": 0},
            {"elapsed_ms": 400, "candidate_world_x": 1, "candidate_world_y": 1}])
        self.assertAlmostEqual(m["path_distance_candidate"], 2)
        self.assertAlmostEqual(m["net_distance_candidate"], 2 ** 0.5)
        self.assertAlmostEqual(m["samples"][-1]["speed_candidate_units_s"], 5)
        self.assertTrue(m["movement_observed"])
        self.assertFalse(m["arrival_verified"])

    def test_stationary_not_arrival(self):
        m = movement_metrics([
            {"elapsed_ms": i * 200, "candidate_world_x": 1,
             "candidate_world_y": 2} for i in range(5)])
        self.assertTrue(m["stationary_observed"])
        self.assertFalse(m["movement_observed"])
        self.assertEqual(m["arrival_status"], "arrival_unverified")

    def test_invalid_timestamps(self):
        with self.assertRaises(ValueError):
            movement_metrics([{"elapsed_ms": 0, "candidate_world_x": 0, "candidate_world_y": 0},
                              {"elapsed_ms": 0, "candidate_world_x": 0, "candidate_world_y": 0}])


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.obj = SimpleNamespace(address=0x120000, owner_address=0x130000,
                                   genie_type_id=83, class_id=4)
        self.api = SimpleNamespace(allow_candidates=True,
                                   get_object_by_id=lambda _: self.obj)
        self.p = iter([(1, 2), (1.1, 2), (1.5, 2), (1.7, 2)])
        self.calls = []
        self.now = 0.0

    @staticmethod
    def select(api, oid):
        return {"consistency": "stable_with_candidate_count",
                "selected_objects": [{"object_id": oid}]}

    def position(self, api, oid, obj):
        x, y = next(self.p)
        return {"finite": True, "candidate_world_x": x,
                "candidate_world_y": y}

    def run_monitor(self, **overrides):
        opts = dict(pid=123, object_id=2114, client_x=600, client_y=400,
                    armed=True, offline_confirmed=True,
                    interval_ms=200, duration_ms=600,
                    sender=lambda *a: self.calls.append(a),
                    clock=lambda: self.now,
                    sleep=lambda duration: setattr(self, "now", self.now + duration))
        opts.update(overrides)
        with patch("aoe2hdcontrol.movement_v3_5._selection_id", self.select), \
             patch("aoe2hdcontrol.movement_v3_5._identity_position", self.position):
            return monitor(self.api, **opts)

    def test_single_dispatch_and_metrics(self):
        r = self.run_monitor()
        self.assertEqual(self.calls, [(123, 600, 400)])
        self.assertEqual(r["status"], "movement_observed")
        self.assertEqual(len(r["metrics"]["samples"]), 4)
        self.assertEqual(r["arrival_status"], "arrival_unverified")
        self.assertFalse(r["memory_write"])

    def test_not_armed(self):
        with self.assertRaises(DispatchGuardError):
            self.run_monitor(armed=False)
        self.assertFalse(self.calls)

    def test_changes_in_identity_interrupt(self):
        def identity(api, oid, obj):
            if self.calls:
                raise DispatchGuardError("identity changed")
            return {"finite": True, "candidate_world_x": 1,
                    "candidate_world_y": 2}
        with patch("aoe2hdcontrol.movement_v3_5._selection_id", self.select), \
             patch("aoe2hdcontrol.movement_v3_5._identity_position", identity):
            r = monitor(self.api, pid=123, object_id=2114, client_x=600,
                        client_y=400, armed=True, offline_confirmed=True,
                        duration_ms=200, sender=lambda *a: self.calls.append(a),
                        clock=lambda: self.now,
                        sleep=lambda duration: setattr(self, "now", self.now + duration))
        self.assertEqual(r["status"], "observation_blocked")
        self.assertEqual(len(self.calls), 1)

    def test_bad_duration_before_dispatch(self):
        with self.assertRaises(ValueError):
            self.run_monitor(duration_ms=6000)
        self.assertFalse(self.calls)


if __name__ == "__main__":
    unittest.main()
