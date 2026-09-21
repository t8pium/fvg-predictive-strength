from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fvg_research.dataset import current_pickle
from fvg_research.run_record import write_run_record

ORIGINAL = ROOT / "src" / "original"
RESULTS = ROOT / "results"
RUNS = RESULTS / "_runs"

SCRIPTS = {
    "detailed-1m": "fvg_final_fast.py",
    "multi-tf": "fvg_strength_one_tf.py",
    "midpoint": "fvg_midpoint_reaction.py",
    "ce-body": "fvg_ce_rejection_study.py",
}
SOURCE_HASHES = {
    "fvg_ce_rejection_study.py": "bd9714711a61493a9a1e207364d2b7e59d7eb5b9306526e36e2fc0e645187d41",
    "fvg_final_fast.py": "f1f896c70d222cdae6eeda3e22cf24c9778b183922a96ef454528a84de6adef0",
    "fvg_midpoint_reaction.py": "9ce25efc05b6ecb13c29102c6b50abf825a0b23d2b363d69acc346f82db1036e",
    "fvg_strength_one_tf.py": "45dd13a28bcebabaaf49320d53f2bcac2c9c816761a9cdfeba2b792bc92e752c",
}
VALID_TFS = {1, 2, 3, 5, 10, 15, 30, 60, 120, 240, 360, 480, 720, 1440}


def normalized_source(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def canonical_source_digest(text: str) -> str:
    return hashlib.sha256(normalized_source(text).encode("utf-8")).hexdigest()


class PathRewriter(ast.NodeTransformer):
    def __init__(self, data_path: Path, results_root: Path = RESULTS) -> None:
        self.data_path = data_path
        self.results_root = results_root
        self.replacements = 0

    def visit_Constant(self, node: ast.Constant):
        if not isinstance(node.value, str):
            return node
        legacy = "/mnt" + "/data"
        replacements = {
            legacy + "/active_mnq.pkl": str(self.data_path),
            legacy + "/fvg_study_outputs": str(self.results_root / "detailed_1m"),
            legacy + "/fvg_strength_project_single": str(self.results_root / "multi_tf"),
            legacy + "/fvg_ce_study": str(self.results_root / "ce_body"),
            legacy + "/midpoint_year_tf": str(self.results_root / "midpoint" / "midpoint_year_tf"),
            legacy + "/midpoint_tf": str(self.results_root / "midpoint" / "midpoint_tf"),
        }
        value = node.value
        for old, new in replacements.items():
            if value.startswith(old):
                self.replacements += 1
                return ast.copy_location(ast.Constant(new + value[len(old):]), node)
        return node


def patch_source(
    text: str,
    name: str,
    data_path: Path | None = None,
    results_root: Path | None = None,
) -> str:
    data_path = data_path or current_pickle()
    results_root = results_root or RESULTS
    tree = ast.parse(text, filename=name)
    rewriter = PathRewriter(data_path, results_root)
    tree = rewriter.visit(tree)
    ast.fix_missing_locations(tree)
    legacy = "/mnt" + "/data"
    remaining = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and legacy in node.value
    ]
    if remaining:
        raise ValueError(f"Unpatched canonical path(s) in {name}: {remaining}")
    if rewriter.replacements < 2:
        raise ValueError(f"Expected at least two canonical path constants in {name}; found {rewriter.replacements}")
    return ast.unparse(tree) + "\n"


