from __future__ import annotations

import json
from html import escape
from pathlib import Path

from .explainers import experiment_svg, research_flow_svg


def _metric_rows(exp_id: str, reference: dict) -> list[tuple[str, str]]:
    e = reference["experiments"][exp_id]
    if exp_id == "raw_fill":
        return [
            ("5m touch", f"{e['touch_rate'][0] * 100:.2f}%"),
            ("60m touch", f"{e['touch_rate'][3] * 100:.2f}%"),
            ("Eventual touch", f"{e['eventual_touch'] * 100:.3f}%"),
            ("Eventual full fill", f"{e['eventual_full'] * 100:.3f}%"),
        ]
    if exp_id == "matched_attraction":
        rows = e["deep_1m"]
        return [
            ("5m FVG − control", f"{rows[0]['difference_pp']:+.3f} pp"),
            ("60m FVG − control", f"{rows[3]['difference_pp']:+.3f} pp"),
            ("~1d FVG − control", f"{rows[6]['difference_pp']:+.3f} pp"),
            ("~3d FVG − control", f"{rows[7]['difference_pp']:+.3f} pp"),
        ]
    if exp_id == "age_decay":
        return [(row["window"], f"{row['difference_pp']:+.2f} pp") for row in e["one_minute"]]
    if exp_id == "continuation":
        return [(row["timeframe"], f"{row['difference_atr']:+.4f} ATR") for row in e["five_bar"]]
    if exp_id == "retest":
        return [(row["timeframe"], f"{row['difference_pp']:+.2f} pp") for row in e["reaction"]]
    if exp_id == "midpoint":
        return [(row["timeframe"], f"{row['difference_pp']:+.2f} pp") for row in e["reaction"]]
    if exp_id == "body_acceptance":
        return [
            (f"4H {row['band']}", f"N={row['N']} · win={row['win_rate']:.2f}% · mean R={row['mean_R']:+.3f}")
            for row in e["four_hour_bands"]
        ]
    if exp_id == "controls_regimes":
        return [
            ("60m FVG odds ratio", f"{e['fvg_odds_ratio_60m']:.4f}"),
            *[(row["bucket"], f"{row['difference_pp']:+.2f} pp") for row in e["distance"]],
        ]
    if exp_id == "oos":
        return [
            ("Deep 1m / 60m early", f"{e['deep_1m_60m']['train_pp']:+.2f} pp"),
            ("Deep 1m / 60m later", f"{e['deep_1m_60m']['test_pp']:+.2f} pp"),
            *[
                (f"{row['timeframe']} early → later", f"{row['train_pp']:+.2f} → {row['test_pp']:+.2f} pp")
                for row in e["five_bar"]
            ],
        ]
    return []


def _table(rows: list[tuple[str, str]]) -> str:
    return (
        '<div class="metric-grid">'
        + "".join(
            f'<div class="metric"><div class="metric-label">{escape(label)}</div>'
            f'<div class="metric-value">{escape(value)}</div></div>'
            for label, value in rows
        )
        + "</div>"
    )


def _published_figure_html(root: Path) -> str:
    figures = [
        ("Raw revisit probability", "01_fill_curve.svg"),
        ("Matched attraction", "02_matched_advantage.svg"),
        ("Midpoint / CE", "03_midpoint_reaction.svg"),
        ("Chronological robustness", "04_oos_robustness.svg"),
    ]
    cards = []
    for title, name in figures:
        path = root / "reference_results" / "figures" / name
        if path.is_file():
            cards.append(f'<section class="figure-card"><h3>{escape(title)}</h3>{path.read_text(encoding="utf-8")}</section>')
    return "\n".join(cards)


