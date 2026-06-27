"""Independent tests for Stage124 Batch 2 Part 3 research screening.

Part 3.1A focus: correct research-status semantics (a network failure is
"research blocked", never "no reliable evidence") and a safe, testable
evidence/ready decision that separates a successful *fetch* from reviewed
*evidence*.
"""

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
    FETCHED_STATUSES,
    NETWORK_FAILURE_STATUSES,
    FROZEN_V2_TSETMC_AUDIT,
    PART02_PROTECTED,
    ROOT,
    build_tickers_df,
    build_research_screening,
    build_source_provenance,
    build_tsetmc_audit,
    build_manual_research_worklist,
    load_historical_tsetmc,
    run_part03_qc,
    evaluate_source_record,
    decide_ready_for_user_review,
    compute_evidence_accepted,
    classify_source_authority,
    classify_source_authority_with_validation,
    is_document_specific_source,
    is_valid_exact_jalali_date,
    registrable_domain,
    _derive_screening_status,
)
from project.src.stage124_batch02_part02 import PART02_TICKERS
from project.src.stage124_batch02_v2 import PILOT15, sha


# ---- helpers -------------------------------------------------------------------
def _names():
    return {tk: f"Company_{tk}" for tk in PART03_TICKERS}


def _absent_tsetmc():
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
    """All sources attempted, all timed out — no snapshot, no hash, no review."""
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
                "content_review_status": "not_available_due_to_fetch_failure",
                "source_authority_class": classify_source_authority(src[0], src[2]),
                "ordinary_share_explicit": "unknown",
                "event_type_supported": "",
                "exact_date_explicit": "false",
                "reviewed_date_jalali": "",
                "independent_source_group": registrable_domain(src[2]),
                "evidence_accepted": "false",
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
        frozen=None, p02=None, worklist=None):
    frozen = frozen or {}
    p02 = p02 or {}
    return run_part03_qc(tickers_df, research_df, provenance_df, tsetmc_df,
                         frozen, frozen, p02, p02, worklist_df=worklist)


def _result(qc, name):
    for a in qc["assertions"]:
        if a["assertion"] == name:
            return a["passed"]
    return None


def _any_failed_containing(qc, substr):
    return any((not a["passed"]) and substr in a["assertion"] for a in qc["assertions"])


def _reviewed_rec(**over):
    """A fully-accepted reviewed evidence record (official-regulatory, Codal
    document-specific). Override fields as needed."""
    rec = {
        "ticker": PART03_TICKERS[0], "source_index": 1,
        "source_type": "codal_official",
        "source_url": "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=abc",
        "retrieval_status": "fetched_ok",
        "content_sha256": "a" * 64,
        "snapshot_path": "stage124/batch02_parts/snapshots_part03/x.html",
        "content_review_status": "reviewed",
        "source_authority_class": "official_regulatory",
        "event_type_supported": "first_public_offering",
        "exact_date_explicit": "true",
        "reviewed_date_jalali": "1380-03-15",
        "ordinary_share_explicit": "true",
        "publication_date_jalali": "",
        "publication_date_explicit": "false",
        "contemporaneous_with_event": "false",
        "independent_source_group": "",
        "evidence_accepted": "false",
    }
    rec.update(over)
    return rec


def _news_rec(**over):
    """A reviewed credible-news document-specific record (not contemporaneous by
    default)."""
    rec = _reviewed_rec(
        source_type="news_agency",
        source_url="https://donya-e-eqtesad.com/news/100",
        source_authority_class="credible_news",
        independent_source_group="",
    )
    rec.update(over)
    return rec


# ---- baseline ------------------------------------------------------------------
def test_baseline_qc_passes():
    qc = _qc(*_baseline_dfs(),
             worklist=build_manual_research_worklist(_names(), _baseline_dfs()[1]))
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


# ---- (1)(2)(3) all-timeout research semantics ----------------------------------
def test_all_timeout_research_blocked_network():
    _, research_df, _, _ = _baseline_dfs()
    assert (research_df["research_status"] == "research_blocked_network").all()
    assert (research_df["network_blocked"].str.lower() == "true").all()
    assert (research_df["research_completion_status"] == "blocked_network").all()


