from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fvg_research.histdata_nsx import prepare_histdata_nsx


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit HistData NSX/USD 1-minute CSV data and build a schema-compatible "
            "external dataset for FVG discovery/robustness experiments."
        )
    )
    parser.add_argument("--input", required=True, help="Path to NSXUSD_M1_ALL.csv")
    parser.add_argument(
        "--output",
        default=str(ROOT / "data" / "external" / "nsxusd"),
        help="Output directory (default: data/external/nsxusd)",
    )
    parser.add_argument("--chunksize", type=int, default=500_000)
    args = parser.parse_args(argv)

    try:
        result = prepare_histdata_nsx(args.input, args.output, chunksize=args.chunksize)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2))
    print()
    print("Prepared external NSX/USD dataset.")
    print("Important: this is a Nasdaq-100 index-style quote feed, not CME NQ/MNQ futures.")
    print("Use results/external/... so published MNQ outputs remain untouched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
