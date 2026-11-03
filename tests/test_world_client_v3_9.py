import unittest
from aoe2hdcontrol.world_client_v3_9 import calibrate, predict, append_capture

def s(oid,x,y):
    return {"object_id":oid,"world_candidate":{"x":x,"y":y},
            "client":{"x":2*x+3*y+100,"y":-x+4*y+200}}

class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.samples=[s(1,0,0),s(2,10,0),s(3,0,10),s(4,5,7)]

    def test_affine_heldout(self):
        c=calibrate(self.samples)
        self.assertAlmostEqual(c["validation_error_px"],0,places=7)
        self.assertTrue(c["validation_within_threshold"])
        self.assertFalse(c["world_to_client_validated"])
        self.assertEqual(c["status"],"candidate_fit_passed_heldout")
        q=predict(c["coefficients_candidate"],(5,7))
        self.assertAlmostEqual(q["x"],131)
        self.assertAlmostEqual(q["y"],223)

    def test_bad_heldout(self):
        self.samples[3]["client"]["x"]+=30
        c=calibrate(self.samples)
        self.assertFalse(c["validation_within_threshold"])
        self.assertEqual(c["status"],"candidate_fit_failed_heldout")

    def test_collinear(self):
        with self.assertRaises(ValueError):
            calibrate([s(1,0,0),s(2,1,1),s(3,2,2),s(4,2,1)])

    def test_duplicate_ids(self):
        self.samples[3]["object_id"]=1
        with self.assertRaises(ValueError):
            calibrate(self.samples)

    def test_undersized_data(self):
        with self.assertRaises(ValueError):
            calibrate(self.samples[:3])

    def test_append_four_independent(self):
        r=None
        for i in range(4):
            r=append_capture(r,object_id=i,position={"x":i,"y":i+1},
                client={"x":20+i,"y":40+i},identity={"address":100+i,"owner_address":9},pid=55)
        self.assertEqual(len(r["samples"]),4)
        self.assertFalse(r["memory_write"])
        with self.assertRaises(ValueError):
            append_capture(r,object_id=5,position={"x":1,"y":1},
                client={"x":1,"y":1},identity={"address":5,"owner_address":9},pid=55)

    def test_owner_change(self):
        r=append_capture(None,object_id=1,position={"x":1,"y":2},
                client={"x":1,"y":2},identity={"address":100,"owner_address":9},pid=55)
        with self.assertRaises(ValueError):
            append_capture(r,object_id=2,position={"x":1,"y":2},
                client={"x":1,"y":2},identity={"address":200,"owner_address":8},pid=55)

if __name__=="__main__":
    unittest.main()
