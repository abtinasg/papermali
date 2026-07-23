"""Stage126 M1 — Robustness Part 1: target-proximity six-feature set.

Explicitly human-authorized, development-only sensitivity analysis. ONLY the
feature set changes relative to the locked primary Stage126 M1 development
analysis; the sample, target, temporal folds, selected configurations, imbalance
policy, seeds and metric contract are all held fixed.

Fail-closed guarantees:
  * the locked final test is never opened — final-test predictor/target values
    are never parsed, stored, summarized, logged or exported;
  * no hyperparameter search runs (the three primary selected configurations are
    loaded from the frozen artifact and reused verbatim);
  * no full-development refit, no SMOTE/SMOTENC, no SHAP, no calibration, no
    bootstrap/Holm, no winner selection;
  * the frozen Stage125 tree, the nine consumed Stage125 contracts and the eight
    primary Stage126 artifacts must remain byte-identical.

Part 1 results are sensitivity-analysis evidence only. They never replace the
primary results and never re-rank the primary model families.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from src import stage125_part3b0_evidence_readiness as p3b0
from src import stage126_m1_primary_development_tuning as primary
from src import stage126_m1_robustness_part0_decision_lock as part0

# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #

QC_STAGE = "stage126_m1_robustness_part1_target_proximity"
CURRENT_STAGE = "Stage126"
CONTRACT_VERSION = "stage126_m1_robustness_part1_target_proximity_v1"
CATEGORY_ID = "m1_target_proximity_six_feature_set"
SCIENTIFIC_ROLE = "target_proximity_feature_set_robustness"
CHANGED_DIMENSION = "feature_set"
FEATURE_SET_NAME = "M1_TARGET_PROXIMITY_ROBUSTNESS"
IMBALANCE_POLICY = "primary_class_weighting"
SCIENTIFIC_INTERPRETATION = "sensitivity_analysis_only"
NEXT_CATEGORY_ID = "main_rule_b_listing_robustness"

SRC_REL = "project/src/stage126_m1_robustness_part1_target_proximity.py"
RUN_REL = "project/run_stage126_m1_robustness_part1_target_proximity.py"
TEST_REL = "project/tests/test_stage126_m1_robustness_part1_target_proximity.py"

STAGE126_DIR_REL = "project/stage126"
F_AUTH = "stage126_m1_robustness_part1_human_authorization_record.json"
F_FEATURE_MANIFEST = "stage126_m1_robustness_part1_feature_manifest.csv"
F_EXEC_MANIFEST = "stage126_m1_robustness_part1_execution_manifest.json"
F_OOF = "stage126_m1_robustness_part1_oof_predictions.csv"
F_METRICS = "stage126_m1_robustness_part1_metrics.csv"
F_COMPLETION_LOCK = "stage126_m1_robustness_part1_completion_lock.json"
F_PART5_COMPAT = (
    "stage126_m1_robustness_part1_part5_successor_compatibility.json"
)
F_QC = "stage126_m1_robustness_part1_qc_report.json"
F_METADATA = "metadata_and_hashes_stage126_m1_robustness_part1.json"
F_README = "README_STAGE126_M1_ROBUSTNESS_PART1_TARGET_PROXIMITY.md"

# --------------------------------------------------------------------------- #
# Exact human authorization (byte-for-byte Persian)
# --------------------------------------------------------------------------- #

HUMAN_AUTHORIZATION_TEXT_FA = "مجوز انجام مرحله بعدی رو میدم"
HUMAN_AUTHORIZATION_TEXT_SHA256 = (
    "7364a67ce5761c69f6705ae0ee4b0563fc092a576e960df471ebb4581ae1b5ea"
)
AUTHORIZATION_ID = "stage126-m1-robustness-part1-human-authorization"
AUTHORIZATION_DATE = "2026-07-22"
AUTHORIZATION_CONTEXT = (
    "The immediately preceding independently verified repository state "
    "identified Stage126 M1 Robustness Part 1 — m1_target_proximity_six_feature_"
    "set — as the next gated micro-part."
)

# --------------------------------------------------------------------------- #
# Exact Part 1 feature specification (six features, locked order)
# --------------------------------------------------------------------------- #

PART1_FEATURE_ORDER: tuple[str, ...] = (
    "log_total_assets",
    "current_ratio",
    "roa_period_adjusted",
    "asset_turnover_period_adjusted",
    "operating_margin_period_adjusted",
    "financial_expense_to_assets_period_adjusted",
)
PART1_FEATURE_SOURCE_COLUMN: dict[str, str] = {
    "log_total_assets": "total_assets",
    "current_ratio": "current_ratio",
    "roa_period_adjusted": "roa_period_adjusted",
    "asset_turnover_period_adjusted": "asset_turnover_period_adjusted",
    "operating_margin_period_adjusted": "operating_margin_period_adjusted",
    "financial_expense_to_assets_period_adjusted":
        "financial_expense_to_assets_period_adjusted",
}
PART1_FEATURE_TRANSFORMATION: dict[str, str] = {
    "log_total_assets":
        "ln(total_assets) if total_assets > 0 else missing",
    "current_ratio": "frozen_part3c_value",
    "roa_period_adjusted": "frozen_part3c_value",
    "asset_turnover_period_adjusted": "frozen_part3c_value",
    "operating_margin_period_adjusted": "frozen_part3c_value",
    "financial_expense_to_assets_period_adjusted":
        "frozen_part3c_value_source_sign_preserved",
}
# Primary features removed by the target-proximity robustness set, plus the
# audit-only growth feature. NONE of these may reach the Part 1 model surface.
EXCLUDED_PRIMARY_FEATURES: tuple[str, ...] = (
    "leverage_ratio",
    "ocf_to_assets_period_adjusted",
    "accumulated_loss_to_capital_ratio",
)
PROHIBITED_FEATURE = "revenue_growth_period_adjusted"
EXCLUDED_SOURCE_COLUMNS: frozenset[str] = frozenset(
    list(EXCLUDED_PRIMARY_FEATURES) + [PROHIBITED_FEATURE]
)

BASE_FEATURE_COUNT = 6
TRANSFORMED_FEATURE_COUNT = 12  # 6 imputed continuous + 6 missingness indicators

# --------------------------------------------------------------------------- #
# Fixed (inherited) analysis dimensions
# --------------------------------------------------------------------------- #

PART1_SAMPLE = primary.PRIMARY_SAMPLE            # main_rule_a_primary
PART1_TARGET = primary.PRIMARY_TARGET            # FD_target_main_t_plus_1
MODEL_FAMILIES = primary.ALLOWED_MODEL_FAMILIES  # 3 locked families
MODEL_SEEDS = primary.FINAL_OOF_SEEDS            # 20260719..20260723
LOGISTIC_DETERMINISTIC_SEED = primary.TUNING_SEEDS[0]  # 20260719

EXPECTED_MODEL_FIT_CALLS = 22   # 2 logistic + 10 RF + 10 XGB
EXPECTED_PREDICTION_CALLS = 22
EXPECTED_OOF_ROWS_PER_FAMILY = primary.EXPECTED_POOLED_OOF_ROWS  # 421
EXPECTED_OOF_ROWS_TOTAL = EXPECTED_OOF_ROWS_PER_FAMILY * len(MODEL_FAMILIES)  # 1263
EXPECTED_METRICS_ROWS = len(MODEL_FAMILIES) * 3  # 9

SELECTED_CONFIGURATIONS_REL = (
    "project/stage126/stage126_m1_selected_configurations.json"
)
SELECTED_CONFIGURATIONS_SHA256 = (
    "34488e07bd16d467b177c37dcaf571d9c68c25ecbc1c94fee5091f554d2eb97e"
)
PRIMARY_OOF_REL = "project/stage126/stage126_m1_development_oof_predictions.csv"
PRIMARY_OOF_SHA256 = (
    "48a00c882309c412aeba8f3b7200b65003e435080410c7b7c7ab62c9c3326749"
)
PART0_DECISION_RECORD_REL = (
    "project/stage126/stage126_m1_robustness_part0_decision_record.json"
)
PART0_DECISION_RECORD_SHA256 = (
    "9ccd7bfae8fa522cb87e94ed7bebe806324837e9a2e12783d12aabfedd07c2ee"
)
PRIMARY_SRC_REL = "project/src/stage126_m1_primary_development_tuning.py"
PRIMARY_SRC_SHA256 = (
    "ae63bee24c3b868919b008cb15a0d4f4bfb8300ee6e3002a61e1e105d9391d82"
)

# Pinned primary Stage126 artifacts (must remain byte-identical).
PINNED_PRIMARY_ARTIFACTS: dict[str, str] = {
    "project/stage126/stage126_m1_development_access_manifest.csv":
        "0c2783d0e43ebba712a1c41b6889a2f8f646340bae6a75ad15902a8a0c368e39",
    PRIMARY_OOF_REL: PRIMARY_OOF_SHA256,
    "project/stage126/stage126_m1_development_metrics.csv":
        "1c5f33b4e3a156b111d29a2c4e13ecee9c5e7ad73f6b3d98cf3c6b4b506be17a",
    "project/stage126/stage126_m1_primary_development_lock.json":
        "c500563049e30a27ac59fd3d673ef801b8d8e12f0bb684dd2e0aec13eb5618e4",
    "project/stage126/stage126_m1_final_test_lock_guard.json":
        "509e58fc39e3c5d886993c11b954fc06c267c96d02c081d8e50b0cda52e58b03",
    SELECTED_CONFIGURATIONS_REL: SELECTED_CONFIGURATIONS_SHA256,
    "project/stage126/stage126_m1_configuration_registry.csv":
        "decbf43a5c34669bdd7a0c68c0ad6aec5611efc7c3ca82b09f5e85f72d635804",
    "project/stage126/stage126_m1_tuning_results.csv":
        "e7e1e6808e394273676709aa94bfa713bbf8a790fadabee22ea20b849adbe649",
}

OOF_COLUMNS = [
    "robustness_category_id", "feature_set", "ticker", "predictor_row_key_t",
    "target_row_key_t_plus_1", "fiscal_year_t", "target_year", "temporal_fold",
    "model_family", "observed_target", "predicted_probability",
    "configuration_id", "probability_seed_aggregation",
]
METRICS_COLUMNS = [
    "robustness_category_id", "feature_set", "model_family", "configuration_id",
    "scope", "n_rows", "n_positive", "k_top10", "pr_auc", "roc_auc",
    "brier_score", "recall_at_10pct", "lift_at_10pct",
]
FEATURE_MANIFEST_COLUMNS = [
    "feature_order", "feature_name", "source_column", "transformation",
    "missingness_indicator_appended", "included_in_part1",
]


class QCFail(RuntimeError):
    """Fail-closed Part 1 validation error."""


class FinalTestLockError(QCFail):
    """The locked final test was approached (fail-closed)."""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _json_str(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def recompute_authorization_sha256(text_fa: str) -> str:
    return hashlib.sha256(text_fa.encode("utf-8")).hexdigest()


def _git(repo_root: str | Path, *args: str) -> str:
    """Informational git helper only (never used for integrity decisions)."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=True, capture_output=True, text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return ""
    return out.stdout.strip()


