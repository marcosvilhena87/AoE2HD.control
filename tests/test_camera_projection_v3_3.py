import unittest
from aoe2hdcontrol.camera_projection_v3_3 import calibrate_projection,project
class Tests(unittest.TestCase):
    def test_affine(self):
        pairs=[{"world_x":x,"world_y":y,"client_x":2*x-y+100,"client_y":x+y+50}
               for x,y in ((0,0),(5,0),(0,7),(4,3))]
        c=calibrate_projection(pairs)
        self.assertAlmostEqual(c["rmse_px"],0)
        p=project(c,3,4)
        self.assertAlmostEqual(p["client_x"],102)
        self.assertAlmostEqual(p["client_y"],57)
        self.assertFalse(p["validated"])
    def test_collinear_rejected(self):
        with self.assertRaises(ValueError):
            calibrate_projection([{"world_x":i,"world_y":i,"client_x":i,"client_y":i} for i in range(3)])
    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):
            calibrate_projection([{"world_x":float("nan"),"world_y":0,"client_x":0,"client_y":0}]*3)
    def test_too_few(self):
        with self.assertRaises(ValueError):calibrate_projection([])
if __name__=="__main__":unittest.main()
