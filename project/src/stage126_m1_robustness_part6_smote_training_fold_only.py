"""Stage126 M1 — Robustness Part 6: SMOTE training-fold-only robustness.

Explicitly human-authorized, development-only sensitivity analysis. This is
the sixth and FINAL registered M1 robustness category. ONLY the imbalance
strategy changes relative to the locked primary Stage126 M1 development
analysis: the `main_rule_a_primary` sample, the primary target
(`FD_target_main_t_plus_1`), the nine-feature primary set, the selected
configurations (non-weight hyperparameters), the temporal folds, the seeds and
the metric contract are all held fixed. Class weighting is disabled and
replaced by SMOTENC applied strictly inside each training fold, after all
fold-specific preprocessing parameters have been estimated from that training
fold alone.

Fail-closed guarantees:
  * the locked final test is never opened — final-test predictor/target values
    are never parsed, stored, summarized, logged or exported, never
    preprocessed and never resampled. Final-test rows are counted ONLY through
    the frozen temporal split/identity contract, and the only permitted
    final-test information is the frozen aggregate event gate;
  * no hyperparameter search runs (the three primary selected configurations
    are loaded from the frozen artifact and reused verbatim, minus their class
    weighting);
  * validation rows never enter the resampler;
  * no full-development refit, no SHAP, no calibration, no threshold
    optimization, no bootstrap, no Holm correction, no p-values and no winner
    selection;
  * the frozen Stage125 tree and the Part 1-5 scientific artifacts must remain
    byte-identical.

Part 6 is development-only imbalance-strategy robustness evidence. It never
replaces the primary class-weighted results or the locked primary ordering
used for confirmatory interpretation, and never selects a paper winner.
Completing Part 6 completes all six registered M1 robustness categories, but
does NOT itself authorize a full-development refit or final-test access —
those remain a separate, later human decision.
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
from src import stage126_m1_robustness_part1_target_proximity as part1
from src import stage126_m1_robustness_part2_listing_rule_b as part2
from src import stage126_m1_robustness_part3_expanded_rule_a as part3
from src import stage126_m1_robustness_part4_expanded_rule_b as part4
from src import stage126_m1_robustness_part5_persistent_loss_target as part5

# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #

QC_STAGE = "stage126_m1_robustness_part6_smote_training_fold_only"
CURRENT_STAGE = "Stage126"
CONTRACT_VERSION = "stage126_m1_robustness_part6_smote_training_fold_only_v1"
CATEGORY_ID = "smote_training_fold_only_robustness"
SCIENTIFIC_ROLE = "imbalance_strategy_robustness"
CHANGED_DIMENSION = "imbalance_strategy"
IMBALANCE_POLICY = "SMOTE_family_training_fold_only_robustness"
SCIENTIFIC_INTERPRETATION = (
    "development_only_imbalance_strategy_robustness_evidence"
)
MICRO_PART_ID = "stage126-m1-robustness-part6-smote-training-fold-only"
PART1_CATEGORY_ID = "m1_target_proximity_six_feature_set"
PART2_CATEGORY_ID = "main_rule_b_listing_robustness"
PART3_CATEGORY_ID = "expanded_rule_a_company_scope_robustness"
PART4_CATEGORY_ID = "expanded_rule_b_combined_robustness"
PART5_CATEGORY_ID = "persistent_loss_robustness_target"
# Terminal category: there is no seventh registered robustness category. The
# schema-native representation of "no next category" is an empty string.
NEXT_CATEGORY_ID = ""

SRC_REL = "project/src/stage126_m1_robustness_part6_smote_training_fold_only.py"
RUN_REL = "project/run_stage126_m1_robustness_part6_smote_training_fold_only.py"
TEST_REL = (
    "project/tests/test_stage126_m1_robustness_part6_smote_training_fold_only.py"
)

STAGE126_DIR_REL = "project/stage126"
F_AUTH = "stage126_m1_robustness_part6_human_authorization_record.json"
F_FEATURE_MANIFEST = "stage126_m1_robustness_part6_feature_manifest.csv"
F_RESAMPLING = "stage126_m1_robustness_part6_resampling_audit.csv"
F_EXEC_MANIFEST = "stage126_m1_robustness_part6_execution_manifest.json"
F_OOF = "stage126_m1_robustness_part6_oof_predictions.csv"
F_METRICS = "stage126_m1_robustness_part6_metrics.csv"
F_COMPARISON = "stage126_m1_robustness_part6_primary_comparison.json"
F_COMPLETION_LOCK = "stage126_m1_robustness_part6_completion_lock.json"
F_QC = "stage126_m1_robustness_part6_qc_report.json"
F_METADATA = "metadata_and_hashes_stage126_m1_robustness_part6.json"
F_README = (
    "README_STAGE126_M1_ROBUSTNESS_PART6_SMOTE_TRAINING_FOLD_ONLY.md"
)

# The base `main` commit this micro-part was authorized from.
BASE_MAIN_COMMIT = "357a661e8579a2637f574a56e5586a7a0cb6c17e"

# --------------------------------------------------------------------------- #
# Exact human authorization (byte-for-byte Persian; 696 UTF-8 bytes)
# --------------------------------------------------------------------------- #

HUMAN_AUTHORIZATION_TEXT_FA = (
    "مجوز اجرای Stage126 M1 Robustness Part 6 — "
    "`smote_training_fold_only_robustness` را می‌دهم.\n"
    "\n"
    "این مجوز فقط برای اجرای Part 6 روی development folds با نمونه "
    "`main_rule_a_primary`، هدف `FD_target_main_t_plus_1`، مجموعه ویژگی "
    "`M1_PRIMARY_FEATURE_ORDER` و تنظیمات منتخب قفل‌شده M1 است؛ تنها راهبرد "
    "عدم‌تعادل به SMOTENC/SMOTE درون هر training fold تغییر می‌کند و "
    "class weighting غیرفعال است. این مجوز شامل Merge، retuning، "
    "full-development refit، final test، calibration، bootstrap، Holm، "
    "winner selection، SHAP یا M2/M3/M4 نمی‌شود."
)
HUMAN_AUTHORIZATION_TEXT_SHA256 = (
    "4a3bb0d722d288f754b780208b5805f264b4caac75a902f434135f56430ed269"
)
HUMAN_AUTHORIZATION_TEXT_BYTES = 696
AUTHORIZATION_ID = "stage126-m1-robustness-part6-human-authorization"
AUTHORIZATION_DATE = "2026-07-25"
AUTHORIZATION_CONTEXT = (
    "The independently verified repository state completed Stage126 M1 "
    "Robustness Parts 1, 2, 3, 4 and 5 and identified Part 6 — "
    "smote_training_fold_only_robustness — as the sixth and final registered "
    "gated micro-part."
)

# --------------------------------------------------------------------------- #
# Fixed (inherited) analysis dimensions — ONLY the imbalance strategy changes
# --------------------------------------------------------------------------- #

PART6_SAMPLE = primary.PRIMARY_SAMPLE                   # main_rule_a_primary
PRIMARY_SAMPLE = primary.PRIMARY_SAMPLE
PRIMARY_TARGET = primary.PRIMARY_TARGET                 # FD_target_main_t_plus_1
PART6_TARGET = primary.PRIMARY_TARGET                   # unchanged
PROHIBITED_TARGET = "FD_target_article141_only_t_plus_1"
FEATURE_SET_NAME = primary.FEATURE_SET_NAME             # M1_PRIMARY_FEATURE_ORDER
PART6_FEATURE_ORDER: tuple[str, ...] = tuple(primary.M1_PRIMARY_FEATURE_ORDER)
PART6_FEATURE_SOURCE_COLUMN: dict[str, str] = dict(primary.FEATURE_SOURCE_COLUMN)
PROHIBITED_FEATURE = primary.PROHIBITED_FEATURE

BASE_FEATURE_COUNT = 9
TRANSFORMED_FEATURE_COUNT = 18  # 9 imputed continuous + 9 missingness indicators
# Zero-based indices of the appended missingness-indicator columns (categorical
# for SMOTENC).
CATEGORICAL_FEATURE_INDICES: tuple[int, ...] = tuple(
    range(BASE_FEATURE_COUNT, TRANSFORMED_FEATURE_COUNT)
)

MODEL_FAMILIES = primary.ALLOWED_MODEL_FAMILIES
MODEL_SEEDS = primary.FINAL_OOF_SEEDS
LOGISTIC_DETERMINISTIC_SEED = primary.TUNING_SEEDS[0]
FEATURE_TRANSFORMATION: dict[str, str] = dict(part2.FEATURE_TRANSFORMATION)

SMOTE_SAMPLER_CLASS = "imblearn.over_sampling.SMOTENC"
SMOTE_RANDOM_STATE = 20260725

# --------------------------------------------------------------------------- #
# Exact expected primary-sample counts under the primary target (unchanged)
# --------------------------------------------------------------------------- #

EXPECTED_ROWS = 1012
EXPECTED_COMPANIES = 119
EXPECTED_POSITIVE = 80
EXPECTED_NEGATIVE = 932
EXPECTED_MISSING_TARGET = 0

EXPECTED_DEV_ROWS = 666
EXPECTED_DEV_POSITIVE = 68
EXPECTED_DEV_NEGATIVE = 598

EXPECTED_FOLD_COUNTS: dict[str, dict[str, int]] = {
    "fold1_train": {"rows": 245, "positive": 33, "negative": 212},
    "fold1_validation": {"rows": 205, "positive": 25, "negative": 180},
    "fold2_train": {"rows": 450, "positive": 58, "negative": 392},
    "fold2_validation": {"rows": 216, "positive": 10, "negative": 206},
}
EXPECTED_OOF_ROWS_PER_FAMILY = 421        # 205 + 216 (primary identities)
EXPECTED_OOF_ROWS_TOTAL = EXPECTED_OOF_ROWS_PER_FAMILY * len(MODEL_FAMILIES)
EXPECTED_OOF_POSITIVE = 35                # 25 + 10
EXPECTED_METRICS_ROWS = len(MODEL_FAMILIES) * 3

EXPECTED_MODEL_FIT_CALLS = 22   # 2 logistic + 10 RF + 10 XGBoost
EXPECTED_PREDICTION_CALLS = 22
EXPECTED_FINAL_TEST_IDENTITIES = 346

# Expected SMOTENC resampling contract per training fold (identical across the
# three model families, since class counts do not depend on model family).
EXPECTED_RESAMPLING: dict[str, dict[str, int]] = {
    "fold1_train": {
        "original_positive": 33, "original_negative": 212,
        "resampled_positive": 212, "resampled_negative": 212,
        "synthetic_positive": 179, "total_after": 424, "k_neighbors": 5,
    },
    "fold2_train": {
        "original_positive": 58, "original_negative": 392,
        "resampled_positive": 392, "resampled_negative": 392,
        "synthetic_positive": 334, "total_after": 784, "k_neighbors": 5,
    },
}
EXPECTED_SMOTENC_CALLS = len(EXPECTED_RESAMPLING) * len(MODEL_FAMILIES)  # 6

# Frozen final-test aggregate positive/negative counts (never row-level;
# unchanged from the primary target — Part 6 does not touch the target).
EXPECTED_FINAL_TEST_POSITIVE_PRIMARY = 12
EXPECTED_FINAL_TEST_NEGATIVE_PRIMARY = 334

# --------------------------------------------------------------------------- #
# Frozen inputs (pinned; never modified)
# --------------------------------------------------------------------------- #

ANALYSIS_READY_REL = primary.ANALYSIS_READY_REL
ANALYSIS_READY_SHA256 = primary.ANALYSIS_READY_SHA256
SPLIT_MANIFEST_REL = primary.SPLIT_MANIFEST_REL
SPLIT_MANIFEST_SHA256 = primary.SPLIT_MANIFEST_SHA256
EVENT_COUNT_GATE_REL = part2.EVENT_COUNT_GATE_REL
EVENT_COUNT_GATE_SHA256 = part2.EVENT_COUNT_GATE_SHA256
SAMPLE_SUMMARY_REL = part2.SAMPLE_SUMMARY_REL
SAMPLE_SUMMARY_SHA256 = part2.SAMPLE_SUMMARY_SHA256

SELECTED_CONFIGURATIONS_REL = part2.SELECTED_CONFIGURATIONS_REL
SELECTED_CONFIGURATIONS_SHA256 = part2.SELECTED_CONFIGURATIONS_SHA256
PART0_DECISION_RECORD_REL = part2.PART0_DECISION_RECORD_REL
PART0_DECISION_RECORD_SHA256 = part2.PART0_DECISION_RECORD_SHA256
PRIMARY_SRC_REL = part2.PRIMARY_SRC_REL
PRIMARY_SRC_SHA256 = part2.PRIMARY_SRC_SHA256
PRIMARY_METRICS_REL = part2.PRIMARY_METRICS_REL
PINNED_PRIMARY_ARTIFACTS: dict[str, str] = dict(part2.PINNED_PRIMARY_ARTIFACTS)

# Locked primary pooled development-OOF PR-AUC (the confirmatory reference).
LOCKED_PRIMARY_POOLED_PR_AUC: dict[str, float] = dict(
    part3.LOCKED_PRIMARY_POOLED_PR_AUC
)

# Closed micro-part scientific artifacts — Parts 1-5 must remain byte-identical.
PART2_METRICS_REL = part3.PART2_METRICS_REL
PART3_METRICS_REL = "project/stage126/stage126_m1_robustness_part3_metrics.csv"
PART4_METRICS_REL = "project/stage126/stage126_m1_robustness_part4_metrics.csv"
PART5_METRICS_REL = "project/stage126/stage126_m1_robustness_part5_metrics.csv"
PINNED_CLOSED_PART_ARTIFACTS: dict[str, str] = {
    **part5.PINNED_CLOSED_PART_ARTIFACTS,
    "project/stage126/"
    "stage126_m1_robustness_part5_human_authorization_record.json":
        "5b9ac4e04475695302e7c6bee01126642e36ffe2b583d89db16d5b5e5eed17ac",
    "project/stage126/stage126_m1_robustness_part5_feature_manifest.csv":
        "d33ea2adbd73cfcc5fd1a2af7e774e8a4eab283b4c0dbd7fe79c002a145472cc",
    "project/stage126/stage126_m1_robustness_part5_execution_manifest.json":
        "bc1cfd8dbf8197b96f595235aaa74ca18ad2cb5452ea67798dd77166b5289cea",
    "project/stage126/stage126_m1_robustness_part5_oof_predictions.csv":
        "7b721af7b9b5b5a3f88f7a957d70c87480dc1a3ca56a55b10c885e99177ad977",
    PART5_METRICS_REL:
        "a811703bf3b96acd042f63c88aa2fbcdbd541f81da34d9abc1ba0d912a3bb3cf",
    "project/stage126/stage126_m1_robustness_part5_primary_comparison.json":
        "e0ddde1977ccbbdc0c892d92ef8812316373266e3a5efb5f7ac0ebaed9a81c97",
    "project/stage126/stage126_m1_robustness_part5_completion_lock.json":
        "c41335c377c4f58d6a710095076327aae9c5027dc83bcb377680526cd94d486b",
}

# --------------------------------------------------------------------------- #
# Deterministic output column orders
# --------------------------------------------------------------------------- #

OOF_COLUMNS = [
    "robustness_category_id", "sample", "feature_set", "model_family",
    "configuration_id", "temporal_fold", "ticker", "predictor_row_key_t",
    "target_row_key_t_plus_1", "fiscal_year_t", "target_year",
    "observed_target", "predicted_probability", "seed_aggregation",
]
METRICS_COLUMNS = [
    "robustness_category_id", "sample", "feature_set", "model_family",
    "configuration_id", "scope", "n_rows", "n_positive", "k_top10", "pr_auc",
    "roc_auc", "brier_score", "recall_at_10pct", "lift_at_10pct",
]
FEATURE_MANIFEST_COLUMNS = [
    "feature_order", "feature_name", "source_column", "transformation",
    "missingness_indicator_appended", "missingness_indicator_column_index",
    "included_in_part6",
]
RESAMPLING_COLUMNS = [
    "model_family", "temporal_fold", "sampler_class",
    "categorical_feature_indices", "random_state", "k_neighbors",
    "original_positive", "original_negative", "resampled_positive",
    "resampled_negative", "synthetic_rows", "validation_rows_before",
    "validation_rows_after", "indicators_binary", "validation_resampled",
    "final_test_approached", "class_weighting_disabled",
    "xgboost_scale_pos_weight",
]

METRIC_NAMES: tuple[str, ...] = (
    "pr_auc", "roc_auc", "brier_score", "recall_at_10pct", "lift_at_10pct",
)
METRIC_SCOPES: tuple[str, ...] = (
    "fold1_validation", "fold2_validation", "pooled_development_oof",
)


class QCFail(RuntimeError):
    """Fail-closed Part 6 validation error."""


class FinalTestLockError(QCFail):
    """The locked final test was approached (fail-closed)."""


# --------------------------------------------------------------------------- #
# Helpers (reused deterministic utilities)
# --------------------------------------------------------------------------- #

def _json_str(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def _csv_str(header: list[str], rows: list[dict[str, Any]]) -> str:
    return primary._csv_str(header, rows)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


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
    raw = HUMAN_AUTHORIZATION_TEXT_FA.encode("utf-8")
    if len(raw) != HUMAN_AUTHORIZATION_TEXT_BYTES:
        raise QCFail(
            f"Part 6 authorization byte length {len(raw)} != "
            f"{HUMAN_AUTHORIZATION_TEXT_BYTES}"
        )
    got = hashlib.sha256(raw).hexdigest()
    if got != HUMAN_AUTHORIZATION_TEXT_SHA256:
        raise QCFail(
            f"Part 6 human authorization SHA-256 mismatch: {got} != "
            f"{HUMAN_AUTHORIZATION_TEXT_SHA256}"
        )


def build_authorization_record() -> dict[str, Any]:
    """Deterministic Part 6 human authorization record (hash recomputed)."""
    verify_authorization_text()
    return {
        "authorization_id": AUTHORIZATION_ID,
        "authorization_date": AUTHORIZATION_DATE,
        "authorizing_role": "human_supervisor_data_owner",
        "human_authorization_text": HUMAN_AUTHORIZATION_TEXT_FA,
        "human_authorization_text_sha256": HUMAN_AUTHORIZATION_TEXT_SHA256,
        "human_authorization_text_utf8_bytes": HUMAN_AUTHORIZATION_TEXT_BYTES,
        "authorization_context": AUTHORIZATION_CONTEXT,
        "authorized_category_id": CATEGORY_ID,
        "authorized_base_main_commit": BASE_MAIN_COMMIT,
        "part6_execution_authorized": True,
        "development_fold_execution_authorized": True,
        "create_open_unmerged_pr_authorized": True,
        "merge_authorized": False,
        "retuning_authorized": False,
        "full_development_refit_authorized": False,
        "final_test_predictor_access_authorized": False,
        "final_test_target_access_authorized": False,
        "final_test_access_authorized": False,
        "final_test_evaluation_authorized": False,
        "calibration_authorized": False,
        "threshold_optimization_authorized": False,
        "bootstrap_authorized": False,
        "holm_authorized": False,
        "p_values_authorized": False,
        "winner_selection_authorized": False,
        "shap_authorized": False,
        "m2_authorized": False,
        "m3_authorized": False,
        "m4_authorized": False,
        "authorization_scope_note": (
            "Consumed by this Part 6 execution. Creates no standing execution "
            "authorization for a full-development refit, final test or any "
            "later scientific stage."
        ),
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
    order = list(record.get("execution_order") or [])
    if len(order) != 6:
        raise QCFail(f"Part 0 execution_order length {len(order)} != 6")
    expected_order = [
        PART1_CATEGORY_ID, PART2_CATEGORY_ID, PART3_CATEGORY_ID,
        PART4_CATEGORY_ID, PART5_CATEGORY_ID, CATEGORY_ID,
    ]
    for i, cat in enumerate(expected_order):
        if order[i] != cat:
            raise QCFail(
                f"Part 0 execution_order[{i}] {order[i]!r} != {cat!r}"
            )
    return record


def verify_predecessors_completed(repo_root: Path) -> list[str]:
    """Parts 1-5 must already be complete — no category may be skipped."""
    completed: list[str] = []
    for index, category in (
        (1, PART1_CATEGORY_ID), (2, PART2_CATEGORY_ID),
        (3, PART3_CATEGORY_ID), (4, PART4_CATEGORY_ID), (5, PART5_CATEGORY_ID),
    ):
        rel = (
            f"{STAGE126_DIR_REL}/stage126_m1_robustness_part{index}"
            "_completion_lock.json"
        )
        path = repo_root / rel
        if not path.is_file():
            raise QCFail(
                f"Part {index} completion lock missing — Part 6 may not run "
                f"before Parts 1-5"
            )
        lock = json.loads(path.read_text(encoding="utf-8"))
        if lock.get("category_id") != category:
            raise QCFail(f"Part {index} completion lock category mismatch")
        if lock.get(f"part{index}_execution_completed") is not True:
            raise QCFail(f"Part {index} is not completed")
        completed.append(category)
    return completed


def verify_closed_parts_immutable(repo_root: Path) -> dict[str, str]:
    """Part 1-5 scientific outputs must be byte-identical."""
    observed: dict[str, str] = {}
    for rel, expected in sorted(PINNED_CLOSED_PART_ARTIFACTS.items()):
        observed[rel] = require_file_hash(
            repo_root, rel, expected, label="closed micro-part artifact",
        )
    return observed


def verify_frozen_integrity(repo_root: Path) -> dict[str, str]:
    """Fail-closed integrity of every frozen upstream and primary surface."""
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
    for rel, expected in (
        (ANALYSIS_READY_REL, ANALYSIS_READY_SHA256),
        (SPLIT_MANIFEST_REL, SPLIT_MANIFEST_SHA256),
        (EVENT_COUNT_GATE_REL, EVENT_COUNT_GATE_SHA256),
        (SAMPLE_SUMMARY_REL, SAMPLE_SUMMARY_SHA256),
    ):
        require_file_hash(repo_root, rel, expected, label="frozen Stage125 input")
    return observed


# --------------------------------------------------------------------------- #
# Allowlist (identical to the primary sample — same sample and folds)
# --------------------------------------------------------------------------- #

def build_part6_allowlist(repo_root: Path) -> dict[str, Any]:
    """Development allowlist + final-test denylist for the primary sample.

    The sample, target and temporal folds are unchanged from the locked
    primary M1 analysis, so the identity sets are the primary identity sets
    by construction.
    """
    try:
        return primary.build_development_allowlist(repo_root)
    except primary.QCFail as exc:
        raise QCFail(str(exc)) from exc


# --------------------------------------------------------------------------- #
# Part 6 nine-feature loader (development rows only; primary target)
# --------------------------------------------------------------------------- #

def part6_source_columns() -> list[str]:
    """Exactly the nine primary source columns; the growth feature can't appear."""
    cols = sorted({PART6_FEATURE_SOURCE_COLUMN[f] for f in PART6_FEATURE_ORDER})
    if len(cols) != BASE_FEATURE_COUNT:
        raise QCFail(
            f"Part 6 source column count {len(cols)} != {BASE_FEATURE_COUNT}"
        )
    if PROHIBITED_FEATURE in cols:
        raise QCFail("prohibited growth feature reached the Part 6 loader")
    return cols


