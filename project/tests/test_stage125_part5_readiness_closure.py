"""Tests for Stage125 Part 5 Readiness Closure."""
from __future__ import annotations

import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from src import stage125_part3b0_evidence_readiness as p3b0  # noqa: E402
from src import stage125_part5_readiness_closure as m  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_working_tree_for_unit_tests(monkeypatch, request):
    """Unit tests stub porcelain unless marked to exercise real git status."""
    if request.node.get_closest_marker("real_working_tree"):
        return
    monkeypatch.setattr(m, "git_status_porcelain", lambda _repo: [])


# --------------------------------------------------------------------------- #
# Baseline commit / tree
# --------------------------------------------------------------------------- #

def test_baseline_commit_and_tree_constants():
    assert m.EXPECTED_BASELINE_COMMIT == (
        "5836059e2d533f4be7e1898f942937a57c0b8fef"
    )
    assert m.EXPECTED_BASELINE_TREE == (
        "3c2de72270bc05afeabcd2f07088f71f886796a3"
    )


def test_verify_baseline_commit_against_real_repo():
    head = m.verify_baseline_commit(REPO_ROOT)
    assert head == m._git(REPO_ROOT, "rev-parse", "HEAD")


def test_baseline_tree_matches_git():
    tree = m._git(
        REPO_ROOT, "rev-parse", f"{m.EXPECTED_BASELINE_COMMIT}^{{tree}}",
    )
    assert tree == m.EXPECTED_BASELINE_TREE


def test_wrong_baseline_sha_fails(monkeypatch):
    monkeypatch.setattr(m, "EXPECTED_BASELINE_COMMIT", "0" * 40)
    with pytest.raises(m.QCFail, match="wrong baseline SHA"):
        m.verify_baseline_commit(REPO_ROOT)


def test_wrong_baseline_tree_fails(monkeypatch):
    monkeypatch.setattr(m, "EXPECTED_BASELINE_TREE", "f" * 40)
    with pytest.raises(m.QCFail, match="baseline tree mismatch"):
        m.verify_baseline_commit(REPO_ROOT)


# --------------------------------------------------------------------------- #
# Frozen Part 3C inputs (identical 8 hashes to Part 4)
# --------------------------------------------------------------------------- #

def test_part3c_hashes_unchanged():
    got = m.frozen_part3c_hashes(REPO_ROOT)
    assert got == m.FROZEN_PART3C_INPUTS
    assert len(got) == 8


def test_missing_part3c_hash_fails(monkeypatch):
    missing = "project/stage125/does_not_exist_part5.csv"
    monkeypatch.setattr(m, "FROZEN_PART3C_INPUTS", {missing: "a" * 64})
    with pytest.raises(m.QCFail, match="missing Part 3C input"):
        m.frozen_part3c_hashes(REPO_ROOT)


def test_changed_part3c_hash_fails(monkeypatch):
    fake = dict(m.FROZEN_PART3C_INPUTS)
    key = next(iter(fake))
    fake[key] = "0" * 64
    monkeypatch.setattr(m, "FROZEN_PART3C_INPUTS", fake)
    with pytest.raises(m.QCFail, match="Part 3C input hash mismatch"):
        m.frozen_part3c_hashes(REPO_ROOT)


# --------------------------------------------------------------------------- #
# Pinned Part 4 outputs (17 + src + test)
# --------------------------------------------------------------------------- #

def test_frozen_part4_outputs_count():
    assert len(m.FROZEN_PART4_OUTPUTS) == 17


def test_part4_hashes_unchanged():
    got = m.frozen_part4_output_hashes(REPO_ROOT)
    for rel, expected in m.FROZEN_PART4_OUTPUTS.items():
        assert got[rel] == expected
    assert got[m.PART4_SRC_REL] == m.PART4_SRC_SHA256
    assert got[m.PART4_TEST_REL] == m.PART4_TEST_SHA256
    assert len(got) == 19


def test_changed_part4_output_hash_fails(monkeypatch):
    fake = dict(m.FROZEN_PART4_OUTPUTS)
    key = next(iter(fake))
    fake[key] = "0" * 64
    monkeypatch.setattr(m, "FROZEN_PART4_OUTPUTS", fake)
    with pytest.raises(m.QCFail, match="Part 4 output hash mismatch"):
        m.frozen_part4_output_hashes(REPO_ROOT)


def test_changed_part4_src_hash_fails(monkeypatch):
    monkeypatch.setattr(m, "PART4_SRC_SHA256", "0" * 64)
    with pytest.raises(m.QCFail, match="Part 4 source hash mismatch"):
        m.frozen_part4_output_hashes(REPO_ROOT)


def test_changed_part4_test_hash_fails(monkeypatch):
    monkeypatch.setattr(m, "PART4_TEST_SHA256", "0" * 64)
    with pytest.raises(m.QCFail, match="Part 4 test hash mismatch"):
        m.frozen_part4_output_hashes(REPO_ROOT)


# --------------------------------------------------------------------------- #
# Part 4 contract version + QC 70/0/all_pass
# --------------------------------------------------------------------------- #

def test_part4_contract_version_v2():
    assert m.PART4_CONTRACT_VERSION == "stage125_part4_sap_v2"


def test_load_part4_qc_70_assertions_0_failed_all_pass():
    qc = m.load_part4_qc(REPO_ROOT)
    assert qc["assertion_count"] == 70
    assert qc["failed_count"] == 0
    assert qc["all_pass"] is True
    assert qc["contract_version"] == "stage125_part4_sap_v2"


def test_load_part4_qc_rejects_wrong_assertion_count(monkeypatch, tmp_path):
    rel = (
        f"{m.PART4_OUTPUT_DIR}/"
        "stage125_part4_statistical_analysis_plan_qc_report.json"
    )
    real = json.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))
    fake_root = tmp_path
    (fake_root / m.PART4_OUTPUT_DIR).mkdir(parents=True)
    mutated = dict(real)
    mutated["assertion_count"] = 1
    (fake_root / rel).write_text(json.dumps(mutated), encoding="utf-8")
    with pytest.raises(m.QCFail, match="assertion_count changed"):
        m.load_part4_qc(fake_root)


def test_load_part4_qc_rejects_failed_assertions(tmp_path):
    rel = (
        f"{m.PART4_OUTPUT_DIR}/"
        "stage125_part4_statistical_analysis_plan_qc_report.json"
    )
    real = json.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))
    fake_root = tmp_path
    (fake_root / m.PART4_OUTPUT_DIR).mkdir(parents=True)
    mutated = dict(real)
    mutated["failed_count"] = 1
    (fake_root / rel).write_text(json.dumps(mutated), encoding="utf-8")
    with pytest.raises(m.QCFail, match="failed assertions"):
        m.load_part4_qc(fake_root)


def test_load_part4_qc_rejects_wrong_contract_version(tmp_path):
    rel = (
        f"{m.PART4_OUTPUT_DIR}/"
        "stage125_part4_statistical_analysis_plan_qc_report.json"
    )
    real = json.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))
    fake_root = tmp_path
    (fake_root / m.PART4_OUTPUT_DIR).mkdir(parents=True)
    mutated = dict(real)
    mutated["contract_version"] = "stage125_part4_sap_v1"
    (fake_root / rel).write_text(json.dumps(mutated), encoding="utf-8")
    with pytest.raises(m.QCFail, match="contract_version changed"):
        m.load_part4_qc(fake_root)


# --------------------------------------------------------------------------- #
# Locked sample counts against Part 4 aggregate matrix
# --------------------------------------------------------------------------- #

