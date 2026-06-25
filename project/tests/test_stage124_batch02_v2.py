"""Independent tests for Stage124 Batch 2 Gate A V2.

These tests verify the new tiered lexicographic ranking, removal of
gap_after_1392, screening logic, TSETMC probe structure, event-type
separation, evidence standard enforcement, substantive tie handling,
batch selection constraints, and QC guardrails.
"""
import json
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from src.stage124_batch02_v2 import (
    BATCH02_MAX, BATCH02_MIN, EXPECTED_PENDING, EXPECTED_VERIFIED,
    FULL_VERIFIED_FORBIDDEN, PILOT15, REFERENCE_MERGE_COMMIT,
    SCREENING_COLUMNS, STAGE122_INPUT, STAGE123_INPUT,
    SUBSTANTIVE_TIE_KEYS, W_GAP,
    _compare_candidate_with_fye, _fye_to_jalali_date, _num_or_neg,
    _substantive_tie_key, assign_tiers, build_hash_manifest,
    build_outputs_v2, gregorian_to_jalali_str, jalali_str_to_gregorian_date,
    jalali_to_gregorian, jalali_to_gregorian_str, load_pending, load_research,
    normalize_digits, normalize_jalali, normalize_symbol, normalize_ticker,
    panel_features, read_csv, run_qc, screen_all_pending, select_batch_v2,
    sha, tsetmc_probe_ticker,
)

PARTIAL_MASTER = PROJECT / "stage124" / "listing_master_partial_verified_stage124.csv"


# ---- Test 1: W_GAP is zero ----------------------------------------------------
def test_w_gap_is_zero():
    assert W_GAP == 0.0, "W_GAP must be zero — gap_after_1392 removed from ranking"


# ---- Test 2: gap_after_1392 absent from screening columns ---------------------
def test_gap_after_1392_not_in_screening_columns():
    assert "gap_after_1392" not in SCREENING_COLUMNS
    assert "priority_score" not in SCREENING_COLUMNS


# ---- Test 3: ticker_normalized not in substantive tie keys --------------------
def test_ticker_normalized_not_in_substantive_tie_keys():
    assert "ticker_normalized" not in SUBSTANTIVE_TIE_KEYS


# ---- Test 4: priority_tier column exists in screening columns -----------------
def test_priority_tier_in_screening_columns():
    assert "priority_tier" in SCREENING_COLUMNS
    assert "priority_rank" in SCREENING_COLUMNS


# ---- Test 5: Jalali to Gregorian conversion -----------------------------------
def test_jalali_to_gregorian_conversion():
    d = jalali_to_gregorian(1397, 7, 25)
    assert d.isoformat() == "2018-10-17"

    d2 = jalali_to_gregorian(1392, 6, 26)
    assert d2.isoformat() == "2013-09-17"

    d3 = jalali_to_gregorian(1395, 11, 17)
    assert d3.isoformat() == "2017-02-05"


# ---- Test 6: Gregorian to Jalali conversion -----------------------------------
def test_gregorian_to_jalali_conversion():
    assert gregorian_to_jalali_str("2018-10-17") == "1397-07-25"
    assert gregorian_to_jalali_str("2013-09-17") == "1392-06-26"


# ---- Test 7: normalize_jalali -------------------------------------------------
def test_normalize_jalali():
    assert normalize_jalali("1397/07/25") == "1397-07-25"
    assert normalize_jalali("۱۳۹۷/۰۷/۲۵") == "1397-07-25"
    assert normalize_jalali("1397-7-5") == "1397-07-05"


# ---- Test 8: normalize_ticker -------------------------------------------------
def test_normalize_ticker():
    assert normalize_ticker("جم‌پیلن") == "جم پیلن"
    assert normalize_ticker("پی‌پاد") == "پی پاد"
    assert normalize_ticker("كي") == "کی"


# ---- Test 9: normalize_symbol -------------------------------------------------
def test_normalize_symbol():
    assert normalize_symbol("اردستان") == "اردستان"
    assert normalize_symbol("سیمان‌اردستان") == "سیمان اردستان"


