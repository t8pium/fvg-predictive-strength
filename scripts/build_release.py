from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from app.catalog import EXPERIMENTS
from app.provenance import EXPERIMENT_PROVENANCE
from fvg_research.report import write_report

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
EXCLUDE_TOP = {".git", ".fvg_venv", "data", "results", "dist", "__pycache__"}
EXCLUDE_PARTS = {".pytest_cache", ".mypy_cache", "__pycache__"}


def include(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if relative.parts and relative.parts[0] in EXCLUDE_TOP:
        return False
    if any(part in EXCLUDE_PARTS for part in relative.parts):
        return False
    if path.suffix in {".pyc", ".pyo"}:
        return False
    return True


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a GitHub Release bundle for the FVG Research Platform.")
    parser.add_argument("--version", default=(ROOT / "VERSION").read_text(encoding="utf-8").strip())
    args = parser.parse_args(argv)

    version = args.version.lstrip("v")
    DIST.mkdir(parents=True, exist_ok=True)
    archive = DIST / f"fvg-predictive-strength-v{version}.zip"
    report = DIST / f"fvg-predictive-strength-v{version}-report.html"

    write_report(
        report,
        ROOT / "reference_results" / "reference_metrics.json",
        EXPERIMENTS,
        EXPERIMENT_PROVENANCE,
        ROOT,
    )

    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(ROOT.rglob("*")):
            if not path.is_file() or not include(path):
                continue
            zf.write(path, path.relative_to(ROOT.parent))

    checksums = {
        archive.name: sha256(archive),
        report.name: sha256(report),
    }
    checksum_path = DIST / "SHA256SUMS.json"
    checksum_path.write_text(json.dumps(checksums, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(checksums, indent=2))
    print(f"Built {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
