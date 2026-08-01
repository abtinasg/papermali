"""Stage127 M2 — paired incremental evaluation of M2 versus M1 (authorized).

Authorized action: ``stage127-m2-incremental-evaluation`` (one action only).

Development-only. This module:

* records the explicit human authorization byte-for-byte (Persian utterance +
  recomputed SHA-256), keeping the original text separate from the derived
  normalized scope;
* rebuilds the exact three-variable M2 common development sample by joining the
  frozen Stage126 M1 development surface to the terminal Stage128 D2 Gate
  feature table on canonical row identity;
* audits attrition from the parent M1 development surface to the common sample;
* executes the MANDATORY post-lock D2 eligibility audit (descriptive only);
* refits BOTH blocks on exactly the same common-sample training rows and
  evaluates them on exactly the same common-sample validation rows, so the
  M2-minus-M1 comparison is genuinely paired;
* computes the frozen metrics, calibration reporting and paired
  company-cluster bootstrap uncertainty;
* records the multiplicity-family status with the family left incomplete.

It parses, inspects, stores, preprocesses, fits, predicts and evaluates NO
final-test predictor or target value. The frozen two-pass streaming loader
does structurally encounter the final-test row records and rejects them before
value parsing; that is a structural skip, not a read. It performs no tuning,
no grid search, no feature search, no SMOTE, no design change, no winner
selection and no successor action.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import platform
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from src import stage126_m1_primary_development_tuning as m1

# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #

STAGE = "Stage128"
ACTION_ID = "stage127-m2-incremental-evaluation"
CONTRACT_ID = "stage127_m2_incremental_evaluation"
CONTRACT_VERSION = "stage127_m2_incremental_evaluation_v1"
ACTIVE_WORKSTREAM = "stage128_m2_d2_boundary_month_equity_return"

#: Artifacts live under the active Stage128 M2 workstream package; the ACTION
#: ID is never renamed.
OUT_DIR_REL = "project/stage128/m2_incremental_evaluation"

SRC_REL = "project/src/stage127_m2_incremental_evaluation.py"
RUN_REL = "project/run_stage127_m2_incremental_evaluation.py"
TEST_REL = "project/tests/test_stage127_m2_incremental_evaluation.py"

#: The merge commit of PR #70, which must be an ancestor of the working head.
EXPECTED_BASE_MERGE_COMMIT = "fb5f0e13cb806e0ba28f0372b3b2264881564950"


class EvaluationFail(RuntimeError):
    """Fail-closed error for this action."""


class FinalTestLockError(EvaluationFail):
    """Any attempt to touch the locked final test."""


# --------------------------------------------------------------------------- #
# Human authorization (verbatim; never replaced by the normalized scope)
# --------------------------------------------------------------------------- #

AUTHORIZATION_TEXT_FA = "بریم مرحله بعد"
AUTHORIZATION_TEXT_SHA256 = (
    "a9999c0cab0ec43d200cbc2d00112132e27c4bd7ed52e0db92ef0d5eb6c3cdc6"
)
AUTHORIZATION_DATE = "2026-08-01"
AUTHORIZATION_ID = "stage127-m2-incremental-evaluation-human-authorization"

NORMALIZED_SCOPE = (
    "Authorizes one development-only execution of "
    "stage127-m2-incremental-evaluation: the mandatory post-lock D2 "
    "eligibility audit and the paired common-sample comparison of frozen M2 "
    "versus frozen M1 under the locked temporal folds, retained model "
    "configurations, metrics and uncertainty procedures. It authorizes no "
    "final-test access, retuning, feature search, design change, successor "
    "action or Merge."
)

DOES_NOT_EXTEND_TO = [
    "merge_of_this_pr",
    "final_test_predictor_inspection",
    "final_test_target_inspection",
    "final_test_model_fit_or_evaluation",
    "full_development_refit",
    "hyperparameter_tuning_or_retuning",
    "grid_search",
    "feature_selection_or_feature_search",
    "d2_d3_jalali_redesign_or_comparison",
    "m2_gate_threshold_change",
    "temporal_fold_change",
    "sample_or_target_change",
    "m1_selected_configuration_change",
    "smote_or_any_new_imbalance_method",
    "new_model_families",
    "winner_or_retained_block_selection",
    "shap_execution",
    "causal_interpretation",
    "m3_start",
    "m4_start",
    "manuscript_superiority_claim",
    "automatic_authorization_of_any_successor_action",
]


def build_authorization_record() -> dict[str, Any]:
    """The one-action authorization; fails closed on any digest mismatch."""
    actual = hashlib.sha256(AUTHORIZATION_TEXT_FA.encode("utf-8")).hexdigest()
    if actual != AUTHORIZATION_TEXT_SHA256:
        raise EvaluationFail(
            f"authorization utterance SHA256 {actual} != "
            f"{AUTHORIZATION_TEXT_SHA256}"
        )
    return {
        "authorization_id": AUTHORIZATION_ID,
        "authorization_class": "ORIGINAL_SCIENTIFIC_AUTHORIZATION",
        "authorized_action_id": ACTION_ID,
        "authorizing_role": "human_supervisor_data_owner",
        "authorization_date": AUTHORIZATION_DATE,
        "human_source_utterance": AUTHORIZATION_TEXT_FA,
        "human_source_utterance_language": "fa",
        "human_source_utterance_sha256": AUTHORIZATION_TEXT_SHA256,
        "human_source_utterance_availability": "available_and_recorded_verbatim",
        "one_action_only": True,
        "standing_authorization": False,
        "non_transitive": True,
        "authorization_consumed_by_this_execution": True,
        "normalized_authorization_scope": NORMALIZED_SCOPE,
        "normalized_authorization_scope_is_derived_not_verbatim_human_text": (
            True
        ),
        "normalized_scope_never_replaces_original_text": True,
        "merge_authorized": False,
        "final_test_access_authorized": False,
        "final_test_evaluation_authorized": False,
        "full_development_refit_authorized": False,
        "hyperparameter_tuning_authorized": False,
        "grid_search_authorized": False,
        "feature_search_authorized": False,
        "design_change_authorized": False,
        "smote_authorized": False,
        "new_model_family_authorized": False,
        "winner_selection_authorized": False,
        "retained_block_selection_authorized": False,
        "shap_authorized": False,
        "m3_authorized": False,
        "m4_authorized": False,
        "successor_action_authorized": False,
        "does_not_extend_to": list(DOES_NOT_EXTEND_TO),
    }


def assert_authorization(record: dict[str, Any]) -> None:
    """Fail closed on any weakening of the recorded authorization."""
    if record["human_source_utterance"] != AUTHORIZATION_TEXT_FA:
        raise EvaluationFail("authorization utterance altered")
    actual = hashlib.sha256(
        record["human_source_utterance"].encode("utf-8")).hexdigest()
    if actual != AUTHORIZATION_TEXT_SHA256:
        raise EvaluationFail("authorization utterance digest mismatch")
    if record["authorization_date"] != AUTHORIZATION_DATE:
        raise EvaluationFail("authorization date altered")
    if record["authorized_action_id"] != ACTION_ID:
        raise EvaluationFail("authorized action id altered")
    if record["one_action_only"] is not True:
        raise EvaluationFail("authorization is one action only")
    if record["standing_authorization"] is not False:
        raise EvaluationFail("authorization is never standing")
    for field in (
        "merge_authorized", "final_test_access_authorized",
        "final_test_evaluation_authorized", "full_development_refit_authorized",
        "hyperparameter_tuning_authorized", "grid_search_authorized",
        "feature_search_authorized", "design_change_authorized",
        "smote_authorized", "new_model_family_authorized",
        "winner_selection_authorized", "retained_block_selection_authorized",
        "shap_authorized", "m3_authorized", "m4_authorized",
        "successor_action_authorized",
    ):
        if record[field] is not False:
            raise EvaluationFail(f"{field} must be False")


# --------------------------------------------------------------------------- #
# Frozen blocks
# --------------------------------------------------------------------------- #

#: The retained nine-feature M1 order, imported unchanged.
M1_FEATURE_ORDER: list[str] = list(m1.M1_PRIMARY_FEATURE_ORDER)

#: The three frozen M2 market variables, appended to the NESTED M1 set.
M2_MARKET_FEATURE_ORDER: list[str] = [
    "equity_return_window",
    "realized_volatility",
    "amihud_illiquidity",
]
M2_FEATURE_ORDER: list[str] = M1_FEATURE_ORDER + M2_MARKET_FEATURE_ORDER

#: ``equity_return_window`` is measured ONLY by the frozen Gregorian D2
#: construct, taken from the terminal Gate table's ``equity_return_d2`` column.
D2_SPECIFICATION = "BOUNDARY_MONTH_ASOF_TRAILING_EQUITY_RETURN"
D2_CALENDAR_CONVENTION = "GREGORIAN"
EQUITY_RETURN_SOURCE_COLUMN = "equity_return_d2"
EQUITY_RETURN_CONTRACT_FIELD = "equity_return_window"

#: Market predictors that must NOT enter the M2 block in this action.
FORBIDDEN_MARKET_FEATURES = (
    "zero_trade_day_ratio_W",
    "equity_return_window_d1",
    "equity_return_window_d3",
    "equity_return_window_jalali",
    "equity_return_window_d0_historical",
    "raw_close",
    "unadjusted_close",
)

BLOCKS = ("M1", "M2")
MODEL_FAMILIES = (
    "regularized_logistic_regression",
    "random_forest",
    "xgboost",
)

#: The retained Stage126 configurations, reused verbatim (never re-selected).
FROZEN_CONFIGURATIONS: dict[str, dict[str, Any]] = {
    "regularized_logistic_regression": {
        "configuration_id": "logistic__C_0.1",
        "hyperparameters": {
            "C": 0.1, "penalty": "l2", "solver": "liblinear",
            "max_iter": 5000, "class_weight": "balanced",
        },
    },
    "random_forest": {
        "configuration_id": "rf__depth_3__maxfeat_'sqrt'__leaf_10",
        "hyperparameters": {
            "bootstrap": True, "max_depth": 3, "max_features": "sqrt",
            "min_samples_leaf": 10, "n_estimators": 500,
            "class_weight": "balanced_subsample",
        },
    },
    "xgboost": {
        "configuration_id": "xgboost__lr_0.03__depth_2__mcw_1__lambda_1",
        "hyperparameters": {
            "learning_rate": 0.03, "max_depth": 2, "min_child_weight": 1,
            "reg_lambda": 1, "n_estimators": 300, "subsample": 0.8,
            "colsample_bytree": 0.8, "gamma": 0,
            "objective": "binary:logistic", "eval_metric": "aucpr",
            "tree_method": "hist", "early_stopping": False, "n_jobs": 1,
        },
    },
}

#: Deterministic families are fit once; stochastic families average the five
#: frozen final-OOF seeds. Tuning seeds are never used here.
DETERMINISTIC_FAMILIES = ("regularized_logistic_regression",)
FINAL_OOF_SEEDS: tuple[int, ...] = m1.FINAL_OOF_SEEDS
LOGISTIC_FIT_SEED = FINAL_OOF_SEEDS[0]

#: 2 blocks x 2 folds x (1 logistic + 5 RF + 5 XGB).
EXPECTED_PRIMARY_FIT_COUNT = 44

#: IMMUTABLE provenance of the ONE authorized scientific execution of this
#: action. Every value is a LOCKED CONSTANT verified against the metadata
#: committed by the canonical scientific artifact commit. None of it is
#: derived from ``platform``, ``importlib.metadata`` or ``origin/main``, so a
#: later ``--check``, maintenance regeneration, interpreter upgrade or
#: post-merge run cannot overwrite it.
ORIGINAL_AUTHORIZED_SCIENTIFIC_EXECUTION: dict[str, Any] = {
    "action_id": ACTION_ID,
    "authorization_sha256": AUTHORIZATION_TEXT_SHA256,
    "source_base_commit": "fb5f0e13cb806e0ba28f0372b3b2264881564950",
    "canonical_scientific_artifact_commit": (
        "96a1d6b19b91756b6a0257344c50754fb6d38c7d"
    ),
    "python_version": "3.14.0",
    "platform": "macOS-26.5.2-arm64-arm-64bit-Mach-O",
    "runtime_versions": {
        "jdatetime": "5.3.0",
        "numpy": "2.4.6",
        "pandas": "3.0.3",
        "python": "3.14.0",
        "scikit-learn": "1.9.0",
        "xgboost": "3.3.0",
    },
    "canonical_authorized_execution_count": 1,
    "scientific_decision_count": 1,
    "canonical_primary_predictive_fit_count": EXPECTED_PRIMARY_FIT_COUNT,
    "immutable_provenance": True,
    "derived_dynamically_from_current_interpreter": False,
    "overwritten_by_verification_or_maintenance": False,
}

#: What the counters above do and do not mean.
EXECUTION_COUNT_SEMANTICS = {
    "canonical_authorized_scientific_executions": 1,
    "scientific_decisions": 1,
    "canonical_primary_predictive_fits_in_that_execution": (
        EXPECTED_PRIMARY_FIT_COUNT
    ),
    "note": (
        "44 is the CANONICAL SCIENTIFIC fit count of the single authorized "
        "execution of this action — not a lifetime count of CPU-level "
        "estimator fits. `--check` and the test suite deterministically "
        "RECOMPUTE the same models to verify the committed artifacts; those "
        "recomputations are verification, not new scientific executions, "
        "they make no new scientific decision, they consume no new human "
        "authorization, and they never change the canonical counts."
    ),
    "deterministic_verification_recomputation_is_not_a_new_execution": True,
    "verification_recomputation_changes_canonical_counts": False,
}


def latest_non_scientific_verification_environment() -> dict[str, Any]:
    """Environment of the CURRENT, explicitly non-scientific rebuild/check."""
    return {
        "role": "verification_or_maintenance_regeneration_only",
        "scientific_execution": False,
        "new_scientific_decision": False,
        "new_human_authorization": False,
        "is_original_authorized_execution_environment": False,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "runtime_versions": m1.runtime_versions(),
    }

# --------------------------------------------------------------------------- #
# Frozen sample expectations (fail closed; never used to relax loading)
# --------------------------------------------------------------------------- #

EXPECTED_PARENT_DEV_ROWS = 666
EXPECTED_COMMON_ROWS = 539
EXPECTED_COMMON_POSITIVE = 55
EXPECTED_COMMON_NEGATIVE = 484
EXPECTED_COMMON_FOLD_COUNTS = {
    "fold1_train": 173,
    "fold1_validation": 159,
    "fold2_train": 332,
    "fold2_validation": 207,
}
EXPECTED_COMMON_VALIDATION_POSITIVES = {
    "fold1_validation": 18,
    "fold2_validation": 10,
}
EXPECTED_POOLED_OOF_ROWS = 366
EXPECTED_POOLED_OOF_POSITIVE = 28

#: The frozen streaming loader structurally encounters these final-test row
#: records and rejects them BEFORE parsing any predictor or target value.
#: Recording the number keeps the firewall claim literally precise: values
#: read = 0, rows structurally encountered != 0.
FINAL_TEST_ROWS_STRUCTURALLY_ENCOUNTERED = 346

D2_FEATURES_REL = "project/stage128/stage128_m2_d2_development_features.csv"
GATE_DECISION_REL = "project/stage128/stage128_m2_d2_gate_rerun_decision.json"
COMMON_SAMPLE_AUDIT_REL = (
    "project/stage128/stage128_m2_d2_common_sample_audit.json"
)
EVENT_COUNT_REL = (
    "project/stage128/stage128_m2_d2_event_count_feasibility.json"
)
SELECTED_CONFIGS_REL = "project/stage126/stage126_m1_selected_configurations.json"
RETAINED_FREEZE_REL = "project/stage126/stage126_m1_retained_design_freeze.json"

EXTERNAL_BUNDLE_SHA256 = (
    "d8456b50b7813b44789b556efcdd9ed81ee0318f85e3d9127b27807f75c6c6ec"
)
GATE_STATUS_PASS = "PASS_FOR_M2_INCREMENTAL_EVALUATION"
HISTORICAL_D0_GATE_STATUS = "FAIL_M2_DATA_GATE"

#: Frozen sources that must remain byte-identical.
FROZEN_SOURCES = (
    "project/src/stage127_m2_market_data_gate.py",
    "project/src/stage128_m2_d2_boundary_month_equity_return.py",
)

# --------------------------------------------------------------------------- #
# Metrics / calibration / uncertainty contracts
# --------------------------------------------------------------------------- #

PRIMARY_METRIC = "pr_auc"
SECONDARY_METRICS = ("roc_auc", "brier_score", "recall_at_10pct",
                     "lift_at_10pct")
ALL_METRICS = (PRIMARY_METRIC,) + SECONDARY_METRICS

CALIBRATION_BINS = 5
ISOTONIC_CALIBRATION_ALLOWED = False

BOOTSTRAP_METHOD = "paired_company_cluster_bootstrap"
BOOTSTRAP_CLUSTER = "ticker"
BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_SEED = 20260724
BOOTSTRAP_CI = 0.95
BOOTSTRAP_MIN_VALID_REPLICATES = 1000

CONFIRMATORY_FAMILY = ("M2_minus_M1", "M3_minus_M2", "M4_minus_M3")
CONFIRMATORY_FAMILY_MEMBER = "M2_minus_M1"
SMD_FLAG_THRESHOLD = 0.10

FLOAT_ROUND = m1.FLOAT_ROUND

# --------------------------------------------------------------------------- #
# Output file names
# --------------------------------------------------------------------------- #

F_AUTH = "stage127_m2_incremental_evaluation_human_authorization_record.json"
F_CONTRACT = "stage127_m2_incremental_evaluation_execution_contract.json"
F_JOIN_AUDIT = "stage127_m2_common_sample_join_audit.json"
F_ATTRITION = "stage127_m2_parent_to_common_sample_attrition_audit.json"
F_ELIGIBILITY = "stage127_m2_post_lock_d2_eligibility_audit.json"
F_ELIGIBILITY_CSV = "stage127_m2_post_lock_d2_eligibility_smd.csv"
F_MANIFEST = "stage127_m2_feature_configuration_manifest.json"
F_FIT_AUDIT = "stage127_m2_predictive_fit_count_audit.json"
F_OOF = "stage127_m2_paired_oof_predictions.csv"
F_METRICS = "stage127_m2_block_model_metrics.csv"
F_CALIBRATION = "stage127_m2_calibration_report.json"
F_BOOTSTRAP = "stage127_m2_paired_bootstrap_delta_summary.json"
F_MULTIPLICITY = "stage127_m2_multiplicity_family_status.json"
F_DECISION = "stage127_m2_incremental_evaluation_decision.json"
F_FIREWALL = "stage127_m2_final_test_firewall_audit.json"
F_QC = "stage127_m2_incremental_evaluation_qc_report.json"
F_README = "README_STAGE127_M2_INCREMENTAL_EVALUATION.md"
F_METADATA = "metadata_and_hashes_stage127_m2_incremental_evaluation.json"

TRACKED_CONTENT_FILES = (
    F_AUTH, F_CONTRACT, F_JOIN_AUDIT, F_ATTRITION, F_ELIGIBILITY,
    F_ELIGIBILITY_CSV, F_MANIFEST, F_FIT_AUDIT, F_OOF, F_METRICS,
    F_CALIBRATION, F_BOOTSTRAP, F_MULTIPLICITY, F_DECISION, F_FIREWALL,
    F_QC, F_README,
)

OOF_COLUMNS = [
    "model_family", "configuration_id", "temporal_fold", "ticker",
    "fiscal_year_t", "target_year", "predictor_row_key_t",
    "target_row_key_t_plus_1", "target",
    "m1_probability", "m2_probability", "m2_minus_m1_probability",
    "seed_aggregation",
]

METRICS_COLUMNS = [
    "model_family", "configuration_id", "scope", "block", "n_rows",
    "n_positive", "k_top10", "pr_auc", "roc_auc", "brier_score",
    "recall_at_10pct", "lift_at_10pct",
]

SMD_COLUMNS = [
    "dimension", "variable", "type", "eligible_n", "ineligible_n",
    "eligible_summary", "ineligible_summary", "smd", "abs_smd",
    "imbalance_flag", "availability", "note",
]


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #

def _round(x: float) -> float:
    if x is None:
        return None
    x = float(x)
    if math.isnan(x):
        return None
    return round(x, FLOAT_ROUND)


def json_dumps(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def csv_text(header: list[str], rows: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=header, lineterminator="\n")
    w.writeheader()
    for row in rows:
        w.writerow({k: _fmt(row.get(k)) for k in header})
    return buf.getvalue()


def _fmt(v: Any) -> Any:
    if v is None:
        return ""
    if isinstance(v, float):
        if math.isnan(v):
            return ""
        return repr(_round(v))
    return v


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _git(repo_root: Path, *args: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return ""


def repo_root_from(project_dir: Path) -> Path:
    return Path(project_dir).resolve().parent


# --------------------------------------------------------------------------- #
# Frozen-input verification
# --------------------------------------------------------------------------- #

def verify_frozen_inputs(repo_root: Path) -> dict[str, Any]:
    """Fail closed unless every immutable authority is present and terminal."""
    gate = json.loads(
        (repo_root / GATE_DECISION_REL).read_text(encoding="utf-8"))
    if gate["gate_status"] != GATE_STATUS_PASS:
        raise EvaluationFail(
            f"Stage128 D2 Gate status {gate['gate_status']} != {GATE_STATUS_PASS}"
        )
    if gate["historical_d0_gate_status"] != HISTORICAL_D0_GATE_STATUS:
        raise EvaluationFail("historical D0 Gate status altered")
    if gate["external_delivery"]["bundle_sha256"] != EXTERNAL_BUNDLE_SHA256:
        raise EvaluationFail("external evidence bundle SHA256 mismatch")
    if gate["equity_return_measurement_specification"] != D2_SPECIFICATION:
        raise EvaluationFail("equity-return specification is not the frozen D2")

    selected = json.loads(
        (repo_root / SELECTED_CONFIGS_REL).read_text(encoding="utf-8"))
    for family, frozen in FROZEN_CONFIGURATIONS.items():
        if selected[family]["configuration_id"] != frozen["configuration_id"]:
            raise EvaluationFail(
                f"{family} configuration id drifted from the Stage126 freeze"
            )

    head = _git(repo_root, "rev-parse", "HEAD")
    ancestor = subprocess.run(
        ["git", "-C", str(repo_root), "merge-base", "--is-ancestor",
         EXPECTED_BASE_MERGE_COMMIT, "HEAD"],
        capture_output=True, text=True,
    ).returncode == 0 if head else False

    return {
        "gate_status": gate["gate_status"],
        "historical_d0_gate_status": gate["historical_d0_gate_status"],
        "external_bundle_sha256": EXTERNAL_BUNDLE_SHA256,
        "equity_return_measurement_specification": D2_SPECIFICATION,
        "equity_return_calendar_convention": D2_CALENDAR_CONVENTION,
        "pr70_merge_commit": EXPECTED_BASE_MERGE_COMMIT,
        "pr70_merge_commit_is_ancestor_of_head": ancestor,
        "frozen_sources_sha256": {
            rel: sha256_file(repo_root / rel) for rel in FROZEN_SOURCES
        },
        "frozen_authority_sha256": {
            rel: sha256_file(repo_root / rel) for rel in (
                GATE_DECISION_REL, D2_FEATURES_REL, COMMON_SAMPLE_AUDIT_REL,
                EVENT_COUNT_REL, SELECTED_CONFIGS_REL, RETAINED_FREEZE_REL,
                "project/stage125/part4_statistical_analysis_plan_stage125.json",
                "project/stage125/part4_temporal_split_contract_stage125.json",
                "project/stage125/part4_temporal_split_manifest_stage125.csv",
                "project/stage125/part4_preprocessing_contract_stage125.json",
                "project/stage125/part4_model_specifications_stage125.json",
                "project/stage125/part4_metrics_uncertainty_contract_stage125.json",
                "project/docs/ai/STAGE128_M2_D2_DESIGN_FREEZE.md",
            )
        },
        "stage127_historical_artifacts_modified": False,
        "gate_decision_modified": False,
    }


# --------------------------------------------------------------------------- #
# D2 market table + industry side-table
# --------------------------------------------------------------------------- #

def load_d2_features(repo_root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    """Read the terminal Gate feature table, keyed by (ticker, fiscal_year_t)."""
    path = repo_root / D2_FEATURES_REL
    out: dict[tuple[str, str], dict[str, Any]] = {}
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        header = set(reader.fieldnames or [])
        required = {
            "ticker", "fiscal_year_t", "target_year", "temporal_folds",
            EQUITY_RETURN_SOURCE_COLUMN, "realized_volatility",
            "amihud_illiquidity", "in_three_variable_common_sample",
            "d2_status", "window_trading_day_count", "usable_daily_return_count",
            "usable_amihud_day_count", "missing_price_day_count",
            "zero_traded_value_day_count",
        }
        missing = required - header
        if missing:
            raise EvaluationFail(f"D2 feature table missing: {sorted(missing)}")
        for row in reader:
            key = (row["ticker"], str(int(row["fiscal_year_t"])))
            if key in out:
                raise EvaluationFail(f"duplicate D2 row for {key}")
            out[key] = row
    if len(out) != EXPECTED_PARENT_DEV_ROWS:
        raise EvaluationFail(
            f"D2 table has {len(out)} rows != {EXPECTED_PARENT_DEV_ROWS}")
    return out


def load_development_industry(
    repo_root: Path, allowlist: dict[str, Any],
) -> dict[tuple[str, str], str]:
    """Industry label for DEVELOPMENT keys only (an audit dimension).

    Final-test rows are skipped without parsing any value.
    """
    dev_pairs = allowlist["dev_pairs"]
    denylist = allowlist["denylist_pairs"]
    out: dict[tuple[str, str], str] = {}
    path = repo_root / m1.ANALYSIS_READY_REL
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if "industry" not in (reader.fieldnames or []):
            return {}
        for row in reader:
            key = (row["predictor_row_key_t"], row["target_row_key_t_plus_1"])
            if key in dev_pairs:
                out[key] = (row.get("industry") or "").strip()
            elif key in denylist:
                continue
    return out


# --------------------------------------------------------------------------- #
# Common-sample construction
# --------------------------------------------------------------------------- #

def _float_or_nan(raw: str) -> float:
    raw = (raw or "").strip()
    return math.nan if raw == "" else float(raw)


def build_common_sample(
    repo_root: Path,
) -> dict[str, Any]:
    """Join the M1 development surface to the D2 table on canonical identity."""
    allowlist = m1.build_development_allowlist(repo_root)
    loaded = m1.load_development_values(repo_root, allowlist)
    rows = loaded["rows"]
    if len(rows) != EXPECTED_PARENT_DEV_ROWS:
        raise EvaluationFail("parent development row count mismatch")

    d2 = load_d2_features(repo_root)
    industry = load_development_industry(repo_root, allowlist)

    join_stats = {
        "join_keys": ["ticker", "fiscal_year_t"],
        "canonical_row_identity": [
            "ticker", "fiscal_year_t", "predictor_row_key_t",
            "target_row_key_t_plus_1", "target_year", "temporal_fold_role",
        ],
        "parent_rows": len(rows),
        "d2_rows": len(d2),
        "matched_rows": 0,
        "unmatched_parent_rows": 0,
        "unmatched_d2_rows": 0,
        "duplicate_join_keys": 0,
        "many_to_many_joins": 0,
        "target_year_disagreements": 0,
        "fold_role_disagreements": 0,
        "final_test_rows_in_join": 0,
    }

    seen_join_keys: set[tuple[str, str]] = set()
    records: dict[tuple[str, str], dict[str, Any]] = {}
    for key, info in rows.items():
        jkey = (info["ticker"], str(int(info["fiscal_year_t"])))
        if jkey in seen_join_keys:
            join_stats["duplicate_join_keys"] += 1
            raise EvaluationFail(f"duplicate join key {jkey} (fail-closed)")
        seen_join_keys.add(jkey)
        mrow = d2.get(jkey)
        if mrow is None:
            join_stats["unmatched_parent_rows"] += 1
            raise EvaluationFail(f"parent row {jkey} has no D2 row")
        join_stats["matched_rows"] += 1
        if int(mrow["target_year"]) != int(info["target_year"]):
            join_stats["target_year_disagreements"] += 1
            raise EvaluationFail(f"target_year disagreement at {jkey}")
        if int(info["target_year"]) in m1.FINAL_TEST_TARGET_YEARS:
            join_stats["final_test_rows_in_join"] += 1
            raise FinalTestLockError("final-test target year reached the join")
        roles = set(allowlist["dev_pairs"][key]["roles"])
        d2_roles = set(mrow["temporal_folds"].split(","))
        if roles != d2_roles:
            join_stats["fold_role_disagreements"] += 1
            raise EvaluationFail(f"fold-role disagreement at {jkey}")
        records[key] = {
            "pair_key": key,
            "join_key": jkey,
            "ticker": info["ticker"],
            "fiscal_year_t": str(int(info["fiscal_year_t"])),
            "target_year": int(info["target_year"]),
            "predictor_row_key_t": info["predictor_row_key_t"],
            "target_row_key_t_plus_1": info["target_row_key_t_plus_1"],
            "roles": roles,
            "target": info["target"],
            "m1_features": info["features"],
            "industry": industry.get(key, ""),
            "in_common_sample": mrow["in_three_variable_common_sample"] == "True",
            "d2_status": mrow["d2_status"],
            "equity_return_window": _float_or_nan(
                mrow[EQUITY_RETURN_SOURCE_COLUMN]),
            "realized_volatility": _float_or_nan(mrow["realized_volatility"]),
            "amihud_illiquidity": _float_or_nan(mrow["amihud_illiquidity"]),
            "window_trading_day_count": int(mrow["window_trading_day_count"]),
            "usable_daily_return_count": int(mrow["usable_daily_return_count"]),
            "usable_amihud_day_count": int(mrow["usable_amihud_day_count"]),
            "missing_price_day_count": int(mrow["missing_price_day_count"]),
            "zero_traded_value_day_count": int(
                mrow["zero_traded_value_day_count"]),
        }
    join_stats["unmatched_d2_rows"] = len(d2) - join_stats["matched_rows"]

    for rec in records.values():
        wtd = rec["window_trading_day_count"]
        rec["zero_trade_day_ratio_W"] = (
            rec["zero_traded_value_day_count"] / wtd if wtd > 0 else math.nan
        )

    common = {k: v for k, v in records.items() if v["in_common_sample"]}
    if len(common) != EXPECTED_COMMON_ROWS:
        raise EvaluationFail(
            f"common sample {len(common)} != {EXPECTED_COMMON_ROWS}")
    pos = sum(1 for v in common.values() if v["target"] == 1.0)
    neg = sum(1 for v in common.values() if v["target"] == 0.0)
    if pos != EXPECTED_COMMON_POSITIVE or neg != EXPECTED_COMMON_NEGATIVE:
        raise EvaluationFail(
            f"common composition {pos}/{neg} != "
            f"{EXPECTED_COMMON_POSITIVE}/{EXPECTED_COMMON_NEGATIVE}")
    for rec in common.values():
        for feat in M2_MARKET_FEATURE_ORDER:
            if math.isnan(rec[feat]):
                raise EvaluationFail(
                    f"common-sample row {rec['join_key']} missing {feat}")

    role_keys: dict[str, list[tuple[str, str]]] = {}
    for role in m1.DEV_ROLES:
        role_keys[role] = sorted(
            k for k, v in common.items() if role in v["roles"])
        got = len(role_keys[role])
        exp = EXPECTED_COMMON_FOLD_COUNTS[role]
        if got != exp:
            raise EvaluationFail(f"common {role} count {got} != {exp}")
    for role, exp in EXPECTED_COMMON_VALIDATION_POSITIVES.items():
        got = sum(1 for k in role_keys[role] if common[k]["target"] == 1.0)
        if got != exp:
            raise EvaluationFail(
                f"common {role} positives {got} != {exp}")

    pooled = sorted(role_keys["fold1_validation"] + role_keys["fold2_validation"])
    if len(set(pooled)) != len(pooled):
        raise EvaluationFail("validation windows overlap (fail-closed)")
    if len(pooled) != EXPECTED_POOLED_OOF_ROWS:
        raise EvaluationFail(
            f"pooled OOF rows {len(pooled)} != {EXPECTED_POOLED_OOF_ROWS}")
    pooled_pos = sum(1 for k in pooled if common[k]["target"] == 1.0)
    if pooled_pos != EXPECTED_POOLED_OOF_POSITIVE:
        raise EvaluationFail(
            f"pooled OOF positives {pooled_pos} != "
            f"{EXPECTED_POOLED_OOF_POSITIVE}")

    join_stats["common_rows"] = len(common)
    join_stats["common_positive"] = pos
    join_stats["common_negative"] = neg
    join_stats["pooled_oof_rows"] = len(pooled)
    join_stats["pooled_oof_positive"] = pooled_pos
    join_stats["join_is_one_to_one"] = True
    join_stats["duplicate_joins_rejected"] = True
    join_stats["many_to_many_rejected"] = True
    join_stats["final_test_rows_loaded"] = 0
    join_stats["final_test_rows_seen_and_skipped"] = loaded["final_test_rows_seen"]

    return {
        "allowlist": allowlist,
        "records": records,
        "common": common,
        "role_keys": role_keys,
        "pooled_validation_keys": pooled,
        "join_audit": join_stats,
    }


# --------------------------------------------------------------------------- #
# Attrition audit
# --------------------------------------------------------------------------- #

def build_attrition_audit(sample: dict[str, Any]) -> dict[str, Any]:
    """Parent M1 surface -> M2 common sample. Reported, never concealed."""
    records = sample["records"]
    common = sample["common"]
    allowlist = sample["allowlist"]

    def _compose(keys) -> dict[str, Any]:
        keys = list(keys)
        pos = sum(1 for k in keys if records[k]["target"] == 1.0)
        return {
            "rows": len(keys),
            "positive": pos,
            "negative": len(keys) - pos,
            "companies": len({records[k]["ticker"] for k in keys}),
            "event_rate": _round(pos / len(keys)) if keys else None,
        }

    parent_keys = list(records)
    common_keys = list(common)
    dropped = [k for k in parent_keys if k not in common]

    parent_folds = {}
    common_folds = {}
    for role in m1.DEV_ROLES:
        parent_folds[role] = _compose(
            k for k in parent_keys if role in allowlist["dev_pairs"][k]["roles"])
        common_folds[role] = _compose(sample["role_keys"][role])

    parent_pooled = sorted(
        {k for k in parent_keys
         if allowlist["dev_pairs"][k]["roles"] & {
             "fold1_validation", "fold2_validation"}})
    by_year = {}
    for year in sorted({r["target_year"] for r in records.values()}):
        by_year[str(year)] = {
            "parent": _compose(
                k for k in parent_keys if records[k]["target_year"] == year),
            "common": _compose(
                k for k in common_keys if records[k]["target_year"] == year),
        }

    return {
        "parent_surface": "stage126-m1-financial-baseline development surface",
        "parent_development": _compose(parent_keys),
        "common_sample": _compose(common_keys),
        "dropped_by_d2_ineligibility": _compose(dropped),
        "parent_fold_counts": parent_folds,
        "common_fold_counts": common_folds,
        "parent_pooled_oof": _compose(parent_pooled),
        "common_pooled_oof": _compose(sample["pooled_validation_keys"]),
        "by_target_year": by_year,
        "attrition_rows": len(parent_keys) - len(common_keys),
        "attrition_fraction": _round(
            (len(parent_keys) - len(common_keys)) / len(parent_keys)),
        "attrition_is_reported_not_concealed": True,
        "attrition_is_not_model_improvement": True,
        "interpretation_note": (
            "The M2 common sample is a strict subset of the parent M1 "
            "development surface. Any metric difference against the ORIGINAL "
            "666-row M1 results reflects sample restriction, not model "
            "improvement; that comparison is deliberately not made here. Only "
            "the paired same-row M1-versus-M2 comparison is interpreted."
        ),
    }


# --------------------------------------------------------------------------- #
# Post-lock D2 eligibility audit (descriptive only)
# --------------------------------------------------------------------------- #

def _smd_continuous(a: list[float], b: list[float]) -> float:
    a = [x for x in a if not math.isnan(x)]
    b = [x for x in b if not math.isnan(x)]
    if len(a) < 2 or len(b) < 2:
        return math.nan
    ma, mb = float(np.mean(a)), float(np.mean(b))
    va, vb = float(np.var(a, ddof=1)), float(np.var(b, ddof=1))
    pooled = math.sqrt((va + vb) / 2.0)
    if pooled == 0.0:
        return math.nan
    return (ma - mb) / pooled


def _smd_binary(pa: float, pb: float) -> float:
    pooled = (pa * (1 - pa) + pb * (1 - pb)) / 2.0
    if pooled <= 0.0:
        return math.nan
    return (pa - pb) / math.sqrt(pooled)


def build_eligibility_audit(sample: dict[str, Any]) -> tuple[dict, list[dict]]:
    """MANDATORY post-lock predictor-side audit. Descriptive only."""
    records = sample["records"]
    elig = [r for r in records.values() if r["in_common_sample"]]
    inel = [r for r in records.values() if not r["in_common_sample"]]
    rows: list[dict[str, Any]] = []

    def _cont(dimension: str, variable: str, getter, note: str = "") -> None:
        a = [getter(r) for r in elig]
        b = [getter(r) for r in inel]
        a_obs = [x for x in a if not math.isnan(x)]
        b_obs = [x for x in b if not math.isnan(x)]
        smd = _smd_continuous(a, b)
        rows.append({
            "dimension": dimension,
            "variable": variable,
            "type": "continuous",
            "eligible_n": len(a_obs),
            "ineligible_n": len(b_obs),
            "eligible_summary": (
                f"mean={_round(float(np.mean(a_obs)))}" if a_obs else "unavailable"
            ),
            "ineligible_summary": (
                f"mean={_round(float(np.mean(b_obs)))}" if b_obs else "unavailable"
            ),
            "smd": None if math.isnan(smd) else _round(smd),
            "abs_smd": None if math.isnan(smd) else _round(abs(smd)),
            "imbalance_flag": (
                "" if math.isnan(smd)
                else ("FLAG" if abs(smd) >= SMD_FLAG_THRESHOLD else "")
            ),
            "availability": "available" if a_obs and b_obs else "unavailable",
            "note": note,
        })

    def _cat(dimension: str, variable: str, getter, note: str = "") -> None:
        levels = sorted({getter(r) for r in records.values() if getter(r) != ""})
        if not levels:
            rows.append({
                "dimension": dimension, "variable": variable,
                "type": "categorical", "eligible_n": 0, "ineligible_n": 0,
                "eligible_summary": "unavailable",
                "ineligible_summary": "unavailable",
                "smd": None, "abs_smd": None, "imbalance_flag": "",
                "availability": "unavailable",
                "note": note or "field not present in the frozen sources",
            })
            return
        for lvl in levels:
            pa = sum(1 for r in elig if getter(r) == lvl) / len(elig)
            pb = sum(1 for r in inel if getter(r) == lvl) / len(inel)
            smd = _smd_binary(pa, pb)
            rows.append({
                "dimension": dimension,
                "variable": f"{variable}={lvl}",
                "type": "categorical_level",
                "eligible_n": sum(1 for r in elig if getter(r) == lvl),
                "ineligible_n": sum(1 for r in inel if getter(r) == lvl),
                "eligible_summary": f"proportion={_round(pa)}",
                "ineligible_summary": f"proportion={_round(pb)}",
                "smd": None if math.isnan(smd) else _round(smd),
                "abs_smd": None if math.isnan(smd) else _round(abs(smd)),
                "imbalance_flag": (
                    "" if math.isnan(smd)
                    else ("FLAG" if abs(smd) >= SMD_FLAG_THRESHOLD else "")
                ),
                "availability": "available",
                "note": note,
            })

    # 1. prediction cohort / target year
    _cat("prediction_cohort", "target_year",
         lambda r: str(r["target_year"]))
    # 2. industry
    _cat("industry", "industry", lambda r: r["industry"])
    # 3. firm size (the frozen M1 size predictor, pre-imputation)
    size_idx = M1_FEATURE_ORDER.index("log_total_assets")
    _cont("firm_size", "log_total_assets",
          lambda r: float(r["m1_features"][size_idx]),
          "frozen M1 predictor, pre-imputation values")
    # 4. zero-trade day ratio (audit-only; never an M2 predictor here)
    _cont("market_activity", "zero_trade_day_ratio_W",
          lambda r: r["zero_trade_day_ratio_W"],
          "audit-only diagnostic; explicitly NOT an M2 block feature")
    # 5. market activity / traded-value diagnostics
    for var in ("window_trading_day_count", "usable_daily_return_count",
                "usable_amihud_day_count", "missing_price_day_count",
                "zero_traded_value_day_count"):
        _cont("market_activity_and_traded_value", var,
              lambda r, v=var: float(r[v]))
    # 6. M1 predictor availability (per-feature observed rate + overall count)
    for i, feat in enumerate(M1_FEATURE_ORDER):
        _cont("m1_predictor_availability", f"{feat}__observed",
              lambda r, i=i: 0.0 if math.isnan(
                  float(r["m1_features"][i])) else 1.0)
    _cont("m1_predictor_availability", "m1_observed_feature_count",
          lambda r: float(sum(
              0 if math.isnan(float(x)) else 1 for x in r["m1_features"])))

    flagged = [r for r in rows if r["imbalance_flag"] == "FLAG"]
    unavailable = [r for r in rows if r["availability"] == "unavailable"]

    # Distress-rate comparison: post-lock, descriptive, strictly separated.
    e_pos = sum(1 for r in elig if r["target"] == 1.0)
    i_pos = sum(1 for r in inel if r["target"] == 1.0)
    outcome_side = {
        "label": "post_lock_descriptive_distress_rate_comparison",
        "separated_from_predictor_side_audit": True,
        "permitted_because_design_is_locked": True,
        "eligible_rows": len(elig),
        "eligible_positive": e_pos,
        "eligible_distress_rate": _round(e_pos / len(elig)),
        "ineligible_rows": len(inel),
        "ineligible_positive": i_pos,
        "ineligible_distress_rate": _round(i_pos / len(inel)),
        "difference_eligible_minus_ineligible": _round(
            e_pos / len(elig) - i_pos / len(inel)),
        "used_to_change_d2": False,
        "used_to_change_sample_rule": False,
        "used_to_change_model_configuration": False,
        "used_to_change_interpretation_protocol": False,
        "is_descriptive_only": True,
    }

    audit = {
        "audit_id": "stage127-m2-post-lock-d2-eligibility-audit",
        "executed_before_interpreting_predictive_results": True,
        "eligible_definition": (
            "development pairs inside the terminal Stage128 D2 three-variable "
            "M2 common sample"
        ),
        "eligible_rows": len(elig),
        "ineligible_rows": len(inel),
        "required_dimensions": [
            "prediction_cohort_target_year", "industry", "firm_size",
            "zero_trade_day_ratio_W",
            "market_activity_and_traded_value_diagnostics",
            "m1_predictor_availability",
        ],
        "required_dimensions_attempted": True,
        "dimension_count": len({r["dimension"] for r in rows}),
        "comparison_count": len(rows),
        "smd_flag_threshold": SMD_FLAG_THRESHOLD,
        "smd_is_descriptive_flag_only": True,
        "smd_is_not_an_exclusion_threshold": True,
        "rows_removed_due_to_smd": 0,
        "weighting_applied": False,
        "matching_applied": False,
        "sample_repair_applied": False,
        "m2_feature_changed_by_audit": False,
        "boundary_rule_changed_by_audit": False,
        "gate_result_revised_by_audit": False,
        "model_design_changed_by_audit": False,
        "audit_stops_model_execution": False,
        "flagged_comparison_count": len(flagged),
        "flagged_comparisons": [
            {"variable": r["variable"], "smd": r["smd"]} for r in flagged
        ],
        "unavailable_field_count": len(unavailable),
        "unavailable_fields": [
            {"variable": r["variable"], "note": r["note"]} for r in unavailable
        ],
        "post_lock_outcome_side_comparison": outcome_side,
        "interpretation_consequence": (
            "Imbalance flags limit INTERPRETATION only. They are recorded in "
            "the limitations of the decision artifact and never remove a row, "
            "reweight the sample, alter D2, alter the model or revise the Gate."
        ),
    }
    return audit, rows


# --------------------------------------------------------------------------- #
# Modeling
# --------------------------------------------------------------------------- #

def _block_matrix(
    common: dict[tuple[str, str], dict[str, Any]],
    keys: list[tuple[str, str]],
    block: str,
) -> np.ndarray:
    if block == "M1":
        return np.vstack([common[k]["m1_features"] for k in keys])
    if block == "M2":
        return np.vstack([
            np.concatenate([
                common[k]["m1_features"],
                np.array([common[k][f] for f in M2_MARKET_FEATURE_ORDER],
                         dtype=float),
            ])
            for k in keys
        ])
    raise EvaluationFail(f"unknown block {block}")


def _targets(common, keys) -> np.ndarray:
    return np.array([common[k]["target"] for k in keys], dtype=float)


def run_paired_evaluation(sample: dict[str, Any]) -> dict[str, Any]:
    """Refit BOTH blocks on identical rows; predict on identical rows."""
    common = sample["common"]
    role_keys = sample["role_keys"]
    fit_log: list[dict[str, Any]] = []
    predictions: dict[tuple[str, str], dict[str, Any]] = {}

    for fold, spec in m1.FOLD_SPEC.items():
        train_role = spec["train_role"]
        val_role = spec["validation_role"]
        tr_keys = role_keys[train_role]
        va_keys = role_keys[val_role]
        if set(tr_keys) & set(va_keys):
            raise EvaluationFail(f"{fold}: train/validation overlap")
        ytr = _targets(common, tr_keys)
        yva = _targets(common, va_keys)
        if np.isnan(ytr).any() or np.isnan(yva).any():
            raise EvaluationFail(f"{fold}: missing target in common sample")

        for family in MODEL_FAMILIES:
            cfg = FROZEN_CONFIGURATIONS[family]
            hp = cfg["hyperparameters"]
            standardize = m1._requires_standardization(family)
            seeds = ((LOGISTIC_FIT_SEED,) if family in DETERMINISTIC_FAMILIES
                     else FINAL_OOF_SEEDS)
            per_block: dict[str, np.ndarray] = {}
            for block in BLOCKS:
                Xtr_raw = _block_matrix(common, tr_keys, block)
                Xva_raw = _block_matrix(common, va_keys, block)
                # Preprocessing parameters come ONLY from this training fold.
                pre = m1.fit_preprocessor(Xtr_raw, standardize=standardize)
                Xtr = m1.transform(Xtr_raw, pre)
                Xva = m1.transform(Xva_raw, pre)
                probs = []
                for seed in seeds:
                    p = m1._fit_predict(family, hp, seed, Xtr, ytr, Xva)
                    probs.append(np.asarray(p, dtype=float))
                    fit_log.append({
                        "block": block, "fold": fold, "family": family,
                        "configuration_id": cfg["configuration_id"],
                        "seed": seed,
                        "train_rows": len(tr_keys),
                        "train_positive": int((ytr == 1).sum()),
                        "train_negative": int((ytr == 0).sum()),
                        "scale_pos_weight": (
                            _round(int((ytr == 0).sum()) / int((ytr == 1).sum()))
                            if family == "xgboost" else None
                        ),
                    })
                per_block[block] = np.mean(np.vstack(probs), axis=0)
            for i, key in enumerate(va_keys):
                rec = common[key]
                predictions[(family, key)] = {
                    "model_family": family,
                    "configuration_id": cfg["configuration_id"],
                    "temporal_fold": val_role,
                    "ticker": rec["ticker"],
                    "fiscal_year_t": rec["fiscal_year_t"],
                    "target_year": rec["target_year"],
                    "predictor_row_key_t": rec["predictor_row_key_t"],
                    "target_row_key_t_plus_1": rec["target_row_key_t_plus_1"],
                    "target": int(rec["target"]),
                    "m1_probability": float(per_block["M1"][i]),
                    "m2_probability": float(per_block["M2"][i]),
                    "m2_minus_m1_probability": float(
                        per_block["M2"][i] - per_block["M1"][i]),
                    "seed_aggregation": (
                        "deterministic_single_fit"
                        if family in DETERMINISTIC_FAMILIES
                        else "mean_of_5_frozen_final_oof_seeds"
                    ),
                }

    if len(fit_log) != EXPECTED_PRIMARY_FIT_COUNT:
        raise EvaluationFail(
            f"primary predictive fit count {len(fit_log)} != "
            f"{EXPECTED_PRIMARY_FIT_COUNT}")
    return {"fit_log": fit_log, "predictions": predictions}


def oof_rows(evaluation: dict[str, Any]) -> list[dict[str, Any]]:
    rows = list(evaluation["predictions"].values())
    rows.sort(key=lambda r: (
        r["model_family"], r["temporal_fold"], r["ticker"],
        r["fiscal_year_t"]))
    return rows


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #

def _metrics_for(rows: list[dict[str, Any]], prob_key: str) -> dict[str, Any]:
    y = np.array([r["target"] for r in rows], dtype=float)
    p = np.array([r[prob_key] for r in rows], dtype=float)
    tickers = [r["ticker"] for r in rows]
    years = [r["target_year"] for r in rows]
    return m1.compute_metrics(y, p, tickers, years)


def build_metrics_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for family in MODEL_FAMILIES:
        fam_rows = [r for r in rows if r["model_family"] == family]
        cfg = FROZEN_CONFIGURATIONS[family]["configuration_id"]
        scopes = [("pooled_oof", fam_rows)]
        for role in ("fold1_validation", "fold2_validation"):
            scopes.append(
                (role, [r for r in fam_rows if r["temporal_fold"] == role]))
        for scope, subset in scopes:
            if not subset:
                continue
            m1m = _metrics_for(subset, "m1_probability")
            m2m = _metrics_for(subset, "m2_probability")
            for block, mets in (("M1", m1m), ("M2", m2m)):
                out.append({
                    "model_family": family, "configuration_id": cfg,
                    "scope": scope, "block": block, **mets,
                })
            out.append({
                "model_family": family, "configuration_id": cfg,
                "scope": scope, "block": "M2_minus_M1",
                "n_rows": m1m["n_rows"], "n_positive": m1m["n_positive"],
                "k_top10": m1m["k_top10"],
                **{k: _round(m2m[k] - m1m[k]) for k in ALL_METRICS},
            })
    return out


# --------------------------------------------------------------------------- #
# Calibration
# --------------------------------------------------------------------------- #

def _calibration_curve(y: np.ndarray, p: np.ndarray, bins: int) -> list[dict]:
    order = np.argsort(p, kind="stable")
    chunks = np.array_split(order, bins)
    out = []
    for i, idx in enumerate(chunks):
        if idx.size == 0:
            continue
        out.append({
            "bin": i + 1,
            "n_rows": int(idx.size),
            "mean_predicted_probability": _round(float(p[idx].mean())),
            "observed_event_rate": _round(float(y[idx].mean())),
            "n_positive": int(y[idx].sum()),
        })
    return out


def _calibration_fit(y: np.ndarray, p: np.ndarray) -> dict[str, Any]:
    """Calibration intercept/slope from a logistic fit on logit(p)."""
    eps = 1e-12
    pc = np.clip(p, eps, 1 - eps)
    logit = np.log(pc / (1 - pc))
    if len(set(y.tolist())) < 2 or float(np.std(logit)) == 0.0:
        return {
            "estimable": False,
            "reason": (
                "outcome is single-class or the logit of the predicted "
                "probability has zero variance"
            ),
            "calibration_intercept": None,
            "calibration_slope": None,
        }
    try:
        from sklearn.linear_model import LogisticRegression
        # Effectively unpenalized; a very large C is used instead of
        # `penalty=None` so the fit is stable across scikit-learn versions.
        clf = LogisticRegression(C=1e12, solver="lbfgs", max_iter=10000)
        clf.fit(logit.reshape(-1, 1), y)
        slope = float(clf.coef_[0][0])
        intercept = float(clf.intercept_[0])
        if not (math.isfinite(slope) and math.isfinite(intercept)):
            raise ValueError("non-finite calibration coefficients")
        unstable = abs(slope) > 50.0
        return {
            "estimable": True,
            "calibration_intercept": _round(intercept),
            "calibration_slope": _round(slope),
            "unstable": unstable,
            "reason": "separation-like instability" if unstable else "",
        }
    except Exception as exc:  # pragma: no cover - reported, never fabricated
        return {
            "estimable": False,
            "reason": f"not estimable: {type(exc).__name__}: {exc}",
            "calibration_intercept": None,
            "calibration_slope": None,
        }


def build_calibration_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    from sklearn.metrics import brier_score_loss
    out: dict[str, Any] = {
        "probability_surface": "raw_locked_pipeline_probabilities",
        "primary_probabilities_are_raw": True,
        "isotonic_calibration_allowed": ISOTONIC_CALIBRATION_ALLOWED,
        "isotonic_calibration_executed": False,
        "platt_recalibration_executed": False,
        "recalibrated_probabilities_used_as_primary_surface": False,
        "recalibration_influenced_conclusion": False,
        "recalibration_influenced_family_selection": False,
        "recalibration_influenced_block_retention": False,
        "bins": CALIBRATION_BINS,
        "by_family": {},
    }
    for family in MODEL_FAMILIES:
        fam = [r for r in rows if r["model_family"] == family]
        y = np.array([r["target"] for r in fam], dtype=float)
        entry = {}
        for block, key in (("M1", "m1_probability"), ("M2", "m2_probability")):
            p = np.array([r[key] for r in fam], dtype=float)
            entry[block] = {
                "n_rows": int(y.size),
                "n_positive": int(y.sum()),
                "brier_score": _round(float(brier_score_loss(y, p))),
                "calibration_curve_quantile_bins": _calibration_curve(
                    y, p, CALIBRATION_BINS),
                **_calibration_fit(y, p),
            }
        out["by_family"][family] = entry
    return out


# --------------------------------------------------------------------------- #
# Paired company-cluster bootstrap
# --------------------------------------------------------------------------- #

def _metric_value(y, p, tickers, years, metric: str) -> float:
    mets = m1.compute_metrics(y, p, tickers, years)
    v = mets[metric]
    return math.nan if v is None else float(v)


def run_paired_bootstrap(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Same resampled companies and rows for BOTH blocks in every replicate."""
    summary: dict[str, Any] = {
        "method": BOOTSTRAP_METHOD,
        "cluster": BOOTSTRAP_CLUSTER,
        "replicates_attempted": BOOTSTRAP_REPLICATES,
        "seed": BOOTSTRAP_SEED,
        "confidence_interval": BOOTSTRAP_CI,
        "interval_type": "percentile",
        "minimum_valid_replicates": BOOTSTRAP_MIN_VALID_REPLICATES,
        "valid_replicate_requires_both_classes": True,
        "same_resampled_rows_for_both_blocks": True,
        "models_refit_during_bootstrap": False,
        "primary_metric": PRIMARY_METRIC,
        "by_family": {},
    }
    for family in MODEL_FAMILIES:
        fam = [r for r in rows if r["model_family"] == family]
        tickers = sorted({r["ticker"] for r in fam})
        by_ticker: dict[str, list[int]] = {t: [] for t in tickers}
        for i, r in enumerate(fam):
            by_ticker[r["ticker"]].append(i)
        y_all = np.array([r["target"] for r in fam], dtype=float)
        p1_all = np.array([r["m1_probability"] for r in fam], dtype=float)
        p2_all = np.array([r["m2_probability"] for r in fam], dtype=float)
        tick_all = [r["ticker"] for r in fam]
        year_all = [r["target_year"] for r in fam]

        rng = np.random.default_rng(BOOTSTRAP_SEED)
        deltas: dict[str, list[float]] = {m: [] for m in ALL_METRICS}
        valid = 0
        for _ in range(BOOTSTRAP_REPLICATES):
            picked = rng.integers(0, len(tickers), size=len(tickers))
            idx: list[int] = []
            for j in picked:
                idx.extend(by_ticker[tickers[int(j)]])
            y = y_all[idx]
            if len(set(y.tolist())) < 2:
                continue
            p1 = p1_all[idx]
            p2 = p2_all[idx]
            tk = [tick_all[i] for i in idx]
            yr = [year_all[i] for i in idx]
            ok = True
            rep: dict[str, float] = {}
            for metric in ALL_METRICS:
                a = _metric_value(y, p1, tk, yr, metric)
                b = _metric_value(y, p2, tk, yr, metric)
                if math.isnan(a) or math.isnan(b):
                    ok = False
                    break
                rep[metric] = b - a
            if not ok:
                continue
            valid += 1
            for metric, v in rep.items():
                deltas[metric].append(v)

        point = {}
        for metric in ALL_METRICS:
            a = _metric_value(y_all, p1_all, tick_all, year_all, metric)
            b = _metric_value(y_all, p2_all, tick_all, year_all, metric)
            arr = np.array(deltas[metric], dtype=float)
            enough = valid >= BOOTSTRAP_MIN_VALID_REPLICATES and arr.size > 0
            lo = float(np.percentile(arr, 2.5)) if enough else None
            hi = float(np.percentile(arr, 97.5)) if enough else None
            point[metric] = {
                "m1_estimate": _round(a),
                "m2_estimate": _round(b),
                "m2_minus_m1_delta": _round(b - a),
                "ci_lower": _round(lo) if lo is not None else None,
                "ci_upper": _round(hi) if hi is not None else None,
                "ci_estimable": bool(enough),
                "ci_excludes_zero": (
                    bool(enough and ((lo > 0) or (hi < 0)))
                ),
                "bootstrap_delta_replicates": int(arr.size),
            }
        summary["by_family"][family] = {
            "configuration_id": FROZEN_CONFIGURATIONS[family]["configuration_id"],
            "clusters": len(tickers),
            "rows": len(fam),
            "valid_replicates": valid,
            "valid_replicate_fraction": _round(valid / BOOTSTRAP_REPLICATES),
            "minimum_valid_replicates_met": (
                valid >= BOOTSTRAP_MIN_VALID_REPLICATES),
            "metrics": point,
        }
    return summary


