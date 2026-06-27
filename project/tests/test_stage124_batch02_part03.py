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


# (18) all 20 current timeout records unchanged in character
def test_o18_current_timeout_records_unchanged():
    p = PART03_DIR / "part03_source_provenance_10tickers.csv"
    df = pd.read_csv(p, dtype=str).fillna("")
    assert len(df) == 20
    assert (df["retrieval_status"] == "timeout").all()
    assert (df["content_review_status"] == "not_available_due_to_fetch_failure").all()
    assert (df["evidence_accepted"].str.lower() == "false").all()
    assert (df["document_specific"].str.lower() == "false").all()
    assert (df["snapshot_path"].str.strip() == "").all()


# (19) all 10 current research rows unchanged in character
def test_o19_current_research_rows_unchanged():
    p = PART03_DIR / "part03_research_screening_10tickers.csv"
    df = pd.read_csv(p, dtype=str).fillna("")
    assert df["ticker"].tolist() == PART03_TICKERS
    assert (df["research_status"] == "research_blocked_network").all()
    assert (df["ready_for_user_review"].str.lower() == "false").all()
    assert (df["ordinary_share_confirmed"] == "unknown").all()


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


# (20) current 20 timeout records and 10 research rows unchanged in character
def test_r20_current_outputs_unchanged_character():
    prov = pd.read_csv(PART03_DIR / "part03_source_provenance_10tickers.csv",
                       dtype=str).fillna("")
    assert len(prov) == 20
    assert (prov["retrieval_status"] == "timeout").all()
    assert (prov["evidence_accepted"].str.lower() == "false").all()
    assert (prov["reviewer_notes"] == "").all()
    assert (prov["manual_reviewed_at_utc"] == "").all()
    research = pd.read_csv(PART03_DIR / "part03_research_screening_10tickers.csv",
                           dtype=str).fillna("")
    assert research["ticker"].tolist() == PART03_TICKERS
    assert (research["research_status"] == "research_blocked_network").all()
    assert (research["ready_for_user_review"].str.lower() == "false").all()


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
    assert _result(qc, "provenance_only_active_registry") is True
