from __future__ import annotations

import html
from pathlib import Path


def _fmt(value, suffix=""):
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.4g}{suffix}"
    return f"{value}{suffix}"


def _has_real_output(value) -> bool:
    if isinstance(value, dict):
        return any(_has_real_output(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return bool(value) and any(_has_real_output(item) for item in value)
    return value is not None and value != ""


def build_public_report(summary: dict, experiments: dict) -> str:
    dataset = summary.get("dataset", {})
    raw = summary.get("experiments", {}).get("raw_fill", {}).get("summary", {})
    experiment_cards = []
    for exp_id, meta in experiments.items():
        payload = summary.get("experiments", {}).get(exp_id, {})
        has_output = _has_real_output(payload)
        status = "Local output available" if has_output else "Run locally to populate"
        experiment_cards.append(
            f"""<article class="card">
<div class="eyebrow">Experiment {html.escape(meta['num'])}</div>
<h3>{html.escape(meta['title'])}</h3>
<p>{html.escape(meta['question'])}</p>
<div class="status">{html.escape(status)}</div>
</article>"""
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Public Nasdaq FVG Replication</title>
<style>
:root{{--bg:#0b0f17;--panel:#111827;--panel2:#182235;--line:#334155;--text:#f8fafc;--muted:#cbd5e1;--blue:#60a5fa;--amber:#f59e0b}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:16px/1.65 system-ui,sans-serif}}a{{color:var(--blue)}}.wrap{{max-width:1180px;margin:auto;padding:32px 24px 80px}}.hero{{padding:42px;border:1px solid var(--line);border-radius:22px;background:linear-gradient(135deg,rgba(96,165,250,.15),transparent 50%),var(--panel)}}.eyebrow{{font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.12em;color:var(--blue)}}h1{{font-size:clamp(38px,7vw,68px);line-height:1;letter-spacing:-.05em;margin:10px 0 18px}}h2{{font-size:30px;margin:42px 0 14px}}h3{{margin:8px 0}}p{{color:var(--muted)}}.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}}.metric,.card,.callout{{border:1px solid var(--line);background:var(--panel);border-radius:14px;padding:16px}}.metric strong{{display:block;font-size:23px}}.metric span,.status{{font-size:13px;color:var(--muted)}}.callout{{margin-top:18px;border-left:4px solid var(--amber)}}.status{{margin-top:12px}}code{{background:var(--panel2);padding:2px 5px;border-radius:5px}}@media(max-width:800px){{.grid{{grid-template-columns:1fr}}.hero{{padding:28px}}}}
</style>
</head>
<body>
<main class="wrap">
<section class="hero">
<div class="eyebrow">Public long-history replication</div>
<h1>FVG Predictive Strength · Nasdaq 2010–2026</h1>
<p>A free-source companion to the licensed MNQ study. The public track repeats the same FVG falsification sequence on HistData NSX/USD, a Nasdaq-100 index-style quote feed.</p>
<div class="callout"><strong>Boundary:</strong> this is not CME NQ/MNQ futures data. Price-pattern replication is in scope; futures volume, rolls, exact ticks, slippage and execution claims are not. The preserved CE/body code also carries a 0.25-point MNQ-derived minimum-gap/tick-unit convention, so those public-track fields must be interpreted as 0.25-point units rather than NSX/USD exchange ticks.</div>
</section>

<h2>Dataset</h2>
<div class="grid">
<div class="metric"><span>Rows</span><strong>{int(dataset.get('rows', 0)):,}</strong></div>
<div class="metric"><span>Start</span><strong>{html.escape(str(dataset.get('start_utc', '—'))[:10])}</strong></div>
<div class="metric"><span>End</span><strong>{html.escape(str(dataset.get('end_utc', '—'))[:10])}</strong></div>
</div>

<h2>Latest local replication</h2>
<div class="grid">
<div class="metric"><span>Detected 1m FVGs</span><strong>{int(raw.get('fvg_count', 0)):,}</strong></div>
<div class="metric"><span>Raw 60m touch</span><strong>{_fmt(raw.get('raw_touch_60') * 100 if raw.get('raw_touch_60') is not None else None, '%')}</strong></div>
<div class="metric"><span>Experiment families populated</span><strong>{int(summary.get('experiment_families_with_outputs', 0))}/9</strong></div>
</div>

<h2>Experiment library</h2>
<div class="grid">{''.join(experiment_cards)}</div>

<h2>Reproduce</h2>
<div class="callout">
<p>Prepare the free HistData CSV locally, then run the replication:</p>
<pre><code>python scripts/prepare_histdata_nsx.py --input "C:\\path\\to\\NSXUSD_M1_ALL.csv" --output data/public/nsxusd
python scripts/reproduce_public_nsx.py
python scripts/generate_public_nsx_report.py</code></pre>
<p><code>scripts/install_public_nsx.py</code> is only an optional route if a permitted GitHub Release data asset is published later. The repository does not assume redistribution rights for the HistData-derived market files.</p>
<p>The interactive Research Lab exposes local raw candles, FVG overlays, individual experiment reruns and the complete cached replication workflow after the dataset has been prepared on that machine.</p>
</div>
</main>
</body>
</html>"""


def write_public_report(output: str | Path, summary: dict, experiments: dict) -> Path:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_public_report(summary, experiments), encoding="utf-8")
    return output
