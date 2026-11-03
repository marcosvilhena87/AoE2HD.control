"""Synthetic regression tests for v3.3.18 multi-session audit."""
import json
import tempfile
import unittest
from pathlib import Path

from aoe2hdcontrol.calibration_camera_v3_3_14 import sha256_file
from aoe2hdcontrol.multisession_identity_v3_3_18 import audit


class MultiSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root/"multi.json"
        self.exe = self.root/"AoK_HD.exe"
        self.exe.write_bytes(b"test executable fixture")
        self.data = {"schema":"hd-multisession-dynamic-v3.3.18",
                     "operator_note":"Synthetic offline test, not a real game restart",
                     "sessions":[]}
        directions = [(120,90),(-120,90),(-120,-90),(120,-90),(130,80),(-130,-80)]
        for s in range(3):
            folder = self.root/f"session_{s}"
            folder.mkdir()
            pid = 4200+s
            fit = {"schema":"hd-synchronized-calibration-v3.3.2",
                   "status":"candidate_fit_passed_threshold",
                   "calibration":{"schema":"hd-affine-projection-v3.3"}}
            fit_file = self.write(folder/"fit.json",fit)
            calibration = {"schema":"hd-camera-session-v3.3.15-report",
                           "status":"candidate_session_numeric_passed",
                           "pid":pid,"holdout_ids":list(range(10)),
                           "fit":fit,"validated_for_selection":False,
                           "selection_dispatch":"not_dispatched","memory_write":False}
            cfile = self.write(folder/"calibration.json",calibration)
            trials=[]
            for j in range(2):
                target,control = 1000+s*10+j*2,1001+s*10+j*2
                dx,dy = directions[s*2+j]
                captures={}
                for state in ("target_before","control_before","target_after","control_after"):
                    cap = self.write(folder/f"{j}_{state}.json",{"id":target})
                    image = folder/f"{j}_{state}.bmp"
                    image.write_bytes(b"fixture image"+state.encode()+bytes([j,s]))
                    captures[state]={"object_id":target if state.startswith("target") else control,
                                     "pid":pid,"capture_file":str(cap),
                                     "capture_sha256":sha256_file(cap),
                                     "image":str(image),"image_sha256":sha256_file(image)}
                dyn = {"schema":"hd-dynamic-identity-v3.3.17",
                       "pid":pid,"target_id":target,"control_id":control,
                       "fit_sha256":sha256_file(fit_file),
                       "movement_method":"manual_in_game"}
                dm_path=self.write(folder/f"{j}_manifest.json",dyn)
                report={"schema":"hd-dynamic-identity-v3.3.17-report",
                        "status":"candidate_dynamic_consistency_passed",
                        "reasons":[],"pid":pid,"target_id":target,"control_id":control,
                        "movement_method":"manual_in_game",
                        "camera_consistency":"sampled_images_only",
                        "visual_object_identity":"dynamic_correspondence_candidate_only",
                        "fit_sha256":sha256_file(fit_file),
                        "manifest_sha256":sha256_file(dm_path),
                        "captures":captures,
                        "validated_for_selection":False,
                        "selection_dispatch":"not_dispatched","memory_write":False,
                        "measurements":{
                            "target":{"world_delta":[dx/40,dy/40],
                                      "screen_delta":[dx,dy],
                                      "predicted_screen_delta":[dx,dy],
                                      "delta_residual_px":0.0},
                            "control":{"world_delta":[0,0],"screen_delta":[2,-2],
                                       "predicted_screen_delta":[0,0],
                                       "delta_residual_px":2.8284271247461903}}}
                rp=self.write(folder/f"{j}_report.json",report)
                trials.append({"manifest":self.entry(dm_path),"report":self.entry(rp)})
            self.data["sessions"].append({
                "session_id":f"run-{s}","boot_id":f"operator-restart-{s}",
                "pid":pid,"restart_attestation":"Operator states game restarted",
                "game_version":"5.8.INT",
                "executable":self.entry(self.exe),
                "calibration_report":self.entry(cfile),"fit_file":self.entry(fit_file),
                "trials":trials})
        self.save()

    def write(self,path,obj):
        path.write_text(json.dumps(obj),encoding="utf-8")
        return path

    def entry(self,path):
        return {"path":str(path),"sha256":sha256_file(path)}

    def save(self):
        self.write(self.manifest,self.data)

    def evaluate(self):
        return audit(self.manifest,self.root/"output")

    def test_synthetic_success(self):
        result=self.evaluate()
        self.assertEqual(result["status"],"candidate_multisession_repeatability_passed")
        self.assertEqual(result["metrics"]["accepted_trials"],6)
        self.assertEqual(len(result["metrics"]["quadrants"]),4)
        self.assertFalse(result["validated_for_selection"])

    def test_duplicate_pid_blocks(self):
        self.data["sessions"][1]["pid"]=4200
        self.save()
        result=self.evaluate()
        self.assertEqual(result["status"],"blocked")
        self.assertIn("session_independence_not_attested",result["reasons"])

    def test_missing_session_blocks(self):
        self.data["sessions"].pop()
        self.save()
        result=self.evaluate()
        self.assertIn("insufficient_sessions",result["reasons"])

    def test_tampered_report_blocks(self):
        rp = Path(self.data["sessions"][0]["trials"][0]["report"]["path"])
        with rp.open("a",encoding="utf-8") as f:
            f.write(" ")
        result=self.evaluate()
        self.assertEqual(result["status"],"blocked")
        self.assertIn("trial_0_blocked",result["sessions"][0]["reasons"])

    def test_missing_direction_blocks(self):
        for s in self.data["sessions"]:
            for trial in s["trials"]:
                rp=Path(trial["report"]["path"])
                r=json.loads(rp.read_text())
                r["measurements"]["target"].update(
                    screen_delta=[120,90],predicted_screen_delta=[120,90],
                    world_delta=[3,2.25],delta_residual_px=0)
                self.write(rp,r)
                trial["report"]=self.entry(rp)
        self.save()
        result=self.evaluate()
        self.assertIn("insufficient_directional_coverage",result["reasons"])

    def test_negative_control_moved_blocks(self):
        trial=self.data["sessions"][0]["trials"][0]
        rp=Path(trial["report"]["path"])
        r=json.loads(rp.read_text())
        r["measurements"]["control"]["screen_delta"]=[40,40]
        self.write(rp,r)
        trial["report"]=self.entry(rp)
        self.save()
        result=self.evaluate()
        self.assertEqual(result["status"],"blocked")

    def test_unsafe_dispatch_blocks(self):
        trial=self.data["sessions"][0]["trials"][0]
        rp=Path(trial["report"]["path"])
        r=json.loads(rp.read_text())
        r["selection_dispatch"]="dispatched"
        self.write(rp,r)
        trial["report"]=self.entry(rp)
        self.save()
        result=self.evaluate()
        self.assertEqual(result["status"],"blocked")

    def test_reused_capture_blocks(self):
        first=self.data["sessions"][0]["trials"][0]
        second=self.data["sessions"][0]["trials"][1]
        a=Path(first["report"]["path"]); b=Path(second["report"]["path"])
        ar=json.loads(a.read_text());br=json.loads(b.read_text())
        br["captures"]["target_before"]["capture_file"]=ar["captures"]["target_before"]["capture_file"]
        br["captures"]["target_before"]["capture_sha256"]=ar["captures"]["target_before"]["capture_sha256"]
        self.write(b,br)
        second["report"]=self.entry(b)
        self.save()
        result=self.evaluate()
        self.assertIn("trial_1_blocked",result["sessions"][0]["reasons"])

    def test_prevent_overwriting_reports(self):
        self.evaluate()
        with self.assertRaises(FileExistsError):
            self.evaluate()


if __name__ == "__main__":
    unittest.main()
