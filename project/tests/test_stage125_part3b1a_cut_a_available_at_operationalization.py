"""Tests for Stage125 Part 3B.1A CUT-A Available-at Operationalization Lock.

Synthetic / offline only. No network. No real row admission.
"""
from __future__ import annotations

import json
import socket
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from src import stage125_part3b0_evidence_readiness as p3b0  # noqa: E402
from src import stage125_part3b1a_cut_a_available_at_operationalization as m  # noqa: E402

OUTPUT_DIR = ROOT / "stage125"


def test_baseline_constant():
    assert m.EXPECTED_BASELINE_COMMIT == (
        "3a54a79c935f27e311679e8582e4c46330590a43"
    )


def test_baseline_ancestry():
    m.verify_baseline_commit(str(REPO_ROOT))


def test_publish_datetime_mapping_success_exact_letterserial():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw="1400/01/15 09:00:00",
        binding=m.synthetic_valid_binding(),
    )
    assert res.available_at is not None
    assert res.source_field == "PublishDateTime"
    assert res.cutoff_status == m.CUTOFF_STATUS_RESOLVED
    assert res.binding_ok is True


def test_sent_datetime_never_availability():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw="1400/01/15 09:00:00",
        binding=m.synthetic_valid_binding(),
        force_use_sent_as_availability=True,
    )
    assert res.available_at is None
    assert m.REASON_SENT_USED_AS_AVAILABILITY in res.reasons


def test_sent_equals_publish_still_uses_publish():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw="1400/01/15 10:30:00",
        binding=m.synthetic_valid_binding(),
    )
    assert res.sent_publish_relation == "equal"
    assert res.source_field == "PublishDateTime"
    assert res.available_at is not None


def test_sent_before_publish_cutoff_from_publish():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw="1400/01/14 18:00:00",
        binding=m.synthetic_valid_binding(),
    )
    assert res.sent_publish_relation == "sent_before_publish"
    assert res.source_field == "PublishDateTime"
    assert res.available_at is not None


def test_sent_after_publish_inconsistency_no_fallback():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw="1400/01/16 08:00:00",
        binding=m.synthetic_valid_binding(),
    )
    assert res.available_at is None
    assert res.cutoff_status == m.CUTOFF_STATUS_UNRESOLVED
    assert m.REASON_SENT_AFTER_PUBLISH in res.reasons
    assert res.source_field is None


def test_malformed_timestamp_null():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="bad///ts",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(),
    )
    assert res.available_at is None
    assert m.REASON_MALFORMED_PUBLISH in res.reasons


def test_missing_timestamp_null():
    res = m.resolve_operational_available_at(
        publish_datetime_raw=None,
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(),
    )
    assert res.available_at is None
    assert m.REASON_MISSING_PUBLISH in res.reasons


def test_persian_digit_normalization():
    fa = m.parse_codal_publish_datetime("۱۴۰۰/۰۱/۱۵ ۱۰:۳۰:۰۰")
    en = m.parse_codal_publish_datetime("1400/01/15 10:30:00")
    assert isinstance(fa, m.NormalizedTimestamp)
    assert isinstance(en, m.NormalizedTimestamp)
    assert fa.utc_iso8601 == en.utc_iso8601
    assert m.normalize_persian_digits("۱۴۰۰") == "1400"


def test_jalali_conversion():
    parsed = m.parse_codal_publish_datetime("1400/01/01 12:00:00")
    assert isinstance(parsed, m.NormalizedTimestamp)
    assert parsed.utc.year == 2021
    assert parsed.utc.month == 3
    assert parsed.utc.day == 21


def test_historical_asia_tehran_timezone_conversion():
    winter = m.parse_codal_publish_datetime("1400/01/01 12:00:00")
    summer = m.parse_codal_publish_datetime("1400/06/01 12:00:00")
    assert isinstance(winter, m.NormalizedTimestamp)
    assert isinstance(summer, m.NormalizedTimestamp)
    assert winter.local_tehran.utcoffset() != summer.local_tehran.utcoffset()
    # Must not use a single fixed +03:30 for all seasons.
    assert winter.utc_iso8601.endswith("Z")
    assert summer.utc_iso8601.endswith("Z")


