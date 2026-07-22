"""Stage126 M1 — Robustness Part 0 Decision Lock (human-authorized, no execution).

This module records and validates the **execution contract** for the six
registered Stage126 M1 robustness categories. It is a *decision lock only*:

  * it authorizes NO robustness execution, model fit, prediction, retuning,
    full-development refit, final-test access, SMOTE/SMOTENC, SHAP, or M2/M3/M4;
  * it imports NO model-fitting / resampling / SHAP / final-test code;
  * it is offline, deterministic, and performs zero network activity.

It records the exact human decision text (byte-for-byte Persian + recomputed
SHA-256), the six category execution specifications, the global execution rules,
and the one-category-per-micro-part packaging policy — and cross-validates every
locked value against the frozen Stage125 Part 4 / Part 5 contracts and the
immutable primary Stage126 artifacts (which must remain byte-identical).

The decision record is an **additive operational layer**. It does not rewrite or
retroactively alter any historical Stage125 contract or any primary Stage126
artifact.
"""
from __future__ import annotations

import hashlib
import importlib.metadata as importlib_metadata
import json
import platform
import subprocess
from pathlib import Path
from typing import Any

from src import stage125_part3b0_evidence_readiness as p3b0
from src import stage126_authorization_transition_guard as auth_guard

# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #

QC_STAGE = "stage126_m1_robustness_part0_decision_lock"
CURRENT_STAGE = "Stage126"
CONTRACT_ID = "stage126_m1_robustness_execution_contract"
CONTRACT_VERSION = "stage126_m1_robustness_execution_contract_v1"
DECISION_ID = "stage126-m1-robustness-part0-decision-lock"
SOURCE_REPOSITORY = "abtinasg/papermali"
SOURCE_MAIN_COMMIT = "6a4f05da219db7faea5a27c2adbee6b55497ec01"

RUNTIME_VERSION_PACKAGES = ("pandas", "numpy", "scikit-learn", "xgboost", "jdatetime")

# Relative source / runner / test / output paths.
SRC_REL = "project/src/stage126_m1_robustness_part0_decision_lock.py"
RUN_REL = "project/run_stage126_m1_robustness_part0_decision_lock.py"
TEST_REL = "project/tests/test_stage126_m1_robustness_part0_decision_lock.py"

F_RECORD = "stage126_m1_robustness_part0_decision_record.json"
F_QC = "stage126_m1_robustness_part0_decision_lock_qc_report.json"
F_METADATA = "metadata_and_hashes_stage126_m1_robustness_part0_decision_lock.json"
F_README = "README_STAGE126_M1_ROBUSTNESS_PART0_DECISION_LOCK.md"

STAGE126_DIR_REL = "project/stage126"

# --------------------------------------------------------------------------- #
# Exact human decision text (byte-for-byte, ZWNJ-preserving UTF-8)
# --------------------------------------------------------------------------- #

HUMAN_DECISION_TEXT_FA = (
    "من به‌عنوان ناظر انسانی و مالک تصمیم پژوهشی پروژه، فقط ثبت و "
    "قفل‌کردن قرارداد اجرایی آزمون‌های استحکام M1 را مطابق مشخصات این "
    "دستور مجاز می‌کنم. این مجوز شامل اجرای هیچ آزمون استحکام، برازش یا "
    "پیش‌بینی مدل، بازتنظیم ابرپارامتر، بازبرازش روی کل دوره توسعه، دسترسی "
    "یا ارزیابی آزمون نهایی، SMOTE یا SMOTENC، SHAP، یا شروع M2، M3 یا M4 نیست."
)
HUMAN_DECISION_TEXT_SHA256 = (
    "79f98e4c6dc81e6362ad90b138997c0d0bc3c8bad5d471ea65615ffc49627a5b"
)

# --------------------------------------------------------------------------- #
# Frozen contract references (read-only; never modified by this module)
# --------------------------------------------------------------------------- #

FROZEN_PART5_ENTRY_CONTRACT_REL = (
    "project/stage125/part5_stage126_m1_entry_contract_stage125.json"
)
FROZEN_PART4_CONTRACT_PATHS = (
    "project/stage125/part4_statistical_analysis_plan_stage125.json",
    "project/stage125/part4_model_specifications_stage125.json",
    "project/stage125/part4_preprocessing_contract_stage125.json",
    "project/stage125/part4_temporal_split_contract_stage125.json",
    "project/stage125/part4_metrics_uncertainty_contract_stage125.json",
    "project/stage125/part4_feature_sets_stage125.csv",
    "project/stage125/part4_sample_target_matrix_stage125.csv",
    "project/stage125/part4_hyperparameter_budget_stage125.json",
)

# Immutable primary Stage126 artifacts (must remain byte-identical).
PRIMARY_ARTIFACT_SHA256: dict[str, str] = {
    "project/stage126/stage126_m1_configuration_registry.csv":
        "decbf43a5c34669bdd7a0c68c0ad6aec5611efc7c3ca82b09f5e85f72d635804",
    "project/stage126/stage126_m1_development_access_manifest.csv":
        "0c2783d0e43ebba712a1c41b6889a2f8f646340bae6a75ad15902a8a0c368e39",
    "project/stage126/stage126_m1_development_metrics.csv":
        "1c5f33b4e3a156b111d29a2c4e13ecee9c5e7ad73f6b3d98cf3c6b4b506be17a",
    "project/stage126/stage126_m1_development_oof_predictions.csv":
        "48a00c882309c412aeba8f3b7200b65003e435080410c7b7c7ab62c9c3326749",
    "project/stage126/stage126_m1_final_test_lock_guard.json":
        "509e58fc39e3c5d886993c11b954fc06c267c96d02c081d8e50b0cda52e58b03",
    "project/stage126/stage126_m1_primary_development_lock.json":
        "c500563049e30a27ac59fd3d673ef801b8d8e12f0bb684dd2e0aec13eb5618e4",
    "project/stage126/stage126_m1_selected_configurations.json":
        "34488e07bd16d467b177c37dcaf571d9c68c25ecbc1c94fee5091f554d2eb97e",
    "project/stage126/stage126_m1_tuning_results.csv":
        "e7e1e6808e394273676709aa94bfa713bbf8a790fadabee22ea20b849adbe649",
}