# ---- Test 10: _compare_candidate_with_fye -------------------------------------
def test_compare_candidate_with_fye():
    assert _compare_candidate_with_fye("1397-07-25", "1397-09-30") == 1
    assert _compare_candidate_with_fye("1397-07-25", "1396-09-30") == 0
    assert _compare_candidate_with_fye("", "1397-09-30") == -1


# ---- Test 11: _fye_to_jalali_date ---------------------------------------------
def test_fye_to_jalali_date():
    assert _fye_to_jalali_date("1394/09/30") == "1394-09-30"
    assert _fye_to_jalali_date("") == ""
    assert _fye_to_jalali_date("۱۳۹۴/۰۹/۳۰") == "1394-09-30"


# ---- Test 12: _num_or_neg -----------------------------------------------------
def test_num_or_neg():
    assert _num_or_neg(5) == 5
    assert _num_or_neg("5") == 5
    assert _num_or_neg("unknown") == -1
    assert _num_or_neg(None) == -1


# ---- Test 13: load_research returns dict with expected tickers ----------------
def test_load_research():
    r = load_research()
    assert isinstance(r, dict)
    assert "زپارس" in r
    assert "برکت" in r
    assert "جم" in r
    assert "بالبر" in r
    # Admission-only tickers have empty proposed_canonical
    assert r["بالبر"]["proposed_canonical_public_entry_date_jalali"] == ""
    assert r["بالبر"]["ready_for_user_review"] == "false"
    # candidate_supported tickers have non-empty proposed_canonical
    assert r["زپارس"]["proposed_canonical_public_entry_date_jalali"] != ""
    assert r["زپارس"]["ready_for_user_review"] == "true"


# ---- Test 14: Admission-only tickers have empty proposed_canonical ------------
def test_admission_only_empty_canonical():
    r = load_research()
    admission_only = ["بالبر", "بکام", "تپمپی", "درازک", "دسینا", "دشیمی"]
    for tk in admission_only:
        assert tk in r, f"{tk} missing from research"
        assert r[tk]["proposed_canonical_public_entry_date_jalali"] == "", \
            f"{tk} should have empty proposed_canonical"
        assert r[tk]["ready_for_user_review"] == "false", \
            f"{tk} should have ready_for_user_review=false"
        assert r[tk]["evidence_status"] == "requires_first_public_trade_evidence", \
            f"{tk} should have requires_first_public_trade_evidence"


# ---- Test 15: Event types are separated in research data ----------------------
def test_event_types_separated():
    r = load_research()
    for tk, info in r.items():
        # All four event date fields must exist as separate keys
        assert "admission_date_candidate_jalali" in info
        assert "listing_date_candidate_jalali" in info
        assert "first_public_offering_date_candidate_jalali" in info
        assert "first_public_trading_date_candidate_jalali" in info


# ---- Test 16: candidate_supported requires exact_day and non-empty date -------
def test_candidate_supported_evidence_standard():
    r = load_research()
    for tk, info in r.items():
        if info["evidence_status"] == "candidate_supported":
            assert info["date_precision"] == "exact_day", \
                f"{tk} candidate_supported must have exact_day precision"
            assert info["proposed_canonical_public_entry_date_jalali"] != "", \
                f"{tk} candidate_supported must have non-empty proposed_canonical"
            assert info["ready_for_user_review"] == "true", \
                f"{tk} candidate_supported must have ready_for_user_review=true"


# ---- Test 17: ready_for_user_review is false for non-exact-day ----------------
def test_ready_for_user_review_false_for_non_exact_day():
    r = load_research()
    for tk, info in r.items():
        if info["date_precision"] != "exact_day":
            assert info["ready_for_user_review"] == "false", \
                f"{tk} non-exact-day must have ready_for_user_review=false"


