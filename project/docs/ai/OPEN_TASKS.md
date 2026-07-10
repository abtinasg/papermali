# OPEN TASKS

Human-maintained. The authoritative "next action" ID lives in `ROADMAP.md`
front matter; this file is the working description.

## Active research workstream: `stage124-batch02-part03`

### Superseded — `stage124-batch02-part03-1b-1`

**Cancelled by official TSE API.** The canonical listing dates for all 130
tickers were obtained from the official TSETMC API and are stored in
`project/stage124/listing_master_verified_stage124.csv` with the column
`first_observed_trading_date_from_official_tse_api` and status
`verified_tse_api_first_observed_trade`.

The manual Human-in-the-Loop research path (HIL dashboard, manual intake runner)
has been **retired**. The 10 Part 3 tickers no longer require manual source
discovery or dashboard confirmation.

### Next action — `stage124-gate-b-readiness`

**Gate B readiness / eligibility rebuild planning.** This is planning only —
Gate B execution, modeling, tuning, SHAP, SMOTE, calibration, and article
reporting are **not** in scope for the current PR.

## Completed

- ✅ `stage124-batch02-part03-1b-0` — dedicated intake scaffold and readiness gate.
- ✅ `stage124-batch02-part03-1b-1` — superseded by official TSE API; verified
  master with 130 tickers created.
- ✅ Verified master: `listing_master_verified_stage124.csv` — 130 unique tickers,
  dates are `first_observed_trading_date` (not necessarily IPO, admission, or
  listing dates).

## Not in scope yet (do NOT start)

- ❌ Gate B execution
- ❌ Modeling, tuning, SHAP, SMOTE, calibration, or article reporting

## Maintenance

- 🔧 `repository-driven-ai-handoff` — keep generated state synchronized after each
  completed research action and merge.
