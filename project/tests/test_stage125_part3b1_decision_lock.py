"""Tests for Stage125 Part 3B.1 Decision Lock (synthetic / offline only)."""
from __future__ import annotations

import csv
import io
import json
import shutil
import socket
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

from src import stage125_part3b0_evidence_readiness as p3b0  # noqa: E402
from src import stage125_part3b_evidence_capture as part3b  # noqa: E402
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
    assert m2["threshold_reduction_allowed"] is False
    assert m2["minimum_valid_daily_return_observations"] == 126
    assert m2["minimum_valid_amihud_observations"] == 126
    assert m2["shared_window"]["length"] == "12_calendar_months"
    assert m2["shared_window"]["applies_to_all_m2_variables"] is True
    assert m2["shared_window"]["end_rule"] == (
        "last_trading_day_with_verified_available_at_strictly_before_pair_cutoff"
    )
    assert m2["shared_window"]["market_observation_end_predicate"] == (
        "market_observation_date < pair_cutoff_date"
    )
    assert m2["leakage_rules"]["window_must_end_strictly_before_pair_cutoff"] is True
    assert "window_must_end_on_or_before_pair_cutoff" not in m2["leakage_rules"]
    assert m2["price_field"]["name"] == "adjusted_close"
    assert m2["real_extraction_authorized"] is False
    assert "126" in m2["variables"]["realized_volatility"]["formula"]
    assert "126" in m2["variables"]["equity_return_window"]["formula"]
    assert "126" in m2["variables"]["amihud_illiquidity"]["formula"]


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
    assert "false only when an explicit structured official field" in (
        m4["variables"]["going_concern_flag"]["definition"]
    )
    assert "negative lag" in m4["variables"]["audit_lag_days"]["definition"]


def test_rubric_r_a_candidate_level():
    r = part3b1.build_rubric_operational_mapping()
    assert r["option_id"] == "R-A"
    assert r["score_level"] == "candidate_source_accessibility"
    assert r["pair_coverage_evaluated_by"] == ["G09", "G10", "G11", "G12"]
    assert r["missing_evidence_rule"] == "null_or_unresolved_never_zero"
    assert r["real_scoring_authorized"] is False


def test_cutoff_cut_a_retains_part2_and_keeps_feature_le():
    c = part3b1.build_cutoff_contract(REPO_ROOT)
    assert c["option_id"] == "CUT-A"
    assert c["pair_cutoff"]["cutoff_basis"] == "verified_available_at_timestamp"
    assert "fiscal_year_end_alone" in c["pair_cutoff"]["cutoff_not_based_on"]
    assert "available_at <= pair_cutoff" in c["feature_availability"]["rule"]
    assert "strictly_before" in c["block_rules"]["M2"]


def _weekday_span(start: date, n_days: int) -> list[date]:
    out: list[date] = []
    d = start
    while len(out) < n_days:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


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
    assert w[-1] < cutoff
    assert part3b1.cumulative_simple_return(prices, w) is not None
    assert part3b1.sample_stdev(part3b1.daily_returns(prices, w)) is not None
    am = part3b1.amihud_mean(prices, values, w)
    assert am is not None and am > 0
    diag = part3b1.m2_window_diagnostics(prices, values, w)
    assert diag["zero_traded_value_day_count"] >= 1
    assert diag["usable_daily_return_count"] >= 126


def test_m2_boundary_125_fail_126_pass_returns():
    days = _weekday_span(date(2020, 1, 2), 130)
    prices = {d: 100.0 + i for i, d in enumerate(days)}
    # 126 consecutive priced days => 125 returns
    w125 = days[:126]
    assert len(part3b1.daily_returns(prices, w125)) == 125
    assert part3b1.sample_stdev(part3b1.daily_returns(prices, w125)) is None
    assert part3b1.cumulative_simple_return(prices, w125) is None
    # 127 priced days => 126 returns
    w126 = days[:127]
    assert len(part3b1.daily_returns(prices, w126)) == 126
    assert part3b1.sample_stdev(part3b1.daily_returns(prices, w126)) is not None
    assert part3b1.cumulative_simple_return(prices, w126) is not None


