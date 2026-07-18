"""Tests for Stage125 Part 3B.1E Conservative Six-Month Lag Decision Lock."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import jdatetime
import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from src import stage125_part3b0_evidence_readiness as p3b0  # noqa: E402
from src import stage125_part3b1e_conservative_lag_decision as m  # noqa: E402


def test_lag_shorter_than_six_months_rejected():
    with pytest.raises(m.AuthorizationError, match="shorter"):
        m.require_approved_lag_months(5)
    with pytest.raises(m.AuthorizationError, match="shorter"):
        m.compute_assumed_available_at_conservative(
            jdatetime.date(1401, 12, 29), lag_months=3,
        )


def test_lag_longer_or_different_from_six_rejected():
    with pytest.raises(m.AuthorizationError, match="longer"):
        m.require_approved_lag_months(7)
    with pytest.raises(m.AuthorizationError, match="longer"):
        m.require_approved_lag_months(12)
    with pytest.raises(m.AuthorizationError):
        m.require_approved_lag_months(True)  # type: ignore[arg-type]


def test_assumed_date_cannot_populate_observed_available_at():
    sample = m.compute_assumed_available_at_conservative(
        jdatetime.date(1401, 12, 29)
    )
    with pytest.raises(m.AuthorizationError, match="observed field"):
        m.reject_assumed_date_as_observed_field(
            "available_at",
            sample["assumed_available_at_conservative_jalali"],
        )
    with pytest.raises(m.AuthorizationError, match="observed field"):
        m.reject_assumed_date_as_observed_field(
            "observed_available_at",
            sample["assumed_available_at_conservative_gregorian"],
        )


def test_assumed_date_cannot_be_called_PublishDateTime():
    sample = m.compute_assumed_available_at_conservative(
        jdatetime.date(1400, 12, 29)
    )
    assert sample["is_PublishDateTime"] is False
    with pytest.raises(m.AuthorizationError, match="PublishDateTime"):
        m.reject_assumed_date_as_observed_field(
            "PublishDateTime",
            sample["assumed_available_at_conservative_jalali"],
        )


def test_same_year_t_target_alignment_rejected():
    with pytest.raises(m.AuthorizationError, match="same-year"):
        m.validate_predictor_target_alignment(1399, 1399)


def test_t_to_t_plus_1_alignment_accepted():
    m.validate_predictor_target_alignment(1399, 1400)
    m.validate_predictor_target_alignment(1401, 1402)


def test_financial_value_mutation_rejected(tmp_path):
    before = m.frozen_canonical_hashes(REPO_ROOT)
    after = dict(before)
    key = m.FINANCIAL_VALUE_PATHS[0]
    after[key] = "0" * 64
    with pytest.raises(m.AuthorizationError, match="financial-value mutation"):
        m.reject_financial_value_mutation(
            REPO_ROOT, before=before, after=after,
        )


def test_target_mutation_rejected():
    before = m.frozen_canonical_hashes(REPO_ROOT)
    after = dict(before)
    key = m.TARGET_PATHS[0]
    after[key] = "f" * 64
    with pytest.raises(m.AuthorizationError, match="target mutation"):
        m.reject_target_mutation(REPO_ROOT, before=before, after=after)


def test_codal_capture_authorization_rejected():
    lock = m.build_decision_lock(m.FROZEN_CANONICAL_INPUTS)
    lock["broad_codal_capture_authorized"] = True
    with pytest.raises(m.AuthorizationError, match="CODAL capture"):
        m.assert_authorization_policy(lock)


def test_80_row_scale_up_rejected():
    lock = m.build_decision_lock(m.FROZEN_CANONICAL_INPUTS)
    lock["scale_up_to_80_rows_authorized"] = True
    with pytest.raises(m.AuthorizationError, match="80-row"):
        m.assert_authorization_policy(lock)


def test_stage126_and_modeling_authorization_rejected():
    lock = m.build_decision_lock(m.FROZEN_CANONICAL_INPUTS)
    bad_stage = dict(lock)
    bad_stage["stage126_authorized"] = True
    with pytest.raises(m.AuthorizationError, match="Stage126"):
        m.assert_authorization_policy(bad_stage)
    bad_model = dict(lock)
    bad_model["modeling_authorized"] = True
    with pytest.raises(m.AuthorizationError, match="modeling"):
        m.assert_authorization_policy(bad_model)


def test_six_month_formula_jalali():
    out = m.compute_assumed_available_at_conservative(
        jdatetime.date(1401, 12, 29)
    )
    assert out["field_name"] == m.ASSUMED_FIELD_NAME
    assert out["assumed_available_at_conservative_jalali"] == "1402-06-29"
    assert out["availability_method"] == m.AVAILABILITY_METHOD
    assert out["is_observed_publication_timestamp"] is False


def test_canonical_input_hashes_match_pinned():
    pinned = m.frozen_canonical_hashes(REPO_ROOT)
    assert pinned == m.FROZEN_CANONICAL_INPUTS


def test_network_sentinel_records_zero_requests():
    # Requires source/test/runner already committed for full run();
    # exercise pure builders under the sentinel when source_commit missing.
    with p3b0.network_sentinel() as sentinel:
        content, extras = m.build_all_content(REPO_ROOT)
        assert content
        assert extras["lock"]["conservative_lag_months"] == 6
        assert sentinel.calls_attempted == 0


def test_decision_lock_principles_exact():
    lock = m.build_decision_lock(m.FROZEN_CANONICAL_INPUTS)
    assert lock["financial_data_status"] == "researcher_verified_frozen"
    assert lock["financial_value_reextraction_required"] is False
    assert lock["broad_codal_capture_authorized"] is False
    assert lock["row_level_publish_datetime_collection_authorized"] is False
    assert lock["row_level_real_available_at_assignment_authorized"] is False
    assert lock["availability_method"] == "fixed_conservative_lag"
    assert lock["conservative_lag_months"] == 6
    assert lock["availability_date_semantics"] == (
        "assumed_methodological_date_not_observed_publication_timestamp"
    )
    assert lock["stage126_authorized"] is False
    assert lock["modeling_authorized"] is False
    assert lock["research_pointers"]["last_completed_research_action_id"] == (
        m.RESEARCH_LAST_COMPLETED
    )
    assert lock["research_pointers"]["next_research_action_id"] == (
        m.RESEARCH_NEXT
    )


def test_readme_scientific_interpretation():
    text = m.build_readme()
    assert "manually extracted and verified by the researcher" in text
    assert "prevent temporal leakage" in text
    assert "PR #47 was closed unmerged" in text
    assert "No 80-row or 130-company" in text


def test_run_write_check_offline(tmp_path):
    """Full run requires committed source; skip write to canonical if uncommitted."""
    src_commit = m._git(
        str(REPO_ROOT), "log", "--format=%H", "-n", "1",
        "--", m.SRC_REL, m.TEST_REL, m.RUN_REL,
    )
    if not src_commit:
        pytest.skip("source/test/runner not yet committed")
    with p3b0.network_sentinel() as sentinel:
        result = m.run(
            project_dir=ROOT,
            output_dir=tmp_path,
            write=True,
        )
        assert sentinel.calls_attempted == 0
    assert result["network_requests_attempted"] == 0
    assert result["qc"]["all_pass"] is True
    assert (tmp_path / m.F_LOCK).is_file()
    assert (tmp_path / m.F_MANIFEST).is_file()
    assert (tmp_path / m.F_QC).is_file()
    lock = json.loads((tmp_path / m.F_LOCK).read_text(encoding="utf-8"))
    assert lock["conservative_lag_months"] == 6
    # Failures list must be empty.
    failed = [
        a for a in result["qc"]["assertions"] if a["status"] != "PASS"
    ]
    assert failed == []