def test_naive_datetime_rejected():
    assert m.reject_naive_datetime(datetime(2021, 3, 21, 12, 0, 0)) is False
    assert m.reject_naive_datetime(
        datetime(2021, 3, 21, 12, 0, 0, tzinfo=timezone.utc)
    ) is True


def test_historical_nonexistent_tehran_wall_time():
    """Known historical spring-forward gap → nonexistent_local_time (not ambiguous)."""
    jalali = m.jalali_string_from_tehran_gregorian_wall(2021, 3, 22, 0, 0, 0)
    parsed = m.parse_codal_publish_datetime(jalali)
    assert isinstance(parsed, m.TimestampParseFailure)
    assert parsed.reason == m.REASON_NONEXISTENT_LOCAL
    res = m.resolve_operational_available_at(
        publish_datetime_raw=jalali,
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(),
    )
    assert res.available_at is None
    assert m.REASON_NONEXISTENT_LOCAL in res.reasons


def test_historical_ambiguous_tehran_wall_time():
    """Known historical fall-back fold → ambiguous without deterministic rule."""
    jalali = m.jalali_string_from_tehran_gregorian_wall(2021, 9, 21, 23, 0, 0)
    parsed = m.parse_codal_publish_datetime(jalali)
    assert isinstance(parsed, m.TimestampParseFailure)
    assert parsed.reason == m.REASON_AMBIGUOUS_LOCAL
    res = m.resolve_operational_available_at(
        publish_datetime_raw=jalali,
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(),
    )
    assert res.available_at is None
    assert m.REASON_AMBIGUOUS_LOCAL in res.reasons


def test_normal_pre_transition_timestamp_resolves():
    jalali = m.jalali_string_from_tehran_gregorian_wall(2021, 3, 21, 23, 0, 0)
    parsed = m.parse_codal_publish_datetime(jalali)
    assert isinstance(parsed, m.NormalizedTimestamp)


def test_normal_post_transition_timestamp_resolves():
    jalali = m.jalali_string_from_tehran_gregorian_wall(2021, 3, 22, 1, 0, 0)
    parsed = m.parse_codal_publish_datetime(jalali)
    assert isinstance(parsed, m.NormalizedTimestamp)


def test_post_dst_abolition_ordinary_timestamp_no_fabricated_fold():
    """Current non-DST year must not receive a fabricated fold/gap."""
    jalali = m.jalali_string_from_tehran_gregorian_wall(2024, 3, 22, 0, 0, 0)
    parsed = m.parse_codal_publish_datetime(jalali)
    assert isinstance(parsed, m.NormalizedTimestamp)
    assert parsed.local_tehran.fold == 0
    tz = ZoneInfo(m.TEHRAN_TZ_NAME)
    kind, local = m.classify_tehran_wall_time(2024, 3, 22, 0, 0, 0, tz)
    assert kind == "valid"
    assert local is not None


def test_no_fixed_0330_assumption_across_seasons():
    winter = m.parse_codal_publish_datetime("1400/01/01 12:00:00")
    summer = m.parse_codal_publish_datetime("1400/06/01 12:00:00")
    assert isinstance(winter, m.NormalizedTimestamp)
    assert isinstance(summer, m.NormalizedTimestamp)
    assert winter.local_tehran.utcoffset() != summer.local_tehran.utcoffset()
    contract = m.build_operationalization_contract()
    assert "fixed_offset_plus_0330_for_all_years" in (
        contract["timezone_and_normalization"]["forbidden"]
    )


def test_subsidiary_title_rejected():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(subsidiary_only_title=True),
    )
    assert res.available_at is None
    assert "subsidiary_only_title" in res.reasons


def test_interim_statement_rejected():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(is_interim=True, is_annual=False),
    )
    assert res.available_at is None
    assert "interim_statement" in res.reasons


def test_unaudited_statement_rejected():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(is_audited=False),
    )
    assert res.available_at is None
    assert "unaudited_statement" in res.reasons


def test_fye_mismatch_rejected():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(fiscal_year_end_letter="1399/12/29"),
    )
    assert res.available_at is None
    assert "fiscal_year_end_mismatch" in res.reasons


def test_ticker_mismatch_rejected():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(letter_ticker="اپال"),
    )
    assert res.available_at is None
    assert "ticker_mismatch" in res.reasons


