#!/usr/bin/env python3
"""Repository-driven AI Handoff Package generator.

Generates the 🤖 auto-managed files in ``project/docs/ai/`` from the repository
state (git + QC reports + frozen-asset manifests):

    - handoff_state.json   (machine-readable snapshot + semantic fingerprint)
    - CURRENT_STATE.md     (human-readable render of the snapshot)
    - FROZEN_ASSETS.md     (report over Stage122/Stage123/Stage124 hash manifests)

Design rules (see docs/ai/README.md):
    * A tracked file cannot store the SHA of the commit that contains it, so we
      never persist "HEAD == X". We anchor on ``generated_from_commit`` (an
      ancestor of HEAD) and a semantic ``state_fingerprint``.
    * QC freshness is checked by source/test SHA-256 fingerprint, not by
      ``qc_source_commit == HEAD`` (code-commit -> artifact-commit -> merge).
    * Frozen-asset mismatch/absence is FATAL, unless the file is explicitly
      classified as regenerable/non-frozen (NON_FROZEN_TRACKED) or is gitignored.
    * Human files (ROADMAP/DECISIONS/OPEN_TASKS/CHANGELOG/README/HANDOFF_PACKAGE)
      are *inputs*; this script never overwrites them.
    * Generation is package-atomic and fail-closed: outputs are written to temp
      siblings, originals are moved aside, and on any error everything is rolled
      back so no partial state is left behind. ``--check`` writes nothing.

Usage:
    python project/scripts/update_ai_handoff.py --from-repository --write
    python project/scripts/update_ai_handoff.py --from-repository --check
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

AUTO_FILES = (
    "project/docs/ai/handoff_state.json",
    "project/docs/ai/CURRENT_STATE.md",
    "project/docs/ai/FROZEN_ASSETS.md",
)

HUMAN_FILES = (
    "project/docs/ai/README.md",
    "project/docs/ai/HANDOFF_PACKAGE.md",
    "project/docs/ai/ROADMAP.md",
    "project/docs/ai/DECISIONS.md",
    "project/docs/ai/OPEN_TASKS.md",
    "project/docs/ai/CHANGELOG.md",
)

# Change allowlist, split by kind so matching is precise (no prefix attacks):
#   * directory entries match via startswith(dir) and MUST end with "/".
#   * file entries match by EXACT path only.
ALLOWLIST_DIRS = (
    "project/docs/ai/",
    # Stage125 Part 1 is tracked as a maintenance task (it does not advance the
    # research stage); its deliverables live under this directory.
    "project/stage125/",
    # Stage126 M1 primary development-fold tuning deliverables.
    "project/stage126/",
    # Stage127 M2 market-data admission Gate deliverables.
    "project/stage127/",
    # Stage128 M2 D2 boundary-month equity-return design-freeze deliverables
    # (machine-readable freeze record, human authorization record, QC report,
    # metadata/hashes manifest, feasibility provenance and reproduction
    # artifacts). Design-freeze/contract only -- no canonical Gate execution.
    "project/stage128/",
)
ALLOWLIST_FILES = (
    "project/scripts/update_ai_handoff.py",
    "project/scripts/validate_ai_handoff.py",
    "project/tests/test_ai_handoff.py",
    # Stage127 M2 market-data admission Gate code, runner, and tests.
    "project/src/stage127_m2_market_data_gate.py",
    "project/run_stage127_m2_market_data_gate.py",
    "project/tests/test_stage127_m2_market_data_gate.py",
    # Stage127 external TSETMC delivery import / revalidation layer and tests.
    # (the T* semantics audit artifacts live under project/stage127/)
    "project/src/stage127_m2_external_delivery_import.py",
    "project/tests/test_stage127_m2_external_delivery_import.py",
    # Stage127 equity_return_window root-cause audit (DIAGNOSTIC ONLY: reads
    # the immutable bundle and the Gate's own frozen window/feature functions;
    # never modifies the canonical Gate decision or any frozen artifact).
    "project/src/stage127_m2_equity_return_root_cause_audit.py",
    "project/run_stage127_m2_equity_return_root_cause_audit.py",
    # Stage127 zero-trade endpoint semantics external evidence-REQUEST package
    # (RETRIEVAL-REQUEST ONLY: generates a deterministic request for the
    # already-used Iranian TSETMC retriever; requests no decision, retrieves
    # nothing itself, and never modifies the canonical Gate). v1 is retained
    # as historical record only -- v2 supersedes it for actual retrieval.
    "project/src/stage127_m2_zero_trade_endpoint_evidence_request.py",
    "project/run_stage127_m2_zero_trade_endpoint_evidence_request.py",
    "project/src/stage127_m2_zero_trade_endpoint_evidence_request_v2.py",
    "project/run_stage127_m2_zero_trade_endpoint_evidence_request_v2.py",
    # Stage127 zero-trade "trading day" SEMANTICS evidence import and
    # frozen-contract adjudication (EVIDENCE IMPORT + ADJUDICATION ONLY:
    # independently revalidates the immutable v3 delivery, traces the frozen
    # Stage125 contract, and never fits a model, generates a prediction, reads
    # a final-test row, or modifies the canonical Gate).
    "project/src/stage127_m2_zero_trade_semantics_import.py",
    "project/src/stage127_m2_trading_day_semantics_adjudication.py",
    "project/run_stage127_m2_zero_trade_semantics_adjudication.py",
    "project/tests/test_stage127_m2_zero_trade_semantics_import.py",
    # Stage127 external TSETMC retrieval-request package code and tests.
    "project/src/stage127_m2_external_retrieval_request.py",
    "project/run_stage127_m2_external_retrieval_request.py",
    "project/tests/test_stage127_m2_external_retrieval_request.py",
    # Stage128 M2 D2 boundary-month equity-return design-freeze code and
    # tests (narrowest exact-file allowance; the generated freeze artifacts
    # themselves live under the already-allowlisted project/stage128/
    # directory, not here). Pure endpoint-selection function library built on
    # top of the unchanged, frozen Stage127 window/adjacency primitives; no
    # canonical Gate execution, no model fit, no prediction.
    "project/src/stage128_m2_d2_boundary_month_equity_return.py",
    # Stage127 M2 paired incremental-evaluation code, runner and tests. The
    # action id keeps its `stage127-` prefix while its generated artifacts
    # live under the already-allowlisted project/stage128/ workstream
    # directory. Development-only paired comparison of the frozen M2 block
    # against the frozen M1 block: it retunes nothing, searches no feature,
    # selects no winner and reads no final-test predictor or target value.
    "project/src/stage127_m2_incremental_evaluation.py",
    "project/run_stage127_m2_incremental_evaluation.py",
    "project/tests/test_stage127_m2_incremental_evaluation.py",
    "project/tests/test_stage128_m2_d2_boundary_month_equity_return.py",
    "project/tests/test_stage128_m2_d2_design_freeze_package.py",
    # Stage128 canonical M2 Gate RE-RUN under the frozen Gregorian D2
    # specification (action `stage128-m2-d2-gate-rerun`, one authorized
    # execution). Narrowest exact-file allowance; the Gate-rerun artifacts
    # themselves live under the already-allowlisted project/stage128/. The
    # module composes the frozen Stage127 importer/window/volatility/Amihud
    # primitives and the frozen Stage128 D2 endpoint selection -- it fits no
    # model, generates no prediction and reads no final-test row.
    "project/src/stage128_m2_d2_gate_rerun.py",
    "project/run_stage128_m2_d2_gate_rerun.py",
    "project/tests/test_stage128_m2_d2_gate_rerun.py",
    # Stage124 Gregorian->Jalali Esfand converter correctness fix
    # (CODE-CORRECTNESS ONLY: gregorian_to_jalali_str could never emit month 12,
    # so every Esfand date was mislabelled and is_valid_exact_jalali_date
    # rejected all of them. A read-only impact audit proved the defect produced
    # zero stored values and rejected zero real dates in the Stage124->125->126
    # lineage -- no canonical artifact, eligibility flag, cutoff, development
    # pair or Gate result changes. Fix plus Esfand/leap-Esfand regression tests
    # only.)
    "project/src/stage124_batch02_v2.py",
    "project/tests/test_stage124_batch02_v2.py",
    "project/tests/test_stage124_batch02_part03.py",
    # Stage125 Part 1 code, runner, and tests (maintenance task).
    "project/src/stage125_part1_data_contract.py",
    "project/run_stage125_part1.py",
    "project/tests/test_stage125_part1_data_contract.py",
    # Stage125 Part 2 code, runner, and tests.
    "project/src/stage125_part2_prediction_time_contract.py",
    "project/run_stage125_part2.py",
    "project/tests/test_stage125_part2_prediction_time_contract.py",
    # Stage125 Part 3A code, runner, and tests.
    "project/src/stage125_part3a_pilot_protocol.py",
    "project/run_stage125_part3a.py",
    "project/tests/test_stage125_part3a_pilot_protocol.py",
    # Stage125 Part 3A.1 code, runner, and tests.
    "project/src/stage125_part3a_decision_lock.py",
    "project/run_stage125_part3a_decision_lock.py",
    "project/tests/test_stage125_part3a_decision_lock.py",
    # Stage125 Part 3B.0 code, runner, and tests.
    "project/src/stage125_part3b0_evidence_readiness.py",
    "project/run_stage125_part3b0.py",
    "project/tests/test_stage125_part3b0_evidence_readiness.py",
    # Stage125 Part 3B code, runner, and tests.
    "project/src/stage125_part3b_evidence_capture.py",
    "project/run_stage125_part3b.py",
    "project/tests/test_stage125_part3b_evidence_capture.py",
    # Stage125 Part 3B.1 code, runner, and tests.
    "project/src/stage125_part3b1_decision_lock.py",
    "project/run_stage125_part3b1.py",
    "project/tests/test_stage125_part3b1_decision_lock.py",
    "project/tests/test_stage125_part3b1_allowlist_guards.py",
    # Stage125 Part 3B.1A code, runner, and tests.
    "project/src/stage125_part3b1a_cut_a_available_at_operationalization.py",
    "project/run_stage125_part3b1a.py",
    "project/tests/test_stage125_part3b1a_cut_a_available_at_operationalization.py",
    # Stage125 Part 3B.1B code, runner, and tests.
    "project/src/stage125_part3b1b_codal_document_binding.py",
    "project/run_stage125_part3b1b.py",
    "project/tests/test_stage125_part3b1b_codal_document_binding.py",
    # Stage125 Part 3B.1C code, runner, and tests.
    "project/src/stage125_part3b1c_document_binding_resolution.py",
    "project/run_stage125_part3b1c.py",
    "project/tests/test_stage125_part3b1c_document_binding_resolution.py",
    # Stage125 Part 3B.1E code, runner, and tests.
    "project/src/stage125_part3b1e_conservative_lag_decision.py",
    "project/run_stage125_part3b1e.py",
    "project/tests/test_stage125_part3b1e_conservative_lag_decision.py",
    # Stage125 Part 3C code, runner, and tests.
    "project/src/stage125_part3c_leakage_safe_dataset_finalization.py",
    "project/run_stage125_part3c.py",
    "project/tests/test_stage125_part3c_leakage_safe_dataset_finalization.py",
    # Stage125 Part 4 code, runner, and tests.
    "project/src/stage125_part4_statistical_analysis_plan.py",
    "project/run_stage125_part4.py",
    "project/tests/test_stage125_part4_statistical_analysis_plan.py",
    # Stage125 Part 5 code, runner, and tests.
    "project/src/stage125_part5_readiness_closure.py",
    "project/run_stage125_part5.py",
    "project/tests/test_stage125_part5_readiness_closure.py",
    # Stage126 M1 primary development-fold tuning code, runner, and tests.
    "project/src/stage126_authorization_transition_guard.py",
    "project/tests/test_stage126_authorization_transition_guard.py",
    "project/src/stage126_m1_primary_development_tuning.py",
    "project/run_stage126_m1_primary_development_tuning.py",
    "project/tests/test_stage126_m1_primary_development_tuning.py",
    # Stage126 M1 robustness Part 0 decision-lock code, runner, and tests.
    "project/src/stage126_m1_robustness_part0_decision_lock.py",
    "project/run_stage126_m1_robustness_part0_decision_lock.py",
    "project/tests/test_stage126_m1_robustness_part0_decision_lock.py",
    # Stage126 M1 robustness Part 1 target-proximity code, runner, and tests.
    "project/src/stage126_m1_robustness_part1_target_proximity.py",
    "project/run_stage126_m1_robustness_part1_target_proximity.py",
    "project/tests/test_stage126_m1_robustness_part1_target_proximity.py",
    # Stage126 M1 robustness Part 2 listing-Rule-B code, runner, and tests.
    "project/src/stage126_m1_robustness_part2_listing_rule_b.py",
    "project/run_stage126_m1_robustness_part2_listing_rule_b.py",
    "project/tests/test_stage126_m1_robustness_part2_listing_rule_b.py",
    # Stage126 M1 robustness Part 3 expanded-Rule-A code, runner, and tests.
    "project/src/stage126_m1_robustness_part3_expanded_rule_a.py",
    "project/run_stage126_m1_robustness_part3_expanded_rule_a.py",
    "project/tests/test_stage126_m1_robustness_part3_expanded_rule_a.py",
    # Stage126 M1 robustness Part 4 expanded-Rule-B code, runner, and tests.
    "project/src/stage126_m1_robustness_part4_expanded_rule_b.py",
    "project/run_stage126_m1_robustness_part4_expanded_rule_b.py",
    "project/tests/test_stage126_m1_robustness_part4_expanded_rule_b.py",
    # Stage126 M1 robustness Part 5 persistent-loss-target code, runner, tests.
    "project/src/stage126_m1_robustness_part5_persistent_loss_target.py",
    "project/run_stage126_m1_robustness_part5_persistent_loss_target.py",
    "project/tests/test_stage126_m1_robustness_part5_persistent_loss_target.py",
    # Stage126 M1 robustness Part 6 SMOTE-training-fold-only code, runner, tests.
    "project/src/stage126_m1_robustness_part6_smote_training_fold_only.py",
    "project/run_stage126_m1_robustness_part6_smote_training_fold_only.py",
    "project/tests/test_stage126_m1_robustness_part6_smote_training_fold_only.py",
    # Stage126 M1 robustness closure (synthesis-only) code, runner, and tests.
    "project/src/stage126_m1_robustness_closure.py",
    "project/run_stage126_m1_robustness_closure.py",
    "project/tests/test_stage126_m1_robustness_closure.py",
    # Stage126 M1 retained-design freeze (decision-freeze-only, no
    # execution) tests. There is no src/run_ builder for this action: the
    # freeze artifact/authorization record/metadata are hand-authored,
    # source-derived-and-verified records, not generated outputs.
    "project/tests/test_stage126_m1_retained_design_freeze.py",
    # Post-Part6 historical-replay overlay for the byte-frozen Part 5 test
    # file (see project/tests/conftest.py docstring); an operational test
    # fixture, not a Stage125/126 scientific or source artifact.
    "project/tests/conftest.py",
    # Stage126 live/historical test-suite boundary: config, runner, and tests.
    "pytest.ini",
    "project/run_stage125_part5_historical_successor_tests.py",
    "project/tests/test_stage126_live_historical_test_boundary.py",
    # Stage126 independent current-state validator code, runner, and tests.
    "project/src/stage126_current_state_validator.py",
    "project/run_stage126_current_state_validator.py",
    "project/tests/test_stage126_current_state_validator.py",
    # Transition-aware historical runners (Part 3A / 3A.1) touched for Part 3B.
    # (already allowlisted above)
    # Stage124 modeling-guardrail fix — narrowest exact-file allowance.
    # Do NOT broadly allowlist Stage122–Stage124 directories.
    "project/src/stage124_gate_b_execution.py",
    "project/tests/test_stage124_gate_b_execution.py",
    "project/stage124/stage124_batch02_gate_b_qc_report.json",
    "project/stage124/metadata_and_hashes_stage124_batch02_gate_b.json",
    "AGENTS.md",
    "CLAUDE.md",
    ".gitignore",
    "project/README_RUN.md",
)

# Handoff-only classification, INDEPENDENT of the change allowlist. A commit is
# "Handoff-only" (and therefore never advances last_stage_commit) only when every
# file it introduces is one of these Handoff-maintenance paths. Research /
# maintenance-task code (e.g. Stage125 Part 1) is deliberately EXCLUDED here even
# though it is change-allowlisted, so a code commit is still recognised as a
# Stage/Part commit by last_stage_commit().
#   * directory entries match via startswith(dir) and MUST end with "/".
#   * file entries match by EXACT path only.
HANDOFF_ONLY_DIRS = (
    "project/docs/ai/",
)
HANDOFF_ONLY_FILES = (
    "project/scripts/update_ai_handoff.py",
    "project/scripts/validate_ai_handoff.py",
    "project/tests/test_ai_handoff.py",
    "AGENTS.md",
    "CLAUDE.md",
)

# Generated-artifact-only classification, INDEPENDENT of both the change
# allowlist AND the Handoff-only classification. A commit is "artifact-only"
# (and therefore never advances last_stage_commit) only when every file it
# introduces is one of these exact, generated bookkeeping outputs (a QC report
# or a metadata_and_hashes hash manifest written by a runner). This is
# deliberately NOT wording-based (a commit body containing "Stage"/"Part" is
# irrelevant to this classification) and deliberately NOT directory-based for
# whole Stage122-Stage125 trees, so a real research/data-contract deliverable
# living under project/stageNNN/ (e.g. a data dictionary or contract JSON) is
# never swept in by accident. New generated outputs must be added here
# explicitly, one exact path at a time, the same way HANDOFF_ONLY_FILES and
# ALLOWLIST_FILES are curated.
#   * file entries match by EXACT path only (no directory entries).
ARTIFACT_ONLY_FILES = (
    "project/stage122/metadata_and_hashes_stage122.json",
    "project/stage122/stage122_qc_report.json",
    "project/stage123/metadata_and_hashes_stage123.json",
    "project/stage123/stage123_qc_report.json",
    "project/stage124/batch02_parts/part02_qc_report.json",
    "project/stage124/batch02_parts/part02_metadata_and_hashes.json",
    "project/stage124/batch02_parts/part03_qc_report.json",
    "project/stage124/gate_b_readiness/gate_b_readiness_qc_report.json",
    "project/stage124/gate_b_readiness/metadata_and_hashes_gate_b_readiness.json",
    "project/stage124/metadata_and_hashes_stage124_batch02_gate_a.json",
    "project/stage124/metadata_and_hashes_stage124_batch02_gate_a_v2.json",
    "project/stage124/metadata_and_hashes_stage124_batch02_gate_b.json",
    "project/stage124/metadata_and_hashes_stage124_part1.json",
    "project/stage124/metadata_and_hashes_stage124_pilot15.json",
    "project/stage124/stage124_batch02_gate_a_qc_report.json",
    "project/stage124/stage124_batch02_gate_a_v2_qc_report.json",
    "project/stage124/stage124_batch02_gate_b_qc_report.json",
    "project/stage124/stage124_pilot15_qc_report.json",
    "project/stage124/stage124_template_report.json",
    "project/stage124/official_api/metadata_and_hashes.json",
    "project/stage125/metadata_and_hashes_stage125_part1.json",
    "project/stage125/metadata_and_hashes_stage125_part2.json",
    "project/stage125/metadata_and_hashes_stage125_part3a.json",
    "project/stage125/stage125_part1_data_contract_qc_report.json",
    "project/stage125/stage125_part2_prediction_time_contract_qc_report.json",
    "project/stage125/stage125_part3a_pilot_protocol_qc_report.json",
    # Stage125 Part 3A generated protocol artifacts (runner output only).
    "project/stage125/README_STAGE125_PART3A_PILOT_PROTOCOL.md",
    "project/stage125/accessibility_scoring_rubric_stage125_part3a.json",
    "project/stage125/part3_candidate_inventory_stage125.csv",
    "project/stage125/part3_gate_decision_protocol_stage125.csv",
    "project/stage125/part3_pilot_sampling_options_stage125.csv",
    "project/stage125/part3_sampling_frame_by_target_year_stage125.csv",
    "project/stage125/part3_sampling_frame_summary_stage125.json",
    "project/stage125/part3_source_evidence_manifest_schema_stage125.json",
    # Stage125 Part 3A.1 generated decision-lock artifacts (runner output only).
    "project/stage125/metadata_and_hashes_stage125_part3a_decision_lock.json",
    "project/stage125/stage125_part3a_decision_lock_qc_report.json",
    "project/stage125/README_STAGE125_PART3A_DECISION_LOCK.md",
    "project/stage125/part3a_decision_lock_stage125.json",
    "project/stage125/part3a_approved_gate_thresholds_stage125.csv",
    "project/stage125/part3a_selected_pilot_pairs_stage125.csv",
    # Stage125 Part 3B.0 generated readiness artifacts (runner output only).
    "project/stage125/metadata_and_hashes_stage125_part3b0.json",
    "project/stage125/stage125_part3b0_evidence_readiness_qc_report.json",
    "project/stage125/README_STAGE125_PART3B0_EVIDENCE_READINESS.md",
    "project/stage125/part3b0_evidence_capture_contract_stage125.json",
    "project/stage125/part3b0_evidence_manifest_template_stage125.csv",
    "project/stage125/part3b0_gate_result_template_stage125.csv",
    "project/stage125/part3b0_immutable_cache_contract_stage125.json",
    "project/stage125/part3b0_network_denial_contract_stage125.json",
    # Stage125 Part 3B generated artifacts (runner output only).
    "project/stage125/part3b_authorization_stage125.json",
    "project/stage125/part3b_capture_plan_stage125.csv",
    "project/stage125/part3b_verified_endpoint_registry_stage125.csv",
    "project/stage125/part3b_evidence_manifest_stage125.csv",
    "project/stage125/part3b_cache_handles_stage125.csv",
    "project/stage125/part3b_candidate_evidence_linkage_stage125.csv",
    "project/stage125/part3b_capture_attempt_log_stage125.csv",
    "project/stage125/part3b_capture_network_log_stage125.json",
    "project/stage125/part3b_pair_candidate_assessment_stage125.csv",
    "project/stage125/part3b_accessibility_scores_stage125.csv",
    "project/stage125/part3b_gate_results_stage125.csv",
    "project/stage125/part3b_gate_summary_stage125.json",
    "project/stage125/part3b_unresolved_and_failures_stage125.csv",
    "project/stage125/part3b_decision_requirements_stage125.json",
    "project/stage125/README_STAGE125_PART3B_EVIDENCE_CAPTURE.md",
    "project/stage125/README_STAGE125_PART3B1_FEATURE_DEFINITION_SCORING_ADJUDICATION.md",
    "project/stage125/stage125_part3b_evidence_capture_qc_report.json",
    "project/stage125/metadata_and_hashes_stage125_part3b.json",
    # Stage125 Part 3B.1 generated decision-lock artifacts (runner output only).
    "project/stage125/part3b1_decision_lock_stage125.json",
    "project/stage125/part3b1_adjudicated_decision_requirements_stage125.json",
    "project/stage125/part3b1_m2_feature_formula_contract_stage125.json",
    "project/stage125/part3b1_m3_cbi_policy_contract_stage125.json",
    "project/stage125/part3b1_m4_feature_definition_contract_stage125.json",
    "project/stage125/part3b1_rubric_operational_mapping_stage125.json",
    "project/stage125/part3b1_cutoff_available_at_contract_stage125.json",
    "project/stage125/part3b1_selected_decisions_stage125.csv",
    "project/stage125/README_STAGE125_PART3B1_DECISION_LOCK.md",
    "project/stage125/stage125_part3b1_decision_lock_qc_report.json",
    "project/stage125/metadata_and_hashes_stage125_part3b1.json",
    # Stage125 Part 3B.1A generated available-at operationalization lock artifacts.
    "project/stage125/README_STAGE125_PART3B1A_CUT_A_AVAILABLE_AT_LOCK.md",
    "project/stage125/part3b1a_cut_a_available_at_operationalization_contract_stage125.json",
    "project/stage125/part3b1a_cut_a_available_at_decision_lock_stage125.json",
    "project/stage125/stage125_part3b1a_cut_a_available_at_qc_report.json",
    "project/stage125/metadata_and_hashes_stage125_part3b1a.json",
    # Stage125 Part 3B.1B generated document-binding mini-pilot artifacts.
    "project/stage125/README_STAGE125_PART3B1B_CODAL_DOCUMENT_BINDING.md",
    "project/stage125/part3b1b_predictor_document_scope_stage125.csv",
    "project/stage125/part3b1b_codal_document_evidence_stage125.csv",
    "project/stage125/part3b1b_document_binding_adjudication_stage125.csv",
    "project/stage125/part3b1b_capture_attempt_log_stage125.csv",
    "project/stage125/part3b1b_network_log_stage125.json",
    "project/stage125/part3b1b_unresolved_and_rejections_stage125.csv",
    "project/stage125/part3b1b_thanusa_capture_receipt_stage125.json",
    "project/stage125/part3b1b_thanusa_parsed_metadata_receipt_stage125.json",
    "project/stage125/stage125_part3b1b_codal_document_binding_qc_report.json",
    "project/stage125/metadata_and_hashes_stage125_part3b1b.json",
    # Stage125 Part 3B.1C generated decision-lock artifacts.
    "project/stage125/README_STAGE125_PART3B1C_DOCUMENT_BINDING_RESOLUTION.md",
    "project/stage125/part3b1c_binding_failure_taxonomy_stage125.csv",
    "project/stage125/part3b1c_identity_normalization_contract_stage125.json",
    "project/stage125/part3b1c_exact_document_evidence_hierarchy_stage125.json",
    "project/stage125/part3b1c_row_resolution_requirements_stage125.csv",
    "project/stage125/part3b1c_proposed_capture_authorization_stage125.json",
    "project/stage125/part3b1c_scale_up_readiness_decision_stage125.json",
    "project/stage125/part3b1c_document_binding_resolution_decision_lock_stage125.json",
    "project/stage125/stage125_part3b1c_document_binding_resolution_qc_report.json",
    "project/stage125/metadata_and_hashes_stage125_part3b1c.json",
    # Stage125 Part 3B.1E generated conservative-lag decision-lock artifacts.
    "project/stage125/README_STAGE125_PART3B1E_CONSERVATIVE_LAG.md",
    "project/stage125/part3b1e_conservative_lag_decision_lock_stage125.json",
    "project/stage125/part3b1e_frozen_financial_data_manifest_stage125.json",
    "project/stage125/stage125_part3b1e_conservative_lag_qc_report.json",
    "project/stage125/metadata_and_hashes_stage125_part3b1e.json",
    # Stage125 Part 3C generated leakage-safe dataset artifacts.
    "project/stage125/README_STAGE125_PART3C_LEAKAGE_SAFE_DATASET.md",
    "project/stage125/part3c_leakage_safe_dataset_contract_stage125.json",
    "project/stage125/part3c_four_month_regulatory_lag_revision_decision_stage125.json",
    "project/stage125/README_STAGE125_PART3C_FOUR_MONTH_LAG_REVISION.md",
    "project/stage125/part3c_input_hash_manifest_stage125.json",
    "project/stage125/part3c_column_role_map_stage125.csv",
    "project/stage125/part3c_sample_summary_stage125.csv",
    "project/stage125/part3c_target_year_distribution_stage125.csv",
    "project/stage125/part3c_leakage_audit_stage125.csv",
    "project/stage125/stage125_part3c_leakage_safe_dataset_qc_report.json",
    "project/stage125/metadata_and_hashes_stage125_part3c.json",
    # Stage125 Part 4 generated statistical-analysis-plan artifacts.
    "project/stage125/README_STAGE125_PART4_STATISTICAL_ANALYSIS_PLAN.md",
    "project/stage125/part4_statistical_analysis_plan_stage125.json",
    "project/stage125/part4_feature_sets_stage125.csv",
    "project/stage125/part4_feature_exclusion_decisions_stage125.csv",
    "project/stage125/part4_sample_target_matrix_stage125.csv",
    "project/stage125/part4_temporal_split_contract_stage125.json",
    "project/stage125/part4_temporal_split_manifest_stage125.csv",
    "project/stage125/part4_event_count_gate_stage125.csv",
    "project/stage125/part4_development_feature_coverage_audit_stage125.csv",
    "project/stage125/part4_preprocessing_contract_stage125.json",
    "project/stage125/part4_model_specifications_stage125.json",
    "project/stage125/part4_hyperparameter_budget_stage125.json",
    "project/stage125/part4_metrics_uncertainty_contract_stage125.json",
    "project/stage125/part4_shap_stability_contract_stage125.json",
    "project/stage125/part4_revenue_growth_exclusion_revision_decision_stage125.json",
    "project/stage125/README_STAGE125_PART4_REVENUE_GROWTH_EXCLUSION_REVISION.md",
    "project/stage125/stage125_part4_statistical_analysis_plan_qc_report.json",
    "project/stage125/metadata_and_hashes_stage125_part4.json",
    # Stage125 Part 5 generated readiness-closure artifacts.
    "project/stage125/README_STAGE125_PART5_READINESS_CLOSURE.md",
    "project/stage125/part5_readiness_closure_report_stage125.json",
    "project/stage125/part5_keep_drop_decisions_stage125.csv",
    "project/stage125/part5_blocker_register_stage125.csv",
    "project/stage125/part5_stage126_m1_entry_contract_stage125.json",
    "project/stage125/part5_artifact_integrity_manifest_stage125.csv",
    "project/stage125/stage125_part5_readiness_closure_qc_report.json",
    "project/stage125/metadata_and_hashes_stage125_part5.json",
    # Stage126 M1 primary development-fold tuning generated artifacts.
    "project/stage126/stage126_m1_human_authorization_record.json",
    "project/stage126/stage126_m1_development_access_manifest.csv",
    "project/stage126/stage126_m1_final_test_lock_guard.json",
    "project/stage126/stage126_m1_configuration_registry.csv",
    "project/stage126/stage126_m1_tuning_results.csv",
    "project/stage126/stage126_m1_selected_configurations.json",
    "project/stage126/stage126_m1_development_oof_predictions.csv",
    "project/stage126/stage126_m1_development_metrics.csv",
    "project/stage126/stage126_m1_primary_development_lock.json",
    "project/stage126/README_STAGE126_M1_PRIMARY_DEVELOPMENT_TUNING.md",
    "project/stage126/stage126_m1_primary_development_tuning_qc_report.json",
    "project/stage126/metadata_and_hashes_stage126_m1_primary_development_tuning.json",
    # Stage126 M1 robustness Part 0 decision-lock deliverables + generated QC.
    "project/stage126/stage126_m1_robustness_part0_decision_record.json",
    "project/stage126/README_STAGE126_M1_ROBUSTNESS_PART0_DECISION_LOCK.md",
    "project/stage126/stage126_m1_robustness_part0_decision_lock_qc_report.json",
    "project/stage126/metadata_and_hashes_stage126_m1_robustness_part0_decision_lock.json",
    # Stage126 M1 robustness Part 1 generated scientific artifacts.
    "project/stage126/stage126_m1_robustness_part1_human_authorization_record.json",
    "project/stage126/stage126_m1_robustness_part1_feature_manifest.csv",
    "project/stage126/stage126_m1_robustness_part1_execution_manifest.json",
    "project/stage126/stage126_m1_robustness_part1_oof_predictions.csv",
    "project/stage126/stage126_m1_robustness_part1_metrics.csv",
    "project/stage126/stage126_m1_robustness_part1_completion_lock.json",
    "project/stage126/stage126_m1_robustness_part1_primary_comparison.json",
    "project/stage126/stage126_m1_robustness_part1_part5_successor_compatibility.json",
    "project/stage126/README_STAGE126_M1_ROBUSTNESS_PART1_TARGET_PROXIMITY.md",
    "project/stage126/stage126_m1_robustness_part1_qc_report.json",
    "project/stage126/metadata_and_hashes_stage126_m1_robustness_part1.json",
    # Stage126 M1 robustness Part 2 generated scientific artifacts.
    "project/stage126/stage126_m1_robustness_part2_human_authorization_record.json",
    "project/stage126/stage126_m1_robustness_part2_feature_manifest.csv",
    "project/stage126/stage126_m1_robustness_part2_sample_delta.csv",
    "project/stage126/stage126_m1_robustness_part2_execution_manifest.json",
    "project/stage126/stage126_m1_robustness_part2_oof_predictions.csv",
    "project/stage126/stage126_m1_robustness_part2_metrics.csv",
    "project/stage126/stage126_m1_robustness_part2_completion_lock.json",
    "project/stage126/stage126_m1_robustness_part2_primary_comparison.json",
    "project/stage126/stage126_m1_robustness_part2_part5_successor_compatibility.json",
    "project/stage126/README_STAGE126_M1_ROBUSTNESS_PART2_LISTING_RULE_B.md",
    "project/stage126/stage126_m1_robustness_part2_qc_report.json",
    "project/stage126/metadata_and_hashes_stage126_m1_robustness_part2.json",
    # Stage126 M1 robustness Part 3 generated scientific artifacts.
    "project/stage126/stage126_m1_robustness_part3_human_authorization_record.json",
    "project/stage126/stage126_m1_robustness_part3_feature_manifest.csv",
    "project/stage126/stage126_m1_robustness_part3_sample_delta.csv",
    "project/stage126/stage126_m1_robustness_part3_execution_manifest.json",
    "project/stage126/stage126_m1_robustness_part3_oof_predictions.csv",
    "project/stage126/stage126_m1_robustness_part3_metrics.csv",
    "project/stage126/stage126_m1_robustness_part3_primary_comparison.json",
    "project/stage126/stage126_m1_robustness_part3_completion_lock.json",
    "project/stage126/README_STAGE126_M1_ROBUSTNESS_PART3_EXPANDED_RULE_A.md",
    "project/stage126/stage126_m1_robustness_part3_qc_report.json",
    "project/stage126/metadata_and_hashes_stage126_m1_robustness_part3.json",
    # Stage126 M1 robustness Part 5 generated scientific artifacts (no
    # sample-delta artifact: the sample is unchanged from the primary sample).
    "project/stage126/stage126_m1_robustness_part5_human_authorization_record.json",
    "project/stage126/stage126_m1_robustness_part5_feature_manifest.csv",
    "project/stage126/stage126_m1_robustness_part5_execution_manifest.json",
    "project/stage126/stage126_m1_robustness_part5_oof_predictions.csv",
    "project/stage126/stage126_m1_robustness_part5_metrics.csv",
    "project/stage126/stage126_m1_robustness_part5_primary_comparison.json",
    "project/stage126/stage126_m1_robustness_part5_completion_lock.json",
    "project/stage126/README_STAGE126_M1_ROBUSTNESS_PART5_PERSISTENT_LOSS_TARGET.md",
    "project/stage126/stage126_m1_robustness_part5_qc_report.json",
    "project/stage126/metadata_and_hashes_stage126_m1_robustness_part5.json",
    # Stage126 validation-architecture boundary artifacts.
    "project/stage126/stage126_validation_architecture_boundary_decision.json",
    "project/stage126/stage126_historical_boundary_manifest.json",
    "project/stage126/stage126_closed_part_registry.json",
    "project/stage126/stage126_current_state_validation_report.json",
    "project/stage126/stage126_live_vs_historical_test_boundary.json",
    "project/stage126/README_STAGE126_CURRENT_STATE_VALIDATION.md",
    "project/stage126/metadata_and_hashes_stage126_current_state_validator.json",
)

# Dependency-contract maintenance classification, INDEPENDENT of the change
# allowlist, Handoff-only classification, and artifact-only classification.
# A commit is "maintenance-only" (and therefore never advances
# last_stage_commit) only when every file it introduces is one of these exact
# curated dependency/environment paths. This keeps dependency-contract PRs
# (e.g. jdatetime pin, Python runtime pin) from advancing the research-stage
# anchor while still allowing mixed commits that touch real research code.
#   * file entries match by EXACT path only (no directory entries).
MAINTENANCE_ONLY_FILES = (
    "project/environment.yml",
    "project/requirements.txt",
    "project/tests/test_dependency_contract.py",
)

FROZEN_MANIFESTS = (
    "project/stage122/metadata_and_hashes_stage122.json",
    "project/stage123/metadata_and_hashes_stage123.json",
    "project/stage124/metadata_and_hashes_stage124_batch02_gate_b.json",
    "project/stage125/metadata_and_hashes_stage125_part1.json",
    "project/stage125/metadata_and_hashes_stage125_part2.json",
    "project/stage125/metadata_and_hashes_stage125_part3a.json",
    "project/stage125/metadata_and_hashes_stage125_part3a_decision_lock.json",
)

# Tracked files declared in a frozen manifest that are EXPLICITLY classified as
# regenerable / non-frozen, and therefore allowed to mismatch without aborting.
# Each entry must have a documented reason.
NON_FROZEN_TRACKED = {
    # pytest log: last line "N passed in X.XXs" embeds a non-deterministic wall
    # time, so the byte content (and SHA) varies per run while the tests pass.
    "project/stage123/stage123_unit_test_output.txt",
}

# Explicit, allow-listed workflow markers (NOT broad filename search). Legacy
# Stage121 artifacts under outputs/04_models/ must never flip these to True.
VERIFIED_MASTER_PATH = "project/stage124/listing_master_verified_stage124.csv"
GATE_B_MARKER_PATHS = (
    "project/stage124/stage124_batch02_gate_b_qc_report.json",
    "project/stage124/metadata_and_hashes_stage124_batch02_gate_b.json",
)
MODELING_MARKER_PATHS = (
    "project/outputs/stage_modeling/run_manifest.json",
)

# handoff_state.json fields that are informational / HEAD-relative and must be
# EXCLUDED from the full semantic-projection equality check.
VOLATILE_FIELDS = frozenset({
    "generated_at_utc",
    "observed_branch",
    "observed_repository_head_commit",
    "generated_from_commit",
    "baseline_commit",
    # The live evidence-capture PR head is the CURRENT repository head, so it
    # is HEAD-relative by construction and must never be pinned to a stale SHA.
    "stage128_m3i2_live_pr_head_commit",
})

GENERATOR_VERSION = 2

# QC workflow markers propagated into handoff_state.json (fail-closed per scope).
QC_WORKFLOW_FIELDS_BY_SCOPE: dict[str, tuple[str, ...]] = {
    "stage125_part3a_pilot_protocol": (
        "part3a_protocol_locked",
        "part3b_started",
    ),
    "stage125_part3a_decision_lock": (
        "part3a_protocol_locked",
        "part3a_decision_locked",
        "part3b_started",
    ),
    "stage125_part3b0_evidence_readiness": (
        "part3a_protocol_locked",
        "part3a_decision_locked",
        "part3b0_readiness",
        "part3b_started",
        "evidence_collected",
        "accessibility_scoring_applied",
        "network_extraction_performed",
        "modeling_started",
    ),
    "stage125_part3b_evidence_capture": (
        "part3a_protocol_locked",
        "part3a_decision_locked",
        "part3b0_readiness",
        "part3b_started",
        "evidence_collected",
        "endpoint_probe_evidence_collected",
        "candidate_value_evidence_collected",
        "pair_level_evidence_collected",
        "data_value_extraction_performed",
        "accessibility_scoring_applied",
        "part3b_completed",
        "network_extraction_performed",
        "modeling_started",
    ),
    "stage125_part3b1_decision_lock": (
        "part3a_protocol_locked",
        "part3a_decision_locked",
        "part3b0_readiness",
        "part3b_started",
        "part3b1_decision_locked",
        "evidence_collected",
        "endpoint_probe_evidence_collected",
        "candidate_value_evidence_collected",
        "pair_level_evidence_collected",
        "data_value_extraction_performed",
        "accessibility_scoring_applied",
        "part3b_completed",
        "network_extraction_performed",
        "modeling_started",
    ),
    "stage125_part3b1a_cut_a_available_at_operationalization_lock": (
        "part3a_protocol_locked",
        "part3a_decision_locked",
        "part3b0_readiness",
        "part3b_started",
        "part3b1_decision_locked",
        "cut_a_available_at_operationalization_locked",
        "evidence_collected",
        "endpoint_probe_evidence_collected",
        "predictor_available_at_evidence_collected",
        "pilot_cutoff_provenance_resolved",
        "candidate_value_evidence_collected",
        "pair_level_evidence_collected",
        "data_value_extraction_performed",
        "accessibility_scoring_applied",
        "part3b_completed",
        "network_extraction_performed",
        "modeling_started",
    ),
    "stage125_part3b1b_codal_document_binding_mini_pilot": (
        "part3a_protocol_locked",
        "part3a_decision_locked",
        "part3b0_readiness",
        "part3b_started",
        "part3b1_decision_locked",
        "cut_a_available_at_operationalization_locked",
        "predictor_document_binding_mini_pilot_completed",
        "predictor_document_binding_evidence_collected",
        "predictor_available_at_evidence_collected",
        "pilot_cutoff_provenance_resolved",
        "evidence_collected",
        "endpoint_probe_evidence_collected",
        "candidate_value_evidence_collected",
        "pair_level_evidence_collected",
        "data_value_extraction_performed",
        "accessibility_scoring_applied",
        "part3b_completed",
        "network_extraction_performed",
        "modeling_started",
    ),
    "stage125_part3b1c_document_binding_resolution_decision_lock": (
        "part3a_protocol_locked",
        "part3a_decision_locked",
        "part3b0_readiness",
        "part3b_started",
        "part3b1_decision_locked",
        "cut_a_available_at_operationalization_locked",
        "predictor_document_binding_mini_pilot_completed",
        "predictor_document_binding_evidence_collected",
        "document_binding_resolution_decision_locked",
        "predictor_available_at_evidence_collected",
        "pilot_cutoff_provenance_resolved",
        "evidence_collected",
        "endpoint_probe_evidence_collected",
        "candidate_value_evidence_collected",
        "pair_level_evidence_collected",
        "data_value_extraction_performed",
        "accessibility_scoring_applied",
        "part3b_completed",
        "network_extraction_performed",
        "modeling_started",
    ),
    "stage125_part3b1e_conservative_six_month_lag_decision_lock": (
        "part3a_protocol_locked",
        "part3a_decision_locked",
        "part3b0_readiness",
        "part3b_started",
        "part3b1_decision_locked",
        "cut_a_available_at_operationalization_locked",
        "predictor_document_binding_mini_pilot_completed",
        "predictor_document_binding_evidence_collected",
        "document_binding_resolution_decision_locked",
        "conservative_six_month_lag_decision_locked",
        "broad_codal_capture_stopped",
        "financial_data_researcher_verified_frozen",
        "conservative_availability_lag_locked",
        "conservative_lag_months",
        "row_level_publish_datetime_collection_required",
        "predictor_available_at_evidence_collected",
        "pilot_cutoff_provenance_resolved",
        "evidence_collected",
        "endpoint_probe_evidence_collected",
        "candidate_value_evidence_collected",
        "pair_level_evidence_collected",
        "data_value_extraction_performed",
        "accessibility_scoring_applied",
        "part3b_completed",
        "network_extraction_performed",
        "modeling_started",
    ),
    "stage125_part3c_leakage_safe_dataset_finalization": (
        "part3a_protocol_locked",
        "part3a_decision_locked",
        "part3b0_readiness",
        "part3b_started",
        "part3b1_decision_locked",
        "cut_a_available_at_operationalization_locked",
        "predictor_document_binding_mini_pilot_completed",
        "predictor_document_binding_evidence_collected",
        "document_binding_resolution_decision_locked",
        "conservative_six_month_lag_decision_locked",
        "broad_codal_capture_stopped",
        "financial_data_researcher_verified_frozen",
        "conservative_availability_lag_locked",
        "row_level_publish_datetime_collection_required",
        "active_availability_method",
        "active_availability_lag_months",
        "four_month_regulatory_lag_locked",
        "six_month_lag_superseded",
        "historical_six_month_decision_retained",
        "historical_six_month_decision_active",
        "predictor_available_at_evidence_collected",
        "pilot_cutoff_provenance_resolved",
        "evidence_collected",
        "endpoint_probe_evidence_collected",
        "candidate_value_evidence_collected",
        "pair_level_evidence_collected",
        "data_value_extraction_performed",
        "accessibility_scoring_applied",
        "part3b_completed",
        "part3c_leakage_safe_finalization_completed",
        "network_extraction_performed",
        "modeling_started",
    ),
    "stage125_part4_statistical_analysis_plan": (
        "part3a_protocol_locked",
        "part3a_decision_locked",
        "part3b0_readiness",
        "part3b_started",
        "part3b1_decision_locked",
        "cut_a_available_at_operationalization_locked",
        "predictor_document_binding_mini_pilot_completed",
        "predictor_document_binding_evidence_collected",
        "document_binding_resolution_decision_locked",
        "conservative_six_month_lag_decision_locked",
        "broad_codal_capture_stopped",
        "financial_data_researcher_verified_frozen",
        "conservative_availability_lag_locked",
        "row_level_publish_datetime_collection_required",
        "active_availability_method",
        "active_availability_lag_months",
        "four_month_regulatory_lag_locked",
        "six_month_lag_superseded",
        "historical_six_month_decision_retained",
        "historical_six_month_decision_active",
        "predictor_available_at_evidence_collected",
        "pilot_cutoff_provenance_resolved",
        "evidence_collected",
        "endpoint_probe_evidence_collected",
        "candidate_value_evidence_collected",
        "pair_level_evidence_collected",
        "data_value_extraction_performed",
        "accessibility_scoring_applied",
        "part3b_completed",
        "part3c_leakage_safe_finalization_completed",
        "part4_statistical_analysis_plan_locked",
        "contract_version",
        "network_extraction_performed",
        "modeling_started",
    ),
    "stage125_part5_readiness_closure": (
        "part3a_protocol_locked",
        "part3a_decision_locked",
        "part3b0_readiness",
        "part3b_started",
        "part3b1_decision_locked",
        "cut_a_available_at_operationalization_locked",
        "predictor_document_binding_mini_pilot_completed",
        "predictor_document_binding_evidence_collected",
        "document_binding_resolution_decision_locked",
        "conservative_six_month_lag_decision_locked",
        "broad_codal_capture_stopped",
        "financial_data_researcher_verified_frozen",
        "conservative_availability_lag_locked",
        "row_level_publish_datetime_collection_required",
        "active_availability_method",
        "active_availability_lag_months",
        "four_month_regulatory_lag_locked",
        "six_month_lag_superseded",
        "historical_six_month_decision_retained",
        "historical_six_month_decision_active",
        "predictor_available_at_evidence_collected",
        "pilot_cutoff_provenance_resolved",
        "evidence_collected",
        "endpoint_probe_evidence_collected",
        "candidate_value_evidence_collected",
        "pair_level_evidence_collected",
        "data_value_extraction_performed",
        "accessibility_scoring_applied",
        "part3b_completed",
        "part3c_leakage_safe_finalization_completed",
        "part4_statistical_analysis_plan_locked",
        "stage125_part5_readiness_closure_completed",
        "stage125_completed",
        "stage126_m1_entry_ready",
        "stage126_authorized",
        "stage126_started",
        "modeling_authorized",
        "modeling_started",
        "final_test_unlocked",
        "contract_version",
        "network_extraction_performed",
    ),
    "stage126_m1_financial_baseline": (
        "stage125_completed",
        "stage126_m1_entry_ready",
        "stage126_authorized",
        "stage126_started",
        "development_modeling_authorized",
        "modeling_authorized",
        "modeling_started",
        "final_test_unlocked",
        "final_test_access_authorized",
        "final_test_predictor_values_inspected",
        "final_test_target_values_inspected",
        "final_test_evaluation_performed",
        "m1_primary_development_tuning_completed",
        "m1_robustness_started",
        "m1_robustness_completed",
        "m2_data_collected",
        "m3_data_collected",
        "m4_data_collected",
        "contract_version",
    ),
    # Stage126 M1 robustness Part 1 inherits the unchanged Stage126 markers and
    # adds the Part 1 completion state.
    "stage126_m1_robustness_part1_target_proximity": (
        "stage125_completed",
        "stage126_m1_entry_ready",
        "stage126_authorized",
        "stage126_started",
        "development_modeling_authorized",
        "modeling_authorized",
        "modeling_started",
        "final_test_unlocked",
        "final_test_access_authorized",
        "final_test_predictor_values_inspected",
        "final_test_target_values_inspected",
        "final_test_evaluation_performed",
        "m1_primary_development_tuning_completed",
        "m1_robustness_started",
        "m1_robustness_completed",
        "m1_robustness_part1_human_authorized",
        "m1_robustness_part1_completed",
        "m1_robustness_completed_category_ids",
        "m1_robustness_next_category_id",
        "m1_robustness_part2_authorized",
        "full_development_refit_performed",
        "m2_data_collected",
        "m3_data_collected",
        "m4_data_collected",
        "contract_version",
    ),
    # Stage126 M1 robustness Part 3 inherits the unchanged Stage126 markers and
    # adds the Part 3 completion state on top of the retained Part 1/2 state.
    "stage126_m1_robustness_part3_expanded_rule_a": (
        "stage125_completed",
        "stage126_m1_entry_ready",
        "stage126_authorized",
        "stage126_started",
        "development_modeling_authorized",
        "modeling_authorized",
        "modeling_started",
        "final_test_unlocked",
        "final_test_access_authorized",
        "final_test_predictor_values_inspected",
        "final_test_target_values_inspected",
        "final_test_evaluation_performed",
        "m1_primary_development_tuning_completed",
        "m1_robustness_started",
        "m1_robustness_completed",
        "m1_robustness_part1_completed",
        "m1_robustness_part2_completed",
        "m1_robustness_part3_human_authorized",
        "m1_robustness_part3_completed",
        "m1_robustness_completed_category_ids",
        "m1_robustness_next_category_id",
        "m1_robustness_part4_authorized",
        "full_development_refit_performed",
        "m2_data_collected",
        "m3_data_collected",
        "m4_data_collected",
        "contract_version",
    ),
    # Stage126 M1 robustness Part 4 inherits the unchanged Stage126 markers and
    # adds the Part 4 completion state on top of the retained Part 1/2/3 state.
    "stage126_m1_robustness_part4_expanded_rule_b": (
        "stage125_completed",
        "stage126_m1_entry_ready",
        "stage126_authorized",
        "stage126_started",
        "development_modeling_authorized",
        "modeling_authorized",
        "modeling_started",
        "final_test_unlocked",
        "final_test_access_authorized",
        "final_test_predictor_values_inspected",
        "final_test_target_values_inspected",
        "final_test_evaluation_performed",
        "m1_primary_development_tuning_completed",
        "m1_robustness_started",
        "m1_robustness_completed",
        "m1_robustness_part1_completed",
        "m1_robustness_part2_completed",
        "m1_robustness_part3_completed",
        "m1_robustness_part4_human_authorized",
        "m1_robustness_part4_completed",
        "m1_robustness_completed_category_ids",
        "m1_robustness_next_category_id",
        "m1_robustness_part5_authorized",
        "full_development_refit_performed",
        "m2_data_collected",
        "m3_data_collected",
        "m4_data_collected",
        "contract_version",
    ),
    # Stage126 M1 robustness Part 5 inherits the unchanged Stage126 markers and
    # adds the Part 5 completion state on top of the retained Part 1/2/3/4 state.
    "stage126_m1_robustness_part5_persistent_loss_target": (
        "stage125_completed",
        "stage126_m1_entry_ready",
        "stage126_authorized",
        "stage126_started",
        "development_modeling_authorized",
        "modeling_authorized",
        "modeling_started",
        "final_test_unlocked",
        "final_test_access_authorized",
        "final_test_predictor_values_inspected",
        "final_test_target_values_inspected",
        "final_test_evaluation_performed",
        "m1_primary_development_tuning_completed",
        "m1_robustness_started",
        "m1_robustness_completed",
        "m1_robustness_part1_completed",
        "m1_robustness_part2_completed",
        "m1_robustness_part3_completed",
        "m1_robustness_part4_completed",
        "m1_robustness_part5_human_authorized",
        "m1_robustness_part5_completed",
        "m1_robustness_completed_category_ids",
        "m1_robustness_next_category_id",
        "m1_robustness_part6_authorized",
        "full_development_refit_performed",
        "m2_data_collected",
        "m3_data_collected",
        "m4_data_collected",
        "contract_version",
    ),
    # Stage126 M1 robustness Part 2 inherits the unchanged Stage126 markers and
    # adds the Part 2 completion state on top of the retained Part 1 state.
    "stage126_m1_robustness_part2_listing_rule_b": (
        "stage125_completed",
        "stage126_m1_entry_ready",
        "stage126_authorized",
        "stage126_started",
        "development_modeling_authorized",
        "modeling_authorized",
        "modeling_started",
        "final_test_unlocked",
        "final_test_access_authorized",
        "final_test_predictor_values_inspected",
        "final_test_target_values_inspected",
        "final_test_evaluation_performed",
        "m1_primary_development_tuning_completed",
        "m1_robustness_started",
        "m1_robustness_completed",
        "m1_robustness_part1_completed",
        "m1_robustness_part2_human_authorized",
        "m1_robustness_part2_completed",
        "m1_robustness_completed_category_ids",
        "m1_robustness_next_category_id",
        "m1_robustness_part3_authorized",
        "full_development_refit_performed",
        "m2_data_collected",
        "m3_data_collected",
        "m4_data_collected",
        "contract_version",
    ),
    # Stage126 M1 robustness Part 6 inherits the unchanged Stage126 markers,
    # adds the Part 6 completion state on top of the retained Part 1-5 state,
    # and closes the six-category M1 robustness set.
    "stage126_m1_robustness_part6_smote_training_fold_only": (
        "stage125_completed",
        "stage126_m1_entry_ready",
        "stage126_authorized",
        "stage126_started",
        "development_modeling_authorized",
        "modeling_authorized",
        "modeling_started",
        "final_test_unlocked",
        "final_test_access_authorized",
        "final_test_predictor_values_inspected",
        "final_test_target_values_inspected",
        "final_test_evaluation_performed",
        "m1_primary_development_tuning_completed",
        "m1_robustness_started",
        "m1_robustness_completed",
        "m1_robustness_part1_completed",
        "m1_robustness_part2_completed",
        "m1_robustness_part3_completed",
        "m1_robustness_part4_completed",
        "m1_robustness_part5_completed",
        "m1_robustness_part6_human_authorized",
        "m1_robustness_part6_completed",
        "m1_robustness_completed_category_ids",
        "m1_robustness_next_category_id",
        "full_development_refit_performed",
        "m2_data_collected",
        "m3_data_collected",
        "m4_data_collected",
        "contract_version",
    ),
}

# Repository-wide temporal-availability invariants carried into Stage126 Handoff
# scope. Values are derived from frozen Stage125 contracts/artifacts (never
# invented by the Stage126 QC report). Missing or cross-artifact conflict is
# fatal (fail-closed).
# Every Stage126 QC scope (primary + completed robustness micro-parts) carries
# the repository-wide Stage125 temporal-availability invariants.
STAGE126_QC_SCOPES = frozenset({
    "stage126_m1_financial_baseline",
    "stage126_m1_robustness_part1_target_proximity",
    "stage126_m1_robustness_part2_listing_rule_b",
    "stage126_m1_robustness_part3_expanded_rule_a",
    "stage126_m1_robustness_part4_expanded_rule_b",
    "stage126_m1_robustness_part5_persistent_loss_target",
    "stage126_m1_robustness_part6_smote_training_fold_only",
})

STAGE126_CARRIED_TEMPORAL_AVAILABILITY_FIELDS = (
    "financial_data_researcher_verified_frozen",
    "broad_codal_capture_stopped",
    "active_availability_method",
    "active_availability_lag_months",
    "four_month_regulatory_lag_locked",
    "six_month_lag_superseded",
    "historical_six_month_decision_retained",
    "row_level_publish_datetime_collection_required",
    "part3b_completed",
    "part3c_leakage_safe_finalization_completed",
    "part4_statistical_analysis_plan_locked",
    "stage125_completed",
)

_STAGE125_PART3B1E_LOCK_REL = (
    "project/stage125/part3b1e_conservative_lag_decision_lock_stage125.json"
)
_STAGE125_PART3C_FOUR_MONTH_REL = (
    "project/stage125/part3c_four_month_regulatory_lag_revision_decision_stage125.json"
)
_STAGE125_PART3C_CONTRACT_REL = (
    "project/stage125/part3c_leakage_safe_dataset_contract_stage125.json"
)
_STAGE125_PART4_SAP_REL = (
    "project/stage125/part4_statistical_analysis_plan_stage125.json"
)
_STAGE125_PART5_CLOSURE_REL = (
    "project/stage125/part5_readiness_closure_report_stage125.json"
)


class HandoffError(RuntimeError):
    """Fatal, fail-closed error during extraction/generation."""


# --------------------------------------------------------------------------- #
# Git helpers
# --------------------------------------------------------------------------- #

def _git(repo_root: str, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", repo_root, *args], capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise HandoffError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def repo_root() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError as exc:  # pragma: no cover - env guard
        raise HandoffError(f"not inside a git repository: {exc.stderr}") from exc


def head_commit(root: str) -> str:
    return _git(root, "rev-parse", "HEAD")


def current_branch(root: str) -> str:
    return _git(root, "rev-parse", "--abbrev-ref", "HEAD")


def is_ancestor(root: str, ancestor: str, descendant: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", root, "merge-base", "--is-ancestor", ancestor, descendant],
        capture_output=True, text=True,
    )
    return proc.returncode == 0


def _commit_parents(root: str, sha: str) -> list[str]:
    """Return parent SHAs for ``sha`` (empty for a root commit)."""
    parts = _git(root, "rev-list", "--parents", "-n", "1", sha).split()
    return parts[1:]


def _commit_tree(root: str, sha: str) -> str:
    """Return the tree SHA for ``sha``."""
    return _git(root, "rev-parse", f"{sha}^{{tree}}")


def _is_content_preserving_merge(root: str, sha: str) -> bool:
    """True when ``sha`` is a two-parent merge whose tree equals parent 2.

    Such merges introduce no unique tree content of their own (typical clean
    GitHub --no-ff merges). They must not become ``last_stage_commit``.
    """
    parents = _commit_parents(root, sha)
    if len(parents) != 2:
        return False
    return _commit_tree(root, sha) == _commit_tree(root, parents[1])


def _introduced_files(root: str, sha: str) -> list[str]:
    """Files a commit introduced relative to its first parent.

    Works for merge commits too (diff against the first parent shows what the
    merge brought in). The root commit (no parent) lists all its files.
    """
    parents = _commit_parents(root, sha)
    if not parents:
        out = _git(root, "show", "--no-renames", "--name-only", "--format=", sha)
    else:
        out = _git(root, "diff", "--no-renames", "--name-only", f"{sha}^1", sha)
    return [line for line in out.splitlines() if line.strip()]


def path_allowlisted(path: str) -> bool:
    """Change allowlist: directory => startswith(dir); file => exact.

    Controls which paths a Handoff-maintenance PR may modify. This is a broader
    set than the Handoff-only classification and MUST NOT be used to decide
    whether a commit advances last_stage_commit.
    """
    if path in ALLOWLIST_FILES:
        return True
    return any(path.startswith(d) for d in ALLOWLIST_DIRS)


def path_handoff_only(path: str) -> bool:
    """Handoff-only classification: directory => startswith(dir); file => exact.

    A strict, independent subset used solely by last_stage_commit() to skip pure
    Handoff-maintenance commits. Research / maintenance-task code (e.g. Stage125
    Part 1) is intentionally NOT handoff-only, so such commits still advance the
    stage anchor even though they are change-allowlisted.
    """
    if path in HANDOFF_ONLY_FILES:
        return True
    return any(path.startswith(d) for d in HANDOFF_ONLY_DIRS)


def path_artifact_only(path: str) -> bool:
    """Generated-artifact-only classification: EXACT file match only.

    A strict, independent subset used solely by last_stage_commit() to skip
    commits that only regenerate a QC report / metadata_and_hashes hash
    manifest. See ARTIFACT_ONLY_FILES for the curation rules.
    """
    return path in ARTIFACT_ONLY_FILES


def path_maintenance_only(path: str) -> bool:
    """Dependency-contract maintenance classification: EXACT file match only.

    A strict, independent subset used solely by last_stage_commit() to skip
    commits that only touch curated dependency/environment contract files.
    See MAINTENANCE_ONLY_FILES for the curation rules.
    """
    return path in MAINTENANCE_ONLY_FILES


def _is_handoff_only(files: list[str]) -> bool:
    if not files:
        return False
    return all(path_handoff_only(f) for f in files)


def _is_artifact_only(files: list[str]) -> bool:
    if not files:
        return False
    return all(path_artifact_only(f) for f in files)


def _is_maintenance_only(files: list[str]) -> bool:
    if not files:
        return False
    return all(path_maintenance_only(f) for f in files)


def _is_stage_relevant(files: list[str]) -> bool:
    """True iff at least one introduced file is REAL content — i.e. neither
    Handoff-only infrastructure, a curated generated artifact, nor a
    dependency-contract maintenance file.

    This is deliberately PATH-BASED / SEMANTIC, not wording-based: it does not
    inspect the commit subject or body at all. A commit that changes
    ``project/src/stage124_gate_b_execution.py`` and
    ``project/tests/test_stage124_gate_b_execution.py`` is stage-relevant
    whether its subject is ``fix(qc-scan): ...`` or ``Stage124: ...`` — the
    message text is irrelevant to the classification.
    """
    return any(
        not path_handoff_only(f)
        and not path_artifact_only(f)
        and not path_maintenance_only(f)
        for f in files
    )


def last_stage_commit(root: str) -> str:
    """Latest reachable commit that introduces real (non-Handoff-only,
    non-artifact-only, non-maintenance-only) content.

    PATH-BASED / SEMANTIC, NOT message-wording-dependent: this walks commit
    history from HEAD and returns the first (i.e. most recent) commit whose
    introduced files (vs first parent; works for merges too) include at least
    one file that is neither Handoff-only infrastructure, a curated generated
    artifact, nor a dependency-contract maintenance file. A commit whose
    introduced files are ALL Handoff-only is skipped; a commit whose introduced
    files are ALL curated generated artifacts (QC report / metadata_and_hashes
    regeneration) is skipped; a commit whose introduced files are ALL
    dependency-contract maintenance files is skipped; a commit mixing real
    content with any of those (e.g. a source-code fix committed alongside its
    regenerated QC artifact) still qualifies, because only ONE introduced file
    needs to be real content.
    """
    for sha in _git(root, "rev-list", "HEAD").splitlines():
        # Clean GitHub-style merges replay second-parent trees; the real
        # content commits already exist on that parent and must remain the
        # stage anchor (otherwise post-merge last_stage_commit drifts).
        if _is_content_preserving_merge(root, sha):
            continue
        files = _introduced_files(root, sha)
        if _is_stage_relevant(files):
            return sha
    raise HandoffError("no qualifying stage-relevant commit found in history")


def derive_repository(root: str) -> str | None:
    url = _safe(lambda: _git(root, "remote", "get-url", "origin"))
    if not url:
        return None
    m = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?/?$", url)
    return m.group(1) if m else url


# --------------------------------------------------------------------------- #
# Hashing
# --------------------------------------------------------------------------- #

def sha256_file(path: str) -> str | None:
    if not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------- #
# ROADMAP front matter
# --------------------------------------------------------------------------- #

def read_roadmap(root: str) -> dict:
    path = os.path.join(root, "project/docs/ai/ROADMAP.md")
    if not os.path.isfile(path):
        raise HandoffError("ROADMAP.md missing - bootstrap the human files first")
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        raise HandoffError("ROADMAP.md has no YAML front matter")
    fm = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip()
    body = text[m.end():]
    required = (
        "active_research_workstream_id",
        "last_completed_research_action_id",
        "next_research_action_id",
        "active_maintenance_task_id",
    )
    for key in required:
        if key not in fm:
            raise HandoffError(f"ROADMAP front matter missing '{key}'")
    for key in ("last_completed_research_action_id", "next_research_action_id"):
        if fm[key] not in body:
            raise HandoffError(
                f"ROADMAP body does not list action id '{fm[key]}' (from {key})"
            )
    return fm


# --------------------------------------------------------------------------- #
# QC discovery
# --------------------------------------------------------------------------- #

# Limited overrides when QC stage id does not equal the source/test stem.
_QC_SOURCE_TEST_OVERRIDES: dict[str, tuple[str, str]] = {
    "stage125_part3b1a_cut_a_available_at_operationalization_lock": (
        "project/src/stage125_part3b1a_cut_a_available_at_operationalization.py",
        "project/tests/test_stage125_part3b1a_cut_a_available_at_operationalization.py",
    ),
    "stage125_part3b1b_codal_document_binding_mini_pilot": (
        "project/src/stage125_part3b1b_codal_document_binding.py",
        "project/tests/test_stage125_part3b1b_codal_document_binding.py",
    ),
    "stage125_part3b1c_document_binding_resolution_decision_lock": (
        "project/src/stage125_part3b1c_document_binding_resolution.py",
        "project/tests/test_stage125_part3b1c_document_binding_resolution.py",
    ),
    "stage125_part3b1e_conservative_six_month_lag_decision_lock": (
        "project/src/stage125_part3b1e_conservative_lag_decision.py",
        "project/tests/test_stage125_part3b1e_conservative_lag_decision.py",
    ),
    "stage125_part3c_leakage_safe_dataset_finalization": (
        "project/src/stage125_part3c_leakage_safe_dataset_finalization.py",
        "project/tests/test_stage125_part3c_leakage_safe_dataset_finalization.py",
    ),
    "stage125_part4_statistical_analysis_plan": (
        "project/src/stage125_part4_statistical_analysis_plan.py",
        "project/tests/test_stage125_part4_statistical_analysis_plan.py",
    ),
    "stage125_part5_readiness_closure": (
        "project/src/stage125_part5_readiness_closure.py",
        "project/tests/test_stage125_part5_readiness_closure.py",
    ),
    "stage126_m1_financial_baseline": (
        "project/src/stage126_m1_primary_development_tuning.py",
        "project/tests/test_stage126_m1_primary_development_tuning.py",
    ),
    "stage126_m1_robustness_part1_target_proximity": (
        "project/src/stage126_m1_robustness_part1_target_proximity.py",
        "project/tests/test_stage126_m1_robustness_part1_target_proximity.py",
    ),
    "stage126_m1_robustness_part2_listing_rule_b": (
        "project/src/stage126_m1_robustness_part2_listing_rule_b.py",
        "project/tests/test_stage126_m1_robustness_part2_listing_rule_b.py",
    ),
    "stage126_m1_robustness_part3_expanded_rule_a": (
        "project/src/stage126_m1_robustness_part3_expanded_rule_a.py",
        "project/tests/test_stage126_m1_robustness_part3_expanded_rule_a.py",
    ),
}


def _qc_source_test_paths(stage: str) -> tuple[str, str]:
    """Convention: src/<stage>.py and tests/test_<stage>.py (repo-relative)."""
    if stage in _QC_SOURCE_TEST_OVERRIDES:
        return _QC_SOURCE_TEST_OVERRIDES[stage]
    return f"project/src/{stage}.py", f"project/tests/test_{stage}.py"


def derive_stage_batch(qc_stage: str) -> tuple[str | None, str | None]:
    s = re.search(r"stage(\d+)", qc_stage, re.IGNORECASE)
    b = re.search(r"batch(\d+)", qc_stage, re.IGNORECASE)
    return (f"Stage{s.group(1)}" if s else None,
            f"Batch{b.group(1)}" if b else None)


def select_qc_report(root: str, workstream: str, head: str) -> dict:
    """Pick the newest *valid* QC report whose scope matches the workstream."""
    candidates: list[dict] = []
    for dirpath, _dirs, files in os.walk(os.path.join(root, "project")):
        for name in files:
            if not (name.endswith(".json") and "qc" in name.lower()):
                continue
            full = os.path.join(dirpath, name)
            try:
                data = json.load(open(full, encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if data.get("stage") != workstream:
                continue
            required = (
                "source_commit", "source_file_sha256", "test_file_sha256",
                "assertion_count", "failed_count", "all_pass", "tickers",
            )
            if any(k not in data for k in required):
                continue
            data["_path"] = os.path.relpath(full, root)
            candidates.append(data)

    if not candidates:
        raise HandoffError(f"no QC report found with stage == '{workstream}'")

    valid: list[dict] = []
    for data in candidates:
        if not is_ancestor(root, data["source_commit"], head):
            continue
        src_rel, test_rel = _qc_source_test_paths(data["stage"])
        if sha256_file(os.path.join(root, src_rel)) != data["source_file_sha256"]:
            continue
        if sha256_file(os.path.join(root, test_rel)) != data["test_file_sha256"]:
            continue
        data["_source_path"] = src_rel
        data["_test_path"] = test_rel
        valid.append(data)

    if not valid:
        raise HandoffError(
            f"QC report(s) for '{workstream}' exist but none are valid "
            "(unreachable source_commit or source/test fingerprint mismatch)"
        )
    valid.sort(key=lambda d: d.get("generated_at", ""), reverse=True)
    return valid[0]


# --------------------------------------------------------------------------- #
# Frozen assets
# --------------------------------------------------------------------------- #

def _tracked_files(root: str) -> set[str]:
    return set(_git(root, "ls-files").splitlines())


def _is_git_ignored(root: str, path: str) -> bool:
    """True iff `git check-ignore` confirms the path is ignored (rc 0)."""
    proc = subprocess.run(
        ["git", "-C", root, "check-ignore", "-q", "--", path],
        capture_output=True,
    )
    return proc.returncode == 0


def frozen_asset_report(root: str) -> list[dict]:
    """Classify every frozen-manifest file (fail-closed).

    A file is *regenerable* (exempt from hash verification) ONLY when:
      * it is git-tracked and explicitly listed in NON_FROZEN_TRACKED, or
      * it is untracked AND (explicitly NON_FROZEN_TRACKED OR proven gitignored).
    Everything else is *frozen* and must be tracked, present, and matching —
    otherwise the caller treats it as fatal. An untracked, non-ignored,
    unclassified manifest file is therefore fatal (it is not really frozen).
    """
    tracked = _tracked_files(root)
    rows: list[dict] = []
    for manifest_rel in FROZEN_MANIFESTS:
        manifest_path = os.path.join(root, manifest_rel)
        if not os.path.isfile(manifest_path):
            raise HandoffError(f"frozen manifest missing: {manifest_rel}")
        data = json.load(open(manifest_path, encoding="utf-8"))
        outputs = data.get("output_files_sha256", {})
        if not outputs:
            raise HandoffError(f"manifest {manifest_rel} has no output_files_sha256")
        manifest_dir = os.path.dirname(manifest_rel)
        for fname, expected in sorted(outputs.items()):
            file_rel = f"{manifest_dir}/{fname}"
            is_tracked = file_rel in tracked
            classified = file_rel in NON_FROZEN_TRACKED
            if is_tracked:
                regenerable = classified
            else:
                regenerable = classified or _is_git_ignored(root, file_rel)
            frozen = not regenerable
            # Hash only what we must verify (tracked frozen files).
            actual = (sha256_file(os.path.join(root, file_rel))
                      if (frozen and is_tracked) else None)
            rows.append({
                "manifest": manifest_rel,
                "path": file_rel,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "tracked": is_tracked,
                "frozen": frozen,                 # frozen => must be tracked & match
                "exists": os.path.isfile(os.path.join(root, file_rel)),
                "matches": (actual == expected) if (frozen and is_tracked) else None,
            })
    return rows


# --------------------------------------------------------------------------- #
# Markers
# --------------------------------------------------------------------------- #

_M1_ROBUSTNESS_DECISION_RECORD_REL = (
    "project/stage126/stage126_m1_robustness_part0_decision_record.json"
)


def derive_m1_robustness_decision_markers(root: str) -> dict:
    """Derive the six Stage126 M1 robustness-decision markers (fail-closed).

    Reads only the tracked Part 0 decision record. When the record is absent
    (repository states before the Part 0 decision lock), returns an empty dict
    so pre-Part-0 Handoffs are unaffected. When the record is present it must be
    internally consistent, otherwise a HandoffError is raised.
    """
    path = os.path.join(root, _M1_ROBUSTNESS_DECISION_RECORD_REL)
    if not os.path.isfile(path):
        return {}
    try:
        record = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(
            f"unreadable robustness decision record: {exc}"
        ) from exc

    # Exact identity + flag contract (fail-closed).
    exact_fields = {
        "contract_id": "stage126_m1_robustness_execution_contract",
        "contract_version": "stage126_m1_robustness_execution_contract_v1",
        "decision_id": "stage126-m1-robustness-part0-decision-lock",
        "decision_locked": True,
        "execution_authorized": False,
        "m1_robustness_started": False,
        "m1_robustness_completed": False,
        "part0_authorizes_part1": False,
        "one_category_per_micro_part_pr": True,
        "each_part_requires_separate_human_authorization": True,
        "packaging_policy": "one_category_per_micro_part_pr",
    }
    for key, expected in exact_fields.items():
        if record.get(key) != expected:
            raise HandoffError(
                f"robustness decision record field {key}="
                f"{record.get(key)!r} != {expected!r}"
            )

    # Exact full execution order (not just the first member).
    expected_order = [
        "m1_target_proximity_six_feature_set",
        "main_rule_b_listing_robustness",
        "expanded_rule_a_company_scope_robustness",
        "expanded_rule_b_combined_robustness",
        "persistent_loss_robustness_target",
        "smote_training_fold_only_robustness",
    ]
    if list(record.get("execution_order") or []) != expected_order:
        raise HandoffError(
            "robustness decision record execution_order is not the exact "
            "six-member sequence"
        )

    # Recompute SHA-256 of the human decision text and require equality with the
    # pinned digest AND the record's own hash field.
    text = record.get("human_decision_text")
    expected_hash = (
        "79f98e4c6dc81e6362ad90b138997c0d0bc3c8bad5d471ea65615ffc49627a5b"
    )
    if not isinstance(text, str):
        raise HandoffError("robustness decision record human_decision_text missing")
    recomputed = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if recomputed != expected_hash:
        raise HandoffError(
            "robustness decision record human_decision_text SHA-256 mismatch"
        )
    if record.get("human_decision_text_sha256") != expected_hash:
        raise HandoffError(
            "robustness decision record human_decision_text_sha256 field mismatch"
        )

    markers = {
        "m1_robustness_decision_locked": True,
        "m1_robustness_execution_authorized": False,
        "m1_robustness_started": False,
        "m1_robustness_completed": False,
        "m1_robustness_next_category_id": expected_order[0],
        "m1_robustness_packaging_policy": "one_category_per_micro_part_pr",
    }
    # Layer completed-category state on top (Part 1 onward), fail-closed.
    markers.update(derive_m1_robustness_part1_markers(root, expected_order))
    markers.update(derive_validation_architecture_markers(root))
    return markers


_BOUNDARY_DECISION_REL = (
    "project/stage126/stage126_validation_architecture_boundary_decision.json"
)
_BOUNDARY_MANIFEST_REL = (
    "project/stage126/stage126_historical_boundary_manifest.json"
)
_CURRENT_STATE_REPORT_REL = (
    "project/stage126/stage126_current_state_validation_report.json"
)
_BOUNDARY_DECISION_SHA256 = (
    "8231bbf8704d3128cce6a7f2cc40a33af8e7fe7730b2c4575997330cafb21ac1"
)
_VALIDATION_ARCHITECTURE = "stage126_current_state_validator_v2_lean"
_VALIDATOR_ID = "stage126_current_state_validator"
# The validator version AS RECORDED by the frozen 2026-07-23 human decision
# text/architecture (project/stage126/
# stage126_validation_architecture_boundary_decision.json). That file is a
# historical, locked governance record and must stay byte-identical to what
# was actually decided that day, regardless of how many times the CURRENT
# validator implementation version (_VALIDATION_ARCHITECTURE above) is bumped
# afterward by ordinary maintenance. Never compare the two.
_HISTORICAL_DECISION_VALIDATOR_VERSION = "stage126_current_state_validator_v1"
# Stage126+ Q1/Q2 Lean Governance label surfaced in the Handoff's
# `validation_architecture` field (see
# project/docs/ai/STAGE126_Q1Q2_LEAN_GOVERNANCE.md). Distinct from
# `_VALIDATION_ARCHITECTURE` above, which pins the validator's own code
# contract version.
_LEAN_GOVERNANCE_ARCHITECTURE = "stage126_q1q2_lean_governance_v1"


_CURRENT_STATE_METADATA_REL = (
    "project/stage126/metadata_and_hashes_stage126_current_state_validator.json"
)


def derive_current_state_qc_markers(root: str) -> dict:
    """Separate the CURRENT-STATE validation QC from the last scientific QC.

    ``current_state_validation_*`` describes the independent Stage126
    current-state validator — the sole current-state validation surface.
    ``last_completed_micro_part_qc_*`` describes the newest completed
    SCIENTIFIC micro-part. The two roles must never be conflated.
    """
    meta_path = os.path.join(root, _CURRENT_STATE_METADATA_REL)
    report_path = os.path.join(root, _CURRENT_STATE_REPORT_REL)
    if not (os.path.isfile(meta_path) and os.path.isfile(report_path)):
        return {}
    try:
        meta = json.load(open(meta_path, encoding="utf-8"))
        report = json.load(open(report_path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"unreadable current-state artifacts: {exc}") from exc

    if meta.get("all_pass") is not True or meta.get("failed_count") != 0:
        raise HandoffError("current-state validation is not all_pass (fail-closed)")
    if report.get("current_state_validation_scope") != _VALIDATOR_ID:
        raise HandoffError("current-state report scope mismatch")

    markers = {
        "current_state_validation_scope": _VALIDATOR_ID,
        "current_state_validation_path": _CURRENT_STATE_REPORT_REL,
        "current_state_validation_metadata_path": _CURRENT_STATE_METADATA_REL,
        "current_state_validation_assertions": meta["assertion_count"],
        "current_state_validation_failed": meta["failed_count"],
        "current_state_validation_all_pass": True,
    }

    # The last completed SCIENTIFIC micro-part QC, reported separately and
    # derived from the newest DISCOVERED package (not from the report, so a
    # newly completed part is represented truthfully before the current-state
    # artifacts are rebuilt).
    discovered = discover_robustness_micro_parts(root)
    qc_rel = discovered[-1][3] if discovered else (
        report.get("last_completed_micro_part_qc_path") or ""
    )
    if qc_rel:
        qc_path = os.path.join(root, qc_rel)
        if not os.path.isfile(qc_path):
            raise HandoffError(f"micro-part QC path missing: {qc_rel}")
        try:
            qc = json.load(open(qc_path, encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HandoffError(f"unreadable micro-part QC: {exc}") from exc
        if qc.get("all_pass") is not True:
            raise HandoffError("last completed micro-part QC is not all_pass")
        expected_scope = discovered[-1][0] if discovered else report.get(
            "last_completed_micro_part_qc_scope"
        )
        if qc.get("stage") != expected_scope:
            raise HandoffError(
                "micro-part QC scope disagrees with the discovered package"
            )
        markers.update({
            "last_completed_micro_part_qc_scope": qc["stage"],
            "last_completed_micro_part_qc_path": qc_rel,
            "last_completed_micro_part_qc_assertions": qc["assertion_count"],
            "last_completed_micro_part_qc_failed": qc["failed_count"],
        })
    return markers


def derive_validation_architecture_markers(root: str) -> dict:
    """Derive the validation-architecture boundary markers (fail-closed).

    Emitted only when the boundary decision, the historical manifest and the
    current-state validation report are all present and mutually consistent.
    Stage125 Part 5 is recorded as historical/immutable and NOT a live gate.
    """
    paths = [
        os.path.join(root, rel) for rel in (
            _BOUNDARY_DECISION_REL, _BOUNDARY_MANIFEST_REL,
            _CURRENT_STATE_REPORT_REL,
        )
    ]
    present = [os.path.isfile(p) for p in paths]
    if not any(present):
        return {}
    if not all(present):
        raise HandoffError(
            "validation-architecture boundary artifacts are only partially "
            "present (fail-closed)"
        )
    try:
        decision = json.load(open(paths[0], encoding="utf-8"))
        manifest = json.load(open(paths[1], encoding="utf-8"))
        report = json.load(open(paths[2], encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"unreadable boundary artifacts: {exc}") from exc

    text = decision.get("human_decision_text")
    if not isinstance(text, str):
        raise HandoffError("boundary decision text missing")
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != _BOUNDARY_DECISION_SHA256:
        raise HandoffError("boundary decision text SHA-256 mismatch")
    if decision.get("human_decision_text_sha256") != _BOUNDARY_DECISION_SHA256:
        raise HandoffError("boundary decision hash field mismatch")
    if decision.get("decision_locked") is not True:
        raise HandoffError("boundary decision is not locked")
    for key, want in (
        ("merge", False), ("part3_execution", False),
        ("full_development_refit", False), ("final_test_access", False),
        ("final_test_evaluation", False), ("new_scientific_execution", False),
    ):
        if (decision.get("does_not_authorize") or {}).get(key) is not want:
            raise HandoffError(f"boundary decision must deny {key}")

    arch = decision.get("architecture") or {}
    if arch.get("stage125_part5_mode") != "historical_immutable":
        raise HandoffError("boundary decision does not freeze Stage125 Part 5")
    if arch.get("stage125_part5_is_live_successor_validator") is not False:
        raise HandoffError("boundary decision still treats Part 5 as live")
    # The decision is HISTORICAL provenance: it must still record exactly the
    # validator version that existed when it was authorized on 2026-07-23 --
    # never the CURRENT validator implementation version. Coupling the two
    # would force rewriting a locked historical record every time the live
    # validator evolves, which Stage126+ Q1/Q2 Lean Governance explicitly
    # rules out (section 3: "validator refactor that preserves scientific
    # gates" needs no new authorization, and section 5: earlier state must
    # not be forced to keep matching current state).
    if arch.get("stage126_current_state_validator_version") != \
            _HISTORICAL_DECISION_VALIDATOR_VERSION:
        raise HandoffError(
            "boundary decision no longer records its ORIGINAL historical "
            "validator version -- this historical record must never be "
            "rewritten to track the current validator implementation"
        )
    if manifest.get("stage125_part5_mode") != "historical_immutable":
        raise HandoffError("boundary manifest does not freeze Stage125 Part 5")
    # Stage126+ Q1/Q2 Lean Governance: SCIENTIFIC artifact regeneration for a
    # closed part remains forbidden; OPERATIONAL verification-artifact
    # bookkeeping (tests/QC/metadata) is explicitly permitted to evolve
    # without a new scientific-error exception or authorization. The old
    # blanket `regeneration_of_earlier_part_verification_artifacts_allowed`
    # gate conflated the two and is retired here.
    if manifest.get(
        "prior_part_scientific_artifact_regeneration_forbidden"
    ) is not True:
        raise HandoffError(
            "boundary manifest does not forbid scientific artifact regeneration"
        )
    if manifest.get(
        "prior_part_operational_verification_artifact_evolution_permitted"
    ) is not True:
        raise HandoffError(
            "boundary manifest does not permit operational verification "
            "artifact evolution"
        )
    if report.get("stage125_part5_live_gate_active") is not False:
        raise HandoffError("validation report still marks Part 5 as a live gate")
    if report.get("contract_version") != _VALIDATION_ARCHITECTURE:
        raise HandoffError("validation report version mismatch")
    if report.get(
        "prior_part_scientific_artifact_regeneration_forbidden"
    ) is not True:
        raise HandoffError(
            "validation report does not forbid scientific artifact regeneration"
        )
    if report.get(
        "prior_part_operational_verification_artifact_evolution_permitted"
    ) is not True:
        raise HandoffError(
            "validation report does not permit operational verification "
            "artifact evolution"
        )

    markers = {
        "validation_architecture": _LEAN_GOVERNANCE_ARCHITECTURE,
        "scientific_artifacts_hard_locked": True,
        "operational_surfaces_git_versioned": True,
        "single_live_current_state_authority": True,
        "legacy_validation_boundary_adapted": True,
        "stage125_part5_mode": "historical_immutable",
        "stage125_part5_live_gate_active": False,
        "stage125_part5_future_regeneration_allowed": False,
        "prior_part_scientific_artifact_regeneration_forbidden": True,
        "prior_part_operational_verification_artifact_evolution_permitted": True,
        "prior_part_reopening_requires_scientific_error": True,
        "prior_part_reopening_requires_explicit_human_authorization": True,
    }
    markers.update(derive_current_state_qc_markers(root))
    markers.update(derive_live_vs_historical_test_boundary_markers(root))
    return markers


_TEST_BOUNDARY_REL = (
    "project/stage126/stage126_live_vs_historical_test_boundary.json"
)
_HISTORICAL_MARKER = "live_successor_state"
_TERMINAL_HISTORICAL_MARKER = "stage126_terminal_successor_state"
_HISTORICAL_REFERENCE_COMMIT = "6412b45c4adc6584a5567c7c96e0932f68f31e8a"
_FROZEN_PART5_TEST_SHA256 = (
    "0b9413b2adbf9c44b0fb12b4f7ef2dad60be5cd4c401ccefac30d19f0905af71"
)


def derive_live_vs_historical_test_boundary_markers(root: str) -> dict:
    """Derive the live-versus-historical test-suite boundary markers.

    Fail-closed: emitted only when the boundary record is present, internally
    consistent, and the frozen Stage125 Part 5 test file is still byte-identical
    on disk. The historical successor tests are never a live gate.
    """
    path = os.path.join(root, _TEST_BOUNDARY_REL)
    if not os.path.isfile(path):
        return {}
    try:
        record = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"unreadable test-boundary record: {exc}") from exc

    exact = {
        "contract_id": "stage126_live_vs_historical_test_boundary",
        "contract_version": "stage126_live_vs_historical_test_boundary_v1",
        "stage125_part5_mode": "historical_immutable",
        "historical_marker": _HISTORICAL_MARKER,
        "historical_test_file_sha256": _FROZEN_PART5_TEST_SHA256,
        "historical_reference_commit": _HISTORICAL_REFERENCE_COMMIT,
        "historical_successor_tests_are_live_gate": False,
        "stage126_live_suite_marker_expression": (
            "not live_successor_state and not stage126_terminal_successor_state"
        ),
        "current_state_validator_remains_live_gate": True,
        "part3_scientific_artifacts_changed": False,
        "part4_authorized": False,
        "final_test_unlocked": False,
        "stage125_part5_reopened_or_repinned": False,
        "terminal_historical_marker": _TERMINAL_HISTORICAL_MARKER,
        "terminal_historical_marked_node_count": 5,
        "terminal_historical_successor_tests_are_live_gate": False,
        "whole_part1_or_part2_test_file_excluded": False,
    }
    for key, want in exact.items():
        if record.get(key) != want:
            raise HandoffError(
                f"test-boundary record field {key}={record.get(key)!r} != {want!r}"
            )
    frozen = os.path.join(root, record["historical_test_file"])
    if not os.path.isfile(frozen):
        raise HandoffError("frozen Part 5 test file missing")
    got = hashlib.sha256(open(frozen, "rb").read()).hexdigest()
    if got != _FROZEN_PART5_TEST_SHA256:
        raise HandoffError(
            f"frozen Part 5 test file changed: {got} != {_FROZEN_PART5_TEST_SHA256}"
        )
    return {
        "stage125_part5_historical_successor_tests": True,
        "stage125_part5_historical_successor_test_marker": _HISTORICAL_MARKER,
        "stage125_part5_historical_successor_test_reference_commit":
            _HISTORICAL_REFERENCE_COMMIT,
        "stage125_part5_historical_successor_tests_in_live_gate": False,
        "stage126_live_test_suite_marker_expression": (
            "not live_successor_state and not stage126_terminal_successor_state"
        ),
    }


_M1_ROBUSTNESS_PART1_AUTH_REL = (
    "project/stage126/stage126_m1_robustness_part1_human_authorization_record.json"
)
_M1_ROBUSTNESS_PART1_LOCK_REL = (
    "project/stage126/stage126_m1_robustness_part1_completion_lock.json"
)
_PART1_CATEGORY_ID = "m1_target_proximity_six_feature_set"


def derive_m1_robustness_part1_markers(root: str, expected_order: list) -> dict:
    """Derive Part 1 completion markers (fail-closed).

    Returns {} when Part 1 has not been executed. When the Part 1 authorization
    record and completion lock are present they must be internally consistent
    and mutually agreeing, otherwise a HandoffError is raised. A completed and
    consumed Part 1 authorization grants NO standing authorization for Part 2.
    """
    auth_path = os.path.join(root, _M1_ROBUSTNESS_PART1_AUTH_REL)
    lock_path = os.path.join(root, _M1_ROBUSTNESS_PART1_LOCK_REL)
    if not (os.path.isfile(auth_path) and os.path.isfile(lock_path)):
        if os.path.isfile(auth_path) != os.path.isfile(lock_path):
            raise HandoffError(
                "Part 1 authorization record and completion lock must both exist"
            )
        return {}
    try:
        auth = json.load(open(auth_path, encoding="utf-8"))
        lock = json.load(open(lock_path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"unreadable Part 1 artifacts: {exc}") from exc

    auth_exact = {
        "authorization_id": "stage126-m1-robustness-part1-human-authorization",
        "authorized_category_id": _PART1_CATEGORY_ID,
        "part1_execution_authorized": True,
        "part2_execution_authorized": False,
        "final_test_access_authorized": False,
    }
    for k, v in auth_exact.items():
        if auth.get(k) != v:
            raise HandoffError(
                f"Part 1 authorization field {k}={auth.get(k)!r} != {v!r}"
            )
    text = auth.get("human_authorization_text")
    expected_hash = (
        "7364a67ce5761c69f6705ae0ee4b0563fc092a576e960df471ebb4581ae1b5ea"
    )
    if not isinstance(text, str):
        raise HandoffError("Part 1 authorization text missing")
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != expected_hash:
        raise HandoffError("Part 1 authorization text SHA-256 mismatch")
    if auth.get("human_authorization_text_sha256") != expected_hash:
        raise HandoffError("Part 1 authorization hash field mismatch")

    lock_exact = {
        "category_id": _PART1_CATEGORY_ID,
        "part1_human_authorized": True,
        "part1_execution_completed": True,
        "authorization_consumed": True,
        "development_only": True,
        "no_retuning": True,
        "m1_robustness_started": True,
        "m1_robustness_completed": False,
        "part2_execution_authorized": False,
        "full_development_refit_performed": False,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_evaluation_performed": False,
        "smote_executed": False,
        "smotenc_executed": False,
        "shap_executed": False,
    }
    for k, v in lock_exact.items():
        if lock.get(k) != v:
            raise HandoffError(
                f"Part 1 completion lock field {k}={lock.get(k)!r} != {v!r}"
            )
    completed = lock.get("completed_category_ids") or []
    if list(completed) != [_PART1_CATEGORY_ID]:
        raise HandoffError("Part 1 completed_category_ids unexpected")
    # The next category must be the next registered category after Part 1.
    if lock.get("next_category_id") != expected_order[1]:
        raise HandoffError(
            f"Part 1 next_category_id {lock.get('next_category_id')!r} != "
            f"{expected_order[1]!r}"
        )
    markers = {
        "m1_robustness_started": True,
        "m1_robustness_completed": False,
        "m1_robustness_part1_human_authorized": True,
        "m1_robustness_part1_completed": True,
        "m1_robustness_completed_category_ids": [_PART1_CATEGORY_ID],
        "m1_robustness_next_category_id": expected_order[1],
        "m1_robustness_part2_authorized": False,
        # A consumed Part 1 authorization is NOT a standing authorization.
        "m1_robustness_execution_authorized": False,
    }
    markers.update(derive_part5_successor_compatibility_markers(root))
    # Part 2 layers on top of (never replaces) the retained Part 1 state.
    markers.update(derive_m1_robustness_part2_markers(root, expected_order))
    return markers


_M1_ROBUSTNESS_PART2_AUTH_REL = (
    "project/stage126/stage126_m1_robustness_part2_human_authorization_record.json"
)
_M1_ROBUSTNESS_PART2_LOCK_REL = (
    "project/stage126/stage126_m1_robustness_part2_completion_lock.json"
)
_PART2_CATEGORY_ID = "main_rule_b_listing_robustness"
_PART2_MICRO_PART_ID = "stage126-m1-robustness-part2-listing-rule-b"
_PART2_AUTH_TEXT_SHA256 = (
    "27935d31a6efcc6116f0d4007424bad5c7b8599faabcb8d39176c569bf172bcb"
)


def derive_m1_robustness_part2_markers(root: str, expected_order: list) -> dict:
    """Derive Part 2 completion markers (fail-closed).

    Returns {} when Part 2 has not been executed. When the Part 2 authorization
    record and completion lock are present they must be internally consistent
    and mutually agreeing, otherwise a HandoffError is raised. A completed and
    consumed Part 2 authorization grants NO standing authorization for Part 3.
    """
    auth_path = os.path.join(root, _M1_ROBUSTNESS_PART2_AUTH_REL)
    lock_path = os.path.join(root, _M1_ROBUSTNESS_PART2_LOCK_REL)
    if not (os.path.isfile(auth_path) and os.path.isfile(lock_path)):
        if os.path.isfile(auth_path) != os.path.isfile(lock_path):
            raise HandoffError(
                "Part 2 authorization record and completion lock must both exist"
            )
        return {}
    try:
        auth = json.load(open(auth_path, encoding="utf-8"))
        lock = json.load(open(lock_path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"unreadable Part 2 artifacts: {exc}") from exc

    auth_exact = {
        "authorization_id": "stage126-m1-robustness-part2-human-authorization",
        "authorized_category_id": _PART2_CATEGORY_ID,
        "part2_execution_authorized": True,
        "create_open_unmerged_pr_authorized": True,
        "merge_authorized": False,
        "part3_execution_authorized": False,
        "full_development_refit_authorized": False,
        "final_test_access_authorized": False,
        "final_test_evaluation_authorized": False,
        "smote_authorized": False,
        "smotenc_authorized": False,
        "shap_authorized": False,
        "m2_authorized": False,
        "m3_authorized": False,
        "m4_authorized": False,
    }
    for k, v in auth_exact.items():
        if auth.get(k) != v:
            raise HandoffError(
                f"Part 2 authorization field {k}={auth.get(k)!r} != {v!r}"
            )
    text = auth.get("human_authorization_text")
    if not isinstance(text, str):
        raise HandoffError("Part 2 authorization text missing")
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != _PART2_AUTH_TEXT_SHA256:
        raise HandoffError("Part 2 authorization text SHA-256 mismatch")
    if auth.get("human_authorization_text_sha256") != _PART2_AUTH_TEXT_SHA256:
        raise HandoffError("Part 2 authorization hash field mismatch")

    lock_exact = {
        "category_id": _PART2_CATEGORY_ID,
        "micro_part_id": _PART2_MICRO_PART_ID,
        "part2_human_authorized": True,
        "part2_execution_completed": True,
        "authorization_consumed": True,
        "development_only": True,
        "only_sample_changed": True,
        "no_retuning": True,
        "sample": _PART2_CATEGORY_ID,
        "target": "FD_target_main_t_plus_1",
        "feature_set": "M1_PRIMARY_FEATURE_ORDER",
        "model_fit_calls": 22,
        "prediction_calls": 22,
        "m1_robustness_started": True,
        "m1_robustness_completed": False,
        "part3_execution_authorized": False,
        "m1_robustness_execution_authorized": False,
        "full_development_refit_performed": False,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_evaluation_performed": False,
        "smote_executed": False,
        "smotenc_executed": False,
        "shap_executed": False,
        "replaces_primary_results": False,
        "selects_paper_winner": False,
        "part1_scientific_artifacts_byte_identical": True,
    }
    for k, v in lock_exact.items():
        if lock.get(k) != v:
            raise HandoffError(
                f"Part 2 completion lock field {k}={lock.get(k)!r} != {v!r}"
            )
    completed = list(lock.get("completed_category_ids") or [])
    if completed != [_PART1_CATEGORY_ID, _PART2_CATEGORY_ID]:
        raise HandoffError(
            f"Part 2 completed_category_ids {completed!r} is not the exact "
            f"two-category sequence"
        )
    if lock.get("next_category_id") != expected_order[2]:
        raise HandoffError(
            f"Part 2 next_category_id {lock.get('next_category_id')!r} != "
            f"{expected_order[2]!r}"
        )
    markers = {
        "m1_robustness_started": True,
        "m1_robustness_completed": False,
        "m1_robustness_part1_completed": True,
        "m1_robustness_part2_human_authorized": True,
        "m1_robustness_part2_completed": True,
        "m1_robustness_completed_category_ids": completed,
        "m1_robustness_next_category_id": expected_order[2],
        "m1_robustness_part3_authorized": False,
        # A consumed Part 2 authorization is NOT a standing authorization.
        "m1_robustness_execution_authorized": False,
    }
    markers.update(derive_part2_sample_robustness_markers(root))
    markers.update(derive_m1_robustness_part3_markers(root, expected_order))
    return markers


_M1_ROBUSTNESS_PART3_AUTH_REL = (
    "project/stage126/stage126_m1_robustness_part3_human_authorization_record.json"
)
_M1_ROBUSTNESS_PART3_LOCK_REL = (
    "project/stage126/stage126_m1_robustness_part3_completion_lock.json"
)
_PART3_CATEGORY_ID = "expanded_rule_a_company_scope_robustness"
_PART3_MICRO_PART_ID = "stage126-m1-robustness-part3-expanded-rule-a"
_PART3_AUTH_TEXT_SHA256 = (
    "f1230aa0dac18670695d41d99709cfd4ba5619e96e6f93c2e0678387ab28dab1"
)


def derive_m1_robustness_part3_markers(root: str, expected_order: list) -> dict:
    """Derive Part 3 completion markers (fail-closed).

    Returns {} when Part 3 has not been executed. A completed and consumed
    Part 3 authorization grants NO standing authorization for Part 4.
    """
    auth_path = os.path.join(root, _M1_ROBUSTNESS_PART3_AUTH_REL)
    lock_path = os.path.join(root, _M1_ROBUSTNESS_PART3_LOCK_REL)
    if not (os.path.isfile(auth_path) and os.path.isfile(lock_path)):
        if os.path.isfile(auth_path) != os.path.isfile(lock_path):
            raise HandoffError(
                "Part 3 authorization record and completion lock must both exist"
            )
        return {}
    try:
        auth = json.load(open(auth_path, encoding="utf-8"))
        lock = json.load(open(lock_path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"unreadable Part 3 artifacts: {exc}") from exc

    auth_exact = {
        "authorization_id": "stage126-m1-robustness-part3-human-authorization",
        "authorized_category_id": _PART3_CATEGORY_ID,
        "part3_execution_authorized": True,
        "create_open_unmerged_pr_authorized": True,
        "merge_authorized": False,
        "part4_execution_authorized": False,
        "full_development_refit_authorized": False,
        "final_test_access_authorized": False,
        "final_test_evaluation_authorized": False,
        "calibration_authorized": False,
        "bootstrap_authorized": False,
        "holm_authorized": False,
        "winner_selection_authorized": False,
        "smote_authorized": False,
        "shap_authorized": False,
    }
    for k, v in auth_exact.items():
        if auth.get(k) != v:
            raise HandoffError(
                f"Part 3 authorization field {k}={auth.get(k)!r} != {v!r}"
            )
    text = auth.get("human_authorization_text")
    if not isinstance(text, str):
        raise HandoffError("Part 3 authorization text missing")
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != _PART3_AUTH_TEXT_SHA256:
        raise HandoffError("Part 3 authorization text SHA-256 mismatch")
    if auth.get("human_authorization_text_sha256") != _PART3_AUTH_TEXT_SHA256:
        raise HandoffError("Part 3 authorization hash field mismatch")

    lock_exact = {
        "category_id": _PART3_CATEGORY_ID,
        "micro_part_id": _PART3_MICRO_PART_ID,
        "part3_human_authorized": True,
        "part3_execution_completed": True,
        "authorization_consumed": True,
        "development_only": True,
        "replaces_primary_results": False,
        "selects_paper_winner": False,
        "part4_execution_authorized": False,
        "m1_robustness_execution_authorized": False,
        "m1_robustness_completed": False,
        "full_development_refit_performed": False,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_predictor_values_inspected": False,
        "final_test_target_values_inspected": False,
        "final_test_evaluation_performed": False,
        "smote_executed": False,
        "smotenc_executed": False,
        "shap_executed": False,
        "calibration_executed": False,
        "bootstrap_executed": False,
        "holm_executed": False,
        "winner_selected": False,
    }
    for k, v in lock_exact.items():
        if lock.get(k) != v:
            raise HandoffError(
                f"Part 3 completion lock field {k}={lock.get(k)!r} != {v!r}"
            )
    completed = list(lock.get("completed_category_ids") or [])
    if completed != list(expected_order[:3]):
        raise HandoffError(
            f"Part 3 completed_category_ids {completed!r} is not the exact "
            f"three-category prefix"
        )
    if lock.get("next_category_id") != expected_order[3]:
        raise HandoffError(
            f"Part 3 next_category_id {lock.get('next_category_id')!r} != "
            f"{expected_order[3]!r}"
        )
    markers = {
        "m1_robustness_started": True,
        "m1_robustness_completed": False,
        "m1_robustness_part1_completed": True,
        "m1_robustness_part2_completed": True,
        "m1_robustness_part3_human_authorized": True,
        "m1_robustness_part3_completed": True,
        "m1_robustness_completed_category_ids": completed,
        "m1_robustness_next_category_id": expected_order[3],
        "m1_robustness_part3_authorized": False,
        "m1_robustness_part4_authorized": False,
        # A consumed Part 3 authorization is NOT a standing authorization.
        "m1_robustness_execution_authorized": False,
    }
    markers.update(derive_m1_robustness_part4_markers(root, expected_order))
    return markers


_M1_ROBUSTNESS_PART4_AUTH_REL = (
    "project/stage126/stage126_m1_robustness_part4_human_authorization_record.json"
)
_M1_ROBUSTNESS_PART4_LOCK_REL = (
    "project/stage126/stage126_m1_robustness_part4_completion_lock.json"
)
_PART4_CATEGORY_ID = "expanded_rule_b_combined_robustness"
_PART4_MICRO_PART_ID = "stage126-m1-robustness-part4-expanded-rule-b"
_PART4_AUTH_TEXT_SHA256 = (
    "e40852d9e2a78cc6d9b3079379abd0fed8f4921b65bec00ecf58d5aad78fd1b4"
)


def derive_m1_robustness_part4_markers(root: str, expected_order: list) -> dict:
    """Derive Part 4 completion markers (fail-closed).

    Returns {} when Part 4 has not been executed. A completed and consumed
    Part 4 authorization grants NO standing authorization for Part 5.
    """
    auth_path = os.path.join(root, _M1_ROBUSTNESS_PART4_AUTH_REL)
    lock_path = os.path.join(root, _M1_ROBUSTNESS_PART4_LOCK_REL)
    if not (os.path.isfile(auth_path) and os.path.isfile(lock_path)):
        if os.path.isfile(auth_path) != os.path.isfile(lock_path):
            raise HandoffError(
                "Part 4 authorization record and completion lock must both exist"
            )
        return {}
    try:
        auth = json.load(open(auth_path, encoding="utf-8"))
        lock = json.load(open(lock_path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"unreadable Part 4 artifacts: {exc}") from exc

    auth_exact = {
        "authorization_id": "stage126-m1-robustness-part4-human-authorization",
        "authorized_category_id": _PART4_CATEGORY_ID,
        "part4_execution_authorized": True,
        "create_open_unmerged_pr_authorized": True,
        "merge_authorized": False,
        "part5_execution_authorized": False,
        "full_development_refit_authorized": False,
        "final_test_access_authorized": False,
        "final_test_evaluation_authorized": False,
        "calibration_authorized": False,
        "bootstrap_authorized": False,
        "holm_authorized": False,
        "winner_selection_authorized": False,
        "smote_authorized": False,
        "shap_authorized": False,
    }
    for k, v in auth_exact.items():
        if auth.get(k) != v:
            raise HandoffError(
                f"Part 4 authorization field {k}={auth.get(k)!r} != {v!r}"
            )
    text = auth.get("human_authorization_text")
    if not isinstance(text, str):
        raise HandoffError("Part 4 authorization text missing")
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != _PART4_AUTH_TEXT_SHA256:
        raise HandoffError("Part 4 authorization text SHA-256 mismatch")
    if auth.get("human_authorization_text_sha256") != _PART4_AUTH_TEXT_SHA256:
        raise HandoffError("Part 4 authorization hash field mismatch")

    lock_exact = {
        "category_id": _PART4_CATEGORY_ID,
        "micro_part_id": _PART4_MICRO_PART_ID,
        "part4_human_authorized": True,
        "part4_execution_completed": True,
        "authorization_consumed": True,
        "development_only": True,
        "replaces_primary_results": False,
        "selects_paper_winner": False,
        "part5_execution_authorized": False,
        "m1_robustness_execution_authorized": False,
        "m1_robustness_completed": False,
        "full_development_refit_performed": False,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_predictor_values_inspected": False,
        "final_test_target_values_inspected": False,
        "final_test_evaluation_performed": False,
        "smote_executed": False,
        "smotenc_executed": False,
        "shap_executed": False,
        "calibration_executed": False,
        "bootstrap_executed": False,
        "holm_executed": False,
        "winner_selected": False,
    }
    for k, v in lock_exact.items():
        if lock.get(k) != v:
            raise HandoffError(
                f"Part 4 completion lock field {k}={lock.get(k)!r} != {v!r}"
            )
    completed = list(lock.get("completed_category_ids") or [])
    if completed != list(expected_order[:4]):
        raise HandoffError(
            f"Part 4 completed_category_ids {completed!r} is not the exact "
            f"four-category prefix"
        )
    if lock.get("next_category_id") != expected_order[4]:
        raise HandoffError(
            f"Part 4 next_category_id {lock.get('next_category_id')!r} != "
            f"{expected_order[4]!r}"
        )
    part4_markers = {
        "m1_robustness_started": True,
        "m1_robustness_completed": False,
        "m1_robustness_part1_completed": True,
        "m1_robustness_part2_completed": True,
        "m1_robustness_part3_completed": True,
        "m1_robustness_part4_human_authorized": True,
        "m1_robustness_part4_completed": True,
        "m1_robustness_completed_category_ids": completed,
        "m1_robustness_next_category_id": expected_order[4],
        "m1_robustness_part4_authorized": False,
        "m1_robustness_part5_authorized": False,
        # A consumed Part 4 authorization is NOT a standing authorization.
        "m1_robustness_execution_authorized": False,
    }
    # Part 5 (if executed) advances the completion prefix on top of Part 4.
    part4_markers.update(
        derive_m1_robustness_part5_markers(root, expected_order)
    )
    return part4_markers


_NEXT_RESEARCH_ACTION_ID_AFTER_M1_ROBUSTNESS = "stage126-m1-robustness-closure"


_M1_ROBUSTNESS_PART5_AUTH_REL = (
    "project/stage126/stage126_m1_robustness_part5_human_authorization_record.json"
)
_M1_ROBUSTNESS_PART5_LOCK_REL = (
    "project/stage126/stage126_m1_robustness_part5_completion_lock.json"
)
_PART5_CATEGORY_ID = "persistent_loss_robustness_target"
_PART5_MICRO_PART_ID = "stage126-m1-robustness-part5-persistent-loss-target"
_PART5_AUTH_TEXT_SHA256 = (
    "e00b43d812b3da2104bfedb30a1dd63276a7f28347b93ff7f4bbcad60fd23678"
)


def derive_m1_robustness_part5_markers(root: str, expected_order: list) -> dict:
    """Derive Part 5 completion markers (fail-closed).

    Returns {} when Part 5 has not been executed. A completed and consumed
    Part 5 authorization grants NO standing authorization for Part 6.
    """
    auth_path = os.path.join(root, _M1_ROBUSTNESS_PART5_AUTH_REL)
    lock_path = os.path.join(root, _M1_ROBUSTNESS_PART5_LOCK_REL)
    if not (os.path.isfile(auth_path) and os.path.isfile(lock_path)):
        if os.path.isfile(auth_path) != os.path.isfile(lock_path):
            raise HandoffError(
                "Part 5 authorization record and completion lock must both exist"
            )
        return {}
    try:
        auth = json.load(open(auth_path, encoding="utf-8"))
        lock = json.load(open(lock_path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"unreadable Part 5 artifacts: {exc}") from exc

    auth_exact = {
        "authorization_id": "stage126-m1-robustness-part5-human-authorization",
        "authorized_category_id": _PART5_CATEGORY_ID,
        "part5_execution_authorized": True,
        "create_open_unmerged_pr_authorized": True,
        "merge_authorized": False,
        "part6_execution_authorized": False,
        "retuning_authorized": False,
        "full_development_refit_authorized": False,
        "final_test_access_authorized": False,
        "final_test_evaluation_authorized": False,
        "calibration_authorized": False,
        "bootstrap_authorized": False,
        "holm_authorized": False,
        "winner_selection_authorized": False,
        "smote_authorized": False,
        "shap_authorized": False,
    }
    for k, v in auth_exact.items():
        if auth.get(k) != v:
            raise HandoffError(
                f"Part 5 authorization field {k}={auth.get(k)!r} != {v!r}"
            )
    text = auth.get("human_authorization_text")
    if not isinstance(text, str):
        raise HandoffError("Part 5 authorization text missing")
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != _PART5_AUTH_TEXT_SHA256:
        raise HandoffError("Part 5 authorization text SHA-256 mismatch")
    if auth.get("human_authorization_text_sha256") != _PART5_AUTH_TEXT_SHA256:
        raise HandoffError("Part 5 authorization hash field mismatch")

    lock_exact = {
        "category_id": _PART5_CATEGORY_ID,
        "micro_part_id": _PART5_MICRO_PART_ID,
        "part5_human_authorized": True,
        "part5_execution_completed": True,
        "authorization_consumed": True,
        "development_only": True,
        "only_target_changed": True,
        "sample_changed": False,
        "replaces_primary_results": False,
        "replaces_primary_target": False,
        "selects_paper_winner": False,
        "part6_execution_authorized": False,
        "m1_robustness_execution_authorized": False,
        "m1_robustness_completed": False,
        "full_development_refit_performed": False,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_predictor_values_inspected": False,
        "final_test_target_values_inspected": False,
        "final_test_evaluation_performed": False,
        "smote_executed": False,
        "smotenc_executed": False,
        "shap_executed": False,
        "calibration_executed": False,
        "bootstrap_executed": False,
        "holm_executed": False,
        "winner_selected": False,
    }
    for k, v in lock_exact.items():
        if lock.get(k) != v:
            raise HandoffError(
                f"Part 5 completion lock field {k}={lock.get(k)!r} != {v!r}"
            )
    completed = list(lock.get("completed_category_ids") or [])
    if completed != list(expected_order[:5]):
        raise HandoffError(
            f"Part 5 completed_category_ids {completed!r} is not the exact "
            f"five-category prefix"
        )
    if lock.get("next_category_id") != expected_order[5]:
        raise HandoffError(
            f"Part 5 next_category_id {lock.get('next_category_id')!r} != "
            f"{expected_order[5]!r}"
        )
    part5_markers = {
        "m1_robustness_started": True,
        "m1_robustness_completed": False,
        "m1_robustness_part1_completed": True,
        "m1_robustness_part2_completed": True,
        "m1_robustness_part3_completed": True,
        "m1_robustness_part4_completed": True,
        "m1_robustness_part5_human_authorized": True,
        "m1_robustness_part5_completed": True,
        "m1_robustness_completed_category_ids": completed,
        "m1_robustness_next_category_id": expected_order[5],
        "m1_robustness_part5_authorized": False,
        "m1_robustness_part6_authorized": False,
        # A consumed Part 5 authorization is NOT a standing authorization.
        "m1_robustness_execution_authorized": False,
    }
    # Part 6 (if executed) closes the six-category robustness set.
    part5_markers.update(
        derive_m1_robustness_part6_markers(root, expected_order)
    )
    return part5_markers


_M1_ROBUSTNESS_PART6_AUTH_REL = (
    "project/stage126/stage126_m1_robustness_part6_human_authorization_record.json"
)
_M1_ROBUSTNESS_PART6_LOCK_REL = (
    "project/stage126/stage126_m1_robustness_part6_completion_lock.json"
)
_PART6_CATEGORY_ID = "smote_training_fold_only_robustness"
_PART6_MICRO_PART_ID = "stage126-m1-robustness-part6-smote-training-fold-only"
_PART6_AUTH_TEXT_SHA256 = (
    "4a3bb0d722d288f754b780208b5805f264b4caac75a902f434135f56430ed269"
)


def derive_m1_robustness_part6_markers(root: str, expected_order: list) -> dict:
    """Derive Part 6 completion markers (fail-closed).

    Returns {} when Part 6 has not been executed. Part 6 is the sixth and
    FINAL registered robustness category: unlike Parts 1-5, its completion
    lock legitimately shows `smotenc_executed=True` (SMOTENC applied strictly
    inside each training fold is the one authorized change, per
    STAGE126_Q1Q2_LEAN_GOVERNANCE.md section 10), and there is no seventh
    category to authorize. A completed and consumed Part 6 authorization
    grants NO standing authorization for full-development refit, final test
    or M2/M3/M4.
    """
    auth_path = os.path.join(root, _M1_ROBUSTNESS_PART6_AUTH_REL)
    lock_path = os.path.join(root, _M1_ROBUSTNESS_PART6_LOCK_REL)
    if not (os.path.isfile(auth_path) and os.path.isfile(lock_path)):
        if os.path.isfile(auth_path) != os.path.isfile(lock_path):
            raise HandoffError(
                "Part 6 authorization record and completion lock must both exist"
            )
        return {}
    try:
        auth = json.load(open(auth_path, encoding="utf-8"))
        lock = json.load(open(lock_path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"unreadable Part 6 artifacts: {exc}") from exc

    auth_exact = {
        "authorization_id": "stage126-m1-robustness-part6-human-authorization",
        "authorized_category_id": _PART6_CATEGORY_ID,
        "part6_execution_authorized": True,
        "create_open_unmerged_pr_authorized": True,
        "development_fold_execution_authorized": True,
        "merge_authorized": False,
        "retuning_authorized": False,
        "full_development_refit_authorized": False,
        "final_test_access_authorized": False,
        "final_test_evaluation_authorized": False,
        "final_test_predictor_access_authorized": False,
        "final_test_target_access_authorized": False,
        "calibration_authorized": False,
        "bootstrap_authorized": False,
        "holm_authorized": False,
        "winner_selection_authorized": False,
        "shap_authorized": False,
        "p_values_authorized": False,
        "threshold_optimization_authorized": False,
        "m2_authorized": False,
        "m3_authorized": False,
        "m4_authorized": False,
    }
    for k, v in auth_exact.items():
        if auth.get(k) != v:
            raise HandoffError(
                f"Part 6 authorization field {k}={auth.get(k)!r} != {v!r}"
            )
    text = auth.get("human_authorization_text")
    if not isinstance(text, str):
        raise HandoffError("Part 6 authorization text missing")
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != _PART6_AUTH_TEXT_SHA256:
        raise HandoffError("Part 6 authorization text SHA-256 mismatch")
    if auth.get("human_authorization_text_sha256") != _PART6_AUTH_TEXT_SHA256:
        raise HandoffError("Part 6 authorization hash field mismatch")
    if auth.get("human_authorization_text_utf8_bytes") != 696:
        raise HandoffError("Part 6 authorization text byte-length mismatch")

    lock_exact = {
        "category_id": _PART6_CATEGORY_ID,
        "micro_part_id": _PART6_MICRO_PART_ID,
        "part6_human_authorized": True,
        "part6_execution_completed": True,
        "authorization_consumed": True,
        "development_only": True,
        "only_imbalance_strategy_changed": True,
        "sample_changed": False,
        "target_changed": False,
        "replaces_primary_results": False,
        "selects_paper_winner": False,
        "part7_execution_authorized": False,
        "m1_robustness_execution_authorized": False,
        "m1_robustness_completed": True,
        "full_development_refit_performed": False,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_predictor_values_inspected": False,
        "final_test_target_values_inspected": False,
        "final_test_evaluation_performed": False,
        "smote_executed": False,
        "smotenc_executed": True,
        "shap_executed": False,
        "calibration_executed": False,
        "bootstrap_executed": False,
        "holm_executed": False,
        "winner_selected": False,
    }
    for k, v in lock_exact.items():
        if lock.get(k) != v:
            raise HandoffError(
                f"Part 6 completion lock field {k}={lock.get(k)!r} != {v!r}"
            )
    completed = list(lock.get("completed_category_ids") or [])
    if completed != list(expected_order):
        raise HandoffError(
            f"Part 6 completed_category_ids {completed!r} is not the exact "
            f"six-category full set"
        )
    if lock.get("next_category_id") not in (None, ""):
        raise HandoffError(
            f"Part 6 next_category_id {lock.get('next_category_id')!r} is not "
            "empty -- Part 6 is the final registered category"
        )
    return {
        "m1_robustness_started": True,
        "m1_robustness_completed": True,
        "m1_robustness_part1_completed": True,
        "m1_robustness_part2_completed": True,
        "m1_robustness_part3_completed": True,
        "m1_robustness_part4_completed": True,
        "m1_robustness_part5_completed": True,
        "m1_robustness_part6_human_authorized": True,
        "m1_robustness_part6_completed": True,
        "m1_robustness_completed_category_ids": completed,
        "m1_robustness_next_category_id": "",
        "m1_robustness_part6_authorized": False,
        # A consumed Part 6 authorization is NOT a standing authorization for
        # full-development refit, final test, or M2/M3/M4.
        "m1_robustness_execution_authorized": False,
        "full_development_refit_performed": False,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_predictor_values_inspected": False,
        "final_test_target_values_inspected": False,
        "final_test_evaluation_performed": False,
        "m2_data_collected": False,
        "m3_data_collected": False,
        "m4_data_collected": False,
        # M1 robustness closure is a truthful, one-time state transition, not
        # a per-part advance (see STAGE126_Q1Q2_LEAN_GOVERNANCE.md section
        # 10-11): it does not itself authorize retained-design freeze.
        "next_research_action_id": _NEXT_RESEARCH_ACTION_ID_AFTER_M1_ROBUSTNESS,
        **derive_m1_robustness_closure_markers(root),
    }


_CLOSURE_LOCK_REL = (
    "project/stage126/stage126_m1_robustness_closure_completion_lock.json"
)
_NEXT_RESEARCH_ACTION_ID_AFTER_ROBUSTNESS_CLOSURE = (
    "stage126-m1-retained-design-freeze"
)


#: Every ``<prefix>`` whose authorization the repository publishes as the
#: HISTORICAL/STANDING pair. The naming contract, established by the step B
#: retrieval markers and stated in their comment, is:
#:
#:   ``<prefix>_was_authorized``          historical fact — it happened
#:   ``<prefix>_authorized_now``          standing permission — right now
#:   ``<prefix>_authorized``              THE SAME standing meaning (generic)
#:   ``<prefix>_authorization_consumed``  the one-time grant is spent
#:
#: so a CONSUMED authorization must never publish the generic (or ``_now``)
#: field as True. Publishing history in a standing field is precisely how a
#: spent one-time authorization comes to read as live permission.
_ONE_TIME_AUTHORIZATION_PREFIXES = (
    "stage128_m3_lag_wdi_retrieval",
    "stage128_m3_lag_wdi_post_retrieval_audit",
    "stage128_m3_lag_wdi_data_gate",
    "stage128_m3_lag_wdi_calendar_mapping_lock",
    "stage128_m3_lag_wdi_modeling",
)


def _assert_no_consumed_authorization_is_standing(state: dict) -> dict:
    """Fail closed if a consumed authorization is published as a standing one.

    This is a structural invariant, not a per-step opinion: it holds for every
    one-time Track B authorization at every point in the sequence, so a future
    step cannot reintroduce the drift by copying whichever neighbouring step
    happened to be wrong. It never inspects a scientific result — only the
    authorization bookkeeping around it.
    """
    for prefix in _ONE_TIME_AUTHORIZATION_PREFIXES:
        consumed = state.get(f"{prefix}_authorization_consumed")
        if consumed is not True:
            continue
        for suffix in ("authorized", "authorized_now"):
            if state.get(f"{prefix}_{suffix}") is True:
                raise HandoffError(
                    f"{prefix}_authorization_consumed is True, so "
                    f"{prefix}_{suffix} must be False: a consumed one-time "
                    "authorization is history and may never be published as "
                    f"a standing permission (the historical fact belongs in "
                    f"{prefix}_was_authorized)")
        if state.get(f"{prefix}_authorization_reusable") is True:
            raise HandoffError(
                f"{prefix}_authorization_consumed is True, so "
                f"{prefix}_authorization_reusable must be False")
        # History must actually be recorded somewhere, or "consumed" would be
        # describing an authorization the state never admits existed.
        if state.get(f"{prefix}_was_authorized") is not True:
            raise HandoffError(
                f"{prefix}_authorization_consumed is True, so "
                f"{prefix}_was_authorized must be True")
    return state


def _assert_stage128_action_sequence_and_track_a_invariants(
        state: dict) -> dict:
    """Fail closed on the invariants that Bug 1/Bug 3 fixes must hold.

    * Every step published in ``stage128_m3_lag_wdi_action_sequence`` keeps
      ``authorized`` / ``authorized_now`` False, whatever its
      ``was_authorized`` / ``status`` say — a one-time execution is history,
      never a standing permission. This must hold for the WHOLE sequence,
      not only for step E, so a future step F cannot reintroduce the drift.
    * Once ``stage128_m3_lag_wdi_modeling_started`` is True, the sequence
      must actually contain a COMPLETE / was_authorized step E entry — this
      is the direct regression guard for the stale-cap bug where the
      calendar-mapping-lock deriver's D-capped list silently won the merge.
    * Once the Track A waiting-period termination package is recorded, the
      historical ``stage128_m3i2_inquiry_waiting_period_status`` field may
      never be the only status a consumer sees: the historical-superseded
      flag and the current termination status must both be published.
    """
    sequence = state.get("stage128_m3_lag_wdi_action_sequence") or []
    for step_item in sequence:
        step = step_item.get("step")
        if step_item.get("authorized_now") is not False:
            raise HandoffError(
                f"action-sequence step {step!r} authorized_now must stay "
                "False: execution history is never a standing authorization")
        if step_item.get("authorized") is not False:
            raise HandoffError(
                f"action-sequence step {step!r} authorized must stay False: "
                "execution history is never a standing authorization")

    if state.get("stage128_m3_lag_wdi_modeling_started") is True:
        e_entry = next(
            (item for item in sequence if item.get("step") == "E"), None)
        if e_entry is None:
            raise HandoffError(
                "stage128_m3_lag_wdi_modeling_started is True, so the "
                "action sequence must contain a step E entry")
        if e_entry.get("status") != "COMPLETE":
            raise HandoffError(
                "stage128_m3_lag_wdi_modeling_started is True, so step E's "
                "action-sequence status must be COMPLETE, not "
                f"{e_entry.get('status')!r}")
        if e_entry.get("was_authorized") is not True:
            raise HandoffError(
                "stage128_m3_lag_wdi_modeling_started is True, so step E's "
                "action-sequence was_authorized must be True")

    if state.get("stage128_track_a_waiting_termination_recorded") is True:
        if not state.get(
                "stage128_m3i2_inquiry_waiting_period_status_is_historical_"
                "superseded_by_termination"):
            raise HandoffError(
                "Track A termination is recorded, so "
                "stage128_m3i2_inquiry_waiting_period_status must be marked "
                "historical/superseded via the companion flag")
        if state.get("stage128_track_a_waiting_period_status") != (
                "VOLUNTARILY_TERMINATED_BY_EXPLICIT_HUMAN_DECISION"):
            raise HandoffError(
                "Track A termination is recorded, so "
                "stage128_track_a_waiting_period_status must be "
                "VOLUNTARILY_TERMINATED_BY_EXPLICIT_HUMAN_DECISION")
    return state


def derive_m1_robustness_closure_markers(root: str) -> dict:
    """Recognize the (synthesis-only) M1 robustness closure, if completed.

    Narrow, fail-closed recognition mirroring the Part 6 completion pattern:
    if the closure completion lock is present and internally consistent, the
    Handoff's ``next_research_action_id`` advances to
    ``stage126-m1-retained-design-freeze`` (itself requiring a SEPARATE future
    human authorization — this function never sets that authorization True).
    Returns an empty dict when the closure has not yet been built, so
    pre-closure Handoffs are unaffected.
    """
    path = os.path.join(root, _CLOSURE_LOCK_REL)
    if not os.path.isfile(path):
        return {}
    try:
        lock = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"unreadable robustness closure lock: {exc}") from exc

    exact = {
        "robustness_closure_completed": True,
        "all_six_registered_categories_verified": True,
        "paper_winner_selected": False,
        "retained_design_selected": False,
        "retained_design_freeze_authorized": False,
        "full_development_refit_performed": False,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_predictor_values_inspected": False,
        "final_test_target_values_inspected": False,
        "final_test_evaluation_performed": False,
    }
    for key, want in exact.items():
        if lock.get(key) != want:
            raise HandoffError(
                f"robustness closure lock field {key}={lock.get(key)!r} != {want!r}"
            )
    return _assert_no_consumed_authorization_is_standing(
        _assert_stage128_action_sequence_and_track_a_invariants({
        "m1_robustness_closure_completed": True,
        "m1_robustness_closure_paper_winner_selected": False,
        "m1_robustness_closure_retained_design_selected": False,
        "m1_robustness_closure_retained_design_freeze_authorized": False,
        "next_research_action_id": _NEXT_RESEARCH_ACTION_ID_AFTER_ROBUSTNESS_CLOSURE,
        **derive_m1_retained_design_freeze_markers(root),
        **derive_stage127_m2_market_data_gate_markers(root),
        **derive_stage127_m2_zero_trade_semantics_markers(root),
        **derive_stage128_m2_d2_design_freeze_markers(root),
        **derive_stage128_m2_d2_gate_rerun_markers(root),
        **derive_stage127_m2_incremental_evaluation_markers(root),
        **derive_stage128_m2_retained_block_human_decision_markers(root),
        **derive_stage128_m3_macro_data_gate_markers(root),
        # Must come last: the supplementary M3I-2 contract lock succeeds the
        # CBI M3 Gate as the live action and owns the research pointers.
        **derive_stage128_m3i2_contract_lock_markers(root),
        **derive_stage128_m3i2_evidence_capture_markers(root),
        # Post-capture, read-only bundle audit: integrity only, so it may add
        # audit markers but must never move the scientific state.
        **derive_stage128_m3i2_independent_bundle_audit_markers(root),
        # Must come last: it publishes the LIVE evidence-capture PR topology
        # and demotes the contract-lock topology to explicit history.
        **derive_stage128_m3i2_live_pr_topology_markers(root),
        # Must come last: the final official documentary recovery succeeds the
        # (now merged) evidence capture as the live action and owns both the
        # research pointers and the live PR topology.
        **derive_stage128_m3i2_final_documentary_recovery_markers(root),
        # Must come after it: the human submission the recovery pointed at has
        # HAPPENED, so this recording owns the research pointers. It still
        # admits nothing and authorizes nothing.
        **derive_stage128_m3i2_inquiry_human_submission_markers(root),
        # Verification record only: it reports how the suite behaved, and is
        # never allowed to move a scientific marker.
        **derive_stage128_m3i2_full_suite_comparison_markers(root),
        # Must come last: Track B (the M3-LAG-WDI exploratory contract lock)
        # runs in PARALLEL with the still-active World Bank inquiry. It owns
        # the live PR topology, and it owns nothing else: it never advances a
        # Track A pointer and never terminates the inquiry.
        **derive_stage128_m3_lag_wdi_exploratory_markers(root),
        # Must come last within Track B: the retrieval is the newest Track B
        # action. It moves the Track B pointer from retrieval to the (still
        # unauthorized) post-retrieval audit. It admits nothing: acquisition
        # is not admission, and it never touches the Gate, modeling, the Final
        # Test or Track A.
        **derive_stage128_m3_lag_wdi_data_retrieval_markers(root),
        # Step C. Must come after the retrieval markers: the audit is the newer
        # Track B action and moves the pointer from the audit to the (still
        # unauthorized) Data Gate. Reading what is inside the bytes admits
        # nothing — it executes no Gate, computes no coverage against any
        # threshold and returns no admission decision.
        **derive_stage128_m3_lag_wdi_post_retrieval_audit_markers(root),
        # Step D. Must come after the step C markers: the executed Data Gate
        # is the newest Track B action and moves the pointer from the Gate to
        # the (still unauthorized) modeling step E. It is the ONLY action that
        # may compute coverage against the locked thresholds and return an
        # admission verdict — and a PASS admits DATA ONLY: it authorizes no
        # model fit, makes no claim that the FX feature is informative, and
        # never propagates authorization to step E.
        **derive_stage128_m3_lag_wdi_data_gate_markers(root),
        # The calendar-mapping lock. Must come after the Gate markers: it is
        # the newer Track B action, and it resolves the gap step D exposed.
        # It moves NO scientific result — the Gate verdict, coverage and
        # limitations are carried forward untouched — and it authorizes
        # nothing: locking a timing convention is not permission to build a
        # feature table, fit a model or start step E.
        **derive_stage128_m3_lag_wdi_calendar_mapping_lock_markers(root),
        # Step E. Must come after the calendar-mapping lock markers: the
        # exploratory incremental evaluation is the newest Track B action. It
        # is the ONLY action that may materialize the modeling feature table
        # and fit a model — and its result is SUPPLEMENTARY EXPLORATORY only:
        # it never enters the confirmatory Holm family, never makes a
        # superiority claim, never selects the paper winner and never unlocks
        # the Final Test.
        **derive_stage128_m3_lag_wdi_incremental_evaluation_markers(root),
        # Must come last: PR #78 (the contract lock) has been MERGED, so the
        # contract-lock topology above is history. This re-anchors the LIVE
        # topology onto the retrieval Draft PR #79 while carrying every pinned
        # historical PR role forward unchanged. Metadata only.
        **derive_stage128_m3_lag_wdi_retrieval_live_pr_topology_markers(root),
        # Must come last of all: the Track A waiting-period termination and
        # M3-LAG-WDI final-disposition decision succeeds every action above
        # on BOTH pointer chains. It owns neither PR topology (it carries no
        # topology of its own) nor any scientific artifact — it only
        # confirms, cross-checked against disk, that step E's result is
        # unmoved, and converges both the Track A and Track B pointers on
        # `human_decision_required`.
        **derive_stage128_m3i2_track_a_waiting_termination_markers(root),
        # Must come last of all: Stage129 is an ADDITIVE, design-only,
        # pre-retrieval contract lock for a distinct future block (M4). It
        # never advances the Track A pointer (`next_research_action_id`) or
        # the Track B pointer (`stage128_m3_lag_wdi_next_action_id`) set
        # above -- it publishes its own, separate M4 pointer instead.
        **derive_stage129_m4_governance_data_gate_contract_lock_markers(
            root),
        # Must come after the contract lock: the human decision to discontinue
        # M4 SUPERSEDES the contract lock's own M4 pointer, which still named
        # `stage129-m4-governance-data-gate`. A discontinued block may not keep
        # pointing at its own Gate. It still advances neither live research
        # pointer chain.
        **derive_stage129_m4_human_discontinuation_markers(root),
        # Must come after the discontinuation: the human manuscript-reporting
        # decision SUPERSEDES exactly one marker the discontinuation left
        # open -- how a never-admitted block's comparison is presented. It
        # resolves a REPORTING question only. It changes no scientific state:
        # the disposition, the comparison status, the null p-value, the null
        # formal Gate verdict, the four candidates and both live research
        # pointers all survive it untouched.
        **derive_stage129_m4_manuscript_reporting_decision_markers(root),
        }))


_RETAINED_DESIGN_FREEZE_REL = (
    "project/stage126/stage126_m1_retained_design_freeze.json"
)
_NEXT_RESEARCH_ACTION_ID_AFTER_RETAINED_DESIGN_FREEZE = (
    "stage127-m2-market-data-gate"
)


def derive_m1_retained_design_freeze_markers(root: str) -> dict:
    """Recognize the (decision-freeze-only) M1 retained-design freeze.

    Narrow, fail-closed recognition mirroring the robustness-closure
    recognition pattern above: if the freeze artifact is present and its
    ``status_flags`` are internally consistent (frozen, no execution, no
    winner, firewall untouched), the Handoff's ``next_research_action_id``
    advances to ``stage127-m2-market-data-gate`` (itself requiring a
    SEPARATE future human authorization -- this function never sets that
    authorization True and never marks M2 as started). Returns an empty
    dict when the freeze artifact has not yet been built, so pre-freeze
    Handoffs are unaffected.
    """
    path = os.path.join(root, _RETAINED_DESIGN_FREEZE_REL)
    if not os.path.isfile(path):
        return {}
    try:
        freeze = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"unreadable retained design freeze artifact: {exc}") from exc

    if freeze.get("decision_id") != "stage126-m1-retained-design-freeze":
        raise HandoffError("retained design freeze artifact decision_id mismatch")
    if freeze.get("last_completed_research_action_id") != (
        "stage126-m1-retained-design-freeze"
    ):
        raise HandoffError(
            "retained design freeze artifact last_completed_research_action_id mismatch"
        )
    if freeze.get("next_research_action_id") != (
        _NEXT_RESEARCH_ACTION_ID_AFTER_RETAINED_DESIGN_FREEZE
    ):
        raise HandoffError(
            "retained design freeze artifact next_research_action_id mismatch"
        )

    sf = freeze.get("status_flags") or {}
    exact = {
        "retained_design_freeze_completed": True,
        "paper_winner_selected": False,
        "final_model_selected": False,
        "full_development_refit_performed": False,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_evaluation_performed": False,
        "m2_started": False,
    }
    for key, want in exact.items():
        if sf.get(key) != want:
            raise HandoffError(
                f"retained design freeze status_flags field {key}={sf.get(key)!r} "
                f"!= {want!r}"
            )

    return {
        "retained_design_freeze_completed": True,
        "last_completed_research_action_id": (
            "stage126-m1-retained-design-freeze"
        ),
        "m2_started": False,
        "m2_authorized": False,
        "m2_data_collected": False,
        "paper_winner_selected": False,
        "final_model_selected": False,
        "full_development_refit_performed": False,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_predictor_values_inspected": False,
        "final_test_target_values_inspected": False,
        "final_test_evaluation_performed": False,
        "next_research_action_id": _NEXT_RESEARCH_ACTION_ID_AFTER_RETAINED_DESIGN_FREEZE,
    }


_PART2_QC_REL = "project/stage126/stage126_m1_robustness_part2_qc_report.json"
_PART2_COMPARISON_REL = (
    "project/stage126/stage126_m1_robustness_part2_primary_comparison.json"
)
_PART2_PART5_COMPAT_REL = (
    "project/stage126/"
    "stage126_m1_robustness_part2_part5_successor_compatibility.json"
)


def derive_part2_sample_robustness_markers(root: str) -> dict:
    """Derive the Part 2 sample-robustness comparison markers (fail-closed).

    The observed Part 2 ordering is REPORTED, whatever it is. It must never
    imply that the primary results, the locked confirmatory ordering, the
    selected configurations or a paper winner changed — any record claiming
    otherwise raises rather than being propagated into the Handoff.
    """
    cmp_path = os.path.join(root, _PART2_COMPARISON_REL)
    qc_path = os.path.join(root, _PART2_QC_REL)
    compat_path = os.path.join(root, _PART2_PART5_COMPAT_REL)
    if not (os.path.isfile(cmp_path) and os.path.isfile(qc_path)
            and os.path.isfile(compat_path)):
        return {}
    try:
        cmp_ = json.load(open(cmp_path, encoding="utf-8"))
        qc = json.load(open(qc_path, encoding="utf-8"))
        compat = json.load(open(compat_path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"unreadable Part 2 artifacts: {exc}") from exc

    if qc.get("all_pass") is not True or qc.get("failed_count") != 0:
        raise HandoffError("Part 2 QC is not all_pass (fail-closed)")

    cmp_exact = {
        "contract_version":
            "stage126_m1_robustness_part2_primary_comparison_v1",
        "category_id": _PART2_CATEGORY_ID,
        "changed_dimension": "sample",
        "scientific_role": "sample_robustness_sensitivity_only",
        "comparison_scope": "pooled_development_oof",
        "comparison_metric": "pr_auc",
        "primary_results_replaced": False,
        "primary_ordering_for_confirmatory_claims_changed": False,
        "selected_configurations_changed": False,
        "paper_winner_selected": False,
        "automatic_scientific_action_triggered": False,
        "ordering_reported_to_human_supervisor": True,
        "full_development_refit_authorized": False,
        "final_test_unlocked": False,
    }
    for key, expected in cmp_exact.items():
        if cmp_.get(key) != expected:
            raise HandoffError(
                f"Part 2 comparison field {key}={cmp_.get(key)!r} != {expected!r}"
            )
    observed = list(cmp_.get("part2_observed_sensitivity_ordering") or [])
    primary_order = list(cmp_.get("primary_observed_ordering") or [])
    if sorted(observed) != sorted(primary_order) or len(observed) != 3:
        raise HandoffError("Part 2 comparison orderings are not the three families")
    differs = cmp_.get("observed_ordering_differs_from_primary")
    if differs is not (observed != primary_order):
        raise HandoffError(
            "Part 2 comparison ordering-difference flag contradicts the orderings"
        )

    # The Part 2 QC must agree with the frozen Part 5 boundary record.
    if qc.get("stage125_part5_live_handoff_check_applicable") is not False:
        raise HandoffError("Part 2 QC part5 applicability flag mismatch")
    if qc.get("stage125_part5_source_modified") is not False:
        raise HandoffError("Part 2 QC reports a modified Part 5 source")
    if qc.get("stage125_part5_artifacts_modified") is not False:
        raise HandoffError("Part 2 QC reports modified Part 5 artifacts")
    if list(qc.get("stage125_part5_live_handoff_mismatch_fields") or []) != \
            _PART5_EXPECTED_MISMATCH_FIELDS:
        raise HandoffError("Part 2 QC mismatch-field list is not exact")
    if list(compat.get("expected_live_mismatch_fields") or []) != \
            _PART5_EXPECTED_MISMATCH_FIELDS:
        raise HandoffError(
            "Part 2 compatibility record expected_live_mismatch_fields "
            "is not the exact documented five-field set"
        )
    if compat.get("part1_completion_hash_is_not_the_current_hash") is not True:
        raise HandoffError(
            "Part 2 compatibility record does not separate the Part 1 "
            "completion-time test hash from the current hash"
        )
    hashes = {
        compat.get("stage125_part5_historical_test_file_sha256"),
        compat.get("stage126_part1_completion_test_file_sha256"),
        compat.get("stage126_part2_current_test_file_sha256"),
    }
    if len(hashes) != 3 or None in hashes or "" in hashes:
        raise HandoffError(
            "Part 2 compatibility record must carry three distinct "
            "successor-test-file hash generations"
        )
    if compat.get("part1_scientific_artifacts_byte_identical") is not True:
        raise HandoffError(
            "Part 2 compatibility record does not assert Part 1 byte identity"
        )

    _require_stage125_tree_unchanged(root)

    return {
        "m1_robustness_part2_observed_ordering": observed,
        "m1_robustness_part2_ordering_differs_from_primary": bool(differs),
        "m1_robustness_part2_sample_sensitivity_reported": True,
        "m1_primary_claim_ordering_preserved": True,
    }


_PART1_QC_REL = "project/stage126/stage126_m1_robustness_part1_qc_report.json"
_PART1_PART5_COMPAT_REL = (
    "project/stage126/"
    "stage126_m1_robustness_part1_part5_successor_compatibility.json"
)
_PART5_EXPECTED_MISMATCH_FIELDS = [
    "m1_robustness_started",
    "selected_qc_scope",
    "selected_qc_path",
    "contract_version",
    "last_completed_micro_part",
]
# The frozen Part 5 live-successor boundary is a property of having completed
# ANY robustness micro-part — it is not Part 1-specific and must not be
# re-pinned to whichever micro-part happens to be newest.
_PART5_SUCCESSOR_COMPATIBILITY_STATUS = (
    "expected_historical_contract_boundary_after_completed_robustness_micro_part"
)


def derive_part5_successor_compatibility_markers(root: str) -> dict:
    """Derive the frozen-Part-5 successor-compatibility markers (fail-closed).

    Emitted ONLY when the Part 1 authorization record and completion lock are
    valid (already checked by the caller), the Part 1 QC is all_pass, the
    compatibility record is internally consistent, and the complete tracked
    Stage125 tree is unchanged. Any inconsistency raises HandoffError rather
    than silently asserting that the frozen Part 5 boundary is understood.
    """
    compat_path = os.path.join(root, _PART1_PART5_COMPAT_REL)
    qc_path = os.path.join(root, _PART1_QC_REL)
    if not (os.path.isfile(compat_path) and os.path.isfile(qc_path)):
        return {}
    try:
        compat = json.load(open(compat_path, encoding="utf-8"))
        qc = json.load(open(qc_path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(
            f"unreadable Part 1 compatibility/QC artifacts: {exc}"
        ) from exc

    if qc.get("all_pass") is not True or qc.get("failed_count") != 0:
        raise HandoffError("Part 1 QC is not all_pass (fail-closed)")

    compat_exact = {
        "contract_id":
            "stage126_m1_robustness_part1_part5_successor_compatibility",
        "contract_version":
            "stage126_m1_robustness_part1_part5_successor_compatibility_v1",
        "part1_category_id": _PART1_CATEGORY_ID,
        "stage125_part5_artifacts_frozen": True,
        "stage125_part5_artifacts_modified": False,
        "stage125_part5_source_modified": False,
        "stage125_part5_live_handoff_check_applicable_after_part1": False,
        "stage125_part5_historical_closure_remains_valid": True,
        "part1_scientific_execution_valid": True,
        "part2_execution_authorized": False,
        "full_development_refit_performed": False,
        "final_test_access_authorized": False,
        "final_test_evaluation_performed": False,
    }
    for key, expected in compat_exact.items():
        if compat.get(key) != expected:
            raise HandoffError(
                f"Part 1 compatibility record field {key}="
                f"{compat.get(key)!r} != {expected!r}"
            )
    if list(compat.get("expected_live_mismatch_fields") or []) != \
            _PART5_EXPECTED_MISMATCH_FIELDS:
        raise HandoffError(
            "Part 1 compatibility record expected_live_mismatch_fields "
            "is not the exact documented five-field set"
        )
    # The QC must agree with the compatibility record.
    if qc.get("stage125_part5_live_handoff_check_applicable") is not False:
        raise HandoffError("Part 1 QC part5 applicability flag mismatch")
    if qc.get("stage125_part5_source_modified") is not False:
        raise HandoffError("Part 1 QC reports a modified Part 5 source")
    if qc.get("stage125_part5_artifacts_modified") is not False:
        raise HandoffError("Part 1 QC reports modified Part 5 artifacts")
    if list(qc.get("stage125_part5_live_handoff_mismatch_fields") or []) != \
            _PART5_EXPECTED_MISMATCH_FIELDS:
        raise HandoffError("Part 1 QC mismatch-field list is not exact")

    # The complete tracked Stage125 tree must be unchanged (fail-closed, git).
    _require_stage125_tree_unchanged(root)

    # The boundary status may only be emitted when a completed robustness
    # micro-part actually exists (fail-closed — never asserted speculatively).
    if active_micro_part_qc_scope(root, "") == "":
        raise HandoffError(
            "Part 5 successor-compatibility status requires a completed "
            "robustness micro-part (fail-closed)"
        )

    markers = {
        "stage125_part5_frozen_artifacts_verified": True,
        "stage125_part5_live_successor_check_applicable": False,
        # Generic, future-safe: the boundary is a property of ANY completed
        # robustness micro-part, not of Part 1 specifically. Naming Part 1 here
        # became untrue the moment Part 2 completed.
        "stage125_part5_successor_compatibility_status":
            _PART5_SUCCESSOR_COMPATIBILITY_STATUS,
    }
    markers.update(derive_part1_ordering_instability_markers(root))
    return markers


_PART1_COMPARISON_REL = (
    "project/stage126/stage126_m1_robustness_part1_primary_comparison.json"
)
_PART1_EXPECTED_OBSERVED_ORDERING = [
    "xgboost", "random_forest", "regularized_logistic_regression",
]


def derive_part1_ordering_instability_markers(root: str) -> dict:
    """Derive the observed-ordering-instability markers (fail-closed).

    The instability is REPORTED. It must never imply that the primary ordering,
    selected configurations or paper winner changed — any record claiming
    otherwise raises rather than being propagated into the Handoff.
    """
    path = os.path.join(root, _PART1_COMPARISON_REL)
    if not os.path.isfile(path):
        return {}
    try:
        cmp_ = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"unreadable Part 1 comparison artifact: {exc}") from exc

    exact = {
        "contract_version":
            "stage126_m1_robustness_part1_primary_comparison_v1",
        "comparison_scope": "pooled_development_oof",
        "comparison_metric": "pr_auc",
        "observed_ordering_differs_from_primary": True,
        "ordering_instability_reported_to_human_supervisor": True,
        "primary_ordering_for_confirmatory_claims_changed": False,
        "selected_configurations_changed": False,
        "paper_winner_selected": False,
        "automatic_scientific_action_triggered": False,
    }
    for key, expected in exact.items():
        if cmp_.get(key) != expected:
            raise HandoffError(
                f"Part 1 comparison field {key}={cmp_.get(key)!r} != {expected!r}"
            )
    observed = list(cmp_.get("part1_observed_sensitivity_ordering") or [])
    if observed != _PART1_EXPECTED_OBSERVED_ORDERING:
        raise HandoffError(
            f"Part 1 observed ordering {observed!r} != "
            f"{_PART1_EXPECTED_OBSERVED_ORDERING!r}"
        )
    return {
        "m1_robustness_part1_ordering_instability_reported": True,
        "m1_robustness_part1_observed_ordering": observed,
        "m1_primary_claim_ordering_preserved": True,
    }


def _require_stage125_tree_unchanged(root: str) -> None:
    """Fail closed unless the tracked project/stage125/ tree is unchanged."""
    base = "6a4f05da219db7faea5a27c2adbee6b55497ec01"
    offending: list[str] = []
    for args, label in (
        (["diff", "--name-only", base, "HEAD", "--", "project/stage125/"],
         "committed"),
        (["diff", "--cached", "--name-only", "HEAD", "--", "project/stage125/"],
         "staged"),
        (["diff", "--name-only", "--", "project/stage125/"], "unstaged"),
        (["ls-files", "--others", "--exclude-standard", "--", "project/stage125/"],
         "untracked"),
    ):
        out = _git(root, *args)
        offending += [f"{label}:{p}" for p in out.splitlines() if p.strip()]
    if offending:
        raise HandoffError(
            f"frozen Stage125 tree changed (fail-closed): {sorted(set(offending))}"
        )


def detect_markers(root: str) -> dict:
    def any_exists(paths) -> bool:
        return any(os.path.isfile(os.path.join(root, p)) for p in paths)

    return {
        "verified_master_created": os.path.isfile(os.path.join(root, VERIFIED_MASTER_PATH)),
        "gate_b_started": any_exists(GATE_B_MARKER_PATHS),
        "modeling_started": any_exists(MODELING_MARKER_PATHS),
    }


def extract_qc_workflow_markers(qc: dict) -> dict:
    """Fail-closed extraction of scope-specific workflow markers from QC."""
    scope = qc.get("stage")
    if not scope:
        raise HandoffError("QC report missing 'stage' (fail-closed)")
    required = QC_WORKFLOW_FIELDS_BY_SCOPE.get(scope)
    if required is None:
        return {}
    missing = [key for key in required if key not in qc]
    if missing:
        raise HandoffError(
            f"QC scope '{scope}' missing required workflow field(s) "
            f"{missing} (fail-closed)"
        )
    return {key: qc[key] for key in required}


def _require_json_artifact(root: str, rel: str) -> dict:
    path = os.path.join(root, rel)
    if not os.path.isfile(path):
        raise HandoffError(
            f"missing frozen Stage125 artifact '{rel}' (fail-closed)"
        )
    try:
        data = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(
            f"unreadable frozen Stage125 artifact '{rel}': {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise HandoffError(
            f"frozen Stage125 artifact '{rel}' is not a JSON object "
            "(fail-closed)"
        )
    return data


def _require_field(artifact: dict, rel: str, key: str):
    if key not in artifact:
        raise HandoffError(
            f"frozen Stage125 artifact '{rel}' missing required field "
            f"'{key}' (fail-closed)"
        )
    return artifact[key]


def _agree_or_fail(field: str, values: list[tuple[str, object]]) -> object:
    """Require every (source, value) pair to agree; return the shared value."""
    if not values:
        raise HandoffError(
            f"no sources for temporal-availability field '{field}' "
            "(fail-closed)"
        )
    first_src, first_val = values[0]
    for src, val in values[1:]:
        if val != first_val:
            raise HandoffError(
                f"Stage125 temporal-availability conflict on '{field}': "
                f"{first_src}={first_val!r} vs {src}={val!r} (fail-closed)"
            )
    return first_val


def derive_stage125_temporal_availability_invariants(root: str) -> dict:
    """Derive repository-wide temporal-availability invariants from Stage125.

    Reads frozen Stage125 contracts/artifacts only. Used to carry these
    invariants into the Stage126 Handoff scope without hardcoding them into
    generated outputs independently of the repository.
    """
    part3b1e = _require_json_artifact(root, _STAGE125_PART3B1E_LOCK_REL)
    four_month = _require_json_artifact(root, _STAGE125_PART3C_FOUR_MONTH_REL)
    part3c = _require_json_artifact(root, _STAGE125_PART3C_CONTRACT_REL)
    part4 = _require_json_artifact(root, _STAGE125_PART4_SAP_REL)
    part5 = _require_json_artifact(root, _STAGE125_PART5_CLOSURE_REL)

    financial_frozen = _agree_or_fail(
        "financial_data_researcher_verified_frozen",
        [
            (
                _STAGE125_PART3B1E_LOCK_REL,
                _require_field(
                    part3b1e,
                    _STAGE125_PART3B1E_LOCK_REL,
                    "financial_data_researcher_verified_frozen",
                ),
            ),
            (
                _STAGE125_PART4_SAP_REL,
                _require_field(
                    part4,
                    _STAGE125_PART4_SAP_REL,
                    "financial_data_researcher_verified_frozen",
                ),
            ),
        ],
    )
    broad_codal_stopped = _agree_or_fail(
        "broad_codal_capture_stopped",
        [
            (
                _STAGE125_PART3B1E_LOCK_REL,
                _require_field(
                    part3b1e,
                    _STAGE125_PART3B1E_LOCK_REL,
                    "broad_codal_capture_stopped",
                ),
            ),
            (
                _STAGE125_PART4_SAP_REL,
                _require_field(
                    part4,
                    _STAGE125_PART4_SAP_REL,
                    "broad_codal_capture_stopped",
                ),
            ),
        ],
    )
    active_method = _agree_or_fail(
        "active_availability_method",
        [
            (
                _STAGE125_PART3C_FOUR_MONTH_REL,
                _require_field(
                    four_month,
                    _STAGE125_PART3C_FOUR_MONTH_REL,
                    "active_availability_method",
                ),
            ),
            (
                _STAGE125_PART3C_CONTRACT_REL,
                _require_field(
                    part3c, _STAGE125_PART3C_CONTRACT_REL, "availability_method",
                ),
            ),
            (
                _STAGE125_PART4_SAP_REL,
                _require_field(
                    part4,
                    _STAGE125_PART4_SAP_REL,
                    "active_availability_method",
                ),
            ),
            (
                _STAGE125_PART5_CLOSURE_REL,
                _require_field(
                    part5,
                    _STAGE125_PART5_CLOSURE_REL,
                    "active_availability_method",
                ),
            ),
        ],
    )
    active_lag_months = _agree_or_fail(
        "active_availability_lag_months",
        [
            (
                _STAGE125_PART3C_FOUR_MONTH_REL,
                _require_field(
                    four_month, _STAGE125_PART3C_FOUR_MONTH_REL, "active_lag_months",
                ),
            ),
            (
                _STAGE125_PART3C_CONTRACT_REL,
                _require_field(
                    part3c, _STAGE125_PART3C_CONTRACT_REL, "active_lag_months",
                ),
            ),
            (
                _STAGE125_PART4_SAP_REL,
                _require_field(
                    part4,
                    _STAGE125_PART4_SAP_REL,
                    "active_availability_lag_months",
                ),
            ),
            (
                _STAGE125_PART5_CLOSURE_REL,
                _require_field(
                    part5,
                    _STAGE125_PART5_CLOSURE_REL,
                    "active_availability_lag_months",
                ),
            ),
        ],
    )
    four_month_locked = _require_field(
        part3c, _STAGE125_PART3C_CONTRACT_REL, "four_month_regulatory_lag_locked",
    )
    six_month_superseded = _require_field(
        part3c, _STAGE125_PART3C_CONTRACT_REL, "six_month_lag_superseded",
    )
    historical_six_retained = _agree_or_fail(
        "historical_six_month_decision_retained",
        [
            (
                _STAGE125_PART3C_FOUR_MONTH_REL,
                _require_field(
                    four_month,
                    _STAGE125_PART3C_FOUR_MONTH_REL,
                    "historical_six_month_decision_retained",
                ),
            ),
            (
                _STAGE125_PART3C_CONTRACT_REL,
                _require_field(
                    part3c,
                    _STAGE125_PART3C_CONTRACT_REL,
                    "historical_six_month_decision_retained",
                ),
            ),
        ],
    )
    row_level_pub = _agree_or_fail(
        "row_level_publish_datetime_collection_required",
        [
            (
                _STAGE125_PART3B1E_LOCK_REL,
                _require_field(
                    part3b1e,
                    _STAGE125_PART3B1E_LOCK_REL,
                    "row_level_publish_datetime_collection_required",
                ),
            ),
            (
                _STAGE125_PART3C_FOUR_MONTH_REL,
                _require_field(
                    four_month,
                    _STAGE125_PART3C_FOUR_MONTH_REL,
                    "row_level_publish_datetime_collection_required",
                ),
            ),
            (
                _STAGE125_PART3C_CONTRACT_REL,
                _require_field(
                    part3c,
                    _STAGE125_PART3C_CONTRACT_REL,
                    "row_level_publish_datetime_collection_required",
                ),
            ),
        ],
    )
    part3b_completed = _agree_or_fail(
        "part3b_completed",
        [
            (
                _STAGE125_PART3B1E_LOCK_REL,
                _require_field(
                    part3b1e, _STAGE125_PART3B1E_LOCK_REL, "part3b_completed",
                ),
            ),
            (
                _STAGE125_PART3C_CONTRACT_REL,
                _require_field(
                    part3c, _STAGE125_PART3C_CONTRACT_REL, "part3b_completed",
                ),
            ),
            (
                _STAGE125_PART5_CLOSURE_REL,
                _require_field(
                    part5, _STAGE125_PART5_CLOSURE_REL, "part3b_completed",
                ),
            ),
        ],
    )
    part3c_completed = _require_field(
        part3c,
        _STAGE125_PART3C_CONTRACT_REL,
        "part3c_leakage_safe_finalization_completed",
    )
    part4_locked = _require_field(
        part4,
        _STAGE125_PART4_SAP_REL,
        "part4_statistical_analysis_plan_locked",
    )
    stage125_completed = _require_field(
        part5, _STAGE125_PART5_CLOSURE_REL, "stage125_completed",
    )

    derived = {
        "financial_data_researcher_verified_frozen": financial_frozen,
        "broad_codal_capture_stopped": broad_codal_stopped,
        "active_availability_method": active_method,
        "active_availability_lag_months": active_lag_months,
        "four_month_regulatory_lag_locked": four_month_locked,
        "six_month_lag_superseded": six_month_superseded,
        "historical_six_month_decision_retained": historical_six_retained,
        "row_level_publish_datetime_collection_required": row_level_pub,
        "part3b_completed": part3b_completed,
        "part3c_leakage_safe_finalization_completed": part3c_completed,
        "part4_statistical_analysis_plan_locked": part4_locked,
        "stage125_completed": stage125_completed,
    }
    missing = [
        key for key in STAGE126_CARRIED_TEMPORAL_AVAILABILITY_FIELDS
        if key not in derived
    ]
    if missing:
        raise HandoffError(
            f"derived Stage125 temporal-availability invariants missing "
            f"{missing} (fail-closed)"
        )
    return {
        key: derived[key]
        for key in STAGE126_CARRIED_TEMPORAL_AVAILABILITY_FIELDS
    }


def merge_stage126_carried_temporal_availability(
    root: str, scope: str, qc_workflow: dict,
) -> dict:
    """Carry Stage125 temporal-availability invariants into Stage126 scope.

    Every Stage126 scope carries the invariants, including the robustness
    micro-part scopes (a micro-part never drops repository-wide invariants).
    """
    if scope not in STAGE126_QC_SCOPES:
        return qc_workflow
    carried = derive_stage125_temporal_availability_invariants(root)
    merged = dict(qc_workflow)
    for key, value in carried.items():
        if key in merged and merged[key] != value:
            raise HandoffError(
                f"Stage126 QC workflow marker '{key}'={merged[key]!r} "
                f"conflicts with Stage125-derived invariant {value!r} "
                "(fail-closed)"
            )
        merged[key] = value
    return merged


def _verified_master_tickers(root: str) -> list[str] | None:
    """Read tickers from the verified master CSV if it exists."""
    vm_path = os.path.join(root, VERIFIED_MASTER_PATH)
    if not os.path.isfile(vm_path):
        return None
    try:
        with open(vm_path, encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            return [row["ticker"] for row in reader if row.get("ticker")]
    except (OSError, KeyError):
        return None


# --------------------------------------------------------------------------- #
# State assembly + fingerprint
# --------------------------------------------------------------------------- #

_PART1_QC_SCOPE = "stage126_m1_robustness_part1_target_proximity"
_PART1_MICRO_PART_ID = "stage126-m1-robustness-part1-target-proximity"
_PART2_QC_SCOPE = "stage126_m1_robustness_part2_listing_rule_b"

# Robustness micro-part packages are DISCOVERED by the shared naming
# convention, newest-last, so a newly completed part is recognized without
# adding a per-part entry here.
_MAX_ROBUSTNESS_MICRO_PARTS = 6


def discover_robustness_micro_parts(root: str) -> list:
    """Completed robustness micro-part packages, oldest first.

    Each entry is ``(qc_scope, micro_part_id, lock_rel, qc_rel)`` derived from
    the part's own completion lock and QC report — never hard-coded per part.
    """
    found = []
    for index in range(1, _MAX_ROBUSTNESS_MICRO_PARTS + 1):
        prefix = f"stage126_m1_robustness_part{index}"
        lock_rel = f"project/stage126/{prefix}_completion_lock.json"
        qc_rel = f"project/stage126/{prefix}_qc_report.json"
        lock_path = os.path.join(root, lock_rel)
        qc_path = os.path.join(root, qc_rel)
        if not (os.path.isfile(lock_path) and os.path.isfile(qc_path)):
            continue
        try:
            lock = json.load(open(lock_path, encoding="utf-8"))
            qc = json.load(open(qc_path, encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HandoffError(
                f"unreadable robustness part {index} artifacts: {exc}"
            ) from exc
        qc_scope = qc.get("stage") or ""
        micro_id = lock.get("micro_part_id") or qc_scope.replace("_", "-")
        if not qc_scope or not micro_id:
            raise HandoffError(
                f"robustness part {index} does not declare a QC scope or "
                f"micro-part identifier (fail-closed)"
            )
        found.append((qc_scope, micro_id, lock_rel, qc_rel))
    return found


def active_micro_part_qc_scope(root: str, default_scope: str) -> str:
    """Return the QC scope of the newest completed robustness micro-part.

    Falls back to ``default_scope`` when no robustness micro-part has completed.
    This selects which QC report describes current state; it never advances the
    research-action pointers (which stay on the Stage126 M1 research action).
    """
    parts = discover_robustness_micro_parts(root)
    return parts[-1][0] if parts else default_scope


def active_micro_part_id(root: str, default_id: str) -> str:
    """Micro-part identifier for the newest completed robustness micro-part."""
    parts = discover_robustness_micro_parts(root)
    return parts[-1][1] if parts else default_id


def semantic_state(root: str):
    head = head_commit(root)
    roadmap = read_roadmap(root)
    workstream = roadmap["active_research_workstream_id"].replace("-", "_")
    qc_scope_val = roadmap.get("qc_scope", "")
    qc_scope = qc_scope_val.replace("-", "_") if qc_scope_val else workstream
    # A completed robustness micro-part supplies the newest QC for the active
    # workstream. It never advances the research-action pointers.
    qc_scope = active_micro_part_qc_scope(root, qc_scope)
    qc = select_qc_report(root, qc_scope, head)
    frozen = frozen_asset_report(root)

    # Fatal: any FROZEN (non-regenerable) tracked asset that is missing or
    # mismatched. Regenerable / gitignored files are exempt by classification.
    fatal = []
    for r in frozen:
        if not r["frozen"]:
            continue
        if not r["tracked"]:
            fatal.append(f"untracked non-ignored frozen asset {r['path']}")
        elif not r["exists"]:
            fatal.append(f"missing {r['path']}")
        elif not r["matches"]:
            fatal.append(f"mismatch {r['path']}")
    if fatal:
        raise HandoffError("frozen-asset integrity failure (fail-closed): "
                           + "; ".join(fatal))

    # Use verified master tickers when available (Gate B readiness scope);
    # fall back to QC report tickers when the verified master does not exist.
    vm_tickers = _verified_master_tickers(root)
    tickers = sorted(vm_tickers) if vm_tickers is not None else sorted(qc["tickers"])
    qc_workflow = extract_qc_workflow_markers(qc)
    qc_workflow = merge_stage126_carried_temporal_availability(
        root, qc["stage"], qc_workflow,
    )

    state = {
        "last_stage_commit": last_stage_commit(root),
        "selected_qc": {
            "path": qc["_path"],
            "source_commit": qc["source_commit"],
            "assertion_count": qc["assertion_count"],
            "failed_count": qc["failed_count"],
            "all_pass": qc["all_pass"],
            "source_file_sha256": qc["source_file_sha256"],
            "test_file_sha256": qc["test_file_sha256"],
        },
        # Only FROZEN (verified) files feed the fingerprint, by expected SHA.
        # Regenerable files are excluded so benign log churn is not "drift".
        "frozen_assets": {
            r["path"]: r["expected_sha256"]
            for r in sorted(frozen, key=lambda x: x["path"]) if r["frozen"]
        },
        "roadmap": {
            "active_research_workstream_id": roadmap["active_research_workstream_id"],
            "last_completed_research_action_id": roadmap["last_completed_research_action_id"],
            "next_research_action_id": roadmap["next_research_action_id"],
        },
        "markers": detect_markers(root),
        "qc_workflow": qc_workflow,
        "m1_robustness_decision": derive_m1_robustness_decision_markers(root),
        "tickers": tickers,
    }
    return state, head, qc, roadmap, frozen


def fingerprint(state: dict) -> str:
    payload = json.dumps(state, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_handoff_state(root: str):
    state, head, qc, roadmap, frozen = semantic_state(root)
    derived_stage, derived_batch = derive_stage_batch(qc["stage"])
    stage = qc.get("current_stage") or derived_stage
    batch = qc.get("current_batch") or derived_batch
    # `current_stage` claims to describe the CURRENT live research state, so it
    # cannot keep naming Stage126 once the Stage128 D2 boundary-month design
    # freeze is complete — that would leave the snapshot saying "Stage126"
    # beside pointers that have advanced to `stage128-m2-d2-gate-rerun`. The
    # Stage126 label survives, truthfully, in the SEPARATE micro-part QC role
    # below (`selected_qc_scope` / `last_completed_micro_part*`), which is about
    # the newest completed robustness micro-part, not the live stage.
    if derive_stage128_m2_d2_design_freeze_markers(root):
        stage = _STAGE128_CURRENT_STAGE
    record = {
        "schema_version": GENERATOR_VERSION,
        "repository": derive_repository(root),
        # Informational only (see VOLATILE_FIELDS).
        "observed_branch": current_branch(root),
        "observed_repository_head_commit": head,
        "baseline_branch": "origin/main",
        "baseline_commit": _safe(lambda: _git(root, "rev-parse", "origin/main")),
        "generated_from_commit": head,
        # Semantic anchors (checked by the validator).
        "last_stage_commit": state["last_stage_commit"],
        "qc_source_commit": state["selected_qc"]["source_commit"],
        "current_stage": stage,
        "current_batch": batch,
        "active_workstream": roadmap["active_research_workstream_id"].replace("-", "_"),
        # The workstream the live one succeeded. Once the supplementary M3I-2
        # contract lock is live, its predecessor is the CBI M3 macro data
        # Gate, not the older M2 D2 boundary-month workstream.
        "active_workstream_predecessor_context": (
            _STAGE128_M3I2_EVIDENCE_WORKSTREAM_ID.replace("-", "_")
            if derive_stage128_m3i2_final_documentary_recovery_markers(
                root).get("stage128_m3i2_final_documentary_recovery_initiated")
            else _STAGE128_M3I2_ACTIVE_WORKSTREAM_ID.replace("-", "_")
            if derive_stage128_m3i2_evidence_capture_markers(root).get(
                "stage128_m3i2_evidence_capture_executed")
            else _STAGE128_M3_ACTIVE_WORKSTREAM_ID.replace("-", "_")
            if derive_stage128_m3i2_contract_lock_markers(root).get(
                "stage128_m3i2_contract_lock_executed")
            else "stage128_m2_d2_boundary_month_equity_return"),
        # Newest completed micro-part (robustness micro-parts included). The
        # research-action pointers below are deliberately NOT advanced.
        "last_completed_micro_part": active_micro_part_id(
            root, roadmap["last_completed_research_action_id"],
        ),
        "next_research_action_id": roadmap["next_research_action_id"],
        "selected_qc_scope": qc["stage"],
        "selected_qc_path": state["selected_qc"]["path"],
        "qc_assertions": state["selected_qc"]["assertion_count"],
        "qc_failed": state["selected_qc"]["failed_count"],
        "qc_all_pass": state["selected_qc"]["all_pass"],
        "modeling_started": state["markers"]["modeling_started"],
        "gate_b_started": state["markers"]["gate_b_started"],
        "verified_master_created": state["markers"]["verified_master_created"],
        "tickers": state["tickers"],
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "state_fingerprint": fingerprint(state),
    }
    record.update(state["qc_workflow"])
    record.update(state["m1_robustness_decision"])
    # The live M3I-2 PR head is the CURRENT repository head: informational and
    # HEAD-relative (see VOLATILE_FIELDS), never pinned to a superseded SHA and
    # never part of the fingerprinted semantic state.
    if record.get("stage128_m3i2_live_pr_number") is not None:
        record["stage128_m3i2_live_pr_head_commit"] = head
    return record, state, frozen


def compute_record(root: str) -> dict:
    return build_handoff_state(root)[0]


def _safe(fn):
    try:
        return fn()
    except HandoffError:
        return None


def projection(record: dict) -> dict:
    """Non-volatile semantic projection of a handoff_state record."""
    return {k: v for k, v in record.items() if k not in VOLATILE_FIELDS}


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #

_AUTO_BANNER = (
    "<!-- AUTO-GENERATED by project/scripts/update_ai_handoff.py — do not edit by "
    "hand. Run `python project/scripts/update_ai_handoff.py --from-repository "
    "--write` to refresh. -->\n\n"
)


def render_current_state(record: dict) -> str:
    qc_ok = "✅" if record["qc_all_pass"] and record["qc_failed"] == 0 else "❌"
    lines = [
        _AUTO_BANNER,
        "# CURRENT STATE\n",
        "_Generated from the repository (git + QC). Do not edit by hand._\n",
        "## Snapshot\n",
        f"- **Stage / Batch:** {record['current_stage']} / {record['current_batch']}",
        f"- **Active workstream:** `{record['active_workstream']}`",
        # `last_completed_micro_part` tracks the newest completed MICRO-PART
        # (robustness micro-parts included). It is deliberately NOT labelled a
        # completed research action — the research-action chain is reported
        # separately below and is never advanced by a micro-part.
        f"- **Last completed micro-part:** `{record['last_completed_micro_part']}`",
        f"- **Next research action:** `{record['next_research_action_id']}`",
        f"- **Last stage commit:** `{record['last_stage_commit']}`",
        f"- **Generated from commit:** `{record['generated_from_commit']}` "
        f"(branch `{record['observed_branch']}`, informational)",
        f"- **Baseline:** `{record['baseline_branch']}` @ `{record['baseline_commit']}`",
        "",
        "## Current-state validation\n",
    ]
    if "current_state_validation_scope" in record:
        cs_ok = (
            "✅" if record.get("current_state_validation_all_pass")
            and record.get("current_state_validation_failed") == 0 else "❌"
        )
        lines += [
            "_The independent Stage126 current-state validator is the SOLE "
            "current-state validation surface._\n",
            f"- {cs_ok} **{record['current_state_validation_assertions']} "
            f"assertions, {record['current_state_validation_failed']} failed**, "
            f"all_pass={record['current_state_validation_all_pass']}",
            f"- Scope: `{record['current_state_validation_scope']}`",
            f"- Report: `{record['current_state_validation_path']}`",
            f"- Metadata: `{record['current_state_validation_metadata_path']}`",
            "",
        ]
    else:
        lines += ["_Not yet generated._\n", ""]
    if record.get("stage127_m2_market_data_gate_executed"):
        status = record.get("stage127_m2_market_data_gate_status", "")
        resolved = record.get("stage127_m2_market_data_gate_resolved")
        admitted = record.get("stage127_m2_block_admitted_for_modeling")
        gate_ok = "✅" if admitted else "⛔"
        # Once the Stage128 D2 design freeze is recognized as completed, the
        # Stage127 Gate is no longer the CURRENT scientific action and is no
        # longer awaiting a human decision: it is a HISTORICAL, completed and
        # resolved Gate whose terminal FAIL result stands unchanged.
        stage128_freeze = record.get("stage128_m2_d2_design_freeze_completed")
        if stage128_freeze:
            heading = (
                "## Stage127 — M2 market-data admission Gate "
                "(HISTORICAL — COMPLETED AND RESOLVED)\n"
            )
            preamble = (
                "_Historical record, **not** the current scientific action. "
                "The Gate was executed under its own pre-existing human "
                "authorization and returned a terminal, resolved result. The "
                "human review it originally required has since been completed: "
                "it was discharged by the separately authorized "
                "`stage128-m2-boundary-month-return-design-freeze` action "
                "(see the Stage128 section below), which is the answer to "
                "\"which scientific action follows the failed M2 extension\". "
                "The historical D0 Gate result below remains "
                "`FAIL_M2_DATA_GATE` and is **never** rewritten to PASS._\n"
            )
        else:
            heading = "## Stage127 — M2 market-data admission Gate\n"
            preamble = (
                "_The current scientific action. Its human authorization "
                "already exists; the Gate has been executed and its result is "
                "reported here. This section exists so the snapshot can never "
                "render the project as though Stage127 had not happened._\n"
            )
        lines += [
            heading,
            preamble,
            f"- {gate_ok} **Gate status:** `{status}`",
            f"- **Executed:** {record['stage127_m2_market_data_gate_executed']}"
            f" — **resolved (terminal observed decision):** {resolved}",
            f"- **M2 block admitted for modeling:** {admitted}",
            f"- **Terminal result pending human review:** "
            f"{record.get('stage127_m2_market_data_gate_terminal_result_pending_human_review')}",
            f"- **M2 market evidence collected:** "
            f"{record.get('stage127_m2_market_data_evidence_collected')}"
            f" — **independently validated:** "
            f"{record.get('stage127_m2_market_data_evidence_validated')}"
            f" ({record.get('stage127_m2_market_data_evidence_observation_count')}"
            " normalized daily observations)",
            f"- **Evidence bundle SHA256:** "
            f"`{record.get('stage127_m2_market_data_evidence_bundle_sha256')}`",
            "- Evidence collection is recorded **separately** from block "
            "admission. The frozen Stage125 Part 4 marker `m2_data_collected` "
            "is pinned `false` as **historical schema state** — in that "
            "schema it is a prohibition marker meaning \"M2 data has entered "
            "the authorized M2 modeling pipeline\", and flipping it would "
            "mutate a frozen scientific artifact. It is NOT live state and "
            "NOT a statement that no M2 evidence exists: the live fields are "
            "`m2_market_data_evidence_collected`, "
            "`m2_market_data_evidence_validated` and "
            "`m2_data_entered_authorized_incremental_modeling_pipeline`.",
            f"- **M2 incremental evaluation authorized (live):** "
            f"{record.get('m2_incremental_evaluation_authorized')} — "
            f"**M2 modeling started (live):** "
            f"{record.get('m2_modeling_started')}. These are CURRENT global "
            "markers, not statements about this historical Gate: this Gate "
            "fitted no model. Any `True` above was produced by a later, "
            "separately authorized action.",
            "",
        ]
    if record.get("stage127_m2_trading_day_semantics_adjudication_completed"):
        outcome = record.get(
            "stage127_m2_trading_day_semantics_adjudication_outcome", "")
        conformant = record.get("stage127_m2_current_implementation_conformant")
        lines += [
            "### Stage127 — zero-trade \"trading day\" semantics adjudication\n",
            "_Why `equity_return_window` coverage is 0.4039. This subsection "
            "records the SEMANTIC state only; it changes no canonical "
            "result._\n",
            f"- **Official TSETMC evidence:** completed and independently "
            f"validated — "
            f"{record.get('stage127_m2_zero_trade_semantics_raw_artifacts_sha256_verified')}"
            " raw artifacts SHA256-verified",
            f"- **Evidence bundle SHA256:** "
            f"`{record.get('stage127_m2_zero_trade_semantics_bundle_sha256')}`",
            f"- **Endpoint dates that are official InstrumentCalendar members:**"
            f" {record.get('stage127_m2_point_dates_in_official_instrument_calendar')}"
            f" / {record.get('stage127_m2_point_date_requests')}",
            f"- **RANGE requests with InstrumentCalendar == "
            f"ClosingPriceDailyList date set:** "
            f"{record.get('stage127_m2_range_calendar_vs_daily_equal')} / "
            f"{record.get('stage127_m2_range_requests')}",
            f"- **Adjudication outcome:** `{outcome}` (Outcome A)",
            f"- **Current implementation conformant:** {conformant}",
            f"- **Cases still pending external adjudication:** "
            f"{record.get('stage127_m2_semantics_pending_count')}",
            f"- **Canonical Gate changed by the adjudication:** "
            f"{record.get('stage127_m2_semantics_canonical_gate_changed')} — "
            f"Gate remains "
            f"`{record.get('stage127_m2_market_data_gate_status')}` with "
            "coverage 269 / 576 / 576 and common sample 269 of 666 pairs",
            f"- **Model fits:** "
            f"{record.get('stage127_m2_semantics_model_fits')} — "
            f"**predictions:** "
            f"{record.get('stage127_m2_semantics_predictions_generated')} — "
            f"**final-test access:** "
            f"{record.get('stage127_m2_semantics_final_test_access')}",
            "- **No M2 modeling authorization follows from this.** The "
            "shortfall is now established as TRUE frozen-contract missingness "
            "rather than a data defect.",
        ]
        if record.get("stage128_m2_d2_design_freeze_completed"):
            lines += [
                "- ✅ **Human decision COMPLETED (historical).** A human "
                "decision on which scientific roadmap action follows the "
                "failed M2 extension was originally required "
                "(`stage127_m2_human_review_originally_required=true`). It was "
                "made and discharged by the separately authorized "
                "`stage128-m2-boundary-month-return-design-freeze` action; "
                "`stage127_m2_semantics_human_decision_required` is therefore "
                "now `false`. The historical Gate result is unchanged.",
            ]
        else:
            lines += [
                "- ⏳ **Human decision still required:** which scientific "
                "roadmap action follows the failed M2 extension.",
            ]
        lines += [""]
    if record.get("stage128_m2_d2_design_freeze_completed"):
        # Once the canonical Gate re-run has executed AND resolved, the
        # Gate re-run section below is the SOLE CURRENT scientific-action
        # section. This section then renders as historical, completed,
        # frozen-design context: it must not stay marked (CURRENT), must not
        # inherit the global `last_completed_research_action_id`, and must not
        # carry a live "next action" pointer.
        freeze_is_historical = bool(
            record.get("stage128_m2_d2_gate_rerun_executed")
            and record.get("stage128_m2_d2_gate_rerun_resolved")
        )
        if freeze_is_historical:
            lines += [
                "## Stage128 — M2 D2 boundary-month equity-return design "
                "freeze (COMPLETED DESIGN CONTRACT)\n",
                "_Historical, completed frozen-design context — **not** the "
                "current scientific action. This was a DESIGN-FREEZE / "
                "CONTRACT action only: no canonical Gate was executed, no "
                "model was fit, no prediction was generated and no "
                "final-test predictor or target value was parsed, inspected "
                "or used. The canonical Gate re-run section below is the "
                "current scientific action._\n",
            ]
        else:
            lines += [
                "## Stage128 — M2 D2 boundary-month equity-return design "
                "freeze (CURRENT)\n",
                "_The current scientific state. This is a DESIGN-FREEZE / "
                "CONTRACT action only: no canonical Gate was executed, no "
                "model was fit, no prediction was generated and no "
                "final-test predictor or target value was parsed, inspected "
                "or used._\n",
            ]
        lines += [
            "- ✅ **D2 design freeze completed:** "
            f"{record['stage128_m2_d2_design_freeze_completed']}",
            "- **Frozen primary M2 equity-return construct:** "
            "`BOUNDARY_MONTH_ASOF_TRAILING_EQUITY_RETURN` — calendar "
            "convention **GREGORIAN** (selected for coherence with the frozen "
            "Gregorian market-time axis, not because it clears a coverage "
            "threshold)",
            "- ⛔ **Historical D0 Gate remains** "
            f"`{record.get('stage127_m2_market_data_gate_status')}` — "
            "preserved unchanged; never rewritten to PASS",
            # NB: deliberately NOT phrased "Last completed research action" —
            # that exact phrase is reserved by test_ai_handoff so a robustness
            # micro-part can never be mislabelled as a research action.
            # The action completed BY THIS FREEZE is a fixed historical fact.
            # It must never inherit the global
            # `last_completed_research_action_id`, which advances with every
            # later research action.
            "- **Research action completed by this freeze:** "
            f"`{_STAGE128_M2_D2_FREEZE_ACTION_ID}`",
        ]
        if freeze_is_historical:
            # Historical successor statement only. The SOLE live next-action
            # pointer is rendered in the Gate re-run CURRENT section below.
            lines += [
                "- **Immediate successor of this freeze (historical):** "
                f"`{_NEXT_RESEARCH_ACTION_ID_AFTER_STAGE128_M2_D2_FREEZE}` — "
                "the canonical M2 Gate re-run under the frozen D2 construct, "
                "now COMPLETED (see the current section below). This line is "
                "historical: it is not the branch's live next-action pointer.",
            ]
        else:
            lines += [
                "- **Next research action (pointer only):** "
                f"`{record['next_research_action_id']}` — the canonical M2 "
                "Gate re-run under the frozen D2 construct",
            ]
        lines += [
            "- ⛔ **D2 Gate rerun authorized (standing):** "
            f"{record.get('stage128_m2_d2_gate_rerun_authorized')} — "
            + ("the one-action authorization that executed the Gate re-run "
               "was consumed by that execution and is not standing"
               if freeze_is_historical else
               "identifying the next action is NOT an authorization to "
               "execute it; that requires a separate, explicit human "
               "authorization"),
            f"- ⛔ **M2 admitted:** {record.get('m2_authorized')} — "
            f"**M2 incremental evaluation authorized:** "
            f"{record.get('m2_incremental_evaluation_authorized')} — "
            "**this freeze started no modeling** (it is a design contract "
            "only; any live M2 execution marker was set by a later, "
            "separately authorized action)",
            "- 🔒 **Final test locked:** final_test_unlocked="
            f"{record.get('final_test_unlocked')}, "
            f"final_test_access_authorized="
            f"{record.get('final_test_access_authorized')}, "
            f"final_test_evaluation_performed="
            f"{record.get('final_test_evaluation_performed')}",
            "- Contract: `project/docs/ai/STAGE128_M2_D2_DESIGN_FREEZE.md`; "
            "machine-readable package: `project/stage128/`",
            "",
        ]
    if record.get("stage128_m2_d2_gate_rerun_executed"):
        rerun_status = record.get("stage128_m2_d2_gate_rerun_status", "")
        admitted = record.get("stage128_m2_d2_block_data_admission_passed")
        rerun_ok = "✅" if admitted else "⛔"
        # Once the authorized successor (the paired M2-vs-M1 incremental
        # evaluation) has itself completed, this Gate becomes historical
        # context and its section must stop being marked (CURRENT) and stop
        # carrying the branch's live next-action pointer.
        rerun_is_historical = bool(
            record.get("stage127_m2_incremental_evaluation_completed"))
        rerun_heading = (
            "## Stage128 — canonical M2 Gate RE-RUN under Gregorian D2 "
            "(COMPLETED DATA-ADMISSION GATE)\n"
            if rerun_is_historical else
            "## Stage128 — canonical M2 Gate RE-RUN under Gregorian D2 "
            "(CURRENT)\n"
        )
        lines += [
            rerun_heading,
            "_The canonical M2 data-admission Gate, re-executed ONCE under "
            "the already-frozen Gregorian D2 equity-return specification, "
            "offline from the same immutable TSETMC bundle. The one-action "
            "human authorization was consumed by this execution. No model was "
            "fit, no prediction generated, no predictive metric computed and "
            "no final-test predictor or target value parsed, inspected or "
            "used._\n",
            f"- {rerun_ok} **Gate re-run status:** `{rerun_status}`",
            "- **Executed:** "
            f"{record['stage128_m2_d2_gate_rerun_executed']} — **resolved "
            f"(terminal observed decision):** "
            f"{record.get('stage128_m2_d2_gate_rerun_resolved')}",
            "- **D2 equity return:** "
            f"{record.get('stage128_m2_d2_equity_return_valid_rows')}/666 = "
            f"{record.get('stage128_m2_d2_equity_return_coverage')} — "
            "**three-variable common sample:** "
            f"{record.get('stage128_m2_d2_common_sample_rows')}/666 = "
            f"{record.get('stage128_m2_d2_common_sample_coverage')}",
            "- ⛔ **Historical Stage127 D0 Gate remains** "
            f"`{record.get('stage127_m2_market_data_gate_status')}` — "
            "preserved unchanged in its own Stage127 artifacts; this re-run "
            "never rewrites it",
            "- **Authorization consumed by this execution:** "
            f"{record.get('stage128_m2_d2_gate_rerun_authorization_consumed')}"
            " — **D2 Gate rerun authorized (standing):** "
            f"{record.get('stage128_m2_d2_gate_rerun_authorized')}",
            "- **This is DATA ADMISSION only.** It does not say M2 improves "
            "prediction. **M2 incremental evaluation authorized:** "
            f"{record.get('m2_incremental_evaluation_authorized')} — "
            "**this Gate fitted no model and started no modeling**; it made "
            "the successor eligible, nothing more. Any live M2 execution or "
            "block-admission marker was set by the later, separately "
            "authorized paired evaluation.",
            # The SOLE live next-action pointer while this Gate is CURRENT.
            (
                "- **Immediate successor of this Gate (historical):** "
                "`stage127-m2-incremental-evaluation` — the paired M2 "
                "incremental evaluation, since AUTHORIZED and COMPLETED (see "
                "the current section below). This line is historical: it is "
                "not the branch's live next-action pointer."
                if rerun_is_historical else
                "- **Next research action (pointer only):** "
                f"`{record['next_research_action_id']}` — scientifically "
                "ELIGIBLE after this data-admission PASS; a POINTER ONLY, "
                "**not authorized** "
                "(`m2_incremental_evaluation_authorized="
                f"{record.get('m2_incremental_evaluation_authorized')}`) and "
                "**not started** "
                f"(`m2_modeling_started={record.get('m2_modeling_started')}`)"
                ". It requires a new, explicit human authorization. It is the "
                "M2 incremental evaluation action — it is NOT the canonical "
                "M2 Gate re-run, which is the completed action reported in "
                "this section."
            ),
            "- The post-lock eligibility audit frozen by the design-freeze "
            "contract remains REQUIRED before any M2 predictive result is "
            "interpreted. It was not executed by this Gate.",
            "- Package: `project/stage128/`; interpretation: "
            "`project/stage128/README_STAGE128_M2_D2_GATE_RERUN.md`",
            "",
        ]
    if record.get("stage127_m2_incremental_evaluation_completed"):
        _eval_heading_suffix = (
            "" if record.get(
                "stage128_m2_retained_block_human_decision_completed")
            else " (CURRENT)"
        )
        lines += [
            "## Stage127 — paired M2 vs M1 incremental evaluation"
            f"{_eval_heading_suffix}\n",
            "_The paired, development-only comparison of the frozen M2 block "
            "against the frozen M1 block on the exact three-variable D2 "
            "common sample, under the locked temporal folds, retained "
            "configurations, frozen metrics and frozen uncertainty procedure. "
            "The one-action human authorization was consumed by this "
            "execution. The frozen streaming loader read only the "
            "row-identity and split fields required to identify and exclude "
            "346 locked-final-test records; it did not parse, inspect, "
            "store, preprocess, fit on, predict from, evaluate, summarize or "
            "export any final-test predictor or target value. Nothing was "
            "retuned and NO winner or retained block was selected._\n",
            "- \u2705 **Executed and completed:** "
            f"{record['stage127_m2_incremental_evaluation_completed']} — "
            "**authorization consumed:** "
            f"{record.get('stage127_m2_incremental_evaluation_authorization_consumed')}",
            "- **Paired common sample:** "
            f"{record.get('stage127_m2_incremental_evaluation_common_sample_rows')}"
            " rows — **pooled locked-validation OOF rows:** "
            f"{record.get('stage127_m2_incremental_evaluation_pooled_oof_rows')}",
            "- **Primary predictive model fits:** "
            f"{record.get('stage127_m2_incremental_evaluation_primary_model_fits')}"
            " (both blocks refitted on identical common-sample training rows)",
            (
                "- \u26d4 **M2 block retained BY THIS ACTION:** false \u2014 it "
                "reports OBSERVED development evidence only and selects no "
                "winner. The retained-block question was answered "
                "separately, by the human decision reported below "
                f"(`m2_block_retained={record.get('m2_block_retained')}`, "
                "`m2_retained_block_decision_required="
                f"{record.get('m2_retained_block_decision_required')}`)"
                if record.get(
                    "stage128_m2_retained_block_human_decision_completed")
                else
                "- \u26d4 **M2 block retained:** "
                f"{record.get('m2_block_retained')} \u2014 this action reports "
                "OBSERVED development evidence only and selects no winner; "
                "a **human retained-block decision is REQUIRED** "
                f"(`m2_retained_block_decision_required="
                f"{record.get('m2_retained_block_decision_required')}`)"
            ),
            "- \u2705 **M2 market data (live):** evidence collected="
            f"{record.get('m2_market_data_evidence_collected')}, validated="
            f"{record.get('m2_market_data_evidence_validated')}, entered the "
            "authorized incremental modeling pipeline="
            f"{record.get('m2_data_entered_authorized_incremental_modeling_pipeline')}"
            ", evaluation data materialized="
            f"{record.get('m2_incremental_evaluation_data_materialized')}. "
            "(The frozen Stage125 Part 4 marker `m2_data_collected` stays "
            "`false` as immutable historical schema state; it is not live "
            "state — see the historical/legacy section below.)",
            "- \u2705 **M2 modeling started (executed):** "
            f"{record.get('m2_modeling_started')} — **M2 block admitted for "
            "modeling:** "
            f"{record.get('m2_block_admitted_for_modeling')}. The authorized "
            "development modeling for this comparison WAS executed.",
            "- \u26d4 **M2 incremental evaluation authorized:** "
            f"{record.get('m2_incremental_evaluation_authorized')} — the "
            "one-action authorization was CONSUMED by this execution and is "
            "not standing. A consumed authorization is `false`; it does "
            "**not** mean the modeling never happened.",
            "- \u26d4 **Historical Stage127 D0 Gate remains** "
            f"`{record.get('stage127_m2_market_data_gate_status')}`; the "
            "terminal Stage128 D2 Gate result "
            f"`{record.get('stage128_m2_d2_gate_rerun_status')}` is preserved "
            "unchanged",
            "- \U0001f512 **Final test locked:** final_test_unlocked="
            f"{record.get('final_test_unlocked')}, "
            f"final_test_access_authorized="
            f"{record.get('final_test_access_authorized')}, "
            f"final_test_evaluation_performed="
            f"{record.get('final_test_evaluation_performed')} — "
            f"**M3 started:** {record.get('m3_started')} — "
            f"**M4 started:** {record.get('m4_started')}",
            (
                "- **Successor to THIS action:** the human retained-block "
                "decision `stage128-m2-retained-block-human-decision`, "
                "now COMPLETE and reported in its own section below."
                if record.get(
                    "stage128_m2_retained_block_human_decision_completed")
                else
                "- **Next research action (pointer only):** "
                f"`{record['next_research_action_id']}` — a human "
                "retained-block review. A pointer is **not** an "
                "authorization."
            ),
            "- Package: `project/stage128/m2_incremental_evaluation/`; "
            "interpretation: `project/stage128/m2_incremental_evaluation/"
            "README_STAGE127_M2_INCREMENTAL_EVALUATION.md`",
            "",
        ]
    if record.get("stage128_m2_retained_block_human_decision_completed"):
        lines += [
            "## Stage128 — M2 retained-block HUMAN decision (CURRENT)\n",
            "_The human governance decision that the paired evaluation "
            "deliberately left open, recorded from already-committed evidence "
            "under its own one-action human authorization. Zero model fits, "
            "zero predictions, zero resampling, zero refits and zero "
            "final-test values read. This is a **retained-block decision, not "
            "a superiority decision**._\n",
            "- ✅ **Decision outcome:** "
            f"`{record.get('stage128_m2_retained_block_human_decision_outcome')}`"
            " — **authorization consumed:** "
            f"{record.get('stage128_m2_retained_block_human_decision_authorization_consumed')}",
            "- ✅ **M2 block retained:** "
            f"{record.get('m2_block_retained')} — as the INTERMEDIATE "
            "block of the preregistered nested chain M1→M2→M3→M4 "
            "and the comparator for a future paired `M3 − M2` evaluation, "
            "conditional on a separately authorized M3 data Gate that passes",
            "- **Retention basis:** "
            f"`{record.get('stage128_m2_retention_basis')}`",
            "- ⛔ **M2 predictive superiority claim supported:** "
            f"{record.get('m2_predictive_superiority_claim_supported')} — "
            "the observed development evidence stays approximately null (all "
            "three 95% paired-bootstrap PR-AUC intervals include zero and the "
            "point-estimate signs disagree across model families). Retention "
            "implies no predictive improvement and no statistical "
            "significance.",
            "- ⛔ **No winner, no final model:** paper_winner_selected="
            f"{record.get('paper_winner_selected')}, final_model_selected="
            f"{record.get('final_model_selected')}, "
            "full_development_refit_performed="
            f"{record.get('full_development_refit_performed')}",
            "- ⛔ **Holm family:** complete="
            f"{record.get('holm_family_complete')}, final adjustment "
            f"deferred={record.get('holm_final_adjustment_deferred')} — "
            "the incomplete confirmatory family stays incomplete",
            "- 🔒 **Final test locked:** final_test_unlocked="
            f"{record.get('final_test_unlocked')}, "
            "final_test_access_authorized="
            f"{record.get('final_test_access_authorized')}, "
            "predictor values inspected="
            f"{record.get('final_test_predictor_values_inspected')}, "
            "target values inspected="
            f"{record.get('final_test_target_values_inspected')}",
            "- ⛔ **M3:** authorized="
            f"{record.get('m3_authorized')}, started={record.get('m3_started')}"
            " — **M4:** authorized="
            f"{record.get('m4_authorized')}, started={record.get('m4_started')}",
            (
                # The live pointer moved on: it is rendered once, by the
                # newest completed action's own section below. Here it is
                # recorded only as the historical pointer this decision
                # published.
                "- **Pointer published by this decision (historical):** "
                "`stage128-m3-macro-data-gate` — the M3 macro data Gate, "
                "which has since been EXECUTED as a data-admission Gate only "
                "(see the M3 section below). A pointer was **not** an "
                "authorization, and the Gate execution started no modeling: "
                "`m3_modeling_started=False`, "
                "`m3_incremental_evaluation_authorized=False`."
                if record.get("stage128_m3i2_contract_lock_executed")
                else
                "- **Next research action (pointer only):** "
                f"`{record['next_research_action_id']}` — the M3 macro data "
                "Gate, which has since been EXECUTED as a data-admission Gate "
                "only (see the M3 section below). A pointer is **not** an "
                "authorization, and the Gate execution started no modeling: "
                "`m3_modeling_started=False`, "
                "`m3_incremental_evaluation_authorized=False`."
                if record.get("stage128_m3_macro_data_gate_executed")
                else
                "- **Next research action (pointer only):** "
                f"`{record['next_research_action_id']}` — the M3 macro data "
                "Gate. A pointer is **not** an authorization: no macro data "
                "was collected, no M3 variable created, no M3 Gate executed "
                "and no M3 model fit."
            ),
            "- Package: "
            "`project/stage128/m2_retained_block_human_decision/`; "
            "interpretation: "
            "`project/stage128/m2_retained_block_human_decision/"
            "README_STAGE128_M2_RETAINED_BLOCK_HUMAN_DECISION.md`",
            "",
        ]
    if record.get("stage128_m3_macro_data_gate_executed"):
        m3_status = record.get("stage128_m3_macro_data_gate_status")
        m3_passed = m3_status == "PASS_FOR_M3_INCREMENTAL_EVALUATION"
        m3_mark = "\u2705" if m3_passed else "\u26d4"
        lines += [
            "### Stage128 — M3 macro DATA Gate (data admission only)\n",
            "_The data-admission Gate for the exact frozen three-variable M3 "
            "macro block (`cpi_inflation`, `fx_change_official`, "
            "`policy_financing_rate`). It asks only whether that block can be "
            "obtained from authoritative, reproducible, point-in-time-safe "
            "sources. It does NOT ask, and does not answer, whether M3 "
            "improves prediction._\n",
            f"- {m3_mark} **Gate status:** `{m3_status}`",
            "- \u2705 **Executed:** True — **authorization consumed:** "
            f"{record.get('stage128_m3_macro_data_gate_authorization_consumed')}"
            " (one action only, not standing)",
            "- \u26d4 **Zero modeling in the Gate:** 0 model fits, 0 "
            "predictions, 0 predictive metrics, 0 M3-versus-M2 comparisons, 0 "
            "bootstrap/Holm/SHAP/SMOTE executions",
            "- **Gate denominator:** the retained-M2 development common "
            f"sample, {record.get('m3_macro_data_gate_parent_rows')} rows — "
            "**not** the 666-row M1 development universe",
            "- \u26d4 **M3 block admitted for incremental evaluation:** "
            f"{record.get('m3_block_admitted_for_incremental_evaluation')}"
            + ("" if m3_passed else
               " — no partial block was admitted and no candidate was dropped "
               "or substituted"),
            "- \u26d4 **M3 incremental evaluation authorized:** "
            f"{record.get('m3_incremental_evaluation_authorized')} — **M3 "
            f"modeling started:** {record.get('m3_modeling_started')}. The "
            "data workstream started; the MODELING did not.",
            "- \u26d4 **M4:** authorized="
            f"{record.get('m4_authorized')}, started="
            f"{record.get('m4_started')} — **final test locked:** "
            f"{record.get('final_test_locked')}",
        ]
        if m3_passed:
            lines.append(
                "- **Next research action (pointer only):** "
                f"`{record.get('next_research_action_id')}`. A PASS is **data "
                "admission only** — it does not mean M3 improves prediction, "
                "and a pointer is **not** an authorization.")
        else:
            lines.append(
                "- \u26d4 **Research pointer NOT advanced** — "
                "`m3_macro_data_gate_human_review_required` = "
                f"{record.get('m3_macro_data_gate_human_review_required')}; "
                f"{record.get('m3_macro_data_gate_unresolved_reason_count')} "
                "recorded blocker/unresolved reasons. Missing evidence was "
                "recorded as null, never scored as zero, and never converted "
                "into an observed failure.")
        lines += [
            "- Package: `project/stage128/m3_macro_data_gate/`; "
            "interpretation: `project/stage128/m3_macro_data_gate/"
            "README_STAGE128_M3_MACRO_DATA_GATE.md`",
            "",
        ]
    if record.get("stage128_m3i2_contract_lock_executed"):
        lines += [
            "### Stage128 — M3I-2 prospective contract lock "
            "(HISTORICAL, contract-time)\n",
            "_A metadata-only, PROSPECTIVE source/definition/statistical "
            "contract lock for the SUPPLEMENTARY international-macro block "
            "M3I-2 (`intl_cpi_inflation_annual`, "
            "`intl_fx_change_official_annual`), plus a contingent, UNRESOLVED "
            "M3I-3 financing shell. It is not a substitution, correction or "
            "continuation of the frozen M3-CBI block, and it is never "
            "confirmatory M3._\n",
            "> **This section describes CONTRACT-TIME state and is retained "
            "as history.** Every retrieval/PR-topology statement below was "
            "true at the moment of the contract lock. The retrieval and "
            "PR-topology facts were later superseded by the independent "
            "action `stage128-m3i2-official-source-evidence-capture` "
            "(see the evidence-capture section below). The **scientific "
            "contract itself is unchanged** — it remains "
            "`PROSPECTIVELY_LOCKED_NO_DATA`, unadmitted and ungated.\n",
            "- ✅ **Contract status:** "
            f"`{record.get('stage128_m3i2_contract_status')}` — "
            "authorization consumed: "
            f"{record.get('stage128_m3i2_contract_lock_authorization_consumed')}"
            " (one action only, not standing)",
            "- ⛔ **No data, no Gate, no modeling:** 0 network requests, "
            "0 macro observations read, 0 company rows loaded, 0 coverage "
            "calculations, 0 model fits, 0 predictions, 0 Holm calculations",
            "- ⛔ **At contract-lock time — M3I-2 retrieval started:** "
            f"{record.get('m3i2_retrieval_started')} "
            f"(`{record.get('m3i2_retrieval_started_semantics')}` — the "
            "contract-time marker is retained for compatibility; official-"
            "source evidence WAS captured later under a separate action, see "
            "`stage128_m3i2_official_source_retrieval_completed`) — "
            "**Data Gate executed:** "
            f"{record.get('m3i2_data_gate_executed')} — **block admitted:** "
            f"{record.get('m3i2_block_admitted')} — **modeling started:** "
            f"{record.get('m3i2_modeling_started')}",
            "- ⛔ **M3I-3 financing metadata lock:** "
            f"`{record.get('m3i3_financing_lock')}` — **admitted:** "
            f"{record.get('m3i3_admitted')}",
            "- **M3-CBI preserved unchanged:** Gate status "
            f"`{record.get('m3_macro_data_gate_status')}`, block admitted "
            f"{record.get('m3_block_admitted_for_incremental_evaluation')}",
            "- **Scientific provenance baseline:** PR #"
            f"{record.get('stage128_m3i2_baseline_pr_number')} head "
            f"`{record.get('stage128_m3i2_baseline_commit')}` — protected "
            "hashes are verified against that commit permanently; a merge or "
            "retarget never moves it",
            "- **PR topology at contract-lock time (HISTORICAL, not live):** "
            "PR #73 **was merged** by merge commit "
            f"`{record.get('stage128_m3i2_predecessor_pr_merge_commit')}`; "
            f"PR #{record.get('stage128_m3i2_contract_time_pr_number')} was "
            "subsequently retargeted to "
            f"`{record.get('stage128_m3i2_contract_time_pr_base_branch')}` "
            f"(base `{record.get('stage128_m3i2_contract_time_pr_base_commit')}`"
            ") and never merged under this action — merged = "
            f"{record.get('stage128_m3i2_contract_time_pr_merged')}, no merge "
            "authorization. Semantics: "
            f"`{record.get('stage128_m3i2_contract_time_pr_semantics')}`. "
            f"PR #{record.get('stage128_m3i2_contract_time_pr_number')} is the "
            "**historical contract-lock PR**, never the current draft; the "
            "live Draft PR is identified in the live-action section below.",
            "- **Next research action (pointer only):** "
            f"`{record.get('next_research_action_id')}` — it is **not "
            "authorized** and a pointer is **not** an authorization "
            "(`next_research_action_authorized` = "
            f"{record.get('next_research_action_authorized')}).",
            "- Package: `project/stage128/m3_intl_macro_contract_lock/`; "
            "interpretation: `project/stage128/m3_intl_macro_contract_lock/"
            "README_STAGE128_M3_INTL_MACRO_CONTRACT_LOCK.md`",
            "",
        ]
    if record.get("stage128_m3i2_evidence_capture_executed"):
        lines += [
            "### Stage128 — M3I-2 official-source evidence capture\n",
            "_The action that supersedes the contract-time \"no retrieval\" "
            "statements above. It is ACQUISITION ONLY: official bytes were "
            "requested, retained and hashed. Every count below is an "
            "input-integrity count and **never coverage**. Capture is not "
            "admission — it answers nothing about coverage, the Data Gate or "
            "modeling._\n",
            # Once the final documentary recovery is initiated, THIS action is
            # no longer the live one: it keeps its own action id and its own
            # (now merged) PR, and the live PR topology moves to the recovery
            # section below. A merged predecessor is never the live Draft.
            ("- ✅ **Evidence capture executed:** True — action "
             f"`{_STAGE128_M3I2_EVIDENCE_ACTION_ID}`, carried by "
             "**PR #"
             f"{record.get('stage128_m3i2_evidence_capture_pr_number', 'n/a')}"
             "** (the MERGED predecessor PR, no longer the live Draft)"
             if record.get(
                 "stage128_m3i2_final_documentary_recovery_initiated")
             else
             "- ✅ **Evidence capture executed:** True — action "
             f"`{record.get('last_completed_research_action_id')}`, carried by "
             "**PR #"
             f"{record.get('stage128_m3i2_live_pr_number', 'n/a')}** "
             "(the LIVE evidence-capture PR)"),
            "- ✅ **Official-source retrieval completed:** "
            f"{record.get('stage128_m3i2_official_source_retrieval_completed')}"
            " — this is acquisition only and is **not** a Data Gate, **not** "
            "coverage and **not** an admission",
            ("- **PR topology at capture time (HISTORICAL, not live):** PR #"
             f"{record.get('stage128_m3i2_evidence_capture_pr_number')} "
             "**was merged** by merge commit "
             f"`{record.get('stage128_m3i2_evidence_capture_pr_merge_commit')}`"
             f" — semantics: "
             f"`{record.get('stage128_m3i2_evidence_capture_pr_semantics')}`. "
             "The LIVE Draft PR is **PR #"
             f"{record.get('stage128_m3i2_live_pr_number')}**, identified in "
             "full below."
             if record.get(
                 "stage128_m3i2_final_documentary_recovery_initiated")
             else
             "- **Live PR topology:** PR #"
             f"{record.get('stage128_m3i2_live_pr_number')} → base "
             f"`{record.get('stage128_m3i2_live_pr_base_branch')}` @ "
             f"`{record.get('stage128_m3i2_live_pr_base_commit')}` — draft = "
             f"{record.get('stage128_m3i2_live_pr_is_draft')}, merged = "
             f"{record.get('stage128_m3i2_live_pr_merged')}, head derived from "
             f"`{record.get('stage128_m3i2_live_pr_head_commit_source')}` "
             "(never pinned)"),
            "- **Official traffic:** "
            f"{record.get('stage128_m3i2_official_requests_attempted')} "
            "requests — "
            f"{record.get('stage128_m3i2_official_responses_successful')} "
            "successful responses — "
            f"{record.get('stage128_m3i2_official_responses_retained')} "
            "responses retained — raw bytes retained "
            f"{record.get('stage128_m3i2_raw_bytes_retained'):,}",
            "- **Archive editions:** "
            f"{record.get('stage128_m3i2_archive_editions_captured')} captured "
            "and held out of "
            f"{record.get('stage128_m3i2_wdi_editions_discovered')} "
            "discovered — verified required editions "
            f"{record.get('stage128_m3i2_required_editions_captured')} of "
            f"{record.get('stage128_m3i2_required_editions_total')} — "
            "verified release dates "
            f"{record.get('stage128_m3i2_editions_with_verified_release_date')}"
            f" of {record.get('stage128_m3i2_wdi_editions_discovered')}",
            "- ⛔ **Unresolved:** cutoffs "
            f"{record.get('stage128_m3i2_cutoffs_without_verified_pre_cutoff_edition')}"
            f" of {record.get('stage128_m3i2_unique_development_cutoffs')} — "
            "development pairs "
            f"{record.get('stage128_m3i2_development_pairs_without_verified_pre_cutoff_edition')}"
            f" of {record.get('stage128_m3i2_development_pairs_behind_cutoff_plan')}",
            "- **Semantic compatibility:** CPI "
            f"{record.get('stage128_m3i2_cpi_semantic_pass_count')} PASS — FX "
            f"{record.get('stage128_m3i2_fx_semantic_unresolved_count')} "
            "UNRESOLVED",
            "- ⛔ **Evidence status:** "
            f"`{record.get('stage128_m3i2_evidence_status')}` — result code "
            f"`{record.get('stage128_m3i2_evidence_result_code')}`",
            "- ⛔ **Data Gate:** NOT_EXECUTED (`m3i2_data_gate_executed` = "
            f"{record.get('m3i2_data_gate_executed')}) — **M3I-2 admitted:** "
            f"{record.get('m3i2_block_admitted')} — **modeling started:** "
            f"{record.get('m3i2_modeling_started')} — **Final Test locked:** "
            f"{record.get('final_test_locked')} — **M4 authorized:** "
            f"{record.get('m4_authorized')} — **merge authorized:** "
            f"{record.get('stage128_m3i2_merge_authorized')}",
            "- Package: `project/stage128/"
            "m3i2_official_source_evidence_capture/`; interpretation: "
            "`project/stage128/m3i2_official_source_evidence_capture/"
            "README_STAGE128_M3I2_OFFICIAL_SOURCE_EVIDENCE_CAPTURE.md`",
            "",
        ]
    if record.get("stage128_m3i2_independent_audit_completed"):
        lines += [
            "### Stage128 — M3I-2 independent bundle integrity audit "
            "(integrity only)\n",
            "_A post-capture, read-only audit of the external evidence "
            "bundle by an auditor independent of the PR author and of the "
            "bundle creator. Its scope is bytes, not science: SHA-256, ZIP "
            "CRC, multipart structure, manifest consistency, official-source "
            "restrictions and raw-member integrity. It is **not** coverage, "
            "**not** the Data Gate, **not** an M3I-2 admission, **not** "
            "modeling and **not** Final Test access._\n",
            "- ✅ **Result:** "
            f"`{record.get('stage128_m3i2_independent_bundle_integrity_audit')}`"
            " — verification type "
            f"`{record.get('stage128_m3i2_independent_bundle_audit_verification_type')}`",
            "- ✅ **Independence:** independent of PR author = "
            f"{record.get('stage128_m3i2_auditor_independent_from_pr_author')}"
            " — independent of bundle creator = "
            f"{record.get('stage128_m3i2_auditor_independent_from_bundle_creator')}"
            " — participated in artifact creation = "
            f"{record.get('stage128_m3i2_auditor_participated_in_artifact_creation')}"
            " — identity disclosure: "
            f"`{record.get('stage128_m3i2_auditor_identity_disclosure_status')}`",
            "- **Audited object:** PR #"
            f"{record.get('stage128_m3i2_audited_pr_number')} head "
            f"`{record.get('stage128_m3i2_audited_pr_head_sha')}` — primary "
            "members expected/found "
            f"{record.get('stage128_m3i2_audit_primary_members_expected')}/"
            f"{record.get('stage128_m3i2_audit_primary_members_found')}",
            "- **Capture-time provenance retained:** the bundle manifest "
            "still records `delivered_to_independent_auditor` = False and "
            "`independently_verified_by_auditor` = False. Those were true of "
            "the moment the bundle was built, are kept unmodified, and are "
            "**superseded — not corrected** — by the post-capture audit "
            "record.",
            "- ⛔ **Nothing scientific moved:** M3I-2 evidence status "
            f"`{record.get('stage128_m3i2_evidence_status')}` — admitted "
            f"{record.get('m3i2_block_admitted')} — Data Gate executed "
            f"{record.get('m3i2_data_gate_executed')} — modeling started "
            f"{record.get('m3i2_modeling_started')} — Final Test locked "
            f"{record.get('final_test_locked')} — M4 authorized "
            f"{record.get('m4_authorized')} — merge authorized "
            f"{record.get('stage128_m3i2_merge_authorized')}",
            "- ⛔ A passing integrity audit does **not** resolve the "
            "historical-vintage evidence problem and does **not** admit "
            "M3I-2.",
            "- Attestation: `project/stage128/"
            "m3i2_official_source_evidence_capture/"
            "stage128_m3i2_independent_bundle_integrity_audit_attestation.md`",
            "",
        ]
    if record.get("stage128_m3i2_final_documentary_recovery_initiated"):
        submission_recorded = bool(
            record.get("stage128_m3i2_inquiry_human_submission_recorded"))
        # Once the Track B contract-lock PR is itself merged it stops being
        # the live Draft and joins the pinned historical roles. Rendered only
        # when that merge is actually recorded, so the line never asserts a
        # merge that has not happened.
        contract_lock_pr_clause = ""
        if record.get("stage128_m3_lag_wdi_contract_lock_pr_merged") is True:
            contract_lock_pr_clause = (
                "PR #"
                f"{record.get('stage128_m3_lag_wdi_contract_lock_pr_number')}"
                " = "
                f"`{record.get('stage128_m3_lag_wdi_contract_lock_pr_role')}`"
                " (action "
                f"`{record.get('stage128_m3_lag_wdi_contract_lock_pr_action_id')}`)"
                " — merged = "
                f"{record.get('stage128_m3_lag_wdi_contract_lock_pr_merged')}"
                " by merge commit "
                f"`{record.get('stage128_m3_lag_wdi_contract_lock_pr_merge_commit')}`"
                " — semantics "
                f"`{record.get('stage128_m3_lag_wdi_contract_lock_pr_semantics')}`. "
            )
        lines += [
            "### Stage128 — M3I-2 final official documentary recovery "
            "(INITIATION ONLY)\n",
            ("_A COMPLETED predecessor action, superseded by the human "
             "submission recorded below. A bounded search of OFFICIAL World "
             "Bank Group sources for the two remaining M3I-2 blockers, plus "
             "preparation of exactly ONE official Data Help Desk inquiry. "
             "Acquiring DOCUMENTS is not admitting DATA: it answers nothing "
             "about coverage, the Data Gate or modeling._\n"
             if submission_recorded else
             "_The LIVE action. A bounded search of OFFICIAL World Bank Group "
             "sources for the two remaining M3I-2 blockers, plus preparation "
             "of exactly ONE official Data Help Desk inquiry. Acquiring "
             "DOCUMENTS is not admitting DATA: it answers nothing about "
             "coverage, the Data Gate or modeling._\n"),
            # Once the human submission is recorded, the PR that carried this
            # initiation has itself been MERGED. It is history from that point
            # on and must never be rendered as the live Draft.
            ("- ✅ **Initiated:** True — action "
             "`stage128-m3i2-final-official-documentary-recovery-initiation`, "
             "carried by **PR #"
             f"{record.get('stage128_m3i2_recovery_pr_number')}**, which "
             "**was merged** by merge commit "
             f"`{record.get('stage128_m3i2_recovery_pr_merge_commit')}` — it "
             "is the MERGED predecessor, no longer the live Draft PR"
             if submission_recorded else
             "- ✅ **Initiated:** True — action "
             f"`{record.get('last_completed_research_action_id')}`, carried by "
             f"**PR #{record.get('stage128_m3i2_live_pr_number')}** (the LIVE "
             "Draft PR) on base "
             f"`{record.get('stage128_m3i2_live_pr_base_branch')}` @ "
             f"`{record.get('stage128_m3i2_live_pr_base_commit')}`"),
            ("- **PR topology at recovery time (HISTORICAL, not live):** PR #"
             f"{record.get('stage128_m3i2_recovery_pr_number')} **was merged** "
             f"— semantics: "
             f"`{record.get('stage128_m3i2_recovery_pr_semantics')}`. The LIVE "
             "Draft PR is identified in the human-submission section below."
             if submission_recorded else
             "- **Live PR topology:** PR #"
             f"{record.get('stage128_m3i2_live_pr_number')} → base "
             f"`{record.get('stage128_m3i2_live_pr_base_branch')}` @ "
             f"`{record.get('stage128_m3i2_live_pr_base_commit')}` — draft = "
             f"{record.get('stage128_m3i2_live_pr_is_draft')}, merged = "
             f"{record.get('stage128_m3i2_live_pr_merged')}, head derived from "
             f"`{record.get('stage128_m3i2_live_pr_head_commit_source')}` "
             "(never pinned)"),
            "- **Merged predecessor:** PR #"
            f"{record.get('stage128_m3i2_evidence_capture_pr_number')} "
            "(official-source evidence capture) — merged = "
            f"{record.get('stage128_m3i2_evidence_capture_pr_merged')}, merge "
            "commit "
            f"`{record.get('stage128_m3i2_evidence_capture_pr_merge_commit')}`",
            "- **Bounded search:** "
            f"{record.get('stage128_m3i2_documentary_get_requests')} of a "
            "maximum "
            f"{record.get('stage128_m3i2_documentary_get_requests_max')} "
            "official documentary GET requests — archive ZIP downloads "
            f"{record.get('stage128_m3i2_archive_zip_downloads')}, "
            "redownloads "
            f"{record.get('stage128_m3i2_archive_zip_redownloads')}, prior "
            "capture repeated "
            f"{record.get('stage128_m3i2_prior_capture_repeated')}",
            "- ⛔ **Outcome:** "
            f"`{record.get('stage128_m3i2_bounded_search_outcome')}` — "
            "blocker 1 (archive release availability) resolved "
            f"{record.get('stage128_m3i2_blocker_1_archive_release_resolved')}"
            " — blocker 2 (FX semantic continuity) resolved "
            f"{record.get('stage128_m3i2_blocker_2_fx_semantic_resolved')}",
            "- ⛔ **Release-date discipline unchanged:** filename token is "
            "release evidence = "
            f"{record.get('stage128_m3i2_filename_token_is_release_evidence')}"
            " — unproven previous-month fallback used = "
            f"{record.get('stage128_m3i2_unproven_previous_month_fallback_used')}"
            " — official-month → first day of the NEXT month rule locked = "
            f"{record.get('stage128_m3i2_official_month_only_next_month_rule_locked')}",
            "- **Official inquiry:** status "
            f"`{record.get('stage128_m3i2_inquiry_submission_status')}` — "
            "initial attempts "
            f"{record.get('stage128_m3i2_inquiry_initial_attempts')} / "
            "submitted "
            f"{record.get('stage128_m3i2_inquiry_initial_submitted')} (maximum "
            "1) — body SHA-256 "
            f"`{record.get('stage128_m3i2_inquiry_body_sha256')}` — ticket id "
            f"{record.get('stage128_m3i2_inquiry_ticket_id_redacted')} (none "
            "invented) — PII committed to Git = "
            f"{record.get('stage128_m3i2_inquiry_pii_committed_to_git')}",
            "- **Human submission:** submitted by the human supervisor = "
            f"{record.get('stage128_m3i2_inquiry_human_authenticated_submission')}"
            " — displayed timestamp "
            f"`{record.get('stage128_m3i2_inquiry_submission_timestamp_displayed')}`"
            " (calendar date "
            f"`{record.get('stage128_m3i2_inquiry_submission_calendar_date')}`)"
            " — UTC instant "
            f"`{record.get('stage128_m3i2_inquiry_submission_timestamp_utc_status')}`"
            ", never guessed — acknowledgement received = "
            f"{record.get('stage128_m3i2_inquiry_acknowledgement_received')}, "
            "substantive response received = "
            f"{record.get('stage128_m3i2_inquiry_substantive_response_received')}"
            " — ticket id present = "
            f"{record.get('stage128_m3i2_inquiry_ticket_id_present')}, "
            "fabricated = "
            f"{record.get('stage128_m3i2_inquiry_ticket_id_fabricated')} — "
            "raw confirmation kept outside Git, SHA-256 "
            f"`{record.get('stage128_m3i2_inquiry_external_raw_confirmation_sha256')}`"
            " — body evidence "
            f"`{record.get('stage128_m3i2_inquiry_body_submission_evidence_status')}`"
            ", attachments server-enumerated = "
            f"{record.get('stage128_m3i2_inquiry_attachments_server_enumerated')}",
            "- **Stopping rule:** waiting period "
            f"{record.get('stage128_m3i2_inquiry_waiting_period_business_days')}"
            " business days — status "
            f"`{record.get('stage128_m3i2_inquiry_waiting_period_status')}` "
            "through "
            f"`{record.get('stage128_m3i2_inquiry_waiting_period_completion_date')}`"
            " — earliest possible follow-up "
            f"`{record.get('stage128_m3i2_inquiry_follow_up_earliest_calendar_date')}`"
            " — follow-ups attempted "
            f"{record.get('stage128_m3i2_inquiry_follow_up_attempted')} — "
            "follow-up authorized now = "
            f"{record.get('stage128_m3i2_inquiry_follow_up_authorized_now')} — "
            "response adjudication authorized = "
            f"{record.get('stage128_m3i2_response_adjudication_authorized')}"
            + (
                " — **superseded "
                f"{record.get('stage128_track_a_waiting_termination_date')}"
                " by explicit human decision to voluntarily terminate the "
                "waiting period early; see the Track A section below for "
                "current status**"
                if record.get(
                    "stage128_track_a_waiting_termination_recorded")
                else ""
            ),
            "- **LIVE PR topology:** the LIVE Draft PR is **PR #"
            f"{record.get('stage128_m3i2_live_pr_number')}** "
            f"(`{record.get('stage128_m3i2_live_pr_role')}`) → base "
            f"`{record.get('stage128_m3i2_live_pr_base_branch')}` @ "
            f"`{record.get('stage128_m3i2_live_pr_base_commit')}` — draft = "
            f"{record.get('stage128_m3i2_live_pr_is_draft')}, merged = "
            f"{record.get('stage128_m3i2_live_pr_merged')}, ready-for-review "
            "authorized = "
            f"{record.get('stage128_m3i2_live_pr_ready_for_review_authorized')}"
            ", merge authorized = "
            f"{record.get('stage128_m3i2_merge_authorized')}. The head shown "
            "for it is a GENERATION ANCHOR "
            f"(`{record.get('stage128_m3i2_live_pr_head_commit_source')}`), "
            "never pinned and **not** the instantaneous GitHub PR head",
            # Each historical PR keeps its OWN role. "The recovery PR" is PR
            # #76 forever; it never slides forward to mean whatever merged
            # most recently.
            "- **HISTORICAL PR roles (pinned, never re-derived):** PR #"
            f"{record.get('stage128_m3i2_recovery_pr_number')} = "
            f"`{record.get('stage128_m3i2_recovery_pr_role')}` (action "
            f"`{record.get('stage128_m3i2_recovery_pr_action_id')}`) — merged "
            f"= {record.get('stage128_m3i2_recovery_pr_merged')} by merge "
            f"commit `{record.get('stage128_m3i2_recovery_pr_merge_commit')}`"
            " — semantics "
            f"`{record.get('stage128_m3i2_recovery_pr_semantics')}`. PR #"
            f"{record.get('stage128_m3i2_human_submission_pr_number')} = "
            f"`{record.get('stage128_m3i2_human_submission_pr_role')}` "
            "(action "
            f"`{record.get('stage128_m3i2_human_submission_pr_action_id')}`) "
            "— merged = "
            f"{record.get('stage128_m3i2_human_submission_pr_merged')} by "
            "merge commit "
            f"`{record.get('stage128_m3i2_human_submission_pr_merge_commit')}`"
            " — semantics "
            f"`{record.get('stage128_m3i2_human_submission_pr_semantics')}`. "
            f"{contract_lock_pr_clause}"
            "PR #"
            f"{record.get('stage128_m3i2_live_pr_number')} = "
            f"`{record.get('stage128_m3i2_live_pr_role')}`, the current LIVE "
            "Draft. Roles are historical facts, not positions "
            f"({record.get('stage128_m3i2_pr_roles_are_historical_facts_not_positional')})",
            "- ⛔ **M3-LAG-WDI-EXPLORATORY:** authoritative contract status "
            f"`{record.get('stage128_m3_lag_wdi_authoritative_contract_status')}`"
            " — the earlier local, uncommitted partial draft was detected "
            f"({record.get('stage128_m3_lag_wdi_local_partial_draft_detected')})"
            " and quarantined outside the repository "
            f"({record.get('stage128_m3_lag_wdi_local_partial_draft_quarantined')})"
            "; it is not authoritative "
            f"({record.get('stage128_m3_lag_wdi_local_partial_draft_authoritative')})"
            ", its authorization is not reusable "
            f"({record.get('stage128_m3_lag_wdi_prior_authorization_reusable')})"
            ", retrieval started = "
            f"{record.get('stage128_m3_lag_wdi_data_retrieval_started')}",
            "- ⛔ **Nothing scientific moved:** M3I-2 evidence status "
            f"`{record.get('stage128_m3i2_evidence_status')}` — admitted "
            f"{record.get('m3i2_block_admitted')} — Data Gate executed "
            f"{record.get('m3i2_data_gate_executed')} — modeling started "
            f"{record.get('m3i2_modeling_started')} — Final Test locked "
            f"{record.get('final_test_locked')} — M4 authorized "
            f"{record.get('m4_authorized')} — merge authorized "
            f"{record.get('stage128_m3i2_merge_authorized')}",
            "- Package: `project/stage128/"
            "m3i2_final_official_documentary_recovery/`; interpretation: "
            "`project/stage128/m3i2_final_official_documentary_recovery/"
            "README_STAGE128_M3I2_FINAL_OFFICIAL_DOCUMENTARY_RECOVERY.md`",
            "",
        ]
    if record.get("full_suite_baseline_comparison_completed"):
        lines += [
            "### Stage128 — M3I-2 full-suite baseline comparison "
            "(VERIFICATION ONLY)\n",
            "_A test-evidence record, not a scientific one. It states only "
            "that the same suite was run on the baseline and on the candidate "
            "correction head in the same environment. It admits nothing, "
            "moves no pointer and resolves no evidence question._\n",
            "- ✅ **Comparison completed:** True — result "
            f"`{record.get('full_suite_comparison_result')}` — **new failures "
            f"{record.get('full_suite_new_failures')}**",
            "- **Baseline** `"
            f"{record.get('full_suite_baseline_sha')}`: "
            f"{record.get('full_suite_baseline_passed')} passed / "
            f"{record.get('full_suite_baseline_failed')} failed — "
            "**candidate correction head** `"
            f"{record.get('full_suite_candidate_correction_head')}`: "
            f"{record.get('full_suite_candidate_passed')} passed / "
            f"{record.get('full_suite_candidate_failed')} failed",
            "- **Pre-existing failures carried by both:** "
            f"{record.get('full_suite_preexisting_failures')} — they are not "
            "introduced by this PR and no test was deleted or weakened to "
            "hide one",
            "- ⛔ **Not science:** verification-only = "
            f"{record.get('full_suite_comparison_is_verification_not_science')}"
            " — the record never claims to have tested the commit that "
            "carries it (self-reference avoided = "
            f"{record.get('full_suite_comparison_self_reference_avoided')})",
            "- Record: `project/stage128/"
            "m3i2_final_official_documentary_recovery/"
            "stage128_m3i2_full_suite_baseline_comparison.json`",
            "",
        ]
    if record.get("stage128_m3_lag_wdi_exploratory_contract_locked"):
        # Historical vs standing retrieval authorization, kept separate so a
        # consumed one-time authorization can never render as a live one.
        # Before the retrieval both fall back to the generic (standing)
        # field, which is False until a new authorization is granted.
        _rtrv_generic = record.get("stage128_m3_lag_wdi_retrieval_authorized")
        _rtrv_was = record.get(
            "stage128_m3_lag_wdi_retrieval_was_authorized", _rtrv_generic)
        _rtrv_now = record.get(
            "stage128_m3_lag_wdi_retrieval_authorized_now", _rtrv_generic)
        _rtrv_consumed = record.get(
            "stage128_m3_lag_wdi_retrieval_authorization_consumed", False)
        _rtrv_reusable = record.get(
            "stage128_m3_lag_wdi_retrieval_authorization_reusable", False)
        _rtrv_new_auth = record.get(
            "stage128_m3_lag_wdi_further_retrieval_requires_new_human_"
            "authorization", True)
        # Durable custody of the retained raw bytes, rendered only once it is
        # real. Before the deposit existed this stayed absent rather than
        # showing a promise the repository could not keep.
        _custody_lines = []
        if record.get("stage128_m3_lag_wdi_raw_evidence_durably_resolvable"):
            _cst = record.get(
                "stage128_m3_lag_wdi_raw_retention_custody_class")
            _bundle = record.get(
                "stage128_m3_lag_wdi_raw_retention_bundle_id")
            _vdoi = record.get(
                "stage128_m3_lag_wdi_raw_retention_version_doi")
            _cdoi = record.get(
                "stage128_m3_lag_wdi_raw_retention_concept_doi")
            _rec_url = record.get(
                "stage128_m3_lag_wdi_raw_retention_record_url")
            _dep_n = record.get(
                "stage128_m3_lag_wdi_raw_retention_deposited_artifact_count")
            _needs_wb = record.get(
                "stage128_m3_lag_wdi_raw_evidence_recovery_requires_new_"
                "world_bank_request")
            _needs_fs = record.get(
                "stage128_m3_lag_wdi_raw_evidence_depends_on_developer_"
                "filesystem")
            _custody_lines = [
                "- ✅ **Raw-evidence custody is durably resolvable:** the "
                f"retained bundle `{_bundle}` is deposited in `{_cst}` — "
                f"version DOI (immutable) `{_vdoi}`, concept DOI `{_cdoi}`, "
                f"record {_rec_url} — {_dep_n} artifacts deposited. Recovery "
                f"requires a new World Bank request = {_needs_wb}; depends on "
                f"a developer filesystem = {_needs_fs}. The DOI LOCATES; "
                "identity remains the committed filename + byte count + "
                "SHA-256",
            ]
        # Step C. Rendered with its findings attached: a published "PASS" that
        # hid the limitations would be the whole failure mode this section
        # exists to prevent.
        _audit_lines = []
        if record.get("stage128_m3_lag_wdi_post_retrieval_audit_executed"):
            _a_result = record.get(
                "stage128_m3_lag_wdi_post_retrieval_audit_result")
            _a_obs = record.get("stage128_m3_lag_wdi_wdi_observations_read")
            _a_first = record.get(
                "stage128_m3_lag_wdi_both_features_predictor_year_first")
            _a_last = record.get(
                "stage128_m3_lag_wdi_both_features_predictor_year_last")
            _a_bind = record.get(
                "stage128_m3_lag_wdi_binding_constraint_indicator")
            _a_zero = record.get(
                "stage128_m3_lag_wdi_fx_trailing_zero_change_predictor_years")
            _a_lims = record.get(
                "stage128_m3_lag_wdi_post_retrieval_audit_material_"
                "limitations") or []
            _audit_lines = [
                "- ✅ **Step C post-retrieval audit EXECUTED** — result "
                f"`{_a_result}`; {_a_obs} WDI observations read (the first "
                "authorized decode). Audited evidence modified = "
                f"{record.get('stage128_m3_lag_wdi_audited_evidence_modified')}"
                ". Its one-time authorization is consumed = "
                f"{record.get('stage128_m3_lag_wdi_post_retrieval_audit_authorization_consumed')}"
                ", reusable = "
                f"{record.get('stage128_m3_lag_wdi_post_retrieval_audit_authorization_reusable')}"
                ", authorized NOW (standing) = "
                f"{record.get('stage128_m3_lag_wdi_post_retrieval_audit_authorized_now')}",
                "- ⛔ **Reading is not admitting:** the audit executed NO Data "
                "Gate, applied NO coverage threshold, made NO admission "
                "decision and touched 0 company rows. Both contract features "
                f"are constructible at SERIES level for {_a_first}–{_a_last}, "
                f"bound by `{_a_bind}` — a series-level statement, NOT "
                "coverage and NOT an admission",
                "- ⚠️ **Material findings recorded "
                f"({len(_a_lims)}):** "
                + " | ".join(_a_lims),
                "- ⚠️ **FX feature degeneracy:** the log-ratio transform is "
                f"defined but identically ZERO for the last {_a_zero} usable "
                "predictor years (the official rate is repeated unchanged), "
                "so completeness there does not imply information",
            ]
        # Step C authorization, split the same way step B's and step D's are.
        # Rendering only the generic field here used to hide the historical
        # fact behind a bare "authorized False", which reads as though the
        # audit never happened — the mirror image of the drift where a spent
        # authorization read as a live one. Both facts are shown instead.
        _audit_generic = record.get(
            "stage128_m3_lag_wdi_post_retrieval_audit_authorized")
        _audit_was = record.get(
            "stage128_m3_lag_wdi_post_retrieval_audit_was_authorized",
            _audit_generic)
        _audit_now = record.get(
            "stage128_m3_lag_wdi_post_retrieval_audit_authorized_now",
            _audit_generic)
        _audit_consumed = record.get(
            "stage128_m3_lag_wdi_post_retrieval_audit_authorization_consumed",
            False)
        _audit_reusable = record.get(
            "stage128_m3_lag_wdi_post_retrieval_audit_authorization_reusable",
            False)
        # Step D authorization, split the same way step B's is: a spent
        # one-time Gate authorization must never render as a live permission
        # to run the Gate again. Before step D both fall back to the generic
        # (standing) field, which is False until a new authorization exists.
        _gate_generic = record.get("stage128_m3_lag_wdi_data_gate_authorized")
        _gate_was = record.get(
            "stage128_m3_lag_wdi_data_gate_was_authorized", _gate_generic)
        _gate_now = record.get(
            "stage128_m3_lag_wdi_data_gate_authorized_now", _gate_generic)
        _gate_consumed = record.get(
            "stage128_m3_lag_wdi_data_gate_authorization_consumed", False)
        _gate_reusable = record.get(
            "stage128_m3_lag_wdi_data_gate_authorization_reusable", False)
        # Step E authorization, pulled from the published action sequence
        # rather than hard-coded: the sequence is the single place every
        # step's historical-vs-standing authorization is kept in sync, and
        # a step E entry only exists there once the step E deriver runs.
        _e_seq_entry = next(
            (item for item in
             (record.get("stage128_m3_lag_wdi_action_sequence") or [])
             if item.get("step") == "E"), {})
        _e_was = _e_seq_entry.get("was_authorized", False)
        _e_now = _e_seq_entry.get("authorized_now", False)
        _e_consumed = record.get(
            "stage128_m3_lag_wdi_modeling_authorization_consumed", False)
        _e_reusable = record.get(
            "stage128_m3_lag_wdi_modeling_authorization_reusable", False)
        _e_status = _e_seq_entry.get("status", "NOT_AUTHORIZED")
        # Step D. The single most dangerous thing this section could do is
        # render a coverage PASS in a way that reads as scientific
        # endorsement or as permission to model, so the verdict is never
        # published without the limitations that survive it.
        _gate_lines = []
        if record.get("stage128_m3_lag_wdi_data_gate_executed"):
            _g_result = record.get("stage128_m3_lag_wdi_data_gate_result")
            _g_admitted = record.get("stage128_m3_lag_wdi_block_admitted")
            _g_n = record.get("stage128_m3_lag_wdi_gate_denominator_rows")
            _g_cpi = record.get("stage128_m3_lag_wdi_gate_cpi_valid_rows")
            _g_fx = record.get("stage128_m3_lag_wdi_gate_fx_valid_rows")
            _g_block = record.get(
                "stage128_m3_lag_wdi_gate_block_common_sample_rows")
            _g_cand_min = record.get(
                "stage128_m3_lag_wdi_gate_candidate_coverage_min")
            _g_block_min = record.get(
                "stage128_m3_lag_wdi_gate_block_coverage_min")
            _g_pos_min = record.get(
                "stage128_m3_lag_wdi_gate_min_positive_each_validation_window")
            _g_f1 = record.get(
                "stage128_m3_lag_wdi_gate_fold1_positive_evaluable")
            _g_f2 = record.get(
                "stage128_m3_lag_wdi_gate_fold2_positive_evaluable")
            _g_zero = record.get(
                "stage128_m3_lag_wdi_gate_fx_zero_change_development_rows")
            _g_lims = record.get(
                "stage128_m3_lag_wdi_gate_material_limitations") or []
            _gate_lines = [
                "- ✅ **Step D Data Gate EXECUTED** — formal verdict "
                f"`{_g_result}`; block formally admitted = {_g_admitted}, and "
                "that admission is DATA ADMISSION ONLY (authorizes modeling = "
                f"{record.get('stage128_m3_lag_wdi_gate_pass_authorizes_modeling')}"
                ", unlocks the Final Test = "
                f"{record.get('stage128_m3_lag_wdi_gate_pass_unlocks_final_test')}"
                "). Its one-time authorization is consumed = "
                f"{record.get('stage128_m3_lag_wdi_data_gate_authorization_consumed')}"
                ", reusable = "
                f"{record.get('stage128_m3_lag_wdi_data_gate_authorization_reusable')}"
                ", authorized NOW (standing) = "
                f"{record.get('stage128_m3_lag_wdi_data_gate_authorized_now')}",
                "- **Coverage against the LOCKED, INHERITED thresholds** "
                "(thresholds changed by this action = "
                f"{record.get('stage128_m3_lag_wdi_gate_thresholds_changed_by_this_action')}"
                f", criteria weakened = "
                f"{record.get('stage128_m3_lag_wdi_gate_criteria_weakened')}): "
                f"CPI {_g_cpi}/{_g_n}, FX {_g_fx}/{_g_n} (each vs "
                f">= {_g_cand_min}); block common sample {_g_block}/{_g_n} "
                f"(vs >= {_g_block_min}); positive evaluable per locked "
                f"validation window {_g_f1} and {_g_f2} (vs >= {_g_pos_min}); "
                "rows excluded = "
                f"{record.get('stage128_m3_lag_wdi_gate_rows_excluded')}",
                "- ⚠️ **A coverage PASS is NOT an information-content claim** "
                "(published as one = "
                f"{record.get('stage128_m3_lag_wdi_gate_pass_is_information_content_claim')}"
                "). The step C finding stands unchanged (step C result "
                f"`{record.get('stage128_m3_lag_wdi_post_retrieval_audit_result')}`"
                ", findings preserved = "
                f"{record.get('stage128_m3_lag_wdi_step_c_material_findings_preserved')}"
                "): the FX log-ratio is identically ZERO for predictor years "
                "2021–2024. Those years fall OUTSIDE the development sample, "
                f"which carries {_g_zero} zero-change rows — so the "
                "degeneracy does not change the formal verdict under the "
                "PRE-EXISTING rules, and no new rejection criterion was "
                "invented to make it do so",
            ]
            # The limitation list is the Step D artifact's own wording, read
            # verbatim and never rewritten. One of its four entries — the
            # unlocked calendar mapping — was TRUE WHEN STEP D RAN and was
            # later resolved by a separate human decision. Publishing the
            # historical list under a present-tense header is what made the
            # generated CURRENT_STATE contradict
            # `calendar_mapping_locked = True`, so the header states when the
            # list was recorded and the calendar bullet below reports the
            # CURRENT status of that entry.
            _calmap_locked = bool(
                record.get("stage128_m3_lag_wdi_calendar_mapping_locked"))
            _lims_header = (
                "Limitations RECORDED AT STEP D, verbatim"
                if _calmap_locked
                else "Limitations that SURVIVE the verdict")
            _gate_lines += [
                f"- ⚠️ **{_lims_header} ({len(_g_lims)}):** "
                + " | ".join(_g_lims),
            ]
            if _calmap_locked:
                _gate_lines += [
                    "- ✅ **Calendar mapping LOCKED (resolved AFTER step D, "
                    "by a separate human scientific decision — action "
                    f"`{record.get('stage128_m3_lag_wdi_calendar_mapping_lock_action_id')}`):** "
                    "the fourth step-D limitation above is HISTORICAL and no "
                    "longer open. Locked rule "
                    f"`{record.get('stage128_m3_lag_wdi_calendar_mapping_rule')}` "
                    "— "
                    f"`{record.get('stage128_m3_lag_wdi_calendar_mapping_rule_formula')}` "
                    "(locked = "
                    f"{record.get('stage128_m3_lag_wdi_calendar_mapping_locked')}"
                    "). Offset +"
                    f"{record.get('stage128_m3_lag_wdi_calendar_mapping_locked_offset')}"
                    " carries "
                    f"{record.get('stage128_m3_lag_wdi_calendar_mapping_locked_offset_violations')}"
                    f"/{_g_n} timing violations (minimum margin "
                    f"{record.get('stage128_m3_lag_wdi_calendar_mapping_locked_offset_margin_days_min')}"
                    " days); the REJECTED offset +"
                    f"{record.get('stage128_m3_lag_wdi_calendar_mapping_rejected_offset')}"
                    " carries "
                    f"{record.get('stage128_m3_lag_wdi_calendar_mapping_rejected_offset_violations')}"
                    f"/{_g_n} (worst "
                    f"{record.get('stage128_m3_lag_wdi_calendar_mapping_rejected_offset_worst_days')}"
                    " days past the cutoff), so the two conventions are NOT "
                    "equally admissible. Selected on timing alone (selection "
                    "used model performance = "
                    f"{record.get('stage128_m3_lag_wdi_calendar_mapping_selection_used_model_performance')}"
                    "). A further calendar-mapping decision is required "
                    "before modeling = "
                    f"{record.get('stage128_m3_lag_wdi_calendar_mapping_lock_required_before_modeling')}"
                    "; its one-time authorization is consumed = "
                    f"{record.get('stage128_m3_lag_wdi_calendar_mapping_lock_authorization_consumed')}"
                    ", reusable = "
                    f"{record.get('stage128_m3_lag_wdi_calendar_mapping_lock_authorization_reusable')}"
                    ", authorized NOW (standing) = "
                    f"{record.get('stage128_m3_lag_wdi_calendar_mapping_lock_authorized_now')}"
                    " — changing it needs a NEW human decision = "
                    f"{record.get('stage128_m3_lag_wdi_calendar_mapping_changing_requires_new_human_decision')}",
                    "- ⛔ **The lock authorized NOTHING downstream:** "
                    "authorizes modeling = "
                    f"{record.get('stage128_m3_lag_wdi_calendar_mapping_lock_authorizes_modeling')}"
                    ", authorizes a feature-value table = "
                    f"{record.get('stage128_m3_lag_wdi_calendar_mapping_lock_authorizes_feature_table')}"
                    ". It amends the frozen contract without editing its "
                    "history (amends but does not edit = "
                    f"{record.get('stage128_m3_lag_wdi_calendar_mapping_amends_but_does_not_edit')}"
                    "), and it resolved NO data limitation: "
                    f"{record.get('stage128_m3_lag_wdi_calendar_mapping_unresolved_limitation_count')}"
                    " limitations survive it (point-in-time WDI availability "
                    "UNPROVEN, the FX 2021–2024 degeneracy and the "
                    "`PA.NUS.FCRF` 2024–2025 missingness all stand). "
                    "**As of the calendar-mapping lock,** step E still "
                    "requires its own NEW explicit human authorization"
                    + (
                        " — **step E has since executed, see the Step E "
                        "section below**"
                        if record.get(
                            "stage128_m3_lag_wdi_modeling_started")
                        else ""
                    ),
                    "- Package: `project/stage128/"
                    "m3_lag_wdi_exploratory_calendar_mapping_lock/`; "
                    "interpretation: `project/stage128/"
                    "m3_lag_wdi_exploratory_calendar_mapping_lock/"
                    "README_STAGE128_M3_LAG_WDI_EXPLORATORY_CALENDAR_MAPPING"
                    "_LOCK.md`",
                ]
            else:
                _gate_lines += [
                    "- ⛔ **Calendar mapping still unlocked:** the locked "
                    "contract does not fix the Jalali→Gregorian mapping for "
                    "`predictor_year_t` (locked = "
                    f"{record.get('stage128_m3_lag_wdi_calendar_mapping_locked')}"
                    "). The verdict is invariant across BOTH admissible "
                    "conventions (invariant = "
                    f"{record.get('stage128_m3_lag_wdi_gate_status_invariant_across_calendar_conventions')}"
                    "), so it is well-defined despite the gap — but feature "
                    "VALUES are not invariant, so no feature-value table was "
                    "materialized and the mapping must be human-locked "
                    "before any modeling table exists",
                ]
            _gate_lines += [
                "- Package: `project/stage128/"
                "m3_lag_wdi_exploratory_data_gate/`; interpretation: "
                "`project/stage128/m3_lag_wdi_exploratory_data_gate/"
                "README_STAGE128_M3_LAG_WDI_EXPLORATORY_DATA_GATE.md`",
            ]
        # "Nothing executed" was true only while Track B was a bare contract
        # lock. Derived so the summary can never contradict the line below it.
        _track_b_ran = bool(
            record.get("stage128_m3_lag_wdi_data_retrieval_started")
            or record.get("stage128_m3_lag_wdi_data_gate_executed"))
        _track_b_exec_icon = "✅" if _track_b_ran else "⛔"
        _track_b_exec_label = (
            "Track B execution state" if _track_b_ran else "Nothing executed")
        lines += [
            "### Stage128 — TRACK B: M3-LAG-WDI-EXPLORATORY contract lock "
            "(PRE-RETRIEVAL)\n",
            "_Two tracks now run in PARALLEL. **Track A** is the World Bank "
            "official inquiry, still waiting for a substantive response. "
            "**Track B** is this exploratory contract lock. Activating Track "
            "B does NOT mean the inquiry failed, terminated, was abandoned or "
            "became unnecessary, and a locked contract is NOT an "
            "authorization to retrieve anything._\n",
            "- ✅ **Contract status:** "
            f"`{record.get('stage128_m3_lag_wdi_authoritative_contract_status')}`"
            " — role "
            f"`{record.get('stage128_m3_lag_wdi_scientific_role')}`, "
            "confirmatory M3 = "
            f"{record.get('stage128_m3_lag_wdi_is_confirmatory_m3')} — "
            "authorization SHA-256 "
            f"`{record.get('stage128_m3_lag_wdi_authorization_sha256')}` "
            f"({record.get('stage128_m3_lag_wdi_authorization_utf8_bytes')} "
            "UTF-8 bytes), consumed = "
            f"{record.get('stage128_m3_lag_wdi_authorization_consumed')}",
            "- **Exactly two lagged WDI features** "
            f"({record.get('stage128_m3_lag_wdi_additional_feature_count')}): "
            f"`{record.get('stage128_m3_lag_wdi_cpi_indicator_code')}` "
            "(identity) and "
            f"`{record.get('stage128_m3_lag_wdi_fx_indicator_code')}` "
            f"(`{record.get('stage128_m3_lag_wdi_fx_transformation')}`), "
            "country `IRN`, observation year "
            f"`{record.get('stage128_m3_lag_wdi_observation_year_rule')}` — "
            "M2 comparator "
            f"{record.get('stage128_m3_lag_wdi_m2_comparator_feature_count')} "
            "features, M3-LAG-WDI "
            f"{record.get('stage128_m3_lag_wdi_feature_count')} features on "
            "the retained-M2 "
            f"{record.get('stage128_m3_lag_wdi_parent_sample_rows')}-row "
            "development sample",
            "- ⛔ **No point-in-time claim:** point-in-time availability "
            "claimed = "
            f"{record.get('stage128_m3_lag_wdi_point_in_time_availability_claimed')}"
            " — the future retrieval uses the CURRENT/LATEST revised WDI "
            f"({record.get('stage128_m3_lag_wdi_current_revised_wdi_semantics')})"
            ", and the one-year lag does not turn revised WDI into "
            "point-in-time data",
            "- ⛔ **Separate family:** exploratory comparison family "
            f"`{record.get('stage128_m3_lag_wdi_comparison_family_id')}` — in "
            "the confirmatory Holm family = "
            f"{record.get('stage128_m3_lag_wdi_in_confirmatory_holm_family')}",
            # The heading must describe what is actually true NOW. Once the
            # Gate has run, "Nothing executed" would be a false summary
            # sitting directly above a line that says it executed.
            f"- {_track_b_exec_icon} **{_track_b_exec_label}:** retrieval "
            "started "
            f"{record.get('stage128_m3_lag_wdi_data_retrieval_started')} — "
            "Data Gate "
            f"`{record.get('stage128_m3_lag_wdi_data_gate_result')}` "
            "(executed "
            f"{record.get('stage128_m3_lag_wdi_data_gate_executed')}) — "
            "modeling started "
            f"{record.get('stage128_m3_lag_wdi_modeling_started')} "
            "(authorized "
            f"{record.get('stage128_m3_lag_wdi_modeling_authorized')}) — "
            "Final Test rows read "
            f"{record.get('stage128_m3_lag_wdi_final_test_rows_read')}",
            # The label must describe the NEXT action, never the one just
            # completed. Retrieval is done and its authorization is consumed,
            # so the pointer is rendered with its own published scope instead
            # of a hard-coded phrase that would go stale the moment Track B
            # advances.
            "- **Track B next action (pointer only, NOT an "
            "authorization):** "
            f"`{record.get('stage128_m3_lag_wdi_next_action_id')}` — scope "
            f"`{record.get('stage128_m3_lag_wdi_next_action_scope')}`, "
            "authorized = "
            f"{record.get('stage128_m3_lag_wdi_next_action_authorized')}, "
            "WOULD execute the Data Gate if it were ever authorized = "
            f"{record.get('stage128_m3_lag_wdi_next_action_executes_data_gate')}"
            " (a property of the named action, NOT a statement that the Gate "
            "ran — see Data Gate executed below). A pointer is never an "
            "authorization",
            # Retrieval, the Gate and modeling are three separate actions, so
            # an authorization for one can never be read as authorizing the
            # next. Rendering them as one line would erase that boundary.
            # Step B renders HISTORICAL and STANDING authorization separately:
            # after execution its one-time authorization is consumed, and a
            # reader must never mistake that spent authorization for a live
            # permission to issue another World Bank request.
            "- ⛔ **Separated future actions (each needs its OWN new explicit "
            "human authorization):** (B) "
            f"`{record.get('stage128_m3_lag_wdi_retrieval_action_id')}` — "
            f"was authorized (historical) {_rtrv_was}, "
            f"authorized NOW (standing) {_rtrv_now} — one-time "
            f"authorization consumed = {_rtrv_consumed}, "
            f"reusable = {_rtrv_reusable}, further retrieval requires NEW "
            f"human authorization = {_rtrv_new_auth}, "
            "executes Gate "
            f"{record.get('stage128_m3_lag_wdi_retrieval_executes_data_gate')}"
            "; (C) "
            f"`{record.get('stage128_m3_lag_wdi_post_retrieval_audit_action_id')}`"
            f" — was authorized (historical) {_audit_was}, authorized NOW "
            f"(standing) {_audit_now} — one-time authorization consumed = "
            f"{_audit_consumed}, reusable = {_audit_reusable}"
            ", executes Gate "
            f"{record.get('stage128_m3_lag_wdi_post_retrieval_audit_executes_data_gate')}"
            "; (D) "
            f"`{record.get('stage128_m3_lag_wdi_data_gate_action_id')}` — "
            f"was authorized (historical) {_gate_was}, authorized NOW "
            f"(standing) {_gate_now} — one-time authorization consumed = "
            f"{_gate_consumed}, reusable = {_gate_reusable}; (E) "
            f"`{record.get('stage128_m3_lag_wdi_modeling_action_id')}` — "
            f"was authorized (historical) {_e_was}, "
            f"authorized NOW (standing) {_e_now} — one-time authorization "
            f"consumed = {_e_consumed}, reusable = {_e_reusable}, "
            f"status {_e_status}",
            "- ⛔ **Authorization boundaries:** a retrieval authorization "
            "implies a Gate authorization = "
            f"{record.get('stage128_m3_lag_wdi_retrieval_authorization_implies_gate_authorization')}"
            " — a combined retrieval-and-Gate action is permitted = "
            f"{record.get('stage128_m3_lag_wdi_combined_retrieval_and_gate_action_permitted')}"
            " — a Gate PASS is data admission only = "
            f"{record.get('stage128_m3_lag_wdi_gate_pass_is_data_admission_only')}"
            " and authorizes modeling = "
            f"{record.get('stage128_m3_lag_wdi_gate_pass_authorizes_modeling')}",
            "- **Prior restriction:** "
            f"`{record.get('stage128_m3_lag_wdi_prior_restriction_status')}` "
            "— the old \"only after "
            "`UNRESOLVED_AFTER_FINAL_OFFICIAL_INQUIRY`\" rule is retained as "
            "HISTORY, not deleted",
            (
                "- ⛔ **Track A voluntarily terminated:** as of the "
                "calendar-mapping lock the inquiry was not terminated by "
                "this action "
                f"({record.get('stage128_m3i2_inquiry_terminated_by_track_b')})"
                " — Track A had not yet been touched; it has since been "
                "voluntarily terminated by explicit human decision on "
                f"`{record.get('stage128_track_a_waiting_termination_date')}`"
                " (status "
                f"`{record.get('stage128_track_a_waiting_period_status')}`), "
                "see the Track A waiting-period termination section below "
                "— follow-up authorized now "
                f"{record.get('stage128_m3i2_inquiry_follow_up_authorized_now')}, "
                "response adjudication authorized "
                f"{record.get('stage128_m3i2_response_adjudication_authorized')}"
                if record.get("stage128_track_a_waiting_termination_recorded")
                else
                "- ⛔ **Track A untouched:** the inquiry was NOT terminated by "
                "this action "
                f"({record.get('stage128_m3i2_inquiry_terminated_by_track_b')}) — "
                "follow-up authorized now "
                f"{record.get('stage128_m3i2_inquiry_follow_up_authorized_now')}, "
                "response adjudication authorized "
                f"{record.get('stage128_m3i2_response_adjudication_authorized')}"
            ),
            *_custody_lines,
            *_audit_lines,
            *_gate_lines,
            "- Package: `project/stage128/"
            "m3_lag_wdi_exploratory_contract_lock/`; interpretation: "
            "`project/stage128/m3_lag_wdi_exploratory_contract_lock/"
            "README_STAGE128_M3_LAG_WDI_EXPLORATORY_CONTRACT_LOCK.md`",
            "",
        ]
    if record.get("stage128_track_a_waiting_termination_recorded"):
        lines += [
            "### Stage128 — TRACK A waiting-period termination and "
            "M3-LAG-WDI final disposition (DECISION RECORDING ONLY)\n",
            "_An explicit human governance decision, not a one-action "
            "execution authorization. Zero data, zero network access, zero "
            "model fits, zero Final Test rows read._\n",
            "- ✅ **Waiting period:** "
            f"`{record.get('stage128_track_a_waiting_period_status')}` on "
            f"`{record.get('stage128_track_a_waiting_termination_date')}` — "
            "the previously locked completion date "
            f"`{record.get('stage128_track_a_waiting_period_original_completion_date')}`"
            " is preserved as history and is **no longer an active "
            "blocker**.",
            "- ⛔ **Not recorded as World Bank non-response:** "
            "`world_bank_will_not_respond_claim_made` = "
            f"{record.get('stage128_track_a_world_bank_will_not_respond_claim_made')}."
            " Recorded exactly: "
            f"`{record.get('stage128_track_a_world_bank_response_characterization')}`.",
            "- ⛔ **No further Track A action authorized:** further "
            "follow-up authorized = "
            f"{record.get('stage128_track_a_further_followup_authorized')}"
            " — further WDI retrieval authorized = "
            f"{record.get('stage128_track_a_further_wdi_retrieval_authorized')}"
            " — historical release-date inference/backfill authorized = "
            f"{record.get('stage128_track_a_release_date_inference_or_backfill_authorized')}.",
            "- ⚠️ **Point-in-time WDI availability:** "
            f"`{record.get('stage128_m3_lag_wdi_point_in_time_availability_status')}`"
            " — treated as "
            f"`{record.get('stage128_m3_lag_wdi_point_in_time_availability_treated_as')}`,"
            " never as a task that blocks the research programme.",
            "- ✅ **M3-LAG-WDI final research disposition:** "
            f"`{record.get('stage128_m3_lag_wdi_final_research_disposition')}`"
            " — promoted to the confirmatory model = "
            f"{record.get('stage128_m3_lag_wdi_promoted_to_confirmatory_model')}."
            " A future unsolicited World Bank response auto-reopens M3 = "
            f"{record.get('stage128_m3_lag_wdi_unsolicited_future_response_auto_reopens')}"
            " (using it for anything requires a new explicit human decision "
            "= "
            f"{record.get('stage128_m3_lag_wdi_future_response_requires_new_human_decision')}).",
            "- ✅ **Step E result PRESERVED EXACTLY, re-verified against the "
            "committed artifact by this recording:** "
            f"`{record.get('stage128_m3_lag_wdi_e1_conclusion')}` — paired "
            "PR-AUC deltas (M3-LAG-WDI minus retained M2) logistic "
            "+0.000862 [-0.028237, +0.032186], random forest -0.002720 "
            "[-0.029157, +0.011924], XGBoost +0.002749 [-0.007437, "
            "+0.014554] (all three 95% intervals include zero); secondary "
            "Brier deltas logistic -0.004600 [-0.006147, -0.003066] and "
            "random forest -0.001375 [-0.002229, -0.000566] (calibration "
            "only, non-confirmatory).",
            "- ⛔ **Unchanged:** M4 authorized "
            f"{record.get('m4_authorized')} — Final Test locked "
            f"{record.get('final_test_locked')}, rows read "
            f"{record.get('stage128_m3_lag_wdi_final_test_rows_read', 0)} — "
            "confirmatory Holm family unchanged and unexecuted — paper "
            f"winner selected {record.get('paper_winner_selected')}.",
            "- **Both pointer chains converge on the same human decision:** "
            f"`{record.get('next_research_action_id')}` — scope "
            f"`{record.get('next_research_action_scope')}`, authorized = "
            f"{record.get('next_research_action_authorized')}. Track B: "
            f"`{record.get('stage128_m3_lag_wdi_next_action_id')}` — scope "
            f"`{record.get('stage128_m3_lag_wdi_next_action_scope')}`, "
            "authorized = "
            f"{record.get('stage128_m3_lag_wdi_next_action_authorized')}. A "
            "pointer is never an authorization.",
            "- Package: `project/stage128/"
            "m3i2_track_a_waiting_termination_and_m3_disposition/`; "
            "interpretation: `project/stage128/"
            "m3i2_track_a_waiting_termination_and_m3_disposition/"
            "README_STAGE128_M3I2_TRACK_A_WAITING_TERMINATION_AND_M3_"
            "DISPOSITION.md`",
            "",
        ]
    if record.get("stage129_m4_contract_lock_executed"):
        holm = record.get("stage129_m4_confirmatory_holm_family") or []
        lines += [
            "### Stage129 — M4 governance Data-Gate contract lock "
            "(DESIGN ONLY, additive, not on either live pointer chain)\n",
            "_A prospective, pre-retrieval contract lock only. Zero M4 "
            "retrieval, zero Data Gate execution, zero modeling, zero Final "
            "Test access._\n",
            "- ✅ **(A) Candidate identity lock:** "
            f"`{record.get('stage129_m4_contract_status')}` — candidate "
            f"identity set locked = "
            f"{record.get('stage129_m4_candidate_identity_set_locked')}, "
            f"count `{record.get('stage129_m4_candidate_count')}` "
            "(exact, no substitution): "
            f"`{record.get('stage129_m4_candidate_set')}`.",
            "- ✅ **(B) Gate policy contract recorded:** "
            f"{record.get('stage129_m4_gate_policy_contract_recorded')} "
            "(thresholds, Gate dimensions, point-in-time rule, join "
            "identity, missingness policy, three-state semantics).",
            "- ⛔ **(D) The contract as a whole is NOT complete:** "
            f"contract complete = "
            f"{record.get('stage129_m4_contract_complete')}, fully "
            "executable = "
            f"{record.get('stage129_m4_contract_fully_executable')}, status "
            f"`{record.get('stage129_m4_contract_completion_status')}`. "
            "M4 Data Gate executable = "
            f"{record.get('stage129_m4_data_gate_executable')}, Data Gate "
            f"authorized = "
            f"{record.get('stage129_m4_data_gate_authorized')}, coverage "
            f"calculated = {record.get('stage129_m4_coverage_calculated')}. "
            "Candidates blocked by an unresolved semantic definition: "
            f"`{record.get('stage129_m4_candidates_blocked_by_unresolved_definitions')}`"
            "; candidates with gate-ready semantic definitions: "
            f"`{record.get('stage129_m4_candidates_with_gate_ready_semantic_definitions')}`"
            "; candidates the Gate may actually execute for: "
            f"`{record.get('stage129_m4_candidates_the_gate_may_execute_for')}` "
            "(none — see the cross-cutting identity issue below).",
            "- ⚠️ **(C) CROSS-CUTTING CONTRACT ISSUE — CODAL company "
            "identity:** "
            f"`{record.get('stage129_m4_codal_identity_resolution_status')}`. "
            "No audited deterministic mapping resolves a CODAL issuer "
            "identity to the frozen parent-side `ticker` key. The audited "
            "stage127 join evidence is PARENT-SIDE only (its child side was "
            "TSETMC market data, not CODAL filings), so it does not "
            "establish cross-source identity compatibility. The Gate's "
            "join-quality dimension is therefore not executable for "
            "CODAL-sourced values "
            f"({record.get('stage129_m4_join_dimension_executable_for_codal_values')})"
            " — which is every M4 candidate.",
            "- ⛔ **Nothing executed:** M4 data retrieval started "
            f"{record.get('m4_data_retrieval_started')} — candidate "
            f"observations read {record.get('m4_candidate_observations_read')}"
            f" — Data Gate executed {record.get('m4_data_gate_executed')} — "
            f"block admitted {record.get('m4_block_admitted')} — modeling "
            f"started {record.get('m4_modeling_started')} — incremental "
            "evaluation authorized "
            f"{record.get('m4_incremental_evaluation_authorized')}.",
            "- **Contract-lock authorization (consumed, not standing):** "
            f"was_authorized={record.get('stage129_m4_contract_lock_was_authorized')}, "
            f"authorized_now={record.get('stage129_m4_contract_lock_authorized_now')}, "
            f"authorization_consumed={record.get('stage129_m4_contract_lock_authorization_consumed')}, "
            f"authorization_reusable={record.get('stage129_m4_contract_lock_authorization_reusable')}.",
            "- **A THIRD, separate pointer** (neither Track A's "
            f"`{record.get('next_research_action_id')}` nor Track B's "
            f"`{record.get('stage128_m3_lag_wdi_next_action_id')}` is moved "
            "by this action): at lock time this action published "
            f"`{record.get('stage129_m4_contract_lock_pointer_at_lock_time')}`"
            " — authorized = "
            f"{record.get('stage129_m4_next_action_authorized')}. A pointer "
            "is never an authorization."
            + (" **Superseded:** the live M4 pointer is now "
               f"`{record.get('stage129_m4_next_action_id')}` after the human "
               "decision to discontinue M4."
               if record.get("stage129_m4_discontinuation_recorded") else ""),
            "- ⚠️ **(C) Two candidate-specific CONTRACT ISSUES / UNRESOLVED "
            "prerequisite definitions.** Candidate IDENTITY for both is frozen; their "
            "DEFINITIONS are not, no modeled values are admitted, no "
            "empirical discovery is allowed, and the future Gate cannot "
            "execute for either candidate until a separately authorized, "
            "authoritative resolution exists: `audit_opinion_type` category "
            "taxonomy = "
            f"`{record.get('stage129_m4_audit_opinion_type_taxonomy_status')}`"
            " (only secondary Persian accounting-blog sources found, no "
            "authoritative CODAL field schema or IACPA/Audit Organization "
            "standard text); `audit_lag_days` calendar-conversion "
            "convention = "
            f"`{record.get('stage129_m4_audit_lag_days_calendar_conversion_status')}`"
            " (the M3-LAG-WDI `jalali_fiscal_year_t_plus_621` YEAR-MAPPING "
            "rule is explicitly NOT applicable to this day-level date "
            "difference, and no authoritative CODAL date-field conversion "
            "rule was found).",
            "- ⚠️ **Join identity: parent-side keys frozen, CODAL side "
            "UNRESOLVED.** Frozen to the already-audited M2/M3-family "
            "keys:** company key = "
            f"`{record.get('stage129_m4_join_identity_company_key')}`, "
            "fiscal-year key = "
            f"`{record.get('stage129_m4_join_identity_fiscal_year_key')}`, "
            "ambiguous-identity verdict = "
            f"`{record.get('stage129_m4_join_identity_ambiguous_verdict')}`"
            " — source: "
            f"`{record.get('stage129_m4_join_identity_source')}`.",
            "- ⛔ **Unchanged (regression check):** M3-CBI status "
            f"`{record.get('stage129_m4_m3_cbi_status_preserved')}`, "
            "M3-LAG-WDI disposition "
            f"`{record.get('stage129_m4_m3_lag_wdi_disposition_preserved')}`,"
            f" confirmatory Holm family `{holm}` executed = "
            f"{record.get('stage129_m4_confirmatory_holm_family_executed')}.",
            "- ⛔ **Final Test firewall untouched:** locked "
            f"{record.get('stage129_m4_final_test_locked')}, rows read "
            f"{record.get('stage129_m4_final_test_rows_read')}.",
            "- Package: `project/stage129/m4_governance_data_gate_contract/`;"
            " interpretation: `project/stage129/"
            "m4_governance_data_gate_contract/"
            "README_STAGE129_M4_GOVERNANCE_DATA_GATE_CONTRACT.md`",
            "",
        ]
    if record.get("stage129_m4_discontinuation_recorded"):
        lines += [
            "### Stage129 — M4 DISCONTINUED by human decision (data inadequacy)\n",
            "_A human governance decision only. The formal M4 Data Gate was "
            "NEVER executed: zero formal coverage computation, zero feature "
            "materialization, zero modeling, zero Final Test access._\n",
            "- ⛔ **Block disposition:** "
            f"`{record.get('m4_block_disposition')}` — authorized by human = "
            f"{record.get('stage129_m4_discontinuation_authorized_by_human')}, "
            f"reason class `{record.get('stage129_m4_discontinuation_reason_class')}`.",
            "- ❗ **This is NOT a formal Gate failure:** formal Gate executed = "
            f"{record.get('m4_data_gate_executed')}, formal verdict "
            f"`{record.get('m4_formal_gate_verdict')}`, is-formal-gate-failure = "
            f"{record.get('stage129_m4_discontinuation_is_formal_gate_failure')}. "
            "The observational figures "
            f"({record.get('stage129_m4_observational_verified_opinion_rows')} "
            "verified opinions and "
            f"{record.get('stage129_m4_observational_report_date_rows')} report "
            "dates over the whole 1331-row canonical population, "
            f"{record.get('stage129_m4_observational_field_level_missing')} "
            "field-level missing) are OBSERVATIONAL coverage, not a Gate "
            "verdict: "
            f"{record.get('stage129_m4_observational_coverage_is_not_formal_gate_coverage')}.",
            "- ⛔ **Nothing downstream is authorized:** retrieval continues = "
            f"{record.get('m4_retrieval_continues')}, manual completion "
            f"continues = {record.get('m4_manual_completion_continues')}, "
            f"feature materialization = "
            f"{record.get('m4_feature_materialization_authorized')}, modeling "
            f"will run = {record.get('m4_modeling_will_run')}, incremental "
            f"evaluation will run = "
            f"{record.get('m4_incremental_evaluation_will_run')}.",
            "- 🔒 **Reopening:** authorized = "
            f"{record.get('m4_reopening_authorized')}, requires new explicit "
            "human authorization = "
            f"{record.get('m4_reopening_requires_new_human_authorization')}.",
            "- ✅ **Candidate identity preserved, not rewritten:** count "
            f"`{record.get('stage129_m4_candidate_count_after_discontinuation')}`, "
            f"set `{record.get('stage129_m4_candidate_set_after_discontinuation')}`, "
            "removed or renamed = "
            f"{record.get('stage129_m4_candidates_removed_or_renamed')}.",
            "- ⛔ **Holm family unchanged and the M4 comparison unexecuted:** "
            f"`{record.get('stage129_m4_comparison_id')}` status "
            f"`{record.get('stage129_m4_comparison_status')}`, p-value "
            f"`{record.get('stage129_m4_comparison_p_value')}`, family modified "
            f"= {record.get('stage129_m4_confirmatory_holm_family_modified')}, "
            "shrunk post hoc = "
            f"{record.get('stage129_m4_family_shrunk_post_hoc')}. Manuscript "
            "reporting decision for the unexecuted comparison: "
            f"`{record.get('stage129_m4_manuscript_reporting_decision_for_unexecuted_comparison')}`.",
            "- 📄 **Observational extraction:** status "
            f"`{record.get('stage129_m4_observational_package_status_preserved')}`"
            " — retained in custody, not a model input, reportable in "
            "limitations = "
            f"{record.get('stage129_m4_observational_extraction_reportable_in_limitations')}.",
            "- ⛔ **Final Test firewall untouched:** locked "
            f"{record.get('stage129_m4_final_test_locked')}, rows read "
            f"{record.get('stage129_m4_final_test_rows_read')}.",
            "- ➡️ **Next action:** "
            f"`{record.get('stage129_m4_next_action_id')}` — scope "
            f"`{record.get('stage129_m4_next_action_scope')}`, authorized = "
            f"{record.get('stage129_m4_next_action_authorized')}, executes M4 = "
            f"{record.get('stage129_m4_next_action_executes_m4')}. A pointer is "
            "never an authorization.",
            "- Package: `project/stage129/"
            "m4_human_discontinuation_data_inadequacy/`; interpretation: "
            "`project/stage129/m4_human_discontinuation_data_inadequacy/"
            "README_STAGE129_M4_HUMAN_DISCONTINUATION_DATA_INADEQUACY.md`",
            "",
        ]
    if record.get("stage129_m4_manuscript_reporting_decision_recorded"):
        lines += [
            "### Stage129 — M4 manuscript reporting decision (governance only)\n",
            "_A human REPORTING decision only. It settles how a prespecified "
            "but never-admitted block is presented, and changes no scientific "
            "state: zero extraction rerun, zero retrieval, zero coverage "
            "computation, zero feature materialization, zero modeling, zero "
            "Holm, zero bootstrap, zero Final Test access._\n",
            "- ✅ **Reporting decision (resolved):** "
            f"`{record.get('stage129_m4_manuscript_reporting_decision_for_unexecuted_comparison')}`"
            " — authorized by human = "
            f"{record.get('stage129_m4_manuscript_reporting_decision_authorized_by_human')}"
            ", resolved = "
            f"{record.get('stage129_m4_manuscript_reporting_decision_is_resolved')}.",
            "- 🔁 **Supersedes one marker, in the open:** previous value "
            f"`{record.get('stage129_m4_manuscript_reporting_decision_previous_value')}`"
            " in "
            f"`{record.get('stage129_m4_manuscript_reporting_decision_supersedes_artifact')}`"
            " (key "
            f"`{record.get('stage129_m4_manuscript_reporting_decision_supersedes_key')}`)"
            ". The discontinuation package is preserved byte-for-byte = "
            f"{record.get('stage129_m4_prior_discontinuation_artifact_preserved')}"
            " — history is superseded, never rewritten.",
            "- ⛔ **M4 is reported as prespecified but NOT executed:** "
            "prespecified = "
            f"{record.get('stage129_m4_reported_as_prespecified')}, not "
            f"executed = {record.get('stage129_m4_reported_as_not_executed')}, "
            "reason class "
            f"`{record.get('stage129_m4_reporting_reason_class')}`.",
            "- ⛔ **No inference is drawn:** "
            f"`{record.get('stage129_m4_comparison_id')}` stays "
            f"`{record.get('stage129_m4_comparison_status')}`, p-value "
            f"`{record.get('stage129_m4_comparison_p_value')}`, null hypothesis "
            "accepted or rejected = "
            f"`{record.get('stage129_m4_reporting_null_hypothesis_accepted_or_rejected')}`"
            ", claims an executed result = "
            f"{record.get('stage129_m4_reporting_claims_an_executed_result')}, "
            "claims M4 performance = "
            f"{record.get('stage129_m4_reporting_claims_m4_performance')}.",
            "- ✅ **SAP history intact:** the comparison is removed from SAP "
            "history = "
            f"{record.get('stage129_m4_comparison_removed_from_sap_history')}, "
            "renamed or substituted = "
            f"{record.get('stage129_m4_comparison_renamed_or_substituted')} — it "
            "is reported as prespecified-but-not-executed, not erased.",
            "- ❗ **Still NOT a Gate failure:** formal Gate executed = "
            f"{record.get('m4_data_gate_executed')}, formal verdict "
            f"`{record.get('m4_formal_gate_verdict')}`, "
            "is-formal-gate-failure = "
            f"{record.get('stage129_m4_reporting_is_formal_gate_failure')}.",
            "- 📝 **Approved reporting text (EN):** "
            f"{record.get('stage129_m4_approved_manuscript_text_en')}",
            "- 📝 **Approved reporting text (FA):** "
            f"{record.get('stage129_m4_approved_manuscript_text_fa')}",
            "- ⛔ **Text is a reporting decision, not a writing authorization:** "
            "manuscript writing or rewriting authorized = "
            f"{record.get('stage129_m4_manuscript_writing_authorized')}.",
            "- ⛔ **Final Test firewall untouched:** rows read "
            f"{record.get('stage129_m4_reporting_final_test_rows_read')}.",
            "- Package: `project/stage129/m4_manuscript_reporting_decision/`;"
            " interpretation: `project/stage129/m4_manuscript_reporting_decision/"
            "README_STAGE129_M4_MANUSCRIPT_REPORTING_DECISION.md`",
            "",
        ]
    lines += [
        "### Last completed scientific micro-part QC\n",
        "_Scientific QC of the newest completed robustness micro-part — a "
        "DIFFERENT role from current-state validation above._\n",
        f"- {qc_ok} **{record['qc_assertions']} assertions, "
        f"{record['qc_failed']} failed**, all_pass={record['qc_all_pass']}",
        f"- Scope: `{record.get('last_completed_micro_part_qc_scope', record['selected_qc_scope'])}`",
        f"- Report: `{record.get('last_completed_micro_part_qc_path', record['selected_qc_path'])}`",
        f"- QC source commit (code): `{record['qc_source_commit']}`",
        "",
        "## Workflow markers\n",
        f"- modeling_started: **{record['modeling_started']}**",
        f"- gate_b_started: **{record['gate_b_started']}**",
        f"- verified_master_created: **{record['verified_master_created']}**",
    ]
    if "part3a_protocol_locked" in record:
        lines.append(
            f"- part3a_protocol_locked: **{record['part3a_protocol_locked']}**"
        )
    if "part3a_decision_locked" in record:
        lines.append(
            f"- part3a_decision_locked: **{record['part3a_decision_locked']}**"
        )
    if "part3b_started" in record:
        lines.append(f"- part3b_started: **{record['part3b_started']}**")
    if "part3b1_decision_locked" in record:
        lines.append(
            f"- part3b1_decision_locked: **{record['part3b1_decision_locked']}**"
        )
    if "cut_a_available_at_operationalization_locked" in record:
        lines.append(
            "- cut_a_available_at_operationalization_locked: "
            f"**{record['cut_a_available_at_operationalization_locked']}**"
        )
    if "predictor_available_at_evidence_collected" in record:
        lines.append(
            "- predictor_available_at_evidence_collected: "
            f"**{record['predictor_available_at_evidence_collected']}**"
        )
    if "predictor_document_binding_mini_pilot_completed" in record:
        lines.append(
            "- predictor_document_binding_mini_pilot_completed: "
            f"**{record['predictor_document_binding_mini_pilot_completed']}**"
        )
    if "predictor_document_binding_evidence_collected" in record:
        lines.append(
            "- predictor_document_binding_evidence_collected: "
            f"**{record['predictor_document_binding_evidence_collected']}**"
        )
    if "pilot_cutoff_provenance_resolved" in record:
        lines.append(
            "- pilot_cutoff_provenance_resolved: "
            f"**{record['pilot_cutoff_provenance_resolved']}**"
        )
    if "part3b0_readiness" in record:
        lines.append(f"- part3b0_readiness: **{record['part3b0_readiness']}**")
    if "evidence_collected" in record:
        lines.append(
            f"- evidence_collected: **{record['evidence_collected']}** "
            f"(endpoint-probe scope when Part 3B active)"
        )
    for key in (
        "endpoint_probe_evidence_collected",
        "candidate_value_evidence_collected",
        "pair_level_evidence_collected",
        "data_value_extraction_performed",
        "accessibility_scoring_applied",
        "part3b_completed",
        "network_extraction_performed",
    ):
        if key in record:
            lines.append(f"- {key}: **{record[key]}**")
    for key in (
        "stage125_completed",
        "stage126_authorized",
        "stage126_started",
        "development_modeling_authorized",
        "modeling_authorized",
        "m1_primary_development_tuning_completed",
        "m1_robustness_started",
        "m1_robustness_completed",
        "final_test_unlocked",
        "final_test_access_authorized",
        "final_test_evaluation_performed",
        # NB: `m2_data_collected` is deliberately NOT rendered here. It is a
        # frozen Stage125 Part 4 prohibition marker, not live state, and
        # printing a bare `m2_data_collected: False` beside an executed M2
        # evaluation reads as a contradiction. It is republished below under
        # the historical/legacy heading, and the live data-state markers are
        # rendered with the current scientific action.
        "m3_data_collected",
        "m4_data_collected",
        # Stage125 temporal-availability invariants carried into Stage126.
        "financial_data_researcher_verified_frozen",
        "broad_codal_capture_stopped",
        "active_availability_method",
        "active_availability_lag_months",
        "four_month_regulatory_lag_locked",
        "six_month_lag_superseded",
        "historical_six_month_decision_retained",
        "row_level_publish_datetime_collection_required",
        "part3c_leakage_safe_finalization_completed",
        "part4_statistical_analysis_plan_locked",
    ):
        if key in record:
            lines.append(f"- {key}: **{record[key]}**")
    if "stage125_part4_m2_data_collected_historical" in record:
        lines.extend([
            "",
            "## Historical / legacy frozen schema markers (NOT live state)\n",
            "_Frozen Stage125 Part 4 contract values, republished verbatim "
            "for audit. They record what that SAP froze when it was created "
            "and are **not** live data-availability or execution markers. The "
            "live M2 data and execution state is rendered with the current "
            "scientific action above._\n",
            "- stage125_part4_m2_data_collected_historical (frozen Part 4 "
            f"value): **{record['stage125_part4_m2_data_collected_historical']}**"
            " — "
            f"{record.get('stage125_part4_m2_data_collected_historical_semantics', '')}",
        ])
    lines.extend([
        "",
        "## Tickers in current research scope\n",
        "، ".join(record["tickers"]),
        "",
        f"_state_fingerprint: `{record['state_fingerprint']}`_",
        f"_generated_at_utc: {record['generated_at_utc']} (informational)_",
        "",
    ])
    return "\n".join(lines)


def render_frozen_assets(frozen: list[dict]) -> str:
    def status(r: dict) -> str:
        if not r["frozen"]:
            return ("➖ regenerable (classified non-frozen)" if r["tracked"]
                    else "➖ regenerable (gitignored, not verified)")
        if not r["tracked"]:
            return "❌ UNTRACKED non-ignored (frozen)"
        if not r["exists"]:
            return "⚠️ MISSING (frozen)"
        return "✅ match" if r["matches"] else "❌ MISMATCH (frozen)"

    frozen_rows = [r for r in frozen if r["frozen"] and r["tracked"]]
    n_frozen = len(frozen_rows)
    n_match = sum(1 for r in frozen_rows if r["matches"])
    lines = [
        _AUTO_BANNER,
        "# FROZEN ASSETS\n",
        "_Generated from the Stage122/Stage123/Stage124 hash manifests "
        "(`metadata_and_hashes_stage12{2,3}.json`, "
        "`metadata_and_hashes_stage124_batch02_gate_b.json`)._\n",
        f"- Frozen (verified) files: **{n_match}/{n_frozen} match**. A missing or "
        "mismatched frozen file is **fatal** (generation/validation fails).",
        "- Files are *regenerable* when gitignored (machine-dependent SHA) or "
        "explicitly classified non-frozen (`NON_FROZEN_TRACKED`, e.g. a pytest log "
        "whose timing line is non-deterministic); these are not hash-verified.",
        "",
        "| Status | Path | Manifest |",
        "|---|---|---|",
    ]
    for r in sorted(frozen, key=lambda x: x["path"]):
        lines.append(f"| {status(r)} | `{r['path']}` | `{r['manifest']}` |")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Package-atomic write with rollback
# --------------------------------------------------------------------------- #

def _atomic_write(root: str, rel_outputs: dict[str, str]) -> None:
    """All-or-nothing write of the auto files.

    1) Write every new file to a ``.handoff_tmp`` sibling.
    2) Move each existing target aside to ``.handoff_bak``, then move the temp in.
    3) On success, delete backups. On any error, restore backups / remove newly
       created files so the package is never left half-updated.
    """
    targets = {rel: os.path.join(root, rel) for rel in rel_outputs}
    tmpfiles: dict[str, str] = {}
    backups: dict[str, str] = {}
    created_new: list[str] = []   # targets we created that had no prior version

    for rel, content in rel_outputs.items():
        os.makedirs(os.path.dirname(targets[rel]), exist_ok=True)
        tmp = targets[rel] + ".handoff_tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(content)
        tmpfiles[rel] = tmp

    try:
        for rel in rel_outputs:
            tgt = targets[rel]
            if os.path.exists(tgt):
                bak = tgt + ".handoff_bak"
                os.replace(tgt, bak)
                backups[rel] = bak  # recorded BEFORE the risky tmp->tgt replace
            os.replace(tmpfiles[rel], tgt)
            if rel not in backups:
                created_new.append(rel)
    except Exception:
        # Restore EVERY original we moved aside — even one whose tmp->tgt replace
        # failed (it has a backup but never made it past the failing step).
        for rel, bak in backups.items():
            tgt = targets[rel]
            if os.path.exists(tgt):
                _silent_remove(tgt)
            try:
                os.replace(bak, tgt)
            except OSError:
                pass
        # Remove only targets WE created (had no prior version); never touch
        # originals that were simply not reached before the failure.
        for rel in created_new:
            _silent_remove(targets[rel])
        for tmp in tmpfiles.values():
            _silent_remove(tmp)
        raise
    else:
        for bak in backups.values():
            _silent_remove(bak)


def _silent_remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def generate(root: str) -> dict[str, str]:
    record, _state, frozen = build_handoff_state(root)
    return generate_from(record, frozen)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-repository", action="store_true",
                        help="extract state from the repository (required)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write the auto files")
    mode.add_argument("--check", action="store_true",
                      help="compute outputs and compare; write nothing; exit 1 on drift")
    args = parser.parse_args(argv)

    if not args.from_repository:
        parser.error("--from-repository is required")

    try:
        root = repo_root()
        record, _state, frozen = build_handoff_state(root)
        outputs = generate_from(record, frozen)
    except HandoffError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.write:
        _atomic_write(root, outputs)
        print("Handoff Package regenerated:")
        for rel in outputs:
            print(f"  - {rel}")
        return 0

    # --check: full semantic-projection comparison for the JSON, content compare
    # (minus volatile timestamp) for the markdown.
    drift = False
    state_path = os.path.join(root, "project/docs/ai/handoff_state.json")
    on_disk = _load_json(state_path)
    if on_disk is None or projection(on_disk) != projection(record):
        drift = True
        print("DRIFT: handoff_state.json (semantic projection differs)", file=sys.stderr)
    for rel, content in outputs.items():
        if rel.endswith("handoff_state.json"):
            continue
        disk = open(os.path.join(root, rel), encoding="utf-8").read() \
            if os.path.isfile(os.path.join(root, rel)) else None
        if _strip_volatile(disk) != _strip_volatile(content):
            drift = True
            print(f"DRIFT: {rel}", file=sys.stderr)
    if drift:
        print("Handoff Package is OUT OF DATE — run with --write.", file=sys.stderr)
        return 1
    print("Handoff Package is up to date.")
    return 0


def generate_from(record: dict, frozen: list[dict]) -> dict[str, str]:
    return {
        "project/docs/ai/handoff_state.json":
            json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        "project/docs/ai/CURRENT_STATE.md": render_current_state(record),
        "project/docs/ai/FROZEN_ASSETS.md": render_frozen_assets(frozen),
    }


def _load_json(path: str):
    if not os.path.isfile(path):
        return None
    try:
        return json.load(open(path, encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _strip_volatile(text: str | None) -> str:
    if text is None:
        return ""
    return "\n".join(l for l in text.splitlines() if "generated_at_utc" not in l)


_STAGE127_M2_GATE_REL = (
    "project/stage127/stage127_m2_market_data_gate_decision.json"
)
_STAGE127_M2_GATE_ACTION_ID = "stage127-m2-market-data-gate"
_STAGE127_M2_NEXT_ACTION_ON_PASS = "stage127-m2-incremental-evaluation"
_STAGE127_GATE_PASS = "PASS_FOR_M2_INCREMENTAL_EVALUATION"
_STAGE127_GATE_FAIL = "FAIL_M2_DATA_GATE"


def derive_stage127_m2_market_data_gate_markers(root: str) -> dict:
    """Recognize an EXECUTED Stage127 M2 market-data Gate.

    Narrow and fail-closed, mirroring the retained-design-freeze recognizer.
    Critically, this function never authorizes or starts M2: it advances
    ``next_research_action_id`` to the incremental-evaluation action ONLY when
    the Gate artifact itself records a PASS, and even then leaves
    ``m2_incremental_evaluation_authorized`` False, since that action requires
    its own separate human authorization. An UNRESOLVED or FAIL Gate keeps the
    pointer on the Gate itself (it must be re-executed / reviewed) and never
    marks M2 data as collected. Returns {} before the Gate has been executed.
    """
    path = os.path.join(root, _STAGE127_M2_GATE_REL)
    if not os.path.isfile(path):
        return {}
    try:
        gate = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"unreadable stage127 M2 gate artifact: {exc}") from exc

    if gate.get("decision_id") != _STAGE127_M2_GATE_ACTION_ID:
        raise HandoffError("stage127 M2 gate artifact decision_id mismatch")

    status = gate.get("gate_status")
    if status not in (
        _STAGE127_GATE_PASS, "FAIL_M2_DATA_GATE", "UNRESOLVED_M2_DATA_GATE",
    ):
        raise HandoffError(f"stage127 M2 gate status not recognized: {status!r}")

    # The Gate must never have performed modeling, and the firewall must hold.
    if gate.get("modeling_performed") is not False:
        raise HandoffError("stage127 M2 gate reports modeling_performed")
    if gate.get("model_fit_calls") != 0 or gate.get("prediction_calls") != 0:
        raise HandoffError("stage127 M2 gate reports model fit/prediction calls")
    fw = gate.get("final_test_firewall") or {}
    for key in (
        "final_test_unlocked", "final_test_access_authorized",
        "final_test_predictor_values_inspected",
        "final_test_target_values_inspected", "final_test_evaluation_performed",
    ):
        if fw.get(key) is not False:
            raise HandoffError(f"stage127 M2 gate firewall field {key} not False")
    if fw.get("final_test_locked") is not True:
        raise HandoffError("stage127 M2 gate does not report final_test_locked")

    passed = status == _STAGE127_GATE_PASS
    # RESOLVED means the Gate reached a TERMINAL OBSERVED DECISION. An observed
    # FAIL resolves the Gate just as an observed PASS does -- it is a real
    # scientific result, not an absence of one. Only UNRESOLVED (the evidence
    # required to decide was unavailable) leaves the Gate unresolved. Resolution
    # is deliberately NOT a synonym for admission: see
    # stage127_m2_block_admitted_for_modeling below.
    resolved = status in (_STAGE127_GATE_PASS, _STAGE127_GATE_FAIL)
    eligible = bool(
        (gate.get("eligibility_for_next_action") or {})
        .get("eligible_to_start_m2_incremental_evaluation")
    )
    if eligible and not passed:
        raise HandoffError(
            "stage127 M2 gate claims eligibility without a PASS status"
        )

    # Evidence collection/validation is a SEPARATE fact from block admission.
    # It is read from the Gate artifact's own immutable-delivery record, so a
    # failed Gate can never erase the fact that authoritative M2 market
    # evidence was obtained and independently revalidated.
    delivery = gate.get("external_delivery") or {}
    evidence_rows = int(delivery.get("normalized_row_count") or 0)
    evidence_collected = bool(
        evidence_rows > 0 and delivery.get("bundle_sha256")
    )
    evidence_validated = bool(
        evidence_collected
        and delivery.get("independently_revalidated_in_papermali")
        and delivery.get("external_qc_report_trusted") is False
    )

    markers = {
        "stage127_m2_market_data_gate_executed": True,
        "stage127_m2_market_data_gate_status": status,
        "stage127_m2_market_data_gate_resolved": resolved,
        "stage127_m2_market_data_gate_terminal_result_pending_human_review": (
            resolved and not passed
        ),
        "stage127_m2_block_admitted_for_modeling": passed,
        # Authoritative M2 market EVIDENCE state — independent of admission.
        "stage127_m2_market_data_evidence_collected": evidence_collected,
        "stage127_m2_market_data_evidence_validated": evidence_validated,
        "stage127_m2_market_data_evidence_bundle_sha256": (
            delivery.get("bundle_sha256") or ""
        ),
        "stage127_m2_market_data_evidence_observation_count": evidence_rows,
        "m2_incremental_evaluation_authorized": False,
        "m2_modeling_started": False,
        "m2_authorized": False,
        "m2_started": False,
        # NOTE ON SEMANTICS: in this schema `m2_data_collected` is a frozen
        # PROHIBITION marker, not a data-availability flag. It is pinned False
        # by the frozen Stage125 Part 4 SAP and the frozen Stage126 robustness
        # closure completion lock, and Stage125 Part 5's successor validator
        # treats flipping it to True as a handoff mutation VIOLATION. It means
        # "M2 data has entered the authorized M2 modeling pipeline", which
        # remains false and must remain false while M2 is unauthorized. It does
        # NOT mean "no M2 evidence exists" and it is NOT a restatement of the
        # Gate result -- that is what the explicit
        # stage127_m2_market_data_evidence_* markers above record.
        "m2_data_collected": False,
        "m2_data_collected_semantics": (
            "frozen_prohibition_marker_m2_data_entered_authorized_modeling_"
            "pipeline_not_evidence_availability"
        ),
        # Explicit HISTORICAL restatement of the same frozen Part 4 value, so
        # no reader can mistake it for live state. The live data-state fields
        # are the m2_market_data_evidence_* /
        # m2_data_entered_authorized_incremental_modeling_pipeline markers.
        "stage125_part4_m2_data_collected_historical": False,
        "stage125_part4_m2_data_collected_historical_semantics": (
            "Frozen Stage125 Part4 state at the time that SAP was created; "
            "not a live data-availability or execution marker."
        ),
        "paper_winner_selected": False,
        "final_model_selected": False,
        "full_development_refit_performed": False,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_predictor_values_inspected": False,
        "final_test_target_values_inspected": False,
        "final_test_evaluation_performed": False,
    }
    # An UNRESOLVED or FAIL Gate produced no admission decision, so the
    # research pointer must NOT advance past the Gate: the repository
    # invariant is that next_research_action_id comes strictly after
    # last_completed_research_action_id, and an unresolved Gate has not
    # completed. Only a PASS both completes the Gate and opens the (still
    # separately-authorized) incremental-evaluation action.
    if passed:
        markers["last_completed_research_action_id"] = _STAGE127_M2_GATE_ACTION_ID
        markers["next_research_action_id"] = _STAGE127_M2_NEXT_ACTION_ON_PASS
    return markers


_STAGE127_SEMANTICS_ADJUDICATION_REL = (
    "project/stage127/stage127_m2_trading_day_semantics_adjudication.json"
)
_STAGE127_SEMANTICS_IMPORT_QC_REL = (
    "project/stage127/stage127_m2_zero_trade_semantics_import_qc.json"
)
_STAGE127_ROOT_CAUSE_REL = (
    "project/stage127/stage127_m2_equity_return_root_cause_summary.json"
)
_STAGE127_SEMANTICS_OUTCOME_A = (
    "FROZEN_CONTRACT_UNAMBIGUOUS_CURRENT_IMPLEMENTATION_CONFORMANT"
)
_STAGE127_SEMANTICS_OUTCOMES = (
    _STAGE127_SEMANTICS_OUTCOME_A,
    "FROZEN_CONTRACT_UNAMBIGUOUS_IMPLEMENTATION_DEFECT",
    "SEMANTIC_AMBIGUITY_REQUIRES_HUMAN_DECISION",
)


def derive_stage127_m2_zero_trade_semantics_markers(root: str) -> dict:
    """Recognize a COMPLETED Stage127 zero-trade trading-day adjudication.

    Narrow and fail-closed, like the Gate recognizer. It records only the
    SEMANTIC state and can never authorize M2, admit a block, or alter the
    canonical Gate: an adjudication artifact that claims a Gate change, a model
    fit, a prediction or final-test access is rejected outright. Returns {}
    before the adjudication has been produced.
    """
    path = os.path.join(root, _STAGE127_SEMANTICS_ADJUDICATION_REL)
    if not os.path.isfile(path):
        return {}
    try:
        adj = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(
            f"unreadable stage127 semantics adjudication artifact: {exc}"
        ) from exc

    outcome = adj.get("adjudication_outcome")
    if outcome not in _STAGE127_SEMANTICS_OUTCOMES:
        raise HandoffError(
            f"stage127 semantics adjudication outcome not recognized: "
            f"{outcome!r}"
        )
    # The adjudication is diagnostic: it may never move a canonical result.
    for key in ("canonical_gate_changed", "t0_changed", "t_star_changed",
                "thresholds_changed", "features_changed",
                "frozen_stage125_contract_modified"):
        if adj.get(key) is not False:
            raise HandoffError(
                f"stage127 semantics adjudication reports {key} is not False"
            )
    if adj.get("model_fits") != 0 or adj.get("predictions_generated") != 0:
        raise HandoffError(
            "stage127 semantics adjudication reports model fits/predictions"
        )
    if adj.get("final_test_access") != 0:
        raise HandoffError(
            "stage127 semantics adjudication reports final-test access"
        )
    if adj.get("canonical_gate_status") != _STAGE127_GATE_FAIL:
        raise HandoffError(
            "stage127 semantics adjudication does not preserve the canonical "
            "Gate status"
        )

    qc_path = os.path.join(root, _STAGE127_SEMANTICS_IMPORT_QC_REL)
    if not os.path.isfile(qc_path):
        raise HandoffError(
            "stage127 semantics adjudication present without its import QC"
        )
    try:
        qc = json.load(open(qc_path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(
            f"unreadable stage127 semantics import QC: {exc}"
        ) from exc
    if qc.get("validator_pass") is not True:
        raise HandoffError("stage127 semantics import QC did not pass")
    if qc.get("external_qc_report_trusted") is not False:
        raise HandoffError(
            "stage127 semantics import QC trusts the external QC report"
        )
    provenance = qc.get("provenance") or {}
    if not (provenance.get("bundle_sha256_verified")
            and provenance.get("bundle_size_verified")):
        raise HandoffError(
            "stage127 semantics evidence bundle identity was not verified"
        )
    calendar = qc.get("calendar_point") or {}
    ranges = qc.get("calendar_range_vs_daily") or {}

    # The root-cause surface must agree that nothing is pending any more.
    pending = None
    rc_path = os.path.join(root, _STAGE127_ROOT_CAUSE_REL)
    if os.path.isfile(rc_path):
        try:
            rc = json.load(open(rc_path, encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HandoffError(f"unreadable stage127 root-cause summary: {exc}") from exc
        pending = int(rc.get("pending_external_tsetmc_adjudication_count") or 0)
        if rc.get("canonical_gate_status_unchanged") != _STAGE127_GATE_FAIL:
            raise HandoffError(
                "stage127 root-cause summary does not preserve the canonical "
                "Gate status"
            )

    conformant = adj.get("current_implementation_conformant")
    return {
        "stage127_m2_zero_trade_semantics_evidence_validated": True,
        "stage127_m2_zero_trade_semantics_bundle_sha256": (
            provenance.get("bundle_sha256") or ""
        ),
        "stage127_m2_zero_trade_semantics_bundle_filename": (
            provenance.get("bundle_filename") or ""
        ),
        "stage127_m2_zero_trade_semantics_raw_artifacts_sha256_verified": (
            (qc.get("raw") or {}).get("sha256_verified_count", 0)
        ),
        "stage127_m2_trading_day_semantics_adjudication_completed": True,
        "stage127_m2_trading_day_semantics_adjudication_outcome": outcome,
        "stage127_m2_current_implementation_conformant": conformant == "YES",
        "stage127_m2_semantics_pending_count": pending if pending is not None else 0,
        "stage127_m2_semantics_canonical_gate_changed": False,
        "stage127_m2_semantics_model_fits": 0,
        "stage127_m2_semantics_predictions_generated": 0,
        "stage127_m2_semantics_final_test_access": 0,
        "stage127_m2_point_dates_in_official_instrument_calendar": (
            calendar.get("point_present_in_official_instrument_calendar", 0)
        ),
        "stage127_m2_point_date_requests": (
            calendar.get("point_date_requests", 0)
        ),
        "stage127_m2_range_calendar_vs_daily_equal": (
            ranges.get("calendar_vs_daily_date_sets_equal", 0)
        ),
        "stage127_m2_range_requests": ranges.get("range_requests", 0),
        "stage127_m2_semantics_human_decision_required": True,
        # The adjudication changes NOTHING about authorization.
        "stage127_m2_block_admitted_for_modeling": False,
        "m2_incremental_evaluation_authorized": False,
        "m2_modeling_started": False,
    }


_STAGE128_M2_D2_FREEZE_REL = (
    "project/stage128/stage128_m2_d2_design_freeze.json"
)
_STAGE128_M2_D2_FREEZE_ACTION_ID = (
    "stage128-m2-boundary-month-return-design-freeze"
)
_NEXT_RESEARCH_ACTION_ID_AFTER_STAGE128_M2_D2_FREEZE = (
    "stage128-m2-d2-gate-rerun"
)
#: Live stage/workstream labels once the freeze is complete. The workstream id
#: is DERIVED FROM the frozen action and names the M2 D2 boundary-month
#: equity-return workstream it opened; it is not a new scientific action and
#: never substitutes for a research-action id.
_STAGE128_CURRENT_STAGE = "Stage128"
_STAGE128_ACTIVE_WORKSTREAM_ID = "stage128-m2-d2-boundary-month-equity-return"


def derive_stage128_m2_d2_design_freeze_markers(root: str) -> dict:
    """Recognize the (design-freeze-only) Stage128 M2 D2 amendment.

    Narrow, fail-closed recognition mirroring the Stage126 retained-design-
    freeze / Stage127 Gate recognizers above: if the freeze artifact is
    present and internally consistent (no canonical Gate execution, no M2
    admission, no model fit/prediction, no final-test access, historical
    Stage127 D0 result preserved), the Handoff's
    ``next_research_action_id`` advances to ``stage128-m2-d2-gate-rerun`` --
    itself requiring a SEPARATE future human authorization; this function
    never sets that authorization True and never marks M2 admitted or
    started. It never overwrites the historical
    ``stage127_m2_market_data_gate_status`` / ``..._block_admitted_for_
    modeling`` markers set above, which remain the D0 historical record.
    Returns {} before the freeze artifact has been built, so pre-freeze
    Handoffs (and any branch without ``project/stage128/``) are unaffected.
    """
    path = os.path.join(root, _STAGE128_M2_D2_FREEZE_REL)
    if not os.path.isfile(path):
        return {}
    try:
        freeze = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"unreadable stage128 M2 D2 freeze artifact: {exc}") from exc

    if freeze.get("decision_id") != _STAGE128_M2_D2_FREEZE_ACTION_ID:
        raise HandoffError("stage128 M2 D2 freeze artifact decision_id mismatch")
    if freeze.get("last_completed_research_action_id_if_this_pr_is_merged") != (
        _STAGE128_M2_D2_FREEZE_ACTION_ID
    ):
        raise HandoffError(
            "stage128 M2 D2 freeze artifact "
            "last_completed_research_action_id_if_this_pr_is_merged mismatch"
        )
    if freeze.get("next_research_action_id_if_this_pr_is_merged") != (
        _NEXT_RESEARCH_ACTION_ID_AFTER_STAGE128_M2_D2_FREEZE
    ):
        raise HandoffError(
            "stage128 M2 D2 freeze artifact "
            "next_research_action_id_if_this_pr_is_merged mismatch"
        )
    if freeze.get("historical_D0_gate_status") != _STAGE127_GATE_FAIL:
        raise HandoffError(
            "stage128 M2 D2 freeze artifact does not preserve the historical "
            "Stage127 D0 Gate status"
        )
    # Fail closed on a stale live workstream label. Once the freeze is
    # recognized the ROADMAP's CURRENT workstream pointer may not still name
    # the completed Stage126 M1 baseline. The M2 D2 label is correct only
    # while M2 D2 is the live workstream; once the M3 macro data Gate has been
    # EXECUTED, the live data workstream is the M3 Gate and the M2 D2 label
    # becomes predecessor context.
    roadmap_workstream = read_roadmap(root)["active_research_workstream_id"]
    m3_gate_executed = bool(
        derive_stage128_m3_macro_data_gate_markers(root).get(
            "stage128_m3_macro_data_gate_executed"))
    m3i2_locked = bool(
        derive_stage128_m3i2_contract_lock_markers(root).get(
            "stage128_m3i2_contract_lock_executed"))
    m3i2_evidence = bool(
        derive_stage128_m3i2_evidence_capture_markers(root).get(
            "stage128_m3i2_evidence_capture_executed"))
    m3i2_recovery = bool(
        derive_stage128_m3i2_final_documentary_recovery_markers(root).get(
            "stage128_m3i2_final_documentary_recovery_initiated"))
    if m3i2_recovery:
        allowed = _STAGE128_M3I2_RECOVERY_WORKSTREAM_ID
    elif m3i2_evidence:
        allowed = _STAGE128_M3I2_EVIDENCE_WORKSTREAM_ID
    elif m3i2_locked:
        allowed = _STAGE128_M3I2_ACTIVE_WORKSTREAM_ID
    else:
        allowed = (_STAGE128_M3_ACTIVE_WORKSTREAM_ID if m3_gate_executed
                   else _STAGE128_ACTIVE_WORKSTREAM_ID)
    if roadmap_workstream != allowed:
        raise HandoffError(
            f"stage128 M2 D2 freeze is complete but ROADMAP "
            f"active_research_workstream_id={roadmap_workstream!r} != "
            f"{allowed!r}"
            + (" (the M3 macro data Gate has executed, so the live workstream "
               "is the M3 Gate and the M2 D2 label is predecessor context)"
               if m3_gate_executed else "")
        )

    exact = {
        "canonical_gate_executed_in_this_action": False,
        "M2_admitted_in_this_action": False,
        "model_fits": 0,
        "predictions": 0,
        "final_test_access": 0,
        "target_values_accessed": 0,
        "shared_window_changed": False,
        "t0_changed": False,
        "T_star_changed": False,
        "trading_day_sequence_changed": False,
        "daily_return_adjacency_changed": False,
        "realized_volatility_changed": False,
        "amihud_illiquidity_changed": False,
        "stage128_m2_d2_gate_rerun_authorized": False,
        "M2_admitted": False,
        "M2_incremental_evaluation_authorized": False,
        "final_test_unlocked": False,
        "next_action_identified_does_not_mean_authorized": True,
    }
    for key, want in exact.items():
        if freeze.get(key) != want:
            raise HandoffError(
                f"stage128 M2 D2 freeze field {key}={freeze.get(key)!r} != {want!r}"
            )

    fw = freeze.get("final_test_firewall") or {}
    for key in (
        "final_test_unlocked", "final_test_access_authorized",
        "final_test_predictor_values_inspected",
        "final_test_target_values_inspected", "final_test_evaluation_performed",
    ):
        if fw.get(key) is not False:
            raise HandoffError(f"stage128 M2 D2 freeze firewall field {key} not False")
    if fw.get("final_test_locked") is not True:
        raise HandoffError("stage128 M2 D2 freeze does not report final_test_locked")

    sf = freeze.get("status_flags") or {}
    for key in (
        "canonical_gate_executed", "m2_admitted", "m2_started", "m3_started",
        "m4_started", "final_model_selected", "paper_winner_selected", "merged",
    ):
        if sf.get(key) is not False:
            raise HandoffError(f"stage128 M2 D2 freeze status_flags.{key} not False")
    if sf.get("design_freeze_completed") is not True:
        raise HandoffError(
            "stage128 M2 D2 freeze status_flags.design_freeze_completed not True"
        )

    return {
        "stage128_m2_d2_design_freeze_completed": True,
        "stage128_m2_d2_gate_rerun_authorized": False,
        # --- Stage127 human-review closure -------------------------------- #
        # Stage127's terminal FAIL result DID require a human decision about
        # which scientific roadmap action follows it. That decision has now
        # been made: the human supervisor separately authorized the Stage128
        # D2 boundary-month design freeze, which IS the answer to that
        # question. Once this freeze is recognized as completed, it is no
        # longer true that Stage127 is pending human review — so these two
        # markers are flipped False here (this recognizer is merged LAST, so
        # it overrides the Stage127 recognizers above). The historical facts
        # are preserved, not erased: `stage127_m2_market_data_gate_status`
        # remains FAIL_M2_DATA_GATE and is never touched here, and the two
        # markers below record that the review was originally required and
        # by which action it was discharged.
        "stage127_m2_market_data_gate_terminal_result_pending_human_review": (
            False
        ),
        "stage127_m2_semantics_human_decision_required": False,
        "stage127_m2_human_review_originally_required": True,
        "stage127_m2_human_review_resolved_by_action_id": (
            _STAGE128_M2_D2_FREEZE_ACTION_ID
        ),
        "last_completed_research_action_id": _STAGE128_M2_D2_FREEZE_ACTION_ID,
        "next_research_action_id": (
            _NEXT_RESEARCH_ACTION_ID_AFTER_STAGE128_M2_D2_FREEZE
        ),
        "m2_incremental_evaluation_authorized": False,
        "m2_modeling_started": False,
        "m2_authorized": False,
        "m2_started": False,
        "paper_winner_selected": False,
        "final_model_selected": False,
        "full_development_refit_performed": False,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_predictor_values_inspected": False,
        "final_test_target_values_inspected": False,
        "final_test_evaluation_performed": False,
    }


_STAGE128_M2_D2_GATE_RERUN_REL = (
    "project/stage128/stage128_m2_d2_gate_rerun_decision.json"
)
_STAGE128_M2_D2_GATE_RERUN_ACTION_ID = "stage128-m2-d2-gate-rerun"
_STAGE128_GATE_RERUN_PASS = "PASS_FOR_M2_INCREMENTAL_EVALUATION"
_STAGE128_GATE_RERUN_FAIL = "FAIL_M2_DATA_GATE"
#: Identified ONLY as a pointer if the re-run PASSes. A pointer is never an
#: authorization: `m2_incremental_evaluation_authorized` stays False.
_NEXT_RESEARCH_ACTION_ID_AFTER_STAGE128_M2_D2_GATE_RERUN_PASS = (
    "stage127-m2-incremental-evaluation"
)
#: On FAIL the pointer stays on the Gate re-run itself: inventing a new
#: scientific action in response to an observed negative result is exactly the
#: silent-redesign this recognizer must never perform.
_NEXT_RESEARCH_ACTION_ID_AFTER_STAGE128_M2_D2_GATE_RERUN_FAIL = (
    _STAGE128_M2_D2_GATE_RERUN_ACTION_ID
)


def derive_stage128_m2_d2_gate_rerun_markers(root: str) -> dict:
    """Recognize the executed Stage128 canonical M2 Gate re-run under D2.

    Narrow and fail-closed, mirroring the recognizers above. The Gate re-run
    is a DATA-ADMISSION decision only:

    * it never sets ``m2_incremental_evaluation_authorized`` or
      ``m2_modeling_started`` — a PASS makes the successor scientifically
      eligible for a NEW explicit human authorization, nothing more;
    * it never unlocks the final test;
    * it never touches ``stage127_m2_market_data_gate_status``, which remains
      the historical D0 ``FAIL_M2_DATA_GATE`` record;
    * the one-action human authorization is CONSUMED by the execution, so
      ``stage128_m2_d2_gate_rerun_authorized`` stays False afterwards and is
      never left standing.

    Returns {} before the Gate has been executed, so pre-rerun Handoffs are
    unaffected.
    """
    path = os.path.join(root, _STAGE128_M2_D2_GATE_RERUN_REL)
    if not os.path.isfile(path):
        return {}
    try:
        d = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"unreadable stage128 D2 Gate rerun decision: {exc}") from exc

    if d.get("decision_id") != _STAGE128_M2_D2_GATE_RERUN_ACTION_ID:
        raise HandoffError("stage128 D2 Gate rerun decision_id mismatch")
    status = d.get("gate_status")
    if status not in (_STAGE128_GATE_RERUN_PASS, _STAGE128_GATE_RERUN_FAIL):
        raise HandoffError(
            f"stage128 D2 Gate rerun status {status!r} is not terminal"
        )
    if d.get("historical_d0_gate_status") != _STAGE127_GATE_FAIL:
        raise HandoffError(
            "stage128 D2 Gate rerun does not preserve the historical Stage127 "
            "D0 Gate status"
        )
    if d.get("historical_d0_artifacts_rewritten") is not False:
        raise HandoffError("stage128 D2 Gate rerun claims to rewrite D0 artifacts")

    exact = {
        "modeling_performed": False,
        "model_fit_calls": 0,
        "prediction_calls": 0,
        "predictive_metric_computed": False,
        "m2_vs_m1_performance_compared": False,
        "gate_thresholds_changed": False,
        "gate_criteria_added_or_removed": False,
        "new_design_decision_made_in_this_action": False,
        "d0_d1_d2_d3_jalali_selection_reopened": False,
        "gate_outcome_used_to_redesign_d2": False,
    }
    for key, want in exact.items():
        if d.get(key) != want:
            raise HandoffError(
                f"stage128 D2 Gate rerun field {key}={d.get(key)!r} != {want!r}"
            )

    fw = d.get("final_test_firewall") or {}
    for key in (
        "final_test_unlocked", "final_test_access_authorized",
        "final_test_predictor_values_inspected",
        "final_test_target_values_inspected", "final_test_evaluation_performed",
    ):
        if fw.get(key) is not False:
            raise HandoffError(f"stage128 D2 Gate rerun firewall {key} not False")
    if fw.get("final_test_locked") is not True:
        raise HandoffError("stage128 D2 Gate rerun does not report final_test_locked")

    elig = d.get("eligibility_for_next_action") or {}
    if elig.get("m2_incremental_evaluation_authorized") is not False:
        raise HandoffError(
            "stage128 D2 Gate rerun must not authorize M2 incremental evaluation"
        )
    if elig.get("m2_modeling_started") is not False:
        raise HandoffError("stage128 D2 Gate rerun must not start M2 modeling")

    passed = status == _STAGE128_GATE_RERUN_PASS
    cov = (d.get("candidate_coverage") or {}).get("equity_return_window") or {}
    common = d.get("block_common_sample") or {}

    return {
        "stage128_m2_d2_gate_rerun_executed": True,
        "stage128_m2_d2_gate_rerun_resolved": True,
        "stage128_m2_d2_gate_rerun_status": status,
        # The one-action authorization was CONSUMED by this execution. It is
        # never left standing, whatever the outcome.
        "stage128_m2_d2_gate_rerun_authorized": False,
        "stage128_m2_d2_gate_rerun_authorization_consumed": True,
        "stage128_m2_d2_equity_return_valid_rows": cov.get("valid_rows"),
        "stage128_m2_d2_equity_return_coverage": cov.get("overall_coverage"),
        "stage128_m2_d2_common_sample_rows": common.get("common_usable_rows"),
        "stage128_m2_d2_common_sample_coverage": common.get("common_coverage"),
        # DATA admission only — never a statement that M2 improves prediction.
        "stage128_m2_d2_block_data_admission_passed": passed,
        "m2_block_admitted_for_modeling": False,
        "last_completed_research_action_id": (
            _STAGE128_M2_D2_GATE_RERUN_ACTION_ID
        ),
        "next_research_action_id": (
            _NEXT_RESEARCH_ACTION_ID_AFTER_STAGE128_M2_D2_GATE_RERUN_PASS
            if passed
            else _NEXT_RESEARCH_ACTION_ID_AFTER_STAGE128_M2_D2_GATE_RERUN_FAIL
        ),
        "next_research_action_pointer_is_not_authorization": True,
        # Nothing below is ever advanced by a data-admission Gate.
        "m2_incremental_evaluation_authorized": False,
        "m2_modeling_started": False,
        "m2_authorized": False,
        "m2_started": False,
        "paper_winner_selected": False,
        "final_model_selected": False,
        "full_development_refit_performed": False,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_predictor_values_inspected": False,
        "final_test_target_values_inspected": False,
        "final_test_evaluation_performed": False,
    }


_STAGE127_M2_INCREMENTAL_EVALUATION_REL = (
    "project/stage128/m2_incremental_evaluation/"
    "stage127_m2_incremental_evaluation_decision.json"
)
_STAGE127_M2_INCREMENTAL_EVALUATION_ACTION_ID = (
    "stage127-m2-incremental-evaluation"
)
#: After the paired M2-versus-M1 development comparison, the live question is a
#: HUMAN retained-block decision. Identifying it is a pointer only: it is not a
#: scientific authorization, it does not retain M2, and it never starts M3.
_NEXT_RESEARCH_ACTION_ID_AFTER_M2_INCREMENTAL_EVALUATION = (
    "stage128-m2-retained-block-human-decision"
)


def derive_stage127_m2_incremental_evaluation_markers(root: str) -> dict:
    """Recognize the executed, authorized paired M2-versus-M1 evaluation.

    Narrow and fail-closed. The action reports OBSERVED development evidence:

    * it never retains or rejects the M2 block — that stays a human decision;
    * it never selects a winner and never claims superiority;
    * its one-action human authorization is CONSUMED, so
      ``m2_incremental_evaluation_authorized`` returns to False afterwards;
    * it never unlocks the final test and never starts M3 or M4.

    Returns {} before the action has been executed.
    """
    path = os.path.join(root, _STAGE127_M2_INCREMENTAL_EVALUATION_REL)
    if not os.path.isfile(path):
        return {}
    try:
        d = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(
            f"unreadable stage127 M2 incremental evaluation decision: {exc}"
        ) from exc

    if d.get("decision_id") != _STAGE127_M2_INCREMENTAL_EVALUATION_ACTION_ID:
        raise HandoffError("stage127 M2 incremental evaluation decision_id mismatch")
    if d.get("gate_status_consumed") != _STAGE128_GATE_RERUN_PASS:
        raise HandoffError(
            "stage127 M2 incremental evaluation did not consume a passing D2 Gate"
        )
    if d.get("historical_d0_gate_status") != _STAGE127_GATE_FAIL:
        raise HandoffError(
            "stage127 M2 incremental evaluation does not preserve the historical "
            "D0 Gate status"
        )

    exact = {
        "winner_selected": False,
        "retained_block_selected": False,
        "m2_automatically_retained": False,
        "m2_automatically_rejected": False,
        "superiority_claimed": False,
        "causal_interpretation_made": False,
        "new_pass_fail_threshold_created": False,
        "design_changed_after_seeing_results": False,
        "authorizes_next_action": False,
        "m3_started": False,
        "m4_started": False,
        "merge_authorized": False,
        "human_retained_block_decision_required": True,
    }
    for key, want in exact.items():
        if d.get(key) != want:
            raise HandoffError(
                f"stage127 M2 incremental evaluation field {key}="
                f"{d.get(key)!r} != {want!r}"
            )

    fw = d.get("firewall") or {}
    for key in (
        "final_test_predictor_values_read", "final_test_target_values_read",
        "final_test_predictions", "final_test_model_fits",
        "full_development_refits", "m3_executions", "m4_executions",
    ):
        if fw.get(key) != 0:
            raise HandoffError(
                f"stage127 M2 incremental evaluation firewall {key}={fw.get(key)!r}"
            )
    for key in (
        "final_test_unlocked", "final_test_access_authorized",
        "final_test_evaluation_performed",
    ):
        if fw.get(key) is not False:
            raise HandoffError(
                f"stage127 M2 incremental evaluation firewall {key} not False"
            )
    if fw.get("final_test_locked") is not True:
        raise HandoffError(
            "stage127 M2 incremental evaluation does not report final_test_locked"
        )

    fits = d.get("primary_predictive_model_fits")
    if fits != 44:
        raise HandoffError(
            f"stage127 M2 incremental evaluation primary fit count {fits!r} != 44"
        )

    return {
        "stage127_m2_incremental_evaluation_executed": True,
        "stage127_m2_incremental_evaluation_completed": True,
        "stage127_m2_incremental_evaluation_authorization_consumed": True,
        # LIVE, unambiguous data-state fields. The frozen Stage125 Part 4
        # marker `m2_data_collected` stays False because flipping it is a
        # handoff-mutation violation of a frozen scientific artifact; it is
        # NOT the live truth and is republished only as clearly-labelled
        # historical schema state.
        "m2_market_data_evidence_collected": True,
        "m2_market_data_evidence_validated": True,
        "m2_data_entered_authorized_incremental_modeling_pipeline": True,
        "m2_incremental_evaluation_data_materialized": True,
        "stage127_m2_incremental_evaluation_common_sample_rows": d.get(
            "common_sample_rows"),
        "stage127_m2_incremental_evaluation_pooled_oof_rows": d.get(
            "pooled_oof_rows"),
        "stage127_m2_incremental_evaluation_primary_model_fits": fits,
        "stage127_m2_families_agree_on_direction": d.get(
            "families_agree_on_direction"),
        "last_completed_research_action_id": (
            _STAGE127_M2_INCREMENTAL_EVALUATION_ACTION_ID
        ),
        "next_research_action_id": (
            _NEXT_RESEARCH_ACTION_ID_AFTER_M2_INCREMENTAL_EVALUATION
        ),
        "next_research_action_pointer_is_not_authorization": True,
        # AUTHORIZATION, EXECUTION and RETENTION are three different things.
        #
        # The one-action authorization was CONSUMED by this execution, so the
        # authorization flag is False again. That False must never be read as
        # "M2 modeling never happened": the authorized development modeling
        # WAS executed (44 canonical primary fits), so the execution flags are
        # True. Retention remains undecided and stays False.
        "m2_incremental_evaluation_authorized": False,
        "m2_started": True,
        "m2_modeling_started": True,
        "m2_block_retained": False,
        "m2_retained_block_decision_required": True,
        "m2_authorized": False,
        # Truthful live admission field: the D2 Gate passed and the authorized
        # incremental models were actually fitted on the admitted block.
        "m2_block_admitted_for_modeling": True,
        "m2_block_admitted_for_authorized_incremental_evaluation": True,
        "paper_winner_selected": False,
        "final_model_selected": False,
        "full_development_refit_performed": False,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_predictor_values_inspected": False,
        "final_test_target_values_inspected": False,
        "final_test_evaluation_performed": False,
        "m3_started": False,
        "m3_authorized": False,
        "m4_started": False,
        "m4_authorized": False,
    }


#: Once the M3 macro data Gate has EXECUTED, this is the live research/data
#: workstream label. Gate execution is a DATA workstream, never modeling.
_STAGE128_M3I2_MAIN_BRANCH = "main"
_STAGE128_M3I2_PREDECESSOR_BRANCH = "stage128-m3-macro-data-gate"
_STAGE128_M3I2_PROVENANCE_BASELINE_COMMIT = (
    "e6db63fb7d105f0d3a39db101c9e364161c367e9")
_STAGE128_M3I2_PREDECESSOR_MERGE_COMMIT = (
    "b94f73fab99b5c3bc5c55ea7c14736f2bddb516a")
_STAGE128_M3_ACTIVE_WORKSTREAM_ID = "stage128-m3-macro-data-gate"

_STAGE128_M3_MACRO_DATA_GATE_REL = (
    "project/stage128/m3_macro_data_gate/"
    "stage128_m3_macro_data_gate_decision.json"
)
_STAGE128_M3_MACRO_DATA_GATE_ACTION_ID = "stage128-m3-macro-data-gate"
_STAGE128_M3_GATE_STATUS_VOCABULARY = (
    "PASS_FOR_M3_INCREMENTAL_EVALUATION",
    "FAIL_M3_DATA_GATE",
    "UNRESOLVED_M3_DATA_GATE",
)
#: Advanced ONLY when the Gate PASSES. A pointer is never an authorization.
_NEXT_RESEARCH_ACTION_ID_AFTER_M3_GATE_PASS = (
    "stage128-m3-incremental-evaluation"
)


def derive_stage128_m3_macro_data_gate_markers(root: str) -> dict:
    """Recognize the executed M3 macro DATA-ADMISSION Gate.

    Narrow and fail-closed. The Gate is data admission only:

    * it never fits a model, predicts, or computes a predictive metric;
    * it never executes an M3-versus-M2 comparison;
    * a PASS would be data admission, never a superiority claim;
    * the research pointer advances ONLY on PASS;
    * M3 modeling, M4 and the final test are untouched in every outcome.

    Returns {} before the Gate has been executed.
    """
    path = os.path.join(root, _STAGE128_M3_MACRO_DATA_GATE_REL)
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)

    if d.get("action_id") != _STAGE128_M3_MACRO_DATA_GATE_ACTION_ID:
        raise HandoffError("stage128 M3 macro data Gate action_id mismatch")
    status = d.get("gate_status")
    if status not in _STAGE128_M3_GATE_STATUS_VOCABULARY:
        raise HandoffError(
            f"stage128 M3 macro data Gate status {status!r} outside the "
            f"locked vocabulary {_STAGE128_M3_GATE_STATUS_VOCABULARY}")
    passed = status == "PASS_FOR_M3_INCREMENTAL_EVALUATION"

    for field, expected in (
        ("m3_incremental_evaluation_authorized", False),
        ("m3_modeling_started", False),
        ("m4_authorized", False),
        ("m4_started", False),
        ("final_test_locked", True),
        ("final_test_access_authorized", False),
        ("final_test_evaluation_performed", False),
        ("m3_macro_data_gate_authorization_consumed", True),
    ):
        if d.get(field) is not expected:
            raise HandoffError(
                f"stage128 M3 macro data Gate {field} must be {expected}")
    for field in ("model_fits", "predictions", "predictive_metrics_computed",
                  "m3_versus_m2_evaluations"):
        if d.get(field) != 0:
            raise HandoffError(
                f"stage128 M3 macro data Gate {field} must be 0")
    if d.get("m3_block_admitted_for_incremental_evaluation") is not passed:
        raise HandoffError(
            "stage128 M3 block admission must track the PASS status exactly")
    if passed and d.get("next_research_action_id") != (
            _NEXT_RESEARCH_ACTION_ID_AFTER_M3_GATE_PASS):
        raise HandoffError(
            "stage128 M3 Gate PASS must point at "
            f"{_NEXT_RESEARCH_ACTION_ID_AFTER_M3_GATE_PASS}")
    if not passed and d.get("next_research_action_id") == (
            _NEXT_RESEARCH_ACTION_ID_AFTER_M3_GATE_PASS):
        raise HandoffError(
            "stage128 M3 Gate did not PASS, so the research pointer must not "
            "advance to the incremental evaluation")

    parent = d.get("parent_surface") or {}
    markers = {
        "stage128_m3_macro_data_gate_executed": True,
        "stage128_m3_macro_data_gate_status": status,
        "stage128_m3_macro_data_gate_authorization_consumed": True,
        "m3_macro_data_gate_executed": True,
        "m3_macro_data_gate_status": status,
        "m3_data_workstream_started": True,
        # Gate execution is NOT modeling. These stay false in every outcome.
        "m3_incremental_evaluation_authorized": False,
        "m3_modeling_started": False,
        "m3_block_admitted_for_incremental_evaluation": passed,
        "m3_macro_data_gate_human_review_required": not passed,
        "m3_macro_data_gate_parent_rows": parent.get("parent_rows"),
        "m3_macro_data_gate_unresolved_reason_count": len(
            d.get("unresolved_or_blocker_reasons") or []),
        "m4_authorized": False,
        "m4_started": False,
        "final_test_locked": True,
    }
    if passed:
        markers["last_completed_research_action_id"] = (
            _STAGE128_M3_MACRO_DATA_GATE_ACTION_ID)
        markers["next_research_action_id"] = (
            _NEXT_RESEARCH_ACTION_ID_AFTER_M3_GATE_PASS)
        markers["next_research_action_pointer_is_not_authorization"] = True
    return markers


#: Once the supplementary M3I-2 contract has been prospectively locked, this
#: is the live workstream label. A CONTRACT lock is metadata only: no macro
#: observation is retrieved, no Data Gate runs and no modeling starts.
_STAGE128_M3I2_EVIDENCE_ACTION_ID = (
    "stage128-m3i2-official-source-evidence-capture")
_STAGE128_M3I2_EVIDENCE_WORKSTREAM_ID = (
    "stage128-m3i2-official-source-evidence-capture")
_STAGE128_M3I2_EVIDENCE_DECISION_REL = (
    "project/stage128/m3i2_official_source_evidence_capture/"
    "stage128_m3i2_official_source_evidence_decision.json")
#: `m3i2_retrieval_started` is a CONTRACT-LOCK-TIME marker that is retained at
#: False for retrieval compatibility. It does NOT mean "no official source was
#: ever retrieved" — the separate evidence-capture action superseded it.
_STAGE128_M3I2_RETRIEVAL_MARKER_SEMANTICS = (
    "contract_lock_time_marker_superseded_by_official_source_evidence_capture")
_STAGE128_M3I2_EVIDENCE_STATUSES = (
    "EVIDENCE_COMPLETE_FOR_SEPARATE_M3I2_DATA_GATE_REVIEW",
    "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE",
    "INVALID_OFFICIAL_SOURCE_EVIDENCE_CAPTURE",
)


def derive_stage128_m3i2_evidence_capture_markers(root: str) -> dict:
    """Markers for the M3I-2 official-source evidence capture.

    Evidence capture is acquisition, not admission: it produces hashed official
    source material and answers nothing about coverage, the Data Gate or
    modeling. Every marker below therefore keeps the scientific state exactly
    where the contract lock left it.
    """
    path = os.path.join(root, _STAGE128_M3I2_EVIDENCE_DECISION_REL)
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)

    if d.get("action_id") != _STAGE128_M3I2_EVIDENCE_ACTION_ID:
        raise HandoffError("stage128 M3I-2 evidence-capture action_id mismatch")
    status = d.get("m3i2_official_source_evidence_status")
    if status not in _STAGE128_M3I2_EVIDENCE_STATUSES:
        raise HandoffError(f"unknown M3I-2 evidence status {status!r}")
    for field, expected in (
        ("data_gate_passed", False),
        ("m3i2_admitted", False),
        ("m3i3_admitted", False),
        ("m3i3_contract_null_fields_populated", False),
        ("final_test_locked", True),
        ("final_test_access_authorized", False),
        ("m4_authorized", False),
        ("m4_started", False),
        ("merge_authorized", False),
        ("next_research_action_authorized", False),
    ):
        if d.get(field) is not expected:
            raise HandoffError(
                f"stage128 M3I-2 evidence capture {field} must be {expected}")
    for field in ("company_macro_joins", "feature_materializations",
                  "coverage_calculations", "data_gate_executions",
                  "model_fits", "predictions", "predictive_metrics",
                  "holm_calculations", "final_test_rows_read"):
        if d.get(field) != 0:
            raise HandoffError(
                f"stage128 M3I-2 evidence capture {field} must be 0")
    if d.get("m3_cbi_status") != "UNRESOLVED_M3_DATA_GATE":
        raise HandoffError(
            "the M3I-2 evidence capture must preserve the M3-CBI Gate status")

    summary = d.get("evidence_summary") or {}
    return {
        "stage128_m3i2_evidence_capture_executed": True,
        # LIVE retrieval fact. Official-source material WAS requested, retained
        # and hashed under this separate action. This is acquisition only: it
        # is not a Data Gate, not coverage and not an admission.
        "stage128_m3i2_official_source_retrieval_completed": True,
        # The contract-time marker `m3i2_retrieval_started` stays False for
        # backwards compatibility; this field says what that False means.
        "m3i2_retrieval_started_semantics": (
            _STAGE128_M3I2_RETRIEVAL_MARKER_SEMANTICS),
        "stage128_m3i2_evidence_status": status,
        "stage128_m3i2_evidence_result_code": d.get("result_code"),
        "stage128_m3i2_financing_metadata_decision": d.get(
            "m3i3_financing_metadata_decision"),
        "stage128_m3i2_official_responses_retained": summary.get(
            "official_responses_retained"),
        "stage128_m3i2_official_requests_attempted": summary.get(
            "official_requests_attempted"),
        "stage128_m3i2_official_responses_successful": summary.get(
            "official_responses_successful"),
        "stage128_m3i2_archive_editions_captured": summary.get(
            "archive_editions_captured"),
        "stage128_m3i2_wdi_editions_discovered": summary.get(
            "wdi_editions_discovered"),
        "stage128_m3i2_editions_with_verified_release_date": summary.get(
            "editions_with_verified_release_date"),
        "stage128_m3i2_unique_development_cutoffs": summary.get(
            "unique_development_cutoffs"),
        "stage128_m3i2_development_pairs_behind_cutoff_plan": summary.get(
            "development_pairs_behind_cutoff_plan"),
        "stage128_m3i2_development_pairs_without_verified_pre_cutoff_edition":
            summary.get(
                "development_pairs_without_verified_pre_cutoff_edition"),
        "stage128_m3i2_cpi_semantic_pass_count": summary.get(
            "cpi_semantic_pass_count"),
        "stage128_m3i2_fx_semantic_unresolved_count": summary.get(
            "fx_semantic_unresolved_count"),
        "stage128_m3i2_locked_series_rows_extracted": summary.get(
            "locked_series_rows_extracted"),
        "stage128_m3i2_raw_bytes_retained": summary.get("raw_bytes_total"),
        "stage128_m3i2_required_editions_total": summary.get(
            "required_editions_total"),
        "stage128_m3i2_required_editions_captured": summary.get(
            "required_editions_captured"),
        "stage128_m3i2_cutoffs_without_verified_pre_cutoff_edition":
            summary.get("cutoffs_without_verified_pre_cutoff_edition"),
        "stage128_m3i2_external_bundle_available_for_handoff": summary.get(
            "external_bundle_available_for_handoff"),
        # Acquisition never moves the scientific state.
        "m3i2_data_gate_executed": False,
        "m3i2_block_admitted": False,
        "m3i2_modeling_started": False,
        "m3i3_admitted": False,
        "m4_authorized": False,
        "m4_started": False,
        "final_test_locked": True,
        "last_completed_research_action_id": _STAGE128_M3I2_EVIDENCE_ACTION_ID,
        "next_research_action_id": d.get("next_research_action_id"),
        "next_research_action_authorized": False,
        "next_research_action_pointer_is_not_authorization": True,
    }


_STAGE128_M3I2_INDEPENDENT_AUDIT_REL = (
    "project/stage128/m3i2_official_source_evidence_capture/"
    "stage128_m3i2_independent_bundle_integrity_audit_record.json"
)
_STAGE128_M3I2_INDEPENDENT_AUDIT_RECORD_TYPE = (
    "post_capture_independent_bundle_integrity_audit")
_STAGE128_M3I2_INDEPENDENT_AUDIT_VERIFICATION_TYPE = (
    "external_independent_bundle_integrity_audit")
_STAGE128_M3I2_INDEPENDENT_AUDIT_PASS = (
    "INDEPENDENT_BUNDLE_INTEGRITY_AUDIT_PASS")
#: The audited object is pinned: this PR, at this head, and nothing else.
_STAGE128_M3I2_AUDITED_PR_NUMBER = 75
_STAGE128_M3I2_AUDITED_PR_HEAD_SHA = (
    "187c628a17f6e429fbf6455412f5f655d2f3602e")
#: Integrity only — the audit may claim exactly this scope, no more.
_STAGE128_M3I2_AUDIT_SCOPE_INCLUDES = (
    "bundle_integrity",
    "sha256",
    "zip_crc",
    "multipart_structure",
    "manifest_consistency",
    "official_source_restrictions",
    "raw_member_integrity",
)
#: ...and must keep exactly these outside its scope.
_STAGE128_M3I2_AUDIT_SCOPE_EXCLUDES = (
    "coverage",
    "data_gate",
    "m3i2_admission",
    "modeling",
    "final_test",
)


def derive_stage128_m3i2_independent_bundle_audit_markers(root: str) -> dict:
    """Markers for the post-capture independent bundle-integrity audit.

    The audit is a read-only integrity check of the already-produced external
    evidence bundle, performed by an auditor independent of the PR author and
    of the bundle creator. Integrity is not admission: a PASS says the bytes
    are the bytes that were captured, and says nothing about coverage, the
    Data Gate, M3I-2 admission, modeling or the Final Test. Fail-closed — the
    record must restate every excluded marker at its unmoved value.
    """
    path = os.path.join(root, _STAGE128_M3I2_INDEPENDENT_AUDIT_REL)
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)

    if d.get("record_type") != _STAGE128_M3I2_INDEPENDENT_AUDIT_RECORD_TYPE:
        raise HandoffError("M3I-2 independent audit record_type mismatch")
    if d.get("verification_type") != (
            _STAGE128_M3I2_INDEPENDENT_AUDIT_VERIFICATION_TYPE):
        raise HandoffError("M3I-2 independent audit verification_type mismatch")
    if d.get("overall_result") != _STAGE128_M3I2_INDEPENDENT_AUDIT_PASS:
        raise HandoffError("unknown M3I-2 independent audit overall_result")
    for field, expected in (
        ("independent_audit_completed", True),
        ("independently_verified_by_auditor", True),
        # Integrity findings — every one must be an explicit PASS. A missing
        # field is a failure, never an optimistic default.
        ("all_part_hashes_match", True),
        ("all_zip_crc_checks_pass", True),
        ("all_zip_structures_valid", True),
        ("primary_members_unique", True),
        ("all_member_hashes_match", True),
        ("all_member_sizes_match", True),
        ("third_invocation_present", False),
        ("official_hosts_only", True),
        ("original_single_bundle_present", True),
        ("original_single_bundle_directly_rechecked", True),
        ("original_single_bundle_hash_match", True),
        # Provenance of the audit claim itself.
        ("capture_time_values_superseded_by_this_record", True),
        ("audit_result_relies_on_prior_session_execution_by_auditor", True),
        ("auditor_independent_from_pr_author", True),
        ("auditor_independent_from_bundle_creator", True),
        ("auditor_participated_in_artifact_creation", False),
        # Integrity only — the scientific state stays exactly where the
        # evidence capture left it.
        ("m3i2_admitted", False),
        ("data_gate_executed", False),
        ("final_test_locked", True),
        ("merge_authorized", False),
        ("m4_authorized", False),
        ("modeling_started", False),
        ("historical_vintage_problem_resolved", False),
        # Provenance: capture-time manifest values are retained, not rewritten.
        ("capture_time_manifest_retained_unmodified", True),
        ("capture_time_delivered_to_independent_auditor", False),
        ("capture_time_independently_verified_by_auditor", False),
    ):
        if d.get(field) is not expected:
            raise HandoffError(
                f"M3I-2 independent bundle audit {field} must be {expected}")
    for field, expected in (
        # Member accounting: all 24 primary members expected and found.
        ("primary_members_expected", 24),
        ("primary_members_found", 24),
        # Official traffic: 21 requests, 21 responses, all successful.
        ("request_count", 21),
        ("response_count", 21),
        ("successful_response_count", 21),
        ("failed_response_count", 0),
        # Exactly the two recorded capture invocations, no third.
        ("capture_invocations", 2),
        # The audited object is pinned; an audit of some other head is not
        # an audit of this PR.
        ("pr_number", _STAGE128_M3I2_AUDITED_PR_NUMBER),
        ("audited_pr_head_sha", _STAGE128_M3I2_AUDITED_PR_HEAD_SHA),
    ):
        if d.get(field) != expected:
            raise HandoffError(
                f"M3I-2 independent bundle audit {field} must be {expected!r}")
    if d.get("audit_scope_includes") != list(
            _STAGE128_M3I2_AUDIT_SCOPE_INCLUDES):
        raise HandoffError(
            "M3I-2 independent bundle audit scope_includes mismatch")
    if d.get("audit_scope_excludes") != list(
            _STAGE128_M3I2_AUDIT_SCOPE_EXCLUDES):
        raise HandoffError(
            "M3I-2 independent bundle audit scope_excludes mismatch")
    if d.get("m3i2_evidence_status") != "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE":
        raise HandoffError(
            "the M3I-2 independent bundle audit must preserve the UNRESOLVED "
            "official-source evidence status")
    for field in ("network_requests", "company_macro_joins",
                  "feature_materializations", "coverage_calculations",
                  "data_gate_executions", "model_fits", "predictions",
                  "predictive_metrics", "holm_calculations",
                  "final_test_rows_read"):
        if d.get(field) != 0:
            raise HandoffError(
                f"M3I-2 independent bundle audit {field} must be 0")

    return {
        "stage128_m3i2_independent_bundle_integrity_audit":
            _STAGE128_M3I2_INDEPENDENT_AUDIT_PASS,
        "stage128_m3i2_independent_bundle_audit_verification_type":
            _STAGE128_M3I2_INDEPENDENT_AUDIT_VERIFICATION_TYPE,
        "stage128_m3i2_independent_audit_completed": True,
        "stage128_m3i2_independently_verified_by_auditor": True,
        "stage128_m3i2_auditor_independent_from_pr_author": True,
        "stage128_m3i2_auditor_independent_from_bundle_creator": True,
        "stage128_m3i2_auditor_participated_in_artifact_creation": False,
        "stage128_m3i2_auditor_identity_disclosure_status": d.get(
            "auditor_identity_disclosure_status"),
        "stage128_m3i2_audited_pr_number": d.get("pr_number"),
        "stage128_m3i2_audited_pr_head_sha": d.get("audited_pr_head_sha"),
        "stage128_m3i2_audit_primary_members_expected": d.get(
            "primary_members_expected"),
        "stage128_m3i2_audit_primary_members_found": d.get(
            "primary_members_found"),
        "stage128_m3i2_audit_capture_time_manifest_superseded": d.get(
            "capture_time_values_superseded_by_this_record"),
        # An integrity PASS moves nothing scientific.
        "stage128_m3i2_evidence_status": d.get("m3i2_evidence_status"),
        "m3i2_block_admitted": False,
        "m3i2_data_gate_executed": False,
        "m3i2_modeling_started": False,
        "stage128_m3i2_merge_authorized": False,
        "m4_authorized": False,
        "final_test_locked": True,
    }


_STAGE128_M3I2_RECOVERY_PKG = (
    "project/stage128/m3i2_final_official_documentary_recovery")
_STAGE128_M3I2_RECOVERY_ACTION_ID = (
    "stage128-m3i2-final-official-documentary-recovery-initiation")
_STAGE128_M3I2_RECOVERY_WORKSTREAM_ID = (
    "stage128-m3i2-final-official-documentary-recovery")
_STAGE128_M3I2_RECOVERY_DECISION_REL = (
    f"{_STAGE128_M3I2_RECOVERY_PKG}/"
    "stage128_m3i2_final_official_documentary_recovery_decision.json")
_STAGE128_M3I2_RECOVERY_CONTRACT_REL = (
    f"{_STAGE128_M3I2_RECOVERY_PKG}/"
    "stage128_m3i2_final_official_documentary_recovery_contract.json")
_STAGE128_M3I2_RECOVERY_SUBMISSION_REL = (
    f"{_STAGE128_M3I2_RECOVERY_PKG}/"
    "stage128_m3i2_world_bank_inquiry_submission_record.json")
_STAGE128_M3I2_RECOVERY_SUPERSESSION_REL = (
    f"{_STAGE128_M3I2_RECOVERY_PKG}/"
    "stage128_m3_lag_partial_local_execution_supersession_record.json")
_STAGE128_M3I2_RECOVERY_QC_REL = (
    f"{_STAGE128_M3I2_RECOVERY_PKG}/"
    "stage128_m3i2_final_official_documentary_recovery_qc_report.json")
_STAGE128_M3I2_RECOVERY_TOPOLOGY_REL = (
    f"{_STAGE128_M3I2_RECOVERY_PKG}/"
    "stage128_m3i2_final_official_documentary_recovery_pr_topology.json")

#: Submission outcomes this initiation may legitimately record. The third value
#: is written only by the SEPARATE human-submission recording action: the
#: initiation itself could never reach it, because automation must not sign in.
_STAGE128_M3I2_RECOVERY_SUBMISSION_STATUSES = (
    "OFFICIAL_INQUIRY_SUBMITTED_PENDING_RESPONSE",
    "HUMAN_SUBMISSION_REQUIRED",
    "SUBMITTED_ACKNOWLEDGED_WAITING_FOR_SUBSTANTIVE_RESPONSE",
)
#: An acknowledgement is a receipt, never an answer.
_STAGE128_M3I2_HUMAN_SUBMITTED_STATUS = (
    "SUBMITTED_ACKNOWLEDGED_WAITING_FOR_SUBSTANTIVE_RESPONSE")
_STAGE128_M3I2_RECOVERY_SEARCH_OUTCOMES = (
    "OFFICIAL_DOCUMENTARY_EVIDENCE_FOUND_DURING_BOUNDED_SEARCH",
    "NO_NEW_DOCUMENTARY_EVIDENCE_IN_BOUNDED_SEARCH",
)
#: Pointer only, and explicitly NOT an authorization. This maps the LIVE
#: submission status onto the pointer the FROZEN initiation decision recorded,
#: so the decision record is never rewritten when the world moves on: once a
#: human has submitted, the initiation's own "next action" is still the human
#: submission — that action is simply COMPLETE. The live pointer that succeeds
#: it is derived from the human-submission package instead.
_NEXT_ACTION_AFTER_RECOVERY_BY_SUBMISSION_STATUS = {
    "OFFICIAL_INQUIRY_SUBMITTED_PENDING_RESPONSE":
        "stage128-m3i2-final-official-response-adjudication",
    "HUMAN_SUBMISSION_REQUIRED":
        "stage128-m3i2-final-official-inquiry-human-submission",
    _STAGE128_M3I2_HUMAN_SUBMITTED_STATUS:
        "stage128-m3i2-final-official-inquiry-human-submission",
}


def derive_stage128_m3i2_final_documentary_recovery_markers(root: str) -> dict:
    """Recognize the M3I-2 final official documentary recovery INITIATION.

    Narrow and fail-closed. The action is an INITIATION only:

    * it repeats no part of the prior capture and re-downloads no archive ZIP;
    * it runs a bounded official documentary search (ceiling enforced here as
      well as in the capture layer) and may attempt at most ONE inquiry;
    * it executes no Data Gate, computes no coverage, materializes no feature,
      fits no model and never touches the Final Test;
    * it never admits M3I-2 and never contract-locks M3-LAG-WDI;
    * the superseded local M3-LAG draft stays non-authoritative.

    Returns {} before the recovery package exists.
    """
    decision_path = os.path.join(root, _STAGE128_M3I2_RECOVERY_DECISION_REL)
    if not os.path.isfile(decision_path):
        return {}
    parts = {}
    for key, rel in (
        ("decision", _STAGE128_M3I2_RECOVERY_DECISION_REL),
        ("contract", _STAGE128_M3I2_RECOVERY_CONTRACT_REL),
        ("submission", _STAGE128_M3I2_RECOVERY_SUBMISSION_REL),
        ("supersession", _STAGE128_M3I2_RECOVERY_SUPERSESSION_REL),
        ("qc", _STAGE128_M3I2_RECOVERY_QC_REL),
        ("topology", _STAGE128_M3I2_RECOVERY_TOPOLOGY_REL),
    ):
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            raise HandoffError(
                f"the M3I-2 documentary recovery package is missing {rel}")
        with open(path, encoding="utf-8") as fh:
            parts[key] = json.load(fh)
    decision, contract = parts["decision"], parts["contract"]
    submission, supersession = parts["submission"], parts["supersession"]
    qc, topology = parts["qc"], parts["topology"]

    if decision.get("action_id") != _STAGE128_M3I2_RECOVERY_ACTION_ID:
        raise HandoffError("M3I-2 documentary recovery action_id mismatch")
    if qc.get("all_pass") is not True or qc.get("failed_count") != 0:
        raise HandoffError("the M3I-2 documentary recovery QC must be green")

    status = submission.get("submission_status")
    if status not in _STAGE128_M3I2_RECOVERY_SUBMISSION_STATUSES:
        raise HandoffError(f"unknown M3I-2 inquiry submission status {status!r}")
    outcome = decision.get("bounded_search_outcome")
    if outcome not in _STAGE128_M3I2_RECOVERY_SEARCH_OUTCOMES:
        raise HandoffError(f"unknown bounded-search outcome {outcome!r}")

    # Bounds.
    executed = contract.get("official_documentary_get_requests_executed")
    ceiling = contract.get("official_documentary_get_requests_max")
    if ceiling != 20 or not isinstance(executed, int) or executed > ceiling:
        raise HandoffError(
            "the bounded documentary search ceiling (20) is violated")
    if submission.get("initial_inquiry_max_count") != 1:
        raise HandoffError("at most ONE initial inquiry may ever be attempted")
    for field in ("initial_inquiries_attempted",
                  "initial_inquiries_successfully_submitted"):
        if submission.get(field) not in (0, 1):
            raise HandoffError(f"M3I-2 inquiry {field} must be 0 or 1")
    if status == "HUMAN_SUBMISSION_REQUIRED":
        if submission.get("initial_inquiries_successfully_submitted") != 0:
            raise HandoffError(
                "a human submission is required, so nothing was submitted")
        for field in ("submission_timestamp_utc", "ticket_id_redacted",
                      "ticket_id_sha256"):
            if submission.get(field) is not None:
                raise HandoffError(
                    f"no {field} may exist without a successful submission")
    elif status == _STAGE128_M3I2_HUMAN_SUBMITTED_STATUS:
        # A human submitted it exactly once. Everything the Help Desk did NOT
        # show must stay absent rather than be reconstructed.
        for field, expected in (
            ("initial_inquiries_attempted", 1),
            ("initial_inquiries_successfully_submitted", 1),
            ("acknowledgement_received", True),
            ("substantive_response_received", False),
            ("human_authenticated_submission", True),
            ("external_raw_confirmation_present", True),
            ("ticket_id_present", False),
            ("follow_up_attempted", 0),
            ("attachments_selected_before_submission", True),
            # the confirmation e-mail never enumerated the attachments, and the
            # body was seen but not verified byte-for-byte from raw source
            ("attachments_server_confirmation_enumerated", False),
            ("body_hash_byte_verified_from_raw_email_source", False),
            ("automatic_follow_up_forbidden", True),
            ("follow_up_before_2026_08_21_forbidden", True),
            ("waiting_period_status", "ACTIVE"),
        ):
            if submission.get(field) != expected:
                raise HandoffError(
                    f"M3I-2 inquiry {field} must be {expected!r} once the "
                    "human submission is recorded")
        # The confirmation UI displayed no timezone, so no UTC instant exists.
        for field in ("submission_timestamp_utc",
                      "submission_timestamp_display_timezone",
                      "ticket_id_redacted", "ticket_id_sha256"):
            if submission.get(field) is not None:
                raise HandoffError(
                    f"{field} was never displayed and must not be invented")
        if submission.get("submission_timestamp_utc_status") != (
                "UNRESOLVED_CONFIRMATION_UI_DID_NOT_DISPLAY_TIMEZONE"):
            raise HandoffError(
                "the unresolved UTC timestamp status must be recorded exactly")
        if submission.get("submission_calendar_date") != "2026-08-06":
            raise HandoffError("the displayed submission date is 2026-08-06")
        if submission.get("waiting_period_completion_date") != "2026-08-20":
            raise HandoffError(
                "10 business days from 2026-08-06 completes on 2026-08-20")
        if submission.get("follow_up_earliest_calendar_date") != "2026-08-21":
            raise HandoffError(
                "the earliest possible follow-up date is 2026-08-21")
        if submission.get("canonical_body_sha256") != submission.get(
                "submitted_body_sha256"):
            raise HandoffError(
                "the canonical inquiry body hash must not have changed")
        if submission.get("external_raw_confirmation_sha256") != (
                "14060eef17ccb52838433d8186b3e476d1a703d2476bb37cbd9b5aa8e0a9"
                "31f6"):
            raise HandoffError(
                "the external raw confirmation hash must match exactly")
        evidence = submission.get("external_confirmation_evidence")
        if not isinstance(evidence, list) or len(evidence) != 3:
            raise HandoffError(
                "three external confirmation copies were recorded")
        for row in evidence:
            if row.get("stored_outside_repository") is not True or row.get(
                    "committed_to_git") is not False:
                raise HandoffError(
                    "raw confirmation evidence stays outside Git")

    # Nothing may be fabricated, bypassed or leaked.
    for field, expected in (
        ("pii_committed_to_git", False),
        ("credentials_used_by_automation", False),
        ("captcha_bypassed", False),
        ("ticket_id_fabricated", False),
        ("automatic_follow_up_authorized", False),
        ("follow_up_authorized_now", False),
        ("response_adjudication_authorized", False),
    ):
        if submission.get(field) is not expected:
            raise HandoffError(
                f"M3I-2 inquiry {field} must be {expected}")
    if submission.get("follow_up_max_count") != 1:
        raise HandoffError("the follow-up ceiling is exactly one")
    if submission.get("waiting_period_business_days") != 10:
        raise HandoffError("the waiting period is 10 business days")

    # The two blockers, and only those two, and neither resolved by this action.
    if decision.get("blocker_1_resolved") is not False or decision.get(
            "blocker_2_resolved") is not False:
        raise HandoffError(
            "this initiation cannot resolve a blocker on its own")
    for field, expected in (
        ("filename_token_is_release_evidence", False),
        ("unproven_previous_month_fallback_permitted", False),
        ("official_month_only_next_month_rule_locked", True),
        ("partial_documentary_recovery_can_admit_m3i2", False),
        ("release_date_recovery_alone_can_admit_m3i2", False),
        ("fx_semantic_recovery_alone_can_admit_m3i2", False),
        ("final_test_locked", True),
        ("final_test_access_authorized", False),
        ("m4_authorized", False),
        ("m4_started", False),
        ("merge_authorized", False),
        ("next_research_action_authorized", False),
    ):
        if contract.get(field) is not expected:
            raise HandoffError(
                f"M3I-2 documentary recovery contract {field} must be "
                f"{expected}")
    for field in ("archive_zip_downloads", "archive_zip_redownloads",
                  "company_macro_joins", "feature_materializations",
                  "coverage_calculations", "data_gate_executions",
                  "model_fits", "predictions", "predictive_metrics",
                  "bootstrap_executions", "holm_calculations",
                  "target_values_read", "final_test_rows_read",
                  "final_test_predictor_values_inspected",
                  "final_test_target_values_inspected",
                  "m3i2_admission_decisions", "m3_lag_wdi_contract_locks",
                  "m3_lag_wdi_data_retrievals"):
        if contract.get(field) != 0:
            raise HandoffError(
                f"M3I-2 documentary recovery {field} must be 0")
    if decision.get("m3i2_evidence_status") != (
            "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE"):
        raise HandoffError("M3I-2 evidence must remain UNRESOLVED")
    if decision.get("m3_cbi_status") != "UNRESOLVED_M3_DATA_GATE":
        raise HandoffError("the M3-CBI Gate status must be preserved")

    # The superseded local M3-LAG draft is never authoritative.
    for field, expected in (
        ("local_partial_execution_detected", True),
        ("authoritative_repository_contract_locked", False),
        ("scientific_effective_contract_locked", False),
        ("remote_branch_created", False),
        ("pull_request_created", False),
        ("data_retrieval_started", False),
        ("data_gate_executed", False),
        ("modeling_started", False),
        ("final_test_accessed", False),
        ("prior_authorization_reusable", False),
        ("completion_authorized", False),
        ("commit_authorized", False),
        ("quarantine_created", True),
        ("quarantine_location_committed_to_git", False),
        ("original_dirty_worktree_cleaned_or_deleted", False),
    ):
        if supersession.get(field) is not expected:
            raise HandoffError(
                f"M3-LAG supersession record {field} must be {expected}")
    if supersession.get("commits_created") != 0 or supersession.get(
            "network_requests") != 0:
        raise HandoffError(
            "the local M3-LAG draft created no commit and no network request")

    # LIVE PR topology: this Draft PR, on main, unmerged; PR #75 is history.
    live_number = topology.get("live_pr_number")
    predecessor_number = topology.get("predecessor_pr_number")
    if not isinstance(live_number, int) or isinstance(live_number, bool):
        raise HandoffError("the live recovery PR number must be an integer")
    if predecessor_number != _STAGE128_M3I2_EVIDENCE_CAPTURE_PR_NUMBER:
        raise HandoffError(
            "the merged predecessor of the recovery PR is PR "
            f"#{_STAGE128_M3I2_EVIDENCE_CAPTURE_PR_NUMBER}")
    if live_number <= predecessor_number:
        raise HandoffError(
            "the live recovery PR must succeed the merged evidence-capture PR")
    if topology.get("predecessor_pr_merged") is not True:
        raise HandoffError("PR #75 must be recorded as merged")
    if topology.get("live_pr_base_branch") != _STAGE128_M3I2_MAIN_BRANCH:
        raise HandoffError("the recovery PR must target main")
    if topology.get("live_pr_base_commit") != topology.get(
            "predecessor_pr_merge_commit"):
        raise HandoffError(
            "the recovery PR base must equal the PR #75 merge commit")
    if topology.get("live_pr_is_draft") is not True:
        raise HandoffError("the recovery PR must remain a Draft")
    if topology.get("live_pr_merged") is not False:
        raise HandoffError("the recovery PR must remain unmerged")
    if topology.get("merge_authorized") is not False:
        raise HandoffError("no merge authorization exists for the recovery PR")
    if topology.get("live_pr_head_commit_pinned") is not False:
        raise HandoffError("the live PR head must never be pinned")

    next_action = _NEXT_ACTION_AFTER_RECOVERY_BY_SUBMISSION_STATUS[status]
    if decision.get("next_research_action_id") != next_action:
        raise HandoffError(
            f"with submission status {status} the next research action is "
            f"{next_action}")

    return {
        "stage128_m3i2_final_documentary_recovery_initiated": True,
        "stage128_m3i2_final_documentary_recovery_status":
            decision.get("initiation_status"),
        "stage128_m3i2_final_documentary_recovery_result_code":
            decision.get("result_code"),
        "stage128_m3i2_bounded_search_outcome": outcome,
        "stage128_m3i2_documentary_get_requests": executed,
        "stage128_m3i2_documentary_get_requests_max": ceiling,
        "stage128_m3i2_archive_zip_downloads": 0,
        "stage128_m3i2_archive_zip_redownloads": 0,
        "stage128_m3i2_prior_capture_repeated": False,
        "stage128_m3i2_inquiry_submission_status": status,
        "stage128_m3i2_inquiry_initial_attempts":
            submission.get("initial_inquiries_attempted"),
        "stage128_m3i2_inquiry_initial_submitted":
            submission.get("initial_inquiries_successfully_submitted"),
        "stage128_m3i2_inquiry_body_sha256":
            submission.get("submitted_body_sha256"),
        "stage128_m3i2_inquiry_edition_inventory_sha256":
            submission.get("edition_inventory_sha256"),
        "stage128_m3i2_inquiry_fx_questions_sha256":
            submission.get("fx_questions_sha256"),
        "stage128_m3i2_inquiry_ticket_id_redacted":
            submission.get("ticket_id_redacted"),
        "stage128_m3i2_inquiry_ticket_id_present":
            bool(submission.get("ticket_id_present")),
        "stage128_m3i2_inquiry_ticket_id_fabricated": False,
        "stage128_m3i2_inquiry_acknowledgement_received":
            bool(submission.get("acknowledgement_received")),
        "stage128_m3i2_inquiry_substantive_response_received":
            bool(submission.get("substantive_response_received")),
        "stage128_m3i2_inquiry_human_authenticated_submission":
            bool(submission.get("human_authenticated_submission")),
        "stage128_m3i2_inquiry_external_raw_confirmation_present":
            bool(submission.get("external_raw_confirmation_present")),
        "stage128_m3i2_inquiry_external_raw_confirmation_sha256":
            submission.get("external_raw_confirmation_sha256"),
        "stage128_m3i2_inquiry_submission_timestamp_displayed":
            submission.get("submission_timestamp_displayed"),
        "stage128_m3i2_inquiry_submission_timestamp_utc":
            submission.get("submission_timestamp_utc"),
        "stage128_m3i2_inquiry_submission_timestamp_utc_status":
            submission.get("submission_timestamp_utc_status"),
        "stage128_m3i2_inquiry_submission_calendar_date":
            submission.get("submission_calendar_date"),
        "stage128_m3i2_inquiry_body_submission_evidence_status":
            submission.get("body_submission_evidence_status"),
        "stage128_m3i2_inquiry_attachments_server_enumerated":
            bool(submission.get("attachments_server_confirmation_enumerated")),
        "stage128_m3i2_inquiry_waiting_period_status":
            submission.get("waiting_period_status"),
        "stage128_m3i2_inquiry_waiting_period_completion_date":
            submission.get("waiting_period_completion_date"),
        "stage128_m3i2_inquiry_follow_up_earliest_calendar_date":
            submission.get("follow_up_earliest_calendar_date"),
        "stage128_m3i2_inquiry_follow_up_attempted":
            submission.get("follow_up_attempted", 0),
        "stage128_m3i2_inquiry_pii_committed_to_git": False,
        "stage128_m3i2_inquiry_follow_up_authorized_now": False,
        "stage128_m3i2_inquiry_waiting_period_business_days": 10,
        "stage128_m3i2_response_adjudication_authorized": False,
        "stage128_m3i2_blocker_1_archive_release_resolved": False,
        "stage128_m3i2_blocker_2_fx_semantic_resolved": False,
        "stage128_m3i2_filename_token_is_release_evidence": False,
        "stage128_m3i2_unproven_previous_month_fallback_used": False,
        "stage128_m3i2_official_month_only_next_month_rule_locked": True,
        # The superseded local M3-LAG draft.
        "stage128_m3_lag_wdi_local_partial_draft_detected": True,
        "stage128_m3_lag_wdi_local_partial_draft_quarantined": True,
        "stage128_m3_lag_wdi_local_partial_draft_authoritative": False,
        "stage128_m3_lag_wdi_prior_authorization_reusable": False,
        "stage128_m3_lag_wdi_exploratory_contract_locked": False,
        "stage128_m3_lag_wdi_authoritative_contract_status": "NOT_LOCKED",
        "stage128_m3_lag_wdi_data_retrieval_started": False,
        "stage128_m3_lag_wdi_data_gate_executed": False,
        # DERIVED, never hard-coded: step E flips this, and a marker
        # function must not publish a moment as if it were a rule.
        "stage128_m3_lag_wdi_modeling_started":
            _stage128_m3_lag_modeling_started(root),
        # LIVE PR topology; PR #75 becomes the merged predecessor.
        "stage128_m3i2_live_pr_number": live_number,
        "stage128_m3i2_live_pr_base_branch": _STAGE128_M3I2_MAIN_BRANCH,
        "stage128_m3i2_live_pr_base_commit":
            topology.get("live_pr_base_commit"),
        "stage128_m3i2_live_main_commit": topology.get("live_pr_base_commit"),
        "stage128_m3i2_live_pr_is_draft": True,
        "stage128_m3i2_live_pr_merged": False,
        "stage128_m3i2_live_pr_role": topology.get("live_pr_role"),
        "stage128_m3i2_evidence_capture_pr_number": predecessor_number,
        "stage128_m3i2_evidence_capture_pr_merged": True,
        "stage128_m3i2_evidence_capture_pr_merge_commit":
            topology.get("predecessor_pr_merge_commit"),
        "stage128_m3i2_evidence_capture_pr_semantics":
            "merged_predecessor_superseded_by_pr" f"{live_number}",
        "stage128_m3i2_merge_authorized": False,
        # Acquisition of DOCUMENTS is not admission of DATA.
        "stage128_m3i2_evidence_status": "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE",
        "m3i2_block_admitted": False,
        "m3i2_data_gate_executed": False,
        "m3i2_modeling_started": False,
        "m3i3_admitted": False,
        "m4_authorized": False,
        "m4_started": False,
        "final_test_locked": True,
        # Pointers. The initiation IS a completed research action; the pointer
        # it publishes is informational and explicitly unauthorized.
        "last_completed_research_action_id":
            _STAGE128_M3I2_RECOVERY_ACTION_ID,
        "next_research_action_id": next_action,
        "next_research_action_authorized": False,
        "next_research_action_pointer_is_not_authorization": True,
    }


_STAGE128_M3I2_INQUIRY_SUBMISSION_PKG = (
    "project/stage128/m3i2_final_official_inquiry_human_submission")
_STAGE128_M3I2_INQUIRY_SUBMISSION_ACTION_ID = (
    "stage128-m3i2-final-official-inquiry-human-submission")
_STAGE128_M3I2_INQUIRY_SUBMISSION_DECISION_REL = (
    f"{_STAGE128_M3I2_INQUIRY_SUBMISSION_PKG}/"
    "stage128_m3i2_final_official_inquiry_submission_decision.json")
_STAGE128_M3I2_INQUIRY_SUBMISSION_BOUNDARY_REL = (
    f"{_STAGE128_M3I2_INQUIRY_SUBMISSION_PKG}/"
    "stage128_m3i2_final_official_inquiry_governance_boundary.json")
_STAGE128_M3I2_INQUIRY_SUBMISSION_AUTHORIZATION_REL = (
    f"{_STAGE128_M3I2_INQUIRY_SUBMISSION_PKG}/"
    "stage128_m3i2_final_official_inquiry_human_authorization_record.json")
_STAGE128_M3I2_INQUIRY_SUBMISSION_TOPOLOGY_REL = (
    f"{_STAGE128_M3I2_INQUIRY_SUBMISSION_PKG}/"
    "stage128_m3i2_final_official_inquiry_submission_pr_topology.json")
#: The head published for the live PR is the repository head observed at
#: GENERATION time. It is an engineering anchor for the snapshot, NOT the
#: instantaneous GitHub PR head, and pinning it would make the record
#: self-referential the instant it is committed.
_STAGE128_M3I2_LIVE_PR_HEAD_SEMANTICS = (
    "repository_head_at_generation_not_github_pr_head")
_STAGE128_M3I2_INQUIRY_RESPONSE_INGESTION_ACTION_ID = (
    "stage128-m3i2-final-official-inquiry-response-ingestion")
_STAGE128_M3I2_INQUIRY_FOLLOW_UP_ACTION_ID = (
    "stage128-m3i2-final-official-inquiry-one-follow-up")


def derive_stage128_m3i2_inquiry_human_submission_markers(root: str) -> dict:
    """Recognize the sanitized recording of the HUMAN inquiry submission.

    The action is a RECORDING: a human supervisor submitted the prepared
    inquiry exactly once and an acknowledgement came back. An acknowledgement
    is a receipt, not an answer, so this deriver admits nothing, resolves
    neither blocker and authorizes neither a follow-up nor any ingestion of a
    response. It fails closed on any artifact that claims otherwise, and in
    particular on any attempt to invent the ticket id or the UTC instant that
    the confirmation UI never displayed.

    Returns {} before the submission recording exists.
    """
    path = os.path.join(root, _STAGE128_M3I2_INQUIRY_SUBMISSION_DECISION_REL)
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        decision = json.load(fh)
    with open(os.path.join(
            root, _STAGE128_M3I2_INQUIRY_SUBMISSION_BOUNDARY_REL),
            encoding="utf-8") as fh:
        boundary = json.load(fh)
    with open(os.path.join(
            root, _STAGE128_M3I2_INQUIRY_SUBMISSION_AUTHORIZATION_REL),
            encoding="utf-8") as fh:
        authorization = json.load(fh)
    topology_path = os.path.join(
        root, _STAGE128_M3I2_INQUIRY_SUBMISSION_TOPOLOGY_REL)
    if not os.path.isfile(topology_path):
        raise HandoffError(
            "the M3I-2 inquiry submission package is missing "
            f"{_STAGE128_M3I2_INQUIRY_SUBMISSION_TOPOLOGY_REL}")
    with open(topology_path, encoding="utf-8") as fh:
        topology = json.load(fh)

    for record, label in ((decision, "decision"), (boundary, "boundary"),
                          (authorization, "authorization"),
                          (topology, "topology")):
        if record.get("action_id") != (
                _STAGE128_M3I2_INQUIRY_SUBMISSION_ACTION_ID):
            raise HandoffError(
                f"M3I-2 inquiry submission {label} action_id mismatch")

    if decision.get("submission_status") != (
            _STAGE128_M3I2_HUMAN_SUBMITTED_STATUS):
        raise HandoffError(
            "the recorded M3I-2 inquiry submission status must be "
            f"{_STAGE128_M3I2_HUMAN_SUBMITTED_STATUS}")

    # The authorization is identified by its text, never by its hash alone,
    # and this recording consumes it. It authorizes no merge.
    text = authorization.get("authorization_text") or ""
    if len(text.encode("utf-8")) != authorization.get(
            "authorization_utf8_bytes"):
        raise HandoffError(
            "the recorded authorization byte length must match its text")
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != (
            authorization.get("authorization_sha256")):
        raise HandoffError(
            "the recorded authorization hash must match its text")
    for field, expected in (
        ("scope_identified_by_hash_alone", False),
        ("authorization_consumed_by_this_recording", True),
        ("standing_authorization", False),
        ("merge_authorized", False),
    ):
        if authorization.get(field) is not expected:
            raise HandoffError(
                f"M3I-2 inquiry submission authorization {field} must be "
                f"{expected}")

    # Nothing executed, nothing sent again, nothing personal touched.
    for field in ("coverage_calculations", "feature_materializations",
                  "data_gate_executions", "model_fits", "predictions",
                  "predictive_metrics", "wdi_archive_downloads",
                  "network_requests"):
        if boundary.get(field) != 0:
            raise HandoffError(
                f"M3I-2 inquiry submission recording {field} must be 0")
    for field, expected in (
        ("resubmission_executed", False),
        ("new_documentary_search_executed", False),
        ("gmail_or_personal_account_accessed", False),
        ("response_ingestion_authorized", False),
        ("response_adjudication_authorized", False),
        ("conditional_follow_up_authorized", False),
        ("follow_up_authorized_now", False),
        ("follow_up_before_2026_08_21_forbidden", True),
        ("ready_for_review_authorized", False),
        ("merge_authorized", False),
        ("next_research_action_authorized", False),
        ("final_test_locked", True),
        ("m4_authorized", False),
        ("m3i2_admitted", False),
    ):
        if boundary.get(field) is not expected:
            raise HandoffError(
                f"M3I-2 inquiry submission boundary {field} must be "
                f"{expected}")
    if boundary.get("conditional_follow_up_action_id") != (
            _STAGE128_M3I2_INQUIRY_FOLLOW_UP_ACTION_ID):
        raise HandoffError(
            "the conditional follow-up pointer id must be "
            f"{_STAGE128_M3I2_INQUIRY_FOLLOW_UP_ACTION_ID}")
    if boundary.get("conditional_follow_up_earliest_date") != "2026-08-21":
        raise HandoffError("the earliest possible follow-up date is 2026-08-21")

    # An acknowledgement moves no science.
    if decision.get("scientific_effect") != "NONE":
        raise HandoffError(
            "recording an acknowledgement has no scientific effect")
    for field, expected in (
        ("archive_release_blocker_resolved", False),
        ("fx_semantic_continuity_blocker_resolved", False),
        ("blocker_1_resolved", False),
        ("blocker_2_resolved", False),
        ("m3i2_admitted", False),
        ("final_test_locked", True),
        ("m4_authorized", False),
        ("merge_authorized", False),
        ("next_research_action_authorized", False),
        ("paper_winner_selected", False),
    ):
        if decision.get(field) is not expected:
            raise HandoffError(
                f"M3I-2 inquiry submission decision {field} must be "
                f"{expected}")
    if decision.get("m3i2_evidence_status") != (
            "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE"):
        raise HandoffError("M3I-2 evidence must remain UNRESOLVED")
    if decision.get("m3_cbi_status") != "UNRESOLVED_M3_DATA_GATE":
        raise HandoffError("the M3-CBI Gate status must be preserved")
    if decision.get("m3_lag_wdi_authoritative_contract_status") != "NOT_LOCKED":
        raise HandoffError("M3-LAG-WDI must remain NOT_LOCKED")
    if decision.get("data_gate_status") != "NOT_EXECUTED":
        raise HandoffError("the Data Gate must remain NOT_EXECUTED")
    if decision.get("verified_wdi_release_dates") != 0 or decision.get(
            "verified_pre_cutoff_editions") != 0:
        raise HandoffError(
            "an acknowledgement verifies no release date and no edition")
    if decision.get("unresolved_cutoffs") != decision.get(
            "unresolved_cutoffs_total"):
        raise HandoffError("every cutoff must remain unresolved")
    if decision.get("unresolved_development_pairs") != decision.get(
            "unresolved_development_pairs_total"):
        raise HandoffError("every development pair must remain unresolved")
    cpi = decision.get("cpi_semantic_compatibility") or {}
    fx = decision.get("fx_semantic_compatibility") or {}
    if cpi.get("fail_integrity") or fx.get("fail_integrity"):
        raise HandoffError(
            "no semantic-compatibility integrity failure may appear here")
    if fx.get("pass"):
        raise HandoffError(
            "FX semantic continuity is still UNRESOLVED for every edition")

    if decision.get("next_research_action_id") != (
            _STAGE128_M3I2_INQUIRY_RESPONSE_INGESTION_ACTION_ID):
        raise HandoffError(
            "the pointer after the human submission is "
            f"{_STAGE128_M3I2_INQUIRY_RESPONSE_INGESTION_ACTION_ID}")
    if decision.get("last_completed_research_action_id") != (
            _STAGE128_M3I2_INQUIRY_SUBMISSION_ACTION_ID):
        raise HandoffError(
            "the human submission is the last completed research action")

    # --- LIVE PR topology. A MERGED PR is never the live Draft. ---------- #
    # The recovery initiation published itself as the live Draft PR; it has
    # since been merged, so this recording re-anchors the live topology onto
    # its OWN PR and demotes the recovery PR to a merged predecessor. Every
    # value is read from the topology record and validated here, so a stale
    # or self-contradictory topology fails closed rather than being rendered.
    live_number = topology.get("live_pr_number")
    predecessor_number = topology.get("predecessor_pr_number")
    for value, label in ((live_number, "live"),
                         (predecessor_number, "predecessor")):
        if not isinstance(value, int) or isinstance(value, bool):
            raise HandoffError(
                f"the M3I-2 {label} PR number must be an integer")
    if live_number <= predecessor_number:
        raise HandoffError(
            f"the live M3I-2 PR #{live_number} must succeed the merged "
            f"predecessor PR #{predecessor_number}")
    base_commit = topology.get("live_pr_base_commit")
    merge_commit = topology.get("predecessor_pr_merge_commit")
    for value, label in ((base_commit, "live PR base"),
                         (merge_commit, "predecessor merge")):
        if not (isinstance(value, str) and len(value) == 40):
            raise HandoffError(
                f"the M3I-2 {label} commit must be a full 40-hex SHA")
    # The live PR targets `main`, and `main` IS the predecessor's merge
    # commit: that identity is what makes the predecessor merged and gone.
    if base_commit != merge_commit:
        raise HandoffError(
            "the live M3I-2 PR must be based on the merge commit of its "
            "merged predecessor")
    if topology.get("live_pr_base_branch") != _STAGE128_M3I2_LIVE_BASE_BRANCH:
        raise HandoffError(
            "the live M3I-2 PR must target "
            f"{_STAGE128_M3I2_LIVE_BASE_BRANCH}")
    for field, expected in (
        ("predecessor_pr_merged", True),
        ("live_pr_is_draft", True),
        ("live_pr_merged", False),
        ("merge_authorized", False),
        ("auto_merge", False),
        ("ready_for_review_authorized", False),
        ("pr_is_stacked_on_open_predecessor", False),
        ("live_pr_head_commit_pinned", False),
        ("live_pr_head_is_github_pr_head", False),
    ):
        if topology.get(field) is not expected:
            raise HandoffError(
                f"M3I-2 inquiry submission topology {field} must be "
                f"{expected}")
    if topology.get("live_pr_head_semantics") != (
            _STAGE128_M3I2_LIVE_PR_HEAD_SEMANTICS):
        raise HandoffError(
            "the live M3I-2 PR head semantics must be "
            f"{_STAGE128_M3I2_LIVE_PR_HEAD_SEMANTICS}")

    return {
        "stage128_m3i2_inquiry_human_submission_recorded": True,
        # The live topology, re-anchored onto THIS Draft PR.
        "stage128_m3i2_live_pr_number": live_number,
        "stage128_m3i2_live_pr_base_branch":
            topology.get("live_pr_base_branch"),
        "stage128_m3i2_live_pr_base_commit": base_commit,
        "stage128_m3i2_live_main_commit": base_commit,
        "stage128_m3i2_live_pr_is_draft": True,
        "stage128_m3i2_live_pr_merged": False,
        "stage128_m3i2_live_pr_role": topology.get("live_pr_role"),
        "stage128_m3i2_live_pr_head_commit_source":
            _STAGE128_M3I2_LIVE_PR_HEAD_SEMANTICS,
        "stage128_m3i2_live_pr_ready_for_review_authorized": False,
        # ... which demotes the recovery initiation PR to HISTORY.
        "stage128_m3i2_recovery_pr_number": predecessor_number,
        "stage128_m3i2_recovery_pr_merged": True,
        "stage128_m3i2_recovery_pr_merge_commit": merge_commit,
        "stage128_m3i2_recovery_pr_semantics": (
            "merged_predecessor_superseded_by_pr" f"{live_number}"),
        "stage128_m3i2_merge_authorized": False,
        "stage128_m3i2_inquiry_human_submission_result_code":
            decision.get("result_code"),
        "stage128_m3i2_inquiry_authorization_sha256":
            authorization.get("authorization_sha256"),
        "stage128_m3i2_inquiry_authorization_utf8_bytes":
            authorization.get("authorization_utf8_bytes"),
        "stage128_m3i2_inquiry_authorization_consumed": True,
        "stage128_m3i2_inquiry_resubmission_executed": False,
        "stage128_m3i2_inquiry_response_ingestion_authorized": False,
        "stage128_m3i2_inquiry_conditional_follow_up_action_id":
            _STAGE128_M3I2_INQUIRY_FOLLOW_UP_ACTION_ID,
        "stage128_m3i2_inquiry_conditional_follow_up_earliest_date":
            boundary.get("conditional_follow_up_earliest_date"),
        "stage128_m3i2_inquiry_conditional_follow_up_authorized": False,
        "stage128_m3i2_inquiry_gmail_or_personal_account_accessed": False,
        "stage128_m3i2_inquiry_submission_recording_pr_is_draft": True,
        "stage128_m3i2_inquiry_submission_recording_merge_authorized": False,
        # Pointers. The human submission IS a completed research action; what
        # it publishes is informational and explicitly unauthorized.
        "last_completed_research_action_id":
            _STAGE128_M3I2_INQUIRY_SUBMISSION_ACTION_ID,
        "next_research_action_id":
            _STAGE128_M3I2_INQUIRY_RESPONSE_INGESTION_ACTION_ID,
        "next_research_action_authorized": False,
        "next_research_action_pointer_is_not_authorization": True,
    }


_STAGE128_M3I2_SUITE_COMPARISON_REL = (
    f"{_STAGE128_M3I2_RECOVERY_PKG}/"
    "stage128_m3i2_full_suite_baseline_comparison.json")


def derive_stage128_m3i2_full_suite_comparison_markers(root: str) -> dict:
    """Recognize the baseline-versus-candidate full-suite comparison record.

    A VERIFICATION record, not a scientific one: it says only that the same
    suite was run on the baseline and on the candidate correction head in the
    same environment, and that the candidate introduced no new failure. It
    admits nothing and moves no pointer.

    Fail-closed. The record must evaluate the declared baseline, must not
    claim to have tested the commit that carries it, and must agree with its
    own node-id sets — a record that says "no new failures" while listing some
    is a broken record, not a passing one.

    Returns {} before the comparison record exists.
    """
    path = os.path.join(root, _STAGE128_M3I2_SUITE_COMPARISON_REL)
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        rec = json.load(fh)
    decision_path = os.path.join(root, _STAGE128_M3I2_RECOVERY_DECISION_REL)
    with open(decision_path, encoding="utf-8") as fh:
        expected_baseline = json.load(fh).get("baseline_commit")
    if rec.get("baseline_sha") != expected_baseline:
        raise HandoffError(
            "the full-suite comparison must be measured against the baseline "
            "commit the recovery decision records")
    if not rec.get("report_commit_self_reference_avoided"):
        raise HandoffError(
            "the full-suite comparison must not claim to have tested the "
            "commit that carries it")
    new_ids = rec.get("new_failure_node_ids")
    if not isinstance(new_ids, list):
        raise HandoffError("new_failure_node_ids must be a list")
    if rec.get("new_failures_count") != len(new_ids):
        raise HandoffError(
            "new_failures_count disagrees with new_failure_node_ids")
    base_ids = set(rec.get("baseline_failure_node_ids") or [])
    cand_ids = set(rec.get("candidate_failure_node_ids") or [])
    if set(new_ids) != cand_ids - base_ids:
        raise HandoffError(
            "new_failure_node_ids is not candidate minus baseline")
    if set(rec.get("preexisting_failure_node_ids") or []) != base_ids & cand_ids:
        raise HandoffError(
            "preexisting_failure_node_ids is not the baseline/candidate "
            "intersection")
    if set(rec.get("resolved_failure_node_ids") or []) != base_ids - cand_ids:
        raise HandoffError(
            "resolved_failure_node_ids is not baseline minus candidate")
    if new_ids and rec.get("comparison_result") == (
            "PASS_NO_PR_INTRODUCED_FULL_SUITE_FAILURES"):
        raise HandoffError(
            "a PASS comparison result cannot carry new failures")
    for field in ("same_pytest_command", "same_assets",
                  "same_environment_variables",
                  "same_working_directory_semantics",
                  "no_test_was_deleted_or_weakened_to_hide_a_failure"):
        if rec.get(field) is not True:
            raise HandoffError(f"full-suite comparison {field} must be True")
    # A verification record may never move the scientific state.
    for field, expected in (
        ("m3i2_admitted", False),
        ("m3i2_data_gate_executed", False),
        ("final_test_locked", True),
        ("m4_authorized", False),
        ("merge_authorized", False),
    ):
        if rec.get(field) is not expected:
            raise HandoffError(
                f"full-suite comparison {field} != {expected}")
    if rec.get("m3_lag_wdi_authoritative_contract_status") != "NOT_LOCKED":
        raise HandoffError(
            "the full-suite comparison must keep M3-LAG-WDI NOT_LOCKED")
    return {
        "full_suite_baseline_comparison_completed": True,
        "full_suite_new_failures": len(new_ids),
        "full_suite_baseline_sha": rec.get("baseline_sha"),
        "full_suite_candidate_correction_head": rec.get(
            "candidate_correction_head"),
        "full_suite_comparison_result": rec.get("comparison_result"),
        "full_suite_baseline_failed": rec.get("baseline_failed"),
        "full_suite_candidate_failed": rec.get("candidate_failed"),
        "full_suite_baseline_passed": rec.get("baseline_passed"),
        "full_suite_candidate_passed": rec.get("candidate_passed"),
        "full_suite_preexisting_failures": len(
            rec.get("preexisting_failure_node_ids") or []),
        "full_suite_comparison_is_verification_not_science": True,
        "full_suite_comparison_self_reference_avoided": True,
    }


# --------------------------------------------------------------------------- #
# Stage128 — M3-LAG-WDI exploratory contract lock (Track B)
# --------------------------------------------------------------------------- #

_STAGE128_M3_LAG_PKG = (
    "project/stage128/m3_lag_wdi_exploratory_contract_lock")
_STAGE128_M3_LAG_ACTION_ID = "stage128-m3-lag-wdi-exploratory-contract-lock"
_STAGE128_M3_LAG_CONTRACT_REL = (
    f"{_STAGE128_M3_LAG_PKG}/stage128_m3_lag_wdi_exploratory_contract.json")
_STAGE128_M3_LAG_DECISION_REL = (
    f"{_STAGE128_M3_LAG_PKG}/"
    "stage128_m3_lag_wdi_exploratory_contract_decision.json")
_STAGE128_M3_LAG_BOUNDARY_REL = (
    f"{_STAGE128_M3_LAG_PKG}/"
    "stage128_m3_lag_wdi_exploratory_governance_boundary.json")
_STAGE128_M3_LAG_GATE_REL = (
    f"{_STAGE128_M3_LAG_PKG}/"
    "stage128_m3_lag_wdi_exploratory_data_gate_contract.json")
_STAGE128_M3_LAG_MODELING_REL = (
    f"{_STAGE128_M3_LAG_PKG}/"
    "stage128_m3_lag_wdi_exploratory_modeling_contract.json")
_STAGE128_M3_LAG_AUDIT_REL = (
    f"{_STAGE128_M3_LAG_PKG}/"
    "stage128_m3_lag_wdi_exploratory_execution_audit.json")
_STAGE128_M3_LAG_AUTHORIZATION_REL = (
    f"{_STAGE128_M3_LAG_PKG}/"
    "stage128_m3_lag_wdi_exploratory_human_authorization_record.json")
_STAGE128_M3_LAG_TOPOLOGY_REL = (
    f"{_STAGE128_M3_LAG_PKG}/"
    "stage128_m3_lag_wdi_exploratory_pr_topology.json")

#: The ONLY status a satisfied M3-LAG-WDI contract lock may publish.
_STAGE128_M3_LAG_LOCKED_STATUS = "AUTHORITATIVE_CONTRACT_LOCKED_PRE_RETRIEVAL"
_STAGE128_M3_LAG_ROLE = "supplementary_exploratory_robustness_block"
#: Track B's future actions, each a SEPARATE action with its own identity and
#: its own future authorization. Retrieval is the immediate pointer and it is
#: retrieval ONLY: it does not execute the Data Gate, and an authorization to
#: retrieve is not an authorization to Gate. The Gate, in turn, is DATA
#: ADMISSION ONLY and does not authorize modeling. Collapsing any two of these
#: into one action erases an authorization boundary, so the identities are
#: pinned here and every surface is derived from them.
_STAGE128_M3_LAG_NEXT_ACTION_ID = (
    "stage128-m3-lag-wdi-exploratory-data-retrieval")
_STAGE128_M3_LAG_RETRIEVAL_ACTION_ID = _STAGE128_M3_LAG_NEXT_ACTION_ID
_STAGE128_M3_LAG_POST_RETRIEVAL_AUDIT_ACTION_ID = (
    "stage128-m3-lag-wdi-exploratory-post-retrieval-audit")
_STAGE128_M3_LAG_DATA_GATE_ACTION_ID = (
    "stage128-m3-lag-wdi-exploratory-data-gate")
_STAGE128_M3_LAG_MODELING_ACTION_ID = (
    "stage128-m3-lag-wdi-exploratory-incremental-evaluation")
#: The immediate pointer's scope. "retrieval_only" is the ONLY accepted value:
#: anything that also names the Gate is a conflated action.
_STAGE128_M3_LAG_NEXT_ACTION_SCOPE = "retrieval_only"
#: (step, action_id, executes_retrieval, executes_gate, executes_modeling)
_STAGE128_M3_LAG_ACTION_SEQUENCE = (
    ("A", "stage128-m3-lag-wdi-exploratory-contract-lock", False, False, False),
    ("B", _STAGE128_M3_LAG_RETRIEVAL_ACTION_ID, True, False, False),
    ("C", _STAGE128_M3_LAG_POST_RETRIEVAL_AUDIT_ACTION_ID, False, False, False),
    ("D", _STAGE128_M3_LAG_DATA_GATE_ACTION_ID, False, True, False),
    ("E", _STAGE128_M3_LAG_MODELING_ACTION_ID, False, False, True),
)
def _stage128_m3_lag_action_executes_data_gate(action_id: str) -> bool:
    """Does the NAMED Track B action execute the Data Gate?

    ``*_executes_data_gate`` is a DESCRIPTIVE property of a specific action,
    not a promise that no Gate will ever run. The canonical values live in
    ``_STAGE128_M3_LAG_ACTION_SEQUENCE``: only step D, the Data Gate action
    itself, carries True.

    ``next_action_executes_data_gate`` is therefore the same property applied
    to whichever action the pointer currently names — it has always mirrored
    the per-action field for that action (at contract-lock time it mirrored
    ``retrieval_action_executes_data_gate``, after retrieval it mirrored
    ``post_retrieval_audit_executes_data_gate``). Deriving it here means it can
    never again be hard-coded to a value that was only true at one moment.

    The safety property is carried by ``next_action_authorized`` and by
    ``data_gate_authorized``/``data_gate_executed``, NOT by pretending the Gate
    action does not gate.
    """
    for _step, candidate, _retr, executes_gate, _model in (
            _STAGE128_M3_LAG_ACTION_SEQUENCE):
        if candidate == action_id:
            return bool(executes_gate)
    raise HandoffError(
        f"{action_id!r} is not a Track B action in the locked sequence")


#: The step E (modeling) decision artifact. Its EXISTENCE on disk is what makes
#: ``modeling_started`` true — the field is a fact about the repository, never
#: a permission.
_STAGE128_M3_LAG_EVAL_DECISION_REL = (
    "project/stage128/m3_lag_wdi_exploratory_incremental_evaluation/"
    "stage128_m3_lag_wdi_evaluation_decision.json")


def _stage128_m3_lag_modeling_started(root: str) -> bool:
    """Has Track B step E actually executed?

    Every step before E published ``modeling_started: False`` as a hard-coded
    constant. That was true at the MOMENT each of them ran, but it is not a
    rule — step E exists precisely to make it False no longer. Hard-coding it
    would mean an executed step E silently reads as never having happened, and
    (worse) that whichever marker function happened to be merged last would
    decide the published value.

    So it is DERIVED from the committed step E decision artifact. The safety
    property lives where it belongs and stays hard-coded, because it IS a
    rule: ``modeling_authorized`` is a STANDING permission and is False at
    every moment — before step E because it had not been granted, and after
    step E because its single-use grant was consumed.
    """
    return os.path.isfile(
        os.path.join(root, _STAGE128_M3_LAG_EVAL_DECISION_REL))


#: The two features, in the exact locked order, with their exact identities.
_STAGE128_M3_LAG_FEATURES = (
    ("intl_cpi_inflation_lag1_wdi", "FP.CPI.TOTL.ZG"),
    ("intl_fx_change_official_lag1_wdi", "PA.NUS.FCRF"),
)
_STAGE128_M3_LAG_FX_FORMULA = "FX_LAG1_t = 100 * ln(E_y / E_(y-1))"
_STAGE128_M3_LAG_FX_FORMULA_EQUIVALENT = "100 * ln(E_(t-1) / E_(t-2))"
_STAGE128_M3_LAG_CONFIRMATORY_FAMILY = (
    "M2_minus_M1", "M3_CBI_minus_M2", "M4_minus_M3_CBI")
#: PR #77 (the M3I-2 human-submission recording) was merged into main by this
#: commit. Pinning BOTH halves is what stops a merged PR from being re-rendered
#: as the live Draft: "live > predecessor" alone would accept a topology that
#: renamed #77 the live PR and demoted #76 in its place.
_STAGE128_M3_LAG_MERGED_PREDECESSOR_PR = 77
_STAGE128_M3_LAG_MERGED_PREDECESSOR_COMMIT = (
    "93de6bae9344ce893b0261f818abce8a991cf842")

#: HISTORICAL PR ROLES — pinned facts, never re-derived from adjacency.
#:
#: "The recovery PR" is a NAME for a specific historical action, not a moving
#: label for "whatever merged most recently". PR #76 carried the final official
#: documentary recovery INITIATION and PR #77 carried the later HUMAN inquiry
#: submission RECORDING; they are two different actions and each keeps its own
#: identity forever. Re-anchoring the live topology onto a newer Draft must
#: never shift either of them, so both are pinned here and validated against
#: the topology artifact fail-closed.
_STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR = 76
_STAGE128_M3I2_DOCUMENTARY_RECOVERY_MERGE_COMMIT = (
    "89d8e6ff2d12ec82903cd28aa7ab839eb946b658")
_STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR_ROLE = (
    "final_official_documentary_recovery_initiation_pr")
_STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR_ACTION_ID = (
    "stage128-m3i2-final-official-documentary-recovery-initiation")
#: The documentary-recovery PR was superseded by the human-submission PR — not
#: by whatever Draft happens to be live now.
_STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR_SEMANTICS = (
    "merged_predecessor_superseded_by_pr77")
_STAGE128_M3I2_HUMAN_SUBMISSION_PR = 77
_STAGE128_M3I2_HUMAN_SUBMISSION_MERGE_COMMIT = (
    "93de6bae9344ce893b0261f818abce8a991cf842")
_STAGE128_M3I2_HUMAN_SUBMISSION_PR_ROLE = (
    "final_official_inquiry_human_submission_recording_pr")
_STAGE128_M3I2_HUMAN_SUBMISSION_PR_ACTION_ID = (
    "stage128-m3i2-final-official-inquiry-human-submission")


def derive_stage128_m3_lag_wdi_exploratory_markers(root: str) -> dict:
    """Recognize the M3-LAG-WDI-EXPLORATORY authoritative contract lock.

    Narrow and fail-closed. The action is a CONTRACT LOCK ONLY: it retrieves
    nothing, inspects no value, executes no Data Gate, materializes no feature,
    fits no model and reads no Final Test row. A ``LOCKED`` status may
    therefore exist only if the authoritative contract still says every one of
    those things, still describes the exact two lagged WDI features, still
    keeps the exploratory comparison out of the confirmatory Holm family, and
    still leaves the World Bank inquiry active and unresolved. Anything else
    fails closed rather than being rendered.

    Returns an empty dict before the package exists, so pre-lock Handoffs are
    unaffected.
    """
    path = os.path.join(root, _STAGE128_M3_LAG_CONTRACT_REL)
    if not os.path.isfile(path):
        return {}
    contract = _require_json_artifact(root, _STAGE128_M3_LAG_CONTRACT_REL)
    decision = _require_json_artifact(root, _STAGE128_M3_LAG_DECISION_REL)
    boundary = _require_json_artifact(root, _STAGE128_M3_LAG_BOUNDARY_REL)
    gate = _require_json_artifact(root, _STAGE128_M3_LAG_GATE_REL)
    modeling = _require_json_artifact(root, _STAGE128_M3_LAG_MODELING_REL)
    audit = _require_json_artifact(root, _STAGE128_M3_LAG_AUDIT_REL)
    authorization = _require_json_artifact(
        root, _STAGE128_M3_LAG_AUTHORIZATION_REL)
    topology = _require_json_artifact(root, _STAGE128_M3_LAG_TOPOLOGY_REL)

    for artifact, rel in ((contract, _STAGE128_M3_LAG_CONTRACT_REL),
                          (decision, _STAGE128_M3_LAG_DECISION_REL),
                          (boundary, _STAGE128_M3_LAG_BOUNDARY_REL),
                          (audit, _STAGE128_M3_LAG_AUDIT_REL),
                          (authorization, _STAGE128_M3_LAG_AUTHORIZATION_REL),
                          (topology, _STAGE128_M3_LAG_TOPOLOGY_REL)):
        if artifact.get("action_id") != _STAGE128_M3_LAG_ACTION_ID:
            raise HandoffError(
                f"{rel} must name action {_STAGE128_M3_LAG_ACTION_ID}")

    # --- Exploratory role, never confirmatory ---------------------------- #
    if contract.get("scientific_role") != _STAGE128_M3_LAG_ROLE:
        raise HandoffError(
            f"M3-LAG-WDI must stay a {_STAGE128_M3_LAG_ROLE}")
    for field in ("is_confirmatory_m3", "is_replacement_for_m3_cbi",
                  "is_repair_of_m3_cbi",
                  "is_continuation_or_replacement_of_m3i2",
                  "is_real_time_wdi", "is_historical_vintage_wdi",
                  "in_original_confirmatory_holm_family",
                  "can_select_paper_winner_alone",
                  "proves_historical_point_in_time_wdi_availability",
                  "one_year_lag_establishes_point_in_time_availability",
                  "exploratory_result_can_rewrite_main_confirmatory_conclusion",
                  "reuses_m3i2_historical_vintage_availability_logic",
                  "third_macro_feature_permitted",
                  "financing_rate_feature_permitted",
                  "indicator_search_permitted", "imputation_permitted",
                  "feature_selection_permitted",
                  "feature_substitution_permitted",
                  "new_proxy_search_permitted", "feature_search_permitted"):
        if contract.get(field) is not False:
            raise HandoffError(f"M3-LAG-WDI contract {field} must be False")
    if contract.get(
            "one_year_lag_is_conservative_temporal_separation_design_only"
    ) is not True:
        raise HandoffError(
            "the one-year lag is a conservative temporal-separation design "
            "only")

    # --- Exactly two features, exact identities, exact lag rule ---------- #
    features = contract.get("features") or []
    if len(features) != 2 or contract.get(
            "additional_macro_feature_count") != 2:
        raise HandoffError(
            "M3-LAG-WDI contains EXACTLY two additional macro features")
    for feature, (feature_id, code) in zip(
            features, _STAGE128_M3_LAG_FEATURES):
        if feature.get("feature_id") != feature_id:
            raise HandoffError(
                f"M3-LAG-WDI feature id must be {feature_id}")
        if feature.get("indicator_code") != code:
            raise HandoffError(
                f"{feature_id} must use indicator {code}")
        if feature.get("country_code") != "IRN":
            raise HandoffError(f"{feature_id} must use country IRN")
        if feature.get("source_identity") != "World Bank WDI":
            raise HandoffError(f"{feature_id} must come from World Bank WDI")
        if feature.get("lag_years") != 1:
            raise HandoffError(f"{feature_id} must be lagged by one year")
        if feature.get("same_year_t_observation_permitted") is not False:
            raise HandoffError(
                f"{feature_id} may not use a same-year t observation")
        for field in ("alternative_indicator_after_failure_permitted",
                      "imputation_permitted"):
            if feature.get(field) is not False:
                raise HandoffError(f"{feature_id} {field} must be False")
    cpi, fx = features
    if cpi.get("observation_year_rule") != "t - 1":
        raise HandoffError("the CPI observation year rule must be t - 1")
    if cpi.get("transformation") != "identity":
        raise HandoffError("the CPI transformation must be the identity")
    if cpi.get("required_observation_years") != ["t-1"]:
        raise HandoffError("CPI requires exactly the t-1 observation")
    if cpi.get("worked_example") != {"predictor_year": 2019,
                                     "wdi_observation_year": 2018}:
        raise HandoffError("predictor year 2019 maps to CPI year 2018")
    if fx.get("observation_year_rule") != "y = t - 1":
        raise HandoffError("the FX observation year rule must be y = t - 1")
    if fx.get("transformation") != _STAGE128_M3_LAG_FX_FORMULA:
        raise HandoffError(
            f"the FX transformation must be {_STAGE128_M3_LAG_FX_FORMULA}")
    if fx.get("transformation_equivalent") != (
            _STAGE128_M3_LAG_FX_FORMULA_EQUIVALENT):
        raise HandoffError(
            "the FX transformation must equal "
            f"{_STAGE128_M3_LAG_FX_FORMULA_EQUIVALENT}")
    if fx.get("required_observation_years") != ["t-1", "t-2"]:
        raise HandoffError("FX requires exactly the t-1 and t-2 observations")
    if list(fx.get("observation_requirements") or []) != [
            "present", "numeric", "strictly_positive",
            "consecutive_gregorian_annual_observations"]:
        raise HandoffError(
            "both FX observations must be present, numeric, strictly "
            "positive and consecutive annual observations")
    if "PA.NUS.ATLS" not in (fx.get("forbidden_substitutions") or []):
        raise HandoffError(
            "PA.NUS.ATLS must remain an explicitly forbidden substitution")

    # --- Sample and feature architecture --------------------------------- #
    parent = contract.get("parent_sample") or {}
    if parent.get("expected_parent_rows") != 539:
        raise HandoffError(
            "the parent sample is the retained-M2 539-row development sample")
    if parent.get("original_666_row_m1_comparison_sample_permitted") is not (
            False):
        raise HandoffError(
            "the original 666-row M1 comparison sample may not be used")
    if parent.get("scope") != "development_only":
        raise HandoffError("the parent sample scope is development only")
    comparator = contract.get("m2_comparator") or {}
    if comparator.get("feature_count") != 12 or len(
            comparator.get("feature_order") or []) != 12:
        raise HandoffError("the M2 comparator has exactly 12 features")
    if comparator.get("m2_status") != (
            "RETAIN_M2_AS_INTERMEDIATE_CONFIRMATORY_BLOCK"):
        raise HandoffError(
            "M2 remains RETAIN_M2_AS_INTERMEDIATE_CONFIRMATORY_BLOCK")
    order = contract.get("m3_lag_wdi_feature_order") or []
    if contract.get("feature_count_total") != 14 or len(order) != 14:
        raise HandoffError("M3-LAG-WDI has exactly 14 features")
    if order[:12] != list(comparator.get("feature_order") or []):
        raise HandoffError(
            "M3-LAG-WDI must be the M2 feature set plus the two lagged WDI "
            "features")
    if order[12:] != [fid for fid, _ in _STAGE128_M3_LAG_FEATURES]:
        raise HandoffError(
            "the last two M3-LAG-WDI features are the locked lagged WDI pair")
    complete_case = contract.get("complete_case_policy") or {}
    for field in ("both_lagged_wdi_features_required_complete",
                  "m2_and_m3_lag_wdi_refit_on_the_same_resulting_common_"
                  "sample"):
        if complete_case.get(field) is not True:
            raise HandoffError(f"complete-case policy {field} must be True")
    for field in ("imputation_permitted",
                  "previous_666_row_m1_results_reusable_as_comparator"):
        if complete_case.get(field) is not False:
            raise HandoffError(f"complete-case policy {field} must be False")

    # --- WDI vintage semantics: the honest limitation -------------------- #
    vintage = contract.get("wdi_vintage_semantics") or {}
    for field in ("current_or_latest_revised_wdi_allowed",
                  "retrieval_uses_then_current_official_latest_wdi_values",
                  "revisions_may_be_present",
                  "limitation_is_why_the_analysis_is_exploratory_"
                  "supplementary"):
        if vintage.get(field) is not True:
            raise HandoffError(f"WDI vintage semantics {field} must be True")
    for field in ("historical_vintage_availability_claimed",
                  "point_in_time_availability_claimed",
                  "lagging_transforms_revised_wdi_into_point_in_time_data",
                  "release_date_proof_attempted"):
        if vintage.get(field) is not False:
            raise HandoffError(f"WDI vintage semantics {field} must be False")

    # --- Data Gate: frozen, inherited thresholds, NOT executed ----------- #
    thresholds = gate.get("thresholds") or {}
    if thresholds.get("candidate_valid_coverage_min") != 0.8:
        raise HandoffError("individual candidate coverage must be >= 0.80")
    if thresholds.get("block_common_sample_coverage_min") != 0.7:
        raise HandoffError("block common-sample coverage must be >= 0.70")
    if thresholds.get(
            "minimum_positive_evaluable_each_locked_validation_window") != 5:
        raise HandoffError(
            ">= 5 positive outcomes are required in EACH locked validation "
            "window")
    if thresholds.get("expected_parent_rows") != 539:
        raise HandoffError("the Gate denominator is the 539-row sample")
    if thresholds.get("coverage_scope") != "development_only":
        raise HandoffError("the Gate is development-only")
    if gate.get("thresholds_inherited_not_redesigned") is not True:
        raise HandoffError("the Gate thresholds are inherited, not redesigned")
    if gate.get("gate_executed") is not False or gate.get(
            "gate_result") != "NOT_EXECUTED":
        raise HandoffError("the M3-LAG-WDI Data Gate must be NOT_EXECUTED")
    if gate.get("gate_pass_is_data_admission_only") is not True:
        raise HandoffError("a Gate PASS is data admission only")
    for field in ("gate_pass_authorizes_modeling",
                  "gate_pass_unlocks_final_test"):
        if gate.get(field) is not False:
            raise HandoffError(f"M3-LAG-WDI Gate {field} must be False")
    if gate.get("unresolved_values_are_null_not_zero") is not True:
        raise HandoffError("unresolved coverage values are null, not zero")
    for name, value in (gate.get("observed_values") or {}).items():
        if value is not None:
            raise HandoffError(
                f"observed Gate value {name} must stay null before execution")

    # --- Modeling: three frozen families, separate family, no Holm ------- #
    if list(modeling.get("model_families") or []) != [
            "regularized_logistic_regression", "random_forest", "xgboost"]:
        raise HandoffError(
            "the future evaluation uses exactly the three retained M2 model "
            "families")
    for field in ("retuning_permitted", "grid_search_permitted",
                  "hyperparameter_search_permitted",
                  "model_family_search_permitted",
                  "new_secondary_metrics_defined_by_this_action",
                  "exploratory_comparison_inserted_into_confirmatory_holm_"
                  "family",
                  "confirmatory_holm_family_changed_by_this_action",
                  "confirmatory_superiority_claim_permitted",
                  "modeling_authorized", "modeling_started"):
        if modeling.get(field) is not False:
            raise HandoffError(f"M3-LAG-WDI modeling contract {field} is False")
    for field in ("inherits_canonical_metric_definitions",
                  "inherits_locked_validation_architecture",
                  "inherits_seed_policy",
                  "inherits_bootstrap_and_paired_comparison_machinery",
                  "retained_configurations_used_unchanged"):
        if modeling.get(field) is not True:
            raise HandoffError(f"M3-LAG-WDI modeling contract {field} is True")
    if tuple(modeling.get("confirmatory_holm_family") or ()) != (
            _STAGE128_M3_LAG_CONFIRMATORY_FAMILY):
        raise HandoffError(
            "the confirmatory Holm family must stay "
            f"{list(_STAGE128_M3_LAG_CONFIRMATORY_FAMILY)}")
    family_id = modeling.get("comparison_family_id")
    if not family_id or family_id in _STAGE128_M3_LAG_CONFIRMATORY_FAMILY:
        raise HandoffError(
            "the exploratory comparison needs its OWN family identity")
    for field in ("comparisons_executed", "holm_executions",
                  "bootstrap_executions", "model_fits",
                  "supplementary_family_size_now"):
        if modeling.get(field) != 0:
            raise HandoffError(f"M3-LAG-WDI modeling {field} must be 0")

    # --- Zero execution -------------------------------------------------- #
    for field in ("retrieval_started", "data_gate_executed",
                  "modeling_started",
                  "earlier_historical_vintage_bundle_used_as_value_input"):
        if audit.get(field) is not False:
            raise HandoffError(f"M3-LAG-WDI execution audit {field} is False")
    for field in ("final_test_rows_read", "final_test_predictor_values_read",
                  "final_test_target_values_read",
                  "scientific_artifacts_regenerated"):
        if audit.get(field) != 0:
            raise HandoffError(f"M3-LAG-WDI execution audit {field} must be 0")
    counters = audit.get("counters") or {}
    if not counters:
        raise HandoffError("the M3-LAG-WDI execution audit must be explicit")
    for name, value in counters.items():
        if value != 0:
            raise HandoffError(
                f"M3-LAG-WDI execution counter {name} must be 0")

    # --- Governance: Track A untouched, Track B locked but unauthorized -- #
    if boundary.get("m3_lag_wdi_authoritative_contract_status") != (
            _STAGE128_M3_LAG_LOCKED_STATUS):
        raise HandoffError(
            "the M3-LAG-WDI contract status must be "
            f"{_STAGE128_M3_LAG_LOCKED_STATUS}")
    if boundary.get("m3_lag_wdi_exploratory_contract_locked") is not True:
        raise HandoffError("the M3-LAG-WDI contract must be locked")
    if boundary.get("world_bank_inquiry_status") != (
            _STAGE128_M3I2_HUMAN_SUBMITTED_STATUS):
        raise HandoffError(
            "the World Bank inquiry must stay "
            f"{_STAGE128_M3I2_HUMAN_SUBMITTED_STATUS}")
    if boundary.get("world_bank_waiting_period_status") != "ACTIVE":
        raise HandoffError("the World Bank waiting period must stay ACTIVE")
    if boundary.get("world_bank_waiting_period_completion_date") != (
            "2026-08-20"):
        raise HandoffError("the waiting period completes on 2026-08-20")
    if boundary.get(
            "world_bank_waiting_period_earliest_follow_up_date") != (
            "2026-08-21"):
        raise HandoffError("the earliest possible follow-up is 2026-08-21")
    for field in ("world_bank_inquiry_terminated_by_this_action",
                  "world_bank_follow_up_authorized",
                  "world_bank_response_ingestion_authorized",
                  "parallel_activation_implies_inquiry_failed",
                  "parallel_activation_implies_inquiry_terminated",
                  "parallel_activation_implies_inquiry_unnecessary",
                  "m3_lag_wdi_data_retrieval_started",
                  "m3_lag_wdi_data_gate_executed",
                  "m3_lag_wdi_modeling_started",
                  "m3_lag_wdi_next_action_authorized",
                  "m3_lag_wdi_local_partial_draft_authoritative",
                  "m3_lag_wdi_local_partial_draft_modified_by_this_action",
                  "m3_lag_wdi_local_partial_draft_committed_by_this_action",
                  "m3_lag_wdi_prior_authorization_reusable",
                  "m3_cbi_modified_by_this_action",
                  "m3i2_conclusions_modified_by_this_action",
                  "observed_m1_m2_results_modified_by_this_action",
                  "final_test_access_authorized",
                  "final_test_unlock_implied_by_contract_lock",
                  "final_test_unlock_implied_by_gate_pass",
                  "final_test_unlock_implied_by_successful_retrieval",
                  "m4_authorized", "m4_started", "merge_authorized",
                  "auto_merge", "ready_for_review_authorized",
                  "paper_winner_selected"):
        if boundary.get(field) is not False:
            raise HandoffError(
                f"M3-LAG-WDI governance boundary {field} must be False")
    if boundary.get("final_test_locked") is not True:
        raise HandoffError("the Final Test must stay locked")
    if boundary.get("m3_cbi_status") != "UNRESOLVED_M3_DATA_GATE":
        raise HandoffError("the M3-CBI Gate status must be preserved")
    if boundary.get("m3i2_evidence_status") != (
            "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE"):
        raise HandoffError("M3I-2 evidence must remain UNRESOLVED")
    if boundary.get("prior_restriction_status") != (
            "SUPERSEDED_BY_NEW_EXPLICIT_HUMAN_AUTHORIZATION"):
        raise HandoffError(
            "the prior wait-only restriction is superseded by the new "
            "explicit human authorization")
    if boundary.get("prior_restriction_retained_as_history") is not True:
        raise HandoffError(
            "the prior restriction must be retained as history, not deleted")
    if boundary.get("m3_lag_wdi_next_action_id") != (
            _STAGE128_M3_LAG_NEXT_ACTION_ID):
        raise HandoffError(
            "the Track B next action is "
            f"{_STAGE128_M3_LAG_NEXT_ACTION_ID}")

    # --- Authorization: new, one-action, consumed, never reusable -------- #
    for field in ("authorization_consumed",
                  "authorization_consumed_by_this_contract_lock",
                  "supersedes_only_the_prior_wait_for_terminal_inquiry_"
                  "restriction"):
        if authorization.get(field) is not True:
            raise HandoffError(f"M3-LAG-WDI authorization {field} must be True")
    for field in ("standing_authorization", "scope_identified_by_hash_alone",
                  "authorization_is_reusable_for_retrieval",
                  "authorization_is_reusable_for_data_gate",
                  "authorization_is_reusable_for_modeling",
                  "prior_local_draft_authorization_reused",
                  "terminates_or_resolves_the_world_bank_inquiry",
                  "merge_authorized"):
        if authorization.get(field) is not False:
            raise HandoffError(
                f"M3-LAG-WDI authorization {field} must be False")
    if authorization.get("expected_baseline_sha") != decision.get(
            "expected_baseline_sha"):
        raise HandoffError(
            "the authorization and the decision must name the same baseline")
    auth_sha = authorization.get("authorization_sha256")
    if not (isinstance(auth_sha, str) and len(auth_sha) == 64):
        raise HandoffError("the authorization SHA-256 must be a 64-hex digest")
    auth_text = authorization.get("authorization_text")
    if not isinstance(auth_text, str) or not auth_text:
        raise HandoffError("the exact human authorization text is required")
    recomputed = hashlib.sha256(auth_text.encode("utf-8"))
    if recomputed.hexdigest() != auth_sha:
        raise HandoffError(
            "the recorded authorization SHA-256 does not match its text")
    if authorization.get("authorization_utf8_bytes") != len(
            auth_text.encode("utf-8")):
        raise HandoffError(
            "the recorded authorization byte length does not match its text")

    # --- Decision: scientific effect NONE, pointers unmoved -------------- #
    if decision.get("scientific_effect") != "NONE":
        raise HandoffError("a contract lock has no scientific effect")
    if decision.get("contract_status") != _STAGE128_M3_LAG_LOCKED_STATUS:
        raise HandoffError(
            "the decision must publish the locked contract status")
    for field in ("authorizes_next_action", "track_b_next_action_authorized",
                  "next_research_action_authorized", "merge_authorized",
                  "m4_authorized", "paper_winner_selected"):
        if decision.get(field) is not False:
            raise HandoffError(f"M3-LAG-WDI decision {field} must be False")
    if decision.get("final_test_locked") is not True:
        raise HandoffError("the M3-LAG-WDI decision keeps the Final Test locked")
    # Track A owns the research pointers; a parallel Track B lock never moves
    # them, and it never advances the World Bank inquiry.
    if decision.get("last_completed_research_action_id") != (
            _STAGE128_M3I2_INQUIRY_SUBMISSION_ACTION_ID):
        raise HandoffError(
            "Track B does not take over the Track A research pointers")
    if decision.get("next_research_action_id") != (
            _STAGE128_M3I2_INQUIRY_RESPONSE_INGESTION_ACTION_ID):
        raise HandoffError(
            "the live research pointer stays "
            f"{_STAGE128_M3I2_INQUIRY_RESPONSE_INGESTION_ACTION_ID}")
    if decision.get("verified_wdi_release_dates") != 0 or decision.get(
            "verified_pre_cutoff_editions") != 0:
        raise HandoffError(
            "a contract lock verifies no release date and no edition")
    if decision.get("unresolved_cutoffs") != decision.get(
            "unresolved_cutoffs_total"):
        raise HandoffError("every M3I-2 cutoff must remain unresolved")
    if decision.get("unresolved_development_pairs") != decision.get(
            "unresolved_development_pairs_total"):
        raise HandoffError("every M3I-2 development pair must remain unresolved")

    # --- LIVE PR topology: a MERGED PR is never the live Draft ----------- #
    live_number = topology.get("live_pr_number")
    predecessor_number = topology.get("predecessor_pr_number")
    for value, label in ((live_number, "live"),
                         (predecessor_number, "predecessor")):
        if not isinstance(value, int) or isinstance(value, bool):
            raise HandoffError(
                f"the M3-LAG-WDI {label} PR number must be an integer")
    if predecessor_number != _STAGE128_M3_LAG_MERGED_PREDECESSOR_PR:
        raise HandoffError(
            "the merged predecessor of the M3-LAG-WDI PR is PR "
            f"#{_STAGE128_M3_LAG_MERGED_PREDECESSOR_PR}")
    if live_number <= predecessor_number:
        raise HandoffError(
            f"the live PR #{live_number} must succeed the merged predecessor "
            f"PR #{predecessor_number}")
    base_commit = topology.get("live_pr_base_commit")
    merge_commit = topology.get("predecessor_pr_merge_commit")
    for value, label in ((base_commit, "live PR base"),
                         (merge_commit, "predecessor merge")):
        if not (isinstance(value, str) and len(value) == 40):
            raise HandoffError(
                f"the M3-LAG-WDI {label} commit must be a full 40-hex SHA")
    if merge_commit != _STAGE128_M3_LAG_MERGED_PREDECESSOR_COMMIT:
        raise HandoffError(
            f"PR #{_STAGE128_M3_LAG_MERGED_PREDECESSOR_PR} was merged by "
            f"{_STAGE128_M3_LAG_MERGED_PREDECESSOR_COMMIT}")
    if base_commit != merge_commit:
        raise HandoffError(
            "the live M3-LAG-WDI PR must be based on the merge commit of its "
            "merged predecessor")
    if topology.get("live_pr_base_branch") != _STAGE128_M3I2_LIVE_BASE_BRANCH:
        raise HandoffError(
            f"the live PR must target {_STAGE128_M3I2_LIVE_BASE_BRANCH}")
    for field, expected in (
        ("predecessor_pr_merged", True),
        ("live_pr_is_draft", True),
        ("live_pr_merged", False),
        ("merge_authorized", False),
        ("auto_merge", False),
        ("ready_for_review_authorized", False),
        ("pr_is_stacked_on_open_predecessor", False),
        ("live_pr_head_commit_pinned", False),
        ("live_pr_head_is_github_pr_head", False),
    ):
        if topology.get(field) is not expected:
            raise HandoffError(
                f"M3-LAG-WDI topology {field} must be {expected}")
    if topology.get("live_pr_head_semantics") != (
            _STAGE128_M3I2_LIVE_PR_HEAD_SEMANTICS):
        raise HandoffError(
            "the live PR head semantics must be "
            f"{_STAGE128_M3I2_LIVE_PR_HEAD_SEMANTICS}")

    # --- HISTORICAL PR ROLES: pinned, never re-derived from adjacency ---- #
    # Re-anchoring the LIVE topology onto PR #78 must not shift what PR #76
    # and PR #77 *were*. Each historical role is checked against its pinned
    # fact, and the three roles are required to stay three distinct PRs.
    for field, expected, label in (
        ("documentary_recovery_pr_number",
         _STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR,
         "the documentary-recovery INITIATION PR number"),
        ("documentary_recovery_pr_merge_commit",
         _STAGE128_M3I2_DOCUMENTARY_RECOVERY_MERGE_COMMIT,
         "the documentary-recovery PR merge commit"),
        ("documentary_recovery_pr_role",
         _STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR_ROLE,
         "the documentary-recovery PR role"),
        ("documentary_recovery_pr_action_id",
         _STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR_ACTION_ID,
         "the documentary-recovery PR action id"),
        ("documentary_recovery_pr_semantics",
         _STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR_SEMANTICS,
         "the documentary-recovery PR supersession semantics"),
        ("human_submission_pr_number", _STAGE128_M3I2_HUMAN_SUBMISSION_PR,
         "the human-submission RECORDING PR number"),
        ("human_submission_pr_merge_commit",
         _STAGE128_M3I2_HUMAN_SUBMISSION_MERGE_COMMIT,
         "the human-submission PR merge commit"),
        ("human_submission_pr_role", _STAGE128_M3I2_HUMAN_SUBMISSION_PR_ROLE,
         "the human-submission PR role"),
        ("human_submission_pr_action_id",
         _STAGE128_M3I2_HUMAN_SUBMISSION_PR_ACTION_ID,
         "the human-submission PR action id"),
    ):
        if topology.get(field) != expected:
            raise HandoffError(f"{label} is pinned to {expected!r}")
    for field in ("documentary_recovery_pr_merged",
                  "human_submission_pr_merged",
                  "pr_roles_are_historical_facts_not_positional",
                  "recovery_pr_role_is_pinned_to_pr76"):
        if topology.get(field) is not True:
            raise HandoffError(f"M3-LAG-WDI topology {field} must be True")
    if topology.get("pr_roles_re_derived_from_adjacency") is not False:
        raise HandoffError(
            "PR roles may never be re-derived from adjacency: 'the recovery "
            "PR' is PR #76, not 'the PR that merged most recently'")
    recovery_number = topology.get("documentary_recovery_pr_number")
    submission_number = topology.get("human_submission_pr_number")
    if not (recovery_number < submission_number < live_number):
        raise HandoffError(
            "the three PR roles must stay three distinct PRs in order: "
            f"#{recovery_number} (documentary recovery initiation) -> "
            f"#{submission_number} (human submission recording) -> "
            f"#{live_number} (live Draft contract lock)")
    if topology.get("documentary_recovery_pr_merge_commit") == topology.get(
            "human_submission_pr_merge_commit"):
        raise HandoffError(
            "the documentary-recovery and human-submission PRs were merged by "
            "two DIFFERENT commits")
    sequence = topology.get("pr_role_sequence") or []
    expected_sequence = [
        (_STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR,
         _STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR_ROLE, True,
         _STAGE128_M3I2_DOCUMENTARY_RECOVERY_MERGE_COMMIT),
        (_STAGE128_M3I2_HUMAN_SUBMISSION_PR,
         _STAGE128_M3I2_HUMAN_SUBMISSION_PR_ROLE, True,
         _STAGE128_M3I2_HUMAN_SUBMISSION_MERGE_COMMIT),
        (live_number, topology.get("live_pr_role"), False, None),
    ]
    if [(entry.get("pr_number"), entry.get("role"), entry.get("merged"),
         entry.get("merge_commit")) for entry in sequence] != (
            expected_sequence):
        raise HandoffError(
            "the published PR role sequence must be exactly "
            f"#{_STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR} -> "
            f"#{_STAGE128_M3I2_HUMAN_SUBMISSION_PR} -> #{live_number}")

    # --- Retrieval, the Data Gate and modeling are SEPARATE actions ------ #
    # An authorization boundary only exists where an action boundary exists.
    # The immediate Track B pointer is retrieval ONLY; the Gate is its own
    # action needing its own new human authorization; and a Gate PASS admits
    # data without authorizing a single model fit.
    for field, expected, source, label in (
        ("m3_lag_wdi_next_action_id", _STAGE128_M3_LAG_NEXT_ACTION_ID,
         boundary, "the immediate Track B pointer"),
        ("m3_lag_wdi_next_action_scope", _STAGE128_M3_LAG_NEXT_ACTION_SCOPE,
         boundary, "the immediate Track B pointer scope"),
        ("m3_lag_wdi_retrieval_action_id",
         _STAGE128_M3_LAG_RETRIEVAL_ACTION_ID, boundary,
         "the retrieval action id"),
        ("m3_lag_wdi_post_retrieval_audit_action_id",
         _STAGE128_M3_LAG_POST_RETRIEVAL_AUDIT_ACTION_ID, boundary,
         "the post-retrieval audit action id"),
        ("m3_lag_wdi_data_gate_action_id",
         _STAGE128_M3_LAG_DATA_GATE_ACTION_ID, boundary,
         "the Data Gate action id"),
        ("m3_lag_wdi_modeling_action_id", _STAGE128_M3_LAG_MODELING_ACTION_ID,
         boundary, "the modeling action id"),
        ("gate_action_id", _STAGE128_M3_LAG_DATA_GATE_ACTION_ID, gate,
         "the Gate contract's own action id"),
        ("retrieval_action_id", _STAGE128_M3_LAG_RETRIEVAL_ACTION_ID, gate,
         "the Gate contract's retrieval action id"),
        ("modeling_action_id", _STAGE128_M3_LAG_MODELING_ACTION_ID, modeling,
         "the modeling contract's action id"),
        ("gate_action_id", _STAGE128_M3_LAG_DATA_GATE_ACTION_ID, modeling,
         "the modeling contract's Gate action id"),
    ):
        if source.get(field) != expected:
            raise HandoffError(f"{label} must be {expected}")
    if _STAGE128_M3_LAG_RETRIEVAL_ACTION_ID == (
            _STAGE128_M3_LAG_DATA_GATE_ACTION_ID):
        raise HandoffError(
            "retrieval and the Data Gate may not share one action identity")
    # Nothing anywhere may say that retrieving authorizes or executes the Gate,
    # that the Gate may be bundled into retrieval, or that a PASS authorizes
    # modeling.
    for field, source, label in (
        ("m3_lag_wdi_retrieval_action_authorized", boundary, "boundary"),
        ("m3_lag_wdi_retrieval_action_executes_data_gate", boundary,
         "boundary"),
        ("m3_lag_wdi_next_action_executes_data_gate", boundary, "boundary"),
        ("m3_lag_wdi_retrieval_authorization_implies_gate_authorization",
         boundary, "boundary"),
        ("m3_lag_wdi_combined_retrieval_and_gate_action_permitted", boundary,
         "boundary"),
        ("m3_lag_wdi_data_gate_action_authorized", boundary, "boundary"),
        ("m3_lag_wdi_post_retrieval_audit_action_authorized", boundary,
         "boundary"),
        ("m3_lag_wdi_post_retrieval_audit_executes_data_gate", boundary,
         "boundary"),
        ("m3_lag_wdi_gate_pass_authorizes_modeling", boundary, "boundary"),
        ("gate_executed_by_retrieval_action", gate, "Gate contract"),
        ("retrieval_authorization_implies_gate_authorization", gate,
         "Gate contract"),
        ("combined_retrieval_and_gate_action_permitted", gate,
         "Gate contract"),
        ("post_retrieval_audit_action_executes_gate", gate, "Gate contract"),
        ("gate_action_authorized", gate, "Gate contract"),
        ("gate_pass_authorizes_modeling", gate, "Gate contract"),
        ("gate_pass_authorizes_modeling", modeling, "modeling contract"),
        ("modeling_authorized_by_gate_pass", modeling, "modeling contract"),
    ):
        if source.get(field) is not False:
            raise HandoffError(f"the {label} field {field} must be False")
    for field, source, label in (
        ("m3_lag_wdi_data_gate_is_a_separate_action_from_retrieval", boundary,
         "boundary"),
        ("m3_lag_wdi_data_gate_requires_new_explicit_human_authorization",
         boundary, "boundary"),
        ("m3_lag_wdi_retrieval_requires_new_explicit_human_authorization",
         boundary, "boundary"),
        ("m3_lag_wdi_modeling_requires_new_explicit_human_authorization",
         boundary, "boundary"),
        ("m3_lag_wdi_gate_pass_is_data_admission_only", boundary, "boundary"),
        ("m3_lag_wdi_gate_pointer_is_not_authorization", boundary,
         "boundary"),
        ("gate_is_a_separate_action_from_retrieval", gate, "Gate contract"),
        ("gate_requires_new_explicit_human_authorization", gate,
         "Gate contract"),
        ("gate_pointer_is_not_authorization", gate, "Gate contract"),
        ("gate_pass_is_data_admission_only", gate, "Gate contract"),
        ("modeling_requires_separate_explicit_human_authorization", gate,
         "Gate contract"),
        ("gate_pass_is_data_admission_only", modeling, "modeling contract"),
        ("modeling_requires_new_explicit_human_authorization", modeling,
         "modeling contract"),
    ):
        if source.get(field) is not True:
            raise HandoffError(f"the {label} field {field} must be True")
    published_sequence = boundary.get("m3_lag_wdi_action_sequence") or []
    if [(entry.get("step"), entry.get("action_id"),
         entry.get("executes_retrieval"), entry.get("executes_data_gate"),
         entry.get("executes_modeling"))
            for entry in published_sequence] != list(
                _STAGE128_M3_LAG_ACTION_SEQUENCE):
        raise HandoffError(
            "the Track B action sequence must separate contract lock -> "
            "retrieval -> post-retrieval audit -> Data Gate -> modeling, with "
            "exactly one executing step each")
    for entry in published_sequence:
        if entry.get("executes_retrieval") and entry.get(
                "executes_data_gate"):
            raise HandoffError(
                f"action {entry.get('action_id')!r} both retrieves and "
                "executes the Data Gate: that is a conflated action")
        if entry.get("step") != "A" and entry.get("authorized") is not False:
            raise HandoffError(
                f"future Track B action {entry.get('action_id')!r} must be "
                "unauthorized")

    return {
        # Track B: the contract is LOCKED, and locked is not authorized.
        "stage128_m3_lag_wdi_exploratory_contract_locked": True,
        "stage128_m3_lag_wdi_authoritative_contract_status":
            _STAGE128_M3_LAG_LOCKED_STATUS,
        "stage128_m3_lag_wdi_scientific_role": _STAGE128_M3_LAG_ROLE,
        "stage128_m3_lag_wdi_is_confirmatory_m3": False,
        "stage128_m3_lag_wdi_feature_count": 14,
        "stage128_m3_lag_wdi_additional_feature_count": 2,
        "stage128_m3_lag_wdi_m2_comparator_feature_count": 12,
        "stage128_m3_lag_wdi_parent_sample_rows": 539,
        "stage128_m3_lag_wdi_cpi_indicator_code": _STAGE128_M3_LAG_FEATURES[0][1],
        "stage128_m3_lag_wdi_fx_indicator_code": _STAGE128_M3_LAG_FEATURES[1][1],
        "stage128_m3_lag_wdi_observation_year_rule": "t - 1",
        "stage128_m3_lag_wdi_fx_transformation":
            _STAGE128_M3_LAG_FX_FORMULA_EQUIVALENT,
        "stage128_m3_lag_wdi_point_in_time_availability_claimed": False,
        "stage128_m3_lag_wdi_current_revised_wdi_semantics": True,
        "stage128_m3_lag_wdi_comparison_family_id": family_id,
        "stage128_m3_lag_wdi_in_confirmatory_holm_family": False,
        "stage128_m3_lag_wdi_data_retrieval_started": False,
        "stage128_m3_lag_wdi_data_gate_executed": False,
        "stage128_m3_lag_wdi_data_gate_result": "NOT_EXECUTED",
        # DERIVED, never hard-coded: step E flips this, and a marker
        # function must not publish a moment as if it were a rule.
        "stage128_m3_lag_wdi_modeling_started":
            _stage128_m3_lag_modeling_started(root),
        "stage128_m3_lag_wdi_modeling_authorized": False,
        "stage128_m3_lag_wdi_final_test_rows_read": 0,
        # The immediate pointer is RETRIEVAL ONLY. The Data Gate and modeling
        # are separate later actions, each with its own identity and its own
        # required new human authorization.
        "stage128_m3_lag_wdi_next_action_id": _STAGE128_M3_LAG_NEXT_ACTION_ID,
        "stage128_m3_lag_wdi_next_action_authorized": False,
        "stage128_m3_lag_wdi_next_action_scope":
            _STAGE128_M3_LAG_NEXT_ACTION_SCOPE,
        # Derived from the action the pointer names (here: retrieval → False).
        "stage128_m3_lag_wdi_next_action_executes_data_gate":
            _stage128_m3_lag_action_executes_data_gate(
                _STAGE128_M3_LAG_NEXT_ACTION_ID),
        "stage128_m3_lag_wdi_retrieval_action_id":
            _STAGE128_M3_LAG_RETRIEVAL_ACTION_ID,
        "stage128_m3_lag_wdi_retrieval_authorized": False,
        "stage128_m3_lag_wdi_retrieval_executes_data_gate": False,
        "stage128_m3_lag_wdi_retrieval_requires_new_human_authorization": True,
        "stage128_m3_lag_wdi_post_retrieval_audit_action_id":
            _STAGE128_M3_LAG_POST_RETRIEVAL_AUDIT_ACTION_ID,
        "stage128_m3_lag_wdi_post_retrieval_audit_authorized": False,
        "stage128_m3_lag_wdi_post_retrieval_audit_executes_data_gate": False,
        "stage128_m3_lag_wdi_data_gate_action_id":
            _STAGE128_M3_LAG_DATA_GATE_ACTION_ID,
        "stage128_m3_lag_wdi_data_gate_authorized": False,
        "stage128_m3_lag_wdi_data_gate_is_a_separate_action": True,
        "stage128_m3_lag_wdi_data_gate_requires_new_human_authorization": True,
        "stage128_m3_lag_wdi_data_gate_pointer_is_not_authorization": True,
        "stage128_m3_lag_wdi_retrieval_authorization_implies_gate_"
        "authorization": False,
        "stage128_m3_lag_wdi_combined_retrieval_and_gate_action_permitted":
            False,
        "stage128_m3_lag_wdi_gate_pass_is_data_admission_only": True,
        "stage128_m3_lag_wdi_gate_pass_authorizes_modeling": False,
        "stage128_m3_lag_wdi_modeling_action_id":
            _STAGE128_M3_LAG_MODELING_ACTION_ID,
        "stage128_m3_lag_wdi_modeling_requires_new_human_authorization": True,
        "stage128_m3_lag_wdi_action_sequence": [
            {
                "step": step,
                "action_id": action_id,
                "executes_retrieval": executes_retrieval,
                "executes_data_gate": executes_gate,
                "executes_modeling": executes_modeling,
                "authorized": step == "A",
            }
            for (step, action_id, executes_retrieval, executes_gate,
                 executes_modeling) in _STAGE128_M3_LAG_ACTION_SEQUENCE
        ],
        "stage128_m3_lag_wdi_authorization_sha256": auth_sha,
        "stage128_m3_lag_wdi_authorization_utf8_bytes":
            authorization.get("authorization_utf8_bytes"),
        "stage128_m3_lag_wdi_authorization_consumed": True,
        "stage128_m3_lag_wdi_prior_restriction_status":
            boundary.get("prior_restriction_status"),
        # The quarantined draft stays quarantined and untouched.
        "stage128_m3_lag_wdi_local_partial_draft_detected": True,
        "stage128_m3_lag_wdi_local_partial_draft_quarantined": True,
        "stage128_m3_lag_wdi_local_partial_draft_authoritative": False,
        "stage128_m3_lag_wdi_prior_authorization_reusable": False,
        # Track A is untouched and still waiting.
        "stage128_m3i2_inquiry_terminated_by_track_b": False,
        "stage128_m3i2_response_adjudication_authorized": False,
        "stage128_m3i2_inquiry_follow_up_authorized_now": False,
        # LIVE topology re-anchored onto THIS Draft PR; PR #77 is history.
        "stage128_m3i2_live_pr_number": live_number,
        "stage128_m3i2_live_pr_base_branch":
            topology.get("live_pr_base_branch"),
        "stage128_m3i2_live_pr_base_commit": base_commit,
        "stage128_m3i2_live_main_commit": base_commit,
        "stage128_m3i2_live_pr_is_draft": True,
        "stage128_m3i2_live_pr_merged": False,
        "stage128_m3i2_live_pr_role": topology.get("live_pr_role"),
        "stage128_m3i2_live_pr_head_commit_source":
            _STAGE128_M3I2_LIVE_PR_HEAD_SEMANTICS,
        "stage128_m3i2_live_pr_ready_for_review_authorized": False,
        # HISTORY IS PINNED, NOT RE-DERIVED. "The recovery PR" names the
        # documentary-recovery INITIATION carried by PR #76; it does NOT mean
        # "the PR that merged immediately before the live one". The later
        # human-submission RECORDING carried by PR #77 keeps its own separate
        # identity, and PR #78 is the live Draft. Three actions, three PRs.
        "stage128_m3i2_recovery_pr_number":
            _STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR,
        "stage128_m3i2_recovery_pr_merged": True,
        "stage128_m3i2_recovery_pr_merge_commit":
            _STAGE128_M3I2_DOCUMENTARY_RECOVERY_MERGE_COMMIT,
        "stage128_m3i2_recovery_pr_role":
            _STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR_ROLE,
        "stage128_m3i2_recovery_pr_action_id":
            _STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR_ACTION_ID,
        "stage128_m3i2_recovery_pr_semantics":
            _STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR_SEMANTICS,
        "stage128_m3i2_human_submission_pr_number":
            _STAGE128_M3I2_HUMAN_SUBMISSION_PR,
        "stage128_m3i2_human_submission_pr_merged": True,
        "stage128_m3i2_human_submission_pr_merge_commit":
            _STAGE128_M3I2_HUMAN_SUBMISSION_MERGE_COMMIT,
        "stage128_m3i2_human_submission_pr_role":
            _STAGE128_M3I2_HUMAN_SUBMISSION_PR_ROLE,
        "stage128_m3i2_human_submission_pr_action_id":
            _STAGE128_M3I2_HUMAN_SUBMISSION_PR_ACTION_ID,
        "stage128_m3i2_human_submission_pr_semantics": (
            "merged_predecessor_superseded_by_pr" f"{live_number}"),
        "stage128_m3i2_pr_roles_are_historical_facts_not_positional": True,
        "stage128_m3i2_pr_role_sequence": [
            {
                "pr_number": entry[0],
                "role": entry[1],
                "merged": entry[2],
                "merge_commit": entry[3],
            }
            for entry in expected_sequence
        ],
        "stage128_m3i2_merge_authorized": False,
    }


_STAGE128_M3_LAG_RETRIEVAL_PKG = (
    "project/stage128/m3_lag_wdi_exploratory_data_retrieval")
_STAGE128_M3_LAG_RETRIEVAL_MANIFEST_REL = (
    f"{_STAGE128_M3_LAG_RETRIEVAL_PKG}/"
    "stage128_m3_lag_wdi_retrieval_source_manifest.json")
_STAGE128_M3_LAG_RETRIEVAL_AUDIT_REL = (
    f"{_STAGE128_M3_LAG_RETRIEVAL_PKG}/"
    "stage128_m3_lag_wdi_retrieval_execution_audit.json")
_STAGE128_M3_LAG_RETRIEVAL_BOUNDARY_REL = (
    f"{_STAGE128_M3_LAG_RETRIEVAL_PKG}/"
    "stage128_m3_lag_wdi_retrieval_governance_boundary.json")
_STAGE128_M3_LAG_RETRIEVAL_AUTH_REL = (
    f"{_STAGE128_M3_LAG_RETRIEVAL_PKG}/"
    "stage128_m3_lag_wdi_retrieval_human_authorization_record.json")
_STAGE128_M3_LAG_RETRIEVAL_DECISION_REL = (
    f"{_STAGE128_M3_LAG_RETRIEVAL_PKG}/"
    "stage128_m3_lag_wdi_retrieval_decision.json")
_STAGE128_M3_LAG_RETRIEVAL_TOPOLOGY_REL = (
    f"{_STAGE128_M3_LAG_RETRIEVAL_PKG}/"
    "stage128_m3_lag_wdi_retrieval_pr_topology.json")

#: PR #78 (the M3-LAG-WDI exploratory CONTRACT LOCK) was merged into main by
#: this commit, and PR #79 (this retrieval) is the current LIVE Draft. Both
#: halves are pinned, because "live > predecessor" alone would still accept a
#: topology that re-published the merged #78 as the live Draft.
_STAGE128_M3_LAG_RETRIEVAL_MERGED_PREDECESSOR_PR = 78
_STAGE128_M3_LAG_RETRIEVAL_MERGED_PREDECESSOR_COMMIT = (
    "175e7949e009eeecdd66aedab31ec4b48e9d3c7d")
_STAGE128_M3_LAG_RETRIEVAL_MERGED_PREDECESSOR_ROLE = (
    "m3_lag_wdi_exploratory_contract_lock_pr")
_STAGE128_M3_LAG_RETRIEVAL_MERGED_PREDECESSOR_ACTION_ID = (
    "stage128-m3-lag-wdi-exploratory-contract-lock")
_STAGE128_M3_LAG_RETRIEVAL_LIVE_PR_ROLE = (
    "m3_lag_wdi_exploratory_data_retrieval_pr")
_STAGE128_M3_LAG_RETRIEVAL_ACTION_ID = (
    "stage128-m3-lag-wdi-exploratory-data-retrieval")

_STAGE128_M3_LAG_RETRIEVAL_AUTH_SHA256 = (
    "b409e0a53d255955199c59005d39f911ae272713dbf85c38651cd0dcfd5ba604")
_STAGE128_M3_LAG_RETRIEVAL_AUTH_BYTES = 125
_STAGE128_M3_LAG_RETRIEVAL_SCOPE = "retrieval_only"
#: The contract-lock authorization: historical, consumed, and never reusable
#: as a retrieval authorization. Kept here so the two can be told apart.
_STAGE128_M3_LAG_RETRIEVAL_PRIOR_LOCK_SHA = (
    "0c1e10496bfba98d5ae4a6a3a8bf593a42258388fce1003c4cc36e6cdee4995b")
#: Acquisition counters that MUST still be zero after a retrieval-only action.
#: Each belongs to a later, separately authorized step.
_STAGE128_M3_LAG_RETRIEVAL_ZERO_COUNTERS = (
    "wdi_value_inspections", "wdi_observations_read",
    "alternative_indicators_searched", "alternative_indicators_retrieved",
    "proxy_or_substitute_series_retrieved", "coverage_calculations",
    "candidate_coverage_evaluations", "block_coverage_evaluations",
    "positives_per_window_counts", "data_gate_executions",
    "data_gate_results_returned", "admission_decisions",
    "company_row_macro_joins", "feature_materializations",
    "fx_transformation_calculations", "common_sample_constructions",
    "model_fits", "predictions", "predictive_metrics",
    "bootstrap_executions", "holm_calculations", "shap_executions",
    "hyperparameter_tuning_runs", "final_test_rows_read",
    "final_test_predictor_values_read", "final_test_target_values_read",
)


def derive_stage128_m3_lag_wdi_data_retrieval_markers(root: str) -> dict:
    """Recognize the M3-LAG-WDI exploratory DATA RETRIEVAL (retrieval only).

    Narrow and fail-closed. The action ACQUIRED the two locked WDI payloads for
    IRN and did nothing else: it never decoded a payload, never read an
    observation, never computed coverage, never executed the Data Gate, never
    admitted anything, never joined a company row, never fit a model and never
    read a Final Test row. A ``retrieval executed`` state may therefore be
    published only if every one of those counters is still zero, the retrieved
    indicators are exactly the two locked codes for the locked country, and the
    Gate/modeling boundaries are all still closed.

    Returns {} before the retrieval package exists.
    """
    manifest_path = os.path.join(
        root, _STAGE128_M3_LAG_RETRIEVAL_MANIFEST_REL)
    if not os.path.isfile(manifest_path):
        return {}
    manifest = _require_json_artifact(
        root, _STAGE128_M3_LAG_RETRIEVAL_MANIFEST_REL)
    audit = _require_json_artifact(
        root, _STAGE128_M3_LAG_RETRIEVAL_AUDIT_REL)
    boundary = _require_json_artifact(
        root, _STAGE128_M3_LAG_RETRIEVAL_BOUNDARY_REL)
    authorization = _require_json_artifact(
        root, _STAGE128_M3_LAG_RETRIEVAL_AUTH_REL)
    decision = _require_json_artifact(
        root, _STAGE128_M3_LAG_RETRIEVAL_DECISION_REL)

    # --- A NEW single-use authorization, distinct from the lock's ---------- #
    if authorization.get("authorization_sha256") != (
            _STAGE128_M3_LAG_RETRIEVAL_AUTH_SHA256):
        raise HandoffError(
            "the retrieval authorization digest does not match the recorded "
            "one-action authorization")
    if authorization.get("authorization_utf8_bytes") != (
            _STAGE128_M3_LAG_RETRIEVAL_AUTH_BYTES):
        raise HandoffError(
            "the retrieval authorization byte length must be "
            f"{_STAGE128_M3_LAG_RETRIEVAL_AUTH_BYTES}")
    text = authorization.get("authorization_text")
    if not isinstance(text, str) or not text:
        raise HandoffError("the verbatim retrieval authorization is required")
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != (
            _STAGE128_M3_LAG_RETRIEVAL_AUTH_SHA256):
        raise HandoffError(
            "the recorded retrieval authorization SHA-256 does not match its "
            "own text")
    if len(text.encode("utf-8")) != _STAGE128_M3_LAG_RETRIEVAL_AUTH_BYTES:
        raise HandoffError(
            "the recorded retrieval authorization byte length does not match "
            "its own text")
    if authorization.get("authorization_scope") != (
            _STAGE128_M3_LAG_RETRIEVAL_SCOPE):
        raise HandoffError(
            f"the retrieval scope must be {_STAGE128_M3_LAG_RETRIEVAL_SCOPE}")
    # The consumed contract-lock authorization must not be re-presented here.
    if authorization.get("authorization_sha256") == (
            _STAGE128_M3_LAG_RETRIEVAL_PRIOR_LOCK_SHA):
        raise HandoffError(
            "the contract-lock authorization may not be reused for retrieval")
    if authorization.get("prior_contract_lock_authorization_reused") is not (
            False):
        raise HandoffError(
            "the prior contract-lock authorization must stay unreused")
    for field in ("authorization_is_reusable_for_post_retrieval_audit",
                  "authorization_is_reusable_for_data_gate",
                  "authorization_is_reusable_for_modeling",
                  "standing_authorization",
                  "scope_identified_by_hash_alone"):
        if authorization.get(field) is not False:
            raise HandoffError(f"retrieval authorization {field} must be False")

    # --- Exactly the two locked indicators, for the locked country -------- #
    indicators = manifest.get("indicators") or []
    codes = tuple(entry.get("indicator_code") for entry in indicators)
    if codes != tuple(f[1] for f in _STAGE128_M3_LAG_FEATURES):
        raise HandoffError(
            "retrieval must cover exactly the two locked indicators "
            f"{[f[1] for f in _STAGE128_M3_LAG_FEATURES]}, found {list(codes)}")
    if manifest.get("indicator_count") != 2:
        raise HandoffError("exactly two indicators may be retrieved")
    for entry in indicators:
        if entry.get("country_code") != "IRN":
            raise HandoffError("both retrieved indicators are for IRN")
        url = entry.get("request_url") or ""
        if not url.startswith("https://api.worldbank.org/v2/"):
            raise HandoffError(
                "every retrieval must target the official World Bank WDI API "
                f"over HTTPS; got {url!r}")
        if entry.get("payload_parsed") is not False:
            raise HandoffError(
                "a retrieval-only action may not parse the payload")
        for field in ("observations_read", "values_inspected",
                      "coverage_calculated"):
            if entry.get(field) is not None:
                raise HandoffError(
                    f"{field} must stay null after a retrieval-only action")
    if manifest.get("point_in_time_availability_claimed") is not False:
        raise HandoffError(
            "retrieval never establishes point-in-time availability")
    if manifest.get("historical_vintage_availability_claimed") is not False:
        raise HandoffError(
            "retrieval never establishes a historical vintage claim")
    if manifest.get("raw_payloads_committed_to_git") != 0:
        raise HandoffError("raw WDI payloads are retained OUTSIDE Git")

    # --- Durable custody may be CLAIMED only when it is real -------------- #
    # A bundle id says WHICH bytes are authoritative, not WHERE to get them.
    # "Durably resolvable" is therefore only publishable together with a real
    # locator that a stranger can resolve. Fail-closed: claiming the flag
    # without the DOI, or with a locator that is really a filesystem path,
    # raises rather than publishing a custody promise the repository cannot
    # keep.
    if manifest.get("raw_retention_durably_resolvable") is True:
        for field in ("raw_retention_version_doi",
                      "raw_retention_concept_doi",
                      "raw_retention_record_url",
                      "raw_retention_custody_class"):
            value = manifest.get(field)
            if not isinstance(value, str) or not value.strip():
                raise HandoffError(
                    f"durable custody claimed without {field}")
            if value.startswith(("/", "~", ".")) or "\\" in value:
                raise HandoffError(
                    f"{field} looks like a local filesystem path, which is "
                    "not a durable locator")
        if not manifest.get("raw_retention_version_doi", "").startswith("10."):
            raise HandoffError(
                "the durable custody locator must be a DOI")
        # Recovery must never route back to the live API: a new request would
        # return the CURRENT series, silently auditing different bytes.
        if manifest.get(
                "raw_retention_recovery_requires_new_world_bank_request"
        ) is not False:
            raise HandoffError(
                "re-requesting the World Bank API is not a recovery mechanism")
        if manifest.get(
                "raw_retention_depends_on_developer_filesystem") is not False:
            raise HandoffError(
                "durable custody may not depend on a developer filesystem")
        # The DOI locates; content still identifies.
        if manifest.get("raw_artifacts_identified_by_content_not_path") is not (
                True):
            raise HandoffError(
                "a DOI is a locator, not an identity: content addressing must "
                "stay in force")

    # --- Retrieval happened; NOTHING downstream of it did ----------------- #
    if audit.get("retrieval_started") is not True:
        raise HandoffError("the retrieval audit must record retrieval started")
    for counter in _STAGE128_M3_LAG_RETRIEVAL_ZERO_COUNTERS:
        if audit.get(counter) != 0:
            raise HandoffError(
                f"retrieval-only: execution counter {counter} must be 0")
    for field in ("payload_json_decoded", "post_retrieval_audit_executed",
                  "quarantined_local_draft_used_as_input",
                  "earlier_historical_vintage_bundle_used_as_value_input"):
        if audit.get(field) is not False:
            raise HandoffError(f"retrieval audit {field} must be False")

    # --- The boundary the retrieval stopped at ---------------------------- #
    for field in ("m3_lag_wdi_next_action_authorized",
                  "m3_lag_wdi_next_action_executes_data_gate",
                  "m3_lag_wdi_post_retrieval_audit_action_authorized",
                  "m3_lag_wdi_post_retrieval_audit_executed",
                  "m3_lag_wdi_data_gate_action_authorized",
                  "m3_lag_wdi_data_gate_executed",
                  "m3_lag_wdi_gate_pass_authorizes_modeling",
                  "m3_lag_wdi_modeling_authorized",
                  "m3_lag_wdi_modeling_started",
                  "retrieval_executed_data_gate",
                  "combined_retrieval_and_gate_action_permitted",
                  "retrieval_authorization_implies_gate_authorization",
                  "retrieval_authorization_covers_post_retrieval_audit",
                  "retrieval_authorization_covers_data_gate",
                  "retrieval_authorization_covers_modeling",
                  "retrieval_authorization_covers_final_test",
                  "retrieval_authorization_covers_track_a_follow_up",
                  "retrieval_authorization_reusable",
                  "m3_lag_wdi_block_admitted",
                  "world_bank_inquiry_terminated_by_this_action",
                  "world_bank_follow_up_authorized",
                  "world_bank_response_ingestion_authorized",
                  "track_b_retrieval_implies_track_a_resolved",
                  "track_b_retrieval_implies_track_a_abandoned",
                  "final_test_access_authorized", "m4_authorized",
                  "merge_authorized", "pii_committed_to_git",
                  "credentials_committed_to_git"):
        if boundary.get(field) is not False:
            raise HandoffError(
                f"retrieval governance boundary {field} must be False")
    if boundary.get("final_test_locked") is not True:
        raise HandoffError("the Final Test must stay locked after retrieval")
    if boundary.get("m3_lag_wdi_authoritative_contract_status") != (
            _STAGE128_M3_LAG_LOCKED_STATUS):
        raise HandoffError(
            "retrieval does not change the authoritative contract status")
    if boundary.get("m3_lag_wdi_contract_modified_by_this_action") is not (
            False):
        raise HandoffError("retrieval may not modify the locked contract")
    if boundary.get("m3_lag_wdi_next_action_id") != (
            _STAGE128_M3_LAG_POST_RETRIEVAL_AUDIT_ACTION_ID):
        raise HandoffError(
            "the Track B pointer after retrieval is "
            f"{_STAGE128_M3_LAG_POST_RETRIEVAL_AUDIT_ACTION_ID}")
    if boundary.get("m3_lag_wdi_data_gate_action_id") != (
            _STAGE128_M3_LAG_DATA_GATE_ACTION_ID):
        raise HandoffError("the Data Gate keeps its own separate action id")
    if boundary.get("m3_lag_wdi_modeling_action_id") != (
            _STAGE128_M3_LAG_MODELING_ACTION_ID):
        raise HandoffError("modeling keeps its own separate action id")
    if decision.get("scientific_effect") != "NONE":
        raise HandoffError("acquisition has no scientific effect")
    for field in ("admission_decision_made", "coverage_decision_made",
                  "gate_decision_made", "modeling_decision_made",
                  "authorizes_next_action"):
        if decision.get(field) is not False:
            raise HandoffError(f"retrieval decision {field} must be False")

    retrieved = sum(1 for entry in indicators
                    if entry.get("retrieval_result") == "SUCCESS")
    return {
        # Retrieval EXECUTED — and that is all it did.
        "stage128_m3_lag_wdi_data_retrieval_started": True,
        "stage128_m3_lag_wdi_data_retrieval_completed":
            retrieved == len(indicators),
        "stage128_m3_lag_wdi_retrieval_status":
            decision.get("retrieval_status"),
        "stage128_m3_lag_wdi_retrieval_scope":
            _STAGE128_M3_LAG_RETRIEVAL_SCOPE,
        "stage128_m3_lag_wdi_retrieval_authorization_sha256":
            _STAGE128_M3_LAG_RETRIEVAL_AUTH_SHA256,
        "stage128_m3_lag_wdi_retrieval_authorization_utf8_bytes":
            _STAGE128_M3_LAG_RETRIEVAL_AUTH_BYTES,
        # HISTORICAL vs STANDING authorization are published as two separate
        # facts so neither can be misread as the other. The retrieval WAS
        # explicitly authorized — once — and that authorization was CONSUMED
        # by the executed retrieval, so no standing permission to issue
        # another World Bank request exists NOW. The generic
        # ``retrieval_authorized`` field carries the STANDING meaning and is
        # therefore False after consumption; the historical fact lives only
        # in ``retrieval_was_authorized``.
        "stage128_m3_lag_wdi_retrieval_was_authorized": True,
        "stage128_m3_lag_wdi_retrieval_authorized_now": False,
        "stage128_m3_lag_wdi_retrieval_authorized": False,
        "stage128_m3_lag_wdi_retrieval_authorization_consumed": True,
        "stage128_m3_lag_wdi_retrieval_authorization_reusable": False,
        "stage128_m3_lag_wdi_further_retrieval_requires_new_human_"
        "authorization": True,
        "stage128_m3_lag_wdi_indicators_retrieved": retrieved,
        "stage128_m3_lag_wdi_indicator_codes_retrieved": list(codes),
        "stage128_m3_lag_wdi_retrieval_country_code": "IRN",
        "stage128_m3_lag_wdi_world_bank_api_requests":
            audit.get("world_bank_api_requests"),
        "stage128_m3_lag_wdi_raw_artifacts_retained":
            audit.get("raw_artifacts_retained"),
        "stage128_m3_lag_wdi_raw_bytes_retained":
            audit.get("raw_bytes_retained"),
        "stage128_m3_lag_wdi_raw_payloads_committed_to_git": 0,
        # DURABLE CUSTODY of the retained bytes. Published so a future audit
        # session can resolve the bundle id to real bytes without this
        # developer's machine and without a new World Bank request.
        "stage128_m3_lag_wdi_raw_retention_bundle_id":
            manifest.get("raw_retention_bundle_id"),
        "stage128_m3_lag_wdi_raw_retention_custody_class":
            manifest.get("raw_retention_custody_class"),
        "stage128_m3_lag_wdi_raw_retention_version_doi":
            manifest.get("raw_retention_version_doi"),
        "stage128_m3_lag_wdi_raw_retention_concept_doi":
            manifest.get("raw_retention_concept_doi"),
        "stage128_m3_lag_wdi_raw_retention_record_url":
            manifest.get("raw_retention_record_url"),
        "stage128_m3_lag_wdi_raw_retention_deposited_artifact_count":
            manifest.get("raw_retention_deposited_artifact_count"),
        "stage128_m3_lag_wdi_raw_evidence_durably_resolvable":
            manifest.get("raw_retention_durably_resolvable") is True,
        "stage128_m3_lag_wdi_raw_evidence_recovery_requires_new_world_bank_"
        "request": manifest.get(
            "raw_retention_recovery_requires_new_world_bank_request"),
        "stage128_m3_lag_wdi_raw_evidence_depends_on_developer_filesystem":
            manifest.get("raw_retention_depends_on_developer_filesystem"),
        "stage128_m3_lag_wdi_payload_json_decoded": False,
        "stage128_m3_lag_wdi_wdi_observations_read": 0,
        "stage128_m3_lag_wdi_alternative_indicators_retrieved": 0,
        # Everything after acquisition is still closed.
        "stage128_m3_lag_wdi_next_action_id":
            _STAGE128_M3_LAG_POST_RETRIEVAL_AUDIT_ACTION_ID,
        "stage128_m3_lag_wdi_next_action_authorized": False,
        "stage128_m3_lag_wdi_next_action_scope": "post_retrieval_audit_only",
        # Derived from the action the pointer names (here: the audit → False).
        "stage128_m3_lag_wdi_next_action_executes_data_gate":
            _stage128_m3_lag_action_executes_data_gate(
                _STAGE128_M3_LAG_POST_RETRIEVAL_AUDIT_ACTION_ID),
        "stage128_m3_lag_wdi_post_retrieval_audit_executed": False,
        "stage128_m3_lag_wdi_data_gate_executed": False,
        "stage128_m3_lag_wdi_data_gate_authorized": False,
        "stage128_m3_lag_wdi_data_gate_result": "NOT_EXECUTED",
        # DERIVED, never hard-coded: step E flips this, and a marker
        # function must not publish a moment as if it were a rule.
        "stage128_m3_lag_wdi_modeling_started":
            _stage128_m3_lag_modeling_started(root),
        "stage128_m3_lag_wdi_modeling_authorized": False,
        "stage128_m3_lag_wdi_block_admitted": False,
        "stage128_m3_lag_wdi_final_test_rows_read": 0,
        "stage128_m3_lag_wdi_action_sequence": [
            {
                "step": step,
                "action_id": action_id,
                "executes_retrieval": executes_retrieval,
                "executes_data_gate": executes_gate,
                "executes_modeling": executes_modeling,
                # "authorized" is STANDING: consumed one-time authorizations
                # (A, B) are history, recorded in "was_authorized" only.
                "was_authorized": step in ("A", "B"),
                "authorized_now": False,
                "authorized": False,
                "status": "COMPLETE" if step in ("A", "B")
                          else "NOT_AUTHORIZED",
            }
            for (step, action_id, executes_retrieval, executes_gate,
                 executes_modeling) in _STAGE128_M3_LAG_ACTION_SEQUENCE
        ],
    }


#: Stage128 Track B step C — the post-retrieval audit package.
_STAGE128_M3_LAG_AUDIT_PKG = (
    "project/stage128/m3_lag_wdi_exploratory_post_retrieval_audit")
_STAGE128_M3_LAG_AUDIT_REPORT_REL = (
    f"{_STAGE128_M3_LAG_AUDIT_PKG}/"
    "stage128_m3_lag_wdi_post_retrieval_audit_report.json")
_STAGE128_M3_LAG_AUDIT_EXEC_REL = (
    f"{_STAGE128_M3_LAG_AUDIT_PKG}/"
    "stage128_m3_lag_wdi_post_retrieval_audit_execution_audit.json")
_STAGE128_M3_LAG_AUDIT_BOUNDARY_REL = (
    f"{_STAGE128_M3_LAG_AUDIT_PKG}/"
    "stage128_m3_lag_wdi_post_retrieval_audit_governance_boundary.json")
_STAGE128_M3_LAG_AUDIT_DECISION_REL = (
    f"{_STAGE128_M3_LAG_AUDIT_PKG}/"
    "stage128_m3_lag_wdi_post_retrieval_audit_decision.json")

#: Counters a post-retrieval audit must still leave at zero. It decodes a
#: series; it does not touch the sample, the Gate, the models or the Final Test.
_STAGE128_M3_LAG_AUDIT_ZERO_COUNTERS = (
    "world_bank_api_requests", "new_payloads_retrieved",
    "alternative_indicators_retrieved", "coverage_calculations",
    "candidate_coverage_evaluations", "block_coverage_evaluations",
    "coverage_threshold_comparisons", "data_gate_executions",
    "admission_decisions", "company_row_macro_joins",
    "feature_materializations", "common_sample_constructions", "model_fits",
    "predictions", "predictive_metrics", "bootstrap_executions",
    "holm_calculations", "shap_executions", "final_test_rows_read",
)


def derive_stage128_m3_lag_wdi_post_retrieval_audit_markers(
        root: str) -> dict:
    """Publish Track B step C — the M3-LAG-WDI POST-RETRIEVAL AUDIT.

    Step C is the first action allowed to DECODE the retained payloads, and
    the only thing it may conclude is what the evidence contains. Fail-closed
    on exactly the confusion that would matter: an audit that quietly ran the
    Gate, computed coverage against a threshold, admitted the block, or let a
    PASS read as permission for step D.

    A material finding is never allowed to vanish. If the audit recorded
    limitations, they are republished here rather than being summarised away
    into a bare "PASS".

    Returns {} before the audit package exists.
    """
    report_path = os.path.join(root, _STAGE128_M3_LAG_AUDIT_REPORT_REL)
    if not os.path.isfile(report_path):
        return {}
    report = _require_json_artifact(root, _STAGE128_M3_LAG_AUDIT_REPORT_REL)
    audit = _require_json_artifact(root, _STAGE128_M3_LAG_AUDIT_EXEC_REL)
    boundary = _require_json_artifact(
        root, _STAGE128_M3_LAG_AUDIT_BOUNDARY_REL)
    decision = _require_json_artifact(
        root, _STAGE128_M3_LAG_AUDIT_DECISION_REL)

    if report.get("action_id") != _STAGE128_M3_LAG_POST_RETRIEVAL_AUDIT_ACTION_ID:
        raise HandoffError("the step C action id is wrong")
    if report.get("authorized_scope") != "post_retrieval_audit_only":
        raise HandoffError("step C scope must be post_retrieval_audit_only")

    # The audit decoded bytes — and did ONLY that.
    if audit.get("post_retrieval_audit_executed") is not True:
        raise HandoffError("the step C audit must record that it executed")
    if audit.get("payload_json_decoded") is not True:
        raise HandoffError(
            "a post-retrieval audit that decoded nothing audited nothing")
    for counter in _STAGE128_M3_LAG_AUDIT_ZERO_COUNTERS:
        if audit.get(counter) != 0:
            raise HandoffError(
                f"post-retrieval-audit-only: counter {counter} must be 0")
    for field in ("retained_bytes_modified", "deposited_evidence_modified"):
        if audit.get(field) is not False:
            raise HandoffError(
                f"the audit may not mutate the evidence it audits ({field})")

    # Reading is not admitting, and passing is not authorizing.
    for field in ("m3_lag_wdi_post_retrieval_audit_executes_data_gate",
                  "post_retrieval_audit_authorization_implies_gate_"
                  "authorization",
                  "post_retrieval_audit_pass_is_gate_authorization",
                  "post_retrieval_audit_pass_is_admission",
                  "m3_lag_wdi_next_action_authorized",
                  "m3_lag_wdi_data_gate_action_authorized",
                  "m3_lag_wdi_data_gate_executed",
                  "m3_lag_wdi_gate_pass_authorizes_modeling",
                  "m3_lag_wdi_modeling_authorized",
                  "m3_lag_wdi_modeling_started",
                  "m3_lag_wdi_block_admitted",
                  "m3_lag_wdi_contract_modified_by_this_action",
                  "retrieval_authorized_now",
                  "retrieval_authorization_reusable",
                  "new_world_bank_request_made_by_this_action",
                  "world_bank_inquiry_terminated_by_this_action",
                  "final_test_access_authorized", "m4_authorized",
                  "merge_authorized", "ready_for_review_authorized",
                  "pii_committed_to_git", "credentials_committed_to_git"):
        if boundary.get(field) is not False:
            raise HandoffError(
                f"step C governance boundary {field} must be False")
    for field in ("m3_lag_wdi_post_retrieval_audit_action_authorized",
                  "m3_lag_wdi_post_retrieval_audit_executed",
                  "m3_lag_wdi_post_retrieval_audit_authorization_consumed",
                  "retrieval_was_authorized",
                  "retrieval_authorization_consumed",
                  "further_retrieval_requires_new_human_authorization",
                  "final_test_locked"):
        if boundary.get(field) is not True:
            raise HandoffError(
                f"step C governance boundary {field} must be True")
    if boundary.get(
            "m3_lag_wdi_post_retrieval_audit_authorization_reusable") is not (
                False):
        raise HandoffError(
            "the step C authorization is single-use and is now consumed")
    if boundary.get("m3_lag_wdi_next_action_id") != (
            _STAGE128_M3_LAG_DATA_GATE_ACTION_ID):
        raise HandoffError(
            "the Track B pointer after step C is the Data Gate")
    # The pointer's descriptive fields must agree with the locked sequence for
    # the action they point AT. Publishing "the next action is the Data Gate"
    # beside "the next action does not execute the Data Gate" is a
    # contradiction, and it is exactly what happens when the field is carried
    # forward as a hard-coded False instead of being derived.
    if _stage128_m3_lag_action_executes_data_gate(
            _STAGE128_M3_LAG_DATA_GATE_ACTION_ID) is not True:
        raise HandoffError(
            "the locked sequence must mark the Data Gate action as the step "
            "that executes the Gate")
    if decision.get("scientific_effect") != "NONE":
        raise HandoffError("an audit has no scientific effect")
    if decision.get("authorizes_next_action") is not False:
        raise HandoffError("step C authorizes nothing")
    if report.get("admission_decision_made") is not False:
        raise HandoffError("step C admits nothing")
    if report.get("coverage_thresholds_applied") is not False:
        raise HandoffError("applying a coverage threshold is the Data Gate")
    if report.get("company_rows_touched") != 0:
        raise HandoffError("step C touches no company row")

    limitations = decision.get("material_limitations") or []
    result = decision.get("audit_result")
    if result not in ("PASS", "PASS_WITH_MATERIAL_FINDINGS", "FAIL"):
        raise HandoffError(f"unrecognized step C audit result {result!r}")
    # A result that claims a clean PASS while carrying material limitations
    # would launder the findings out of the published state.
    if result == "PASS" and limitations:
        raise HandoffError(
            "material limitations were recorded, so the result may not be "
            "published as a bare PASS")

    cpi_avail, fx_avail = report["feature_availability"]
    return {
        "stage128_m3_lag_wdi_post_retrieval_audit_executed": True,
        # Same HISTORICAL vs STANDING split step B established: the generic
        # ``*_authorized`` field carries the STANDING meaning, so a consumed
        # one-time audit authorization publishes False here and keeps the
        # historical fact in ``*_was_authorized``. This field previously
        # published True after consumption, which contradicted step B's
        # documented semantics, the action sequence (where every completed
        # step carries authorized=False) and ROADMAP.md's own
        # ``m3_lag_wdi_post_retrieval_audit_authorized: false``. Correcting it
        # changes NO audit result: step C was not rerun and its
        # PASS_WITH_MATERIAL_FINDINGS and findings are untouched.
        "stage128_m3_lag_wdi_post_retrieval_audit_authorized": False,
        "stage128_m3_lag_wdi_post_retrieval_audit_was_authorized": True,
        "stage128_m3_lag_wdi_post_retrieval_audit_authorized_now": False,
        "stage128_m3_lag_wdi_post_retrieval_audit_authorization_consumed":
            True,
        "stage128_m3_lag_wdi_post_retrieval_audit_authorization_reusable":
            False,
        "stage128_m3_lag_wdi_post_retrieval_audit_result": result,
        "stage128_m3_lag_wdi_post_retrieval_audit_material_limitations":
            limitations,
        "stage128_m3_lag_wdi_post_retrieval_audit_material_limitation_count":
            len(limitations),
        "stage128_m3_lag_wdi_payload_json_decoded": True,
        "stage128_m3_lag_wdi_wdi_observations_read":
            audit.get("wdi_observations_read"),
        "stage128_m3_lag_wdi_cpi_constructible_predictor_year_first":
            cpi_avail.get("constructible_predictor_year_first"),
        "stage128_m3_lag_wdi_cpi_constructible_predictor_year_last":
            cpi_avail.get("constructible_predictor_year_last"),
        "stage128_m3_lag_wdi_fx_constructible_predictor_year_first":
            fx_avail.get("constructible_predictor_year_first"),
        "stage128_m3_lag_wdi_fx_constructible_predictor_year_last":
            fx_avail.get("constructible_predictor_year_last"),
        "stage128_m3_lag_wdi_fx_trailing_zero_change_predictor_years":
            fx_avail.get("trailing_zero_change_predictor_years"),
        "stage128_m3_lag_wdi_both_features_predictor_year_first":
            report.get("both_features_constructible_predictor_year_first"),
        "stage128_m3_lag_wdi_both_features_predictor_year_last":
            report.get("both_features_constructible_predictor_year_last"),
        "stage128_m3_lag_wdi_binding_constraint_indicator":
            report.get("binding_constraint_indicator"),
        "stage128_m3_lag_wdi_audited_evidence_modified": False,
        # The pointer advances to the Data Gate — still a pointer, still not
        # an authorization.
        "stage128_m3_lag_wdi_next_action_id":
            _STAGE128_M3_LAG_DATA_GATE_ACTION_ID,
        "stage128_m3_lag_wdi_next_action_authorized": False,
        "stage128_m3_lag_wdi_next_action_scope": "data_gate_only",
        # DERIVED, never hard-coded. The pointer now names the Data Gate
        # action, and that action does by definition execute the Gate — so
        # this is True. It is NOT a statement that the Gate has run or may
        # run: `next_action_authorized`, `data_gate_authorized` and
        # `data_gate_executed` are all False, and they are what hold the line.
        "stage128_m3_lag_wdi_next_action_executes_data_gate":
            _stage128_m3_lag_action_executes_data_gate(
                _STAGE128_M3_LAG_DATA_GATE_ACTION_ID),
        "stage128_m3_lag_wdi_action_sequence": [
            {
                "step": step,
                "action_id": action_id,
                "executes_retrieval": executes_retrieval,
                "executes_data_gate": executes_gate,
                "executes_modeling": executes_modeling,
                "was_authorized": step in ("A", "B", "C"),
                "authorized_now": False,
                "authorized": False,
                "status": "COMPLETE" if step in ("A", "B", "C")
                          else "NOT_AUTHORIZED",
            }
            for (step, action_id, executes_retrieval, executes_gate,
                 executes_modeling) in _STAGE128_M3_LAG_ACTION_SEQUENCE
        ],
    }


#: Stage128 Track B step D — the executed Data Gate package.
_STAGE128_M3_LAG_GATE_PKG = (
    "project/stage128/m3_lag_wdi_exploratory_data_gate")
_STAGE128_M3_LAG_GATE_REPORT_REL = (
    f"{_STAGE128_M3_LAG_GATE_PKG}/stage128_m3_lag_wdi_data_gate_report.json")
_STAGE128_M3_LAG_GATE_EXEC_REL = (
    f"{_STAGE128_M3_LAG_GATE_PKG}/"
    "stage128_m3_lag_wdi_data_gate_execution_audit.json")
_STAGE128_M3_LAG_GATE_BOUNDARY_REL = (
    f"{_STAGE128_M3_LAG_GATE_PKG}/"
    "stage128_m3_lag_wdi_data_gate_governance_boundary.json")
_STAGE128_M3_LAG_GATE_DECISION_REL = (
    f"{_STAGE128_M3_LAG_GATE_PKG}/stage128_m3_lag_wdi_data_gate_decision.json")

#: The Gate's own outcome vocabulary. Anything else is an invented verdict.
_STAGE128_M3_LAG_GATE_VOCABULARY = (
    "PASS_M3_LAG_WDI_DATA_GATE",
    "FAIL_M3_LAG_WDI_DATA_GATE",
    "UNRESOLVED_M3_LAG_WDI_DATA_GATE",
)

#: Counters a data Gate must STILL leave at zero. The Gate computes coverage
#: — that is its job — but it retrieves nothing, fits nothing, materializes no
#: feature-value table and reads no Final Test row.
_STAGE128_M3_LAG_GATE_ZERO_COUNTERS = (
    "world_bank_api_requests", "new_payloads_retrieved",
    "alternative_indicators_searched", "alternative_indicators_retrieved",
    "feature_value_tables_materialized", "model_fits", "predictions",
    "predictive_metrics", "bootstrap_executions", "holm_calculations",
    "shap_executions", "tuning_runs", "cross_validation_runs",
    "model_selections", "final_test_rows_read",
    "final_test_predictor_values_read", "final_test_target_values_read",
)

#: The locked, inherited thresholds. Republished here so a silently lowered
#: threshold in the Gate package cannot reach the Handoff unnoticed.
#: The locked Gate denominator: the retained-M2 development common sample.
_STAGE128_M3_LAG_PARENT_ROWS = 539
_STAGE128_M3_LAG_GATE_CANDIDATE_COVERAGE_MIN = 0.80
_STAGE128_M3_LAG_GATE_BLOCK_COVERAGE_MIN = 0.70
_STAGE128_M3_LAG_GATE_MIN_POSITIVE_EACH_WINDOW = 5


def derive_stage128_m3_lag_wdi_data_gate_markers(root: str) -> dict:
    """Publish Track B step D — the EXECUTED M3-LAG-WDI Data Gate.

    Step D is the only action permitted to bring the audited series to the
    development sample and return an admission verdict. Fail-closed on the
    confusions that would matter most here, all of which are ways a coverage
    PASS could be laundered into something it is not:

    * a verdict outside the Gate's own vocabulary;
    * a threshold that does not match the locked, inherited contract — the
      single most valuable thing to catch, since lowering one is exactly how
      a FAIL becomes a PASS;
    * a verdict that does not follow from the published numbers (recomputed
      here from numerator, denominator and threshold, never trusted);
    * a PASS published as modeling authorization, as an information-content
      claim about the FX feature, as a Final Test unlock, or as anything that
      propagates to step E;
    * the step C material findings quietly dropped once the Gate passed.

    Returns {} before the Gate package exists.
    """
    report_path = os.path.join(root, _STAGE128_M3_LAG_GATE_REPORT_REL)
    if not os.path.isfile(report_path):
        return {}
    report = _require_json_artifact(root, _STAGE128_M3_LAG_GATE_REPORT_REL)
    audit = _require_json_artifact(root, _STAGE128_M3_LAG_GATE_EXEC_REL)
    boundary = _require_json_artifact(
        root, _STAGE128_M3_LAG_GATE_BOUNDARY_REL)
    decision = _require_json_artifact(
        root, _STAGE128_M3_LAG_GATE_DECISION_REL)

    if report.get("action_id") != _STAGE128_M3_LAG_DATA_GATE_ACTION_ID:
        raise HandoffError("the step D action id is wrong")
    if report.get("authorized_scope") != "data_gate_only":
        raise HandoffError("step D scope must be data_gate_only")
    if audit.get("data_gate_executed") is not True:
        raise HandoffError("the step D audit must record that it executed")
    if audit.get("data_gate_executions") != 1:
        raise HandoffError("the Gate is executed exactly once")
    for counter in _STAGE128_M3_LAG_GATE_ZERO_COUNTERS:
        if audit.get(counter) != 0:
            raise HandoffError(f"data-gate-only: counter {counter} must be 0")
    for field in ("retained_bytes_modified", "deposited_evidence_modified"):
        if audit.get(field) is not False:
            raise HandoffError(
                f"the Gate may not mutate the evidence it reads ({field})")

    # ---- the thresholds are the locked, inherited ones -------------------- #
    thresholds = report["locked_thresholds"]
    gate = report["gate_computation"]
    if thresholds.get("thresholds_changed_by_this_action") is not False:
        raise HandoffError("step D may not change the locked thresholds")
    if thresholds.get("coverage_scope") != "development_only":
        raise HandoffError("the M3-LAG-WDI Gate is development-only")
    expected_thresholds = (
        ("candidate_valid_coverage_min",
         _STAGE128_M3_LAG_GATE_CANDIDATE_COVERAGE_MIN),
        ("block_common_sample_coverage_min",
         _STAGE128_M3_LAG_GATE_BLOCK_COVERAGE_MIN),
        ("minimum_positive_evaluable_each_locked_validation_window",
         _STAGE128_M3_LAG_GATE_MIN_POSITIVE_EACH_WINDOW),
    )
    for key, expected in expected_thresholds:
        if float(thresholds.get(key)) != float(expected):
            raise HandoffError(
                f"step D threshold {key} is {thresholds.get(key)}, not the "
                f"locked inherited {expected}; thresholds must not be "
                "lowered, raised or replaced")

    # ---- the verdict must FOLLOW from the published numbers --------------- #
    rows = gate.get("rows")
    if rows != _STAGE128_M3_LAG_PARENT_ROWS:
        raise HandoffError(
            f"the Gate denominator is the {_STAGE128_M3_LAG_PARENT_ROWS}-row "
            f"retained-M2 development sample, not {rows}")
    if report.get("parent_surface", {}).get(
            "final_test_rows_in_parent_surface") != 0:
        raise HandoffError("no final-test row may enter the Gate denominator")
    verdict = decision.get("gate_result")
    if verdict not in _STAGE128_M3_LAG_GATE_VOCABULARY:
        raise HandoffError(f"unrecognized step D verdict {verdict!r}")

    cand_min = float(thresholds["candidate_valid_coverage_min"])
    block_min = float(thresholds["block_common_sample_coverage_min"])
    pos_min = int(thresholds[
        "minimum_positive_evaluable_each_locked_validation_window"])
    recomputed = {
        "cpi_candidate_coverage_meets_threshold":
            gate["cpi_constructible_rows"] / rows >= cand_min,
        "fx_candidate_coverage_meets_threshold":
            gate["fx_constructible_rows"] / rows >= cand_min,
        "block_common_sample_coverage_meets_threshold":
            gate["both_constructible_rows"] / rows >= block_min,
        "every_validation_window_meets_positive_floor": all(
            window["positive_evaluable_in_m3_lag_wdi_common_sample"] >= pos_min
            for window in gate["validation_windows"].values()),
    }
    if recomputed != gate.get("threshold_checks"):
        raise HandoffError(
            "the published threshold checks do not follow from the published "
            "coverage numerators, denominator and locked thresholds")
    invariant = gate.get("status_invariant_across_calendar_conventions")
    expected_verdict = (
        "UNRESOLVED_M3_LAG_WDI_DATA_GATE" if invariant is not True
        else "PASS_M3_LAG_WDI_DATA_GATE" if all(recomputed.values())
        else "FAIL_M3_LAG_WDI_DATA_GATE")
    if verdict != expected_verdict:
        raise HandoffError(
            f"the published verdict {verdict} does not follow from the "
            f"published checks (recomputed {expected_verdict})")

    admitted = verdict == "PASS_M3_LAG_WDI_DATA_GATE"
    if decision.get("block_formally_admitted") is not admitted:
        raise HandoffError(
            "block_formally_admitted must equal (verdict == PASS)")
    if boundary.get("m3_lag_wdi_block_admitted") is not admitted:
        raise HandoffError(
            "the governance boundary disagrees with the Gate verdict about "
            "whether the block was admitted")

    # ---- a PASS admits DATA and nothing else ------------------------------ #
    for field in ("gate_pass_is_modeling_authorization",
                  "gate_pass_is_information_content_claim",
                  "gate_pass_is_final_test_unlock",
                  "gate_authorization_propagates_to_step_e",
                  "m3_lag_wdi_data_gate_authorized_now",
                  "m3_lag_wdi_data_gate_authorization_reusable",
                  "m3_lag_wdi_next_action_authorized",
                  "m3_lag_wdi_modeling_authorized",
                  "m3_lag_wdi_modeling_started",
                  "m3_lag_wdi_contract_modified_by_this_action",
                  "m3_lag_wdi_thresholds_modified_by_this_action",
                  "step_c_rerun_by_this_action",
                  "step_c_result_modified_by_this_action",
                  "m3_lag_wdi_calendar_mapping_locked",
                  "retrieval_authorized_now",
                  "new_world_bank_request_made_by_this_action",
                  "world_bank_inquiry_terminated_by_this_action",
                  "final_test_access_authorized", "m4_authorized",
                  "merge_authorized", "ready_for_review_authorized",
                  "pii_committed_to_git", "credentials_committed_to_git"):
        if boundary.get(field) is not False:
            raise HandoffError(
                f"step D governance boundary {field} must be False")
    for field in ("m3_lag_wdi_data_gate_action_authorized",
                  "m3_lag_wdi_data_gate_executed",
                  "m3_lag_wdi_data_gate_authorization_consumed",
                  "m3_lag_wdi_block_admission_is_data_admission_only",
                  "m3_lag_wdi_modeling_requires_new_explicit_human_"
                  "authorization",
                  "step_c_material_findings_preserved",
                  "retrieval_was_authorized",
                  "retrieval_authorization_consumed",
                  "post_retrieval_audit_was_authorized",
                  "post_retrieval_audit_authorization_consumed",
                  "further_retrieval_requires_new_human_authorization",
                  "final_test_locked"):
        if boundary.get(field) is not True:
            raise HandoffError(
                f"step D governance boundary {field} must be True")
    if boundary.get("m3_lag_wdi_next_action_id") != (
            _STAGE128_M3_LAG_MODELING_ACTION_ID):
        raise HandoffError("the Track B pointer after step D is step E")
    if decision.get("authorizes_next_action") is not False:
        raise HandoffError("step D authorizes nothing")
    if decision.get("gate_pass_authorizes_modeling") is not False:
        raise HandoffError("a Gate PASS is not modeling authorization")

    # ---- step C's findings are not allowed to evaporate ------------------- #
    step_c_decision = _require_json_artifact(
        root, _STAGE128_M3_LAG_AUDIT_DECISION_REL)
    if decision.get("step_c_result_preserved") != (
            step_c_decision.get("audit_result")):
        raise HandoffError("step D misreports the accepted step C result")
    if decision.get("step_c_material_limitations_preserved") != (
            step_c_decision.get("material_limitations")):
        raise HandoffError(
            "the step C material findings must be preserved verbatim")
    distinctions = decision.get("scientific_distinctions") or {}
    required_distinctions = {
        "A_syntactic_availability_and_coverage",
        "B_pre_defined_thresholds_satisfied",
        "C_information_content_limitation_from_step_c",
        "D_effect_on_the_formal_gate_decision",
        "E_remaining_scientific_limitation",
    }
    if set(distinctions) != required_distinctions:
        raise HandoffError(
            "step D must distinguish coverage, thresholds, information "
            "content, formal effect and residual limitation")
    if distinctions["D_effect_on_the_formal_gate_decision"].get(
            "new_rejection_criterion_created") is not False:
        raise HandoffError(
            "step D may not invent a rejection criterion the locked contract "
            "does not contain")
    if distinctions["E_remaining_scientific_limitation"].get(
            "limitation_survives_the_pass") is not True:
        raise HandoffError(
            "the FX information-content limitation survives a formal PASS")
    limitations = decision.get("material_limitations") or []
    if not limitations:
        raise HandoffError(
            "step D inherited material limitations and may not publish none")
    for field in ("thresholds_changed_to_obtain_result", "criteria_weakened",
                  "criteria_strengthened_after_seeing_result",
                  "imputation_used", "alternative_indicator_tried"):
        if decision.get(field) is not False:
            raise HandoffError(f"step D decision {field} must be False")

    windows = gate["validation_windows"]
    return {
        "stage128_m3_lag_wdi_data_gate_executed": True,
        # HISTORICAL vs STANDING authorization, published as two separate
        # facts so neither can be misread as the other — the same semantics
        # step B established for retrieval. The Gate WAS explicitly authorized
        # (once), and that authorization was CONSUMED by this execution, so no
        # standing permission to run the Gate again exists NOW. The generic
        # ``data_gate_authorized`` field carries the STANDING meaning and is
        # therefore False after consumption; the historical fact lives only in
        # ``data_gate_was_authorized``.
        "stage128_m3_lag_wdi_data_gate_authorized": False,
        "stage128_m3_lag_wdi_data_gate_was_authorized": True,
        "stage128_m3_lag_wdi_data_gate_authorized_now": False,
        "stage128_m3_lag_wdi_data_gate_authorization_consumed": True,
        "stage128_m3_lag_wdi_data_gate_authorization_reusable": False,
        "stage128_m3_lag_wdi_data_gate_result": verdict,
        "stage128_m3_lag_wdi_data_gate_result_vocabulary": list(
            _STAGE128_M3_LAG_GATE_VOCABULARY),
        "stage128_m3_lag_wdi_block_admitted": admitted,
        "stage128_m3_lag_wdi_block_admission_is_data_admission_only": True,
        "stage128_m3_lag_wdi_gate_denominator_rows": rows,
        "stage128_m3_lag_wdi_gate_cpi_valid_rows":
            gate["cpi_constructible_rows"],
        "stage128_m3_lag_wdi_gate_fx_valid_rows":
            gate["fx_constructible_rows"],
        "stage128_m3_lag_wdi_gate_block_common_sample_rows":
            gate["both_constructible_rows"],
        "stage128_m3_lag_wdi_gate_cpi_candidate_coverage":
            gate["cpi_candidate_coverage"],
        "stage128_m3_lag_wdi_gate_fx_candidate_coverage":
            gate["fx_candidate_coverage"],
        "stage128_m3_lag_wdi_gate_block_common_sample_coverage":
            gate["block_common_sample_coverage"],
        "stage128_m3_lag_wdi_gate_candidate_coverage_min": cand_min,
        "stage128_m3_lag_wdi_gate_block_coverage_min": block_min,
        "stage128_m3_lag_wdi_gate_min_positive_each_validation_window":
            pos_min,
        "stage128_m3_lag_wdi_gate_fold1_positive_evaluable":
            windows["fold1_validation"][
                "positive_evaluable_in_m3_lag_wdi_common_sample"],
        "stage128_m3_lag_wdi_gate_fold2_positive_evaluable":
            windows["fold2_validation"][
                "positive_evaluable_in_m3_lag_wdi_common_sample"],
        "stage128_m3_lag_wdi_gate_rows_excluded": decision["rows_excluded"],
        "stage128_m3_lag_wdi_gate_fx_zero_change_development_rows":
            gate["fx_zero_change_rows"],
        "stage128_m3_lag_wdi_gate_status_invariant_across_calendar_"
        "conventions": invariant,
        "stage128_m3_lag_wdi_calendar_mapping_locked": False,
        "stage128_m3_lag_wdi_calendar_mapping_lock_required_before_modeling":
            True,
        "stage128_m3_lag_wdi_gate_material_limitations": limitations,
        "stage128_m3_lag_wdi_gate_material_limitation_count": len(limitations),
        "stage128_m3_lag_wdi_gate_thresholds_changed_by_this_action": False,
        "stage128_m3_lag_wdi_gate_criteria_weakened": False,
        "stage128_m3_lag_wdi_step_c_material_findings_preserved": True,
        # The step C result and its findings stay exactly as accepted.
        "stage128_m3_lag_wdi_post_retrieval_audit_result":
            step_c_decision["audit_result"],
        # A PASS admits DATA. It authorizes nothing, and the pointer that now
        # names step E is still only a pointer.
        "stage128_m3_lag_wdi_gate_pass_authorizes_modeling": False,
        "stage128_m3_lag_wdi_gate_pass_is_information_content_claim": False,
        "stage128_m3_lag_wdi_gate_pass_unlocks_final_test": False,
        "stage128_m3_lag_wdi_next_action_id":
            _STAGE128_M3_LAG_MODELING_ACTION_ID,
        "stage128_m3_lag_wdi_next_action_authorized": False,
        "stage128_m3_lag_wdi_next_action_scope":
            "modeling_requires_new_human_authorization",
        "stage128_m3_lag_wdi_next_action_executes_data_gate":
            _stage128_m3_lag_action_executes_data_gate(
                _STAGE128_M3_LAG_MODELING_ACTION_ID),
        "stage128_m3_lag_wdi_modeling_authorized": False,
        # DERIVED, never hard-coded: step E flips this, and a marker
        # function must not publish a moment as if it were a rule.
        "stage128_m3_lag_wdi_modeling_started":
            _stage128_m3_lag_modeling_started(root),
        "stage128_m3_lag_wdi_modeling_requires_new_human_authorization": True,
        "stage128_m3_lag_wdi_final_test_rows_read": 0,
        "stage128_m3_lag_wdi_world_bank_api_requests": 0,
        "stage128_m3_lag_wdi_action_sequence": [
            {
                "step": step,
                "action_id": action_id,
                "executes_retrieval": executes_retrieval,
                "executes_data_gate": executes_gate,
                "executes_modeling": executes_modeling,
                "was_authorized": step in ("A", "B", "C", "D"),
                "authorized_now": False,
                "authorized": False,
                "status": "COMPLETE" if step in ("A", "B", "C", "D")
                          else "NOT_AUTHORIZED",
            }
            for (step, action_id, executes_retrieval, executes_gate,
                 executes_modeling) in _STAGE128_M3_LAG_ACTION_SEQUENCE
        ],
    }


#: Stage128 Track B — the calendar-mapping lock package.
_STAGE128_M3_LAG_CALMAP_ACTION_ID = (
    "stage128-m3-lag-wdi-exploratory-calendar-mapping-lock")
_STAGE128_M3_LAG_CALMAP_PKG = (
    "project/stage128/m3_lag_wdi_exploratory_calendar_mapping_lock")
_STAGE128_M3_LAG_CALMAP_DECISION_REL = (
    f"{_STAGE128_M3_LAG_CALMAP_PKG}/"
    "stage128_m3_lag_wdi_calendar_mapping_decision.json")
_STAGE128_M3_LAG_CALMAP_EVIDENCE_REL = (
    f"{_STAGE128_M3_LAG_CALMAP_PKG}/"
    "stage128_m3_lag_wdi_calendar_mapping_timing_evidence.json")
_STAGE128_M3_LAG_CALMAP_AUDIT_REL = (
    f"{_STAGE128_M3_LAG_CALMAP_PKG}/"
    "stage128_m3_lag_wdi_calendar_mapping_execution_audit.json")
_STAGE128_M3_LAG_CALMAP_BOUNDARY_REL = (
    f"{_STAGE128_M3_LAG_CALMAP_PKG}/"
    "stage128_m3_lag_wdi_calendar_mapping_governance_boundary.json")

#: The only mapping the repository may publish as locked, and the one it must
#: publish as rejected. Pinned independently of the lock package so a swapped
#: constant there cannot validate itself here.
_STAGE128_M3_LAG_CALMAP_LOCKED_OFFSET = 621
_STAGE128_M3_LAG_CALMAP_LOCKED_RULE = "jalali_fiscal_year_t_plus_621"
_STAGE128_M3_LAG_CALMAP_REJECTED_OFFSET = 622

#: Counters a calendar-mapping lock must leave at zero.
_STAGE128_M3_LAG_CALMAP_ZERO_COUNTERS = (
    "world_bank_api_requests", "new_payloads_retrieved",
    "alternative_indicators_retrieved", "feature_value_tables_materialized",
    "feature_values_computed", "data_gate_executions",
    "post_retrieval_audit_executions", "coverage_calculations",
    "admission_decisions", "model_fits", "predictions", "predictive_metrics",
    "bootstrap_executions", "holm_calculations", "shap_executions",
    "tuning_runs", "cross_validation_runs", "model_selections",
    "final_test_rows_read", "final_test_predictor_values_read",
    "final_test_target_values_read",
)


def derive_stage128_m3_lag_wdi_calendar_mapping_lock_markers(
        root: str) -> dict:
    """Publish the M3-LAG-WDI calendar-mapping lock.

    Step D's Gate verdict is invariant to the two admissible Jalali-to-
    Gregorian mappings, but the feature VALUES are not — so the mapping had to
    be locked by a human scientific decision before any modeling table could
    exist. This publishes that lock, and fail-closes on the ways it could
    become something it is not:

    * a locked offset other than the one the timing evidence permits — the
      single most valuable check here, because swapping the offset is exactly
      how a leaking convention would be smuggled in;
    * a lock whose own evidence no longer supports it (the rejected offset
      suddenly showing no violation, or the locked one showing some);
    * a selection made on model performance, coverage or feature values;
    * a lock that reads as authorization for a feature table, for modeling,
      for step E or for the Final Test;
    * a lock that edits the frozen contract instead of amending it, or that
      erases the historical unlocked state;
    * a lock that quietly claims point-in-time availability it does not have.

    Returns {} before the lock package exists.
    """
    decision_path = os.path.join(
        root, _STAGE128_M3_LAG_CALMAP_DECISION_REL)
    if not os.path.isfile(decision_path):
        return {}
    decision = _require_json_artifact(
        root, _STAGE128_M3_LAG_CALMAP_DECISION_REL)
    evidence = _require_json_artifact(
        root, _STAGE128_M3_LAG_CALMAP_EVIDENCE_REL)
    audit = _require_json_artifact(root, _STAGE128_M3_LAG_CALMAP_AUDIT_REL)
    boundary = _require_json_artifact(
        root, _STAGE128_M3_LAG_CALMAP_BOUNDARY_REL)

    if decision.get("action_id") != _STAGE128_M3_LAG_CALMAP_ACTION_ID:
        raise HandoffError("the calendar-mapping lock action id is wrong")
    if decision.get("authorized_scope") != "calendar_mapping_lock_only":
        raise HandoffError(
            "the calendar-mapping lock scope must be "
            "calendar_mapping_lock_only")

    # ---- the locked rule is the one the evidence permits ------------------ #
    if decision.get("calendar_mapping_locked") is not True:
        raise HandoffError(
            "a calendar-mapping lock package must publish the mapping as "
            "locked")
    locked_offset = decision.get("calendar_mapping_locked_offset")
    if locked_offset != _STAGE128_M3_LAG_CALMAP_LOCKED_OFFSET:
        raise HandoffError(
            f"the locked calendar offset is {locked_offset}, not the "
            f"scientifically decided {_STAGE128_M3_LAG_CALMAP_LOCKED_OFFSET}; "
            "changing it requires a new explicit human scientific decision")
    if decision.get("calendar_mapping_rule") != (
            _STAGE128_M3_LAG_CALMAP_LOCKED_RULE):
        raise HandoffError(
            "the published calendar-mapping rule id does not match the "
            "locked offset")
    if decision.get("rejected_offset") != (
            _STAGE128_M3_LAG_CALMAP_REJECTED_OFFSET):
        raise HandoffError(
            "the rejected calendar offset must be "
            f"{_STAGE128_M3_LAG_CALMAP_REJECTED_OFFSET}")

    per_offset = evidence.get("per_offset") or {}
    selected = per_offset.get(str(locked_offset))
    rejected = per_offset.get(str(_STAGE128_M3_LAG_CALMAP_REJECTED_OFFSET))
    if not selected or not rejected:
        raise HandoffError(
            "the timing evidence must evaluate BOTH admissible mappings")
    if selected.get("timing_violation_rows") != 0 or selected.get(
            "satisfies_necessary_timing_condition") is not True:
        raise HandoffError(
            "the locked mapping must have ZERO timing violations: a mapping "
            "that needs an incomplete observation year admits future "
            "information")
    if rejected.get("timing_violation_rows", 0) <= 0 or rejected.get(
            "satisfies_necessary_timing_condition") is not False:
        raise HandoffError(
            "the recorded rejection basis is stale: the rejected mapping no "
            "longer shows a timing violation, so the lock would rest on a "
            "justification its own evidence contradicts")
    for field, expected in (
            ("locked_offset_timing_violation_rows",
             selected["timing_violation_rows"]),
            ("rejected_offset_timing_violation_rows",
             rejected["timing_violation_rows"])):
        if decision.get(field) != expected:
            raise HandoffError(
                f"{field} disagrees with the recomputed timing evidence")
    if evidence.get("denominator_rows") != _STAGE128_M3_LAG_PARENT_ROWS:
        raise HandoffError(
            "the calendar-mapping evidence must be computed over the "
            f"{_STAGE128_M3_LAG_PARENT_ROWS}-row development sample")

    # ---- a timing decision, not an outcome-driven one --------------------- #
    for field in ("selection_used_model_performance",
                  "selection_used_coverage_comparison",
                  "selection_used_feature_values",
                  "selection_reversible_by_a_better_predictive_result",
                  "point_in_time_availability_established_by_this_lock",
                  "historical_unlocked_state_erased",
                  "authorizes_next_action", "next_action_authorized",
                  "calendar_mapping_lock_required_before_modeling"):
        if decision.get(field) is not False:
            raise HandoffError(
                f"calendar-mapping decision {field} must be False")
    for field in ("amends_but_does_not_edit",
                  "changing_the_locked_mapping_requires_new_explicit_human_"
                  "decision"):
        if decision.get(field) is not True:
            raise HandoffError(
                f"calendar-mapping decision {field} must be True")
    if not (decision.get("unresolved_limitations") or []):
        raise HandoffError(
            "locking a calendar mapping resolves no data limitation, so the "
            "surviving limitations may not be published as none")

    # ---- it built nothing and authorized nothing -------------------------- #
    if audit.get("calendar_mapping_lock_executed") is not True:
        raise HandoffError("the calendar-mapping audit must record execution")
    if audit.get("calendar_mapping_lock_executions") != 1:
        raise HandoffError("the calendar mapping is locked exactly once")
    for counter in _STAGE128_M3_LAG_CALMAP_ZERO_COUNTERS:
        if audit.get(counter) != 0:
            raise HandoffError(
                f"calendar-mapping-lock-only: counter {counter} must be 0")
    for field in ("authoritative_contract_edited",
                  "data_gate_artifacts_modified",
                  "post_retrieval_audit_artifacts_modified",
                  "retained_bytes_modified", "deposited_evidence_modified"):
        if audit.get(field) is not False:
            raise HandoffError(
                f"the calendar-mapping lock may not mutate {field}")
    for field in ("calendar_mapping_lock_is_modeling_authorization",
                  "calendar_mapping_lock_authorizes_feature_value_table",
                  "calendar_mapping_lock_propagates_to_step_e",
                  "calendar_mapping_lock_is_final_test_unlock",
                  "calendar_mapping_lock_changed_the_gate_result",
                  "m3_lag_wdi_calendar_mapping_lock_authorized_now",
                  "m3_lag_wdi_calendar_mapping_lock_authorization_reusable",
                  "m3_lag_wdi_calendar_mapping_lock_required_before_modeling",
                  "m3_lag_wdi_next_action_authorized",
                  "m3_lag_wdi_modeling_authorized",
                  "m3_lag_wdi_modeling_started",
                  "m3_lag_wdi_data_gate_rerun_by_this_action",
                  "m3_lag_wdi_post_retrieval_audit_rerun_by_this_action",
                  "m3_lag_wdi_contract_edited_by_this_action",
                  "m3_lag_wdi_gate_thresholds_modified_by_this_action",
                  "point_in_time_availability_claimed",
                  "retrieval_authorized_now",
                  "new_world_bank_request_made_by_this_action",
                  "world_bank_inquiry_terminated_by_this_action",
                  "final_test_access_authorized", "m4_authorized",
                  "merge_authorized", "ready_for_review_authorized",
                  "pii_committed_to_git", "credentials_committed_to_git"):
        if boundary.get(field) is not False:
            raise HandoffError(
                f"calendar-mapping governance boundary {field} must be False")
    for field in ("m3_lag_wdi_calendar_mapping_locked",
                  "m3_lag_wdi_calendar_mapping_lock_action_authorized",
                  "m3_lag_wdi_calendar_mapping_lock_executed",
                  "m3_lag_wdi_calendar_mapping_lock_authorization_consumed",
                  "m3_lag_wdi_modeling_requires_new_explicit_human_"
                  "authorization",
                  "m3_lag_wdi_block_admission_is_data_admission_only",
                  "step_c_material_findings_preserved", "final_test_locked"):
        if boundary.get(field) is not True:
            raise HandoffError(
                f"calendar-mapping governance boundary {field} must be True")
    if boundary.get("m3_lag_wdi_data_gate_result") != (
            "PASS_M3_LAG_WDI_DATA_GATE"):
        raise HandoffError(
            "the calendar-mapping lock must carry the accepted Gate verdict "
            "forward unchanged")

    limitations = decision["unresolved_limitations"]
    return {
        "stage128_m3_lag_wdi_calendar_mapping_locked": True,
        "stage128_m3_lag_wdi_calendar_mapping_rule":
            decision["calendar_mapping_rule"],
        "stage128_m3_lag_wdi_calendar_mapping_rule_formula":
            decision["calendar_mapping_rule_formula"],
        "stage128_m3_lag_wdi_calendar_mapping_locked_offset": locked_offset,
        "stage128_m3_lag_wdi_calendar_mapping_lock_action_id":
            _STAGE128_M3_LAG_CALMAP_ACTION_ID,
        "stage128_m3_lag_wdi_calendar_mapping_lock_required_before_modeling":
            False,
        "stage128_m3_lag_wdi_calendar_mapping_lock_executed": True,
        # Its own one-time authorization: historical, consumed, never standing.
        "stage128_m3_lag_wdi_calendar_mapping_lock_was_authorized": True,
        "stage128_m3_lag_wdi_calendar_mapping_lock_authorized": False,
        "stage128_m3_lag_wdi_calendar_mapping_lock_authorized_now": False,
        "stage128_m3_lag_wdi_calendar_mapping_lock_authorization_consumed":
            True,
        "stage128_m3_lag_wdi_calendar_mapping_lock_authorization_reusable":
            False,
        # The evidence, republished so the rejection cannot quietly vanish.
        "stage128_m3_lag_wdi_calendar_mapping_rejected_offset":
            _STAGE128_M3_LAG_CALMAP_REJECTED_OFFSET,
        "stage128_m3_lag_wdi_calendar_mapping_rejected_offset_violations":
            rejected["timing_violation_rows"],
        "stage128_m3_lag_wdi_calendar_mapping_rejected_offset_worst_days":
            rejected["worst_violation_days_after_cutoff"],
        "stage128_m3_lag_wdi_calendar_mapping_locked_offset_violations": 0,
        "stage128_m3_lag_wdi_calendar_mapping_locked_offset_margin_days_min":
            selected["margin_days_min"],
        "stage128_m3_lag_wdi_calendar_mapping_predictor_year_first":
            selected["predictor_year_first"],
        "stage128_m3_lag_wdi_calendar_mapping_predictor_year_last":
            selected["predictor_year_last"],
        "stage128_m3_lag_wdi_calendar_mapping_observation_year_first":
            selected["observation_year_first"],
        "stage128_m3_lag_wdi_calendar_mapping_observation_year_last":
            selected["observation_year_last"],
        "stage128_m3_lag_wdi_calendar_mapping_selection_used_model_"
        "performance": False,
        "stage128_m3_lag_wdi_calendar_mapping_changing_requires_new_human_"
        "decision": True,
        "stage128_m3_lag_wdi_calendar_mapping_amends_but_does_not_edit": True,
        "stage128_m3_lag_wdi_calendar_mapping_unresolved_limitations":
            limitations,
        "stage128_m3_lag_wdi_calendar_mapping_unresolved_limitation_count":
            len(limitations),
        "stage128_m3_lag_wdi_fiscal_year_t_semantics":
            decision["fiscal_year_semantics"]["fiscal_year_t_labels"],
        # Locking a timing convention authorizes nothing downstream.
        "stage128_m3_lag_wdi_calendar_mapping_lock_authorizes_modeling": False,
        "stage128_m3_lag_wdi_calendar_mapping_lock_authorizes_feature_table":
            False,
        "stage128_m3_lag_wdi_modeling_authorized": False,
        # DERIVED, never hard-coded: step E flips this, and a marker
        # function must not publish a moment as if it were a rule.
        "stage128_m3_lag_wdi_modeling_started":
            _stage128_m3_lag_modeling_started(root),
        "stage128_m3_lag_wdi_next_action_authorized": False,
    }


#: The step E package. Every file is re-read; nothing about the result is
#: taken on trust from the summary fields alone.
_STAGE128_M3_LAG_EVAL_DIR = (
    "project/stage128/m3_lag_wdi_exploratory_incremental_evaluation")
_STAGE128_M3_LAG_EVAL_BOUNDARY_REL = (
    f"{_STAGE128_M3_LAG_EVAL_DIR}/"
    "stage128_m3_lag_wdi_evaluation_governance_boundary.json")
_STAGE128_M3_LAG_EVAL_AUDIT_REL = (
    f"{_STAGE128_M3_LAG_EVAL_DIR}/"
    "stage128_m3_lag_wdi_evaluation_execution_audit.json")
_STAGE128_M3_LAG_EVAL_SAMPLE_REL = (
    f"{_STAGE128_M3_LAG_EVAL_DIR}/"
    "stage128_m3_lag_wdi_evaluation_common_sample_audit.json")
_STAGE128_M3_LAG_EVAL_MULTIPLICITY_REL = (
    f"{_STAGE128_M3_LAG_EVAL_DIR}/"
    "stage128_m3_lag_wdi_evaluation_multiplicity_family_status.json")
_STAGE128_M3_LAG_EVAL_FITS_REL = (
    f"{_STAGE128_M3_LAG_EVAL_DIR}/"
    "stage128_m3_lag_wdi_evaluation_predictive_fit_count_audit.json")
_STAGE128_M3_LAG_EVAL_QC_REL = (
    f"{_STAGE128_M3_LAG_EVAL_DIR}/"
    "stage128_m3_lag_wdi_evaluation_qc_report.json")

_STAGE128_M3_LAG_EVAL_ACTION_ID = _STAGE128_M3_LAG_MODELING_ACTION_ID
_STAGE128_M3_LAG_EVAL_SCOPE = "exploratory_incremental_evaluation_only"
_STAGE128_M3_LAG_EVAL_FAMILY_ID = "M3_LAG_WDI_EXPLORATORY_SUPPLEMENTARY"
_STAGE128_M3_LAG_EVAL_HYPOTHESIS_ID = "E1"
_STAGE128_M3_LAG_EVAL_RESULTS_LABEL = "supplementary_exploratory_robustness_only"
_STAGE128_M3_LAG_EVAL_ROLE = "supplementary_exploratory_robustness_block"
_STAGE128_M3_LAG_EVAL_M2_FEATURES = 12
_STAGE128_M3_LAG_EVAL_M3_FEATURES = 14
_STAGE128_M3_LAG_EVAL_FIT_COUNT = 44

#: Counters step E must leave at exactly zero. Fitting a model is the ONLY new
#: capability this action had.
_STAGE128_M3_LAG_EVAL_ZERO_COUNTERS = (
    "world_bank_api_requests", "new_payloads_retrieved",
    "alternative_indicators_searched", "alternative_indicators_retrieved",
    "step_c_reruns", "step_d_reruns", "data_gate_executions",
    "calendar_mapping_lock_reruns", "calendar_mapping_changes",
    "third_macro_features_added", "feature_searches", "feature_selections",
    "feature_substitutions", "imputations",
    "rows_excluded_outside_frozen_complete_case_rule",
    "tuning_runs", "grid_searches", "hyperparameter_searches",
    "model_family_searches", "model_selections",
    "metric_definitions_created", "metric_definitions_changed",
    "validation_windows_changed", "thresholds_changed",
    "seed_policy_changes", "shap_executions", "holm_calculations",
    "confirmatory_holm_executions", "confirmatory_family_modifications",
    "paper_winner_selections", "final_test_rows_read",
    "final_test_predictor_values_read", "final_test_target_values_read",
    "final_test_unlocks", "m4_actions",
    "pr_ready_for_review_transitions", "pr_merges",
)


def derive_stage128_m3_lag_wdi_incremental_evaluation_markers(
        root: str) -> dict:
    """Publish Track B step E — the exploratory incremental evaluation.

    This is the first Track B action that fits a model, so it is the first one
    whose RESULT could be misread as changing the paper. The fail-closed checks
    here are aimed squarely at that:

    * a result that leaked out of the exploratory family into the confirmatory
      Holm family, or that was published as a confirmatory superiority claim —
      the single most valuable check here;
    * a comparison run on two DIFFERENT samples for the two blocks, or one
      that quietly reused the published 666-row M1 results as the comparator
      instead of refitting M2;
    * a feature architecture that is not exactly 12 versus 14;
    * a calendar mapping, threshold, metric, validation window, seed or
      hyperparameter that moved because the result was observed;
    * a limitation marked resolved by a favourable predictive result;
    * any Final Test read, retrieval, rerun, SHAP run or merge/ready
      transition.

    Returns {} before the step E package exists.
    """
    if not _stage128_m3_lag_modeling_started(root):
        return {}

    decision = _require_json_artifact(
        root, _STAGE128_M3_LAG_EVAL_DECISION_REL)
    boundary = _require_json_artifact(
        root, _STAGE128_M3_LAG_EVAL_BOUNDARY_REL)
    audit = _require_json_artifact(root, _STAGE128_M3_LAG_EVAL_AUDIT_REL)
    sample = _require_json_artifact(root, _STAGE128_M3_LAG_EVAL_SAMPLE_REL)
    multiplicity = _require_json_artifact(
        root, _STAGE128_M3_LAG_EVAL_MULTIPLICITY_REL)
    fits = _require_json_artifact(root, _STAGE128_M3_LAG_EVAL_FITS_REL)
    qc = _require_json_artifact(root, _STAGE128_M3_LAG_EVAL_QC_REL)

    if decision.get("action_id") != _STAGE128_M3_LAG_EVAL_ACTION_ID:
        raise HandoffError("the step E action id is wrong")
    if decision.get("authorized_scope") != _STAGE128_M3_LAG_EVAL_SCOPE:
        raise HandoffError(
            f"the step E scope must be {_STAGE128_M3_LAG_EVAL_SCOPE}")

    # ---- the result stayed exploratory ----------------------------------- #
    if decision.get("comparison_family") != _STAGE128_M3_LAG_EVAL_FAMILY_ID:
        raise HandoffError(
            "the step E comparison must live in the exploratory family "
            f"{_STAGE128_M3_LAG_EVAL_FAMILY_ID}")
    if decision.get("hypothesis_id") != _STAGE128_M3_LAG_EVAL_HYPOTHESIS_ID:
        raise HandoffError("the step E hypothesis id must be E1")
    if decision.get("results_label") != _STAGE128_M3_LAG_EVAL_RESULTS_LABEL:
        raise HandoffError(
            "step E results must be labelled "
            f"{_STAGE128_M3_LAG_EVAL_RESULTS_LABEL}")
    if decision.get("scientific_role") != _STAGE128_M3_LAG_EVAL_ROLE:
        raise HandoffError(
            "the M3-LAG-WDI scientific role may not change at step E")
    if list(multiplicity.get("confirmatory_holm_family") or []) != list(
            _STAGE128_M3_LAG_CONFIRMATORY_FAMILY):
        raise HandoffError(
            "the confirmatory Holm family membership changed at step E")
    for field in ("exploratory_comparison_inserted_into_confirmatory_family",
                  "confirmatory_holm_family_changed_by_this_action",
                  "confirmatory_holm_executed_by_this_action",
                  "confirmatory_holm_modified_by_this_action",
                  "e1_is_confirmatory", "confirmatory_superiority_claim_made",
                  "paper_winner_selected_by_this_action",
                  "main_confirmatory_conclusion_changed_by_this_action"):
        if multiplicity.get(field) is not False:
            raise HandoffError(
                f"step E multiplicity field {field} must be False: an "
                "exploratory result may never become a confirmatory one")
    for field in ("confirmatory_superiority_claim_made",
                  "confirmatory_conclusions_changed",
                  "confirmatory_holm_family_changed", "paper_winner_selected",
                  "block_promoted_to_confirmatory",
                  "m3_cbi_repaired_by_this_action",
                  "m3i2_replaced_by_this_action",
                  "authorizes_next_action", "next_action_authorized"):
        if decision.get(field) is not False:
            raise HandoffError(f"step E decision {field} must be False")

    # ---- one sample, two nested blocks, 12 versus 14 ---------------------- #
    if sample.get("identical_sample_for_both_blocks") is not True:
        raise HandoffError(
            "step E must evaluate both blocks on the identical sample")
    composition = sample.get("composition") or {}
    if composition.get("rows") != _STAGE128_M3_LAG_PARENT_ROWS:
        raise HandoffError(
            f"the step E sample is {composition.get('rows')} rows, not the "
            f"admitted {_STAGE128_M3_LAG_PARENT_ROWS}")
    if (sample.get("attrition_from_parent") or {}).get(
            "exclusions_outside_the_frozen_complete_case_rule") != 0:
        raise HandoffError(
            "step E excluded rows outside the frozen complete-case rule")
    if fits.get("primary_predictive_fits") != _STAGE128_M3_LAG_EVAL_FIT_COUNT:
        raise HandoffError(
            f"step E must record exactly {_STAGE128_M3_LAG_EVAL_FIT_COUNT} "
            "primary predictive fits")
    counts = fits.get("feature_counts_by_block") or {}
    if counts.get("M2") != [_STAGE128_M3_LAG_EVAL_M2_FEATURES]:
        raise HandoffError("the M2 comparator must be fit on exactly 12 "
                           "features")
    if counts.get("M3_LAG_WDI") != [_STAGE128_M3_LAG_EVAL_M3_FEATURES]:
        raise HandoffError("the M3-LAG-WDI block must be fit on exactly 14 "
                           "features")
    if sample.get("calendar_mapping_locked_offset") is not None and (
            sample.get("calendar_mapping_locked_offset")
            != _STAGE128_M3_LAG_CALMAP_LOCKED_OFFSET):
        raise HandoffError("step E used a calendar offset other than +621")
    if sample.get("calendar_mapping_rule") != (
            _STAGE128_M3_LAG_CALMAP_LOCKED_RULE):
        raise HandoffError("step E used a calendar rule other than the locked "
                           "one")
    if sample.get("same_year_t_observations_read") != 0:
        raise HandoffError(
            "step E read a same-year t macro observation, which the contract "
            "forbids")
    if sample.get("final_test_rows_in_sample") != 0:
        raise HandoffError("a final-test row reached the step E sample")

    # ---- nothing was changed because of what the result showed ----------- #
    for counter in _STAGE128_M3_LAG_EVAL_ZERO_COUNTERS:
        if audit.get(counter) != 0:
            raise HandoffError(
                f"exploratory-evaluation-only: counter {counter} must be 0")
    for field in ("retained_bytes_modified", "deposited_evidence_modified",
                  "step_c_artifacts_modified", "step_d_artifacts_modified",
                  "calendar_lock_artifacts_modified",
                  "authoritative_contract_edited",
                  "confirmatory_holm_state_modified"):
        if audit.get(field) is not False:
            raise HandoffError(f"step E may not mutate {field}")
    for field in ("retuning_executed", "grid_search_executed",
                  "model_family_search_executed", "feature_search_executed",
                  "feature_substitution_executed", "imputation_executed",
                  "metric_definition_changed",
                  "validation_architecture_changed", "seed_policy_changed",
                  "thresholds_changed", "shap_executed",
                  "calendar_mapping_changed_by_this_action",
                  "step_c_rerun_by_this_action", "step_d_rerun_by_this_action",
                  "data_gate_rerun_by_this_action",
                  "calendar_mapping_lock_rerun_by_this_action",
                  "m3_lag_wdi_contract_edited_by_this_action",
                  "m3_lag_wdi_gate_thresholds_modified_by_this_action",
                  # The block's role never moves, whatever the numbers said.
                  "m3_lag_wdi_is_confirmatory_m3",
                  "m3_lag_wdi_replaces_m3_cbi", "m3_lag_wdi_repairs_m3_cbi",
                  "m3_lag_wdi_replaces_m3i2",
                  "m3_lag_wdi_is_historical_vintage_wdi",
                  "m3_lag_wdi_is_real_time_wdi",
                  "m3_lag_wdi_in_confirmatory_holm_family",
                  "m3_lag_wdi_can_select_paper_winner",
                  "m3_lag_wdi_point_in_time_availability_proven",
                  # One-time grants, all spent.
                  "m3_lag_wdi_modeling_authorized_now",
                  "m3_lag_wdi_modeling_authorization_reusable",
                  "prior_authorization_reused_by_this_action",
                  "retrieval_authorized_now",
                  "post_retrieval_audit_authorized_now",
                  "data_gate_authorized_now",
                  "calendar_mapping_lock_authorized_now",
                  # Hard locks.
                  "final_test_access_authorized",
                  "final_test_unlocked_by_this_action",
                  "new_world_bank_request_made_by_this_action",
                  "world_bank_inquiry_terminated_by_this_action",
                  "m4_authorized", "merge_authorized",
                  "ready_for_review_authorized",
                  "m3_lag_wdi_next_action_authorized",
                  "pii_committed_to_git", "credentials_committed_to_git"):
        if boundary.get(field) is not False:
            raise HandoffError(
                f"step E governance boundary {field} must be False")
    for field in ("m3_lag_wdi_modeling_action_authorized",
                  "m3_lag_wdi_modeling_executed",
                  "m3_lag_wdi_modeling_started",
                  "m3_lag_wdi_modeling_authorization_consumed",
                  "step_c_material_findings_preserved",
                  "step_d_gate_result_preserved",
                  "m3_lag_wdi_block_admission_is_data_admission_only",
                  "final_test_locked",
                  "next_action_requires_new_explicit_human_decision"):
        if boundary.get(field) is not True:
            raise HandoffError(
                f"step E governance boundary {field} must be True")
    if boundary.get("final_test_rows_read") != 0:
        raise HandoffError("step E must read 0 Final Test rows")

    # ---- limitations survive the result ---------------------------------- #
    limitations = decision.get("limitations") or []
    if not limitations:
        raise HandoffError(
            "fitting a model resolves none of the block's data limitations, "
            "so they may not be published as none")
    for item in limitations:
        if item.get("resolved_by_this_action") is not False:
            raise HandoffError(
                f"step E limitation {item.get('id')!r} may not be marked "
                "resolved by a modeling action")
        if item.get("erased_by_a_favourable_predictive_result") is not False:
            raise HandoffError(
                f"step E limitation {item.get('id')!r} may not be erased by a "
                "favourable predictive result")
    limitation_ids = [item["id"] for item in limitations]
    for required in ("point_in_time_wdi_availability_unproven",
                     "lagging_does_not_create_point_in_time_data",
                     "fx_degenerate_2021_2024", "fx_missing_2024_2025"):
        if required not in limitation_ids:
            raise HandoffError(
                f"the step E limitation {required!r} must be preserved")

    if qc.get("all_pass") is not True or qc.get("failed") != 0:
        raise HandoffError("the step E QC report does not pass")

    return {
        "stage128_m3_lag_wdi_modeling_action_id":
            _STAGE128_M3_LAG_EVAL_ACTION_ID,
        "stage128_m3_lag_wdi_modeling_executed": True,
        "stage128_m3_lag_wdi_last_completed_action_id":
            _STAGE128_M3_LAG_EVAL_ACTION_ID,
        # Its own one-time authorization: historical, consumed, never standing.
        "stage128_m3_lag_wdi_modeling_was_authorized": True,
        "stage128_m3_lag_wdi_modeling_authorized": False,
        "stage128_m3_lag_wdi_modeling_authorized_now": False,
        "stage128_m3_lag_wdi_modeling_authorization_consumed": True,
        "stage128_m3_lag_wdi_modeling_authorization_reusable": False,
        # The comparison, and the family it is confined to.
        "stage128_m3_lag_wdi_comparison_id": decision["comparison"],
        "stage128_m3_lag_wdi_hypothesis_id":
            _STAGE128_M3_LAG_EVAL_HYPOTHESIS_ID,
        "stage128_m3_lag_wdi_exploratory_family_id":
            _STAGE128_M3_LAG_EVAL_FAMILY_ID,
        "stage128_m3_lag_wdi_results_label":
            _STAGE128_M3_LAG_EVAL_RESULTS_LABEL,
        "stage128_m3_lag_wdi_scientific_role": _STAGE128_M3_LAG_EVAL_ROLE,
        "stage128_m3_lag_wdi_e1_conclusion": decision["e1_conclusion"],
        "stage128_m3_lag_wdi_e1_direction_by_family":
            decision["e1_direction_by_family"],
        "stage128_m3_lag_wdi_e1_any_interval_excludes_zero":
            decision["e1_any_family_interval_excludes_zero"],
        # The sample and the architecture.
        "stage128_m3_lag_wdi_evaluation_rows": composition["rows"],
        "stage128_m3_lag_wdi_evaluation_positive": composition["positive"],
        "stage128_m3_lag_wdi_evaluation_negative": composition["negative"],
        "stage128_m3_lag_wdi_evaluation_companies": composition["companies"],
        "stage128_m3_lag_wdi_evaluation_pooled_oof_rows":
            composition["pooled_oof_rows"],
        "stage128_m3_lag_wdi_evaluation_pooled_oof_positive":
            composition["pooled_oof_positive"],
        "stage128_m3_lag_wdi_evaluation_identical_sample_for_both_blocks":
            True,
        "stage128_m3_lag_wdi_m2_feature_count":
            _STAGE128_M3_LAG_EVAL_M2_FEATURES,
        "stage128_m3_lag_wdi_block_feature_count":
            _STAGE128_M3_LAG_EVAL_M3_FEATURES,
        "stage128_m3_lag_wdi_primary_predictive_fits":
            _STAGE128_M3_LAG_EVAL_FIT_COUNT,
        "stage128_m3_lag_wdi_evaluation_predictor_year_first":
            sample["predictor_year_first"],
        "stage128_m3_lag_wdi_evaluation_predictor_year_last":
            sample["predictor_year_last"],
        # What it explicitly is not.
        "stage128_m3_lag_wdi_confirmatory_superiority_claim_made": False,
        "stage128_m3_lag_wdi_in_confirmatory_holm_family": False,
        "stage128_m3_lag_wdi_confirmatory_holm_family_changed": False,
        "stage128_m3_lag_wdi_confirmatory_holm_executed": False,
        "stage128_m3_lag_wdi_paper_winner_selected": False,
        "stage128_m3_lag_wdi_point_in_time_availability_claimed": False,
        "stage128_m3_lag_wdi_evaluation_limitations": limitation_ids,
        "stage128_m3_lag_wdi_evaluation_limitation_count":
            len(limitation_ids),
        "stage128_m3_lag_wdi_evaluation_qc_assertions": qc["assertions"],
        "stage128_m3_lag_wdi_evaluation_qc_all_pass": True,
        "stage128_m3_lag_wdi_final_test_rows_read": 0,
        # Nothing downstream is authorized by this result.
        "stage128_m3_lag_wdi_next_action_id": "human_decision_required",
        "stage128_m3_lag_wdi_next_action_authorized": False,
        "stage128_m3_lag_wdi_next_action_scope":
            "no_further_action_is_authorized",
        # The pointer no longer names a Track B action, so the descriptive
        # "does the next action execute the Gate" property is republished here
        # rather than left derived from the superseded step E pointer: there
        # is no next action to describe until a human names one.
        "stage128_m3_lag_wdi_next_action_executes_data_gate": False,
        "stage128_m3_lag_wdi_next_action_executes_data_gate_semantics":
            "no_next_action_is_named_so_nothing_is_described",
        "stage128_m3_lag_wdi_track_b_sequence_complete": True,
        "stage128_m3_lag_wdi_action_sequence": [
            {
                "step": step,
                "action_id": action_id,
                "executes_retrieval": executes_retrieval,
                "executes_data_gate": executes_gate,
                "executes_modeling": executes_modeling,
                # "authorized" is STANDING: consumed one-time authorizations
                # (A, B, C, D, E) are history, recorded in "was_authorized"
                # only. Step E fitting a model does not make its one-time
                # authorization reusable or standing.
                "was_authorized": step in ("A", "B", "C", "D", "E"),
                "authorized_now": False,
                "authorized": False,
                "status": "COMPLETE" if step in ("A", "B", "C", "D", "E")
                          else "NOT_AUTHORIZED",
            }
            for (step, action_id, executes_retrieval, executes_gate,
                 executes_modeling) in _STAGE128_M3_LAG_ACTION_SEQUENCE
        ],
    }


def derive_stage128_m3_lag_wdi_retrieval_live_pr_topology_markers(
        root: str) -> dict:
    """Publish the LIVE (retrieval) PR topology and demote PR #78 to history.

    The contract-lock artifact records the topology that was live *at contract
    time*: PR #78 as the live Draft, based on the merge commit of PR #77. That
    is now history — PR #78 has since been MERGED into ``main`` by
    ``175e7949…``, and the live Draft is the separate retrieval PR #79.

    Fail-closed, and deliberately narrow:

    * the merged predecessor is pinned to PR #78 **and** to its merge commit,
      so a merged PR can never be re-published as the live Draft;
    * the live PR must be a strict successor of it, must be an open Draft, and
      must be based on exactly that merge commit;
    * every historical role (#76 documentary-recovery initiation, #77 human
      submission recording, #78 contract lock) is pinned and carried forward
      unchanged — roles are facts about actions, never labels for "whatever
      merged most recently";
    * any entry in the published role sequence that carries a merge commit is
      MERGED history, and only the final entry may be the live Draft.

    Returns {} before the retrieval package exists. Publishing a live topology
    is pure metadata: it admits nothing and moves no scientific state.
    """
    topology_path = os.path.join(
        root, _STAGE128_M3_LAG_RETRIEVAL_TOPOLOGY_REL)
    if not os.path.isfile(topology_path):
        return {}
    topology = _require_json_artifact(
        root, _STAGE128_M3_LAG_RETRIEVAL_TOPOLOGY_REL)
    if topology.get("action_id") != _STAGE128_M3_LAG_RETRIEVAL_ACTION_ID:
        raise HandoffError(
            "the M3-LAG-WDI retrieval PR topology names another action")

    live_number = topology.get("live_pr_number")
    predecessor_number = topology.get("predecessor_pr_number")
    for value, label in ((live_number, "live"),
                         (predecessor_number, "predecessor")):
        if not isinstance(value, int) or isinstance(value, bool):
            raise HandoffError(
                f"the M3-LAG-WDI retrieval {label} PR number must be an "
                "integer")
    if predecessor_number != _STAGE128_M3_LAG_RETRIEVAL_MERGED_PREDECESSOR_PR:
        raise HandoffError(
            "the merged predecessor of the M3-LAG-WDI retrieval PR is PR "
            f"#{_STAGE128_M3_LAG_RETRIEVAL_MERGED_PREDECESSOR_PR}")
    if live_number <= predecessor_number:
        raise HandoffError(
            f"the live PR #{live_number} must succeed the merged predecessor "
            f"PR #{predecessor_number}")

    merge_commit = topology.get("predecessor_pr_merge_commit")
    base_commit = topology.get("live_pr_base_commit")
    for value, label in ((merge_commit, "predecessor merge"),
                         (base_commit, "live PR base")):
        if not (isinstance(value, str) and len(value) == 40):
            raise HandoffError(
                f"the M3-LAG-WDI retrieval {label} commit must be a full "
                "40-hex SHA")
    if merge_commit != _STAGE128_M3_LAG_RETRIEVAL_MERGED_PREDECESSOR_COMMIT:
        raise HandoffError(
            f"PR #{_STAGE128_M3_LAG_RETRIEVAL_MERGED_PREDECESSOR_PR} was "
            f"merged by {_STAGE128_M3_LAG_RETRIEVAL_MERGED_PREDECESSOR_COMMIT}")
    if base_commit != merge_commit:
        raise HandoffError(
            "the live M3-LAG-WDI retrieval PR must be based on the merge "
            "commit of its merged predecessor")
    if topology.get("live_pr_base_branch") != _STAGE128_M3I2_LIVE_BASE_BRANCH:
        raise HandoffError(
            f"the live PR must target {_STAGE128_M3I2_LIVE_BASE_BRANCH}")
    if topology.get("live_pr_role") != (
            _STAGE128_M3_LAG_RETRIEVAL_LIVE_PR_ROLE):
        raise HandoffError(
            "the live M3-LAG-WDI retrieval PR role must be "
            f"{_STAGE128_M3_LAG_RETRIEVAL_LIVE_PR_ROLE}")
    if topology.get("predecessor_pr_role") != (
            _STAGE128_M3_LAG_RETRIEVAL_MERGED_PREDECESSOR_ROLE):
        raise HandoffError(
            f"PR #{_STAGE128_M3_LAG_RETRIEVAL_MERGED_PREDECESSOR_PR} keeps "
            f"the role {_STAGE128_M3_LAG_RETRIEVAL_MERGED_PREDECESSOR_ROLE}")

    for field, expected in (
        ("predecessor_pr_merged", True),
        ("contract_lock_pr_merged", True),
        ("documentary_recovery_pr_merged", True),
        ("human_submission_pr_merged", True),
        ("pr_roles_are_historical_facts_not_positional", True),
        ("recovery_pr_role_is_pinned_to_pr76", True),
        ("live_pr_is_draft", True),
        ("live_pr_merged", False),
        ("merge_authorized", False),
        ("auto_merge", False),
        ("ready_for_review_authorized", False),
        ("pr_is_stacked_on_open_predecessor", False),
        ("live_pr_head_commit_pinned", False),
        ("live_pr_head_is_github_pr_head", False),
        ("pr_roles_re_derived_from_adjacency", False),
    ):
        if topology.get(field) is not expected:
            raise HandoffError(
                f"M3-LAG-WDI retrieval topology {field} must be {expected}")
    if topology.get("live_pr_head_semantics") != (
            _STAGE128_M3I2_LIVE_PR_HEAD_SEMANTICS):
        raise HandoffError(
            "the live PR head semantics must be "
            f"{_STAGE128_M3I2_LIVE_PR_HEAD_SEMANTICS}")

    # --- HISTORICAL PR ROLES: pinned, never re-derived from adjacency ---- #
    for field, expected, label in (
        ("documentary_recovery_pr_number",
         _STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR,
         "the documentary-recovery INITIATION PR number"),
        ("documentary_recovery_pr_merge_commit",
         _STAGE128_M3I2_DOCUMENTARY_RECOVERY_MERGE_COMMIT,
         "the documentary-recovery PR merge commit"),
        ("documentary_recovery_pr_role",
         _STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR_ROLE,
         "the documentary-recovery PR role"),
        ("documentary_recovery_pr_semantics",
         _STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR_SEMANTICS,
         "the documentary-recovery PR supersession semantics"),
        ("human_submission_pr_number", _STAGE128_M3I2_HUMAN_SUBMISSION_PR,
         "the human-submission RECORDING PR number"),
        ("human_submission_pr_merge_commit",
         _STAGE128_M3I2_HUMAN_SUBMISSION_MERGE_COMMIT,
         "the human-submission PR merge commit"),
        ("human_submission_pr_role", _STAGE128_M3I2_HUMAN_SUBMISSION_PR_ROLE,
         "the human-submission PR role"),
        ("contract_lock_pr_number",
         _STAGE128_M3_LAG_RETRIEVAL_MERGED_PREDECESSOR_PR,
         "the M3-LAG-WDI contract-lock PR number"),
        ("contract_lock_pr_merge_commit",
         _STAGE128_M3_LAG_RETRIEVAL_MERGED_PREDECESSOR_COMMIT,
         "the M3-LAG-WDI contract-lock PR merge commit"),
        ("contract_lock_pr_role",
         _STAGE128_M3_LAG_RETRIEVAL_MERGED_PREDECESSOR_ROLE,
         "the M3-LAG-WDI contract-lock PR role"),
        ("contract_lock_pr_action_id",
         _STAGE128_M3_LAG_RETRIEVAL_MERGED_PREDECESSOR_ACTION_ID,
         "the M3-LAG-WDI contract-lock PR action id"),
    ):
        if topology.get(field) != expected:
            raise HandoffError(f"{label} is pinned to {expected!r}")

    recovery_number = topology.get("documentary_recovery_pr_number")
    submission_number = topology.get("human_submission_pr_number")
    if not (recovery_number < submission_number < predecessor_number
            < live_number):
        raise HandoffError(
            "the four PR roles must stay four distinct PRs in order: "
            f"#{recovery_number} (documentary recovery initiation) -> "
            f"#{submission_number} (human submission recording) -> "
            f"#{predecessor_number} (contract lock, merged) -> "
            f"#{live_number} (live Draft retrieval)")

    # --- A MERGED PR MAY NEVER BE REPUBLISHED AS THE LIVE DRAFT ---------- #
    # This is the regression guard. Every sequence entry carrying a merge
    # commit is merged history; only the final entry may be the open Draft,
    # and the live PR number may never collide with a merged one.
    sequence = topology.get("pr_role_sequence") or []
    expected_sequence = [
        (_STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR,
         _STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR_ROLE, True,
         _STAGE128_M3I2_DOCUMENTARY_RECOVERY_MERGE_COMMIT),
        (_STAGE128_M3I2_HUMAN_SUBMISSION_PR,
         _STAGE128_M3I2_HUMAN_SUBMISSION_PR_ROLE, True,
         _STAGE128_M3I2_HUMAN_SUBMISSION_MERGE_COMMIT),
        (_STAGE128_M3_LAG_RETRIEVAL_MERGED_PREDECESSOR_PR,
         _STAGE128_M3_LAG_RETRIEVAL_MERGED_PREDECESSOR_ROLE, True,
         _STAGE128_M3_LAG_RETRIEVAL_MERGED_PREDECESSOR_COMMIT),
        (live_number, _STAGE128_M3_LAG_RETRIEVAL_LIVE_PR_ROLE, False, None),
    ]
    if [(entry.get("pr_number"), entry.get("role"), entry.get("merged"),
         entry.get("merge_commit")) for entry in sequence] != (
            expected_sequence):
        raise HandoffError(
            "the published PR role sequence must be exactly "
            f"#{_STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR} -> "
            f"#{_STAGE128_M3I2_HUMAN_SUBMISSION_PR} -> "
            f"#{_STAGE128_M3_LAG_RETRIEVAL_MERGED_PREDECESSOR_PR} -> "
            f"#{live_number}")
    merged_numbers = {entry.get("pr_number") for entry in sequence
                      if entry.get("merged") is True}
    if live_number in merged_numbers:
        raise HandoffError(
            f"PR #{live_number} is recorded as MERGED and therefore may never "
            "be published as the live Draft")
    for entry in sequence:
        if entry.get("merged") is True and not entry.get("merge_commit"):
            raise HandoffError(
                f"merged PR #{entry.get('pr_number')} must record its merge "
                "commit")
        if entry.get("merged") is False and entry.get("merge_commit"):
            raise HandoffError(
                f"unmerged PR #{entry.get('pr_number')} must not record a "
                "merge commit")

    return {
        # LIVE topology re-anchored onto THIS Draft PR; PR #78 is now history.
        "stage128_m3i2_live_pr_number": live_number,
        "stage128_m3i2_live_pr_base_branch":
            topology.get("live_pr_base_branch"),
        "stage128_m3i2_live_pr_base_commit": base_commit,
        "stage128_m3i2_live_main_commit": base_commit,
        "stage128_m3i2_live_pr_is_draft": True,
        "stage128_m3i2_live_pr_merged": False,
        "stage128_m3i2_live_pr_role": topology.get("live_pr_role"),
        "stage128_m3i2_live_pr_head_commit_source":
            _STAGE128_M3I2_LIVE_PR_HEAD_SEMANTICS,
        "stage128_m3i2_live_pr_ready_for_review_authorized": False,
        # PR #78 is the MERGED predecessor now, with its merge commit pinned.
        "stage128_m3_lag_wdi_contract_lock_pr_number": predecessor_number,
        "stage128_m3_lag_wdi_contract_lock_pr_merged": True,
        "stage128_m3_lag_wdi_contract_lock_pr_merge_commit": merge_commit,
        "stage128_m3_lag_wdi_contract_lock_pr_role":
            _STAGE128_M3_LAG_RETRIEVAL_MERGED_PREDECESSOR_ROLE,
        "stage128_m3_lag_wdi_contract_lock_pr_action_id":
            _STAGE128_M3_LAG_RETRIEVAL_MERGED_PREDECESSOR_ACTION_ID,
        "stage128_m3_lag_wdi_contract_lock_pr_semantics": (
            f"merged_predecessor_superseded_by_pr{live_number}"),
        "stage128_m3_lag_wdi_retrieval_pr_number": live_number,
        # The pinned historical roles are unchanged by this re-anchoring.
        "stage128_m3i2_recovery_pr_number":
            _STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR,
        "stage128_m3i2_recovery_pr_merged": True,
        "stage128_m3i2_recovery_pr_merge_commit":
            _STAGE128_M3I2_DOCUMENTARY_RECOVERY_MERGE_COMMIT,
        "stage128_m3i2_recovery_pr_role":
            _STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR_ROLE,
        "stage128_m3i2_recovery_pr_action_id":
            _STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR_ACTION_ID,
        "stage128_m3i2_recovery_pr_semantics":
            _STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR_SEMANTICS,
        "stage128_m3i2_human_submission_pr_number":
            _STAGE128_M3I2_HUMAN_SUBMISSION_PR,
        "stage128_m3i2_human_submission_pr_merged": True,
        "stage128_m3i2_human_submission_pr_merge_commit":
            _STAGE128_M3I2_HUMAN_SUBMISSION_MERGE_COMMIT,
        "stage128_m3i2_human_submission_pr_role":
            _STAGE128_M3I2_HUMAN_SUBMISSION_PR_ROLE,
        "stage128_m3i2_human_submission_pr_action_id":
            _STAGE128_M3I2_HUMAN_SUBMISSION_PR_ACTION_ID,
        # #77 was superseded by #78, NOT by whatever Draft is live now.
        "stage128_m3i2_human_submission_pr_semantics": (
            "merged_predecessor_superseded_by_pr"
            f"{_STAGE128_M3_LAG_RETRIEVAL_MERGED_PREDECESSOR_PR}"),
        "stage128_m3i2_pr_roles_are_historical_facts_not_positional": True,
        "stage128_m3i2_pr_role_sequence": [
            {
                "pr_number": entry[0],
                "role": entry[1],
                "merged": entry[2],
                "merge_commit": entry[3],
            }
            for entry in expected_sequence
        ],
        "stage128_m3i2_merge_authorized": False,
        # Topology metadata never moves the scientific state.
        "m3i2_data_gate_executed": False,
        "m3i2_block_admitted": False,
        "m3i2_modeling_started": False,
        "m4_authorized": False,
        "final_test_locked": True,
    }


# --------------------------------------------------------------------------- #
# Stage128 — Track A waiting-period termination and M3-LAG-WDI final
# disposition (governance DECISION RECORDING, not a one-action authorization)
# --------------------------------------------------------------------------- #

_STAGE128_TRACK_A_TERMINATION_PKG = (
    "project/stage128/m3i2_track_a_waiting_termination_and_m3_disposition")
_STAGE128_TRACK_A_TERMINATION_ACTION_ID = (
    "stage128-m3i2-track-a-waiting-termination-and-m3-disposition")
_STAGE128_TRACK_A_TERMINATION_DECISION_REL = (
    f"{_STAGE128_TRACK_A_TERMINATION_PKG}/"
    "stage128_m3i2_track_a_waiting_termination_decision.json")
_STAGE128_TRACK_A_TERMINATION_BOUNDARY_REL = (
    f"{_STAGE128_TRACK_A_TERMINATION_PKG}/"
    "stage128_m3i2_track_a_waiting_termination_governance_boundary.json")
_STAGE128_TRACK_A_TERMINATION_HUMAN_DECISION_REL = (
    f"{_STAGE128_TRACK_A_TERMINATION_PKG}/"
    "stage128_m3i2_track_a_waiting_termination_human_decision_record.json")
#: The exact decision text this recording is genuinely hashing — recomputed
#: below, never trusted from the artifact alone.
_STAGE128_TRACK_A_TERMINATION_TEXT = (
    "As of 2026-08-08, no response resolving the point-in-time availability "
    "question had been obtained, and the human researcher elected to "
    "terminate the waiting period and adjudicate the M3-LAG-WDI evidence "
    "using the currently available evidence.")
_STAGE128_TRACK_A_TERMINATION_TEXT_SHA256 = (
    "ddfd7f094adc910597fdc49cea8ae39bc6c487cf6611978c353f2f802ae70811")
#: The step-E result this decision preserves exactly. Read once here, at
#: module import, purely as an audit constant to compare against — it is
#: still the committed artifact under
#: ``_STAGE128_M3_LAG_EVAL_DECISION_REL`` that is re-read and re-validated
#: inside the deriver below; this is not a substitute for that read.
_STAGE128_TRACK_A_TERMINATION_STEP_E_E1_CONCLUSION = (
    "E1_NULL_NO_DETECTABLE_INCREMENTAL_CONTRIBUTION")
_STAGE128_TRACK_A_TERMINATION_ORIGINAL_WAITING_COMPLETION_DATE = "2026-08-20"
_STAGE128_TRACK_A_TERMINATION_DATE = "2026-08-08"


def derive_stage128_m3i2_track_a_waiting_termination_markers(
        root: str) -> dict:
    """Recognize the human decision that ends Track A's wait and freezes M3.

    This is a DECISION RECORDING, not an "authorize one action" grant: no
    network request, model fit, Data Gate, or Final Test read needed
    authorizing, so nothing here carries ``authorization_consumed`` /
    ``authorized_now`` standing-permission fields. It is fail-closed on the
    one thing decision recordings can silently get wrong: overclaiming.

    In particular it refuses to publish anything as true that the decision
    text does not say. The World Bank is never recorded as "will not
    respond" — only that no substantive response had been obtained as of
    the decision date. It refuses to publish the M3-LAG-WDI step E result as
    modified, refuses to publish any further Track A or Track B action as
    authorized, and refuses to publish M3-LAG-WDI as promoted into the
    confirmatory family. A future unsolicited World Bank response is
    recorded as requiring its own new explicit human decision before it may
    be used for anything.

    Returns {} before the package exists, so pre-decision Handoffs are
    unaffected.
    """
    path = os.path.join(root, _STAGE128_TRACK_A_TERMINATION_DECISION_REL)
    if not os.path.isfile(path):
        return {}
    decision = _require_json_artifact(
        root, _STAGE128_TRACK_A_TERMINATION_DECISION_REL)
    boundary = _require_json_artifact(
        root, _STAGE128_TRACK_A_TERMINATION_BOUNDARY_REL)
    human_decision = _require_json_artifact(
        root, _STAGE128_TRACK_A_TERMINATION_HUMAN_DECISION_REL)

    for record, label in ((decision, "decision"), (boundary, "boundary"),
                          (human_decision, "human decision record")):
        if record.get("action_id") != _STAGE128_TRACK_A_TERMINATION_ACTION_ID:
            raise HandoffError(
                f"Track A waiting-termination {label} action_id mismatch")

    # --- the decision text is genuinely hashed, never trusted verbatim ---- #
    text = human_decision.get("human_decision_text") or ""
    if text != _STAGE128_TRACK_A_TERMINATION_TEXT:
        raise HandoffError(
            "the recorded Track A waiting-termination decision text does "
            "not match the pinned decision text")
    if len(text.encode("utf-8")) != human_decision.get(
            "human_decision_text_utf8_bytes"):
        raise HandoffError(
            "the Track A waiting-termination decision byte length must "
            "match its text")
    recomputed = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if recomputed != _STAGE128_TRACK_A_TERMINATION_TEXT_SHA256:
        raise HandoffError(
            "the pinned Track A waiting-termination decision hash does not "
            "match the recomputed hash of the pinned text")
    if human_decision.get("human_decision_text_sha256") != recomputed:
        raise HandoffError(
            "the recorded Track A waiting-termination decision hash field "
            "does not match its own text")
    for field, expected in (
        ("standing_authorization", False),
        ("one_time_action_authorization_grant", False),
        ("authorizes_any_future_action", False),
        ("authorizes_world_bank_followup", False),
        ("authorizes_wdi_retrieval", False),
        ("authorizes_repeated_requests", False),
        ("authorizes_historical_release_date_inference_or_backfill", False),
        ("authorizes_m3_lag_wdi_promotion_to_confirmatory", False),
        ("authorizes_m4", False),
        ("authorizes_final_test_access", False),
        ("authorizes_merge", False),
        ("scope_identified_by_hash_alone", False),
        ("next_action_requires_new_explicit_human_decision", True),
    ):
        if human_decision.get(field) is not expected:
            raise HandoffError(
                f"Track A waiting-termination human decision record {field} "
                f"must be {expected}")

    # --- overclaim refusal: the World Bank is never "will not respond" ---- #
    if decision.get("world_bank_will_not_respond_claim_made") is not False:
        raise HandoffError(
            "this decision may never claim the World Bank will not respond")
    if decision.get("world_bank_non_response_asserted_as_proven_fact") is not (
            False):
        raise HandoffError(
            "World Bank non-response may never be asserted as proven fact")
    if decision.get("world_bank_response_characterization") != (
            "AS_OF_2026_08_08_NO_RESPONSE_RESOLVING_THE_POINT_IN_TIME_"
            "AVAILABILITY_QUESTION_HAD_BEEN_OBTAINED"):
        raise HandoffError(
            "the World Bank response characterization must state exactly "
            "what is true: no response had been obtained as of the "
            "decision date, nothing stronger")

    # --- waiting period: terminated early, history preserved -------------- #
    if decision.get("waiting_period_original_completion_date") != (
            _STAGE128_TRACK_A_TERMINATION_ORIGINAL_WAITING_COMPLETION_DATE):
        raise HandoffError(
            "the original waiting-period completion date "
            f"{_STAGE128_TRACK_A_TERMINATION_ORIGINAL_WAITING_COMPLETION_DATE} "
            "must be preserved as history")
    if decision.get("waiting_period_original_completion_date_preserved_as_"
                     "history") is not True:
        raise HandoffError(
            "the original waiting-period completion date must be preserved, "
            "not deleted, even though it is no longer an active blocker")
    if decision.get("waiting_period_termination_date") != (
            _STAGE128_TRACK_A_TERMINATION_DATE):
        raise HandoffError(
            "the waiting-period termination date must be "
            f"{_STAGE128_TRACK_A_TERMINATION_DATE}")
    for field, expected in (
        ("waiting_period_was_active", True),
        ("waiting_period_terminated_early", True),
    ):
        if decision.get(field) is not expected:
            raise HandoffError(
                f"Track A waiting-termination decision {field} must be "
                f"{expected}")
    if decision.get("waiting_period_status") != (
            "VOLUNTARILY_TERMINATED_BY_EXPLICIT_HUMAN_DECISION"):
        raise HandoffError(
            "the waiting-period status must record a voluntary termination "
            "by explicit human decision, never an inferred World Bank "
            "silence")

    # --- no further Track A action, no inference, no backfill ------------- #
    for field in (
        "further_world_bank_followup_authorized",
        "further_world_bank_followup_requested",
        "further_wdi_api_retrieval_authorized",
        "further_wdi_archive_retrieval_authorized",
        "repeated_requests_authorized",
        "historical_release_date_inference_attempted",
        "historical_release_date_backfill_attempted",
        "historical_release_date_manufacture_attempted",
        "point_in_time_wdi_availability_resolved_by_this_decision",
        "unsolicited_future_world_bank_response_auto_reopens_m3",
        "unsolicited_future_world_bank_response_auto_reruns_m3",
        "m3_lag_wdi_promoted_to_confirmatory_model",
        "m3_lag_wdi_promotion_to_confirmatory_model_authorized",
        "m3_lag_wdi_step_e_artifacts_modified_by_this_decision",
        "confirmatory_holm_family_changed_by_this_decision",
        "confirmatory_holm_family_executed_by_this_decision",
        "confirmatory_holm_state_modified_by_this_decision",
        "m4_authorized", "m4_started", "final_test_access_authorized",
        "paper_winner_selected", "merge_authorized",
        "next_research_action_authorized", "track_b_next_action_authorized",
    ):
        if decision.get(field) is not False:
            raise HandoffError(
                f"Track A waiting-termination decision {field} must be "
                "False")
    for field, expected in (
        ("using_a_future_unsolicited_response_requires_new_explicit_human_"
         "decision", True),
        ("final_test_locked", True),
        ("m3_lag_wdi_step_e_result_preserved_exactly", True),
        ("next_action_pointer_is_not_authorization", True),
    ):
        if decision.get(field) is not expected:
            raise HandoffError(
                f"Track A waiting-termination decision {field} must be "
                f"{expected}")
    if decision.get("final_test_rows_read") != 0:
        raise HandoffError(
            "Track A waiting-termination decision must read 0 Final Test "
            "rows")
    if decision.get("point_in_time_wdi_availability_status") != (
            "UNVERIFIED_WITH_CURRENTLY_AVAILABLE_EVIDENCE"):
        raise HandoffError(
            "point-in-time WDI availability must remain UNVERIFIED")
    if decision.get("point_in_time_wdi_availability_treated_as") != (
            "EVIDENCE_LIMITATION_NOT_A_BLOCKING_TASK"):
        raise HandoffError(
            "the unverified point-in-time availability must be treated as "
            "an evidence limitation, not a blocking task")

    # --- M3-LAG-WDI final disposition: supplementary/exploratory only ----- #
    if decision.get("m3_lag_wdi_final_research_disposition") != (
            "SUPPLEMENTARY_EXPLORATORY_ONLY"):
        raise HandoffError(
            "the M3-LAG-WDI final research disposition must be "
            "SUPPLEMENTARY_EXPLORATORY_ONLY")
    if decision.get("m3_lag_wdi_scientific_role") != (
            _STAGE128_M3_LAG_ROLE):
        raise HandoffError(
            f"the M3-LAG-WDI scientific role must stay {_STAGE128_M3_LAG_ROLE}")
    if decision.get("m3_lag_wdi_in_confirmatory_holm_family") is not False:
        raise HandoffError(
            "M3-LAG-WDI must stay outside the confirmatory Holm family")
    if list(decision.get("confirmatory_holm_family") or []) != list(
            _STAGE128_M3_LAG_CONFIRMATORY_FAMILY):
        raise HandoffError(
            "the confirmatory Holm family membership changed at this "
            "decision")

    # --- step E is cross-checked, not merely trusted ----------------------- #
    if not _stage128_m3_lag_modeling_started(root):
        raise HandoffError(
            "step E must have already executed before this decision can "
            "preserve its result")
    step_e_decision = _require_json_artifact(
        root, _STAGE128_M3_LAG_EVAL_DECISION_REL)
    if step_e_decision.get("e1_conclusion") != (
            _STAGE128_TRACK_A_TERMINATION_STEP_E_E1_CONCLUSION):
        raise HandoffError(
            "the step E result on disk no longer matches the result this "
            "decision claims to preserve exactly — step E artifacts must "
            "never be touched by this action")
    if decision.get("m3_lag_wdi_step_e_e1_conclusion") != (
            step_e_decision.get("e1_conclusion")):
        raise HandoffError(
            "the decision's own copy of the step E conclusion disagrees "
            "with the step E artifact it claims to preserve")

    # --- execution audit: zero everything ---------------------------------- #
    for field in (
        "world_bank_requests", "world_bank_followup_sent",
        "world_bank_new_inquiry_submitted", "wdi_api_requests",
        "wdi_archive_downloads", "wdi_archive_redownloads",
        "network_requests", "coverage_calculations",
        "feature_materializations", "data_gate_executions", "model_fits",
        "predictions", "predictive_metrics", "bootstrap_executions",
        "holm_executions", "shap_executions", "final_test_rows_read",
        "final_test_predictor_values_read", "final_test_target_values_read",
    ):
        if boundary.get(field) != 0:
            raise HandoffError(
                f"Track A waiting-termination boundary {field} must be 0")
    for field, expected in (
        ("gmail_or_personal_account_accessed", False),
        ("new_documentary_search_executed", False),
        ("resubmission_executed", False),
        ("response_ingestion_executed", False),
        ("response_adjudication_executed", False),
        ("release_date_inference_executed", False),
        ("release_date_backfill_executed", False),
        ("calendar_mapping_lock_rerun", False),
        ("step_c_artifacts_modified", False),
        ("step_d_artifacts_modified", False),
        ("step_e_artifacts_modified", False),
        ("m3_lag_wdi_contract_edited_by_this_action", False),
        ("m3_lag_wdi_gate_thresholds_modified_by_this_action", False),
        ("m3i2_evidence_capture_artifacts_modified", False),
        ("m3i2_documentary_recovery_artifacts_modified", False),
        ("m3i2_inquiry_submission_artifacts_modified", False),
        ("confirmatory_holm_family_modified", False),
        ("confirmatory_holm_family_changed", False),
        ("confirmatory_holm_executed", False),
        ("paper_winner_selected", False),
        ("m3_lag_wdi_promoted_to_confirmatory", False),
        ("final_test_access_authorized", False),
        ("m4_authorized", False), ("m4_started", False),
        ("next_research_action_authorized", False),
        ("track_b_next_action_authorized", False),
        ("ready_for_review_authorized", False),
        ("merge_authorized", False), ("auto_merge", False),
        ("pii_committed_to_git", False),
        ("credentials_committed_to_git", False),
        ("prior_stage128_m3_lag_wdi_artifacts_modified_by_this_action",
         False),
        ("prior_stage128_m3i2_artifacts_modified_by_this_action", False),
        ("final_test_locked", True),
    ):
        if boundary.get(field) is not expected:
            raise HandoffError(
                f"Track A waiting-termination boundary {field} must be "
                f"{expected}")

    return {
        "stage128_track_a_waiting_termination_recorded": True,
        "stage128_track_a_waiting_termination_action_id":
            _STAGE128_TRACK_A_TERMINATION_ACTION_ID,
        "stage128_track_a_waiting_termination_date":
            _STAGE128_TRACK_A_TERMINATION_DATE,
        "stage128_track_a_waiting_period_status":
            "VOLUNTARILY_TERMINATED_BY_EXPLICIT_HUMAN_DECISION",
        "stage128_track_a_waiting_period_original_completion_date":
            _STAGE128_TRACK_A_TERMINATION_ORIGINAL_WAITING_COMPLETION_DATE,
        "stage128_track_a_world_bank_response_characterization":
            decision.get("world_bank_response_characterization"),
        "stage128_track_a_world_bank_will_not_respond_claim_made": False,
        "stage128_track_a_further_followup_authorized": False,
        "stage128_track_a_further_wdi_retrieval_authorized": False,
        "stage128_track_a_release_date_inference_or_backfill_authorized":
            False,
        "stage128_m3_lag_wdi_point_in_time_availability_status":
            "UNVERIFIED_WITH_CURRENTLY_AVAILABLE_EVIDENCE",
        "stage128_m3_lag_wdi_point_in_time_availability_treated_as":
            "EVIDENCE_LIMITATION_NOT_A_BLOCKING_TASK",
        "stage128_m3_lag_wdi_final_research_disposition":
            "SUPPLEMENTARY_EXPLORATORY_ONLY",
        "stage128_m3_lag_wdi_promoted_to_confirmatory_model": False,
        "stage128_m3_lag_wdi_unsolicited_future_response_auto_reopens":
            False,
        "stage128_m3_lag_wdi_future_response_requires_new_human_decision":
            True,
        "stage128_track_a_termination_human_decision_text_sha256":
            _STAGE128_TRACK_A_TERMINATION_TEXT_SHA256,
        "stage128_track_a_termination_human_decision_text_utf8_bytes":
            human_decision.get("human_decision_text_utf8_bytes"),
        # The human-submission action's `stage128_m3i2_inquiry_waiting_
        # period_status` field is left untouched (it is the historically
        # accurate value that action itself asserted), but a consumer of
        # that key alone would see a stale "ACTIVE" with no signal that a
        # later action superseded it. This key is that signal.
        "stage128_m3i2_inquiry_waiting_period_status_is_historical_"
        "superseded_by_termination": True,
        # Both pointer chains now converge on the same human decision point.
        "last_completed_research_action_id":
            _STAGE128_TRACK_A_TERMINATION_ACTION_ID,
        # Hyphenated to match the `stage128-...` action-id convention: this
        # is the value published in ROADMAP.md's front matter
        # `next_research_action_id`, which the validator requires to be a
        # real, listed item id (item 25n) — not the underscored status-value
        # convention used by scope/enum fields such as
        # `stage128_m3_lag_wdi_next_action_id` below.
        "next_research_action_id": "human-decision-required",
        "next_research_action_scope": "no_further_action_is_authorized",
        "next_research_action_authorized": False,
        "next_research_action_pointer_is_not_authorization": True,
        "stage128_m3_lag_wdi_next_action_id": "human_decision_required",
        "stage128_m3_lag_wdi_next_action_authorized": False,
        "stage128_m3_lag_wdi_next_action_scope":
            "no_further_action_is_authorized",
        "m4_authorized": False,
        "final_test_locked": True,
        "merge_authorized": False,
        "paper_winner_selected": False,
    }


# --------------------------------------------------------------------------- #
# Stage129 -- M4 governance Data-Gate contract lock (design only)
# --------------------------------------------------------------------------- #

_STAGE129_M4_PKG = "project/stage129/m4_governance_data_gate_contract"
_STAGE129_M4_ACTION_ID = "stage129-m4-governance-data-gate-contract-lock"
_STAGE129_M4_CONTRACT_REL = (
    f"{_STAGE129_M4_PKG}/stage129_m4_data_gate_contract.json")
_STAGE129_M4_BOUNDARY_REL = (
    f"{_STAGE129_M4_PKG}/stage129_m4_data_gate_governance_boundary.json")
_STAGE129_M4_AUDIT_REL = (
    f"{_STAGE129_M4_PKG}/stage129_m4_data_gate_execution_audit.json")

_STAGE129_M4_CONTRACT_STATUS = "PROSPECTIVELY_LOCKED_PRE_RETRIEVAL"
_STAGE129_M4_CANDIDATE_SET = (
    "audit_opinion_type", "going_concern_flag", "audit_lag_days",
    "board_size",
)
#: This is a THIRD, independent pointer. It is distinct from both the Track A
#: pointer (`next_research_action_id`) and the Track B pointer
#: (`stage128_m3_lag_wdi_next_action_id`), neither of which this additive,
#: design-only action may advance -- the contract itself says so
#: (`m3_comparator_boundary.confirmatory_chain_redefined_by_this_action` is
#: false and ROADMAP.md records both live pointers as unchanged by this item).
_STAGE129_M4_NEXT_ACTION_ID = "stage129-m4-governance-data-gate"
#: The two candidates whose mandatory preregistered semantic definitions are
#: unresolved CONTRACT ISSUES. Their candidate IDENTITY is frozen (they stay
#: M4 candidates and are never substituted); what is not frozen is the
#: taxonomy / date-conversion definition each needs before the Gate can run.
_STAGE129_M4_BLOCKED_CANDIDATES = ("audit_opinion_type", "audit_lag_days")


def derive_stage129_m4_governance_data_gate_contract_lock_markers(
        root: str) -> dict:
    """Recognize the prospective, pre-retrieval M4 governance Data-Gate lock.

    Narrow and fail-closed, mirroring the M3I-2 / M3-LAG-WDI contract-lock
    recognition pattern. The lock is a CONTRACT event only: it retrieves no
    M4 observation, executes no Data Gate, fits no model and never touches
    the Final Test. Two of the four candidate semantic definitions
    (`audit_opinion_type`'s category taxonomy and `audit_lag_days`'s
    calendar-conversion convention) are explicit, unresolved CONTRACT ISSUES
    -- this function surfaces that status rather than letting it silently
    read as a frozen, gate-ready definition. Returns {} before the contract
    package exists, so pre-lock Handoffs are unaffected. Raises on a
    present-but-corrupt or internally inconsistent package (fail-closed).
    """
    path = os.path.join(root, _STAGE129_M4_CONTRACT_REL)
    if not os.path.isfile(path):
        return {}
    try:
        contract = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(
            f"unreadable Stage129 M4 contract-lock artifact: {exc}"
        ) from exc

    if contract.get("action_id") != _STAGE129_M4_ACTION_ID:
        raise HandoffError("Stage129 M4 contract-lock action_id mismatch")
    for field, expected in (
        ("locked_before_any_value_level_work", True),
        ("authorizes_retrieval", False),
        ("authorizes_gate_execution", False),
        ("authorizes_modeling", False),
        ("is_the_gate_itself", False),
        ("is_confirmatory_m4_admission", False),
    ):
        if contract.get(field) is not expected:
            raise HandoffError(
                f"Stage129 M4 contract-lock {field} must be {expected}")

    candidates = contract.get("candidate_set") or {}
    if tuple(candidates.get("candidates") or ()) != _STAGE129_M4_CANDIDATE_SET:
        raise HandoffError(
            "Stage129 M4 candidate set must be exactly "
            f"{_STAGE129_M4_CANDIDATE_SET} in order, no substitution")
    for field, expected in (
        ("candidate_count", 4),
        ("candidate_count_is_exact", True),
        ("no_feature_shopping", True),
        ("candidate_order_is_frozen", True),
        ("failed_candidate_may_be_replaced_to_preserve_count", False),
    ):
        if candidates.get(field) != expected:
            raise HandoffError(
                f"Stage129 M4 candidate_set.{field} must be {expected!r}")

    semantic = contract.get("semantic_definitions") or {}
    opinion = semantic.get("audit_opinion_type") or {}
    if opinion.get("categories_derived_from_empirical_data_forbidden") is not (
            True):
        raise HandoffError(
            "Stage129 M4 audit_opinion_type must forbid deriving categories "
            "from empirical data")
    if opinion.get("taxonomy_status") != "CONTRACT_ISSUE_UNRESOLVED":
        raise HandoffError(
            "Stage129 M4 audit_opinion_type taxonomy must be published as "
            "CONTRACT_ISSUE_UNRESOLVED, not a frozen enum")
    # An unresolved taxonomy may never simultaneously read as frozen, admit
    # modeled categorical values, or leave the Gate executable for this
    # candidate. Flipping any of these to a "resolved" reading without an
    # authoritative taxonomy is exactly the silent overstatement this
    # recognizer exists to prevent.
    for field, expected in (
        ("candidate_identity_frozen", True),
        ("taxonomy_frozen", False),
        ("modeled_categorical_values_admitted", False),
        ("gate_may_execute_for_this_candidate", False),
    ):
        if opinion.get(field) is not expected:
            raise HandoffError(
                f"Stage129 M4 audit_opinion_type.{field} must be {expected} "
                "while the taxonomy is CONTRACT_ISSUE_UNRESOLVED")
    candidate_taxonomy = opinion.get(
        "candidate_taxonomy_documented_not_verified") or {}
    if candidate_taxonomy.get("must_not_be_treated_as_frozen") is not True:
        raise HandoffError(
            "Stage129 M4 audit_opinion_type candidate taxonomy must be "
            "marked must_not_be_treated_as_frozen")
    if candidate_taxonomy.get("source_authority") != "secondary_not_authoritative":
        raise HandoffError(
            "Stage129 M4 audit_opinion_type candidate taxonomy source "
            "authority must be recorded as secondary_not_authoritative")

    audit_lag = semantic.get("audit_lag_days") or {}
    if audit_lag.get("calendar_conversion_status") != (
            "CONTRACT_ISSUE_UNRESOLVED"):
        raise HandoffError(
            "Stage129 M4 audit_lag_days calendar conversion must be "
            "published as CONTRACT_ISSUE_UNRESOLVED")
    for field, expected in (
        ("candidate_identity_frozen", True),
        ("calendar_conversion_frozen", False),
        ("value_may_be_calculated", False),
        ("jalali_fiscal_year_t_plus_621_permitted_as_daily_date_conversion",
         False),
        ("gate_may_execute_for_this_candidate", False),
    ):
        if audit_lag.get(field) is not expected:
            raise HandoffError(
                f"Stage129 M4 audit_lag_days.{field} must be {expected} while "
                "the calendar conversion is CONTRACT_ISSUE_UNRESOLVED")
    conversion_text = str(audit_lag.get("calendar_conversion_convention", ""))
    if "jalali_fiscal_year_t_plus_621" not in conversion_text:
        raise HandoffError(
            "Stage129 M4 audit_lag_days calendar_conversion_convention must "
            "explicitly address the M3-LAG-WDI +621 rule")
    if "NOT applicable" not in conversion_text and "NOT be reused" not in (
            conversion_text) and "not applicable" not in conversion_text:
        raise HandoffError(
            "Stage129 M4 audit_lag_days calendar_conversion_convention must "
            "explicitly state the +621 year-mapping rule is not applicable "
            "to this day-level date difference")

    join_rule = contract.get("join_identity_rule") or {}
    required_identifier = join_rule.get("required_identifier")
    if not isinstance(required_identifier, dict):
        raise HandoffError(
            "Stage129 M4 join_identity_rule.required_identifier must be a "
            "concrete frozen field mapping, not an open-ended description")
    if required_identifier.get("company_key") != "ticker" or (
            required_identifier.get("fiscal_year_key") != "fiscal_year_t"):
        raise HandoffError(
            "Stage129 M4 join_identity_rule must freeze the already-audited "
            "ticker / fiscal_year_t join keys")
    # The audited join evidence is PARENT-SIDE only: it proves a one-to-one
    # join against a TSETMC-sourced child, not against CODAL-sourced company
    # filings. Prior use of the same parent keys is not evidence of
    # cross-source identity compatibility, so the CODAL-identity resolution
    # is its own unresolved, cross-cutting contract issue and may never be
    # published as settled.
    codal_identity = join_rule.get(
        "codal_to_parent_company_identity_resolution") or {}
    if codal_identity.get("status") != "CONTRACT_ISSUE_UNRESOLVED":
        raise HandoffError(
            "Stage129 M4 codal_to_parent_company_identity_resolution must be "
            "CONTRACT_ISSUE_UNRESOLVED: no audited CODAL-identity-to-ticker "
            "mapping exists in this repository")
    if codal_identity.get(
            "gate_may_execute_join_dimension_for_codal_sourced_values") is not (
            False):
        raise HandoffError(
            "Stage129 M4 Gate join dimension must not be executable for "
            "CODAL-sourced values while the identity mapping is unresolved")
    if required_identifier.get("fallback_mapping_permitted") is not False:
        raise HandoffError(
            "Stage129 M4 join identity must not permit a fallback mapping")
    if join_rule.get("ambiguous_identity_verdict") != "unresolved":
        raise HandoffError(
            "Stage129 M4 join_identity_rule.ambiguous_identity_verdict must "
            "remain 'unresolved'")
    for field in ("fuzzy_matching_at_gate_time_forbidden",
                  "accidental_many_to_many_forbidden",
                  "outcome_informed_manual_matching_forbidden",
                  "cross_year_carry_forward_forbidden_unless_explicitly_"
                  "preregistered"):
        if join_rule.get(field) is not True:
            raise HandoffError(f"Stage129 M4 join_identity_rule.{field} "
                                "must be True")

    thresholds = contract.get("thresholds") or {}
    canonical_sources = thresholds.get("canonical_sources") or {}
    fourth = canonical_sources.get(
        "minimum_positive_evaluable_per_locked_validation_fold") or {}
    if "stage128_m3_macro_data_gate_decision.json" not in str(
            fourth.get("found_in", "")):
        raise HandoffError(
            "Stage129 M4 minimum_positive_evaluable_per_locked_validation_"
            "fold threshold must cite its true source (Stage128 M3 macro "
            "Data Gate decision), not a blanket Stage125 Part4 claim")
    if thresholds.get("thresholds_changed_by_this_action") is not False:
        raise HandoffError(
            "Stage129 M4 thresholds must not be changed by this action")

    lock_state = contract.get("contract_lock_state") or {}
    if lock_state.get("m4_contract_status") != _STAGE129_M4_CONTRACT_STATUS:
        raise HandoffError(
            "Stage129 M4 contract_lock_state.m4_contract_status must be "
            f"{_STAGE129_M4_CONTRACT_STATUS}")
    for field, expected in (
        ("candidate_count", 4),
        ("m4_data_retrieval_started", False),
        ("m4_candidate_observations_read", 0),
        ("m4_data_gate_executed", False),
        ("m4_block_admitted", False),
        ("m4_modeling_started", False),
        ("m4_incremental_evaluation_authorized", False),
        ("next_action_pointer", _STAGE129_M4_NEXT_ACTION_ID),
        ("next_action_authorized", False),
        ("pointer_is_not_authorization", True),
        # Section A/B are complete; section D must never publish the whole
        # contract as complete or the Gate as executable while section C
        # holds unresolved prerequisite definitions.
        ("m4_candidate_identity_set_locked", True),
        ("m4_gate_policy_contract_recorded", True),
        ("m4_contract_complete", False),
        ("m4_contract_fully_executable", False),
        ("m4_contract_completion_status",
         "LOCKED_WITH_UNRESOLVED_PREREQUISITE_DEFINITIONS"),
        ("m4_data_gate_executable", False),
        ("m4_data_gate_authorized", False),
        ("m4_coverage_calculated", False),
    ):
        if lock_state.get(field) != expected:
            raise HandoffError(
                f"Stage129 M4 contract_lock_state.{field} must be "
                f"{expected!r}")
    if tuple(lock_state.get("candidate_set") or ()) != (
            _STAGE129_M4_CANDIDATE_SET):
        raise HandoffError(
            "Stage129 M4 contract_lock_state.candidate_set mismatch")

    # The blocked-candidate list, the per-candidate semantic statuses and the
    # section C entries must agree. A package that drops a candidate from one
    # surface while leaving it unresolved on another is inconsistent and must
    # fail closed rather than publish a partially-resolved reading.
    blocked = tuple(lock_state.get(
        "m4_candidates_blocked_by_unresolved_definitions") or ())
    if blocked != _STAGE129_M4_BLOCKED_CANDIDATES:
        raise HandoffError(
            "Stage129 M4 contract_lock_state."
            "m4_candidates_blocked_by_unresolved_definitions must be "
            f"{list(_STAGE129_M4_BLOCKED_CANDIDATES)} while both semantic "
            "definitions remain CONTRACT_ISSUE_UNRESOLVED")
    ready = tuple(lock_state.get(
        "m4_candidates_with_gate_ready_semantic_definitions") or ())
    if sorted(ready) + sorted(blocked) and set(ready) & set(blocked):
        raise HandoffError(
            "Stage129 M4 gate-ready and blocked candidate lists overlap")
    if sorted(list(ready) + list(blocked)) != sorted(
            _STAGE129_M4_CANDIDATE_SET):
        raise HandoffError(
            "Stage129 M4 gate-ready + blocked candidates must together be "
            "exactly the four locked candidates")
    cross_cutting = lock_state.get(
        "unresolved_cross_cutting_prerequisites") or []
    if not any(entry.get("issue") == (
            "codal_to_parent_company_identity_resolution")
            and entry.get("status") == "CONTRACT_ISSUE_UNRESOLVED"
            for entry in cross_cutting):
        raise HandoffError(
            "Stage129 M4 contract_lock_state must record the unresolved, "
            "cross-cutting codal_to_parent_company_identity_resolution issue")
    if lock_state.get("m4_candidates_the_gate_may_execute_for") != []:
        raise HandoffError(
            "Stage129 M4 Gate may not be executable for any candidate while "
            "the cross-cutting CODAL identity issue is unresolved")
    unresolved_entries = lock_state.get(
        "unresolved_prerequisite_definitions") or []
    if tuple(e.get("candidate") for e in unresolved_entries) != (
            _STAGE129_M4_BLOCKED_CANDIDATES):
        raise HandoffError(
            "Stage129 M4 unresolved_prerequisite_definitions must list "
            f"exactly {list(_STAGE129_M4_BLOCKED_CANDIDATES)}")
    for entry in unresolved_entries:
        if entry.get("status") != "CONTRACT_ISSUE_UNRESOLVED":
            raise HandoffError(
                f"Stage129 M4 unresolved prerequisite for "
                f"{entry.get('candidate')!r} must carry status "
                "CONTRACT_ISSUE_UNRESOLVED")
        if entry.get("candidate_identity_frozen") is not True:
            raise HandoffError(
                f"Stage129 M4 unresolved prerequisite for "
                f"{entry.get('candidate')!r} must still record the candidate "
                "identity as frozen")
        if entry.get("gate_may_execute_for_this_candidate") is not False:
            raise HandoffError(
                f"Stage129 M4 Gate must not be executable for "
                f"{entry.get('candidate')!r} while its definition is "
                "unresolved")
    auth = lock_state.get("contract_lock_authorization") or {}
    for field, expected in (
        ("was_authorized", True),
        ("authorized_now", False),
        ("authorization_consumed", True),
        ("authorization_reusable", False),
    ):
        if auth.get(field) is not expected:
            raise HandoffError(
                f"Stage129 M4 contract_lock_authorization.{field} must be "
                f"{expected}")

    firewall = contract.get("final_test_firewall") or {}
    if firewall.get("final_test_locked") is not True or firewall.get(
            "final_test_rows_read") != 0:
        raise HandoffError(
            "Stage129 M4 final_test_firewall must show locked=True and "
            "rows_read=0")

    comparator = contract.get("m3_comparator_boundary") or {}
    if comparator.get("m3_cbi_status_preserved") != "UNRESOLVED_M3_DATA_GATE":
        raise HandoffError(
            "Stage129 M4 contract must preserve M3-CBI as "
            "UNRESOLVED_M3_DATA_GATE")
    if comparator.get("m3_lag_wdi_disposition_preserved") != (
            "SUPPLEMENTARY_EXPLORATORY_ONLY"):
        raise HandoffError(
            "Stage129 M4 contract must preserve the M3-LAG-WDI disposition "
            "as SUPPLEMENTARY_EXPLORATORY_ONLY")
    holm_family = tuple(comparator.get("confirmatory_holm_family") or ())
    if holm_family != ("M2_minus_M1", "M3_CBI_minus_M2", "M4_minus_M3_CBI"):
        raise HandoffError(
            "Stage129 M4 contract must preserve the confirmatory Holm "
            "family unchanged")
    if comparator.get("confirmatory_holm_family_executed") is not False or (
            comparator.get("confirmatory_holm_family_changed_by_this_action")
            is not False):
        raise HandoffError(
            "Stage129 M4 contract must record the confirmatory Holm family "
            "as unexecuted and unchanged")

    # The governance boundary and execution audit are required companions,
    # not optional -- a contract-lock claim unsupported by either is a
    # corrupt/incomplete package and must fail closed, never silently pass.
    boundary = _require_json_artifact(root, _STAGE129_M4_BOUNDARY_REL)
    for field, expected in (
        ("m4_authorized", False), ("m4_started", False),
        ("m4_data_collected", False), ("m4_data_gate_executed", False),
        ("m4_block_admitted", False),
        ("m4_incremental_evaluation_authorized", False),
        ("final_test_locked", True), ("final_test_access_authorized", False),
        ("merge_authorized", False), ("pr_is_draft", True),
        ("candidate_count", 4),
        ("candidate_count_can_change_without_new_human_authorization", False),
        ("institutional_ownership_admitted_as_m4_candidate", False),
        ("non_executive_ratio_admitted_as_m4_candidate", False),
        ("m3_lag_wdi_described_as_confirmatory", False),
        ("gate_pass_described_as_modeling_authorization", False),
        ("m2_retained_status_modified_by_this_action", False),
        ("m3_cbi_status_modified_by_this_action", False),
        ("m3_lag_wdi_disposition_modified_by_this_action", False),
        ("confirmatory_holm_family_modified_by_this_action", False),
        ("paper_winner_selected", False), ("final_model_selected", False),
        ("pointer_is_not_authorization", True),
    ):
        if boundary.get(field) is not expected:
            raise HandoffError(
                f"Stage129 M4 governance boundary {field} must be "
                f"{expected}")
    if boundary.get("final_test_rows_read") != 0:
        raise HandoffError(
            "Stage129 M4 governance boundary final_test_rows_read must be 0")
    if boundary.get("next_action_pointer") != _STAGE129_M4_NEXT_ACTION_ID:
        raise HandoffError(
            "Stage129 M4 governance boundary next_action_pointer mismatch")

    audit = _require_json_artifact(root, _STAGE129_M4_AUDIT_REL)
    for field, expected in (
        ("retrieval_started", False), ("data_gate_executed", False),
        ("modeling_started", False),
        ("external_data_source_accessed", False),
        ("scientific_computation_ran", False),
    ):
        if audit.get(field) is not expected:
            raise HandoffError(f"Stage129 M4 execution audit {field} must "
                                f"be {expected}")
    for field in ("final_test_rows_read", "final_test_predictor_values_read",
                  "final_test_target_values_read"):
        if audit.get(field) != 0:
            raise HandoffError(
                f"Stage129 M4 execution audit {field} must be 0")
    counters = audit.get("counters") or {}
    for field, value in counters.items():
        if value != 0:
            raise HandoffError(
                f"Stage129 M4 execution audit counters.{field} must be 0 "
                "(no M4 retrieval, coverage or modeling occurred)")

    return {
        # Namespaced (stage129_m4_*) detail, following the same convention
        # used for the other Stage128 contract-lock actions.
        "stage129_m4_contract_lock_executed": True,
        "stage129_m4_contract_status": _STAGE129_M4_CONTRACT_STATUS,
        "stage129_m4_candidate_count": 4,
        "stage129_m4_candidate_set": list(_STAGE129_M4_CANDIDATE_SET),
        "stage129_m4_contract_lock_was_authorized": True,
        "stage129_m4_contract_lock_authorized_now": False,
        "stage129_m4_contract_lock_authorization_consumed": True,
        "stage129_m4_contract_lock_authorization_reusable": False,
        # This is a THIRD pointer, deliberately NOT named
        # `next_research_action_id` or `stage128_m3_lag_wdi_next_action_id`:
        # this additive, design-only action does not own or advance either
        # of those two live pointer chains, both of which stay
        # `human-decision-required` / `human_decision_required` untouched.
        "stage129_m4_next_action_id": _STAGE129_M4_NEXT_ACTION_ID,
        # Immutable history: the pointer this lock published AT LOCK TIME.
        # A later action may supersede the live pointer above; it may not
        # rewrite what the lock itself published.
        "stage129_m4_contract_lock_pointer_at_lock_time":
            _STAGE129_M4_NEXT_ACTION_ID,
        "stage129_m4_next_action_authorized": False,
        "stage129_m4_next_action_pointer_is_not_authorization": True,
        "stage129_m4_audit_opinion_type_taxonomy_status":
            "CONTRACT_ISSUE_UNRESOLVED",
        "stage129_m4_audit_lag_days_calendar_conversion_status":
            "CONTRACT_ISSUE_UNRESOLVED",
        "stage129_m4_contract_issues_unresolved": [
            "audit_opinion_type_taxonomy",
            "audit_lag_days_calendar_conversion",
            "codal_to_parent_company_identity_resolution",
        ],
        "stage129_m4_codal_identity_resolution_status":
            "CONTRACT_ISSUE_UNRESOLVED",
        "stage129_m4_join_dimension_executable_for_codal_values": False,
        "stage129_m4_candidates_the_gate_may_execute_for": [],
        # Section A/B locked, section C unresolved, section D therefore
        # blocked. Publishing the status string alone would let a consumer
        # read "PROSPECTIVELY_LOCKED_PRE_RETRIEVAL" as "contract finished",
        # so completion and executability are published explicitly.
        "stage129_m4_candidate_identity_set_locked": True,
        "stage129_m4_gate_policy_contract_recorded": True,
        "stage129_m4_contract_complete": False,
        "stage129_m4_contract_fully_executable": False,
        "stage129_m4_contract_completion_status":
            "LOCKED_WITH_UNRESOLVED_PREREQUISITE_DEFINITIONS",
        "stage129_m4_data_gate_executable": False,
        "stage129_m4_data_gate_authorized": False,
        "stage129_m4_coverage_calculated": False,
        "stage129_m4_candidates_blocked_by_unresolved_definitions":
            list(_STAGE129_M4_BLOCKED_CANDIDATES),
        "stage129_m4_candidates_with_gate_ready_semantic_definitions":
            list(ready),
        "m4_contract_fully_executable": False,
        "m4_data_gate_executable": False,
        "m4_data_gate_authorized": False,
        "m4_coverage_calculated": False,
        "stage129_m4_join_identity_company_key": "ticker",
        "stage129_m4_join_identity_fiscal_year_key": "fiscal_year_t",
        "stage129_m4_join_identity_ambiguous_verdict": "unresolved",
        "stage129_m4_join_identity_source": required_identifier.get(
            "source"),
        "stage129_m4_threshold_canonical_sources": canonical_sources,
        "stage129_m4_m3_cbi_status_preserved": "UNRESOLVED_M3_DATA_GATE",
        "stage129_m4_m3_lag_wdi_disposition_preserved":
            "SUPPLEMENTARY_EXPLORATORY_ONLY",
        "stage129_m4_confirmatory_holm_family": list(holm_family),
        "stage129_m4_confirmatory_holm_family_executed": False,
        "stage129_m4_final_test_locked": True,
        "stage129_m4_final_test_rows_read": 0,
        # Flat/bare fields, matching the vocabulary already used by other
        # M4-adjacent state elsewhere in the Handoff (`m4_authorized`,
        # `m4_started`) and by the contract's own `contract_lock_state`
        # field names, so a consumer checking either surface sees the same
        # facts.
        "m4_authorized": False,
        "m4_started": False,
        "m4_data_retrieval_started": False,
        "m4_candidate_observations_read": 0,
        "m4_data_gate_executed": False,
        "m4_block_admitted": False,
        "m4_modeling_started": False,
        "m4_incremental_evaluation_authorized": False,
        "m4_pointer_is_not_authorization": True,
        "final_test_locked": True,
        "final_test_rows_read": 0,
    }


_STAGE129_M4_DISC_PKG = "project/stage129/m4_human_discontinuation_data_inadequacy"
_STAGE129_M4_DISC_ACTION_ID = "stage129-m4-human-discontinuation-data-inadequacy"
_STAGE129_M4_DISC_DECISION_REL = (
    f"{_STAGE129_M4_DISC_PKG}/stage129_m4_human_discontinuation_decision.json")
_STAGE129_M4_DISC_BOUNDARY_REL = (
    f"{_STAGE129_M4_DISC_PKG}/"
    "stage129_m4_human_discontinuation_governance_boundary.json")
_STAGE129_M4_DISC_STATUS = "M4_DISCONTINUED_BY_HUMAN_DECISION_DATA_INADEQUACY"
#: Deliberately NOT the M4 Data Gate. The block is stopped, so the M4 pointer
#: may not keep naming an M4 execution step.
_STAGE129_M4_DISC_NEXT_ACTION_ID = "human_decision_required"
_STAGE129_M4_DISC_NEXT_ACTION_SCOPE = (
    "m4_discontinued_no_further_m4_action_is_authorized")
#: Formal Gate verdict vocabulary. None of these may be published by a decision
#: that never executed the Gate.
_STAGE129_M4_GATE_VERDICT_VOCAB = (
    "PASS_M4_DATA_GATE", "FAIL_M4_DATA_GATE", "UNRESOLVED_M4_DATA_GATE")


def derive_stage129_m4_human_discontinuation_markers(root: str) -> dict:
    """Recognize the human decision to discontinue the M4 block.

    Narrow and fail-closed, mirroring the contract-lock recognition pattern.
    This is a DECISION event only: it retrieves no M4 observation, computes no
    formal Gate coverage, materializes no feature, fits no model and never
    touches the Final Test.

    The decision is emphatically NOT a formal Gate verdict -- the Gate was never
    executed -- so this function refuses to publish any Gate-verdict vocabulary
    and fails closed if the artifacts try to. Returns {} before the package
    exists, so pre-decision Handoffs are unaffected.
    """
    path = os.path.join(root, _STAGE129_M4_DISC_DECISION_REL)
    if not os.path.isfile(path):
        return {}
    decision = _require_json_artifact(root, _STAGE129_M4_DISC_DECISION_REL)
    boundary = _require_json_artifact(root, _STAGE129_M4_DISC_BOUNDARY_REL)

    if decision.get("decision_id") != _STAGE129_M4_DISC_ACTION_ID:
        raise HandoffError("Stage129 M4 discontinuation decision_id mismatch")
    if boundary.get("action_id") != _STAGE129_M4_DISC_ACTION_ID:
        raise HandoffError("Stage129 M4 discontinuation boundary action_id mismatch")
    if decision.get("decision_type") != "human_scientific_decision":
        raise HandoffError(
            "Stage129 M4 discontinuation must be a human_scientific_decision")
    if decision.get("decision_status") != _STAGE129_M4_DISC_STATUS:
        raise HandoffError(
            f"Stage129 M4 discontinuation status must be {_STAGE129_M4_DISC_STATUS}")
    if boundary.get("m4_block_disposition") != _STAGE129_M4_DISC_STATUS:
        raise HandoffError(
            "Stage129 M4 discontinuation boundary disposition must match the decision")
    if decision.get("authorized_by_human") is not True:
        raise HandoffError("Stage129 M4 discontinuation must be human-authorized")

    # The decision must not masquerade as a Gate verdict.
    if decision.get("formal_m4_data_gate_executed") is not False:
        raise HandoffError(
            "Stage129 M4 discontinuation may not report an executed formal Gate")
    if decision.get("formal_m4_gate_verdict") is not None:
        raise HandoffError(
            "Stage129 M4 discontinuation formal_m4_gate_verdict must be null")
    if decision.get("observational_coverage_is_not_formal_gate_coverage") is not True:
        raise HandoffError(
            "Stage129 M4 discontinuation must distinguish observational coverage "
            "from formal Gate coverage")
    if _STAGE129_M4_DISC_STATUS in _STAGE129_M4_GATE_VERDICT_VOCAB:
        raise HandoffError(
            "Stage129 M4 discontinuation status must not be Gate-verdict vocabulary")
    for field in ("m4_block_disposition", "m4_comparison_status"):
        if boundary.get(field) in _STAGE129_M4_GATE_VERDICT_VOCAB:
            raise HandoffError(
                f"Stage129 M4 discontinuation {field} must not be a Gate verdict")

    # Nothing downstream of the decision may be authorized by it.
    for field in ("m4_retrieval_to_continue", "m4_manual_completion_to_continue",
                  "m4_feature_materialization_authorized", "m4_modeling_authorized",
                  "m4_incremental_evaluation_authorized", "reopening_authorized_now",
                  "outcome_or_final_test_observation_used_for_this_decision",
                  "reason_is_poor_model_result", "reason_is_outcome_inspection"):
        if decision.get(field) is not False:
            raise HandoffError(
                f"Stage129 M4 discontinuation decision {field} must be False")
    if decision.get("reopening_requires_new_explicit_human_authorization") is not True:
        raise HandoffError(
            "Stage129 M4 discontinuation must require new human authorization to reopen")

    # The four frozen candidates survive the decision unchanged.
    if tuple(decision.get("m4_candidate_set") or ()) != _STAGE129_M4_CANDIDATE_SET:
        raise HandoffError(
            "Stage129 M4 discontinuation must preserve the four frozen candidates "
            f"exactly as {_STAGE129_M4_CANDIDATE_SET}")
    if decision.get("m4_candidate_count") != 4:
        raise HandoffError("Stage129 M4 discontinuation must preserve candidate_count 4")
    for field in ("m4_candidate_count_changed_by_this_decision",
                  "m4_candidates_removed_or_renamed_by_this_decision",
                  "m4_candidates_substituted_by_this_decision"):
        if decision.get(field) is not False:
            raise HandoffError(f"Stage129 M4 discontinuation {field} must be False")

    # Prior blocks, the Holm family and the firewall are untouched.
    for field in ("m1_status_modified_by_this_action",
                  "m2_status_modified_by_this_action",
                  "m3_cbi_status_modified_by_this_action",
                  "m3_cbi_declared_successful_by_this_action",
                  "m3_lag_wdi_disposition_modified_by_this_action",
                  "m3_lag_wdi_promoted_to_confirmatory_model",
                  "confirmatory_holm_family_modified_by_this_action",
                  "family_shrunk_post_hoc_after_observing_a_result",
                  "paper_winner_selected", "final_model_selected",
                  "full_development_refit_executed",
                  "stage130_or_next_stage_executed",
                  "observational_package_modified_by_this_action",
                  "observational_extraction_admitted_as_model_input",
                  "prior_packages_modified_by_this_action"):
        if boundary.get(field) is not False:
            raise HandoffError(
                f"Stage129 M4 discontinuation boundary {field} must be False")
    if boundary.get("m4_comparison_p_value") is not None:
        raise HandoffError(
            "Stage129 M4 discontinuation must not publish a p-value for an "
            "unexecuted comparison")
    if boundary.get("m4_comparison_null_hypothesis_accepted_or_rejected") is not None:
        raise HandoffError(
            "Stage129 M4 discontinuation must not accept or reject a null "
            "hypothesis for an unexecuted comparison")
    if boundary.get("final_test_rows_read") != 0 or \
            decision.get("final_test_rows_read") != 0:
        raise HandoffError("Stage129 M4 discontinuation final_test_rows_read must be 0")
    counters = boundary.get("counters") or {}
    if not counters:
        raise HandoffError("Stage129 M4 discontinuation boundary must carry counters")
    for field, value in counters.items():
        if value != 0:
            raise HandoffError(
                f"Stage129 M4 discontinuation counters.{field} must be 0 "
                "(no retrieval, coverage, modeling or Final Test access occurred)")

    return {
        "stage129_m4_discontinuation_recorded": True,
        "stage129_m4_discontinuation_action_id": _STAGE129_M4_DISC_ACTION_ID,
        "stage129_m4_discontinuation_authorized_by_human": True,
        "stage129_m4_discontinuation_reason_class":
            decision.get("reason_class"),
        "stage129_m4_discontinuation_is_formal_gate_failure": False,
        "stage129_m4_observational_verified_opinion_rows":
            (decision.get("decision_basis") or {}).get(
                "observational_verified_auditor_opinion_rows"),
        "stage129_m4_observational_report_date_rows":
            (decision.get("decision_basis") or {}).get(
                "observational_auditor_report_date_rows"),
        "stage129_m4_observational_field_level_missing":
            (decision.get("decision_basis") or {}).get(
                "observational_field_level_missing"),
        "stage129_m4_observational_coverage_is_not_formal_gate_coverage": True,

        # Block disposition. Bare and namespaced, so a consumer checking either
        # surface sees the same fact.
        "m4_block_disposition": _STAGE129_M4_DISC_STATUS,
        "stage129_m4_block_disposition": _STAGE129_M4_DISC_STATUS,
        "m4_formal_gate_verdict": None,
        "stage129_m4_formal_gate_verdict": None,
        "m4_retrieval_continues": False,
        "m4_manual_completion_continues": False,
        "m4_feature_materialization_authorized": False,
        "m4_modeling_will_run": False,
        "m4_incremental_evaluation_will_run": False,
        "m4_reopening_authorized": False,
        "m4_reopening_requires_new_human_authorization": True,

        # Candidate identity history survives the discontinuation.
        "stage129_m4_candidate_count_after_discontinuation": 4,
        "stage129_m4_candidate_set_after_discontinuation":
            list(_STAGE129_M4_CANDIDATE_SET),
        "stage129_m4_candidates_removed_or_renamed": False,

        # Holm: recorded, never rewritten.
        "stage129_m4_comparison_id": boundary.get("m4_comparison_id"),
        "stage129_m4_comparison_status": boundary.get("m4_comparison_status"),
        "stage129_m4_comparison_p_value": None,
        "stage129_m4_confirmatory_holm_family_modified": False,
        "stage129_m4_family_shrunk_post_hoc": False,
        "stage129_m4_manuscript_reporting_decision_for_unexecuted_comparison":
            boundary.get(
                "manuscript_reporting_decision_for_the_unexecuted_m4_comparison"),

        # The M4 pointer must stop naming an M4 execution step.
        "stage129_m4_next_action_id": _STAGE129_M4_DISC_NEXT_ACTION_ID,
        "stage129_m4_next_action_scope": _STAGE129_M4_DISC_NEXT_ACTION_SCOPE,
        "stage129_m4_next_action_authorized": False,
        "stage129_m4_next_action_executes_m4": False,
        "stage129_m4_next_action_pointer_is_not_authorization": True,

        "stage129_m4_observational_package_status_preserved":
            boundary.get("observational_package_status_preserved"),
        "stage129_m4_observational_extraction_reportable_in_limitations": True,
        "stage129_m4_final_test_locked": True,
        "stage129_m4_final_test_rows_read": 0,
    }


_STAGE129_M4_REPORT_PKG = "project/stage129/m4_manuscript_reporting_decision"
_STAGE129_M4_REPORT_ACTION_ID = "stage129-m4-manuscript-reporting-decision"
_STAGE129_M4_REPORT_DECISION_REL = (
    f"{_STAGE129_M4_REPORT_PKG}/stage129_m4_manuscript_reporting_decision.json")
_STAGE129_M4_REPORT_BOUNDARY_REL = (
    f"{_STAGE129_M4_REPORT_PKG}/"
    "stage129_m4_manuscript_reporting_governance_boundary.json")
#: The one canonical, machine-readable value the reporting question resolves to.
_STAGE129_M4_REPORT_DECISION_VALUE = (
    "REPORT_AS_PRESPECIFIED_NOT_EXECUTED_DATA_INADEQUACY_NO_INFERENCE")
#: What the discontinuation package left open, and what this supersedes.
_STAGE129_M4_REPORT_SUPERSEDED_VALUE = "UNRESOLVED_REPORTING_DECISION"
_STAGE129_M4_REPORT_COMPARISON_ID = "M4_minus_M3_CBI"
_STAGE129_M4_REPORT_COMPARISON_STATUS = "NOT_EXECUTED_M4_DISCONTINUED"
#: Phrases that would turn a presentation decision into a claim about a result
#: that was never produced. The approved text may not contain any of them.
_STAGE129_M4_REPORT_FORBIDDEN_TEXT = (
    "p =", "p-value of", "p<", "p >", "p <", "significant", "significantly",
    "outperform", "improved", "improvement", "gain of", "we reject",
    "we accept", "rejected the null", "accepted the null",
)


def derive_stage129_m4_manuscript_reporting_decision_markers(root: str) -> dict:
    """Recognize the human decision on how to REPORT the unexecuted M4 block.

    Narrow and fail-closed. This is a presentation decision and nothing else:
    it retrieves no observation, re-runs no extraction, computes no coverage,
    materializes no feature, fits no model, runs no Holm step and never touches
    the Final Test.

    It resolves exactly one marker that the M4 discontinuation left open --
    ``manuscript_reporting_decision_for_the_unexecuted_m4_comparison``, which
    stood at ``UNRESOLVED_REPORTING_DECISION``. The discontinuation package
    itself stays byte-for-byte intact: this function reads it only to prove the
    supersede is anchored on the real prior value, so history is superseded in
    the open rather than rewritten.

    Fails closed if the decision tries to revert to unresolved, publish a
    p-value, resolve a null hypothesis, forge a Gate verdict, disturb the
    comparison status or the four frozen candidates, or claim a result that was
    never produced. Returns {} before the package exists.
    """
    path = os.path.join(root, _STAGE129_M4_REPORT_DECISION_REL)
    if not os.path.isfile(path):
        return {}
    decision = _require_json_artifact(root, _STAGE129_M4_REPORT_DECISION_REL)
    boundary = _require_json_artifact(root, _STAGE129_M4_REPORT_BOUNDARY_REL)

    if decision.get("decision_id") != _STAGE129_M4_REPORT_ACTION_ID:
        raise HandoffError("Stage129 M4 reporting decision decision_id mismatch")
    if boundary.get("action_id") != _STAGE129_M4_REPORT_ACTION_ID:
        raise HandoffError("Stage129 M4 reporting decision boundary action_id mismatch")
    if decision.get("decision_type") != "human_reporting_decision":
        raise HandoffError(
            "Stage129 M4 reporting decision must be a human_reporting_decision")
    if decision.get("authorized_by_human") is not True:
        raise HandoffError("Stage129 M4 reporting decision must be human-authorized")

    # (1) The decision must be RESOLVED, and resolved to the canonical value.
    # Reverting to the unresolved placeholder is a build failure, not a state.
    for source, label in ((decision, "decision"), (boundary, "boundary")):
        value = source.get(
            "manuscript_reporting_decision_for_the_unexecuted_m4_comparison")
        if value == _STAGE129_M4_REPORT_SUPERSEDED_VALUE:
            raise HandoffError(
                f"Stage129 M4 reporting {label} may not revert the manuscript "
                "reporting decision to "
                f"{_STAGE129_M4_REPORT_SUPERSEDED_VALUE}")
        if value != _STAGE129_M4_REPORT_DECISION_VALUE:
            raise HandoffError(
                f"Stage129 M4 reporting {label} decision value must be "
                f"{_STAGE129_M4_REPORT_DECISION_VALUE}, got {value!r}")
    if decision.get("decision_status") != _STAGE129_M4_REPORT_DECISION_VALUE:
        raise HandoffError(
            "Stage129 M4 reporting decision_status must be "
            f"{_STAGE129_M4_REPORT_DECISION_VALUE}")
    if boundary.get("manuscript_reporting_decision_is_resolved") is not True:
        raise HandoffError(
            "Stage129 M4 reporting boundary must declare the decision resolved")

    # (2) The supersede must be anchored on the REAL prior value, read from the
    # untouched discontinuation artifact -- not on an asserted one.
    marker = decision.get("superseded_marker") or {}
    if marker.get("artifact") != _STAGE129_M4_DISC_BOUNDARY_REL:
        raise HandoffError(
            "Stage129 M4 reporting decision must supersede "
            f"{_STAGE129_M4_DISC_BOUNDARY_REL}")
    if marker.get("key") != (
            "manuscript_reporting_decision_for_the_unexecuted_m4_comparison"):
        raise HandoffError(
            "Stage129 M4 reporting decision must supersede the reporting marker")
    if marker.get("previous_value") != _STAGE129_M4_REPORT_SUPERSEDED_VALUE:
        raise HandoffError(
            "Stage129 M4 reporting decision must record the real prior value "
            f"{_STAGE129_M4_REPORT_SUPERSEDED_VALUE}")
    if marker.get("resolved_value") != _STAGE129_M4_REPORT_DECISION_VALUE:
        raise HandoffError(
            "Stage129 M4 reporting supersede resolved_value must match the "
            "canonical decision value")
    prior = _require_json_artifact(root, _STAGE129_M4_DISC_BOUNDARY_REL)
    prior_value = prior.get(
        "manuscript_reporting_decision_for_the_unexecuted_m4_comparison")
    if prior_value != _STAGE129_M4_REPORT_SUPERSEDED_VALUE:
        raise HandoffError(
            "Stage129 M4 reporting supersede is not anchored on the historical "
            f"discontinuation value: found {prior_value!r}. The discontinuation "
            "package must stay byte-for-byte intact.")
    for field in ("prior_discontinuation_artifact_preserved_byte_for_byte",
                  "prior_contract_lock_history_preserved",
                  "prior_prerequisite_resolution_history_preserved"):
        if boundary.get(field) is not True:
            raise HandoffError(
                f"Stage129 M4 reporting boundary {field} must be True")

    # (3) The scientific state is untouched. A reporting decision may not move
    # the comparison, invent a p-value or resolve a hypothesis.
    if boundary.get("m4_comparison_id") != _STAGE129_M4_REPORT_COMPARISON_ID:
        raise HandoffError("Stage129 M4 reporting comparison_id mismatch")
    for source, label in ((decision, "decision"), (boundary, "boundary")):
        status = source.get("comparison_status") if label == "decision" \
            else source.get("m4_comparison_status")
        if status != _STAGE129_M4_REPORT_COMPARISON_STATUS:
            raise HandoffError(
                f"Stage129 M4 reporting {label} must keep the comparison at "
                f"{_STAGE129_M4_REPORT_COMPARISON_STATUS}")
    if decision.get("comparison_p_value") is not None or \
            boundary.get("m4_comparison_p_value") is not None:
        raise HandoffError(
            "Stage129 M4 reporting decision must not publish a p-value for an "
            "unexecuted comparison")
    if decision.get("null_hypothesis_accepted_or_rejected") is not None or \
            boundary.get("m4_comparison_null_hypothesis_accepted_or_rejected") \
            is not None:
        raise HandoffError(
            "Stage129 M4 reporting decision must not accept or reject a null "
            "hypothesis for an unexecuted comparison")
    for field in ("m4_comparison_removed_from_sap_history",
                  "m4_comparison_renamed_or_substituted",
                  "m4_comparison_status_modified_by_this_action",
                  "m4_block_disposition_modified_by_this_action"):
        if boundary.get(field) is not False:
            raise HandoffError(
                f"Stage129 M4 reporting boundary {field} must be False")
    if boundary.get("m4_block_disposition") != _STAGE129_M4_DISC_STATUS:
        raise HandoffError(
            "Stage129 M4 reporting boundary must preserve the M4 disposition "
            f"{_STAGE129_M4_DISC_STATUS}")

    # (4) The Gate was never executed and no Gate verdict may be forged.
    for source, label in ((decision, "decision"), (boundary, "boundary")):
        executed = source.get("formal_m4_data_gate_executed") if \
            label == "decision" else source.get("m4_data_gate_executed")
        if executed is not False:
            raise HandoffError(
                f"Stage129 M4 reporting {label} may not report an executed "
                "formal Gate")
        verdict = source.get("formal_m4_gate_verdict") if label == "decision" \
            else source.get("m4_formal_gate_verdict")
        if verdict is not None:
            raise HandoffError(
                f"Stage129 M4 reporting {label} formal Gate verdict must be null")
    if _STAGE129_M4_REPORT_DECISION_VALUE in _STAGE129_M4_GATE_VERDICT_VOCAB:
        raise HandoffError(
            "Stage129 M4 reporting decision value must not be Gate vocabulary")
    for field in ("m4_block_disposition", "m4_comparison_status",
                  "manuscript_reporting_decision_for_the_unexecuted_m4_comparison"):
        if boundary.get(field) in _STAGE129_M4_GATE_VERDICT_VOCAB:
            raise HandoffError(
                f"Stage129 M4 reporting {field} must not be a Gate verdict")

    # (5) The approved text is a reporting position, never a result claim.
    for field in ("approved_manuscript_text_en", "approved_manuscript_text_fa"):
        text = decision.get(field)
        if not isinstance(text, str) or not text.strip():
            raise HandoffError(
                f"Stage129 M4 reporting decision must carry {field}")
        lowered = text.lower()
        for phrase in _STAGE129_M4_REPORT_FORBIDDEN_TEXT:
            if phrase in lowered:
                raise HandoffError(
                    f"Stage129 M4 reporting {field} claims an executed result "
                    f"via {phrase!r}; the comparison was never executed")
    for field in ("reporting_claims_an_executed_result",
                  "reporting_claims_m4_performance"):
        if decision.get(field) is not False or boundary.get(field) is not False:
            raise HandoffError(
                f"Stage129 M4 reporting {field} must be False")
    if decision.get("m4_was_prespecified") is not True:
        raise HandoffError(
            "Stage129 M4 reporting decision must record that M4 was prespecified")
    if decision.get("m4_was_stopped_before_admission_and_modeling") is not True:
        raise HandoffError(
            "Stage129 M4 reporting decision must record that M4 was stopped "
            "before admission and modeling")
    if boundary.get("manuscript_writing_or_rewriting_authorized") is not False:
        raise HandoffError(
            "Stage129 M4 reporting decision is not a manuscript writing "
            "authorization")

    # (6) The four frozen candidates survive with identity, order and count.
    if tuple(decision.get("m4_candidate_set") or ()) != _STAGE129_M4_CANDIDATE_SET:
        raise HandoffError(
            "Stage129 M4 reporting decision must preserve the four frozen "
            f"candidates exactly as {_STAGE129_M4_CANDIDATE_SET}")
    if decision.get("m4_candidate_count") != 4:
        raise HandoffError(
            "Stage129 M4 reporting decision must preserve candidate_count 4")
    for field in ("m4_candidate_count_changed_by_this_decision",
                  "m4_candidates_removed_or_renamed_by_this_decision",
                  "m4_candidates_substituted_by_this_decision"):
        if decision.get(field) is not False:
            raise HandoffError(f"Stage129 M4 reporting decision {field} must be False")

    # (7) Nothing is authorized or executed by a reporting decision.
    for field in ("m4_retrieval_continues", "m4_manual_completion_continues",
                  "m4_feature_materialization_authorized", "m4_modeling_will_run",
                  "m4_incremental_evaluation_will_run", "m4_reopening_authorized",
                  "m4_block_admitted", "m4_data_gate_authorized",
                  "m4_coverage_calculated",
                  "confirmatory_holm_family_modified_by_this_action",
                  "family_shrunk_post_hoc_after_observing_a_result",
                  "m1_status_modified_by_this_action",
                  "m2_status_modified_by_this_action",
                  "m3_cbi_status_modified_by_this_action",
                  "m3_cbi_declared_successful_by_this_action",
                  "m3_lag_wdi_disposition_modified_by_this_action",
                  "m3_lag_wdi_promoted_to_confirmatory_model",
                  "observational_package_modified_by_this_action",
                  "observational_extraction_admitted_as_model_input",
                  "prior_packages_modified_by_this_action",
                  "paper_winner_selected", "final_model_selected",
                  "full_development_refit_executed",
                  "stage130_or_next_stage_executed",
                  "final_test_access_authorized", "next_action_authorized",
                  "next_action_executes_m4"):
        if boundary.get(field) is not False:
            raise HandoffError(
                f"Stage129 M4 reporting boundary {field} must be False")
    if boundary.get("m4_reopening_requires_new_human_authorization") is not True:
        raise HandoffError(
            "Stage129 M4 reporting must keep reopening behind a new human "
            "authorization")
    if boundary.get("final_test_rows_read") != 0 or \
            decision.get("final_test_rows_read") != 0:
        raise HandoffError("Stage129 M4 reporting final_test_rows_read must be 0")
    if boundary.get("final_test_locked") is not True:
        raise HandoffError("Stage129 M4 reporting must keep the Final Test locked")
    if boundary.get("next_action_id") != _STAGE129_M4_DISC_NEXT_ACTION_ID:
        raise HandoffError(
            "Stage129 M4 reporting must keep the M4 pointer at "
            f"{_STAGE129_M4_DISC_NEXT_ACTION_ID}")
    if boundary.get("next_action_scope") != _STAGE129_M4_DISC_NEXT_ACTION_SCOPE:
        raise HandoffError(
            "Stage129 M4 reporting must keep the M4 pointer scope unchanged")
    counters = boundary.get("counters") or {}
    if not counters:
        raise HandoffError("Stage129 M4 reporting boundary must carry counters")
    for field, value in counters.items():
        if value != 0:
            raise HandoffError(
                f"Stage129 M4 reporting counters.{field} must be 0 "
                "(no extraction rerun, retrieval, coverage, modeling, Holm, "
                "bootstrap, SHAP or Final Test access occurred)")

    return {
        "stage129_m4_manuscript_reporting_decision_recorded": True,
        "stage129_m4_manuscript_reporting_decision_action_id":
            _STAGE129_M4_REPORT_ACTION_ID,
        "stage129_m4_manuscript_reporting_decision_authorized_by_human": True,
        "stage129_m4_manuscript_reporting_decision_is_resolved": True,

        # THE resolved marker. Supersedes the discontinuation's unresolved
        # placeholder on the live surface; the artifact itself keeps its history.
        "stage129_m4_manuscript_reporting_decision_for_unexecuted_comparison":
            _STAGE129_M4_REPORT_DECISION_VALUE,
        "stage129_m4_manuscript_reporting_decision_previous_value":
            _STAGE129_M4_REPORT_SUPERSEDED_VALUE,
        "stage129_m4_manuscript_reporting_decision_supersedes_artifact":
            _STAGE129_M4_DISC_BOUNDARY_REL,
        "stage129_m4_manuscript_reporting_decision_supersedes_key":
            "manuscript_reporting_decision_for_the_unexecuted_m4_comparison",
        "stage129_m4_prior_discontinuation_artifact_preserved": True,

        # The reporting position itself, stated as what was NOT done.
        "stage129_m4_reported_as_prespecified": True,
        "stage129_m4_reported_as_not_executed": True,
        "stage129_m4_reporting_reason_class":
            decision.get("reporting_reason_class"),
        "stage129_m4_reporting_claims_an_executed_result": False,
        "stage129_m4_reporting_claims_m4_performance": False,
        "stage129_m4_reporting_null_hypothesis_accepted_or_rejected": None,
        "stage129_m4_comparison_removed_from_sap_history": False,
        "stage129_m4_comparison_renamed_or_substituted": False,
        "stage129_m4_approved_manuscript_text_en":
            decision.get("approved_manuscript_text_en"),
        "stage129_m4_approved_manuscript_text_fa":
            decision.get("approved_manuscript_text_fa"),
        "stage129_m4_manuscript_writing_authorized": False,

        # Restated from this action's own boundary, so a consumer reading only
        # the reporting decision still sees the firewall.
        "stage129_m4_reporting_is_formal_gate_failure": False,
        "stage129_m4_reporting_final_test_rows_read": 0,
    }


#: The evidence-capture PR, merged into main and now the predecessor context.
_STAGE128_M3I2_EVIDENCE_CAPTURE_PR_NUMBER = 75

_STAGE128_M3I2_GOVERNANCE_BOUNDARY_REL = (
    "project/stage128/m3i2_official_source_evidence_capture/"
    "stage128_m3i2_evidence_capture_governance_boundary.json")
_STAGE128_M3I2_LIVE_BASE_BRANCH = "main"


def derive_stage128_m3i2_live_pr_topology_markers(root: str) -> dict:
    """Publish the LIVE (evidence-capture) M3I-2 PR topology.

    The contract-lock artifact records the topology that was live *at contract
    time* (PR #74). That is history. The live draft is the separate
    evidence-capture PR, and this function derives it — fail-closed — from the
    evidence-capture artifacts themselves:

    * the evidence decision and the governance boundary agree on the base
      branch, the base commit and the Draft/no-merge posture;
    * the independent bundle-integrity audit record names the PR number, which
      must be a *successor* of the contract-time PR;
    * the live head is taken from the CURRENT repository head, never pinned.

    Returns {} before the evidence capture exists. Publishing a live topology
    is pure metadata: it admits nothing and moves no scientific state.
    """
    decision_path = os.path.join(root, _STAGE128_M3I2_EVIDENCE_DECISION_REL)
    if not os.path.isfile(decision_path):
        return {}
    with open(decision_path, encoding="utf-8") as fh:
        decision = json.load(fh)
    if decision.get("action_id") != _STAGE128_M3I2_EVIDENCE_ACTION_ID:
        raise HandoffError("stage128 M3I-2 evidence-capture action_id mismatch")

    boundary_path = os.path.join(root, _STAGE128_M3I2_GOVERNANCE_BOUNDARY_REL)
    audit_path = os.path.join(root, _STAGE128_M3I2_INDEPENDENT_AUDIT_REL)
    for path in (boundary_path, audit_path):
        if not os.path.isfile(path):
            raise HandoffError(
                "the M3I-2 live PR topology cannot be derived without "
                f"{os.path.relpath(path, root)}")
    with open(boundary_path, encoding="utf-8") as fh:
        boundary = json.load(fh)
    with open(audit_path, encoding="utf-8") as fh:
        audit = json.load(fh)

    # 1. Base branch: all three artifacts must agree, and it must be main.
    branches = {
        decision.get("pr_base_branch"),
        boundary.get("pr_base_branch"),
        audit.get("audited_pr_base_branch"),
    }
    if branches != {_STAGE128_M3I2_LIVE_BASE_BRANCH}:
        raise HandoffError(
            "the live M3I-2 PR base branch is inconsistent across the "
            f"evidence-capture artifacts: {sorted(map(str, branches))}")

    # 2. Base commit: the merge commit of the contract-time predecessor PR is
    #    current main, and it is the live base of the evidence-capture PR.
    commits = {
        decision.get("baseline_commit"),
        decision.get("predecessor_pr_merge_commit"),
        boundary.get("baseline_commit"),
        boundary.get("predecessor_pr_merge_commit"),
        audit.get("audited_pr_base_sha"),
    }
    if len(commits) != 1:
        raise HandoffError(
            "the live M3I-2 PR base commit is inconsistent across the "
            f"evidence-capture artifacts: {sorted(map(str, commits))}")
    base_commit = commits.pop()
    if not (isinstance(base_commit, str) and len(base_commit) == 40):
        raise HandoffError(
            "the live M3I-2 PR base commit must be a full 40-hex SHA")

    # 3. The live PR is a Draft, unmerged and carries no merge authorization.
    for source, artifact in (("evidence decision", decision),
                             ("governance boundary", boundary)):
        if artifact.get("pr_is_draft") is not True:
            raise HandoffError(
                f"the live M3I-2 PR must remain a Draft ({source})")
        if artifact.get("merge_authorized") is not False:
            raise HandoffError(
                f"no merge authorization exists for the live M3I-2 PR "
                f"({source})")
    if audit.get("merge_authorized") is not False:
        raise HandoffError(
            "no merge authorization exists for the live M3I-2 PR (audit)")

    # 4. The live PR number is a strict successor of the contract-time PR.
    live_number = audit.get("pr_number")
    predecessor_numbers = {
        decision.get("predecessor_pr_number"),
        boundary.get("predecessor_pr_number"),
    }
    if len(predecessor_numbers) != 1:
        raise HandoffError(
            "the M3I-2 contract-time predecessor PR number is inconsistent")
    predecessor_number = predecessor_numbers.pop()
    if not isinstance(live_number, int) or isinstance(live_number, bool):
        raise HandoffError("the live M3I-2 PR number must be an integer")
    if not isinstance(predecessor_number, int):
        raise HandoffError(
            "the M3I-2 contract-time predecessor PR number must be an integer")
    if live_number <= predecessor_number:
        raise HandoffError(
            f"the live M3I-2 PR #{live_number} must succeed the contract-time "
            f"PR #{predecessor_number}")
    if decision.get("predecessor_pr_merged") is not True or boundary.get(
            "predecessor_pr_merged") is not True:
        raise HandoffError(
            "the live M3I-2 PR targets main, so the contract-time PR must be "
            "recorded as merged")

    # The live head is NOT published here: it is the CURRENT repository head,
    # so it is HEAD-relative and must stay out of the fingerprinted semantic
    # state. `build_handoff_state` attaches it to the record as a VOLATILE
    # field derived from the repository head — never a pinned SHA.
    return {
        "stage128_m3i2_live_pr_number": live_number,
        "stage128_m3i2_live_pr_base_branch": _STAGE128_M3I2_LIVE_BASE_BRANCH,
        "stage128_m3i2_live_pr_base_commit": base_commit,
        "stage128_m3i2_live_main_commit": base_commit,
        "stage128_m3i2_live_pr_is_draft": True,
        "stage128_m3i2_live_pr_merged": False,
        "stage128_m3i2_live_pr_head_commit_source": (
            "observed_repository_head_commit_at_generation"),
        "stage128_m3i2_live_pr_role": "official_source_evidence_capture_pr",
        "stage128_m3i2_contract_time_pr_number": predecessor_number,
        "stage128_m3i2_contract_time_pr_semantics": (
            "historical_contract_lock_topology_superseded_by_pr"
            f"{live_number}"),
        "stage128_m3i2_merge_authorized": False,
        # Topology metadata never moves the scientific state.
        "m3i2_data_gate_executed": False,
        "m3i2_block_admitted": False,
        "m3i2_modeling_started": False,
        "m4_authorized": False,
        "final_test_locked": True,
    }


#: Semantics label for the CONTRACT-TIME PR topology. It is history, never the
#: live draft. When the superseding evidence-capture PR is recognizable the
#: live-topology deriver replaces it with the explicit
#: ``..._superseded_by_pr<N>`` form (N derived, never hard-coded).
_STAGE128_M3I2_CONTRACT_TIME_PR_SEMANTICS_BASE = (
    "historical_contract_lock_topology_not_live")

_STAGE128_M3I2_ACTIVE_WORKSTREAM_ID = "stage128-m3i2-prospective-contract-lock"

_STAGE128_M3I2_CONTRACT_LOCK_REL = (
    "project/stage128/m3_intl_macro_contract_lock/"
    "stage128_m3_intl_macro_contract_decision.json"
)
_STAGE128_M3I2_ACTION_ID = "stage128-m3i2-prospective-contract-lock"
_STAGE128_M3I2_CONTRACT_STATUS = "PROSPECTIVELY_LOCKED_NO_DATA"
_STAGE128_M3I3_FINANCING_LOCK_STATUS = "UNRESOLVED_METADATA_LOCK"
#: Informational pointer only, and explicitly NOT authorized.
_NEXT_RESEARCH_ACTION_ID_AFTER_M3I2_CONTRACT_LOCK = (
    "stage128-m3i2-official-source-evidence-capture"
)


def derive_stage128_m3i2_contract_lock_markers(root: str) -> dict:
    """Recognize the prospective M3I-2 supplementary contract lock.

    Narrow and fail-closed. The lock is a CONTRACT event only:

    * it retrieves no macro observation and creates no dataset row;
    * it executes no Data Gate and computes no coverage;
    * it fits no model, predicts nothing and runs no M3I-versus-M2 comparison;
    * it never admits a block and never authorizes an evaluation;
    * the frozen CBI M3 contract is preserved unchanged, and M3I is a
      SUPPLEMENTARY family that is never presented as confirmatory M3;
    * M3I-3 financing stays UNRESOLVED and inadmissible;
    * M4 and the final test are untouched.

    Returns {} before the contract lock exists.
    """
    path = os.path.join(root, _STAGE128_M3I2_CONTRACT_LOCK_REL)
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)

    if d.get("action_id") != _STAGE128_M3I2_ACTION_ID:
        raise HandoffError("stage128 M3I-2 contract-lock action_id mismatch")
    if d.get("m3i2_contract_lock_executed") is not True:
        return {}
    if d.get("m3i2_contract_status") != _STAGE128_M3I2_CONTRACT_STATUS:
        raise HandoffError(
            "stage128 M3I-2 contract status must be "
            f"{_STAGE128_M3I2_CONTRACT_STATUS}")
    for field, expected in (
        ("m3i2_retrieval_started", False),
        ("m3i2_data_gate_executed", False),
        ("m3i2_block_admitted", False),
        ("m3i2_incremental_evaluation_authorized", False),
        ("m3i2_modeling_started", False),
        ("m3i3_admitted", False),
        ("m3_cbi_contract_changed", False),
        ("m3_cbi_block_admitted", False),
        ("m4_authorized", False),
        ("m4_started", False),
        ("final_test_locked", True),
        ("final_test_access_authorized", False),
        ("merge_authorized", False),
        ("data_collection_started", False),
        ("pr_is_draft", True),
    ):
        if d.get(field) is not expected:
            raise HandoffError(
                f"stage128 M3I-2 contract lock {field} must be {expected}")
    for field in ("network_requests", "data_files_downloaded",
                  "macro_observations_read", "company_rows_loaded",
                  "final_test_rows_loaded", "model_fits", "predictions",
                  "predictive_metrics", "coverage_calculations",
                  "holm_calculations"):
        if d.get(field) != 0:
            raise HandoffError(
                f"stage128 M3I-2 contract lock {field} must be 0")
    if d.get("m3_cbi_gate_status") != "UNRESOLVED_M3_DATA_GATE":
        raise HandoffError(
            "stage128 M3I-2 contract lock must preserve the M3-CBI Gate "
            "status UNRESOLVED_M3_DATA_GATE")
    if d.get("m3i3_financing_lock") != _STAGE128_M3I3_FINANCING_LOCK_STATUS:
        raise HandoffError(
            "stage128 M3I-3 financing metadata lock must remain "
            f"{_STAGE128_M3I3_FINANCING_LOCK_STATUS}")
    if d.get("next_research_action_id") != (
            _NEXT_RESEARCH_ACTION_ID_AFTER_M3I2_CONTRACT_LOCK):
        raise HandoffError(
            "stage128 M3I-2 contract lock next_research_action_id mismatch")
    if d.get("next_action_authorized") is not False:
        raise HandoffError(
            "the action after the M3I-2 contract lock is NOT authorized")
    # The base rule is STATE-DEPENDENT. It was "never main" only while PR #73
    # was open; PR #73 has since been merged and PR #74 was retargeted to main.
    topo = d.get("live_topology") or {}
    merged = topo.get("predecessor_pr_merged", d.get("predecessor_pr_merged"))
    base = topo.get("live_pr_base_branch", d.get("pr_base_branch"))
    if merged is False:
        if base == _STAGE128_M3I2_MAIN_BRANCH:
            raise HandoffError(
                "the M3I-2 contract-lock PR may not target main while PR #73 "
                "is open")
        if base != _STAGE128_M3I2_PREDECESSOR_BRANCH:
            raise HandoffError(
                "while PR #73 is open the M3I-2 contract-lock PR base must be "
                f"{_STAGE128_M3I2_PREDECESSOR_BRANCH}")
        if topo.get("pr_is_stacked_on_open_predecessor") is False:
            raise HandoffError(
                "PR #73 is open, so the M3I-2 PR is stacked on it")
    elif merged is True:
        if topo.get("predecessor_pr_merge_commit") != (
                _STAGE128_M3I2_PREDECESSOR_MERGE_COMMIT):
            raise HandoffError(
                "the M3I-2 contract lock records PR #73 as merged without the "
                "verified merge commit "
                f"{_STAGE128_M3I2_PREDECESSOR_MERGE_COMMIT}")
        if topo.get("live_main_commit") != (
                _STAGE128_M3I2_PREDECESSOR_MERGE_COMMIT):
            raise HandoffError(
                "live main must equal the PR #73 merge commit")
        if base == _STAGE128_M3I2_PREDECESSOR_BRANCH:
            raise HandoffError(
                "PR #73 is merged; the M3I-2 PR base may not still name the "
                "merged predecessor branch")
        if base != _STAGE128_M3I2_MAIN_BRANCH:
            raise HandoffError(
                "after PR #73 merged the M3I-2 contract-lock PR base must be "
                "main")
        if topo.get("live_pr_base_commit") != (
                _STAGE128_M3I2_PREDECESSOR_MERGE_COMMIT):
            raise HandoffError(
                "the live PR base commit must equal current main")
        if topo.get("pr_is_stacked_on_open_predecessor") is not False:
            raise HandoffError(
                "PR #73 is merged, so the M3I-2 PR is no longer stacked on an "
                "open predecessor")
        if topo.get(
                "retargeted_to_main_after_predecessor_merge_verified") is not (
                True):
            raise HandoffError(
                "the retarget to main must be recorded as verified after the "
                "PR #73 merge")
        if topo.get("may_target_main") is not True:
            raise HandoffError(
                "after PR #73 merged the M3I-2 PR may target main")
    else:
        raise HandoffError(
            "the M3I-2 contract lock must record predecessor_pr_merged "
            "explicitly")
    # In BOTH states the scientific provenance baseline stays the PR #73 HEAD,
    # never the merge commit, and PR #74 stays a Draft with no merge rights.
    if topo.get("scientific_provenance_baseline_commit") != (
            _STAGE128_M3I2_PROVENANCE_BASELINE_COMMIT):
        raise HandoffError(
            "the M3I-2 scientific provenance baseline must remain the PR #73 "
            f"head {_STAGE128_M3I2_PROVENANCE_BASELINE_COMMIT}")
    if topo.get("live_pr_is_draft") is not True:
        raise HandoffError("PR #74 must remain a Draft")
    if topo.get("live_pr_merged") is not False:
        raise HandoffError("PR #74 must remain unmerged")
    if topo.get("merge_authorized") is not False:
        raise HandoffError("no merge authorization exists for PR #74")

    return {
        "stage128_m3i2_contract_lock_executed": True,
        "stage128_m3i2_contract_status": _STAGE128_M3I2_CONTRACT_STATUS,
        "stage128_m3i2_contract_lock_authorization_consumed": True,
        "stage128_m3i2_baseline_pr_number": d.get("baseline_pr_number"),
        "stage128_m3i2_baseline_commit": d.get("baseline_commit"),
        "stage128_m3i2_pr_base_branch": d.get("pr_base_branch"),
        "stage128_m3i2_provenance_baseline_commit": topo.get(
            "scientific_provenance_baseline_commit"),
        # CONTRACT-TIME topology. These values were live at the moment of the
        # contract lock and are retained as HISTORY only; they are never the
        # current draft. The live evidence-capture PR topology is published
        # separately by `derive_stage128_m3i2_live_pr_topology_markers`.
        "stage128_m3i2_contract_time_pr_number": topo.get("live_pr_number"),
        "stage128_m3i2_contract_time_pr_base_branch": topo.get(
            "live_pr_base_branch"),
        "stage128_m3i2_contract_time_pr_base_commit": topo.get(
            "live_pr_base_commit"),
        "stage128_m3i2_contract_time_main_commit": topo.get("live_main_commit"),
        "stage128_m3i2_contract_time_pr_is_draft": topo.get("live_pr_is_draft"),
        "stage128_m3i2_contract_time_pr_merged": topo.get("live_pr_merged"),
        "stage128_m3i2_contract_time_pr_semantics": (
            _STAGE128_M3I2_CONTRACT_TIME_PR_SEMANTICS_BASE),
        "stage128_m3i2_predecessor_pr_merged": topo.get(
            "predecessor_pr_merged"),
        "stage128_m3i2_predecessor_pr_merge_commit": topo.get(
            "predecessor_pr_merge_commit"),
        "stage128_m3i2_pr_is_stacked_on_open_predecessor": topo.get(
            "pr_is_stacked_on_open_predecessor"),
        "stage128_m3i2_retargeted_to_main_after_predecessor_merge_verified":
            topo.get("retargeted_to_main_after_predecessor_merge_verified"),
        "stage128_m3i2_may_target_main": topo.get("may_target_main"),
        "stage128_m3i2_merge_authorized": False,
        # A CONTRACT lock is not data and not modeling.
        "m3i2_contract_lock_executed": True,
        "m3i2_contract_status": _STAGE128_M3I2_CONTRACT_STATUS,
        "m3i2_retrieval_started": False,
        "m3i2_data_gate_executed": False,
        "m3i2_block_admitted": False,
        "m3i2_incremental_evaluation_authorized": False,
        "m3i2_modeling_started": False,
        "m3i3_financing_lock": _STAGE128_M3I3_FINANCING_LOCK_STATUS,
        "m3i3_admitted": False,
        "m3i_is_supplementary_not_confirmatory_m3": True,
        # The frozen CBI block is untouched.
        "m3_macro_data_gate_status": d.get("m3_cbi_gate_status"),
        "m3_block_admitted_for_incremental_evaluation": False,
        "m3_incremental_evaluation_authorized": False,
        "m3_modeling_started": False,
        "m4_authorized": False,
        "m4_started": False,
        "final_test_locked": True,
        # Pointers. The lock IS a completed research action; the pointer it
        # publishes is informational and explicitly unauthorized.
        "last_completed_research_action_id": _STAGE128_M3I2_ACTION_ID,
        "next_research_action_id": (
            _NEXT_RESEARCH_ACTION_ID_AFTER_M3I2_CONTRACT_LOCK),
        "next_research_action_authorized": False,
        "next_research_action_pointer_is_not_authorization": True,
    }


_STAGE128_M2_RETAINED_BLOCK_DECISION_REL = (
    "project/stage128/m2_retained_block_human_decision/"
    "stage128_m2_retained_block_human_decision.json"
)
_STAGE128_M2_RETAINED_BLOCK_DECISION_ACTION_ID = (
    "stage128-m2-retained-block-human-decision"
)
_STAGE128_M2_RETAINED_BLOCK_DECISION_OUTCOME = (
    "RETAIN_M2_AS_INTERMEDIATE_CONFIRMATORY_BLOCK"
)
#: After the human retained-block decision the live pointer is the M3 data
#: Gate. It is a pointer ONLY: M3 is not authorized and not started.
_NEXT_RESEARCH_ACTION_ID_AFTER_M2_RETAINED_BLOCK_DECISION = (
    "stage128-m3-macro-data-gate"
)


def derive_stage128_m2_retained_block_human_decision_markers(
    root: str,
) -> dict:
    """Recognize the recorded HUMAN retained-block decision.

    Narrow and fail-closed. The decision is a governance/design decision only:

    * M2 is RETAINED as the intermediate confirmatory block, and that retention
      is explicitly NOT a superiority claim, a winner, or a final model;
    * nothing was fit, predicted, resampled or refitted;
    * the final test stays locked and M3/M4 stay unauthorized and unstarted;
    * its one-action human authorization is CONSUMED by the recording.

    Returns {} before the decision has been recorded.
    """
    path = os.path.join(root, _STAGE128_M2_RETAINED_BLOCK_DECISION_REL)
    if not os.path.isfile(path):
        return {}
    try:
        d = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(
            f"unreadable stage128 M2 retained-block decision: {exc}") from exc

    if d.get("decision_id") != _STAGE128_M2_RETAINED_BLOCK_DECISION_ACTION_ID:
        raise HandoffError("stage128 M2 retained-block decision_id mismatch")
    if d.get("decision_outcome") != _STAGE128_M2_RETAINED_BLOCK_DECISION_OUTCOME:
        raise HandoffError(
            "stage128 M2 retained-block decision_outcome mismatch")

    exact = {
        "m2_block_retained": True,
        "m2_retained_block_decision_required": False,
        "m2_retained_block_human_decision_completed": True,
        "m2_retained_block_human_decision_authorization_consumed": True,
        "m2_predictive_superiority_claim_supported": False,
        "paper_winner_selected": False,
        "final_model_selected": False,
        "full_development_refit_performed": False,
        "final_test_locked": True,
        "final_test_access_authorized": False,
        "final_test_evaluation_performed": False,
        "m3_authorized": False,
        "m3_started": False,
        "m4_authorized": False,
        "m4_started": False,
        "holm_family_complete": False,
        "holm_final_adjustment_deferred": True,
        "authorization_consumed": True,
        "authorizes_next_action": False,
        "next_research_action_pointer_is_not_authorization": True,
    }
    for key, want in exact.items():
        if d.get(key) != want:
            raise HandoffError(
                f"stage128 M2 retained-block decision field {key}="
                f"{d.get(key)!r} != {want!r}"
            )

    audit = d.get("execution_audit") or {}
    for key in (
        "model_fits", "predictions", "new_oof_rows_generated",
        "resampling_executions", "bootstrap_executions",
        "holm_adjustment_executions", "p_value_computations",
        "calibration_executions", "shap_executions",
        "full_development_refits", "final_test_predictor_values_read",
        "final_test_target_values_read", "final_test_predictions",
        "final_test_evaluations", "m3_executions", "m4_executions",
        "scientific_artifacts_regenerated",
    ):
        if audit.get(key) != 0:
            raise HandoffError(
                f"stage128 M2 retained-block execution audit {key}="
                f"{audit.get(key)!r} != 0"
            )
    if d.get("next_research_action_id") != (
        _NEXT_RESEARCH_ACTION_ID_AFTER_M2_RETAINED_BLOCK_DECISION
    ):
        raise HandoffError(
            "stage128 M2 retained-block next_research_action_id mismatch")

    return {
        "stage128_m2_retained_block_human_decision_completed": True,
        "stage128_m2_retained_block_human_decision_outcome": (
            _STAGE128_M2_RETAINED_BLOCK_DECISION_OUTCOME
        ),
        "stage128_m2_retained_block_human_decision_authorization_consumed":
            True,
        "stage128_m2_retention_basis": d.get("m2_retention_basis"),
        # RETENTION and SUPERIORITY are different things. M2 is retained as the
        # intermediate confirmatory block; the observed development evidence
        # stays approximately null and no superiority claim is supported.
        "m2_block_retained": True,
        "m2_retained_block_decision_required": False,
        "m2_retained_block_human_decision_completed": True,
        "m2_retained_block_human_decision_authorization_consumed": True,
        "m2_predictive_superiority_claim_supported": False,
        "m2_evaluation_completed": True,
        "m2_superiority_established": False,
        "m2_winner_selected": False,
        "holm_family_complete": False,
        "holm_final_adjustment_deferred": True,
        "last_completed_research_action_id": (
            _STAGE128_M2_RETAINED_BLOCK_DECISION_ACTION_ID
        ),
        "next_research_action_id": (
            _NEXT_RESEARCH_ACTION_ID_AFTER_M2_RETAINED_BLOCK_DECISION
        ),
        "next_research_action_pointer_is_not_authorization": True,
        "paper_winner_selected": False,
        "final_model_selected": False,
        "full_development_refit_performed": False,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_predictor_values_inspected": False,
        "final_test_target_values_inspected": False,
        "final_test_evaluation_performed": False,
        "m3_authorized": False,
        "m3_started": False,
        "m3_data_collected": False,
        "m4_authorized": False,
        "m4_started": False,
    }


if __name__ == "__main__":
    raise SystemExit(main())
