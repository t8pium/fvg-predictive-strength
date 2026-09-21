# Research Platform Guide

The repository has three layers that should not be confused:

1. **Published MNQ study v1** — frozen evidence and hash-locked canonical analysis.
2. **Research platform** — the UI, demo, full-reproduction orchestration, diagnostics, benchmarking, report generation and corrected v2 research tools around that evidence.
3. **Public Nasdaq replication track** — a separate NSX/USD 2010–2026 price-history workflow for longer-horizon robustness research. It does not replace the MNQ evidence or create futures-specific claims.

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

### I want to reproduce the public long-history Nasdaq track

Use the merged free HistData NSX/USD M1 CSV:

```bash
python scripts/prepare_histdata_nsx.py --input "C:\\path\\to\\NSXUSD_M1_ALL.csv" --output data/public/nsxusd
python scripts/reproduce_public_nsx.py
python scripts/generate_public_nsx_report.py
```

The prepared public dataset is queried locally in the Research Lab. The “live” candle explorer is not a public raw-data website.

Important boundaries:

- NSX/USD is an index-style quote feed, not CME NQ/MNQ futures;
- volume is not usable as centralized exchange volume;
- there are no contract identifiers or futures roll boundaries;
- the preserved CE/body script carries an MNQ-derived 0.25-point minimum-gap / `width_ticks` convention, which becomes a transferred 0.25-point method unit on NSX/USD rather than an exchange tick;
- the complete 5,046,180-row public replication is not yet a published result until the full 12-stage run is completed and reviewed.

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
results/public_nsx/            public NSX/USD replication outputs
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


## Research Platform v4 audit tools

### Event explorer

**Event explorer** provides an event-level visual audit on the active dataset:

- real candlestick bars around the formation;
- lower/upper FVG edges and midpoint;
- selected forward touch outcome;
- year/direction/session/geometry filters;
- optional exact causal volatility/trend state;
- one matched ordinary control generated on demand.

The expensive state-matching operation is not run during ordinary navigation.

### Placebo / negative-control suite

`research_v2/placebos.py` asks whether the pipeline also creates apparent effects after deliberately breaking the FVG hypothesis.

Current controls include:

- state-matched ordinary zones;
- shuffled FVG geometry;
- direction-flipped mirror zones;
- time-shifted FVG geometry.

Run it from **Placebos / ablations** or:

```bash
python -m research_v2.runner placebo-1m --horizon 60
```

### Matching ablation

`research_v2/ablation.py` systematically compares full matching with versions that remove session, time-of-day, volatility regime, trend or all state grouping.

```bash
python -m research_v2.runner ablation-1m --horizon 60
```

### Power / MDE

The power page reports approximate two-sided minimum detectable probability differences at 80% and 90% power. A configurable design effect penalizes nominal N for clustered/dependent observations.

The page also estimates the detectable mean R for smaller trade-like samples.

### Preregistered hypothesis registry

The registry requires:

- hypothesis ID/title/question;
- dataset window;
- primary outcome;
- timeframe;
- filters;
- horizon;
- expected direction;
- statistic;
- multiplicity family.

Locking creates a SHA-256 hash over the confirmatory fields. Editing one of those fields invalidates verification.

```bash
python scripts/register_hypothesis.py hypothesis_draft.json
```

### Golden miniature dataset

`tests/fixtures/golden_ohlcv.csv` is synthetic, redistributable and byte-stable. Its manifest records the expected row count, FVG count, first event and Git blob hash.

This provides a permanent exact regression target in addition to the larger randomized synthetic demo.

### Dataset preflight

**Dataset preflight** is intentionally separate from active-contract construction. It does not mutate the current dataset.

For ZIPs it inspects archive members, expanded/compressed size, supported market-data entries and small sidecars. For CSV/Parquet it inspects schema/row metadata. Direct DBN files expose metadata where available through the pinned Databento library.

### Standard run capsules

Serious calculations write `results/_run_records/*.json` containing:

- command;
- start/finish/elapsed time;
- git commit where available;
- Python/OS;
- dependency fingerprint;
- dataset pointer hash;
- input/output file size and SHA-256;
- run-specific parameters.

### Stability atlas

The published atlas shows timeframe, chronological and distance variation immediately.

After local reproduction it also ingests generated multi-timeframe/year/distance/volatility/sensitivity tables and renders a timeframe × horizon heatmap when those columns are available.

### Economic significance

Only trade-like canonical CE output is converted into economic scenarios. The model applies explicit MNQ point/tick values, round-turn commission and slippage assumptions.

Attraction probabilities are never converted into PnL without a defined execution rule.

### v1 → v2 comparison

The comparison page never fabricates corrected results. It appears only after the corresponding v2 output exists locally and reports:

```text
published v1 | corrected v2 | change | reason for correction
```

### Versioned GitHub Releases

`.github/workflows/release.yml` supports both `v*` tags and manual workflow dispatch.

`scripts/build_release.py` creates a clean ZIP, standalone HTML report and checksum manifest while excluding local data, results, environments and generated site output.

## Research Platform v5 — public long-history replication

Version 5 adds a second first-class dataset path around HistData NSX/USD:

- full CSV audit and fixed-EST → UTC normalization;
- prepared Parquet/pickle under `data/public/nsxusd/`;
- DuckDB-backed local date-range queries;
- local candlestick/FVG exploration;
- isolated individual experiment reruns;
- resume-safe 12-stage public reproduction;
- machine-readable public summary and separate report;
- explicit data-redistribution boundary.

The v5 double-check found and fixed two presentation/status bugs: empty nested result dictionaries could be mistaken for completed output, and some copy overstated the eras covered by the November 2010 dataset start. It also made the inherited 0.25-point CE convention explicit.

The audited PR state passed **80 tests** on Ubuntu Python 3.11, Windows Python 3.12 and Ubuntu Python 3.13. The current squash merge commit is `39528f2aff3a7d93f55db5ad21ef3ea5ceab5dcf`; the PR head, rather than the post-merge squash SHA, is the state directly exercised by the matrix.
