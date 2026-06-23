# Stage124 — Batch 2, Gate A

Priority ranking of the 115 pending tickers, selection of a 15-ticker Batch 2,
and a public-entry candidate / research package prepared for **user review**.

> **Gate A only.** No ticker is promoted to `verified_user_confirmed`. No new
> cumulative partial master with more verified rows is written. No
> `listing_master_verified_stage124.csv` is created. No Stage124 Part2 run, no
> modelling. Stage122 / Stage123 / targets / financials / ratios / statement
> scope are read-only and their hashes are checked before and after the run.

## Reproduce

```bash
cd project
python3 run_stage124_batch02.py        # builds all Gate A artifacts
python3 -m pytest tests/test_stage124_batch02.py -q
```

The run aborts with an explicit error if the Stage122/Stage123 input SHA-256 do
not match the expected frozen values, or if any guardrail assertion fails.

## Unit of observation & canonical date

- Unit: `ticker + fiscal_year`; eligibility uses the **exact** `fiscal_year_end`.
- Canonical date = the first confirmed public offering / public entry of the
  company's **ordinary** shares to general investors.
- Founding / admission (پذیرش) / درج / market-transfer / re-opening / rights
  (حق‌تقدم) / oldest TSETMC `dEven` are **not** canonical on their own; the
  TSETMC date is candidate / conflict-audit evidence only.
- No ambiguous date is force-selected; nothing is guessed.

## Priority score (deterministic, reproducible)

```
priority_score = W_GAP   * gap_after_1392
               + W_PRELIST* current_prelisting_proxy_row_count
               + W_RISK   * estimated_rows_at_risk
               + W_PAIR   * estimated_pairs_at_risk
               + W_MULTI  * multiple_ordinary_instruments
               + W_CONF   * tsetmc_candidate_conflict_flag
```

Weights: `W_GAP=10, W_PRELIST=8, W_RISK=3, W_PAIR=2, W_MULTI=5, W_CONF=4`.

Definitions (all derived directly from frozen Stage123 + the existing partial
master — no hidden judgement):

- `gap_after_1392 = max(0, earliest_fiscal_year_in_dataset - 1392)`.
- `suspect window` = the first `gap+1` panel years (the years whose listing
  eligibility is most sensitive if the true public-entry date is later than the
  first observed dataset year).
- `estimated_rows_at_risk` = currently-eligible panel rows inside the suspect
  window. **Pre-audit estimate only** — never a final eligibility result.
- `estimated_pairs_at_risk` = at-risk rows that have a `t+1` successor in the
  panel (one-year-ahead pairs). **Pre-audit estimate only.**
- `multiple_ordinary_instruments`, `tsetmc_candidate_conflict_flag`: 0 for all
  pending tickers in Gate A (only Pilot15 was TSETMC-probed; pending tickers are
  marked `not_probed_gate_a`).

Deterministic ordering (and tie-break): `priority_score` desc →
`current_prelisting_proxy_row_count` desc → `estimated_rows_at_risk` desc →
`n_panel_rows` desc → `ticker_normalized` asc. Because `ticker_normalized` is
unique across the panel, the multi-key sort fully resolves the rank-15/16
boundary, so `priority_rank` is unique, gap-free, and Batch 2 = the top **15**.
Extension toward 20 is triggered only if the boundary rows are identical on
every ordering key (which cannot happen here); the rule is implemented and
unit-tested for completeness.

## Batch 2 (15 selected)

`زپارس بالبر بترانس برکت بکاب بکام تاپیکو تپمپی تکمبا جم ددام درازک دسینا دشیمی ذوب`

Research finding summary (candidates only — to be confirmed by the user):

| ticker | candidate (Jalali) | event | research_status |
|---|---|---|---|
| زپارس | 1397-07-25 | first_public_offering | candidate_supported (post-1392, eligibility-relevant) |
| برکت | 1395-11-17 | first_public_offering | candidate_supported (post-1392) |
| جم | 1392-06-26 | first_public_offering | candidate_supported (near window start) |
| بکاب | 1383-07-07 | first_public_trading | candidate_supported (pre-window) |
| ذوب | 1390-06-29 | otc_first_listing_public_entry | candidate_supported (pre-window) |
| بالبر | 1372-05-10 | listing_admission | candidate_partially_supported |
| بکام | 1382-12-27 | listing_admission | candidate_partially_supported |
| تپمپی | 1373-07-23 | listing_admission | candidate_partially_supported |
| درازک | 1370-10-18 | listing_admission | candidate_partially_supported |
| دسینا | 1374-12-26 | listing_admission | candidate_partially_supported |
| دشیمی | 1381-10-08 | listing_admission | candidate_partially_supported |
| تاپیکو | (month only: تیر ۱۳۹۲) | first_public_offering | requires_manual_review |
| تکمبا | (month only: آذر ۱۳۷۳) | listing_admission | requires_manual_review |
| بترانس | (year only: ۱۳۶۹) | listing_admission | requires_manual_review |
| ددام | — | ambiguous_corporate_history | requires_manual_review |

Most of the gap=1 tickers are long-established firms whose dataset merely starts
at 1393 (data availability), not late listings — research confirms pre-1392
public entry, so no eligibility change is expected for them. The eligibility
impact will be computed in **Gate B**, only for tickers the user explicitly
confirms.

## Outputs (all immutable / versioned; Pilot15 & Part1 not overwritten)

- `listing_pending_priority_stage124_batch02.csv` — 115 ranked pending tickers
- `listing_batch02_selected_tickers.csv` — the 15 selected
- `listing_batch02_research_candidates.csv` — candidates + sources + status
- `listing_batch02_source_provenance.csv` — per-source provenance
- `listing_batch02_tsetmc_conflict_audit.csv` — TSETMC candidate disposition
- `listing_batch02_user_review_template.csv` — **user decision file (blanks)**
- `stage124_batch02_gate_a_qc_report.json`
- `metadata_and_hashes_stage124_batch02_gate_a.json`
- `stage124_batch02_gate_a_unit_test_output.txt`

## Gate B (NOT run here — design only)

After the user returns a confirmed-dates file (new, immutable, separate from the
research file and from Pilot15), Gate B will: admit only rows whose
`user_decision` is approved/confirmed; set `verification_status =
verified_user_confirmed`, `conflict_status = resolved_user_confirmed`,
`verified = true`, `canonical_event_type = first_public_offering_or_public_entry`,
`user_confirmation_date` from the real confirmation date; recompute eligibility
impact for the newly confirmed Batch 2 tickers with the exact `fiscal_year_end`;
write a new cumulative partial master; preserve the 15 Pilot15 rows unchanged;
and report cumulative counts (e.g. 15 new confirmations → verified=30,
pending=100). The full verified master is still **not** created and Part2 is
still **not** run.
