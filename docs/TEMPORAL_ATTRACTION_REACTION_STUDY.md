# Temporal Attraction, Reaction & Rejection Study

**Status:** exploratory / extended research, not part of the frozen published v1 metrics  
**Market:** MNQ  
**Base dataset:** same active-contract history used by the main study  
**Period:** 2020-01-01 through 2026-07-10

## Research question

When do FVGs appear to contain more predictive information?

This extension separates two distinct ideas:

1. **Attraction** — after an FVG forms, is price more likely to reach the zone than an ordinary comparable zone?
2. **Reaction / rejection** — after price enters an FVG, is it more likely to move back away from the zone before traversing through it?

The study then asks whether these effects vary by:

- year;
- quarter;
- calendar month;
- weekday;
- week of year;
- session;
- hour of day;
- individual month/week/day regimes;
- native chart timeframe;
- age since FVG formation.

All intraday time references use **America/New_York / ET**.

---

## Outcome definitions

### Attraction

A real FVG or matched ordinary zone is counted as attracted/touched when price reaches the zone's near edge within the 60-minute horizon.

### Rejection

After first touch, the reaction race asks whether price moves one full gap-width back away from the zone before traversing the far edge.

### Three-bar reaction

Normalized movement away from the zone three bars after first touch, measured in ATR units.

---

## Matching design

The temporal extension used approximately:

- **150,000 eligible 1m FVG parents**
- **449,640 matched ordinary control zones**

Controls were restricted by:

- calendar month;
- session;
- hour;
- volatility regime;
- trend regime;

while preserving normalized width and starting distance.

The purpose is to prevent an apparent “time effect” from simply reflecting that the controls came from a different market environment.

---

## Overall result

| Outcome | FVG | Matched control | Difference |
|---|---:|---:|---:|
| 60m near-edge attraction | **90.98%** | 89.93% | **+1.05 pp** |
| First-touch rejection | **52.66%** | 50.93% | **+1.93 pp** |
| 3-bar move away | **+0.020 ATR** | -0.007 ATR | **+0.032 ATR** |

Approximate date-clustered 95% intervals:

- attraction premium: **+0.88 to +1.22 pp**
- rejection premium: **+1.51 to +2.35 pp**
- 3-bar reaction premium: **+0.021 to +0.043 ATR**

The central result is therefore not that FVGs produce a huge deterministic effect.

It is that:

> the FVG label appears to add a small amount of incremental information both before touch and after touch.

---

## Attraction is more regime-dependent than rejection

Broad temporal heterogeneity:

| Dimension | Attraction | Rejection |
|---|---|---|
| Year | materially different | not strongly different |
| Calendar month | weak / no broad effect | weak / no broad effect |
| Weekday | weak | very weak |
| Session | materially different | weak |
| Hour | suggestive, not robust | suggestive, not robust |
| Quarter | materially different | weak |

The best summary is:

> **Attraction changes with regime. Rejection is smaller but more stable.**

---

## Year-by-year attraction

| Year | Matched 60m attraction premium |
|---:|---:|
| 2020 | **+1.56 pp** |
| 2021 | **+1.35 pp** |
| 2022 | **+0.44 pp** |
| 2023 | **+1.18 pp** |
| 2024 | **+1.28 pp** |
| 2025 | **+0.44 pp** |
| 2026* | **+1.08 pp** |

*2026 through July 10.

Era averages:

- 2020–2022: **+1.12 pp**
- 2023–2024: **+1.23 pp**
- 2025–2026: **+0.66 pp**

There is no evidence that FVG attraction recently “started working.”

If anything, the incremental attraction premium has weakened somewhat in the latest era.

---

## Year-by-year rejection

| Year | FVG rejection | Control | Premium |
|---:|---:|---:|---:|
| 2020 | 53.10% | 50.49% | **+2.97 pp** |
| 2021 | 52.03% | 50.01% | +1.78 pp |
| 2022 | 52.61% | 50.92% | +1.52 pp |
| 2023 | 52.08% | 51.01% | +1.26 pp |
| 2024 | 52.48% | 51.18% | +2.07 pp |
| 2025 | 53.07% | 51.70% | +1.60 pp |
| 2026* | 53.90% | 51.51% | **+2.62 pp** |

The broad year-to-year rejection difference was not strong enough to establish a reliable yearly rejection regime.

---

## Formation session and attraction

