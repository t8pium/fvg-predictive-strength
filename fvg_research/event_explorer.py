from __future__ import annotations

import numpy as np
import pandas as pd

from .bars import market_state
from .controls import matched_controls
from .fvg import detect_fvgs, full_at_horizon, midpoint_at_horizon, touch_at_horizon


def event_catalog(bars: pd.DataFrame) -> pd.DataFrame:
    """Build a filterable event table from completed-candle FVGs."""
    events = detect_fvgs(bars)
    state = market_state(bars)
    columns = ["session", "tod_30m", "vol_regime", "trend"]
    available = [column for column in columns if column in state.columns]
    events = events.join(state[available], how="left")
    events["timestamp"] = events.index
    events["direction_label"] = np.where(events["direction"].eq(1), "Bullish", "Bearish")
    events["year"] = events.index.year
    return events


def event_outcomes(
    bars: pd.DataFrame,
    events: pd.DataFrame,
    horizons: tuple[int, ...] = (1, 5, 15, 60),
) -> pd.DataFrame:
    output = events.copy()
    for horizon in horizons:
        output[f"touch_{horizon}"] = touch_at_horizon(bars, output, horizon).to_numpy()
        output[f"mid_{horizon}"] = midpoint_at_horizon(bars, output, horizon).to_numpy()
        output[f"full_{horizon}"] = full_at_horizon(bars, output, horizon).to_numpy()
    return output


def event_window(
    bars: pd.DataFrame,
    event_ts: pd.Timestamp,
    *,
    before: int = 12,
    after: int = 60,
) -> pd.DataFrame:
    if before < 0 or after < 1:
        raise ValueError("before must be >= 0 and after must be >= 1")
    timestamp = pd.Timestamp(event_ts)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")
    try:
        position = bars.index.get_loc(timestamp)
    except KeyError as exc:
        raise KeyError(f"Event timestamp is not in the bar index: {timestamp}") from exc
    if not isinstance(position, (int, np.integer)):
        raise ValueError("Event timestamp must resolve to exactly one bar.")
    start = max(0, int(position) - before)
    end = min(len(bars), int(position) + after + 1)
    return bars.iloc[start:end].copy()


def matched_control_for_event(
    bars: pd.DataFrame,
    event_ts: pd.Timestamp,
    *,
    seed: int = 20260920,
) -> pd.Series | None:
    events = detect_fvgs(bars)
    timestamp = pd.Timestamp(event_ts)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")
    if timestamp not in events.index:
        return None
    state = market_state(bars)
    matched = matched_controls(
        events.loc[[timestamp]],
        state,
        n_controls=1,
        seed=seed,
        max_events=1,
    )
    if matched.empty:
        return None
    return matched.iloc[0]


def summarize_event(
    bars: pd.DataFrame,
    event_ts: pd.Timestamp,
    *,
    horizon: int = 60,
) -> dict[str, object]:
    events = detect_fvgs(bars)
    timestamp = pd.Timestamp(event_ts)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")
    if timestamp not in events.index:
        raise KeyError(f"No FVG exists at {timestamp}")
    event = events.loc[[timestamp]]
    row = event.iloc[0]
    return {
        "timestamp": timestamp.isoformat(),
        "direction": "bullish" if int(row["direction"]) == 1 else "bearish",
        "lower": float(row["lower"]),
        "upper": float(row["upper"]),
        "near": float(row["near"]),
        "far": float(row["far"]),
        "mid": float(row["mid"]),
        "width_points": float(row["width"]),
        "width_ticks": float(row["ticks"]),
        "width_atr": float(row["width_atr"]),
        "distance_atr": float(row["distance_atr"]),
        "touch_within_horizon": bool(touch_at_horizon(bars, event, horizon).iloc[0]),
        "midpoint_within_horizon": bool(midpoint_at_horizon(bars, event, horizon).iloc[0]),
        "full_fill_within_horizon": bool(full_at_horizon(bars, event, horizon).iloc[0]),
        "horizon_bars": int(horizon),
    }
