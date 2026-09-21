from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.catalog import EXPERIMENTS
from fvg_research.public_nsx import PUBLIC_RESULTS
from fvg_research.public_report import write_public_report
from fvg_research.public_summary import build_public_summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the public Nasdaq FVG replication report.")
    parser.add_argument("--output", default=str(ROOT / "site" / "public-nasdaq" / "index.html"))
    parser.add_argument("--summary", default=str(PUBLIC_RESULTS / "public_summary.json"))
    args = parser.parse_args(argv)

    summary_path = Path(args.summary)
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    else:
        summary = build_public_summary(PUBLIC_RESULTS)
    out = write_public_report(args.output, summary, EXPERIMENTS)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
