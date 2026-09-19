from __future__ import annotations

import numpy as np
import pandas as pd

from fvg_research.bars import market_state
from fvg_research.controls import matched_controls
from fvg_research.fvg import detect_fvgs, touch_at_horizon


def _sample_events(events: pd.DataFrame, max_events: int, seed: int) -> pd.DataFrame:
    if max_events < 1:
        raise ValueError("max_events must be >= 1")
    if len(events) <= max_events:
        return events.copy()
    rng = np.random.default_rng(seed)
    positions = np.sort(rng.choice(len(events), max_events, replace=False))
    return events.iloc[positions].copy()


def _geometry_zone(
    state_rows: pd.DataFrame,
    direction: np.ndarray,
    width_atr: np.ndarray,
    distance_atr: np.ndarray,
) -> pd.DataFrame:
    close = state_rows["close"].to_numpy(float)
    atr = state_rows["atr14"].to_numpy(float)
    width = width_atr * atr
    distance = distance_atr * atr

    bullish = direction == 1
    near = np.where(bullish, close - distance, close + distance)
    far = np.where(bullish, near - width, near + width)
    lower = np.minimum(near, far)
    upper = np.maximum(near, far)
    return pd.DataFrame(
        {
            "direction": direction.astype(int),
            "near": near,
            "far": far,
            "lower": lower,
            "upper": upper,
            "mid": (lower + upper) / 2,
            "width": width,
            "width_atr": width_atr,
            "distance_atr": distance_atr,
        },
        index=state_rows.index,
    )


def placebo_suite(
    bars: pd.DataFrame,
    *,
    horizon: int = 60,
    max_events: int = 5000,
    seed: int = 20260920,
) -> pd.DataFrame:
    """Run negative controls that should not create a stable FVG-specific edge."""
    if horizon < 1:
        raise ValueError("horizon must be >= 1")

    state = market_state(bars)
    events = detect_fvgs(bars)
    events = _sample_events(events, max_events, seed)
    events = events.loc[events.index.isin(state.dropna(subset=["atr14"]).index)].copy()
    if len(events) < 20:
        raise RuntimeError("Too few eligible FVG events for placebo analysis.")

    rng = np.random.default_rng(seed)
    real = touch_at_horizon(bars, events, horizon).astype(float)
    rows = [{
        "series": "Real FVG",
        "N": int(len(real)),
        "touch_rate": float(real.mean()),
        "difference_vs_real_pp": 0.0,
        "kind": "observed",
    }]

    matched = matched_controls(events, state, n_controls=1, seed=seed + 1, max_events=max_events)
    if len(matched):
        hit = touch_at_horizon(bars, matched, horizon, time_col="control_ts").astype(float)
        rows.append({
            "series": "State-matched ordinary zone",
            "N": int(len(hit)),
            "touch_rate": float(hit.mean()),
            "difference_vs_real_pp": float((hit.mean() - real.mean()) * 100),
            "kind": "negative control",
        })

    eligible_state = state.reindex(events.index).dropna(subset=["atr14", "close"])
    aligned = events.reindex(eligible_state.index)
    count = len(aligned)

    permutation = rng.permutation(count)
    shuffled = _geometry_zone(
        eligible_state,
        aligned["direction"].to_numpy()[permutation],
        aligned["width_atr"].to_numpy()[permutation],
        aligned["distance_atr"].to_numpy()[permutation],
    )
    hit = touch_at_horizon(bars, shuffled, horizon).astype(float)
    rows.append({
        "series": "Shuffled event geometry",
        "N": int(len(hit)),
        "touch_rate": float(hit.mean()),
        "difference_vs_real_pp": float((hit.mean() - real.reindex(shuffled.index).mean()) * 100),
        "kind": "negative control",
    })

    flipped = _geometry_zone(
        eligible_state,
        -aligned["direction"].to_numpy(),
        aligned["width_atr"].to_numpy(),
        aligned["distance_atr"].to_numpy(),
    )
    hit = touch_at_horizon(bars, flipped, horizon).astype(float)
    rows.append({
        "series": "Direction-flipped mirror",
        "N": int(len(hit)),
        "touch_rate": float(hit.mean()),
        "difference_vs_real_pp": float((hit.mean() - real.reindex(flipped.index).mean()) * 100),
        "kind": "negative control",
    })

    shifted_index = eligible_state.index + pd.Timedelta(minutes=max(390, horizon + 30))
    valid = shifted_index.intersection(state.index)
    if len(valid) >= 20:
        original_positions = eligible_state.index.get_indexer(valid - pd.Timedelta(minutes=max(390, horizon + 30)))
        original_positions = original_positions[original_positions >= 0]
        shifted_state = state.reindex(valid).dropna(subset=["atr14", "close"])
        original = aligned.iloc[original_positions[: len(shifted_state)]]
        shifted_state = shifted_state.iloc[: len(original)]
        shifted = _geometry_zone(
            shifted_state,
            original["direction"].to_numpy(),
            original["width_atr"].to_numpy(),
            original["distance_atr"].to_numpy(),
        )
        hit = touch_at_horizon(bars, shifted, horizon).astype(float)
        rows.append({
            "series": "Time-shifted geometry",
            "N": int(len(hit)),
            "touch_rate": float(hit.mean()),
            "difference_vs_real_pp": float((hit.mean() - real.mean()) * 100),
            "kind": "negative control",
        })

    return pd.DataFrame(rows)
