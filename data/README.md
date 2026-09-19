# Local data area

Licensed MNQ data is not redistributed. `raw/`, `uploads/`, and `processed/` are ignored by Git.

The Research Lab now prefers a native Windows file picker or direct local path for large Databento/OHLCV inputs. Browser upload remains a fallback.

`scripts/prepare_active_contract.py` writes each completed build into a new generation under `data/processed/datasets/` and atomically updates `data/processed/current_dataset.json`. This avoids replacing a large pickle that another Windows process may still have open. Old pre-v2 installs with `data/processed/active_mnq.pkl` remain supported as a legacy fallback.

The published snapshot contains 2,303,483 active one-minute rows, 27 contracts, no duplicate timestamps, and no missing OHLC fields from 2020-01-01 through 2026-07-10.
