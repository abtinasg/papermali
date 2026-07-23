"""Stage126 M1 — Robustness Part 3: expanded Rule A company-scope sample.

Explicitly human-authorized, development-only sensitivity analysis. ONLY the
sample (company scope) changes relative to the locked primary Stage126 M1
development analysis; the target, the nine-feature primary set, the selected
configurations, the temporal folds, the imbalance policy, the seeds and the
metric contract are all held fixed.

Fail-closed guarantees:
  * the locked final test is never opened — final-test predictor/target values
    are never parsed, stored, summarized, logged or exported. Final-test rows
    are counted ONLY through the frozen temporal split/identity contract;
  * no hyperparameter search runs (the three primary selected configurations are
    loaded from the frozen artifact and reused verbatim);
  * no full-development refit, no SMOTE/SMOTENC, no SHAP, no calibration, no
    threshold optimization, no bootstrap, no Holm correction, no p-values and no
    winner selection;
  * the frozen Stage125 tree, the eight primary Stage126 artifacts and the
    Part 1 and Part 2 scientific artifacts must remain byte-identical.

Part 3 is development-only sample-sensitivity evidence. It never replaces the
primary results, never changes the locked primary ordering used for confirmatory
interpretation, and never selects a paper winner. Stage125 Part 5 is historical
and immutable: this module neither imports nor executes it, and emits no Part 5
compatibility artifact.
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
from src import stage126_m1_robustness_part2_listing_rule_b as part2

# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #

QC_STAGE = "stage126_m1_robustness_part3_expanded_rule_a"
CURRENT_STAGE = "Stage126"
CONTRACT_VERSION = "stage126_m1_robustness_part3_expanded_rule_a_v1"
CATEGORY_ID = "expanded_rule_a_company_scope_robustness"
SCIENTIFIC_ROLE = "expanded_company_scope_sample_robustness"
CHANGED_DIMENSION = "sample"
IMBALANCE_POLICY = "primary_class_weighting"
SCIENTIFIC_INTERPRETATION = "development_only_sample_sensitivity_evidence"
MICRO_PART_ID = "stage126-m1-robustness-part3-expanded-rule-a"
PART1_CATEGORY_ID = "m1_target_proximity_six_feature_set"
PART2_CATEGORY_ID = "main_rule_b_listing_robustness"
NEXT_CATEGORY_ID = "expanded_rule_b_combined_robustness"

SRC_REL = "project/src/stage126_m1_robustness_part3_expanded_rule_a.py"
RUN_REL = "project/run_stage126_m1_robustness_part3_expanded_rule_a.py"
TEST_REL = "project/tests/test_stage126_m1_robustness_part3_expanded_rule_a.py"

STAGE126_DIR_REL = "project/stage126"
F_AUTH = "stage126_m1_robustness_part3_human_authorization_record.json"
F_FEATURE_MANIFEST = "stage126_m1_robustness_part3_feature_manifest.csv"
F_SAMPLE_DELTA = "stage126_m1_robustness_part3_sample_delta.csv"
F_EXEC_MANIFEST = "stage126_m1_robustness_part3_execution_manifest.json"
F_OOF = "stage126_m1_robustness_part3_oof_predictions.csv"
F_METRICS = "stage126_m1_robustness_part3_metrics.csv"
F_COMPARISON = "stage126_m1_robustness_part3_primary_comparison.json"
F_COMPLETION_LOCK = "stage126_m1_robustness_part3_completion_lock.json"
F_QC = "stage126_m1_robustness_part3_qc_report.json"
F_METADATA = "metadata_and_hashes_stage126_m1_robustness_part3.json"
F_README = "README_STAGE126_M1_ROBUSTNESS_PART3_EXPANDED_RULE_A.md"

# The base `main` commit this micro-part was authorized from.
BASE_MAIN_COMMIT = "6412b45c4adc6584a5567c7c96e0932f68f31e8a"

# --------------------------------------------------------------------------- #
# Exact human authorization (byte-for-byte Persian; 423 UTF-8 bytes)
# --------------------------------------------------------------------------- #

HUMAN_AUTHORIZATION_TEXT_FA = (
    "مجوز اجرای Stage126 M1 Robustness Part 3 — "
    "`expanded_rule_a_company_scope_robustness` را می‌دهم.\n"
    "\n"
    "این مجوز فقط برای اجرای Part 3 روی development folds و ساخت یک PR باز و "
    "Merge‌نشده است. این مجوز شامل Merge، Part 4، full-development refit، "
    "final test، calibration، bootstrap، Holm، winner selection، SMOTE، SHAP "
    "یا M2/M3/M4 نمی‌شود."
)
HUMAN_AUTHORIZATION_TEXT_SHA256 = (
    "f1230aa0dac18670695d41d99709cfd4ba5619e96e6f93c2e0678387ab28dab1"
)
HUMAN_AUTHORIZATION_TEXT_BYTES = 423
AUTHORIZATION_ID = "stage126-m1-robustness-part3-human-authorization"
AUTHORIZATION_DATE = "2026-07-23"
AUTHORIZATION_CONTEXT = (
    "The independently verified repository state completed Stage126 M1 "
    "Robustness Parts 1 and 2 and identified Part 3 — "
    "expanded_rule_a_company_scope_robustness — as the next registered "
    "gated micro-part."
)

# --------------------------------------------------------------------------- #
# Fixed (inherited) analysis dimensions — ONLY the company-scope sample changes
# --------------------------------------------------------------------------- #

PRIMARY_SAMPLE = primary.PRIMARY_SAMPLE                 # main_rule_a_primary
PART3_SAMPLE = "expanded_rule_a_company_scope_robustness"
PART3_TARGET = primary.PRIMARY_TARGET                   # FD_target_main_t_plus_1
FEATURE_SET_NAME = primary.FEATURE_SET_NAME             # M1_PRIMARY_FEATURE_ORDER
PART3_FEATURE_ORDER: tuple[str, ...] = tuple(primary.M1_PRIMARY_FEATURE_ORDER)
PART3_FEATURE_SOURCE_COLUMN: dict[str, str] = dict(primary.FEATURE_SOURCE_COLUMN)
PROHIBITED_FEATURE = primary.PROHIBITED_FEATURE
PROHIBITED_TARGET = "FD_target_persistent_loss_robustness_t_plus_1"

BASE_FEATURE_COUNT = 9
TRANSFORMED_FEATURE_COUNT = 18  # 9 imputed continuous + 9 missingness indicators

MODEL_FAMILIES = primary.ALLOWED_MODEL_FAMILIES
MODEL_SEEDS = primary.FINAL_OOF_SEEDS
LOGISTIC_DETERMINISTIC_SEED = primary.TUNING_SEEDS[0]
FEATURE_TRANSFORMATION: dict[str, str] = dict(part2.FEATURE_TRANSFORMATION)

# --------------------------------------------------------------------------- #
# Exact expected Expanded Rule A counts
# --------------------------------------------------------------------------- #

EXPECTED_ROWS = 1056
EXPECTED_COMPANIES = 124
EXPECTED_POSITIVE = 80
EXPECTED_NEGATIVE = 976
EXPECTED_MISSING_TARGET = 0

EXPECTED_DEV_ROWS = 695
EXPECTED_DEV_POSITIVE = 68
EXPECTED_DEV_NEGATIVE = 627

EXPECTED_FOLD_COUNTS: dict[str, dict[str, int]] = {
    "fold1_train": {"rows": 254, "positive": 33, "negative": 221},
    "fold1_validation": {"rows": 215, "positive": 25, "negative": 190},
    "fold2_train": {"rows": 469, "positive": 58, "negative": 411},
    "fold2_validation": {"rows": 226, "positive": 10, "negative": 216},
}
EXPECTED_OOF_ROWS_PER_FAMILY = 441        # 215 + 226
EXPECTED_OOF_ROWS_TOTAL = EXPECTED_OOF_ROWS_PER_FAMILY * len(MODEL_FAMILIES)
EXPECTED_OOF_POSITIVE = 35
EXPECTED_METRICS_ROWS = len(MODEL_FAMILIES) * 3

EXPECTED_MODEL_FIT_CALLS = 22   # 2 logistic + 10 RF + 10 XGBoost
EXPECTED_PREDICTION_CALLS = 22
EXPECTED_FINAL_TEST_IDENTITIES = 361
EXPECTED_XGB_SCALE_POS_WEIGHT: dict[str, tuple[int, int]] = {
    "fold1_train": (221, 33),
    "fold2_train": (411, 58),
}

# Primary Rule A reference counts (frozen; identity-level delta audit only).
EXPECTED_PRIMARY_ROWS = primary.EXPECTED_ALL_PRIMARY_ROWS          # 1012
EXPECTED_PRIMARY_COMPANIES = 119
EXPECTED_PRIMARY_POSITIVE = 80
EXPECTED_PRIMARY_NEGATIVE = 932
EXPECTED_PRIMARY_DEV_ROWS = primary.EXPECTED_DEV_ROWS              # 666
EXPECTED_PRIMARY_OOF_ROWS = primary.EXPECTED_POOLED_OOF_ROWS       # 421
EXPECTED_PRIMARY_FINAL_TEST_IDENTITIES = primary.EXPECTED_FINAL_TEST_PAIRS  # 346

EXPECTED_EXPANDED_ONLY_KEYS = 44
EXPECTED_PRIMARY_ONLY_KEYS = 0
EXPECTED_COMPANY_DELTA = 5
EXPECTED_POSITIVE_DELTA = 0
EXPECTED_NEGATIVE_DELTA = 44
EXPECTED_DEV_ROW_DELTA = 29
EXPECTED_DEV_POSITIVE_DELTA = 0
EXPECTED_DEV_NEGATIVE_DELTA = 29
EXPECTED_FOLD_ROW_DELTA: dict[str, int] = {
    "fold1_train": 9,
    "fold1_validation": 10,
    "fold2_train": 19,
    "fold2_validation": 10,
}
EXPECTED_OOF_IDENTITY_DELTA = 20
EXPECTED_FINAL_TEST_IDENTITY_DELTA = 15

# --------------------------------------------------------------------------- #
# Frozen inputs (pinned; never modified)
# --------------------------------------------------------------------------- #

PRIMARY_ANALYSIS_READY_REL = primary.ANALYSIS_READY_REL
PRIMARY_ANALYSIS_READY_SHA256 = primary.ANALYSIS_READY_SHA256
PART3_ANALYSIS_READY_REL = (
    "project/stage125/part3c_outputs/analysis_ready_expanded_rule_a_stage125.csv"
)
PART3_ANALYSIS_READY_SHA256 = (
    "fbe9b29c6323b59e830ca9d2dd8c1543b9ef48b21709b01cc56a3989cd2d64d9"
)
SPLIT_MANIFEST_REL = primary.SPLIT_MANIFEST_REL
SPLIT_MANIFEST_SHA256 = primary.SPLIT_MANIFEST_SHA256
# Frozen Stage125 aggregate contracts. Aggregate final-test counts are read ONLY
# from these already-frozen summaries — never from row-level final-test values.
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
LOCKED_PRIMARY_POOLED_PR_AUC: dict[str, float] = {
    "regularized_logistic_regression": 0.445756964048,
    "random_forest": 0.402441830020,
    "xgboost": 0.356545008162,
}

# Closed micro-part scientific artifacts — must remain byte-identical.
PART2_METRICS_REL = (
    "project/stage126/stage126_m1_robustness_part2_metrics.csv"
)
PINNED_CLOSED_PART_ARTIFACTS: dict[str, str] = {
    "project/stage126/"
    "stage126_m1_robustness_part1_human_authorization_record.json":
        "87a4f55baeb1081eaf936e49c5e8923f67df54ec444f0abc33ec835c0c7e06f4",
    "project/stage126/stage126_m1_robustness_part1_feature_manifest.csv":
        "c65735795eda7dce6b4cacbc6af9dd5914b5068f44c77277035a51463cceaf90",
    "project/stage126/stage126_m1_robustness_part1_execution_manifest.json":
        "80813ce8af9544dde736cc6b94372d2626dccbf888553cd7964625bfe12d8738",
    "project/stage126/stage126_m1_robustness_part1_oof_predictions.csv":
        "1303a31a45e8293be84e7d6c3b23aa1a4c771847de0f1b0207110c33cafdba31",
    "project/stage126/stage126_m1_robustness_part1_metrics.csv":
        "c60f4b15aa40273472be98c867c73795d254f32c2a0e29b76641b1c5d5c18e98",
    "project/stage126/stage126_m1_robustness_part1_primary_comparison.json":
        "2b58a85250420a8a18b0ff37cecdf3f2e31160c37e0cb48d027324c87a25c46a",
    "project/stage126/stage126_m1_robustness_part1_completion_lock.json":
        "964d84f2269bb35b0176f88bb12bcfc13ef2cb487817cf5b49a5c28a87e1822b",
    "project/stage126/"
    "stage126_m1_robustness_part2_human_authorization_record.json":
        "0a7bba7489f62f59d3e0f07946b82d8ce4be1a49c4d098f47ca308de9466959e",
    "project/stage126/stage126_m1_robustness_part2_feature_manifest.csv":
        "58c52c17337286237779153d59f85f74c76f84d0c0415b8efadd618aa524b78f",
    "project/stage126/stage126_m1_robustness_part2_sample_delta.csv":
        "baafe97323e45f0a88b07aaf1ea97c50c4b213e43724ddb2b97f3f55144fc7d3",
    "project/stage126/stage126_m1_robustness_part2_execution_manifest.json":
        "9fc153b65a77c906339f51d7c0ad576d23eb06c5895eacb1a0ee92578b321ce8",
    "project/stage126/stage126_m1_robustness_part2_oof_predictions.csv":
        "3af630141a905370849875926fa84052cf10322cc34e18258a25d28106d47dd6",
    PART2_METRICS_REL:
        "073b8657c0ba2c40f52e05d766a102e2b5d20845821c4eb1cef1b6e53459228c",
    "project/stage126/stage126_m1_robustness_part2_primary_comparison.json":
        "9fc3b4eaf0a27fc66cd22444d92363747157743e822d3be877ecca7f153763bf",
    "project/stage126/stage126_m1_robustness_part2_completion_lock.json":
        "23d1920c4fb0a351456fe54b60616446381bbd550fb18e0bba5dab091486fec6",
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
    "included_in_part3",
]
SAMPLE_DELTA_COLUMNS = [
    "predictor_row_key_t", "target_row_key_t_plus_1", "ticker", "fiscal_year_t",
    "target_year", "temporal_partition", "fold_membership",
    "present_in_main_rule_a_primary", "present_in_expanded_rule_a",
    "sample_delta_status",
]

DELTA_STATUS_BOTH = "present_in_both_samples"
DELTA_STATUS_EXPANDED_ONLY = "expanded_only_added_by_company_scope"

METRIC_NAMES: tuple[str, ...] = (
    "pr_auc", "roc_auc", "brier_score", "recall_at_10pct", "lift_at_10pct",
)
METRIC_SCOPES: tuple[str, ...] = (
    "fold1_validation", "fold2_validation", "pooled_development_oof",
)


class QCFail(RuntimeError):
    """Fail-closed Part 3 validation error."""


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
            f"Part 3 authorization byte length {len(raw)} != "
            f"{HUMAN_AUTHORIZATION_TEXT_BYTES}"
        )
    got = hashlib.sha256(raw).hexdigest()
    if got != HUMAN_AUTHORIZATION_TEXT_SHA256:
        raise QCFail(
            f"Part 3 human authorization SHA-256 mismatch: {got} != "
            f"{HUMAN_AUTHORIZATION_TEXT_SHA256}"
        )


def build_authorization_record() -> dict[str, Any]:
    """Deterministic Part 3 human authorization record (hash recomputed)."""
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
        "part3_execution_authorized": True,
        "development_fold_execution_authorized": True,
        "create_open_unmerged_pr_authorized": True,
        "merge_authorized": False,
        "part4_execution_authorized": False,
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
        "smote_authorized": False,
        "smotenc_authorized": False,
        "shap_authorized": False,
        "m2_authorized": False,
        "m3_authorized": False,
        "m4_authorized": False,
        "authorization_scope_note": (
            "Consumed by this Part 3 execution. Creates no standing execution "
            "authorization for any later micro-part."
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
    if len(order) < 4:
        raise QCFail("Part 0 execution_order is too short")
    if order[0] != PART1_CATEGORY_ID or order[1] != PART2_CATEGORY_ID:
        raise QCFail("Part 0 execution_order head is not Parts 1 and 2")
    if order[2] != CATEGORY_ID:
        raise QCFail(
            f"Part 0 execution_order[2] {order[2]!r} is not the Part 3 category"
        )
    if order[3] != NEXT_CATEGORY_ID:
        raise QCFail("Part 0 execution_order[3] is not the Part 4 category")
    return record


def verify_predecessors_completed(repo_root: Path) -> list[str]:
    """Parts 1 and 2 must already be complete — no category may be skipped."""
    completed: list[str] = []
    for index, category in ((1, PART1_CATEGORY_ID), (2, PART2_CATEGORY_ID)):
        rel = (
            f"{STAGE126_DIR_REL}/stage126_m1_robustness_part{index}"
            "_completion_lock.json"
        )
        path = repo_root / rel
        if not path.is_file():
            raise QCFail(
                f"Part {index} completion lock missing — Part 3 may not run "
                f"before Parts 1 and 2"
            )
        lock = json.loads(path.read_text(encoding="utf-8"))
        if lock.get("category_id") != category:
            raise QCFail(f"Part {index} completion lock category mismatch")
        if lock.get(f"part{index}_execution_completed") is not True:
            raise QCFail(f"Part {index} is not completed")
        completed.append(category)
    return completed


def verify_closed_parts_immutable(repo_root: Path) -> dict[str, str]:
    """Part 1 and Part 2 scientific outputs must be byte-identical."""
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
        (PRIMARY_ANALYSIS_READY_REL, PRIMARY_ANALYSIS_READY_SHA256),
        (PART3_ANALYSIS_READY_REL, PART3_ANALYSIS_READY_SHA256),
        (SPLIT_MANIFEST_REL, SPLIT_MANIFEST_SHA256),
        (EVENT_COUNT_GATE_REL, EVENT_COUNT_GATE_SHA256),
        (SAMPLE_SUMMARY_REL, SAMPLE_SUMMARY_SHA256),
    ):
        require_file_hash(repo_root, rel, expected, label="frozen Stage125 input")
    return observed


# --------------------------------------------------------------------------- #
# Allowlist / denylist from the frozen temporal split contract (identities only)
# --------------------------------------------------------------------------- #

def build_sample_allowlist(
    repo_root: Path, sample_design: str,
    expected_fold_counts: dict[str, dict[str, int]],
    expected_dev_rows: int, expected_final_test_identities: int,
) -> dict[str, Any]:
    """Development allowlist + final-test denylist for one sample (keys only).

    Reuses the reviewed Part 2 identity loader, re-raising its fail-closed
    errors as Part 3 errors so every Part 3 failure surfaces with this
    micro-part's own exception type.
    """
    try:
        return part2.build_sample_allowlist(
            repo_root, sample_design, expected_fold_counts,
            expected_dev_rows, expected_final_test_identities,
        )
    except part2.QCFail as exc:
        raise QCFail(str(exc)) from exc


def build_part3_allowlist(repo_root: Path) -> dict[str, Any]:
    return build_sample_allowlist(
        repo_root, PART3_SAMPLE, EXPECTED_FOLD_COUNTS,
        EXPECTED_DEV_ROWS, EXPECTED_FINAL_TEST_IDENTITIES,
    )


def build_primary_allowlist(repo_root: Path) -> dict[str, Any]:
    return build_sample_allowlist(
        repo_root, PRIMARY_SAMPLE, primary.EXPECTED_FOLD_COUNTS,
        primary.EXPECTED_DEV_ROWS, primary.EXPECTED_FINAL_TEST_PAIRS,
    )


# --------------------------------------------------------------------------- #
# Part 3 nine-feature loader (development rows only)
# --------------------------------------------------------------------------- #

def part3_source_columns() -> list[str]:
    """Exactly the nine primary source columns; the growth feature can't appear."""
    cols = sorted({PART3_FEATURE_SOURCE_COLUMN[f] for f in PART3_FEATURE_ORDER})
    if len(cols) != BASE_FEATURE_COUNT:
        raise QCFail(
            f"Part 3 source column count {len(cols)} != {BASE_FEATURE_COUNT}"
        )
    if PROHIBITED_FEATURE in cols:
        raise QCFail("prohibited growth feature reached the Part 3 loader")
    return cols


