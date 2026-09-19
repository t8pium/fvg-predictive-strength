from __future__ import annotations

import math

import numpy as np
import pandas as pd

from research_v2.methods import benjamini_hochberg, cme_cluster


def depth_band_labels(depth: pd.Series, width: float = 0.05) -> pd.Series:
    if not 0 < width <= 1:
        raise ValueError("width must be in (0, 1]")
    clipped = depth.clip(lower=0, upper=np.nextafter(1.0, 0.0))
    lower = np.floor(clipped / width) * width
    upper = np.minimum(lower + width, 1.0)
    labels = [
        f"{lo * 100:.0f}-{hi * 100:.0f}%"
        for lo, hi in zip(lower.to_numpy(), upper.to_numpy())
    ]
    return pd.Series(labels, index=depth.index, dtype="string")


def _cluster_bootstrap_metric(
    frame: pd.DataFrame,
    *,
    value_col: str,
    cluster_col: str,
    n_boot: int,
    seed: int,
) -> dict[str, float]:
    if n_boot < 1:
        raise ValueError("n_boot must be >= 1")
    clean = frame[[value_col, cluster_col]].dropna()
    clusters = pd.Index(clean[cluster_col].unique())
    if clean.empty or clusters.empty:
        return {
            "estimate": math.nan,
            "ci_low": math.nan,
            "ci_high": math.nan,
            "p_two_sided": math.nan,
        }

    groups = {key: clean.loc[clean[cluster_col] == key, value_col] for key in clusters}
    rng = np.random.default_rng(seed)
    samples = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        chosen = rng.choice(clusters, size=len(clusters), replace=True)
        samples[i] = pd.concat([groups[key] for key in chosen], ignore_index=True).mean()

    estimate = float(clean[value_col].mean())
    low, high = np.percentile(samples, [2.5, 97.5])
    below = float(np.mean(samples <= 0))
    above = float(np.mean(samples >= 0))
    return {
        "estimate": estimate,
        "ci_low": float(low),
        "ci_high": float(high),
        "p_two_sided": float(min(1.0, 2 * min(below, above))),
    }


def ce_reinference(
    trades: pd.DataFrame,
    *,
    band_width: float = 0.05,
    min_n: int = 20,
    n_boot: int = 250,
    seed: int = 20260920,
) -> pd.DataFrame:
    """Re-infer CE depth cells with trade-date clustering and FDR correction.

    This does not redefine the canonical signal/trade mechanics. It reuses the
    canonical trade-level output and changes only the uncertainty/multiplicity layer.
    """
    required = {
        "timeframe",
        "mode",
        "trigger_ts",
        "depth",
        "outcome_code",
        "realized_R_conservative",
    }
    missing = sorted(required - set(trades.columns))
    if missing:
        raise ValueError(f"CE trades are missing required columns: {missing}")

    frame = trades.loc[
        trades["mode"].eq("qualifying")
        & trades["outcome_code"].isin([1, -1, 2])
        & trades["depth"].ge(0)
        & trades["depth"].lt(1)
    ].copy()
    if frame.empty:
        return pd.DataFrame()

    frame["win_cons"] = frame["outcome_code"].eq(1).astype(float)
    frame["depth_band"] = depth_band_labels(frame["depth"], band_width)
    timestamps = pd.DatetimeIndex(pd.to_datetime(frame["trigger_ts"], utc=True))
    frame["cme_trade_date"] = cme_cluster(timestamps).to_numpy()

    rows: list[dict[str, object]] = []
    grouped = frame.groupby(["timeframe", "depth_band"], observed=True, sort=False)
    for number, ((timeframe, band), cell) in enumerate(grouped, 1):
        if len(cell) < min_n:
            continue

        r_stats = _cluster_bootstrap_metric(
            cell,
            value_col="realized_R_conservative",
            cluster_col="cme_trade_date",
            n_boot=n_boot,
            seed=seed + number * 17,
        )
        win_stats = _cluster_bootstrap_metric(
            cell,
            value_col="win_cons",
            cluster_col="cme_trade_date",
            n_boot=n_boot,
            seed=seed + number * 17 + 1,
        )
        rows.append(
            {
                "timeframe": str(timeframe),
                "depth_band": str(band),
                "N": int(len(cell)),
                "trade_dates": int(cell["cme_trade_date"].nunique()),
                "win_rate": float(cell["win_cons"].mean()),
                "win_ci_low": win_stats["ci_low"],
                "win_ci_high": win_stats["ci_high"],
                "mean_R": float(cell["realized_R_conservative"].mean()),
                "mean_R_ci_low": r_stats["ci_low"],
                "mean_R_ci_high": r_stats["ci_high"],
                "p_mean_R_two_sided": r_stats["p_two_sided"],
            }
        )

    result = pd.DataFrame(rows)
    if len(result):
        result["q_mean_R_bh"] = benjamini_hochberg(result["p_mean_R_two_sided"])
        result = result.sort_values(["timeframe", "depth_band"], kind="stable").reset_index(drop=True)
    return result