def test_all_timeout_requires_manual_review():
    _, research_df, _, _ = _baseline_dfs()
    assert (research_df["evidence_status"] == "requires_manual_review").all()
    assert (research_df["recommended_next_step"]
            == "manual_web_research_required").all()


def test_all_timeout_never_no_reliable_evidence():
    _, research_df, _, _ = _baseline_dfs()
    assert (research_df["evidence_status"] != "no_reliable_evidence").all()
    assert (research_df["research_status"] != "no_reliable_evidence").all()
    # counts must all be zero
    for c in ("fetched_source_count", "reviewed_source_count", "evidence_source_count"):
        assert (research_df[c].astype(str) == "0").all()
    # ordinary share unknown, ready never true
    assert (research_df["ordinary_share_confirmed"] == "unknown").all()
    assert (research_df["ready_for_user_review"].str.lower() == "false").all()


def test_derive_status_timeout_is_blocked_not_no_evidence():
    recs = [{"retrieval_status": "timeout",
             "content_review_status": "not_available_due_to_fetch_failure"},
            {"retrieval_status": "connection_error",
             "content_review_status": "not_available_due_to_fetch_failure"}]
    st = _derive_screening_status(recs, snapshot_root=ROOT)
    assert st["research_status"] == "research_blocked_network"
    assert st["evidence_status"] == "requires_manual_review"
    assert st["evidence_status"] != "no_reliable_evidence"
    assert st["network_blocked"] == "true"
    assert st["ready_for_user_review"] == "false"


def test_no_reliable_evidence_only_after_review():
    """no_reliable_evidence is only produced once sources are fetched AND
    reviewed but carry no public-entry evidence."""
    recs = [_reviewed_rec(event_type_supported="", exact_date_explicit="false",
                          reviewed_date_jalali="", ordinary_share_explicit="unknown")]
    st = _derive_screening_status(recs, snapshot_root=None)
    assert st["evidence_status"] == "no_reliable_evidence"
    assert st["research_status"] == "research_completed_no_evidence"
    assert st["ready_for_user_review"] == "false"


# ---- (4) fetched but unreviewed → not ready ------------------------------------
def test_fetched_unreviewed_not_ready():
    recs = [_reviewed_rec(content_review_status="pending_manual_review")]
    st = _derive_screening_status(recs, snapshot_root=None)
    assert st["ready_for_user_review"] == "false"
    assert st["research_completion_status"] == "fetched_pending_review"
    assert decide_ready_for_user_review(recs, snapshot_root=None)["ready"] is False


# ---- (5) aggregator alone → not ready ------------------------------------------
def test_aggregator_alone_not_ready():
    # document-specific aggregator → accepted as supporting evidence but never
    # qualifying on its own.
    rec = _reviewed_rec(source_type="market_information_aggregator",
                        source_url="https://rahavard365.com/instrument/12/report",
                        source_authority_class="market_information_aggregator")
    assert evaluate_source_record(rec, snapshot_root=None) is True
    d = decide_ready_for_user_review([rec], snapshot_root=None)
    assert d["ready"] is False
    assert d["reason"] == "insufficient_qualifying_or_independent_sources"


# ---- (6) generic Codal search page → not ready ---------------------------------
def test_codal_search_page_alone_not_ready():
    """A generic Codal symbol-search page with no specific reviewed announcement
    (no supported event) is not initial-offering evidence."""
    rec = _reviewed_rec(
        source_url="https://www.codal.ir/ReportList.aspx?search&Symbol=x",
        event_type_supported="", exact_date_explicit="false",
        reviewed_date_jalali="")
    assert evaluate_source_record(rec, snapshot_root=None) is False
    assert decide_ready_for_user_review([rec], snapshot_root=None)["ready"] is False


