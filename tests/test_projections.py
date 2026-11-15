
import unittest

from src.projections import estimate_probabilities


class TestPlayerPropProjections(unittest.TestCase):

    def setUp(self):
        self.observations = [
            20, 22, 18, 25, 21,
            19, 24, 23, 20, 22,
            18, 21, 25, 19, 23,
            22, 20, 24, 21, 26,
        ]

    def test_probabilities_sum_to_one(self):
        result = estimate_probabilities(
            self.observations, 21.5
        )

        total = (
            result["model_over_probability"]
            + result["model_under_probability"]
            + result["model_push_probability"]
        )

        self.assertAlmostEqual(total, 1.0)

    def test_push_probability(self):
        result = estimate_probabilities(
            [10] * 20, 10
        )

        self.assertAlmostEqual(
            result["model_push_probability"], 1.0
        )

        self.assertAlmostEqual(
            result["model_over_probability"], 0.0
        )

    def test_insufficient_observations_rejected(self):
        with self.assertRaises(ValueError):
            estimate_probabilities([10, 11, 12], 10.5)

    def test_invalid_observation_rejected(self):
        values = self.observations.copy()
        values[0] = float("nan")

        with self.assertRaises(ValueError):
            estimate_probabilities(values, 21.5)

    def test_effective_sample_size(self):
        result = estimate_probabilities(
            self.observations, 21.5
        )

        self.assertGreater(result["effective_sample_size"], 0)
        self.assertLessEqual(
            result["effective_sample_size"], 20
        )

    def test_counts_all_observations(self):
        result = estimate_probabilities(
            self.observations, 21.5
        )

        self.assertEqual(result["observations"], 20)
        self.assertEqual(
            result["raw_over"]
            + result["raw_under"]
            + result["raw_push"],
            20,
        )


if __name__ == "__main__":
    unittest.main()
  
