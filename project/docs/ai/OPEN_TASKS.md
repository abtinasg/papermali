# OPEN TASKS

Human-maintained. The authoritative "next action" ID lives in `ROADMAP.md`
front matter; this file is the working description.

## Active research workstream: `stage124-gate-b-readiness`

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

33 independent tests added in `project/tests/test_stage124_gate_b_readiness.py`.

**No rule has been finalized.** Gate B execution, modeling, tuning, SHAP, SMOTE,
calibration, and article reporting are **not** in scope.

### Next action — `stage124-gate-b-rule-approval`

**User and scientific reviewer must approve the final Gate B rule** from the
comparison report in `project/stage124/gate_b_readiness/`.

## Completed

- ✅ `stage124-batch02-part03-1b-0` — dedicated intake scaffold and readiness gate.
- ✅ `stage124-official-api-finalize` — Finalized verified master for 130 tickers
  using official TSETMC first-observed-trade dates; merged through PR #15, merge
  commit 22c2d0c.
- ✅ `stage124-gate-b-readiness` — Dry-run comparison of three eligibility rules
  (A/B/C) with per-rule impact reports and 33 independent tests. No rule finalized.
- ✅ Verified master: `listing_master_verified_stage124.csv` — 130 unique tickers,
  dates in `first_public_trading_date_jalali` / `first_public_trading_date_gregorian`
  with date_semantics=`first_observed_trading_date_from_official_tse_api`
  (not necessarily IPO, admission, or listing dates).
- ⚠️ `stage124-batch02-part03-1b-1` — superseded / cancelled by official TSE API
  (not completed).

## Not in scope yet (do NOT start)

- ❌ Gate B execution
- ❌ Modeling, tuning, SHAP, SMOTE, calibration, or article reporting

## Maintenance

- 🔧 `repository-driven-ai-handoff` — keep generated state synchronized after each
  completed research action and merge.
