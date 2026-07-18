# Stage125 Part 3C — Leakage-Safe Dataset Finalization

**Status:** audited pair datasets and timing-eligible leakage-safe analysis-ready datasets finalized under the locked six-month Jalali lag. Stage125 remains incomplete. No modeling / Stage126.

## Terminology

- **Audited pair datasets** = full frozen Gate B membership (authorized timing exceptions remain visible).
- **Leakage-safe analysis-ready datasets** = timing-eligible subset only (`assumed_before_target_fiscal_year_end=true`).
- Gate B membership preservation refers to the **audit population**, not necessarily the analysis-ready population.
- The authorized `رمپنا|1396` → `رمپنا|1397` exception is **not** timing-safe and is **not** analysis/model eligible.

## Methodology

- Part 3B broad CODAL expansion is **superseded**.
- Six-month conservative Jalali lag is **approved** (`conservative_lag_months=6`).
- Part 3C leakage-safe finalization is **completed** for all four locked Gate B sample designs.
- Financial data remain **researcher-verified and frozen** (no re-extraction).
- Assumed availability uses `assumed_available_at_conservative` only — **no** observed publication-time claim (`PublishDateTime` / `available_at` / `SentDateTime`).
- Targets are copied from frozen Gate B pair files; never recomputed.
- Predictors join Stage123 on `predictor_row_key_t` → `row_key` (fail-closed one-to-one).
- Predictor feature matrix uses an **explicit whitelist** only.

## Audited Gate B membership (complete pair surface)

| Design | audited pairs | companies | positive | negative | excluded |
|---|---:|---:|---:|---:|---:|
| `main_rule_a_primary` | 1013 | 119 | 81 | 932 | 1 |
| `main_rule_b_listing_robustness` | 994 | 117 | 80 | 914 | 1 |
| `expanded_rule_a_company_scope_robustness` | 1057 | 124 | 81 | 976 | 1 |
| `expanded_rule_b_combined_robustness` | 1036 | 122 | 80 | 956 | 1 |

## Leakage-safe analysis-ready (timing-eligible)

| Design | analysis pairs | companies | positive | negative |
|---|---:|---:|---:|---:|
| `main_rule_a_primary` | 1012 | 119 | 80 | 932 |
| `main_rule_b_listing_robustness` | 993 | 117 | 79 | 914 |
| `expanded_rule_a_company_scope_robustness` | 1056 | 124 | 80 | 976 |
| `expanded_rule_b_combined_robustness` | 1035 | 122 | 79 | 956 |

## Outputs

- Bulky CSVs (gitignored): `project/stage125/part3c_outputs/`
  - `audited_pairs_*.csv` — complete audited pair datasets
  - `analysis_ready_*.csv` — leakage-safe analysis-ready datasets
- Tracked contracts / QC / hashes / column-role map / audits in `project/stage125/`.

## Research pointers

- `last_completed_research_action_id=stage125-part3c-leakage-safe-dataset-finalization`
- `next_research_action_id=stage125-part4-statistical-analysis-plan`