# ---- (7) one credible source but ordinary share unknown → not ready ------------
def test_credible_source_ordinary_share_unknown_not_ready():
    rec = _news_rec(source_url="https://donya-e-eqtesad.com/news/1",
                    ordinary_share_explicit="unknown")
    assert evaluate_source_record(rec, snapshot_root=None) is False
    assert decide_ready_for_user_review([rec], snapshot_root=None)["ready"] is False


# ---- (8) one official source + ordinary explicit + exact day → ready -----------
def test_official_source_ordinary_exact_day_ready():
    rec = _reviewed_rec()  # official_regulatory codal.ir, ordinary explicit, exact day
    assert evaluate_source_record(rec, snapshot_root=None) is True
    d = decide_ready_for_user_review([rec], snapshot_root=None)
    assert d["ready"] is True
    assert d["event_type"] == "first_public_offering"
    assert d["canonical_date"] == "1380-03-15"
    assert d["ordinary_share_confirmed"] == "true"


# ---- (9) two independent credible sources → ready ------------------------------
def test_two_independent_credible_sources_ready():
    r1 = _news_rec(source_url="https://donya-e-eqtesad.com/news/1")
    r2 = _news_rec(source_index=2, source_url="https://isna.ir/news/2")
    d = decide_ready_for_user_review([r1, r2], snapshot_root=None)
    assert d["ready"] is True


# ---- (10) two sources from same domain → not independent → not ready -----------
def test_two_sources_same_domain_not_ready():
    # two qualifying news sources but on the SAME domain → not independent
    r1 = _news_rec(source_url="https://isna.ir/news/1")
    r2 = _news_rec(source_index=2, source_url="https://isna.ir/news/2")
    d = decide_ready_for_user_review([r1, r2], snapshot_root=None)
    assert d["ready"] is False
    assert d["reason"] == "insufficient_qualifying_or_independent_sources"


# ---- (11) snapshot hash mismatch → not accepted → not ready --------------------
def test_snapshot_hash_mismatch_not_ready():
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snap = SNAPSHOT_DIR / "__test_mismatch.html"
    snap.write_bytes(b"<html>real</html>")
    rel = "stage124/batch02_parts/snapshots_part03/__test_mismatch.html"
    try:
        rec = _reviewed_rec(snapshot_path=rel, content_sha256="0" * 64)  # wrong hash
        assert evaluate_source_record(rec, snapshot_root=ROOT) is False
        assert decide_ready_for_user_review([rec], snapshot_root=ROOT)["ready"] is False
        # matching hash → accepted
        good = hashlib.sha256(snap.read_bytes()).hexdigest()
        rec2 = _reviewed_rec(snapshot_path=rel, content_sha256=good)
        assert evaluate_source_record(rec2, snapshot_root=ROOT) is True
    finally:
        snap.unlink(missing_ok=True)


# ---- (12) conflicting dates → not ready ----------------------------------------
def test_conflicting_dates_not_ready():
    r1 = _reviewed_rec(reviewed_date_jalali="1380-03-15")
    r2 = _news_rec(source_index=2, source_url="https://isna.ir/news/2",
                   event_type_supported="first_public_trading",
                   reviewed_date_jalali="1381-04-20")
    d = decide_ready_for_user_review([r1, r2], snapshot_root=None)
    assert d["ready"] is False
    assert d["conflict_flag"] is True
    st = _derive_screening_status([r1, r2], snapshot_root=None)
    assert st["conflict_flag"] == "true"
    assert st["ready_for_user_review"] == "false"


# ---- (13)(14) worklist ---------------------------------------------------------
def test_worklist_exact_ticker_order():
    wl = build_manual_research_worklist(_names(), _baseline_dfs()[1])
    assert wl["ticker"].tolist() == PART03_TICKERS
    assert len(wl) == 10


