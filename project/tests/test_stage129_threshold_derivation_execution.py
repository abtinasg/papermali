"""Stage129 — the executed threshold derivation.

The derivation finally ran. Three things could still go wrong afterwards, and
these tests pin each shut:

  * the recorded number could be **internally inconsistent** -- so F2 is
    recomputed from the recorded confusion counts, the round-trip property is
    re-checked, and the three artifacts are cross-agreed rather than trusted
    individually;
  * the earlier abort could be **quietly erased** now that a success exists --
    so the PR #93 record is asserted byte-identical, and the cumulative counters
    must still show two attempts, one of them aborted;
  * resolving PRE02 could be mistaken for **unblocking the Final Test** -- so
    PRE01 must stay unresolved and every Final Test flag must stay shut.

The suite deliberately does NOT re-run the derivation. The contract permits one
execution; verification is from the written bytes.
"""
import hashlib
import json
import os
import re

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_PKG_REL = "project/stage129/threshold_derivation_execution"
_PKG = os.path.join(REPO_ROOT, _PKG_REL)
_VALUE = f"{_PKG_REL}/stage129_threshold_value.json"
_PROV = f"{_PKG_REL}/stage129_threshold_derivation_provenance_record.json"
_QC = f"{_PKG_REL}/stage129_threshold_derivation_qc_report.json"
_MANIFEST_NAME = "metadata_and_hashes_stage129_threshold_derivation_execution.json"
_MAN = f"{_PKG_REL}/{_MANIFEST_NAME}"
_README_NAME = "README_STAGE129_THRESHOLD_DERIVATION_EXECUTION.md"

_EXECUTOR_REL = "project/src/stage129_threshold_derivation.py"
_OOF_REL = "project/stage126/stage126_m1_development_oof_predictions.csv"
_OOF_SHA = "48a00c882309c412aeba8f3b7200b65003e435080410c7b7c7ab62c9c3326749"
_ABORT_REL = ("project/stage129/threshold_derivation_abort_and_parse_rule_lock/"
              "stage129_threshold_derivation_abort_record.json")
_ALG_REL = ("project/stage129/threshold_derivation_algorithm_contract_lock/"
            "stage129_threshold_derivation_algorithm_contract.json")
_FT_REL = ("project/stage129/final_test_execution_contract_lock/"
           "stage129_final_test_execution_contract.json")

THRESHOLD = 0.426878838687
F2 = 0.5916030534351145
TP, FP, FN = 31, 91, 4
CANDIDATES = 421
SELECTED = 421
TOTAL_READ = 1263


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
def value():
    return _load(_VALUE)


@pytest.fixture(scope="module")
def prov():
    return _load(_PROV)


@pytest.fixture(scope="module")
def qc():
    return _load(_QC)


@pytest.fixture(scope="module")
def manifest():
    return _load(_MAN)


# ------------------------------------------------- the number is consistent
def test_the_threshold_and_its_f2_are_recorded(value):
    assert value["threshold"] == THRESHOLD
    assert value["f2_at_threshold"] == F2
    assert value["confusion_at_threshold"] == {"tp": TP, "fp": FP, "fn": FN}
    assert value["thresholds_selected"] == 0


def test_f2_recomputes_from_the_recorded_counts(value):
    """The closed form, applied to the artifact's own numbers."""
    c = value["confusion_at_threshold"]
    tp, fp, fn = c["tp"], c["fp"], c["fn"]
    assert 5 * tp / (5 * tp + 4 * fn + fp) == value["f2_at_threshold"]
    assert 5 * TP + 4 * FN + FP == 262
    assert 5 * TP == 155


def test_the_threshold_round_trips_exactly(value):
    assert float(str(value["threshold"])) == value["threshold"]
    assert value["threshold_round_trip_exact"] is True


def test_the_three_artifacts_agree(value, prov, qc):
    assert qc["selected_threshold"] == value["threshold"]
    assert qc["f2_at_selected_threshold"] == value["f2_at_threshold"]
    assert (qc["tp"], qc["fp"], qc["fn"]) == (TP, FP, FN)
    assert qc["unique_candidate_count"] == value["candidate_count"] == CANDIDATES
    assert qc["evaluable_rows"] == value["evaluable_rows"] == prov["evaluable_rows"]
    assert prov["candidate_count"] == CANDIDATES


