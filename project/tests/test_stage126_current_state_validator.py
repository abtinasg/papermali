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


# --------------------------------------------------------------------------- #
# Historical decision record stays decoupled from the LIVE validator version
# --------------------------------------------------------------------------- #

def test_historical_decision_records_its_own_original_validator_version():
    """The 2026-07-23 locked decision must record v1 — the version that
    existed when it was authorized — never the current implementation."""
    assert v.HISTORICAL_DECISION_VALIDATOR_VERSION == (
        "stage126_current_state_validator_v1"
    )
    decision = v.build_decision_record()
    assert decision["architecture"]["stage126_current_state_validator_version"] \
        == "stage126_current_state_validator_v1"


def test_future_validator_version_bump_does_not_mutate_the_historical_decision(
    monkeypatch,
):
    """A future VALIDATOR_VERSION bump must not change one byte of the
    historical decision record — proving the two are decoupled."""
    before = v.build_decision_record()
    monkeypatch.setattr(v, "VALIDATOR_VERSION", "stage126_current_state_validator_v99_future")
    after = v.build_decision_record()
    assert before == after
    assert after["architecture"]["stage126_current_state_validator_version"] == (
        "stage126_current_state_validator_v1"
    )


def test_committed_historical_decision_file_matches_origin_main_exactly():
    """The on-disk decision file must remain byte-identical to origin/main —
    it is historical, locked provenance, not a live artifact that tracks the
    current validator implementation."""
    on_disk = json.loads(
        (_root() / v.STAGE126_DIR_REL / v.F_DECISION).read_text(encoding="utf-8")
    )
    assert on_disk["architecture"]["stage126_current_state_validator_version"] \
        == "stage126_current_state_validator_v1"


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


def test_closed_part_registry_pins_both_packages():
    registry = _read_json(v.F_CLOSED_REGISTRY)
    assert registry["closed_part_count"] == 6
    assert registry["regeneration_allowed"] is False
    parts = registry["parts"]
    assert set(parts) == {
        "m1_target_proximity_six_feature_set", "main_rule_b_listing_robustness",
        "expanded_rule_a_company_scope_robustness",
        "expanded_rule_b_combined_robustness",
        "persistent_loss_robustness_target",
        "smote_training_fold_only_robustness",
    }
    for category, pinned in (
        ("m1_target_proximity_six_feature_set", PART1_SCIENTIFIC),
        ("main_rule_b_listing_robustness", PART2_SCIENTIFIC),
    ):
        recorded = parts[category]["scientific_artifacts_sha256"]
        for name, want in pinned.items():
            rel = f"project/stage126/{name}"
            assert recorded[rel] == want, (category, name)


CLOSED_VERIFICATION_ARTIFACTS = {
    "m1_target_proximity_six_feature_set": [
        "project/stage126/stage126_m1_robustness_part1_qc_report.json",
        "project/stage126/metadata_and_hashes_stage126_m1_robustness_part1.json",
        "project/stage126/stage126_m1_robustness_part1_part5_successor_compatibility.json",
        "project/stage126/README_STAGE126_M1_ROBUSTNESS_PART1_TARGET_PROXIMITY.md",
    ],
    "main_rule_b_listing_robustness": [
        "project/stage126/stage126_m1_robustness_part2_qc_report.json",
        "project/stage126/metadata_and_hashes_stage126_m1_robustness_part2.json",
        "project/stage126/stage126_m1_robustness_part2_part5_successor_compatibility.json",
        "project/stage126/README_STAGE126_M1_ROBUSTNESS_PART2_LISTING_RULE_B.md",
    ],
}


def test_closed_verification_artifacts_are_recorded_as_historical_provenance():
    """Verification-only artifacts are recorded, as historical PROVENANCE.

    Under Stage126+ Q1/Q2 Lean Governance these are operational bookkeeping,
    not a live scientific gate: once a category is first registered, its
    recorded hashes are carried forward from the committed registry rather
    than resynchronized to current file bytes on every build, so a routine
    test/QC/metadata edit never requires "repinning" the registry (see
    build_closed_part_registry). This test therefore checks structure and
    presence, not byte-for-byte equality with the CURRENT live file.
    """
    registry = _read_json(v.F_CLOSED_REGISTRY)
    for category, expected_paths in CLOSED_VERIFICATION_ARTIFACTS.items():
        recorded = registry["parts"][category]["verification_artifacts_sha256"]
        for rel in expected_paths:
            assert rel in recorded, (category, rel)
            assert len(recorded[rel]) == 64, rel
    # Source, runner and tests of the closed packages are recorded as well.
    for category in CLOSED_VERIFICATION_ARTIFACTS:
        code = registry["parts"][category]["code_artifacts_sha256"]
        assert len(code) >= 3, (category, sorted(code))
        assert all(len(h) == 64 for h in code.values())


def test_registry_operational_hashes_are_sticky_across_rebuilds(tmp_path):
    """A routine operational edit must NOT require closed-registry repinning.

    Editing a closed part's test file changes that file's live hash, but the
    registry's `code_artifacts_sha256` entry for the already-closed category
    must stay exactly what was committed — it is carried forward, not
    resynchronized — so the routine edit needs no registry update at all.
    """
    root = _mirror(tmp_path)
    category = "m1_target_proximity_six_feature_set"
    before_registry = json.loads(
        (root / "project/stage126" / v.F_CLOSED_REGISTRY).read_text(
            encoding="utf-8")
    )
    before_code = before_registry["parts"][category]["code_artifacts_sha256"]

    test_rel = (
        "project/tests/test_stage126_m1_robustness_part1_target_proximity.py"
    )
    target = root / test_rel
    target.write_text(target.read_text(encoding="utf-8") + "\n# routine edit\n",
                       encoding="utf-8")

    # The live file hash changed...
    assert _sha(target) != before_code[test_rel]

    # ...but a fresh build reproduces the SAME registry entry unchanged: no
    # repinning was required.
    built = v.run(project_dir=root / "project", build=True)
    assert built["metadata"]["all_pass"] is True
    after_registry = json.loads(
        (root / "project/stage126" / v.F_CLOSED_REGISTRY).read_text(
            encoding="utf-8")
    )
    after_code = after_registry["parts"][category]["code_artifacts_sha256"]
    assert after_code == before_code


def test_qc_metadata_drift_requires_no_handoff_policy_change(tmp_path):
    """Editing a closed part's QC/metadata bookkeeping requires no Handoff
    architecture-field or policy change: the Handoff still validates exactly
    the same lean-governance markers, unmodified."""
    root = _mirror(tmp_path)
    before_handoff = json.loads(
        (root / v.HANDOFF_STATE_REL).read_text(encoding="utf-8")
    )

    qc_rel = "project/stage126/stage126_m1_robustness_part1_qc_report.json"
    target = root / qc_rel
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["_routine_operational_note"] = "reformatted for readability"
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")

    built = v.run(project_dir=root / "project", build=True)
    assert built["metadata"]["all_pass"] is True

    after_handoff = json.loads(
        (root / v.HANDOFF_STATE_REL).read_text(encoding="utf-8")
    )
    for key in v.REQUIRED_HANDOFF_ARCHITECTURE_FIELDS:
        assert after_handoff.get(key) == before_handoff.get(key), key