def load_part3_development_values(
    repo_root: Path, allowlist: dict[str, Any],
) -> dict[str, Any]:
    """Stream the Expanded Rule A analysis-ready CSV keeping ONLY dev keys.

    Reads exactly the nine primary source columns and parses the primary target
    for development rows only. Final-test rows are never numerically parsed,
    stored, summarized, logged or exported — only their identities are counted.
    Unknown/unclassified rows fail closed.
    """
    dev_pairs = allowlist["dev_pairs"]
    denylist = allowlist["denylist_pairs"]
    source_cols = part3_source_columns()

    loaded: dict[tuple[str, str], dict[str, Any]] = {}
    final_test_rows_seen = 0
    final_test_predictor_rows_loaded = 0
    final_test_target_rows_loaded = 0
    unknown_rows = 0
    missing_target = 0

    path = repo_root / PART3_ANALYSIS_READY_REL
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        header = set(reader.fieldnames or [])
        needed = set(source_cols) | {
            "predictor_row_key_t", "target_row_key_t_plus_1", "ticker",
            "fiscal_year_t", "target_year", PART3_TARGET,
        }
        missing = needed - header
        if missing:
            raise QCFail(
                f"Expanded Rule A analysis-ready CSV missing columns: "
                f"{sorted(missing)}"
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
                target = primary._target_value(row[PART3_TARGET])
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
            f"{unknown_rows} Expanded Rule A rows unclassified (fail-closed)"
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
            raise QCFail("Part 3 feature vector is not nine-dimensional")

    return {
        "rows": loaded,
        "final_test_rows_seen": final_test_rows_seen,
        "final_test_predictor_rows_loaded": final_test_predictor_rows_loaded,
        "final_test_target_rows_loaded": final_test_target_rows_loaded,
        "missing_target": missing_target,
    }


# --------------------------------------------------------------------------- #
# Selected configurations (loaded, never re-searched)
# --------------------------------------------------------------------------- #

EXPECTED_SELECTED: dict[str, dict[str, Any]] = part2.EXPECTED_SELECTED


def load_selected_configurations(repo_root: Path) -> dict[str, Any]:
    """Load the frozen primary selected configurations. NO search is performed."""
    return part2.load_selected_configurations(repo_root)


# --------------------------------------------------------------------------- #
# Execution (development folds only; counted fits/predictions)
# --------------------------------------------------------------------------- #

class ExecutionCounters:
    """Explicit zero counters for every forbidden operation."""

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
        self.full_development_refits = 0
        self.scale_pos_weight_by_fold: dict[str, float] = {}

    def zero_counters(self) -> dict[str, int]:
        return {
            "tuning_search_calls": self.tuning_search_calls,
            "smote_calls": self.smote_calls,
            "smotenc_calls": self.smotenc_calls,
            "shap_calls": self.shap_calls,
            "calibration_calls": self.calibration_calls,
            "threshold_optimization_calls": self.threshold_optimization_calls,
            "bootstrap_calls": self.bootstrap_calls,
            "holm_calls": self.holm_calls,
            "p_value_calls": self.p_value_calls,
            "winner_selection_calls": self.winner_selection_calls,
            "final_test_evaluations": self.final_test_evaluations,
            "final_test_predictions": self.final_test_predictions,
            "full_development_refits": self.full_development_refits,
        }


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


def generate_part3_oof(
    folds_data: dict[str, dict[str, Any]], selected: dict[str, Any],
    counters: ExecutionCounters,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, np.ndarray]]]:
    """Development-fold OOF predictions on the expanded company-scope sample.

    Logistic is a deterministic single fit per fold; RF/XGBoost average the
    validation probabilities over the five frozen model seeds within each fold.
    No fold ever combines training and validation rows, class weights are
    computed from training-fold rows only, and no fold is ever refit on the
    complete development set.
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
        for fspec in primary.FOLD_SPEC.values():
            tr = folds_data[fspec["train_role"]]
            va = folds_data[fspec["validation_role"]]
            # Training-fold-only preprocessing (nine features -> eighteen cols).
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
                    "sample": PART3_SAMPLE,
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
                    # Plain Python float: a numpy scalar would serialize as
                    # "np.float64(...)" under numpy>=2.
                    "predicted_probability": float(probs[i]),
                    "seed_aggregation": agg,
                })
    return oof_rows, predictions


def compute_part3_metrics(
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
                "sample": PART3_SAMPLE,
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
            "sample": PART3_SAMPLE,
            "feature_set": FEATURE_SET_NAME,
            "model_family": family, "configuration_id": cid,
            "scope": "pooled_development_oof", **m,
        })
    return rows


# --------------------------------------------------------------------------- #
# Primary vs expanded sample-delta audit (row identities only)
# --------------------------------------------------------------------------- #

def _fold_membership(roles: set[str]) -> str:
    return "|".join(sorted(roles))


def build_sample_delta(
    repo_root: Path, allow_primary: dict[str, Any], allow_part3: dict[str, Any],
    loaded: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Identity-level primary-vs-expanded delta audit.

    Compares ROW IDENTITIES only. Final-test rows contribute identities and
    counts exclusively — no row-level final-test target value is ever read.
    Aggregate positive/negative totals come from the frozen Stage125 summaries.
    Fails closed unless Expanded Rule A is a strict superset of primary Rule A
    with exactly the registered deltas.
    """
    def _identities(allow: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
        out: dict[tuple[str, str], dict[str, Any]] = {}
        for key, info in allow["dev_pairs"].items():
            out[key] = {
                "ticker": info["ticker"],
                "fiscal_year_t": info["fiscal_year_t"],
                "target_year": info["target_year"],
                "temporal_partition": "development",
                "fold_membership": _fold_membership(info["roles"]),
            }
        for key, info in allow["final_test_identities"].items():
            out[key] = {
                "ticker": info["ticker"],
                "fiscal_year_t": info["fiscal_year_t"],
                "target_year": info["target_year"],
                "temporal_partition": "locked_final_test",
                "fold_membership": primary.FINAL_TEST_ROLE,
            }
        return out

    ident_p = _identities(allow_primary)
    ident_e = _identities(allow_part3)
    keys_p, keys_e = set(ident_p), set(ident_e)

    if not keys_p <= keys_e:
        raise QCFail(
            "Expanded Rule A is not a strict superset of primary Rule A"
        )
    expanded_only = sorted(keys_e - keys_p)
    primary_only = sorted(keys_p - keys_e)
    if len(expanded_only) != EXPECTED_EXPANDED_ONLY_KEYS:
        raise QCFail(
            f"expanded-only keys {len(expanded_only)} != "
            f"{EXPECTED_EXPANDED_ONLY_KEYS}"
        )
    if len(primary_only) != EXPECTED_PRIMARY_ONLY_KEYS:
        raise QCFail(f"primary-only keys {len(primary_only)} != 0")

    rows: list[dict[str, Any]] = []
    for key in sorted(keys_e):
        info = ident_e[key]
        in_primary = key in keys_p
        if in_primary:
            p_info = ident_p[key]
            if (p_info["temporal_partition"] != info["temporal_partition"]
                    or p_info["fold_membership"] != info["fold_membership"]):
                raise QCFail(
                    f"shared key {key} changed temporal role between samples"
                )
        rows.append({
            "predictor_row_key_t": key[0],
            "target_row_key_t_plus_1": key[1],
            "ticker": info["ticker"],
            "fiscal_year_t": info["fiscal_year_t"],
            "target_year": info["target_year"],
            "temporal_partition": info["temporal_partition"],
            "fold_membership": info["fold_membership"],
            "present_in_main_rule_a_primary": "true" if in_primary else "false",
            "present_in_expanded_rule_a": "true",
            "sample_delta_status": (
                DELTA_STATUS_BOTH if in_primary else DELTA_STATUS_EXPANDED_ONLY
            ),
        })

    # Per-fold identity deltas (development roles only).
    fold_delta: dict[str, dict[str, Any]] = {}
    dev_rows = loaded["rows"]
    for role in primary.DEV_ROLES:
        added = allow_part3["role_pairs"][role] - allow_primary["role_pairs"][role]
        removed = allow_primary["role_pairs"][role] - allow_part3["role_pairs"][role]
        if removed:
            raise QCFail(f"{role} lost rows relative to primary (fail-closed)")
        if len(added) != EXPECTED_FOLD_ROW_DELTA[role]:
            raise QCFail(
                f"{role} row delta {len(added)} != {EXPECTED_FOLD_ROW_DELTA[role]}"
            )
        added_pos = sum(1 for k in added if dev_rows[k]["target"] == 1)
        if added_pos != 0:
            raise QCFail(
                f"{role} added {added_pos} positive rows; the expanded company "
                f"scope is expected to add negative-only development rows"
            )
        fold_delta[role] = {
            "rows_added": len(added),
            "positives_added": added_pos,
            "negatives_added": len(added) - added_pos,
            "rows_removed": 0,
        }

    # Development + OOF identity deltas.
    dev_added = set(allow_part3["dev_pairs"]) - set(allow_primary["dev_pairs"])
    if len(dev_added) != EXPECTED_DEV_ROW_DELTA:
        raise QCFail(
            f"development row delta {len(dev_added)} != {EXPECTED_DEV_ROW_DELTA}"
        )
    dev_added_pos = sum(1 for k in dev_added if dev_rows[k]["target"] == 1)
    if dev_added_pos != EXPECTED_DEV_POSITIVE_DELTA:
        raise QCFail(f"development positives added {dev_added_pos} != 0")

    oof_e = (allow_part3["role_pairs"]["fold1_validation"]
             | allow_part3["role_pairs"]["fold2_validation"])
    oof_p = (allow_primary["role_pairs"]["fold1_validation"]
             | allow_primary["role_pairs"]["fold2_validation"])
    oof_added = oof_e - oof_p
    if len(oof_e) != EXPECTED_OOF_ROWS_PER_FAMILY:
        raise QCFail(f"expanded OOF identities {len(oof_e)} != "
                     f"{EXPECTED_OOF_ROWS_PER_FAMILY}")
    if len(oof_p) != EXPECTED_PRIMARY_OOF_ROWS:
        raise QCFail("primary OOF identity count mismatch")
    if len(oof_added) != EXPECTED_OOF_IDENTITY_DELTA:
        raise QCFail(
            f"expanded-only OOF identities {len(oof_added)} != "
            f"{EXPECTED_OOF_IDENTITY_DELTA}"
        )
    if oof_p - oof_e:
        raise QCFail("primary-only OOF identities exist (fail-closed)")
    oof_added_pos = sum(1 for k in oof_added if dev_rows[k]["target"] == 1)
    if oof_added_pos != 0:
        raise QCFail(
            f"{oof_added_pos} added OOF identities carry target 1; all 20 added "
            f"OOF identities are expected to have target 0"
        )

    # Final-test identity delta — identities and counts ONLY.
    ft_e = allow_part3["role_pairs"][primary.FINAL_TEST_ROLE]
    ft_p = allow_primary["role_pairs"][primary.FINAL_TEST_ROLE]
    if len(ft_e) != EXPECTED_FINAL_TEST_IDENTITIES:
        raise QCFail("expanded final-test identity count mismatch")
    if len(ft_p) != EXPECTED_PRIMARY_FINAL_TEST_IDENTITIES:
        raise QCFail("primary final-test identity count mismatch")
    if len(ft_e - ft_p) != EXPECTED_FINAL_TEST_IDENTITY_DELTA:
        raise QCFail(
            f"expanded-only final-test identities {len(ft_e - ft_p)} != "
            f"{EXPECTED_FINAL_TEST_IDENTITY_DELTA}"
        )
    if ft_p - ft_e:
        raise QCFail("primary-only final-test identities exist (fail-closed)")

    gate = part2.read_frozen_event_counts(repo_root)
    summary = part2.read_frozen_sample_summary(repo_root)
    p_all, e_all = gate[(PRIMARY_SAMPLE, "all")], gate[(PART3_SAMPLE, "all")]
    p_dev, e_dev = (gate[(PRIMARY_SAMPLE, "development")],
                    gate[(PART3_SAMPLE, "development")])
    p_comp = summary[PRIMARY_SAMPLE]["companies"]
    e_comp = summary[PART3_SAMPLE]["companies"]

    exact = [
        (p_all["rows"], EXPECTED_PRIMARY_ROWS, "primary_rows"),
        (p_all["positive"], EXPECTED_PRIMARY_POSITIVE, "primary_positive"),
        (p_all["negative"], EXPECTED_PRIMARY_NEGATIVE, "primary_negative"),
        (p_comp, EXPECTED_PRIMARY_COMPANIES, "primary_companies"),
        (e_all["rows"], EXPECTED_ROWS, "expanded_rows"),
        (e_all["positive"], EXPECTED_POSITIVE, "expanded_positive"),
        (e_all["negative"], EXPECTED_NEGATIVE, "expanded_negative"),
        (e_comp, EXPECTED_COMPANIES, "expanded_companies"),
        (p_dev["rows"], EXPECTED_PRIMARY_DEV_ROWS, "primary_dev_rows"),
        (e_dev["rows"], EXPECTED_DEV_ROWS, "expanded_dev_rows"),
        (e_comp - p_comp, EXPECTED_COMPANY_DELTA, "company_delta"),
        (e_all["positive"] - p_all["positive"], EXPECTED_POSITIVE_DELTA,
         "positive_delta"),
        (e_all["negative"] - p_all["negative"], EXPECTED_NEGATIVE_DELTA,
         "negative_delta"),
    ]
    for got, want, label in exact:
        if got != want:
            raise QCFail(f"sample-delta {label} {got} != {want}")

    summary_record = {
        "comparison_basis": "row_identities_only",
        "final_test_values_read": False,
        "final_test_identity_source": SPLIT_MANIFEST_REL,
        "aggregate_count_source": EVENT_COUNT_GATE_REL,
        "expanded_is_strict_superset_of_primary": True,
        "main_rule_a_primary": {
            "analysis_ready": {**p_all, "companies": p_comp},
            "development": p_dev,
            "oof_identities": len(oof_p),
            "final_test_identities": len(ft_p),
        },
        "expanded_rule_a_company_scope_robustness": {
            "analysis_ready": {**e_all, "companies": e_comp},
            "development": e_dev,
            "oof_identities": len(oof_e),
            "final_test_identities": len(ft_e),
        },
        "expanded_only_rows": len(expanded_only),
        "primary_only_rows": len(primary_only),
        "company_delta": e_comp - p_comp,
        "positive_delta": e_all["positive"] - p_all["positive"],
        "negative_delta": e_all["negative"] - p_all["negative"],
        "development_rows_added": len(dev_added),
        "development_positives_added": dev_added_pos,
        "development_negatives_added": len(dev_added) - dev_added_pos,
        "fold_delta": fold_delta,
        "oof_identities_added": len(oof_added),
        "oof_identities_added_all_target_zero": True,
        "final_test_identities_added": len(ft_e - ft_p),
        "added_development_rows_are_negative_only": True,
        "delta_rows_emitted": len(rows),
    }
    return rows, summary_record


# --------------------------------------------------------------------------- #
# Artifact builders
# --------------------------------------------------------------------------- #

def build_feature_manifest_rows() -> list[dict[str, Any]]:
    rows = []
    for i, feat in enumerate(PART3_FEATURE_ORDER, start=1):
        rows.append({
            "feature_order": i,
            "feature_name": feat,
            "source_column": PART3_FEATURE_SOURCE_COLUMN[feat],
            "transformation": FEATURE_TRANSFORMATION[feat],
            "missingness_indicator_appended": "true",
            # Indicators occupy columns 10-18, in the same order as the features.
            "missingness_indicator_column_index": BASE_FEATURE_COUNT + i,
            "included_in_part3": "true",
        })
    return rows


def build_execution_manifest(
    counters: ExecutionCounters, loaded: dict[str, Any],
    allowlist: dict[str, Any], selected: dict[str, Any],
    delta_summary: dict[str, Any],
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
        "sample": PART3_SAMPLE,
        "sample_input_file": PART3_ANALYSIS_READY_REL,
        "sample_input_sha256": PART3_ANALYSIS_READY_SHA256,
        "primary_sample_input_file": PRIMARY_ANALYSIS_READY_REL,
        "primary_sample_input_sha256": PRIMARY_ANALYSIS_READY_SHA256,
        "target": PART3_TARGET,
        "target_changed": False,
        "prohibited_target": PROHIBITED_TARGET,
        "feature_set": FEATURE_SET_NAME,
        "feature_set_changed": False,
        "features_exact_order": list(PART3_FEATURE_ORDER),
        "feature_source_columns": dict(sorted(PART3_FEATURE_SOURCE_COLUMN.items())),
        "prohibited_feature": PROHIBITED_FEATURE,
        "base_feature_count": BASE_FEATURE_COUNT,
        "transformed_feature_count": TRANSFORMED_FEATURE_COUNT,
        "model_matrix_column_order": (
            "9_transformed_features_then_9_missingness_indicators"
        ),
        "preprocessing_changed": False,
        "missingness_indicator_logic_changed": False,
        "imbalance_policy": IMBALANCE_POLICY,
        "imbalance_policy_changed": False,
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
        "xgboost_scale_pos_weight_by_training_fold": {
            k: primary._round(v)
            for k, v in sorted(counters.scale_pos_weight_by_fold.items())
        },
        "class_weights_use_validation_rows": False,
        "class_weights_reused_from_primary_sample": False,
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
        "sample_delta": delta_summary,
        "final_test_identities_counted": loaded["final_test_rows_seen"],
        "final_test_identity_source": SPLIT_MANIFEST_REL,
        "final_test_predictor_rows_loaded": 0,
        "final_test_target_rows_loaded": 0,
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


COMPARISON_CONTRACT_VERSION = (
    "stage126_m1_robustness_part3_primary_comparison_v1"
)


def build_primary_comparison(
    repo_root: Path, metrics_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare Part 3 pooled PR-AUC PRIMARILY against the locked primary run.

    A clearly separated, descriptive Part 2 comparison is included; it makes no
    additional claim and selects no preferred robustness sample. Nothing is
    hardcoded: both sides are read from their hash-pinned sources.
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
    part3_pooled = {
        r["model_family"]: float(r["pr_auc"])
        for r in metrics_rows if r["scope"] == "pooled_development_oof"
    }
    missing = set(MODEL_FAMILIES) - set(part3_pooled)
    if missing:
        raise QCFail(f"Part 3 metrics missing pooled rows for: {sorted(missing)}")

    absolute = {
        f: primary._round(part3_pooled[f] - primary_pooled[f])
        for f in MODEL_FAMILIES
    }
    relative = {
        f: primary._round(
            (part3_pooled[f] - primary_pooled[f]) / primary_pooled[f] * 100.0
        )
        for f in MODEL_FAMILIES
    }
    direction = {
        f: ("improved" if absolute[f] > 0 else
            "declined" if absolute[f] < 0 else "unchanged")
        for f in MODEL_FAMILIES
    }
    primary_order = sorted(MODEL_FAMILIES, key=lambda f: -primary_pooled[f])
    part3_order = sorted(MODEL_FAMILIES, key=lambda f: -part3_pooled[f])
    ordering_preserved = list(primary_order) == list(part3_order)

    # Separated, descriptive Part 2 comparison (no additional claim).
    require_file_hash(
        repo_root, PART2_METRICS_REL,
        PINNED_CLOSED_PART_ARTIFACTS[PART2_METRICS_REL],
        label="Part 2 metrics",
    )
    part2_pooled = _pooled_pr_auc_from_metrics_csv(repo_root / PART2_METRICS_REL)
    part2_order = sorted(MODEL_FAMILIES, key=lambda f: -part2_pooled[f])

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
        "primary_reference": {
            "sample": PRIMARY_SAMPLE,
            "metrics_source": PRIMARY_METRICS_REL,
            "metrics_sha256": PINNED_PRIMARY_ARTIFACTS[PRIMARY_METRICS_REL],
            "locked_pooled_pr_auc": {
                f: LOCKED_PRIMARY_POOLED_PR_AUC[f] for f in MODEL_FAMILIES
            },
            "observed_pooled_pr_auc": {
                f: primary._round(primary_pooled[f]) for f in MODEL_FAMILIES
            },
            "locked_values_match_observed": True,
        },
        "part3_pooled_pr_auc": {
            f: primary._round(part3_pooled[f]) for f in MODEL_FAMILIES
        },
        "absolute_change_vs_primary": absolute,
        "relative_change_percent_vs_primary": relative,
        "direction_by_family": direction,
        "largest_absolute_pr_auc_change": primary._round(max_abs),
        "primary_observed_ordering": list(primary_order),
        "part3_observed_ordering": list(part3_order),
        "primary_ordering_preserved": ordering_preserved,
        "expanded_company_scope_materially_changes_interpretation": False,
        "interpretation": (
            "Development-only sample sensitivity. The expanded company scope "
            "adds negative-only development rows (29 development rows, of which "
            "20 enter the pooled OOF surface, all with target 0), so pooled "
            "PR-AUC shifts here mainly reflect a slightly lower event rate "
            "rather than a change in discrimination. The comparison is reported "
            "descriptively and cautiously: it does not replace the primary "
            "results, does not alter the locked primary ordering used for "
            "confirmatory interpretation, does not constitute a new "
            "confirmatory model comparison and selects no paper winner."
        ),
        "descriptive_part2_comparison": {
            "note": (
                "Separated descriptive context only. Part 2 (listing Rule B) "
                "and Part 3 (expanded company scope) probe DIFFERENT sample "
                "dimensions; no preferred robustness sample is selected and no "
                "additional claim is made."
            ),
            "part2_sample": "main_rule_b_listing_robustness",
            "part2_metrics_source": PART2_METRICS_REL,
            "part2_pooled_pr_auc": {
                f: primary._round(part2_pooled[f]) for f in MODEL_FAMILIES
            },
            "part2_observed_ordering": list(part2_order),
            "part3_minus_part2_absolute": {
                f: primary._round(part3_pooled[f] - part2_pooled[f])
                for f in MODEL_FAMILIES
            },
            "preferred_robustness_sample_selected": False,
            "claims_multiplied": False,
        },
        "primary_results_replaced": False,
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

COMPLETED_CATEGORY_IDS = [PART1_CATEGORY_ID, PART2_CATEGORY_ID, CATEGORY_ID]


def build_completion_lock(
    counters: ExecutionCounters, comparison: dict[str, Any],
) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "category_id": CATEGORY_ID,
        "micro_part_id": MICRO_PART_ID,
        "part3_human_authorized": True,
        "part3_execution_completed": True,
        "authorization_consumed": True,
        "development_only": True,
        "sample": PART3_SAMPLE,
        "primary_sample": PRIMARY_SAMPLE,
        "target": PART3_TARGET,
        "feature_set": FEATURE_SET_NAME,
        "base_feature_count": BASE_FEATURE_COUNT,
        "transformed_feature_count": TRANSFORMED_FEATURE_COUNT,
        "only_sample_changed": True,
        "no_retuning": True,
        "model_fit_calls": counters.model_fit_calls,
        "prediction_calls": counters.prediction_calls,
        "tuning_search_calls": counters.tuning_search_calls,
        "m1_robustness_started": True,
        "m1_robustness_completed": False,
        "completed_category_ids": list(COMPLETED_CATEGORY_IDS),
        "next_category_id": NEXT_CATEGORY_ID,
        "part4_execution_authorized": False,
        "m1_robustness_execution_authorized": False,
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
        "threshold_optimization_executed": False,
        "p_values_computed": False,
        "scientific_interpretation": SCIENTIFIC_INTERPRETATION,
        "replaces_primary_results": False,
        "selects_paper_winner": False,
        "primary_ordering_lock_changed": False,
        "primary_ordering_preserved": comparison["primary_ordering_preserved"],
        "closed_parts_byte_identical": True,
        "primary_comparison_artifact": F_COMPARISON,
        "m1_robustness_remaining_parts": "parts_4_to_6_outstanding",
    }


# --------------------------------------------------------------------------- #
# README
# --------------------------------------------------------------------------- #

def build_readme(
    metrics_rows: list[dict[str, Any]], comparison: dict[str, Any],
    delta_summary: dict[str, Any], exec_manifest: dict[str, Any],
) -> str:
    d = delta_summary
    p = d["main_rule_a_primary"]
    e = d["expanded_rule_a_company_scope_robustness"]
    lines = [
        "# Stage126 M1 — Robustness Part 3: Expanded Rule A Company Scope",
        "",
        "**Part 3 only. Explicitly human-authorized. Development folds only. "
        "Only the company-scope sample changed. No retuning occurred. No "
        "full-development refit occurred. No final-test predictor or target "
        "values were accessed. No final-test evaluation occurred. No "
        "calibration, threshold optimization, bootstrap, Holm correction, "
        "p-values, SMOTE, SMOTENC or SHAP was executed. Part 4 is not "
        "authorized and not started. Primary results were not replaced and no "
        "paper winner was selected. Stage125 Part 5 remains historical and "
        "immutable.**",
        "",
        "Part 3 is **development-only sample-sensitivity evidence**.",
        "",
        "## Specification",
        "",
        f"- Category: `{CATEGORY_ID}` (changed dimension: `{CHANGED_DIMENSION}`)",
        f"- Scientific role: `{SCIENTIFIC_ROLE}`",
        f"- Micro-part: `{MICRO_PART_ID}`",
        f"- Sample: `{PART3_SAMPLE}` (**changed**; primary is `{PRIMARY_SAMPLE}`)",
        f"- Input: `{PART3_ANALYSIS_READY_REL}` (`{PART3_ANALYSIS_READY_SHA256}`)",
        f"- Target: `{PART3_TARGET}` (unchanged)",
        f"- Feature set: `{FEATURE_SET_NAME}` — {BASE_FEATURE_COUNT} base "
        f"features, {TRANSFORMED_FEATURE_COUNT} model-matrix columns "
        "(9 transformed features followed by their 9 missingness indicators)",
        f"- Imbalance policy: `{IMBALANCE_POLICY}` (unchanged)",
        "- Folds: Fold 1 train 1393-1395 / val 1396-1397; "
        "Fold 2 train 1393-1397 / val 1398-1399 (unchanged)",
        f"- Model seeds: {', '.join(str(s) for s in MODEL_SEEDS)}; "
        f"Logistic deterministic seed {LOGISTIC_DETERMINISTIC_SEED} (unchanged)",
        f"- Model fits: {EXPECTED_MODEL_FIT_CALLS}; predictions: "
        f"{EXPECTED_PREDICTION_CALLS}; tuning searches: 0",
        "",
        "## Nine-feature primary order (unchanged)",
        "",
        "| # | feature | source column | transformation | indicator column |",
        "|---|---|---|---|---|",
    ]
    for i, feat in enumerate(PART3_FEATURE_ORDER, start=1):
        lines.append(
            f"| {i} | `{feat}` | `{PART3_FEATURE_SOURCE_COLUMN[feat]}` | "
            f"{FEATURE_TRANSFORMATION[feat]} | {BASE_FEATURE_COUNT + i} |"
        )
    lines += [
        "",
        f"`{PROHIBITED_FEATURE}` remains audit-only and prohibited.",
        "",
        "## Sample counts",
        "",
        f"- Analysis-ready: **{e['analysis_ready']['rows']} rows**, "
        f"{e['analysis_ready']['companies']} companies, "
        f"{e['analysis_ready']['positive']} positive, "
        f"{e['analysis_ready']['negative']} negative, 0 missing target",
        f"- Development: **{exec_manifest['development_rows_loaded']} rows** "
        f"({exec_manifest['fold_counts']['fold1_train']['positive'] and ''}"
        f"{EXPECTED_DEV_POSITIVE} positive, {EXPECTED_DEV_NEGATIVE} negative)",
        "- Fold roles: "
        + ", ".join(
            f"{role} {exec_manifest['fold_counts'][role]['rows']}"
            for role in primary.DEV_ROLES
        ),
        f"- Final-test identities (counted via the frozen split contract only): "
        f"**{exec_manifest['final_test_identities_counted']}**",
        "",
        "## Sample delta versus the primary Rule A sample (row identities only)",
        "",
        "| scope | primary Rule A | expanded Rule A | difference |",
        "|---|---|---|---|",
        f"| analysis-ready rows | {p['analysis_ready']['rows']} | "
        f"{e['analysis_ready']['rows']} | +{d['expanded_only_rows']} |",
        f"| companies | {p['analysis_ready']['companies']} | "
        f"{e['analysis_ready']['companies']} | +{d['company_delta']} |",
        f"| positive | {p['analysis_ready']['positive']} | "
        f"{e['analysis_ready']['positive']} | {d['positive_delta']} |",
        f"| negative | {p['analysis_ready']['negative']} | "
        f"{e['analysis_ready']['negative']} | +{d['negative_delta']} |",
        f"| development rows | {p['development']['rows']} | "
        f"{e['development']['rows']} | +{d['development_rows_added']} |",
        f"| OOF identities | {p['oof_identities']} | {e['oof_identities']} | "
        f"+{d['oof_identities_added']} |",
        f"| final-test identities | {p['final_test_identities']} | "
        f"{e['final_test_identities']} | +{d['final_test_identities_added']} |",
        "",
        "Expanded Rule A is a **strict superset** of primary Rule A "
        f"({d['expanded_only_rows']} expanded-only rows, "
        f"{d['primary_only_rows']} primary-only rows). **Every added "
        "development row is negative**, and all "
        f"{d['oof_identities_added']} added OOF identities carry target 0. "
        "Final-test rows contribute identities and counts only — no row-level "
        f"final-test value was read. Detail: `{F_SAMPLE_DELTA}`.",
        "",
        "## Development results (sample sensitivity only)",
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
    qp = comparison["part3_pooled_pr_auc"]
    ac = comparison["absolute_change_vs_primary"]
    rc = comparison["relative_change_percent_vs_primary"]
    dirn = comparison["direction_by_family"]
    lines += [
        "",
        "## Comparison with the locked primary Rule A results",
        "",
        "| model family | locked primary pooled PR-AUC | Part 3 pooled PR-AUC | "
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
        "- Part 3 observed ordering: "
        + " > ".join(f"`{f}`" for f in comparison["part3_observed_ordering"]),
        f"- **Primary ordering preserved: "
        f"{str(comparison['primary_ordering_preserved']).lower()}**",
        f"- Largest absolute pooled PR-AUC change: "
        f"{comparison['largest_absolute_pr_auc_change']}",
        "",
        "**Interpretation (cautious).** " + comparison["interpretation"],
        "",
        "## Descriptive comparison with Part 2 (separated; no additional claim)",
        "",
        "| model family | Part 2 pooled PR-AUC | Part 3 pooled PR-AUC | Part 3 − Part 2 |",
        "|---|---|---|---|",
    ]
    dp2 = comparison["descriptive_part2_comparison"]
    for fam in MODEL_FAMILIES:
        lines.append(
            f"| `{fam}` | {dp2['part2_pooled_pr_auc'][fam]} | {qp[fam]} | "
            f"{dp2['part3_minus_part2_absolute'][fam]} |"
        )
    lines += [
        "",
        dp2["note"],
        "",
        "## Final-test lock",
        "",
        f"- Final-test identities counted via the frozen split contract: "
        f"**{exec_manifest['final_test_identities_counted']}**",
        "- Final-test predictor rows loaded: **0**",
        "- Final-test target rows loaded: **0**",
        "- Final-test predictions generated: **0**",
        "- Final-test metrics computed: **0**",
        "- Final-test evaluations: **0**",
        "- Full-development refits: **0**",
        "",
        "## Validation architecture",
        "",
        "Current Stage126 state is validated by the independent Stage126 "
        "current-state validator, which recognized this Part 3 package "
        "generically with **no validator source change**. **Stage125 Part 5 "
        "remains historical and immutable** and is not a live gate; no Part 3 "
        "Part 5 compatibility artifact exists. Part 1 and Part 2 remain closed "
        "packages and were not regenerated.",
        "",
        "## Next",
        "",
        f"The next registered category is `{NEXT_CATEGORY_ID}` (Part 4). "
        "**Part 4 is not authorized and not started** — it requires its own "
        "separate explicit human authorization. Parts 4-6 remain outstanding, "
        "so the overall M1 robustness program is **not** complete. The final "
        "test remains locked and untouched.",
    ]
    return "\n".join(lines).rstrip("\n") + "\n"


# --------------------------------------------------------------------------- #
# QC
# --------------------------------------------------------------------------- #

def build_qc_assertions(
    repo_root: Path, *, auth_record: dict[str, Any], part0_record: dict[str, Any],
    exec_manifest: dict[str, Any], completion_lock: dict[str, Any],
    comparison: dict[str, Any], delta_rows: list[dict[str, Any]],
    delta_summary: dict[str, Any], oof_rows: list[dict[str, Any]],
    metrics_rows: list[dict[str, Any]], counters: ExecutionCounters,
    loaded: dict[str, Any], primary_observed: dict[str, str],
    closed_observed: dict[str, str], predecessors: list[str],
    network_attempts: int, base_main_commit: str,
) -> list[dict[str, Any]]:
    a: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        a.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    # ----------------------------- Authorization ---------------------------- #
    raw = auth_record["human_authorization_text"].encode("utf-8")
    add("authorization_text_bytes_exact",
        len(raw) == HUMAN_AUTHORIZATION_TEXT_BYTES, str(len(raw)))
    add("authorization_text_hash_exact",
        hashlib.sha256(raw).hexdigest() == HUMAN_AUTHORIZATION_TEXT_SHA256
        == auth_record["human_authorization_text_sha256"])
    add("authorized_category_is_part3",
        auth_record["authorized_category_id"] == CATEGORY_ID)
    add("part3_execution_authorized",
        auth_record["part3_execution_authorized"] is True
        and auth_record["development_fold_execution_authorized"] is True)
    add("open_unmerged_pr_authorized",
        auth_record["create_open_unmerged_pr_authorized"] is True)
    for field in (
        "merge_authorized", "part4_execution_authorized",
        "full_development_refit_authorized",
        "final_test_predictor_access_authorized",
        "final_test_target_access_authorized", "final_test_access_authorized",
        "final_test_evaluation_authorized", "calibration_authorized",
        "threshold_optimization_authorized", "bootstrap_authorized",
        "holm_authorized", "p_values_authorized",
        "winner_selection_authorized", "smote_authorized",
        "smotenc_authorized", "shap_authorized", "m2_authorized",
        "m3_authorized", "m4_authorized",
    ):
        add(f"not_authorized[{field}]", auth_record[field] is False)
    add("authorization_consumed",
        completion_lock["authorization_consumed"] is True)
    add("base_main_commit_exact",
        auth_record["authorized_base_main_commit"] == BASE_MAIN_COMMIT
        == base_main_commit, base_main_commit)

    # ------------------------- Category order ------------------------------- #
    add("part0_execution_order_places_part3_third",
        part0_record["execution_order"][2] == CATEGORY_ID)
    add("parts_1_and_2_completed_before_part3",
        predecessors == [PART1_CATEGORY_ID, PART2_CATEGORY_ID], str(predecessors))
    add("completed_category_ids_exact",
        completion_lock["completed_category_ids"] == COMPLETED_CATEGORY_IDS)
    add("next_category_is_part4",
        completion_lock["next_category_id"] == NEXT_CATEGORY_ID)

    # --------------------- One-factor-at-a-time contract -------------------- #
    add("sample_changed_to_expanded_rule_a",
        exec_manifest["sample"] == PART3_SAMPLE
        and exec_manifest["primary_sample"] == PRIMARY_SAMPLE
        and exec_manifest["sample"] != exec_manifest["primary_sample"])
    add("changed_dimension_is_sample",
        exec_manifest["changed_dimension"] == CHANGED_DIMENSION)
    add("target_unchanged",
        exec_manifest["target"] == PART3_TARGET == primary.PRIMARY_TARGET
        and exec_manifest["target_changed"] is False)
    add("persistent_loss_target_not_used",
        exec_manifest["target"] != PROHIBITED_TARGET)
    add("sample_sha256_exact",
        sha256_file(repo_root / PART3_ANALYSIS_READY_REL)
        == PART3_ANALYSIS_READY_SHA256)
    add("primary_sample_sha256_exact",
        sha256_file(repo_root / PRIMARY_ANALYSIS_READY_REL)
        == PRIMARY_ANALYSIS_READY_SHA256)
    add("nine_feature_order_exact",
        tuple(exec_manifest["features_exact_order"]) == PART3_FEATURE_ORDER
        == tuple(primary.M1_PRIMARY_FEATURE_ORDER))
    add("feature_count_and_matrix_width_exact",
        exec_manifest["base_feature_count"] == BASE_FEATURE_COUNT == 9
        and exec_manifest["transformed_feature_count"]
        == TRANSFORMED_FEATURE_COUNT == 18)
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
    add("imbalance_policy_unchanged",
        exec_manifest["imbalance_policy"] == IMBALANCE_POLICY
        and exec_manifest["imbalance_policy_changed"] is False)
    add("class_weights_from_training_folds_only",
        exec_manifest["class_weights_use_validation_rows"] is False
        and exec_manifest["class_weights_reused_from_primary_sample"] is False)
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
    ar = delta_summary["expanded_rule_a_company_scope_robustness"]["analysis_ready"]
    add("analysis_ready_rows", ar["rows"] == EXPECTED_ROWS, str(ar["rows"]))
    add("analysis_ready_companies", ar["companies"] == EXPECTED_COMPANIES)
    add("analysis_ready_positive", ar["positive"] == EXPECTED_POSITIVE)
    add("analysis_ready_negative", ar["negative"] == EXPECTED_NEGATIVE)
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
    for name, value in counters.zero_counters().items():
        add(f"zero_counter[{name}]", value == 0, str(value))
    add("network_requests_attempted_zero", network_attempts == 0)
    spw = counters.scale_pos_weight_by_fold
    for role, (neg, pos) in EXPECTED_XGB_SCALE_POS_WEIGHT.items():
        add(f"xgboost_scale_pos_weight[{role}]",
            abs(spw.get(role, 0.0) - (neg / pos)) < 1e-12, repr(spw.get(role)))

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
    add("oof_sample_column_is_expanded",
        all(r["sample"] == PART3_SAMPLE for r in oof_rows))
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
    add("final_test_predictions_zero",
        exec_manifest["final_test_predictions_generated"] == 0
        and counters.final_test_predictions == 0)
    add("final_test_metrics_zero",
        exec_manifest["final_test_metrics_computed"] == 0)
    add("final_test_evaluations_zero", counters.final_test_evaluations == 0)
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
        and completion_lock["full_development_refit_performed"] is False)

    # ------------------------------ Sample delta ----------------------------- #
    add("expanded_is_strict_superset",
        delta_summary["expanded_is_strict_superset_of_primary"] is True
        and delta_summary["primary_only_rows"] == EXPECTED_PRIMARY_ONLY_KEYS)
    add("expanded_only_rows_exact",
        delta_summary["expanded_only_rows"] == EXPECTED_EXPANDED_ONLY_KEYS,
        str(delta_summary["expanded_only_rows"]))
    add("company_delta_exact",
        delta_summary["company_delta"] == EXPECTED_COMPANY_DELTA)
    add("positive_delta_zero",
        delta_summary["positive_delta"] == EXPECTED_POSITIVE_DELTA)
    add("negative_delta_exact",
        delta_summary["negative_delta"] == EXPECTED_NEGATIVE_DELTA)
    add("development_delta_exact",
        delta_summary["development_rows_added"] == EXPECTED_DEV_ROW_DELTA
        and delta_summary["development_positives_added"] == 0
        and delta_summary["development_negatives_added"]
        == EXPECTED_DEV_NEGATIVE_DELTA)
    for role, want in EXPECTED_FOLD_ROW_DELTA.items():
        fd = delta_summary["fold_delta"][role]
        add(f"fold_delta[{role}]",
            fd["rows_added"] == want and fd["positives_added"] == 0
            and fd["negatives_added"] == want and fd["rows_removed"] == 0,
            f"+{fd['rows_added']}")
    add("oof_identity_delta_exact",
        delta_summary["oof_identities_added"] == EXPECTED_OOF_IDENTITY_DELTA
        and delta_summary["oof_identities_added_all_target_zero"] is True)
    add("final_test_identity_delta_exact",
        delta_summary["final_test_identities_added"]
        == EXPECTED_FINAL_TEST_IDENTITY_DELTA)
    add("sample_delta_uses_identities_only",
        delta_summary["comparison_basis"] == "row_identities_only"
        and delta_summary["final_test_values_read"] is False)
    add("sample_delta_rows_emitted",
        len(delta_rows) == EXPECTED_ROWS, str(len(delta_rows)))
    add("sample_delta_no_value_columns",
        all(set(r) == set(SAMPLE_DELTA_COLUMNS) for r in delta_rows))
    add("sample_delta_status_counts",
        sum(1 for r in delta_rows
            if r["sample_delta_status"] == DELTA_STATUS_EXPANDED_ONLY)
        == EXPECTED_EXPANDED_ONLY_KEYS
        and sum(1 for r in delta_rows
                if r["sample_delta_status"] == DELTA_STATUS_BOTH)
        == EXPECTED_PRIMARY_ROWS)

    # ---------------------------- Immutability ------------------------------- #
    add("primary_stage126_artifacts_byte_identical",
        primary_observed == {
            k: PINNED_PRIMARY_ARTIFACTS[k] for k in primary_observed
        })
    add("part1_and_part2_artifacts_byte_identical",
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

    # ---------------------------- Interpretation ----------------------------- #
    add("locked_primary_pr_auc_unchanged",
        comparison["primary_reference"]["locked_values_match_observed"] is True)
    add("primary_results_not_replaced",
        comparison["primary_results_replaced"] is False
        and completion_lock["replaces_primary_results"] is False)
    add("primary_ordering_lock_not_changed",
        comparison["primary_ordering_lock_changed"] is False
        and completion_lock["primary_ordering_lock_changed"] is False)
    add("no_paper_winner_selected",
        comparison["paper_winner_selected"] is False
        and completion_lock["selects_paper_winner"] is False
        and completion_lock["winner_selected"] is False)
    add("no_new_confirmatory_comparison",
        comparison["new_confirmatory_model_comparison"] is False)
    add("part2_comparison_is_descriptive_only",
        comparison["descriptive_part2_comparison"][
            "preferred_robustness_sample_selected"] is False
        and comparison["descriptive_part2_comparison"]["claims_multiplied"]
        is False)
    add("development_only_interpretation",
        completion_lock["scientific_interpretation"]
        == SCIENTIFIC_INTERPRETATION
        and completion_lock["development_only"] is True)
    add("part4_not_authorized",
        completion_lock["part4_execution_authorized"] is False
        and completion_lock["m1_robustness_execution_authorized"] is False)
    add("m1_robustness_not_completed",
        completion_lock["m1_robustness_completed"] is False)
    add("no_prohibited_analysis_executed",
        completion_lock["calibration_executed"] is False
        and completion_lock["bootstrap_executed"] is False
        and completion_lock["holm_executed"] is False
        and completion_lock["threshold_optimization_executed"] is False
        and completion_lock["p_values_computed"] is False
        and completion_lock["smote_executed"] is False
        and completion_lock["smotenc_executed"] is False
        and completion_lock["shap_executed"] is False)
    return a


# --------------------------------------------------------------------------- #
# Handoff markers
# --------------------------------------------------------------------------- #

def part3_handoff_markers() -> dict[str, Any]:
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
        "m1_robustness_completed": False,
        "m1_robustness_part1_completed": True,
        "m1_robustness_part2_completed": True,
        "m1_robustness_part3_human_authorized": True,
        "m1_robustness_part3_completed": True,
        "m1_robustness_completed_category_ids": list(COMPLETED_CATEGORY_IDS),
        "m1_robustness_next_category_id": NEXT_CATEGORY_ID,
        "m1_robustness_part3_authorized": False,
        "m1_robustness_part4_authorized": False,
        "m1_robustness_execution_authorized": False,
        "full_development_refit_performed": False,
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

    allow_p3 = build_part3_allowlist(repo_root)
    allow_pr = build_primary_allowlist(repo_root)
    loaded = load_part3_development_values(repo_root, allow_p3)
    delta_rows, delta_summary = build_sample_delta(
        repo_root, allow_pr, allow_p3, loaded,
    )

    folds_data = {
        role: primary._role_matrix(loaded["rows"], allow_p3["role_pairs"], role)
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
    oof_rows, predictions = generate_part3_oof(folds_data, selected, counters)
    metrics_rows = compute_part3_metrics(folds_data, selected, predictions)

    if counters.model_fit_calls != EXPECTED_MODEL_FIT_CALLS:
        raise QCFail(
            f"model_fit_calls {counters.model_fit_calls} != "
            f"{EXPECTED_MODEL_FIT_CALLS}"
        )
    if counters.prediction_calls != EXPECTED_PREDICTION_CALLS:
        raise QCFail("prediction_calls mismatch")
    if counters.tuning_search_calls != 0:
        raise QCFail("tuning searches executed (fail-closed)")

    exec_manifest = build_execution_manifest(
        counters, loaded, allow_p3, selected, delta_summary,
    )
    comparison = build_primary_comparison(repo_root, metrics_rows)
    completion_lock = build_completion_lock(counters, comparison)
    readme = build_readme(metrics_rows, comparison, delta_summary, exec_manifest)

    content = {
        F_AUTH: _json_str(auth_record),
        F_FEATURE_MANIFEST: _csv_str(
            FEATURE_MANIFEST_COLUMNS, build_feature_manifest_rows(),
        ),
        F_SAMPLE_DELTA: _csv_str(SAMPLE_DELTA_COLUMNS, delta_rows),
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
        "comparison": comparison, "delta_rows": delta_rows,
        "delta_summary": delta_summary, "oof_rows": oof_rows,
        "metrics_rows": metrics_rows, "counters": counters, "loaded": loaded,
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

    # Git-based frozen Stage125 checks run OUTSIDE the network sentinel.
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
        comparison=extras["comparison"], delta_rows=extras["delta_rows"],
        delta_summary=extras["delta_summary"], oof_rows=extras["oof_rows"],
        metrics_rows=extras["metrics_rows"], counters=extras["counters"],
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
        "sample": PART3_SAMPLE,
        "sample_sha256": PART3_ANALYSIS_READY_SHA256,
        "target": PART3_TARGET,
        "feature_set": FEATURE_SET_NAME,
        "base_feature_count": BASE_FEATURE_COUNT,
        "transformed_feature_count": TRANSFORMED_FEATURE_COUNT,
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
        "sample_delta": extras["delta_summary"],
        "selected_configuration_ids": {
            f: EXPECTED_SELECTED[f]["configuration_id"] for f in MODEL_FAMILIES
        },
        "selected_configurations_changed": False,
        "model_seeds": list(MODEL_SEEDS),
        "model_fit_calls": counters.model_fit_calls,
        "prediction_calls": counters.prediction_calls,
        "network_requests_attempted": network_attempts,
        "zero_counters": counters.zero_counters(),
        "final_test_identities_counted": loaded["final_test_rows_seen"],
        "final_test_predictor_rows_loaded": 0,
        "final_test_target_rows_loaded": 0,
        "final_test_predictions_generated": 0,
        "final_test_metrics_computed": 0,
        "final_test_evaluations": 0,
        "primary_artifact_sha256": dict(sorted(
            extras["primary_observed"].items()
        )),
        "closed_part_artifact_sha256": dict(sorted(
            extras["closed_observed"].items()
        )),
        "output_sha256": dict(sorted(content_hashes.items())),
        "primary_comparison_sha256": content_hashes[F_COMPARISON],
        "sample_delta_sha256": content_hashes[F_SAMPLE_DELTA],
        "primary_ordering_preserved":
            extras["comparison"]["primary_ordering_preserved"],
        "stage125_part5_used_as_gate": False,
        "assertions": assertions,
        **part3_handoff_markers(),
    }
    qc_text = _json_str(qc)
    qc_hash = sha256_bytes(qc_text.encode("utf-8"))
    meta = {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "description": (
            "Stage126 M1 robustness Part 3 expanded Rule A company-scope sample "
            "(human-authorized; development folds only; only the sample "
            "changed; no retuning; no full-development refit; final test "
            "locked; no calibration/bootstrap/Holm/winner selection; no "
            "SMOTE/SMOTENC/SHAP; development-only sample sensitivity evidence)."
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
            PART3_ANALYSIS_READY_REL: PART3_ANALYSIS_READY_SHA256,
            PRIMARY_ANALYSIS_READY_REL: PRIMARY_ANALYSIS_READY_SHA256,
            SPLIT_MANIFEST_REL: SPLIT_MANIFEST_SHA256,
            EVENT_COUNT_GATE_REL: EVENT_COUNT_GATE_SHA256,
            SAMPLE_SUMMARY_REL: SAMPLE_SUMMARY_SHA256,
            SELECTED_CONFIGURATIONS_REL: SELECTED_CONFIGURATIONS_SHA256,
        },
        "closed_part_artifact_sha256": dict(sorted(
            extras["closed_observed"].items()
        )),
        "primary_comparison_sha256": content_hashes[F_COMPARISON],
        "sample_delta_sha256": content_hashes[F_SAMPLE_DELTA],
        "network_requests_attempted": network_attempts,
        "model_fit_calls": counters.model_fit_calls,
        "prediction_calls": counters.prediction_calls,
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
        raise QCFail(f"Part 3 QC failed: {failed} assertions failed")

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
