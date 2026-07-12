# Stage124: Approve and execute final Gate B eligibility rules

## Purpose

This PR finalises Stage124 Gate B in two logical steps:

1. **Approval** — explicit user/data-owner approval of the Gate B listing-eligibility
   rules, supported by the Stage124 Gate B readiness dry-run comparison (PR #17).
2. **Execution** — applies the approved rules to the frozen Stage123 modeling data
   and the verified Stage124 listing master, producing four canonical sample designs.

**No modeling, tuning, SHAP, SMOTE, calibration, temporal splitting, feature
selection, or article result generation occurs in this PR.**

---

## Approved rules

| Rule | Expression | Status |
|---|---|---|
| **Rule A (primary)** | `first_observed_trading_date <= fiscal_year_end` | ✅ Approved |
| **Rule B (listing-timing robustness)** | `first_observed_trading_date <= fiscal_year_start` | ✅ Approved |
| **Rule C** | `first_observed_trading_year < fiscal_year` | ❌ Rejected — coarse year-level approximation, no advantage over exact-date Rule B |

Date semantics: `first_observed_trading_date_from_official_tse_api`
(TSETMC first-observed-trade date; not necessarily IPO, admission, or listing date).

---

## Sample designs — t → t+1 pairs

All designs operate on 1331 company-year rows and 1200 pairs (1393–1402 target years),
130 tickers.

| Design | Scope | Rule | Eligible pairs | Positive | Negative | Target missing |
|---|---|---|---|---|---|---|
| `main_rule_a_primary` | main | Rule A | **1013** | **81** | **932** | 0 |
| `main_rule_b_listing_robustness` | main | Rule B | **994** | **80** | **914** | 0 |
| `expanded_rule_a_company_scope_robustness` | expanded | Rule A | **1057** | **81** | **976** | 0 |
| `expanded_rule_b_combined_robustness` | expanded | Rule B | **1036** | **80** | **956** | 0 |

**Primary modeling candidate:** `modeling_main_rule_a_eligible.csv` (Rule A, main scope).

### Nesting invariants (verified)
- `main_rule_b` ⊆ `main_rule_a`
- `expanded_rule_b` ⊆ `expanded_rule_a`
- `main_rule_a` ⊆ `expanded_rule_a`
- `main_rule_b` ⊆ `expanded_rule_b`

---

## Unresolved listing rows

| Rule | Unresolved company-year rows |
|---|---|
| Rule A (primary) | **4** |
| Rule B (robustness) | **10** |

Unresolved rows are preserved explicitly as the string `"unresolved"` — never
zero-filled or dropped.

---

## Commits (6, all ahead of `origin/main` @ `cf1ab88`)

| # | Full SHA | Role |
|---|---|---|
| 1 | `dbaf010b0ed1e86bf7c817299e8c98924be37d96` | Approval JSON + README + DECISIONS + CHANGELOG |
| 2 | `cf5f7f2f1f6fc7fc1283782ee6cdad20fc8e8965` | Execution module, runner, 46 tests, frozen-manifest, gitignore |
| 3 | `f575a57f671237ace8f820a7dc2b5e75cb48b64c` | Artifacts, QC, metadata, docs; readiness QC/metadata refresh |
| 4 | `b3e5ed49368c30aca5e45a795e00b4586a683531` | Handoff regeneration (gate_b_started=true) |
| 5 | `24d4fa9fe4a3a370204dba4b9f68097d1963fea0` | Readiness metadata python version string fix (no data change) |
| 6 | `e62e2bf8c15b81e7eea04044c7b3c1ac126097e9` | Handoff regeneration after python-version fix ← **HEAD** |

---

## Test results

### Focused execution tests (46)
```
python -m pytest project/tests/test_stage124_gate_b_execution.py -q
46 passed in 6.25s
```

### Full project test suite (724 + 1 skipped)
```
python -m pytest project/tests -q
724 passed, 1 skipped, 3 warnings in 56.50s
```

(The 1 skipped test is `test_change_allowlist_real_repo`, skipped unless
`ENFORCE_HANDOFF_CHANGE_ALLOWLIST=1` is set — pre-existing, unrelated to this PR.)

---

## QC report

- **QC scope:** `stage124_gate_b_execution`
- **Assertion count:** 23
- **Failed:** 0
- **`all_pass`:** `true`
- **Report path:** `project/stage124/stage124_batch02_gate_b_qc_report.json`

---

## Workflow markers

| Marker | Value |
|---|---|
| `gate_b_started` | **`true`** |
| `modeling_started` | **`false`** |
| `verified_master_created` | `true` |

---

## Idempotence verification

Running `python project/run_stage124_gate_b_execution.py` twice in succession:
SHA-256 of all 7 tracked small outputs (sample matrix, target-year distribution,
pair change CSV, unresolved rows CSV, README, QC report, metadata) was identical
across both runs — confirmed deterministic.

---

## Handoff validation

```
python project/scripts/validate_ai_handoff.py --check
Handoff validation passed (--check).
```

---

## Git status (exact)

```
(empty — working tree is clean)
```

---

## Outputs

**Large (gitignored, hashed in metadata manifest):**
- `project/stage124/gate_b_final/modeling_all_rows_stage124_gate_b.csv` (1331 rows)
- `project/stage124/gate_b_final/modeling_one_year_ahead_stage124_gate_b.csv` (1200 pairs)
- `project/stage124/gate_b_final/modeling_main_rule_a_eligible.csv`
- `project/stage124/gate_b_final/modeling_main_rule_b_eligible.csv`
- `project/stage124/gate_b_final/modeling_expanded_rule_a_eligible.csv`
- `project/stage124/gate_b_final/modeling_expanded_rule_b_eligible.csv`

**Small (tracked, frozen):**
- `project/stage124/gate_b_final/gate_b_sample_matrix.csv`
- `project/stage124/gate_b_final/gate_b_distribution_by_target_year.csv`
- `project/stage124/gate_b_final/gate_b_pair_change_vs_stage123.csv`
- `project/stage124/gate_b_final/gate_b_unresolved_rows.csv`
- `project/stage124/gate_b_final/README_STAGE124_GATE_B_EXECUTION.md`
- `project/stage124/gate_b_final/gate_b_rule_approval_stage124.json`
- `project/stage124/gate_b_final/README_GATE_B_RULE_APPROVAL.md`
- `project/stage124/stage124_batch02_gate_b_qc_report.json`
- `project/stage124/metadata_and_hashes_stage124_batch02_gate_b.json`

---

## Scientific controls

- No source / target / feature value changed.
- No missing value zero-filled; unresolved listing preserved explicitly.
- No row (1331) or pair (1200) dropped.
- Non-listing eligibility components taken verbatim from Stage123.
- Rule C never emitted as a final canonical eligibility flag.
- No modeling artifacts produced.

---

## Next action

**`stage125-modeling-readiness`** — modeling remains prohibited until that stage
is explicitly approved.

Do not merge without review. Do not start modeling.
