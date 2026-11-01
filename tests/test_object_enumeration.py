import unittest
from types import SimpleNamespace
from aoe2hdcontrol.object_api import ObjectAPIError
from aoe2hdcontrol.object_enumeration import enumerate_known_id_window


class FakeAPI:
    allow_candidates = True

    def __init__(self):
        self.seen = []

    def get_assigned_player(self):
        return SimpleNamespace(address=100)

    def get_object_by_id(self, oid):
        self.seen.append(oid)
        if oid == 2:
            raise ObjectAPIError("unreadable pointer")
        return {
            1: SimpleNamespace(object_id=1, class_id=4, genie_type_id=83, owner_address=100),
            3: SimpleNamespace(object_id=3, class_id=6, genie_type_id=74, owner_address=200),
            4: SimpleNamespace(object_id=4, class_id=3, genie_type_id=70, owner_address=None),
            5: SimpleNamespace(object_id=5, class_id=4, genie_type_id=293, owner_address=100),
        }.get(oid)


class EnumerationTests(unittest.TestCase):
    def test_no_gui_selection_dependency_and_owner_filter(self):
        api = FakeAPI()
        report = enumerate_known_id_window(api, start_id=0, stop_id=6)
        self.assertEqual([x["object_id"] for x in report["objects"]], [1, 5])
        self.assertEqual(api.seen, list(range(6)))
        self.assertEqual(report["completeness"], "unknown")
        self.assertEqual(report["coverage"], "explicit_id_window_only")
        self.assertEqual(len(report["rejected"]), 3)

    def test_type_filter(self):
        report = enumerate_known_id_window(FakeAPI(), start_id=0, stop_id=6,
                                            class_id=4, genie_type_id=293)
        self.assertEqual([x["object_id"] for x in report["objects"]], [5])

    def test_invalid_windows(self):
        for start, stop in ((0, 257), (-1, 1), (3, 3), (2, 1)):
            with self.subTest(start=start, stop=stop):
                with self.assertRaises(ValueError):
                    enumerate_known_id_window(FakeAPI(), start_id=start, stop_id=stop)

    def test_explicit_opt_in(self):
        api = FakeAPI()
        api.allow_candidates = False
        with self.assertRaises(ObjectAPIError):
            enumerate_known_id_window(api, start_id=0, stop_id=1)

    def test_other_owners_visible_only_with_opt_out(self):
        report = enumerate_known_id_window(FakeAPI(), start_id=0, stop_id=6,
                                            own_only=False)
        self.assertEqual([x["object_id"] for x in report["objects"]], [1, 3, 4, 5])


if __name__ == "__main__":
    unittest.main()
