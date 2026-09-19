import unittest

from fvg_research.demo import run_demo


class TestQuickDemo(unittest.TestCase):
    def test_demo_runs_end_to_end_and_is_deterministic(self):
        first = run_demo(n=4000, max_events=30, n_controls=2)
        second = run_demo(n=4000, max_events=30, n_controls=2)
        self.assertGreater(len(first.events), 10)
        self.assertGreater(len(first.controls), 0)
        self.assertEqual(list(first.horizons["horizon_bars"]), [5, 15, 60])
        self.assertEqual(
            first.horizons.round(10).to_dict(orient="records"),
            second.horizons.round(10).to_dict(orient="records"),
        )


if __name__ == "__main__":
    unittest.main()