# --------------------------------------------------------------------------- #
# Multiplicity
# --------------------------------------------------------------------------- #

def build_multiplicity_record() -> dict[str, Any]:
    return {
        "confirmatory_family": list(CONFIRMATORY_FAMILY),
        "confirmatory_family_size": len(CONFIRMATORY_FAMILY),
        "confirmatory_family_2_member": CONFIRMATORY_FAMILY_MEMBER,
        "available_members_in_this_action": [CONFIRMATORY_FAMILY_MEMBER],
        "pending_members": [
            m for m in CONFIRMATORY_FAMILY if m != CONFIRMATORY_FAMILY_MEMBER
        ],
        "holm_family_complete": False,
        "holm_final_adjustment_deferred": True,
        "holm_adjustment_executed_in_this_action": False,
        "family_redefined_as_one_hypothesis": False,
        "one_comparison_holm_reported_as_complete_family": False,
        "additional_post_hoc_hypothesis_family_authorized": False,
        "raw_paired_uncertainty_preserved": True,
        "note": (
            "The frozen adjacent-block confirmatory family has three members; "
            "only M2_minus_M1 is observable in this action. No family-level "
            "Holm adjustment is reported, and the family is NOT silently "
            "redefined as a single-hypothesis family. Final adjustment stays "
            "deferred until the status of M3_minus_M2 and M4_minus_M3 is "
            "known."
        ),
    }