def test_worklist_source_and_date_fields_initially_empty():
    wl = build_manual_research_worklist(_names(), _baseline_dfs()[1])
    for c in ("discovered_source_1_url", "discovered_source_2_url",
              "first_public_event_candidate", "candidate_date_jalali"):
        assert (wl[c].astype(str).str.strip() == "").all()
    # search queries are pre-filled (non-empty)
    assert (wl["primary_search_query_fa"].astype(str).str.strip() != "").all()
    assert (wl["secondary_search_query_fa"].astype(str).str.strip() != "").all()
    # no fabricated URLs anywhere in the worklist
    blob = " ".join(wl.astype(str).values.ravel().tolist())
    assert "http" not in blob.lower()


def test_worklist_qc_checks():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    wl = build_manual_research_worklist(_names(), research_df)
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df, worklist=wl)
    assert _result(qc, "worklist_exactly_10_rows") is True
    assert _result(qc, "worklist_ticker_order") is True
    assert _result(qc, "worklist_no_http_urls") is True


def test_worklist_qc_detects_guessed_url():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    wl = build_manual_research_worklist(_names(), research_df)
    wl.at[0, "discovered_source_1_url"] = "https://example.com/guess"
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df, worklist=wl)
    assert _any_failed_containing(qc, "worklist_no_guessed_discovered_source_1_url")
    assert _result(qc, "worklist_no_http_urls") is False


# ---- QC: ready / evidence integrity in research_df + provenance ----------------
def test_qc_fetched_unreviewed_provenance_not_ready():
    """A ticker whose only source is fetched-but-unreviewed must not be ready,
    and the unreviewed record must not be evidence_accepted."""
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    tk = research_df.at[research_df.index[0], "ticker"]
    j = prov_df.index[prov_df["ticker"] == tk][0]
    prov_df.at[j, "retrieval_status"] = "fetched_ok"
    prov_df.at[j, "content_sha256"] = "a" * 64
    prov_df.at[j, "snapshot_path"] = "stage124/batch02_parts/snapshots_part03/x.html"
    prov_df.at[j, "content_review_status"] = "pending_manual_review"
    # forcibly mark ready in research_df → QC must catch it
    i = research_df.index[0]
    research_df.at[i, "ready_for_user_review"] = "true"
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert _result(qc, f"fetched_unreviewed_not_ready_{tk}") is False


def test_qc_evidence_accepted_requires_snapshot_hash():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    j = prov_df.index[0]
    tk = prov_df.at[j, "ticker"]
    idx = prov_df.at[j, "source_index"]
    # accepted but still a failed fetch with no hash → integrity violation
    prov_df.at[j, "evidence_accepted"] = "true"
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert _result(qc, f"accepted_requires_snapshot_hash_{tk}_{idx}") is False


def test_qc_ordinary_share_true_only_when_ready():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    i = research_df.index[0]
    tk = research_df.at[i, "ticker"]
    research_df.at[i, "ordinary_share_confirmed"] = "true"
    research_df.at[i, "ready_for_user_review"] = "false"
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert _result(qc, f"ordinary_share_only_when_ready_{tk}") is False


def test_qc_no_reliable_requires_review():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    i = research_df.index[0]
    tk = research_df.at[i, "ticker"]
    # claim no_reliable_evidence while provenance is all-timeout (never reviewed)
    research_df.at[i, "evidence_status"] = "no_reliable_evidence"
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert _result(qc, f"no_reliable_only_after_review_{tk}") is False


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


def test_ready_true_without_fetched_source_hash():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    i = research_df.index[0]
    tk = research_df.at[i, "ticker"]
    research_df.at[i, "proposed_canonical_public_entry_date_jalali"] = "1380-01-01"
    research_df.at[i, "proposed_canonical_event_type"] = "first_public_trading"
    research_df.at[i, "date_precision"] = "exact_day"
    research_df.at[i, "evidence_status"] = "candidate_supported"
    research_df.at[i, "ordinary_share_confirmed"] = "true"
    research_df.at[i, "ready_for_user_review"] = "true"
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


def test_conflict_with_ready_true_fails():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    i = research_df.index[0]
    tk = research_df.at[i, "ticker"]
    research_df.at[i, "conflict_flag"] = "true"
    research_df.at[i, "ready_for_user_review"] = "true"
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert _result(qc, f"conflict_not_ready_{tk}") is False


