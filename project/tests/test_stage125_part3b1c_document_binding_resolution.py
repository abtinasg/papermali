"""Tests for Stage125 Part 3B.1C Document Binding Resolution Decision Lock."""
from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from src import stage125_part3b0_evidence_readiness as p3b0  # noqa: E402
from src import stage125_part3b1c_document_binding_resolution as m  # noqa: E402


def test_exact_five_row_scope():
    rows = m.load_evidence_rows(REPO_ROOT)
    assert [r["predictor_row_key_t"] for r in rows] == list(m.LOCKED_KEYS)


def test_exact_frozen_part3b1b_hashes():
    pinned = m.verify_pinned_inputs(REPO_ROOT)
    assert pinned == m.PINNED_INPUTS


def test_all_frozen_failure_tokens_covered():
    evidence = m.load_evidence_rows(REPO_ROOT)
    tax = list(csv.DictReader(
        (REPO_ROOT / "project/stage125" / m.F_TAXONOMY).open(encoding="utf-8")
    ))
    m.verify_taxonomy_coverage(evidence, tax)


def test_missing_taxonomy_token_fails(tmp_path):
    evidence = m.load_evidence_rows(REPO_ROOT)
    tax = list(csv.DictReader(
        (REPO_ROOT / "project/stage125" / m.F_TAXONOMY).open(encoding="utf-8")
    ))
    tax = [r for r in tax if r["failure_reason"] != "entity_mismatch"]
    with pytest.raises(m.QCFail, match="all_failure_tokens_taxonomized"):
        m.verify_taxonomy_coverage(evidence, tax)


def test_invented_taxonomy_token_fails():
    evidence = m.load_evidence_rows(REPO_ROOT)
    tax = list(csv.DictReader(
        (REPO_ROOT / "project/stage125" / m.F_TAXONOMY).open(encoding="utf-8")
    ))
    invented = dict(tax[0])
    invented["failure_reason"] = "invented_token_xyz"
    tax.append(invented)
    with pytest.raises(m.QCFail, match="no_invented_failure_token"):
        m.verify_taxonomy_coverage(evidence, tax)


def test_raw_source_canonical_values_preserved():
    tax = list(csv.DictReader(
        (REPO_ROOT / "project/stage125" / m.F_TAXONOMY).open(encoding="utf-8")
    ))
    entity_rows = [r for r in tax if r["failure_reason"] == "entity_mismatch"]
    assert entity_rows
    thanusa = next(r for r in entity_rows if r["predictor_row_key_t"] == "ثنوسا|1392")
    assert thanusa["observed_source_value"] == "نوسازي و ساختمان تهران"
    assert thanusa["observed_canonical_value"] == "نوسازی و ساختمان تهران"


def test_arabic_persian_character_normalization_mechanical():
    raw = "نوسازي"
    canon = "نوسازی"
    assert m.apply_mechanical_normalization(raw) == m.apply_mechanical_normalization(canon)


def test_arbitrary_word_removal_rejected():
    with pytest.raises(m.QCFail, match="prohibited_normalization_config"):
        m.reject_fuzzy_or_destructive_config({"remove_arbitrary_words": True})


def test_global_removal_of_sherkat_rejected():
    with pytest.raises(m.QCFail, match="prohibited_normalization_config"):
        m.reject_fuzzy_or_destructive_config({"global_remove_شرکت": True})


def test_fuzzy_matching_configuration_rejected():
    with pytest.raises(m.QCFail, match="prohibited_normalization_config"):
        m.reject_fuzzy_or_destructive_config({"fuzzy_matching": True})


def test_subsidiary_only_row_structurally_rejected():
    req = list(csv.DictReader(
        (REPO_ROOT / "project/stage125" / m.F_ROW_REQ).open(encoding="utf-8")
    ))
    ard = next(r for r in req if r["predictor_row_key_t"] == "اردستان|1401")
    assert ard["structural_disposition"] == "structurally_rejected"
    assert ard["current_status"] == "REJECTED"


