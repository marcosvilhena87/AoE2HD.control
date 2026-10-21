import unittest
from unittest.mock import patch
from aoe2hdcontrol.selected_objects_v2_7 import inspect_selection, get_selected_count
from aoe2hdcontrol.object_api import ObjectAPIError


class API:
    allow_candidates = True


def shot(pairs, consistency="consistent_with_candidate_count"):
    return {
        "consistency": consistency,
        "count_before": len(pairs),
        "selected_objects": [
            {"object_id": oid, "address": addr} for oid, addr in pairs
        ] if consistency == "consistent_with_candidate_count" else [],
    }


class SelectionV27Tests(unittest.TestCase):
    def test_stable_empty(self):
        with patch("aoe2hdcontrol.selected_objects_v2_7.inspect_v26",
                   side_effect=[shot([]), shot([])]):
            report = inspect_selection(API())
        self.assertEqual(report["selected_count_verified"], 0)
        self.assertEqual(report["consistency"], "repeated_observations_agree")
        self.assertFalse(report["atomic"])

    def test_stable_sixty(self):
        pairs = [(i, 0x200000 + 256*i) for i in range(60)]
        with patch("aoe2hdcontrol.selected_objects_v2_7.inspect_v26",
                   side_effect=[shot(pairs), shot(pairs)]):
            report = inspect_selection(API())
        self.assertEqual(report["selected_count_verified"], 60)

    def test_identity_swap_same_count_rejected(self):
        with patch("aoe2hdcontrol.selected_objects_v2_7.inspect_v26",
                   side_effect=[shot([(1, 0x200000)]), shot([(2, 0x200100)])]):
            report = inspect_selection(API())
        self.assertIsNone(report["selected_count_verified"])
        self.assertEqual(report["selected_objects"], [])
        self.assertEqual(report["consistency"], "selection_changed_same_or_different_count")

    def test_order_change_rejected(self):
        a = [(1, 0x200000), (2, 0x200100)]
        with patch("aoe2hdcontrol.selected_objects_v2_7.inspect_v26",
                   side_effect=[shot(a), shot(list(reversed(a)))]):
            self.assertIsNone(inspect_selection(API())["selected_count_verified"])

    def test_invalid_observation_rejected(self):
        with patch("aoe2hdcontrol.selected_objects_v2_7.inspect_v26",
                   side_effect=[shot([(1, 0x200000)]), shot([], "counter_changed")]):
            self.assertEqual(inspect_selection(API())["consistency"], "unstable_or_invalid_observation")

    def test_opt_in_required(self):
        api = API()
        api.allow_candidates = False
        with self.assertRaises(ObjectAPIError):
            inspect_selection(api)


if __name__ == "__main__":
    unittest.main()
