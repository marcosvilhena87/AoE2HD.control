import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch
from aoe2hdcontrol.object_validation_v1_5 import phase_capture, compare_phases, append_capture

def shot(phase, objects, session="test", errors=None):
    return {"schema":"hd-object-behavior-v1.5","session":session,"phase":phase,
            "capture":{"range":[2100,2300],"objects":objects,"errors":errors or []}}

def obj(oid, typ=109):
    return {"object_id":oid,"object_address":oid*100,
            "genie_type_id":typ,"class_id":3,"owner_slot":1,
            "owner_address":999,"candidate_position":[1,2]}

class Tests(unittest.TestCase):
    def test_differences(self):
        a=shot("baseline",[obj(2180),obj(2181,618)])
        b=shot("destroyed",[obj(2181,619),obj(2200)])
        c=compare_phases([a,b])["transitions"][0]
        self.assertEqual(c["appeared_ids"],[2200])
        self.assertEqual(c["disappeared_ids"],[2180])
        self.assertIn("genie_type_id",c["changed"][0]["fields"])
    def test_session_isolation(self):
        with self.assertRaises(ValueError):
            compare_phases([shot("baseline",[]),shot("selected",[],session="other")])
    def test_append(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"evidence.json"
            append_capture(path,shot("baseline",[]))
            self.assertEqual(len(append_capture(path,shot("selected",[]))),2)
            self.assertEqual(len(json.loads(path.read_text(encoding="utf-8"))),2)
            with self.assertRaises(ValueError):
                append_capture(path,shot("selected",[],session="other"))
    @patch("aoe2hdcontrol.object_validation_v1_5.collect")
    def test_capture(self, collect):
        collect.return_value={"range":[2100,2300],"objects":[],"errors":[]}
        x=phase_capture(object(),2100,2300,phase="selected",session="run1")
        self.assertEqual(x["phase"],"selected")
        with self.assertRaises(ValueError):
            phase_capture(object(),2100,2300,phase="invalid",session="run1")

if __name__ == "__main__":
    unittest.main()
