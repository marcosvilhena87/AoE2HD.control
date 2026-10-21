import struct
import unittest
from aoe2hdcontrol.selected_objects_v2_5 import inspect_selection
from aoe2hdcontrol.object_api import ObjectAPIError

BASE=0x200000

class Reader:
    def __init__(self,n,flip=False):
        self.n=n;self.flip=flip;self.calls=0
    def read(self,address,size):
        self.calls+=1
        count=size//4
        n=self.n if not (self.flip and self.calls==2) else self.n-1
        return struct.pack("<"+"I"*count,*([BASE+0x100*i for i in range(n)]+[0]*(count-n)))

class API:
    allow_candidates=True
    def __init__(self,n,flip=False):
        self.reader=Reader(n,flip)
    def get_assigned_player(self):
        return type("Player",(),{"slot":1,"address":0x300000})()
    def _read(self,addr,fmt):
        if (addr-BASE)%0x100==0x08:
            return (addr-BASE)//0x100
        if (addr-BASE)%0x100==0x38:
            return 0x10000
        raise ObjectAPIError("bad offset")
    def get_object_by_id(self,oid):
        if oid<0 or oid>63:return None
        return type("O",(),{"object_id":oid,"address":BASE+0x100*oid,
                            "class_id":4,"genie_type_id":83})()

class Tests(unittest.TestCase):
    def test_sixty(self):
        r=inspect_selection(API(60))
        self.assertEqual(r["consistency"],"stable_within_window")
        self.assertEqual(r["selected_count_verified"],60)
        self.assertEqual(r["first_zero_index"],60)
        self.assertEqual(r["selected_objects"][-1]["object_id"],59)
        self.assertEqual(r["completeness"],"unknown")
    def test_empty(self):
        self.assertEqual(inspect_selection(API(0))["selected_count_verified"],0)
    def test_full_window(self):
        r=inspect_selection(API(64))
        self.assertEqual(r["consistency"],"bounded_unterminated")
        self.assertTrue(r["window_exhausted"])
    def test_unstable(self):
        r=inspect_selection(API(60,flip=True))
        self.assertEqual(r["consistency"],"unstable")
        self.assertIsNone(r["selected_count_verified"])
    def test_guards(self):
        for n in (0,65,True):
            with self.assertRaises(ValueError):inspect_selection(API(0),max_entries=n)
        a=API(0);a.allow_candidates=False
        with self.assertRaises(ObjectAPIError):inspect_selection(a)
if __name__=="__main__":unittest.main()
