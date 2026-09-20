# FVG Predictive Strength — Full Chat Research & Platform Archive

**Project:** `t8pium/fvg-predictive-strength`  
**Market:** CME Micro E-mini Nasdaq-100 futures (MNQ)  
**Study period:** 2020-01-01 through 2026-07-10  
**Current validated repository state at archive time:** `1cc9d5a7f5cfcd51231bc8d351465bbbc9972431`  
**Purpose of this file:** preserve the research, engineering decisions, methodological corrections, reproducibility work, platform evolution, and new temporal findings developed through the project chat.

---

## 1. Original research question

The project began with a direct statistical question:

> Are Fair Value Gaps genuinely special price zones, or does price appear to be attracted to them mainly because nearby price levels are revisited frequently anyway?

The project deliberately moved away from the weak claim that “FVGs fill often” and toward a stricter falsification-style question:

> After controlling for distance, volatility, trend, session, time of day, ordinary price revisitation, width, and broad market state, does the **FVG label itself** add incremental predictive information?

This distinction drives the entire repository.

---

## 2. Dataset and active-contract construction

The published study uses:

- **Instrument:** CME Micro E-mini Nasdaq-100 futures (MNQ)
- **Source:** Databento `GLBX.MDP3`
- **Schema:** 1-minute OHLCV
- **Requested parent symbol:** `MNQ.FUT`
- **Study range:** 2020-01-01 through 2026-07-10
- **Active 1-minute bars:** **2,303,483**
- **Contracts represented:** **27**
- **Detected 1m FVGs:** **454,197**
- **Duplicate active timestamps:** 0
- **Missing OHLC values:** 0

The active-contract builder:

1. keeps strict quarterly MNQ outrights;
2. assigns CME trade date using the 18:00 America/New_York boundary;
3. totals volume by contract and trade date;
4. selects the highest-volume contract each trade date;
5. removes exact duplicate overlap;
6. rejects conflicting duplicate candles;
7. validates OHLC;
8. writes a versioned dataset generation;
9. switches a tiny current-dataset pointer only after a successful build.

The resulting series is not back-adjusted.

---

## 3. Mechanical FVG definition

For completed candles A = t-2, B = t-1, C = t:

- **Bullish FVG:** Low[C] > High[A]
- **Bearish FVG:** High[C] < Low[A]
- **Bullish zone:** High[A] to Low[C]
- **Bearish zone:** High[C] to Low[A]
- The FVG is considered known only after candle C closes.

The reusable detector therefore avoids future leakage in event creation.

---

## 4. Published v1 research architecture

The nine reader-facing experiments are powered by four preserved canonical analysis scripts under `src/original/`.

### Canonical computational suites

- `fvg_final_fast.py`
  - raw fill rates
  - deep matched attraction
  - distance/regime controls
  - controlled logistic model
  - chronological robustness

- `fvg_strength_one_tf.py`
  - multi-timeframe matched attraction
  - age decay
  - formation continuation
  - first-touch reaction

- `fvg_midpoint_reaction.py`
  - midpoint / Consequent Encroachment reaction tests

- `fvg_ce_rejection_study.py`
  - candle-body acceptance around CE
  - trade-like CE rejection study

These published scripts are hash-locked.

The portability runner verifies their SHA-256 hashes, rewrites only machine-specific paths in a temporary AST copy, and executes that temporary copy. The preserved source is not silently rewritten.

---

## 5. The nine published experiments

### 01 — Raw Fill Rates

Question:

> How often are FVGs revisited?

Key published result:

- 1m FVG touch within 60 minutes: **90.86%**
- eventual in-sample touch: **99.88%**

Interpretation:

Very high raw revisit probability is real, but is not evidence that the FVG label itself causes or predicts the revisit.

### 02 — Matched-Zone Attraction

Question:

> Are FVGs reached more often than comparable ordinary zones?

Deep 1m published matched excess:

- 5m: **+3.03 pp**
- 15m: **+1.45 pp**
- 30m: **+0.96 pp**
- 60m: **+0.58 pp**
- 120m: **+0.52 pp**
- 240m: **+0.25 pp**
- ~1 trading day: **~0.00 pp**
- ~3 trading days: **slightly negative**

Interpretation:

The attraction effect is real but concentrated very shortly after formation.

### 03 — FVG Age Decay

Published 1m conditional excess:

