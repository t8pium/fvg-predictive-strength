import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import bootstrap


class TestBootstrapFastPath(unittest.TestCase):
    def test_healthy_environment_skips_all_install_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            fake_python = Path(directory) / "python.exe"
            fake_python.write_bytes(b"stub")

            calls = []
            with patch.object(bootstrap, "venv_python", return_value=fake_python), \
                 patch.object(bootstrap, "installed_environment_is_healthy", return_value=True), \
                 patch.object(bootstrap, "run", side_effect=lambda cmd, **kwargs: calls.append(cmd)):
                bootstrap.main()

        self.assertEqual(len(calls), 1)
        command = [str(value) for value in calls[0]]
        self.assertIn("streamlit", command)
        self.assertNotIn("pip", command)
        self.assertNotIn("install", command)


if __name__ == "__main__":
    unittest.main()
