from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "scripts" / "reproduce_full.py"

raise SystemExit(subprocess.call([sys.executable, str(SCRIPT)], cwd=ROOT))