def test_the_argmax_and_tie_break_are_proved_not_assumed(value, qc):
    assert qc["argmax_member_count"] == value["argmax_member_count"] == 1
    assert qc["argmax_member_thresholds"] == [THRESHOLD]
    assert value["tie_break_applied"] is False
    assert qc["tie_break_rule"] == "higher_threshold"
    proof = qc["tie_break_proof"].lower()
    assert "argmax set" in proof
    assert "max()" in proof
    assert "re-asserted" in proof
    # the selected threshold really is the maximum of the argmax set
    assert value["threshold"] == max(qc["argmax_member_thresholds"])


# --------------------------------------------- selection preceded parsing
def test_row_selection_preceded_parsing(prov, qc):
    assert prov["total_rows_read"] == qc["total_rows_read"] == TOTAL_READ
    assert prov["selected_rows"] == qc["selected_rows"] == SELECTED
    assert prov["probability_tokens_parsed"] == SELECTED
    assert prov["probability_tokens_parsed_scope"] == "selected_evaluable_rows_only"
    assert prov["other_family_tokens_parsed"] == 0
    assert prov["non_evaluable_rows_excluded"] == 0
    assert prov["positives"] == 35
    assert prov["negatives"] == 386
    assert prov["positives"] + prov["negatives"] == prov["evaluable_rows"]


def test_the_locked_parse_rule_was_used(prov):
    assert prov["eval_exec_or_literal_eval_used"] is False
    assert prov["pick_threshold_used"] is False
    pattern = prov["parse_regex"]
    assert "[0-9]" in pattern and "\\d" not in pattern
    rx = re.compile(pattern)
    assert rx.fullmatch("np.float64(0.426878838687)")
    for bad in ("np.float64(nan)", " np.float64(0.5)", "0.5", "np.float64(۰.۵)"):
        assert not rx.fullmatch(bad), bad


def test_the_algorithm_terms_are_the_contracted_ones(prov):
    assert prov["comparison_operator"] == ">="
    assert prov["beta"] == 2
    assert prov["closed_form"] == "5*TP / (5*TP + 4*FN + FP)"
    assert prov["zero_denominator_convention"] == "F2 = 0"
    assert prov["candidate_set_definition"] == "exactly_the_distinct_parsed_values"
    assert prov["rounding_applied_before_selection"] is False


def test_the_conversion_was_conforming_but_pp08_clause_b_did_not_run(prov):
    """float() was permitted; the missing piece is the contracted re-check."""
    assert prov["numeric_conversion_implementation"] == \
        "python_builtin_float_on_the_regex_capture_group"
    assert prov["numpy_float64_constructor_invoked"] is False
    assert prov["numpy_imported_by_executor"] is False
    assert prov["pp08_clause_b_agreement_check_executed"] is False
    assert prov["result_admitted"] is False
    note = prov["conversion_conformity_note"]
    assert "equivalent_to_python_float_on_the_captured_group" in note
    assert "may use either" in note


def test_exactly_one_run_with_no_dry_run_or_determinism_rerun(prov):
    assert prov["computational_dry_run_executed"] is False
    assert prov["determinism_rerun_executed"] is False
    assert "written_artifact" in prov["verification_method"]
    assert prov["model_fits_executed"] == 0


def test_the_executor_refuses_to_run_without_write():
    """A reflexive dry run must be impossible, not merely discouraged."""
    src = _text(_EXECUTOR_REL)
    assert '"--write" not in sys.argv' in src
    assert "Refusing to run without --write" in src


def test_the_thirty_contractual_controls_are_counted_honestly(qc):
    """TD01-TD18 and PP01-PP12 are the 30 contractual controls -- no more."""
    assert qc["all_contractual_controls_passed"] is False
    assert qc["contractual_control_count"] == 30
    assert qc["control_count"] == len(qc["controls"]) == 30
    ids = {c["id"] for c in qc["controls"]}
    assert ids == ({f"TD{i:02d}" for i in range(1, 19)}
                   | {f"PP{i:02d}" for i in range(1, 13)})
    assert qc["contractual_controls_passed"] == 29
    assert qc["contractual_controls_failed"] == 0
    assert qc["contractual_controls_not_executed"] == 1
    assert (qc["contractual_controls_passed"] + qc["contractual_controls_failed"]
            + qc["contractual_controls_not_executed"]) == 30


