"""Stage126 M1 — Robustness Part 2: listing-timing Rule B sample.

Explicitly human-authorized, development-only sensitivity analysis. ONLY the
sample changes relative to the locked primary Stage126 M1 development analysis;
the target, the nine-feature primary set, the selected configurations, the
temporal folds, the imbalance policy, the seeds and the metric contract are all
held fixed.

Fail-closed guarantees:
  * the locked final test is never opened — final-test predictor/target values
    are never parsed, stored, summarized, logged or exported (only denylisted
    row identities are counted, and aggregate final-test counts are read only
    from already frozen Stage125 summary artifacts);
  * no hyperparameter search runs (the three primary selected configurations are
    loaded from the frozen artifact and reused verbatim);
  * no full-development refit, no SMOTE/SMOTENC, no SHAP, no calibration, no
    bootstrap/Holm, no winner selection;
  * the frozen Stage125 tree, the eight primary Stage126 artifacts and the Part 1
    scientific artifacts must remain byte-identical.

Part 2 results are sensitivity-analysis evidence only. They never replace the
primary results and never change the locked primary ordering used for
confirmatory interpretation.
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

# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #

QC_STAGE = "stage126_m1_robustness_part2_listing_rule_b"
CURRENT_STAGE = "Stage126"
CONTRACT_VERSION = "stage126_m1_robustness_part2_listing_rule_b_v1"
CATEGORY_ID = "main_rule_b_listing_robustness"
SCIENTIFIC_ROLE = "listing_timing_sample_robustness"
CHANGED_DIMENSION = "sample"
IMBALANCE_POLICY = "primary_class_weighting"
SCIENTIFIC_INTERPRETATION = "sensitivity_analysis_only"
MICRO_PART_ID = "stage126-m1-robustness-part2-listing-rule-b"
PART1_CATEGORY_ID = part1.CATEGORY_ID
NEXT_CATEGORY_ID = "expanded_rule_a_company_scope_robustness"

SRC_REL = "project/src/stage126_m1_robustness_part2_listing_rule_b.py"
RUN_REL = "project/run_stage126_m1_robustness_part2_listing_rule_b.py"
TEST_REL = "project/tests/test_stage126_m1_robustness_part2_listing_rule_b.py"

STAGE126_DIR_REL = "project/stage126"
F_AUTH = "stage126_m1_robustness_part2_human_authorization_record.json"
F_FEATURE_MANIFEST = "stage126_m1_robustness_part2_feature_manifest.csv"
F_SAMPLE_DELTA = "stage126_m1_robustness_part2_sample_delta.csv"
F_EXEC_MANIFEST = "stage126_m1_robustness_part2_execution_manifest.json"
F_OOF = "stage126_m1_robustness_part2_oof_predictions.csv"
F_METRICS = "stage126_m1_robustness_part2_metrics.csv"
F_COMPARISON = "stage126_m1_robustness_part2_primary_comparison.json"
F_COMPLETION_LOCK = "stage126_m1_robustness_part2_completion_lock.json"
F_PART5_COMPAT = (
    "stage126_m1_robustness_part2_part5_successor_compatibility.json"
)
F_QC = "stage126_m1_robustness_part2_qc_report.json"
F_METADATA = "metadata_and_hashes_stage126_m1_robustness_part2.json"
F_README = "README_STAGE126_M1_ROBUSTNESS_PART2_LISTING_RULE_B.md"

# --------------------------------------------------------------------------- #
# Exact human authorization (byte-for-byte Persian)
# --------------------------------------------------------------------------- #

HUMAN_AUTHORIZATION_TEXT_FA = (
    "مجوز اجرای Stage126 M1 Robustness Part 2 — "
    "`main_rule_b_listing_robustness` را می‌دهم.\n"
    "\n"
    "این مجوز فقط برای اجرای Part 2 و ساخت یک PR باز و Merge‌نشده است و "
    "شامل Merge، Part 3، full-development refit، final test، SMOTE، SHAP یا "
    "M2/M3/M4 نمی‌شود."
)
HUMAN_AUTHORIZATION_TEXT_SHA256 = (
    "27935d31a6efcc6116f0d4007424bad5c7b8599faabcb8d39176c569bf172bcb"
)
AUTHORIZATION_ID = "stage126-m1-robustness-part2-human-authorization"
AUTHORIZATION_DATE = "2026-07-23"
AUTHORIZATION_CONTEXT = (
    "The immediately preceding independently verified repository state merged "
    "Stage126 M1 Robustness Part 1 and identified Part 2 — "
    "main_rule_b_listing_robustness — as the next gated micro-part."
)

# --------------------------------------------------------------------------- #
# Fixed (inherited) analysis dimensions — ONLY the sample changes
# --------------------------------------------------------------------------- #

PRIMARY_SAMPLE = primary.PRIMARY_SAMPLE            # main_rule_a_primary
PART2_SAMPLE = "main_rule_b_listing_robustness"
PART2_TARGET = primary.PRIMARY_TARGET              # FD_target_main_t_plus_1
FEATURE_SET_NAME = primary.FEATURE_SET_NAME        # M1_PRIMARY_FEATURE_ORDER
PART2_FEATURE_ORDER: tuple[str, ...] = tuple(primary.M1_PRIMARY_FEATURE_ORDER)
PART2_FEATURE_SOURCE_COLUMN: dict[str, str] = dict(primary.FEATURE_SOURCE_COLUMN)
PROHIBITED_FEATURE = primary.PROHIBITED_FEATURE
PROHIBITED_TARGET = "FD_target_persistent_loss_robustness_t_plus_1"

BASE_FEATURE_COUNT = 9
TRANSFORMED_FEATURE_COUNT = 18  # 9 imputed continuous + 9 missingness indicators

MODEL_FAMILIES = primary.ALLOWED_MODEL_FAMILIES
MODEL_SEEDS = primary.FINAL_OOF_SEEDS
LOGISTIC_DETERMINISTIC_SEED = primary.TUNING_SEEDS[0]

FEATURE_TRANSFORMATION: dict[str, str] = {
    "log_total_assets": "ln(total_assets) if total_assets > 0 else missing",
    "leverage_ratio": "frozen_part3c_value",
    "current_ratio": "frozen_part3c_value",
    "roa_period_adjusted": "frozen_part3c_value",
    "ocf_to_assets_period_adjusted": "frozen_part3c_value",
    "asset_turnover_period_adjusted": "frozen_part3c_value",
    "operating_margin_period_adjusted": "frozen_part3c_value",
    "financial_expense_to_assets_period_adjusted":
        "frozen_part3c_value_source_sign_preserved",
    "accumulated_loss_to_capital_ratio": "frozen_part3c_value",
}

# --------------------------------------------------------------------------- #
# Exact expected Rule B counts (asserted; never used to relax fail-closed loads)
# --------------------------------------------------------------------------- #

EXPECTED_RULE_B_ROWS = 993
EXPECTED_RULE_B_COMPANIES = 117
EXPECTED_RULE_B_POSITIVE = 79
EXPECTED_RULE_B_NEGATIVE = 914

EXPECTED_DEV_ROWS = 655
EXPECTED_DEV_POSITIVE = 68
EXPECTED_DEV_NEGATIVE = 587

EXPECTED_FOLD_COUNTS: dict[str, dict[str, int]] = {
    "fold1_train": {"rows": 242, "positive": 33, "negative": 209},
    "fold1_validation": {"rows": 202, "positive": 25, "negative": 177},
    "fold2_train": {"rows": 444, "positive": 58, "negative": 386},
    "fold2_validation": {"rows": 211, "positive": 10, "negative": 201},
}
EXPECTED_OOF_ROWS_PER_FAMILY = 413        # 202 + 211
EXPECTED_OOF_ROWS_TOTAL = EXPECTED_OOF_ROWS_PER_FAMILY * len(MODEL_FAMILIES)
EXPECTED_OOF_POSITIVE = 35
EXPECTED_OOF_NEGATIVE = 378
EXPECTED_METRICS_ROWS = len(MODEL_FAMILIES) * 3

EXPECTED_MODEL_FIT_CALLS = 22   # 2 logistic + 10 RF + 10 XGBoost
EXPECTED_PREDICTION_CALLS = 22

EXPECTED_FINAL_TEST_IDENTITIES = 338
EXPECTED_XGB_SCALE_POS_WEIGHT: dict[str, tuple[int, int]] = {
    "fold1_train": (209, 33),
    "fold2_train": (386, 58),
}

# Rule A reference counts (frozen; used only for the identity-level delta audit).
EXPECTED_RULE_A_ROWS = primary.EXPECTED_ALL_PRIMARY_ROWS      # 1012
EXPECTED_RULE_A_COMPANIES = 119
EXPECTED_RULE_A_POSITIVE = 80
EXPECTED_RULE_A_NEGATIVE = 932
EXPECTED_RULE_A_DEV_ROWS = primary.EXPECTED_DEV_ROWS          # 666
EXPECTED_RULE_A_DEV_POSITIVE = primary.EXPECTED_DEV_POSITIVE  # 68
EXPECTED_RULE_A_DEV_NEGATIVE = primary.EXPECTED_DEV_NEGATIVE  # 598
EXPECTED_RULE_A_OOF_ROWS = primary.EXPECTED_POOLED_OOF_ROWS   # 421
EXPECTED_RULE_A_OOF_POSITIVE = primary.EXPECTED_POOLED_OOF_POSITIVE
EXPECTED_RULE_A_OOF_NEGATIVE = primary.EXPECTED_POOLED_OOF_NEGATIVE
EXPECTED_RULE_A_FINAL_TEST_IDENTITIES = primary.EXPECTED_FINAL_TEST_PAIRS  # 346

EXPECTED_RULE_A_ONLY_KEYS = 19
EXPECTED_RULE_B_ONLY_KEYS = 0

# --------------------------------------------------------------------------- #
# Frozen inputs (pinned; never modified)
# --------------------------------------------------------------------------- #

RULE_A_ANALYSIS_READY_REL = primary.ANALYSIS_READY_REL
RULE_A_ANALYSIS_READY_SHA256 = primary.ANALYSIS_READY_SHA256
RULE_B_ANALYSIS_READY_REL = (
    "project/stage125/part3c_outputs/analysis_ready_main_rule_b_stage125.csv"
)
RULE_B_ANALYSIS_READY_SHA256 = (
    "5492cf244489cb88919243cf2f19d57663ba9e0b0d377791a3a1c26babc9b480"
)
SPLIT_MANIFEST_REL = primary.SPLIT_MANIFEST_REL
SPLIT_MANIFEST_SHA256 = primary.SPLIT_MANIFEST_SHA256
# Frozen Stage125 aggregate count artifacts. Aggregate final-test counts are read
# ONLY from these already-frozen summaries — never from row-level final-test
# predictor or target values.
EVENT_COUNT_GATE_REL = "project/stage125/part4_event_count_gate_stage125.csv"
EVENT_COUNT_GATE_SHA256 = (
    "e8432e1f6e3958b658affa05070b5161d36d95e98bc2041bef4b1143ac9f0d17"
)
SAMPLE_SUMMARY_REL = "project/stage125/part3c_sample_summary_stage125.csv"
SAMPLE_SUMMARY_SHA256 = (
    "c203ed3f31a796b769d96e586d45b9b14ab1f73a74bffdfbfcf2d975f2e512bc"
)

SELECTED_CONFIGURATIONS_REL = part1.SELECTED_CONFIGURATIONS_REL
SELECTED_CONFIGURATIONS_SHA256 = part1.SELECTED_CONFIGURATIONS_SHA256
PART0_DECISION_RECORD_REL = part1.PART0_DECISION_RECORD_REL
PART0_DECISION_RECORD_SHA256 = part1.PART0_DECISION_RECORD_SHA256
PRIMARY_SRC_REL = part1.PRIMARY_SRC_REL
PRIMARY_SRC_SHA256 = part1.PRIMARY_SRC_SHA256
PRIMARY_METRICS_REL = part1.PRIMARY_METRICS_REL
PINNED_PRIMARY_ARTIFACTS: dict[str, str] = dict(part1.PINNED_PRIMARY_ARTIFACTS)

# Part 1 SCIENTIFIC artifacts — must remain byte-identical after Part 2.
PINNED_PART1_SCIENTIFIC_ARTIFACTS: dict[str, str] = {
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
    "project/stage126/stage126_m1_robustness_part1_completion_lock.json":
        "964d84f2269bb35b0176f88bb12bcfc13ef2cb487817cf5b49a5c28a87e1822b",
    "project/stage126/stage126_m1_robustness_part1_primary_comparison.json":
        "2b58a85250420a8a18b0ff37cecdf3f2e31160c37e0cb48d027324c87a25c46a",
}
PART1_METRICS_REL = (
    "project/stage126/stage126_m1_robustness_part1_metrics.csv"
)

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
    "missingness_indicator_appended", "included_in_part2",
]
SAMPLE_DELTA_COLUMNS = [
    "predictor_row_key_t", "target_row_key_t_plus_1", "ticker", "fiscal_year_t",
    "target_year", "temporal_partition", "fold_membership",
    "present_in_main_rule_a", "present_in_main_rule_b", "sample_delta_status",
]

DELTA_STATUS_BOTH = "present_in_both_samples"
DELTA_STATUS_RULE_A_ONLY = "rule_a_only_removed_by_listing_rule_b"


class QCFail(RuntimeError):
    """Fail-closed Part 2 validation error."""


class FinalTestLockError(QCFail):
    """The locked final test was approached (fail-closed)."""


# --------------------------------------------------------------------------- #
# Helpers (reused from the already-reviewed primary/Part 1 implementations)
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
    got = recompute_authorization_sha256(HUMAN_AUTHORIZATION_TEXT_FA)
    if got != HUMAN_AUTHORIZATION_TEXT_SHA256:
        raise QCFail(
            f"Part 2 human authorization SHA-256 mismatch: {got} != "
            f"{HUMAN_AUTHORIZATION_TEXT_SHA256}"
        )


def build_authorization_record() -> dict[str, Any]:
    """Deterministic Part 2 human authorization record (hash recomputed)."""
    verify_authorization_text()
    return {
        "authorization_id": AUTHORIZATION_ID,
        "authorization_date": AUTHORIZATION_DATE,
        "authorizing_role": "human_supervisor_data_owner",
        "human_authorization_text": HUMAN_AUTHORIZATION_TEXT_FA,
        "human_authorization_text_sha256": HUMAN_AUTHORIZATION_TEXT_SHA256,
        "authorization_context": AUTHORIZATION_CONTEXT,
        "authorized_category_id": CATEGORY_ID,
        "part2_execution_authorized": True,
        "create_open_unmerged_pr_authorized": True,
        "merge_authorized": False,
        "part3_execution_authorized": False,
        "full_development_refit_authorized": False,
        "final_test_access_authorized": False,
        "final_test_evaluation_authorized": False,
        "smote_authorized": False,
        "smotenc_authorized": False,
        "shap_authorized": False,
        "m2_authorized": False,
        "m3_authorized": False,
        "m4_authorized": False,
        "authorization_scope_note": (
            "Consumed by this Part 2 execution. Grants no standing "
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
    if len(order) < 3 or order[0] != PART1_CATEGORY_ID:
        raise QCFail("Part 0 execution_order head is not the Part 1 category")
    if order[1] != CATEGORY_ID:
        raise QCFail(
            f"Part 0 execution_order[1] {order[1]!r} is not the Part 2 category"
        )
    if order[2] != NEXT_CATEGORY_ID:
        raise QCFail("Part 0 execution_order[2] is not the Part 3 category")
    return record


def verify_part1_scientific_artifacts(repo_root: Path) -> dict[str, str]:
    """Part 1 scientific outputs must be byte-identical after Part 2."""
    observed: dict[str, str] = {}
    for rel, expected in sorted(PINNED_PART1_SCIENTIFIC_ARTIFACTS.items()):
        observed[rel] = require_file_hash(
            repo_root, rel, expected, label="Part 1 scientific artifact",
        )
    return observed


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
    for rel, expected in (
        (RULE_A_ANALYSIS_READY_REL, RULE_A_ANALYSIS_READY_SHA256),
        (RULE_B_ANALYSIS_READY_REL, RULE_B_ANALYSIS_READY_SHA256),
        (SPLIT_MANIFEST_REL, SPLIT_MANIFEST_SHA256),
        (EVENT_COUNT_GATE_REL, EVENT_COUNT_GATE_SHA256),
        (SAMPLE_SUMMARY_REL, SAMPLE_SUMMARY_SHA256),
    ):
        require_file_hash(repo_root, rel, expected, label="frozen Stage125 input")
    return observed


# --------------------------------------------------------------------------- #
# Rule B allowlist (identities only; final-test rows go straight to a denylist)
# --------------------------------------------------------------------------- #

def _read_manifest_split_columns(
    repo_root: Path, sample_design: str,
) -> list[dict[str, str]]:
    """First pass: read ONLY split/key columns for one sample design.

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
            if row.get("sample_design") != sample_design:
                continue
            rows.append({c: row.get(c, "") for c in allowed_cols})
    if not rows:
        raise QCFail(f"no manifest rows for sample design {sample_design!r}")
    return rows


