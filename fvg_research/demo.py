from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .bars import market_state
from .controls import matched_controls
from .fvg import detect_fvgs, touch_at_horizon


@dataclass(frozen=True)
class DemoResult:
    bars: pd.DataFrame
    events: pd.DataFrame
    controls: pd.DataFrame
    horizons: pd.DataFrame
    elapsed_seconds: float


def synthetic_ohlcv(n: int = 16_000, seed: int = 20260920) -> pd.DataFrame:
    """Generate deterministic MNQ-like OHLCV for a software demo, not market inference."""
    if n < 2_000:
        raise ValueError("Demo requires at least 2,000 bars.")
    rng = np.random.default_rng(seed)
    index = pd.date_range("2026-01-05 23:00:00+00:00", periods=n, freq="1min")
    increments = rng.normal(0, 1.05, n)
    close = 20_000 + np.cumsum(increments)
    open_ = np.r_[close[0], close[:-1]]
    pad_hi = rng.uniform(0.25, 1.5, n)
    pad_lo = rng.uniform(0.25, 1.5, n)
    high = np.maximum(open_, close) + pad_hi
    low = np.minimum(open_, close) - pad_lo
    volume = rng.integers(20, 800, n)

    frame = pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=index,
    )

    # Inject clean alternating FVG formations so the demo has enough deterministic events.
    for count, i in enumerate(range(500, n - 100, 170)):
        if count % 2 == 0:
            floor = float(frame["high"].iloc[i - 2] + rng.uniform(0.5, 1.25))
            frame.iloc[i, frame.columns.get_loc("low")] = floor
            frame.iloc[i, frame.columns.get_loc("open")] = floor + 0.25
            frame.iloc[i, frame.columns.get_loc("close")] = floor + 0.75
            frame.iloc[i, frame.columns.get_loc("high")] = floor + 1.25
        else:
            ceiling = float(frame["low"].iloc[i - 2] - rng.uniform(0.5, 1.25))
            frame.iloc[i, frame.columns.get_loc("high")] = ceiling
            frame.iloc[i, frame.columns.get_loc("open")] = ceiling - 0.25
            frame.iloc[i, frame.columns.get_loc("close")] = ceiling - 0.75
            frame.iloc[i, frame.columns.get_loc("low")] = ceiling - 1.25

    return frame


def run_demo(
    n: int = 16_000,
    seed: int = 20260920,
    max_events: int = 120,
    n_controls: int = 3,
) -> DemoResult:
    """Exercise detector → state → matching → forward-outcome pipeline on synthetic data."""
    started = time.perf_counter()
    bars = synthetic_ohlcv(n=n, seed=seed)
    state = market_state(bars)
    events = detect_fvgs(bars)
    controls = matched_controls(
        events,
        state,
        n_controls=n_controls,
        seed=seed,
        max_events=max_events,
    )
    if controls.empty:
        raise RuntimeError("Synthetic demo produced no matched controls.")

    parent_index = pd.DatetimeIndex(pd.unique(controls["event_ts"]))
    parents = events.reindex(parent_index).dropna(subset=["direction", "near"])
    rows: list[dict[str, float | int]] = []
    for horizon in (5, 15, 60):
        fvg_hit = touch_at_horizon(bars, parents, horizon)
        control_hit = touch_at_horizon(bars, controls, horizon, time_col="control_ts")
        control_parent = pd.DataFrame(
            {"event_ts": controls["event_ts"], "hit": control_hit.astype(float).to_numpy()}
        ).groupby("event_ts")["hit"].mean()
        aligned = pd.DataFrame(
            {
                "fvg": fvg_hit.astype(float),
                "control": control_parent.reindex(parents.index),
            }
        ).dropna()
        rows.append(
            {
                "horizon_bars": horizon,
                "parents": int(len(aligned)),
                "controls": int(controls["event_ts"].isin(aligned.index).sum()),
                "fvg_rate": float(aligned["fvg"].mean()),
                "control_rate": float(aligned["control"].mean()),
                "difference_pp": float((aligned["fvg"].mean() - aligned["control"].mean()) * 100),
            }
        )

    elapsed = time.perf_counter() - started
    return DemoResult(
        bars=bars,
        events=events,
        controls=controls,
        horizons=pd.DataFrame(rows),
        elapsed_seconds=elapsed,
    )
