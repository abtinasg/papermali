"""Stage129 — the one-time Full-Development Refit EXECUTION.

This is the only action in the programme that fits a model outside the locked
development tuning, so the tests are the inverse of the usual ones: instead of
proving nothing ran, they prove that EXACTLY the contracted thing ran.

Pinned hardest:

  * exactly one fit, of exactly the selected model, on exactly 1393-1399;
  * the fit set is the 666-row development union with the locked 68/598 events
    - never the 1012-row full sample and never the 421-row pooled OOF surface;
  * preprocessing was re-estimated on that one fit set, and FC07's
    clip-before-impute ordering is re-proved here independently;
  * all twelve controls ran and passed;
  * the Final Test was never read and stays locked and unauthorized;
  * the locked primary development results are byte-identical;
  * the run is reproducible - re-running the executor yields byte-identical
    artifacts.

The executor itself is also exercised against tampered inputs, and every
tampering must raise `AbortRefit` rather than silently degrade.
"""
import copy
import hashlib
import json
import os
import re
import subprocess
import sys

import numpy as np
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "project", "scripts"))
sys.path.insert(0, os.path.join(REPO_ROOT, "project"))

_PKG_REL = "project/stage129/full_development_refit_execution"
_PKG = os.path.join(REPO_ROOT, _PKG_REL)
_MODEL = f"{_PKG_REL}/stage129_full_development_refit_model.json"
_PRE = f"{_PKG_REL}/stage129_full_development_refit_preprocessing_parameters.json"
_PROV = f"{_PKG_REL}/stage129_full_development_refit_provenance_record.json"
_QC = f"{_PKG_REL}/stage129_full_development_refit_qc_report.json"
_BND = (f"{_PKG_REL}/"
        "stage129_full_development_refit_execution_governance_boundary.json")
_CONTRACT_REL = ("project/stage129/full_development_refit_contract_lock/"
                 "stage129_full_development_refit_contract.json")

ACTION_ID = "stage129-full-development-refit-execution"
BLOCK = "M1"
ALGORITHM = "regularized_logistic_regression"
CONFIGURATION = "logistic__C_0.1"
FIT_YEARS = [1393, 1394, 1395, 1396, 1397, 1398, 1399]
FINAL_TEST_YEARS = [1400, 1401, 1402]
EXPECTED_ROWS = 666
EXPECTED_POSITIVE = 68
EXPECTED_NEGATIVE = 598
DESIGN_COLUMNS = 18
FC_IDS = [f"FC{i:02d}" for i in range(1, 13)]
FEATURES = [
    "log_total_assets", "leverage_ratio", "current_ratio", "roa_period_adjusted",
    "ocf_to_assets_period_adjusted", "asset_turnover_period_adjusted",
    "operating_margin_period_adjusted",
    "financial_expense_to_assets_period_adjusted",
    "accumulated_loss_to_capital_ratio",
]
NEXT_ACTION = "human_authorization_required_for_final_test_access"


