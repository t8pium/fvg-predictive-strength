from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from fvg_research.active_contract import cme_trade_date
from fvg_research.controls import matched_controls


def full_horizon_mask(index: pd.Index, horizon: int) -> pd.Series:
    """Mark rows with a complete requested future horizon."""
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    values = np.arange(len(index)) + horizon < len(index)
    return pd.Series(values, index=index)


def contiguous_segment_id(symbol: pd.Series) -> pd.Series:
    """Return an integer id that changes whenever the active contract symbol changes."""
    if len(symbol) == 0:
        return pd.Series(dtype="int64", index=symbol.index)
    changed = symbol.astype(str).ne(symbol.astype(str).shift())
    return changed.cumsum().astype("int64") - 1


def bounded_touch_outcome(
    bars: pd.DataFrame,
    zones: pd.DataFrame,
    horizon: int,
    *,
    level: str = "near",
    time_col: str | None = None,
) -> pd.Series:
    """Touch outcome with full-horizon eligibility and active-contract segment censoring.

    Returns 1/0 for eligible cases and NaN when a complete same-segment horizon is unavailable.
    """
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    if level not in zones.columns:
        raise ValueError(f"zones has no {level!r} column")
    if not isinstance(bars.index, pd.DatetimeIndex):
        raise ValueError("bars must use a DatetimeIndex")

    positions = pd.Series(np.arange(len(bars)), index=bars.index)
    if "symbol" in bars.columns:
        segments = contiguous_segment_id(bars["symbol"]).to_numpy()
    else:
        segments = np.zeros(len(bars), dtype=np.int64)

    timestamps = pd.DatetimeIndex(zones[time_col]) if time_col else pd.DatetimeIndex(zones.index)
    pos = positions.reindex(timestamps).to_numpy()
    direction = zones["direction"].to_numpy()
    threshold = zones[level].to_numpy(dtype=float)
    result = np.full(len(zones), np.nan, dtype=float)

    highs = bars["high"].to_numpy(dtype=float)
    lows = bars["low"].to_numpy(dtype=float)

    for row, raw_position in enumerate(pos):
        if pd.isna(raw_position):
            continue
        start = int(raw_position)
        end = start + horizon
        if end >= len(bars):
            continue
        if segments[end] != segments[start]:
            continue
        future_high = highs[start + 1:end + 1]
        future_low = lows[start + 1:end + 1]
        if direction[row] == 1:
            result[row] = float(np.any(future_low <= threshold[row]))
        elif direction[row] == -1:
            result[row] = float(np.any(future_high >= threshold[row]))
    return pd.Series(result, index=zones.index, name=f"touch_{horizon}")


def cme_cluster(index: pd.DatetimeIndex) -> pd.Series:
    """Cluster labels aligned to the CME trade date, including the 18:00 ET boundary."""
    return cme_trade_date(pd.DatetimeIndex(index)).reset_index(drop=True)


def matched_controls_in_window(
    events: pd.DataFrame,
    state: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    *,
    n_controls: int = 3,
    seed: int = 20260920,
    max_events: int | None = None,
) -> pd.DataFrame:
    """Construct controls using candidates from the same chronological window only."""
    event_window = events.loc[(events.index >= start) & (events.index < end)]
    state_window = state.loc[(state.index >= start) & (state.index < end)]
    return matched_controls(
        event_window,
        state_window,
        n_controls=n_controls,
        seed=seed,
        max_events=max_events,
    )


