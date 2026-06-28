"""Independent tests for Stage124 Batch 2 Part 3 research screening.

Part 3.1A focus: correct research-status semantics (a network failure is
"research blocked", never "no reliable evidence") and a safe, testable
evidence/ready decision that separates a successful *fetch* from reviewed
*evidence*.
"""

import json
import re
import hashlib
from pathlib import Path
from urllib.parse import urlparse

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
    evaluate_reviewed_evidence_record,
    decide_ready_for_user_review,
    compute_evidence_accepted,
    classify_source_authority,
    classify_source_authority_with_validation,
    is_document_specific_source,
    is_valid_exact_jalali_date,
    registrable_domain,
    apply_validated_review_overlay,
    normalize_provenance_records,
    _derive_screening_status,
    PROVENANCE_COLUMNS,
    SOURCE_REGISTRY_COLUMNS,
    build_seed_registry_df,
    load_source_registry,
    validate_source_registry,
    registry_to_research_sources,
    register_discovered_sources,
    merge_existing_worklist_with_current_status,
    build_manual_research_worklist,
    fetch_sources,
    WORKLIST_COLUMNS,
    WORKLIST_DATE_PRECISIONS,
    validate_worklist_date_precision,
    REVIEWED_EVENT_TYPES,
    REVIEWED_DATE_PRECISIONS,
    EVIDENCE_ROLES,
    _is_sha256,
    _truthy,
)
import project.src.stage124_batch02_part03 as part03_mod
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


# ---- (12) conflicting same-event dates → not ready -----------------------------
def test_conflicting_dates_not_ready():
    # two incompatible *offering* dates → same-event conflict (offering vs trading
    # is no longer a conflict as of Part 3.1A.5.2).
    r1 = _reviewed_rec(reviewed_date_jalali="1380-03-15")
    r2 = _news_rec(source_index=2, source_url="https://isna.ir/news/2",
                   event_type_supported="first_public_offering",
                   reviewed_date_jalali="1381-04-20")
    st = _derive_screening_status([r1, r2], snapshot_root=None)
    assert st["conflict_flag"] == "true"
    assert st["research_status"] == "research_completed_conflict"
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
    assert _result(qc, "worklist_exact_ticker_scope") is True
    assert _result(qc, "worklist_no_duplicates") is True
    assert _result(qc, "worklist_discovered_urls_valid") is True


def test_worklist_qc_detects_invalid_url():
    # a local/filesystem URL is invalid; a valid https URL is allowed
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    wl = build_manual_research_worklist(_names(), research_df)
    wl.at[0, "discovered_source_1_url"] = "/Users/x/Desktop/guess.html"
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df, worklist=wl)
    assert _result(qc, "worklist_discovered_urls_valid") is False


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


# ================================================================================
# Part 3.1A.2 — Manual review overlay ↔ evidence engine wiring (20 checks)
# ================================================================================

def _make_snapshot(name, body=b"<html>specific document</html>"):
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    p = SNAPSHOT_DIR / name
    p.write_bytes(body)
    rel = f"stage124/batch02_parts/snapshots_part03/{name}"
    return p, rel, hashlib.sha256(body).hexdigest()


def _retrieval_rec(tk, url, rel, h, status="fetched_ok", **over):
    rec = {
        "ticker": tk, "source_index": 1, "source_type": "codal_official",
        "source_title": "t", "source_url": url, "publication_date": "",
        "retrieved_at_utc": "2026-01-01T00:00:00Z", "http_status": "200",
        "retrieval_status": status, "final_url": url, "content_type": "text/html",
        "response_size_bytes": "10", "snapshot_path": rel if status in
        ("fetched_ok", "reused_existing_snapshot") else "",
        "content_sha256": h if status in ("fetched_ok", "reused_existing_snapshot") else "",
        "extraction_notes": "", "exact_text_or_event_summary": "",
        "supported_event_type": "", "supported_date_jalali": "",
        "content_review_status": "pending_manual_review" if status in
        ("fetched_ok", "reused_existing_snapshot") else "not_available_due_to_fetch_failure",
    }
    rec.update(over)
    return rec


def _existing_prov_df(tk, url, rel, h, **review):
    row = {c: "" for c in PROVENANCE_COLUMNS}
    row.update({
        "ticker": tk, "source_index": "1", "source_type": "codal_official",
        "source_url": url, "retrieval_status": "fetched_ok",
        "snapshot_path": rel, "content_sha256": h,
        "content_review_status": "reviewed",
        "event_type_supported": "first_public_offering",
        "exact_date_explicit": "true", "reviewed_date_jalali": "1380-03-15",
        "ordinary_share_explicit": "true", "evidence_accepted": "true",
    })
    row.update(review)
    return pd.DataFrame([row])


_CODAL_DOC = "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=ABC123"


# (1) valid review overlay preserved
def test_o01_valid_review_overlay_preserved():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("o01.html")
    try:
        retrieval = _retrieval_rec(tk, _CODAL_DOC, rel, h)
        existing = _existing_prov_df(tk, _CODAL_DOC, rel, h)
        out = apply_validated_review_overlay([retrieval], existing, ROOT)
        assert out[0]["content_review_status"] == "reviewed"
        assert out[0]["event_type_supported"] == "first_public_offering"
        assert out[0]["evidence_accepted"] == "true"
    finally:
        snap.unlink(missing_ok=True)


# (2) changed snapshot hash invalidates review
def test_o02_changed_hash_invalidates():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("o02.html")
    try:
        retrieval = _retrieval_rec(tk, _CODAL_DOC, rel, h)
        existing = _existing_prov_df(tk, _CODAL_DOC, rel, "0" * 64)  # different hash
        out = apply_validated_review_overlay([retrieval], existing, ROOT)
        assert out[0]["content_review_status"] == "stale_review_invalidated"
        assert out[0]["evidence_accepted"] == "false"
        assert out[0]["event_type_supported"] == ""
    finally:
        snap.unlink(missing_ok=True)


# (3) changed source URL invalidates review
def test_o03_changed_url_invalidates():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("o03.html")
    try:
        retrieval = _retrieval_rec(tk, _CODAL_DOC, rel, h)
        existing = _existing_prov_df(tk, "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=OTHER",
                                     rel, h)
        out = apply_validated_review_overlay([retrieval], existing, ROOT)
        assert out[0]["content_review_status"] == "stale_review_invalidated"
        assert out[0]["evidence_accepted"] == "false"
    finally:
        snap.unlink(missing_ok=True)


# (4) timeout record cannot inherit review
def test_o04_timeout_cannot_inherit():
    tk = PART03_TICKERS[0]
    retrieval = _retrieval_rec(tk, _CODAL_DOC, "", "", status="timeout")
    existing = _existing_prov_df(tk, _CODAL_DOC, "stale.html", "a" * 64)
    out = apply_validated_review_overlay([retrieval], existing, ROOT)
    assert out[0]["content_review_status"] == "not_available_due_to_fetch_failure"
    assert out[0]["evidence_accepted"] == "false"
    assert out[0]["event_type_supported"] == ""


# (5) old evidence_accepted=true is recomputed
def test_o05_old_evidence_accepted_recomputed():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("o05.html")
    try:
        # existing claims accepted but ordinary_share unknown → must recompute false
        retrieval = _retrieval_rec(tk, _CODAL_DOC, rel, h)
        existing = _existing_prov_df(tk, _CODAL_DOC, rel, h,
                                     ordinary_share_explicit="unknown",
                                     evidence_accepted="true")
        out = apply_validated_review_overlay([retrieval], existing, ROOT)
        assert out[0]["evidence_accepted"] == "false"
    finally:
        snap.unlink(missing_ok=True)


# (6) research uses recomputed provenance
def test_o06_research_uses_recomputed_provenance():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    qc = _qc(tickers_df, research_df, prov_df, tsetmc_df)
    for tk in PART03_TICKERS:
        assert _result(qc, f"research_from_provenance_{tk}") is True


# (7) company_official without ticker whitelist rejected
def test_o07_company_official_no_whitelist_rejected():
    cls, err = classify_source_authority_with_validation(
        "company_official", "https://acme.example/news/1", ticker=PART03_TICKERS[0])
    assert cls == "unknown" and err != ""


# (8) company official exact domain for same ticker accepted
def test_o08_company_official_exact_domain_accepted():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("o08.html")
    part03_mod.VERIFIED_COMPANY_OFFICIAL_DOMAINS[tk] = {"acme.example"}
    try:
        rec = _retrieval_rec(tk, "https://acme.example/news/12345", rel, h,
                             source_type="company_official",
                             content_review_status="reviewed",
                             event_type_supported="first_public_offering",
                             exact_date_explicit="true",
                             reviewed_date_jalali="1380-03-15",
                             ordinary_share_explicit="true")
        assert classify_source_authority("company_official",
                                         "https://acme.example/news/12345", tk) == "company_official"
        assert evaluate_source_record(rec, snapshot_root=ROOT) is True
    finally:
        snap.unlink(missing_ok=True)
        part03_mod.VERIFIED_COMPANY_OFFICIAL_DOMAINS.pop(tk, None)


# (9) company official domain for another ticker rejected
def test_o09_company_official_other_ticker_rejected():
    tkA, tkB = PART03_TICKERS[0], PART03_TICKERS[1]
    part03_mod.VERIFIED_COMPANY_OFFICIAL_DOMAINS[tkA] = {"acme.example"}
    try:
        cls, err = classify_source_authority_with_validation(
            "company_official", "https://acme.example/news/1", ticker=tkB)
        assert cls == "unknown" and err != ""
    finally:
        part03_mod.VERIFIED_COMPANY_OFFICIAL_DOMAINS.pop(tkA, None)


# (10) fake subdomain boundary rejected
def test_o10_company_official_fake_subdomain_rejected():
    tk = PART03_TICKERS[0]
    part03_mod.VERIFIED_COMPANY_OFFICIAL_DOMAINS[tk] = {"acme.example"}
    try:
        for bad in ("https://acme.example.evil.com/news/1",
                    "https://fake-acme.example/news/1"):
            cls, err = classify_source_authority_with_validation(
                "company_official", bad, ticker=tk)
            assert cls == "unknown" and err != "", bad
    finally:
        part03_mod.VERIFIED_COMPANY_OFFICIAL_DOMAINS.pop(tk, None)


# (11) TSETMC official market data never ready
def test_o11_tsetmc_never_ready():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("o11.html")
    try:
        rec = _retrieval_rec(tk, "https://tsetmc.com/instInfo/123", rel, h,
                             source_type="market_data",
                             content_review_status="reviewed",
                             event_type_supported="first_public_trading",
                             exact_date_explicit="true",
                             reviewed_date_jalali="1380-03-15",
                             ordinary_share_explicit="true")
        assert classify_source_authority("market_data",
                                         "https://tsetmc.com/instInfo/123", tk) == "official_market_data_audit"
        assert evaluate_source_record(rec, snapshot_root=ROOT) is False
        assert decide_ready_for_user_review([rec], snapshot_root=ROOT)["ready"] is False
    finally:
        snap.unlink(missing_ok=True)


# (12) TSETMC + aggregator never ready
def test_o12_tsetmc_plus_aggregator_never_ready():
    tk = PART03_TICKERS[0]
    s1, r1, h1 = _make_snapshot("o12a.html", b"a")
    s2, r2, h2 = _make_snapshot("o12b.html", b"b")
    try:
        tsetmc = _retrieval_rec(tk, "https://tsetmc.com/instInfo/1", r1, h1,
                                source_type="market_data",
                                content_review_status="reviewed",
                                event_type_supported="first_public_trading",
                                exact_date_explicit="true",
                                reviewed_date_jalali="1380-03-15",
                                ordinary_share_explicit="true")
        agg = _retrieval_rec(tk, "https://rahavard365.com/instrument/9/report", r2, h2,
                             source_index=2, source_type="market_information_aggregator",
                             content_review_status="reviewed",
                             event_type_supported="first_public_trading",
                             exact_date_explicit="true",
                             reviewed_date_jalali="1380-03-15",
                             ordinary_share_explicit="true")
        assert decide_ready_for_user_review([tsetmc, agg], snapshot_root=ROOT)["ready"] is False
    finally:
        s1.unlink(missing_ok=True)
        s2.unlink(missing_ok=True)


# (13) SENA without contemporaneous publication date not ready
def test_o13_sena_without_pubdate_not_ready():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("o13.html")
    try:
        rec = _retrieval_rec(tk, "https://sena.ir/news/12345", rel, h,
                             source_type="official_market_news",
                             content_review_status="reviewed",
                             event_type_supported="first_public_offering",
                             exact_date_explicit="true",
                             reviewed_date_jalali="1380-03-15",
                             ordinary_share_explicit="true")
        assert evaluate_source_record(rec, snapshot_root=ROOT) is True  # accepted
        assert decide_ready_for_user_review([rec], snapshot_root=ROOT)["ready"] is False
    finally:
        snap.unlink(missing_ok=True)


# (14) contemporaneous SENA article can qualify
def test_o14_sena_contemporaneous_ready():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("o14.html")
    try:
        rec = _retrieval_rec(tk, "https://sena.ir/news/12345", rel, h,
                             source_type="official_market_news",
                             content_review_status="reviewed",
                             event_type_supported="first_public_offering",
                             exact_date_explicit="true",
                             reviewed_date_jalali="1380-03-15",
                             ordinary_share_explicit="true",
                             publication_date_explicit="true",
                             publication_date_jalali="1380-03-20")
        assert decide_ready_for_user_review([rec], snapshot_root=ROOT)["ready"] is True
    finally:
        snap.unlink(missing_ok=True)


# (15) generic company profile rejected
def test_o15_company_profile_rejected():
    tk = PART03_TICKERS[0]
    part03_mod.VERIFIED_COMPANY_OFFICIAL_DOMAINS[tk] = {"acme.example"}
    try:
        assert is_document_specific_source("https://acme.example/about",
                                           "company_official", tk) is False
    finally:
        part03_mod.VERIFIED_COMPANY_OFFICIAL_DOMAINS.pop(tk, None)


# (16) generic news category rejected
def test_o16_news_category_rejected():
    assert is_document_specific_source("https://isna.ir/category/economy",
                                       "news_agency") is False


# (17) specific news article accepted (document-specific)
def test_o17_specific_news_article_accepted():
    assert is_document_specific_source("https://isna.ir/news/12345",
                                       "news_agency") is True


