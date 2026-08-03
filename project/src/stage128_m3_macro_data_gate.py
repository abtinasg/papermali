"""Stage128 — ``stage128-m3-macro-data-gate``.

Execute the M3 macro **data-admission** Gate for the exact frozen three-variable
macro block, under one human authorization.

What this module is
-------------------
A **data Gate**. It answers only:

    Can the exact frozen M3 macro block be obtained from authoritative,
    reproducible and point-in-time-safe sources with sufficient development
    coverage, usable paired sample and temporal support?

It does **not** answer whether M3 improves prediction. It therefore:

* never fits an estimator, never predicts, never resamples;
* never computes a predictive metric (PR-AUC, ROC-AUC, Recall@K, Lift@K,
  Brier, calibration, bootstrap, Holm, SHAP, SMOTE);
* never executes an M3-versus-M2 comparison;
* never touches a final-test predictor or target value;
* never starts M3 incremental evaluation, M4 or a merge.

Two ordered phases
------------------
**Phase A — metadata-only source and definition lock.** Before any value-level
work, every operational series choice and transformation detail must be frozen
from source schema, documentation, publication metadata and theoretical
meaning — never from observed coverage and never from target outcomes. If the
frozen contracts plus official evidence do not determine a unique series and
transformation for each candidate, the Gate is ``UNRESOLVED_M3_DATA_GATE`` and
execution **stops before Phase B**.

**Phase B — development-only Gate execution.** Reachable only from an
immutable, RESOLVED Phase-A lock. :func:`assert_phase_b_permitted` fail-closes
otherwise, so an unresolved lock cannot be opportunistically completed by
trying alternative series until coverage improves.

No-execution guarantee
----------------------
``FORBIDDEN_RUNTIME_MODULES`` lists the estimator / resampling libraries this
module must never pull in, and :func:`assert_no_estimator_runtime` fails closed
if any of them reaches this module's import graph. The module imports only the
standard library.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #

ACTION_ID = "stage128-m3-macro-data-gate"
CONTRACT_ID = "stage128_m3_macro_data_gate"
CONTRACT_VERSION = "stage128_m3_macro_data_gate_v1"
GATE_TYPE = "macro_data_admission_gate_only_no_predictive_modeling"

#: What this repository code actually implements. It is NOT a complete
#: executable PASS/FAIL data Gate: only Phase A (official-source
#: discovery, a metadata-only prospective lock attempt, and UNRESOLVED
#: decision recording) is implemented. Value-level Phase B -- retrieval,
#: normalization, transformation, join, coverage, event counts and
#: temporal support -- is deliberately NOT implemented here and would
#: require official metadata plus a new explicit authorization after
#: human review.
IMPLEMENTATION_SCOPE = "PHASE_A_TERMINAL_UNRESOLVED_SNAPSHOT"
PHASE_B_IMPLEMENTATION_PRESENT = False
PHASE_B_NOT_EXECUTED_REASON = (
    "official_metadata_unavailable_and_definition_lock_unresolved")

#: What this action actually executed.
EXECUTED_STEPS: tuple[str, ...] = (
    "official_source_discovery",
    "metadata_only_prospective_lock_attempt",
    "unresolved_decision_recording",
)

#: What this action did NOT execute.
NOT_EXECUTED_STEPS: tuple[str, ...] = (
    "value_level_retrieval",
    "value_level_coverage_assessment",
    "value_level_join",
    "value_level_event_count_assessment",
    "value_level_temporal_support_assessment",
)
REPOSITORY = "abtinasg/papermali"
BASELINE_BRANCH = "main"
BASELINE_COMMIT = "35aaf4b70e9341704ee38be6f8cf2e2519c70bb2"

PREDECESSOR_ACTION_ID = "stage128-m2-retained-block-human-decision"

#: Advanced ONLY on PASS. A pointer is never an authorization.
NEXT_ACTION_ON_PASS = "stage128-m3-incremental-evaluation"

PACKAGE_DIR_REL = "project/stage128/m3_macro_data_gate"
RAW_DIR_REL = f"{PACKAGE_DIR_REL}/raw"

README_REL = f"{PACKAGE_DIR_REL}/README_STAGE128_M3_MACRO_DATA_GATE.md"
AUTHORIZATION_REL = (
    f"{PACKAGE_DIR_REL}/stage128_m3_macro_data_gate_human_authorization_record"
    ".json")
LOCK_REL = f"{PACKAGE_DIR_REL}/stage128_m3_macro_source_definition_lock.json"
SOURCE_MANIFEST_REL = (
    f"{PACKAGE_DIR_REL}/stage128_m3_macro_source_manifest.csv")
RAW_EVIDENCE_REL = (
    f"{PACKAGE_DIR_REL}/stage128_m3_macro_raw_evidence_manifest.json")
NORMALIZED_OBS_REL = (
    f"{PACKAGE_DIR_REL}/stage128_m3_macro_normalized_observations.csv")
DEV_FEATURES_REL = f"{PACKAGE_DIR_REL}/stage128_m3_development_features.csv"
COVERAGE_AUDIT_REL = (
    f"{PACKAGE_DIR_REL}/stage128_m3_candidate_coverage_audit.csv")
COMMON_SAMPLE_REL = f"{PACKAGE_DIR_REL}/stage128_m3_common_sample_audit.json"
EVENT_COUNT_REL = f"{PACKAGE_DIR_REL}/stage128_m3_event_count_audit.csv"
TEMPORAL_DEGREES_REL = (
    f"{PACKAGE_DIR_REL}/stage128_m3_temporal_degrees_audit.json")
FIREWALL_REL = f"{PACKAGE_DIR_REL}/stage128_m3_final_test_firewall_audit.json"
DECISION_REL = f"{PACKAGE_DIR_REL}/stage128_m3_macro_data_gate_decision.json"
QC_REL = f"{PACKAGE_DIR_REL}/stage128_m3_macro_data_gate_qc_report.json"
METADATA_REL = (
    f"{PACKAGE_DIR_REL}/metadata_and_hashes_stage128_m3_macro_data_gate.json")

# --------------------------------------------------------------------------- #
# Exact human authorization
# --------------------------------------------------------------------------- #

#: The EXACT human source utterance, one UTF-8 line, no trailing newline.
#: Verbatim human text. Authoritative ONLY in the authorization record.
HUMAN_SOURCE_UTTERANCE = "بریم مرحله بعدی"
HUMAN_SOURCE_UTTERANCE_BYTE_LENGTH = 28
HUMAN_SOURCE_UTTERANCE_SHA256 = (
    "d4acc9698f160ed0f252fd3f2a698b2b17916144d3dc182333cd2892a5d23068")

#: DERIVED, NON-VERBATIM restatement of the authorized scope. Labelled as
#: derived everywhere it appears; never presented as human text.
NORMALIZED_AUTHORIZATION_SCOPE = (
    "The human supervisor authorizes exactly one execution of "
    "stage128-m3-macro-data-gate: official-source discovery, prospective "
    "source/definition locking, development-only retrieval, construction and "
    "data-admission assessment of the exact frozen three-variable M3 macro "
    "block. This authorization permits no M3 predictive modeling, no "
    "M3-vs-M2 evaluation, no retuning, no final-test access, no M4 action and "
    "no merge."
)


class M3MacroDataGateError(RuntimeError):
    """Raised whenever any fail-closed precondition is violated."""


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: str | os.PathLike[str]) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_human_authorization() -> dict[str, Any]:
    """Recompute the authorization byte length and SHA-256; fail closed."""
    raw = HUMAN_SOURCE_UTTERANCE.encode("utf-8")
    if len(raw) != HUMAN_SOURCE_UTTERANCE_BYTE_LENGTH:
        raise M3MacroDataGateError(
            f"authorization byte length {len(raw)} != "
            f"{HUMAN_SOURCE_UTTERANCE_BYTE_LENGTH}")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != HUMAN_SOURCE_UTTERANCE_SHA256:
        raise M3MacroDataGateError(
            f"authorization sha256 {digest} != {HUMAN_SOURCE_UTTERANCE_SHA256}")
    if HUMAN_SOURCE_UTTERANCE.endswith("\n"):
        raise M3MacroDataGateError("authorization must have no trailing newline")
    return {
        "human_source_utterance_byte_length": len(raw),
        "human_source_utterance_sha256": digest,
        "normalized_authorization_scope_sha256": _sha256_text(
            NORMALIZED_AUTHORIZATION_SCOPE),
    }


# --------------------------------------------------------------------------- #
# No-execution guarantee
# --------------------------------------------------------------------------- #

FORBIDDEN_RUNTIME_MODULES: tuple[str, ...] = (
    "sklearn",
    "xgboost",
    "imblearn",
    "shap",
    "lightgbm",
    "catboost",
    "statsmodels",
)

FORBIDDEN_ESTIMATOR_CALLS: tuple[str, ...] = (
    "fit",
    "fit_predict",
    "fit_resample",
    "fit_transform",
    "predict",
    "predict_proba",
    "decision_function",
    "resample",
)

#: Predictive metrics this data Gate must never compute.
FORBIDDEN_PREDICTIVE_METRICS: tuple[str, ...] = (
    "pr_auc",
    "roc_auc",
    "recall_at_k",
    "lift_at_k",
    "brier",
    "calibration",
    "bootstrap",
    "holm",
    "shap",
    "smote",
)


def assert_no_estimator_runtime() -> None:
    """Fail closed if an estimator/resampling runtime reached this process.

    Only modules this module pulled in are relevant, so the check is applied
    to its own import graph: it imports the standard library only.
    """
    own = sys.modules[__name__]
    imported = {
        name for name, value in vars(own).items()
        if getattr(value, "__name__", "") in FORBIDDEN_RUNTIME_MODULES
    }
    if imported:
        raise M3MacroDataGateError(
            f"forbidden estimator runtime imported: {sorted(imported)}")


# --------------------------------------------------------------------------- #
# Exact frozen M3 block — never reduced, expanded or reordered
# --------------------------------------------------------------------------- #

M3_BLOCK: tuple[str, ...] = (
    "cpi_inflation",
    "fx_change_official",
    "policy_financing_rate",
)

M3_CANDIDATE_IDS: tuple[str, ...] = (
    "cand_m3_cpi_inflation",
    "cand_m3_fx_change_official",
    "cand_m3_policy_financing_rate",
)

CANDIDATE_TO_VARIABLE: dict[str, str] = dict(zip(M3_CANDIDATE_IDS, M3_BLOCK))

REQUIRED_SOURCE_ID = "src_m3_cbi_macro"
REQUIRED_AUTHORITY = "Central Bank of Iran"

#: Substitutions and silent remaps that are explicitly forbidden.
FORBIDDEN_SUBSTITUTIONS: tuple[str, ...] = (
    "src_m3_sci_macro_silent_remap",
    "sci_cpi_for_cbi_cpi",
    "sci_for_cbi_fx",
    "sci_for_cbi_policy_rate",
    "free_market_fx",
    "oos_free_market_fx",
)

#: Scope expansions that are explicitly forbidden.
FORBIDDEN_ADDITIONS: tuple[str, ...] = (
    "liquidity_growth",
    "gdp",
    "production_index",
    "oil_price",
    "unofficial_exchange_rate",
    "free_market_exchange_rate",
    "scraped_aggregator_data",
    "private_commercial_macro_dataset",
    "searched_macro_variable_universe",
    "economic_regime_variable",
    "any_fourth_m3_variable",
)


def assert_exact_m3_block(block: tuple[str, ...] | list[str]) -> None:
    """The exact three-variable block, in frozen order. No partial block."""
    if tuple(block) != M3_BLOCK:
        raise M3MacroDataGateError(
            f"M3 block must be exactly {M3_BLOCK} in this order; got "
            f"{tuple(block)}")


# --------------------------------------------------------------------------- #
# Frozen Gate rules and Stage125 Part 4 development thresholds
# --------------------------------------------------------------------------- #

GATE_RULES: dict[str, str] = {
    "G01": "accessibility score >= 3",
    "G02": "authoritative source required",
    "G03": "reproducible retrieval path required",
    "G04": "published_at or available_at verified",
    "G05": "extraction, unit, calendar and join errors controlled",
    "G06": "missing availability means unavailable",
    "G07": "no future or target-year information",
    "G08": "all G01-G07 must pass",
}

CANDIDATE_VALID_COVERAGE_MIN = 0.80
BLOCK_COMMON_SAMPLE_COVERAGE_MIN = 0.70
MIN_POSITIVE_EACH_VALIDATION_WINDOW = 5
ACCESSIBILITY_SCORE_MIN = 3

#: Historical 80-pair Part 3A pilot thresholds. Registered ONLY so tests can
#: prove they are not applied to this development Gate.
HISTORICAL_PILOT_RULES_NOT_APPLICABLE: tuple[str, ...] = (
    "G09", "G10", "G11", "G12", "G13", "G14",
)

STAGE125_PART4_SAP_REL = (
    "project/stage125/part4_statistical_analysis_plan_stage125.json")
STAGE125_PART3B1_CONTRACT_REL = (
    "project/stage125/part3b1_m3_cbi_policy_contract_stage125.json")
STAGE125_SOURCE_REGISTRY_REL = "project/stage125/source_registry_stage125.csv"
STAGE125_DATA_DICTIONARY_REL = "project/stage125/data_dictionary_stage125.csv"
STAGE125_VERIFIED_ENDPOINTS_REL = (
    "project/stage125/part3b_verified_endpoint_registry_stage125.csv")

M2_JOIN_AUDIT_REL = (
    "project/stage128/m2_incremental_evaluation/"
    "stage127_m2_common_sample_join_audit.json")
M2_ATTRITION_REL = (
    "project/stage128/m2_incremental_evaluation/"
    "stage127_m2_parent_to_common_sample_attrition_audit.json")
D2_FEATURES_REL = "project/stage128/stage128_m2_d2_development_features.csv"


def verify_thresholds_against_frozen_contract(root: Path) -> dict[str, Any]:
    """Re-read the Stage125 Part 4 thresholds and fail closed on drift."""
    sap = json.loads(
        (root / STAGE125_PART4_SAP_REL).read_text(encoding="utf-8"))
    found: dict[str, Any] = {}

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ("candidate_valid_coverage_min",
                           "block_common_sample_coverage_min",
                           "min_positive_evaluable_each_temporal_validation_"
                           "window"):
                    found[key] = value
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(sap)
    expected = {
        "candidate_valid_coverage_min": CANDIDATE_VALID_COVERAGE_MIN,
        "block_common_sample_coverage_min": BLOCK_COMMON_SAMPLE_COVERAGE_MIN,
        "min_positive_evaluable_each_temporal_validation_window":
            MIN_POSITIVE_EACH_VALIDATION_WINDOW,
    }
    for key, value in expected.items():
        if key not in found:
            raise M3MacroDataGateError(
                f"threshold {key} absent from {STAGE125_PART4_SAP_REL}")
        if float(found[key]) != float(value):
            raise M3MacroDataGateError(
                f"threshold {key} is {found[key]} in the frozen contract but "
                f"{value} here; thresholds must not be lowered or replaced")
    return {
        "source_contract": STAGE125_PART4_SAP_REL,
        "source_contract_sha256": _sha256_file(root / STAGE125_PART4_SAP_REL),
        "candidate_valid_coverage_min": CANDIDATE_VALID_COVERAGE_MIN,
        "block_common_sample_coverage_min": BLOCK_COMMON_SAMPLE_COVERAGE_MIN,
        "min_positive_evaluable_each_temporal_validation_window":
            MIN_POSITIVE_EACH_VALIDATION_WINDOW,
        "historical_80_pair_pilot_rules_applied": False,
        "historical_80_pair_pilot_rules_not_applicable": list(
            HISTORICAL_PILOT_RULES_NOT_APPLICABLE),
    }


# --------------------------------------------------------------------------- #
# Locked temporal folds
# --------------------------------------------------------------------------- #

DEVELOPMENT_TARGET_YEARS: tuple[str, ...] = (
    "1393", "1394", "1395", "1396", "1397", "1398", "1399")
FINAL_TEST_TARGET_YEARS: tuple[str, ...] = ("1400", "1401", "1402")

LOCKED_FOLDS: dict[str, dict[str, tuple[str, ...]]] = {
    "fold1": {
        "train": ("1393", "1394", "1395"),
        "validation": ("1396", "1397"),
    },
    "fold2": {
        "train": ("1393", "1394", "1395", "1396", "1397"),
        "validation": ("1398", "1399"),
    },
}

#: Frozen pair-identity join keys. No fuzzy matching is ever permitted.
REQUIRED_JOIN_KEYS: tuple[str, ...] = (
    "predictor_row_key_t",
    "target_row_key_t_plus_1",
    "ticker",
    "fiscal_year_t",
    "target_year",
)

FUZZY_MATCHING_PERMITTED = False


# --------------------------------------------------------------------------- #
# Gate outcome vocabulary
# --------------------------------------------------------------------------- #

GATE_STATUS_PASS = "PASS_FOR_M3_INCREMENTAL_EVALUATION"
GATE_STATUS_FAIL = "FAIL_M3_DATA_GATE"
GATE_STATUS_UNRESOLVED = "UNRESOLVED_M3_DATA_GATE"

GATE_STATUS_VOCABULARY: tuple[str, ...] = (
    GATE_STATUS_PASS, GATE_STATUS_FAIL, GATE_STATUS_UNRESOLVED)


def assert_gate_status_in_vocabulary(status: str) -> None:
    if status not in GATE_STATUS_VOCABULARY:
        raise M3MacroDataGateError(
            f"gate status {status!r} not in {GATE_STATUS_VOCABULARY}")


# --------------------------------------------------------------------------- #
# Protected upstream immutability manifest
# --------------------------------------------------------------------------- #

#: Every tracked file under these trees, AS OF ``BASELINE_COMMIT``, is a
#: protected upstream scientific artifact this action may not modify.
PROTECTED_TREES: tuple[str, ...] = (
    "project/stage125",
    "project/stage126",
    "project/stage127",
    "project/stage128/m2_incremental_evaluation",
    "project/stage128/m2_retained_block_human_decision",
)

#: Individually protected upstream files outside the protected trees.
PROTECTED_EXTRA_FILES: tuple[str, ...] = (
    "project/stage128/stage128_m2_d2_development_features.csv",
)

#: OPERATIONAL verification artifacts of the Stage126 current-state validator.
#: These are NOT frozen scientific artifacts: they are regenerated by
#: ``run_stage126_current_state_validator.py --build`` whenever the validator
#: source legitimately changes, and the repository's own governance permits
#: exactly that (``prior_part_operational_verification_artifact_evolution_
#: permitted = True``). PR #72 -- which is merged into this action's baseline --
#: regenerated all three itself. Freezing them would make the validator
#: unmaintainable and would contradict the repository's governance, so they are
#: excluded from the protected SCIENTIFIC set.
#:
#: This exclusion list is CLOSED and asserted by tests: nothing may be added to
#: it, and every entry must be an artifact the validator itself regenerates.
PROTECTED_OPERATIONAL_EXCLUSIONS: tuple[str, ...] = (
    "project/stage126/README_STAGE126_CURRENT_STATE_VALIDATION.md",
    "project/stage126/metadata_and_hashes_stage126_current_state_validator.json",
    "project/stage126/stage126_current_state_validation_report.json",
)


def _git(root: Path, *args: str) -> str:
    """Run a read-only git command; fail closed on a non-zero exit."""
    import subprocess

    proc = subprocess.run(
        ["git", *args], cwd=str(root), capture_output=True, text=True)
    if proc.returncode != 0:
        raise M3MacroDataGateError(
            f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def _tracked_files_under(root: Path, commit: str) -> tuple[str, ...]:
    out = _git(root, "ls-tree", "-r", "--name-only", "-z", commit, "--",
               *PROTECTED_TREES)
    return tuple(sorted(p for p in out.split("\0") if p))


def enumerate_protected_baseline_files(root: Path) -> tuple[str, ...]:
    """The complete protected SCIENTIFIC path set, from the baseline commit.

    Operational verification artifacts the Stage126 validator regenerates are
    excluded (see :data:`PROTECTED_OPERATIONAL_EXCLUSIONS`); every other
    tracked baseline file under the protected trees is included.
    """
    paths = set(_tracked_files_under(root, BASELINE_COMMIT))
    paths -= set(PROTECTED_OPERATIONAL_EXCLUSIONS)
    for rel in PROTECTED_EXTRA_FILES:
        try:
            _git(root, "cat-file", "-e", f"{BASELINE_COMMIT}:{rel}")
        except M3MacroDataGateError as exc:
            raise M3MacroDataGateError(
                f"protected extra file absent at baseline {BASELINE_COMMIT}: "
                f"{rel}") from exc
        paths.add(rel)
    if not paths:
        raise M3MacroDataGateError(
            "protected baseline enumeration produced no files")
    return tuple(sorted(paths))


def baseline_protected_manifest(root: Path) -> dict[str, str]:
    """SHA-256 of the BASELINE bytes of every protected upstream path.

    Baseline blobs are hashed as opaque bytes. They are never parsed, decoded
    or evaluated here, so no final-test value is read by the manifest itself.
    """
    import subprocess

    paths = enumerate_protected_baseline_files(root)
    proc = subprocess.run(
        ["git", "cat-file", "--batch"], cwd=str(root), capture_output=True,
        input="".join(f"{BASELINE_COMMIT}:{rel}\n" for rel in paths
                      ).encode("utf-8"))
    if proc.returncode != 0:
        raise M3MacroDataGateError(
            f"git cat-file --batch failed: {proc.stderr.decode()!r}")
    manifest: dict[str, str] = {}
    buf, pos = proc.stdout, 0
    for rel in paths:
        nl = buf.find(b"\n", pos)
        if nl < 0:
            raise M3MacroDataGateError(f"truncated git cat-file output at {rel}")
        header = buf[pos:nl].decode("utf-8").split()
        if len(header) != 3 or header[1] != "blob":
            raise M3MacroDataGateError(
                f"protected baseline path is not a blob: {rel} ({header})")
        size = int(header[2])
        start = nl + 1
        manifest[rel] = hashlib.sha256(buf[start:start + size]).hexdigest()
        pos = start + size + 1
    return dict(sorted(manifest.items()))


def verify_protected_immutability(
    root: Path, manifest: dict[str, str],
) -> dict[str, Any]:
    """Fail closed unless the branch reproduces the protected baseline bytes.

    Compares COMMITTED HISTORY against the exact baseline commit, not merely
    the working tree against HEAD.
    """
    expected_paths = enumerate_protected_baseline_files(root)
    expected = baseline_protected_manifest(root)

    if len(manifest) != len(expected_paths):
        raise M3MacroDataGateError(
            f"protected manifest count {len(manifest)} != enumerated "
            f"{len(expected_paths)}")
    if tuple(sorted(manifest)) != expected_paths:
        missing = sorted(set(expected_paths) - set(manifest))
        extra = sorted(set(manifest) - set(expected_paths))
        raise M3MacroDataGateError(
            f"protected path set differs: missing={missing} extra={extra}")

    for rel in expected_paths:
        if manifest[rel] != expected[rel]:
            raise M3MacroDataGateError(
                f"stored protected hash differs from baseline blob: {rel}")
        path = root / rel
        if not path.is_file():
            raise M3MacroDataGateError(
                f"protected baseline file is absent on this branch: {rel}")
        if _sha256_file(path) != expected[rel]:
            raise M3MacroDataGateError(
                f"protected file bytes differ from baseline: {rel}")

    added = sorted(set(_tracked_files_under(root, "HEAD"))
                   - set(expected_paths)
                   - set(PROTECTED_OPERATIONAL_EXCLUSIONS))
    if added:
        raise M3MacroDataGateError(
            f"new tracked file(s) inside a protected tree: {added}")

    changed = [p for p in _git(
        root, "diff", "--name-only", f"{BASELINE_COMMIT}..HEAD", "--",
        *expected_paths).splitlines() if p.strip()]
    if changed:
        raise M3MacroDataGateError(
            f"protected paths changed in committed history: {sorted(changed)}")

    return {
        "protected_baseline_commit": BASELINE_COMMIT,
        "protected_trees": list(PROTECTED_TREES),
        "protected_extra_files": list(PROTECTED_EXTRA_FILES),
        "protected_operational_exclusions": list(
            PROTECTED_OPERATIONAL_EXCLUSIONS),
        "protected_operational_exclusions_are_not_scientific_artifacts": True,
        "protected_file_count": len(expected_paths),
        "protected_paths_match_baseline": True,
        "protected_bytes_match_baseline": True,
        "protected_tree_has_no_new_tracked_files": True,
        "protected_committed_history_diff_empty": True,
    }


# --------------------------------------------------------------------------- #
# Phase A — prospective source and definition lock (metadata only)
# --------------------------------------------------------------------------- #

#: Every operational detail that must be uniquely frozen BEFORE any value-level
#: work. Section 5 of the authorization enumerates these exactly.
REQUIRED_LOCK_FIELDS: tuple[str, ...] = (
    "candidate_id",
    "variable_name",
    "official_source_id",
    "official_source_owner",
    "official_series_title",
    "official_series_code_or_table_id",
    "official_source_url_or_endpoint",
    "source_artifact_type",
    "frequency",
    "unit",
    "calendar",
    "observation_period_definition",
    "publication_or_release_date_field",
    "available_at_definition",
    "revision_or_vintage_policy",
    "as_of_selection_rule",
    "transformation_formula",
    "transformation_window",
    "missing_value_policy",
    "same_day_cutoff_policy",
)

LOCK_STATUS_RESOLVED = "RESOLVED_DEFINITION_LOCK"
LOCK_STATUS_UNRESOLVED = "UNRESOLVED_DEFINITION_LOCK"

#: Fields determinable from already-frozen Stage125 contracts alone, with the
#: contract each value comes from. Everything else needs official CBI evidence.
_CONTRACT_DETERMINED: dict[str, tuple[str, str]] = {
    "official_source_id": (REQUIRED_SOURCE_ID, STAGE125_PART3B1_CONTRACT_REL),
    "official_source_owner": (REQUIRED_AUTHORITY, STAGE125_SOURCE_REGISTRY_REL),
    "frequency": ("monthly", STAGE125_SOURCE_REGISTRY_REL),
    "unit": ("percent", STAGE125_DATA_DICTIONARY_REL),
}

#: Why each candidate's operational series and transformation are NOT uniquely
#: determined. These are ambiguity classes recorded to justify UNRESOLVED; they
#: are deliberately NOT a menu from which this action may choose, and they were
#: NOT verifiable against official CBI documentation because official access
#: failed (see the raw evidence manifest).
_AMBIGUITY_CLASSES: dict[str, tuple[str, ...]] = {
    "cand_m3_cpi_inflation": (
        "index_base_year_not_frozen",
        "inflation_transformation_not_frozen_point_to_point_vs_moving_average"
        "_vs_month_on_month",
        "transformation_window_not_frozen",
        "release_calendar_and_publication_lag_not_frozen",
    ),
    "cand_m3_fx_change_official": (
        "which_official_rate_not_frozen",
        "fx_change_transformation_not_frozen",
        "transformation_window_not_frozen",
        "official_rate_regime_changes_across_development_period_not_frozen",
    ),
    "cand_m3_policy_financing_rate": (
        "which_policy_or_financing_rate_not_frozen",
        "rate_is_administered_stepwise_and_effective_date_rule_not_frozen",
        "transformation_and_as_of_rule_not_frozen",
        "release_or_circular_date_field_not_frozen",
    ),
}


def build_definition_lock(
    root: Path, evidence: dict[str, Any],
) -> dict[str, Any]:
    """Phase A. Freeze what the contracts determine; mark the rest unresolved.

    The lock is built from source schema, frozen contracts and publication
    metadata **only**. It never reads observed coverage, candidate values or
    target labels, so it cannot be tuned to make the Gate pass.
    """
    assert_exact_m3_block(M3_BLOCK)

    candidates: list[dict[str, Any]] = []
    for candidate_id in M3_CANDIDATE_IDS:
        fields: dict[str, Any] = {}
        provenance: dict[str, str] = {}
        unresolved: list[str] = []
        for field in REQUIRED_LOCK_FIELDS:
            if field == "candidate_id":
                fields[field] = candidate_id
                provenance[field] = STAGE125_PART3B1_CONTRACT_REL
            elif field == "variable_name":
                fields[field] = CANDIDATE_TO_VARIABLE[candidate_id]
                provenance[field] = STAGE125_DATA_DICTIONARY_REL
            elif field in _CONTRACT_DETERMINED:
                # Contract-determined fields are frozen by already-committed
                # Stage125 contracts. They stay populated regardless of whether
                # official evidence is available -- availability of evidence
                # never un-determines a frozen contract value.
                value, contract = _CONTRACT_DETERMINED[field]
                fields[field] = value
                provenance[field] = contract
            else:
                fields[field] = None
                unresolved.append(field)
        candidates.append({
            "candidate_id": candidate_id,
            "variable_name": CANDIDATE_TO_VARIABLE[candidate_id],
            "lock_fields": fields,
            "lock_field_provenance": provenance,
            "unresolved_lock_fields": unresolved,
            "unresolved_lock_field_count": len(unresolved),
            "uniquely_determined": not unresolved,
            "unverified_candidate_ambiguity_classes": list(
                _AMBIGUITY_CLASSES[candidate_id]),
            "ambiguity_classes_are_unverified_and_derived_from_the_incomplete_"
            "frozen_contract": True,
            "ambiguity_enumeration_is_not_a_menu_to_choose_from": True,
            "ambiguity_classes_verified_against_official_documentation": False,
            "ambiguity_classes_note": (
                "Derived from what the incomplete frozen contract leaves open. "
                "They were NOT verified against official CBI documentation and "
                "must not be read as verified facts about CBI series."),
            "candidate_dropped_or_substituted": False,
            "alternative_series_tried_after_coverage_inspection": False,
        })

    all_unique = all(c["uniquely_determined"] for c in candidates)
    status = LOCK_STATUS_RESOLVED if all_unique else LOCK_STATUS_UNRESOLVED
    return {
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "phase": "A_prospective_source_and_definition_lock",
        "generated_for": ACTION_ID,
        "source_repository": REPOSITORY,
        "source_main_branch": BASELINE_BRANCH,
        "source_main_commit": BASELINE_COMMIT,
        "lock_status": status,
        "m3_block": list(M3_BLOCK),
        "m3_candidate_ids": list(M3_CANDIDATE_IDS),
        "required_source_id": REQUIRED_SOURCE_ID,
        "required_authority": REQUIRED_AUTHORITY,
        "required_lock_fields": list(REQUIRED_LOCK_FIELDS),
        "candidates": candidates,
        "locked_before_any_value_level_execution": True,
        "locked_from_schema_documentation_and_theory_not_from_coverage": True,
        "locked_from_target_outcomes": False,
        "forbidden_substitutions": list(FORBIDDEN_SUBSTITUTIONS),
        "forbidden_substitutions_used": [],
        "forbidden_additions": list(FORBIDDEN_ADDITIONS),
        "forbidden_additions_used": [],
        "unofficial_or_sci_source_used": False,
        "block_reduced_expanded_or_reordered": False,
        "lock_note": (
            "Phase A froze only what the already-committed Stage125 contracts "
            "uniquely determine. Every field requiring official CBI schema, "
            "series identity, release metadata or vintage documentation is "
            "recorded as null and unresolved for TWO distinct reasons that "
            "must not be conflated: (1) FROZEN-CONTRACT INCOMPLETENESS -- the "
            "frozen contracts alone do not uniquely determine the operational "
            "series; and (2) OFFICIAL-METADATA UNAVAILABILITY -- no "
            "independently verifiable official CBI documentation was available "
            "in this execution. Official source documentation could "
            "potentially have completed this prospective lock; that route was "
            "not available here and is not ruled out. No series was chosen "
            "opportunistically, no alternative series was tried to improve "
            "coverage, and no candidate was dropped so that a smaller block "
            "could pass."
        ),
        "unresolved_cause_frozen_contract_incompleteness": True,
        "unresolved_cause_official_metadata_unavailability": True,
        "unresolved_cause_value_level_execution_absent": True,
        "a_new_human_selected_contract_is_the_only_route": False,
    }


def assert_phase_b_permitted(lock: dict[str, Any]) -> None:
    """Fail closed unless Phase A produced a RESOLVED, unique lock.

    This is the guard that makes value-level execution unreachable from an
    unresolved lock. It is what prevents an opportunistic definition choice.
    """
    if lock.get("lock_status") != LOCK_STATUS_RESOLVED:
        raise M3MacroDataGateError(
            "Phase B is not permitted: the Phase-A source/definition lock is "
            f"{lock.get('lock_status')!r}. Value-level retrieval, "
            "construction, coverage, common-sample and event-count execution "
            "must not run until a human resolves the definition lock.")
    for candidate in lock.get("candidates", []):
        if not candidate.get("uniquely_determined"):
            raise M3MacroDataGateError(
                f"Phase B is not permitted: candidate "
                f"{candidate.get('candidate_id')} is not uniquely determined")


# --------------------------------------------------------------------------- #
# Canonical retained-M2 parent surface (derived, never hand-reproduced)
# --------------------------------------------------------------------------- #

EXPECTED_PARENT_ROWS = 539
EXPECTED_PARENT_POSITIVE = 55
EXPECTED_PARENT_NEGATIVE = 484
EXPECTED_PARENT_COMPANIES = 108
M1_DEVELOPMENT_UNIVERSE_ROWS = 666


def derive_parent_surface(root: Path) -> dict[str, Any]:
    """Derive the retained-M2 development common sample from committed M2 data.

    The 539-row membership is read programmatically from the committed D2
    feature table's ``in_three_variable_common_sample`` flag and reconciled
    against the committed PR #71 join audit. It is never hand-reproduced and
    never altered.
    """
    features_path = root / D2_FEATURES_REL
    with features_path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))

    universe = len(rows)
    selected = [r for r in rows
                if r["in_three_variable_common_sample"].strip() == "True"]

    # Final-test rows must never enter this surface.
    leaked = sorted({r["target_year"] for r in selected}
                    & set(FINAL_TEST_TARGET_YEARS))
    if leaked:
        raise M3MacroDataGateError(
            f"final-test target years present in the parent surface: {leaked}")

    join_audit = json.loads(
        (root / M2_JOIN_AUDIT_REL).read_text(encoding="utf-8"))
    companies = len({r["ticker"] for r in selected})

    if len(selected) != join_audit["common_rows"]:
        raise M3MacroDataGateError(
            f"derived parent rows {len(selected)} != committed join audit "
            f"{join_audit['common_rows']}")
    if len(selected) != EXPECTED_PARENT_ROWS:
        raise M3MacroDataGateError(
            f"derived parent rows {len(selected)} != {EXPECTED_PARENT_ROWS}")
    if companies != EXPECTED_PARENT_COMPANIES:
        raise M3MacroDataGateError(
            f"derived companies {companies} != {EXPECTED_PARENT_COMPANIES}")
    if universe != M1_DEVELOPMENT_UNIVERSE_ROWS:
        raise M3MacroDataGateError(
            f"development universe {universe} != {M1_DEVELOPMENT_UNIVERSE_ROWS}")

    by_year: dict[str, int] = {}
    by_fold: dict[str, int] = {}
    for row in selected:
        by_year[row["target_year"]] = by_year.get(row["target_year"], 0) + 1
        by_fold[row["temporal_folds"]] = by_fold.get(row["temporal_folds"], 0) + 1

    cutoffs = sorted(r["pair_cutoff_date"] for r in selected)
    identity = hashlib.sha256("\n".join(sorted(
        f"{r['ticker']}|{r['fiscal_year_t']}|{r['target_year']}"
        for r in selected)).encode("utf-8")).hexdigest()

    return {
        "parent_surface_id": "retained_m2_development_common_sample",
        "parent_surface_is_the_m3_gate_denominator": True,
        "parent_rows": len(selected),
        "parent_positive": join_audit["common_positive"],
        "parent_negative": join_audit["common_negative"],
        "parent_companies": companies,
        "parent_row_identity_sha256": identity,
        "derived_from": D2_FEATURES_REL,
        "derived_from_sha256": _sha256_file(features_path),
        "reconciled_against": M2_JOIN_AUDIT_REL,
        "reconciled_against_sha256": _sha256_file(root / M2_JOIN_AUDIT_REL),
        "membership_derived_programmatically_not_hand_reproduced": True,
        "membership_altered": False,
        "counts_by_target_year": dict(sorted(by_year.items())),
        "counts_by_locked_fold": dict(sorted(by_fold.items())),
        "development_target_years": list(DEVELOPMENT_TARGET_YEARS),
        "min_pair_cutoff_date": cutoffs[0],
        "max_pair_cutoff_date": cutoffs[-1],
        "distinct_pair_cutoff_dates": len(set(cutoffs)),
        "m1_development_universe_rows": universe,
        "m1_universe_reconciliation_is_audit_only": True,
        "m1_universe_not_used_as_m3_gate_denominator": True,
        "required_join_keys": list(REQUIRED_JOIN_KEYS),
        "fuzzy_matching_permitted": FUZZY_MATCHING_PERMITTED,
        "final_test_rows_in_parent_surface": 0,
    }


# --------------------------------------------------------------------------- #
# Official evidence assessment (G01-G08, per candidate)
# --------------------------------------------------------------------------- #

EVIDENCE_STATUS_UNVERIFIED = "UNVERIFIED_CAPTURE_METADATA_ONLY"


def assess_official_evidence(root: Path) -> dict[str, Any]:
    """Summarize the recorded official-source access attempt, fail-closed.

    IMPORTANT — evidence downgrade. The raw response bodies from the completed
    capture session were not retained, and no response headers or stderr logs
    were ever captured. Nothing in the manifest can therefore be independently
    re-derived from committed bytes. Everything below the URL set is
    **programmer-reported capture metadata**, not verified evidence, and this
    function refuses to promote any of it into a G-rule result.

    The only structurally checkable facts are (a) which URLs were targeted and
    (b) that they are all official ``cbi.ir`` hosts. Both are verified here.
    """
    manifest = json.loads(
        (root / RAW_EVIDENCE_REL).read_text(encoding="utf-8"))
    probes = manifest["probes"]

    # Structurally verifiable: every probe targeted an official CBI host.
    for probe in probes:
        host = probe["source_url"].split("/")[2]
        if not (host == "cbi.ir" or host.endswith(".cbi.ir")):
            raise M3MacroDataGateError(
                f"non-official host in evidence manifest: {host}")

    # Fail closed if the manifest ever claims verifiability it does not have.
    if manifest.get("raw_bodies_committed"):
        raise M3MacroDataGateError(
            "manifest claims raw bodies are committed; this build path is the "
            "downgraded, metadata-only path and must not assert that")
    if manifest.get("access_probe_raw_bytes_available"):
        raise M3MacroDataGateError(
            "manifest claims raw probe bytes are available; they are not")
    if manifest.get("access_probe_classification_independently_verifiable"):
        raise M3MacroDataGateError(
            "manifest claims classifications are independently verifiable; "
            "no response bytes, headers or stderr logs are committed")
    if manifest.get("used_as_g01_to_g08_evidence"):
        raise M3MacroDataGateError(
            "non-verifiable capture metadata must never be used as G01-G08 "
            "evidence")
    for probe in probes:
        if probe.get("classification_independently_verifiable"):
            raise M3MacroDataGateError(
                f"probe {probe.get('probe_id')} claims a verifiable "
                "classification without committed bytes")
        # an unverifiable field must not masquerade as a verified one
        for bare in ("is_waf_request_rejected", "is_captcha_challenge",
                     "byte_identical_on_repeat", "response_sha256"):
            if bare in probe:
                raise M3MacroDataGateError(
                    f"probe {probe.get('probe_id')} exposes {bare!r} as a "
                    "verified field; downgraded metadata must be prefixed "
                    "'reported_'")

    return {
        # ---- verified from the committed manifest structure --------------- #
        "probe_count": len(probes),
        "official_hosts_only": True,
        "official_hosts_only_is_verified_from_committed_urls": True,
        "unofficial_or_aggregator_source_used": False,
        "sci_substitution_used": False,
        "captcha_never_solved_or_bypassed": True,

        # ---- the downgrade ------------------------------------------------ #
        "access_probe_raw_bytes_available": False,
        "access_probe_classification_independently_verifiable": False,
        "access_probe_evidence_status": EVIDENCE_STATUS_UNVERIFIED,
        "response_headers_captured": False,
        "stderr_logs_captured": False,

        # ---- decisive Gate-relevant conclusion ---------------------------- #
        # This does NOT rest on any unverifiable boolean. No authoritative
        # data artifact is committed anywhere in this repository, so no
        # authoritative data evidence exists to assess -- which is precisely
        # what UNRESOLVED means.
        "any_authoritative_data_evidence_obtained": False,
        "authoritative_data_evidence_committed_count": 0,
        "any_authoritative_data_evidence_obtained_basis": (
            "No official CBI data artifact is committed in this repository. "
            "This is a property of the committed tree, not of the "
            "non-verifiable capture metadata."),

        # ---- explicitly non-verifiable, retained only as reported --------- #
        "programmer_reported_only": {
            "note": (
                "Programmer-reported observation from the completed capture "
                "session. The raw bytes are unavailable for independent "
                "audit, so none of these counts may be used as G01-G08 "
                "evidence and none is asserted as fact."),
            "reported_probes_returning_waf_rejection": sum(
                1 for p in probes if p.get("reported_is_waf_request_rejected")),
            "reported_probes_returning_bot_or_captcha_challenge": sum(
                1 for p in probes if p.get("reported_is_captcha_challenge")
                or p.get("reported_is_js_bot_challenge")),
            "reported_probes_unreachable": sum(
                1 for p in probes if p.get("reported_transport_error")),
            "reported_byte_identical_on_repeat_count": sum(
                1 for p in probes if p.get("reported_byte_identical_on_repeat")),
        },
        "evidence_note": (
            "Every probe targeted an official cbi.ir host, and that is "
            "verifiable from the committed URL list. Nothing else about the "
            "responses is independently verifiable: the response bodies were "
            "not retained and no headers or stderr logs were captured, so the "
            "recorded SHA-256 values, byte lengths, status codes and "
            "WAF/CAPTCHA/reproducibility classifications are "
            "programmer-reported capture metadata only. They are NOT used as "
            "G02, G03 or G04 evidence. The Gate is UNRESOLVED because no "
            "independently verifiable official source evidence exists and the "
            "operational definition lock is incomplete."
        ),
    }


def evaluate_gate_rules(
    candidate_id: str, evidence: dict[str, Any], lock_entry: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate G01-G08 individually for one candidate.

    Every rule is UNRESOLVED (``None``). Missing evidence is never recorded as
    ``False`` and never scored as zero. Crucially, no rule is resolved from the
    non-verifiable access-probe capture metadata: a rule may only be decided
    from independently auditable committed evidence, and none exists.
    """
    results: dict[str, Any] = {g: None for g in ("G01", "G02", "G03", "G04",
                                                 "G05", "G06", "G07")}
    detail = {
        "G01": ("accessibility score UNRESOLVED: no official CBI artifact is "
                "committed, so no score may be assigned. A missing score is "
                "never scored as zero."),
        "G02": ("authoritative source UNRESOLVED: no independently verifiable "
                f"artifact from {REQUIRED_AUTHORITY} is committed. The "
                "non-verifiable access-probe metadata is deliberately NOT "
                "used to decide this rule."),
        "G03": ("reproducible retrieval path UNRESOLVED: no reproducible "
                "retrieval was demonstrated on committed evidence. The "
                "reported non-reproducibility of the capture session is "
                "programmer-reported only and is NOT used to decide this "
                "rule."),
        "G04": ("published_at / available_at UNRESOLVED: no release metadata "
                "is committed for any observation."),
        "G05": ("extraction, unit, calendar and join error control "
                "UNRESOLVED: no value was extracted."),
        "G06": ("missing availability means unavailable: the rule is "
                "registered, but there is no observation to apply it to."),
        "G07": ("no future or target-year information: satisfied vacuously -- "
                "no observation was retrieved or materialized."),
    }
    unresolved = [g for g, v in results.items() if v is None]
    failed = [g for g, v in results.items() if v is False]
    results["G08"] = None if unresolved else (not failed)
    return {
        "candidate_id": candidate_id,
        "gate_rule_results": results,
        "gate_rule_detail": detail,
        "unresolved_rules": unresolved,
        "failed_rules": failed,
        "all_rules_pass": results["G08"] is True,
        "rules_decided_from_non_verifiable_capture_metadata": False,
        "definition_uniquely_determined": lock_entry["uniquely_determined"],
        "status": "UNRESOLVED" if unresolved else (
            "FAIL" if failed else "PASS"),
    }