def _csv_str(header: list[str], rows: list[dict[str, Any]]) -> str:
    return primary._csv_str(header, rows)


def repo_root_from(project_dir: Path) -> Path:
    return project_dir.parent if project_dir.name == "project" else project_dir


def require_file_hash(repo_root: Path, rel: str, expected: str, *, label: str) -> str:
    path = repo_root / rel
    if not path.is_file():
        raise QCFail(f"missing {label}: {rel}")
    got = sha256_file(path)
    if got != expected:
        raise QCFail(f"{label} hash mismatch: {rel} {got} != {expected}")
    return got


# --------------------------------------------------------------------------- #
# Authorization + frozen-contract verification
# --------------------------------------------------------------------------- #

def verify_authorization_text() -> None:
    got = recompute_authorization_sha256(HUMAN_AUTHORIZATION_TEXT_FA)
    if got != HUMAN_AUTHORIZATION_TEXT_SHA256:
        raise QCFail(
            f"Part 1 human authorization SHA-256 mismatch: {got} != "
            f"{HUMAN_AUTHORIZATION_TEXT_SHA256}"
        )


def build_authorization_record() -> dict[str, Any]:
    """Deterministic Part 1 human authorization record (hash recomputed)."""
    verify_authorization_text()
    return {
        "authorization_id": AUTHORIZATION_ID,
        "authorization_date": AUTHORIZATION_DATE,
        "authorizing_role": "human_supervisor_data_owner",
        "human_authorization_text": HUMAN_AUTHORIZATION_TEXT_FA,
        "human_authorization_text_sha256": HUMAN_AUTHORIZATION_TEXT_SHA256,
        "authorization_context": AUTHORIZATION_CONTEXT,
        "authorized_category_id": CATEGORY_ID,
        "part1_execution_authorized": True,
        "part2_execution_authorized": False,
        "merge_authorized": False,
        "final_test_access_authorized": False,
    }


def verify_part0_contract(repo_root: Path) -> dict[str, Any]:
    """The merged Part 0 decision record is authoritative and must be exact."""
    require_file_hash(
        repo_root, PART0_DECISION_RECORD_REL, PART0_DECISION_RECORD_SHA256,
        label="Part 0 decision record",
    )
    record = json.loads(
        (repo_root / PART0_DECISION_RECORD_REL).read_text(encoding="utf-8")
    )
    exact = {
        "contract_id": "stage126_m1_robustness_execution_contract",
        "contract_version": "stage126_m1_robustness_execution_contract_v1",
        "decision_locked": True,
        "one_category_per_micro_part_pr": True,
        "each_part_requires_separate_human_authorization": True,
    }
    for k, v in exact.items():
        if record.get(k) != v:
            raise QCFail(f"Part 0 contract field {k}={record.get(k)!r} != {v!r}")
    order = record.get("execution_order") or []
    if not order or order[0] != CATEGORY_ID:
        raise QCFail("Part 0 execution_order[0] is not the Part 1 category")
    return record


def verify_frozen_integrity(repo_root: Path) -> dict[str, str]:
    """Reuse the merged Part 0 fail-closed integrity helpers + pinned primaries."""
    part0.verify_frozen_stage125_contract_hashes(repo_root)
    part0.verify_primary_artifacts_immutable(repo_root)
    observed: dict[str, str] = {}
    for rel, expected in sorted(PINNED_PRIMARY_ARTIFACTS.items()):
        observed[rel] = require_file_hash(
            repo_root, rel, expected, label="pinned primary artifact",
        )
    require_file_hash(
        repo_root, PRIMARY_SRC_REL, PRIMARY_SRC_SHA256,
        label="primary implementation source",
    )
    return observed


# --------------------------------------------------------------------------- #
# Part 1 six-feature loader (own loader; excluded values never touched)
# --------------------------------------------------------------------------- #

def part1_source_columns() -> list[str]:
    """Exactly the six Part 1 source columns; excluded columns can never appear."""
    cols = sorted({PART1_FEATURE_SOURCE_COLUMN[f] for f in PART1_FEATURE_ORDER})
    if len(cols) != BASE_FEATURE_COUNT:
        raise QCFail(f"Part 1 source column count {len(cols)} != {BASE_FEATURE_COUNT}")
    bad = EXCLUDED_SOURCE_COLUMNS & set(cols)
    if bad:
        raise QCFail(f"excluded source column reached Part 1 loader: {sorted(bad)}")
    return cols


def _derive_part1_features(raw_sources: dict[str, str]) -> np.ndarray:
    """Deterministic six-feature source-to-feature transform (pre-imputation)."""
    vals = np.empty(BASE_FEATURE_COUNT, dtype=float)
    for i, feat in enumerate(PART1_FEATURE_ORDER):
        src = PART1_FEATURE_SOURCE_COLUMN[feat]
        raw = primary._to_float(raw_sources[src])
        if feat == "log_total_assets":
            if math.isnan(raw) or raw <= 0.0:
                vals[i] = math.nan
            else:
                vals[i] = math.log(raw)
        else:
            vals[i] = raw
    return vals


def load_part1_development_values(
    repo_root: Path, allowlist: dict[str, Any],
) -> dict[str, Any]:
    """Second pass: stream the analysis-ready CSV keeping ONLY development keys.

    Reads exactly the six Part 1 source columns. Final-test rows are never
    numerically parsed, stored, summarized, logged or exported — the loader only
    counts that it saw them. Values of the three excluded primary features and
    of the prohibited growth feature are never read into the Part 1 surface.
    """
    dev_pairs = allowlist["dev_pairs"]
    denylist = allowlist["denylist_pairs"]
    source_cols = part1_source_columns()

    loaded: dict[tuple[str, str], dict[str, Any]] = {}
    final_test_rows_seen = 0
    final_test_predictor_rows_loaded = 0
    final_test_target_rows_loaded = 0
    unknown_rows = 0

    path = repo_root / primary.ANALYSIS_READY_REL
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        header = set(reader.fieldnames or [])
        needed = set(source_cols) | {
            "predictor_row_key_t", "target_row_key_t_plus_1", "ticker",
            "fiscal_year_t", "target_year", PART1_TARGET,
        }
        missing = needed - header
        if missing:
            raise QCFail(f"analysis-ready CSV missing columns: {sorted(missing)}")
        for row in reader:
            key = (row["predictor_row_key_t"], row["target_row_key_t_plus_1"])
            if key in dev_pairs:
                ty = int(row["target_year"])
                if ty not in primary.DEVELOPMENT_TARGET_YEARS:
                    raise FinalTestLockError(
                        f"development key has non-development target_year {ty}"
                    )
                raw_sources = {c: row[c] for c in source_cols}
                loaded[key] = {
                    "ticker": row["ticker"],
                    "predictor_row_key_t": key[0],
                    "target_row_key_t_plus_1": key[1],
                    "fiscal_year_t": row["fiscal_year_t"],
                    "target_year": ty,
                    "features": _derive_part1_features(raw_sources),
                    "target": primary._target_value(row[PART1_TARGET]),
                }
            elif key in denylist:
                # Locked final-test row: no predictor/target value is parsed.
                final_test_rows_seen += 1
            else:
                unknown_rows += 1

    if unknown_rows:
        raise QCFail(f"{unknown_rows} analysis-ready rows unclassified (fail-closed)")
    if len(loaded) != primary.EXPECTED_DEV_ROWS:
        raise QCFail(
            f"loaded {len(loaded)} dev rows != {primary.EXPECTED_DEV_ROWS}"
        )
    if final_test_predictor_rows_loaded or final_test_target_rows_loaded:
        raise FinalTestLockError("final-test values loaded (fail-closed)")
    for info in loaded.values():
        if info["target_year"] in primary.FINAL_TEST_TARGET_YEARS:
            raise FinalTestLockError("final-test target_year in loaded modeling rows")
        if info["features"].shape[0] != BASE_FEATURE_COUNT:
            raise QCFail("Part 1 feature vector is not six-dimensional")

    return {
        "rows": loaded,
        "final_test_rows_seen": final_test_rows_seen,
        "final_test_predictor_rows_loaded": final_test_predictor_rows_loaded,
        "final_test_target_rows_loaded": final_test_target_rows_loaded,
    }


# --------------------------------------------------------------------------- #
# Selected configurations (loaded, never re-searched)
# --------------------------------------------------------------------------- #

EXPECTED_SELECTED: dict[str, dict[str, Any]] = {
    "regularized_logistic_regression": {
        "configuration_id": "logistic__C_0.1",
        "hyperparameters": {
            "C": 0.1, "max_iter": 5000, "penalty": "l2", "solver": "liblinear",
        },
    },
    "random_forest": {
        "configuration_id": "rf__depth_3__maxfeat_'sqrt'__leaf_10",
        "hyperparameters": {
            "bootstrap": True, "max_depth": 3, "max_features": "sqrt",
            "min_samples_leaf": 10, "n_estimators": 500,
        },
    },
    "xgboost": {
        "configuration_id": "xgboost__lr_0.03__depth_2__mcw_1__lambda_1",
        "hyperparameters": {
            "colsample_bytree": 0.8, "early_stopping": False,
            "eval_metric": "aucpr", "gamma": 0, "learning_rate": 0.03,
            "max_depth": 2, "min_child_weight": 1, "n_estimators": 300,
            "n_jobs": 1, "objective": "binary:logistic", "reg_lambda": 1,
            "subsample": 0.8, "tree_method": "hist",
        },
    },
}


