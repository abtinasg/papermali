# Stage129 — final model human selection (governance only)

**Action id:** `stage129-final-model-human-selection-governance`
**Type:** human governance decision. No fit, no refit, no trained artifact, no Final Test.

| marker | value |
| --- | --- |
| `final_development_block` | `M1` |
| `final_algorithm` | `regularized_logistic_regression` |
| `final_configuration` | `logistic__C_0.1` (pre-locked, **not** chosen here) |
| `selection_basis` | `HUMAN_DECISION_BASED_ON_PRELOCKED_DEVELOPMENT_EVIDENCE` |
| `paper_winner_selected` | `true` |
| `inferential_superiority_claimed` | `false` |

## What this decision is — and what it is not

The preceding read-only audit (`stage129-final-development-model-eligibility-audit`)
found **no frozen rule** determining either the block or the algorithm, and
therefore returned `FINAL_BLOCK_REQUIRES_HUMAN_DECISION` and
`FINAL_ALGORITHM_REQUIRES_HUMAN_DECISION`. That finding was correct and stands.

This package records the human decision the audit called for. It does **not**
retroactively create the rule the audit looked for. That is exactly why the
basis is recorded as a *human decision on pre-locked development evidence* and
not as a rule-derived determination.

The selection is therefore **not**:

- an inferential superiority claim (`inferential_superiority_claimed = false`),
- a tested superiority (`is_tested_superiority = false`),
- a Holm result (`is_holm_result = false`, `selection_used_holm_result = false`),
- a statistical proof (`is_statistical_proof = false`).

No hypothesis test selected this model. `confirmatory_family_1`
(`Logistic_vs_RF`, `Logistic_vs_XGBoost`, `RF_vs_XGBoost`) was **never
executed**, so no adjusted inferential ranking of the three algorithms exists.
The development evidence behind the decision was locked before it and is quoted,
never recomputed.

## M2 is still an intermediate confirmatory block

M2 keeps its role: `m2_role_preserved = intermediate_confirmatory_block`. Not
selecting M2 as the final block is **not** a statistical failure of M2 and is not
reported as one (`m2_declared_statistically_failed = false`,
`m2_not_selected_is_not_a_statistical_failure = true`). The committed evidence
still shows `m2_predictive_superiority_claim_supported = false` — an absence of
demonstrated superiority, which is a different statement from a demonstrated
absence.

## Random Forest and XGBoost are not rejected

Both keep their frozen configurations and their place in the record:

| algorithm | configuration | status |
| --- | --- | --- |
| random forest | `rf__depth_3__maxfeat_'sqrt'__leaf_10` | `NOT_SELECTED_BY_HUMAN_DECISION_ONLY` |
| xgboost | `xgboost__lr_0.03__depth_2__mcw_1__lambda_1` | `NOT_SELECTED_BY_HUMAN_DECISION_ONLY` |

Neither is declared removed, rejected, or statistically inferior
(`declared_removed`, `declared_rejected`, `declared_statistically_inferior` all
`false`). They were simply not selected, by human decision.

## Holm family — preserved, not executed

**Status: `HOLM_NOT_EXECUTED_FAMILY_PRESERVED_NO_INFERENCE`**

| member | status | p-value | H₀ accepted | H₀ rejected |
| --- | --- | --- | --- | --- |
| `M2_minus_M1` | `EVALUATED_NO_SUPERIORITY_ESTABLISHED` | `null` | `false` | `false` |
| `M3_CBI_minus_M2` | `NOT_EXECUTED_M3_CBI_DISCONTINUED` | `null` | `false` | `false` |
| `M4_minus_M3_CBI` | `NOT_EXECUTED_M4_DISCONTINUED` | `null` | `false` | `false` |

All three members survive with the frozen SAP counterparts
(`M2_minus_M1`, `M3_minus_M2`, `M4_minus_M3`) untouched. No Holm adjustment was
executed, the family was neither shrunk nor redefined, and no hypothesis was
accepted or rejected.

## The distinction the Handoff must keep