- 1→3 bars: **+3.09 pp**
- 3→5 bars: **-0.21 pp**
- 5→10 bars: **-0.08 pp**
- 10→20 bars: **-1.86 pp**

Interpretation:

Fresh gaps carry more incremental attraction information than old surviving gaps.

### 04 — Formation Continuation

Question:

> Does creation of an FVG predict continued movement in the same direction?

Published result:

Five-bar directional-return differences were small and mixed across timeframes.

Interpretation:

No stable “an FVG formed, therefore price keeps going” rule was demonstrated.

### 05 — First-Touch Retest Reaction

Question:

> Once price reaches the FVG, does it reject differently than it would at an ordinary matched zone?

Published FVG-minus-control rejection differences:

- 1m: **+2.32 pp**
- 5m: **+1.22 pp**
- 15m: **+1.41 pp**
- 1H: **+0.91 pp**
- 4H: **+1.55 pp**

Interpretation:

The most persistent property may be a small local reaction/barrier effect after contact rather than long-lived magnetism.

### 06 — Midpoint / CE

Question:

> Is the exact 50% midpoint unusually reactive?

Published matched midpoint reaction differences:

- 1m: **+0.92 pp**
- 5m: **+2.45 pp**
- 15m: **+2.64 pp**
- 1H: **+0.36 pp**
- 4H: **+4.39 pp**

Interpretation:

The result varies materially by timeframe. The strongest cell is exploratory and should not be treated as independently confirmed.

### 07 — Candle-Body Acceptance Around CE

Question:

> Does the depth of an opposite-color body close inside the gap matter?

Key exploratory result:

The highlighted 4H 45–50% depth cell had approximately:

- N = 49
- win rate ≈ **67.35%**
- mean ≈ **+0.286R**

Interpretation:

Interesting hypothesis generation, not a confirmed edge, because many timeframe/depth cells were searched and observations overlap.

### 08 — Distance, Regimes & Controlled Model

Key published result:

A 60-minute logistic model gave an FVG indicator odds ratio around **1.079** after controlling for geometry/state variables.

Distance explained much more of raw touch probability than the binary FVG label.

Interpretation:

FVG status contributes some conditional information, but geometry and market state dominate.

### 09 — Chronological Robustness

Selected early → later matched differences:

- 1m: **3.06 → 1.86 pp**
- 5m: **2.10 → 2.31 pp**
- 15m: **0.69 → 0.49 pp**
- 1H: **1.02 → -0.38 pp**
- 4H: **-0.71 → -2.09 pp**

A separate deep 1m / 60m split weakened from roughly **+0.79 pp** early to **+0.08 pp** later.

Interpretation:

Lower-timeframe short-horizon behavior survives better than higher-timeframe or long-horizon attraction.

---

## 6. Main published scientific conclusion

The strongest defensible statement is:

> FVGs are neither meaningless chart annotations nor deterministic market magnets. They show weak, short-lived, context-dependent predictive structure. The clearest attraction effect is concentrated in the first few bars after formation, while first-touch reaction appears somewhat more persistent across timeframes. The FVG label alone was not shown to be a standalone trading edge.

A better conceptual model is:

> **FVG = weak contextual marker of temporary displacement / market state, not a permanent force pulling price.**

---

## 7. Scientific limitations retained in v1

The project deliberately preserves known limitations rather than silently rewriting the published study:

1. long-horizon right-censor asymmetry in one detailed 1m comparison;
2. chronological split is not a sealed prospective pipeline holdout;
3. published age-decay controls are survivor-zone weighted rather than perfectly parent-paired;
4. some v1 cluster bootstraps use calendar date rather than CME trade date;
5. some non-CE future outcomes may span active-contract rolls;
6. overlapping observations weaken naive independence assumptions;
7. exploratory CE analysis searched multiple timeframe/depth cells.

These are documented in `docs/SCIENTIFIC_AUDIT.md`.

---

## 8. Research Platform evolution

The repository was rebuilt from a research-code archive into a local research platform.

### Windows one-click startup

`START_HERE.bat` launches `bootstrap.py`.

First launch:

- validate Python 3.11–3.13, 64-bit;
- create `.fvg_venv`;
- install pinned dependencies;
- verify environment;
- launch Streamlit.

Later launches:

