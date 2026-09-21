from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .public_nsx import PUBLIC_RESULTS, public_audit, public_manifest

PUBLIC_TFS = (1, 5, 15, 60, 240)


def _csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.is_file() else pd.DataFrame()


def _json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    clean = frame.where(pd.notna(frame), None)
    return clean.to_dict(orient="records")


def _has_real_output(value: Any) -> bool:
    """Return True only when a nested result payload contains an actual value/record."""
    if isinstance(value, dict):
        return any(_has_real_output(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return bool(value) and any(_has_real_output(item) for item in value)
    return value is not None and value != ""


def build_public_summary(results_root: str | Path = PUBLIC_RESULTS) -> dict[str, Any]:
    root = Path(results_root)
    detailed = root / "detailed_1m"
    multi = root / "multi_tf"
    midpoint = root / "midpoint"
    ce = root / "ce_body"

    result: dict[str, Any] = {
        "status": "public_replication",
        "dataset": public_manifest(),
        "audit": public_audit(),
        "experiments": {},
    }

    detailed_summary = _json(detailed / "summary.json")
    main_results = _csv(detailed / "main_results.csv")
    result["experiments"]["raw_fill"] = {
        "summary": detailed_summary,
        "horizons": _records(main_results),
    }

    multi_rows: dict[str, Any] = {}
    for tf in PUBLIC_TFS:
        multi_rows[str(tf)] = {
            "magnet": _records(_csv(multi / f"magnet_tf{tf}.csv")),
            "decay": _records(_csv(multi / f"decay_tf{tf}.csv")),
            "formation": _records(_csv(multi / f"formation_tf{tf}.csv")),
            "reaction": _records(_csv(multi / f"reaction_tf{tf}.csv")),
            "oos": _records(_csv(multi / f"oos_tf{tf}.csv")),
            "counts": _records(_csv(multi / f"counts_tf{tf}.csv")),
        }

    result["experiments"]["matched_attraction"] = {
        tf: payload["magnet"] for tf, payload in multi_rows.items()
    }
    result["experiments"]["age_decay"] = {
        tf: payload["decay"] for tf, payload in multi_rows.items()
    }
    result["experiments"]["continuation"] = {
        tf: payload["formation"] for tf, payload in multi_rows.items()
    }
    result["experiments"]["retest"] = {
        tf: payload["reaction"] for tf, payload in multi_rows.items()
    }
    result["experiments"]["oos"] = {
        "deep_1m": _records(_csv(detailed / "train_test.csv")),
        "multi_timeframe": {tf: payload["oos"] for tf, payload in multi_rows.items()},
    }
    result["experiments"]["controls_regimes"] = {
        "main": _records(main_results),
        "distance": _records(_csv(detailed / "strat_distance.csv")),
        "session": _records(_csv(detailed / "strat_session.csv")),
        "year": _records(_csv(detailed / "strat_year.csv")),
        "logistic_60m": _json(detailed / "logistic_60m.json"),
    }

    result["experiments"]["midpoint"] = {
        str(tf): _records(_csv(midpoint / f"midpoint_tf{tf}.csv"))
        for tf in PUBLIC_TFS
    }
    result["experiments"]["body_acceptance"] = {
        "summary": _json(ce / "summary.json"),
        "body_depth_5pct": _records(_csv(ce / "body_depth_5pct.csv")),
        "summary_by_timeframe": _records(_csv(ce / "summary_by_timeframe.csv")),
        "midpoint_slices": _records(_csv(ce / "midpoint_slices.csv")),
        "ce_train_test": _records(_csv(ce / "ce_train_test.csv")),
    }

    present = 0
    total = 9
    for payload in result["experiments"].values():
        if _has_real_output(payload):
            present += 1
    result["experiment_families_with_outputs"] = present
    result["experiment_families_total"] = total
    return result


def write_public_summary(
    output: str | Path,
    results_root: str | Path = PUBLIC_RESULTS,
) -> Path:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build_public_summary(results_root)
    output.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return output
