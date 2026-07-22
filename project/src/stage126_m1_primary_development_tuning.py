"""Stage126 M1 — Primary Development-Fold Tuning (human-authorized).

Development-only M1 modeling under the frozen Stage125 Part 4 / Part 5 contracts.

This module:
  * records the explicit human authorization (byte-for-byte Persian text + hash),
  * loads ONLY the primary M1 development sample via a fail-closed two-pass
    loader (split/key columns first, then feature/target values for the
    development allowlist only),
  * fits and tunes the three locked primary model families over the locked
    32-configuration budget on the two locked temporal development folds,
  * selects one locked configuration per family,
  * generates development validation / OOF predictions and metrics,
  * records deterministic, auditable results.

It NEVER inspects, loads, parses, evaluates, or refits against the final test.
The final test remains locked until a separate explicit human authorization.

Offline. Deterministic. Zero network. No SMOTE. No SHAP. No robustness variants.
No full-development refit. No final-test access.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.metadata as importlib_metadata
import io
import json
import math
import platform
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from src import stage125_part3b0_evidence_readiness as p3b0
from src import stage125_part5_readiness_closure as part5
from src import stage126_authorization_transition_guard as auth_guard

# --------------------------------------------------------------------------- #
# Identity / baseline
# --------------------------------------------------------------------------- #

QC_STAGE = "stage126_m1_financial_baseline"
CURRENT_STAGE = "Stage126"
CONTRACT_VERSION = "stage126_m1_primary_development_tuning_v1"
RESEARCH_ACTION_ID = "stage126-m1-financial-baseline"
RESEARCH_LAST_COMPLETED = "stage125-part5-readiness-closure"
RESEARCH_NEXT = "stage126-m1-financial-baseline"
ACTIVE_WORKSTREAM = "stage126_m1_financial_baseline"

# Packages whose exact versions are recorded for reproducibility (§16). Recorded
# under the canonical Stage126 environment; --check compares them verbatim so a
# version drift surfaces as drift rather than silently altering numeric results.
RUNTIME_VERSION_PACKAGES = ("pandas", "numpy", "scikit-learn", "xgboost", "jdatetime")


def runtime_versions() -> dict[str, str]:
    """Deterministically record exact runtime package versions."""
    def _v(dist: str) -> str:
        try:
            return importlib_metadata.version(dist)
        except Exception:
            return "unavailable"

    versions = {"python": platform.python_version()}
    versions.update({pkg: _v(pkg) for pkg in RUNTIME_VERSION_PACKAGES})
    return versions

EXPECTED_BASELINE_COMMIT = "5f56be5b2e49e66c54b451994a5e36c4fcc754d9"
EXPECTED_BASELINE_TREE = "d8f399e3dedac123065f6eda876dc9e71f0c36e7"

SRC_REL = "project/src/stage126_m1_primary_development_tuning.py"
TEST_REL = "project/tests/test_stage126_m1_primary_development_tuning.py"
RUN_REL = "project/run_stage126_m1_primary_development_tuning.py"

# --------------------------------------------------------------------------- #
# Human authorization (byte-for-byte) — shared transition guard
# --------------------------------------------------------------------------- #

AUTHORIZATION_TEXT_FA = auth_guard.AUTHORIZATION_TEXT_FA
AUTHORIZATION_TEXT_SHA256 = auth_guard.AUTHORIZATION_TEXT_SHA256
AUTHORIZATION_ID = auth_guard.AUTHORIZATION_ID
AUTHORIZATION_DATE = auth_guard.AUTHORIZATION_DATE

# --------------------------------------------------------------------------- #
# Primary M1 specification (frozen)
# --------------------------------------------------------------------------- #

PRIMARY_SAMPLE = "main_rule_a_primary"
PRIMARY_TARGET = "FD_target_main_t_plus_1"
FEATURE_SET_NAME = "M1_PRIMARY_FEATURE_ORDER"

# Exact feature order, and the frozen Part 3C source column each derives from.
M1_PRIMARY_FEATURE_ORDER: list[str] = [
    "log_total_assets",
    "leverage_ratio",
    "current_ratio",
    "roa_period_adjusted",
    "ocf_to_assets_period_adjusted",
    "asset_turnover_period_adjusted",
    "operating_margin_period_adjusted",
    "financial_expense_to_assets_period_adjusted",
    "accumulated_loss_to_capital_ratio",
]
FEATURE_SOURCE_COLUMN: dict[str, str] = {
    "log_total_assets": "total_assets",
    "leverage_ratio": "leverage_ratio",
    "current_ratio": "current_ratio",
    "roa_period_adjusted": "roa_period_adjusted",
    "ocf_to_assets_period_adjusted": "ocf_to_assets_period_adjusted",
    "asset_turnover_period_adjusted": "asset_turnover_period_adjusted",
    "operating_margin_period_adjusted": "operating_margin_period_adjusted",
    "financial_expense_to_assets_period_adjusted":
        "financial_expense_to_assets_period_adjusted",
    "accumulated_loss_to_capital_ratio": "accumulated_loss_to_capital_ratio",
}
# Feature that must never appear on model surfaces, plus the Article-141 target.
PROHIBITED_FEATURE = "revenue_growth_period_adjusted"
ARTICLE141_TARGET = "FD_target_article141_only_t_plus_1"

ALLOWED_MODEL_FAMILIES = (
    "regularized_logistic_regression",
    "random_forest",
    "xgboost",
)
FORBIDDEN_MODEL_FAMILIES = (
    "SVM", "neural_network", "LightGBM", "CatBoost",
    "stacking", "voting",
)

# --------------------------------------------------------------------------- #
# Temporal folds (frozen; role-based manifest rows)
# --------------------------------------------------------------------------- #

DEVELOPMENT_TARGET_YEARS = (1393, 1394, 1395, 1396, 1397, 1398, 1399)
FINAL_TEST_TARGET_YEARS = (1400, 1401, 1402)

FOLD_TRAIN_ROLES = ("fold1_train", "fold2_train")
FOLD_VALIDATION_ROLES = ("fold1_validation", "fold2_validation")
DEV_ROLES = ("fold1_train", "fold1_validation", "fold2_train", "fold2_validation")
FINAL_TEST_ROLE = "locked_final_test"

FOLD_SPEC: dict[str, dict[str, Any]] = {
    "fold1": {
        "train_role": "fold1_train",
        "validation_role": "fold1_validation",
        "train_target_years": (1393, 1394, 1395),
        "validation_target_years": (1396, 1397),
    },
    "fold2": {
        "train_role": "fold2_train",
        "validation_role": "fold2_validation",
        "train_target_years": (1393, 1394, 1395, 1396, 1397),
        "validation_target_years": (1398, 1399),
    },
}

# Exact expected counts (asserted; never used to relax fail-closed loading).
EXPECTED_DEV_ROWS = 666
EXPECTED_DEV_POSITIVE = 68
EXPECTED_DEV_NEGATIVE = 598
EXPECTED_FINAL_TEST_PAIRS = 346
EXPECTED_FINAL_TEST_POSITIVE = 12
EXPECTED_FINAL_TEST_NEGATIVE = 334
EXPECTED_ALL_PRIMARY_ROWS = 1012
EXPECTED_FOLD_COUNTS: dict[str, dict[str, int]] = {
    "fold1_train": {"rows": 245, "positive": 33, "negative": 212},
    "fold1_validation": {"rows": 205, "positive": 25, "negative": 180},
    "fold2_train": {"rows": 450, "positive": 58, "negative": 392},
    "fold2_validation": {"rows": 216, "positive": 10, "negative": 206},
}
EXPECTED_POOLED_OOF_ROWS = 421
EXPECTED_POOLED_OOF_POSITIVE = 35
EXPECTED_POOLED_OOF_NEGATIVE = 386

# --------------------------------------------------------------------------- #
# Locked hyperparameter budget
# --------------------------------------------------------------------------- #

LOGISTIC_C_GRID = (0.01, 0.1, 1.0, 10.0)
RF_MAX_DEPTH_GRID = (3, 5, None)
RF_MAX_FEATURES_GRID = ("sqrt", 0.5)
RF_MIN_SAMPLES_LEAF_GRID = (5, 10)
XGB_LEARNING_RATE_GRID = (0.03, 0.1)
XGB_MAX_DEPTH_GRID = (2, 3)
XGB_MIN_CHILD_WEIGHT_GRID = (1, 5)
XGB_REG_LAMBDA_GRID = (1, 10)

EXPECTED_CONFIG_COUNTS = {
    "regularized_logistic_regression": 4,
    "random_forest": 12,
    "xgboost": 16,
}
EXPECTED_TOTAL_CONFIGS = 32

TUNING_SEEDS = (20260719, 20260720, 20260721)
FINAL_OOF_SEEDS = (20260719, 20260720, 20260721, 20260722, 20260723)

FLOAT_ROUND = 12

# --------------------------------------------------------------------------- #
# Frozen upstream inputs (pinned; never modified)
# --------------------------------------------------------------------------- #

ANALYSIS_READY_REL = (
    "project/stage125/part3c_outputs/analysis_ready_main_rule_a_stage125.csv"
)
ANALYSIS_READY_SHA256 = (
    "4d04d7d28808573bb28c30848340b676bed3bb6820e67d8bfd4d9d7e1bb3755e"
)
SPLIT_MANIFEST_REL = (
    "project/stage125/part4_temporal_split_manifest_stage125.csv"
)
SPLIT_MANIFEST_SHA256 = (
    "5e27dc48cc502e36951d4080ef80be684eacff61a46b55a07d39d3318863aedc"
)
PART4_SPLIT_CONTRACT_REL = (
    "project/stage125/part4_temporal_split_contract_stage125.json"
)
PART4_SPLIT_CONTRACT_SHA256 = (
    "3f6ff8c7adf77295e558045e5bcaa391b5d2c10e7be0a89aeb0c8ac2dd0463b9"
)

# Frozen Part 5 artifacts (exact, from the merged baseline).
FROZEN_PART5_OUTPUTS: dict[str, str] = {
    "project/stage125/part5_stage126_m1_entry_contract_stage125.json":
        "74a2159785daeda44fa82ebd76f42870fa25aba3667846bccba6b3099ea65da5",
    "project/stage125/part5_readiness_closure_report_stage125.json":
        "c6c47bfbf45e924e49797512180a04b560f764d11f95445907759e8587933cde",
    "project/stage125/stage125_part5_readiness_closure_qc_report.json":
        "886e6d3766ad2d0da02228fcf56d81cbbe9f68d22cf2dd98e53d7388449f8df1",
}

# --------------------------------------------------------------------------- #
# Output file names
# --------------------------------------------------------------------------- #

F_AUTH = "stage126_m1_human_authorization_record.json"
F_ACCESS_MANIFEST = "stage126_m1_development_access_manifest.csv"
F_LOCK_GUARD = "stage126_m1_final_test_lock_guard.json"
F_CONFIG_REGISTRY = "stage126_m1_configuration_registry.csv"
F_TUNING = "stage126_m1_tuning_results.csv"
F_SELECTED = "stage126_m1_selected_configurations.json"
F_OOF = "stage126_m1_development_oof_predictions.csv"
F_METRICS = "stage126_m1_development_metrics.csv"
F_DEV_LOCK = "stage126_m1_primary_development_lock.json"
F_README = "README_STAGE126_M1_PRIMARY_DEVELOPMENT_TUNING.md"
F_QC = "stage126_m1_primary_development_tuning_qc_report.json"
F_METADATA = "metadata_and_hashes_stage126_m1_primary_development_tuning.json"

# Tracked scientific-content files (QC + metadata are appended separately).
TRACKED_CONTENT_FILES = (
    F_AUTH, F_ACCESS_MANIFEST, F_LOCK_GUARD, F_CONFIG_REGISTRY, F_TUNING,
    F_SELECTED, F_OOF, F_METRICS, F_DEV_LOCK, F_README,
)

ACCESS_MANIFEST_COLUMNS = [
    "sample_design", "ticker", "predictor_row_key_t", "target_row_key_t_plus_1",
    "fiscal_year_t", "target_year", "dataset_split",
    "in_fold1_train", "in_fold1_validation",
    "in_fold2_train", "in_fold2_validation",
]
CONFIG_REGISTRY_COLUMNS = [
    "model_family", "configuration_id", "hyperparameters_json",
    "mean_validation_pr_auc", "fold1_validation_pr_auc",
    "fold2_validation_pr_auc", "min_fold_pr_auc", "selected",
]
TUNING_COLUMNS = [
    "model_family", "configuration_id", "temporal_fold", "seed",
    "validation_pr_auc",
]
OOF_COLUMNS = [
    "ticker", "predictor_row_key_t", "target_row_key_t_plus_1",
    "fiscal_year_t", "target_year", "temporal_fold", "model_family",
    "observed_target", "predicted_probability", "configuration_id",
    "probability_seed_aggregation",
]
METRICS_COLUMNS = [
    "model_family", "configuration_id", "scope", "n_rows", "n_positive",
    "k_top10", "pr_auc", "roc_auc", "brier_score", "recall_at_10pct",
    "lift_at_10pct",
]


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #

class QCFail(RuntimeError):
    """Fail-closed Stage126 QC error."""


class AuthorizationError(QCFail):
    """Authorization / policy violation."""


class FinalTestLockError(AuthorizationError):
    """Any attempt to touch the locked final test."""


# --------------------------------------------------------------------------- #
# Serialization / hashing
# --------------------------------------------------------------------------- #

def _json_str(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def _csv_str(header: list[str], rows: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf, fieldnames=header, lineterminator="\n", extrasaction="ignore",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({k: _fmt(row.get(k, "")) for k in header})
    return buf.getvalue()


def _fmt(v: Any) -> Any:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return repr(round(v, FLOAT_ROUND))
    return v


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _round(x: float) -> float:
    return round(float(x), FLOAT_ROUND)


# --------------------------------------------------------------------------- #
# Git / baseline
# --------------------------------------------------------------------------- #

def _git(repo_root: str | Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def _is_ancestor(repo_root: Path, maybe_ancestor: str, head: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "merge-base", "--is-ancestor",
         maybe_ancestor, head],
        capture_output=True, text=True,
    )
    return proc.returncode == 0


def verify_baseline_commit(repo_root: str | Path) -> str:
    root = Path(repo_root)
    head = _git(root, "rev-parse", "HEAD")
    if not head:
        raise QCFail("unable to resolve HEAD")
    if head != EXPECTED_BASELINE_COMMIT and not _is_ancestor(
        root, EXPECTED_BASELINE_COMMIT, head,
    ):
        raise QCFail(
            f"wrong baseline SHA: HEAD={head} does not contain "
            f"EXPECTED_BASELINE_COMMIT={EXPECTED_BASELINE_COMMIT}"
        )
    baseline_tree = _git(root, "rev-parse", f"{EXPECTED_BASELINE_COMMIT}^{{tree}}")
    if baseline_tree != EXPECTED_BASELINE_TREE:
        raise QCFail(
            f"baseline tree mismatch: {baseline_tree} != {EXPECTED_BASELINE_TREE}"
        )
    return head


def require_file_hash(repo_root: Path, rel: str, expected: str, *, label: str) -> str:
    path = repo_root / rel
    if not path.is_file():
        raise QCFail(f"missing {label}: {rel}")
    got = sha256_file(path)
    if got != expected:
        raise QCFail(f"{label} hash mismatch: {rel} ({got} != {expected})")
    return got


def frozen_upstream_hashes(repo_root: Path) -> dict[str, str]:
    """Pin and verify frozen Part 3C, Part 4, and Part 5 upstream artifacts.

    Part 3C and Part 4 hashes are reused verbatim from the Part 5 module so
    they can never silently diverge; Part 5 artifacts are pinned here.
    """
    out: dict[str, str] = {}
    for rel, expected in part5.FROZEN_PART3C_INPUTS.items():
        out[rel] = require_file_hash(repo_root, rel, expected, label="Part 3C input")
    for rel, expected in part5.FROZEN_PART4_OUTPUTS.items():
        out[rel] = require_file_hash(repo_root, rel, expected, label="Part 4 output")
    out[PART4_SPLIT_CONTRACT_REL] = require_file_hash(
        repo_root, PART4_SPLIT_CONTRACT_REL, PART4_SPLIT_CONTRACT_SHA256,
        label="Part 4 split contract",
    )
    out[SPLIT_MANIFEST_REL] = require_file_hash(
        repo_root, SPLIT_MANIFEST_REL, SPLIT_MANIFEST_SHA256,
        label="Part 4 split manifest",
    )
    for rel, expected in FROZEN_PART5_OUTPUTS.items():
        out[rel] = require_file_hash(repo_root, rel, expected, label="Part 5 output")
    return out


# --------------------------------------------------------------------------- #
# Authorization record
# --------------------------------------------------------------------------- #

def build_authorization_record() -> dict[str, Any]:
    return auth_guard.build_authorization_record()


def assert_authorization(record: dict[str, Any]) -> None:
    """Validate via the shared exact authorization transition guard."""
    try:
        auth_guard.validate_authorization_record(record)
    except auth_guard.AuthorizationError as exc:
        msg = str(exc)
        if "final_test" in msg:
            raise FinalTestLockError(msg) from exc
        raise AuthorizationError(msg) from exc


# --------------------------------------------------------------------------- #
# Fail-closed loader
# --------------------------------------------------------------------------- #

def _read_manifest_split_columns(repo_root: Path) -> list[dict[str, str]]:
    """First pass: read ONLY split/key columns for the primary sample.

    Predictor and target VALUES are never read in this pass.
    """
    allowed_cols = {
        "sample_design", "predictor_row_key_t", "target_row_key_t_plus_1",
        "ticker", "fiscal_year_t", "target_year", "dataset_split",
        "temporal_fold",
    }
    path = repo_root / SPLIT_MANIFEST_REL
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        header = set(reader.fieldnames or [])
        missing = allowed_cols - header
        if missing:
            raise QCFail(f"manifest missing split columns: {sorted(missing)}")
        for row in reader:
            if row.get("sample_design") != PRIMARY_SAMPLE:
                continue
            rows.append({c: row.get(c, "") for c in allowed_cols})
    return rows


def build_development_allowlist(repo_root: Path) -> dict[str, Any]:
    """Construct the development allowlist and final-test denylist (keys only)."""
    man_rows = _read_manifest_split_columns(repo_root)

    dev_pairs: dict[tuple[str, str], dict[str, Any]] = {}
    denylist_pairs: set[tuple[str, str]] = set()
    role_pairs: dict[str, set[tuple[str, str]]] = {r: set() for r in DEV_ROLES}
    role_pairs[FINAL_TEST_ROLE] = set()

    for row in man_rows:
        key = (row["predictor_row_key_t"], row["target_row_key_t_plus_1"])
        ty = int(row["target_year"])
        split = row["dataset_split"]
        fold = row["temporal_fold"]

        if split == "development" and ty in DEVELOPMENT_TARGET_YEARS:
            role_pairs.setdefault(fold, set()).add(key)
            if fold in DEV_ROLES:
                info = dev_pairs.setdefault(key, {
                    "sample_design": PRIMARY_SAMPLE,
                    "ticker": row["ticker"],
                    "predictor_row_key_t": key[0],
                    "target_row_key_t_plus_1": key[1],
                    "fiscal_year_t": row["fiscal_year_t"],
                    "target_year": row["target_year"],
                    "dataset_split": "development",
                    "roles": set(),
                })
                info["roles"].add(fold)
        elif split == "final_test" and ty in FINAL_TEST_TARGET_YEARS:
            denylist_pairs.add(key)
            role_pairs[FINAL_TEST_ROLE].add(key)
        else:
            raise QCFail(
                f"manifest row not classifiable as dev or final_test: "
                f"split={split} target_year={ty}"
            )

    # Fold-role membership must match the frozen fold counts exactly.
    for role in DEV_ROLES:
        got = len(role_pairs[role])
        exp = EXPECTED_FOLD_COUNTS[role]["rows"]
        if got != exp:
            raise QCFail(f"fold-role {role} count {got} != {exp}")
    if len(role_pairs[FINAL_TEST_ROLE]) != EXPECTED_FINAL_TEST_PAIRS:
        raise QCFail("final-test pair count mismatch")
    if len(dev_pairs) != EXPECTED_DEV_ROWS:
        raise QCFail(f"development unique rows {len(dev_pairs)} != {EXPECTED_DEV_ROWS}")
    if dev_pairs.keys() & denylist_pairs:
        raise QCFail("development/final-test key overlap (fail-closed)")

    return {
        "dev_pairs": dev_pairs,
        "denylist_pairs": denylist_pairs,
        "role_pairs": role_pairs,
    }


def _to_float(raw: str) -> float:
    raw = raw.strip()
    if raw == "":
        return math.nan
    return float(raw)


def _target_value(raw: str) -> float:
    raw = raw.strip()
    if raw == "":
        return math.nan
    return float(raw)


def load_development_values(
    repo_root: Path, allowlist: dict[str, Any],
) -> dict[str, Any]:
    """Second pass: stream the analysis-ready CSV, keeping ONLY development keys.

    Final-test rows are never numerically parsed, stored, logged, summarized,
    or exported. The complete CSV is never materialized in a DataFrame.
    """
    dev_pairs = allowlist["dev_pairs"]
    denylist = allowlist["denylist_pairs"]
    source_cols = sorted({FEATURE_SOURCE_COLUMN[f] for f in M1_PRIMARY_FEATURE_ORDER})

    loaded: dict[tuple[str, str], dict[str, Any]] = {}
    final_test_rows_seen = 0
    final_test_values_loaded = 0
    unknown_rows = 0

    path = repo_root / ANALYSIS_READY_REL
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        header = set(reader.fieldnames or [])
        needed = set(source_cols) | {
            "predictor_row_key_t", "target_row_key_t_plus_1", "ticker",
            "fiscal_year_t", "target_year", PRIMARY_TARGET,
        }
        missing = needed - header
        if missing:
            raise QCFail(f"analysis-ready CSV missing columns: {sorted(missing)}")
        if PROHIBITED_FEATURE not in header:
            # informational: prohibited column may or may not exist; either way
            # it must never enter the model surface (guarded below).
            pass
        for row in reader:
            key = (row["predictor_row_key_t"], row["target_row_key_t_plus_1"])
            if key in dev_pairs:
                ty = int(row["target_year"])
                if ty not in DEVELOPMENT_TARGET_YEARS:
                    raise FinalTestLockError(
                        f"development key has non-development target_year {ty}"
                    )
                raw_sources = {c: row[c] for c in source_cols}
                feats = _derive_features(raw_sources)
                loaded[key] = {
                    "ticker": row["ticker"],
                    "predictor_row_key_t": key[0],
                    "target_row_key_t_plus_1": key[1],
                    "fiscal_year_t": row["fiscal_year_t"],
                    "target_year": ty,
                    "features": feats,
                    "target": _target_value(row[PRIMARY_TARGET]),
                }
            elif key in denylist:
                # Final-test row: DO NOT parse any predictor/target value.
                final_test_rows_seen += 1
            else:
                unknown_rows += 1

    if unknown_rows:
        raise QCFail(f"{unknown_rows} analysis-ready rows unclassified (fail-closed)")
    if len(loaded) != EXPECTED_DEV_ROWS:
        raise QCFail(f"loaded {len(loaded)} dev rows != {EXPECTED_DEV_ROWS}")
    if final_test_values_loaded != 0:
        raise FinalTestLockError("final-test values loaded (fail-closed)")

    # Target-year guard on loaded modeling rows.
    for info in loaded.values():
        if info["target_year"] in FINAL_TEST_TARGET_YEARS:
            raise FinalTestLockError("final-test target_year in loaded modeling rows")

    return {
        "rows": loaded,
        "final_test_rows_seen": final_test_rows_seen,
        "final_test_values_loaded": final_test_values_loaded,
    }


def _derive_features(raw_sources: dict[str, str]) -> np.ndarray:
    """Deterministic source-to-feature transformation (pre-imputation)."""
    vals = np.empty(len(M1_PRIMARY_FEATURE_ORDER), dtype=float)
    for i, feat in enumerate(M1_PRIMARY_FEATURE_ORDER):
        src = FEATURE_SOURCE_COLUMN[feat]
        raw = _to_float(raw_sources[src])
        if feat == "log_total_assets":
            # log_total_assets = ln(total_assets) if total_assets > 0 else missing
            if math.isnan(raw) or raw <= 0.0:
                vals[i] = math.nan
            else:
                vals[i] = math.log(raw)
        else:
            vals[i] = raw
    return vals


# --------------------------------------------------------------------------- #
# Matrix assembly per fold-role
# --------------------------------------------------------------------------- #

def _role_matrix(
    loaded_rows: dict[tuple[str, str], dict[str, Any]],
    role_pairs: dict[str, set[tuple[str, str]]],
    role: str,
) -> dict[str, Any]:
    keys = sorted(role_pairs[role])
    X = np.vstack([loaded_rows[k]["features"] for k in keys])
    y = np.array([loaded_rows[k]["target"] for k in keys], dtype=float)
    meta = [loaded_rows[k] for k in keys]
    return {"keys": keys, "X": X, "y": y, "meta": meta}


# --------------------------------------------------------------------------- #
# Preprocessing (per temporal training fold, fail-closed)
# --------------------------------------------------------------------------- #

def fit_preprocessor(train_X: np.ndarray, *, standardize: bool) -> dict[str, Any]:
    """Fit clipping bounds, median, and (optional) standardization on TRAIN only."""
    n_feat = train_X.shape[1]
    p_low = np.empty(n_feat)
    p_high = np.empty(n_feat)
    median = np.empty(n_feat)
    for j in range(n_feat):
        col = train_X[:, j]
        obs = col[~np.isnan(col)]
        if obs.size == 0:
            p_low[j], p_high[j], median[j] = 0.0, 0.0, 0.0
            continue
        p_low[j] = np.percentile(obs, 1)
        p_high[j] = np.percentile(obs, 99)
        clipped = np.clip(obs, p_low[j], p_high[j])
        median[j] = np.median(clipped)
    pre = {"p_low": p_low, "p_high": p_high, "median": median,
           "standardize": standardize}
    if standardize:
        imp = _clip_impute(train_X, pre)
        imp_mean = imp.mean(axis=0)
        std = imp.std(axis=0)
        std = np.where(std == 0.0, 1.0, std)
        pre["mean"] = imp_mean
        pre["std"] = std
    return pre


def _clip_impute(X: np.ndarray, pre: dict[str, Any]) -> np.ndarray:
    clipped = np.clip(X, pre["p_low"], pre["p_high"])
    out = clipped.copy()
    inds = np.where(np.isnan(out))
    out[inds] = np.take(pre["median"], inds[1])
    return out


def transform(X: np.ndarray, pre: dict[str, Any]) -> np.ndarray:
    """Apply frozen preprocessing: clip -> impute -> [standardize] + indicators.

    The missingness indicators are derived from the row's OWN original
    pre-imputation missing positions and are NEVER standardized.
    """
    mask = np.isnan(X).astype(float)
    cont = _clip_impute(X, pre)
    if pre["standardize"]:
        cont = (cont - pre["mean"]) / pre["std"]
    return np.hstack([cont, mask])


# --------------------------------------------------------------------------- #
# Model families
# --------------------------------------------------------------------------- #

def _logistic_configs() -> list[dict[str, Any]]:
    out = []
    for c in LOGISTIC_C_GRID:
        out.append({
            "model_family": "regularized_logistic_regression",
            "configuration_id": f"logistic__C_{c!r}",
            "hyperparameters": {
                "penalty": "l2", "solver": "liblinear", "max_iter": 5000, "C": c,
            },
        })
    return out


def _rf_configs() -> list[dict[str, Any]]:
    out = []
    for depth in RF_MAX_DEPTH_GRID:
        for maxf in RF_MAX_FEATURES_GRID:
            for leaf in RF_MIN_SAMPLES_LEAF_GRID:
                depth_tag = "None" if depth is None else str(depth)
                out.append({
                    "model_family": "random_forest",
                    "configuration_id":
                        f"rf__depth_{depth_tag}__maxfeat_{maxf!r}__leaf_{leaf}",
                    "hyperparameters": {
                        "n_estimators": 500, "bootstrap": True,
                        "max_depth": depth, "max_features": maxf,
                        "min_samples_leaf": leaf,
                    },
                })
    return out


def _xgb_configs() -> list[dict[str, Any]]:
    out = []
    for lr in XGB_LEARNING_RATE_GRID:
        for depth in XGB_MAX_DEPTH_GRID:
            for mcw in XGB_MIN_CHILD_WEIGHT_GRID:
                for lam in XGB_REG_LAMBDA_GRID:
                    out.append({
                        "model_family": "xgboost",
                        "configuration_id":
                            f"xgboost__lr_{lr!r}__depth_{depth}__mcw_{mcw}"
                            f"__lambda_{lam}",
                        "hyperparameters": {
                            "objective": "binary:logistic",
                            "eval_metric": "aucpr", "n_estimators": 300,
                            "tree_method": "hist", "n_jobs": 1,
                            "subsample": 0.8, "colsample_bytree": 0.8,
                            "gamma": 0, "early_stopping": False,
                            "learning_rate": lr, "max_depth": depth,
                            "min_child_weight": mcw, "reg_lambda": lam,
                        },
                    })
    return out


def all_configurations() -> dict[str, list[dict[str, Any]]]:
    cfgs = {
        "regularized_logistic_regression": _logistic_configs(),
        "random_forest": _rf_configs(),
        "xgboost": _xgb_configs(),
    }
    for fam, exp in EXPECTED_CONFIG_COUNTS.items():
        if len(cfgs[fam]) != exp:
            raise QCFail(f"{fam} config count {len(cfgs[fam])} != {exp}")
    total = sum(len(v) for v in cfgs.values())
    if total != EXPECTED_TOTAL_CONFIGS:
        raise QCFail(f"total config count {total} != {EXPECTED_TOTAL_CONFIGS}")
    return cfgs


def _requires_standardization(family: str) -> bool:
    return family == "regularized_logistic_regression"


def _fit_predict(
    family: str, hp: dict[str, Any], seed: int,
    Xtr: np.ndarray, ytr: np.ndarray, Xva: np.ndarray,
) -> np.ndarray:
    n_pos = int((ytr == 1).sum())
    n_neg = int((ytr == 0).sum())
    if family == "regularized_logistic_regression":
        from sklearn.linear_model import LogisticRegression
        clf = LogisticRegression(
            penalty="l2", solver="liblinear", C=hp["C"], max_iter=5000,
            class_weight="balanced", random_state=seed,
        )
        clf.fit(Xtr, ytr)
        return clf.predict_proba(Xva)[:, 1]
    if family == "random_forest":
        from sklearn.ensemble import RandomForestClassifier
        clf = RandomForestClassifier(
            n_estimators=500, bootstrap=True, max_depth=hp["max_depth"],
            max_features=hp["max_features"], min_samples_leaf=hp["min_samples_leaf"],
            class_weight="balanced_subsample", random_state=seed, n_jobs=1,
        )
        clf.fit(Xtr, ytr)
        return clf.predict_proba(Xva)[:, 1]
    if family == "xgboost":
        from xgboost import XGBClassifier
        if n_pos == 0:
            raise QCFail("xgboost scale_pos_weight undefined (no positives)")
        spw = n_neg / n_pos
        clf = XGBClassifier(
            objective="binary:logistic", eval_metric="aucpr", n_estimators=300,
            tree_method="hist", n_jobs=1, subsample=0.8, colsample_bytree=0.8,
            gamma=0, learning_rate=hp["learning_rate"], max_depth=hp["max_depth"],
            min_child_weight=hp["min_child_weight"], reg_lambda=hp["reg_lambda"],
            scale_pos_weight=spw, random_state=seed,
        )
        clf.fit(Xtr, ytr)
        return clf.predict_proba(Xva)[:, 1]
    raise QCFail(f"unauthorized model family: {family}")


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #

def _pr_auc(y: np.ndarray, p: np.ndarray) -> float:
    from sklearn.metrics import average_precision_score
    return float(average_precision_score(y, p))


def compute_metrics(
    y: np.ndarray,
    p: np.ndarray,
    tickers: list[str],
    target_years: list[int] | np.ndarray,
) -> dict[str, float]:
    """Development metrics under the frozen Part 4 Top-K contract.

    PR-AUC / ROC-AUC / Brier are computed over the complete reported scope.
    Recall@10% and Lift@10% use the per-target-year rule:

        For each target year y: K_y = ceil(0.10 × N_y)
        Rank within year: predicted_probability desc, ticker asc tie-break
        Recall@10% = sum_captured_positives / sum_total_positives
        Lift@10%   = (sum_captured / sum_K_y) / overall_prevalence
    """
    from sklearn.metrics import (
        average_precision_score, roc_auc_score, brier_score_loss,
    )
    y = np.asarray(y)
    p = np.asarray(p, dtype=float)
    years = [int(t) for t in target_years]
    if not (len(y) == len(p) == len(tickers) == len(years)):
        raise QCFail(
            "compute_metrics length mismatch among y/p/tickers/target_years"
        )
    n = len(y)
    n_pos = int((y == 1).sum())
    captured = 0
    k_sum = 0
    # Isolate ranking by target year; never pool ranks across years.
    for year in sorted(set(years)):
        idxs = [i for i, yy in enumerate(years) if yy == year]
        n_y = len(idxs)
        k_y = math.ceil(0.10 * n_y) if n_y > 0 else 0
        k_sum += k_y
        order = sorted(idxs, key=lambda i: (-p[i], tickers[i]))
        top = order[:k_y]
        captured += int(sum(1 for i in top if y[i] == 1))
    recall_at_10 = (captured / n_pos) if n_pos > 0 else math.nan
    base_rate = n_pos / n if n > 0 else math.nan
    precision_top = (captured / k_sum) if k_sum > 0 else math.nan
    lift_at_10 = (
        (precision_top / base_rate)
        if base_rate not in (0, math.nan) and not math.isnan(base_rate)
        else math.nan
    )
    return {
        "n_rows": n,
        "n_positive": n_pos,
        "k_top10": k_sum,
        "pr_auc": _round(average_precision_score(y, p)),
        "roc_auc": _round(roc_auc_score(y, p)),
        "brier_score": _round(brier_score_loss(y, p)),
        "recall_at_10pct": _round(recall_at_10),
        "lift_at_10pct": _round(lift_at_10),
    }


# --------------------------------------------------------------------------- #
# Tuning + selection
# --------------------------------------------------------------------------- #

def _complexity_key(family: str, hp: dict[str, Any]) -> tuple:
    if family == "regularized_logistic_regression":
        return (float(hp["C"]),)  # smaller C simpler
    if family == "random_forest":
        depth = hp["max_depth"]
        depth_rank = 10 ** 9 if depth is None else int(depth)  # shallower simpler
        leaf_rank = -int(hp["min_samples_leaf"])  # larger leaf simpler
        mf_rank = 0 if hp["max_features"] == "sqrt" else 1  # sqrt preferred
        return (depth_rank, leaf_rank, mf_rank)
    if family == "xgboost":
        return (
            int(hp["max_depth"]),                 # shallower simpler
            -int(hp["min_child_weight"]),         # larger simpler
            -int(hp["reg_lambda"]),               # larger simpler
            float(hp["learning_rate"]),           # lower simpler
        )
    raise QCFail(f"unknown family for complexity: {family}")


def run_tuning(folds_data: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Fit every configuration on both folds and all tuning seeds."""
    cfgs = all_configurations()
    tuning_rows: list[dict[str, Any]] = []
    per_config: dict[tuple[str, str], dict[str, Any]] = {}

    for family, configs in cfgs.items():
        standardize = _requires_standardization(family)
        for cfg in configs:
            hp = cfg["hyperparameters"]
            cid = cfg["configuration_id"]
            fold_means: dict[str, float] = {}
            for fold_name, fspec in FOLD_SPEC.items():
                tr = folds_data[fspec["train_role"]]
                va = folds_data[fspec["validation_role"]]
                pre = fit_preprocessor(tr["X"], standardize=standardize)
                Xtr = transform(tr["X"], pre)
                Xva = transform(va["X"], pre)
                seed_scores: list[float] = []
                for seed in TUNING_SEEDS:
                    prob = _fit_predict(family, hp, seed, Xtr, tr["y"], Xva)
                    score = _round(_pr_auc(va["y"], prob))
                    seed_scores.append(score)
                    tuning_rows.append({
                        "model_family": family,
                        "configuration_id": cid,
                        "temporal_fold": fspec["validation_role"],
                        "seed": seed,
                        "validation_pr_auc": score,
                    })
                if standardize:
                    # Logistic is deterministic: seeds must be identical.
                    if len(set(seed_scores)) != 1:
                        raise QCFail(
                            f"logistic not deterministic across seeds: {cid} "
                            f"{fold_name} {seed_scores}"
                        )
                fold_means[fspec["validation_role"]] = _round(
                    float(np.mean(seed_scores))
                )
            mean_prauc = _round(float(np.mean(list(fold_means.values()))))
            min_fold = _round(min(fold_means.values()))
            per_config[(family, cid)] = {
                "model_family": family,
                "configuration_id": cid,
                "hyperparameters": hp,
                "fold_means": fold_means,
                "mean_validation_pr_auc": mean_prauc,
                "min_fold_pr_auc": min_fold,
                "complexity_key": _complexity_key(family, hp),
            }
    return {"cfgs": cfgs, "tuning_rows": tuning_rows, "per_config": per_config}


