# Stage124 Gate B — Final Eligibility Rule Approval

## Decision status

**Approved.** The user/data owner has explicitly confirmed the final Gate B
listing-eligibility rules. This approval is recorded as **explicit
user/data-owner approval supported by the completed Stage124 Gate B readiness
scientific comparison** (`project/stage124/gate_b_readiness/`). No external
reviewer approval is claimed.

- `decision_status`: `approved`
- `approval_basis`: `explicit_user_data_owner_confirmation`
- `approval_date`: `2026-07-12`
- `readiness_merge_commit`: `cf1ab8877555159f127e4f9d7bf581ca7059a745`
- `readiness_summary_sha256`: `c910bf89ec4e4b63faa4c466d0b7f18a3f2a8d1ed1036b9bdf43bd3346b11e54`

## Approved rules

### Rule A — primary eligibility rule (main financial-statement sample)

```
first_observed_trading_date <= fiscal_year_end
```

- `primary_rule_id`: `rule_a`
- `primary_rule_role`: `primary`
- Rule A is the **primary** eligibility rule for the main financial-statement
  sample. It must not be replaced by Rule B in the primary sample.

### Rule B — listing-timing robustness rule

```
first_observed_trading_date <= fiscal_year_start
```

- `robustness_rule_id`: `rule_b`
- `robustness_rule_role`: `listing_timing_robustness`
- Rule B is a **listing-timing robustness** rule only. It must **not** replace
  Rule A in the primary sample, and it must **not** be treated as a future
  market-data / minimum trading-history / market-lookback rule. Later
  market-feature work must define a separate minimum trading-history or
  market-lookback rule.

### Rule C — rejected

```
first_observed_trading_year < fiscal_year
```

- `rejected_rule_id`: `rule_c`
- Rule C is **rejected** as the final rule. It is a coarse year-level
  approximation of the listing-timing test and provides **no methodological
  advantage** over the exact-date Rule B. Rule C must **not** appear as a final
  canonical eligibility flag; it may remain documented only as a **rejected
  readiness candidate**.

## Date semantics

All listing dates carry
`date_semantics = first_observed_trading_date_from_official_tse_api`.

**These dates are the first observed trading dates from the official TSETMC API.
They are NOT IPO dates, admission dates, or listing dates.**

Both rules use **exact Jalali dates**:

- `fiscal_year_end` is parsed as an exact Jalali date.
- `fiscal_year_start` is computed only for valid 12-month periods
  (month 12 → first day of the same Jalali year; otherwise → first day of the
  following month in the previous Jalali year). Missing `fiscal_year_end` or
  non-12-month periods remain **unresolved** for Rule B — no date is guessed and
  no missing value is zero-filled.

## Sample impact (main financial-statement sample)

| Rule | Eligible pairs | Positive | Negative |
|---|---|---|---|
| Rule A (primary) | **1013** | **81** | **932** |
| Rule B (robustness) | **994** | **80** | **914** |

These counts reproduce the approved Gate B readiness comparison exactly.

## Modeling remains prohibited

`modeling_authorized` is **false**. No modeling, tuning, SHAP, SMOTE,
calibration, temporal splitting, feature selection, or article result
generation is authorized by this approval. The next research action is
`stage125-modeling-readiness`.