def test_pp08_is_not_executed_with_both_clauses_stated(qc):
    """The control was recorded PASS but its clause (b) never ran."""
    assert qc["contractual_controls_not_executed_ids"] == ["PP08"]
    pp08 = next(c for c in qc["controls"] if c["id"] == "PP08")
    assert pp08["result"] == "NOT_EXECUTED"
    assert pp08["clause_a_conversion_to_binary64"] == "PERFORMED"
    assert pp08["clause_b_numpy_float_agreement_over_all_tokens"] == "NOT_PERFORMED"
    assert pp08["originally_recorded_as"] == "PASS"
    assert "no later edit" in pp08["correction_note"].lower()
    for c in qc["controls"]:
        if c["id"] != "PP08":
            assert c["result"] == "PASS", c["id"]


def test_the_result_is_computed_but_not_admitted(qc, value, manifest):
    assert qc["result_admitted"] is False
    assert qc["result_admission_status"] == "COMPUTED_BUT_NOT_ADMITTED_QC_INCOMPLETE"
    assert qc["qc_complete"] is False
    assert qc["qc_incomplete_reason"] == "PP08_CLAUSE_B_NOT_EXECUTED"
    assert value["admitted"] is False
    assert value["admission_status"] == "COMPUTED_BUT_NOT_ADMITTED_QC_INCOMPLETE"
    for field in ("is_canonical_threshold", "is_authorized_threshold",
                  "is_operational_threshold", "usable_for_final_test"):
        assert value[field] is False, field
    assert value["retained_for"] == "audit_history_only"
    assert manifest["result_admitted"] is False
    assert manifest["thresholds_admitted"] == 0


def test_the_number_is_preserved_not_hidden(value):
    """Audit history must keep the computed number visible."""
    assert value["threshold"] == THRESHOLD
    assert value["f2_at_threshold"] == F2
    assert value["confusion_at_threshold"] == {"tp": TP, "fp": FP, "fn": FN}
    assert value["threshold_computed"] is True
    assert value["threshold_admitted"] is False


def test_the_supplementary_check_is_not_counted_as_contractual(qc):
    """A non-contracted observation must never inflate the control count."""
    supp = qc["supplementary_checks"]
    assert qc["supplementary_check_count"] == len(supp) == 1
    entry = supp[0]
    assert entry["classification"] == "SUPPLEMENTARY_QC_CHECK"
    assert entry["contractual"] is False
    assert not entry["id"].startswith(("TD", "PP")), entry["id"]
    assert entry["id"] == "SUP01"
    # and it is absent from the contractual list
    assert entry["id"] not in {c["id"] for c in qc["controls"]}
    assert "31" in qc["control_count_note"], "the earlier miscount must be disclosed"


# --------------------------------------------- the earlier abort survives
def test_the_prior_abort_record_is_byte_identical(qc):
    cum = qc["cumulative_counters"]
    assert _sha256(_ABORT_REL) == cum["prior_attempt_record_sha256"]
    abort = _load(_ABORT_REL)
    assert abort["attempt"]["terminal_status"] == "ABORT_THRESHOLD_DERIVATION"
    assert abort["attempt"]["derivation_attempts_started"] == 1
    assert abort["counters"]["aborted_derivation_run"][
        "evaluable_rows_determined"] == "UNKNOWN_NOT_ZERO"


def test_cumulative_counters_keep_both_attempts_and_admit_neither(qc, manifest):
    cum = qc["cumulative_counters"]
    assert cum["total_derivation_attempts_started"] == 2
    assert cum["prior_aborted_attempts"] == 1
    assert cum["computations_completed_but_not_admitted"] == 1
    assert cum["admitted_derivations"] == 0
    assert cum["successful_attempts"] == 0
    assert cum["total_thresholds_computed"] == 1
    assert cum["total_thresholds_admitted"] == 0
    assert cum["prior_attempt_terminal_status"] == "ABORT_THRESHOLD_DERIVATION"
    assert manifest["total_derivation_attempts_started"] == 2
    assert manifest["prior_aborted_attempts"] == 1
    assert manifest["successful_admitted_derivations"] == 0
    assert manifest["computations_completed_but_not_admitted"] == 1
    assert manifest["thresholds_computed"] == 1
    assert manifest["thresholds_admitted"] == 0