def snapshot_outputs(results_root: Path, runs: Path) -> dict[str, int]:
    if not results_root.exists():
        return {}
    return {
        str(path.relative_to(ROOT)): path.stat().st_mtime_ns
        for path in results_root.rglob("*")
        if path.is_file() and runs not in path.parents
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a canonical analysis script with portable local paths.")
    parser.add_argument("study", choices=SCRIPTS)
    parser.add_argument("--tf", type=int, help="Native timeframe for multi-tf or midpoint")
    parser.add_argument("--ce-tfs", help="Comma-separated CE timeframes in minutes")
    parser.add_argument(
        "--data",
        help=(
            "Optional schema-compatible pickle instead of the active MNQ generation. "
            "Use this for external discovery datasets such as prepared HistData NSX/USD."
        ),
    )
    parser.add_argument(
        "--results-root",
        help=(
            "Optional result directory under this repository. When --data is supplied and "
            "this is omitted, results are isolated under results/external/<dataset-stem>."
        ),
    )
    return parser.parse_args(argv)


def validate_args(args: argparse.Namespace) -> list[int]:
    if args.study in {"multi-tf", "midpoint"} and args.tf is None:
        raise ValueError(f"{args.study} requires --tf")
    if args.tf is not None and (args.study not in {"multi-tf", "midpoint"} or args.tf not in VALID_TFS):
        raise ValueError("--tf is only valid for multi-tf/midpoint and must be a supported minute value")
    if args.ce_tfs and args.study != "ce-body":
        raise ValueError("--ce-tfs is only valid for ce-body")
    values = [int(x.strip()) for x in args.ce_tfs.split(",") if x.strip()] if args.ce_tfs else sorted(VALID_TFS)
    if args.study == "ce-body" and (not values or len(values) != len(set(values)) or any(x not in VALID_TFS for x in values)):
        raise ValueError("--ce-tfs must contain unique supported minute values")
    return values


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        ce_values = validate_args(args)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    data = Path(args.data).expanduser().resolve() if args.data else current_pickle()
    if not data.is_file():
        if args.data:
            print(f"ERROR: External dataset pickle not found: {data}", file=sys.stderr)
        else:
            print("ERROR: No active MNQ dataset is prepared. Use Data Setup first.", file=sys.stderr)
        return 2

    if args.results_root:
        results_root = Path(args.results_root).expanduser()
        if not results_root.is_absolute():
            results_root = ROOT / results_root
        results_root = results_root.resolve()
    elif args.data:
        safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in data.stem)
        results_root = (RESULTS / "external" / safe_name).resolve()
    else:
        results_root = RESULTS.resolve()

    try:
        results_root.relative_to(ROOT.resolve())
    except ValueError:
        print("ERROR: --results-root must remain inside the repository.", file=sys.stderr)
        return 2

    runs = results_root / "_runs"
    results_root.mkdir(parents=True, exist_ok=True)
    runs.mkdir(parents=True, exist_ok=True)
    for folder in ("detailed_1m", "multi_tf", "midpoint", "ce_body"):
        (results_root / folder).mkdir(parents=True, exist_ok=True)

    source = ORIGINAL / SCRIPTS[args.study]
    source_text = source.read_text(encoding="utf-8")
    digest = canonical_source_digest(source_text)
    if digest != SOURCE_HASHES[source.name]:
        print(
            f"ERROR: Canonical source hash changed for {source.name}. Audit the research change "
            "and update the declared hash deliberately.",
            file=sys.stderr,
        )
        return 2
    try:
        code = patch_source(normalized_source(source_text), source.name, data, results_root)
    except Exception as exc:
        print(f"ERROR: Could not create portable source: {exc}", file=sys.stderr)
        return 2

    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT) + (os.pathsep + environment["PYTHONPATH"] if environment.get("PYTHONPATH") else "")
    if args.tf is not None:
        environment["TF"] = str(args.tf)
    if args.study == "ce-body":
        environment["CE_TFS"] = ",".join(map(str, ce_values))
    command_extra = [str(args.tf)] if args.study == "midpoint" else []

    before = snapshot_outputs(results_root, runs)
    started = datetime.now(timezone.utc)
    status = "failed"
    exit_code = 1
    error = None
    try:
        with tempfile.TemporaryDirectory(prefix="fvg_canonical_") as temporary:
            patched = Path(temporary) / source.name
            patched.write_text(code, encoding="utf-8")
            process = subprocess.run([sys.executable, str(patched), *command_extra], cwd=ROOT, env=environment)
            exit_code = process.returncode
            if exit_code:
                raise subprocess.CalledProcessError(exit_code, process.args)
            if args.study == "ce-body":
                suffix = "_" + "_".join(map(str, ce_values)) if len(ce_values) < len(VALID_TFS) else ""
                trade_file = results_root / "ce_body" / f"trades{suffix}.pkl"
                subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "scripts" / "postprocess_body_bands.py"),
                        "--trade-file",
                        str(trade_file),
                        "--output",
                        str(results_root / "ce_body" / "body_depth_5pct.csv"),
                    ],
                    check=True,
                    cwd=ROOT,
                    env=environment,
                )
            status = "success"
            exit_code = 0
    except Exception as exc:
        error = str(exc)
        if isinstance(exc, subprocess.CalledProcessError):
            exit_code = exc.returncode

    finished = datetime.now(timezone.utc)
    after = snapshot_outputs(results_root, runs)
    changed = sorted(path for path, mtime in after.items() if before.get(path) != mtime)
    manifest = {
        "study": args.study,
        "status": status,
        "exit_code": exit_code,
        "started_utc": started.isoformat(),
        "finished_utc": finished.isoformat(),
        "source": str(source.relative_to(ROOT)),
        "source_sha256": digest,
        "tf": args.tf,
        "ce_tfs": ce_values if args.study == "ce-body" else None,
        "data_path": (
            str(data.relative_to(ROOT)) if data.is_relative_to(ROOT) else str(data)
        ),
        "results_root": str(results_root.relative_to(ROOT)),
        "data_mtime_ns": data.stat().st_mtime_ns,
        "generated_files": changed,
        "error": error,
    }
    run_name = f"{started.strftime('%Y%m%dT%H%M%S')}_{args.study}.json"
    manifest_text = json.dumps(manifest, indent=2)
    (runs / run_name).write_text(manifest_text, encoding="utf-8")
    (runs / f"latest_{args.study}.json").write_text(manifest_text, encoding="utf-8")
    if args.tf is not None:
        (runs / f"latest_{args.study}_tf{args.tf}.json").write_text(manifest_text, encoding="utf-8")
    record = write_run_record(
        ROOT,
        kind=f"canonical-{args.study}" + (f"-tf{args.tf}" if args.tf is not None else ""),
        command=[sys.executable, str(ROOT / "scripts" / "run_original.py"), *sys.argv[1:]],
        status=status,
        started_unix=started.timestamp(),
        finished_unix=finished.timestamp(),
        inputs=[data, source],
        outputs=changed,
        extra={
            "canonical_source_sha256": digest,
            "tf": args.tf,
            "ce_tfs": ce_values if args.study == "ce-body" else None,
            "exit_code": exit_code,
            "error": error,
        },
    )
    manifest["run_record"] = str(record.relative_to(ROOT))
    manifest_text = json.dumps(manifest, indent=2)
    (runs / run_name).write_text(manifest_text, encoding="utf-8")
    (runs / f"latest_{args.study}.json").write_text(manifest_text, encoding="utf-8")
    if args.tf is not None:
        (runs / f"latest_{args.study}_tf{args.tf}.json").write_text(manifest_text, encoding="utf-8")

    if status != "success":
        print(f"ERROR: Canonical experiment failed: {error}", file=sys.stderr)
    else:
        print(f"Run manifest: {runs / run_name}")
        print(f"Run provenance capsule: {record}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
