import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from aoe2hdcontrol.calibration_camera_v3_3_14 import (
 bind_calibration,camera_bound_projection,render_overlay,sha256_file)

def fit():
 return {"schema":"hd-synchronized-calibration-v3.3.2",
  "status":"candidate_fit_passed_threshold",
  "calibration":{"schema":"hd-affine-projection-v3.3",
   "x_coefficients":[1,0,400],"y_coefficients":[0,1,360]}}
def check():
 return {"schema":"hd-camera-robust-v3.3.11","status":"candidate_camera_static",
         "selection_dispatch":"not_dispatched","memory_write":False}
def capture(ref,pre):
 cursor={"client":{"x":458,"y":380}}
 return {"schema":"hd-guarded-capture-v3.3.12","status":"candidate_capture_accepted",
 "camera_consistency":"sampled_frames_only","pid":123,"object_id":2535,
 "camera_checks":{"reference_to_before":check(),"reference_to_after":check(),
                   "before_to_after":check()},
 "anchor_usable":True,"cursor_stable":True,"image_errors":[],
 "validated_for_selection":False,"selection_dispatch":"not_dispatched",
 "memory_write":False,"visual_object_correspondence":"unverified",
 "reference_image":str(ref),
 "before_image":{"path":str(pre),"width":600,"height":500},
 "after_image":{"path":"after.bmp","width":600,"height":500},
 "cursor_after":cursor,
 "anchor":{"pid":123,"object_id":2535,"cursor_after":cursor,
 "unit":{"finite":True,"candidate_world_x":50,"candidate_world_y":20}}}
def detector(a,b):
 return check()
class BindingTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name)
  self.f=self.root/"fit.json";self.f.write_text(json.dumps(fit()))
  self.ref=self.root/"reference.bmp";self.pre=self.root/"pre.bmp"
  Image.new("RGB",(600,500),"white").save(self.ref)
  Image.new("RGB",(600,500),"white").save(self.pre)
 def bound(self,provenance="contemporaneous_operator_attested"):
  return bind_calibration(self.f,self.ref,provenance=provenance,operator_note="Imagens da sessao original")
 def run_project(self,binding=None,cap=None,detect=detector):
  return camera_bound_projection(cap or capture(self.ref,self.pre),fit(),
    binding or self.bound(),fit_path=self.f,reference_path=self.ref,
    capture_reference_path=self.ref,capture_before_path=self.pre,
    client_width=600,client_height=500,detector=detect)
 def test_bound_projection_numeric(self):
  r=self.run_project()
  self.assertEqual(r["status"],"candidate_bound_projection")
  self.assertEqual(r["error_px"],8.0)
  self.assertTrue(r["eligible_for_numeric_batch"])
  self.assertFalse(r["validated_for_selection"])
 def test_legacy_fit_unverified_blocked(self):
  r=self.run_project(binding=self.bound("legacy_unverified"))
  self.assertEqual(r["status"],"calibration_camera_blocked")
  self.assertIn("calibration_camera_unverified",r["reasons"])
  self.assertFalse(r["eligible_for_numeric_batch"])
 def test_camera_moved_blocks(self):
  def moved(a,b):
   return dict(check(),status="camera_moved")
  r=self.run_project(detect=moved)
  self.assertIn("calibration_camera_mismatch_or_unverified",r["reasons"])
 def test_camera_unverified_blocks(self):
  r=self.run_project(detect=lambda a,b:dict(check(),status="camera_unverified"))
  self.assertFalse(r["eligible_for_numeric_batch"])
 def test_hash_mismatch_blocks(self):
  binding=self.bound()
  self.f.write_text(self.f.read_text()+" ")
  r=self.run_project(binding=binding)
  self.assertIn("fit_hash_mismatch",r["reasons"])
 def test_reference_tampering_blocks(self):
  binding=self.bound()
  Image.new("RGB",(600,500),"black").save(self.ref)
  r=self.run_project(binding=binding)
  self.assertIn("calibration_reference_hash_mismatch",r["reasons"])
 def test_capture_blocked_remains_blocked(self):
  c=capture(self.ref,self.pre);c["status"]="capture_blocked"
  self.assertFalse(self.run_project(cap=c)["eligible_for_numeric_batch"])
 def test_capture_reference_path_mismatch(self):
  c=capture(self.ref,self.pre);c["reference_image"]="different.bmp"
  self.assertIn("capture_reference_path_mismatch",self.run_project(cap=c)["reasons"])
 def test_annotated_image_non_destructive(self):
  r=self.run_project()
  dest=self.root/"annotated.png"
  out=render_overlay(r,self.pre,dest)
  self.assertTrue(dest.is_file())
  self.assertEqual(out["status"],"annotated_not_verified")
  with self.assertRaises(ValueError): render_overlay(r,self.pre,self.pre)
 def test_provenance_requires_note(self):
  with self.assertRaises(ValueError):
   bind_calibration(self.f,self.ref,provenance="contemporaneous_operator_attested",operator_note="")
if __name__=="__main__":unittest.main()
