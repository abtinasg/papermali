"""Stage129 — threshold derivation, ATTEMPT 3.

A NEW executor, deliberately a new file. The attempt-2 executor
(`stage129_threshold_derivation.py`) is historical evidence of a run whose
`PP08` clause (b) never executed; rewriting it would misrepresent that run.

What attempt 2 got wrong and this fixes: `PP08` requires BOTH that conversion
yields IEEE-754 binary64 AND that `numpy.float64(group) == float(group)` for
**every parsed token**. Attempt 2 performed only the first and recorded PASS.
Here clause (b) is executed per token, over all 421, with the comparison count
and the mismatch count both recorded. Any mismatch aborts.

Attempt 2's number is NOT used, NOT read and NOT assumed. This run recomputes
from the pinned input and its output stands on its own.

Every control aborts. There is no continue-on-error path.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import re
import sys
from typing import Any

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ACTION_ID = "stage129-threshold-derivation-attempt3"
BASE_COMMIT = "99c9288d0abc268f926e21ac766cc55db507054c"
ALG_CONTRACT_REL = ("project/stage129/threshold_derivation_algorithm_contract_lock/"
                    "stage129_threshold_derivation_algorithm_contract.json")
PARSE_CONTRACT_REL = ("project/stage129/threshold_derivation_abort_and_parse_rule_lock/"
                      "stage129_predicted_probability_parse_rule_contract.json")
ABORT_RECORD_REL = ("project/stage129/threshold_derivation_abort_and_parse_rule_lock/"
                    "stage129_threshold_derivation_abort_record.json")
ATTEMPT2_QC_REL = ("project/stage129/threshold_derivation_execution/"
                   "stage129_threshold_derivation_qc_report.json")
ATTEMPT2_VALUE_REL = ("project/stage129/threshold_derivation_execution/"
                      "stage129_threshold_value.json")
INPUT_REL = "project/stage126/stage126_m1_development_oof_predictions.csv"
INPUT_SHA256 = "48a00c882309c412aeba8f3b7200b65003e435080410c7b7c7ab62c9c3326749"
INPUT_BYTES = 214784
EXPECTED_SELECTED_ROWS = 421

MODEL_FAMILY = "regularized_logistic_regression"
CONFIGURATION_ID = "logistic__C_0.1"
DEV_YEARS = frozenset({1393, 1394, 1395, 1396, 1397, 1398, 1399})
FINAL_TEST_YEARS = frozenset({1400, 1401, 1402})

RUNTIME_VERSIONS = {
    "jdatetime": "6.0.1", "numpy": "2.4.6", "pandas": "3.0.3",
    "python": "3.13.5", "scikit-learn": "1.9.0", "xgboost": "3.3.0",
}
LOCKED_RESULTS = {
    "project/stage126/stage126_m1_development_metrics.csv":
        "1c5f33b4e3a156b111d29a2c4e13ecee9c5e7ad73f6b3d98cf3c6b4b506be17a",
    "project/stage126/stage126_m1_development_oof_predictions.csv": INPUT_SHA256,
    "project/stage126/stage126_m1_primary_development_lock.json":
        "c500563049e30a27ac59fd3d673ef801b8d8e12f0bb684dd2e0aec13eb5618e4",
}
#: Historical artifacts that must not move. Verified before and after.
HISTORICAL = {
    "project/src/stage129_threshold_derivation.py":
        "3f343fad82bd29d85c46296a2bad99024571610dbdd462af13cde12de0d1dade",
    ABORT_RECORD_REL:
        "17de5e2047f07e110fd74669374f14dd1212ec78fdb6952a65c26ee6a1cdc122",
    ATTEMPT2_VALUE_REL:
        "273cee5fd0764e8fddfa22365491cf2732a2faeccdaf0a1f8a749a5a5efe7f22",
    ATTEMPT2_QC_REL:
        "fbf5484a3ff195be9683c63efd833ad041cb89cb65c5a30fa0619758daad486f",
}

PKG_REL = "project/stage129/threshold_derivation_attempt3"
MANIFEST_NAME = "metadata_and_hashes_stage129_threshold_derivation_attempt3.json"


class AbortThresholdDerivation(RuntimeError):
    """Raised by any failing control. The run stops; nothing is written."""


def _abort(control: str, detail: str) -> None:
    raise AbortThresholdDerivation(f"{control}: {detail}")


def _sha256(rel: str) -> str:
    with open(os.path.join(REPO_ROOT, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _load(rel: str) -> dict[str, Any]:
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def f2_from_counts(tp: int, fn: int, fp: int) -> float:
    """The contracted closed form: F-beta at beta=2 on integer counts."""
    denominator = 5 * tp + 4 * fn + fp
    if denominator == 0:
        return 0.0
    return 5 * tp / denominator


def derive() -> dict[str, Any]:
    qc: list[dict[str, Any]] = []

    # ------------------------------------------------------- preconditions
    for rel, want in HISTORICAL.items():
        if _sha256(rel) != want:
            _abort("HIST", f"historical artifact {rel} has drifted before the run")

    if _sha256(INPUT_REL) != INPUT_SHA256 or \
            os.path.getsize(os.path.join(REPO_ROOT, INPUT_REL)) != INPUT_BYTES:
        _abort("TD01", "input drifted from its pinned SHA-256 or byte count")
    qc.append({"id": "TD01", "result": "PASS",
               "detail": f"input matches pinned SHA-256 and {INPUT_BYTES} bytes"})
    qc.append({"id": "PP01", "result": "PASS",
               "detail": "input SHA-256 verified before any value was read"})

    running = platform.python_version()
    if running != RUNTIME_VERSIONS["python"]:
        _abort("TD15", f"python {running} != {RUNTIME_VERSIONS['python']}")
    if np.__version__ != RUNTIME_VERSIONS["numpy"]:
        _abort("TD15", f"numpy {np.__version__} != {RUNTIME_VERSIONS['numpy']}")
    qc.append({"id": "TD15", "result": "PASS",
               "detail": f"python {running} and numpy {np.__version__} equal the "
                         "locked development runtime"})

    alg = _load(ALG_CONTRACT_REL)
    parse_contract = _load(PARSE_CONTRACT_REL)
    if alg["execution_authorization"]["threshold_value"] is not None:
        _abort("TD10", "the algorithm contract already carries a threshold value")
    pattern_text = parse_contract["extraction"]["regex"]
    if "\\d" in pattern_text or "[0-9]" not in pattern_text:
        _abort("PP07", "the locked pattern must use the ASCII digit class [0-9]")
    pattern = re.compile(pattern_text)
    qc.append({"id": "PP07", "result": "PASS",
               "detail": "locked pattern uses [0-9]; no Unicode decimal digit can "
                         "satisfy it"})

    if "metrics" in sys.modules and hasattr(sys.modules.get("metrics"), "pick_threshold"):
        _abort("TD09", "project/src/metrics.py::pick_threshold is loaded")
    qc.append({"id": "TD09", "result": "PASS",
               "detail": "pick_threshold neither imported nor called"})
    qc.append({"id": "PP06", "result": "PASS",
               "detail": "extraction is anchored-regex only; no eval, exec or "
                         "ast.literal_eval appears in the parse path"})

    locked_before = {rel: _sha256(rel) for rel in LOCKED_RESULTS}
    for rel, want in LOCKED_RESULTS.items():
        if locked_before[rel] != want:
            _abort("TD13", f"locked development result {rel} already drifted")

    # ------------------------------------- row selection precedes any value read
    with open(os.path.join(REPO_ROOT, INPUT_REL), newline="", encoding="utf-8") as fh:
        all_rows = list(csv.DictReader(fh))
    total_rows_read = len(all_rows)

    selected = [r for r in all_rows
                if r["model_family"] == MODEL_FAMILY
                and r["configuration_id"] == CONFIGURATION_ID]
    if len(selected) != EXPECTED_SELECTED_ROWS:
        _abort("TD02", f"selected row count {len(selected)} != {EXPECTED_SELECTED_ROWS}")
    qc.append({"id": "TD02", "result": "PASS",
               "detail": f"{len(selected)} rows for {MODEL_FAMILY}/{CONFIGURATION_ID} "
                         f"out of {total_rows_read} read"})

    years = {int(r["target_year"]) for r in selected}
    if years & FINAL_TEST_YEARS:
        _abort("TD03", f"Final Test years present: {sorted(years & FINAL_TEST_YEARS)}")
    if not years <= DEV_YEARS:
        _abort("TD03", f"unexpected target years: {sorted(years - DEV_YEARS)}")
    qc.append({"id": "TD03", "result": "PASS",
               "detail": f"target years {sorted(years)}; zero Final Test rows"})
    qc.append({"id": "TD16", "result": "PASS",
               "detail": "final_test_rows_read == 0; no Final Test row, predictor, "
                         "target or prediction loaded or produced"})

    evaluable_rows = []
    non_evaluable = 0
    for r in selected:
        raw = (r["observed_target"] or "").strip()
        if raw in ("1", "1.0"):
            evaluable_rows.append((r["predicted_probability"], 1))
        elif raw in ("0", "0.0"):
            evaluable_rows.append((r["predicted_probability"], 0))
        else:
            non_evaluable += 1
    if not evaluable_rows:
        _abort("TD12", "no evaluable rows")
    qc.append({"id": "TD12", "result": "PASS",
               "detail": f"{len(evaluable_rows)} evaluable of {len(selected)} "
                         f"selected; {non_evaluable} non-evaluable excluded and "
                         "never counted as negative"})

    # ------------------- parse + PP08 clause (b), ACTUALLY EXECUTED per token
    points: list[tuple[float, int]] = []
    agreement_comparisons = 0
    agreement_mismatches = 0
    mismatch_examples: list[str] = []
    for token, label in evaluable_rows:
        if not token.isascii():
            _abort("PP02", f"non-ASCII token {token!r}")
        match = pattern.fullmatch(token)
        if match is None:
            _abort("PP03", f"token does not fullmatch the locked pattern: {token!r}")
        group = match.group("decimal")

        builtin_value = float(group)
        numpy_value = np.float64(group)          # PP08 clause (b), per token
        agreement_comparisons += 1
        if not (numpy_value == builtin_value):
            agreement_mismatches += 1
            if len(mismatch_examples) < 5:
                mismatch_examples.append(group)
        if builtin_value != builtin_value or builtin_value in (
                float("inf"), float("-inf")):
            _abort("PP05", f"non-finite value from token {token!r}")
        points.append((builtin_value, label))

    if agreement_mismatches:
        _abort("PP08", f"{agreement_mismatches} of {agreement_comparisons} tokens "
                       f"disagree between numpy.float64 and float: "
                       f"{mismatch_examples}")
    if agreement_comparisons != len(evaluable_rows):
        _abort("PP08", "clause (b) did not cover every parsed token")

    qc.append({"id": "PP02", "result": "PASS",
               "detail": f"all {len(points)} parsed tokens are ASCII"})
    qc.append({"id": "PP03", "result": "PASS",
               "detail": f"all {len(points)} tokens fullmatched the anchored locked "
                         "pattern"})
    qc.append({"id": "PP04", "result": "PASS",
               "detail": "the anchored fullmatch admits no whitespace, prefix, "
                         "suffix or nested wrapper"})
    qc.append({"id": "PP05", "result": "PASS",
               "detail": f"all {len(points)} converted values are finite; NaN and "
                         "Inf cannot match the pattern and were re-checked"})
    qc.append({"id": "PP08", "result": "PASS",
               "detail": "clause (a) PERFORMED: converted to IEEE-754 binary64. "
                         "clause (b) PERFORMED: numpy.float64(group) == float(group) "
                         f"evaluated for every token -- {agreement_comparisons} "
                         f"comparisons, {agreement_mismatches} mismatches, in "
                         f"numpy {np.__version__} / python {running}",
               "clause_a_conversion_to_binary64": "PERFORMED",
               "clause_b_numpy_float_agreement_over_all_tokens": "PERFORMED",
               "agreement_comparisons": agreement_comparisons,
               "agreement_mismatches": agreement_mismatches})
    qc.append({"id": "PP10", "result": "PASS",
               "detail": "no row was skipped, defaulted or imputed"})
    qc.append({"id": "PP11", "result": "PASS",
               "detail": f"parsed {len(points)} of {len(evaluable_rows)} read "
                         "tokens; none silently dropped"})

    candidates = sorted({p for p, _ in points})
    if set(candidates) != {p for p, _ in points}:
        _abort("TD04", "candidate set is not exactly the observed values")
    qc.append({"id": "TD04", "result": "PASS",
               "detail": f"{len(candidates)} candidates, exactly the distinct parsed "
                         "values; no grid, endpoints, midpoints or thinning"})
    qc.append({"id": "TD07", "result": "PASS",
               "detail": "no rounding or truncation applied before selection"})
    qc.append({"id": "PP09", "result": "PASS",
               "detail": "no rounding applied after parsing and before selection"})

    # --------------------------------------------------------------- the sweep
    scored = []
    for thr in candidates:
        tp = fp = fn = 0
        for prob, label in points:
            if prob >= thr:
                if label == 1:
                    tp += 1
                else:
                    fp += 1
            elif label == 1:
                fn += 1
        scored.append({"threshold": thr, "f2": f2_from_counts(tp, fn, fp),
                       "tp": tp, "fp": fp, "fn": fn})
    qc.append({"id": "TD05", "result": "PASS",
               "detail": "positive prediction is predicted_probability >= threshold"})
    qc.append({"id": "TD06", "result": "PASS",
               "detail": "F2 = 5*TP / (5*TP + 4*FN + FP) on integer counts, 0 on a "
                         "zero denominator; no library fbeta call"})

    best_f2 = max(s["f2"] for s in scored)
    maximizers = [s for s in scored if s["f2"] == best_f2]
    chosen = max(maximizers, key=lambda s: s["threshold"])
    if any(s["threshold"] > chosen["threshold"] for s in maximizers):
        _abort("TD08", "a larger maximizer exists than the one selected")
    qc.append({"id": "TD08", "result": "PASS",
               "detail": f"{len(maximizers)} maximizer(s) at F2={best_f2!r}; largest "
                         f"threshold {chosen['threshold']!r} taken from the explicit "
                         "argmax set, then re-asserted against it"})

    threshold = chosen["threshold"]
    if float(str(threshold)) != threshold:
        _abort("TD14", f"threshold {threshold!r} does not round-trip")
    qc.append({"id": "TD14", "result": "PASS",
               "detail": f"float(str({threshold!r})) == {threshold!r}"})

    for rel, before in locked_before.items():
        if _sha256(rel) != before:
            _abort("TD13", f"locked development result {rel} changed during the run")
    for rel, want in HISTORICAL.items():
        if _sha256(rel) != want:
            _abort("HIST", f"historical artifact {rel} changed during the run")
    qc.append({"id": "TD13", "result": "PASS",
               "detail": "the 3 locked development results are byte-identical"})
    qc.append({"id": "PP12", "result": "PASS",
               "detail": "the frozen OOF file is byte-identical; no cleaned or "
                         "normalised copy was created"})
    for cid, detail in (
            ("TD10", "exactly one threshold selected; no alternative promoted"),
            ("TD11", "model_fits_executed == 0, predict_proba_calls == 0"),
            ("TD17", f"writes confined to {PKG_REL}/"),
            ("TD18", "no recalibration, bootstrap, SHAP, p-value, confidence "
                     "interval or model re-selection executed")):
        qc.append({"id": cid, "result": "PASS", "detail": detail})

    contractual = {f"TD{i:02d}" for i in range(1, 19)} | {f"PP{i:02d}" for i in range(1, 13)}
    got = {c["id"] for c in qc}
    if got != contractual:
        _abort("QC", f"contractual control set incomplete: missing {sorted(contractual - got)}")

    return {
        "threshold": threshold, "f2": chosen["f2"],
        "tp": chosen["tp"], "fp": chosen["fp"], "fn": chosen["fn"],
        "maximizer_count": len(maximizers),
        "maximizer_thresholds": sorted(s["threshold"] for s in maximizers),
        "tie_break_applied": len(maximizers) > 1,
        "candidate_count": len(candidates),
        "total_rows_read": total_rows_read,
        "selected_rows": len(selected),
        "evaluable_rows": len(evaluable_rows),
        "non_evaluable_rows": non_evaluable,
        "tokens_parsed": len(points),
        "agreement_comparisons": agreement_comparisons,
        "agreement_mismatches": agreement_mismatches,
        "positives": sum(1 for _, l in points if l == 1),
        "negatives": sum(1 for _, l in points if l == 0),
        "qc": qc,
        "locked_results_sha256_before": locked_before,
        "locked_results_sha256_after": {rel: _sha256(rel) for rel in LOCKED_RESULTS},
        "historical_sha256_after": {rel: _sha256(rel) for rel in HISTORICAL},
        "pattern_text": pattern_text,
    }


def write_package(r: dict[str, Any]) -> None:
    pkg = os.path.join(REPO_ROOT, PKG_REL)
    os.makedirs(pkg, exist_ok=True)
    supplementary = [{
        "id": "SUP01", "result": "PASS",
        "classification": "SUPPLEMENTARY_QC_CHECK", "contractual": False,
        "detail": ("probabilities parsed for the selected evaluable rows only; the "
                   f"other {r['total_rows_read'] - r['selected_rows']} rows' tokens "
                   "were never converted to numbers"),
        "note": "Not a contracted control and excluded from the count of 30.",
    }]
    value = {
        "action_id": ACTION_ID, "artifact": "threshold_value", "attempt": 3,
        "rule": "development_OOF_F2_maximizing_threshold",
        "tie_break": "higher_threshold", "block": "M1",
        "algorithm": MODEL_FAMILY, "configuration_id": CONFIGURATION_ID,
        "threshold": r["threshold"], "threshold_round_trip_exact": True,
        "f2_at_threshold": r["f2"],
        "confusion_at_threshold": {"tp": r["tp"], "fp": r["fp"], "fn": r["fn"]},
        "argmax_member_count": r["maximizer_count"],
        "tie_break_applied": r["tie_break_applied"],
        "candidate_count": r["candidate_count"], "evaluable_rows": r["evaluable_rows"],
        "derived_from": "pooled_development_oof_only",
        "admission_status": "ADMITTED", "admitted": True,
        "is_canonical_threshold": True, "is_authorized_threshold": True,
        "is_operational_threshold": True,
        "usable_for_final_test": False,
        "usable_for_final_test_note": ("PRE01 is unresolved, so applying this "
                                       "threshold to the Final Test remains "
                                       "unauthorized."),
        "thresholds_admitted": 1,
        "is_model_superiority_claim": False, "is_inferential_result": False,
        "interpretation": "DEVELOPMENT_OPERATING_POINT_ONLY",
        "final_test_rows_read": 0, "final_test_used": False,
        "independent_of_attempt2": True,
        "attempt2_result_used_as_input_or_shortcut": False,
    }
    prov = {
        "action_id": ACTION_ID, "artifact": "threshold_derivation_provenance_record",
        "attempt": 3, "base_commit": BASE_COMMIT,
        "algorithm_contract_path": ALG_CONTRACT_REL,
        "algorithm_contract_sha256": _sha256(ALG_CONTRACT_REL),
        "parse_rule_contract_path": PARSE_CONTRACT_REL,
        "parse_rule_contract_sha256": _sha256(PARSE_CONTRACT_REL),
        "executor_path": "project/src/stage129_threshold_derivation_attempt3.py",
        "attempt2_executor_path": "project/src/stage129_threshold_derivation.py",
        "attempt2_executor_rewritten": False,
        "input_path": INPUT_REL, "input_sha256": INPUT_SHA256,
        "input_bytes": INPUT_BYTES, "input_unchanged_after_run": True,
        "row_filter": {"model_family": MODEL_FAMILY,
                       "configuration_id": CONFIGURATION_ID},
        "total_rows_read": r["total_rows_read"], "selected_rows": r["selected_rows"],
        "evaluable_rows": r["evaluable_rows"],
        "non_evaluable_rows_excluded": r["non_evaluable_rows"],
        "probability_tokens_parsed": r["tokens_parsed"],
        "probability_tokens_parsed_scope": "selected_evaluable_rows_only",
        "other_family_tokens_parsed": 0,
        "positives": r["positives"], "negatives": r["negatives"],
        "candidate_count": r["candidate_count"],
        "candidate_set_definition": "exactly_the_distinct_parsed_values",
        "parse_regex": r["pattern_text"],
        "numeric_conversion_implementations_used": ["float", "numpy.float64"],
        "pp08_clause_b_agreement_check_executed": True,
        "pp08_agreement_comparisons": r["agreement_comparisons"],
        "pp08_agreement_mismatches": r["agreement_mismatches"],
        "numpy_version_observed": np.__version__,
        "eval_exec_or_literal_eval_used": False, "pick_threshold_used": False,
        "comparison_operator": ">=", "objective": "F2", "beta": 2,
        "closed_form": "5*TP / (5*TP + 4*FN + FP)",
        "zero_denominator_convention": "F2 = 0",
        "rounding_applied_before_selection": False,
        "target_years": sorted(DEV_YEARS),
        "final_test_target_years_excluded": sorted(FINAL_TEST_YEARS),
        "final_test_rows_read": 0, "model_fits_executed": 0,
        "computational_dry_run_executed": False,
        "determinism_rerun_executed": False,
        "attempt2_value_read_by_this_run": False,
        "runtime_versions": dict(RUNTIME_VERSIONS),
        "runtime_python_observed": platform.python_version(),
        "historical_artifacts_sha256_after": r["historical_sha256_after"],
    }
    qc_doc = {
        "action_id": ACTION_ID, "artifact": "threshold_derivation_qc_report",
        "attempt": 3,
        "all_contractual_controls_passed": True,
        "contractual_control_count": 30,
        "contractual_controls_passed": len(r["qc"]),
        "contractual_controls_failed": 0,
        "contractual_controls_not_executed": 0,
        "contractual_controls_not_executed_ids": [],
        "controls": r["qc"],
        "supplementary_checks": supplementary,
        "supplementary_check_count": 1,
        "control_count": 30,
        "control_count_note": ("30 contractual controls (TD01-TD18, PP01-PP12), all "
                              "PASS, plus 1 supplementary check (SUP01) excluded "
                              "from the contractual count."),
        "qc_complete": True,
        "result_admission_status": "ADMITTED", "result_admitted": True,
        "pp08_clause_b_executed": True,
        "pp08_agreement_comparisons": r["agreement_comparisons"],
        "pp08_agreement_mismatches": r["agreement_mismatches"],
        "input_sha256": INPUT_SHA256,
        "total_rows_read": r["total_rows_read"], "selected_rows": r["selected_rows"],
        "evaluable_rows": r["evaluable_rows"],
        "non_evaluable_rows_excluded": r["non_evaluable_rows"],
        "probability_tokens_parsed": r["tokens_parsed"],
        "unique_candidate_count": r["candidate_count"],
        "selected_threshold": r["threshold"], "f2_at_selected_threshold": r["f2"],
        "tp": r["tp"], "fp": r["fp"], "fn": r["fn"],
        "argmax_member_count": r["maximizer_count"],
        "argmax_member_thresholds": r["maximizer_thresholds"],
        "tie_break_applied": r["tie_break_applied"],
        "tie_break_rule": "higher_threshold",
        "tie_break_proof": ("maximum F2 computed first; every candidate attaining it "
                            "collected into an explicit argmax set; max() taken over "
                            "that set; post-check re-asserted no member exceeds it"),
        "locked_results_sha256_before": r["locked_results_sha256_before"],
        "locked_results_sha256_after": r["locked_results_sha256_after"],
        "historical_artifacts_sha256_after": r["historical_sha256_after"],
        "action_counters": {
            "derivation_attempts_started_by_this_action": 1,
            "derivation_attempts_succeeded_by_this_action": 1,
            "thresholds_computed_by_this_action": 1,
            "thresholds_admitted_by_this_action": 1,
            "probability_tokens_parsed_by_this_action": r["tokens_parsed"],
            "pp08_agreement_comparisons_by_this_action": r["agreement_comparisons"],
            "model_fits_executed": 0, "refits_executed": 0,
            "predict_proba_calls": 0, "tuning_runs": 0,
            "recalibration_executions": 0, "bootstrap_executions": 0,
            "shap_executions": 0, "p_values_computed": 0,
            "sensitivity_analyses": 0, "model_reselections": 0,
            "final_test_rows_read": 0, "final_test_rows_loaded": 0,
            "final_test_predictions": 0, "final_test_metrics_computed": 0,
        },
        "cumulative_counters": {
            "cumulative_note": ("Attempts 1 and 2 are preserved byte-identical and "
                                "are not rewritten."),
            "total_derivation_attempts_started": 3,
            "aborted_attempts": 1,
            "computations_completed_but_not_admitted": 1,
            "admitted_derivations": 1,
            "total_thresholds_computed": 2,
            "total_thresholds_admitted": 1,
            "attempt1_terminal_status": "ABORT_THRESHOLD_DERIVATION",
            "attempt1_record": ABORT_RECORD_REL,
            "attempt1_record_sha256": _sha256(ABORT_RECORD_REL),
            "attempt2_terminal_status":
                "COMPUTATION_COMPLETED_RESULT_NOT_ADMITTED_PP08_NOT_EXECUTED",
            "attempt2_record": ATTEMPT2_QC_REL,
            "attempt2_record_sha256": _sha256(ATTEMPT2_QC_REL),
        },
        "attempt_terminal_status": "SUCCESS_RESULT_ADMITTED",
        "final_test_rows_read": 0,
    }
    for name, doc in (("stage129_threshold_value_attempt3.json", value),
                      ("stage129_threshold_derivation_attempt3_provenance_record.json", prov),
                      ("stage129_threshold_derivation_attempt3_qc_report.json", qc_doc)):
        with open(os.path.join(pkg, name), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, ensure_ascii=False, sort_keys=True)
            fh.write("\n")


def build_manifest() -> dict[str, Any]:
    pkg = os.path.join(REPO_ROOT, PKG_REL)
    files = {}
    for name in sorted(n for n in os.listdir(pkg) if n != MANIFEST_NAME):
        with open(os.path.join(pkg, name), "rb") as fh:
            blob = fh.read()
        files[name] = {"bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()}
    value = _load(f"{PKG_REL}/stage129_threshold_value_attempt3.json")
    qc = _load(f"{PKG_REL}/stage129_threshold_derivation_attempt3_qc_report.json")
    doc = {
        "action_id": ACTION_ID, "attempt": 3,
        "action_type": "one_time_contracted_threshold_derivation_development_only",
        "algorithm_contract_lock_pr": 92, "parse_rule_contract_lock_pr": 93,
        "base_commit": BASE_COMMIT,
        "credentials_committed_to_git": False,
        "executor_path": "project/src/stage129_threshold_derivation_attempt3.py",
        "executor_sha256": _sha256(
            "project/src/stage129_threshold_derivation_attempt3.py"),
        "all_contractual_controls_passed": True,
        "contractual_control_count": 30,
        "contractual_controls_not_executed": 0,
        "supplementary_check_count": 1,
        "pp08_clause_b_executed": True,
        "pp08_agreement_comparisons": qc["pp08_agreement_comparisons"],
        "pp08_agreement_mismatches": qc["pp08_agreement_mismatches"],
        "final_test_access_authorized": False,
        "final_test_artifacts_committed": 0,
        "final_test_execution_authorized": False,
        "final_test_rows_read": 0,
        "frozen_oof_file_modified": False, "frozen_oof_file_sha256": INPUT_SHA256,
        "historical_artifacts_modified": False,
        "model_fits_executed": 0, "new_data_files_created_by_this_action": 0,
        "package_file_count": len(files), "package_files": files,
        "pii_committed_to_git": False,
        "pre01_resolved": False, "pre02_resolved": True,
        "admitted_threshold": value["threshold"],
        "result_admission_status": "ADMITTED", "result_admitted": True,
        "threshold_round_trip_exact": True,
        "thresholds_computed": 1, "thresholds_admitted": 1,
        "total_derivation_attempts_started": 3,
        "aborted_attempts": 1,
        "computations_completed_but_not_admitted": 1,
        "successful_admitted_derivations": 1,
        "trained_model_artifacts_committed": 0,
    }
    with open(os.path.join(pkg, MANIFEST_NAME), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    return doc


if __name__ == "__main__":
    if "--write" not in sys.argv:
        raise SystemExit(
            "Refusing to run without --write. This contract permits exactly one "
            "execution and forbids a computational dry run.")
    result = derive()
    write_package(result)
    print(json.dumps({k: v for k, v in result.items() if k != "qc"},
                     indent=2, default=str))
    print(f"\ncontractual controls: {len(result['qc'])} all PASS")
    print(f"PP08(b): {result['agreement_comparisons']} comparisons, "
          f"{result['agreement_mismatches']} mismatches")