def _load(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def _text(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def model():
    return _load(_MODEL)


@pytest.fixture(scope="module")
def pre():
    return _load(_PRE)


@pytest.fixture(scope="module")
def prov():
    return _load(_PROV)


@pytest.fixture(scope="module")
def qc():
    return _load(_QC)


@pytest.fixture(scope="module")
def boundary():
    return _load(_BND)


@pytest.fixture(scope="module")
def state():
    return _load("project/docs/ai/handoff_state.json")


@pytest.fixture(scope="module")
def roadmap_front_matter():
    text = _text("project/docs/ai/ROADMAP.md")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    assert m, "ROADMAP.md must carry YAML front matter"
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.strip().startswith("#"):
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


# ------------------------------------------------- exactly one, exactly this
def test_exactly_one_model_was_fitted(qc, prov, boundary, state,
                                      roadmap_front_matter):
    assert qc["model_fits_executed"] == 1
    assert prov["model_fits_executed"] == 1
    assert boundary["counters"]["model_fits"] == 1
    assert state["stage129_refit_model_fits_executed"] == 1
    assert roadmap_front_matter["refit_execution_model_fits"] == "1"


def test_the_model_fitted_is_the_selected_one(model, boundary, state):
    assert model["block"] == BLOCK == state["final_development_block"]
    assert model["algorithm"] == ALGORITHM == state["final_algorithm"]
    assert model["configuration_id"] == CONFIGURATION == state["final_configuration"]
    hp = model["hyperparameters"]
    assert hp["C"] == 0.1
    assert hp["penalty"] == "l2"
    assert hp["solver"] == "liblinear"
    assert hp["max_iter"] == 5000
    assert hp["class_weight"] == "balanced"
    assert boundary["final_model_reselected_by_this_action"] is False
    assert boundary["retuning_authorized"] is False
    # and they equal the retained design freeze
    freeze = _load("project/stage126/stage126_m1_retained_design_freeze.json")
    frozen = freeze["retained_model_families"][CONFIGURATION]
    assert frozen["family"] == ALGORITHM
    for k, v in frozen["hyperparameters"].items():
        assert hp[k] == v, k


def test_the_fit_set_is_the_development_window_with_locked_counts(
        model, prov, state, roadmap_front_matter):
    fit = model["fit_set"]
    assert fit["target_years"] == FIT_YEARS
    assert fit["rows"] == EXPECTED_ROWS
    assert fit["positive"] == EXPECTED_POSITIVE
    assert fit["negative"] == EXPECTED_NEGATIVE
    assert fit["positive"] + fit["negative"] == fit["rows"]
    d = prov["fit_set_definition"]
    assert d["target_years"] == FIT_YEARS
    assert d["rows"] == EXPECTED_ROWS
    assert d["sample"] == "main_rule_a_primary"
    assert d["target"] == "FD_target_main_t_plus_1"
    assert state["stage129_refit_fit_set_rows"] == EXPECTED_ROWS
    assert roadmap_front_matter["refit_execution_fit_set_rows"] == str(EXPECTED_ROWS)
    # these are the locked development counts, not the full sample or the OOF surface
    from src import stage126_m1_primary_development_tuning as dev
    assert EXPECTED_ROWS == dev.EXPECTED_DEV_ROWS
    assert EXPECTED_POSITIVE == dev.EXPECTED_DEV_POSITIVE
    assert EXPECTED_NEGATIVE == dev.EXPECTED_DEV_NEGATIVE
    assert EXPECTED_ROWS != dev.EXPECTED_ALL_PRIMARY_ROWS      # not 1012
    assert EXPECTED_ROWS != dev.EXPECTED_POOLED_OOF_ROWS       # not 421


def test_the_design_matrix_is_nine_continuous_plus_nine_indicators(model, state):
    assert model["n_design_columns"] == DESIGN_COLUMNS
    assert len(model["coefficients"]) == DESIGN_COLUMNS
    cols = model["design_matrix_columns"]
    assert len(cols) == DESIGN_COLUMNS
    assert cols[:9] == FEATURES
    assert cols[9:] == [f"{f}__missing" for f in FEATURES]
    assert state["stage129_refit_design_columns"] == DESIGN_COLUMNS
    assert isinstance(model["intercept"], float)
    assert all(isinstance(c, float) for c in model["coefficients"])
    assert all(np.isfinite(model["coefficients"]))
    assert np.isfinite(model["intercept"])
    assert model["classes"] == [0, 1]


def test_the_prohibited_growth_feature_is_absent(model):
    from src import stage126_m1_primary_development_tuning as dev
    for col in model["design_matrix_columns"]:
        assert dev.PROHIBITED_FEATURE not in col, col


# ------------------------ preprocessing re-estimated on THIS fit set only
def test_preprocessing_was_estimated_on_the_single_fit_set(pre, state):
    assert pre["estimated_on"] == "the_single_full_development_fit_set_1393_1399"
    assert "Nothing was carried over from a development fold." in pre[
        "estimated_on_note"]
    assert pre["feature_order"] == FEATURES
    assert pre["clip_percentiles"] == [1, 99]
    assert pre["standardization_applied"] is True
    assert pre["missingness_indicators_standardized"] is False
    for field in ("clip_lower_1st_percentile", "clip_upper_99th_percentile",
                  "median_of_clipped_observed", "standardization_mean",
                  "standardization_std"):
        assert len(pre[field]) == 9, field
        assert all(np.isfinite(pre[field])), field
    assert all(s > 0 for s in pre["standardization_std"])
    assert state["stage129_refit_preprocessing_estimated_on_fit_set_only"] is True


def test_the_pipeline_order_matches_the_frozen_contract(pre):
    frozen = _load("project/stage125/part4_preprocessing_contract_stage125.json")
    assert pre["pipeline_order"] == frozen["continuous_pipeline_order"]


def test_clipping_bounds_bracket_the_medians(pre):
    """A cheap structural invariant of clip-before-impute: the median of the
    CLIPPED observed values must lie inside the clipping bounds."""
    for lo, med, hi in zip(pre["clip_lower_1st_percentile"],
                           pre["median_of_clipped_observed"],
                           pre["clip_upper_99th_percentile"]):
        assert lo <= med <= hi, (lo, med, hi)


def test_fc07_ordering_is_reproved_independently_of_the_executor():
    """Re-derive the clip bounds and the median-of-clipped-observed straight
    from the raw fit set and compare to the committed parameters. If imputation
    had preceded clipping the medians would differ."""
    from src import stage126_m1_primary_development_tuning as dev
    from pathlib import Path
    allow = dev.build_development_allowlist(Path(REPO_ROOT))
    loaded = dev.load_development_values(Path(REPO_ROOT), allow)
    rows = loaded["rows"]
    keys = sorted(rows)
    raw = np.vstack([rows[k]["features"] for k in keys])
    assert raw.shape == (EXPECTED_ROWS, 9)
    committed = _load(_PRE)
    for j in range(9):
        col = raw[:, j]
        obs = col[~np.isnan(col)]
        lo = float(np.percentile(obs, 1))
        hi = float(np.percentile(obs, 99))
        med = float(np.median(np.clip(obs, lo, hi)))
        assert np.isclose(lo, committed["clip_lower_1st_percentile"][j]), j
        assert np.isclose(hi, committed["clip_upper_99th_percentile"][j]), j
        assert np.isclose(med, committed["median_of_clipped_observed"][j]), j
    # and the loader saw zero final-test values
    assert loaded["final_test_values_loaded"] == 0


# ------------------------------------------- all twelve controls ran and passed
def test_all_twelve_controls_ran_and_passed(qc, boundary, state,
                                            roadmap_front_matter):
    controls = qc["controls"]
    assert [c["id"] for c in controls] == FC_IDS
    for c in controls:
        assert c["result"] == "PASS", c["id"]
        assert c["detail"].strip(), c["id"]
    assert qc["all_pass"] is True
    assert boundary["fail_closed_controls_all_passed"] is True
    assert boundary["fail_closed_controls_evaluated"] == 12
    assert state["stage129_refit_controls_all_passed"] is True
    assert state["stage129_refit_controls_evaluated"] == 12
    assert roadmap_front_matter["refit_execution_controls_all_passed"] == "true"


# ---------------------------------------------- the Final Test was never touched
def test_no_final_test_row_predictor_target_prediction_or_metric(
        qc, prov, boundary, state, roadmap_front_matter):
    counters = qc["final_test_counters"]
    for key in ("final_test_rows_read", "final_test_rows_loaded",
                "final_test_predictor_values_read",
                "final_test_target_values_read", "final_test_predictions",
                "final_test_metrics_computed"):
        assert counters[key] == 0, key
        assert boundary["counters"][key] == 0, key
    assert prov["final_test_rows_read"] == 0
    assert prov["final_test_target_years_excluded"] == FINAL_TEST_YEARS
    assert state["final_test_rows_read"] == 0
    assert state["stage129_refit_execution_final_test_rows_read"] == 0
    assert roadmap_front_matter["refit_execution_final_test_rows_read"] == "0"


def test_the_fit_set_and_the_final_test_years_are_disjoint(model):
    assert set(model["fit_set"]["target_years"]).isdisjoint(FINAL_TEST_YEARS)
    assert max(model["fit_set"]["target_years"]) < min(FINAL_TEST_YEARS)
    assert model["final_test_used"] is False


def test_the_final_test_stays_locked_and_unauthorized(boundary, state):
    assert boundary["final_test_locked"] is True
    assert boundary["final_test_access_authorized"] is False
    assert boundary["final_test_unlock_authorized"] is False
    assert boundary["final_test_rows_read"] == 0
    assert state["final_test_locked"] is True
    assert state["final_test_access_authorized"] is False
    assert state["stage129_refit_execution_final_test_locked"] is True


# ------------------------------------------------------- nothing else happened
def test_no_new_scientific_result_was_produced(qc, model, boundary, state,
                                               roadmap_front_matter):
    for field in ("new_metric_computed", "new_p_value_computed",
                  "bootstrap_executed", "recalibration_executed",
                  "shap_executed"):
        assert qc[field] is False, field
    assert qc["predictions_generated"] == 0
    assert model["predictions_generated"] == 0
    assert boundary["new_scientific_result_produced"] is False
    assert boundary["inferential_superiority_claimed"] is False
    assert state["stage129_refit_new_scientific_result_produced"] is False
    assert state["stage129_refit_predictions_generated"] == 0
    assert roadmap_front_matter[
        "refit_execution_new_scientific_result_produced"] == "false"
    for key in ("tuning_runs", "feature_searches", "threshold_searches",
                "bootstrap_executions", "recalibration_executions",
                "shap_executions", "holm_executions", "p_values_computed",
                "confidence_intervals_computed",
                "new_scientific_metrics_computed"):
        assert boundary["counters"][key] == 0, key


def test_the_locked_primary_results_are_byte_identical(qc, boundary):
    before = qc["locked_results_sha256_before"]
    after = qc["locked_results_sha256_after"]
    assert before and before == after
    for rel, want in before.items():
        path = os.path.join(REPO_ROOT, rel)
        assert os.path.isfile(path), rel
        with open(path, "rb") as fh:
            assert hashlib.sha256(fh.read()).hexdigest() == want, rel
    assert boundary["locked_primary_development_results_modified_by_this_action"] is False
    assert boundary["m1_results_modified_by_this_action"] is False
    # the locked pooled PR-AUC is untouched by the refit
    lock = _load("project/stage126/stage126_m1_primary_development_lock.json")
    assert lock["pooled_oof_pr_auc"][ALGORITHM] == 0.445756964048


def test_no_stage130_and_no_holm_change(boundary, state):
    assert boundary["stage130_started"] is False
    assert boundary["stage130_authorized"] is False
    assert boundary["holm_family_complete"] is False
    assert boundary["holm_reporting_status"] == (
        "HOLM_NOT_EXECUTED_FAMILY_PRESERVED_NO_INFERENCE")
    assert state["stage130_started"] is False
    assert state["holm_family_complete"] is False
    assert state["stage129_final_holm_reporting_status"] == (
        "HOLM_NOT_EXECUTED_FAMILY_PRESERVED_NO_INFERENCE")


def test_nothing_historical_was_modified(boundary):
    for field in ("historical_scientific_artifacts_modified_by_this_action",
                  "prior_packages_modified_by_this_action",
                  "existing_pull_requests_modified_by_this_action",
                  "m2_status_modified_by_this_action",
                  "m3_cbi_disposition_modified_by_this_action",
                  "m4_disposition_modified_by_this_action",
                  "m3_lag_wdi_promoted_to_confirmatory_model",
                  "pipeline_reimplemented_by_this_action"):
        assert boundary[field] is False, field


def test_the_pointer_authorizes_nothing(boundary, state, roadmap_front_matter):
    assert boundary["next_action_id"] == NEXT_ACTION
    assert boundary["next_action_authorized"] is False
    assert boundary["next_action_executes_final_test"] is False
    assert boundary["pointer_is_not_authorization"] is True
    assert boundary["next_research_action_authorized"] is False
    assert state["stage129_refit_execution_next_action_id"] == NEXT_ACTION
    assert state["stage129_refit_execution_next_action_authorized"] is False
    assert roadmap_front_matter["refit_execution_next_action_authorized"] == "false"


# ------------------------------------------------- provenance and reproducibility
def test_the_provenance_pins_the_contract_inputs_and_pipeline(prov):
    assert prov["contract_path"] == _CONTRACT_REL
    with open(os.path.join(REPO_ROOT, _CONTRACT_REL), "rb") as fh:
        assert hashlib.sha256(fh.read()).hexdigest() == prov["contract_sha256"]
    for rel, want in prov["input_sha256"].items():
        path = os.path.join(REPO_ROOT, rel)
        assert os.path.isfile(path), rel
        with open(path, "rb") as fh:
            assert hashlib.sha256(fh.read()).hexdigest() == want, rel
    # the pinned inputs really are the contract's pinned inputs
    contract = _load(_CONTRACT_REL)
    data = contract["authorized_development_data"]
    assert prov["input_sha256"][data["analysis_ready_path"]] == \
        data["analysis_ready_sha256"]
    assert prov["input_sha256"][data["audited_pairs_path"]] == \
        data["audited_pairs_sha256"]
    # the pipeline module is pinned and was reused, not reimplemented
    assert prov["pipeline_reused_not_reimplemented"] is True
    mod = prov["pipeline_source_module"]
    with open(os.path.join(REPO_ROOT, mod), "rb") as fh:
        assert hashlib.sha256(fh.read()).hexdigest() == prov["pipeline_source_sha256"]


def test_the_runtime_matches_the_contract(prov):
    contract = _load(_CONTRACT_REL)
    assert prov["runtime_versions"] == contract["environment"]["runtime_versions"]


def test_rerunning_the_executor_reproduces_the_artifacts_byte_for_byte():
    """The refit is deterministic. Re-deriving in memory (no write) must yield
    exactly the committed bytes."""
    from src import stage129_full_development_refit as refit
    result = refit.run(REPO_ROOT, write=False)
    for name, info in result["hashes"].items():
        path = os.path.join(_PKG, name)
        assert os.path.isfile(path), name
        with open(path, "rb") as fh:
            blob = fh.read()
        assert hashlib.sha256(blob).hexdigest() == info["sha256"], name
        assert len(blob) == info["bytes"], name


def test_the_model_serialization_is_not_a_pickle(model):
    assert model["serialization"] == "explicit_coefficients_not_a_pickle"
    manifest = _load(f"{_PKG_REL}/"
                     "metadata_and_hashes_stage129_full_development_refit_execution.json")
    assert manifest["pickle_or_binary_model_committed"] is False


def test_no_new_seed_was_introduced(model):
    from src import stage126_m1_primary_development_tuning as dev
    assert model["random_state"] in dev.FINAL_OOF_SEEDS
    assert "No new seed was introduced." in model["random_state_note"]


# --------------------------------------------- the executor fails closed
@pytest.fixture
def sandbox(tmp_path):
    """A repo copy sufficient for the executor, so tampering can be tested."""
    import shutil
    needed_dirs = [
        "project/src",
        "project/stage129/full_development_refit_contract_lock",
    ]
    needed_files = [
        "project/stage125/part3c_outputs/analysis_ready_main_rule_a_stage125.csv",
        "project/stage125/part3c_outputs/audited_pairs_main_rule_a_stage125.csv",
        "project/stage125/part4_temporal_split_manifest_stage125.csv",
        "project/stage126/stage126_m1_primary_development_lock.json",
        "project/stage126/stage126_m1_development_metrics.csv",
        "project/stage126/stage126_m1_selected_configurations.json",
        "project/stage126/stage126_m1_development_oof_predictions.csv",
    ]
    for d in needed_dirs:
        shutil.copytree(os.path.join(REPO_ROOT, d), tmp_path / d,
                        ignore=shutil.ignore_patterns("__pycache__"))
    for f in needed_files:
        dst = tmp_path / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(os.path.join(REPO_ROOT, f), dst)
    # upstream artifacts the dev module pins/reads
    for extra in _load(
            "project/stage129/full_development_refit_contract_lock/"
            "stage129_full_development_refit_source_provenance.json"
    )["source_artifacts_sha256"]:
        dst = tmp_path / extra
        if dst.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(os.path.join(REPO_ROOT, extra), dst)
    return tmp_path


def _run_in(root):
    from src import stage129_full_development_refit as refit
    return refit.run(root, write=False)


def test_the_sandbox_baseline_runs_clean(sandbox):
    """The tamper tests below are only meaningful if the untampered copy runs."""
    result = _run_in(sandbox)
    qc = result["artifacts"]["stage129_full_development_refit_qc_report.json"]
    assert qc["all_pass"] is True
    assert qc["model_fits_executed"] == 1


def test_a_tampered_input_file_aborts(sandbox):
    from src import stage129_full_development_refit as refit
    p = sandbox / "project/stage125/part3c_outputs/analysis_ready_main_rule_a_stage125.csv"
    p.write_bytes(p.read_bytes() + b"\n")
    with pytest.raises(refit.AbortRefit) as exc:
        _run_in(sandbox)
    assert "FC01" in str(exc.value)


def test_a_final_test_year_in_the_contract_fit_window_aborts(sandbox):
    from src import stage129_full_development_refit as refit
    rel = ("project/stage129/full_development_refit_contract_lock/"
           "stage129_full_development_refit_contract.json")
    blob = json.loads((sandbox / rel).read_text(encoding="utf-8"))
    blob["authorized_development_data"]["fit_target_years"] = FIT_YEARS + [1400]
    (sandbox / rel).write_text(json.dumps(blob, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    with pytest.raises(refit.AbortRefit) as exc:
        _run_in(sandbox)
    assert "FC03" in str(exc.value)


@pytest.mark.parametrize("mutation,control", [
    ({"selected_model": {"block": "M2", "algorithm": ALGORITHM,
                         "configuration_id": CONFIGURATION,
                         "hyperparameters": {"C": 0.1, "max_iter": 5000,
                                             "penalty": "l2",
                                             "solver": "liblinear"},
                         "retuning_authorized": False,
                         "hyperparameter_search_authorized": False,
                         "grid_expansion_after_results_authorized": False}}, "FC05"),
    ({"contract_status": "EXECUTED"}, "FC01"),
])
def test_a_tampered_contract_aborts(sandbox, mutation, control):
    from src import stage129_full_development_refit as refit
    rel = ("project/stage129/full_development_refit_contract_lock/"
           "stage129_full_development_refit_contract.json")
    blob = json.loads((sandbox / rel).read_text(encoding="utf-8"))
    blob.update(mutation)
    (sandbox / rel).write_text(json.dumps(blob, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    with pytest.raises(refit.AbortRefit) as exc:
        _run_in(sandbox)
    assert control in str(exc.value)


def test_a_wrong_feature_order_aborts(sandbox):
    from src import stage129_full_development_refit as refit
    rel = ("project/stage129/full_development_refit_contract_lock/"
           "stage129_full_development_refit_contract.json")
    blob = json.loads((sandbox / rel).read_text(encoding="utf-8"))
    blob["features"]["features_exact_order"] = list(reversed(FEATURES))
    (sandbox / rel).write_text(json.dumps(blob, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    with pytest.raises(refit.AbortRefit) as exc:
        _run_in(sandbox)
    assert "FC04" in str(exc.value)


def test_authorizing_a_search_aborts(sandbox):
    from src import stage129_full_development_refit as refit
    rel = ("project/stage129/full_development_refit_contract_lock/"
           "stage129_full_development_refit_contract.json")
    blob = json.loads((sandbox / rel).read_text(encoding="utf-8"))
    blob["selected_model"]["hyperparameter_search_authorized"] = True
    (sandbox / rel).write_text(json.dumps(blob, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    with pytest.raises(refit.AbortRefit) as exc:
        _run_in(sandbox)
    assert "FC08" in str(exc.value)


def test_moving_the_threshold_off_development_oof_aborts(sandbox):
    from src import stage129_full_development_refit as refit
    rel = ("project/stage129/full_development_refit_contract_lock/"
           "stage129_full_development_refit_contract.json")
    blob = json.loads((sandbox / rel).read_text(encoding="utf-8"))
    blob["threshold"]["rule"] = "refit_in_sample_F2_threshold"
    (sandbox / rel).write_text(json.dumps(blob, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    with pytest.raises(refit.AbortRefit) as exc:
        _run_in(sandbox)
    assert "FC11" in str(exc.value)


def test_fc12_rejects_any_count_other_than_one():
    from src import stage129_full_development_refit as refit
    for n in (0, 2, 3):
        with pytest.raises(refit.AbortRefit) as exc:
            refit.fc12_exactly_one_fit(n)
        assert "FC12" in str(exc.value)
    refit.fc12_exactly_one_fit(1)          # the only permitted count


def test_fc07_rejects_a_median_that_was_not_clipped_first():
    """Directly exercise the ordering control with a preprocessor whose median
    was computed on unclipped values."""
    from src import stage129_full_development_refit as refit
    rng = np.random.default_rng(0)
    X = rng.normal(size=(200, 3))
    X[0, 0] = 1e6                                   # an outlier clipping removes
    good = {"p_low": np.percentile(X, 1, axis=0),
            "p_high": np.percentile(X, 99, axis=0)}
    good["median"] = np.array([
        np.median(np.clip(X[:, j], good["p_low"][j], good["p_high"][j]))
        for j in range(3)])
    refit.fc07_clipping_before_imputation(good, X)   # passes
    bad = dict(good)
    bad["median"] = np.median(X, axis=0) + 1.0       # not the clipped median
    with pytest.raises(refit.AbortRefit) as exc:
        refit.fc07_clipping_before_imputation(bad, X)
    assert "FC07" in str(exc.value)


def test_fc09_rejects_any_loaded_final_test_value():
    from src import stage129_full_development_refit as refit
    with pytest.raises(refit.AbortRefit) as exc:
        refit.fc09_final_test_untouched({"final_test_values_loaded": 1})
    assert "FC09" in str(exc.value)
    assert refit.fc09_final_test_untouched(
        {"final_test_values_loaded": 0})["final_test_rows_read"] == 0


def test_fc10_rejects_a_changed_locked_result(tmp_path):
    from src import stage129_full_development_refit as refit
    p = tmp_path / "locked.json"
    p.write_text("original", encoding="utf-8")
    before = {"locked.json": hashlib.sha256(b"original").hexdigest()}
    assert refit.fc10_locked_results_intact(tmp_path, before) == before
    p.write_text("tampered", encoding="utf-8")
    with pytest.raises(refit.AbortRefit) as exc:
        refit.fc10_locked_results_intact(tmp_path, before)
    assert "FC10" in str(exc.value)


# ---------------------------------------- generator, validator, idempotency
def _run_generator(root):
    import importlib
    gen = importlib.import_module("update_ai_handoff")
    return gen.derive_stage129_full_development_refit_execution_markers(root)


@pytest.mark.parametrize("rel,key,value,needle", [
    (_QC, "model_fits_executed", 2, "fits"),
    (_QC, "model_fits_executed", 0, "fits"),
    (_QC, "all_pass", False, "all controls passed"),
    (_QC, "predictions_generated", 5, "predictions"),
    (_QC, "new_metric_computed", True, "new_metric_computed"),
    (_QC, "bootstrap_executed", True, "bootstrap_executed"),
    (_QC, "shap_executed", True, "shap_executed"),
    (_QC, "recalibration_executed", True, "recalibration_executed"),
    (_BND, "final_test_locked", False, "final_test_locked"),
    (_BND, "final_test_rows_read", 1, "final_test_rows_read"),
    (_BND, "final_test_access_authorized", True, "final_test_access_authorized"),
    (_BND, "stage130_started", True, "stage130_started"),
    (_BND, "stage130_authorized", True, "stage130_authorized"),
    (_BND, "next_action_authorized", True, "next_action_authorized"),
    (_BND, "new_scientific_result_produced", True, "new_scientific_result"),
    (_BND, "retuning_authorized", True, "retune"),
    (_BND, "final_model_reselected_by_this_action", True, "re-select"),
    (_BND, "pipeline_reimplemented_by_this_action", True, "pipeline_reimplemented"),
    (_BND, "next_action_id", "stage130-final-test", "pointer must be"),
    (_MODEL, "n_design_columns", 12, "design matrix"),
    (_MODEL, "predictions_generated", 3, "predictions"),
    (_PROV, "final_test_rows_read", 2, "final_test_rows_read"),
])
def test_the_generator_fails_closed_on_tampering(tmp_path, rel, key, value, needle):
    import shutil
    import update_ai_handoff as gen
    for f in (_MODEL, _PRE, _PROV, _QC, _BND):
        dst = tmp_path / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(os.path.join(REPO_ROOT, f), dst)
    for locked in _load(_QC)["locked_results_sha256_before"]:
        dst = tmp_path / locked
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(os.path.join(REPO_ROOT, locked), dst)
    blob = json.loads((tmp_path / rel).read_text(encoding="utf-8"))
    blob[key] = value
    (tmp_path / rel).write_text(
        json.dumps(blob, ensure_ascii=False, indent=2), encoding="utf-8")
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(tmp_path))
    assert needle.lower() in str(exc.value).lower()


@pytest.mark.parametrize("year", FINAL_TEST_YEARS)
def test_the_generator_rejects_a_final_test_year_in_the_fit_set(tmp_path, year):
    import shutil
    import update_ai_handoff as gen
    for f in (_MODEL, _PRE, _PROV, _QC, _BND):
        dst = tmp_path / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(os.path.join(REPO_ROOT, f), dst)
    blob = json.loads((tmp_path / _MODEL).read_text(encoding="utf-8"))
    blob["fit_set"]["target_years"] = FIT_YEARS + [year]
    (tmp_path / _MODEL).write_text(
        json.dumps(blob, ensure_ascii=False, indent=2), encoding="utf-8")
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(tmp_path))
    assert "fit set" in str(exc.value).lower()


def test_the_generator_rejects_a_failed_control(tmp_path):
    import shutil
    import update_ai_handoff as gen
    for f in (_MODEL, _PRE, _PROV, _QC, _BND):
        dst = tmp_path / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(os.path.join(REPO_ROOT, f), dst)
    blob = json.loads((tmp_path / _QC).read_text(encoding="utf-8"))
    blob["controls"][8]["result"] = "FAIL"
    (tmp_path / _QC).write_text(
        json.dumps(blob, ensure_ascii=False, indent=2), encoding="utf-8")
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(tmp_path))
    assert "did not" in str(exc.value)


def test_validate_ai_handoff_check_passes():
    proc = subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "project/scripts/validate_ai_handoff.py"),
         "--check"],
        cwd=REPO_ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_the_generator_is_semantically_idempotent():
    import update_ai_handoff as gen
    first = gen.derive_stage129_full_development_refit_execution_markers(REPO_ROOT)
    second = gen.derive_stage129_full_development_refit_execution_markers(REPO_ROOT)
    assert first == second
    assert copy.deepcopy(first) == second
    assert first["stage129_refit_executed"] is True


def test_current_state_renders_the_execution():
    text = _text("project/docs/ai/CURRENT_STATE.md")
    assert "Full-Development Refit EXECUTED" in text
    assert "logistic__C_0.1" in text
    assert NEXT_ACTION in text


def test_the_readme_documents_the_run_in_english_and_persian():
    readme = _text(f"{_PKG_REL}/README_STAGE129_FULL_DEVELOPMENT_REFIT_EXECUTION.md")
    flat = re.sub(r"\s+", " ", readme)
    for phrase in ("all twelve fail-closed controls PASS",
                   "nothing was carried over from a development fold",
                   "explicit coefficients, not a pickle",
                   "The Final Test remains locked and unread"):
        assert phrase.lower() in flat.lower(), phrase
    for phrase in ("دقیقاً **یک** مدل", "هیچ آماره‌ای از",
                   "final_test_rows_read = 0"):
        assert phrase in flat, phrase


# --------------------------------------------------------- package hygiene
def test_no_binary_or_data_artifact_was_committed():
    names = sorted(os.listdir(_PKG))
    assert names
    for name in names:
        assert name.endswith((".json", ".md")), name
        for bad in (".pkl", ".joblib", ".parquet", ".csv", ".npy", ".bin"):
            assert not name.endswith(bad), name
    manifest = _load(f"{_PKG_REL}/"
                     "metadata_and_hashes_stage129_full_development_refit_execution.json")
    assert manifest["final_test_artifacts_committed"] == 0
    assert manifest["final_test_rows_read"] == 0
    assert manifest["model_fits_executed"] == 1
    assert manifest["fail_closed_controls_all_passed"] is True


def test_package_hash_manifest_matches_every_file():
    rel = (f"{_PKG_REL}/"
           "metadata_and_hashes_stage129_full_development_refit_execution.json")
    manifest = _load(rel)
    listed = set(manifest["package_files"])
    on_disk = {n for n in os.listdir(_PKG) if n != os.path.basename(rel)}
    assert listed == on_disk
    for name, info in manifest["package_files"].items():
        with open(os.path.join(_PKG, name), "rb") as fh:
            blob = fh.read()
        assert hashlib.sha256(blob).hexdigest() == info["sha256"], name
        assert len(blob) == info["bytes"], name
    # the executor itself is pinned
    with open(os.path.join(REPO_ROOT, manifest["executor_path"]), "rb") as fh:
        assert hashlib.sha256(fh.read()).hexdigest() == manifest["executor_sha256"]
