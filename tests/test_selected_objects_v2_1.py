import struct
import tempfile
import unittest
from pathlib import Path
from aoe2hdcontrol.selected_objects_v2_1 import capture,append,compare
from aoe2hdcontrol.object_api import ObjectAPIError

class Reader:
    def read(self,address,size):
        buf=bytearray(size)
        for offset,value in ((0x15c,0x200000),(0x160,0x210000),(0x164,0x220000),(0x168,0x200000)):
            struct.pack_into("<I",buf,offset-0x150,value)
        return bytes(buf)

class API:
    allow_candidates=True
    reader=Reader()
    def get_assigned_player(self):return type("P",(),{"slot":1,"address":0x300000})()
    def get_object_by_id(self,oid):
        if oid not in (1,2,3):return None
        return type("O",(),{"address":0x200000+(oid-1)*0x10000,"class_id":4,"genie_type_id":83})()
    def _read(self,addr,fmt):return 0x10000

class Tests(unittest.TestCase):
    def test_slots(self):
        shot=capture(API(),[1,2,3],"trio","s")
        known={s["offset"]:s["known_object_id"] for s in shot["slots"] if s["known_object_id"] is not None}
        self.assertEqual(known,{"0x15C":1,"0x160":2,"0x164":3,"0x168":1})
        self.assertEqual(len(shot["slots"]),24)
        self.assertEqual(shot["objects"][0]["selected_candidate"],True)
    def test_compare_and_append(self):
        a=capture(API(),[1,2,3],"clear","s")
        b=capture(API(),[1,2,3],"trio","s")
        b["slots"][3]["value"]=0x1234
        out=compare([a,b])
        self.assertEqual(out["changed_slots"][0]["offset"],"0x15C")
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"shots.json"
            self.assertEqual(len(append(path,a)),1)
            self.assertEqual(len(append(path,b)),2)
            with self.assertRaises(ValueError):append(path,b)
    def test_guards(self):
        with self.assertRaises(ValueError):capture(API(),[1,1],"trio","s")
        with self.assertRaises(ValueError):capture(API(),[1],"wrong","s")
        with self.assertRaises(ValueError):compare([])
        api=API()
        api.allow_candidates=False
        with self.assertRaises(ObjectAPIError):capture(api,[1],"clear","s")
if __name__=="__main__":unittest.main()