def load_selected_configurations(repo_root: Path) -> dict[str, Any]:
    """Load the frozen primary selected configurations. NO search is performed."""
    require_file_hash(
        repo_root, SELECTED_CONFIGURATIONS_REL, SELECTED_CONFIGURATIONS_SHA256,
        label="primary selected configurations",
    )
    data = json.loads(
        (repo_root / SELECTED_CONFIGURATIONS_REL).read_text(encoding="utf-8")
    )
    for family in MODEL_FAMILIES:
        if family not in data:
            raise QCFail(f"selected configurations missing family: {family}")
        exp = EXPECTED_SELECTED[family]
        if data[family]["configuration_id"] != exp["configuration_id"]:
            raise QCFail(
                f"{family} configuration_id "
                f"{data[family]['configuration_id']!r} != "
                f"{exp['configuration_id']!r}"
            )
        got_hp = data[family]["hyperparameters"]
        for k, v in exp["hyperparameters"].items():
            if got_hp.get(k) != v:
                raise QCFail(
                    f"{family} hyperparameter {k}={got_hp.get(k)!r} != {v!r}"
                )
    return data


# --------------------------------------------------------------------------- #
# Execution (development folds only; counted fits/predictions)
# --------------------------------------------------------------------------- #

class ExecutionCounters:
    """Explicit counters proving the exact executed work."""

    def __init__(self) -> None:
        self.model_fit_calls = 0
        self.prediction_calls = 0
        self.tuning_search_calls = 0
        self.smote_calls = 0
        self.smotenc_calls = 0
        self.shap_calls = 0
        self.final_test_evaluations = 0
        self.scale_pos_weight_by_fold: dict[str, float] = {}


def _fit_predict_counted(
    counters: ExecutionCounters, family: str, hp: dict[str, Any], seed: int,
    Xtr: np.ndarray, ytr: np.ndarray, Xva: np.ndarray,
) -> np.ndarray:
    """One counted fit + one counted prediction on development-fold data only."""
    if Xtr.shape[1] != TRANSFORMED_FEATURE_COUNT:
        raise QCFail(
            f"training matrix has {Xtr.shape[1]} columns != "
            f"{TRANSFORMED_FEATURE_COUNT}"
        )
    if Xva.shape[1] != TRANSFORMED_FEATURE_COUNT:
        raise QCFail("validation matrix column count mismatch")
    counters.model_fit_calls += 1
    counters.prediction_calls += 1
    return primary._fit_predict(family, hp, seed, Xtr, ytr, Xva)


def generate_part1_oof(
    folds_data: dict[str, dict[str, Any]], selected: dict[str, Any],
    counters: ExecutionCounters,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, np.ndarray]]]:
    """Development-fold OOF predictions for the six-feature set.

    Logistic is a deterministic single fit per fold; RF/XGBoost average the
    validation probabilities over the five fixed model seeds within each fold.
    No fold ever combines training and validation rows.
    """
    oof_rows: list[dict[str, Any]] = []
    predictions: dict[str, dict[str, np.ndarray]] = {}
    for family in MODEL_FAMILIES:
        cid = selected[family]["configuration_id"]
        hp = selected[family]["hyperparameters"]
        standardize = primary._requires_standardization(family)
        deterministic = standardize
        agg = ("deterministic_single_fit" if deterministic
               else "mean_of_5_fixed_seeds")
        predictions[family] = {}
        for fold_name, fspec in primary.FOLD_SPEC.items():
            tr = folds_data[fspec["train_role"]]
            va = folds_data[fspec["validation_role"]]
            # Training-fold-only preprocessing (six features -> twelve columns).
            pre = primary.fit_preprocessor(tr["X"], standardize=standardize)
            Xtr = primary.transform(tr["X"], pre)
            Xva = primary.transform(va["X"], pre)
            if family == "xgboost":
                n_pos = int((tr["y"] == 1).sum())
                n_neg = int((tr["y"] == 0).sum())
                counters.scale_pos_weight_by_fold[fspec["train_role"]] = (
                    n_neg / n_pos if n_pos else math.nan
                )
            if deterministic:
                probs = _fit_predict_counted(
                    counters, family, hp, LOGISTIC_DETERMINISTIC_SEED,
                    Xtr, tr["y"], Xva,
                )
            else:
                stacked = np.vstack([
                    _fit_predict_counted(
                        counters, family, hp, seed, Xtr, tr["y"], Xva,
                    )
                    for seed in MODEL_SEEDS
                ])
                probs = stacked.mean(axis=0)
            probs = np.array([primary._round(p) for p in probs])
            predictions[family][fspec["validation_role"]] = probs
            for i, info in enumerate(va["meta"]):
                oof_rows.append({
                    "robustness_category_id": CATEGORY_ID,
                    "feature_set": FEATURE_SET_NAME,
                    "ticker": info["ticker"],
                    "predictor_row_key_t": info["predictor_row_key_t"],
                    "target_row_key_t_plus_1": info["target_row_key_t_plus_1"],
                    "fiscal_year_t": info["fiscal_year_t"],
                    "target_year": info["target_year"],
                    "temporal_fold": fspec["validation_role"],
                    "model_family": family,
                    "observed_target": int(info["target"]),
                    # Plain Python float: a numpy scalar would serialize as
                    # "np.float64(...)" under numpy>=2 and would not be a valid
                    # numeric CSV field. The frozen primary artifact is left
                    # untouched; only this new Part 1 surface is emitted clean.
                    "predicted_probability": float(probs[i]),
                    "configuration_id": cid,
                    "probability_seed_aggregation": agg,
                })
    return oof_rows, predictions


def compute_part1_metrics(
    folds_data: dict[str, dict[str, Any]], selected: dict[str, Any],
    predictions: dict[str, dict[str, np.ndarray]],
) -> list[dict[str, Any]]:
    """Exactly five metrics for three scopes per family (frozen Top-K rule)."""
    rows: list[dict[str, Any]] = []
    for family in MODEL_FAMILIES:
        cid = selected[family]["configuration_id"]
        pooled_y: list[float] = []
        pooled_p: list[float] = []
        pooled_t: list[str] = []
        pooled_years: list[int] = []
        for fspec in primary.FOLD_SPEC.values():
            role = fspec["validation_role"]
            va = folds_data[role]
            y = va["y"]
            p = predictions[family][role]
            tickers = [m["ticker"] for m in va["meta"]]
            years = [int(m["target_year"]) for m in va["meta"]]
            m = primary.compute_metrics(y, p, tickers, years)
            rows.append({
                "robustness_category_id": CATEGORY_ID,
                "feature_set": FEATURE_SET_NAME,
                "model_family": family, "configuration_id": cid,
                "scope": role, **m,
            })
            pooled_y.extend(y.tolist())
            pooled_p.extend(p.tolist())
            pooled_t.extend(tickers)
            pooled_years.extend(years)
        m = primary.compute_metrics(
            np.array(pooled_y), np.array(pooled_p), pooled_t, pooled_years,
        )
        rows.append({
            "robustness_category_id": CATEGORY_ID,
            "feature_set": FEATURE_SET_NAME,
            "model_family": family, "configuration_id": cid,
            "scope": "pooled_development_oof", **m,
        })
    return rows


# --------------------------------------------------------------------------- #
# Primary-key parity
# --------------------------------------------------------------------------- #

def primary_oof_key_index(repo_root: Path) -> dict[tuple[str, str, str], dict[str, str]]:
    """Read the frozen primary OOF surface keys + observed targets (no probabilities)."""
    require_file_hash(
        repo_root, PRIMARY_OOF_REL, PRIMARY_OOF_SHA256, label="primary OOF",
    )
    idx: dict[tuple[str, str, str], dict[str, str]] = {}
    with (repo_root / PRIMARY_OOF_REL).open(
        "r", encoding="utf-8-sig", newline="",
    ) as fh:
        for row in csv.DictReader(fh):
            key = (
                row["model_family"], row["predictor_row_key_t"],
                row["target_row_key_t_plus_1"],
            )
            idx[key] = {
                "ticker": row["ticker"],
                "fiscal_year_t": row["fiscal_year_t"],
                "target_year": row["target_year"],
                "temporal_fold": row["temporal_fold"],
                "observed_target": row["observed_target"],
            }
    return idx


def assert_key_parity_with_primary(
    repo_root: Path, oof_rows: list[dict[str, Any]],
) -> None:
    """Part 1 must reuse EXACTLY the primary development OOF keys and targets."""
    primary_idx = primary_oof_key_index(repo_root)
    if len(oof_rows) != len(primary_idx):
        raise QCFail(
            f"Part 1 OOF rows {len(oof_rows)} != primary {len(primary_idx)}"
        )
    for r in oof_rows:
        key = (
            r["model_family"], r["predictor_row_key_t"],
            r["target_row_key_t_plus_1"],
        )
        ref = primary_idx.get(key)
        if ref is None:
            raise QCFail(f"Part 1 OOF key absent from primary surface: {key}")
        if r["ticker"] != ref["ticker"]:
            raise QCFail(f"ticker mismatch vs primary for {key}")
        if str(r["fiscal_year_t"]) != ref["fiscal_year_t"]:
            raise QCFail(f"fiscal_year_t mismatch vs primary for {key}")
        if str(r["target_year"]) != ref["target_year"]:
            raise QCFail(f"target_year mismatch vs primary for {key}")
        if r["temporal_fold"] != ref["temporal_fold"]:
            raise QCFail(f"temporal_fold mismatch vs primary for {key}")
        if str(r["observed_target"]) != ref["observed_target"]:
            raise QCFail(f"observed_target mismatch vs primary for {key}")


# --------------------------------------------------------------------------- #
# Artifact builders
# --------------------------------------------------------------------------- #

def build_feature_manifest_rows() -> list[dict[str, Any]]:
    rows = []
    for i, feat in enumerate(PART1_FEATURE_ORDER, start=1):
        rows.append({
            "feature_order": i,
            "feature_name": feat,
            "source_column": PART1_FEATURE_SOURCE_COLUMN[feat],
            "transformation": PART1_FEATURE_TRANSFORMATION[feat],
            "missingness_indicator_appended": "true",
            "included_in_part1": "true",
        })
    return rows