# ---- Test 18: Tiered ranking produces tiers A-E only --------------------------
def test_tiers_only_a_to_e():
    pm = read_csv(PARTIAL_MASTER)
    st = read_csv(STAGE123_INPUT)
    pending = load_pending(pm)
    feats = panel_features(st)
    research = load_research()
    probe_stub = {tk: {"instrument_match_status": "network_unreachable",
                       "ordinary_instrument_count": "",
                       "tsetmc_candidate_date_jalali": "",
                       "multiple_ordinary_instruments": 0,
                       "probe_retrieved_at": "",
                       "probe_raw_sha256": "",
                       "probe_notes": "test stub",
                       "selected_inscode": "",
                       "ordinary_instrument_candidates_json": "[]",
                       "tsetmc_candidate_date_gregorian": "",
                       "tsetmc_candidate_raw_field": "dEven"} for tk in pending["ticker"]}
    screening = screen_all_pending(pending, feats, probe_stub, research)
    priority = assign_tiers(screening)
    valid_tiers = {"A", "B", "C", "D", "E"}
    actual_tiers = set(priority["priority_tier"].unique())
    assert actual_tiers.issubset(valid_tiers), f"Unexpected tiers: {actual_tiers - valid_tiers}"


# ---- Test 19: Substantive tie key excludes ticker -----------------------------
def test_substantive_tie_key_excludes_ticker():
    row = {"estimated_eligibility_rows_changed": 3,
           "estimated_t_plus_1_pairs_changed": 2,
           "current_prelisting_proxy_row_count": 0,
           "tsetmc_conflict_flag": 0,
           "multiple_ordinary_instruments": 0,
           "screening_source_confidence": "candidate_supported",
           "ticker_normalized": "AAA"}
    key = _substantive_tie_key(row)
    assert "AAA" not in key
    assert len(key) == len(SUBSTANTIVE_TIE_KEYS)


# ---- Test 20: Batch selection respects 15-20 range ----------------------------
def test_batch_selection_size():
    pm = read_csv(PARTIAL_MASTER)
    st = read_csv(STAGE123_INPUT)
    pending = load_pending(pm)
    feats = panel_features(st)
    research = load_research()
    probe_stub = {tk: {"instrument_match_status": "network_unreachable",
                       "ordinary_instrument_count": "",
                       "tsetmc_candidate_date_jalali": "",
                       "multiple_ordinary_instruments": 0,
                       "probe_retrieved_at": "",
                       "probe_raw_sha256": "",
                       "probe_notes": "test stub",
                       "selected_inscode": "",
                       "ordinary_instrument_candidates_json": "[]",
                       "tsetmc_candidate_date_gregorian": "",
                       "tsetmc_candidate_raw_field": "dEven"} for tk in pending["ticker"]}
    screening = screen_all_pending(pending, feats, probe_stub, research)
    priority = assign_tiers(screening)
    selected, tickers, note, unresolved = select_batch_v2(priority)
    assert BATCH02_MIN <= len(tickers) <= BATCH02_MAX, \
        f"Batch size {len(tickers)} outside [{BATCH02_MIN}, {BATCH02_MAX}]"


# ---- Test 21: No Pilot15 ticker in selected batch -----------------------------
def test_no_pilot15_in_batch():
    pm = read_csv(PARTIAL_MASTER)
    st = read_csv(STAGE123_INPUT)
    pending = load_pending(pm)
    feats = panel_features(st)
    research = load_research()
    probe_stub = {tk: {"instrument_match_status": "network_unreachable",
                       "ordinary_instrument_count": "",
                       "tsetmc_candidate_date_jalali": "",
                       "multiple_ordinary_instruments": 0,
                       "probe_retrieved_at": "",
                       "probe_raw_sha256": "",
                       "probe_notes": "test stub",
                       "selected_inscode": "",
                       "ordinary_instrument_candidates_json": "[]",
                       "tsetmc_candidate_date_gregorian": "",
                       "tsetmc_candidate_raw_field": "dEven"} for tk in pending["ticker"]}
    screening = screen_all_pending(pending, feats, probe_stub, research)
    priority = assign_tiers(screening)
    selected, tickers, note, unresolved = select_batch_v2(priority)
    assert len(set(tickers) & PILOT15) == 0, \
        f"Pilot15 tickers found in batch: {set(tickers) & PILOT15}"