def build_sample_allowlist(
    repo_root: Path, sample_design: str,
    expected_fold_counts: dict[str, dict[str, int]],
    expected_dev_rows: int, expected_final_test_identities: int,
) -> dict[str, Any]:
    """Development allowlist + final-test denylist for one sample (keys only)."""
    man_rows = _read_manifest_split_columns(repo_root, sample_design)

    dev_pairs: dict[tuple[str, str], dict[str, Any]] = {}
    denylist_pairs: set[tuple[str, str]] = set()
    role_pairs: dict[str, set[tuple[str, str]]] = {
        r: set() for r in primary.DEV_ROLES
    }
    role_pairs[primary.FINAL_TEST_ROLE] = set()
    final_test_identities: dict[tuple[str, str], dict[str, str]] = {}

    for row in man_rows:
        key = (row["predictor_row_key_t"], row["target_row_key_t_plus_1"])
        ty = int(row["target_year"])
        split = row["dataset_split"]
        fold = row["temporal_fold"]

        if split == "development" and ty in primary.DEVELOPMENT_TARGET_YEARS:
            if fold not in primary.DEV_ROLES:
                raise QCFail(f"unknown development fold role: {fold!r}")
            role_pairs[fold].add(key)
            info = dev_pairs.setdefault(key, {
                "sample_design": sample_design,
                "ticker": row["ticker"],
                "predictor_row_key_t": key[0],
                "target_row_key_t_plus_1": key[1],
                "fiscal_year_t": row["fiscal_year_t"],
                "target_year": row["target_year"],
                "dataset_split": "development",
                "roles": set(),
            })
            info["roles"].add(fold)
        elif split == "final_test" and ty in primary.FINAL_TEST_TARGET_YEARS:
            # Identity only. No predictor or target value is ever read.
            denylist_pairs.add(key)
            role_pairs[primary.FINAL_TEST_ROLE].add(key)
            final_test_identities[key] = {
                "ticker": row["ticker"],
                "fiscal_year_t": row["fiscal_year_t"],
                "target_year": row["target_year"],
            }
        else:
            raise QCFail(
                f"manifest row not classifiable as dev or final_test: "
                f"split={split} target_year={ty}"
            )

    for role in primary.DEV_ROLES:
        got = len(role_pairs[role])
        exp = expected_fold_counts[role]["rows"]
        if got != exp:
            raise QCFail(f"{sample_design} fold-role {role} count {got} != {exp}")
    if len(role_pairs[primary.FINAL_TEST_ROLE]) != expected_final_test_identities:
        raise QCFail(f"{sample_design} final-test identity count mismatch")
    if len(dev_pairs) != expected_dev_rows:
        raise QCFail(
            f"{sample_design} development unique rows {len(dev_pairs)} != "
            f"{expected_dev_rows}"
        )
    if dev_pairs.keys() & denylist_pairs:
        raise QCFail("development/final-test key overlap (fail-closed)")

    return {
        "sample_design": sample_design,
        "dev_pairs": dev_pairs,
        "denylist_pairs": denylist_pairs,
        "role_pairs": role_pairs,
        "final_test_identities": final_test_identities,
    }


def build_rule_b_allowlist(repo_root: Path) -> dict[str, Any]:
    return build_sample_allowlist(
        repo_root, PART2_SAMPLE, EXPECTED_FOLD_COUNTS,
        EXPECTED_DEV_ROWS, EXPECTED_FINAL_TEST_IDENTITIES,
    )


def build_rule_a_allowlist(repo_root: Path) -> dict[str, Any]:
    return build_sample_allowlist(
        repo_root, PRIMARY_SAMPLE, primary.EXPECTED_FOLD_COUNTS,
        primary.EXPECTED_DEV_ROWS, primary.EXPECTED_FINAL_TEST_PAIRS,
    )


# --------------------------------------------------------------------------- #
# Part 2 nine-feature Rule B loader
# --------------------------------------------------------------------------- #