def test_m2_boundary_125_fail_126_pass_amihud():
    days = _weekday_span(date(2020, 1, 2), 130)
    prices = {d: 100.0 + i for i, d in enumerate(days)}
    values = {d: 1_000_000.0 for d in days}
    w125 = days[:126]
    assert part3b1.amihud_mean(prices, values, w125) is None
    w126 = days[:127]
    assert part3b1.amihud_mean(prices, values, w126) is not None


def test_m2_missing_endpoint_null():
    days = _weekday_span(date(2020, 1, 2), 130)
    prices = {d: 100.0 + i for i, d in enumerate(days)}
    w = days[:127]
    prices_missing = dict(prices)
    del prices_missing[w[0]]
    assert part3b1.cumulative_simple_return(prices_missing, w) is None


def test_m2_zero_volume_excluded_not_imputed():
    days = _weekday_span(date(2020, 1, 2), 130)
    prices = {d: 100.0 + i for i, d in enumerate(days)}
    values = {d: 1_000_000.0 for d in days}
    w = days[:127]
    # Force all but 125 Amihud-usable days to zero volume → FAIL
    for d in w[1:]:
        values[d] = 0.0
    for d in w[1:126]:
        values[d] = 1_000_000.0
    assert part3b1.amihud_mean(prices, values, w) is None
    diag = part3b1.m2_window_diagnostics(prices, values, w)
    assert diag["zero_traded_value_day_count"] >= 1
    assert diag["usable_amihud_day_count"] == 125


def test_m2_sparse_window_below_threshold_null():
    # Sparse window with endpoints but only a handful of returns
    days = [date(2020, 1, 3), date(2020, 1, 6), date(2020, 1, 7)]
    prices = {d: 10.0 + i for i, d in enumerate(days)}
    values = {d: 1_000_000.0 for d in days}
    assert part3b1.cumulative_simple_return(prices, days) is None
    assert part3b1.sample_stdev(part3b1.daily_returns(prices, days)) is None
    assert part3b1.amihud_mean(prices, values, days) is None


def test_m2_trading_day_before_cutoff_accepted():
    cutoff = date(2020, 6, 10)
    days = [date(2020, 6, 8), date(2020, 6, 9)]
    assert part3b1.last_trading_day_strictly_before(cutoff, days) == date(2020, 6, 9)


def test_m2_trading_day_equal_cutoff_rejected():
    cutoff = date(2020, 6, 10)
    days = [date(2020, 6, 8), date(2020, 6, 10)]
    chosen = part3b1.last_trading_day_strictly_before(cutoff, days)
    assert chosen == date(2020, 6, 8)
    assert chosen != cutoff


def test_m2_trading_day_after_cutoff_rejected():
    cutoff = date(2020, 6, 10)
    days = [date(2020, 6, 8), date(2020, 6, 11)]
    chosen = part3b1.last_trading_day_strictly_before(cutoff, days)
    assert chosen == date(2020, 6, 8)
    assert date(2020, 6, 11) not in (part3b1.window_trading_days(days, cutoff) or [])


def test_m2_equal_cutoff_falls_back_to_previous_trading_day():
    cutoff = date(2020, 6, 10)
    days = [date(2020, 6, 5), date(2020, 6, 8), date(2020, 6, 9), date(2020, 6, 10)]
    w = part3b1.window_trading_days(days, cutoff)
    assert w is not None
    assert w[-1] == date(2020, 6, 9)
    assert date(2020, 6, 10) not in w


def test_m2_no_valid_pre_cutoff_day_returns_null_window():
    cutoff = date(2020, 6, 10)
    days = [date(2020, 6, 10), date(2020, 6, 11)]
    assert part3b1.last_trading_day_strictly_before(cutoff, days) is None
    assert part3b1.window_trading_days(days, cutoff) is None


