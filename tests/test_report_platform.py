import json
import unittest
from html import escape
from pathlib import Path

from app.catalog import EXPERIMENTS
from app.provenance import EXPERIMENT_PROVENANCE
from fvg_research.explainers import experiment_svg, research_flow_svg
from fvg_research.report import build_report

ROOT = Path(__file__).resolve().parents[1]


class TestResearchReport(unittest.TestCase):
    def test_every_experiment_has_a_visual_explainer(self):
        for exp_id in EXPERIMENTS:
            with self.subTest(experiment=exp_id):
                svg = experiment_svg(exp_id)
                self.assertTrue(svg.startswith("<svg"))
                self.assertIn("</svg>", svg)
                self.assertGreater(len(svg), 500)
        self.assertIn("</svg>", research_flow_svg())

    def test_static_report_contains_all_experiments_and_provenance(self):
        reference = json.loads(
            (ROOT / "reference_results" / "reference_metrics.json").read_text(encoding="utf-8")
        )
        html = build_report(reference, EXPERIMENTS, EXPERIMENT_PROVENANCE, ROOT)
        self.assertIn("<!doctype html>", html.lower())
        self.assertIn("FVG Predictive Strength", html)
        for exp_id, meta in EXPERIMENTS.items():
            self.assertIn(f'id="exp-{exp_id}"', html)
            self.assertIn(escape(meta["title"]), html)
        self.assertIn("Canonical suite", html)
        self.assertNotIn("DATABENTO_API_KEY", html)


if __name__ == "__main__":
    unittest.main()
