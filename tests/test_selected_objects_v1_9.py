import unittest
from aoe2hdcontrol.selected_objects_v1_9 import capture, compare

class Fake:
    allow_candidates=True
    def get_assigned_player(self):return type("P",(),{"slot":1,"address":0x300000})()
    def _ptr(self,addr):return 0x200000 if addr-0x300000==0x15c else 0x220000
    def get_object_by_id(self,oid):
        if oid not in (1,2,3): return None
        return type("O",(),{"object_id":oid,"address":0x200000+(oid-1)*0x10000,
          "class_id":4,"genie_type_id":83,"owner_address":0x300000})()
    def _read(self,addr,fmt):return 0x10200

class Tests(unittest.TestCase):
    def test_three_selected(self):
        a=capture(Fake(),[1,2,3],"session","multi_abc")
        b=capture(Fake(),[1,2,3],"session","multi_cba")
        x=compare([a,b])
        self.assertEqual(x["phases"]["multi_abc"]["flagged_count_among_probed"],3)
        self.assertTrue(x["order_comparison"]["same_pointer_ids"])
    def test_bounds(self):
        with self.assertRaises(ValueError):capture(Fake(),[1,2],"s","multi_abc")
        with self.assertRaises(ValueError):capture(Fake(),[1,2,3],"s","bad")
    def test_consistency(self):
        a=capture(Fake(),[1,2,3],"s","multi_abc")
        b=capture(Fake(),[1,2,3],"t","multi_cba")
        with self.assertRaises(ValueError):compare([a,b])
        with self.assertRaises(ValueError):compare([a,a])
if __name__=="__main__":unittest.main()