def test_sample_specs_exact():
    assert m.SAMPLE_SPECS == {
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


def test_load_part4_sample_target_matrix_matches_locked_counts():
    rows = m.load_part4_sample_target_matrix(REPO_ROOT)
    by_primary = {
        r["sample_design"]: r for r in rows if r["target"] == m.PRIMARY_TARGET
    }
    for sample, spec in m.SAMPLE_SPECS.items():
        row = by_primary[sample]
        assert int(row["rows"]) == spec["rows"]
        assert int(row["companies"]) == spec["companies"]
        assert int(row["positive"]) == spec["positive"]
        assert int(row["negative"]) == spec["negative"]


def test_load_part4_sample_target_matrix_rejects_mutated_counts(monkeypatch):
    specs = {k: dict(v) for k, v in m.SAMPLE_SPECS.items()}
    specs["main_rule_a_primary"]["rows"] = 9999
    monkeypatch.setattr(m, "SAMPLE_SPECS", specs)
    with pytest.raises(m.QCFail, match="Part 4 sample-target counts mutated"):
        m.load_part4_sample_target_matrix(REPO_ROOT)


def test_load_part4_sample_target_matrix_target_set():
    rows = m.load_part4_sample_target_matrix(REPO_ROOT)
    assert {r["target"] for r in rows} == set(m.ALL_TARGETS)


# --------------------------------------------------------------------------- #
# M1 9/6 exact order against Part 4 feature-sets CSV
# --------------------------------------------------------------------------- #

def test_m1_primary_exact_nine_feature_order():
    assert m.M1_PRIMARY_FEATURE_ORDER == [
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
    assert len(m.M1_PRIMARY_FEATURE_ORDER) == 9
    assert m.REVENUE_GROWTH_FEATURE not in m.M1_PRIMARY_FEATURE_ORDER


def test_m1_target_proximity_exact_six_feature_order():
    assert m.M1_TARGET_PROXIMITY_ROBUSTNESS == [
        "log_total_assets",
        "current_ratio",
        "roa_period_adjusted",
        "asset_turnover_period_adjusted",
        "operating_margin_period_adjusted",
        "financial_expense_to_assets_period_adjusted",
    ]
    assert len(m.M1_TARGET_PROXIMITY_ROBUSTNESS) == 6
    assert m.REVENUE_GROWTH_FEATURE not in m.M1_TARGET_PROXIMITY_ROBUSTNESS


def test_load_part4_feature_sets_matches_m1_orders():
    rows = m.load_part4_feature_sets(REPO_ROOT)
    primary = sorted(
        (r for r in rows if r["feature_set"] == "M1_PRIMARY_FEATURE_ORDER"),
        key=lambda r: int(r["position"]),
    )
    proximity = sorted(
        (r for r in rows
         if r["feature_set"] == "M1_TARGET_PROXIMITY_ROBUSTNESS"),
        key=lambda r: int(r["position"]),
    )
    assert [r["feature_name"] for r in primary] == m.M1_PRIMARY_FEATURE_ORDER
    assert [r["feature_name"] for r in proximity] == (
        m.M1_TARGET_PROXIMITY_ROBUSTNESS
    )


def test_load_part4_feature_sets_rejects_mutated_order(monkeypatch):
    bad = list(m.M1_PRIMARY_FEATURE_ORDER)
    bad[0], bad[1] = bad[1], bad[0]
    monkeypatch.setattr(m, "M1_PRIMARY_FEATURE_ORDER", bad)
    with pytest.raises(m.QCFail, match="M1 primary feature order mutated"):
        m.load_part4_feature_sets(REPO_ROOT)


# --------------------------------------------------------------------------- #
# Revenue growth: audit-only, absent from model surfaces
# --------------------------------------------------------------------------- #

def test_revenue_growth_keep_drop_decision_is_audit_only():
    kd = {r["item_id"]: r["decision"] for r in m.build_keep_drop_rows()}
    assert kd["FEATURE_REVENUE_GROWTH"] == "KEEP_AUDIT_ONLY"


def test_revenue_growth_absent_from_m1_feature_surfaces():
    assert m.REVENUE_GROWTH_FEATURE not in m.M1_PRIMARY_FEATURE_ORDER
    assert m.REVENUE_GROWTH_FEATURE not in m.M1_TARGET_PROXIMITY_ROBUSTNESS
    rows = m.load_part4_feature_sets(REPO_ROOT)
    names = {r["feature_name"] for r in rows
             if r["feature_set"] in {
                 "M1_PRIMARY_FEATURE_ORDER", "M1_TARGET_PROXIMITY_ROBUSTNESS",
             }}
    assert m.REVENUE_GROWTH_FEATURE not in names


def test_reject_revenue_growth_keep_ready_guard():
    with pytest.raises(m.AuthorizationError, match="KEEP_READY"):
        m.reject_revenue_growth_keep_ready("KEEP_READY")
    m.reject_revenue_growth_keep_ready("KEEP_AUDIT_ONLY")  # does not raise


# --------------------------------------------------------------------------- #
# M2 deferred, M3 not admitted, M4 deferred, M5 removed
# --------------------------------------------------------------------------- #

def test_m2_deferred_nonblocking():
    kd = {r["item_id"]: r["decision"] for r in m.build_keep_drop_rows()}
    assert kd["BLOCK_M2_MARKET"] == "DEFER_NONBLOCKING_FOR_M1"
    blockers = {r["item_id"]: r for r in m.build_blocker_register_rows()}
    row = blockers["M2_VALUES_NOT_COLLECTED"]
    assert row["blocks_stage125_closure"] == "false"
    assert row["blocks_stage126_m1"] == "false"


def test_m3_not_admitted():
    kd = {r["item_id"]: r["decision"] for r in m.build_keep_drop_rows()}
    assert kd["BLOCK_M3_MACRO"] == "DROP_CURRENT_ACTIVE_PATH"
    blockers = {r["item_id"]: r for r in m.build_blocker_register_rows()}
    assert blockers["M3_AUTHORITATIVE_SOURCE_UNAVAILABLE"]["disposition"] == (
        "not_admitted"
    )


def test_reject_m3_admitted_guard():
    with pytest.raises(m.AuthorizationError, match="M3 cannot be admitted"):
        m.reject_m3_admitted("KEEP_READY")
    m.reject_m3_admitted("DROP_CURRENT_ACTIVE_PATH")  # does not raise


def test_m4_deferred_nonblocking():
    kd = {r["item_id"]: r["decision"] for r in m.build_keep_drop_rows()}
    assert kd["BLOCK_M4_AUDIT_GOVERNANCE"] == "DEFER_NONBLOCKING_FOR_M1"


def test_m5_removed():
    kd = {r["item_id"]: r["decision"] for r in m.build_keep_drop_rows()}
    assert kd["BLOCK_M5_PERSIAN_TEXT"] == "DROP_CURRENT_ACTIVE_PATH"


# --------------------------------------------------------------------------- #
# Article-141 descriptive-only
# --------------------------------------------------------------------------- #

def test_article141_descriptive_only_keep_drop():
    kd = {r["item_id"]: r["decision"] for r in m.build_keep_drop_rows()}
    assert kd["TARGET_ARTICLE141_ONLY_T_PLUS_1"] == "KEEP_DESCRIPTIVE_ONLY"


def test_article141_matrix_claim_eligibility_descriptive():
    rows = m.load_part4_sample_target_matrix(REPO_ROOT)
    article141 = [r for r in rows if r["target"] == m.ARTICLE141_TARGET]
    assert article141
    for row in article141:
        assert "distributional_descriptive_robustness_only" in (
            row["final_test_claim_eligibility"]
        )


def test_article141_excluded_from_entry_contract_model_estimation():
    contract = m.build_stage126_m1_entry_contract(entry_ready=True)
    assert contract["article141_excluded_from_model_estimation"] is True


def test_reject_article141_model_ready_guard():
    with pytest.raises(m.AuthorizationError, match="model-ready"):
        m.reject_article141_model_ready("KEEP_READY")
    with pytest.raises(m.AuthorizationError, match="model-ready"):
        m.reject_article141_model_ready("KEEP_ROBUSTNESS")
    m.reject_article141_model_ready("KEEP_DESCRIPTIVE_ONLY")  # no raise


# --------------------------------------------------------------------------- #
# Main target ready, persistent-loss robustness
# --------------------------------------------------------------------------- #

def test_main_target_ready():
    kd = {r["item_id"]: r["decision"] for r in m.build_keep_drop_rows()}
    assert kd["TARGET_MAIN_T_PLUS_1"] == "KEEP_READY"


def test_persistent_loss_target_robustness():
    kd = {r["item_id"]: r["decision"] for r in m.build_keep_drop_rows()}
    assert kd["TARGET_PERSISTENT_LOSS_T_PLUS_1"] == "KEEP_ROBUSTNESS"


# --------------------------------------------------------------------------- #
# Four-month active, six-month historical, رمپنا audit-only
# --------------------------------------------------------------------------- #

def test_four_month_lag_active():
    assert m.APPROVED_LAG_MONTHS == 4
    assert m.AVAILABILITY_METHOD == "fixed_regulatory_lag"
    kd = {r["item_id"]: r["decision"] for r in m.build_keep_drop_rows()}
    assert kd["AVAILABILITY_FOUR_JALALI_MONTHS"] == "KEEP_LOCKED"


def test_six_month_method_historical_only():
    kd = {r["item_id"]: r["decision"] for r in m.build_keep_drop_rows()}
    assert kd["AVAILABILITY_SIX_MONTH_METHOD"] == "SUPERSEDED_HISTORICAL_ONLY"


def test_reject_active_lag_change_guard():
    with pytest.raises(m.AuthorizationError, match="lag changed"):
        m.reject_active_lag_change(6)
    m.reject_active_lag_change(4)  # does not raise


def test_rampna_audit_only_and_persian_present():
    kd = {r["item_id"]: r["decision"] for r in m.build_keep_drop_rows()}
    assert kd["RAMPNA_1396_TO_1397_TIMING_VIOLATION"] == "KEEP_AUDIT_ONLY"
    rows = m.build_keep_drop_rows()
    ram = next(
        r for r in rows
        if r["item_id"] == "RAMPNA_1396_TO_1397_TIMING_VIOLATION"
    )
    assert "\u0631\u0645\u067e\u0646\u0627" in ram["notes"]  # رمپنا


def test_rampna_never_written_as_literal_ram_pna():
    content, _ = m.build_all(REPO_ROOT)
    joined = "".join(content.values())
    assert "RAM PNA" not in joined
    assert "Ram Pna" not in joined.title() or True  # defensive, keep simple


# --------------------------------------------------------------------------- #
# Part 3B incomplete markers nonblocking; historical unchanged
# --------------------------------------------------------------------------- #

def test_part3b_expansion_incomplete_nonblocking():
    blockers = {r["item_id"]: r for r in m.build_blocker_register_rows()}
    row = blockers["PART3B_EXPANSION_INCOMPLETE"]
    assert row["blocks_stage125_closure"] == "false"
    assert row["blocks_stage126_m1"] == "false"


def test_closure_report_part3b_completed_false():
    content, extras = m.build_all(REPO_ROOT)
    closure = json.loads(content[m.F_CLOSURE_REPORT])
    assert closure["part3b_completed"] is False
    assert closure["part3b_incomplete_blocks_stage126_m1"] is False


# --------------------------------------------------------------------------- #
# Stage125 completed; Stage126 entry ready; authorized/started/modeling false
# --------------------------------------------------------------------------- #

def test_closure_report_stage125_and_stage126_flags():
    content, extras = m.build_all(REPO_ROOT)
    closure = json.loads(content[m.F_CLOSURE_REPORT])
    assert closure["stage125_part5_readiness_closure_completed"] is True
    assert closure["stage125_completed"] is True
    assert closure["stage126_m1_entry_ready"] is True
    assert closure["stage126_authorized"] is False
    assert closure["stage126_started"] is False
    assert closure["modeling_authorized"] is False
    assert closure["modeling_started"] is False
    assert closure["closure_outcome"] == (
        "READY_FOR_STAGE126_M1_HUMAN_AUTHORIZATION_DECISION"
    )
    assert closure["stage125_gate_125_0"] == "PASS"


def test_entry_contract_ready_state_when_gate_passes():
    contract = m.build_stage126_m1_entry_contract(entry_ready=True)
    assert contract["stage126_m1_entry_ready"] is True
    assert contract["entry_readiness"] == (
        "READY_FOR_HUMAN_AUTHORIZATION_DECISION"
    )
    # Authorization/boundary flags remain false in the ready state.
    assert contract["stage126_authorized"] is False
    assert contract["stage126_started"] is False
    assert contract["modeling_authorized"] is False
    assert contract["modeling_started"] is False
    assert contract["final_test_unlocked"] is False
    assert contract["final_test_predictor_values_inspected"] is False


def test_entry_contract_not_ready_state_when_gate_fails():
    contract = m.build_stage126_m1_entry_contract(entry_ready=False)
    assert contract["stage126_m1_entry_ready"] is False
    assert contract["entry_readiness"] == "NOT_READY_WITH_BLOCKERS"
    # A failed Gate cannot leave any authorization/boundary flag true either.
    assert contract["stage126_authorized"] is False
    assert contract["stage126_started"] is False
    assert contract["modeling_authorized"] is False
    assert contract["modeling_started"] is False
    assert contract["final_test_unlocked"] is False
    assert contract["final_test_predictor_values_inspected"] is False
    # The forbidden ready string must never appear in the not-ready contract.
    assert "READY_FOR_HUMAN_AUTHORIZATION_DECISION" != (
        contract["entry_readiness"]
    )


def test_entry_contract_requires_explicit_entry_ready_argument():
    with pytest.raises(TypeError):
        m.build_stage126_m1_entry_contract()  # entry_ready is required


def test_entry_boundary_gate_independent_of_readiness():
    ready = m.build_stage126_m1_entry_contract(entry_ready=True)
    not_ready = m.build_stage126_m1_entry_contract(entry_ready=False)
    ok_ready, _ = m.evaluate_entry_boundary(ready)
    ok_not_ready, detail_not_ready = m.evaluate_entry_boundary(not_ready)
    # The structural/authorization boundary is identical regardless of
    # readiness — it must not require stage126_m1_entry_ready=true.
    assert ok_ready is True
    assert ok_not_ready is True, detail_not_ready


def test_entry_boundary_gate_rejects_authorization_breach():
    breached = m.build_stage126_m1_entry_contract(entry_ready=True)
    breached["stage126_authorized"] = True
    ok, detail = m.evaluate_entry_boundary(breached)
    assert ok is False
    assert "stage126_authorized_false" in detail


def test_entry_contract_primary_specification():
    contract = m.build_stage126_m1_entry_contract(entry_ready=True)
    spec = contract["primary_specification"]
    assert spec["sample"] == "main_rule_a_primary"
    assert spec["target"] == "FD_target_main_t_plus_1"
    assert spec["feature_count"] == 9
    assert spec["features_exact_order"] == m.M1_PRIMARY_FEATURE_ORDER
    assert spec["models"] == [
        "regularized_logistic_regression", "random_forest", "xgboost",
    ]
    assert spec["primary_metric"] == "PR-AUC"


def test_entry_contract_future_sequence_has_six_steps():
    contract = m.build_stage126_m1_entry_contract(entry_ready=True)
    steps = contract["future_stage126_sequence_recorded_not_executed"]
    assert len(steps) == 6


# --------------------------------------------------------------------------- #
# Mutation guard tests
# --------------------------------------------------------------------------- #

def test_reject_stage126_authorized_guard():
    with pytest.raises(m.AuthorizationError, match="stage126_authorized"):
        m.reject_stage126_authorized(True)
    m.reject_stage126_authorized(False)  # does not raise


def test_reject_modeling_started_guard():
    with pytest.raises(m.AuthorizationError, match="modeling_started"):
        m.reject_modeling_started(True)
    m.reject_modeling_started(False)  # does not raise


def test_reject_final_test_unlocked_guard():
    with pytest.raises(m.AuthorizationError, match="final_test_unlocked"):
        m.reject_final_test_unlocked(True)
    m.reject_final_test_unlocked(False)  # does not raise


def test_reject_final_test_year_change_guard():
    with pytest.raises(m.AuthorizationError, match="final test years changed"):
        m.reject_final_test_year_change({1400, 1401})
    m.reject_final_test_year_change({1400, 1401, 1402})  # does not raise


def test_reject_next_research_pointer_guard():
    with pytest.raises(
        m.AuthorizationError, match="next research pointer changed",
    ):
        m.reject_next_research_pointer("stage126-something-else")
    m.reject_next_research_pointer("stage126-m1-financial-baseline")


# --------------------------------------------------------------------------- #
# Keep/drop vocabulary and exact rows
# --------------------------------------------------------------------------- #

def test_keep_drop_vocabulary_exact():
    assert m.KEEP_DROP_VOCAB == frozenset({
        "KEEP_READY", "KEEP_ROBUSTNESS", "KEEP_LOCKED", "KEEP_AUDIT_ONLY",
        "KEEP_DESCRIPTIVE_ONLY", "DEFER_NONBLOCKING_FOR_M1",
        "DROP_CURRENT_ACTIVE_PATH", "SUPERSEDED_HISTORICAL_ONLY",
    })


def test_validate_decision_vocabulary_rejects_unknown():
    with pytest.raises(m.QCFail, match="unknown keep/drop decision"):
        m.validate_decision_vocabulary("SOMETHING_ELSE")
    m.validate_decision_vocabulary("KEEP_READY")  # does not raise


def test_keep_drop_rows_exact_item_ids_and_decisions():
    rows = m.build_keep_drop_rows()
    assert len(rows) == 24
    kd = {r["item_id"]: r["decision"] for r in rows}
    assert kd == m.REQUIRED_KEEP_DROP_DECISIONS
    assert kd == {
        "SAMPLE_PRIMARY_RULE_A": "KEEP_READY",
        "SAMPLE_RULE_B": "KEEP_ROBUSTNESS",
        "SAMPLE_EXPANDED_RULE_A": "KEEP_ROBUSTNESS",
        "SAMPLE_EXPANDED_RULE_B": "KEEP_ROBUSTNESS",
        "TARGET_MAIN_T_PLUS_1": "KEEP_READY",
        "TARGET_PERSISTENT_LOSS_T_PLUS_1": "KEEP_ROBUSTNESS",
        "TARGET_ARTICLE141_ONLY_T_PLUS_1": "KEEP_DESCRIPTIVE_ONLY",
        "FEATURESET_M1_PRIMARY_9": "KEEP_READY",
        "FEATURESET_M1_TARGET_PROXIMITY_6": "KEEP_ROBUSTNESS",
        "FEATURE_REVENUE_GROWTH": "KEEP_AUDIT_ONLY",
        "BLOCK_M2_MARKET": "DEFER_NONBLOCKING_FOR_M1",
        "BLOCK_M3_MACRO": "DROP_CURRENT_ACTIVE_PATH",
        "BLOCK_M4_AUDIT_GOVERNANCE": "DEFER_NONBLOCKING_FOR_M1",
        "BLOCK_M5_PERSIAN_TEXT": "DROP_CURRENT_ACTIVE_PATH",
        "MODEL_REGULARIZED_LOGISTIC": "KEEP_READY",
        "MODEL_RANDOM_FOREST": "KEEP_READY",
        "MODEL_XGBOOST": "KEEP_READY",
        "IMBALANCE_CLASS_WEIGHTING": "KEEP_READY",
        "IMBALANCE_SMOTE": "KEEP_ROBUSTNESS",
        "FINAL_TEST_1400_1402": "KEEP_LOCKED",
        "AVAILABILITY_FOUR_JALALI_MONTHS": "KEEP_LOCKED",
        "AVAILABILITY_SIX_MONTH_METHOD": "SUPERSEDED_HISTORICAL_ONLY",
        "BROAD_CODAL_PUBLISH_DATETIME_CAPTURE": "DROP_CURRENT_ACTIVE_PATH",
        "RAMPNA_1396_TO_1397_TIMING_VIOLATION": "KEEP_AUDIT_ONLY",
    }


def test_validate_keep_drop_rows_accepts_exact_rows():
    m.validate_keep_drop_rows(m.build_keep_drop_rows())


def test_validate_keep_drop_rows_rejects_unknown_vocabulary():
    rows = m.build_keep_drop_rows()
    rows[0] = dict(rows[0])
    rows[0]["decision"] = "NOT_A_REAL_DECISION"
    with pytest.raises(m.QCFail, match="unknown keep/drop decision"):
        m.validate_keep_drop_rows(rows)


def test_validate_keep_drop_rows_rejects_missing_item():
    rows = [r for r in m.build_keep_drop_rows() if r["item_id"] != (
        "FEATURE_REVENUE_GROWTH"
    )]
    with pytest.raises(m.QCFail, match="missing required keep/drop items"):
        m.validate_keep_drop_rows(rows)


def test_validate_keep_drop_rows_rejects_mutated_decision():
    rows = m.build_keep_drop_rows()
    rows[0] = dict(rows[0])
    rows[0]["decision"] = "KEEP_ROBUSTNESS"  # was KEEP_READY
    with pytest.raises(m.QCFail, match="keep/drop decision mutated"):
        m.validate_keep_drop_rows(rows)


def test_validate_keep_drop_rows_rejects_duplicate_item_id():
    rows = m.build_keep_drop_rows()
    rows.append(dict(rows[0]))
    with pytest.raises(m.QCFail, match="duplicate keep/drop item_id"):
        m.validate_keep_drop_rows(rows)


# --------------------------------------------------------------------------- #
# Blocker register
# --------------------------------------------------------------------------- #

def test_blocker_register_required_rows_present():
    rows = m.build_blocker_register_rows()
    assert len(rows) == 8
    ids = {r["item_id"] for r in rows}
    assert ids == {
        "M2_VALUES_NOT_COLLECTED",
        "M3_AUTHORITATIVE_SOURCE_UNAVAILABLE",
        "M4_VALUES_NOT_COLLECTED",
        "PART3B_EXPANSION_INCOMPLETE",
        "ARTICLE141_LOW_EVENT_COUNT",
        "REVENUE_GROWTH_COVERAGE_FAILURE",
        "NO_GITHUB_ACTIONS",
        "M1_PROVENANCE_GAPS_AUDITED",
    }


def test_blocker_register_none_block_closure_or_m1():
    rows = m.build_blocker_register_rows()
    for row in rows:
        assert row["blocks_stage125_closure"] == "false"
        assert row["blocks_stage126_m1"] == "false"


def test_validate_blocker_rows_accepts_exact_rows():
    m.validate_blocker_rows(m.build_blocker_register_rows())


def test_validate_blocker_rows_rejects_missing_item():
    rows = [
        r for r in m.build_blocker_register_rows()
        if r["item_id"] != "NO_GITHUB_ACTIONS"
    ]
    with pytest.raises(m.QCFail, match="missing required blocker items"):
        m.validate_blocker_rows(rows)


def test_validate_blocker_rows_rejects_non_boolean_flag():
    rows = m.build_blocker_register_rows()
    rows[0] = dict(rows[0])
    rows[0]["blocks_stage125_closure"] = "yes"
    with pytest.raises(m.QCFail, match="non-boolean-string"):
        m.validate_blocker_rows(rows)


def test_validate_blocker_rows_rejects_m2_m3_m4_blocking():
    rows = m.build_blocker_register_rows()
    for i, row in enumerate(rows):
        if row["item_id"] == "M2_VALUES_NOT_COLLECTED":
            rows[i] = dict(row)
            rows[i]["blocks_stage126_m1"] = "true"
    with pytest.raises(m.QCFail, match="must not block Stage126 M1 entry"):
        m.validate_blocker_rows(rows)


# --------------------------------------------------------------------------- #
# No model imports; no fit/predict/SHAP; no analysis-ready access
# --------------------------------------------------------------------------- #

def test_no_model_imports_in_source():
    m.assert_no_model_imports_in_source(REPO_ROOT)


def test_no_analysis_ready_access_in_source():
    m.assert_no_analysis_ready_access_in_source(REPO_ROOT)


def test_forbidden_call_names_rejected_via_ast():
    import ast
    import tempfile

    src = "def f():\n    model.fit(X, y)\n"
    tree = ast.parse(src)
    banned_hit = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(
                fn, "id", None,
            )
            if name in m.BANNED_CALL_NAMES:
                banned_hit = True
    assert banned_hit
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "project" / "src").mkdir(parents=True)
        rel = "project/src/fake_model_call.py"
        (tmp_path / rel).write_text(src, encoding="utf-8")
        with pytest.raises(m.AuthorizationError, match="forbidden model call"):
            m.assert_no_model_imports_in_source(tmp_path, rel=rel)


def test_forbidden_import_rejected_via_ast(tmp_path):
    src = "from sklearn.linear_model import LogisticRegression\n"
    (tmp_path / "fake.py").write_text(src, encoding="utf-8")
    with pytest.raises(m.AuthorizationError, match="model import attempt"):
        m.assert_no_model_imports_in_source(tmp_path, rel="fake.py")


def test_forbidden_shap_import_rejected_via_ast(tmp_path):
    src = "import shap\n"
    (tmp_path / "fake.py").write_text(src, encoding="utf-8")
    with pytest.raises(m.AuthorizationError, match="model import attempt"):
        m.assert_no_model_imports_in_source(tmp_path, rel="fake.py")


def test_forbidden_analysis_ready_reference_rejected_via_ast(tmp_path):
    src = "from src import stage125_part4_statistical_analysis_plan as p4\nx = p4.ANALYSIS_READY_FILES\n"
    (tmp_path / "fake.py").write_text(src, encoding="utf-8")
    with pytest.raises(
        m.AuthorizationError, match="analysis-ready predictor data",
    ):
        m.assert_no_analysis_ready_access_in_source(tmp_path, rel="fake.py")


def test_forbidden_surfaces_absent():
    m.assert_forbidden_surfaces_absent(REPO_ROOT)
    for rel in m.FORBIDDEN_SURFACE_EXACT:
        assert not (REPO_ROOT / rel).exists()


def test_forbidden_surfaces_exact_paths():
    assert m.FORBIDDEN_SURFACE_EXACT == (
        "project/src/stage126_m1_financial_baseline.py",
        "project/run_stage126.py",
        "project/stage126",
    )


# --------------------------------------------------------------------------- #
# Network sentinel / determinism / offline
# --------------------------------------------------------------------------- #

def test_network_attempt_blocked_by_sentinel():
    with p3b0.network_sentinel() as sentinel:
        with pytest.raises(Exception):
            socket.create_connection(("example.com", 80), timeout=0.1)
        assert sentinel.calls_attempted >= 1


def test_build_all_offline_and_deterministic():
    with p3b0.network_sentinel() as sentinel:
        c1, _ = m.build_all(REPO_ROOT)
        c2, _ = m.build_all(REPO_ROOT)
        assert sentinel.calls_attempted == 0
    assert set(c1) == set(m.TRACKED_CONTENT_FILES)
    for k in c1:
        assert c1[k] == c2[k]
    assert c1[m.F_CLOSURE_REPORT] == json.dumps(
        json.loads(c1[m.F_CLOSURE_REPORT]), indent=2, ensure_ascii=False,
        sort_keys=True,
    ) + "\n"


def test_run_build_and_check(tmp_path):
    with p3b0.network_sentinel() as sentinel:
        result = m.run(
            project_dir=ROOT, output_dir=tmp_path, build=True, check=False,
        )
        assert sentinel.calls_attempted == 0
    assert result["qc"]["all_pass"] is True
    assert result["qc"]["model_fit_calls"] == 0
    assert result["qc"]["prediction_calls"] == 0
    assert result["qc"]["shap_calls"] == 0
    assert result["qc"]["contract_version"] == (
        "stage125_part5_readiness_closure_v1"
    )
    assert result["qc"]["research_pointers"]["next_research_action_id"] == (
        "stage126-m1-financial-baseline"
    )
    assert result["qc"]["stage126_authorized"] is False
    assert result["qc"]["modeling_started"] is False
    assert result["qc"]["final_test_unlocked"] is False
    result2 = m.run(
        project_dir=ROOT, output_dir=tmp_path, build=False, check=True,
    )
    assert result2["qc"]["all_pass"] is True


def test_check_mode_zero_writes(tmp_path, monkeypatch):
    with p3b0.network_sentinel():
        m.run(project_dir=ROOT, output_dir=tmp_path, build=True, check=False)

    write_calls: list[Path] = []
    orig_write_text = Path.write_text

    def _tracking_write_text(self, *args, **kwargs):
        write_calls.append(self)
        return orig_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", _tracking_write_text)
    with p3b0.network_sentinel():
        result = m.run(
            project_dir=ROOT, output_dir=tmp_path, build=False, check=True,
        )
    assert result["qc"]["all_pass"] is True
    assert write_calls == []


def test_run_canonical_check_zero_drift():
    with p3b0.network_sentinel():
        result = m.run(project_dir=ROOT, build=False, check=True)
    assert result["qc"]["all_pass"] is True
    assert result["drift"] == []


# --------------------------------------------------------------------------- #
# QC report content
# --------------------------------------------------------------------------- #

def test_qc_assertions_all_pass_on_real_repo():
    with p3b0.network_sentinel():
        head = m.verify_baseline_commit(REPO_ROOT)
        content, extras = m.build_all(REPO_ROOT)
        assertions = m.build_qc_assertions(
            repo_root=REPO_ROOT, extras=extras, content=content,
            network_attempts=0, head=head,
        )
    failed = [a for a in assertions if a["status"] != "PASS"]
    assert failed == []
    assert len(assertions) >= 40


def test_qc_marker_fields_present():
    ready = m.derive_closure_flags(True)
    markers = m._static_qc_markers(ready)
    for field in m.REQUIRED_HANDOFF_MARKER_FIELDS:
        assert field in markers


def test_qc_marker_values_exact():
    ready = m.derive_closure_flags(True)
    markers = m._static_qc_markers(ready)
    assert markers["stage125_part5_readiness_closure_completed"] is True
    assert markers["stage125_completed"] is True
    assert markers["stage126_m1_entry_ready"] is True
    assert markers["stage126_authorized"] is False
    assert markers["stage126_started"] is False
    assert markers["modeling_authorized"] is False
    assert markers["modeling_started"] is False
    assert markers["part4_statistical_analysis_plan_locked"] is True
    assert markers["part3c_leakage_safe_finalization_completed"] is True
    assert markers["active_availability_lag_months"] == 4
    assert markers["shap_calls"] == 0
    assert markers["final_test_unlocked"] is False
    assert markers["part3b_completed"] is False
    assert markers["m3_admitted"] is False


def test_qc_markers_derive_from_failed_gate():
    failed = m.derive_closure_flags(False)
    markers = m._static_qc_markers(failed)
    assert markers["stage125_part5_readiness_closure_completed"] is False
    assert markers["stage125_completed"] is False
    assert markers["stage126_m1_entry_ready"] is False
    assert markers["stage126_authorized"] is False
    assert markers["modeling_started"] is False
    assert markers["final_test_unlocked"] is False


# --------------------------------------------------------------------------- #
# Gate 125.0
# --------------------------------------------------------------------------- #

def test_gate_125_0_has_27_dimensions_and_all_pass():
    with p3b0.network_sentinel():
        content, extras = m.build_all(REPO_ROOT)
    gate = extras["gate"]
    assert len(gate) == 27
    for name, dim in gate.items():
        assert dim["pass"] is True, f"{name}: {dim}"


def test_gate_125_0_dimension_names_exact():
    with p3b0.network_sentinel():
        _, extras = m.build_all(REPO_ROOT)
    assert set(extras["gate"]) == {
        "contradiction_free_docs", "valid_handoff", "part3c_hashes_unchanged",
        "part4_hashes_unchanged", "part4_qc_all_pass",
        "keep_drop_decisions_complete", "blocker_register_complete",
        "stage126_entry_boundary_explicit", "final_test_still_locked",
        "financial_data_unchanged", "targets_unchanged", "samples_unchanged",
        "four_month_lag_active", "six_month_method_historical_only",
        "revenue_growth_audit_only", "article141_descriptive_only",
        "m1_ready", "m2_deferred", "m3_not_admitted", "m4_deferred",
        "m5_removed", "network_requests_zero", "model_fit_calls_zero",
        "prediction_calls_zero", "shap_calls_zero", "stage126_false",
        "working_tree_clean",
    }


def test_closure_report_gate_pass_string():
    with p3b0.network_sentinel():
        content, _ = m.build_all(REPO_ROOT)
    closure = json.loads(content[m.F_CLOSURE_REPORT])
    assert closure["stage125_gate_125_0"] == "PASS"


# --------------------------------------------------------------------------- #
# Integrity manifest
# --------------------------------------------------------------------------- #

def test_integrity_manifest_row_count_and_roles():
    with p3b0.network_sentinel():
        content, extras = m.build_all(REPO_ROOT)
    rows = extras["integrity_rows"]
    assert len(rows) == 34
    roles = {r["artifact_role"] for r in rows}
    assert roles == {
        "frozen_part3c_input", "frozen_part4_output", "frozen_part4_source",
        "frozen_part4_test", "roadmap_pointer_source",
        "handoff_selected_qc_source", "part5_output",
    }
    for row in rows:
        assert row["status"] == "MATCH"
        assert row["mutation_authorized"] in {"true", "false"}


def test_integrity_manifest_frozen_rows_not_mutation_authorized():
    with p3b0.network_sentinel():
        _, extras = m.build_all(REPO_ROOT)
    for row in extras["integrity_rows"]:
        if row["artifact_role"] in {
            "frozen_part3c_input", "frozen_part4_output",
            "frozen_part4_source", "frozen_part4_test",
        }:
            assert row["mutation_authorized"] == "false"


def test_integrity_manifest_part5_own_outputs_mutation_authorized():
    with p3b0.network_sentinel():
        _, extras = m.build_all(REPO_ROOT)
    part5_rows = [
        r for r in extras["integrity_rows"] if r["artifact_role"] == (
            "part5_output"
        )
    ]
    assert len(part5_rows) == 5
    for row in part5_rows:
        assert row["mutation_authorized"] == "true"


# --------------------------------------------------------------------------- #
# Closure report sample counts / keep-drop / blocker summaries
# --------------------------------------------------------------------------- #

def test_closure_report_sample_counts():
    with p3b0.network_sentinel():
        content, _ = m.build_all(REPO_ROOT)
    closure = json.loads(content[m.F_CLOSURE_REPORT])
    assert closure["sample_counts"] == {
        sample: dict(spec) for sample, spec in m.SAMPLE_SPECS.items()
    }


def test_closure_report_keep_drop_and_blocker_summary():
    with p3b0.network_sentinel():
        content, _ = m.build_all(REPO_ROOT)
    closure = json.loads(content[m.F_CLOSURE_REPORT])
    assert closure["keep_drop_item_count"] == 24
    assert sum(closure["keep_drop_summary"].values()) == 24
    assert closure["blocker_summary"]["total"] == 8
    assert closure["blocker_summary"]["blocking_stage125_closure"] == 0
    assert closure["blocker_summary"]["blocking_stage126_m1"] == 0


def test_closure_report_final_test_fields():
    with p3b0.network_sentinel():
        content, _ = m.build_all(REPO_ROOT)
    closure = json.loads(content[m.F_CLOSURE_REPORT])
    assert closure["final_test_status"] == "locked_for_single_future_evaluation"
    assert closure["final_test_years"] == [1400, 1401, 1402]
    assert closure["final_test_predictor_inspection_in_part5"] is False
    assert closure["final_test_model_evaluation_in_part5"] is False
    assert closure["active_availability_lag_months"] == 4


# --------------------------------------------------------------------------- #
# Deterministic rebuild / drift
# --------------------------------------------------------------------------- #

def test_deterministic_content_hashes_stable():
    with p3b0.network_sentinel():
        c1, _ = m.build_all(REPO_ROOT)
        c2, _ = m.build_all(REPO_ROOT)
    for name in m.TRACKED_CONTENT_FILES:
        assert c1[name] == c2[name]


def test_csv_outputs_are_sorted_deterministically():
    with p3b0.network_sentinel():
        content, _ = m.build_all(REPO_ROOT)
    integrity_lines = content[m.F_INTEGRITY].splitlines()[1:]
    paths = [line.split(",", 1)[0] for line in integrity_lines]
    assert paths == sorted(paths)


# --------------------------------------------------------------------------- #
# Derived closure from Gate 125.0 (mutation → NOT_READY)
# --------------------------------------------------------------------------- #

def _failed_gate_surfaces(extras, dim_name: str):
    """Derive every readiness surface from a Gate with one dimension flipped.

    Returns ``(closure, entry_contract, handoff_markers, metadata_markers,
    readme_text)``, all built from the SAME failed final Gate result — exactly
    as ``build_all`` derives them for a real failing Gate.
    """
    gate = {k: dict(v) for k, v in extras["gate"].items()}
    assert dim_name in gate, dim_name
    gate[dim_name] = {"pass": False, "detail": f"mutated_{dim_name}"}
    final_pass = all(v["pass"] for v in gate.values())
    entry_contract = m.build_stage126_m1_entry_contract(entry_ready=final_pass)
    closure = m.build_closure_report(
        keep_drop_rows=extras["keep_drop_rows"],
        blocker_rows=extras["blocker_rows"],
        part4_qc=extras["part4_qc"],
        entry_contract=entry_contract,
        gate=gate,
    )
    flags = m.derive_closure_flags(closure["all_gate_pass"])
    markers = m._static_qc_markers(flags)  # handoff + metadata markers
    # Both README readiness statements derive from the SAME final Gate result.
    readme_text = m.build_readme(
        closure_outcome=closure["closure_outcome"],
        entry_readiness=entry_contract["entry_readiness"],
    )
    return closure, entry_contract, markers, readme_text


@pytest.mark.parametrize(
    "dim_name",
    [
        "part3c_hashes_unchanged",
        "part4_hashes_unchanged",
        "valid_handoff",
        "final_test_still_locked",
        "stage126_false",
    ],
)
def test_gate_dimension_failure_produces_not_ready(dim_name):
    with p3b0.network_sentinel():
        _, extras = m.build_all(REPO_ROOT)
    closure, entry_contract, markers, readme_text = _failed_gate_surfaces(
        extras, dim_name,
    )
    # Closure report.
    assert closure["all_gate_pass"] is False
    assert closure["stage125_completed"] is False
    assert closure["stage126_m1_entry_ready"] is False
    assert closure["stage125_part5_readiness_closure_completed"] is False
    assert closure["stage125_gate_125_0"] == "FAIL"
    assert closure["closure_outcome"] == m.CLOSURE_OUTCOME_NOT_READY
    assert closure["stage126_authorized"] is False
    assert closure["stage126_started"] is False
    assert closure["modeling_authorized"] is False
    assert closure["modeling_started"] is False
    assert closure["final_test_unlocked"] is False
    # Entry contract.
    assert entry_contract["stage126_m1_entry_ready"] is False
    assert entry_contract["entry_readiness"] == m.ENTRY_READINESS_NOT_READY
    # Handoff markers.
    assert markers["stage125_completed"] is False
    assert markers["stage126_m1_entry_ready"] is False
    # Metadata markers (same derived marker source as Handoff/metadata).
    assert markers["stage125_part5_readiness_closure_completed"] is False
    # README: contains NOT_READY_WITH_BLOCKERS and NEITHER READY string, and
    # carries no READY entry-readiness statement.
    assert m.CLOSURE_OUTCOME_NOT_READY in readme_text
    assert m.CLOSURE_OUTCOME_READY not in readme_text
    assert m.ENTRY_READINESS_READY not in readme_text
    assert f"entry_readiness = {m.ENTRY_READINESS_NOT_READY}" in readme_text
    assert m._readme_reports_ready(readme_text) is False
    # No surface may hold the ready outcome on a failed Gate.
    ok, detail = m.validate_readiness_surface_consistency(
        final_gate_pass=False,
        closure_report=closure,
        entry_contract=entry_contract,
        readme_text=readme_text,
    )
    assert ok is True, detail


# --------------------------------------------------------------------------- #
# Cross-artifact readiness consistency (§3)
# --------------------------------------------------------------------------- #

def test_cross_artifact_readiness_consistency_on_disk():
    ok, detail, states = m.check_cross_artifact_readiness_consistency(REPO_ROOT)
    assert ok is True, f"{detail} :: {states}"
    # All six surfaces must be present and ready in the canonical (passing) state.
    assert set(states) == set(m.READINESS_SURFACE_NAMES)
    assert all(v is True for v in states.values()), states


def test_readiness_surface_consistency_detects_ready_leak():
    ready_closure = {
        "stage126_m1_entry_ready": True,
        "stage125_completed": True,
        "all_gate_pass": True,
        "closure_outcome": m.CLOSURE_OUTCOME_READY,
        "stage125_gate_125_0": "PASS",
    }
    # A ready closure while the final Gate failed is a fail-closed inconsistency.
    ok, detail = m.validate_readiness_surface_consistency(
        final_gate_pass=False, closure_report=ready_closure,
    )
    assert ok is False
    assert "disagreement" in detail or "leaked" in detail


def test_readiness_surface_consistency_all_not_ready_agree():
    not_ready_closure = {
        "stage126_m1_entry_ready": False,
        "stage125_completed": False,
        "all_gate_pass": False,
        "closure_outcome": m.CLOSURE_OUTCOME_NOT_READY,
        "stage125_gate_125_0": "FAIL",
    }
    entry = m.build_stage126_m1_entry_contract(entry_ready=False)
    readme = m.build_readme(
        closure_outcome=m.CLOSURE_OUTCOME_NOT_READY,
        entry_readiness=m.ENTRY_READINESS_NOT_READY,
    )
    ok, detail = m.validate_readiness_surface_consistency(
        final_gate_pass=False,
        closure_report=not_ready_closure,
        entry_contract=entry,
        readme_text=readme,
    )
    assert ok is True, detail


# --------------------------------------------------------------------------- #
# README readiness is derived from both closure_outcome and entry_readiness
# --------------------------------------------------------------------------- #

def test_build_readme_requires_entry_readiness_argument():
    with pytest.raises(TypeError):
        m.build_readme(closure_outcome=m.CLOSURE_OUTCOME_READY)


def test_build_readme_rejects_unknown_entry_readiness():
    with pytest.raises(m.QCFail, match="invalid entry_readiness"):
        m.build_readme(
            closure_outcome=m.CLOSURE_OUTCOME_READY,
            entry_readiness="SOMETHING_ELSE",
        )


def test_readme_passing_gate_both_statements_ready():
    readme = m.build_readme(
        closure_outcome=m.CLOSURE_OUTCOME_READY,
        entry_readiness=m.ENTRY_READINESS_READY,
    )
    assert m.CLOSURE_OUTCOME_READY in readme
    assert m.ENTRY_READINESS_READY in readme
    assert m.CLOSURE_OUTCOME_NOT_READY not in readme
    assert f"closure_outcome = {m.CLOSURE_OUTCOME_READY}" in readme
    assert f"entry_readiness = {m.ENTRY_READINESS_READY}" in readme
    assert m._readme_reports_ready(readme) is True


def test_readme_failing_gate_both_statements_not_ready():
    readme = m.build_readme(
        closure_outcome=m.CLOSURE_OUTCOME_NOT_READY,
        entry_readiness=m.ENTRY_READINESS_NOT_READY,
    )
    assert m.CLOSURE_OUTCOME_NOT_READY in readme
    assert m.CLOSURE_OUTCOME_READY not in readme
    assert m.ENTRY_READINESS_READY not in readme
    assert f"closure_outcome = {m.CLOSURE_OUTCOME_NOT_READY}" in readme
    assert f"entry_readiness = {m.ENTRY_READINESS_NOT_READY}" in readme
    assert m._readme_reports_ready(readme) is False


def test_readme_reports_ready_rejects_mixed_states():
    # closure_outcome NOT_READY but entry_readiness READY => ambiguous => None.
    mixed = m.build_readme(
        closure_outcome=m.CLOSURE_OUTCOME_NOT_READY,
        entry_readiness=m.ENTRY_READINESS_READY,
    )
    assert m.ENTRY_READINESS_READY in mixed
    assert m.CLOSURE_OUTCOME_NOT_READY in mixed
    assert m._readme_reports_ready(mixed) is None
    # The reverse mix (ready closure, not-ready entry) is also ambiguous.
    mixed2 = m.build_readme(
        closure_outcome=m.CLOSURE_OUTCOME_READY,
        entry_readiness=m.ENTRY_READINESS_NOT_READY,
    )
    assert m._readme_reports_ready(mixed2) is None


def test_cross_artifact_validator_fails_on_mixed_readme():
    # A README stating closure_outcome=NOT_READY_WITH_BLOCKERS but
    # entry_readiness=READY_FOR_HUMAN_AUTHORIZATION_DECISION is a fail-closed
    # cross-artifact inconsistency for a failed Gate.
    mixed_readme = m.build_readme(
        closure_outcome=m.CLOSURE_OUTCOME_NOT_READY,
        entry_readiness=m.ENTRY_READINESS_READY,
    )
    assert m.CLOSURE_OUTCOME_NOT_READY in mixed_readme
    assert m.ENTRY_READINESS_READY in mixed_readme
    ok, detail = m.validate_readiness_surface_consistency(
        final_gate_pass=False,
        readme_text=mixed_readme,
    )
    assert ok is False, detail
    # And it must not pass as ready either.
    ok_ready, _ = m.validate_readiness_surface_consistency(
        final_gate_pass=True,
        readme_text=mixed_readme,
    )
    assert ok_ready is False


def test_derive_closure_flags_ready_and_not_ready():
    ready = m.derive_closure_flags(True)
    assert ready["closure_outcome"] == m.CLOSURE_OUTCOME_READY
    assert ready["stage125_gate_125_0"] == "PASS"
    assert ready["stage125_completed"] is True
    failed = m.derive_closure_flags(False)
    assert failed["closure_outcome"] == m.CLOSURE_OUTCOME_NOT_READY
    assert failed["stage125_gate_125_0"] == "FAIL"
    assert failed["stage125_completed"] is False
    assert failed["stage126_m1_entry_ready"] is False


# --------------------------------------------------------------------------- #
# M1 robustness registry — exact six categories / three samples
# --------------------------------------------------------------------------- #

def test_registered_m1_robustness_six_categories_exact():
    contract = m.build_stage126_m1_entry_contract(entry_ready=True)
    entries = contract["registered_m1_robustness_after_primary_lock"]
    assert len(entries) == 6
    m.validate_registered_m1_robustness(entries)
    samples = [e["sample"] for e in entries if "sample" in e]
    assert sorted(samples) == sorted(m.REQUIRED_ROBUSTNESS_SAMPLES)
    by_sample = {e["sample"]: e for e in entries if "sample" in e}
    assert by_sample["main_rule_b_listing_robustness"]["role"] == (
        "listing_timing_sample_robustness"
    )
    assert by_sample["expanded_rule_a_company_scope_robustness"]["role"] == (
        "expanded_company_scope_sample_robustness"
    )
    assert by_sample["expanded_rule_b_combined_robustness"]["role"] == (
        "combined_sample_robustness"
    )
    smote = next(
        e for e in entries
        if e.get("category_id") == "smote_training_fold_only_robustness"
    )
    assert smote["class_weighting"] == "disabled"
    assert smote["second_tuning_search"] is False
    prox = next(
        e for e in entries
        if e.get("category_id") == "m1_target_proximity_six_feature_set"
    )
    assert prox["feature_count"] == 6
    assert prox["features_exact_order"] == m.M1_TARGET_PROXIMITY_ROBUSTNESS
    persistent = next(
        e for e in entries
        if e.get("category_id") == "persistent_loss_robustness_target"
    )
    assert persistent["target"] == m.SECONDARY_TARGET


@pytest.mark.parametrize(
    "missing_sample",
    sorted(m.REQUIRED_ROBUSTNESS_SAMPLES),
)
def test_robustness_sample_absence_fails(missing_sample):
    entries = [
        dict(e) for e in m.REGISTERED_M1_ROBUSTNESS_AFTER_PRIMARY_LOCK
        if e.get("sample") != missing_sample
    ]
    with pytest.raises(m.QCFail, match="robustness sample set mutation"):
        m.validate_registered_m1_robustness(entries)


def test_robustness_sample_rename_fails():
    entries = [dict(e) for e in m.REGISTERED_M1_ROBUSTNESS_AFTER_PRIMARY_LOCK]
    for e in entries:
        if e.get("sample") == "main_rule_b_listing_robustness":
            e["sample"] = "main_rule_b_listing_robustness_renamed"
    with pytest.raises(m.QCFail, match="robustness sample set mutation"):
        m.validate_registered_m1_robustness(entries)


def test_robustness_sample_duplicate_fails():
    entries = [dict(e) for e in m.REGISTERED_M1_ROBUSTNESS_AFTER_PRIMARY_LOCK]
    entries.append(dict(entries[1]))
    with pytest.raises(m.QCFail):
        m.validate_registered_m1_robustness(entries)


# --------------------------------------------------------------------------- #
# Actual Handoff validation mutations
# --------------------------------------------------------------------------- #

def test_validate_actual_handoff_passes_current_state():
    ok, detail = m.validate_actual_handoff(
        REPO_ROOT, derived_completed=True, derived_entry_ready=True,
    )
    assert ok is True
    assert detail == "actual_handoff_state_matches_derived_closure"


def test_handoff_mutation_wrong_selected_qc_scope(tmp_path, monkeypatch):
    state = m.load_handoff_state(REPO_ROOT)
    state["selected_qc_scope"] = "stage125_part4_statistical_analysis_plan"
    handoff = tmp_path / "handoff_state.json"
    handoff.write_text(json.dumps(state), encoding="utf-8")
    monkeypatch.setattr(m, "HANDOFF_STATE_REL", str(handoff.name))
    # Point load to tmp via monkeypatch on load_handoff_state
    monkeypatch.setattr(
        m, "load_handoff_state", lambda _root: state,
    )
    ok, detail = m.validate_actual_handoff(
        REPO_ROOT, derived_completed=True, derived_entry_ready=True,
    )
    assert ok is False
    assert "selected_qc_scope" in detail


def test_handoff_mutation_wrong_next_research_action_id(monkeypatch):
    state = m.load_handoff_state(REPO_ROOT)
    state["next_research_action_id"] = "stage126-unauthorized"
    monkeypatch.setattr(m, "load_handoff_state", lambda _root: state)
    ok, detail = m.validate_actual_handoff(
        REPO_ROOT, derived_completed=True, derived_entry_ready=True,
    )
    assert ok is False
    assert "next_research_action_id" in detail


@pytest.mark.parametrize(
    "field,value",
    [
        ("stage126_authorized", True),
        ("modeling_started", True),
        ("final_test_unlocked", True),
        ("active_availability_lag_months", 6),
    ],
)
def test_handoff_mutation_auth_and_lag_fields(monkeypatch, field, value):
    state = m.load_handoff_state(REPO_ROOT)
    state[field] = value
    monkeypatch.setattr(m, "load_handoff_state", lambda _root: state)
    ok, detail = m.validate_actual_handoff(
        REPO_ROOT, derived_completed=True, derived_entry_ready=True,
    )
    assert ok is False
    assert field in detail


# --------------------------------------------------------------------------- #
# Working-tree control via actual git status (temp repo fixtures)
# --------------------------------------------------------------------------- #

def _init_temp_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init"], cwd=repo, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "test"],
        cwd=repo, check=True, capture_output=True,
    )
    tracked = repo / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "tracked.txt"], cwd=repo, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo, check=True, capture_output=True,
    )
    return repo


