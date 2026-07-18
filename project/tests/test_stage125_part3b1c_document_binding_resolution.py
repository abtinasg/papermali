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
    evidence = {r["predictor_row_key_t"]: r for r in m.load_evidence_rows(REPO_ROOT)}
    entity_rows = [r for r in tax if r["failure_reason"] == "entity_mismatch"]
    assert entity_rows
    thanusa = next(r for r in entity_rows if r["predictor_row_key_t"] == "ثنوسا|1392")
    assert thanusa["observed_source_value"] == "نوسازي و ساختمان تهران"
    assert thanusa["observed_canonical_value"] == "نوسازی و ساختمان تهران"
    for er in entity_rows:
        row = evidence[er["predictor_row_key_t"]]
        assert er["observed_source_value"] == (row.get("source_legal_entity") or "")
        assert er["observed_canonical_value"] == (row.get("canonical_legal_entity") or "")


def test_thanusa_ticker_mismatch_source_not_backfilled():
    tax = list(csv.DictReader(
        (REPO_ROOT / "project/stage125" / m.F_TAXONOMY).open(encoding="utf-8")
    ))
    row = next(
        r for r in tax
        if r["predictor_row_key_t"] == "ثنوسا|1392"
        and r["failure_reason"] == "ticker_mismatch"
    )
    assert row["observed_source_value"] == ""
    assert row["observed_canonical_value"] == "ثنوسا"
    assert row["normalization_safe"] == "false"
    assert row["normalization_rule_id"] == ""
    assert row["failure_layer"] == "ticker"
    assert row["failure_class"] == "missing_source_evidence"
    assert row["resolution_status"] == "requires_official_symbol_metadata"
    assert "must not be copied" in row["notes"]


def test_missing_official_title_side_classification():
    tax = list(csv.DictReader(
        (REPO_ROOT / "project/stage125" / m.F_TAXONOMY).open(encoding="utf-8")
    ))
    evidence = {r["predictor_row_key_t"]: r for r in m.load_evidence_rows(REPO_ROOT)}
    title_rows = [r for r in tax if r["failure_reason"] == "missing_official_title"]
    assert title_rows
    for tr in title_rows:
        er = evidence[tr["predictor_row_key_t"]]
        assert tr["observed_source_value"] == (er.get("source_official_title") or "")
        assert tr["observed_canonical_value"] == (er.get("canonical_official_title") or "")
        assert tr["observed_source_value"]
        assert tr["observed_canonical_value"] == ""
        assert tr["failure_layer"] == "canonical_metadata"
        assert tr["failure_class"] == "missing_canonical_evidence"


def test_letter_code_not_substituted_with_letter_serial():
    tax = list(csv.DictReader(
        (REPO_ROOT / "project/stage125" / m.F_TAXONOMY).open(encoding="utf-8")
    ))
    evidence = {r["predictor_row_key_t"]: r for r in m.load_evidence_rows(REPO_ROOT)}
    letter_rows = [r for r in tax if r["failure_reason"] == "letter_code_mismatch"]
    assert letter_rows
    for lr in letter_rows:
        er = evidence[lr["predictor_row_key_t"]]
        serials = {
            (er.get("source_letter_serial") or "").strip(),
            (er.get("canonical_letter_serial") or "").strip(),
        }
        serials.discard("")
        assert lr["observed_source_value"] == ""
        assert lr["observed_canonical_value"] == ""
        assert lr["observed_source_value"] not in serials
        assert lr["observed_canonical_value"] not in serials
        assert lr["resolution_status"] == (
            "letter_code_values_not_preserved_in_frozen_evidence"
        )
        assert "LetterSerial must not be substituted" in lr["notes"]


def test_statement_scope_values_preserved():
    tax = list(csv.DictReader(
        (REPO_ROOT / "project/stage125" / m.F_TAXONOMY).open(encoding="utf-8")
    ))
    evidence = {r["predictor_row_key_t"]: r for r in m.load_evidence_rows(REPO_ROOT)}
    scope_rows = [
        r for r in tax
        if r["failure_reason"] in (
            "statement_scope_mismatch", "separate_scope_required_but_not_met",
        )
    ]
    assert scope_rows
    for sr in scope_rows:
        er = evidence[sr["predictor_row_key_t"]]
        assert sr["observed_source_value"] == (er.get("source_statement_scope") or "")
        assert sr["observed_canonical_value"] == (
            er.get("canonical_statement_scope") or ""
        )


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
    with pytest.raises(m.QCFail, match="wildcard"):
        m.build_proposed_capture(bad)


def test_wildcard_host_fails():
    proposed = json.loads(
        (REPO_ROOT / "project/stage125" / m.F_PROPOSED).read_text(encoding="utf-8")
    )
    assert proposed["wildcard_host_forbidden"] is True
    assert proposed["wildcard_url_forbidden"] is True
    with pytest.raises(m.QCFail, match="hosts_exact|wildcard"):
        m.validate_proposed_request_url(
            "https://*.codal.ir/Reports/Decision.aspx?LetterSerial=abc",
            "abc",
            request_status="proposed_not_authorized",
        )


