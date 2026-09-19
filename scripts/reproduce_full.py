from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.catalog import EXPERIMENTS
from app.provenance import EXPERIMENT_PROVENANCE
from app.verification import verification_rows
from fvg_research.dashboard_helpers import load_latest_success
from fvg_research.dataset import current_pickle
from fvg_research.report import write_report
from fvg_research.run_record import write_run_record

RESULTS = ROOT / "results"
RUNNER = ROOT / "scripts" / "run_original.py"
STATE_DIR = RESULTS / "_full_reproduction"
STATE_FILE = STATE_DIR / "state.json"
VERIFY_FILE = STATE_DIR / "verification.json"
REPORT_FILE = STATE_DIR / "research_report.html"
REFERENCE_PATH = ROOT / "reference_results" / "reference_metrics.json"
CE_TFS = [1, 2, 3, 5, 10, 15, 30, 60, 120, 240, 360, 480, 720, 1440]


@dataclass(frozen=True)
class Stage:
    key: str
    label: str
    study: str
    args: tuple[str, ...]
    cache_key: str


STAGES = [
    Stage("detailed", "Detailed 1m falsification suite", "detailed-1m", ("detailed-1m",), "detailed-1m"),
    *[
        Stage(
            f"multi_{tf}",
            f"Multi-timeframe suite · {tf}m",
            "multi-tf",
            ("multi-tf", "--tf", str(tf)),
            f"multi-tf_tf{tf}",
        )
        for tf in (1, 5, 15, 60, 240)
    ],
    *[
        Stage(
            f"midpoint_{tf}",
            f"Midpoint / CE suite · {tf}m",
            "midpoint",
            ("midpoint", "--tf", str(tf)),
            f"midpoint_tf{tf}",
        )
        for tf in (1, 5, 15, 60, 240)
    ],
    Stage(
        "ce_body",
        "Candle-body / CE execution suite",
        "ce-body",
        ("ce-body", "--ce-tfs", ",".join(map(str, CE_TFS))),
        "ce-body",
    ),
]


def _cached(stage: Stage, data: Path) -> dict | None:
    payload = load_latest_success(RESULTS, data, stage.cache_key)
    if not payload:
        return None
    if stage.study == "ce-body":
        if set(payload.get("ce_tfs") or []) != set(CE_TFS):
            return None
    return payload


def _write_state(payload: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _run_stage(stage: Stage) -> int:
    command = [sys.executable, str(RUNNER), *stage.args]
    print(f"\n=== {stage.label} ===", flush=True)
    print(">", " ".join(command), flush=True)
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="", flush=True)
    return process.wait()


def _verification() -> list[dict]:
    reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    rows = []
    for exp_id in (
        "raw_fill", "matched_attraction", "age_decay", "continuation", "retest",
        "midpoint", "body_acceptance", "controls_regimes", "oos",
    ):
        for row in verification_rows(exp_id, reference):
            rows.append({"experiment": exp_id, **row})
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the complete published study with resume/cache support."
    )
    parser.add_argument("--force", action="store_true", help="Rerun even if a fresh successful stage exists.")
    parser.add_argument("--plan", action="store_true", help="Print the stage plan and exit.")
    parser.add_argument("--from-stage", help="Start at a specific stage key; earlier uncached stages are skipped deliberately.")
    args = parser.parse_args(argv)

    data = current_pickle()
    if not data.is_file():
        print("ERROR: No active dataset is prepared. Build the dataset first.", file=sys.stderr)
        return 2

    if args.plan:
        for number, stage in enumerate(STAGES, 1):
            status = "cached" if _cached(stage, data) else "needs run"
            print(f"{number:02d}. {stage.key:16s} {status:10s} {stage.label}")
        return 0

    start_index = 0
    if args.from_stage:
        keys = [stage.key for stage in STAGES]
        if args.from_stage not in keys:
            print(f"ERROR: Unknown stage {args.from_stage!r}. Choose one of {keys}", file=sys.stderr)
            return 2
        start_index = keys.index(args.from_stage)

    state = {
        "version": 1,
        "data_path": str(data),
        "data_mtime_ns": data.stat().st_mtime_ns,
        "started_unix": time.time(),
        "status": "running",
        "stages": [],
    }
    _write_state(state)

    for index, stage in enumerate(STAGES):
        state["current_stage"] = stage.key
        state["current_stage_number"] = index + 1
        state["total_stages"] = len(STAGES)
        _write_state(state)
        print(f"\n[{index + 1}/{len(STAGES)}] {stage.label}", flush=True)

        if index < start_index:
            state["stages"].append(
                {"key": stage.key, "label": stage.label, "status": "skipped_by_request", "seconds": 0.0}
            )
            _write_state(state)
            continue

        cached = None if args.force else _cached(stage, data)
        if cached:
            print(f"\n=== {stage.label} ===\nCACHED · fresh successful run already matches the active dataset.", flush=True)
            state["stages"].append(
                {
                    "key": stage.key,
                    "label": stage.label,
                    "status": "cached",
                    "seconds": 0.0,
                    "manifest": cached,
                }
            )
            _write_state(state)
            continue

        started = time.perf_counter()
        rc = _run_stage(stage)
        elapsed = time.perf_counter() - started
        row = {
            "key": stage.key,
            "label": stage.label,
            "status": "success" if rc == 0 else "failed",
            "seconds": round(elapsed, 3),
            "exit_code": rc,
        }
        state["stages"].append(row)
        _write_state(state)
        if rc != 0:
            state["status"] = "failed"
            state["failed_stage"] = stage.key
            state["finished_unix"] = time.time()
            _write_state(state)
            print(f"\nFAILED at {stage.label}. Re-run this command to resume from cached completed stages.", file=sys.stderr)
            return rc

    verification = _verification()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    VERIFY_FILE.write_text(json.dumps(verification, indent=2), encoding="utf-8")
    write_report(
        REPORT_FILE,
        REFERENCE_PATH,
        EXPERIMENTS,
        EXPERIMENT_PROVENANCE,
        ROOT,
    )
    state["status"] = "success"
    state["current_stage"] = None
    state["finished_unix"] = time.time()
    state["verification_rows"] = len(verification)
    state["report"] = str(REPORT_FILE.relative_to(ROOT))
    record = write_run_record(
        ROOT,
        kind="full-reproduction",
        command=[sys.executable, str(ROOT / "scripts" / "reproduce_full.py"), *sys.argv[1:]],
        status="success",
        started_unix=float(state["started_unix"]),
        finished_unix=float(state["finished_unix"]),
        inputs=[data, REFERENCE_PATH],
        outputs=[STATE_FILE, VERIFY_FILE, REPORT_FILE],
        extra={
            "stages": state["stages"],
            "verification_rows": len(verification),
            "cached_stage_count": sum(1 for row in state["stages"] if row.get("status") == "cached"),
        },
    )
    state["run_record"] = str(record.relative_to(ROOT))
    _write_state(state)

    print("\n=== Full reproduction complete ===")
    print(f"State: {STATE_FILE}")
    print(f"Published-vs-local verification: {VERIFY_FILE}")
    print(f"Self-contained research report: {REPORT_FILE}")
    print(f"Run provenance capsule: {record}")
    print("Completed stages are cached by active-dataset timestamp. Re-running will skip them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