This is the part most likely to be misread, so it is recorded explicitly:

- ✅ The **block and algorithm family** have been selected.
- ✅ The **development configuration** was already locked *before* this decision
  — this action did not choose it
  (`final_configuration_selected_by_this_decision = false`).
- ❌ **No full-development model was refit** (`full_development_refit_performed = false`).
- ❌ **No trained final-model artifact was created**
  (`trained_final_model_artifact_created = false`, `trained_model_artifacts_written = 0`).
- ❌ **The Final Test is still locked and unread**
  (`final_test_locked = true`, `final_test_rows_read = 0`).

Selecting *which* model the paper reports is a governance act. Producing the
fitted object and evaluating it are separate, still-unauthorized steps.

## متن فارسی برای مقاله

بلوک نهایی توسعه `M1` و الگوریتم منتخب، رگرسیون لجستیک تنظیم‌شده با پیکربندی
از پیش قفل‌شده `logistic__C_0.1` است. مبنای این انتخاب یک **تصمیم انسانی بر
پایه شواهد توسعه‌ای از پیش قفل‌شده** است و نه برتری استنباطی، برتری آزمون‌شده،
نتیجه Holm یا اثبات آماری. خانواده آزمون‌های تأییدی هرگز اجرا نشد و هیچ مقدار p
برای اعضای آن وجود ندارد.

بلوک `M2` همچنان یک **بلوک تأییدی میانی** است؛ انتخاب‌نشدن آن به معنای شکست
آماری M2 نیست. جنگل تصادفی و XGBoost نیز حذف، مردود یا از نظر آماری مغلوب
اعلام نمی‌شوند؛ صرفاً به‌موجب تصمیم انسانی انتخاب نهایی نشده‌اند.

پیکربندی توسعه پیش از این تصمیم قفل شده بود؛ هیچ مدل full-development مجدداً
برازش نشد، هیچ artifact آموزش‌دیده نهایی ساخته نشد و Final Test همچنان قفل و
خوانده‌نشده باقی مانده است.

## English text for the manuscript

The final development block is M1 and the selected algorithm is regularized
logistic regression with the pre-locked configuration `logistic__C_0.1`. The
basis of this selection is a **human decision on pre-locked development
evidence**; it is not an inferential superiority claim, a tested superiority, a
Holm result or a statistical proof. The confirmatory model-comparison family was
never executed and no p-value exists for any of its members.

M2 remains an **intermediate confirmatory block**; not selecting it is not a
statistical failure of M2. Random forest and XGBoost are likewise not removed,
rejected or declared statistically inferior — they were simply not selected, by
human decision.

The development configuration was locked before this decision. No
full-development model was refit, no trained final-model artifact was created,
and the Final Test remains locked and unread.

## Supersede — the pending decision, not the audit findings

This package supersedes the audit's `next_action_id = human_decision_required`
and its two "requires human decision" verdicts, **and nothing else**. The audit
package stays byte-for-byte intact and its findings remain the historical record
of what the frozen rules did and did not determine. The supersede names the
artifact, the keys, the previous values and their meaning machine-readably.

## What this decision does NOT authorize

No full-development refit; no trained final-model artifact; no tuning,
calibration, threshold search, bootstrap, SHAP or prediction; no new metric, CI
or p-value; no Holm execution; no row-level scientific data read; no Final Test
access or unlock; no Stage130. Every counter in the governance boundary is `0`.

The pointer is
`human_authorization_required_for_full_development_refit_and_final_test` with
`authorized = false` — a pointer is never an authorization.

## Files

- `stage129_final_model_human_selection_decision.json` — the decision, the
  non-selected algorithms and the supersede pointer.
- `stage129_final_holm_family_status.json` — the preserved three-member ledger.
- `stage129_final_model_selection_governance_boundary.json` — what stays shut.
- `metadata_and_hashes_stage129_final_model_human_selection_governance.json`.

Regression tests:
`project/tests/test_stage129_final_model_human_selection_governance.py`.