def test_entity_mismatch_rejected():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(legal_entity_letter="دیگر"),
    )
    assert res.available_at is None
    assert "entity_mismatch" in res.reasons


def test_consolidated_separate_mismatch_rejected():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(statement_scope_letter="consolidated"),
    )
    assert res.available_at is None
    assert "statement_scope_mismatch" in res.reasons


def test_multiple_letterserial_candidates_unresolved():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(
            candidate_letter_serials=["A", "B"],
        ),
    )
    assert res.available_at is None
    assert res.cutoff_status == m.CUTOFF_STATUS_UNRESOLVED
    assert "multiple_candidate_letters" in res.reasons


def test_incomplete_cache_without_canonical_letterserial_unresolved():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(
            incomplete_pagination=True,
            canonical_letter_serial=None,
            letter_serial=None,
            values_source_letter_serial=None,
        ),
    )
    assert res.available_at is None
    assert "incomplete_pagination_without_canonical_letter_serial" in res.reasons
    assert m.REASON_MISSING_CANONICAL_LETTER_SERIAL in res.reasons


def test_missing_canonical_letter_serial_unresolved():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(canonical_letter_serial=None),
    )
    assert res.available_at is None
    assert m.REASON_MISSING_CANONICAL_LETTER_SERIAL in res.reasons


def test_letter_serial_mismatch_unresolved():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(
            letter_serial="A1",
            canonical_letter_serial="B2",
            values_source_letter_serial="A1",
            candidate_letter_serials=["A1"],
        ),
    )
    assert res.available_at is None
    assert "letter_serial_mismatch" in res.reasons


def test_canonical_tracing_no_present_but_letter_tracing_missing():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(
            tracing_no=None,
            canonical_tracing_no="T-9",
        ),
    )
    assert res.available_at is None
    assert m.REASON_MISSING_REQUIRED_TRACING_NO in res.reasons


def test_tracing_no_mismatch_unresolved():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(
            tracing_no="T-1",
            canonical_tracing_no="T-9",
        ),
    )
    assert res.available_at is None
    assert "tracing_no_mismatch" in res.reasons


def test_revision_values_source_serial_differs_unresolved():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/02/01 11:00:00",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(
            revision_status="revision",
            revision_status_raw=m.CODAL_ESLAHIYE_RAW,
            letter_serial="REV9",
            canonical_letter_serial="REV9",
            candidate_letter_serials=["REV9"],
            values_source_letter_serial="ORIG1",
        ),
    )
    assert res.available_at is None
    assert m.REASON_VALUES_SOURCE_SERIAL_MISMATCH in res.reasons


def test_restatement_values_source_serial_differs_unresolved():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/02/01 11:00:00",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(
            revision_status="restatement",
            letter_serial="RST9",
            canonical_letter_serial="RST9",
            candidate_letter_serials=["RST9"],
            values_source_letter_serial="ORIG1",
        ),
    )
    assert res.available_at is None
    assert m.REASON_VALUES_SOURCE_SERIAL_MISMATCH in res.reasons


def test_exact_original_binding():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(revision_status="original"),
    )
    assert res.available_at is not None
    assert res.source_field == "PublishDateTime"


def test_exact_revision_binding():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/02/01 11:00:00",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(
            revision_status="revision",
            revision_status_raw=m.CODAL_ESLAHIYE_RAW,
            letter_serial="REV9",
            canonical_letter_serial="REV9",
            candidate_letter_serials=["REV9"],
            values_source_letter_serial="REV9",
        ),
    )
    assert res.available_at is not None
    assert res.source_field == "PublishDateTime"


def test_exact_restatement_binding():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/02/01 11:00:00",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(
            revision_status="restatement",
            letter_serial="RST9",
            canonical_letter_serial="RST9",
            candidate_letter_serials=["RST9"],
            values_source_letter_serial="RST9",
        ),
    )
    assert res.available_at is not None
    assert res.source_field == "PublishDateTime"


def test_boolean_flags_cannot_bypass_identifier_mismatch():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(
            letter_serial="A1",
            canonical_letter_serial="B2",
            values_source_letter_serial="A1",
            candidate_letter_serials=["A1"],
            canonical_source_version_bound=True,
            publish_of_original_used_for_correction_values=False,
        ),
    )
    assert res.available_at is None
    assert "letter_serial_mismatch" in res.reasons


