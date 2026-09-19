# Research Lab v2 rebuild

This rebuild preserves the four hash-locked published analysis scripts while replacing the presentation and local-reproduction shell.

Key changes:

- evidence-first README and dashboard;
- multiple published charts per experiment;
- explicit published-vs-local verification;
- native Windows file selection for large local market-data archives;
- versioned dataset generations selected through current_dataset.json, avoiding in-place replacement of large locked files;
- provenance manifest and committed reference figures;
- modular app/ presentation layer;
- deterministic tests for dataset-generation switching.

The scientific limitations documented in SCIENTIFIC_AUDIT.md remain intentionally unchanged.

The v2 shell is covered by dashboard-route, dataset-pointer, reference-figure, portability and existing synthetic research tests.

## Readability pass

The Research Lab now uses a shared visual system, clearer page hierarchy, glossary/reading guidance, experiment tags, stronger interpretation guardrails, improved reproduction flow, and consistent chart styling. A regression test also protects the fast repeat-launch path from dependency reinstalls.


## Research Platform v3

The repository now behaves as a small research platform rather than only a reproduction wrapper:

- deterministic no-data quick demo;
- resumable/cached 12-stage full-study reproduction;
- conceptual SVG explainer for every experiment;
- experiment-level provenance panels;
- statistical diagnostics and descriptive uncertainty views;
- machine-specific benchmarking instead of invented timing claims;
- self-contained downloadable HTML report;
- generated GitHub Pages research report;
- separate corrected/extended Research v2 methods and walk-forward runner;
- repeat-launch bootstrap reduced to a single health probe on a healthy environment.

Published v1 canonical scripts and frozen evidence remain unchanged.

Final v3 scope also includes corrected parent-paired age decay, CME-trade-date clustered CE re-inference with FDR correction, local year/sensitivity/bootstrap diagnostics, and a generated report at the end of a full reproduction.