@pytest.mark.parametrize("victim", [
    "project/stage126/stage126_m1_robustness_part2_metrics.csv",
], ids=["part2_scientific"])
def test_closed_package_scientific_byte_drift_fails_full_validation(
    tmp_path, victim,
):
    """Mutating ONE byte of a closed SCIENTIFIC artifact must fail full
    current-state validation — this remains a hard scientific gate under
    Stage126+ Q1/Q2 Lean Governance."""
    root = _mirror(tmp_path)
    target = root / victim
    target.write_bytes(target.read_bytes() + b" ")
    with pytest.raises(v.ValidationFail):
        v.build_all(root, strict_pointers=False)


@pytest.mark.parametrize("victim", [
    "project/stage126/stage126_m1_robustness_part1_qc_report.json",
    "project/stage126/metadata_and_hashes_stage126_m1_robustness_part2.json",
    "project/stage126/README_STAGE126_M1_ROBUSTNESS_PART1_TARGET_PROXIMITY.md",
    "project/stage126/stage126_m1_robustness_part2_part5_successor_compatibility.json",
], ids=["part1_qc", "part2_metadata", "part1_readme", "part2_compat"])
def test_closed_package_operational_byte_drift_does_not_fail_full_validation(
    tmp_path, victim,
):
    """Mutating ONE byte of a closed part's QC/metadata/README/compat
    bookkeeping must NOT fail full current-state validation under Stage126+
    Q1/Q2 Lean Governance — these are operational/engineering surfaces, not
    scientific control surfaces (see
    project/docs/ai/STAGE126_Q1Q2_LEAN_GOVERNANCE.md sections 2-3)."""
    root = _mirror(tmp_path)
    target = root / victim
    target.write_bytes(target.read_bytes() + b" ")
    v.build_all(root, strict_pointers=False)  # must not raise


def test_prior_part_scientific_regeneration_forbidden_operational_permitted():
    """Scientific regeneration stays forbidden; operational evolution is
    explicitly permitted under Stage126+ Q1/Q2 Lean Governance."""
    manifest = _read_json(v.F_BOUNDARY_MANIFEST)
    assert manifest["prior_part_scientific_artifact_regeneration_forbidden"] is True
    assert manifest[
        "prior_part_operational_verification_artifact_evolution_permitted"
    ] is True
    report = _read_json(v.F_REPORT)
    assert report["prior_part_scientific_artifact_regeneration_forbidden"] is True
    assert report[
        "prior_part_operational_verification_artifact_evolution_permitted"
    ] is True
    registry = _read_json(v.F_CLOSED_REGISTRY)
    assert registry["regeneration_allowed"] is False


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

def test_no_hard_coded_current_state_constants():
    """The three current-state constants must no longer exist."""
    for name in ("EXPECTED_COMPLETED_CATEGORY_IDS", "EXPECTED_NEXT_CATEGORY_ID",
                 "EXPECTED_LAST_MICRO_PART"):
        assert not hasattr(v, name), name
    src = open(os.path.join(REAL_ROOT, v.SRC_REL), encoding="utf-8").read()
    for name in ("EXPECTED_COMPLETED_CATEGORY_IDS", "EXPECTED_NEXT_CATEGORY_ID",
                 "EXPECTED_LAST_MICRO_PART"):
        assert name not in src, name


def test_current_state_is_derived_from_the_registered_order():
    report = _read_json(v.F_REPORT)
    order = report["registered_execution_order"]
    n = report["completed_part_count"]
    assert report["completed_category_ids"] == order[:n]
    assert report["expected_completed_prefix"] == order[:n]
    assert report["next_category_id"] == (order[n] if n < len(order) else "")


def test_completed_categories_and_next_category():
    report = _read_json(v.F_REPORT)
    assert report["completed_category_ids"] == [
        "m1_target_proximity_six_feature_set", "main_rule_b_listing_robustness",
        "expanded_rule_a_company_scope_robustness",
        "expanded_rule_b_combined_robustness",
        "persistent_loss_robustness_target",
        "smote_training_fold_only_robustness",
    ]
    assert report["next_category_id"] == ""
    assert report["next_category_authorized"] is False
    assert report["standing_execution_authorization"] is False
    assert report["m1_robustness_completed"] is True
    assert report["last_completed_micro_part"] == (
        "stage126-m1-robustness-part6-smote-training-fold-only"
    )


def test_next_part_is_unauthorized_and_absent():
    """The next registered category must be unauthorized and have no package."""
    report = _read_json(v.F_REPORT)
    assert report["next_category_authorized"] is False
    next_index = report["completed_part_count"] + 1
    for suffix in ("_completion_lock.json", "_human_authorization_record.json",
                   "_oof_predictions.csv", "_metrics.csv"):
        assert not os.path.isfile(os.path.join(
            STAGE126,
            f"stage126_m1_robustness_part{next_index}{suffix}",
        )), suffix
    state = json.loads(
        (_root() / v.HANDOFF_STATE_REL).read_text(encoding="utf-8")
    )
    assert state["m1_robustness_part5_authorized"] is False
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
    assert report["active_workstream"] == (
        "stage128_m2_d2_boundary_month_equity_return"
    )
    # Part 6 closed the six-category robustness set, the synthesis-only
    # robustness closure completed, the retained-design freeze (PR #65)
    # completed, and the Stage128 M2 D2 boundary-month design freeze (PR #69)
    # has since also completed: the next research action legitimately
    # transitioned once more to the D2 Gate re-run pointer (which itself
    # still requires a separate future human authorization -- see
    # STAGE128_M2_D2_DESIGN_FREEZE.md §8-9).
    # The authorized paired M2-vs-M1 incremental evaluation was executed and
    # COMPLETED, and the human retained-block decision has since been RECORDED,
    # so the pointer advanced once more — to the M3 macro data Gate, which is a
    # POINTER, not an authorization.
    assert report["next_research_action_id"] == "stage128-m3-macro-data-gate"


@pytest.mark.parametrize("field", sorted(
    v.REQUIRED_HANDOFF_ARCHITECTURE_FIELDS
))
def test_mutating_each_handoff_architecture_field_fails_the_real_validator(
    tmp_path, field,
):
    """Each architecture field is enforced INSIDE verify_handoff, not just reported."""
    root = _mirror(tmp_path)
    path = root / v.HANDOFF_STATE_REL
    state = json.loads(path.read_text(encoding="utf-8"))
    original = state[field]
    state[field] = "TAMPERED" if isinstance(original, str) else (not original)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    with pytest.raises(v.ValidationFail) as exc:
        v.build_all(root, strict_pointers=False)
    assert field in str(exc.value)


@pytest.mark.parametrize("field", sorted(
    v.REQUIRED_HANDOFF_ARCHITECTURE_FIELDS
))
def test_removing_each_handoff_architecture_field_fails_the_real_validator(
    tmp_path, field,
):
    root = _mirror(tmp_path)
    path = root / v.HANDOFF_STATE_REL
    state = json.loads(path.read_text(encoding="utf-8"))
    del state[field]
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    with pytest.raises(v.ValidationFail) as exc:
        v.build_all(root, strict_pointers=False)
    assert field in str(exc.value)