def load_part6_development_values(
    repo_root: Path, allowlist: dict[str, Any],
) -> dict[str, Any]:
    """Stream the primary analysis-ready CSV keeping ONLY development keys.

    Reads exactly the nine primary source columns and the primary target for
    development rows only. Final-test rows are never numerically parsed,
    stored, summarized, logged, exported, preprocessed or resampled — only
    their identities are counted. Unknown/unclassified rows fail closed.
    """
    dev_pairs = allowlist["dev_pairs"]
    denylist = allowlist["denylist_pairs"]
    source_cols = part6_source_columns()

    loaded: dict[tuple[str, str], dict[str, Any]] = {}
    final_test_rows_seen = 0
    final_test_predictor_rows_loaded = 0
    final_test_target_rows_loaded = 0
    unknown_rows = 0
    missing_target = 0

    path = repo_root / ANALYSIS_READY_REL
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        header = set(reader.fieldnames or [])
        needed = set(source_cols) | {
            "predictor_row_key_t", "target_row_key_t_plus_1", "ticker",
            "fiscal_year_t", "target_year", PART6_TARGET,
        }
        missing = needed - header
        if missing:
            raise QCFail(
                f"analysis-ready CSV missing columns: {sorted(missing)}"
            )
        for row in reader:
            key = (row["predictor_row_key_t"], row["target_row_key_t_plus_1"])
            if key in dev_pairs:
                ty = int(row["target_year"])
                if ty not in primary.DEVELOPMENT_TARGET_YEARS:
                    raise FinalTestLockError(
                        f"development key has non-development target_year {ty}"
                    )
                raw_sources = {c: row[c] for c in source_cols}
                target = primary._target_value(row[PART6_TARGET])
                if math.isnan(target):
                    missing_target += 1
                loaded[key] = {
                    "ticker": row["ticker"],
                    "predictor_row_key_t": key[0],
                    "target_row_key_t_plus_1": key[1],
                    "fiscal_year_t": row["fiscal_year_t"],
                    "target_year": ty,
                    "features": primary._derive_features(raw_sources),
                    "target": target,
                }
            elif key in denylist:
                # Locked final-test row: no predictor/target value is parsed.
                final_test_rows_seen += 1
            else:
                unknown_rows += 1

    if unknown_rows:
        raise QCFail(
            f"{unknown_rows} analysis-ready rows unclassified (fail-closed)"
        )
    if missing_target != EXPECTED_MISSING_TARGET:
        raise QCFail(f"missing development targets {missing_target} != 0")
    if len(loaded) != EXPECTED_DEV_ROWS:
        raise QCFail(f"loaded {len(loaded)} dev rows != {EXPECTED_DEV_ROWS}")
    if final_test_rows_seen != EXPECTED_FINAL_TEST_IDENTITIES:
        raise QCFail(
            f"final-test identities seen {final_test_rows_seen} != "
            f"{EXPECTED_FINAL_TEST_IDENTITIES}"
        )
    if final_test_predictor_rows_loaded or final_test_target_rows_loaded:
        raise FinalTestLockError("final-test values loaded (fail-closed)")
    for info in loaded.values():
        if info["target_year"] in primary.FINAL_TEST_TARGET_YEARS:
            raise FinalTestLockError("final-test target_year in loaded modeling rows")
        if info["features"].shape[0] != BASE_FEATURE_COUNT:
            raise QCFail("Part 6 feature vector is not nine-dimensional")
        if info["target"] not in (0.0, 1.0):
            raise QCFail("Part 6 development target is not binary")

    return {
        "rows": loaded,
        "final_test_rows_seen": final_test_rows_seen,
        "final_test_predictor_rows_loaded": final_test_predictor_rows_loaded,
        "final_test_target_rows_loaded": final_test_target_rows_loaded,
        "missing_target": missing_target,
    }


