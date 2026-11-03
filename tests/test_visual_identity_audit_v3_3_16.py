import csv
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from aoe2hdcontrol.calibration_camera_v3_3_14 import sha256_file
from aoe2hdcontrol.visual_identity_audit_v3_3_16 import prepare, finalize


class VisualAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.capture_dir = self.root / "json"
        self.capture_dir.mkdir()
        self.report = self.root / "session_report.json"
        self.manifest = self.capture_dir / "manifest.json"
        self.output = self.root / "review"
        self.fit_file = self.root / "fit.json"
        ids = list(range(3000, 3010))
        anchors, audits = [], []
        for index, oid in enumerate(ids):
            image = self.capture_dir / f"{oid}_guard_before_v3_3_15.bmp"
            Image.new("RGB", (640, 480), "white").save(image)
            anchor = {"schema":"hd-synchronized-anchor-v3.3.2", "pid":4244,
                      "object_id":oid, "usable":True,
                      "cursor_after":{"client":{"x":100+index,"y":120+index}},
                      "unit":{"finite":True,"candidate_world_x":index,
                              "candidate_world_y":index+1}}
            checks = {key:{"status":"candidate_camera_static"} for key in
                      ("reference_to_before","reference_to_after","before_to_after")}
            capture = {"schema":"hd-guarded-capture-v3.3.12",
                       "pid":4244, "object_id":oid,
                       "status":"candidate_capture_accepted",
                       "camera_consistency":"sampled_frames_only",
                       "anchor_usable":True,"cursor_stable":True,
                       "validated_for_selection":False,
                       "selection_dispatch":"not_dispatched","memory_write":False,
                       "camera_checks":checks,"image_errors":[],
                       "before_image":{"path":str(image)}, "anchor":anchor}
            (self.capture_dir / f"{oid}_guard_v3_3_15.json").write_text(json.dumps(capture))
            anchors.append({"role":"holdout","anchor":anchor,
                            "camera_image":image.name,
                            "camera_sha256":sha256_file(image)})
            audits.append({"object_id":oid,"predicted_client_x":101+index,
                           "predicted_client_y":120+index,
                           "measured_client_x":100+index,
                           "measured_client_y":120+index,"error_px":1.})
        self.manifest.write_text(json.dumps({
            "schema":"hd-camera-session-v3.3.15","session":"test-session",
            "anchors":anchors}))
        fit = {"status":"candidate_fit_passed_threshold",
               "audit":{"holdouts":audits}}
        self.fit_file.write_text(json.dumps(fit))
        self.report.write_text(json.dumps({
            "schema":"hd-camera-session-v3.3.15-report",
            "status":"candidate_session_numeric_passed",
            "session":"test-session","pid":4244,
            "training_ids":[2000,2001,2002],
            "holdout_ids":ids,"fit":fit,
            "validated_for_selection":False,
            "selection_dispatch":"not_dispatched","memory_write":False}))

    def test_prepare_and_final_review(self):
        result = prepare(self.report, self.manifest, self.capture_dir, self.output,
                         fit_path=self.fit_file)
        self.assertEqual(result["status"],"ready_for_human_review")
        self.assertEqual(len(list(self.output.glob("*_review.png"))),10)
        self.assertFalse(result["validated_for_selection"])
        reviews = self.output / "reviews.csv"
        with reviews.open(encoding="utf-8-sig",newline="") as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            row.update(decision="confirmed", reviewer="operator",
                       reason="manual_visual_confirmation")
        with reviews.open("w",encoding="utf-8-sig",newline="") as f:
            writer = csv.DictWriter(f,fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        finalized = finalize(self.output/"prepared_report.json",reviews,
                             self.output/"final.json")
        self.assertEqual(finalized["status"],"operator_visual_review_complete")
        self.assertEqual(finalized["counts"]["confirmed"],10)
        self.assertFalse(finalized["validated_for_selection"])

    def test_default_review_is_inconclusive(self):
        prepare(self.report, self.manifest, self.capture_dir, self.output)
        result = finalize(self.output/"prepared_report.json",
                          self.output/"reviews.csv", self.output/"final.json")
        self.assertEqual(result["status"],"inconclusive")
        self.assertFalse(result["validated_for_selection"])

    def test_capture_mismatch_blocks(self):
        capture_path = self.capture_dir/"3000_guard_v3_3_15.json"
        data = json.loads(capture_path.read_text())
        data["object_id"] = 99
        capture_path.write_text(json.dumps(data))
        result = prepare(self.report,self.manifest,self.capture_dir,self.output)
        self.assertEqual(result["status"],"blocked")
        self.assertIn("capture_or_anchor_mismatch",result["records"][0]["reasons"])

    def test_tampered_image_blocks(self):
        image = self.capture_dir/"3000_guard_before_v3_3_15.bmp"
        Image.new("RGB",(640,480),"black").save(image)
        result = prepare(self.report,self.manifest,self.capture_dir,self.output)
        self.assertEqual(result["status"],"blocked")

    def test_fit_mismatch_rejected(self):
        self.fit_file.write_text("{}")
        with self.assertRaises(ValueError):
            prepare(self.report,self.manifest,self.capture_dir,self.output,
                    fit_path=self.fit_file)

    def test_duplicate_review_rejected(self):
        prepare(self.report,self.manifest,self.capture_dir,self.output)
        path=self.output/"reviews.csv"
        with path.open("a",encoding="utf-8") as f:
            f.write("3000,confirmed,operator,note,abc\n")
        with self.assertRaises(ValueError):
            finalize(self.output/"prepared_report.json",path,self.output/"final.json")

    def test_overlay_tampering_fails_closed(self):
        prepare(self.report,self.manifest,self.capture_dir,self.output)
        image=self.output/"3000_review.png"
        image.write_bytes(b"tampered")
        result=finalize(self.output/"prepared_report.json",self.output/"reviews.csv",
                        self.output/"final.json")
        self.assertEqual(result["status"],"inconclusive")
        self.assertIn("overlay_hash_mismatch",result["records"][0]["reasons"])

    def test_no_overwrite(self):
        prepare(self.report,self.manifest,self.capture_dir,self.output)
        with self.assertRaises(FileExistsError):
            prepare(self.report,self.manifest,self.capture_dir,self.output)

if __name__=="__main__":
    unittest.main()
