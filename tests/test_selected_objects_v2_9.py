import unittest
from aoe2hdcontrol.selected_objects_v2_8 import make_selection_intent
from aoe2hdcontrol.selected_objects_v2_9 import (
    dispatch_selection, DispatchUnavailable, evaluate_external_transition)

def snapshot(ids, *, stable=True):
    return {"schema":"hd-selected-v2.7",
            "consistency":"stable_with_candidate_count" if stable else "selection_changed",
            "selected_objects":[{"object_id":i} for i in ids],
            "selected_count_verified":len(ids) if stable else None}

class Tests(unittest.TestCase):
    def setUp(self):
        self.intent=make_selection_intent([4])
    def test_fail_closed(self):
        with self.assertRaises(DispatchUnavailable):
            dispatch_selection(self.intent)
    def test_never_call_backend(self):
        class Trap:
            def __getattr__(self, name):
                raise AssertionError("backend must never be used")
            def __call__(self, *args):
                raise AssertionError("backend must never be called")
        with self.assertRaises(DispatchUnavailable):
            dispatch_selection(self.intent, backend=Trap())
    def test_external_transition(self):
        r=evaluate_external_transition(self.intent,snapshot([3]),snapshot([4]))
        self.assertEqual(r["status"],"external_transition_observed")
        self.assertEqual(r["execution"],"not_dispatched")
        self.assertEqual(r["causality"],"unproven")
    def test_already_selected(self):
        r=evaluate_external_transition(self.intent,snapshot([4]),snapshot([4]))
        self.assertEqual(r["status"],"already_selected_before")
    def test_mismatch(self):
        r=evaluate_external_transition(self.intent,snapshot([3]),snapshot([5]))
        self.assertEqual(r["status"],"target_not_observed")
    def test_unstable(self):
        r=evaluate_external_transition(self.intent,snapshot([3],stable=False),snapshot([4]))
        self.assertEqual(r["status"],"inconclusive_snapshot")
    def test_invalid_intent(self):
        with self.assertRaises(ValueError):
            evaluate_external_transition({"object_ids":[4]},snapshot([3]),snapshot([4]))
    def test_invalid_report(self):
        with self.assertRaises(ValueError):
            evaluate_external_transition(self.intent,{"schema":"other"},snapshot([4]))
    def test_duplicate_observation(self):
        r=evaluate_external_transition(self.intent,snapshot([3,3]),snapshot([4]))
        self.assertEqual(r["status"],"inconclusive_snapshot")
if __name__=="__main__":
    unittest.main()
