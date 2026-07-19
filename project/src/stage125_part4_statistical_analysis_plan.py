"""Stage125 Part 4 — Statistical Analysis Plan (contract lock only).

Locks M1–M4 feature definitions/order, sample designs, temporal splits,
preprocessing, model families, hyperparameter budgets, metrics, calibration,
paired uncertainty/multiplicity, SHAP stability, and no-modeling guards.

Offline. Deterministic. Zero network. No model fitting. No Stage126.
Does not inspect final-test predictor values for admission or tuning.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path
from typing import Any

from src import stage125_part3b0_evidence_readiness as p3b0

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

QC_STAGE = "stage125_part4_statistical_analysis_plan"
CURRENT_STAGE = "Stage125"
EXPECTED_BASELINE_COMMIT = "6cb27d6817bf167358d480adbccc1728ad59e109"
CONTRACT_VERSION = "stage125_part4_sap_v2"
CONTRACT_VERSION_V1_HISTORICAL = "stage125_part4_sap_v1"
RESEARCH_ACTION_ID = "stage125-part4-statistical-analysis-plan"
RESEARCH_LAST_COMPLETED = RESEARCH_ACTION_ID
RESEARCH_NEXT = "stage125-part5-readiness-closure"

SRC_REL = "project/src/stage125_part4_statistical_analysis_plan.py"
TEST_REL = "project/tests/test_stage125_part4_statistical_analysis_plan.py"
RUN_REL = "project/run_stage125_part4.py"
REVENUE_GROWTH_FEATURE = "revenue_growth_period_adjusted"

PRIMARY_TARGET = "FD_target_main_t_plus_1"
SECONDARY_TARGET = "FD_target_persistent_loss_robustness_t_plus_1"
ARTICLE141_TARGET = "FD_target_article141_only_t_plus_1"
ALL_TARGETS = (PRIMARY_TARGET, SECONDARY_TARGET, ARTICLE141_TARGET)

PRIMARY_SAMPLE = "main_rule_a_primary"
AVAILABILITY_METHOD = "fixed_regulatory_lag"
APPROVED_LAG_MONTHS = 4

DEVELOPMENT_YEARS = frozenset(range(1393, 1400))
FINAL_TEST_YEARS = frozenset({1400, 1401, 1402})
FOLD1_TRAIN_YEARS = frozenset({1393, 1394, 1395})
FOLD1_VAL_YEARS = frozenset({1396, 1397})
FOLD2_TRAIN_YEARS = frozenset({1393, 1394, 1395, 1396, 1397})
FOLD2_VAL_YEARS = frozenset({1398, 1399})

TUNING_SEEDS = (20260719, 20260720, 20260721)
FINAL_SEEDS = (20260719, 20260720, 20260721, 20260722, 20260723)
SMOTE_SEED = 20260725
BOOTSTRAP_SEED = 20260724
BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_MIN_VALID = 1000
BOOTSTRAP_CLUSTER = "ticker"
HOLM_ALPHA = 0.05
PRIMARY_METRIC = "PR-AUC"
TOPK_FRACTION = 0.10
CALIBRATION_EPSILON = 1e-6
SHAP_MAX_BACKGROUND = 200

M1_COVERAGE_OVERALL_MIN = 0.80
M1_COVERAGE_FOLD_TRAIN_MIN = 0.75
BLOCK_CANDIDATE_COVERAGE_MIN = 0.80
BLOCK_COMMON_COVERAGE_MIN = 0.70
MIN_VAL_POSITIVES = 5
MIN_FINAL_TEST_POSITIVES = 10

F_SAP = "part4_statistical_analysis_plan_stage125.json"
F_FEATURE_SETS = "part4_feature_sets_stage125.csv"
F_EXCLUSIONS = "part4_feature_exclusion_decisions_stage125.csv"
F_SAMPLE_TARGET = "part4_sample_target_matrix_stage125.csv"
F_SPLIT_CONTRACT = "part4_temporal_split_contract_stage125.json"
F_SPLIT_MANIFEST = "part4_temporal_split_manifest_stage125.csv"
F_EVENT_GATE = "part4_event_count_gate_stage125.csv"
F_COVERAGE = "part4_development_feature_coverage_audit_stage125.csv"
F_PREPROCESS = "part4_preprocessing_contract_stage125.json"
F_MODELS = "part4_model_specifications_stage125.json"
F_HYPER = "part4_hyperparameter_budget_stage125.json"
F_METRICS = "part4_metrics_uncertainty_contract_stage125.json"
F_SHAP = "part4_shap_stability_contract_stage125.json"
F_README = "README_STAGE125_PART4_STATISTICAL_ANALYSIS_PLAN.md"
F_RG_DECISION = (
    "part4_revenue_growth_exclusion_revision_decision_stage125.json"
)
F_RG_README = "README_STAGE125_PART4_REVENUE_GROWTH_EXCLUSION_REVISION.md"
F_QC = "stage125_part4_statistical_analysis_plan_qc_report.json"
F_METADATA = "metadata_and_hashes_stage125_part4.json"

TRACKED_CONTENT_FILES = (
    F_SAP, F_FEATURE_SETS, F_EXCLUSIONS, F_SAMPLE_TARGET, F_SPLIT_CONTRACT,
    F_SPLIT_MANIFEST, F_EVENT_GATE, F_COVERAGE, F_PREPROCESS, F_MODELS,
    F_HYPER, F_METRICS, F_SHAP, F_README, F_RG_DECISION, F_RG_README,
)

COVERAGE_AUDIT_COLUMNS = [
    "feature_name", "source_column", "development_rows", "nonmissing_rows",
    "coverage", "positive_row_coverage", "negative_row_coverage",
    "fold1_train_rows", "fold1_train_nonmissing", "fold1_train_coverage",
    "fold1_validation_rows", "fold1_validation_nonmissing",
    "fold1_validation_coverage",
    "fold2_train_rows", "fold2_train_nonmissing", "fold2_train_coverage",
    "fold2_validation_rows", "fold2_validation_nonmissing",
    "fold2_validation_coverage",
    "minimum_fold_training_coverage", "minimum_fold_validation_coverage",
    "admission_status",
]

EVENT_GATE_COLUMNS = [
    "sample_design", "target", "window", "rows", "evaluable_rows",
    "positive", "negative", "missing", "event_gate_decision",
]

SPLIT_MANIFEST_COLUMNS = [
    "sample_design", "predictor_row_key_t", "target_row_key_t_plus_1",
    "ticker", "fiscal_year_t", "target_year", "dataset_split", "temporal_fold",
]

FROZEN_PART3C_INPUTS: dict[str, str] = {
    "project/stage125/part3c_outputs/audited_pairs_main_rule_a_stage125.csv":
        "66ab136701b563a3ab9a5f4d168fce1b2a8790d73bc9b386963377db67f541f4",
    "project/stage125/part3c_outputs/audited_pairs_main_rule_b_stage125.csv":
        "d2d9893e40b0c3bdf876a7447fc5147985fc25c9c5add07264677f6ed817b72c",
    "project/stage125/part3c_outputs/audited_pairs_expanded_rule_a_stage125.csv":
        "23ff63d82bbc1a5a06536783eddfa5113ad988cb0db8c1c9adb004489da22bc9",
    "project/stage125/part3c_outputs/audited_pairs_expanded_rule_b_stage125.csv":
        "56c80ccb0a8bcbb1c030e87c892190579628c298026c6140045cbaf08ff7135f",
    "project/stage125/part3c_outputs/analysis_ready_main_rule_a_stage125.csv":
        "4d04d7d28808573bb28c30848340b676bed3bb6820e67d8bfd4d9d7e1bb3755e",
    "project/stage125/part3c_outputs/analysis_ready_main_rule_b_stage125.csv":
        "5492cf244489cb88919243cf2f19d57663ba9e0b0d377791a3a1c26babc9b480",
    "project/stage125/part3c_outputs/analysis_ready_expanded_rule_a_stage125.csv":
        "fbe9b29c6323b59e830ca9d2dd8c1543b9ef48b21709b01cc56a3989cd2d64d9",
    "project/stage125/part3c_outputs/analysis_ready_expanded_rule_b_stage125.csv":
        "2e61a282165ccdaef37bac61a460c83878f2ae633b10535945cc33897d3b4c22",
}

ANALYSIS_READY_FILES = {
    "main_rule_a_primary":
        "project/stage125/part3c_outputs/analysis_ready_main_rule_a_stage125.csv",
    "main_rule_b_listing_robustness":
        "project/stage125/part3c_outputs/analysis_ready_main_rule_b_stage125.csv",
    "expanded_rule_a_company_scope_robustness":
        "project/stage125/part3c_outputs/analysis_ready_expanded_rule_a_stage125.csv",
    "expanded_rule_b_combined_robustness":
        "project/stage125/part3c_outputs/analysis_ready_expanded_rule_b_stage125.csv",
}

SAMPLE_SPECS: dict[str, dict[str, Any]] = {
    "main_rule_a_primary": {
        "role": "primary",
        "rows": 1012, "companies": 119, "positive": 80, "negative": 932,
        "final_test_pairs": 346, "final_test_positive": 12,
        "final_test_negative": 334,
    },
    "main_rule_b_listing_robustness": {
        "role": "robustness_listing",
        "rows": 993, "companies": 117, "positive": 79, "negative": 914,
    },
    "expanded_rule_a_company_scope_robustness": {
        "role": "robustness_company_scope",
        "rows": 1056, "companies": 124, "positive": 80, "negative": 976,
    },
    "expanded_rule_b_combined_robustness": {
        "role": "robustness_combined",
        "rows": 1035, "companies": 122, "positive": 79, "negative": 956,
    },
}

# Pre-specified coverage-audit candidates (v1 proposed set). Admission uses
# ordinary subset denominators; revenue_growth fails the fold-training gate.
M1_COVERAGE_AUDIT_CANDIDATES = [
    "log_total_assets",
    "leverage_ratio",
    "current_ratio",
    "roa_period_adjusted",
    "ocf_to_assets_period_adjusted",
    "asset_turnover_period_adjusted",
    "operating_margin_period_adjusted",
    REVENUE_GROWTH_FEATURE,
    "financial_expense_to_assets_period_adjusted",
    "accumulated_loss_to_capital_ratio",
]

M1_PRIMARY_FEATURE_ORDER = [
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

M1_FEATURE_SOURCE = {
    "log_total_assets": "total_assets",
    "leverage_ratio": "leverage_ratio",
    "current_ratio": "current_ratio",
    "roa_period_adjusted": "roa_period_adjusted",
    "ocf_to_assets_period_adjusted": "ocf_to_assets_period_adjusted",
    "asset_turnover_period_adjusted": "asset_turnover_period_adjusted",
    "operating_margin_period_adjusted": "operating_margin_period_adjusted",
    REVENUE_GROWTH_FEATURE: REVENUE_GROWTH_FEATURE,
    "financial_expense_to_assets_period_adjusted":
        "financial_expense_to_assets_period_adjusted",
    "accumulated_loss_to_capital_ratio": "accumulated_loss_to_capital_ratio",
}

M1_TARGET_PROXIMITY_ROBUSTNESS = [
    "log_total_assets",
    "current_ratio",
    "roa_period_adjusted",
    "asset_turnover_period_adjusted",
    "operating_margin_period_adjusted",
    "financial_expense_to_assets_period_adjusted",
]

M1_TARGET_PROXIMITY_REMOVED = [
    "leverage_ratio",
    "ocf_to_assets_period_adjusted",
    "accumulated_loss_to_capital_ratio",
]

M2_BLOCK = ["equity_return_window", "realized_volatility", "amihud_illiquidity"]
M3_BLOCK = ["cpi_inflation", "fx_change_official", "policy_financing_rate"]
M4_BLOCK = [
    "audit_opinion_type", "going_concern_flag", "audit_lag_days", "board_size",
]

FORBIDDEN_TARGET_DERIVED = frozenset({
    "loss_dummy", "equity_negative_dummy", "distressed_target_reviewed",
    "FD_target_main", "FD_target_article141_only",
    "FD_target_persistent_loss_robustness",
    "FD_target_main_t_plus_1", "FD_target_article141_only_t_plus_1",
    "FD_target_persistent_loss_robustness_t_plus_1",
    "fd_article141_direct", "fd_accumulated_loss", "fd_negative_equity",
    "fd_ocf_high_leverage", "target_status_reviewed",
    "distressed_flag_source_reviewed", "positive_target_reasons",
    "target_missing_reason",
})

M1_EXCLUSIONS: list[dict[str, str]] = [
    {"feature_name": "current_assets",
     "exclusion_reasons": "numerator/denominator duplication; scale redundancy"},
    {"feature_name": "current_liabilities",
     "exclusion_reasons": "numerator/denominator duplication; scale redundancy"},
    {"feature_name": "debt_to_equity",
     "exclusion_reasons": "high conceptual overlap; unstable denominator"},
    {"feature_name": "equity",
     "exclusion_reasons": "raw-level size dependence; scale redundancy"},
    {"feature_name": "equity_ratio",
     "exclusion_reasons":
         "exact or near accounting identity; high conceptual overlap"},
    {"feature_name": "gross_margin_period_adjusted",
     "exclusion_reasons":
         "high conceptual overlap; parsimony under low event count"},
    {"feature_name": "gross_profit_period_adjusted",
     "exclusion_reasons":
         "raw-level size dependence; numerator/denominator duplication"},
    {"feature_name": "net_income_growth_period_adjusted",
     "exclusion_reasons":
         "duplicate growth definition; parsimony under low event count"},
    {"feature_name": "net_income_period_adjusted",
     "exclusion_reasons":
         "raw-level size dependence; target-component proximity"},
    {"feature_name": "net_margin_period_adjusted",
     "exclusion_reasons":
         "high conceptual overlap; parsimony under low event count"},
    {"feature_name": "operating_cash_flow_period_adjusted",
     "exclusion_reasons":
         "numerator/denominator duplication; raw-level size dependence"},
    {"feature_name": "operating_profit_period_adjusted",
     "exclusion_reasons":
         "numerator/denominator duplication; raw-level size dependence"},
    {"feature_name": "profit_margin_period_adjusted",
     "exclusion_reasons":
         "high conceptual overlap; parsimony under low event count"},
    {"feature_name": "registered_capital",
     "exclusion_reasons": "raw-level size dependence; scale redundancy"},
    {"feature_name": "revenue_period_adjusted",
     "exclusion_reasons":
         "raw-level size dependence; numerator/denominator duplication"},
    {"feature_name": "roe_period_adjusted",
     "exclusion_reasons": "unstable denominator; high conceptual overlap"},
    {"feature_name": "sales_growth_period_adjusted",
     "exclusion_reasons": "duplicate growth definition"},
    {"feature_name": "total_assets",
     "exclusion_reasons":
         "raw-level size dependence; replaced by log_total_assets transform"},
    {"feature_name": "total_liabilities",
     "exclusion_reasons": "raw-level size dependence; scale redundancy"},
    {"feature_name": "accumulated_loss",
     "exclusion_reasons":
         "raw-level size dependence; target-component proximity"},
    {"feature_name": "financial_expense_period_adjusted",
     "exclusion_reasons":
         "numerator/denominator duplication; raw-level size dependence"},
    {"feature_name": "financial_expense_to_revenue_period_adjusted",
     "exclusion_reasons": "high conceptual overlap; unstable denominator"},
    {
        "feature_name": REVENUE_GROWTH_FEATURE,
        "exclusion_reasons": (
            "minimum temporal-fold training coverage below locked threshold; "
            "Fold 1 training coverage 148/245 = 0.6040816327; "
            "parsimony under low event count"
        ),
        "admission_status": "rejected_m1_primary_coverage_gate_failed",
        "decision": "rejected_m1_primary_coverage_gate_failed",
    },
]

FORBIDDEN_SURFACE_EXACT = (
    "project/src/stage126_m1_financial_baseline.py",
    "project/run_stage126.py",
    "project/stage126",
)


class QCFail(RuntimeError):
    """Fail-closed Part 4 QC error."""


class AuthorizationError(QCFail):
    """Policy / authorization violation."""


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
        writer.writerow({k: row.get(k, "") for k in header})
    return buf.getvalue()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


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
    return head


def require_file_hash(repo_root: Path, rel: str, expected: str) -> str:
    path = repo_root / rel
    if not path.is_file():
        raise QCFail(f"missing Part 3C input: {rel}")
    got = sha256_file(path)
    if got != expected:
        raise QCFail(f"Part 3C input hash mismatch: {rel}")
    return got


def frozen_part3c_hashes(repo_root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel, expected in FROZEN_PART3C_INPUTS.items():
        out[rel] = require_file_hash(repo_root, rel, expected)
    return out


def _read_csv_dicts(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    s = str(value).strip()
    return s == "" or s.lower() in {"nan", "none", "null", "missing"}


def classify_target_state(value: Any) -> str:
    """Strict three-state target parser. Missing is never negative."""
    if value is None:
        return "missing"
    if isinstance(value, float):
        # NaN must not fall through to string conversion quirks.
        if value != value:  # noqa: PLR0124 — NaN check
            return "missing"
        if value == 1.0:
            return "positive"
        if value == 0.0:
            return "negative"
        return "missing"
    if isinstance(value, int) and not isinstance(value, bool):
        if value == 1:
            return "positive"
        if value == 0:
            return "negative"
        return "missing"
    s = str(value).strip()
    if s in {"1", "1.0"}:
        return "positive"
    if s in {"0", "0.0"}:
        return "negative"
    return "missing"


def _is_positive(value: Any) -> bool:
    return classify_target_state(value) == "positive"


def _is_negative(value: Any) -> bool:
    return classify_target_state(value) == "negative"


def count_target_states(values: list[Any]) -> dict[str, int]:
    positive = negative = missing = 0
    for value in values:
        state = classify_target_state(value)
        if state == "positive":
            positive += 1
        elif state == "negative":
            negative += 1
        else:
            missing += 1
    rows = positive + negative + missing
    return {
        "rows": rows,
        "evaluable_rows": positive + negative,
        "positive": positive,
        "negative": negative,
        "missing": missing,
    }


def _assert(
    assertions: list[dict[str, str]], name: str, ok: bool, detail: str,
) -> None:
    assertions.append({
        "assertion": name,
        "status": "PASS" if ok else "FAIL",
        "detail": detail,
    })


# --------------------------------------------------------------------------- #
# Guards
# --------------------------------------------------------------------------- #

def reject_random_split(method: str) -> None:
    if method.lower() in {"random", "shuffle", "kfold", "stratified_kfold"}:
        raise AuthorizationError(f"random split attempted: {method}")


def reject_final_test_year_change(years: set[int] | frozenset[int]) -> None:
    if set(years) != set(FINAL_TEST_YEARS):
        raise AuthorizationError(
            f"final test year changed: {sorted(years)} != "
            f"{sorted(FINAL_TEST_YEARS)}"
        )


def reject_validation_overlap(train: set[int], val: set[int]) -> None:
    overlap = set(train) & set(val)
    if overlap:
        raise AuthorizationError(f"validation-year overlap: {sorted(overlap)}")


def reject_train_after_validation(train: set[int], val: set[int]) -> None:
    if train and val and max(train) >= min(val):
        raise AuthorizationError(
            f"train year later than validation year: "
            f"max(train)={max(train)} >= min(val)={min(val)}"
        )


def reject_growth_denominator_exception(
    *,
    exclude_first_observed_fiscal_year_from_fold_denominator: bool = False,
    structural_first_observation_denominator_adjustment: bool = False,
    growth_coverage_exception: bool = False,
) -> None:
    if (
        exclude_first_observed_fiscal_year_from_fold_denominator
        or structural_first_observation_denominator_adjustment
        or growth_coverage_exception
    ):
        raise AuthorizationError(
            "growth coverage denominator exception forbidden under "
            "stage125_part4_sap_v2"
        )


def reject_coverage_denominator_mutation(
    *,
    subset_row_count: int,
    denominator_used: int,
    label: str,
) -> None:
    if denominator_used != subset_row_count:
        raise AuthorizationError(
            f"coverage denominator mutation: {label} "
            f"denominator_used={denominator_used} != "
            f"subset_row_count={subset_row_count}"
        )


def reject_final_test_claim_gate_mutating_feature_admission(
    *,
    claim_gate_controls_feature_admission: bool,
) -> None:
    if claim_gate_controls_feature_admission:
        raise AuthorizationError(
            "final-test claim threshold cannot change feature admission"
        )


def reject_final_test_claim_gate_mutating_split(
    *,
    claim_gate_controls_temporal_split: bool,
) -> None:
    if claim_gate_controls_temporal_split:
        raise AuthorizationError(
            "final-test claim threshold cannot change temporal split"
        )


def validate_locked_folds() -> None:
    reject_random_split("target_year_temporal")
    reject_final_test_year_change(FINAL_TEST_YEARS)
    for train, val in (
        (FOLD1_TRAIN_YEARS, FOLD1_VAL_YEARS),
        (FOLD2_TRAIN_YEARS, FOLD2_VAL_YEARS),
    ):
        reject_validation_overlap(set(train), set(val))
        reject_train_after_validation(set(train), set(val))


def assert_no_model_imports_in_source(repo_root: Path) -> None:
    src_path = repo_root / SRC_REL
    if not src_path.is_file():
        return
    src = src_path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    banned_names = {
        "LogisticRegression", "RandomForestClassifier", "XGBClassifier",
        "GridSearchCV", "RandomizedSearchCV", "SMOTE",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name in {"xgboost", "shap", "imblearn"} or name.startswith(
                    ("sklearn.linear_model", "sklearn.ensemble",
                     "sklearn.model_selection")
                ):
                    raise AuthorizationError(f"model import attempt: {name}")
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            names = {a.name for a in node.names}
            hit = names & banned_names
            if hit:
                raise AuthorizationError(f"model import attempt: {sorted(hit)}")
            if mod in {"xgboost", "shap", "imblearn.over_sampling"}:
                raise AuthorizationError(f"model import attempt: {mod}")
            if mod.startswith("sklearn.") and (
                "linear_model" in mod
                or "ensemble" in mod
                or "model_selection" in mod
            ):
                raise AuthorizationError(f"model import attempt: {mod}")


def assert_feature_order(
    actual: list[str], expected: list[str], label: str,
) -> None:
    if actual != expected:
        raise QCFail(f"{label} feature order mutation: {actual} != {expected}")


def assert_no_unapproved_m1(features: list[str]) -> None:
    allowed = set(M1_PRIMARY_FEATURE_ORDER)
    extra = [f for f in features if f not in allowed]
    if extra:
        raise QCFail(f"unapproved feature entering M1: {extra}")
    missing = [f for f in M1_PRIMARY_FEATURE_ORDER if f not in features]
    if missing:
        raise QCFail(f"approved feature silently removed: {missing}")


def assert_no_target_derived(features: list[str]) -> None:
    bad = [f for f in features if f in FORBIDDEN_TARGET_DERIVED]
    if bad:
        raise QCFail(f"target-derived field entering predictor set: {bad}")


def feature_present(row: dict[str, str], feature_name: str) -> bool:
    source = M1_FEATURE_SOURCE[feature_name]
    raw = row.get(source, "")
    if _is_missing(raw):
        return False
    if feature_name == "log_total_assets":
        try:
            return float(raw) > 0.0
        except ValueError:
            return False
    return True


def first_fiscal_year_by_ticker(rows: list[dict[str, str]]) -> dict[str, int]:
    first: dict[str, int] = {}
    for row in rows:
        t = row["ticker"]
        y = int(row["fiscal_year_t"])
        if t not in first or y < first[t]:
            first[t] = y
    return first


# --------------------------------------------------------------------------- #
# Coverage / counts
# --------------------------------------------------------------------------- #

def load_analysis_ready(repo_root: Path, sample: str) -> list[dict[str, str]]:
    rel = ANALYSIS_READY_FILES[sample]
    rows = _read_csv_dicts(repo_root / rel)
    spec = SAMPLE_SPECS[sample]
    if len(rows) != spec["rows"]:
        raise QCFail(
            f"sample-count mutation: {sample} rows={len(rows)} "
            f"expected={spec['rows']}"
        )
    companies = {r["ticker"] for r in rows}
    if len(companies) != spec["companies"]:
        raise QCFail(
            f"sample-count mutation: {sample} companies={len(companies)} "
            f"expected={spec['companies']}"
        )
    counts = count_target_states([r[PRIMARY_TARGET] for r in rows])
    pos = counts["positive"]
    neg = counts["negative"]
    if pos != spec["positive"] or neg != spec["negative"]:
        raise QCFail(
            f"target-count mutation: {sample} pos/neg={pos}/{neg} "
            f"expected={spec['positive']}/{spec['negative']}"
        )
    ramp = [
        r for r in rows
        if r["ticker"] == "رمپنا" and str(r["fiscal_year_t"]) == "1396"
    ]
    if ramp:
        raise QCFail("رمپنا re-entering analysis-ready data")
    return rows


def development_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [r for r in rows if int(r["target_year"]) in DEVELOPMENT_YEARS]


def final_test_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [r for r in rows if int(r["target_year"]) in FINAL_TEST_YEARS]


def _subset_coverage(
    subset: list[dict[str, str]], feat: str,
) -> tuple[int, int, float]:
    """Ordinary coverage: denominator = all rows in the subset."""
    n = len(subset)
    if n == 0:
        return 0, 0, 0.0
    reject_coverage_denominator_mutation(
        subset_row_count=n, denominator_used=n, label=feat,
    )
    nonmiss = sum(1 for r in subset if feature_present(r, feat))
    return nonmiss, n, nonmiss / n


def compute_m1_coverage(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Development-only M1 candidate coverage; never uses final-test features.

    Audits all pre-specified candidates. Rejected candidates remain in the
    audit. Only final admitted M1 features must pass coverage gates.
    """
    reject_growth_denominator_exception()
    dev = development_rows(rows)
    if not dev:
        raise QCFail("no development rows for coverage")
    fold_sets = {
        "fold1_train": [
            r for r in dev if int(r["target_year"]) in FOLD1_TRAIN_YEARS
        ],
        "fold1_validation": [
            r for r in dev if int(r["target_year"]) in FOLD1_VAL_YEARS
        ],
        "fold2_train": [
            r for r in dev if int(r["target_year"]) in FOLD2_TRAIN_YEARS
        ],
        "fold2_validation": [
            r for r in dev if int(r["target_year"]) in FOLD2_VAL_YEARS
        ],
    }
    # Locked ordinary denominators for the primary sample development folds.
    expected_denominators = {
        "fold1_train": 245,
        "fold1_validation": 205,
        "fold2_train": 450,
        "fold2_validation": 216,
        "development": 666,
    }
    if len(dev) != expected_denominators["development"]:
        raise QCFail(
            f"coverage denominator mutation: development rows={len(dev)} "
            f"expected={expected_denominators['development']}"
        )
    for key, expected_n in expected_denominators.items():
        if key == "development":
            continue
        got_n = len(fold_sets[key])
        if got_n != expected_n:
            raise QCFail(
                f"coverage denominator mutation: {key} rows={got_n} "
                f"expected={expected_n}"
            )

    out: list[dict[str, Any]] = []
    for feat in M1_COVERAGE_AUDIT_CANDIDATES:
        source = M1_FEATURE_SOURCE[feat]
        nonmiss_n, dev_n, overall = _subset_coverage(dev, feat)
        pos_rows = [
            r for r in dev if classify_target_state(r[PRIMARY_TARGET]) == "positive"
        ]
        neg_rows = [
            r for r in dev if classify_target_state(r[PRIMARY_TARGET]) == "negative"
        ]
        pos_nm = sum(1 for r in pos_rows if feature_present(r, feat))
        neg_nm = sum(1 for r in neg_rows if feature_present(r, feat))

        fold_stats: dict[str, tuple[int, int, float]] = {
            key: _subset_coverage(subset, feat)
            for key, subset in fold_sets.items()
        }
        min_train = min(
            fold_stats["fold1_train"][2], fold_stats["fold2_train"][2],
        )
        min_val = min(
            fold_stats["fold1_validation"][2],
            fold_stats["fold2_validation"][2],
        )
        ok = (
            overall >= M1_COVERAGE_OVERALL_MIN
            and min_train >= M1_COVERAGE_FOLD_TRAIN_MIN
        )
        if ok:
            status = "admitted_m1_primary"
        else:
            status = "rejected_m1_primary_coverage_gate_failed"
        f1t_nm, f1t_n, f1t_c = fold_stats["fold1_train"]
        f1v_nm, f1v_n, f1v_c = fold_stats["fold1_validation"]
        f2t_nm, f2t_n, f2t_c = fold_stats["fold2_train"]
        f2v_nm, f2v_n, f2v_c = fold_stats["fold2_validation"]
        out.append({
            "feature_name": feat,
            "source_column": source,
            "development_rows": str(dev_n),
            "nonmissing_rows": str(nonmiss_n),
            "coverage": f"{overall:.10f}",
            "positive_row_coverage": (
                f"{(pos_nm / len(pos_rows)) if pos_rows else 0.0:.10f}"
            ),
            "negative_row_coverage": (
                f"{(neg_nm / len(neg_rows)) if neg_rows else 0.0:.10f}"
            ),
            "fold1_train_rows": str(f1t_n),
            "fold1_train_nonmissing": str(f1t_nm),
            "fold1_train_coverage": f"{f1t_c:.10f}",
            "fold1_validation_rows": str(f1v_n),
            "fold1_validation_nonmissing": str(f1v_nm),
            "fold1_validation_coverage": f"{f1v_c:.10f}",
            "fold2_train_rows": str(f2t_n),
            "fold2_train_nonmissing": str(f2t_nm),
            "fold2_train_coverage": f"{f2t_c:.10f}",
            "fold2_validation_rows": str(f2v_n),
            "fold2_validation_nonmissing": str(f2v_nm),
            "fold2_validation_coverage": f"{f2v_c:.10f}",
            "minimum_fold_training_coverage": f"{min_train:.10f}",
            "minimum_fold_validation_coverage": f"{min_val:.10f}",
            "admission_status": status,
        })
        if feat in M1_PRIMARY_FEATURE_ORDER and not ok:
            raise QCFail(
                f"M1 coverage gate failed for admitted feature {feat}: "
                f"overall={overall:.4f} min_fold_train={min_train:.4f}"
            )
        if feat == REVENUE_GROWTH_FEATURE and status == "admitted_m1_primary":
            raise QCFail(
                "revenue_growth incorrectly admitted under ordinary "
                "fold-training coverage denominator"
            )
    return out