| Formation session | Raw FVG 60m touch | Matched premium |
|---|---:|---:|
| Asia | 91.17% | **+1.28 pp** |
| London | 91.31% | **+1.15 pp** |
| NY premarket | **93.88%** | **+0.19 pp** |
| NY AM | 88.65% | +0.68 pp |
| NY lunch | 90.12% | +0.71 pp |
| NY PM | 90.04% | +0.91 pp |
| Post-market | 91.75% | **+1.67 pp** |

The most important observation is NY premarket.

Premarket FVGs have a very high raw touch rate, but ordinary matched zones do too.

So the raw number exaggerates the FVG-specific effect.

---

## Actual touch session and rejection

Descriptive matched rejection premiums:

| Touch session | Rejection premium |
|---|---:|
| NY premarket | **+2.97 pp** |
| Asia | **+2.43 pp** |
| London | **+2.34 pp** |
| NY lunch | +1.73 pp |
| NY PM | +1.33 pp |
| Post-market | +1.28 pp |
| NY AM | **+0.99 pp** |

The ordering is interesting, but broad session heterogeneity for rejection was not strong enough to convert this into a fixed production rule.

---

## Hour-of-day candidates

Descriptively stronger ET reaction hours:

- **02:00**: +4.51 pp
- **19:00**: +4.15 pp
- **21:00**: +3.10 pp
- **09:00**: +3.07 pp
- **04:00**: +2.89 pp

Descriptively weaker ET reaction hours:

- **15:00**: +0.48 pp
- **22:00**: +0.89 pp
- **10:00**: +0.93 pp
- **11:00**: +1.10 pp
- **03:00**: +1.13 pp
- **05:00**: +1.13 pp

These are exploratory candidates only.

The overall hour-of-day heterogeneity evidence was not strong enough to establish a reliable fixed-hour edge.

---

## Calendar month

No convincing recurring calendar-month seasonality was established.

Some months looked stronger than others, but the overall January-through-December variation was not robust.

Do not interpret this study as evidence for an “April FVG strategy.”

---

## Historical month regimes

Some specific year-month periods did show substantially stronger attraction premiums:

- **April 2020:** +2.71 pp
- **August 2021:** +2.68 pp
- **March 2020:** +2.58 pp
- **September 2021:** +2.54 pp
- **June 2024:** +2.48 pp
- **December 2020:** +2.32 pp
- **January 2023:** +2.11 pp

This supports episodic regime dependence rather than stable calendar seasonality.

---

## Quarter regimes

Examples:

- **2021 Q3:** +2.16 pp
- **2024 Q2:** +1.83 pp
- **2020 Q2:** +1.81 pp
- **2025 Q1:** +0.25 pp
- **2022 Q2:** +0.23 pp
- **2025 Q2:** -0.31 pp

The FVG-specific attraction premium can therefore be strong, weak, or absent for entire multi-month regimes.

---

## Weekday

The dataset does not show a convincing weekday-specific rejection effect.

Attraction shows only weak weekday heterogeneity.

This is not evidence for rules such as:

- “Tuesday FVGs work best”
- “Friday FVGs fail”
- “Sunday is structurally special”

---

## Individual weeks and days

Short-lived extremes exist and can be much larger than the long-run average.

Examples observed in the broader temporal scan include both strongly positive and strongly negative weeks/days.

Interpretation:

> Individual spikes are evidence that FVG behavior is regime-sensitive, not evidence that the same calendar date will repeat predictably in future years.

---

## Native chart timeframe

The already-published matched five-native-bar attraction premium:

| Timeframe | Attraction premium |
|---|---:|
| 1m | **+2.70 pp** |
| 5m | **+2.16 pp** |
| 15m | +0.63 pp |
| 1H | +0.60 pp |
| 4H | **-1.13 pp** |

This is one of the clearest results in the project.

The attraction/magnet component is primarily a lower-timeframe phenomenon.

---

## Reaction by timeframe

Published first-touch rejection premium:

| Timeframe | Rejection premium |
|---|---:|
| 1m | **+2.32 pp** |
| 5m | +1.22 pp |
| 15m | +1.41 pp |
| 1H | +0.91 pp |
| 4H | +1.55 pp |

Unlike attraction, the reaction effect does not collapse monotonically as native timeframe rises.

---

## Age since formation

The strongest temporal variable remains FVG age.

Published 1m conditional attraction premium:

| Age window | Incremental attraction |
|---|---:|
| 1→3 bars | **+3.09 pp** |
| 3→5 bars | -0.21 pp |
| 5→10 bars | -0.08 pp |
| 10→20 bars | **-1.86 pp** |

This is the cleanest “when” result:

> If an FVG contains unusual attraction information, that information is concentrated very soon after formation.

Old untouched FVGs do not become progressively stronger magnets.

---

## Best current model

The data is more consistent with two different behaviors than one universal FVG effect.

### Attraction

- short-lived;
- strongest on 1m/5m;
- strongest immediately after formation;
- varies by regime/year/quarter/session;
- near zero at long horizons;
- has not strengthened monotonically over recent years.

### Reaction

- smaller in magnitude;
- roughly +1–2 pp long-run;
- relatively stable through time;
- persists across native timeframes;
- may vary descriptively by session/hour, but not robustly enough yet for fixed time filters.

---

## Research priority going forward

The strongest conditioning variables are:

1. FVG age / freshness;
2. native chart timeframe;
3. current regime / year / quarter;
4. session;
5. hour as exploratory;
6. weekday/month as weak;
7. individual day/week spikes as regime diagnostics, not recurring calendar rules.

The next proper test should preregister the strongest session/hour hypotheses and test them on sealed later data or another market.

---

## Exact heterogeneity tests and anomaly scan

The broader temporal scan also quantified whether the matched FVG premium changes systematically across calendar/time buckets. These values are **exploratory diagnostics** and should not be treated as production filters without preregistration and later-data replication.

Approximate heterogeneity p-values:

| Dimension | Attraction | Rejection |
|---|---:|---:|
| Year | **0.0004** | 0.29 |
| Calendar month | 0.82 | 0.16 |
| Weekday | 0.10 | 0.92 |
| Session | **0.014** | 0.79 |
| Hour of day | 0.10 | 0.46 |
| Quarter | **0.019** | 0.28 |
| ISO week of year | 0.31 | 0.11 |

This strengthens the main interpretation: **attraction varies materially with regime; rejection is much more stable across ordinary calendar partitions.**

### Trend through time

Using monthly matched observations:

- attraction premium vs time: **Pearson r ≈ -0.23**
- rejection premium vs time: **r ≈ -0.12**
- 3-bar reaction magnitude vs time: **r ≈ -0.25**

There is therefore no evidence that FVGs only began to work recently. The attraction component has, if anything, drifted somewhat weaker over the sample.

### Extreme historical weeks

Examples from the diagnostic scan:

- attraction high: week of **2024-01-08 → +6.17 pp**
- attraction low: week of **2020-10-12 → -4.37 pp**
- rejection high: week of **2020-05-18 → +14.8 pp**
- rejection low: week of **2022-08-08 → -14.5 pp**

These swings are much larger than the long-run mean, but they do **not** recur reliably by calendar week. They are better interpreted as market-regime episodes.

### Extreme raw days

Raw 60-minute attraction examples:

- **2026-07-03:** 97.44%
- **2021-02-15:** 97.27%
- **2023-12-26:** 97.06%
- **2020-10-12:** 82.16%
- **2022-07-05:** 82.46%
- **2021-12-16:** 83.64%

Raw first-touch rejection examples:

- **2022-05-17:** 68.61%
- **2023-11-24:** 38.46%

These observations show how violently FVG behavior can vary on individual days. They are **descriptive regime diagnostics**, not evidence that those calendar dates should repeat.

### Day-of-month anomaly

An exploratory grouping by day number of the month produced unusually positive rejection premiums on:

- 6th: **+3.80 pp**
- 15th: **+5.92 pp**
- 23rd: **+4.47 pp**
- 26th: **+4.48 pp**

This is intentionally not promoted as a trading rule. There is no established causal reason the calendar day itself should matter; it may proxy recurring macro, expiry, options, or liquidity conditions. Any further use should be preregistered.

### Multiple-comparison caution

Some specific historical attraction months survived an approximate FDR screen, while the strongest reaction-month cells did not survive the same screen. Exact hour/week/day extremes face even greater data-mining risk.

The proper hierarchy remains:

1. freshness / age;
2. native timeframe;
3. regime / quarter / year;
4. session;
5. hour as exploratory;
6. weekday/month as weak;
7. isolated day/week/day-of-month effects as hypothesis generation only.
