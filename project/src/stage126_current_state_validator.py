"""Stage126 — independent current-state validator.

Establishes and enforces the validation-architecture boundary locked by the
human governance decision recorded here:

  * **Stage125 Part 5 is historical and immutable.** It is no longer a live
    successor-state validator for Stage126. This module NEVER imports the
    Part 5 source, NEVER executes the Part 5 runner and NEVER calls its
    ``validate_actual_handoff``. Part 5 is pinned by hash only.
  * **Current Stage126 state is validated only here**, from Stage126-native
    contracts (the Part 0 execution-order contract, the primary development
    lock, the selected configurations, the final-test lock guard, per-part
    authorization records and completion locks, per-part metadata manifests)
    plus the live Handoff.
  * **Completing a later robustness micro-part must not regenerate, modify or
    rehash verification-only artifacts belonging to earlier parts.** Earlier
    parts are closed historical packages, protected by immutable hashes.
  * **Reopening a completed part requires a documented genuine scientific error
    AND a separate explicit human authorization.** This validator never reopens
    a previous part automatically.

The per-part logic is GENERIC: parts are discovered from the Part 0 registered
execution order by naming convention, so a future Part 3 advances current state
by adding only its own files — no Part 1, Part 2 or Stage125 file may change.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #

QC_STAGE = "stage126_current_state_validator"
CURRENT_STAGE = "Stage126"
VALIDATOR_ID = "stage126_current_state_validator"
VALIDATOR_VERSION = "stage126_current_state_validator_v2_lean"
DECISION_ID = "stage126-validation-architecture-boundary-lock"
DECISION_VERSION = "stage126_validation_architecture_boundary_v1"
# The validator version AS RECORDED by the frozen 2026-07-23 human decision
# text/architecture. This decision is a historical, locked governance record
# (see build_decision_record and STAGE126_Q1Q2_LEAN_GOVERNANCE.md section 3:
# "validator refactor that preserves scientific gates" needs no new
# authorization). It must stay byte-identical to what was actually decided
# that day — including the validator version that existed then — regardless
# of how many times VALIDATOR_VERSION itself is bumped afterward by ordinary
# maintenance. Do NOT change this constant when VALIDATOR_VERSION changes.
HISTORICAL_DECISION_VALIDATOR_VERSION = "stage126_current_state_validator_v1"

# --------------------------------------------------------------------------- #
# Stage126+ Q1/Q2 Lean Research Governance (see
# project/docs/ai/STAGE126_Q1Q2_LEAN_GOVERNANCE.md)
# --------------------------------------------------------------------------- #
# Scientific decisions/outputs are hard-locked; engineering support files are
# Git-versioned, reviewable and mutable. Of the three closed-part registry
# buckets, only `scientific_artifacts_sha256` remains a live scientific gate.
# `code_artifacts_sha256` and `verification_artifacts_sha256` describe
# tests/QC/metadata bookkeeping for a closed part: they remain in the registry
# as historical provenance, but their byte drift is reported informationally
# and never fails the live current-state gate.
VALIDATION_ARCHITECTURE = "stage126_q1q2_lean_governance_v1"
SCIENTIFIC_GATE_BUCKETS: tuple[str, ...] = ("scientific_artifacts_sha256",)
INFORMATIONAL_ONLY_BUCKETS: tuple[str, ...] = (
    "code_artifacts_sha256",
    "verification_artifacts_sha256",
)

SRC_REL = "project/src/stage126_current_state_validator.py"
RUN_REL = "project/run_stage126_current_state_validator.py"
TEST_REL = "project/tests/test_stage126_current_state_validator.py"

STAGE126_DIR_REL = "project/stage126"
F_DECISION = "stage126_validation_architecture_boundary_decision.json"
F_BOUNDARY_MANIFEST = "stage126_historical_boundary_manifest.json"
F_REPORT = "stage126_current_state_validation_report.json"
F_METADATA = "metadata_and_hashes_stage126_current_state_validator.json"
F_README = "README_STAGE126_CURRENT_STATE_VALIDATION.md"
F_CLOSED_REGISTRY = "stage126_closed_part_registry.json"

# --------------------------------------------------------------------------- #
# Exact human governance decision (byte-for-byte Persian)
# --------------------------------------------------------------------------- #

HUMAN_DECISION_TEXT_FA = (
    "اره منم با این موافقم اینو اعمال کنیم از این نقطه به بعد Stage125 Part5 "
    "فقط historical و immutable است.\n"
    "وضعیت زنده فقط با validator مستقل Stage126 کنترل می‌شود.\n"
    "تغییر هر robustness part نباید باعث بازتولید artifactهای verification-only\n"
    "Partهای قبلی شود، مگر اینکه یک خطای علمی واقعی کشف شده باشد."
)
HUMAN_DECISION_TEXT_SHA256 = (
    "8231bbf8704d3128cce6a7f2cc40a33af8e7fe7730b2c4575997330cafb21ac1"
)
DECISION_DATE = "2026-07-23"

DECISION_AUTHORIZES: dict[str, bool] = {
    "stage126_validation_architecture_boundary_lock": True,
    "stage126_current_state_validator_creation": True,
    "historical_stage125_part5_freeze": True,
    "documentation_and_test_changes_required_for_this_boundary": True,
}
DECISION_DOES_NOT_AUTHORIZE: dict[str, bool] = {
    "merge": False,
    "part3_execution": False,
    "full_development_refit": False,
    "final_test_access": False,
    "final_test_evaluation": False,
    "new_scientific_execution": False,
}

# --------------------------------------------------------------------------- #
# Frozen Stage125 Part 5 historical boundary (hash-pinned; never executed)
# --------------------------------------------------------------------------- #

PART5_SOURCE_REL = "project/src/stage125_part5_readiness_closure.py"
PART5_RUNNER_REL = "project/run_stage125_part5.py"
PART5_TEST_REL = "project/tests/test_stage125_part5_readiness_closure.py"

PART5_SOURCE_SHA256 = (
    "cb61ea7c99b53f1988c22f5eac0af66af9cd9e46657a48bf66ccb198d654d41c"
)
PART5_RUNNER_SHA256 = (
    "ba6bd9e8e155e9cad71299e53806515caa1f95664bfcba0aebd20929f769e037"
)
PART5_TEST_SHA256 = (
    "0b9413b2adbf9c44b0fb12b4f7ef2dad60be5cd4c401ccefac30d19f0905af71"
)
STAGE125_TREE_REL = "project/stage125"

# Forward-looking prohibitions established by this decision.
BOUNDARY_PROHIBITIONS: dict[str, bool] = {
    "future_stage126_gate_may_execute_stage125_part5_runner": False,
    "future_stage126_gate_may_import_stage125_part5_validator": False,
    "future_stage126_gate_may_call_validate_actual_handoff_from_part5": False,
    "future_robustness_part_may_modify_part5_test": False,
    "future_robustness_part_may_regenerate_stage125_part5_outputs": False,
}

# The historical Part 5 runner behaviour is retained as PROVENANCE ONLY. It is
# no longer a required live Stage126 gate and is never executed by this module.
PART5_HISTORICAL_PROVENANCE: dict[str, Any] = {
    "full_runner_exit_code": 1,
    "first_failure_code": "readiness_surface_disagreement",
    "direct_validate_actual_handoff_mismatch_fields": [
        "m1_robustness_started",
        "selected_qc_scope",
        "selected_qc_path",
        "contract_version",
        "last_completed_micro_part",
    ],
    "status": "historical_provenance_only",
    "is_required_live_stage126_gate": False,
    "executed_by_this_validator": False,
}

# Coupling the validator must never re-acquire to the frozen Part 5 surface.
# Detected structurally (AST), never by substring matching — the names below
# necessarily appear in this file as data, and a substring scan would both
# false-positive here and be trivially defeated elsewhere.
FORBIDDEN_PART5_MODULE_FRAGMENT = "stage125_part5"
FORBIDDEN_PART5_CALL_NAMES: tuple[str, ...] = (
    "validate_actual_handoff",
)
FORBIDDEN_PART5_RUNNER_FRAGMENT = "run_stage125_part5"


def part5_coupling_findings(source_text: str) -> list[str]:
    """Structural proof that this module neither imports nor invokes Part 5.

    Walks the AST for (a) any import of the frozen Part 5 module, (b) any call
    to its live-successor validator, and (c) any subprocess invocation naming
    the Part 5 runner. String literals that merely mention those names — such
    as the documentation this module emits — are correctly ignored.
    """
    import ast
    findings: list[str] = []
    tree = ast.parse(source_text)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if FORBIDDEN_PART5_MODULE_FRAGMENT in alias.name:
                    findings.append(f"import:{alias.name}")
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if FORBIDDEN_PART5_MODULE_FRAGMENT in mod:
                findings.append(f"import_from:{mod}")
            for alias in node.names:
                if FORBIDDEN_PART5_MODULE_FRAGMENT in alias.name:
                    findings.append(f"import_from_name:{alias.name}")
        elif isinstance(node, ast.Call):
            func = node.func
            name = (
                func.attr if isinstance(func, ast.Attribute)
                else func.id if isinstance(func, ast.Name) else ""
            )
            if name in FORBIDDEN_PART5_CALL_NAMES:
                findings.append(f"call:{name}")
            if name in ("run", "Popen", "check_output", "call"):
                for arg in ast.walk(node):
                    if (isinstance(arg, ast.Constant)
                            and isinstance(arg.value, str)
                            and FORBIDDEN_PART5_RUNNER_FRAGMENT in arg.value):
                        findings.append(f"subprocess_runner:{arg.value}")
    return sorted(set(findings))

# --------------------------------------------------------------------------- #
# Stage126-native contracts (immutable, hash-pinned)
# --------------------------------------------------------------------------- #

PART0_DECISION_RECORD_REL = (
    "project/stage126/stage126_m1_robustness_part0_decision_record.json"
)
PART0_DECISION_RECORD_SHA256 = (
    "9ccd7bfae8fa522cb87e94ed7bebe806324837e9a2e12783d12aabfedd07c2ee"
)
PRIMARY_DEVELOPMENT_LOCK_REL = (
    "project/stage126/stage126_m1_primary_development_lock.json"
)
SELECTED_CONFIGURATIONS_REL = (
    "project/stage126/stage126_m1_selected_configurations.json"
)
FINAL_TEST_LOCK_GUARD_REL = (
    "project/stage126/stage126_m1_final_test_lock_guard.json"
)

PINNED_PRIMARY_ARTIFACTS: dict[str, str] = {
    "project/stage126/stage126_m1_development_access_manifest.csv":
        "0c2783d0e43ebba712a1c41b6889a2f8f646340bae6a75ad15902a8a0c368e39",
    "project/stage126/stage126_m1_development_oof_predictions.csv":
        "48a00c882309c412aeba8f3b7200b65003e435080410c7b7c7ab62c9c3326749",
    "project/stage126/stage126_m1_development_metrics.csv":
        "1c5f33b4e3a156b111d29a2c4e13ecee9c5e7ad73f6b3d98cf3c6b4b506be17a",
    PRIMARY_DEVELOPMENT_LOCK_REL:
        "c500563049e30a27ac59fd3d673ef801b8d8e12f0bb684dd2e0aec13eb5618e4",
    FINAL_TEST_LOCK_GUARD_REL:
        "509e58fc39e3c5d886993c11b954fc06c267c96d02c081d8e50b0cda52e58b03",
    SELECTED_CONFIGURATIONS_REL:
        "34488e07bd16d467b177c37dcaf571d9c68c25ecbc1c94fee5091f554d2eb97e",
    "project/stage126/stage126_m1_configuration_registry.csv":
        "decbf43a5c34669bdd7a0c68c0ad6aec5611efc7c3ca82b09f5e85f72d635804",
    "project/stage126/stage126_m1_tuning_results.csv":
        "e7e1e6808e394273676709aa94bfa713bbf8a790fadabee22ea20b849adbe649",
}

# --------------------------------------------------------------------------- #
# Per-part scientific artifacts — CLOSED historical micro-part packages
#
# Verification-only artifacts (QC report, metadata manifest, Part 5
# compatibility record, README) are deliberately NOT pinned here: they are the
# part's own bookkeeping. What is pinned — and what may never drift — is the
# SCIENTIFIC surface of every completed part.
# --------------------------------------------------------------------------- #

PART_SCIENTIFIC_SUFFIXES: tuple[str, ...] = (
    "human_authorization_record.json",
    "feature_manifest.csv",
    "execution_manifest.json",
    "oof_predictions.csv",
    "metrics.csv",
    "primary_comparison.json",
    "completion_lock.json",
    # Emitted only by parts whose changed dimension is the sample.
    "sample_delta.csv",
    # Emitted only by Part 6, whose changed dimension is the imbalance
    # strategy: the per-fold SMOTENC before/after resampling counts.
    "resampling_audit.csv",
)

# The sixth and final registered M1 robustness category: the ONLY category
# whose changed dimension is the imbalance strategy (SMOTENC applied strictly
# inside each training fold; every other category is a non-SMOTE scientific
# execution).
SMOTE_ROBUSTNESS_CATEGORY_ID = "smote_training_fold_only_robustness"
# Verification-only bookkeeping. The governance decision forbids regenerating
# these for a CLOSED part, so they are pinned exactly like the scientific
# surface — by the closed-part registry, not by a per-part constant.
PART_VERIFICATION_SUFFIXES: tuple[str, ...] = (
    "qc_report.json",
    "part5_successor_compatibility.json",
)


def part_file_prefix(part_index: int) -> str:
    """Naming convention shared by every robustness micro-part package."""
    return f"stage126_m1_robustness_part{part_index}"


def part_package_files(repo_root: Path, part_index: int) -> dict[str, dict[str, str]]:
    """Discover a micro-part's COMPLETE package by convention.

    Returns ``{"scientific": {...}, "verification": {...}, "code": {...}}`` with
    repository-relative paths mapped to SHA-256. Nothing here is part-specific:
    a future Part 3 is discovered by the same rules, with no source change.
    """
    prefix = part_file_prefix(part_index)
    stage_dir = repo_root / STAGE126_DIR_REL

    scientific: dict[str, str] = {}
    for suffix in PART_SCIENTIFIC_SUFFIXES:
        rel = f"{STAGE126_DIR_REL}/{prefix}_{suffix}"
        if (repo_root / rel).is_file():
            scientific[rel] = sha256_file(repo_root / rel)

    verification: dict[str, str] = {}
    for suffix in PART_VERIFICATION_SUFFIXES:
        rel = f"{STAGE126_DIR_REL}/{prefix}_{suffix}"
        if (repo_root / rel).is_file():
            verification[rel] = sha256_file(repo_root / rel)
    meta_rel = f"{STAGE126_DIR_REL}/metadata_and_hashes_{prefix}.json"
    if (repo_root / meta_rel).is_file():
        verification[meta_rel] = sha256_file(repo_root / meta_rel)
    readme_prefix = f"README_{prefix.upper()}"
    for path in sorted(stage_dir.glob("README_*.md")):
        if path.name.upper().startswith(readme_prefix):
            rel = f"{STAGE126_DIR_REL}/{path.name}"
            verification[rel] = sha256_file(path)

    code: dict[str, str] = {}
    for directory, pattern in (
        ("project/src", f"{prefix}_*.py"),
        ("project", f"run_{prefix}_*.py"),
        ("project/tests", f"test_{prefix}_*.py"),
    ):
        base = repo_root / directory
        if not base.is_dir():
            continue
        for path in sorted(base.glob(pattern)):
            rel = f"{directory}/{path.name}"
            code[rel] = sha256_file(path)

    return {
        "scientific": dict(sorted(scientific.items())),
        "verification": dict(sorted(verification.items())),
        "code": dict(sorted(code.items())),
    }


def derive_micro_part_id(repo_root: Path, part_index: int, lock: dict[str, Any]) -> str:
    """Deterministic micro-part identifier for a completed part.

    Contract, in order: the completion lock's own ``micro_part_id``; otherwise
    the part QC report's ``stage`` with underscores replaced by hyphens. Never a
    hard-coded per-part string. Fails closed when neither surface supplies one.
    """
    declared = lock.get("micro_part_id")
    if isinstance(declared, str) and declared:
        return declared
    qc_rel = f"{STAGE126_DIR_REL}/{part_file_prefix(part_index)}_qc_report.json"
    if (repo_root / qc_rel).is_file():
        stage = (_read_json(repo_root, qc_rel).get("stage") or "")
        if stage:
            return stage.replace("_", "-")
    raise ValidationFail(
        f"cannot derive a micro-part identifier for part {part_index} "
        f"(no micro_part_id in the completion lock and no QC stage)"
    )


HANDOFF_STATE_REL = "project/docs/ai/handoff_state.json"
CURRENT_STATE_MD_REL = "project/docs/ai/CURRENT_STATE.md"
#: The historical Stage127 D0 Gate outcome. It is a HISTORICAL record: the
#: Stage128 D2 design freeze amends only the equity-return measurement
#: component for FUTURE Gate execution and must never rewrite this to PASS.
STAGE127_HISTORICAL_D0_GATE_STATUS = "FAIL_M2_DATA_GATE"

# Architecture fields the live Handoff MUST carry, enforced inside
# verify_handoff() itself (not merely reported).
REQUIRED_HANDOFF_ARCHITECTURE_FIELDS: dict[str, Any] = {
    "validation_architecture": VALIDATION_ARCHITECTURE,
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
# Current-state validation pointers (distinct from the last scientific
# micro-part QC — the two roles must never share one ambiguous field).
CURRENT_STATE_QC_SCOPE = VALIDATOR_ID
CURRENT_STATE_QC_PATH = f"{STAGE126_DIR_REL}/{F_REPORT}"
CURRENT_STATE_QC_METADATA_PATH = f"{STAGE126_DIR_REL}/{F_METADATA}"

# Research-action pointers. These are properties of the Stage126 research action
# itself, not of how many robustness micro-parts have completed — a micro-part
# never advances them, so they are stable across Parts 1-6.
ACTIVE_WORKSTREAM = "stage126_m1_financial_baseline"
#: The canonical Stage128 workstream identifier. It is DERIVED FROM the already
#: frozen action `stage128-m2-boundary-month-return-design-freeze` and names the
#: M2 D2 boundary-month equity-return workstream that action opened; it is NOT a
#: new scientific action and it never replaces a research-action id. The
#: authoritative research-action pointers remain
#: `stage128-m2-boundary-month-return-design-freeze` (last completed) and
#: `stage128-m2-d2-gate-rerun` (next, unauthorized).
STAGE128_ACTIVE_WORKSTREAM = "stage128_m2_d2_boundary_month_equity_return"
#: `current_stage` once the Stage128 D2 design freeze is complete. Before it,
#: the live stage label remains the Stage126 M1 baseline.
STAGE126_CURRENT_STAGE = "Stage126"
STAGE128_CURRENT_STAGE = "Stage128"
NEXT_RESEARCH_ACTION_ID = "stage126-m1-financial-baseline"
# Once all six registered M1 robustness categories are complete (Part 6
# closes the set), the next legitimate ROADMAP research action advances to
# the synthesis/closure milestone. This is a truthful state transition, not a
# per-part advance: it fires exactly once, when m1_robustness_completed
# becomes True, and does not itself authorize retained-design freeze,
# full-development refit or final-test access.
NEXT_RESEARCH_ACTION_ID_AFTER_M1_ROBUSTNESS = "stage126-m1-robustness-closure"
# Once the (synthesis-only) M1 robustness closure itself has also completed,
# the next legitimate ROADMAP research action advances once more, to the
# retained-design-freeze milestone. That milestone still requires a SEPARATE,
# future, explicit human authorization -- this validator never grants it.
NEXT_RESEARCH_ACTION_ID_AFTER_ROBUSTNESS_CLOSURE = (
    "stage126-m1-retained-design-freeze"
)
ROBUSTNESS_CLOSURE_LOCK_REL = (
    f"{STAGE126_DIR_REL}/stage126_m1_robustness_closure_completion_lock.json"
)


def robustness_closure_completed(repo_root: Path) -> bool:
    """Narrow, fail-closed recognition of the M1 robustness closure.

    Mirrors the existing per-part completion-lock recognition pattern: only
    returns True when the closure completion lock exists and its exact
    required fields hold. Never itself authorizes retained-design freeze.
    """
    path = repo_root / ROBUSTNESS_CLOSURE_LOCK_REL
    if not path.is_file():
        return False
    try:
        lock = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    required = {
        "robustness_closure_completed": True,
        "all_six_registered_categories_verified": True,
        "paper_winner_selected": False,
        "retained_design_selected": False,
        "retained_design_freeze_authorized": False,
        "final_test_unlocked": False,
    }
    return all(lock.get(k) == v for k, v in required.items())


# Once the retained-design freeze itself has also completed, the next
# legitimate ROADMAP research action advances once more, to the M2
# market-data gate. That gate still requires a SEPARATE, future, explicit
# human authorization -- this validator never grants it, and never marks
# M2 as started.
NEXT_RESEARCH_ACTION_ID_AFTER_RETAINED_DESIGN_FREEZE = (
    "stage127-m2-market-data-gate"
)
RETAINED_DESIGN_FREEZE_REL = (
    f"{STAGE126_DIR_REL}/stage126_m1_retained_design_freeze.json"
)


def retained_design_freeze_completed(repo_root: Path) -> bool:
    """Narrow, fail-closed recognition of the M1 retained-design freeze.

    Mirrors ``robustness_closure_completed`` above: only returns True when
    the freeze artifact exists and its exact required ``status_flags`` hold.
    Never itself authorizes M2, a full-development refit or final-test access.
    """
    path = repo_root / RETAINED_DESIGN_FREEZE_REL
    if not path.is_file():
        return False
    try:
        freeze = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if freeze.get("decision_id") != "stage126-m1-retained-design-freeze":
        return False
    sf = freeze.get("status_flags") or {}
    required = {
        "retained_design_freeze_completed": True,
        "paper_winner_selected": False,
        "final_model_selected": False,
        "full_development_refit_performed": False,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_evaluation_performed": False,
        "m2_started": False,
    }
    return all(sf.get(k) == v for k, v in required.items())


# Once the Stage127 M2 market-data Gate has ALSO been executed and the
# Stage128 M2 D2 boundary-month design freeze completes on top of it, the
# next legitimate ROADMAP research action advances once more, to the D2 Gate
# re-run. That action still requires a SEPARATE, future, explicit human
# authorization -- this validator never grants it, and never marks M2 as
# admitted or started. An UNRESOLVED/FAIL Gate result is unaffected: the
# freeze amends only the D0 equity-return measurement component for FUTURE
# Gate execution and never rewrites the historical Gate outcome.
NEXT_RESEARCH_ACTION_ID_AFTER_STAGE128_M2_D2_DESIGN_FREEZE = (
    "stage128-m2-d2-gate-rerun"
)
STAGE128_M2_D2_DESIGN_FREEZE_REL = (
    "project/stage128/stage128_m2_d2_design_freeze.json"
)


def stage128_m2_d2_design_freeze_completed(repo_root: Path) -> bool:
    """Narrow, fail-closed recognition of the Stage128 M2 D2 design freeze.

    Mirrors ``retained_design_freeze_completed`` above: only returns True
    when the freeze artifact exists and its exact required
    ``status_flags``/no-execution fields hold, and the historical Stage127
    D0 Gate result is preserved. Never itself authorizes a Gate re-run, M2
    admission or final-test access.
    """
    path = repo_root / STAGE128_M2_D2_DESIGN_FREEZE_REL
    if not path.is_file():
        return False
    try:
        freeze = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if freeze.get("decision_id") != (
        "stage128-m2-boundary-month-return-design-freeze"
    ):
        return False
    if freeze.get("historical_D0_gate_status") != "FAIL_M2_DATA_GATE":
        return False
    sf = freeze.get("status_flags") or {}
    required_status_flags = {
        "design_freeze_completed": True,
        "canonical_gate_executed": False,
        "m2_admitted": False,
        "m2_started": False,
        "m3_started": False,
        "m4_started": False,
        "final_model_selected": False,
        "paper_winner_selected": False,
        "merged": False,
    }
    if not all(sf.get(k) == v for k, v in required_status_flags.items()):
        return False
    required_exact = {
        "canonical_gate_executed_in_this_action": False,
        "M2_admitted_in_this_action": False,
        "model_fits": 0,
        "predictions": 0,
        "final_test_access": 0,
        "target_values_accessed": 0,
        "stage128_m2_d2_gate_rerun_authorized": False,
    }
    return all(freeze.get(k) == v for k, v in required_exact.items())


STAGE128_M3_ACTIVE_WORKSTREAM = "stage128_m3_macro_data_gate"

_STAGE128_M3_GATE_DECISION_REL = (
    "project/stage128/m3_macro_data_gate/"
    "stage128_m3_macro_data_gate_decision.json"
)


def stage128_m3_macro_data_gate_executed(repo_root: Path) -> bool:
    """True once the M3 macro DATA Gate has been executed.

    Gate execution is a DATA workstream event, never modeling. Fail closed if
    the artifact contradicts the no-modeling invariants.
    """
    path = repo_root / _STAGE128_M3_GATE_DECISION_REL
    if not path.is_file():
        return False
    decision = json.loads(path.read_text(encoding="utf-8"))
    if decision.get("action_id") != "stage128-m3-macro-data-gate":
        raise ValidationFail("stage128 M3 Gate decision action_id mismatch")
    if not decision.get("m3_macro_data_gate_executed"):
        return False
    for field, expected in (
        ("m3_modeling_started", False),
        ("m3_incremental_evaluation_authorized", False),
        ("m4_authorized", False),
        ("m4_started", False),
        ("final_test_locked", True),
    ):
        if decision.get(field) is not expected:
            raise ValidationFail(
                f"stage128 M3 Gate executed but {field} != {expected}")
    return True


#: The live workstream once the supplementary M3I-2 contract has been
#: prospectively locked. The lock is a CONTRACT event: no macro observation is
#: retrieved, no Data Gate is executed and no modeling starts.
STAGE128_M3I2_ACTIVE_WORKSTREAM = "stage128_m3i2_prospective_contract_lock"

STAGE128_M3I2_ACTION_ID = "stage128-m3i2-prospective-contract-lock"
STAGE128_M3I2_CONTRACT_STATUS = "PROSPECTIVELY_LOCKED_NO_DATA"
NEXT_RESEARCH_ACTION_ID_AFTER_M3I2_CONTRACT_LOCK = (
    "stage128-m3i2-official-source-evidence-capture"
)

_STAGE128_M3I2_DECISION_REL = (
    "project/stage128/m3_intl_macro_contract_lock/"
    "stage128_m3_intl_macro_contract_decision.json"
)


def stage128_m3i2_contract_lock_completed(repo_root: Path) -> bool:
    """True once the supplementary M3I-2 contract has been locked.

    A contract lock is metadata only. Fail closed if the artifact claims data
    retrieval, Gate execution, modeling, M4, final-test access or a merge.
    """
    path = repo_root / _STAGE128_M3I2_DECISION_REL
    if not path.is_file():
        return False
    decision = json.loads(path.read_text(encoding="utf-8"))
    if decision.get("action_id") != STAGE128_M3I2_ACTION_ID:
        raise ValidationFail("stage128 M3I-2 contract-lock action_id mismatch")
    if not decision.get("m3i2_contract_lock_executed"):
        return False
    if decision.get("m3i2_contract_status") != STAGE128_M3I2_CONTRACT_STATUS:
        raise ValidationFail(
            "stage128 M3I-2 contract status must be "
            f"{STAGE128_M3I2_CONTRACT_STATUS}")
    for field, expected in (
        ("m3i2_retrieval_started", False),
        ("m3i2_data_gate_executed", False),
        ("m3i2_block_admitted", False),
        ("m3i2_incremental_evaluation_authorized", False),
        ("m3i2_modeling_started", False),
        ("m3i3_admitted", False),
        ("m3_cbi_contract_changed", False),
        ("m4_authorized", False),
        ("m4_started", False),
        ("final_test_locked", True),
        ("merge_authorized", False),
        ("data_collection_started", False),
    ):
        if decision.get(field) is not expected:
            raise ValidationFail(
                f"stage128 M3I-2 contract lock {field} != {expected}")
    for field in ("network_requests", "macro_observations_read",
                  "model_fits", "predictions", "coverage_calculations",
                  "holm_calculations"):
        if decision.get(field) != 0:
            raise ValidationFail(
                f"stage128 M3I-2 contract lock {field} must be 0")
    # The frozen CBI block is preserved, never replaced by the supplementary
    # international family.
    if decision.get("m3_cbi_gate_status") != "UNRESOLVED_M3_DATA_GATE":
        raise ValidationFail(
            "stage128 M3I-2 contract lock must preserve the M3-CBI Gate status")
    _assert_m3i2_live_topology(decision)
    return True


STAGE128_M3I2_EVIDENCE_ACTION_ID = (
    "stage128-m3i2-official-source-evidence-capture")
STAGE128_M3I2_EVIDENCE_ACTIVE_WORKSTREAM = (
    "stage128_m3i2_official_source_evidence_capture")
_STAGE128_M3I2_EVIDENCE_DECISION_REL = (
    "project/stage128/m3i2_official_source_evidence_capture/"
    "stage128_m3i2_official_source_evidence_decision.json")
STAGE128_M3I2_EVIDENCE_STATUSES = (
    "EVIDENCE_COMPLETE_FOR_SEPARATE_M3I2_DATA_GATE_REVIEW",
    "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE",
    "INVALID_OFFICIAL_SOURCE_EVIDENCE_CAPTURE",
)


def stage128_m3i2_evidence_capture_completed(repo_root: Path) -> bool:
    """True once the M3I-2 official-source evidence capture has been recorded.

    Evidence capture is NOT a Data Gate: it retrieves and hashes official
    source material and says nothing about coverage or admission. This
    recognizer therefore fails closed on any artifact that claims otherwise.
    """
    path = repo_root / _STAGE128_M3I2_EVIDENCE_DECISION_REL
    if not path.is_file():
        return False
    decision = json.loads(path.read_text(encoding="utf-8"))
    if decision.get("action_id") != STAGE128_M3I2_EVIDENCE_ACTION_ID:
        raise ValidationFail("stage128 M3I-2 evidence-capture action_id mismatch")
    status = decision.get("m3i2_official_source_evidence_status")
    if status not in STAGE128_M3I2_EVIDENCE_STATUSES:
        raise ValidationFail(
            f"unknown M3I-2 evidence status {status!r}")
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
        if decision.get(field) is not expected:
            raise ValidationFail(
                f"stage128 M3I-2 evidence capture {field} != {expected}")
    for field in ("company_macro_joins", "feature_materializations",
                  "coverage_calculations", "data_gate_executions",
                  "model_fits", "predictions", "predictive_metrics",
                  "holm_calculations", "final_test_rows_read"):
        if decision.get(field) != 0:
            raise ValidationFail(
                f"stage128 M3I-2 evidence capture {field} must be 0")
    if decision.get("m3_cbi_status") != "UNRESOLVED_M3_DATA_GATE":
        raise ValidationFail(
            "the M3I-2 evidence capture must preserve the M3-CBI Gate status")
    if decision.get("m3i3_lock_status") != "UNRESOLVED_METADATA_LOCK":
        raise ValidationFail(
            "M3I-3 must remain UNRESOLVED_METADATA_LOCK")
    return True


STAGE128_M3I2_RECOVERY_ACTION_ID = (
    "stage128-m3i2-final-official-documentary-recovery-initiation")
STAGE128_M3I2_RECOVERY_ACTIVE_WORKSTREAM = (
    "stage128_m3i2_final_official_documentary_recovery")
_STAGE128_M3I2_RECOVERY_DECISION_REL = (
    "project/stage128/m3i2_final_official_documentary_recovery/"
    "stage128_m3i2_final_official_documentary_recovery_decision.json")
STAGE128_M3I2_RECOVERY_INITIATION_STATUSES = (
    "OFFICIAL_INQUIRY_SUBMITTED_PENDING_RESPONSE",
    "HUMAN_SUBMISSION_REQUIRED",
)


def stage128_m3i2_final_documentary_recovery_initiated(repo_root: Path) -> bool:
    """True once the M3I-2 final official documentary recovery is recorded.

    The action is an INITIATION: a bounded official documentary search plus at
    most one prepared inquiry. It admits nothing, executes no Data Gate and
    never contract-locks M3-LAG-WDI, so this recognizer fails closed on any
    artifact that claims otherwise.
    """
    path = repo_root / _STAGE128_M3I2_RECOVERY_DECISION_REL
    if not path.is_file():
        return False
    decision = json.loads(path.read_text(encoding="utf-8"))
    if decision.get("action_id") != STAGE128_M3I2_RECOVERY_ACTION_ID:
        raise ValidationFail("stage128 M3I-2 recovery action_id mismatch")
    status = decision.get("initiation_status")
    if status not in STAGE128_M3I2_RECOVERY_INITIATION_STATUSES:
        raise ValidationFail(
            f"unknown M3I-2 recovery initiation status {status!r}")
    for field, expected in (
        ("m3i2_admitted", False),
        ("m3i2_data_gate_executed", False),
        ("m3i2_modeling_started", False),
        ("m3_lag_wdi_exploratory_contract_locked", False),
        ("m3_lag_wdi_data_retrieval_started", False),
        ("final_test_locked", True),
        ("m4_authorized", False),
        ("merge_authorized", False),
        ("next_research_action_authorized", False),
    ):
        if decision.get(field) is not expected:
            raise ValidationFail(
                f"stage128 M3I-2 recovery {field} != {expected}")
    if decision.get("m3_lag_wdi_authoritative_contract_status") != "NOT_LOCKED":
        raise ValidationFail("M3-LAG-WDI must remain NOT_LOCKED")
    if decision.get("m3i2_evidence_status") != (
            "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE"):
        raise ValidationFail(
            "the M3I-2 recovery initiation must preserve the unresolved "
            "official-source evidence status")
    if decision.get("m3_cbi_status") != "UNRESOLVED_M3_DATA_GATE":
        raise ValidationFail(
            "the M3I-2 recovery must preserve the M3-CBI Gate status")
    if decision.get("m3i3_lock_status") != "UNRESOLVED_METADATA_LOCK":
        raise ValidationFail(
            "M3I-3 must remain UNRESOLVED_METADATA_LOCK")
    return True


STAGE128_M3I2_INQUIRY_SUBMISSION_ACTION_ID = (
    "stage128-m3i2-final-official-inquiry-human-submission")
_STAGE128_M3I2_INQUIRY_SUBMISSION_DECISION_REL = (
    "project/stage128/m3i2_final_official_inquiry_human_submission/"
    "stage128_m3i2_final_official_inquiry_submission_decision.json")
STAGE128_M3I2_INQUIRY_SUBMITTED_STATUS = (
    "SUBMITTED_ACKNOWLEDGED_WAITING_FOR_SUBSTANTIVE_RESPONSE")
#: 10 business days, Mon-Fri, submission day excluded, holidays not modeled.
STAGE128_M3I2_INQUIRY_SUBMISSION_CALENDAR_DATE = "2026-08-06"
STAGE128_M3I2_INQUIRY_WAITING_PERIOD_COMPLETION_DATE = "2026-08-20"
STAGE128_M3I2_INQUIRY_FOLLOW_UP_EARLIEST_DATE = "2026-08-21"


def stage128_m3i2_inquiry_human_submission_recorded(repo_root: Path) -> bool:
    """True once the HUMAN submission of the M3I-2 inquiry has been recorded.

    The recording is sanitized and governance-only: a human submitted the
    prepared inquiry exactly once, an acknowledgement came back, and that is
    all. It admits nothing, resolves neither blocker, executes no Data Gate and
    authorizes no follow-up, so this recognizer fails closed on any artifact
    that claims otherwise.
    """
    path = repo_root / _STAGE128_M3I2_INQUIRY_SUBMISSION_DECISION_REL
    if not path.is_file():
        return False
    decision = json.loads(path.read_text(encoding="utf-8"))
    if decision.get("action_id") != STAGE128_M3I2_INQUIRY_SUBMISSION_ACTION_ID:
        raise ValidationFail("stage128 M3I-2 inquiry submission action_id "
                             "mismatch")
    if decision.get("submission_status") != (
            STAGE128_M3I2_INQUIRY_SUBMITTED_STATUS):
        raise ValidationFail(
            "the recorded M3I-2 inquiry submission status must be "
            f"{STAGE128_M3I2_INQUIRY_SUBMITTED_STATUS}")
    for field, expected in (
        ("m3i2_admitted", False),
        ("archive_release_blocker_resolved", False),
        ("fx_semantic_continuity_blocker_resolved", False),
        ("final_test_locked", True),
        ("m4_authorized", False),
        ("merge_authorized", False),
        ("next_research_action_authorized", False),
    ):
        if decision.get(field) is not expected:
            raise ValidationFail(
                f"stage128 M3I-2 inquiry submission {field} != {expected}")
    if decision.get("m3i2_evidence_status") != (
            "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE"):
        raise ValidationFail(
            "an acknowledged inquiry is not evidence: M3I-2 must stay "
            "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE")
    if decision.get("m3_lag_wdi_authoritative_contract_status") != "NOT_LOCKED":
        raise ValidationFail("M3-LAG-WDI must remain NOT_LOCKED")
    if decision.get("m3_cbi_status") != "UNRESOLVED_M3_DATA_GATE":
        raise ValidationFail(
            "the M3I-2 inquiry submission must preserve the M3-CBI Gate "
            "status")
    if decision.get("data_gate_status") != "NOT_EXECUTED":
        raise ValidationFail("the Data Gate must remain NOT_EXECUTED")
    if decision.get("verified_wdi_release_dates") != 0 or decision.get(
            "verified_pre_cutoff_editions") != 0:
        raise ValidationFail(
            "an acknowledgement verifies no release date and no edition")
    if decision.get("unresolved_cutoffs") != decision.get(
            "unresolved_cutoffs_total"):
        raise ValidationFail("every cutoff must remain unresolved")
    if decision.get("unresolved_development_pairs") != decision.get(
            "unresolved_development_pairs_total"):
        raise ValidationFail("every development pair must remain unresolved")
    if decision.get("waiting_period_status") != "ACTIVE":
        raise ValidationFail("the M3I-2 inquiry waiting period must be ACTIVE")
    if decision.get("waiting_period_completion_date") != (
            STAGE128_M3I2_INQUIRY_WAITING_PERIOD_COMPLETION_DATE):
        raise ValidationFail(
            "10 business days from "
            f"{STAGE128_M3I2_INQUIRY_SUBMISSION_CALENDAR_DATE} complete on "
            f"{STAGE128_M3I2_INQUIRY_WAITING_PERIOD_COMPLETION_DATE}")
    return True


# --------------------------------------------------------------------------- #
# Stage128 — Track B: the M3-LAG-WDI-EXPLORATORY contract lock
# --------------------------------------------------------------------------- #

_STAGE128_M3_LAG_PKG = "project/stage128/m3_lag_wdi_exploratory_contract_lock"
STAGE128_M3_LAG_ACTION_ID = "stage128-m3-lag-wdi-exploratory-contract-lock"
_STAGE128_M3_LAG_CONTRACT_REL = (
    f"{_STAGE128_M3_LAG_PKG}/stage128_m3_lag_wdi_exploratory_contract.json")
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
_STAGE128_M3_LAG_TOPOLOGY_REL = (
    f"{_STAGE128_M3_LAG_PKG}/stage128_m3_lag_wdi_exploratory_pr_topology.json")

STAGE128_M3_LAG_LOCKED_STATUS = "AUTHORITATIVE_CONTRACT_LOCKED_PRE_RETRIEVAL"
STAGE128_M3_LAG_ROLE = "supplementary_exploratory_robustness_block"
STAGE128_M3_LAG_CPI_CODE = "FP.CPI.TOTL.ZG"
STAGE128_M3_LAG_FX_CODE = "PA.NUS.FCRF"
STAGE128_M3_LAG_FX_FORMULA = "FX_LAG1_t = 100 * ln(E_y / E_(y-1))"
STAGE128_M3_LAG_FX_FORMULA_EQUIVALENT = "100 * ln(E_(t-1) / E_(t-2))"
STAGE128_M3_LAG_PARENT_ROWS = 539
STAGE128_M3_LAG_M2_FEATURES = 12
STAGE128_M3_LAG_TOTAL_FEATURES = 14
STAGE128_M3_LAG_CONFIRMATORY_FAMILY = (
    "M2_minus_M1", "M3_CBI_minus_M2", "M4_minus_M3_CBI")
STAGE128_M3_LAG_WAITING_PERIOD_COMPLETION_DATE = "2026-08-20"
STAGE128_M3_LAG_EARLIEST_FOLLOW_UP_DATE = "2026-08-21"
#: PR #77 (the M3I-2 human-submission recording) was merged into main by this
#: commit, and is therefore historical, not the live Draft.
STAGE128_M3_LAG_MERGED_PREDECESSOR_PR = 77
STAGE128_M3_LAG_MERGED_PREDECESSOR_COMMIT = (
    "93de6bae9344ce893b0261f818abce8a991cf842")

#: HISTORICAL PR ROLES — pinned facts. PR #76 carried the final official
#: documentary recovery INITIATION; PR #77 carried the later HUMAN inquiry
#: submission RECORDING. Two different actions, two different PRs, two
#: different merge commits. "The recovery PR" is a name for the first of them,
#: never a moving label for "whatever merged most recently", so re-anchoring
#: the live topology onto a newer Draft may not shift either role.
STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR = 76
STAGE128_M3I2_DOCUMENTARY_RECOVERY_MERGE_COMMIT = (
    "89d8e6ff2d12ec82903cd28aa7ab839eb946b658")
STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR_ROLE = (
    "final_official_documentary_recovery_initiation_pr")
STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR_SEMANTICS = (
    "merged_predecessor_superseded_by_pr77")
STAGE128_M3I2_HUMAN_SUBMISSION_PR = 77
STAGE128_M3I2_HUMAN_SUBMISSION_MERGE_COMMIT = (
    "93de6bae9344ce893b0261f818abce8a991cf842")
STAGE128_M3I2_HUMAN_SUBMISSION_PR_ROLE = (
    "final_official_inquiry_human_submission_recording_pr")

#: Track B's future actions. Each is SEPARATE, and each needs its own new
#: explicit human authorization: retrieving does not authorize the Gate, and a
#: Gate PASS is data admission only and does not authorize modeling.
STAGE128_M3_LAG_RETRIEVAL_ACTION_ID = (
    "stage128-m3-lag-wdi-exploratory-data-retrieval")
STAGE128_M3_LAG_POST_RETRIEVAL_AUDIT_ACTION_ID = (
    "stage128-m3-lag-wdi-exploratory-post-retrieval-audit")
STAGE128_M3_LAG_DATA_GATE_ACTION_ID = (
    "stage128-m3-lag-wdi-exploratory-data-gate")
STAGE128_M3_LAG_MODELING_ACTION_ID = (
    "stage128-m3-lag-wdi-exploratory-incremental-evaluation")
STAGE128_M3_LAG_NEXT_ACTION_SCOPE = "retrieval_only"
#: (step, action_id, executes_retrieval, executes_gate, executes_modeling)
STAGE128_M3_LAG_ACTION_SEQUENCE = (
    ("A", "stage128-m3-lag-wdi-exploratory-contract-lock", False, False, False),
    ("B", STAGE128_M3_LAG_RETRIEVAL_ACTION_ID, True, False, False),
    ("C", STAGE128_M3_LAG_POST_RETRIEVAL_AUDIT_ACTION_ID, False, False, False),
    ("D", STAGE128_M3_LAG_DATA_GATE_ACTION_ID, False, True, False),
    ("E", STAGE128_M3_LAG_MODELING_ACTION_ID, False, False, True),
)


def stage128_m3_lag_wdi_exploratory_contract_locked(repo_root: Path) -> bool:
    """True once the M3-LAG-WDI exploratory contract is authoritatively locked.

    A ``LOCKED`` status may exist ONLY if the authoritative contract still
    satisfies every frozen requirement: exploratory-only role, exactly the two
    lagged WDI features with their exact indicator codes and lag rules, the
    retained-M2 539-row parent sample, 12 M2 features against 14 M3-LAG-WDI
    features, the inherited Gate thresholds, the three frozen model families, a
    SEPARATE exploratory comparison family, no point-in-time claim, and zero
    retrieval / Gate / modeling / Final-Test execution — while the World Bank
    inquiry stays active and unresolved. Anything else raises, so the validator
    can never report a locked contract that has quietly drifted.
    """
    path = repo_root / _STAGE128_M3_LAG_CONTRACT_REL
    if not path.is_file():
        return False
    contract = _read_json(repo_root, _STAGE128_M3_LAG_CONTRACT_REL)
    boundary = _read_json(repo_root, _STAGE128_M3_LAG_BOUNDARY_REL)
    gate = _read_json(repo_root, _STAGE128_M3_LAG_GATE_REL)
    modeling = _read_json(repo_root, _STAGE128_M3_LAG_MODELING_REL)
    audit = _read_json(repo_root, _STAGE128_M3_LAG_AUDIT_REL)
    topology = _read_json(repo_root, _STAGE128_M3_LAG_TOPOLOGY_REL)

    if contract.get("action_id") != STAGE128_M3_LAG_ACTION_ID:
        raise ValidationFail("stage128 M3-LAG-WDI contract action_id mismatch")
    if contract.get("contract_status") != STAGE128_M3_LAG_LOCKED_STATUS:
        raise ValidationFail(
            "the M3-LAG-WDI contract status must be "
            f"{STAGE128_M3_LAG_LOCKED_STATUS}")

    # Exploratory only — never confirmatory, never a repair of M3-CBI.
    if contract.get("scientific_role") != STAGE128_M3_LAG_ROLE:
        raise ValidationFail(
            f"M3-LAG-WDI must stay a {STAGE128_M3_LAG_ROLE}")
    for field in ("is_confirmatory_m3", "is_replacement_for_m3_cbi",
                  "is_repair_of_m3_cbi",
                  "is_continuation_or_replacement_of_m3i2",
                  "in_original_confirmatory_holm_family",
                  "can_select_paper_winner_alone",
                  "proves_historical_point_in_time_wdi_availability",
                  "one_year_lag_establishes_point_in_time_availability",
                  "third_macro_feature_permitted",
                  "financing_rate_feature_permitted",
                  "indicator_search_permitted", "imputation_permitted"):
        if contract.get(field) is not False:
            raise ValidationFail(f"M3-LAG-WDI contract {field} must be False")

    # Exactly two features, exact identities, exact temporal rules.
    features = contract.get("features") or []
    if len(features) != 2 or contract.get(
            "additional_macro_feature_count") != 2:
        raise ValidationFail(
            "M3-LAG-WDI contains EXACTLY two additional macro features")
    cpi, fx = features
    if cpi.get("indicator_code") != STAGE128_M3_LAG_CPI_CODE:
        raise ValidationFail(
            f"the CPI indicator must be {STAGE128_M3_LAG_CPI_CODE}")
    if fx.get("indicator_code") != STAGE128_M3_LAG_FX_CODE:
        raise ValidationFail(
            f"the FX indicator must be {STAGE128_M3_LAG_FX_CODE}")
    for feature in features:
        if feature.get("country_code") != "IRN":
            raise ValidationFail("both M3-LAG-WDI features are for IRN")
        if feature.get("lag_years") != 1:
            raise ValidationFail("both M3-LAG-WDI features are lagged 1 year")
        if feature.get("same_year_t_observation_permitted") is not False:
            raise ValidationFail(
                "no same-year t observation is permitted")
    if cpi.get("observation_year_rule") != "t - 1":
        raise ValidationFail("the CPI observation year rule must be t - 1")
    if cpi.get("transformation") != "identity":
        raise ValidationFail("the CPI transformation must be the identity")
    if fx.get("observation_year_rule") != "y = t - 1":
        raise ValidationFail("the FX observation year rule must be y = t - 1")
    if fx.get("transformation") != STAGE128_M3_LAG_FX_FORMULA:
        raise ValidationFail(
            f"the FX transformation must be {STAGE128_M3_LAG_FX_FORMULA}")
    if fx.get("transformation_equivalent") != (
            STAGE128_M3_LAG_FX_FORMULA_EQUIVALENT):
        raise ValidationFail(
            "the FX transformation must equal "
            f"{STAGE128_M3_LAG_FX_FORMULA_EQUIVALENT}")
    if fx.get("required_observation_years") != ["t-1", "t-2"]:
        raise ValidationFail("FX requires exactly the t-1 and t-2 observations")

    # Sample and feature architecture.
    parent = contract.get("parent_sample") or {}
    if parent.get("expected_parent_rows") != STAGE128_M3_LAG_PARENT_ROWS:
        raise ValidationFail(
            "the parent sample is the retained-M2 "
            f"{STAGE128_M3_LAG_PARENT_ROWS}-row development sample")
    if parent.get("original_666_row_m1_comparison_sample_permitted") is not (
            False):
        raise ValidationFail(
            "the original 666-row M1 comparison sample may not be used")
    comparator = contract.get("m2_comparator") or {}
    if comparator.get("feature_count") != STAGE128_M3_LAG_M2_FEATURES:
        raise ValidationFail(
            f"the M2 comparator has {STAGE128_M3_LAG_M2_FEATURES} features")
    if contract.get("feature_count_total") != STAGE128_M3_LAG_TOTAL_FEATURES:
        raise ValidationFail(
            f"M3-LAG-WDI has {STAGE128_M3_LAG_TOTAL_FEATURES} features")
    complete_case = contract.get("complete_case_policy") or {}
    if complete_case.get("both_lagged_wdi_features_required_complete") is not (
            True):
        raise ValidationFail(
            "complete cases are required for BOTH lagged WDI features")
    if complete_case.get(
            "m2_and_m3_lag_wdi_refit_on_the_same_resulting_common_sample"
    ) is not True:
        raise ValidationFail(
            "M2 and M3-LAG-WDI must be refitted on the same common sample")
    if complete_case.get(
            "previous_666_row_m1_results_reusable_as_comparator") is not False:
        raise ValidationFail(
            "the previous 666-row M1 results are not a valid comparator")

    # WDI vintage semantics — the honest limitation must stay explicit.
    vintage = contract.get("wdi_vintage_semantics") or {}
    if vintage.get("current_or_latest_revised_wdi_allowed") is not True:
        raise ValidationFail(
            "the contract must state that current/latest revised WDI is used")
    for field in ("historical_vintage_availability_claimed",
                  "point_in_time_availability_claimed",
                  "lagging_transforms_revised_wdi_into_point_in_time_data"):
        if vintage.get(field) is not False:
            raise ValidationFail(f"WDI vintage semantics {field} must be False")

    # Inherited Data Gate thresholds, frozen and NOT executed.
    thresholds = gate.get("thresholds") or {}
    if thresholds.get("candidate_valid_coverage_min") != 0.8:
        raise ValidationFail("individual candidate coverage must be >= 0.80")
    if thresholds.get("block_common_sample_coverage_min") != 0.7:
        raise ValidationFail("block common-sample coverage must be >= 0.70")
    if thresholds.get(
            "minimum_positive_evaluable_each_locked_validation_window") != 5:
        raise ValidationFail(
            ">= 5 positive outcomes are required in EACH locked validation "
            "window")
    if gate.get("gate_executed") is not False or gate.get(
            "gate_result") != "NOT_EXECUTED":
        raise ValidationFail("the M3-LAG-WDI Data Gate must be NOT_EXECUTED")
    for name, value in (gate.get("observed_values") or {}).items():
        if value is not None:
            raise ValidationFail(
                f"observed Gate value {name} must stay null, not zero")

    # Three frozen model families, in a SEPARATE exploratory family.
    if list(modeling.get("model_families") or []) != [
            "regularized_logistic_regression", "random_forest", "xgboost"]:
        raise ValidationFail(
            "exactly the three retained M2 model families may be used")
    if modeling.get(
            "exploratory_comparison_inserted_into_confirmatory_holm_family"
    ) is not False:
        raise ValidationFail(
            "the exploratory comparison may never enter the confirmatory Holm "
            "family")
    if tuple(modeling.get("confirmatory_holm_family") or ()) != (
            STAGE128_M3_LAG_CONFIRMATORY_FAMILY):
        raise ValidationFail(
            "the confirmatory Holm family must stay "
            f"{list(STAGE128_M3_LAG_CONFIRMATORY_FAMILY)}")
    family_id = modeling.get("comparison_family_id")
    if not family_id or family_id in STAGE128_M3_LAG_CONFIRMATORY_FAMILY:
        raise ValidationFail(
            "the exploratory comparison needs its OWN family identity")

    # Zero execution, and a hard Final-Test firewall.
    for field in ("retrieval_started", "data_gate_executed",
                  "modeling_started",
                  "earlier_historical_vintage_bundle_used_as_value_input"):
        if audit.get(field) is not False:
            raise ValidationFail(f"M3-LAG-WDI {field} must be False")
    for field in ("final_test_rows_read", "final_test_predictor_values_read",
                  "final_test_target_values_read"):
        if audit.get(field) != 0:
            raise ValidationFail(f"M3-LAG-WDI {field} must be 0")
    for name, value in (audit.get("counters") or {}).items():
        if value != 0:
            raise ValidationFail(
                f"M3-LAG-WDI execution counter {name} must be 0")

    # Track A stays active: a parallel lock never terminates the inquiry.
    if boundary.get("world_bank_inquiry_status") != (
            STAGE128_M3I2_INQUIRY_SUBMITTED_STATUS):
        raise ValidationFail(
            "the World Bank inquiry must stay "
            f"{STAGE128_M3I2_INQUIRY_SUBMITTED_STATUS}")
    if boundary.get("world_bank_waiting_period_status") != "ACTIVE":
        raise ValidationFail("the World Bank waiting period must stay ACTIVE")
    if boundary.get("world_bank_waiting_period_completion_date") != (
            STAGE128_M3_LAG_WAITING_PERIOD_COMPLETION_DATE):
        raise ValidationFail(
            "the waiting period completes on "
            f"{STAGE128_M3_LAG_WAITING_PERIOD_COMPLETION_DATE}")
    if boundary.get(
            "world_bank_waiting_period_earliest_follow_up_date") != (
            STAGE128_M3_LAG_EARLIEST_FOLLOW_UP_DATE):
        raise ValidationFail(
            "the earliest possible follow-up stays "
            f"{STAGE128_M3_LAG_EARLIEST_FOLLOW_UP_DATE}")
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
                  "m4_authorized", "merge_authorized",
                  "final_test_access_authorized"):
        if boundary.get(field) is not False:
            raise ValidationFail(
                f"M3-LAG-WDI governance boundary {field} must be False")
    if boundary.get("final_test_locked") is not True:
        raise ValidationFail("the Final Test must stay locked")
    if boundary.get("m3_cbi_status") != "UNRESOLVED_M3_DATA_GATE":
        raise ValidationFail("the M3-CBI Gate status must be preserved")
    if boundary.get("m3i2_evidence_status") != (
            "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE"):
        raise ValidationFail("M3I-2 evidence must remain UNRESOLVED")
    if boundary.get("prior_restriction_retained_as_history") is not True:
        raise ValidationFail(
            "the superseded wait-only restriction must be retained as history")

    # A MERGED PR is never the live Draft.
    if topology.get("predecessor_pr_merged") is not True:
        raise ValidationFail(
            "the predecessor PR must be recorded as merged")
    if topology.get("live_pr_is_draft") is not True:
        raise ValidationFail("the M3-LAG-WDI PR must remain a Draft")
    if topology.get("live_pr_merged") is not False:
        raise ValidationFail("the M3-LAG-WDI PR must remain unmerged")
    if topology.get("merge_authorized") is not False:
        raise ValidationFail("no merge authorization exists for this PR")
    live_number = topology.get("live_pr_number")
    predecessor_number = topology.get("predecessor_pr_number")
    if not isinstance(live_number, int) or isinstance(live_number, bool):
        raise ValidationFail("the live PR number must be an integer")
    if not isinstance(predecessor_number, int) or isinstance(
            predecessor_number, bool):
        raise ValidationFail("the predecessor PR number must be an integer")
    # Pinning the merged predecessor is what stops a MERGED PR from being
    # re-rendered as the live Draft: "live > predecessor" alone would accept a
    # topology that promoted PR #77 back to live and demoted #76 in its place.
    if predecessor_number != STAGE128_M3_LAG_MERGED_PREDECESSOR_PR:
        raise ValidationFail(
            "the merged predecessor is PR "
            f"#{STAGE128_M3_LAG_MERGED_PREDECESSOR_PR}")
    if topology.get("predecessor_pr_merge_commit") != (
            STAGE128_M3_LAG_MERGED_PREDECESSOR_COMMIT):
        raise ValidationFail(
            f"PR #{STAGE128_M3_LAG_MERGED_PREDECESSOR_PR} was merged by "
            f"{STAGE128_M3_LAG_MERGED_PREDECESSOR_COMMIT}")
    if live_number <= predecessor_number:
        raise ValidationFail(
            f"the live PR #{live_number} must succeed the merged predecessor "
            f"PR #{predecessor_number}")
    if topology.get("live_pr_base_commit") != topology.get(
            "predecessor_pr_merge_commit"):
        raise ValidationFail(
            "the live PR base must equal the predecessor merge commit")

    # Historical PR roles are pinned facts, never re-derived from adjacency.
    for field, expected, label in (
        ("documentary_recovery_pr_number",
         STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR,
         "the documentary-recovery INITIATION PR"),
        ("documentary_recovery_pr_merge_commit",
         STAGE128_M3I2_DOCUMENTARY_RECOVERY_MERGE_COMMIT,
         "the documentary-recovery PR merge commit"),
        ("documentary_recovery_pr_role",
         STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR_ROLE,
         "the documentary-recovery PR role"),
        ("documentary_recovery_pr_semantics",
         STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR_SEMANTICS,
         "the documentary-recovery PR supersession semantics"),
        ("human_submission_pr_number", STAGE128_M3I2_HUMAN_SUBMISSION_PR,
         "the human-submission RECORDING PR"),
        ("human_submission_pr_merge_commit",
         STAGE128_M3I2_HUMAN_SUBMISSION_MERGE_COMMIT,
         "the human-submission PR merge commit"),
        ("human_submission_pr_role", STAGE128_M3I2_HUMAN_SUBMISSION_PR_ROLE,
         "the human-submission PR role"),
    ):
        if topology.get(field) != expected:
            raise ValidationFail(f"{label} is pinned to {expected!r}")
    if topology.get("pr_roles_re_derived_from_adjacency") is not False:
        raise ValidationFail(
            "PR roles may never be re-derived from adjacency")
    if topology.get("pr_roles_are_historical_facts_not_positional") is not (
            True):
        raise ValidationFail("PR roles must be recorded as historical facts")
    if not (STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR
            < STAGE128_M3I2_HUMAN_SUBMISSION_PR < live_number):
        raise ValidationFail(
            "the documentary recovery, the human submission and the live "
            "Draft must stay three distinct PRs in order")
    if topology.get("documentary_recovery_pr_merge_commit") == topology.get(
            "human_submission_pr_merge_commit"):
        raise ValidationFail(
            "the two merged historical PRs have two DIFFERENT merge commits")
    if [(entry.get("pr_number"), entry.get("role"), entry.get("merged"))
            for entry in (topology.get("pr_role_sequence") or [])] != [
        (STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR,
         STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR_ROLE, True),
        (STAGE128_M3I2_HUMAN_SUBMISSION_PR,
         STAGE128_M3I2_HUMAN_SUBMISSION_PR_ROLE, True),
        (live_number, topology.get("live_pr_role"), False),
    ]:
        raise ValidationFail(
            "the PR role sequence must be exactly "
            f"#{STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR} -> "
            f"#{STAGE128_M3I2_HUMAN_SUBMISSION_PR} -> #{live_number}")

    # Retrieval, the Data Gate and modeling are SEPARATE authorized actions.
    for field, expected, source, label in (
        ("m3_lag_wdi_next_action_id", STAGE128_M3_LAG_RETRIEVAL_ACTION_ID,
         boundary, "the immediate Track B pointer"),
        ("m3_lag_wdi_next_action_scope", STAGE128_M3_LAG_NEXT_ACTION_SCOPE,
         boundary, "the immediate Track B pointer scope"),
        ("m3_lag_wdi_retrieval_action_id",
         STAGE128_M3_LAG_RETRIEVAL_ACTION_ID, boundary,
         "the retrieval action id"),
        ("m3_lag_wdi_data_gate_action_id", STAGE128_M3_LAG_DATA_GATE_ACTION_ID,
         boundary, "the Data Gate action id"),
        ("m3_lag_wdi_post_retrieval_audit_action_id",
         STAGE128_M3_LAG_POST_RETRIEVAL_AUDIT_ACTION_ID, boundary,
         "the post-retrieval audit action id"),
        ("m3_lag_wdi_modeling_action_id", STAGE128_M3_LAG_MODELING_ACTION_ID,
         boundary, "the modeling action id"),
        ("gate_action_id", STAGE128_M3_LAG_DATA_GATE_ACTION_ID, gate,
         "the Gate contract's action id"),
        ("retrieval_action_id", STAGE128_M3_LAG_RETRIEVAL_ACTION_ID, gate,
         "the Gate contract's retrieval action id"),
    ):
        if source.get(field) != expected:
            raise ValidationFail(f"{label} must be {expected}")
    if STAGE128_M3_LAG_RETRIEVAL_ACTION_ID == (
            STAGE128_M3_LAG_DATA_GATE_ACTION_ID):
        raise ValidationFail(
            "retrieval and the Data Gate may not share one action identity")
    for field, source in (
        ("m3_lag_wdi_retrieval_action_authorized", boundary),
        ("m3_lag_wdi_retrieval_action_executes_data_gate", boundary),
        ("m3_lag_wdi_next_action_executes_data_gate", boundary),
        ("m3_lag_wdi_retrieval_authorization_implies_gate_authorization",
         boundary),
        ("m3_lag_wdi_combined_retrieval_and_gate_action_permitted", boundary),
        ("m3_lag_wdi_data_gate_action_authorized", boundary),
        ("m3_lag_wdi_post_retrieval_audit_action_authorized", boundary),
        ("m3_lag_wdi_post_retrieval_audit_executes_data_gate", boundary),
        ("m3_lag_wdi_gate_pass_authorizes_modeling", boundary),
        ("gate_executed_by_retrieval_action", gate),
        ("retrieval_authorization_implies_gate_authorization", gate),
        ("combined_retrieval_and_gate_action_permitted", gate),
        ("post_retrieval_audit_action_executes_gate", gate),
        ("gate_action_authorized", gate),
        ("gate_pass_authorizes_modeling", gate),
        ("gate_pass_authorizes_modeling", modeling),
        ("modeling_authorized_by_gate_pass", modeling),
    ):
        if source.get(field) is not False:
            raise ValidationFail(f"M3-LAG-WDI {field} must be False")
    for field, source in (
        ("m3_lag_wdi_data_gate_is_a_separate_action_from_retrieval", boundary),
        ("m3_lag_wdi_data_gate_requires_new_explicit_human_authorization",
         boundary),
        ("m3_lag_wdi_retrieval_requires_new_explicit_human_authorization",
         boundary),
        ("m3_lag_wdi_modeling_requires_new_explicit_human_authorization",
         boundary),
        ("m3_lag_wdi_gate_pass_is_data_admission_only", boundary),
        ("m3_lag_wdi_gate_pointer_is_not_authorization", boundary),
        ("gate_is_a_separate_action_from_retrieval", gate),
        ("gate_requires_new_explicit_human_authorization", gate),
        ("gate_pointer_is_not_authorization", gate),
        ("gate_pass_is_data_admission_only", gate),
        ("gate_pass_is_data_admission_only", modeling),
        ("modeling_requires_new_explicit_human_authorization", modeling),
    ):
        if source.get(field) is not True:
            raise ValidationFail(f"M3-LAG-WDI {field} must be True")
    sequence = boundary.get("m3_lag_wdi_action_sequence") or []
    if [(entry.get("step"), entry.get("action_id"),
         entry.get("executes_retrieval"), entry.get("executes_data_gate"),
         entry.get("executes_modeling")) for entry in sequence] != list(
            STAGE128_M3_LAG_ACTION_SEQUENCE):
        raise ValidationFail(
            "the Track B action sequence must separate contract lock -> "
            "retrieval -> post-retrieval audit -> Data Gate -> modeling")
    for entry in sequence:
        if entry.get("executes_retrieval") and entry.get(
                "executes_data_gate"):
            raise ValidationFail(
                f"action {entry.get('action_id')!r} both retrieves and "
                "executes the Data Gate: that is a conflated action")
        if entry.get("step") != "A" and entry.get("authorized") is not False:
            raise ValidationFail(
                f"future Track B action {entry.get('action_id')!r} must be "
                "unauthorized")
    return True


# --------------------------------------------------------------------------- #
# Stage128 — Track B step B: the M3-LAG-WDI exploratory DATA RETRIEVAL
# --------------------------------------------------------------------------- #

_STAGE128_M3_LAG_RETRIEVAL_PKG = (
    "project/stage128/m3_lag_wdi_exploratory_data_retrieval")
STAGE128_M3_LAG_RETRIEVAL_ACTION_ID = (
    "stage128-m3-lag-wdi-exploratory-data-retrieval")
STAGE128_M3_LAG_RETRIEVAL_SCOPE = "retrieval_only"
STAGE128_M3_LAG_POST_RETRIEVAL_AUDIT_ACTION_ID = (
    "stage128-m3-lag-wdi-exploratory-post-retrieval-audit")
STAGE128_M3_LAG_RETRIEVAL_AUTH_SHA256 = (
    "b409e0a53d255955199c59005d39f911ae272713dbf85c38651cd0dcfd5ba604")
STAGE128_M3_LAG_RETRIEVAL_AUTH_BYTES = 125
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

#: Counters a retrieval-only action must still leave at zero.
_STAGE128_M3_LAG_RETRIEVAL_ZERO = (
    "wdi_value_inspections", "wdi_observations_read",
    "alternative_indicators_searched", "alternative_indicators_retrieved",
    "proxy_or_substitute_series_retrieved", "coverage_calculations",
    "candidate_coverage_evaluations", "block_coverage_evaluations",
    "data_gate_executions", "data_gate_results_returned",
    "admission_decisions", "company_row_macro_joins",
    "feature_materializations", "fx_transformation_calculations",
    "common_sample_constructions", "model_fits", "predictions",
    "predictive_metrics", "bootstrap_executions", "holm_calculations",
    "shap_executions", "final_test_rows_read",
    "final_test_predictor_values_read", "final_test_target_values_read",
)


def stage128_m3_lag_wdi_data_retrieval_executed(repo_root: Path) -> bool:
    """True once the retrieval-only action has acquired the locked payloads.

    An ``executed`` retrieval may exist ONLY if it stayed strictly inside
    ``retrieval_only``: exactly the two locked indicator codes, the locked
    country, official HTTPS World Bank API URLs, no payload parsing, no value
    read, no coverage, no Gate, no admission, no join, no model, no Final Test
    row — and with the post-retrieval audit, the Data Gate and modeling each
    still unauthorized. Anything else raises, so the validator can never report
    a retrieval that quietly did more than acquire bytes.
    """
    path = repo_root / _STAGE128_M3_LAG_RETRIEVAL_MANIFEST_REL
    if not path.is_file():
        return False
    manifest = _read_json(repo_root, _STAGE128_M3_LAG_RETRIEVAL_MANIFEST_REL)
    audit = _read_json(repo_root, _STAGE128_M3_LAG_RETRIEVAL_AUDIT_REL)
    boundary = _read_json(repo_root, _STAGE128_M3_LAG_RETRIEVAL_BOUNDARY_REL)
    authorization = _read_json(repo_root, _STAGE128_M3_LAG_RETRIEVAL_AUTH_REL)

    if manifest.get("action_id") != STAGE128_M3_LAG_RETRIEVAL_ACTION_ID:
        raise ValidationFail("M3-LAG-WDI retrieval action_id mismatch")
    if manifest.get("authorized_scope") != STAGE128_M3_LAG_RETRIEVAL_SCOPE:
        raise ValidationFail(
            f"the retrieval scope must be {STAGE128_M3_LAG_RETRIEVAL_SCOPE}")

    # A NEW single-use authorization, byte-exact and distinct from the lock's.
    if authorization.get("authorization_sha256") != (
            STAGE128_M3_LAG_RETRIEVAL_AUTH_SHA256):
        raise ValidationFail("the retrieval authorization digest is wrong")
    if authorization.get("authorization_utf8_bytes") != (
            STAGE128_M3_LAG_RETRIEVAL_AUTH_BYTES):
        raise ValidationFail("the retrieval authorization byte length is wrong")
    text = authorization.get("authorization_text") or ""
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != (
            STAGE128_M3_LAG_RETRIEVAL_AUTH_SHA256):
        raise ValidationFail(
            "the retrieval authorization digest does not match its own text")
    for field in ("authorization_is_reusable_for_post_retrieval_audit",
                  "authorization_is_reusable_for_data_gate",
                  "authorization_is_reusable_for_modeling",
                  "standing_authorization",
                  "prior_contract_lock_authorization_reused"):
        if authorization.get(field) is not False:
            raise ValidationFail(f"retrieval authorization {field} must be "
                                 "False")

    # Exactly the two locked indicators, locked country, official API only.
    indicators = manifest.get("indicators") or []
    if [entry.get("indicator_code") for entry in indicators] != [
            STAGE128_M3_LAG_CPI_CODE, STAGE128_M3_LAG_FX_CODE]:
        raise ValidationFail(
            "retrieval must cover exactly the two locked indicators")
    for entry in indicators:
        if entry.get("country_code") != "IRN":
            raise ValidationFail("both retrieved indicators are for IRN")
        if not (entry.get("request_url") or "").startswith(
                "https://api.worldbank.org/v2/"):
            raise ValidationFail(
                "retrieval must use the official World Bank WDI API over "
                "HTTPS")
        if entry.get("payload_parsed") is not False:
            raise ValidationFail("a retrieval-only action parses no payload")
        # Unresolved stays null, never 0: a 0 here would be a CLAIM about the
        # data ("we looked and found none"), which acquisition may not make.
        for field in ("observations_read", "values_inspected",
                      "coverage_calculated"):
            if entry.get(field) is not None:
                raise ValidationFail(
                    f"{field} must stay null after a retrieval-only action, "
                    "not zero and not a value")
    if manifest.get("point_in_time_availability_claimed") is not False:
        raise ValidationFail(
            "retrieval never establishes point-in-time availability")
    if manifest.get("raw_payloads_committed_to_git") != 0:
        raise ValidationFail("raw WDI payloads stay OUTSIDE Git")

    # Retrieval happened; nothing downstream of it did.
    if audit.get("retrieval_started") is not True:
        raise ValidationFail("the retrieval audit must record retrieval")
    for counter in _STAGE128_M3_LAG_RETRIEVAL_ZERO:
        if audit.get(counter) != 0:
            raise ValidationFail(
                f"retrieval-only: counter {counter} must be 0")
    for field in ("payload_json_decoded", "post_retrieval_audit_executed",
                  "quarantined_local_draft_used_as_input"):
        if audit.get(field) is not False:
            raise ValidationFail(f"retrieval audit {field} must be False")

    # The boundary it stopped at: C, D and E all still closed.
    if boundary.get("m3_lag_wdi_next_action_id") != (
            STAGE128_M3_LAG_POST_RETRIEVAL_AUDIT_ACTION_ID):
        raise ValidationFail(
            "the pointer after retrieval is the post-retrieval audit")
    for field in ("m3_lag_wdi_next_action_authorized",
                  "m3_lag_wdi_post_retrieval_audit_action_authorized",
                  "m3_lag_wdi_data_gate_action_authorized",
                  "m3_lag_wdi_data_gate_executed",
                  "m3_lag_wdi_gate_pass_authorizes_modeling",
                  "m3_lag_wdi_modeling_authorized",
                  "m3_lag_wdi_modeling_started",
                  "retrieval_executed_data_gate",
                  "combined_retrieval_and_gate_action_permitted",
                  "retrieval_authorization_implies_gate_authorization",
                  "retrieval_authorization_reusable",
                  "m3_lag_wdi_block_admitted",
                  "world_bank_inquiry_terminated_by_this_action",
                  "world_bank_follow_up_authorized",
                  "world_bank_response_ingestion_authorized",
                  "final_test_access_authorized", "m4_authorized",
                  "merge_authorized", "pii_committed_to_git",
                  "credentials_committed_to_git"):
        if boundary.get(field) is not False:
            raise ValidationFail(
                f"retrieval governance boundary {field} must be False")
    if boundary.get("final_test_locked") is not True:
        raise ValidationFail("the Final Test stays locked after retrieval")
    if boundary.get("m3_lag_wdi_authoritative_contract_status") != (
            STAGE128_M3_LAG_LOCKED_STATUS):
        raise ValidationFail(
            "retrieval does not change the authoritative contract status")
    if boundary.get("world_bank_inquiry_status") != (
            STAGE128_M3I2_INQUIRY_SUBMITTED_STATUS):
        raise ValidationFail(
            "Track A must stay "
            f"{STAGE128_M3I2_INQUIRY_SUBMITTED_STATUS} after a Track B "
            "retrieval")
    return True


# --------------------------------------------------------------------------- #
# Stage128 Track B step D — the executed M3-LAG-WDI Data Gate
# --------------------------------------------------------------------------- #

_STAGE128_M3_LAG_GATE_PKG = (
    "project/stage128/m3_lag_wdi_exploratory_data_gate")
STAGE128_M3_LAG_GATE_SCOPE = "data_gate_only"
_STAGE128_M3_LAG_GATE_REPORT_REL = (
    f"{_STAGE128_M3_LAG_GATE_PKG}/stage128_m3_lag_wdi_data_gate_report.json")
_STAGE128_M3_LAG_GATE_AUDIT_REL = (
    f"{_STAGE128_M3_LAG_GATE_PKG}/"
    "stage128_m3_lag_wdi_data_gate_execution_audit.json")
_STAGE128_M3_LAG_GATE_BOUNDARY_REL = (
    f"{_STAGE128_M3_LAG_GATE_PKG}/"
    "stage128_m3_lag_wdi_data_gate_governance_boundary.json")
_STAGE128_M3_LAG_GATE_DECISION_REL = (
    f"{_STAGE128_M3_LAG_GATE_PKG}/stage128_m3_lag_wdi_data_gate_decision.json")

#: The Gate's own verdict vocabulary.
STAGE128_M3_LAG_GATE_VOCABULARY = (
    "PASS_M3_LAG_WDI_DATA_GATE",
    "FAIL_M3_LAG_WDI_DATA_GATE",
    "UNRESOLVED_M3_LAG_WDI_DATA_GATE",
)
STAGE128_M3_LAG_GATE_PASS = "PASS_M3_LAG_WDI_DATA_GATE"

#: The locked, inherited thresholds, pinned independently of the Gate package
#: so a lowered threshold cannot validate itself.
STAGE128_M3_LAG_GATE_CANDIDATE_MIN = 0.80
STAGE128_M3_LAG_GATE_BLOCK_MIN = 0.70
STAGE128_M3_LAG_GATE_MIN_POSITIVE = 5
STAGE128_M3_LAG_GATE_DENOMINATOR_ROWS = 539

#: Counters a data Gate must STILL leave at zero. It computes coverage — that
#: is its job — but it retrieves nothing, fits nothing and reads no Final Test
#: row.
_STAGE128_M3_LAG_GATE_ZERO = (
    "world_bank_api_requests", "new_payloads_retrieved",
    "alternative_indicators_searched", "alternative_indicators_retrieved",
    "feature_value_tables_materialized", "model_fits", "predictions",
    "predictive_metrics", "bootstrap_executions", "holm_calculations",
    "shap_executions", "tuning_runs", "cross_validation_runs",
    "model_selections", "final_test_rows_read",
    "final_test_predictor_values_read", "final_test_target_values_read",
)


def stage128_m3_lag_wdi_data_gate_executed(repo_root: Path) -> bool:
    """True once the Data Gate has been executed inside its own boundary.

    An ``executed`` Gate may exist ONLY if it stayed strictly inside
    ``data_gate_only``: the locked inherited thresholds unchanged, the exact
    539-row retained-M2 development denominator with no final-test row, a
    verdict from the Gate's own vocabulary that FOLLOWS from the published
    numerators, no model fit, no feature-value table and no Final Test row —
    with modeling still unauthorized and the Gate's own authorization already
    consumed. Anything else raises, so the validator can never report a Gate
    that quietly admitted more than the numbers support.
    """
    path = repo_root / _STAGE128_M3_LAG_GATE_REPORT_REL
    if not path.is_file():
        return False
    report = _read_json(repo_root, _STAGE128_M3_LAG_GATE_REPORT_REL)
    audit = _read_json(repo_root, _STAGE128_M3_LAG_GATE_AUDIT_REL)
    boundary = _read_json(repo_root, _STAGE128_M3_LAG_GATE_BOUNDARY_REL)
    decision = _read_json(repo_root, _STAGE128_M3_LAG_GATE_DECISION_REL)

    if report.get("action_id") != STAGE128_M3_LAG_DATA_GATE_ACTION_ID:
        raise ValidationFail("M3-LAG-WDI Data Gate action_id mismatch")
    if report.get("authorized_scope") != STAGE128_M3_LAG_GATE_SCOPE:
        raise ValidationFail(
            f"the Gate scope must be {STAGE128_M3_LAG_GATE_SCOPE}")

    # The thresholds are the locked, inherited ones. This is the single most
    # valuable check here: lowering one is exactly how a FAIL becomes a PASS.
    thresholds = report.get("locked_thresholds") or {}
    if thresholds.get("thresholds_changed_by_this_action") is not False:
        raise ValidationFail("the Gate may not change the locked thresholds")
    if thresholds.get("coverage_scope") != "development_only":
        raise ValidationFail("the M3-LAG-WDI Gate is development-only")
    for key, expected in (
            ("candidate_valid_coverage_min",
             STAGE128_M3_LAG_GATE_CANDIDATE_MIN),
            ("block_common_sample_coverage_min",
             STAGE128_M3_LAG_GATE_BLOCK_MIN),
            ("minimum_positive_evaluable_each_locked_validation_window",
             STAGE128_M3_LAG_GATE_MIN_POSITIVE)):
        if float(thresholds.get(key, -1)) != float(expected):
            raise ValidationFail(
                f"Gate threshold {key} is {thresholds.get(key)}, not the "
                f"locked inherited {expected}")

    # The denominator is the exact retained-M2 development sample.
    gate = report.get("gate_computation") or {}
    rows = gate.get("rows")
    if rows != STAGE128_M3_LAG_GATE_DENOMINATOR_ROWS:
        raise ValidationFail(
            f"the Gate denominator must be "
            f"{STAGE128_M3_LAG_GATE_DENOMINATOR_ROWS} rows, not {rows}")
    if (report.get("parent_surface") or {}).get(
            "final_test_rows_in_parent_surface") != 0:
        raise ValidationFail("no final-test row may enter the Gate")

    # The verdict must FOLLOW from the published numbers, never be asserted.
    verdict = decision.get("gate_result")
    if verdict not in STAGE128_M3_LAG_GATE_VOCABULARY:
        raise ValidationFail(f"unrecognized Gate verdict {verdict!r}")
    recomputed = {
        "cpi_candidate_coverage_meets_threshold":
            gate["cpi_constructible_rows"] / rows
            >= STAGE128_M3_LAG_GATE_CANDIDATE_MIN,
        "fx_candidate_coverage_meets_threshold":
            gate["fx_constructible_rows"] / rows
            >= STAGE128_M3_LAG_GATE_CANDIDATE_MIN,
        "block_common_sample_coverage_meets_threshold":
            gate["both_constructible_rows"] / rows
            >= STAGE128_M3_LAG_GATE_BLOCK_MIN,
        "every_validation_window_meets_positive_floor": all(
            window["positive_evaluable_in_m3_lag_wdi_common_sample"]
            >= STAGE128_M3_LAG_GATE_MIN_POSITIVE
            for window in gate["validation_windows"].values()),
    }
    if recomputed != gate.get("threshold_checks"):
        raise ValidationFail(
            "the Gate's threshold checks do not follow from its own published "
            "numerators, denominator and locked thresholds")
    expected_verdict = (
        "UNRESOLVED_M3_LAG_WDI_DATA_GATE"
        if gate.get("status_invariant_across_calendar_conventions") is not True
        else STAGE128_M3_LAG_GATE_PASS if all(recomputed.values())
        else "FAIL_M3_LAG_WDI_DATA_GATE")
    if verdict != expected_verdict:
        raise ValidationFail(
            f"the published Gate verdict {verdict} does not follow from its "
            f"own checks (recomputed {expected_verdict})")
    if decision.get("block_formally_admitted") is not (
            verdict == STAGE128_M3_LAG_GATE_PASS):
        raise ValidationFail(
            "block_formally_admitted must equal (verdict == PASS)")

    # The Gate ran; nothing downstream of it did.
    if audit.get("data_gate_executed") is not True:
        raise ValidationFail("the Gate audit must record that the Gate ran")
    if audit.get("data_gate_executions") != 1:
        raise ValidationFail("the Gate is executed exactly once")
    for counter in _STAGE128_M3_LAG_GATE_ZERO:
        if audit.get(counter) != 0:
            raise ValidationFail(f"data-gate-only: counter {counter} must be 0")
    for field in ("retained_bytes_modified", "deposited_evidence_modified",
                  "quarantined_local_draft_used_as_input"):
        if audit.get(field) is not False:
            raise ValidationFail(f"Gate audit {field} must be False")

    # A PASS admits DATA. The boundary it stopped at: E still closed.
    if boundary.get("m3_lag_wdi_next_action_id") != (
            STAGE128_M3_LAG_MODELING_ACTION_ID):
        raise ValidationFail("the pointer after the Gate is modeling")
    for field in ("m3_lag_wdi_next_action_authorized",
                  "m3_lag_wdi_data_gate_authorized_now",
                  "m3_lag_wdi_data_gate_authorization_reusable",
                  "gate_pass_is_modeling_authorization",
                  "gate_pass_is_information_content_claim",
                  "gate_pass_is_final_test_unlock",
                  "gate_authorization_propagates_to_step_e",
                  "m3_lag_wdi_modeling_authorized",
                  "m3_lag_wdi_modeling_started",
                  "m3_lag_wdi_contract_modified_by_this_action",
                  "m3_lag_wdi_thresholds_modified_by_this_action",
                  "step_c_rerun_by_this_action",
                  "step_c_result_modified_by_this_action",
                  "retrieval_authorized_now",
                  "new_world_bank_request_made_by_this_action",
                  "world_bank_inquiry_terminated_by_this_action",
                  "world_bank_follow_up_authorized",
                  "world_bank_response_ingestion_authorized",
                  "final_test_access_authorized", "m4_authorized",
                  "merge_authorized", "ready_for_review_authorized",
                  "pii_committed_to_git", "credentials_committed_to_git"):
        if boundary.get(field) is not False:
            raise ValidationFail(f"Gate governance boundary {field} must be "
                                 "False")
    for field in ("m3_lag_wdi_data_gate_authorization_consumed",
                  "m3_lag_wdi_block_admission_is_data_admission_only",
                  "step_c_material_findings_preserved",
                  "final_test_locked"):
        if boundary.get(field) is not True:
            raise ValidationFail(f"Gate governance boundary {field} must be "
                                 "True")
    if boundary.get("m3_lag_wdi_authoritative_contract_status") != (
            STAGE128_M3_LAG_LOCKED_STATUS):
        raise ValidationFail(
            "the Gate does not change the authoritative contract status")
    if boundary.get("world_bank_inquiry_status") != (
            STAGE128_M3I2_INQUIRY_SUBMITTED_STATUS):
        raise ValidationFail(
            "Track A must stay "
            f"{STAGE128_M3I2_INQUIRY_SUBMITTED_STATUS} after a Track B Gate")

    # A coverage PASS must never be published without the limitations that
    # survive it, and step C's accepted findings must still be there.
    if not (decision.get("material_limitations") or []):
        raise ValidationFail(
            "the Gate inherited material limitations and may not publish none")
    if set(decision.get("scientific_distinctions") or {}) != {
            "A_syntactic_availability_and_coverage",
            "B_pre_defined_thresholds_satisfied",
            "C_information_content_limitation_from_step_c",
            "D_effect_on_the_formal_gate_decision",
            "E_remaining_scientific_limitation"}:
        raise ValidationFail(
            "the Gate must distinguish coverage, thresholds, information "
            "content, formal effect and residual limitation")
    for field in ("thresholds_changed_to_obtain_result", "criteria_weakened",
                  "criteria_strengthened_after_seeing_result",
                  "imputation_used", "alternative_indicator_tried"):
        if decision.get(field) is not False:
            raise ValidationFail(f"Gate decision {field} must be False")
    return True


#: PR #73 was merged into main by this commit; PR #74 was retargeted after.
STAGE128_M3I2_PROVENANCE_BASELINE_COMMIT = (
    "e6db63fb7d105f0d3a39db101c9e364161c367e9")
STAGE128_M3I2_PREDECESSOR_MERGE_COMMIT = (
    "b94f73fab99b5c3bc5c55ea7c14736f2bddb516a")
STAGE128_M3I2_PREDECESSOR_BRANCH = "stage128-m3-macro-data-gate"
STAGE128_M3I2_MAIN_BRANCH = "main"


def _assert_m3i2_live_topology(decision: dict) -> None:
    """Validate the PR topology in a STATE-DEPENDENT way.

    "Never base on main" held only while the predecessor PR was open. Now that
    PR #73 is merged, that rule would reject the correct live topology, so each
    predecessor state is validated on its own terms. In both states the
    scientific provenance baseline stays the PR #73 HEAD, PR #74 stays a Draft
    and unmerged, and no merge authorization exists.
    """
    topo = decision.get("live_topology") or {}
    if not topo:
        raise ValidationFail(
            "stage128 M3I-2 contract lock must record its live PR topology")
    merged = topo.get("predecessor_pr_merged")
    base = topo.get("live_pr_base_branch")

    if merged is False:
        if base != STAGE128_M3I2_PREDECESSOR_BRANCH:
            raise ValidationFail(
                "while the predecessor PR is open the M3I-2 PR base must be "
                f"{STAGE128_M3I2_PREDECESSOR_BRANCH}")
        if topo.get("pr_is_stacked_on_open_predecessor") is not True:
            raise ValidationFail(
                "while the predecessor PR is open the M3I-2 PR is stacked")
        if topo.get("may_target_main") is not False:
            raise ValidationFail(
                "the M3I-2 PR may not target main while the predecessor is "
                "open")
    elif merged is True:
        if topo.get("predecessor_pr_merge_commit") != (
                STAGE128_M3I2_PREDECESSOR_MERGE_COMMIT):
            raise ValidationFail(
                "the predecessor is marked merged without the verified merge "
                f"commit {STAGE128_M3I2_PREDECESSOR_MERGE_COMMIT}")
        if topo.get("live_main_commit") != (
                STAGE128_M3I2_PREDECESSOR_MERGE_COMMIT):
            raise ValidationFail(
                "live main must equal the predecessor merge commit")
        if base == STAGE128_M3I2_PREDECESSOR_BRANCH:
            raise ValidationFail(
                "the M3I-2 PR base still names the merged predecessor branch")
        if base != STAGE128_M3I2_MAIN_BRANCH:
            raise ValidationFail(
                "after the predecessor merged the M3I-2 PR base must be main")
        if topo.get("live_pr_base_commit") != (
                STAGE128_M3I2_PREDECESSOR_MERGE_COMMIT):
            raise ValidationFail(
                "the live PR base commit must equal current main")
        if topo.get("pr_is_stacked_on_open_predecessor") is not False:
            raise ValidationFail(
                "the predecessor is merged; the M3I-2 PR is no longer stacked "
                "on an open predecessor")
        if topo.get(
                "retargeted_to_main_after_predecessor_merge_verified") is not (
                True):
            raise ValidationFail(
                "the retarget to main must be verified after the predecessor "
                "merge")
        if topo.get("may_target_main") is not True:
            raise ValidationFail(
                "after the predecessor merged the M3I-2 PR may target main")
    else:
        raise ValidationFail(
            "predecessor_pr_merged must be recorded explicitly")

    if topo.get("scientific_provenance_baseline_commit") != (
            STAGE128_M3I2_PROVENANCE_BASELINE_COMMIT):
        raise ValidationFail(
            "the M3I-2 scientific provenance baseline must remain the "
            f"predecessor PR head {STAGE128_M3I2_PROVENANCE_BASELINE_COMMIT}")
    if topo.get("live_pr_is_draft") is not True:
        raise ValidationFail("the M3I-2 PR must remain a Draft")
    if topo.get("live_pr_merged") is not False:
        raise ValidationFail("the M3I-2 PR must remain unmerged")
    if topo.get("merge_authorized") is not False:
        raise ValidationFail("no merge authorization exists for the M3I-2 PR")


def m3_gate_state_is_self_consistent(
    handoff: dict[str, Any], *, m3_gate_executed: bool,
) -> bool:
    """False on the exact contradiction the reviewed head contained.

    The reviewed head simultaneously recorded ``m3_macro_data_gate_executed``
    and ``m3_data_workstream_started`` as true while still labelling the live
    workstream as the M2 D2 one and narrating the M3 Gate as "not executed" /
    "not started". Once the Gate has executed, the CURRENT-state fields must
    say so, and the no-modeling invariants must still hold.
    """
    if not m3_gate_executed:
        return handoff.get("m3_macro_data_gate_executed") is not True
    return (
        handoff.get("m3_macro_data_gate_executed") is True
        and handoff.get("m3_data_workstream_started") is True
        # The live workstream is the M3 Gate until the supplementary M3I-2
        # contract lock succeeds it; both are M3-family DATA/CONTRACT labels
        # and neither implies modeling.
        and handoff.get("active_workstream") in (
            STAGE128_M3_ACTIVE_WORKSTREAM, STAGE128_M3I2_ACTIVE_WORKSTREAM,
            STAGE128_M3I2_EVIDENCE_ACTIVE_WORKSTREAM,
            STAGE128_M3I2_RECOVERY_ACTIVE_WORKSTREAM)
        and handoff.get("m3_modeling_started") is False
        and handoff.get("m3_incremental_evaluation_authorized") is False
        and handoff.get("m3_block_admitted_for_incremental_evaluation") is False
        and handoff.get("m3_macro_data_gate_status") in (
            "PASS_FOR_M3_INCREMENTAL_EVALUATION", "FAIL_M3_DATA_GATE",
            "UNRESOLVED_M3_DATA_GATE")
    )


def expected_active_workstream(repo_root: Path) -> str:
    """The single source of truth for the CURRENT live workstream label.

    `active_workstream` claims to describe the workstream that is live NOW. It
    must therefore advance with the live research state: once the Stage128 D2
    boundary-month design freeze is complete, the live workstream is the
    Stage128 M2 D2 one, not the Stage126 M1 financial baseline. The Stage126
    value remains correct history, but it is no longer the CURRENT value.
    """
    if stage128_m3i2_final_documentary_recovery_initiated(repo_root):
        return STAGE128_M3I2_RECOVERY_ACTIVE_WORKSTREAM
    if stage128_m3i2_evidence_capture_completed(repo_root):
        return STAGE128_M3I2_EVIDENCE_ACTIVE_WORKSTREAM
    if stage128_m3i2_contract_lock_completed(repo_root):
        return STAGE128_M3I2_ACTIVE_WORKSTREAM
    if stage128_m3_macro_data_gate_executed(repo_root):
        return STAGE128_M3_ACTIVE_WORKSTREAM
    if stage128_m2_d2_design_freeze_completed(repo_root):
        return STAGE128_ACTIVE_WORKSTREAM
    return ACTIVE_WORKSTREAM


def expected_current_stage(repo_root: Path) -> str:
    """The single source of truth for the CURRENT live stage label."""
    if stage128_m2_d2_design_freeze_completed(repo_root):
        return STAGE128_CURRENT_STAGE
    return STAGE126_CURRENT_STAGE


def current_state_labels_are_not_stale(
    handoff: dict[str, Any], *, freeze_completed: bool,
) -> bool:
    """False when the live labels still claim Stage126 after the freeze.

    Guards the exact ambiguity this check exists for: a snapshot that says
    `Stage126 / stage126_m1_financial_baseline` while the same canonical state
    says the Stage128 D2 design freeze is complete and the research pointers
    have advanced to `stage128-m2-d2-gate-rerun`. `current_stage` and
    `active_workstream` are CURRENT-state fields, so after the freeze they may
    not carry the Stage126 M1 values.
    """
    if not freeze_completed:
        return True
    if handoff.get("current_stage") != STAGE128_CURRENT_STAGE:
        return False
    # Once the supplementary M3I-2 contract has been locked, the live
    # workstream is that contract lock and the CBI-only M3 Gate label becomes
    # predecessor context — stale as a CURRENT value.
    # The evidence capture is the newest completed action, so it - not the
    # contract lock - is the CURRENT workstream once it has been recorded.
    # ...and the final official documentary recovery is newer still: once it
    # is INITIATED it is the CURRENT workstream and the evidence capture
    # becomes predecessor context.
    if handoff.get(
            "stage128_m3i2_final_documentary_recovery_initiated") is True:
        return handoff.get("active_workstream") == (
            STAGE128_M3I2_RECOVERY_ACTIVE_WORKSTREAM)
    if handoff.get("stage128_m3i2_evidence_capture_executed") is True:
        return handoff.get("active_workstream") == (
            STAGE128_M3I2_EVIDENCE_ACTIVE_WORKSTREAM)
    if handoff.get("stage128_m3i2_contract_lock_executed") is True:
        return handoff.get("active_workstream") == (
            STAGE128_M3I2_ACTIVE_WORKSTREAM)
    # After the M3 Gate has executed the live workstream is the M3 Gate; the
    # M2 D2 label becomes predecessor context and is stale as a CURRENT value.
    if handoff.get("m3_macro_data_gate_executed") is True:
        return handoff.get("active_workstream") == STAGE128_M3_ACTIVE_WORKSTREAM
    return handoff.get("active_workstream") == STAGE128_ACTIVE_WORKSTREAM


def stage127_human_review_closure_consistent(
    handoff: dict[str, Any], *, freeze_completed: bool,
) -> bool:
    """False when the repository contradicts itself about Stage127.

    A completed Stage128 D2 design freeze IS the human decision the terminal
    Stage127 ``FAIL_M2_DATA_GATE`` result was waiting for. So once
    ``stage128_m2_d2_design_freeze_completed`` is True, it can no longer also
    be true that Stage127's terminal result is pending human review or that a
    Stage127 semantics human decision is still required. Before the freeze,
    those markers are unconstrained by this function.
    """
    if not freeze_completed:
        return True
    return (
        handoff.get(
            "stage127_m2_market_data_gate_terminal_result_pending_human_review"
        ) is False
        and handoff.get("stage127_m2_semantics_human_decision_required") is False
    )


def stage127_historical_d0_gate_status_preserved(handoff: dict[str, Any]) -> bool:
    """The historical D0 Gate outcome may never be rewritten (e.g. to PASS)."""
    if not handoff.get("stage127_m2_market_data_gate_executed"):
        return True
    return (
        handoff.get("stage127_m2_market_data_gate_status")
        == STAGE127_HISTORICAL_D0_GATE_STATUS
    )


# The canonical M2 Gate re-run under the frozen Gregorian D2 specification.
# It is a DATA-ADMISSION decision: a PASS makes the M2 incremental-evaluation
# action scientifically ELIGIBLE and advances the pointer to it, but never
# authorizes it, never starts modeling and never unlocks the final test. A
# FAIL leaves the pointer on the Gate re-run itself rather than inventing a
# new scientific action in response to a negative result.
STAGE128_M2_D2_GATE_RERUN_REL = (
    "project/stage128/stage128_m2_d2_gate_rerun_decision.json"
)
STAGE128_M2_D2_GATE_RERUN_ACTION_ID = "stage128-m2-d2-gate-rerun"
STAGE128_M2_D2_GATE_RERUN_PASS = "PASS_FOR_M2_INCREMENTAL_EVALUATION"
STAGE128_M2_D2_GATE_RERUN_FAIL = "FAIL_M2_DATA_GATE"
NEXT_RESEARCH_ACTION_ID_AFTER_STAGE128_M2_D2_GATE_RERUN_PASS = (
    "stage127-m2-incremental-evaluation"
)
#: The design-freeze action the Gate re-run executed. Rendering must always
#: attribute the freeze to THIS id and never to a later research action.
_STAGE128_M2_D2_FREEZE_ACTION_ID = (
    "stage128-m2-boundary-month-return-design-freeze"
)
ROADMAP_MD_REL = "project/docs/ai/ROADMAP.md"


def _roadmap_front_matter(text: str) -> dict[str, str]:
    """Parse the simple ``key: value`` ROADMAP YAML front matter."""
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    fm: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


def _describes_incremental_evaluation_as_gate_rerun(text: str) -> bool:
    """True if prose calls the M2 incremental evaluation the Gate re-run.

    The successor action is the M2 INCREMENTAL EVALUATION. Describing it as
    "the canonical M2 Gate re-run" conflates it with the already-completed
    ``stage128-m2-d2-gate-rerun`` and is a fail-closed rendering defect. The
    explicit negation ("it is NOT the canonical M2 Gate re-run") is allowed.
    """
    target = NEXT_RESEARCH_ACTION_ID_AFTER_STAGE128_M2_D2_GATE_RERUN_PASS
    for line in text.splitlines():
        if target not in line:
            continue
        lowered = line.lower()
        if "gate re-run" not in lowered and "gate rerun" not in lowered:
            continue
        if "not the canonical m2 gate re-run" in lowered:
            continue
        if "the canonical m2 gate re-run" in lowered:
            return True
    return False


def _stage128_m2_d2_gate_rerun_decision(repo_root: Path) -> dict[str, Any]:
    path = repo_root / STAGE128_M2_D2_GATE_RERUN_REL
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def stage128_m2_d2_gate_rerun_executed(repo_root: Path) -> bool:
    """Narrow, fail-closed recognition of the executed D2 Gate re-run."""
    d = _stage128_m2_d2_gate_rerun_decision(repo_root)
    if d.get("decision_id") != STAGE128_M2_D2_GATE_RERUN_ACTION_ID:
        return False
    if d.get("gate_status") not in (
        STAGE128_M2_D2_GATE_RERUN_PASS, STAGE128_M2_D2_GATE_RERUN_FAIL
    ):
        return False
    if d.get("historical_d0_gate_status") != STAGE127_HISTORICAL_D0_GATE_STATUS:
        return False
    required = {
        "modeling_performed": False,
        "model_fit_calls": 0,
        "prediction_calls": 0,
        "gate_thresholds_changed": False,
        "new_design_decision_made_in_this_action": False,
        "historical_d0_artifacts_rewritten": False,
    }
    if not all(d.get(k) == v for k, v in required.items()):
        return False
    elig = d.get("eligibility_for_next_action") or {}
    return (
        elig.get("m2_incremental_evaluation_authorized") is False
        and elig.get("m2_modeling_started") is False
    )


def stage128_m2_d2_gate_rerun_next_action_id(repo_root: Path) -> str:
    """Pointer after the Gate re-run. A pointer is never an authorization."""
    d = _stage128_m2_d2_gate_rerun_decision(repo_root)
    if d.get("gate_status") == STAGE128_M2_D2_GATE_RERUN_PASS:
        return NEXT_RESEARCH_ACTION_ID_AFTER_STAGE128_M2_D2_GATE_RERUN_PASS
    return STAGE128_M2_D2_GATE_RERUN_ACTION_ID


STAGE127_M2_INCREMENTAL_EVALUATION_REL = (
    "project/stage128/m2_incremental_evaluation/"
    "stage127_m2_incremental_evaluation_decision.json"
)
STAGE127_M2_INCREMENTAL_EVALUATION_ACTION_ID = (
    "stage127-m2-incremental-evaluation"
)
#: A human retained-block review, identified as a POINTER only.
NEXT_RESEARCH_ACTION_ID_AFTER_M2_INCREMENTAL_EVALUATION = (
    "stage128-m2-retained-block-human-decision"
)


def stage127_m2_incremental_evaluation_completed(repo_root: Path) -> bool:
    """Narrow, fail-closed recognition of the completed paired evaluation."""
    path = repo_root / STAGE127_M2_INCREMENTAL_EVALUATION_REL
    if not path.is_file():
        return False
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if d.get("decision_id") != STAGE127_M2_INCREMENTAL_EVALUATION_ACTION_ID:
        return False
    if d.get("historical_d0_gate_status") != STAGE127_HISTORICAL_D0_GATE_STATUS:
        return False
    required = {
        "winner_selected": False,
        "retained_block_selected": False,
        "superiority_claimed": False,
        "authorizes_next_action": False,
        "m3_started": False,
        "m4_started": False,
        "human_retained_block_decision_required": True,
    }
    if not all(d.get(k) == v for k, v in required.items()):
        return False
    fw = d.get("firewall") or {}
    return (
        fw.get("final_test_predictor_values_read") == 0
        and fw.get("final_test_target_values_read") == 0
        and fw.get("final_test_model_fits") == 0
        and fw.get("full_development_refits") == 0
    )


STAGE128_M2_RETAINED_BLOCK_DECISION_REL = (
    "project/stage128/m2_retained_block_human_decision/"
    "stage128_m2_retained_block_human_decision.json"
)
STAGE128_M2_RETAINED_BLOCK_DECISION_ACTION_ID = (
    "stage128-m2-retained-block-human-decision"
)
STAGE128_M2_RETAINED_BLOCK_DECISION_OUTCOME = (
    "RETAIN_M2_AS_INTERMEDIATE_CONFIRMATORY_BLOCK"
)
#: The M3 macro data Gate, identified as a POINTER only. Retaining M2 as the
#: intermediate confirmatory block never authorizes or starts M3.
NEXT_RESEARCH_ACTION_ID_AFTER_M2_RETAINED_BLOCK_DECISION = (
    "stage128-m3-macro-data-gate"
)


def stage128_m2_retained_block_decision_completed(repo_root: Path) -> bool:
    """Narrow, fail-closed recognition of the recorded retained-block decision.

    A retained-block decision is a GOVERNANCE decision. It is recognized only
    when the artifact simultaneously records retention AND the absence of any
    superiority claim, winner, final model, refit, final-test access or
    successor-block start, and reports zero scientific execution.
    """
    path = repo_root / STAGE128_M2_RETAINED_BLOCK_DECISION_REL
    if not path.is_file():
        return False
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if d.get("decision_id") != STAGE128_M2_RETAINED_BLOCK_DECISION_ACTION_ID:
        return False
    if d.get("decision_outcome") != STAGE128_M2_RETAINED_BLOCK_DECISION_OUTCOME:
        return False
    required = {
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
        "authorizes_next_action": False,
    }
    if not all(d.get(k) == v for k, v in required.items()):
        return False
    audit = d.get("execution_audit") or {}
    return all(audit.get(k) == 0 for k in (
        "model_fits", "predictions", "resampling_executions",
        "full_development_refits", "final_test_predictor_values_read",
        "final_test_target_values_read", "m3_executions", "m4_executions",
    ))


def expected_next_research_action_id(
    repo_root: Path, m1_robustness_completed: bool,
) -> str:
    """The single source of truth for the current expected research pointer."""
    if (
        m1_robustness_completed
        and robustness_closure_completed(repo_root)
        and retained_design_freeze_completed(repo_root)
        and stage128_m2_d2_design_freeze_completed(repo_root)
        and stage128_m2_d2_gate_rerun_executed(repo_root)
        and stage127_m2_incremental_evaluation_completed(repo_root)
        and stage128_m2_retained_block_decision_completed(repo_root)
        and stage128_m3i2_contract_lock_completed(repo_root)
    ):
        # A pointer is never an authorization. Once the evidence capture has
        # itself been recorded, the pointer advances to whatever that capture's
        # OWN decision names - still unauthorized.
        # The human submission the recovery pointed at has since HAPPENED, so
        # the live pointer advances past it to whatever the submission
        # recording's OWN decision names - still unauthorized.
        if stage128_m3i2_inquiry_human_submission_recorded(repo_root):
            decision = json.loads(
                (repo_root
                 / _STAGE128_M3I2_INQUIRY_SUBMISSION_DECISION_REL).read_text(
                    encoding="utf-8"))
            return decision["next_research_action_id"]
        if stage128_m3i2_final_documentary_recovery_initiated(repo_root):
            decision = json.loads(
                (repo_root / _STAGE128_M3I2_RECOVERY_DECISION_REL).read_text(
                    encoding="utf-8"))
            return decision["next_research_action_id"]
        if stage128_m3i2_evidence_capture_completed(repo_root):
            decision = json.loads(
                (repo_root / _STAGE128_M3I2_EVIDENCE_DECISION_REL).read_text(
                    encoding="utf-8"))
            return decision["next_research_action_id"]
        return NEXT_RESEARCH_ACTION_ID_AFTER_M3I2_CONTRACT_LOCK
    if (
        m1_robustness_completed
        and robustness_closure_completed(repo_root)
        and retained_design_freeze_completed(repo_root)
        and stage128_m2_d2_design_freeze_completed(repo_root)
        and stage128_m2_d2_gate_rerun_executed(repo_root)
        and stage127_m2_incremental_evaluation_completed(repo_root)
        and stage128_m2_retained_block_decision_completed(repo_root)
    ):
        return NEXT_RESEARCH_ACTION_ID_AFTER_M2_RETAINED_BLOCK_DECISION
    if (
        m1_robustness_completed
        and robustness_closure_completed(repo_root)
        and retained_design_freeze_completed(repo_root)
        and stage128_m2_d2_design_freeze_completed(repo_root)
        and stage128_m2_d2_gate_rerun_executed(repo_root)
        and stage127_m2_incremental_evaluation_completed(repo_root)
    ):
        return NEXT_RESEARCH_ACTION_ID_AFTER_M2_INCREMENTAL_EVALUATION
    if (
        m1_robustness_completed
        and robustness_closure_completed(repo_root)
        and retained_design_freeze_completed(repo_root)
        and stage128_m2_d2_design_freeze_completed(repo_root)
        and stage128_m2_d2_gate_rerun_executed(repo_root)
    ):
        return stage128_m2_d2_gate_rerun_next_action_id(repo_root)
    if (
        m1_robustness_completed
        and robustness_closure_completed(repo_root)
        and retained_design_freeze_completed(repo_root)
        and stage128_m2_d2_design_freeze_completed(repo_root)
    ):
        return NEXT_RESEARCH_ACTION_ID_AFTER_STAGE128_M2_D2_DESIGN_FREEZE
    if (
        m1_robustness_completed
        and robustness_closure_completed(repo_root)
        and retained_design_freeze_completed(repo_root)
    ):
        return NEXT_RESEARCH_ACTION_ID_AFTER_RETAINED_DESIGN_FREEZE
    if m1_robustness_completed and robustness_closure_completed(repo_root):
        return NEXT_RESEARCH_ACTION_ID_AFTER_ROBUSTNESS_CLOSURE
    if m1_robustness_completed:
        return NEXT_RESEARCH_ACTION_ID_AFTER_M1_ROBUSTNESS
    return NEXT_RESEARCH_ACTION_ID

FINAL_TEST_LOCK_FIELDS: tuple[str, ...] = (
    "final_test_unlocked",
    "final_test_access_authorized",
    "final_test_predictor_values_inspected",
    "final_test_target_values_inspected",
    "final_test_evaluation_performed",
)

# --------------------------------------------------------------------------- #
# Exception policy
# --------------------------------------------------------------------------- #

PRIOR_PART_REOPENING_DEFAULT = "forbidden"
SCIENTIFIC_ERROR_EXCEPTION_REQUIRES: tuple[str, ...] = (
    "documented_scientific_error",
    "impact_assessment",
    "explicit_new_human_authorization",
    "separate_corrective_PR",
)
NOT_A_SCIENTIFIC_ERROR: tuple[str, ...] = (
    "new Handoff timestamp",
    "new branch SHA",
    "new current test hash",
    "new completed robustness part",
    "documentation wording drift",
    "historical validator successor mismatch",
)
MAY_QUALIFY_AS_SCIENTIFIC_ERROR: tuple[str, ...] = (
    "incorrect target construction",
    "leakage",
    "incorrect feature computation",
    "wrong sample membership",
    "wrong fold assignment",
    "incorrect probability or metric computation",
    "unauthorized final-test access",
)


class ValidationFail(RuntimeError):
    """Fail-closed Stage126 current-state validation error."""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _json_str(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def recompute_decision_sha256(text_fa: str) -> str:
    return hashlib.sha256(text_fa.encode("utf-8")).hexdigest()


def repo_root_from(project_dir: Path) -> Path:
    return project_dir.parent if project_dir.name == "project" else project_dir


def _git(repo_root: str | Path, *args: str) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=True, capture_output=True, text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return ""
    return out.stdout.strip()


def require_file_hash(repo_root: Path, rel: str, expected: str, *, label: str) -> str:
    path = repo_root / rel
    if not path.is_file():
        raise ValidationFail(f"missing {label}: {rel}")
    got = sha256_file(path)
    if got != expected:
        raise ValidationFail(f"{label} hash drift: {rel} {got} != {expected}")
    return got


def _read_json(repo_root: Path, rel: str) -> dict[str, Any]:
    path = repo_root / rel
    if not path.is_file():
        raise ValidationFail(f"missing contract: {rel}")
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Decision verification
# --------------------------------------------------------------------------- #

def verify_decision_text() -> None:
    got = recompute_decision_sha256(HUMAN_DECISION_TEXT_FA)
    if got != HUMAN_DECISION_TEXT_SHA256:
        raise ValidationFail(
            f"governance decision SHA-256 mismatch: {got} != "
            f"{HUMAN_DECISION_TEXT_SHA256}"
        )


def build_decision_record() -> dict[str, Any]:
    """Deterministic validation-architecture boundary decision record."""
    verify_decision_text()
    return {
        "decision_id": DECISION_ID,
        "decision_version": DECISION_VERSION,
        "decision_date": DECISION_DATE,
        "deciding_role": "human_supervisor_data_owner",
        "human_decision_text": HUMAN_DECISION_TEXT_FA,
        "human_decision_text_sha256": HUMAN_DECISION_TEXT_SHA256,
        "decision_locked": True,
        "applies_from": "stage126-m1-robustness-part2-listing-rule-b",
        "authorizes": dict(sorted(DECISION_AUTHORIZES.items())),
        "does_not_authorize": dict(sorted(DECISION_DOES_NOT_AUTHORIZE.items())),
        "architecture": {
            "stage125_part5_mode": "historical_immutable",
            "stage125_part5_is_live_successor_validator": False,
            "stage126_current_state_validation_surface": VALIDATOR_ID,
            "stage126_current_state_validator_version":
                HISTORICAL_DECISION_VALIDATOR_VERSION,
            "later_part_may_regenerate_earlier_part_verification_artifacts":
                False,
            "earlier_part_reopening_requires_scientific_error": True,
            "earlier_part_reopening_requires_new_human_authorization": True,
        },
        "boundary_prohibitions": dict(sorted(BOUNDARY_PROHIBITIONS.items())),
        "exception_policy": {
            "prior_part_reopening_default": PRIOR_PART_REOPENING_DEFAULT,
            "scientific_error_exception_requires": list(
                SCIENTIFIC_ERROR_EXCEPTION_REQUIRES
            ),
            "not_a_scientific_error": list(NOT_A_SCIENTIFIC_ERROR),
            "may_qualify_as_scientific_error": list(
                MAY_QUALIFY_AS_SCIENTIFIC_ERROR
            ),
            "validator_may_automatically_reopen_previous_part": False,
        },
        "stage125_part5_historical_provenance": dict(
            sorted(PART5_HISTORICAL_PROVENANCE.items())
        ),
    }


# --------------------------------------------------------------------------- #
# Frozen historical boundary manifest
# --------------------------------------------------------------------------- #

def tracked_stage125_files(repo_root: Path) -> list[str]:
    """Tracked `project/stage125/**` paths (deterministic, sorted)."""
    out = _git(repo_root, "ls-files", "--", STAGE125_TREE_REL)
    files = sorted(p for p in out.splitlines() if p.strip())
    if not files:
        raise ValidationFail("no tracked project/stage125 files found")
    return files


def stage125_tree_hashes(repo_root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for rel in tracked_stage125_files(repo_root):
        path = repo_root / rel
        if not path.is_file():
            raise ValidationFail(f"tracked Stage125 file missing on disk: {rel}")
        hashes[rel] = sha256_file(path)
    return hashes


def stage125_tree_digest(hashes: dict[str, str]) -> str:
    """Single aggregate digest over the sorted `sha  path` lines."""
    payload = "".join(f"{hashes[k]}  {k}\n" for k in sorted(hashes))
    return sha256_bytes(payload.encode("utf-8"))


def build_boundary_manifest(repo_root: Path) -> dict[str, Any]:
    """Hash-pinned record of every surface frozen by this decision."""
    part5 = {
        PART5_SOURCE_REL: require_file_hash(
            repo_root, PART5_SOURCE_REL, PART5_SOURCE_SHA256,
            label="frozen Part 5 source",
        ),
        PART5_RUNNER_REL: require_file_hash(
            repo_root, PART5_RUNNER_REL, PART5_RUNNER_SHA256,
            label="frozen Part 5 runner",
        ),
        PART5_TEST_REL: require_file_hash(
            repo_root, PART5_TEST_REL, PART5_TEST_SHA256,
            label="frozen Part 5 test",
        ),
    }
    tree = stage125_tree_hashes(repo_root)
    return {
        "contract_id": "stage126_historical_boundary_manifest",
        "contract_version": DECISION_VERSION,
        "decision_id": DECISION_ID,
        "stage125_part5_mode": "historical_immutable",
        "stage125_part5_frozen_files_sha256": dict(sorted(part5.items())),
        "stage125_tracked_file_count": len(tree),
        "stage125_tracked_files_sha256": dict(sorted(tree.items())),
        "stage125_tree_aggregate_sha256": stage125_tree_digest(tree),
        "primary_stage126_artifacts_sha256": dict(sorted(
            PINNED_PRIMARY_ARTIFACTS.items()
        )),
        "boundary_prohibitions": dict(sorted(BOUNDARY_PROHIBITIONS.items())),
        "stage125_part5_historical_provenance": dict(
            sorted(PART5_HISTORICAL_PROVENANCE.items())
        ),
        # Stage126+ Q1/Q2 Lean Governance: SCIENTIFIC artifact regeneration for
        # an already-closed part remains forbidden (enforced fail-closed by
        # verify_registry_immutability's SCIENTIFIC_GATE_BUCKETS). Operational
        # verification bookkeeping (test/QC/metadata hashes,
        # INFORMATIONAL_ONLY_BUCKETS) is git-versioned and mutable, and its
        # evolution is permitted without a new scientific-error exception or
        # human authorization.
        "prior_part_scientific_artifact_regeneration_forbidden": True,
        "prior_part_operational_verification_artifact_evolution_permitted": True,
    }


# --------------------------------------------------------------------------- #
# Generic per-part discovery (no per-part branching)
# --------------------------------------------------------------------------- #

def part_file_prefix(part_index: int) -> str:
    """Naming convention shared by every robustness micro-part package."""
    return f"stage126_m1_robustness_part{part_index}"


def discover_part(
    repo_root: Path, part_index: int, category_id: str,
) -> dict[str, Any] | None:
    """Discover a completed robustness micro-part package by convention.

    Returns ``None`` when the part has not been executed. Any half-present
    package (authorization without completion lock, or vice versa) fails closed.
    """
    prefix = part_file_prefix(part_index)
    auth_rel = f"{STAGE126_DIR_REL}/{prefix}_human_authorization_record.json"
    lock_rel = f"{STAGE126_DIR_REL}/{prefix}_completion_lock.json"
    meta_rel = f"{STAGE126_DIR_REL}/metadata_and_hashes_{prefix}.json"
    has_auth = (repo_root / auth_rel).is_file()
    has_lock = (repo_root / lock_rel).is_file()
    if not has_auth and not has_lock:
        return None
    if has_auth != has_lock:
        raise ValidationFail(
            f"part {part_index} package is half-present (authorization "
            f"{has_auth}, completion lock {has_lock}) — fail-closed"
        )
    auth = _read_json(repo_root, auth_rel)
    lock = _read_json(repo_root, lock_rel)
    meta = _read_json(repo_root, meta_rel) if (repo_root / meta_rel).is_file() else {}

    if auth.get("authorized_category_id") != category_id:
        raise ValidationFail(
            f"part {part_index} authorization category "
            f"{auth.get('authorized_category_id')!r} != {category_id!r}"
        )
    if lock.get("category_id") != category_id:
        raise ValidationFail(
            f"part {part_index} completion lock category "
            f"{lock.get('category_id')!r} != {category_id!r}"
        )
    if lock.get(f"part{part_index}_execution_completed") is not True:
        raise ValidationFail(f"part {part_index} completion lock is not completed")
    if lock.get(f"part{part_index}_human_authorized") is not True:
        raise ValidationFail(f"part {part_index} completion lock is not authorized")
    if lock.get("authorization_consumed") is not True:
        raise ValidationFail(f"part {part_index} authorization is not consumed")
    if lock.get("development_only") is not True:
        raise ValidationFail(f"part {part_index} is not development-only")
    # No standing authorization for the NEXT part.
    next_key = f"part{part_index + 1}_execution_authorized"
    if lock.get(next_key) is not False:
        raise ValidationFail(
            f"part {part_index} completion lock does not deny {next_key}"
        )
    for field in (
        "full_development_refit_performed", "final_test_unlocked",
        "final_test_access_authorized", "final_test_evaluation_performed",
        "smote_executed", "shap_executed",
        "replaces_primary_results", "selects_paper_winner",
    ):
        if lock.get(field) is not False:
            raise ValidationFail(
                f"part {part_index} completion lock field {field} is not False"
            )
    # Narrow Part 6 semantic rule: the sixth and final registered robustness
    # category changes ONLY the imbalance strategy (SMOTENC applied strictly
    # inside each training fold) — so it is the ONE category required to have
    # executed SMOTENC. Every other registered category (Parts 1-5) remains a
    # non-SMOTE scientific execution and must show `smotenc_executed=False`,
    # exactly as before.
    want_smotenc = category_id == SMOTE_ROBUSTNESS_CATEGORY_ID
    if lock.get("smotenc_executed") is not want_smotenc:
        raise ValidationFail(
            f"part {part_index} ({category_id}) completion lock field "
            f"smotenc_executed={lock.get('smotenc_executed')!r} != "
            f"{want_smotenc!r}"
        )
    return {
        "part_index": part_index,
        "category_id": category_id,
        "micro_part_id": derive_micro_part_id(repo_root, part_index, lock),
        "authorization_record": auth_rel,
        "completion_lock": lock_rel,
        "metadata_manifest": meta_rel if meta else "",
        "authorization_text_sha256": auth.get("human_authorization_text_sha256", ""),
        "next_category_id": lock.get("next_category_id", ""),
        "completed_category_ids": list(lock.get("completed_category_ids") or []),
        "lock": lock,
        "metadata": meta,
    }


def closed_part_entry(
    repo_root: Path, part: dict[str, Any],
) -> dict[str, Any]:
    """Immutable package contract for one completed micro-part.

    Built entirely from the part's own package by convention plus its own
    completion lock — no per-part constant, so a future part is covered the
    moment it lands.
    """
    files = part_package_files(repo_root, part["part_index"])
    lock = part["lock"]
    meta = part.get("metadata") or {}
    scientific = files["scientific"]
    if len(scientific) < 7:
        raise ValidationFail(
            f"part {part['part_index']} exposes only {len(scientific)} "
            f"scientific artifacts (expected the full package)"
        )
    # Cross-check the part's own metadata manifest where it declares a hash.
    for rel, got in scientific.items():
        name = rel.rsplit("/", 1)[-1]
        declared = (meta.get("output_files_sha256") or {}).get(name)
        if declared is not None and declared != got:
            raise ValidationFail(
                f"{part['category_id']} scientific artifact drifted from its "
                f"own metadata manifest: {name}"
            )
    return {
        "part_index": part["part_index"],
        "category_id": part["category_id"],
        "micro_part_id": part["micro_part_id"],
        "authorization_record": part["authorization_record"],
        "authorization_record_sha256": sha256_file(
            repo_root / part["authorization_record"]
        ),
        "authorization_text_sha256": part["authorization_text_sha256"],
        "authorization_consumed": lock.get("authorization_consumed") is True,
        "completion_lock": part["completion_lock"],
        "completion_lock_sha256": sha256_file(repo_root / part["completion_lock"]),
        "next_registered_category": part["next_category_id"],
        "final_test_lock_flags": {
            field: lock.get(field, False)
            for field in (
                "final_test_unlocked", "final_test_access_authorized",
                "final_test_evaluation_performed",
                "full_development_refit_performed",
            )
        },
        "scientific_artifacts_sha256": scientific,
        "verification_artifacts_sha256": files["verification"],
        "code_artifacts_sha256": files["code"],
    }


def micro_part_qc_pointers(
    repo_root: Path, part: dict[str, Any] | None,
) -> dict[str, Any]:
    """Pointers to the last completed SCIENTIFIC micro-part QC report.

    Derived from the part package by convention: the QC file lives at the part
    prefix, and its scope is the QC report's own ``stage``. Deliberately kept
    separate from the current-state validation pointers.
    """
    if not part:
        return {"scope": "", "path": "", "assertions": 0, "failed": 0}
    rel = f"{STAGE126_DIR_REL}/{part_file_prefix(part['part_index'])}_qc_report.json"
    if not (repo_root / rel).is_file():
        raise ValidationFail(f"completed part {part['part_index']} has no QC report")
    qc = _read_json(repo_root, rel)
    return {
        "scope": qc.get("stage", ""),
        "path": rel,
        "assertions": qc.get("assertion_count", 0),
        "failed": qc.get("failed_count", -1),
    }


def build_closed_part_registry(
    repo_root: Path, completed: list[dict[str, Any]],
) -> dict[str, Any]:
    """Generic registry of every CLOSED micro-part package.

    Scientific artifact hashes and completion/authorization/category identity
    are always recomputed fresh (they are frozen inputs, so this is a no-op
    cross-check, not a rewrite).

    Operational bookkeeping hashes (``code_artifacts_sha256`` /
    ``verification_artifacts_sha256``) are NOT a required live-state
    synchronization surface under Stage126+ Q1/Q2 Lean Governance: once a
    category is first registered, its operational hashes are carried forward
    from the COMMITTED registry unchanged rather than recomputed, so a
    routine test/QC/metadata edit on a closed part never requires
    "repinning" the registry. (Current, live operational-file hashes remain
    directly readable from disk for informational reporting; they are simply
    not written back into this registry.)
    """
    committed_path = repo_root / STAGE126_DIR_REL / F_CLOSED_REGISTRY
    committed_parts: dict[str, Any] = {}
    if committed_path.is_file():
        committed_parts = (
            json.loads(committed_path.read_text(encoding="utf-8")).get("parts")
            or {}
        )

    parts: dict[str, Any] = {}
    for p in completed:
        entry = closed_part_entry(repo_root, p)
        prior = committed_parts.get(p["category_id"])
        if prior is not None:
            for bucket in INFORMATIONAL_ONLY_BUCKETS:
                if bucket in prior:
                    entry[bucket] = prior[bucket]
        parts[p["category_id"]] = entry

    return {
        "contract_id": "stage126_closed_part_registry",
        "contract_version": VALIDATOR_VERSION,
        "decision_id": DECISION_ID,
        "closed_part_count": len(completed),
        "regeneration_allowed": False,
        "parts": parts,
    }


def verify_registry_immutability(
    repo_root: Path, generated: dict[str, Any],
) -> list[str]:
    """Every already-registered SCIENTIFIC artifact hash must still match.

    Compares the freshly computed registry against the COMMITTED registry on
    disk. Under Stage126+ Q1/Q2 Lean Governance, only
    ``SCIENTIFIC_GATE_BUCKETS`` (scientific artifact hashes) and completion/
    category identity fields are live scientific gates for a closed part; a
    completed micro-part may never be removed, and its scientific artifacts
    may never change.

    ``INFORMATIONAL_ONLY_BUCKETS`` (test/QC/metadata bookkeeping hashes) are
    retained in the registry as historical provenance only: their drift is
    returned for reporting but never raises, because tests, QC formatting and
    metadata bookkeeping are operational/engineering surfaces, not scientific
    control surfaces (see project/docs/ai/STAGE126_Q1Q2_LEAN_GOVERNANCE.md
    sections 2-3).

    Returns the list of informational (non-fatal) drift entries; raises on any
    scientific or identity drift.
    """
    committed_path = repo_root / STAGE126_DIR_REL / F_CLOSED_REGISTRY
    if not committed_path.is_file():
        return []
    committed = json.loads(committed_path.read_text(encoding="utf-8"))
    fatal: list[str] = []
    informational: list[str] = []
    for category, entry in (committed.get("parts") or {}).items():
        fresh = (generated.get("parts") or {}).get(category)
        if fresh is None:
            raise ValidationFail(
                f"closed part {category!r} disappeared from the registry — a "
                f"completed micro-part may never be removed"
            )
        for bucket in SCIENTIFIC_GATE_BUCKETS:
            for rel, want in (entry.get(bucket) or {}).items():
                got = (fresh.get(bucket) or {}).get(rel)
                if got != want:
                    fatal.append(f"{bucket}:{rel}")
        for bucket in INFORMATIONAL_ONLY_BUCKETS:
            for rel, want in (entry.get(bucket) or {}).items():
                got = (fresh.get(bucket) or {}).get(rel)
                if got != want:
                    informational.append(f"{bucket}:{rel}")
        for field in ("authorization_record_sha256", "completion_lock_sha256",
                      "authorization_text_sha256", "micro_part_id",
                      "category_id", "part_index", "next_registered_category"):
            if entry.get(field) != fresh.get(field):
                fatal.append(f"{field}:{category}")
    if fatal:
        raise ValidationFail(
            "closed micro-part scientific/identity drift (regeneration or "
            f"mutation of a closed part's scientific state is forbidden): "
            f"{sorted(fatal)}"
        )
    return informational


def completed_prefix(
    repo_root: Path, execution_order: list[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Completed CONTIGUOUS prefix of the registered execution order.

    Fails closed when a category is skipped (a later package exists while an
    earlier one does not).
    """
    discovered: list[dict[str, Any] | None] = [
        discover_part(repo_root, i, category)
        for i, category in enumerate(execution_order, start=1)
    ]
    completed: list[dict[str, Any]] = []
    for i, part in enumerate(discovered):
        if part is None:
            later = [
                execution_order[j] for j in range(i + 1, len(discovered))
                if discovered[j] is not None
            ]
            if later:
                raise ValidationFail(
                    f"registered category {execution_order[i]!r} is not "
                    f"completed but later categories exist: {later} — a "
                    f"category may not be skipped"
                )
            break
        completed.append(part)
    return completed, [p["category_id"] for p in completed]


