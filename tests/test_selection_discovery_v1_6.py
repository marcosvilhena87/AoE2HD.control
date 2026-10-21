import unittest
from unittest.mock import patch
from aoe2hdcontrol.selection_discovery_v1_6 import compare, capture

def make(phase, raw):
    return {"schema":"hd-selection-v1.6","session":"s1","phase":phase,"ids":[2180],
            "regions":{"player_local":{"address":0x10000,"size":8,"hex":raw}},
            "errors":[]}

class Tests(unittest.TestCase):
    def test_reversible_selection(self):
        x=compare([make("baseline","0000000000000000"),
                   make("tc_selected","0100000000000000"),
                   make("deselected","0000000000000000")])
        self.assertEqual(len(x["reversible_candidates"]),1)
        self.assertEqual(x["reversible_candidates"][0]["offset"],"0x0")
    def test_no_false_positive(self):
        x=compare([make("baseline","00000000"),
                   make("tc_selected","01000000"),
                   make("deselected","02000000")])
        self.assertFalse(x["reversible_candidates"])
    def test_reject_sessions(self):
        b=make("tc_selected","01000000")
        b["session"]="s2"
        with self.assertRaises(ValueError):
            compare([make("baseline","00000000"),b,make("deselected","00000000")])
    def test_capture_readonly(self):
        class Reader:
            def read(self,address,size): return bytes([0])*size
        class Api:
            allow_candidates=True
            reader=Reader()
            def get_assigned_player(self):
                return type("Player",(),{"slot":1,"address":0x100000})()
            def get_object_by_id(self,oid):
                return type("Obj",(),{"address":0x200000})()
        shot=capture(Api(),"baseline","s1",[2180],object_bytes=16,player_bytes=16)
        self.assertEqual(shot["errors"],[])
        self.assertEqual(len(shot["regions"]),2)

if __name__=="__main__":
    unittest.main()
