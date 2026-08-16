"""Stage129 — the aborted derivation record and the parse rule lock.

Two artifacts, two distinct failure modes.

The abort record's failure mode is **flattering arithmetic**: quietly reporting
a counter as 0 because the real number is inconvenient or unprovable. So the
tests assert the attempt is recorded as having happened, that the unprovable
count carries `UNKNOWN_NOT_ZERO` rather than a zero or a guess, and that the
diagnostic reads which DID parse 421 values are disclosed rather than folded
away. The counters that must genuinely be zero -- F2 candidates, thresholds,
fits, Final Test reads -- are checked separately and strictly.

The parse rule's failure mode is a **permissive pattern**. A rule that looks
strict but accepts `NaN`, a nested wrapper, or a Unicode digit would silently
admit a value nobody intended. So the regex is executed here against an
accept/reject corpus rather than eyeballed, and the ``\\d`` vs ``[0-9]``
distinction is proven rather than asserted.

Neither artifact may resolve PRE02, and the frozen OOF file must not move.
"""
import hashlib
import json
import os
import re

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_PKG_REL = "project/stage129/threshold_derivation_abort_and_parse_rule_lock"
_PKG = os.path.join(REPO_ROOT, _PKG_REL)
_ABORT = f"{_PKG_REL}/stage129_threshold_derivation_abort_record.json"
_PARSE = f"{_PKG_REL}/stage129_predicted_probability_parse_rule_contract.json"
_BND = (f"{_PKG_REL}/stage129_threshold_derivation_abort_and_parse_rule"
        "_governance_boundary.json")
_PROV = (f"{_PKG_REL}/stage129_threshold_derivation_abort_and_parse_rule"
         "_source_provenance.json")
_MANIFEST_NAME = ("metadata_and_hashes_stage129_threshold_derivation_abort_and"
                  "_parse_rule_lock.json")
_MAN = f"{_PKG_REL}/{_MANIFEST_NAME}"
_README_NAME = "README_STAGE129_THRESHOLD_DERIVATION_ABORT_AND_PARSE_RULE_LOCK.md"

_OOF_REL = "project/stage126/stage126_m1_development_oof_predictions.csv"
_OOF_SHA = "48a00c882309c412aeba8f3b7200b65003e435080410c7b7c7ab62c9c3326749"
_ALG_REL = ("project/stage129/threshold_derivation_algorithm_contract_lock/"
            "stage129_threshold_derivation_algorithm_contract.json")
_FT_REL = ("project/stage129/final_test_execution_contract_lock/"
           "stage129_final_test_execution_contract.json")

ACTION_ID = "stage129-threshold-derivation-abort-and-parse-rule-lock"
STATUS = "PROSPECTIVELY_LOCKED_NOT_EXECUTED"
PP_IDS = [f"PP{i:02d}" for i in range(1, 13)]
NEXT_ACTION = "human_authorization_required_for_threshold_derivation_re_execution"


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
def abort():
    return _load(_ABORT)


@pytest.fixture(scope="module")
def parse():
    return _load(_PARSE)


@pytest.fixture(scope="module")
def boundary():
    return _load(_BND)


@pytest.fixture(scope="module")
def manifest():
    return _load(_MAN)


# ------------------------------------------------ the abort record is honest
def test_the_attempt_is_recorded_as_having_happened(abort, boundary):
    a = abort["attempt"]
    assert a["derivation_attempts_started"] == 1
    assert a["derivation_attempts_completed"] == 0
    assert a["terminal_status"] == "ABORT_THRESHOLD_DERIVATION"
    assert a["started_from_commit"] == "fbcc48b6c24a1199a945914696a3eae359180808"
    assert boundary["aborted_attempt_recorded"] is True
    assert boundary["derivation_attempts_started"] == 1


def test_the_abort_mechanism_is_described_honestly(abort):
    """It was a crash that behaved like an abort, not a control firing."""
    a = abort["attempt"]
    assert a["abort_mechanism"] == \
        "uncaught_valueerror_classified_as_abort_by_the_operator"
    assert "ValueError" in a["raised_exception"]
    assert "crash" in a["abort_mechanism_note"].lower()
    assert a["abort_stage"] == "candidate_set_construction"