# --------------------------------------------------------------------------- #
# Stage126-native contract validation
# --------------------------------------------------------------------------- #

def verify_part0_contract(repo_root: Path) -> dict[str, Any]:
    require_file_hash(
        repo_root, PART0_DECISION_RECORD_REL, PART0_DECISION_RECORD_SHA256,
        label="Part 0 decision record",
    )
    record = _read_json(repo_root, PART0_DECISION_RECORD_REL)
    exact = {
        "contract_id": "stage126_m1_robustness_execution_contract",
        "contract_version": "stage126_m1_robustness_execution_contract_v1",
        "decision_locked": True,
        "one_category_per_micro_part_pr": True,
        "each_part_requires_separate_human_authorization": True,
    }
    for key, want in exact.items():
        if record.get(key) != want:
            raise ValidationFail(
                f"Part 0 contract field {key}={record.get(key)!r} != {want!r}"
            )
    order = list(record.get("execution_order") or [])
    if len(order) != 6:
        raise ValidationFail(f"Part 0 execution_order has {len(order)} != 6 entries")
    return record


def verify_primary_stage126_artifacts(repo_root: Path) -> dict[str, str]:
    observed: dict[str, str] = {}
    for rel, expected in sorted(PINNED_PRIMARY_ARTIFACTS.items()):
        observed[rel] = require_file_hash(
            repo_root, rel, expected, label="primary Stage126 artifact",
        )
    return observed