# --------------------------------------------------------------------------- #
# Firewall
# --------------------------------------------------------------------------- #

def build_firewall_audit(sample: dict[str, Any]) -> dict[str, Any]:
    return {
        "final_test_locked": True,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_predictor_values_read": 0,
        "final_test_target_values_read": 0,
        "final_test_predictions": 0,
        "final_test_model_fits": 0,
        "final_test_evaluation_performed": False,
        "final_test_rows_seen_and_skipped_without_parsing": (
            sample["join_audit"]["final_test_rows_seen_and_skipped"]
        ),
        "final_test_target_years_excluded": list(m1.FINAL_TEST_TARGET_YEARS),
        "final_test_keys_in_any_artifact": 0,
        "full_development_refits": 0,
        "m3_executions": 0,
        "m4_executions": 0,
        "smote_executions": 0,
        "shap_executions": 0,
        "grid_search_executions": 0,
        "hyperparameter_tuning_executions": 0,
        "feature_search_executions": 0,
    }


# --------------------------------------------------------------------------- #
# Decision / interpretation
# --------------------------------------------------------------------------- #

def _direction(delta: float, lo, hi) -> str:
    if lo is not None and hi is not None:
        if lo > 0:
            return "positive_with_interval_excluding_zero"
        if hi < 0:
            return "negative_with_interval_excluding_zero"
        return "approximately_null_interval_includes_zero"
    return "not_estimable"