# ---- Test 22: Frozen input SHA-256 matches ------------------------------------
def test_frozen_input_sha():
    assert sha(STAGE123_INPUT) == "28b9f9d4185617182c0fe06299deeb0e9a092558b8849f1dfdef7072261bc390"
    assert sha(STAGE122_INPUT) == "ece991c5ff280afa50c2ced6acfecbed4e57937cf2048cd7a11ae496a3ae7437"


# ---- Test 23: Pending count is 115, verified is 15 ----------------------------
def test_pending_and_verified_counts():
    pm = read_csv(PARTIAL_MASTER)
    pending = load_pending(pm)
    verified = pm[pm["verification_status"] == "verified_user_confirmed"]
    assert len(pending) == EXPECTED_PENDING
    assert len(verified) == EXPECTED_VERIFIED


# ---- Test 24: Screening produces 115 rows -------------------------------------
def test_screening_produces_115_rows():
    pm = read_csv(PARTIAL_MASTER)
    st = read_csv(STAGE123_INPUT)
    pending = load_pending(pm)
    feats = panel_features(st)
    research = load_research()
    probe_stub = {tk: {"instrument_match_status": "network_unreachable",
                       "ordinary_instrument_count": "",
                       "tsetmc_candidate_date_jalali": "",
                       "multiple_ordinary_instruments": 0,
                       "probe_retrieved_at": "",
                       "probe_raw_sha256": "",
                       "probe_notes": "test stub",
                       "selected_inscode": "",
                       "ordinary_instrument_candidates_json": "[]",
                       "tsetmc_candidate_date_gregorian": "",
                       "tsetmc_candidate_raw_field": "dEven"} for tk in pending["ticker"]}
    screening = screen_all_pending(pending, feats, probe_stub, research)
    assert len(screening) == EXPECTED_PENDING


# ---- Test 25: estimated_eligibility_rows_changed is "unknown" when no date ----
def test_unknown_eligibility_when_no_candidate_date():
    pm = read_csv(PARTIAL_MASTER)
    st = read_csv(STAGE123_INPUT)
    pending = load_pending(pm)
    feats = panel_features(st)
    research = load_research()
    probe_stub = {tk: {"instrument_match_status": "network_unreachable",
                       "ordinary_instrument_count": "",
                       "tsetmc_candidate_date_jalali": "",
                       "multiple_ordinary_instruments": 0,
                       "probe_retrieved_at": "",
                       "probe_raw_sha256": "",
                       "probe_notes": "test stub",
                       "selected_inscode": "",
                       "ordinary_instrument_candidates_json": "[]",
                       "tsetmc_candidate_date_gregorian": "",
                       "tsetmc_candidate_raw_field": "dEven"} for tk in pending["ticker"]}
    screening = screen_all_pending(pending, feats, probe_stub, research)
    # Tickers not in RESEARCH_V2 should have "unknown"
    unknown_count = (screening["estimated_eligibility_rows_changed"] == "unknown").sum()
    assert unknown_count > 0, "Expected unknown eligibility rows for tickers without candidate dates"