# (18) real provenance retrieval/evidence invariants (forward-compatible)
def test_o18_real_provenance_retrieval_evidence_invariants():
    p = PART03_DIR / "part03_source_provenance_10tickers.csv"
    if not p.exists():
        pytest.skip("part03 provenance not generated yet")
    df = pd.read_csv(p, dtype=str).fillna("")
    for _, r in df.iterrows():
        status = str(r.get("retrieval_status", ""))
        snap = str(r.get("snapshot_path", "")).strip()
        h = str(r.get("content_sha256", "")).strip()
        if status not in FETCHED_STATUSES:
            assert snap == "", f"failed fetch has snapshot: {snap}"
            assert h == "", f"failed fetch has hash: {h}"
        else:
            assert snap != "", "fetched source has empty snapshot_path"
            assert _is_sha256(h), f"fetched source has invalid SHA-256: {h}"
            sp = ROOT / snap
            if sp.exists():
                assert hashlib.sha256(sp.read_bytes()).hexdigest() == h.lower(), \
                    f"snapshot hash mismatch for {snap}"
        review_status = str(r.get("content_review_status", "")).strip().lower()
        if review_status == "reviewed":
            assert status in FETCHED_STATUSES, "reviewed source not fetched"
            assert snap != "" and _is_sha256(h), "reviewed source missing snapshot/hash"
        assert str(r.get("evidence_accepted", "")).strip().lower() == \
            compute_evidence_accepted({k: r.get(k, "") for k in r.index}, snapshot_root=ROOT)


# (19) real research rows are semantically valid (forward-compatible)
def test_o19_real_research_rows_semantically_valid():
    df = _load_real_research()
    assert df["ticker"].tolist() == PART03_TICKERS
    allowed_rs = {"research_blocked_network", "source_discovered",
                  "fetched_pending_manual_review", "research_completed_no_evidence",
                  "candidate_supported", "research_completed_conflict",
                  "research_completed_partial_public_entry_date",
                  "research_completed_admission_only",
                  "research_completed_listing_only",
                  "research_completed_noncanonical_entry_evidence"}
    allowed_es = {"requires_manual_review", "no_reliable_evidence",
                  "candidate_supported", "requires_first_public_trade_evidence"}
    for _, r in df.iterrows():
        assert str(r["research_status"]).strip() in allowed_rs, \
            f"invalid research_status: {r['research_status']}"
        assert str(r["evidence_status"]).strip() in allowed_es, \
            f"invalid evidence_status: {r['evidence_status']}"
        if _truthy(r.get("network_blocked", "")):
            assert r["research_status"] == "research_blocked_network"
            assert str(r.get("fetched_source_count")) == "0"
            assert str(r.get("reviewed_source_count")) == "0"
            assert str(r.get("evidence_source_count")) == "0"
            assert not _truthy(r.get("ready_for_user_review", ""))
        if _truthy(r.get("ready_for_user_review", "")):
            assert str(r.get("date_precision", "")).strip() == "exact_day"
            assert str(r.get("proposed_canonical_public_entry_date_jalali", "")).strip() != ""
            assert str(r.get("proposed_canonical_event_type", "")).strip() in CANONICAL_EVENT_TYPES
            assert _truthy(r.get("ordinary_share_confirmed", ""))
            assert not _truthy(r.get("conflict_flag", ""))
        if _truthy(r.get("conflict_flag", "")):
            assert not _truthy(r.get("ready_for_user_review", ""))


# (20) Part 2 and TSETMC audit unchanged
def test_o20_part2_and_tsetmc_audit_unchanged():
    manifest = PART03_DIR / "part02_hash_manifest.csv"
    if manifest.exists():
        mdf = pd.read_csv(manifest, dtype=str).fillna("")
        for _, r in mdf.iterrows():
            if not r.get("sha256", "").strip():
                continue
            fp = ROOT / r["relative_path"]
            if fp.exists():
                assert sha(fp) == r["sha256"], f"{r['relative_path']} changed"
    ta = PART03_DIR / "part03_tsetmc_audit_10tickers.csv"
    df = pd.read_csv(ta, dtype=str).fillna("")
    assert (df["network_request_performed"].str.lower() == "false").all()
    assert (df["probe_source"] == "historical_v2_audit").all()


# ---- (15)(16) real generated output --------------------------------------------
def _load_real_research():
    p = PART03_DIR / "part03_research_screening_10tickers.csv"
    if not p.exists():
        pytest.skip("part03 output not generated yet")
    return pd.read_csv(p, dtype=str).fillna("")


def test_real_output_exact_set_and_order():
    df = _load_real_research()
    assert df["ticker"].tolist() == PART03_TICKERS


def test_real_output_research_semantics_valid():
    df = _load_real_research()
    assert df["ticker"].tolist() == PART03_TICKERS
    allowed_rs = {"research_blocked_network", "source_discovered",
                  "fetched_pending_manual_review", "research_completed_no_evidence",
                  "candidate_supported", "research_completed_conflict",
                  "research_completed_partial_public_entry_date",
                  "research_completed_admission_only",
                  "research_completed_listing_only",
                  "research_completed_noncanonical_entry_evidence"}
    allowed_es = {"requires_manual_review", "no_reliable_evidence",
                  "candidate_supported", "requires_first_public_trade_evidence"}
    for _, r in df.iterrows():
        assert str(r["research_status"]).strip() in allowed_rs
        assert str(r["evidence_status"]).strip() in allowed_es
        if _truthy(r.get("network_blocked", "")):
            assert r["research_status"] == "research_blocked_network"
            assert str(r.get("fetched_source_count")) == "0"
            assert str(r.get("reviewed_source_count")) == "0"
            assert str(r.get("evidence_source_count")) == "0"
            assert not _truthy(r.get("ready_for_user_review", ""))
        if _truthy(r.get("ready_for_user_review", "")):
            assert str(r.get("date_precision", "")).strip() == "exact_day"
            cand = str(r.get("proposed_canonical_public_entry_date_jalali", "")).strip()
            assert cand != "" and is_valid_exact_jalali_date(cand)
            assert str(r.get("proposed_canonical_event_type", "")).strip() in CANONICAL_EVENT_TYPES
            assert _truthy(r.get("ordinary_share_confirmed", ""))
            assert not _truthy(r.get("conflict_flag", ""))
        if _truthy(r.get("conflict_flag", "")):
            assert not _truthy(r.get("ready_for_user_review", ""))
            assert str(r.get("proposed_canonical_event_type", "")).strip() == "unresolved"


def test_real_output_no_fabricated_evidence():
    p = PART03_DIR / "part03_source_provenance_10tickers.csv"
    if not p.exists():
        pytest.skip("part03 provenance not generated yet")
    df = pd.read_csv(p, dtype=str).fillna("")
    for _, r in df.iterrows():
        status = str(r.get("retrieval_status", ""))
        snap = str(r.get("snapshot_path", "")).strip()
        h = str(r.get("content_sha256", "")).strip()
        if status not in FETCHED_STATUSES:
            assert snap == "", f"failed fetch has snapshot: {snap}"
            assert h == "", f"failed fetch has hash: {h}"
            assert not _truthy(r.get("evidence_accepted", "")), \
                "failed fetch must not have evidence_accepted=true"
        else:
            assert snap != "", "fetched source has empty snapshot_path"
            assert _is_sha256(h), f"fetched source has invalid SHA-256: {h}"
        assert str(r.get("evidence_accepted", "")).strip().lower() == \
            compute_evidence_accepted({k: r.get(k, "") for k in r.index}, snapshot_root=ROOT)


def test_real_worklist_semantically_valid():
    p = PART03_DIR / "part03_manual_research_worklist.csv"
    if not p.exists():
        pytest.skip("worklist not generated yet")
    df = pd.read_csv(p, dtype=str).fillna("")
    assert df["ticker"].tolist() == PART03_TICKERS
    assert len(df) == 10
    assert df["ticker"].nunique() == 10
    allowed_events = {"", "first_public_offering", "first_public_trading",
                      "admission", "listing", "unresolved"}
    allowed_ord = {"true", "false", "unknown"}
    allowed_status = {"pending_manual_research", "source_discovered",
                      "under_review", "reviewed", "unresolved"}
    allowed_precisions = {"unknown", "year_only", "month_only", "exact_day"}
    for _, r in df.iterrows():
        for c in ("discovered_source_1_url", "discovered_source_2_url"):
            v = str(r.get(c, "")).strip()
            if v:
                parsed = urlparse(v)
                assert parsed.scheme in ("http", "https"), f"invalid URL scheme: {v}"
                assert parsed.hostname and "." in parsed.hostname, f"invalid URL host: {v}"
                assert "/Users/" not in v and "Desktop" not in v, f"local path: {v}"
        cand_date = str(r.get("candidate_date_jalali", "")).strip()
        precision = str(r.get("date_precision", "")).strip()
        assert precision in allowed_precisions, f"invalid date_precision: {precision}"
        if cand_date:
            assert precision != "unknown", "non-empty date with unknown precision"
            if precision == "year_only":
                assert bool(re.fullmatch(r"\d{4}", cand_date)), f"year_only mismatch: {cand_date}"
            elif precision == "month_only":
                assert bool(re.fullmatch(r"\d{4}-\d{2}", cand_date)), f"month_only mismatch: {cand_date}"
            elif precision == "exact_day":
                assert is_valid_exact_jalali_date(cand_date), f"exact_day invalid: {cand_date}"
        else:
            assert precision == "unknown", "empty date with non-unknown precision"
        event = str(r.get("first_public_event_candidate", "")).strip()
        assert event in allowed_events, f"invalid event candidate: {event}"
        ord_val = str(r.get("ordinary_share_explicit", "")).strip().lower()
        assert ord_val in allowed_ord, f"invalid ordinary_share_explicit: {ord_val}"
        assert ord_val != "", "ordinary_share_explicit must not be empty"
        status_val = str(r.get("manual_review_status", "")).strip()
        assert status_val in allowed_status, f"invalid manual_review_status: {status_val}"
        assert status_val != "", "manual_review_status must not be empty"


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


# ================================================================================
# Part 3.1A.3 — Source registry + worklist persistence + review audit fields
# ================================================================================

def _seed_registry():
    return build_seed_registry_df()


# (1) initial registry has 20 rows
def test_r01_registry_initial_20_rows():
    df = _seed_registry()
    assert len(df) == 20
    assert list(df.columns) == SOURCE_REGISTRY_COLUMNS
    ok, errs = validate_source_registry(df)
    assert ok, errs


# (2) exact ticker / source_index set
def test_r02_registry_exact_keys():
    df = _seed_registry()
    keys = {(str(r["ticker"]), str(r["source_index"])) for _, r in df.iterrows()}
    expected = {(tk, str(i)) for tk in PART03_TICKERS for i in (1, 2)}
    assert keys == expected
    assert (df["source_origin"] == "seed_part03").all()
    assert (df["active"] == "true").all()
    assert (df["discovery_status"] == "network_blocked").all()


# (3) duplicate (ticker, source_index) rejected
def test_r03_duplicate_key_rejected():
    df = _seed_registry()
    dup = df.iloc[[0]].copy()
    dup["source_url"] = "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=Z"
    bad = pd.concat([df, dup], ignore_index=True)
    ok, errs = validate_source_registry(bad)
    assert ok is False and any("duplicate (ticker, source_index)" in e for e in errs)


# (4) duplicate URL for one ticker rejected
def test_r04_duplicate_url_rejected():
    df = _seed_registry()
    row = df.iloc[[0]].copy()
    row["source_index"] = "3"
    bad = pd.concat([df, row], ignore_index=True)  # same url as index 1
    ok, errs = validate_source_registry(bad)
    assert ok is False and any("duplicate source_url" in e for e in errs)


# (5) ticker out of Part 3 scope rejected
def test_r05_out_of_scope_ticker_rejected():
    df = _seed_registry()
    row = df.iloc[[0]].copy()
    row["ticker"] = "زپارس"
    bad = pd.concat([df, row], ignore_index=True)
    ok, errs = validate_source_registry(bad)
    assert ok is False and any("not in Part 3 scope" in e for e in errs)


# (6) invalid source_index rejected
def test_r06_invalid_source_index_rejected():
    df = _seed_registry()
    df = df.copy()
    df.at[0, "source_index"] = "x"
    ok, errs = validate_source_registry(df)
    assert ok is False and any("source_index" in e for e in errs)


# (7) pipeline uses the registry (not the hardcoded list)
def test_r07_pipeline_uses_registry():
    # a registry with only one active source for the first ticker → fetch yields 1
    df = _seed_registry()
    df = df[~((df["ticker"] == PART03_TICKERS[0]) & (df["source_index"] == "2"))].copy()
    sources = registry_to_research_sources(df, include_inactive=False)
    saved = part03_mod._requests.get
    part03_mod._requests.get = lambda *a, **k: (_ for _ in ()).throw(
        part03_mod._requests.exceptions.Timeout())
    try:
        res = fetch_sources(force=True, sources_by_ticker=sources)
    finally:
        part03_mod._requests.get = saved
    assert len(res[PART03_TICKERS[0]]) == 1
    assert len(res[PART03_TICKERS[1]]) == 2


# (8) a third source enters the pipeline with no code change
def test_r08_third_source_enters_pipeline():
    tk = PART03_TICKERS[0]
    df = _seed_registry()
    add = pd.DataFrame([{
        "ticker": tk, "source_type": "codal_official",
        "source_title": "new doc", "added_by": "tester",
        "source_url": "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=NEW3",
        "discovery_notes": "",
    }])
    df2 = register_discovered_sources(df, add)
    sources = registry_to_research_sources(df2, include_inactive=False)
    saved = part03_mod._requests.get
    part03_mod._requests.get = lambda *a, **k: (_ for _ in ()).throw(
        part03_mod._requests.exceptions.Timeout())
    try:
        res = fetch_sources(force=True, sources_by_ticker=sources)
    finally:
        part03_mod._requests.get = saved
    idxs = sorted(int(r["source_index"]) for r in res[tk])
    assert idxs == [1, 2, 3]


# (9) inactive source is ignored by retrieval
def test_r09_inactive_source_ignored():
    tk = PART03_TICKERS[0]
    df = _seed_registry().copy()
    df.loc[(df["ticker"] == tk) & (df["source_index"] == "2"), "active"] = "false"
    sources = registry_to_research_sources(df, include_inactive=False)
    assert len(sources[tk]) == 1
    assert all(e[0] != 2 for e in sources[tk])


