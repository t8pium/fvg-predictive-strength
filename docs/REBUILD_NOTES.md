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
