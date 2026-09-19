from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

from .config import ACTIVE_1M, ACTIVE_PICKLE, PROCESSED, ROOT

CURRENT_DATASET = PROCESSED / "current_dataset.json"
GENERATIONS = PROCESSED / "datasets"


def _resolve(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def current_dataset() -> dict[str, Path | str | int] | None:
    """Return the active dataset generation, with backward-compatible legacy fallback."""
    if CURRENT_DATASET.is_file():
        try:
            payload = json.loads(CURRENT_DATASET.read_text(encoding="utf-8"))
            pickle_path = _resolve(payload.get("pickle"))
            parquet_path = _resolve(payload.get("parquet"))
            manifest_path = _resolve(payload.get("manifest"))
            if pickle_path and pickle_path.is_file():
                return {
                    "pickle": pickle_path,
                    "parquet": parquet_path or ACTIVE_1M,
                    "manifest": manifest_path or ACTIVE_1M.with_suffix(".manifest.json"),
                    "generation": payload.get("generation", "pointer"),
                    "created_ns": int(payload.get("created_ns", 0)),
                }
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
    if ACTIVE_PICKLE.is_file():
        return {
            "pickle": ACTIVE_PICKLE,
            "parquet": ACTIVE_1M,
            "manifest": PROCESSED / "active_mnq.manifest.json",
            "generation": "legacy",
            "created_ns": ACTIVE_PICKLE.stat().st_mtime_ns,
        }
    return None


def current_pickle() -> Path:
    dataset = current_dataset()
    return Path(dataset["pickle"]) if dataset else ACTIVE_PICKLE


def current_parquet() -> Path:
    dataset = current_dataset()
    return Path(dataset["parquet"]) if dataset else ACTIVE_1M


def current_manifest() -> Path:
    dataset = current_dataset()
    return Path(dataset["manifest"]) if dataset else PROCESSED / "active_mnq.manifest.json"


def dataset_ready() -> bool:
    return current_pickle().is_file()


def new_generation_dir() -> Path:
    GENERATIONS.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
    path = GENERATIONS / f"{stamp}_{os.getpid()}_{time.time_ns() % 1_000_000_000:09d}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def activate_generation(pickle_path: Path, parquet_path: Path, manifest_path: Path) -> dict[str, object]:
    """Atomically point the app at a completed generation; large dataset files are never replaced in place."""
    for path in (pickle_path, parquet_path, manifest_path):
        if not path.is_file():
            raise FileNotFoundError(f"Cannot activate missing dataset artifact: {path}")
    payload: dict[str, object] = {
        "version": 1,
        "generation": pickle_path.parent.name,
        "created_ns": time.time_ns(),
        "pickle": _relative(pickle_path),
        "parquet": _relative(parquet_path),
        "manifest": _relative(manifest_path),
    }
    CURRENT_DATASET.parent.mkdir(parents=True, exist_ok=True)
    temp = CURRENT_DATASET.with_name(CURRENT_DATASET.name + f".{os.getpid()}.partial")
    temp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(temp, CURRENT_DATASET)
    return payload


def cleanup_old_generations(keep: int = 2) -> None:
    """Best-effort cleanup; locked Windows generations are retained and retried next import."""
    if keep < 1 or not GENERATIONS.is_dir():
        return
    active = current_dataset()
    active_dir = Path(active["pickle"]).parent.resolve() if active else None
    directories = sorted(
        (p for p in GENERATIONS.iterdir() if p.is_dir()),
        key=lambda p: p.stat().st_mtime_ns,
        reverse=True,
    )
    protected = set(directories[:keep])
    if active_dir:
        protected.add(active_dir)
    for directory in directories:
        if directory.resolve() in protected:
            continue
        try:
            shutil.rmtree(directory)
        except OSError:
            pass
