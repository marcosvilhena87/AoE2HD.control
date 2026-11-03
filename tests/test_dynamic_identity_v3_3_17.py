"""Synthetic and negative-case tests for offline v3.3.17 dynamic identity."""
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from aoe2hdcontrol.calibration_camera_v3_3_14 import sha256_file
from aoe2hdcontrol.dynamic_identity_v3_3_17 import analyze


def stationary_detector(before, after):
    return {"schema": "hd-camera-robust-v3.3.11",
            "status": "candidate_camera_static"}


class DynamicIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.json_dir = self.root / "json"
        self.json_dir.mkdir()
        ref = self.json_dir / "camera.bmp"
        Image.new("RGB", (640, 480), "white").save(ref)
        fit_path = self.json_dir / "fit.json"
        fit_path.write_text(json.dumps({
            "schema":"hd-synchronized-calibration-v3.3.2",
            "status":"candidate_fit_passed_threshold",
            "calibration":{"schema":"hd-affine-projection-v3.3",
                           "x_coefficients":[40,40,0],
                           "y_coefficients":[-20,20,0]}}))
        self.manifest = self.json_dir / "experiment.json"
        self.data = {
            "schema":"hd-dynamic-identity-v3.3.17",
            "operator_note":"Target manually moved while control remained stationary",
            "movement_method":"manual_in_game",
            "pid":4244,
            "target_id":500,
            "control_id":600,
            "fit_file":"fit.json",
            "fit_sha256":sha256_file(fit_path),
            "reference_image":"camera.bmp",
            "reference_sha256":sha256_file(ref),
            "captures":{},
            "thresholds":{"target_min_client_px":30,
                          "target_min_world":0.25,
                          "control_max_client_px":8,
                          "control_max_world":0.2,
                          "delta_max_error_px":12}}
        points = {
            "target_before":(500, (10,10), (100,100)),
            "control_before":(600,(8,8),(300,300)),
            "target_after":(500,(11,10),(140,80)),
            "control_after":(600,(8,8),(300,300))}
        for state, (oid, world, screen) in points.items():
            bmp = self.json_dir / (state+".bmp")
            Image.new("RGB",(640,480),"white").save(bmp)
            path = self.json_dir / (state+".json")
            checks = {k:{"schema":"hd-camera-robust-v3.3.11",
                         "status":"candidate_camera_static"} for k in
                      ("reference_to_before","reference_to_after","before_to_after")}
            cursor={"x":screen[0],"y":screen[1]}
            record={
                "schema":"hd-guarded-capture-v3.3.12",
                "status":"candidate_capture_accepted",
                "camera_consistency":"sampled_frames_only",
                "object_id":oid, "pid":4244,
                "anchor_usable":True, "cursor_stable":True,
                "validated_for_selection":False,
                "selection_dispatch":"not_dispatched",
                "memory_write":False,"image_errors":[],
                "camera_checks":checks,
                "before_image":{"path":str(bmp)},
                "cursor_after":{"client":cursor},
                "anchor":{"schema":"hd-synchronized-anchor-v3.3.2",
                          "object_id":oid,"pid":4244,"usable":True,
                          "unit":{"finite":True,
                                  "candidate_world_x":world[0],
                                  "candidate_world_y":world[1]},
                          "cursor_after":{"client":cursor}}}
            path.write_text(json.dumps(record))
            self.data["captures"][state] = path.name
        self.save()

    def save(self):
        self.manifest.write_text(json.dumps(self.data))

    def run_analysis(self):
        return analyze(self.manifest, self.root / "output",
                       detector=stationary_detector)

    def change_capture(self, state, callback):
        path = self.json_dir / self.data["captures"][state]
        row = json.loads(path.read_text())
        callback(row)
        path.write_text(json.dumps(row))

    def test_success_with_control(self):
        r=self.run_analysis()
        self.assertEqual(r["status"],"candidate_dynamic_consistency_passed")
        self.assertAlmostEqual(r["measurements"]["target"]["delta_residual_px"],0)
        self.assertEqual(r["measurements"]["control"]["screen_distance_px"],0)
        self.assertFalse(r["validated_for_selection"])
        self.assertTrue((self.root/"output"/"target_motion_review.png").exists())

    def test_camera_shift_blocks(self):
        def shifted(_before,_after):
            return {"schema":"hd-camera-robust-v3.3.11","status":"camera_moved"}
        r=analyze(self.manifest,self.root/"output",detector=shifted)
        self.assertEqual(r["status"],"blocked")
        self.assertTrue(any("camera_shift" in e for e in r["reasons"]))

    def test_negative_control_moved(self):
        def modify(r):
            r["anchor"]["cursor_after"]["client"]["x"] = 330
            r["cursor_after"]["client"]["x"] = 330
        self.change_capture("control_after",modify)
        r=self.run_analysis()
        self.assertIn("negative_control_visual_moved",r["reasons"])

    def test_target_too_short(self):
        def modify(r):
            r["anchor"]["unit"]["candidate_world_x"] = 10
            r["anchor"]["cursor_after"]["client"] = {"x":100,"y":100}
            r["cursor_after"]["client"] = {"x":100,"y":100}
        self.change_capture("target_after",modify)
        r=self.run_analysis()
        self.assertIn("target_world_movement_too_small",r["reasons"])
        self.assertIn("target_visual_movement_too_small",r["reasons"])

    def test_displacement_mismatch(self):
        def modify(r):
            r["anchor"]["cursor_after"]["client"] = {"x":200,"y":150}
            r["cursor_after"]["client"] = {"x":200,"y":150}
        self.change_capture("target_after",modify)
        r=self.run_analysis()
        self.assertIn("target_delta_prediction_mismatch",r["reasons"])

    def test_mixed_pid(self):
        def modify(r):
            r["pid"]=555
            r["anchor"]["pid"]=555
        self.change_capture("control_after",modify)
        r=self.run_analysis()
        self.assertIn("mixed_or_missing_pid",r["reasons"])

    def test_duplicate_target_and_control(self):
        self.data["control_id"]=500
        self.save()
        with self.assertRaises(ValueError):
            self.run_analysis()

    def test_fit_tamper_blocks(self):
        (self.json_dir/"fit.json").write_text("{}")
        with self.assertRaises(ValueError):
            self.run_analysis()

    def test_output_not_overwritten(self):
        self.run_analysis()
        with self.assertRaises(FileExistsError):
            self.run_analysis()


if __name__=="__main__":
    unittest.main()
