from __future__ import annotations

from pathlib import Path

import pandas as pd


def reference_atlas(reference: dict) -> dict[str, pd.DataFrame]:
    matched = pd.DataFrame(reference["experiments"]["matched_attraction"]["multi_tf_5bar"]).copy()
    matched = matched.rename(columns={"timeframe": "Timeframe", "difference_pp": "Difference (pp)"})
    matched["Horizon"] = "5 native bars"

    oos = pd.DataFrame(reference["experiments"]["oos"]["five_bar"]).copy()
    early = oos[["timeframe", "train_pp"]].rename(columns={"timeframe": "Timeframe", "train_pp": "Difference (pp)"})
    early["Period"] = "Early 70%"
    late = oos[["timeframe", "test_pp"]].rename(columns={"timeframe": "Timeframe", "test_pp": "Difference (pp)"})
    late["Period"] = "Later 30%"
    chronology = pd.concat([early, late], ignore_index=True)

    distance = pd.DataFrame(reference["experiments"]["controls_regimes"]["distance"]).copy()
    distance = distance.rename(columns={"bucket": "Distance bucket", "difference_pp": "Difference (pp)"})
    return {
        "timeframe": matched,
        "chronology": chronology,
        "distance": distance,
    }


def local_atlas(results_root: str | Path) -> dict[str, pd.DataFrame]:
    root = Path(results_root)
    output: dict[str, pd.DataFrame] = {}

    multi = root / "multi_tf"
    magnet_files = sorted(multi.glob("magnet_tf*.csv"))
    frames = []
    for path in magnet_files:
        try:
            frame = pd.read_csv(path)
        except Exception:
            continue
        if "Difference" in frame:
            frame["Difference (pp)"] = frame["Difference"] * 100
        frames.append(frame)
    if frames:
        output["timeframe_horizon"] = pd.concat(frames, ignore_index=True)

    detailed = root / "detailed_1m"
    for key, pattern in (
        ("year", "strat_year.csv"),
        ("distance", "strat_distance.csv"),
        ("volatility", "strat_vol*.csv"),
        ("sensitivity", "sensitivity.csv"),
    ):
        matches = sorted(detailed.glob(pattern))
        if not matches:
            continue
        try:
            frame = pd.read_csv(matches[-1])
            if "Difference" in frame:
                frame["Difference (pp)"] = frame["Difference"] * 100
            output[key] = frame
        except Exception:
            continue
    return output
