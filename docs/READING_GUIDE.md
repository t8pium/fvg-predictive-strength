# How to read the FVG Predictive Strength study

This guide is for readers who want to understand the project before reading the code.

## Start with the research question

The study does **not** ask whether Fair Value Gaps are common, whether traders use them, or whether price often revisits them.

It asks a stricter question:

> After controlling for obvious factors such as distance, volatility, trend, session and ordinary price revisitation, does the **FVG label itself** add useful predictive information?

That distinction matters because a zone can be revisited frequently without being special.

## Read the experiments in this order

1. **Raw Fill Rates** — establishes the descriptive baseline.
2. **Matched-Zone Attraction** — compares FVGs with ordinary zones of similar geometry and broad market state.
3. **FVG Age Decay** — asks whether the effect persists as an unfilled gap gets older.
4. **Formation Continuation** — tests whether the move that created the FVG predicts continuation.
5. **First-Touch Retest Reaction** — tests the reaction after price reaches the gap.
6. **Midpoint / CE** — tests whether the exact 50% level behaves differently.
7. **Candle-Body Acceptance Around CE** — studies close depth and a trade-like rejection definition.
8. **Distance, Regimes & Controlled Model** — checks whether the FVG label survives explicit controls.
9. **Chronological Robustness** — compares earlier and later samples.

## Terms

### FVG

A mechanically detected three-candle Fair Value Gap. The code defines the geometry explicitly; the study does not rely on discretionary chart marking.

### Matched control

A non-FVG comparison zone. It is built to resemble a real FVG in direction, normalized width, normalized starting distance and broad market state.

A matched control is important because the raw fact that "price returned to this area" is not enough to show that the FVG label caused or predicted the return.

### Percentage point (pp)

A difference between two probabilities.

Example:

- FVG touch rate = 90.86%
- control touch rate = 90.28%
- difference = **+0.58 percentage points**

That is not the same as saying the probability increased by 0.58% relative.

### ATR

Average True Range. The study uses ATR normalization so a five-point gap in a quiet market is not treated as equivalent to a five-point gap in a very volatile market.

### CE / midpoint

Consequent Encroachment, the exact 50% level of the FVG.

### Chronological split

The sample is divided by time rather than shuffled randomly. This is useful for market data because relationships can change across regimes.

## How to interpret a large raw fill rate

A raw fill rate answers:

> How often did price revisit this FVG?

It does **not** answer:

> Was price more likely to revisit this zone because it was an FVG?

The matched-control experiments are designed to address the second question more directly.

## How to interpret a positive FVG-minus-control difference

A positive difference means the real FVG was reached more often than its matched controls under the experiment's construction.

It does not automatically imply:

- causality,
- profitability after costs,
- a stable trading edge,
- persistence in future data,
- independence from unmeasured market structure.

The robustness and regime experiments exist because the effect can be small or unstable.

## Published reference vs local reproduction

The Research Lab deliberately separates two concepts.

### Published reference

Frozen values in `reference_results/reference_metrics.json`.

These are visible immediately and are the evidence presented by the project.

### Local reproduction

Values generated on your machine from your own licensed input.

A local match means your environment reproduced the published calculation within the declared tolerance. It does not mean the effect is a universal market law.

## Why some limitations were not "fixed"

The files under `src/original/` are preserved analysis scripts. Some known methodological limitations remain because silently changing them would create a different study while still presenting the old published numbers.

Those issues are documented in `docs/SCIENTIFIC_AUDIT.md`.

A future corrected or extended study should be versioned as new research rather than rewriting the historical analysis invisibly.

## Suggested reading path

If you have five minutes:

1. README
2. Research Lab home page
3. Matched-Zone Attraction
4. Chronological Robustness

If you want the full technical audit:

1. `docs/EXPERIMENTS.md`
2. `docs/SCIENTIFIC_AUDIT.md`
3. `reference_results/manifest.json`
4. the four files in `src/original/`
