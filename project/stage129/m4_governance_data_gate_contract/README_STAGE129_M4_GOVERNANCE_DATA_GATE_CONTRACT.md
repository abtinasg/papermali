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
Gate-design layer: prospective category enumeration for
`audit_opinion_type`, an explicit forbidden-inference list for
`going_concern_flag`, frozen date fields/direction for `audit_lag_days`, a
frozen provenance schema, a three-state Gate vocabulary, join/missingness
rules, and the coverage thresholds — none of which the Stage125 contract by
itself specified.

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
validation fold) already exist canonically in
[`project/stage125/part4_statistical_analysis_plan_stage125.json`](../../stage125/part4_statistical_analysis_plan_stage125.json)
and have already been reused, unchanged, by the M3 macro data Gate and the
M3-LAG-WDI exploratory Data Gate. See
`stage129_m4_data_gate_contract.json` → `thresholds.canonical_sources` for the
exact field names and file paths. No conflicting pre-existing threshold was
found for these four numbers; this action does not override anything.

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

## Known scope limitation (disclosed, not hidden)

The repository's Handoff generator
(`project/scripts/update_ai_handoff.py`) and independent current-state
validator recognize each stage's contract-lock package through a dedicated,
hand-written, fail-closed recognizer function specific to that stage (for
example `derive_stage128_m3_lag_wdi_exploratory_markers`). Writing an
equivalent recognizer for Stage129 — to the same fail-closed standard as the
existing ~11,000-line generator — was judged out of scope for this
design-only contract-lock action. Consequently:

- `project/docs/ai/handoff_state.json` and `project/docs/ai/CURRENT_STATE.md`
  were **not** regenerated and are **not** modified by this PR. Every field
  in them — including all M2/M3/M3-LAG-WDI/Final-Test/Holm state the task
  requires to stay byte-for-byte unchanged — is therefore unchanged by
  construction (a diff against `origin/main` on those two files is empty).
- `project/docs/ai/ROADMAP.md` received a new, purely additive prose item
  describing this action; its machine-readable front-matter pointer block
  was **not** touched, so `next_research_action_id` / `next_research_action_authorized`
  remain exactly what they were before this PR (`human-decision-required` /
  `false`) and this contract-lock's own pointer
  (`stage129-m4-governance-data-gate`, unauthorized) is recorded only inside
  the new prose item and the stage129 contract JSON, not in the front matter.
- Regression coverage for this action lives in
  `project/tests/test_stage129_m4_governance_data_gate_contract.py` and
  exercises the stage129 package's own JSON content directly, rather than a
  new generator recognizer.

A human supervisor should treat full generator integration (a
`derive_stage129_*` recognizer mirroring the Stage128 pattern, wired into
`build_handoff_state`/`render_current_state`, with matching drift tests) as
follow-up work if this contract is later carried forward — it was not
attempted here in order to avoid hand-modifying, or risking silent drift in,
the auto-generated state files this task was explicitly told to protect.