def test_the_counters_that_must_be_zero_are_zero(abort):
    c = abort["counters"]
    for k in ("f2_candidates_evaluated", "f2_values_computed", "thresholds_selected",
              "thresholds_materialized", "confusion_matrices_computed",
              "model_fits_executed", "refits_executed", "predict_proba_calls",
              "models_loaded", "recalibration_executions", "bootstrap_executions",
              "shap_executions", "p_values_computed", "final_test_rows_read",
              "final_test_rows_loaded", "final_test_predictor_values_read",
              "final_test_target_values_read", "final_test_predictions",
              "final_test_metrics_computed"):
        assert c[k] == 0, k


def test_the_unprovable_counter_is_unknown_not_zero(abort, boundary):
    """The failure mode being guarded is a flattering, silent zero."""
    run = abort["counters"]["aborted_derivation_run"]
    assert run["evaluable_rows_determined"] == "UNKNOWN_NOT_ZERO"
    assert run["evaluable_rows_determined"] != 0
    assert "at least 1" in run["evaluable_rows_determined_basis"]
    assert boundary["unprovable_counters_recorded_as_unknown_not_zero"] is True
    assert boundary["unprovable_counter_ids"] == [
        "aborted_derivation_run.evaluable_rows_determined"]


def test_the_aborted_run_counters_carry_their_basis(abort):
    run = abort["counters"]["aborted_derivation_run"]
    assert run["csv_rows_read_into_memory"] == 1263
    assert run["filtered_rows_for_selected_model"] == 421
    assert run["observed_target_values_classified"] == 421
    assert run["probability_token_float_conversion_attempts"] == 1
    assert run["probability_inner_values_successfully_parsed"] == 0
    assert run["candidate_set_constructed"] is False
    for key in ("csv_rows_read_into_memory_basis",
                "observed_target_values_classified_basis",
                "probability_token_float_conversion_attempts_basis"):
        assert run[key].strip(), key


def test_the_post_abort_diagnostic_parsing_is_disclosed(abort, boundary):
    """421 inner values WERE parsed while characterising the defect. Say so."""
    d = abort["counters"]["subsequent_diagnostic_reads"]
    assert d["probability_inner_values_parsed_to_float"] == 421
    assert d["anchored_regex_matches_on_selected_model"] == 421
    assert d["distinct_inner_values_observed"] == 421
    assert d["f2_candidates_evaluated"] == 0
    assert d["thresholds_selected"] == 0
    assert boundary["diagnostic_reads_after_abort_disclosed"] is True
    assert boundary["diagnostic_probability_inner_values_parsed"] == 421


def test_the_required_assertions_are_recorded(abort):
    a = abort["assertions"]
    assert a["one_attempt_was_started_and_aborted"] is True
    assert a["no_candidate_was_evaluated_for_f2"] is True
    assert a["no_threshold_was_selected"] is True
    assert a["no_threshold_was_materialized"] is True
    assert a["pre02_remains_unresolved"] is True
    assert a["final_test_rows_read"] == 0
    assert a["no_final_test_access_occurred"] is True


def test_the_defect_is_recorded_as_serialization_not_data_loss(abort):
    d = abort["defect_found"]
    assert d["defect"] == "SERIALIZATION_ONLY_NUMPY_REPR_LEAKED_INTO_CSV"
    assert d["numeric_content_damaged"] is False
    assert d["no_digits_were_lost"] is True
    assert d["rows_affected_total"] == 1263
    assert d["rows_affected_selected_model"] == 421
    assert d["other_columns_affected"] == []
    assert d["artifact_unchanged_by_this_action"] is True
    assert d["artifact_sha256"] == _OOF_SHA


# ------------------------------------------------------ the parse rule bites
def test_parse_rule_identity(parse, boundary):
    assert parse["action_id"] == ACTION_ID == boundary["action_id"]
    assert parse["contract_status"] == STATUS == boundary["contract_status"]
    assert parse["provenance_of_terms"][
        "every_term_is_extracted_from_a_prelocked_artifact"] is False
    assert len(parse["provenance_of_terms"]["human_supplied_terms"]) == 8
    assert boundary["human_supplied_term_count"] == 8


