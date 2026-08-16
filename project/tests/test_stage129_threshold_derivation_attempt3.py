"""Stage129 — attempt 3, the admitted threshold derivation.

Attempt 2 failed admission because a contractual control was recorded PASS
without running. So the tests here are pointed at exactly that class of failure:

  * `PP08(b)` must be shown to have **actually executed**, with a comparison
    count equal to the token count and zero mismatches -- not merely asserted;
  * attempts 1 and 2 must survive **byte-identical**, pinned by hash, because a
    success is when a programme is most tempted to tidy away its failures;
  * this run must not lean on attempt 2's number -- it agrees, but agreement is
    not the basis for admission;
  * `PRE02` resolving must not drag `PRE01` or any Final Test lock with it.

The suite does not re-run the derivation; verification is from written bytes.
"""
import hashlib
import json
import os
import re

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PKG_REL = "project/stage129/threshold_derivation_attempt3"
_PKG = os.path.join(REPO_ROOT, _PKG_REL)
_VALUE = f"{_PKG_REL}/stage129_threshold_value_attempt3.json"
_PROV = f"{_PKG_REL}/stage129_threshold_derivation_attempt3_provenance_record.json"
_QC = f"{_PKG_REL}/stage129_threshold_derivation_attempt3_qc_report.json"
_MANIFEST_NAME = "metadata_and_hashes_stage129_threshold_derivation_attempt3.json"
_MAN = f"{_PKG_REL}/{_MANIFEST_NAME}"
_README = f"{_PKG_REL}/README_STAGE129_THRESHOLD_DERIVATION_ATTEMPT3.md"

_EXECUTOR = "project/src/stage129_threshold_derivation_attempt3.py"
_OLD_EXECUTOR = "project/src/stage129_threshold_derivation.py"
_OLD_EXECUTOR_SHA = "3f343fad82bd29d85c46296a2bad99024571610dbdd462af13cde12de0d1dade"
_OOF_REL = "project/stage126/stage126_m1_development_oof_predictions.csv"
_OOF_SHA = "48a00c882309c412aeba8f3b7200b65003e435080410c7b7c7ab62c9c3326749"
_FT_REL = ("project/stage129/final_test_execution_contract_lock/"
           "stage129_final_test_execution_contract.json")

THRESHOLD = 0.426878838687
F2 = 0.5916030534351145
TP, FP, FN = 31, 91, 4
TOKENS = 421


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


# ------------------------------------------------ PP08(b) actually executed
def test_pp08_clause_b_really_ran_over_every_token(qc, prov, manifest):
    """The defect that blocked attempt 2 must be demonstrably gone."""
    assert qc["pp08_clause_b_executed"] is True
    assert prov["pp08_clause_b_agreement_check_executed"] is True
    assert qc["pp08_agreement_comparisons"] == TOKENS
    assert qc["pp08_agreement_mismatches"] == 0
    assert prov["pp08_agreement_comparisons"] == TOKENS
    assert prov["pp08_agreement_mismatches"] == 0
    assert manifest["pp08_agreement_comparisons"] == TOKENS
    assert manifest["pp08_agreement_mismatches"] == 0
    # one comparison per parsed token, not a sample
    assert qc["pp08_agreement_comparisons"] == qc["probability_tokens_parsed"]
    pp08 = next(c for c in qc["controls"] if c["id"] == "PP08")
    assert pp08["result"] == "PASS"
    assert pp08["clause_a_conversion_to_binary64"] == "PERFORMED"
    assert pp08["clause_b_numpy_float_agreement_over_all_tokens"] == "PERFORMED"
    assert pp08["agreement_comparisons"] == TOKENS
    assert pp08["agreement_mismatches"] == 0


def test_both_constructors_were_used(prov):
    assert set(prov["numeric_conversion_implementations_used"]) == {
        "float", "numpy.float64"}
    assert prov["numpy_version_observed"] == "2.4.6"


def test_all_thirty_contractual_controls_passed(qc):
    assert qc["all_contractual_controls_passed"] is True
    assert qc["contractual_control_count"] == 30
    assert qc["contractual_controls_passed"] == 30
    assert qc["contractual_controls_failed"] == 0
    assert qc["contractual_controls_not_executed"] == 0
    assert qc["contractual_controls_not_executed_ids"] == []
    ids = {c["id"] for c in qc["controls"]}
    assert ids == ({f"TD{i:02d}" for i in range(1, 19)}
                   | {f"PP{i:02d}" for i in range(1, 13)})
    for c in qc["controls"]:
        assert c["result"] == "PASS", c["id"]


