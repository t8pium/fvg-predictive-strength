from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fvg_research.active_contract import build_active_contract
from fvg_research.config import RAW
from fvg_research.dataset import activate_generation, cleanup_old_generations, new_generation_dir


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and activate the volume-selected active MNQ one-minute series.")
    parser.add_argument(
        "--input",
        action="append",
        dest="inputs",
        help=(
            "Input file or directory; repeat for multiple inputs. Supported: "
            ".dbn, .dbn.zst, .parquet, .pq, .csv, .csv.gz, .csv.zst, .zip."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    inputs = [Path(value) for value in args.inputs] if args.inputs else [RAW]
    print("Reading input(s):", flush=True)
    for path in inputs:
        print(" -", path, flush=True)

    generation = new_generation_dir()
    parquet = generation / "mnq_active_1m.parquet"
    pickle = generation / "active_mnq.pkl"
    manifest = generation / "active_mnq.manifest.json"
    try:
        summary = build_active_contract(inputs, parquet, pickle, manifest)
        pointer = activate_generation(pickle, parquet, manifest)
        cleanup_old_generations(keep=2)
    except Exception as exc:
        try:
            shutil.rmtree(generation)
        except OSError:
            pass
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    summary["generation"] = pointer["generation"]
    print(json.dumps(summary, indent=2))
    print(f"Activated {pickle}")
    print(f"Parquet {parquet}")
    print("The Research Lab now points to this generation; existing dataset files were not overwritten in place.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
