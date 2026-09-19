import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fvg_research.dataset as dataset


class TestDatasetPointer(unittest.TestCase):
    def test_activate_and_resolve_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            processed = root / "data" / "processed"
            generation = processed / "datasets" / "g1"
            generation.mkdir(parents=True)
            pickle = generation / "active_mnq.pkl"
            parquet = generation / "mnq_active_1m.parquet"
            manifest = generation / "active_mnq.manifest.json"
            pickle.write_bytes(b"pickle")
            parquet.write_bytes(b"parquet")
            manifest.write_text("{}", encoding="utf-8")
            pointer = processed / "current_dataset.json"
            with patch.multiple(
                dataset,
                ROOT=root,
                PROCESSED=processed,
                CURRENT_DATASET=pointer,
                GENERATIONS=processed / "datasets",
                ACTIVE_PICKLE=processed / "active_mnq.pkl",
                ACTIVE_1M=processed / "mnq_active_1m.parquet",
            ):
                payload = dataset.activate_generation(pickle, parquet, manifest)
                resolved = dataset.current_dataset()
            self.assertEqual(payload["generation"], "g1")
            self.assertEqual(Path(resolved["pickle"]), pickle)
            self.assertEqual(json.loads(pointer.read_text())["generation"], "g1")

    def test_legacy_pickle_is_backward_compatible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            processed = root / "data" / "processed"
            processed.mkdir(parents=True)
            legacy = processed / "active_mnq.pkl"
            legacy.write_bytes(b"old")
            with patch.multiple(
                dataset,
                ROOT=root,
                PROCESSED=processed,
                CURRENT_DATASET=processed / "current_dataset.json",
                ACTIVE_PICKLE=legacy,
                ACTIVE_1M=processed / "mnq_active_1m.parquet",
            ):
                resolved = dataset.current_dataset()
            self.assertEqual(resolved["generation"], "legacy")
            self.assertEqual(Path(resolved["pickle"]), legacy)


if __name__ == "__main__":
    unittest.main()
