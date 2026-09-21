from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from fvg_research.histdata_nsx import prepare_histdata_nsx


class HistDataNsxTests(unittest.TestCase):
    def _write(self, root: Path, rows: list[str]) -> Path:
        path = root / "NSXUSD_M1_ALL.csv"
        path.write_text(
            "timestamp_est_fixed,open,high,low,close,volume\n" + "\n".join(rows) + "\n",
            encoding="utf-8",
        )
        return path

    def test_prepares_schema_compatible_external_dataset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self._write(
                root,
                [
                    "2024-07-01 08:30:00,20000,20002,19999,20001,0",
                    "2024-07-01 08:31:00,20001,20003,20000,20002,0",
                    "2024-07-01 08:32:00,20002,20004,20001,20003,0",
                ],
            )
            out = root / "out"
            result = prepare_histdata_nsx(source, out, chunksize=2)

            frame = pd.read_pickle(result["pickle_path"])
            self.assertEqual(
                list(frame.columns),
                [
                    "ts_event",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "symbol",
                    "trade_date",
                    "active_symbol",
                    "roll_date",
                ],
            )
            self.assertEqual(str(frame.ts_event.dtype), "datetime64[ns, UTC]")
            # Source is fixed EST (UTC-05), so 08:30 becomes 13:30 UTC.
            self.assertEqual(frame.ts_event.iloc[0].isoformat(), "2024-07-01T13:30:00+00:00")
            # In July, that instant is 09:30 America/New_York (EDT).
            self.assertEqual(
                frame.ts_event.dt.tz_convert("America/New_York").iloc[0].strftime("%H:%M"),
                "09:30",
            )
            self.assertTrue((frame.symbol.astype(str) == "NSXUSD").all())
            self.assertTrue((frame.volume == 0).all())
            self.assertFalse(frame.roll_date.any())

            audit = json.loads((out / "audit.json").read_text(encoding="utf-8"))
            self.assertEqual(audit["rows"], 3)
            self.assertEqual(audit["invalid_ohlc_geometry_rows"], 0)
            self.assertEqual(audit["duplicate_adjacent_timestamps"], 0)
            self.assertFalse(audit["volume_usable"])

    def test_invalid_ohlc_is_blocked_but_audit_is_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self._write(
                root,
                ["2024-01-02 09:30:00,100,99,98,100,0"],
            )
            out = root / "out"
            with self.assertRaisesRegex(ValueError, "audit failed"):
                prepare_histdata_nsx(source, out)

            audit = json.loads((out / "audit.json").read_text(encoding="utf-8"))
            self.assertEqual(audit["invalid_ohlc_geometry_rows"], 1)
            self.assertFalse((out / "active_nsxusd.pkl").exists())


if __name__ == "__main__":
    unittest.main()
