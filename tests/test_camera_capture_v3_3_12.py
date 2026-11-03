import tempfile
import unittest
from pathlib import Path
from PIL import Image

from aoe2hdcontrol.camera_capture_v3_3_12 import evaluate_capture_gate, capture_guarded


def result(status="candidate_camera_static"):
    return {"schema":"hd-camera-robust-v3.3.11","status":status,
            "selection_dispatch":"not_dispatched","memory_write":False}

class GateCaptureTests(unittest.TestCase):
    def test_all_checks_required(self):
        g=evaluate_capture_gate(result(),result(),result(),
             anchor_usable=True,cursor_stable=True)
        self.assertEqual(g["status"],"candidate_capture_accepted")
        self.assertFalse(g["validated_for_selection"])
        self.assertEqual(g["camera_consistency"],"sampled_frames_only")
    def test_motion_blocks(self):
        g=evaluate_capture_gate(result("camera_moved"),result(),result(),
            anchor_usable=True,cursor_stable=True)
        self.assertEqual(g["status"],"capture_blocked")
    def test_unverified_blocks(self):
        g=evaluate_capture_gate(result(),result("camera_unverified"),result(),
            anchor_usable=True,cursor_stable=True)
        self.assertEqual(g["status"],"capture_blocked")
    def test_missing_check_blocks(self):
        g=evaluate_capture_gate(result(),None,result(),
            anchor_usable=True,cursor_stable=True)
        self.assertEqual(g["status"],"capture_blocked")
    def test_anchor_cursor_and_error_block(self):
        for kwargs in ({"anchor_usable":False,"cursor_stable":True},
                       {"anchor_usable":True,"cursor_stable":False},
                       {"anchor_usable":True,"cursor_stable":True,"image_errors":["failure"]}):
            g=evaluate_capture_gate(result(),result(),result(),**kwargs)
            self.assertEqual(g["status"],"capture_blocked")
    def test_injected_capture_accepts_only_sampled_frames(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d); ref=d/"ref.bmp";pre=d/"pre.bmp";post=d/"post.bmp"
            Image.new("RGB",(240,220),(40,80,120)).save(ref)
            def capture(pid,path):
                Image.new("RGB",(240,220),(40,80,120)).save(path)
                return {"path":str(path),"width":240,"height":220}
            def cursor(pid):
                return {"game_foreground":True,"client":{"x":20,"y":20}}
            def anchor(pid,object_id,mapping):
                return {"usable":True,"cursor_after":{"client":{"x":20,"y":20}}}
            a=capture_guarded(pid=123,object_id=2535,delay=0,reference=ref,
                before_path=pre,after_path=post,mapping_path=None,
                screenshot=capture,cursor_reader=cursor,anchor_reader=anchor,
                detector=lambda x,y:result(),sleep=lambda sec:None)
            self.assertEqual(a["status"],"candidate_capture_accepted")
            self.assertEqual(a["object_id"],2535)
            self.assertFalse(a["validated_for_selection"])
    def test_injected_camera_moved_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);ref=d/"ref.bmp"
            Image.new("RGB",(240,220)).save(ref)
            def capture(pid,path):
                Image.new("RGB",(240,220)).save(path)
                return {}
            c={"game_foreground":True,"client":{"x":1,"y":1}}
            a=capture_guarded(pid=123,object_id=2535,delay=0,reference=ref,
                before_path=d/"pre.bmp",after_path=d/"post.bmp",mapping_path=None,
                screenshot=capture,cursor_reader=lambda pid:c,
                anchor_reader=lambda pid,oid,m:{"usable":True,"cursor_after":c},
                detector=lambda x,y:result("camera_moved"),sleep=lambda x:None)
            self.assertEqual(a["status"],"capture_blocked")
    def test_paths_cannot_overlap(self):
        with tempfile.TemporaryDirectory() as d:
            ref=Path(d)/"ref.bmp";Image.new("RGB",(200,200)).save(ref)
            with self.assertRaises(ValueError):
                capture_guarded(pid=1,object_id=1,delay=0,reference=ref,
                    before_path=ref,after_path=Path(d)/"post.bmp",
                    mapping_path=None,sleep=lambda x:None)

if __name__=="__main__":
    unittest.main()
