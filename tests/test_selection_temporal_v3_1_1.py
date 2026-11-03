import unittest
from unittest.mock import patch
from aoe2hdcontrol.selection_temporal_v3_1_1 import select_with_temporal_verification
from aoe2hdcontrol.selection_coordinate_v3_1 import DispatchGuardError

class API:
    allow_candidates=True

def snap(ids, state="stable_with_candidate_count"):
    return {"consistency":state,"selected_objects":[{"object_id":i} for i in ids]}

class FakeTime:
    def __init__(self):self.t=0.
    def clock(self):return self.t
    def sleep(self,seconds):self.t+=seconds

class Tests(unittest.TestCase):
    def run_case(self, readings, schedule=(50,100,200)):
        t=FakeTime();sent=[]
        with patch("aoe2hdcontrol.selection_temporal_v3_1_1.inspect_selection",
                   side_effect=readings):
            out=select_with_temporal_verification(API(),pid=1,object_id=2,
                x=686,y=461,armed=True,intervals_ms=schedule,
                click=lambda *a:sent.append(a),clock=t.clock,sleep=t.sleep)
        self.assertEqual(sent,[(686,461,1)])
        return out
    def test_delayed_success(self):
        r=self.run_case([snap([1]),snap([]),snap([2])])
        self.assertTrue(r["match"])
        self.assertEqual(len(r["observations"]),2)
        self.assertEqual(r["first_match_elapsed_ms"],100.0)
    def test_no_match(self):
        r=self.run_case([snap([1]),snap([]),snap([3]),snap([1])])
        self.assertFalse(r["match"])
        self.assertEqual(len(r["observations"]),3)
    def test_unstable_then_success(self):
        r=self.run_case([snap([1]),snap([2],"selection_changed"),snap([2])])
        self.assertIsNone(r["observations"][0]["observed_ids"])
        self.assertTrue(r["match"])
    def test_already_selected_blocks_click(self):
        sent=[]
        with patch("aoe2hdcontrol.selection_temporal_v3_1_1.inspect_selection",return_value=snap([2])):
            with self.assertRaises(DispatchGuardError):
                select_with_temporal_verification(API(),pid=1,object_id=2,x=1,y=1,
                    armed=True,click=lambda *a:sent.append(a))
        self.assertEqual(sent,[])
    def test_unarmed(self):
        with self.assertRaises(DispatchGuardError):
            select_with_temporal_verification(API(),pid=1,object_id=2,x=1,y=1)
    def test_intervals(self):
        for values in [(),(100,50),(50,50),(0,),(10001,),("50",)]:
            with self.subTest(values=values),self.assertRaises(ValueError):
                select_with_temporal_verification(API(),pid=1,object_id=2,
                    x=1,y=1,armed=True,intervals_ms=values)
    def test_opt_in(self):
        a=API();a.allow_candidates=False
        with self.assertRaises(DispatchGuardError):
            select_with_temporal_verification(a,pid=1,object_id=2,x=1,y=1,armed=True)
    def test_unstable_before_blocks_click(self):
        with patch("aoe2hdcontrol.selection_temporal_v3_1_1.inspect_selection",
                   return_value=snap([],"selection_changed")):
            with self.assertRaises(DispatchGuardError):
                select_with_temporal_verification(API(),pid=1,object_id=2,x=1,y=1,
                    armed=True,click=lambda *a:self.fail("unexpected click"))
if __name__=="__main__":unittest.main()
