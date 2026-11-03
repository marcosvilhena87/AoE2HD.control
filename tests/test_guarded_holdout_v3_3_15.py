"""Validation of guarded v3.3.12 -> v3.3.15 handoff (synthetic only)."""
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image

from aoe2hdcontrol.calibration_session_v3_3_15 import evaluate_session
from aoe2hdcontrol.guarded_holdout_v3_3_15 import build_manifest, TRAIN_IDS


def camera_check():
    return {"schema":"hd-camera-robust-v3.3.11","status":"candidate_camera_static",
            "selection_dispatch":"not_dispatched","memory_write":False}


class GuardedHoldoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = self.root / "reference.bmp"
        Image.new("RGB", (640,480), "white").save(self.image)
        self.training = []
        self.holdouts = []
        for i, oid in enumerate(list(TRAIN_IDS) + list(range(3000, 3010))):
            x,y = 10 + i % 4 * 7, 20 + i // 4 * 9
            anchor = {"schema":"hd-synchronized-anchor-v3.3.2",
                      "pid":4244,"object_id":oid,"usable":True,
                      "camera_verified_stationary":False,
                      "unit":{"candidate_world_x":x,"candidate_world_y":y,"finite":True},
                      "cursor_after":{"client":{"x":2*x+y+50,"y":x+3*y+60}}}
            before = self.root / (str(oid) + "_before.bmp")
            Image.new("RGB",(640,480),"white").save(before)
            report = {"schema":"hd-guarded-capture-v3.3.12",
                      "status":"candidate_capture_accepted",
                      "camera_consistency":"sampled_frames_only",
                      "anchor_usable":True,"cursor_stable":True,
                      "selection_dispatch":"not_dispatched","memory_write":False,
                      "validated_for_selection":False,"object_id":oid,"pid":4244,
                      "reference_image":str(self.image),
                      "before_image":{"path":str(before)},
                      "anchor":anchor,
                      "camera_checks":{name:camera_check() for name in
                                       ("reference_to_before","reference_to_after","before_to_after")}}
            path = self.root / (str(oid) + "_guard.json")
            path.write_text(json.dumps(report),encoding="utf-8")
            (self.training if i<6 else self.holdouts).append(path)

    def build(self, holdouts=None):
        return build_manifest(reference=self.image, training=self.training,
                              holdouts=self.holdouts if holdouts is None else holdouts,
                              session="experiment",note="Operador: mesma camera")

    def test_complete_holdout(self):
        result = self.build()
        self.assertEqual(result["status"], "ready_for_evaluation",result["errors"])
        report = evaluate_session(result["manifest"],
                                  detector=lambda a,b:camera_check())
        self.assertEqual(report["status"],"candidate_session_numeric_passed",report["reasons"])
        self.assertFalse(report["validated_for_selection"])

    def test_partial_is_never_ready(self):
        result = self.build(self.holdouts[:4])
        self.assertEqual(result["holdout_count"],4)
        self.assertEqual(result["status"],"blocked_or_incomplete")

    def test_mismatched_training_order_blocked(self):
        self.training[0],self.training[1] = self.training[1],self.training[0]
        self.assertNotEqual(self.build()["status"],"ready_for_evaluation")

    def test_guard_tampering_blocked(self):
        result = self.build()
        path = self.holdouts[0]
        path.write_text(path.read_text()+" ",encoding="utf-8")
        report = evaluate_session(result["manifest"],detector=lambda a,b:camera_check())
        self.assertEqual(report["status"],"blocked")
        self.assertIn("guarded_source_mismatch",report["camera_checks"][6]["reasons"])

    def test_missing_before_image_blocked(self):
        (self.root / "3000_before.bmp").unlink()
        self.assertEqual(self.build()["status"],"blocked_or_incomplete")

    def test_invalid_camera_check_blocked(self):
        path=self.holdouts[0]
        data=json.loads(path.read_text())
        data["camera_checks"]["reference_to_before"]["status"]="camera_moved"
        path.write_text(json.dumps(data))
        self.assertEqual(self.build()["status"],"blocked_or_incomplete")


if __name__ == "__main__":
    unittest.main()
