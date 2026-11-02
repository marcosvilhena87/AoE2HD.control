import unittest
from aoe2hdcontrol.assisted_visual_v3_3_4 import confirm_anchor,compare_recaptures
def a(x=100,y=200,wx=1.,wy=2.,oid=8):
 return {"schema":"hd-synchronized-anchor-v3.3.2","usable":True,"object_id":oid,"pid":7,
 "unit":{"candidate_world_x":wx,"candidate_world_y":wy},
 "cursor_after":{"client":{"x":x,"y":y}}}
W=dict(left=0,top=0,width=1500,height=900,client_origin_x=0,client_origin_y=0,client_width=1500,client_height=860)
def c(a0,window=W):return confirm_anchor(a0,confirmed_id=8,operator_confirmed=True,window=window)
class TestAssisted(unittest.TestCase):
 def test_repeatable(self):
  r=compare_recaptures(c(a()),c(a(x=102)))
  self.assertEqual(r["status"],"candidate_repeatable")
  self.assertEqual(r["camera_movement"],"unknown")
 def test_big_cursor_move(self):
  self.assertIn("visual_point_not_repeatable",compare_recaptures(c(a()),c(a(x=900)))["flags"])
 def test_window_change(self):
  w=dict(W);w["left"]=30
  self.assertIn("window_geometry_changed",compare_recaptures(c(a()),c(a(),w))["flags"])
 def test_world_move(self):
  self.assertIn("unit_world_position_changed",compare_recaptures(c(a()),c(a(wx=3)))["flags"])
 def test_id_mismatch(self):
  with self.assertRaises(ValueError):confirm_anchor(a(),confirmed_id=9,operator_confirmed=True,window=W)
 def test_confirmation_required(self):
  with self.assertRaises(ValueError):confirm_anchor(a(),confirmed_id=8,window=W)
if __name__=="__main__":unittest.main()