def assign_temporal_roles(target_year: int) -> list[tuple[str, str]]:
    y = target_year
    roles: list[tuple[str, str]] = []
    if y in FINAL_TEST_YEARS:
        roles.append(("final_test", "locked_final_test"))
        return roles
    if y in DEVELOPMENT_YEARS:
        if y in FOLD1_TRAIN_YEARS:
            roles.append(("development", "fold1_train"))
        if y in FOLD1_VAL_YEARS:
            roles.append(("development", "fold1_validation"))
        if y in FOLD2_TRAIN_YEARS:
            roles.append(("development", "fold2_train"))
        if y in FOLD2_VAL_YEARS:
            roles.append(("development", "fold2_validation"))
    return roles


def build_split_manifest(
    sample_rows: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    manifest: list[dict[str, str]] = []
    for sample in sorted(sample_rows):
        for row in sample_rows[sample]:
            y = int(row["target_year"])
            for dataset_split, temporal_fold in assign_temporal_roles(y):
                manifest.append({
                    "sample_design": sample,
                    "predictor_row_key_t": row["predictor_row_key_t"],
                    "target_row_key_t_plus_1": row["target_row_key_t_plus_1"],
                    "ticker": row["ticker"],
                    "fiscal_year_t": str(row["fiscal_year_t"]),
                    "target_year": str(y),
                    "dataset_split": dataset_split,
                    "temporal_fold": temporal_fold,
                })
    for row in manifest:
        for forbidden in ALL_TARGETS:
            if forbidden in row:
                raise QCFail(
                    "final-test row-level target leaked into split manifest"
                )
        if set(row) - set(SPLIT_MANIFEST_COLUMNS):
            raise QCFail("split manifest contains disallowed columns")
    manifest.sort(key=lambda r: (
        r["sample_design"], r["temporal_fold"], r["ticker"],
        int(r["fiscal_year_t"]), r["predictor_row_key_t"],
    ))
    return manifest


def build_event_counts(
    sample_rows: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    windows = [
        ("development", DEVELOPMENT_YEARS),
        ("fold1_train", FOLD1_TRAIN_YEARS),
        ("fold1_validation", FOLD1_VAL_YEARS),
        ("fold2_train", FOLD2_TRAIN_YEARS),
        ("fold2_validation", FOLD2_VAL_YEARS),
        ("final_test", FINAL_TEST_YEARS),
        ("all", None),
    ]
    rows_out: list[dict[str, str]] = []
    for sample, data in sorted(sample_rows.items()):
        for target in ALL_TARGETS:
            for window_name, years in windows:
                if years is None:
                    subset = data
                else:
                    subset = [
                        r for r in data if int(r["target_year"]) in years
                    ]
                counts = count_target_states([r[target] for r in subset])
                if counts["rows"] != (
                    counts["positive"] + counts["negative"] + counts["missing"]
                ):
                    raise QCFail("target event-count reconciliation failed")
                if counts["evaluable_rows"] != (
                    counts["positive"] + counts["negative"]
                ):
                    raise QCFail("evaluable_rows reconciliation failed")
                # Missing must never be folded into negative.
                if counts["negative"] > counts["evaluable_rows"]:
                    raise QCFail("missing counted as negative")
                decision = "eligible_for_comparative_claims"
                pos = counts["positive"]
                if window_name == "final_test":
                    # Claim eligibility only — never feature admission.
                    if pos < MIN_FINAL_TEST_POSITIVES:
                        decision = (
                            "distributional_descriptive_robustness_only;"
                            "no_comparative_predictive_performance_claim;"
                            "no_inferential_model_ranking"
                        )
                    else:
                        decision = "final_test_inferential_claim_eligible"
                elif window_name in {"fold1_validation", "fold2_validation"}:
                    if pos < MIN_VAL_POSITIVES:
                        decision = "development_comparison_not_supported"
                    else:
                        decision = "development_comparison_feasibility_met"
                rows_out.append({
                    "sample_design": sample,
                    "target": target,
                    "window": window_name,
                    "rows": str(counts["rows"]),
                    "evaluable_rows": str(counts["evaluable_rows"]),
                    "positive": str(counts["positive"]),
                    "negative": str(counts["negative"]),
                    "missing": str(counts["missing"]),
                    "event_gate_decision": decision,
                })
    return rows_out


# --------------------------------------------------------------------------- #
# Contract builders
# --------------------------------------------------------------------------- #

def build_feature_set_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for i, feat in enumerate(M1_PRIMARY_FEATURE_ORDER, start=1):
        if feat == "log_total_assets":
            notes = (
                "log_total_assets=ln(total_assets) if total_assets>0 "
                "else missing; do_not_overwrite_total_assets"
            )
        elif feat == "financial_expense_to_assets_period_adjusted":
            notes = (
                "source_sign_preserved_expenses_nonpositive_in_frozen_data;"
                "do_not_abs_or_reverse_sign"
            )
        else:
            notes = "frozen_part3c_value"
        rows.append({
            "feature_set": "M1_PRIMARY_FEATURE_ORDER",
            "block": "M1",
            "position": str(i),
            "feature_name": feat,
            "source_column": M1_FEATURE_SOURCE[feat],
            "status": "approved_primary",
            "notes": notes,
        })
    for i, feat in enumerate(M1_TARGET_PROXIMITY_ROBUSTNESS, start=1):
        rows.append({
            "feature_set": "M1_TARGET_PROXIMITY_ROBUSTNESS",
            "block": "M1_robustness",
            "position": str(i),
            "feature_name": feat,
            "source_column": M1_FEATURE_SOURCE[feat],
            "status": "approved_secondary_robustness",
            "notes": (
                "removes_target_proximal_predictors; not_leakage; "
                "lagged_t_predictors_permitted_for_t_plus_1_target"
            ),
        })
    for block_name, block_feats, status in (
        ("M2", M2_BLOCK, "conditional_not_collected"),
        ("M3", M3_BLOCK, "not_admitted_no_authoritative_cbi_endpoint"),
        ("M4", M4_BLOCK, "conditional_future_variable_level_gate"),
    ):
        for i, feat in enumerate(block_feats, start=1):
            rows.append({
                "feature_set": f"{block_name}_BLOCK",
                "block": block_name,
                "position": str(i),
                "feature_name": feat,
                "source_column": feat,
                "status": status,
                "notes": "no_extraction_in_part4",
            })
    return rows


def build_exclusion_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in M1_EXCLUSIONS:
        decision = item.get("decision", "excluded_from_m1_primary")
        admission = item.get("admission_status", decision)
        rows.append({
            "feature_name": item["feature_name"],
            "decision": decision,
            "admission_status": admission,
            "exclusion_reasons": item["exclusion_reasons"],
            "retained_in_frozen_datasets": "true",
            "retained_in_audit": "true",
            "available_in_audit_surface": "true",
            "deleted_from_source_data": "false",
        })
    return rows


def build_sample_target_matrix(
    sample_rows: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for sample, data in sorted(sample_rows.items()):
        role = SAMPLE_SPECS[sample]["role"]
        for target in ALL_TARGETS:
            counts = count_target_states([r[target] for r in data])
            if target == PRIMARY_TARGET:
                target_role = "primary"
            elif target == SECONDARY_TARGET:
                target_role = "secondary_robustness"
            else:
                target_role = "article141_only_robustness"
            out.append({
                "sample_design": sample,
                "sample_role": role,
                "target": target,
                "target_role": target_role,
                "rows": str(counts["rows"]),
                "evaluable_rows": str(counts["evaluable_rows"]),
                "companies": str(len({r["ticker"] for r in data})),
                "positive": str(counts["positive"]),
                "negative": str(counts["negative"]),
                "missing": str(counts["missing"]),
                "paper_primary_result": (
                    "true"
                    if sample == PRIMARY_SAMPLE and target == PRIMARY_TARGET
                    else "false"
                ),
            })
    return out


def build_sap_contract(
    *,
    pinned: dict[str, str],
    coverage_rows: list[dict[str, Any]],
    event_rows: list[dict[str, str]],
) -> dict[str, Any]:
    m2 = M1_PRIMARY_FEATURE_ORDER + M2_BLOCK
    m3 = m2 + M3_BLOCK
    m4 = m3 + M4_BLOCK
    art_ft = [
        r for r in event_rows
        if r["sample_design"] == PRIMARY_SAMPLE
        and r["target"] == ARTICLE141_TARGET
        and r["window"] == "final_test"
    ][0]
    return {
        "contract_version": CONTRACT_VERSION,
        "contract_version_history": {
            "v1": CONTRACT_VERSION_V1_HISTORICAL,
            "v2": CONTRACT_VERSION,
            "v2_changes": [
                "removes_revenue_growth_from_admitted_M1",
                "removes_unauthorized_denominator_exception",
                "adds_strict_positive_negative_missing_event_accounting",
                "clarifies_pre_imputation_missingness_indicators",
                "separates_SMOTE_from_class_weighting",
                "separates_predictor_admission_from_final_test_claim_eligibility",
            ],
        },
        "research_action_id": RESEARCH_ACTION_ID,
        "baseline_commit": EXPECTED_BASELINE_COMMIT,
        "part4_statistical_analysis_plan_locked": True,
        "modeling_authorized": False,
        "modeling_started": False,
        "stage126_authorized": False,
        "stage126_started": False,
        "model_fit_calls": 0,
        "prediction_calls": 0,
        "final_test_accessed_for_modeling": False,
        "primary_sample": PRIMARY_SAMPLE,
        "primary_target": PRIMARY_TARGET,
        "prediction_alignment": "predictor_year_t_to_target_year_t_plus_1",
        "active_availability_method": AVAILABILITY_METHOD,
        "active_availability_lag_months": APPROVED_LAG_MONTHS,
        "financial_data_researcher_verified_frozen": True,
        "broad_codal_capture_stopped": True,
        "row_level_publish_datetime_collection_required": False,
        "rampna_audit_only": True,
        "pinned_part3c_input_sha256": pinned,
        "sample_specs": SAMPLE_SPECS,
        "m1_coverage_audit_candidates": M1_COVERAGE_AUDIT_CANDIDATES,
        "m1_primary_feature_order": M1_PRIMARY_FEATURE_ORDER,
        "m1_feature_source_mapping": M1_FEATURE_SOURCE,
        "m1_target_proximity_robustness_order": M1_TARGET_PROXIMITY_ROBUSTNESS,
        "m1_target_proximity_removed": M1_TARGET_PROXIMITY_REMOVED,
        "revenue_growth_period_adjusted_status": {
            "feature": REVENUE_GROWTH_FEATURE,
            "admission_status": "rejected_m1_primary_coverage_gate_failed",
            "retained_in_frozen_dataset": True,
            "retained_in_coverage_audit": True,
            "present_in_admitted_model_feature_sets": False,
            "growth_denominator_exception_authorized": False,
            "rejection_reason": (
                "minimum_fold_training_coverage_below_locked_threshold; "
                "Fold_1_training_coverage_148/245=0.6040816327; "
                "passed_overall_development_coverage_0.8483483483_but_failed_"
                "minimum_fold_training_threshold_0.75"
            ),
        },
        "financial_expense_to_assets_sign_convention": {
            "feature": "financial_expense_to_assets_period_adjusted",
            "convention": (
                "preserve_frozen_part3c_source_sign; expenses_are_nonpositive_"
                "in_researcher_verified_data; do_not_abs_or_reverse_sign"
            ),
        },
        "growth_feature_coverage_exception": None,
        "growth_denominator_exception_absent": True,
        "coverage_denominator_policy": (
            "all_rows_belonging_to_the_relevant_development_or_fold_subset"
        ),
        "m2_block": M2_BLOCK,
        "m2_definitions": {
            "shared_window": "12_calendar_month_pre_cutoff",
            "market_observation_date": "strictly_before_cutoff",
            "min_valid_return_observations": 126,
            "min_valid_amihud_observations": 126,
            "price": "adjusted_close_only",
            "imputation_of_market_days": False,
            "automatic_threshold_reduction": False,
        },
        "m2_data_collected": False,
        "m3_block": M3_BLOCK,
        "m3_admitted": False,
        "m3_status": "not_admitted_no_authoritative_cbi_endpoint",
        "m3_data_collected": False,
        "m3_substitution_sci_or_free_market_allowed": False,
        "m4_block": M4_BLOCK,
        "m4_status": "conditional_future_variable_level_data_gate",
        "m4_data_collected": False,
        "m4_constraints": {
            "official_structured_codal_only": True,
            "persian_nlp": False,
            "ambiguity_or_missing": "null",
        },
        "nested_blocks": {
            "M1": M1_PRIMARY_FEATURE_ORDER,
            "M2": m2,
            "M3": m3,
            "M4": m4,
        },
        "nested_block_counts": {
            "M1": len(M1_PRIMARY_FEATURE_ORDER),
            "M2": len(m2),
            "M3": len(m3),
            "M4": len(m4),
        },
        "candidate_data_admission": {
            "scope": "development_predictor_data_only",
            "candidate_valid_coverage_min": BLOCK_CANDIDATE_COVERAGE_MIN,
            "block_common_sample_coverage_min": BLOCK_COMMON_COVERAGE_MIN,
            "m1_overall_development_min": M1_COVERAGE_OVERALL_MIN,
            "m1_minimum_fold_training_min": M1_COVERAGE_FOLD_TRAIN_MIN,
            "coverage_years": "development_only_1393_1399",
            "final_test_predictor_inspection_for_admission": False,
            "fail_action": "not_admitted_retained_in_coverage_audit",
            "replaces_pilot_G09_G14_for_modeling_path": True,
        },
        "development_model_comparison_feasibility": {
            "min_positive_evaluable_each_temporal_validation_window":
                MIN_VAL_POSITIVES,
            "fail_action": "development_comparison_not_supported",
        },
        "final_test_inferential_claim_eligibility": {
            "min_positive_evaluable_locked_final_test": MIN_FINAL_TEST_POSITIVES,
            "fail_action": (
                "distributional_descriptive_robustness_only;"
                "no_comparative_predictive_performance_claim;"
                "no_inferential_model_ranking"
            ),
            "does_not_admit_or_reject_predictors": True,
            "does_not_admit_or_reject_data_sources": True,
            "does_not_change_block_definitions": True,
            "does_not_change_temporal_split": True,
            "does_not_change_final_test_years": True,
        },
        "m1_coverage_gates": {
            "overall_development_min": M1_COVERAGE_OVERALL_MIN,
            "minimum_fold_training_min": M1_COVERAGE_FOLD_TRAIN_MIN,
            "coverage_denominator":
                "all_rows_belonging_to_the_relevant_development_or_fold_subset",
            "growth_denominator_exception_authorized": False,
            "audit": coverage_rows,
        },
        "target_state_contract": {
            "positive": "exact_numeric_or_string_1",
            "negative": "exact_numeric_or_string_0",
            "missing": "blank_null_unparseable_or_any_other_value",
            "missing_never_counted_as_negative": True,
            "evaluable_rows": "positive_plus_negative",
            "target_specific_analyses_use_evaluable_rows_only": True,
        },
        "article141_final_test_gate": {
            "sample": PRIMARY_SAMPLE,
            "target": ARTICLE141_TARGET,
            "positive": int(art_ft["positive"]),
            "evaluable_rows": int(art_ft["evaluable_rows"]),
            "missing": int(art_ft["missing"]),
            "decision": art_ft["event_gate_decision"],
            "gate_type": "final_test_inferential_claim_eligibility",
        },
        "human_revenue_growth_exclusion_decision": F_RG_DECISION,
        "research_pointers": {
            "last_completed_research_action_id": RESEARCH_LAST_COMPLETED,
            "next_research_action_id": RESEARCH_NEXT,
        },
    }


def build_split_contract() -> dict[str, Any]:
    validate_locked_folds()
    return {
        "split_variable": "target_year",
        "random_split_authorized": False,
        "shuffle_authorized": False,
        "development_target_years": sorted(DEVELOPMENT_YEARS),
        "final_test_target_years": sorted(FINAL_TEST_YEARS),
        "temporal_validation_fold_1": {
            "train_target_years": sorted(FOLD1_TRAIN_YEARS),
            "validation_target_years": sorted(FOLD1_VAL_YEARS),
        },
        "temporal_validation_fold_2": {
            "train_target_years": sorted(FOLD2_TRAIN_YEARS),
            "validation_target_years": sorted(FOLD2_VAL_YEARS),
        },
        "primary_sample_final_test_expected": {
            "sample": PRIMARY_SAMPLE,
            "pairs": 346,
            "positive": 12,
            "negative": 334,
        },
        "final_test_untouched_until_stage126_lock": True,
        "manifest_allowed_columns": SPLIT_MANIFEST_COLUMNS,
        "manifest_forbids_predictor_values": True,
        "manifest_forbids_row_level_targets": True,
    }


def build_preprocessing_contract() -> dict[str, Any]:
    return {
        "fit_scope": "each_temporal_training_fold_separately",
        "forbidden_fit_on": [
            "validation_data", "final_test_data",
            "combined_train_plus_validation_before_configuration_selection",
        ],
        "continuous_pipeline_order": [
            "1_deterministic_source_to_feature_transformation",
            "2_capture_original_pre_imputation_missingness_mask",
            "3_estimate_1st_99th_percentile_clipping_bounds_on_observed_training_fold_values_only",
            "4_apply_training_derived_clipping_bounds",
            "5_estimate_training_fold_median_on_observed_clipped_training_values",
            "6_impute_missing_values_with_training_fold_median",
            "7_append_missingness_indicators_from_original_pre_imputation_mask",
            "8_logistic_regression_only_standardize_imputed_continuous_features_using_training_fold_mean_std",
        ],
        "missingness_indicator_source": "original_pre_imputation_mask",
        "missingness_mask_captured_before_imputation": True,
        "missing_indicators_standardized": False,
        "clipping_fit_on_observed_training_values_only": True,
        "median_fit_after_training_clipping": True,
        "do_not_compute_clipping_quantiles_after_median_imputation": True,
        "do_not_infer_missingness_indicator_from_imputed_matrix": True,
        "validation_and_final_test_masks_from_own_original_missing_positions": True,
        "clipping_medians_standardization_parameters_from_training_only": True,
        "logistic_regression_extra":
            "training_fold_standardization_after_imputation_continuous_only",
        "random_forest_standardization": False,
        "xgboost_standardization": False,
        "future_categorical_m4": {
            "encoding": "training_only_one_hot",
            "unknown_category": True,
            "target_encoding": False,
        },
        "final_development_refit": {
            "after_hyperparameter_selection": True,
            "fit_years": sorted(DEVELOPMENT_YEARS),
            "apply_once_to_locked_final_test": True,
        },
        "forbidden_selection": [
            "univariate_screening", "recursive_feature_elimination",
            "shap_selection", "p_value_feature_selection",
        ],
    }


def build_model_specs() -> dict[str, Any]:
    return {
        "allowed_models_only": [
            "regularized_logistic_regression",
            "random_forest",
            "xgboost",
        ],
        "forbidden_models": [
            "SVM", "neural_network", "LightGBM", "CatBoost",
            "stacking", "voting",
        ],
        "imbalance_handling_primary": {
            "logistic_regression": {"class_weight": "balanced"},
            "random_forest": {"class_weight": "balanced_subsample"},
            "xgboost": {
                "scale_pos_weight": (
                    "training_fold_negative_evaluable_count / "
                    "training_fold_positive_evaluable_count"
                ),
                "counts_exclude_missing_target_rows": True,
            },
        },
        "smote_robustness": {
            "primary": False,
            "sample": PRIMARY_SAMPLE,
            "features": "M1_PRIMARY_FEATURE_ORDER",
            "m1_feature_count": len(M1_PRIMARY_FEATURE_ORDER),
            "models": ["Logistic", "RF", "XGBoost"],
            "apply_only_inside_training_fold": True,
            "never_before_temporal_splitting": True,
            "k_neighbors": "min(5, training_minority_count - 1)",
            "random_state": SMOTE_SEED,
            "uses_selected_non_weight_hyperparameters": True,
            "class_weighting_disabled_when_smote_active": True,
            "oversampling_and_class_weighting_combined": False,
            "second_tuning_search": False,
            "logistic_regression": {"class_weight": None},
            "random_forest": {"class_weight": None},
            "xgboost": {"scale_pos_weight": 1},
        },
        "no_model_fitting_in_part4": True,
    }


def build_revenue_growth_exclusion_decision() -> dict[str, Any]:
    return {
        "decision_id":
            "stage125-part4-revenue-growth-exclusion-revision",
        "decision_authority": "human_supervisor_data_owner",
        "decision_status": "active",
        "decision_date": "2026-07-19",
        "decision_scope": "Stage125_Part4_M1_feature_admission",
        "contract_version": CONTRACT_VERSION,
        "supersedes_active_methodology": (
            "admitted_m1_primary_using_unauthorized_denominator_exception"
        ),
        "feature": REVENUE_GROWTH_FEATURE,
        "previous_status":
            "admitted_m1_primary_using_unauthorized_denominator_exception",
        "revised_status": "rejected_m1_primary_coverage_gate_failed",
        "admission_status": "rejected_m1_primary_coverage_gate_failed",
        "retained_in_frozen_dataset": True,
        "retained_in_coverage_audit": True,
        "removed_from_primary_feature_set": True,
        "removed_from_target_proximity_robustness": True,
        "removed_from_nested_M2_M3_M4_surfaces": True,
        "financial_data_changed": False,
        "sample_changed": False,
        "target_changed": False,
        "temporal_split_changed": False,
        "final_test_changed": False,
        "denominator_exception_authorized": False,
        "first_observation_denominator_exception_authorized": False,
        "locked_minimum_fold_training_coverage_threshold":
            M1_COVERAGE_FOLD_TRAIN_MIN,
        "overall_development_coverage_threshold": M1_COVERAGE_OVERALL_MIN,
        "evidence": {
            "development_rows": 666,
            "development_nonmissing": 565,
            "overall_development_coverage": 0.8483483483,
            "fold1_training_rows": 245,
            "fold1_training_nonmissing": 148,
            "fold1_training_coverage": 0.6040816327,
            "fold1_validation_rows": 205,
            "fold1_validation_nonmissing": 203,
            "fold1_validation_coverage": 0.9902439024,
            "fold2_training_rows": 450,
            "fold2_training_nonmissing": 351,
            "fold2_training_coverage": 0.7800000000,
            "fold2_validation_rows": 216,
            "fold2_validation_nonmissing": 214,
            "fold2_validation_coverage": 0.9907407407,
            "minimum_fold_training_coverage": 0.6040816327,
            "passed_overall_development_coverage_gate": True,
            "failed_minimum_fold_training_coverage_gate": True,
        },
        "exclusion_reasons": (
            "minimum temporal-fold training coverage below locked threshold; "
            "Fold 1 training coverage 148/245 = 0.6040816327; "
            "parsimony under low event count"
        ),
        "not_labeled_as": [
            "source_error",
            "financial_data_error",
            "target_leakage",
            "overall_development_coverage_failure",
        ],
        "research_pointers": {
            "last_completed_research_action_id": RESEARCH_LAST_COMPLETED,
            "next_research_action_id": RESEARCH_NEXT,
        },
        "modeling_started": False,
        "stage126_started": False,
    }


def build_revenue_growth_exclusion_readme() -> str:
    return """# Stage125 Part 4 — Revenue-Growth Exclusion Revision

**Status:** active human-supervisor methodological correction.
**Decision date:** 2026-07-19
**Contract:** `stage125_part4_sap_v2`

## Decision

`revenue_growth_period_adjusted` is **rejected** from admitted M1 primary
features because raw Fold 1 training coverage fails the locked minimum
fold-training coverage threshold:

```text
148 / 245 = 0.6040816327  <  0.75
```

Overall development coverage passes (`565 / 666 = 0.8483483483` ≥ 0.80), but
that is not sufficient for M1 admission.

## Explicit non-authorizations

- No coverage-denominator exception.
- No first-observation exclusion from the fold denominator.
- Missing first observations remain missing observations.
- Imputation later in a training pipeline does **not** retroactively change
  feature-admission coverage.

## Retention

- Retained in frozen Part 3C datasets.
- Retained in the development coverage audit as
  `rejected_m1_primary_coverage_gate_failed`.
- Removed from `M1_PRIMARY_FEATURE_ORDER`,
  `M1_TARGET_PROXIMITY_ROBUSTNESS`, and all nested M2–M4 modeling surfaces.

## Immutable scientific state

Financial values, targets, sample membership, temporal folds, final-test years,
and Part 3C hashes are unchanged.
"""


def build_hyperparameter_budget() -> dict[str, Any]:
    return {
        "logistic_regression": {
            "penalty": "l2", "solver": "liblinear", "max_iter": 5000,
            "C": [0.01, 0.1, 1.0, 10.0],
            "n_configurations": 4,
        },
        "random_forest": {
            "n_estimators": 500, "bootstrap": True,
            "max_depth": [3, 5, None],
            "min_samples_leaf": [5, 10],
            "max_features": ["sqrt", 0.5],
            "n_configurations": 12,
        },
        "xgboost": {
            "objective": "binary:logistic",
            "eval_metric": "aucpr",
            "n_estimators": 300,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "gamma": 0,
            "tree_method": "hist",
            "n_jobs": 1,
            "learning_rate": [0.03, 0.10],
            "max_depth": [2, 3],
            "min_child_weight": [1, 5],
            "reg_lambda": [1, 10],
            "n_configurations": 16,
            "early_stopping": False,
        },
        "total_configurations_per_block": 32,
        "grid_expansion_after_results_authorized": False,
        "early_stopping_authorized": False,
        "tuning_seeds": list(TUNING_SEEDS),
        "final_seeds": list(FINAL_SEEDS),
        "configuration_score": (
            "equal_weight_mean_validation_PR_AUC_across_2_folds_and_3_seeds"
        ),
        "final_rf_xgb_probability":
            "mean_predicted_probability_across_5_fixed_seeds",
        "logistic_regression_deterministic": True,
        "tie_breaking_order": [
            "higher_mean_temporal_validation_PR_AUC",
            "higher_minimum_fold_PR_AUC",
            "simpler_configuration",
            "lexicographically_smaller_configuration_id",
        ],
        "complexity_ordering": {
            "logistic": "smaller_C_preferred",
            "rf": "shallower_max_depth_then_larger_min_samples_leaf_then_sqrt",
            "xgboost": (
                "shallower_max_depth_then_larger_min_child_weight_"
                "then_larger_reg_lambda_then_lower_learning_rate"
            ),
        },
    }


def build_metrics_contract() -> dict[str, Any]:
    return {
        "primary_metric": PRIMARY_METRIC,
        "secondary_metrics": [
            "ROC-AUC", "Brier_score", "Recall@10%", "Lift@10%",
        ],
        "topk": {
            "definition": "K_y = ceil(0.10 * N_y)",
            "fraction": TOPK_FRACTION,
            "ranking_order": [
                "predicted_probability_descending",
                "ticker_ascending_deterministic_tiebreaker",
            ],
            "recall_at_10pct": (
                "sum_captured_positives_across_target_years / "
                "sum_total_positives_across_target_years"
            ),
            "lift_at_10pct": (
                "pooled_precision_among_selected_topK / pooled_test_prevalence"
            ),
            "optimize_K_after_results": False,
        },
        "thresholded_secondary": {
            "rule": "development_OOF_F2_maximizing_threshold",
            "tie_break": "higher_threshold",
            "never_optimize_on_final_test": True,
        },
        "calibration": {
            "primary_probabilities": "raw_locked_pipeline_probabilities",
            "report": [
                "Brier_score", "5_bin_quantile_calibration_curve",
                "calibration_intercept", "calibration_slope",
            ],
            "logit_clip_epsilon": CALIBRATION_EPSILON,
            "optional_secondary_recalibration": "sigmoid_Platt",
            "platt_fit_on": "pooled_development_OOF_predictions_only",
            "isotonic_authorized": False,
            "skip_recalibration_if_oof_positives_lt": 20,
            "do_not_select_winner_on_calibrated_final_test": True,
        },
        "uncertainty": {
            "method": "paired_company_cluster_bootstrap",
            "cluster": BOOTSTRAP_CLUSTER,
            "replicates": BOOTSTRAP_REPLICATES,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "confidence_interval": "percentile_95",
            "min_valid_replicates": BOOTSTRAP_MIN_VALID,
            "valid_replicate_requires_both_classes": True,
            "same_resampled_rows_for_all_compared_models": True,
        },
        "multiplicity": {
            "confirmatory_family_1": [
                "Logistic_vs_RF", "Logistic_vs_XGBoost", "RF_vs_XGBoost",
            ],
            "confirmatory_family_2_adjacent_block_gains_if_admitted": [
                "M2_minus_M1", "M3_minus_M2", "M4_minus_M3",
            ],
            "correction": "Holm",
            "alpha": HOLM_ALPHA,
            "additional_post_hoc_families_authorized": False,
        },
    }


def build_shap_contract() -> dict[str, Any]:
    return {
        "shap_for_feature_selection": False,
        "methods": {
            "Logistic": "LinearSHAP",
            "RF": "TreeSHAP",
            "XGBoost": "TreeSHAP",
        },
        "background": {
            "source": "development_period_only",
            "max_rows": SHAP_MAX_BACKGROUND,
            "selection": "deterministic_stratified_by_target_year_and_class",
        },
        "report": [
            "mean_absolute_SHAP", "mean_signed_SHAP",
            "feature_rank", "top5_features",
        ],
        "stability_checks": [
            "pairwise_Spearman_rank_correlation",
            "top5_Jaccard_overlap",
            "mean_sign_agreement",
        ],
        "stability_across": [
            "temporal_validation_folds",
            "RF_XGBoost_seeds",
            "final_test_versus_development_OOF_explanations",
        ],
        "no_single_plot_stability_claim": True,
        "do_not_suppress_unstable_explanations": True,
        "no_shap_computation_in_part4": True,
    }


def build_readme() -> str:
    return """# Stage125 Part 4 — Statistical Analysis Plan

**Status:** Locked research-design / contract surface only.
**Contract version:** `stage125_part4_sap_v2` (v1 retained in Git history).
**Research action:** `stage125-part4-statistical-analysis-plan`
**Next:** `stage125-part5-readiness-closure`

## Scope

Part 4 locks the statistical analysis plan for future Stage126 modeling:

- primary sample `main_rule_a_primary` (1012 / 119 / 80 / 932)
- primary target `FD_target_main_t_plus_1`
- M1 primary ordered feature set (exactly 9 admitted)
- M1 coverage-audit candidates (exactly 10, including rejected revenue growth)
- M1 target-proximity robustness set (exactly 6)
- nested M2–M4 blocks (9 / 12 / 15 / 19; conditional; no data collected here)
- target-year temporal folds and locked final test 1400–1402
- strict positive / negative / missing target event accounting
- preprocessing with pre-imputation missingness masks
- model families, finite hyperparameter budget, seeds
- SMOTE robustness disables class weighting (no combined oversampling+weights)
- PR-AUC primary; Recall@10% / Lift@10%; calibration; paired ticker-cluster bootstrap; Holm
- SHAP stability contract (no SHAP computation in Part 4)

## v2 methodological correction

Human supervisor rejected `revenue_growth_period_adjusted` from admitted M1
because raw Fold 1 training coverage `148/245 = 0.6040816327` is below the
locked 0.75 threshold. The unauthorized first-observation denominator exception
is removed. The feature remains in frozen Part 3C data and in the coverage
audit as `rejected_m1_primary_coverage_gate_failed`.

## Explicit non-claims

- No model was fitted (`model_fit_calls = 0`).
- No prediction was generated (`prediction_calls = 0`).
- No SHAP value was calculated.
- Final-test predictor values were not used for admission, tuning, or selection.
- Final-test event thresholds control claim eligibility only, not feature admission.
- Stage126 remains unauthorized and unstarted.
- Modeling remains unstarted.
- M3 remains unavailable pending an authoritative CBI source.
- No M2/M3/M4 values were collected.
- Active availability lag remains four Jalali calendar months.
- Financial data and targets remain frozen.
- `رمپنا|1396 → رمپنا|1397` remains audit-only.
- Part 3C outputs remain unchanged (SHA-256 pinned).

## Runners

```bash
python project/run_stage125_part4.py --build
python project/run_stage125_part4.py --check
```

`--build` is offline and deterministic. `--check` performs zero writes.
"""


# --------------------------------------------------------------------------- #
# Build / QC / run
# --------------------------------------------------------------------------- #

def build_all(repo_root: Path) -> tuple[dict[str, str], dict[str, Any]]:
    validate_locked_folds()
    assert_no_model_imports_in_source(repo_root)
    assert_no_unapproved_m1(list(M1_PRIMARY_FEATURE_ORDER))
    assert_no_target_derived(
        M1_PRIMARY_FEATURE_ORDER + M1_TARGET_PROXIMITY_ROBUSTNESS
        + M2_BLOCK + M3_BLOCK + M4_BLOCK
    )
    if REVENUE_GROWTH_FEATURE in M1_PRIMARY_FEATURE_ORDER:
        raise QCFail("revenue_growth admitted to M1 primary")
    if REVENUE_GROWTH_FEATURE in M1_TARGET_PROXIMITY_ROBUSTNESS:
        raise QCFail("revenue_growth admitted to target-proximity robustness")
    if REVENUE_GROWTH_FEATURE not in M1_COVERAGE_AUDIT_CANDIDATES:
        raise QCFail("revenue_growth missing from coverage audit candidates")
    assert_feature_order(
        list(M1_PRIMARY_FEATURE_ORDER),
        [
            "log_total_assets", "leverage_ratio", "current_ratio",
            "roa_period_adjusted", "ocf_to_assets_period_adjusted",
            "asset_turnover_period_adjusted", "operating_margin_period_adjusted",
            "financial_expense_to_assets_period_adjusted",
            "accumulated_loss_to_capital_ratio",
        ],
        "M1",
    )
    assert_feature_order(
        list(M1_TARGET_PROXIMITY_ROBUSTNESS),
        [
            "log_total_assets", "current_ratio", "roa_period_adjusted",
            "asset_turnover_period_adjusted", "operating_margin_period_adjusted",
            "financial_expense_to_assets_period_adjusted",
        ],
        "M1_TARGET_PROXIMITY_ROBUSTNESS",
    )
    assert_feature_order(
        list(M1_COVERAGE_AUDIT_CANDIDATES),
        [
            "log_total_assets", "leverage_ratio", "current_ratio",
            "roa_period_adjusted", "ocf_to_assets_period_adjusted",
            "asset_turnover_period_adjusted", "operating_margin_period_adjusted",
            REVENUE_GROWTH_FEATURE,
            "financial_expense_to_assets_period_adjusted",
            "accumulated_loss_to_capital_ratio",
        ],
        "M1_COVERAGE_AUDIT_CANDIDATES",
    )
    if M2_BLOCK != [
        "equity_return_window", "realized_volatility", "amihud_illiquidity",
    ]:
        raise QCFail("M2 ordering mutation")
    if M3_BLOCK != [
        "cpi_inflation", "fx_change_official", "policy_financing_rate",
    ]:
        raise QCFail("M3 ordering mutation")
    if M4_BLOCK != [
        "audit_opinion_type", "going_concern_flag",
        "audit_lag_days", "board_size",
    ]:
        raise QCFail("M4 ordering mutation")

    pinned = frozen_part3c_hashes(repo_root)
    sample_rows = {
        sample: load_analysis_ready(repo_root, sample)
        for sample in ANALYSIS_READY_FILES
    }
    coverage_rows = compute_m1_coverage(sample_rows[PRIMARY_SAMPLE])
    event_rows = build_event_counts(sample_rows)
    manifest_rows = build_split_manifest(sample_rows)
    feature_rows = build_feature_set_rows()
    exclusion_rows = build_exclusion_rows()
    sample_target_rows = build_sample_target_matrix(sample_rows)
    sap = build_sap_contract(
        pinned=pinned, coverage_rows=coverage_rows, event_rows=event_rows,
    )
    split_contract = build_split_contract()
    preprocess = build_preprocessing_contract()
    models = build_model_specs()
    hyper = build_hyperparameter_budget()
    metrics = build_metrics_contract()
    shap_c = build_shap_contract()

    ft = final_test_rows(sample_rows[PRIMARY_SAMPLE])
    ft_counts = count_target_states([r[PRIMARY_TARGET] for r in ft])
    if (
        len(ft) != 346
        or ft_counts["positive"] != 12
        or ft_counts["negative"] != 334
        or ft_counts["missing"] != 0
    ):
        raise QCFail(
            f"primary final-test count mutation: n={len(ft)} "
            f"pos/neg/miss="
            f"{ft_counts['positive']}/{ft_counts['negative']}/"
            f"{ft_counts['missing']}"
        )

    nested = sap["nested_blocks"]
    if REVENUE_GROWTH_FEATURE in (
        nested["M1"] + nested["M2"] + nested["M3"] + nested["M4"]
    ):
        raise QCFail("revenue_growth present in nested model surfaces")
    if len(M1_EXCLUSIONS) != 23:
        raise QCFail(f"M1 exclusion count mutation: {len(M1_EXCLUSIONS)}")

    rg_decision = build_revenue_growth_exclusion_decision()
    content = {
        F_SAP: _json_str(sap),
        F_FEATURE_SETS: _csv_str(
            ["feature_set", "block", "position", "feature_name",
             "source_column", "status", "notes"],
            feature_rows,
        ),
        F_EXCLUSIONS: _csv_str(
            ["feature_name", "decision", "admission_status",
             "exclusion_reasons", "retained_in_frozen_datasets",
             "retained_in_audit", "available_in_audit_surface",
             "deleted_from_source_data"],
            exclusion_rows,
        ),
        F_SAMPLE_TARGET: _csv_str(
            ["sample_design", "sample_role", "target", "target_role",
             "rows", "evaluable_rows", "companies", "positive", "negative",
             "missing", "paper_primary_result"],
            sample_target_rows,
        ),
        F_SPLIT_CONTRACT: _json_str(split_contract),
        F_SPLIT_MANIFEST: _csv_str(SPLIT_MANIFEST_COLUMNS, manifest_rows),
        F_EVENT_GATE: _csv_str(EVENT_GATE_COLUMNS, event_rows),
        F_COVERAGE: _csv_str(COVERAGE_AUDIT_COLUMNS, coverage_rows),
        F_PREPROCESS: _json_str(preprocess),
        F_MODELS: _json_str(models),
        F_HYPER: _json_str(hyper),
        F_METRICS: _json_str(metrics),
        F_SHAP: _json_str(shap_c),
        F_README: build_readme(),
        F_RG_DECISION: _json_str(rg_decision),
        F_RG_README: build_revenue_growth_exclusion_readme(),
    }
    extras = {
        "sap": sap,
        "coverage_rows": coverage_rows,
        "event_rows": event_rows,
        "manifest_rows": manifest_rows,
        "pinned": pinned,
        "sample_rows": sample_rows,
    }
    return content, extras


def build_qc_assertions(
    *,
    repo_root: Path,
    extras: dict[str, Any],
    content: dict[str, str],
    network_attempts: int,
    head: str,
) -> list[dict[str, str]]:
    assertions: list[dict[str, str]] = []
    sap = extras["sap"]
    cov_by_feat = {
        r["feature_name"]: r for r in extras["coverage_rows"]
    }
    rg = cov_by_feat.get(REVENUE_GROWTH_FEATURE)
    preprocess = json.loads(content[F_PREPROCESS])
    models = json.loads(content[F_MODELS])
    nested = sap["nested_blocks"]
    rg_decision = json.loads(content[F_RG_DECISION])

    _assert(
        assertions, "baseline_commit_pinned",
        head == EXPECTED_BASELINE_COMMIT or _is_ancestor(
            repo_root, EXPECTED_BASELINE_COMMIT, head,
        ),
        EXPECTED_BASELINE_COMMIT,
    )
    pinned_now = frozen_part3c_hashes(repo_root)
    _assert(
        assertions, "part3c_inputs_pinned",
        extras["pinned"] == pinned_now, "8 hashes",
    )
    _assert(
        assertions, "Part3C_hashes_unchanged",
        pinned_now == FROZEN_PART3C_INPUTS
        and len(pinned_now) == 8,
        "8 unchanged",
    )
    _assert(
        assertions, "human_revenue_growth_exclusion_decision_recorded",
        rg_decision.get("decision_authority") == "human_supervisor_data_owner"
        and rg_decision.get("decision_status") == "active"
        and rg_decision.get("revised_status")
        == "rejected_m1_primary_coverage_gate_failed"
        and rg_decision.get("feature") == REVENUE_GROWTH_FEATURE,
        "recorded",
    )
    _assert(
        assertions, "part4_contract_version_v2_active",
        CONTRACT_VERSION == "stage125_part4_sap_v2"
        and sap.get("contract_version") == "stage125_part4_sap_v2"
        and sap.get("contract_version_history", {}).get("v1")
        == CONTRACT_VERSION_V1_HISTORICAL,
        CONTRACT_VERSION,
    )
    _assert(
        assertions, "growth_denominator_exception_absent",
        sap.get("growth_feature_coverage_exception") is None
        and sap.get("growth_denominator_exception_absent") is True
        and "growth_coverage_exception_applied" not in content[F_COVERAGE]
        and sap["m1_coverage_gates"][
            "growth_denominator_exception_authorized"
        ] is False
        and rg_decision.get("denominator_exception_authorized") is False
        and rg_decision.get(
            "first_observation_denominator_exception_authorized"
        ) is False,
        "absent",
    )
    _assert(
        assertions, "coverage_denominator_all_subset_rows",
        sap["m1_coverage_gates"]["coverage_denominator"]
        == "all_rows_belonging_to_the_relevant_development_or_fold_subset"
        and rg is not None
        and int(rg["fold1_train_rows"]) == 245
        and int(rg["fold1_validation_rows"]) == 205
        and int(rg["fold2_train_rows"]) == 450
        and int(rg["fold2_validation_rows"]) == 216
        and int(rg["development_rows"]) == 666,
        "ordinary_denominators",
    )
    _assert(
        assertions, "revenue_growth_coverage_audit_present",
        rg is not None
        and REVENUE_GROWTH_FEATURE in M1_COVERAGE_AUDIT_CANDIDATES
        and len(extras["coverage_rows"]) == 10,
        "present",
    )
    _assert(
        assertions, "revenue_growth_fold1_train_numerator_148",
        rg is not None and int(rg["fold1_train_nonmissing"]) == 148,
        str(rg["fold1_train_nonmissing"] if rg else None),
    )
    _assert(
        assertions, "revenue_growth_fold1_train_denominator_245",
        rg is not None and int(rg["fold1_train_rows"]) == 245,
        str(rg["fold1_train_rows"] if rg else None),
    )
    _assert(
        assertions, "revenue_growth_fold1_train_coverage_0_6040816327",
        rg is not None
        and abs(float(rg["fold1_train_coverage"]) - 0.6040816327) < 1e-10,
        str(rg["fold1_train_coverage"] if rg else None),
    )
    _assert(
        assertions, "revenue_growth_rejected",
        rg is not None
        and rg["admission_status"] == "rejected_m1_primary_coverage_gate_failed"
        and REVENUE_GROWTH_FEATURE not in M1_PRIMARY_FEATURE_ORDER
        and REVENUE_GROWTH_FEATURE not in nested["M1"]
        and REVENUE_GROWTH_FEATURE not in nested["M2"]
        and REVENUE_GROWTH_FEATURE not in nested["M3"]
        and REVENUE_GROWTH_FEATURE not in nested["M4"],
        "rejected_audit_only",
    )
    admitted = [
        r for r in extras["coverage_rows"]
        if r["admission_status"] == "admitted_m1_primary"
    ]
    rejected = [
        r for r in extras["coverage_rows"]
        if r["admission_status"] == "rejected_m1_primary_coverage_gate_failed"
    ]
    _assert(
        assertions, "m1_coverage_decisions_exact",
        len(admitted) == 9
        and len(rejected) == 1
        and rejected[0]["feature_name"] == REVENUE_GROWTH_FEATURE,
        "9 admitted + 1 rejected revenue-growth",
    )
    _assert(
        assertions, "nine_final_M1_features_pass_coverage",
        all(
            cov_by_feat[f]["admission_status"] == "admitted_m1_primary"
            for f in M1_PRIMARY_FEATURE_ORDER
        ),
        "9 pass",
    )
    _assert(
        assertions, "m1_primary_feature_count_9",
        len(M1_PRIMARY_FEATURE_ORDER) == 9, str(len(M1_PRIMARY_FEATURE_ORDER)),
    )
    _assert(
        assertions, "m1_target_proximity_count_6",
        len(M1_TARGET_PROXIMITY_ROBUSTNESS) == 6,
        str(len(M1_TARGET_PROXIMITY_ROBUSTNESS)),
    )
    _assert(
        assertions, "nested_M2_count_12",
        len(nested["M2"]) == 12, str(len(nested["M2"])),
    )
    _assert(
        assertions, "nested_M3_count_15",
        len(nested["M3"]) == 15, str(len(nested["M3"])),
    )
    _assert(
        assertions, "nested_M4_count_19",
        len(nested["M4"]) == 19, str(len(nested["M4"])),
    )
    _assert(
        assertions, "m1_exclusion_count_23",
        len(M1_EXCLUSIONS) == 23, str(len(M1_EXCLUSIONS)),
    )
    _assert(assertions, "m2_block_count_3", len(M2_BLOCK) == 3, str(len(M2_BLOCK)))
    _assert(assertions, "m3_block_count_3", len(M3_BLOCK) == 3, str(len(M3_BLOCK)))
    _assert(assertions, "m4_block_count_4", len(M4_BLOCK) == 4, str(len(M4_BLOCK)))
    event_rows = extras["event_rows"]
    _assert(
        assertions, "target_event_counts_have_missing_column",
        event_rows
        and all("missing" in r and "evaluable_rows" in r for r in event_rows),
        "missing+evaluable",
    )
    recon_ok = all(
        int(r["rows"])
        == int(r["positive"]) + int(r["negative"]) + int(r["missing"])
        and int(r["evaluable_rows"])
        == int(r["positive"]) + int(r["negative"])
        for r in event_rows
    )
    _assert(
        assertions, "target_event_count_reconciliation_exact",
        recon_ok, "rows=pos+neg+miss",
    )
    _assert(
        assertions, "missing_never_counted_as_negative",
        all(
            classify_target_state("") == "missing"
            and classify_target_state("nan") == "missing"
            and classify_target_state("2") == "missing"
            and classify_target_state("0") == "negative"
            and classify_target_state("1") == "positive"
            for _ in [0]
        )
        and all(
            int(r["negative"]) <= int(r["evaluable_rows"]) for r in event_rows
        ),
        "strict_three_state",
    )
    _assert(
        assertions, "target_specific_evaluable_rows_recorded",
        all(int(r["evaluable_rows"]) >= 0 for r in event_rows)
        and sap["target_state_contract"][
            "target_specific_analyses_use_evaluable_rows_only"
        ] is True,
        "evaluable_recorded",
    )
    claim = sap["final_test_inferential_claim_eligibility"]
    _assert(
        assertions, "final_test_threshold_is_claim_gate_not_feature_admission",
        claim["does_not_admit_or_reject_predictors"] is True
        and claim["does_not_change_temporal_split"] is True
        and "min_positives_locked_final_test"
        not in sap.get("candidate_data_admission", {})
        and "final_data_admission_thresholds" not in sap,
        "claim_gate_only",
    )
    _assert(
        assertions, "missingness_mask_before_imputation",
        preprocess["missingness_mask_captured_before_imputation"] is True
        and preprocess["missingness_indicator_source"]
        == "original_pre_imputation_mask"
        and preprocess["clipping_fit_on_observed_training_values_only"] is True
        and preprocess["median_fit_after_training_clipping"] is True,
        "pre_imputation_mask",
    )
    _assert(
        assertions, "missingness_indicators_not_standardized",
        preprocess["missing_indicators_standardized"] is False,
        "false",
    )
    smote = models["smote_robustness"]
    _assert(
        assertions, "SMOTE_class_weighting_disabled",
        smote["class_weighting_disabled_when_smote_active"] is True
        and smote["oversampling_and_class_weighting_combined"] is False
        and smote["logistic_regression"]["class_weight"] is None
        and smote["random_forest"]["class_weight"] is None
        and smote["xgboost"]["scale_pos_weight"] == 1,
        "disabled",
    )
    _assert(
        assertions, "SMOTE_uses_no_second_tuning_search",
        smote["second_tuning_search"] is False
        and smote["uses_selected_non_weight_hyperparameters"] is True,
        "no_second_search",
    )
    split_c = json.loads(content[F_SPLIT_CONTRACT])
    _assert(
        assertions, "temporal_split_unchanged",
        split_c["development_target_years"] == sorted(DEVELOPMENT_YEARS)
        and split_c["final_test_target_years"] == sorted(FINAL_TEST_YEARS)
        and split_c["temporal_validation_fold_1"]["train_target_years"]
        == sorted(FOLD1_TRAIN_YEARS)
        and split_c["temporal_validation_fold_1"]["validation_target_years"]
        == sorted(FOLD1_VAL_YEARS)
        and split_c["temporal_validation_fold_2"]["train_target_years"]
        == sorted(FOLD2_TRAIN_YEARS)
        and split_c["temporal_validation_fold_2"]["validation_target_years"]
        == sorted(FOLD2_VAL_YEARS),
        "unchanged",
    )
    _assert(
        assertions, "final_test_unchanged",
        set(FINAL_TEST_YEARS) == {1400, 1401, 1402}
        and split_c["primary_sample_final_test_expected"]["pairs"] == 346
        and split_c["primary_sample_final_test_expected"]["positive"] == 12
        and split_c["primary_sample_final_test_expected"]["negative"] == 334,
        "1400-1402",
    )
    _assert(
        assertions, "primary_metric_pr_auc",
        PRIMARY_METRIC == "PR-AUC"
        and json.loads(content[F_METRICS])["primary_metric"] == "PR-AUC",
        PRIMARY_METRIC,
    )
    _assert(
        assertions, "topk_fraction_10pct",
        abs(TOPK_FRACTION - 0.10) < 1e-12, str(TOPK_FRACTION),
    )
    _assert(
        assertions, "bootstrap_contract",
        BOOTSTRAP_REPLICATES == 2000 and BOOTSTRAP_CLUSTER == "ticker",
        f"{BOOTSTRAP_REPLICATES}/{BOOTSTRAP_CLUSTER}",
    )
    _assert(
        assertions, "holm_correction_present",
        json.loads(content[F_METRICS])["multiplicity"]["correction"] == "Holm",
        "Holm",
    )
    _assert(
        assertions, "seed_lists_locked",
        list(TUNING_SEEDS) == [20260719, 20260720, 20260721]
        and list(FINAL_SEEDS) == [
            20260719, 20260720, 20260721, 20260722, 20260723,
        ],
        "seeds",
    )
    hyper = json.loads(content[F_HYPER])
    _assert(
        assertions, "hyperparameter_budget_32",
        hyper["total_configurations_per_block"] == 32
        and hyper["logistic_regression"]["n_configurations"] == 4
        and hyper["random_forest"]["n_configurations"] == 12
        and hyper["xgboost"]["n_configurations"] == 16
        and hyper["early_stopping_authorized"] is False
        and hyper["grid_expansion_after_results_authorized"] is False,
        "32",
    )
    _assert(
        assertions, "smote_training_fold_only",
        smote["apply_only_inside_training_fold"] is True
        and smote["never_before_temporal_splitting"] is True,
        "train_fold_only",
    )
    _assert(
        assertions, "manifest_columns_only",
        all(
            set(r) <= set(SPLIT_MANIFEST_COLUMNS)
            for r in extras["manifest_rows"]
        ),
        "ok",
    )
    _assert(
        assertions, "manifest_no_targets",
        all(
            not any(t in r for t in ALL_TARGETS)
            for r in extras["manifest_rows"]
        ),
        "ok",
    )
    art = sap["article141_final_test_gate"]
    _assert(
        assertions, "article141_descriptive_only",
        art["positive"] < MIN_FINAL_TEST_POSITIVES
        and "distributional_descriptive_robustness_only" in art["decision"],
        str(art["positive"]),
    )
    _assert(
        assertions, "network_requests_zero",
        network_attempts == 0, str(network_attempts),
    )
    _assert(assertions, "model_fit_calls_zero", sap["model_fit_calls"] == 0, "0")
    _assert(
        assertions, "prediction_calls_zero", sap["prediction_calls"] == 0, "0",
    )
    _assert(
        assertions, "final_test_not_used_for_modeling",
        sap["final_test_accessed_for_modeling"] is False, "false",
    )
    _assert(
        assertions, "modeling_false",
        sap["modeling_started"] is False and sap["modeling_authorized"] is False,
        "false",
    )
    _assert(
        assertions, "Stage126_false",
        sap["stage126_started"] is False and sap["stage126_authorized"] is False,
        "false",
    )
    _assert(
        assertions, "m3_not_admitted",
        sap["m3_admitted"] is False and sap["m3_data_collected"] is False,
        "false",
    )
    _assert(
        assertions, "no_m2_m3_m4_collection",
        (not sap["m2_data_collected"]
         and not sap["m3_data_collected"]
         and not sap["m4_data_collected"]),
        "false",
    )
    _assert(
        assertions, "four_month_lag_active",
        sap["active_availability_lag_months"] == 4
        and sap["active_availability_method"] == AVAILABILITY_METHOD,
        "4",
    )
    _assert(
        assertions, "forbidden_surfaces_absent",
        all(not (repo_root / rel).exists() for rel in FORBIDDEN_SURFACE_EXACT),
        "absent",
    )
    content2, _ = build_all(repo_root)
    det_ok = all(content[k] == content2[k] for k in TRACKED_CONTENT_FILES)
    _assert(assertions, "deterministic_rebuild", det_ok, "stable")
    try:
        reject_random_split("random")
        rand_rejected = False
    except AuthorizationError:
        rand_rejected = True
    _assert(assertions, "random_split_rejected", rand_rejected, "rejected")
    try:
        reject_final_test_year_change({1400, 1401})
        ft_rejected = False
    except AuthorizationError:
        ft_rejected = True
    _assert(
        assertions, "final_test_year_change_rejected", ft_rejected, "rejected",
    )
    return assertions


def _compare_drift(out_dir: Path, payloads: dict[str, str]) -> list[str]:
    drift: list[str] = []
    for name, text in payloads.items():
        path = out_dir / name
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            drift.append(name)
    return drift


def run(
    *,
    project_dir: Path,
    output_dir: Path | None = None,
    build: bool = False,
    check: bool = False,
) -> dict[str, Any]:
    if build and check:
        raise QCFail("build and check are mutually exclusive")
    if not build and not check:
        raise QCFail("one of --build or --check is required")

    repo_root = (
        project_dir.parent if project_dir.name == "project" else project_dir
    )
    canonical_out = (repo_root / "project" / "stage125").resolve()
    out_dir = Path(output_dir).resolve() if output_dir else canonical_out

    head = verify_baseline_commit(str(repo_root))
    pinned_before = frozen_part3c_hashes(repo_root)
    network_attempts = 0
    files_written: dict[str, str] = {}

    with p3b0.network_sentinel() as sentinel:
        content, extras = build_all(repo_root)
        if sentinel.calls_attempted != 0:
            raise QCFail(
                f"network_requests_attempted_zero failed: "
                f"{sentinel.calls_attempted}"
            )
        network_attempts = sentinel.calls_attempted
        pinned_after = frozen_part3c_hashes(repo_root)
        if pinned_before != pinned_after:
            raise QCFail("Part 3C inputs mutated during Part 4 run")

        assertions = build_qc_assertions(
            repo_root=repo_root,
            extras=extras,
            content=content,
            network_attempts=network_attempts,
            head=head,
        )
        failed = sum(1 for a in assertions if a["status"] != "PASS")
        source_commit = _git(
            str(repo_root), "log", "--format=%H", "-n", "1",
            "--", SRC_REL, TEST_REL, RUN_REL,
        )
        if not source_commit:
            source_commit = head

        content_hashes = {
            name: sha256_bytes(text.encode("utf-8"))
            for name, text in content.items()
        }
        qc = {
            "stage": QC_STAGE,
            "current_stage": CURRENT_STAGE,
            "research_action_id": RESEARCH_ACTION_ID,
            "baseline_commit": EXPECTED_BASELINE_COMMIT,
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
            "broad_codal_capture_stopped": True,
            "financial_data_researcher_verified_frozen": True,
            "active_availability_method": AVAILABILITY_METHOD,
            "active_availability_lag_months": APPROVED_LAG_MONTHS,
            "four_month_regulatory_lag_locked": True,
            "six_month_lag_superseded": True,
            "historical_six_month_decision_retained": True,
            "historical_six_month_decision_active": False,
            "conservative_six_month_lag_decision_locked": True,
            "conservative_availability_lag_locked": True,
            "row_level_publish_datetime_collection_required": False,
            "part3a_protocol_locked": True,
            "part3a_decision_locked": True,
            "part3b0_readiness": True,
            "part3b_started": True,
            "part3b1_decision_locked": True,
            "cut_a_available_at_operationalization_locked": True,
            "predictor_document_binding_mini_pilot_completed": True,
            "predictor_document_binding_evidence_collected": True,
            "document_binding_resolution_decision_locked": True,
            "predictor_available_at_evidence_collected": False,
            "pilot_cutoff_provenance_resolved": False,
            "evidence_collected": True,
            "endpoint_probe_evidence_collected": True,
            "candidate_value_evidence_collected": False,
            "pair_level_evidence_collected": True,
            "data_value_extraction_performed": False,
            "accessibility_scoring_applied": False,
            "part3b_completed": False,
            "network_extraction_performed": True,
            "part3c_leakage_safe_finalization_completed": True,
            "part4_statistical_analysis_plan_locked": True,
            "modeling_started": False,
            "stage126_started": False,
            "stage126_authorized": False,
            "modeling_authorized": False,
            "model_fit_calls": 0,
            "prediction_calls": 0,
            "final_test_accessed_for_modeling": False,
            "m2_data_collected": False,
            "m3_data_collected": False,
            "m4_data_collected": False,
            "m3_admitted": False,
            "research_pointers": {
                "last_completed_research_action_id": RESEARCH_LAST_COMPLETED,
                "next_research_action_id": RESEARCH_NEXT,
            },
            "output_sha256": dict(sorted(content_hashes.items())),
            "frozen_part3c_input_sha256": dict(sorted(pinned_after.items())),
            "assertions": assertions,
            "contract_version": CONTRACT_VERSION,
        }
        qc["failed_count"] = sum(
            1 for a in qc["assertions"] if a["status"] != "PASS"
        )
        qc["all_pass"] = qc["failed_count"] == 0
        qc_text = _json_str(qc)
        qc_hash = sha256_bytes(qc_text.encode("utf-8"))
        meta = {
            "stage": QC_STAGE,
            "current_stage": CURRENT_STAGE,
            "description": (
                "Stage125 Part 4 statistical analysis plan lock "
                "(features/samples/splits/metrics/seeds; no modeling)."
            ),
            "generated_at": source_commit,
            "code_commit": source_commit,
            "baseline_commit": EXPECTED_BASELINE_COMMIT,
            "source_file_sha256": qc["source_file_sha256"],
            "test_file_sha256": qc["test_file_sha256"],
            "output_files_sha256": dict(
                sorted({**content_hashes, F_QC: qc_hash}.items())
            ),
            "part4_statistical_analysis_plan_locked": True,
            "modeling_started": False,
            "stage126_started": False,
            "network_requests_attempted": network_attempts,
            "model_fit_calls": 0,
            "prediction_calls": 0,
            "research_pointers": qc["research_pointers"],
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
            raise QCFail(
                f"Part 4 QC failed: {qc['failed_count']} assertions failed"
            )

        return {
            "qc": qc,
            "metadata": meta,
            "output_dir": str(out_dir),
            "files": files_written,
            "drift": tracked_drift,
            "network_requests_attempted": network_attempts,
        }
