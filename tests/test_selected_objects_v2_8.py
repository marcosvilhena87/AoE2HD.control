import unittest
from unittest.mock import patch
from aoe2hdcontrol.selected_objects_v2_8 import make_selection_intent, verify_selection
from aoe2hdcontrol.object_api import ObjectAPIError

class API:
    allow_candidates = True

def sample(ids, state="stable_with_candidate_count"):
    return {"consistency": state, "selected_objects": [{"object_id": i} for i in ids]}

class Tests(unittest.TestCase):
    def test_intent(self):
        self.assertEqual(make_selection_intent([2183])["execution"], "not_dispatched")
    def test_reject_duplicates(self):
        with self.assertRaises(ValueError): make_selection_intent([1, 1])
    def test_reject_non_int(self):
        for ids in ([True], ["1"], [1.0], [-1], [1000001], [], list(range(61))):
            with self.subTest(ids=ids):
                with self.assertRaises(ValueError): make_selection_intent(ids)
    def test_reject_append(self):
        with self.assertRaises(ValueError): make_selection_intent([1], mode="append")
    def test_equal_unordered(self):
        with patch("aoe2hdcontrol.selected_objects_v2_8.inspect_selection", return_value=sample([2,1])):
            r=verify_selection(API(), make_selection_intent([1,2]))
        self.assertTrue(r["match"])
        self.assertEqual(r["execution"], "not_dispatched")
    def test_ordered(self):
        with patch("aoe2hdcontrol.selected_objects_v2_8.inspect_selection", return_value=sample([2,1])):
            self.assertFalse(verify_selection(API(), make_selection_intent([1,2]), ordered=True)["match"])
    def test_partial(self):
        with patch("aoe2hdcontrol.selected_objects_v2_8.inspect_selection", return_value=sample([1])):
            self.assertFalse(verify_selection(API(), make_selection_intent([1,2]))["match"])
    def test_unstable(self):
        with patch("aoe2hdcontrol.selected_objects_v2_8.inspect_selection", return_value=sample([1], "selection_changed")):
            r=verify_selection(API(), make_selection_intent([1]))
        self.assertFalse(r["match"])
        self.assertEqual(r["observed_ids"], [])
    def test_opt_in(self):
        a=API();a.allow_candidates=False
        with self.assertRaises(ObjectAPIError): verify_selection(a,make_selection_intent([1]))
    def test_invalid_intent(self):
        with self.assertRaises(ValueError): verify_selection(API(), {"object_ids":[1], "mode":"replace"})
if __name__ == "__main__":
    unittest.main()
