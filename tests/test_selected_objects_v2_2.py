import struct
import unittest
from aoe2hdcontrol.selected_objects_v2_2 import enumerate_selected,get_selected_objects,get_selected_count
from aoe2hdcontrol.object_api import ObjectAPIError

class Reader:
    def __init__(self, values):self.values=values
    def read(self,addr,size):
        data=self.values+[0]*(size//4-len(self.values))
        return struct.pack("<"+"I"*len(data),*data)

class API:
    allow_candidates=True
    def __init__(self,values):
        self.reader=Reader(values)
    def get_assigned_player(self):
        return type("P",(),{"slot":1,"address":0x300000})()
    def _read(self,addr,fmt):
        if addr%0x10000==8:return {0x200008:1,0x210008:2,0x220008:3}.get(addr,999999)
        return 0x10000 if addr!=0x220038 else 0
    def get_object_by_id(self,oid):
        if oid not in (1,2,3):return None
        return type("O",(),{"object_id":oid,"address":0x200000+(oid-1)*0x10000,
                            "class_id":4,"genie_type_id":83})()

class Tests(unittest.TestCase):
    def test_verified_and_count(self):
        a=API([0x200000,0x210000,0x220000,0])
        r=enumerate_selected(a,max_entries=4)
        self.assertEqual([o["object_id"] for o in r["selected_objects"]],[1,2])
        self.assertEqual(r["slots"][2]["status"],"selection_bit_inactive")
        self.assertEqual(get_selected_count(a,max_entries=4),2)
        self.assertEqual(len(get_selected_objects(a,max_entries=4)),2)
    def test_zero_not_terminator_and_duplicate(self):
        r=enumerate_selected(API([0x200000,0,0x200000,0x210000]),max_entries=4)
        self.assertTrue(r["nonzero_after_first_zero"])
        self.assertEqual(r["slots"][2]["status"],"duplicate_selected")
        self.assertEqual(r["selected_count_verified"],2)
    def test_limits(self):
        with self.assertRaises(ValueError):enumerate_selected(API([]),max_entries=33)
        a=API([])
        a.allow_candidates=False
        with self.assertRaises(ObjectAPIError):enumerate_selected(a)
if __name__=="__main__":unittest.main()
