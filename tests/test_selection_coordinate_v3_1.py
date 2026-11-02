import unittest
from unittest.mock import patch
from aoe2hdcontrol.selection_coordinate_v3_1 import (
    select_by_screen_point, DispatchGuardError)

class API:
    allow_candidates=True

def shot(ids, state="stable_with_candidate_count"):
    return {"consistency":state,"selected_objects":[{"object_id":i} for i in ids]}

class Tests(unittest.TestCase):
    def test_success(self):
        calls=[]
        with patch("aoe2hdcontrol.selection_coordinate_v3_1.inspect_selection",
                   side_effect=[shot([1]),shot([2])]):
            r=select_by_screen_point(API(),pid=99,object_id=2,x=10,y=20,
                                     armed=True,click=lambda *a:calls.append(a))
        self.assertTrue(r["match"])
        self.assertEqual(calls,[(10,20,99)])
    def test_mismatch(self):
        with patch("aoe2hdcontrol.selection_coordinate_v3_1.inspect_selection",
                   side_effect=[shot([1]),shot([3])]):
            r=select_by_screen_point(API(),pid=99,object_id=2,x=10,y=20,
                                     armed=True,click=lambda *a:None)
        self.assertFalse(r["match"])
    def test_no_arm(self):
        with self.assertRaises(DispatchGuardError):
            select_by_screen_point(API(),pid=1,object_id=2,x=1,y=1)
    def test_invalid_coordinate(self):
        with self.assertRaises(ValueError):
            select_by_screen_point(API(),pid=1,object_id=2,x=-1,y=1,armed=True)
    def test_invalid_id(self):
        with self.assertRaises(ValueError):
            select_by_screen_point(API(),pid=1,object_id=True,x=1,y=1,armed=True)
    def test_opt_in(self):
        a=API();a.allow_candidates=False
        with self.assertRaises(DispatchGuardError):
            select_by_screen_point(a,pid=1,object_id=1,x=1,y=1,armed=True)
    def test_unstable_no_send(self):
        with patch("aoe2hdcontrol.selection_coordinate_v3_1.inspect_selection",return_value=shot([], "selection_changed")):
            with self.assertRaises(DispatchGuardError):
                select_by_screen_point(API(),pid=1,object_id=1,x=1,y=1,armed=True,
                    click=lambda *a:self.fail("must not click"))
if __name__=="__main__":unittest.main()
