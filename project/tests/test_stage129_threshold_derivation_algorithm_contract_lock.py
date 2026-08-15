"""Stage129 — the prospectively locked threshold derivation algorithm.

This lock differs from its two predecessors in a way the tests have to police
directly: it is **not** a pure extraction. Six of its terms are human decisions
filling a gap the Final Test audit recorded as PRE02. The danger is therefore
not only drift, but *laundering* -- a decision quietly acquiring the authority
of a frozen rule. So these tests pin:

  * the honest provenance split. The contract must declare
    every_term_is_extracted_from_a_prelocked_artifact = false, enumerate the six
    supplied terms, and give each an untraceability reason;
  * that the frozen record really is silent on those six, checked against the
    frozen artifacts rather than taken on faith;
  * that nothing was computed. threshold_value is null, every counter is zero,
    and no probability value was read;
  * that PRE02 is NOT resolved. Defining an algorithm is not running it, and a
    lock that quietly flipped PRE02 would unblock the Final Test;
  * that the forbidden implementation stays forbidden, including the specific
    reason it is unusable -- it contradicts the locked tie-break.

The F2 closed form is checked against the F-beta identity rather than trusted
as a literal string.
"""
import hashlib
import json
import os
import re

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_PKG_REL = "project/stage129/threshold_derivation_algorithm_contract_lock"
_PKG = os.path.join(REPO_ROOT, _PKG_REL)
_CON = f"{_PKG_REL}/stage129_threshold_derivation_algorithm_contract.json"
_PROV = f"{_PKG_REL}/stage129_threshold_derivation_algorithm_source_provenance.json"
_BND = f"{_PKG_REL}/stage129_threshold_derivation_algorithm_governance_boundary.json"
_MANIFEST_NAME = ("metadata_and_hashes_stage129_threshold_derivation_algorithm"
                  "_contract_lock.json")
_MAN = f"{_PKG_REL}/{_MANIFEST_NAME}"
_README_NAME = "README_STAGE129_THRESHOLD_DERIVATION_ALGORITHM_CONTRACT_LOCK.md"

_METRICS_REL = "project/stage125/part4_metrics_uncertainty_contract_stage125.json"
_FREEZE_REL = "project/stage126/stage126_m1_retained_design_freeze.json"
_SAP_REL = "project/stage125/part4_statistical_analysis_plan_stage125.json"
_LOCK_REL = "project/stage126/stage126_m1_primary_development_lock.json"
_OOF_REL = "project/stage126/stage126_m1_development_oof_predictions.csv"
_FT_CONTRACT_REL = ("project/stage129/final_test_execution_contract_lock/"
                    "stage129_final_test_execution_contract.json")

ACTION_ID = "stage129-threshold-derivation-algorithm-contract-lock"
STATUS = "PROSPECTIVELY_LOCKED_NOT_EXECUTED"
TD_IDS = [f"TD{i:02d}" for i in range(1, 19)]
NEXT_ACTION = "human_authorization_required_for_threshold_derivation_execution"
SUPPLIED_TERMS = {
    "candidate_threshold_set_definition",
    "positive_prediction_comparison_operator",
    "f2_beta_and_closed_form_formula",
    "zero_denominator_convention",
    "no_rounding_before_selection",
    "output_precision_requirement",
}


