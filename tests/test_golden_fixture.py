import hashlib
import json
import unittest
from pathlib import Path

import pandas as pd

from fvg_research.fvg import detect_fvgs
from fvg_research.io import normalize_ohlcv

ROOT = Path(__file__).resolve().parents[1]


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("utf-8")
    return hashlib.sha1(header + data).hexdigest()


class TestGoldenFixture(unittest.TestCase):
    def test_fixture_has_stable_bytes_and_expected_detector_output(self):
        fixture = ROOT / "tests" / "fixtures" / "golden_ohlcv.csv"
        manifest = json.loads((ROOT / "tests" / "fixtures" / "golden_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(git_blob_sha1(fixture), manifest["git_blob_sha1"])

        frame = normalize_ohlcv(pd.read_csv(fixture))
        self.assertEqual(len(frame), manifest["rows"])
        events = detect_fvgs(frame)
        self.assertEqual(len(events), manifest["expected_detected_fvgs"])
        self.assertEqual(events.index[0].isoformat(), manifest["first_fvg_timestamp_utc"])


if __name__ == "__main__":
    unittest.main()
