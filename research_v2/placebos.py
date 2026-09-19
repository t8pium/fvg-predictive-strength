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
    """Run negative controls on one common parent-FVG sample.

    The ordinary matched-control step defines the common eligible parent set.
    Every additional placebo is then evaluated against those same real parents
    so differences are not driven by changing parent composition.
    """
    if horizon < 1:
        raise ValueError("horizon must be >= 1")

    state = market_state(bars)
    events = _sample_events(detect_fvgs(bars), max_events, seed)
    events = events.loc[events.index.isin(state.dropna(subset=["atr14"]).index)].copy()
    if len(events) < 20:
        raise RuntimeError("Too few eligible FVG events for placebo analysis.")

    matched = matched_controls(events, state, n_controls=1, seed=seed + 1, max_events=max_events)
    if matched.empty:
        raise RuntimeError("No state-matched ordinary controls were available for the placebo sample.")

    parent_index = pd.DatetimeIndex(pd.unique(matched["event_ts"]))
    real_events = events.reindex(parent_index).dropna(subset=["near"])
    matched = matched.loc[matched["event_ts"].isin(real_events.index)].copy()
    real_hit = touch_at_horizon(bars, real_events, horizon).astype(float)

    rows = [{
        "series": "Real FVG",
        "N": int(len(real_hit)),
        "touch_rate": float(real_hit.mean()),
        "difference_vs_real_pp": 0.0,
        "kind": "observed",
    }]

    matched_hit = touch_at_horizon(bars, matched, horizon, time_col="control_ts").astype(float)
    matched_parent = pd.DataFrame(
        {"event_ts": matched["event_ts"], "hit": matched_hit.to_numpy()}
    ).groupby("event_ts")["hit"].mean().reindex(real_events.index)
    paired = pd.DataFrame({"real": real_hit, "placebo": matched_parent}).dropna()
    rows.append({
        "series": "State-matched ordinary zone",
        "N": int(len(paired)),
        "touch_rate": float(paired["placebo"].mean()),
        "difference_vs_real_pp": float((paired["placebo"] - paired["real"]).mean() * 100),
        "kind": "negative control",
    })

    eligible_state = state.reindex(real_events.index).dropna(subset=["atr14", "close"])
    aligned = real_events.reindex(eligible_state.index)
    count = len(aligned)
    rng = np.random.default_rng(seed)

    permutation = rng.permutation(count)
    shuffled = _geometry_zone(
        eligible_state,
        aligned["direction"].to_numpy()[permutation],
        aligned["width_atr"].to_numpy()[permutation],
        aligned["distance_atr"].to_numpy()[permutation],
    )
    hit = touch_at_horizon(bars, shuffled, horizon).astype(float)
    paired = pd.DataFrame({"real": real_hit.reindex(shuffled.index), "placebo": hit}).dropna()
    rows.append({
        "series": "Shuffled event geometry",
        "N": int(len(paired)),
        "touch_rate": float(paired["placebo"].mean()),
        "difference_vs_real_pp": float((paired["placebo"] - paired["real"]).mean() * 100),
        "kind": "negative control",
    })

    flipped = _geometry_zone(
        eligible_state,
        -aligned["direction"].to_numpy(),
        aligned["width_atr"].to_numpy(),
        aligned["distance_atr"].to_numpy(),
    )
    hit = touch_at_horizon(bars, flipped, horizon).astype(float)
    paired = pd.DataFrame({"real": real_hit.reindex(flipped.index), "placebo": hit}).dropna()
    rows.append({
        "series": "Direction-flipped mirror",
        "N": int(len(paired)),
        "touch_rate": float(paired["placebo"].mean()),
        "difference_vs_real_pp": float((paired["placebo"] - paired["real"]).mean() * 100),
        "kind": "negative control",
    })

    offset = pd.Timedelta(minutes=max(390, horizon + 30))
    original_index = eligible_state.index
    shifted_index = original_index + offset
    valid_mask = shifted_index.isin(state.index)
    if int(valid_mask.sum()) >= 20:
        original = aligned.loc[original_index[valid_mask]].copy()
        shifted_times = shifted_index[valid_mask]
        shifted_state = state.reindex(shifted_times)
        complete = shifted_state[["atr14", "close"]].notna().all(axis=1).to_numpy()
        shifted_state = shifted_state.iloc[np.flatnonzero(complete)].copy()
        original = original.iloc[np.flatnonzero(complete)].copy()
        if len(original) >= 20:
            shifted = _geometry_zone(
                shifted_state,
                original["direction"].to_numpy(),
                original["width_atr"].to_numpy(),
                original["distance_atr"].to_numpy(),
            )
            hit = touch_at_horizon(bars, shifted, horizon).astype(float)
            original_real = real_hit.reindex(original.index).reset_index(drop=True)
            shifted_hit = hit.reset_index(drop=True)
            paired = pd.DataFrame({"real": original_real, "placebo": shifted_hit}).dropna()
            rows.append({
                "series": "Time-shifted geometry",
                "N": int(len(paired)),
                "touch_rate": float(paired["placebo"].mean()),
                "difference_vs_real_pp": float((paired["placebo"] - paired["real"]).mean() * 100),
                "kind": "negative control",
            })

    return pd.DataFrame(rows)
