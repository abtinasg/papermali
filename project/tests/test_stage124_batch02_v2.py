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
    assert "relative_path" in df.columns
    assert "sha256" in df.columns
    assert "file_role" in df.columns
    # Source code files should have non-empty hashes
    src_rows = df[df["file_role"] == "source_code"]
    for _, r in src_rows.iterrows():
        if (PROJECT / r["relative_path"]).exists():
            assert r["sha256"] != "", f"{r['relative_path']} should have a hash"


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


# ---- Test 33: Verified listing master exists after official API finalize -----
def test_full_verified_master_exists():
    assert FULL_VERIFIED_FORBIDDEN.exists(), \
        "listing_master_verified_stage124.csv must exist after official API finalize"
    df = pd.read_csv(FULL_VERIFIED_FORBIDDEN, dtype=str, keep_default_na=False)
    assert len(df) == 130


# ---- Test 34: normalize_digits ------------------------------------------------
def test_normalize_digits():
    assert normalize_digits("۱۳۹۷") == "1397"
    assert normalize_digits("۰۱۲۳۴۵۶۷۸۹") == "0123456789"
    assert normalize_digits("1397") == "1397"


def _build_test_fixture():
    """Build a standard test fixture: pending, priority, selected, outputs, probe_stub."""
    pm = read_csv(PARTIAL_MASTER)
    st = read_csv(STAGE123_INPUT)
    pending = load_pending(pm)
    pending_tickers = pending["ticker"].tolist()
    feats = panel_features(st)
    research = load_research()
    probe_stub = {tk: {"instrument_match_status": "network_unreachable",
                       "ordinary_instrument_count": "", "tsetmc_candidate_date_jalali": "",
                       "multiple_ordinary_instruments": 0, "probe_retrieved_at": "",
                       "probe_raw_sha256": "", "probe_notes": "stub",
                       "selected_inscode": "", "ordinary_instrument_candidates_json": "[]",
                       "tsetmc_candidate_date_gregorian": "", "tsetmc_candidate_raw_field": "dEven"}
                  for tk in pending_tickers}
    screening = screen_all_pending(pending, feats, probe_stub, research)
    priority = assign_tiers(screening)
    selected, tickers, note, unresolved = select_batch_v2(priority)
    priority["selected_for_batch02_v2"] = priority["ticker"].isin(tickers).astype(int)
    selected["selected_for_batch02_v2"] = 1
    r_df, p_df, c_df, u_df = build_outputs_v2(selected, priority, probe_stub, research, "2026-06-26T00:00:00Z")
    return pending, pending_tickers, priority, tickers, note, unresolved, research, probe_stub, r_df, p_df, c_df, u_df


def _adm_mask(df):
    """Compute admission-only mask using the real detection logic."""
    ev_mask = df.get("evidence_status", pd.Series([""])).astype(str).str.contains(
        "requires_first_public_trade_evidence", case=False, na=False)
    adm_date_mask = (
        df.get("admission_date_candidate_jalali", pd.Series([""])).astype(str).str.strip().ne("")
        & df.get("proposed_canonical_public_entry_date_jalali", pd.Series([""])).astype(str).str.strip().eq("")
    )
    return ev_mask | adm_date_mask


