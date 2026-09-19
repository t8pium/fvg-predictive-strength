import unittest

from fvg_research.demo import run_demo, synthetic_ohlcv


class TestQuickDemo(unittest.TestCase):
    def test_synthetic_demo_is_deterministic_and_end_to_end(self):
        one = synthetic_ohlcv(n=3000, seed=123)
        two = synthetic_ohlcv(n=3000, seed=123)
        self.assertTrue(one.equals(two))

        result = run_demo(n=3000, seed=123, max_events=20, n_controls=2)
        self.assertEqual(len(result.horizons), 3)
        self.assertGreater(len(result.events), 0)
        self.assertGreater(len(result.controls), 0)
        self.assertTrue({"horizon_bars", "fvg_rate", "control_rate", "difference_pp"}.issubset(result.horizons.columns))
        self.assertTrue(result.horizons["fvg_rate"].between(0, 1).all())
        self.assertTrue(result.horizons["control_rate"].between(0, 1).all())


if __name__ == "__main__":
    unittest.main()
