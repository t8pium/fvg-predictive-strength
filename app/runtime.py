from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections.abc import Iterable
from pathlib import Path

from fvg_research.dashboard_helpers import discover_results, load_latest_success, safe_upload_name
from fvg_research.dataset import current_dataset, current_manifest, current_pickle, dataset_ready

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
UPLOADS = ROOT / "data" / "uploads"
LOGS = RESULTS / "_logs"
UPLOADS.mkdir(parents=True, exist_ok=True)
LOGS.mkdir(parents=True, exist_ok=True)

MAX_BROWSER_UPLOAD = 1024**3
LARGE_UPLOAD_WARNING = 512 * 1024**2


def repo_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "ZIP / no git metadata"


def run_process(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
    live_placeholder=None,
) -> tuple[int, str]:
    """Run a child Python process, persist its complete log, and optionally stream a tail to Streamlit."""
    cmd = [str(Path(sys.executable)), *args]
    child_env = os.environ.copy()
    if env:
        child_env.update(env)
    child_env["PYTHONUNBUFFERED"] = "1"
    existing = child_env.get("PYTHONPATH", "")
    child_env["PYTHONPATH"] = str(ROOT) + (os.pathsep + existing if existing else "")

    log_path = LOGS / f"run_{time.time_ns()}.log"
    lines: list[str] = []
    try:
        with log_path.open("w", encoding="utf-8", errors="replace") as log:
            process = subprocess.Popen(
                cmd,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=child_env,
                bufsize=1,
            )
            assert process.stdout is not None
            for line in process.stdout:
                log.write(line)
                log.flush()
                lines.append(line)
                if len(lines) > 2500:
                    del lines[:500]
                if live_placeholder is not None:
                    live_placeholder.code("".join(lines[-80:]), language="text")
            return_code = process.wait()
        content = log_path.read_text(encoding="utf-8", errors="replace")
        if len(content) > 300_000:
            content = (
                f"[Earlier output omitted here; complete log: {log_path.relative_to(ROOT)}]\n"
                + content[-300_000:]
            )
        return return_code, content
    except OSError as exc:
        return 127, f"Could not start child process: {exc}"


def preparation_args(paths: Iterable[Path]) -> list[str]:
    args = [str(ROOT / "scripts" / "prepare_active_contract.py")]
    for path in paths:
        args.extend(["--input", str(path)])
    return args


def run_original(study: str, tf: int | None = None, ce_tfs: list[int] | None = None, *, live_placeholder=None):
    args = [str(ROOT / "scripts" / "run_original.py"), study]
    if tf is not None:
        args += ["--tf", str(tf)]
    if ce_tfs:
        args += ["--ce-tfs", ",".join(map(str, ce_tfs))]
    return run_process(args, live_placeholder=live_placeholder)


def save_uploaded_files(uploaded_files, key_prefix: str) -> list[Path]:
    session_dir = UPLOADS / key_prefix
    session_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for number, uploaded in enumerate(uploaded_files, 1):
        if (getattr(uploaded, "size", 0) or 0) > MAX_BROWSER_UPLOAD:
            raise ValueError(f"{uploaded.name} exceeds the 1 GiB browser limit; use Choose files on this computer instead.")
        target = session_dir / f"{number:02d}_{safe_upload_name(uploaded.name)}"
        uploaded.seek(0)
        with target.open("wb") as destination:
            while True:
                chunk = uploaded.read(8 * 1024 * 1024)
                if not chunk:
                    break
                destination.write(chunk)
        uploaded.seek(0)
        paths.append(target)
    return paths


def choose_local_files() -> list[Path]:
    """Open a native picker when the Research Lab is running on the user's local desktop."""
    if os.name != "nt":
        return []
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        names = filedialog.askopenfilenames(
            parent=root,
            title="Choose Databento / OHLCV files",
            filetypes=[
                ("Market data", "*.zip *.dbn *.zst *.parquet *.pq *.csv *.gz"),
                ("All files", "*.*"),
            ],
        )
        root.destroy()
        return [Path(name).expanduser().resolve() for name in names]
    except Exception:
        return []


def read_dataset_manifest() -> dict | None:
    path = current_manifest()
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def dataset_comparison(reference: dict) -> list[dict[str, object]]:
    manifest = read_dataset_manifest()
    if not manifest:
        return []
    study = reference["study"]
    expected = {
        "Active rows": study["active_1m_rows"],
        "Contracts": study["contracts"],
        "Duplicate timestamps": 0,
        "Missing OHLC": 0,
    }
    actual = {
        "Active rows": manifest.get("active_rows"),
        "Contracts": manifest.get("contracts"),
        "Duplicate timestamps": manifest.get("duplicate_timestamps"),
        "Missing OHLC": manifest.get("missing_ohlc"),
    }
    rows = []
    for metric, expected_value in expected.items():
        actual_value = actual.get(metric)
        rows.append({
            "Check": metric,
            "Your dataset": actual_value,
            "Published snapshot": expected_value,
            "Status": "MATCH" if actual_value == expected_value else "DIFF",
        })
    return rows


def latest_success(study: str) -> dict | None:
    data = current_pickle()
    return load_latest_success(RESULTS, data, study) if data.is_file() else None


def result_files() -> list[Path]:
    return discover_results(RESULTS)


def current_dataset_label() -> str:
    data = current_dataset()
    if not data:
        return "not prepared"
    path = Path(data["pickle"])
    return f"{data.get('generation', 'dataset')} · {path.stat().st_size / (1024**2):.1f} MB"
