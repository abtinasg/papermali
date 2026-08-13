# Stage129 — M4 manuscript reporting decision

**Action id:** `stage129-m4-manuscript-reporting-decision`
**Decision status:** `REPORT_AS_PRESPECIFIED_NOT_EXECUTED_DATA_INADEQUACY_NO_INFERENCE`
**Type:** human reporting decision — governance only.

This package records **one** thing: how the manuscript presents an M4−M3-CBI
comparison that belongs to a block which was **prespecified but never
admitted**. It is a *presentation* decision. It executes nothing, retrieves
nothing, computes nothing and reads nothing.

## What was unresolved, and what is now resolved

The merged M4 discontinuation package (PR #84,
`project/stage129/m4_human_discontinuation_data_inadequacy/`) recorded
truthfully that the frozen Stage125 contract makes family-2 membership
*prospectively conditional on block admission* but says nothing about how to
present the comparison of a block that was never admitted. It therefore left:

```
manuscript_reporting_decision_for_the_unexecuted_m4_comparison =
UNRESOLVED_REPORTING_DECISION
```

A human supervisor has now decided it. The canonical value is:

```
manuscript_reporting_decision_for_the_unexecuted_m4_comparison =
REPORT_AS_PRESPECIFIED_NOT_EXECUTED_DATA_INADEQUACY_NO_INFERENCE
```

## How the supersede works — history is preserved, not rewritten

The discontinuation package is **untouched, byte for byte**. Its boundary
artifact still reads `UNRESOLVED_REPORTING_DECISION`, because that is what was
true at the moment of the discontinuation decision, and this repository does not
rewrite history to make a later decision look ex ante.

This package supersedes **that single marker and nothing else**. The supersede
is declared machine-readably in both this package's decision artifact
(`superseded_marker`) and its governance boundary
(`manuscript_reporting_decision_supersedes_artifact` /
`..._supersedes_key` / `manuscript_reporting_decision_previous_value`), and the
canonical generator publishes the resolved value to the Handoff. Reading either
side of the supersede tells you the whole story: the prior value, the new value,
who resolved it and which file it came from.

## The decided reporting position

Recorded explicitly, and each one is a *statement about what did not happen*:

- M4 was a **prespecified** block.
- M4 was stopped **before admission and before any modeling**, because coverage
  was inadequate and the frozen feature definitions were not satisfied.
- `M4_minus_M3_CBI` stays `NOT_EXECUTED_M4_DISCONTINUED`.
- The comparison's p-value stays `null`.
- **No null hypothesis is accepted or rejected.**
- **No inferential conclusion and no performance claim is made about M4.**
- The comparison is **not** deleted from, renamed in, or substituted out of the
  SAP history — it is reported as prespecified-but-not-executed.
- This is **NOT** `FAIL_M4_DATA_GATE`. The Gate was never executed
  (`formal_m4_data_gate_executed = false`) and the formal verdict stays `null`.
- The Final Test stays locked with `rows_read = 0`.

## Approved reporting text

**English (approved wording):**

> M4 was prespecified but was not admitted to modeling because the available
> data did not provide adequate coverage and did not satisfy the frozen feature
> definitions. Consequently, the M4−M3-CBI comparison was not executed, no
> p-value was computed, and no inferential conclusion is drawn for M4.

**Persian (equivalent wording):**

> بلوک M4 از پیش تعریف شده بود، اما به‌دلیل ناکافی‌بودن پوشش داده‌ها و
> برآورده‌نشدن تعاریف تثبیت‌شده ویژگی‌ها، وارد مرحله مدل‌سازی نشد. در نتیجه،
> مقایسه M4−M3-CBI اجرا نشد، هیچ مقدار p محاسبه نشد و هیچ نتیجه استنباطی درباره
> M4 ارائه نمی‌شود.

This is the **approved reporting text only**
(`APPROVED_REPORTING_TEXT_ONLY_NOT_A_MANUSCRIPT_WRITING_AUTHORIZATION`). It is
**not** an authorization to write or rewrite the manuscript
(`manuscript_writing_or_rewriting_authorized = false`).

## What this decision does NOT do

It authorizes **nothing** scientific. Explicitly not authorized and not
performed by this action: re-running the V4.3.1 extraction or re-inspecting the
1628 payloads; any download or data completion; the M4 Data Gate; any formal or
per-fold coverage computation; feature materialization; modeling; incremental
evaluation; Holm execution; bootstrap; SHAP; prediction; final-model selection;
refit; Final Test access; Stage130. Every counter in the governance boundary is
`0`.

The M4 block disposition is unchanged
(`M4_DISCONTINUED_BY_HUMAN_DECISION_DATA_INADEQUACY`), the four frozen
candidates — `audit_opinion_type`, `going_concern_flag`, `audit_lag_days`,
`board_size` — keep their identity, order and count, and the M4 pointer stays
`human_decision_required` with `authorized = false`. A pointer is never an
authorization.

M1 and M2 results are unchanged; M3-CBI stays `UNRESOLVED_M3_DATA_GATE`;
M3-LAG-WDI stays `SUPPLEMENTARY_EXPLORATORY_ONLY`.

## Files

- `stage129_m4_manuscript_reporting_decision.json` — the decision, the approved
  EN/FA text and the supersede pointer.
- `stage129_m4_manuscript_reporting_governance_boundary.json` — what stays shut.
- `metadata_and_hashes_stage129_m4_manuscript_reporting_decision.json` — package
  hash manifest.

Regression tests:
`project/tests/test_stage129_m4_manuscript_reporting_decision.py`.
