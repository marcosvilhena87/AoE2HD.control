import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from aoe2hdcontrol.calibration_session_v3_3_15 import evaluate_session, SCHEMA


def stationary(_a, _b):
    return {"schema":"hd-camera-robust-v3.3.11","status":"candidate_camera_static"}


class CameraSessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.image = Path(self.tmp.name) / "camera.bmp"
        Image.new("RGB", (640, 480), "white").save(self.image)
        self.digest = hashlib.sha256(self.image.read_bytes()).hexdigest()

    def manifest(self):
        records = []
        # Geometrically diverse anchors and a genuinely disjoint ten-unit holdout.
        for i in range(16):
            x, y = (i % 4) * 8 + 7, (i // 4) * 9 + 11
            anchor = {
                "schema":"hd-synchronized-anchor-v3.3.2",
                "pid":321, "object_id":2500+i, "usable":True,
                "camera_verified_stationary":False,
                "unit":{"candidate_world_x":x,"candidate_world_y":y,"finite":True},
                "cursor_after":{"client":{"x":2*x-y+100,"y":x+3*y+70}},
            }
            records.append({"role":"train" if i<6 else "holdout",
                            "anchor":anchor, "camera_image":str(self.image),
                            "camera_sha256":self.digest})
        return {"schema":SCHEMA, "session":"local-001",
                "note":"Capturas manuais da mesma sessao e camera imovel",
                "reference_image":str(self.image), "reference_sha256":self.digest,
                "anchors":records}

    def check(self, manifest):
        return evaluate_session(manifest, detector=stationary)

    def test_independent_holdout_numeric_pass(self):
        result = self.check(self.manifest())
        self.assertEqual(result["status"], "candidate_session_numeric_passed", result["reasons"])
        self.assertEqual(len(result["holdout_ids"]), 10)
        self.assertFalse(result["validated_for_selection"])
        self.assertEqual(result["selection_dispatch"], "not_dispatched")
        self.assertFalse(result["memory_write"])

    def test_duplicate_ids_block(self):
        m = self.manifest()
        m["anchors"][-1]["anchor"]["object_id"] = 2500
        self.assertEqual(self.check(m)["status"],"blocked")

    def test_camera_motion_blocks(self):
        m = self.manifest()
        result = evaluate_session(m, detector=lambda _a,_b: {
            "schema":"hd-camera-robust-v3.3.11","status":"camera_moved"})
        self.assertEqual(result["status"],"blocked")

    def test_missing_holdouts_block(self):
        m = self.manifest()
        m["anchors"][-1]["role"] = "train"
        self.assertIn("insufficient_independent_holdouts",self.check(m)["reasons"])

    def test_tampered_image_blocks(self):
        m = self.manifest()
        m["anchors"][0]["camera_sha256"] = "0" * 64
        self.assertEqual(self.check(m)["status"],"blocked")

    def test_mixed_pid_blocks(self):
        m = self.manifest()
        m["anchors"][-1]["anchor"]["pid"] = 322
        self.assertIn("mixed_pids",self.check(m)["reasons"])

    def test_bad_note_blocks(self):
        m = self.manifest()
        m["note"] = ""
        with self.assertRaises(ValueError):
            self.check(m)

    def test_nonfinite_anchor_blocks(self):
        m = self.manifest()
        m["anchors"][0]["anchor"]["unit"]["candidate_world_x"] = float("nan")
        self.assertEqual(self.check(m)["status"], "blocked")

if __name__ == "__main__":
    unittest.main()