def part2_source_columns() -> list[str]:
    """Exactly the nine primary source columns; the growth feature can't appear."""
    cols = sorted({PART2_FEATURE_SOURCE_COLUMN[f] for f in PART2_FEATURE_ORDER})
    if len(cols) != BASE_FEATURE_COUNT:
        raise QCFail(
            f"Part 2 source column count {len(cols)} != {BASE_FEATURE_COUNT}"
        )
    if PROHIBITED_FEATURE in cols:
        raise QCFail("prohibited growth feature reached the Part 2 loader")
    return cols


def load_part2_development_values(
    repo_root: Path, allowlist: dict[str, Any],
) -> dict[str, Any]:
    """Second pass: stream the Rule B analysis-ready CSV keeping ONLY dev keys.

    Reads exactly the nine primary source columns and parses the primary target
    for development rows only. Final-test rows are never numerically parsed,
    stored, summarized, logged or exported — the loader only counts that it saw
    their identities. Unknown/unclassified rows fail closed.
    """
    dev_pairs = allowlist["dev_pairs"]
    denylist = allowlist["denylist_pairs"]
    source_cols = part2_source_columns()

    loaded: dict[tuple[str, str], dict[str, Any]] = {}
    final_test_rows_seen = 0
    final_test_predictor_rows_loaded = 0
    final_test_target_rows_loaded = 0
    unknown_rows = 0

    path = repo_root / RULE_B_ANALYSIS_READY_REL
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        header = set(reader.fieldnames or [])
        needed = set(source_cols) | {
            "predictor_row_key_t", "target_row_key_t_plus_1", "ticker",
            "fiscal_year_t", "target_year", PART2_TARGET,
        }
        missing = needed - header
        if missing:
            raise QCFail(f"Rule B analysis-ready CSV missing columns: {sorted(missing)}")
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
                    "features": primary._derive_features(raw_sources),
                    "target": primary._target_value(row[PART2_TARGET]),
                }
            elif key in denylist:
                # Locked final-test row: no predictor/target value is parsed.
                final_test_rows_seen += 1
            else:
                unknown_rows += 1

    if unknown_rows:
        raise QCFail(
            f"{unknown_rows} Rule B analysis-ready rows unclassified (fail-closed)"
        )
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
            raise QCFail("Part 2 feature vector is not nine-dimensional")

    return {
        "rows": loaded,
        "final_test_rows_seen": final_test_rows_seen,
        "final_test_predictor_rows_loaded": final_test_predictor_rows_loaded,
        "final_test_target_rows_loaded": final_test_target_rows_loaded,
    }


# --------------------------------------------------------------------------- #
# Selected configurations (loaded, never re-searched)
# --------------------------------------------------------------------------- #

EXPECTED_SELECTED: dict[str, dict[str, Any]] = part1.EXPECTED_SELECTED


def load_selected_configurations(repo_root: Path) -> dict[str, Any]:
    """Load the frozen primary selected configurations. NO search is performed."""
    return part1.load_selected_configurations(repo_root)


# --------------------------------------------------------------------------- #
# Execution (Rule B development folds only; counted fits/predictions)
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
        self.full_development_refits = 0
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


