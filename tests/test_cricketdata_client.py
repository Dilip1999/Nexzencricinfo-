import unittest
from unittest.mock import Mock
from nexzen.providers.cricketdata import CricketDataClient, CricketDataError

class Response:
    def __init__(self, payload, status_code=200):
        self.payload, self.status_code = payload, status_code
    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("HTTP error")
    def json(self):
        return self.payload

class CricketDataClientTests(unittest.TestCase):
    def client(self, payload):
        session = Mock()
        session.get.return_value = Response(payload)
        return CricketDataClient("test-secret", session=session), session

    def test_matches_endpoint_and_auth_parameter(self):
        client, session = self.client({"status":"success","data":[{"id":"m1"}]})
        self.assertEqual(client.matches()["data"][0]["id"], "m1")
        args, kwargs = session.get.call_args
        self.assertEqual(args[0], "https://api.cricapi.com/v1/matches")
        self.assertEqual(kwargs["params"]["apikey"], "test-secret")
        self.assertEqual(kwargs["params"]["offset"], 0)
        self.assertNotIn("test-secret", str(kwargs["headers"]))

    def test_scorecard_uses_match_id(self):
        client, session = self.client({"status":"success","data":{"scorecard":[]}})
        client.scorecard("match-123")
        self.assertEqual(session.get.call_args.kwargs["params"]["id"], "match-123")

    def test_missing_key_fails_before_network(self):
        client = CricketDataClient("", session=Mock())
        with self.assertRaises(CricketDataError): client.matches()

    def test_provider_failure_is_surfaced(self):
        client, _ = self.client({"status":"failure","reason":"quota exceeded"})
        with self.assertRaisesRegex(CricketDataError, "quota exceeded"): client.matches()

    def test_invalid_offset_rejected(self):
        client, session = self.client({"status":"success","data":[]})
        with self.assertRaises(ValueError): client.matches(-1)
        session.get.assert_not_called()

    def test_empty_player_query_rejected(self):
        client, session = self.client({"status":"success","data":[]})
        with self.assertRaises(ValueError): client.player_search(" ")
        session.get.assert_not_called()

if __name__ == "__main__": unittest.main()