def verify_final_test_lock(repo_root: Path) -> dict[str, Any]:
    """The locked final test must remain inaccessible on every surface."""
    guard = _read_json(repo_root, FINAL_TEST_LOCK_GUARD_REL)
    lock = _read_json(repo_root, PRIMARY_DEVELOPMENT_LOCK_REL)
    for source, name in ((guard, "final-test lock guard"),
                         (lock, "primary development lock")):
        for field in FINAL_TEST_LOCK_FIELDS:
            if field in source and source.get(field) is not False:
                raise ValidationFail(
                    f"{name} field {field} is not False (final test must stay locked)"
                )
    return {"final_test_lock_guard": guard, "primary_development_lock": lock}


def verify_selected_configurations(repo_root: Path) -> dict[str, str]:
    data = _read_json(repo_root, SELECTED_CONFIGURATIONS_REL)
    expected = {
        "regularized_logistic_regression": "logistic__C_0.1",
        "random_forest": "rf__depth_3__maxfeat_'sqrt'__leaf_10",
        "xgboost": "xgboost__lr_0.03__depth_2__mcw_1__lambda_1",
    }
    for family, cid in expected.items():
        if family not in data:
            raise ValidationFail(f"selected configurations missing {family}")
        if data[family].get("configuration_id") != cid:
            raise ValidationFail(
                f"selected configuration {family} "
                f"{data[family].get('configuration_id')!r} != {cid!r}"
            )
    return expected


