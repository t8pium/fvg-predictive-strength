import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from fvg_research.demo import synthetic_ohlcv
from fvg_research.economics import economic_summary
from fvg_research.event_explorer import event_catalog, event_window, summarize_event
from fvg_research.preflight import inspect_source
from fvg_research.run_record import write_run_record
from fvg_research.stability import reference_atlas
from research_v2.ablation import run_ablation
from research_v2.hypotheses import register_hypothesis, verify_hypothesis
from research_v2.placebos import placebo_suite
from research_v2.power import mde_two_proportion

ROOT = Path(__file__).resolve().parents[1]


class TestV4ResearchPlatform(unittest.TestCase):
    def test_power_mde_shrinks_with_sample_size(self):
        small = mde_two_proportion(1000, 1000, baseline=0.9, design_effect=1.5)
        large = mde_two_proportion(10000, 10000, baseline=0.9, design_effect=1.5)
        self.assertGreater(small, large)

    def test_hypothesis_registry_hash_detects_edits(self):
        payload = {
            "hypothesis_id": "TEST-001",
            "title": "Test",
            "question": "Does x differ?",
            "dataset_window": "2026",
            "primary_outcome": "difference",
            "timeframe": "1m",
            "filters": [],
            "horizon": "60",
            "expected_direction": "two-sided",
            "statistic": "cluster bootstrap",
            "correction_family": "primary",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "h.json"
            locked = register_hypothesis(path, payload)
            self.assertTrue(verify_hypothesis(locked))
            locked["horizon"] = "120"
            self.assertFalse(verify_hypothesis(locked))

    def test_preflight_reads_golden_csv_without_mutation(self):
        fixture = ROOT / "tests" / "fixtures" / "golden_ohlcv.csv"
        result = inspect_source(fixture)
        self.assertEqual(result["status"], "PASS")
        self.assertIn("open", [column.lower() for column in result["columns"]])

    def test_event_explorer_reads_golden_event(self):
        frame = pd.read_csv(ROOT / "tests" / "fixtures" / "golden_ohlcv.csv")
        frame["ts_event"] = pd.to_datetime(frame["ts_event"], utc=True)
        frame = frame.set_index("ts_event")
        catalog = event_catalog(frame)
        self.assertGreater(len(catalog), 0)
        timestamp = catalog.index[0]
        summary = summarize_event(frame, timestamp, horizon=5)
        window = event_window(frame, timestamp, before=3, after=5)
        self.assertEqual(summary["timestamp"], timestamp.isoformat())
        self.assertGreaterEqual(len(window), 6)

    def test_economic_costs_reduce_expectancy(self):
        trades = pd.DataFrame({
            "risk_pts": [5.0, 5.0, 10.0],
            "realized_R_conservative": [1.0, -1.0, 0.5],
        })
        grossish = economic_summary(trades, commission_round_turn_usd=0, slippage_ticks_round_turn=0)
        costly = economic_summary(trades, commission_round_turn_usd=2, slippage_ticks_round_turn=4)
        self.assertGreater(grossish["net_mean_R"], costly["net_mean_R"])

    def test_placebo_and_ablation_smoke_on_synthetic_data(self):
        bars = synthetic_ohlcv(n=3000, seed=77)
        placebo = placebo_suite(bars, horizon=15, max_events=40, seed=77)
        self.assertGreaterEqual(len(placebo), 3)
        self.assertIn("Real FVG", placebo["series"].tolist())

        ablation = run_ablation(bars, horizon=15, max_events=40, n_controls=1, seed=77)
        self.assertGreaterEqual(len(ablation), 2)
        self.assertTrue({"Variant", "Difference (pp)"}.issubset(ablation.columns))

    def test_run_record_contains_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
            inp = root / "input.txt"
            out = root / "output.txt"
            inp.write_text("input", encoding="utf-8")
            out.write_text("output", encoding="utf-8")
            record = write_run_record(
                root,
                kind="unit-test",
                command=["python", "x.py"],
                status="success",
                started_unix=1.0,
                finished_unix=2.0,
                inputs=[inp],
                outputs=[out],
            )
            payload = json.loads(record.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "success")
            self.assertEqual(len(payload["inputs"][0]["sha256"]), 64)
            self.assertEqual(len(payload["outputs"][0]["sha256"]), 64)

    def test_reference_stability_atlas_has_core_dimensions(self):
        reference = json.loads((ROOT / "reference_results" / "reference_metrics.json").read_text(encoding="utf-8"))
        atlas = reference_atlas(reference)
        self.assertEqual(set(atlas), {"timeframe", "chronology", "distance"})
        self.assertGreater(len(atlas["timeframe"]), 0)


if __name__ == "__main__":
    unittest.main()