def test_correction_is_not_normalized_revision_status():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(revision_status="correction"),
    )
    assert res.available_at is None
    assert "unknown_revision_status" in res.reasons
    assert m.NORMALIZED_REVISION_STATUS == {"original", "revision", "restatement"}
    assert "correction" not in m.NORMALIZED_REVISION_STATUS


def test_codal_eslahiye_explicit_map_to_revision_only():
    assert m.explicit_normalized_revision_for_codal_eslahiye(
        revision_status_raw=m.CODAL_ESLAHIYE_RAW,
        map_eslahiye_to_revision=True,
    ) == "revision"
    assert m.explicit_normalized_revision_for_codal_eslahiye(
        revision_status_raw=m.CODAL_ESLAHIYE_RAW,
        map_eslahiye_to_revision=False,
    ) is None
    # Never silently map اصلاحیه to restatement.
    assert m.explicit_normalized_revision_for_codal_eslahiye(
        revision_status_raw=m.CODAL_ESLAHIYE_RAW,
        map_eslahiye_to_revision=True,
    ) != "restatement"


def test_unknown_revision_status_unresolved():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(revision_status="unknown"),
    )
    assert res.available_at is None
    assert "unknown_revision_status" in res.reasons


def test_null_revision_status_unresolved():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(revision_status=None),
    )
    assert res.available_at is None
    assert "unknown_revision_status" in res.reasons


def test_redundant_audit_flag_still_fail_closed():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/01 10:00:00",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(
            revision_status="revision",
            revision_status_raw=m.CODAL_ESLAHIYE_RAW,
            letter_serial="REV9",
            canonical_letter_serial="REV9",
            candidate_letter_serials=["REV9"],
            values_source_letter_serial="REV9",
            publish_of_original_used_for_correction_values=True,
        ),
    )
    assert res.available_at is None
    assert m.REASON_CORRECTION_USES_ORIGINAL in res.reasons


def test_multi_document_row_unresolved():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(multi_document_predictor_row=True),
    )
    assert res.available_at is None
    assert m.REASON_MULTI_DOCUMENT in res.reasons


def test_no_actual_pilot_row_assignment():
    res = m.resolve_operational_available_at(
        publish_datetime_raw="1400/01/15 10:30:00",
        sent_datetime_raw=None,
        binding=m.synthetic_valid_binding(),
    )
    assert res.real_pilot_row_assigned is False
    lock = m.build_decision_lock_record(m.build_operationalization_contract())
    assert lock["real_pilot_rows_assigned"] == 0
    assert lock["resolved_pilot_cutoffs"] == 0


def test_no_network():
    with p3b0.network_sentinel() as sentinel:
        m.run(project_dir=ROOT, write=False)
        assert sentinel.calls_attempted == 0
    # Direct socket should still be blocked inside sentinel.
    with p3b0.network_sentinel():
        with pytest.raises(Exception):
            socket.create_connection(("codal.ir", 443), timeout=0.2)


def test_no_scoring_and_no_stage126_modeling():
    contract = m.build_operationalization_contract()
    lock = m.build_decision_lock_record(contract)
    assert lock["accessibility_scoring_applied"] is False
    assert lock["modeling_started"] is False
    assert lock["stage126_started"] is False
    assert lock["part3b2_started"] is False
    assert "accessibility_scoring" in contract["implementation_scope"]["forbidden"]
    assert "stage126" in contract["implementation_scope"]["forbidden"]
    assert "modeling" in contract["implementation_scope"]["forbidden"]
    for rel in m.FORBIDDEN_SURFACE_EXACT:
        assert not (REPO_ROOT / rel).exists()


def test_frozen_stage122_to_stage125_scientific_artifacts_unchanged():
    before = {
        rel: m.sha256_file(REPO_ROOT / rel) for rel in m.FROZEN_SCIENTIFIC_PATHS
    }
    m.run(project_dir=ROOT, write=False)
    after = {
        rel: m.sha256_file(REPO_ROOT / rel) for rel in m.FROZEN_SCIENTIFIC_PATHS
    }
    assert before == after
    assert all(v is not None for v in after.values())