def verify_handoff(
    repo_root: Path, completed_ids: list[str], *,
    last_micro_part: str = "", micro_qc: dict[str, Any] | None = None,
    strict_pointers: bool = True, m1_robustness_completed: bool = False,
) -> dict[str, Any]:
    """Validate the live Handoff — WITHOUT the frozen Part 5 validator.

    Enforces, fail-closed and inside this function:
      * every required validation-architecture field, exactly;
      * the current-state validation pointers, kept DISTINCT from the last
        scientific micro-part QC pointers;
      * the completed-category list and the derived last micro-part.

    ``strict_pointers`` is False only during the bootstrap ``--build`` that
    first creates these artifacts: a MISSING pointer is then tolerated, but a
    pointer that is present and WRONG always fails.
    """
    state = _read_json(repo_root, HANDOFF_STATE_REL)

    # (1) Architecture fields — always strict, never merely reported.
    for key, want in REQUIRED_HANDOFF_ARCHITECTURE_FIELDS.items():
        if key not in state:
            raise ValidationFail(
                f"Handoff is missing required architecture field {key!r}"
            )
        if state.get(key) != want:
            raise ValidationFail(
                f"Handoff architecture field {key}={state.get(key)!r} != {want!r}"
            )

    # (2) Current-state validation pointers must be unambiguous and correct.
    pointer_expected = {
        "current_state_validation_scope": CURRENT_STATE_QC_SCOPE,
        "current_state_validation_path": CURRENT_STATE_QC_PATH,
        "current_state_validation_metadata_path": CURRENT_STATE_QC_METADATA_PATH,
        "current_state_validation_failed": 0,
        "current_state_validation_all_pass": True,
    }
    for key, want in pointer_expected.items():
        if key not in state:
            if strict_pointers:
                raise ValidationFail(
                    f"Handoff is missing current-state validation field {key!r}"
                )
            continue
        if state.get(key) != want:
            raise ValidationFail(
                f"Handoff current-state field {key}={state.get(key)!r} != {want!r}"
            )
    # The scientific micro-part QC must be reported SEPARATELY and truthfully.
    if last_micro_part:
        mq = micro_qc or {}
        for key, want in (
            ("last_completed_micro_part_qc_scope", mq.get("scope")),
            ("last_completed_micro_part_qc_path", mq.get("path")),
            ("last_completed_micro_part_qc_assertions", mq.get("assertions")),
            ("last_completed_micro_part_qc_failed", mq.get("failed")),
        ):
            if key not in state:
                if strict_pointers:
                    raise ValidationFail(f"Handoff is missing {key!r}")
                continue
            if state[key] != want:
                raise ValidationFail(
                    f"Handoff {key}={state[key]!r} != actual {want!r}"
                )
        declared = state.get("last_completed_micro_part_qc_path")
        if declared and not (repo_root / declared).is_file():
            raise ValidationFail(
                f"Handoff micro-part QC path points at a missing file: {declared}"
            )
        if state.get("last_completed_micro_part") != last_micro_part:
            raise ValidationFail(
                f"Handoff last_completed_micro_part="
                f"{state.get('last_completed_micro_part')!r} != "
                f"{last_micro_part!r}"
            )

    exact: dict[str, Any] = {
        "active_workstream": expected_active_workstream(repo_root),
        "next_research_action_id": expected_next_research_action_id(
            repo_root, m1_robustness_completed,
        ),
        "m1_robustness_started": True,
        "m1_robustness_completed": m1_robustness_completed,
        "m1_robustness_execution_authorized": False,
        "full_development_refit_performed": False,
    }
    for field in FINAL_TEST_LOCK_FIELDS:
        exact[field] = False
    for key, want in exact.items():
        if state.get(key) != want:
            raise ValidationFail(
                f"Handoff field {key}={state.get(key)!r} != {want!r}"
            )
    if list(state.get("m1_robustness_completed_category_ids") or []) != completed_ids:
        raise ValidationFail(
            f"Handoff completed categories "
            f"{state.get('m1_robustness_completed_category_ids')!r} != "
            f"{completed_ids!r}"
        )
    return state