def build_decision(
    sample, attrition, eligibility, metrics_rows, bootstrap, multiplicity,
    fit_log, firewall, frozen,
) -> dict[str, Any]:
    per_family = {}
    for family in MODEL_FAMILIES:
        b = bootstrap["by_family"][family]["metrics"][PRIMARY_METRIC]
        per_family[family] = {
            "configuration_id": FROZEN_CONFIGURATIONS[family][
                "configuration_id"],
            "primary_metric": PRIMARY_METRIC,
            "m1_pr_auc": b["m1_estimate"],
            "m2_pr_auc": b["m2_estimate"],
            "m2_minus_m1_pr_auc": b["m2_minus_m1_delta"],
            "ci_lower": b["ci_lower"],
            "ci_upper": b["ci_upper"],
            "observed_direction": _direction(
                b["m2_minus_m1_delta"], b["ci_lower"], b["ci_upper"]),
            "point_estimate_sign": (
                "positive" if (b["m2_minus_m1_delta"] or 0) > 0
                else "negative" if (b["m2_minus_m1_delta"] or 0) < 0
                else "zero"
            ),
        }
    directions = {v["observed_direction"] for v in per_family.values()}
    signs = {v["point_estimate_sign"] for v in per_family.values()}

    return {
        "decision_id": ACTION_ID,
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "stage": STAGE,
        "active_workstream": ACTIVE_WORKSTREAM,
        "scope": "development_only_paired_m2_vs_m1_incremental_evaluation",
        "evidence_class": "observed_development_evidence",
        "gate_status_consumed": frozen["gate_status"],
        "historical_d0_gate_status": frozen["historical_d0_gate_status"],
        "common_sample_rows": len(sample["common"]),
        "pooled_oof_rows": len(sample["pooled_validation_keys"]),
        "primary_predictive_model_fits": len(fit_log),
        "per_family_primary_metric": per_family,
        "families_agree_on_direction": len(directions) == 1,
        "families_agree_on_point_estimate_sign": len(signs) == 1,
        "new_pass_fail_threshold_created": False,
        "winner_selected": False,
        "retained_block_selected": False,
        "m2_automatically_retained": False,
        "m2_automatically_rejected": False,
        "superiority_claimed": False,
        "single_fabricated_score_reported": False,
        "design_changed_after_seeing_results": False,
        "causal_interpretation_made": False,
        "human_retained_block_decision_required": True,
        "human_decision_question": (
            "Given the observed paired development evidence, its uncertainty, "
            "the common-sample attrition and the D2 eligibility imbalance, "
            "should the M2 market block be retained for the confirmatory "
            "programme? This action deliberately does not answer it."
        ),
        "interpretation_inputs": {
            "common_sample_attrition_rows": attrition["attrition_rows"],
            "common_sample_attrition_fraction": attrition[
                "attrition_fraction"],
            "parent_event_rate": attrition["parent_development"]["event_rate"],
            "common_event_rate": attrition["common_sample"]["event_rate"],
            "pooled_oof_positive": attrition["common_pooled_oof"]["positive"],
            "d2_eligibility_flagged_comparisons": eligibility[
                "flagged_comparison_count"],
            "temporal_heterogeneity_reported": True,
            "bootstrap_uncertainty_reported": True,
            "cross_family_agreement_reported": True,
            "multiplicity_family_complete": multiplicity[
                "holm_family_complete"],
        },
        "limitations": [
            "The comparison is restricted to the 539-row three-variable M2 "
            "common sample; 127 parent development rows are absent and the "
            "absent rows differ from the retained rows on flagged "
            "predictor-side dimensions (see the post-lock eligibility audit).",
            "Only 28 positive events are available across the two pooled "
            "locked validation windows, so all interval estimates are wide "
            "and fold-level estimates are unstable.",
            "The confirmatory multiplicity family is incomplete; no "
            "family-level adjusted inference is available in this action.",
            "Development evidence only. Nothing here is a final-test result "
            "and nothing here selects a winner or a retained block.",
        ],
        "authorizes_next_action": False,
        "m3_started": False,
        "m4_started": False,
        "merge_authorized": False,
        "firewall": firewall,
    }


