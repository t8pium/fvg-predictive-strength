import json
import tempfile
from html import escape
import unittest
from pathlib import Path

from app.catalog import EXPERIMENTS
from app.provenance import EXPERIMENT_PROVENANCE
from fvg_research.report import build_report, write_report

ROOT = Path(__file__).resolve().parents[1]


class TestStaticReport(unittest.TestCase):
    def test_report_contains_all_experiments_and_audit_material(self):
        reference = json.loads((ROOT / "reference_results" / "reference_metrics.json").read_text(encoding="utf-8"))
        html = build_report(reference, EXPERIMENTS, EXPERIMENT_PROVENANCE, ROOT)

        self.assertIn("<!doctype html>", html.lower())
        self.assertIn("Published conclusion", html)
        self.assertIn("Research architecture", html)
        self.assertIn("When are FVGs most predictive?", html)
        self.assertIn("+1.05 pp", html)
        self.assertIn("+1.93 pp", html)
        self.assertIn("Provenance", html)
        self.assertNotIn("/mnt" + "/data", html)

        for exp_id, exp in EXPERIMENTS.items():
            with self.subTest(exp_id=exp_id):
                self.assertIn(f'id="exp-{exp_id}"', html)
                self.assertIn(escape(exp["title"]), html)

    def test_report_can_be_written_as_one_self_contained_html_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.html"
            result = write_report(
                output,
                ROOT / "reference_results" / "reference_metrics.json",
                EXPERIMENTS,
                EXPERIMENT_PROVENANCE,
                ROOT,
            )
            self.assertEqual(result, output)
            self.assertGreater(output.stat().st_size, 10_000)
            text = output.read_text(encoding="utf-8")
            self.assertIn("<svg", text)
            self.assertNotIn('<script src=', text)


if __name__ == "__main__":
    unittest.main()