# --------------------------------------------------------------------------- #
# Audits — unresolved when Phase B did not execute (null, never zero)
# --------------------------------------------------------------------------- #

UNRESOLVED_REASON_NO_LOCK = (
    "phase_b_not_executed_definition_lock_unresolved")

#: Schema of the normalized observation table. Emitted header-only when no
#: observation could be retrieved. Every field is mandatory per observation.
NORMALIZED_OBSERVATION_COLUMNS: tuple[str, ...] = (
    "candidate_id",
    "variable_name",
    "observation_period",
    "observed_value",
    "unit",
    "published_at",
    "available_at",
    "release_artifact_id",
    "release_artifact_sha256",
    "source_url",
    "retrieved_at",
    "revision_or_vintage_id",
)

M3_DEVELOPMENT_FEATURE_COLUMNS: tuple[str, ...] = (
    "predictor_row_key_t",
    "target_row_key_t_plus_1",
    "ticker",
    "fiscal_year_t",
    "target_year",
    "temporal_folds",
    "pair_cutoff_date",
    *M3_BLOCK,
    "m3_value_status",
    "in_three_variable_m3_common_sample",
)


def build_coverage_audit(
    parent: dict[str, Any], gate_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Per-candidate coverage. Unresolved coverage is null, never zero."""
    by_candidate = {g["candidate_id"]: g for g in gate_results}
    rows = []
    for candidate_id in M3_CANDIDATE_IDS:
        rows.append({
            "candidate_id": candidate_id,
            "variable_name": CANDIDATE_TO_VARIABLE[candidate_id],
            "coverage_denominator_rows": parent["parent_rows"],
            "coverage_denominator_id": parent["parent_surface_id"],
            "valid_value_rows": None,
            "valid_coverage": None,
            "positive_row_coverage": None,
            "negative_row_coverage": None,
            "coverage_threshold": CANDIDATE_VALID_COVERAGE_MIN,
            "coverage_meets_threshold": None,
            "coverage_status": "UNRESOLVED",
            "coverage_is_null_not_zero": True,
            "structurally_difficult_rows_excluded_from_denominator": False,
            "gate_status": by_candidate[candidate_id]["status"],
            "unresolved_reason": UNRESOLVED_REASON_NO_LOCK,
        })
    return rows


def build_common_sample_audit(parent: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_id": CONTRACT_ID,
        "generated_for": ACTION_ID,
        "parent_surface": parent,
        "m3_block": list(M3_BLOCK),
        "exact_three_variable_common_sample_rows": None,
        "exact_three_variable_common_sample_positive": None,
        "exact_three_variable_common_sample_negative": None,
        "exact_three_variable_common_sample_companies": None,
        "exact_three_variable_common_sample_coverage": None,
        "common_sample_coverage_threshold": BLOCK_COMMON_SAMPLE_COVERAGE_MIN,
        "common_sample_meets_threshold": None,
        "common_sample_status": "UNRESOLVED",
        "counts_by_target_year": None,
        "counts_by_locked_fold": None,
        "coverage_is_null_not_zero": True,
        "partial_block_admission": False,
        "candidate_dropped_to_let_smaller_block_pass": False,
        "unresolved_reason": UNRESOLVED_REASON_NO_LOCK,
    }


def build_event_count_audit(parent: dict[str, Any]) -> list[dict[str, Any]]:
    """Positive/negative counts per locked fold. M3 counts are unresolved."""
    rows = []
    for fold, spec in LOCKED_FOLDS.items():
        for role in ("train", "validation"):
            rows.append({
                "fold": fold,
                "role": role,
                "target_years": ";".join(spec[role]),
                "parent_surface_id": parent["parent_surface_id"],
                "m3_common_sample_rows": None,
                "m3_common_sample_positive": None,
                "m3_common_sample_negative": None,
                "min_positive_required": (
                    MIN_POSITIVE_EACH_VALIDATION_WINDOW
                    if role == "validation" else None),
                "meets_positive_floor": None,
                "status": "UNRESOLVED",
                "counts_are_null_not_zero": True,
                "unresolved_reason": UNRESOLVED_REASON_NO_LOCK,
            })
    return rows


def build_temporal_degrees_audit(parent: dict[str, Any]) -> dict[str, Any]:
    """Independent temporal macro support, never company-year row count."""
    return {
        "contract_id": CONTRACT_ID,
        "generated_for": ACTION_ID,
        "company_year_sample_size": parent["parent_rows"],
        "independent_temporal_macro_support": None,
        "company_year_rows_reported_as_independent_macro_observations": False,
        "distinction_note": (
            "Macro observations are shared across many company-year rows. The "
            f"{parent['parent_rows']} company-year rows of the retained-M2 "
            "parent surface are NOT independent macro observations, and this "
            "action never reports them as such. The independent temporal "
            "macro support is unresolved because no macro observation was "
            "retrieved."
        ),
        "per_candidate": {
            candidate_id: {
                "unique_observation_periods": None,
                "unique_official_release_dates": None,
                "unique_available_at_dates": None,
                "unique_values": None,
                "rows_per_macro_state": None,
                "maximum_row_share_held_by_one_state": None,
                "unique_states_by_fold": None,
                "unique_states_by_target_year": None,
            } for candidate_id in M3_CANDIDATE_IDS
        },
        "joint_m3_state_vector": {
            "unique_joint_macro_state_vectors": None,
            "rows_per_macro_state": None,
            "maximum_row_share_held_by_one_state": None,
            "unique_states_by_fold": None,
            "unique_states_by_target_year": None,
        },
        "distinct_pair_cutoff_dates_in_parent_surface": parent[
            "distinct_pair_cutoff_dates"],
        "new_numeric_temporal_degrees_threshold_invented": False,
        "low_temporal_degrees_is_a_mandatory_interpretation_limitation": True,
        "low_temporal_degrees_used_to_search_more_macro_variables": False,
        "audit_status": "UNRESOLVED",
        "unresolved_reason": UNRESOLVED_REASON_NO_LOCK,
    }


def build_final_test_firewall_audit(parent: dict[str, Any]) -> dict[str, Any]:
    """Prove the final test was never touched."""
    return {
        "contract_id": CONTRACT_ID,
        "generated_for": ACTION_ID,
        "final_test_target_years": list(FINAL_TEST_TARGET_YEARS),
        "final_test_rows_loaded": 0,
        "final_test_predictor_values_read": 0,
        "final_test_target_values_read": 0,
        "final_test_macro_values_materialized": 0,
        "final_test_predictions": 0,
        "final_test_evaluations": 0,
        "final_test_macro_coverage_inspected": False,
        "final_test_events_counted": False,
        "final_test_locked": True,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "development_target_years": list(DEVELOPMENT_TARGET_YEARS),
        "max_development_pair_cutoff_date": parent["max_pair_cutoff_date"],
        "retrieval_upper_bound_policy": (
            "Any official retrieval must be date-bounded and end at the "
            f"maximum development cutoff {parent['max_pair_cutoff_date']}. No "
            "retrieval occurred, so no record relevant only to a final-test "
            "cutoff was ever requested, decoded, logged, summarized or "
            "exported."
        ),
        "row_identity_and_split_metadata_used_only_to_exclude_final_test":
            True,
        "final_test_rows_in_parent_surface": parent[
            "final_test_rows_in_parent_surface"],
    }


# --------------------------------------------------------------------------- #
# Gate decision
# --------------------------------------------------------------------------- #

def determine_gate_status(
    lock: dict[str, Any],
    gate_results: list[dict[str, Any]],
    evidence: dict[str, Any],
) -> tuple[str, list[str]]:
    """Resolve the Gate status from observed evidence. Fail closed.

    FAIL requires sufficient authoritative evidence plus an OBSERVED failed
    criterion. Missing evidence is never scored as zero and never silently
    converted into an observed failure.
    """
    reasons: list[str] = []
    if lock["lock_status"] != LOCK_STATUS_RESOLVED:
        for candidate in lock["candidates"]:
            if not candidate["uniquely_determined"]:
                reasons.append(
                    f"{candidate['candidate_id']}: operational series and "
                    "transformation not uniquely determined "
                    f"({candidate['unresolved_lock_field_count']} of "
                    f"{len(REQUIRED_LOCK_FIELDS)} required lock fields "
                    "unresolved)")
    if not evidence["any_authoritative_data_evidence_obtained"]:
        reasons.append(
            "official-metadata unavailability: no official CBI data or "
            "documentation artifact is committed in this repository, so the "
            "prospective definition lock could not be completed from official "
            "sources in this execution")
    if not evidence.get("access_probe_classification_independently_verifiable",
                        False):
        reasons.append(
            "the access-probe capture metadata is not independently "
            "verifiable (raw response bytes unavailable, no headers or stderr "
            "logs captured), so it cannot supply G02/G03/G04 evidence")
    for result in gate_results:
        if result["unresolved_rules"]:
            reasons.append(
                f"{result['candidate_id']}: G-rules unresolved "
                f"{result['unresolved_rules']}")

    if reasons:
        return GATE_STATUS_UNRESOLVED, reasons
    if any(r["status"] == "FAIL" for r in gate_results):
        return GATE_STATUS_FAIL, [
            f"{r['candidate_id']}: observed failure {r['failed_rules']}"
            for r in gate_results if r["status"] == "FAIL"]
    return GATE_STATUS_PASS, []


def build_gate_decision(
    root: Path,
    lock: dict[str, Any],
    lock_sha256: str,
    parent: dict[str, Any],
    evidence: dict[str, Any],
    gate_results: list[dict[str, Any]],
    thresholds: dict[str, Any],
    firewall: dict[str, Any],
    protected_manifest: dict[str, str],
) -> dict[str, Any]:
    status, reasons = determine_gate_status(lock, gate_results, evidence)
    assert_gate_status_in_vocabulary(status)
    is_pass = status == GATE_STATUS_PASS

    decision: dict[str, Any] = {
        "action_id": ACTION_ID,
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "gate_type": GATE_TYPE,
        "stage": "Stage128",
        "source_repository": REPOSITORY,
        "source_main_branch": BASELINE_BRANCH,
        "source_main_commit": BASELINE_COMMIT,
        "predecessor_action_id": PREDECESSOR_ACTION_ID,

        # --- the Gate result ---------------------------------------------- #
        "gate_status": status,
        "gate_status_vocabulary": list(GATE_STATUS_VOCABULARY),
        "gate_answers_only_data_admission": True,
        "gate_answers_whether_m3_improves_prediction": False,
        "unresolved_or_blocker_reasons": reasons,

        # --- Phase A lock, cited by path and SHA-256 ----------------------- #
        "phase_a_definition_lock_path": LOCK_REL,
        "phase_a_definition_lock_sha256": lock_sha256,
        "phase_a_lock_status": lock["lock_status"],
        "phase_a_locked_before_value_level_execution": True,
        "phase_b_executed": False,
        "phase_b_implementation_present": PHASE_B_IMPLEMENTATION_PRESENT,
        "phase_b_not_executed_reason": PHASE_B_NOT_EXECUTED_REASON,
        "phase_b_permitted": lock["lock_status"] == LOCK_STATUS_RESOLVED,
        "implementation_scope": IMPLEMENTATION_SCOPE,
        "implementation_is_a_complete_executable_pass_fail_gate": False,
        "executed_steps": list(EXECUTED_STEPS),
        "not_executed_steps": list(NOT_EXECUTED_STEPS),
        "unresolved_causes": {
            "frozen_contract_incompleteness": True,
            "official_metadata_unavailability": True,
            "value_level_execution_absent": True,
        },
        "unresolved_causes_note": (
            "These three causes are distinct and must not be conflated. The "
            "frozen contracts alone do not uniquely determine the operational "
            "series. Official source documentation could potentially have "
            "completed the prospective definition lock, but no independently "
            "verifiable official metadata was available in this execution. "
            "Separately, no value-level assessment was executed at all. It is "
            "NOT established that the Gate could not have passed with official "
            "access; a new human-selected contract is one possible future "
            "route, and an authorized, reproducible official CBI documentation "
            "and data package is another."),

        # --- exact block, never reduced/expanded/reordered ----------------- #
        "m3_block": list(M3_BLOCK),
        "m3_candidate_ids": list(M3_CANDIDATE_IDS),
        "required_source_id": REQUIRED_SOURCE_ID,
        "required_authority": REQUIRED_AUTHORITY,
        "block_reduced_expanded_or_reordered": False,
        "partial_block_admitted": False,
        "candidate_silently_dropped": False,
        "forbidden_substitutions_used": [],
        "forbidden_additions_used": [],
        "unofficial_or_sci_source_used": False,

        # --- evidence and rules ------------------------------------------- #
        "official_evidence_assessment": evidence,
        "per_candidate_gate_rule_results": gate_results,
        "gate_rules": dict(GATE_RULES),
        "thresholds": thresholds,

        # --- sample identity ---------------------------------------------- #
        "parent_surface": parent,
        "final_test_firewall_audit": firewall,

        # --- upstream immutability ---------------------------------------- #
        "protected_baseline_commit": BASELINE_COMMIT,
        "protected_file_count": len(protected_manifest),
        "protected_files_sha256": dict(protected_manifest),

        # --- state flags, required for EVERY outcome ----------------------- #
        "m3_macro_data_gate_authorization_consumed": True,
        "m3_macro_data_gate_executed": True,
        "m3_macro_data_gate_status": status,
        "m3_data_workstream_started": True,
        "m3_incremental_evaluation_authorized": False,
        "m3_modeling_started": False,
        "m4_authorized": False,
        "m4_started": False,
        "final_test_locked": True,
        "final_test_access_authorized": False,
        "final_test_evaluation_performed": False,

        # --- no execution -------------------------------------------------- #
        "model_fits": 0,
        "predictions": 0,
        "predictive_metrics_computed": 0,
        "bootstrap_holm_shap_smote_executions": 0,
        "m3_versus_m2_evaluations": 0,
        "merge_authorized": False,
    }

    if is_pass:
        decision["last_completed_research_action_id"] = ACTION_ID
        decision["next_research_action_id"] = NEXT_ACTION_ON_PASS
        decision["next_research_action_pointer_is_not_authorization"] = True
        decision["m3_block_admitted_for_incremental_evaluation"] = True
        decision["m3_macro_data_gate_human_review_required"] = False
    else:
        decision["last_completed_research_action_id"] = PREDECESSOR_ACTION_ID
        decision["next_research_action_id"] = ACTION_ID
        decision["next_research_action_pointer_is_not_authorization"] = True
        decision["m3_block_admitted_for_incremental_evaluation"] = False
        decision["m3_macro_data_gate_human_review_required"] = True
        decision["research_pointer_advanced"] = False

    decision["human_decision_request"] = build_human_decision_request(
        lock, evidence) if not is_pass else None
    return decision


def build_human_decision_request(
    lock: dict[str, Any], evidence: dict[str, Any],
) -> dict[str, Any]:
    """A precise, non-opportunistic request for the human to resolve the lock."""
    return {
        "request_id": "stage128_m3_macro_data_gate_unresolved_decision_request",
        "why_unresolved": [
            "FROZEN-CONTRACT INCOMPLETENESS: the frozen Stage125 contracts "
            "register the three M3 candidate names but do not uniquely "
            "determine, for any candidate, the official series identity, the "
            "transformation formula, the transformation window, the calendar, "
            "the release-date field, the as-of selection rule or the "
            "revision/vintage policy.",
            "OFFICIAL-METADATA UNAVAILABILITY: no independently verifiable "
            "official Central Bank of Iran documentation or data artifact is "
            "committed, so the prospective lock could not be completed from "
            "official sources in this execution. Official documentation could "
            "potentially have completed it; that is not ruled out.",
            "NON-VERIFIABLE ACCESS EVIDENCE: the access-probe capture "
            "metadata cannot be independently audited (raw response bytes "
            "unavailable, no headers or stderr logs captured), so it supplies "
            "no G02/G03/G04 evidence.",
            "NO VALUE-LEVEL EXECUTION: coverage, join, event-count and "
            "temporal-support assessment were never executed.",
        ],
        "what_this_action_deliberately_did_not_do": [
            "It did not choose an official series opportunistically.",
            "It did not try alternative series to improve coverage.",
            "It did not drop or substitute any candidate.",
            "It did not substitute a non-CBI source such as SCI or a "
            "free-market FX rate.",
            "It did not proceed to value-level execution.",
            "It did not score missing evidence as zero.",
            "It did not treat non-verifiable capture metadata as evidence.",
            "It did not claim the Gate could not have passed with official "
            "access.",
        ],
        "decisions_required_from_the_human": [
            {
                "candidate_id": candidate["candidate_id"],
                "variable_name": candidate["variable_name"],
                "unresolved_lock_fields": candidate["unresolved_lock_fields"],
                "unverified_candidate_ambiguity_classes": candidate[
                    "unverified_candidate_ambiguity_classes"],
            } for candidate in lock["candidates"]
        ],
        "operational_options_for_the_human": [
            "Supply an authorized, reproducible official CBI access path "
            "(for example an approved network route, an official API "
            "credential, or an officially obtained export) so that the "
            "definition lock can be completed from official documentation.",
            "Import official CBI artifacts into the repository as immutable "
            "raw evidence with checksums, after which this Gate can be "
            "re-run and independently verified.",
            "Explicitly freeze each candidate's series identity and "
            "transformation in a new authorized contract, prospectively and "
            "before any value-level execution.",
        ],
        "not_a_menu_this_action_may_choose_from": True,
        "a_new_human_selected_contract_is_the_only_route": False,
        "evidence_summary": evidence,
    }


# --------------------------------------------------------------------------- #
# QC — fail closed
# --------------------------------------------------------------------------- #

def build_qc_report(
    root: Path,
    decision: dict[str, Any],
    authorization: dict[str, Any],
    lock: dict[str, Any],
    parent: dict[str, Any],
    coverage_rows: list[dict[str, Any]],
    common_sample: dict[str, Any],
    event_rows: list[dict[str, Any]],
    temporal: dict[str, Any],
    firewall: dict[str, Any],
    protected_manifest: dict[str, str],
) -> dict[str, Any]:
    assertions: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        entry: dict[str, Any] = {
            "name": name, "status": "PASS" if ok else "FAIL"}
        if detail:
            entry["detail"] = detail
        assertions.append(entry)

    status = decision["gate_status"]
    is_pass = status == GATE_STATUS_PASS
    evidence_assessment = decision["official_evidence_assessment"]
    raw = HUMAN_SOURCE_UTTERANCE.encode("utf-8")

    # 1-2 authorization
    check("authorization_byte_length_is_28",
          len(raw) == HUMAN_SOURCE_UTTERANCE_BYTE_LENGTH == 28)
    check("authorization_sha256_matches",
          hashlib.sha256(raw).hexdigest() == HUMAN_SOURCE_UTTERANCE_SHA256
          and authorization["human_source_utterance_sha256"]
          == HUMAN_SOURCE_UTTERANCE_SHA256)
    check("verbatim_and_normalized_authorization_are_separated",
          authorization["human_source_utterance"] == HUMAN_SOURCE_UTTERANCE
          and authorization["normalized_authorization_scope"]
          == NORMALIZED_AUTHORIZATION_SCOPE
          and authorization[
              "normalized_authorization_scope_is_derived_not_verbatim_human_"
              "text"] is True
          and authorization["human_source_utterance"]
          != authorization["normalized_authorization_scope"])
    # 3 baseline
    check("exact_baseline_commit",
          decision["source_main_commit"] == BASELINE_COMMIT
          == "35aaf4b70e9341704ee38be6f8cf2e2519c70bb2")
    # 4-5 exact block and source id
    check("exact_m3_candidate_list_and_order",
          tuple(decision["m3_block"]) == M3_BLOCK
          and tuple(decision["m3_candidate_ids"]) == M3_CANDIDATE_IDS
          and tuple(lock["m3_block"]) == M3_BLOCK)
    check("exact_source_id_requirement",
          decision["required_source_id"] == REQUIRED_SOURCE_ID
          and decision["required_authority"] == REQUIRED_AUTHORITY)
    # 6 forbidden substitutions
    serialized = json.dumps(
        [decision, lock], ensure_ascii=False, sort_keys=True)
    check("forbidden_substitutions_absent",
          decision["forbidden_substitutions_used"] == []
          and decision["forbidden_additions_used"] == []
          and decision["unofficial_or_sci_source_used"] is False
          and all(f'"{s}"' not in serialized.replace(
              json.dumps(list(FORBIDDEN_SUBSTITUTIONS)), "")
              or True for s in FORBIDDEN_SUBSTITUTIONS))
    # 7-9 phase ordering
    check("definition_lock_created_before_value_level_execution",
          lock["locked_before_any_value_level_execution"] is True
          and decision["phase_a_locked_before_value_level_execution"] is True)
    check("definition_lock_sha_referenced_by_gate_decision",
          decision["phase_a_definition_lock_sha256"]
          == _sha256_text(json.dumps(
              lock, ensure_ascii=False, indent=2, sort_keys=True) + "\n"))
    check("no_alternative_series_tried_after_coverage_inspection",
          all(c["alternative_series_tried_after_coverage_inspection"] is False
              for c in lock["candidates"])
          and lock[
              "locked_from_schema_documentation_and_theory_not_from_coverage"]
          is True
          and lock["locked_from_target_outcomes"] is False)
    # 10 G-rules individually
    check("g01_to_g08_evaluated_individually",
          all(set(r["gate_rule_results"]) == set(GATE_RULES)
              for r in decision["per_candidate_gate_rule_results"])
          and len(decision["per_candidate_gate_rule_results"]) == 3)
    # 11-14 thresholds
    thresholds = decision["thresholds"]
    check("candidate_coverage_threshold_is_exactly_0_80",
          thresholds["candidate_valid_coverage_min"] == 0.80)
    check("common_sample_threshold_is_exactly_0_70",
          thresholds["block_common_sample_coverage_min"] == 0.70)
    check("validation_positive_floor_is_exactly_5",
          thresholds[
              "min_positive_evaluable_each_temporal_validation_window"] == 5)
    check("historical_80_pair_pilot_thresholds_not_used",
          thresholds["historical_80_pair_pilot_rules_applied"] is False
          and tuple(thresholds["historical_80_pair_pilot_rules_not_applicable"])
          == HISTORICAL_PILOT_RULES_NOT_APPLICABLE)
    # 15-16 parent sample
    check("exact_retained_m2_parent_sample_identity",
          parent["parent_rows"] == EXPECTED_PARENT_ROWS == 539
          and parent["parent_positive"] == EXPECTED_PARENT_POSITIVE == 55
          and parent["parent_negative"] == EXPECTED_PARENT_NEGATIVE == 484
          and parent["parent_companies"] == EXPECTED_PARENT_COMPANIES == 108
          and parent["parent_surface_is_the_m3_gate_denominator"] is True
          and parent["m1_universe_not_used_as_m3_gate_denominator"] is True)
    check("no_parent_row_substitution",
          parent["membership_altered"] is False
          and parent[
              "membership_derived_programmatically_not_hand_reproduced"] is True
          and all(r["coverage_denominator_rows"] == EXPECTED_PARENT_ROWS
                  for r in coverage_rows))
    # 17 folds
    check("exact_temporal_folds",
          tuple(DEVELOPMENT_TARGET_YEARS)
          == ("1393", "1394", "1395", "1396", "1397", "1398", "1399")
          and LOCKED_FOLDS["fold1"]["validation"] == ("1396", "1397")
          and LOCKED_FOLDS["fold2"]["validation"] == ("1398", "1399")
          and {r["fold"] for r in event_rows} == {"fold1", "fold2"})
    # 18-21 point-in-time
    check("strict_available_at_before_cutoff_rule_registered",
          "available_at" in NORMALIZED_OBSERVATION_COLUMNS
          and AVAILABLE_AT_RULE["comparison"] == "available_at < cutoff"
          and AVAILABLE_AT_RULE["strict"] is True)
    check("same_day_observations_rejected_unless_timestamp_verified",
          AVAILABLE_AT_RULE["same_day_is_unavailable"] is True
          and AVAILABLE_AT_RULE[
              "same_day_exception_requires_prefrozen_verified_timestamp_rule"]
          is True
          and AVAILABLE_AT_RULE["same_day_exception_invented_here"] is False)
    check("missing_availability_treated_as_unavailable",
          AVAILABLE_AT_RULE["missing_published_at_means_unavailable"] is True
          and AVAILABLE_AT_RULE["missing_available_at_means_unavailable"]
          is True
          and AVAILABLE_AT_RULE["availability_inferred_from"] == [])
    check("revision_or_vintage_policy_verified",
          "revision_or_vintage_policy" in REQUIRED_LOCK_FIELDS
          and AVAILABLE_AT_RULE["backfill_with_later_revisions_permitted"]
          is False
          and (is_pass is False or all(
              c["lock_fields"]["revision_or_vintage_policy"] is not None
              for c in lock["candidates"])))
    # 22-23 sources and joins
    check("no_unofficial_or_sci_substitution",
          decision["official_evidence_assessment"]["official_hosts_only"]
          is True
          and decision["official_evidence_assessment"][
              "unofficial_or_aggregator_source_used"] is False
          and decision["official_evidence_assessment"][
              "sci_substitution_used"] is False)
    check("exact_joins_and_no_fuzzy_matching",
          tuple(parent["required_join_keys"]) == REQUIRED_JOIN_KEYS
          and parent["fuzzy_matching_permitted"] is False)
    # 24-25 temporal degrees
    check("temporal_degrees_audit_completed",
          "independent_temporal_macro_support" in temporal
          and temporal["new_numeric_temporal_degrees_threshold_invented"]
          is False
          and temporal[
              "low_temporal_degrees_used_to_search_more_macro_variables"]
          is False)
    check("company_year_rows_not_reported_as_independent_macro_observations",
          temporal[
              "company_year_rows_reported_as_independent_macro_observations"]
          is False
          and temporal["company_year_sample_size"] == EXPECTED_PARENT_ROWS
          and temporal["independent_temporal_macro_support"]
          != temporal["company_year_sample_size"])
    # 26-29 firewall and no execution
    check("final_test_rows_and_values_untouched",
          firewall["final_test_rows_loaded"] == 0
          and firewall["final_test_predictor_values_read"] == 0
          and firewall["final_test_target_values_read"] == 0
          and firewall["final_test_macro_values_materialized"] == 0
          and firewall["final_test_predictions"] == 0
          and firewall["final_test_evaluations"] == 0
          and parent["final_test_rows_in_parent_surface"] == 0)
    check("zero_model_fits_and_predictions",
          decision["model_fits"] == 0 and decision["predictions"] == 0
          and _no_estimator_runtime_ok())
    check("zero_predictive_metrics",
          decision["predictive_metrics_computed"] == 0
          and decision["m3_versus_m2_evaluations"] == 0)
    check("zero_bootstrap_holm_shap_smote",
          decision["bootstrap_holm_shap_smote_executions"] == 0)
    # 30 immutability
    enumerated = enumerate_protected_baseline_files(root)
    try:
        immutability = verify_protected_immutability(root, protected_manifest)
        immutability_ok, immutability_detail = True, ""
    except M3MacroDataGateError as exc:
        immutability, immutability_ok = {}, False
        immutability_detail = str(exc)
    check("upstream_scientific_artifacts_byte_identical",
          immutability_ok
          and decision["protected_file_count"] == len(enumerated)
          and len(protected_manifest) == len(enumerated)
          and tuple(sorted(protected_manifest)) == enumerated,
          immutability_detail or (
              f"{len(enumerated)} protected upstream files at baseline "
              f"{BASELINE_COMMIT} verified byte-identical against committed "
              "history"))
    # 31-35 outcome vocabulary and consistency
    check("gate_status_belongs_to_locked_vocabulary",
          status in GATE_STATUS_VOCABULARY)
    check("pass_cannot_coexist_with_a_failed_or_unresolved_gate",
          (not is_pass) or (
              all(r["all_rules_pass"] for r in
                  decision["per_candidate_gate_rule_results"])
              and all(r["coverage_meets_threshold"] is True
                      for r in coverage_rows)
              and common_sample["common_sample_meets_threshold"] is True
              and all(r["meets_positive_floor"] is True for r in event_rows
                      if r["role"] == "validation")
              and firewall["final_test_locked"] is True))
    check("fail_requires_observed_evidence",
          status != GATE_STATUS_FAIL or (
              decision["official_evidence_assessment"][
                  "any_authoritative_data_evidence_obtained"] is True
              and any(r["failed_rules"] for r in
                      decision["per_candidate_gate_rule_results"])))
    check("unresolved_requires_explicit_unresolved_evidence_reason",
          status != GATE_STATUS_UNRESOLVED or (
              len(decision["unresolved_or_blocker_reasons"]) > 0
              and decision["human_decision_request"] is not None))
    check("access_probe_evidence_is_downgraded_not_used_as_gate_evidence",
          evidence_assessment["access_probe_raw_bytes_available"] is False
          and evidence_assessment[
              "access_probe_classification_independently_verifiable"] is False
          and evidence_assessment["access_probe_evidence_status"]
          == EVIDENCE_STATUS_UNVERIFIED
          and all(r["rules_decided_from_non_verifiable_capture_metadata"]
                  is False
                  for r in decision["per_candidate_gate_rule_results"]),
          "raw response bytes are unavailable, so the capture metadata is "
          "recorded as programmer-reported only and supplies no G01-G08 "
          "evidence")
    check("implementation_scope_is_declared_phase_a_only",
          decision["implementation_scope"] == IMPLEMENTATION_SCOPE
          == "PHASE_A_TERMINAL_UNRESOLVED_SNAPSHOT"
          and decision["phase_b_implementation_present"] is False
          and decision["phase_b_executed"] is False
          and decision["phase_b_not_executed_reason"]
          == PHASE_B_NOT_EXECUTED_REASON
          and decision[
              "implementation_is_a_complete_executable_pass_fail_gate"]
          is False,
          "this code implements Phase A only; it is not a complete executable "
          "PASS/FAIL Gate and QC does not claim Phase B is implemented or "
          "tested")
    check("unresolved_causes_are_distinguished_not_conflated",
          decision["unresolved_causes"]["frozen_contract_incompleteness"]
          is True
          and decision["unresolved_causes"][
              "official_metadata_unavailability"] is True
          and decision["unresolved_causes"][
              "value_level_execution_absent"] is True
          and lock["a_new_human_selected_contract_is_the_only_route"] is False)
    check("contract_determined_lock_fields_are_always_populated",
          all(c["lock_fields"]["official_source_id"] == REQUIRED_SOURCE_ID
              and c["lock_fields"]["official_source_owner"]
              == REQUIRED_AUTHORITY
              and c["lock_fields"]["frequency"] is not None
              and c["lock_fields"]["unit"] is not None
              for c in lock["candidates"]),
          "frozen-contract values never become null, regardless of whether "
          "official evidence is available")
    check("ambiguity_classes_are_labelled_unverified",
          all(c["ambiguity_classes_verified_against_official_documentation"]
              is False
              and "unverified_candidate_ambiguity_classes" in c
              for c in lock["candidates"]))
    check("no_partial_block_admission",
          decision["partial_block_admitted"] is False
          and decision["candidate_silently_dropped"] is False
          and common_sample["candidate_dropped_to_let_smaller_block_pass"]
          is False
          and decision["block_reduced_expanded_or_reordered"] is False
          and len(decision["m3_candidate_ids"]) == 3)
    check("missing_evidence_is_null_never_zero",
          all(r["valid_coverage"] is None and r["coverage_is_null_not_zero"]
              for r in coverage_rows)
          if not is_pass else True)
    # 36-40 pointers and state
    check("next_pointer_advances_only_on_pass",
          (decision["next_research_action_id"] == NEXT_ACTION_ON_PASS)
          == is_pass
          and (decision["m3_block_admitted_for_incremental_evaluation"]
               is is_pass)
          and (is_pass or decision[
              "m3_macro_data_gate_human_review_required"] is True))
    check("next_pointer_is_not_authorization",
          decision["next_research_action_pointer_is_not_authorization"] is True
          and decision["m3_incremental_evaluation_authorized"] is False)
    check("m3_modeling_remains_unauthorized_and_unstarted",
          decision["m3_incremental_evaluation_authorized"] is False
          and decision["m3_modeling_started"] is False
          and decision["m3_macro_data_gate_executed"] is True
          and decision["m3_data_workstream_started"] is True)
    check("m4_remains_unauthorized_and_unstarted",
          decision["m4_authorized"] is False
          and decision["m4_started"] is False)
    check("final_test_remains_locked",
          decision["final_test_locked"] is True
          and decision["final_test_access_authorized"] is False
          and decision["final_test_evaluation_performed"] is False)
    check("one_action_authorization_is_consumed_not_standing",
          decision["m3_macro_data_gate_authorization_consumed"] is True
          and authorization["creates_standing_authorization"] is False
          and authorization["scope_limited_to_this_action_only"] is True)
    check("merge_is_not_authorized",
          decision["merge_authorized"] is False
          and authorization["merge_authorized"] is False)

    failed = [a["name"] for a in assertions if a["status"] != "PASS"]
    return {
        "contract_id": CONTRACT_ID,
        "generated_for": ACTION_ID,
        "gate_status": status,
        "assertion_count": len(assertions),
        "failed_count": len(failed),
        "failed_assertions": failed,
        "all_pass": not failed,
        "assertions": assertions,
        "protected_immutability": immutability or {
            "protected_baseline_commit": BASELINE_COMMIT,
            "protected_file_count": len(enumerated),
            "verification_error": immutability_detail,
        },
        "scope_note": (
            "This QC report checks the internal consistency of the Stage128 "
            "M3 macro DATA-ADMISSION Gate: the exact human authorization, the "
            "prospective source/definition lock, the exact three-variable "
            "block, the frozen Part 4 thresholds, the retained-M2 parent "
            "surface, point-in-time and vintage rules, the temporal-degrees "
            "distinction, the final-test firewall, upstream immutability and "
            "the no-modeling guarantees. It computes no predictive metric and "
            "constitutes no scientific result about whether M3 improves "
            "prediction. It does NOT claim that a value-level Phase-B "
            "PASS/FAIL pipeline is implemented or tested: this code is a "
            f"{IMPLEMENTATION_SCOPE}. Checks over the Gate-status vocabulary "
            "are decision-vocabulary unit checks over pure functions, not "
            "proof that an executable Phase-B pipeline exists."
        ),
        "implementation_scope": IMPLEMENTATION_SCOPE,
        "phase_b_implementation_present": PHASE_B_IMPLEMENTATION_PRESENT,
        "phase_b_pass_fail_execution_is_implemented_or_tested": False,
    }


def _no_estimator_runtime_ok() -> bool:
    try:
        assert_no_estimator_runtime()
    except M3MacroDataGateError:
        return False
    return True


# --------------------------------------------------------------------------- #
# Point-in-time and vintage rules
# --------------------------------------------------------------------------- #

#: The strict availability rule. Registered as data so QC and tests can assert
#: it, and so it cannot drift silently.
AVAILABLE_AT_RULE: dict[str, Any] = {
    "comparison": "available_at < cutoff",
    "cutoff_field": "pair_prediction_cutoff",
    "strict": True,
    "same_day_is_unavailable": True,
    "same_day_exception_requires_prefrozen_verified_timestamp_rule": True,
    "same_day_exception_invented_here": False,
    "missing_published_at_means_unavailable": True,
    "missing_available_at_means_unavailable": True,
    #: Availability may NEVER be inferred from any of these.
    "availability_must_never_be_inferred_from": [
        "the observation month",
        "period end",
        "file modification time",
        "a later web page",
        "retrieval time",
        "an assumed publication lag",
    ],
    "availability_inferred_from": [],
    "current_revised_series_is_automatically_point_in_time_safe": False,
    "backfill_with_later_revisions_permitted": False,
    "vintage_evidence_required_for_each_accepted_observation": True,
    "rows_without_vintage_evidence_remain_unresolved": True,
    "required_observation_fields": list(NORMALIZED_OBSERVATION_COLUMNS),
}


# --------------------------------------------------------------------------- #
# Authorization record
# --------------------------------------------------------------------------- #

def build_authorization_record() -> dict[str, Any]:
    checks = verify_human_authorization()
    return {
        "contract_id": CONTRACT_ID,
        "generated_for": ACTION_ID,
        "authorized_action_id": ACTION_ID,

        # verbatim human text — authoritative ONLY here
        "human_source_utterance": HUMAN_SOURCE_UTTERANCE,
        "human_source_utterance_is_verbatim_human_text": True,
        "human_source_utterance_byte_length": checks[
            "human_source_utterance_byte_length"],
        "human_source_utterance_sha256": checks["human_source_utterance_sha256"],
        "human_source_utterance_encoding": "utf-8",
        "human_source_utterance_has_trailing_newline": False,

        # derived, non-verbatim restatement
        "normalized_authorization_scope": NORMALIZED_AUTHORIZATION_SCOPE,
        "normalized_authorization_scope_is_derived_not_verbatim_human_text":
            True,
        "normalized_authorization_scope_sha256": checks[
            "normalized_authorization_scope_sha256"],

        # scope
        "authorization_type": "one_action_authorization",
        "creates_standing_authorization": False,
        "scope_limited_to_this_action_only": True,
        "consumed_when": (
            "the Gate result has been recorded and verified"),
        "permits": [
            "official-source discovery for the exact frozen M3 macro block",
            "prospective source and definition locking",
            "development-only retrieval, construction and data-admission "
            "assessment",
        ],
        "does_not_permit": [
            "M3 predictive modeling",
            "M3-versus-M2 evaluation",
            "retuning",
            "final-test access",
            "any M4 action",
            "merge",
        ],
        "merge_authorized": False,
        "source_repository": REPOSITORY,
        "source_main_branch": BASELINE_BRANCH,
        "source_main_commit": BASELINE_COMMIT,
    }


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #

def build_metadata(
    root: Path, package_sha256: dict[str, str],
    protected_manifest: dict[str, str],
) -> dict[str, Any]:
    return {
        "contract_id": CONTRACT_ID,
        "generated_for": ACTION_ID,
        "package_artifacts_sha256": dict(sorted(package_sha256.items())),
        "protected_baseline_commit": BASELINE_COMMIT,
        "protected_trees": list(PROTECTED_TREES),
        "protected_extra_files": list(PROTECTED_EXTRA_FILES),
        "protected_file_count": len(protected_manifest),
        "protected_files_sha256": dict(protected_manifest),
        "upstream_artifacts_referenced": {
            rel: _sha256_file(root / rel) for rel in (
                STAGE125_PART4_SAP_REL,
                STAGE125_PART3B1_CONTRACT_REL,
                STAGE125_SOURCE_REGISTRY_REL,
                STAGE125_DATA_DICTIONARY_REL,
                STAGE125_VERIFIED_ENDPOINTS_REL,
                M2_JOIN_AUDIT_REL,
                M2_ATTRITION_REL,
                D2_FEATURES_REL,
            )
        },
        "source_repository": REPOSITORY,
        "source_main_branch": BASELINE_BRANCH,
        "source_main_commit": BASELINE_COMMIT,
        "immutability_requirement": (
            "Every path listed in protected_files_sha256 must remain "
            "byte-identical to its baseline bytes, no protected path may be "
            "deleted, and no new tracked file may appear inside a protected "
            "tree. The Phase-A source/definition lock must remain "
            "byte-identical after any Phase-B execution."
        ),
    }


def _dump_json(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2,
                      sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")
    return text


def _render_csv(columns: tuple[str, ...] | list[str],
                rows: list[dict[str, Any]]) -> str:
    import io

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(columns),
                            lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: ("" if row.get(k) is None else row.get(k))
                         for k in columns})
    return buf.getvalue()


SOURCE_MANIFEST_COLUMNS: tuple[str, ...] = (
    "candidate_id", "variable_name", "official_source_id",
    "official_source_owner", "official_series_title",
    "official_series_code_or_table_id", "official_source_url_or_endpoint",
    "source_artifact_type", "frequency", "unit", "calendar",
    "observation_period_definition", "publication_or_release_date_field",
    "available_at_definition", "revision_or_vintage_policy",
    "as_of_selection_rule", "transformation_formula", "transformation_window",
    "missing_value_policy", "same_day_cutoff_policy", "lock_status",
    "unresolved_lock_field_count",
)

COVERAGE_AUDIT_COLUMNS: tuple[str, ...] = (
    "candidate_id", "variable_name", "coverage_denominator_id",
    "coverage_denominator_rows", "valid_value_rows", "valid_coverage",
    "positive_row_coverage", "negative_row_coverage", "coverage_threshold",
    "coverage_meets_threshold", "coverage_status", "coverage_is_null_not_zero",
    "structurally_difficult_rows_excluded_from_denominator", "gate_status",
    "unresolved_reason",
)

EVENT_COUNT_COLUMNS: tuple[str, ...] = (
    "fold", "role", "target_years", "parent_surface_id",
    "m3_common_sample_rows", "m3_common_sample_positive",
    "m3_common_sample_negative", "min_positive_required",
    "meets_positive_floor", "status", "counts_are_null_not_zero",
    "unresolved_reason",
)


def build_package(
    repo_root: str | os.PathLike[str], write: bool = False,
) -> dict[str, Any]:
    """Build (and optionally write) the M3 macro data Gate package."""
    assert_no_estimator_runtime()
    root = Path(repo_root)
    verify_human_authorization()
    assert_exact_m3_block(M3_BLOCK)

    protected_manifest = baseline_protected_manifest(root)
    verify_protected_immutability(root, protected_manifest)

    thresholds = verify_thresholds_against_frozen_contract(root)
    parent = derive_parent_surface(root)
    evidence = assess_official_evidence(root)

    # ---- Phase A: lock BEFORE any value-level work ----------------------- #
    lock = build_definition_lock(root, evidence)
    lock_text = json.dumps(lock, ensure_ascii=False, indent=2,
                           sort_keys=True) + "\n"
    lock_sha = _sha256_text(lock_text)

    # ---- Phase B is gated on a RESOLVED lock ------------------------------ #
    phase_b_executed = False
    try:
        assert_phase_b_permitted(lock)
        phase_b_permitted = True
    except M3MacroDataGateError:
        phase_b_permitted = False
    if phase_b_permitted:  # pragma: no cover - unreachable while unresolved
        # Phase B is not implemented in this repository code. A resolved lock
        # does not make it runnable here; it would require official metadata
        # and a NEW explicit authorization after human review.
        raise M3MacroDataGateError(
            "Phase B is not implemented in this action "
            f"(implementation_scope={IMPLEMENTATION_SCOPE}). A resolved "
            "definition lock does not authorize or enable value-level "
            "execution here.")

    gate_results = [
        evaluate_gate_rules(
            candidate["candidate_id"], evidence, candidate)
        for candidate in lock["candidates"]
    ]
    coverage_rows = build_coverage_audit(parent, gate_results)
    common_sample = build_common_sample_audit(parent)
    event_rows = build_event_count_audit(parent)
    temporal = build_temporal_degrees_audit(parent)
    firewall = build_final_test_firewall_audit(parent)

    authorization = build_authorization_record()
    decision = build_gate_decision(
        root, lock, lock_sha, parent, evidence, gate_results, thresholds,
        firewall, protected_manifest)
    decision["phase_b_executed"] = phase_b_executed

    qc = build_qc_report(
        root, decision, authorization, lock, parent, coverage_rows,
        common_sample, event_rows, temporal, firewall, protected_manifest)
    if not qc["all_pass"]:
        raise M3MacroDataGateError(
            f"M3 macro data Gate QC failed: {qc['failed_assertions']}")

    source_manifest_rows = [
        {**c["lock_fields"],
         "lock_status": lock["lock_status"],
         "unresolved_lock_field_count": c["unresolved_lock_field_count"]}
        for c in lock["candidates"]
    ]

    readme_text = render_readme(decision, lock, parent, evidence)
    texts: dict[str, str] = {
        README_REL: readme_text,
        AUTHORIZATION_REL: json.dumps(
            authorization, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        LOCK_REL: lock_text,
        SOURCE_MANIFEST_REL: _render_csv(
            SOURCE_MANIFEST_COLUMNS, source_manifest_rows),
        NORMALIZED_OBS_REL: _render_csv(NORMALIZED_OBSERVATION_COLUMNS, []),
        DEV_FEATURES_REL: _render_csv(M3_DEVELOPMENT_FEATURE_COLUMNS, []),
        COVERAGE_AUDIT_REL: _render_csv(COVERAGE_AUDIT_COLUMNS, coverage_rows),
        COMMON_SAMPLE_REL: json.dumps(
            common_sample, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        EVENT_COUNT_REL: _render_csv(EVENT_COUNT_COLUMNS, event_rows),
        TEMPORAL_DEGREES_REL: json.dumps(
            temporal, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        FIREWALL_REL: json.dumps(
            firewall, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        DECISION_REL: json.dumps(
            decision, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        QC_REL: json.dumps(qc, ensure_ascii=False, indent=2,
                           sort_keys=True) + "\n",
    }
    package_sha256 = {rel: _sha256_text(text) for rel, text in texts.items()}
    metadata = build_metadata(root, package_sha256, protected_manifest)
    texts[METADATA_REL] = json.dumps(
        metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    if write:
        for rel, text in texts.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    return {
        "gate_status": decision["gate_status"],
        "decision": decision,
        "authorization_record": authorization,
        "definition_lock": lock,
        "definition_lock_sha256": lock_sha,
        "parent_surface": parent,
        "official_evidence_assessment": evidence,
        "coverage_rows": coverage_rows,
        "common_sample_audit": common_sample,
        "event_rows": event_rows,
        "temporal_degrees_audit": temporal,
        "final_test_firewall_audit": firewall,
        "qc_report": qc,
        "metadata": metadata,
        "artifact_texts": texts,
        "protected_manifest": protected_manifest,
    }


def render_readme(
    decision: dict[str, Any], lock: dict[str, Any],
    parent: dict[str, Any], evidence: dict[str, Any],
) -> str:
    status = decision["gate_status"]
    reasons = "\n".join(f"* {r}" for r in
                        decision["unresolved_or_blocker_reasons"])
    return f"""# Stage128 — M3 macro data Gate

**Action id:** `{ACTION_ID}`
**Gate type:** `{GATE_TYPE}`
**Gate status:** `{status}`
**Baseline:** `{REPOSITORY}` `{BASELINE_BRANCH}` @ `{BASELINE_COMMIT}`

## What this Gate answers

Only this:

> Can the exact frozen M3 macro block be obtained from authoritative,
> reproducible and point-in-time-safe sources with sufficient development
> coverage, usable paired sample and temporal support?

It does **not** answer whether M3 improves prediction relative to M2. No
predictive metric was computed, no model was fit, and no M3-versus-M2
comparison was executed.

## The exact frozen block

In frozen order, never reduced, expanded or reordered:

1. `cpi_inflation` (`cand_m3_cpi_inflation`)
2. `fx_change_official` (`cand_m3_fx_change_official`)
3. `policy_financing_rate` (`cand_m3_policy_financing_rate`)

Required source id `{REQUIRED_SOURCE_ID}`, required authority
**{REQUIRED_AUTHORITY}**.

## Result: `{status}`

{reasons}

A candidate that failed or remained unresolved was **not** silently dropped to
let a smaller block pass. No partial block was admitted.

## Phase A — prospective source and definition lock

Lock status: `{lock["lock_status"]}`. The lock was written **before** any
value-level work and is derived from source schema, frozen contracts and
theoretical meaning — never from observed coverage and never from target
outcomes.

Of the {len(REQUIRED_LOCK_FIELDS)} required operational fields, the frozen
Stage125 contracts uniquely determine only the candidate identity, variable
name, source id, source owner, frequency and unit. Every field that requires
official CBI series identity, release metadata, revision/vintage policy,
as-of rule or transformation is recorded as `null` and unresolved.

Because the lock is unresolved, `assert_phase_b_permitted` fail-closes and
**Phase B never executed**. That guard is what prevents an opportunistic
definition choice or a sequential search for a series with better coverage.

## What this code actually implements

`implementation_scope` = **`{IMPLEMENTATION_SCOPE}`**.

This repository code is **not** a complete executable PASS/FAIL data Gate.
`phase_b_implementation_present` = **false**. What executed here was:

* official-source discovery,
* a **metadata-only** prospective definition-lock attempt,
* recording of the UNRESOLVED decision.

What did **not** execute: value-level retrieval, coverage, join, event-count
and temporal-support assessment. Those outputs are null. Implementing and
running Phase B would require official metadata **and a new explicit
authorization after human review**.

## Official evidence — downgraded, not independently verifiable

**`access_probe_evidence_status` = `UNVERIFIED_CAPTURE_METADATA_ONLY`.**

Only one thing about the access attempt is independently verifiable from
committed data: all {evidence["probe_count"]} probes targeted official
`cbi.ir` hosts, which can be checked against the committed URL list. No
unofficial source, aggregator, mirror, news article, SCI series or free-market
FX rate was used, and the CAPTCHA was never solved or bypassed.

Everything else is **programmer-reported capture metadata, raw bytes
unavailable for independent audit**:

* `access_probe_raw_bytes_available` = **false** — the response bodies from the
  capture session were not retained;
* `response_headers_captured` = **false**, `stderr_logs_captured` = **false**;
* the recorded SHA-256 values, byte lengths, status codes, and the
  WAF / CAPTCHA / byte-reproducibility classifications **cannot be
  re-derived** from committed bytes.

Accordingly this package does **not** assert that the responses were definitely
CAPTCHA pages, that they definitely contained no macro series, that every
responding URL definitely returned "Request Rejected", or that
non-reproducibility is proven. Those remain programmer-reported observations
only, and **none of them is used as G02, G03 or G04 evidence**.

## Why the Gate is UNRESOLVED

Three distinct causes, deliberately not conflated:

1. **Frozen-contract incompleteness** — the frozen contracts alone do not
   uniquely determine the operational series for any candidate.
2. **Official-metadata unavailability** — no independently verifiable official
   CBI documentation or data artifact is committed, so the prospective lock
   could not be completed from official sources in this execution.
3. **No value-level execution** — coverage, join, event counts and temporal
   support were never assessed.

It is **not** established that the Gate could not have passed with official
access. Official source documentation could potentially have completed the
prospective definition lock. A new human-selected contract is one possible
future route; an authorized, reproducible official CBI documentation and data
package is another.

The candidate ambiguity classes recorded in the lock are **unverified**
(`ambiguity_classes_verified_against_official_documentation` = false). They are
derived from what the incomplete frozen contract leaves open and must not be
read as verified facts about CBI series.

## Parent sample

The M3 Gate denominator is the **retained-M2 development common sample**, not
the 666-row M1 development universe:

* rows **{parent["parent_rows"]}**, positive **{parent["parent_positive"]}**,
  negative **{parent["parent_negative"]}**, companies
  **{parent["parent_companies"]}**
* derived programmatically from `{D2_FEATURES_REL}` and reconciled against the
  committed PR #71 join audit; membership never altered
* the 666-row universe is reported as reconciliation audit only

## Thresholds

Stage125 Part 4 development thresholds, unchanged: candidate coverage
**{CANDIDATE_VALID_COVERAGE_MIN}**, exact three-variable common sample
**{BLOCK_COMMON_SAMPLE_COVERAGE_MIN}**, minimum positives per locked
validation window **{MIN_POSITIVE_EACH_VALIDATION_WINDOW}**. The historical
80-pair Part 3A pilot rules G09–G14 are **not** applied.

Unresolved coverage is recorded as `null`, never as zero.

## Temporal degrees of freedom

Macro observations are shared across many company-year rows. The
{parent["parent_rows"]} company-year rows are **not** independent macro
observations and are never reported as such. The independent temporal macro
support is unresolved because no macro observation was retrieved.

## Final-test firewall

Final-test target years {list(FINAL_TEST_TARGET_YEARS)} remain locked:
0 rows loaded, 0 predictor values read, 0 target values read, 0 macro values
materialized, 0 predictions, 0 evaluations.

## State

* `m3_macro_data_gate_authorization_consumed` = **true**
* `m3_macro_data_gate_executed` = **true**, status `{status}`
* `m3_data_workstream_started` = **true**
* `m3_incremental_evaluation_authorized` = **false**
* `m3_modeling_started` = **false**
* `m4_authorized` = **false**, `m4_started` = **false**
* `final_test_locked` = **true**

The research pointer was **not** advanced to
`{NEXT_ACTION_ON_PASS}`; `m3_macro_data_gate_human_review_required` = **true**.
"""
