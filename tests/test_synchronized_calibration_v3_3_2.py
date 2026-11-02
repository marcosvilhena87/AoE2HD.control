import unittest
from unittest.mock import patch
from aoe2hdcontrol.synchronized_calibration_v3_3_2 import synchronized_anchor,fit_and_holdout
class API:allow_candidates=True
def cursor(x):return {"game_foreground":True,"screen":{"x":x,"y":20},"client":{"x":x,"y":20}}
def anchor(oid,x,y,cx,cy):
 return {"schema":"hd-synchronized-anchor-v3.3.2","usable":True,"pid":1,"object_id":oid,
 "unit":{"candidate_world_x":x,"candidate_world_y":y},
 "cursor_after":{"client":{"x":cx,"y":cy}}}
class Tests(unittest.TestCase):
 def test_stable_anchor(self):
  with patch("aoe2hdcontrol.synchronized_calibration_v3_3_2.probe_unit_position",
    return_value={"finite":True}):
   r=synchronized_anchor(API(),pid=1,object_id=2,cursor_reader=lambda p:cursor(10))
  self.assertTrue(r["usable"])
 def test_cursor_motion_rejected(self):
  readings=iter((cursor(10),cursor(20)))
  with patch("aoe2hdcontrol.synchronized_calibration_v3_3_2.probe_unit_position",
    return_value={"finite":True}):
   r=synchronized_anchor(API(),pid=1,object_id=2,cursor_reader=lambda p:next(readings))
  self.assertFalse(r["usable"])
 def test_holdout_pass(self):
  rows=[anchor(i,x,y,2*x-y+100,x+y+50) for i,(x,y) in
    enumerate(((0,0),(5,0),(0,7),(3,4)),1)]
  r=fit_and_holdout(rows,holdout_ids=[4])
  self.assertEqual(r["status"],"candidate_fit_passed_threshold")
 def test_bad_holdout(self):
  rows=[anchor(i,x,y,2*x-y+100,x+y+50) for i,(x,y) in
    enumerate(((0,0),(5,0),(0,7),(3,4)),1)]
  rows[-1]["cursor_after"]["client"]["x"]+=200
  self.assertEqual(fit_and_holdout(rows,holdout_ids=[4])["status"],"rejected")
 def test_duplicate(self):
  rows=[anchor(1,0,0,0,0)]*4
  with self.assertRaises(ValueError):fit_and_holdout(rows,holdout_ids=[1])
if __name__=="__main__":unittest.main()