def test_m2_no_imputation_or_cutoff_mutation():
    cutoff = date(2020, 6, 10)
    days = [date(2020, 6, 10)]
    assert part3b1.window_trading_days(days, cutoff) is None
    assert cutoff == date(2020, 6, 10)


def test_m2_shared_window_used_by_all_three_variables():
    days = [
        date(2020, 1, 2) + timedelta(days=i)
        for i in range(0, 400)
        if (date(2020, 1, 2) + timedelta(days=i)).weekday() < 5
    ]
    cutoff = date(2020, 12, 15)
    prices = {d: 100.0 + (i % 11) for i, d in enumerate(days)}
    values = {d: 1_000_000.0 for d in days}
    w = part3b1.window_trading_days(days, cutoff)
    assert w is not None
    r = part3b1.cumulative_simple_return(prices, w)
    vol = part3b1.sample_stdev(part3b1.daily_returns(prices, w))
    am = part3b1.amihud_mean(prices, values, w)
    assert r is not None and vol is not None and am is not None
    assert w[-1] < cutoff
    m2 = part3b1.build_m2_formula_contract()
    assert set(m2["variables"]) == {
        "equity_return_window", "realized_volatility", "amihud_illiquidity",
    }
    assert m2["shared_window"]["length"] == "12_calendar_months"


def test_synth_m2_null_when_endpoint_price_missing():
    days = [date(2020, 1, 3), date(2020, 1, 6), date(2020, 1, 7)]
    prices = {date(2020, 1, 6): 10.0}  # missing endpoints
    assert part3b1.cumulative_simple_return(prices, days) is None


def test_synth_m4_null_and_explicit_rules():
    assert part3b1.audit_lag_days(None, "2020-06-01") is None
    assert part3b1.audit_lag_days("2020-03-19", "2020-06-20") == 93
    assert part3b1.audit_lag_days("2020-03-19", "2020-03-19") == 0
    assert part3b1.audit_lag_days("2020-06-20", "2020-03-19") is None
    assert part3b1.audit_lag_days("not-a-date", "2020-06-20") is None
    assert part3b1.going_concern_flag(None) is None
    assert part3b1.going_concern_flag("ambiguous") is None
    assert part3b1.going_concern_flag("unstructured_only") is None
    assert part3b1.going_concern_flag("conflict") is None
    assert part3b1.going_concern_flag("present") is True
    assert part3b1.going_concern_flag("true") is True
    assert part3b1.going_concern_flag("false") is False
    assert part3b1.going_concern_flag("absent_explicit_false") is False


@pytest.mark.parametrize(
    ("available_at", "pair_cutoff", "expected"),
    [
        ("2020-06-01T00:00:00Z", "2020-06-15T00:00:00Z", True),  # before
        ("2020-06-15T00:00:00Z", "2020-06-15T00:00:00Z", True),  # equal
        ("2020-06-20T00:00:00Z", "2020-06-15T00:00:00Z", False),  # after
        ("2020-06-15T04:00:00+04:00", "2020-06-15T00:00:00Z", True),  # offset eq
        ("2020-06-15T00:00:00Z", "2020-06-15T00:00:00+00:00", True),  # Z vs +00
        ("2020-06-15T00:00:00", "2020-06-15T00:00:00Z", False),  # naive
        ("not-a-timestamp", "2020-06-15T00:00:00Z", False),  # malformed
        ("", "2020-06-15T00:00:00Z", False),
        (None, "2020-06-15T00:00:00Z", False),
        # DST/offset edge: same instant across US DST spring-forward window
        ("2020-03-08T07:00:00+00:00", "2020-03-08T02:00:00-05:00", True),
        ("2020-03-08T08:00:00+00:00", "2020-03-08T02:00:00-05:00", False),
    ],
)
def test_feature_usable_semantic_timestamps(available_at, pair_cutoff, expected):
    assert part3b1.feature_usable(available_at, pair_cutoff) is expected


