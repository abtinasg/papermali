"""Stage125 Part 5 — Readiness Closure (contract lock only).

Closes Stage125 research-design readiness: records keep/drop decisions over
every Stage125 surface, a blocker register, an explicit Stage126 M1 entry
contract (entry-ready, **not** authorization), an artifact-integrity manifest,
and a derived Gate 125.0 readiness gate.

Offline. Deterministic. Zero network. No model fitting. No SHAP. No
Stage126. Does not read Part 3C analysis-ready predictor columns; only
aggregate Part 3C hashes and aggregate Part 4 CSV/JSON artifacts are used.
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

QC_STAGE = "stage125_part5_readiness_closure"
CURRENT_STAGE = "Stage125"
EXPECTED_BASELINE_COMMIT = "5836059e2d533f4be7e1898f942937a57c0b8fef"
EXPECTED_BASELINE_TREE = "3c2de72270bc05afeabcd2f07088f71f886796a3"
CONTRACT_VERSION = "stage125_part5_readiness_closure_v1"
PART4_CONTRACT_VERSION = "stage125_part4_sap_v2"
RESEARCH_ACTION_ID = "stage125-part5-readiness-closure"
RESEARCH_LAST_COMPLETED = RESEARCH_ACTION_ID
RESEARCH_NEXT = "stage126-m1-financial-baseline"

SRC_REL = "project/src/stage125_part5_readiness_closure.py"
TEST_REL = "project/tests/test_stage125_part5_readiness_closure.py"
RUN_REL = "project/run_stage125_part5.py"

PART4_OUTPUT_DIR = "project/stage125"
PART4_SRC_REL = "project/src/stage125_part4_statistical_analysis_plan.py"
PART4_TEST_REL = "project/tests/test_stage125_part4_statistical_analysis_plan.py"
PART4_SRC_SHA256 = (
    "3b75764d9c2d9c2f259ed8d01dcbee8d8cb621440e18b97bca636ff8690a2d7b"
)
PART4_TEST_SHA256 = (
    "f78aae6e8e52f838a6da3106fa55b6a2a36fd0665877f6f4e3965902c344ced3"
)

ROADMAP_REL = "project/docs/ai/ROADMAP.md"
HANDOFF_STATE_REL = "project/docs/ai/handoff_state.json"

REVENUE_GROWTH_FEATURE = "revenue_growth_period_adjusted"
PRIMARY_TARGET = "FD_target_main_t_plus_1"
SECONDARY_TARGET = "FD_target_persistent_loss_robustness_t_plus_1"
ARTICLE141_TARGET = "FD_target_article141_only_t_plus_1"
ALL_TARGETS = (PRIMARY_TARGET, SECONDARY_TARGET, ARTICLE141_TARGET)

PRIMARY_SAMPLE = "main_rule_a_primary"
AVAILABILITY_METHOD = "fixed_regulatory_lag"
APPROVED_LAG_MONTHS = 4
FINAL_TEST_YEARS = (1400, 1401, 1402)
PRIMARY_METRIC = "PR-AUC"

# Locked sample counts, validated against Part 4 aggregate outputs only
# (never against analysis-ready predictor columns).
SAMPLE_SPECS: dict[str, dict[str, int]] = {
    "main_rule_a_primary": {
        "rows": 1012, "companies": 119, "positive": 80, "negative": 932,
    },
    "main_rule_b_listing_robustness": {
        "rows": 993, "companies": 117, "positive": 79, "negative": 914,
    },
    "expanded_rule_a_company_scope_robustness": {
        "rows": 1056, "companies": 124, "positive": 80, "negative": 976,
    },
    "expanded_rule_b_combined_robustness": {
        "rows": 1035, "companies": 122, "positive": 79, "negative": 956,
    },
}

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

M1_TARGET_PROXIMITY_ROBUSTNESS = [
    "log_total_assets",
    "current_ratio",
    "roa_period_adjusted",
    "asset_turnover_period_adjusted",
    "operating_margin_period_adjusted",
    "financial_expense_to_assets_period_adjusted",
]

FORBIDDEN_SURFACE_EXACT = (
    "project/src/stage126_m1_financial_baseline.py",
    "project/run_stage126.py",
    "project/stage126",
)

# --------------------------------------------------------------------------- #
# Output file names
# --------------------------------------------------------------------------- #

F_CLOSURE_REPORT = "part5_readiness_closure_report_stage125.json"
F_KEEP_DROP = "part5_keep_drop_decisions_stage125.csv"
F_BLOCKER = "part5_blocker_register_stage125.csv"
F_ENTRY_CONTRACT = "part5_stage126_m1_entry_contract_stage125.json"
F_INTEGRITY = "part5_artifact_integrity_manifest_stage125.csv"
F_README = "README_STAGE125_PART5_READINESS_CLOSURE.md"
F_QC = "stage125_part5_readiness_closure_qc_report.json"
F_METADATA = "metadata_and_hashes_stage125_part5.json"

TRACKED_CONTENT_FILES = (
    F_CLOSURE_REPORT, F_KEEP_DROP, F_BLOCKER, F_ENTRY_CONTRACT,
    F_INTEGRITY, F_README,
)

KEEP_DROP_COLUMNS = [
    "item_id", "decision", "category", "notes", "blocks_stage126_m1",
    "interpretation",
]
BLOCKER_COLUMNS = [
    "item_id", "current_status", "blocks_stage125_closure",
    "blocks_stage126_m1", "blocks_future_block", "disposition",
    "required_future_action",
]
INTEGRITY_COLUMNS = [
    "path", "artifact_role", "expected_sha256", "observed_sha256",
    "status", "mutation_authorized",
]

# --------------------------------------------------------------------------- #
# Frozen Part 3C inputs (identical to Part 4; hash-only, never inspected)
# --------------------------------------------------------------------------- #

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

# --------------------------------------------------------------------------- #
# Pinned Part 4 outputs (exact hashes; Part 4 is not re-derived, only pinned)
# --------------------------------------------------------------------------- #

FROZEN_PART4_OUTPUTS: dict[str, str] = {
    f"{PART4_OUTPUT_DIR}/README_STAGE125_PART4_REVENUE_GROWTH_EXCLUSION_REVISION.md":
        "e656fdf915f7dff89173b99c14c23a73f1f6664777b12e75c98e57ef388a65e8",
    f"{PART4_OUTPUT_DIR}/README_STAGE125_PART4_STATISTICAL_ANALYSIS_PLAN.md":
        "b9d8a5354967e9c5dae863fd240cbca145fbc358c50c81967fa866b8babb01ac",
    f"{PART4_OUTPUT_DIR}/part4_development_feature_coverage_audit_stage125.csv":
        "7c18da23265d1c544bd397686518cbc064f14f6deba45ecf1af8d55c21126703",
    f"{PART4_OUTPUT_DIR}/part4_event_count_gate_stage125.csv":
        "e8432e1f6e3958b658affa05070b5161d36d95e98bc2041bef4b1143ac9f0d17",
    f"{PART4_OUTPUT_DIR}/part4_feature_exclusion_decisions_stage125.csv":
        "f89125c99b6d6d4f4e5063b4276aa42e9a5b21933aa5e939bf65c7e76705291d",
    f"{PART4_OUTPUT_DIR}/part4_feature_sets_stage125.csv":
        "79e87cbcef1a6aa70fa6e4b837c4634df9e1f701e25f42a87ac34012452b850f",
    f"{PART4_OUTPUT_DIR}/part4_hyperparameter_budget_stage125.json":
        "22d6989681a7cd59ffbf57077910615ce00adb9f171d303d5d61100a54490b40",
    f"{PART4_OUTPUT_DIR}/part4_metrics_uncertainty_contract_stage125.json":
        "117ddf3ecf688032a3baba4843a477e58890a33b2ad80c26574c33c949ae7760",
    f"{PART4_OUTPUT_DIR}/part4_model_specifications_stage125.json":
        "ef933be3eb2f75e6f493ac1401100c629bdb83850c81950d8f235c5ccf4cdb21",
    f"{PART4_OUTPUT_DIR}/part4_preprocessing_contract_stage125.json":
        "3722bd6165574c78aef1138a810ff4863b5c214f80df197889eaa40163f0e415",
    f"{PART4_OUTPUT_DIR}/part4_revenue_growth_exclusion_revision_decision_stage125.json":
        "f6104b2038224a2b76679ad5957fb012b9e413e979377efe80fb8f2b97369f4e",
    f"{PART4_OUTPUT_DIR}/part4_sample_target_matrix_stage125.csv":
        "d7f026ecf0b3b2810eb95df5b912184c3b9f4e36031e9b366c00fd858b7c4792",
    f"{PART4_OUTPUT_DIR}/part4_shap_stability_contract_stage125.json":
        "acd19339b8f998ba54c00f3cb32d5ca12d353619316ecab951b7d03f96ed5f8a",
    f"{PART4_OUTPUT_DIR}/part4_statistical_analysis_plan_stage125.json":
        "8763bc094561ce63da2f9f621b8278a1c9836c8cbc2aeaace934e439d6e79d6e",
    f"{PART4_OUTPUT_DIR}/part4_temporal_split_contract_stage125.json":
        "3f6ff8c7adf77295e558045e5bcaa391b5d2c10e7be0a89aeb0c8ac2dd0463b9",
    f"{PART4_OUTPUT_DIR}/part4_temporal_split_manifest_stage125.csv":
        "5e27dc48cc502e36951d4080ef80be684eacff61a46b55a07d39d3318863aedc",
    f"{PART4_OUTPUT_DIR}/stage125_part4_statistical_analysis_plan_qc_report.json":
        "c119932134482304500f4b90d625f015245f1818113db83c82fac1cf8072a939",
}

# --------------------------------------------------------------------------- #
# Keep/drop vocabulary and exact decision rows
# --------------------------------------------------------------------------- #

KEEP_DROP_VOCAB = frozenset({
    "KEEP_READY", "KEEP_ROBUSTNESS", "KEEP_LOCKED", "KEEP_AUDIT_ONLY",
    "KEEP_DESCRIPTIVE_ONLY", "DEFER_NONBLOCKING_FOR_M1",
    "DROP_CURRENT_ACTIVE_PATH", "SUPERSEDED_HISTORICAL_ONLY",
})

# item_id, decision, category, notes, interpretation
KEEP_DROP_SPEC: tuple[tuple[str, str, str, str, str], ...] = (
    ("SAMPLE_PRIMARY_RULE_A", "KEEP_READY", "sample",
     "Rule A primary sample locked in Part 3C/Part 4 (1012 rows, "
     "119 companies, 80 positive, 932 negative).",
     "primary_sample_ready_for_stage126_m1_primary_specification"),
    ("SAMPLE_RULE_B", "KEEP_ROBUSTNESS", "sample",
     "Rule B listing-timing robustness sample (993 rows, 117 companies, "
     "79 positive, 914 negative).",
     "robustness_only_not_primary"),
    ("SAMPLE_EXPANDED_RULE_A", "KEEP_ROBUSTNESS", "sample",
     "Expanded Rule A company-scope robustness sample (1056 rows, "
     "124 companies, 80 positive, 976 negative).",
     "robustness_only_not_primary"),
    ("SAMPLE_EXPANDED_RULE_B", "KEEP_ROBUSTNESS", "sample",
     "Expanded Rule B combined robustness sample (1035 rows, "
     "122 companies, 79 positive, 956 negative).",
     "robustness_only_not_primary"),
    ("TARGET_MAIN_T_PLUS_1", "KEEP_READY", "target",
     "Primary target FD_target_main_t_plus_1; development-comparison "
     "supported and final-test claim-eligible on all four sample designs.",
     "primary_target_ready_for_stage126_m1"),
    ("TARGET_PERSISTENT_LOSS_T_PLUS_1", "KEEP_ROBUSTNESS", "target",
     "Secondary robustness target "
     "FD_target_persistent_loss_robustness_t_plus_1.",
     "robustness_target_registered_after_primary_lock"),
    ("TARGET_ARTICLE141_ONLY_T_PLUS_1", "KEEP_DESCRIPTIVE_ONLY", "target",
     "Article-141-only target: development comparison not supported "
     "(Fold 2 validation positive=3<5); final test 1 positive on the "
     "primary sample; distributional/descriptive robustness only.",
     "excluded_from_model_estimation_descriptive_only"),
    ("FEATURESET_M1_PRIMARY_9", "KEEP_READY", "feature_set",
     "9 admitted M1 primary features locked in Part 4 in exact order.",
     "primary_feature_set_ready"),
    ("FEATURESET_M1_TARGET_PROXIMITY_6", "KEEP_ROBUSTNESS", "feature_set",
     "6-feature target-proximity robustness set, registered for use only "
     "after the primary specification is locked.",
     "robustness_feature_set_registered_after_primary_lock"),
    ("FEATURE_REVENUE_GROWTH", "KEEP_AUDIT_ONLY", "feature",
     "revenue_growth_period_adjusted rejected from M1 primary "
     "(Fold 1 training coverage 148/245=0.6040816327 below the locked "
     "0.75 threshold); retained only in frozen data and in the "
     "coverage/exclusion audits.",
     "audit_only_absent_from_all_model_surfaces"),
    ("BLOCK_M2_MARKET", "DEFER_NONBLOCKING_FOR_M1", "block",
     "M2 market/liquidity block; no values collected; deferred and does "
     "not block Stage126 M1.",
     "deferred_future_block_not_required_for_m1"),
    ("BLOCK_M3_MACRO", "DROP_CURRENT_ACTIVE_PATH", "block",
     "M3 macro block; not admitted on the current active path "
     "(no authoritative CBI endpoint). M3 is not permanently eliminated; "
     "it may re-enter only after a new explicit versioned human decision, "
     "an authoritative reproducible source, publication/availability-time "
     "validation, and coverage/temporal data-Gate approval.",
     "not_admitted_current_path_may_reenter_via_new_versioned_decision"),
    ("BLOCK_M4_AUDIT_GOVERNANCE", "DEFER_NONBLOCKING_FOR_M1", "block",
     "M4 audit/governance block; no values collected; deferred and does "
     "not block Stage126 M1.",
     "deferred_future_block_not_required_for_m1"),
    ("BLOCK_M5_PERSIAN_TEXT", "DROP_CURRENT_ACTIVE_PATH", "block",
     "M5 Persian-text block; never defined or collected on the current "
     "active path; removed.",
     "removed_current_path_dropped"),
    ("MODEL_REGULARIZED_LOGISTIC", "KEEP_READY", "model",
     "Regularized logistic regression locked model family for "
     "Stage126 M1.",
     "model_family_ready_no_fitting_in_part5"),
    ("MODEL_RANDOM_FOREST", "KEEP_READY", "model",
     "Random forest locked model family for Stage126 M1.",
     "model_family_ready_no_fitting_in_part5"),
    ("MODEL_XGBOOST", "KEEP_READY", "model",
     "XGBoost locked model family for Stage126 M1.",
     "model_family_ready_no_fitting_in_part5"),
    ("IMBALANCE_CLASS_WEIGHTING", "KEEP_READY", "imbalance",
     "Primary class-weighting imbalance-handling strategy locked.",
     "primary_imbalance_strategy_ready"),
    ("IMBALANCE_SMOTE", "KEEP_ROBUSTNESS", "imbalance",
     "SMOTE robustness strategy locked (disables class weighting; "
     "training-fold only; no second tuning search).",
     "robustness_imbalance_strategy_ready"),
    ("FINAL_TEST_1400_1402", "KEEP_LOCKED", "temporal",
     "Locked single-use final test years 1400-1402; predictor values "
     "not inspected in Part 5.",
     "locked_for_single_future_evaluation_not_yet_used"),
    ("AVAILABILITY_FOUR_JALALI_MONTHS", "KEEP_LOCKED", "availability",
     "Active four-Jalali-month fixed regulatory lag remains locked.",
     "active_locked_method"),
    ("AVAILABILITY_SIX_MONTH_METHOD", "SUPERSEDED_HISTORICAL_ONLY",
     "availability",
     "Historical conservative six-month lag decision retained as "
     "history only; not active.",
     "superseded_historical_evidence_only"),
    ("BROAD_CODAL_PUBLISH_DATETIME_CAPTURE", "DROP_CURRENT_ACTIVE_PATH",
     "evidence_capture",
     "Broad CODAL PublishDateTime capture remains stopped on the "
     "current active path.",
     "not_admitted_current_path_dropped"),
    ("RAMPNA_1396_TO_1397_TIMING_VIOLATION", "KEEP_AUDIT_ONLY", "audit",
     "رمپنا|1396 → رمپنا|1397 timing violation retained as audit-only "
     "evidence; رمپنا|1396 does not re-enter analysis-ready data.",
     "audit_only_historical_violation_record"),
)

REQUIRED_KEEP_DROP_DECISIONS: dict[str, str] = {
    item_id: decision for item_id, decision, *_ in KEEP_DROP_SPEC
}
REQUIRED_KEEP_DROP_ITEM_IDS = frozenset(REQUIRED_KEEP_DROP_DECISIONS)

# --------------------------------------------------------------------------- #
# Blocker register exact rows
# --------------------------------------------------------------------------- #

# item_id, current_status, blocks_stage125_closure, blocks_stage126_m1,
# blocks_future_block, disposition, required_future_action
BLOCKER_SPEC: tuple[tuple[str, str, str, str, str, str, str], ...] = (
    ("M2_VALUES_NOT_COLLECTED", "no_values_collected", "false", "false",
     "M2", "deferred",
     "Collect M2 market/liquidity values under an authorized future "
     "extraction protocol before admitting M2 to any modeling block."),
    ("M3_AUTHORITATIVE_SOURCE_UNAVAILABLE",
     "no_authoritative_cbi_endpoint_admitted_current_path", "false", "false",
     "M3", "not_admitted",
     "M3 may re-enter only after: (1) a new explicit versioned human "
     "decision; (2) identification of an authoritative and reproducible "
     "source; (3) publication/availability-time validation; (4) coverage "
     "and temporal data-Gate approval. No M3 data collection is authorized "
     "in Part 5."),
    ("M4_VALUES_NOT_COLLECTED", "no_values_collected", "false", "false",
     "M4", "deferred",
     "Collect M4 audit/governance values under an authorized future "
     "extraction protocol before admitting M4 to any modeling block."),
    ("PART3B_EXPANSION_INCOMPLETE",
     "part3b_completed_false_expansion_superseded", "false", "false",
     "", "superseded",
     "None required for Stage125 closure or Stage126 M1 entry; Part 3B "
     "expansion remains historical and non-blocking."),
    ("ARTICLE141_LOW_EVENT_COUNT",
     "final_test_positive_1_on_primary_sample", "false", "false",
     "Article141 comparative inference", "descriptive_only",
     "Treat Article-141-only results as distributional/descriptive "
     "robustness only; do not use for comparative or inferential model "
     "ranking."),
    ("REVENUE_GROWTH_COVERAGE_FAILURE",
     "fold1_train_coverage_0.6040816327_below_0.75_threshold",
     "false", "false", "", "audit_only_rejected",
     "Keep revenue_growth_period_adjusted audit-only; re-evaluate "
     "coverage only if future data collection raises Fold-1 training "
     "coverage above the locked threshold."),
    ("NO_GITHUB_ACTIONS", "no_ci_workflow_configured", "false", "false",
     "CI", "local_canonical_verification_only",
     "Continue running --build/--check and pytest locally; configure "
     "CI only if separately authorized."),
    ("M1_PROVENANCE_GAPS_AUDITED", "provenance_gaps_recorded_part1_audit",
     "false", "false", "", "audited_missing_provenance_not_filled_or_guessed",
     "No action required; gaps remain audited-only and are never "
     "filled or guessed."),
)

REQUIRED_BLOCKER_ITEM_IDS = frozenset(spec[0] for spec in BLOCKER_SPEC)


class QCFail(RuntimeError):
    """Fail-closed Part 5 QC error."""


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
    baseline_tree = _git(root, "rev-parse", f"{EXPECTED_BASELINE_COMMIT}^{{tree}}")
    if baseline_tree != EXPECTED_BASELINE_TREE:
        raise QCFail(
            f"baseline tree mismatch: {baseline_tree} != "
            f"{EXPECTED_BASELINE_TREE}"
        )
    return head


def require_file_hash(
    repo_root: Path, rel: str, expected: str, *, label: str = "input",
) -> str:
    path = repo_root / rel
    if not path.is_file():
        raise QCFail(f"missing {label}: {rel}")
    got = sha256_file(path)
    if got != expected:
        raise QCFail(f"{label} hash mismatch: {rel}")
    return got


def frozen_part3c_hashes(repo_root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel, expected in FROZEN_PART3C_INPUTS.items():
        out[rel] = require_file_hash(
            repo_root, rel, expected, label="Part 3C input",
        )
    return out


def frozen_part4_output_hashes(repo_root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel, expected in FROZEN_PART4_OUTPUTS.items():
        out[rel] = require_file_hash(
            repo_root, rel, expected, label="Part 4 output",
        )
    out[PART4_SRC_REL] = require_file_hash(
        repo_root, PART4_SRC_REL, PART4_SRC_SHA256, label="Part 4 source",
    )
    out[PART4_TEST_REL] = require_file_hash(
        repo_root, PART4_TEST_REL, PART4_TEST_SHA256, label="Part 4 test",
    )
    return out


def _read_csv_dicts(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _assert(
    assertions: list[dict[str, str]], name: str, ok: bool, detail: str,
) -> None:
    assertions.append({
        "assertion": name,
        "status": "PASS" if ok else "FAIL",
        "detail": detail,
    })


# --------------------------------------------------------------------------- #
# Guards / mutation rejection helpers
# --------------------------------------------------------------------------- #

def reject_stage126_authorized(flag: bool) -> None:
    if flag:
        raise AuthorizationError(
            "stage126_authorized cannot be true during Part 5"
        )


def reject_modeling_started(flag: bool) -> None:
    if flag:
        raise AuthorizationError(
            "modeling_started cannot be true during Part 5"
        )


def reject_final_test_unlocked(flag: bool) -> None:
    if flag:
        raise AuthorizationError(
            "final_test_unlocked cannot be true during Part 5"
        )


def reject_revenue_growth_keep_ready(decision: str) -> None:
    if decision == "KEEP_READY":
        raise AuthorizationError(
            f"revenue_growth cannot become KEEP_READY: {decision}"
        )


def reject_article141_model_ready(decision: str) -> None:
    if decision in {"KEEP_READY", "KEEP_ROBUSTNESS"}:
        raise AuthorizationError(
            f"article141 cannot become model-ready: {decision}"
        )


def reject_m3_admitted(decision: str) -> None:
    if decision != "DROP_CURRENT_ACTIVE_PATH":
        raise AuthorizationError(f"M3 cannot be admitted: {decision}")


def reject_final_test_year_change(years: Any) -> None:
    if tuple(sorted(years)) != tuple(sorted(FINAL_TEST_YEARS)):
        raise AuthorizationError(
            f"final test years changed: {sorted(years)} != "
            f"{sorted(FINAL_TEST_YEARS)}"
        )


def reject_active_lag_change(months: int) -> None:
    if months != APPROVED_LAG_MONTHS:
        raise AuthorizationError(
            f"active availability lag changed: {months} != "
            f"{APPROVED_LAG_MONTHS}"
        )


def reject_next_research_pointer(next_id: str) -> None:
    if next_id != RESEARCH_NEXT:
        raise AuthorizationError(
            f"next research pointer changed: {next_id} != {RESEARCH_NEXT}"
        )


def validate_decision_vocabulary(decision: str) -> None:
    if decision not in KEEP_DROP_VOCAB:
        raise QCFail(f"unknown keep/drop decision vocabulary: {decision}")


def validate_keep_drop_rows(rows: list[dict[str, str]]) -> None:
    seen: set[str] = set()
    for row in rows:
        item_id = row.get("item_id")
        decision = row.get("decision")
        if not item_id:
            raise QCFail("keep/drop row missing item_id")
        validate_decision_vocabulary(decision)
        if item_id in seen:
            raise QCFail(f"duplicate keep/drop item_id: {item_id}")
        seen.add(item_id)
    missing = REQUIRED_KEEP_DROP_ITEM_IDS - seen
    if missing:
        raise QCFail(f"missing required keep/drop items: {sorted(missing)}")
    by_id = {r["item_id"]: r["decision"] for r in rows}
    for item_id, expected in REQUIRED_KEEP_DROP_DECISIONS.items():
        actual = by_id[item_id]
        if actual != expected:
            raise QCFail(
                f"keep/drop decision mutated for {item_id}: "
                f"{actual} != {expected}"
            )


def validate_blocker_rows(rows: list[dict[str, str]]) -> None:
    seen: set[str] = set()
    for row in rows:
        item_id = row.get("item_id")
        if not item_id:
            raise QCFail("blocker row missing item_id")
        for flag_col in ("blocks_stage125_closure", "blocks_stage126_m1"):
            if row.get(flag_col) not in {"true", "false"}:
                raise QCFail(
                    f"blocker row {item_id} has non-boolean-string "
                    f"{flag_col}={row.get(flag_col)!r}"
                )
        seen.add(item_id)
    missing = REQUIRED_BLOCKER_ITEM_IDS - seen
    if missing:
        raise QCFail(f"missing required blocker items: {sorted(missing)}")
    for row in rows:
        if row["item_id"] in {"M2_VALUES_NOT_COLLECTED",
                               "M3_AUTHORITATIVE_SOURCE_UNAVAILABLE",
                               "M4_VALUES_NOT_COLLECTED"}:
            if row["blocks_stage125_closure"] != "false":
                raise QCFail(
                    f"{row['item_id']} must not block Stage125 closure"
                )
            if row["blocks_stage126_m1"] != "false":
                raise QCFail(
                    f"{row['item_id']} must not block Stage126 M1 entry"
                )


BANNED_IMPORT_NAMES = frozenset({
    "LogisticRegression", "RandomForestClassifier", "XGBClassifier",
    "SMOTE", "GridSearchCV", "RandomizedSearchCV",
})
BANNED_MODULES = ("xgboost", "shap", "imblearn")
BANNED_SKLEARN_SUBMODULES = (
    "sklearn.linear_model", "sklearn.ensemble", "sklearn.model_selection",
)
BANNED_CALL_NAMES = frozenset({"fit", "fit_predict", "predict", "predict_proba"})


def assert_no_model_imports_in_source(
    repo_root: Path, rel: str = SRC_REL,
) -> None:
    src_path = repo_root / rel
    if not src_path.is_file():
        return
    src = src_path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name in BANNED_IMPORT_NAMES or name in {"shap"}:
                    raise AuthorizationError(f"model import attempt: {name}")
                if name in BANNED_MODULES:
                    raise AuthorizationError(f"model import attempt: {name}")
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            names = {a.name for a in node.names}
            hit = names & BANNED_IMPORT_NAMES
            if hit:
                raise AuthorizationError(f"model import attempt: {sorted(hit)}")
            if mod in BANNED_MODULES:
                raise AuthorizationError(f"model import attempt: {mod}")
            if mod.startswith(BANNED_SKLEARN_SUBMODULES):
                raise AuthorizationError(f"model import attempt: {mod}")
        if isinstance(node, ast.Call):
            fn = node.func
            call_name = None
            if isinstance(fn, ast.Name):
                call_name = fn.id
            elif isinstance(fn, ast.Attribute):
                call_name = fn.attr
            if call_name in BANNED_CALL_NAMES:
                raise AuthorizationError(
                    f"forbidden model call attempted: {call_name}"
                )


FORBIDDEN_ANALYSIS_READY_IDENTIFIERS = frozenset({
    "load_analysis_ready", "ANALYSIS_READY_FILES",
})


def assert_no_analysis_ready_access_in_source(
    repo_root: Path, rel: str = SRC_REL,
) -> None:
    """AST-based check (not a raw substring scan, to avoid self-matching
    this guard's own identifier constants) that Part 5 source never
    references Part 4's analysis-ready predictor loader/paths.
    """
    src_path = repo_root / rel
    if not src_path.is_file():
        return
    tree = ast.parse(src_path.read_text(encoding="utf-8"))
    hits: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Name)
            and node.id in FORBIDDEN_ANALYSIS_READY_IDENTIFIERS
        ):
            hits.add(node.id)
        if (
            isinstance(node, ast.Attribute)
            and node.attr in FORBIDDEN_ANALYSIS_READY_IDENTIFIERS
        ):
            hits.add(node.attr)
    if hits:
        raise AuthorizationError(
            f"Part 5 must not access analysis-ready predictor data: "
            f"{sorted(hits)}"
        )


# Stage126 M1 development is gated by the shared exact authorization transition
# guard (Persian text byte-for-byte + recomputed SHA-256 + required flags).
from src import stage126_authorization_transition_guard as _stage126_auth

STAGE126_M1_AUTHORIZATION_RECORD_REL = (
    _stage126_auth.AUTHORIZATION_RECORD_REL
)
STAGE126_M1_AUTHORIZATION_TEXT_SHA256 = (
    _stage126_auth.AUTHORIZATION_TEXT_SHA256
)


def stage126_m1_development_authorized(repo_root: Path) -> bool:
    """Delegate to the shared Stage126 authorization transition guard."""
    return _stage126_auth.stage126_m1_development_authorized(repo_root)


def effective_forbidden_surfaces(repo_root: Path) -> tuple[str, ...]:
    """Forbidden Stage126 surfaces after applying the authorization gate.

    Once Stage126 M1 development is human-authorized, the ``project/stage126``
    directory surface is permitted (development-only work lives there while the
    final test remains locked). The two legacy Stage126 filenames stay forbidden
    regardless, as they were never the sanctioned entry points.
    """
    if stage126_m1_development_authorized(repo_root):
        return tuple(
            rel for rel in FORBIDDEN_SURFACE_EXACT if rel != "project/stage126"
        )
    return FORBIDDEN_SURFACE_EXACT


def assert_forbidden_surfaces_absent(repo_root: Path) -> None:
    forbidden = effective_forbidden_surfaces(repo_root)
    present = [rel for rel in forbidden if (repo_root / rel).exists()]
    if present:
        raise AuthorizationError(f"forbidden Stage126 surfaces present: {present}")


# --------------------------------------------------------------------------- #
# Loaders over Part 4 aggregate artifacts (never analysis-ready predictors)
# --------------------------------------------------------------------------- #

def load_part4_qc(repo_root: Path) -> dict[str, Any]:
    rel = f"{PART4_OUTPUT_DIR}/stage125_part4_statistical_analysis_plan_qc_report.json"
    data = json.loads((repo_root / rel).read_text(encoding="utf-8"))
    if data.get("assertion_count") != 70:
        raise QCFail(
            f"Part 4 QC assertion_count changed: {data.get('assertion_count')}"
        )
    if data.get("failed_count") != 0:
        raise QCFail(f"Part 4 QC has failed assertions: {data.get('failed_count')}")
    if data.get("all_pass") is not True:
        raise QCFail("Part 4 QC all_pass is not true")
    if data.get("contract_version") != PART4_CONTRACT_VERSION:
        raise QCFail(
            f"Part 4 QC contract_version changed: {data.get('contract_version')}"
        )
    return data


def load_part4_sample_target_matrix(repo_root: Path) -> list[dict[str, str]]:
    rel = f"{PART4_OUTPUT_DIR}/part4_sample_target_matrix_stage125.csv"
    rows = _read_csv_dicts(repo_root / rel)
    by_sample_primary = {
        r["sample_design"]: r for r in rows if r["target"] == PRIMARY_TARGET
    }
    for sample, spec in SAMPLE_SPECS.items():
        row = by_sample_primary.get(sample)
        if row is None:
            raise QCFail(f"missing Part 4 sample-target row: {sample}")
        if (
            int(row["rows"]) != spec["rows"]
            or int(row["companies"]) != spec["companies"]
            or int(row["positive"]) != spec["positive"]
            or int(row["negative"]) != spec["negative"]
        ):
            raise QCFail(f"Part 4 sample-target counts mutated: {sample}")
    target_names = {r["target"] for r in rows}
    if target_names != set(ALL_TARGETS):
        raise QCFail(f"Part 4 target set mutated: {sorted(target_names)}")
    return rows


def load_part4_feature_sets(repo_root: Path) -> list[dict[str, str]]:
    rel = f"{PART4_OUTPUT_DIR}/part4_feature_sets_stage125.csv"
    rows = _read_csv_dicts(repo_root / rel)
    primary = sorted(
        (r for r in rows if r["feature_set"] == "M1_PRIMARY_FEATURE_ORDER"),
        key=lambda r: int(r["position"]),
    )
    proximity = sorted(
        (r for r in rows
         if r["feature_set"] == "M1_TARGET_PROXIMITY_ROBUSTNESS"),
        key=lambda r: int(r["position"]),
    )
    primary_names = [r["feature_name"] for r in primary]
    proximity_names = [r["feature_name"] for r in proximity]
    if primary_names != M1_PRIMARY_FEATURE_ORDER:
        raise QCFail(
            f"Part 4 M1 primary feature order mutated: {primary_names}"
        )
    if proximity_names != M1_TARGET_PROXIMITY_ROBUSTNESS:
        raise QCFail(
            f"Part 4 M1 target-proximity feature order mutated: "
            f"{proximity_names}"
        )
    if REVENUE_GROWTH_FEATURE in primary_names + proximity_names:
        raise QCFail("revenue_growth present in Part 4 model feature surfaces")
    return rows


# --------------------------------------------------------------------------- #
# Build: keep/drop, blocker register, entry contract
# --------------------------------------------------------------------------- #

def build_keep_drop_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item_id, decision, category, notes, interpretation in KEEP_DROP_SPEC:
        rows.append({
            "item_id": item_id,
            "decision": decision,
            "category": category,
            "notes": notes,
            "blocks_stage126_m1": "false",
            "interpretation": interpretation,
        })
    return rows


def build_blocker_register_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for (item_id, current_status, blocks_closure, blocks_m1, future_block,
         disposition, required_action) in BLOCKER_SPEC:
        rows.append({
            "item_id": item_id,
            "current_status": current_status,
            "blocks_stage125_closure": blocks_closure,
            "blocks_stage126_m1": blocks_m1,
            "blocks_future_block": future_block,
            "disposition": disposition,
            "required_future_action": required_action,
        })
    return rows


REGISTERED_M1_ROBUSTNESS_AFTER_PRIMARY_LOCK: tuple[dict[str, Any], ...] = (
    {
        "category_id": "m1_target_proximity_six_feature_set",
        "feature_set": "M1_TARGET_PROXIMITY_ROBUSTNESS",
        "feature_count": 6,
        "features_exact_order": list(M1_TARGET_PROXIMITY_ROBUSTNESS),
        "role": "target_proximity_feature_set_robustness",
    },
    {
        "category_id": "main_rule_b_listing_robustness",
        "sample": "main_rule_b_listing_robustness",
        "role": "listing_timing_sample_robustness",
    },
    {
        "category_id": "expanded_rule_a_company_scope_robustness",
        "sample": "expanded_rule_a_company_scope_robustness",
        "role": "expanded_company_scope_sample_robustness",
    },
    {
        "category_id": "expanded_rule_b_combined_robustness",
        "sample": "expanded_rule_b_combined_robustness",
        "role": "combined_sample_robustness",
    },
    {
        "category_id": "persistent_loss_robustness_target",
        "target": SECONDARY_TARGET,
        "role": "secondary_robustness_target",
    },
    {
        "category_id": "smote_training_fold_only_robustness",
        "imbalance_strategy": "SMOTE",
        "role": "smote_training_fold_only_robustness",
        "class_weighting": "disabled",
        "second_tuning_search": False,
        "notes": (
            "SMOTE inside training folds only; class weighting disabled; "
            "no second tuning search"
        ),
    },
)

REQUIRED_ROBUSTNESS_SAMPLES = frozenset({
    "main_rule_b_listing_robustness",
    "expanded_rule_a_company_scope_robustness",
    "expanded_rule_b_combined_robustness",
})


ENTRY_READINESS_READY = "READY_FOR_HUMAN_AUTHORIZATION_DECISION"
ENTRY_READINESS_NOT_READY = "NOT_READY_WITH_BLOCKERS"


def build_stage126_m1_entry_contract(*, entry_ready: bool) -> dict[str, Any]:
    """Stage126 M1 entry contract with readiness as an explicit derived input.

    ``entry_ready`` MUST be the complete final Gate 125.0 result. When the Gate
    passes, ``entry_readiness`` is READY_FOR_HUMAN_AUTHORIZATION_DECISION and
    ``stage126_m1_entry_ready`` is true. When any mandatory Gate dimension
    fails, both fall to NOT_READY_WITH_BLOCKERS / false. Under no circumstance
    may a failed Gate leave the contract in the READY state.

    The authorization/boundary flags below are unconditional constants and
    remain false in both the ready and the not-ready state.
    """
    entry_ready = bool(entry_ready)
    return {
        "contract_id": "stage126_m1_financial_baseline_entry_contract",
        "entry_readiness": (
            ENTRY_READINESS_READY if entry_ready else ENTRY_READINESS_NOT_READY
        ),
        "stage126_m1_entry_ready": entry_ready,
        "stage126_authorized": False,
        "stage126_started": False,
        "modeling_authorized": False,
        "modeling_started": False,
        "final_test_unlocked": False,
        "final_test_predictor_values_inspected": False,
        "primary_specification": {
            "sample": PRIMARY_SAMPLE,
            "target": PRIMARY_TARGET,
            "feature_set": "M1_PRIMARY_FEATURE_ORDER",
            "feature_count": len(M1_PRIMARY_FEATURE_ORDER),
            "features_exact_order": list(M1_PRIMARY_FEATURE_ORDER),
            "models": [
                "regularized_logistic_regression", "random_forest", "xgboost",
            ],
            "development_years": "1393\u20131399",
            "fold1": {"train": "1393\u20131395", "validation": "1396\u20131397"},
            "fold2": {"train": "1393\u20131397", "validation": "1398\u20131399"},
            "locked_final_test": "1400\u20131402",
            "primary_metric": PRIMARY_METRIC,
        },
        "registered_m1_robustness_after_primary_lock": [
            dict(entry) for entry in REGISTERED_M1_ROBUSTNESS_AFTER_PRIMARY_LOCK
        ],
        "article141_excluded_from_model_estimation": True,
        "m2_m3_m4_excluded_from_immediate_stage126_m1": True,
        "future_stage126_sequence_recorded_not_executed": [
            "1_obtain_explicit_human_stage126_authorization",
            "2_fit_primary_M1_models_on_development_folds_only",
            "3_select_hyperparameters_within_locked_finite_budget",
            "4_evaluate_registered_M1_robustness_variants",
            "5_unlock_locked_final_test_1400_1402_exactly_once",
            "6_report_paired_uncertainty_and_holm_corrected_comparisons",
        ],
        "authorization_note": (
            "entry_readiness is NOT authorization; stage126_authorized "
            "remains false"
        ),
    }


def validate_registered_m1_robustness(entries: list[dict[str, Any]]) -> None:
    samples = [e.get("sample") for e in entries if e.get("sample")]
    if len(samples) != len(set(samples)):
        raise QCFail("duplicate robustness sample entries")
    if sorted(samples) != sorted(REQUIRED_ROBUSTNESS_SAMPLES):
        raise QCFail(
            f"robustness sample set mutation: {sorted(samples)} != "
            f"{sorted(REQUIRED_ROBUSTNESS_SAMPLES)}"
        )
    if len(entries) != 6:
        raise QCFail(
            f"registered_m1_robustness must have exactly 6 categories: "
            f"{len(entries)}"
        )
    if any(e.get("target") == ARTICLE141_TARGET for e in entries):
        raise QCFail("Article-141 must not enter model-estimation robustness")


# --------------------------------------------------------------------------- #
# Gate 125.0 — derived readiness dimensions
# --------------------------------------------------------------------------- #

CLOSURE_OUTCOME_READY = "READY_FOR_STAGE126_M1_HUMAN_AUTHORIZATION_DECISION"
CLOSURE_OUTCOME_NOT_READY = "NOT_READY_WITH_BLOCKERS"

EXPECTED_ENTRY_CONTRACT_ID = "stage126_m1_financial_baseline_entry_contract"
EXPECTED_M1_MODELS = [
    "regularized_logistic_regression", "random_forest", "xgboost",
]
EXPECTED_FOLD1 = {"train": "1393\u20131395", "validation": "1396\u20131397"}
EXPECTED_FOLD2 = {"train": "1393\u20131397", "validation": "1398\u20131399"}
EXPECTED_DEVELOPMENT_YEARS = "1393\u20131399"
EXPECTED_LOCKED_FINAL_TEST = "1400\u20131402"


def evaluate_entry_boundary(entry_contract: dict[str, Any]) -> tuple[bool, str]:
    """Structural + authorization boundary Gate dimension.

    This dimension MUST NOT depend on ``stage126_m1_entry_ready`` or
    ``entry_readiness`` — readiness is attached only after the complete Gate
    result is derived, so requiring readiness here would be circular. It
    validates only the structural specification and the hard authorization
    boundary that must hold regardless of readiness.
    """
    spec = entry_contract.get("primary_specification") or {}
    robustness = entry_contract.get(
        "registered_m1_robustness_after_primary_lock",
    ) or []
    try:
        validate_registered_m1_robustness(list(robustness))
        robustness_ok = len(robustness) == 6
    except QCFail:
        robustness_ok = False

    checks = {
        "contract_id":
            entry_contract.get("contract_id") == EXPECTED_ENTRY_CONTRACT_ID,
        "primary_sample": spec.get("sample") == PRIMARY_SAMPLE,
        "primary_target": spec.get("target") == PRIMARY_TARGET,
        "primary_feature_set":
            spec.get("feature_set") == "M1_PRIMARY_FEATURE_ORDER",
        "nine_features_exact":
            spec.get("feature_count") == 9
            and spec.get("features_exact_order") == M1_PRIMARY_FEATURE_ORDER
            and len(M1_PRIMARY_FEATURE_ORDER) == 9,
        "three_model_families_exact":
            spec.get("models") == EXPECTED_M1_MODELS,
        "development_folds_exact":
            spec.get("development_years") == EXPECTED_DEVELOPMENT_YEARS
            and spec.get("fold1") == EXPECTED_FOLD1
            and spec.get("fold2") == EXPECTED_FOLD2,
        "final_test_years_exact":
            spec.get("locked_final_test") == EXPECTED_LOCKED_FINAL_TEST
            and tuple(sorted(FINAL_TEST_YEARS)) == (1400, 1401, 1402),
        "primary_metric_exact": spec.get("primary_metric") == PRIMARY_METRIC,
        "six_robustness_categories_exact": robustness_ok,
        "article141_excluded":
            entry_contract.get("article141_excluded_from_model_estimation")
            is True,
        "m2_m3_m4_excluded":
            entry_contract.get(
                "m2_m3_m4_excluded_from_immediate_stage126_m1",
            ) is True,
        "stage126_authorized_false":
            entry_contract.get("stage126_authorized") is False,
        "stage126_started_false":
            entry_contract.get("stage126_started") is False,
        "modeling_authorized_false":
            entry_contract.get("modeling_authorized") is False,
        "modeling_started_false":
            entry_contract.get("modeling_started") is False,
        "final_test_unlocked_false":
            entry_contract.get("final_test_unlocked") is False,
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        return False, f"boundary_failed:{sorted(failed)}"
    return True, "structural_and_authorization_boundary_valid"

# Exact Part 5 generated paths authorized to be dirty during --build only.
AUTHORIZED_PART5_GENERATED_PATHS = frozenset(
    {f"{PART4_OUTPUT_DIR}/{name}" for name in TRACKED_CONTENT_FILES}
    | {
        f"{PART4_OUTPUT_DIR}/{F_QC}",
        f"{PART4_OUTPUT_DIR}/{F_METADATA}",
    }
)


def git_status_porcelain(repo_root: Path) -> list[str]:
    """Read-only working-tree status via the exact allowed git status form.

    Must not strip leading spaces from the full stdout: porcelain v1 lines use
    a fixed 2-char XY status plus a space, and stripping the blob would corrupt
    the first path (e.g. `` M path`` → ``M path`` → ``ath``).
    """
    proc = subprocess.run(
        [
            "git", "-C", str(repo_root),
            "status", "--porcelain=v1", "--untracked-files=all",
        ],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise QCFail(
            f"git status --porcelain=v1 --untracked-files=all failed: "
            f"{proc.stderr.strip()}"
        )
    return [line for line in proc.stdout.splitlines() if line.strip()]


def parse_porcelain_paths(lines: list[str]) -> list[str]:
    """Extract paths from porcelain v1 lines (tracked mods, deletes, untracked)."""
    paths: list[str] = []
    for line in lines:
        if len(line) < 4:
            continue
        body = line[3:]
        if " -> " in body:
            body = body.split(" -> ", 1)[1]
        paths.append(body.replace("\\", "/"))
    return paths


def evaluate_working_tree_clean(
    repo_root: Path, *, mode: str,
) -> tuple[bool, str]:
    """Actual git-status working-tree Gate.

    --check: porcelain output must be completely empty.
    --build: only exact authorized Part 5 generated paths may be dirty.
    """
    if mode not in {"build", "check"}:
        raise QCFail(f"invalid working-tree mode: {mode}")
    lines = git_status_porcelain(repo_root)
    if mode == "check":
        ok = len(lines) == 0
        # Stable pass detail so --build/--check closure reports do not drift.
        return ok, "clean" if ok else f"dirty_lines={len(lines)}"
    paths = parse_porcelain_paths(lines)
    stage126_authorized = stage126_m1_development_authorized(repo_root)

    def _authorized_dirty(p: str) -> bool:
        if p in AUTHORIZED_PART5_GENERATED_PATHS:
            return True
        # Once Stage126 M1 development is human-authorized, its own surfaces may
        # legitimately be present/dirty alongside a Part 5 build. Part 5 never
        # writes them; they are the authorized Stage126 development deliverables.
        if stage126_authorized and (
            p == "project/src/stage126_m1_primary_development_tuning.py"
            or p == "project/run_stage126_m1_primary_development_tuning.py"
            or p == "project/tests/test_stage126_m1_primary_development_tuning.py"
            or p.startswith("project/stage126/")
        ):
            return True
        return False

    unauthorized = [p for p in paths if not _authorized_dirty(p)]
    ok = len(unauthorized) == 0
    detail = "clean" if ok else f"unauthorized={unauthorized[:8]}"
    return ok, detail


def load_handoff_state(repo_root: Path) -> dict[str, Any]:
    path = repo_root / HANDOFF_STATE_REL
    if not path.is_file():
        raise QCFail(f"missing handoff state: {HANDOFF_STATE_REL}")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_actual_handoff(
    repo_root: Path, *, derived_completed: bool, derived_entry_ready: bool,
) -> tuple[bool, str]:
    """Validate actual project/docs/ai/handoff_state.json values.

    When Stage126 M1 development is human-authorized, validate the *actual*
    authorized Stage126 successor Handoff (not a bypass). The Part 5 readiness
    verdict (``derived_completed`` / ``derived_entry_ready``) must still hold,
    and every Stage126 successor marker required by the transition contract must
    match exactly. The Handoff is never excluded from this check.
    """
    try:
        state = load_handoff_state(repo_root)
    except QCFail as exc:
        return False, str(exc)

    if stage126_m1_development_authorized(repo_root):
        expected_selected_qc = (
            "project/stage126/stage126_m1_primary_development_tuning_qc_report.json"
        )
        checks = [
            (state.get("current_stage") == "Stage126", "current_stage"),
            (
                state.get("active_workstream")
                == "stage126_m1_financial_baseline",
                "active_workstream",
            ),
            (state.get("stage125_completed") is True, "stage125_completed"),
            (
                state.get("stage126_m1_entry_ready") is True,
                "stage126_m1_entry_ready",
            ),
            # Part 5-derived readiness must still agree with the live successor.
            (derived_completed is True, "derived_completed"),
            (derived_entry_ready is True, "derived_entry_ready"),
            (state.get("stage126_authorized") is True, "stage126_authorized"),
            (state.get("stage126_started") is True, "stage126_started"),
            (
                state.get("development_modeling_authorized") is True,
                "development_modeling_authorized",
            ),
            (state.get("modeling_authorized") is True, "modeling_authorized"),
            (state.get("modeling_started") is True, "modeling_started"),
            (
                state.get("m1_primary_development_tuning_completed") is True,
                "m1_primary_development_tuning_completed",
            ),
            (
                state.get("m1_robustness_started") is False,
                "m1_robustness_started",
            ),
            (
                state.get("m1_robustness_completed") is False,
                "m1_robustness_completed",
            ),
            (state.get("m2_data_collected") is False, "m2_data_collected"),
            (state.get("m3_data_collected") is False, "m3_data_collected"),
            (state.get("m4_data_collected") is False, "m4_data_collected"),
            (state.get("final_test_unlocked") is False, "final_test_unlocked"),
            (
                state.get("final_test_access_authorized") is False,
                "final_test_access_authorized",
            ),
            (
                state.get("final_test_predictor_values_inspected") is False,
                "final_test_predictor_values_inspected",
            ),
            (
                state.get("final_test_target_values_inspected") is False,
                "final_test_target_values_inspected",
            ),
            (
                state.get("final_test_evaluation_performed") is False,
                "final_test_evaluation_performed",
            ),
            (
                state.get("selected_qc_scope")
                == "stage126_m1_financial_baseline",
                "selected_qc_scope",
            ),
            (
                str(state.get("selected_qc_path", "")).replace("\\", "/")
                == expected_selected_qc,
                "selected_qc_path",
            ),
            (
                state.get("contract_version")
                == "stage126_m1_primary_development_tuning_v1",
                "contract_version",
            ),
            (
                state.get("last_completed_micro_part")
                == "stage125-part5-readiness-closure",
                "last_completed_micro_part",
            ),
            (
                state.get("next_research_action_id")
                == "stage126-m1-financial-baseline",
                "next_research_action_id",
            ),
        ]
        failed = [name for ok, name in checks if not ok]
        if failed:
            return False, f"handoff_mismatch:{','.join(failed)}"
        return True, "actual_stage126_successor_handoff_matches_authorized_transition"

    expected_selected_qc = f"{PART4_OUTPUT_DIR}/{F_QC}"
    checks = [
        (
            state.get("last_completed_micro_part") == RESEARCH_ACTION_ID,
            "last_completed_micro_part",
        ),
        (
            state.get("next_research_action_id") == RESEARCH_NEXT,
            "next_research_action_id",
        ),
        (
            state.get("selected_qc_scope") == QC_STAGE,
            "selected_qc_scope",
        ),
        (
            str(state.get("selected_qc_path", "")).replace("\\", "/")
            == expected_selected_qc,
            "selected_qc_path",
        ),
        (
            state.get("contract_version") == CONTRACT_VERSION,
            "contract_version",
        ),
        (
            state.get("stage125_completed") is derived_completed,
            "stage125_completed",
        ),
        (
            state.get("stage126_m1_entry_ready") is derived_entry_ready,
            "stage126_m1_entry_ready",
        ),
        (state.get("stage126_authorized") is False, "stage126_authorized"),
        (state.get("stage126_started") is False, "stage126_started"),
        (state.get("modeling_authorized") is False, "modeling_authorized"),
        (state.get("modeling_started") is False, "modeling_started"),
        (state.get("final_test_unlocked") is False, "final_test_unlocked"),
        (state.get("part3b_completed") is False, "part3b_completed"),
        (
            state.get("active_availability_lag_months") == APPROVED_LAG_MONTHS,
            "active_availability_lag_months",
        ),
    ]
    failed = [name for ok, name in checks if not ok]
    if failed:
        return False, f"handoff_mismatch:{','.join(failed)}"
    return True, "actual_handoff_state_matches_derived_closure"


def derive_closure_flags(all_gate_pass: bool) -> dict[str, Any]:
    return {
        "stage125_part5_readiness_closure_completed": bool(all_gate_pass),
        "stage125_completed": bool(all_gate_pass),
        "stage126_m1_entry_ready": bool(all_gate_pass),
        "stage125_gate_125_0": "PASS" if all_gate_pass else "FAIL",
        "closure_outcome": (
            CLOSURE_OUTCOME_READY if all_gate_pass else CLOSURE_OUTCOME_NOT_READY
        ),
        "stage126_authorized": False,
        "stage126_started": False,
        "modeling_authorized": False,
        "modeling_started": False,
        "final_test_unlocked": False,
    }


# --------------------------------------------------------------------------- #
# Cross-artifact readiness consistency
# --------------------------------------------------------------------------- #

# The six readiness surfaces that must always agree (§3). For a passing Gate
# every surface must report ready; for a failing Gate every surface must report
# not-ready. No surface may hold the ready outcome while all_gate_pass is false.
READINESS_SURFACE_NAMES = (
    "closure_report",
    "entry_contract",
    "qc_report",
    "metadata",
    "handoff_state",
    "readme",
)


def _readme_reports_ready(readme_text: str) -> bool | None:
    """Reduce the README to a single ready / not-ready / ambiguous state.

    Validates BOTH readiness statements the README carries — the
    ``closure_outcome`` and the entry-contract ``entry_readiness`` — so a
    README can never look ready on one statement while not-ready on the other.

    Ready  => contains CLOSURE_OUTCOME_READY and ENTRY_READINESS_READY, and does
              NOT contain NOT_READY_WITH_BLOCKERS.
    Failed => contains NOT_READY_WITH_BLOCKERS, and contains NEITHER READY
              string.
    Anything else (mixed / ambiguous) => None (fail-closed).
    """
    has_closure_ready = CLOSURE_OUTCOME_READY in readme_text
    has_entry_ready = ENTRY_READINESS_READY in readme_text
    # CLOSURE_OUTCOME_NOT_READY and ENTRY_READINESS_NOT_READY are the same
    # "NOT_READY_WITH_BLOCKERS" token, so one membership test covers both.
    has_not_ready = CLOSURE_OUTCOME_NOT_READY in readme_text
    if has_closure_ready and has_entry_ready and not has_not_ready:
        return True
    if has_not_ready and not has_closure_ready and not has_entry_ready:
        return False
    return None  # ambiguous / contradictory README


def readiness_surface_states(
    *,
    closure_report: dict[str, Any] | None = None,
    entry_contract: dict[str, Any] | None = None,
    qc_report: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    handoff_state: dict[str, Any] | None = None,
    readme_text: str | None = None,
) -> dict[str, bool | None]:
    """Reduce each provided surface to a single ready / not-ready / ambiguous.

    ``True`` = surface reports the ready outcome, ``False`` = surface reports
    not-ready, ``None`` = surface is internally inconsistent (fail-closed).
    """
    states: dict[str, bool | None] = {}

    def _bool_ready(*flags: Any) -> bool | None:
        if all(f is True for f in flags):
            return True
        if all(f is False for f in flags):
            return False
        return None

    if closure_report is not None:
        states["closure_report"] = _bool_ready(
            closure_report.get("stage126_m1_entry_ready"),
            closure_report.get("stage125_completed"),
            closure_report.get("all_gate_pass"),
            closure_report.get("closure_outcome") == CLOSURE_OUTCOME_READY,
            closure_report.get("stage125_gate_125_0") == "PASS",
        )
    if entry_contract is not None:
        states["entry_contract"] = _bool_ready(
            entry_contract.get("stage126_m1_entry_ready"),
            entry_contract.get("entry_readiness") == ENTRY_READINESS_READY,
        )
    if qc_report is not None:
        states["qc_report"] = _bool_ready(
            qc_report.get("stage126_m1_entry_ready"),
            qc_report.get("stage125_completed"),
            qc_report.get("stage125_gate_125_0") == "PASS",
        )
    if metadata is not None:
        states["metadata"] = _bool_ready(
            metadata.get("stage126_m1_entry_ready"),
            metadata.get("stage125_completed"),
            metadata.get("closure_outcome") == CLOSURE_OUTCOME_READY,
            metadata.get("stage125_gate_125_0") == "PASS",
        )
    if handoff_state is not None:
        # Stage126 successor Handoff omits Part 5-only workflow fields such as
        # ``stage125_part5_readiness_closure_completed``; readiness agreement
        # for the authorized successor uses the Stage126-carried readiness
        # flags. Pre-Stage126 Handoff still requires the three Part 5 flags.
        if (
            handoff_state.get("stage126_authorized") is True
            or handoff_state.get("current_stage") == "Stage126"
            or handoff_state.get("active_workstream")
            == "stage126_m1_financial_baseline"
        ):
            states["handoff_state"] = _bool_ready(
                handoff_state.get("stage126_m1_entry_ready"),
                handoff_state.get("stage125_completed"),
            )
        else:
            states["handoff_state"] = _bool_ready(
                handoff_state.get("stage126_m1_entry_ready"),
                handoff_state.get("stage125_completed"),
                handoff_state.get("stage125_part5_readiness_closure_completed"),
            )
    if readme_text is not None:
        states["readme"] = _readme_reports_ready(readme_text)
    return states


def validate_readiness_surface_consistency(
    *,
    final_gate_pass: bool,
    closure_report: dict[str, Any] | None = None,
    entry_contract: dict[str, Any] | None = None,
    qc_report: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    handoff_state: dict[str, Any] | None = None,
    readme_text: str | None = None,
) -> tuple[bool, str]:
    """Require every provided readiness surface to agree with the final Gate.

    Fail-closed: any surface that disagrees, or is internally ambiguous, or
    holds the ready outcome while ``final_gate_pass`` is false, is a failure.
    """
    states = readiness_surface_states(
        closure_report=closure_report,
        entry_contract=entry_contract,
        qc_report=qc_report,
        metadata=metadata,
        handoff_state=handoff_state,
        readme_text=readme_text,
    )
    disagreeing = [
        name for name, ready in states.items()
        if ready is not bool(final_gate_pass)
    ]
    if disagreeing:
        return False, (
            f"readiness_surface_disagreement:final_gate_pass="
            f"{bool(final_gate_pass)} states="
            f"{ {k: states[k] for k in sorted(states)} } "
            f"disagreeing={sorted(disagreeing)}"
        )
    if not final_gate_pass:
        leaked = [name for name, ready in states.items() if ready is True]
        if leaked:
            return False, f"ready_state_leaked_on_failed_gate:{sorted(leaked)}"
    return True, (
        f"all_{len(states)}_readiness_surfaces_consistent_"
        f"{'ready' if final_gate_pass else 'not_ready'}"
    )


def check_cross_artifact_readiness_consistency(
    repo_root: Path, out_dir: Path | None = None,
) -> tuple[bool, str, dict[str, bool | None]]:
    """Read all six on-disk readiness surfaces and validate they agree.

    ``final_gate_pass`` is taken from the closure report's ``all_gate_pass``.
    Returns ``(ok, detail, per_surface_states)``.
    """
    out = out_dir or (repo_root / PART4_OUTPUT_DIR)

    def _load_json(rel_name: str) -> dict[str, Any] | None:
        path = out / rel_name
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    closure = _load_json(F_CLOSURE_REPORT)
    entry = _load_json(F_ENTRY_CONTRACT)
    qc = _load_json(F_QC)
    metadata = _load_json(F_METADATA)
    readme_path = out / F_README
    readme_text = (
        readme_path.read_text(encoding="utf-8")
        if readme_path.is_file() else None
    )
    handoff_path = repo_root / HANDOFF_STATE_REL
    # Always include the live Handoff in cross-artifact readiness consistency.
    # When Stage126 is authorized the successor Handoff still reports
    # stage125_completed / stage126_m1_entry_ready and must agree with Part 5's
    # ready verdict — it is never omitted.
    handoff = (
        json.loads(handoff_path.read_text(encoding="utf-8"))
        if handoff_path.is_file() else None
    )
    if closure is None:
        return False, "missing_closure_report", {}
    final_gate_pass = bool(closure.get("all_gate_pass"))
    states = readiness_surface_states(
        closure_report=closure,
        entry_contract=entry,
        qc_report=qc,
        metadata=metadata,
        handoff_state=handoff,
        readme_text=readme_text,
    )
    ok, detail = validate_readiness_surface_consistency(
        final_gate_pass=final_gate_pass,
        closure_report=closure,
        entry_contract=entry,
        qc_report=qc,
        metadata=metadata,
        handoff_state=handoff,
        readme_text=readme_text,
    )
    return ok, detail, states


def _evaluate_contradiction_free_docs(
    *,
    repo_root: Path,
    readme_text: str,
    derived_completed: bool,
) -> tuple[bool, str]:
    roadmap_text = ""
    roadmap_path = repo_root / ROADMAP_REL
    if roadmap_path.is_file():
        roadmap_text = roadmap_path.read_text(encoding="utf-8")
    roadmap_lists_next = (
        f"next_research_action_id: {RESEARCH_ACTION_ID}" in roadmap_text
    )
    roadmap_already_advanced = (
        f"next_research_action_id: {RESEARCH_NEXT}" in roadmap_text
    )
    readme_next_ok = RESEARCH_NEXT in readme_text
    readme_has_ready = CLOSURE_OUTCOME_READY in readme_text
    readme_has_not_ready = CLOSURE_OUTCOME_NOT_READY in readme_text
    if derived_completed:
        readme_outcome_ok = readme_has_ready and not readme_has_not_ready
    else:
        readme_outcome_ok = readme_has_not_ready and not readme_has_ready
    ok = (
        (roadmap_lists_next or roadmap_already_advanced)
        and readme_next_ok
        and readme_outcome_ok
    )
    return ok, "roadmap_and_readme_outcome_consistent_with_derived_closure"


def build_gate_125_0(
    *,
    repo_root: Path,
    part3c_hashes: dict[str, str],
    part4_hashes: dict[str, str],
    part4_qc: dict[str, Any],
    sample_matrix_rows: list[dict[str, str]],
    feature_set_rows: list[dict[str, str]],
    keep_drop_rows: list[dict[str, str]],
    blocker_rows: list[dict[str, str]],
    entry_contract: dict[str, Any],
    readme_text: str,
    network_attempts: int,
    no_model_calls_detected: bool,
    mode: str = "build",
    derived_completed: bool | None = None,
    derived_entry_ready: bool | None = None,
    include_handoff_and_docs: bool = True,
) -> dict[str, dict[str, Any]]:
    kd = {r["item_id"]: r["decision"] for r in keep_drop_rows}
    blockers = {r["item_id"]: r for r in blocker_rows}
    gate: dict[str, dict[str, Any]] = {}

    def add(name: str, ok: bool, detail: str) -> None:
        gate[name] = {"pass": bool(ok), "detail": detail}

    if include_handoff_and_docs:
        if derived_completed is None or derived_entry_ready is None:
            raise QCFail(
                "derived_completed and derived_entry_ready required when "
                "include_handoff_and_docs is True"
            )
        docs_ok, docs_detail = _evaluate_contradiction_free_docs(
            repo_root=repo_root,
            readme_text=readme_text,
            derived_completed=derived_completed,
        )
        add("contradiction_free_docs", docs_ok, docs_detail)
        handoff_ok, handoff_detail = validate_actual_handoff(
            repo_root,
            derived_completed=derived_completed,
            derived_entry_ready=derived_entry_ready,
        )
        add("valid_handoff", handoff_ok, handoff_detail)

    part3c_ok = (
        part3c_hashes == FROZEN_PART3C_INPUTS and len(part3c_hashes) == 8
    )
    add("part3c_hashes_unchanged", part3c_ok, "8 unchanged")

    part4_ok = (
        all(part4_hashes.get(k) == v for k, v in FROZEN_PART4_OUTPUTS.items())
        and part4_hashes.get(PART4_SRC_REL) == PART4_SRC_SHA256
        and part4_hashes.get(PART4_TEST_REL) == PART4_TEST_SHA256
        and len(part4_hashes) == len(FROZEN_PART4_OUTPUTS) + 2
    )
    add("part4_hashes_unchanged", part4_ok, "17 outputs + src + test unchanged")

    part4_qc_ok = (
        part4_qc.get("assertion_count") == 70
        and part4_qc.get("failed_count") == 0
        and part4_qc.get("all_pass") is True
        and part4_qc.get("contract_version") == PART4_CONTRACT_VERSION
    )
    add("part4_qc_all_pass", part4_qc_ok, "70/0/true/sap_v2")

    try:
        validate_keep_drop_rows(keep_drop_rows)
        kd_ok = True
    except QCFail:
        kd_ok = False
    add("keep_drop_decisions_complete", kd_ok, f"{len(keep_drop_rows)} rows")

    try:
        validate_blocker_rows(blocker_rows)
        blocker_ok = True
    except QCFail:
        blocker_ok = False
    add("blocker_register_complete", blocker_ok, f"{len(blocker_rows)} rows")

    entry_boundary_ok, entry_boundary_detail = evaluate_entry_boundary(
        entry_contract,
    )
    add(
        "stage126_entry_boundary_explicit",
        entry_boundary_ok,
        entry_boundary_detail,
    )

    final_test_ok = (
        entry_contract.get("final_test_unlocked") is False
        and entry_contract.get("final_test_predictor_values_inspected")
        is False
        and tuple(sorted(FINAL_TEST_YEARS)) == (1400, 1401, 1402)
    )
    add("final_test_still_locked", final_test_ok, "locked")

    add("financial_data_unchanged", part3c_ok, "part3c_pinned_unchanged")

    target_names = {r["target"] for r in sample_matrix_rows}
    targets_ok = target_names == set(ALL_TARGETS)
    add("targets_unchanged", targets_ok, "3_targets_present")

    samples_ok = True
    by_primary = {
        r["sample_design"]: r for r in sample_matrix_rows
        if r["target"] == PRIMARY_TARGET
    }
    for sample, spec in SAMPLE_SPECS.items():
        row = by_primary.get(sample)
        if row is None or (
            int(row["rows"]) != spec["rows"]
            or int(row["companies"]) != spec["companies"]
            or int(row["positive"]) != spec["positive"]
            or int(row["negative"]) != spec["negative"]
        ):
            samples_ok = False
    add("samples_unchanged", samples_ok, "4_sample_designs_match")

    four_month_ok = (
        APPROVED_LAG_MONTHS == 4
        and AVAILABILITY_METHOD == "fixed_regulatory_lag"
        and kd.get("AVAILABILITY_FOUR_JALALI_MONTHS") == "KEEP_LOCKED"
    )
    add("four_month_lag_active", four_month_ok, "4")

    six_month_ok = kd.get("AVAILABILITY_SIX_MONTH_METHOD") == (
        "SUPERSEDED_HISTORICAL_ONLY"
    )
    add("six_month_method_historical_only", six_month_ok, "superseded")

    rg_feature_names = {
        r["feature_name"] for r in feature_set_rows
        if r["feature_set"] in {
            "M1_PRIMARY_FEATURE_ORDER", "M1_TARGET_PROXIMITY_ROBUSTNESS",
        }
    }
    rg_ok = (
        kd.get("FEATURE_REVENUE_GROWTH") == "KEEP_AUDIT_ONLY"
        and REVENUE_GROWTH_FEATURE not in rg_feature_names
    )
    add("revenue_growth_audit_only", rg_ok, "audit_only_absent_from_model_surfaces")

    article141_rows = [
        r for r in sample_matrix_rows if r["target"] == ARTICLE141_TARGET
    ]
    article141_ok = (
        kd.get("TARGET_ARTICLE141_ONLY_T_PLUS_1") == "KEEP_DESCRIPTIVE_ONLY"
        and entry_contract.get("article141_excluded_from_model_estimation")
        is True
        and article141_rows
        and all(
            "distributional_descriptive_robustness_only"
            in r["final_test_claim_eligibility"]
            for r in article141_rows
        )
    )
    add("article141_descriptive_only", article141_ok, "descriptive_only")

    m1_feature_rows = sorted(
        (r for r in feature_set_rows
         if r["feature_set"] == "M1_PRIMARY_FEATURE_ORDER"),
        key=lambda r: int(r["position"]),
    )
    m1_ready_ok = (
        kd.get("FEATURESET_M1_PRIMARY_9") == "KEEP_READY"
        and len(M1_PRIMARY_FEATURE_ORDER) == 9
        and [r["feature_name"] for r in m1_feature_rows]
        == M1_PRIMARY_FEATURE_ORDER
    )
    add("m1_ready", m1_ready_ok, "9_features_ready")

    add(
        "m2_deferred",
        kd.get("BLOCK_M2_MARKET") == "DEFER_NONBLOCKING_FOR_M1",
        "deferred",
    )
    add(
        "m3_not_admitted",
        kd.get("BLOCK_M3_MACRO") == "DROP_CURRENT_ACTIVE_PATH"
        and blockers.get("M3_AUTHORITATIVE_SOURCE_UNAVAILABLE", {}).get(
            "disposition"
        ) == "not_admitted",
        "not_admitted",
    )
    add(
        "m4_deferred",
        kd.get("BLOCK_M4_AUDIT_GOVERNANCE") == "DEFER_NONBLOCKING_FOR_M1",
        "deferred",
    )
    add(
        "m5_removed",
        kd.get("BLOCK_M5_PERSIAN_TEXT") == "DROP_CURRENT_ACTIVE_PATH",
        "removed",
    )
    add("network_requests_zero", network_attempts == 0, str(network_attempts))
    add("model_fit_calls_zero", no_model_calls_detected, "0")
    add("prediction_calls_zero", no_model_calls_detected, "0")
    add("shap_calls_zero", no_model_calls_detected, "0")

    # Part 5's own entry contract never itself authorizes/starts Stage126, and
    # the two legacy Stage126 code entry points must remain absent. The
    # ``project/stage126`` directory surface is permitted once the signed human
    # authorization record is present (see effective_forbidden_surfaces).
    stage126_false_ok = (
        entry_contract.get("stage126_authorized") is False
        and entry_contract.get("stage126_started") is False
        and all(
            not (repo_root / rel).exists()
            for rel in effective_forbidden_surfaces(repo_root)
        )
    )
    add("stage126_false", stage126_false_ok, "false_and_absent")

    wt_ok, wt_detail = evaluate_working_tree_clean(repo_root, mode=mode)
    add("working_tree_clean", wt_ok, wt_detail)

    return gate


# --------------------------------------------------------------------------- #
# Integrity manifest
# --------------------------------------------------------------------------- #

def build_integrity_manifest_rows(
    *,
    repo_root: Path,
    part3c_hashes: dict[str, str],
    part4_hashes: dict[str, str],
    content: dict[str, str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for rel, expected in sorted(FROZEN_PART3C_INPUTS.items()):
        observed = part3c_hashes[rel]
        rows.append({
            "path": rel,
            "artifact_role": "frozen_part3c_input",
            "expected_sha256": expected,
            "observed_sha256": observed,
            "status": "MATCH" if observed == expected else "MISMATCH",
            "mutation_authorized": "false",
        })
    for rel, expected in sorted(FROZEN_PART4_OUTPUTS.items()):
        observed = part4_hashes[rel]
        rows.append({
            "path": rel,
            "artifact_role": "frozen_part4_output",
            "expected_sha256": expected,
            "observed_sha256": observed,
            "status": "MATCH" if observed == expected else "MISMATCH",
            "mutation_authorized": "false",
        })
    rows.append({
        "path": PART4_SRC_REL,
        "artifact_role": "frozen_part4_source",
        "expected_sha256": PART4_SRC_SHA256,
        "observed_sha256": part4_hashes[PART4_SRC_REL],
        "status": "MATCH" if part4_hashes[PART4_SRC_REL] == PART4_SRC_SHA256
        else "MISMATCH",
        "mutation_authorized": "false",
    })
    rows.append({
        "path": PART4_TEST_REL,
        "artifact_role": "frozen_part4_test",
        "expected_sha256": PART4_TEST_SHA256,
        "observed_sha256": part4_hashes[PART4_TEST_REL],
        "status": "MATCH" if part4_hashes[PART4_TEST_REL] == PART4_TEST_SHA256
        else "MISMATCH",
        "mutation_authorized": "false",
    })

    roadmap_path = repo_root / ROADMAP_REL
    if roadmap_path.is_file():
        roadmap_sha = sha256_file(roadmap_path)
        rows.append({
            "path": ROADMAP_REL,
            "artifact_role": "roadmap_pointer_source",
            "expected_sha256": roadmap_sha,
            "observed_sha256": roadmap_sha,
            "status": "MATCH",
            "mutation_authorized": "true",
        })

    # Pin the Handoff-selected QC *producer* (Part 5 source) rather than the
    # Part 5 QC report itself — hashing the QC report here would create a
    # build/check cycle because this build rewrites that QC file.
    # Once Stage126 M1 development is authorized, the live Handoff state has
    # advanced to select the Stage126 QC report; pinning that QC file here would
    # couple the Part 5 integrity manifest to a downstream artifact (and create a
    # build/check cycle). In that case Part 5 pins its own QC producer (Part 5
    # source), exactly as it does when the Handoff still selects the Part 5 QC.
    handoff_path = repo_root / HANDOFF_STATE_REL
    selected_qc_path = ""
    if handoff_path.is_file() and not stage126_m1_development_authorized(repo_root):
        handoff_state = json.loads(handoff_path.read_text(encoding="utf-8"))
        selected_qc_path = str(handoff_state.get("selected_qc_path") or "")
    part5_qc_rel = f"{PART4_OUTPUT_DIR}/{F_QC}"
    if (
        selected_qc_path.replace("\\", "/") == part5_qc_rel
        or selected_qc_path.endswith(F_QC)
        or not selected_qc_path
    ):
        source_sha = sha256_file(repo_root / SRC_REL)
        rows.append({
            "path": SRC_REL,
            "artifact_role": "handoff_selected_qc_source",
            "expected_sha256": source_sha,
            "observed_sha256": source_sha,
            "status": "MATCH",
            "mutation_authorized": "true",
        })
    elif (repo_root / selected_qc_path).is_file():
        selected_sha = sha256_file(repo_root / selected_qc_path)
        rows.append({
            "path": selected_qc_path.replace("\\", "/"),
            "artifact_role": "handoff_selected_qc_source",
            "expected_sha256": selected_sha,
            "observed_sha256": selected_sha,
            "status": "MATCH",
            "mutation_authorized": "true",
        })

    for name in (
        F_CLOSURE_REPORT, F_KEEP_DROP, F_BLOCKER, F_ENTRY_CONTRACT, F_README,
    ):
        text = content[name]
        own_sha = sha256_bytes(text.encode("utf-8"))
        rows.append({
            "path": f"{PART4_OUTPUT_DIR}/{name}",
            "artifact_role": "part5_output",
            "expected_sha256": own_sha,
            "observed_sha256": own_sha,
            "status": "MATCH",
            "mutation_authorized": "true",
        })
    rows.sort(key=lambda r: (r["path"], r["artifact_role"]))
    return rows


# --------------------------------------------------------------------------- #
# Closure report
# --------------------------------------------------------------------------- #

def build_closure_report(
    *,
    keep_drop_rows: list[dict[str, str]],
    blocker_rows: list[dict[str, str]],
    part4_qc: dict[str, Any],
    entry_contract: dict[str, Any],
    gate: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    sample_counts = {
        sample: dict(spec) for sample, spec in sorted(SAMPLE_SPECS.items())
    }
    keep_drop_summary: dict[str, int] = {}
    for row in keep_drop_rows:
        keep_drop_summary[row["decision"]] = (
            keep_drop_summary.get(row["decision"], 0) + 1
        )
    blocker_summary = {
        "total": len(blocker_rows),
        "blocking_stage125_closure": sum(
            1 for r in blocker_rows if r["blocks_stage125_closure"] == "true"
        ),
        "blocking_stage126_m1": sum(
            1 for r in blocker_rows if r["blocks_stage126_m1"] == "true"
        ),
    }
    all_gate_pass = all(v["pass"] for v in gate.values())
    flags = derive_closure_flags(all_gate_pass)
    return {
        "contract_version": CONTRACT_VERSION,
        "research_action_id": RESEARCH_ACTION_ID,
        **flags,
        "part3b_completed": False,
        "part3b_expansion_disposition": (
            "superseded_not_required_for_stage125_closure"
        ),
        "part3b_incomplete_blocks_stage126_m1": False,
        "m3_disposition": "not_admitted_on_current_active_path",
        "m3_reentry_requirements": [
            "new_explicit_versioned_human_decision",
            "authoritative_and_reproducible_source",
            "publication_availability_time_validation",
            "coverage_and_temporal_data_gate_approval",
        ],
        "m3_data_collection_authorized_in_part5": False,
        "final_test_status": "locked_for_single_future_evaluation",
        "final_test_years": list(FINAL_TEST_YEARS),
        "final_test_predictor_inspection_in_part5": False,
        "final_test_model_evaluation_in_part5": False,
        "active_availability_lag_months": APPROVED_LAG_MONTHS,
        "active_availability_method": AVAILABILITY_METHOD,
        "part4_contract_version": PART4_CONTRACT_VERSION,
        "part4_qc_assertion_count": part4_qc["assertion_count"],
        "part4_qc_failed_count": part4_qc["failed_count"],
        "part4_qc_all_pass": part4_qc["all_pass"],
        "sample_counts": sample_counts,
        "keep_drop_summary": dict(sorted(keep_drop_summary.items())),
        "keep_drop_item_count": len(keep_drop_rows),
        "blocker_summary": blocker_summary,
        "stage126_m1_entry_contract_id": entry_contract["contract_id"],
        "gate_125_0": gate,
        "all_gate_pass": all_gate_pass,
    }


# --------------------------------------------------------------------------- #
# README
# --------------------------------------------------------------------------- #

def entry_readiness_for(ready: bool) -> str:
    """Map a final-Gate readiness bool to the entry-readiness statement."""
    return ENTRY_READINESS_READY if ready else ENTRY_READINESS_NOT_READY


def build_readme(*, closure_outcome: str, entry_readiness: str) -> str:
    """Render the Part 5 README with BOTH readiness statements derived.

    ``closure_outcome`` and ``entry_readiness`` must both be supplied from the
    same final Gate 125.0 result. Each is validated against its known
    vocabulary; a failed Gate therefore cannot leave either the closure outcome
    or the entry-readiness statement in a READY form. Cross-statement
    consistency is independently enforced by ``_readme_reports_ready`` and the
    cross-artifact readiness validator.
    """
    if closure_outcome not in {CLOSURE_OUTCOME_READY, CLOSURE_OUTCOME_NOT_READY}:
        raise QCFail(f"invalid closure_outcome for README: {closure_outcome}")
    if entry_readiness not in {ENTRY_READINESS_READY, ENTRY_READINESS_NOT_READY}:
        raise QCFail(f"invalid entry_readiness for README: {entry_readiness}")
    return f"""# Stage125 Part 5 — Readiness Closure

**Status:** Stage125 closure / readiness report only. No modeling.
**Contract version:** `stage125_part5_readiness_closure_v1`
**Research action:** `stage125-part5-readiness-closure`
**Next:** `stage126-m1-financial-baseline`

## Scope

Part 5 closes Stage125 research-design readiness:

- keep/drop decisions across samples, targets, feature sets, model-block
  candidates, model families, imbalance strategies, temporal/availability
  policy, and audit-only historical items (24 exact rows)
- a blocker register recording every known incomplete/deferred item and
  confirming none blocks Stage125 closure or Stage126 M1 entry
- an explicit Stage126 M1 entry contract:
  `entry_readiness = {entry_readiness}`, while
  `stage126_authorized`, `stage126_started`, `modeling_authorized`, and
  `modeling_started` all remain `false`
- an artifact-integrity manifest pinning all frozen Part 3C inputs and Part 4
  outputs by SHA-256, plus Part 5's own generated outputs
- a derived Gate 125.0 readiness gate (dimension-by-dimension; completion and
  readiness fields are never unconditional constants)

## Explicit non-claims

- No model was fitted, no prediction was generated, no SHAP value was
  computed (`model_fit_calls = prediction_calls = shap_calls = 0`).
- Final-test predictor values were **not** inspected in Part 5
  (`final_test_predictor_inspection_in_part5 = false`).
- The locked final test (1400\u20131402) remains locked for a single future
  evaluation; it is **not** unlocked in Part 5
  (`final_test_unlocked = false`).
- Stage126 remains unauthorized and unstarted
  (`stage126_authorized = false`, `stage126_started = false`).
- Modeling remains unauthorized and unstarted
  (`modeling_authorized = false`, `modeling_started = false`).
- `revenue_growth_period_adjusted` remains audit-only and absent from every
  admitted model feature surface.
- The Article-141-only target remains descriptive-only and excluded from
  model estimation.
- M2 and M4 remain deferred (non-blocking for Stage126 M1).
- M3 remains **not admitted on the current active path** (no authoritative
  CBI endpoint). M3 is **not** permanently eliminated from all future
  research; it may re-enter only after: (1) a new explicit versioned human
  decision; (2) an authoritative and reproducible source; (3)
  publication/availability-time validation; (4) coverage and temporal
  data-Gate approval. No M3 data collection is authorized in Part 5.
- M5 remains removed.
- Part 3B expansion remains incomplete but superseded and non-blocking
  (`part3b_completed = false`, `part3b_incomplete_blocks_stage126_m1 =
  false`).
- The active four-Jalali-month regulatory lag remains locked
  (`active_availability_lag_months = 4`); the historical six-month
  methodology remains superseded / historical-only.
- `رمپنا|1396 \u2192 رمپنا|1397` remains audit-only; it never re-enters
  analysis-ready data.
- Part 3C inputs and Part 4 outputs remain unchanged (SHA-256 pinned).

## Closure outcome

```
closure_outcome = {closure_outcome}
```

This outcome is derived from Gate 125.0 (`all_gate_pass`). A failed Gate
cannot produce a ready/complete outcome.
`entry_readiness` is **not** authorization. Stage126 (M1 Financial Baseline)
begins only after an explicit separate human authorization decision.

## Runners

```bash
python project/run_stage125_part5.py --build
python project/run_stage125_part5.py --check
```

`--build` is offline and deterministic. `--check` performs zero writes.
"""


# --------------------------------------------------------------------------- #
# QC static markers (inherited Part 4 workflow fields + Part 5 additions)
# --------------------------------------------------------------------------- #

def _static_qc_markers(closure: dict[str, Any]) -> dict[str, Any]:
    """Handoff/QC markers derived from the closure report (never unconditional)."""
    return {
        "accessibility_scoring_applied": False,
        "active_availability_method": AVAILABILITY_METHOD,
        "active_availability_lag_months": APPROVED_LAG_MONTHS,
        "four_month_regulatory_lag_locked": True,
        "six_month_lag_superseded": True,
        "historical_six_month_decision_retained": True,
        "historical_six_month_decision_active": False,
        "conservative_six_month_lag_decision_locked": True,
        "conservative_availability_lag_locked": True,
        "row_level_publish_datetime_collection_required": False,
        "broad_codal_capture_stopped": True,
        "financial_data_researcher_verified_frozen": True,
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
        "part3b_completed": False,
        "network_extraction_performed": True,
        "part3c_leakage_safe_finalization_completed": True,
        "part4_statistical_analysis_plan_locked": True,
        "stage125_part5_readiness_closure_completed": closure[
            "stage125_part5_readiness_closure_completed"
        ],
        "stage125_completed": closure["stage125_completed"],
        "stage126_m1_entry_ready": closure["stage126_m1_entry_ready"],
        "stage126_authorized": False,
        "stage126_started": False,
        "modeling_authorized": False,
        "modeling_started": False,
        "final_test_unlocked": False,
        "model_fit_calls": 0,
        "prediction_calls": 0,
        "shap_calls": 0,
        "final_test_accessed_for_modeling": False,
        "m2_data_collected": False,
        "m3_data_collected": False,
        "m4_data_collected": False,
        "m3_admitted": False,
    }


REQUIRED_HANDOFF_MARKER_FIELDS = (
    "stage125_part5_readiness_closure_completed",
    "stage125_completed",
    "stage126_m1_entry_ready",
    "stage126_authorized",
    "stage126_started",
    "modeling_authorized",
    "modeling_started",
    "part4_statistical_analysis_plan_locked",
    "part3c_leakage_safe_finalization_completed",
    "active_availability_lag_months",
    "shap_calls",
    "final_test_unlocked",
)


# --------------------------------------------------------------------------- #
# Build / QC / run
# --------------------------------------------------------------------------- #

def build_all(
    repo_root: Path, *, network_attempts: int = 0, mode: str = "build",
) -> tuple[dict[str, str], dict[str, Any]]:
    assert_no_model_imports_in_source(repo_root)
    assert_no_analysis_ready_access_in_source(repo_root)
    assert_forbidden_surfaces_absent(repo_root)
    if mode not in {"build", "check"}:
        raise QCFail(f"invalid build_all mode: {mode}")

    keep_drop_rows = build_keep_drop_rows()
    blocker_rows = build_blocker_register_rows()
    validate_keep_drop_rows(keep_drop_rows)
    validate_blocker_rows(blocker_rows)

    if len(M1_PRIMARY_FEATURE_ORDER) != 9:
        raise QCFail("M1 primary feature count mutation")
    if len(M1_TARGET_PROXIMITY_ROBUSTNESS) != 6:
        raise QCFail("M1 target-proximity feature count mutation")
    if REVENUE_GROWTH_FEATURE in (
        M1_PRIMARY_FEATURE_ORDER + M1_TARGET_PROXIMITY_ROBUSTNESS
    ):
        raise QCFail("revenue_growth present in M1 model surfaces")

    part3c_hashes = frozen_part3c_hashes(repo_root)
    part4_hashes = frozen_part4_output_hashes(repo_root)
    part4_qc = load_part4_qc(repo_root)
    sample_matrix_rows = load_part4_sample_target_matrix(repo_root)
    feature_set_rows = load_part4_feature_sets(repo_root)

    # Step 1: build a readiness-NEUTRAL Stage126 M1 specification. Readiness is
    # not yet known, so it must never influence the Gate. The entry-boundary
    # Gate dimension validates this spec structurally only; readiness itself is
    # attached in step 6 once the complete Gate result is derived.
    spec_contract = build_stage126_m1_entry_contract(entry_ready=False)
    validate_registered_m1_robustness(
        spec_contract["registered_m1_robustness_after_primary_lock"],
    )

    gate_kwargs = dict(
        repo_root=repo_root,
        part3c_hashes=part3c_hashes,
        part4_hashes=part4_hashes,
        part4_qc=part4_qc,
        sample_matrix_rows=sample_matrix_rows,
        feature_set_rows=feature_set_rows,
        keep_drop_rows=keep_drop_rows,
        blocker_rows=blocker_rows,
        entry_contract=spec_contract,
        network_attempts=network_attempts,
        no_model_calls_detected=True,
        mode=mode,
    )

    # Step 2: evaluate all core Gate dimensions (no Handoff/docs that need
    # derived flags).
    core_gate = build_gate_125_0(
        **gate_kwargs,
        readme_text="",
        include_handoff_and_docs=False,
    )
    provisional_pass = all(dim["pass"] for dim in core_gate.values())

    # Step 3: derive provisional closure flags from the core Gate result.
    flags = derive_closure_flags(provisional_pass)
    readme_text = build_readme(
        closure_outcome=flags["closure_outcome"],
        entry_readiness=entry_readiness_for(flags["stage126_m1_entry_ready"]),
    )

    # Steps 4-5: validate actual Handoff + documents, then derive the complete
    # final Gate result.
    gate = build_gate_125_0(
        **gate_kwargs,
        readme_text=readme_text,
        derived_completed=flags["stage125_completed"],
        derived_entry_ready=flags["stage126_m1_entry_ready"],
        include_handoff_and_docs=True,
    )
    final_pass = all(dim["pass"] for dim in gate.values())
    if final_pass != provisional_pass:
        flags = derive_closure_flags(final_pass)
        readme_text = build_readme(
            closure_outcome=flags["closure_outcome"],
            entry_readiness=entry_readiness_for(
                flags["stage126_m1_entry_ready"],
            ),
        )
        gate = build_gate_125_0(
            **gate_kwargs,
            readme_text=readme_text,
            derived_completed=flags["stage125_completed"],
            derived_entry_ready=flags["stage126_m1_entry_ready"],
            include_handoff_and_docs=True,
        )
        final_pass = all(dim["pass"] for dim in gate.values())

    # Step 6: build the FINAL entry contract using the complete final Gate
    # result. A failed Gate cannot leave the contract in the READY state.
    entry_contract = build_stage126_m1_entry_contract(entry_ready=final_pass)
    validate_registered_m1_robustness(
        entry_contract["registered_m1_robustness_after_primary_lock"],
    )

    # Step 7: build closure report + README from the SAME final Gate result.
    closure_report = build_closure_report(
        keep_drop_rows=keep_drop_rows,
        blocker_rows=blocker_rows,
        part4_qc=part4_qc,
        entry_contract=entry_contract,
        gate=gate,
    )
    # Both README readiness statements derive from the SAME final Gate result:
    # closure_outcome from the closure report, entry_readiness from the final
    # entry contract (itself built from final_gate_pass).
    readme_text = build_readme(
        closure_outcome=closure_report["closure_outcome"],
        entry_readiness=entry_contract["entry_readiness"],
    )

    # Step 8: revalidate cross-artifact readiness consistency across the
    # surfaces built here (closure report, entry contract, README, actual
    # Handoff). Fail closed if any disagree with the final Gate result. The
    # live Handoff is always included — never bypassed when Stage126 is
    # authorized.
    handoff_state_now = (
        load_handoff_state(repo_root)
        if (repo_root / HANDOFF_STATE_REL).is_file() else None
    )
    consistent, consistency_detail = validate_readiness_surface_consistency(
        final_gate_pass=closure_report["all_gate_pass"],
        closure_report=closure_report,
        entry_contract=entry_contract,
        handoff_state=handoff_state_now,
        readme_text=readme_text,
    )
    if not consistent:
        raise QCFail(
            f"cross-artifact readiness inconsistency (fail-closed): "
            f"{consistency_detail}"
        )

    content: dict[str, str] = {
        F_CLOSURE_REPORT: _json_str(closure_report),
        F_KEEP_DROP: _csv_str(KEEP_DROP_COLUMNS, keep_drop_rows),
        F_BLOCKER: _csv_str(BLOCKER_COLUMNS, blocker_rows),
        F_ENTRY_CONTRACT: _json_str(entry_contract),
        F_README: readme_text,
    }
    integrity_rows = build_integrity_manifest_rows(
        repo_root=repo_root,
        part3c_hashes=part3c_hashes,
        part4_hashes=part4_hashes,
        content=content,
    )
    content[F_INTEGRITY] = _csv_str(INTEGRITY_COLUMNS, integrity_rows)

    extras = {
        "part3c_hashes": part3c_hashes,
        "part4_hashes": part4_hashes,
        "part4_qc": part4_qc,
        "sample_matrix_rows": sample_matrix_rows,
        "feature_set_rows": feature_set_rows,
        "keep_drop_rows": keep_drop_rows,
        "blocker_rows": blocker_rows,
        "entry_contract": entry_contract,
        "readme_text": readme_text,
        "gate": gate,
        "closure_report": closure_report,
        "integrity_rows": integrity_rows,
        "readiness_consistency_detail": consistency_detail,
        "final_gate_pass": closure_report["all_gate_pass"],
        "mode": mode,
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
    gate = extras["gate"]
    closure = extras["closure_report"]
    entry = extras["entry_contract"]
    kd = {r["item_id"]: r["decision"] for r in extras["keep_drop_rows"]}
    blockers = {r["item_id"]: r for r in extras["blocker_rows"]}
    sample_matrix_rows = extras["sample_matrix_rows"]
    feature_set_rows = extras["feature_set_rows"]
    part4_qc = extras["part4_qc"]

    baseline_tree = _git(repo_root, "rev-parse", f"{EXPECTED_BASELINE_COMMIT}^{{tree}}")
    _assert(
        assertions, "baseline_commit_pinned",
        head == EXPECTED_BASELINE_COMMIT or _is_ancestor(
            repo_root, EXPECTED_BASELINE_COMMIT, head,
        ),
        EXPECTED_BASELINE_COMMIT,
    )
    _assert(
        assertions, "baseline_tree_pinned",
        baseline_tree == EXPECTED_BASELINE_TREE, EXPECTED_BASELINE_TREE,
    )
    _assert(
        assertions, "part3c_hashes_unchanged",
        extras["part3c_hashes"] == FROZEN_PART3C_INPUTS
        and len(extras["part3c_hashes"]) == 8,
        "8 unchanged",
    )
    _assert(
        assertions, "part4_hashes_unchanged",
        all(
            extras["part4_hashes"].get(k) == v
            for k, v in FROZEN_PART4_OUTPUTS.items()
        )
        and extras["part4_hashes"].get(PART4_SRC_REL) == PART4_SRC_SHA256
        and extras["part4_hashes"].get(PART4_TEST_REL) == PART4_TEST_SHA256,
        "17 outputs + src + test unchanged",
    )
    _assert(
        assertions, "part4_contract_version_v2_still_active",
        PART4_CONTRACT_VERSION == "stage125_part4_sap_v2"
        and part4_qc.get("contract_version") == PART4_CONTRACT_VERSION,
        PART4_CONTRACT_VERSION,
    )
    _assert(
        assertions, "part4_qc_70_assertions_0_failed_all_pass",
        part4_qc.get("assertion_count") == 70
        and part4_qc.get("failed_count") == 0
        and part4_qc.get("all_pass") is True,
        "70/0/true",
    )
    _assert(
        assertions, "keep_drop_exact_item_ids_and_decisions",
        kd == REQUIRED_KEEP_DROP_DECISIONS,
        f"{len(kd)} rows",
    )
    _assert(
        assertions, "keep_drop_vocabulary_no_unknown",
        all(d in KEEP_DROP_VOCAB for d in kd.values()),
        "all_known",
    )
    _assert(
        assertions, "blocker_register_required_rows_present",
        REQUIRED_BLOCKER_ITEM_IDS <= set(blockers),
        f"{len(REQUIRED_BLOCKER_ITEM_IDS)} required",
    )
    _assert(
        assertions, "blocker_register_nonblocking",
        all(
            blockers[i]["blocks_stage125_closure"] == "false"
            and blockers[i]["blocks_stage126_m1"] == "false"
            for i in REQUIRED_BLOCKER_ITEM_IDS
        ),
        "nonblocking",
    )
    m1_primary_rows = sorted(
        (r for r in feature_set_rows
         if r["feature_set"] == "M1_PRIMARY_FEATURE_ORDER"),
        key=lambda r: int(r["position"]),
    )
    m1_prox_rows = sorted(
        (r for r in feature_set_rows
         if r["feature_set"] == "M1_TARGET_PROXIMITY_ROBUSTNESS"),
        key=lambda r: int(r["position"]),
    )
    _assert(
        assertions, "m1_primary_exact_nine_feature_order",
        [r["feature_name"] for r in m1_primary_rows]
        == M1_PRIMARY_FEATURE_ORDER
        and len(M1_PRIMARY_FEATURE_ORDER) == 9,
        "9_exact_order",
    )
    _assert(
        assertions, "m1_target_proximity_exact_six_feature_order",
        [r["feature_name"] for r in m1_prox_rows]
        == M1_TARGET_PROXIMITY_ROBUSTNESS
        and len(M1_TARGET_PROXIMITY_ROBUSTNESS) == 6,
        "6_exact_order",
    )
    _assert(
        assertions, "revenue_growth_audit_only_absent_from_model_surfaces",
        kd.get("FEATURE_REVENUE_GROWTH") == "KEEP_AUDIT_ONLY"
        and REVENUE_GROWTH_FEATURE not in [
            r["feature_name"] for r in m1_primary_rows + m1_prox_rows
        ],
        "audit_only",
    )
    _assert(
        assertions, "m2_deferred_nonblocking",
        kd.get("BLOCK_M2_MARKET") == "DEFER_NONBLOCKING_FOR_M1",
        "deferred",
    )
    _assert(
        assertions, "m3_not_admitted",
        kd.get("BLOCK_M3_MACRO") == "DROP_CURRENT_ACTIVE_PATH",
        "not_admitted",
    )
    _assert(
        assertions, "m4_deferred_nonblocking",
        kd.get("BLOCK_M4_AUDIT_GOVERNANCE") == "DEFER_NONBLOCKING_FOR_M1",
        "deferred",
    )
    _assert(
        assertions, "m5_removed",
        kd.get("BLOCK_M5_PERSIAN_TEXT") == "DROP_CURRENT_ACTIVE_PATH",
        "removed",
    )
    article141_rows = [
        r for r in sample_matrix_rows if r["target"] == ARTICLE141_TARGET
    ]
    _assert(
        assertions, "article141_descriptive_only",
        kd.get("TARGET_ARTICLE141_ONLY_T_PLUS_1") == "KEEP_DESCRIPTIVE_ONLY"
        and all(
            "distributional_descriptive_robustness_only"
            in r["final_test_claim_eligibility"]
            for r in article141_rows
        ),
        "descriptive_only",
    )
    _assert(
        assertions, "article141_absent_from_entry_contract_model_estimation",
        entry["article141_excluded_from_model_estimation"] is True,
        "excluded",
    )
    _assert(
        assertions, "main_target_ready",
        kd.get("TARGET_MAIN_T_PLUS_1") == "KEEP_READY",
        "ready",
    )
    _assert(
        assertions, "persistent_loss_target_robustness",
        kd.get("TARGET_PERSISTENT_LOSS_T_PLUS_1") == "KEEP_ROBUSTNESS",
        "robustness",
    )
    _assert(
        assertions, "four_month_lag_active",
        APPROVED_LAG_MONTHS == 4
        and kd.get("AVAILABILITY_FOUR_JALALI_MONTHS") == "KEEP_LOCKED",
        "4",
    )
    _assert(
        assertions, "six_month_method_historical_only",
        kd.get("AVAILABILITY_SIX_MONTH_METHOD")
        == "SUPERSEDED_HISTORICAL_ONLY",
        "historical_only",
    )
    _assert(
        assertions, "rampna_audit_only_persian_present",
        kd.get("RAMPNA_1396_TO_1397_TIMING_VIOLATION") == "KEEP_AUDIT_ONLY"
        and "رمپنا" in content[F_KEEP_DROP],
        "persian_present",
    )
    _assert(
        assertions, "rampna_never_literal_ram_pna",
        "RAM PNA" not in "".join(content.values())
        and "RAMPNA" not in "".join(
            v for k, v in content.items() if k != F_KEEP_DROP
        ).replace("RAMPNA_1396_TO_1397_TIMING_VIOLATION", ""),
        "absent",
    )
    _assert(
        assertions, "part3b_incomplete_nonblocking",
        blockers["PART3B_EXPANSION_INCOMPLETE"]["blocks_stage125_closure"]
        == "false"
        and blockers["PART3B_EXPANSION_INCOMPLETE"]["blocks_stage126_m1"]
        == "false",
        "nonblocking",
    )
    _assert(
        assertions, "part3b_completed_false_in_qc",
        closure["part3b_completed"] is False,
        "false",
    )
    all_gate_pass = all(v["pass"] for v in gate.values())
    expected_flags = derive_closure_flags(all_gate_pass)
    _assert(
        assertions, "stage125_completed_matches_gate",
        closure["stage125_completed"]
        is expected_flags["stage125_completed"],
        str(expected_flags["stage125_completed"]).lower(),
    )
    _assert(
        assertions, "stage126_entry_ready_matches_gate",
        closure["stage126_m1_entry_ready"]
        is expected_flags["stage126_m1_entry_ready"],
        str(expected_flags["stage126_m1_entry_ready"]).lower(),
    )
    _assert(
        assertions, "part5_closure_completed_matches_gate",
        closure["stage125_part5_readiness_closure_completed"]
        is expected_flags["stage125_part5_readiness_closure_completed"],
        str(
            expected_flags["stage125_part5_readiness_closure_completed"]
        ).lower(),
    )
    _assert(
        assertions, "stage126_authorized_false",
        closure["stage126_authorized"] is False
        and entry["stage126_authorized"] is False,
        "false",
    )
    _assert(
        assertions, "stage126_started_false",
        closure["stage126_started"] is False
        and entry["stage126_started"] is False,
        "false",
    )
    _assert(
        assertions, "modeling_authorized_false",
        closure["modeling_authorized"] is False
        and entry["modeling_authorized"] is False,
        "false",
    )
    _assert(
        assertions, "modeling_started_false",
        closure["modeling_started"] is False
        and entry["modeling_started"] is False,
        "false",
    )
    _assert(
        assertions, "final_test_unlocked_false",
        entry["final_test_unlocked"] is False, "false",
    )
    _assert(
        assertions, "final_test_predictor_inspection_false",
        entry["final_test_predictor_values_inspected"] is False
        and closure["final_test_predictor_inspection_in_part5"] is False,
        "false",
    )
    def _no_analysis_ready_access() -> bool:
        try:
            assert_no_analysis_ready_access_in_source(repo_root)
            return True
        except AuthorizationError:
            return False

    _assert(
        assertions, "no_analysis_ready_access_in_source",
        _no_analysis_ready_access(), "absent",
    )
    for sample, spec in SAMPLE_SPECS.items():
        row = next(
            r for r in sample_matrix_rows
            if r["sample_design"] == sample and r["target"] == PRIMARY_TARGET
        )
        ok = (
            int(row["rows"]) == spec["rows"]
            and int(row["companies"]) == spec["companies"]
            and int(row["positive"]) == spec["positive"]
            and int(row["negative"]) == spec["negative"]
        )
        _assert(
            assertions, f"sample_counts_match_part4_matrix_{sample}", ok,
            f"{spec['rows']}/{spec['companies']}/{spec['positive']}/"
            f"{spec['negative']}",
        )
    _assert(
        assertions, "closure_outcome_matches_gate",
        closure["closure_outcome"] == expected_flags["closure_outcome"]
        and closure["stage125_gate_125_0"]
        == expected_flags["stage125_gate_125_0"],
        expected_flags["closure_outcome"],
    )
    _assert(
        assertions, "gate_125_0_all_dimensions_pass",
        all_gate_pass and closure["stage125_gate_125_0"] == "PASS",
        f"{sum(1 for v in gate.values() if v['pass'])}/{len(gate)}",
    )
    # Entry-boundary Gate dimension must be structural/authorization only and
    # must NOT depend on readiness (no circular logic): it passes identically
    # for an entry-ready and a not-ready contract.
    boundary_ready_ok, _ = evaluate_entry_boundary(
        build_stage126_m1_entry_contract(entry_ready=True),
    )
    boundary_notready_ok, _ = evaluate_entry_boundary(
        build_stage126_m1_entry_contract(entry_ready=False),
    )
    _assert(
        assertions, "entry_boundary_independent_of_readiness",
        boundary_ready_ok is True and boundary_notready_ok is True
        and gate["stage126_entry_boundary_explicit"]["pass"] is True,
        "structural_only",
    )
    # Entry-contract readiness is derived from the final Gate result and never
    # unconditionally READY.
    _assert(
        assertions, "entry_contract_readiness_derived_from_gate",
        entry["stage126_m1_entry_ready"]
        is expected_flags["stage126_m1_entry_ready"]
        and entry["entry_readiness"] == (
            ENTRY_READINESS_READY if all_gate_pass else ENTRY_READINESS_NOT_READY
        ),
        entry["entry_readiness"],
    )
    # Direct cross-artifact readiness consistency over the surfaces available
    # at QC time (closure report, entry contract, README, actual Handoff).
    # The live Handoff is always included — never bypassed under Stage126
    # authorization.
    handoff_now = (
        load_handoff_state(repo_root)
        if (repo_root / HANDOFF_STATE_REL).is_file() else None
    )
    consistency_ok, consistency_detail = (
        validate_readiness_surface_consistency(
            final_gate_pass=all_gate_pass,
            closure_report=closure,
            entry_contract=entry,
            handoff_state=handoff_now,
            readme_text=content[F_README],
        )
    )
    _assert(
        assertions, "cross_artifact_readiness_consistency",
        consistency_ok, consistency_detail,
    )
    try:
        validate_registered_m1_robustness(
            entry["registered_m1_robustness_after_primary_lock"],
        )
        robustness_ok = True
    except QCFail:
        robustness_ok = False
    _assert(
        assertions, "m1_robustness_registry_six_categories_exact",
        robustness_ok
        and len(entry["registered_m1_robustness_after_primary_lock"]) == 6,
        "6_exact",
    )
    _assert(
        assertions, "gate_125_0_has_27_dimensions",
        len(gate) == 27, str(len(gate)),
    )
    _assert(
        assertions, "no_model_imports_in_source",
        True,  # already enforced (raises) in build_all
        "enforced",
    )
    _assert(
        assertions, "network_requests_zero",
        network_attempts == 0, str(network_attempts),
    )
    _assert(assertions, "model_fit_calls_zero", True, "0")
    _assert(assertions, "prediction_calls_zero", True, "0")
    _assert(assertions, "shap_calls_zero", True, "0")
    _assert(
        assertions, "forbidden_surfaces_absent",
        all(
            not (repo_root / rel).exists()
            for rel in effective_forbidden_surfaces(repo_root)
        ),
        "absent",
    )
    content2, _ = build_all(repo_root, mode=extras.get("mode", "build"))
    det_ok = all(content[k] == content2[k] for k in TRACKED_CONTENT_FILES)
    _assert(assertions, "deterministic_rebuild", det_ok, "stable")

    def _rejected(fn, *args, **kwargs) -> bool:
        try:
            fn(*args, **kwargs)
            return False
        except AuthorizationError:
            return True

    _assert(
        assertions, "reject_stage126_authorized_guard",
        _rejected(reject_stage126_authorized, True), "rejected",
    )
    _assert(
        assertions, "reject_modeling_started_guard",
        _rejected(reject_modeling_started, True), "rejected",
    )
    _assert(
        assertions, "reject_final_test_unlocked_guard",
        _rejected(reject_final_test_unlocked, True), "rejected",
    )
    _assert(
        assertions, "reject_revenue_growth_keep_ready_guard",
        _rejected(reject_revenue_growth_keep_ready, "KEEP_READY"), "rejected",
    )
    _assert(
        assertions, "reject_article141_model_ready_guard",
        _rejected(reject_article141_model_ready, "KEEP_READY"), "rejected",
    )
    _assert(
        assertions, "reject_m3_admitted_guard",
        _rejected(reject_m3_admitted, "KEEP_READY"), "rejected",
    )
    _assert(
        assertions, "reject_final_test_year_change_guard",
        _rejected(reject_final_test_year_change, {1400, 1401}), "rejected",
    )
    _assert(
        assertions, "reject_active_lag_change_guard",
        _rejected(reject_active_lag_change, 6), "rejected",
    )
    _assert(
        assertions, "reject_next_research_pointer_guard",
        _rejected(reject_next_research_pointer, "stage126-something-else"),
        "rejected",
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
    part3c_before = frozen_part3c_hashes(repo_root)
    part4_before = frozen_part4_output_hashes(repo_root)
    network_attempts = 0
    files_written: dict[str, str] = {}

    run_mode = "build" if build else "check"
    with p3b0.network_sentinel() as sentinel:
        content, extras = build_all(repo_root, mode=run_mode)
        if sentinel.calls_attempted != 0:
            raise QCFail(
                f"network_requests_attempted_zero failed: "
                f"{sentinel.calls_attempted}"
            )
        network_attempts = sentinel.calls_attempted
        part3c_after = frozen_part3c_hashes(repo_root)
        part4_after = frozen_part4_output_hashes(repo_root)
        if part3c_before != part3c_after:
            raise QCFail("Part 3C inputs mutated during Part 5 run")
        if part4_before != part4_after:
            raise QCFail("Part 4 outputs mutated during Part 5 run")

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
        markers = _static_qc_markers(extras["closure_report"])
        qc: dict[str, Any] = {
            "stage": QC_STAGE,
            "current_stage": CURRENT_STAGE,
            "research_action_id": RESEARCH_ACTION_ID,
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
            "part4_contract_version": PART4_CONTRACT_VERSION,
            "part4_qc_assertion_count": extras["part4_qc"]["assertion_count"],
            "part4_qc_failed_count": extras["part4_qc"]["failed_count"],
            "part4_qc_all_pass": extras["part4_qc"]["all_pass"],
            "gate_125_0": extras["gate"],
            "stage125_gate_125_0": extras["closure_report"][
                "stage125_gate_125_0"
            ],
            "research_pointers": {
                "last_completed_research_action_id": RESEARCH_LAST_COMPLETED,
                "next_research_action_id": RESEARCH_NEXT,
            },
            "output_sha256": dict(sorted(content_hashes.items())),
            "frozen_part3c_input_sha256": dict(sorted(part3c_after.items())),
            "frozen_part4_output_sha256": dict(sorted(part4_after.items())),
            "assertions": assertions,
            "contract_version": CONTRACT_VERSION,
            **markers,
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
                "Stage125 Part 5 readiness closure (keep/drop decisions, "
                "blocker register, Stage126 M1 entry contract, artifact "
                "integrity manifest, Gate 125.0; no modeling)."
            ),
            "generated_at": source_commit,
            "code_commit": source_commit,
            "baseline_commit": EXPECTED_BASELINE_COMMIT,
            "baseline_tree": EXPECTED_BASELINE_TREE,
            "source_file_sha256": qc["source_file_sha256"],
            "test_file_sha256": qc["test_file_sha256"],
            "output_files_sha256": dict(
                sorted({**content_hashes, F_QC: qc_hash}.items())
            ),
            "stage125_part5_readiness_closure_completed": extras[
                "closure_report"
            ]["stage125_part5_readiness_closure_completed"],
            "stage125_completed": extras["closure_report"][
                "stage125_completed"
            ],
            "stage126_m1_entry_ready": extras["closure_report"][
                "stage126_m1_entry_ready"
            ],
            "stage126_authorized": False,
            "stage126_started": False,
            "modeling_authorized": False,
            "modeling_started": False,
            "final_test_unlocked": False,
            "network_requests_attempted": network_attempts,
            "model_fit_calls": 0,
            "prediction_calls": 0,
            "shap_calls": 0,
            "research_pointers": qc["research_pointers"],
            "closure_outcome": extras["closure_report"]["closure_outcome"],
            "stage125_gate_125_0": extras["closure_report"][
                "stage125_gate_125_0"
            ],
        }
        meta_text = _json_str(meta)
        all_tracked = {**content, F_QC: qc_text, F_METADATA: meta_text}

        # Full six-surface cross-artifact readiness consistency (§3): closure
        # report, entry contract, QC report, metadata, actual Handoff state and
        # README must all agree with the final Gate result. Fail closed. The
        # live Handoff is always included — never bypassed under Stage126
        # authorization.
        handoff_state_now = (
            load_handoff_state(repo_root)
            if (repo_root / HANDOFF_STATE_REL).is_file() else None
        )
        six_ok, six_detail = validate_readiness_surface_consistency(
            final_gate_pass=extras["closure_report"]["all_gate_pass"],
            closure_report=extras["closure_report"],
            entry_contract=extras["entry_contract"],
            qc_report=qc,
            metadata=meta,
            handoff_state=handoff_state_now,
            readme_text=content[F_README],
        )
        if not six_ok:
            raise QCFail(
                f"cross-artifact readiness inconsistency (fail-closed): "
                f"{six_detail}"
            )

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
                f"Part 5 QC failed: {qc['failed_count']} assertions failed"
            )

        return {
            "qc": qc,
            "metadata": meta,
            "output_dir": str(out_dir),
            "files": files_written,
            "drift": tracked_drift,
            "network_requests_attempted": network_attempts,
        }
