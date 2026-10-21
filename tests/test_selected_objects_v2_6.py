import struct
import unittest
from aoe2hdcontrol.selected_objects_v2_6 import inspect_selection
from aoe2hdcontrol.object_api import ObjectAPIError

BASE=0x200000

class Reader:
    def __init__(self,count,seq=None):
        self.count=count
        self.seq=iter(seq or [count,count,count])
    def read(self,address,size):
        return struct.pack("<"+"I"*(size//4),
            *(BASE+0x100*i for i in range(size//4)))

class API:
    allow_candidates=True
    def __init__(self,n,seq=None,bad=False):
        self.reader=Reader(n,seq)
        self.bad=bad
    def get_assigned_player(self):
        return type("P",(),{"slot":1,"address":0x300000})()
    def _read(self,address,fmt):
        if address==0x300254:return next(self.reader.seq)
        delta=address-BASE
        if delta%0x100==8:return delta//0x100
        if delta%0x100==0x38:return 0 if self.bad else 0x10000
        raise ObjectAPIError("Invalid")
    def get_object_by_id(self,oid):
        return type("O",(),{"address":BASE+0x100*oid,
                      "class_id":4,"genie_type_id":83})()

class Tests(unittest.TestCase):
    def test_empty(self):
        r=inspect_selection(API(0))
        self.assertEqual(r["selected_count_verified"],0)
        self.assertEqual(r["consistency"],"consistent_with_candidate_count")
    def test_sixty(self):
        r=inspect_selection(API(60))
        self.assertEqual(r["selected_count_verified"],60)
        self.assertEqual(r["entries"][-1]["offset"],"0x24C")
        self.assertEqual(r["completeness"],"unknown")
    def test_counter_changed(self):
        r=inspect_selection(API(4,seq=[4,5,5]))
        self.assertEqual(r["consistency"],"counter_changed")
        self.assertIsNone(r["selected_count_verified"])
    def test_invalid_count_and_flag(self):
        self.assertEqual(inspect_selection(API(61,seq=[61]))["consistency"],"invalid_count")
        r=inspect_selection(API(4,bad=True))
        self.assertEqual(r["consistency"],"invalid_entries")
    def test_opt_in(self):
        a=API(0);a.allow_candidates=False
        with self.assertRaises(ObjectAPIError):inspect_selection(a)
if __name__=="__main__":unittest.main()
