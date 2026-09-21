from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fvg_research.dashboard_helpers import load_latest_success
from fvg_research.public_nsx import PUBLIC_PICKLE, PUBLIC_RESULTS, ensure_pickle, public_ready

TFS = (1, 5, 15, 60, 240)


def stages() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = [
        {"key": "detailed-1m", "label": "Detailed 1m", "study": "detailed-1m"},
    ]
    rows += [
        {"key": f"multi-tf_tf{tf}", "label": f"Multi-timeframe {tf}m", "study": "multi-tf", "tf": tf}
        for tf in TFS
    ]
    rows += [
        {"key": f"midpoint_tf{tf}", "label": f"Midpoint {tf}m", "study": "midpoint", "tf": tf}
        for tf in TFS
    ]
    rows += [
        {
            "key": "ce-body",
            "label": "CE body / execution",
            "study": "ce-body",
            "ce_tfs": "1,2,3,5,10,15,30,60,120,240,360,480,720,1440",
        }
    ]
    return rows


def _fresh(stage: dict[str, object], data: Path, results_root: Path) -> bool:
    key = str(stage["key"])
    return load_latest_success(results_root, data, key) is not None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the full nine-experiment FVG replication on the free public NSX/USD history."
    )
    parser.add_argument("--data", default=str(PUBLIC_PICKLE))
    parser.add_argument("--results-root", default=str(PUBLIC_RESULTS))
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--skip-ce", action="store_true", help="Skip the heaviest CE/body stage.")
    args = parser.parse_args(argv)

    if Path(args.data) == PUBLIC_PICKLE and not PUBLIC_PICKLE.is_file():
        if not public_ready() and not PUBLIC_PICKLE.is_file():
            try:
                ensure_pickle()
            except Exception as exc:
                print(f"ERROR: public dataset is not installed/prepared: {exc}", file=sys.stderr)
                return 2

    data = Path(args.data).expanduser().resolve()
    results_root = Path(args.results_root).expanduser().resolve()
    results_root.mkdir(parents=True, exist_ok=True)
    state_dir = results_root / "_full_reproduction"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / "state.json"

    state = {
        "status": "running",
        "dataset": str(data),
        "results_root": str(results_root),
        "stages": [],
    }
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    failed = False
    for stage in stages():
        if args.skip_ce and stage["study"] == "ce-body":
            state["stages"].append({**stage, "status": "skipped", "seconds": 0.0, "exit_code": 0})
            continue
        if not args.force and _fresh(stage, data, results_root):
            print("SKIP", stage["label"], "(fresh cached result)", flush=True)
            state["stages"].append({**stage, "status": "cached", "seconds": 0.0, "exit_code": 0})
            state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
            continue

        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "run_original.py"),
            str(stage["study"]),
            "--data",
            str(data),
            "--results-root",
            str(results_root),
        ]
        if "tf" in stage:
            cmd += ["--tf", str(stage["tf"])]
        if "ce_tfs" in stage:
            cmd += ["--ce-tfs", str(stage["ce_tfs"])]

        print("\nRUN", stage["label"], flush=True)
        started = time.perf_counter()
        proc = subprocess.run(cmd, cwd=ROOT)
        elapsed = time.perf_counter() - started
        status = "success" if proc.returncode == 0 else "failed"
        state["stages"].append(
            {**stage, "status": status, "seconds": round(elapsed, 3), "exit_code": proc.returncode}
        )
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        if proc.returncode:
            failed = True
            break

    if not failed:
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "summarize_public_nsx.py"),
                "--results-root",
                str(results_root),
                "--output",
                str(results_root / "public_summary.json"),
            ],
            cwd=ROOT,
            check=True,
        )

    state["status"] = "failed" if failed else "success"
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print("\nSTATE", state_path, flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