# ---- Test 35: QC no_verified_user_confirmed_flag checks all DataFrames --------
def test_qc_no_verified_user_confirmed_flag_real_check():
    """Verify QC fails when any Gate A DataFrame contains verified_user_confirmed."""
    _, pt, priority, tickers, note, unresolved, research, probe_stub, r_df, _, c_df, u_df = _build_test_fixture()

    # Normal case: should pass
    qc = run_qc(115, 15, tickers, priority, research, probe_stub, unresolved, note,
                research_df=r_df, conflict_df=c_df, review_df=u_df, pending_tickers=pt)
    a = next(x for x in qc["assertions"] if x["assertion"] == "no_verified_user_confirmed_flag")
    assert a["passed"] is True, "Normal case should pass"

    # Inject violation in priority
    priority_bad = priority.copy()
    priority_bad["verification_status"] = "verified_user_confirmed"
    qc2 = run_qc(115, 15, tickers, priority_bad, research, probe_stub, unresolved, note,
                 research_df=r_df, conflict_df=c_df, review_df=u_df, pending_tickers=pt)
    a2 = next(x for x in qc2["assertions"] if x["assertion"] == "no_verified_user_confirmed_flag")
    assert a2["passed"] is False, "Should fail when verified_user_confirmed in priority"

    # Inject violation in research_df
    r_df_bad = r_df.copy()
    r_df_bad.loc[r_df_bad.index[0], "evidence_status"] = "verified_user_confirmed"
    qc3 = run_qc(115, 15, tickers, priority, research, probe_stub, unresolved, note,
                 research_df=r_df_bad, conflict_df=c_df, review_df=u_df, pending_tickers=pt)
    a3 = next(x for x in qc3["assertions"] if x["assertion"] == "no_verified_user_confirmed_flag")
    assert a3["passed"] is False, "Should fail when verified_user_confirmed in research_df"

    # Inject violation in conflict_df
    c_df_bad = c_df.copy()
    c_df_bad.loc[c_df_bad.index[0], "tsetmc_instrument_match_status"] = "verified_user_confirmed"
    qc4 = run_qc(115, 15, tickers, priority, research, probe_stub, unresolved, note,
                 research_df=r_df, conflict_df=c_df_bad, review_df=u_df, pending_tickers=pt)
    a4 = next(x for x in qc4["assertions"] if x["assertion"] == "no_verified_user_confirmed_flag")
    assert a4["passed"] is False, "Should fail when verified_user_confirmed in conflict_df"

    # Inject violation in review_df
    u_df_bad = u_df.copy()
    u_df_bad.loc[u_df_bad.index[0], "evidence_status"] = "verified_user_confirmed"
    qc5 = run_qc(115, 15, tickers, priority, research, probe_stub, unresolved, note,
                 research_df=r_df, conflict_df=c_df, review_df=u_df_bad, pending_tickers=pt)
    a5 = next(x for x in qc5["assertions"] if x["assertion"] == "no_verified_user_confirmed_flag")
    assert a5["passed"] is False, "Should fail when verified_user_confirmed in review_df"


# ---- Test 36: QC canonical_date_selected_empty checks real conflict_df --------
def test_qc_canonical_date_selected_real_check():
    """Verify QC fails when conflict_df has non-empty canonical_date_selected."""
    _, pt, priority, tickers, note, unresolved, research, probe_stub, r_df, _, c_df, u_df = _build_test_fixture()

    qc = run_qc(115, 15, tickers, priority, research, probe_stub, unresolved, note,
                research_df=r_df, conflict_df=c_df, review_df=u_df, pending_tickers=pt)
    a = next(x for x in qc["assertions"] if x["assertion"] == "canonical_date_selected_empty_in_all_conflicts")
    assert a["passed"] is True

    c_df_bad = c_df.copy()
    c_df_bad.loc[0, "canonical_date_selected_jalali"] = "1397-01-01"
    qc2 = run_qc(115, 15, tickers, priority, research, probe_stub, unresolved, note,
                 research_df=r_df, conflict_df=c_df_bad, review_df=u_df, pending_tickers=pt)
    a2 = next(x for x in qc2["assertions"] if x["assertion"] == "canonical_date_selected_empty_in_all_conflicts")
    assert a2["passed"] is False, "Should fail when canonical_date_selected is non-empty"


# ---- Test 37: QC admission_only_not_in_proposed_canonical checks real data ----
def test_qc_admission_only_not_in_proposed_canonical_real_check():
    """Verify QC fails when admission-only row has non-empty proposed_canonical."""
    _, pt, priority, tickers, note, unresolved, research, probe_stub, r_df, _, c_df, u_df = _build_test_fixture()

    qc = run_qc(115, 15, tickers, priority, research, probe_stub, unresolved, note,
                research_df=r_df, conflict_df=c_df, review_df=u_df, pending_tickers=pt)
    a = next(x for x in qc["assertions"] if x["assertion"] == "admission_only_not_in_proposed_canonical")
    assert a["passed"] is True

    # Inject violation using new admission-only detection
    adm = _adm_mask(r_df)
    if adm.any():
        r_df_bad = r_df.copy()
        r_df_bad.loc[adm, "proposed_canonical_public_entry_date_jalali"] = "1380-01-01"
        qc2 = run_qc(115, 15, tickers, priority, research, probe_stub, unresolved, note,
                     research_df=r_df_bad, conflict_df=c_df, review_df=u_df, pending_tickers=pt)
        a2 = next(x for x in qc2["assertions"] if x["assertion"] == "admission_only_not_in_proposed_canonical")
        assert a2["passed"] is False, "Should fail when admission-only has proposed_canonical date"


