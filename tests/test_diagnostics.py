import unittest

from fvg_research.diagnostics import wilson_interval


class TestDiagnostics(unittest.TestCase):
    def test_wilson_interval_contains_rate(self):
        low, high = wilson_interval(0.7, 1000)
        self.assertLess(low, 0.7)
        self.assertGreater(high, 0.7)

    def test_more_data_narrows_interval(self):
        low1, high1 = wilson_interval(0.5, 100)
        low2, high2 = wilson_interval(0.5, 10_000)
        self.assertLess(high2 - low2, high1 - low1)


if __name__ == "__main__":
    unittest.main()
