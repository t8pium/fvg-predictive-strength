from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from fvg_research.bars import market_state
from fvg_research.dataset import current_pickle
from fvg_research.fvg import detect_fvgs
from research_v2.ce_inference import ce_reinference
from research_v2.methods import (
    benjamini_hochberg,
    bounded_touch_outcome,
    cluster_bootstrap_difference,
    cme_cluster,
    matched_controls_in_window,
    parent_paired_age_decay,
    walk_forward_windows,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "research_v2"
AGE_HORIZONS = (1, 3, 5, 10, 20)


def load_bars() -> pd.DataFrame:
    path = current_pickle()
    if not path.is_file():
        raise FileNotFoundError("No active dataset is prepared.")
    bars = pd.read_pickle(path)
    if "ts_event" in bars.columns:
        bars = bars.set_index("ts_event")
    bars.index = pd.to_datetime(bars.index, utc=True)
    return bars.sort_index()


def _matched_sample(
    bars: pd.DataFrame,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
    max_events: int,
    controls_per_event: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    state = market_state(bars)
    events = detect_fvgs(bars)
    controls = matched_controls_in_window(
        events,
        state,
        start,
        end,
        n_controls=controls_per_event,
        seed=seed,
        max_events=max_events,
    )
    if controls.empty:
        raise RuntimeError("No matched controls were available in the requested window.")

    parents = pd.DatetimeIndex(pd.unique(controls["event_ts"]))
    real = events.reindex(parents).dropna(subset=["near"])
    controls = controls.loc[controls["event_ts"].isin(real.index)].copy()
    if real.empty or controls.empty:
        raise RuntimeError("No matched parent/control sample remained after alignment.")
    return real, controls


def corrected_attraction(
    bars: pd.DataFrame,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
    horizon: int,
    max_events: int,
    controls_per_event: int,
    seed: int,
    n_boot: int,
) -> dict[str, float | int | str]:
    real, controls = _matched_sample(
        bars,
        start=start,
        end=end,
        max_events=max_events,
        controls_per_event=controls_per_event,
        seed=seed,
    )

    real_hit = bounded_touch_outcome(bars, real, horizon)
    control_hit = bounded_touch_outcome(bars, controls, horizon, time_col="control_ts")
    ctrl = pd.DataFrame(
        {"event_ts": controls["event_ts"], "hit": control_hit.to_numpy()}
    ).dropna()
    ctrl_parent = ctrl.groupby("event_ts")["hit"].mean()

    paired = pd.DataFrame(
        {"real": real_hit, "control": ctrl_parent.reindex(real.index)}
    ).dropna()
    if paired.empty:
        raise RuntimeError("No fully eligible same-segment parent/control pairs remained.")

    difference = paired["real"] - paired["control"]
    bootstrap = cluster_bootstrap_difference(
        difference,
        cme_cluster(pd.DatetimeIndex(paired.index)),
        n_boot=n_boot,
        seed=seed,
    )
    return {
        "start": str(start),
        "end": str(end),
        "horizon_bars": horizon,
        "parents": int(len(paired)),
        "control_rows": int(len(ctrl)),
        "fvg_rate": float(paired["real"].mean()),
        "control_rate": float(paired["control"].mean()),
        "difference_pp": float(difference.mean() * 100),
        "ci_low_pp": float(bootstrap["ci_low"] * 100),
        "ci_high_pp": float(bootstrap["ci_high"] * 100),
        "p_two_sided": float(bootstrap["p_two_sided"]),
    }


def corrected_age_decay(
    bars: pd.DataFrame,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
    max_events: int,
    controls_per_event: int,
    seed: int,
    n_boot: int,
) -> pd.DataFrame:
    real, controls = _matched_sample(
        bars,
        start=start,
        end=end,
        max_events=max_events,
        controls_per_event=controls_per_event,
        seed=seed,
    )

    real_outcomes = pd.DataFrame(index=real.index)
    control_outcomes = controls[["event_ts"]].copy()
    horizon_columns: dict[int, str] = {}

    for horizon in AGE_HORIZONS:
        column = f"touch_{horizon}"
        horizon_columns[horizon] = column
        real_outcomes[column] = bounded_touch_outcome(bars, real, horizon)
        control_outcomes[column] = bounded_touch_outcome(
            bars,
            controls,
            horizon,
            time_col="control_ts",
        ).to_numpy()

    summary = parent_paired_age_decay(
        real_outcomes,
        control_outcomes,
        control_parent_col="event_ts",
        horizon_columns=horizon_columns,
    )

    rows: list[dict[str, object]] = []
    for start_h, end_h in zip(AGE_HORIZONS[:-1], AGE_HORIZONS[1:]):
        start_col = horizon_columns[start_h]
        end_col = horizon_columns[end_h]

        real_conditional = real_outcomes.loc[
            real_outcomes[start_col].eq(0),
            end_col,
        ].astype(float)

        ctrl_survivors = control_outcomes.loc[
            control_outcomes[start_col].eq(0),
            ["event_ts", end_col],
        ].dropna()
        ctrl_parent = ctrl_survivors.groupby("event_ts")[end_col].mean()

        paired = pd.DataFrame(
            {
                "real": real_conditional,
                "control": ctrl_parent.reindex(real_conditional.index),
            }
        ).dropna()

        if len(paired):
            diff = paired["real"] - paired["control"]
            inference = cluster_bootstrap_difference(
                diff,
                cme_cluster(pd.DatetimeIndex(paired.index)),
                n_boot=n_boot,
                seed=seed + end_h,
            )
            ci_low_pp = inference["ci_low"] * 100
            ci_high_pp = inference["ci_high"] * 100
            p_value = inference["p_two_sided"]
        else:
            ci_low_pp = np.nan
            ci_high_pp = np.nan
            p_value = np.nan

        base = summary.loc[summary["window"] == f"{start_h}→{end_h}"]
        row = base.iloc[0].to_dict() if len(base) else {
            "window": f"{start_h}→{end_h}",
            "parents": 0,
            "real_rate": np.nan,
            "control_rate": np.nan,
            "difference_pp": np.nan,
        }
        row.update(
            {
                "ci_low_pp": float(ci_low_pp),
                "ci_high_pp": float(ci_high_pp),
                "p_two_sided": float(p_value),
            }
        )
        rows.append(row)

    frame = pd.DataFrame(rows)
    if len(frame):
        frame["q_bh"] = benjamini_hochberg(frame["p_two_sided"])
    return frame


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Corrected/extended Research v2 runner. Results are new research, not published v1 evidence."
    )
    parser.add_argument("study", choices=["attraction-1m", "age-decay-1m", "walk-forward-1m", "ce-reinfer"])
    parser.add_argument("--horizon", type=int, default=60)
    parser.add_argument("--max-events", type=int, default=10_000)
    parser.add_argument("--controls", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20260920)
    parser.add_argument("--bootstrap", type=int, default=500)
    args = parser.parse_args(argv)

    OUT.mkdir(parents=True, exist_ok=True)

    if args.study == "ce-reinfer":
        ce_dir = ROOT / "results" / "ce_body"
        preferred = ce_dir / "trades.pkl"
        candidates = [preferred] if preferred.is_file() else sorted(ce_dir.glob("trades*.pkl"), key=lambda path: path.stat().st_mtime_ns, reverse=True)
        if not candidates:
            print("ERROR: No canonical CE trade-level output found. Run the ce-body suite first.", file=sys.stderr)
            return 2
        trade_file = candidates[0]
        trades = pd.read_pickle(trade_file)
        frame = ce_reinference(
            trades,
            band_width=0.05,
            min_n=20,
            n_boot=args.bootstrap,
            seed=args.seed,
        )
        frame.to_csv(OUT / "ce_reinference.csv", index=False)
        payload = {
            "research_version": "v2",
            "published_reference": False,
            "source_trade_file": str(trade_file.relative_to(ROOT)),
            "corrections": [
                "canonical trade mechanics reused unchanged",
                "uncertainty clustered by CME trade date",
                "5%-wide depth cells evaluated together",
                "Benjamini-Hochberg correction across tested timeframe/depth cells",
            ],
            "cells": frame.to_dict(orient="records"),
        }
        (OUT / "ce_reinference.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 0

    bars = load_bars()

    if args.study == "attraction-1m":
        result = corrected_attraction(
            bars,
            start=bars.index.min(),
            end=bars.index.max() + pd.Timedelta(nanoseconds=1),
            horizon=args.horizon,
            max_events=args.max_events,
            controls_per_event=args.controls,
            seed=args.seed,
            n_boot=args.bootstrap,
        )
        payload = {
            "research_version": "v2",
            "published_reference": False,
            "corrections": [
                "full requested horizon required for real and control zones",
                "outcomes cannot cross an active-contract segment",
                "parent-paired matched-control outcome",
                "bootstrap clusters use CME trade date",
            ],
            "result": result,
        }
        path = OUT / "corrected_attraction_1m.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 0

    if args.study == "age-decay-1m":
        frame = corrected_age_decay(
            bars,
            start=bars.index.min(),
            end=bars.index.max() + pd.Timedelta(nanoseconds=1),
            max_events=args.max_events,
            controls_per_event=args.controls,
            seed=args.seed,
            n_boot=args.bootstrap,
        )
        frame.to_csv(OUT / "corrected_age_decay_1m.csv", index=False)
        payload = {
            "research_version": "v2",
            "published_reference": False,
            "corrections": [
                "parent-paired conditional control outcomes",
                "full requested horizon required",
                "active-contract boundary censoring",
                "CME trade-date cluster bootstrap",
                "Benjamini-Hochberg correction across age windows",
            ],
            "windows": frame.to_dict(orient="records"),
        }
        (OUT / "corrected_age_decay_1m.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 0

    events = detect_fvgs(bars)
    windows = walk_forward_windows(events.index)
    rows = []
    for number, window in enumerate(windows, 1):
        print(
            f"Walk-forward window {number}/{len(windows)}: "
            f"{window['test_start']} → {window['test_end']}",
            flush=True,
        )
        row = corrected_attraction(
            bars,
            start=window["test_start"],
            end=window["test_end"],
            horizon=args.horizon,
            max_events=args.max_events,
            controls_per_event=args.controls,
            seed=args.seed + number,
            n_boot=args.bootstrap,
        )
        row["window"] = number
        rows.append(row)

    frame = pd.DataFrame(rows)
    if len(frame):
        frame["q_bh"] = benjamini_hochberg(frame["p_two_sided"])
    frame.to_csv(OUT / "walk_forward_1m.csv", index=False)
    payload = {
        "research_version": "v2",
        "published_reference": False,
        "corrections": [
            "controls are constructed inside each test period only",
            "full requested horizon required",
            "active-contract boundary censoring",
            "CME trade-date cluster bootstrap",
            "Benjamini-Hochberg correction across walk-forward windows",
        ],
        "windows": frame.to_dict(orient="records"),
    }
    (OUT / "walk_forward_1m.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
