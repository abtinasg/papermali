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
)
ALLOWLIST_FILES = (
    "project/scripts/update_ai_handoff.py",
    "project/scripts/validate_ai_handoff.py",
    "project/tests/test_ai_handoff.py",
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
    "project/stage125/part3c_input_hash_manifest_stage125.json",
    "project/stage125/part3c_column_role_map_stage125.csv",
    "project/stage125/part3c_sample_summary_stage125.csv",
    "project/stage125/part3c_target_year_distribution_stage125.csv",
    "project/stage125/part3c_leakage_audit_stage125.csv",
    "project/stage125/stage125_part3c_leakage_safe_dataset_qc_report.json",
    "project/stage125/metadata_and_hashes_stage125_part3c.json",
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
        "part3c_leakage_safe_finalization_completed",
        "network_extraction_performed",
        "modeling_started",
    ),
}


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


def _introduced_files(root: str, sha: str) -> list[str]:
    """Files a commit introduced relative to its first parent.

    Works for merge commits too (diff against the first parent shows what the
    merge brought in). The root commit (no parent) lists all its files.
    """
    parents = _git(root, "rev-list", "--parents", "-n", "1", sha).split()[1:]
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

def semantic_state(root: str):
    head = head_commit(root)
    roadmap = read_roadmap(root)
    workstream = roadmap["active_research_workstream_id"].replace("-", "_")
    qc_scope_val = roadmap.get("qc_scope", "")
    qc_scope = qc_scope_val.replace("-", "_") if qc_scope_val else workstream
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
        "last_completed_micro_part": roadmap["last_completed_research_action_id"],
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
        f"- **Last completed research action:** `{record['last_completed_micro_part']}`",
        f"- **Next research action:** `{record['next_research_action_id']}`",
        f"- **Last stage commit:** `{record['last_stage_commit']}`",
        f"- **Generated from commit:** `{record['generated_from_commit']}` "
        f"(branch `{record['observed_branch']}`, informational)",
        f"- **Baseline:** `{record['baseline_branch']}` @ `{record['baseline_commit']}`",
        "",
        "## QC\n",
        f"- {qc_ok} **{record['qc_assertions']} assertions, "
        f"{record['qc_failed']} failed**, all_pass={record['qc_all_pass']}",
        f"- Scope: `{record['selected_qc_scope']}`",
        f"- Report: `{record['selected_qc_path']}`",
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


if __name__ == "__main__":
    raise SystemExit(main())