- fingerprint dependency definitions;
- run a lightweight environment-health probe;
- skip pip installation when the environment is healthy;
- launch the Research Lab.

A regression test protects the fast repeat-launch path.

### Data import UX

The Research Lab supports:

- native Windows file selection;
- pasted local paths;
- browser upload fallback;
- optional Databento API download.

Supported source types include DBN, compressed DBN, Parquet, CSV variants, ZIP archives, multiple files, and directories.

### Versioned dataset generations

The project moved away from replacing a live `active_mnq.pkl` in place because Windows could hold the file open.

The current design creates immutable generations and atomically switches `current_dataset.json` only after a build completes.

This prevents the WinError 32 lock failure from corrupting or partially replacing the active dataset.

---

## 9. Research Platform v3

The major v3 platform pass added:

- results-first Research Lab homepage;
- experiment-specific charts and exact-value tables;
- visual experiment explainers;
- full experiment provenance panels;
- Quick Demo with deterministic synthetic OHLCV;
- one-click full-study reproduction;
- stage caching and resume;
- generated standalone HTML research report;
- performance benchmarks;
- diagnostics and uncertainty pages;
- separate corrected `research_v2/` layer;
- public static portfolio report;
- improved README and reading guide.

The 12-stage full reproduction includes:

- detailed 1m;
- multi-timeframe 1m, 5m, 15m, 1H, 4H;
- midpoint 1m, 5m, 15m, 1H, 4H;
- CE/body suite.

Successful stages are reused for the current dataset instead of recomputed unnecessarily.

---

## 10. Research Platform v4 audit layer

The v4 audit layer added tools designed to make the project harder to fool.

### Event Explorer

Allows visual inspection of individual FVG observations on candlestick charts with:

- formation timestamp;
- direction;
- near edge;
- far edge;
- midpoint;
- width;
- width/ATR;
- starting distance/ATR;
- session;
- future touch outcome;
- surrounding candles;
- optional matched controls.

### Placebo / negative-control suite

Tests deliberately broken constructions such as:

- ordinary state-matched zones;
- shuffled geometry;
- mirrored direction;
- time-shifted geometry.

Purpose:

> If nonsense labels produce persistent “edge,” the research pipeline itself may be generating false discoveries.

### Matching ablations

Removes matching dimensions one at a time, including session, time-of-day, volatility, and trend, while attempting to hold parent-event population fixed.

Purpose:

> Determine which control assumptions actually explain the measured FVG effect.

### Statistical power / MDE

Calculates minimum detectable probability or mean-R effects under explicit sample size and design-effect assumptions.

Purpose:

> Distinguish “probably tiny effect” from “insufficient power.”

### Hypothesis registry / preregistration

Research v2 supports append-only JSON hypotheses with SHA-256 locking.

A hypothesis can define:

- dataset window;
- primary outcome;
- timeframe;
- filters;
- horizon;
- expected direction;
- statistic;
- correction family;
- status.

Purpose:

> Separate confirmatory tests from ideas discovered after inspecting results.

### Golden mini-dataset

A permanent deterministic synthetic OHLCV fixture with expected detector output and a fixed file hash is tested in CI.

Purpose:

> Detect accidental changes to detector mechanics.

### Standard run provenance

Run capsules can record:

- git commit;
- Python version;
- OS;
- dependency fingerprint;
- exact command;
- seed;
- start/end time;
- input file hashes;
- output file hashes;
- dataset metadata;
- warnings.

### Dataset preflight

Inspects a source before full import and reports file/archive structure, schema, OHLCV availability, DBN metadata, symbol hints, and likely MNQ coverage.

### Stability Atlas

Brings together effect estimates across:

- timeframe;
- horizon;
- chronology;
- distance;
- year;
- volatility;
- sensitivity thresholds.

### Economic significance

Trade-like CE outputs can be evaluated under explicit MNQ commission/slippage/risk assumptions.

Ordinary fill probabilities are intentionally not converted into fake PnL.

### v1 → v2 comparison

Corrected v2 outputs can be displayed beside published v1 values with the methodological reason for each change.

### Release packaging

The repository supports clean versioned release packages containing:

- project ZIP;
- standalone HTML report;
- SHA-256 checksums;
- release metadata;

while excluding local licensed data, local results, environments, caches, and secrets.

---

## 11. Research v2 corrected / extended methods

The separate v2 layer avoids rewriting published v1 history.