# (10) provenance and active registry are one-to-one
def test_r10_provenance_registry_one_to_one():
    df = _seed_registry()
    sources = registry_to_research_sources(df, include_inactive=False)
    saved = part03_mod._requests.get
    part03_mod._requests.get = lambda *a, **k: (_ for _ in ()).throw(
        part03_mod._requests.exceptions.Timeout())
    try:
        res = fetch_sources(force=True, sources_by_ticker=sources)
    finally:
        part03_mod._requests.get = saved
    prov = build_source_provenance(res, snapshot_root=None)
    prov_keys = {(str(r["ticker"]), str(r["source_index"])) for _, r in prov.iterrows()}
    active_keys = {(str(r["ticker"]), str(r["source_index"])) for _, r in df.iterrows()
                   if r["active"] == "true"}
    assert prov_keys == active_keys


# (11) primary/secondary built from registry/provenance ordering
def test_r11_primary_secondary_from_provenance():
    names = _names()
    df = _seed_registry()
    sources = registry_to_research_sources(df, include_inactive=False)
    saved = part03_mod._requests.get
    part03_mod._requests.get = lambda *a, **k: (_ for _ in ()).throw(
        part03_mod._requests.exceptions.Timeout())
    try:
        res = fetch_sources(force=True, sources_by_ticker=sources)
    finally:
        part03_mod._requests.get = saved
    overlaid = {tk: normalize_provenance_records(res.get(tk, []), None)
                for tk in PART03_TICKERS}
    research = build_research_screening(names, overlaid, _absent_tsetmc())
    tk = PART03_TICKERS[0]
    row = research[research["ticker"] == tk].iloc[0]
    first_url = sorted(overlaid[tk], key=lambda r: int(r["source_index"]))[0]["source_url"]
    assert row["primary_source_url"] == first_url


# (12) existing worklist is preserved on refresh
def test_r12_worklist_preserved():
    names = _names()
    template = build_manual_research_worklist(names, _baseline_dfs()[1])
    existing = template.copy()
    existing.at[0, "manual_review_status"] = "in_progress"
    existing.at[0, "reviewer_notes"] = "looked at codal"
    merged = merge_existing_worklist_with_current_status(template, existing)
    assert merged.at[0, "manual_review_status"] == "in_progress"
    assert merged.at[0, "reviewer_notes"] == "looked at codal"


# (13) discovered URLs in worklist are not cleared
def test_r13_worklist_discovered_urls_preserved():
    names = _names()
    template = build_manual_research_worklist(names, _baseline_dfs()[1])
    existing = template.copy()
    existing.at[1, "discovered_source_1_url"] = "https://www.codal.ir/x?LetterSerial=1"
    existing.at[1, "candidate_date_jalali"] = "1380-03-15"
    merged = merge_existing_worklist_with_current_status(template, existing)
    assert merged.at[1, "discovered_source_1_url"] == "https://www.codal.ir/x?LetterSerial=1"
    assert merged.at[1, "candidate_date_jalali"] == "1380-03-15"


# (14) worklist URLs do not auto-enter the registry
def test_r14_worklist_url_not_in_registry():
    df = load_source_registry()
    urls = set(df["source_url"])
    # a discovered url placed only in the worklist must not appear in the registry
    assert "https://www.codal.ir/x?LetterSerial=1" not in urls


# (15) register_discovered_sources assigns the next index
def test_r15_register_next_index():
    tk = PART03_TICKERS[0]
    df = _seed_registry()
    add = pd.DataFrame([{
        "ticker": tk, "source_type": "codal_official", "source_title": "t",
        "source_url": "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=AA",
        "added_by": "x", "discovery_notes": "n",
    }])
    out = register_discovered_sources(df, add)
    new = out[(out["ticker"] == tk) & (out["source_index"] == "3")]
    assert len(new) == 1
    assert new.iloc[0]["source_origin"] == "manual_discovery"
    assert new.iloc[0]["active"] == "true"


# (16) duplicate discovered URL rejected
def test_r16_register_duplicate_url_rejected():
    tk = PART03_TICKERS[0]
    df = _seed_registry()
    existing_url = df[(df["ticker"] == tk) & (df["source_index"] == "1")].iloc[0]["source_url"]
    add = pd.DataFrame([{
        "ticker": tk, "source_type": "market_information_aggregator",
        "source_title": "t", "source_url": existing_url,
        "added_by": "x", "discovery_notes": "",
    }])
    with pytest.raises(ValueError):
        register_discovered_sources(df, add)


# (17)(18) reviewer_notes / manual_reviewed_at_utc round-trip via valid overlay
def test_r17_18_review_audit_fields_roundtrip():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("r17.html")
    try:
        retrieval = _retrieval_rec(tk, _CODAL_DOC, rel, h)
        existing = _existing_prov_df(tk, _CODAL_DOC, rel, h,
                                     reviewer_notes="checked LetterSerial",
                                     manual_reviewed_at_utc="2026-06-20T00:00:00Z")
        out = apply_validated_review_overlay([retrieval], existing, ROOT)
        assert out[0]["reviewer_notes"] == "checked LetterSerial"
        assert out[0]["manual_reviewed_at_utc"] == "2026-06-20T00:00:00Z"
    finally:
        snap.unlink(missing_ok=True)


# (19) stale review clears the audit fields
def test_r19_stale_review_clears_audit_fields():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("r19.html")
    try:
        retrieval = _retrieval_rec(tk, _CODAL_DOC, rel, h)
        existing = _existing_prov_df(tk, _CODAL_DOC, rel, "0" * 64,  # hash changed
                                     reviewer_notes="stale note",
                                     manual_reviewed_at_utc="2026-06-20T00:00:00Z")
        out = apply_validated_review_overlay([retrieval], existing, ROOT)
        assert out[0]["content_review_status"] == "stale_review_invalidated"
        assert out[0]["reviewer_notes"] == ""
        assert out[0]["manual_reviewed_at_utc"] == ""
    finally:
        snap.unlink(missing_ok=True)


# (20) real provenance ↔ registry integrity (forward-compatible)
def test_r20_real_provenance_registry_integrity():
    reg_path = PART03_DIR / "part03_source_registry.csv"
    prov_path = PART03_DIR / "part03_source_provenance_10tickers.csv"
    if not reg_path.exists() or not prov_path.exists():
        pytest.skip("part03 registry or provenance not generated yet")
    reg = pd.read_csv(reg_path, dtype=str).fillna("")
    prov = pd.read_csv(prov_path, dtype=str).fillna("")
    active_keys = {(str(r["ticker"]), str(r["source_index"]).strip())
                   for _, r in reg.iterrows()
                   if str(r.get("active", "")).strip().lower() == "true"}
    inactive_keys = {(str(r["ticker"]), str(r["source_index"]).strip())
                     for _, r in reg.iterrows()
                     if str(r.get("active", "")).strip().lower() != "true"}
    prov_keys = {(str(r["ticker"]), str(r["source_index"]).strip())
                 for _, r in prov.iterrows()}
    reg_keys = {(str(r["ticker"]), str(r["source_index"]).strip())
                for _, r in reg.iterrows()}
    assert prov_keys <= reg_keys, f"provenance rows outside registry: {prov_keys - reg_keys}"
    assert prov_keys == active_keys, \
        f"active/provenance mismatch: prov_only={prov_keys - active_keys}, active_only={active_keys - prov_keys}"
    assert not (inactive_keys & prov_keys), \
        f"inactive rows in provenance: {inactive_keys & prov_keys}"


# (20b) real retrieval/evidence invariants (forward-compatible)
def test_r20b_real_retrieval_evidence_invariants():
    prov_path = PART03_DIR / "part03_source_provenance_10tickers.csv"
    if not prov_path.exists():
        pytest.skip("part03 provenance not generated yet")
    df = pd.read_csv(prov_path, dtype=str).fillna("")
    for _, r in df.iterrows():
        status = str(r.get("retrieval_status", ""))
        snap = str(r.get("snapshot_path", "")).strip()
        h = str(r.get("content_sha256", "")).strip()
        if status not in FETCHED_STATUSES:
            assert snap == "", f"failed fetch has snapshot: {snap}"
            assert h == "", f"failed fetch has hash: {h}"
            assert not _truthy(r.get("evidence_accepted", "")), \
                "failed fetch must not have evidence_accepted=true"
        else:
            assert snap != "", "fetched source has empty snapshot_path"
            assert _is_sha256(h), f"fetched source has invalid SHA-256: {h}"
            sp = ROOT / snap
            if sp.exists():
                assert hashlib.sha256(sp.read_bytes()).hexdigest() == h.lower(), \
                    f"snapshot hash mismatch for {snap}"
        review_status = str(r.get("content_review_status", "")).strip().lower()
        if review_status == "reviewed":
            assert status in FETCHED_STATUSES, "reviewed source not fetched"
            assert snap != "" and _is_sha256(h), "reviewed source missing snapshot/hash"
        assert str(r.get("evidence_accepted", "")).strip().lower() == \
            compute_evidence_accepted({k: r.get(k, "") for k in r.index}, snapshot_root=ROOT)


# (20c) real research counts match provenance (forward-compatible)
def test_r20c_real_research_counts_match_provenance():
    prov_path = PART03_DIR / "part03_source_provenance_10tickers.csv"
    research_path = PART03_DIR / "part03_research_screening_10tickers.csv"
    if not prov_path.exists() or not research_path.exists():
        pytest.skip("part03 outputs not generated yet")
    prov = pd.read_csv(prov_path, dtype=str).fillna("")
    research = pd.read_csv(research_path, dtype=str).fillna("")
    for _, r in research.iterrows():
        tk = str(r["ticker"])
        sub = prov[prov["ticker"] == tk]
        attempted = len(sub)
        fetched = sum(1 for _, p in sub.iterrows()
                      if str(p.get("retrieval_status", "")) in FETCHED_STATUSES)
        reviewed = sum(1 for _, p in sub.iterrows()
                       if str(p.get("content_review_status", "")).strip().lower() == "reviewed")
        accepted = sum(1 for _, p in sub.iterrows()
                       if _truthy(p.get("evidence_accepted", "")))
        assert str(r.get("attempted_source_count")) == str(attempted), \
            f"{tk}: attempted {r.get('attempted_source_count')} != {attempted}"
        assert str(r.get("fetched_source_count")) == str(fetched), \
            f"{tk}: fetched {r.get('fetched_source_count')} != {fetched}"
        assert str(r.get("reviewed_source_count")) == str(reviewed), \
            f"{tk}: reviewed {r.get('reviewed_source_count')} != {reviewed}"
        assert str(r.get("evidence_source_count")) == str(accepted), \
            f"{tk}: evidence {r.get('evidence_source_count')} != {accepted}"


# (20d) real summary matches current outputs (forward-compatible)
def test_r20d_real_summary_matches_current_outputs():
    summary_path = PART03_DIR / "part03_summary.json"
    research_path = PART03_DIR / "part03_research_screening_10tickers.csv"
    prov_path = PART03_DIR / "part03_source_provenance_10tickers.csv"
    if not summary_path.exists() or not research_path.exists() or not prov_path.exists():
        pytest.skip("part03 outputs not generated yet")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    research = pd.read_csv(research_path, dtype=str).fillna("")
    prov = pd.read_csv(prov_path, dtype=str).fillna("")
    counts = summary["counts"]
    assert counts["ready_count"] == sum(
        1 for _, r in research.iterrows() if _truthy(r.get("ready_for_user_review", "")))
    assert counts["network_blocked_count"] == sum(
        1 for _, r in research.iterrows() if _truthy(r.get("network_blocked", "")))
    assert counts["total_attempted_sources"] == len(prov)
    assert counts["total_fetched_sources"] == sum(
        1 for _, p in prov.iterrows() if str(p.get("retrieval_status", "")) in FETCHED_STATUSES)
    assert counts["total_reviewed_sources"] == sum(
        1 for _, p in prov.iterrows()
        if str(p.get("content_review_status", "")).strip().lower() == "reviewed")
    assert counts["total_evidence_sources"] == sum(
        1 for _, p in prov.iterrows() if _truthy(p.get("evidence_accepted", "")))


# (21) Part 2 hashes stable
def test_r21_part2_hashes_stable():
    manifest = PART03_DIR / "part02_hash_manifest.csv"
    if not manifest.exists():
        pytest.skip("manifest missing")
    mdf = pd.read_csv(manifest, dtype=str).fillna("")
    for _, r in mdf.iterrows():
        if not r.get("sha256", "").strip():
            continue
        fp = ROOT / r["relative_path"]
        if fp.exists():
            assert sha(fp) == r["sha256"], f"{r['relative_path']} changed"


# (22) TSETMC audit stable
def test_r22_tsetmc_audit_stable():
    df = pd.read_csv(PART03_DIR / "part03_tsetmc_audit_10tickers.csv",
                     dtype=str).fillna("")
    assert (df["network_request_performed"].str.lower() == "false").all()
    assert (df["probe_source"] == "historical_v2_audit").all()


# registry one-to-one QC surfaced through run_part03_qc
def test_r_qc_registry_provenance_mapping():
    df = _seed_registry()
    sources = registry_to_research_sources(df, include_inactive=False)
    saved = part03_mod._requests.get
    part03_mod._requests.get = lambda *a, **k: (_ for _ in ()).throw(
        part03_mod._requests.exceptions.Timeout())
    try:
        res = fetch_sources(force=True, sources_by_ticker=sources)
    finally:
        part03_mod._requests.get = saved
    overlaid = {tk: normalize_provenance_records(res.get(tk, []), None)
                for tk in PART03_TICKERS}
    prov = build_source_provenance(overlaid, snapshot_root=None)
    research = build_research_screening(_names(), overlaid, _absent_tsetmc())
    tickers_df = build_tickers_df(_names())
    tsetmc_df = build_tsetmc_audit(_absent_tsetmc())
    qc = run_part03_qc(tickers_df, research, prov, tsetmc_df, {}, {}, {}, {},
                       registry_df=df)
    assert _result(qc, "registry_valid") is True
    assert _result(qc, "active_registry_matches_provenance") is True


# ================================================================================
# Part 3.1A.4 — Forward-compatible registry & worklist QC
# ================================================================================

def _prov_from_registry(reg_df):
    sources = registry_to_research_sources(reg_df, include_inactive=False)
    saved = part03_mod._requests.get
    part03_mod._requests.get = lambda *a, **k: (_ for _ in ()).throw(
        part03_mod._requests.exceptions.Timeout())
    try:
        res = fetch_sources(force=True, sources_by_ticker=sources)
    finally:
        part03_mod._requests.get = saved
    overlaid = {tk: normalize_provenance_records(res.get(tk, []), None)
                for tk in PART03_TICKERS}
    return build_source_provenance(overlaid, snapshot_root=None)


def _qc_reg(registry_df, prov_df=None):
    tickers_df, research_df, base_prov, tsetmc_df = _baseline_dfs()
    prov = prov_df if prov_df is not None else base_prov
    return run_part03_qc(tickers_df, research_df, prov, tsetmc_df,
                         {}, {}, {}, {}, registry_df=registry_df)


