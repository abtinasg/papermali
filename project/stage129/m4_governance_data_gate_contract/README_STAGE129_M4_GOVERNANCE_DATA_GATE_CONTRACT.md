# Stage129 — M4 Governance / Provenance Data-Gate contract lock (DESIGN ONLY)

This package prospectively locks the rules for a future **M4 Data Accessibility
/ Provenance Gate** over the four-feature governance-predictor block, **before
any M4 value is retrieved, read or inspected**. It is a contract, not a Gate:
it executes nothing, retrieves nothing, admits nothing and authorizes nothing
downstream. It was authorized as a bounded, design-only action; that
authorization is consumed by this lock and is not reusable for retrieval, the
Gate itself, or modeling.

## What is locked

**Candidate set — exactly four, no substitution.**

1. `audit_opinion_type`
2. `going_concern_flag`
3. `audit_lag_days`
4. `board_size`

These four identities and their `cand_m4_*` ids are **not new** — they are the
same candidate set already defined in
[`project/stage125/part3b1_m4_feature_definition_contract_stage125.json`](../../stage125/part3b1_m4_feature_definition_contract_stage125.json)
(`decision_id: m4_feature_definitions`, `option_id: M4-A`), which this action
inherits. What this action adds on top of that Stage125 contract is the
Gate-design layer: an explicit forbidden-inference list for
`going_concern_flag`, frozen source date fields and difference direction for
`audit_lag_days`, a frozen provenance schema, a three-state Gate vocabulary,
join/missingness rules, and the coverage thresholds — none of which the
Stage125 contract by itself specified.

