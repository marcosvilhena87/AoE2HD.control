import unittest
from aoe2hdcontrol.correspondence_review_v3_3_9 import review_audit

def sample(name,oid,err=8,predx=100,predy=100):
 return {"file":name,"pid":28628,"object_id":oid,
         "predicted":{"x":predx,"y":predy},
         "measured":{"x":predx+err,"y":predy},
         "residual":{"x":err,"y":0},"error_px":err}
def manifest(entries):
 return {"schema":"hd-visual-reviews-v3.3.9","reviews":entries}
def checked(path,identity="confirmed",camera="confirmed_static",ref="unit_base"):
 return {"report":path,"identity":identity,"camera":camera,"reference":ref,
         "reason":"Conferido no BMP","bmp":"visual.bmp","reviewer":"operador"}
def audit(*samples):
 return {"schema":"hd-residual-audit-v3.3.8","threshold_px":25,
         "client":{"width":1536,"height":864},"samples":list(samples),"invalid":[]}

class ReviewTests(unittest.TestCase):
 def test_no_reviews_preserves_everything(self):
  a=review_audit(audit(sample("first",2535,92),sample("second",2535,19)),manifest([]))
  self.assertEqual(a["all_observations"]["n"],2)
  self.assertEqual(a["review_eligible_only"]["n"],0)
  self.assertEqual(a["flagged_or_unreviewed"]["n"],2)
  self.assertEqual(a["repeated_objects"][0]["max_measured_spread_px"],73)
 def test_confirmed_subset_and_outlier_retained(self):
  a=review_audit(audit(sample("first",2535,92),sample("second",2535,19)),
                 manifest([checked("first",identity="rejected"),checked("second")]))
  self.assertEqual(a["all_observations"]["max_error_px"],92)
  self.assertEqual(a["review_eligible_only"]["max_error_px"],19)
  self.assertEqual(a["status"],"manual_review_required")
 def test_camera_uncertain_not_eligible(self):
  a=review_audit(audit(sample("a",1)),manifest([checked("a",camera="uncertain")]))
  self.assertEqual(a["review_eligible_only"]["n"],0)
 def test_reference_other_not_eligible(self):
  a=review_audit(audit(sample("a",1)),manifest([checked("a",ref="other")]))
  self.assertEqual(a["review_eligible_only"]["n"],0)
 def test_unknown_path_fail_closed(self):
  with self.assertRaises(ValueError):
   review_audit(audit(sample("a",1)),manifest([checked("b")]))
 def test_duplicate_reviews_fail_closed(self):
  with self.assertRaises(ValueError):
   review_audit(audit(sample("a",1)),manifest([checked("a"),checked("a")]))
 def test_reason_required(self):
  c=checked("a");c["reason"]=""
  with self.assertRaises(ValueError):review_audit(audit(sample("a",1)),manifest([c]))
 def test_robust_slope_and_regions(self):
  a=review_audit(audit(sample("a",1,8,100,20),sample("b",2,10,200,310),
                       sample("c",3,12,300,700)),manifest([]))
  self.assertAlmostEqual(a["robust_trends_all"]["dx_vs_x"]["slope"],.02)
  self.assertEqual([x["all"]["n"] for x in a["region_by_predicted_y"]],[1,1,1])

if __name__=="__main__":unittest.main()
