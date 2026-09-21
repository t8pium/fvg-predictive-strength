# HistData NSX/USD workflow — long-history discovery dataset

This repository can prepare the free HistData **NSX/USD** Generic ASCII M1 export as a separate, schema-compatible research dataset.

This workflow is intentionally isolated from the published MNQ evidence.

## What this dataset is

HistData labels NSX/USD as a NASDAQ-100 feed. It is useful for long-history price-pattern discovery and cross-market robustness work, but it is **not CME NQ or MNQ futures data**.

Important differences:

- no CME futures contract identifiers;
- no futures roll boundaries;
- no centralized futures volume;
- HistData timestamps are documented as fixed EST (UTC-05:00) without daylight-saving adjustment;
- the published v1 canonical code contains some MNQ-specific assumptions, including a 0.25-point tick in sensitivity calculations.

Therefore results from this source must be labeled **external index-proxy / discovery research** and validated on CME NQ/MNQ before making futures-specific claims.

## Prepare and audit the merged CSV

After using the HistData downloader, point the repository at the merged file:

~~~bash
python scripts/prepare_histdata_nsx.py --input "C:\\path\\to\\NSXUSD_M1_ALL.csv"
~~~

Default output:

~~~text
data/external/nsxusd/
├── active_nsxusd.pkl
├── nsxusd_1m.parquet
├── audit.json
├── annual_coverage.csv
└── manifest.json
~~~

The preparation step performs a complete pass over the CSV and blocks dataset creation when it finds:

- malformed timestamps;
- non-numeric or missing OHLCV fields;
- impossible OHLC geometry;
- non-positive prices;
- duplicate adjacent timestamps;
- out-of-order timestamps;
- non-minute-aligned timestamps.

It also records gap counts, the largest timestamp gaps, annual row counts, and whether any non-zero volume exists.

## Timezone handling

The source clock is treated as a **fixed UTC-05:00 offset**, not America/New_York.

For example:

~~~text
HistData source: 2024-07-01 08:30 fixed EST
UTC:             2024-07-01 13:30
New York clock:  2024-07-01 09:30 EDT
~~~

That conversion is important. Treating the source timestamp directly as America/New_York would shift summer sessions incorrectly.

## Run a canonical experiment without touching published MNQ results

scripts/run_original.py accepts a schema-compatible external pickle through --data.

~~~bash
python scripts/run_original.py detailed-1m \
  --data data/external/nsxusd/active_nsxusd.pkl \
  --results-root results/external/nsxusd
~~~

Example multi-timeframe run:

~~~bash
python scripts/run_original.py multi-tf --tf 5 \
  --data data/external/nsxusd/active_nsxusd.pkl \
  --results-root results/external/nsxusd
~~~

If --data is supplied without --results-root, the runner automatically isolates outputs under:

~~~text
results/external/<dataset-stem>/
~~~

The hash-locked canonical source files under src/original/ are still not edited.

## Interpretation rules

External NSX/USD runs are valuable for questions such as:

- whether FVG attraction/reaction survives much longer history;
- whether age decay is present across older regimes;
- whether session/time effects persist;
- whether midpoint/CE behavior generalizes;
- whether a result found on MNQ also appears in a related Nasdaq-100 price feed.

Do **not** use this source alone to claim:

- NQ/MNQ execution performance;
- futures volume effects;
- roll behavior;
- exact CME tick behavior;
- exact futures slippage/fill behavior.

The best use is **discovery + robustness**, followed by confirmation on proper CME futures data.