> **This contract is NOT complete.** Two mandatory preregistered *semantic
> definitions* could not be frozen from any authoritative source and are
> recorded as open CONTRACT ISSUES — see
> [Unresolved prerequisite definitions](#unresolved-prerequisite-definitions)
> below. Candidate *identity* is frozen for all four; that is a different lock
> from the definitions, and it does not make the Gate executable.

Explicitly and permanently excluded from ever entering M4: `non_executive_ratio`,
`institutional_ownership`, any ownership/management feature, auditor-identity
features, audit-fee features, textual/NLP/LLM-derived predictors,
outcome-inspected keywords, and any governance feature "discovered later." A
failed or unavailable candidate may **not** be replaced by a substitute to
keep the count at four — a failed candidate simply shrinks the admitted block.

**Point-in-time rule — inherited verbatim, not invented.** The M4 block rule
(`document_available_at_le_pair_cutoff`) and the underlying cutoff definition
come unchanged from
[`project/stage125/part3b1_cutoff_available_at_contract_stage125.json`](../../stage125/part3b1_cutoff_available_at_contract_stage125.json).
A report's internal date is explicitly **not** its availability date: a report
dated before a pair's cutoff whose verified public availability is after the
cutoff is not usable for that pair.

**Thresholds — reused, not newly invented.** All four numeric thresholds
(candidate coverage ≥ 0.80, minimum training-fold coverage ≥ 0.75, block
common-sample coverage ≥ 0.70, ≥ 5 positive evaluable outcomes per locked
validation fold) already exist canonically elsewhere in the repository and are
reused here unchanged. Three of the four (candidate coverage ≥ 0.80, minimum
training-fold coverage ≥ 0.75, block common-sample coverage ≥ 0.70) originate
in
[`project/stage125/part4_statistical_analysis_plan_stage125.json`](../../stage125/part4_statistical_analysis_plan_stage125.json).
The fourth (≥ 5 positive evaluable outcomes per locked validation fold)
originates in
[`project/stage128/m3_macro_data_gate/stage128_m3_macro_data_gate_decision.json`](../../stage128/m3_macro_data_gate/stage128_m3_macro_data_gate_decision.json)
(field `min_positive_evaluable_each_temporal_validation_window`), not in the
Stage125 Part 4 SAP. See `stage129_m4_data_gate_contract.json` →
`thresholds.canonical_sources` for the exact per-threshold field names and
file paths. No conflicting pre-existing threshold was found for these four
numbers; this action does not override anything.

**Three-state Gate semantics.** `PASS_M4_DATA_GATE` /
`FAIL_M4_DATA_GATE` / `UNRESOLVED_M4_DATA_GATE`, kept distinct and
non-collapsible. `UNKNOWN → FAIL` and `UNKNOWN → zero` are explicitly
forbidden coercions.

**M3/comparator boundary — unchanged.** M3-CBI remains
`UNRESOLVED_M3_DATA_GATE`; M3-LAG-WDI remains
`SUPPLEMENTARY_EXPLORATORY_ONLY` and is never promoted to confirmatory M3; the
confirmatory Holm family `(M2_minus_M1, M3_CBI_minus_M2, M4_minus_M3_CBI)` is
unchanged and unexecuted. M3-CBI's unresolved status is recorded as a known
future **dependency** for any M4-vs-M3-CBI incremental evaluation — that
dependency is not resolved by this contract.

**Final Test firewall.** `final_test_locked = true`, `rows_read = 0`. Neither
this contract nor the future Gate it describes ever inspects an M4 value,
target, distribution or coverage figure for a Final Test row.

## Unresolved prerequisite definitions

Three prerequisites **could not be resolved from any authoritative source**
and are recorded in the contract as `CONTRACT_ISSUE_UNRESOLVED`: two
candidate-specific semantic definitions, and one cross-cutting identity issue
that blocks all four candidates. For every candidate the *identity* is frozen
(they remain M4 candidates and are never substituted); what is not frozen is
the definition or mapping each needs before the Gate can run.

| Candidate | Unresolved definition | Consequence |
| --- | --- | --- |
| `audit_opinion_type` | Exact allowed audit-opinion taxonomy | No modeled categorical values are admitted; empirical/frequency-based category discovery is forbidden; the future Gate may not execute for this candidate |
| `audit_lag_days` | Exact deterministic calendar-date conversion convention | No `audit_lag_days` value may be calculated; the future Gate may not execute for this candidate |

**`audit_opinion_type`.** A plausible four-category structure (مقبول /
Unqualified, مشروط / Qualified, مردود / Adverse, عدم اظهارنظر / Disclaimer of
opinion, reported to align with ISA 700/705) was found only in **secondary
Persian accounting-blog sources**. No official IACPA or Audit Organization
standard text, and no CODAL structured-field schema, was located confirming
that CODAL's field encodes exactly these identifiers. The candidate categories
are therefore recorded as unverified/provisional and explicitly flagged
`must_not_be_treated_as_frozen`. Resolving this requires an authoritative
source — **it may not be resolved by inspecting M4 observations.**

**`audit_lag_days`.** The Stage128 M3-LAG-WDI `jalali_fiscal_year_t_plus_621`
rule is a **year-mapping** convention (Jalali fiscal year t → annual
macro-indicator lookup year t + 621). It is **not** a calendar-date-to-date
conversion rule and is explicitly **forbidden** as a daily date-conversion
method for this candidate. No authoritative CODAL date-field format
documentation, and no independently verifiable Jalali→Gregorian conversion
rule specific to `audit_report_date` / `fiscal_year_end`, currently exists in
this repository or was found in available research. No conversion may be
invented or assumed.

### Cross-cutting: CODAL company-identity resolution

The join keys frozen by this contract — `ticker` + `fiscal_year_t` — are the
**parent-side** canonical row identity of the retained M2 development common
sample, audited in
[`stage127_m2_common_sample_join_audit.json`](../../stage128/m2_incremental_evaluation/stage127_m2_common_sample_join_audit.json)
(`join_is_one_to_one: true`, `duplicate_join_keys: 0`, `many_to_many_joins: 0`,
`matched_rows: 666`, `unmatched_parent_rows: 0`).

That audit is **parent-side only**. Its child side was **TSETMC market data**
(`src_m2_tsetmc_market`, matched on the Persian نماد); the M3 macro Gate that
reuses the same keys joins **country-year macro data**. Neither audited a
**CODAL-sourced, company-level** child side. Prior use of the same parent keys
is therefore *not* evidence that a CODAL disclosure can be deterministically
resolved to that same `ticker`.

No audited mapping from a CODAL issuer identity (symbol/نماد, issuer id,
national id, ISIN) to `ticker` exists in this repository. The only CODAL
identity work present is the Stage124 batch02 10-ticker screening pilot, in
which all 10 tickers are `network_blocked` with `fetched_source_count = 0`,
`evidence_source_count = 0` and `ready_count = 0` — it establishes no mapping.

Because **every** M4 candidate value is CODAL-sourced, the Gate's
join-quality/uniqueness dimension (G) is not evaluable for any of the four
candidates. `going_concern_flag` and `board_size` have gate-ready *semantic*
definitions, but the Gate is still not executable for them. No fuzzy matching,
name matching, outcome-informed matching or fallback mapping may substitute
for the missing audited mapping.

Unblocking any of these issues requires a **separately authorized** resolution
from an authoritative source. This contract lock does not authorize that work,
and the consumed contract-lock authorization does not extend to it.

## What this action did NOT do

Zero CODAL requests, zero network requests, zero documents retrieved, zero
M4 candidate observations read, zero company rows loaded, zero coverage
calculations, zero Gate executions, zero model fits, zero predictions, zero
Final Test rows read. See `stage129_m4_data_gate_execution_audit.json`.

## Files

- `stage129_m4_data_gate_contract.json` — the full contract: candidate set,
  semantic definitions, source/provenance policy, point-in-time rule,
  thresholds (with canonical-source citations), the ten individual Gate
  dimensions the future Gate must independently assess, join/identity rule,
  missingness policy, three-state semantics, M3/comparator boundary, Final
  Test firewall, and the contract-lock state block.
- `stage129_m4_data_gate_execution_audit.json` — all execution counters,
  every one zero.
- `stage129_m4_data_gate_governance_boundary.json` — the explicit
  non-authorization/non-drift assertions (candidate count fixed at 4,
  excluded candidates never admitted, M3-LAG-WDI never confirmatory, pointer
  is not authorization, etc.).
- `metadata_and_hashes_stage129_m4_governance_data_gate_contract.json` — hash
  manifest for this package.

## Generator integration (implemented)

A follow-up correction to this contract-lock action implemented Stage129
generator integration, to the same fail-closed standard used by the other
stages' recognizer functions (for example
`derive_stage128_m3_lag_wdi_exploratory_markers`):

