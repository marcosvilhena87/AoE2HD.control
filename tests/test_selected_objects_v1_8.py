import unittest
from aoe2hdcontrol.object_api import HDObject, ObjectAPIError
from aoe2hdcontrol.selected_objects_v1_8 import inspect, capture, compare

class Fake:
    allow_candidates=True
    def __init__(self, flags=(True,True), pointers=(0x200000,0x210000)):
        self.flags,self.pointers=flags,pointers
    def get_assigned_player(self):
        return type("Player",(),{"slot":1,"address":0x300000})()
    def _ptr(self,addr):
        return self.pointers[0] if addr-0x300000==0x15C else self.pointers[1]
    def get_object_by_id(self,oid):
        if oid not in (2191,2192):return None
        return HDObject(oid,0x200000 if oid==2191 else 0x210000,4,83,0x300000,None,())
    def _read(self,addr,fmt):
        i=0 if addr-0x38==0x200000 else 1
        return 0x200|(0x10000 if self.flags[i] else 0)

class Tests(unittest.TestCase):
    def test_multiple_flags(self):
        x=inspect(Fake(),[2191,2192])
        self.assertEqual(x["flagged_ids_among_probed"],[2191,2192])
        self.assertTrue(x["objects"][0]["matches_pointer_0x15c"])
        self.assertTrue(x["objects"][1]["matches_pointer_0x160"])
    def test_clear_preserves_other_bits(self):
        x=inspect(Fake(flags=(False,False),pointers=(0,0)),[2191,2192])
        self.assertEqual(x["flagged_ids_among_probed"],[])
        self.assertEqual(x["objects"][0]["selection_word_0x38"],512)
    def test_compare_and_missing(self):
        a=capture(Fake(flags=(False,False)),[2191,2192],"clear","s1")
        b=capture(Fake(),[2191,2192],"multi","s1")
        x=compare([a,b])
        self.assertEqual(x["phases"]["multi"][0]["flagged_ids"],[2191,2192])
        self.assertEqual(len(inspect(Fake(),[2191,9999])["errors"]),1)
    def test_bounds(self):
        with self.assertRaises(ValueError):inspect(Fake(),[2191,2191])
        with self.assertRaises(ValueError):capture(Fake(),[2191],"wrong","s1")
        with self.assertRaises(ValueError):compare([])
        f=Fake()
        f.allow_candidates=False
        with self.assertRaises(ObjectAPIError):inspect(f,[2191])

if __name__=="__main__":
    unittest.main()
