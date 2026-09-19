from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.catalog import EXPERIMENTS
from app.provenance import EXPERIMENT_PROVENANCE
from fvg_research.dataset import current_pickle
from fvg_research.demo import run_demo
from fvg_research.report import write_report

OUT = ROOT / "results" / "_benchmarks" / "latest.json"


def timed_import_probe() -> float:
    started = time.perf_counter()
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import numpy,pandas,streamlit,plotly,databento,duckdb,fvg_research; print('ok')",
        ],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    return time.perf_counter() - started


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark common FVG Research Lab operations on this machine.")
    parser.add_argument("--include-dataset", action="store_true", help="Also time loading the current active pickle.")
    parser.add_argument("--demo-bars", type=int, default=8_000)
    args = parser.parse_args(argv)

    results: dict[str, object] = {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "demo_bars": args.demo_bars,
        "measurements": {},
    }
    measurements = results["measurements"]

    measurements["fresh_import_probe_seconds"] = round(timed_import_probe(), 4)

    tracemalloc.start()
    demo = run_demo(n=args.demo_bars, max_events=60, n_controls=2)
    _, demo_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    measurements["quick_demo_seconds"] = round(demo.elapsed_seconds, 4)
    measurements["quick_demo_python_peak_mb"] = round(demo_peak / 1024**2, 2)

    report_path = ROOT / "results" / "_benchmarks" / "benchmark_report.html"
    started = time.perf_counter()
    write_report(
        report_path,
        ROOT / "reference_results" / "reference_metrics.json",
        EXPERIMENTS,
        EXPERIMENT_PROVENANCE,
        ROOT,
    )
    measurements["static_report_generation_seconds"] = round(time.perf_counter() - started, 4)

    data = current_pickle()
    results["dataset_present"] = data.is_file()
    if args.include_dataset and data.is_file():
        import pandas as pd

        tracemalloc.start()
        started = time.perf_counter()
        frame = pd.read_pickle(data)
        elapsed = time.perf_counter() - started
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        measurements["active_dataset_load_seconds"] = round(elapsed, 4)
        measurements["active_dataset_python_peak_mb"] = round(peak / 1024**2, 2)
        measurements["active_dataset_rows"] = int(len(frame))
        del frame

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