# ---- Test 26: suspected_public_entry_after_1392 is "unknown" when no evidence -
def test_suspected_unknown_when_no_evidence():
    pm = read_csv(PARTIAL_MASTER)
    st = read_csv(STAGE123_INPUT)
    pending = load_pending(pm)
    feats = panel_features(st)
    research = load_research()
    probe_stub = {tk: {"instrument_match_status": "network_unreachable",
                       "ordinary_instrument_count": "",
                       "tsetmc_candidate_date_jalali": "",
                       "multiple_ordinary_instruments": 0,
                       "probe_retrieved_at": "",
                       "probe_raw_sha256": "",
                       "probe_notes": "test stub",
                       "selected_inscode": "",
                       "ordinary_instrument_candidates_json": "[]",
                       "tsetmc_candidate_date_gregorian": "",
                       "tsetmc_candidate_raw_field": "dEven"} for tk in pending["ticker"]}
    screening = screen_all_pending(pending, feats, probe_stub, research)
    unknown_count = (screening["suspected_public_entry_after_1392"] == "unknown").sum()
    assert unknown_count > 0, "Expected 'unknown' for tickers without external evidence"


# ---- Test 27: build_hash_manifest produces entries ----------------------------
def test_build_hash_manifest():
    df = build_hash_manifest()
    assert len(df) > 0
    assert "file_path" in df.columns
    assert "sha256" in df.columns
    assert "file_type" in df.columns
    # Source code files should have non-empty hashes
    src_rows = df[df["file_type"] == "source_code"]
    for _, r in src_rows.iterrows():
        if (PROJECT / r["file_path"]).exists():
            assert r["sha256"] != "", f"{r['file_path']} should have a hash"


# ---- Test 28: QC assertions cover key guardrails ------------------------------
def test_qc_covers_key_guardrails():
    pm = read_csv(PARTIAL_MASTER)
    st = read_csv(STAGE123_INPUT)
    pending = load_pending(pm)
    verified = pm[pm["verification_status"] == "verified_user_confirmed"]
    feats = panel_features(st)
    research = load_research()
    probe_stub = {tk: {"instrument_match_status": "network_unreachable",
                       "ordinary_instrument_count": "",
                       "tsetmc_candidate_date_jalali": "",
                       "multiple_ordinary_instruments": 0,
                       "probe_retrieved_at": "",
                       "probe_raw_sha256": "",
                       "probe_notes": "test stub",
                       "selected_inscode": "",
                       "ordinary_instrument_candidates_json": "[]",
                       "tsetmc_candidate_date_gregorian": "",
                       "tsetmc_candidate_raw_field": "dEven"} for tk in pending["ticker"]}
    screening = screen_all_pending(pending, feats, probe_stub, research)
    priority = assign_tiers(screening)
    selected, tickers, note, unresolved = select_batch_v2(priority)
    qc = run_qc(len(pending), len(verified), tickers, priority, research,
                probe_stub, unresolved, note)
    assertion_names = [a["assertion"] for a in qc["assertions"]]
    assert "w_gap_is_zero" in assertion_names
    assert "gap_after_1392_not_in_priority_columns" in assertion_names
    assert "no_verified_user_confirmed_flag" in assertion_names
    assert "no_full_verified_master_created" in assertion_names
    assert "no_ticker_normalized_in_substantive_tie_keys" in assertion_names


# ---- Test 29: build_outputs_v2 produces canonical_date_selected empty --------
def test_canonical_date_selected_empty():
    pm = read_csv(PARTIAL_MASTER)
    st = read_csv(STAGE123_INPUT)
    pending = load_pending(pm)
    feats = panel_features(st)
    research = load_research()
    probe_stub = {tk: {"instrument_match_status": "network_unreachable",
                       "ordinary_instrument_count": "",
                       "tsetmc_candidate_date_jalali": "",
                       "multiple_ordinary_instruments": 0,
                       "probe_retrieved_at": "",
                       "probe_raw_sha256": "",
                       "probe_notes": "test stub",
                       "selected_inscode": "",
                       "ordinary_instrument_candidates_json": "[]",
                       "tsetmc_candidate_date_gregorian": "",
                       "tsetmc_candidate_raw_field": "dEven"} for tk in pending["ticker"]}
    screening = screen_all_pending(pending, feats, probe_stub, research)
    priority = assign_tiers(screening)
    selected, tickers, note, unresolved = select_batch_v2(priority)
    r_df, p_df, c_df, u_df = build_outputs_v2(selected, priority, probe_stub, research, "2025-01-01T00:00:00Z")
    assert (c_df["canonical_date_selected_jalali"] == "").all()
    assert (c_df["canonical_date_selected_gregorian"] == "").all()