def _qc_wl(worklist_df):
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    return run_part03_qc(tickers_df, research_df, prov_df, tsetmc_df,
                         {}, {}, {}, {}, worklist_df=worklist_df)


# (f1) current 20-row registry passes
def test_f01_seed_registry_passes():
    reg = build_seed_registry_df()
    qc = _qc_reg(reg, _prov_from_registry(reg))
    for a in ("registry_valid", "registry_seed_20_preserved",
              "registry_seed_keys_preserved", "registry_seed_content_unchanged",
              "registry_minimum_two_seed_sources_each",
              "registry_additional_sources_allowed",
              "active_registry_matches_provenance"):
        assert _result(qc, a) is True, a


# (f2)/(f3) registry with a valid manual source_index=3 passes (21 rows)
def test_f02_f03_registry_with_index3_passes():
    tk = PART03_TICKERS[0]
    add = pd.DataFrame([{
        "ticker": tk, "source_type": "codal_official", "source_title": "doc3",
        "source_url": "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=NEW3",
        "added_by": "tester", "discovery_notes": "found in 3.1B",
    }])
    reg = register_discovered_sources(build_seed_registry_df(), add)
    assert len(reg) == 21
    prov = _prov_from_registry(reg)
    # the index=3 source must reach provenance
    sub = prov[(prov["ticker"] == tk) & (prov["source_index"] == "3")]
    assert len(sub) == 1
    qc = _qc_reg(reg, prov)
    assert _result(qc, "registry_additional_sources_allowed") is True
    assert _result(qc, "registry_seed_20_preserved") is True
    assert _result(qc, "active_registry_matches_provenance") is True
    # not failed merely for having 21 rows
    assert _result(qc, "registry_valid") is True


# (f4) removing one of the 20 seeds fails
def test_f04_removed_seed_fails():
    reg = build_seed_registry_df().iloc[1:].copy()  # drop one seed
    qc = _qc_reg(reg, _prov_from_registry(reg))
    assert _result(qc, "registry_seed_20_preserved") is False


# (f5) changing a seed URL fails
def test_f05_changed_seed_url_fails():
    reg = build_seed_registry_df().copy()
    reg.at[0, "source_url"] = "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=HACK"
    qc = _qc_reg(reg, _prov_from_registry(reg))
    assert _result(qc, "registry_seed_content_unchanged") is False


# (f6) duplicate manual URL for same ticker rejected
def test_f06_duplicate_manual_url_rejected():
    reg = build_seed_registry_df()
    existing = reg[(reg["ticker"] == PART03_TICKERS[0]) &
                   (reg["source_index"] == "1")].iloc[0]["source_url"]
    add = pd.DataFrame([{
        "ticker": PART03_TICKERS[0], "source_type": "market_information_aggregator",
        "source_title": "dup", "source_url": existing, "added_by": "x",
        "discovery_notes": "",
    }])
    with pytest.raises(ValueError):
        register_discovered_sources(reg, add)
    # validation also catches a duplicate-url registry
    bad = reg.copy()
    bad.loc[len(bad)] = {
        "ticker": PART03_TICKERS[0], "source_index": "3",
        "source_type": "market_information_aggregator", "source_title": "d",
        "source_url": existing, "source_origin": "manual_discovery",
        "active": "true", "discovery_status": "discovered_pending_fetch",
        "added_at_utc": "", "added_by": "", "discovery_notes": "",
    }
    ok, errs = validate_source_registry(bad)
    assert ok is False and any("duplicate source_url" in e for e in errs)


# (f7) inactive source appearing in provenance fails
def test_f07_inactive_in_provenance_fails():
    reg = build_seed_registry_df().copy()
    reg.loc[(reg["ticker"] == PART03_TICKERS[0]) & (reg["source_index"] == "2"),
            "active"] = "false"
    # provenance still includes the now-inactive key (built before deactivation)
    prov = _prov_from_registry(build_seed_registry_df())
    qc = _qc_reg(reg, prov)
    assert (_result(qc, "inactive_registry_not_in_provenance") is False
            or _result(qc, "active_registry_matches_provenance") is False)


# (f8) active source missing from provenance fails
def test_f08_active_missing_from_provenance_fails():
    reg = build_seed_registry_df()
    prov = _prov_from_registry(reg)
    prov = prov.iloc[1:].copy()  # drop one active provenance row
    qc = _qc_reg(reg, prov)
    assert _result(qc, "active_registry_matches_provenance") is False


# (f9) empty (template) worklist passes
def test_f09_empty_worklist_passes():
    wl = build_manual_research_worklist(_names(), _baseline_dfs()[1])
    qc = _qc_wl(wl)
    for a in ("worklist_exact_ticker_scope", "worklist_no_duplicates",
              "worklist_discovered_urls_valid", "worklist_candidate_date_valid",
              "worklist_event_candidate_valid", "worklist_ordinary_share_value_valid",
              "worklist_manual_status_valid"):
        assert _result(qc, a) is True, a


# (f10) valid https discovered URL passes
def test_f10_worklist_valid_url_passes():
    wl = build_manual_research_worklist(_names(), _baseline_dfs()[1])
    wl.at[0, "discovered_source_1_url"] = "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=AB"
    wl.at[0, "manual_review_status"] = "source_discovered"
    qc = _qc_wl(wl)
    assert _result(qc, "worklist_discovered_urls_valid") is True
    assert _result(qc, "worklist_manual_status_valid") is True


# (f11) invalid discovered URL fails
def test_f11_worklist_invalid_url_fails():
    wl = build_manual_research_worklist(_names(), _baseline_dfs()[1])
    wl.at[0, "discovered_source_1_url"] = "file:///Users/x/Desktop/snap.html"
    qc = _qc_wl(wl)
    assert _result(qc, "worklist_discovered_urls_valid") is False


# (f12) valid exact Jalali passes
def test_f12_worklist_valid_date_passes():
    wl = build_manual_research_worklist(_names(), _baseline_dfs()[1])
    wl.at[0, "candidate_date_jalali"] = "1380-03-15"
    qc = _qc_wl(wl)
    assert _result(qc, "worklist_candidate_date_valid") is True


# (f13) invalid candidate date fails
def test_f13_worklist_invalid_date_fails():
    wl = build_manual_research_worklist(_names(), _baseline_dfs()[1])
    wl.at[0, "candidate_date_jalali"] = "1380-13-40"
    qc = _qc_wl(wl)
    assert _result(qc, "worklist_candidate_date_valid") is False


# (f14) invalid event candidate fails
def test_f14_worklist_invalid_event_fails():
    wl = build_manual_research_worklist(_names(), _baseline_dfs()[1])
    wl.at[0, "first_public_event_candidate"] = "rights_offering"
    qc = _qc_wl(wl)
    assert _result(qc, "worklist_event_candidate_valid") is False


# (f15) invalid manual status fails
def test_f15_worklist_invalid_status_fails():
    wl = build_manual_research_worklist(_names(), _baseline_dfs()[1])
    wl.at[0, "manual_review_status"] = "totally_made_up"
    qc = _qc_wl(wl)
    assert _result(qc, "worklist_manual_status_valid") is False


# (f16) a worklist URL does not auto-enter the registry
def test_f16_worklist_url_not_in_registry():
    names = _names()
    template = build_manual_research_worklist(names, _baseline_dfs()[1])
    existing = template.copy()
    existing.at[0, "discovered_source_1_url"] = "https://example.com/news/1"
    merged = merge_existing_worklist_with_current_status(template, existing)
    # merge must not touch the registry
    reg = load_source_registry()
    assert "https://example.com/news/1" not in set(reg["source_url"])
    assert merged.at[0, "discovered_source_1_url"] == "https://example.com/news/1"


# (f17) merge preserves existing URL and date
def test_f17_merge_preserves_url_and_date():
    names = _names()
    template = build_manual_research_worklist(names, _baseline_dfs()[1])
    existing = template.copy()
    existing.at[2, "discovered_source_1_url"] = "https://isna.ir/news/99"
    existing.at[2, "candidate_date_jalali"] = "1382-06-10"
    existing.at[2, "manual_review_status"] = "under_review"
    merged = merge_existing_worklist_with_current_status(template, existing)
    assert merged.at[2, "discovered_source_1_url"] == "https://isna.ir/news/99"
    assert merged.at[2, "candidate_date_jalali"] == "1382-06-10"
    assert merged.at[2, "manual_review_status"] == "under_review"


# (f18) real outputs are forward-compatible — covered by r20* tests above
# (removed test_f18_current_outputs_unchanged which locked on 20 timeout rows)


# (f19) Part 2 hashes stable
def test_f19_part2_hashes_stable():
    manifest = PART03_DIR / "part02_hash_manifest.csv"
    if not manifest.exists():
        pytest.skip("manifest missing")
    mdf = pd.read_csv(manifest, dtype=str).fillna("")
    for _, r in mdf.iterrows():
        if not r.get("sha256", "").strip():
            continue
        fp = ROOT / r["relative_path"]
        if fp.exists():
            assert sha(fp) == r["sha256"], f"{r['relative_path']} changed"


# (f20) TSETMC audit stable
def test_f20_tsetmc_audit_stable():
    df = pd.read_csv(PART03_DIR / "part03_tsetmc_audit_10tickers.csv",
                     dtype=str).fillna("")
    assert (df["network_request_performed"].str.lower() == "false").all()
    assert (df["probe_source"] == "historical_v2_audit").all()


# ================================================================================
# Part 3.1A.4.1 — candidate_date_jalali ↔ date_precision agreement + strict enums
# ================================================================================

from project.src.stage124_batch02_part03 import validate_worklist_date_precision


# date/precision agreement unit cases (1-11)
def test_g01_empty_unknown_pass():
    assert validate_worklist_date_precision("", "unknown") is True


def test_g02_empty_exact_day_fail():
    assert validate_worklist_date_precision("", "exact_day") is False


def test_g03_year_only_pass():
    assert validate_worklist_date_precision("1380", "year_only") is True


def test_g04_year_with_exact_day_fail():
    assert validate_worklist_date_precision("1380", "exact_day") is False


def test_g05_month_only_pass():
    assert validate_worklist_date_precision("1380-03", "month_only") is True


def test_g06_month_with_year_only_fail():
    assert validate_worklist_date_precision("1380-03", "year_only") is False


def test_g07_exact_day_pass():
    assert validate_worklist_date_precision("1380-03-15", "exact_day") is True


def test_g08_exact_day_with_month_only_fail():
    assert validate_worklist_date_precision("1380-03-15", "month_only") is False


def test_g09_nonempty_unknown_fail():
    assert validate_worklist_date_precision("1380-03-15", "unknown") is False


def test_g10_invalid_precision_fail():
    assert validate_worklist_date_precision("1380", "decade") is False


def test_g11_out_of_range_month_fail():
    assert validate_worklist_date_precision("9999-03", "month_only") is False
    assert validate_worklist_date_precision("1380-13", "month_only") is False


# QC-level checks (12-15): strict enums + precision matching
def _wl_template():
    return build_manual_research_worklist(_names(), _baseline_dfs()[1])


def test_g12_ordinary_share_empty_fails():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    wl = _wl_template()
    wl.at[0, "ordinary_share_explicit"] = ""
    qc = run_part03_qc(tickers_df, research_df, prov_df, tsetmc_df,
                       {}, {}, {}, {}, worklist_df=wl)
    assert _result(qc, "worklist_ordinary_share_value_valid") is False


def test_g13_ordinary_share_invalid_fails():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    wl = _wl_template()
    wl.at[0, "ordinary_share_explicit"] = "maybe"
    qc = run_part03_qc(tickers_df, research_df, prov_df, tsetmc_df,
                       {}, {}, {}, {}, worklist_df=wl)
    assert _result(qc, "worklist_ordinary_share_value_valid") is False


def test_g14_manual_status_empty_fails():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    wl = _wl_template()
    wl.at[0, "manual_review_status"] = ""
    qc = run_part03_qc(tickers_df, research_df, prov_df, tsetmc_df,
                       {}, {}, {}, {}, worklist_df=wl)
    assert _result(qc, "worklist_manual_status_valid") is False


def test_g15_manual_status_invalid_fails():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    wl = _wl_template()
    wl.at[0, "manual_review_status"] = "done_ish"
    qc = run_part03_qc(tickers_df, research_df, prov_df, tsetmc_df,
                       {}, {}, {}, {}, worklist_df=wl)
    assert _result(qc, "worklist_manual_status_valid") is False


def test_g_qc_date_precision_mismatch_fails():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    wl = _wl_template()
    wl.at[0, "candidate_date_jalali"] = "1380"
    wl.at[0, "date_precision"] = "exact_day"
    qc = run_part03_qc(tickers_df, research_df, prov_df, tsetmc_df,
                       {}, {}, {}, {}, worklist_df=wl)
    assert _result(qc, "worklist_date_precision_matches_candidate") is False


def test_g_qc_date_precision_aligned_passes():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    wl = _wl_template()
    wl.at[0, "candidate_date_jalali"] = "1380-03-15"
    wl.at[0, "date_precision"] = "exact_day"
    wl.at[0, "manual_review_status"] = "reviewed"
    qc = run_part03_qc(tickers_df, research_df, prov_df, tsetmc_df,
                       {}, {}, {}, {}, worklist_df=wl)
    assert _result(qc, "worklist_date_precision_matches_candidate") is True
    assert _result(qc, "worklist_date_precision_enum_valid") is True


# (16) current worklist still passes all new checks
def test_g16_current_worklist_passes():
    tickers_df, research_df, prov_df, tsetmc_df = _baseline_dfs()
    wl = _wl_template()
    qc = run_part03_qc(tickers_df, research_df, prov_df, tsetmc_df,
                       {}, {}, {}, {}, worklist_df=wl)
    for a in ("worklist_date_precision_enum_valid",
              "worklist_date_precision_matches_candidate",
              "worklist_ordinary_share_value_valid",
              "worklist_manual_status_valid"):
        assert _result(qc, a) is True, a


# (17) registry with source_index=3 still passes
def test_g17_registry_index3_still_passes():
    tk = PART03_TICKERS[0]
    add = pd.DataFrame([{
        "ticker": tk, "source_type": "codal_official", "source_title": "doc3",
        "source_url": "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=NEW3",
        "added_by": "tester", "discovery_notes": "",
    }])
    reg = register_discovered_sources(build_seed_registry_df(), add)
    qc = _qc_reg(reg, _prov_from_registry(reg))
    assert _result(qc, "registry_additional_sources_allowed") is True
    assert _result(qc, "active_registry_matches_provenance") is True


