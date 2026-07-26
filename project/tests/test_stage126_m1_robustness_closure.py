"""Tests for Stage126 M1 — Robustness Closure (synthesis-only).

These tests confirm: build/check determinism; the 18-row evidence matrix
reconciles independently against the source Part 1-6 artifacts; the closure
source performs no model-fit/prediction/resampling/network calls (AST/token
scan); completion-lock fields are exact; consumed Part 1-6/primary artifacts
are byte-identical before and after running the closure; and all final-test
lock fields are False.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import json
import os
from pathlib import Path

import pytest

from src import stage126_m1_robustness_closure as closure

REAL_ROOT = Path(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
STAGE126 = REAL_ROOT / "project" / "stage126"

FORBIDDEN_TOKENS = (
    "import shap", "SMOTE(", "SMOTENC(", ".fit(", ".fit_resample(", ".predict(",
    "predict_proba", "GridSearchCV", "RandomizedSearchCV", "urllib",
    "import requests", "socket.", "http.client",
)
FORBIDDEN_IMPORT_MODULES = (
    "sklearn", "xgboost", "imblearn", "shap", "requests", "urllib", "socket",
)


def _src_text() -> str:
    return (REAL_ROOT / closure.SRC_REL).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# Zero-execution firewall
# --------------------------------------------------------------------------- #

def test_source_has_no_forbidden_tokens():
    text = _src_text()
    for tok in FORBIDDEN_TOKENS:
        assert tok not in text, f"forbidden token present: {tok}"


def test_source_ast_has_no_forbidden_imports():
    tree = ast.parse(_src_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                assert top not in FORBIDDEN_IMPORT_MODULES, (
                    f"forbidden import: {alias.name}"
                )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                assert top not in FORBIDDEN_IMPORT_MODULES, (
                    f"forbidden import-from: {node.module}"
                )


def test_no_network_sockets_opened():
    text = _src_text()
    assert "socket.socket" not in text
    assert "urlopen" not in text


# --------------------------------------------------------------------------- #
# Build / check determinism
# --------------------------------------------------------------------------- #

def test_build_all_deterministic_across_two_calls():
    content1, extras1 = closure.build_all(REAL_ROOT)
    content2, extras2 = closure.build_all(REAL_ROOT)
    assert content1 == content2
    assert extras1["rows"] == extras2["rows"]
    assert extras1["synthesis"] == extras2["synthesis"]
    assert extras1["lock"] == extras2["lock"]


def test_run_build_then_check_no_drift(tmp_path):
    out1 = closure.run(
        project_dir=REAL_ROOT / "project", output_dir=tmp_path, build=True,
    )
    out2 = closure.run(
        project_dir=REAL_ROOT / "project", output_dir=tmp_path, check=True,
    )
    assert out2["drift"] == []
    assert out1["qc"]["all_pass"] is True
    assert out2["qc"]["all_pass"] is True


def test_on_disk_artifacts_match_fresh_build():
    content, _extras = closure.build_all(REAL_ROOT)
    for name, text in content.items():
        on_disk = (STAGE126 / name).read_text(encoding="utf-8")
        assert on_disk == text, f"drift in {name}"


# --------------------------------------------------------------------------- #
# 18-row evidence matrix reconciliation
# --------------------------------------------------------------------------- #

def test_evidence_table_has_18_rows_on_disk():
    with open(STAGE126 / closure.F_EVIDENCE_TABLE, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 18
    assert {r["part_index"] for r in rows} == {str(i) for i in range(1, 7)}
    assert {r["model_family"] for r in rows} == set(closure.MODEL_FAMILIES)


def test_evidence_table_reconciles_independently_against_source_artifacts():
    """Recompute pooled PR-AUC deltas independently and compare to the on-disk
    evidence table, without reusing the closure's own row-building function
    for the comparison values (guards against a bug shared by both paths)."""
    primary_rows = list(
        csv.DictReader(
            open(REAL_ROOT / closure.PRIMARY_METRICS_REL, encoding="utf-8", newline="")
        )
    )
    primary_pooled = {
        r["model_family"]: float(r["pr_auc"])
        for r in primary_rows if r["scope"] == "pooled_development_oof"
    }

    with open(STAGE126 / closure.F_EVIDENCE_TABLE, encoding="utf-8", newline="") as f:
        table_rows = list(csv.DictReader(f))

    for part in closure.PARTS:
        n = part["part_index"]
        metrics_path = REAL_ROOT / f"project/stage126/stage126_m1_robustness_part{n}_metrics.csv"
        part_rows = list(csv.DictReader(open(metrics_path, encoding="utf-8", newline="")))
        part_pooled = {
            r["model_family"]: float(r["pr_auc"])
            for r in part_rows if r["scope"] == "pooled_development_oof"
        }
        for fam in closure.MODEL_FAMILIES:
            expected_abs = part_pooled[fam] - primary_pooled[fam]
            table_row = next(
                r for r in table_rows
                if int(r["part_index"]) == n and r["model_family"] == fam
            )
            assert abs(float(table_row["primary_pooled_pr_auc"]) - primary_pooled[fam]) < 1e-9
            assert abs(float(table_row["robustness_pooled_pr_auc"]) - part_pooled[fam]) < 1e-9
            assert abs(float(table_row["absolute_delta_vs_primary"]) - expected_abs) < 1e-9


def test_part1_all_families_declined_and_ordering_differs():
    with open(STAGE126 / closure.F_EVIDENCE_TABLE, encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f) if int(r["part_index"]) == 1]
    assert len(rows) == 3
    for r in rows:
        assert float(r["absolute_delta_vs_primary"]) < 0
        assert r["primary_ordering_preserved"] == "false"


def test_parts_2_through_6_ordering_preserved():
    with open(STAGE126 / closure.F_EVIDENCE_TABLE, encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f) if int(r["part_index"]) != 1]
    assert len(rows) == 15
    for r in rows:
        assert r["primary_ordering_preserved"] == "true"


def test_all_rows_final_test_never_accessed():
    with open(STAGE126 / closure.F_EVIDENCE_TABLE, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        assert r["final_test_accessed_or_evaluated"] == "false"
        assert r["development_only"] == "true"
        assert r["selected_configurations_changed"] == "false"


def test_changed_dimension_flags_one_factor_at_a_time():
    with open(STAGE126 / closure.F_EVIDENCE_TABLE, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        flags = {
            "sample_changed": r["sample_changed"] == "true",
            "target_changed": r["target_changed"] == "true",
            "feature_set_changed": r["feature_set_changed"] == "true",
            "imbalance_strategy_changed": r["imbalance_strategy_changed"] == "true",
        }
        assert sum(flags.values()) == 1, f"expected exactly one changed dimension: {flags}"


# --------------------------------------------------------------------------- #
# Synthesis record
# --------------------------------------------------------------------------- #

def _synthesis() -> dict:
    with open(STAGE126 / closure.F_SYNTHESIS_RECORD, encoding="utf-8") as f:
        return json.load(f)


def test_synthesis_record_registered_categories_in_order():
    rec = _synthesis()
    assert rec["registered_categories_in_order"] == [
        "m1_target_proximity_six_feature_set",
        "main_rule_b_listing_robustness",
        "expanded_rule_a_company_scope_robustness",
        "expanded_rule_b_combined_robustness",
        "persistent_loss_robustness_target",
        "smote_training_fold_only_robustness",
    ]


def test_synthesis_record_interpretation_findings_present():
    rec = _synthesis()
    interp = rec["scientific_interpretation"]
    for key in (
        "A_model_family_ordering", "B_sample_definition_sensitivity",
        "C_target_sensitivity", "D_imbalance_strategy_sensitivity",
        "E_overall_synthesis",
    ):
        assert key in interp
        assert isinstance(interp[key]["finding"], str) and interp[key]["finding"]


def test_synthesis_record_no_selection_or_freeze():
    rec = _synthesis()
    assert rec["paper_winner_selected"] is False
    assert rec["retained_design_selected"] is False
    assert rec["retained_design_freeze_authorized"] is False
    assert rec["next_action_id"] == "stage126-m1-retained-design-freeze"
    assert rec["next_action_requires_separate_human_authorization"] is True


def test_synthesis_record_prohibited_actions_list():
    rec = _synthesis()
    for action in (
        "winner_selection", "retained_design_freeze", "retuning",
        "final_test_access", "final_test_evaluation", "shap",
        "paired_bootstrap", "holm_correction",
    ):
        assert action in rec["prohibited_actions"]


def test_synthesis_record_target_sensitivity_caveat():
    rec = _synthesis()
    c_finding = rec["scientific_interpretation"]["C_target_sensitivity"]
    assert c_finding["development_positive_count_primary"] == 68
    assert c_finding["development_positive_count_persistent_loss"] == 85
    assert c_finding["development_positive_count_delta"] == 17


# --------------------------------------------------------------------------- #
# Completion lock: exact fields
# --------------------------------------------------------------------------- #

def _lock() -> dict:
    with open(STAGE126 / closure.F_COMPLETION_LOCK, encoding="utf-8") as f:
        return json.load(f)


def test_completion_lock_exact_fields():
    lock = _lock()
    exact_true = (
        "robustness_closure_completed", "all_six_registered_categories_verified",
    )
    exact_false = (
        "paper_winner_selected", "retained_design_selected",
        "retained_design_freeze_authorized", "full_development_refit_performed",
        "final_test_unlocked", "final_test_access_authorized",
        "final_test_predictor_values_inspected",
        "final_test_target_values_inspected", "final_test_evaluation_performed",
        "smote_executed", "smotenc_executed", "shap_executed",
        "calibration_executed", "bootstrap_executed", "holm_executed",
        "p_values_computed", "threshold_optimization_executed",
        "m2_data_collected", "m3_data_collected", "m4_data_collected",
        "m2_started", "m3_started", "m4_started",
    )
    for f in exact_true:
        assert lock[f] is True, f
    for f in exact_false:
        assert lock[f] is False, f
    assert lock["model_fit_calls"] == 0
    assert lock["prediction_calls"] == 0
    assert lock["tuning_search_calls"] == 0
    assert lock["next_action_id"] == "stage126-m1-retained-design-freeze"
    assert lock["completed_category_ids"] == [p["category_id"] for p in closure.PARTS]


def test_completion_lock_final_test_lock_fields_all_false():
    lock = _lock()
    for field in (
        "final_test_unlocked", "final_test_access_authorized",
        "final_test_predictor_values_inspected",
        "final_test_target_values_inspected",
        "final_test_evaluation_performed",
    ):
        assert lock[field] is False


# --------------------------------------------------------------------------- #
# Source manifest
# --------------------------------------------------------------------------- #

def test_source_manifest_pins_all_consumed_artifacts():
    with open(STAGE126 / closure.F_SOURCE_MANIFEST, encoding="utf-8") as f:
        manifest = json.load(f)
    consumed = manifest["consumed_source_artifacts_sha256"]
    assert closure.PRIMARY_METRICS_REL in consumed
    assert closure.REGISTRY_REL in consumed
    for part in closure.PARTS:
        for rel in closure._part_artifact_rels(part["part_index"]).values():
            assert rel in consumed
            expected = hashlib.sha256((REAL_ROOT / rel).read_bytes()).hexdigest()
            assert consumed[rel] == expected

    generated = manifest["generated_output_sha256"]
    for name in (
        closure.F_EVIDENCE_TABLE, closure.F_SYNTHESIS_RECORD,
        closure.F_COMPLETION_LOCK, closure.F_README,
    ):
        assert name in generated

    # No recursive self-reference: the manifest never hashes its own QC report
    # or itself.
    assert closure.F_QC not in generated
    assert closure.F_SOURCE_MANIFEST not in generated


# --------------------------------------------------------------------------- #
# Immutability of consumed Part 1-6 / primary artifacts
# --------------------------------------------------------------------------- #

def test_consumed_artifacts_immutable_before_and_after_build():
    before = closure.verify_closed_parts_immutable(REAL_ROOT)
    closure.build_all(REAL_ROOT)  # in-memory only; no writes performed here.
    after = closure.verify_closed_parts_immutable(REAL_ROOT)
    assert before == after


def test_run_check_does_not_mutate_consumed_artifacts():
    before = closure.verify_closed_parts_immutable(REAL_ROOT)
    closure.run(project_dir=REAL_ROOT / "project", check=True)
    after = closure.verify_closed_parts_immutable(REAL_ROOT)
    assert before == after


# --------------------------------------------------------------------------- #
# QC report
# --------------------------------------------------------------------------- #

def test_qc_report_all_pass_and_zero_execution_counters():
    with open(STAGE126 / closure.F_QC, encoding="utf-8") as f:
        qc = json.load(f)
    assert qc["all_pass"] is True
    assert qc["failed_count"] == 0
    assert qc["model_fit_calls"] == 0
    assert qc["prediction_calls"] == 0
    assert qc["smote_calls"] == 0
    assert qc["smotenc_calls"] == 0
    assert qc["shap_calls"] == 0
    assert qc["network_requests_attempted"] == 0
    assert qc["final_test_predictor_rows_loaded"] == 0
    assert qc["final_test_target_rows_loaded"] == 0
    assert qc["final_test_evaluations"] == 0
    assert qc["robustness_closure_completed"] is True
    assert qc["next_action_id"] == "stage126-m1-retained-design-freeze"


def test_registered_categories_match_closed_part_registry():
    ids = closure.load_registered_categories(REAL_ROOT)
    assert ids == [p["category_id"] for p in closure.PARTS]


def test_missing_consumed_artifact_fails_closed(tmp_path):
    import shutil
    # Mirror the repo minimally then delete one consumed artifact.
    shutil.copytree(
        REAL_ROOT / "project" / "stage126", tmp_path / "project" / "stage126"
    )
    victim = tmp_path / "project/stage126/stage126_m1_robustness_part3_metrics.csv"
    victim.unlink()
    with pytest.raises(closure.QCFail):
        closure.build_evidence_rows(tmp_path, {
            fam: 0.4 for fam in closure.MODEL_FAMILIES
        })
