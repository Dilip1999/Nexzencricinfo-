import unittest
from unittest.mock import Mock
import requests
from nexzen.providers.cricketdata import CricketDataClient, CricketDataError

class Response:
    status_code = 200
    def __init__(self, payload, status_code=200):
        self.payload, self.status_code = payload, status_code
    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError("HTTP error")
    def json(self):
        return self.payload

class CricketDataClientTests(unittest.TestCase):
    def client(self, payload, status=200):
        session = Mock()
        session.get.return_value = Response(payload, status)
        return CricketDataClient("test-secret", session=session), session

    def test_matches_uses_bearer_auth(self):
        client, session = self.client({"data":[{"match":"m1"}],"meta":{"plan":"free"}})
        self.assertEqual(client.matches()["data"][0]["match"], "m1")
        args, kwargs = session.get.call_args
        self.assertEqual(args[0], "https://api.cricketdatabase.com/v1/matches")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-secret")
        self.assertNotIn("test-secret", str(kwargs["params"]))

    def test_yesterdays_results_endpoint(self):
        client, session = self.client({"data":[]})
        client.results_yesterday()
        self.assertEqual(session.get.call_args.args[0], "https://api.cricketdatabase.com/v1/results/yesterday")

    def test_scorecard_uses_documented_match_address(self):
        client, session = self.client({"data":{"innings":[]}})
        client.scorecard("2026-11-10-team-a-v-team-b")
        self.assertTrue(session.get.call_args.args[0].endswith("/matches/2026-11-10-team-a-v-team-b/scorecard"))

    def test_player_stats_endpoint(self):
        client, session = self.client({"data":{"batting":[]}})
        client.player_stats("joe-root")
        self.assertTrue(session.get.call_args.args[0].endswith("/players/joe-root/stats"))

    def test_missing_key_fails_before_network(self):
        session = Mock()
        with self.assertRaises(CricketDataError):
            CricketDataClient("", session=session).matches()
        session.get.assert_not_called()

    def test_provider_http_error_does_not_leak_key(self):
        client, _ = self.client({"data":[]}, 403)
        with self.assertRaisesRegex(CricketDataError, "HTTP error"):
            client.matches()

    def test_invalid_slug_rejected(self):
        client, session = self.client({"data":[]})
        with self.assertRaises(ValueError):
            client.scorecard("../private")
        session.get.assert_not_called()

    def test_empty_player_search_rejected(self):
        client, session = self.client({"data":[]})
        with self.assertRaises(ValueError):
            client.player_search(" ")
        session.get.assert_not_called()

if __name__ == "__main__":
    unittest.main()
