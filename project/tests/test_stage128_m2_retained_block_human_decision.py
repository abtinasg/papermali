"""Focused tests — ``stage128-m2-retained-block-human-decision``.

These tests are decision-package tests. They read committed artifacts, rebuild
the package in memory and assert the governance invariants. They deliberately
run NO scientific computation: no model is fit, nothing is predicted, nothing
is resampled, no final-test value is touched, and no PR #71 artifact is
regenerated.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "project"))

from src import stage128_m2_retained_block_human_decision as d  # noqa: E402

PKG = REPO_ROOT / d.PACKAGE_DIR_REL


def _load(rel: str) -> dict:
    return json.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    """Read-only git in the repository root, computed here independently."""
    import subprocess

    out = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return out.stdout


@pytest.fixture(scope="module")
def metadata() -> dict:
    return _load(d.METADATA_REL)


@pytest.fixture(scope="module")
def decision() -> dict:
    return _load(d.DECISION_REL)


@pytest.fixture(scope="module")
def authorization() -> dict:
    return _load(d.AUTHORIZATION_REL)


@pytest.fixture(scope="module")
def qc() -> dict:
    return _load(d.QC_REL)


@pytest.fixture(scope="module")
def metadata() -> dict:
    return _load(d.METADATA_REL)


# --------------------------------------------------------------------------- #
# 1-2. Exact authorization, verbatim vs derived
# --------------------------------------------------------------------------- #

def test_authorization_byte_length_and_sha_are_exact():
    raw = d.HUMAN_SOURCE_UTTERANCE.encode("utf-8")
    assert len(raw) == 240
    assert hashlib.sha256(raw).hexdigest() == (
        "91edbdedbf69fd3af4ec5a378b1b0506ed4df941f1331be91755068c6fb6e2b4")
    assert not d.HUMAN_SOURCE_UTTERANCE.endswith("\n")


def test_authorization_record_is_the_only_home_of_the_verbatim_text(
    authorization, decision,
):
    assert authorization["human_source_utterance"] == d.HUMAN_SOURCE_UTTERANCE
    assert authorization["human_source_utterance_byte_length"] == 240
    assert authorization["human_source_utterance_sha256"] == (
        d.HUMAN_SOURCE_UTTERANCE_SHA256)
    assert authorization["human_source_utterance_is_verbatim_human_text"]
    blob = json.dumps(decision, ensure_ascii=False)
    assert d.HUMAN_SOURCE_UTTERANCE not in blob
    assert decision["human_source_utterance_duplicated_here"] is False


def test_normalized_scope_is_labelled_derived_and_kept_separate(authorization):
    assert authorization[
        "normalized_authorization_scope_is_derived_not_verbatim_human_text"
    ] is True
    assert authorization["normalized_authorization_scope"] != (
        d.HUMAN_SOURCE_UTTERANCE)
    assert authorization["verbatim_and_normalized_are_recorded_separately"]
    assert authorization["normalized_authorization_scope_sha256"] == (
        hashlib.sha256(
            authorization["normalized_authorization_scope"].encode("utf-8")
        ).hexdigest())


def test_authorization_is_one_action_and_creates_no_standing_grant(
    authorization, decision,
):
    assert authorization["authorized_action_id"] == d.ACTION_ID
    assert authorization["scope_limited_to_this_action_only"] is True
    assert authorization["creates_standing_authorization"] is False
    assert authorization["merge_authorized"] is False
    assert decision["authorization_consumed"] is True
    assert decision[
        "m2_retained_block_human_decision_authorization_consumed"] is True


def test_decision_references_the_authorization_record_by_path_and_sha(
    decision,
):
    assert decision["human_authorization_record_path"] == d.AUTHORIZATION_REL
    on_disk = hashlib.sha256(
        (REPO_ROOT / d.AUTHORIZATION_REL).read_bytes()).hexdigest()
    assert decision["human_authorization_record_sha256"] == on_disk


# --------------------------------------------------------------------------- #
# 3-8. Baseline, outcome, retention semantics
# --------------------------------------------------------------------------- #

def test_baseline_commit_is_the_canonical_main_sha(decision, authorization):
    expected = "bdac807788b377690be0a879765cfe4ac148970d"
    assert decision["source_main_commit"] == expected
    assert authorization["source_main_commit"] == expected
    assert decision["source_repository"] == "abtinasg/papermali"


def test_decision_outcome_and_type(decision):
    assert decision["decision_outcome"] == (
        "RETAIN_M2_AS_INTERMEDIATE_CONFIRMATORY_BLOCK")
    assert decision["decision_type"] == (
        "human_retained_block_decision_only_no_scientific_execution")
    assert decision["action_id"] == "stage128-m2-retained-block-human-decision"
    assert decision["decision_id"] == decision["action_id"]


def test_m2_is_retained_as_the_intermediate_block(decision):
    assert decision["m2_block_retained"] is True
    assert decision["m2_role"] == "intermediate_confirmatory_block"
    assert decision["nested_confirmatory_chain"] == ["M1", "M2", "M3", "M4"]
    assert decision["m2_remains_comparator_for"] == "M3_minus_M2"
    assert "separately authorized" in decision["m3_minus_m2_conditional_on"]
    assert decision["m2_retained_block_decision_required"] is False
    assert decision["m2_retained_block_human_decision_completed"] is True


def test_retention_is_not_a_superiority_claim(decision):
    assert decision["m2_predictive_superiority_claim_supported"] is False
    assert decision[
        "decision_is_a_retained_block_decision_not_a_superiority_decision"
    ] is True
    assert decision["m2_retention_basis"] == d.M2_RETENTION_BASIS
    for item in (
        "predictive_improvement", "statistical_significance",
        "paper_winner_selection", "final_model_selection",
        "full_development_refit_authorization",
        "final_test_unlock_or_access_authorization",
        "m3_authorization", "m4_authorization",
    ):
        assert item in decision["m2_retention_does_not_imply"]


def test_no_winner_and_no_final_model(decision):
    assert decision["paper_winner_selected"] is False
    assert decision["final_model_selected"] is False
    assert decision["full_development_refit_performed"] is False


def test_prose_never_claims_m2_improves_prediction():
    text = (REPO_ROOT / d.README_REL).read_text(encoding="utf-8").lower()
    for banned in (
        "m2 improves prediction", "improves prediction", "the best block",
        "best block", "m2 is superior", "m2 wins",
    ):
        assert banned not in text
    assert "approximately null" in text


# --------------------------------------------------------------------------- #
# 9-11. No scientific execution
# --------------------------------------------------------------------------- #

def test_execution_audit_is_all_zero(decision):
    audit = decision["execution_audit"]
    for key, value in audit.items():
        if isinstance(value, int) and not isinstance(value, bool):
            assert value == 0, key
    assert audit["built_only_by_reading_existing_committed_evidence"] is True


def test_builder_module_imports_no_estimator_or_resampling_runtime():
    d.assert_no_estimator_runtime()
    source = (REPO_ROOT / "project/src"
              / "stage128_m2_retained_block_human_decision.py").read_text(
        encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not imported & set(d.FORBIDDEN_RUNTIME_MODULES)


def test_builder_and_runner_call_no_estimator_entry_point():
    """The builder/validator cannot reach ``.fit()``/``.predict()``/resampling."""
    for rel in (
        "project/src/stage128_m2_retained_block_human_decision.py",
        "project/run_stage128_m2_retained_block_human_decision.py",
    ):
        tree = ast.parse((REPO_ROOT / rel).read_text(encoding="utf-8"))
        called = {
            node.func.attr for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
        }
        assert not called & set(d.FORBIDDEN_ESTIMATOR_CALLS), rel


def test_building_the_package_does_not_import_an_estimator_runtime():
    before = set(sys.modules)
    d.build_package(REPO_ROOT, write=False)
    new = set(sys.modules) - before
    assert not {m.split(".")[0] for m in new} & set(d.FORBIDDEN_RUNTIME_MODULES)


# --------------------------------------------------------------------------- #
# 12-15. Firewall and successors
# --------------------------------------------------------------------------- #

def test_final_test_remains_locked_and_uninspected(decision):
    assert decision["final_test_locked"] is True
    assert decision["final_test_unlocked"] is False
    assert decision["final_test_access_authorized"] is False
    assert decision["final_test_evaluation_performed"] is False
    assert decision["final_test_predictor_values_inspected"] is False
    assert decision["final_test_target_values_inspected"] is False


def test_m3_and_m4_remain_unauthorized_and_unstarted(decision):
    assert decision["m3_authorized"] is False
    assert decision["m3_started"] is False
    assert decision["m4_authorized"] is False
    assert decision["m4_started"] is False
    assert decision["execution_audit"]["m3_executions"] == 0
    assert decision["execution_audit"]["m4_executions"] == 0


def test_no_m3_artifact_was_created():
    stage128 = REPO_ROOT / "project/stage128"
    offenders = [
        p for p in stage128.rglob("*m3*")
        if p.is_file() and "macro" in p.name.lower()
    ]
    assert offenders == []


# --------------------------------------------------------------------------- #
# 16. Frozen M2 definition
# --------------------------------------------------------------------------- #

def test_exact_retained_m2_feature_definition(decision):
    rm2 = decision["retained_m2_definition"]
    assert rm2["m1_feature_order"] == [
        "log_total_assets",
        "leverage_ratio",
        "current_ratio",
        "roa_period_adjusted",
        "ocf_to_assets_period_adjusted",
        "asset_turnover_period_adjusted",
        "operating_margin_period_adjusted",
        "financial_expense_to_assets_period_adjusted",
        "accumulated_loss_to_capital_ratio",
    ]
    assert rm2["m2_added_features"] == [
        "equity_return_window", "realized_volatility", "amihud_illiquidity"]
    assert rm2["m2_feature_order"] == (
        rm2["m1_feature_order"] + rm2["m2_added_features"])
    assert rm2["equity_return_window_semantics"] == (
        "BOUNDARY_MONTH_ASOF_TRAILING_EQUITY_RETURN")
    assert rm2["equity_return_window_calendar_convention"] == "Gregorian"
    assert rm2["reopened_design_components"] == []


def test_zero_trade_day_ratio_remains_eligibility_audit_only(decision):
    rm2 = decision["retained_m2_definition"]
    assert "zero_trade_day_ratio_W" not in rm2["m2_feature_order"]
    assert rm2["audit_only_field_not_in_m2"] == "zero_trade_day_ratio_W"


def test_retained_definition_matches_the_committed_feature_manifest(decision):
    manifest = _load(d.SRC_FEATURE_MANIFEST_REL)
    rm2 = decision["retained_m2_definition"]
    assert manifest["m2_feature_order"] == rm2["m2_feature_order"]
    assert manifest["m1_feature_order"] == rm2["m1_feature_order"]
    assert manifest["equity_return_window_implementation"] == (
        rm2["equity_return_window_semantics"])


# --------------------------------------------------------------------------- #
# 17-23. Source-derived evidence
# --------------------------------------------------------------------------- #

def test_exact_common_sample_counts(decision):
    counts = decision["source_derived_evidence"]["counts"]["common_sample"]
    assert counts == {
        "rows": 539, "parent_rows": 666, "positive": 55, "negative": 484,
        "companies": 108,
    }


def test_exact_attrition_counts(decision):
    a = decision["source_derived_evidence"]["counts"]["attrition"]
    assert a["rows"] == 127
    assert a["parent_rows"] == 666
    assert a["positive"] == 13
    assert a["negative"] == 114
    assert a["distinct_companies"] == 53
    assert abs(a["fraction"] - 0.190690690691) < 1e-12


def test_exact_pooled_oof_counts(decision):
    pooled = decision["source_derived_evidence"]["counts"][
        "pooled_locked_validation_oof"]
    assert pooled == {"rows": 366, "positive": 28}


def test_exact_eligibility_audit_counts(decision):
    audit = decision["source_derived_evidence"]["counts"][
        "post_lock_d2_eligibility_audit"]
    assert audit["comparison_count"] == 53
    assert audit["flagged_comparison_count"] == 35
    assert audit["smd_flag_threshold"] == 0.1


def test_exact_pr_auc_deltas_and_intervals(decision):
    deltas = decision["source_derived_evidence"]["pr_auc_deltas"]
    expected = {
        "regularized_logistic_regression": (
            0.008530265112, -0.021177343686, 0.035281506756),
        "random_forest": (
            -0.007313160157, -0.049131999282, 0.031850216682),
        "xgboost": (
            0.018802067544, -0.026163341118, 0.072970509355),
    }
    for family, (delta, lo, hi) in expected.items():
        got = deltas[family]
        assert abs(got["m2_minus_m1_pr_auc"] - delta) < 1e-12
        assert abs(got["ci_lower"] - lo) < 1e-12
        assert abs(got["ci_upper"] - hi) < 1e-12


def test_all_intervals_include_zero(decision):
    deltas = decision["source_derived_evidence"]["pr_auc_deltas"]
    for family, got in deltas.items():
        assert got["ci_lower"] <= 0.0 <= got["ci_upper"], family
        assert got["interval_includes_zero"] is True
    assert decision["source_derived_evidence"][
        "all_primary_intervals_include_zero"] is True


def test_model_family_signs_disagree(decision):
    signs = decision["source_derived_evidence"]["observed_point_estimate_signs"]
    assert signs["random_forest"] == "negative"
    assert signs["regularized_logistic_regression"] == "positive"
    assert signs["xgboost"] == "positive"
    assert decision["source_derived_evidence"][
        "families_agree_on_point_estimate_sign"] is False


def test_null_result_is_preserved_and_reported(decision):
    assert decision[
        "approximately_null_m2_development_result_preserved_and_reported"
    ] is True
    joined = " ".join(decision["decision_rationale"]).lower()
    assert "approximately null" in joined
    assert "does not support a superiority claim" in joined
    assert "reportable scientific result" in joined


# --------------------------------------------------------------------------- #
# 24. Multiplicity family
# --------------------------------------------------------------------------- #

def test_holm_family_remains_incomplete_and_deferred(decision):
    assert decision["confirmatory_comparison_family"] == [
        "M2_minus_M1", "M3_minus_M2", "M4_minus_M3"]
    assert decision["confirmatory_comparison_family_unchanged"] is True
    assert decision["holm_family_complete"] is False
    assert decision["holm_final_adjustment_deferred"] is True
    source = _load(d.SRC_MULTIPLICITY_REL)
    assert source["holm_family_complete"] is False
    assert source["holm_final_adjustment_deferred"] is True


# --------------------------------------------------------------------------- #
# 25. Immutability
# --------------------------------------------------------------------------- #

def test_every_pinned_scientific_artifact_is_byte_identical(decision):
    for rel, sha in decision["source_artifacts_sha256"].items():
        on_disk = hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest()
        assert on_disk == sha, rel


def test_all_required_pr71_artifacts_are_pinned(decision):
    pinned = decision["source_artifacts_sha256"]
    for rel in d.PINNED_PR71_SOURCES + d.PINNED_EXTERNAL_SOURCES:
        assert rel in pinned


def test_protected_path_set_is_enumerated_from_the_baseline_commit():
    """The scope comes from the baseline commit, never from the worktree."""
    paths = d.enumerate_protected_baseline_files(REPO_ROOT)
    assert len(paths) == len(set(paths)) > 0
    assert tuple(sorted(paths)) == paths
    for rel in d.PROTECTED_EXTRA_FILES:
        assert rel in paths
    for rel in paths:
        assert rel in d.PROTECTED_EXTRA_FILES or rel.startswith(
            tuple(t + "/" for t in d.PROTECTED_TREES)), rel
    # independent enumeration, computed here, not read from the artifact
    listed = _git("ls-tree", "-r", "--name-only", d.BASELINE_COMMIT, "--",
                  *d.PROTECTED_TREES).split()
    assert set(paths) == set(listed) | set(d.PROTECTED_EXTRA_FILES)


def test_complete_protected_manifest_is_committed_in_the_package(
        decision, metadata):
    """Every protected baseline file has a committed SHA-256, not just 17."""
    paths = d.enumerate_protected_baseline_files(REPO_ROOT)
    for artifact in (decision, metadata):
        assert artifact["protected_baseline_commit"] == d.BASELINE_COMMIT
        assert artifact["protected_file_count"] == len(paths)
        manifest = artifact["protected_files_sha256"]
        assert len(manifest) == len(paths)
        assert tuple(sorted(manifest)) == paths
    assert decision["protected_files_sha256"] == metadata[
        "protected_files_sha256"]
    # the manifest is strictly larger than the re-derivation subset
    assert len(decision["protected_files_sha256"]) > len(
        decision["source_artifacts_sha256"])


def test_stored_manifest_equals_the_baseline_blob_hashes(decision):
    baseline = d.baseline_protected_manifest(REPO_ROOT)
    assert decision["protected_files_sha256"] == baseline


def test_every_protected_file_matches_baseline_bytes_on_this_branch(decision):
    for rel, sha in decision["protected_files_sha256"].items():
        path = REPO_ROOT / rel
        assert path.is_file(), rel
        assert hashlib.sha256(path.read_bytes()).hexdigest() == sha, rel


def test_protected_immutability_verifies_against_committed_history(decision):
    report = d.verify_protected_immutability(
        REPO_ROOT, decision["protected_files_sha256"])
    assert report["protected_baseline_commit"] == d.BASELINE_COMMIT
    assert report["protected_file_count"] == len(
        decision["protected_files_sha256"])
    assert report["protected_paths_match_baseline"] is True
    assert report["protected_bytes_match_baseline"] is True
    assert report["protected_tree_has_no_new_tracked_files"] is True
    assert report["protected_committed_history_diff_empty"] is True


def test_committed_history_not_worktree_is_compared_against_the_baseline():
    """The guard must compare BASELINE..HEAD, not the working tree vs HEAD."""
    source = (REPO_ROOT / "project/src"
              / "stage128_m2_retained_block_human_decision.py").read_text(
                  encoding="utf-8")
    assert f'f"{{BASELINE_COMMIT}}..HEAD"' in source
    # the ineffective working-tree-only guard must be gone from both files
    tests = Path(__file__).read_text(encoding="utf-8")
    # assembled at runtime so this assertion cannot match its own source line
    worktree_only = '", "'.join(["diff", "--name-only", "HEAD", '--"'])
    for text in (source, tests):
        assert ('"' + worktree_only) not in text
    changed = _git("diff", "--name-only", f"{d.BASELINE_COMMIT}..HEAD", "--",
                   *d.enumerate_protected_baseline_files(REPO_ROOT))
    assert changed.strip() == ""


# --------------------------------------------------------------------------- #
# 25b. Negative immutability tests — the guard must actually detect violations
# --------------------------------------------------------------------------- #

def _sandbox(tmp_path: Path) -> Path:
    """A shared-object clone of this repository, safe to mutate and commit."""
    import subprocess

    dest = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", "--quiet", "--shared", str(REPO_ROOT), str(dest)],
        check=True, capture_output=True,
    )
    for key, value in (("user.email", "qc@example.invalid"),
                       ("user.name", "qc")):
        subprocess.run(["git", "config", key, value], cwd=dest, check=True)
    return dest


def _commit(root: Path, message: str) -> None:
    import subprocess

    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", message],
                   cwd=root, check=True, capture_output=True)


@pytest.fixture(scope="module")
def manifest(decision) -> dict:
    return dict(decision["protected_files_sha256"])


def test_negative_committing_a_changed_protected_file_is_detected(
        tmp_path, manifest):
    root = _sandbox(tmp_path)
    target = next(iter(sorted(manifest)))
    (root / target).write_bytes(
        (root / target).read_bytes() + b"\n# tampered\n")
    _commit(root, "tamper: modify a protected file")
    with pytest.raises(d.RetainedBlockDecisionError) as exc:
        d.verify_protected_immutability(root, manifest)
    assert target in str(exc.value)


def test_negative_deleting_a_protected_file_is_detected(tmp_path, manifest):
    root = _sandbox(tmp_path)
    target = next(iter(sorted(manifest)))
    (root / target).unlink()
    _commit(root, "tamper: delete a protected file")
    with pytest.raises(d.RetainedBlockDecisionError) as exc:
        d.verify_protected_immutability(root, manifest)
    assert target in str(exc.value)


def test_negative_adding_a_tracked_file_in_a_protected_tree_is_detected(
        tmp_path, manifest):
    root = _sandbox(tmp_path)
    intruder = f"{d.PROTECTED_TREES[0]}/intruder.json"
    (root / intruder).write_text("{}\n", encoding="utf-8")
    _commit(root, "tamper: add a tracked file inside a protected tree")
    with pytest.raises(d.RetainedBlockDecisionError) as exc:
        d.verify_protected_immutability(root, manifest)
    assert "new tracked file" in str(exc.value)
    assert intruder in str(exc.value)


def test_negative_changing_a_stored_hash_is_detected(manifest):
    tampered = dict(manifest)
    target = next(iter(sorted(tampered)))
    tampered[target] = "0" * 64
    with pytest.raises(d.RetainedBlockDecisionError) as exc:
        d.verify_protected_immutability(REPO_ROOT, tampered)
    assert target in str(exc.value)


def test_negative_dropping_a_manifest_entry_is_detected(manifest):
    tampered = dict(manifest)
    target = next(iter(sorted(tampered)))
    del tampered[target]
    with pytest.raises(d.RetainedBlockDecisionError) as exc:
        d.verify_protected_immutability(REPO_ROOT, tampered)
    assert "count" in str(exc.value) or "path set differs" in str(exc.value)


def test_historical_gate_results_are_not_rewritten():
    rerun = _load("project/stage128/stage128_m2_d2_gate_rerun_decision.json")
    assert rerun["gate_status"] == "PASS_FOR_M2_INCREMENTAL_EVALUATION"
    assert rerun["historical_d0_gate_status"] == "FAIL_M2_DATA_GATE"


# --------------------------------------------------------------------------- #
# 26-28. Pointers, QC, generated state
# --------------------------------------------------------------------------- #

def test_next_pointer_is_the_m3_gate_and_is_not_authorization(decision):
    assert decision["last_completed_research_action_id"] == d.ACTION_ID
    assert decision["next_research_action_id"] == "stage128-m3-macro-data-gate"
    assert decision["next_research_action_pointer_is_not_authorization"] is True
    assert decision["authorizes_next_action"] is False
    assert decision["merge_authorized"] is False


def test_qc_report_passes_and_covers_the_required_checks(qc):
    assert qc["all_pass"] is True
    assert qc["failed_count"] == 0
    assert qc["failed_assertions"] == []
    assert qc["assertion_count"] >= 28
    names = {a["name"] for a in qc["assertions"]}
    for required in (
        "authorization_byte_length_is_240",
        "authorization_sha256_matches",
        "verbatim_and_normalized_authorization_are_separate_fields",
        "baseline_commit_is_the_canonical_main_sha",
        "decision_outcome_is_retain_m2_as_intermediate_block",
        "m2_block_retained_is_true",
        "m2_superiority_claim_is_false",
        "no_paper_winner_selected",
        "no_final_model_selected",
        "zero_model_fits_and_predictions",
        "zero_resampling_and_new_uncertainty_execution",
        "zero_full_development_refits",
        "final_test_remains_locked",
        "final_test_predictor_and_target_values_uninspected",
        "m3_remains_unauthorized_and_unstarted",
        "m4_remains_unauthorized_and_unstarted",
        "exact_m1_and_m2_feature_lists",
        "frozen_d2_equity_return_semantics_preserved",
        "exact_common_sample_counts",
        "exact_attrition_counts",
        "exact_pooled_oof_counts",
        "exact_pr_auc_deltas_and_intervals",
        "all_primary_intervals_include_zero",
        "model_family_point_estimate_signs_disagree",
        "eligibility_audit_counts_53_and_35",
        "holm_family_remains_incomplete_and_deferred",
        "pinned_scientific_artifacts_are_byte_identical",
        "next_pointer_is_m3_gate_and_is_not_authorization",
    ):
        assert required in names, required
    assert all(a["status"] == "PASS" for a in qc["assertions"])


def test_metadata_hashes_match_the_on_disk_package(metadata):
    for rel, sha in metadata["package_artifacts_sha256"].items():
        assert hashlib.sha256(
            (REPO_ROOT / rel).read_bytes()).hexdigest() == sha, rel
    assert metadata["source_main_commit"] == d.BASELINE_COMMIT


def test_on_disk_package_matches_a_fresh_in_memory_build():
    built = d.build_package(REPO_ROOT, write=False)
    assert (REPO_ROOT / d.README_REL).read_text(encoding="utf-8") == (
        built["readme_text"])
    for rel, payload in (
        (d.AUTHORIZATION_REL, built["authorization_record"]),
        (d.DECISION_REL, built["decision"]),
        (d.METADATA_REL, built["metadata"]),
        (d.QC_REL, built["qc_report"]),
    ):
        expected = json.dumps(
            payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        assert (REPO_ROOT / rel).read_text(encoding="utf-8") == expected, rel


def test_roadmap_and_handoff_agree_on_the_decided_state():
    roadmap = (REPO_ROOT / "project/docs/ai/ROADMAP.md").read_text(
        encoding="utf-8")
    front = roadmap.split("---", 2)[1]
    assert "last_completed_research_action_id: stage128-m2-retained-block-" \
           "human-decision" in front
    assert "next_research_action_id: stage128-m3-macro-data-gate" in front

    state = _load("project/docs/ai/handoff_state.json")
    assert state["last_completed_research_action_id"] == d.ACTION_ID
    assert state["next_research_action_id"] == "stage128-m3-macro-data-gate"
    assert state["next_research_action_pointer_is_not_authorization"] is True
    assert state["m2_block_retained"] is True
    assert state["m2_retained_block_decision_required"] is False
    assert state["m2_evaluation_completed"] is True
    assert state["m2_superiority_established"] is False
    assert state["m2_winner_selected"] is False
    assert state["paper_winner_selected"] is False
    assert state["final_model_selected"] is False
    # ACTION-SCOPED: this decision authorized no refit, and its own artifact
    # records that permanently. The live global is set by the separately
    # authorized Stage129 contracted refit and is not a proxy for it.
    assert _load("project/stage128/m2_retained_block_human_decision/"
                 "stage128_m2_retained_block_human_decision.json"
                 )["full_development_refit_performed"] is False
    assert state["final_test_unlocked"] is False
    assert state["final_test_access_authorized"] is False
    assert state["m3_authorized"] is False
    assert state["m3_started"] is False
    assert state["m4_authorized"] is False
    assert state["m4_started"] is False
    assert state["holm_family_complete"] is False
    assert state["holm_final_adjustment_deferred"] is True


def test_current_state_renders_the_decision_without_a_superiority_claim():
    text = (REPO_ROOT / "project/docs/ai/CURRENT_STATE.md").read_text(
        encoding="utf-8")
    assert "## Stage128 — M2 retained-block HUMAN decision (CURRENT)" in text
    assert "RETAIN_M2_AS_INTERMEDIATE_CONFIRMATORY_BLOCK" in text
    assert text.count("(CURRENT)") == 1
    heading = "## Stage128 — M2 retained-block HUMAN decision (CURRENT)"
    section = text.split(heading, 1)[1].split("\n## ", 1)[0].lower()
    # The section must state retention WITHOUT asserting superiority. (The
    # historical Gate section elsewhere legitimately contains the NEGATED
    # phrase "does not say M2 improves prediction", so this check is scoped.)
    assert "improves prediction" not in section
    assert "best block" not in section
    assert "m2 predictive superiority claim supported:** false" in section
    assert "approximately null" in section


def test_package_contains_exactly_the_five_required_artifacts():
    assert sorted(p.name for p in PKG.iterdir()) == sorted([
        "README_STAGE128_M2_RETAINED_BLOCK_HUMAN_DECISION.md",
        "metadata_and_hashes_stage128_m2_retained_block_human_decision.json",
        "stage128_m2_retained_block_human_authorization_record.json",
        "stage128_m2_retained_block_human_decision.json",
        "stage128_m2_retained_block_human_decision_qc_report.json",
    ])


def test_builder_fails_closed_on_a_tampered_authorization(monkeypatch):
    monkeypatch.setattr(d, "HUMAN_SOURCE_UTTERANCE",
                        d.HUMAN_SOURCE_UTTERANCE + " ")
    with pytest.raises(d.RetainedBlockDecisionError):
        d.verify_human_authorization()


def test_builder_fails_closed_on_a_tampered_expected_count(monkeypatch):
    monkeypatch.setitem(d.EXPECTED_POOLED_OOF, "positive", 29)
    with pytest.raises(d.RetainedBlockDecisionError):
        d.read_source_evidence(REPO_ROOT)


def test_repository_reports_no_uncommitted_scientific_drift():
    assert os.path.isdir(PKG)
    assert (REPO_ROOT / d.QC_REL).is_file()