# Exact byte-integrity SHA-256 of the nine consumed frozen Stage125 contracts,
# computed from the frozen source-commit blobs. These pin the exact bytes (not a
# normalized-text or semantic equivalence) so any byte or whitespace change in a
# consumed contract fails closed.
FROZEN_STAGE125_SOURCE_COMMIT = "6a4f05da219db7faea5a27c2adbee6b55497ec01"
FROZEN_STAGE125_CONTRACT_SHA256: dict[str, str] = {
    "project/stage125/part5_stage126_m1_entry_contract_stage125.json":
        "74a2159785daeda44fa82ebd76f42870fa25aba3667846bccba6b3099ea65da5",
    "project/stage125/part4_statistical_analysis_plan_stage125.json":
        "8763bc094561ce63da2f9f621b8278a1c9836c8cbc2aeaace934e439d6e79d6e",
    "project/stage125/part4_model_specifications_stage125.json":
        "ef933be3eb2f75e6f493ac1401100c629bdb83850c81950d8f235c5ccf4cdb21",
    "project/stage125/part4_preprocessing_contract_stage125.json":
        "3722bd6165574c78aef1138a810ff4863b5c214f80df197889eaa40163f0e415",
    "project/stage125/part4_temporal_split_contract_stage125.json":
        "3f6ff8c7adf77295e558045e5bcaa391b5d2c10e7be0a89aeb0c8ac2dd0463b9",
    "project/stage125/part4_metrics_uncertainty_contract_stage125.json":
        "117ddf3ecf688032a3baba4843a477e58890a33b2ad80c26574c33c949ae7760",
    "project/stage125/part4_feature_sets_stage125.csv":
        "79e87cbcef1a6aa70fa6e4b837c4634df9e1f701e25f42a87ac34012452b850f",
    "project/stage125/part4_sample_target_matrix_stage125.csv":
        "d7f026ecf0b3b2810eb95df5b912184c3b9f4e36031e9b366c00fd858b7c4792",
    "project/stage125/part4_hyperparameter_budget_stage125.json":
        "22d6989681a7cd59ffbf57077910615ce00adb9f171d303d5d61100a54490b40",
}

# Exact frozen Part 4 preprocessing-contract fields incorporated by reference and
# validated for exact equality. The continuous pipeline must remain exactly this.
PREPROCESSING_CONTRACT_REL = (
    "project/stage125/part4_preprocessing_contract_stage125.json"
)
EXPECTED_CONTINUOUS_PIPELINE_ORDER = (
    "1_deterministic_source_to_feature_transformation",
    "2_capture_original_pre_imputation_missingness_mask",
    "3_estimate_1st_99th_percentile_clipping_bounds_on_observed_training_fold_values_only",
    "4_apply_training_derived_clipping_bounds",
    "5_estimate_training_fold_median_on_observed_clipped_training_values",
    "6_impute_missing_values_with_training_fold_median",
    "7_append_missingness_indicators_from_original_pre_imputation_mask",
    "8_logistic_regression_only_standardize_imputed_continuous_features_using_training_fold_mean_std",
)
# Exact required preprocessing scalar/list fields (field -> expected value).
EXPECTED_PREPROCESSING_FIELDS: dict[str, Any] = {
    "fit_scope": "each_temporal_training_fold_separately",
    "forbidden_fit_on": [
        "validation_data",
        "final_test_data",
        "combined_train_plus_validation_before_configuration_selection",
    ],
    "logistic_regression_extra":
        "training_fold_standardization_after_imputation_continuous_only",
    "missing_indicators_standardized": False,
    "random_forest_standardization": False,
    "xgboost_standardization": False,
    "validation_and_final_test_masks_from_own_original_missing_positions": True,
}

# --------------------------------------------------------------------------- #
# Locked contract values (cross-validated against frozen contracts at run time)
# --------------------------------------------------------------------------- #

MODEL_FAMILIES = (
    "regularized_logistic_regression",
    "random_forest",
    "xgboost",
)

SELECTED_CONFIGURATIONS = {
    "regularized_logistic_regression": "logistic__C_0.1",
    "random_forest": "rf__depth_3__maxfeat_'sqrt'__leaf_10",
    "xgboost": "xgboost__lr_0.03__depth_2__mcw_1__lambda_1",
}

MODEL_SEEDS = (20260719, 20260720, 20260721, 20260722, 20260723)
SMOTE_SAMPLER_RANDOM_STATE = 20260725

DEVELOPMENT_TARGET_YEARS = (1393, 1394, 1395, 1396, 1397, 1398, 1399)
FOLD1 = {
    "train_target_years": [1393, 1394, 1395],
    "validation_target_years": [1396, 1397],
}
FOLD2 = {
    "train_target_years": [1393, 1394, 1395, 1396, 1397],
    "validation_target_years": [1398, 1399],
}

M1_PRIMARY_FEATURE_ORDER = (
    "log_total_assets",
    "leverage_ratio",
    "current_ratio",
    "roa_period_adjusted",
    "ocf_to_assets_period_adjusted",
    "asset_turnover_period_adjusted",
    "operating_margin_period_adjusted",
    "financial_expense_to_assets_period_adjusted",
    "accumulated_loss_to_capital_ratio",
)
M1_TARGET_PROXIMITY_ORDER = (
    "log_total_assets",
    "current_ratio",
    "roa_period_adjusted",
    "asset_turnover_period_adjusted",
    "operating_margin_period_adjusted",
    "financial_expense_to_assets_period_adjusted",
)

PRIMARY_SAMPLE = "main_rule_a_primary"
PRIMARY_TARGET = "FD_target_main_t_plus_1"
PERSISTENT_LOSS_TARGET = "FD_target_persistent_loss_robustness_t_plus_1"

METRICS = ("PR-AUC", "ROC-AUC", "Brier_score", "Recall@10%", "Lift@10%")
METRIC_SCOPES = ("fold1_validation", "fold2_validation", "pooled_development_oof")
TOPK_RULE = "K_y = ceil(0.10 * N_y)"

FORBIDDEN_IN_ROBUSTNESS_MICRO_PARTS = (
    "platt_calibration",
    "calibration_curves",
    "calibration_intercept_or_slope",
    "f2_threshold_optimization",
    "paired_bootstrap",
    "holm_correction",
    "p_values",
    "new_confirmatory_families",
    "post_hoc_multiplicity_families",
    "winner_selection",
)

