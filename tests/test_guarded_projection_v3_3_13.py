import math
import unittest
from aoe2hdcontrol.guarded_projection_v3_3_13 import project_guarded, validate_guarded_batch

def check(status="candidate_camera_static"):
    return {"schema":"hd-camera-robust-v3.3.11","status":status,
            "selection_dispatch":"not_dispatched","memory_write":False}

def capture(status="candidate_capture_accepted",oid=2535):
    cursor={"client":{"x":458,"y":380}}
    return {"schema":"hd-guarded-capture-v3.3.12","status":status,
            "camera_consistency":"sampled_frames_only",
            "pid":28628,"object_id":oid,
            "camera_checks":{"reference_to_before":check(),"reference_to_after":check(),
                             "before_to_after":check()},
            "anchor_usable":True,"cursor_stable":True,"image_errors":[],
            "validated_for_selection":False,"selection_dispatch":"not_dispatched",
            "memory_write":False,"visual_object_correspondence":"unverified",
            "before_image":{"width":1536,"height":864},
            "after_image":{"width":1536,"height":864},
            "cursor_after":cursor,
            "anchor":{"pid":28628,"object_id":oid,"cursor_after":cursor,
                      "unit":{"finite":True,"candidate_world_x":50,
                              "candidate_world_y":20}}}

def fit():
    return {"schema":"hd-synchronized-calibration-v3.3.2",
            "status":"candidate_fit_passed_threshold",
            "calibration":{"schema":"hd-affine-projection-v3.3",
                           "x_coefficients":[1,0,400],
                           "y_coefficients":[0,1,360]}}

class GuardedProjectionTests(unittest.TestCase):
    def test_accepted_projection(self):
        result=project_guarded(capture(),fit(),client_width=1536,client_height=864)
        self.assertEqual(result["status"],"candidate_guarded_projection")
        self.assertAlmostEqual(result["error_px"],math.hypot(8,0))
        self.assertEqual(result["residual"],{"dx_px":8,"dy_px":0})
        self.assertFalse(result["validated_for_selection"])
    def test_blocked_capture_excluded(self):
        r=project_guarded(capture("capture_blocked"),fit(),client_width=1536,client_height=864)
        self.assertEqual(r["status"],"projection_blocked")
        self.assertIsNone(r["error_px"])
        self.assertFalse(r["eligible_for_numeric_batch"])
    def test_moved_camera_cannot_be_forged_by_status(self):
        c=capture();c["camera_checks"]["reference_to_after"]=check("camera_moved")
        self.assertEqual(project_guarded(c,fit(),client_width=1536,client_height=864)["status"],"projection_blocked")
    def test_foreground_cursor_mismatch_blocked(self):
        c=capture();c["cursor_after"]={"client":{"x":460,"y":380}}
        self.assertIn("cursor_after_mismatch",project_guarded(c,fit(),client_width=1536,client_height=864)["reasons"])
    def test_image_dimensions_mismatch(self):
        c=capture();c["after_image"]["width"]=1920
        self.assertEqual(project_guarded(c,fit(),client_width=1536,client_height=864)["status"],"projection_blocked")
    def test_bad_fit_rejected(self):
        f=fit();f["status"]="inconclusive"
        with self.assertRaises(ValueError):
            project_guarded(capture(),f,client_width=1536,client_height=864)
    def test_out_of_bounds_rejected(self):
        f=fit();f["calibration"]["x_coefficients"]=[1,0,2000]
        self.assertEqual(project_guarded(capture(),f,client_width=1536,client_height=864)["status"],"projection_blocked")
    def test_numeric_batch_preserves_blocked(self):
        good=project_guarded(capture(),fit(),client_width=1536,client_height=864)
        bad=project_guarded(capture("capture_blocked",oid=2536),fit(),client_width=1536,client_height=864)
        result=validate_guarded_batch([("good.json",good),("blocked.json",bad)],min_samples=1)
        self.assertEqual(result["metrics"]["count"],1)
        self.assertEqual(len(result["excluded"]),1)
        self.assertEqual(result["status"],"inconclusive")
    def test_no_cherry_picking_duplicate_ids(self):
        a=project_guarded(capture(),fit(),client_width=1536,client_height=864)
        result=validate_guarded_batch([("a",a),("b",a)],min_samples=2)
        self.assertEqual(result["metrics"]["count"],1)
        self.assertIn("duplicate_object_id",result["excluded"][0]["reasons"])
    def test_minimum_and_gates(self):
        a=project_guarded(capture(),fit(),client_width=1536,client_height=864)
        result=validate_guarded_batch([("a",a)],min_samples=1)
        self.assertEqual(result["status"],"candidate_numeric_batch_passed")
        self.assertFalse(result["validated_for_selection"])
    def test_outlier_kept(self):
        c=capture();c["anchor"]["cursor_after"]["client"]={"x":500,"y":450}
        c["cursor_after"]={"client":{"x":500,"y":450}}
        r=project_guarded(c,fit(),client_width=1536,client_height=864)
        b=validate_guarded_batch([("outlier",r)],min_samples=1)
        self.assertEqual(b["metrics"]["count"],1)
        self.assertEqual(b["status"],"inconclusive")
        self.assertGreater(b["metrics"]["max_error_px"],25)

if __name__=="__main__":
    unittest.main()
