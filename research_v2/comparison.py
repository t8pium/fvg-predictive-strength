from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _load(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def build_v1_v2_comparison(reference: dict, output_dir: str | Path) -> pd.DataFrame:
    out = Path(output_dir)
    rows: list[dict[str, object]] = []

    attraction = _load(out / "corrected_attraction_1m.json")
    if attraction:
        v2 = attraction.get("result", {}).get("difference_pp")
        v1_row = next(row for row in reference["experiments"]["matched_attraction"]["deep_1m"] if row["horizon"] == "60m")
        rows.append({
            "Question": "1m attraction at 60m",
            "Published v1": float(v1_row["difference_pp"]),
            "Corrected v2": float(v2),
            "Change": float(v2) - float(v1_row["difference_pp"]),
            "Correction": "symmetric horizon eligibility + contract-boundary censoring + parent-paired controls + CME-day clustering",
        })

    age = _load(out / "corrected_age_decay_1m.json")
    if age:
        v1 = {row["window"]: row["difference_pp"] for row in reference["experiments"]["age_decay"]["one_minute"]}
        for row in age.get("windows", []):
            window = str(row.get("window"))
            if window in v1 and row.get("difference_pp") is not None:
                rows.append({
                    "Question": f"Age decay {window}",
                    "Published v1": float(v1[window]),
                    "Corrected v2": float(row["difference_pp"]),
                    "Change": float(row["difference_pp"]) - float(v1[window]),
                    "Correction": "parent-paired conditional controls + symmetric eligibility + CME-day clustering",
                })

    ce = _load(out / "ce_reinference.json")
    if ce:
        for row in ce.get("cells", []):
            if str(row.get("timeframe")) == "4H" and str(row.get("depth_band")) == "45-50%":
                v1_band = next(
                    item
                    for item in reference["experiments"]["body_acceptance"]["four_hour_bands"]
                    if str(item["band"]) == "45–50%"
                )
                v1_mean_r = float(v1_band["mean_R"])
                rows.append({
                    "Question": "4H CE body close 45–50%",
                    "Published v1": v1_mean_r,
                    "Corrected v2": float(row["mean_R"]),
                    "Change": float(row["mean_R"]) - v1_mean_r,
                    "Correction": f"same point estimate; CME-day clustered CI + FDR q={float(row['q_mean_R_bh']):.4f}",
                })
                break

    return pd.DataFrame(rows)
