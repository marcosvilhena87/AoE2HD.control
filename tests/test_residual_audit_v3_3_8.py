import math
import unittest

from aoe2hdcontrol.residual_audit_v3_3_8 import audit_residuals, render_svg

def obs(oid, mx=108, my=100, pid=28628):
    return {"schema":"hd-observation-projection-v3.3.6",
            "pid":pid,"object_id":oid,"selection_dispatch":"not_dispatched",
            "memory_write":False,"predicted_client":{"x":100,"y":100},
            "measurement_comparison":{"measured_client_x":mx,
                "measured_client_y":my,"error_px":math.hypot(mx-100,my-100),
                "correspondence":"operator_review_required"}}

class ResidualAuditTests(unittest.TestCase):
    def audit(self, records):
        return audit_residuals(records,client_width=1536,client_height=864)
    def test_keep_outlier_and_repeat(self):
        result=self.audit([("a.json",obs(2535,367,378)),("b.json",obs(2535,366,378)),
                           ("c.json",obs(2535,108,100))])
        self.assertEqual(len(result["samples"]),3)
        self.assertEqual(result["statistics"]["n_distinct_object_pid"],1)
        self.assertGreater(result["repeated_objects"][0]["max_cursor_spread_px"],300)
        self.assertEqual(result["status"],"review_required")
    def test_signed_residual_and_svg(self):
        result=self.audit([("a.json",obs(2611,108,95))])
        self.assertEqual(result["samples"][0]["residual"],{"x":8.,"y":-5.})
        svg=render_svg(result)
        self.assertIn("<svg",svg)
        self.assertIn("2611",svg)
    def test_reject_invalid_error(self):
        r=obs(3);r["measurement_comparison"]["error_px"]=0
        result=self.audit([("a.json",r)])
        self.assertEqual(len(result["samples"]),0)
        self.assertEqual(len(result["invalid"]),1)
    def test_reject_dispatch(self):
        r=obs(3);r["selection_dispatch"]="clicked"
        self.assertEqual(self.audit([("x",r)])["invalid"][0]["reason"],"not_read_only")
    def test_reject_out_of_bounds(self):
        self.assertEqual(self.audit([("x",obs(3,mx=1800))])["invalid"][0]["reason"],"out_of_client_bounds")
    def test_no_automatic_camera_claim(self):
        r=self.audit([("x",obs(1))])
        self.assertEqual(r["camera_consistency"],"unverified")
        self.assertEqual(r["visual_correspondence"],"unverified")
    def test_multiple_files_kept_distinct(self):
        a=self.audit([("first.json",obs(3)),("second.json",obs(3,mx=111))])
        self.assertEqual(len(a["samples"]),2)
        self.assertEqual(len(a["repeated_objects"]),1)

if __name__=="__main__":unittest.main()
