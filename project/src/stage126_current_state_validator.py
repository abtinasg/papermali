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
VALIDATOR_VERSION = "stage126_current_state_validator_v1"
DECISION_ID = "stage126-validation-architecture-boundary-lock"
DECISION_VERSION = "stage126_validation_architecture_boundary_v1"

SRC_REL = "project/src/stage126_current_state_validator.py"
RUN_REL = "project/run_stage126_current_state_validator.py"
TEST_REL = "project/tests/test_stage126_current_state_validator.py"

STAGE126_DIR_REL = "project/stage126"
F_DECISION = "stage126_validation_architecture_boundary_decision.json"
F_BOUNDARY_MANIFEST = "stage126_historical_boundary_manifest.json"
F_REPORT = "stage126_current_state_validation_report.json"
F_METADATA = "metadata_and_hashes_stage126_current_state_validator.json"
F_README = "README_STAGE126_CURRENT_STATE_VALIDATION.md"

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
)
# Part 2 additionally emits an identity-only sample-delta audit.
PART_OPTIONAL_SCIENTIFIC_SUFFIXES: tuple[str, ...] = (
    "sample_delta.csv",
)

PINNED_PART_SCIENTIFIC_ARTIFACTS: dict[str, dict[str, str]] = {
    "m1_target_proximity_six_feature_set": {
        "stage126_m1_robustness_part1_human_authorization_record.json":
            "87a4f55baeb1081eaf936e49c5e8923f67df54ec444f0abc33ec835c0c7e06f4",
        "stage126_m1_robustness_part1_feature_manifest.csv":
            "c65735795eda7dce6b4cacbc6af9dd5914b5068f44c77277035a51463cceaf90",
        "stage126_m1_robustness_part1_execution_manifest.json":
            "80813ce8af9544dde736cc6b94372d2626dccbf888553cd7964625bfe12d8738",
        "stage126_m1_robustness_part1_oof_predictions.csv":
            "1303a31a45e8293be84e7d6c3b23aa1a4c771847de0f1b0207110c33cafdba31",
        "stage126_m1_robustness_part1_metrics.csv":
            "c60f4b15aa40273472be98c867c73795d254f32c2a0e29b76641b1c5d5c18e98",
        "stage126_m1_robustness_part1_primary_comparison.json":
            "2b58a85250420a8a18b0ff37cecdf3f2e31160c37e0cb48d027324c87a25c46a",
        "stage126_m1_robustness_part1_completion_lock.json":
            "964d84f2269bb35b0176f88bb12bcfc13ef2cb487817cf5b49a5c28a87e1822b",
    },
    "main_rule_b_listing_robustness": {
        "stage126_m1_robustness_part2_human_authorization_record.json":
            "0a7bba7489f62f59d3e0f07946b82d8ce4be1a49c4d098f47ca308de9466959e",
        "stage126_m1_robustness_part2_feature_manifest.csv":
            "58c52c17337286237779153d59f85f74c76f84d0c0415b8efadd618aa524b78f",
        "stage126_m1_robustness_part2_sample_delta.csv":
            "baafe97323e45f0a88b07aaf1ea97c50c4b213e43724ddb2b97f3f55144fc7d3",
        "stage126_m1_robustness_part2_execution_manifest.json":
            "9fc153b65a77c906339f51d7c0ad576d23eb06c5895eacb1a0ee92578b321ce8",
        "stage126_m1_robustness_part2_oof_predictions.csv":
            "3af630141a905370849875926fa84052cf10322cc34e18258a25d28106d47dd6",
        "stage126_m1_robustness_part2_metrics.csv":
            "073b8657c0ba2c40f52e05d766a102e2b5d20845821c4eb1cef1b6e53459228c",
        "stage126_m1_robustness_part2_primary_comparison.json":
            "9fc3b4eaf0a27fc66cd22444d92363747157743e822d3be877ecca7f153763bf",
        "stage126_m1_robustness_part2_completion_lock.json":
            "23d1920c4fb0a351456fe54b60616446381bbd550fb18e0bba5dab091486fec6",
    },
}

