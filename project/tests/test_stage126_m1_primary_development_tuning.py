"""Fail-closed tests for Stage126 M1 — Primary Development-Fold Tuning.

These tests verify the human authorization, the development-only fail-closed
loader, the frozen upstream contracts, the locked specification / budget /
seeds, the deterministic outputs, and — most importantly — that the final test
is never inspected, loaded, or evaluated.

No test loads final-test predictor or target values to prove that the lock
works: the guards are exercised structurally and against key-level metadata
only.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJECT_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

from src import stage126_m1_primary_development_tuning as m1  # noqa: E402

STAGE_DIR = PROJECT_DIR / "stage126"

AUTH_TEXT = (
    "Stage126 M1 Financial Baseline را با قرارداد قفل\u200cشده Part 4 و Part 5 "
    "مجاز می\u200cکنم؛ final test همچنان قفل بماند."
)
AUTH_SHA = "eeba72fe612b292fb611729676eef0a1d7e4b0c1e5fc9d8b533d62d8dcf41a50"


# --------------------------------------------------------------------------- #
# Fixtures (fast: load allowlist + development values once)
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def allowlist():
    return m1.build_development_allowlist(REPO_ROOT)


@pytest.fixture(scope="module")
def loaded(allowlist):
    return m1.load_development_values(REPO_ROOT, allowlist)


@pytest.fixture(scope="module")
def folds(allowlist, loaded):
    return {
        role: m1._role_matrix(loaded["rows"], allowlist["role_pairs"], role)
        for role in m1.DEV_ROLES
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# 1. Authorization
# --------------------------------------------------------------------------- #

def test_authorization_text_exact():
    assert m1.AUTHORIZATION_TEXT_FA == AUTH_TEXT


def test_authorization_sha256_exact():
    assert hashlib.sha256(AUTH_TEXT.encode("utf-8")).hexdigest() == AUTH_SHA
    assert m1.AUTHORIZATION_TEXT_SHA256 == AUTH_SHA


def test_authorization_record_on_disk_byte_for_byte():
    rec = _read_json(STAGE_DIR / m1.F_AUTH)
    assert rec["authorization_text_fa"] == AUTH_TEXT
    assert rec["authorization_text_sha256"] == AUTH_SHA
    assert (
        hashlib.sha256(rec["authorization_text_fa"].encode("utf-8")).hexdigest()
        == AUTH_SHA
    )
    assert rec["stage126_authorized"] is True
    assert rec["development_modeling_authorized"] is True
    assert rec["final_test_unlocked"] is False
    assert rec["final_test_access_authorized"] is False
    assert rec["final_test_evaluation_authorized"] is False
    assert rec["contract_change_authorized"] is False
    assert rec["m2_m3_m4_authorized"] is False


def test_authorization_text_mutation_fails():
    rec = m1.build_authorization_record()
    with pytest.raises(m1.AuthorizationError):
        m1.assert_authorization({**rec, "authorization_text_fa": "tampered"})


def test_authorization_hash_mutation_fails():
    rec = m1.build_authorization_record()
    with pytest.raises(m1.AuthorizationError):
        m1.assert_authorization({**rec, "authorization_text_sha256": "0" * 64})


def test_missing_authorization_record_fails():
    with pytest.raises(m1.AuthorizationError):
        m1.assert_authorization({})


def test_stage126_authorized_false_fails_before_fitting():
    rec = m1.build_authorization_record()
    with pytest.raises(m1.AuthorizationError):
        m1.assert_authorization({**rec, "stage126_authorized": False})


def test_final_test_unlocked_true_fails():
    rec = m1.build_authorization_record()
    with pytest.raises(m1.FinalTestLockError):
        m1.assert_authorization({**rec, "final_test_unlocked": True})


def test_final_test_access_authorized_true_fails():
    rec = m1.build_authorization_record()
    with pytest.raises(m1.FinalTestLockError):
        m1.assert_authorization({**rec, "final_test_access_authorized": True})


# --------------------------------------------------------------------------- #
# 2. Baseline + frozen upstream
# --------------------------------------------------------------------------- #

def test_baseline_constants():
    assert m1.EXPECTED_BASELINE_COMMIT == "5f56be5b2e49e66c54b451994a5e36c4fcc754d9"
    assert m1.EXPECTED_BASELINE_TREE == "d8f399e3dedac123065f6eda876dc9e71f0c36e7"


def test_wrong_baseline_fails():
    with pytest.raises(m1.QCFail):
        m1.verify_baseline_commit_with(REPO_ROOT, "0" * 40)


def test_frozen_part3c_hash_change_fails():
    rel = next(iter(m1.part5.FROZEN_PART3C_INPUTS))
    with pytest.raises(m1.QCFail):
        m1.require_file_hash(REPO_ROOT, rel, "0" * 64, label="Part 3C input")


def test_frozen_part4_hash_change_fails():
    rel = next(iter(m1.part5.FROZEN_PART4_OUTPUTS))
    with pytest.raises(m1.QCFail):
        m1.require_file_hash(REPO_ROOT, rel, "0" * 64, label="Part 4 output")


def test_frozen_part5_contract_hash_change_fails():
    rel = "project/stage125/part5_stage126_m1_entry_contract_stage125.json"
    with pytest.raises(m1.QCFail):
        m1.require_file_hash(REPO_ROOT, rel, "0" * 64, label="Part 5 output")


def test_frozen_upstream_all_present_and_matching():
    got = m1.frozen_upstream_hashes(REPO_ROOT)
    for rel, h in m1.part5.FROZEN_PART3C_INPUTS.items():
        assert got[rel] == h
    for rel, h in m1.part5.FROZEN_PART4_OUTPUTS.items():
        assert got[rel] == h
    for rel, h in m1.FROZEN_PART5_OUTPUTS.items():
        assert got[rel] == h
    assert got[m1.SPLIT_MANIFEST_REL] == m1.SPLIT_MANIFEST_SHA256


def test_analysis_ready_input_hash_pinned():
    assert (
        m1.sha256_file(REPO_ROOT / m1.ANALYSIS_READY_REL)
        == m1.ANALYSIS_READY_SHA256
    )


# --------------------------------------------------------------------------- #
# 3. Specification
# --------------------------------------------------------------------------- #

def test_exact_feature_order():
    assert m1.M1_PRIMARY_FEATURE_ORDER == [
        "log_total_assets", "leverage_ratio", "current_ratio",
        "roa_period_adjusted", "ocf_to_assets_period_adjusted",
        "asset_turnover_period_adjusted", "operating_margin_period_adjusted",
        "financial_expense_to_assets_period_adjusted",
        "accumulated_loss_to_capital_ratio",
    ]


def test_feature_added_removed_reordered_fails():
    with pytest.raises(m1.QCFail):
        m1.validate_feature_order(m1.M1_PRIMARY_FEATURE_ORDER[::-1])
    with pytest.raises(m1.QCFail):
        m1.validate_feature_order(m1.M1_PRIMARY_FEATURE_ORDER + ["extra"])
    with pytest.raises(m1.QCFail):
        m1.validate_feature_order(m1.M1_PRIMARY_FEATURE_ORDER[:-1])


def test_revenue_growth_included_fails():
    with pytest.raises(m1.QCFail):
        m1.validate_feature_order(
            m1.M1_PRIMARY_FEATURE_ORDER + ["revenue_growth_period_adjusted"]
        )
    assert "revenue_growth_period_adjusted" not in m1.M1_PRIMARY_FEATURE_ORDER
    assert (
        "revenue_growth_period_adjusted" not in m1.FEATURE_SOURCE_COLUMN.values()
    )


def test_article141_target_included_fails():
    with pytest.raises(m1.QCFail):
        m1.validate_target("FD_target_article141_only_t_plus_1")


def test_non_primary_sample_fails():
    with pytest.raises(m1.QCFail):
        m1.validate_sample("expanded_rule_a_company_scope_robustness")


def test_wrong_target_fails():
    with pytest.raises(m1.QCFail):
        m1.validate_target("FD_target_persistent_loss_robustness_t_plus_1")


def test_unauthorized_model_family_fails():
    for bad in ("SVM", "neural_network", "LightGBM", "CatBoost",
                "stacking", "voting"):
        with pytest.raises(m1.QCFail):
            m1.validate_model_family(bad)


def test_fit_predict_rejects_unauthorized_family(folds):
    import numpy as np
    tr = folds["fold1_train"]
    with pytest.raises(m1.QCFail):
        m1._fit_predict("SVM", {}, 1, np.zeros((3, 2)), np.array([0, 1, 0.0]),
                        np.zeros((1, 2)))


# --------------------------------------------------------------------------- #
# 4. Development-only loader counts
# --------------------------------------------------------------------------- #

def test_development_rows_666(allowlist):
    assert len(allowlist["dev_pairs"]) == 666


def test_final_test_denylist_346(allowlist):
    assert len(allowlist["denylist_pairs"]) == 346


def test_no_dev_final_test_overlap(allowlist):
    assert not (allowlist["dev_pairs"].keys() & allowlist["denylist_pairs"])


def test_fold1_train_245(folds):
    y = folds["fold1_train"]["y"]
    assert len(y) == 245
    assert int((y == 1).sum()) == 33
    assert int((y == 0).sum()) == 212


def test_fold1_validation_205(folds):
    y = folds["fold1_validation"]["y"]
    assert len(y) == 205
    assert int((y == 1).sum()) == 25
    assert int((y == 0).sum()) == 180


def test_fold2_train_450(folds):
    y = folds["fold2_train"]["y"]
    assert len(y) == 450
    assert int((y == 1).sum()) == 58
    assert int((y == 0).sum()) == 392


def test_fold2_validation_216(folds):
    y = folds["fold2_validation"]["y"]
    assert len(y) == 216
    assert int((y == 1).sum()) == 10
    assert int((y == 0).sum()) == 206


def test_development_class_totals(folds):
    import numpy as np
    dev_y = np.concatenate([
        folds[r]["y"] for r in
        ("fold1_train", "fold1_validation", "fold2_validation")
    ])
    assert len(dev_y) == 666
    assert int((dev_y == 1).sum()) == 68
    assert int((dev_y == 0).sum()) == 598
    assert int(np.isnan(dev_y).sum()) == 0


def test_no_final_test_values_loaded(loaded):
    assert loaded["final_test_values_loaded"] == 0
    assert loaded["final_test_rows_seen"] == 346
    assert len(loaded["rows"]) == 666


def test_loaded_modeling_rows_only_development_years(loaded):
    for info in loaded["rows"].values():
        assert info["target_year"] in m1.DEVELOPMENT_TARGET_YEARS
        assert info["target_year"] not in m1.FINAL_TEST_TARGET_YEARS


def test_loaded_rows_have_no_missing_target(loaded):
    import math
    for info in loaded["rows"].values():
        assert not math.isnan(info["target"])


# --------------------------------------------------------------------------- #
# 5. Budget / seeds
# --------------------------------------------------------------------------- #

def test_configuration_count_32():
    cfgs = m1.all_configurations()
    assert len(cfgs["regularized_logistic_regression"]) == 4
    assert len(cfgs["random_forest"]) == 12
    assert len(cfgs["xgboost"]) == 16
    assert sum(len(v) for v in cfgs.values()) == 32


def test_config_budget_mutation_fails():
    cfgs = m1.all_configurations()
    cfgs["xgboost"] = cfgs["xgboost"][:-1]  # grid contraction
    with pytest.raises(m1.QCFail):
        m1.validate_config_budget(cfgs)


def test_grid_expansion_fails():
    cfgs = m1.all_configurations()
    cfgs["random_forest"] = cfgs["random_forest"] + [cfgs["random_forest"][0]]
    with pytest.raises(m1.QCFail):
        m1.validate_config_budget(cfgs)


def test_seed_mutation_fails():
    with pytest.raises(m1.QCFail):
        m1.validate_seeds((1, 2, 3), m1.FINAL_OOF_SEEDS)
    with pytest.raises(m1.QCFail):
        m1.validate_seeds(m1.TUNING_SEEDS, (1, 2, 3, 4, 5))


def test_seeds_locked():
    assert m1.TUNING_SEEDS == (20260719, 20260720, 20260721)
    assert m1.FINAL_OOF_SEEDS == (
        20260719, 20260720, 20260721, 20260722, 20260723
    )


def test_early_stopping_and_grid_expansion_prohibited():
    budget = _read_json(
        REPO_ROOT / "project/stage125/part4_hyperparameter_budget_stage125.json"
    )
    m1.validate_no_early_stopping_or_grid_expansion(budget)
    with pytest.raises(m1.QCFail):
        m1.validate_no_early_stopping_or_grid_expansion(
            {**budget, "early_stopping_authorized": True}
        )
    with pytest.raises(m1.QCFail):
        m1.validate_no_early_stopping_or_grid_expansion(
            {**budget, "grid_expansion_after_results_authorized": True}
        )


def test_random_split_and_shuffle_prohibited():
    contract = _read_json(REPO_ROOT / m1.PART4_SPLIT_CONTRACT_REL)
    m1.validate_no_random_split(contract)
    with pytest.raises(m1.QCFail):
        m1.validate_no_random_split({**contract, "random_split_authorized": True})
    with pytest.raises(m1.QCFail):
        m1.validate_no_random_split({**contract, "shuffle_authorized": True})


# --------------------------------------------------------------------------- #
# 6. Preprocessing (training-only) — unit
# --------------------------------------------------------------------------- #

def test_preprocessing_fit_uses_training_only():
    import numpy as np
    train = np.array([[1.0], [2.0], [3.0], [100.0], [np.nan]])
    pre = m1.fit_preprocessor(train, standardize=False)
    # median from clipped observed TRAINING values only
    assert pre["median"][0] == np.median(np.clip(
        np.array([1.0, 2.0, 3.0, 100.0]), pre["p_low"][0], pre["p_high"][0]))
    # a validation array with different distribution must NOT change the params
    val = np.array([[10.0], [np.nan]])
    out = m1.transform(val, pre)
    # missing imputed with the TRAINING median, not any validation statistic
    assert out[1, 0] == pre["median"][0]


def test_missingness_indicator_from_own_row_not_standardized():
    import numpy as np
    train = np.array([[1.0], [2.0], [3.0], [np.nan]])
    pre = m1.fit_preprocessor(train, standardize=True)
    out = m1.transform(train, pre)
    # 1 continuous + 1 indicator
    assert out.shape[1] == 2
    # indicator column is 0/1 only (never standardized)
    assert set(np.unique(out[:, 1]).tolist()) <= {0.0, 1.0}
    assert out[3, 1] == 1.0
    assert out[0, 1] == 0.0


def test_log_total_assets_transformation():
    import math
    feats = m1._derive_features({
        "total_assets": "1000",
        "leverage_ratio": "0.5", "current_ratio": "1.2",
        "roa_period_adjusted": "0.1", "ocf_to_assets_period_adjusted": "0.2",
        "asset_turnover_period_adjusted": "0.3",
        "operating_margin_period_adjusted": "0.4",
        "financial_expense_to_assets_period_adjusted": "-0.05",
        "accumulated_loss_to_capital_ratio": "0.0",
    })
    assert abs(feats[0] - math.log(1000)) < 1e-12


def test_log_total_assets_nonpositive_missing():
    import math
    feats = m1._derive_features({
        "total_assets": "0",
        "leverage_ratio": "", "current_ratio": "",
        "roa_period_adjusted": "", "ocf_to_assets_period_adjusted": "",
        "asset_turnover_period_adjusted": "",
        "operating_margin_period_adjusted": "",
        "financial_expense_to_assets_period_adjusted": "",
        "accumulated_loss_to_capital_ratio": "",
    })
    assert math.isnan(feats[0])


# --------------------------------------------------------------------------- #
# 7. Committed OOF predictions
# --------------------------------------------------------------------------- #

def test_oof_row_counts():
    rows = _read_csv(STAGE_DIR / m1.F_OOF)
    assert len(rows) == 1263
    per_family: dict[str, int] = {}
    for r in rows:
        per_family[r["model_family"]] = per_family.get(r["model_family"], 0) + 1
    for fam in m1.ALLOWED_MODEL_FAMILIES:
        assert per_family[fam] == 421


def test_oof_only_validation_folds_and_no_final_test():
    rows = _read_csv(STAGE_DIR / m1.F_OOF)
    for r in rows:
        assert r["temporal_fold"] in ("fold1_validation", "fold2_validation")
        assert int(r["target_year"]) in (1396, 1397, 1398, 1399)
        assert int(r["target_year"]) not in m1.FINAL_TEST_TARGET_YEARS


def test_oof_no_final_test_key(allowlist):
    denylist = allowlist["denylist_pairs"]
    rows = _read_csv(STAGE_DIR / m1.F_OOF)
    for r in rows:
        key = (r["predictor_row_key_t"], r["target_row_key_t_plus_1"])
        assert key not in denylist


def test_oof_pooled_class_counts():
    rows = _read_csv(STAGE_DIR / m1.F_OOF)
    rf = [r for r in rows if r["model_family"] == "random_forest"]
    pos = sum(1 for r in rf if r["observed_target"] == "1")
    neg = sum(1 for r in rf if r["observed_target"] == "0")
    assert pos == 35
    assert neg == 386


def test_final_test_key_in_oof_fails(allowlist):
    denylist_key = next(iter(allowlist["denylist_pairs"]))
    bad = [{
        "predictor_row_key_t": denylist_key[0],
        "target_row_key_t_plus_1": denylist_key[1],
        "temporal_fold": "fold1_validation",
        "target_year": 1396, "model_family": "random_forest",
    }]
    with pytest.raises(m1.FinalTestLockError):
        m1._assert_oof(bad, allowlist)


def test_final_test_year_in_oof_fails(allowlist):
    bad = [{
        "predictor_row_key_t": "x|1399",
        "target_row_key_t_plus_1": "x|1400",
        "temporal_fold": "fold2_validation",
        "target_year": 1400, "model_family": "random_forest",
    }]
    with pytest.raises(m1.FinalTestLockError):
        m1._assert_oof(bad, allowlist)


# --------------------------------------------------------------------------- #
# 8. Committed metrics / selection / registry
# --------------------------------------------------------------------------- #

def test_metrics_present_for_each_scope():
    rows = _read_csv(STAGE_DIR / m1.F_METRICS)
    scopes = {(r["model_family"], r["scope"]) for r in rows}
    for fam in m1.ALLOWED_MODEL_FAMILIES:
        assert (fam, "fold1_validation") in scopes
        assert (fam, "fold2_validation") in scopes
        assert (fam, "pooled_development_oof") in scopes
    for r in rows:
        for col in ("pr_auc", "roc_auc", "brier_score",
                    "recall_at_10pct", "lift_at_10pct"):
            assert r[col] != ""


def test_pooled_metrics_row_counts():
    rows = _read_csv(STAGE_DIR / m1.F_METRICS)
    for r in rows:
        if r["scope"] == "pooled_development_oof":
            assert int(r["n_rows"]) == 421
            assert int(r["n_positive"]) == 35


def test_selected_one_per_family():
    sel = _read_json(STAGE_DIR / m1.F_SELECTED)
    assert set(sel) == set(m1.ALLOWED_MODEL_FAMILIES)
    for fam in m1.ALLOWED_MODEL_FAMILIES:
        assert sel[fam]["configuration_id"]


def test_configuration_registry_has_32_per_family():
    rows = _read_csv(STAGE_DIR / m1.F_CONFIG_REGISTRY)
    per_family: dict[str, int] = {}
    selected: dict[str, int] = {}
    for r in rows:
        per_family[r["model_family"]] = per_family.get(r["model_family"], 0) + 1
        if r["selected"] == "true":
            selected[r["model_family"]] = selected.get(r["model_family"], 0) + 1
    assert per_family["regularized_logistic_regression"] == 4
    assert per_family["random_forest"] == 12
    assert per_family["xgboost"] == 16
    assert sum(per_family.values()) == 32
    for fam in m1.ALLOWED_MODEL_FAMILIES:
        assert selected[fam] == 1


def test_tuning_results_fold_seed_rows():
    rows = _read_csv(STAGE_DIR / m1.F_TUNING)
    # 32 configs * 2 folds * 3 seeds = 192 rows
    assert len(rows) == 192
    for r in rows:
        assert r["temporal_fold"] in ("fold1_validation", "fold2_validation")
        assert int(r["seed"]) in m1.TUNING_SEEDS


# --------------------------------------------------------------------------- #
# 9. Final-test lock guard + dev lock + no refit / SMOTE / SHAP
# --------------------------------------------------------------------------- #

def test_lock_guard_zero_loaded():
    g = _read_json(STAGE_DIR / m1.F_LOCK_GUARD)
    assert g["final_test_predictor_rows_loaded"] == 0
    assert g["final_test_target_rows_loaded"] == 0
    assert g["final_test_locked"] is True
    assert g["final_test_unlocked"] is False
    assert g["aggregate_derived_from_row_level_targets"] is False
    assert g["final_test_aggregate"] == {"pairs": 346, "positive": 12, "negative": 334}


def test_dev_lock_no_refit_no_smote_no_shap():
    d = _read_json(STAGE_DIR / m1.F_DEV_LOCK)
    assert d["full_development_refit_performed"] is False
    assert d["smote_executed"] is False
    assert d["shap_executed"] is False
    assert d["m1_robustness_started"] is False
    assert d["m1_robustness_completed"] is False
    assert d["stage126_m1_primary_development_tuning_completed"] is True


def test_no_model_binaries_serialized():
    for pattern in ("*.joblib", "*.pkl", "*.pickle", "*.bin", "*.ubj", "*.model"):
        assert list(STAGE_DIR.glob(pattern)) == [], pattern


def test_source_has_no_smote_or_shap_imports():
    m1.assert_source_clean(REPO_ROOT)
    text = (REPO_ROOT / m1.SRC_REL).read_text(encoding="utf-8")
    body = text.split("FORBIDDEN_SOURCE_TOKENS", 1)[0]
    for tok in ("imblearn", "import shap", "shap.", "lightgbm", "catboost",
                "from sklearn.svm"):
        assert tok not in body


def test_source_has_no_random_split_or_shuffle_usage():
    text = (REPO_ROOT / m1.SRC_REL).read_text(encoding="utf-8")
    for tok in ("train_test_split", "KFold", "StratifiedKFold",
                "shuffle=True", "cross_val"):
        assert tok not in text


# --------------------------------------------------------------------------- #
# 10. QC report + network
# --------------------------------------------------------------------------- #

def test_qc_report_all_pass_and_no_final_test_access():
    qc = _read_json(STAGE_DIR / m1.F_QC)
    assert qc["stage"] == "stage126_m1_financial_baseline"
    assert qc["all_pass"] is True
    assert qc["failed_count"] == 0
    assert qc["network_requests_attempted"] == 0
    assert qc["final_test_predictor_rows_loaded"] == 0
    assert qc["final_test_target_rows_loaded"] == 0
    assert qc["final_test_evaluations"] == 0
    assert qc["shap_calls"] == 0
    assert qc["smote_calls"] == 0


def test_qc_handoff_markers():
    qc = _read_json(STAGE_DIR / m1.F_QC)
    assert qc["stage126_authorized"] is True
    assert qc["stage126_started"] is True
    assert qc["modeling_started"] is True
    assert qc["modeling_authorized"] is True
    assert qc["development_modeling_authorized"] is True
    assert qc["final_test_unlocked"] is False
    assert qc["final_test_access_authorized"] is False
    assert qc["final_test_evaluation_performed"] is False
    assert qc["m1_primary_development_tuning_completed"] is True
    assert qc["m1_robustness_started"] is False
    assert qc["m2_data_collected"] is False
    assert qc["m3_data_collected"] is False
    assert qc["m4_data_collected"] is False


# --------------------------------------------------------------------------- #
# 11. Full deterministic integration (refits models; verifies zero drift)
# --------------------------------------------------------------------------- #

@pytest.mark.skipif(
    os.environ.get("STAGE126_SKIP_INTEGRATION") == "1",
    reason="integration refit skipped by env",
)
def test_full_run_check_is_deterministic_and_clean():
    result = m1.run(project_dir=PROJECT_DIR, build=False, check=True)
    assert result["qc"]["all_pass"] is True
    assert result["qc"]["failed_count"] == 0
    assert result["drift"] == []
    assert result["network_requests_attempted"] == 0
