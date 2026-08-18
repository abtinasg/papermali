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
* The Phase 1 evidence-package generator and the Handoff generator were
  corrected (see below) and the package was regenerated deterministically; no
  generated file was hand-edited, and no Stage125-Stage129 scientific artifact
  was changed.

## Contents

| file | role |
|---|---|
| `manuscript_draft_en.md` | the complete English manuscript draft |
| `claim_traceability_matrix.csv` | one row per quantitative or material scientific claim, with canonical source, exact committed value and source SHA-256 |
| `references.bib` | bibliography; every entry verified against an authoritative record |
| `reference_audit.csv` | per-reference verification record, including DOI resolution and manuscript role |
| `README.md` | source hierarchy, corrections, prohibited sources, repository-side audit detail |
| `validate_manuscript.py` | focused acceptance checks for this directory |
| `test_stage130_manuscript.py` | tests that run the acceptance checks |

## Source hierarchy

Scientific content in the manuscript comes only from aggregate, committed,
canonical artifacts, in this order of authority:

1. `project/stage130/manuscript_evidence_package/manuscript_claim_freeze.md` —
   highest authority. Where it conflicts with anything else, it wins.
2. The eight canonical tables (six result tables, the locked
   development-performance table and the definitional outcome table), the
   coefficient/odds-ratio table, the three schematic figures, the README and the
   manifest in the same package.
3. The Stage125–Stage129 aggregate source artifacts explicitly pinned by that
   package's `manifest.json`, plus the committed block-disposition and
   reporting-decision records for the M2–M4 narrative.
4. The earlier article blueprint, only where it does not conflict with the
   current claim freeze.

Two defects found during the first assembly have since been **corrected at their
source**, by fixing the Phase 1 generator and regenerating the package
deterministically. Git history preserves the prior version; no erratum overlay or
supersession package was created, and no generated file was hand-edited.

1. **Table 5 understated the robustness evidence.** It recorded
   `ordering_preserved_in_parts = [2, 3, 4]`, because the generator read the
   sample-definition subsection rather than the per-part flag. The authority is
   `part_summaries[*].primary_ordering_preserved` in
   `project/stage126/stage126_m1_robustness_closure_synthesis_record.json`, which
   marks Parts 2, 3, 4, 5 **and** 6 as preserving and Part 1 as the sole
   reversal — matching claim freeze C6. Table 5 now reports
   `[2, 3, 4, 5, 6]` and carries an explicit `ordering_reversed_in_parts = [1]`.

2. **The outcome definition had no canonical Stage130 home.** The claim freeze
   covers results, not the definition of the outcome, so the manuscript could not
   state what it predicts without reaching outside the package. The package now
   carries `table_8_outcome_definition.csv` and claim-freeze section **C10**,
   both copied verbatim from the committed
   `project/stage122/target_definition_stage122.csv`, and that file is pinned in
   the manifest. C10 is explicitly **definitional, not inferential**: no value in
   it is estimated, tuned, derived or inferred.

A third gap was closed the same way: the manuscript reported a development
ordering that a reader could not audit. The package now carries
`table_7_development_performance.csv` and claim-freeze section **C11**, copying
the locked values in `project/stage126/stage126_m1_development_metrics.csv`
verbatim for all three model families in both validation folds and in the pooled
out-of-fold scope. Nothing was recomputed, averaged or re-rounded, and the table
carries no delta, interval, p-value or significance column, because no such
quantity exists.

## Repository-side audit detail

The journal-facing manuscript deliberately carries **no** SHA-256 digests, no
FT-control identifiers, no internal repository paths and no discussion of the
repository test suite. Those belong to the audit surface, not to the scientific
narrative, and they live here instead:

* per-claim source digests — `claim_traceability_matrix.csv`;
* package and pinned-source digests — the Phase 1 `manifest.json`;
* the fail-closed control identifiers and their individual results —
  `project/stage129/final_test_execution/stage129_final_test_qc_report.json`;
* the frozen executor digest and the single-pass record —
  `project/stage129/final_test_execution/stage129_final_test_provenance_record.json`.

**Accepted historical test failures.** The repository test suite carries a set of
accepted failures that originate in earlier-stage boundary conditions and predate
this manuscript. They were not repaired, not expanded and not hidden by this
work, and no claim is made anywhere that the full suite passes. They are a
property of the repository's software boundary, **not** a limitation of the
scientific findings, which is why they no longer appear in the manuscript's
Limitations section.

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
