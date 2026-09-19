from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_v2.hypotheses import register_hypothesis, verify_hypothesis

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "research_v2" / "hypotheses"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lock a Research v2 hypothesis definition before running it.")
    parser.add_argument("source_json", help="Draft hypothesis JSON file.")
    parser.add_argument("--output-dir", default=str(DEFAULT_DIR))
    args = parser.parse_args(argv)

    source = Path(args.source_json)
    payload = json.loads(source.read_text(encoding="utf-8"))
    hypothesis_id = str(payload.get("hypothesis_id", "")).strip()
    if not hypothesis_id:
        raise SystemExit("hypothesis_id is required.")
    target = Path(args.output_dir) / f"{hypothesis_id}.json"
    if target.exists():
        raise SystemExit(f"Refusing to overwrite existing preregistration: {target}")

    locked = register_hypothesis(target, payload)
    if not verify_hypothesis(locked):
        raise SystemExit("Internal preregistration hash verification failed.")
    print(json.dumps(locked, indent=2))
    print(f"Locked hypothesis: {target}")
    print("Commit this file before running or inspecting the corresponding result.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