def test_the_regex_accepts_exactly_what_it_should(parse):
    rx = re.compile(parse["extraction"]["regex"])
    for token in ("np.float64(0.5)", "np.float64(0.513922437119)",
                  "np.float64(-0.25)", "np.float64(+1.0)", "np.float64(.5)",
                  "np.float64(1)", "np.float64(1e-3)", "np.float64(1.5E+10)",
                  "np.float64(0.0)"):
        assert rx.fullmatch(token), token


@pytest.mark.parametrize("token", [
    "np.float64(nan)", "np.float64(NaN)", "np.float64(inf)", "np.float64(-Inf)",
    "np.float64(Infinity)", " np.float64(0.5)", "np.float64(0.5) ",
    "np.float64( 0.5 )", "np.float64(np.float64(0.5))", "x np.float64(0.5)",
    "np.float64(0.5)x", "0.5", "", "np.float64()", "np.float64(0x1f)",
    "np.float64(1_000.5)", "np.float64(۰.۵)", "np.float64(1,000.5)",
    "np.float64(1e)",
])
def test_the_regex_rejects_every_contracted_rejection(parse, token):
    rx = re.compile(parse["extraction"]["regex"])
    assert not rx.fullmatch(token), token


def test_ascii_digit_class_is_used_and_the_risk_is_real(parse):
    r"""Prove the \d hazard rather than asserting it."""
    assert parse["extraction"]["regex_uses_ascii_digit_class_not_backslash_d"] is True
    assert "[0-9]" in parse["extraction"]["regex"]
    assert "\\d" not in parse["extraction"]["regex"]
    # the hazard: \d matches a Persian digit, [0-9] does not
    assert re.fullmatch(r"\d", "۵")
    assert not re.fullmatch(r"[0-9]", "۵")
    assert parse["token_grammar"]["token_must_be_ascii"] is True


def test_code_evaluation_is_forbidden(parse):
    ex = parse["extraction"]
    for field in ("eval_authorized", "exec_authorized",
                  "ast_literal_eval_authorized", "general_code_parser_authorized",
                  "partial_match_authorized",
                  "search_instead_of_fullmatch_authorized"):
        assert ex[field] is False, field
    assert ex["method"] == "fullmatch_anchored_regular_expression"
    assert ex["regex_is_anchored"] is True
    pp06 = next(c for c in parse["fail_closed_controls"] if c["id"] == "PP06")
    assert "eval" in pp06["check"] and "exec" in pp06["check"]


def test_rejection_never_skips_defaults_or_imputes(parse):
    r = parse["rejection_set"]
    assert r["on_any_rejection"] == "ABORT_THRESHOLD_DERIVATION"
    assert r["row_skipping_on_rejection_authorized"] is False
    assert r["default_or_sentinel_substitution_authorized"] is False
    assert r["imputation_on_rejection_authorized"] is False
    joined = " ".join(r["rejected"]).lower()
    for token in ("nan", "inf", "whitespace", "nested", "prefix", "suffix",
                  "non_ascii", "hexadecimal"):
        assert token in joined, token


def test_conversion_is_binary64_with_no_extra_rounding(parse):
    c = parse["conversion"]
    assert c["target_type"] == "IEEE_754_binary64"
    assert c["locked_runtime_numpy_version"] == "2.4.6"
    assert c["additional_rounding_authorized"] is False
    assert c["truncation_authorized"] is False
    assert c["rounding_after_parse_and_before_selection_authorized"] is False
    assert c["equivalent_to_python_float_on_the_captured_group"] is True


def test_numpy_float64_and_float_really_agree_on_literals():
    """PP08's premise, checked on literals only -- no data file is read."""
    np = pytest.importorskip("numpy")
    for lit in ("0.513922437119", "-0.25", "1e-3", ".5", "1", "0.0"):
        assert np.float64(lit) == float(lit), lit


def test_this_is_classified_as_interpretation_not_cleaning(parse):
    c = parse["classification"]
    assert c["this_is"] == "serialization_interpretation"
    for forbidden in ("data_cleaning", "rounding", "imputation", "correction",
                      "normalisation"):
        assert forbidden in c["this_is_not"], forbidden
    assert c["underlying_numeric_content_is_unchanged_by_parsing"] is True
    assert c["parsing_is_a_read_operation_only"] is True