def test_research_pointers_unchanged():
    lock = m.build_decision_lock_record(m.build_operationalization_contract())
    assert lock["research_pointers_unchanged"] == {
        "last_completed_research_action_id": "stage125-part3a-decision-lock",
        "next_research_action_id": "stage125-part3b-evidence-capture",
    }
    # Later ROADMAP advancement (conservative lag) is expected and must not
    # rewrite the Part 3B.1A lock-embedded historical pointers above.
    roadmap = (REPO_ROOT / "project/docs/ai/ROADMAP.md").read_text(encoding="utf-8")
    assert "stage125-part3a-decision-lock" in roadmap
    assert (
        "last_completed_research_action_id: "
        "stage125-part3c-leakage-safe-dataset-finalization"
    ) in roadmap
    assert (
        "next_research_action_id: "
        "stage125-part4-statistical-analysis-plan"
    ) in roadmap


def test_contract_and_lock_markers():
    contract = m.build_operationalization_contract()
    lock = m.build_decision_lock_record(contract)
    assert contract["operational_available_at"]["source_field"] == "PublishDateTime"
    assert contract["operational_available_at"]["sent_datetime_policy"][
        "sent_datetime_is_available_at"
    ] is False
    assert lock["cut_a_available_at_operationalization_locked"] is True
    assert lock["part3b1_decision_locked"] is True
    assert lock["part3b_started"] is True
    assert lock["part3b_completed"] is False
    assert lock["predictor_available_at_evidence_collected"] is False
    assert lock["pilot_cutoff_provenance_resolved"] is False
    assert set(contract["source_version_and_revision_policy"][
        "normalized_revision_status_enum"
    ]) == m.NORMALIZED_REVISION_STATUS
    assert "correction" not in contract["source_version_and_revision_policy"][
        "normalized_revision_status_enum"
    ]


def test_canonical_jdatetime_runtime():
    assert version("jdatetime") == "6.0.1"


def test_run_check_and_qc_assertions():
    result = m.run(project_dir=ROOT, write=True)
    qc = result["qc"]
    assert qc["all_pass"] is True
    assert qc["failed_count"] == 0
    assert qc["decision_lock_only"] is True
    assert qc["synthetic_validation_only"] is True
    assert qc["zero_network_calls"] is True
    assert qc["zero_real_available_at_assignments"] is True
    assert qc["zero_resolved_pilot_cutoffs"] is True
    assert qc["zero_candidate_values"] is True
    assert qc["zero_pair_values"] is True
    assert qc["zero_accessibility_scores"] is True
    assert qc["zero_gate_admissions"] is True
    assert qc["no_part3b_completion"] is True
    assert qc["no_modeling"] is True
    assert qc["cut_a_available_at_operationalization_locked"] is True
    assert qc["part3b1_decision_locked"] is True
    assert qc["stage"] == m.QC_STAGE
    assertion_names = {a["assertion"] for a in qc["assertions"]}
    for required in (
        "normalized_revision_enum_matches_frozen_provenance_schema",
        "correction_not_emitted_as_normalized_revision_status",
        "exact_values_source_serial_binding",
        "missing_canonical_serial_rejected",
        "missing_required_tracing_no_rejected",
        "synth_historical_nonexistent_tehran_time",
        "synth_historical_ambiguous_tehran_time",
        "canonical_jdatetime_runtime_pin",
    ):
        assert required in assertion_names
        assert next(
            a for a in qc["assertions"] if a["assertion"] == required
        )["status"] == "PASS"
    # Idempotent check
    result2 = m.run(project_dir=ROOT, write=False)
    assert result2["drift"] == []
    assert (OUTPUT_DIR / m.F_QC).is_file()
    assert (OUTPUT_DIR / m.F_METADATA).is_file()
    on_disk = json.loads((OUTPUT_DIR / m.F_LOCK).read_text(encoding="utf-8"))
    assert on_disk["cut_a_available_at_operationalization_locked"] is True


def test_raw_timestamp_preserved():
    raw = "۱۴۰۰/۰۱/۱۵ ۱۰:۳۰:۰۰"
    res = m.resolve_operational_available_at(
        publish_datetime_raw=raw,
        sent_datetime_raw="1400/01/15 09:00:00",
        binding=m.synthetic_valid_binding(),
    )
    assert res.available_at_raw_publish == raw
    assert res.sent_datetime_raw == "1400/01/15 09:00:00"
