import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image

from aoe2hdcontrol.visual_identity_v3_3_15 import (
    prepare_review,adjudicate_review,audit_repeat)


def static_check():
    return {"schema":"hd-camera-robust-v3.3.11",
            "status":"candidate_camera_static",
            "selection_dispatch":"not_dispatched","memory_write":False}


def capture(image, reference, *, x=420, oid=2535, pid=99):
    cursor={"client":{"x":x,"y":310}}
    return {"schema":"hd-guarded-capture-v3.3.12",
            "status":"candidate_capture_accepted",
            "camera_consistency":"sampled_frames_only",
            "pid":pid,"object_id":oid,
            "camera_checks":{"reference_to_before":static_check(),
                             "reference_to_after":static_check(),
                             "before_to_after":static_check()},
            "anchor_usable":True,"cursor_stable":True,"image_errors":[],
            "validated_for_selection":False,
            "selection_dispatch":"not_dispatched","memory_write":False,
            "visual_object_correspondence":"unverified",
            "reference_image":str(reference),
            "before_image":{"path":str(image),"width":640,"height":480},
            "after_image":{"path":"after.bmp","width":640,"height":480},
            "anchor":{"pid":pid,"object_id":oid,
                      "unit":{"finite":True,"candidate_world_x":30.96875,
                              "candidate_world_y":31.46875},
                      "cursor_after":cursor}}


class CorrespondenceTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.d=Path(tmp.name)
        self.ref=self.d/"ref.bmp"
        Image.new("RGB",(640,480),"white").save(self.ref)

    def make(self, n, *, x=420, status="candidate_capture_accepted"):
        image=self.d/f"capture_{n}.bmp"
        Image.new("RGB",(640,480),"gray").save(image)
        cap=capture(image,self.ref,x=x)
        cap["status"]=status
        path=self.d/f"capture_{n}.json"
        path.write_text(json.dumps(cap))
        review=prepare_review(cap,capture_path=path,
                              screenshot_path=image,output_image=self.d/f"review_{n}.png")
        return cap,review,path,image

    def confirm(self, review):
        return adjudicate_review(review,identity="confirmed",isolated=True,
                                 cursor_on_target=True,reviewer="operador",
                                 note="alvo isolado e base inspecionada")

    def audit(self,a,b):
        x,y=a
        return audit_repeat(x[1],y[1],
            first_capture=x[0],second_capture=y[0],
            first_image=x[3],second_image=y[3])

    def test_prepare_creates_non_destructive_overlay(self):
        cap,rev,path,image=self.make(1)
        self.assertEqual(rev["status"],"pending_manual_review")
        self.assertTrue(Path(rev["annotated_image"]).is_file())
        self.assertFalse(rev["visual_identity_automatically_verified"])
        self.assertFalse(rev["validated_for_selection"])

    def test_review_requires_explicit_flags(self):
        _,review,_,_=self.make(1)
        with self.assertRaises(ValueError):
            adjudicate_review(review,identity="confirmed",isolated=False,
                              cursor_on_target=True,reviewer="a",note="b")

    def test_uncertain_is_not_approved(self):
        _,review,_,_=self.make(1)
        out=adjudicate_review(review,identity="uncertain",isolated=False,
                              cursor_on_target=False,reviewer="a",note="ambiguous")
        self.assertEqual(out["status"],"manual_review_rejected_or_uncertain")

    def test_repeated_operator_review_candidate(self):
        a=self.make(1);b=self.make(2,x=423)
        a=(a[0],self.confirm(a[1]),a[2],a[3])
        b=(b[0],self.confirm(b[1]),b[2],b[3])
        with patch("aoe2hdcontrol.camera_robust_v3_3_11.detect_robust_camera_motion",
                   return_value=static_check()):
            result=self.audit((a,b),(a,b))
        self.assertEqual(result["status"],"candidate_operator_correspondence_repeatable")
        self.assertFalse(result["validated_for_selection"])

    def test_cursor_movement_blocks(self):
        a=self.make(1);b=self.make(2,x=500)
        a=(a[0],self.confirm(a[1]),a[2],a[3])
        b=(b[0],self.confirm(b[1]),b[2],b[3])
        with patch("aoe2hdcontrol.camera_robust_v3_3_11.detect_robust_camera_motion",
                   return_value=static_check()):
            result=self.audit((a,b),(a,b))
        self.assertIn("cursor_not_repeatable",result["reasons"])

    def test_camera_moved_blocks(self):
        a=self.make(1);b=self.make(2)
        a=(a[0],self.confirm(a[1]),a[2],a[3])
        b=(b[0],self.confirm(b[1]),b[2],b[3])
        with patch("aoe2hdcontrol.camera_robust_v3_3_11.detect_robust_camera_motion",
                   return_value=dict(static_check(),status="camera_moved")):
            result=self.audit((a,b),(a,b))
        self.assertIn("camera_changed_between_captures",result["reasons"])

    def test_hash_tamper_blocks(self):
        a=self.make(1);b=self.make(2)
        a=(a[0],self.confirm(a[1]),a[2],a[3])
        b=(b[0],self.confirm(b[1]),b[2],b[3])
        b[2].write_text(b[2].read_text()+" ")
        with patch("aoe2hdcontrol.camera_robust_v3_3_11.detect_robust_camera_motion",
                   return_value=static_check()):
            result=self.audit((a,b),(a,b))
        self.assertIn("capture_hash_mismatch",result["reasons"])

    def test_reference_changed_blocks(self):
        a=self.make(1);b=self.make(2)
        a=(a[0],self.confirm(a[1]),a[2],a[3])
        b=(b[0],self.confirm(b[1]),b[2],b[3])
        Image.new("RGB",(640,480),"red").save(self.ref)
        with patch("aoe2hdcontrol.camera_robust_v3_3_11.detect_robust_camera_motion",
                   return_value=static_check()):
            result=self.audit((a,b),(a,b))
        self.assertIn("reference_hash_mismatch",result["reasons"])

    def test_blocked_camera_capture_blocks(self):
        a=self.make(1,status="capture_blocked");b=self.make(2)
        a=(a[0],self.confirm(a[1]),a[2],a[3])
        b=(b[0],self.confirm(b[1]),b[2],b[3])
        with patch("aoe2hdcontrol.camera_robust_v3_3_11.detect_robust_camera_motion",
                   return_value=static_check()):
            result=self.audit((a,b),(a,b))
        self.assertIn("camera_capture_blocked",result["reasons"])

    def test_same_capture_cannot_be_reused(self):
        a=self.make(1)
        a=(a[0],self.confirm(a[1]),a[2],a[3])
        with patch("aoe2hdcontrol.camera_robust_v3_3_11.detect_robust_camera_motion",
                   return_value=static_check()):
            result=self.audit((a,a),(a,a))
        self.assertIn("captures_not_independent",result["reasons"])

if __name__=="__main__":
    unittest.main()