def test_all_twelve_parse_controls_exist_and_abort(parse):
    controls = parse["fail_closed_controls"]
    assert [c["id"] for c in controls] == PP_IDS
    for c in controls:
        assert c["on_failure"] == "ABORT_THRESHOLD_DERIVATION", c["id"]
        assert c["check"].strip()


# ------------------------------------------- the frozen file must not move
def test_the_frozen_oof_file_is_byte_identical(parse, boundary, manifest):
    assert _sha256(_OOF_REL) == _OOF_SHA
    im = parse["immutability"]
    assert im["original_file_must_remain_byte_identical"] is True
    assert im["original_file_sha256"] == _OOF_SHA
    for field in ("cleaned_copy_authorized",
                  "rewritten_or_normalised_replacement_authorized",
                  "in_place_edit_authorized",
                  "cascade_of_dependent_pinned_hashes_authorized"):
        assert im[field] is False, field
    assert boundary["frozen_oof_file_modified_by_this_action"] is False
    assert boundary["cleaned_copy_created_by_this_action"] is False
    assert boundary["dependent_pinned_hash_cascade_triggered"] is False
    assert manifest["frozen_oof_file_modified"] is False


def test_no_cleaned_copy_of_the_oof_file_exists():
    """PP12's second half, checked against the tree."""
    hits = []
    for root, _dirs, files in os.walk(os.path.join(REPO_ROOT, "project")):
        for name in files:
            low = name.lower()
            if "development_oof_predictions" in low and not low.endswith(".py"):
                hits.append(os.path.relpath(os.path.join(root, name), REPO_ROOT))
    assert hits == [_OOF_REL], hits


def test_the_merged_algorithm_contract_is_untouched(parse, boundary):
    u = parse["unchanged_terms_of_the_merged_algorithm_contract"]
    assert _sha256(_ALG_REL) == u["algorithm_contract_sha256"]
    assert u["algorithm_contract_modified_by_this_action"] is False
    assert boundary["algorithm_contract_modified_by_this_action"] is False
    assert u["comparison_operator"] == ">="
    assert u["objective_beta"] == 2
    assert u["objective_closed_form"] == "5*TP / (5*TP + 4*FN + FP)"
    assert u["pick_threshold_authorized"] is False
    alg = _load(_ALG_REL)
    assert alg["execution_authorization"]["threshold_value"] is None


# --------------------------------------------------- PRE02 stays unresolved
def test_pre02_is_not_resolved(parse, abort, boundary, manifest):
    rel = parse["relationship_to_pre02"]
    assert rel["this_lock_resolves_pre02"] is False
    assert rel["pre02_status_after_this_lock"] == "UNRESOLVED"
    assert rel["pre01_status_after_this_lock"] == "UNRESOLVED"
    assert rel["final_test_contract_fully_executable"] is False
    assert abort["assertions"]["pre02_remains_unresolved"] is True
    assert boundary["pre02_resolved_by_this_action"] is False
    assert manifest["pre02_resolved"] is False
    ft = _load(_FT_REL)
    pre02 = next(p for p in ft["execution_prerequisites"]["prerequisites"]
                 if p["id"] == "PRE02")
    assert pre02["satisfied_now"] is False


def test_nothing_was_executed_by_this_action(parse, boundary, manifest):
    ex = parse["execution_authorization"]
    assert ex["parse_executed_by_this_action"] is False
    assert ex["probability_values_reread_by_this_action"] == 0
    assert ex["threshold_value"] is None
    assert ex["threshold_value_materialized"] is False
    assert ex["final_test_rows_read"] == 0
    assert boundary["parse_rule_executed_by_this_action"] is False
    assert boundary["eval_or_exec_used_by_this_action"] is False
    assert manifest["parse_executed_against_data"] is False
    assert manifest["probability_values_reread_by_this_action"] == 0
    assert manifest["threshold_values_materialized"] == 0


def test_every_governance_counter_of_this_action_is_zero(boundary):
    assert boundary["counters"]
    for k, v in boundary["counters"].items():
        assert v == 0, f"{k} must be 0 for this action, got {v}"