# --------------------------------------------------------------------------- #
# Expected current state
# --------------------------------------------------------------------------- #

EXPECTED_COMPLETED_CATEGORY_IDS: tuple[str, ...] = (
    "m1_target_proximity_six_feature_set",
    "main_rule_b_listing_robustness",
)
EXPECTED_NEXT_CATEGORY_ID = "expanded_rule_a_company_scope_robustness"
EXPECTED_LAST_MICRO_PART = "stage126-m1-robustness-part2-listing-rule-b"
ACTIVE_WORKSTREAM = "stage126_m1_financial_baseline"
NEXT_RESEARCH_ACTION_ID = "stage126-m1-financial-baseline"

HANDOFF_STATE_REL = "project/docs/ai/handoff_state.json"

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
            "stage126_current_state_validator_version": VALIDATOR_VERSION,
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
    parts: dict[str, Any] = {}
    for category, pinned in sorted(PINNED_PART_SCIENTIFIC_ARTIFACTS.items()):
        observed: dict[str, str] = {}
        for name, expected in sorted(pinned.items()):
            observed[name] = require_file_hash(
                repo_root, f"{STAGE126_DIR_REL}/{name}", expected,
                label=f"{category} scientific artifact",
            )
        parts[category] = observed
    return {
        "contract_id": "stage126_historical_boundary_manifest",
        "contract_version": DECISION_VERSION,
        "decision_id": DECISION_ID,
        "stage125_part5_mode": "historical_immutable",
        "stage125_part5_frozen_files_sha256": dict(sorted(part5.items())),
        "stage125_tracked_file_count": len(tree),
        "stage125_tracked_files_sha256": dict(sorted(tree.items())),
        "stage125_tree_aggregate_sha256": stage125_tree_digest(tree),
        "closed_micro_part_scientific_artifacts_sha256": parts,
        "primary_stage126_artifacts_sha256": dict(sorted(
            PINNED_PRIMARY_ARTIFACTS.items()
        )),
        "boundary_prohibitions": dict(sorted(BOUNDARY_PROHIBITIONS.items())),
        "stage125_part5_historical_provenance": dict(
            sorted(PART5_HISTORICAL_PROVENANCE.items())
        ),
        "regeneration_of_earlier_part_verification_artifacts_allowed": False,
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
        "smote_executed", "smotenc_executed", "shap_executed",
        "replaces_primary_results", "selects_paper_winner",
    ):
        if lock.get(field) is not False:
            raise ValidationFail(
                f"part {part_index} completion lock field {field} is not False"
            )
    return {
        "part_index": part_index,
        "category_id": category_id,
        "authorization_record": auth_rel,
        "completion_lock": lock_rel,
        "metadata_manifest": meta_rel if meta else "",
        "authorization_text_sha256": auth.get("human_authorization_text_sha256", ""),
        "next_category_id": lock.get("next_category_id", ""),
        "completed_category_ids": list(lock.get("completed_category_ids") or []),
        "lock": lock,
        "metadata": meta,
    }


def verify_part_scientific_artifacts(
    repo_root: Path, part: dict[str, Any],
) -> dict[str, str]:
    """Verify a completed part's scientific surface against immutable hashes.

    Pinned parts are checked against the boundary manifest pins. Any part —
    pinned or not — is additionally checked against its OWN metadata manifest,
    so a future Part 3 is protected the moment it lands, with no change here.
    """
    prefix = part_file_prefix(part["part_index"])
    observed: dict[str, str] = {}
    pinned = PINNED_PART_SCIENTIFIC_ARTIFACTS.get(part["category_id"], {})
    for name, expected in sorted(pinned.items()):
        observed[name] = require_file_hash(
            repo_root, f"{STAGE126_DIR_REL}/{name}", expected,
            label=f"{part['category_id']} scientific artifact",
        )
    meta_hashes = (part.get("metadata") or {}).get("output_files_sha256") or {}
    for suffix in PART_SCIENTIFIC_SUFFIXES + PART_OPTIONAL_SCIENTIFIC_SUFFIXES:
        name = f"{prefix}_{suffix}"
        if name not in meta_hashes:
            continue
        got = sha256_file(repo_root / f"{STAGE126_DIR_REL}/{name}")
        if got != meta_hashes[name]:
            raise ValidationFail(
                f"{part['category_id']} scientific artifact drifted from its "
                f"own metadata manifest: {name}"
            )
        observed.setdefault(name, got)
    return observed


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


