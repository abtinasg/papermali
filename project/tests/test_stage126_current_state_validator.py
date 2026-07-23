"""Fail-closed tests for the Stage126 validation-architecture boundary.

Proves that Stage125 Part 5 is frozen historical/immutable and no longer a live
gate, that the independent Stage126 validator neither imports nor executes it,
that closed micro-part packages are immutable, and that a future part can
advance current state without touching any earlier part's files.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest

from src import stage126_current_state_validator as v

REAL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STAGE126 = os.path.join(REAL_ROOT, "project", "stage126")


def _root() -> Path:
    return Path(REAL_ROOT)


def _read_json(name: str) -> dict:
    return json.loads(open(os.path.join(STAGE126, name), encoding="utf-8").read())


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# Human governance decision
# --------------------------------------------------------------------------- #

def test_decision_text_hash_recomputes_exactly():
    got = hashlib.sha256(v.HUMAN_DECISION_TEXT_FA.encode("utf-8")).hexdigest()
    assert got == v.HUMAN_DECISION_TEXT_SHA256
    assert got == (
        "8231bbf8704d3128cce6a7f2cc40a33af8e7fe7730b2c4575997330cafb21ac1"
    )


def test_decision_text_mentions_the_boundary():
    text = v.HUMAN_DECISION_TEXT_FA
    assert "Stage125 Part5" in text
    assert "historical" in text and "immutable" in text
    assert "validator" in text
    assert "verification-only" in text


def test_wrong_decision_text_fails_closed(monkeypatch):
    monkeypatch.setattr(v, "HUMAN_DECISION_TEXT_FA", "تصمیم جعلی")
    with pytest.raises(v.ValidationFail):
        v.verify_decision_text()


def test_decision_record_authorizes_only_the_boundary():
    rec = _read_json(v.F_DECISION)
    assert rec["decision_id"] == "stage126-validation-architecture-boundary-lock"
    assert rec["decision_version"] == "stage126_validation_architecture_boundary_v1"
    assert rec["decision_locked"] is True
    assert rec["authorizes"] == {
        "documentation_and_test_changes_required_for_this_boundary": True,
        "historical_stage125_part5_freeze": True,
        "stage126_current_state_validator_creation": True,
        "stage126_validation_architecture_boundary_lock": True,
    }
    for key in ("merge", "part3_execution", "full_development_refit",
                "final_test_access", "final_test_evaluation",
                "new_scientific_execution"):
        assert rec["does_not_authorize"][key] is False, key


# --------------------------------------------------------------------------- #
# Stage125 Part 5 is frozen historical/immutable
# --------------------------------------------------------------------------- #

def test_part5_source_runner_and_test_hashes_pinned():
    manifest = _read_json(v.F_BOUNDARY_MANIFEST)
    pinned = manifest["stage125_part5_frozen_files_sha256"]
    assert pinned[v.PART5_SOURCE_REL] == v.PART5_SOURCE_SHA256
    assert pinned[v.PART5_RUNNER_REL] == v.PART5_RUNNER_SHA256
    assert pinned[v.PART5_TEST_REL] == v.PART5_TEST_SHA256
    assert v.PART5_TEST_SHA256 == (
        "0b9413b2adbf9c44b0fb12b4f7ef2dad60be5cd4c401ccefac30d19f0905af71"
    )
    # And they match the files on disk right now.
    for rel, want in pinned.items():
        assert _sha(_root() / rel) == want, rel


def test_all_stage125_artifacts_are_pinned():
    manifest = _read_json(v.F_BOUNDARY_MANIFEST)
    tree = manifest["stage125_tracked_files_sha256"]
    assert manifest["stage125_tracked_file_count"] == len(tree)
    assert len(tree) >= 140
    tracked = v.tracked_stage125_files(_root())
    assert sorted(tree) == sorted(tracked)
    for rel, want in tree.items():
        assert _sha(_root() / rel) == want, rel
    assert manifest["stage125_tree_aggregate_sha256"] == v.stage125_tree_digest(tree)


def test_part5_drift_fails_closed(tmp_path):
    """A changed Part 5 file must fail the boundary manifest, not be absorbed."""
    shutil.copytree(
        os.path.join(REAL_ROOT, "project", "src"),
        tmp_path / "project" / "src",
    )
    tampered = tmp_path / "project" / "src" / "stage125_part5_readiness_closure.py"
    tampered.write_text(
        tampered.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8"
    )
    with pytest.raises(v.ValidationFail):
        v.require_file_hash(
            tmp_path, v.PART5_SOURCE_REL, v.PART5_SOURCE_SHA256,
            label="frozen Part 5 source",
        )


def test_part5_mode_and_prohibitions():
    manifest = _read_json(v.F_BOUNDARY_MANIFEST)
    report = _read_json(v.F_REPORT)
    assert manifest["stage125_part5_mode"] == "historical_immutable"
    assert report["stage125_part5_mode"] == "historical_immutable"
    assert report["stage125_part5_live_gate_active"] is False
    prohibitions = manifest["boundary_prohibitions"]
    for key in (
        "future_stage126_gate_may_execute_stage125_part5_runner",
        "future_stage126_gate_may_import_stage125_part5_validator",
        "future_stage126_gate_may_call_validate_actual_handoff_from_part5",
        "future_robustness_part_may_modify_part5_test",
        "future_robustness_part_may_regenerate_stage125_part5_outputs",
    ):
        assert prohibitions[key] is False, key


def test_part5_historical_behavior_is_provenance_only():
    prov = v.PART5_HISTORICAL_PROVENANCE
    assert prov["full_runner_exit_code"] == 1
    assert prov["first_failure_code"] == "readiness_surface_disagreement"
    assert prov["direct_validate_actual_handoff_mismatch_fields"] == [
        "m1_robustness_started", "selected_qc_scope", "selected_qc_path",
        "contract_version", "last_completed_micro_part",
    ]
    assert prov["is_required_live_stage126_gate"] is False
    assert prov["executed_by_this_validator"] is False


# --------------------------------------------------------------------------- #
# The validator is genuinely independent of Part 5
# --------------------------------------------------------------------------- #

def _validator_sources() -> list[tuple[str, str]]:
    return [
        (rel, open(os.path.join(REAL_ROOT, rel), encoding="utf-8").read())
        for rel in (v.SRC_REL, v.RUN_REL)
    ]


def test_validator_does_not_import_part5_source():
    for rel, text in _validator_sources():
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "stage125_part5" not in alias.name, (rel, alias.name)
            elif isinstance(node, ast.ImportFrom):
                assert "stage125_part5" not in (node.module or ""), rel
                for alias in node.names:
                    assert "stage125_part5" not in alias.name, (rel, alias.name)


def test_validator_does_not_call_part5_validate_actual_handoff():
    for rel, text in _validator_sources():
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.Call):
                func = node.func
                name = (
                    func.attr if isinstance(func, ast.Attribute)
                    else func.id if isinstance(func, ast.Name) else ""
                )
                assert name != "validate_actual_handoff", rel


def test_validator_does_not_execute_the_part5_runner():
    for rel, text in _validator_sources():
        for node in ast.walk(ast.parse(text)):
            if isinstance(node, ast.Call):
                func = node.func
                name = (
                    func.attr if isinstance(func, ast.Attribute)
                    else func.id if isinstance(func, ast.Name) else ""
                )
                if name in ("run", "Popen", "check_output", "call"):
                    for arg in ast.walk(node):
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            assert "run_stage125_part5" not in arg.value, rel


def test_validator_self_coupling_check_is_clean_and_can_detect_coupling():
    src = open(os.path.join(REAL_ROOT, v.SRC_REL), encoding="utf-8").read()
    assert v.part5_coupling_findings(src) == []
    # The detector is not vacuous: real coupling is caught.
    assert v.part5_coupling_findings(
        "from src import stage125_part5_readiness_closure as p5\n"
    ) == ["import_from_name:stage125_part5_readiness_closure"]
    assert v.part5_coupling_findings("x = validate_actual_handoff(1)\n") == [
        "call:validate_actual_handoff"
    ]
    assert v.part5_coupling_findings(
        "import subprocess\nsubprocess.run(['python','run_stage125_part5.py'])\n"
    ) == ["subprocess_runner:run_stage125_part5.py"]
    # A mere mention in a docstring or message is NOT coupling.
    assert v.part5_coupling_findings('MSG = "see run_stage125_part5.py"\n') == []


def test_report_and_metadata_declare_no_part5_use():
    report = _read_json(v.F_REPORT)
    meta = _read_json(v.F_METADATA)
    assert report["stage125_part5_executed_by_this_validator"] is False
    assert report["stage125_part5_imported_by_this_validator"] is False
    assert meta["stage125_part5_executed"] is False
    assert meta["stage125_part5_imported"] is False


# --------------------------------------------------------------------------- #
# Closed micro-part packages are immutable
# --------------------------------------------------------------------------- #

PART1_SCIENTIFIC = {
    "stage126_m1_robustness_part1_human_authorization_record.json":
        "87a4f55baeb1081eaf936e49c5e8923f67df54ec444f0abc33ec835c0c7e06f4",
    "stage126_m1_robustness_part1_feature_manifest.csv":
        "c65735795eda7dce6b4cacbc6af9dd5914b5068f44c77277035a51463cceaf90",
    "stage126_m1_robustness_part1_execution_manifest.json":
        "80813ce8af9544dde736cc6b94372d2626dccbf888553cd7964625bfe12d8738",
    "stage126_m1_robustness_part1_oof_predictions.csv":
        "1303a31a45e8293be84e7d6c3b23aa1a4c771847de0f1b0207110c33cafdba31",
    "stage126_m1_robustness_part1_metrics.csv":
        "c60f4b15aa40273472be98c867c73795d254f32c2a0e29b76641b1c5d5c18e98",
    "stage126_m1_robustness_part1_primary_comparison.json":
        "2b58a85250420a8a18b0ff37cecdf3f2e31160c37e0cb48d027324c87a25c46a",
    "stage126_m1_robustness_part1_completion_lock.json":
        "964d84f2269bb35b0176f88bb12bcfc13ef2cb487817cf5b49a5c28a87e1822b",
}
PART2_SCIENTIFIC = {
    "stage126_m1_robustness_part2_human_authorization_record.json":
        "0a7bba7489f62f59d3e0f07946b82d8ce4be1a49c4d098f47ca308de9466959e",
    "stage126_m1_robustness_part2_feature_manifest.csv":
        "58c52c17337286237779153d59f85f74c76f84d0c0415b8efadd618aa524b78f",
    "stage126_m1_robustness_part2_sample_delta.csv":
        "baafe97323e45f0a88b07aaf1ea97c50c4b213e43724ddb2b97f3f55144fc7d3",
    "stage126_m1_robustness_part2_execution_manifest.json":
        "9fc153b65a77c906339f51d7c0ad576d23eb06c5895eacb1a0ee92578b321ce8",
    "stage126_m1_robustness_part2_oof_predictions.csv":
        "3af630141a905370849875926fa84052cf10322cc34e18258a25d28106d47dd6",
    "stage126_m1_robustness_part2_metrics.csv":
        "073b8657c0ba2c40f52e05d766a102e2b5d20845821c4eb1cef1b6e53459228c",
    "stage126_m1_robustness_part2_primary_comparison.json":
        "9fc3b4eaf0a27fc66cd22444d92363747157743e822d3be877ecca7f153763bf",
    "stage126_m1_robustness_part2_completion_lock.json":
        "23d1920c4fb0a351456fe54b60616446381bbd550fb18e0bba5dab091486fec6",
}


@pytest.mark.parametrize("pinned,label", [
    (PART1_SCIENTIFIC, "part1"), (PART2_SCIENTIFIC, "part2"),
])
def test_part_scientific_artifacts_are_immutable(pinned, label):
    for name, want in pinned.items():
        assert _sha(Path(STAGE126) / name) == want, f"{label}:{name}"


def test_boundary_manifest_pins_both_closed_packages():
    manifest = _read_json(v.F_BOUNDARY_MANIFEST)
    closed = manifest["closed_micro_part_scientific_artifacts_sha256"]
    assert set(closed) == {
        "m1_target_proximity_six_feature_set", "main_rule_b_listing_robustness",
    }
    assert closed["m1_target_proximity_six_feature_set"] == PART1_SCIENTIFIC
    assert closed["main_rule_b_listing_robustness"] == PART2_SCIENTIFIC


def test_scientific_artifact_drift_fails_closed(monkeypatch):
    bad = {k: dict(v_) for k, v_ in v.PINNED_PART_SCIENTIFIC_ARTIFACTS.items()}
    bad["main_rule_b_listing_robustness"][
        "stage126_m1_robustness_part2_metrics.csv"
    ] = "0" * 64
    monkeypatch.setattr(v, "PINNED_PART_SCIENTIFIC_ARTIFACTS", bad)
    with pytest.raises(v.ValidationFail):
        v.build_boundary_manifest(_root())


def test_prior_part_verification_artifacts_are_not_regenerated():
    """The boundary must pin scientific artifacts WITHOUT pinning bookkeeping.

    Verification-only artifacts (QC report, metadata manifest, Part 5
    compatibility record, README) are deliberately outside the immutable set,
    and the policy forbids regenerating them from a later part.
    """
    manifest = _read_json(v.F_BOUNDARY_MANIFEST)
    closed = manifest["closed_micro_part_scientific_artifacts_sha256"]
    for category, files in closed.items():
        for name in files:
            assert "qc_report" not in name, (category, name)
            assert not name.startswith("metadata_and_hashes"), (category, name)
            assert "part5_successor_compatibility" not in name, (category, name)
            assert not name.startswith("README"), (category, name)
    assert manifest[
        "regeneration_of_earlier_part_verification_artifacts_allowed"
    ] is False
    report = _read_json(v.F_REPORT)
    assert report["prior_part_verification_artifact_regeneration_allowed"] is False


def test_no_closed_part_artifact_embeds_a_mutable_current_test_hash():
    """Any test hash a closed package embeds must be a FROZEN, pinned file."""
    frozen = {
        v.PART5_SOURCE_SHA256, v.PART5_RUNNER_SHA256, v.PART5_TEST_SHA256,
        "0a117c1916ad845653e148d951a49a2c0375d13b7de23019e50ae891aee1b437",
        "62cd1593e7bfafdeb1aa1c728f3fb9c22aadf50d3031e2cec964d267e752b189",
    }
    for part in (1, 2):
        compat = _read_json(
            f"stage126_m1_robustness_part{part}_part5_successor_compatibility.json"
        )
        embedded = [
            value for key, value in compat.items()
            if key.endswith("test_file_sha256") and isinstance(value, str) and value
        ]
        assert embedded, part
        for value in embedded:
            assert value in frozen, (part, value)


# --------------------------------------------------------------------------- #
# Current state
# --------------------------------------------------------------------------- #

def test_completed_categories_and_next_category():
    report = _read_json(v.F_REPORT)
    assert report["completed_category_ids"] == [
        "m1_target_proximity_six_feature_set", "main_rule_b_listing_robustness",
    ]
    assert report["next_category_id"] == "expanded_rule_a_company_scope_robustness"
    assert report["next_category_authorized"] is False
    assert report["standing_execution_authorization"] is False
    assert report["m1_robustness_completed"] is False
    assert report["last_completed_micro_part"] == (
        "stage126-m1-robustness-part2-listing-rule-b"
    )


def test_part3_is_unauthorized_and_absent():
    report = _read_json(v.F_REPORT)
    assert report["next_category_authorized"] is False
    for suffix in ("_completion_lock.json", "_human_authorization_record.json",
                   "_oof_predictions.csv", "_metrics.csv"):
        assert not os.path.isfile(
            os.path.join(STAGE126, f"stage126_m1_robustness_part3{suffix}")
        ), suffix
    state = json.loads(
        (_root() / v.HANDOFF_STATE_REL).read_text(encoding="utf-8")
    )
    assert state["m1_robustness_part3_authorized"] is False
    assert state["m1_robustness_execution_authorized"] is False


def test_final_test_remains_locked():
    report = _read_json(v.F_REPORT)
    state = json.loads(
        (_root() / v.HANDOFF_STATE_REL).read_text(encoding="utf-8")
    )
    for field in v.FINAL_TEST_LOCK_FIELDS:
        assert report[field] is False, field
        assert state[field] is False, field
    assert report["full_development_refit_performed"] is False


def test_research_pointers_unchanged():
    report = _read_json(v.F_REPORT)
    assert report["active_workstream"] == "stage126_m1_financial_baseline"
    assert report["next_research_action_id"] == "stage126-m1-financial-baseline"


def test_handoff_carries_boundary_markers():
    state = json.loads(
        (_root() / v.HANDOFF_STATE_REL).read_text(encoding="utf-8")
    )
    assert state["validation_architecture"] == "stage126_current_state_validator_v1"
    assert state["stage125_part5_mode"] == "historical_immutable"
    assert state["stage125_part5_live_gate_active"] is False
    assert state["stage125_part5_future_regeneration_allowed"] is False
    assert state[
        "prior_robustness_verification_artifact_regeneration_allowed"
    ] is False
    assert state["prior_part_reopening_requires_scientific_error"] is True
    assert state[
        "prior_part_reopening_requires_explicit_human_authorization"
    ] is True


# --------------------------------------------------------------------------- #
# Change-resilience: incidental changes must not reopen a closed part
# --------------------------------------------------------------------------- #

def _mirror(tmp_path: Path) -> Path:
    """Copy the Stage126/Stage125/docs surfaces the validator reads."""
    root = tmp_path / "repo"
    for rel in ("project/stage126", "project/stage125", "project/docs/ai",
                "project/src", "project/tests"):
        src = Path(REAL_ROOT) / rel
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst)
    # Top-level runners the boundary pins by hash.
    for rel in (v.PART5_RUNNER_REL, v.RUN_REL):
        src = Path(REAL_ROOT) / rel
        if src.is_file():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, root / rel)
    return root


def test_handoff_timestamp_change_does_not_reopen_a_closed_part(tmp_path):
    root = _mirror(tmp_path)
    state_path = root / v.HANDOFF_STATE_REL
    state = json.loads(state_path.read_text(encoding="utf-8"))
    before = {
        name: _sha(root / "project/stage126" / name) for name in PART2_SCIENTIFIC
    }
    state["generated_at_utc"] = "2099-01-01T00:00:00Z"
    state["state_fingerprint"] = "f" * 64
    state["observed_repository_head_commit"] = "a" * 40
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    # Current state still validates and nothing in the closed package moved.
    completed, ids = v.completed_prefix(
        root, list(v.EXPECTED_COMPLETED_CATEGORY_IDS)
        + ["expanded_rule_a_company_scope_robustness"],
    )
    assert ids == list(v.EXPECTED_COMPLETED_CATEGORY_IDS)
    after = {
        name: _sha(root / "project/stage126" / name) for name in PART2_SCIENTIFIC
    }
    assert before == after
    assert "new Handoff timestamp" in v.NOT_A_SCIENTIFIC_ERROR
    assert "new branch SHA" in v.NOT_A_SCIENTIFIC_ERROR


def test_new_current_test_hash_does_not_regenerate_a_closed_part(tmp_path):
    root = _mirror(tmp_path)
    before = {
        name: _sha(root / "project/stage126" / name)
        for name in list(PART1_SCIENTIFIC) + list(PART2_SCIENTIFIC)
    }
    target = root / "project/tests/test_stage126_current_state_validator.py"
    target.write_text(
        target.read_text(encoding="utf-8") + "\n# a new current test\n",
        encoding="utf-8",
    )
    after = {
        name: _sha(root / "project/stage126" / name)
        for name in list(PART1_SCIENTIFIC) + list(PART2_SCIENTIFIC)
    }
    assert before == after
    assert "new current test hash" in v.NOT_A_SCIENTIFIC_ERROR


# --------------------------------------------------------------------------- #
# Generic future-part advancement
# --------------------------------------------------------------------------- #

def _synthetic_part3(root: Path) -> None:
    """Write a minimal, VALID Part 3 package into a mirrored repository."""
    d = root / "project/stage126"
    prefix = "stage126_m1_robustness_part3"
    (d / f"{prefix}_human_authorization_record.json").write_text(json.dumps({
        "authorization_id": "stage126-m1-robustness-part3-human-authorization",
        "authorized_category_id": "expanded_rule_a_company_scope_robustness",
        "human_authorization_text": "synthetic",
        "human_authorization_text_sha256": "3" * 64,
        "part3_execution_authorized": True,
    }), encoding="utf-8")
    (d / f"{prefix}_completion_lock.json").write_text(json.dumps({
        "category_id": "expanded_rule_a_company_scope_robustness",
        "part3_human_authorized": True,
        "part3_execution_completed": True,
        "authorization_consumed": True,
        "development_only": True,
        "part4_execution_authorized": False,
        "full_development_refit_performed": False,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_evaluation_performed": False,
        "smote_executed": False,
        "smotenc_executed": False,
        "shap_executed": False,
        "replaces_primary_results": False,
        "selects_paper_winner": False,
        "completed_category_ids": [
            "m1_target_proximity_six_feature_set",
            "main_rule_b_listing_robustness",
            "expanded_rule_a_company_scope_robustness",
        ],
        "next_category_id": "expanded_rule_b_combined_robustness",
    }), encoding="utf-8")


def test_hypothetical_next_completion_advances_without_touching_earlier_parts(tmp_path):
    """A valid Part 3 must be recognized with ZERO changes to earlier files.

    This is the generic-design guarantee: no new validator branch, and no
    Part 1, Part 2 or Stage125 file may be modified.
    """
    root = _mirror(tmp_path)
    watched = (
        [f"project/stage126/{n}" for n in
         list(PART1_SCIENTIFIC) + list(PART2_SCIENTIFIC)]
        + [
            "project/stage126/stage126_m1_robustness_part1_qc_report.json",
            "project/stage126/metadata_and_hashes_stage126_m1_robustness_part1.json",
            "project/stage126/stage126_m1_robustness_part1_part5_successor_compatibility.json",
            "project/stage126/stage126_m1_robustness_part2_qc_report.json",
            "project/stage126/metadata_and_hashes_stage126_m1_robustness_part2.json",
            "project/stage126/stage126_m1_robustness_part2_part5_successor_compatibility.json",
            v.PART5_SOURCE_REL, v.PART5_RUNNER_REL, v.PART5_TEST_REL,
        ]
    )
    before = {rel: _sha(root / rel) for rel in watched}

    order = json.loads(
        (root / v.PART0_DECISION_RECORD_REL).read_text(encoding="utf-8")
    )["execution_order"]
    completed_before, ids_before = v.completed_prefix(root, order)
    assert ids_before == list(v.EXPECTED_COMPLETED_CATEGORY_IDS)

    _synthetic_part3(root)

    completed_after, ids_after = v.completed_prefix(root, order)
    assert ids_after == [
        "m1_target_proximity_six_feature_set",
        "main_rule_b_listing_robustness",
        "expanded_rule_a_company_scope_robustness",
    ]
    assert len(completed_after) == len(completed_before) + 1
    assert v.verify_no_unauthorized_execution(root, order, completed_after) == (
        "expanded_rule_b_combined_robustness"
    )
    # Not one earlier-part or Stage125 file changed.
    after = {rel: _sha(root / rel) for rel in watched}
    assert before == after


def test_skipped_category_fails_closed(tmp_path):
    """A Part 4 package without Part 3 must fail — categories cannot be skipped."""
    root = _mirror(tmp_path)
    d = root / "project/stage126"
    (d / "stage126_m1_robustness_part4_human_authorization_record.json").write_text(
        json.dumps({"authorized_category_id": "expanded_rule_b_combined_robustness"}),
        encoding="utf-8",
    )
    (d / "stage126_m1_robustness_part4_completion_lock.json").write_text(
        json.dumps({"category_id": "expanded_rule_b_combined_robustness"}),
        encoding="utf-8",
    )
    order = json.loads(
        (root / v.PART0_DECISION_RECORD_REL).read_text(encoding="utf-8")
    )["execution_order"]
    with pytest.raises(v.ValidationFail):
        v.completed_prefix(root, order)


def test_half_present_part_package_fails_closed(tmp_path):
    root = _mirror(tmp_path)
    (root / "project/stage126"
     / "stage126_m1_robustness_part3_completion_lock.json").write_text(
        json.dumps({"category_id": "expanded_rule_a_company_scope_robustness"}),
        encoding="utf-8",
    )
    with pytest.raises(v.ValidationFail):
        v.discover_part(root, 3, "expanded_rule_a_company_scope_robustness")


def test_unauthorized_future_artifact_fails_closed(tmp_path):
    root = _mirror(tmp_path)
    (root / "project/stage126"
     / "stage126_m1_robustness_part3_oof_predictions.csv").write_text(
        "a,b\n1,2\n", encoding="utf-8",
    )
    order = json.loads(
        (root / v.PART0_DECISION_RECORD_REL).read_text(encoding="utf-8")
    )["execution_order"]
    completed, _ids = v.completed_prefix(root, order)
    with pytest.raises(v.ValidationFail):
        v.verify_no_unauthorized_execution(root, order, completed)


# --------------------------------------------------------------------------- #
# Repository-level policy: no future part may own an earlier part's artifacts
# --------------------------------------------------------------------------- #

EARLIER_PART_VERIFICATION_ARTIFACTS = (
    "stage126_m1_robustness_part1_qc_report.json",
    "metadata_and_hashes_stage126_m1_robustness_part1.json",
    "stage126_m1_robustness_part1_part5_successor_compatibility.json",
    "README_STAGE126_M1_ROBUSTNESS_PART1_TARGET_PROXIMITY.md",
    "stage126_m1_robustness_part2_qc_report.json",
    "metadata_and_hashes_stage126_m1_robustness_part2.json",
    "stage126_m1_robustness_part2_part5_successor_compatibility.json",
    "README_STAGE126_M1_ROBUSTNESS_PART2_LISTING_RULE_B.md",
)


def test_no_future_robustness_module_declares_an_earlier_parts_artifacts():
    """Policy test: a later part must not emit an earlier part's artifacts.

    Scans every robustness implementation for string constants naming another
    part's verification or scientific artifacts. A module may reference its OWN
    part's files; declaring a *different* part's outputs would mean completing
    it regenerates that closed package.
    """
    src_dir = Path(REAL_ROOT) / "project" / "src"
    modules = sorted(src_dir.glob("stage126_m1_robustness_part*.py"))
    assert modules, "no robustness modules found"
    offences: list[str] = []
    for module in modules:
        own = ""
        for token in ("part1", "part2", "part3", "part4", "part5", "part6"):
            if f"_{token}_" in module.name or module.name.endswith(f"{token}.py"):
                own = token
                break
        if not own:
            for token in ("part0", "part1", "part2"):
                if token in module.name:
                    own = token
                    break
        text = module.read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(text)):
            if not (isinstance(node, ast.Constant)
                    and isinstance(node.value, str)):
                continue
            value = node.value
            for artifact in EARLIER_PART_VERIFICATION_ARTIFACTS:
                if artifact not in value:
                    continue
                if own and own in artifact.lower():
                    continue  # its own package
                offences.append(f"{module.name} declares {artifact}")
    assert offences == [], offences


def test_required_live_sequence_excludes_the_part5_runner():
    """The documented live gate sequence must not include the Part 5 runner."""
    readme = open(os.path.join(STAGE126, v.F_README), encoding="utf-8").read()
    sequence = readme.split("```bash", 1)[1].split("```", 1)[0]
    assert "run_stage126_current_state_validator.py --check" in sequence
    assert "run_stage126_m1_robustness_part2_listing_rule_b.py --check" in sequence
    assert "validate_ai_handoff.py --check" in sequence
    assert "run_stage125_part5.py" not in sequence
    # Earlier robustness runners are not current-state gates either.
    assert "run_stage126_m1_robustness_part1" not in sequence


# --------------------------------------------------------------------------- #
# Determinism + metadata
# --------------------------------------------------------------------------- #

def test_validator_all_pass_and_assertion_count():
    meta = _read_json(v.F_METADATA)
    assert meta["all_pass"] is True
    assert meta["failed_count"] == 0
    assert meta["assertion_count"] >= 35
    assert all(a["status"] == "PASS" for a in meta["assertions"])
    assert meta["validator_version"] == "stage126_current_state_validator_v1"
    assert meta["human_decision_text_sha256"] == v.HUMAN_DECISION_TEXT_SHA256


def test_outputs_are_deterministic_and_sorted():
    for name in (v.F_DECISION, v.F_BOUNDARY_MANIFEST, v.F_REPORT, v.F_METADATA):
        text = open(os.path.join(STAGE126, name), encoding="utf-8").read()
        assert text.endswith("\n"), name
        obj = json.loads(text)
        assert text == json.dumps(
            obj, indent=2, ensure_ascii=False, sort_keys=True
        ) + "\n", name
        assert "np.float64(" not in text


def test_check_mode_is_clean():
    result = v.run(project_dir=Path(REAL_ROOT) / "project", check=True)
    assert result["drift"] == []
    assert result["metadata"]["all_pass"] is True


def test_deterministic_repeated_build(tmp_path):
    a = v.run(project_dir=Path(REAL_ROOT) / "project",
              output_dir=tmp_path / "a", build=True)
    b = v.run(project_dir=Path(REAL_ROOT) / "project",
              output_dir=tmp_path / "b", build=True)
    assert a["files"] == b["files"]
