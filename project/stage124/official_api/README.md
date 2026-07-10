# Stage124 Official TSE API Exports

Canonical storage for normalized Tehran Stock Exchange API exports used to populate
`listing_master_verified_stage124.csv`.

## Layout

| File | Role |
|------|------|
| `tse_first_trade_dates_batch01_bulk.csv` | Bulk first-trade export |
| `tse_first_trade_dates_batch02_ambiguous_resolved.csv` | Previously ambiguous / pending tickers |
| `tse_first_trade_dates_batch03_final_pair.csv` | Final pair: اروند, وکغدیر |
| `tse_first_trade_conflict_audit.csv` | Prior research vs API observed-date conflicts |
| `import_manifest.json` | Batch provenance, SHA-256, API metadata |
| `metadata_and_hashes.json` | Reproducibility hashes for all files in this folder |
| `provenance_manifests/*_provenance_manifest.json` | Per-batch provenance manifests (normalized CSV; raw JSON not archived) |

## API provenance

| Field | Value |
|-------|-------|
| `api_provider` | Tehran Stock Exchange Market Data (TSETMC CDN API) |
| `exact_endpoint_url` | `https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceDailyList/{ins_code}/0` |
| `request_parameters` | `ins_code` from batch CSV; `history_offset=0` |
| `extraction_script_not_archived` | Raw extraction script was not committed to this repository |
| `api_response_semantics` | Earliest observed closing-price record date (`dEven`) per `insCode` |
| `date_semantics` | `first_observed_trading_date_from_official_tse_api` |
| `retrieved_at_utc` | `null` when original API retrieval time was not archived |
| `finalized_at_utc` | UTC timestamp when `run_stage124_official_api_finalize.py` last ran |

## Date semantics

Committed batch CSV rows are normalized extractions from TSE API trade-history
responses. They are **first observed trading dates**, not official IPO,
admission, or listing announcement dates.

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

`listing_master_partial_verified_stage124.csv` is not modified by this stage.

## Not stored here

Dashboard / HIL artifacts remain under `stage124/batch02_parts/`. Application
code under `project/apps/` does not hold canonical listing-date data.

Raw API JSON responses and the original extraction script are **not** archived in
this repository. Provenance manifests record normalized batch CSV SHA-256 values
under `normalized_batch_csv_sha256`.