def test_action_counters_are_separate_from_cumulative(qc):
    a = qc["action_counters"]
    assert a["derivation_attempts_started_by_this_action"] == 1
    assert a["derivation_attempts_succeeded_by_this_action"] == 0
    assert a["computations_completed_but_not_admitted_by_this_action"] == 1
    assert a["thresholds_computed_by_this_action"] == 1
    assert a["thresholds_admitted_by_this_action"] == 0
    assert a["probability_tokens_parsed_by_this_action"] == SELECTED
    for k in ("model_fits_executed", "refits_executed", "predict_proba_calls",
              "tuning_runs", "recalibration_executions", "bootstrap_executions",
              "shap_executions", "p_values_computed", "sensitivity_analyses",
              "model_reselections", "final_test_rows_read", "final_test_rows_loaded",
              "final_test_predictions", "final_test_metrics_computed"):
        assert a[k] == 0, k


# ------------------------------------ PRE02 resolved, Final Test still shut
def test_pre02_is_not_resolved_by_a_qc_incomplete_computation(manifest):
    """A committed numeric file is not a resolved prerequisite."""
    assert manifest["pre02_resolved"] is False
    assert manifest["pre01_resolved"] is False


def test_the_final_test_stays_shut(value, prov, qc, manifest):
    assert value["final_test_rows_read"] == 0
    assert value["final_test_used"] is False
    assert prov["final_test_rows_read"] == 0
    assert qc["final_test_rows_read"] == 0
    assert manifest["final_test_rows_read"] == 0
    assert manifest["final_test_access_authorized"] is False
    assert manifest["final_test_execution_authorized"] is False
    # the Final Test contract's own PRE01 is still unsatisfied
    ft = _load(_FT_REL)
    pre01 = next(p for p in ft["execution_prerequisites"]["prerequisites"]
                 if p["id"] == "PRE01")
    assert pre01["satisfied_now"] is False


def test_the_result_is_not_reported_as_superiority_or_inference(value):
    assert value["is_model_superiority_claim"] is False
    assert value["is_inferential_result"] is False
    assert value["derived_from"] == "pooled_development_oof_only"


# --------------------------------------------------- frozen inputs unmoved
def test_the_frozen_oof_file_is_byte_identical(prov, qc, manifest):
    assert _sha256(_OOF_REL) == _OOF_SHA == prov["input_sha256"]
    assert prov["input_unchanged_after_run"] is True
    assert manifest["frozen_oof_file_modified"] is False
    assert qc["locked_results_sha256_before"] == qc["locked_results_sha256_after"]
    for rel, want in qc["locked_results_sha256_after"].items():
        assert _sha256(rel) == want, rel


def test_no_cleaned_copy_of_the_oof_file_exists():
    hits = []
    for root, _dirs, files in os.walk(os.path.join(REPO_ROOT, "project")):
        for name in files:
            low = name.lower()
            if "development_oof_predictions" in low and not low.endswith(".py"):
                hits.append(os.path.relpath(os.path.join(root, name), REPO_ROOT))
    assert hits == [_OOF_REL], hits


def test_the_governing_contracts_are_pinned_and_unchanged(prov):
    assert _sha256(prov["algorithm_contract_path"]) == prov["algorithm_contract_sha256"]
    assert _sha256(prov["parse_rule_contract_path"]) == prov["parse_rule_contract_sha256"]
    alg = _load(_ALG_REL)
    assert alg["execution_authorization"]["threshold_value"] is None, \
        "the merged algorithm contract must not be back-filled with the value"


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
    assert _sha256(_EXECUTOR_REL) == manifest["executor_sha256"]


def test_the_readme_reports_the_number_in_english_and_persian():
    readme = _text(f"{_PKG_REL}/{_README_NAME}")
    flat = re.sub(r"\s+", " ", readme)
    assert "0.426878838687" in flat
    assert "0.5916030534351145" in flat
    for phrase in ("exactly one run", "row selection precedes parsing",
                   "not admitted", "no later edit can make `pp08` have run"):
        assert phrase.lower() in flat.lower(), phrase
    for phrase in ("نتیجه پذیرفته نشد", "PRE01", "NOT_EXECUTED"):
        assert phrase in flat, phrase
