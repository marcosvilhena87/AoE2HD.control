"""Offline unit tests for fail-closed guarded movement experiment."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from aoe2hdcontrol.movement_v3_4 import experiment
from aoe2hdcontrol.selection_coordinate_v3_1 import DispatchGuardError


class MovementTests(unittest.TestCase):
    def setUp(self):
        self.api = SimpleNamespace(allow_candidates=True)
        self.obj = SimpleNamespace(address=0x120000, owner_address=0x130000,
                                   genie_type_id=83, class_id=4)
        self.positions = iter([(10.0, 20.0), (10.5, 20.5), (11.0, 21.0)])
        self.calls = []
        self.clock_value = 0.0

    def selection(self, api):
        return {"consistency": "stable_with_candidate_count",
                "selected_objects": [{"object_id": 22}]}

    def position(self, api, object_id):
        x, y = next(self.positions)
        return {"object_id": object_id, "candidate_world_x": x,
                "candidate_world_y": y, "finite": True}

    def run_experiment(self, **kw):
        self.api.get_object_by_id = lambda oid: self.obj
        def clock():
            return self.clock_value
        def sleep(delta):
            self.clock_value += delta
        with patch("aoe2hdcontrol.movement_v3_4.inspect_selection", self.selection), \
             patch("aoe2hdcontrol.movement_v3_4.probe_unit_position", self.position):
            return experiment(self.api, pid=123, object_id=22, client_x=450,
                              client_y=310, armed=True, offline_confirmed=True,
                              intervals_ms=(200, 500), sender=lambda *v: self.calls.append(v),
                              clock=clock, sleep=sleep, **kw)

    def test_candidate_movement_not_proof(self):
        result = self.run_experiment()
        self.assertEqual(result["status"], "candidate_displacement_observed")
        self.assertEqual(self.calls, [(123, 450, 310)])
        self.assertEqual(result["game_command_accepted"], "unknown")
        self.assertFalse(result["direct_object_id_command"])
        self.assertFalse(result["memory_write"])

    def test_arm_and_offline_required(self):
        for opts in ({"armed": False, "offline_confirmed": True},
                     {"armed": True, "offline_confirmed": False}):
            with self.assertRaises(DispatchGuardError):
                experiment(self.api, pid=123, object_id=22, client_x=1, client_y=1, **opts)
        self.assertEqual(self.calls, [])

    def test_candidate_opt_in_required(self):
        self.api.allow_candidates = False
        with self.assertRaises(DispatchGuardError):
            experiment(self.api, pid=123, object_id=22, client_x=1, client_y=1,
                       armed=True, offline_confirmed=True)

    def test_selection_mismatch_blocks_dispatch(self):
        self.api.get_object_by_id = lambda oid: self.obj
        with patch("aoe2hdcontrol.movement_v3_4.inspect_selection",
                   return_value={"consistency": "unstable", "selected_objects": []}):
            with self.assertRaises(DispatchGuardError):
                experiment(self.api, pid=123, object_id=22, client_x=1, client_y=1,
                           armed=True, offline_confirmed=True,
                           sender=lambda *v: self.calls.append(v))
        self.assertEqual(self.calls, [])

    def test_identity_change_stops_followup(self):
        count = 0
        def getobj(_):
            nonlocal count
            count += 1
            if count >= 3:
                return SimpleNamespace(address=0x222000, owner_address=0x130000,
                                       genie_type_id=83, class_id=4)
            return self.obj
        self.api.get_object_by_id = getobj
        with patch("aoe2hdcontrol.movement_v3_4.inspect_selection", self.selection), \
             patch("aoe2hdcontrol.movement_v3_4.probe_unit_position", self.position):
            out = experiment(self.api, pid=123, object_id=22, client_x=1, client_y=1,
                             armed=True, offline_confirmed=True, intervals_ms=(200,),
                             sender=lambda *v: self.calls.append(v),
                             clock=lambda: 0, sleep=lambda _: None)
        self.assertEqual(out["status"], "observation_blocked")
        self.assertEqual(len(self.calls), 1)

    def test_reject_invalid_coordinates_before_dispatch(self):
        with self.assertRaises(ValueError):
            experiment(self.api, pid=123, object_id=22, client_x=-1, client_y=1,
                       armed=True, offline_confirmed=True)


if __name__ == "__main__":
    unittest.main()
