from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .catalog import TF_LABELS
from .runtime import ROOT, RESULTS, latest_success


def _fresh_file(path: Path, studies: tuple[str, ...]) -> bool:
    try:
        relative = str(path.relative_to(ROOT))
    except ValueError:
        return False
    return any(
        payload and relative in payload.get("generated_files", [])
        for payload in (latest_success(study) for study in studies)
    )


def _latest_generated(study: str, prefix: str) -> Path | None:
    payload = latest_success(study)
    if not payload:
        return None
    matches = [
        ROOT / value
        for value in payload.get("generated_files", [])
        if Path(value).name.startswith(prefix)
    ]
    return matches[-1] if matches else None


def verification_rows(exp_id: str, reference: dict) -> list[dict[str, object]]:
    rows: list[tuple[str, float, float, float]] = []
    try:
        if exp_id == "raw_fill":
            path = RESULTS / "detailed_1m" / "summary.json"
            if _fresh_file(path, ("detailed-1m",)):
                actual = json.loads(path.read_text(encoding="utf-8"))
                ref = reference["experiments"]["raw_fill"]
                rows += [
                    ("5m touch %", actual["raw_touch_5"] * 100, ref["touch_rate"][0] * 100, 0.35),
                    ("60m touch %", actual["raw_touch_60"] * 100, ref["touch_rate"][3] * 100, 0.35),
                    ("Eventual touch %", actual["eventual_touch_within_dataset"] * 100, ref["eventual_touch"] * 100, 0.35),
                ]

        elif exp_id == "matched_attraction":
            path = RESULTS / "detailed_1m" / "main_results.csv"
            if _fresh_file(path, ("detailed-1m",)):
                frame = pd.read_csv(path)
                refs = {"touch_5": 3.0275, "touch_60": 0.5770, "touch_1380": 0.0030}
                for test, expected in refs.items():
                    hit = frame.loc[frame["test"] == test]
                    if len(hit):
                        rows.append((f"{test} difference pp", float(hit.iloc[0]["Difference"]) * 100, expected, 0.50))
            else:
                path = _latest_generated("multi-tf", "magnet_tf")
                if path:
                    frame = pd.read_csv(path)
                    hit = frame.loc[frame["horizon_bars"] == 5]
                    if len(hit):
                        tf = int(hit.iloc[0]["timeframe_min"])
                        expected = next(x["difference_pp"] for x in reference["experiments"]["matched_attraction"]["multi_tf_5bar"] if x["timeframe"] == TF_LABELS[tf])
                        rows.append((f"{TF_LABELS[tf]} five-bar difference pp", float(hit.iloc[0]["Difference"]) * 100, expected, 0.75))

        elif exp_id == "age_decay":
            path = _latest_generated("multi-tf", "decay_tf")
            if path:
                frame = pd.read_csv(path)
                hit = frame[(frame["survived_through_bars"] == 1) & (frame["next_horizon_bars"] == 3)]
                if len(hit) and int(hit.iloc[0]["timeframe_min"]) == 1:
                    rows.append(("1→3 bar difference pp", float(hit.iloc[0]["Difference"]) * 100, 3.09, 0.75))

        elif exp_id == "continuation":
            path = _latest_generated("multi-tf", "formation_tf")
            if path:
                frame = pd.read_csv(path)
                hit = frame[frame["horizon_bars"] == 5]
                if len(hit):
                    tf = int(hit.iloc[0]["timeframe_min"])
                    expected = next(x["difference_atr"] for x in reference["experiments"]["continuation"]["five_bar"] if x["timeframe"] == TF_LABELS[tf])
                    rows.append((f"{TF_LABELS[tf]} five-bar difference ATR", float(hit.iloc[0]["Difference_ATR"]), expected, 0.03))

        elif exp_id == "retest":
            path = _latest_generated("multi-tf", "reaction_tf")
            if path:
                frame = pd.read_csv(path)
                hit = frame[frame["metric"] == "1gap_rejection_before_fullfill"]
                if len(hit):
                    tf = int(hit.iloc[0]["timeframe_min"])
                    expected = next(x["difference_pp"] for x in reference["experiments"]["retest"]["reaction"] if x["timeframe"] == TF_LABELS[tf])
                    rows.append((f"{TF_LABELS[tf]} reaction difference pp", float(hit.iloc[0]["Difference"]) * 100, expected, 1.25))

        elif exp_id == "midpoint":
            path = _latest_generated("midpoint", "midpoint_tf")
            if path and "year" not in path.name:
                frame = pd.read_csv(path)
                if len(frame):
                    tf = int(frame.iloc[0]["timeframe_min"])
                    expected = next(x["difference_pp"] for x in reference["experiments"]["midpoint"]["reaction"] if x["timeframe"] == TF_LABELS[tf])
                    rows.append((f"{TF_LABELS[tf]} midpoint difference pp", float(frame.iloc[0]["Difference"]) * 100, expected, 1.25))

        elif exp_id == "body_acceptance":
            path = RESULTS / "ce_body" / "body_depth_5pct.csv"
            if _fresh_file(path, ("ce-body",)):
                frame = pd.read_csv(path)
                hit = frame[(frame["timeframe"] == "4H") & (frame["depth_band"] == "45-50%")]
                if len(hit):
                    rows.append(("4H 45-50% win rate %", float(hit.iloc[0]["win_rate"]) * 100, 67.35, 1.50))
                    rows.append(("4H 45-50% mean R", float(hit.iloc[0]["mean_R_conservative"]), 0.286, 0.08))

        elif exp_id == "controls_regimes":
            path = RESULTS / "detailed_1m" / "logistic_60m.json"
            if _fresh_file(path, ("detailed-1m",)):
                actual = json.loads(path.read_text(encoding="utf-8"))
                rows.append(("FVG odds ratio", float(actual["fvg_odds_ratio"]), 1.0789, 0.03))

        elif exp_id == "oos":
            path = RESULTS / "detailed_1m" / "train_test.csv"
            if _fresh_file(path, ("detailed-1m",)):
                frame = pd.read_csv(path)
                early = frame[frame["split"] == "train"]
                late = frame[frame["split"] == "test"]
                if len(early):
                    rows.append(("Deep 1m early difference pp", float(early.iloc[0]["Difference"]) * 100, 0.79, 0.35))
                if len(late):
                    rows.append(("Deep 1m later difference pp", float(late.iloc[0]["Difference"]) * 100, 0.08, 0.35))
            else:
                path = _latest_generated("multi-tf", "oos_tf")
                if path:
                    frame = pd.read_csv(path)
                    tf = int(frame.iloc[0]["timeframe_min"])
                    ref = next(x for x in reference["experiments"]["oos"]["five_bar"] if x["timeframe"] == TF_LABELS[tf])
                    for split, key in (("train", "train_pp"), ("test", "test_pp")):
                        hit = frame.loc[frame["split"] == split]
                        if len(hit):
                            rows.append((f"{TF_LABELS[tf]} {split} difference pp", float(hit.iloc[0]["Difference"]) * 100, ref[key], 1.0))
    except Exception:
        return []

    output: list[dict[str, object]] = []
    for name, actual, expected, tolerance in rows:
        delta = actual - expected
        output.append({
            "Metric": name,
            "Local run": round(actual, 5),
            "Published reference": round(expected, 5),
            "Delta": round(delta, 5),
            "Tolerance": tolerance,
            "Status": "MATCH" if abs(delta) <= tolerance else "CHECK",
        })
    return output
