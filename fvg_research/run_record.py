from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def dependency_fingerprint(root: str | Path) -> str:
    root = Path(root)
    digest = hashlib.sha256()
    for name in ("pyproject.toml", "requirements.txt"):
        path = root / name
        if path.is_file():
            digest.update(name.encode("utf-8"))
            digest.update(path.read_bytes())
    return digest.hexdigest()


def git_commit(root: str | Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(root),
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return None


def _file_records(paths: Iterable[str | Path], root: Path) -> list[dict[str, object]]:
    records = []
    for value in paths:
        path = Path(value)
        if not path.is_absolute():
            path = root / path
        if not path.is_file():
            continue
        try:
            display = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            display = str(path.resolve())
        records.append({
            "path": display,
            "bytes": int(path.stat().st_size),
            "sha256": sha256_file(path),
        })
    return records


def write_run_record(
    root: str | Path,
    *,
    kind: str,
    command: list[str],
    status: str,
    started_unix: float,
    finished_unix: float | None = None,
    inputs: Iterable[str | Path] = (),
    outputs: Iterable[str | Path] = (),
    extra: dict[str, object] | None = None,
) -> Path:
    root = Path(root)
    finished = time.time() if finished_unix is None else finished_unix
    dataset_manifest = root / "data" / "processed" / "current_dataset.json"
    payload: dict[str, object] = {
        "schema_version": 1,
        "kind": kind,
        "status": status,
        "command": command,
        "started_unix": started_unix,
        "finished_unix": finished,
        "elapsed_seconds": max(0.0, finished - started_unix),
        "git_commit": git_commit(root),
        "python": sys.version,
        "platform": platform.platform(),
        "dependency_fingerprint": dependency_fingerprint(root),
        "inputs": _file_records(inputs, root),
        "outputs": _file_records(outputs, root),
        "environment": {
            "cwd": str(root),
            "python_executable": sys.executable,
            "processor": platform.processor(),
        },
        "extra": extra or {},
    }
    if dataset_manifest.is_file():
        payload["dataset_pointer"] = {
            "path": str(dataset_manifest.relative_to(root)),
            "sha256": sha256_file(dataset_manifest),
        }

    target_dir = root / "results" / "_run_records"
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_kind = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in kind)
    target = target_dir / f"{int(started_unix * 1000)}_{safe_kind}.json"
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    latest = target_dir / f"latest_{safe_kind}.json"
    latest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target
