import unittest
from unittest.mock import patch
from aoe2hdcontrol.selection_investigation_v3_0 import investigate_manual_selection

def capture(oid, player=123):
    return {"schema":"hd-selected-v2.7","consistency":"stable_with_candidate_count",
            "player_address":player,"local_slot":1,
            "selected_count_verified":1,"selected_objects":[{"object_id":oid}]}

class API:
    allow_candidates=True

class Tests(unittest.TestCase):
    def test_observed_manual_transition(self):
        with patch("aoe2hdcontrol.selection_investigation_v3_0.inspect_selection",
                   side_effect=[capture(1),capture(2)]):
            r=investigate_manual_selection(API(),[2],pause_for_manual_action=lambda: None,pid=1234)
        self.assertEqual(r["status"],"external_transition_observed")
        self.assertEqual(r["execution"],"not_dispatched")
        self.assertEqual(r["pid"],1234)
    def test_context_changed(self):
        with patch("aoe2hdcontrol.selection_investigation_v3_0.inspect_selection",
                   side_effect=[capture(1),capture(2,321)]):
            r=investigate_manual_selection(API(),[2],pause_for_manual_action=lambda: None,pid=1234)
        self.assertEqual(r["status"],"player_context_changed")
        self.assertIsNone(r["transition"])
    def test_pause_once(self):
        pauses=[]
        with patch("aoe2hdcontrol.selection_investigation_v3_0.inspect_selection",
                   side_effect=[capture(1),capture(2)]):
            investigate_manual_selection(API(),[2],pause_for_manual_action=lambda:pauses.append(1),pid=1)
        self.assertEqual(pauses,[1])
    def test_invalid_pid(self):
        with self.assertRaises(ValueError):
            investigate_manual_selection(API(),[2],pause_for_manual_action=lambda:None,pid=0)
    def test_opt_in(self):
        a=API();a.allow_candidates=False
        with self.assertRaises(ValueError):
            investigate_manual_selection(a,[2],pause_for_manual_action=lambda:None,pid=1)
    def test_invalid_pause(self):
        with self.assertRaises(TypeError):
            investigate_manual_selection(API(),[2],pause_for_manual_action=None,pid=1)
if __name__=="__main__":
    unittest.main()
