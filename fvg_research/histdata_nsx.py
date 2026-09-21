from __future__ import annotations

import heapq
import json
from collections import Counter
from datetime import timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SOURCE_TIMESTAMP = "timestamp_est_fixed"
OHLCV = ("open", "high", "low", "close", "volume")
REQUIRED = {SOURCE_TIMESTAMP, *OHLCV}
FIXED_EST = timezone(timedelta(hours=-5))


def _fixed_est_to_utc(values: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Parse HistData's fixed-EST clock and return (naive source time, UTC time)."""
    parsed = pd.to_datetime(values, format="%Y-%m-%d %H:%M:%S", errors="coerce")
    utc = parsed.dt.tz_localize(FIXED_EST).dt.tz_convert("UTC")
    return parsed, utc


def _trade_date(utc: pd.Series) -> pd.Series:
    """18:00 America/New_York begins the next research trade date."""
    eastern = utc.dt.tz_convert("America/New_York")
    local_midnight = eastern.dt.normalize().dt.tz_localize(None)
    return local_midnight + pd.to_timedelta((eastern.dt.hour >= 18).astype("int8"), unit="D")


def _constant_category(length: int, value: str) -> pd.Categorical:
    codes = np.zeros(length, dtype=np.int8)
    return pd.Categorical.from_codes(codes, categories=[value])


def _push_gap(heap: list[tuple[int, str, str]], seconds: int, left: pd.Timestamp, right: pd.Timestamp) -> None:
    item = (int(seconds), left.isoformat(), right.isoformat())
    if len(heap) < 25:
        heapq.heappush(heap, item)
    elif item[0] > heap[0][0]:
        heapq.heapreplace(heap, item)


def prepare_histdata_nsx(
    source: str | Path,
    output_dir: str | Path,
    *,
    chunksize: int = 500_000,
) -> dict[str, Any]:
    """
    Audit HistData NSX/USD M1 data and write a schema-compatible research dataset.

    This is intentionally an *external index-proxy* dataset. It does not become the
    published MNQ dataset and it is never activated through current_dataset.json.
    """
    source = Path(source).expanduser().resolve()
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not source.is_file():
        raise FileNotFoundError(source)

    frames: list[pd.DataFrame] = []
    annual = Counter()
    audit: dict[str, Any] = {
        "source": str(source),
        "source_bytes": int(source.stat().st_size),
        "instrument": "HistData NSX/USD",
        "dataset_kind": "nasdaq_100_index_proxy",
        "rows": 0,
        "bad_timestamp_rows": 0,
        "missing_or_non_numeric": {column: 0 for column in OHLCV},
        "invalid_ohlc_geometry_rows": 0,
        "nonpositive_price_rows": 0,
        "duplicate_adjacent_timestamps": 0,
        "nonmonotonic_timestamp_transitions": 0,
        "non_minute_aligned_rows": 0,
        "zero_volume_rows": 0,
        "nonzero_volume_rows": 0,
        "gaps_gt_1m": 0,
        "gaps_gt_5m": 0,
        "gaps_gt_60m": 0,
        "gaps_gt_12h": 0,
        "gaps_gt_24h": 0,
        "gaps_gt_48h": 0,
        "first_source_timestamp_fixed_est": None,
        "last_source_timestamp_fixed_est": None,
        "first_timestamp_utc": None,
        "last_timestamp_utc": None,
        "largest_gaps": [],
        "timezone": {
            "source_clock": "fixed EST (UTC-05:00), no daylight-saving adjustment",
            "conversion": "localize source clock to UTC-05:00, then convert to UTC",
        },
        "limitations": [
            "NSX/USD is not CME NQ or MNQ futures.",
            "HistData volume is not centralized exchange volume; this file commonly contains zero volume.",
            "There are no futures contract identifiers or roll boundaries in this source.",
            "Canonical v1 code contains MNQ-specific assumptions such as a 0.25-point tick in some sensitivity calculations.",
            "Use this dataset for discovery/cross-market robustness, not as a replacement for futures-specific validation.",
        ],
    }

    previous_utc: pd.Timestamp | None = None
    largest: list[tuple[int, str, str]] = []
    first_columns_checked = False

    reader = pd.read_csv(source, chunksize=chunksize)
    try:
        for chunk in reader:
            chunk.columns = [str(column).strip().lower() for column in chunk.columns]
            if not first_columns_checked:
                missing = REQUIRED.difference(chunk.columns)
                if missing:
                    raise ValueError(f"Missing required HistData columns: {sorted(missing)}")
                first_columns_checked = True

            source_ts, utc = _fixed_est_to_utc(chunk[SOURCE_TIMESTAMP])
            audit["rows"] += int(len(chunk))
            audit["bad_timestamp_rows"] += int(source_ts.isna().sum())
            audit["non_minute_aligned_rows"] += int(
                ((source_ts.dt.second.fillna(0) != 0) | (source_ts.dt.microsecond.fillna(0) != 0)).sum()
            )

            numeric: dict[str, pd.Series] = {}
            for column in OHLCV:
                values = pd.to_numeric(chunk[column], errors="coerce")
                numeric[column] = values
                audit["missing_or_non_numeric"][column] += int(values.isna().sum())

            o = numeric["open"].to_numpy(float)
            h = numeric["high"].to_numpy(float)
            l = numeric["low"].to_numpy(float)
            c = numeric["close"].to_numpy(float)
            v = numeric["volume"].to_numpy(float)
            finite = np.isfinite(o) & np.isfinite(h) & np.isfinite(l) & np.isfinite(c)

            audit["invalid_ohlc_geometry_rows"] += int(
                np.sum(finite & ((h < np.maximum.reduce([o, l, c])) | (l > np.minimum.reduce([o, h, c]))))
            )
            audit["nonpositive_price_rows"] += int(
                np.sum(finite & ((o <= 0) | (h <= 0) | (l <= 0) | (c <= 0)))
            )
            audit["zero_volume_rows"] += int(np.sum(np.isfinite(v) & (v == 0)))
            audit["nonzero_volume_rows"] += int(np.sum(np.isfinite(v) & (v != 0)))

            valid_source = source_ts.dropna()
            if len(valid_source):
                counts = valid_source.dt.year.value_counts()
                for year, count in counts.items():
                    annual[int(year)] += int(count)
                if audit["first_source_timestamp_fixed_est"] is None:
                    audit["first_source_timestamp_fixed_est"] = valid_source.iloc[0].isoformat()
                audit["last_source_timestamp_fixed_est"] = valid_source.iloc[-1].isoformat()

            valid_utc = utc.dropna()
            if len(valid_utc):
                if audit["first_timestamp_utc"] is None:
                    audit["first_timestamp_utc"] = valid_utc.iloc[0].isoformat()
                audit["last_timestamp_utc"] = valid_utc.iloc[-1].isoformat()

                values = valid_utc.astype("int64").to_numpy()
                stamps = valid_utc.to_numpy()
                if previous_utc is not None:
                    values = np.concatenate([[previous_utc.value], values])
                    stamps = np.concatenate([[previous_utc.to_datetime64()], stamps])
                if len(values) > 1:
                    seconds = np.diff(values) // 1_000_000_000
                    audit["duplicate_adjacent_timestamps"] += int(np.sum(seconds == 0))
                    audit["nonmonotonic_timestamp_transitions"] += int(np.sum(seconds < 0))
                    for key, threshold in (
                        ("gaps_gt_1m", 60),
                        ("gaps_gt_5m", 300),
                        ("gaps_gt_60m", 3600),
                        ("gaps_gt_12h", 43_200),
                        ("gaps_gt_24h", 86_400),
                        ("gaps_gt_48h", 172_800),
                    ):
                        audit[key] += int(np.sum(seconds > threshold))
                    for index in np.flatnonzero(seconds > 60):
                        _push_gap(
                            largest,
                            int(seconds[index]),
                            pd.Timestamp(stamps[index]),
                            pd.Timestamp(stamps[index + 1]),
                        )
                previous_utc = valid_utc.iloc[-1]

            frame = pd.DataFrame(
                {
                    "ts_event": utc,
                    "open": numeric["open"],
                    "high": numeric["high"],
                    "low": numeric["low"],
                    "close": numeric["close"],
                    "volume": numeric["volume"],
                }
            )
            frames.append(frame)
    finally:
        reader.close()

    audit["largest_gaps"] = [
        {"seconds": seconds, "minutes": seconds / 60.0, "from_utc": left, "to_utc": right}
        for seconds, left, right in sorted(largest, reverse=True)
    ]
    audit["annual_rows"] = {str(year): annual[year] for year in sorted(annual)}
    audit["volume_usable"] = bool(audit["nonzero_volume_rows"])

    audit_path = output_dir / "audit.json"
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    failure_counts = {
        "bad_timestamp_rows": audit["bad_timestamp_rows"],
        "invalid_ohlc_geometry_rows": audit["invalid_ohlc_geometry_rows"],
        "nonpositive_price_rows": audit["nonpositive_price_rows"],
        "duplicate_adjacent_timestamps": audit["duplicate_adjacent_timestamps"],
        "nonmonotonic_timestamp_transitions": audit["nonmonotonic_timestamp_transitions"],
        "non_minute_aligned_rows": audit["non_minute_aligned_rows"],
        "missing_or_non_numeric": sum(audit["missing_or_non_numeric"].values()),
    }
    failed = {key: int(value) for key, value in failure_counts.items() if value}
    if failed:
        raise ValueError(
            f"HistData audit failed; see {audit_path}. Blocking issues: {failed}"
        )

    if not frames:
        raise ValueError("No rows found in HistData input.")

    active = pd.concat(frames, ignore_index=True, copy=False)
    if active["ts_event"].isna().any():
        raise ValueError("Unexpected NaT remained after successful timestamp audit.")
    if active["ts_event"].duplicated().any():
        raise ValueError("Unexpected duplicate timestamps remained after successful audit.")

    active["symbol"] = _constant_category(len(active), "NSXUSD")
    active["trade_date"] = _trade_date(active["ts_event"])
    active["active_symbol"] = _constant_category(len(active), "NSXUSD")
    active["roll_date"] = False

    parquet_path = output_dir / "nsxusd_1m.parquet"
    pickle_path = output_dir / "active_nsxusd.pkl"
    manifest_path = output_dir / "manifest.json"
    annual_path = output_dir / "annual_coverage.csv"

    active.to_parquet(parquet_path, index=False)
    active.to_pickle(pickle_path)
    pd.DataFrame(
        [{"year": year, "rows": annual[year]} for year in sorted(annual)]
    ).to_csv(annual_path, index=False)

    manifest = {
        "version": 1,
        "dataset_id": "histdata_nsxusd_m1",
        "dataset_kind": "external_index_proxy",
        "instrument": "NSX/USD",
        "rows": int(len(active)),
        "start_utc": active["ts_event"].min().isoformat(),
        "end_utc": active["ts_event"].max().isoformat(),
        "volume_usable": bool(audit["volume_usable"]),
        "futures_contracts": False,
        "roll_censoring_available": False,
        "tick_size": None,
        "source_timestamp_convention": audit["timezone"],
        "pickle": pickle_path.name,
        "parquet": parquet_path.name,
        "audit": audit_path.name,
        "annual_coverage": annual_path.name,
        "runner_example": (
            "python scripts/run_original.py detailed-1m "
            f"--data {pickle_path.as_posix()} "
            "--results-root results/external/nsxusd"
        ),
        "research_status": (
            "Discovery/cross-market robustness only. Not a substitute for CME NQ/MNQ validation."
        ),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return {
        **manifest,
        "audit_path": str(audit_path),
        "manifest_path": str(manifest_path),
        "pickle_path": str(pickle_path),
        "parquet_path": str(parquet_path),
        "annual_path": str(annual_path),
    }