# --------------------------------------------------------------------------- #
# Execution contract + feature/configuration manifest
# --------------------------------------------------------------------------- #

def build_execution_contract(frozen: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "action_id": ACTION_ID,
        "stage": STAGE,
        "active_workstream": ACTIVE_WORKSTREAM,
        "package_location": OUT_DIR_REL,
        "action_id_renamed": False,
        "scope": "development_only",
        "final_test_access": False,
        "blocks": list(BLOCKS),
        "m2_is_nested_superset_of_m1": True,
        "equity_return_measurement_specification": D2_SPECIFICATION,
        "equity_return_calendar_convention": D2_CALENDAR_CONVENTION,
        "equity_return_source_column": EQUITY_RETURN_SOURCE_COLUMN,
        "equity_return_contract_field": EQUITY_RETURN_CONTRACT_FIELD,
        "historical_d0_equity_return_used_as_predictor": False,
        "forbidden_market_features": list(FORBIDDEN_MARKET_FEATURES),
        "model_families": list(MODEL_FAMILIES),
        "configurations_reused_from": SELECTED_CONFIGS_REL,
        "configuration_reselection_performed": False,
        "tuning_performed": False,
        "grid_search_performed": False,
        "feature_search_performed": False,
        "smote_used": False,
        "early_stopping_used": False,
        "final_oof_seeds": list(FINAL_OOF_SEEDS),
        "tuning_seeds_used": False,
        "expected_primary_predictive_fit_count": EXPECTED_PRIMARY_FIT_COUNT,
        "primary_metric": PRIMARY_METRIC,
        "secondary_metrics": list(SECONDARY_METRICS),
        "top_k_rule": (
            "per target year: K_y = ceil(0.10 * N_y); rank by predicted "
            "probability descending; deterministic tie-break ticker ascending"
        ),
        "k_optimized_after_seeing_results": False,
        "uncertainty": {
            "method": BOOTSTRAP_METHOD,
            "cluster": BOOTSTRAP_CLUSTER,
            "replicates": BOOTSTRAP_REPLICATES,
            "seed": BOOTSTRAP_SEED,
            "confidence_interval": BOOTSTRAP_CI,
            "minimum_valid_replicates": BOOTSTRAP_MIN_VALID_REPLICATES,
        },
        "preprocessing": {
            "estimated_inside_each_temporal_training_fold_only": True,
            "steps": [
                "deterministic_source_to_feature_transformation",
                "capture_original_pre_imputation_missingness_mask",
                "training_fold_1st_99th_percentile_clipping_bounds",
                "apply_training_derived_clipping_bounds",
                "training_fold_median_after_clipping",
                "median_imputation",
                "append_missingness_indicators_from_original_mask",
                "standardize_imputed_continuous_predictors_for_logistic_only",
            ],
            "missingness_indicators_standardized": False,
            "random_forest_standardized": False,
            "xgboost_standardized": False,
            "parameters_estimated_on_combined_train_and_validation": False,
            "final_test_influenced_preprocessing": False,
            "feature_screening_performed": False,
            "financial_expense_sign_preserved": True,
            "financial_expense_absolute_value_taken": False,
        },
        "frozen_inputs": frozen,
    }


