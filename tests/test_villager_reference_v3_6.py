import unittest
from types import SimpleNamespace
from unittest.mock import patch
from aoe2hdcontrol.villager_reference_v3_6 import compare_reference,experiment
from aoe2hdcontrol.selection_coordinate_v3_1 import DispatchGuardError

def p(x,y):
    return {"candidate_world_x":x,"candidate_world_y":y}

class Comparison(unittest.TestCase):
    def test_approach_and_stop_not_arrival(self):
        report={"status":"movement_observed","metrics":{"stationary_observed":True,
                "samples":[{"x":1,"y":0}]}}
        out=compare_reference(report,p(0,0),p(1.3,0),p(1.3,0))
        self.assertEqual(out["status"],"candidate_proximity_observed")
        self.assertEqual(out["arrival_status"],"arrival_unverified")
        self.assertAlmostEqual(out["initial_distance_candidate"],1.3)
        self.assertAlmostEqual(out["final_distance_candidate"],0.3)

    def test_reference_motion_invalidates(self):
        report={"status":"movement_observed","metrics":{"stationary_observed":True,
                "samples":[{"x":4,"y":0}]}}
        self.assertEqual(compare_reference(report,p(0,0),p(5,0),p(6,0))["status"],"reference_moved")

    def test_stop_far_away_not_arrived(self):
        report={"status":"movement_observed","metrics":{"stationary_observed":True,
                "samples":[{"x":1,"y":0}]}}
        self.assertEqual(compare_reference(report,p(0,0),p(10,0),p(10,0))["status"],"proximity_not_observed")

    def test_missing_samples(self):
        out=compare_reference({"metrics":None},p(0,0),p(1,0),p(1,0))
        self.assertEqual(out["status"],"observation_blocked")

class Guard(unittest.TestCase):
    def test_same_id(self):
        with self.assertRaises(ValueError):
            experiment(SimpleNamespace(),pid=1,mover_id=1,reference_id=1,
                       client_x=10,client_y=10,armed=True,offline_confirmed=True)

    def test_no_arm(self):
        with self.assertRaises(DispatchGuardError):
            experiment(SimpleNamespace(),pid=1,mover_id=1,reference_id=2,
                       client_x=10,client_y=10)

    def test_full(self):
        objs={1:SimpleNamespace(address=100,owner_address=10,genie_type_id=83),
              2:SimpleNamespace(address=200,owner_address=10,genie_type_id=293)}
        api=SimpleNamespace(allow_candidates=True,get_object_by_id=lambda oid:objs[oid])
        with patch("aoe2hdcontrol.villager_reference_v3_6._selection_id"), \
             patch("aoe2hdcontrol.villager_reference_v3_6.load_catalog", return_value=[{"genie_type_id":"83","nome_pt":"Aldeão"},{"genie_type_id":"293","nome_pt":"Aldeão"}]), \
             patch("aoe2hdcontrol.villager_reference_v3_6._identity_position",
                   side_effect=[p(0,0),p(4,0),p(4,0)]), \
             patch("aoe2hdcontrol.villager_reference_v3_6.monitor",
                   return_value={"status":"movement_observed","metrics":{
                     "stationary_observed":True,"samples":[{"x":3.5,"y":0}]}}) as dispatch:
            result=experiment(api,pid=1,mover_id=1,reference_id=2,
                              client_x=600,client_y=400,
                              armed=True,offline_confirmed=True)
        self.assertEqual(dispatch.call_count,1)
        self.assertEqual(result["comparison"]["status"],"candidate_proximity_observed")
        self.assertFalse(result["direct_move_to_object"])

if __name__=="__main__":
    unittest.main()