def test_sup01_stays_outside_the_contractual_count(qc):
    assert qc["supplementary_check_count"] == 1
    entry = qc["supplementary_checks"][0]
    assert entry["id"] == "SUP01"
    assert entry["contractual"] is False
    assert entry["id"] not in {c["id"] for c in qc["controls"]}


# ------------------------------------------------------- the admitted number
def test_the_threshold_is_admitted(value, qc, manifest):
    assert value["threshold"] == THRESHOLD
    assert value["f2_at_threshold"] == F2
    assert value["confusion_at_threshold"] == {"tp": TP, "fp": FP, "fn": FN}
    assert value["admitted"] is True
    assert value["admission_status"] == "ADMITTED"
    assert value["thresholds_admitted"] == 1
    assert qc["result_admitted"] is True
    assert manifest["result_admitted"] is True
    assert manifest["thresholds_admitted"] == 1


def test_f2_recomputes_and_round_trips(value):
    c = value["confusion_at_threshold"]
    tp, fp, fn = c["tp"], c["fp"], c["fn"]
    assert 5 * tp / (5 * tp + 4 * fn + fp) == value["f2_at_threshold"]
    assert float(str(value["threshold"])) == value["threshold"]


def test_the_argmax_tie_break_is_proved(value, qc):
    assert qc["argmax_member_count"] == value["argmax_member_count"] == 1
    assert value["threshold"] == max(qc["argmax_member_thresholds"])
    proof = qc["tie_break_proof"].lower()
    assert "argmax set" in proof and "max()" in proof and "post-check" in proof


def test_admission_does_not_rest_on_attempt_two(value, prov):
    """It agrees with attempt 2, but agreement is not the basis."""
    assert value["independent_of_attempt2"] is True
    assert value["attempt2_result_used_as_input_or_shortcut"] is False
    assert prov["attempt2_value_read_by_this_run"] is False


def test_it_is_not_a_superiority_or_inferential_claim(value):
    assert value["is_model_superiority_claim"] is False
    assert value["is_inferential_result"] is False
    assert value["interpretation"] == "DEVELOPMENT_OPERATING_POINT_ONLY"


# ------------------------------------------------ method, as contracted
def test_row_selection_preceded_parsing(prov, qc):
    assert prov["total_rows_read"] == 1263
    assert prov["selected_rows"] == TOKENS
    assert prov["evaluable_rows"] == TOKENS
    assert prov["probability_tokens_parsed"] == TOKENS
    assert prov["probability_tokens_parsed_scope"] == "selected_evaluable_rows_only"
    assert prov["other_family_tokens_parsed"] == 0
    assert prov["positives"] == 35 and prov["negatives"] == 386
    assert qc["unique_candidate_count"] == TOKENS


def test_the_contracted_algorithm_terms(prov):
    assert prov["comparison_operator"] == ">="
    assert prov["beta"] == 2
    assert prov["closed_form"] == "5*TP / (5*TP + 4*FN + FP)"
    assert prov["zero_denominator_convention"] == "F2 = 0"
    assert prov["candidate_set_definition"] == "exactly_the_distinct_parsed_values"
    assert prov["rounding_applied_before_selection"] is False
    assert prov["pick_threshold_used"] is False
    assert prov["eval_exec_or_literal_eval_used"] is False


def test_exactly_one_run(prov):
    assert prov["computational_dry_run_executed"] is False
    assert prov["determinism_rerun_executed"] is False
    assert prov["model_fits_executed"] == 0
    src = _text(_EXECUTOR)
    assert '"--write" not in sys.argv' in src


# -------------------------------------------- history survives byte-identical
def test_the_attempt2_executor_was_not_rewritten(prov):
    assert prov["attempt2_executor_rewritten"] is False
    assert _sha256(_OLD_EXECUTOR) == _OLD_EXECUTOR_SHA
    assert prov["executor_path"] == _EXECUTOR
    assert _EXECUTOR != _OLD_EXECUTOR


