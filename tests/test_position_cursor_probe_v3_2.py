import unittest
from aoe2hdcontrol.position_cursor_probe_v3_2 import probe_unit_position,capture_position_cursor_series
from aoe2hdcontrol.object_api import ObjectAPIError

class Object:
    address=0x20000
    class_id=4
    genie_type_id=83

class API:
    allow_candidates=True
    def get_object_by_id(self,oid):return Object()
    def _read(self,addr,fmt):return {0x2003c:21.5,0x20040:42.25}[addr]

class Tests(unittest.TestCase):
    def test_candidate_position(self):
        r=probe_unit_position(API(),2630)
        self.assertEqual((r["candidate_world_x"],r["candidate_world_y"]),(21.5,42.25))
        self.assertFalse(r["validated_world_position"])
    def test_reject_without_opt_in(self):
        a=API();a.allow_candidates=False
        with self.assertRaises(ObjectAPIError):probe_unit_position(a,2630)
    def test_samples(self):
        r=capture_position_cursor_series(API(),pid=22,object_id=2630,samples=3,
           cursor_reader=lambda pid:{"game_foreground":True,"client":{"x":10,"y":20}},
           sleep=lambda n:None)
        self.assertEqual(len(r["readings"]),3)
        self.assertEqual(r["game_cursor_world_coordinates"],"unknown")
    def test_invalid_arguments(self):
        for kwargs in ({"pid":0},{"samples":0},{"samples":61},{"interval":0},{"object_id":True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                capture_position_cursor_series(API(),cursor_reader=lambda p:None,
                    sleep=lambda n:None,**({"pid":22,"object_id":2630}|kwargs))
if __name__=="__main__":unittest.main()