def generate_part2_oof(
    folds_data: dict[str, dict[str, Any]], selected: dict[str, Any],
    counters: ExecutionCounters,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, np.ndarray]]]:
    """Development-fold OOF predictions on the Rule B sample.

    Logistic is a deterministic single fit per fold; RF/XGBoost average the
    validation probabilities over the five fixed model seeds within each fold.
    No fold ever combines training and validation rows, and no fold is ever
    refit on the complete development set.
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
                    "sample": PART2_SAMPLE,
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
                    # "np.float64(...)" under numpy>=2 and would not be a valid
                    # numeric CSV field.
                    "predicted_probability": float(probs[i]),
                    "seed_aggregation": agg,
                })
    return oof_rows, predictions


def compute_part2_metrics(
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
                "sample": PART2_SAMPLE,
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
            "sample": PART2_SAMPLE,
            "feature_set": FEATURE_SET_NAME,
            "model_family": family, "configuration_id": cid,
            "scope": "pooled_development_oof", **m,
        })
    return rows


# --------------------------------------------------------------------------- #
# Rule A vs Rule B sample-delta audit (row identities only)
# --------------------------------------------------------------------------- #

def read_frozen_event_counts(repo_root: Path) -> dict[tuple[str, str], dict[str, int]]:
    """Aggregate counts per (sample_design, window) from the frozen Part 4 gate.

    This frozen summary artifact is the ONLY permitted source of aggregate
    final-test counts. No row-level final-test value is ever read.
    """
    require_file_hash(
        repo_root, EVENT_COUNT_GATE_REL, EVENT_COUNT_GATE_SHA256,
        label="frozen Part 4 event-count gate",
    )
    out: dict[tuple[str, str], dict[str, int]] = {}
    with (repo_root / EVENT_COUNT_GATE_REL).open(
        "r", encoding="utf-8-sig", newline="",
    ) as fh:
        for row in csv.DictReader(fh):
            if row["target"] != PART2_TARGET:
                continue
            out[(row["sample_design"], row["window"])] = {
                "rows": int(row["rows"]),
                "positive": int(row["positive"]),
                "negative": int(row["negative"]),
            }
    for sample in (PRIMARY_SAMPLE, PART2_SAMPLE):
        for window in ("all", "development", "final_test",
                       "fold1_validation", "fold2_validation"):
            if (sample, window) not in out:
                raise QCFail(
                    f"frozen event-count gate missing {sample}/{window}"
                )
    return out


def read_frozen_sample_summary(repo_root: Path) -> dict[str, dict[str, int]]:
    """Analysis-ready company counts per sample from the frozen Part 3C summary."""
    require_file_hash(
        repo_root, SAMPLE_SUMMARY_REL, SAMPLE_SUMMARY_SHA256,
        label="frozen Part 3C sample summary",
    )
    out: dict[str, dict[str, int]] = {}
    with (repo_root / SAMPLE_SUMMARY_REL).open(
        "r", encoding="utf-8-sig", newline="",
    ) as fh:
        for row in csv.DictReader(fh):
            out[row["sample_design"]] = {
                "rows": int(row["analysis_ready_pairs"]),
                "companies": int(row["analysis_ready_companies"]),
                "positive": int(row["analysis_ready_positive"]),
                "negative": int(row["analysis_ready_negative"]),
            }
    for sample in (PRIMARY_SAMPLE, PART2_SAMPLE):
        if sample not in out:
            raise QCFail(f"frozen sample summary missing {sample}")
    return out


def _fold_membership(roles: set[str]) -> str:
    return "|".join(sorted(roles))


def build_sample_delta(
    repo_root: Path, allow_a: dict[str, Any], allow_b: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Identity-level Rule A vs Rule B delta audit.

    Compares ROW IDENTITIES only — no predictor value and no final-test target
    value is read. Aggregate positive/negative counts come from the frozen
    Stage125 summary artifacts. Fails closed unless Rule B keys are a strict
    subset of Rule A keys with exactly the registered deltas.
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

    ident_a = _identities(allow_a)
    ident_b = _identities(allow_b)
    keys_a, keys_b = set(ident_a), set(ident_b)

    if not keys_b <= keys_a:
        raise QCFail("Rule B keys are not a strict subset of Rule A keys")
    a_only = sorted(keys_a - keys_b)
    b_only = sorted(keys_b - keys_a)
    if len(a_only) != EXPECTED_RULE_A_ONLY_KEYS:
        raise QCFail(f"Rule A-only keys {len(a_only)} != {EXPECTED_RULE_A_ONLY_KEYS}")
    if len(b_only) != EXPECTED_RULE_B_ONLY_KEYS:
        raise QCFail(f"Rule B-only keys {len(b_only)} != {EXPECTED_RULE_B_ONLY_KEYS}")
    if len(keys_a) != EXPECTED_RULE_A_ROWS:
        raise QCFail(f"Rule A identity rows {len(keys_a)} != {EXPECTED_RULE_A_ROWS}")
    if len(keys_b) != EXPECTED_RULE_B_ROWS:
        raise QCFail(f"Rule B identity rows {len(keys_b)} != {EXPECTED_RULE_B_ROWS}")

    rows: list[dict[str, Any]] = []
    for key in sorted(keys_a):
        info = ident_a[key]
        in_b = key in keys_b
        if in_b:
            b_info = ident_b[key]
            if (b_info["temporal_partition"] != info["temporal_partition"]
                    or b_info["fold_membership"] != info["fold_membership"]):
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
            "present_in_main_rule_a": "true",
            "present_in_main_rule_b": "true" if in_b else "false",
            "sample_delta_status": (
                DELTA_STATUS_BOTH if in_b else DELTA_STATUS_RULE_A_ONLY
            ),
        })

    gate = read_frozen_event_counts(repo_root)
    summary = read_frozen_sample_summary(repo_root)

    def _oof(sample: str) -> dict[str, int]:
        f1 = gate[(sample, "fold1_validation")]
        f2 = gate[(sample, "fold2_validation")]
        return {
            "rows": f1["rows"] + f2["rows"],
            "positive": f1["positive"] + f2["positive"],
            "negative": f1["negative"] + f2["negative"],
        }

    a_all, b_all = gate[(PRIMARY_SAMPLE, "all")], gate[(PART2_SAMPLE, "all")]
    a_dev, b_dev = (gate[(PRIMARY_SAMPLE, "development")],
                    gate[(PART2_SAMPLE, "development")])
    a_oof, b_oof = _oof(PRIMARY_SAMPLE), _oof(PART2_SAMPLE)
    a_ft, b_ft = (gate[(PRIMARY_SAMPLE, "final_test")],
                  gate[(PART2_SAMPLE, "final_test")])
    a_comp = summary[PRIMARY_SAMPLE]["companies"]
    b_comp = summary[PART2_SAMPLE]["companies"]

    exact = [
        (a_all["rows"], EXPECTED_RULE_A_ROWS, "rule_a_rows"),
        (a_all["positive"], EXPECTED_RULE_A_POSITIVE, "rule_a_positive"),
        (a_all["negative"], EXPECTED_RULE_A_NEGATIVE, "rule_a_negative"),
        (a_comp, EXPECTED_RULE_A_COMPANIES, "rule_a_companies"),
        (b_all["rows"], EXPECTED_RULE_B_ROWS, "rule_b_rows"),
        (b_all["positive"], EXPECTED_RULE_B_POSITIVE, "rule_b_positive"),
        (b_all["negative"], EXPECTED_RULE_B_NEGATIVE, "rule_b_negative"),
        (b_comp, EXPECTED_RULE_B_COMPANIES, "rule_b_companies"),
        (a_dev["rows"], EXPECTED_RULE_A_DEV_ROWS, "rule_a_dev_rows"),
        (b_dev["rows"], EXPECTED_DEV_ROWS, "rule_b_dev_rows"),
        (a_oof["rows"], EXPECTED_RULE_A_OOF_ROWS, "rule_a_oof_rows"),
        (b_oof["rows"], EXPECTED_OOF_ROWS_PER_FAMILY, "rule_b_oof_rows"),
        (a_ft["rows"], EXPECTED_RULE_A_FINAL_TEST_IDENTITIES, "rule_a_final_test"),
        (b_ft["rows"], EXPECTED_FINAL_TEST_IDENTITIES, "rule_b_final_test"),
    ]
    for got, want, label in exact:
        if got != want:
            raise QCFail(f"sample-delta {label} {got} != {want}")

    def _diff(a: dict[str, int], b: dict[str, int]) -> dict[str, int]:
        return {k: b[k] - a[k] for k in ("rows", "positive", "negative")}

    summary_record = {
        "comparison_basis": "row_identities_only",
        "final_test_values_read": False,
        "aggregate_final_test_counts_source": EVENT_COUNT_GATE_REL,
        "main_rule_a_primary": {
            "analysis_ready": {**a_all, "companies": a_comp},
            "development": a_dev,
            "oof_validation": a_oof,
            "final_test_identities": a_ft["rows"],
        },
        "main_rule_b_listing_robustness": {
            "analysis_ready": {**b_all, "companies": b_comp},
            "development": b_dev,
            "oof_validation": b_oof,
            "final_test_identities": b_ft["rows"],
        },
        "net_difference": {
            "analysis_ready": {**_diff(a_all, b_all), "companies": b_comp - a_comp},
            "development": _diff(a_dev, b_dev),
            "oof_validation": _diff(a_oof, b_oof),
            "final_test_identities": b_ft["rows"] - a_ft["rows"],
        },
        "rule_b_is_strict_subset_of_rule_a": True,
        "rule_a_only_keys": len(a_only),
        "rule_b_only_keys": len(b_only),
        "delta_rows_emitted": len(rows),
    }
    return rows, summary_record


# --------------------------------------------------------------------------- #
# Artifact builders
# --------------------------------------------------------------------------- #

def build_feature_manifest_rows() -> list[dict[str, Any]]:
    rows = []
    for i, feat in enumerate(PART2_FEATURE_ORDER, start=1):
        rows.append({
            "feature_order": i,
            "feature_name": feat,
            "source_column": PART2_FEATURE_SOURCE_COLUMN[feat],
            "transformation": FEATURE_TRANSFORMATION[feat],
            "missingness_indicator_appended": "true",
            "included_in_part2": "true",
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
        "scientific_role": SCIENTIFIC_ROLE,
        "changed_dimension": CHANGED_DIMENSION,
        "scientific_interpretation": SCIENTIFIC_INTERPRETATION,
        "primary_sample": PRIMARY_SAMPLE,
        "sample": PART2_SAMPLE,
        "sample_input_file": RULE_B_ANALYSIS_READY_REL,
        "sample_input_sha256": RULE_B_ANALYSIS_READY_SHA256,
        "primary_sample_input_file": RULE_A_ANALYSIS_READY_REL,
        "primary_sample_input_sha256": RULE_A_ANALYSIS_READY_SHA256,
        "target": PART2_TARGET,
        "target_changed": False,
        "prohibited_target": PROHIBITED_TARGET,
        "feature_set": FEATURE_SET_NAME,
        "feature_set_changed": False,
        "features_exact_order": list(PART2_FEATURE_ORDER),
        "feature_source_columns": dict(sorted(PART2_FEATURE_SOURCE_COLUMN.items())),
        "prohibited_feature": PROHIBITED_FEATURE,
        "base_feature_count": BASE_FEATURE_COUNT,
        "transformed_feature_count": TRANSFORMED_FEATURE_COUNT,
        "imbalance_policy": IMBALANCE_POLICY,
        "imbalance_policy_changed": False,
        "model_families": list(MODEL_FAMILIES),
        "selected_configurations": {
            f: selected[f]["configuration_id"] for f in MODEL_FAMILIES
        },
        "selected_configurations_changed": False,
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
        "temporal_folds_changed": False,
        "locked_final_test_target_years": list(primary.FINAL_TEST_TARGET_YEARS),
        "development_rows_loaded": len(loaded["rows"]),
        "fold_counts": fold_counts,
        "sample_delta": delta_summary,
        "final_test_rows_seen_but_not_parsed": loaded["final_test_rows_seen"],
        "final_test_predictor_rows_loaded": 0,
        "final_test_target_rows_loaded": 0,
        "final_test_evaluations": 0,
        "full_development_refit_performed": False,
        "development_only": True,
    }


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


COMPARISON_CONTRACT_VERSION = (
    "stage126_m1_robustness_part2_primary_comparison_v1"
)


def build_primary_comparison(
    repo_root: Path, metrics_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare Part 2 pooled PR-AUC against the frozen primary pooled PR-AUC.

    Both sides are read from their actual (hash-pinned) sources — no Part 2
    result is hardcoded. Any observed ordering difference is reported
    transparently WITHOUT replacing the primary results, changing the selected
    configurations, selecting a paper winner, or triggering any automatic
    scientific action.
    """
    require_file_hash(
        repo_root, PRIMARY_METRICS_REL,
        PINNED_PRIMARY_ARTIFACTS[PRIMARY_METRICS_REL],
        label="primary development metrics",
    )
    primary_pooled = _pooled_pr_auc_from_metrics_csv(
        repo_root / PRIMARY_METRICS_REL
    )
    part2_pooled = {
        r["model_family"]: float(r["pr_auc"])
        for r in metrics_rows if r["scope"] == "pooled_development_oof"
    }
    missing = set(MODEL_FAMILIES) - set(part2_pooled)
    if missing:
        raise QCFail(f"Part 2 metrics missing pooled rows for: {sorted(missing)}")

    absolute = {
        f: primary._round(part2_pooled[f] - primary_pooled[f])
        for f in MODEL_FAMILIES
    }
    relative = {
        f: primary._round(
            (part2_pooled[f] - primary_pooled[f]) / primary_pooled[f] * 100.0
        )
        for f in MODEL_FAMILIES
    }
    direction = {
        f: ("improved" if absolute[f] > 0 else
            "declined" if absolute[f] < 0 else "unchanged")
        for f in MODEL_FAMILIES
    }
    primary_order = sorted(MODEL_FAMILIES, key=lambda f: -primary_pooled[f])
    part2_order = sorted(MODEL_FAMILIES, key=lambda f: -part2_pooled[f])
    differs = list(primary_order) != list(part2_order)

    return {
        "contract_version": COMPARISON_CONTRACT_VERSION,
        "category_id": CATEGORY_ID,
        "changed_dimension": CHANGED_DIMENSION,
        "scientific_role": "sample_robustness_sensitivity_only",
        "comparison_scope": "pooled_development_oof",
        "comparison_metric": "pr_auc",
        "primary_sample": PRIMARY_SAMPLE,
        "part2_sample": PART2_SAMPLE,
        "primary_metrics_source": PRIMARY_METRICS_REL,
        "primary_metrics_sha256":
            PINNED_PRIMARY_ARTIFACTS[PRIMARY_METRICS_REL],
        "part2_metrics_source": f"{STAGE126_DIR_REL}/{F_METRICS}",
        "primary_pooled_pr_auc": {
            f: primary._round(primary_pooled[f]) for f in MODEL_FAMILIES
        },
        "part2_pooled_pr_auc": {
            f: primary._round(part2_pooled[f]) for f in MODEL_FAMILIES
        },
        "absolute_change": absolute,
        "relative_change_percent": relative,
        "direction_by_family": direction,
        "families_improved": sorted(
            f for f in MODEL_FAMILIES if direction[f] == "improved"
        ),
        "families_declined": sorted(
            f for f in MODEL_FAMILIES if direction[f] == "declined"
        ),
        "all_families_declined": all(v < 0 for v in absolute.values()),
        "all_families_improved": all(v > 0 for v in absolute.values()),
        "primary_observed_ordering": list(primary_order),
        "part2_observed_sensitivity_ordering": list(part2_order),
        "observed_ordering_differs_from_primary": differs,
        "ordering_reported_to_human_supervisor": True,
        "primary_results_replaced": False,
        "primary_ordering_for_confirmatory_claims_changed": False,
        "selected_configurations_changed": False,
        "paper_winner_selected": False,
        "automatic_scientific_action_triggered": False,
        "full_development_refit_authorized": False,
        "final_test_unlocked": False,
        "interpretation": (
            "Listing-timing Rule B sample sensitivity, development folds only. "
            "The observed Part 2 ordering is reported as sample sensitivity and "
            "does not replace the locked primary results, does not alter the "
            "locked primary ordering used for confirmatory interpretation, does "
            "not change the selected configurations, does not select a paper "
            "winner, authorizes no refit, and does not unlock the final test."
        ),
    }


# --------------------------------------------------------------------------- #
# Frozen Stage125 Part 5 successor-compatibility boundary + test provenance
# --------------------------------------------------------------------------- #

PART5_COMPAT_CONTRACT_ID = (
    "stage126_m1_robustness_part2_part5_successor_compatibility"
)
PART5_COMPAT_CONTRACT_VERSION = (
    "stage126_m1_robustness_part2_part5_successor_compatibility_v1"
)
PART5_EXPECTED_LIVE_MISMATCH_FIELDS: tuple[str, ...] = (
    part1.PART5_EXPECTED_LIVE_MISMATCH_FIELDS
)
PART5_EXPECTED_LIVE_MISMATCH_DETAIL = (
    "handoff_mismatch:" + ",".join(PART5_EXPECTED_LIVE_MISMATCH_FIELDS)
)
PART5_FORBIDDEN_MISMATCH_FIELDS: tuple[str, ...] = (
    part1.PART5_FORBIDDEN_MISMATCH_FIELDS
)
PART5_SUCCESSOR_VALIDATION_SURFACES: tuple[str, ...] = (
    "stage126_m1_robustness_part0_decision_lock",
    "stage126_m1_robustness_part1_qc",
    "stage126_m1_robustness_part2_qc",
    "stage126_m1_robustness_part2_completion_lock",
    "ai_handoff_validator",
)
PART5_SOURCE_REL = part1.PART5_SOURCE_REL
PART5_RUNNER_REL = part1.PART5_RUNNER_REL
PART5_TEST_REL = part1.PART5_TEST_REL
PART5_METADATA_REL = part1.PART5_METADATA_REL