def test_wrong_current_state_pointer_fails_even_when_not_strict(tmp_path):
    """A pointer that is PRESENT and wrong always fails, in either mode."""
    root = _mirror(tmp_path)
    path = root / v.HANDOFF_STATE_REL
    state = json.loads(path.read_text(encoding="utf-8"))
    state["current_state_validation_path"] = "project/stage126/WRONG.json"
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    with pytest.raises(v.ValidationFail):
        v.build_all(root, strict_pointers=False)


def test_wrong_micro_part_qc_count_fails(tmp_path):
    root = _mirror(tmp_path)
    path = root / v.HANDOFF_STATE_REL
    state = json.loads(path.read_text(encoding="utf-8"))
    state["last_completed_micro_part_qc_assertions"] = 1
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    with pytest.raises(v.ValidationFail):
        v.build_all(root, strict_pointers=False)


def test_handoff_carries_boundary_markers():
    state = json.loads(
        (_root() / v.HANDOFF_STATE_REL).read_text(encoding="utf-8")
    )
    assert state["validation_architecture"] == "stage126_q1q2_lean_governance_v1"
    assert state["stage125_part5_mode"] == "historical_immutable"
    assert state["stage125_part5_live_gate_active"] is False
    assert state["stage125_part5_future_regeneration_allowed"] is False
    assert state[
        "prior_part_scientific_artifact_regeneration_forbidden"
    ] is True
    assert state[
        "prior_part_operational_verification_artifact_evolution_permitted"
    ] is True
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
    for rel in ("project/stage126", "project/stage125", "project/stage128",
                "project/docs/ai", "project/src", "project/tests"):
        src = Path(REAL_ROOT) / rel
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst)
    # Every top-level runner: the closed-part registry pins each part's runner.
    (root / "project").mkdir(parents=True, exist_ok=True)
    for src in sorted((Path(REAL_ROOT) / "project").glob("*.py")):
        shutil.copy2(src, root / "project" / src.name)
    # The validator enumerates the frozen Stage125 tree via `git ls-files`, so
    # the mirror must be a real repository with the same ignore rules (the
    # part3c_outputs inputs are gitignored and therefore untracked upstream).
    shutil.copy2(Path(REAL_ROOT) / ".gitignore", root / ".gitignore")
    import subprocess
    for args in (["init", "-q"], ["add", "-A"],
                 ["-c", "user.email=t@t", "-c", "user.name=t",
                  "commit", "-qm", "mirror"]):
        subprocess.run(["git", "-C", str(root), *args], check=True,
                       capture_output=True)
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
    order = json.loads(
        (root / v.PART0_DECISION_RECORD_REL).read_text(encoding="utf-8")
    )["execution_order"]
    completed, ids = v.completed_prefix(root, order)
    assert ids == order[:6]
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