# ---- Test 38: QC ready_for_user_review_false_for_admission_only real check ----
def test_qc_ready_for_user_review_admission_only_real_check():
    """Verify QC fails when admission-only row has ready_for_user_review=true."""
    _, pt, priority, tickers, note, unresolved, research, probe_stub, r_df, _, c_df, u_df = _build_test_fixture()

    qc = run_qc(115, 15, tickers, priority, research, probe_stub, unresolved, note,
                research_df=r_df, conflict_df=c_df, review_df=u_df, pending_tickers=pt)
    a = next(x for x in qc["assertions"] if x["assertion"] == "ready_for_user_review_false_for_admission_only")
    assert a["passed"] is True

    adm = _adm_mask(r_df)
    if adm.any():
        r_df_bad = r_df.copy()
        r_df_bad.loc[adm, "ready_for_user_review"] = "true"
        qc2 = run_qc(115, 15, tickers, priority, research, probe_stub, unresolved, note,
                     research_df=r_df_bad, conflict_df=c_df, review_df=u_df, pending_tickers=pt)
        a2 = next(x for x in qc2["assertions"] if x["assertion"] == "ready_for_user_review_false_for_admission_only")
        assert a2["passed"] is False, "Should fail when admission-only has ready_for_user_review=true"


# ---- Test 39: QC event_types_separated checks real columns --------------------
def test_qc_event_types_separated_real_check():
    """Verify QC fails when event-type columns are missing from research_df."""
    _, pt, priority, tickers, note, unresolved, research, probe_stub, r_df, _, c_df, u_df = _build_test_fixture()

    qc = run_qc(115, 15, tickers, priority, research, probe_stub, unresolved, note,
                research_df=r_df, conflict_df=c_df, review_df=u_df, pending_tickers=pt)
    a = next(x for x in qc["assertions"] if x["assertion"] == "event_types_separated")
    assert a["passed"] is True

    r_df_bad = r_df.drop(columns=["admission_date_candidate_jalali"])
    qc2 = run_qc(115, 15, tickers, priority, research, probe_stub, unresolved, note,
                 research_df=r_df_bad, conflict_df=c_df, review_df=u_df, pending_tickers=pt)
    a2 = next(x for x in qc2["assertions"] if x["assertion"] == "event_types_separated")
    assert a2["passed"] is False, "Should fail when event-type column missing"


# ---- Test 40: QC tsetmc_probe_attempted checks real probe completeness --------
def test_qc_tsetmc_probe_attempted_real_check():
    """Verify QC checks exact key set match, valid statuses, no not_probed."""
    _, pt, priority, tickers, note, unresolved, research, probe_stub, r_df, _, c_df, u_df = _build_test_fixture()

    # Normal: 115 network_unreachable — should pass
    qc = run_qc(115, 15, tickers, priority, research, probe_stub, unresolved, note,
                research_df=r_df, conflict_df=c_df, review_df=u_df, pending_tickers=pt)
    a = next(x for x in qc["assertions"] if x["assertion"] == "tsetmc_probe_attempted")
    assert a["passed"] is True, "115 network_unreachable should pass"

    # Truncated probe results — should fail (key set mismatch)
    probe_short = dict(list(probe_stub.items())[:50])
    qc2 = run_qc(115, 15, tickers, priority, research, probe_short, unresolved, note,
                 research_df=r_df, conflict_df=c_df, review_df=u_df, pending_tickers=pt)
    a2 = next(x for x in qc2["assertions"] if x["assertion"] == "tsetmc_probe_attempted")
    assert a2["passed"] is False, "Should fail when probe keys != pending set"

    # All not_probed — should fail
    probe_not_probed = {tk: dict(v, instrument_match_status="not_probed") for tk, v in probe_stub.items()}
    qc3 = run_qc(115, 15, tickers, priority, research, probe_not_probed, unresolved, note,
                 research_df=r_df, conflict_df=c_df, review_df=u_df, pending_tickers=pt)
    a3 = next(x for x in qc3["assertions"] if x["assertion"] == "tsetmc_probe_attempted")
    assert a3["passed"] is False, "Should fail when all statuses are not_probed"

    # Missing ticker — should fail
    probe_missing = dict(probe_stub)
    first_key = next(iter(probe_missing))
    del probe_missing[first_key]
    qc4 = run_qc(115, 15, tickers, priority, research, probe_missing, unresolved, note,
                 research_df=r_df, conflict_df=c_df, review_df=u_df, pending_tickers=pt)
    a4 = next(x for x in qc4["assertions"] if x["assertion"] == "tsetmc_probe_attempted")
    assert a4["passed"] is False, "Should fail when missing ticker in probe results"

    # Extra ticker — should fail
    probe_extra = dict(probe_stub)
    probe_extra["FAKE_TICKER"] = dict(probe_stub[next(iter(probe_stub))])
    qc5 = run_qc(115, 15, tickers, priority, research, probe_extra, unresolved, note,
                 research_df=r_df, conflict_df=c_df, review_df=u_df, pending_tickers=pt)
    a5 = next(x for x in qc5["assertions"] if x["assertion"] == "tsetmc_probe_attempted")
    assert a5["passed"] is False, "Should fail when extra ticker in probe results"