def test_unknown_revision_remains_unknown():
    hier = json.loads(
        (REPO_ROOT / "project/stage125" / m.F_HIERARCHY).read_text(encoding="utf-8")
    )
    assert hier["locked_rules"]["unknown_revision_status_remains_unresolved"] is True
    assert hier["locked_rules"]["absence_of_eslahiye_does_not_prove_original"] is True


def test_incomplete_cache_cannot_prove_unique_binding():
    hier = json.loads(
        (REPO_ROOT / "project/stage125" / m.F_HIERARCHY).read_text(encoding="utf-8")
    )
    assert hier["locked_rules"][
        "incomplete_paginated_cache_cannot_prove_canonical_uniqueness"
    ] is True


def test_publish_datetime_cannot_be_assigned_before_binding():
    hier = json.loads(
        (REPO_ROOT / "project/stage125" / m.F_HIERARCHY).read_text(encoding="utf-8")
    )
    assert hier["locked_rules"][
        "publish_datetime_only_after_exact_source_version_binding"
    ] is True


def test_sent_datetime_cannot_become_available_at():
    hier = json.loads(
        (REPO_ROOT / "project/stage125" / m.F_HIERARCHY).read_text(encoding="utf-8")
    )
    assert hier["locked_rules"]["sent_datetime_is_audit_only_never_available_at"] is True


def test_wildcard_url_fails():
    evidence = m.load_evidence_rows(REPO_ROOT)
    bad = [dict(r) for r in evidence]
    bad[0]["source_url"] = "https://www.codal.ir/*/Decision.aspx"
    with pytest.raises(m.QCFail, match="wildcard_endpoint_forbidden"):
        m.build_proposed_capture(bad)


def test_wildcard_host_fails():
    proposed = json.loads(
        (REPO_ROOT / "project/stage125" / m.F_PROPOSED).read_text(encoding="utf-8")
    )
    assert proposed["wildcard_host_forbidden"] is True
    assert proposed["wildcard_url_forbidden"] is True


def test_unresolved_endpoint_stays_null_when_url_absent():
    evidence = m.load_evidence_rows(REPO_ROOT)
    cleared = [dict(r) for r in evidence]
    for r in cleared:
        r["source_url"] = ""
    prop = m.build_proposed_capture(cleared)
    for req in prop["proposed_requests"]:
        if req["request_status"] == "endpoint_unresolved_not_authorizable":
            assert req["exact_url"] is None


def test_authorization_status_cannot_become_authorized():
    proposed = json.loads(
        (REPO_ROOT / "project/stage125" / m.F_PROPOSED).read_text(encoding="utf-8")
    )
    assert proposed["authorization_status"] == "not_authorized"
    assert proposed["execution_performed"] is False
    assert proposed["requires_explicit_user_approval"] is True


def test_network_sentinel_records_zero_requests():
    with p3b0.network_sentinel() as sentinel:
        result = m.run(project_dir=ROOT, check=True)
        assert sentinel.calls_attempted == 0
    assert result["network_requests_attempted"] == 0


def test_current_scientific_counts_unchanged():
    evidence = m.load_evidence_rows(REPO_ROOT)
    m.verify_current_statuses(evidence)
    qc = json.loads(
        (REPO_ROOT / "project/stage125" / m.F_QC).read_text(encoding="utf-8")
    )
    assert qc["bound_count"] == 0
    assert qc["unresolved_count"] == 4
    assert qc["rejected_count"] == 1
    assert qc["available_at_non_null_count"] == 0


def test_scale_up_to_80_cannot_become_true():
    scale = json.loads(
        (REPO_ROOT / "project/stage125" / m.F_SCALE).read_text(encoding="utf-8")
    )
    assert scale["scale_up_to_80_rows_authorized"] is False


def test_value_extraction_fields_forbidden():
    scale = json.loads(
        (REPO_ROOT / "project/stage125" / m.F_SCALE).read_text(encoding="utf-8")
    )
    assert scale["candidate_value_extraction_authorized"] is False
    assert scale["pair_value_extraction_authorized"] is False
    text = (REPO_ROOT / "project/stage125" / m.F_LOCK).read_text(encoding="utf-8")
    assert "m1_value" not in text
    assert "operating_cash_flow" not in text