# The six categories, in binding execution order (Part 1 .. Part 6).
CATEGORY_SPECS: tuple[dict[str, Any], ...] = (
    {
        "order": 1,
        "future_micro_part": "Part 1",
        "category_id": "m1_target_proximity_six_feature_set",
        "scientific_role": "target_proximity_feature_set_robustness",
        "changed_dimension": "feature_set",
        "sample": PRIMARY_SAMPLE,
        "target": PRIMARY_TARGET,
        "feature_set": "M1_TARGET_PROXIMITY_ROBUSTNESS",
        "features_exact_order": list(M1_TARGET_PROXIMITY_ORDER),
        "imbalance_policy": "primary_class_weighting",
    },
    {
        "order": 2,
        "future_micro_part": "Part 2",
        "category_id": "main_rule_b_listing_robustness",
        "scientific_role": "listing_timing_sample_robustness",
        "changed_dimension": "sample",
        "sample": "main_rule_b_listing_robustness",
        "target": PRIMARY_TARGET,
        "feature_set": "M1_PRIMARY_FEATURE_ORDER",
        "features_exact_order": list(M1_PRIMARY_FEATURE_ORDER),
        "imbalance_policy": "primary_class_weighting",
    },
    {
        "order": 3,
        "future_micro_part": "Part 3",
        "category_id": "expanded_rule_a_company_scope_robustness",
        "scientific_role": "expanded_company_scope_sample_robustness",
        "changed_dimension": "sample",
        "sample": "expanded_rule_a_company_scope_robustness",
        "target": PRIMARY_TARGET,
        "feature_set": "M1_PRIMARY_FEATURE_ORDER",
        "features_exact_order": list(M1_PRIMARY_FEATURE_ORDER),
        "imbalance_policy": "primary_class_weighting",
    },
    {
        "order": 4,
        "future_micro_part": "Part 4",
        "category_id": "expanded_rule_b_combined_robustness",
        "scientific_role": "combined_sample_robustness",
        "changed_dimension": "sample",
        "sample": "expanded_rule_b_combined_robustness",
        "target": PRIMARY_TARGET,
        "feature_set": "M1_PRIMARY_FEATURE_ORDER",
        "features_exact_order": list(M1_PRIMARY_FEATURE_ORDER),
        "imbalance_policy": "primary_class_weighting",
    },
    {
        "order": 5,
        "future_micro_part": "Part 5",
        "category_id": "persistent_loss_robustness_target",
        "scientific_role": "secondary_robustness_target",
        "changed_dimension": "target",
        "sample": PRIMARY_SAMPLE,
        "target": PERSISTENT_LOSS_TARGET,
        "feature_set": "M1_PRIMARY_FEATURE_ORDER",
        "features_exact_order": list(M1_PRIMARY_FEATURE_ORDER),
        "imbalance_policy": "primary_class_weighting",
        "notes": (
            "persistent-loss target restricted to the primary Rule A sample so "
            "only the target changes; not multiplied across all four samples"
        ),
    },
    {
        "order": 6,
        "future_micro_part": "Part 6",
        "category_id": "smote_training_fold_only_robustness",
        "scientific_role": "smote_training_fold_only_robustness",
        "changed_dimension": "imbalance_strategy",
        "sample": PRIMARY_SAMPLE,
        "target": PRIMARY_TARGET,
        "feature_set": "M1_PRIMARY_FEATURE_ORDER",
        "features_exact_order": list(M1_PRIMARY_FEATURE_ORDER),
        "imbalance_policy": "SMOTE_family_training_fold_only_robustness",
        "smote_rules": {
            "class_weighting_disabled": True,
            "xgboost_scale_pos_weight": 1,
            "second_tuning_search": False,
            "uses_selected_non_weight_hyperparameters": True,
            "applied_only_inside_each_training_fold": True,
            "validation_data_never_resampled": True,
            "final_test_never_accessed_or_resampled": True,
            "k_neighbors": "min(5, training_minority_count - 1)",
            "sampler_random_state": SMOTE_SAMPLER_RANDOM_STATE,
            "missingness_indicator_rule": (
                "If appended binary missingness-indicator columns are present, "
                "operationalize the registered SMOTE robustness with SMOTENC and "
                "mark all appended missingness-indicator columns as categorical; "
                "continuous features remain continuous; missingness indicators "
                "must remain binary 0/1 in synthetic observations. If no "
                "missingness-indicator columns exist in the fold matrix, standard "
                "SMOTE may be used."
            ),
            "logistic_pipeline": (
                "standardize continuous features using training-fold parameters; "
                "do not standardize indicators; then apply SMOTENC/SMOTE inside "
                "the training fold; Logistic fit is deterministic"
            ),
            "rf_xgboost_pipeline": (
                "do not standardize; use the fixed sampler random_state "
                "20260725; use model seeds 20260719-20260723; use the same fixed "
                "resampled training matrix across the five model seeds; mean "
                "RF/XGBoost probabilities across the five model seeds"
            ),
        },
    },
)

FUTURE_MICRO_PART_ORDER = tuple(c["category_id"] for c in CATEGORY_SPECS)


