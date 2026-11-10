import unittest
from nexzen.cricket_data import (
    batting_average, strike_rate, bowling_economy, bowling_average,
    overs_from_balls, PlayerBattingAggregate, compare_batters, squad_balance
)

class CricketMetricTests(unittest.TestCase):
    def test_batting_average(self):
        self.assertEqual(batting_average(420, 12), 35.0)
        self.assertIsNone(batting_average(100, 0))
    def test_strike_rate(self):
        self.assertEqual(strike_rate(75, 50), 150.0)
        self.assertIsNone(strike_rate(0, 0))
    def test_bowling_economy_uses_legal_balls(self):
        self.assertEqual(bowling_economy(30, 24), 7.5)
        self.assertIsNone(bowling_economy(0, 0))
    def test_bowling_average(self):
        self.assertEqual(bowling_average(120, 6), 20.0)
        self.assertIsNone(bowling_average(20, 0))
    def test_overs_not_decimal_conversion(self):
        self.assertEqual(overs_from_balls(47), "7.5")
    def test_negative_inputs_rejected(self):
        with self.assertRaises(ValueError): strike_rate(-1, 2)
    def test_comparison_keeps_context_requirement(self):
        a = PlayerBattingAggregate("Player A", 300, 10, 8, 200)
        b = PlayerBattingAggregate("Player B", 280, 10, 10, 180)
        self.assertIn("comparison_context_required", compare_batters(a, b))
    def test_squad_role_counts_and_no_xi_claim(self):
        result = squad_balance([{"name":"A","role":"batter"},{"name":"B","role":"bowler"},{"name":"C","role":"wicketkeeper"}])
        self.assertEqual(result["role_counts"]["bowler"], 1)
        self.assertFalse(result["playing_xi_confirmed"])
    def test_duplicate_squad_member_rejected(self):
        with self.assertRaises(ValueError):
            squad_balance([{"name":"A","role":"batter"},{"name":"a","role":"bowler"}])

if __name__ == "__main__": unittest.main()
