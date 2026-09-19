# Research v2 — corrected / extended study

This directory is deliberately separate from the published v1 analysis.

The files in `src/original/` reproduce the published study. **Research v2 produces new results** and must never be presented as if those values were part of the frozen v1 report.

## Corrections implemented

The shared v2 methods address the methodological issues documented in `docs/SCIENTIFIC_AUDIT.md`:

- **Full-horizon symmetry:** real FVGs and controls must both have the complete requested future horizon.
- **Contract-boundary censoring:** future outcomes cannot cross an active-contract segment.
- **Parent-paired age decay:** control survivors are averaged within each parent before the parent-level comparison.
- **CME trade-date clustering:** bootstrap clusters use the same 18:00 ET trade-date convention as active-contract construction.
- **Chronological isolation:** walk-forward controls are built only from candidates inside the corresponding test period.
- **Multiplicity control:** walk-forward p-values receive Benjamini-Hochberg FDR-adjusted q-values.
- **Walk-forward validation:** expanding chronology produces multiple forward test windows rather than one random shuffle.

## Current v2 runner

The first concrete v2 target is the primary 1-minute matched-attraction claim:

```bash
python -m research_v2.runner attraction-1m --horizon 60
```

A walk-forward version is also implemented:

```bash
python -m research_v2.runner walk-forward-1m --horizon 60
```

Outputs go to `results/research_v2/`.

## Interpretation rule

Until a v2 result has been run on licensed data and reviewed, it is labeled **NEW / UNPUBLISHED RESEARCH**. The Research Lab keeps v1 published evidence and v2 corrected research visually separate.
