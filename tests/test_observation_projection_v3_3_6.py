import unittest
from unittest.mock import patch
from aoe2hdcontrol.observation_projection_v3_3_6 import observe_projection

FIT={"schema":"hd-synchronized-calibration-v3.3.2",
     "status":"candidate_fit_passed_threshold",
     "calibration":{"schema":"hd-affine-projection-v3.3",
       "x_coefficients":[10,0,20],"y_coefficients":[0,10,30]}}
UNIT={"finite":True,"candidate_world_x":2.0,"candidate_world_y":3.0}

class ObservationTests(unittest.TestCase):
 def invoke(self,**kw):
  with patch("aoe2hdcontrol.observation_projection_v3_3_6.probe_unit_position",return_value=UNIT):
   return observe_projection(object(),pid=8,object_id=5,fit=FIT,
                             client_width=200,client_height=200,**kw)
 def test_projection_inside(self):
  r=self.invoke()
  self.assertEqual(r["predicted_client"],{"x":40.,"y":60.})
  self.assertTrue(r["inside_client"])
  self.assertEqual(r["selection_dispatch"],"not_dispatched")
 def test_outside(self):
  with patch("aoe2hdcontrol.observation_projection_v3_3_6.probe_unit_position",return_value=UNIT):
   r=observe_projection(object(),pid=8,object_id=5,fit=FIT,client_width=35,client_height=200)
  self.assertEqual(r["status"],"outside_client")
 def test_reject_unaccepted_fit(self):
  f=dict(FIT,status="rejected")
  with self.assertRaises(ValueError):
   observe_projection(object(),pid=8,object_id=5,fit=f,client_width=200,client_height=200)
 def test_measurement_comparison(self):
  m={"schema":"hd-visual-evidence-v3.3.5","status":"candidate_visual_evidence",
     "cursor_stable_across_image":True,"pid":8,"object_id":5,
     "anchor":{"unit":{"candidate_world_x":2.,"candidate_world_y":3.},
               "cursor_after":{"client":{"x":41,"y":62}}}}
  r=self.invoke(measurement=m)
  self.assertAlmostEqual(r["measurement_comparison"]["error_px"],5**.5)
 def test_measurement_id_mismatch(self):
  m={"schema":"hd-visual-evidence-v3.3.5","status":"candidate_visual_evidence",
     "cursor_stable_across_image":True,"pid":8,"object_id":999}
  with self.assertRaises(ValueError):self.invoke(measurement=m)
if __name__=="__main__":unittest.main()
