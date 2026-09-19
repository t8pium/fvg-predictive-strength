from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd

from .io import DATA_SUFFIXES, supported_file

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
    with zipfile.ZipFile(path, "r") as archive:
        members = [member for member in archive.infolist() if not member.is_dir()]
        data_members = [
            member for member in members
            if Path(member.filename).name.lower().endswith(DATA_SUFFIXES)
        ]
        sidecars = [member for member in members if member.filename.lower().endswith(".json")]
        expanded = sum(member.file_size for member in members)
        compressed = sum(member.compress_size for member in members)
    return {
        "members": len(members),
        "market_data_members": len(data_members),
        "symbology_sidecars": len(sidecars),
        "expanded_bytes": int(expanded),
        "compressed_bytes": int(compressed),
        "data_member_names": [Path(member.filename).name for member in data_members[:20]],
    }


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