def verify_handoff(repo_root: Path, completed_ids: list[str]) -> dict[str, Any]:
    """Validate the live Handoff — WITHOUT the frozen Part 5 validator."""
    state = _read_json(repo_root, HANDOFF_STATE_REL)
    exact: dict[str, Any] = {
        "active_workstream": ACTIVE_WORKSTREAM,
        "next_research_action_id": NEXT_RESEARCH_ACTION_ID,
        "m1_robustness_started": True,
        "m1_robustness_completed": False,
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
    next_category: str, part_hashes: dict[str, dict[str, str]],
    primary_observed: dict[str, str], handoff: dict[str, Any],
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
        "completed_category_ids": list(completed_ids),
        "completed_micro_parts": [
            {
                "part_index": p["part_index"],
                "category_id": p["category_id"],
                "authorization_record": p["authorization_record"],
                "completion_lock": p["completion_lock"],
                "authorization_text_sha256": p["authorization_text_sha256"],
            }
            for p in completed
        ],
        "next_category_id": next_category,
        "next_category_authorized": False,
        "standing_execution_authorization": False,
        "m1_robustness_started": True,
        "m1_robustness_completed": False,
        "full_development_refit_performed": False,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_predictor_values_inspected": False,
        "final_test_target_values_inspected": False,
        "final_test_evaluation_performed": False,
        "last_completed_micro_part": handoff.get("last_completed_micro_part", ""),
        "active_workstream": ACTIVE_WORKSTREAM,
        "next_research_action_id": NEXT_RESEARCH_ACTION_ID,
        "closed_micro_part_scientific_artifacts_sha256": part_hashes,
        "primary_stage126_artifacts_sha256": dict(sorted(primary_observed.items())),
        "prior_part_verification_artifact_regeneration_allowed": False,
        "prior_part_reopening_requires_scientific_error": True,
        "prior_part_reopening_requires_explicit_human_authorization": True,
        "validator_reopened_a_previous_part": False,
    }