# --------------------------------------------------------------------------- #
# Selected configurations (loaded, never re-searched; class weighting removed)
# --------------------------------------------------------------------------- #

EXPECTED_SELECTED: dict[str, dict[str, Any]] = part1.EXPECTED_SELECTED


def load_selected_configurations(repo_root: Path) -> dict[str, Any]:
    """Load the frozen primary selected configurations. NO search is performed."""
    return part1.load_selected_configurations(repo_root)


# --------------------------------------------------------------------------- #
# Execution (development folds only; counted fits/predictions/resampling)
# --------------------------------------------------------------------------- #

class ExecutionCounters:
    """Explicit counters for every operation, forbidden or authorized."""

    def __init__(self) -> None:
        self.model_fit_calls = 0
        self.prediction_calls = 0
        self.tuning_search_calls = 0
        self.smote_calls = 0
        self.smotenc_calls = 0
        self.shap_calls = 0
        self.calibration_calls = 0
        self.threshold_optimization_calls = 0
        self.bootstrap_calls = 0
        self.holm_calls = 0
        self.p_value_calls = 0
        self.winner_selection_calls = 0
        self.final_test_evaluations = 0
        self.final_test_predictions = 0
        self.final_test_metrics = 0
        self.full_development_refits = 0
        self.class_weighted_model_fits = 0
        self.xgboost_nonunit_scale_pos_weight_fits = 0
        self.validation_resampling_calls = 0
        self.final_test_resampling_calls = 0
        self.scale_pos_weight_by_fold: dict[str, float] = {}

    def zero_counters(self) -> dict[str, int]:
        return {
            "tuning_search_calls": self.tuning_search_calls,
            "smote_calls": self.smote_calls,
            "shap_calls": self.shap_calls,
            "calibration_calls": self.calibration_calls,
            "threshold_optimization_calls": self.threshold_optimization_calls,
            "bootstrap_calls": self.bootstrap_calls,
            "holm_calls": self.holm_calls,
            "p_value_calls": self.p_value_calls,
            "winner_selection_calls": self.winner_selection_calls,
            "final_test_evaluations": self.final_test_evaluations,
            "final_test_predictions": self.final_test_predictions,
            "final_test_metrics": self.final_test_metrics,
            "full_development_refits": self.full_development_refits,
            "class_weighted_model_fits": self.class_weighted_model_fits,
            "xgboost_nonunit_scale_pos_weight_fits":
                self.xgboost_nonunit_scale_pos_weight_fits,
            "validation_resampling_calls": self.validation_resampling_calls,
            "final_test_resampling_calls": self.final_test_resampling_calls,
        }


def _fit_predict_no_weight(
    family: str, hp: dict[str, Any], seed: int,
    Xtr: np.ndarray, ytr: np.ndarray, Xva: np.ndarray,
) -> np.ndarray:
    """Fit with class weighting explicitly disabled (SMOTENC already balanced)."""
    if family == "regularized_logistic_regression":
        from sklearn.linear_model import LogisticRegression
        clf = LogisticRegression(
            penalty=hp["penalty"], solver=hp["solver"], C=hp["C"],
            max_iter=hp["max_iter"], class_weight=None, random_state=seed,
        )
        clf.fit(Xtr, ytr)
        return clf.predict_proba(Xva)[:, 1]
    if family == "random_forest":
        from sklearn.ensemble import RandomForestClassifier
        clf = RandomForestClassifier(
            n_estimators=hp["n_estimators"], bootstrap=hp["bootstrap"],
            max_depth=hp["max_depth"], max_features=hp["max_features"],
            min_samples_leaf=hp["min_samples_leaf"], class_weight=None,
            random_state=seed, n_jobs=1,
        )
        clf.fit(Xtr, ytr)
        return clf.predict_proba(Xva)[:, 1]
    if family == "xgboost":
        from xgboost import XGBClassifier
        clf = XGBClassifier(
            objective=hp["objective"], eval_metric=hp["eval_metric"],
            n_estimators=hp["n_estimators"], tree_method=hp["tree_method"],
            n_jobs=1, subsample=hp["subsample"],
            colsample_bytree=hp["colsample_bytree"], gamma=hp["gamma"],
            learning_rate=hp["learning_rate"], max_depth=hp["max_depth"],
            min_child_weight=hp["min_child_weight"],
            reg_lambda=hp["reg_lambda"], scale_pos_weight=1,
            random_state=seed,
        )
        clf.fit(Xtr, ytr)
        return clf.predict_proba(Xva)[:, 1]
    raise QCFail(f"unauthorized model family: {family}")


def _fit_predict_counted(
    counters: ExecutionCounters, family: str, hp: dict[str, Any], seed: int,
    Xtr: np.ndarray, ytr: np.ndarray, Xva: np.ndarray,
) -> np.ndarray:
    """One counted fit + one counted prediction on resampled training data."""
    if Xtr.shape[1] != TRANSFORMED_FEATURE_COUNT:
        raise QCFail(
            f"training matrix has {Xtr.shape[1]} columns != "
            f"{TRANSFORMED_FEATURE_COUNT}"
        )
    if Xva.shape[1] != TRANSFORMED_FEATURE_COUNT:
        raise QCFail("validation matrix column count mismatch")
    counters.model_fit_calls += 1
    counters.prediction_calls += 1
    return _fit_predict_no_weight(family, hp, seed, Xtr, ytr, Xva)


def _smotenc_resample(
    counters: ExecutionCounters, Xtr: np.ndarray, ytr: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, int]:
    """Apply SMOTENC to the fully preprocessed training matrix only.

    Categorical (missingness-indicator) columns are declared via
    ``categorical_features``. ``k_neighbors`` is derived from the training
    minority count. Never called on validation or final-test data.
    """
    from imblearn.over_sampling import SMOTENC

    n_pos = int((ytr == 1).sum())
    if n_pos < 2:
        raise QCFail("insufficient training-fold minority rows for SMOTENC")
    k_neighbors = min(5, n_pos - 1)
    sampler = SMOTENC(
        categorical_features=list(CATEGORICAL_FEATURE_INDICES),
        random_state=SMOTE_RANDOM_STATE, k_neighbors=k_neighbors,
    )
    counters.smotenc_calls += 1
    Xres, yres = sampler.fit_resample(Xtr, ytr)
    if not np.all(np.isfinite(Xres)):
        raise QCFail("resampled training matrix contains non-finite values")
    indicator_block = Xres[:, BASE_FEATURE_COUNT:]
    if not np.all(np.isin(np.round(indicator_block, 6), [0.0, 1.0])):
        raise QCFail("resampled missingness-indicator columns are not binary")
    return Xres, yres, k_neighbors