def _synthetic_next_part(root: Path) -> str:
    """Write a COMPLETE, valid synthetic Part 6 package into a mirrored repo.

    Parts 1-5 are already real in the mirror; Part 6
    (``smote_training_fold_only_robustness``) is the next registered category.
    Mirrors the real per-part package contract exactly: authorization record,
    completion lock, the full scientific surface, QC report, metadata manifest
    and README. Nothing here touches Parts 1-5 or Stage125. This synthetic
    package is a validator fixture only: it never runs literal SMOTE
    (``smote_executed`` stays False), but does set ``smotenc_executed=True``
    since Part 6 is the one registered category required to have executed
    SMOTENC (see ``SMOTE_ROBUSTNESS_CATEGORY_ID``).
    """
    d = root / "project/stage126"
    prefix = "stage126_m1_robustness_part6"
    micro_id = "stage126-m1-robustness-part6-smote"
    qc_scope = "stage126_m1_robustness_part6_smote"

    (d / f"{prefix}_human_authorization_record.json").write_text(json.dumps({
        "authorization_id": "stage126-m1-robustness-part6-human-authorization",
        "authorized_category_id": "smote_training_fold_only_robustness",
        "human_authorization_text": "synthetic part 6 authorization",
        "human_authorization_text_sha256": hashlib.sha256(
            b"synthetic part 6 authorization"
        ).hexdigest(),
        "part6_execution_authorized": True,
        "merge_authorized": False,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    (d / f"{prefix}_completion_lock.json").write_text(json.dumps({
        "category_id": "smote_training_fold_only_robustness",
        "micro_part_id": micro_id,
        "part6_human_authorized": True,
        "part6_execution_completed": True,
        "authorization_consumed": True,
        "development_only": True,
        "part7_execution_authorized": False,
        "m1_robustness_execution_authorized": False,
        "m1_robustness_started": True,
        "m1_robustness_completed": False,
        "full_development_refit_performed": False,
        "final_test_unlocked": False,
        "final_test_access_authorized": False,
        "final_test_evaluation_performed": False,
        "smote_executed": False,
        "smotenc_executed": True,
        "shap_executed": False,
        "replaces_primary_results": False,
        "selects_paper_winner": False,
        "completed_category_ids": [
            "m1_target_proximity_six_feature_set",
            "main_rule_b_listing_robustness",
            "expanded_rule_a_company_scope_robustness",
            "expanded_rule_b_combined_robustness",
            "persistent_loss_robustness_target",
            "smote_training_fold_only_robustness",
        ],
        "next_category_id": "",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    payloads = {
        f"{prefix}_feature_manifest.csv": "feature_order,feature_name\n1,synthetic\n",
        f"{prefix}_execution_manifest.json": json.dumps(
            {"category_id": "smote_training_fold_only_robustness"},
            indent=2, sort_keys=True) + "\n",
        f"{prefix}_oof_predictions.csv": "ticker,predicted_probability\nX,0.5\n",
        f"{prefix}_metrics.csv": "model_family,scope,pr_auc\nrf,pooled,0.4\n",
        f"{prefix}_primary_comparison.json": json.dumps(
            {"scientific_role": "sample_robustness_sensitivity_only"},
            indent=2, sort_keys=True) + "\n",
    }
    for name, text in payloads.items():
        (d / name).write_text(text, encoding="utf-8")

    (d / f"{prefix}_qc_report.json").write_text(json.dumps({
        "stage": qc_scope,
        "assertion_count": 7,
        "failed_count": 0,
        "all_pass": True,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    scientific_names = list(payloads) + [
        f"{prefix}_human_authorization_record.json",
        f"{prefix}_completion_lock.json",
    ]
    (d / f"metadata_and_hashes_{prefix}.json").write_text(json.dumps({
        "stage": qc_scope,
        "output_files_sha256": {
            name: hashlib.sha256((d / name).read_bytes()).hexdigest()
            for name in sorted(scientific_names)
        },
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (d / f"README_{prefix.upper()}.md").write_text(
        "# Synthetic Part 6\n", encoding="utf-8")

    # A real part also ships source, runner and tests — the registry pins them.
    (root / "project/src" / f"{prefix}_smote.py").write_text(
        '"""Synthetic Part 6 implementation."""\n', encoding="utf-8")
    (root / "project" / f"run_{prefix}_smote.py").write_text(
        '"""Synthetic Part 6 runner."""\n', encoding="utf-8")
    (root / "project/tests" / f"test_{prefix}_smote.py").write_text(
        '"""Synthetic Part 6 tests."""\n', encoding="utf-8")
    return micro_id


def _set_handoff_to_next_part(root: Path, micro_id: str) -> None:
    """Update the mirrored Handoff to the truthful Part 6-completed state."""
    path = root / v.HANDOFF_STATE_REL
    state = json.loads(path.read_text(encoding="utf-8"))
    state["last_completed_micro_part"] = micro_id
    state["m1_robustness_completed_category_ids"] = [
        "m1_target_proximity_six_feature_set",
        "main_rule_b_listing_robustness",
        "expanded_rule_a_company_scope_robustness",
        "expanded_rule_b_combined_robustness",
        "persistent_loss_robustness_target",
        "smote_training_fold_only_robustness",
    ]
    state["last_completed_micro_part_qc_scope"] = (
        "stage126_m1_robustness_part6_smote"
    )
    state["last_completed_micro_part_qc_path"] = (
        "project/stage126/stage126_m1_robustness_part6_qc_report.json"
    )
    state["last_completed_micro_part_qc_assertions"] = 7
    state["last_completed_micro_part_qc_failed"] = 0
    state["m1_robustness_completed"] = True
    state["next_research_action_id"] = "stage126-m1-robustness-closure"
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def _revert_mirror_to_pre_part6(root: Path) -> None:
    """Undo the real, already-closed Part 6 in a freshly mirrored repo.

    `_mirror` copies the REAL repo, which now genuinely contains a completed
    and hash-pinned Part 6. Injecting a DIFFERENT synthetic Part 6 package
    on top of that would collide with the closed-part registry's pinned
    scientific hashes for that same category (correctly fail-closed). This
    helper restores the mirror to the pre-Part-6 (five completed categories)
    state so the synthetic-next-part scenario this test exercises remains
    meaningful, without touching the REAL repository's own Part 6 artifacts.
    """
    d = root / "project/stage126"
    for pattern in (
        "stage126_m1_robustness_part6_*",
        "metadata_and_hashes_stage126_m1_robustness_part6*",
        "README_STAGE126_M1_ROBUSTNESS_PART6_SMOTE_TRAINING_FOLD_ONLY*",
    ):
        for path in d.glob(pattern):
            path.unlink()
    for rel in (
        "project/src/stage126_m1_robustness_part6_smote_training_fold_only.py",
        "project/run_stage126_m1_robustness_part6_smote_training_fold_only.py",
        "project/tests/test_stage126_m1_robustness_part6_smote_training_fold_only.py",
    ):
        (root / rel).unlink()

    registry_path = d / "stage126_closed_part_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["parts"].pop("smote_training_fold_only_robustness", None)
    registry["closed_part_count"] = len(registry["parts"])
    registry_path.write_text(
        json.dumps(registry, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    state_path = root / v.HANDOFF_STATE_REL
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["last_completed_micro_part"] = (
        "stage126-m1-robustness-part5-persistent-loss-target"
    )
    state["m1_robustness_completed_category_ids"] = [
        "m1_target_proximity_six_feature_set",
        "main_rule_b_listing_robustness",
        "expanded_rule_a_company_scope_robustness",
        "expanded_rule_b_combined_robustness",
        "persistent_loss_robustness_target",
    ]
    state["m1_robustness_next_category_id"] = "smote_training_fold_only_robustness"
    state["m1_robustness_completed"] = False
    state["next_research_action_id"] = "stage126-m1-financial-baseline"
    state["last_completed_micro_part_qc_scope"] = (
        "stage126_m1_robustness_part5_persistent_loss_target"
    )
    state["last_completed_micro_part_qc_path"] = (
        "project/stage126/stage126_m1_robustness_part5_qc_report.json"
    )
    state["last_completed_micro_part_qc_assertions"] = 134
    state["last_completed_micro_part_qc_failed"] = 0
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")


def test_end_to_end_synthetic_next_part_build_and_check(tmp_path):
    """FULL validator build + check on a mirrored repo with a valid next part.

    Runs the real build/check code paths — no monkeypatching of any expected
    current-state constant (they no longer exist) — and proves Parts 1-4 and
    Stage125 stay byte-identical.
    """
    root = _mirror(tmp_path)
    _revert_mirror_to_pre_part6(root)
    # The mirror copies the REAL repo, which now also contains the
    # synthesis-only robustness-closure completion lock. This test simulates
    # the state immediately after Part 6 lands (closure not yet built), so
    # remove the closure lock from the mirror -- otherwise the validator
    # would (correctly) advance the pointer past the value this synthetic
    # scenario expects.
    closure_lock = root / v.ROBUSTNESS_CLOSURE_LOCK_REL
    if closure_lock.is_file():
        closure_lock.unlink()
    watched = (
        [f"project/stage126/{n}" for n in
         list(PART1_SCIENTIFIC) + list(PART2_SCIENTIFIC)]
        + [rel for paths in CLOSED_VERIFICATION_ARTIFACTS.values() for rel in paths]
        + [f"project/stage126/stage126_m1_robustness_part4_{suf}" for suf in (
            "human_authorization_record.json", "feature_manifest.csv",
            "sample_delta.csv", "execution_manifest.json",
            "oof_predictions.csv", "metrics.csv", "primary_comparison.json",
            "completion_lock.json", "qc_report.json",
        )]
        + [v.PART5_SOURCE_REL, v.PART5_RUNNER_REL, v.PART5_TEST_REL]
        + [f"project/stage125/{p.name}"
           for p in sorted((Path(REAL_ROOT) / "project/stage125").glob("*.json"))]
    )
    before = {rel: _sha(root / rel) for rel in watched}

    micro_id = _synthetic_next_part(root)
    _set_handoff_to_next_part(root, micro_id)

    built = v.run(project_dir=root / "project", build=True)
    assert built["metadata"]["all_pass"] is True

    checked = v.run(project_dir=root / "project", check=True)
    assert checked["drift"] == []
    assert checked["metadata"]["all_pass"] is True

    report = checked["report"]
    assert report["completed_category_ids"] == [
        "m1_target_proximity_six_feature_set",
        "main_rule_b_listing_robustness",
        "expanded_rule_a_company_scope_robustness",
        "expanded_rule_b_combined_robustness",
        "persistent_loss_robustness_target",
        "smote_training_fold_only_robustness",
    ]
    assert report["completed_part_count"] == 6
    assert report["next_category_id"] == ""
    assert report["last_completed_micro_part"] == micro_id
    assert report["last_completed_micro_part_qc_scope"] == (
        "stage126_m1_robustness_part6_smote"
    )
    assert report["last_completed_micro_part_qc_assertions"] == 7
    assert set(report["closed_part_registry"]["parts"]) == {
        "m1_target_proximity_six_feature_set",
        "main_rule_b_listing_robustness",
        "expanded_rule_a_company_scope_robustness",
        "expanded_rule_b_combined_robustness",
        "persistent_loss_robustness_target",
        "smote_training_fold_only_robustness",
    }

    after = {rel: _sha(root / rel) for rel in watched}
    assert before == after
    assert _sha(root / v.SRC_REL) == _sha(Path(REAL_ROOT) / v.SRC_REL)


def test_end_to_end_skipped_part_with_later_part_present_fails(tmp_path):
    """A Part 5 package without Part 4 must fail the FULL validator."""
    root = _mirror(tmp_path)
    d = root / "project/stage126"
    for name, payload in (
        ("stage126_m1_robustness_part5_human_authorization_record.json",
         {"authorized_category_id": "persistent_loss_robustness_target"}),
        ("stage126_m1_robustness_part5_completion_lock.json",
         {"category_id": "persistent_loss_robustness_target",
          "micro_part_id": "stage126-m1-robustness-part5",
          "part5_execution_completed": True, "part5_human_authorized": True,
          "authorization_consumed": True, "development_only": True,
          "part6_execution_authorized": False}),
    ):
        (d / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                              encoding="utf-8")
    with pytest.raises(v.ValidationFail):
        v.run(project_dir=root / "project", build=True)


def test_skipped_category_fails_closed(tmp_path):
    """A Part 4 package without Part 3 must fail — categories cannot be skipped."""
    root = _mirror(tmp_path)
    d = root / "project/stage126"
    (d / "stage126_m1_robustness_part5_human_authorization_record.json").write_text(
        json.dumps({"authorized_category_id": "persistent_loss_robustness_target"}),
        encoding="utf-8",
    )
    (d / "stage126_m1_robustness_part5_completion_lock.json").write_text(
        json.dumps({"category_id": "persistent_loss_robustness_target"}),
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
     / "stage126_m1_robustness_part5_completion_lock.json").write_text(
        json.dumps({"category_id": "persistent_loss_robustness_target"}),
        encoding="utf-8",
    )
    with pytest.raises(v.ValidationFail):
        v.discover_part(root, 5, "persistent_loss_robustness_target")


def test_unauthorized_future_artifact_fails_closed(tmp_path):
    """A dangling artifact for a category beyond the completed prefix must
    fail closed. Part 6 is now genuinely completed in the real repo, so this
    simulates the pre-Part-6 state (only Parts 1-5 completed) and drops a
    Part 6 oof_predictions.csv WITHOUT the rest of its package -- exactly the
    "unauthorized future execution" scenario this guards against."""
    root = _mirror(tmp_path)
    part6_dir = root / "project/stage126"
    for path in part6_dir.glob("stage126_m1_robustness_part6_*"):
        path.unlink()
    for path in part6_dir.glob("metadata_and_hashes_stage126_m1_robustness_part6*"):
        path.unlink()
    for path in part6_dir.glob(
        "README_STAGE126_M1_ROBUSTNESS_PART6_SMOTE_TRAINING_FOLD_ONLY*"
    ):
        path.unlink()
    (part6_dir / "stage126_m1_robustness_part6_oof_predictions.csv").write_text(
        "a,b\n1,2\n", encoding="utf-8",
    )
    order = json.loads(
        (root / v.PART0_DECISION_RECORD_REL).read_text(encoding="utf-8")
    )["execution_order"]
    completed, _ids = v.completed_prefix(root, order)
    assert len(completed) == 5
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
    assert meta["validator_version"] == v.VALIDATOR_VERSION
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


def test_anchor_only_drift_helper_tolerates_commit_anchors_only(tmp_path):
    """The check-mode tolerance must stay narrow: anchors only, fail-closed."""
    expected = {
        "generated_at": "a" * 40,
        "code_commit": "a" * 40,
        "source_file_sha256": "b" * 64,
        "all_pass": True,
    }
    path = tmp_path / "metadata.json"

    def write(obj):
        path.write_text(json.dumps(obj), encoding="utf-8")

    # Only commit anchors differ -> tolerated.
    write({**expected, "generated_at": "c" * 40, "code_commit": "c" * 40})
    assert v._metadata_drift_is_anchor_only(path, expected) is True

    # A scientific/content field differs -> NOT tolerated.
    write({**expected, "generated_at": "c" * 40, "all_pass": False})
    assert v._metadata_drift_is_anchor_only(path, expected) is False

    # A hashed source file differs -> NOT tolerated.
    write({**expected, "source_file_sha256": "d" * 64})
    assert v._metadata_drift_is_anchor_only(path, expected) is False

    # Identical content is not "drift" at all.
    write(expected)
    assert v._metadata_drift_is_anchor_only(path, expected) is False

    # Added/removed keys -> NOT tolerated.
    write({**expected, "unexpected_extra_key": 1})
    assert v._metadata_drift_is_anchor_only(path, expected) is False

    # Malformed / missing file -> fail closed.
    path.write_text("{not json", encoding="utf-8")
    assert v._metadata_drift_is_anchor_only(path, expected) is False
    assert v._metadata_drift_is_anchor_only(tmp_path / "absent.json", expected) is False


def test_anchor_tolerance_covers_only_the_metadata_file():
    # Every other tracked output must remain fully drift-gated.
    assert v.METADATA_COMMIT_ANCHOR_FIELDS == ("generated_at", "code_commit")
    for name in (v.F_DECISION, v.F_BOUNDARY_MANIFEST, v.F_REPORT,
                 v.F_README, v.F_CLOSED_REGISTRY):
        assert name != v.F_METADATA


def test_deterministic_repeated_build(tmp_path):
    a = v.run(project_dir=Path(REAL_ROOT) / "project",
              output_dir=tmp_path / "a", build=True)
    b = v.run(project_dir=Path(REAL_ROOT) / "project",
              output_dir=tmp_path / "b", build=True)
    assert a["files"] == b["files"]


# --------------------------------------------------------------------------- #
# Stage126+ Q1/Q2 Lean Governance — legacy validation boundary adaptation
#
# Only `scientific_artifacts_sha256` and completion/category identity fields
# remain live scientific gates for a closed registry part;
# `code_artifacts_sha256` / `verification_artifacts_sha256` (test/QC/metadata
# bookkeeping) are historical provenance only and never fail the live gate.
# --------------------------------------------------------------------------- #

def _committed_registry(repo_root: Path) -> dict:
    return json.loads(
        (repo_root / v.STAGE126_DIR_REL / v.F_CLOSED_REGISTRY)
        .read_text(encoding="utf-8")
    )


def test_scientific_artifact_drift_still_fails_closed():
    """A closed part's SCIENTIFIC artifact hash may never change."""
    repo_root = _root()
    committed = _committed_registry(repo_root)
    generated = json.loads(json.dumps(committed))  # deep copy
    category = "m1_target_proximity_six_feature_set"
    rel = next(iter(generated["parts"][category]["scientific_artifacts_sha256"]))
    generated["parts"][category]["scientific_artifacts_sha256"][rel] = "0" * 64
    with pytest.raises(v.ValidationFail, match="scientific/identity drift"):
        v.verify_registry_immutability(repo_root, generated)


def test_completion_lock_mutation_still_fails_closed():
    """A closed part's completion-lock identity may never change."""
    repo_root = _root()
    committed = _committed_registry(repo_root)
    generated = json.loads(json.dumps(committed))
    category = "main_rule_b_listing_robustness"
    generated["parts"][category]["completion_lock_sha256"] = "f" * 64
    with pytest.raises(v.ValidationFail, match="scientific/identity drift"):
        v.verify_registry_immutability(repo_root, generated)


def test_operational_bookkeeping_drift_alone_is_not_a_scientific_failure():
    """Test/QC/metadata bookkeeping hash drift never raises: informational only."""
    repo_root = _root()
    committed = _committed_registry(repo_root)
    generated = json.loads(json.dumps(committed))
    category = "m1_target_proximity_six_feature_set"
    for bucket in ("code_artifacts_sha256", "verification_artifacts_sha256"):
        rel = next(iter(generated["parts"][category][bucket]))
        generated["parts"][category][bucket][rel] = "0" * 64
    informational = v.verify_registry_immutability(repo_root, generated)
    assert len(informational) == 2
    assert all(
        b.startswith("code_artifacts_sha256:")
        or b.startswith("verification_artifacts_sha256:")
        for b in informational
    )


def test_final_test_lock_drift_still_fails_closed(tmp_path):
    """Final-test lock flags flipping True must fail closed, never be waived."""
    repo_root = _root()
    for rel in (v.FINAL_TEST_LOCK_GUARD_REL, v.PRIMARY_DEVELOPMENT_LOCK_REL):
        src = repo_root / rel
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    # Sanity: the real, untouched copies pass.
    v.verify_final_test_lock(tmp_path)

    tampered = json.loads(
        (tmp_path / v.FINAL_TEST_LOCK_GUARD_REL).read_text(encoding="utf-8")
    )
    tampered[v.FINAL_TEST_LOCK_FIELDS[0]] = True
    (tmp_path / v.FINAL_TEST_LOCK_GUARD_REL).write_text(
        json.dumps(tampered), encoding="utf-8"
    )
    with pytest.raises(v.ValidationFail):
        v.verify_final_test_lock(tmp_path)


def test_lean_governance_handoff_fields_are_enforced():
    state = json.loads(
        (_root() / v.HANDOFF_STATE_REL).read_text(encoding="utf-8")
    )
    assert state["validation_architecture"] == "stage126_q1q2_lean_governance_v1"
    for field in (
        "scientific_artifacts_hard_locked",
        "operational_surfaces_git_versioned",
        "single_live_current_state_authority",
        "legacy_validation_boundary_adapted",
    ):
        assert state[field] is True, field


def test_informational_drift_reported_but_never_fails_build_assertions():
    """`closed_part_registry_scientific_state_immutable` always PASSes here.

    Fatal (scientific/identity) drift already raises inside
    verify_registry_immutability before build_assertions runs, so any
    registry_drift reaching build_assertions is informational-only by
    construction; the assertion documents that state rather than gating it.
    """
    meta = _read_json(v.F_METADATA)
    names = {a["name"]: a for a in meta["assertions"]}
    assert "closed_part_registry_scientific_state_immutable" in names
    assert names["closed_part_registry_scientific_state_immutable"]["status"] == "PASS"


# --------------------------------------------------------------------------- #
# Stage127 human-review closure after the Stage128 D2 design freeze
# --------------------------------------------------------------------------- #

def _live_handoff() -> dict:
    return json.loads(
        (_root() / v.HANDOFF_STATE_REL).read_text(encoding="utf-8")
    )


def test_stage128_freeze_forbids_stale_stage127_pending_human_review():
    """The contradiction this guard exists for must be detected.

    Once the Stage128 D2 design freeze is completed, the freeze IS the human
    decision the terminal Stage127 FAIL result was waiting for, so neither
    Stage127 pending-human-review marker may still be True.
    """
    ok = dict(_live_handoff())
    assert v.stage127_human_review_closure_consistent(
        ok, freeze_completed=True) is True

    for field in (
        "stage127_m2_market_data_gate_terminal_result_pending_human_review",
        "stage127_m2_semantics_human_decision_required",
    ):
        contradictory = dict(ok)
        contradictory[field] = True
        assert v.stage127_human_review_closure_consistent(
            contradictory, freeze_completed=True) is False, field
        # Before the freeze the same state is legitimate history.
        assert v.stage127_human_review_closure_consistent(
            contradictory, freeze_completed=False) is True, field


def test_live_handoff_has_no_stage127_human_review_contradiction():
    state = _live_handoff()
    if state.get("stage128_m2_d2_design_freeze_completed"):
        assert state[
            "stage127_m2_market_data_gate_terminal_result_pending_human_review"
        ] is False
        assert state["stage127_m2_semantics_human_decision_required"] is False
        # The history is preserved, not erased.
        assert state["stage127_m2_human_review_originally_required"] is True
        assert state["stage127_m2_human_review_resolved_by_action_id"] == (
            "stage128-m2-boundary-month-return-design-freeze"
        )


def test_historical_d0_gate_status_never_rewritten():
    state = _live_handoff()
    assert state["stage127_m2_market_data_gate_status"] == "FAIL_M2_DATA_GATE"
    assert v.stage127_historical_d0_gate_status_preserved(state) is True
    for bad in ("PASS_M2_DATA_GATE", "PASS", "UNRESOLVED"):
        tampered = dict(state)
        tampered["stage127_m2_market_data_gate_status"] = bad
        assert v.stage127_historical_d0_gate_status_preserved(tampered) is False


def test_current_state_renders_stage128_section_after_freeze():
    state = _live_handoff()
    text = (_root() / v.CURRENT_STATE_MD_REL).read_text(encoding="utf-8")
    if state.get("stage128_m2_d2_design_freeze_completed"):
        assert (
            "## Stage128 — M2 D2 boundary-month equity-return design freeze"
            in text
        )
        # Stage127 is rendered as HISTORICAL, not as the current action.
        assert "(HISTORICAL — COMPLETED AND RESOLVED)" in text
        assert (
            "_The current scientific action. Its human authorization already "
            "exists" not in text
        )
        assert "Human decision still required" not in text
        assert "`FAIL_M2_DATA_GATE`" in text


def test_new_stage127_closure_assertions_present_and_passing():
    meta = _read_json(v.F_METADATA)
    names = {a["name"]: a for a in meta["assertions"]}
    for name in (
        "stage128_freeze_closes_stage127_pending_human_review",
        "stage127_human_review_history_not_erased",
        "stage127_historical_d0_gate_status_preserved",
        "current_state_renders_stage128_section_after_freeze",
        "current_state_does_not_call_stage127_the_current_action_after_freeze",
    ):
        assert name in names, name
        assert names[name]["status"] == "PASS", name


# --------------------------------------------------------------------------- #
# Live current-state labels must not go stale after the Stage128 D2 freeze
# --------------------------------------------------------------------------- #

def test_stage128_freeze_forbids_stale_stage126_current_labels():
    """`current_stage` / `active_workstream` describe the CURRENT state.

    Leaving them at `Stage126` / `stage126_m1_financial_baseline` once the
    Stage128 D2 design freeze is complete produces an ambiguous live state:
    a snapshot naming the Stage126 M1 workstream beside canonical pointers
    that have advanced past the Stage126 M1 baseline.
    """
    ok = dict(_live_handoff())
    assert v.current_state_labels_are_not_stale(
        ok, freeze_completed=True) is True

    for field, stale in (
        ("current_stage", "Stage126"),
        ("active_workstream", "stage126_m1_financial_baseline"),
    ):
        contradictory = dict(ok)
        contradictory[field] = stale
        assert v.current_state_labels_are_not_stale(
            contradictory, freeze_completed=True) is False, field
        # Before the freeze the same values are the correct live state.
        assert v.current_state_labels_are_not_stale(
            contradictory, freeze_completed=False) is True, field


def test_live_handoff_labels_match_the_live_research_state():
    state = _live_handoff()
    if state.get("stage128_m2_d2_design_freeze_completed"):
        assert state["current_stage"] == "Stage128"
        assert state["active_workstream"] == (
            "stage128_m2_d2_boundary_month_equity_return"
        )
        # The authoritative research-action ids advance only with real
        # scientific actions, never with a label fix. The D2 design freeze,
        # then the executed D2 Gate re-run, each advanced them once.
        assert state["last_completed_research_action_id"] == (
            "stage128-m2-retained-block-human-decision"
        )
        assert state["next_research_action_id"] == (
            "stage128-m3-macro-data-gate"
        )
        # And nothing further is AUTHORIZED by advancing a label.
        for field in (
            "stage128_m2_d2_gate_rerun_authorized",
            "m2_incremental_evaluation_authorized",
            "final_test_unlocked",
        ):
            assert state[field] is False, field
        # `m2_modeling_started` is an EXECUTION fact, not an authorization: it
        # is True because the separately authorized paired M2 evaluation
        # actually ran. A label fix never sets it, and a consumed
        # authorization never unsets it.
        assert state["m2_modeling_started"] is True
        # Retention is now DECIDED (a governance decision), and it authorizes
        # nothing further: superiority stays unclaimed and M3 stays unstarted.
        assert state["m2_block_retained"] is True
        assert state["m2_predictive_superiority_claim_supported"] is False
        assert state["stage127_m2_market_data_gate_status"] == (
            "FAIL_M2_DATA_GATE"
        )


def test_expected_labels_are_state_dependent_not_hardcoded():
    root = _root()
    assert v.expected_current_stage(root) == "Stage128"
    assert v.expected_active_workstream(root) == (
        "stage128_m2_d2_boundary_month_equity_return"
    )
    # The Stage126 constants survive as the pre-freeze expectation.
    assert v.ACTIVE_WORKSTREAM == "stage126_m1_financial_baseline"
    assert v.STAGE126_CURRENT_STAGE == "Stage126"


def test_current_state_snapshot_renders_stage128_labels():
    state = _live_handoff()
    text = (_root() / v.CURRENT_STATE_MD_REL).read_text(encoding="utf-8")
    if state.get("stage128_m2_d2_design_freeze_completed"):
        assert "- **Stage / Batch:** Stage128 /" in text
        assert (
            "- **Active workstream:** `stage128_m2_d2_boundary_month_equity_return`"
            in text
        )
        assert (
            "- **Next research action:** "
            "`stage128-m3-macro-data-gate`" in text
        )
        assert (
            "## Stage128 — M2 D2 boundary-month equity-return design freeze"
            in text
        )


def test_stale_label_assertions_present_and_passing():
    meta = _read_json(v.F_METADATA)
    names = {a["name"]: a for a in meta["assertions"]}
    for name in (
        "current_state_labels_not_stale_after_stage128_freeze",
        "stage128_workstream_id_does_not_replace_research_action_ids",
        "stage128_freeze_authorizes_nothing_further",
    ):
        assert name in names, name
        assert names[name]["status"] == "PASS", name


# --------------------------------------------------------------------------- #
# Stage128 D2 Gate re-run — current-state rendering must fail closed
# --------------------------------------------------------------------------- #

_CURRENT_STATE = os.path.join(REAL_ROOT, "project", "docs", "ai",
                              "CURRENT_STATE.md")
_ROADMAP = os.path.join(REAL_ROOT, v.ROADMAP_MD_REL)

_RERUN_RENDERING_ASSERTIONS = (
    "current_state_freeze_section_not_current_after_gate_rerun",
    "current_state_has_exactly_one_current_scientific_action_section",
    "current_state_current_section_is_the_live_action",
    "current_state_gate_rerun_section_not_current_after_successor",
    "m2_incremental_evaluation_authorization_is_consumed_not_standing",
    "m2_evaluation_selects_no_winner_and_retains_no_block",
    "completed_m2_evaluation_with_44_fits_implies_modeling_started",
    "m2_evaluation_consumed_authorization_stays_false",
    "m2_block_retained_remains_false_pending_human_decision",
    "m3_and_m4_remain_unauthorized_and_unstarted",
    "final_test_remains_locked_after_the_m2_evaluation",
    "completed_m2_evaluation_implies_market_data_collected_and_materialized",
    "frozen_stage125_m2_data_collected_is_never_rendered_as_live_state",
    "frozen_stage125_m2_data_collected_value_is_not_mutated",
    "current_state_final_test_wording_is_literally_precise",
    "m2_evaluation_records_a_required_human_retained_block_decision",
    "current_state_freeze_section_claims_only_its_own_action",
    "current_state_freeze_section_does_not_claim_the_gate_rerun",
    "current_state_does_not_call_incremental_evaluation_the_gate_rerun",
    "current_state_renders_a_single_live_next_action_pointer",
    "current_state_next_pointer_is_a_pointer_not_an_authorization",
    "next_pointer_flags_are_false_when_pointer_is_incremental_evaluation",
    "gate_rerun_complete_implies_current_action_is_the_gate_rerun_"
    "or_a_recognized_successor",
    "roadmap_prose_agrees_with_front_matter_pointers",
    "roadmap_prose_does_not_contradict_front_matter_pointers",
    "roadmap_prose_does_not_call_incremental_evaluation_the_gate_rerun",
)


def test_gate_rerun_rendering_guards_exist_and_pass():
    meta = _read_json(v.F_METADATA)
    by_name = {a["name"]: a for a in meta["assertions"]}
    for name in _RERUN_RENDERING_ASSERTIONS:
        assert name in by_name, name
        assert by_name[name]["status"] == "PASS", name


def test_current_state_presents_exactly_one_current_section():
    text = open(_CURRENT_STATE, encoding="utf-8").read()
    current = [ln for ln in text.splitlines()
               if ln.startswith("## ") and "(CURRENT)" in ln]
    assert len(current) == 1, current
    assert "M2 retained-block HUMAN decision" in current[0]
    assert (
        "## Stage127 — paired M2 vs M1 incremental evaluation (CURRENT)"
        not in text
    )
    assert (
        "## Stage128 — canonical M2 Gate RE-RUN under Gregorian D2 (CURRENT)"
        not in open(_CURRENT_STATE, encoding="utf-8").read()
    )


def test_design_freeze_section_is_historical_after_the_gate_rerun():
    text = open(_CURRENT_STATE, encoding="utf-8").read()
    assert (
        "## Stage128 — M2 D2 boundary-month equity-return design freeze "
        "(COMPLETED DESIGN CONTRACT)" in text
    )
    assert (
        "## Stage128 — M2 D2 boundary-month equity-return design freeze "
        "(CURRENT)" not in text
    )
    assert (
        "- **Research action completed by this freeze:** "
        "`stage128-m2-boundary-month-return-design-freeze`" in text
    )
    assert (
        "Research action completed by this freeze:** "
        "`stage128-m2-d2-gate-rerun`" not in text
    )


def test_sole_live_next_pointer_is_a_pointer_not_an_authorization():
    text = open(_CURRENT_STATE, encoding="utf-8").read()
    pointers = [ln for ln in text.splitlines()
                if ln.startswith("- **Next research action (pointer only):**")]
    assert len(pointers) == 1, pointers
    line = pointers[0]
    assert "`stage128-m3-macro-data-gate`" in line
    assert "pointer is **not** an authorization" in line


def test_incremental_evaluation_is_never_called_the_gate_rerun():
    for path in (_CURRENT_STATE, _ROADMAP):
        text = open(path, encoding="utf-8").read()
        assert not v._describes_incremental_evaluation_as_gate_rerun(text), path


def test_helper_detects_the_conflation_and_allows_the_negation():
    bad = (
        "- **Next research action (pointer only):** "
        "`stage127-m2-incremental-evaluation` — the canonical M2 Gate re-run "
        "under the frozen D2 construct"
    )
    good = (
        "- **Next research action (pointer only):** "
        "`stage127-m2-incremental-evaluation` — it is NOT the canonical M2 "
        "Gate re-run"
    )
    assert v._describes_incremental_evaluation_as_gate_rerun(bad) is True
    assert v._describes_incremental_evaluation_as_gate_rerun(good) is False


def test_roadmap_front_matter_matches_handoff_pointers():
    text = open(_ROADMAP, encoding="utf-8").read()
    fm = v._roadmap_front_matter(text)
    assert fm["last_completed_research_action_id"] == (
        "stage128-m2-retained-block-human-decision"
    )
    assert fm["next_research_action_id"] == "stage128-m3-macro-data-gate"
    state = json.loads(open(
        os.path.join(REAL_ROOT, "project", "docs", "ai",
                     "handoff_state.json"), encoding="utf-8").read())
    assert fm["last_completed_research_action_id"] == (
        state["last_completed_research_action_id"]
    )
    assert fm["next_research_action_id"] == state["next_research_action_id"]


def test_roadmap_prose_drops_the_superseded_pointer_pair_claim():
    text = open(_ROADMAP, encoding="utf-8").read()
    assert (
        "the authoritative pointers remain "
        "`last_completed_research_action_id: "
        "stage128-m2-boundary-month-return-design-freeze`" not in text
    )
    assert "are now **historical** pointer state" in text


def test_live_m2_state_distinguishes_authorization_execution_and_retention():
    """Consumed authorization must not erase the executed M2 modeling."""
    state = json.loads(open(
        os.path.join(REAL_ROOT, "project", "docs", "ai",
                     "handoff_state.json"), encoding="utf-8").read())
    # Executed.
    assert state["stage127_m2_incremental_evaluation_executed"] is True
    assert state["stage127_m2_incremental_evaluation_completed"] is True
    assert state[
        "stage127_m2_incremental_evaluation_authorization_consumed"] is True
    assert state["stage127_m2_incremental_evaluation_primary_model_fits"] == 44
    assert state["m2_started"] is True
    assert state["m2_modeling_started"] is True
    assert state["m2_block_admitted_for_modeling"] is True
    assert state[
        "m2_block_admitted_for_authorized_incremental_evaluation"] is True
    # Authorization consumed.
    assert state["m2_incremental_evaluation_authorized"] is False
    # Retention DECIDED by a separate human governance action; successors and
    # the final test remain untouched, and no superiority is claimed.
    assert state["m2_block_retained"] is True
    assert state["m2_retained_block_decision_required"] is False
    assert state["m2_retained_block_human_decision_completed"] is True
    assert state["m2_predictive_superiority_claim_supported"] is False
    assert state["m2_superiority_established"] is False
    assert state["m2_winner_selected"] is False
    for field in (
        "m3_authorized", "m3_started", "m4_authorized", "m4_started",
        "final_test_unlocked", "final_test_access_authorized",
        "final_test_evaluation_performed",
    ):
        assert state[field] is False, field


def test_current_state_does_not_report_modeling_as_never_started():
    text = open(_CURRENT_STATE, encoding="utf-8").read()
    assert "**M2 modeling started (executed):** True" in text
    assert "**M2 block admitted for modeling:** True" in text
    assert "does **not** mean the modeling never happened" in text


def test_live_m2_data_state_is_true_and_historical_marker_is_labelled():
    """The frozen Part 4 marker must not masquerade as live state."""
    state = json.loads(open(
        os.path.join(REAL_ROOT, "project", "docs", "ai",
                     "handoff_state.json"), encoding="utf-8").read())
    # 1. completed evaluation implies collected + materialized
    for field in (
        "m2_market_data_evidence_collected",
        "m2_market_data_evidence_validated",
        "m2_data_entered_authorized_incremental_modeling_pipeline",
        "m2_incremental_evaluation_data_materialized",
    ):
        assert state[field] is True, field
    # 2. the frozen Part 4 value is preserved and explicitly labelled
    assert state["m2_data_collected"] is False
    assert state["stage125_part4_m2_data_collected_historical"] is False
    assert "not a live data-availability or execution marker" in state[
        "stage125_part4_m2_data_collected_historical_semantics"]
    # 3-7. the surrounding distinctions are unchanged
    assert state["m2_incremental_evaluation_authorized"] is False
    assert state["m2_started"] is True
    assert state["m2_modeling_started"] is True
    assert state["m2_block_retained"] is True
    assert state["m2_retained_block_decision_required"] is False
    for field in (
        "m3_authorized", "m3_started", "m4_authorized", "m4_started",
        "final_test_unlocked", "final_test_access_authorized",
        "final_test_evaluation_performed",
    ):
        assert state[field] is False, field


def test_current_state_never_renders_bare_m2_data_collected_as_live():
    text = open(_CURRENT_STATE, encoding="utf-8").read()
    live = text.split("## Workflow markers")[1].split("## ")[0]
    assert "- m2_data_collected: " not in live
    assert "- m3_data_collected: " in live
    # It is republished only under the clearly titled historical heading.
    assert (
        "## Historical / legacy frozen schema markers (NOT live state)" in text
    )
    assert "stage125_part4_m2_data_collected_historical" in text


def test_current_state_reports_the_live_m2_market_data_state():
    text = open(_CURRENT_STATE, encoding="utf-8").read()
    assert "**M2 market data (live):** evidence collected=True" in text
    assert "entered the authorized incremental modeling pipeline=True" in text
    assert "evaluation data materialized=True" in text
