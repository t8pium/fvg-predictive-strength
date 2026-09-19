import json
import unittest
from pathlib import Path

from scripts.render_reference_figures import render

ROOT = Path(__file__).resolve().parents[1]


class TestReferenceFigures(unittest.TestCase):
    def test_all_reference_figures_render_from_frozen_metrics(self):
        reference = json.loads((ROOT / "reference_results" / "reference_metrics.json").read_text(encoding="utf-8"))
        figures = render(reference)
        self.assertEqual(set(figures), {
            "01_fill_curve.svg",
            "02_matched_advantage.svg",
            "03_midpoint_reaction.svg",
            "04_oos_robustness.svg",
        })
        for name, svg in figures.items():
            with self.subTest(name=name):
                self.assertTrue(svg.startswith("<svg"))
                self.assertIn("</svg>", svg)
                self.assertNotIn("nan", svg.lower())
                self.assertGreater(len(svg), 500)


if __name__ == "__main__":
    unittest.main()
