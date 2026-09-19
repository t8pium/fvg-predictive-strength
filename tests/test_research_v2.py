import unittest

import numpy as np
import pandas as pd

from research_v2.methods import (
    benjamini_hochberg,
    bounded_touch_outcome,
    full_horizon_mask,
    walk_forward_windows,
)


class TestResearchV2Methods(unittest.TestCase):
    def test_full_horizon_excludes_tail(self):
        index = pd.RangeIndex(6)
        mask = full_horizon_mask(index, 2)
        self.assertEqual(mask.tolist(), [True, True, True, True, False, False])

    def test_bounded_touch_censors_contract_roll(self):
        index = pd.date_range("2026-01-01", periods=6, freq="1min", tz="UTC")
        bars = pd.DataFrame(
            {
                "open": [10] * 6,
                "high": [11, 11, 11, 20, 20, 20],
                "low": [9, 9, 9, 8, 8, 8],
                "close": [10] * 6,
                "volume": [1] * 6,
                "symbol": ["MNQH26"] * 3 + ["MNQM26"] * 3,
            },
            index=index,
        )
        zones = pd.DataFrame(
            {"direction": [1], "near": [8.5]},
            index=pd.DatetimeIndex([index[1]]),
        )
        result = bounded_touch_outcome(bars, zones, 3)
        self.assertTrue(np.isnan(result.iloc[0]))

    def test_bh_is_monotone_in_rank(self):
        p = np.array([0.01, 0.04, 0.03, 0.2])
        q = benjamini_hochberg(p)
        self.assertTrue(np.all((q >= p) | np.isclose(q, p)))
        self.assertTrue(np.all(q <= 1))

    def test_walk_forward_is_chronological(self):
        index = pd.date_range("2026-01-01", periods=100, freq="1h", tz="UTC")
        windows = walk_forward_windows(index)
        self.assertGreater(len(windows), 1)
        for row in windows:
            self.assertLess(row["train_end"], row["test_start"])


if __name__ == "__main__":
    unittest.main()