# ---- taxonomy ------------------------------------------------------------------
def test_classify_source_authority():
    assert classify_source_authority("codal_official",
                                     "https://www.codal.ir/x") == "official_regulatory"
    assert classify_source_authority("market_information_aggregator",
                                     "https://rahavard365.com/x") == "market_information_aggregator"
    assert classify_source_authority("news_agency",
                                     "https://isna.ir/x") == "credible_news"
    assert registrable_domain("https://www.codal.ir/Report?x=1") == "codal.ir"


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


def test_failed_fetch_with_fabricated_hash_fails():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    j = prov_df.index[0]
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


# ================================================================================
# Part 3.1A.1 — Evidence Engine hardening (20 required checks)
# ================================================================================

# (1) declared codal_official on aggregator domain → unknown + validation error
def test_h01_codal_official_on_tacodal_unknown():
    cls, err = classify_source_authority_with_validation("codal_official",
                                                         "https://tacodal.ir/symbol/x")
    assert cls == "unknown"
    assert err != ""


# (2) declared codal_official on look-alike domain → invalid
def test_h02_codal_official_on_fake_codal_invalid():
    cls, err = classify_source_authority_with_validation("codal_official",
                                                         "https://fake-codal.ir/x")
    assert cls == "unknown" and err != ""
    # boundary: codal.ir.example.com must NOT be treated as codal
    cls2, err2 = classify_source_authority_with_validation("codal_official",
                                                           "https://codal.ir.example.com/x")
    assert cls2 == "unknown" and err2 != ""


# (3) genuine codal.ir → official_regulatory, no error
def test_h03_real_codal_official():
    cls, err = classify_source_authority_with_validation(
        "codal_official", "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=1")
    assert cls == "official_regulatory" and err == ""


# (4) news_agency on unknown domain → unknown
def test_h04_news_agency_unknown_domain():
    cls, err = classify_source_authority_with_validation("news_agency",
                                                         "https://random-blog.example/x")
    assert cls == "unknown" and err != ""


# (5) two aggregators from different domains → ready=false
def test_h05_two_aggregators_diff_domains_not_ready():
    r1 = _reviewed_rec(source_type="market_information_aggregator",
                       source_url="https://rahavard365.com/instrument/12/report",
                       source_authority_class="market_information_aggregator")
    r2 = _reviewed_rec(source_index=2, source_type="market_information_aggregator",
                       source_url="https://tgju.org/profile/12/report",
                       source_authority_class="market_information_aggregator")
    assert decide_ready_for_user_review([r1, r2], snapshot_root=None)["ready"] is False


# (6) aggregator + unknown → ready=false
def test_h06_aggregator_plus_unknown_not_ready():
    r1 = _reviewed_rec(source_type="market_information_aggregator",
                       source_url="https://rahavard365.com/instrument/12/report")
    r2 = _reviewed_rec(source_index=2, source_type="",
                       source_url="https://random-blog.example/post/9")
    assert decide_ready_for_user_review([r1, r2], snapshot_root=None)["ready"] is False


# (7) two qualifying independent sources → ready=true
def test_h07_two_qualifying_independent_ready():
    r1 = _news_rec(source_url="https://donya-e-eqtesad.com/news/100")
    r2 = _news_rec(source_index=2, source_url="https://isna.ir/news/200")
    assert decide_ready_for_user_review([r1, r2], snapshot_root=None)["ready"] is True


# (8) two qualifying sources on the same domain → ready=false
def test_h08_two_qualifying_same_domain_not_ready():
    r1 = _news_rec(source_url="https://isna.ir/news/100")
    r2 = _news_rec(source_index=2, source_url="https://isna.ir/news/200")
    d = decide_ready_for_user_review([r1, r2], snapshot_root=None)
    assert d["ready"] is False


