# OPEN TASKS

Human-maintained. The authoritative "next action" ID lives in `ROADMAP.md`
front matter; this file is the working description.

## Active research workstream: `stage124-gate-b-execution`

### Completed — `stage124-gate-b-rule-approval`

**Approved.** The user/data owner explicitly approved the final Gate B listing
rules (supported by the readiness comparison; no external reviewer claimed):

- **Rule A (primary):** `first_observed_trading_date <= fiscal_year_end`
- **Rule B (listing-timing robustness):** `first_observed_trading_date <= fiscal_year_start`
- **Rule C rejected:** `first_observed_trading_year < fiscal_year`

Record: `project/stage124/gate_b_final/gate_b_rule_approval_stage124.json` and
`README_GATE_B_RULE_APPROVAL.md`.

### Completed — `stage124-gate-b-execution`

**Gate B executed.** The approved rules were applied to the frozen Stage123 data
and the verified listing master (1331 company-year rows, 1200 t→t+1 pairs, 130
tickers). Four sample designs:

- **main_rule_a_primary** — 1013 eligible (81 pos / 932 neg)
- **main_rule_b_listing_robustness** — 994 eligible (80 pos / 914 neg)
- **expanded_rule_a_company_scope_robustness** — 1057 eligible (81 pos / 976 neg)
- **expanded_rule_b_combined_robustness** — 1036 eligible (80 pos / 956 neg)

Unresolved listing rows: Rule A = 4, Rule B = 10 (preserved explicitly, never
zero-filled). Outputs in `project/stage124/gate_b_final/` (large canonical +
filtered CSVs gitignored/hashed; small audit CSVs, QC, metadata, README tracked).
58 focused tests (`project/tests/test_stage124_gate_b_execution.py`); 736 passed,
1 skipped in the full suite (local results — no GitHub Actions configured).
**No modeling started.**

### Next action — `stage125-modeling-readiness`

Post-Gate-B modeling readiness. **Modeling remains prohibited** (no modeling,
tuning, SHAP, SMOTE, calibration, temporal splitting, feature selection, or
article result generation) until this action is explicitly approved.

## Historical — `stage124-gate-b-readiness`

### Superseded — `stage124-batch02-part03-1b-1`

**Cancelled by official TSE API (not completed).** The canonical listing dates
for all 130 tickers were obtained from the official TSETMC API and are stored in
`project/stage124/listing_master_verified_stage124.csv` with
date_semantics=`first_observed_trading_date_from_official_tse_api`, in columns
`first_public_trading_date_jalali` and `first_public_trading_date_gregorian`,
with status `verified_tse_api_first_observed_trade`.

The manual Human-in-the-Loop research path (HIL dashboard, manual intake runner)
has been **retired**. The 10 Part 3 tickers no longer require manual source
discovery or dashboard confirmation.

### Completed — `stage124-gate-b-readiness`

**Gate B readiness dry-run completed.** Three eligibility rules (A/B/C) were
compared as a dry-run:

- **Rule A**: `first_observed_trading_date <= fiscal_year_end` — 1013 eligible pairs (81 pos / 932 neg)
- **Rule B**: `first_observed_trading_date <= fiscal_year_start` — 994 eligible pairs (80 pos / 914 neg)
- **Rule C**: `first_observed_trading_year < fiscal_year` — 995 eligible pairs (80 pos / 915 neg)
- **Stage123 baseline**: 1085 eligible pairs (86 pos / 999 neg)

Output files in `project/stage124/gate_b_readiness/`:
- `gate_b_rule_comparison_summary.json` — full comparison
- `gate_b_company_year_audit.csv` — per-row audit (1331 rows)
- `gate_b_pair_impact_summary.csv` — per-rule pair statistics
- `gate_b_unmatched_or_ambiguous_rows.csv` — data quality issues
- `gate_b_readiness_qc_report.json` — QC report (all pass)
- `metadata_and_hashes_gate_b_readiness.json` — hashes and metadata
- `README_GATE_B_READINESS.md` — human-readable summary

45 focused tests added in `project/tests/test_stage124_gate_b_readiness.py`.

The rule was subsequently finalized under `stage124-gate-b-rule-approval` and
applied under `stage124-gate-b-execution` (see the active workstream above).

## Completed

- ✅ `stage124-batch02-part03-1b-0` — dedicated intake scaffold and readiness gate.
- ✅ `stage124-official-api-finalize` — Finalized verified master for 130 tickers
  using official TSETMC first-observed-trade dates; merged through PR #15, merge
  commit 22c2d0c.
- ✅ `stage124-gate-b-readiness` — Dry-run comparison of three eligibility rules
  (A/B/C) with per-rule impact reports and 45 focused tests.
- ✅ `stage124-gate-b-rule-approval` — Rule A approved as primary, Rule B as
  listing-timing robustness; Rule C rejected.
- ✅ `stage124-gate-b-execution` — Approved rules applied; four sample designs,
  canonical + filtered outputs, 58 focused tests. No modeling started.
- ✅ Verified master: `listing_master_verified_stage124.csv` — 130 unique tickers,
  dates in `first_public_trading_date_jalali` / `first_public_trading_date_gregorian`
  with date_semantics=`first_observed_trading_date_from_official_tse_api`
  (not necessarily IPO, admission, or listing dates).
- ⚠️ `stage124-batch02-part03-1b-1` — superseded / cancelled by official TSE API
  (not completed).

## Not in scope yet (do NOT start)

- ❌ Modeling, tuning, SHAP, SMOTE, calibration, temporal splitting, feature
  selection, or article reporting (blocked until `stage125-modeling-readiness`)

## Maintenance

- 🔧 `repository-driven-ai-handoff` — keep generated state synchronized after each
  completed research action and merge.