def _tracked_serial_for(key: str) -> str:
    row = next(
        r for r in m.load_evidence_rows(REPO_ROOT)
        if r["predictor_row_key_t"] == key
    )
    return row["source_letter_serial"]


@pytest.mark.parametrize("bad_url,match", [
    (
        "http://www.codal.ir/Reports/Decision.aspx?LetterSerial=SERIAL",
        "https",
    ),
    (
        "https://codal.ir/Reports/Decision.aspx?LetterSerial=SERIAL",
        "hosts_exact",
    ),
    (
        "https://www.codal.ir:444/Reports/Decision.aspx?LetterSerial=SERIAL",
        "port",
    ),
    (
        "https://www.codal.ir/Reports/Other.aspx?LetterSerial=SERIAL",
        "paths_exact",
    ),
    (
        "https://www.codal.ir/Reports/Decision.aspx",
        "LetterSerial count",
    ),
    (
        "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=SERIAL&LetterSerial=OTHER",
        "LetterSerial count",
    ),
    (
        "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=WRONG",
        "all_url_letter_serials_match",
    ),
    (
        "https://www.codal.ir/*/Decision.aspx?LetterSerial=SERIAL",
        "wildcard",
    ),
    (
        "https://user:pass@www.codal.ir/Reports/Decision.aspx?LetterSerial=SERIAL",
        "credentials",
    ),
    (
        "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=SERIAL#frag",
        "fragment",
    ),
])
def test_url_mutation_fails_closed(bad_url, match):
    serial = _tracked_serial_for("ثنوسا|1392")
    url = bad_url.replace("SERIAL", serial).replace("WRONG", serial + "x")
    with pytest.raises(m.QCFail, match=match):
        m.validate_proposed_request_url(
            url, serial, request_status="proposed_not_authorized",
        )


def test_current_five_tracked_urls_pass_exact_validation():
    proposed = json.loads(
        (REPO_ROOT / "project/stage125" / m.F_PROPOSED).read_text(encoding="utf-8")
    )
    assert len(proposed["proposed_requests"]) == 5
    for req in proposed["proposed_requests"]:
        m.validate_proposed_request_url(
            req["exact_url"],
            req["candidate_letter_serial"],
            request_status=req["request_status"],
        )
        if req["predictor_row_key_t"] == "اردستان|1401":
            assert req["request_status"] == "not_proposed_structurally_rejected"
            assert req["request_necessity"] == "none_structural_rejection"
            assert req["exact_url"]


def test_unresolved_endpoint_stays_null_when_url_absent():
    evidence = m.load_evidence_rows(REPO_ROOT)
    cleared = [dict(r) for r in evidence]
    for r in cleared:
        r["source_url"] = ""
    prop = m.build_proposed_capture(cleared)
    for req in prop["proposed_requests"]:
        if req["request_status"] == "endpoint_unresolved_not_authorizable":
            assert req["exact_url"] is None
            m.validate_proposed_request_url(
                None, req.get("candidate_letter_serial"),
                request_status=req["request_status"],
            )


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
    """Isolated detached worktree: official --check with zero writes/network."""
    wt = tmp_path / "fresh_wt"
    subprocess.run(
        ["git", "-C", str(REPO_ROOT), "worktree", "add", "--detach", str(wt), "HEAD"],
        check=True, capture_output=True, text=True,
    )
    try:
        # Optional gitignored Part 3B.1B raw cache must be absent in the worktree.
        raw_cache_candidates = [
            wt / "project/stage125/raw_cache",
            wt / "project/stage125/.cache",
            wt / "project/stage125/part3b1b_thanusa_decision_raw.html",
        ]
        for cand in raw_cache_candidates:
            assert not cand.exists()

        part3b1c_rels = sorted(
            rel for rel in m.PART3B1C_AUTHORIZED_EXACT
            if rel.startswith("project/stage125/")
        )
        before_bytes = {
            rel: (wt / rel).read_bytes()
            for rel in part3b1c_rels
            if (wt / rel).is_file()
        }
        before_mtime = {
            rel: (wt / rel).stat().st_mtime_ns
            for rel in before_bytes
        }
        env = dict(**{k: v for k, v in __import__("os").environ.items()})
        env["PYTHONPATH"] = str(wt / "project")
        proc = subprocess.run(
            [sys.executable, str(wt / m.RUN_REL), "--check"],
            cwd=str(wt),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr
        assert "Deliverables up to date" in proc.stdout
        assert "network_requests_attempted=0" in proc.stdout
        for rel, expected in before_bytes.items():
            actual = (wt / rel).read_bytes()
            assert actual == expected
            assert actual == (REPO_ROOT / rel).read_bytes()
            assert (wt / rel).stat().st_mtime_ns == before_mtime[rel]
    finally:
        subprocess.run(
            ["git", "-C", str(REPO_ROOT), "worktree", "remove", "--force", str(wt)],
            check=False, capture_output=True, text=True,
        )


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
