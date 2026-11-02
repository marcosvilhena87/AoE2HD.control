import unittest
from aoe2hdcontrol.visual_correspondence_v3_3_3 import audit_aba

def sample(i,wx=10,wy=20,x=100,y=100,pid=7):
 return {"schema":"hd-synchronized-anchor-v3.3.2","usable":True,
 "object_id":i,"pid":pid,"unit":{"candidate_world_x":wx,"candidate_world_y":wy},
 "cursor_after":{"client":{"x":x,"y":y}},"camera_verified_stationary":False}
class TestABA(unittest.TestCase):
 def test_observed_large_cursor_delta(self):
  r=audit_aba(sample(2630,x=1002,y=499),sample(2629),sample(2630,x=172,y=380))
  self.assertAlmostEqual(r["cursor_delta_px"]["x"],-830)
  self.assertAlmostEqual(r["cursor_delta_px"]["distance"],838.4879,places=2)
  self.assertEqual(r["camera_movement"],"unknown")
  self.assertIn("cursor_position_changed_between_A_captures",r["warnings"])
 def test_no_camera_inference(self):
  r=audit_aba(sample(1),sample(2),sample(1))
  self.assertEqual(r["visual_correspondence"],"unverified")
  self.assertEqual(r["status"],"inconclusive")
 def test_world_change(self):
  r=audit_aba(sample(1),sample(2),sample(1,wx=11))
  self.assertIn("world_position_changed",r["warnings"])
 def test_id_mismatch(self):
  with self.assertRaises(ValueError):audit_aba(sample(1),sample(2),sample(3))
 def test_pid_mismatch(self):
  with self.assertRaises(ValueError):audit_aba(sample(1),sample(2,pid=8),sample(1))
 def test_reject_bad_capture(self):
  b=sample(1);b["usable"]=False
  with self.assertRaises(ValueError):audit_aba(sample(1),sample(2),b)
if __name__=="__main__":unittest.main()