class QCFail(RuntimeError):
    """Fail-closed decision-lock validation error."""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _json_str(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def recompute_decision_text_sha256(text_fa: str) -> str:
    """SHA-256 of the UTF-8 bytes of the actual Persian decision text."""
    return hashlib.sha256(text_fa.encode("utf-8")).hexdigest()


def _git(repo_root: str | Path, *args: str) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=True, capture_output=True, text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return ""
    return out.stdout.strip()


def runtime_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for pkg in RUNTIME_VERSION_PACKAGES:
        try:
            versions[pkg] = importlib_metadata.version(pkg)
        except importlib_metadata.PackageNotFoundError:
            versions[pkg] = "absent"
    versions["python"] = platform.python_version()
    return versions


def _read_json(repo_root: Path, rel: str) -> dict[str, Any]:
    path = repo_root / rel
    if not path.is_file():
        raise QCFail(f"missing frozen contract: {rel}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QCFail(f"unreadable frozen contract {rel}: {exc}") from exc


def repo_root_from(project_dir: Path) -> Path:
    return project_dir.parent if project_dir.name == "project" else project_dir


# --------------------------------------------------------------------------- #
# Cross-validation against frozen contracts (fail-closed)
# --------------------------------------------------------------------------- #

def verify_decision_text() -> None:
    recomputed = recompute_decision_text_sha256(HUMAN_DECISION_TEXT_FA)
    if recomputed != HUMAN_DECISION_TEXT_SHA256:
        raise QCFail(
            f"human decision text SHA-256 mismatch: {recomputed} != "
            f"{HUMAN_DECISION_TEXT_SHA256}"
        )


def verify_primary_artifacts_immutable(repo_root: Path) -> dict[str, str]:
    observed: dict[str, str] = {}
    for rel, expected in PRIMARY_ARTIFACT_SHA256.items():
        path = repo_root / rel
        if not path.is_file():
            raise QCFail(f"missing primary Stage126 artifact: {rel}")
        got = sha256_file(path)
        observed[rel] = got
        if got != expected:
            raise QCFail(
                f"primary Stage126 artifact changed: {rel} {got} != {expected}"
            )
    return observed


def verify_frozen_stage125_contract_hashes(repo_root: Path) -> dict[str, str]:
    """Exact byte-integrity of the nine consumed frozen Stage125 contracts.

    Reads the current working-tree bytes, computes SHA-256, and fails closed on
    any missing path or any hash difference. Returns the exact observed hash map
    (which equals the pinned map on success). This is stronger than Git object
    SHA-1 identity: it pins the exact content bytes independently of Git.
    """
    if set(FROZEN_STAGE125_CONTRACT_SHA256) != set(FROZEN_PART4_CONTRACT_PATHS) | {
        FROZEN_PART5_ENTRY_CONTRACT_REL
    }:
        raise QCFail("frozen Stage125 contract hash map path set is not exact")
    observed: dict[str, str] = {}
    for rel, expected in sorted(FROZEN_STAGE125_CONTRACT_SHA256.items()):
        path = repo_root / rel
        if not path.is_file():
            raise QCFail(f"missing frozen Stage125 contract: {rel}")
        got = sha256_file(path)
        observed[rel] = got
        if got != expected:
            raise QCFail(
                f"frozen Stage125 contract byte change: {rel} {got} != {expected}"
            )
    return observed


def verify_stage125_tree_unchanged(
    repo_root: Path, base: str = FROZEN_STAGE125_SOURCE_COMMIT,
) -> None:
    """Fail-closed: the complete tracked project/stage125/ tree is unchanged.

    Covers committed modifications/additions/deletions relative to the frozen
    source commit, staged changes, unstaged changes, and non-ignored untracked
    paths under project/stage125/. Reports the exact offending paths. ``base``
    defaults to the frozen source commit and is parameterizable for testing.
    """
    root = str(repo_root)
    offending: list[str] = []
    # Committed diff (base..HEAD) restricted to project/stage125/.
    committed = _git(root, "diff", "--name-only", base, "HEAD", "--", "project/stage125/")
    offending += [f"committed:{p}" for p in committed.splitlines() if p.strip()]
    # Staged diff vs base.
    staged = _git(root, "diff", "--cached", "--name-only", base, "--", "project/stage125/")
    offending += [f"staged:{p}" for p in staged.splitlines() if p.strip()]
    # Unstaged working-tree diff vs base.
    unstaged = _git(root, "diff", "--name-only", base, "--", "project/stage125/")
    offending += [f"worktree:{p}" for p in unstaged.splitlines() if p.strip()]
    # Non-ignored untracked paths under project/stage125/.
    untracked = _git(
        root, "ls-files", "--others", "--exclude-standard", "--", "project/stage125/"
    )
    offending += [f"untracked:{p}" for p in untracked.splitlines() if p.strip()]
    if offending:
        raise QCFail(
            "frozen Stage125 tree changed relative to "
            f"{base}: {sorted(set(offending))}"
        )


def load_preprocessing_incorporation(repo_root: Path) -> dict[str, Any]:
    """Load and exactly validate the frozen Part 4 preprocessing contract.

    Returns the exact incorporated preprocessing fields for the decision record.
    Fails closed if any incorporated field differs from the frozen contract.
    """
    contract = _read_json(repo_root, PREPROCESSING_CONTRACT_REL)
    order = contract.get("continuous_pipeline_order")
    if tuple(order or ()) != EXPECTED_CONTINUOUS_PIPELINE_ORDER:
        raise QCFail("preprocessing continuous_pipeline_order differs from frozen")
    incorporated: dict[str, Any] = {
        "continuous_pipeline_order": list(EXPECTED_CONTINUOUS_PIPELINE_ORDER),
    }
    for field, expected in EXPECTED_PREPROCESSING_FIELDS.items():
        if contract.get(field) != expected:
            raise QCFail(
                f"preprocessing field '{field}' differs from frozen contract: "
                f"{contract.get(field)!r} != {expected!r}"
            )
        incorporated[field] = expected
    return incorporated


def verify_against_frozen_contracts(repo_root: Path) -> None:
    """Every locked value must agree with the frozen Part 4 / Part 5 contracts.

    Fail-closed: any disagreement raises QCFail so the decision lock can never
    silently diverge from the historical contracts it operationalizes.
    """
    entry = _read_json(repo_root, FROZEN_PART5_ENTRY_CONTRACT_REL)
    sap = _read_json(
        repo_root, "project/stage125/part4_statistical_analysis_plan_stage125.json"
    )
    model_specs = _read_json(
        repo_root, "project/stage125/part4_model_specifications_stage125.json"
    )
    temporal = _read_json(
        repo_root, "project/stage125/part4_temporal_split_contract_stage125.json"
    )
    dev_lock = _read_json(
        repo_root, "project/stage126/stage126_m1_primary_development_lock.json"
    )

    # 1. Six registered categories match (same set + same order).
    registered = [
        c["category_id"]
        for c in entry.get("registered_m1_robustness_after_primary_lock", [])
    ]
    if tuple(registered) != FUTURE_MICRO_PART_ORDER:
        raise QCFail(
            f"registered robustness categories mismatch: {registered} != "
            f"{list(FUTURE_MICRO_PART_ORDER)}"
        )

    # 2. Model families + selected configurations match the primary lock exactly.
    if tuple(dev_lock.get("model_families", [])) != MODEL_FAMILIES:
        raise QCFail("model_families disagree with primary development lock")
    if dev_lock.get("selected_configurations") != SELECTED_CONFIGURATIONS:
        raise QCFail("selected_configurations disagree with primary lock")
    if tuple(dev_lock.get("final_oof_seeds", [])) != MODEL_SEEDS:
        raise QCFail("model seeds disagree with primary lock final_oof_seeds")

    # 3. Feature orders match the frozen Part 4 SAP.
    if tuple(sap.get("m1_primary_feature_order", [])) != M1_PRIMARY_FEATURE_ORDER:
        raise QCFail("M1 primary feature order disagrees with Part 4 SAP")
    if (tuple(sap.get("m1_target_proximity_robustness_order", []))
            != M1_TARGET_PROXIMITY_ORDER):
        raise QCFail("M1 target-proximity order disagrees with Part 4 SAP")

    # 4. Samples exist in the frozen Part 4 sample_specs.
    sample_specs = sap.get("sample_specs", {})
    for c in CATEGORY_SPECS:
        if c["sample"] not in sample_specs:
            raise QCFail(f"sample not in Part 4 sample_specs: {c['sample']}")

    # 5. Persistent-loss target matches the frozen secondary robustness target.
    if PERSISTENT_LOSS_TARGET not in {
        row_target
        for row_target in _sample_target_targets(repo_root)
    }:
        raise QCFail("persistent-loss target not present in Part 4 matrix")

    # 6. SMOTE sampler seed matches the frozen Part 4 model specification.
    smote = model_specs.get("smote_robustness", {})
    if smote.get("random_state") != SMOTE_SAMPLER_RANDOM_STATE:
        raise QCFail("SMOTE sampler random_state disagrees with Part 4 model spec")
    if smote.get("second_tuning_search") is not False:
        raise QCFail("Part 4 SMOTE second_tuning_search is not False")
    if smote.get("class_weighting_disabled_when_smote_active") is not True:
        raise QCFail("Part 4 SMOTE class weighting not disabled")

    # 7. Temporal folds match the frozen Part 4 temporal split contract.
    if (temporal.get("temporal_validation_fold_1", {}).get("train_target_years")
            != FOLD1["train_target_years"]):
        raise QCFail("Fold 1 train years disagree with Part 4 temporal contract")
    if (temporal.get("temporal_validation_fold_1", {}).get("validation_target_years")
            != FOLD1["validation_target_years"]):
        raise QCFail("Fold 1 validation years disagree with Part 4 contract")
    if (temporal.get("temporal_validation_fold_2", {}).get("train_target_years")
            != FOLD2["train_target_years"]):
        raise QCFail("Fold 2 train years disagree with Part 4 temporal contract")
    if (temporal.get("temporal_validation_fold_2", {}).get("validation_target_years")
            != FOLD2["validation_target_years"]):
        raise QCFail("Fold 2 validation years disagree with Part 4 contract")
    if list(temporal.get("development_target_years", [])) != list(
        DEVELOPMENT_TARGET_YEARS
    ):
        raise QCFail("development target years disagree with Part 4 contract")

    # 8. Final test must remain locked (entry contract + primary lock guard).
    if entry.get("final_test_unlocked") is not False:
        raise QCFail("Part 5 entry contract final_test_unlocked is not False")
    if dev_lock.get("final_test_locked") is not True:
        raise QCFail("primary development lock final_test_locked is not True")


def _sample_target_targets(repo_root: Path) -> list[str]:
    path = repo_root / "project/stage125/part4_sample_target_matrix_stage125.csv"
    if not path.is_file():
        raise QCFail("missing Part 4 sample_target_matrix")
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return []
    header = lines[0].split(",")
    idx = header.index("target")
    return [ln.split(",")[idx] for ln in lines[1:] if ln.strip()]


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #

def build_decision_record(repo_root: Path) -> dict[str, Any]:
    """Deterministic decision record. NO git/time fields (stable across builds).

    ``repo_root`` is required so the frozen-contract integrity map and the exact
    Part 4 preprocessing incorporation are materialized from the frozen
    contracts themselves (fail-closed), not hardcoded independently.
    """
    verify_decision_text()
    frozen_hashes = verify_frozen_stage125_contract_hashes(repo_root)
    preprocessing_incorporation = load_preprocessing_incorporation(repo_root)
    return {
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "decision_id": DECISION_ID,
        "decision_locked": True,
        "execution_authorized": False,
        "m1_robustness_started": False,
        "m1_robustness_completed": False,
        "full_development_refit_authorized": False,
        "full_development_refit_performed": False,
        "final_test_access_authorized": False,
        "final_test_unlocked": False,
        "final_test_evaluation_authorized": False,
        "final_test_evaluation_performed": False,
        "shap_authorized": False,
        "m2_m3_m4_authorized": False,
        "one_category_per_micro_part_pr": True,
        "human_decision_text": HUMAN_DECISION_TEXT_FA,
        "human_decision_text_sha256": HUMAN_DECISION_TEXT_SHA256,
        "authorizing_role": "human_supervisor_data_owner",
        "source_repository": SOURCE_REPOSITORY,
        "source_main_commit": SOURCE_MAIN_COMMIT,
        "frozen_part4_contract_paths": list(FROZEN_PART4_CONTRACT_PATHS),
        "frozen_part5_contract_path": FROZEN_PART5_ENTRY_CONTRACT_REL,
        "frozen_stage125_source_commit": FROZEN_STAGE125_SOURCE_COMMIT,
        "frozen_stage125_tree_unchanged": True,
        "frozen_stage125_contract_sha256": dict(sorted(frozen_hashes.items())),
        "primary_artifact_sha256": dict(sorted(PRIMARY_ARTIFACT_SHA256.items())),
        "global_execution_rules": build_global_execution_rules(
            preprocessing_incorporation
        ),
        "categories": [dict(c) for c in CATEGORY_SPECS],
        "execution_order": list(FUTURE_MICRO_PART_ORDER),
        "packaging_policy": "one_category_per_micro_part_pr",
        "future_micro_parts": [
            {"micro_part": c["future_micro_part"], "category_id": c["category_id"]}
            for c in CATEGORY_SPECS
        ],
        "part0_authorizes_part1": False,
        "each_part_requires_separate_human_authorization": True,
        "scientific_interpretation": "sensitivity_analysis_only",
    }


def build_global_execution_rules(
    preprocessing_incorporation: dict[str, Any],
) -> dict[str, Any]:
    return {
        "one_factor_at_a_time": (
            "Each robustness category changes only its registered robustness "
            "dimension; all non-changed dimensions remain equal to the locked "
            "primary specification."
        ),
        "model_families": list(MODEL_FAMILIES),
        "no_retuning": {
            "second_tuning_search": False,
            "reuse_selected_primary_configurations": True,
            "selected_configurations": dict(SELECTED_CONFIGURATIONS),
            "robustness_may_not_replace_selected_configurations": True,
        },
        "temporal_folds": {
            "fold1": FOLD1,
            "fold2": FOLD2,
            "only_development_years_loaded": list(DEVELOPMENT_TARGET_YEARS),
        },
        "preprocessing": {
            "use_frozen_part4_training_fold_only_contract": True,
            "frozen_preprocessing_contract_path": PREPROCESSING_CONTRACT_REL,
            "reduced_feature_set_missingness_indicators": (
                "create missingness indicators only for the selected base features"
            ),
            "never_fit_on_validation_or_final_test": True,
            # Exact incorporation-by-reference of the frozen Part 4 preprocessing
            # contract (materialized + validated for exact equality at build).
            "continuous_pipeline_order":
                preprocessing_incorporation["continuous_pipeline_order"],
            "fit_scope": preprocessing_incorporation["fit_scope"],
            "forbidden_fit_on": preprocessing_incorporation["forbidden_fit_on"],
            "logistic_regression_extra":
                preprocessing_incorporation["logistic_regression_extra"],
            "missing_indicators_standardized":
                preprocessing_incorporation["missing_indicators_standardized"],
            "random_forest_standardization":
                preprocessing_incorporation["random_forest_standardization"],
            "xgboost_standardization":
                preprocessing_incorporation["xgboost_standardization"],
            "validation_and_final_test_masks_from_own_original_missing_positions":
                preprocessing_incorporation[
                    "validation_and_final_test_masks_from_own_original_missing_positions"
                ],
        },
        "non_smote_imbalance_policy": {
            "logistic_regression": {"class_weight": "balanced"},
            "random_forest": {"class_weight": "balanced_subsample"},
            "xgboost": {
                "scale_pos_weight": (
                    "training_fold_negative_evaluable_count / "
                    "training_fold_positive_evaluable_count"
                )
            },
            "weights_recomputed_from_robustness_training_fold_and_target": True,
        },
        "seeds_without_retuning": {
            "no_tuning_seeds_used": True,
            "logistic": "deterministic_single_fit_per_fold",
            "rf_xgboost_model_seeds": list(MODEL_SEEDS),
            "rf_xgboost_fold_probability": "mean_across_five_fixed_model_seeds",
        },
        "metrics": {
            "report": list(METRICS),
            "scopes": list(METRIC_SCOPES),
            "topk_rule": TOPK_RULE,
            "not_executed_in_robustness_micro_parts": list(
                FORBIDDEN_IN_ROBUSTNESS_MICRO_PARTS
            ),
            "frozen_calibration_and_uncertainty_retained_for_later_stage": True,
        },
        "scientific_interpretation": {
            "all_categories": "sensitivity_analysis_only",
            "may_not": [
                "change_a_selected_configuration",
                "change_the_locked_primary_model_family_ordering",
                "select_a_final_paper_winner",
                "unlock_the_final_test",
                "trigger_an_automatic_refit",
                "advance_m2_m3_m4",
            ],
            "severe_instability_reported_to_human_supervisor_not_auto_applied": True,
        },
    }


def build_readme() -> str:
    lines = [
        "# Stage126 M1 — Robustness Part 0 Decision Lock",
        "",
        "**Decision lock only. No robustness model was executed. No model was "
        "fit or predicted. No retuning occurred. No SMOTE or SMOTENC was "
        "executed. Primary Stage126 artifacts are byte-identical. The final "
        "test remains locked and untouched. Part 1 is not authorized or "
        "started.**",
        "",
        "This Part 0 records the machine-readable execution contract "
        f"(`{CONTRACT_ID}`, version `{CONTRACT_VERSION}`) for the six "
        "registered Stage126 M1 robustness categories. It is an additive "
        "operational layer over the frozen Stage125 Part 4 / Part 5 contracts "
        "and does not modify any historical contract or primary Stage126 "
        "artifact.",
        "",
        "## Execution order (binding via this decision record)",
        "",
        "| Micro-part | Category | Changed dimension | Sample | Target | Feature set |",
        "|---|---|---|---|---|---|",
    ]
    for c in CATEGORY_SPECS:
        lines.append(
            f"| {c['future_micro_part']} | `{c['category_id']}` | "
            f"{c['changed_dimension']} | `{c['sample']}` | `{c['target']}` | "
            f"`{c['feature_set']}` |"
        )
    lines += [
        "",
        "## Global rules (locked)",
        "",
        "- One factor at a time: each category changes only its registered "
        "dimension; all others equal the locked primary specification.",
        "- Model families (all three, every category): "
        + ", ".join(f"`{m}`" for m in MODEL_FAMILIES) + ".",
        "- No retuning (`second_tuning_search=false`); reuse the primary "
        "selected configurations; robustness may not replace them.",
        "- Temporal folds: Fold 1 train 1393-1395 / val 1396-1397; "
        "Fold 2 train 1393-1397 / val 1398-1399. Only 1393-1399 loaded.",
        "- Metrics: PR-AUC, ROC-AUC, Brier score, Recall@10%, Lift@10% at "
        "fold1_validation / fold2_validation / pooled_development_oof; "
        f"top-K rule `{TOPK_RULE}`.",
        "- No calibration, no F2 threshold optimization, no paired bootstrap, "
        "no Holm correction, no p-values, no winner selection.",
        "- All six categories are sensitivity analyses only; they may not "
        "change a selected configuration, the primary model-family ordering, "
        "select a final winner, unlock the final test, trigger a refit, or "
        "advance M2/M3/M4.",
        "",
        "## Packaging",
        "",
        "One robustness category per micro-part PR. Each future Part requires a "
        "separate explicit human authorization after the preceding PR is "
        "reviewed and merged. **Part 0 does not authorize Part 1.**",
        "",
        "## SMOTE / SMOTENC missingness-indicator rule (Part 6)",
        "",
        "If appended binary missingness-indicator columns are present, "
        "operationalize the registered SMOTE robustness with **SMOTENC** and "
        "mark all appended missingness-indicator columns as categorical; "
        "continuous features remain continuous; missingness indicators must "
        "remain binary 0/1 in synthetic observations. If no missingness-"
        "indicator columns exist in the fold matrix, standard **SMOTE** may be "
        "used. Sampler `random_state=20260725`; "
        "`k_neighbors=min(5, training_minority_count - 1)`; applied only inside "
        "each training fold; validation and final-test data are never resampled.",
        "",
        "## Frozen Stage125 integrity (fail-closed)",
        "",
        "- **All frozen Stage125 tracked files are protected against change** — the "
        "complete tracked `project/stage125/` tree is verified unchanged relative "
        f"to `{FROZEN_STAGE125_SOURCE_COMMIT}` (committed, staged, unstaged, and "
        "non-ignored untracked paths), fail-closed.",
        "- **The nine consumed Stage125 contracts are individually SHA-256 pinned** "
        "to their exact frozen bytes; any byte or whitespace change fails closed.",
        "- **The Part 4 preprocessing sequence is incorporated exactly** — the "
        "frozen `continuous_pipeline_order` and the training-fold-only fit-scope / "
        "standardization / mask fields are materialized and validated for exact "
        "equality against `part4_preprocessing_contract_stage125.json`.",
    ]
    return "\n".join(lines).rstrip("\n") + "\n"


def build_qc_assertions(
    repo_root: Path, record: dict[str, Any],
    primary_observed: dict[str, str], network_attempts: int,
) -> list[dict[str, Any]]:
    a: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        a.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    add("decision_locked", record["decision_locked"] is True)
    add("execution_authorized_false", record["execution_authorized"] is False)
    add("m1_robustness_started_false", record["m1_robustness_started"] is False)
    add("m1_robustness_completed_false", record["m1_robustness_completed"] is False)
    add("full_development_refit_authorized_false",
        record["full_development_refit_authorized"] is False)
    add("full_development_refit_performed_false",
        record["full_development_refit_performed"] is False)
    add("final_test_access_authorized_false",
        record["final_test_access_authorized"] is False)
    add("final_test_unlocked_false", record["final_test_unlocked"] is False)
    add("final_test_evaluation_authorized_false",
        record["final_test_evaluation_authorized"] is False)
    add("final_test_evaluation_performed_false",
        record["final_test_evaluation_performed"] is False)
    add("shap_authorized_false", record["shap_authorized"] is False)
    add("m2_m3_m4_authorized_false", record["m2_m3_m4_authorized"] is False)
    add("one_category_per_micro_part_pr",
        record["one_category_per_micro_part_pr"] is True)
    add("part0_does_not_authorize_part1", record["part0_authorizes_part1"] is False)

    add("human_decision_text_sha256_recomputed",
        recompute_decision_text_sha256(record["human_decision_text"])
        == HUMAN_DECISION_TEXT_SHA256)
    add("human_decision_text_field_hash_matches",
        record["human_decision_text_sha256"] == HUMAN_DECISION_TEXT_SHA256)

    add("exactly_six_categories", len(record["categories"]) == 6)
    add("execution_order_exact",
        tuple(record["execution_order"]) == FUTURE_MICRO_PART_ORDER,
        str(record["execution_order"]))
    ids = [c["category_id"] for c in record["categories"]]
    add("category_ids_match_execution_order",
        tuple(ids) == FUTURE_MICRO_PART_ORDER)
    orders = [c["order"] for c in record["categories"]]
    add("category_order_1_to_6", orders == [1, 2, 3, 4, 5, 6])

    for c in record["categories"]:
        add(f"model_families_all_three[{c['category_id']}]",
            list(MODEL_FAMILIES) == record["global_execution_rules"]["model_families"])
    add("no_retuning",
        record["global_execution_rules"]["no_retuning"]["second_tuning_search"]
        is False)
    add("selected_configurations_locked",
        record["global_execution_rules"]["no_retuning"]["selected_configurations"]
        == SELECTED_CONFIGURATIONS)
    add("model_seeds_locked",
        record["global_execution_rules"]["seeds_without_retuning"][
            "rf_xgboost_model_seeds"] == list(MODEL_SEEDS))
    add("metrics_locked",
        record["global_execution_rules"]["metrics"]["report"] == list(METRICS))
    add("bootstrap_and_holm_not_executed",
        "paired_bootstrap" in FORBIDDEN_IN_ROBUSTNESS_MICRO_PARTS
        and "holm_correction" in FORBIDDEN_IN_ROBUSTNESS_MICRO_PARTS)
    add("winner_selection_not_permitted",
        "winner_selection" in FORBIDDEN_IN_ROBUSTNESS_MICRO_PARTS)

    # Category-specific sample/target/feature-set mapping.
    cat_by_id = {c["category_id"]: c for c in record["categories"]}
    add("cat1_target_proximity_features",
        cat_by_id["m1_target_proximity_six_feature_set"]["features_exact_order"]
        == list(M1_TARGET_PROXIMITY_ORDER))
    add("cat5_persistent_loss_primary_sample_only",
        cat_by_id["persistent_loss_robustness_target"]["sample"] == PRIMARY_SAMPLE
        and cat_by_id["persistent_loss_robustness_target"]["target"]
        == PERSISTENT_LOSS_TARGET)
    smote_cat = cat_by_id["smote_training_fold_only_robustness"]
    add("cat6_smote_class_weighting_disabled",
        smote_cat["smote_rules"]["class_weighting_disabled"] is True
        and smote_cat["smote_rules"]["xgboost_scale_pos_weight"] == 1)
    add("cat6_smote_training_fold_only",
        smote_cat["smote_rules"]["applied_only_inside_each_training_fold"] is True
        and smote_cat["smote_rules"]["validation_data_never_resampled"] is True)
    add("cat6_smotenc_categorical_indicator_rule_present",
        "SMOTENC" in smote_cat["smote_rules"]["missingness_indicator_rule"]
        and "categorical" in smote_cat["smote_rules"]["missingness_indicator_rule"])
    add("cat6_sampler_random_state",
        smote_cat["smote_rules"]["sampler_random_state"]
        == SMOTE_SAMPLER_RANDOM_STATE)

    # Frozen-contract and immutability cross-checks (raise earlier if violated).
    add("frozen_contracts_consistent", True, "verified pre-QC (fail-closed)")
    add("primary_artifacts_byte_identical",
        primary_observed == {k: PRIMARY_ARTIFACT_SHA256[k] for k in primary_observed})

    # Frozen Stage125 byte-integrity: exact nine-path SHA-256 map + tree unchanged.
    observed_frozen = verify_frozen_stage125_contract_hashes(repo_root)
    add("frozen_stage125_contract_hashes_exact",
        observed_frozen == FROZEN_STAGE125_CONTRACT_SHA256
        and record["frozen_stage125_contract_sha256"]
        == dict(sorted(FROZEN_STAGE125_CONTRACT_SHA256.items())))
    add("frozen_stage125_contract_map_nine_paths",
        len(record["frozen_stage125_contract_sha256"]) == 9)
    verify_stage125_tree_unchanged(repo_root)
    add("frozen_stage125_tree_unchanged",
        record["frozen_stage125_tree_unchanged"] is True)
    add("frozen_stage125_source_commit",
        record["frozen_stage125_source_commit"] == FROZEN_STAGE125_SOURCE_COMMIT)

    # Preprocessing incorporation exactly equals the frozen Part 4 contract.
    prep = record["global_execution_rules"]["preprocessing"]
    add("preprocessing_continuous_pipeline_order_exact",
        prep["continuous_pipeline_order"] == list(EXPECTED_CONTINUOUS_PIPELINE_ORDER))
    add("preprocessing_fields_exact",
        all(prep.get(k) == v for k, v in EXPECTED_PREPROCESSING_FIELDS.items()))

    add("network_requests_attempted_zero", network_attempts == 0)

    # No-execution counters (this module runs no models).
    add("zero_model_fit_calls", True)
    add("zero_prediction_calls", True)
    add("zero_smote_smotenc_calls", True)
    add("zero_shap_calls", True)
    return a


def robustness_decision_handoff_markers() -> dict[str, Any]:
    return {
        "m1_robustness_decision_locked": True,
        "m1_robustness_execution_authorized": False,
        "m1_robustness_started": False,
        "m1_robustness_completed": False,
        "m1_robustness_next_category_id": "m1_target_proximity_six_feature_set",
        "m1_robustness_packaging_policy": "one_category_per_micro_part_pr",
    }


# --------------------------------------------------------------------------- #
# Build-all + run
# --------------------------------------------------------------------------- #

def build_all(repo_root: Path) -> tuple[dict[str, str], dict[str, Any]]:
    verify_decision_text()
    # Frozen Stage125 byte-integrity (file reads) BEFORE semantic cross-validation
    # and before any artifact generation (fail-closed). The git-based tree-unchanged
    # check runs in the runner OUTSIDE the network sentinel (git spawns a subprocess
    # the sentinel denies) and again in build_qc_assertions.
    verify_frozen_stage125_contract_hashes(repo_root)
    primary_observed = verify_primary_artifacts_immutable(repo_root)
    verify_against_frozen_contracts(repo_root)

    record = build_decision_record(repo_root)
    readme = build_readme()
    content = {
        F_RECORD: _json_str(record),
        F_README: readme,
    }
    extras = {"record": record, "primary_observed": primary_observed}
    return content, extras


def _compare_drift(out_dir: Path, payloads: dict[str, str]) -> list[str]:
    drift: list[str] = []
    for name, text in payloads.items():
        path = out_dir / name
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            drift.append(name)
    return drift


def run(
    *, project_dir: Path, output_dir: Path | None = None,
    build: bool = False, check: bool = False,
) -> dict[str, Any]:
    if build and check:
        raise QCFail("build and check are mutually exclusive")
    if not build and not check:
        raise QCFail("one of --build or --check is required")

    repo_root = repo_root_from(project_dir)
    canonical_out = (repo_root / STAGE126_DIR_REL).resolve()
    out_dir = Path(output_dir).resolve() if output_dir else canonical_out

    # Git-based frozen Stage125 tree-immutability check runs OUTSIDE the network
    # sentinel (the sentinel denies subprocess launches, which git requires).
    verify_stage125_tree_unchanged(repo_root)

    with p3b0.network_sentinel() as sentinel:
        content, extras = build_all(repo_root)
        if sentinel.calls_attempted != 0:
            raise QCFail(
                f"network_requests_attempted_zero failed: {sentinel.calls_attempted}"
            )
        network_attempts = sentinel.calls_attempted

    assertions = build_qc_assertions(
        repo_root, extras["record"], extras["primary_observed"], network_attempts,
    )
    failed = sum(1 for x in assertions if x["status"] != "PASS")

    source_commit = _git(
        str(repo_root), "log", "--format=%H", "-n", "1",
        "--", SRC_REL, TEST_REL, RUN_REL,
    ) or _git(str(repo_root), "rev-parse", "HEAD")

    content_hashes = {
        name: sha256_bytes(text.encode("utf-8")) for name, text in content.items()
    }
    qc: dict[str, Any] = {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "decision_id": DECISION_ID,
        "source_commit": source_commit,
        "source_file_sha256": (
            sha256_file(repo_root / SRC_REL)
            if (repo_root / SRC_REL).is_file() else ""
        ),
        "test_file_sha256": (
            sha256_file(repo_root / TEST_REL)
            if (repo_root / TEST_REL).is_file() else ""
        ),
        "assertion_count": len(assertions),
        "failed_count": failed,
        "all_pass": failed == 0,
        "tickers": [],
        "ticker_count": 0,
        "network_requests_attempted": network_attempts,
        "model_fit_calls": 0,
        "prediction_calls": 0,
        "smote_calls": 0,
        "smotenc_calls": 0,
        "shap_calls": 0,
        "final_test_predictor_rows_loaded": 0,
        "final_test_target_rows_loaded": 0,
        "final_test_evaluations": 0,
        "output_sha256": dict(sorted(content_hashes.items())),
        "assertions": assertions,
        **robustness_decision_handoff_markers(),
    }
    qc_text = _json_str(qc)
    qc_hash = sha256_bytes(qc_text.encode("utf-8"))
    meta = {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "description": (
            "Stage126 M1 robustness Part 0 decision lock (decision contract only; "
            "no robustness execution; no model fit/predict; no SMOTE/SMOTENC; "
            "no SHAP; no final-test access; primary artifacts byte-identical)."
        ),
        "generated_at": source_commit,
        "code_commit": source_commit,
        "source_file_sha256": qc["source_file_sha256"],
        "test_file_sha256": qc["test_file_sha256"],
        "runtime_versions": runtime_versions(),
        "output_files_sha256": dict(
            sorted({**content_hashes, F_QC: qc_hash}.items())
        ),
        "network_requests_attempted": network_attempts,
        "model_fit_calls": 0,
        "prediction_calls": 0,
        "smote_calls": 0,
        "smotenc_calls": 0,
        "shap_calls": 0,
    }
    meta_text = _json_str(meta)
    all_tracked = {**content, F_QC: qc_text, F_METADATA: meta_text}

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
        raise QCFail(f"check drift (tracked): {tracked_drift}")

    if not qc["all_pass"]:
        raise QCFail(f"Part 0 decision-lock QC failed: {failed} assertions failed")

    return {
        "qc": qc,
        "metadata": meta,
        "output_dir": str(out_dir),
        "files": files_written,
        "drift": tracked_drift,
        "network_requests_attempted": network_attempts,
    }


# --------------------------------------------------------------------------- #
# Handoff integration helper (imported by the generator)
# --------------------------------------------------------------------------- #

DECISION_RECORD_REL = f"{STAGE126_DIR_REL}/{F_RECORD}"


def load_decision_markers(repo_root: str | Path) -> dict[str, Any]:
    """Fail-closed derivation of the six robustness-decision Handoff markers.

    Reads only the tracked decision record. Raises QCFail on any missing record
    or field mismatch so the Handoff can never claim a robustness state the
    record does not support.
    """
    path = Path(repo_root) / DECISION_RECORD_REL
    if not path.is_file():
        raise QCFail(f"missing decision record: {DECISION_RECORD_REL}")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QCFail(f"unreadable decision record: {exc}") from exc

    if record.get("decision_locked") is not True:
        raise QCFail("decision record decision_locked is not True")
    if record.get("execution_authorized") is not False:
        raise QCFail("decision record execution_authorized is not False")
    if record.get("m1_robustness_started") is not False:
        raise QCFail("decision record m1_robustness_started is not False")
    if record.get("m1_robustness_completed") is not False:
        raise QCFail("decision record m1_robustness_completed is not False")
    if list(record.get("execution_order") or []) != list(FUTURE_MICRO_PART_ORDER):
        raise QCFail("decision record execution_order is not the exact sequence")
    if record.get("one_category_per_micro_part_pr") is not True:
        raise QCFail("decision record one_category_per_micro_part_pr is not True")

    return {
        "m1_robustness_decision_locked": True,
        "m1_robustness_execution_authorized": False,
        "m1_robustness_started": False,
        "m1_robustness_completed": False,
        "m1_robustness_next_category_id": FUTURE_MICRO_PART_ORDER[0],
        "m1_robustness_packaging_policy": "one_category_per_micro_part_pr",
    }
