from __future__ import annotations

import unittest
from pathlib import Path

from scripts.run_original import patch_source


class ExternalRunnerPathTests(unittest.TestCase):
    def test_external_data_and_results_root_are_isolated(self):
        source = (
            "from pathlib import Path\n"
            "DATA = '/mnt/data/active_mnq.pkl'\n"
            "OUT = Path('/mnt/data/fvg_study_outputs')\n"
        )
        data = Path("C:/research/active_nsxusd.pkl")
        results = Path("C:/repo/results/external/nsxusd")
        patched = patch_source(source, "fixture.py", data, results)

        self.assertIn(str(data), patched)
        self.assertIn(str(results / "detailed_1m"), patched)
        self.assertNotIn("/mnt/data/active_mnq.pkl", patched)
        self.assertNotIn("/mnt/data/fvg_study_outputs", patched)


if __name__ == "__main__":
    unittest.main()
