from __future__ import annotations

import numpy as np
import pandas as pd

MNQ_POINT_VALUE = 2.0
MNQ_TICK_SIZE = 0.25
MNQ_TICK_VALUE = 0.50


def apply_trade_costs(
    trades: pd.DataFrame,
    *,
    commission_round_turn_usd: float = 1.24,
    slippage_ticks_round_turn: float = 2.0,
    tick_value_usd: float = MNQ_TICK_VALUE,
    point_value_usd: float = MNQ_POINT_VALUE,
) -> pd.DataFrame:
    """Translate canonical trade-like CE outcomes into gross/net economic terms."""
    required = {"risk_pts", "realized_R_conservative"}
    missing = sorted(required - set(trades.columns))
    if missing:
        raise ValueError(f"Trade table missing required columns: {missing}")
    if commission_round_turn_usd < 0 or slippage_ticks_round_turn < 0:
        raise ValueError("cost assumptions cannot be negative")

    frame = trades.dropna(subset=["risk_pts", "realized_R_conservative"]).copy()
    frame = frame.loc[frame["risk_pts"].gt(0)].copy()
    frame["risk_usd"] = frame["risk_pts"] * point_value_usd
    frame["gross_pnl_usd"] = frame["realized_R_conservative"] * frame["risk_usd"]
    frame["estimated_cost_usd"] = commission_round_turn_usd + slippage_ticks_round_turn * tick_value_usd
    frame["net_pnl_usd"] = frame["gross_pnl_usd"] - frame["estimated_cost_usd"]
    frame["net_R"] = frame["net_pnl_usd"] / frame["risk_usd"]
    return frame


def economic_summary(
    trades: pd.DataFrame,
    *,
    commission_round_turn_usd: float = 1.24,
    slippage_ticks_round_turn: float = 2.0,
) -> dict[str, float | int]:
    frame = apply_trade_costs(
        trades,
        commission_round_turn_usd=commission_round_turn_usd,
        slippage_ticks_round_turn=slippage_ticks_round_turn,
    )
    if frame.empty:
        return {
            "N": 0,
            "gross_mean_R": np.nan,
            "net_mean_R": np.nan,
            "gross_total_usd": 0.0,
            "net_total_usd": 0.0,
            "cost_total_usd": 0.0,
            "net_positive_fraction": np.nan,
        }
    return {
        "N": int(len(frame)),
        "gross_mean_R": float(frame["realized_R_conservative"].mean()),
        "net_mean_R": float(frame["net_R"].mean()),
        "gross_total_usd": float(frame["gross_pnl_usd"].sum()),
        "net_total_usd": float(frame["net_pnl_usd"].sum()),
        "cost_total_usd": float(frame["estimated_cost_usd"].sum()),
        "net_positive_fraction": float((frame["net_pnl_usd"] > 0).mean()),
    }


def scenario_table(
    trades: pd.DataFrame,
    *,
    commissions: tuple[float, ...] = (0.80, 1.24, 2.00),
    slippage_ticks: tuple[float, ...] = (0.0, 1.0, 2.0, 4.0),
) -> pd.DataFrame:
    rows = []
    for commission in commissions:
        for slip in slippage_ticks:
            summary = economic_summary(
                trades,
                commission_round_turn_usd=commission,
                slippage_ticks_round_turn=slip,
            )
            rows.append({
                "Commission RT ($)": commission,
                "Slippage RT (ticks)": slip,
                "N": summary["N"],
                "Gross mean R": summary["gross_mean_R"],
                "Net mean R": summary["net_mean_R"],
                "Net total PnL ($/1 contract)": summary["net_total_usd"],
            })
    return pd.DataFrame(rows)
