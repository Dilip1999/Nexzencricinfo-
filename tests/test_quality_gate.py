import unittest
from nexzen.quality_gate import validate_analysis_report

def report():
 return {"source_url":"https://cricketdatabase.com/matches/example","innings":[
  {"runs":10,"extras":2,"wickets":1,"overs":"2","batting_card":[{"runs":8,"out":True},{"runs":0,"out":False}],"bowling_card":[
   {"player_id":"a","overs":"1","runs_conceded":4,"wickets":1,"economy":4.0},
   {"player_id":"b","overs":"1","runs_conceded":6,"wickets":0,"economy":6.0}],
   "bowling_figures":[{"player_id":"a"},{"player_id":"b"}]}]}

class QualityGateTests(unittest.TestCase):
 def test_consistent_scorecard_is_validated(self):
  self.assertEqual(validate_analysis_report(report())["status"],"validated")
 def test_missing_extras_reconciliation_requires_review(self):
  data=report(); data["innings"][0]["runs"]=12
  result=validate_analysis_report(data)
  self.assertEqual(result["status"],"needs_human_review")
  self.assertFalse(result["publish_eligible"])
 def test_batting_runs_over_total_blocks(self):
  data=report(); data["innings"][0]["runs"]=5
  self.assertEqual(validate_analysis_report(data)["status"],"blocked")
 def test_bowling_summary_mismatch_warns(self):
  data=report(); data["innings"][0]["bowling_figures"]=[{"player_id":"b"}]
  self.assertIn("bowling leaders summary", " ".join(validate_analysis_report(data)["warnings"]))
 def test_t10_format_conflict_warns(self):
  data=report(); data["match_listing_context"]={"format":"one-day","competition":"Abu Dhabi T10"}
  self.assertIn("format conflicts", " ".join(validate_analysis_report(data)["warnings"]))

if __name__ == "__main__": unittest.main()
