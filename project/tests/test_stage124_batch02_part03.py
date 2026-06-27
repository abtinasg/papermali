"""Independent tests for Stage124 Batch 2 Part 3 research screening."""

import json
import hashlib
from pathlib import Path

import pandas as pd
import pytest

from project.src.stage124_batch02_part03 import (
    PART03_TICKERS,
    PART03_DIR,
    SNAPSHOT_DIR,
    RESEARCH_SOURCES,
    CANONICAL_EVENT_TYPES,
    FROZEN_V2_TSETMC_AUDIT,
    PART02_PROTECTED,
    build_tickers_df,
    build_research_screening,
    build_source_provenance,
    build_tsetmc_audit,
    load_historical_tsetmc,
    run_part03_qc,
    _derive_screening_status,
)
from project.src.stage124_batch02_part02 import PART02_TICKERS
from project.src.stage124_batch02_v2 import PILOT15, sha, ROOT


# ---- helpers -------------------------------------------------------------------
def _names():
    return {tk: f"Company_{tk}" for tk in PART03_TICKERS}


def _absent_tsetmc():
    """All 10 tickers absent from frozen V2 audit (matches reality)."""
    out = {}
    for tk in PART03_TICKERS:
        out[tk] = {
            "instrument_match_status": "not_in_historical_v2_audit",
            "tsetmc_candidate_date_jalali": "",
            "tsetmc_candidate_date_gregorian": "",
            "selected_inscode": "",
            "candidate_disposition": "not_in_historical_v2_audit",
            "source_file_path": "stage124/listing_batch02_tsetmc_conflict_audit_v2.csv",
            "source_file_sha256": "abc",
            "probe_source": "historical_v2_audit",
            "network_request_performed": "false",
        }
    return out


def _failed_fetch_results():
    """All sources attempted, all timed out — no snapshot, no hash."""
    out = {}
    for tk in PART03_TICKERS:
        recs = []
        for idx, src in enumerate(RESEARCH_SOURCES.get(tk, []), 1):
            recs.append({
                "ticker": tk, "source_index": idx,
                "source_type": src[0], "source_title": src[1],
                "source_url": src[2], "publication_date": "",
                "retrieved_at_utc": "2025-01-01T00:00:00Z", "http_status": "",
                "retrieval_status": "timeout", "final_url": src[2],
                "content_type": "", "response_size_bytes": "",
                "snapshot_path": "", "content_sha256": "",
                "extraction_notes": "timed out; no snapshot stored; no hash fabricated.",
                "exact_text_or_event_summary": "",
                "supported_event_type": "", "supported_date_jalali": "",
            })
        out[tk] = recs
    return out


def _baseline_dfs():
    names = _names()
    tsetmc = _absent_tsetmc()
    fetch = _failed_fetch_results()
    tickers_df = build_tickers_df(names)
    research_df = build_research_screening(names, fetch, tsetmc)
    provenance_df = build_source_provenance(fetch)
    tsetmc_df = build_tsetmc_audit(tsetmc)
    return tickers_df, research_df, provenance_df, tsetmc_df


def _qc(tickers_df, research_df, provenance_df, tsetmc_df,
        frozen=None, p02=None):
    frozen = frozen or {}
    p02 = p02 or {}
    return run_part03_qc(tickers_df, research_df, provenance_df, tsetmc_df,
                         frozen, frozen, p02, p02)


def _result(qc, name):
    for a in qc["assertions"]:
        if a["assertion"] == name:
            return a["passed"]
    return None


def _any_failed_containing(qc, substr):
    return any((not a["passed"]) and substr in a["assertion"] for a in qc["assertions"])


# ---- baseline ------------------------------------------------------------------
def test_baseline_qc_passes():
    qc = _qc(*_baseline_dfs())
    failed = [a["assertion"] for a in qc["assertions"] if not a["passed"]]
    assert qc["all_pass"], f"unexpected failures: {failed}"


def test_exact_ticker_set_and_order():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    assert research_df["ticker"].tolist() == PART03_TICKERS
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert _result(qc, "ticker_set_and_order_match") is True


def test_no_part2_or_pilot15_overlap():
    _, research_df, _, _ = _baseline_dfs()
    s = set(research_df["ticker"])
    assert s & set(PART02_TICKERS) == set()
    assert s & PILOT15 == set()


# ---- ticker-set violations -----------------------------------------------------
def test_missing_ticker():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    research_df = research_df.iloc[:-1].copy()
    tickers_df = tickers_df.iloc[:-1].copy()
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert qc["all_pass"] is False
    assert _result(qc, "exactly_10_rows") is False or _result(qc, "no_missing_tickers") is False