def build_feature_configuration_manifest() -> dict[str, Any]:
    return {
        "m1_feature_order": list(M1_FEATURE_ORDER),
        "m1_feature_count": len(M1_FEATURE_ORDER),
        "m2_feature_order": list(M2_FEATURE_ORDER),
        "m2_feature_count": len(M2_FEATURE_ORDER),
        "m2_market_features": list(M2_MARKET_FEATURE_ORDER),
        "m2_is_nested_superset_of_m1": (
            M2_FEATURE_ORDER[:len(M1_FEATURE_ORDER)] == M1_FEATURE_ORDER
        ),
        "extra_market_features_added": [],
        "forbidden_market_features_absent": [
            f for f in FORBIDDEN_MARKET_FEATURES if f not in M2_FEATURE_ORDER
        ],
        "equity_return_window_implementation": D2_SPECIFICATION,
        "equity_return_window_source": (
            f"{D2_FEATURES_REL}:{EQUITY_RETURN_SOURCE_COLUMN}"
        ),
        "configurations": {
            fam: {
                "configuration_id": cfg["configuration_id"],
                "hyperparameters": cfg["hyperparameters"],
                "seed_policy": (
                    "deterministic_single_fit"
                    if fam in DETERMINISTIC_FAMILIES
                    else "mean_of_5_frozen_final_oof_seeds"
                ),
            }
            for fam, cfg in FROZEN_CONFIGURATIONS.items()
        },
    }


def build_fit_count_audit(fit_log: list[dict[str, Any]]) -> dict[str, Any]:
    by_family: dict[str, int] = {f: 0 for f in MODEL_FAMILIES}
    by_block: dict[str, int] = {b: 0 for b in BLOCKS}
    for entry in fit_log:
        by_family[entry["family"]] += 1
        by_block[entry["block"]] += 1
    return {
        "expected_primary_predictive_fit_count": EXPECTED_PRIMARY_FIT_COUNT,
        "observed_primary_predictive_fit_count": len(fit_log),
        "matches_expected": len(fit_log) == EXPECTED_PRIMARY_FIT_COUNT,
        "by_model_family": by_family,
        "by_block": by_block,
        "bootstrap_refits": 0,
        "bootstrap_increases_fit_count": False,
        "final_test_fits": 0,
        "full_development_refits": 0,
        "smote_fits": 0,
        "tuning_fits": 0,
        "fits": fit_log,
    }


# --------------------------------------------------------------------------- #
# QC
# --------------------------------------------------------------------------- #