def verify_no_unauthorized_execution(
    repo_root: Path, execution_order: list[str], completed: list[dict[str, Any]],
) -> str:
    """No package may exist for a category beyond the completed prefix."""
    next_index = len(completed) + 1
    for i in range(next_index, len(execution_order) + 1):
        prefix = part_file_prefix(i)
        for suffix in ("_completion_lock.json",
                       "_human_authorization_record.json",
                       "_oof_predictions.csv", "_metrics.csv"):
            path = repo_root / STAGE126_DIR_REL / f"{prefix}{suffix}"
            if path.is_file():
                raise ValidationFail(
                    f"unauthorized artifact for uncompleted category "
                    f"{execution_order[i - 1]!r}: {prefix}{suffix}"
                )
    if next_index > len(execution_order):
        return ""
    return execution_order[next_index - 1]


# --------------------------------------------------------------------------- #
# Validation report + assertions
# --------------------------------------------------------------------------- #

def build_validation_report(
    repo_root: Path, *, execution_order: list[str],
    completed: list[dict[str, Any]], completed_ids: list[str],
    next_category: str, registry: dict[str, Any],
    primary_observed: dict[str, str], handoff: dict[str, Any],
    last_micro_part: str, micro_qc: dict[str, Any],
) -> dict[str, Any]:
    return {
        "contract_id": VALIDATOR_ID,
        "contract_version": VALIDATOR_VERSION,
        "decision_id": DECISION_ID,
        "validation_architecture": VALIDATOR_VERSION,
        "stage125_part5_mode": "historical_immutable",
        "stage125_part5_live_gate_active": False,
        "stage125_part5_executed_by_this_validator": False,
        "stage125_part5_imported_by_this_validator": False,
        "registered_execution_order": list(execution_order),
        # Derived, never hard-coded: execution_order[:n] and execution_order[n].
        "completed_part_count": len(completed),
        "expected_completed_prefix": execution_order[:len(completed)],
        "completed_category_ids": list(completed_ids),
        "completed_micro_parts": [
            {
                "part_index": p["part_index"],
                "category_id": p["category_id"],
                "authorization_record": p["authorization_record"],
                "completion_lock": p["completion_lock"],
                "authorization_text_sha256": p["authorization_text_sha256"],
                "micro_part_id": p["micro_part_id"],
            }
            for p in completed
        ],
        "next_category_id": next_category,
        "next_category_authorized": False,
        "standing_execution_authorization": False,
        "m1_robustness_started": True,
        "m1_robustness_completed": (
            len(completed) == len(execution_order) and len(execution_order) > 0
        ),
        "full_development_refit_performed": False,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_predictor_values_inspected": False,
        "final_test_target_values_inspected": False,
        "final_test_evaluation_performed": False,
        # Derived from the newest completion lock / per-part QC contract.
        "last_completed_micro_part": last_micro_part,
        "current_state_validation_scope": CURRENT_STATE_QC_SCOPE,
        "current_state_validation_path": CURRENT_STATE_QC_PATH,
        "current_state_validation_metadata_path": CURRENT_STATE_QC_METADATA_PATH,
        "last_completed_micro_part_qc_scope": micro_qc["scope"],
        "last_completed_micro_part_qc_path": micro_qc["path"],
        "last_completed_micro_part_qc_assertions": micro_qc["assertions"],
        "last_completed_micro_part_qc_failed": micro_qc["failed"],
        "active_workstream": expected_active_workstream(repo_root),
        "next_research_action_id": expected_next_research_action_id(
            repo_root,
            len(completed) == len(execution_order) and len(execution_order) > 0,
        ),
        "closed_part_registry": registry,
        "primary_stage126_artifacts_sha256": dict(sorted(primary_observed.items())),
        "prior_part_scientific_artifact_regeneration_forbidden": True,
        "prior_part_operational_verification_artifact_evolution_permitted": True,
        "prior_part_reopening_requires_scientific_error": True,
        "prior_part_reopening_requires_explicit_human_authorization": True,
        "validator_reopened_a_previous_part": False,
    }