def test_extra_ticker():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    extra = research_df.iloc[[0]].copy()
    extra["ticker"] = " زپارس"
    extra["ticker_normalized"] = "زپارس"
    research_df = pd.concat([research_df, extra], ignore_index=True)
    tickers_df = pd.concat([tickers_df, tickers_df.iloc[[0]].assign(ticker="زپارس")],
                           ignore_index=True)
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert qc["all_pass"] is False
    assert _result(qc, "no_extra_tickers") is False


def test_duplicate_ticker():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    research_df = pd.concat([research_df, research_df.iloc[[0]]], ignore_index=True)
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert _result(qc, "no_duplicate_tickers") is False


# ---- canonical-rule violations -------------------------------------------------
def test_admission_only_canonical_violation():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    i = research_df.index[0]
    research_df.at[i, "admission_date_candidate_jalali"] = "1380-01-01"
    research_df.at[i, "proposed_canonical_public_entry_date_jalali"] = "1380-01-01"
    research_df.at[i, "proposed_canonical_event_type"] = "first_public_offering"
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert _any_failed_containing(qc, "no_canonical_from_admission")


def test_invalid_canonical_event_type():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    i = research_df.index[0]
    research_df.at[i, "proposed_canonical_public_entry_date_jalali"] = "1380-01-01"
    research_df.at[i, "proposed_canonical_event_type"] = "admission"
    research_df.at[i, "date_precision"] = "exact_day"
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert _any_failed_containing(qc, "canonical_event_valid")


def test_exact_day_without_valid_evidence_is_not_ready():
    """An exact-day canonical claim with no fetched, hashed source must fail the
    ready-requires-fetched-source assertion when marked ready."""
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    i = research_df.index[0]
    research_df.at[i, "proposed_canonical_public_entry_date_jalali"] = "1380-01-01"
    research_df.at[i, "proposed_canonical_event_type"] = "first_public_offering"
    research_df.at[i, "date_precision"] = "exact_day"
    research_df.at[i, "evidence_status"] = "candidate_supported"
    research_df.at[i, "ready_for_user_review"] = "true"
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert _any_failed_containing(qc, "ready_requires_fetched_source_with_hash")


def test_ready_true_without_fetched_source_hash():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    i = research_df.index[0]
    tk = research_df.at[i, "ticker"]
    research_df.at[i, "proposed_canonical_public_entry_date_jalali"] = "1380-01-01"
    research_df.at[i, "proposed_canonical_event_type"] = "first_public_trading"
    research_df.at[i, "date_precision"] = "exact_day"
    research_df.at[i, "evidence_status"] = "candidate_supported"
    research_df.at[i, "ready_for_user_review"] = "true"
    # provenance for tk remains failed (no hash)
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert _result(qc, f"ready_requires_fetched_source_with_hash_{tk}") is False


def test_month_only_ready_true_fails():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    i = research_df.index[0]
    tk = research_df.at[i, "ticker"]
    research_df.at[i, "date_precision"] = "month_only"
    research_df.at[i, "ready_for_user_review"] = "true"
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert _result(qc, f"non_exact_not_ready_{tk}") is False


def test_year_only_ready_true_fails():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    i = research_df.index[0]
    tk = research_df.at[i, "ticker"]
    research_df.at[i, "date_precision"] = "year_only"
    research_df.at[i, "ready_for_user_review"] = "true"
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert _result(qc, f"non_exact_not_ready_{tk}") is False


def test_conflict_with_ready_true_fails():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    i = research_df.index[0]
    tk = research_df.at[i, "ticker"]
    research_df.at[i, "conflict_flag"] = "true"
    research_df.at[i, "ready_for_user_review"] = "true"
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert _result(qc, f"conflict_not_ready_{tk}") is False


# ---- taxonomy ------------------------------------------------------------------
def test_tacodal_marked_codal_official_fails():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    j = prov_df.index[0]
    prov_df.at[j, "source_url"] = "https://tacodal.ir/symbol/test"
    prov_df.at[j, "source_type"] = "codal_official"
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert _any_failed_containing(qc, "aggregator_not_codal_official")


def test_codal_official_must_be_codal_domain():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    j = prov_df.index[0]
    prov_df.at[j, "source_type"] = "codal_official"
    prov_df.at[j, "source_url"] = "https://example.com/x"
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert _any_failed_containing(qc, "codal_official_is_codal_domain")


# ---- TSETMC --------------------------------------------------------------------
def test_tsetmc_date_used_as_canonical_fails():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    i = research_df.index[0]
    tk = research_df.at[i, "ticker"]
    research_df.at[i, "proposed_canonical_public_entry_date_jalali"] = "1390-05-05"
    j = tsetmc_df.index[tsetmc_df["ticker"] == tk][0]
    tsetmc_df.at[j, "tsetmc_candidate_date_jalali"] = "1390-05-05"
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert _result(qc, f"tsetmc_date_not_canonical_{tk}") is False


