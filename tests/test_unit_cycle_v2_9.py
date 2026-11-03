import unittest
from unittest.mock import patch

from aoe2hdcontrol.object_api import HDObject, ObjectAPIError
from aoe2hdcontrol.unit_cycle_v2_9 import (
    make_move_request, identify, observe_selection, dispatch_move,
    verify_observed_movement,
)


class MockAPI:
    allow_candidates = True

    def get_assigned_player(self):
        return type("Player", (), {"address": 0x100000})()

    def get_object_by_id(self, object_id):
        return HDObject(object_id, 0x200000 + object_id * 4, 1, 83,
                        0x100000, None, ("Object+0x10",))


class Transport:
    def __init__(self, accepted=True):
        self.accepted = accepted
        self.calls = []

    def dispatch_move(self, request):
        self.calls.append(request)
        return self.accepted


def selection(request):
    return {"schema": "hd-unit-cycle-v2.9", "session": request.session,
            "requested_ids": list(request.object_ids), "matches": True,
            "snapshot_consistency": "stable_with_candidate_count"}


class UnitCycleTests(unittest.TestCase):
    def setUp(self):
        self.req = make_move_request([42, 43], (10, 20), session="local-01")

    def test_validate_request(self):
        for ids in ([], [42, 42], [True], ["42"], list(range(61))):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                make_move_request(ids, (10, 20), session="local")
        for target in ((float("nan"), 2), (float("inf"), 2), (1,), ("1", 2)):
            with self.subTest(target=target), self.assertRaises(ValueError):
                make_move_request([1], target, session="local")
        with self.assertRaises(ValueError):
            make_move_request([1], (1, 2), session="")

    def test_identification(self):
        report = identify(MockAPI(), self.req)
        self.assertEqual([x["object_id"] for x in report["objects"]], [42, 43])
        self.assertEqual(report["stage"], "identified_candidate")

    def test_reject_wrong_owner_and_missing_object(self):
        api = MockAPI()
        with patch.object(api, "get_object_by_id", return_value=None):
            with self.assertRaises(ObjectAPIError): identify(api, self.req)
        other = HDObject(42, 0x222000, 1, 83, 0x999999, None, ())
        with patch.object(api, "get_object_by_id", return_value=other):
            with self.assertRaises(ObjectAPIError): identify(api, self.req)
        api.allow_candidates = False
        with self.assertRaises(ObjectAPIError): identify(api, self.req)

    def test_observe_selection_only(self):
        sample = {"consistency": "stable_with_candidate_count",
                  "selected_objects": [{"object_id": 43}, {"object_id": 42}]}
        with patch("aoe2hdcontrol.unit_cycle_v2_9.inspect_selection", return_value=sample):
            report = observe_selection(MockAPI(), self.req)
        self.assertTrue(report["matches"])
        self.assertFalse(report["selection_dispatched"])

    def test_selection_change_blocks(self):
        sample = {"consistency": "selection_changed", "selected_objects": []}
        with patch("aoe2hdcontrol.unit_cycle_v2_9.inspect_selection", return_value=sample):
            report = observe_selection(MockAPI(), self.req)
        with self.assertRaises(ObjectAPIError):
            dispatch_move(self.req, transport=Transport(), offline_confirmed=True,
                          selection=report)

    def test_no_default_dispatch_or_without_confirmation(self):
        with self.assertRaises(ObjectAPIError):
            dispatch_move(self.req, selection=selection(self.req))
        with self.assertRaises(ObjectAPIError):
            dispatch_move(self.req, selection=selection(self.req),
                          offline_confirmed=True)

    def test_transport_ack_is_not_execution(self):
        driver = Transport()
        receipt = dispatch_move(self.req, selection=selection(self.req),
                                offline_confirmed=True, transport=driver)
        self.assertEqual(len(driver.calls), 1)
        self.assertTrue(receipt["accepted"])
        self.assertEqual(receipt["executed"], "unverified")
        self.assertEqual(receipt["movement"], "unverified")

    def test_transport_reject_and_malformed_ack(self):
        receipt = dispatch_move(self.req, selection=selection(self.req),
                                offline_confirmed=True, transport=Transport(False))
        self.assertFalse(receipt["accepted"])
        with self.assertRaises(ObjectAPIError):
            dispatch_move(self.req, selection=selection(self.req),
                          offline_confirmed=True, transport=Transport("yes"))

    def test_observation_is_not_causation(self):
        receipt = dispatch_move(self.req, selection=selection(self.req),
                                offline_confirmed=True, transport=Transport())
        before = {42: (0, 0), 43: (1, 1)}
        after = {42: (10, 20), 43: (10, 20)}
        observed = verify_observed_movement(self.req, receipt, before, after)
        self.assertEqual(observed["status"], "arrival_observed")
        self.assertEqual(observed["executed"], "unverified")
        self.assertEqual(observed["causality"], "not_established")

    def test_missing_evidence_and_wrong_receipt(self):
        receipt = dispatch_move(self.req, selection=selection(self.req),
                                offline_confirmed=True, transport=Transport())
        self.assertEqual(verify_observed_movement(
            self.req, receipt, {42: (0, 0)}, {42: (10, 20)})["status"], "unverified")
        with self.assertRaises(ValueError):
            verify_observed_movement(self.req, {"accepted": True}, {}, {})


if __name__ == "__main__":
    unittest.main()
