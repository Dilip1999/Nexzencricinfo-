import unittest
from nexzen.scorecard_analysis import analyze_scorecard, overs_to_balls

FIXTURE = {"data":{"match":"2026-09-17-sri-lanka-v-england","result":"England won by 6 wickets","innings":[
 {"innings":1,"team":"sri-lanka","name":"Sri Lanka","runs":145,"wickets":9,"overs":"20","run_rate":7.25,
  "batting":[{"player":"p-n","name":"P Nissanka","runs":37,"balls":21,"fours":4,"sixes":1,"out":True,"dismissal":"caught"}],
  "bowling":[{"player":"j-b","name":"J Bowler","overs":"4","runs":25,"wickets":2}]},
 {"innings":2,"team":"england","name":"England","runs":146,"wickets":4,"overs":"12.1","run_rate":12,
  "batting":[{"player":"j-b","name":"J Batter","runs":55,"balls":25,"fours":5,"sixes":3,"out":False}],
  "bowling":[{"player":"p-n","name":"P Bowler","overs":"3.4","runs":30,"wickets":1}]}
]}}
class ScorecardAnalysisTests(unittest.TestCase):
 def test_overs_not_decimal(self):
  self.assertEqual(overs_to_balls("3.4"),22)
  self.assertEqual(overs_to_balls("12.1"),73)
 def test_invalid_overs_rejected(self):
  with self.assertRaises(ValueError): overs_to_balls("3.7")
 def test_derived_rates_and_provenance(self):
  result=analyze_scorecard(FIXTURE,source_url="https://cricketdatabase.com/matches/example")
  self.assertEqual(result["innings"][0]["top_scorers"][0]["strike_rate"],176.19)
  self.assertEqual(result["innings"][0]["bowling_figures"][0]["player_id"],"j-b")
  self.assertEqual(result["innings"][1]["bowling_figures"][0]["economy"],8.18)
  self.assertEqual(result["editorial_status"],"data_ready_for_human_review")
  self.assertIn("source_url",result)
 def test_malformed_scorecard_fails_closed(self):
  with self.assertRaises(ValueError): analyze_scorecard({"data":{"innings":[]}},source_url="https://example.com")
if __name__ == "__main__": unittest.main()