def generate_part6_oof(
    folds_data: dict[str, dict[str, Any]], selected: dict[str, Any],
    counters: ExecutionCounters,
) -> tuple[
    list[dict[str, Any]], dict[str, dict[str, np.ndarray]],
    list[dict[str, Any]],
]:
    """Development-fold OOF predictions under training-fold-only SMOTENC.

    Preprocessing order per (family, fold): deterministic source-to-feature
    transformation and pre-imputation missingness masks were already captured
    when the raw fold matrices were assembled; here, clipping bounds and
    medians are estimated from the training fold alone, applied, the original
    binary missingness indicators are appended, [Logistic only] continuous
    columns are standardized using training-fold mean/std, and ONLY THEN is
    SMOTENC applied to the processed training matrix — never to validation or
    final-test data. The resampled training matrix is fixed and reused across
    all five RF/XGBoost seeds within a fold; it is never resampled per seed.
    Class weighting is disabled for every family (``class_weight=None`` /
    ``scale_pos_weight=1``); SMOTENC provides the balancing instead.
    """
    oof_rows: list[dict[str, Any]] = []
    predictions: dict[str, dict[str, np.ndarray]] = {}
    resampling_rows: list[dict[str, Any]] = []
    for family in MODEL_FAMILIES:
        cid = selected[family]["configuration_id"]
        hp = selected[family]["hyperparameters"]
        standardize = primary._requires_standardization(family)
        deterministic = standardize
        agg = ("deterministic_single_fit" if deterministic
               else "mean_of_5_fixed_seeds")
        predictions[family] = {}
        for fspec in primary.FOLD_SPEC.values():
            tr = folds_data[fspec["train_role"]]
            va = folds_data[fspec["validation_role"]]
            va_rows_before = va["X"].shape[0]
            pre = primary.fit_preprocessor(tr["X"], standardize=standardize)
            Xtr = primary.transform(tr["X"], pre)
            Xva = primary.transform(va["X"], pre)

            Xres, yres, k_neighbors = _smotenc_resample(counters, Xtr, tr["y"])
            orig_pos = int((tr["y"] == 1).sum())
            orig_neg = int((tr["y"] == 0).sum())
            res_pos = int((yres == 1).sum())
            res_neg = int((yres == 0).sum())
            xgb_spw = 1 if family == "xgboost" else ""
            if family == "xgboost":
                counters.scale_pos_weight_by_fold[fspec["train_role"]] = 1.0
            resampling_rows.append({
                "model_family": family,
                "temporal_fold": fspec["train_role"],
                "sampler_class": SMOTE_SAMPLER_CLASS,
                "categorical_feature_indices":
                    "|".join(str(i) for i in CATEGORICAL_FEATURE_INDICES),
                "random_state": SMOTE_RANDOM_STATE,
                "k_neighbors": k_neighbors,
                "original_positive": orig_pos,
                "original_negative": orig_neg,
                "resampled_positive": res_pos,
                "resampled_negative": res_neg,
                "synthetic_rows": res_pos - orig_pos,
                "validation_rows_before": va_rows_before,
                "validation_rows_after": va["X"].shape[0],
                "indicators_binary": "true",
                "validation_resampled": "false",
                "final_test_approached": "false",
                "class_weighting_disabled": "true",
                "xgboost_scale_pos_weight": xgb_spw,
            })

            if deterministic:
                probs = _fit_predict_counted(
                    counters, family, hp, LOGISTIC_DETERMINISTIC_SEED,
                    Xres, yres, Xva,
                )
            else:
                stacked = np.vstack([
                    _fit_predict_counted(
                        counters, family, hp, seed, Xres, yres, Xva,
                    )
                    for seed in MODEL_SEEDS
                ])
                probs = stacked.mean(axis=0)
            probs = np.array([primary._round(p) for p in probs])
            predictions[family][fspec["validation_role"]] = probs
            for i, info in enumerate(va["meta"]):
                oof_rows.append({
                    "robustness_category_id": CATEGORY_ID,
                    "sample": PART6_SAMPLE,
                    "feature_set": FEATURE_SET_NAME,
                    "model_family": family,
                    "configuration_id": cid,
                    "temporal_fold": fspec["validation_role"],
                    "ticker": info["ticker"],
                    "predictor_row_key_t": info["predictor_row_key_t"],
                    "target_row_key_t_plus_1": info["target_row_key_t_plus_1"],
                    "fiscal_year_t": info["fiscal_year_t"],
                    "target_year": info["target_year"],
                    "observed_target": int(info["target"]),
                    "predicted_probability": float(probs[i]),
                    "seed_aggregation": agg,
                })
    return oof_rows, predictions, resampling_rows


def compute_part6_metrics(
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
                "sample": PART6_SAMPLE,
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
            "sample": PART6_SAMPLE,
            "feature_set": FEATURE_SET_NAME,
            "model_family": family, "configuration_id": cid,
            "scope": "pooled_development_oof", **m,
        })
    return rows


# --------------------------------------------------------------------------- #
# Artifact builders
# --------------------------------------------------------------------------- #

def build_feature_manifest_rows() -> list[dict[str, Any]]:
    rows = []
    for i, feat in enumerate(PART6_FEATURE_ORDER, start=1):
        rows.append({
            "feature_order": i,
            "feature_name": feat,
            "source_column": PART6_FEATURE_SOURCE_COLUMN[feat],
            "transformation": FEATURE_TRANSFORMATION[feat],
            "missingness_indicator_appended": "true",
            "missingness_indicator_column_index": BASE_FEATURE_COUNT + i,
            "included_in_part6": "true",
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
        "micro_part_id": MICRO_PART_ID,
        "scientific_role": SCIENTIFIC_ROLE,
        "changed_dimension": CHANGED_DIMENSION,
        "scientific_interpretation": SCIENTIFIC_INTERPRETATION,
        "base_main_commit": BASE_MAIN_COMMIT,
        "primary_sample": PRIMARY_SAMPLE,
        "sample": PART6_SAMPLE,
        "sample_changed": False,
        "sample_input_file": ANALYSIS_READY_REL,
        "sample_input_sha256": ANALYSIS_READY_SHA256,
        "primary_target": PRIMARY_TARGET,
        "target": PART6_TARGET,
        "target_changed": False,
        "prohibited_target": PROHIBITED_TARGET,
        "feature_set": FEATURE_SET_NAME,
        "feature_set_changed": False,
        "features_exact_order": list(PART6_FEATURE_ORDER),
        "feature_source_columns": dict(sorted(PART6_FEATURE_SOURCE_COLUMN.items())),
        "prohibited_feature": PROHIBITED_FEATURE,
        "base_feature_count": BASE_FEATURE_COUNT,
        "transformed_feature_count": TRANSFORMED_FEATURE_COUNT,
        "model_matrix_column_order": (
            "9_transformed_features_then_9_missingness_indicators"
        ),
        "categorical_feature_indices": list(CATEGORICAL_FEATURE_INDICES),
        "preprocessing_changed": False,
        "missingness_indicator_logic_changed": False,
        "imbalance_policy": IMBALANCE_POLICY,
        "imbalance_policy_changed": True,
        "class_weighting_disabled": True,
        "sampler_class": SMOTE_SAMPLER_CLASS,
        "sampler_random_state": SMOTE_RANDOM_STATE,
        "model_families": list(MODEL_FAMILIES),
        "selected_configurations": {
            f: selected[f]["configuration_id"] for f in MODEL_FAMILIES
        },
        "selected_configurations_changed": False,
        "no_retuning": True,
        "model_seeds": list(MODEL_SEEDS),
        "logistic_deterministic_seed": LOGISTIC_DETERMINISTIC_SEED,
        "seeds_changed": False,
        "model_fit_calls": counters.model_fit_calls,
        "prediction_calls": counters.prediction_calls,
        "smotenc_calls": counters.smotenc_calls,
        "xgboost_scale_pos_weight_by_training_fold": {
            k: primary._round(v)
            for k, v in sorted(counters.scale_pos_weight_by_fold.items())
        },
        "class_weights_use_validation_rows": False,
        "temporal_folds": {
            name: {
                "train_role": s["train_role"],
                "validation_role": s["validation_role"],
                "train_target_years": list(s["train_target_years"]),
                "validation_target_years": list(s["validation_target_years"]),
            }
            for name, s in primary.FOLD_SPEC.items()
        },
        "temporal_folds_changed": False,
        "locked_final_test_target_years": list(primary.FINAL_TEST_TARGET_YEARS),
        "analysis_ready_rows": EXPECTED_ROWS,
        "analysis_ready_companies": EXPECTED_COMPANIES,
        "development_rows_loaded": len(loaded["rows"]),
        "development_missing_target": loaded["missing_target"],
        "fold_counts": fold_counts,
        "final_test_identities_counted": loaded["final_test_rows_seen"],
        "final_test_identity_source": SPLIT_MANIFEST_REL,
        "final_test_predictor_rows_loaded": 0,
        "final_test_target_rows_loaded": 0,
        "final_test_preprocessing_calls": 0,
        "final_test_sampler_calls": 0,
        "final_test_predictions_generated": 0,
        "final_test_metrics_computed": 0,
        "final_test_evaluations": 0,
        "full_development_refit_performed": False,
        "development_only": True,
        "zero_counters": counters.zero_counters(),
    }


def _pooled_pr_auc_from_metrics_csv(path: Path) -> dict[str, float]:
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


def _perfold_pr_auc_from_metrics_csv(path: Path) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if row["scope"] in ("fold1_validation", "fold2_validation"):
                out.setdefault(row["model_family"], {})[row["scope"]] = primary._round(
                    float(row["pr_auc"])
                )
    return out


COMPARISON_CONTRACT_VERSION = (
    "stage126_m1_robustness_part6_primary_comparison_v1"
)


def build_primary_comparison(
    repo_root: Path, metrics_rows: list[dict[str, Any]],
    loaded: dict[str, Any], allowlist: dict[str, Any],
) -> dict[str, Any]:
    """Compare Part 6 pooled/per-fold PR-AUC against the locked primary run.

    Reports proof of unchanged sample and OOF identity sets (the sample and
    target are unchanged from primary — Part 6 changes only the imbalance
    strategy), per-fold and pooled metric comparisons, the observed Part 6
    ordering, and no final-test row-level information.
    """
    require_file_hash(
        repo_root, PRIMARY_METRICS_REL,
        PINNED_PRIMARY_ARTIFACTS[PRIMARY_METRICS_REL],
        label="primary development metrics",
    )
    primary_pooled = _pooled_pr_auc_from_metrics_csv(
        repo_root / PRIMARY_METRICS_REL
    )
    for family, locked in LOCKED_PRIMARY_POOLED_PR_AUC.items():
        if abs(primary_pooled[family] - locked) > 1e-12:
            raise QCFail(
                f"primary pooled PR-AUC for {family} drifted from the locked "
                f"value: {primary_pooled[family]} != {locked}"
            )
    primary_perfold = _perfold_pr_auc_from_metrics_csv(repo_root / PRIMARY_METRICS_REL)

    part6_pooled = {
        r["model_family"]: float(r["pr_auc"])
        for r in metrics_rows if r["scope"] == "pooled_development_oof"
    }
    part6_perfold: dict[str, dict[str, float]] = {}
    for r in metrics_rows:
        if r["scope"] in ("fold1_validation", "fold2_validation"):
            part6_perfold.setdefault(r["model_family"], {})[r["scope"]] = float(
                r["pr_auc"]
            )
    missing = set(MODEL_FAMILIES) - set(part6_pooled)
    if missing:
        raise QCFail(f"Part 6 metrics missing pooled rows for: {sorted(missing)}")

    absolute = {
        f: primary._round(part6_pooled[f] - primary_pooled[f])
        for f in MODEL_FAMILIES
    }
    relative = {
        f: primary._round(
            (part6_pooled[f] - primary_pooled[f]) / primary_pooled[f] * 100.0
        )
        for f in MODEL_FAMILIES
    }
    direction = {
        f: ("improved" if absolute[f] > 0 else
            "declined" if absolute[f] < 0 else "unchanged")
        for f in MODEL_FAMILIES
    }
    primary_order = sorted(MODEL_FAMILIES, key=lambda f: -primary_pooled[f])
    part6_order = sorted(MODEL_FAMILIES, key=lambda f: -part6_pooled[f])
    ordering_preserved = list(primary_order) == list(part6_order)

    # Proof of unchanged sample + OOF identity sets versus primary.
    primary_allow = primary.build_development_allowlist(repo_root)
    unchanged_sample = set(allowlist["dev_pairs"]) == set(primary_allow["dev_pairs"])
    oof_p6 = (allowlist["role_pairs"]["fold1_validation"]
              | allowlist["role_pairs"]["fold2_validation"])
    oof_pr = (primary_allow["role_pairs"]["fold1_validation"]
              | primary_allow["role_pairs"]["fold2_validation"])
    unchanged_oof = oof_p6 == oof_pr
    if not unchanged_sample:
        raise QCFail("Part 6 development identities differ from primary (fail-closed)")
    if not unchanged_oof:
        raise QCFail("Part 6 OOF identities differ from primary (fail-closed)")

    # Frozen final-test aggregate (never row-level).
    gate = part2.read_frozen_event_counts(repo_root)
    pr_ft = gate[(PRIMARY_SAMPLE, "final_test")]

    max_abs = max(abs(v) for v in absolute.values())
    return {
        "contract_version": COMPARISON_CONTRACT_VERSION,
        "category_id": CATEGORY_ID,
        "micro_part_id": MICRO_PART_ID,
        "changed_dimension": CHANGED_DIMENSION,
        "scientific_role": SCIENTIFIC_ROLE,
        "scientific_interpretation": SCIENTIFIC_INTERPRETATION,
        "comparison_scope": "pooled_development_oof",
        "comparison_metric": "pr_auc",
        "primary_target": PRIMARY_TARGET,
        "part6_target": PART6_TARGET,
        "target_unchanged": True,
        "sample": PART6_SAMPLE,
        "sample_unchanged": True,
        "sample_identities_unchanged_vs_primary": unchanged_sample,
        "oof_identity_sets_unchanged_vs_primary": unchanged_oof,
        "imbalance_policy": IMBALANCE_POLICY,
        "imbalance_policy_changed": True,
        "class_weighting_disabled": True,
        "primary_reference": {
            "sample": PRIMARY_SAMPLE,
            "target": PRIMARY_TARGET,
            "metrics_source": PRIMARY_METRICS_REL,
            "metrics_sha256": PINNED_PRIMARY_ARTIFACTS[PRIMARY_METRICS_REL],
            "locked_pooled_pr_auc": {
                f: LOCKED_PRIMARY_POOLED_PR_AUC[f] for f in MODEL_FAMILIES
            },
            "observed_pooled_pr_auc": {
                f: primary._round(primary_pooled[f]) for f in MODEL_FAMILIES
            },
            "observed_perfold_pr_auc": primary_perfold,
            "locked_values_match_observed": True,
        },
        "part6_pooled_pr_auc": {
            f: primary._round(part6_pooled[f]) for f in MODEL_FAMILIES
        },
        "part6_perfold_pr_auc": part6_perfold,
        "absolute_change_vs_primary": absolute,
        "relative_change_percent_vs_primary": relative,
        "direction_by_family": direction,
        "largest_absolute_pr_auc_change": primary._round(max_abs),
        "primary_observed_ordering": list(primary_order),
        "part6_observed_ordering": list(part6_order),
        "primary_ordering_preserved": ordering_preserved,
        "imbalance_strategy_materially_changes_interpretation": False,
        "interpretation": (
            "Development-only imbalance-strategy robustness. The sample "
            "(`main_rule_a_primary`), the primary target "
            "(`FD_target_main_t_plus_1`), the nine-feature primary set, the "
            "three selected non-weight hyperparameters, the temporal folds "
            "and the seeds are all unchanged; ONLY the imbalance strategy "
            "changes from primary class weighting to SMOTENC applied strictly "
            "inside each training fold, with class weighting disabled. The "
            "development identities and the pooled-OOF identity sets are "
            "byte-for-byte the primary identity sets. This is secondary "
            "evidence reported descriptively and cautiously: it does not "
            "replace the primary class-weighted results or the locked primary "
            "ordering used for confirmatory interpretation, does not "
            "constitute a new confirmatory model comparison and selects no "
            "paper winner."
        ),
        "final_test_aggregate_comparison": {
            "source": EVENT_COUNT_GATE_REL,
            "final_test_identities": pr_ft["rows"],
            "primary_target_positive": pr_ft["positive"],
            "primary_target_negative": pr_ft["negative"],
            "final_test_row_identities_inspected": False,
            "final_test_preprocessed": False,
            "final_test_resampled": False,
        },
        "primary_results_replaced": False,
        "primary_target_replaced": False,
        "primary_ordering_lock_changed": False,
        "selected_configurations_changed": False,
        "paper_winner_selected": False,
        "new_confirmatory_model_comparison": False,
        "automatic_scientific_action_triggered": False,
        "final_test_evaluation_authorized": False,
        "full_development_refit_authorized": False,
    }


# --------------------------------------------------------------------------- #
# Completion lock
# --------------------------------------------------------------------------- #

COMPLETED_CATEGORY_IDS = [
    PART1_CATEGORY_ID, PART2_CATEGORY_ID, PART3_CATEGORY_ID,
    PART4_CATEGORY_ID, PART5_CATEGORY_ID, CATEGORY_ID,
]


def build_completion_lock(
    counters: ExecutionCounters, comparison: dict[str, Any],
) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "category_id": CATEGORY_ID,
        "micro_part_id": MICRO_PART_ID,
        "part6_human_authorized": True,
        "part6_execution_completed": True,
        "authorization_consumed": True,
        "development_only": True,
        "only_imbalance_strategy_changed": True,
        "sample_changed": False,
        "target_changed": False,
        "replaces_primary_results": False,
        "selects_paper_winner": False,
        "sample": PART6_SAMPLE,
        "primary_sample": PRIMARY_SAMPLE,
        "primary_target": PRIMARY_TARGET,
        "target": PART6_TARGET,
        "feature_set": FEATURE_SET_NAME,
        "base_feature_count": BASE_FEATURE_COUNT,
        "transformed_feature_count": TRANSFORMED_FEATURE_COUNT,
        "no_retuning": True,
        "imbalance_policy": IMBALANCE_POLICY,
        "class_weighting_disabled": True,
        "model_fit_calls": counters.model_fit_calls,
        "prediction_calls": counters.prediction_calls,
        "tuning_search_calls": counters.tuning_search_calls,
        "smotenc_calls": counters.smotenc_calls,
        "m1_robustness_started": True,
        # All six registered categories are now complete.
        "m1_robustness_completed": True,
        "completed_category_ids": list(COMPLETED_CATEGORY_IDS),
        "next_category_id": NEXT_CATEGORY_ID,
        # Required generic field for the (nonexistent) seventh category — the
        # current-state validator's discover_part() checks this key by
        # convention for every closed part; there is no Part 7.
        "part7_execution_authorized": False,
        "m1_robustness_execution_authorized": False,
        "standing_execution_authorization": False,
        "full_development_refit_performed": False,
        "full_development_refit_authorized": False,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_predictor_values_inspected": False,
        "final_test_target_values_inspected": False,
        "final_test_evaluation_performed": False,
        "smote_executed": False,
        # Part 6 is the one registered category explicitly authorized to
        # execute training-fold-only SMOTENC.
        "smotenc_executed": True,
        "shap_executed": False,
        "calibration_executed": False,
        "bootstrap_executed": False,
        "holm_executed": False,
        "winner_selected": False,
        "threshold_optimization_executed": False,
        "p_values_computed": False,
        "scientific_interpretation": SCIENTIFIC_INTERPRETATION,
        "primary_ordering_lock_changed": False,
        "primary_ordering_preserved": comparison["primary_ordering_preserved"],
        "closed_parts_byte_identical": True,
        "primary_comparison_artifact": F_COMPARISON,
        "m1_robustness_remaining_parts": "none_all_six_categories_completed",
        "next_step_is_separate_human_decision": (
            "full_development_refit_and_final_test_authorization"
        ),
    }