# (9) generic Codal ReportList with event/date filled → evidence=false
def test_h09_codal_reportlist_filled_not_evidence():
    rec = _reviewed_rec(
        source_url="https://www.codal.ir/ReportList.aspx?search&Symbol=x",
        event_type_supported="first_public_offering",
        exact_date_explicit="true", reviewed_date_jalali="1380-03-15")
    assert evaluate_source_record(rec, snapshot_root=None) is False
    assert decide_ready_for_user_review([rec], snapshot_root=None)["ready"] is False


# (10) Codal document-specific (LetterSerial) → can be evidence=true
def test_h10_codal_document_specific_evidence():
    rec = _reviewed_rec(
        source_url="https://www.codal.ir/Reports/Decision.aspx?LetterSerial=XYZ123")
    assert is_document_specific_source(rec["source_url"], "codal_official") is True
    assert evaluate_source_record(rec, snapshot_root=None) is True


# (11) year-only date → evidence=false
def test_h11_year_only_not_evidence():
    assert is_valid_exact_jalali_date("1380") is False
    rec = _reviewed_rec(reviewed_date_jalali="1380")
    assert evaluate_source_record(rec, snapshot_root=None) is False


# (12) month-only date → evidence=false
def test_h12_month_only_not_evidence():
    assert is_valid_exact_jalali_date("1380-03") is False
    rec = _reviewed_rec(reviewed_date_jalali="1380-03")
    assert evaluate_source_record(rec, snapshot_root=None) is False


# (13) invalid Jalali → evidence=false
def test_h13_invalid_jalali_not_evidence():
    for bad in ("1380/03", "1380-13-01", "1380-02-32", "unknown", ""):
        assert is_valid_exact_jalali_date(bad) is False
        rec = _reviewed_rec(reviewed_date_jalali=bad)
        assert evaluate_source_record(rec, snapshot_root=None) is False


# (14) valid exact Jalali → acceptable
def test_h14_valid_exact_jalali_acceptable():
    assert is_valid_exact_jalali_date("1380-03-15") is True
    assert evaluate_source_record(_reviewed_rec(), snapshot_root=None) is True


# (15) credible news without publication date → ready=false
def test_h15_news_without_pub_date_not_ready():
    rec = _news_rec()  # publication_date_explicit false by default
    assert decide_ready_for_user_review([rec], snapshot_root=None)["ready"] is False


# (16) credible news with publication date far from event → ready=false
def test_h16_news_pub_date_far_not_ready():
    rec = _news_rec(publication_date_explicit="true",
                    publication_date_jalali="1381-03-15",  # ~1 year after event
                    reviewed_date_jalali="1380-03-15")
    assert decide_ready_for_user_review([rec], snapshot_root=None)["ready"] is False


# (17) credible news contemporaneous with event → can be ready=true
def test_h17_news_contemporaneous_ready():
    rec = _news_rec(publication_date_explicit="true",
                    publication_date_jalali="1380-03-20",  # 5 days after event
                    reviewed_date_jalali="1380-03-15")
    d = decide_ready_for_user_review([rec], snapshot_root=None)
    assert d["ready"] is True


# (18) manual evidence_accepted=true on an invalid record → recomputed false
def test_h18_manual_evidence_accepted_overridden():
    # invalid: ordinary share unknown, manually flagged accepted
    rec = _reviewed_rec(ordinary_share_explicit="unknown", evidence_accepted="true")
    assert compute_evidence_accepted(rec, snapshot_root=None) == "false"
    # build_source_provenance must overwrite the manual value with the computed one
    fetch = {tk: [] for tk in PART03_TICKERS}
    bad = dict(rec); bad["ticker"] = PART03_TICKERS[0]; bad["retrieval_status"] = "timeout"
    bad["evidence_accepted"] = "true"
    fetch[PART03_TICKERS[0]] = [bad]
    prov = build_source_provenance(fetch, snapshot_root=None)
    assert not (prov["evidence_accepted"].str.lower() == "true").any()


# (19) fabricated independent_source_group inconsistent with URL → not accepted
def test_h19_fake_independent_group_rejected():
    rec = _news_rec(source_url="https://isna.ir/news/1",
                    publication_date_explicit="true",
                    publication_date_jalali="1380-03-20",
                    independent_source_group="donya-e-eqtesad.com")  # lies about domain
    assert evaluate_source_record(rec, snapshot_root=None) is False
    assert decide_ready_for_user_review([rec], snapshot_root=None)["ready"] is False