def test_scoring_gate_fields_forbidden():
    scale = json.loads(
        (REPO_ROOT / "project/stage125" / m.F_SCALE).read_text(encoding="utf-8")
    )
    assert scale["accessibility_scoring_authorized"] is False
    assert scale["gate_application_authorized"] is False
    qc = json.loads(
        (REPO_ROOT / "project/stage125" / m.F_QC).read_text(encoding="utf-8")
    )
    assert qc["accessibility_scoring_applied"] is False
    assert qc["gates_applied"] == 0


def test_stage126_modeling_surfaces_forbidden():
    scale = json.loads(
        (REPO_ROOT / "project/stage125" / m.F_SCALE).read_text(encoding="utf-8")
    )
    assert scale["stage126_authorized"] is False
    assert scale["modeling_authorized"] is False
    assert scale["part3b2_authorized"] is False
    for rel in m.FORBIDDEN_SURFACE_EXACT:
        assert not (REPO_ROOT / rel).exists()


def test_official_check_zero_drift():
    result = m.run(project_dir=ROOT, check=True)
    assert result["drift"] == []
    assert result["files"] == {}


def test_mutation_of_committed_artifact_causes_check_drift(tmp_path):
    wt = tmp_path / "iso"
    subprocess.run(
        ["git", "-C", str(REPO_ROOT), "worktree", "add", "--detach", str(wt), "HEAD"],
        check=True, capture_output=True, text=True,
    )
    try:
        for rel in sorted(m.PART3B1C_AUTHORIZED_EXACT):
            src = REPO_ROOT / rel
            if src.is_file():
                dst = wt / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        target = wt / "project" / "stage125" / m.F_TAXONOMY
        target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with pytest.raises(m.QCFail, match="check drift"):
            m.run(project_dir=wt / "project", check=True)
    finally:
        subprocess.run(
            ["git", "-C", str(REPO_ROOT), "worktree", "remove", "--force", str(wt)],
            check=False, capture_output=True, text=True,
        )


def test_fresh_clone_check_zero_writes_zero_network(tmp_path):
    missing = tmp_path / "does_not_exist"
    before = {
        p: p.stat().st_mtime_ns
        for p in (REPO_ROOT / "project" / "stage125").glob("part3b1c_*")
    }
    with p3b0.network_sentinel() as sentinel:
        result = m.run(project_dir=ROOT, output_dir=missing, check=True)
        assert sentinel.calls_attempted == 0
    assert not missing.exists()
    assert result["files"] == {}
    after = {
        p: p.stat().st_mtime_ns
        for p in (REPO_ROOT / "project" / "stage125").glob("part3b1c_*")
    }
    assert before == after


def test_frozen_scientific_hashes_unchanged():
    before = m.frozen_scientific_hashes(REPO_ROOT)
    with tempfile.TemporaryDirectory() as td:
        m.run(project_dir=ROOT, output_dir=Path(td) / "stage125", check=True)
    after = m.frozen_scientific_hashes(REPO_ROOT)
    assert before == after


def test_research_pointers_unchanged():
    qc = json.loads(
        (REPO_ROOT / "project/stage125" / m.F_QC).read_text(encoding="utf-8")
    )
    assert qc["research_pointers"]["last_completed_research_action_id"] == (
        "stage125-part3a-decision-lock"
    )
    assert qc["research_pointers"]["next_research_action_id"] == (
        "stage125-part3b-evidence-capture"
    )


def test_bouali_prefix_not_auto_aliased():
    norm = json.loads(
        (REPO_ROOT / "project/stage125" / m.F_NORM).read_text(encoding="utf-8")
    )
    assert norm["pinned_alias_source_present"] is False
    pair = norm["explicit_non_equivalence_without_alias"][0]
    assert pair["normalization_safe"] is False
    assert pair["resolution_status"] == "requires_alias_evidence"