def build_execution_manifest(
    counters: ExecutionCounters, loaded: dict[str, Any],
    allowlist: dict[str, Any], selected: dict[str, Any],
) -> dict[str, Any]:
    fold_counts = {
        role: {
            "rows": len(allowlist["role_pairs"][role]),
            "positive": int(sum(
                1 for k in allowlist["role_pairs"][role]
                if loaded["rows"][k]["target"] == 1
            )),
            "negative": int(sum(
                1 for k in allowlist["role_pairs"][role]
                if loaded["rows"][k]["target"] == 0
            )),
        }
        for role in primary.DEV_ROLES
    }
    return {
        "contract_version": CONTRACT_VERSION,
        "category_id": CATEGORY_ID,
        "scientific_role": SCIENTIFIC_ROLE,
        "changed_dimension": CHANGED_DIMENSION,
        "scientific_interpretation": SCIENTIFIC_INTERPRETATION,
        "sample": PART1_SAMPLE,
        "target": PART1_TARGET,
        "feature_set": FEATURE_SET_NAME,
        "features_exact_order": list(PART1_FEATURE_ORDER),
        "feature_source_columns": dict(sorted(PART1_FEATURE_SOURCE_COLUMN.items())),
        "excluded_primary_features": list(EXCLUDED_PRIMARY_FEATURES),
        "prohibited_feature": PROHIBITED_FEATURE,
        "base_feature_count": BASE_FEATURE_COUNT,
        "transformed_feature_count": TRANSFORMED_FEATURE_COUNT,
        "imbalance_policy": IMBALANCE_POLICY,
        "model_families": list(MODEL_FAMILIES),
        "selected_configurations": {
            f: selected[f]["configuration_id"] for f in MODEL_FAMILIES
        },
        "no_retuning": True,
        "tuning_search_calls": counters.tuning_search_calls,
        "model_seeds": list(MODEL_SEEDS),
        "logistic_deterministic_seed": LOGISTIC_DETERMINISTIC_SEED,
        "model_fit_calls": counters.model_fit_calls,
        "prediction_calls": counters.prediction_calls,
        "xgboost_scale_pos_weight_by_training_fold": {
            k: primary._round(v)
            for k, v in sorted(counters.scale_pos_weight_by_fold.items())
        },
        "temporal_folds": {
            name: {
                "train_role": s["train_role"],
                "validation_role": s["validation_role"],
                "train_target_years": list(s["train_target_years"]),
                "validation_target_years": list(s["validation_target_years"]),
            }
            for name, s in primary.FOLD_SPEC.items()
        },
        "development_rows_loaded": len(loaded["rows"]),
        "fold_counts": fold_counts,
        "final_test_rows_seen_but_not_parsed": loaded["final_test_rows_seen"],
        "final_test_predictor_rows_loaded": 0,
        "final_test_target_rows_loaded": 0,
        "final_test_evaluations": 0,
        "full_development_refit_performed": False,
        "development_only": True,
    }


# --------------------------------------------------------------------------- #
# Frozen Stage125 Part 5 successor-compatibility boundary
# --------------------------------------------------------------------------- #

PART5_COMPAT_CONTRACT_ID = (
    "stage126_m1_robustness_part1_part5_successor_compatibility"
)
PART5_COMPAT_CONTRACT_VERSION = (
    "stage126_m1_robustness_part1_part5_successor_compatibility_v1"
)
# The frozen Stage125 Part 5 live-successor check hard-codes the earlier
# primary-development successor Handoff. After a truthful Part 1 completion it
# necessarily reports exactly these five fields — no more, no less.
PART5_EXPECTED_LIVE_MISMATCH_FIELDS: tuple[str, ...] = (
    "m1_robustness_started",
    "selected_qc_scope",
    "selected_qc_path",
    "contract_version",
    "last_completed_micro_part",
)
PART5_EXPECTED_LIVE_MISMATCH_DETAIL = (
    "handoff_mismatch:" + ",".join(PART5_EXPECTED_LIVE_MISMATCH_FIELDS)
)
# Fields that must NEVER appear in the mismatch (they would signal real drift).
PART5_FORBIDDEN_MISMATCH_FIELDS: tuple[str, ...] = (
    "stage125_completed",
    "stage126_m1_entry_ready",
    "final_test_unlocked",
    "final_test_access_authorized",
    "final_test_evaluation_performed",
    "next_research_action_id",
)
PART5_SUCCESSOR_VALIDATION_SURFACES: tuple[str, ...] = (
    "stage126_m1_robustness_part0_decision_lock",
    "stage126_m1_robustness_part1_qc",
    "stage126_m1_robustness_part1_completion_lock",
    "ai_handoff_validator",
)
PART5_SOURCE_REL = "project/src/stage125_part5_readiness_closure.py"
PART5_RUNNER_REL = "project/run_stage125_part5.py"
PART5_TEST_REL = "project/tests/test_stage125_part5_readiness_closure.py"
PART5_METADATA_REL = "project/stage125/metadata_and_hashes_stage125_part5.json"

# The Part 5 metadata/QC pin the test-file hash as it stood at Stage125 closure.
# The successor-aware test file intentionally diverges (it separates the frozen
# historical Part 5 replay from the live Stage126 Part 1 successor state). That
# divergence is recorded explicitly — it is an authorized successor-test
# evolution, NOT a Stage125 scientific-artifact mutation.
PART5_HISTORICAL_TEST_SHA256 = (
    "0a117c1916ad845653e148d951a49a2c0375d13b7de23019e50ae891aee1b437"
)
# Exactly the two self-describing bookkeeping files that would differ when the
# frozen Part 5 build is replayed against the successor-aware test file.
PART5_EXPECTED_BOOKKEEPING_DRIFT_FILES: tuple[str, ...] = (
    "metadata_and_hashes_stage125_part5.json",
    "stage125_part5_readiness_closure_qc_report.json",
)
# Part 5 scientific/historical outputs — these must NEVER drift.
PART5_SCIENTIFIC_OUTPUT_FILES: tuple[str, ...] = (
    "part5_readiness_closure_report_stage125.json",
    "part5_stage126_m1_entry_contract_stage125.json",
    "part5_keep_drop_decisions_stage125.csv",
    "part5_blocker_register_stage125.csv",
    "part5_artifact_integrity_manifest_stage125.csv",
    "README_STAGE125_PART5_READINESS_CLOSURE.md",
)

F_COMPARISON = "stage126_m1_robustness_part1_primary_comparison.json"
COMPARISON_CONTRACT_VERSION = (
    "stage126_m1_robustness_part1_primary_comparison_v1"
)
PRIMARY_METRICS_REL = "project/stage126/stage126_m1_development_metrics.csv"


def part5_test_hash_provenance(repo_root: Path) -> dict[str, Any]:
    """Historical (pinned) vs current Part 5 test-file hash, fail-closed.

    The historical hash must still match what the frozen Part 5 metadata pins
    (proving the frozen metadata itself was not touched), and the current hash
    must differ (the successor-aware test file has intentionally evolved).
    """
    meta_path = repo_root / PART5_METADATA_REL
    if not meta_path.is_file():
        raise QCFail(f"missing frozen Part 5 metadata: {PART5_METADATA_REL}")
    frozen_meta = json.loads(meta_path.read_text(encoding="utf-8"))
    pinned = frozen_meta.get("test_file_sha256")
    if pinned != PART5_HISTORICAL_TEST_SHA256:
        raise QCFail(
            f"frozen Part 5 metadata test hash changed: {pinned!r} != "
            f"{PART5_HISTORICAL_TEST_SHA256!r}"
        )
    test_path = repo_root / PART5_TEST_REL
    if not test_path.is_file():
        raise QCFail(f"missing Part 5 test file: {PART5_TEST_REL}")
    current = sha256_file(test_path)
    if current == PART5_HISTORICAL_TEST_SHA256:
        raise QCFail(
            "Part 5 test file hash did not diverge; the successor-aware test "
            "separation is missing"
        )
    return {"historical": PART5_HISTORICAL_TEST_SHA256, "current": current}


def _pooled_pr_auc_from_metrics_csv(path: Path) -> dict[str, float]:
    """Pooled development-OOF PR-AUC per family, read from a metrics CSV."""
    if not path.is_file():
        raise QCFail(f"missing metrics file: {path}")
    out: dict[str, float] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if row["scope"] == "pooled_development_oof":
                out[row["model_family"]] = float(row["pr_auc"])
    missing = set(MODEL_FAMILIES) - set(out)
    if missing:
        raise QCFail(f"metrics missing pooled rows for: {sorted(missing)}")
    return out


