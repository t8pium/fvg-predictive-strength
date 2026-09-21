from __future__ import annotations

import hashlib
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path

import duckdb
import pandas as pd

from .config import ROOT

PUBLIC_DIR = ROOT / "data" / "public" / "nsxusd"
PUBLIC_RESULTS = ROOT / "results" / "public_nsx"
PUBLIC_PARQUET = PUBLIC_DIR / "nsxusd_1m.parquet"
PUBLIC_PICKLE = PUBLIC_DIR / "active_nsxusd.pkl"
PUBLIC_MANIFEST = PUBLIC_DIR / "manifest.json"
PUBLIC_AUDIT = PUBLIC_DIR / "audit.json"
PUBLIC_ANNUAL = PUBLIC_DIR / "annual_coverage.csv"

PUBLIC_ASSET_NAME = "NSXUSD_M1_PUBLIC.zip"
PUBLIC_ASSET_URL = (
    "https://github.com/t8pium/fvg-predictive-strength/"
    "releases/latest/download/" + PUBLIC_ASSET_NAME
)

EXPERIMENT_OUTPUTS = {
    "raw_fill": ["detailed_1m/summary.json", "detailed_1m/main_results.csv"],
    "matched_attraction": ["multi_tf/magnet_tf{tf}.csv"],
    "age_decay": ["multi_tf/decay_tf{tf}.csv"],
    "continuation": ["multi_tf/formation_tf{tf}.csv"],
    "retest": ["multi_tf/reaction_tf{tf}.csv"],
    "midpoint": ["midpoint/midpoint_tf{tf}.csv"],
    "body_acceptance": ["ce_body/body_depth_5pct.csv", "ce_body/midpoint_slices.csv"],
    "controls_regimes": [
        "detailed_1m/main_results.csv",
        "detailed_1m/strat_distance.csv",
        "detailed_1m/strat_session.csv",
        "detailed_1m/strat_year.csv",
        "detailed_1m/logistic_60m.json",
    ],
    "oos": ["detailed_1m/train_test.csv", "multi_tf/oos_tf{tf}.csv"],
}


def public_ready() -> bool:
    return PUBLIC_PARQUET.is_file() and PUBLIC_PICKLE.is_file() and PUBLIC_MANIFEST.is_file()


def public_manifest() -> dict:
    if not PUBLIC_MANIFEST.is_file():
        return {}
    try:
        return json.loads(PUBLIC_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def public_audit() -> dict:
    if not PUBLIC_AUDIT.is_file():
        return {}
    try:
        return json.loads(PUBLIC_AUDIT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def ensure_pickle() -> Path:
    if PUBLIC_PICKLE.is_file():
        return PUBLIC_PICKLE
    if not PUBLIC_PARQUET.is_file():
        raise FileNotFoundError("Public NSX/USD Parquet is not installed.")
    frame = pd.read_parquet(PUBLIC_PARQUET)
    PUBLIC_PICKLE.parent.mkdir(parents=True, exist_ok=True)
    frame.to_pickle(PUBLIC_PICKLE)
    return PUBLIC_PICKLE


def _safe_extract(archive: Path, destination: Path) -> None:
    destination = destination.resolve()
    with zipfile.ZipFile(archive) as zf:
        for member in zf.infolist():
            if member.is_dir():
                continue
            target = (destination / member.filename).resolve()
            if destination not in target.parents and target != destination:
                raise ValueError("Unsafe path in public dataset archive.")
        zf.extractall(destination)


def install_public_release(
    *,
    url: str = PUBLIC_ASSET_URL,
    destination: Path = PUBLIC_DIR,
) -> dict:
    destination.mkdir(parents=True, exist_ok=True)
    temp = destination.parent / (PUBLIC_ASSET_NAME + ".partial")
    try:
        urllib.request.urlretrieve(url, temp)
        _safe_extract(temp, destination)
    finally:
        temp.unlink(missing_ok=True)

    release_manifest_path = destination / "PUBLIC_DATA_MANIFEST.json"
    if not release_manifest_path.is_file():
        raise ValueError("Public dataset archive is missing PUBLIC_DATA_MANIFEST.json.")
    release_manifest = json.loads(release_manifest_path.read_text(encoding="utf-8"))
    for item in release_manifest.get("files", []):
        path = destination / str(item["name"])
        if not path.is_file():
            raise ValueError(f"Public dataset archive is missing {path.name}.")
        expected = str(item.get("sha256", ""))
        if expected and sha256(path) != expected:
            raise ValueError(f"SHA-256 verification failed for {path.name}.")

    ensure_pickle()
    manifest = public_manifest()
    if not manifest:
        raise ValueError("Public dataset installed but manifest.json is missing or invalid.")
    return manifest


def sha256(path: Path, chunk: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def public_result_paths(exp_id: str, tf: int = 1) -> list[Path]:
    patterns = EXPERIMENT_OUTPUTS.get(exp_id, [])
    paths = [PUBLIC_RESULTS / pattern.format(tf=tf) for pattern in patterns]
    return [path for path in paths if path.is_file()]


def public_result_payload(path: Path):
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return None


def query_public_ohlcv(
    start: str,
    end: str,
    *,
    max_rows: int = 250_000,
) -> pd.DataFrame:
    if not PUBLIC_PARQUET.is_file():
        raise FileNotFoundError("Public NSX/USD dataset is not installed.")
    con = duckdb.connect()
    try:
        frame = con.execute(
            """
            SELECT ts_event, open, high, low, close, volume
            FROM read_parquet(?)
            WHERE ts_event >= CAST(? AS TIMESTAMPTZ)
              AND ts_event < CAST(? AS TIMESTAMPTZ)
            ORDER BY ts_event
            LIMIT ?
            """,
            [str(PUBLIC_PARQUET), start, end, int(max_rows)],
        ).fetchdf()
    finally:
        con.close()
    frame["ts_event"] = pd.to_datetime(frame["ts_event"], utc=True)
    return frame


def resample_ohlcv(frame: pd.DataFrame, minutes: int) -> pd.DataFrame:
    if minutes <= 1 or frame.empty:
        return frame.copy()
    x = frame.set_index(frame["ts_event"].dt.tz_convert("America/New_York"))
    out = x.resample(
        f"{minutes}min",
        origin="start_day",
        offset="18h",
        label="left",
        closed="left",
    ).agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna(subset=["open"])
    out = out.reset_index()
    out["ts_event"] = out["ts_event"].dt.tz_convert("UTC")
    return out[["ts_event", "open", "high", "low", "close", "volume"]]


def package_inventory(directory: Path) -> list[dict[str, object]]:
    rows = []
    for path in sorted(directory.iterdir()):
        if path.is_file():
            rows.append(
                {
                    "name": path.name,
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    return rows
