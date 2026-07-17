"""Tests for Stage125 Part 3B.1 Decision Lock (synthetic / offline only)."""
from __future__ import annotations

import csv
import io
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from src import stage125_part3b1_decision_lock as part3b1  # noqa: E402

OUTPUT_DIR = ROOT / "stage125"


def test_baseline_constant():
    assert part3b1.EXPECTED_BASELINE_COMMIT == (
        "274ff216f0f3a59ae611c68b662382d75ad84c8b"
    )


def test_baseline_ancestry():
    part3b1.verify_baseline_commit(str(REPO_ROOT))


def test_m2_contract_locked():
    m2 = part3b1.build_m2_formula_contract()
    assert m2["option_id"] == "M2-A_modified"
    assert m2["imputation_allowed"] is False
    assert m2["shared_window"]["length"] == "12_calendar_months"
    assert m2["price_field"]["name"] == "adjusted_close"
    assert m2["real_extraction_authorized"] is False


def test_m3_cbi_fail_closed():
    m3 = part3b1.build_m3_cbi_policy_contract()
    assert m3["option_id"] == "M3-C"
    assert m3["paired_option_id"] == "CBI-A"
    assert m3["authoritative_cbi_endpoint_frozen"] is False
    assert "free_market_fx" in m3["substitutions_forbidden"]
    assert "sci_for_cbi_fx" in m3["substitutions_forbidden"]


def test_m4_ambiguity_null():
    m4 = part3b1.build_m4_definition_contract()
    assert m4["option_id"] == "M4-A"
    assert m4["ambiguity_or_missing_equals_null"] is True
    assert m4["nlp_or_persian_text_modeling_forbidden"] is True


def test_rubric_r_a_candidate_level():
    r = part3b1.build_rubric_operational_mapping()
    assert r["option_id"] == "R-A"
    assert r["score_level"] == "candidate_source_accessibility"
    assert r["pair_coverage_evaluated_by"] == ["G09", "G10", "G11", "G12"]
    assert r["missing_evidence_rule"] == "null_or_unresolved_never_zero"
    assert r["real_scoring_authorized"] is False


def test_cutoff_cut_a_retains_part2():
    c = part3b1.build_cutoff_contract(REPO_ROOT)
    assert c["option_id"] == "CUT-A"
    assert c["pair_cutoff"]["cutoff_basis"] == "verified_available_at_timestamp"
    assert "fiscal_year_end_alone" in c["pair_cutoff"]["cutoff_not_based_on"]


def test_synth_m2_formulas_no_imputation():
    days = [
        date(2020, 1, 2) + timedelta(days=i)
        for i in range(0, 400)
        if (date(2020, 1, 2) + timedelta(days=i)).weekday() < 5
    ]
    cutoff = date(2020, 12, 15)
    prices = {d: 100.0 + (i % 11) for i, d in enumerate(days)}
    values = {d: 1_000_000.0 for d in days}
    values[days[20]] = 0.0
    w = part3b1.window_trading_days(days, cutoff)
    assert w is not None
    assert w[-1] <= cutoff
    assert part3b1.cumulative_simple_return(prices, w) is not None
    assert part3b1.sample_stdev(part3b1.daily_returns(prices, w)) is not None
    am = part3b1.amihud_mean(prices, values, w)
    assert am is not None and am > 0


def test_synth_m2_null_when_endpoint_price_missing():
    days = [date(2020, 1, 3), date(2020, 1, 6), date(2020, 1, 7)]
    prices = {date(2020, 1, 6): 10.0}  # missing endpoints
    assert part3b1.cumulative_simple_return(prices, days) is None


def test_synth_m4_null_rules():
    assert part3b1.audit_lag_days(None, "2020-06-01") is None
    assert part3b1.going_concern_flag(None) is None
    assert part3b1.going_concern_flag("ambiguous") is None
    assert part3b1.going_concern_flag("present") is True


def test_synth_cutoff_gate():
    assert part3b1.feature_usable("2020-01-01T00:00:00Z", "2020-02-01T00:00:00Z")
    assert not part3b1.feature_usable("2020-03-01T00:00:00Z", "2020-02-01T00:00:00Z")
    assert not part3b1.feature_usable(None, "2020-02-01T00:00:00Z")


def test_build_all_contains_required_files():
    content = part3b1.build_all(REPO_ROOT)
    for name in part3b1.CONTENT_FILES:
        assert name in content
        assert content[name]


def test_selected_answers_in_requirements():
    content = part3b1.build_all(REPO_ROOT)
    req = json.loads(content[part3b1.F_REQ])
    answers = {d["decision_id"]: d["selected_answer"]
               for d in req["user_decisions_still_needed"]}
    assert answers["m2_feature_definitions"] == "M2-A_modified"
    assert answers["m3_feature_definitions"] == "M3-C"
    assert answers["m4_feature_definitions"] == "M4-A"
    assert answers["rubric_score_mapping_0_5"] == "R-A"
    assert answers["cbi_endpoint_provenance"] == "CBI-A"
    assert answers["available_at_and_cutoff_rules"] == "CUT-A"


def test_qc_all_pass_offline():
    content = part3b1.build_all(REPO_ROOT)
    hashes = {
        k: part3b1.sha256_bytes(v.encode("utf-8")) for k, v in content.items()
    }
    frozen = part3b1.frozen_input_hashes(REPO_ROOT)
    qc = part3b1.build_qc_report(REPO_ROOT, content, hashes, frozen)
    assert qc["all_pass"] is True
    assert qc["failed_count"] == 0
    assert qc["part3b1_decision_locked"] is True
    assert qc["part3b_completed"] is False
    assert qc["modeling_started"] is False
    assert qc["accessibility_scoring_applied"] is False
    assert qc["network_extraction_performed"] is True
    assert qc["part3b1_network_calls_attempted"] == 0


def test_decisions_csv_header():
    rows = part3b1.build_selected_decision_rows()
    text = part3b1._csv_str(part3b1._DECISIONS_HEADER, rows)
    parsed = list(csv.DictReader(io.StringIO(text)))
    assert len(parsed) == 6
    assert {r["decision_id"] for r in parsed} == {
        "m2_feature_definitions",
        "m3_feature_definitions",
        "m4_feature_definitions",
        "rubric_score_mapping_0_5",
        "cbi_endpoint_provenance",
        "available_at_and_cutoff_rules",
    }


@pytest.mark.skipif(
    not (OUTPUT_DIR / part3b1.F_DECISION).is_file(),
    reason="deliverables not written yet",
)
def test_on_disk_lock_markers():
    lock = json.loads((OUTPUT_DIR / part3b1.F_DECISION).read_text(encoding="utf-8"))
    assert lock["part3b1_decision_locked"] is True
    assert lock["part3b_completed"] is False
    assert lock["modeling_started"] is False