def test_tsetmc_live_network_call_fails():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    j = tsetmc_df.index[0]
    tk = tsetmc_df.at[j, "ticker"]
    tsetmc_df.at[j, "network_request_performed"] = "true"
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert _result(qc, f"tsetmc_no_network_{tk}") is False


def test_tsetmc_not_from_historical_v2_fails():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    j = tsetmc_df.index[0]
    tk = tsetmc_df.at[j, "ticker"]
    tsetmc_df.at[j, "probe_source"] = "live_probe"
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert _result(qc, f"tsetmc_from_historical_v2_{tk}") is False


def test_network_unreachable_preserved():
    """network_unreachable historical status must keep network_unreachable
    disposition (never silently become 'no candidate')."""
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    j = tsetmc_df.index[0]
    tk = tsetmc_df.at[j, "ticker"]
    tsetmc_df.at[j, "instrument_match_status"] = "network_unreachable"
    tsetmc_df.at[j, "candidate_disposition"] = "no_candidate"
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert _result(qc, f"network_unreachable_preserved_{tk}") is False


# ---- provenance integrity ------------------------------------------------------
def test_absolute_snapshot_path_fails():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    j = prov_df.index[0]
    prov_df.at[j, "retrieval_status"] = "fetched_ok"
    prov_df.at[j, "content_sha256"] = "deadbeef"
    prov_df.at[j, "snapshot_path"] = "/Users/x/Desktop/snap.html"
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert _any_failed_containing(qc, "snapshot_path_relative")


def test_snapshot_hash_mismatch_fails(tmp_path):
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    # write a real snapshot under the real snapshots dir, then claim wrong hash
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snap = SNAPSHOT_DIR / "__test_hashmismatch.html"
    snap.write_bytes(b"<html>real</html>")
    rel = "stage124/batch02_parts/snapshots_part03/__test_hashmismatch.html"
    try:
        j = prov_df.index[0]
        prov_df.at[j, "retrieval_status"] = "fetched_ok"
        prov_df.at[j, "snapshot_path"] = rel
        prov_df.at[j, "content_sha256"] = "0" * 64  # wrong
        qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
        assert _any_failed_containing(qc, "snapshot_hash_matches")
    finally:
        snap.unlink(missing_ok=True)


def test_failed_fetch_with_fabricated_hash_fails():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    j = prov_df.index[0]
    # status still failed, but a hash was fabricated
    prov_df.at[j, "retrieval_status"] = "timeout"
    prov_df.at[j, "content_sha256"] = "f" * 64
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert _any_failed_containing(qc, "failed_fetch_no_hash")


def test_failed_fetch_with_fabricated_snapshot_fails():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    j = prov_df.index[0]
    prov_df.at[j, "retrieval_status"] = "connection_error"
    prov_df.at[j, "snapshot_path"] = "stage124/batch02_parts/snapshots_part03/x.html"
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert _any_failed_containing(qc, "failed_fetch_no_snapshot")


# ---- forbidden content ---------------------------------------------------------
def test_verified_user_confirmed_present_fails():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    i = research_df.index[0]
    research_df.at[i, "research_status"] = "verified_user_" + "confirmed"
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert _result(qc, "no_user_verification_token") is False


# ---- empty-input fail-closed ---------------------------------------------------
def test_empty_research_input_fails():
    tickers_df, _, prov_df, tsetmc_df = _baseline_dfs()
    qc = _qc(tickers_df, pd.DataFrame(), prov_df, tsetmc_df)
    assert qc["all_pass"] is False
    assert _result(qc, "research_df_non_empty") is False


def test_empty_provenance_input_fails():
    tickers_df, research_df, _, tsetmc_df = _baseline_dfs()
    qc = _qc(tickers_df, research_df, pd.DataFrame(), tsetmc_df)
    assert qc["all_pass"] is False
    assert _result(qc, "provenance_df_non_empty") is False


def test_empty_tsetmc_input_fails():
    tickers_df, research_df, prov_df, _ = _baseline_dfs()
    qc = _qc(tickers_df, research_df, prov_df, pd.DataFrame())
    assert qc["all_pass"] is False
    assert _result(qc, "tsetmc_df_non_empty") is False


# ---- protected-file change detection -------------------------------------------
def test_part02_change_detected():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    before = {"/x/part02_qc_report.json": "aaa"}
    after = {"/x/part02_qc_report.json": "bbb"}
    qc = run_part03_qc(tickers_df, research_df, prov_df, tsetmc_df,
                       {}, {}, before, after)
    assert _any_failed_containing(qc, "part02_unchanged")


