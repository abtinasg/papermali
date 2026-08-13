# Stage129 — M3-CBI human discontinuation and reporting decision

**Action id:** `stage129-m3-cbi-human-discontinuation-and-reporting`
**Disposition:** `M3_CBI_DISCONTINUED_BY_HUMAN_DECISION_UNRESOLVED_DATA_GATE_AND_UNPROVEN_POINT_IN_TIME`
**Type:** human scientific decision + its direct reporting consequence. Governance only.

A human supervisor decided to stop the M3-CBI block without admitting it to
modeling, and decided how its never-executed confirmatory comparison is
reported. This package records **only** that. It retrieves nothing, contacts
nobody, re-runs no Gate, computes no coverage, materializes no feature, fits no
model and never touches the Final Test.

## The methodological point that governs everything here

**M3-CBI is not M4.** The M4 block never had a Gate run at all. M3-CBI **did**:
`stage128-m3-macro-data-gate` was executed, its authorization was consumed, and
it produced a terminal snapshot. What it produced was:

```
m3_macro_data_gate_executed      = true
m3_macro_data_gate_terminal_status = UNRESOLVED_M3_DATA_GATE
```

So this package is careful in **both** directions:

- It is **NOT** recorded as `FAIL_M3_DATA_GATE`. That verdict exists in the
  Gate's locked vocabulary and the Gate did not return it. It terminated
  unresolved because the prospective definition lock stayed incomplete and no
  independently verifiable official evidence existed — not because a candidate
  was assessed against a threshold and failed. No value-level assessment was
  ever executed. Writing `FAIL` would assert an evaluation that never happened.
- It is **NOT** recorded as an unexecuted Gate either. The Gate ran, and
  erasing that would delete a completed research action.

No new threshold or coverage figure is computed here, and **none of the 8
recorded unresolved/blocker reasons is declared resolved**
(`m3_macro_data_gate_unresolved_reasons_resolved_by_this_decision = 0`).

## Why the block was stopped

Because the executed Gate stayed unresolved and point-in-time availability could
not be established: the definition lock was incomplete for all three candidates
(14 of 20 required lock fields unresolved each), no official CBI data or
documentation artifact is committed in the repository, the access-probe capture
metadata is not independently verifiable, and G04 — *published_at or available_at
verified* — was never satisfied.

The reason is **evidence, not results**: `reason_is_poor_model_result = false`,
`reason_is_outcome_inspection = false`, and no outcome or Final Test observation
was used (`decision_made_before_any_m3_cbi_modeling = true`).

## The confirmatory comparison — kept, not erased

The prespecified comparison is **not** removed, renamed, substituted or shrunk
out of the SAP history or the Holm family.

| field | value |
| --- | --- |
| comparison (live canonical id) | `M3_CBI_minus_M2` |
| frozen SAP identifier | `M3_minus_M2` |
| status | `NOT_EXECUTED_M3_CBI_DISCONTINUED` |
| p-value | `null` |
| null hypothesis accepted | `false` |
| null hypothesis rejected | `false` |
| inferential conclusion | `none` |
| performance claim | `none` |

`M3_CBI_minus_M2` is **not a new alias**. It was already the live canonical
identifier, published by the merged Stage129 M4 packages as member 2 of
`stage129_m4_confirmatory_holm_family`. The frozen Stage125 contract's own
member name, `M3_minus_M2`, is recorded alongside it and is left untouched.

Holm final adjustment is **not** declared complete; unexecuted comparisons keep
their `null` p-values.

## M3-LAG-WDI stays exactly where it was

Recorded fail-closed, and none of it is new — it restates the disposition the
Track A termination already set:

- `SUPPLEMENTARY_EXPLORATORY_ONLY`, role
  `supplementary_exploratory_robustness_block`.
- **Not** a substitute, **not** a proxy, **not** representative of M3-CBI, and
  **not** a confirmatory M3.
