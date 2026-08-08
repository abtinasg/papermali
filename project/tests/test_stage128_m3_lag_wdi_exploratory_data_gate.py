"""Tests — Stage128 Track B step D: the M3-LAG-WDI EXPLORATORY DATA GATE.

These tests hold the Gate to its authorization boundary:

* the thresholds are the locked, inherited ones — never redefined;
* the parent surface is the exact 539-row retained-M2 development sample;
* the verdict is only issued when it is invariant to the two admissible
  Jalali-to-Gregorian calendar conventions;
* a PASS is data admission only — the committed package must say, in every
  place a reader could look, that it authorizes no modeling, no step E, no
  Final Test access and no merge;
* the step C material findings survive verbatim;
* no estimator or resampling runtime is anywhere near the import graph.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "project"))

from src import stage128_m3_lag_wdi_exploratory_data_gate as m  # noqa: E402

PACKAGE_DIR = ROOT / m.PACKAGE_REL

FORBIDDEN_RUNTIME_MODULES = (
    "sklearn", "xgboost", "imblearn", "shap", "lightgbm", "catboost",
    "statsmodels", "requests", "urllib3", "httpx",
)


def _load(filename: str):
    return json.loads((PACKAGE_DIR / filename).read_text(encoding="utf-8"))


class TestModuleBoundary(unittest.TestCase):
    def test_identity(self):
        self.assertEqual(
            m.ACTION_ID, "stage128-m3-lag-wdi-exploratory-data-gate")
        self.assertEqual(m.AUTHORIZED_SCOPE, "data_gate_only")

    def test_no_forbidden_runtime_in_import_graph(self):
        # Scoped to THIS module's own namespace, not to sys.modules: in a
        # full-suite run other test modules legitimately import sklearn, and
        # asserting on the global module table would make this test report on
        # them instead of on the Gate.
        bound = {
            name for name, value in vars(m).items()
            if getattr(value, "__name__", "") in FORBIDDEN_RUNTIME_MODULES
        }
        self.assertEqual(bound, set(),
                         f"forbidden runtime bound in the Gate: {bound}")

    def test_module_has_no_network_and_no_estimator_source(self):
        source = (ROOT / "project/src/"
                  "stage128_m3_lag_wdi_exploratory_data_gate.py"
                  ).read_text(encoding="utf-8")
        runner = (ROOT / "project/"
                  "run_stage128_m3_lag_wdi_exploratory_data_gate.py"
                  ).read_text(encoding="utf-8")
        for text in (source, runner):
            for token in ("urllib", "requests.", "http.client", "socket",
                          "sklearn", "xgboost", "fit_predict",
                          "predict_proba"):
                self.assertNotIn(token, text)

    def test_authorization_is_step_d_specific_and_single_use(self):
        record = m.verify_human_authorization()
        self.assertIn("STEP D / DATA GATE ONLY", record["authorization_text"])
        self.assertIn(m.ACTION_ID, record["authorization_text"])
        raw = record["authorization_text"].encode("utf-8")
        self.assertEqual(record["authorization_utf8_bytes"], len(raw))
        self.assertEqual(record["authorization_sha256"],
                         hashlib.sha256(raw).hexdigest())
        self.assertTrue(record["authorization_is_single_use"])
        for field in ("authorization_covers_modeling",
                      "authorization_covers_final_test",
                      "authorization_covers_new_retrieval",
                      "authorization_covers_step_e",
                      "prior_step_c_authorization_reused",
                      "standing_authorization"):
            self.assertFalse(record[field], field)

    def test_authorization_digest_differs_from_all_prior_steps(self):
        digest = m.verify_human_authorization()["authorization_sha256"]
        prior = {
            # contract lock (step A) and retrieval (step B), from handoff
            "0c1e10496bfba98d5ae4a6a3a8bf593a42258388fce1003c4cc36e6cdee4995b",
            "b409e0a53d255955199c59005d39f911ae272713dbf85c38651cd0dcfd5ba604",
        }
        from src import (
            stage128_m3_lag_wdi_exploratory_post_retrieval_audit as step_c)
        prior.add(step_c.verify_human_authorization()["authorization_sha256"])
        self.assertNotIn(digest, prior)


class TestLockedInputs(unittest.TestCase):
    def test_thresholds_come_from_locked_contract_and_ancestor(self):
        thresholds = m.load_locked_thresholds(ROOT)
        self.assertEqual(thresholds["candidate_valid_coverage_min"], 0.80)
        self.assertEqual(thresholds["block_common_sample_coverage_min"], 0.70)
        self.assertEqual(
            thresholds[
                "minimum_positive_evaluable_each_locked_validation_window"],
            5)
        self.assertEqual(thresholds["coverage_scope"], "development_only")
        self.assertFalse(thresholds["thresholds_changed_by_this_action"])
        self.assertEqual(thresholds["thresholds_source"], m.GATE_CONTRACT_REL)

    def test_threshold_drift_fails_closed(self):
        import tempfile
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            for rel in (m.GATE_CONTRACT_REL, m.THRESHOLD_ANCESTOR_REL):
                dest = tmp_root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(ROOT / rel, dest)
            doc = json.loads(
                (tmp_root / m.GATE_CONTRACT_REL).read_text(encoding="utf-8"))
            doc["thresholds"]["candidate_valid_coverage_min"] = 0.5
            (tmp_root / m.GATE_CONTRACT_REL).write_text(
                json.dumps(doc), encoding="utf-8")
            with self.assertRaises(m.M3LagWdiDataGateError):
                m.load_locked_thresholds(tmp_root)

    def test_feature_contract_is_the_locked_two_feature_contract(self):
        contract = m.verify_locked_feature_contract(ROOT)
        self.assertEqual(contract["cpi_indicator_code"], "FP.CPI.TOTL.ZG")
        self.assertEqual(contract["fx_indicator_code"], "PA.NUS.FCRF")
        self.assertFalse(contract["imputation_permitted"])
        self.assertFalse(
            contract["predictor_year_calendar_mapping_locked_by_contract"])

    def test_parent_surface_is_the_539_row_retained_m2_sample(self):
        rows, surface = m.derive_parent_surface(ROOT)
        self.assertEqual(len(rows), 539)
        self.assertEqual(surface["parent_rows"], 539)
        self.assertEqual(surface["parent_positive"], 55)
        self.assertEqual(surface["parent_negative"], 484)
        self.assertEqual(surface["parent_companies"], 108)
        self.assertEqual(surface["final_test_rows_in_parent_surface"], 0)

    def test_validation_targets_reconcile_with_committed_audit(self):
        validation = m.derive_validation_targets(ROOT)
        self.assertEqual(
            validation["window_counts"]["fold1_validation"]["positive"], 18)
        self.assertEqual(
            validation["window_counts"]["fold2_validation"]["positive"], 10)


class TestRowStatusSemantics(unittest.TestCase):
    def test_cpi_needs_t_minus_1_only(self):
        cpi = {2018: 30.0}
        fx = {}
        s = m.row_feature_status(cpi, fx, 1398, 621)
        self.assertEqual(s["predictor_year_gregorian"], 2019)
        self.assertTrue(s["cpi_constructible"])
        self.assertFalse(s["fx_constructible"])
        self.assertFalse(s["both_constructible"])

    def test_fx_needs_two_consecutive_strictly_positive_observations(self):
        cpi = {2018: 30.0}
        base = {2017: 100.0, 2018: 110.0}
        self.assertTrue(m.row_feature_status(
            cpi, base, 1398, 621)["fx_constructible"])
        for bad in ({2017: None, 2018: 110.0}, {2017: 0.0, 2018: 110.0},
                    {2017: -1.0, 2018: 110.0}, {2018: 110.0},
                    {2017: True, 2018: 110.0}):
            self.assertFalse(m.row_feature_status(
                cpi, bad, 1398, 621)["fx_constructible"], bad)

    def test_fx_zero_change_is_a_status_not_a_null(self):
        cpi = {2018: 30.0}
        pegged = {2017: 42000, 2018: 42000}
        s = m.row_feature_status(cpi, pegged, 1398, 621)
        self.assertTrue(s["fx_constructible"])
        self.assertTrue(s["fx_zero_change"])
        self.assertTrue(s["both_constructible"])

    def test_verdict_unresolved_when_conventions_disagree(self):
        # An observation axis with a hole at exactly one convention's t-1
        # makes the row's status mapping-dependent; the Gate must refuse to
        # choose and return UNRESOLVED.
        cpi = {y: 10.0 for y in range(2010, 2021) if y != 2014}
        fx = {y: float(100 + y) for y in range(2008, 2021)}
        parent_rows = [{"ticker": "X", "fiscal_year_t": "1393",
                        "target_year": "1394", "temporal_folds": "f"}]
        thresholds = m.load_locked_thresholds(ROOT)
        validation = {
            "targets_by_row": {f: {} for f in m.LOCKED_VALIDATION_WINDOWS},
            "window_counts": {f: {"rows": 0, "positive": 0}
                              for f in m.LOCKED_VALIDATION_WINDOWS}}
        gate = m.compute_gate(
            ROOT, {m.CPI_CODE: cpi, m.FX_CODE: fx}, parent_rows, thresholds,
            validation)
        self.assertFalse(
            gate["status_invariant_across_calendar_conventions"])
        self.assertEqual(gate["verdict"], m.GATE_STATUS_UNRESOLVED)

    def test_missing_coverage_is_a_fail_not_a_repair(self):
        # Both conventions agree the features are missing -> honest FAIL.
        parent_rows = [{"ticker": "X", "fiscal_year_t": "1393",
                        "target_year": "1394", "temporal_folds": "f"}]
        thresholds = m.load_locked_thresholds(ROOT)
        validation = {
            "targets_by_row": {f: {} for f in m.LOCKED_VALIDATION_WINDOWS},
            "window_counts": {f: {"rows": 0, "positive": 0}
                              for f in m.LOCKED_VALIDATION_WINDOWS}}
        gate = m.compute_gate(
            ROOT, {m.CPI_CODE: {}, m.FX_CODE: {}}, parent_rows, thresholds,
            validation)
        self.assertTrue(
            gate["status_invariant_across_calendar_conventions"])
        self.assertEqual(gate["verdict"], m.GATE_STATUS_FAIL)


class TestCommittedPackage(unittest.TestCase):
    """The committed step D package, exactly as a future reader will find it."""

    @classmethod
    def setUpClass(cls):
        if not PACKAGE_DIR.is_dir():
            raise unittest.SkipTest("step D package not built yet")

    def test_metadata_hashes_match_package_bytes(self):
        metadata = _load(
            "metadata_and_hashes_stage128_m3_lag_wdi_exploratory_data_gate"
            ".json")
        self.assertGreaterEqual(len(metadata["package_files"]), 11)
        for filename, record in metadata["package_files"].items():
            path = PACKAGE_DIR / filename
            self.assertTrue(path.is_file(), filename)
            blob = path.read_bytes()
            self.assertEqual(len(blob), record["bytes"], filename)
            self.assertEqual(hashlib.sha256(blob).hexdigest(),
                             record["sha256"], filename)

    def test_verdict_and_coverage_are_internally_consistent(self):
        report = _load("stage128_m3_lag_wdi_data_gate_report.json")
        decision = _load("stage128_m3_lag_wdi_data_gate_decision.json")
        gate = report["gate_computation"]
        self.assertEqual(gate["rows"], 539)
        self.assertIn(decision["gate_result"], m.GATE_STATUS_VOCABULARY)
        recomputed_pass = (
            gate["status_invariant_across_calendar_conventions"]
            and all(gate["threshold_checks"].values()))
        self.assertEqual(decision["gate_result"] == m.GATE_STATUS_PASS,
                         recomputed_pass)
        self.assertEqual(
            gate["cpi_candidate_coverage"],
            gate["cpi_constructible_rows"] / gate["rows"])
        self.assertEqual(
            gate["block_common_sample_coverage"],
            gate["both_constructible_rows"] / gate["rows"])

    def test_row_status_csv_has_539_rows_and_supports_the_counts(self):
        with (PACKAGE_DIR /
              "stage128_m3_lag_wdi_data_gate_row_status_audit.csv").open(
                  encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(len(rows), 539)
        report = _load("stage128_m3_lag_wdi_data_gate_report.json")
        gate = report["gate_computation"]
        self.assertEqual(
            sum(1 for r in rows if r["both_constructible"] == "True"),
            gate["both_constructible_rows"])
        self.assertEqual(
            sum(1 for r in rows if r["fx_zero_change"] == "True"),
            gate["fx_zero_change_rows"])
        for r in rows:
            self.assertEqual(
                r["status_invariant_across_calendar_conventions"], "True")
            self.assertNotIn(r["target_year"], m.FINAL_TEST_TARGET_YEARS)

    def test_no_feature_value_table_exists_in_the_package(self):
        # The calendar mapping is unlocked, so a value-level feature table
        # must not exist anywhere in the committed package.
        for path in PACKAGE_DIR.iterdir():
            self.assertNotIn("development_features", path.name)
            self.assertNotIn("normalized_observations", path.name)
        with (PACKAGE_DIR /
              "stage128_m3_lag_wdi_data_gate_row_status_audit.csv").open(
                  encoding="utf-8") as fh:
            header = fh.readline()
        for forbidden in ("value", "cpi_inflation,", "fx_change"):
            self.assertNotIn(forbidden, header)

    def test_pass_is_data_admission_only_everywhere(self):
        decision = _load("stage128_m3_lag_wdi_data_gate_decision.json")
        boundary = _load(
            "stage128_m3_lag_wdi_data_gate_governance_boundary.json")
        self.assertTrue(decision["admission_is_data_admission_only"])
        self.assertFalse(decision["gate_pass_authorizes_modeling"])
        self.assertFalse(decision["gate_pass_unlocks_final_test"])
        self.assertFalse(decision["authorizes_next_action"])
        self.assertFalse(decision["next_action_authorized"])
        for field in ("gate_pass_is_modeling_authorization",
                      "gate_pass_is_information_content_claim",
                      "gate_pass_is_final_test_unlock",
                      "gate_authorization_propagates_to_step_e",
                      "m3_lag_wdi_modeling_authorized",
                      "m3_lag_wdi_modeling_started",
                      "m3_lag_wdi_next_action_authorized",
                      "final_test_access_authorized",
                      "merge_authorized", "ready_for_review_authorized"):
            self.assertFalse(boundary[field], field)
        for field in ("m3_lag_wdi_data_gate_executed",
                      "m3_lag_wdi_data_gate_authorization_consumed",
                      "final_test_locked",
                      "step_c_material_findings_preserved"):
            self.assertTrue(boundary[field], field)
        self.assertFalse(boundary["m3_lag_wdi_data_gate_authorized_now"])
        self.assertFalse(
            boundary["m3_lag_wdi_data_gate_authorization_reusable"])

    def test_execution_counters_hold_the_boundary(self):
        audit = _load("stage128_m3_lag_wdi_data_gate_execution_audit.json")
        self.assertTrue(audit["data_gate_executed"])
        self.assertEqual(audit["data_gate_executions"], 1)
        for counter in ("world_bank_api_requests", "new_payloads_retrieved",
                        "model_fits", "predictions", "tuning_runs",
                        "cross_validation_runs", "model_selections",
                        "shap_executions",
                        "feature_value_tables_materialized",
                        "final_test_rows_read",
                        "final_test_predictor_values_read",
                        "final_test_target_values_read"):
            self.assertEqual(audit[counter], 0, counter)

    def test_step_c_findings_survive_verbatim(self):
        decision = _load("stage128_m3_lag_wdi_data_gate_decision.json")
        step_c = json.loads(
            (ROOT / m.STEP_C_DECISION_REL).read_text(encoding="utf-8"))
        self.assertEqual(decision["step_c_result_preserved"],
                         "PASS_WITH_MATERIAL_FINDINGS")
        self.assertEqual(decision["step_c_material_limitations_preserved"],
                         step_c["material_limitations"])
        distinctions = decision["scientific_distinctions"]
        self.assertEqual(
            set(distinctions),
            {"A_syntactic_availability_and_coverage",
             "B_pre_defined_thresholds_satisfied",
             "C_information_content_limitation_from_step_c",
             "D_effect_on_the_formal_gate_decision",
             "E_remaining_scientific_limitation"})
        self.assertFalse(
            distinctions["D_effect_on_the_formal_gate_decision"][
                "new_rejection_criterion_created"])
        self.assertTrue(
            distinctions["E_remaining_scientific_limitation"][
                "limitation_survives_the_pass"])

    def test_no_exclusion_and_no_criteria_change(self):
        decision = _load("stage128_m3_lag_wdi_data_gate_decision.json")
        self.assertEqual(decision["exclusions"], [])
        self.assertEqual(decision["rows_excluded"], 0)
        self.assertFalse(decision["thresholds_changed_to_obtain_result"])
        self.assertFalse(decision["criteria_weakened"])
        self.assertFalse(
            decision["criteria_strengthened_after_seeing_result"])
        self.assertFalse(decision["imputation_used"])
        self.assertFalse(decision["alternative_indicator_tried"])

    def test_qc_all_pass(self):
        qc = _load("stage128_m3_lag_wdi_data_gate_qc_report.json")
        self.assertTrue(qc["all_pass"])
        self.assertEqual(qc["checks_failed"], 0)

    def test_calendar_mapping_gap_is_recorded_not_hidden(self):
        decision = _load("stage128_m3_lag_wdi_data_gate_decision.json")
        boundary = _load(
            "stage128_m3_lag_wdi_data_gate_governance_boundary.json")
        self.assertTrue(
            decision["calendar_mapping_lock_required_before_modeling"])
        self.assertFalse(boundary["m3_lag_wdi_calendar_mapping_locked"])
        self.assertTrue(any("Jalali" in item or "mapping" in item
                            for item in decision["material_limitations"]))


if __name__ == "__main__":
    unittest.main()