def test_frozen_change_detected():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    before = {"/x/listing_batch02_tsetmc_conflict_audit_v2.csv": "aaa"}
    after = {"/x/listing_batch02_tsetmc_conflict_audit_v2.csv": "bbb"}
    qc = run_part03_qc(tickers_df, research_df, prov_df, tsetmc_df,
                       before, after, {}, {})
    assert _any_failed_containing(qc, "frozen_unchanged")


# ---- _derive_screening_status unit ---------------------------------------------
def test_derive_status_no_evidence_is_unresolved():
    st = _derive_screening_status([
        {"retrieval_status": "timeout", "content_sha256": "",
         "supported_event_type": "", "supported_date_jalali": ""},
    ])
    assert st["evidence_status"] == "no_reliable_evidence"
    assert st["ready_for_user_review"] == "false"
    assert st["proposed_canonical_public_entry_date_jalali"] == ""
    assert st["date_precision"] == "unknown"


def test_derive_status_conflict_when_two_dates():
    st = _derive_screening_status([
        {"retrieval_status": "fetched_ok", "content_sha256": "a",
         "supported_event_type": "first_public_offering", "supported_date_jalali": "1380-01-01"},
        {"retrieval_status": "fetched_ok", "content_sha256": "b",
         "supported_event_type": "first_public_trading", "supported_date_jalali": "1381-02-02"},
    ])
    assert st["conflict_flag"] == "true"
    assert st["ready_for_user_review"] == "false"
    assert st["proposed_canonical_public_entry_date_jalali"] == ""


def test_derive_status_single_supported_date_ready():
    st = _derive_screening_status([
        {"retrieval_status": "fetched_ok", "content_sha256": "a",
         "supported_event_type": "first_public_offering", "supported_date_jalali": "1380-01-01"},
    ])
    assert st["proposed_canonical_event_type"] == "first_public_offering"
    assert st["ready_for_user_review"] == "true"
    assert st["date_precision"] == "exact_day"


# ---- real generated output -----------------------------------------------------
def _load_real_research():
    p = PART03_DIR / "part03_research_screening_10tickers.csv"
    if not p.exists():
        pytest.skip("part03 output not generated yet")
    return pd.read_csv(p, dtype=str).fillna("")


def test_real_output_exact_set_and_order():
    df = _load_real_research()
    assert df["ticker"].tolist() == PART03_TICKERS


def test_real_output_no_fabricated_evidence():
    p = PART03_DIR / "part03_source_provenance_10tickers.csv"
    if not p.exists():
        pytest.skip("part03 provenance not generated yet")
    df = pd.read_csv(p, dtype=str).fillna("")
    for _, r in df.iterrows():
        if r["retrieval_status"] not in ("fetched_ok", "reused_existing_snapshot"):
            assert r["snapshot_path"].strip() == ""
            assert r["content_sha256"].strip() == ""


def test_real_output_no_ready_without_evidence():
    df = _load_real_research()
    prov = pd.read_csv(PART03_DIR / "part03_source_provenance_10tickers.csv",
                       dtype=str).fillna("")
    for _, r in df.iterrows():
        if str(r["ready_for_user_review"]).lower() == "true":
            sub = prov[prov["ticker"] == r["ticker"]]
            assert ((sub["retrieval_status"].isin(["fetched_ok", "reused_existing_snapshot"]))
                    & (sub["content_sha256"].str.strip() != "")).any()


def test_real_qc_report_self_consistent():
    p = PART03_DIR / "part03_qc_report.json"
    if not p.exists():
        pytest.skip("part03 qc not generated yet")
    qc = json.loads(p.read_text(encoding="utf-8"))
    assert qc["ticker_count"] == 10
    assert qc["tickers"] == PART03_TICKERS
    assert qc["failed_count"] == sum(1 for a in qc["assertions"] if not a["passed"])
    assert qc["all_pass"] == (qc["failed_count"] == 0)


def test_real_tsetmc_no_network_and_historical():
    p = PART03_DIR / "part03_tsetmc_audit_10tickers.csv"
    if not p.exists():
        pytest.skip("part03 tsetmc not generated yet")
    df = pd.read_csv(p, dtype=str).fillna("")
    assert (df["network_request_performed"].str.lower() == "false").all()
    assert (df["probe_source"] == "historical_v2_audit").all()


def test_real_part02_outputs_unchanged():
    """The committed Part 2 outputs must still match their recorded manifest."""
    manifest = PART03_DIR / "part02_hash_manifest.csv"
    if not manifest.exists():
        pytest.skip("part02 manifest missing")
    mdf = pd.read_csv(manifest, dtype=str).fillna("")
    for _, r in mdf.iterrows():
        if not r.get("sha256", "").strip():
            continue
        fp = ROOT / r["relative_path"]
        if fp.exists():
            assert sha(fp) == r["sha256"], f"{r['relative_path']} changed"
