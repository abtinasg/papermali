"""Independent tests for Stage124 Batch 2 Part 2 screening."""

import json
import hashlib
from pathlib import Path

import pandas as pd
import pytest

from project.src.stage124_batch02_part02 import (
    PART02_TICKERS,
    RESEARCH_DATA,
    PART02_DIR,
    FROZEN_FILES,
    build_tickers_df,
    build_research_screening,
    build_source_provenance,
    build_tsetmc_audit,
    run_part02_qc,
    build_hash_manifest,
    _tsetmc_disposition,
    _programmer_recommendation,
    _ambiguity_notes,
)
from project.src.stage124_batch02_v2 import (
    PILOT15,
    sha,
    jalali_to_gregorian_str,
    ROOT,
    STAGE123_INPUT,
    STAGE122_INPUT,
    EXPECTED_STAGE123_SHA,
    EXPECTED_STAGE122_SHA,
    PARTIAL_MASTER,
)


# ---- helpers -------------------------------------------------------------------
def _fake_company_names():
    return {tk: f"Company_{tk}" for tk in PART02_TICKERS}


def _fake_probe_results():
    return {
        tk: {
            "instrument_match_status": "network_unreachable",
            "tsetmc_candidate_date_jalali": "",
            "tsetmc_candidate_date_gregorian": "",
            "probe_retrieved_at": "2025-01-01T00:00:00Z",
            "probe_raw_sha256": "",
            "probe_notes": "network unreachable",
            "probe_source": "live_probe",
            "selected_inscode": "",
            "ordinary_instrument_count": "",
            "ordinary_instrument_candidates_json": "[]",
            "multiple_ordinary_instruments": 0,
        }
        for tk in PART02_TICKERS
    }


def _build_fixture():
    names = _fake_company_names()
    probes = _fake_probe_results()
    tickers_df = build_tickers_df(names)
    research_df = build_research_screening(names, probes)
    provenance_df = build_source_provenance(probes, "2025-01-01T00:00:00Z")
    tsetmc_df = build_tsetmc_audit(probes)
    return tickers_df, research_df, provenance_df, tsetmc_df


# ---- tests ---------------------------------------------------------------------
class TestTickerFiltering:
    def test_exactly_10_tickers(self):
        assert len(PART02_TICKERS) == 10

    def test_no_pilot15_overlap(self):
        assert len(set(PART02_TICKERS) & PILOT15) == 0

    def test_tickers_df_has_10_rows(self):
        df = build_tickers_df(_fake_company_names())
        assert len(df) == 10

    def test_no_duplicates(self):
        df = build_tickers_df(_fake_company_names())
        assert df["ticker"].duplicated().sum() == 0

    def test_ticker_set_matches(self):
        df = build_tickers_df(_fake_company_names())
        assert set(df["ticker"]) == set(PART02_TICKERS)


class TestAdmissionOnlyCanonical:
    def test_admission_only_has_empty_canonical(self):
        for tk in ["بموتو", "حپترو", "خمحور"]:
            info = RESEARCH_DATA[tk]
            assert info["proposed_canonical_public_entry_date_jalali"] == ""
            assert info["evidence_status"] == "requires_first_public_trade_evidence"

    def test_listing_only_has_empty_canonical(self):
        for tk in ["ثشرق", "ثنوسا", "خرینگ"]:
            info = RESEARCH_DATA[tk]
            assert info["proposed_canonical_public_entry_date_jalali"] == ""
            assert info["evidence_status"] == "requires_first_public_trade_evidence"

    def test_no_admission_in_canonical_event_type(self):
        for tk, info in RESEARCH_DATA.items():
            ev = info["proposed_canonical_event_type"]
            if ev:
                assert ev in ("first_public_offering", "first_public_trading"), \
                    f"{tk}: {ev} is not a canonical event type"


