import unittest

from aoe2hdcontrol.camera_robust_v3_3_11 import classify_motion, gate_robust_camera

class CameraRobustTests(unittest.TestCase):
    def kwargs(self):
        return dict(matches=200,inliers=165,inlier_ratio=.825,dx=0,
                    dy=0,median_residual=.6,coverage_cells=9,
                    scale=1.0,rotation_deg=0.0)
    def test_static(self):
        self.assertEqual(classify_motion(**self.kwargs()),"candidate_camera_static")
    def test_move(self):
        a=self.kwargs();a.update(dx=114,dy=2)
        self.assertEqual(classify_motion(**a),"camera_moved")
    def test_low_inliers(self):
        a=self.kwargs();a.update(inliers=14)
        self.assertEqual(classify_motion(**a),"camera_unverified")
    def test_inconsistent(self):
        a=self.kwargs();a.update(median_residual=7)
        self.assertEqual(classify_motion(**a),"camera_unverified")
    def test_bad_coverage(self):
        a=self.kwargs();a.update(coverage_cells=1)
        self.assertEqual(classify_motion(**a),"camera_unverified")
    def test_scale_rotation(self):
        a=self.kwargs();a.update(scale=1.04)
        self.assertEqual(classify_motion(**a),"camera_unverified")
        a=self.kwargs();a.update(rotation_deg=4)
        self.assertEqual(classify_motion(**a),"camera_unverified")
    def test_gate_fails_closed(self):
        c={"schema":"hd-camera-robust-v3.3.11","status":"camera_moved",
           "selection_dispatch":"not_dispatched","memory_write":False}
        b={"schema":"hd-projection-batch-validation-v3.3.7",
           "status":"candidate_batch_passed"}
        self.assertEqual(gate_robust_camera(c,b)["status"],"blocked")
        c["status"]="candidate_camera_static"
        gate=gate_robust_camera(c,b)
        self.assertEqual(gate["status"],"manual_intermediate_review_required")
        self.assertFalse(gate["validated_for_selection"])
    def test_bad_schema(self):
        with self.assertRaises(ValueError):
            gate_robust_camera({}, {})
    def test_identical_synthetic_image(self):
        try:
            import cv2
            import numpy as np
            from PIL import Image
        except ImportError:
            self.skipTest("opencv-python numpy Pillow optional for camera integration")
        from aoe2hdcontrol.camera_robust_v3_3_11 import detect_robust_camera_motion
        rng=np.random.default_rng(117)
        arr=rng.integers(0,256,size=(540,720),dtype=np.uint8)
        im=Image.fromarray(arr)
        result=detect_robust_camera_motion(im,im,max_features=1800)
        self.assertEqual(result["status"],"candidate_camera_static")
        self.assertGreaterEqual(result["coverage_cells"],4)
    def test_shift_synthetic_image(self):
        try:
            import cv2
            import numpy as np
            from PIL import Image
        except ImportError:
            self.skipTest("opencv-python numpy Pillow optional for camera integration")
        from aoe2hdcontrol.camera_robust_v3_3_11 import detect_robust_camera_motion
        rng=np.random.default_rng(170)
        arr=rng.integers(0,256,size=(540,720),dtype=np.uint8)
        shifted=np.zeros_like(arr)
        shifted[5:,12:]=arr[:-5,:-12]
        result=detect_robust_camera_motion(Image.fromarray(arr),
                                           Image.fromarray(shifted),max_features=2400)
        self.assertEqual(result["status"],"camera_moved")
        self.assertAlmostEqual(result["dx_px"],12,delta=2)
        self.assertAlmostEqual(result["dy_px"],5,delta=2)

if __name__=="__main__":
    unittest.main()