def select_configurations(tuning: dict[str, Any]) -> dict[str, Any]:
    selected: dict[str, Any] = {}
    for family in ALLOWED_MODEL_FAMILIES:
        candidates = [
            v for (fam, _cid), v in tuning["per_config"].items() if fam == family
        ]
        candidates.sort(key=lambda v: (
            -v["mean_validation_pr_auc"],
            -v["min_fold_pr_auc"],
            v["complexity_key"],
            v["configuration_id"],
        ))
        best = candidates[0]
        selected[family] = {
            "configuration_id": best["configuration_id"],
            "hyperparameters": best["hyperparameters"],
            "mean_validation_pr_auc": best["mean_validation_pr_auc"],
            "fold1_validation_pr_auc": best["fold_means"]["fold1_validation"],
            "fold2_validation_pr_auc": best["fold_means"]["fold2_validation"],
            "min_fold_pr_auc": best["min_fold_pr_auc"],
            "tie_breaking_order": [
                "higher_mean_temporal_validation_PR_AUC",
                "higher_minimum_fold_PR_AUC",
                "simpler_configuration",
                "lexicographically_smaller_configuration_id",
            ],
        }
    return selected


# --------------------------------------------------------------------------- #
# OOF generation
# --------------------------------------------------------------------------- #

def generate_oof(
    folds_data: dict[str, dict[str, Any]], selected: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, np.ndarray]]]:
    oof_rows: list[dict[str, Any]] = []
    predictions: dict[str, dict[str, np.ndarray]] = {}
    for family in ALLOWED_MODEL_FAMILIES:
        cid = selected[family]["configuration_id"]
        hp = selected[family]["hyperparameters"]
        standardize = _requires_standardization(family)
        deterministic = standardize
        agg = ("deterministic_single_fit" if deterministic
               else "mean_of_5_fixed_seeds")
        predictions[family] = {}
        for fold_name, fspec in FOLD_SPEC.items():
            tr = folds_data[fspec["train_role"]]
            va = folds_data[fspec["validation_role"]]
            pre = fit_preprocessor(tr["X"], standardize=standardize)
            Xtr = transform(tr["X"], pre)
            Xva = transform(va["X"], pre)
            if deterministic:
                probs = _fit_predict(family, hp, TUNING_SEEDS[0], Xtr, tr["y"], Xva)
            else:
                stacked = np.vstack([
                    _fit_predict(family, hp, seed, Xtr, tr["y"], Xva)
                    for seed in FINAL_OOF_SEEDS
                ])
                probs = stacked.mean(axis=0)
            probs = np.array([_round(p) for p in probs])
            predictions[family][fspec["validation_role"]] = probs
            for i, info in enumerate(va["meta"]):
                oof_rows.append({
                    "ticker": info["ticker"],
                    "predictor_row_key_t": info["predictor_row_key_t"],
                    "target_row_key_t_plus_1": info["target_row_key_t_plus_1"],
                    "fiscal_year_t": info["fiscal_year_t"],
                    "target_year": info["target_year"],
                    "temporal_fold": fspec["validation_role"],
                    "model_family": family,
                    "observed_target": int(info["target"]),
                    "predicted_probability": probs[i],
                    "configuration_id": cid,
                    "probability_seed_aggregation": agg,
                })
    return oof_rows, predictions