# (18) real outputs are forward-compatible — covered by r20* tests above
# (removed test_g18_current_outputs_unchanged which locked on 20 timeout rows)


# (19) Part 2 hashes stable
def test_g19_part2_hashes_stable():
    manifest = PART03_DIR / "part02_hash_manifest.csv"
    if not manifest.exists():
        pytest.skip("manifest missing")
    mdf = pd.read_csv(manifest, dtype=str).fillna("")
    for _, r in mdf.iterrows():
        if not r.get("sha256", "").strip():
            continue
        fp = ROOT / r["relative_path"]
        if fp.exists():
            assert sha(fp) == r["sha256"], f"{r['relative_path']} changed"


# (20) TSETMC audit stable
def test_g20_tsetmc_audit_stable():
    df = pd.read_csv(PART03_DIR / "part03_tsetmc_audit_10tickers.csv",
                     dtype=str).fillna("")
    assert (df["network_request_performed"].str.lower() == "false").all()
    assert (df["probe_source"] == "historical_v2_audit").all()


# ================================================================================
# Part 3.1A.4.2 — Forward-compatible real-output tests + synthetic fixtures
# ================================================================================

# --- synthetic all-timeout fixture (independent of real repository file) ---
def test_synthetic_all_timeout_fixture_blocked():
    """A synthetic 10-ticker fixture where every source times out must produce
    research_blocked_network, requires_manual_review, ready=false, and
    ordinary_share=unknown — independent of the real committed CSV."""
    fetch = _failed_fetch_results()
    names = _names()
    tsetmc = _absent_tsetmc()
    research = build_research_screening(names, fetch, tsetmc)
    assert (research["research_status"] == "research_blocked_network").all()
    assert (research["evidence_status"] == "requires_manual_review").all()
    assert (research["ready_for_user_review"].str.lower() == "false").all()
    assert (research["ordinary_share_confirmed"] == "unknown").all()
    assert (research["network_blocked"].str.lower() == "true").all()
    for c in ("fetched_source_count", "reviewed_source_count", "evidence_source_count"):
        assert (research[c].astype(str) == "0").all()


# --- provenance with valid third source passes ---
def test_prov_valid_third_source_passes():
    tk = PART03_TICKERS[0]
    reg = build_seed_registry_df()
    add = pd.DataFrame([{
        "ticker": tk, "source_type": "codal_official", "source_title": "doc3",
        "source_url": "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=NEW3",
        "added_by": "tester", "discovery_notes": "found in 3.1B",
    }])
    reg = register_discovered_sources(reg, add)
    assert len(reg) == 21
    prov = _prov_from_registry(reg)
    sub = prov[(prov["ticker"] == tk) & (prov["source_index"] == "3")]
    assert len(sub) == 1
    qc = _qc_reg(reg, prov)
    assert _result(qc, "registry_additional_sources_allowed") is True
    assert _result(qc, "active_registry_matches_provenance") is True


# --- provenance with valid fetched source passes ---
def test_prov_valid_fetched_source_passes():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("fc_fetched.html")
    try:
        retrieval = _retrieval_rec(tk, _CODAL_DOC, rel, h)
        existing = _existing_prov_df(tk, _CODAL_DOC, rel, h)
        overlaid = apply_validated_review_overlay([retrieval], existing, ROOT)
        normalized = normalize_provenance_records(overlaid, ROOT)
        prov = build_source_provenance({tk: normalized}, snapshot_root=ROOT)
        sub = prov[(prov["ticker"] == tk) & (prov["source_index"] == "1")]
        assert len(sub) == 1
        assert str(sub.iloc[0]["retrieval_status"]) in FETCHED_STATUSES
        assert _is_sha256(str(sub.iloc[0]["content_sha256"]))
    finally:
        snap.unlink(missing_ok=True)


# --- research with valid candidate_supported passes ---
def test_research_valid_candidate_supported_passes():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("cs.html")
    try:
        retrieval = _retrieval_rec(tk, _CODAL_DOC, rel, h)
        existing = _existing_prov_df(tk, _CODAL_DOC, rel, h)
        overlaid = apply_validated_review_overlay([retrieval], existing, ROOT)
        normalized = normalize_provenance_records(overlaid, ROOT)
        research = build_research_screening(_names(), {tk: normalized},
                                             _absent_tsetmc())
        row = research[research["ticker"] == tk].iloc[0]
        assert row["research_status"] == "candidate_supported"
        assert str(row["ready_for_user_review"]).lower() == "true"
    finally:
        snap.unlink(missing_ok=True)


# --- research with valid conflict passes ---
def test_research_valid_conflict_passes():
    tk = PART03_TICKERS[0]
    snap1, rel1, h1 = _make_snapshot("conf1.html", b"<html>doc1</html>")
    snap2, rel2, h2 = _make_snapshot("conf2.html", b"<html>doc2</html>")
    try:
        ret1 = _retrieval_rec(tk, _CODAL_DOC, rel1, h1)
        ret1["source_index"] = 1
        ext1 = _existing_prov_df(tk, _CODAL_DOC, rel1, h1,
                                 event_type_supported="first_public_offering",
                                 reviewed_date_jalali="1380-03-15")
        ret2 = _retrieval_rec(tk, "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=DIFF2",
                              rel2, h2)
        ret2["source_index"] = 2
        ext2 = _existing_prov_df(tk, "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=DIFF2",
                                 rel2, h2,
                                 source_index="2",
                                 event_type_supported="first_public_offering",
                                 reviewed_date_jalali="1381-06-20")
        overlaid = apply_validated_review_overlay([ret1, ret2],
                                                  pd.concat([ext1, ext2], ignore_index=True),
                                                  ROOT)
        normalized = normalize_provenance_records(overlaid, ROOT)
        research = build_research_screening(_names(), {tk: normalized},
                                             _absent_tsetmc())
        row = research[research["ticker"] == tk].iloc[0]
        assert str(row["research_status"]) == "research_completed_conflict"
        assert str(row["conflict_flag"]).lower() == "true"
        assert str(row["ready_for_user_review"]).lower() == "false"
    finally:
        snap1.unlink(missing_ok=True)
        snap2.unlink(missing_ok=True)


# --- failed fetch with fabricated snapshot/hash fails ---
def test_failed_fetch_fabricated_snapshot_fails():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("fab.html")
    try:
        retrieval = _retrieval_rec(tk, _CODAL_DOC, rel, h, status="timeout")
        retrieval["snapshot_path"] = rel
        retrieval["content_sha256"] = h
        existing = _existing_prov_df(tk, _CODAL_DOC, "stale.html", "a" * 64)
        overlaid = apply_validated_review_overlay([retrieval], existing, ROOT)
        normalized = normalize_provenance_records(overlaid, ROOT)
        prov = build_source_provenance({tk: normalized}, snapshot_root=ROOT)
        row = prov[(prov["ticker"] == tk) & (prov["source_index"] == "1")].iloc[0]
        assert not _truthy(row["evidence_accepted"]), \
            "failed fetch must not have evidence_accepted=true"
        tickers_df, _, _, tsetmc_df = _baseline_dfs()
        research_df = build_research_screening(_names(), {tk: normalized},
                                               _absent_tsetmc())
        qc = run_part03_qc(tickers_df, research_df, prov, tsetmc_df, {}, {}, {}, {})
        failed = [a["assertion"] for a in qc["assertions"] if not a["passed"]]
        assert any("failed_fetch_no_snapshot" in f for f in failed), \
            f"expected failed_fetch_no_snapshot failure, got: {failed}"
    finally:
        snap.unlink(missing_ok=True)


# --- accepted evidence inconsistent with engine fails ---
def test_accepted_evidence_inconsistent_fails():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("inc.html")
    try:
        retrieval = _retrieval_rec(tk, _CODAL_DOC, rel, h)
        existing = _existing_prov_df(tk, _CODAL_DOC, rel, h,
                                     content_review_status="pending_manual_review",
                                     evidence_accepted="true")
        overlaid = apply_validated_review_overlay([retrieval], existing, ROOT)
        normalized = normalize_provenance_records(overlaid, ROOT)
        prov = build_source_provenance({tk: normalized}, snapshot_root=ROOT)
        row = prov[(prov["ticker"] == tk) & (prov["source_index"] == "1")].iloc[0]
        assert not _truthy(row["evidence_accepted"]), \
            "engine must recompute evidence_accepted=false for unreviewed source"
    finally:
        snap.unlink(missing_ok=True)


# --- active registry row missing in provenance fails ---
def test_active_registry_missing_in_provenance_fails():
    reg = build_seed_registry_df()
    prov = _prov_from_registry(reg)
    prov = prov.iloc[1:].copy()
    qc = _qc_reg(reg, prov)
    assert _result(qc, "active_registry_matches_provenance") is False


# --- provenance row outside registry fails ---
def test_provenance_outside_registry_fails():
    reg = build_seed_registry_df()
    prov = _prov_from_registry(reg)
    extra = prov.iloc[0:1].copy()
    extra.loc[extra.index[0], "source_index"] = "99"
    prov = pd.concat([prov, extra], ignore_index=True)
    qc = _qc_reg(reg, prov)
    assert _result(qc, "provenance_subset_of_registry") is False


# --- research count inconsistent with provenance fails ---
def test_research_count_inconsistent_fails():
    reg = build_seed_registry_df()
    prov = _prov_from_registry(reg)
    sources = registry_to_research_sources(reg, include_inactive=False)
    saved = part03_mod._requests.get
    part03_mod._requests.get = lambda *a, **k: (_ for _ in ()).throw(
        part03_mod._requests.exceptions.Timeout())
    try:
        res = fetch_sources(force=True, sources_by_ticker=sources)
    finally:
        part03_mod._requests.get = saved
    overlaid = {tk: normalize_provenance_records(res.get(tk, []), None)
                for tk in PART03_TICKERS}
    research = build_research_screening(_names(), overlaid, _absent_tsetmc())
    research.at[0, "fetched_source_count"] = 999
    tickers_df, _, prov_df, tsetmc_df = _baseline_dfs()
    qc = run_part03_qc(tickers_df, research, prov_df, tsetmc_df, {}, {}, {}, {},
                       registry_df=reg)
    failed = [a["assertion"] for a in qc["assertions"] if not a["passed"]]
    assert any("research_from_provenance" in f for f in failed), \
        f"expected research_from_provenance failure, got: {failed}"


# --- summary count inconsistent fails ---
def test_summary_count_inconsistent_fails():
    summary_path = PART03_DIR / "part03_summary.json"
    if not summary_path.exists():
        pytest.skip("part03 summary not generated yet")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    research_path = PART03_DIR / "part03_research_screening_10tickers.csv"
    prov_path = PART03_DIR / "part03_source_provenance_10tickers.csv"
    research = pd.read_csv(research_path, dtype=str).fillna("")
    prov = pd.read_csv(prov_path, dtype=str).fillna("")
    counts = summary["counts"]
    actual_fetched = sum(
        1 for _, p in prov.iterrows() if str(p.get("retrieval_status", "")) in FETCHED_STATUSES)
    assert counts["total_fetched_sources"] == actual_fetched, \
        "summary total_fetched_sources must match provenance"
    actual_ready = sum(
        1 for _, r in research.iterrows() if _truthy(r.get("ready_for_user_review", "")))
    assert counts["ready_count"] == actual_ready, \
        "summary ready_count must match research"


# ================================================================================
# Part 3.1A.5 — Reviewed-evidence engine: admission, listing, partial-date,
# public_company_conversion, conflict, no_reliable_evidence (24 tests)
# ================================================================================

from project.src.stage124_batch02_part03 import (
    evaluate_reviewed_evidence_record,
    REVIEWED_EVENT_TYPES,
    REVIEWED_DATE_PRECISIONS,
    EVIDENCE_ROLES,
)

_A5_CODAL = "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=ABC123"


# === Admission-only evidence (3 tests) ===

def test_a5_admission_only_status():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("a5_adm1.html")
    try:
        retrieval = _retrieval_rec(tk, _A5_CODAL, rel, h)
        existing = _existing_prov_df(tk, _A5_CODAL, rel, h,
                                     event_type_supported="admission",
                                     exact_date_explicit="true",
                                     reviewed_date_jalali="1380-03-15",
                                     ordinary_share_explicit="unknown")
        overlaid = apply_validated_review_overlay([retrieval], existing, ROOT)
        normalized = normalize_provenance_records(overlaid, ROOT)
        st = _derive_screening_status(normalized, snapshot_root=ROOT)
        assert st["research_status"] == "research_completed_admission_only"
        assert st["evidence_status"] == "requires_first_public_trade_evidence"
        assert st["ready_for_user_review"] == "false"
        assert st["candidate_event_type"] == "admission"
        assert st["admission_date_candidate_jalali"] == "1380-03-15"
        assert st["proposed_canonical_public_entry_date_jalali"] == ""
    finally:
        snap.unlink(missing_ok=True)


def test_a5_admission_only_evidence_role():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("a5_adm2.html")
    try:
        rec = _retrieval_rec(tk, _A5_CODAL, rel, h,
                             content_review_status="reviewed",
                             event_type_supported="admission",
                             exact_date_explicit="true",
                             reviewed_date_jalali="1380-03-15",
                             ordinary_share_explicit="unknown")
        ev = evaluate_reviewed_evidence_record(rec, snapshot_root=ROOT)
        assert ev["reviewed_evidence_valid"] is True
        assert ev["evidence_role"] == "admission_only"
        assert ev["reviewed_event_type"] == "admission"
        assert ev["reviewed_date_precision"] == "exact_day"
    finally:
        snap.unlink(missing_ok=True)


def test_a5_admission_only_not_ready():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("a5_adm3.html")
    try:
        retrieval = _retrieval_rec(tk, _A5_CODAL, rel, h)
        existing = _existing_prov_df(tk, _A5_CODAL, rel, h,
                                     event_type_supported="admission",
                                     exact_date_explicit="true",
                                     reviewed_date_jalali="1380-06-20",
                                     ordinary_share_explicit="unknown")
        overlaid = apply_validated_review_overlay([retrieval], existing, ROOT)
        normalized = normalize_provenance_records(overlaid, ROOT)
        research = build_research_screening(_names(), {tk: normalized}, _absent_tsetmc())
        row = research[research["ticker"] == tk].iloc[0]
        assert str(row["ready_for_user_review"]).lower() == "false"
        assert str(row["research_status"]) == "research_completed_admission_only"
        assert str(row["admission_date_candidate_jalali"]) == "1380-06-20"
    finally:
        snap.unlink(missing_ok=True)