def build_assertions(
    repo_root: Path, *, decision: dict[str, Any], manifest: dict[str, Any],
    report: dict[str, Any], execution_order: list[str],
    completed: list[dict[str, Any]], handoff: dict[str, Any],
    source_text: str,
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

    # Completed contiguous prefix.
    add("completed_categories_exact",
        tuple(report["completed_category_ids"])
        == EXPECTED_COMPLETED_CATEGORY_IDS,
        str(report["completed_category_ids"]))
    add("completed_prefix_is_contiguous",
        list(report["completed_category_ids"])
        == execution_order[:len(report["completed_category_ids"])])
    add("next_category_exact",
        report["next_category_id"] == EXPECTED_NEXT_CATEGORY_ID,
        report["next_category_id"])
    add("next_category_not_authorized",
        report["next_category_authorized"] is False)
    add("no_standing_execution_authorization",
        report["standing_execution_authorization"] is False
        and handoff.get("m1_robustness_execution_authorized") is False)
    add("m1_robustness_not_completed",
        report["m1_robustness_completed"] is False
        and handoff.get("m1_robustness_completed") is False)

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
    for category, pinned in sorted(PINNED_PART_SCIENTIFIC_ARTIFACTS.items()):
        observed = report["closed_micro_part_scientific_artifacts_sha256"].get(
            category, {}
        )
        add(f"scientific_artifacts_immutable[{category}]",
            all(observed.get(k) == v for k, v in pinned.items())
            and len(pinned) >= 7)

    # Final-test lock.
    add("final_test_locked_everywhere",
        all(report[f] is False for f in FINAL_TEST_LOCK_FIELDS)
        and all(handoff.get(f) is False for f in FINAL_TEST_LOCK_FIELDS))
    add("no_full_development_refit",
        report["full_development_refit_performed"] is False)

    # Earlier-part protection + exception policy.
    add("prior_verification_artifact_regeneration_forbidden",
        report["prior_part_verification_artifact_regeneration_allowed"] is False
        and manifest[
            "regeneration_of_earlier_part_verification_artifacts_allowed"
        ] is False)
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

    # Research pointers unchanged.
    add("research_pointers_unchanged",
        report["active_workstream"] == ACTIVE_WORKSTREAM
        and report["next_research_action_id"] == NEXT_RESEARCH_ACTION_ID)
    add("last_completed_micro_part_exact",
        report["last_completed_micro_part"] == EXPECTED_LAST_MICRO_PART)
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

def build_all(repo_root: Path) -> tuple[dict[str, str], dict[str, Any]]:
    verify_decision_text()
    decision = build_decision_record()
    manifest = build_boundary_manifest(repo_root)

    part0 = verify_part0_contract(repo_root)
    execution_order = list(part0["execution_order"])
    primary_observed = verify_primary_stage126_artifacts(repo_root)
    verify_selected_configurations(repo_root)
    verify_final_test_lock(repo_root)

    completed, completed_ids = completed_prefix(repo_root, execution_order)
    part_hashes = {
        p["category_id"]: verify_part_scientific_artifacts(repo_root, p)
        for p in completed
    }
    next_category = verify_no_unauthorized_execution(
        repo_root, execution_order, completed,
    )
    handoff = verify_handoff(repo_root, completed_ids)

    report = build_validation_report(
        repo_root, execution_order=execution_order, completed=completed,
        completed_ids=completed_ids, next_category=next_category,
        part_hashes=part_hashes, primary_observed=primary_observed,
        handoff=handoff,
    )
    readme = build_readme(report)
    content = {
        F_DECISION: _json_str(decision),
        F_BOUNDARY_MANIFEST: _json_str(manifest),
        F_REPORT: _json_str(report),
        F_README: readme,
    }
    extras = {
        "decision": decision, "manifest": manifest, "report": report,
        "execution_order": execution_order, "completed": completed,
        "handoff": handoff, "part_hashes": part_hashes,
    }
    return content, extras


def _compare_drift(out_dir: Path, payloads: dict[str, str]) -> list[str]:
    drift: list[str] = []
    for name, text in payloads.items():
        path = out_dir / name
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            drift.append(name)
    return drift


def boundary_handoff_markers() -> dict[str, Any]:
    """Fail-closed Handoff markers describing the validation architecture."""
    return {
        "validation_architecture": VALIDATOR_VERSION,
        "stage125_part5_mode": "historical_immutable",
        "stage125_part5_live_gate_active": False,
        "stage125_part5_future_regeneration_allowed": False,
        "prior_robustness_verification_artifact_regeneration_allowed": False,
        "prior_part_reopening_requires_scientific_error": True,
        "prior_part_reopening_requires_explicit_human_authorization": True,
    }


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

    content, extras = build_all(repo_root)

    source_text = (repo_root / SRC_REL).read_text(encoding="utf-8")
    assertions = build_assertions(
        repo_root, decision=extras["decision"], manifest=extras["manifest"],
        report=extras["report"], execution_order=extras["execution_order"],
        completed=extras["completed"], handoff=extras["handoff"],
        source_text=source_text,
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

    if check and out_dir.resolve() == canonical_out and tracked_drift:
        raise ValidationFail(f"check drift (tracked): {tracked_drift}")
    if failed:
        raise ValidationFail(f"current-state validation failed: {failed} assertions")

    return {
        "metadata": meta,
        "report": extras["report"],
        "decision": extras["decision"],
        "manifest": extras["manifest"],
        "assertions": assertions,
        "output_dir": str(out_dir),
        "files": files_written,
        "drift": tracked_drift,
    }