# Three-generation successor-test provenance.
#   * historical  : the hash pinned by the frozen Stage125 Part 5 metadata;
#   * part1       : the successor-aware hash as of Part 1 completion;
#   * part2       : the current hash, recomputed on every run.
PART5_HISTORICAL_TEST_SHA256 = part1.PART5_HISTORICAL_TEST_SHA256
PART5_PART1_COMPLETION_TEST_SHA256 = (
    "62cd1593e7bfafdeb1aa1c728f3fb9c22aadf50d3031e2cec964d267e752b189"
)
PART5_EXPECTED_BOOKKEEPING_DRIFT_FILES: tuple[str, ...] = (
    part1.PART5_EXPECTED_BOOKKEEPING_DRIFT_FILES
)
PART5_SCIENTIFIC_OUTPUT_FILES: tuple[str, ...] = part1.PART5_SCIENTIFIC_OUTPUT_FILES


def part5_test_hash_provenance(repo_root: Path) -> dict[str, Any]:
    """Historical / Part-1-completion / current Part 5 test hashes, fail-closed.

    The historical hash must still match what the frozen Part 5 metadata pins
    (proving the frozen metadata itself was not touched). The Part 1
    completion-time hash is retained as history and must never be described as
    the current hash after Part 2. The current hash is always recomputed.
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
            "Part 5 test file hash did not diverge from the Stage125 historical "
            "hash; the successor-aware test separation is missing"
        )
    return {
        "historical": PART5_HISTORICAL_TEST_SHA256,
        "part1_completion": PART5_PART1_COMPLETION_TEST_SHA256,
        "current": current,
        "current_equals_part1_completion":
            current == PART5_PART1_COMPLETION_TEST_SHA256,
    }


def build_part5_successor_compatibility(
    test_hashes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Deterministic record of the frozen Part 5 historical-contract boundary."""
    th = test_hashes or {}
    return {
        "contract_id": PART5_COMPAT_CONTRACT_ID,
        "contract_version": PART5_COMPAT_CONTRACT_VERSION,
        "part2_category_id": CATEGORY_ID,
        "stage125_part5_artifacts_frozen": True,
        "stage125_part5_artifacts_modified": False,
        "stage125_part5_source_modified": False,
        "stage125_part5_runner_modified": False,
        "stage125_part5_live_handoff_check_applicable_after_part2": False,
        "stage125_part5_historical_closure_remains_valid": True,
        "expected_live_mismatch_fields": list(PART5_EXPECTED_LIVE_MISMATCH_FIELDS),
        "expected_live_mismatch_detail": PART5_EXPECTED_LIVE_MISMATCH_DETAIL,
        "forbidden_live_mismatch_fields": list(PART5_FORBIDDEN_MISMATCH_FIELDS),
        "successor_state_validation_surfaces": list(
            PART5_SUCCESSOR_VALIDATION_SURFACES
        ),
        # Explicit three-generation successor-test provenance.
        "stage125_part5_historical_test_file_sha256":
            th.get("historical", PART5_HISTORICAL_TEST_SHA256),
        "stage126_part1_completion_test_file_sha256":
            th.get("part1_completion", PART5_PART1_COMPLETION_TEST_SHA256),
        "stage126_part2_current_test_file_sha256": th.get("current", ""),
        "part1_completion_hash_is_not_the_current_hash": True,
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
        "part1_scientific_artifacts_byte_identical": True,
        "part2_scientific_execution_valid": True,
        "part3_execution_authorized": False,
        "full_development_refit_performed": False,
        "final_test_access_authorized": False,
        "final_test_evaluation_performed": False,
        "rationale": (
            "run_stage125_part5.py --check is a historical successor-state "
            "validator whose live-Handoff assumptions end at the primary "
            "development state. The five-field mismatch after Part 2 is "
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
        "stage125_part5_historical_test_file_sha256":
            th.get("historical", PART5_HISTORICAL_TEST_SHA256),
        "stage126_part1_completion_test_file_sha256":
            th.get("part1_completion", PART5_PART1_COMPLETION_TEST_SHA256),
        "stage126_part2_current_test_file_sha256": th.get("current", ""),
        "part5_historical_test_hash_matches_frozen_metadata": True,
        "part5_part2_current_test_hash_recomputed": True,
        "part5_test_hash_history_explicit": True,
        "part5_expected_bookkeeping_drift_files_exact": True,
        "part5_expected_bookkeeping_drift_files": sorted(
            PART5_EXPECTED_BOOKKEEPING_DRIFT_FILES
        ),
        "part5_scientific_artifact_drift_zero": True,
        "part5_no_unregistered_drift": True,
    }


def verify_part5_frozen_unmodified(repo_root: Path) -> None:
    """Fail closed if the Part 5 source or runner differ from the frozen base."""
    part1.verify_part5_frozen_unmodified(repo_root)


# --------------------------------------------------------------------------- #
# Completion lock
# --------------------------------------------------------------------------- #

COMPLETED_CATEGORY_IDS = [PART1_CATEGORY_ID, CATEGORY_ID]


def build_completion_lock(
    counters: ExecutionCounters, comparison: dict[str, Any],
) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "category_id": CATEGORY_ID,
        "micro_part_id": MICRO_PART_ID,
        "part2_human_authorized": True,
        "part2_execution_completed": True,
        "authorization_consumed": True,
        "development_only": True,
        "sample": PART2_SAMPLE,
        "primary_sample": PRIMARY_SAMPLE,
        "target": PART2_TARGET,
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
        "part3_execution_authorized": False,
        "m1_robustness_execution_authorized": False,
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
        "part1_scientific_artifacts_byte_identical": True,
        # Observed sample-sensitivity ordering (reported, never acted upon).
        "observed_sensitivity_ordering_differs_from_primary":
            comparison["observed_ordering_differs_from_primary"],
        "observed_sensitivity_ordering":
            list(comparison["part2_observed_sensitivity_ordering"]),
        "ordering_reported_to_human_supervisor": True,
        "primary_ordering_for_confirmatory_claims_changed": False,
        "primary_results_replaced": False,
        "paper_winner_selected": False,
        "primary_comparison_artifact": F_COMPARISON,
        "m1_robustness_remaining_parts": "parts_3_to_6_outstanding",
    }


# --------------------------------------------------------------------------- #
# README
# --------------------------------------------------------------------------- #

def _ordering_sentence(comparison: dict[str, Any]) -> str:
    if comparison["observed_ordering_differs_from_primary"]:
        return (
            "The observed Part 2 sensitivity ordering **differs** from the "
            "primary development ordering (see the table below). This does "
            "**not** alter the locked primary ordering used for confirmatory "
            "interpretation, does **not** replace the primary results, and does "
            "**not** select a paper winner."
        )
    return (
        "The observed Part 2 sensitivity ordering **matches** the primary "
        "development ordering. Either way, Part 2 does **not** replace the "
        "primary results and does **not** select a paper winner."
    )


