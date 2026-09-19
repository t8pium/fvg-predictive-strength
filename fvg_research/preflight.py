from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

import pandas as pd

from .io import DATA_SUFFIXES, supported_file

MNQ_OUTRIGHT_RE = re.compile(r"\bMNQ[HMUZ](?:\d{1,2}|\d{4})\b", re.IGNORECASE)
ISO_DATE_RE = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")

SUPPORTED_LABELS = {
    ".zip": "ZIP archive",
    ".dbn": "Databento DBN",
    ".dbn.zst": "Compressed Databento DBN",
    ".parquet": "Parquet",
    ".pq": "Parquet",
    ".csv": "CSV",
    ".csv.gz": "Compressed CSV",
    ".csv.zst": "Compressed CSV",
}


def _kind(path: Path) -> str:
    lower = path.name.lower()
    for suffix, label in sorted(SUPPORTED_LABELS.items(), key=lambda item: len(item[0]), reverse=True):
        if lower.endswith(suffix):
            return label
    return "Unsupported"


def _zip_inventory(path: Path) -> dict[str, object]:
    detected_symbols: set[str] = set()
    detected_dates: set[str] = set()
    with zipfile.ZipFile(path, "r") as archive:
        members = [member for member in archive.infolist() if not member.is_dir()]
        data_members = [
            member for member in members
            if Path(member.filename).name.lower().endswith(DATA_SUFFIXES)
        ]
        sidecars = [member for member in members if member.filename.lower().endswith(".json")]
        expanded = sum(member.file_size for member in members)
        compressed = sum(member.compress_size for member in members)

        # Sidecars are small and often contain resolved symbol mappings/date metadata.
        # Reading them is much cheaper than decoding the multi-GB market-data payload.
        for sidecar in sidecars[:50]:
            if sidecar.file_size > 20 * 1024**2:
                continue
            try:
                text = archive.read(sidecar).decode("utf-8", errors="ignore")
            except Exception:
                continue
            detected_symbols.update(match.upper() for match in MNQ_OUTRIGHT_RE.findall(text))
            detected_dates.update(ISO_DATE_RE.findall(text))

    result = {
        "members": len(members),
        "market_data_members": len(data_members),
        "symbology_sidecars": len(sidecars),
        "expanded_bytes": int(expanded),
        "compressed_bytes": int(compressed),
        "data_member_names": [Path(member.filename).name for member in data_members[:20]],
    }
    if detected_symbols:
        result["detected_mnq_quarterly_symbols"] = sorted(detected_symbols)
        result["detected_mnq_contracts"] = len(detected_symbols)
    if detected_dates:
        dates = sorted(detected_dates)
        result["metadata_date_min"] = dates[0]
        result["metadata_date_max"] = dates[-1]
    return result


def _dbn_metadata(path: Path) -> dict[str, object]:
    try:
        import databento as db

        store = db.DBNStore.from_file(path)
        metadata = getattr(store, "metadata", None)
        if metadata is None:
            return {}
        result: dict[str, object] = {}
        for attribute in ("dataset", "schema", "stype_in", "stype_out", "start", "end", "limit"):
            value = getattr(metadata, attribute, None)
            if value is not None:
                result[f"dbn_{attribute}"] = str(value)
        symbols = getattr(metadata, "symbols", None)
        if symbols:
            symbol_values = [str(value) for value in symbols]
            result["dbn_symbols"] = symbol_values[:100]
            mnq = sorted({value.upper() for value in symbol_values if MNQ_OUTRIGHT_RE.fullmatch(value.strip())})
            if mnq:
                result["detected_mnq_quarterly_symbols"] = mnq
                result["detected_mnq_contracts"] = len(mnq)
        return result
    except Exception as exc:
        return {"dbn_metadata_warning": str(exc)}


def _tabular_sample(path: Path, rows: int = 5000) -> dict[str, object]:
    lower = path.name.lower()
    if lower.endswith((".csv", ".csv.gz", ".csv.zst")):
        frame = pd.read_csv(path, nrows=rows)
        return {
            "sample_rows": int(len(frame)),
            "columns": [str(column) for column in frame.columns],
        }
    if lower.endswith((".parquet", ".pq")):
        import pyarrow.parquet as pq

        parquet = pq.ParquetFile(path)
        metadata = parquet.metadata
        schema_names = list(parquet.schema.names)
        return {
            "declared_rows": int(metadata.num_rows),
            "row_groups": int(metadata.num_row_groups),
            "columns": schema_names,
        }
    return {}


def inspect_source(path: str | Path) -> dict[str, object]:
    source = Path(path).expanduser().resolve()
    result: dict[str, object] = {
        "path": str(source),
        "exists": source.exists(),
        "kind": _kind(source),
        "supported": supported_file(source) if source.is_file() else source.is_dir(),
    }
    if not source.exists():
        return result

    if source.is_dir():
        children = sorted(item for item in source.iterdir() if item.is_file() and supported_file(item))
        result.update(
            {
                "kind": "Directory",
                "files": len(children),
                "supported_files": [item.name for item in children[:50]],
                "bytes": int(sum(item.stat().st_size for item in children)),
            }
        )
        return result

    result["bytes"] = int(source.stat().st_size)
    lower = source.name.lower()
    if lower.endswith(".zip"):
        try:
            result.update(_zip_inventory(source))
            result["status"] = "PASS" if result.get("market_data_members", 0) else "CHECK"
        except (OSError, zipfile.BadZipFile) as exc:
            result["status"] = "FAIL"
            result["error"] = str(exc)
        return result

    if lower.endswith((".dbn", ".dbn.zst")):
        result.update(_dbn_metadata(source))
        result["status"] = "PASS" if result["supported"] else "FAIL"
        return result

    try:
        result.update(_tabular_sample(source))
        columns = {column.lower() for column in result.get("columns", [])}
        required = {"open", "high", "low", "close", "volume"}
        if columns:
            result["ohlcv_columns_present"] = sorted(required.intersection(columns))
            result["status"] = "PASS" if required.issubset(columns) else "CHECK"
        else:
            result["status"] = "PASS" if result["supported"] else "FAIL"
    except Exception as exc:
        result["status"] = "CHECK"
        result["sample_warning"] = str(exc)
    return result


def inspect_sources(paths: list[str | Path]) -> list[dict[str, object]]:
    return [inspect_source(path) for path in paths]