def build_assertions(
    repo_root: Path, *, decision: dict[str, Any], manifest: dict[str, Any],
    report: dict[str, Any], execution_order: list[str],
    completed: list[dict[str, Any]], handoff: dict[str, Any],
    source_text: str, registry_drift: list[str],
) -> list[dict[str, Any]]:
    a: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        a.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    # Governance decision.
    add("decision_text_hash_exact",
        recompute_decision_sha256(decision["human_decision_text"])
        == HUMAN_DECISION_TEXT_SHA256
        == decision["human_decision_text_sha256"])
    add("decision_locked", decision["decision_locked"] is True)
    add("decision_authorizes_boundary_lock_only",
        decision["authorizes"] == dict(sorted(DECISION_AUTHORIZES.items())))
    add("decision_denies_merge_part3_refit_final_test",
        decision["does_not_authorize"]
        == dict(sorted(DECISION_DOES_NOT_AUTHORIZE.items())))

    # Frozen Stage125 Part 5 boundary.
    add("part5_source_hash_pinned",
        manifest["stage125_part5_frozen_files_sha256"][PART5_SOURCE_REL]
        == PART5_SOURCE_SHA256)
    add("part5_runner_hash_pinned",
        manifest["stage125_part5_frozen_files_sha256"][PART5_RUNNER_REL]
        == PART5_RUNNER_SHA256)
    add("part5_test_hash_pinned",
        manifest["stage125_part5_frozen_files_sha256"][PART5_TEST_REL]
        == PART5_TEST_SHA256)
    add("stage125_tree_fully_pinned",
        manifest["stage125_tracked_file_count"]
        == len(manifest["stage125_tracked_files_sha256"])
        and bool(manifest["stage125_tree_aggregate_sha256"]))
    add("part5_mode_is_historical_immutable",
        manifest["stage125_part5_mode"] == "historical_immutable"
        and report["stage125_part5_mode"] == "historical_immutable")
    add("part5_live_gate_inactive",
        report["stage125_part5_live_gate_active"] is False)
    add("part5_provenance_is_not_a_live_gate",
        PART5_HISTORICAL_PROVENANCE["is_required_live_stage126_gate"] is False
        and PART5_HISTORICAL_PROVENANCE["executed_by_this_validator"] is False)
    add("boundary_prohibitions_all_false",
        all(v is False for v in manifest["boundary_prohibitions"].values())
        and set(manifest["boundary_prohibitions"]) == set(BOUNDARY_PROHIBITIONS))

    # Validator independence — proven structurally from this module's own AST.
    coupling = part5_coupling_findings(source_text)
    add("validator_does_not_import_or_invoke_part5",
        coupling == [], str(coupling))
    add("part5_module_not_loaded_into_this_namespace",
        not any(
            FORBIDDEN_PART5_MODULE_FRAGMENT in str(v)
            for k, v in globals().items()
            if k.startswith("_") is False and hasattr(v, "__file__")
        ))
    add("validator_declares_no_part5_execution",
        report["stage125_part5_executed_by_this_validator"] is False
        and report["stage125_part5_imported_by_this_validator"] is False)

    # Stage126-native contracts.
    add("part0_execution_order_is_six_registered_categories",
        len(execution_order) == 6)
    add("primary_stage126_artifacts_immutable",
        report["primary_stage126_artifacts_sha256"]
        == dict(sorted(PINNED_PRIMARY_ARTIFACTS.items())))

    # Completed contiguous prefix — derived, not pinned to any part number.
    n = report["completed_part_count"]
    add("completed_prefix_is_execution_order_prefix",
        list(report["completed_category_ids"]) == execution_order[:n]
        == report["expected_completed_prefix"],
        str(report["completed_category_ids"]))
    add("completed_part_count_matches_discovered_packages",
        n == len(completed), str(n))
    add("next_category_is_the_next_registered_entry",
        report["next_category_id"]
        == (execution_order[n] if n < len(execution_order) else ""),
        report["next_category_id"])
    add("next_category_not_authorized",
        report["next_category_authorized"] is False)
    add("no_standing_execution_authorization",
        report["standing_execution_authorization"] is False
        and handoff.get("m1_robustness_execution_authorized") is False)
    # Derived, never hard-coded to False: becomes True exactly when every
    # registered category (all six) is completed (Part 6 closes the set).
    expected_m1_robustness_completed = (
        n == len(execution_order) and len(execution_order) > 0
    )
    add("m1_robustness_completed_state_is_derived_and_consistent",
        report["m1_robustness_completed"] == expected_m1_robustness_completed
        and handoff.get("m1_robustness_completed")
        == expected_m1_robustness_completed)

    # Per-part locks agree with the registered order.
    for part in completed:
        idx = part["part_index"]
        add(f"part{idx}_lock_next_category_is_registered_successor",
            part["next_category_id"] == execution_order[idx]
            if idx < len(execution_order) else True)
        add(f"part{idx}_lock_completed_prefix_exact",
            part["completed_category_ids"] == execution_order[:idx])
        add(f"part{idx}_authorization_hash_recorded",
            len(part["authorization_text_sha256"]) == 64)

    # Immutable scientific surfaces of closed micro-part packages.
    registry_parts = report["closed_part_registry"]["parts"]
    add("closed_part_registry_covers_every_completed_part",
        sorted(registry_parts) == sorted(report["completed_category_ids"]))
    for category, entry in sorted(registry_parts.items()):
        add(f"scientific_artifacts_pinned[{category}]",
            len(entry["scientific_artifacts_sha256"]) >= 7
            and all(len(h) == 64
                    for h in entry["scientific_artifacts_sha256"].values()))
        # QC report + metadata manifest + README are the universal minimum; the
        # Part 5 compatibility record exists only for the pre-freeze parts.
        add(f"verification_artifacts_pinned[{category}]",
            len(entry["verification_artifacts_sha256"]) >= 3
            and all(len(h) == 64
                    for h in entry["verification_artifacts_sha256"].values()))
        add(f"code_artifacts_pinned[{category}]",
            len(entry["code_artifacts_sha256"]) >= 1)
        add(f"authorization_consumed[{category}]",
            entry["authorization_consumed"] is True)
        add(f"final_test_locked_in_lock[{category}]",
            all(x is False for x in entry["final_test_lock_flags"].values()))
    # `registry_drift` reaches here only with INFORMATIONAL bucket drift
    # (code_artifacts_sha256 / verification_artifacts_sha256): scientific and
    # identity drift already raised inside verify_registry_immutability. This
    # assertion is therefore reporting-only and never fails the live gate for
    # test/QC/metadata bookkeeping changes on a closed part.
    add("closed_part_registry_scientific_state_immutable", True,
        f"informational_operational_drift={registry_drift}")

    # Final-test lock.
    add("final_test_locked_everywhere",
        all(report[f] is False for f in FINAL_TEST_LOCK_FIELDS)
        and all(handoff.get(f) is False for f in FINAL_TEST_LOCK_FIELDS))
    add("no_full_development_refit",
        report["full_development_refit_performed"] is False)

    # Earlier-part protection + exception policy. Under Stage126+ Q1/Q2 Lean
    # Governance, only SCIENTIFIC artifact regeneration for a closed part
    # remains forbidden (the real enforcement is
    # verify_registry_immutability's SCIENTIFIC_GATE_BUCKETS check, which
    # already ran and would have raised before this assertion is reached).
    # Operational verification-artifact bookkeeping is explicitly PERMITTED
    # to evolve without a new scientific-error exception or authorization.
    add("prior_part_scientific_artifact_regeneration_forbidden",
        report["prior_part_scientific_artifact_regeneration_forbidden"] is True
        and manifest[
            "prior_part_scientific_artifact_regeneration_forbidden"
        ] is True)
    add("prior_part_operational_verification_artifact_evolution_permitted",
        report["prior_part_operational_verification_artifact_evolution_permitted"]
        is True
        and manifest[
            "prior_part_operational_verification_artifact_evolution_permitted"
        ] is True)
    add("prior_part_reopening_requires_error_and_authorization",
        report["prior_part_reopening_requires_scientific_error"] is True
        and report[
            "prior_part_reopening_requires_explicit_human_authorization"
        ] is True
        and decision["exception_policy"]["prior_part_reopening_default"]
        == PRIOR_PART_REOPENING_DEFAULT)
    add("validator_never_reopens_a_previous_part",
        report["validator_reopened_a_previous_part"] is False
        and decision["exception_policy"][
            "validator_may_automatically_reopen_previous_part"
        ] is False)
    add("exception_policy_requirements_exact",
        tuple(decision["exception_policy"]["scientific_error_exception_requires"])
        == SCIENTIFIC_ERROR_EXCEPTION_REQUIRES)
    add("handoff_timestamp_and_test_hash_are_not_scientific_errors",
        "new Handoff timestamp" in NOT_A_SCIENTIFIC_ERROR
        and "new current test hash" in NOT_A_SCIENTIFIC_ERROR
        and "new branch SHA" in NOT_A_SCIENTIFIC_ERROR
        and "new completed robustness part" in NOT_A_SCIENTIFIC_ERROR)

    # Research pointers: the active workstream never advances per-part, but
    # the next research action legitimately transitions exactly once, when
    # all six registered M1 robustness categories are complete.
    add("research_pointers_consistent_with_m1_robustness_state",
        report["active_workstream"] == expected_active_workstream(repo_root)
        and report["next_research_action_id"] == expected_next_research_action_id(
            repo_root, expected_m1_robustness_completed,
        ))
    add("last_completed_micro_part_derived",
        bool(report["last_completed_micro_part"])
        and report["last_completed_micro_part"]
        == (completed[-1]["micro_part_id"] if completed else ""))
    # Current-state QC and the last scientific micro-part QC are separate roles.
    add("current_state_qc_pointers_exact",
        report["current_state_validation_scope"] == CURRENT_STATE_QC_SCOPE
        and report["current_state_validation_path"] == CURRENT_STATE_QC_PATH
        and report["current_state_validation_metadata_path"]
        == CURRENT_STATE_QC_METADATA_PATH)
    add("micro_part_qc_pointer_is_distinct_from_current_state_qc",
        report["last_completed_micro_part_qc_scope"]
        != report["current_state_validation_scope"]
        and report["last_completed_micro_part_qc_path"]
        != report["current_state_validation_path"]
        and (repo_root / report["last_completed_micro_part_qc_path"]).is_file())
    add("handoff_architecture_fields_enforced",
        all(handoff.get(k) == want
            for k, want in REQUIRED_HANDOFF_ARCHITECTURE_FIELDS.items()))

    # --- Stage127 human-review closure ------------------------------------ #
    # A completed Stage128 D2 design freeze IS the human decision that the
    # terminal Stage127 FAIL result was waiting for. The repository must not
    # simultaneously claim that the freeze is complete AND that Stage127 is
    # still pending human review / still requires a human decision: that is an
    # internal contradiction, and this assertion fails on it. The historical
    # D0 Gate result itself is never allowed to change.
    freeze_done = stage128_m2_d2_design_freeze_completed(repo_root)
    add("stage128_freeze_closes_stage127_pending_human_review",
        stage127_human_review_closure_consistent(
            handoff, freeze_completed=freeze_done),
        "stage128_m2_d2_design_freeze_completed=True requires both Stage127 "
        "pending-human-review markers to be False")
    # --- Live labels must not be stale ------------------------------------ #
    # `current_stage` / `active_workstream` claim to describe the CURRENT live
    # research state. Leaving them at Stage126 / stage126_m1_financial_baseline
    # after the Stage128 D2 freeze completes produces exactly the ambiguity
    # this guard forbids: a snapshot naming the Stage126 M1 workstream beside a
    # canonical state whose pointers have advanced to stage128-m2-d2-gate-rerun.
    add("current_state_labels_not_stale_after_stage128_freeze",
        current_state_labels_are_not_stale(
            handoff, freeze_completed=freeze_done),
        f"stage128_m2_d2_design_freeze_completed=True requires "
        f"current_stage={STAGE128_CURRENT_STAGE} and "
        f"active_workstream={STAGE128_ACTIVE_WORKSTREAM}")
    # The workstream label is a WORKSTREAM name derived from the frozen action;
    # it must never be substituted for either authoritative research-action id.
    add("stage128_workstream_id_does_not_replace_research_action_ids",
        (not freeze_done)
        or (handoff.get("last_completed_research_action_id")
            not in (STAGE128_ACTIVE_WORKSTREAM,
                    STAGE128_ACTIVE_WORKSTREAM.replace("_", "-"))
            and handoff.get("next_research_action_id")
            not in (STAGE128_ACTIVE_WORKSTREAM,
                    STAGE128_ACTIVE_WORKSTREAM.replace("_", "-"))),
        "the Stage128 workstream label is derived from the frozen action and "
        "must never be used as, or alter, a research-action id")
    add("stage127_human_review_history_not_erased",
        (not freeze_done)
        or (handoff.get("stage127_m2_human_review_originally_required") is True
            and handoff.get("stage127_m2_human_review_resolved_by_action_id")
            == "stage128-m2-boundary-month-return-design-freeze"),
        "the historical fact that Stage127 originally required human review "
        "must be preserved, together with the action that discharged it")
    # Execution facts recorded by a LATER, separately authorized action are
    # not something the freeze or the data-admission Gate did. Once the
    # authorized paired M2 evaluation has run, `m2_started`,
    # `m2_modeling_started` and the block-admission field record that
    # execution; the AUTHORIZATION fields below stay checked either way.
    m2_evaluation_done = stage127_m2_incremental_evaluation_completed(repo_root)
    _execution_fact_fields = (
        "m2_modeling_started", "m2_started", "m2_block_admitted_for_modeling",
    )

    def _authorization_only(fields: tuple[str, ...]) -> tuple[str, ...]:
        if not m2_evaluation_done:
            return fields
        return tuple(f for f in fields if f not in _execution_fact_fields)

    add("stage128_freeze_authorizes_nothing_further",
        (not freeze_done)
        or all(handoff.get(k) is False for k in _authorization_only((
            "stage128_m2_d2_gate_rerun_authorized",
            "m2_incremental_evaluation_authorized",
            "m2_modeling_started",
            "final_test_unlocked",
        ))),
        "advancing the live stage/workstream labels must not authorize the D2 "
        "Gate re-run, M2 evaluation, M2 modeling or final-test access")
    # --- Stage128 D2 Gate re-run: data admission authorizes nothing ------- #
    rerun_done = stage128_m2_d2_gate_rerun_executed(repo_root)
    add("stage128_d2_gate_rerun_authorization_is_consumed_not_standing",
        (not rerun_done)
        or (handoff.get("stage128_m2_d2_gate_rerun_authorized") is False
            and handoff.get("stage128_m2_d2_gate_rerun_authorization_consumed")
            is True),
        "the one-action Gate re-run authorization is consumed by its "
        "execution and must never be left standing")
    add("stage128_d2_gate_rerun_pass_does_not_authorize_m2",
        (not rerun_done)
        or all(handoff.get(k) is False for k in _authorization_only((
            "m2_incremental_evaluation_authorized",
            "m2_modeling_started",
            "m2_authorized",
            "m2_started",
            "m2_block_admitted_for_modeling",
            "final_test_unlocked",
            "final_test_access_authorized",
            "final_test_evaluation_performed",
        ))),
        "a DATA-ADMISSION PASS makes the successor eligible, never "
        "authorized: no M2 authorization, no modeling, no final-test unlock. "
        "Modeling that a LATER separately-authorized action actually executed "
        "is a different fact and is asserted separately.")
    add("stage128_d2_gate_rerun_result_is_terminal_and_recorded",
        (not rerun_done)
        or (handoff.get("stage128_m2_d2_gate_rerun_executed") is True
            and handoff.get("stage128_m2_d2_gate_rerun_resolved") is True
            and handoff.get("stage128_m2_d2_gate_rerun_status") in (
                STAGE128_M2_D2_GATE_RERUN_PASS,
                STAGE128_M2_D2_GATE_RERUN_FAIL)),
        "the Gate re-run must record a terminal, resolved result")
    add("stage127_historical_d0_gate_status_preserved",
        stage127_historical_d0_gate_status_preserved(handoff),
        f"historical D0 Gate status must remain "
        f"{STAGE127_HISTORICAL_D0_GATE_STATUS}")
    current_state_text = ""
    cs_path = repo_root / CURRENT_STATE_MD_REL
    if cs_path.is_file():
        current_state_text = cs_path.read_text(encoding="utf-8")
    add("current_state_renders_stage128_section_after_freeze",
        (not freeze_done)
        or ("## Stage128 — M2 D2 boundary-month equity-return design freeze"
            in current_state_text),
        "CURRENT_STATE.md must render an explicit Stage128 D2 design-freeze "
        "section once the freeze is completed")
    add("current_state_does_not_call_stage127_the_current_action_after_freeze",
        (not freeze_done)
        or ("_The current scientific action. Its human authorization already "
            "exists" not in current_state_text),
        "after the freeze, Stage127 must be rendered as a HISTORICAL "
        "completed/resolved Gate, not as the current scientific action")
    # --- exactly one CURRENT scientific-action section after the rerun ---- #
    # `rerun_done` is derived from the decision artifact; the rendered
    # narrative must agree with it or the validator fails closed.
    rerun_complete = bool(
        rerun_done
        and handoff.get("stage128_m2_d2_gate_rerun_executed") is True
        and handoff.get("stage128_m2_d2_gate_rerun_resolved") is True
    )
    current_headings = [
        ln for ln in current_state_text.splitlines()
        if ln.startswith("## ") and "(CURRENT)" in ln
    ]
    add("current_state_freeze_section_not_current_after_gate_rerun",
        (not rerun_complete)
        or ("## Stage128 — M2 D2 boundary-month equity-return design freeze "
            "(CURRENT)" not in current_state_text),
        "once the D2 Gate re-run is executed and resolved, the design-freeze "
        "section must render as historical/completed frozen-design context, "
        "never as (CURRENT)")
    add("current_state_has_exactly_one_current_scientific_action_section",
        (not rerun_complete) or len(current_headings) == 1,
        "exactly one scientific-action section may be presented as "
        f"(CURRENT); found {len(current_headings)}: {current_headings}")
    m2_eval_done = m2_evaluation_done
    # The HUMAN retained-block decision is a separate, later action. Until it
    # is recorded, retention must stay open; once it is recorded, retention is
    # decided and the assertions below flip to the decided-state expectations.
    retained_block_done = stage128_m2_retained_block_decision_completed(
        repo_root)
    expected_current = (
        "M2 retained-block HUMAN decision" if retained_block_done
        else "paired M2 vs M1 incremental evaluation" if m2_eval_done
        else "Gate RE-RUN"
    )
    add("current_state_current_section_is_the_live_action",
        (not rerun_complete)
        or (len(current_headings) == 1
            and expected_current in current_headings[0]),
        "the sole CURRENT section must be the newest completed scientific "
        f"action (expected marker: {expected_current!r})")
    add("current_state_m2_evaluation_section_not_current_after_decision",
        (not retained_block_done)
        or ("## Stage127 — paired M2 vs M1 incremental evaluation (CURRENT)"
            not in current_state_text),
        "once the human retained-block decision is recorded, the paired "
        "evaluation section becomes historical evidence context")
    add("current_state_gate_rerun_section_not_current_after_successor",
        (not m2_eval_done)
        or ("## Stage128 — canonical M2 Gate RE-RUN under Gregorian D2 "
            "(CURRENT)" not in current_state_text),
        "once the authorized paired M2 evaluation completes, the Gate re-run "
        "section becomes historical data-admission context")
    add("m2_incremental_evaluation_authorization_is_consumed_not_standing",
        (not m2_eval_done)
        or (handoff.get("m2_incremental_evaluation_authorized") is False
            and handoff.get(
                "stage127_m2_incremental_evaluation_authorization_consumed")
            is True),
        "the one-action M2 evaluation authorization is consumed by its "
        "execution and must never be left standing")
    # NB: `m2_modeling_started` is deliberately NOT in this list. The
    # authorized development modeling WAS executed; equating "no winner and no
    # retained block" with "modeling never started" would misreport the live
    # state. Execution, authorization and retention are checked separately.
    add("m2_evaluation_selects_no_winner_and_retains_no_block",
        (not m2_eval_done)
        or all(handoff.get(k) is False for k in (
            *(() if retained_block_done else ("m2_block_retained",)),
            "paper_winner_selected",
            "final_model_selected",
            "full_development_refit_performed",
            "final_test_unlocked", "final_test_access_authorized",
            "final_test_evaluation_performed",
            "m3_started", "m3_authorized", "m4_started", "m4_authorized",
        )),
        "the paired development comparison retains nothing, selects no "
        "winner, unlocks no final test and starts no successor block")
    add("completed_m2_evaluation_with_44_fits_implies_modeling_started",
        (not m2_eval_done)
        or (handoff.get(
            "stage127_m2_incremental_evaluation_primary_model_fits") == 44
            and handoff.get("m2_modeling_started") is True
            and handoff.get("m2_started") is True
            and handoff.get("m2_block_admitted_for_modeling") is True),
        "a completed incremental evaluation with 44 canonical primary fits "
        "must report M2 modeling as STARTED and the block as admitted; a "
        "consumed authorization never erases the executed modeling")
    add("m2_evaluation_consumed_authorization_stays_false",
        (not m2_eval_done)
        or (handoff.get("m2_incremental_evaluation_authorized") is False
            and handoff.get(
                "stage127_m2_incremental_evaluation_authorization_consumed")
            is True),
        "the consumed one-action authorization must remain False")
    add("m2_block_retained_remains_false_pending_human_decision",
        (not m2_eval_done) or retained_block_done
        or (handoff.get("m2_block_retained") is False
            and handoff.get("m2_retained_block_decision_required") is True),
        "retention stays undecided until a human decides it")
    add("m3_and_m4_remain_unauthorized_and_unstarted",
        (not m2_eval_done)
        or all(handoff.get(k) is False for k in (
            "m3_started", "m3_authorized", "m4_started", "m4_authorized")),
        "the completed M2 evaluation starts and authorizes no successor block")
    add("completed_m2_evaluation_implies_market_data_collected_and_"
        "materialized",
        (not m2_eval_done)
        or all(handoff.get(k) is True for k in (
            "m2_market_data_evidence_collected",
            "m2_market_data_evidence_validated",
            "m2_data_entered_authorized_incremental_modeling_pipeline",
            "m2_incremental_evaluation_data_materialized",
        )),
        "a completed M2 evaluation implies the market evidence was collected, "
        "validated and materialized into the authorized modeling pipeline")
    add("frozen_stage125_m2_data_collected_is_never_rendered_as_live_state",
        ("- m2_data_collected: " not in current_state_text)
        and ((not m2_eval_done)
             or ("stage125_part4_m2_data_collected_historical"
                 in current_state_text)),
        "the frozen Stage125 Part 4 `m2_data_collected` marker must not "
        "appear among the live workflow markers; it is republished only "
        "under the historical/legacy heading")
    add("frozen_stage125_m2_data_collected_value_is_not_mutated",
        handoff.get("m2_data_collected") is False
        and ((not m2_eval_done)
             or handoff.get("stage125_part4_m2_data_collected_historical")
             is False),
        "the frozen Part 4 marker keeps its frozen value; only its "
        "presentation changes")
    add("current_state_final_test_wording_is_literally_precise",
        (not m2_eval_done)
        or ("No final-test row was read" not in current_state_text
            and "not a read" not in current_state_text
            and "identify and exclude 346 locked-final-test records"
            in current_state_text
            and "did not parse, inspect, store, preprocess, fit on, predict "
            "from, evaluate, summarize or export any final-test predictor or "
            "target value" in current_state_text),
        "the final-test claim must state that only identity/split fields "
        "were read to exclude 346 records, and must not claim that no row "
        "was read or that the exclusion was 'not a read'")
    add("final_test_remains_locked_after_the_m2_evaluation",
        (not m2_eval_done)
        or all(handoff.get(k) is False for k in (
            "final_test_unlocked", "final_test_access_authorized",
            "final_test_predictor_values_inspected",
            "final_test_target_values_inspected",
            "final_test_evaluation_performed")),
        "the final test remains locked after the paired evaluation")
    add("m2_evaluation_records_a_required_human_retained_block_decision",
        (not m2_eval_done) or retained_block_done
        or handoff.get("m2_retained_block_decision_required") is True,
        "the retained-block question must stay explicitly open for a human")
    # --- Stage128 human retained-block decision --------------------------- #
    # Retention is a GOVERNANCE decision. It may never be rendered, recorded
    # or implied as superiority, a winner, a final model, a refit, a
    # final-test unlock or a successor-block start.
    add("retained_block_decision_requires_a_completed_m2_evaluation",
        (not retained_block_done) or m2_eval_done,
        "a retained-block decision may only follow the completed paired M2 "
        "evaluation whose evidence it cites")
    add("retained_block_decision_is_recorded_as_retained_and_closed",
        (not retained_block_done)
        or (handoff.get("m2_block_retained") is True
            and handoff.get("m2_retained_block_decision_required") is False
            and handoff.get(
                "m2_retained_block_human_decision_completed") is True),
        "the recorded decision must report M2 as retained and the "
        "retained-block question as closed")
    add("retained_block_authorization_is_consumed_not_standing",
        (not retained_block_done)
        or handoff.get(
            "m2_retained_block_human_decision_authorization_consumed") is True,
        "the one-action retained-block authorization is consumed by the "
        "recording and must never be left standing")
    add("retained_block_decision_claims_no_superiority",
        (not retained_block_done)
        or (handoff.get("m2_predictive_superiority_claim_supported") is False
            and handoff.get("m2_superiority_established") is False),
        "retaining M2 as the intermediate confirmatory block is a governance "
        "decision and supports no predictive-superiority claim")
    add("retained_block_decision_selects_no_winner_and_no_final_model",
        (not retained_block_done)
        or all(handoff.get(k) is False for k in (
            "paper_winner_selected", "m2_winner_selected",
            "final_model_selected", "full_development_refit_performed")),
        "retention selects no winner, no final model and authorizes no "
        "full-development refit")
    add("retained_block_decision_leaves_final_test_locked",
        (not retained_block_done)
        or all(handoff.get(k) is False for k in FINAL_TEST_LOCK_FIELDS),
        "the final test remains locked and uninspected after the decision")
    add("retained_block_decision_starts_and_authorizes_no_successor",
        (not retained_block_done)
        or all(handoff.get(k) is False for k in (
            "m3_authorized", "m3_started", "m3_data_collected",
            "m4_authorized", "m4_started")),
        "the retained-block decision authorizes and starts neither M3 nor M4")
    add("retained_block_decision_keeps_holm_family_incomplete",
        (not retained_block_done)
        or (handoff.get("holm_family_complete") is False
            and handoff.get("holm_final_adjustment_deferred") is True),
        "the incomplete confirmatory family stays incomplete and its final "
        "adjustment stays deferred")
    # Only meaningful when the derived pointer chain has actually reached the
    # decision; a deliberately rewound (synthetic/historical) scenario keeps an
    # earlier expected pointer and must not be judged against this one.
    _retained_block_is_the_live_pointer_state = (
        retained_block_done
        and expected_next_research_action_id(
            repo_root, expected_m1_robustness_completed)
        == NEXT_RESEARCH_ACTION_ID_AFTER_M2_RETAINED_BLOCK_DECISION
    )
    add("retained_block_next_pointer_is_the_m3_gate_and_is_not_authorization",
        (not _retained_block_is_the_live_pointer_state)
        or (handoff.get("next_research_action_id")
            == NEXT_RESEARCH_ACTION_ID_AFTER_M2_RETAINED_BLOCK_DECISION
            and handoff.get("last_completed_research_action_id")
            == STAGE128_M2_RETAINED_BLOCK_DECISION_ACTION_ID
            and handoff.get("next_research_action_pointer_is_not_authorization")
            is True),
        "after the decision the pointer is the M3 macro data Gate, and a "
        "pointer is never an authorization")
    add("current_state_renders_the_retained_block_decision_section",
        (not retained_block_done)
        or ("## Stage128 — M2 retained-block HUMAN decision"
            in current_state_text),
        "CURRENT_STATE.md must render an explicit retained-block decision "
        "section once the decision is recorded")
    add("current_state_freeze_section_claims_only_its_own_action",
        (not freeze_done)
        or (f"- **Research action completed by this freeze:** "
            f"`{_STAGE128_M2_D2_FREEZE_ACTION_ID}`" in current_state_text),
        "the design-freeze section must always name "
        f"`{_STAGE128_M2_D2_FREEZE_ACTION_ID}` as the action it completed, "
        "and must never inherit the global last_completed_research_action_id")
    add("current_state_freeze_section_does_not_claim_the_gate_rerun",
        "- **Research action completed by this freeze:** "
        f"`{STAGE128_M2_D2_GATE_RERUN_ACTION_ID}`" not in current_state_text,
        "the design freeze did not complete the Gate re-run")
    add("current_state_does_not_call_incremental_evaluation_the_gate_rerun",
        not _describes_incremental_evaluation_as_gate_rerun(
            current_state_text),
        f"`{NEXT_RESEARCH_ACTION_ID_AFTER_STAGE128_M2_D2_GATE_RERUN_PASS}` is "
        "the M2 incremental evaluation action, never the canonical M2 Gate "
        "re-run")
    next_pointer_lines = [
        ln for ln in current_state_text.splitlines()
        if ln.startswith("- **Next research action (pointer only):**")
    ]
    add("current_state_renders_a_single_live_next_action_pointer",
        (not rerun_complete) or len(next_pointer_lines) == 1,
        "after the Gate re-run only the CURRENT Gate-re-run section may "
        f"carry a live next-action pointer; found {len(next_pointer_lines)}")
    # Internal consistency of the rendered snapshot: the section-level live
    # pointer must name the SAME action as the snapshot header and must say,
    # in the same line, that a pointer is not an authorization.
    header_pointers = [
        ln for ln in current_state_text.splitlines()
        if ln.startswith("- **Next research action:** `")
    ]
    header_id = (
        header_pointers[0].split("`")[1] if header_pointers else ""
    )
    add("current_state_next_pointer_is_a_pointer_not_an_authorization",
        (not rerun_complete)
        or (len(next_pointer_lines) == 1
            and header_id
            and f"`{header_id}`" in next_pointer_lines[0]
            and ("not an authorization"
                 in next_pointer_lines[0].replace("**", "")
                 or "not authorized"
                 in next_pointer_lines[0].replace("**", ""))),
        "the live next-action pointer must name the same action as the "
        "snapshot header and state that a pointer is not an authorization")
    add("next_pointer_flags_are_false_when_pointer_is_incremental_evaluation",
        (handoff.get("next_research_action_id")
         != NEXT_RESEARCH_ACTION_ID_AFTER_STAGE128_M2_D2_GATE_RERUN_PASS)
        or (handoff.get("m2_incremental_evaluation_authorized") is False
            and handoff.get("m2_modeling_started") is False),
        "pointing at the M2 incremental evaluation never authorizes or "
        "starts it")
    add("gate_rerun_complete_implies_current_action_is_the_gate_rerun_"
        "or_a_recognized_successor",
        (not rerun_complete)
        or (handoff.get("last_completed_research_action_id")
            == STAGE128_M2_D2_GATE_RERUN_ACTION_ID)
        or (m2_eval_done
            and handoff.get("last_completed_research_action_id")
            == STAGE127_M2_INCREMENTAL_EVALUATION_ACTION_ID)
        or (retained_block_done
            and handoff.get("last_completed_research_action_id")
            == STAGE128_M2_RETAINED_BLOCK_DECISION_ACTION_ID)
        or (stage128_m3i2_inquiry_human_submission_recorded(repo_root)
            and handoff.get("last_completed_research_action_id")
            == STAGE128_M3I2_INQUIRY_SUBMISSION_ACTION_ID)
        or (stage128_m3i2_final_documentary_recovery_initiated(repo_root)
            and handoff.get("last_completed_research_action_id")
            == STAGE128_M3I2_RECOVERY_ACTION_ID)
        or (stage128_m3i2_evidence_capture_completed(repo_root)
            and handoff.get("last_completed_research_action_id")
            == STAGE128_M3I2_EVIDENCE_ACTION_ID)
        or (stage128_m3i2_contract_lock_completed(repo_root)
            and handoff.get("last_completed_research_action_id")
            == STAGE128_M3I2_ACTION_ID),
        "after the Gate re-run, the last completed research action must be "
        "the Gate re-run itself or a recognized, completed successor action")
    # --- Track B: the M3-LAG-WDI exploratory contract lock ---------------- #
    # `stage128_m3_lag_wdi_exploratory_contract_locked(...)` above raises on
    # ANY drift in the frozen contract, so reaching this point already proves
    # the contract still satisfies every locked requirement. What is asserted
    # here is the *agreement* between that contract and the published Handoff:
    # a locked status may never appear in the snapshot while the contract that
    # justifies it is absent, and the parallel Track B lock may never be
    # rendered as having moved Track A.
    m3_lag_locked = stage128_m3_lag_wdi_exploratory_contract_locked(repo_root)
    add("m3_lag_wdi_locked_status_requires_the_authoritative_contract",
        (handoff.get("stage128_m3_lag_wdi_authoritative_contract_status")
         != STAGE128_M3_LAG_LOCKED_STATUS) or m3_lag_locked,
        "the Handoff may publish "
        f"{STAGE128_M3_LAG_LOCKED_STATUS} only when the authoritative "
        "M3-LAG-WDI contract satisfies every frozen requirement")
    add("m3_lag_wdi_contract_lock_is_published_when_it_exists",
        (not m3_lag_locked)
        or (handoff.get("stage128_m3_lag_wdi_authoritative_contract_status")
            == STAGE128_M3_LAG_LOCKED_STATUS
            and handoff.get("stage128_m3_lag_wdi_exploratory_contract_locked")
            is True),
        "a locked M3-LAG-WDI contract must be published as locked, not as "
        "NOT_LOCKED")
    # Retrieval (step B) is a SEPARATE, later, separately authorized action, so
    # `data_retrieval_started` is owned by the retrieval recognizer below and is
    # deliberately NOT asserted here. What the lock itself must never have done
    # — Gate, modeling, Final Test — is still asserted unconditionally, and the
    # retrieval-only firewall is asserted separately.
    m3_lag_retrieved = stage128_m3_lag_wdi_data_retrieval_executed(repo_root)
    # The Gate is step D's own separately authorized action, so "no Gate has
    # run" belongs to the Gate recognizer below, not to the contract lock.
    # Pinning it here would encode the pre-Gate MOMENT and would fail the
    # instant a legitimate step D ran. The rule that holds at EVERY step is
    # the one asserted instead: a published Gate execution must be justified
    # by the Gate action's own package, and no step ever fits a model or
    # reads a Final Test row.
    m3_lag_gated = stage128_m3_lag_wdi_data_gate_executed(repo_root)
    add("m3_lag_wdi_lock_executes_no_gate_no_model_no_final_test",
        (not m3_lag_locked)
        or ((handoff.get("stage128_m3_lag_wdi_data_gate_executed") is False
             or m3_lag_gated)
            and handoff.get("stage128_m3_lag_wdi_modeling_started") is False
            and handoff.get("stage128_m3_lag_wdi_final_test_rows_read") == 0),
        "the contract lock executes no Gate — only the separately authorized "
        "Gate action may — and no step fits a model or reads a Final Test row")
    add("m3_lag_wdi_gate_executed_only_with_its_own_action",
        (handoff.get("stage128_m3_lag_wdi_data_gate_executed") is not True)
        or m3_lag_gated,
        "the Handoff may publish the Data Gate as executed only when the "
        "data-gate-only action package justifies it")
    add("m3_lag_wdi_retrieval_started_only_with_its_own_action",
        (handoff.get("stage128_m3_lag_wdi_data_retrieval_started") is not True)
        or m3_lag_retrieved,
        "the Handoff may publish retrieval as started only when the "
        "retrieval-only action package justifies it")
    add("m3_lag_wdi_retrieval_is_published_when_it_exists",
        (not m3_lag_retrieved)
        or (handoff.get("stage128_m3_lag_wdi_data_retrieval_started") is True
            and handoff.get("stage128_m3_lag_wdi_retrieval_scope")
            == STAGE128_M3_LAG_RETRIEVAL_SCOPE),
        "an executed retrieval must be published as executed, and as "
        "retrieval_only")
    # Admission belongs to step D alone. Before the Gate runs, nothing may be
    # admitted; after it runs, admission is permitted only when the Gate's own
    # package justifies it AND its verdict is a PASS. Either way, no step
    # fits a model or reads a Final Test row.
    add("m3_lag_wdi_retrieval_executed_nothing_downstream",
        (not m3_lag_retrieved)
        or (((handoff.get("stage128_m3_lag_wdi_data_gate_executed") is False
              and handoff.get("stage128_m3_lag_wdi_data_gate_authorized")
              is False
              and handoff.get("stage128_m3_lag_wdi_block_admitted") is False)
             if not m3_lag_gated else
             (handoff.get("stage128_m3_lag_wdi_data_gate_was_authorized")
              is True
              and handoff.get("stage128_m3_lag_wdi_block_admitted")
              is (handoff.get("stage128_m3_lag_wdi_data_gate_result")
                  == STAGE128_M3_LAG_GATE_PASS)))
            and handoff.get("stage128_m3_lag_wdi_modeling_started") is False
            and handoff.get("stage128_m3_lag_wdi_modeling_authorized") is False
            and handoff.get("stage128_m3_lag_wdi_final_test_rows_read") == 0),
        "acquisition is not admission: only the separately authorized Data "
        "Gate may admit the block, and no step fits a model or reads a Final "
        "Test row")
    # The byte boundary belongs to step B alone. Step C is the separately
    # authorized action that MAY decode, so pinning "decoded nothing" to the
    # retrieval marker would encode the pre-audit moment and would fail the
    # instant a legitimate step C ran. What must hold at EVERY step is the
    # rule: nothing may decode before the audit is authorized, and no step may
    # substitute an alternative indicator.
    m3_lag_audited = handoff.get(
        "stage128_m3_lag_wdi_post_retrieval_audit_executed") is True
    add("m3_lag_wdi_values_are_read_only_by_an_authorized_audit",
        (not m3_lag_retrieved)
        or (handoff.get(
            "stage128_m3_lag_wdi_alternative_indicators_retrieved") == 0
            and ((handoff.get("stage128_m3_lag_wdi_payload_json_decoded")
                  is False
                  and handoff.get(
                      "stage128_m3_lag_wdi_wdi_observations_read") == 0)
                 if not m3_lag_audited else
                 (handoff.get(
                     "stage128_m3_lag_wdi_post_retrieval_audit_was_authorized")
                  is True
                  and handoff.get(
                      "stage128_m3_lag_wdi_wdi_observations_read") > 0))),
        "values are read only by an authorized post-retrieval audit, and no "
        "step ever retrieves an alternative indicator")
    add("m3_lag_wdi_pointer_advances_but_never_authorizes",
        (not m3_lag_retrieved)
        or (handoff.get("stage128_m3_lag_wdi_next_action_id")
            == (STAGE128_M3_LAG_MODELING_ACTION_ID if m3_lag_gated
                else STAGE128_M3_LAG_DATA_GATE_ACTION_ID if m3_lag_audited
                else STAGE128_M3_LAG_POST_RETRIEVAL_AUDIT_ACTION_ID)
            and handoff.get("stage128_m3_lag_wdi_next_action_authorized")
            is False),
        "the Track B pointer advances one separated step at a time — to the "
        "audit after retrieval, to the Data Gate after the audit, to modeling "
        "after the Gate — and a pointer is never an authorization")
    # Step C, once executed, is history: authorized ONCE, consumed, never
    # standing, and never readable as permission for the Data Gate.
    add("m3_lag_wdi_completed_audit_is_consumed_and_not_a_gate_authorization",
        (not m3_lag_audited)
        or (handoff.get(
            "stage128_m3_lag_wdi_post_retrieval_audit_was_authorized") is True
            and handoff.get(
                "stage128_m3_lag_wdi_post_retrieval_audit_authorized_now")
            is False
            and handoff.get(
                "stage128_m3_lag_wdi_post_retrieval_audit_authorization_"
                "consumed") is True
            and handoff.get(
                "stage128_m3_lag_wdi_post_retrieval_audit_authorization_"
                "reusable") is False
            and (handoff.get("stage128_m3_lag_wdi_data_gate_executed") is False
                 or m3_lag_gated)),
        "a completed post-retrieval audit is consumed, non-reusable and never "
        "an authorization for the Data Gate — a later Gate execution must "
        "rest on the Gate's OWN authorization and package, not on this one")
    # A finding that disappears is worse than no audit at all.
    add("m3_lag_wdi_audit_findings_are_not_laundered_away",
        (not m3_lag_audited)
        or (handoff.get("stage128_m3_lag_wdi_post_retrieval_audit_result")
            in ("PASS", "PASS_WITH_MATERIAL_FINDINGS", "FAIL")
            and (handoff.get("stage128_m3_lag_wdi_post_retrieval_audit_result")
                 != "PASS"
                 or handoff.get(
                     "stage128_m3_lag_wdi_post_retrieval_audit_material_"
                     "limitation_count") == 0)),
        "recorded material findings may never be published as a bare PASS")
    # Step D, once executed, is history too: authorized ONCE, consumed, never
    # standing, and — the part that matters most — a PASS that admits DATA and
    # nothing else.
    add("m3_lag_wdi_completed_gate_is_consumed_and_not_modeling_authorization",
        (not m3_lag_gated)
        or (handoff.get("stage128_m3_lag_wdi_data_gate_was_authorized") is True
            and handoff.get("stage128_m3_lag_wdi_data_gate_authorized_now")
            is False
            and handoff.get(
                "stage128_m3_lag_wdi_data_gate_authorization_consumed") is True
            and handoff.get(
                "stage128_m3_lag_wdi_data_gate_authorization_reusable")
            is False
            and handoff.get(
                "stage128_m3_lag_wdi_gate_pass_authorizes_modeling") is False
            and handoff.get("stage128_m3_lag_wdi_modeling_authorized") is False
            and handoff.get("stage128_m3_lag_wdi_modeling_started") is False),
        "a completed Data Gate is consumed, non-reusable and never an "
        "authorization to fit a model")
    # A coverage PASS is not a scientific endorsement, and the limitation that
    # a coverage count cannot see is exactly the one most likely to be lost.
    add("m3_lag_wdi_gate_pass_is_not_an_information_content_claim",
        (not m3_lag_gated)
        or (handoff.get(
            "stage128_m3_lag_wdi_gate_pass_is_information_content_claim")
            is False
            and handoff.get(
                "stage128_m3_lag_wdi_step_c_material_findings_preserved")
            is True
            and handoff.get(
                "stage128_m3_lag_wdi_post_retrieval_audit_result")
            == "PASS_WITH_MATERIAL_FINDINGS"
            and (handoff.get(
                "stage128_m3_lag_wdi_gate_material_limitation_count") or 0)
            > 0),
        "a coverage PASS never becomes an information-content claim, and the "
        "step C findings survive it")
    add("m3_lag_wdi_gate_thresholds_and_admission_were_not_engineered",
        (not m3_lag_gated)
        or (handoff.get(
            "stage128_m3_lag_wdi_gate_thresholds_changed_by_this_action")
            is False
            and handoff.get("stage128_m3_lag_wdi_gate_criteria_weakened")
            is False
            and handoff.get("stage128_m3_lag_wdi_gate_rows_excluded") == 0
            and handoff.get(
                "stage128_m3_lag_wdi_gate_candidate_coverage_min")
            == STAGE128_M3_LAG_GATE_CANDIDATE_MIN
            and handoff.get("stage128_m3_lag_wdi_gate_block_coverage_min")
            == STAGE128_M3_LAG_GATE_BLOCK_MIN
            and handoff.get(
                "stage128_m3_lag_wdi_gate_min_positive_each_validation_window")
            == STAGE128_M3_LAG_GATE_MIN_POSITIVE),
        "the Gate ran on the locked inherited thresholds, weakened no "
        "criterion and excluded no row to reach its verdict")
    add("m3_lag_wdi_lock_is_exploratory_not_confirmatory",
        (not m3_lag_locked)
        or (handoff.get("stage128_m3_lag_wdi_scientific_role")
            == STAGE128_M3_LAG_ROLE
            and handoff.get("stage128_m3_lag_wdi_is_confirmatory_m3") is False
            and handoff.get("stage128_m3_lag_wdi_in_confirmatory_holm_family")
            is False),
        "M3-LAG-WDI stays a supplementary exploratory robustness block outside "
        "the confirmatory Holm family")
    add("m3_lag_wdi_lock_claims_no_point_in_time_availability",
        (not m3_lag_locked)
        or handoff.get(
            "stage128_m3_lag_wdi_point_in_time_availability_claimed") is False,
        "the one-year lag never becomes a point-in-time availability claim")
    add("m3_lag_wdi_lock_is_not_an_authorization",
        (not m3_lag_locked)
        or (handoff.get("stage128_m3_lag_wdi_next_action_authorized") is False
            and handoff.get("stage128_m3_lag_wdi_modeling_authorized")
            is False),
        "a locked contract authorizes neither retrieval, nor the Data Gate, "
        "nor modeling")
    add("m3_lag_wdi_lock_does_not_terminate_the_world_bank_inquiry",
        (not m3_lag_locked)
        or (handoff.get("stage128_m3i2_inquiry_waiting_period_status")
            == "ACTIVE"
            and handoff.get("stage128_m3i2_inquiry_substantive_response_"
                            "received") is False
            and handoff.get("stage128_m3i2_response_adjudication_authorized")
            is False
            and handoff.get("stage128_m3i2_inquiry_follow_up_authorized_now")
            is False),
        "activating Track B in parallel never terminates, resolves or "
        "authorizes anything on the still-active World Bank inquiry")
    add("m3_lag_wdi_lock_preserves_m3_cbi_and_m3i2",
        (not m3_lag_locked)
        or (handoff.get("stage128_m3i2_evidence_status")
            == "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE"
            and handoff.get("m3i2_block_admitted") is False
            and handoff.get("m3i2_data_gate_executed") is False
            and handoff.get("final_test_locked") is True
            and handoff.get("m4_authorized") is False),
        "the Track B lock changes no M3-CBI or M3I-2 conclusion, unlocks no "
        "Final Test and authorizes no M4")
    # Retrieval and the Data Gate are two actions, not one. If the published
    # pointer named a single action that both retrieves and Gates, the human
    # authorization for retrieval would silently become an authorization to
    # admit data. The Handoff must publish them separated and unauthorized.
    # The pointer ADVANCES as Track B steps complete (retrieval -> audit ->
    # ...), so pinning it to one action id would encode a moment rather than
    # the rule. The invariant that must hold at EVERY step is asserted instead:
    # whatever the pointer names, it is a step of the separated sequence, it
    # never executes the Data Gate, and it is never itself an authorization.
    _m3_lag_pointer = handoff.get("stage128_m3_lag_wdi_next_action_id")
    add("m3_lag_wdi_next_action_is_a_separated_unauthorized_step",
        (not m3_lag_locked)
        or (_m3_lag_pointer in (STAGE128_M3_LAG_RETRIEVAL_ACTION_ID,
                                STAGE128_M3_LAG_POST_RETRIEVAL_AUDIT_ACTION_ID,
                                STAGE128_M3_LAG_DATA_GATE_ACTION_ID,
                                STAGE128_M3_LAG_MODELING_ACTION_ID)
            # Once the audit has run, the pointer legitimately NAMES the Data
            # Gate, and `next_action_executes_data_gate` is a DESCRIPTIVE
            # property of the named action — so it becomes True exactly when
            # the pointer reaches step D. Asserting it is forever False would
            # both encode the pre-audit moment and contradict the locked
            # sequence. What actually protects the boundary is that the
            # pointer is never AUTHORIZED and the Gate is never EXECUTED.
            and (handoff.get(
                "stage128_m3_lag_wdi_next_action_executes_data_gate")
                is (_m3_lag_pointer == STAGE128_M3_LAG_DATA_GATE_ACTION_ID))
            and handoff.get("stage128_m3_lag_wdi_next_action_authorized")
            is False
            and (_m3_lag_pointer != STAGE128_M3_LAG_DATA_GATE_ACTION_ID
                 or (handoff.get("stage128_m3_lag_wdi_data_gate_authorized")
                     is False
                     and handoff.get("stage128_m3_lag_wdi_data_gate_executed")
                     is False))),
        "the immediate Track B pointer is a single separated step whose "
        "executes-the-Gate flag matches the locked sequence for the action it "
        "names, and it is never authorized and never executed")
    add("m3_lag_wdi_pointer_is_retrieval_only_until_retrieval_runs",
        (not m3_lag_locked)
        or handoff.get("stage128_m3_lag_wdi_data_retrieval_started") is True
        or (_m3_lag_pointer == STAGE128_M3_LAG_RETRIEVAL_ACTION_ID
            and handoff.get("stage128_m3_lag_wdi_next_action_scope")
            == STAGE128_M3_LAG_NEXT_ACTION_SCOPE),
        "before retrieval has run, the immediate Track B pointer is the "
        "retrieval action with scope retrieval_only")
    # The Gate is permanently a separate action, and the generic
    # ``*_authorized`` field carries the STANDING meaning at every point in
    # the sequence — so it is False before step D runs AND after its one-time
    # authorization is consumed. The historical fact lives in
    # ``*_was_authorized``, which is why this can be asserted unconditionally.
    add("m3_lag_wdi_data_gate_is_a_separate_never_standing_authorized_action",
        (not m3_lag_locked)
        or (handoff.get("stage128_m3_lag_wdi_data_gate_action_id")
            == STAGE128_M3_LAG_DATA_GATE_ACTION_ID
            and handoff.get("stage128_m3_lag_wdi_data_gate_action_id")
            != handoff.get("stage128_m3_lag_wdi_retrieval_action_id")
            and handoff.get(
                "stage128_m3_lag_wdi_data_gate_requires_new_human_"
                "authorization") is True
            and handoff.get("stage128_m3_lag_wdi_data_gate_authorized")
            is False
            and handoff.get("stage128_m3_lag_wdi_data_gate_authorized_now")
            is not True),
        "the M3-LAG-WDI Data Gate is a SEPARATE action with its own identity "
        "that always requires a new explicit human authorization, and no "
        "STANDING Gate authorization ever exists — before or after it runs")
    # The general invariant, applied to every one-time Track B authorization:
    # a CONSUMED grant is history and may never appear in a standing field.
    # Asserted here, independently of the generator, so the two would have to
    # drift in the same direction to hide it.
    _one_time_prefixes = (
        "stage128_m3_lag_wdi_retrieval",
        "stage128_m3_lag_wdi_post_retrieval_audit",
        "stage128_m3_lag_wdi_data_gate",
    )
    _standing_leaks = sorted(
        f"{prefix}_{suffix}"
        for prefix in _one_time_prefixes
        if handoff.get(f"{prefix}_authorization_consumed") is True
        for suffix in ("authorized", "authorized_now",
                       "authorization_reusable")
        if handoff.get(f"{prefix}_{suffix}") is True)
    _missing_history = sorted(
        f"{prefix}_was_authorized"
        for prefix in _one_time_prefixes
        if handoff.get(f"{prefix}_authorization_consumed") is True
        and handoff.get(f"{prefix}_was_authorized") is not True)
    add("m3_lag_wdi_no_consumed_authorization_is_published_as_standing",
        not _standing_leaks and not _missing_history,
        "a consumed one-time authorization is history: it may never be "
        "published as a standing permission, and the historical fact must be "
        f"recorded in *_was_authorized (standing leaks: {_standing_leaks}; "
        f"missing history: {_missing_history})")
    add("m3_lag_wdi_retrieval_authorization_never_authorizes_the_gate",
        (not m3_lag_locked)
        or (handoff.get(
            "stage128_m3_lag_wdi_retrieval_authorization_implies_gate_"
            "authorization") is False
            and handoff.get(
                "stage128_m3_lag_wdi_combined_retrieval_and_gate_action_"
                "permitted") is False
            and handoff.get("stage128_m3_lag_wdi_retrieval_executes_data_gate")
            is False),
        "an authorization to retrieve is never an authorization to execute "
        "the Data Gate, and the two may not be combined into one action")
    add("m3_lag_wdi_gate_pass_admits_data_and_authorizes_no_modeling",
        (not m3_lag_locked)
        or (handoff.get("stage128_m3_lag_wdi_gate_pass_is_data_admission_only")
            is True
            and handoff.get("stage128_m3_lag_wdi_gate_pass_authorizes_"
                            "modeling") is False
            and handoff.get("stage128_m3_lag_wdi_modeling_requires_new_human_"
                            "authorization") is True),
        "a Data Gate PASS is DATA ADMISSION ONLY and authorizes no modeling")
    # History: PR #76 initiated the documentary recovery and PR #77 recorded
    # the human submission. Re-anchoring the live topology onto PR #78 must
    # never collapse those two roles into one, nor slide either forward.
    add("m3i2_documentary_recovery_pr_stays_pr76",
        (not m3_lag_locked)
        or (handoff.get("stage128_m3i2_recovery_pr_number")
            == STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR
            and handoff.get("stage128_m3i2_recovery_pr_merge_commit")
            == STAGE128_M3I2_DOCUMENTARY_RECOVERY_MERGE_COMMIT
            and handoff.get("stage128_m3i2_recovery_pr_role")
            == STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR_ROLE),
        "the documentary-recovery INITIATION is PR "
        f"#{STAGE128_M3I2_DOCUMENTARY_RECOVERY_PR}, merged by "
        f"{STAGE128_M3I2_DOCUMENTARY_RECOVERY_MERGE_COMMIT}, whatever is live "
        "now")
    add("m3i2_human_submission_pr_stays_separately_represented",
        (not m3_lag_locked)
        or (handoff.get("stage128_m3i2_human_submission_pr_number")
            == STAGE128_M3I2_HUMAN_SUBMISSION_PR
            and handoff.get("stage128_m3i2_human_submission_pr_merge_commit")
            == STAGE128_M3I2_HUMAN_SUBMISSION_MERGE_COMMIT
            and handoff.get("stage128_m3i2_human_submission_pr_role")
            == STAGE128_M3I2_HUMAN_SUBMISSION_PR_ROLE),
        "the human inquiry submission RECORDING keeps its own separate "
        f"identity as PR #{STAGE128_M3I2_HUMAN_SUBMISSION_PR}")
    add("m3i2_three_pr_roles_are_never_collapsed_or_shifted",
        (not m3_lag_locked)
        or (handoff.get("stage128_m3i2_recovery_pr_number")
            < handoff.get("stage128_m3i2_human_submission_pr_number", 0)
            < handoff.get("stage128_m3i2_live_pr_number", 0)
            and handoff.get("stage128_m3i2_recovery_pr_merge_commit")
            != handoff.get("stage128_m3i2_human_submission_pr_merge_commit")
            and handoff.get("stage128_m3i2_live_pr_is_draft") is True
            and handoff.get("stage128_m3i2_live_pr_merged") is False),
        "the documentary recovery, the human submission and the live Draft "
        "stay three distinct PRs with three distinct roles")

    # --- ROADMAP front matter must agree with its own explanatory prose --- #
    roadmap_text = ""
    rm_path = repo_root / ROADMAP_MD_REL
    if rm_path.is_file():
        roadmap_text = rm_path.read_text(encoding="utf-8")
    fm = _roadmap_front_matter(roadmap_text)
    body = roadmap_text.split("---", 2)[-1] if fm else roadmap_text
    stale_pair = (
        "the authoritative pointers remain "
        f"`last_completed_research_action_id: "
        f"{_STAGE128_M2_D2_FREEZE_ACTION_ID}`"
    )
    # ROADMAP-INTERNAL consistency: the explanatory prose must name the same
    # authoritative pointer pair as the machine-readable front matter.
    fm_last = fm.get("last_completed_research_action_id", "")
    fm_next = fm.get("next_research_action_id", "")
    authoritative_prose = [
        ln for ln in body.splitlines()
        if "authoritative pointers" in ln
    ]
    add("roadmap_prose_agrees_with_front_matter_pointers",
        (not fm)
        or all(f"`last_completed_research_action_id: {fm_last}`" in ln
               and f"`next_research_action_id: {fm_next}`" in ln
               for ln in authoritative_prose),
        "ROADMAP prose naming the authoritative pointers must name exactly "
        f"the front-matter pair ({fm_last} / {fm_next})")
    add("roadmap_prose_does_not_contradict_front_matter_pointers",
        stale_pair not in body,
        "ROADMAP prose must not claim a superseded pointer pair still "
        "'remains' authoritative")
    add("roadmap_prose_does_not_call_incremental_evaluation_the_gate_rerun",
        not _describes_incremental_evaluation_as_gate_rerun(body),
        f"`{NEXT_RESEARCH_ACTION_ID_AFTER_STAGE128_M2_D2_GATE_RERUN_PASS}` is "
        "the M2 incremental evaluation action, never the canonical Gate "
        "re-run")
    return a