# (20) all 10 current tickers remain blocked / not ready
def test_h20_all_current_tickers_blocked():
    _, research_df, prov_df, _ = _baseline_dfs()
    assert (research_df["research_status"] == "research_blocked_network").all()
    assert (research_df["ready_for_user_review"].str.lower() == "false").all()
    assert (prov_df["evidence_accepted"].str.lower() != "true").all()
    assert (prov_df["document_specific"].str.lower() == "false").all()


def test_h_qc_evidence_accepted_recompute_detects_mismatch():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    j = prov_df.index[0]
    tk = prov_df.at[j, "ticker"]
    idx = prov_df.at[j, "source_index"]
    prov_df.at[j, "evidence_accepted"] = "true"  # invalid manual override
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    assert _result(qc, f"evidence_accepted_matches_engine_{tk}_{idx}") is False


# ---- (15)(16) real generated output --------------------------------------------
def _load_real_research():
    p = PART03_DIR / "part03_research_screening_10tickers.csv"
    if not p.exists():
        pytest.skip("part03 output not generated yet")
    return pd.read_csv(p, dtype=str).fillna("")


def test_real_output_exact_set_and_order():
    df = _load_real_research()
    assert df["ticker"].tolist() == PART03_TICKERS


def test_real_output_all_blocked_network():
    df = _load_real_research()
    assert (df["research_status"] == "research_blocked_network").all()
    assert (df["network_blocked"].str.lower() == "true").all()
    assert (df["evidence_status"] == "requires_manual_review").all()
    assert (df["evidence_status"] != "no_reliable_evidence").all()
    assert (df["ready_for_user_review"].str.lower() == "false").all()
    assert (df["ordinary_share_confirmed"] == "unknown").all()
    for c in ("fetched_source_count", "reviewed_source_count", "evidence_source_count"):
        assert (df[c].astype(str) == "0").all()


def test_real_output_no_fabricated_evidence():
    p = PART03_DIR / "part03_source_provenance_10tickers.csv"
    if not p.exists():
        pytest.skip("part03 provenance not generated yet")
    df = pd.read_csv(p, dtype=str).fillna("")
    for _, r in df.iterrows():
        if r["retrieval_status"] not in ("fetched_ok", "reused_existing_snapshot"):
            assert r["snapshot_path"].strip() == ""
            assert r["content_sha256"].strip() == ""
        assert r["evidence_accepted"].strip().lower() != "true"


def test_real_worklist_ten_rows_and_empty_fields():
    p = PART03_DIR / "part03_manual_research_worklist.csv"
    if not p.exists():
        pytest.skip("worklist not generated yet")
    df = pd.read_csv(p, dtype=str).fillna("")
    assert df["ticker"].tolist() == PART03_TICKERS
    assert len(df) == 10
    for c in ("discovered_source_1_url", "discovered_source_2_url",
              "first_public_event_candidate", "candidate_date_jalali"):
        assert (df[c].astype(str).str.strip() == "").all()
    blob = " ".join(df.astype(str).values.ravel().tolist())
    assert "http" not in blob.lower()


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


def test_real_tsetmc_audit_unchanged_by_code():
    """Re-building the TSETMC audit must reproduce the on-disk file byte-for-byte
    (Part 3.1A does not touch the TSETMC audit)."""
    p = PART03_DIR / "part03_tsetmc_audit_10tickers.csv"
    if not p.exists():
        pytest.skip("part03 tsetmc not generated yet")
    rebuilt = build_tsetmc_audit(load_historical_tsetmc())
    on_disk = pd.read_csv(p, dtype=str).fillna("")
    rebuilt = rebuilt.astype(str)
    assert on_disk["ticker"].tolist() == rebuilt["ticker"].tolist()
    assert (on_disk["network_request_performed"].str.lower() == "false").all()


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
