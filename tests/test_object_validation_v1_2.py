"""Regressão offline para o scan v1.2."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from aoe2hdcontrol.object_validation_v1_2 import scan_buildings
from aoe2hdcontrol.object_api import ObjectAPIError


def object_(oid, klass=3, typ=109, owner=0x200000):
    return SimpleNamespace(object_id=oid, address=0x300000 + oid * 4,
                           class_id=klass, genie_type_id=typ, owner_address=owner)


class Dummy:
    allow_candidates = True
    def __init__(self):
        self.objects = {2186: object_(2186), 2187: object_(2187, 3, 620, 0x210000),
                        2188: object_(2188, 3, 620, 0x210000),
                        2189: object_(2189, 4, 83)}
    def get_object_by_id(self, oid):
        return self.objects.get(oid)


class Tests(unittest.TestCase):
    def test_local_filters(self):
        with patch("aoe2hdcontrol.object_validation_v1_2._players",
                   return_value=(1, {0x100000: 0, 0x200000: 1, 0x210000: 2})):
            result = scan_buildings(Dummy(), 2186, 2190)
        self.assertEqual([v["object_id"] for v in result["matches"]], [2186])
        self.assertEqual(result["counters"]["other_owners"], 2)
        self.assertEqual(result["counters"]["other_classes"], 1)

    def test_all_owners_and_type(self):
        with patch("aoe2hdcontrol.object_validation_v1_2._players",
                   return_value=(1, {0x200000: 1, 0x210000: 2})):
            result = scan_buildings(Dummy(), 2186, 2188, only_local=False, target_type=620)
        self.assertEqual(len(result["matches"]), 2)
        self.assertTrue(all(not m["is_local"] for m in result["matches"]))

    def test_bounds(self):
        with self.assertRaises(ValueError):
            scan_buildings(Dummy(), 0, 512)
        with self.assertRaises(ValueError):
            scan_buildings(Dummy(), 30, 20)
        obj = Dummy()
        obj.allow_candidates = False
        with self.assertRaises(ObjectAPIError):
            scan_buildings(obj, 2188, 2188)

    def test_errors_counted(self):
        class Faulty(Dummy):
            def get_object_by_id(self, oid):
                if oid == 2187:
                    raise ObjectAPIError("Falha leitura em 0x00123456")
                return super().get_object_by_id(oid)
        with patch("aoe2hdcontrol.object_validation_v1_2._players",
                   return_value=(1, {0x200000: 1, 0x210000: 2})):
            result = scan_buildings(Faulty(), 2186, 2188)
        self.assertEqual(result["counters"]["read_errors"], 1)
        self.assertEqual(len(result["error_samples"]), 1)


if __name__ == "__main__":
    unittest.main()