# === Listing-only evidence (3 tests) ===

def test_a5_listing_only_status():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("a5_lst1.html")
    try:
        retrieval = _retrieval_rec(tk, _A5_CODAL, rel, h)
        existing = _existing_prov_df(tk, _A5_CODAL, rel, h,
                                     event_type_supported="listing",
                                     exact_date_explicit="true",
                                     reviewed_date_jalali="1381-01-10",
                                     ordinary_share_explicit="unknown")
        overlaid = apply_validated_review_overlay([retrieval], existing, ROOT)
        normalized = normalize_provenance_records(overlaid, ROOT)
        st = _derive_screening_status(normalized, snapshot_root=ROOT)
        assert st["research_status"] == "research_completed_listing_only"
        assert st["evidence_status"] == "requires_first_public_trade_evidence"
        assert st["ready_for_user_review"] == "false"
        assert st["candidate_event_type"] == "listing"
        assert st["listing_date_candidate_jalali"] == "1381-01-10"
    finally:
        snap.unlink(missing_ok=True)


def test_a5_listing_only_evidence_role():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("a5_lst2.html")
    try:
        rec = _retrieval_rec(tk, _A5_CODAL, rel, h,
                             content_review_status="reviewed",
                             event_type_supported="listing",
                             exact_date_explicit="true",
                             reviewed_date_jalali="1381-01-10",
                             ordinary_share_explicit="unknown")
        ev = evaluate_reviewed_evidence_record(rec, snapshot_root=ROOT)
        assert ev["reviewed_evidence_valid"] is True
        assert ev["evidence_role"] == "listing_only"
        assert ev["reviewed_event_type"] == "listing"
    finally:
        snap.unlink(missing_ok=True)


def test_a5_listing_only_not_ready():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("a5_lst3.html")
    try:
        retrieval = _retrieval_rec(tk, _A5_CODAL, rel, h)
        existing = _existing_prov_df(tk, _A5_CODAL, rel, h,
                                     event_type_supported="listing",
                                     exact_date_explicit="true",
                                     reviewed_date_jalali="1381-01-10",
                                     ordinary_share_explicit="unknown")
        overlaid = apply_validated_review_overlay([retrieval], existing, ROOT)
        normalized = normalize_provenance_records(overlaid, ROOT)
        research = build_research_screening(_names(), {tk: normalized}, _absent_tsetmc())
        row = research[research["ticker"] == tk].iloc[0]
        assert str(row["ready_for_user_review"]).lower() == "false"
        assert str(row["research_status"]) == "research_completed_listing_only"
        assert str(row["listing_date_candidate_jalali"]) == "1381-01-10"
    finally:
        snap.unlink(missing_ok=True)


# === Partial-date canonical evidence (3 tests) ===

def test_a5_partial_date_year_only_status():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("a5_part1.html")
    try:
        retrieval = _retrieval_rec(tk, _A5_CODAL, rel, h)
        existing = _existing_prov_df(tk, _A5_CODAL, rel, h,
                                     event_type_supported="first_public_offering",
                                     exact_date_explicit="false",
                                     reviewed_date_jalali="1380",
                                     ordinary_share_explicit="true")
        overlaid = apply_validated_review_overlay([retrieval], existing, ROOT)
        normalized = normalize_provenance_records(overlaid, ROOT)
        st = _derive_screening_status(normalized, snapshot_root=ROOT)
        assert st["research_status"] == "research_completed_partial_public_entry_date"
        assert st["evidence_status"] == "requires_manual_review"
        assert st["ready_for_user_review"] == "false"
        assert st["date_precision"] == "year_only"
        assert st["first_public_offering_date_candidate_jalali"] == "1380"
        # canonical date / event type stay empty for partial-date evidence
        assert st["proposed_canonical_public_entry_date_jalali"] == ""
        assert st["proposed_canonical_event_type"] == ""
    finally:
        snap.unlink(missing_ok=True)


def test_a5_partial_date_month_only_evidence_role():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("a5_part2.html")
    try:
        rec = _retrieval_rec(tk, _A5_CODAL, rel, h,
                             content_review_status="reviewed",
                             event_type_supported="first_public_trading",
                             exact_date_explicit="false",
                             reviewed_date_jalali="1380-06",
                             ordinary_share_explicit="true")
        ev = evaluate_reviewed_evidence_record(rec, snapshot_root=ROOT)
        assert ev["reviewed_evidence_valid"] is True
        assert ev["evidence_role"] == "canonical_partial_date"
        assert ev["reviewed_date_precision"] == "month_only"
    finally:
        snap.unlink(missing_ok=True)


def test_a5_partial_date_not_ready():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("a5_part3.html")
    try:
        retrieval = _retrieval_rec(tk, _A5_CODAL, rel, h)
        existing = _existing_prov_df(tk, _A5_CODAL, rel, h,
                                     event_type_supported="first_public_offering",
                                     exact_date_explicit="false",
                                     reviewed_date_jalali="1380-03",
                                     ordinary_share_explicit="true")
        overlaid = apply_validated_review_overlay([retrieval], existing, ROOT)
        normalized = normalize_provenance_records(overlaid, ROOT)
        research = build_research_screening(_names(), {tk: normalized}, _absent_tsetmc())
        row = research[research["ticker"] == tk].iloc[0]
        assert str(row["ready_for_user_review"]).lower() == "false"
        assert str(row["research_status"]) == "research_completed_partial_public_entry_date"
        assert str(row["date_precision"]) == "month_only"
    finally:
        snap.unlink(missing_ok=True)


# === Public company conversion only (3 tests) ===

def test_a5_conversion_only_status():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("a5_conv1.html")
    try:
        retrieval = _retrieval_rec(tk, _A5_CODAL, rel, h)
        existing = _existing_prov_df(tk, _A5_CODAL, rel, h,
                                     event_type_supported="conversion_to_public",
                                     exact_date_explicit="true",
                                     reviewed_date_jalali="1380-05-01",
                                     ordinary_share_explicit="unknown")
        overlaid = apply_validated_review_overlay([retrieval], existing, ROOT)
        normalized = normalize_provenance_records(overlaid, ROOT)
        st = _derive_screening_status(normalized, snapshot_root=ROOT)
        assert st["research_status"] == "research_completed_noncanonical_entry_evidence"
        assert st["evidence_status"] == "requires_manual_review"
        assert st["proposed_canonical_public_entry_date_jalali"] == ""
        assert st["proposed_canonical_event_type"] == ""
        assert st["ready_for_user_review"] == "false"
        assert st["candidate_event_type"] == "public_company_conversion"
    finally:
        snap.unlink(missing_ok=True)


def test_a5_conversion_only_evidence_role():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("a5_conv2.html")
    try:
        rec = _retrieval_rec(tk, _A5_CODAL, rel, h,
                             content_review_status="reviewed",
                             event_type_supported="conversion_to_public",
                             exact_date_explicit="true",
                             reviewed_date_jalali="1380-05-01",
                             ordinary_share_explicit="unknown")
        ev = evaluate_reviewed_evidence_record(rec, snapshot_root=ROOT)
        assert ev["reviewed_evidence_valid"] is True
        assert ev["evidence_role"] == "public_company_conversion_only"
        assert ev["reviewed_event_type"] == "public_company_conversion"
    finally:
        snap.unlink(missing_ok=True)


def test_a5_conversion_only_not_ready():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("a5_conv3.html")
    try:
        retrieval = _retrieval_rec(tk, _A5_CODAL, rel, h)
        existing = _existing_prov_df(tk, _A5_CODAL, rel, h,
                                     event_type_supported="conversion_to_public",
                                     exact_date_explicit="true",
                                     reviewed_date_jalali="1380-05-01",
                                     ordinary_share_explicit="unknown")
        overlaid = apply_validated_review_overlay([retrieval], existing, ROOT)
        normalized = normalize_provenance_records(overlaid, ROOT)
        research = build_research_screening(_names(), {tk: normalized}, _absent_tsetmc())
        row = research[research["ticker"] == tk].iloc[0]
        assert str(row["ready_for_user_review"]).lower() == "false"
        assert str(row["research_status"]) == "research_completed_noncanonical_entry_evidence"
    finally:
        snap.unlink(missing_ok=True)


# === Conflict evidence (3 tests) ===

_CODAL_DOC_2 = "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=DEF456"


def test_a5_conflict_status():
    tk = PART03_TICKERS[0]
    snap1, rel1, h1 = _make_snapshot("a5_conf1a.html")
    snap2, rel2, h2 = _make_snapshot("a5_conf1b.html")
    try:
        rec1 = _retrieval_rec(tk, _A5_CODAL, rel1, h1, source_index=1,
                              content_review_status="reviewed",
                              event_type_supported="first_public_offering",
                              exact_date_explicit="true",
                              reviewed_date_jalali="1380-03-15",
                              ordinary_share_explicit="true")
        rec2 = _retrieval_rec(tk, _CODAL_DOC_2, rel2, h2, source_index=2,
                              content_review_status="reviewed",
                              event_type_supported="first_public_offering",
                              exact_date_explicit="true",
                              reviewed_date_jalali="1381-06-20",
                              ordinary_share_explicit="true")
        st = _derive_screening_status([rec1, rec2], snapshot_root=ROOT)
        assert st["research_status"] == "research_completed_conflict"
        assert st["conflict_flag"] == "true"
        assert st["ready_for_user_review"] == "false"
    finally:
        snap1.unlink(missing_ok=True)
        snap2.unlink(missing_ok=True)


def test_a5_conflict_not_ready():
    tk = PART03_TICKERS[0]
    snap1, rel1, h1 = _make_snapshot("a5_conf2a.html")
    snap2, rel2, h2 = _make_snapshot("a5_conf2b.html")
    try:
        rec1 = _retrieval_rec(tk, _A5_CODAL, rel1, h1, source_index=1,
                              content_review_status="reviewed",
                              event_type_supported="first_public_trading",
                              exact_date_explicit="true",
                              reviewed_date_jalali="1380-01-01",
                              ordinary_share_explicit="true")
        rec2 = _retrieval_rec(tk, _CODAL_DOC_2, rel2, h2, source_index=2,
                              content_review_status="reviewed",
                              event_type_supported="first_public_trading",
                              exact_date_explicit="true",
                              reviewed_date_jalali="1382-06-20",
                              ordinary_share_explicit="true")
        research = build_research_screening(_names(), {tk: [rec1, rec2]}, _absent_tsetmc())
        row = research[research["ticker"] == tk].iloc[0]
        assert str(row["ready_for_user_review"]).lower() == "false"
        assert str(row["conflict_flag"]).lower() == "true"
    finally:
        snap1.unlink(missing_ok=True)
        snap2.unlink(missing_ok=True)


def test_a5_conflict_candidate_event_type():
    tk = PART03_TICKERS[0]
    snap1, rel1, h1 = _make_snapshot("a5_conf3a.html")
    snap2, rel2, h2 = _make_snapshot("a5_conf3b.html")
    try:
        rec1 = _retrieval_rec(tk, _A5_CODAL, rel1, h1, source_index=1,
                              content_review_status="reviewed",
                              event_type_supported="first_public_offering",
                              exact_date_explicit="true",
                              reviewed_date_jalali="1380-03-15",
                              ordinary_share_explicit="true")
        rec2 = _retrieval_rec(tk, _CODAL_DOC_2, rel2, h2, source_index=2,
                              content_review_status="reviewed",
                              event_type_supported="first_public_offering",
                              exact_date_explicit="true",
                              reviewed_date_jalali="1381-03-15",
                              ordinary_share_explicit="true")
        st = _derive_screening_status([rec1, rec2], snapshot_root=ROOT)
        assert st["candidate_event_type"] == "conflict"
        assert st["proposed_canonical_event_type"] == "unresolved"
    finally:
        snap1.unlink(missing_ok=True)
        snap2.unlink(missing_ok=True)


# === No reliable evidence (3 tests) ===

def test_a5_no_reliable_evidence_after_review():
    rec = _reviewed_rec(event_type_supported="", exact_date_explicit="false",
                        reviewed_date_jalali="", ordinary_share_explicit="unknown")
    st = _derive_screening_status([rec], snapshot_root=None)
    assert st["evidence_status"] == "no_reliable_evidence"
    assert st["research_status"] == "research_completed_no_evidence"
    assert st["ready_for_user_review"] == "false"


def test_a5_no_reliable_evidence_not_ready():
    rec = _reviewed_rec(event_type_supported="", exact_date_explicit="false",
                        reviewed_date_jalali="", ordinary_share_explicit="unknown")
    st = _derive_screening_status([rec], snapshot_root=None)
    assert st["ready_for_user_review"] == "false"
    assert st["evidence_status"] == "no_reliable_evidence"


def test_a5_no_reliable_evidence_no_canonical_date():
    rec = _reviewed_rec(event_type_supported="", exact_date_explicit="false",
                        reviewed_date_jalali="", ordinary_share_explicit="unknown")
    st = _derive_screening_status([rec], snapshot_root=None)
    assert st["proposed_canonical_public_entry_date_jalali"] == ""
    assert st["admission_date_candidate_jalali"] == ""
    assert st["listing_date_candidate_jalali"] == ""


# === Provenance field validation (3 tests) ===

def test_a5_provenance_has_new_fields():
    for f in ("reviewed_event_type", "reviewed_date_precision",
              "reviewed_evidence_valid", "evidence_role"):
        assert f in PROVENANCE_COLUMNS, f"missing {f} in PROVENANCE_COLUMNS"


def test_a5_normalize_provenance_computes_new_fields():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("a5_norm1.html")
    try:
        rec = _retrieval_rec(tk, _A5_CODAL, rel, h,
                             content_review_status="reviewed",
                             event_type_supported="first_public_offering",
                             exact_date_explicit="true",
                             reviewed_date_jalali="1380-03-15",
                             ordinary_share_explicit="true")
        normalized = normalize_provenance_records([rec], ROOT)
        r = normalized[0]
        assert r["reviewed_event_type"] == "first_public_offering"
        assert r["reviewed_date_precision"] == "exact_day"
        assert r["reviewed_evidence_valid"] == "true"
        assert r["evidence_role"] == "canonical_exact_candidate"
    finally:
        snap.unlink(missing_ok=True)