def parent_paired_age_decay(
    real: pd.DataFrame,
    controls: pd.DataFrame,
    *,
    control_parent_col: str,
    horizon_columns: Mapping[int, str],
) -> pd.DataFrame:
    """Parent-paired conditional decay instead of survivor-zone weighted controls.

    Each parent receives at most one real observation and one mean control observation
    for each age interval, regardless of how many control zones survive.
    """
    horizons = sorted(horizon_columns)
    if len(horizons) < 2:
        raise ValueError("At least two horizons are required.")
    rows: list[dict[str, float | int | str]] = []
    for start_h, end_h in zip(horizons[:-1], horizons[1:]):
        start_col = horizon_columns[start_h]
        end_col = horizon_columns[end_h]
        if start_col not in real or end_col not in real:
            raise ValueError("Real frame is missing horizon columns.")
        if start_col not in controls or end_col not in controls:
            raise ValueError("Control frame is missing horizon columns.")

        real_survivor = real[start_col].eq(0)
        real_conditional = real.loc[real_survivor, end_col].astype(float)

        ctrl = controls.loc[controls[start_col].eq(0), [control_parent_col, end_col]].copy()
        ctrl_parent = ctrl.groupby(control_parent_col)[end_col].mean()

        paired = pd.DataFrame(
            {
                "real": real_conditional,
                "control": ctrl_parent.reindex(real_conditional.index),
            }
        ).dropna()

        rows.append(
            {
                "window": f"{start_h}→{end_h}",
                "parents": int(len(paired)),
                "real_rate": float(paired["real"].mean()) if len(paired) else np.nan,
                "control_rate": float(paired["control"].mean()) if len(paired) else np.nan,
                "difference_pp": float((paired["real"].mean() - paired["control"].mean()) * 100)
                if len(paired)
                else np.nan,
            }
        )
    return pd.DataFrame(rows)


def cluster_bootstrap_difference(
    differences: pd.Series,
    clusters: pd.Series,
    *,
    n_boot: int = 1000,
    seed: int = 20260920,
) -> dict[str, float]:
    """Bootstrap a paired parent-level difference by CME trade-date cluster."""
    if n_boot < 1:
        raise ValueError("n_boot must be >= 1")
    frame = pd.DataFrame({"difference": differences.to_numpy(), "cluster": clusters.to_numpy()}).dropna()
    unique = pd.Index(frame["cluster"].unique())
    if len(frame) == 0 or len(unique) == 0:
        return {"estimate": np.nan, "ci_low": np.nan, "ci_high": np.nan, "p_two_sided": np.nan}

    groups = {key: frame.loc[frame["cluster"] == key, "difference"] for key in unique}
    rng = np.random.default_rng(seed)
    values = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        sampled = rng.choice(unique, size=len(unique), replace=True)
        values[i] = pd.concat([groups[key] for key in sampled], ignore_index=True).mean()

    estimate = float(frame["difference"].mean())
    ci_low, ci_high = np.percentile(values, [2.5, 97.5])
    p_negative = float(np.mean(values <= 0))
    p_positive = float(np.mean(values >= 0))
    return {
        "estimate": estimate,
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "p_two_sided": float(min(1.0, 2 * min(p_negative, p_positive))),
    }


def benjamini_hochberg(p_values) -> np.ndarray:
    """Benjamini-Hochberg false-discovery-rate adjusted q-values."""
    p = np.asarray(p_values, dtype=float)
    q = np.full_like(p, np.nan)
    valid = np.flatnonzero(np.isfinite(p))
    if not len(valid):
        return q
    pv = p[valid]
    order = np.argsort(pv)
    ranked = pv[order]
    m = len(ranked)
    adjusted = ranked * m / np.arange(1, m + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    adjusted = np.clip(adjusted, 0, 1)
    restored = np.empty_like(adjusted)
    restored[order] = adjusted
    q[valid] = restored
    return q


def walk_forward_windows(
    index: pd.DatetimeIndex,
    *,
    min_train_fraction: float = 0.50,
    test_fraction: float = 0.10,
    step_fraction: float = 0.10,
) -> list[dict[str, pd.Timestamp]]:
    """Create expanding-train, forward-test windows from an ordered event index."""
    if not 0 < min_train_fraction < 1:
        raise ValueError("min_train_fraction must be between 0 and 1")
    if not 0 < test_fraction < 1 or not 0 < step_fraction < 1:
        raise ValueError("test_fraction and step_fraction must be between 0 and 1")
    ordered = pd.DatetimeIndex(index).sort_values().unique()
    n = len(ordered)
    if n < 20:
        return []
    train_end = max(1, int(n * min_train_fraction))
    test_size = max(1, int(n * test_fraction))
    step = max(1, int(n * step_fraction))
    windows = []
    while train_end < n:
        test_end = min(n, train_end + test_size)
        if test_end <= train_end:
            break
        windows.append(
            {
                "train_start": ordered[0],
                "train_end": ordered[train_end - 1],
                "test_start": ordered[train_end],
                "test_end": ordered[test_end - 1] + pd.Timedelta(nanoseconds=1),
            }
        )
        if test_end == n:
            break
        train_end += step
    return windows