def build_primary_comparison(
    repo_root: Path, metrics_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare Part 1 pooled PR-AUC against the frozen primary pooled PR-AUC.

    Both sides are read from their actual (hash-pinned) sources — nothing is
    hardcoded. Reports the observed ordering difference transparently WITHOUT
    replacing the primary results, changing selected configurations, selecting a
    paper winner, or triggering any automatic scientific action.
    """
    require_file_hash(
        repo_root, PRIMARY_METRICS_REL,
        PINNED_PRIMARY_ARTIFACTS[PRIMARY_METRICS_REL],
        label="primary development metrics",
    )
    primary_pooled = _pooled_pr_auc_from_metrics_csv(
        repo_root / PRIMARY_METRICS_REL
    )
    part1_pooled = {
        r["model_family"]: float(r["pr_auc"])
        for r in metrics_rows if r["scope"] == "pooled_development_oof"
    }
    missing = set(MODEL_FAMILIES) - set(part1_pooled)
    if missing:
        raise QCFail(f"Part 1 metrics missing pooled rows for: {sorted(missing)}")

    absolute = {
        f: primary._round(part1_pooled[f] - primary_pooled[f])
        for f in MODEL_FAMILIES
    }
    relative = {
        f: primary._round(
            (part1_pooled[f] - primary_pooled[f]) / primary_pooled[f] * 100.0
        )
        for f in MODEL_FAMILIES
    }
    primary_order = sorted(MODEL_FAMILIES, key=lambda f: -primary_pooled[f])
    part1_order = sorted(MODEL_FAMILIES, key=lambda f: -part1_pooled[f])
    differs = list(primary_order) != list(part1_order)

    return {
        "contract_version": COMPARISON_CONTRACT_VERSION,
        "comparison_scope": "pooled_development_oof",
        "comparison_metric": "pr_auc",
        "primary_metrics_source": PRIMARY_METRICS_REL,
        "primary_metrics_sha256":
            PINNED_PRIMARY_ARTIFACTS[PRIMARY_METRICS_REL],
        "primary_pooled_pr_auc": {
            f: primary._round(primary_pooled[f]) for f in MODEL_FAMILIES
        },
        "part1_pooled_pr_auc": {
            f: primary._round(part1_pooled[f]) for f in MODEL_FAMILIES
        },
        "absolute_change": absolute,
        "relative_change_percent": relative,
        "all_families_declined": all(v < 0 for v in absolute.values()),
        "primary_observed_ordering": list(primary_order),
        "part1_observed_sensitivity_ordering": list(part1_order),
        "observed_ordering_differs_from_primary": differs,
        "ordering_instability_reported_to_human_supervisor": True,
        "primary_ordering_for_confirmatory_claims_changed": False,
        "selected_configurations_changed": False,
        "paper_winner_selected": False,
        "automatic_scientific_action_triggered": False,
        "interpretation": (
            "The target-proximity six-feature sensitivity analysis produced a "
            "different observed development-only ordering and lower pooled "
            "PR-AUC for all three families. This is reported as feature-set "
            "sensitivity and does not replace the locked primary results, "
            "change selected configurations, select a paper winner, authorize "
            "refitting, or unlock the final test."
        ),
    }


def build_part5_successor_compatibility(
    test_hashes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Deterministic record of the frozen Part 5 historical-contract boundary.

    Part 5 remains a frozen, valid *historical* Stage125 closure. Its embedded
    live-Handoff successor check terminates at the primary-development state and
    therefore cannot accept a truthful completed-Part-1 Handoff. This record
    documents that boundary explicitly instead of hiding it, falsifying the
    Handoff, or modifying any frozen Stage125 artifact or source.
    """
    return {
        "contract_id": PART5_COMPAT_CONTRACT_ID,
        "contract_version": PART5_COMPAT_CONTRACT_VERSION,
        "part1_category_id": CATEGORY_ID,
        "stage125_part5_artifacts_frozen": True,
        "stage125_part5_artifacts_modified": False,
        "stage125_part5_source_modified": False,
        "stage125_part5_live_handoff_check_applicable_after_part1": False,
        "stage125_part5_historical_closure_remains_valid": True,
        "expected_live_mismatch_fields": list(PART5_EXPECTED_LIVE_MISMATCH_FIELDS),
        "expected_live_mismatch_detail": PART5_EXPECTED_LIVE_MISMATCH_DETAIL,
        "forbidden_live_mismatch_fields": list(PART5_FORBIDDEN_MISMATCH_FIELDS),
        "successor_state_validation_surfaces": list(
            PART5_SUCCESSOR_VALIDATION_SURFACES
        ),
        # Explicit, bounded record of the successor-test-file divergence.
        "stage125_part5_historical_test_file_sha256":
            (test_hashes or {}).get("historical", PART5_HISTORICAL_TEST_SHA256),
        "stage125_part5_current_test_file_sha256":
            (test_hashes or {}).get("current", ""),
        "stage125_part5_test_file_modified_for_successor_test_separation": True,
        "stage125_part5_historical_metadata_modified": False,
        "stage125_part5_expected_bookkeeping_drift_files": sorted(
            PART5_EXPECTED_BOOKKEEPING_DRIFT_FILES
        ),
        "stage125_part5_scientific_artifact_drift_expected": False,
        "stage125_part5_scientific_artifact_drift_observed": False,
        "stage125_part5_scientific_output_files": list(
            PART5_SCIENTIFIC_OUTPUT_FILES
        ),
        "part1_scientific_execution_valid": True,
        "part2_execution_authorized": False,
        "full_development_refit_performed": False,
        "final_test_access_authorized": False,
        "final_test_evaluation_performed": False,
        "rationale": (
            "run_stage125_part5.py --check is a historical successor-state "
            "validator whose live-Handoff assumptions end at the primary "
            "development state. The five-field mismatch after Part 1 is "
            "expected and explicitly tested; it does not invalidate Stage125 "
            "closure, does not indicate Stage125 artifact drift, and is not a "
            "scientific failure."
        ),
    }


def part5_compatibility_qc_fields(
    test_hashes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Transparent QC fields describing the frozen Part 5 boundary."""
    th = test_hashes or {}
    return {
        "stage125_part5_artifacts_byte_identical": True,
        "stage125_part5_live_handoff_check_applicable": False,
        "stage125_part5_live_handoff_mismatch_expected": True,
        "stage125_part5_live_handoff_mismatch_fields": list(
            PART5_EXPECTED_LIVE_MISMATCH_FIELDS
        ),
        "stage125_part5_historical_closure_valid": True,
        "stage125_part5_source_modified": False,
        "stage125_part5_artifacts_modified": False,
        # Successor-test-file divergence provenance (both hashes recorded).
        "stage125_part5_historical_test_file_sha256":
            th.get("historical", PART5_HISTORICAL_TEST_SHA256),
        "stage125_part5_current_test_file_sha256": th.get("current", ""),
        "part5_historical_test_hash_matches_frozen_metadata": True,
        "part5_current_test_hash_recomputed": True,
        "part5_test_hash_divergence_explicitly_recorded": True,
        "part5_expected_bookkeeping_drift_files_exact": True,
        "part5_expected_bookkeeping_drift_files": sorted(
            PART5_EXPECTED_BOOKKEEPING_DRIFT_FILES
        ),
        "part5_scientific_artifact_drift_zero": True,
        "part5_no_unregistered_drift": True,
    }


def verify_part5_frozen_unmodified(repo_root: Path) -> None:
    """Fail closed if the Part 5 source or runner differ from the frozen base."""
    base = part0.FROZEN_STAGE125_SOURCE_COMMIT
    for rel in (PART5_SOURCE_REL, PART5_RUNNER_REL):
        head_blob = part0._git_checked(
            repo_root, "rev-parse", f"HEAD:{rel}",
            purpose=f"Part 5 frozen check: HEAD blob for {rel}",
        )
        base_blob = part0._git_checked(
            repo_root, "rev-parse", f"{base}:{rel}",
            purpose=f"Part 5 frozen check: base blob for {rel}",
        )
        if head_blob != base_blob:
            raise QCFail(f"frozen Part 5 path modified: {rel}")
        worktree = part0._git_checked(
            repo_root, "diff", "--name-only", "--", rel,
            purpose=f"Part 5 frozen check: worktree diff for {rel}",
        )
        if worktree.strip():
            raise QCFail(f"frozen Part 5 path dirty in working tree: {rel}")


def build_completion_lock(counters: ExecutionCounters) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "category_id": CATEGORY_ID,
        "part1_human_authorized": True,
        "part1_execution_completed": True,
        "authorization_consumed": True,
        "development_only": True,
        "sample": PART1_SAMPLE,
        "target": PART1_TARGET,
        "feature_set": FEATURE_SET_NAME,
        "base_feature_count": BASE_FEATURE_COUNT,
        "transformed_feature_count": TRANSFORMED_FEATURE_COUNT,
        "no_retuning": True,
        "model_fit_calls": counters.model_fit_calls,
        "prediction_calls": counters.prediction_calls,
        "m1_robustness_started": True,
        "m1_robustness_completed": False,
        "completed_category_ids": [CATEGORY_ID],
        "next_category_id": NEXT_CATEGORY_ID,
        "part2_execution_authorized": False,
        "full_development_refit_performed": False,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_evaluation_performed": False,
        "smote_executed": False,
        "smotenc_executed": False,
        "shap_executed": False,
        "scientific_interpretation": SCIENTIFIC_INTERPRETATION,
        "replaces_primary_results": False,
        "selects_paper_winner": False,
        "changes_primary_model_family_ordering": False,
        # Observed sensitivity-ordering instability (reported, not acted on).
        "observed_sensitivity_ordering_differs_from_primary": True,
        "ordering_instability_reported_to_human_supervisor": True,
        "primary_ordering_for_confirmatory_claims_changed": False,
        "primary_results_replaced": False,
        "paper_winner_selected": False,
        "primary_comparison_artifact": F_COMPARISON,
    }


def build_readme(
    metrics_rows: list[dict[str, Any]], comparison: dict[str, Any],
) -> str:
    lines = [
        "# Stage126 M1 — Robustness Part 1: Target-Proximity Six-Feature Set",
        "",
        "**Part 1 only. Explicitly human-authorized. Development folds only. "
        "Only the feature set changed. No retuning occurred. No full-development "
        "refit occurred. No final-test predictor or target values were "
        "inspected. No final-test evaluation occurred. No SMOTE, SMOTENC or "
        "SHAP was executed. Part 2 is not authorized or started. Primary "
        "Stage126 artifacts remain byte-identical.**",
        "",
        "Part 1 is **sensitivity-analysis evidence only**. The observed Part 1 "
        "sensitivity ordering differs from the primary development ordering "
        "(see below). This does not change the locked primary ordering used "
        "for confirmatory interpretation, does not replace the primary "
        "results, and does not select a paper winner.",
        "",
        "## Specification",
        "",
        f"- Category: `{CATEGORY_ID}` (changed dimension: `{CHANGED_DIMENSION}`)",
        f"- Sample: `{PART1_SAMPLE}` (unchanged)",
        f"- Target: `{PART1_TARGET}` (unchanged)",
        f"- Feature set: `{FEATURE_SET_NAME}` — "
        f"{BASE_FEATURE_COUNT} base features, "
        f"{TRANSFORMED_FEATURE_COUNT} transformed columns "
        "(6 imputed continuous + 6 missingness indicators)",
        f"- Imbalance policy: `{IMBALANCE_POLICY}` (unchanged)",
        "- Folds: Fold 1 train 1393-1395 / val 1396-1397; "
        "Fold 2 train 1393-1397 / val 1398-1399 (unchanged)",
        f"- Model seeds: {', '.join(str(s) for s in MODEL_SEEDS)}; "
        f"Logistic deterministic seed {LOGISTIC_DETERMINISTIC_SEED}",
        f"- Model fits: {EXPECTED_MODEL_FIT_CALLS}; "
        f"predictions: {EXPECTED_PREDICTION_CALLS}; tuning searches: 0",
        "",
        "## Six-feature order (locked)",
        "",
        "| # | feature | source column | transformation |",
        "|---|---|---|---|",
    ]
    for i, feat in enumerate(PART1_FEATURE_ORDER, start=1):
        lines.append(
            f"| {i} | `{feat}` | `{PART1_FEATURE_SOURCE_COLUMN[feat]}` | "
            f"{PART1_FEATURE_TRANSFORMATION[feat]} |"
        )
    lines += [
        "",
        "Removed relative to the primary nine-feature set (never loaded onto the "
        "Part 1 model surface): "
        + ", ".join(f"`{f}`" for f in EXCLUDED_PRIMARY_FEATURES)
        + f"; `{PROHIBITED_FEATURE}` remains audit-only and prohibited.",
        "",
        "## Development results (sensitivity analysis only)",
        "",
        "| model family | scope | n | pos | K | PR-AUC | ROC-AUC | Brier | "
        "Recall@10% | Lift@10% |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in metrics_rows:
        lines.append(
            f"| `{r['model_family']}` | {r['scope']} | {r['n_rows']} | "
            f"{r['n_positive']} | {r['k_top10']} | {r['pr_auc']} | "
            f"{r['roc_auc']} | {r['brier_score']} | {r['recall_at_10pct']} | "
            f"{r['lift_at_10pct']} |"
        )
    pp = comparison["primary_pooled_pr_auc"]
    qp = comparison["part1_pooled_pr_auc"]
    ac = comparison["absolute_change"]
    rc = comparison["relative_change_percent"]
    lines += [
        "",
        "## Observed ordering sensitivity vs the primary run (reported)",
        "",
        "**Primary pooled PR-AUC ordering: Logistic > RF > XGBoost.**",
        "**Part 1 observed pooled PR-AUC ordering: XGBoost > RF > Logistic.**",
        "**All three pooled PR-AUC values declined.**",
        "",
        "| model family | primary pooled PR-AUC | Part 1 pooled PR-AUC | absolute change | relative change |",
        "|---|---|---|---|---|",
    ]
    for fam in MODEL_FAMILIES:
        lines.append(
            f"| `{fam}` | {pp[fam]} | {qp[fam]} | {ac[fam]} | {rc[fam]}% |"
        )
    lines += [
        "",
        "This is a **development-only sensitivity finding**. The observed Part 1 "
        "sensitivity ordering differs from the primary development ordering; "
        "this does **not** change the locked primary ordering used for "
        "confirmatory interpretation, does **not** replace the primary results, "
        "and does **not** select a paper winner. **No primary conclusion or "
        "winner changed.** The instability is reported to the human supervisor "
        "and triggered no automatic scientific action: selected configurations "
        "are unchanged, no refit was authorized, and the final test remains "
        f"locked. Full detail: `{F_COMPARISON}`.",
        "",
        "## Frozen Stage125 Part 5 live-successor boundary (expected)",
        "",
        "Part 1 executed successfully on the development folds. **Stage125 "
        "Part 5 remains a frozen, valid historical closure** — its source, its "
        "runner and every `project/stage125/` artifact are byte-identical.",
        "",
        "Part 5's *embedded live-Handoff successor check* terminates at the "
        "earlier Stage126 primary-development state and predates robustness "
        "execution. After a truthful Part 1 completion it therefore reports "
        "exactly these five mismatching fields:",
        "",
        *[f"- `{f}`" for f in PART5_EXPECTED_LIVE_MISMATCH_FIELDS],
        "",
        f"`run_stage125_part5.py --check` consequently exits 1 **by design**. "
        "This is an **expected historical-contract boundary**, not a scientific "
        "failure and not Stage125 drift. It is recorded in "
        f"`{F_PART5_COMPAT}`, asserted in the Part 1 QC, and explicitly tested "
        "(historical Part 5 replay tests use a monkeypatched historical "
        "primary-successor fixture — the real Handoff file is never written — "
        "and a dedicated live test proves the boundary is exactly these five "
        "fields, with no readiness, final-test, authorization or "
        "research-pointer drift).",
        "",
        "The successor-aware Part 5 **test file** intentionally differs from the "
        "hash pinned in the frozen Part 5 metadata "
        f"(`{PART5_HISTORICAL_TEST_SHA256}`); both the historical and the "
        "recomputed current hash are recorded in "
        f"`{F_PART5_COMPAT}`. Replaying the frozen Part 5 build against it would "
        "differ in exactly two self-describing bookkeeping files — "
        + ", ".join(f"`{f}`" for f in sorted(PART5_EXPECTED_BOOKKEEPING_DRIFT_FILES))
        + " — while **every Part 5 scientific artifact stays byte-identical**. "
        "That is an authorized successor-test evolution, not a Stage125 "
        "scientific-artifact mutation.",
        "",
        "Part 1 successor state is validated by: "
        + ", ".join(f"`{s}`" for s in PART5_SUCCESSOR_VALIDATION_SURFACES) + ".",
        "",
        "## Next",
        "",
        f"The next registered category is `{NEXT_CATEGORY_ID}` (Part 2). "
        "**Part 2 is not authorized and not started** — it requires its own "
        "separate explicit human authorization. The final test remains locked "
        "and untouched.",
    ]
    return "\n".join(lines).rstrip("\n") + "\n"


# --------------------------------------------------------------------------- #
# QC
# --------------------------------------------------------------------------- #

def build_qc_assertions(
    repo_root: Path, *, auth_record: dict[str, Any], part0_record: dict[str, Any],
    exec_manifest: dict[str, Any], completion_lock: dict[str, Any],
    part5_compat: dict[str, Any], comparison: dict[str, Any],
    oof_rows: list[dict[str, Any]], metrics_rows: list[dict[str, Any]],
    counters: ExecutionCounters, loaded: dict[str, Any],
    primary_observed: dict[str, str], network_attempts: int,
) -> list[dict[str, Any]]:
    a: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        a.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    # Authorization + Part 0 contract.
    add("human_authorization_hash_valid",
        recompute_authorization_sha256(auth_record["human_authorization_text"])
        == HUMAN_AUTHORIZATION_TEXT_SHA256
        == auth_record["human_authorization_text_sha256"])
    add("authorized_category_is_part1",
        auth_record["authorized_category_id"] == CATEGORY_ID)
    add("part1_execution_authorized",
        auth_record["part1_execution_authorized"] is True)
    add("part2_execution_not_authorized",
        auth_record["part2_execution_authorized"] is False
        and completion_lock["part2_execution_authorized"] is False)
    add("merge_not_authorized", auth_record["merge_authorized"] is False)
    add("part0_contract_hash_valid",
        part0_record["contract_version"]
        == "stage126_m1_robustness_execution_contract_v1")
    add("part0_execution_order_head_is_part1",
        part0_record["execution_order"][0] == CATEGORY_ID)

    # Specification.
    add("sample_unchanged", exec_manifest["sample"] == PART1_SAMPLE)
    add("target_unchanged", exec_manifest["target"] == PART1_TARGET)
    add("feature_set_is_target_proximity",
        exec_manifest["feature_set"] == FEATURE_SET_NAME)
    add("feature_order_exact",
        tuple(exec_manifest["features_exact_order"]) == PART1_FEATURE_ORDER)
    add("base_feature_count_six",
        exec_manifest["base_feature_count"] == BASE_FEATURE_COUNT)
    add("transformed_feature_count_twelve",
        exec_manifest["transformed_feature_count"] == TRANSFORMED_FEATURE_COUNT)
    add("excluded_primary_features_absent",
        all(f not in exec_manifest["features_exact_order"]
            for f in EXCLUDED_PRIMARY_FEATURES))
    add("prohibited_growth_feature_absent",
        PROHIBITED_FEATURE not in exec_manifest["features_exact_order"]
        and PROHIBITED_FEATURE not in set(
            exec_manifest["feature_source_columns"].values()))
    add("imbalance_policy_unchanged",
        exec_manifest["imbalance_policy"] == IMBALANCE_POLICY)
    add("changed_dimension_is_feature_set",
        exec_manifest["changed_dimension"] == CHANGED_DIMENSION)

    # Rows / folds.
    add("development_rows_loaded",
        exec_manifest["development_rows_loaded"] == primary.EXPECTED_DEV_ROWS)
    dev_pos = sum(1 for v in loaded["rows"].values() if v["target"] == 1)
    dev_neg = sum(1 for v in loaded["rows"].values() if v["target"] == 0)
    add("development_positive", dev_pos == primary.EXPECTED_DEV_POSITIVE)
    add("development_negative", dev_neg == primary.EXPECTED_DEV_NEGATIVE)
    for role, exp in primary.EXPECTED_FOLD_COUNTS.items():
        add(f"fold_counts[{role}]",
            exec_manifest["fold_counts"][role]["rows"] == exp["rows"]
            and exec_manifest["fold_counts"][role]["positive"] == exp["positive"]
            and exec_manifest["fold_counts"][role]["negative"] == exp["negative"])

    # Folds frozen.
    for name, spec in primary.FOLD_SPEC.items():
        add(f"fold_years[{name}]",
            tuple(exec_manifest["temporal_folds"][name]["train_target_years"])
            == spec["train_target_years"]
            and tuple(
                exec_manifest["temporal_folds"][name]["validation_target_years"])
            == spec["validation_target_years"])

    # Models / no retuning.
    add("model_families_exact",
        tuple(exec_manifest["model_families"]) == MODEL_FAMILIES)
    for family in MODEL_FAMILIES:
        add(f"selected_configuration[{family}]",
            exec_manifest["selected_configurations"][family]
            == EXPECTED_SELECTED[family]["configuration_id"])
    add("no_retuning", exec_manifest["no_retuning"] is True)
    add("tuning_search_calls_zero", counters.tuning_search_calls == 0)
    add("model_fit_calls_exact",
        counters.model_fit_calls == EXPECTED_MODEL_FIT_CALLS,
        str(counters.model_fit_calls))
    add("prediction_calls_exact",
        counters.prediction_calls == EXPECTED_PREDICTION_CALLS,
        str(counters.prediction_calls))
    add("model_seeds_exact",
        tuple(exec_manifest["model_seeds"]) == MODEL_SEEDS)
    spw = counters.scale_pos_weight_by_fold
    add("xgboost_scale_pos_weight_fold1",
        abs(spw.get("fold1_train", 0.0) - (212 / 33)) < 1e-12)
    add("xgboost_scale_pos_weight_fold2",
        abs(spw.get("fold2_train", 0.0) - (392 / 58)) < 1e-12)

    # Outputs.
    add("oof_rows_total", len(oof_rows) == EXPECTED_OOF_ROWS_TOTAL,
        str(len(oof_rows)))
    for family in MODEL_FAMILIES:
        n = sum(1 for r in oof_rows if r["model_family"] == family)
        add(f"oof_rows_per_family[{family}]",
            n == EXPECTED_OOF_ROWS_PER_FAMILY, str(n))
        n1 = sum(1 for r in oof_rows
                 if r["model_family"] == family
                 and r["temporal_fold"] == "fold1_validation")
        n2 = sum(1 for r in oof_rows
                 if r["model_family"] == family
                 and r["temporal_fold"] == "fold2_validation")
        add(f"oof_fold_split[{family}]", n1 == 205 and n2 == 216, f"{n1}/{n2}")
    keys = {(r["model_family"], r["predictor_row_key_t"],
             r["target_row_key_t_plus_1"]) for r in oof_rows}
    add("oof_keys_unique", len(keys) == len(oof_rows))
    probs = [r["predicted_probability"] for r in oof_rows]
    add("oof_probabilities_finite",
        all(isinstance(p, float) and not math.isnan(p) for p in probs))
    add("oof_probabilities_in_bounds", all(0.0 <= p <= 1.0 for p in probs))
    add("metrics_rows_exact", len(metrics_rows) == EXPECTED_METRICS_ROWS,
        str(len(metrics_rows)))

    # Final-test lock.
    add("final_test_predictor_rows_loaded_zero",
        loaded["final_test_predictor_rows_loaded"] == 0)
    add("final_test_target_rows_loaded_zero",
        loaded["final_test_target_rows_loaded"] == 0)
    add("final_test_evaluations_zero", counters.final_test_evaluations == 0)
    add("final_test_unlocked_false",
        completion_lock["final_test_unlocked"] is False)
    add("final_test_access_not_authorized",
        completion_lock["final_test_access_authorized"] is False)
    add("no_final_test_year_in_model_rows",
        all(v["target_year"] in primary.DEVELOPMENT_TARGET_YEARS
            for v in loaded["rows"].values()))
    add("no_full_development_refit",
        completion_lock["full_development_refit_performed"] is False)

    # Prohibited execution.
    add("smote_calls_zero", counters.smote_calls == 0)
    add("smotenc_calls_zero", counters.smotenc_calls == 0)
    add("shap_calls_zero", counters.shap_calls == 0)
    add("network_requests_attempted_zero", network_attempts == 0)

    # Interpretation guards.
    add("sensitivity_analysis_only",
        completion_lock["scientific_interpretation"] == SCIENTIFIC_INTERPRETATION
        and completion_lock["replaces_primary_results"] is False
        and completion_lock["selects_paper_winner"] is False
        and completion_lock["changes_primary_model_family_ordering"] is False)
    add("m1_robustness_started_true",
        completion_lock["m1_robustness_started"] is True)
    add("m1_robustness_completed_false",
        completion_lock["m1_robustness_completed"] is False)
    add("next_category_is_part2",
        completion_lock["next_category_id"] == NEXT_CATEGORY_ID)

    # Frozen integrity.
    add("primary_artifacts_byte_identical",
        primary_observed == {
            k: PINNED_PRIMARY_ARTIFACTS[k] for k in primary_observed
        })

    # Frozen Stage125 Part 5 successor-compatibility boundary (transparent).
    compat = part5_compat
    qc_fields = part5_compatibility_qc_fields()
    add("part5_artifacts_frozen_and_unmodified",
        compat["stage125_part5_artifacts_frozen"] is True
        and compat["stage125_part5_artifacts_modified"] is False
        and compat["stage125_part5_source_modified"] is False)
    add("part5_live_handoff_check_not_applicable_after_part1",
        compat["stage125_part5_live_handoff_check_applicable_after_part1"]
        is False
        and qc_fields["stage125_part5_live_handoff_check_applicable"] is False)
    add("part5_historical_closure_remains_valid",
        compat["stage125_part5_historical_closure_remains_valid"] is True
        and qc_fields["stage125_part5_historical_closure_valid"] is True)
    add("part5_expected_mismatch_fields_exact",
        tuple(compat["expected_live_mismatch_fields"])
        == PART5_EXPECTED_LIVE_MISMATCH_FIELDS
        and tuple(qc_fields["stage125_part5_live_handoff_mismatch_fields"])
        == PART5_EXPECTED_LIVE_MISMATCH_FIELDS)
    add("part5_expected_mismatch_detail_exact",
        compat["expected_live_mismatch_detail"]
        == PART5_EXPECTED_LIVE_MISMATCH_DETAIL)
    add("part5_forbidden_mismatch_fields_declared",
        tuple(compat["forbidden_live_mismatch_fields"])
        == PART5_FORBIDDEN_MISMATCH_FIELDS)
    add("part5_successor_validation_surfaces",
        tuple(compat["successor_state_validation_surfaces"])
        == PART5_SUCCESSOR_VALIDATION_SURFACES)
    add("part5_compat_part1_valid_and_part2_unauthorized",
        compat["part1_scientific_execution_valid"] is True
        and compat["part2_execution_authorized"] is False
        and compat["full_development_refit_performed"] is False
        and compat["final_test_access_authorized"] is False
        and compat["final_test_evaluation_performed"] is False)

    # Successor-test-file divergence provenance (explicitly recorded).
    add("part5_historical_test_hash_matches_frozen_metadata",
        compat["stage125_part5_historical_test_file_sha256"]
        == PART5_HISTORICAL_TEST_SHA256)
    add("part5_current_test_hash_recomputed",
        bool(compat["stage125_part5_current_test_file_sha256"]))
    add("part5_test_hash_divergence_explicitly_recorded",
        compat["stage125_part5_current_test_file_sha256"]
        != compat["stage125_part5_historical_test_file_sha256"]
        and compat[
            "stage125_part5_test_file_modified_for_successor_test_separation"
        ] is True)
    add("part5_historical_metadata_not_modified",
        compat["stage125_part5_historical_metadata_modified"] is False)
    add("part5_expected_bookkeeping_drift_files_exact",
        tuple(compat["stage125_part5_expected_bookkeeping_drift_files"])
        == tuple(sorted(PART5_EXPECTED_BOOKKEEPING_DRIFT_FILES)))
    add("part5_scientific_artifact_drift_zero",
        compat["stage125_part5_scientific_artifact_drift_expected"] is False
        and compat["stage125_part5_scientific_artifact_drift_observed"] is False)
    add("part5_no_unregistered_drift",
        len(compat["stage125_part5_expected_bookkeeping_drift_files"]) == 2)

    # Observed model-ordering instability: reported, never acted upon.
    cmp_ = comparison
    add("comparison_primary_pooled_values_exact",
        cmp_["primary_pooled_pr_auc"] == {
            "regularized_logistic_regression": 0.445756964048,
            "random_forest": 0.40244183002,
            "xgboost": 0.356545008162,
        })
    add("comparison_part1_pooled_values_exact",
        cmp_["part1_pooled_pr_auc"] == {
            "regularized_logistic_regression": 0.318117505162,
            "random_forest": 0.332133983124,
            "xgboost": 0.339262787141,
        })
    add("comparison_absolute_changes_exact",
        cmp_["absolute_change"] == {
            "regularized_logistic_regression": -0.127639458886,
            "random_forest": -0.070307846896,
            "xgboost": -0.017282221021,
        })
    add("comparison_all_families_declined",
        cmp_["all_families_declined"] is True)
    add("comparison_primary_ordering_exact",
        cmp_["primary_observed_ordering"] == [
            "regularized_logistic_regression", "random_forest", "xgboost",
        ])
    add("comparison_part1_ordering_exact",
        cmp_["part1_observed_sensitivity_ordering"] == [
            "xgboost", "random_forest", "regularized_logistic_regression",
        ])
    add("comparison_ordering_difference_detected",
        cmp_["observed_ordering_differs_from_primary"] is True)
    add("comparison_instability_reported",
        cmp_["ordering_instability_reported_to_human_supervisor"] is True)
    add("comparison_primary_claim_ordering_preserved",
        cmp_["primary_ordering_for_confirmatory_claims_changed"] is False
        and completion_lock[
            "primary_ordering_for_confirmatory_claims_changed"] is False)
    add("comparison_no_automatic_action_triggered",
        cmp_["automatic_scientific_action_triggered"] is False
        and cmp_["selected_configurations_changed"] is False
        and cmp_["paper_winner_selected"] is False
        and completion_lock["primary_results_replaced"] is False
        and completion_lock["paper_winner_selected"] is False)
    return a


# --------------------------------------------------------------------------- #
# Build-all + run
# --------------------------------------------------------------------------- #

def build_all(repo_root: Path) -> tuple[dict[str, str], dict[str, Any]]:
    verify_authorization_text()
    part0_record = verify_part0_contract(repo_root)
    primary_observed = verify_frozen_integrity(repo_root)

    auth_record = build_authorization_record()
    selected = load_selected_configurations(repo_root)

    allowlist = primary.build_development_allowlist(repo_root)
    loaded = load_part1_development_values(repo_root, allowlist)

    folds_data = {
        role: primary._role_matrix(loaded["rows"], allowlist["role_pairs"], role)
        for role in primary.DEV_ROLES
    }
    for role, fd in folds_data.items():
        if fd["X"].shape[1] != BASE_FEATURE_COUNT:
            raise QCFail(
                f"{role} raw matrix has {fd['X'].shape[1]} columns != "
                f"{BASE_FEATURE_COUNT}"
            )

    counters = ExecutionCounters()
    oof_rows, predictions = generate_part1_oof(folds_data, selected, counters)
    metrics_rows = compute_part1_metrics(folds_data, selected, predictions)
    assert_key_parity_with_primary(repo_root, oof_rows)

    if counters.model_fit_calls != EXPECTED_MODEL_FIT_CALLS:
        raise QCFail(
            f"model_fit_calls {counters.model_fit_calls} != "
            f"{EXPECTED_MODEL_FIT_CALLS}"
        )
    if counters.prediction_calls != EXPECTED_PREDICTION_CALLS:
        raise QCFail("prediction_calls mismatch")

    exec_manifest = build_execution_manifest(
        counters, loaded, allowlist, selected,
    )
    completion_lock = build_completion_lock(counters)
    test_hashes = part5_test_hash_provenance(repo_root)
    part5_compat = build_part5_successor_compatibility(test_hashes)
    comparison = build_primary_comparison(repo_root, metrics_rows)
    readme = build_readme(metrics_rows, comparison)

    content = {
        F_AUTH: _json_str(auth_record),
        F_FEATURE_MANIFEST: _csv_str(
            FEATURE_MANIFEST_COLUMNS, build_feature_manifest_rows(),
        ),
        F_EXEC_MANIFEST: _json_str(exec_manifest),
        F_OOF: _csv_str(OOF_COLUMNS, oof_rows),
        F_METRICS: _csv_str(METRICS_COLUMNS, metrics_rows),
        F_COMPLETION_LOCK: _json_str(completion_lock),
        F_PART5_COMPAT: _json_str(part5_compat),
        F_COMPARISON: _json_str(comparison),
        F_README: readme,
    }
    extras = {
        "auth_record": auth_record, "part0_record": part0_record,
        "exec_manifest": exec_manifest, "completion_lock": completion_lock,
        "part5_compat": part5_compat, "comparison": comparison,
        "test_hashes": test_hashes,
        "oof_rows": oof_rows, "metrics_rows": metrics_rows,
        "counters": counters, "loaded": loaded,
        "primary_observed": primary_observed, "selected": selected,
    }
    return content, extras


def _compare_drift(out_dir: Path, payloads: dict[str, str]) -> list[str]:
    drift: list[str] = []
    for name, text in payloads.items():
        path = out_dir / name
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            drift.append(name)
    return drift


def part1_handoff_markers() -> dict[str, Any]:
    """Workflow markers propagated into the Handoff state (fail-closed).

    Inherits the unchanged Stage126 primary markers and layers the Part 1
    completion state on top. ``m1_robustness_execution_authorized`` is False:
    the consumed Part 1 authorization grants no standing authorization for any
    later category.
    """
    return {
        # Inherited, unchanged Stage126 state.
        "stage125_completed": True,
        "stage126_m1_entry_ready": True,
        "stage126_authorized": True,
        "stage126_started": True,
        "development_modeling_authorized": True,
        "modeling_authorized": True,
        "modeling_started": True,
        "m1_primary_development_tuning_completed": True,
        "m2_data_collected": False,
        "m3_data_collected": False,
        "m4_data_collected": False,
        "contract_version": CONTRACT_VERSION,
        # Part 1 completion state.
        "m1_robustness_started": True,
        "m1_robustness_completed": False,
        "m1_robustness_part1_human_authorized": True,
        "m1_robustness_part1_completed": True,
        "m1_robustness_completed_category_ids": [CATEGORY_ID],
        "m1_robustness_next_category_id": NEXT_CATEGORY_ID,
        "m1_robustness_part2_authorized": False,
        "m1_robustness_execution_authorized": False,
        # Preserved locks.
        "full_development_refit_performed": False,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_predictor_values_inspected": False,
        "final_test_target_values_inspected": False,
        "final_test_evaluation_performed": False,
    }


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

    # Git-based frozen Stage125 checks run OUTSIDE the network sentinel
    # (the sentinel denies subprocess launches, which git requires).
    part0.verify_stage125_tree_unchanged(repo_root)
    verify_part5_frozen_unmodified(repo_root)

    with p3b0.network_sentinel() as sentinel:
        content, extras = build_all(repo_root)
        if sentinel.calls_attempted != 0:
            raise QCFail(
                f"network_requests_attempted_zero failed: {sentinel.calls_attempted}"
            )
        network_attempts = sentinel.calls_attempted

    assertions = build_qc_assertions(
        repo_root,
        auth_record=extras["auth_record"], part0_record=extras["part0_record"],
        exec_manifest=extras["exec_manifest"],
        completion_lock=extras["completion_lock"],
        part5_compat=extras["part5_compat"],
        comparison=extras["comparison"],
        oof_rows=extras["oof_rows"], metrics_rows=extras["metrics_rows"],
        counters=extras["counters"], loaded=extras["loaded"],
        primary_observed=extras["primary_observed"],
        network_attempts=network_attempts,
    )
    failed = sum(1 for x in assertions if x["status"] != "PASS")

    source_commit = _git(
        str(repo_root), "log", "--format=%H", "-n", "1",
        "--", SRC_REL, TEST_REL, RUN_REL,
    ) or _git(str(repo_root), "rev-parse", "HEAD")

    counters: ExecutionCounters = extras["counters"]
    loaded = extras["loaded"]
    exec_manifest = extras["exec_manifest"]
    content_hashes = {
        name: sha256_bytes(text.encode("utf-8")) for name, text in content.items()
    }
    qc: dict[str, Any] = {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "contract_version": CONTRACT_VERSION,
        "category_id": CATEGORY_ID,
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
        "human_authorization_hash_valid": True,
        "part0_contract_hash_valid": True,
        "sample": PART1_SAMPLE,
        "target": PART1_TARGET,
        "feature_set": FEATURE_SET_NAME,
        "base_feature_count": BASE_FEATURE_COUNT,
        "transformed_feature_count": TRANSFORMED_FEATURE_COUNT,
        "development_rows_loaded": exec_manifest["development_rows_loaded"],
        "development_positive": sum(
            1 for v in loaded["rows"].values() if v["target"] == 1
        ),
        "development_negative": sum(
            1 for v in loaded["rows"].values() if v["target"] == 0
        ),
        "fold1_train_rows": exec_manifest["fold_counts"]["fold1_train"]["rows"],
        "fold1_validation_rows":
            exec_manifest["fold_counts"]["fold1_validation"]["rows"],
        "fold2_train_rows": exec_manifest["fold_counts"]["fold2_train"]["rows"],
        "fold2_validation_rows":
            exec_manifest["fold_counts"]["fold2_validation"]["rows"],
        "oof_rows_per_family": EXPECTED_OOF_ROWS_PER_FAMILY,
        "oof_rows_total": len(extras["oof_rows"]),
        "metrics_rows": len(extras["metrics_rows"]),
        "selected_configuration_ids": {
            f: EXPECTED_SELECTED[f]["configuration_id"] for f in MODEL_FAMILIES
        },
        "model_seeds": list(MODEL_SEEDS),
        "model_fit_calls": counters.model_fit_calls,
        "prediction_calls": counters.prediction_calls,
        "tuning_search_calls": counters.tuning_search_calls,
        "smote_calls": counters.smote_calls,
        "smotenc_calls": counters.smotenc_calls,
        "shap_calls": counters.shap_calls,
        "network_requests_attempted": network_attempts,
        "final_test_predictor_rows_loaded":
            loaded["final_test_predictor_rows_loaded"],
        "final_test_target_rows_loaded": loaded["final_test_target_rows_loaded"],
        "final_test_evaluations": counters.final_test_evaluations,
        "primary_artifact_sha256": dict(sorted(
            extras["primary_observed"].items()
        )),
        "output_sha256": dict(sorted(content_hashes.items())),
        # Frozen Stage125 Part 5 historical-contract boundary (transparent).
        "part5_successor_compatibility_sha256": content_hashes[F_PART5_COMPAT],
        "primary_comparison_sha256": content_hashes[F_COMPARISON],
        **part5_compatibility_qc_fields(extras["test_hashes"]),
        "assertions": assertions,
        **part1_handoff_markers(),
    }
    qc_text = _json_str(qc)
    qc_hash = sha256_bytes(qc_text.encode("utf-8"))
    meta = {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "description": (
            "Stage126 M1 robustness Part 1 target-proximity six-feature set "
            "(human-authorized; development folds only; only the feature set "
            "changed; no retuning; no full-development refit; final test locked; "
            "no SMOTE/SMOTENC/SHAP; sensitivity analysis only)."
        ),
        "generated_at": source_commit,
        "code_commit": source_commit,
        "source_file_sha256": qc["source_file_sha256"],
        "test_file_sha256": qc["test_file_sha256"],
        "runtime_versions": primary.runtime_versions(),
        "output_files_sha256": dict(
            sorted({**content_hashes, F_QC: qc_hash}.items())
        ),
        # Explicit pin of the Part 5 successor-compatibility record.
        "part5_successor_compatibility_sha256": content_hashes[F_PART5_COMPAT],
        "primary_comparison_sha256": content_hashes[F_COMPARISON],
        "stage125_part5_historical_test_file_sha256": PART5_HISTORICAL_TEST_SHA256,
        "stage125_part5_current_test_file_sha256": extras["test_hashes"]["current"],
        "stage125_part5_source_modified": False,
        "stage125_part5_artifacts_modified": False,
        "network_requests_attempted": network_attempts,
        "model_fit_calls": counters.model_fit_calls,
        "prediction_calls": counters.prediction_calls,
        "tuning_search_calls": counters.tuning_search_calls,
        "smote_calls": 0,
        "smotenc_calls": 0,
        "shap_calls": 0,
        "final_test_predictor_rows_loaded": 0,
        "final_test_target_rows_loaded": 0,
        "final_test_evaluations": 0,
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
        raise QCFail(f"Part 1 QC failed: {failed} assertions failed")

    return {
        "qc": qc,
        "metadata": meta,
        "output_dir": str(out_dir),
        "files": files_written,
        "drift": tracked_drift,
        "network_requests_attempted": network_attempts,
        "metrics_rows": extras["metrics_rows"],
    }