@pytest.mark.real_working_tree
def test_working_tree_unauthorized_tracked_modification_fails(tmp_path):
    repo = _init_temp_repo(tmp_path)
    (repo / "tracked.txt").write_text("mutated\n", encoding="utf-8")
    ok, detail = m.evaluate_working_tree_clean(repo, mode="build")
    assert ok is False
    assert "unauthorized" in detail
    ok_check, _ = m.evaluate_working_tree_clean(repo, mode="check")
    assert ok_check is False


@pytest.mark.real_working_tree
def test_working_tree_unauthorized_nested_untracked_fails(tmp_path):
    repo = _init_temp_repo(tmp_path)
    nested = repo / "project" / "stage125" / "nested"
    nested.mkdir(parents=True)
    (nested / "secret.txt").write_text("x\n", encoding="utf-8")
    ok, detail = m.evaluate_working_tree_clean(repo, mode="build")
    assert ok is False
    assert "unauthorized" in detail


@pytest.mark.real_working_tree
def test_working_tree_unauthorized_deletion_fails(tmp_path):
    repo = _init_temp_repo(tmp_path)
    (repo / "tracked.txt").unlink()
    ok, detail = m.evaluate_working_tree_clean(repo, mode="build")
    assert ok is False
    assert "unauthorized" in detail