def test_build_all_contains_required_files_and_not_legacy_part3b():
    content = part3b1.build_all(REPO_ROOT)
    for name in part3b1.CONTENT_FILES:
        assert name in content
        assert content[name]
    assert part3b1.F_REQ == "part3b1_adjudicated_decision_requirements_stage125.json"
    assert part3b1.F_README == "README_STAGE125_PART3B1_DECISION_LOCK.md"
    assert "part3b_decision_requirements_stage125.json" not in content
    assert (
        "README_STAGE125_PART3B1_FEATURE_DEFINITION_SCORING_ADJUDICATION.md"
        not in content
    )


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


def test_qc_all_pass_offline_evidence_based():
    content = part3b1.build_all(REPO_ROOT)
    hashes = {
        k: part3b1.sha256_bytes(v.encode("utf-8")) for k, v in content.items()
    }
    frozen = part3b1.frozen_input_hashes(REPO_ROOT)
    part3b_hashes = part3b1.verify_frozen_part3b_output_hashes(REPO_ROOT)
    hits = part3b1.scan_closed_world_part3b1(REPO_ROOT)
    ok, offenders = part3b1.verify_changed_paths_exact_allowlist(REPO_ROOT)
    with p3b0.network_sentinel() as sentinel:
        qc = part3b1.build_qc_report(
            REPO_ROOT, content, hashes, frozen,
            network_calls_attempted=sentinel.calls_attempted,
            part3b_hashes=part3b_hashes,
            closed_world_hits=hits,
            changed_path_ok=ok,
            changed_path_offenders=offenders,
        )
    assert qc["all_pass"] is True
    assert qc["failed_count"] == 0
    assert qc["part3b1_decision_locked"] is True
    assert qc["part3b_completed"] is False
    assert qc["modeling_started"] is False
    assert qc["accessibility_scoring_applied"] is False
    assert qc["network_extraction_performed"] is True
    assert qc["part3b1_network_calls_attempted"] == 0
    assert qc["frozen_part3b_output_sha256"]
    names = {a["assertion"] for a in qc["assertions"]}
    assert "zero_part3b1_network_calls_sentinel" in names
    assert "unchanged_frozen_part3b_hashes" in names
    assert "closed_world_no_new_cache_evidence_score_model" in names
    assert "changed_path_exact_allowlist" in names


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


def test_part3b_check_verifies_all_metadata_hashes_no_skip():
    src = (ROOT / "src" / "stage125_part3b_evidence_capture.py").read_text(
        encoding="utf-8",
    )
    assert "PART3B1_OWNED_AFTER_LOCK" not in src
    assert "skip_owned" not in src
    assert "part3b1_decision_locked" not in src


