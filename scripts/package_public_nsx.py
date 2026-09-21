from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fvg_research.histdata_nsx import prepare_histdata_nsx
from fvg_research.public_nsx import package_inventory


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(8 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit/prepare NSXUSD_M1_ALL.csv and build a candidate dataset ZIP. "
            "Do not publish the archive unless redistribution permission is confirmed."
        )
    )
    parser.add_argument("--input", required=True, help="Path to NSXUSD_M1_ALL.csv")
    parser.add_argument("--output", default=str(ROOT / "dist" / "public_nsx"))
    parser.add_argument("--chunksize", type=int, default=500_000)
    args = parser.parse_args(argv)

    out = Path(args.output).expanduser().resolve()
    prepared = out / "prepared"
    out.mkdir(parents=True, exist_ok=True)
    if prepared.exists():
        shutil.rmtree(prepared)
    prepared.mkdir(parents=True)

    result = prepare_histdata_nsx(args.input, prepared, chunksize=args.chunksize)

    # The release package contains Parquet + metadata. The pickle is rebuilt locally
    # after install to avoid distributing two full copies of the same 5M-row dataset.
    pickle = prepared / "active_nsxusd.pkl"
    pickle.unlink(missing_ok=True)

    inventory = package_inventory(prepared)
    release_manifest = {
        "format_version": 1,
        "asset_name": "NSXUSD_M1_PUBLIC.zip",
        "dataset_id": "histdata_nsxusd_m1",
        "dataset_kind": "public_nasdaq_100_index_proxy",
        "source": "HistData NSX/USD Generic ASCII M1",
        "rows": result["rows"],
        "start_utc": result["start_utc"],
        "end_utc": result["end_utc"],
        "files": inventory,
        "research_warning": (
            "NSX/USD is an index-style quote feed, not CME NQ/MNQ futures; "
            "volume and futures roll/execution claims are out of scope."
        ),
    }
    (prepared / "PUBLIC_DATA_MANIFEST.json").write_text(
        json.dumps(release_manifest, indent=2), encoding="utf-8"
    )

    archive = out / "NSXUSD_M1_PUBLIC.zip"
    archive.unlink(missing_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(prepared.iterdir()):
            if path.is_file():
                zf.write(path, arcname=path.name)

    digest = _sha256(archive)
    (out / "NSXUSD_M1_PUBLIC.sha256").write_text(
        f"{digest}  {archive.name}\n", encoding="utf-8"
    )
    print(json.dumps({
        "archive": str(archive),
        "bytes": archive.stat().st_size,
        "sha256": digest,
        "rows": result["rows"],
        "start_utc": result["start_utc"],
        "end_utc": result["end_utc"],
    }, indent=2))
    print()
    print("Candidate archive built. Do NOT publish it unless the source terms or explicit permission allow redistribution.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
