from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fvg_research.demo import run_demo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the fast synthetic end-to-end FVG software demo.")
    parser.add_argument("--bars", type=int, default=16_000)
    parser.add_argument("--output", default=str(ROOT / "results" / "demo"))
    args = parser.parse_args(argv)

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    result = run_demo(n=args.bars)
    result.horizons.to_csv(output / "demo_horizons.csv", index=False)
    result.bars.tail(800).to_csv(output / "sample_bars.csv", index_label="ts_event")
    summary = {
        "kind": "synthetic_software_demo",
        "market_claim": False,
        "bars": len(result.bars),
        "detected_fvgs": len(result.events),
        "matched_control_rows": len(result.controls),
        "elapsed_seconds": round(result.elapsed_seconds, 4),
        "horizons": result.horizons.to_dict(orient="records"),
        "note": "Synthetic data validates the software workflow only. These numbers are not market evidence.",
    }
    (output / "demo_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Wrote demo artifacts to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