def _load(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def _text(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def _sha256(rel):
    with open(os.path.join(REPO_ROOT, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


@pytest.fixture(scope="module")
def contract():
    return _load(_CON)


@pytest.fixture(scope="module")
def provenance():
    return _load(_PROV)


@pytest.fixture(scope="module")
def boundary():
    return _load(_BND)


@pytest.fixture(scope="module")
def manifest():
    return _load(_MAN)


# ------------------------------------------------------------------ identity
def test_contract_identity_is_a_lock_not_a_derivation(contract, boundary):
    assert contract["action_id"] == ACTION_ID == boundary["action_id"]
    assert contract["contract_id"] == "stage129_threshold_derivation_algorithm_contract"
    assert contract["contract_status"] == STATUS == boundary["contract_status"]


# ------------------------------------------- the honest provenance split
def test_the_contract_admits_it_is_not_a_pure_extraction(contract, provenance,
                                                         boundary):
    p = contract["provenance_of_terms"]
    assert p["every_term_is_extracted_from_a_prelocked_artifact"] is False
    assert p["some_terms_are_supplied_by_human_decision"] is True
    assert p["basis_for_supplied_terms"] == \
        "HUMAN_DECISION_RESOLVING_A_RECORDED_CONTRACT_GAP"
    assert p["supplied_terms_do_not_retroactively_create_a_frozen_rule"] is True
    assert boundary["every_term_is_extracted_from_a_prelocked_artifact"] is False
    assert boundary["some_terms_are_supplied_by_human_decision"] is True
    assert provenance["every_contract_term_traces_to_one_of_these_artifacts"] is False


def test_the_six_supplied_terms_are_named_everywhere_consistently(contract,
                                                                  provenance,
                                                                  boundary):
    assert set(contract["provenance_of_terms"]["human_supplied_terms"]) == SUPPLIED_TERMS
    listed = provenance["human_supplied_terms_not_traceable_to_any_frozen_artifact"]
    assert {e["term"] for e in listed} == SUPPLIED_TERMS
    assert boundary["human_supplied_term_count"] == len(SUPPLIED_TERMS) == 6
    for entry in listed:
        assert entry["value"], entry["term"]
        assert entry["why_not_traceable"].strip(), entry["term"]


def test_the_frozen_record_really_is_silent_on_the_supplied_terms():
    """Check the claim against the frozen artifacts, not against our own file."""
    blocks = [_load(_METRICS_REL)["thresholded_secondary"],
              _load(_FREEZE_REL)["metric_definitions"]["thresholded_secondary"]]
    for block in blocks:
        assert set(block) == {"never_optimize_on_final_test", "rule", "tie_break"}
    flat = json.dumps([_load(_METRICS_REL), _load(_SAP_REL), _load(_FREEZE_REL)])
    for absent in ("candidate_threshold", "threshold_grid", "grid_points",
                   "comparison_operator", "zero_denominator"):
        assert absent not in flat, absent


def test_extracted_terms_carry_their_sources(contract, provenance):
    extracted = contract["provenance_of_terms"]["extracted_terms"]
    assert len(extracted) == 8
    assert not SUPPLIED_TERMS & set(extracted), "a term cannot be both"
    src = provenance["source_artifacts_sha256"]
    assert len(src) == provenance["source_artifact_count"] == 9
    for rel, info in src.items():
        assert _sha256(rel) == info["sha256"], rel
        with open(os.path.join(REPO_ROOT, rel), "rb") as fh:
            assert len(fh.read()) == info["bytes"], rel
        assert info["supplies"].strip(), rel


def test_the_extracted_rule_and_tie_break_match_the_frozen_source(contract):
    alg = contract["algorithm"]
    frozen = _load(_METRICS_REL)["thresholded_secondary"]
    assert alg["id"] == frozen["rule"]
    assert alg["tie_break"] == frozen["tie_break"] == "higher_threshold"


# ------------------------------------------------------------- the algorithm
def test_input_is_the_pinned_development_oof_surface_only(contract):
    inp = contract["authorized_input"]
    assert inp["path"] == _OOF_REL
    assert _sha256(_OOF_REL) == inp["sha256"]
    with open(os.path.join(REPO_ROOT, _OOF_REL), "rb") as fh:
        assert len(fh.read()) == inp["bytes"]
    assert inp["row_filter"] == {
        "model_family": "regularized_logistic_regression",
        "configuration_id": "logistic__C_0.1"}
    assert inp["expected_rows_after_filter"] == \
        _load(_LOCK_REL)["pooled_oof_rows_per_family"] == 421
    assert inp["no_other_input_is_authorized"] is True
    assert inp["final_test_rows_in_input"] == 0
    # the named columns really exist in the committed header
    header = _text(_OOF_REL).splitlines()[0].split(",")
    for key in ("probability_column", "target_column", "cluster_column",
                "target_year_column"):
        assert inp[key] in header, inp[key]


def test_candidate_set_is_exactly_the_unique_stored_probabilities(contract):
    cs = contract["algorithm"]["candidate_set"]
    assert cs["is_exactly_the_unique_stored_probabilities"] is True
    for field in ("synthetic_endpoints_added", "linear_grid_used",
                  "grid_points_parameter_used",
                  "midpoints_between_consecutive_values_used"):
        assert cs[field] is False, field
    forbidden = " ".join(cs["forbidden_candidate_constructions"]).lower()
    for token in ("linspace", "endpoint", "midpoint", "union", "thinning"):
        assert token in forbidden, token


def test_comparison_operator_is_greater_or_equal(contract):
    dr = contract["algorithm"]["decision_rule"]
    assert dr["comparison_operator"] == ">="
    assert dr["positive_prediction"] == "predicted_probability >= threshold"
    assert dr["strict_greater_than_authorized"] is False


def test_f2_closed_form_matches_the_f_beta_identity(contract):
    """5TP/(5TP+4FN+FP) must be F-beta with beta=2, not a lookalike."""
    obj = contract["algorithm"]["objective"]
    beta = obj["beta"]
    assert beta == 2
    assert 1 + beta ** 2 == 5 and beta ** 2 == 4
    nums = [int(n) for n in re.findall(r"\d+", obj["closed_form"])]
    assert nums == [5, 5, 4], obj["closed_form"]
    assert obj["closed_form_is_binding"] is True
    assert obj["library_fbeta_substitution_authorized"] is False
    assert "== 0" in obj["zero_denominator_convention"]
    assert obj["counts_computed_on_evaluable_rows_only"] is True


def test_f2_closed_form_agrees_with_fbeta_on_worked_cases():
    """Independent arithmetic check of the identity the contract locks."""
    def f2_closed(tp, fn, fp):
        den = 5 * tp + 4 * fn + fp
        return 0.0 if den == 0 else 5 * tp / den

    def f_beta(tp, fn, fp, beta=2):
        den = (1 + beta ** 2) * tp + beta ** 2 * fn + fp
        return 0.0 if den == 0 else (1 + beta ** 2) * tp / den

    for tp, fn, fp in [(0, 0, 0), (5, 3, 2), (1, 0, 0), (0, 7, 1), (12, 4, 30)]:
        assert f2_closed(tp, fn, fp) == f_beta(tp, fn, fp), (tp, fn, fp)
    assert f2_closed(0, 0, 0) == 0.0


def test_tie_break_selects_the_largest_threshold(contract):
    sel = contract["algorithm"]["selection"]
    assert sel["objective_direction"] == "maximize"
    assert "LARGEST" in sel["tie_break_criterion"]
    assert sel["tie_break_direction_is_higher_not_lower"] is True
    assert sel["exactly_one_threshold_is_selected"] is True


def test_no_rounding_and_round_trip_precision(contract):
    nd = contract["algorithm"]["numeric_discipline"]
    assert nd["rounding_before_selection_authorized"] is False
    assert nd["truncation_before_selection_authorized"] is False
    assert nd["probabilities_compared_at_full_stored_precision"] is True
    assert nd["output_precision_requirement"] == "round_trip_exact"
    assert "float(str(value)) == value" in nd["output_precision_test"]


def test_round_trip_precision_rule_is_actually_satisfiable():
    """repr round-trip must hold for representative float values."""
    for v in (0.5, 0.1234567890123, 1e-17, 0.30000000000000004, 1.0, 0.0):
        assert float(str(v)) == v, v


def test_pick_threshold_is_forbidden_with_its_reason(contract, provenance):
    fi = contract["algorithm"]["forbidden_implementation"]
    entry = fi["project/src/metrics.py::pick_threshold"]
    assert entry["authorized"] is False
    reasons = " ".join(entry["reasons"]).lower()
    assert "tie-break" in reasons or "tie_break" in reasons
    assert "lowest" in reasons
    assert fi["any_other_unpinned_helper_authorized"] is False
    rej = provenance["rejected_implementation"]
    assert rej["authorized"] is False
    assert rej["referenced_by_merged_contract_count"] == 0
    assert rej["imported_by_locked_development_pipeline"] is False
    assert rej["contradicts_locked_tie_break"] is True


def test_the_rejected_helper_really_does_contradict_the_tie_break():
    """Verify the rejection reason against the file, not the claim."""
    src = _text("project/src/metrics.py")
    assert "def pick_threshold" in src
    assert "grid_points: int = 200" in src, "grid size is a default arg, not a contract"
    assert "linspace" in src
    # ascending scan with strict > keeps the FIRST (lowest) maximizer
    assert "if v > best_v" in src


def test_no_model_is_loaded_or_fitted(contract):
    m = contract["selected_model"]
    assert m["configuration_id"] == "logistic__C_0.1"
    assert m["model_is_not_refitted_by_the_derivation"] is True
    assert m["no_model_is_loaded_by_the_derivation"] is True
    assert m["derivation_reads_stored_predictions_only"] is True


def test_target_semantics_are_quoted_verbatim(contract):
    got = contract["target_semantics"]
    frozen = _load(_SAP_REL)["target_state_contract"]
    for k, v in frozen.items():
        assert got[k] == v, k
    assert got["missing_never_counted_as_negative"] is True


# ------------------------------------------------------ controls and counters
def test_all_eighteen_controls_exist_and_abort(contract):
    controls = contract["fail_closed_controls"]
    assert [c["id"] for c in controls] == TD_IDS
    for c in controls:
        assert c["on_failure"] == "ABORT_THRESHOLD_DERIVATION", c["id"]
        assert c["check"].strip()


@pytest.mark.parametrize("cid,tokens", [
    ("TD03", ("1393-1399", "1400-1402", "zero")),
    ("TD04", ("distinct", "grid", "midpoints")),
    ("TD05", (">=", "strict")),
    ("TD07", ("rounded", "truncated")),
    ("TD08", ("largest", "argmax")),
    ("TD09", ("pick_threshold",)),
    ("TD11", ("model_fits_executed == 0", "predict_proba")),
    ("TD14", ("float(str(value)) == value",)),
    ("TD16", ("final_test_rows_read == 0",)),
])
def test_key_controls_state_their_substance(contract, cid, tokens):
    check = next(c for c in contract["fail_closed_controls"] if c["id"] == cid)["check"]
    for tok in tokens:
        assert tok.lower() in check.lower(), (cid, tok)


def test_required_counters_forbid_fitting_and_final_test_access(contract):
    c = contract["required_counters"]
    for k in ("model_fits_executed", "refits_executed", "predict_proba_calls",
              "tuning_runs", "recalibration_executions", "final_test_rows_read",
              "final_test_rows_loaded", "final_test_predictions",
              "final_test_metrics_computed", "p_values_computed",
              "bootstrap_executions", "shap_executions"):
        assert c[k] == 0, k
    assert c["thresholds_selected"] == 1


def test_every_governance_counter_is_zero(boundary):
    assert boundary["counters"]
    for k, v in boundary["counters"].items():
        assert v == 0, f"{k} must be 0 in a lock-only action, got {v}"
    # the two that matter most for this action specifically
    assert boundary["counters"]["development_oof_probability_values_read"] == 0
    assert boundary["counters"]["candidate_thresholds_evaluated"] == 0


# ------------------------------------------------- nothing was computed
def test_no_threshold_value_was_materialized(contract, boundary, manifest):
    ex = contract["execution_authorization"]
    assert ex["threshold_value"] is None
    assert ex["threshold_value_materialized"] is False
    assert boundary["threshold_value_materialized_by_this_action"] is False
    assert boundary["threshold_derivation_executed_by_this_action"] is False
    assert boundary["threshold_value_status"] == \
        "ALGORITHM_LOCKED_VALUE_STILL_NEVER_COMPUTED"
    assert manifest["threshold_values_materialized"] == 0
    assert manifest["development_oof_probability_values_read"] == 0


def test_no_probability_value_was_read(contract, provenance):
    ft = contract["final_test_boundary"]
    assert ft["probability_values_read_by_this_contract_lock"] == 0
    assert ft["input_row_values_read_by_this_contract_lock"] == 0
    assert ft["input_header_read_by_this_contract_lock"] is True
    assert provenance["no_source_row_values_were_read"] is True


def test_expected_outputs_do_not_exist_yet(contract):
    out = contract["expected_outputs"]
    assert len(out["artifacts"]) == 4
    for a in out["artifacts"]:
        assert a["exists_now"] is False, a["name"]
    forbidden = " ".join(out["forbidden_outputs"]).lower()
    for token in ("final_test", "refit", "recalibrated", "p_value", "sweep"):
        assert token in forbidden, token


def test_locked_development_results_are_pinned(contract):
    for rel, want in contract["expected_outputs"]["locked_development_results_pinned"].items():
        assert _sha256(rel) == want, rel


# ------------------------------------------------------- PRE02 is NOT resolved
def test_this_lock_does_not_resolve_pre02(contract, boundary):
    rel = contract["relationship_to_the_final_test_contract"]
    assert rel["this_lock_resolves_pre02"] is False
    assert rel["pre02_status_after_this_lock"] == "UNRESOLVED"
    assert rel["pre01_status_after_this_lock"] == "UNRESOLVED"
    assert rel["final_test_contract_fully_executable"] is False
    assert rel["final_test_contract_modified_by_this_action"] is False
    assert boundary["pre02_resolved_by_this_action"] is False
    assert boundary["pre02_status"] == "UNRESOLVED"
    assert boundary["final_test_contract_fully_executable"] is False


def test_the_final_test_contract_is_byte_identical(contract):
    rel = contract["relationship_to_the_final_test_contract"]
    assert _sha256(rel["final_test_contract_path"]) == rel["final_test_contract_sha256"]
    ft = _load(_FT_CONTRACT_REL)
    pre02 = next(p for p in ft["execution_prerequisites"]["prerequisites"]
                 if p["id"] == "PRE02")
    assert pre02["satisfied_now"] is False, "the Final Test lock must still be blocked"
    assert ft["executability_status"]["final_test_contract_fully_executable"] is False


def test_final_test_stays_locked_and_unread(contract, boundary):
    ft = contract["final_test_boundary"]
    assert ft["final_test_locked"] is True
    assert ft["final_test_access_authorized"] is False
    assert ft["final_test_rows_read"] == 0
    assert ft["final_test_rows_read_by_this_contract_lock"] == 0
    assert boundary["final_test_locked"] is True
    assert boundary["final_test_rows_read"] == 0


def test_locking_authorizes_nothing(contract, boundary):
    a = contract["execution_authorization"]
    for k in ("threshold_derivation_authorized_by_this_contract",
              "model_fit_authorized", "refit_authorized", "recalibration_authorized",
              "final_test_execution_authorized", "final_test_access_authorized",
              "stage130_authorized", "stage130_started",
              "ready_for_review_authorized", "merge_authorized",
              "next_action_authorized"):
        assert a[k] is False, k
    assert a["threshold_derivation_requires_new_explicit_human_authorization"] is True
    assert a["contract_lock_is_not_an_execution_permission"] is True
    assert a["next_action_id"] == NEXT_ACTION == boundary["next_action_id"]
    assert boundary["next_action_executes_threshold_derivation"] is False


def test_the_action_modified_no_prior_package(boundary):
    for k in ("existing_pull_requests_modified_by_this_action",
              "historical_scientific_artifacts_modified_by_this_action",
              "locked_primary_development_results_modified_by_this_action",
              "m1_results_modified_by_this_action",
              "prior_packages_modified_by_this_action",
              "source_contracts_modified_by_this_action",
              "final_test_contract_modified_by_this_action",
              "new_scientific_result_produced", "new_metric_computed",
              "new_p_value_created", "inferential_superiority_claimed"):
        assert boundary[k] is False, k


# ------------------------------------------------------------ package hygiene
def test_no_binary_or_data_artifact_was_committed():
    for name in sorted(os.listdir(_PKG)):
        assert name.endswith((".json", ".md")), name


def test_package_hash_manifest_matches_every_file(manifest):
    listed = set(manifest["package_files"])
    on_disk = {n for n in os.listdir(_PKG) if n != _MANIFEST_NAME}
    assert listed == on_disk
    for name, info in manifest["package_files"].items():
        with open(os.path.join(_PKG, name), "rb") as fh:
            blob = fh.read()
        assert hashlib.sha256(blob).hexdigest() == info["sha256"], name
        assert len(blob) == info["bytes"], name


def test_manifest_records_the_zero_counters(manifest):
    assert manifest["contract_status"] == STATUS
    assert manifest["model_fits_executed"] == 0
    assert manifest["final_test_rows_read"] == 0
    assert manifest["final_test_artifacts_committed"] == 0
    assert manifest["threshold_derivation_authorized"] is False
    assert manifest["pre02_resolved_by_this_action"] is False
    assert manifest["fail_closed_control_count"] == 18
    assert manifest["human_supplied_term_count"] == 6


def test_the_readme_documents_the_lock_in_english_and_persian():
    readme = _text(f"{_PKG_REL}/{_README_NAME}")
    flat = re.sub(r"\s+", " ", readme)
    for phrase in ("it computes nothing",
                   "decisions, not rules",
                   "this does not resolve `pre02`",
                   "5*tp / (5*tp + 4*fn + fp)"):
        assert phrase.lower() in flat.lower(), phrase
    for phrase in ("هیچ محاسبه‌ای", "مجوز انسانی", "PRE02"):
        assert phrase in flat, phrase