def test_locking_authorizes_nothing(parse, boundary):
    ex = parse["execution_authorization"]
    for k in ("threshold_derivation_authorized_by_this_contract",
              "model_fit_authorized", "refit_authorized", "recalibration_authorized",
              "final_test_execution_authorized", "final_test_access_authorized",
              "stage130_authorized", "stage130_started",
              "ready_for_review_authorized", "merge_authorized",
              "next_action_authorized"):
        assert ex[k] is False, k
    assert ex["next_action_id"] == NEXT_ACTION == boundary["next_action_id"]
    assert ex["contract_lock_is_not_an_execution_permission"] is True


def test_no_prior_package_was_modified(boundary):
    for k in ("final_test_contract_modified_by_this_action",
              "prior_packages_modified_by_this_action",
              "source_contracts_modified_by_this_action",
              "existing_pull_requests_modified_by_this_action",
              "historical_scientific_artifacts_modified_by_this_action",
              "locked_primary_development_results_modified_by_this_action",
              "m1_results_modified_by_this_action",
              "historical_artifacts_rewritten_by_this_action",
              "new_scientific_result_produced"):
        assert boundary[k] is False, k


# ------------------------------------------------------------ provenance
def test_sources_are_pinned_and_current():
    prov = _load(_PROV)
    src = prov["source_artifacts_sha256"]
    assert len(src) == prov["source_artifact_count"] == 5
    for rel, info in src.items():
        assert _sha256(rel) == info["sha256"], rel
        with open(os.path.join(REPO_ROOT, rel), "rb") as fh:
            assert len(fh.read()) == info["bytes"], rel
    assert prov["every_contract_term_traces_to_one_of_these_artifacts"] is False
    assert len(prov["human_supplied_terms_not_traceable_to_any_frozen_artifact"]) == 8
    assert prov["no_probability_or_target_value_was_read_by_this_action"] is True


def test_the_counters_were_reconstructed_not_guessed():
    prov = _load(_PROV)
    ev = prov["aborted_attempt_evidence"]
    assert ev["counts_estimated_or_guessed"] is False
    assert ev["unprovable_counts_marked_unknown_not_zero"] is True
    assert ev["executor_retained_in_repository"] is False
    assert len(ev["evidence_sources"]) == 2


def test_the_aborted_attempts_executor_was_not_retained():
    """The ABORTED run's executor was written, run once and deleted.

    This originally asserted that nothing exists at that path, which encoded a
    transient condition as a permanent invariant. A later authorized derivation
    legitimately puts a NEW executor there, so the durable claim is the scoped
    one the provenance record actually makes: the aborted attempt's executor was
    not retained, and its counters were reconstructed from the traceback and the
    executed source rather than by re-running anything.

    If an executor exists at that path now, it belongs to a successful
    derivation and must be pinned by that run's own manifest.
    """
    prov = _load(_PROV)
    ev = prov["aborted_attempt_evidence"]
    assert ev["executor_retained_in_repository"] is False
    assert ev["counts_estimated_or_guessed"] is False

    executor_rel = "project/src/stage129_threshold_derivation.py"
    executor_abs = os.path.join(REPO_ROOT, executor_rel)
    if not os.path.exists(executor_abs):
        return
    manifest_rel = ("project/stage129/threshold_derivation_execution/"
                    "metadata_and_hashes_stage129_threshold_derivation_execution.json")
    assert os.path.exists(os.path.join(REPO_ROOT, manifest_rel)), (
        "an executor exists at the aborted attempt's path but no successful "
        "derivation package claims it")
    manifest = _load(manifest_rel)
    assert manifest["executor_path"] == executor_rel
    assert manifest["executor_sha256"] == _sha256(executor_rel)


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


def test_the_readme_documents_both_halves_in_english_and_persian():
    readme = _text(f"{_PKG_REL}/{_README_NAME}")
    flat = re.sub(r"\s+", " ", readme)
    for phrase in ("nothing was derived",
                   "unknown_not_zero",
                   "serialization interpretation, not cleaning",
                   "this does not resolve `pre02`"):
        assert phrase.lower() in flat.lower(), phrase
    for phrase in ("هیچ threshold تولید",
                   "UNKNOWN_NOT_ZERO", "PRE02"):
        assert phrase in flat, phrase
