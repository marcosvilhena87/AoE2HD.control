import unittest
from unittest.mock import patch
from aoe2hdcontrol.selected_objects_v2_4 import inspect_consistency
from aoe2hdcontrol.object_api import ObjectAPIError

class API:
    allow_candidates=True

def report(ids=(1,),pointer=0x200000,first_zero=1,anom=None):
    return {"player_address":0x300000,"local_slot":1,"selection_region_start":0x160,
            "max_entries":2,"slots":[{"pointer":pointer,"status":"selected_verified",
              "object_id_candidate":ids[0] if ids else None,"selection_word":0x10000},
              {"pointer":0,"status":"zero"}],
            "selected_objects":[{"object_id":v,"address":pointer,"class_id":4,
                                 "genie_type_id":83} for v in ids],
            "anomalies":anom or [],"nonzero_after_first_zero":False,
            "truncated_at_limit":first_zero is None}

class Tests(unittest.TestCase):
    def test_stable(self):
        with patch("aoe2hdcontrol.selected_objects_v2_4.enumerate_selected",side_effect=[report(),report()]):
            x=inspect_consistency(API(),max_entries=2)
        self.assertEqual(x["consistency"],"stable_within_window")
        self.assertEqual(x["selected_count_verified"],1)
        self.assertEqual(x["completeness"],"unknown")
    def test_unstable(self):
        with patch("aoe2hdcontrol.selected_objects_v2_4.enumerate_selected",side_effect=[report(),report(ids=(2,))]):
            x=inspect_consistency(API(),max_entries=2)
        self.assertEqual(x["consistency"],"unstable")
        self.assertIsNone(x["selected_count_verified"])
        self.assertEqual(x["selected_objects"],[])
    def test_bounded_and_inconsistent(self):
        with patch("aoe2hdcontrol.selected_objects_v2_4.enumerate_selected",side_effect=[report(first_zero=None),report(first_zero=None)]):
            self.assertEqual(inspect_consistency(API(),max_entries=2)["consistency"],"bounded_unterminated")
        with patch("aoe2hdcontrol.selected_objects_v2_4.enumerate_selected",side_effect=[report(anom=[{"status":"read_error"}]),report(anom=[{"status":"read_error"}])]):
            self.assertEqual(inspect_consistency(API(),max_entries=2)["consistency"],"inconsistent")
    def test_opt_in(self):
        api=API()
        api.allow_candidates=False
        with self.assertRaises(ObjectAPIError):inspect_consistency(api)

if __name__=="__main__":unittest.main()