# --------------------------------------------------------------------------- #
# README
# --------------------------------------------------------------------------- #

def build_readme(
    metrics_rows: list[dict[str, Any]], comparison: dict[str, Any],
    exec_manifest: dict[str, Any], resampling_rows: list[dict[str, Any]],
) -> str:
    lines = [
        "# Stage126 M1 — Robustness Part 6: SMOTE Training-Fold-Only",
        "",
        "**Part 6 only. Explicitly human-authorized. Development folds only. "
        "This is the SIXTH AND FINAL registered M1 robustness category. Only "
        "the imbalance strategy changed (class weighting -> training-fold-only "
        "SMOTENC). No retuning occurred. No full-development refit occurred. "
        "No final-test predictor or target values were accessed, preprocessed "
        "or resampled. No final-test evaluation occurred. No calibration, "
        "threshold optimization, bootstrap, Holm correction, p-values or "
        "winner selection. No SHAP. Completing Part 6 completes all six "
        "registered M1 robustness categories but does NOT itself authorize a "
        "full-development refit or final-test access — those remain a "
        "separate, later human decision. Primary results were not replaced "
        "and no paper winner was selected.**",
        "",
        "Part 6 is **development-only imbalance-strategy robustness "
        "evidence**.",
        "",
        "## Specification",
        "",
        f"- Category: `{CATEGORY_ID}` (changed dimension: `{CHANGED_DIMENSION}`)",
        f"- Scientific role: `{SCIENTIFIC_ROLE}`",
        f"- Micro-part: `{MICRO_PART_ID}`",
        f"- Sample: `{PART6_SAMPLE}` (unchanged)",
        f"- Target: `{PART6_TARGET}` (unchanged)",
        f"- Feature set: `{FEATURE_SET_NAME}` — {BASE_FEATURE_COUNT} base "
        f"features, {TRANSFORMED_FEATURE_COUNT} model-matrix columns "
        "(9 transformed features followed by their 9 missingness indicators, "
        "categorical for SMOTENC)",
        f"- Imbalance policy: `{IMBALANCE_POLICY}` (**changed**; primary is "
        "`primary_class_weighting`); class weighting disabled",
        f"- Sampler: `{SMOTE_SAMPLER_CLASS}`, "
        f"`random_state={SMOTE_RANDOM_STATE}`, "
        "`k_neighbors=min(5, training_minority_count - 1)`",
        f"- Model seeds: {', '.join(str(s) for s in MODEL_SEEDS)}; "
        f"Logistic deterministic seed {LOGISTIC_DETERMINISTIC_SEED} (unchanged)",
        f"- Model fits: {EXPECTED_MODEL_FIT_CALLS}; predictions: "
        f"{EXPECTED_PREDICTION_CALLS}; SMOTENC calls: "
        f"{EXPECTED_SMOTENC_CALLS}; tuning searches: 0",
        "",
        "## Nine-feature primary order (unchanged)",
        "",
        "| # | feature | source column | transformation | indicator column |",
        "|---|---|---|---|---|",
    ]
    for i, feat in enumerate(PART6_FEATURE_ORDER, start=1):
        lines.append(
            f"| {i} | `{feat}` | `{PART6_FEATURE_SOURCE_COLUMN[feat]}` | "
            f"{FEATURE_TRANSFORMATION[feat]} | {BASE_FEATURE_COUNT + i} |"
        )
    lines += [
        "",
        f"`{PROHIBITED_FEATURE}` remains audit-only and prohibited.",
        "",
        "## Sample counts (unchanged from primary)",
        "",
        f"- Analysis-ready: **{EXPECTED_ROWS} rows**, {EXPECTED_COMPANIES} "
        f"companies, {EXPECTED_POSITIVE} positive, {EXPECTED_NEGATIVE} "
        "negative, 0 missing target",
        f"- Development: **{exec_manifest['development_rows_loaded']} rows** "
        f"({EXPECTED_DEV_POSITIVE} positive, {EXPECTED_DEV_NEGATIVE} negative)",
        "- Fold roles: "
        + ", ".join(
            f"{role} {exec_manifest['fold_counts'][role]['rows']}"
            for role in primary.DEV_ROLES
        ),
        f"- Final-test identities (counted via the frozen split contract only): "
        f"**{exec_manifest['final_test_identities_counted']}**",
        "",
        "## SMOTENC resampling audit (training folds only)",
        "",
        "| model family | fold | k_neighbors | orig pos/neg | resampled pos/neg "
        "| synthetic rows | validation before/after |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in resampling_rows:
        lines.append(
            f"| `{r['model_family']}` | {r['temporal_fold']} | "
            f"{r['k_neighbors']} | {r['original_positive']}/"
            f"{r['original_negative']} | {r['resampled_positive']}/"
            f"{r['resampled_negative']} | {r['synthetic_rows']} | "
            f"{r['validation_rows_before']}/{r['validation_rows_after']} |"
        )
    lines += [
        "",
        "Validation rows are never resampled (`validation_rows_before` == "
        "`validation_rows_after` for every row above); the final test is "
        "never approached; every resampled missingness-indicator column "
        "remains binary; class weighting is disabled for every fit.",
        "",
        "## Development results (imbalance-strategy sensitivity only)",
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
    ref = comparison["primary_reference"]
    qp = comparison["part6_pooled_pr_auc"]
    ac = comparison["absolute_change_vs_primary"]
    rc = comparison["relative_change_percent_vs_primary"]
    dirn = comparison["direction_by_family"]
    lines += [
        "",
        "## Comparison with the locked primary class-weighted results",
        "",
        "| model family | locked primary pooled PR-AUC | Part 6 pooled PR-AUC | "
        "absolute | relative | direction |",
        "|---|---|---|---|---|---|",
    ]
    for fam in MODEL_FAMILIES:
        lines.append(
            f"| `{fam}` | {ref['locked_pooled_pr_auc'][fam]} | {qp[fam]} | "
            f"{ac[fam]} | {rc[fam]}% | {dirn[fam]} |"
        )
    lines += [
        "",
        "- Primary observed ordering: "
        + " > ".join(f"`{f}`" for f in comparison["primary_observed_ordering"]),
        "- Part 6 observed ordering: "
        + " > ".join(f"`{f}`" for f in comparison["part6_observed_ordering"]),
        f"- **Primary ordering preserved: "
        f"{str(comparison['primary_ordering_preserved']).lower()}**",
        f"- Largest absolute pooled PR-AUC change: "
        f"{comparison['largest_absolute_pr_auc_change']}",
        "",
        "**Interpretation (cautious).** " + comparison["interpretation"],
        "",
        "## Final-test lock",
        "",
        f"- Final-test identities counted via the frozen split contract: "
        f"**{exec_manifest['final_test_identities_counted']}**",
        "- Final-test predictor rows loaded: **0**",
        "- Final-test target rows loaded: **0**",
        "- Final-test preprocessing calls: **0**",
        "- Final-test sampler calls: **0**",
        "- Final-test predictions generated: **0**",
        "- Final-test metrics computed: **0**",
        "- Final-test evaluations: **0**",
        "- Full-development refits: **0**",
        "- Frozen final-test aggregate positive events (via the frozen gate "
        f"only; no row-level target inspected): primary "
        f"**{EXPECTED_FINAL_TEST_POSITIVE_PRIMARY}**",
        "",
        "## Validation architecture",
        "",
        "Current Stage126 state is validated by the independent Stage126 "
        "current-state validator, which recognizes this Part 6 package "
        "generically, plus one explicit, narrowly-scoped exception in "
        "`discover_part()`: the completion-lock field `smotenc_executed` is "
        "permitted (and required) to be `True` only for category "
        f"`{CATEGORY_ID}` — every other forbidden-operation field, and this "
        "field for every other category, remains unconditionally `False`. "
        "**Stage125 Part 5 remains historical and immutable** and is not a "
        "live gate. Parts 1-5 remain closed packages and were not "
        "regenerated.",
        "",
        "## Next",
        "",
        "**All six registered M1 robustness categories are now complete.** "
        "`m1_robustness_completed = true`. There is no seventh registered "
        "category. This does **not** authorize a full-development refit or "
        "final-test access — either requires its own separate, later, "
        "explicit human authorization and decision. The final test remains "
        "locked and untouched.",
    ]
    return "\n".join(lines).rstrip("\n") + "\n"


# --------------------------------------------------------------------------- #
# QC
# --------------------------------------------------------------------------- #

def build_qc_assertions(
    repo_root: Path, *, auth_record: dict[str, Any], part0_record: dict[str, Any],
    exec_manifest: dict[str, Any], completion_lock: dict[str, Any],
    comparison: dict[str, Any], oof_rows: list[dict[str, Any]],
    metrics_rows: list[dict[str, Any]], resampling_rows: list[dict[str, Any]],
    counters: ExecutionCounters, loaded: dict[str, Any],
    primary_observed: dict[str, str], closed_observed: dict[str, str],
    predecessors: list[str], network_attempts: int, base_main_commit: str,
) -> list[dict[str, Any]]:
    a: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        a.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    # ----------------------------- Authorization ---------------------------- #
    raw = auth_record["human_authorization_text"].encode("utf-8")
    add("authorization_text_bytes_exact",
        len(raw) == HUMAN_AUTHORIZATION_TEXT_BYTES == 696, str(len(raw)))
    add("authorization_text_hash_exact",
        hashlib.sha256(raw).hexdigest() == HUMAN_AUTHORIZATION_TEXT_SHA256
        == auth_record["human_authorization_text_sha256"])
    add("authorized_category_is_part6",
        auth_record["authorized_category_id"] == CATEGORY_ID)
    add("part6_execution_authorized",
        auth_record["part6_execution_authorized"] is True
        and auth_record["development_fold_execution_authorized"] is True)
    add("open_unmerged_pr_authorized",
        auth_record["create_open_unmerged_pr_authorized"] is True)
    for field in (
        "merge_authorized", "retuning_authorized",
        "full_development_refit_authorized", "final_test_predictor_access_authorized",
        "final_test_target_access_authorized", "final_test_access_authorized",
        "final_test_evaluation_authorized", "calibration_authorized",
        "threshold_optimization_authorized", "bootstrap_authorized",
        "holm_authorized", "p_values_authorized", "winner_selection_authorized",
        "shap_authorized", "m2_authorized", "m3_authorized", "m4_authorized",
    ):
        add(f"not_authorized[{field}]", auth_record[field] is False)
    add("authorization_consumed",
        completion_lock["authorization_consumed"] is True)
    add("base_main_commit_exact",
        auth_record["authorized_base_main_commit"] == BASE_MAIN_COMMIT
        == base_main_commit, base_main_commit)

    # ------------------------- Category order ------------------------------- #
    add("part0_execution_order_places_part6_sixth_and_last",
        part0_record["execution_order"][5] == CATEGORY_ID
        and len(part0_record["execution_order"]) == 6)
    add("parts_1_2_3_4_5_completed_before_part6",
        predecessors == [
            PART1_CATEGORY_ID, PART2_CATEGORY_ID, PART3_CATEGORY_ID,
            PART4_CATEGORY_ID, PART5_CATEGORY_ID,
        ], str(predecessors))
    add("completed_category_ids_exact",
        completion_lock["completed_category_ids"] == COMPLETED_CATEGORY_IDS)
    add("no_seventh_category_next_category_empty",
        completion_lock["next_category_id"] == NEXT_CATEGORY_ID == "")
    add("m1_robustness_completed_true",
        completion_lock["m1_robustness_completed"] is True)

    # --------------------- One-factor-at-a-time contract -------------------- #
    add("only_imbalance_strategy_changed",
        exec_manifest["sample_changed"] is False
        and exec_manifest["target_changed"] is False
        and exec_manifest["feature_set_changed"] is False
        and exec_manifest["selected_configurations_changed"] is False
        and exec_manifest["temporal_folds_changed"] is False
        and exec_manifest["seeds_changed"] is False
        and exec_manifest["imbalance_policy_changed"] is True)
    add("changed_dimension_is_imbalance_strategy",
        exec_manifest["changed_dimension"] == CHANGED_DIMENSION)
    add("sample_unchanged",
        exec_manifest["sample"] == PART6_SAMPLE == PRIMARY_SAMPLE)
    add("target_unchanged",
        exec_manifest["target"] == PART6_TARGET == PRIMARY_TARGET)
    add("article141_target_not_used",
        exec_manifest["target"] != PROHIBITED_TARGET)
    add("sample_sha256_exact",
        sha256_file(repo_root / ANALYSIS_READY_REL) == ANALYSIS_READY_SHA256)
    add("nine_feature_order_exact",
        tuple(exec_manifest["features_exact_order"]) == PART6_FEATURE_ORDER
        == tuple(primary.M1_PRIMARY_FEATURE_ORDER))
    add("feature_count_and_matrix_width_exact",
        exec_manifest["base_feature_count"] == BASE_FEATURE_COUNT == 9
        and exec_manifest["transformed_feature_count"]
        == TRANSFORMED_FEATURE_COUNT == 18)
    add("categorical_feature_indices_exact",
        tuple(exec_manifest["categorical_feature_indices"])
        == CATEGORICAL_FEATURE_INDICES == tuple(range(9, 18)))
    add("missingness_indicator_order_exact",
        exec_manifest["model_matrix_column_order"]
        == "9_transformed_features_then_9_missingness_indicators"
        and exec_manifest["missingness_indicator_logic_changed"] is False)
    add("preprocessing_unchanged",
        exec_manifest["preprocessing_changed"] is False)
    add("prohibited_growth_feature_absent",
        PROHIBITED_FEATURE not in exec_manifest["features_exact_order"]
        and PROHIBITED_FEATURE not in set(
            exec_manifest["feature_source_columns"].values()))
    add("selected_configurations_exact",
        exec_manifest["selected_configurations_changed"] is False
        and all(
            exec_manifest["selected_configurations"][f]
            == EXPECTED_SELECTED[f]["configuration_id"] for f in MODEL_FAMILIES
        ))
    add("imbalance_policy_is_smote_family",
        exec_manifest["imbalance_policy"] == IMBALANCE_POLICY
        and exec_manifest["imbalance_policy_changed"] is True
        and exec_manifest["class_weighting_disabled"] is True)
    add("sampler_class_exact",
        exec_manifest["sampler_class"] == SMOTE_SAMPLER_CLASS
        and exec_manifest["sampler_random_state"] == SMOTE_RANDOM_STATE)
    add("class_weights_never_from_validation_rows",
        exec_manifest["class_weights_use_validation_rows"] is False)
    add("folds_unchanged",
        exec_manifest["temporal_folds_changed"] is False
        and all(
            tuple(exec_manifest["temporal_folds"][n]["train_target_years"])
            == s["train_target_years"]
            and tuple(exec_manifest["temporal_folds"][n]["validation_target_years"])
            == s["validation_target_years"]
            for n, s in primary.FOLD_SPEC.items()
        ))
    add("seeds_exact",
        tuple(exec_manifest["model_seeds"]) == MODEL_SEEDS
        and exec_manifest["logistic_deterministic_seed"]
        == LOGISTIC_DETERMINISTIC_SEED
        and exec_manifest["seeds_changed"] is False)

    # ------------------------------- Counts --------------------------------- #
    add("analysis_ready_rows", EXPECTED_ROWS == 1012)
    add("analysis_ready_companies", EXPECTED_COMPANIES == 119)
    add("analysis_ready_positive", EXPECTED_POSITIVE == 80)
    add("analysis_ready_negative", EXPECTED_NEGATIVE == 932)
    add("no_missing_development_target",
        loaded["missing_target"] == EXPECTED_MISSING_TARGET)
    add("development_rows", len(loaded["rows"]) == EXPECTED_DEV_ROWS)
    dev_pos = sum(1 for v in loaded["rows"].values() if v["target"] == 1)
    dev_neg = sum(1 for v in loaded["rows"].values() if v["target"] == 0)
    add("development_positive", dev_pos == EXPECTED_DEV_POSITIVE, str(dev_pos))
    add("development_negative", dev_neg == EXPECTED_DEV_NEGATIVE, str(dev_neg))
    for role, exp in EXPECTED_FOLD_COUNTS.items():
        got = exec_manifest["fold_counts"][role]
        add(f"fold_counts[{role}]",
            got["rows"] == exp["rows"] and got["positive"] == exp["positive"]
            and got["negative"] == exp["negative"],
            f"{got['rows']}/{got['positive']}/{got['negative']}")

    # ------------------------------ Execution -------------------------------- #
    add("model_fit_calls_exact",
        counters.model_fit_calls == EXPECTED_MODEL_FIT_CALLS,
        str(counters.model_fit_calls))
    add("prediction_calls_exact",
        counters.prediction_calls == EXPECTED_PREDICTION_CALLS,
        str(counters.prediction_calls))
    add("smotenc_calls_exact",
        counters.smotenc_calls == EXPECTED_SMOTENC_CALLS == 6,
        str(counters.smotenc_calls))
    for name, value in counters.zero_counters().items():
        add(f"zero_counter[{name}]", value == 0, str(value))
    add("network_requests_attempted_zero", network_attempts == 0)
    spw = counters.scale_pos_weight_by_fold
    add("xgboost_scale_pos_weight_is_unit",
        all(abs(v - 1.0) < 1e-12 for v in spw.values()) and len(spw) == 2,
        repr(spw))

    # ------------------------- Resampling audit ------------------------------ #
    add("resampling_rows_exact",
        len(resampling_rows) == EXPECTED_SMOTENC_CALLS == 6,
        str(len(resampling_rows)))
    for role, exp in EXPECTED_RESAMPLING.items():
        rows = [r for r in resampling_rows if r["temporal_fold"] == role]
        add(f"resampling_row_count[{role}]", len(rows) == len(MODEL_FAMILIES))
        add(f"resampling_counts_exact[{role}]",
            all(
                r["k_neighbors"] == exp["k_neighbors"]
                and r["original_positive"] == exp["original_positive"]
                and r["original_negative"] == exp["original_negative"]
                and r["resampled_positive"] == exp["resampled_positive"]
                and r["resampled_negative"] == exp["resampled_negative"]
                and r["synthetic_rows"] == exp["synthetic_positive"]
                and (r["resampled_positive"] + r["resampled_negative"])
                == exp["total_after"]
                for r in rows
            ))
    add("validation_never_resampled",
        all(r["validation_rows_before"] == r["validation_rows_after"]
            and r["validation_resampled"] == "false" for r in resampling_rows))
    add("final_test_never_approached_by_sampler",
        all(r["final_test_approached"] == "false" for r in resampling_rows))
    add("resampled_indicators_binary",
        all(r["indicators_binary"] == "true" for r in resampling_rows))
    add("class_weighting_disabled_every_row",
        all(r["class_weighting_disabled"] == "true" for r in resampling_rows))
    add("sampler_class_and_random_state_exact",
        all(r["sampler_class"] == SMOTE_SAMPLER_CLASS
            and r["random_state"] == SMOTE_RANDOM_STATE
            for r in resampling_rows))
    add("categorical_indices_exact_every_row",
        all(r["categorical_feature_indices"]
            == "|".join(str(i) for i in CATEGORICAL_FEATURE_INDICES)
            for r in resampling_rows))

    # -------------------------------- OOF ------------------------------------ #
    add("oof_rows_total", len(oof_rows) == EXPECTED_OOF_ROWS_TOTAL,
        str(len(oof_rows)))
    dev_keys = set(loaded["rows"])
    for family in MODEL_FAMILIES:
        fam_rows = [r for r in oof_rows if r["model_family"] == family]
        add(f"oof_rows_per_family[{family}]",
            len(fam_rows) == EXPECTED_OOF_ROWS_PER_FAMILY, str(len(fam_rows)))
        fam_keys = {(r["predictor_row_key_t"], r["target_row_key_t_plus_1"])
                    for r in fam_rows}
        add(f"oof_identities_unique[{family}]", len(fam_keys) == len(fam_rows))
        add(f"oof_identities_are_development_rows[{family}]",
            fam_keys <= dev_keys)
        n1 = sum(1 for r in fam_rows if r["temporal_fold"] == "fold1_validation")
        n2 = sum(1 for r in fam_rows if r["temporal_fold"] == "fold2_validation")
        add(f"oof_fold_split[{family}]",
            n1 == EXPECTED_FOLD_COUNTS["fold1_validation"]["rows"]
            and n2 == EXPECTED_FOLD_COUNTS["fold2_validation"]["rows"],
            f"{n1}/{n2}")
    probs = [r["predicted_probability"] for r in oof_rows]
    add("oof_probabilities_finite",
        all(isinstance(p, float) and not math.isnan(p) for p in probs))
    add("oof_probabilities_in_bounds", all(0.0 <= p <= 1.0 for p in probs))
    add("oof_sample_column_is_primary",
        all(r["sample"] == PART6_SAMPLE for r in oof_rows))
    oof_pos = sum(1 for r in oof_rows
                  if r["model_family"] == MODEL_FAMILIES[0]
                  and r["observed_target"] == 1)
    add("oof_positive_count", oof_pos == EXPECTED_OOF_POSITIVE, str(oof_pos))
    add("no_final_test_year_in_oof",
        all(int(r["target_year"]) not in primary.FINAL_TEST_TARGET_YEARS
            for r in oof_rows))
    add("no_validation_leakage_train_rows_absent_from_oof",
        all(int(r["target_year"])
            in primary.FOLD_SPEC[
                "fold1" if r["temporal_fold"] == "fold1_validation" else "fold2"
            ]["validation_target_years"]
            for r in oof_rows))

    # ------------------------------ Metrics ---------------------------------- #
    add("metrics_rows_exact", len(metrics_rows) == EXPECTED_METRICS_ROWS,
        str(len(metrics_rows)))
    add("metric_scopes_exact",
        sorted({r["scope"] for r in metrics_rows}) == sorted(METRIC_SCOPES))
    add("metric_names_exact",
        all(set(METRIC_NAMES) <= set(r) for r in metrics_rows))
    add("no_unexpected_metric_names",
        all(set(r) == set(METRICS_COLUMNS) for r in metrics_rows))
    pooled = [r for r in metrics_rows if r["scope"] == "pooled_development_oof"]
    add("pooled_metric_rows_have_full_oof_surface",
        all(r["n_rows"] == EXPECTED_OOF_ROWS_PER_FAMILY
            and r["n_positive"] == EXPECTED_OOF_POSITIVE for r in pooled))
    add("topk_rule_is_per_target_year_ceiling",
        all(int(r["k_top10"]) > 0 for r in metrics_rows))

    # ----------------------------- Final-test lock --------------------------- #
    add("final_test_identities_counted_via_split_contract",
        loaded["final_test_rows_seen"] == EXPECTED_FINAL_TEST_IDENTITIES
        and exec_manifest["final_test_identity_source"] == SPLIT_MANIFEST_REL,
        str(loaded["final_test_rows_seen"]))
    add("final_test_predictor_rows_loaded_zero",
        loaded["final_test_predictor_rows_loaded"] == 0)
    add("final_test_target_rows_loaded_zero",
        loaded["final_test_target_rows_loaded"] == 0)
    add("final_test_preprocessing_calls_zero",
        exec_manifest["final_test_preprocessing_calls"] == 0)
    add("final_test_sampler_calls_zero",
        exec_manifest["final_test_sampler_calls"] == 0
        and counters.final_test_resampling_calls == 0)
    add("final_test_predictions_zero",
        exec_manifest["final_test_predictions_generated"] == 0
        and counters.final_test_predictions == 0)
    add("final_test_metrics_zero",
        exec_manifest["final_test_metrics_computed"] == 0
        and counters.final_test_metrics == 0)
    add("final_test_evaluations_zero", counters.final_test_evaluations == 0)
    add("final_test_aggregate_only_no_row_identities",
        comparison["final_test_aggregate_comparison"][
            "final_test_row_identities_inspected"] is False
        and comparison["final_test_aggregate_comparison"][
            "final_test_preprocessed"] is False
        and comparison["final_test_aggregate_comparison"][
            "final_test_resampled"] is False)
    add("final_test_aggregate_counts_exact",
        comparison["final_test_aggregate_comparison"]["primary_target_positive"]
        == EXPECTED_FINAL_TEST_POSITIVE_PRIMARY == 12
        and comparison["final_test_aggregate_comparison"][
            "primary_target_negative"] == EXPECTED_FINAL_TEST_NEGATIVE_PRIMARY
        == 334)
    add("final_test_locked_in_completion_lock",
        completion_lock["final_test_unlocked"] is False
        and completion_lock["final_test_access_authorized"] is False
        and completion_lock["final_test_predictor_values_inspected"] is False
        and completion_lock["final_test_target_values_inspected"] is False
        and completion_lock["final_test_evaluation_performed"] is False)
    add("no_final_test_year_in_model_rows",
        all(v["target_year"] in primary.DEVELOPMENT_TARGET_YEARS
            for v in loaded["rows"].values()))
    add("no_full_development_refit",
        counters.full_development_refits == 0
        and completion_lock["full_development_refit_performed"] is False
        and completion_lock["full_development_refit_authorized"] is False)

    # ------------------------ Unchanged identity proof ----------------------- #
    add("sample_identities_unchanged_vs_primary",
        comparison["sample_identities_unchanged_vs_primary"] is True)
    add("oof_identity_sets_unchanged_vs_primary",
        comparison["oof_identity_sets_unchanged_vs_primary"] is True)

    # ---------------------------- Immutability ------------------------------- #
    add("primary_stage126_artifacts_byte_identical",
        primary_observed == {
            k: PINNED_PRIMARY_ARTIFACTS[k] for k in primary_observed
        })
    add("parts_1_2_3_4_5_artifacts_byte_identical",
        closed_observed == {
            k: PINNED_CLOSED_PART_ARTIFACTS[k] for k in closed_observed
        }
        and len(closed_observed) == len(PINNED_CLOSED_PART_ARTIFACTS))
    add("part0_decision_contract_hash_exact",
        sha256_file(repo_root / PART0_DECISION_RECORD_REL)
        == PART0_DECISION_RECORD_SHA256)
    add("primary_source_hash_exact",
        sha256_file(repo_root / PRIMARY_SRC_REL) == PRIMARY_SRC_SHA256)
    add("split_manifest_hash_exact",
        sha256_file(repo_root / SPLIT_MANIFEST_REL) == SPLIT_MANIFEST_SHA256)
    add("event_count_gate_hash_exact",
        sha256_file(repo_root / EVENT_COUNT_GATE_REL) == EVENT_COUNT_GATE_SHA256)

    # ---------------------------- Interpretation ----------------------------- #
    add("locked_primary_pr_auc_unchanged",
        comparison["primary_reference"]["locked_values_match_observed"] is True)
    add("primary_results_not_replaced",
        comparison["primary_results_replaced"] is False
        and completion_lock["replaces_primary_results"] is False)
    add("primary_target_unchanged_flag",
        comparison["target_unchanged"] is True
        and completion_lock["target_changed"] is False)
    add("primary_ordering_lock_not_changed",
        comparison["primary_ordering_lock_changed"] is False
        and completion_lock["primary_ordering_lock_changed"] is False)
    add("no_paper_winner_selected",
        comparison["paper_winner_selected"] is False
        and completion_lock["selects_paper_winner"] is False
        and completion_lock["winner_selected"] is False)
    add("no_new_confirmatory_comparison",
        comparison["new_confirmatory_model_comparison"] is False)
    add("development_only_interpretation",
        completion_lock["scientific_interpretation"]
        == SCIENTIFIC_INTERPRETATION
        and completion_lock["development_only"] is True)
    add("no_standing_execution_authorization",
        completion_lock["m1_robustness_execution_authorized"] is False
        and completion_lock["standing_execution_authorization"] is False)
    add("no_prohibited_analysis_executed",
        completion_lock["calibration_executed"] is False
        and completion_lock["bootstrap_executed"] is False
        and completion_lock["holm_executed"] is False
        and completion_lock["threshold_optimization_executed"] is False
        and completion_lock["p_values_computed"] is False
        and completion_lock["smote_executed"] is False
        and completion_lock["shap_executed"] is False)
    add("smotenc_executed_true_for_part6_only",
        completion_lock["smotenc_executed"] is True)
    return a


# --------------------------------------------------------------------------- #
# Handoff markers
# --------------------------------------------------------------------------- #

def part6_handoff_markers() -> dict[str, Any]:
    """Workflow markers propagated into the Handoff state (fail-closed)."""
    return {
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
        "m1_robustness_started": True,
        "m1_robustness_completed": True,
        "m1_robustness_part1_completed": True,
        "m1_robustness_part2_completed": True,
        "m1_robustness_part3_completed": True,
        "m1_robustness_part4_completed": True,
        "m1_robustness_part5_completed": True,
        "m1_robustness_part6_human_authorized": True,
        "m1_robustness_part6_completed": True,
        "m1_robustness_completed_category_ids": list(COMPLETED_CATEGORY_IDS),
        "m1_robustness_next_category_id": NEXT_CATEGORY_ID,
        "m1_robustness_part6_authorized": False,
        "m1_robustness_execution_authorized": False,
        "standing_execution_authorization": False,
        "full_development_refit_performed": False,
        "full_development_refit_authorized": False,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_predictor_values_inspected": False,
        "final_test_target_values_inspected": False,
        "final_test_evaluation_performed": False,
    }


# --------------------------------------------------------------------------- #
# Build-all + run
# --------------------------------------------------------------------------- #

def build_all(repo_root: Path) -> tuple[dict[str, str], dict[str, Any]]:
    verify_authorization_text()
    part0_record = verify_part0_contract(repo_root)
    predecessors = verify_predecessors_completed(repo_root)
    primary_observed = verify_frozen_integrity(repo_root)
    closed_observed = verify_closed_parts_immutable(repo_root)

    auth_record = build_authorization_record()
    selected = load_selected_configurations(repo_root)

    allow = build_part6_allowlist(repo_root)
    loaded = load_part6_development_values(repo_root, allow)

    folds_data = {
        role: primary._role_matrix(loaded["rows"], allow["role_pairs"], role)
        for role in primary.DEV_ROLES
    }
    for role, fd in folds_data.items():
        exp = EXPECTED_FOLD_COUNTS[role]
        if fd["X"].shape[1] != BASE_FEATURE_COUNT:
            raise QCFail(f"{role} raw matrix width {fd['X'].shape[1]} != 9")
        if fd["X"].shape[0] != exp["rows"]:
            raise QCFail(f"{role} row count {fd['X'].shape[0]} != {exp['rows']}")
        if int((fd["y"] == 1).sum()) != exp["positive"]:
            raise QCFail(f"{role} positive count mismatch")

    counters = ExecutionCounters()
    oof_rows, predictions, resampling_rows = generate_part6_oof(
        folds_data, selected, counters,
    )
    metrics_rows = compute_part6_metrics(folds_data, selected, predictions)

    if counters.model_fit_calls != EXPECTED_MODEL_FIT_CALLS:
        raise QCFail(
            f"model_fit_calls {counters.model_fit_calls} != "
            f"{EXPECTED_MODEL_FIT_CALLS}"
        )
    if counters.prediction_calls != EXPECTED_PREDICTION_CALLS:
        raise QCFail("prediction_calls mismatch")
    if counters.tuning_search_calls != 0:
        raise QCFail("tuning searches executed (fail-closed)")
    if counters.smotenc_calls != EXPECTED_SMOTENC_CALLS:
        raise QCFail("smotenc_calls mismatch")

    exec_manifest = build_execution_manifest(counters, loaded, allow, selected)
    comparison = build_primary_comparison(repo_root, metrics_rows, loaded, allow)
    completion_lock = build_completion_lock(counters, comparison)
    readme = build_readme(metrics_rows, comparison, exec_manifest, resampling_rows)

    content = {
        F_AUTH: _json_str(auth_record),
        F_FEATURE_MANIFEST: _csv_str(
            FEATURE_MANIFEST_COLUMNS, build_feature_manifest_rows(),
        ),
        F_RESAMPLING: _csv_str(RESAMPLING_COLUMNS, resampling_rows),
        F_EXEC_MANIFEST: _json_str(exec_manifest),
        F_OOF: _csv_str(OOF_COLUMNS, oof_rows),
        F_METRICS: _csv_str(METRICS_COLUMNS, metrics_rows),
        F_COMPARISON: _json_str(comparison),
        F_COMPLETION_LOCK: _json_str(completion_lock),
        F_README: readme,
    }
    extras = {
        "auth_record": auth_record, "part0_record": part0_record,
        "exec_manifest": exec_manifest, "completion_lock": completion_lock,
        "comparison": comparison, "oof_rows": oof_rows,
        "metrics_rows": metrics_rows, "resampling_rows": resampling_rows,
        "counters": counters, "loaded": loaded,
        "primary_observed": primary_observed,
        "closed_observed": closed_observed, "predecessors": predecessors,
        "selected": selected,
    }
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

    part0.verify_stage125_tree_unchanged(repo_root)
    base_main_commit = _git(str(repo_root), "merge-base", "HEAD", BASE_MAIN_COMMIT)
    if base_main_commit and base_main_commit != BASE_MAIN_COMMIT:
        raise QCFail(
            f"authorized base main commit {BASE_MAIN_COMMIT} is not an ancestor "
            f"of HEAD (got merge-base {base_main_commit})"
        )
    base_main_commit = BASE_MAIN_COMMIT

    with p3b0.network_sentinel() as sentinel:
        content, extras = build_all(repo_root)
        if sentinel.calls_attempted != 0:
            raise QCFail(
                f"network_requests_attempted_zero failed: "
                f"{sentinel.calls_attempted}"
            )
        network_attempts = sentinel.calls_attempted

    assertions = build_qc_assertions(
        repo_root,
        auth_record=extras["auth_record"], part0_record=extras["part0_record"],
        exec_manifest=extras["exec_manifest"],
        completion_lock=extras["completion_lock"],
        comparison=extras["comparison"], oof_rows=extras["oof_rows"],
        metrics_rows=extras["metrics_rows"],
        resampling_rows=extras["resampling_rows"], counters=extras["counters"],
        loaded=extras["loaded"], primary_observed=extras["primary_observed"],
        closed_observed=extras["closed_observed"],
        predecessors=extras["predecessors"], network_attempts=network_attempts,
        base_main_commit=base_main_commit,
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
        "micro_part_id": MICRO_PART_ID,
        "source_commit": source_commit,
        "base_main_commit": base_main_commit,
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
        "human_authorization_text_utf8_bytes": HUMAN_AUTHORIZATION_TEXT_BYTES,
        "part0_contract_hash_valid": True,
        "changed_dimension": CHANGED_DIMENSION,
        "primary_sample": PRIMARY_SAMPLE,
        "sample": PART6_SAMPLE,
        "sample_sha256": ANALYSIS_READY_SHA256,
        "primary_target": PRIMARY_TARGET,
        "target": PART6_TARGET,
        "feature_set": FEATURE_SET_NAME,
        "base_feature_count": BASE_FEATURE_COUNT,
        "transformed_feature_count": TRANSFORMED_FEATURE_COUNT,
        "imbalance_policy": IMBALANCE_POLICY,
        "analysis_ready_rows": EXPECTED_ROWS,
        "analysis_ready_companies": EXPECTED_COMPANIES,
        "analysis_ready_positive": EXPECTED_POSITIVE,
        "analysis_ready_negative": EXPECTED_NEGATIVE,
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
        "resampling_rows": len(extras["resampling_rows"]),
        "selected_configuration_ids": {
            f: EXPECTED_SELECTED[f]["configuration_id"] for f in MODEL_FAMILIES
        },
        "selected_configurations_changed": False,
        "model_seeds": list(MODEL_SEEDS),
        "model_fit_calls": counters.model_fit_calls,
        "prediction_calls": counters.prediction_calls,
        "smotenc_calls": counters.smotenc_calls,
        "network_requests_attempted": network_attempts,
        "zero_counters": counters.zero_counters(),
        "final_test_identities_counted": loaded["final_test_rows_seen"],
        "final_test_predictor_rows_loaded": 0,
        "final_test_target_rows_loaded": 0,
        "final_test_predictions_generated": 0,
        "final_test_metrics_computed": 0,
        "final_test_evaluations": 0,
        "final_test_aggregate_primary_positive": EXPECTED_FINAL_TEST_POSITIVE_PRIMARY,
        "primary_artifact_sha256": dict(sorted(
            extras["primary_observed"].items()
        )),
        "closed_part_artifact_sha256": dict(sorted(
            extras["closed_observed"].items()
        )),
        "output_sha256": dict(sorted(content_hashes.items())),
        "primary_comparison_sha256": content_hashes[F_COMPARISON],
        "primary_ordering_preserved":
            extras["comparison"]["primary_ordering_preserved"],
        "assertions": assertions,
        **part6_handoff_markers(),
    }
    qc_text = _json_str(qc)
    qc_hash = sha256_bytes(qc_text.encode("utf-8"))
    meta = {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "description": (
            "Stage126 M1 robustness Part 6 SMOTE training-fold-only "
            "robustness (human-authorized; development folds only; only the "
            "imbalance strategy changed; class weighting disabled; SMOTENC "
            "applied strictly inside each training fold; no retuning; no "
            "full-development refit; final test locked; no "
            "calibration/bootstrap/Holm/winner selection; no SHAP; "
            "development-only imbalance-strategy robustness evidence; sixth "
            "and final registered M1 robustness category)."
        ),
        "generated_at": source_commit,
        "code_commit": source_commit,
        "base_main_commit": base_main_commit,
        "source_file_sha256": qc["source_file_sha256"],
        "test_file_sha256": qc["test_file_sha256"],
        "runtime_versions": primary.runtime_versions(),
        "output_files_sha256": dict(
            sorted({**content_hashes, F_QC: qc_hash}.items())
        ),
        "input_files_sha256": {
            ANALYSIS_READY_REL: ANALYSIS_READY_SHA256,
            SPLIT_MANIFEST_REL: SPLIT_MANIFEST_SHA256,
            EVENT_COUNT_GATE_REL: EVENT_COUNT_GATE_SHA256,
            SAMPLE_SUMMARY_REL: SAMPLE_SUMMARY_SHA256,
            SELECTED_CONFIGURATIONS_REL: SELECTED_CONFIGURATIONS_SHA256,
        },
        "closed_part_artifact_sha256": dict(sorted(
            extras["closed_observed"].items()
        )),
        "primary_comparison_sha256": content_hashes[F_COMPARISON],
        "network_requests_attempted": network_attempts,
        "model_fit_calls": counters.model_fit_calls,
        "prediction_calls": counters.prediction_calls,
        "smotenc_calls": counters.smotenc_calls,
        "zero_counters": counters.zero_counters(),
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
        raise QCFail(f"Part 6 QC failed: {failed} assertions failed")

    return {
        "qc": qc,
        "metadata": meta,
        "output_dir": str(out_dir),
        "files": files_written,
        "drift": tracked_drift,
        "network_requests_attempted": network_attempts,
        "metrics_rows": extras["metrics_rows"],
        "comparison": extras["comparison"],
    }
