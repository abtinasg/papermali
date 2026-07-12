# Stage124 Gate B Execution

Final application of the **approved** Gate B listing-eligibility rules to
the frozen Stage123 modeling data and the verified Stage124 listing master.
No modeling, tuning, SHAP, SMOTE, calibration, temporal splitting, feature
selection, or article result generation is performed.

## Approved rules

- **Rule A (primary):** `first_observed_trading_date <= fiscal_year_end`
- **Rule B (listing-timing robustness):** `first_observed_trading_date <= fiscal_year_start`
- **Rule C:** *rejected* — never emitted as a final canonical eligibility flag.

## Date semantics

All listing dates: `date_semantics = first_observed_trading_date_from_official_tse_api`.

**These dates are the first observed trading dates from the official TSETMC API. They are NOT IPO dates, admission dates, or listing dates.**

## Sample designs (t -> t+1 pairs)

| Design | Company scope | Listing rule | Eligible | Positive | Negative | Target missing |
|---|---|---|---|---|---|---|
| main_rule_a_primary | main | Rule A | 1013 | 81 | 932 | 0 |
| main_rule_b_listing_robustness | main | Rule B | 994 | 80 | 914 | 0 |
| expanded_rule_a_company_scope_robustness | expanded | Rule A | 1057 | 81 | 976 | 0 |
| expanded_rule_b_combined_robustness | expanded | Rule B | 1036 | 80 | 956 | 0 |

The **primary modeling candidate** is `modeling_main_rule_a_eligible.csv`
(Rule A, main scope). **No model is run in this task.**

## Nesting invariants (verified)

- `main_rule_b_listing_robustness` is a subset of `main_rule_a_primary`
- `expanded_rule_b_combined_robustness` is a subset of `expanded_rule_a_company_scope_robustness`
- `main_rule_a_primary` is a subset of `expanded_rule_a_company_scope_robustness`
- `main_rule_b_listing_robustness` is a subset of `expanded_rule_b_combined_robustness`

## Scientific controls

- No source / target / feature value changed.
- No missing value zero-filled; unresolved listing stays explicitly `unresolved`.
- No row (1331) or pair (1200) dropped.
- Non-listing eligibility components taken verbatim from Stage123.

## Outputs

**Large (gitignored, hashed in metadata):**
- `modeling_all_rows_stage124_gate_b.csv` (1331 rows)
- `modeling_one_year_ahead_stage124_gate_b.csv` (1200 pairs)
- `modeling_main_rule_a_eligible.csv`, `modeling_main_rule_b_eligible.csv`,
  `modeling_expanded_rule_a_eligible.csv`, `modeling_expanded_rule_b_eligible.csv`

**Small (tracked, frozen):**
- `gate_b_sample_matrix.csv`, `gate_b_distribution_by_target_year.csv`,
  `gate_b_pair_change_vs_stage123.csv`, `gate_b_unresolved_rows.csv`
- `README_STAGE124_GATE_B_EXECUTION.md` (this file)

## Modeling status

`modeling_started = false`. Next action: `stage125-modeling-readiness`.
