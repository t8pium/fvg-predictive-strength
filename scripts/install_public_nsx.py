from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fvg_research.public_nsx import PUBLIC_ASSET_URL, install_public_release


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Install the free public NSX/USD research dataset from the GitHub release asset."
    )
    parser.add_argument("--url", default=PUBLIC_ASSET_URL)
    args = parser.parse_args(argv)
    try:
        manifest = install_public_release(url=args.url)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
