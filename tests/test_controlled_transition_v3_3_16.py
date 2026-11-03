import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from aoe2hdcontrol.visual_identity_v3_3_15 import prepare_review,adjudicate_review
from aoe2hdcontrol.controlled_transition_v3_3_16 import audit_transition

def static():
 return {"schema":"hd-camera-robust-v3.3.11","status":"candidate_camera_static",
         "selection_dispatch":"not_dispatched","memory_write":False}
class ControlledTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.ref=self.root/"ref.bmp"
  Image.new("RGB",(640,480),"white").save(self.ref)
 def make(self,phase,wx,x,*,status="candidate_capture_accepted",oid=2535):
  image=self.root/f"{phase}.bmp";Image.new("RGB",(640,480),"gray").save(image)
  cursor={"client":{"x":x,"y":210}}
  capture={"schema":"hd-guarded-capture-v3.3.12",
    "status":status,"pid":987,"object_id":oid,
    "camera_consistency":"sampled_frames_only",
    "anchor_usable":True,"cursor_stable":True,"image_errors":[],
    "validated_for_selection":False,"selection_dispatch":"not_dispatched",
    "memory_write":False,"visual_object_correspondence":"unverified",
    "reference_image":str(self.ref),
    "camera_checks":{k:static() for k in
      ("reference_to_before","reference_to_after","before_to_after")},
    "before_image":{"path":str(image),"width":640,"height":480},
    "after_image":{"path":str(image),"width":640,"height":480},
    "anchor":{"pid":987,"object_id":oid,
              "unit":{"finite":True,"candidate_world_x":wx,"candidate_world_y":20},
              "cursor_after":cursor}}
  cp=self.root/f"{phase}.json";cp.write_text(json.dumps(capture))
  review=prepare_review(capture,capture_path=cp,screenshot_path=image,
                        output_image=self.root/f"{phase}_overlay.png")
  review=adjudicate_review(review,identity="confirmed",isolated=True,
                          cursor_on_target=True,reviewer="tester",note="manual external evidence")
  return {"review":review,"capture":capture,"capture_path":str(cp),"image_path":str(image)}
 def stages(self):
  return {"A":self.make("A",10,100),"B":self.make("B",13,190),
          "C":self.make("C",10,101)}
 def audit(self,stages):
  return audit_transition(stages,detector=lambda x,y:static())
 def test_transition_candidate_not_identity_proof(self):
  result=self.audit(self.stages())
  self.assertEqual(result["status"],"candidate_manual_transition_correlated")
  self.assertFalse(result["validated_for_selection"])
  self.assertFalse(result["eligible_for_calibration"])
  self.assertEqual(result["world_AB_distance"],3)
 def test_no_world_motion_blocks(self):
  s=self.stages();s["B"]=self.make("B",10,190)
  self.assertIn("no_verified_world_displacement",self.audit(s)["reasons"])
 def test_no_cursor_motion_blocks(self):
  s=self.stages();s["B"]=self.make("B",13,101)
  self.assertIn("cursor_did_not_follow_movement",self.audit(s)["reasons"])
 def test_no_return_blocks(self):
  s=self.stages();s["C"]=self.make("C",12,150)
  r=self.audit(s)
  self.assertIn("world_not_returned",r["reasons"])
  self.assertIn("cursor_not_returned",r["reasons"])
 def test_blocked_capture_blocks(self):
  s=self.stages();s["B"]["capture"]["status"]="capture_blocked"
  self.assertIn("B:capture_not_accepted",self.audit(s)["reasons"])
 def test_review_unknown_blocks(self):
  s=self.stages();s["B"]["review"]["status"]="manual_review_rejected_or_uncertain"
  self.assertIn("B:manual_review_not_confirmed",self.audit(s)["reasons"])
 def test_id_change_blocks(self):
  s=self.stages();s["B"]=self.make("B",13,190,oid=2536)
  self.assertIn("object_or_process_changed",self.audit(s)["reasons"])
 def test_hash_edit_blocks(self):
  s=self.stages();Path(s["B"]["capture_path"]).write_text("altered")
  self.assertIn("B:capture_hash_mismatch",self.audit(s)["reasons"])
 def test_camera_changed_blocks(self):
  s=self.stages()
  def detector(a,b):
   return dict(static(),status="camera_moved")
  r=audit_transition(s,detector=detector)
  self.assertIn("camera_not_static:A_to_B",r["reasons"])
 def test_non_independent_capture_blocks(self):
  s=self.stages();s["C"]=s["A"]
  self.assertIn("non_independent_captures",self.audit(s)["reasons"])
 def test_invalid_tolerances(self):
  with self.assertRaises(ValueError):
   audit_transition(self.stages(),minimum_world_move=-1)
if __name__=="__main__":unittest.main()