# ---- Test 41: External hash manifest schema -----------------------------------
def test_hash_manifest_schema():
    """Verify manifest has new schema: relative_path, file_role, size_bytes, sha256, generated_at, source_commit."""
    manifest = build_hash_manifest()
    expected_cols = ["relative_path", "file_role", "size_bytes", "sha256", "generated_at", "source_commit"]
    for col in expected_cols:
        assert col in manifest.columns, f"Missing manifest column: {col}"
    assert "file_path" not in manifest.columns, "Old column file_path should be replaced by relative_path"
    assert "file_type" not in manifest.columns, "Old column file_type should be replaced by file_role"
    manifest_row = manifest[manifest["relative_path"] == "stage124/external_hash_manifest_stage124_batch02_gate_a_v2.csv"]
    if len(manifest_row) > 0:
        assert str(manifest_row.iloc[0]["sha256"]).strip() == "", "Manifest self-hash should be empty"
    for _, row in manifest.iterrows():
        if row["file_role"] != "manifest":
            path = PROJECT / row["relative_path"]
            if path.exists():
                assert str(row["sha256"]).strip() != "", f"Empty sha256 for existing file: {row['relative_path']}"
                assert int(row["size_bytes"]) > 0, f"Zero size for existing file: {row['relative_path']}"


# ---- Test 42: QC all assertions use real data (no hardcoded True) -------------
def test_qc_no_hardcoded_true():
    """Verify that QC assertions that were previously hardcoded True now have real detail strings."""
    _, pt, priority, tickers, note, unresolved, research, probe_stub, r_df, _, c_df, u_df = _build_test_fixture()

    qc = run_qc(115, 15, tickers, priority, research, probe_stub, unresolved, note,
                research_df=r_df, conflict_df=c_df, review_df=u_df, pending_tickers=pt)

    real_check_names = [
        "no_verified_user_confirmed_flag",
        "canonical_date_selected_empty_in_all_conflicts",
        "admission_only_not_in_proposed_canonical",
        "ready_for_user_review_false_for_admission_only",
        "event_types_separated",
        "tsetmc_probe_attempted",
    ]
    for name in real_check_names:
        a = next(x for x in qc["assertions"] if x["assertion"] == name)
        assert "checked" in a["detail"] or "found" in a["detail"] or "entries" in a["detail"] or "columns" in a["detail"] or "No " in a["detail"] or "keys_match" in a["detail"], \
            f"QC assertion {name} detail should reference real data: {a['detail']}"


# ---- Test 43: Admission-only detection via evidence_status --------------------
def test_admission_only_detection_evidence_status():
    """Verify admission-only rows are detected via evidence_status == requires_first_public_trade_evidence."""
    _, _, _, _, _, _, _, _, r_df, _, _, _ = _build_test_fixture()

    adm = _adm_mask(r_df)
    ev_mask = r_df.get("evidence_status", pd.Series([""])).astype(str).str.contains(
        "requires_first_public_trade_evidence", case=False, na=False)
    assert adm.sum() > 0, "Expected at least 1 admission-only row in research output"
    assert set(r_df[ev_mask].index).issubset(set(r_df[adm].index))


# ---- Test 44: Admission-only detection via admission_date + empty canonical ----
def test_admission_only_detection_admission_date():
    """Verify rows with admission_date but empty proposed_canonical are detected as admission-only."""
    _, _, _, _, _, _, _, _, r_df, _, _, _ = _build_test_fixture()

    adm_date_mask = (
        r_df.get("admission_date_candidate_jalali", pd.Series([""])).astype(str).str.strip().ne("")
        & r_df.get("proposed_canonical_public_entry_date_jalali", pd.Series([""])).astype(str).str.strip().eq("")
    )
    adm = _adm_mask(r_df)
    assert set(r_df[adm_date_mask].index).issubset(set(r_df[adm].index))