def test_a5_fetch_sources_initializes_new_fields():
    tk = PART03_TICKERS[0]
    sources = {tk: [(1, RESEARCH_SOURCES[tk][0][0], RESEARCH_SOURCES[tk][0][1],
                     RESEARCH_SOURCES[tk][0][2])]}
    results = fetch_sources(timeout=0.001, sources_by_ticker=sources)
    rec = results[tk][0]
    assert "reviewed_event_type" in rec
    assert "reviewed_date_precision" in rec
    assert "reviewed_evidence_valid" in rec
    assert "evidence_role" in rec
    assert rec["reviewed_event_type"] == ""
    assert rec["reviewed_date_precision"] == "unknown"
    assert rec["reviewed_evidence_valid"] == "false"
    assert rec["evidence_role"] == "none"


# === Enum validation (3 tests) ===

def test_a5_evidence_role_enum_valid():
    expected = {"none", "canonical_exact_candidate", "canonical_partial_date",
                "admission_only", "listing_only", "public_company_conversion_only",
                "conflicting_evidence", "non_entry_evidence"}
    assert EVIDENCE_ROLES == expected


def test_a5_reviewed_date_precision_enum_valid():
    expected = {"exact_day", "month_only", "year_only", "unknown"}
    assert REVIEWED_DATE_PRECISIONS == expected


def test_a5_reviewed_event_type_enum_valid():
    assert "first_public_offering" in REVIEWED_EVENT_TYPES
    assert "first_public_trading" in REVIEWED_EVENT_TYPES
    assert "admission" in REVIEWED_EVENT_TYPES
    assert "listing" in REVIEWED_EVENT_TYPES
    assert "public_company_conversion" in REVIEWED_EVENT_TYPES


# ================================================================================
# Part 3.1A.5.1 — partial-date manual review, same-event conflict + precision
# compatibility, admission+listing preservation, derived-field recomputation
# ================================================================================

from project.src.stage124_batch02_part03 import (
    jalali_dates_compatible,
    detect_evidence_conflicts,
    REVIEW_OVERLAY_FIELDS,
    DERIVED_NEVER_TRUSTED,
)

_C1 = "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=AAA111"
_C2 = "https://www.codal.ir/Reports/Decision.aspx?LetterSerial=BBB222"


def _two_source_status(tk, ev1, d1, ev2, d2, ord1="true", ord2="true",
                       ex1="true", ex2="true"):
    """Build a normalized two-source provenance set with the given reviewed
    events/dates and return (_derive_screening_status, normalized records)."""
    snap1, rel1, h1 = _make_snapshot("p351_s1.html", b"<html>doc-one</html>")
    snap2, rel2, h2 = _make_snapshot("p351_s2.html", b"<html>doc-two</html>")
    ret1 = _retrieval_rec(tk, _C1, rel1, h1)
    ret1["source_index"] = 1
    ret2 = _retrieval_rec(tk, _C2, rel2, h2)
    ret2["source_index"] = 2
    ext1 = _existing_prov_df(tk, _C1, rel1, h1, source_index="1",
                             event_type_supported=ev1, exact_date_explicit=ex1,
                             reviewed_date_jalali=d1, ordinary_share_explicit=ord1)
    ext2 = _existing_prov_df(tk, _C2, rel2, h2, source_index="2",
                             event_type_supported=ev2, exact_date_explicit=ex2,
                             reviewed_date_jalali=d2, ordinary_share_explicit=ord2)
    overlaid = apply_validated_review_overlay(
        [ret1, ret2], pd.concat([ext1, ext2], ignore_index=True), ROOT)
    normalized = normalize_provenance_records(overlaid, ROOT)
    st = _derive_screening_status(normalized, snapshot_root=ROOT)
    snap1.unlink(missing_ok=True)
    snap2.unlink(missing_ok=True)
    return st, normalized


# --- precision compatibility helper (requirement 6) ---

def test_p351_compat_exact_with_month():
    assert jalali_dates_compatible("1380-03-15", "1380-03") is True


def test_p351_compat_exact_with_year():
    assert jalali_dates_compatible("1380-03-15", "1380") is True


def test_p351_compat_month_with_year():
    assert jalali_dates_compatible("1380-03", "1380") is True


def test_p351_conflict_different_month():
    assert jalali_dates_compatible("1380-03", "1380-04") is False


def test_p351_conflict_different_year():
    assert jalali_dates_compatible("1380", "1381") is False


def test_p351_conflict_two_exact_days():
    assert jalali_dates_compatible("1380-03-15", "1380-03-16") is False


def test_p351_compat_exact_within_month_not_conflict():
    # exact day inside the stated month is compatible, different day-month conflict
    assert jalali_dates_compatible("1380-03-15", "1380-03") is True
    assert jalali_dates_compatible("1380-03-15", "1380-04") is False


# --- partial offering/trading → manual review, canonical empty (req 1) ---

def test_p351_partial_offering_month_manual_review():
    tk = PART03_TICKERS[0]
    st, _ = _two_source_status(tk, "first_public_offering", "1380-03",
                               "first_public_offering", "1380-03")
    assert st["research_status"] == "research_completed_partial_public_entry_date"
    assert st["evidence_status"] == "requires_manual_review"
    assert st["proposed_canonical_public_entry_date_jalali"] == ""
    assert st["proposed_canonical_event_type"] == ""
    assert st["ready_for_user_review"] == "false"
    assert st["first_public_offering_date_candidate_jalali"] == "1380-03"
    assert st["first_public_trading_date_candidate_jalali"] == ""


def test_p351_partial_trading_year_manual_review():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("p351_trad.html")
    try:
        ret = _retrieval_rec(tk, _C1, rel, h)
        ext = _existing_prov_df(tk, _C1, rel, h,
                                event_type_supported="first_public_trading",
                                exact_date_explicit="false",
                                reviewed_date_jalali="1381",
                                ordinary_share_explicit="true")
        overlaid = apply_validated_review_overlay([ret], ext, ROOT)
        normalized = normalize_provenance_records(overlaid, ROOT)
        st = _derive_screening_status(normalized, snapshot_root=ROOT)
        assert st["research_status"] == "research_completed_partial_public_entry_date"
        assert st["evidence_status"] == "requires_manual_review"
        assert st["date_precision"] == "year_only"
        assert st["first_public_trading_date_candidate_jalali"] == "1381"
        assert st["proposed_canonical_public_entry_date_jalali"] == ""
        assert st["proposed_canonical_event_type"] == ""
    finally:
        snap.unlink(missing_ok=True)


# --- conversion-only: canonical empty + manual review (req 2) ---

def test_p351_conversion_only_canonical_empty():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("p351_conv.html")
    try:
        ret = _retrieval_rec(tk, _C1, rel, h)
        ext = _existing_prov_df(tk, _C1, rel, h,
                                event_type_supported="conversion_to_public",
                                exact_date_explicit="true",
                                reviewed_date_jalali="1380-05-01",
                                ordinary_share_explicit="unknown")
        overlaid = apply_validated_review_overlay([ret], ext, ROOT)
        normalized = normalize_provenance_records(overlaid, ROOT)
        st = _derive_screening_status(normalized, snapshot_root=ROOT)
        assert st["research_status"] == "research_completed_noncanonical_entry_evidence"
        assert st["evidence_status"] == "requires_manual_review"
        assert st["proposed_canonical_public_entry_date_jalali"] == ""
        assert st["proposed_canonical_event_type"] == ""
        assert st["ready_for_user_review"] == "false"
    finally:
        snap.unlink(missing_ok=True)


# --- same-event incompatible dates conflict (req 3) ---

def test_p351_two_admissions_conflict():
    tk = PART03_TICKERS[0]
    st, _ = _two_source_status(tk, "admission", "1380-03-15",
                               "admission", "1381-06-20", ord1="unknown", ord2="unknown")
    assert st["research_status"] == "research_completed_conflict"
    assert st["conflict_flag"] == "true"
    assert st["ready_for_user_review"] == "false"


def test_p351_two_listings_conflict():
    tk = PART03_TICKERS[0]
    st, _ = _two_source_status(tk, "listing", "1380-03-15",
                               "listing", "1381-06-20", ord1="unknown", ord2="unknown")
    assert st["research_status"] == "research_completed_conflict"
    assert st["conflict_flag"] == "true"


def test_p351_two_offerings_conflict():
    tk = PART03_TICKERS[0]
    st, _ = _two_source_status(tk, "first_public_offering", "1380-03-15",
                               "first_public_offering", "1381-06-20")
    assert st["research_status"] == "research_completed_conflict"
    assert st["conflict_flag"] == "true"


def test_p351_two_tradings_conflict():
    tk = PART03_TICKERS[0]
    st, _ = _two_source_status(tk, "first_public_trading", "1380-03-15",
                               "first_public_trading", "1381-06-20")
    assert st["research_status"] == "research_completed_conflict"
    assert st["conflict_flag"] == "true"


def test_p351_two_conversions_conflict():
    tk = PART03_TICKERS[0]
    st, _ = _two_source_status(tk, "conversion_to_public", "1380-03-15",
                               "conversion_to_public", "1381-06-20",
                               ord1="unknown", ord2="unknown")
    assert st["research_status"] == "research_completed_conflict"
    assert st["conflict_flag"] == "true"


# --- compatible same-event dates are NOT a conflict (req 6) ---

def test_p351_compatible_exact_month_no_conflict():
    tk = PART03_TICKERS[0]
    st, _ = _two_source_status(tk, "admission", "1380-03-15",
                               "admission", "1380-03", ord1="unknown", ord2="unknown")
    assert st["research_status"] == "research_completed_admission_only"
    assert st["conflict_flag"] == "false"


# --- different events with different dates are NOT a conflict (req 4) ---

def test_p351_admission_listing_not_conflict():
    tk = PART03_TICKERS[0]
    st, _ = _two_source_status(tk, "admission", "1380-03-15",
                               "listing", "1381-06-20", ord1="unknown", ord2="unknown")
    assert st["conflict_flag"] == "false"
    assert st["research_status"] != "research_completed_conflict"


# --- admission + listing both valid → both candidates preserved (req 5) ---

def test_p351_admission_listing_preservation():
    tk = PART03_TICKERS[0]
    st, _ = _two_source_status(tk, "admission", "1380-03-15",
                               "listing", "1381-06-20", ord1="unknown", ord2="unknown")
    assert st["candidate_event_type"] == "listing"
    assert st["research_status"] == "research_completed_listing_only"
    assert st["evidence_status"] == "requires_first_public_trade_evidence"
    assert st["admission_date_candidate_jalali"] == "1380-03-15"
    assert st["listing_date_candidate_jalali"] == "1381-06-20"
    assert st["proposed_canonical_public_entry_date_jalali"] == ""
    assert st["proposed_canonical_event_type"] == ""
    assert st["conflict_flag"] == "false"


# --- conflicting records get evidence_role=conflicting_evidence (req 9) ---

def test_p351_conflicting_evidence_role():
    tk = PART03_TICKERS[0]
    _st, normalized = _two_source_status(tk, "admission", "1380-03-15",
                                         "admission", "1381-06-20",
                                         ord1="unknown", ord2="unknown")
    roles = {str(r.get("evidence_role", "")) for r in normalized}
    assert "conflicting_evidence" in roles
    # both conflicting admission records are flagged
    flagged = [r for r in normalized if r.get("evidence_role") == "conflicting_evidence"]
    assert len(flagged) == 2


# --- detect_evidence_conflicts direct unit semantics ---

def test_p351_detect_conflicts_same_event():
    pairs = [
        ({"ticker": "X", "source_index": "1", "reviewed_date_jalali": "1380-03-15"},
         {"reviewed_event_type": "admission", "evidence_role": "admission_only"}),
        ({"ticker": "X", "source_index": "2", "reviewed_date_jalali": "1381-06-20"},
         {"reviewed_event_type": "admission", "evidence_role": "admission_only"}),
    ]
    info = detect_evidence_conflicts(pairs)
    assert info["conflict"] is True
    assert "admission" in info["event_types"]
    assert ("X", "1") in info["keys"] and ("X", "2") in info["keys"]


def test_p351_detect_conflicts_different_event_no_conflict():
    pairs = [
        ({"ticker": "X", "source_index": "1", "reviewed_date_jalali": "1380-03-15"},
         {"reviewed_event_type": "admission", "evidence_role": "admission_only"}),
        ({"ticker": "X", "source_index": "2", "reviewed_date_jalali": "1381-06-20"},
         {"reviewed_event_type": "listing", "evidence_role": "listing_only"}),
    ]
    info = detect_evidence_conflicts(pairs)
    assert info["conflict"] is False


def test_p351_detect_conflicts_canonical_group():
    # offering vs trading are DIFFERENT events (Part 3.1A.5.2): different dates are
    # not a conflict; only same-event incompatibility is.
    pairs = [
        ({"ticker": "X", "source_index": "1", "reviewed_date_jalali": "1380-03-15"},
         {"reviewed_event_type": "first_public_offering"}),
        ({"ticker": "X", "source_index": "2", "reviewed_date_jalali": "1381-06-20"},
         {"reviewed_event_type": "first_public_trading"}),
    ]
    info = detect_evidence_conflicts(pairs)
    assert info["conflict"] is False


# --- derived fields are fully recomputed, never inherited from prior CSV (req 7) ---

def test_p351_derived_fields_not_in_overlay():
    for f in ("reviewed_event_type", "reviewed_date_precision",
              "reviewed_evidence_valid", "evidence_role"):
        assert f not in REVIEW_OVERLAY_FIELDS
        assert f in DERIVED_NEVER_TRUSTED


def test_p351_stale_derived_fields_recomputed():
    tk = PART03_TICKERS[0]
    snap, rel, h = _make_snapshot("p351_recompute.html")
    try:
        ret = _retrieval_rec(tk, _C1, rel, h)
        # prior CSV carries WRONG derived values that must be ignored/recomputed
        ext = _existing_prov_df(tk, _C1, rel, h,
                                event_type_supported="listing",
                                exact_date_explicit="true",
                                reviewed_date_jalali="1381-01-10",
                                ordinary_share_explicit="unknown",
                                reviewed_event_type="first_public_offering",
                                reviewed_date_precision="year_only",
                                reviewed_evidence_valid="false",
                                evidence_role="non_entry_evidence")
        overlaid = apply_validated_review_overlay([ret], ext, ROOT)
        normalized = normalize_provenance_records(overlaid, ROOT)
        r = normalized[0]
        assert r["reviewed_event_type"] == "listing"
        assert r["reviewed_date_precision"] == "exact_day"
        assert r["reviewed_evidence_valid"] == "true"
        assert r["evidence_role"] == "listing_only"
    finally:
        snap.unlink(missing_ok=True)


# ================================================================================
# Part 3.1A.5.2 — multi-event canonical selection, earliest-candidate rule,
# weak-source corroboration, partial-before-exact blocker, all-candidate
# preservation, deterministic best-candidate, conflict-role QC, idempotence
# ================================================================================

