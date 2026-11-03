import unittest
from PIL import Image
from aoe2hdcontrol.camera_guard_v3_3_10 import detect_camera_motion, gate_batch

def scene():
    # Deterministic textured image with independently identifiable regions.
    im=Image.new("L",(320,260))
    pixels=im.load()
    for y in range(260):
        for x in range(320):
            pixels[x,y]=(x*17+y*29+((x*y*13) ^ (x*83+y*47)))%256
    return im

ANCHORS=[{"x":95,"y":95},{"x":170,"y":110},{"x":225,"y":175}]
def moved(im,dx,dy):
    out=Image.new("L",im.size,0)
    out.paste(im,(dx,dy))
    return out

class CameraGuardTests(unittest.TestCase):
    def test_stationary_pair(self):
        a=scene()
        r=detect_camera_motion(a,a,ANCHORS,search_px=12)
        self.assertEqual(r["status"],"candidate_camera_static")
        self.assertEqual(r["n_matches"],3)
    def test_shifted_pair(self):
        a=scene()
        r=detect_camera_motion(a,moved(a,8,-6),ANCHORS,search_px=12)
        self.assertEqual(r["status"],"camera_moved")
        self.assertEqual((r["median_dx_px"],r["median_dy_px"]),(8,-6))
    def test_low_texture_fail_closed(self):
        a=Image.new("L",(320,260),128)
        r=detect_camera_motion(a,a,ANCHORS,search_px=12)
        self.assertEqual(r["status"],"camera_unverified")
    def test_invalid_landmarks_fail_closed(self):
        with self.assertRaises(ValueError):
            detect_camera_motion(scene(),scene(),[ANCHORS[0]],search_px=12)
        with self.assertRaises(ValueError):
            detect_camera_motion(scene(),scene(),[ANCHORS[0]]*3,search_px=12)
    def test_gating_never_authorizes_selection(self):
        camera={"schema":"hd-camera-motion-v3.3.10",
                "status":"candidate_camera_static",
                "selection_dispatch":"not_dispatched","memory_write":False}
        batch={"schema":"hd-projection-batch-validation-v3.3.7",
               "status":"candidate_batch_passed"}
        r=gate_batch(camera,batch)
        self.assertEqual(r["status"],"manual_intermediate_review_required")
        self.assertFalse(r["validated_for_selection"])
        camera["status"]="camera_moved"
        self.assertEqual(gate_batch(camera,batch)["status"],"blocked")
if __name__=="__main__":unittest.main()
