# Stage124 Batch 2 — Gate A change log

Date: 2026-06-23
Branch: `stage124-batch02-priority-research`
Base: `origin/main` @ `439c3ce9b673c4c0cf41e6a8b8cf229849aed053` (reference merge
commit present in ancestry; main not reset or rewound).

## Added (new files only)

- `src/stage124_batch02.py` — Gate A engine (priority ranking, Batch 2 selection,
  research package, conflict audit, user-review template, QC, metadata).
- `run_stage124_batch02.py` — runner.
- `tests/test_stage124_batch02.py` — 32 independent tests (several recompute
  expectations outside the production code path).
- `stage124/listing_pending_priority_stage124_batch02.csv`
- `stage124/listing_batch02_selected_tickers.csv`
- `stage124/listing_batch02_research_candidates.csv`
- `stage124/listing_batch02_source_provenance.csv`
- `stage124/listing_batch02_tsetmc_conflict_audit.csv`
- `stage124/listing_batch02_user_review_template.csv`
- `stage124/stage124_batch02_gate_a_qc_report.json`
- `stage124/metadata_and_hashes_stage124_batch02_gate_a.json`
- `stage124/stage124_batch02_gate_a_unit_test_output.txt`
- `stage124/README_STAGE124_BATCH02_GATE_A.md`
- `stage124/stage124_batch02_gate_a_change_log.md`

## Unchanged / not created (verified)

- Stage122 and Stage123 inputs: byte-identical (SHA-256 checked before & after).
- Targets, financial values, ratios, statement scope: unchanged.
- Pilot15 files and Stage124 Part1 metadata: not modified.
- `listing_master_partial_verified_stage124.csv`: unchanged (still 15 verified /
  115 pending).
- `listing_master_verified_stage124.csv`: not created.
- No new cumulative partial master with more verified rows.
- No Stage124 Part2 run; no model / SHAP / Optuna / SMOTE / calibration.

## Confirmation status

No ticker changed to `verified_user_confirmed`. All Batch 2 dates are
**candidates** pending explicit user confirmation (Gate B).
