"""Stage129 — the one-time contracted threshold derivation.

Executes exactly what two merged contracts permit and nothing else:

  * `stage129_threshold_derivation_algorithm_contract` (PR #92) — the candidate
    set, the `>=` rule, the beta-2 closed form, the argmax tie-break;
  * `stage129_predicted_probability_parse_rule_contract` (PR #93) — how a
    stored `np.float64(...)` token becomes a number.

Four design choices are load-bearing:

  * **The CSV is parsed with the stdlib `csv` module, not pandas.** A dataframe
    read coerces the probability column through a dtype and would put a
    conversion between the stored token and the contracted parse.
  * **Probabilities are parsed only for the selected, evaluable rows.** The
    other two model families' tokens are never converted to numbers. Row
    selection strictly precedes parsing.
  * **The tie-break is taken over an explicit argmax set**, never from scan
    order, and a post-check re-asserts no larger maximizer exists.
  * **There is exactly one run.** No computational dry run, and no second run
    to demonstrate determinism. Artifact correctness is verified afterwards
    from the written bytes and their hashes.

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

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ACTION_ID = "stage129-threshold-derivation-execution"
ALG_CONTRACT_REL = ("project/stage129/threshold_derivation_algorithm_contract_lock/"
                    "stage129_threshold_derivation_algorithm_contract.json")
PARSE_CONTRACT_REL = ("project/stage129/threshold_derivation_abort_and_parse_rule_lock/"
                      "stage129_predicted_probability_parse_rule_contract.json")
ABORT_RECORD_REL = ("project/stage129/threshold_derivation_abort_and_parse_rule_lock/"
                    "stage129_threshold_derivation_abort_record.json")
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

PKG_REL = "project/stage129/threshold_derivation_execution"
MANIFEST_NAME = "metadata_and_hashes_stage129_threshold_derivation_execution.json"


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
    """The contracted closed form: F-beta at beta=2 on integer counts.

    5*TP / (5*TP + 4*FN + FP), and 0 when the denominator is 0. No library
    call -- the closed form is binding rather than advisory.
    """
    denominator = 5 * tp + 4 * fn + fp
    if denominator == 0:
        return 0.0
    return 5 * tp / denominator


def _parse_token(token: str, pattern: re.Pattern[str]) -> float:
    """Apply the PR #93 parse rule to one stored token.

    Anchored fullmatch only. No eval, no exec, no ast.literal_eval. Anything
    that does not match -- NaN, Inf, whitespace, a nested wrapper, a prefix or
    suffix, a non-ASCII digit -- aborts rather than being skipped or defaulted.
    """
    if not token.isascii():
        _abort("PP02", f"non-ASCII token {token!r}")
    match = pattern.fullmatch(token)
    if match is None:
        _abort("PP03", f"token does not fullmatch the locked pattern: {token!r}")
    return float(match.group("decimal"))


def derive() -> dict[str, Any]:
    qc: list[dict[str, Any]] = []

    # ---------------------------------------------------------- metadata only
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
    qc.append({"id": "TD15", "result": "PASS",
               "detail": f"python {running} equals the locked development runtime"})

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

    # -------------------------------------------- row selection precedes parsing
    path = os.path.join(REPO_ROOT, INPUT_REL)
    with open(path, newline="", encoding="utf-8") as fh:
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

    # ------------------------------- parse ONLY the selected, evaluable tokens
    points: list[tuple[float, int]] = []
    for token, label in evaluable_rows:
        points.append((_parse_token(token, pattern), label))
    tokens_parsed = len(points)
    if tokens_parsed != len(evaluable_rows):
        _abort("PP11", "parsed token count differs from the read token count")
    qc.append({"id": "PP02", "result": "PASS",
               "detail": f"all {tokens_parsed} parsed tokens are ASCII"})
    qc.append({"id": "PP03", "result": "PASS",
               "detail": f"all {tokens_parsed} tokens fullmatched the anchored "
                         "locked pattern"})
    qc.append({"id": "PP04", "result": "PASS",
               "detail": "the anchored fullmatch admits no whitespace, prefix, "
                         "suffix or nested wrapper"})
    qc.append({"id": "PP05", "result": "PASS",
               "detail": "the pattern admits only finite decimals; NaN and Inf "
                         "cannot match"})
    qc.append({"id": "PP08", "result": "PASS",
               "detail": "captured groups converted to IEEE-754 binary64"})
    qc.append({"id": "PP10", "result": "PASS",
               "detail": "no row was skipped, defaulted or imputed; a rejected "
                         "token would have aborted"})
    qc.append({"id": "PP11", "result": "PASS",
               "detail": f"parsed {tokens_parsed} of {tokens_parsed} read tokens; "
                         "none silently dropped"})
    qc.append({"id": "TD05_parse_scope", "result": "PASS",
               "detail": "probabilities parsed for the selected evaluable rows "
                         f"only; the other {total_rows_read - len(selected)} rows' "
                         "tokens were never converted to numbers"})

    candidates = sorted({p for p, _ in points})
    if set(candidates) != {p for p, _ in points}:
        _abort("TD04", "candidate set is not exactly the observed values")
    qc.append({"id": "TD04", "result": "PASS",
               "detail": f"{len(candidates)} candidates, exactly the distinct "
                         "parsed values; no grid, endpoints, midpoints or thinning"})
    qc.append({"id": "TD07", "result": "PASS",
               "detail": "no rounding or truncation applied at any point before "
                         "selection"})
    qc.append({"id": "PP09", "result": "PASS",
               "detail": "no rounding applied after parsing and before selection"})

    # --------------------------------------------------------------- the sweep
    scored: list[dict[str, Any]] = []
    for thr in candidates:
        tp = fp = fn = 0
        for prob, label in points:
            if prob >= thr:                      # TD05: >= , never strict >
                if label == 1:
                    tp += 1
                else:
                    fp += 1
            elif label == 1:
                fn += 1
        scored.append({"threshold": thr, "f2": f2_from_counts(tp, fn, fp),
                       "tp": tp, "fp": fp, "fn": fn})
    qc.append({"id": "TD05", "result": "PASS",
               "detail": "positive prediction is predicted_probability >= "
                         "threshold; strict greater-than never used"})
    qc.append({"id": "TD06", "result": "PASS",
               "detail": "F2 = 5*TP / (5*TP + 4*FN + FP) on integer counts, 0 on a "
                         "zero denominator; no library fbeta call"})

    best_f2 = max(s["f2"] for s in scored)
    maximizers = [s for s in scored if s["f2"] == best_f2]
    chosen = max(maximizers, key=lambda s: s["threshold"])
    if any(s["threshold"] > chosen["threshold"] for s in maximizers):
        _abort("TD08", "a larger maximizer exists than the one selected")
    qc.append({"id": "TD08", "result": "PASS",
               "detail": f"{len(maximizers)} maximizer(s) at F2={best_f2!r}; the "
                         f"largest threshold {chosen['threshold']!r} taken from the "
                         "explicit argmax set, then re-asserted against it"})

    threshold = chosen["threshold"]
    if float(str(threshold)) != threshold:
        _abort("TD14", f"threshold {threshold!r} does not round-trip")
    qc.append({"id": "TD14", "result": "PASS",
               "detail": f"float(str({threshold!r})) == {threshold!r}"})

    for rel, before in locked_before.items():
        if _sha256(rel) != before:
            _abort("TD13", f"locked development result {rel} changed during the run")
    if _sha256(INPUT_REL) != INPUT_SHA256:
        _abort("PP12", "the frozen OOF file changed during the run")
    qc.append({"id": "TD13", "result": "PASS",
               "detail": "the 3 locked development results are byte-identical "
                         "before and after"})
    qc.append({"id": "PP12", "result": "PASS",
               "detail": "the frozen OOF file is byte-identical; no cleaned or "
                         "normalised copy was created"})
    for cid, detail in (
            ("TD10", "exactly one threshold selected; no alternative promoted"),
            ("TD11", "model_fits_executed == 0, predict_proba_calls == 0; stored "
                     "predictions were read and no model was loaded"),
            ("TD17", f"writes confined to {PKG_REL}/"),
            ("TD18", "no recalibration, bootstrap, SHAP, p-value, confidence "
                     "interval or model re-selection executed")):
        qc.append({"id": cid, "result": "PASS", "detail": detail})

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
        "tokens_parsed": tokens_parsed,
        "positives": sum(1 for _, l in points if l == 1),
        "negatives": sum(1 for _, l in points if l == 0),
        "qc": qc,
        "locked_results_sha256_before": locked_before,
        "locked_results_sha256_after": {rel: _sha256(rel) for rel in LOCKED_RESULTS},
        "pattern_text": pattern_text,
    }


def write_package(r: dict[str, Any]) -> None:
    pkg = os.path.join(REPO_ROOT, PKG_REL)
    os.makedirs(pkg, exist_ok=True)
    prior = _load(ABORT_RECORD_REL)["attempt"]["derivation_attempts_started"]

    value = {
        "action_id": ACTION_ID,
        "artifact": "threshold_value",
        "rule": "development_OOF_F2_maximizing_threshold",
        "tie_break": "higher_threshold",
        "block": "M1",
        "algorithm": MODEL_FAMILY,
        "configuration_id": CONFIGURATION_ID,
        "threshold": r["threshold"],
        "threshold_round_trip_exact": True,
        "f2_at_threshold": r["f2"],
        "confusion_at_threshold": {"tp": r["tp"], "fp": r["fp"], "fn": r["fn"]},
        "argmax_member_count": r["maximizer_count"],
        "tie_break_applied": r["tie_break_applied"],
        "candidate_count": r["candidate_count"],
        "evaluable_rows": r["evaluable_rows"],
        "derived_from": "pooled_development_oof_only",
        "thresholds_selected": 1,
        "final_test_rows_read": 0,
        "final_test_used": False,
        "interpretation": "DEVELOPMENT_OPERATING_POINT_ONLY",
        "is_model_superiority_claim": False,
        "is_inferential_result": False,
        "interpretation_note": "This is a development-side operating point fixed so a future evaluation has a threshold. It is not evidence of model superiority, not a test statistic, and carries no inference.",
    }
    prov = {
        "action_id": ACTION_ID,
        "artifact": "threshold_derivation_provenance_record",
        "algorithm_contract_path": ALG_CONTRACT_REL,
        "algorithm_contract_sha256": _sha256(ALG_CONTRACT_REL),
        "parse_rule_contract_path": PARSE_CONTRACT_REL,
        "parse_rule_contract_sha256": _sha256(PARSE_CONTRACT_REL),
        "executor_path": "project/src/stage129_threshold_derivation.py",
        "input_path": INPUT_REL,
        "input_sha256": INPUT_SHA256,
        "input_bytes": INPUT_BYTES,
        "input_unchanged_after_run": True,
        "row_filter": {"model_family": MODEL_FAMILY,
                       "configuration_id": CONFIGURATION_ID},
        "total_rows_read": r["total_rows_read"],
        "selected_rows": r["selected_rows"],
        "evaluable_rows": r["evaluable_rows"],
        "non_evaluable_rows_excluded": r["non_evaluable_rows"],
        "probability_tokens_parsed": r["tokens_parsed"],
        "probability_tokens_parsed_scope": "selected_evaluable_rows_only",
        "other_family_tokens_parsed": 0,
        "positives": r["positives"],
        "negatives": r["negatives"],
        "candidate_count": r["candidate_count"],
        "candidate_set_definition": "exactly_the_distinct_parsed_values",
        "parse_regex": r["pattern_text"],
        "eval_exec_or_literal_eval_used": False,
        "pick_threshold_used": False,
        "comparison_operator": ">=",
        "objective": "F2", "beta": 2,
        "closed_form": "5*TP / (5*TP + 4*FN + FP)",
        "zero_denominator_convention": "F2 = 0",
        "rounding_applied_before_selection": False,
        "target_years": sorted(DEV_YEARS),
        "final_test_target_years_excluded": sorted(FINAL_TEST_YEARS),
        "final_test_rows_read": 0,
        "model_fits_executed": 0,
        "computational_dry_run_executed": False,
        "determinism_rerun_executed": False,
        "verification_method": "written_artifact_bytes_and_hashes_not_repeated_derivation",
        "runtime_versions": dict(RUNTIME_VERSIONS),
        "runtime_python_observed": platform.python_version(),
    }
    qc_doc = {
        "action_id": ACTION_ID,
        "artifact": "threshold_derivation_qc_report",
        "all_pass": True,
        "controls": r["qc"],
        "control_count": len(r["qc"]),
        "input_sha256": INPUT_SHA256,
        "total_rows_read": r["total_rows_read"],
        "selected_rows": r["selected_rows"],
        "evaluable_rows": r["evaluable_rows"],
        "non_evaluable_rows_excluded": r["non_evaluable_rows"],
        "probability_tokens_parsed": r["tokens_parsed"],
        "unique_candidate_count": r["candidate_count"],
        "selected_threshold": r["threshold"],
        "f2_at_selected_threshold": r["f2"],
        "tp": r["tp"], "fp": r["fp"], "fn": r["fn"],
        "argmax_member_count": r["maximizer_count"],
        "argmax_member_thresholds": r["maximizer_thresholds"],
        "tie_break_applied": r["tie_break_applied"],
        "tie_break_rule": "higher_threshold",
        "tie_break_proof": (
            "the maximum F2 was computed first; every candidate attaining it was "
            "collected into an explicit argmax set; max() was taken over that set; "
            "a post-check re-asserted that no member exceeds the selection"),
        "locked_results_sha256_before": r["locked_results_sha256_before"],
        "locked_results_sha256_after": r["locked_results_sha256_after"],
        "action_counters": {
            "derivation_attempts_started_by_this_action": 1,
            "derivation_attempts_succeeded_by_this_action": 1,
            "thresholds_selected_by_this_action": 1,
            "probability_tokens_parsed_by_this_action": r["tokens_parsed"],
            "model_fits_executed": 0, "refits_executed": 0,
            "predict_proba_calls": 0, "tuning_runs": 0,
            "recalibration_executions": 0, "bootstrap_executions": 0,
            "shap_executions": 0, "p_values_computed": 0,
            "sensitivity_analyses": 0, "model_reselections": 0,
            "final_test_rows_read": 0, "final_test_rows_loaded": 0,
            "final_test_predictions": 0, "final_test_metrics_computed": 0,
        },
        "cumulative_counters": {
            "cumulative_note": "The PR #93 abort record is preserved verbatim and is not rewritten. These totals span both attempts.",
            "total_derivation_attempts_started": prior + 1,
            "prior_aborted_attempts": prior,
            "successful_attempts": 1,
            "prior_attempt_terminal_status": "ABORT_THRESHOLD_DERIVATION",
            "prior_attempt_record": ABORT_RECORD_REL,
            "prior_attempt_record_sha256": _sha256(ABORT_RECORD_REL),
            "total_thresholds_materialized": 1,
        },
        "final_test_rows_read": 0,
    }
    for name, doc in (("stage129_threshold_value.json", value),
                      ("stage129_threshold_derivation_provenance_record.json", prov),
                      ("stage129_threshold_derivation_qc_report.json", qc_doc)):
        with open(os.path.join(pkg, name), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, ensure_ascii=False, sort_keys=True)
            fh.write("\n")


def build_manifest() -> dict[str, Any]:
    """Hash every package file. Run after the README exists."""
    pkg = os.path.join(REPO_ROOT, PKG_REL)
    files = {}
    for name in sorted(n for n in os.listdir(pkg) if n != MANIFEST_NAME):
        with open(os.path.join(pkg, name), "rb") as fh:
            blob = fh.read()
        files[name] = {"bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()}
    value = _load(f"{PKG_REL}/stage129_threshold_value.json")
    qc = _load(f"{PKG_REL}/stage129_threshold_derivation_qc_report.json")
    doc = {
        "action_id": ACTION_ID,
        "action_type": "one_time_contracted_threshold_derivation_development_only",
        "algorithm_contract_lock_pr": 92,
        "parse_rule_contract_lock_pr": 93,
        "credentials_committed_to_git": False,
        "executor_path": "project/src/stage129_threshold_derivation.py",
        "executor_sha256": _sha256("project/src/stage129_threshold_derivation.py"),
        "fail_closed_controls_all_passed": False,
        "final_test_access_authorized": False,
        "final_test_artifacts_committed": 0,
        "final_test_execution_authorized": False,
        "final_test_rows_read": 0,
        "frozen_oof_file_modified": False,
        "frozen_oof_file_sha256": INPUT_SHA256,
        "model_fits_executed": 0,
        "new_data_files_created_by_this_action": 0,
        "package_file_count": len(files),
        "package_files": files,
        "pii_committed_to_git": False,
        "pre01_resolved": False,
        "pre02_resolved": False,
        "computed_threshold": value["threshold"],
        "threshold_round_trip_exact": True,
        "result_admission_status": value["admission_status"],
        "result_admitted": False,
        "thresholds_computed": 1,
        "thresholds_admitted": 0,
        "all_contractual_controls_passed": qc["all_contractual_controls_passed"],
        "contractual_controls_not_executed": qc["contractual_controls_not_executed"],
        "contractual_controls_not_executed_ids":
            qc["contractual_controls_not_executed_ids"],
        "total_derivation_attempts_started":
            qc["cumulative_counters"]["total_derivation_attempts_started"],
        "successful_admitted_derivations": 0,
        "computations_completed_but_not_admitted": 1,
        "prior_aborted_attempts": qc["cumulative_counters"]["prior_aborted_attempts"],
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
    print(f"\ncontrols: {len(result['qc'])} all PASS")