def _temporal_extension_html(root: Path) -> str:
    """Render the optional exploratory temporal extension if its frozen summary exists."""
    path = root / "research_v2" / "findings" / "temporal_attraction_reaction_2026-09-20.json"
    if not path.is_file():
        return ""
    data = json.loads(path.read_text(encoding="utf-8"))
    overall = data["overall"]
    attraction = overall["attraction"]
    rejection = overall["rejection"]
    reaction = overall["reaction_3bar_atr"]
    years = data.get("attraction_by_year_pp", {})
    sessions = data.get("attraction_by_formation_session_pp", {})
    year_rows = "".join(
        f"<tr><th>{escape(str(year))}</th><td>{float(value):+.2f} pp</td></tr>"
        for year, value in years.items()
    )
    session_rows = "".join(
        f"<tr><th>{escape(str(name).replace('_', ' ').title())}</th><td>{float(value):+.2f} pp</td></tr>"
        for name, value in sessions.items()
    )
    return f"""
<section class="experiment" id="temporal-extension">
  <div class="eyebrow">Exploratory extension · 2026-09-20</div>
  <h2>When are FVGs most predictive?</h2>
  <p class="question">The temporal extension separates attraction from first-touch reaction/rejection across year, session, hour and native timeframe.</p>
  <div class="callout"><strong>Main finding.</strong> Attraction is more regime-dependent; reaction/rejection is smaller but more temporally stable.</div>
  <div class="metric-grid">
    <div class="metric"><div class="metric-label">60m near-edge attraction</div><div class="metric-value">{attraction["fvg"] * 100:.2f}% vs {attraction["control"] * 100:.2f}% · {attraction["difference_pp"]:+.2f} pp</div></div>
    <div class="metric"><div class="metric-label">First-touch rejection</div><div class="metric-value">{rejection["fvg"] * 100:.2f}% vs {rejection["control"] * 100:.2f}% · {rejection["difference_pp"]:+.2f} pp</div></div>
    <div class="metric"><div class="metric-label">3-bar move away</div><div class="metric-value">{reaction["difference"]:+.3f} ATR incremental</div></div>
    <div class="metric"><div class="metric-label">Strongest timing variable</div><div class="metric-value">FVG age / freshness</div></div>
  </div>
  <div class="two-col">
    <div>
      <h3>Attraction premium by year</h3>
      <table class="provenance">{year_rows}</table>
    </div>
    <div>
      <h3>Attraction premium by formation session</h3>
      <table class="provenance">{session_rows}</table>
    </div>
  </div>
  <div class="warning"><strong>Status.</strong> This is newer exploratory / extended research on the same MNQ history, not part of the frozen published v1 metrics. Weekday and recurring calendar-month effects were weak; individual day/week/hour spikes are treated as regime diagnostics rather than production rules.</div>
  <p><a href="https://github.com/t8pium/fvg-predictive-strength/blob/main/docs/TEMPORAL_ATTRACTION_REACTION_STUDY.md">Read the complete temporal study ↗</a></p>
</section>
"""


