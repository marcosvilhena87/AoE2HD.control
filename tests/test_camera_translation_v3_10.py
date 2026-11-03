import unittest
from aoe2hdcontrol.camera_translation_v3_10 import (
    compare_camera,append_observation,validate_base)
from aoe2hdcontrol.world_client_v3_9 import calibrate

def row(oid,x,y):
    return {"object_id":oid,"world_candidate":{"x":x,"y":y},
            "client":{"x":2*x+3*y+100,"y":-x+4*y+200},
            "identity":{"address":100+oid,"owner_address":9,"class_id":4,
                        "genie_type_id":83}}
def baseline():
    s=[row(1,0,0),row(2,10,0),row(3,0,10),row(4,5,7)]
    return {"schema":"hd-world-client-affine-v3.9","pid":123,
            "samples":s,"calibration":calibrate(s)}
def observation(base,oid,dx=70,dy=-30):
    sample=next(s for s in base["samples"] if s["object_id"]==oid)
    return {"object_id":oid,"world_candidate":dict(sample["world_candidate"]),
            "client":{"x":sample["client"]["x"]+dx,"y":sample["client"]["y"]+dy},
            "identity":dict(sample["identity"])}

class CameraTests(unittest.TestCase):
    def test_translation_pass(self):
        b=baseline()
        result=compare_camera(b,observation(b,1),observation(b,4))
        self.assertAlmostEqual(result["translation_candidate_px"]["x"],70)
        self.assertAlmostEqual(result["translation_candidate_px"]["y"],-30)
        self.assertAlmostEqual(result["independent_error_px"],0,places=6)
        self.assertEqual(result["status"],"candidate_translation_passed_heldout")
        self.assertFalse(result["world_to_client_validated"])
        self.assertFalse(result["command_dispatched"])

    def test_validation_failure(self):
        b=baseline()
        result=compare_camera(b,observation(b,1),observation(b,4,dx=130))
        self.assertEqual(result["status"],"candidate_translation_failed_heldout")

    def test_camera_not_shifted(self):
        b=baseline()
        result=compare_camera(b,observation(b,1,0,0),observation(b,4,0,0))
        self.assertEqual(result["status"],"candidate_no_measurable_shift")

    def test_moving_reference_rejected(self):
        b=baseline()
        a=observation(b,1)
        a["world_candidate"]["x"]+=1
        with self.assertRaises(ValueError):
            compare_camera(b,a,observation(b,4))

    def test_same_id_not_independent(self):
        b=baseline()
        with self.assertRaises(ValueError):
            compare_camera(b,observation(b,1),observation(b,1))

    def test_bad_baseline_rejected(self):
        b=baseline()
        b["calibration"]["validation_within_threshold"]=False
        with self.assertRaises(ValueError):
            validate_base(b)

    def test_capture_sequence_and_identity(self):
        b=baseline()
        first=observation(b,1)
        r=append_observation(None,b,role="anchor",object_id=1,
            world_candidate=first["world_candidate"],client=first["client"],
            identity=first["identity"],pid=123,base_digest="abc")
        with self.assertRaises(ValueError):
            append_observation(r,b,role="check",object_id=1,
                world_candidate=first["world_candidate"],client=first["client"],
                identity=first["identity"],pid=123,base_digest="abc")
        check=observation(b,4)
        r=append_observation(r,b,role="check",object_id=4,
            world_candidate=check["world_candidate"],client=check["client"],
            identity=check["identity"],pid=123,base_digest="abc")
        self.assertEqual(len(r["observations"]),2)
        self.assertFalse(r["memory_write"])

    def test_first_must_be_anchor(self):
        b=baseline()
        a=observation(b,1)
        with self.assertRaises(ValueError):
            append_observation(None,b,role="check",object_id=1,
                world_candidate=a["world_candidate"],client=a["client"],
                identity=a["identity"],pid=123,base_digest="abc")

if __name__=="__main__":
    unittest.main()
