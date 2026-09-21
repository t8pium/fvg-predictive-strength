from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fvg_research.public_nsx import PUBLIC_RESULTS
from fvg_research.public_summary import write_public_summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a machine-readable summary of the public NSX/USD replication.")
    parser.add_argument("--results-root", default=str(PUBLIC_RESULTS))
    parser.add_argument(
        "--output",
        default=str(PUBLIC_RESULTS / "public_summary.json"),
    )
    args = parser.parse_args(argv)
    path = write_public_summary(args.output, args.results_root)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