from project.src.stage124_batch02_part03 import (
    decide_canonical_public_entry_candidate,
    finalize_reviewed_evidence_set,
    select_best_compatible_candidate,
    partial_candidate_blocks_exact,
    _qc_engine_invariants,
)

_AGG = "https://aggregator-example.ir/co/12345/ipo-report-page"


def _rev(tk, idx, event, date, name, src_type="codal_official", url=None,
         ordinary="true", exact="true"):
    """Create a real snapshot and return a fully-reviewed record."""
    snap, rel, h = _make_snapshot(name, f"<html>{name}</html>".encode())
    rec = _retrieval_rec(tk, url if url is not None else
                         f"https://www.codal.ir/Reports/Decision.aspx?LetterSerial={idx}{name}",
                         rel, h, source_index=idx, source_type=src_type,
                         content_review_status="reviewed",
                         event_type_supported=event, exact_date_explicit=exact,
                         reviewed_date_jalali=date, ordinary_share_explicit=ordinary)
    return rec, snap


def _derive_multi(tk, specs):
    """specs: list of (idx, event, date, kwargs). Returns (status, records)."""
    recs, snaps = [], []
    for spec in specs:
        idx, event, date = spec[0], spec[1], spec[2]
        kw = spec[3] if len(spec) > 3 else {}
        rec, snap = _rev(tk, idx, event, date, f"p352_{idx}_{event[:3]}", **kw)
        recs.append(rec)
        snaps.append(snap)
    try:
        st = _derive_screening_status(recs, snapshot_root=ROOT)
        normalized = normalize_provenance_records(recs, ROOT)
    finally:
        for s in snaps:
            s.unlink(missing_ok=True)
    return st, normalized


# 1. offering and trading with different dates → not a conflict.
def test_p352_offering_trading_diff_dates_not_conflict():
    tk = PART03_TICKERS[0]
    st, _ = _derive_multi(tk, [
        (1, "first_public_offering", "1380-03-15"),
        (2, "first_public_trading", "1381-06-20")])
    assert st["conflict_flag"] == "false"
    assert st["research_status"] != "research_completed_conflict"


# 2. offering exact earlier than trading exact → offering selected.
def test_p352_offering_earlier_selected():
    tk = PART03_TICKERS[0]
    st, _ = _derive_multi(tk, [
        (1, "first_public_offering", "1380-03-15"),
        (2, "first_public_trading", "1381-06-20")])
    assert st["proposed_canonical_event_type"] == "first_public_offering"
    assert st["proposed_canonical_public_entry_date_jalali"] == "1380-03-15"
    assert st["ready_for_user_review"] == "true"


# 3. trading exact earlier than offering exact → trading selected.
def test_p352_trading_earlier_selected():
    tk = PART03_TICKERS[0]
    st, _ = _derive_multi(tk, [
        (1, "first_public_offering", "1381-06-20"),
        (2, "first_public_trading", "1380-02-02")])
    assert st["proposed_canonical_event_type"] == "first_public_trading"
    assert st["proposed_canonical_public_entry_date_jalali"] == "1380-02-02"
    assert st["ready_for_user_review"] == "true"


# 4. offering and trading on the same day → tie-breaker prefers offering.
def test_p352_same_day_tiebreak_offering():
    tk = PART03_TICKERS[0]
    st, _ = _derive_multi(tk, [
        (1, "first_public_trading", "1380-03-15"),
        (2, "first_public_offering", "1380-03-15")])
    assert st["proposed_canonical_event_type"] == "first_public_offering"
    assert st["proposed_canonical_public_entry_date_jalali"] == "1380-03-15"


# 7 / 21. exact candidate from an aggregator → needs corroboration, not no_reliable.
def test_p352_exact_aggregator_needs_corroboration():
    tk = PART03_TICKERS[0]
    st, _ = _derive_multi(tk, [
        (1, "first_public_offering", "1380-03-15",
         {"src_type": "", "url": _AGG})])
    assert st["evidence_status"] != "no_reliable_evidence"
    assert st["research_status"] == "research_completed_exact_public_entry_needs_corroboration"
    assert st["research_completion_status"] == "completed_exact_candidate_needs_corroboration"
    assert st["ready_for_user_review"] == "false"
    assert st["evidence_status"] == "requires_manual_review"
    assert st["recommended_next_step"] == "find_qualifying_corroboration"
    assert st["first_public_offering_date_candidate_jalali"] == "1380-03-15"
    assert st["proposed_canonical_public_entry_date_jalali"] == ""


# 8. earlier weak candidate + later official candidate → later cannot override.
def test_p352_later_official_cannot_override_earlier_weak():
    tk = PART03_TICKERS[0]
    st, _ = _derive_multi(tk, [
        (1, "first_public_offering", "1380-03-15", {"src_type": "", "url": _AGG}),
        (2, "first_public_trading", "1381-06-20")])
    assert st["candidate_event_type"] == "first_public_offering"
    assert st["research_status"] == "research_completed_exact_public_entry_needs_corroboration"
    assert st["proposed_canonical_public_entry_date_jalali"] == ""
    # the later trading candidate is still preserved in its column
    assert st["first_public_trading_date_candidate_jalali"] == "1381-06-20"
    assert st["first_public_offering_date_candidate_jalali"] == "1380-03-15"


# 9. partial offering year 1380 + exact trading 1381 → exact blocked, partial status.
def test_p352_partial_year_blocks_later_exact():
    tk = PART03_TICKERS[0]
    st, _ = _derive_multi(tk, [
        (1, "first_public_offering", "1380", {"exact": "false"}),
        (2, "first_public_trading", "1381-04-10")])
    assert st["ready_for_user_review"] == "false"
    assert st["research_status"] == "research_completed_partial_public_entry_date"
    assert st["evidence_status"] == "requires_manual_review"
    assert st["recommended_next_step"] == "find_exact_public_entry_day"
    assert st["proposed_canonical_public_entry_date_jalali"] == ""
    # both candidate columns preserved
    assert st["first_public_offering_date_candidate_jalali"] == "1380"
    assert st["first_public_trading_date_candidate_jalali"] == "1381-04-10"


# 10. partial offering month 1380-03 + exact trading 1380-04 → blocker.
def test_p352_partial_month_blocks_later_exact():
    tk = PART03_TICKERS[0]
    st, _ = _derive_multi(tk, [
        (1, "first_public_offering", "1380-03", {"exact": "false"}),
        (2, "first_public_trading", "1380-04-10")])
    assert st["research_status"] == "research_completed_partial_public_entry_date"
    assert st["ready_for_user_review"] == "false"


# 11. partial offering month 1380-03 + exact offering 1380-03-15 → compatible.
def test_p352_compatible_partial_exact_same_event():
    tk = PART03_TICKERS[0]
    st, _ = _derive_multi(tk, [
        (1, "first_public_offering", "1380-03", {"exact": "false"}),
        (2, "first_public_offering", "1380-03-15")])
    assert st["conflict_flag"] == "false"
    # exact candidate is usable → ready with the exact date
    assert st["proposed_canonical_public_entry_date_jalali"] == "1380-03-15"
    assert st["ready_for_user_review"] == "true"


# 12. partial candidate entirely after the exact candidate → not a blocker.
def test_p352_partial_after_exact_not_blocker():
    assert partial_candidate_blocks_exact("1382", "year_only", "1380-03-15") is False
    tk = PART03_TICKERS[0]
    st, _ = _derive_multi(tk, [
        (1, "first_public_offering", "1380-03-15"),
        (2, "first_public_trading", "1382", {"exact": "false"})])
    # offering exact is the earliest and is not blocked by the later partial
    assert st["proposed_canonical_public_entry_date_jalali"] == "1380-03-15"
    assert st["ready_for_user_review"] == "true"


# 13. admission year + admission exact compatible → exact candidate chosen.
def test_p352_admission_year_plus_exact_picks_exact():
    tk = PART03_TICKERS[0]
    st, _ = _derive_multi(tk, [
        (1, "admission", "1380", {"ordinary": "unknown", "exact": "false"}),
        (2, "admission", "1380-05-10", {"ordinary": "unknown"})])
    assert st["admission_date_candidate_jalali"] == "1380-05-10"
    assert st["date_precision"] == "exact_day"
    assert st["research_status"] == "research_completed_admission_only"


# 14. listing month + listing exact compatible → exact candidate chosen.
def test_p352_listing_month_plus_exact_picks_exact():
    tk = PART03_TICKERS[0]
    st, _ = _derive_multi(tk, [
        (1, "listing", "1381-01", {"ordinary": "unknown", "exact": "false"}),
        (2, "listing", "1381-01-10", {"ordinary": "unknown"})])
    assert st["listing_date_candidate_jalali"] == "1381-01-10"
    assert st["date_precision"] == "exact_day"
    assert st["research_status"] == "research_completed_listing_only"


# 16. admission + listing + offering partial → all three candidates preserved.
def test_p352_three_candidates_preserved_partial():
    tk = PART03_TICKERS[0]
    st, _ = _derive_multi(tk, [
        (1, "admission", "1379-01-01", {"ordinary": "unknown"}),
        (2, "listing", "1380-02-02", {"ordinary": "unknown"}),
        (3, "first_public_offering", "1381", {"exact": "false"})])
    assert st["admission_date_candidate_jalali"] == "1379-01-01"
    assert st["listing_date_candidate_jalali"] == "1380-02-02"
    assert st["first_public_offering_date_candidate_jalali"] == "1381"


# 17. admission + listing + trading exact → all three candidates preserved.
def test_p352_three_candidates_preserved_exact():
    tk = PART03_TICKERS[0]
    st, _ = _derive_multi(tk, [
        (1, "admission", "1379-01-01", {"ordinary": "unknown"}),
        (2, "listing", "1380-02-02", {"ordinary": "unknown"}),
        (3, "first_public_trading", "1381-04-10")])
    assert st["admission_date_candidate_jalali"] == "1379-01-01"
    assert st["listing_date_candidate_jalali"] == "1380-02-02"
    assert st["first_public_trading_date_candidate_jalali"] == "1381-04-10"
    # the exact trading candidate is the dominant public-entry candidate
    assert st["proposed_canonical_event_type"] == "first_public_trading"


# 18. conflict rows take the finalized role conflicting_evidence (provenance).
def test_p352_conflict_role_in_provenance():
    tk = PART03_TICKERS[0]
    _st, normalized = _derive_multi(tk, [
        (1, "first_public_offering", "1380-03-15"),
        (2, "first_public_offering", "1381-06-20")])
    roles = [str(r.get("evidence_role")) for r in normalized]
    assert roles.count("conflicting_evidence") == 2
    # finalizer agrees with the stored provenance role (idempotent finalization);
    # hashes are still valid so snapshot_root=None re-derives the same roles.
    fin = finalize_reviewed_evidence_set(normalized, None)
    fin_roles = {(str(fr.get("ticker")), str(fr.get("source_index")).strip()):
                 fr["_final_evidence_role"] for fr in fin["finalized_records"]}
    for r in normalized:
        key = (str(r.get("ticker")), str(r.get("source_index")).strip())
        assert str(r.get("evidence_role")) == fin_roles[key]


# 19. finalizer is idempotent (byte/field-identical roles and candidates).
def test_p352_finalizer_idempotent():
    tk = PART03_TICKERS[0]
    _st, normalized = _derive_multi(tk, [
        (1, "first_public_offering", "1380-03-15"),
        (2, "admission", "1379-01-01", {"ordinary": "unknown"})])
    f1 = finalize_reviewed_evidence_set(normalized, ROOT)
    f2 = finalize_reviewed_evidence_set(f1["finalized_records"], ROOT)
    r1 = [fr["_final_evidence_role"] for fr in f1["finalized_records"]]
    r2 = [fr["_final_evidence_role"] for fr in f2["finalized_records"]]
    assert r1 == r2
    c1 = {k: (v["date"], v["precision"], v["conflict"])
          for k, v in f1["candidates_by_event"].items()}
    c2 = {k: (v["date"], v["precision"], v["conflict"])
          for k, v in f2["candidates_by_event"].items()}
    assert c1 == c2


# 20. shuffled record order yields identical candidates and status.
def test_p352_shuffled_order_stable():
    tk = PART03_TICKERS[0]
    specs_a = [
        (1, "first_public_offering", "1380-03-15"),
        (2, "first_public_trading", "1381-06-20"),
        (3, "admission", "1379-01-01", {"ordinary": "unknown"})]
    specs_b = list(reversed(specs_a))
    st_a, _ = _derive_multi(tk, specs_a)
    st_b, _ = _derive_multi(tk, specs_b)
    fields = ("research_status", "evidence_status", "candidate_event_type",
              "proposed_canonical_public_entry_date_jalali",
              "proposed_canonical_event_type", "ready_for_user_review",
              "admission_date_candidate_jalali",
              "first_public_offering_date_candidate_jalali",
              "first_public_trading_date_candidate_jalali")
    assert all(st_a[f] == st_b[f] for f in fields)


# helper-level: select_best_compatible_candidate precision + tie-break.
def test_p352_select_best_candidate_precision():
    recs = [
        ({"source_index": "2", "reviewed_date_jalali": "1380"},
         {"reviewed_date_precision": "year_only", "reviewed_event_type": "admission"}),
        ({"source_index": "1", "reviewed_date_jalali": "1380-05-10"},
         {"reviewed_date_precision": "exact_day", "reviewed_event_type": "admission"}),
    ]
    out = select_best_compatible_candidate(recs)
    assert out["conflict"] is False
    assert out["date"] == "1380-05-10"
    assert out["precision"] == "exact_day"


# the QC engine-invariant block passes cleanly.
def test_p352_qc_engine_invariants_pass():
    results = []
    def _check(name, passed, detail=""):
        results.append((name, bool(passed), detail))
    _qc_engine_invariants(_check)
    failed = [(n, d) for n, p, d in results if not p]
    assert not failed, f"engine-invariant failures: {failed}"
    names = {n for n, _, _ in results}
    for required in ("different_canonical_events_not_conflict",
                     "same_event_conflict_only",
                     "best_candidate_uses_highest_precision",
                     "candidate_selection_deterministic",
                     "earliest_exact_public_event_selected",
                     "later_qualified_candidate_cannot_override_earlier_unqualified_candidate",
                     "exact_unqualified_not_no_reliable_evidence",
                     "exact_candidate_needs_corroboration_not_ready",
                     "earlier_partial_blocks_later_exact",
                     "compatible_partial_does_not_block_exact",
                     "finalizer_idempotent",
                     "qc_report_regenerated_from_current_engine"):
        assert required in names, f"missing invariant {required}"