# ---- Test 45: Zero admission-only rows should fail QC -------------------------
def test_qc_zero_admission_only_rows_fails():
    """Verify QC fails when 0 admission-only rows found in research output."""
    _, pt, priority, tickers, note, unresolved, research, probe_stub, r_df, _, c_df, u_df = _build_test_fixture()

    r_df_no_adm = r_df.copy()
    r_df_no_adm["evidence_status"] = "candidate_supported"
    r_df_no_adm["admission_date_candidate_jalali"] = ""
    r_df_no_adm["proposed_canonical_public_entry_date_jalali"] = "1397-01-01"

    qc = run_qc(115, 15, tickers, priority, research, probe_stub, unresolved, note,
                research_df=r_df_no_adm, conflict_df=c_df, review_df=u_df, pending_tickers=pt)
    a = next(x for x in qc["assertions"] if x["assertion"] == "admission_only_not_in_proposed_canonical")
    assert a["passed"] is False, "Should fail when 0 admission-only rows found"
    assert "0 admission-only" in a["detail"], f"Detail should mention 0 rows: {a['detail']}"


# ---- Test 46: 115 not_probed statuses should fail QC --------------------------
def test_qc_all_not_probed_fails():
    """Verify QC fails when all 115 probe results have status=not_probed."""
    _, pt, priority, tickers, note, unresolved, research, probe_stub, r_df, _, c_df, u_df = _build_test_fixture()

    probe_not_probed = {tk: dict(v, instrument_match_status="not_probed") for tk, v in probe_stub.items()}
    qc = run_qc(115, 15, tickers, priority, research, probe_not_probed, unresolved, note,
                research_df=r_df, conflict_df=c_df, review_df=u_df, pending_tickers=pt)
    a = next(x for x in qc["assertions"] if x["assertion"] == "tsetmc_probe_attempted")
    assert a["passed"] is False, "115 not_probed should fail"
    assert "no_not_probed=False" in a["detail"], f"Detail should mention not_probed: {a['detail']}"


# ---- Test 47: 115 network_unreachable should pass QC --------------------------
def test_qc_all_network_unreachable_passes():
    """Verify QC passes when all 115 probe results have status=network_unreachable."""
    _, pt, priority, tickers, note, unresolved, research, probe_stub, r_df, _, c_df, u_df = _build_test_fixture()

    qc = run_qc(115, 15, tickers, priority, research, probe_stub, unresolved, note,
                research_df=r_df, conflict_df=c_df, review_df=u_df, pending_tickers=pt)
    a = next(x for x in qc["assertions"] if x["assertion"] == "tsetmc_probe_attempted")
    assert a["passed"] is True, "115 network_unreachable should pass"
    assert "no_not_probed=True" in a["detail"], f"Detail should show no not_probed: {a['detail']}"


# ---- Test 48: Missing and extra ticker in probe results should fail -----------
def test_qc_probe_missing_and_extra_ticker_fails():
    """Verify QC fails when probe keys don't exactly match pending tickers."""
    _, pt, priority, tickers, note, unresolved, research, probe_stub, r_df, _, c_df, u_df = _build_test_fixture()

    # Missing: remove one ticker
    probe_missing = dict(probe_stub)
    first_key = next(iter(probe_missing))
    del probe_missing[first_key]
    qc1 = run_qc(115, 15, tickers, priority, research, probe_missing, unresolved, note,
                 research_df=r_df, conflict_df=c_df, review_df=u_df, pending_tickers=pt)
    a1 = next(x for x in qc1["assertions"] if x["assertion"] == "tsetmc_probe_attempted")
    assert a1["passed"] is False, "Missing ticker should fail"
    assert "keys_match=False" in a1["detail"]

    # Extra: add one ticker
    probe_extra = dict(probe_stub)
    probe_extra["FAKE_TICKER"] = dict(probe_stub[next(iter(probe_stub))])
    qc2 = run_qc(115, 15, tickers, priority, research, probe_extra, unresolved, note,
                 research_df=r_df, conflict_df=c_df, review_df=u_df, pending_tickers=pt)
    a2 = next(x for x in qc2["assertions"] if x["assertion"] == "tsetmc_probe_attempted")
    assert a2["passed"] is False, "Extra ticker should fail"
    assert "keys_match=False" in a2["detail"]


