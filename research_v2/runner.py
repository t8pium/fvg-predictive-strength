from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from fvg_research.bars import market_state
from fvg_research.dataset import current_pickle
from fvg_research.fvg import detect_fvgs
from research_v2.methods import (
    benjamini_hochberg,
    bounded_touch_outcome,
    cluster_bootstrap_difference,
    cme_cluster,
    matched_controls_in_window,
    walk_forward_windows,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "research_v2"


def load_bars() -> pd.DataFrame:
    path = current_pickle()
    if not path.is_file():
        raise FileNotFoundError("No active dataset is prepared.")
    bars = pd.read_pickle(path)
    if "ts_event" in bars.columns:
        bars = bars.set_index("ts_event")
    bars.index = pd.to_datetime(bars.index, utc=True)
    return bars.sort_index()


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Corrected/extended Research v2 runner. Results are new research, not published v1 evidence."
    )
    parser.add_argument("study", choices=["attraction-1m", "walk-forward-1m"])
    parser.add_argument("--horizon", type=int, default=60)
    parser.add_argument("--max-events", type=int, default=10_000)
    parser.add_argument("--controls", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20260920)
    parser.add_argument("--bootstrap", type=int, default=500)
    args = parser.parse_args(argv)

    bars = load_bars()
    OUT.mkdir(parents=True, exist_ok=True)

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

    events = detect_fvgs(bars)
    windows = walk_forward_windows(events.index)
    rows = []
    for number, window in enumerate(windows, 1):
        print(f"Walk-forward window {number}/{len(windows)}: {window['test_start']} → {window['test_end']}", flush=True)
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