def test_part3b_tamper_legacy_decision_req_fails_check(tmp_path):
    stage = tmp_path / "project" / "stage125"
    stage.mkdir(parents=True)
    # Copy only the files needed for hash check of one artifact via metadata.
    meta = json.loads(
        (OUTPUT_DIR / "metadata_and_hashes_stage125_part3b.json").read_text(
            encoding="utf-8",
        )
    )
    # Minimal repo for check would need many files; instead unit-test the
    # hash-loop semantics used by run_check.
    name = "part3b_decision_requirements_stage125.json"
    expected = meta["output_files_sha256"][name]
    shutil.copy2(OUTPUT_DIR / name, stage / name)
    assert part3b.sha256_file(stage / name) == expected
    (stage / name).write_text(
        (stage / name).read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    assert part3b.sha256_file(stage / name) != expected


def test_negative_closed_world_evidence_score_cache_model(tmp_path, monkeypatch):
    # Use real repo root scan but plant an unauthorized file via monkeypatch of
    # stage125 path by copying structure is heavy; call scanner on REPO_ROOT
    # after planting a temp unauthorized file then remove it.
    planted = OUTPUT_DIR / "model_weights.pkl"
    planted.write_bytes(b"evil-model")
    try:
        hits = part3b1.scan_closed_world_part3b1(REPO_ROOT)
        assert any("model_weights.pkl" in h for h in hits)
    finally:
        planted.unlink(missing_ok=True)

    planted2 = OUTPUT_DIR / "accessibility_scores_live.csv"
    planted2.write_text("a,b\n", encoding="utf-8")
    try:
        hits = part3b1.scan_closed_world_part3b1(REPO_ROOT)
        assert any("accessibility_scores_live.csv" in h for h in hits)
    finally:
        planted2.unlink(missing_ok=True)

    planted3 = OUTPUT_DIR / "evil_evidence_cache.bin"
    planted3.write_bytes(b"cache")
    try:
        hits = part3b1.scan_closed_world_part3b1(REPO_ROOT)
        assert any("evil_evidence_cache.bin" in h for h in hits)
    finally:
        planted3.unlink(missing_ok=True)


def test_negative_network_attempt_fails_qc_assertion():
    content = part3b1.build_all(REPO_ROOT)
    hashes = {
        k: part3b1.sha256_bytes(v.encode("utf-8")) for k, v in content.items()
    }
    frozen = part3b1.frozen_input_hashes(REPO_ROOT)
    part3b_hashes = part3b1.verify_frozen_part3b_output_hashes(REPO_ROOT)
    hits = part3b1.scan_closed_world_part3b1(REPO_ROOT)
    ok, offenders = part3b1.verify_changed_paths_exact_allowlist(REPO_ROOT)
    with p3b0.network_sentinel() as sentinel:
        with pytest.raises(p3b0.NetworkBlockedError):
            socket.create_connection(("example.com", 80), timeout=0.1)
        assert sentinel.calls_attempted >= 1
        qc = part3b1.build_qc_report(
            REPO_ROOT, content, hashes, frozen,
            network_calls_attempted=sentinel.calls_attempted,
            part3b_hashes=part3b_hashes,
            closed_world_hits=hits,
            changed_path_ok=ok,
            changed_path_offenders=offenders,
        )
    assert qc["all_pass"] is False
    failed = {a["assertion"] for a in qc["assertions"] if a["status"] == "FAIL"}
    assert "zero_part3b1_network_calls_sentinel" in failed


def test_negative_part3b_hash_drift_detected():
    # Mutating a frozen Part 3B file must be detected by verifier.
    path = OUTPUT_DIR / "part3b_decision_requirements_stage125.json"
    original = path.read_text(encoding="utf-8")
    try:
        path.write_text(original + "\n", encoding="utf-8")
        with pytest.raises(part3b1.QCFail, match="Part 3B frozen hash drift"):
            part3b1.verify_frozen_part3b_output_hashes(REPO_ROOT)
    finally:
        path.write_text(original, encoding="utf-8")


def test_part3b_check_fails_on_tampered_legacy_decision_req():
    path = OUTPUT_DIR / "part3b_decision_requirements_stage125.json"
    original = path.read_bytes()
    try:
        path.write_bytes(original + b"\n")
        with pytest.raises(part3b.QCFail, match="check drift"):
            part3b.run_check(REPO_ROOT, OUTPUT_DIR)
    finally:
        path.write_bytes(original)


def test_part3b_check_fails_on_tampered_legacy_readme():
    path = OUTPUT_DIR / (
        "README_STAGE125_PART3B1_FEATURE_DEFINITION_SCORING_ADJUDICATION.md"
    )
    original = path.read_bytes()
    try:
        path.write_bytes(original + b"\n")
        with pytest.raises(part3b.QCFail, match="check drift"):
            part3b.run_check(REPO_ROOT, OUTPUT_DIR)
    finally:
        path.write_bytes(original)


@pytest.mark.skipif(
    not (OUTPUT_DIR / part3b1.F_DECISION).is_file(),
    reason="deliverables not written yet",
)
def test_on_disk_lock_markers():
    lock = json.loads((OUTPUT_DIR / part3b1.F_DECISION).read_text(encoding="utf-8"))
    assert lock["part3b1_decision_locked"] is True
    assert lock["part3b_completed"] is False
    assert lock["modeling_started"] is False
