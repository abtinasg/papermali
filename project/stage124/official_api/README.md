# Stage124 Official TSE API Exports

Canonical storage for raw Tehran Stock Exchange API exports used to populate
`listing_master_verified_stage124.csv`.

## Layout

| File | Role |
|------|------|
| `tse_first_trade_dates_batch01_bulk.csv` | Bulk first-trade export (main tickers) |
| `tse_first_trade_dates_batch02_ambiguous_resolved.csv` | Previously ambiguous / pending tickers |
| `tse_first_trade_dates_batch03_final_pair.csv` | Final pair: اروند, وکغدیر |
| `import_manifest.json` | Batch provenance, SHA-256, build stats |
| `metadata_and_hashes.json` | Reproducibility hashes for all files in this folder |

## Date semantics

All `first_trade_date_*` values are **first observed trading dates** from the
exchange API, not official IPO/listing announcement dates.

The finalize step writes dates **only** to:

- `first_public_trading_date_jalali`
- `first_public_trading_date_gregorian`

`listing_date_jalali` and `ipo_date_jalali` remain empty unless an API row
explicitly denotes an IPO/listing event.

## Regenerate verified master

```bash
python project/run_stage124_official_api_finalize.py
```

Inputs are read **only** from this directory plus
`listing_master_template_stage124.csv`. No `~/Downloads` dependency.

Output:

- `project/stage124/listing_master_verified_stage124.csv`

## Not stored here

Dashboard / HIL artifacts remain under `stage124/batch02_parts/`. Application
code under `project/apps/` does not hold canonical listing-date data.