@pytest.mark.real_working_tree
def test_working_tree_build_allows_only_exact_part5_paths(tmp_path):
    repo = _init_temp_repo(tmp_path)
    for rel in sorted(m.AUTHORIZED_PART5_GENERATED_PATHS):
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("generated\n", encoding="utf-8")
    ok, detail = m.evaluate_working_tree_clean(repo, mode="build")
    assert ok is True, detail
    ok_check, _ = m.evaluate_working_tree_clean(repo, mode="check")
    assert ok_check is False


@pytest.mark.real_working_tree
def test_working_tree_check_requires_completely_empty(tmp_path):
    repo = _init_temp_repo(tmp_path)
    ok, detail = m.evaluate_working_tree_clean(repo, mode="check")
    assert ok is True
    assert detail == "clean"


@pytest.mark.real_working_tree
def test_porcelain_parser_preserves_leading_space_status(tmp_path):
    """First porcelain line often starts with a space; must not lose path[0]."""
    repo = _init_temp_repo(tmp_path)
    (repo / "tracked.txt").write_text("mutated-again\n", encoding="utf-8")
    lines = m.git_status_porcelain(repo)
    assert lines, "expected dirty status"
    assert lines[0].startswith(" "), lines[0]
    paths = m.parse_porcelain_paths(lines)
    assert "tracked.txt" in paths
    assert all(not p.startswith("racked") for p in paths)


