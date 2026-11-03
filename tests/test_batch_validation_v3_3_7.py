import unittest
from aoe2hdcontrol.batch_validation_v3_3_7 import validate_batch

def report(oid,pid=42,error=12.0):
 return {"schema":"hd-observation-projection-v3.3.6","object_id":oid,
         "pid":pid,"status":"candidate_inside_client","inside_client":True,
         "selection_dispatch":"not_dispatched","memory_write":False,
         "measurement_comparison":{"error_px":error,"correspondence":"operator_review_required"}}

class BatchValidationTests(unittest.TestCase):
 def test_ten_units_pass(self):
  items=[(str(i),report(i)) for i in range(10,20)]
  r=validate_batch(items,excluded_ids=[2576,2627],min_samples=10)
  self.assertEqual(r["status"],"candidate_batch_passed")
  self.assertAlmostEqual(r["metrics"]["rmse_px"],12)
  self.assertEqual(r["metrics"]["p95_error_px"],12)
 def test_excluded_is_rejected(self):
  r=validate_batch([("x",report(2627))],excluded_ids=[2627],min_samples=1)
  self.assertEqual(r["metrics"]["count"],0)
  self.assertIn("calibration_or_previous_validation_id",r["rejected"][0]["reasons"])
 def test_duplicate_is_rejected(self):
  r=validate_batch([("a",report(10)),("b",report(10))],excluded_ids=[],min_samples=2)
  self.assertEqual(r["metrics"]["count"],1)
  self.assertEqual(r["status"],"inconclusive")
 def test_mixed_pid_fails(self):
  r=validate_batch([("a",report(10)),("b",report(11,pid=43))],excluded_ids=[],min_samples=2)
  self.assertFalse(r["gates"]["single_pid"])
 def test_threshold_fails(self):
  r=validate_batch([("a",report(10,error=26))],excluded_ids=[],min_samples=1)
  self.assertFalse(r["gates"]["all_under_threshold"])
 def test_missing_measurement(self):
  a=report(10);a["measurement_comparison"]=None
  r=validate_batch([("a",a)],excluded_ids=[],min_samples=1)
  self.assertEqual(r["metrics"]["count"],0)

if __name__=="__main__":unittest.main()