def test_attempts_one_and_two_are_pinned_and_unchanged(qc):
    cum = qc["cumulative_counters"]
    assert _sha256(cum["attempt1_record"]) == cum["attempt1_record_sha256"]
    assert _sha256(cum["attempt2_record"]) == cum["attempt2_record_sha256"]
    assert cum["attempt1_terminal_status"] == "ABORT_THRESHOLD_DERIVATION"
    assert cum["attempt2_terminal_status"] == \
        "COMPUTATION_COMPLETED_RESULT_NOT_ADMITTED_PP08_NOT_EXECUTED"
    # the attempt-2 package still says it was not admitted
    a2 = _load("project/stage129/threshold_derivation_execution/"
               "stage129_threshold_value.json")
    assert a2["admitted"] is False
    assert a2["admission_status"] == "COMPUTED_BUT_NOT_ADMITTED_QC_INCOMPLETE"


def test_cumulative_counters_count_all_three_attempts(qc, manifest):
    cum = qc["cumulative_counters"]
    assert cum["total_derivation_attempts_started"] == 3
    assert cum["aborted_attempts"] == 1
    assert cum["computations_completed_but_not_admitted"] == 1
    assert cum["admitted_derivations"] == 1
    assert cum["total_thresholds_computed"] == 2
    assert cum["total_thresholds_admitted"] == 1
    assert manifest["total_derivation_attempts_started"] == 3
    assert manifest["aborted_attempts"] == 1
    assert manifest["computations_completed_but_not_admitted"] == 1
    assert manifest["successful_admitted_derivations"] == 1


def test_frozen_inputs_did_not_move(prov, qc, manifest):
    assert _sha256(_OOF_REL) == _OOF_SHA == prov["input_sha256"]
    assert prov["input_unchanged_after_run"] is True
    assert manifest["frozen_oof_file_modified"] is False
    assert manifest["historical_artifacts_modified"] is False
    assert qc["locked_results_sha256_before"] == qc["locked_results_sha256_after"]
    for rel, want in qc["locked_results_sha256_after"].items():
        assert _sha256(rel) == want, rel
    for rel, want in qc["historical_artifacts_sha256_after"].items():
        assert _sha256(rel) == want, rel


def test_no_cleaned_copy_of_the_oof_file_exists():
    hits = []
    for root, _dirs, files in os.walk(os.path.join(REPO_ROOT, "project")):
        for name in files:
            low = name.lower()
            if "development_oof_predictions" in low and not low.endswith(".py"):
                hits.append(os.path.relpath(os.path.join(root, name), REPO_ROOT))
    assert hits == [_OOF_REL], hits


# ------------------------------------ PRE02 resolved, Final Test still shut
def test_pre02_resolved_pre01_not(manifest):
    assert manifest["pre02_resolved"] is True
    assert manifest["pre01_resolved"] is False


def test_the_final_test_stays_shut(value, prov, qc, manifest):
    assert value["final_test_rows_read"] == 0
    assert value["final_test_used"] is False
    assert value["usable_for_final_test"] is False
    assert prov["final_test_rows_read"] == 0
    assert qc["final_test_rows_read"] == 0
    assert manifest["final_test_rows_read"] == 0
    assert manifest["final_test_access_authorized"] is False
    assert manifest["final_test_execution_authorized"] is False
    ft = _load(_FT_REL)
    pre01 = next(p for p in ft["execution_prerequisites"]["prerequisites"]
                 if p["id"] == "PRE01")
    assert pre01["satisfied_now"] is False


# ------------------------------------------------------------ package hygiene
def test_no_binary_or_data_artifact_was_committed():
    for name in sorted(os.listdir(_PKG)):
        assert name.endswith((".json", ".md")), name


def test_manifest_matches_every_file(manifest):
    listed = set(manifest["package_files"])
    on_disk = {n for n in os.listdir(_PKG) if n != _MANIFEST_NAME}
    assert listed == on_disk
    for name, info in manifest["package_files"].items():
        with open(os.path.join(_PKG, name), "rb") as fh:
            blob = fh.read()
        assert hashlib.sha256(blob).hexdigest() == info["sha256"], name
        assert len(blob) == info["bytes"], name
    assert _sha256(_EXECUTOR) == manifest["executor_sha256"]


def test_the_readme_reports_it_in_english_and_persian():
    flat = re.sub(r"\s+", " ", _text(_README))
    assert "0.426878838687" in flat
    for phrase in ("421 comparisons, 0 mismatches", "was **not rewritten**",
                   "not the basis for admission"):
        assert phrase.lower() in flat.lower(), phrase
    for phrase in ("نتیجه پذیرفته شد", "PRE01", "۴۲۱ مقایسه"):
        assert phrase in flat, phrase