# --------------------------------------------------------------------------- #
# README
# --------------------------------------------------------------------------- #

def build_readme(report: dict[str, Any]) -> str:
    lines = [
        "# Stage126 — Current-State Validation",
        "",
        "**Stage125 Part 5 is a frozen historical closure. It is no longer "
        "responsible for validating live Stage126 successor state. The "
        "independent Stage126 current-state validator is the sole current-state "
        "validation surface.**",
        "",
        "Future robustness parts must **not** regenerate previous-part "
        "verification artifacts unless a genuine scientific error and a "
        "separate explicit human authorization exist.",
        "",
        "## Decision",
        "",
        f"- Decision: `{DECISION_ID}` (`{DECISION_VERSION}`)",
        f"- Human decision text SHA-256: `{HUMAN_DECISION_TEXT_SHA256}`",
        "- Authorizes: the boundary lock, this validator, the Stage125 Part 5 "
        "freeze, and the documentation/test changes this boundary requires.",
        "- Does **not** authorize: merge, Part 3 execution, full-development "
        "refit, final-test access, final-test evaluation, or any new scientific "
        "execution.",
        "",
        "## Live verification sequence",
        "",
        "```bash",
        "python project/run_stage126_current_state_validator.py --check",
        "python project/run_stage126_m1_robustness_part2_listing_rule_b.py --check",
        "python project/scripts/validate_ai_handoff.py --check",
        "PYTHONPATH=project python -m pytest project/tests -q",
        "```",
        "",
        "`run_stage125_part5.py --check` is **not** part of this sequence. It is "
        "a historical closure runner; its known behaviour (exit 1, first failure "
        "`readiness_surface_disagreement`, and a separate five-field direct "
        "handoff mismatch) is retained as **historical provenance only** and is "
        "no longer a required live gate. Previous robustness runners are also "
        "not current-state gates — previous scientific artifacts are protected "
        "by immutable hashes recorded here.",
        "",
        "## Frozen historical surfaces",
        "",
        f"- `{PART5_SOURCE_REL}` — `{PART5_SOURCE_SHA256}`",
        f"- `{PART5_RUNNER_REL}` — `{PART5_RUNNER_SHA256}`",
        f"- `{PART5_TEST_REL}` — `{PART5_TEST_SHA256}`",
        f"- `project/stage125/**` — every tracked file pinned in "
        f"`{F_BOUNDARY_MANIFEST}`",
        "",
        "## Current state",
        "",
        "| field | value |",
        "|---|---|",
        f"| completed parts | {report['completed_part_count']} |",
        f"| completed categories | {', '.join(f'`{c}`' for c in report['completed_category_ids'])} |",
        f"| next category | `{report['next_category_id']}` |",
        f"| next category authorized | {str(report['next_category_authorized']).lower()} |",
        f"| M1 robustness completed | {str(report['m1_robustness_completed']).lower()} |",
        f"| full-development refit performed | {str(report['full_development_refit_performed']).lower()} |",
        f"| final test unlocked | {str(report['final_test_unlocked']).lower()} |",
        f"| last completed micro-part | `{report['last_completed_micro_part']}` |",
        f"| active workstream | `{report['active_workstream']}` |",
        f"| next research action | `{report['next_research_action_id']}` |",
        "",
        "## Adding a future part",
        "",
        "Parts are discovered generically from the Part 0 registered execution "
        "order by naming convention. A future Part 3 advances current state by "
        "adding only its own implementation, tests, artifacts and completion "
        "lock, plus a refreshed validation report, Handoff and human "
        "documentation. **No Part 1, Part 2 or Stage125 Part 5 file may "
        "change.**",
        "",
        "## Exception policy",
        "",
        f"- Reopening a completed part: **{PRIOR_PART_REOPENING_DEFAULT}** by "
        "default.",
        "- A genuine scientific error exception requires all of: "
        + ", ".join(f"`{r}`" for r in SCIENTIFIC_ERROR_EXCEPTION_REQUIRES) + ".",
        "- **Not** scientific errors: "
        + ", ".join(NOT_A_SCIENTIFIC_ERROR) + ".",
        "- **May** qualify: " + ", ".join(MAY_QUALIFY_AS_SCIENTIFIC_ERROR) + ".",
        "- This validator never reopens a previous part automatically.",
    ]
    return "\n".join(lines).rstrip("\n") + "\n"


