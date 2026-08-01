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


def expected_active_workstream(repo_root: Path) -> str:
    """The single source of truth for the CURRENT live workstream label.

    `active_workstream` claims to describe the workstream that is live NOW. It
    must therefore advance with the live research state: once the Stage128 D2
    boundary-month design freeze is complete, the live workstream is the
    Stage128 M2 D2 one, not the Stage126 M1 financial baseline. The Stage126
    value remains correct history, but it is no longer the CURRENT value.
    """
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
    return (
        handoff.get("current_stage") == STAGE128_CURRENT_STAGE
        and handoff.get("active_workstream") == STAGE128_ACTIVE_WORKSTREAM
    )


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
            == STAGE128_M2_RETAINED_BLOCK_DECISION_ACTION_ID),
        "after the Gate re-run, the last completed research action must be "
        "the Gate re-run itself or a recognized, completed successor action")
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
