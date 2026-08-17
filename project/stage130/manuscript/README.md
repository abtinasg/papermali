# Stage130 Phase 2 — manuscript assembly

**Manuscript writing and reference verification only. No new scientific analysis was
performed by this action.**

* Final Test rows read by this action: **0**.
* Prediction artifact `stage129_final_test_predictions.json`: **never opened**.
* Model fits, predictions, thresholds derived, metrics, confidence intervals,
  bootstrap replicates, p-values, Holm executions, SHAP executions,
  recalibrations, isotonic fits, subgroup calculations, per-year performance
  calculations, decision-curve or net-benefit calculations, new variable
  rankings: **0 of each**.
* No plot, curve or figure was created. The three schematic figures cited by the
  manuscript are used **by reference** from the frozen Phase 1 evidence package
  and were not regenerated.
* No generator or validator logic was modified. No frozen artifact was edited.

## Contents

| file | role |
|---|---|
| `manuscript_draft_en.md` | the complete English manuscript draft |
| `claim_traceability_matrix.csv` | one row per quantitative or material scientific claim, with canonical source, exact committed value and source SHA-256 |
| `references.bib` | bibliography; every entry verified against an authoritative record |
| `reference_audit.csv` | per-reference verification record, including DOI resolution and manuscript role |
| `validate_manuscript.py` | focused acceptance checks for this directory |
| `test_stage130_manuscript.py` | tests that run the acceptance checks |

## Source hierarchy

Scientific content in the manuscript comes only from aggregate, committed,
canonical artifacts, in this order of authority:

1. `project/stage130/manuscript_evidence_package/manuscript_claim_freeze.md` —
   highest authority. Where it conflicts with anything else, it wins.
2. The six canonical result tables, the coefficient/odds-ratio table, the three
   schematic figures, the README and the manifest in the same package.
3. The Stage125–Stage129 aggregate source artifacts explicitly pinned by that
   package's `manifest.json`, plus the committed block-disposition and
   reporting-decision records for the M2–M4 narrative.
4. The earlier article blueprint, only where it does not conflict with the
   current claim freeze.

One conflict was found and resolved in favour of the claim freeze, and is
recorded in the traceability matrix under
`TRACED_TO_CLAIM_FREEZE_C6_WHICH_OVERRIDES_TABLE_5_ordering_preserved_in_parts`:

> Table 5 records `ordering_preserved_in_parts = [2, 3, 4]`. The claim freeze
> (C6) states that the primary ordering was preserved in **Parts 2–6** and not in
> Part 1, and the pinned source artifact
> `project/stage126/stage126_m1_robustness_closure_synthesis_record.json`
> records `primary_ordering_preserved = true` for parts 2, 3, 4, 5 **and** 6.
> The manuscript follows the claim freeze and the pinned source. **The frozen
> table was not edited.** This discrepancy is flagged for human review.

Two definitional constants in the target-construction section — the
accumulated-loss-to-registered-capital threshold and the liabilities-to-assets
threshold — are not enumerated in the claim freeze, because the claim freeze
covers results rather than the outcome definition. They are traced instead to the
committed target-definition table
`project/stage122/target_definition_stage122.csv`. This is also flagged for human
review.

## Prohibited sources

Never cited, never opened by this action:

* `project/outputs/09_report/` — status `LEGACY_STAGE123_NONCANONICAL_DO_NOT_CITE`.
  It describes a different sample and a different analysis, and its numbers
  contradict the accepted analysis. It is preserved byte-identical for audit
  history.
* `project/stage129/final_test_execution/stage129_final_test_predictions.json`
* `project/stage125/part3c_outputs/analysis_ready_main_rule_a_stage125.csv`
* `project/stage125/part3c_outputs/audited_pairs_main_rule_a_stage125.csv`
* `project/stage125/part4_temporal_split_manifest_stage125.csv`
* any raw or row-level Final Test source, and any source whose use would require
  recomputation.

## What the manuscript deliberately does not contain

No ROC, precision–recall, calibration, decision, subgroup or per-year performance
curve. No causal claim, superiority claim, significance claim, stability claim or
deployment-readiness claim. No coefficient p-value, confidence interval or
significance marker. No claim that the Final Test constitutes external or
independent validation. No claim that the full repository test suite passes. No
claim that this is the first study of its kind.

## Verification commands

Focused acceptance checks for this directory:

```
python project/stage130/manuscript/validate_manuscript.py
```

Tests:

```
python -m pytest project/stage130/manuscript/test_stage130_manuscript.py -q
```

Stage129 Final Test tests, and the repository Handoff validator:

```
python -m pytest project/tests/test_stage129_final_test_execution.py -q
python project/scripts/validate_ai_handoff.py --check
```

The repository test suite carries a set of **accepted historical failures** that
predate this manuscript. They were not repaired, not expanded and not hidden by
this action, and no claim is made anywhere that the full suite passes.