def build_qc_report(
    repo_root: Path, auth, frozen, sample, attrition, eligibility,
    smd_rows, manifest, fit_audit, oof, metrics_rows, calibration,
    bootstrap, multiplicity, decision, firewall,
) -> dict[str, Any]:
    a: list[dict[str, str]] = []

    def add(name: str, ok: bool, detail: str = "") -> None:
        a.append({"name": name, "status": "PASS" if ok else "FAIL",
                  "detail": detail})

    # -- authorization ---------------------------------------------------- #
    add("authorization_utterance_verbatim",
        auth["human_source_utterance"] == AUTHORIZATION_TEXT_FA)
    add("authorization_sha256_recomputed",
        hashlib.sha256(
            auth["human_source_utterance"].encode("utf-8")).hexdigest()
        == AUTHORIZATION_TEXT_SHA256)
    add("authorization_date_exact",
        auth["authorization_date"] == AUTHORIZATION_DATE)
    add("authorization_is_one_action_only", auth["one_action_only"] is True)
    add("authorization_not_standing",
        auth["standing_authorization"] is False
        and auth["non_transitive"] is True)
    add("merge_not_authorized", auth["merge_authorized"] is False)
    add("final_test_not_authorized",
        auth["final_test_access_authorized"] is False
        and auth["final_test_evaluation_authorized"] is False)
    add("m3_m4_not_authorized",
        auth["m3_authorized"] is False and auth["m4_authorized"] is False)
    add("normalized_scope_never_replaces_original_text",
        auth["normalized_scope_never_replaces_original_text"] is True
        and auth["normalized_authorization_scope"] != AUTHORIZATION_TEXT_FA)

    # -- inputs ------------------------------------------------------------ #
    add("pr70_merge_commit_is_ancestor",
        frozen["pr70_merge_commit_is_ancestor_of_head"] is True,
        frozen["pr70_merge_commit"])
    add("d2_gate_status_is_pass", frozen["gate_status"] == GATE_STATUS_PASS)
    add("external_bundle_sha256_matches",
        frozen["external_bundle_sha256"] == EXTERNAL_BUNDLE_SHA256)
    add("frozen_source_hashes_recorded",
        set(frozen["frozen_sources_sha256"]) == set(FROZEN_SOURCES)
        and all(len(v) == 64 for v in frozen["frozen_sources_sha256"].values()))
    add("gate_decision_artifact_unchanged",
        frozen["gate_decision_modified"] is False
        and frozen["frozen_authority_sha256"][GATE_DECISION_REL]
        == sha256_file(repo_root / GATE_DECISION_REL))
    add("historical_d0_gate_remains_fail",
        frozen["historical_d0_gate_status"] == HISTORICAL_D0_GATE_STATUS)
    add("stage127_historical_artifacts_not_modified",
        frozen["stage127_historical_artifacts_modified"] is False)

    # -- sample and joins --------------------------------------------------- #
    ja = sample["join_audit"]
    add("parent_development_rows_666",
        ja["parent_rows"] == EXPECTED_PARENT_DEV_ROWS)
    add("common_rows_539", ja["common_rows"] == EXPECTED_COMMON_ROWS)
    add("common_composition_55_positive_484_negative",
        ja["common_positive"] == EXPECTED_COMMON_POSITIVE
        and ja["common_negative"] == EXPECTED_COMMON_NEGATIVE)
    add("common_fold_counts_exact",
        all(len(sample["role_keys"][r]) == n
            for r, n in EXPECTED_COMMON_FOLD_COUNTS.items()))
    add("common_validation_positives_18_and_10",
        all(sum(1 for k in sample["role_keys"][r]
                if sample["common"][k]["target"] == 1.0) == n
            for r, n in EXPECTED_COMMON_VALIDATION_POSITIVES.items()))
    add("pooled_oof_rows_366",
        ja["pooled_oof_rows"] == EXPECTED_POOLED_OOF_ROWS)
    add("pooled_oof_positives_28",
        ja["pooled_oof_positive"] == EXPECTED_POOLED_OOF_POSITIVE)
    add("no_duplicate_or_many_to_many_joins",
        ja["duplicate_join_keys"] == 0 and ja["many_to_many_joins"] == 0
        and ja["unmatched_parent_rows"] == 0)
    add("no_final_test_keys_in_join",
        ja["final_test_rows_in_join"] == 0
        and ja["final_test_rows_loaded"] == 0)

    # -- comparison validity ------------------------------------------------ #
    fam_rows = {f: [r for r in oof if r["model_family"] == f]
                for f in MODEL_FAMILIES}
    add("m1_and_m2_share_identical_row_identities",
        all(
            [(r["ticker"], r["fiscal_year_t"]) for r in fam_rows[f]]
            == [(r["ticker"], r["fiscal_year_t"]) for r in fam_rows[
                MODEL_FAMILIES[0]]]
            for f in MODEL_FAMILIES
        ),
        "each paired OOF row carries both block probabilities for one row")
    add("paired_rows_carry_both_block_probabilities",
        all(r["m1_probability"] is not None and r["m2_probability"] is not None
            for r in oof))
    add("m1_and_m2_temporal_roles_match",
        all(r["temporal_fold"] in EXPECTED_COMMON_VALIDATION_POSITIVES
            for r in oof))
    add("m1_comparator_refitted_on_common_sample_training_rows",
        all(e["train_rows"] == EXPECTED_COMMON_FOLD_COUNTS[
            m1.FOLD_SPEC[e["fold"]]["train_role"]]
            for e in fit_audit["fits"]))
    add("no_reuse_of_unpaired_original_m1_oof_predictions",
        fit_audit["by_block"]["M1"] == fit_audit["by_block"]["M2"]
        and fit_audit["by_block"]["M1"] == EXPECTED_PRIMARY_FIT_COUNT // 2)
    add("m1_feature_order_exact",
        manifest["m1_feature_order"] == list(m1.M1_PRIMARY_FEATURE_ORDER)
        and manifest["m1_feature_count"] == 9)
    add("m2_feature_order_exact_nested_twelve",
        manifest["m2_feature_count"] == 12
        and manifest["m2_is_nested_superset_of_m1"] is True
        and manifest["m2_feature_order"][9:] == list(M2_MARKET_FEATURE_ORDER))
    add("d2_is_the_active_equity_return_implementation",
        manifest["equity_return_window_implementation"] == D2_SPECIFICATION
        and EQUITY_RETURN_SOURCE_COLUMN in
        manifest["equity_return_window_source"])
    add("no_extra_market_feature",
        manifest["extra_market_features_added"] == []
        and set(manifest["forbidden_market_features_absent"])
        == set(FORBIDDEN_MARKET_FEATURES))

    # -- modeling ----------------------------------------------------------- #
    add("exactly_three_model_families",
        set(fit_audit["by_model_family"]) == set(MODEL_FAMILIES))
    add("frozen_configurations_exact",
        all(manifest["configurations"][f]["configuration_id"]
            == FROZEN_CONFIGURATIONS[f]["configuration_id"]
            for f in MODEL_FAMILIES))
    add("no_tuning_or_grid_search",
        fit_audit["tuning_fits"] == 0
        and firewall["grid_search_executions"] == 0
        and firewall["hyperparameter_tuning_executions"] == 0
        and firewall["feature_search_executions"] == 0)
    add("no_smote", fit_audit["smote_fits"] == 0
        and firewall["smote_executions"] == 0)
    add("no_early_stopping",
        FROZEN_CONFIGURATIONS["xgboost"]["hyperparameters"]["early_stopping"]
        is False)
    add("primary_predictive_fit_count_is_44",
        fit_audit["observed_primary_predictive_fit_count"]
        == EXPECTED_PRIMARY_FIT_COUNT)
    add("frozen_seed_list_exact",
        tuple(FINAL_OOF_SEEDS)
        == (20260719, 20260720, 20260721, 20260722, 20260723))
    add("scale_pos_weight_from_training_fold_only",
        all(e["scale_pos_weight"] is not None for e in fit_audit["fits"]
            if e["family"] == "xgboost"))
    add("no_final_test_model_call", fit_audit["final_test_fits"] == 0)

    # -- metrics / uncertainty ---------------------------------------------- #
    add("primary_metric_is_pr_auc", PRIMARY_METRIC == "pr_auc")
    add("secondary_metrics_exact",
        tuple(SECONDARY_METRICS)
        == ("roc_auc", "brier_score", "recall_at_10pct", "lift_at_10pct"))
    add("metrics_reported_for_m1_m2_and_delta",
        {r["block"] for r in metrics_rows} == {"M1", "M2", "M2_minus_M1"})
    add("bootstrap_contract_exact",
        bootstrap["replicates_attempted"] == BOOTSTRAP_REPLICATES
        and bootstrap["seed"] == BOOTSTRAP_SEED
        and bootstrap["cluster"] == BOOTSTRAP_CLUSTER
        and bootstrap["confidence_interval"] == BOOTSTRAP_CI)
    add("bootstrap_uses_same_resampled_rows_for_both_blocks",
        bootstrap["same_resampled_rows_for_both_blocks"] is True
        and bootstrap["models_refit_during_bootstrap"] is False)
    add("bootstrap_valid_replicate_rule_met",
        all(v["minimum_valid_replicates_met"] is True
            for v in bootstrap["by_family"].values()),
        json.dumps({f: v["valid_replicates"]
                    for f, v in bootstrap["by_family"].items()}))
    add("no_silent_one_member_holm_family",
        multiplicity["holm_family_complete"] is False
        and multiplicity["holm_final_adjustment_deferred"] is True
        and multiplicity["family_redefined_as_one_hypothesis"] is False
        and len(multiplicity["confirmatory_family"]) == 3)

    # -- calibration --------------------------------------------------------- #
    add("isotonic_calibration_not_executed",
        calibration["isotonic_calibration_executed"] is False
        and calibration["isotonic_calibration_allowed"] is False)
    add("raw_probabilities_are_the_primary_surface",
        calibration["primary_probabilities_are_raw"] is True
        and calibration["recalibrated_probabilities_used_as_primary_surface"]
        is False)
    add("calibration_reported_for_every_family_and_block",
        all(set(v) == {"M1", "M2"} for v in calibration["by_family"].values())
        and set(calibration["by_family"]) == set(MODEL_FAMILIES))

    # -- eligibility audit ---------------------------------------------------- #
    add("post_lock_eligibility_audit_executed",
        eligibility["executed_before_interpreting_predictive_results"] is True)
    add("all_required_audit_dimensions_attempted",
        eligibility["required_dimensions_attempted"] is True
        and eligibility["dimension_count"] >= 6)
    add("smd_threshold_is_descriptive_only",
        eligibility["smd_is_descriptive_flag_only"] is True
        and eligibility["smd_is_not_an_exclusion_threshold"] is True
        and eligibility["smd_flag_threshold"] == SMD_FLAG_THRESHOLD)
    add("no_row_removed_by_smd",
        eligibility["rows_removed_due_to_smd"] == 0
        and eligibility["weighting_applied"] is False
        and eligibility["matching_applied"] is False
        and eligibility["sample_repair_applied"] is False)
    add("distress_rate_comparison_is_descriptive_only",
        eligibility["post_lock_outcome_side_comparison"]["is_descriptive_only"]
        is True
        and eligibility["post_lock_outcome_side_comparison"][
            "separated_from_predictor_side_audit"] is True)
    add("audit_cannot_alter_d2_or_the_model",
        eligibility["m2_feature_changed_by_audit"] is False
        and eligibility["boundary_rule_changed_by_audit"] is False
        and eligibility["gate_result_revised_by_audit"] is False
        and eligibility["model_design_changed_by_audit"] is False)
    add("zero_trade_day_ratio_used_only_in_the_audit",
        any(r["variable"] == "zero_trade_day_ratio_W" for r in smd_rows)
        and "zero_trade_day_ratio_W" not in M2_FEATURE_ORDER)

    # -- attrition ------------------------------------------------------------ #
    add("attrition_reported_not_concealed",
        attrition["attrition_is_reported_not_concealed"] is True
        and attrition["attrition_rows"]
        == EXPECTED_PARENT_DEV_ROWS - EXPECTED_COMMON_ROWS)

    # -- firewall -------------------------------------------------------------- #
    add("final_test_firewall_intact",
        firewall["final_test_predictor_values_read"] == 0
        and firewall["final_test_target_values_read"] == 0
        and firewall["final_test_predictions"] == 0
        and firewall["final_test_model_fits"] == 0
        and firewall["final_test_unlocked"] is False
        and firewall["final_test_evaluation_performed"] is False)
    add("no_full_development_refit",
        firewall["full_development_refits"] == 0)
    add("no_m3_or_m4_execution",
        firewall["m3_executions"] == 0 and firewall["m4_executions"] == 0)
    add("no_shap_execution", firewall["shap_executions"] == 0)
    add("final_test_rows_structurally_encountered_but_never_parsed",
        firewall["final_test_rows_seen_and_skipped_without_parsing"]
        == FINAL_TEST_ROWS_STRUCTURALLY_ENCOUNTERED
        and firewall["final_test_predictor_values_read"] == 0
        and firewall["final_test_target_values_read"] == 0,
        "the loader structurally encounters final-test row records and "
        "rejects them before value parsing; values read remain 0")

    # -- immutable original-execution provenance ---------------------------- #
    oe = ORIGINAL_AUTHORIZED_SCIENTIFIC_EXECUTION
    add("original_authorized_execution_provenance_is_locked",
        oe["action_id"] == ACTION_ID
        and oe["authorization_sha256"] == AUTHORIZATION_TEXT_SHA256
        and oe["source_base_commit"] == EXPECTED_BASE_MERGE_COMMIT
        and oe["canonical_scientific_artifact_commit"]
        == "96a1d6b19b91756b6a0257344c50754fb6d38c7d"
        and oe["python_version"] == "3.14.0"
        and oe["platform"] == "macOS-26.5.2-arm64-arm-64bit-Mach-O"
        and oe["immutable_provenance"] is True
        and oe["derived_dynamically_from_current_interpreter"] is False
        and oe["overwritten_by_verification_or_maintenance"] is False,
        "the original authorized execution environment is a locked constant")
    add("canonical_execution_and_decision_counts_remain_one",
        oe["canonical_authorized_execution_count"] == 1
        and oe["scientific_decision_count"] == 1
        and EXECUTION_COUNT_SEMANTICS[
            "canonical_authorized_scientific_executions"] == 1
        and EXECUTION_COUNT_SEMANTICS["scientific_decisions"] == 1)
    add("canonical_primary_fit_count_is_locked_at_44",
        oe["canonical_primary_predictive_fit_count"]
        == EXPECTED_PRIMARY_FIT_COUNT
        and EXECUTION_COUNT_SEMANTICS[
            "canonical_primary_predictive_fits_in_that_execution"] == 44)
    add("verification_recomputation_is_not_a_scientific_execution",
        EXECUTION_COUNT_SEMANTICS[
            "deterministic_verification_recomputation_is_not_a_new_execution"]
        is True
        and EXECUTION_COUNT_SEMANTICS[
            "verification_recomputation_changes_canonical_counts"] is False
        and latest_non_scientific_verification_environment()[
            "scientific_execution"] is False
        and latest_non_scientific_verification_environment()[
            "is_original_authorized_execution_environment"] is False)

    # -- interpretation --------------------------------------------------------- #
    add("no_winner_or_retained_block_selected",
        decision["winner_selected"] is False
        and decision["retained_block_selected"] is False
        and decision["m2_automatically_retained"] is False
        and decision["m2_automatically_rejected"] is False)
    add("no_new_pass_fail_threshold_created",
        decision["new_pass_fail_threshold_created"] is False)
    add("no_superiority_or_causal_claim",
        decision["superiority_claimed"] is False
        and decision["causal_interpretation_made"] is False)
    add("human_retained_block_decision_recorded_as_required",
        decision["human_retained_block_decision_required"] is True)

    failed = sum(1 for x in a if x["status"] != "PASS")
    return {
        "contract_id": CONTRACT_ID,
        "decision_id": ACTION_ID,
        "stage": STAGE,
        "assertion_count": len(a),
        "failed_count": failed,
        "all_pass": failed == 0,
        "all_pass_semantics": (
            "all_pass means every REQUIRED fail-closed assertion of this "
            "action passed. It is NOT a scientific verdict on M2: the "
            "observed paired evidence is reported separately and selects no "
            "winner."
        ),
        "assertions": a,
    }


# --------------------------------------------------------------------------- #
# README
# --------------------------------------------------------------------------- #

def build_readme(
    attrition, eligibility, metrics_rows, bootstrap, multiplicity, decision,
) -> str:
    lines = [
        "# Stage127 — paired M2 versus M1 incremental evaluation "
        "(frozen Gregorian D2 common sample)",
        "",
        f"**Action:** `{ACTION_ID}` — one authorized execution, consumed.",
        "",
        "**Development-only.** No final-test predictor or target value was "
        "parsed, inspected, stored in an action artifact, used for "
        "preprocessing, used for fitting, used for prediction or used for "
        "evaluation. The frozen streaming loader structurally encountered "
        f"{FINAL_TEST_ROWS_STRUCTURALLY_ENCOUNTERED} final-test row records "
        "and rejected them before value parsing — that is a structural skip, "
        "not a read. No configuration was retuned, no feature was searched, "
        "no winner was selected and M3/M4 were not started.",
        "",
        "## What was compared, and on which rows",
        "",
        "Both blocks were REFITTED on exactly the same common-sample training "
        "rows and evaluated on exactly the same common-sample validation "
        "rows. The original 666-row M1 results are NOT compared against these "
        "539-row M2 results; that comparison would confound sample "
        "restriction with model change and is deliberately not made.",
        "",
        f"- Parent M1 development surface: "
        f"{attrition['parent_development']['rows']} rows "
        f"({attrition['parent_development']['positive']} positive, "
        f"{attrition['parent_development']['negative']} negative, "
        f"{attrition['parent_development']['companies']} companies)",
        f"- M2 three-variable common sample: "
        f"{attrition['common_sample']['rows']} rows "
        f"({attrition['common_sample']['positive']} positive, "
        f"{attrition['common_sample']['negative']} negative, "
        f"{attrition['common_sample']['companies']} companies)",
        f"- Dropped by D2 ineligibility: "
        f"{attrition['dropped_by_d2_ineligibility']['rows']} rows "
        f"({attrition['dropped_by_d2_ineligibility']['positive']} positive, "
        f"{attrition['dropped_by_d2_ineligibility']['negative']} negative), "
        f"involving {attrition['dropped_by_d2_ineligibility']['companies']} "
        "distinct companies",
        f"- Attrition: {attrition['attrition_rows']} rows "
        f"({attrition['attrition_fraction']}) — reported, never interpreted "
        "as model improvement",
        f"- Pooled locked-validation OOF rows: "
        f"{attrition['common_pooled_oof']['rows']} "
        f"({attrition['common_pooled_oof']['positive']} positive)",
        "",
        "## Blocks",
        "",
        f"- **M1** ({len(M1_FEATURE_ORDER)} features): "
        + ", ".join(f"`{f}`" for f in M1_FEATURE_ORDER),
        f"- **M2** ({len(M2_FEATURE_ORDER)} features): the nested M1 set plus "
        + ", ".join(f"`{f}`" for f in M2_MARKET_FEATURE_ORDER),
        f"- `equity_return_window` is measured ONLY by the frozen "
        f"`{D2_SPECIFICATION}` ({D2_CALENDAR_CONVENTION}) construct, taken "
        f"from `{EQUITY_RETURN_SOURCE_COLUMN}`. The historical D0 equity "
        "return is NOT an active predictor. `zero_trade_day_ratio_W` appears "
        "only in the eligibility audit.",
        "",
        "## Post-lock D2 eligibility audit (descriptive only)",
        "",
        f"- Eligible rows: {eligibility['eligible_rows']} — ineligible: "
        f"{eligibility['ineligible_rows']}",
        f"- Comparisons: {eligibility['comparison_count']} across "
        f"{eligibility['dimension_count']} dimensions; "
        f"{eligibility['flagged_comparison_count']} carry |SMD| ≥ "
        f"{SMD_FLAG_THRESHOLD}",
        "- An SMD flag is descriptive. No row was removed, no weighting or "
        "matching was introduced, D2 was not changed, the Gate was not "
        "revised and no model design was altered. Flags limit "
        "INTERPRETATION and are recorded in the decision limitations.",
        "",
        "## Observed paired results (primary metric: PR-AUC)",
        "",
        "| family | M1 | M2 | M2−M1 | 95% CI | direction |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for family in MODEL_FAMILIES:
        e = decision["per_family_primary_metric"][family]
        ci = (f"[{e['ci_lower']}, {e['ci_upper']}]"
              if e["ci_lower"] is not None else "not estimable")
        lines.append(
            f"| `{family}` | {e['m1_pr_auc']} | {e['m2_pr_auc']} | "
            f"{e['m2_minus_m1_pr_auc']} | {ci} | {e['observed_direction']} |"
        )
    lines += [
        "",
        "Secondary metrics (ROC-AUC, Brier, Recall@10%, Lift@10%), fold-level "
        "results and the full paired bootstrap are in "
        f"`{F_METRICS}` and `{F_BOOTSTRAP}`.",
        "",
        "## Multiplicity",
        "",
        f"- Confirmatory family: "
        + ", ".join(f"`{m}`" for m in CONFIRMATORY_FAMILY),
        f"- Available here: `{CONFIRMATORY_FAMILY_MEMBER}` only",
        f"- `holm_family_complete = {multiplicity['holm_family_complete']}`, "
        f"`holm_final_adjustment_deferred = "
        f"{multiplicity['holm_final_adjustment_deferred']}`",
        "- The three-member family is NOT redefined as a single hypothesis, "
        "and no one-comparison Holm adjustment is presented as a completed "
        "family adjustment.",
        "",
        "## Interpretation",
        "",
        "This action reports OBSERVED development evidence. It creates no new "
        "PASS/FAIL threshold for M2 predictive value, selects no winner, "
        "retains and rejects nothing, and makes no causal or superiority "
        "claim.",
        "",
    ]
    for lim in decision["limitations"]:
        lines.append(f"- {lim}")
    lines += [
        "",
        "**A human retained-block decision is required** and is explicitly "
        "NOT made here.",
        "",
        "## Counters",
        "",
        f"canonical primary predictive model fits = "
        f"{decision['primary_predictive_model_fits']} (the canonical "
        "SCIENTIFIC fit count of the one authorized execution — `--check` and "
        "the test suite deterministically recompute the same models to verify "
        "the committed artifacts, which is verification, not a new scientific "
        "execution); canonical authorized scientific executions = 1; "
        "scientific decisions = 1; final-test predictor values "
        "parsed/inspected = 0; final-test target values parsed/inspected = 0; "
        "final-test fits = 0; final-test predictions = 0; final-test "
        "evaluation = 0; final-test keys in scientific artifacts = 0; "
        "final-test row records structurally encountered and rejected before "
        f"value parsing = {FINAL_TEST_ROWS_STRUCTURALLY_ENCOUNTERED}; "
        "full-development refits = 0; M3 executions = 0; M4 executions = 0; "
        "winners selected = 0.",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Build / run
# --------------------------------------------------------------------------- #

def build_all(repo_root: Path) -> tuple[dict[str, str], dict[str, Any]]:
    auth = build_authorization_record()
    assert_authorization(auth)
    frozen = verify_frozen_inputs(repo_root)
    if not frozen["pr70_merge_commit_is_ancestor_of_head"]:
        raise EvaluationFail(
            f"PR #70 merge commit {EXPECTED_BASE_MERGE_COMMIT} is not an "
            "ancestor of HEAD (fail-closed)"
        )

    sample = build_common_sample(repo_root)
    attrition = build_attrition_audit(sample)
    eligibility, smd_rows = build_eligibility_audit(sample)

    evaluation = run_paired_evaluation(sample)
    oof = oof_rows(evaluation)
    metrics_rows = build_metrics_rows(oof)
    calibration = build_calibration_report(oof)
    bootstrap = run_paired_bootstrap(oof)
    multiplicity = build_multiplicity_record()
    fit_audit = build_fit_count_audit(evaluation["fit_log"])
    firewall = build_firewall_audit(sample)
    manifest = build_feature_configuration_manifest()
    contract = build_execution_contract(frozen)
    decision = build_decision(
        sample, attrition, eligibility, metrics_rows, bootstrap, multiplicity,
        evaluation["fit_log"], firewall, frozen,
    )
    qc = build_qc_report(
        repo_root, auth, frozen, sample, attrition, eligibility, smd_rows,
        manifest, fit_audit, oof, metrics_rows, calibration, bootstrap,
        multiplicity, decision, firewall,
    )
    readme = build_readme(
        attrition, eligibility, metrics_rows, bootstrap, multiplicity, decision)

    files = {
        F_AUTH: json_dumps(auth),
        F_CONTRACT: json_dumps(contract),
        F_JOIN_AUDIT: json_dumps(sample["join_audit"]),
        F_ATTRITION: json_dumps(attrition),
        F_ELIGIBILITY: json_dumps(eligibility),
        F_ELIGIBILITY_CSV: csv_text(SMD_COLUMNS, smd_rows),
        F_MANIFEST: json_dumps(manifest),
        F_FIT_AUDIT: json_dumps(fit_audit),
        F_OOF: csv_text(OOF_COLUMNS, oof),
        F_METRICS: csv_text(METRICS_COLUMNS, metrics_rows),
        F_CALIBRATION: json_dumps(calibration),
        F_BOOTSTRAP: json_dumps(bootstrap),
        F_MULTIPLICITY: json_dumps(multiplicity),
        F_DECISION: json_dumps(decision),
        F_FIREWALL: json_dumps(firewall),
        F_QC: json_dumps(qc),
        F_README: readme,
    }
    if set(files) != set(TRACKED_CONTENT_FILES):
        raise EvaluationFail("tracked content file set drifted")
    if qc["failed_count"]:
        failed = [x["name"] for x in qc["assertions"] if x["status"] != "PASS"]
        raise EvaluationFail(f"QC failed: {failed}")
    return files, {
        "auth": auth, "frozen": frozen, "sample": sample, "qc": qc,
        "decision": decision, "bootstrap": bootstrap, "fit_audit": fit_audit,
    }


def build_metadata(
    repo_root: Path, files: dict[str, str], extras: dict[str, Any],
) -> dict[str, Any]:
    return {
        "contract_id": CONTRACT_ID,
        "contract_version": CONTRACT_VERSION,
        "decision_id": ACTION_ID,
        "stage": STAGE,
        "active_workstream": ACTIVE_WORKSTREAM,
        "package_location": OUT_DIR_REL,
        "human_source_utterance_sha256": AUTHORIZATION_TEXT_SHA256,
        "authorization_date": AUTHORIZATION_DATE,
        "external_bundle_sha256": EXTERNAL_BUNDLE_SHA256,
        "gate_status_consumed": GATE_STATUS_PASS,
        "historical_d0_gate_status": HISTORICAL_D0_GATE_STATUS,
        "primary_predictive_model_fits": extras["fit_audit"][
            "observed_primary_predictive_fit_count"],
        "package_artifacts_sha256": {
            f"{OUT_DIR_REL}/{name}": sha256_text(text)
            for name, text in sorted(files.items())
        },
        "frozen_authority_sha256": extras["frozen"]["frozen_authority_sha256"],
        "frozen_sources_sha256": extras["frozen"]["frozen_sources_sha256"],
        "composed_module_sha256": {
            rel: sha256_file(repo_root / rel)
            for rel in (SRC_REL, RUN_REL,
                        "project/src/stage126_m1_primary_development_tuning.py")
        },
        "stage127_historical_artifacts_modified": False,
        "source_repository": "abtinasg/papermali",
        # Immutable provenance of the ONE authorized scientific execution.
        # Locked constants — never sampled from the interpreter, package set
        # or `origin/main` of a later --check, maintenance regeneration or
        # post-merge run.
        "original_authorized_scientific_execution": dict(
            ORIGINAL_AUTHORIZED_SCIENTIFIC_EXECUTION),
        # Separate and explicitly NON-scientific: whichever verification or
        # maintenance run last wrote this file.
        "latest_non_scientific_verification_environment":
            latest_non_scientific_verification_environment(),
        "execution_count_semantics": EXECUTION_COUNT_SEMANTICS,
    }


def handoff_markers(extras: dict[str, Any]) -> dict[str, Any]:
    """State markers for the Handoff generator. A pointer is not authority."""
    return {
        "stage127_m2_incremental_evaluation_executed": True,
        "stage127_m2_incremental_evaluation_completed": True,
        "stage127_m2_incremental_evaluation_authorization_consumed": True,
        # The one-action authorization was CONSUMED. A consumed
        # authorization is False; it never erases the historical FACT that
        # the authorized M2 modeling was executed.
        "m2_incremental_evaluation_authorized": False,
        "m2_started": True,
        "m2_modeling_started": True,
        "m2_block_admitted_for_authorized_incremental_evaluation": True,
        "m2_block_retained": False,
        "m2_retained_block_decision_required": True,
        "stage127_m2_incremental_evaluation_primary_model_fits": extras[
            "fit_audit"]["observed_primary_predictive_fit_count"],
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_evaluation_performed": False,
        "m3_started": False,
        "m3_authorized": False,
        "m4_started": False,
        "m4_authorized": False,
    }


def run(*, project_dir: Path, build: bool = False, check: bool = False) -> dict:
    if build == check:
        raise EvaluationFail("exactly one of build or check is required")
    repo_root = repo_root_from(project_dir)
    out_dir = repo_root / OUT_DIR_REL
    files, extras = build_all(repo_root)

    if check:
        drift = [
            name for name, text in files.items()
            if not (out_dir / name).is_file()
            or (out_dir / name).read_text(encoding="utf-8") != text
        ]
        if drift:
            raise EvaluationFail(f"check drift: {drift}")
        return {"mode": "check", "drift": [], **extras}

    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (out_dir / name).write_text(text, encoding="utf-8")
    (out_dir / F_METADATA).write_text(
        json_dumps(build_metadata(repo_root, files, extras)), encoding="utf-8")
    return {"mode": "build", "written": sorted(files), **extras}