def build_report(
    reference: dict,
    experiments: dict,
    provenance: dict,
    root: str | Path,
) -> str:
    root = Path(root)
    study = reference["study"]
    toc = "".join(
        f'<a href="#exp-{escape(exp_id)}">{escape(meta["num"])} · {escape(meta["title"])}</a>'
        for exp_id, meta in experiments.items()
    )
    sections = []
    for exp_id, meta in experiments.items():
        prov = provenance[exp_id]
        steps = "".join(f"<li>{escape(step)}</li>" for step in meta["method"])
        prov_rows = "".join(
            f"<tr><th>{escape(label)}</th><td>{escape(str(value))}</td></tr>"
            for label, value in [
                ("Canonical suite", prov["suite"]),
                ("Input", prov["input"]),
                ("Published population", prov["population"]),
                ("Controls", prov["controls"]),
                ("Seed", prov["seed"]),
                ("Primary outputs", ", ".join(prov["outputs"])),
            ]
        )
        sections.append(
            f"""
<section class="experiment" id="exp-{escape(exp_id)}">
  <div class="eyebrow">Experiment {escape(meta["num"])}</div>
  <h2>{escape(meta["title"])}</h2>
  <p class="question">{escape(meta["question"])}</p>
  <p>{escape(meta["summary"])}</p>
  <div class="callout"><strong>Published takeaway.</strong> {escape(meta["takeaway"])}</div>
  {_table(_metric_rows(exp_id, reference))}
  <div class="diagram">{experiment_svg(exp_id)}</div>
  <div class="two-col">
    <div>
      <h3>Method</h3>
      <ol>{steps}</ol>
    </div>
    <div>
      <h3>Provenance</h3>
      <table class="provenance">{prov_rows}</table>
      <div class="warning"><strong>Limitation.</strong> {escape(meta["limitations"])}</div>
    </div>
  </div>
</section>
"""
        )

    css = r"""
:root{--bg:#0b0f14;--panel:#111821;--panel2:#161f2b;--text:#eef3f8;--muted:#9aa9b8;--line:#283442;--blue:#58a6ff;--green:#3fb950;--amber:#d29922}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.65 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
a{color:#8fc3ff;text-decoration:none}a:hover{text-decoration:underline}.wrap{max-width:1180px;margin:auto;padding:28px 24px 80px}
.hero{padding:54px 46px;border:1px solid var(--line);border-radius:24px;background:linear-gradient(135deg,rgba(88,166,255,.16),transparent 48%),var(--panel);margin:18px 0 26px}
.eyebrow{text-transform:uppercase;letter-spacing:.12em;font-size:12px;font-weight:800;color:var(--blue)}h1{font-size:clamp(38px,7vw,68px);line-height:1;letter-spacing:-.05em;margin:10px 0 18px}h2{font-size:34px;letter-spacing:-.035em;margin:8px 0}h3{font-size:20px;margin:18px 0 8px}.lede{font-size:19px;color:var(--muted);max-width:900px}.question{font-size:22px;font-weight:700;line-height:1.35}.pills{display:flex;gap:8px;flex-wrap:wrap;margin-top:20px}.pill{border:1px solid var(--line);border-radius:999px;padding:6px 10px;color:#c8d4df;background:rgba(255,255,255,.02);font-size:13px;font-weight:700}
.nav{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:24px 0 40px}.nav a{border:1px solid var(--line);border-radius:10px;padding:10px 12px;background:var(--panel);color:var(--text)}
.summary{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:24px 0}.summary>div,.metric,.figure-card{border:1px solid var(--line);background:var(--panel);border-radius:14px;padding:16px}.big{font-size:24px;font-weight:800;letter-spacing:-.03em}.muted,.metric-label{color:var(--muted);font-size:13px}.metric-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin:18px 0}.metric-value{font-size:18px;font-weight:800;margin-top:3px}
.callout,.warning{border-left:4px solid var(--blue);background:rgba(88,166,255,.09);padding:14px 16px;border-radius:10px;margin:18px 0}.warning{border-left-color:var(--amber);background:rgba(210,153,34,.09)}
.experiment{border-top:1px solid var(--line);padding:56px 0 24px}.diagram{overflow:auto;margin:22px 0}.diagram svg,.figure-card svg{max-width:100%;height:auto}.two-col{display:grid;grid-template-columns:1.3fr 1fr;gap:28px;align-items:start}.provenance{width:100%;border-collapse:collapse}.provenance th,.provenance td{text-align:left;vertical-align:top;padding:9px 8px;border-bottom:1px solid var(--line)}.provenance th{width:34%;color:var(--muted);font-size:13px}
.figures{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:24px 0}.footer{border-top:1px solid var(--line);margin-top:50px;padding-top:24px;color:var(--muted)}
code{background:#151d27;padding:2px 5px;border-radius:5px}@media(max-width:850px){.summary,.figures,.two-col,.nav{grid-template-columns:1fr}.hero{padding:34px 24px}.wrap{padding:18px 16px 60px}}
"""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FVG Predictive Strength — Research Report</title>
<meta name="description" content="Reproducible MNQ Fair Value Gap predictive-strength study.">
<style>{css}</style>
</head>
<body>
<main class="wrap">
<section class="hero">
  <div class="eyebrow">Quantitative market-structure research</div>
  <h1>FVG Predictive Strength</h1>
  <p class="lede">A reproducible MNQ study testing whether mechanically defined Fair Value Gaps add predictive information beyond distance, volatility, trend, session and ordinary price revisits.</p>
  <div class="pills">
    <span class="pill">MNQ</span><span class="pill">{escape(study["period"])}</span>
    <span class="pill">{study["active_1m_rows"]:,} active 1m bars</span>
    <span class="pill">{study["fvg_1m_count"]:,} detected 1m FVGs</span>
    <span class="pill">9 experiments</span>
  </div>