# ---- Test 30: Research CSV has separated event type columns -------------------
def test_research_csv_has_separated_event_columns():
    pm = read_csv(PARTIAL_MASTER)
    st = read_csv(STAGE123_INPUT)
    pending = load_pending(pm)
    feats = panel_features(st)
    research = load_research()
    probe_stub = {tk: {"instrument_match_status": "network_unreachable",
                       "ordinary_instrument_count": "",
                       "tsetmc_candidate_date_jalali": "",
                       "multiple_ordinary_instruments": 0,
                       "probe_retrieved_at": "",
                       "probe_raw_sha256": "",
                       "probe_notes": "test stub",
                       "selected_inscode": "",
                       "ordinary_instrument_candidates_json": "[]",
                       "tsetmc_candidate_date_gregorian": "",
                       "tsetmc_candidate_raw_field": "dEven"} for tk in pending["ticker"]}
    screening = screen_all_pending(pending, feats, probe_stub, research)
    priority = assign_tiers(screening)
    selected, tickers, note, unresolved = select_batch_v2(priority)
    r_df, p_df, c_df, u_df = build_outputs_v2(selected, priority, probe_stub, research, "2025-01-01T00:00:00Z")
    expected_cols = [
        "admission_date_candidate_jalali",
        "listing_date_candidate_jalali",
        "first_public_offering_date_candidate_jalali",
        "first_public_trading_date_candidate_jalali",
    ]
    for col in expected_cols:
        assert col in r_df.columns, f"Missing separated event column: {col}"


# ---- Test 31: TSETMC probe returns network_unreachable when no session --------
def test_tsetmc_probe_no_session():
    result = tsetmc_probe_ticker("زپارس", None, timeout=5.0)
    assert result["instrument_match_status"] == "network_unreachable"
    assert "not available" in result["probe_notes"] or "requests" in result["probe_notes"]


# ---- Test 32: Priority ranking is deterministic (stable sort) ----------------
def test_priority_ranking_deterministic():
    pm = read_csv(PARTIAL_MASTER)
    st = read_csv(STAGE123_INPUT)
    pending = load_pending(pm)
    feats = panel_features(st)
    research = load_research()
    probe_stub = {tk: {"instrument_match_status": "network_unreachable",
                       "ordinary_instrument_count": "",
                       "tsetmc_candidate_date_jalali": "",
                       "multiple_ordinary_instruments": 0,
                       "probe_retrieved_at": "",
                       "probe_raw_sha256": "",
                       "probe_notes": "test stub",
                       "selected_inscode": "",
                       "ordinary_instrument_candidates_json": "[]",
                       "tsetmc_candidate_date_gregorian": "",
                       "tsetmc_candidate_raw_field": "dEven"} for tk in pending["ticker"]}
    screening1 = screen_all_pending(pending, feats, probe_stub, research)
    priority1 = assign_tiers(screening1)
    screening2 = screen_all_pending(pending, feats, probe_stub, research)
    priority2 = assign_tiers(screening2)
    assert priority1["ticker"].tolist() == priority2["ticker"].tolist(), "Ranking must be deterministic"
    assert priority1["priority_rank"].tolist() == priority2["priority_rank"].tolist()


# ---- Test 33: No listing_master_verified_stage124.csv exists ------------------
def test_no_full_verified_master():
    assert not FULL_VERIFIED_FORBIDDEN.exists(), \
        "listing_master_verified_stage124.csv must not exist (Gate A forbidden action)"


# ---- Test 34: normalize_digits ------------------------------------------------
def test_normalize_digits():
    assert normalize_digits("۱۳۹۷") == "1397"
    assert normalize_digits("۰۱۲۳۴۵۶۷۸۹") == "0123456789"
    assert normalize_digits("1397") == "1397"
