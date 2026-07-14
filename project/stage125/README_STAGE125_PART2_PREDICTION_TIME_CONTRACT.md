# Stage125 Part 2 — Prediction-time & Leakage Contract

## Scope

Part 2 is a **contract / read-only-audit** task. It performs:
- **No** modeling, **no** data extraction, **no** network access.
- **No** changes to eligibility, targets, samples, or frozen assets.
- **No** row dropping or pair dropping.

## Inputs (read-only, SHA-256 verified)

- `modeling_all_rows_stage124_gate_b.csv` — 1331 rows, 1331 unique row_key
- `modeling_one_year_ahead_stage124_gate_b.csv` — 1200 pairs, 130 tickers

## Prediction cutoff rules

- The prediction cutoff is defined by the earliest verified `available_at` timestamp of the predictor (year t) statement.
- No feature whose `available_at` is after the cutoff may be used.
- If `available_at` is unknown, the cutoff is **unresolvable**; the pair is NOT dropped.
- Missing `fiscal_year_end` is never filled or guessed.

## Temporal gap audit (read-only)

- Pairs total: 1200
- Both dates present: 1195
- Either date missing: 5
- Both dates missing: 3
- fiscal_year_end_t missing: 4
- fiscal_year_end_t_plus_1 missing: 4

## Feature availability (M1–M4)

- M1 Financial: available only with verified `available_at` <= cutoff.
- M2 Market: window must close before cutoff.
- M3 Macro: publication date must be before cutoff.
- M4 Audit/Governance: strict point-in-time.
- No feature from target year (t+1) is ever available.

## Leakage checklist (8 checks, all machine-testable)

- LC01: no target-year feature used
- LC02: no future-period data
- LC03: no unverified available_at
- LC04: no inferred cutoff
- LC05: no revision used as original
- LC06: no eligibility changed
- LC07: no pair dropped (all 1200 preserved)
- LC08: missing fiscal_year_end not filled

## Guardrails

- `eligibility_impact` = `none_contract_audit_only` for every pair.
- `modeling_started` remains `false`.
- `part2_started` = `true` (contract only, not modeling).
- Stage122–Stage125 Part 1 frozen assets unchanged.
