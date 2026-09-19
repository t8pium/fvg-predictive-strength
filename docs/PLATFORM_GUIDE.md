# Research Platform Guide

The repository has two layers that should not be confused:

1. **Published study v1** — frozen evidence and hash-locked canonical analysis.
2. **Research platform** — the UI, demo, full-reproduction orchestration, diagnostics, benchmarking, report generation and corrected v2 research tools around that evidence.

## Fastest ways to use the project

### I only want to understand the study

Open the public static report:

**https://t8pium.github.io/fvg-predictive-strength/**

Or run `START_HERE.bat` and stay on **Research overview**.

No market data is required.

### I want proof that the software works

Open **Quick demo** in the Research Lab.

The demo creates deterministic synthetic OHLCV and exercises:

```text
synthetic bars
    ↓
causal market state
    ↓
FVG detection
    ↓
matched ordinary controls
    ↓
forward touch outcomes
    ↓
result table/chart
```

The demo is a software validation only. Its numbers are not market evidence.

CLI:

```bash
python scripts/run_demo.py
```

### I want to reproduce the published market study

1. Prepare your licensed dataset.
2. Open **Full reproduction**.
3. Click **Start / resume full reproduction**.

The orchestrator runs 12 cached stages:

- detailed 1m once;
- multi-timeframe at 1m, 5m, 15m, 1H and 4H;
- midpoint at 1m, 5m, 15m, 1H and 4H;
- complete CE/body suite.

Interrupted runs are resumed by checking fresh success manifests for the current active dataset.

CLI:

```bash
python scripts/reproduce_full.py
```

Use `--force` only when you intentionally want to recompute every stage.

## Public static report

`scripts/generate_static_report.py` builds a self-contained HTML report from:

- `reference_results/reference_metrics.json`;
- `reference_results/manifest.json`;
- experiment metadata;
- provenance metadata;
- deterministic conceptual diagrams;
- committed reference figures.

The public copy is hosted by the existing `t8pium.github.io` portfolio Pages site. The repository generator remains the source for downloadable/offline report builds.

Local generation:

```bash
python scripts/generate_static_report.py --output site/index.html
```

The Research Lab **Report / export** page also provides the same report as a downloadable single HTML file.

## Experiment provenance

Every experiment page shows:

- canonical computational suite;
- input scope;
- published population/sample design;
- control construction;
- random seed;
- primary generated outputs.

This information comes from `app/provenance.py`.

## Visual explainers

`fvg_research/explainers.py` contains deterministic SVG explainers for all nine experiments plus the research architecture.

They are used in both:

- the interactive Research Lab;
- the self-contained static report.

The diagrams explain the experiment conceptually; the canonical source remains the exact numerical specification.

## Diagnostics

The **Diagnostics & uncertainty** page separates:

- absolute raw fill probability;
- FVG-minus-control effect size;
- descriptive Wilson intervals;
- CE sample-size uncertainty;
- early-versus-later chronological stability.

Important: the descriptive Wilson intervals do not pretend overlapping market events are independent. They are explicitly labeled as descriptive and do not replace the canonical clustered/bootstrap calculations.

## Performance

The **Performance & startup** page benchmarks the current computer rather than publishing misleading hardware-independent timing claims.

The benchmark includes:

- fresh dependency import probe;
- deterministic quick-demo runtime;
- Python peak allocation during the quick demo;
- static-report generation;
- optional full active-dataset load;
- measured full-reproduction stage timings when available.

CLI:

```bash
python scripts/benchmark.py
python scripts/benchmark.py --include-dataset
```

## Repeat-launch speed

The first launch creates `.fvg_venv` and installs the pinned dependencies.

On later launches, the bootstrap:

1. fingerprints `pyproject.toml` and `requirements.txt`;
2. performs one lightweight health probe;
3. skips every pip install command when the environment is healthy;
4. launches Streamlit.

A regression test protects this fast path.

## Research v2

`research_v2/` is deliberately separate from published v1.

It implements corrected/extended methods for known limitations:

- symmetric full-horizon eligibility;
- contract-boundary censoring;
- parent-paired age-decay controls;
- CME trade-date bootstrap clustering;
- period-local control construction;
- walk-forward validation;
- Benjamini-Hochberg false-discovery-rate correction.

Current executable studies:

```bash
python -m research_v2.runner attraction-1m --horizon 60
python -m research_v2.runner age-decay-1m
python -m research_v2.runner walk-forward-1m --horizon 60
python -m research_v2.runner ce-reinfer --bootstrap 500
```

All Research v2 output is labeled **NEW / UNPUBLISHED RESEARCH** until it has been run on licensed data and reviewed.

## Local output areas

```text
results/demo/                 quick-demo artifacts
results/_runs/                canonical per-suite run manifests
results/_full_reproduction/   orchestration state + verification
results/_benchmarks/          machine-specific benchmark output
results/research_v2/          corrected / extended unpublished research
results/_logs/                child-process logs
```

Generated results remain ignored by Git.

## Verification

The normal CI suite still checks:

- installation on supported Python versions;
- package imports outside the repository working directory;
- compilation of every Python source;
- child-script startup;
- synthetic/data IO tests;
- every dashboard route;
- quick-demo mechanics;
- Research v2 correction mechanics;
- static report generation;
- canonical source hashes;
- provenance / reference-figure policy;
- exclusion of licensed/generated market data.
