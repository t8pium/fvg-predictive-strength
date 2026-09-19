from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_FIELDS = {
    "hypothesis_id",
    "title",
    "question",
    "dataset_window",
    "primary_outcome",
    "timeframe",
    "filters",
    "horizon",
    "expected_direction",
    "statistic",
    "correction_family",
}


def validate_hypothesis(payload: dict[str, object]) -> None:
    missing = sorted(REQUIRED_FIELDS - set(payload))
    if missing:
        raise ValueError(f"Missing hypothesis fields: {missing}")
    if not str(payload["hypothesis_id"]).strip():
        raise ValueError("hypothesis_id cannot be empty")
    if str(payload["expected_direction"]) not in {"positive", "negative", "two-sided", "none"}:
        raise ValueError("expected_direction must be positive, negative, two-sided, or none")


def canonical_payload(payload: dict[str, object]) -> dict[str, object]:
    validate_hypothesis(payload)
    excluded = {"lock_hash", "registered_utc", "status", "result_reference"}
    return {key: payload[key] for key in sorted(payload) if key not in excluded}


def hypothesis_hash(payload: dict[str, object]) -> str:
    body = json.dumps(canonical_payload(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def register_hypothesis(path: str | Path, payload: dict[str, object]) -> dict[str, object]:
    validate_hypothesis(payload)
    locked = dict(payload)
    locked["registered_utc"] = datetime.now(timezone.utc).isoformat()
    locked["status"] = "preregistered"
    locked["lock_hash"] = hypothesis_hash(locked)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(locked, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return locked


def verify_hypothesis(payload_or_path: dict[str, object] | str | Path) -> bool:
    if isinstance(payload_or_path, dict):
        payload = payload_or_path
    else:
        payload = json.loads(Path(payload_or_path).read_text(encoding="utf-8"))
    expected = payload.get("lock_hash")
    return isinstance(expected, str) and expected == hypothesis_hash(payload)