def build_readme(
    metrics_rows: list[dict[str, Any]], comparison: dict[str, Any],
    delta_summary: dict[str, Any], exec_manifest: dict[str, Any],
) -> str:
    lines = [
        "# Stage126 M1 — Robustness Part 2: Listing Rule B Sample",
        "",
        "**Part 2 only. Explicitly human-authorized. Development folds only. "
        "Only the sample changed. No retuning occurred. No full-development "
        "refit occurred. No final-test predictor or target values were "
        "inspected. No final-test evaluation occurred. No SMOTE, SMOTENC or "
        "SHAP was executed. Part 3 is not authorized and not started. Primary "
        "Stage126 artifacts and Part 1 scientific artifacts remain "
        "byte-identical.**",
        "",
        "Part 2 is **sensitivity-analysis evidence only**. "
        + _ordering_sentence(comparison),
        "",
        "## Specification",
        "",
        f"- Category: `{CATEGORY_ID}` (changed dimension: `{CHANGED_DIMENSION}`)",
        f"- Scientific role: `{SCIENTIFIC_ROLE}`",
        f"- Sample: `{PART2_SAMPLE}` (**changed**; primary is "
        f"`{PRIMARY_SAMPLE}`)",
        f"- Input: `{RULE_B_ANALYSIS_READY_REL}` "
        f"(`{RULE_B_ANALYSIS_READY_SHA256}`)",
        f"- Target: `{PART2_TARGET}` (unchanged)",
        f"- Feature set: `{FEATURE_SET_NAME}` — "
        f"{BASE_FEATURE_COUNT} base features, "
        f"{TRANSFORMED_FEATURE_COUNT} transformed columns "
        "(9 imputed continuous + 9 missingness indicators) (unchanged)",
        f"- Imbalance policy: `{IMBALANCE_POLICY}` (unchanged)",
        "- Folds: Fold 1 train 1393-1395 / val 1396-1397; "
        "Fold 2 train 1393-1397 / val 1398-1399 (unchanged)",
        f"- Model seeds: {', '.join(str(s) for s in MODEL_SEEDS)}; "
        f"Logistic deterministic seed {LOGISTIC_DETERMINISTIC_SEED} (unchanged)",
        f"- Model fits: {EXPECTED_MODEL_FIT_CALLS}; "
        f"predictions: {EXPECTED_PREDICTION_CALLS}; tuning searches: 0",
        "",
        "## Nine-feature primary order (unchanged)",
        "",
        "| # | feature | source column | transformation |",
        "|---|---|---|---|",
    ]
    for i, feat in enumerate(PART2_FEATURE_ORDER, start=1):
        lines.append(
            f"| {i} | `{feat}` | `{PART2_FEATURE_SOURCE_COLUMN[feat]}` | "
            f"{FEATURE_TRANSFORMATION[feat]} |"
        )
    b = delta_summary["main_rule_b_listing_robustness"]
    a = delta_summary["main_rule_a_primary"]
    d = delta_summary["net_difference"]
    lines += [
        "",
        f"`{PROHIBITED_FEATURE}` remains audit-only and prohibited.",
        "",
        "## Rule A versus Rule B sample delta (row identities only)",
        "",
        "| scope | Rule A | Rule B | difference |",
        "|---|---|---|---|",
        f"| analysis-ready rows | {a['analysis_ready']['rows']} | "
        f"{b['analysis_ready']['rows']} | {d['analysis_ready']['rows']} |",
        f"| companies | {a['analysis_ready']['companies']} | "
        f"{b['analysis_ready']['companies']} | "
        f"{d['analysis_ready']['companies']} |",
        f"| positive | {a['analysis_ready']['positive']} | "
        f"{b['analysis_ready']['positive']} | {d['analysis_ready']['positive']} |",
        f"| negative | {a['analysis_ready']['negative']} | "
        f"{b['analysis_ready']['negative']} | {d['analysis_ready']['negative']} |",
        f"| development rows | {a['development']['rows']} | "
        f"{b['development']['rows']} | {d['development']['rows']} |",
        f"| OOF validation rows | {a['oof_validation']['rows']} | "
        f"{b['oof_validation']['rows']} | {d['oof_validation']['rows']} |",
        f"| final-test identities | {a['final_test_identities']} | "
        f"{b['final_test_identities']} | {d['final_test_identities']} |",
        "",
        "Rule B keys are a **strict subset** of Rule A keys "
        f"({delta_summary['rule_a_only_keys']} Rule A-only rows, "
        f"{delta_summary['rule_b_only_keys']} Rule B-only rows). The audit "
        "compares **row identities only**; aggregate final-test counts are read "
        f"from the frozen `{EVENT_COUNT_GATE_REL}`, never from row-level "
        f"final-test values. Full detail: `{F_SAMPLE_DELTA}`.",
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
    qp = comparison["part2_pooled_pr_auc"]
    ac = comparison["absolute_change"]
    rc = comparison["relative_change_percent"]
    dirn = comparison["direction_by_family"]
    lines += [
        "",
        "## Observed sample sensitivity vs the primary run (reported)",
        "",
        "- Primary pooled PR-AUC ordering: "
        + " > ".join(f"`{f}`" for f in comparison["primary_observed_ordering"]),
        "- Part 2 observed pooled PR-AUC ordering: "
        + " > ".join(
            f"`{f}`" for f in comparison["part2_observed_sensitivity_ordering"]
        ),
        f"- Observed ordering differs from primary: "
        f"**{str(comparison['observed_ordering_differs_from_primary']).lower()}**",
        "",
        "| model family | primary pooled PR-AUC | Part 2 pooled PR-AUC | "
        "absolute change | relative change | direction |",
        "|---|---|---|---|---|---|",
    ]
    for fam in MODEL_FAMILIES:
        lines.append(
            f"| `{fam}` | {pp[fam]} | {qp[fam]} | {ac[fam]} | {rc[fam]}% | "
            f"{dirn[fam]} |"
        )
    lines += [
        "",
        "This is a **development-only sensitivity finding** produced by changing "
        "the sample and nothing else. It does **not** replace the primary "
        "results, does **not** change the locked primary ordering used for "
        "confirmatory interpretation, and does **not** select a paper winner. "
        "It is reported to the human supervisor and triggered no automatic "
        "scientific action: selected configurations are unchanged, no refit was "
        "authorized, and the final test remains locked. Full detail: "
        f"`{F_COMPARISON}`.",
        "",
        "## Final-test lock",
        "",
        f"- Final-test identities seen but never parsed: "
        f"**{exec_manifest['final_test_rows_seen_but_not_parsed']}**",
        "- Final-test predictor rows loaded: **0**",
        "- Final-test target rows loaded: **0**",
        "- Final-test evaluations: **0**",
        "- Full-development refits: **0**",
        "",
        "## Frozen Stage125 Part 5 live-successor boundary (expected)",
        "",
        "**Stage125 Part 5 remains a frozen, valid historical closure** — its "
        "source, its runner and every `project/stage125/` artifact are "
        "byte-identical. Part 5's *embedded live-Handoff successor check* "
        "terminates at the earlier Stage126 primary-development state and "
        "predates robustness execution. After a truthful Part 2 completion it "
        "reports exactly these five mismatching fields:",
        "",
        *[f"- `{f}`" for f in PART5_EXPECTED_LIVE_MISMATCH_FIELDS],
        "",
        "`run_stage125_part5.py --check` consequently exits 1 **by design**. "
        "This is an **expected historical-contract boundary**, not a scientific "
        f"failure and not Stage125 drift. It is recorded in `{F_PART5_COMPAT}`, "
        "asserted in the Part 2 QC, and explicitly tested.",
        "",
        "The successor-aware Part 5 **test file** has three recorded "
        "generations: the Stage125 historical hash pinned by the frozen Part 5 "
        f"metadata (`{PART5_HISTORICAL_TEST_SHA256}`), the Part 1 "
        f"completion-time hash (`{PART5_PART1_COMPLETION_TEST_SHA256}`), and "
        "the recomputed Part 2 current hash. All three are recorded separately "
        f"in `{F_PART5_COMPAT}`; the Part 1 hash is history, never the current "
        "hash. Replaying the frozen Part 5 build would differ in exactly two "
        "self-describing bookkeeping files — "
        + ", ".join(f"`{f}`" for f in sorted(PART5_EXPECTED_BOOKKEEPING_DRIFT_FILES))
        + " — while **every Part 5 scientific artifact stays byte-identical**.",
        "",
        "## Next",
        "",
        f"The next registered category is `{NEXT_CATEGORY_ID}` (Part 3). "
        "**Part 3 is not authorized and not started** — it requires its own "
        "separate explicit human authorization. Parts 3-6 remain outstanding, "
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
    part5_compat: dict[str, Any], comparison: dict[str, Any],
    delta_rows: list[dict[str, Any]], delta_summary: dict[str, Any],
    oof_rows: list[dict[str, Any]], metrics_rows: list[dict[str, Any]],
    counters: ExecutionCounters, loaded: dict[str, Any],
    primary_observed: dict[str, str], part1_observed: dict[str, str],
    network_attempts: int,
) -> list[dict[str, Any]]:
    a: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        a.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    # ----------------------------- Authorization ---------------------------- #
    add("human_authorization_hash_exact",
        recompute_authorization_sha256(auth_record["human_authorization_text"])
        == HUMAN_AUTHORIZATION_TEXT_SHA256
        == auth_record["human_authorization_text_sha256"])
    add("authorized_category_is_part2",
        auth_record["authorized_category_id"] == CATEGORY_ID)
    add("part2_execution_authorized",
        auth_record["part2_execution_authorized"] is True)
    add("open_unmerged_pr_authorized",
        auth_record["create_open_unmerged_pr_authorized"] is True)
    add("merge_not_authorized", auth_record["merge_authorized"] is False)
    add("part3_not_authorized",
        auth_record["part3_execution_authorized"] is False
        and completion_lock["part3_execution_authorized"] is False)
    add("final_test_not_authorized",
        auth_record["final_test_access_authorized"] is False
        and auth_record["final_test_evaluation_authorized"] is False)
    add("refit_smote_shap_m2_m3_m4_not_authorized",
        auth_record["full_development_refit_authorized"] is False
        and auth_record["smote_authorized"] is False
        and auth_record["smotenc_authorized"] is False
        and auth_record["shap_authorized"] is False
        and auth_record["m2_authorized"] is False
        and auth_record["m3_authorized"] is False
        and auth_record["m4_authorized"] is False)
    add("authorization_consumed",
        completion_lock["authorization_consumed"] is True)
    add("part0_contract_version_exact",
        part0_record["contract_version"]
        == "stage126_m1_robustness_execution_contract_v1")
    add("part0_execution_order_places_part2_second",
        part0_record["execution_order"][1] == CATEGORY_ID)

    # ------------------- One-factor-at-a-time contract ---------------------- #
    add("sample_changed_to_rule_b", exec_manifest["sample"] == PART2_SAMPLE)
    add("primary_sample_recorded",
        exec_manifest["primary_sample"] == PRIMARY_SAMPLE
        and exec_manifest["sample"] != exec_manifest["primary_sample"])
    add("changed_dimension_is_sample",
        exec_manifest["changed_dimension"] == CHANGED_DIMENSION)
    add("target_unchanged",
        exec_manifest["target"] == PART2_TARGET
        and exec_manifest["target_changed"] is False)
    add("persistent_loss_target_not_used",
        exec_manifest["target"] != PROHIBITED_TARGET)
    add("nine_feature_order_unchanged",
        tuple(exec_manifest["features_exact_order"]) == PART2_FEATURE_ORDER
        and tuple(PART2_FEATURE_ORDER)
        == tuple(primary.M1_PRIMARY_FEATURE_ORDER))
    add("feature_set_name_unchanged",
        exec_manifest["feature_set"] == FEATURE_SET_NAME
        == primary.FEATURE_SET_NAME)
    add("base_feature_count_nine",
        exec_manifest["base_feature_count"] == BASE_FEATURE_COUNT)
    add("transformed_feature_count_eighteen",
        exec_manifest["transformed_feature_count"] == TRANSFORMED_FEATURE_COUNT)
    add("prohibited_growth_feature_absent",
        PROHIBITED_FEATURE not in exec_manifest["features_exact_order"]
        and PROHIBITED_FEATURE not in set(
            exec_manifest["feature_source_columns"].values()))
    add("part1_six_feature_set_not_reused",
        set(part1.PART1_FEATURE_ORDER) != set(PART2_FEATURE_ORDER)
        and len(PART2_FEATURE_ORDER) == BASE_FEATURE_COUNT)
    add("selected_configurations_unchanged",
        exec_manifest["selected_configurations_changed"] is False
        and all(
            exec_manifest["selected_configurations"][f]
            == EXPECTED_SELECTED[f]["configuration_id"]
            for f in MODEL_FAMILIES
        ))
    add("imbalance_policy_unchanged",
        exec_manifest["imbalance_policy"] == IMBALANCE_POLICY
        and exec_manifest["imbalance_policy_changed"] is False)
    add("folds_unchanged",
        exec_manifest["temporal_folds_changed"] is False
        and all(
            tuple(exec_manifest["temporal_folds"][name]["train_target_years"])
            == spec["train_target_years"]
            and tuple(
                exec_manifest["temporal_folds"][name]["validation_target_years"])
            == spec["validation_target_years"]
            for name, spec in primary.FOLD_SPEC.items()
        ))
    add("seeds_unchanged",
        tuple(exec_manifest["model_seeds"]) == MODEL_SEEDS
        and exec_manifest["logistic_deterministic_seed"]
        == LOGISTIC_DETERMINISTIC_SEED)
    add("metric_contract_unchanged",
        sorted({r["scope"] for r in metrics_rows})
        == ["fold1_validation", "fold2_validation", "pooled_development_oof"]
        and all(
            {"pr_auc", "roc_auc", "brier_score", "recall_at_10pct",
             "lift_at_10pct"} <= set(r) for r in metrics_rows
        ))
    add("only_sample_changed", completion_lock["only_sample_changed"] is True)

    # ---------------------------- Frozen inputs ----------------------------- #
    add("rule_a_analysis_ready_hash_exact",
        sha256_file(repo_root / RULE_A_ANALYSIS_READY_REL)
        == RULE_A_ANALYSIS_READY_SHA256)
    add("rule_b_analysis_ready_hash_exact",
        sha256_file(repo_root / RULE_B_ANALYSIS_READY_REL)
        == RULE_B_ANALYSIS_READY_SHA256)
    add("split_manifest_hash_exact",
        sha256_file(repo_root / SPLIT_MANIFEST_REL) == SPLIT_MANIFEST_SHA256)
    add("frozen_event_count_gate_hash_exact",
        sha256_file(repo_root / EVENT_COUNT_GATE_REL) == EVENT_COUNT_GATE_SHA256)
    add("primary_artifacts_byte_identical",
        primary_observed == {
            k: PINNED_PRIMARY_ARTIFACTS[k] for k in primary_observed
        })
    add("part1_scientific_artifacts_byte_identical",
        part1_observed == {
            k: PINNED_PART1_SCIENTIFIC_ARTIFACTS[k] for k in part1_observed
        }
        and len(part1_observed) == len(PINNED_PART1_SCIENTIFIC_ARTIFACTS))
    add("part0_decision_contract_hash_exact",
        sha256_file(repo_root / PART0_DECISION_RECORD_REL)
        == PART0_DECISION_RECORD_SHA256)
    add("primary_source_hash_exact",
        sha256_file(repo_root / PRIMARY_SRC_REL) == PRIMARY_SRC_SHA256)

    # ------------------------------- Counts --------------------------------- #
    ar = delta_summary["main_rule_b_listing_robustness"]["analysis_ready"]
    add("rule_b_total_rows", ar["rows"] == EXPECTED_RULE_B_ROWS, str(ar["rows"]))
    add("rule_b_companies", ar["companies"] == EXPECTED_RULE_B_COMPANIES)
    add("rule_b_positive", ar["positive"] == EXPECTED_RULE_B_POSITIVE)
    add("rule_b_negative", ar["negative"] == EXPECTED_RULE_B_NEGATIVE)
    add("development_rows_loaded",
        exec_manifest["development_rows_loaded"] == EXPECTED_DEV_ROWS)
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
        add(f"oof_fold_split[{family}]",
            n1 == EXPECTED_FOLD_COUNTS["fold1_validation"]["rows"]
            and n2 == EXPECTED_FOLD_COUNTS["fold2_validation"]["rows"],
            f"{n1}/{n2}")
    add("metrics_rows_exact", len(metrics_rows) == EXPECTED_METRICS_ROWS,
        str(len(metrics_rows)))
    keys = {(r["model_family"], r["predictor_row_key_t"],
             r["target_row_key_t_plus_1"]) for r in oof_rows}
    add("oof_keys_unique", len(keys) == len(oof_rows))
    probs = [r["predicted_probability"] for r in oof_rows]
    add("oof_probabilities_finite",
        all(isinstance(p, float) and not math.isnan(p) for p in probs))
    add("oof_probabilities_in_bounds", all(0.0 <= p <= 1.0 for p in probs))
    add("oof_sample_column_is_rule_b",
        all(r["sample"] == PART2_SAMPLE for r in oof_rows))
    oof_pos = sum(1 for r in oof_rows
                  if r["model_family"] == MODEL_FAMILIES[0]
                  and r["observed_target"] == 1)
    add("oof_positive_count", oof_pos == EXPECTED_OOF_POSITIVE, str(oof_pos))

    # ------------------------------ Execution -------------------------------- #
    add("model_fit_calls_exact",
        counters.model_fit_calls == EXPECTED_MODEL_FIT_CALLS,
        str(counters.model_fit_calls))
    add("prediction_calls_exact",
        counters.prediction_calls == EXPECTED_PREDICTION_CALLS,
        str(counters.prediction_calls))
    add("tuning_search_calls_zero", counters.tuning_search_calls == 0)
    add("no_retuning", exec_manifest["no_retuning"] is True)
    add("smote_calls_zero", counters.smote_calls == 0)
    add("smotenc_calls_zero", counters.smotenc_calls == 0)
    add("shap_calls_zero", counters.shap_calls == 0)
    add("network_requests_attempted_zero", network_attempts == 0)
    spw = counters.scale_pos_weight_by_fold
    for role, (neg, pos) in EXPECTED_XGB_SCALE_POS_WEIGHT.items():
        add(f"xgboost_scale_pos_weight[{role}]",
            abs(spw.get(role, 0.0) - (neg / pos)) < 1e-12,
            repr(spw.get(role)))

    # ----------------------------- Final-test lock --------------------------- #
    add("final_test_identities_seen_not_parsed",
        loaded["final_test_rows_seen"] == EXPECTED_FINAL_TEST_IDENTITIES,
        str(loaded["final_test_rows_seen"]))
    add("final_test_predictor_rows_loaded_zero",
        loaded["final_test_predictor_rows_loaded"] == 0)
    add("final_test_target_rows_loaded_zero",
        loaded["final_test_target_rows_loaded"] == 0)
    add("final_test_evaluations_zero", counters.final_test_evaluations == 0)
    add("full_development_refits_zero",
        counters.full_development_refits == 0
        and completion_lock["full_development_refit_performed"] is False)
    add("final_test_unlocked_false",
        completion_lock["final_test_unlocked"] is False)
    add("final_test_access_not_authorized",
        completion_lock["final_test_access_authorized"] is False)
    add("no_final_test_year_in_model_rows",
        all(v["target_year"] in primary.DEVELOPMENT_TARGET_YEARS
            for v in loaded["rows"].values()))
    add("no_final_test_year_in_oof",
        all(int(r["target_year"]) not in primary.FINAL_TEST_TARGET_YEARS
            for r in oof_rows))

    # ------------------------------ Sample delta ----------------------------- #
    add("sample_delta_rows_emitted",
        len(delta_rows) == EXPECTED_RULE_A_ROWS, str(len(delta_rows)))
    add("rule_b_strict_subset_of_rule_a",
        delta_summary["rule_b_is_strict_subset_of_rule_a"] is True
        and delta_summary["rule_b_only_keys"] == EXPECTED_RULE_B_ONLY_KEYS)
    add("rule_a_only_rows_exact",
        delta_summary["rule_a_only_keys"] == EXPECTED_RULE_A_ONLY_KEYS,
        str(delta_summary["rule_a_only_keys"]))
    add("sample_delta_status_counts",
        sum(1 for r in delta_rows
            if r["sample_delta_status"] == DELTA_STATUS_RULE_A_ONLY)
        == EXPECTED_RULE_A_ONLY_KEYS
        and sum(1 for r in delta_rows
                if r["sample_delta_status"] == DELTA_STATUS_BOTH)
        == EXPECTED_RULE_B_ROWS)
    nd = delta_summary["net_difference"]
    add("sample_delta_net_rows", nd["analysis_ready"]["rows"] == -19)
    add("sample_delta_net_companies", nd["analysis_ready"]["companies"] == -2)
    add("sample_delta_net_positive", nd["analysis_ready"]["positive"] == -1)
    add("sample_delta_net_negative", nd["analysis_ready"]["negative"] == -18)
    add("sample_delta_development_rows_removed",
        nd["development"]["rows"] == -11
        and nd["development"]["positive"] == 0
        and nd["development"]["negative"] == -11)
    add("sample_delta_oof_rows_removed",
        nd["oof_validation"]["rows"] == -8
        and nd["oof_validation"]["positive"] == 0
        and nd["oof_validation"]["negative"] == -8)
    add("sample_delta_final_test_identities_removed",
        nd["final_test_identities"] == -8)
    add("sample_delta_uses_identities_only",
        delta_summary["comparison_basis"] == "row_identities_only"
        and delta_summary["final_test_values_read"] is False)
    add("sample_delta_no_value_columns",
        all(set(r) == set(SAMPLE_DELTA_COLUMNS) for r in delta_rows))

    # ---------------------------- Interpretation ----------------------------- #
    add("sensitivity_analysis_only",
        completion_lock["scientific_interpretation"] == SCIENTIFIC_INTERPRETATION
        and comparison["scientific_role"] == "sample_robustness_sensitivity_only")
    add("primary_results_not_replaced",
        comparison["primary_results_replaced"] is False
        and completion_lock["primary_results_replaced"] is False
        and completion_lock["replaces_primary_results"] is False)
    add("primary_confirmatory_ordering_not_changed",
        comparison["primary_ordering_for_confirmatory_claims_changed"] is False
        and completion_lock[
            "primary_ordering_for_confirmatory_claims_changed"] is False)
    add("selected_configurations_not_changed",
        comparison["selected_configurations_changed"] is False)
    add("no_paper_winner_selected",
        comparison["paper_winner_selected"] is False
        and completion_lock["selects_paper_winner"] is False
        and completion_lock["paper_winner_selected"] is False)
    add("no_automatic_scientific_action",
        comparison["automatic_scientific_action_triggered"] is False)
    add("ordering_reported_to_human_supervisor",
        comparison["ordering_reported_to_human_supervisor"] is True
        and completion_lock["ordering_reported_to_human_supervisor"] is True)
    add("comparison_derived_not_hardcoded",
        set(comparison["part2_pooled_pr_auc"]) == set(MODEL_FAMILIES)
        and all(
            comparison["part2_pooled_pr_auc"][f] == primary._round(
                next(r["pr_auc"] for r in metrics_rows
                     if r["model_family"] == f
                     and r["scope"] == "pooled_development_oof")
            )
            for f in MODEL_FAMILIES
        ))
    add("m1_robustness_started_true",
        completion_lock["m1_robustness_started"] is True)
    add("m1_robustness_completed_false",
        completion_lock["m1_robustness_completed"] is False)
    add("completed_category_ids_exact",
        completion_lock["completed_category_ids"] == COMPLETED_CATEGORY_IDS)
    add("next_category_is_part3",
        completion_lock["next_category_id"] == NEXT_CATEGORY_ID)
    add("no_standing_execution_authorization",
        completion_lock["m1_robustness_execution_authorized"] is False)

    # --------------------- Part 5 boundary and provenance -------------------- #
    compat = part5_compat
    add("part5_artifacts_frozen_and_unmodified",
        compat["stage125_part5_artifacts_frozen"] is True
        and compat["stage125_part5_artifacts_modified"] is False
        and compat["stage125_part5_source_modified"] is False
        and compat["stage125_part5_runner_modified"] is False)
    add("part5_historical_closure_remains_valid",
        compat["stage125_part5_historical_closure_remains_valid"] is True)
    add("part5_live_check_not_applicable_after_part2",
        compat["stage125_part5_live_handoff_check_applicable_after_part2"]
        is False)
    add("part5_expected_mismatch_fields_exact",
        tuple(compat["expected_live_mismatch_fields"])
        == PART5_EXPECTED_LIVE_MISMATCH_FIELDS)
    add("part5_expected_mismatch_detail_exact",
        compat["expected_live_mismatch_detail"]
        == PART5_EXPECTED_LIVE_MISMATCH_DETAIL)
    add("part5_forbidden_mismatch_fields_declared",
        tuple(compat["forbidden_live_mismatch_fields"])
        == PART5_FORBIDDEN_MISMATCH_FIELDS
        and not (set(PART5_FORBIDDEN_MISMATCH_FIELDS)
                 & set(PART5_EXPECTED_LIVE_MISMATCH_FIELDS)))
    add("part5_test_hash_history_explicit",
        compat["stage125_part5_historical_test_file_sha256"]
        == PART5_HISTORICAL_TEST_SHA256
        and compat["stage126_part1_completion_test_file_sha256"]
        == PART5_PART1_COMPLETION_TEST_SHA256
        and bool(compat["stage126_part2_current_test_file_sha256"]))
    add("part1_hash_not_described_as_current",
        compat["part1_completion_hash_is_not_the_current_hash"] is True)
    add("part5_current_hash_diverges_from_stage125_historical",
        compat["stage126_part2_current_test_file_sha256"]
        != PART5_HISTORICAL_TEST_SHA256)
    add("part5_historical_metadata_not_modified",
        compat["stage125_part5_historical_metadata_modified"] is False)
    add("part5_expected_bookkeeping_drift_files_exact",
        tuple(compat["stage125_part5_expected_bookkeeping_drift_files"])
        == tuple(sorted(PART5_EXPECTED_BOOKKEEPING_DRIFT_FILES)))
    add("part5_no_unregistered_drift",
        len(compat["stage125_part5_expected_bookkeeping_drift_files"]) == 2
        and compat["stage125_part5_scientific_artifact_drift_expected"] is False
        and compat["stage125_part5_scientific_artifact_drift_observed"] is False)
    add("part5_compat_part2_valid_and_part3_unauthorized",
        compat["part2_scientific_execution_valid"] is True
        and compat["part3_execution_authorized"] is False
        and compat["full_development_refit_performed"] is False
        and compat["final_test_access_authorized"] is False
        and compat["final_test_evaluation_performed"] is False)
    add("part5_successor_validation_surfaces_exact",
        tuple(compat["successor_state_validation_surfaces"])
        == PART5_SUCCESSOR_VALIDATION_SURFACES)
    return a


# --------------------------------------------------------------------------- #
# Handoff markers
# --------------------------------------------------------------------------- #

def part2_handoff_markers() -> dict[str, Any]:
    """Workflow markers propagated into the Handoff state (fail-closed).

    Inherits the unchanged Stage126 primary markers and layers the Part 2
    completion state on top. ``m1_robustness_execution_authorized`` is False:
    the consumed Part 2 authorization grants no standing authorization for any
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
        # Part 1 + Part 2 completion state.
        "m1_robustness_started": True,
        "m1_robustness_completed": False,
        "m1_robustness_part1_completed": True,
        "m1_robustness_part2_human_authorized": True,
        "m1_robustness_part2_completed": True,
        "m1_robustness_completed_category_ids": list(COMPLETED_CATEGORY_IDS),
        "m1_robustness_next_category_id": NEXT_CATEGORY_ID,
        "m1_robustness_part3_authorized": False,
        "m1_robustness_execution_authorized": False,
        # Preserved locks.
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
    primary_observed = verify_frozen_integrity(repo_root)
    part1_observed = verify_part1_scientific_artifacts(repo_root)

    auth_record = build_authorization_record()
    selected = load_selected_configurations(repo_root)

    allow_b = build_rule_b_allowlist(repo_root)
    allow_a = build_rule_a_allowlist(repo_root)
    delta_rows, delta_summary = build_sample_delta(repo_root, allow_a, allow_b)

    loaded = load_part2_development_values(repo_root, allow_b)

    folds_data = {
        role: primary._role_matrix(loaded["rows"], allow_b["role_pairs"], role)
        for role in primary.DEV_ROLES
    }
    for role, fd in folds_data.items():
        if fd["X"].shape[1] != BASE_FEATURE_COUNT:
            raise QCFail(
                f"{role} raw matrix has {fd['X'].shape[1]} columns != "
                f"{BASE_FEATURE_COUNT}"
            )
        exp = EXPECTED_FOLD_COUNTS[role]
        if fd["X"].shape[0] != exp["rows"]:
            raise QCFail(f"{role} row count {fd['X'].shape[0]} != {exp['rows']}")
        if int((fd["y"] == 1).sum()) != exp["positive"]:
            raise QCFail(f"{role} positive count mismatch")

    counters = ExecutionCounters()
    oof_rows, predictions = generate_part2_oof(folds_data, selected, counters)
    metrics_rows = compute_part2_metrics(folds_data, selected, predictions)

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
        counters, loaded, allow_b, selected, delta_summary,
    )
    comparison = build_primary_comparison(repo_root, metrics_rows)
    completion_lock = build_completion_lock(counters, comparison)
    test_hashes = part5_test_hash_provenance(repo_root)
    part5_compat = build_part5_successor_compatibility(test_hashes)
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
        F_PART5_COMPAT: _json_str(part5_compat),
        F_README: readme,
    }
    extras = {
        "auth_record": auth_record, "part0_record": part0_record,
        "exec_manifest": exec_manifest, "completion_lock": completion_lock,
        "part5_compat": part5_compat, "comparison": comparison,
        "test_hashes": test_hashes,
        "delta_rows": delta_rows, "delta_summary": delta_summary,
        "oof_rows": oof_rows, "metrics_rows": metrics_rows,
        "counters": counters, "loaded": loaded,
        "primary_observed": primary_observed,
        "part1_observed": part1_observed, "selected": selected,
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
        delta_rows=extras["delta_rows"], delta_summary=extras["delta_summary"],
        oof_rows=extras["oof_rows"], metrics_rows=extras["metrics_rows"],
        counters=extras["counters"], loaded=extras["loaded"],
        primary_observed=extras["primary_observed"],
        part1_observed=extras["part1_observed"],
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
    delta_summary = extras["delta_summary"]
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
        "changed_dimension": CHANGED_DIMENSION,
        "primary_sample": PRIMARY_SAMPLE,
        "sample": PART2_SAMPLE,
        "target": PART2_TARGET,
        "feature_set": FEATURE_SET_NAME,
        "base_feature_count": BASE_FEATURE_COUNT,
        "transformed_feature_count": TRANSFORMED_FEATURE_COUNT,
        "rule_a_analysis_ready_sha256": RULE_A_ANALYSIS_READY_SHA256,
        "rule_b_analysis_ready_sha256": RULE_B_ANALYSIS_READY_SHA256,
        "rule_b_total_rows": EXPECTED_RULE_B_ROWS,
        "rule_b_companies": EXPECTED_RULE_B_COMPANIES,
        "rule_b_positive": EXPECTED_RULE_B_POSITIVE,
        "rule_b_negative": EXPECTED_RULE_B_NEGATIVE,
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
        "sample_delta": delta_summary,
        "selected_configuration_ids": {
            f: EXPECTED_SELECTED[f]["configuration_id"] for f in MODEL_FAMILIES
        },
        "selected_configurations_changed": False,
        "model_seeds": list(MODEL_SEEDS),
        "model_fit_calls": counters.model_fit_calls,
        "prediction_calls": counters.prediction_calls,
        "tuning_search_calls": counters.tuning_search_calls,
        "smote_calls": counters.smote_calls,
        "smotenc_calls": counters.smotenc_calls,
        "shap_calls": counters.shap_calls,
        "network_requests_attempted": network_attempts,
        "final_test_rows_seen_but_not_parsed": loaded["final_test_rows_seen"],
        "final_test_predictor_rows_loaded":
            loaded["final_test_predictor_rows_loaded"],
        "final_test_target_rows_loaded": loaded["final_test_target_rows_loaded"],
        "final_test_evaluations": counters.final_test_evaluations,
        "full_development_refits": counters.full_development_refits,
        "primary_artifact_sha256": dict(sorted(
            extras["primary_observed"].items()
        )),
        "part1_scientific_artifact_sha256": dict(sorted(
            extras["part1_observed"].items()
        )),
        "output_sha256": dict(sorted(content_hashes.items())),
        "part5_successor_compatibility_sha256": content_hashes[F_PART5_COMPAT],
        "primary_comparison_sha256": content_hashes[F_COMPARISON],
        "sample_delta_sha256": content_hashes[F_SAMPLE_DELTA],
        **part5_compatibility_qc_fields(extras["test_hashes"]),
        "assertions": assertions,
        **part2_handoff_markers(),
    }
    qc_text = _json_str(qc)
    qc_hash = sha256_bytes(qc_text.encode("utf-8"))
    meta = {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "description": (
            "Stage126 M1 robustness Part 2 listing Rule B sample "
            "(human-authorized; development folds only; only the sample "
            "changed; no retuning; no full-development refit; final test "
            "locked; no SMOTE/SMOTENC/SHAP; sensitivity analysis only)."
        ),
        "generated_at": source_commit,
        "code_commit": source_commit,
        "source_file_sha256": qc["source_file_sha256"],
        "test_file_sha256": qc["test_file_sha256"],
        "runtime_versions": primary.runtime_versions(),
        "output_files_sha256": dict(
            sorted({**content_hashes, F_QC: qc_hash}.items())
        ),
        "input_files_sha256": {
            RULE_A_ANALYSIS_READY_REL: RULE_A_ANALYSIS_READY_SHA256,
            RULE_B_ANALYSIS_READY_REL: RULE_B_ANALYSIS_READY_SHA256,
            SPLIT_MANIFEST_REL: SPLIT_MANIFEST_SHA256,
            EVENT_COUNT_GATE_REL: EVENT_COUNT_GATE_SHA256,
            SAMPLE_SUMMARY_REL: SAMPLE_SUMMARY_SHA256,
            SELECTED_CONFIGURATIONS_REL: SELECTED_CONFIGURATIONS_SHA256,
        },
        "part1_scientific_artifact_sha256": dict(sorted(
            extras["part1_observed"].items()
        )),
        "part5_successor_compatibility_sha256": content_hashes[F_PART5_COMPAT],
        "primary_comparison_sha256": content_hashes[F_COMPARISON],
        "sample_delta_sha256": content_hashes[F_SAMPLE_DELTA],
        "stage125_part5_historical_test_file_sha256": PART5_HISTORICAL_TEST_SHA256,
        "stage126_part1_completion_test_file_sha256":
            PART5_PART1_COMPLETION_TEST_SHA256,
        "stage126_part2_current_test_file_sha256":
            extras["test_hashes"]["current"],
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
        raise QCFail(f"Part 2 QC failed: {failed} assertions failed")

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