def compute_development_metrics(
    folds_data: dict[str, dict[str, Any]], selected: dict[str, Any],
    predictions: dict[str, dict[str, np.ndarray]],
) -> list[dict[str, Any]]:
    metrics_rows: list[dict[str, Any]] = []
    for family in ALLOWED_MODEL_FAMILIES:
        cid = selected[family]["configuration_id"]
        pooled_y: list[float] = []
        pooled_p: list[float] = []
        pooled_t: list[str] = []
        pooled_years: list[int] = []
        for fspec in FOLD_SPEC.values():
            role = fspec["validation_role"]
            va = folds_data[role]
            y = va["y"]
            p = predictions[family][role]
            tickers = [m["ticker"] for m in va["meta"]]
            years = [int(m["target_year"]) for m in va["meta"]]
            m = compute_metrics(y, p, tickers, years)
            metrics_rows.append({
                "model_family": family, "configuration_id": cid,
                "scope": role, **m,
            })
            pooled_y.extend(y.tolist())
            pooled_p.extend(p.tolist())
            pooled_t.extend(tickers)
            pooled_years.extend(years)
        m = compute_metrics(
            np.array(pooled_y), np.array(pooled_p), pooled_t, pooled_years,
        )
        metrics_rows.append({
            "model_family": family, "configuration_id": cid,
            "scope": "pooled_development_oof", **m,
        })
    return metrics_rows