class TestReadyForUserReview:
    def test_only_hkeshti_ready(self):
        ready = [tk for tk, info in RESEARCH_DATA.items()
                 if info["ready_for_user_review"] == "true"]
        assert ready == ["حکشتی"]

    def test_hkeshti_is_exact_day(self):
        assert RESEARCH_DATA["حکشتی"]["date_precision"] == "exact_day"
        assert RESEARCH_DATA["حکشتی"]["evidence_status"] == "candidate_supported"

    def test_month_year_not_ready(self):
        for tk in ["خاذین", "خبهمن", "ختوقا"]:
            assert RESEARCH_DATA[tk]["ready_for_user_review"] == "false"
            assert RESEARCH_DATA[tk]["date_precision"] in ("month_only", "year_only")

    def test_admission_only_not_ready(self):
        for tk in ["بموتو", "ثشرق", "ثنوسا", "حپترو", "خرینگ", "خمحور"]:
            assert RESEARCH_DATA[tk]["ready_for_user_review"] == "false"


class TestNetworkUnreachable:
    def test_disposition_preserves_network_unreachable(self):
        assert _tsetmc_disposition("network_unreachable", False) == "network_unreachable"

    def test_disposition_not_no_candidate(self):
        disp = _tsetmc_disposition("network_unreachable", False)
        assert disp != "no_candidate"

    def test_tsetmc_audit_preserves_status(self):
        probes = _fake_probe_results()
        df = build_tsetmc_audit(probes)
        for _, r in df.iterrows():
            assert r["instrument_match_status"] == "network_unreachable"
            assert r["tsetmc_candidate_disposition"] == "network_unreachable"


class TestDateConversions:
    def test_hkeshti_gregorian(self):
        g = jalali_to_gregorian_str("1387-02-28")
        assert g == "2008-05-17"

    def test_bemoto_admission_gregorian(self):
        g = jalali_to_gregorian_str("1369-12-28")
        assert g == "1991-03-19"

    def test_hepetro_admission_gregorian(self):
        g = jalali_to_gregorian_str("1382-05-06")
        assert g == "2003-07-28"

    def test_khamhor_admission_gregorian(self):
        g = jalali_to_gregorian_str("1383-08-25")
        assert g == "2004-11-15"

    def test_thenusa_listing_gregorian(self):
        g = jalali_to_gregorian_str("1383-10-09")
        assert g == "2004-12-29"

    def test_khring_listing_gregorian(self):
        g = jalali_to_gregorian_str("1382-12-16")
        assert g == "2004-03-06"

    def test_theshargh_listing_gregorian(self):
        g = jalali_to_gregorian_str("1393-04-04")
        assert g == "2014-06-25"


class TestProvenance:
    def test_each_ticker_has_at_least_2_sources(self):
        df = build_source_provenance(_fake_probe_results(), "2025-01-01T00:00:00Z")
        for tk in PART02_TICKERS:
            rows = df[df["ticker"] == tk]
            assert len(rows) >= 2, f"{tk}: only {len(rows)} sources"

    def test_tsetmc_source_present(self):
        df = build_source_provenance(_fake_probe_results(), "2025-01-01T00:00:00Z")
        for tk in PART02_TICKERS:
            tsetmc_rows = df[(df["ticker"] == tk) & (df["source_type"] == "tsetmc_api")]
            assert len(tsetmc_rows) == 1, f"{tk}: missing tsetmc source"

    def test_retrieval_status_network_unreachable(self):
        df = build_source_provenance(_fake_probe_results(), "2025-01-01T00:00:00Z")
        for tk in PART02_TICKERS:
            tsetmc_row = df[(df["ticker"] == tk) & (df["source_type"] == "tsetmc_api")].iloc[0]
            assert tsetmc_row["retrieval_status"] == "network_unreachable"


class TestHashManifest:
    def test_manifest_has_sha256(self):
        tmp = Path("/tmp/test_part02_manifest.csv")
        df = build_hash_manifest([(tmp, "test")], "abc123")
        assert "sha256" in df.columns
        assert "relative_path" in df.columns
        assert "file_role" in df.columns

    def test_manifest_sha256_correct(self):
        tmp = Path("/tmp/_test_part02_sha.csv")
        tmp.write_text("hello", encoding="utf-8")
        df = build_hash_manifest([(tmp, "test")], "abc123")
        expected = hashlib.sha256(b"hello").hexdigest()
        assert df.iloc[0]["sha256"] == expected
        tmp.unlink()