# ---- Test 49: verified_user_confirmed in output DataFrames fails QC -----------
def test_qc_verified_in_output_dataframes_fails():
    """Verify QC fails when verified_user_confirmed appears in research_df, conflict_df, or review_df."""
    _, pt, priority, tickers, note, unresolved, research, probe_stub, r_df, _, c_df, u_df = _build_test_fixture()

    # In research_df
    r_df_bad = r_df.copy()
    r_df_bad.loc[r_df_bad.index[0], "evidence_status"] = "verified_user_confirmed"
    qc1 = run_qc(115, 15, tickers, priority, research, probe_stub, unresolved, note,
                 research_df=r_df_bad, conflict_df=c_df, review_df=u_df, pending_tickers=pt)
    a1 = next(x for x in qc1["assertions"] if x["assertion"] == "no_verified_user_confirmed_flag")
    assert a1["passed"] is False, "Should fail for research_df"
    assert "research_df" in a1["detail"]

    # In conflict_df
    c_df_bad = c_df.copy()
    c_df_bad.loc[c_df_bad.index[0], "tsetmc_instrument_match_status"] = "verified_user_confirmed"
    qc2 = run_qc(115, 15, tickers, priority, research, probe_stub, unresolved, note,
                 research_df=r_df, conflict_df=c_df_bad, review_df=u_df, pending_tickers=pt)
    a2 = next(x for x in qc2["assertions"] if x["assertion"] == "no_verified_user_confirmed_flag")
    assert a2["passed"] is False, "Should fail for conflict_df"
    assert "conflict_df" in a2["detail"]

    # In review_df
    u_df_bad = u_df.copy()
    u_df_bad.loc[u_df_bad.index[0], "evidence_status"] = "verified_user_confirmed"
    qc3 = run_qc(115, 15, tickers, priority, research, probe_stub, unresolved, note,
                 research_df=r_df, conflict_df=c_df, review_df=u_df_bad, pending_tickers=pt)
    a3 = next(x for x in qc3["assertions"] if x["assertion"] == "no_verified_user_confirmed_flag")
    assert a3["passed"] is False, "Should fail for review_df"
    assert "review_df" in a3["detail"]


# ---- Test 50: None or empty DataFrame fails QC (fail-closed) ------------------
def test_qc_none_or_empty_dataframes_fails():
    """Verify QC fails when research_df, conflict_df, or review_df is None or empty."""
    _, pt, priority, tickers, note, unresolved, research, probe_stub, r_df, _, c_df, u_df = _build_test_fixture()

    # research_df = None
    qc1 = run_qc(115, 15, tickers, priority, research, probe_stub, unresolved, note,
                 research_df=None, conflict_df=c_df, review_df=u_df, pending_tickers=pt)
    a1 = next(x for x in qc1["assertions"] if x["assertion"] == "admission_only_not_in_proposed_canonical")
    assert a1["passed"] is False, "None research_df should fail"
    assert "None or empty" in a1["detail"]

    # conflict_df = None
    qc2 = run_qc(115, 15, tickers, priority, research, probe_stub, unresolved, note,
                 research_df=r_df, conflict_df=None, review_df=u_df, pending_tickers=pt)
    a2 = next(x for x in qc2["assertions"] if x["assertion"] == "canonical_date_selected_empty_in_all_conflicts")
    assert a2["passed"] is False, "None conflict_df should fail"
    assert "None or empty" in a2["detail"]

    # review_df = None
    qc3 = run_qc(115, 15, tickers, priority, research, probe_stub, unresolved, note,
                 research_df=r_df, conflict_df=c_df, review_df=None, pending_tickers=pt)
    a3 = next(x for x in qc3["assertions"] if x["assertion"] == "review_df_exists")
    assert a3["passed"] is False, "None review_df should fail"
    assert "None or empty" in a3["detail"]

    # Empty DataFrame
    qc4 = run_qc(115, 15, tickers, priority, research, probe_stub, unresolved, note,
                 research_df=pd.DataFrame(), conflict_df=c_df, review_df=u_df, pending_tickers=pt)
    a4 = next(x for x in qc4["assertions"] if x["assertion"] == "event_types_separated")
    assert a4["passed"] is False, "Empty research_df should fail"
