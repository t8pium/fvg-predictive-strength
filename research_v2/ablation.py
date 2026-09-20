from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

from fvg_research.bars import market_state
from fvg_research.controls import candidate_zones
from fvg_research.fvg import detect_fvgs, touch_at_horizon

VARIANTS = {
    "Full matching": ["session", "tod_30m", "vol_regime", "trend"],
    "No session": ["tod_30m", "vol_regime", "trend"],
    "No time-of-day": ["session", "vol_regime", "trend"],
    "No volatility regime": ["session", "tod_30m", "trend"],
    "No trend": ["session", "tod_30m", "vol_regime"],
    "Geometry only": [],
}


def _custom_controls(
    events: pd.DataFrame,
    state: pd.DataFrame,
    *,
    group_columns: list[str],
    n_controls: int,
    max_events: int,
    seed: int,
    excluded_fvg_index: pd.DatetimeIndex | None = None,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    sample = events.copy()
    if len(sample) > max_events:
        sample = sample.iloc[np.sort(rng.choice(len(sample), max_events, replace=False))]
    sample = sample.join(state[[c for c in group_columns if c in state.columns]], how="left")
    pool = candidate_zones(
        state,
        excluded_fvg_index if excluded_fvg_index is not None else events.index,
    ).dropna(subset=["atr14", "volatility"])
    output = []

    groups = [(None, sample)] if not group_columns else sample.dropna(subset=group_columns).groupby(group_columns, dropna=False)
    for key, group in groups:
        candidate_pool = pool
        if group_columns:
            values = key if isinstance(key, tuple) else (key,)
            mask = np.ones(len(pool), dtype=bool)
            for column, value in zip(group_columns, values):
                mask &= pool[column].to_numpy() == value
            candidate_pool = pool.loc[mask]
        if len(candidate_pool) < max(10, n_controls):
            continue

        candidate_features = np.column_stack([
            candidate_pool["body_b_atr"].fillna(0).to_numpy(),
            candidate_pool["volatility"].fillna(0).to_numpy() * 1000,
        ])
        event_features = np.column_stack([
            group["body_b_atr"].fillna(0).to_numpy(),
            state.reindex(group.index)["volatility"].fillna(0).to_numpy() * 1000,
        ])
        model = NearestNeighbors(n_neighbors=min(n_controls, len(candidate_pool))).fit(candidate_features)
        _, indices = model.kneighbors(event_features)

        for row_number, matches in enumerate(indices):
            event = group.iloc[row_number]
            for match in matches:
                timestamp = candidate_pool.index[match]
                bar = candidate_pool.iloc[match]
                scale = float(bar["atr14"])
                distance = float(event["distance_atr"]) * scale
                width = float(event["width_atr"]) * scale
                if int(event["direction"]) == 1:
                    upper, lower = float(bar["close"]) - distance, float(bar["close"]) - distance - width
                    near, far = upper, lower
                else:
                    lower, upper = float(bar["close"]) + distance, float(bar["close"]) + distance + width
                    near, far = lower, upper
                output.append({
                    "event_ts": event.name,
                    "control_ts": timestamp,
                    "direction": int(event["direction"]),
                    "near": near,
                    "far": far,
                    "lower": lower,
                    "upper": upper,
                    "mid": (lower + upper) / 2,
                    "width": width,
                })
    return pd.DataFrame(output)


def run_ablation(
    bars: pd.DataFrame,
    *,
    horizon: int = 60,
    max_events: int = 3000,
    n_controls: int = 2,
    seed: int = 20260920,
) -> pd.DataFrame:
    """Ablate matching assumptions on one common set of eligible parent FVGs."""
    state = market_state(bars)
    all_events = detect_fvgs(bars)
    events = all_events.copy()
    if len(events) > max_events:
        rng = np.random.default_rng(seed)
        positions = np.sort(rng.choice(len(events), max_events, replace=False))
        events = events.iloc[positions].copy()

    controls_by_variant: dict[str, pd.DataFrame] = {}
    parent_sets: list[set[pd.Timestamp]] = []
    for number, (label, group_columns) in enumerate(VARIANTS.items(), 1):
        controls = _custom_controls(
            events,
            state,
            group_columns=group_columns,
            n_controls=n_controls,
            max_events=len(events),
            seed=seed,
            excluded_fvg_index=all_events.index,
        )
        if controls.empty:
            continue
        controls_by_variant[label] = controls
        parent_sets.append(set(pd.to_datetime(controls["event_ts"], utc=True)))

    if not controls_by_variant:
        raise RuntimeError("No ablation variant produced matched controls.")

    common_parents = set.intersection(*parent_sets) if parent_sets else set()
    if len(common_parents) < 20:
        raise RuntimeError(
            "Too few common parent FVGs survived every ablation variant; "
            "increase max_events or reduce matching strictness."
        )

    common_index = pd.DatetimeIndex(sorted(common_parents))
    real = events.reindex(common_index).dropna(subset=["near"])
    real_hit = touch_at_horizon(bars, real, horizon).astype(float)

    rows = []
    for label, group_columns in VARIANTS.items():
        controls = controls_by_variant.get(label)
        if controls is None:
            continue
        controls = controls.loc[pd.to_datetime(controls["event_ts"], utc=True).isin(real.index)].copy()
        if controls.empty:
            continue
        control_hit = touch_at_horizon(bars, controls, horizon, time_col="control_ts").astype(float)
        parent_control = pd.DataFrame({
            "event_ts": pd.to_datetime(controls["event_ts"], utc=True),
            "hit": control_hit.to_numpy(),
        }).groupby("event_ts")["hit"].mean().reindex(real.index)
        paired = pd.DataFrame({
            "real": real_hit,
            "control": parent_control,
        }).dropna()
        rows.append({
            "Variant": label,
            "Matching fields": ", ".join(group_columns) if group_columns else "none",
            "Parents": int(len(paired)),
            "FVG rate": float(paired["real"].mean()),
            "Control rate": float(paired["control"].mean()),
            "Difference (pp)": float((paired["real"] - paired["control"]).mean() * 100),
        })
    return pd.DataFrame(rows)