# --------------------------------------------------------------------------- #
# Build-all + run
# --------------------------------------------------------------------------- #

def build_all(
    repo_root: Path, *, strict_pointers: bool = True,
) -> tuple[dict[str, str], dict[str, Any]]:
    verify_decision_text()
    decision = build_decision_record()
    manifest = build_boundary_manifest(repo_root)

    part0 = verify_part0_contract(repo_root)
    execution_order = list(part0["execution_order"])
    primary_observed = verify_primary_stage126_artifacts(repo_root)
    verify_selected_configurations(repo_root)
    verify_final_test_lock(repo_root)

    completed, completed_ids = completed_prefix(repo_root, execution_order)
    registry = build_closed_part_registry(repo_root, completed)
    registry_drift = verify_registry_immutability(repo_root, registry)
    last_micro_part = completed[-1]["micro_part_id"] if completed else ""
    micro_qc = micro_part_qc_pointers(repo_root, completed[-1] if completed else None)
    next_category = verify_no_unauthorized_execution(
        repo_root, execution_order, completed,
    )
    m1_robustness_completed = (
        len(completed_ids) == len(execution_order) and len(execution_order) > 0
    )
    handoff = verify_handoff(
        repo_root, completed_ids, last_micro_part=last_micro_part,
        micro_qc=micro_qc, strict_pointers=strict_pointers,
        m1_robustness_completed=m1_robustness_completed,
    )

    report = build_validation_report(
        repo_root, execution_order=execution_order, completed=completed,
        completed_ids=completed_ids, next_category=next_category,
        registry=registry, primary_observed=primary_observed,
        handoff=handoff, last_micro_part=last_micro_part, micro_qc=micro_qc,
    )
    readme = build_readme(report)
    content = {
        F_DECISION: _json_str(decision),
        F_BOUNDARY_MANIFEST: _json_str(manifest),
        F_CLOSED_REGISTRY: _json_str(registry),
        F_REPORT: _json_str(report),
        F_README: readme,
    }
    extras = {
        "decision": decision, "manifest": manifest, "report": report,
        "execution_order": execution_order, "completed": completed,
        "handoff": handoff, "registry": registry,
        "registry_drift": registry_drift, "last_micro_part": last_micro_part,
    }
    return content, extras


#: Metadata fields that embed live git HEAD purely as an engineering anchor.
#: These go stale the moment the built file is committed and carry no
#: scientific meaning.
METADATA_COMMIT_ANCHOR_FIELDS: tuple[str, ...] = ("generated_at", "code_commit")


def _metadata_drift_is_anchor_only(path: Path, expected: dict[str, Any]) -> bool:
    """True iff the on-disk metadata differs ONLY in commit-anchor fields.

    Fail-closed: an unreadable/malformed file, a missing anchor field, or any
    difference outside ``METADATA_COMMIT_ANCHOR_FIELDS`` returns False so the
    caller still raises.
    """
    try:
        on_disk = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(on_disk, dict):
        return False
    if set(on_disk) != set(expected):
        return False
    differing = [k for k in expected if on_disk.get(k) != expected[k]]
    if not differing:
        return False
    return all(k in METADATA_COMMIT_ANCHOR_FIELDS for k in differing)


def _compare_drift(out_dir: Path, payloads: dict[str, str]) -> list[str]:
    drift: list[str] = []
    for name, text in payloads.items():
        path = out_dir / name
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            drift.append(name)
    return drift


def boundary_handoff_markers() -> dict[str, Any]:
    """Fail-closed Handoff markers describing the validation architecture."""
    return dict(REQUIRED_HANDOFF_ARCHITECTURE_FIELDS)


def run(
    *, project_dir: Path, output_dir: Path | None = None,
    build: bool = False, check: bool = False,
) -> dict[str, Any]:
    if build and check:
        raise ValidationFail("build and check are mutually exclusive")
    if not build and not check:
        raise ValidationFail("one of --build or --check is required")

    repo_root = repo_root_from(project_dir)
    canonical_out = (repo_root / STAGE126_DIR_REL).resolve()
    out_dir = Path(output_dir).resolve() if output_dir else canonical_out

    # A bootstrap --build may run before the Handoff carries the new
    # current-state pointers; a pointer that is PRESENT and wrong always fails.
    content, extras = build_all(repo_root, strict_pointers=check)

    source_text = (repo_root / SRC_REL).read_text(encoding="utf-8")
    assertions = build_assertions(
        repo_root, decision=extras["decision"], manifest=extras["manifest"],
        report=extras["report"], execution_order=extras["execution_order"],
        completed=extras["completed"], handoff=extras["handoff"],
        source_text=source_text, registry_drift=extras["registry_drift"],
    )
    failed = sum(1 for x in assertions if x["status"] != "PASS")

    source_commit = _git(
        str(repo_root), "log", "--format=%H", "-n", "1",
        "--", SRC_REL, TEST_REL, RUN_REL,
    ) or _git(str(repo_root), "rev-parse", "HEAD")

    content_hashes = {
        name: sha256_bytes(text.encode("utf-8")) for name, text in content.items()
    }
    meta = {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "validator_id": VALIDATOR_ID,
        "validator_version": VALIDATOR_VERSION,
        "decision_id": DECISION_ID,
        "decision_version": DECISION_VERSION,
        "description": (
            "Stage126 independent current-state validator. Stage125 Part 5 is "
            "historical and immutable and is neither imported nor executed "
            "here; current state is validated only from Stage126-native "
            "contracts and immutable hashes."
        ),
        "generated_at": source_commit,
        "code_commit": source_commit,
        "source_file_sha256": sha256_file(repo_root / SRC_REL),
        "test_file_sha256": (
            sha256_file(repo_root / TEST_REL)
            if (repo_root / TEST_REL).is_file() else ""
        ),
        "assertion_count": len(assertions),
        "failed_count": failed,
        "all_pass": failed == 0,
        "human_decision_text_sha256": HUMAN_DECISION_TEXT_SHA256,
        "output_files_sha256": dict(sorted(content_hashes.items())),
        "stage125_part5_frozen_files_sha256":
            extras["manifest"]["stage125_part5_frozen_files_sha256"],
        "stage125_tree_aggregate_sha256":
            extras["manifest"]["stage125_tree_aggregate_sha256"],
        "stage125_part5_executed": False,
        "stage125_part5_imported": False,
        "closed_part_count": extras["registry"]["closed_part_count"],
        "last_completed_micro_part": extras["last_micro_part"],
        "current_state_validation_scope": CURRENT_STATE_QC_SCOPE,
        "current_state_validation_path": CURRENT_STATE_QC_PATH,
        "assertions": assertions,
        **boundary_handoff_markers(),
    }
    meta_text = _json_str(meta)
    all_tracked = {**content, F_METADATA: meta_text}

    tracked_drift = (
        _compare_drift(out_dir, all_tracked)
        if out_dir.is_dir() else sorted(all_tracked)
    )
    files_written: dict[str, str] = {}
    if build:
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, text in all_tracked.items():
            (out_dir / name).write_text(text, encoding="utf-8")
            files_written[name] = sha256_bytes(text.encode("utf-8"))

    # Operational commit-anchor drift (same narrow tolerance already applied to
    # Part 6 in 01f2b8b and to the robustness closure in f9a47a5). The metadata
    # package embeds live git HEAD in `generated_at` / `code_commit`, which
    # necessarily goes stale the instant the built file is itself committed --
    # a self-referential anchor, not a scientific fact. Under Stage126+ Q1/Q2
    # Lean Governance, commit SHAs used purely as engineering anchors do not
    # fail the live gate. Tolerance is deliberately double-narrowed: only the
    # metadata file, and only when EVERY differing field is a commit anchor.
    # Drift in the decision, boundary manifest, validation report, README or
    # closed-part registry -- or any non-anchor field of the metadata file --
    # still fails closed.
    if check and out_dir.resolve() == canonical_out and tracked_drift:
        scientific_drift = [
            name for name in tracked_drift
            if name != F_METADATA
            or not _metadata_drift_is_anchor_only(out_dir / name, meta)
        ]
        if scientific_drift:
            raise ValidationFail(f"check drift (tracked): {scientific_drift}")
        tracked_drift = []
    if failed:
        raise ValidationFail(f"current-state validation failed: {failed} assertions")

    return {
        "metadata": meta,
        "report": extras["report"],
        "decision": extras["decision"],
        "manifest": extras["manifest"],
        "registry": extras["registry"],
        "assertions": assertions,
        "output_dir": str(out_dir),
        "files": files_written,
        "drift": tracked_drift,
    }
