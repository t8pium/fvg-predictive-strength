from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from fvg_research.public_nsx import package_inventory, resample_ohlcv
from fvg_research.public_report import build_public_report


class PublicNsxTests(unittest.TestCase):
    def test_resample_preserves_ohlc_geometry(self):
        frame = pd.DataFrame(
            {
                "ts_event": pd.to_datetime(
                    [
                        "2024-07-01T13:30:00Z",
                        "2024-07-01T13:31:00Z",
                        "2024-07-01T13:32:00Z",
                        "2024-07-01T13:33:00Z",
                        "2024-07-01T13:34:00Z",
                    ],
                    utc=True,
                ),
                "open": [100, 101, 102, 101, 103],
                "high": [102, 103, 104, 104, 105],
                "low": [99, 100, 101, 100, 102],
                "close": [101, 102, 101, 103, 104],
                "volume": [0, 0, 0, 0, 0],
            }
        )
        out = resample_ohlcv(frame, 5)
        self.assertEqual(len(out), 1)
        self.assertEqual(float(out.iloc[0].open), 100)
        self.assertEqual(float(out.iloc[0].high), 105)
        self.assertEqual(float(out.iloc[0].low), 99)
        self.assertEqual(float(out.iloc[0].close), 104)

    def test_package_inventory_hashes_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("abc", encoding="utf-8")
            rows = package_inventory(root)
            self.assertEqual(rows[0]["name"], "a.txt")
            self.assertEqual(rows[0]["bytes"], 3)
            self.assertEqual(len(rows[0]["sha256"]), 64)

    def test_public_report_renders_without_results(self):
        experiments = {
            "raw_fill": {"num": "01", "title": "Raw Fill", "question": "Question?"}
        }
        html = build_public_report(
            {
                "dataset": {"rows": 5_046_180, "start_utc": "2010-11-14", "end_utc": "2026-09-11"},
                "experiments": {},
                "experiment_families_with_outputs": 0,
            },
            experiments,
        )
        self.assertIn("Public Nasdaq FVG Replication", html)
        self.assertIn("5,046,180", html)
        self.assertIn("Run locally to populate", html)


if __name__ == "__main__":
    unittest.main()