class TestQC:
    def test_qc_passes_with_valid_data(self):
        tickers_df, research_df, prov_df, tsetmc_df = _build_fixture()
        frozen = {str(fp): sha(fp) for fp in FROZEN_FILES if fp.exists()}
        qc = run_part02_qc(tickers_df, research_df, prov_df, tsetmc_df, frozen, frozen)
        assert qc["all_pass"], [
            a for a in qc["assertions"] if not a["passed"]
        ]

    def test_qc_fails_with_wrong_ticker_count(self):
        tickers_df, research_df, prov_df, tsetmc_df = _build_fixture()
        research_df = pd.concat([research_df, research_df.iloc[:1]], ignore_index=True)
        frozen = {str(fp): sha(fp) for fp in FROZEN_FILES if fp.exists()}
        qc = run_part02_qc(tickers_df, research_df, prov_df, tsetmc_df, frozen, frozen)
        assert not qc["all_pass"]

    def test_qc_fails_with_pilot15(self):
        names = _fake_company_names()
        names["خساپا"] = "Saipa"
        tickers_df = build_tickers_df(names)
        tickers_df = pd.concat([
            tickers_df,
            pd.DataFrame([{"ticker": "خساپا", "ticker_normalized": "خساپا", "company_name": "Saipa"}])
        ], ignore_index=True)
        probes = _fake_probe_results()
        probes["خساپا"] = probes["بموتو"]
        research_df = build_research_screening(names, probes)
        research_df = pd.concat([
            research_df,
            research_df.iloc[:1].assign(ticker="خساپا")
        ], ignore_index=True)
        prov_df = build_source_provenance(probes, "2025-01-01T00:00:00Z")
        tsetmc_df = build_tsetmc_audit(probes)
        frozen = {str(fp): sha(fp) for fp in FROZEN_FILES if fp.exists()}
        qc = run_part02_qc(tickers_df, research_df, prov_df, tsetmc_df, frozen, frozen)
        assert not qc["all_pass"]

    def test_qc_fails_with_admission_canonical(self):
        tickers_df, research_df, prov_df, tsetmc_df = _build_fixture()
        research_df.loc[research_df["ticker"] == "بموتو",
                        "proposed_canonical_public_entry_date_jalali"] = "1369-12-28"
        frozen = {str(fp): sha(fp) for fp in FROZEN_FILES if fp.exists()}
        qc = run_part02_qc(tickers_df, research_df, prov_df, tsetmc_df, frozen, frozen)
        assert not qc["all_pass"]

    def test_qc_fails_with_ready_for_month_only(self):
        tickers_df, research_df, prov_df, tsetmc_df = _build_fixture()
        research_df.loc[research_df["ticker"] == "خاذین", "ready_for_user_review"] = "true"
        frozen = {str(fp): sha(fp) for fp in FROZEN_FILES if fp.exists()}
        qc = run_part02_qc(tickers_df, research_df, prov_df, tsetmc_df, frozen, frozen)
        assert not qc["all_pass"]

    def test_qc_fails_with_frozen_change(self):
        tickers_df, research_df, prov_df, tsetmc_df = _build_fixture()
        frozen_before = {str(fp): sha(fp) for fp in FROZEN_FILES if fp.exists()}
        frozen_after = dict(frozen_before)
        first_key = next(iter(frozen_after))
        frozen_after[first_key] = "0" * 64
        qc = run_part02_qc(tickers_df, research_df, prov_df, tsetmc_df,
                           frozen_before, frozen_after)
        assert not qc["all_pass"]


class TestFrozenIntegrity:
    def test_stage123_sha_matches(self):
        assert sha(STAGE123_INPUT) == EXPECTED_STAGE123_SHA

    def test_stage122_sha_matches(self):
        assert sha(STAGE122_INPUT) == EXPECTED_STAGE122_SHA

    def test_partial_master_exists(self):
        assert PARTIAL_MASTER.exists()


class TestProgrammerRecommendation:
    def test_candidate_supported(self):
        info = RESEARCH_DATA["حکشتی"]
        assert _programmer_recommendation(info) == "recommend_user_review"

    def test_admission_only(self):
        info = RESEARCH_DATA["بموتو"]
        assert _programmer_recommendation(info) == "requires_first_public_trade_evidence"

    def test_manual_review(self):
        info = RESEARCH_DATA["خاذین"]
        assert _programmer_recommendation(info) == "requires_manual_review_for_exact_date"