- Its results are **not** used to fill the `M3_CBI−M2` comparison.
- No exploratory p-value or result enters the confirmatory Holm family.
- Its existing results and artifacts are **unchanged**.

PR #79 is read **read-only** as an operational/historical fact: it is `MERGED`
(2026-08-08). This decision is not an authorization to change, reopen or re-merge
it, or any other existing PR.

## Approved reporting text

**English (approved wording):**

> M3-CBI was prespecified, but its executed Data Gate remained unresolved
> because point-in-time availability could not be established. The block was
> therefore not admitted to modeling. Consequently, the M3-CBI−M2 comparison was
> not executed, no p-value was computed, and no inferential conclusion is drawn
> for M3-CBI. The M3-LAG-WDI analysis is reported separately as supplementary
> exploratory evidence and is neither a substitute nor a proxy for confirmatory
> M3-CBI.

**Persian (equivalent wording):**

> بلوک M3-CBI از پیش تعریف شده بود، اما Data Gate اجراشده آن به‌دلیل
> اثبات‌نشدن دسترسی point-in-time حل‌نشده باقی ماند؛ بنابراین این بلوک وارد
> مدل‌سازی نشد. در نتیجه، مقایسه M3-CBI−M2 اجرا نشد، هیچ مقدار p محاسبه نشد و
> هیچ نتیجه استنباطی درباره M3-CBI ارائه نمی‌شود. تحلیل M3-LAG-WDI به‌صورت
> جداگانه و صرفاً به‌عنوان شواهد اکتشافی تکمیلی گزارش می‌شود و جایگزین یا
> نماینده M3-CBI تأییدی نیست.

This is the **approved reporting text only**
(`APPROVED_REPORTING_TEXT_ONLY_NOT_A_MANUSCRIPT_WRITING_AUTHORIZATION`). It is
**not** an authorization to write or rewrite the manuscript.

## How the supersede works

The executed Gate handed its disposition question to a human
(`m3_macro_data_gate_human_review_required = true`) and no human disposition had
been recorded. This decision answers **that pending review and nothing else**.

The Gate package stays **byte-for-byte intact**, and — this is the important part
— the Gate's own `gate_status` is **not** reassigned. It stays
`UNRESOLVED_M3_DATA_GATE` and is republished as the *terminal* status. What is
superseded is the open review, not the verdict. The supersede names the
artifact, the key, the previous value and the resolved value machine-readably,
and the canonical generator publishes the resolved disposition to the Handoff.

## What this decision does NOT do

No data retrieval or download; no new contact or follow-up with the World Bank
or any official source; no Gate re-execution; no new coverage or threshold; no
M3-CBI feature materialization; no modeling, incremental evaluation, Holm
execution, bootstrap, SHAP or prediction; no use of an M3-LAG-WDI result as a
confirmatory result; no Final Test access; no Stage130, final model, paper
winner or full-development refit; no change to any existing PR. Every counter in
the governance boundary is `0`.

M1 and its results are unchanged. M2 and the decision to retain it are
unchanged. The M4 discontinuation and reporting decisions merged in PR #84 and
PR #85 are unchanged. `next_research_action_authorized` stays `false`, and the
M3-CBI pointer is `human_decision_required` with `authorized = false` — a
pointer is never an authorization.

## Files

- `stage129_m3_cbi_human_discontinuation_decision.json` — the decision, the
  approved EN/FA text and the supersede pointer.
- `stage129_m3_cbi_confirmatory_comparison_record.json` — the unexecuted
  comparison, its frozen SAP counterpart and the Holm boundary.
- `stage129_m3_cbi_governance_boundary.json` — what stays shut.
- `metadata_and_hashes_stage129_m3_cbi_human_discontinuation_and_reporting.json`
  — package hash manifest.

Regression tests:
`project/tests/test_stage129_m3_cbi_human_discontinuation_and_reporting.py`.
