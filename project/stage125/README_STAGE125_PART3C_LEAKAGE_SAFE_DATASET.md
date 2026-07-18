# Stage125 Part 3C — Leakage-Safe Dataset Finalization

**Status:** leakage-safe pair datasets finalized under the locked six-month Jalali lag. Stage125 remains incomplete. No modeling / Stage126.

## Methodology

- Part 3B broad CODAL expansion is **superseded**.
- Six-month conservative Jalali lag is **approved** (`conservative_lag_months=6`).
- Part 3C leakage-safe finalization is **completed** for all four locked Gate B sample designs.
- Financial data remain **researcher-verified and frozen** (no re-extraction).
- Assumed availability uses `assumed_available_at_conservative` only — **no** observed publication-time claim (`PublishDateTime` / `available_at` / `SentDateTime`).
- Targets are copied from frozen Gate B pair files; never recomputed.
- Predictors join Stage123 on `predictor_row_key_t` → `row_key` (fail-closed one-to-one).

## Designs preserved

| Design | pairs | companies | positive | negative |
|---|---:|---:|---:|---:|
| `main_rule_a_primary` | 1013 | 119 | 81 | 932 |
| `main_rule_b_listing_robustness` | 994 | 117 | 80 | 914 |
| `expanded_rule_a_company_scope_robustness` | 1057 | 124 | 81 | 976 |
| `expanded_rule_b_combined_robustness` | 1036 | 122 | 80 | 956 |

## Outputs

- Bulky CSVs (gitignored): `project/stage125/part3c_outputs/`
- Tracked contracts / QC / hashes / column-role map / audits in `project/stage125/`.

## Research pointers

- `last_completed_research_action_id=stage125-part3c-leakage-safe-dataset-finalization`
- `next_research_action_id=stage125-part4-statistical-analysis-plan`