Implemented improvements include:

- symmetric full-horizon eligibility;
- active-contract-boundary censoring;
- parent-paired age-decay controls;
- CME trade-date cluster bootstrap;
- controls built inside test periods;
- repeated walk-forward validation;
- Benjamini-Hochberg FDR correction;
- CE/body re-inference using canonical trade rows but stronger uncertainty/multiplicity treatment.

Current study families include:

- `attraction-1m`
- `age-decay-1m`
- `walk-forward-1m`
- `ce-reinfer`
- placebo studies
- ablation studies

All v2 results are explicitly **NEW / UNPUBLISHED RESEARCH** until run on licensed history and reviewed.

---

## 12. UI readability repair

The local Research Lab was audited after screenshots showed two serious presentation problems:

1. low-contrast text/background combinations;
2. custom HTML appearing literally as `<div ...>` code text.

The fix:

- explicit high-contrast dark palette;
- compact single-line custom HTML rendering;
- fixed Streamlit dark theme;
- readable warning/info/success callouts;
- readable metrics/tabs/buttons/sidebar/code blocks;
- WCAG-AA contrast regression tests;
- raw-HTML rendering regression tests.

The validated state at archive time passed **72 tests** across:

- Ubuntu Python 3.11;
- Ubuntu Python 3.13;
- Windows Python 3.12.

---

## 13. New temporal attraction / reaction regime study

A new extension was run on the same MNQ history to answer:

> When do FVGs act more strongly as attraction zones, and when do they act more strongly as rejection/reaction zones?

This study is **not part of the frozen published v1 metrics** and should be treated as a newer exploratory/extended analysis.

Definitions:

- **Attraction:** price reaches the FVG near edge within 60 minutes.
- **Reaction / rejection:** after first touch, price moves one full gap-width away before traversing the far edge within the canonical reaction race.
- **3-bar reaction:** normalized movement away from the FVG three bars after first touch.

The temporal matched sample used approximately:

- **150,000 eligible 1m FVG parents**
- **449,640 ordinary matched controls**

Controls were restricted by calendar month, session, hour, volatility regime, and trend regime while copying normalized distance and width.

### Overall temporal-study result

- FVG 60m near-edge attraction: **90.98%**
- control attraction: **89.93%**
- excess attraction: **+1.05 pp**

- FVG first-touch rejection: **52.66%**
- control rejection: **50.93%**
- excess rejection: **+1.93 pp**

- 3-bar movement away:
  - FVG: **+0.020 ATR**
  - control: **-0.007 ATR**
  - excess: **+0.032 ATR**

Approximate date-clustered 95% intervals:

- attraction premium: **+0.88 to +1.22 pp**
- rejection premium: **+1.51 to +2.35 pp**
- 3-bar reaction premium: **+0.021 to +0.043 ATR**

### Main temporal discovery

Attraction and rejection behave differently.

**Attraction is more regime-dependent.**  
**Rejection is smaller but more temporally stable.**

Broad heterogeneity tests indicated:

- attraction varies materially by year;
- attraction varies materially by session;
- attraction varies materially by quarter;
- rejection did not show equally strong year/month/session/weekday heterogeneity.

### Attraction by year

Matched 60-minute attraction premium:

- 2020: **+1.56 pp**
- 2021: **+1.35 pp**
- 2022: **+0.44 pp**
- 2023: **+1.18 pp**
- 2024: **+1.28 pp**
- 2025: **+0.44 pp**
- 2026 through July 10: **+1.08 pp**

There is no evidence that FVG attraction suddenly started working recently.

Era comparison:

- 2020–2022: **+1.12 pp**
- 2023–2024: **+1.23 pp**
- 2025–2026: **+0.66 pp**

This suggests recent attraction has, if anything, weakened somewhat.

### Rejection by year

Matched first-touch rejection premiums were roughly:

- 2020: **+2.97 pp**
- 2021: **+1.78 pp**
- 2022: **+1.52 pp**
- 2023: **+1.26 pp**
- 2024: **+2.07 pp**
- 2025: **+1.60 pp**
- 2026 through July 10: **+2.62 pp**

The broad year-to-year rejection variation was not statistically strong enough to support a robust yearly regime claim.

### Formation session and attraction

Approximate matched attraction premiums by FVG formation session:

- Asia: **+1.28 pp**
- London: **+1.15 pp**
- NY premarket: **+0.19 pp**
- NY AM: **+0.68 pp**
- NY lunch: **+0.71 pp**
- NY PM: **+0.91 pp**
- Post-market: **+1.67 pp**

The key lesson is NY premarket:

Raw touch probability was very high, but the matched premium was near zero.

This shows why raw fill rate is not enough: ordinary nearby zones are also revisited at very high rates in that environment.

### Actual touch session and rejection

Descriptive matched rejection premiums by the session when price first entered the zone:

- NY premarket: **+2.97 pp**
- Asia: **+2.43 pp**
- London: **+2.34 pp**
- NY lunch: **+1.73 pp**
- NY PM: **+1.33 pp**
- Post-market: **+1.28 pp**
- NY AM: **+0.99 pp**

The ranking is interesting, but broad session heterogeneity for rejection was not strong enough to establish a reliable session rule.

### Hour-of-day reaction candidates

Descriptively stronger ET touch hours included:

- 02:00: **+4.51 pp**
- 19:00: **+4.15 pp**
- 21:00: **+3.10 pp**
- 09:00: **+3.07 pp**
- 04:00: **+2.89 pp**

Weaker ET touch hours included:

- 15:00: **+0.48 pp**
- 22:00: **+0.89 pp**
- 10:00: **+0.93 pp**
- 11:00: **+1.10 pp**

The overall hourly heterogeneity test was not strong enough to call these established trading windows.

### Calendar month

No convincing recurring January-vs-February-vs-etc seasonality was established.

Some individual months looked stronger, but the overall month effect was not robust.

### Specific historical month regimes

Stronger attraction episodes included:

- April 2020: **+2.71 pp**
- August 2021: **+2.68 pp**
- March 2020: **+2.58 pp**
- September 2021: **+2.54 pp**
- June 2024: **+2.48 pp**
- December 2020: **+2.32 pp**
- January 2023: **+2.11 pp**

These findings support the idea that attraction comes in episodic market regimes rather than a fixed calendar schedule.

### Quarter regimes

Examples:

- 2021 Q3: **+2.16 pp**
- 2024 Q2: **+1.83 pp**
- 2020 Q2: **+1.81 pp**
- 2025 Q1: **+0.25 pp**
- 2022 Q2: **+0.23 pp**
- 2025 Q2: **-0.31 pp**

Entire multi-month regimes can therefore show strong, weak, or absent FVG-specific attraction.

### Weekday

No convincing weekday rejection effect was found.

Attraction showed only weak evidence of weekday heterogeneity.

Conclusion:

Do not build a “Tuesday FVG” rule from this dataset.

### Individual weeks / days

Large short-lived spikes exist.

Examples of extreme historical attraction/reaction weeks or days can be much larger than the long-run +1–2 pp effect, including both strongly positive and strongly negative periods.

Interpretation:

These extremes are evidence of regime dependence, not evidence that the same calendar week/day will repeat next year.

### Timeframe remains one of the strongest timing variables

Published five-native-bar attraction premium:

- 1m: **+2.70 pp**
- 5m: **+2.16 pp**
- 15m: **+0.63 pp**
- 1H: **+0.60 pp**
- 4H: **-1.13 pp**

By contrast, first-touch rejection stayed modestly positive across all tested native timeframes.

This reinforces a two-part model:

1. attraction is short-lived and strongly lower-timeframe dependent;
2. reaction after contact is smaller but more persistent.

---

## 14. Best current synthesis

The full project now supports the following interpretation:

### Attraction

FVGs have a small extra tendency to be revisited relative to comparable ordinary zones.

That extra attraction:

- is strongest immediately after formation;
- is strongest on low timeframes;
- varies by year/quarter/session;
- weakens toward zero at long horizons;
- may have weakened somewhat in recent years;
- is not well explained by simple recurring weekday/month seasonality.

### Reaction / rejection

Once price actually enters an FVG, there is a small extra probability of rejecting compared with a comparable ordinary zone.

That reaction effect:

- is roughly on the order of 1–2 pp long-run;
- is more stable through time than attraction;
- persists across tested native timeframes;
- shows interesting session/hour rankings, but not yet robust enough to justify fixed time-of-day trading rules.

### Practical research hierarchy

The strongest conditioning variables are currently:

1. **FVG age / freshness**
2. **native chart timeframe**
3. **current market regime / year / quarter**
4. **session**
5. hour of day as exploratory
6. calendar month / weekday as weak
7. isolated day/week spikes as descriptive regime evidence only

---

## 15. What the repository deliberately does not claim

The project does not claim:

- every FVG is a magnet;
- every FVG rejects;
- FVGs are useless;
- the FVG label alone is profitable;
- a 4H CE subgroup is a confirmed edge;
- specific weekday/hour effects are production-ready.

The project separates:

- statistical predictability;
- causal interpretation;
- economic tradability.

---

## 16. Recommended next empirical work

The next high-value work is no longer generic UI expansion.

It is:

1. run all Research v2 corrected studies on the full licensed MNQ history;
2. run the placebo suite at scale;
3. run matching ablations at scale;
4. preregister the strongest temporal hypotheses;
5. test session/hour findings prospectively or on a sealed later period;
6. compare published v1 versus corrected v2;
7. extend the same methodology to NQ, ES/MES, BTC/ETH, and possibly other liquid markets;
8. test whether FVG adds predictive value inside a larger multivariate model rather than as a standalone rule.

---

## 17. Reproducibility state

At the time this archive was created:

- current validated repository commit: `1cc9d5a7f5cfcd51231bc8d351465bbbc9972431`;
- configured validation passed on Windows Python 3.12, Ubuntu Python 3.11, and Ubuntu Python 3.13;
- the test suite had reached **72 tests**;
- the published v1 source remained hash-locked;
- licensed market data remained excluded from the public repository.

---

## 18. Public artifacts

- Repository: https://github.com/t8pium/fvg-predictive-strength
- Generated static report: https://t8pium.github.io/fvg-predictive-strength/
- Portfolio project page: https://t8pium.github.io/projects/fvg-predictive-strength/

This file is the consolidated technical/research archive for the work developed through the project conversation.

---

## 19. Exact temporal heterogeneity / anomaly results archived from the project chat

The final temporal pass added exact diagnostics beyond the high-level regime summary.

### Broad heterogeneity

Approximate p-values for matched-premium variation:

- **Year:** attraction 0.0004; rejection 0.29
- **Calendar month:** attraction 0.82; rejection 0.16
- **Weekday:** attraction 0.10; rejection 0.92
- **Session:** attraction 0.014; rejection 0.79
- **Hour:** attraction 0.10; rejection 0.46
- **Quarter:** attraction 0.019; rejection 0.28
- **Week of year:** attraction 0.31; rejection 0.11

This is one of the cleanest distinctions in the entire project: **attraction is regime-sensitive, while rejection is relatively temporally stable.**

### Monthly time trend

- attraction premium: **r ≈ -0.23**
- rejection premium: **r ≈ -0.12**
- 3-bar reaction magnitude: **r ≈ -0.25**

The project therefore found no “FVGs only became effective recently” story.

### Extreme diagnostic weeks

- week of 2024-01-08: attraction **+6.17 pp**
- week of 2020-10-12: attraction **-4.37 pp**
- week of 2020-05-18: rejection **+14.8 pp**
- week of 2022-08-08: rejection **-14.5 pp**

### Extreme raw days

Attraction:
- 2026-07-03: **97.44%**
- 2021-02-15: **97.27%**
- 2023-12-26: **97.06%**
- 2020-10-12: **82.16%**
- 2022-07-05: **82.46%**
- 2021-12-16: **83.64%**

Rejection:
- 2022-05-17: **68.61%**
- 2023-11-24: **38.46%**

### Day-of-month exploratory anomaly

Matched rejection premium:
- 6th: **+3.80 pp**
- 15th: **+5.92 pp**
- 23rd: **+4.47 pp**
- 26th: **+4.48 pp**

These are archived as hypothesis-generation results only. They should not be turned into calendar trading rules without preregistered replication.

### Final research hierarchy from the complete chat

The complete body of work ranks the “when does an FVG matter?” variables approximately as:

1. **FVG age / freshness**
2. **native timeframe**
3. **market regime / quarter / year**
4. **session**
5. hour of day as exploratory
6. recurring calendar month / weekday as weak
7. isolated day/week/day-of-month spikes as regime diagnostics only

The machine-readable version of these findings lives in `research_v2/findings/temporal_attraction_reaction_2026-09-20.json`.
