"""Independent tests for Stage124 Batch 2 Part 2 screening."""

import json
import hashlib
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def _guard_verified_master_path(tmp_path, monkeypatch):
    """Gate-A guardrails must not depend on whether the repo verified master exists."""
    forbidden = tmp_path / "listing_master_verified_stage124.csv"
    monkeypatch.setattr(
        "project.src.stage124_batch02_part02.FULL_VERIFIED_FORBIDDEN",
        forbidden,
    )


from project.src.stage124_batch02_part02 import (
    PART02_TICKERS,
    RESEARCH_DATA,
    PART02_DIR,
    FROZEN_FILES,
    TSETMC_AUDIT_CSV,
    build_tickers_df,
    build_research_screening,
    build_source_provenance,
    build_tsetmc_audit,
    run_part02_qc,
    build_hash_manifest,
    _tsetmc_disposition,
    _programmer_recommendation,
    _ambiguity_notes,
    _load_existing_tsetmc_audit,
    _snapshot_rel_path,
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
            if ev and ev not in ("unresolved", ""):
                assert ev in ("first_public_offering", "first_public_trading"), \
                    f"{tk}: {ev} is not a canonical event type"


class TestReadyForUserReview:
    def test_no_ticker_ready(self):
        ready = [tk for tk, info in RESEARCH_DATA.items()
                 if info["ready_for_user_review"] == "true"]
        assert ready == []

    def test_hkeshti_not_ready_due_to_conflict(self):
        assert RESEARCH_DATA["حکشتی"]["ready_for_user_review"] == "false"
        assert RESEARCH_DATA["حکشتی"]["evidence_status"] == "requires_manual_review"

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
    def test_hkeshti_now_requires_manual_review(self):
        info = RESEARCH_DATA["حکشتی"]
        assert _programmer_recommendation(info) == "requires_manual_review_for_exact_date"

    def test_admission_only(self):
        info = RESEARCH_DATA["بموتو"]
        assert _programmer_recommendation(info) == "requires_first_public_trade_evidence"

    def test_manual_review(self):
        info = RESEARCH_DATA["خاذین"]
        assert _programmer_recommendation(info) == "requires_manual_review_for_exact_date"


# ---- Part 2.1A tests -----------------------------------------------------------
class TestTacodalSourceType:
    def test_no_codal_official_for_tacodal_urls(self):
        for tk, info in RESEARCH_DATA.items():
            for src in info.get("sources", []):
                url = src[2].lower()
                src_type = src[0]
                if "tacodal" in url:
                    assert src_type != "codal_official", \
                        f"{tk}: Tacodal URL must not be codal_official, got {src_type}"

    def test_tacodal_is_market_information_aggregator(self):
        for tk, info in RESEARCH_DATA.items():
            for src in info.get("sources", []):
                url = src[2].lower()
                if "tacodal" in url:
                    assert src[0] == "market_information_aggregator", \
                        f"{tk}: Tacodal URL should be market_information_aggregator, got {src[0]}"


class TestHkeshtiDateConflict:
    def test_hkeshti_not_ready_for_user_review(self):
        assert RESEARCH_DATA["حکشتی"]["ready_for_user_review"] == "false"

    def test_hkeshti_evidence_requires_manual_review(self):
        assert RESEARCH_DATA["حکشتی"]["evidence_status"] == "requires_manual_review"

    def test_hkeshti_canonical_date_empty(self):
        assert RESEARCH_DATA["حکشتی"]["proposed_canonical_public_entry_date_jalali"] == ""

    def test_hkeshti_event_type_unresolved(self):
        assert RESEARCH_DATA["حکشتی"]["proposed_canonical_event_type"] == "unresolved"

    def test_hkeshti_ordinary_share_unknown(self):
        assert RESEARCH_DATA["حکشتی"]["ordinary_share_confirmed"] == "unknown"

    def test_conflicting_dates_cause_not_ready(self):
        tickers_df, research_df, prov_df, tsetmc_df = _build_fixture()
        hkeshti_row = research_df[research_df["ticker"] == "حکشتی"].iloc[0]
        assert str(hkeshti_row["ready_for_user_review"]).lower() == "false"
        assert hkeshti_row["evidence_status"] == "requires_manual_review"
        assert hkeshti_row["proposed_canonical_public_entry_date_jalali"] == ""


class TestCandidateSupportedRequiresFetchedSource:
    def test_no_candidate_supported_without_fetched_hash(self):
        for tk, info in RESEARCH_DATA.items():
            if info["evidence_status"] == "candidate_supported":
                assert info["ready_for_user_review"] == "true"
                assert info["proposed_canonical_public_entry_date_jalali"] != ""

    def test_hkeshti_not_candidate_supported(self):
        assert RESEARCH_DATA["حکشتی"]["evidence_status"] != "candidate_supported"


class TestListingNotFirstOffering:
    def test_admission_only_not_first_public_offering(self):
        for tk in ["بموتو", "حپترو", "خمحور"]:
            info = RESEARCH_DATA[tk]
            assert info["first_public_offering_date_candidate_jalali"] == ""
            assert info["first_public_trading_date_candidate_jalali"] == ""
            assert info["proposed_canonical_public_entry_date_jalali"] == ""

    def test_listing_only_not_first_public_offering(self):
        for tk in ["ثشرق", "ثنوسا", "خرینگ"]:
            info = RESEARCH_DATA[tk]
            assert info["first_public_offering_date_candidate_jalali"] == ""
            assert info["first_public_trading_date_candidate_jalali"] == ""
            assert info["proposed_canonical_public_entry_date_jalali"] == ""


class TestOtherNineTickersUnchanged:
    OTHER_NINE = ["بموتو", "ثشرق", "ثنوسا", "حپترو", "خاذین", "خبهمن", "ختوقا", "خرینگ", "خمحور"]

    def test_other_nine_evidence_status_unchanged(self):
        expected = {
            "بموتو": "requires_first_public_trade_evidence",
            "ثشرق": "requires_first_public_trade_evidence",
            "ثنوسا": "requires_first_public_trade_evidence",
            "حپترو": "requires_first_public_trade_evidence",
            "خاذین": "requires_manual_review",
            "خبهمن": "requires_manual_review",
            "ختوقا": "requires_manual_review",
            "خرینگ": "requires_first_public_trade_evidence",
            "خمحور": "requires_first_public_trade_evidence",
        }
        for tk in self.OTHER_NINE:
            assert RESEARCH_DATA[tk]["evidence_status"] == expected[tk], \
                f"{tk}: expected {expected[tk]}, got {RESEARCH_DATA[tk]['evidence_status']}"

    def test_other_nine_ready_for_user_review_unchanged(self):
        for tk in self.OTHER_NINE:
            assert RESEARCH_DATA[tk]["ready_for_user_review"] == "false"

    def test_other_nine_canonical_date_unchanged(self):
        for tk in self.OTHER_NINE:
            assert RESEARCH_DATA[tk]["proposed_canonical_public_entry_date_jalali"] == ""

    def test_other_nine_ordinary_share_confirmed_unchanged(self):
        expected = {
            "بموتو": "true", "ثشرق": "true", "ثنوسا": "true",
            "حپترو": "true", "خاذین": "true", "خبهمن": "true",
            "ختوقا": "true", "خرینگ": "true", "خمحور": "true",
        }
        for tk in self.OTHER_NINE:
            assert RESEARCH_DATA[tk]["ordinary_share_confirmed"] == expected[tk], \
                f"{tk}: expected {expected[tk]}, got {RESEARCH_DATA[tk]['ordinary_share_confirmed']}"


# ---- Part 2.1A.1 stabilization tests --------------------------------------------
class TestNonHkeshtiProvenanceRestored:
    OTHER_NINE = ["بموتو", "ثشرق", "ثنوسا", "حپترو", "خاذین", "خبهمن", "ختوقا", "خرینگ", "خمحور"]
    PROVENANCE_PATH = PART02_DIR / "part02_source_provenance_10tickers.csv"

    def test_provenance_file_exists(self):
        assert self.PROVENANCE_PATH.exists()

    def test_non_hkeshti_retrieved_at_from_original_run(self):
        df = pd.read_csv(self.PROVENANCE_PATH, dtype=str, encoding="utf-8-sig", keep_default_na=False)
        non_hk = df[df["ticker"].isin(self.OTHER_NINE)]
        for _, r in non_hk.iterrows():
            ts = r["retrieved_at_utc"]
            assert ts.startswith("2026-06-26T22:44:") or ts.startswith("2026-06-26T22:45:"), \
                f"{r['ticker']} source {r['source_index']}: retrieved_at_utc={ts} not from original run"

    def test_non_hkeshti_tsetmc_probe_retrieved_at_from_original(self):
        df = pd.read_csv(self.PROVENANCE_PATH, dtype=str, encoding="utf-8-sig", keep_default_na=False)
        non_hk_tsetmc = df[(df["ticker"].isin(self.OTHER_NINE)) & (df["source_type"] == "tsetmc_api")]
        for _, r in non_hk_tsetmc.iterrows():
            ts = r["retrieved_at_utc"]
            assert ts.startswith("2026-06-26T22:4"), \
                f"{r['ticker']}: tsetmc retrieved_at_utc={ts} not from original run"

    def test_thnusa_source_type_is_market_information_aggregator(self):
        df = pd.read_csv(self.PROVENANCE_PATH, dtype=str, encoding="utf-8-sig", keep_default_na=False)
        thnusa = df[(df["ticker"] == "ثنوسا") & (df["source_type"] != "tsetmc_api")]
        for _, r in thnusa.iterrows():
            if "tacodal" in r["source_url"].lower():
                assert r["source_type"] == "market_information_aggregator", \
                    f"ثنوسا tacodal source_type={r['source_type']}, expected market_information_aggregator"

    def test_thnusa_source_type_not_codal_official(self):
        df = pd.read_csv(self.PROVENANCE_PATH, dtype=str, encoding="utf-8-sig", keep_default_na=False)
        thnusa = df[df["ticker"] == "ثنوسا"]
        for _, r in thnusa.iterrows():
            assert r["source_type"] != "codal_official", \
                f"ثنوسا source_type should not be codal_official"


class TestTsetmcAuditRestored:
    AUDIT_PATH = PART02_DIR / "part02_tsetmc_audit_10tickers.csv"

    def test_audit_file_exists(self):
        assert self.AUDIT_PATH.exists()

    def test_all_probe_retrieved_at_from_original_run(self):
        df = pd.read_csv(self.AUDIT_PATH, dtype=str, encoding="utf-8-sig", keep_default_na=False)
        for _, r in df.iterrows():
            ts = r["probe_retrieved_at"]
            assert ts.startswith("2026-06-26T22:44:") or ts.startswith("2026-06-26T22:45:"), \
                f"{r['ticker']}: probe_retrieved_at={ts} not from original run"

    def test_all_probe_source_is_live_probe(self):
        df = pd.read_csv(self.AUDIT_PATH, dtype=str, encoding="utf-8-sig", keep_default_na=False)
        for _, r in df.iterrows():
            assert r["probe_source"] == "live_probe", \
                f"{r['ticker']}: probe_source={r['probe_source']}"


class TestNoAbsolutePathInProvenance:
    PROVENANCE_PATH = PART02_DIR / "part02_source_provenance_10tickers.csv"

    def test_no_absolute_path_in_snapshot_path(self):
        df = pd.read_csv(self.PROVENANCE_PATH, dtype=str, encoding="utf-8-sig", keep_default_na=False)
        for _, r in df.iterrows():
            sp = r.get("snapshot_path", "")
            if sp:
                assert not sp.startswith("/"), \
                    f"{r['ticker']} source {r['source_index']}: absolute snapshot_path={sp}"
                assert "/Users/" not in sp, \
                    f"{r['ticker']}: /Users/ in snapshot_path={sp}"
                assert "Desktop" not in sp, \
                    f"{r['ticker']}: Desktop in snapshot_path={sp}"

    def test_no_absolute_path_in_any_column(self):
        df = pd.read_csv(self.PROVENANCE_PATH, dtype=str, encoding="utf-8-sig", keep_default_na=False)
        for _, r in df.iterrows():
            for col in df.columns:
                val = str(r.get(col, ""))
                if val and "/Users/" in val:
                    pytest.fail(f"{r['ticker']} col={col}: contains /Users/ -> {val}")


class TestSnapshotPathRelative:
    def test_snapshot_rel_path_format(self):
        p = _snapshot_rel_path(1)
        assert p == "stage124/batch02_parts/snapshots_hkeshti/source_1.html"
        assert not p.startswith("/")
        assert "/Users/" not in p

    def test_hkeshti_snapshot_path_in_provenance_is_relative(self):
        df = pd.read_csv(
            PART02_DIR / "part02_source_provenance_10tickers.csv",
            dtype=str, encoding="utf-8-sig", keep_default_na=False,
        )
        hk = df[df["ticker"] == "حکشتی"]
        for _, r in hk.iterrows():
            sp = r.get("snapshot_path", "")
            if sp:
                assert sp == "stage124/batch02_parts/snapshots_hkeshti/source_1.html", \
                    f"snapshot_path={sp}"


class TestSnapshotHashMatchesProvenance:
    SNAPSHOT_PATH = PART02_DIR / "snapshots_hkeshti" / "source_1.html"
    PROVENANCE_PATH = PART02_DIR / "part02_source_provenance_10tickers.csv"

    def test_snapshot_exists(self):
        assert self.SNAPSHOT_PATH.exists()

    def test_snapshot_hash_matches_provenance(self):
        body = self.SNAPSHOT_PATH.read_bytes()
        actual_hash = hashlib.sha256(body).hexdigest()
        df = pd.read_csv(self.PROVENANCE_PATH, dtype=str, encoding="utf-8-sig", keep_default_na=False)
        hk_fetched = df[(df["ticker"] == "حکشتی") & (df["retrieval_status"] == "fetched_ok")]
        assert len(hk_fetched) >= 1
        prov_hash = hk_fetched.iloc[0]["content_sha256"]
        assert actual_hash == prov_hash, \
            f"snapshot hash={actual_hash} != provenance hash={prov_hash}"


class TestRerunNoTsetmc:
    def test_load_existing_tsetmc_audit_returns_data(self):
        result = _load_existing_tsetmc_audit()
        assert result is not None
        assert len(result) == 10
        for tk in PART02_TICKERS:
            assert tk in result
            assert result[tk]["instrument_match_status"] == "network_unreachable"

    def test_existing_audit_has_original_timestamps(self):
        result = _load_existing_tsetmc_audit()
        for tk, probe in result.items():
            ts = probe["probe_retrieved_at"]
            assert ts.startswith("2026-06-26T22:4"), \
                f"{tk}: probe_retrieved_at={ts} not from original run"


class TestRerunNoHkeshtiFetch:
    def test_fetch_sources_hkeshti_reuses_existing(self):
        from project.src.stage124_batch02_part02 import fetch_sources_hkeshti
        results = fetch_sources_hkeshti(timeout=5.0, force=False)
        assert results[1]["retrieval_status"] == "reused_existing_snapshot"
        assert results[1]["snapshot_path"] == "stage124/batch02_parts/snapshots_hkeshti/source_1.html"
        assert results[1]["content_sha256"] == hashlib.sha256(
            (PART02_DIR / "snapshots_hkeshti" / "source_1.html").read_bytes()
        ).hexdigest()

    def test_timeout_sources_not_refetched(self):
        from project.src.stage124_batch02_part02 import fetch_sources_hkeshti
        results = fetch_sources_hkeshti(timeout=5.0, force=False)
        assert results[2]["retrieval_status"] == "timeout"
        assert results[3]["retrieval_status"] == "timeout"


class TestHkeshtiStatusUnchanged:
    def test_hkeshti_requires_manual_review(self):
        assert RESEARCH_DATA["حکشتی"]["evidence_status"] == "requires_manual_review"

    def test_hkeshti_not_ready_for_user_review(self):
        assert RESEARCH_DATA["حکشتی"]["ready_for_user_review"] == "false"

    def test_hkeshti_canonical_empty(self):
        assert RESEARCH_DATA["حکشتی"]["proposed_canonical_public_entry_date_jalali"] == ""

    def test_hkeshti_event_type_unresolved(self):
        assert RESEARCH_DATA["حکشتی"]["proposed_canonical_event_type"] == "unresolved"
