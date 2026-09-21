# Public Nasdaq FVG replication — NSX/USD 2010–2026

This track repeats the project's FVG falsification workflow on the free HistData **NSX/USD** one-minute history so the underlying data can be distributed separately from the licensed CME MNQ study and inspected by anyone.

## Why this is a separate research track

The original project uses actual CME MNQ futures and therefore has stronger futures-specific market fidelity, but that licensed vendor history cannot be redistributed.

The public track uses a much longer, freely obtainable Nasdaq-100 index-style quote feed:

- source: HistData NSX/USD Generic ASCII M1;
- merged history observed in the project: 5,046,180 rows;
- source clock: fixed EST (UTC-05:00), without daylight-saving adjustment;
- observed range: 2010-11-14 through 2026-09-11;
- volume: not usable as centralized exchange volume;
- no futures contract identifiers or roll boundaries.

The public track therefore answers **price-pattern robustness** questions. It does not create futures-specific evidence about NQ/MNQ execution, exchange volume, contract rolls, slippage or tick mechanics.

## What has been recreated

The Research Lab now has a parallel public-data workflow:

1. **Public data setup** — install the GitHub Release asset or prepare the merged CSV.
2. **Full dataset audit** — timestamps, ordering, duplicate bars, OHLC geometry, numeric integrity, gaps, year coverage and volume availability.
3. **Timezone normalization** — fixed EST is localized to UTC-05:00 and then converted to UTC/New York correctly.
4. **Live data explorer** — query the Parquet directly with DuckDB, resample 1m/5m/15m/1H/4H and overlay mechanically detected FVGs.
5. **Public experiment lab** — rerun any of the nine reader-facing experiment families on NSX/USD and inspect its CSV/JSON outputs immediately.
6. **Full public reproduction** — a resume-safe 12-stage orchestrator repeats the same four preserved computational suites across the published timeframes.
7. **Machine-readable summary** — generated from the actual public-run outputs rather than manually typed statistics.
8. **Public static report** — generated from the public summary.
9. **MNQ separation** — every output stays under `results/public_nsx/`; frozen MNQ evidence is never overwritten.

## Dataset distribution

The merged CSV is about 365 MB, which is too large for a normal Git object. GitHub blocks individual regular-repository files above 100 MiB, so the public history is packaged as a **GitHub Release asset** instead of polluting Git history.

Build the release asset from the merged CSV:

~~~bash
python scripts/package_public_nsx.py --input "C:\path\to\NSXUSD_M1_ALL.csv"
~~~

Output:

~~~text
dist/public_nsx/
├── NSXUSD_M1_PUBLIC.zip
├── NSXUSD_M1_PUBLIC.sha256
└── prepared/
    ├── nsxusd_1m.parquet
    ├── audit.json
    ├── annual_coverage.csv
    ├── manifest.json
    └── PUBLIC_DATA_MANIFEST.json
~~~

Upload `NSXUSD_M1_PUBLIC.zip` to a GitHub Release with that exact filename. The app and installer use:

~~~text
https://github.com/t8pium/fvg-predictive-strength/releases/latest/download/NSXUSD_M1_PUBLIC.zip
~~~

The installed pickle is rebuilt locally from Parquet so the release does not need to contain two full copies of the same data.

## One-click full replication

After installing/preparing the data:

~~~bash
python scripts/reproduce_public_nsx.py
~~~

The stages are:

- detailed 1m;
- multi-timeframe at 1m, 5m, 15m, 1H and 4H;
- midpoint at 1m, 5m, 15m, 1H and 4H;
- CE/body execution study from 1m through 1D.

Resume behavior uses the same run manifests as the MNQ platform. Completed stages are skipped when the dataset file has not changed.

Use `--force` to rerun all stages or `--skip-ce` for a faster first pass.

## Public output tree

~~~text
results/public_nsx/
├── detailed_1m/
├── multi_tf/
├── midpoint/
├── ce_body/
├── _runs/
├── _full_reproduction/
└── public_summary.json
~~~

Generate the static public-replication report:

~~~bash
python scripts/generate_public_nsx_report.py
~~~

## Scientific caution

The preserved v1 scripts were written around MNQ. Most of the attraction/reaction logic is price-based and portable, but some outputs remain futures-specific in their original naming or assumptions. In particular, the CE/body study contains a 0.25-point minimum-gap/tick convention inherited from MNQ.

For that reason:

- treat this track as **replication/discovery**, not a silent replacement for MNQ;
- keep price-based probability/reaction results separate from futures execution claims;
- do not use zero HistData volume as a market feature;
- confirm anything economically important on proper CME NQ/MNQ data.

The long-history public track is valuable precisely because it can falsify results across many more regimes. It is not valuable because it makes the proxy feed equivalent to CME futures.
