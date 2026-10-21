import unittest
from aoe2hdcontrol.object_api import HDObject, ObjectAPIError
from aoe2hdcontrol.selected_object_v1_7 import inspect

class Stub:
    allow_candidates = True
    def __init__(self, ref=0x200000, word=0x10000):
        self.ref, self.word = ref, word
    def get_assigned_player(self):
        return type("Player", (), {"slot":1, "address":0x300000})()
    def _ptr(self, addr):
        return self.ref
    def _read(self, addr, fmt):
        return self.word
    def get_object_by_id(self, oid):
        if oid == 2180:
            return HDObject(oid,0x200000,3,109,0x300000,None,())
        if oid == 2190:
            return HDObject(oid,0x210000,4,83,0x300000,None,())
        return None

class Tests(unittest.TestCase):
    def test_selected_tc(self):
        result=inspect(Stub(),[2180,2190])
        self.assertTrue(result["objects"][0]["selection_bit_16_candidate"])
        self.assertTrue(result["objects"][0]["matches_player_0x15C"])
        self.assertFalse(result["objects"][1]["matches_player_0x160"])
    def test_deselected(self):
        result=inspect(Stub(ref=0,word=0),[2180])
        self.assertFalse(result["objects"][0]["matches_player_0x15C"])
        self.assertFalse(result["objects"][0]["selection_bit_16_candidate"])
    def test_missing_and_candidates(self):
        self.assertEqual(len(inspect(Stub(),[2180,9999])["errors"]),1)
        a=Stub()
        a.allow_candidates=False
        with self.assertRaises(ObjectAPIError): inspect(a,[2180])
        with self.assertRaises(ValueError): inspect(Stub(),[2180,2180])

if __name__ == "__main__":
    unittest.main()