- `derive_stage129_m4_governance_data_gate_contract_lock_markers()` exists in
  `project/scripts/update_ai_handoff.py` and is wired into the canonical
  Handoff generation path (`build_handoff_state`'s marker-merge chain), reading
  the Stage129 contract plus its governance-boundary and execution-audit
  companions and failing closed on a missing, corrupt or inconsistent
  contract package.
- `project/docs/ai/handoff_state.json` and `project/docs/ai/CURRENT_STATE.md`
  were regenerated by the canonical generator
  (`python project/scripts/update_ai_handoff.py --from-repository --write`)
  and now expose the Stage129 state. The generated fields state, and continue
  to state after this integration, that the M4 contract is **incomplete** and
  **not executable**: `m4_contract_complete=false`,
  `m4_contract_fully_executable=false`, `m4_data_gate_executable=false`,
  `m4_data_gate_authorized=false`, `m4_candidates_the_gate_may_execute_for=[]`,
  retrieval/observations/coverage/Gate/modeling all `false`/`0`, Final Test
  locked with `rows_read=0`.
- `project/docs/ai/ROADMAP.md` item 26 records this corrected integration
  state. The action still does not advance either pre-existing live research
  pointer chain (`next_research_action_id` / `m3_lag_wdi_next_action_id`
  unchanged); it publishes its own, separate, third pointer
  (`stage129_m4_next_action_id: stage129-m4-governance-data-gate`,
  `stage129_m4_next_action_authorized: false`,
  `stage129_m4_next_action_pointer_is_not_authorization: true`). This pointer
  remains a pointer only — generator integration does not authorize
  retrieval, observation reads, coverage calculation, Gate execution,
  modeling, incremental evaluation, Final Test access, or any other later
  scientific action.
- Regression coverage lives in
  `project/tests/test_stage129_m4_governance_data_gate_contract.py`, and
  generator-side coverage lives in `project/tests/test_ai_handoff.py`.
