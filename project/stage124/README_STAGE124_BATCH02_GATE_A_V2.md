# Stage124 — Batch 2, Gate A V2

Corrected prioritisation of 115 pending tickers using **tiered lexicographic
ranking** (not gap-based scoring), screening of all 115, TSETMC instrument
probe, full event-type separation, evidence standard enforcement, and
user-review template.

> **Supersedes V1** (`README_STAGE124_BATCH02_GATE_A.md`). V1 files are
> preserved and not overwritten.

> **Gate A only.** No ticker is promoted to `verified_user_confirmed`. No new
> cumulative partial master with more verified rows is written. No
> `listing_master_verified_stage124.csv` is created. No Stage124 Part2 run, no
> modelling. Stage122 / Stage123 / targets / financials / ratios / statement
> scope are read-only and their hashes are checked before and after the run.

## Key corrections from V1

- `gap_after_1392` / `W_GAP` removed entirely from ranking.
- `earliest_fiscal_year` is descriptive only; never used as public-entry evidence.
- `suspected_public_entry_after_1392` is `"unknown"` unless external evidence exists.
- `estimated_eligibility_rows_changed` / `estimated_t_plus_1_pairs_changed` are
  computed only when a real candidate public-entry date exists; otherwise `"unknown"`.
- Tiered lexicographic ranking (A–E) replaces weighted `priority_score`.
- Substantive tie keys exclude `ticker_normalized`.
- TSETMC probe for all 115 pending tickers (or `network_unreachable` if blocked).
- Admission-only dates are NOT placed in `proposed_canonical_public_entry_date`.
- `ready_for_user_review` is `false` unless evidence standard is met.
- All V2 outputs have independent filenames; V1 files are preserved.

## Reproduce

```bash
cd project
python3 run_stage124_batch02_v2.py        # builds all Gate A V2 artifacts
python3 -m pytest tests/test_stage124_batch02_v2.py -q
```

The run aborts with an explicit error if the Stage122/Stage123 input SHA-256 do
not match the expected frozen values, or if any guardrail assertion fails.

## Tiered lexicographic ranking (A–E)

Tiers are assigned in lexicographic order:

| Tier | Criteria |
|---|---|
| A | `candidate_supported` + exact-day date + eligibility rows changed > 0 |
| B | `candidate_supported` + exact-day date + eligibility rows changed = 0 |
| C | `requires_manual_review` or month/year-only precision |
| D | `requires_first_public_trade_evidence` (admission-only) |
| E | No research data / unknown |

Within each tier, rows are sorted by substantive tie keys:
`estimated_eligibility_rows_changed`, `estimated_t_plus_1_pairs_changed`,
`current_prelisting_proxy_row_count`, `tsetmc_conflict_flag`,
`multiple_ordinary_instruments`, `screening_source_confidence`.
`ticker_normalized` is **not** a substantive tie key.

Batch size: 15 (min) to 20 (max). Extension only if rank-15/16 boundary is a
substantive tie.

## Event-type separation

Four separate date columns in research output:
- `admission_date_candidate_jalali` / `admission_date_candidate_gregorian`
- `listing_date_candidate_jalali` / `listing_date_candidate_gregorian`
- `first_public_offering_date_candidate_jalali` / `first_public_offering_date_candidate_gregorian`
- `first_public_trading_date_candidate_jalali` / `first_public_trading_date_candidate_gregorian`

Admission-only dates are NOT placed in `proposed_canonical_public_entry_date`.

## Evidence standards

- `candidate_supported`: exact-day date + non-empty `proposed_canonical` + `ready_for_user_review=true`
- `requires_manual_review`: month/year-only precision or ambiguous evidence
- `requires_first_public_trade_evidence`: admission-only, no trading evidence
- `ready_for_user_review` is `false` unless `candidate_supported`

## TSETMC probe

All 115 pending tickers are probed via TSETMC CDN API:
- `instrument_match_status`: `candidate_found`, `multiple_ordinary_instruments`,
  `no_exact_ordinary_instrument_match`, `empty_trade_history`, `network_unreachable`,
  `http_error`, `parse_error`
- Non-ordinary instruments (rights, funds, futures) are filtered out
- `multiple_ordinary_instruments` flag set when >1 exact ordinary match
- `tsetmc_conflict_flag` set when TSETMC candidate date conflicts with research date
- Raw response SHA-256 recorded in provenance

## Outputs (all V2; V1 files preserved)

- `listing_pending_priority_stage124_batch02_v2.csv` — 115 ranked pending tickers
- `listing_batch02_selected_tickers_v2.csv` — selected batch
- `listing_batch02_research_candidates_v2.csv` — candidates + sources + status
- `listing_batch02_source_provenance_v2.csv` — per-source provenance
- `listing_batch02_tsetmc_conflict_audit_v2.csv` — TSETMC candidate disposition
- `listing_batch02_user_review_template_v2.csv` — user decision file (blanks)
- `stage124_batch02_gate_a_v2_qc_report.json`
- `metadata_and_hashes_stage124_batch02_gate_a_v2.json`
- `stage124_batch02_gate_a_v2_unit_test_output.txt`
- `external_hash_manifest_stage124_batch02_gate_a_v2.csv`
- `README_STAGE124_BATCH02_GATE_A_V2.md`
- `stage124_batch02_gate_a_v2_change_log.md`

## Forbidden actions (verified by QC)

- No ticker changed to `verified_user_confirmed`
- No `listing_master_verified_stage124.csv` created
- No new cumulative partial master
- No Stage124 Part2 run
- No model training
- No Gate B execution
