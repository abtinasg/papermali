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
    return {
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
    }


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
                "- \\u26d4 **M2 block retained BY THIS ACTION:** false \u2014 it "
                "reports OBSERVED development evidence only and selects no "
                "winner. The retained-block question was answered "
                "separately, by the human decision reported below "
                f"(`m2_block_retained={record.get('m2_block_retained')}`, "
                "`m2_retained_block_decision_required="
                f"{record.get('m2_retained_block_decision_required')}`)"
                if record.get(
                    "stage128_m2_retained_block_human_decision_completed")
                else
                "- \\u26d4 **M2 block retained:** "
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
            "- **Next research action (pointer only):** "
            f"`{record['next_research_action_id']}` — the M3 macro data "
            "Gate. A pointer is **not** an authorization: no macro data was "
            "collected, no M3 variable created, no M3 Gate executed and no M3 "
            "model fit.",
            "- Package: "
            "`project/stage128/m2_retained_block_human_decision/`; "
            "interpretation: "
            "`project/stage128/m2_retained_block_human_decision/"
            "README_STAGE128_M2_RETAINED_BLOCK_HUMAN_DECISION.md`",
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
    # Fail closed on a stale live workstream label: once the freeze is
    # recognized, the ROADMAP's CURRENT workstream pointer may not still name
    # the completed Stage126 M1 baseline.
    roadmap_workstream = read_roadmap(root)["active_research_workstream_id"]
    if roadmap_workstream != _STAGE128_ACTIVE_WORKSTREAM_ID:
        raise HandoffError(
            f"stage128 M2 D2 freeze is complete but ROADMAP "
            f"active_research_workstream_id={roadmap_workstream!r} != "
            f"{_STAGE128_ACTIVE_WORKSTREAM_ID!r}"
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
