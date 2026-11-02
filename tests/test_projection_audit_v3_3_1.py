import unittest
from aoe2hdcontrol.camera_projection_v3_3 import calibrate_projection
from aoe2hdcontrol.projection_audit_v3_3_1 import audit_projection

def anchor(x,y):
    return {"world_x":x,"world_y":y,"client_x":2*x-y+100,"client_y":x+y+50}

class Tests(unittest.TestCase):
    def setUp(self):
        self.cal=calibrate_projection([anchor(0,0),anchor(5,0),anchor(0,7)])
    def test_holdout_exact(self):
        a=audit_projection(self.cal,[anchor(3,4)])
        self.assertAlmostEqual(a["holdout_rmse_px"],0,places=5)
        self.assertEqual(a["status"],"audit_only_not_validated")
    def test_holdout_mismatch(self):
        h=anchor(3,4);h["client_x"]+=10
        a=audit_projection(self.cal,[h])
        self.assertAlmostEqual(a["holdout_rmse_px"],10,places=5)
    def test_parallel_flag(self):
        c=dict(self.cal);c["x_coefficients"]=[10,10,0];c["y_coefficients"]=[10,10.1,0]
        a=audit_projection(c,[anchor(3,4)])
        self.assertIn("nearly_parallel_world_axes",a["geometry"]["flags"])
    def test_no_holdout(self):
        with self.assertRaises(ValueError):audit_projection(self.cal,[])
    def test_nonfinite(self):
        h=anchor(1,2);h["client_x"]=float("nan")
        with self.assertRaises(ValueError):audit_projection(self.cal,[h])
    def test_three_anchor_warning(self):
        a=audit_projection(self.cal,[anchor(2,2)])
        self.assertIn("three_anchor_exact_fit_not_validation",a["geometry"]["flags"])
if __name__=="__main__":unittest.main()
