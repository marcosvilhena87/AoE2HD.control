import struct
import tempfile
import unittest
from pathlib import Path
from aoe2hdcontrol.selected_objects_v2_3 import capture,append,compare

class Reader:
    def read(self,addr,size):
        if size==64:
            raw=bytearray(size)
            struct.pack_into("<I",raw,0,7)
            return bytes(raw)
        return bytes(size)

class API:
    allow_candidates=True
    reader=Reader()
    def get_assigned_player(self):
        return type("P",(),{"slot":1,"address":0x300000})()
    def get_object_by_id(self,oid):return None

class Tests(unittest.TestCase):
    def test_capture(self):
        x=capture(API(),"clear","s")
        self.assertEqual(x["enumeration"]["selected_count_verified"],0)
        self.assertEqual(x["nearby_words"][0]["offset"],"0x120")
        self.assertEqual(x["nearby_words"][0]["value"],7)
    def test_compare_append(self):
        a=capture(API(),"clear","s")
        b=capture(API(),"four","s")
        b["nearby_words"][0]["value"]=4
        r=compare([a,b])
        self.assertEqual(r["nearby_changing_words"][0]["offset"],"0x120")
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"data.json"
            append(p,a)
            self.assertEqual(len(append(p,b)),2)
            with self.assertRaises(ValueError):append(p,b)
    def test_validation(self):
        with self.assertRaises(ValueError):capture(API(),"unknown","s")
        with self.assertRaises(ValueError):capture(API(),"clear","s",max_entries=33)
        with self.assertRaises(ValueError):compare([])
        a=capture(API(),"clear","s")
        b=capture(API(),"four","other")
        with self.assertRaises(ValueError):compare([a,b])
if __name__=="__main__":unittest.main()
