import unittest
from src.nhl_sog_market_ev import weighted_outcome_probabilities, decimal_odds_metrics, evaluate_markets

class TestMarketEV(unittest.TestCase):
    def test_probabilities_sum_to_one(self):
        p=weighted_outcome_probabilities([1,2,3,4],2.5)
        self.assertAlmostEqual(sum(p.values()),1)
    def test_integer_line_push(self):
        p=weighted_outcome_probabilities([2,3,4],3)
        self.assertGreater(p["push_probability"],0)
    def test_ev_with_push(self):
        implied,ev=decimal_odds_metrics(.4,.2,2)
        self.assertAlmostEqual(implied,.5); self.assertAlmostEqual(ev,0)
    def test_excludes_target_and_future_games(self):
        games=[{"player":"A","game_date":"2025-01-01","shots_on_goal":"2"},{"player":"A","game_date":"2025-01-02","shots_on_goal":"4"},{"player":"A","game_date":"2025-01-03","shots_on_goal":"5"}]
        markets=[{"player":"A","game_date":"2025-01-03","line":"3.5","over_decimal_odds":"2","under_decimal_odds":"2"}]
        r=evaluate_markets(games,markets)[0]
        self.assertEqual(r["history_games"],2); self.assertEqual(r["over_probability"],0)
    def test_invalid_odds(self):
        with self.assertRaises(ValueError): decimal_odds_metrics(.5,0,1)
if __name__=="__main__": unittest.main()
