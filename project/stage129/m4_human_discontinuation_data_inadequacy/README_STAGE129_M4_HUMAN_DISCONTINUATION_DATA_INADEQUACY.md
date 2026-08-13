# Stage129 — human discontinuation of M4 for data inadequacy

**Action id:** `stage129-m4-human-discontinuation-data-inadequacy`
**Action type:** human-decision recording only — zero Gate execution, zero
coverage computation, zero feature materialization, zero modeling, zero Final
Test access.

> ## Decision status
>
> ```
> M4_DISCONTINUED_BY_HUMAN_DECISION_DATA_INADEQUACY
> ```
>
> A human supervisor decided that the M4 governance-predictor block will not be
> pursued in this study, because the accessible data for the four frozen M4
> candidates is insufficient and does not match their frozen definitions.

---

## 1. This is NOT a formal Gate failure

This action is deliberately **not** recorded as `FAIL_M4_DATA_GATE`, and the
Gate-verdict vocabulary (`PASS_M4_DATA_GATE` / `FAIL_M4_DATA_GATE` /
`UNRESOLVED_M4_DATA_GATE`) is deliberately not used.

| | |
|---|---|
| Formal M4 Data Gate executed | **No — never** |
| Formal Gate verdict | **`null`** |
| Formal Gate coverage computed on development / folds | **No** |
| Any M4 feature materialized | **No** |
| Threshold passed or failed | **None** |
| Final Test or outcome observed for this decision | **No** |

The figures below are **observational coverage over the whole canonical
population**. They are *not* a Gate verdict, and they were never evaluated
against the Gate's development-set and per-fold thresholds:

- 444 / 1331 rows with a verified auditor opinion
- 446 / 1331 rows with an auditor report date

Recording this as a Gate failure would fabricate a formal evaluation that never
happened. The correct vocabulary is a **human decision taken outside Gate
execution**.

---

## 2. Basis for the decision

All evidence is already committed; this action creates no new data. See
`stage129_m4_human_discontinuation_evidence_references.json` for the exact
paths and hashes.

| Evidence | Value |
|---|---|
| Canonical population | 1331 rows, 130 tickers |
| Verified auditor opinion (observational) | 444 rows |
| Auditor report date | 446 rows |
| Fiscal year end | 889 rows |
| Field-level missing | 2214 |
| Rows with only consolidated statements | 368 |
| Rows with no archive match | 60 |

And, decisively for the *definitions* rather than the counts:

- **All 444 canonical opinions are free-text derived.** The frozen Stage125
  definition of `audit_opinion_type` requires an explicit **structured field**,
  not free-text inference.
- The 65 payloads that do carry a genuine structured `نظر حسابرس` field are all
  fiscal years **۱۳۸۰–۱۳۹۰**, entirely outside the canonical ۱۳۹۲–۱۴۰۲ window;
  **zero** of them fall inside the study population.
- `audit_lag_days` was never computed — the calendar-conversion convention
  remains `CONTRACT_ISSUE_UNRESOLVED`.
- `going_concern_flag` was never extracted.
- `board_size` was never prepared, so a complete four-candidate M4 block does
  not exist.
- The CODAL-to-parent identity prerequisite remains unresolved.
- Large-scale manual completion is not pursued for this study given the size of
  the missingness.

The reason class is therefore **data accessibility / coverage / definition
mismatch** — *not* a poor model result, and *not* outcome inspection. The block
was stopped **before any M4 modeling** and **without reading the Final Test**.

---

## 3. What this decision does and does not change

### Forward disposition

| Marker | Value |
|---|---|
| `m4_block_disposition` | `M4_DISCONTINUED_BY_HUMAN_DECISION_DATA_INADEQUACY` |
| `m4_retrieval_continues` | `false` |
| `m4_manual_completion_continues` | `false` |
| `m4_feature_materialization_authorized` | `false` |
| `m4_modeling_will_run` | `false` |
| `m4_incremental_evaluation_will_run` | `false` |
| `m4_reopening_authorized` | `false` |
| `m4_reopening_requires_new_human_authorization` | `true` |

### The four candidates are preserved, not rewritten

The candidate set stays exactly four, in order —
`audit_opinion_type`, `going_concern_flag`, `audit_lag_days`, `board_size`.
**No candidate is removed, renamed or substituted**, and the count is not
changed, so the contract's own history stays readable. Only the *execution path*
for that block is stopped for this study.

### History is preserved, not rewritten

These earlier facts remain true and their packages are untouched:

- the M4 contract was prospectively locked before any retrieval;
- three prerequisites were recorded as `CONTRACT_ISSUE_UNRESOLVED`;
- the documentary-research attempt resolved **0 of 3**;
- the V4.3.1 package is observational and is **not** a structured M4 input;
- the M4 Data Gate was **never** executed;
- the Final Test was **never** read for M4.

This decision is **additive**. It supersedes no prior record.

---

## 4. Holm family and the unexecuted comparison

The confirmatory multiplicity family is defined in
`project/stage125/part4_metrics_uncertainty_contract_stage125.json` under
`multiplicity`. **This action does not rewrite or redefine it.**

Recorded honestly:

- `M4_minus_M3_CBI` **was not executed**.
- There is **no p-value** for it.
- **No null hypothesis was accepted or rejected.**
- The reason is that the block was discontinued **before** modeling —
  `NOT_EXECUTED_M4_DISCONTINUED`.

On multiplicity: the frozen contract names family 2
`confirmatory_family_2_adjacent_block_gains_if_admitted`, i.e. membership is
**prospectively conditional on the block being admitted**. M4 was never admitted.
So the absence of the M4 comparison follows a condition fixed in advance — it is
**not** an opportunistic post-hoc shrinkage of the family after seeing a result,
and no result was ever seen.

What the contract does **not** settle is how the manuscript should present a
comparison belonging to a never-admitted block. That is recorded as
`manuscript_reporting_decision_for_the_unexecuted_m4_comparison =
UNRESOLVED_REPORTING_DECISION`. **Nothing is invented here**; it needs a separate
human reporting decision consistent with the SAP.

---

## 5. Effect on the paper

- M4 does not enter the main model of this study.
- The observational audit extraction remains in repository custody and **may be
  reported in the limitations / data-access discussion** — but it is not a model
  input.
- M1, M2 and M3 results are unchanged by this action. M3-CBI is **not** declared
  successful. M3-LAG-WDI stays `SUPPLEMENTARY_EXPLORATORY_ONLY`.
- No paper winner, no final model, no full-development refit, no Stage130 work.

---

## 6. Next action

**`human_decision_required`** — scope
`m4_discontinued_no_further_m4_action_is_authorized`.

The next action is **not** the M4 Data Gate. Reopening M4 — any retrieval, any
manual completion, any modeling — requires a **new, explicit human
authorization** that reverses this decision. A pointer is never an
authorization.

---

## 7. Verification

```bash
python -m pytest project/tests/test_stage129_m4_human_discontinuation_data_inadequacy.py -q
python project/scripts/validate_ai_handoff.py --check
```

Package contents: this README, the decision, the governance/non-actions
boundary, the committed-artifact evidence references, and a package hash
manifest.