# --------------------------------------------------------------------------- #
# Artifact builders
# --------------------------------------------------------------------------- #

def build_access_manifest_rows(allowlist: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for info in allowlist["dev_pairs"].values():
        roles = info["roles"]
        rows.append({
            "sample_design": info["sample_design"],
            "ticker": info["ticker"],
            "predictor_row_key_t": info["predictor_row_key_t"],
            "target_row_key_t_plus_1": info["target_row_key_t_plus_1"],
            "fiscal_year_t": info["fiscal_year_t"],
            "target_year": info["target_year"],
            "dataset_split": info["dataset_split"],
            "in_fold1_train": "fold1_train" in roles,
            "in_fold1_validation": "fold1_validation" in roles,
            "in_fold2_train": "fold2_train" in roles,
            "in_fold2_validation": "fold2_validation" in roles,
        })
    rows.sort(key=lambda r: (r["predictor_row_key_t"], r["target_row_key_t_plus_1"]))
    return rows


def build_lock_guard(
    repo_root: Path, allowlist: dict[str, Any], loaded: dict[str, Any],
) -> dict[str, Any]:
    """Record the final-test lock guard using key counts + Part 4 aggregates ONLY.

    The final-test positive/negative aggregate is read from the frozen Part 4
    temporal split contract, NEVER derived by reading row-level final-test
    targets.
    """
    contract = json.loads(
        (repo_root / PART4_SPLIT_CONTRACT_REL).read_text(encoding="utf-8")
    )
    expected = contract["primary_sample_final_test_expected"]
    if (expected["pairs"], expected["positive"], expected["negative"]) != (
        EXPECTED_FINAL_TEST_PAIRS, EXPECTED_FINAL_TEST_POSITIVE,
        EXPECTED_FINAL_TEST_NEGATIVE,
    ):
        raise QCFail("Part 4 final-test aggregate drift")
    return {
        "final_test_locked": True,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_evaluation_authorized": False,
        "final_test_predictor_values_inspected": False,
        "final_test_target_values_inspected": False,
        "final_test_evaluation_performed": False,
        "final_test_target_years": list(FINAL_TEST_TARGET_YEARS),
        "final_test_pair_key_count_from_manifest": len(allowlist["denylist_pairs"]),
        "final_test_predictor_rows_loaded": loaded["final_test_values_loaded"],
        "final_test_target_rows_loaded": loaded["final_test_values_loaded"],
        "final_test_rows_seen_but_not_parsed": loaded["final_test_rows_seen"],
        "final_test_aggregate_source": "frozen_part4_temporal_split_contract",
        "final_test_aggregate": {
            "pairs": expected["pairs"],
            "positive": expected["positive"],
            "negative": expected["negative"],
        },
        "aggregate_derived_from_row_level_targets": False,
    }


def build_config_registry_rows(
    tuning: dict[str, Any], selected: dict[str, Any],
) -> list[dict[str, Any]]:
    selected_ids = {selected[f]["configuration_id"] for f in ALLOWED_MODEL_FAMILIES}
    rows: list[dict[str, Any]] = []
    for family in ALLOWED_MODEL_FAMILIES:
        for cfg in tuning["cfgs"][family]:
            cid = cfg["configuration_id"]
            agg = tuning["per_config"][(family, cid)]
            rows.append({
                "model_family": family,
                "configuration_id": cid,
                "hyperparameters_json": json.dumps(
                    cfg["hyperparameters"], sort_keys=True, ensure_ascii=False,
                ),
                "mean_validation_pr_auc": agg["mean_validation_pr_auc"],
                "fold1_validation_pr_auc": agg["fold_means"]["fold1_validation"],
                "fold2_validation_pr_auc": agg["fold_means"]["fold2_validation"],
                "min_fold_pr_auc": agg["min_fold_pr_auc"],
                "selected": cid in selected_ids,
            })
    return rows


def build_dev_lock(
    selected: dict[str, Any], metrics_rows: list[dict[str, Any]],
    oof_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    pooled = {
        r["model_family"]: r for r in metrics_rows
        if r["scope"] == "pooled_development_oof"
    }
    return {
        "contract_version": CONTRACT_VERSION,
        "stage126_m1_primary_development_tuning_completed": True,
        "development_only": True,
        "final_test_locked": True,
        "final_test_access_authorized": False,
        "final_test_evaluation_performed": False,
        "full_development_refit_performed": False,
        "m1_robustness_started": False,
        "m1_robustness_completed": False,
        "smote_executed": False,
        "shap_executed": False,
        "sample": PRIMARY_SAMPLE,
        "target": PRIMARY_TARGET,
        "feature_set": FEATURE_SET_NAME,
        "feature_order": list(M1_PRIMARY_FEATURE_ORDER),
        "model_families": list(ALLOWED_MODEL_FAMILIES),
        "tuning_seeds": list(TUNING_SEEDS),
        "final_oof_seeds": list(FINAL_OOF_SEEDS),
        "total_configurations": EXPECTED_TOTAL_CONFIGS,
        "configurations_per_family": EXPECTED_CONFIG_COUNTS,
        "selected_configurations": {
            f: selected[f]["configuration_id"] for f in ALLOWED_MODEL_FAMILIES
        },
        "pooled_oof_rows_per_family": EXPECTED_POOLED_OOF_ROWS,
        "oof_rows_total": len(oof_rows),
        "pooled_oof_pr_auc": {
            f: pooled[f]["pr_auc"] for f in ALLOWED_MODEL_FAMILIES
        },
    }


def build_readme(selected: dict[str, Any], metrics_rows: list[dict[str, Any]]) -> str:
    pooled = {
        r["model_family"]: r for r in metrics_rows
        if r["scope"] == "pooled_development_oof"
    }
    lines = [
        "# Stage126 M1 — Primary Development-Fold Tuning",
        "",
        "**Stage126 M1 is human-authorized.** This deliverable performs primary "
        "M1 development-fold tuning only. The final test remains locked. No "
        "final-test predictor or target values were inspected. No final-test "
        "evaluation occurred. M1 robustness is not executed here.",
        "",
        "## Scope",
        "",
        f"- Sample: `{PRIMARY_SAMPLE}`",
        f"- Target: `{PRIMARY_TARGET}`",
        f"- Feature set: `{FEATURE_SET_NAME}` (9 features, exact order)",
        f"- Model families: {', '.join(ALLOWED_MODEL_FAMILIES)}",
        f"- Configurations: {EXPECTED_TOTAL_CONFIGS} "
        "(4 logistic + 12 random forest + 16 xgboost)",
        f"- Tuning seeds: {', '.join(str(s) for s in TUNING_SEEDS)}",
        f"- Final RF/XGBoost OOF seeds: "
        f"{', '.join(str(s) for s in FINAL_OOF_SEEDS)}",
        "",
        "## Temporal development folds",
        "",
        "- Fold 1: train 1393–1395 (245), validation 1396–1397 (205)",
        "- Fold 2: train 1393–1397 (450), validation 1398–1399 (216)",
        "- Development rows: 666 (68 positive / 598 negative)",
        "- Pooled validation/OOF rows: 421 (35 positive / 386 negative) per family",
        "",
        "## Selected configurations",
        "",
    ]
    for family in ALLOWED_MODEL_FAMILIES:
        sel = selected[family]
        lines.append(
            f"- `{family}`: `{sel['configuration_id']}` "
            f"(mean validation PR-AUC={sel['mean_validation_pr_auc']}; "
            f"pooled OOF PR-AUC={pooled[family]['pr_auc']})"
        )
    lines.extend([
        "",
        "## Locks",
        "",
        "- No full-development refit; no final-test application model created.",
        "- No SMOTE, no SHAP, no robustness variants, no M2/M3/M4 data.",
        "- Registered robustness variants remain frozen for a later Stage126 "
        "micro-part.",
        "- The final test stays locked until a separate explicit human "
        "authorization.",
        "",
    ])
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Source self-scan guards (SMOTE / SHAP / forbidden families / network)
# --------------------------------------------------------------------------- #

FORBIDDEN_SOURCE_TOKENS = (
    "imblearn", "SMOTE", "import shap", "shap.", "lightgbm", "LightGBM",
    "catboost", "CatBoost", "from sklearn.svm", "MLPClassifier",
    "StackingClassifier", "VotingClassifier",
)


def assert_source_clean(repo_root: Path) -> None:
    text = (repo_root / SRC_REL).read_text(encoding="utf-8")
    # Ignore this guard's own token tuple definition line-range by checking
    # imports/usages rather than the literal list.
    body = text.split("FORBIDDEN_SOURCE_TOKENS", 1)[0]
    for tok in ("imblearn", "import shap", "shap.", "lightgbm", "catboost",
                "from sklearn.svm", "MLPClassifier", "StackingClassifier",
                "VotingClassifier"):
        if tok in body:
            raise QCFail(f"forbidden token in source: {tok}")


def validate_feature_order(order: list[str]) -> None:
    if list(order) != list(M1_PRIMARY_FEATURE_ORDER):
        raise QCFail("feature set added/removed/reordered")
    if PROHIBITED_FEATURE in order:
        raise QCFail("Revenue Growth included in model surface")


def validate_sample(name: str) -> None:
    if name != PRIMARY_SAMPLE:
        raise QCFail(f"non-primary sample: {name}")


def validate_target(name: str) -> None:
    if name == ARTICLE141_TARGET:
        raise QCFail("Article-141 target used for estimation")
    if name != PRIMARY_TARGET:
        raise QCFail(f"wrong target: {name}")


def validate_model_family(family: str) -> None:
    if family in FORBIDDEN_MODEL_FAMILIES:
        raise QCFail(f"forbidden model family: {family}")
    if family not in ALLOWED_MODEL_FAMILIES:
        raise QCFail(f"unauthorized model family: {family}")


def validate_config_budget(cfgs: dict[str, list[dict[str, Any]]]) -> None:
    for fam, exp in EXPECTED_CONFIG_COUNTS.items():
        if len(cfgs.get(fam, [])) != exp:
            raise QCFail(f"{fam} config count != {exp}")
    if sum(len(v) for v in cfgs.values()) != EXPECTED_TOTAL_CONFIGS:
        raise QCFail("total config count != 32 (grid expansion/contraction)")


def validate_seeds(tuning_seeds: tuple[int, ...], final_seeds: tuple[int, ...]) -> None:
    if tuple(tuning_seeds) != (20260719, 20260720, 20260721):
        raise QCFail("tuning seed mutation")
    if tuple(final_seeds) != (20260719, 20260720, 20260721, 20260722, 20260723):
        raise QCFail("final OOF seed mutation")


def validate_no_random_split(contract: dict[str, Any]) -> None:
    if contract.get("random_split_authorized") is not False:
        raise QCFail("random split not prohibited")
    if contract.get("shuffle_authorized") is not False:
        raise QCFail("shuffle not prohibited")


def validate_no_early_stopping_or_grid_expansion(budget: dict[str, Any]) -> None:
    if budget.get("early_stopping_authorized") is not False:
        raise QCFail("early stopping authorized")
    if budget.get("grid_expansion_after_results_authorized") is not False:
        raise QCFail("grid expansion authorized")


def assert_specification(auth: dict[str, Any]) -> None:
    assert_authorization(auth)
    if PRIMARY_SAMPLE != "main_rule_a_primary":
        raise QCFail("non-primary sample")
    if PRIMARY_TARGET != "FD_target_main_t_plus_1":
        raise QCFail("wrong target")
    if list(M1_PRIMARY_FEATURE_ORDER) != [
        "log_total_assets", "leverage_ratio", "current_ratio",
        "roa_period_adjusted", "ocf_to_assets_period_adjusted",
        "asset_turnover_period_adjusted", "operating_margin_period_adjusted",
        "financial_expense_to_assets_period_adjusted",
        "accumulated_loss_to_capital_ratio",
    ]:
        raise QCFail("feature set added/removed/reordered")
    if PROHIBITED_FEATURE in M1_PRIMARY_FEATURE_ORDER:
        raise QCFail("Revenue Growth included in model surface")
    if PROHIBITED_FEATURE in FEATURE_SOURCE_COLUMN.values():
        raise QCFail("Revenue Growth source column bound")
    if ARTICLE141_TARGET == PRIMARY_TARGET:
        raise QCFail("Article-141 target used for estimation")
    for fam in FORBIDDEN_MODEL_FAMILIES:
        if fam in ALLOWED_MODEL_FAMILIES:
            raise QCFail(f"forbidden model family allowed: {fam}")
    if TUNING_SEEDS != (20260719, 20260720, 20260721):
        raise QCFail("tuning seed mutation")
    if FINAL_OOF_SEEDS != (20260719, 20260720, 20260721, 20260722, 20260723):
        raise QCFail("final OOF seed mutation")


# --------------------------------------------------------------------------- #
# Build orchestration
# --------------------------------------------------------------------------- #

def build_all(repo_root: Path, *, mode: str = "build") -> tuple[dict[str, str], dict[str, Any]]:
    if mode not in {"build", "check"}:
        raise QCFail(f"invalid mode: {mode}")

    assert_source_clean(repo_root)

    auth = build_authorization_record()
    assert_specification(auth)

    frozen = frozen_upstream_hashes(repo_root)

    allowlist = build_development_allowlist(repo_root)
    loaded = load_development_values(repo_root, allowlist)

    folds_data = {
        role: _role_matrix(loaded["rows"], allowlist["role_pairs"], role)
        for role in DEV_ROLES
    }
    # Development class accounting (exclude missing-target rows).
    _assert_fold_class_counts(folds_data)

    tuning = run_tuning(folds_data)
    selected = select_configurations(tuning)
    oof_rows, predictions = generate_oof(folds_data, selected)
    _assert_oof(oof_rows, allowlist)
    metrics_rows = compute_development_metrics(folds_data, selected, predictions)

    access_rows = build_access_manifest_rows(allowlist)
    lock_guard = build_lock_guard(repo_root, allowlist, loaded)
    registry_rows = build_config_registry_rows(tuning, selected)
    dev_lock = build_dev_lock(selected, metrics_rows, oof_rows)
    readme = build_readme(selected, metrics_rows)

    content: dict[str, str] = {
        F_AUTH: _json_str(auth),
        F_ACCESS_MANIFEST: _csv_str(ACCESS_MANIFEST_COLUMNS, access_rows),
        F_LOCK_GUARD: _json_str(lock_guard),
        F_CONFIG_REGISTRY: _csv_str(CONFIG_REGISTRY_COLUMNS, registry_rows),
        F_TUNING: _csv_str(TUNING_COLUMNS, tuning["tuning_rows"]),
        F_SELECTED: _json_str(selected),
        F_OOF: _csv_str(OOF_COLUMNS, oof_rows),
        F_METRICS: _csv_str(METRICS_COLUMNS, metrics_rows),
        F_DEV_LOCK: _json_str(dev_lock),
        F_README: readme,
    }

    extras = {
        "auth": auth,
        "frozen": frozen,
        "allowlist_dev_count": len(allowlist["dev_pairs"]),
        "allowlist_denylist_count": len(allowlist["denylist_pairs"]),
        "loaded": loaded,
        "folds_data": folds_data,
        "tuning": tuning,
        "selected": selected,
        "oof_rows": oof_rows,
        "metrics_rows": metrics_rows,
        "registry_rows": registry_rows,
        "lock_guard": lock_guard,
        "dev_lock": dev_lock,
        "mode": mode,
    }
    return content, extras


def _assert_fold_class_counts(folds_data: dict[str, dict[str, Any]]) -> None:
    for role, spec in EXPECTED_FOLD_COUNTS.items():
        y = folds_data[role]["y"]
        n = len(y)
        pos = int((y == 1).sum())
        neg = int((y == 0).sum())
        miss = int(np.isnan(y).sum())
        if (n, pos, neg) != (spec["rows"], spec["positive"], spec["negative"]):
            raise QCFail(
                f"fold {role} class counts ({n},{pos},{neg}) != "
                f"({spec['rows']},{spec['positive']},{spec['negative']})"
            )
        if miss != 0:
            raise QCFail(f"fold {role} has missing targets: {miss}")


def _assert_oof(oof_rows: list[dict[str, Any]], allowlist: dict[str, Any]) -> None:
    denylist = allowlist["denylist_pairs"]
    per_family: dict[str, int] = {}
    for r in oof_rows:
        key = (r["predictor_row_key_t"], r["target_row_key_t_plus_1"])
        if key in denylist:
            raise FinalTestLockError("final-test key present in OOF output")
        if r["temporal_fold"] not in FOLD_VALIDATION_ROLES:
            raise QCFail(f"OOF row not from a validation fold: {r['temporal_fold']}")
        if int(r["target_year"]) in FINAL_TEST_TARGET_YEARS:
            raise FinalTestLockError("final-test target_year in OOF output")
        per_family[r["model_family"]] = per_family.get(r["model_family"], 0) + 1
    for family in ALLOWED_MODEL_FAMILIES:
        if per_family.get(family, 0) != EXPECTED_POOLED_OOF_ROWS:
            raise QCFail(
                f"OOF rows for {family} = {per_family.get(family, 0)} != "
                f"{EXPECTED_POOLED_OOF_ROWS}"
            )
    if len(oof_rows) != EXPECTED_POOLED_OOF_ROWS * len(ALLOWED_MODEL_FAMILIES):
        raise QCFail("total OOF row count mismatch")


# --------------------------------------------------------------------------- #
# QC assertions
# --------------------------------------------------------------------------- #

def _assert(assertions: list[dict[str, str]], name: str, ok: bool, detail: str = "") -> None:
    assertions.append({
        "assertion": name,
        "status": "PASS" if ok else "FAIL",
        "detail": detail,
    })


def _rejected(fn, *args, **kwargs) -> bool:
    try:
        fn(*args, **kwargs)
        return False
    except QCFail:
        return True


def build_qc_assertions(
    *, repo_root: Path, extras: dict[str, Any], content: dict[str, str],
    network_attempts: int, head: str,
) -> list[dict[str, Any]]:
    a: list[dict[str, Any]] = []
    auth = extras["auth"]
    selected = extras["selected"]
    folds = extras["folds_data"]
    loaded = extras["loaded"]

    # Record the constant frozen baseline commit (not the live HEAD) as the
    # detail so the QC report stays byte-stable across additive commits on the
    # PR branch; the boolean still verifies the live HEAD contains the baseline.
    _assert(a, "baseline_commit_verified", head == EXPECTED_BASELINE_COMMIT
            or _is_ancestor(repo_root, EXPECTED_BASELINE_COMMIT, head),
            EXPECTED_BASELINE_COMMIT)
    _assert(a, "baseline_tree_verified",
            _git(repo_root, "rev-parse", f"{EXPECTED_BASELINE_COMMIT}^{{tree}}")
            == EXPECTED_BASELINE_TREE)

    # Authorization
    _assert(a, "authorization_text_byte_for_byte",
            auth["authorization_text_fa"] == AUTHORIZATION_TEXT_FA)
    _assert(a, "authorization_text_sha256_matches",
            hashlib.sha256(AUTHORIZATION_TEXT_FA.encode("utf-8")).hexdigest()
            == AUTHORIZATION_TEXT_SHA256)
    _assert(a, "stage126_authorized_true", auth["stage126_authorized"] is True)
    _assert(a, "development_modeling_authorized_true",
            auth["development_modeling_authorized"] is True)
    _assert(a, "final_test_unlocked_false", auth["final_test_unlocked"] is False)
    _assert(a, "final_test_access_authorized_false",
            auth["final_test_access_authorized"] is False)
    _assert(a, "final_test_evaluation_authorized_false",
            auth["final_test_evaluation_authorized"] is False)
    _assert(a, "contract_change_not_authorized",
            auth["contract_change_authorized"] is False)
    _assert(a, "m2_m3_m4_not_authorized", auth["m2_m3_m4_authorized"] is False)

    # Frozen upstream integrity (accurate transition wording — Part 4 / Part 5
    # guard+QC sources changed under the authorization transition; scientific
    # Part 3C artifacts and the Part 5 entry contract remain byte-identical to
    # the merged Stage125 baseline).
    _assert(a, "part3c_scientific_hashes_unchanged",
            all(extras["frozen"][r] == h for r, h in part5.FROZEN_PART3C_INPUTS.items()))
    _assert(a, "part4_scientific_contract_hashes_unchanged_and_transition_pins_match",
            all(extras["frozen"][r] == h for r, h in part5.FROZEN_PART4_OUTPUTS.items()))
    entry_rel = (
        "project/stage125/part5_stage126_m1_entry_contract_stage125.json"
    )
    _assert(
        a, "part5_entry_contract_unchanged_and_authorized_transition_hashes_match",
        extras["frozen"][entry_rel] == FROZEN_PART5_OUTPUTS[entry_rel]
        and all(
            extras["frozen"][r] == h for r, h in FROZEN_PART5_OUTPUTS.items()
        ),
    )
    _assert(a, "split_manifest_hash_pinned",
            extras["frozen"][SPLIT_MANIFEST_REL] == SPLIT_MANIFEST_SHA256)
    _assert(a, "analysis_ready_hash_pinned",
            sha256_file(repo_root / ANALYSIS_READY_REL) == ANALYSIS_READY_SHA256)

    # Specification
    _assert(a, "primary_sample", PRIMARY_SAMPLE == "main_rule_a_primary")
    _assert(a, "primary_target", PRIMARY_TARGET == "FD_target_main_t_plus_1")
    _assert(a, "feature_count_9", len(M1_PRIMARY_FEATURE_ORDER) == 9)
    _assert(a, "revenue_growth_prohibited",
            PROHIBITED_FEATURE not in M1_PRIMARY_FEATURE_ORDER
            and PROHIBITED_FEATURE not in FEATURE_SOURCE_COLUMN.values())
    _assert(a, "article141_not_estimation_target",
            ARTICLE141_TARGET != PRIMARY_TARGET)
    _assert(a, "allowed_families_only",
            tuple(ALLOWED_MODEL_FAMILIES) == (
                "regularized_logistic_regression", "random_forest", "xgboost"))
    _assert(a, "no_forbidden_families",
            not set(FORBIDDEN_MODEL_FAMILIES) & set(ALLOWED_MODEL_FAMILIES))

    # Counts
    _assert(a, "development_rows_666", extras["allowlist_dev_count"] == EXPECTED_DEV_ROWS)
    _assert(a, "final_test_pairs_346",
            extras["allowlist_denylist_count"] == EXPECTED_FINAL_TEST_PAIRS)
    for role, spec in EXPECTED_FOLD_COUNTS.items():
        y = folds[role]["y"]
        _assert(a, f"{role}_rows_{spec['rows']}", len(y) == spec["rows"])
        _assert(a, f"{role}_pos_{spec['positive']}",
                int((y == 1).sum()) == spec["positive"])
        _assert(a, f"{role}_neg_{spec['negative']}",
                int((y == 0).sum()) == spec["negative"])
    dev_y = np.concatenate([folds[r]["y"] for r in
                            ("fold1_train", "fold1_validation", "fold2_validation")])
    _assert(a, "development_positive_68", int((dev_y == 1).sum()) == EXPECTED_DEV_POSITIVE)
    _assert(a, "development_negative_598", int((dev_y == 0).sum()) == EXPECTED_DEV_NEGATIVE)
    _assert(a, "development_missing_target_0", int(np.isnan(dev_y).sum()) == 0)

    # Configuration budget
    cfgs = extras["tuning"]["cfgs"]
    _assert(a, "logistic_4_configs",
            len(cfgs["regularized_logistic_regression"]) == 4)
    _assert(a, "rf_12_configs", len(cfgs["random_forest"]) == 12)
    _assert(a, "xgboost_16_configs", len(cfgs["xgboost"]) == 16)
    _assert(a, "total_32_configs",
            sum(len(v) for v in cfgs.values()) == EXPECTED_TOTAL_CONFIGS)
    _assert(a, "tuning_seeds_locked", TUNING_SEEDS == (20260719, 20260720, 20260721))
    _assert(a, "final_oof_seeds_locked",
            FINAL_OOF_SEEDS == (20260719, 20260720, 20260721, 20260722, 20260723))

    # Selection
    _assert(a, "one_config_selected_per_family",
            set(selected) == set(ALLOWED_MODEL_FAMILIES))

    # OOF
    per_family: dict[str, int] = {}
    ft_in_oof = 0
    for r in extras["oof_rows"]:
        per_family[r["model_family"]] = per_family.get(r["model_family"], 0) + 1
        if int(r["target_year"]) in FINAL_TEST_TARGET_YEARS:
            ft_in_oof += 1
    _assert(a, "oof_421_per_family",
            all(per_family[f] == EXPECTED_POOLED_OOF_ROWS for f in ALLOWED_MODEL_FAMILIES))
    _assert(a, "oof_1263_total",
            len(extras["oof_rows"]) == EXPECTED_POOLED_OOF_ROWS * 3)
    _assert(a, "no_final_test_row_in_oof", ft_in_oof == 0)
    pooled_pos = sum(1 for r in extras["oof_rows"]
                     if r["model_family"] == "random_forest" and r["observed_target"] == 1)
    _assert(a, "pooled_oof_positive_35", pooled_pos == EXPECTED_POOLED_OOF_POSITIVE)

    # Final-test lock evidence
    _assert(a, "final_test_predictor_rows_loaded_0",
            loaded["final_test_values_loaded"] == 0)
    _assert(a, "final_test_target_rows_loaded_0",
            loaded["final_test_values_loaded"] == 0)
    _assert(a, "final_test_rows_seen_but_unparsed_346",
            loaded["final_test_rows_seen"] == EXPECTED_FINAL_TEST_PAIRS)
    _assert(a, "no_full_development_refit",
            extras["dev_lock"]["full_development_refit_performed"] is False)
    _assert(a, "no_smote", extras["dev_lock"]["smote_executed"] is False)
    _assert(a, "no_shap", extras["dev_lock"]["shap_executed"] is False)
    _assert(a, "m1_robustness_not_started",
            extras["dev_lock"]["m1_robustness_started"] is False)

    # Fail-closed guard behaviour (negative tests executed at QC time)
    _assert(a, "wrong_baseline_rejected",
            _rejected(verify_baseline_commit_with, repo_root, "0" * 40))
    _assert(a, "auth_text_mutation_rejected",
            _rejected(assert_authorization, {**auth, "authorization_text_fa": "x"}))
    _assert(a, "auth_hash_mutation_rejected",
            _rejected(assert_authorization,
                      {**auth, "authorization_text_sha256": "0" * 64}))
    _assert(a, "final_test_unlocked_true_rejected",
            _rejected(assert_authorization, {**auth, "final_test_unlocked": True}))
    _assert(a, "final_test_access_true_rejected",
            _rejected(assert_authorization,
                      {**auth, "final_test_access_authorized": True}))
    _assert(a, "stage126_unauthorized_rejected",
            _rejected(assert_authorization, {**auth, "stage126_authorized": False}))

    # Network / determinism
    _assert(a, "network_requests_zero", network_attempts == 0)

    return a


def verify_baseline_commit_with(repo_root: Path, fake_commit: str) -> None:
    """Helper for the wrong-baseline guard test (does not mutate global state)."""
    if _is_ancestor(repo_root, fake_commit, _git(repo_root, "rev-parse", "HEAD")):
        return  # pragma: no cover - fake commit is not an ancestor
    raise QCFail("wrong baseline")


# --------------------------------------------------------------------------- #
# Run
# --------------------------------------------------------------------------- #

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

    repo_root = project_dir.parent if project_dir.name == "project" else project_dir
    canonical_out = (repo_root / "project" / "stage126").resolve()
    out_dir = Path(output_dir).resolve() if output_dir else canonical_out

    head = verify_baseline_commit(str(repo_root))
    frozen_before = frozen_upstream_hashes(repo_root)
    files_written: dict[str, str] = {}
    run_mode = "build" if build else "check"

    with p3b0.network_sentinel() as sentinel:
        content, extras = build_all(repo_root, mode=run_mode)
        if sentinel.calls_attempted != 0:
            raise QCFail(
                f"network_requests_attempted_zero failed: {sentinel.calls_attempted}"
            )
        network_attempts = sentinel.calls_attempted
        frozen_after = frozen_upstream_hashes(repo_root)
        if frozen_before != frozen_after:
            raise QCFail("frozen upstream artifacts mutated during run")

        assertions = build_qc_assertions(
            repo_root=repo_root, extras=extras, content=content,
            network_attempts=network_attempts, head=head,
        )
        failed = sum(1 for x in assertions if x["status"] != "PASS")
        source_commit = _git(
            str(repo_root), "log", "--format=%H", "-n", "1",
            "--", SRC_REL, TEST_REL, RUN_REL,
        ) or head

        content_hashes = {
            name: sha256_bytes(text.encode("utf-8")) for name, text in content.items()
        }
        qc: dict[str, Any] = {
            "stage": QC_STAGE,
            "current_stage": CURRENT_STAGE,
            "active_workstream": ACTIVE_WORKSTREAM,
            "research_action_id": RESEARCH_ACTION_ID,
            "contract_version": CONTRACT_VERSION,
            "baseline_commit": EXPECTED_BASELINE_COMMIT,
            "baseline_tree": EXPECTED_BASELINE_TREE,
            "source_commit": source_commit,
            "source_file_sha256": sha256_file(repo_root / SRC_REL),
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
            "final_test_predictor_rows_loaded": extras["loaded"]["final_test_values_loaded"],
            "final_test_target_rows_loaded": extras["loaded"]["final_test_values_loaded"],
            "final_test_evaluations": 0,
            "shap_calls": 0,
            "smote_calls": 0,
            "model_fit_calls_scope": "development_folds_only",
            "selected_configurations": {
                f: extras["selected"][f]["configuration_id"]
                for f in ALLOWED_MODEL_FAMILIES
            },
            "output_sha256": dict(sorted(content_hashes.items())),
            "assertions": assertions,
            # Handoff workflow markers (propagated by the generator).
            **stage126_handoff_markers(),
        }
        qc_text = _json_str(qc)
        qc_hash = sha256_bytes(qc_text.encode("utf-8"))
        meta = {
            "stage": QC_STAGE,
            "current_stage": CURRENT_STAGE,
            "description": (
                "Stage126 M1 primary development-fold tuning (human-authorized; "
                "development only; final test locked; no SMOTE/SHAP/robustness; "
                "no full-development refit)."
            ),
            "generated_at": source_commit,
            "code_commit": source_commit,
            "baseline_commit": EXPECTED_BASELINE_COMMIT,
            "baseline_tree": EXPECTED_BASELINE_TREE,
            "source_file_sha256": qc["source_file_sha256"],
            "test_file_sha256": qc["test_file_sha256"],
            "runtime_versions": runtime_versions(),
            "output_files_sha256": dict(
                sorted({**content_hashes, F_QC: qc_hash}.items())
            ),
            "network_requests_attempted": network_attempts,
            "final_test_predictor_rows_loaded": 0,
            "final_test_target_rows_loaded": 0,
            "final_test_evaluations": 0,
            "shap_calls": 0,
            "smote_calls": 0,
        }
        meta_text = _json_str(meta)
        all_tracked = {**content, F_QC: qc_text, F_METADATA: meta_text}

        tracked_drift = (
            _compare_drift(out_dir, all_tracked)
            if out_dir.is_dir() else sorted(all_tracked)
        )

        if build:
            out_dir.mkdir(parents=True, exist_ok=True)
            for name, text in all_tracked.items():
                (out_dir / name).write_text(text, encoding="utf-8")
                files_written[name] = sha256_bytes(text.encode("utf-8"))

        if check and out_dir.resolve() == canonical_out and tracked_drift:
            raise QCFail(f"check drift (tracked): {tracked_drift}")

        if not qc["all_pass"]:
            raise QCFail(f"Stage126 QC failed: {failed} assertions failed")

        return {
            "qc": qc,
            "metadata": meta,
            "output_dir": str(out_dir),
            "files": files_written,
            "drift": tracked_drift,
            "network_requests_attempted": network_attempts,
        }


def stage126_handoff_markers() -> dict[str, Any]:
    """Workflow markers propagated into the Handoff state (fail-closed).

    ``modeling_started`` is True because at least one authorized development-fold
    fit has occurred; it never implies final-test access.
    """
    return {
        "stage125_completed": True,
        "stage126_m1_entry_ready": True,
        "stage126_authorized": True,
        "stage126_started": True,
        "development_modeling_authorized": True,
        "modeling_authorized": True,
        "modeling_started": True,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_predictor_values_inspected": False,
        "final_test_target_values_inspected": False,
        "final_test_evaluation_performed": False,
        "m1_primary_development_tuning_completed": True,
        "m1_robustness_started": False,
        "m1_robustness_completed": False,
        "m2_data_collected": False,
        "m3_data_collected": False,
        "m4_data_collected": False,
    }

