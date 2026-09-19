from __future__ import annotations

EXPERIMENT_PROVENANCE = {
    "raw_fill": {
        "suite": "detailed-1m",
        "population": "454,197 detected 1m FVGs in the published active-contract sample",
        "controls": "None — descriptive baseline",
        "seed": "Not required for the full raw-event baseline",
        "outputs": ["summary.json", "main_results.csv", "fvg_events.csv"],
        "input": "Active MNQ 1m bars, 2020-01-01 through 2026-07-10",
    },
    "matched_attraction": {
        "suite": "detailed-1m + multi-tf",
        "population": "Deep 1m: up to 40,000 FVG parents; multi-TF: up to 12,000 per timeframe",
        "controls": "Deep 1m: up to 5 matched zones per FVG; multi-TF: 3 per FVG",
        "seed": "42 (deep 1m); 260918 (multi-timeframe family)",
        "outputs": ["main_results.csv", "magnet_tf*.csv"],
        "input": "Active MNQ bars; 1m deep study plus 1m/5m/15m/1H/4H native bars",
    },
    "age_decay": {
        "suite": "multi-tf",
        "population": "Up to 12,000 sampled FVG parents per timeframe",
        "controls": "3 matched ordinary zones per FVG where candidate availability permits",
        "seed": "260918",
        "outputs": ["decay_tf*.csv"],
        "input": "Active MNQ bars resampled to the requested native timeframe",
    },
    "continuation": {
        "suite": "multi-tf",
        "population": "Up to 8,000 FVG-forming moves per timeframe",
        "controls": "One state/move-matched non-FVG displacement",
        "seed": "260918",
        "outputs": ["formation_tf*.csv"],
        "input": "Active MNQ bars resampled to the requested native timeframe",
    },
    "retest": {
        "suite": "multi-tf",
        "population": "Up to 12,000 sampled FVG parents per timeframe before touch eligibility",
        "controls": "3 matched ordinary zones per FVG where available",
        "seed": "260918",
        "outputs": ["reaction_tf*.csv"],
        "input": "Active MNQ bars resampled to the requested native timeframe",
    },
    "midpoint": {
        "suite": "midpoint",
        "population": "Up to 12,000 eligible FVGs per timeframe",
        "controls": "3 state-matched zones per FVG where available",
        "seed": "9917",
        "outputs": ["midpoint_tf*.csv", "midpoint_year_tf*.csv"],
        "input": "Active MNQ bars resampled to 1m/5m/15m/1H/4H",
    },
    "body_acceptance": {
        "suite": "ce-body",
        "population": "All qualifying opposite-color signal candles under the canonical CE rules",
        "controls": "No matched-zone placebo; trade-like TP/SL race is resolved on future 1m bars",
        "seed": "20260918 for bootstrap inference",
        "outputs": ["trades*.pkl", "body_depth_5pct.csv"],
        "input": "Active MNQ 1m bars, aggregated from 1m through 1D for signal formation",
    },
    "controls_regimes": {
        "suite": "detailed-1m",
        "population": "Deep 1m matched sample, up to 40,000 FVG parents",
        "controls": "Up to 5 matched ordinary zones per FVG",
        "seed": "42",
        "outputs": ["main_results.csv", "logistic_60m.json", "regime/distance tables"],
        "input": "Active MNQ 1m bars with ATR, volatility, trend, direction and time-of-day features",
    },
    "oos": {
        "suite": "detailed-1m + multi-tf",
        "population": "Chronologically ordered matched parent events",
        "controls": "Same matched controls as the source attraction studies",
        "seed": "42 (deep 1m); 260918 (multi-timeframe family)",
        "outputs": ["train_test.csv", "oos_tf*.csv", "year stability tables"],
        "input": "Early 70% versus later 30% of the matched-event chronology",
    },
}


def provenance_for(exp_id: str) -> dict[str, object]:
    return EXPERIMENT_PROVENANCE[exp_id]
