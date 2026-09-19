import unittest

from scripts.reproduce_full import STAGES


class TestFullReproductionPlan(unittest.TestCase):
    def test_plan_has_all_canonical_suites_once_per_required_scope(self):
        keys = [stage.key for stage in STAGES]
        self.assertEqual(len(keys), 12)
        self.assertEqual(len(keys), len(set(keys)))
        self.assertIn("detailed", keys)
        self.assertIn("ce_body", keys)
        self.assertEqual(sum(key.startswith("multi_") for key in keys), 5)
        self.assertEqual(sum(key.startswith("midpoint_") for key in keys), 5)


if __name__ == "__main__":
    unittest.main()