</section>

<section>
<h2>Answer in one sentence</h2>
<div class="callout"><strong>Published conclusion.</strong> FVGs were revisited frequently, but after matching comparable ordinary zones the incremental attraction was small, strongest shortly after formation, and inconsistent across longer horizons, timeframes and later data.</div>
<div class="summary">
  <div><div class="muted">60m raw revisit</div><div class="big">90.86%</div></div>
  <div><div class="muted">60m matched excess</div><div class="big">+0.58 pp</div></div>
  <div><div class="muted">~1 day matched excess</div><div class="big">+0.003 pp</div></div>
  <div><div class="muted">Later deep 1m / 60m</div><div class="big">+0.08 pp</div></div>
</div>
</section>

<section>
<h2>Research architecture</h2>
<p class="muted">Four canonical computational suites feed nine reader-facing experiments. The presentation layer does not reimplement the heavy research logic.</p>
<div class="diagram">{research_flow_svg()}</div>
</section>

<section>
<h2>Published figures</h2>
<div class="figures">{_published_figure_html(root)}</div>
</section>

<section>
<h2>Experiment index</h2>
<nav class="nav">{toc}</nav>
</section>

{''.join(sections)}

{_temporal_extension_html(root)}

<section class="experiment" id="platform-v4">
  <div class="eyebrow">Research Platform v4</div>
  <h2>Audit the observations, stress-test the pipeline, then extend the study</h2>
  <p class="question">The published v1 evidence remains frozen while the surrounding platform adds stronger falsification and reproducibility tooling.</p>
  <div class="metric-grid">
    <div class="metric"><div class="metric-label">Visual audit</div><div class="metric-value">Event explorer</div></div>
    <div class="metric"><div class="metric-label">False-discovery checks</div><div class="metric-value">Placebos + ablations</div></div>
    <div class="metric"><div class="metric-label">Sensitivity</div><div class="metric-value">Power / MDE</div></div>
    <div class="metric"><div class="metric-label">Confirmatory workflow</div><div class="metric-value">SHA-256 preregistration</div></div>
    <div class="metric"><div class="metric-label">Regression proof</div><div class="metric-value">Golden fixture</div></div>
    <div class="metric"><div class="metric-label">Run audit trail</div><div class="metric-value">Provenance capsules</div></div>
    <div class="metric"><div class="metric-label">Input safety</div><div class="metric-value">Dataset preflight</div></div>
    <div class="metric"><div class="metric-label">Robustness</div><div class="metric-value">Stability atlas</div></div>
    <div class="metric"><div class="metric-label">Practical relevance</div><div class="metric-value">Economic significance</div></div>
    <div class="metric"><div class="metric-label">Self-audit</div><div class="metric-value">v1 → v2 comparison</div></div>
    <div class="metric"><div class="metric-label">Distribution</div><div class="metric-value">Versioned releases</div></div>
  </div>
  <div class="warning"><strong>Important.</strong> Corrected Research v2 values are not inserted into this published report until they have actually been rerun on licensed data and reviewed. The platform adds the machinery; it does not invent corrected market results.</div>
</section>

<footer class="footer">
<p><strong>Reproducibility.</strong> Frozen evidence lives in <code>reference_results/reference_metrics.json</code>; canonical source hashes and dataset provenance live in <code>reference_results/manifest.json</code>. The original analysis files remain under <code>src/original/</code>.</p>
<p>This report is generated from repository data. It does not redistribute licensed market history.</p>
</footer>
</main>
</body>
</html>
"""


def write_report(
    output: str | Path,
    reference_path: str | Path,
    experiments: dict,
    provenance: dict,
    root: str | Path,
) -> Path:
    output = Path(output)
    reference = json.loads(Path(reference_path).read_text(encoding="utf-8"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_report(reference, experiments, provenance, root), encoding="utf-8")
    return output