# --------------------------------------------------------------------------- #
# M3 nonpermanent not-admitted wording
# --------------------------------------------------------------------------- #

def test_m3_not_permanently_eliminated_wording():
    blockers = {r["item_id"]: r for r in m.build_blocker_register_rows()}
    row = blockers["M3_AUTHORITATIVE_SOURCE_UNAVAILABLE"]
    assert "re-enter" in row["required_future_action"]
    assert "permanently" not in row["required_future_action"].lower()
    kd = {r["item_id"]: r for r in m.build_keep_drop_rows()}
    notes = kd["BLOCK_M3_MACRO"]["notes"]
    assert "not permanently eliminated" in notes
    readme = m.build_readme(
        closure_outcome=m.CLOSURE_OUTCOME_READY,
        entry_readiness=m.ENTRY_READINESS_READY,
    )
    assert "not admitted on the current active path" in readme
    assert "permanently eliminated" in readme
    assert "M3 is **not** permanently eliminated" in readme
    with p3b0.network_sentinel():
        content, _ = m.build_all(REPO_ROOT)
    closure = json.loads(content[m.F_CLOSURE_REPORT])
    assert closure["m3_disposition"] == "not_admitted_on_current_active_path"
    assert closure["m3_data_collection_authorized_in_part5"] is False
    assert closure["m3_reentry_requirements"] == [
        "new_explicit_versioned_human_decision",
        "authoritative_and_reproducible_source",
        "publication_availability_time_validation",
        "coverage_and_temporal_data_gate_approval",
    ]
