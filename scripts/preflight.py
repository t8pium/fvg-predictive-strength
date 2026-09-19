from __future__ import annotations

import argparse
import json

from fvg_research.preflight import inspect_sources


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect market-data inputs without building the active-contract dataset.")
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args(argv)
    results = inspect_sources(args.paths)
    print(json.dumps(results, indent=2))
    return 1 if any(item.get("status") == "FAIL" for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
