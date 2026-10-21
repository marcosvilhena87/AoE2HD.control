import struct
import unittest
from aoe2hdcontrol.object_api import ObjectAPIError
from aoe2hdcontrol.selected_objects_v2_0 import (
    is_object_selected,get_selected_objects,get_selected_count,diagnose)

class Reader:
    def read(self,address,size):
        raw=bytearray(size)
        struct.pack_into("<I",raw,0x15c,0x200000)
        struct.pack_into("<I",raw,0x160,0x210000)
        return bytes(raw)

class API:
    allow_candidates=True
    reader=Reader()
    def get_assigned_player(self):
        return type("P",(),{"slot":1,"address":0x300000})()
    def get_object_by_id(self,oid):
        if oid not in (1,2,3):return None
        return type("O",(),{"object_id":oid,"address":0x200000+(oid-1)*0x10000,
                    "class_id":4,"genie_type_id":83})()
    def _read(self,address,fmt):
        return 0x10200 if address in (0x200038,0x210038) else 0x200

class Tests(unittest.TestCase):
    def test_selected(self):
        api=API()
        self.assertTrue(is_object_selected(api,1))
        self.assertFalse(is_object_selected(api,3))
        self.assertIsNone(is_object_selected(api,999))
        self.assertEqual([o.object_id for o in get_selected_objects(api,[1,2,3])],[1,2])
        self.assertEqual(get_selected_count(api,[1,2,3]),2)
    def test_bounded_diagnostic(self):
        out=diagnose(API(),[1,2,3])
        self.assertEqual(out["flagged_ids_among_probed"],[1,2])
        self.assertEqual([x["player_offset"] for x in out["player_pointer_matches"]],["0x15C","0x160"])
        self.assertEqual(out["scanned_player_bytes"],512)
    def test_validation(self):
        with self.assertRaises(ValueError):diagnose(API(),[1,1,2])
        with self.assertRaises(ValueError):diagnose(API(),[1,2,3],player_scan_bytes=513)
        api=API()
        api.allow_candidates=False
        with self.assertRaises(ObjectAPIError):get_selected_objects(api,[1])
        with self.assertRaises(ObjectAPIError):diagnose(api,[1,2,3])
if __name__=="__main__":unittest.main()
