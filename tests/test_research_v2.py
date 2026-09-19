import unittest

import numpy as np
import pandas as pd

from research_v2.ce_inference import ce_reinference
from research_v2.methods import (
    benjamini_hochberg,
    bounded_touch_outcome,
    cme_cluster,
    full_horizon_mask,
    parent_paired_age_decay,
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

    def test_parent_paired_decay_gives_each_parent_one_control_weight(self):
        index = pd.to_datetime(["2026-01-01T00:00Z", "2026-01-01T01:00Z"])
        real = pd.DataFrame(
            {"touch_1": [0, 0], "touch_3": [1, 0]},
            index=index,
        )
        controls = pd.DataFrame(
            {
                "event_ts": [index[0], index[0], index[0], index[1]],
                "touch_1": [0, 0, 0, 0],
                "touch_3": [1, 1, 0, 0],
            }
        )
        out = parent_paired_age_decay(
            real,
            controls,
            control_parent_col="event_ts",
            horizon_columns={1: "touch_1", 3: "touch_3"},
        )
        row = out.iloc[0]
        self.assertEqual(row["parents"], 2)
        self.assertAlmostEqual(row["real_rate"], 0.5)
        self.assertAlmostEqual(row["control_rate"], 1 / 3, places=6)
        self.assertAlmostEqual(row["difference_pp"], (0.5 - 1 / 3) * 100, places=6)

    def test_cme_cluster_rolls_at_1800_eastern(self):
        index = pd.DatetimeIndex([
            "2026-01-15 22:59:00+00:00",
            "2026-01-15 23:00:00+00:00",
        ])
        labels = cme_cluster(index)
        self.assertEqual([str(x) for x in labels], ["2026-01-15", "2026-01-16"])

    def test_ce_reinference_clusters_and_adjusts_multiple_cells(self):
        rows = []
        timestamps = pd.date_range("2026-01-05 23:00Z", periods=80, freq="12h")
        for i, ts in enumerate(timestamps):
            rows.append(
                {
                    "timeframe": "4H" if i % 2 == 0 else "1H",
                    "mode": "qualifying",
                    "trigger_ts": ts,
                    "depth": 0.46 if i % 4 < 2 else 0.56,
                    "outcome_code": 1 if i % 3 else -1,
                    "realized_R_conservative": 0.5 if i % 3 else -1.0,
                }
            )
        frame = pd.DataFrame(rows)
        out = ce_reinference(frame, band_width=0.05, min_n=5, n_boot=40, seed=7)
        self.assertGreaterEqual(len(out), 2)
        self.assertTrue({"trade_dates", "mean_R_ci_low", "mean_R_ci_high", "q_mean_R_bh"}.issubset(out.columns))
        self.assertTrue(out["q_mean_R_bh"].between(0, 1).all())


if __name__ == "__main__":
    unittest.main()
