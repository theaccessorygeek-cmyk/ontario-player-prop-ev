
import unittest

from src.ev import (
    american_to_decimal,
    implied_probability,
    no_vig_probabilities,
    expected_value_per_dollar
)


class TestEVCalculations(unittest.TestCase):

    def test_negative_american_odds(self):
        self.assertAlmostEqual(
            american_to_decimal(-110),
            1.9090909,
            places=6
        )

    def test_positive_american_odds(self):
        self.assertAlmostEqual(
            american_to_decimal(150),
            2.5
        )

    def test_implied_probability(self):
        self.assertAlmostEqual(
            implied_probability(-110),
            0.5238095,
            places=6
        )

    def test_no_vig(self):
        over, under = no_vig_probabilities(-110, -110)

        self.assertAlmostEqual(over, 0.5)
        self.assertAlmostEqual(under, 0.5)

    def test_positive_expected_value(self):
        ev = expected_value_per_dollar(
            0.55,
            100
        )

        self.assertAlmostEqual(ev, 0.10)

    def test_push_probability(self):
        ev = expected_value_per_dollar(
            0.45,
            100,
            0.10
        )

        self.assertAlmostEqual(ev, 0.0)


if __name__ == "__main__":
    unittest.main()
  
