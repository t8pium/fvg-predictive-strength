from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.catalog import EXPERIMENTS
from app.provenance import EXPERIMENT_PROVENANCE
from fvg_research.report import write_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the self-contained static FVG research report.")
    parser.add_argument("--output", default=str(ROOT / "site" / "index.html"))
    args = parser.parse_args(argv)
    output = write_report(
        args.output,
        ROOT / "reference_results" / "reference_metrics.json",
        EXPERIMENTS,
        EXPERIMENT_PROVENANCE,
        ROOT,
    )
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
