"""Tests — Stage128 M3I-2 official-source evidence capture.

Offline and deterministic. **No test issues a live network request**: every
host check runs against the pure predicate, and every capture-shaped fixture is
synthetic and local.

The forbidden-token scanners are exercised with tokens assembled at runtime
from fragments, so this file never itself contains a literal forbidden token.
"""
from __future__ import annotations

import copy
import json
import zipfile
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import stage128_m3i2_official_source_evidence_capture as m  # noqa: E402
from src import stage128_m3i2_capture_layer as cap  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ERROR = m.M3I2EvidenceCaptureError

BASELINE = "cf23771a383bf9ad8f7ff2855c216c9a240647ff"
MERGE_COMMIT = "cf23771a383bf9ad8f7ff2855c216c9a240647ff"


@pytest.fixture(scope="module")
def built():
    return m.build_package(ROOT, write=False)


# --------------------------------------------------------------------------- #
# Section 0 — the human authorization
# --------------------------------------------------------------------------- #

def test_human_authorization_is_byte_exact():
    checks = m.verify_human_authorization()
    assert checks["authorization_utf8_bytes"] == 695
    assert checks["authorization_sha256"] == (
        "eb0230b06269feee5f274315d2958f762c69fc231f36c73b0048415e5fd95b06")


def test_authorization_names_the_action_and_the_baseline():
    assert m.ACTION_ID in m.HUMAN_AUTHORIZATION_TEXT
    assert BASELINE in m.HUMAN_AUTHORIZATION_TEXT
    assert not m.HUMAN_AUTHORIZATION_TEXT.endswith("\n")


def test_authorization_is_one_action_not_standing(built):
    rec = built["authorization_record"]
    assert rec["authorization_type"] == "one_action_authorization"
    assert rec["authorization_consumed"] is True
    assert rec["standing_authorization"] is False
    assert rec["a_pointer_is_not_an_authorization"] is True
    for field in ("authorization_inferred_from_pointer",
                  "authorization_inferred_from_prior_prompt_hash",
                  "authorization_inferred_from_branch_name"):
        assert rec[field] is False


def test_authorization_forbids_every_downstream_action(built):
    rec = built["authorization_record"]
    for field in ("data_gate_authorized", "company_join_authorized",
                  "feature_materialization_authorized",
                  "coverage_calculation_authorized", "modeling_authorized",
                  "m4_authorized", "final_test_access_authorized",
                  "merge_authorized"):
        assert rec[field] is False


@pytest.mark.parametrize("mutation", ["", "x", m.HUMAN_AUTHORIZATION_TEXT + "!"])
def test_a_tampered_authorization_fails_closed(monkeypatch, mutation):
    monkeypatch.setattr(m, "HUMAN_AUTHORIZATION_TEXT", mutation)
    with pytest.raises(ERROR):
        m.verify_human_authorization()


# --------------------------------------------------------------------------- #
# Section 3 — the merged contract is read-only
# --------------------------------------------------------------------------- #

def test_exact_baseline_contract_values_are_read(built):
    contract = built["contract_read"]
    cpi = contract["cpi_candidate"]
    fx = contract["fx_candidate"]
    assert cpi["candidate_id"] == "cand_m3i_cpi_inflation_annual"
    assert cpi["indicator_code"] == "FP.CPI.TOTL.ZG"
    assert cpi["transformation_formula"] == "identity"
    assert fx["candidate_id"] == "cand_m3i_fx_change_official_annual"
    assert fx["indicator_code"] == "PA.NUS.FCRF"
    assert fx["transformation_formula"] == "100 * ln(E_y / E_(y-1))"
    assert contract["contract_modified_by_this_action"] is False


def test_financing_shell_null_fields_are_not_populated(built):
    financing = built["contract_read"]["financing_candidate"]
    assert financing["candidate_selection_status"] == "UNRESOLVED_METADATA_LOCK"
    assert financing["admitted"] is False
    assert financing["exact_series_code"] is None
    assert built["financing_evidence"]["contract_null_fields_populated"] is False
    assert built["financing_evidence"]["m3i3_admitted"] is False


def test_prior_contract_package_is_byte_identical(built):
    immutability = built["decision"]["protected_immutability"]
    assert immutability["merged_contract_package_byte_identical"] is True
    assert immutability["protected_committed_history_diff_empty"] is True
    assert immutability["protected_baseline_commit"] == BASELINE
    assert immutability["no_scientific_predecessor_artifact_changed"] is True


def test_protected_trees_cover_the_required_scope():
    for tree in ("project/stage125", "project/stage126", "project/stage127",
                 "project/stage128/m3_macro_data_gate",
                 "project/stage128/m3_intl_macro_contract_lock"):
        assert tree in m.PROTECTED_TREES
    assert ("project/stage128/stage128_m2_d2_development_features.csv"
            in m.PROTECTED_EXTRA_FILES)


def test_the_operational_exclusion_list_is_closed():
    assert len(m.PROTECTED_OPERATIONAL_EXCLUSIONS) == 3
    assert all(p.startswith("project/stage126/")
               for p in m.PROTECTED_OPERATIONAL_EXCLUSIONS)


# --------------------------------------------------------------------------- #
# Section 5 — the development-cutoff input firewall
# --------------------------------------------------------------------------- #

def test_cutoff_source_is_uniquely_bound(built):
    audit = built["cutoff_source_audit"]
    assert audit["cutoff_source_repository_path"] == (
        "project/stage128/stage128_m2_d2_development_features.csv")
    assert audit["uniquely_bound"] is True
    assert audit["cutoff_field"] == "pair_cutoff_date"
    assert len(audit["cutoff_source_sha256"]) == 64
    assert len(audit["cutoff_source_git_blob_sha"]) == 40
    assert audit["cutoff_source_row_count"] == 666
    assert audit["final_test_directories_searched"] is False


def test_only_allowlisted_columns_are_read(built):
    audit = built["cutoff_source_audit"]
    assert audit["outcome_or_target_columns_read"] is False
    assert audit["financial_or_market_feature_columns_read"] is False
    for denied in m.CUTOFF_COLUMN_DENYLIST:
        assert denied not in audit["columns_read"]
    for allowed in m.CUTOFF_COLUMN_ALLOWLIST:
        assert allowed in audit["columns_read"]


def test_cutoff_plan_is_development_only(built):
    plan = built["cutoff_plan"]
    assert len(plan) == built["evidence_summary"]["unique_development_cutoffs"]
    total = sum(r["number_of_development_pairs_sharing_cutoff"] for r in plan)
    assert total == m.EXPECTED_DEVELOPMENT_PAIRS == 539
    for row in plan:
        assert row["pair_prediction_cutoff_utc"].endswith("T00:00:00Z")
        for year in m.FINAL_TEST_TARGET_YEARS:
            assert year not in row["cutoff_id"]


def test_a_final_test_row_reaching_the_reader_fails_closed():
    with pytest.raises(ERROR) as exc:
        m.assert_no_final_test_access([{"target_year": "1401"}])
    assert "STOP_FINAL_TEST_ROW_REACHED_EVIDENCE_CAPTURE" in str(exc.value)


def test_final_test_years_are_never_development_years():
    assert not set(m.DEVELOPMENT_TARGET_YEARS) & set(m.FINAL_TEST_TARGET_YEARS)
    assert m.FINAL_TEST_TARGET_YEARS == ("1400", "1401", "1402")


def test_the_date_only_cutoff_limitation_is_declared(built):
    audit = built["cutoff_source_audit"]
    assert audit["cutoff_field_is_date_only"] is True
    assert audit["cutoff_intraday_time_verified"] is False
    assert audit["cutoff_time_assumption_is_conservative"] is True


def test_missing_cutoff_source_fails_closed(tmp_path):
    with pytest.raises(ERROR) as exc:
        m.bind_development_cutoff_source(tmp_path)
    assert "STOP_DEVELOPMENT_CUTOFF_SOURCE_NOT_UNIQUELY_BOUND" in str(exc.value)


# --------------------------------------------------------------------------- #
# Section 6 — the official-host allowlist (pure predicate, no live request)
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("url", [
    "https://datatopics.worldbank.org/world-development-indicators/x.html",
    "https://databank.worldbank.org/data/download/Archive/WDI_excel_2020_07_01.zip",
    "https://databankfiles.worldbank.org/public/x.zip",
    "https://api.worldbank.org/v2/country/IRN",
])
def test_official_world_bank_hosts_are_accepted(url):
    assert cap.is_official_host(url) is True
    cap.assert_official_url(url)


@pytest.mark.parametrize("url", [
    "https://data.imf.org/en/datasets/IMF.STA%3AMFS_IR",
    "https://www.imf.org/en/Data",
])
def test_official_imf_hosts_are_accepted(url):
    assert cap.is_official_host(url) is True
    cap.assert_official_url(url)


@pytest.mark.parametrize("host", [
    "db" + "nomics.world", "fred." + "stlouisfed.org",
    "alfred." + "stlouisfed.org", "www." + "kag" + "gle.com",
    "raw." + "githubusercontent.com", "www." + "trading" + "economics.com",
    "worldbank.org.evil.example", "notworldbank.org",
])
def test_unofficial_hosts_and_mirrors_are_rejected(host):
    url = f"https://{host}/x"
    assert cap.is_official_host(url) is False
    with pytest.raises(cap.CaptureError):
        cap.assert_official_url(url)


def test_plain_http_is_refused():
    with pytest.raises(cap.CaptureError):
        cap.assert_official_url("http://databank.worldbank.org/x.zip")


def test_a_redirect_off_an_official_host_is_a_hard_stop():
    handler = cap._RecordingRedirectHandler()

    class _Req:
        full_url = "https://databank.worldbank.org/a"

    with pytest.raises(cap.CaptureError) as exc:
        handler.redirect_request(
            _Req(), None, 302, "Found", {}, "https://evil.example/b")
    assert "NON_OFFICIAL_HOST" in str(exc.value)


def test_discovery_roots_are_all_official():
    for target in m.DISCOVERY_TARGETS:
        assert cap.is_official_host(target["url"])
        assert target["url"].startswith("https://")


# --------------------------------------------------------------------------- #
# Section 8 — release availability and edition selection
# --------------------------------------------------------------------------- #

def test_date_only_release_gets_next_day_midnight_utc():
    available_at, applied = m.derive_release_available_at("2019-06-28", None)
    assert available_at == "2019-06-29T00:00:00Z"
    assert applied is True


def test_an_exact_release_time_is_used_as_is():
    available_at, applied = m.derive_release_available_at(
        "2019-06-28", "14:30:00")
    assert available_at == "2019-06-28T14:30:00Z"
    assert applied is False


def test_an_edition_without_a_release_date_cannot_get_an_available_at():
    with pytest.raises(ERROR):
        m.derive_release_available_at("", None)


def _editions(*specs):
    out = []
    for edition_id, available_at, verified in specs:
        out.append({
            "archive_edition_id": edition_id,
            "derived_release_available_at_utc": available_at,
            "release_date_verified": verified,
        })
    return out


def test_strictly_earlier_edition_is_selected():
    editions = _editions(
        ("A", "2019-01-02T00:00:00Z", True),
        ("B", "2019-06-29T00:00:00Z", True),
        ("C", "2020-01-02T00:00:00Z", True))
    chosen = m.select_edition_for_cutoff("2019-07-20T00:00:00Z", editions)
    assert chosen["archive_edition_id"] == "B"


def test_a_same_instant_release_is_excluded():
    """``<`` is strict: a release AT the cutoff is not available before it."""
    editions = _editions(("A", "2019-07-20T00:00:00Z", True))
    assert m.select_edition_for_cutoff("2019-07-20T00:00:00Z", editions) is None


def test_a_same_day_date_only_release_is_excluded():
    """A release dated the cutoff day becomes next-day midnight, so it fails."""
    available_at, _ = m.derive_release_available_at("2019-07-20", None)
    editions = _editions(("A", available_at, True))
    assert m.select_edition_for_cutoff("2019-07-20T00:00:00Z", editions) is None


def test_an_unverified_release_date_is_never_selected():
    editions = _editions(("A", "2015-01-02T00:00:00Z", False))
    assert m.select_edition_for_cutoff("2019-07-20T00:00:00Z", editions) is None


def test_a_current_edition_is_never_treated_as_historical():
    """The newest edition must not serve a cutoff that precedes it."""
    editions = _editions(("NEWEST", "2026-02-26T00:00:00Z", True))
    assert m.select_edition_for_cutoff("2015-01-20T00:00:00Z", editions) is None


def test_the_latest_edition_is_not_reused_for_every_cutoff():
    editions = _editions(
        ("OLD", "2018-01-02T00:00:00Z", True),
        ("NEW", "2020-01-02T00:00:00Z", True))
    plan = [
        {"cutoff_id": "c1", "pair_prediction_cutoff_utc": "2019-01-20T00:00:00Z",
         "number_of_development_pairs_sharing_cutoff": 5},
        {"cutoff_id": "c2", "pair_prediction_cutoff_utc": "2021-01-20T00:00:00Z",
         "number_of_development_pairs_sharing_cutoff": 7},
    ]
    resolved, required = m.plan_required_editions(plan, editions)
    assert resolved[0]["selected_wdi_archive_edition_id"] == "OLD"
    assert resolved[1]["selected_wdi_archive_edition_id"] == "NEW"
    assert len(required) == 2


def test_required_editions_are_deduplicated():
    editions = _editions(("ONE", "2018-01-02T00:00:00Z", True))
    plan = [
        {"cutoff_id": "a", "pair_prediction_cutoff_utc": "2019-01-20T00:00:00Z",
         "number_of_development_pairs_sharing_cutoff": 3},
        {"cutoff_id": "b", "pair_prediction_cutoff_utc": "2019-05-20T00:00:00Z",
         "number_of_development_pairs_sharing_cutoff": 4},
    ]
    _, required = m.plan_required_editions(plan, editions)
    assert len(required) == 1
    assert required[0]["development_pair_count_using_edition"] == 7


def test_a_cutoff_without_a_verified_pre_cutoff_edition_is_unresolved():
    editions = _editions(("LATER", "2024-01-02T00:00:00Z", True))
    plan = [{"cutoff_id": "a",
             "pair_prediction_cutoff_utc": "2015-01-20T00:00:00Z",
             "number_of_development_pairs_sharing_cutoff": 9}]
    resolved, required = m.plan_required_editions(plan, editions)
    assert resolved[0]["selection_reason"] == "NO_VERIFIED_PRE_CUTOFF_EDITION"
    assert resolved[0]["selected_wdi_archive_edition_id"] == ""
    assert required == []


def test_edition_selection_must_be_value_blind():
    with pytest.raises(ERROR):
        m.assert_edition_selection_is_value_blind(
            [], {"edition_selection_used_observed_values": True,
                 "edition_switched_after_missing_value_inspection": False})
    with pytest.raises(ERROR):
        m.assert_edition_selection_is_value_blind(
            [], {"edition_selection_used_observed_values": False,
                 "edition_switched_after_missing_value_inspection": True})


# --------------------------------------------------------------------------- #
# The official listing parser (fixtures only — no live request)
# --------------------------------------------------------------------------- #

LISTING_FIXTURE = """
<a href="https://databank.worldbank.org/data/download/Archive/WDI_excel_2019_06_28.zip">June</a>
<a href="http://databank.worldbank.org/data/download/archive/WDI_excel_2015_04.zip">April</a>
<a href="http://databank.worldbank.org/data/download/archive/WDI_2009_05.zip">May</a>
"""

#: Retained bytes that DO explicitly call a date a release date.
STATED_RELEASE_TEXTS = {
    "wb_wdi_archive_listing":
        "The 2019-06-28 edition was released on that date.",
}


def _editions_from_fixture(retained=None):
    return m.parse_wdi_archive_listing(
        LISTING_FIXTURE, "https://datatopics.worldbank.org/x", "a" * 64, "t",
        retained_texts=retained)


def test_a_filename_date_is_only_a_token_not_a_release_date():
    """The core of blocker 1: a token in a filename proves nothing by itself."""
    edition = next(e for e in _editions_from_fixture()
                   if e["archive_edition_id"] == "WDI_2019_06_28")
    assert edition["edition_date_token"] == "2019-06-28"
    assert edition["edition_date_token_source"] == (
        "official_listing_download_filename")
    assert edition["edition_date_token_exact"] is True
    assert edition["release_date_explicitly_stated_by_official_source"] is False
    assert edition["release_date_verified"] is False
    assert edition["derived_release_available_at_utc"] is None
    assert edition["release_available_at_derivation_status"] == (
        "UNRESOLVED_FILENAME_DATE_TOKEN_NOT_VERIFIED_AS_RELEASE_DATE")
    assert edition["release_date_evidence_artifact"] == ""
    assert edition["release_date_evidence_locator"] == ""


def test_an_explicit_official_statement_does_verify_the_release_date():
    edition = next(e for e in _editions_from_fixture(STATED_RELEASE_TEXTS)
                   if e["archive_edition_id"] == "WDI_2019_06_28")
    assert edition["release_date_explicitly_stated_by_official_source"] is True
    assert edition["release_date_verified"] is True
    assert edition["derived_release_available_at_utc"] == (
        "2019-06-29T00:00:00Z")
    assert edition["release_date_evidence_artifact"] == (
        "wb_wdi_archive_listing")
    assert edition["release_date_evidence_locator"]
    assert "token=2019-06-28" in edition["release_date_evidence_locator"]


def test_a_month_only_token_can_never_be_verified():
    for retained in (None, STATED_RELEASE_TEXTS):
        editions = _editions_from_fixture(retained)
        for edition_id in ("WDI_2015_04", "WDI_2009_05"):
            edition = next(e for e in editions
                           if e["archive_edition_id"] == edition_id)
            assert edition["edition_date_token_exact"] is False
            assert edition["release_date_verified"] is False
            assert edition["derived_release_available_at_utc"] is None


def test_an_unverified_token_never_yields_an_available_at():
    for edition in _editions_from_fixture():
        assert edition["release_date_verified"] is False
        assert edition["derived_release_available_at_utc"] is None
        assert m.select_edition_for_cutoff(
            "2026-01-01T00:00:00Z", [edition]) is None


def test_release_time_may_never_come_from_a_timestamp_or_header():
    for edition in _editions_from_fixture():
        joined = edition["non_evidence_for_release_time"]
        for banned in ("retrieval timestamp", "HTTP Last-Modified header",
                       "ZIP member timestamp",
                       "workbook document properties"):
            assert banned in joined


def test_the_provenance_fields_reach_the_committed_csv(built):
    """An evidence field that never lands in the artifact is not evidence."""
    text = built["artifact_texts"][m.RELEASE_MANIFEST_REL]
    header = text.splitlines()[0].split(",")
    for field in ("edition_date_token", "edition_date_token_source",
                  "edition_date_token_exact",
                  "release_date_explicitly_stated_by_official_source",
                  "release_date_evidence_artifact",
                  "release_date_evidence_locator", "release_date_verified",
                  "release_available_at_derivation_status",
                  "release_date_source"):
        assert field in header, field


def test_the_real_capture_verifies_no_release_date_at_all(built):
    """Recomputed from retained bytes — not preserved by expectation."""
    summary = built["evidence_summary"]
    assert summary["editions_with_verified_release_date"] == 0
    assert summary["wdi_editions_discovered"] > 0
    assert summary["editions_with_unverified_filename_date_token"] == (
        summary["wdi_editions_discovered"])
    for edition in built["release_manifest"]:
        assert edition["release_date_verified"] is False
        assert not edition["derived_release_available_at_utc"]


def test_every_cutoff_is_unresolved_and_nothing_is_hard_coded(built):
    summary = built["evidence_summary"]
    plan = built["cutoff_plan"]
    assert summary["required_editions_total"] == 0
    assert summary["cutoffs_without_verified_pre_cutoff_edition"] == len(plan)
    assert summary["cutoffs_with_verified_pre_cutoff_edition"] == 0
    assert summary["development_pairs_without_verified_pre_cutoff_edition"] == (
        m.EXPECTED_DEVELOPMENT_PAIRS)
    for row in plan:
        assert row["selection_reason"] == "NO_VERIFIED_PRE_CUTOFF_EDITION"
        assert row["selected_wdi_archive_edition_id"] == ""


def test_resolved_cutoff_counts_are_recomputed_not_constants():
    """A hard-coded '18 resolved' would survive this; a recomputation cannot."""
    source = (ROOT / "project/src"
              / "stage128_m3i2_official_source_evidence_capture.py").read_text(
                  encoding="utf-8")
    for frozen in ("cutoffs_with_verified_pre_cutoff_edition = 18",
                   "resolved_cutoffs = 18", "= 18\n"):
        assert frozen not in source


def test_archives_are_still_held_even_though_undatable(built):
    """Being unable to date an edition is not the same as not having it."""
    summary = built["evidence_summary"]
    assert summary["archive_editions_captured"] == 16
    assert summary["locked_series_rows_extracted"] > 0
    for entry in built["captured_editions"]:
        assert entry["download_status"] == "SUCCESS"
        assert entry["usable_as_pre_cutoff_vintage"] is False
        assert entry["raw_artifact_sha256"]


# --------------------------------------------------------------------------- #
# Section 11-12 — locked series and semantic compatibility
# --------------------------------------------------------------------------- #

def test_only_the_two_locked_indicator_codes_are_allowed():
    m.assert_locked_indicators_only(["FP.CPI.TOTL.ZG", "PA.NUS.FCRF"])


@pytest.mark.parametrize("code", [
    "PA.NUS.ATLS", "FP.CPI.TOTL", "NY.GDP.DEFL.KD.ZG", "FR.INR.LEND",
])
def test_indicator_substitution_fails_closed(code):
    with pytest.raises(ERROR):
        m.assert_locked_indicators_only(["FP.CPI.TOTL.ZG", code])


def test_an_unknown_indicator_fails_closed():
    with pytest.raises(ERROR):
        m.assert_locked_indicators_only(["SP.POP.TOTL"])


def _complete_evidence(**overrides):
    evidence = {
        "economy_identity_verified": True,
        "indicator_code_verified": True,
        "frequency_annual_verified": True,
        "calendar_year_semantics_verified": True,
        "title_compatibility": "COMPATIBLE",
        "unit_compatibility": "COMPATIBLE",
        "raw_archive_sha256": "b" * 64,
    }
    evidence.update(overrides)
    return evidence


def test_complete_evidence_classifies_as_pass():
    assert m.classify_semantic_compatibility(_complete_evidence()) == "PASS"


@pytest.mark.parametrize("missing", [
    {"economy_identity_verified": False},
    {"indicator_code_verified": False},
    {"frequency_annual_verified": False},
    {"calendar_year_semantics_verified": False},
    {"title_compatibility": ""},
    {"unit_compatibility": ""},
    {"raw_archive_sha256": ""},
])
def test_missing_proof_is_unresolved_never_fail(missing):
    """Absence of metadata is UNRESOLVED. It is never FAIL."""
    status = m.classify_semantic_compatibility(_complete_evidence(**missing))
    assert status == "UNRESOLVED"
    assert status != "FAIL"


def test_a_contradiction_is_fail_integrity():
    assert m.classify_semantic_compatibility(
        _complete_evidence(integrity_contradiction=True)) == "FAIL_INTEGRITY"


def test_every_semantic_status_is_in_the_allowed_vocabulary():
    assert m.SEMANTIC_STATUSES == ("PASS", "UNRESOLVED", "FAIL_INTEGRITY")
    assert "FAIL" not in m.SEMANTIC_STATUSES


def test_a_semantic_pass_without_full_evidence_fails_qc():
    row = {f: "x" for f in m.SEMANTIC_EVIDENCE_FIELDS}
    row["compatibility_status"] = "PASS"
    m.assert_semantic_pass_is_fully_evidenced(row)
    row["raw_archive_sha256"] = ""
    with pytest.raises(ERROR):
        m.assert_semantic_pass_is_fully_evidenced(row)


def test_an_unresolved_row_is_not_required_to_be_fully_evidenced():
    m.assert_semantic_pass_is_fully_evidenced(
        {"compatibility_status": "UNRESOLVED"})


def test_cpi_and_fx_required_interpretations_are_declared():
    assert "inflation-rate" in m.CPI_REQUIRED_INTERPRETATION
    assert "percent" in m.CPI_REQUIRED_INTERPRETATION
    assert "CPI index level" in m.CPI_FORBIDDEN_INTERPRETATIONS
    assert "GDP-deflator inflation" in m.CPI_FORBIDDEN_INTERPRETATIONS
    assert "period average" in m.FX_REQUIRED_INTERPRETATION
    assert "LCU per US dollar" in m.FX_REQUIRED_INTERPRETATION


# --------------------------------------------------------------------------- #
# Blocker 2 — FX continuity evidence
# --------------------------------------------------------------------------- #

def _fx_row(**overrides):
    row = {
        "indicator_code": m.FX_INDICATOR_CODE,
        "compatibility_status": "PASS",
        "fx_pair_semantic_compatibility_status": "PASS",
        "currency_denomination_verified": True,
        "valuation_definition_verified": True,
        "no_redenomination_or_unit_break_verified": True,
        "currency_denomination_evidence_locator": "loc-a",
        "valuation_definition_evidence_locator": "loc-b",
        "redenomination_or_unit_break_evidence_locator": "loc-c",
    }
    row.update(overrides)
    return row


def test_a_fully_evidenced_fx_row_may_pass():
    m.assert_fx_pass_has_continuity_evidence(_fx_row())


@pytest.mark.parametrize("gap", [
    {"currency_denomination_verified": False},
    {"valuation_definition_verified": False},
    {"no_redenomination_or_unit_break_verified": False},
    {"currency_denomination_verified": ""},
    {"valuation_definition_verified": None},
])
def test_fx_pass_without_continuity_evidence_fails_closed(gap):
    with pytest.raises(ERROR):
        m.assert_fx_pass_has_continuity_evidence(_fx_row(**gap))


@pytest.mark.parametrize("locator", [
    "currency_denomination_evidence_locator",
    "valuation_definition_evidence_locator",
    "redenomination_or_unit_break_evidence_locator",
])
def test_fx_pass_without_an_evidence_locator_fails_closed(locator):
    with pytest.raises(ERROR):
        m.assert_fx_pass_has_continuity_evidence(_fx_row(**{locator: ""}))


def test_the_archived_title_alone_is_not_complete_fx_evidence():
    """A generic 'LCU per US$, period average' settles construct and unit
    label only — never denomination, valuation or absence of a unit break."""
    meta = {
        "series_title": "Official exchange rate (LCU per US$, period average)",
        "periodicity": "Annual",
        "unit": "",
        "statistical_concept": (
            "The exchange rate is the price of one currency in terms of "
            "another. Official exchange rates and exchange rate arrangements "
            "are established by governments."),
    }
    rows = [{"indicator_code_raw": m.FX_INDICATOR_CODE,
             "observation_year": "2015"}]
    row = m._semantic_row("WDI_X", "", "b" * 64, m.FX_INDICATOR_CODE, meta,
                          True, rows)
    assert row["compatibility_status"] == "UNRESOLVED"
    assert row["fx_pair_semantic_compatibility_status"] == "UNRESOLVED"
    assert row["currency_denomination_verified"] is False
    assert row["valuation_definition_verified"] is False
    assert row["no_redenomination_or_unit_break_verified"] is False
    assert "generic construct and unit label only" in row["unresolved_reason"]


def test_a_stated_redenomination_is_fail_integrity_not_unresolved():
    meta = {
        "series_title": "Official exchange rate (LCU per US$, period average)",
        "periodicity": "Annual", "unit": "LCU per US$",
        "statistical_concept": "A redenomination occurred during this period.",
    }
    rows = [{"indicator_code_raw": m.FX_INDICATOR_CODE,
             "observation_year": "2015"}]
    row = m._semantic_row("WDI_X", "", "b" * 64, m.FX_INDICATOR_CODE, meta,
                          True, rows)
    assert row["compatibility_status"] == "FAIL_INTEGRITY"


def test_silence_about_a_break_is_never_proof_of_absence():
    meta = {"series_title": "Official exchange rate (LCU per US$, period "
                            "average)", "periodicity": "Annual", "unit": ""}
    rows = [{"indicator_code_raw": m.FX_INDICATOR_CODE,
             "observation_year": "2015"}]
    row = m._semantic_row("WDI_X", "", "b" * 64, m.FX_INDICATOR_CODE, meta,
                          True, rows)
    assert row["no_redenomination_or_unit_break_verified"] is False


def test_every_real_fx_row_is_unresolved_and_recomputed(built):
    fx = [r for r in built["semantic_compatibility"]
          if r["indicator_code"] == m.FX_INDICATOR_CODE]
    assert fx, "FX rows must exist"
    assert built["evidence_summary"]["fx_semantic_pass_count"] == 0
    assert built["evidence_summary"]["fx_semantic_unresolved_count"] == len(fx)
    for row in fx:
        assert row["compatibility_status"] == "UNRESOLVED"
        assert row["currency_denomination_verified"] is False
        assert row["no_redenomination_or_unit_break_verified"] is False


def test_cpi_rows_stay_pass_with_their_unit_provenance_disclosed(built):
    cpi = [r for r in built["semantic_compatibility"]
           if r["indicator_code"] == m.CPI_INDICATOR_CODE]
    assert cpi
    for row in cpi:
        assert row["compatibility_status"] == "PASS"
        assert row["unit_evidence_source"]
        assert row["calendar_year_evidence_locator"]
    text = built["artifact_texts"][m.SEMANTIC_REL]
    assert "unit_evidence_source" in text.splitlines()[0]


def test_semantic_counts_are_not_hard_coded():
    source = (ROOT / "project/src"
              / "stage128_m3i2_official_source_evidence_capture.py").read_text(
                  encoding="utf-8")
    assert "semantic_pass_count = 32" not in source
    assert "= 32\n" not in source


# --------------------------------------------------------------------------- #
# Section 5 — the two capture invocations
# --------------------------------------------------------------------------- #

def test_both_invocations_are_disclosed_in_the_committed_package(built):
    record = built["continuation_record"]
    assert record["capture_invocations"] == 2
    assert record["invocation_1_role"] == "discovery_only"
    assert record["invocation_1_request_count"] == 5
    assert record["invocation_1_closed"] is True
    assert record["invocation_2_role"] == "required_archive_completion"
    assert record["invocation_2_request_count"] == 16
    assert record["invocation_2_closed"] is True
    assert m.CONTINUATION_REL in built["artifact_texts"]


def test_the_continuation_decision_is_recorded_verbatim(built):
    record = built["continuation_record"]
    assert record["continuation_was_explicitly_requested_from_human"] is True
    assert record["continuation_selected_option_text"] == (
        "capture را کامل کن (پیشنهادی)")
    assert record["continuation_question_context"]
    assert record["continuation_scope_changed"] is False
    assert record["continuation_authorized_new_scientific_action"] is False
    assert record[
        "continuation_authorized_only_completion_of_same_capture"] is True


def test_no_timestamp_is_invented_for_the_continuation(built):
    record = built["continuation_record"]
    assert record["continuation_timestamp_status"] == (
        "UNRESOLVED_EXACT_TIMESTAMP")


def test_the_initial_authorization_record_is_preserved(built):
    assert m.AUTHORIZATION_REL in built["artifact_texts"]
    assert built["continuation_record"][
        "supplements_but_does_not_replace"].endswith(
        "human_authorization_record.json")
    assert built["authorization_record"]["authorization_sha256"] == (
        m.HUMAN_AUTHORIZATION_SHA256)


def test_a_second_invocation_without_continuation_authorization_fails():
    with pytest.raises(ERROR):
        m.assert_continuation_record_is_sound({
            "capture_invocations": 2,
            "continuation_was_explicitly_requested_from_human": False,
            "third_invocation_present": False})


@pytest.mark.parametrize("bad", [
    {"continuation_scope_changed": True},
    {"continuation_authorized_new_scientific_action": True},
    {"continuation_authorized_only_completion_of_same_capture": False},
    {"continuation_selected_option_text": ""},
])
def test_a_widened_continuation_fails_closed(bad):
    record = {
        "capture_invocations": 2,
        "continuation_was_explicitly_requested_from_human": True,
        "continuation_selected_option_text": "x",
        "continuation_scope_changed": False,
        "continuation_authorized_new_scientific_action": False,
        "continuation_authorized_only_completion_of_same_capture": True,
        "third_invocation_present": False,
    }
    record.update(bad)
    with pytest.raises(ERROR):
        m.assert_continuation_record_is_sound(record)


@pytest.mark.parametrize("record", [
    {"capture_invocations": 3, "third_invocation_present": False},
    {"capture_invocations": 2, "third_invocation_present": True,
     "continuation_was_explicitly_requested_from_human": True,
     "continuation_selected_option_text": "x",
     "continuation_scope_changed": False,
     "continuation_authorized_new_scientific_action": False,
     "continuation_authorized_only_completion_of_same_capture": True},
])
def test_a_third_invocation_fails_closed(record):
    with pytest.raises(ERROR):
        m.assert_continuation_record_is_sound(record)


# --------------------------------------------------------------------------- #
# Section 2 — the captured evidence itself is frozen
# --------------------------------------------------------------------------- #

def test_capture_manifests_are_byte_identical_to_the_correction_base():
    result = m.assert_capture_manifests_unchanged(ROOT)
    assert result["frozen_against_head"] == (
        "4c7c6114dcda7b3b1382ee3eb48367522d1fd2a2")
    assert result["no_new_network_requests"] is True


def test_the_original_21_requests_are_unchanged(built):
    assert len(built["response_manifest"]) == 21
    assert all(r["capture_result"] == "SUCCESS"
               for r in built["response_manifest"])
    assert built["evidence_summary"]["official_responses_retained"] == 21
    assert built["evidence_summary"]["raw_bytes_total"] == 1066295643


# --------------------------------------------------------------------------- #
# Section 13 — financing metadata
# --------------------------------------------------------------------------- #

def test_financing_unresolved_does_not_invalidate_m3i2(built):
    decision = built["decision"]
    assert decision["financing_failure_invalidates_m3i2_evidence"] is False
    assert decision["m3i3_financing_metadata_decision"] in m.FINANCING_DECISIONS


@pytest.mark.parametrize("title", [
    "Deposit interest rate", "Deposit-rate ceiling", "Real interest rate",
    "Interest-rate spread", "Repo transaction volume",
])
def test_a_forbidden_financing_proxy_fails_closed(title):
    with pytest.raises(ERROR):
        m.assert_financing_not_a_forbidden_proxy(
            {"identified_series_title": title, "m3i3_admitted": False})


def test_financing_may_never_be_admitted_here():
    with pytest.raises(ERROR):
        m.assert_financing_not_a_forbidden_proxy(
            {"identified_series_title": "Lending rate", "m3i3_admitted": True})


def test_an_identified_candidate_stays_pending_a_separate_lock():
    assert m.M3I3_PENDING_STATUS.endswith(
        "PENDING_SEPARATE_PROSPECTIVE_LOCK")


# --------------------------------------------------------------------------- #
# Section 14 — the decision vocabulary
# --------------------------------------------------------------------------- #

def _complete_summary(**overrides):
    summary = {
        "integrity_violations": [],
        "required_editions_total": 3,
        "cutoffs_without_verified_pre_cutoff_edition": 0,
        "development_pairs_without_verified_pre_cutoff_edition": 0,
        "required_editions_with_verified_release_available_at": 3,
        "required_editions_captured": 3,
        "raw_bytes_retained_for_every_capture_claim": True,
        "locked_series_rows_extracted": 120,
        "indicator_substitution_occurred": False,
        "semantic_unresolved_count": 0,
        "semantic_fail_integrity_count": 0,
        "external_bundle_available_for_handoff": True,
        "offline_rebuild_reproduces_committed_artifacts": True,
        "data_gate_executions": 0,
        "company_macro_joins": 0,
    }
    summary.update(overrides)
    return summary


def test_a_fully_evidenced_capture_is_complete():
    assert m.classify_evidence(_complete_summary()) == m.EVIDENCE_COMPLETE


@pytest.mark.parametrize("gap", [
    {"required_editions_total": 0},
    {"cutoffs_without_verified_pre_cutoff_edition": 1},
    {"development_pairs_without_verified_pre_cutoff_edition": 12},
    {"required_editions_with_verified_release_available_at": 2},
    {"required_editions_captured": 2},
    {"raw_bytes_retained_for_every_capture_claim": False},
    {"locked_series_rows_extracted": 0},
    {"semantic_unresolved_count": 1},
    {"external_bundle_available_for_handoff": False},
])
def test_any_gap_downgrades_to_unresolved_not_invalid(gap):
    assert m.classify_evidence(_complete_summary(**gap)) == (
        m.EVIDENCE_UNRESOLVED)


@pytest.mark.parametrize("violation", [
    ["hash mismatch: x"], ["STOP_RAW_BYTES_NOT_RETAINED: y"],
])
def test_an_integrity_violation_is_invalid_not_unresolved(violation):
    assert m.classify_evidence(
        _complete_summary(integrity_violations=violation)) == (
        m.EVIDENCE_INVALID)


def test_a_gate_or_join_leak_can_never_be_complete():
    assert m.classify_evidence(
        _complete_summary(data_gate_executions=1)) == m.EVIDENCE_UNRESOLVED
    assert m.classify_evidence(
        _complete_summary(company_macro_joins=1)) == m.EVIDENCE_UNRESOLVED


def test_result_code_and_next_pointer_track_the_status():
    for status in m.EVIDENCE_STATUSES:
        assert status in m.RESULT_CODES
        assert status in m.NEXT_ACTION_BY_STATUS
    assert m.NEXT_ACTION_BY_STATUS[m.EVIDENCE_COMPLETE] == (
        "stage128-m3i2-data-gate")
    assert m.NEXT_ACTION_BY_STATUS[m.EVIDENCE_UNRESOLVED] == (
        "stage128-m3i2-official-source-evidence-review")
    assert m.NEXT_ACTION_BY_STATUS[m.EVIDENCE_INVALID] == (
        "stage128-m3i2-official-source-evidence-integrity-review")


def test_evidence_completion_never_authorizes_the_data_gate(built):
    governance = built["governance_boundary"]
    assert governance[
        "evidence_completion_does_not_authorize_the_data_gate"] is True
    assert governance["next_research_action_authorized"] is False
    assert built["decision"]["next_research_action_authorized"] is False
    assert built["decision"]["data_gate_passed"] is False
    assert built["decision"]["m3i2_admitted"] is False


# --------------------------------------------------------------------------- #
# Section 10 — raw-byte retention and the external bundle
# --------------------------------------------------------------------------- #

def test_bundle_is_deterministic_and_retains_raw_bytes(tmp_path):
    capture = tmp_path / "capture"
    (capture / "raw").mkdir(parents=True)
    (capture / "raw" / "a.bin").write_bytes(b"alpha")
    (capture / "raw" / "b.bin").write_bytes(b"beta")

    first = m.build_external_bundle(capture, tmp_path / "bundle1")
    second = m.build_external_bundle(capture, tmp_path / "bundle2")
    assert first["bundle_parts"][0]["sha256"] == (
        second["bundle_parts"][0]["sha256"])
    assert first["raw_bytes_deleted_after_hashing"] is False
    assert first["raw_bytes_committed_to_git"] is False
    assert first["raw_bytes_available_for_independent_handoff"] is True
    # raw bytes survive bundling
    assert (capture / "raw" / "a.bin").read_bytes() == b"alpha"


def test_an_empty_capture_directory_fails_closed(tmp_path):
    (tmp_path / "empty").mkdir()
    with pytest.raises(ERROR) as exc:
        m.build_external_bundle(tmp_path / "empty", tmp_path / "out")
    assert "STOP_RAW_BYTES_NOT_RETAINED" in str(exc.value)


def test_a_tampered_bundle_hash_fails_closed(tmp_path):
    capture = tmp_path / "capture"
    capture.mkdir()
    (capture / "x.bin").write_bytes(b"x")
    manifest = m.build_external_bundle(capture, tmp_path / "bundle")
    m.verify_bundle_manifest(manifest, tmp_path / "bundle")

    tampered = copy.deepcopy(manifest)
    tampered["bundle_parts"][0]["sha256"] = "0" * 64
    with pytest.raises(ERROR) as exc:
        m.verify_bundle_manifest(tampered, tmp_path / "bundle")
    assert "STOP_EXTERNAL_BUNDLE_HASH_MISMATCH" in str(exc.value)


def test_a_missing_bundle_part_fails_closed(tmp_path):
    with pytest.raises(ERROR) as exc:
        m.verify_bundle_manifest(
            {"bundle_parts": [{"filename": "absent.zip", "sha256": "0" * 64}]},
            tmp_path)
    assert "STOP_RAW_BYTES_NOT_RETAINED" in str(exc.value)


def test_multipart_parts_are_valid_bounded_zips(tmp_path):
    capture = tmp_path / "capture"
    (capture / "raw").mkdir(parents=True)
    for name in ("a.bin", "b.bin", "c.bin"):
        (capture / "raw" / name).write_bytes(name.encode() * 1000)
    manifest = m.build_multipart_handoff_bundle(capture, tmp_path / "mp")
    assert manifest["multipart_total_parts"] >= 1
    assert manifest["every_member_assigned_exactly_once"] is True
    assert manifest["parts_are_valid_zip_archives"] is True
    for part in manifest["multipart_parts"]:
        assert part["byte_size"] <= m.MULTIPART_MAX_BYTES
        path = tmp_path / "mp" / part["filename"]
        with zipfile.ZipFile(path) as zf:      # a real ZIP, not a byte slice
            assert zf.testzip() is None
            assert m.MULTIPART_HANDOFF_MANIFEST_MEMBER in zf.namelist()
    assert (tmp_path / "mp" / "SHA256SUMS.txt").is_file()
    # originals untouched
    assert (capture / "raw" / "a.bin").read_bytes() == b"a.bin" * 1000


def test_multipart_allocation_covers_every_member_exactly_once(tmp_path):
    capture = tmp_path / "capture"
    capture.mkdir()
    for i in range(5):
        (capture / f"f{i}.bin").write_bytes(bytes([i]) * 500)
    manifest = m.build_multipart_handoff_bundle(capture, tmp_path / "mp")
    allocated = [mem["member_path"]
                 for part in manifest["multipart_parts"]
                 for mem in part["members"]]
    assert sorted(allocated) == sorted(f"f{i}.bin" for i in range(5))
    assert len(allocated) == len(set(allocated))
    assert all(mem["primary_member"] is True
               for part in manifest["multipart_parts"]
               for mem in part["members"])


def test_multipart_is_deterministic(tmp_path):
    capture = tmp_path / "capture"
    capture.mkdir()
    (capture / "x.bin").write_bytes(b"x" * 4096)
    first = m.build_multipart_handoff_bundle(capture, tmp_path / "one")
    second = m.build_multipart_handoff_bundle(capture, tmp_path / "two")
    assert [p["sha256"] for p in first["multipart_parts"]] == (
        [p["sha256"] for p in second["multipart_parts"]])


def test_a_tampered_part_fails_closed(tmp_path):
    capture = tmp_path / "capture"
    capture.mkdir()
    (capture / "x.bin").write_bytes(b"x" * 100)
    manifest = m.build_multipart_handoff_bundle(capture, tmp_path / "mp")
    manifest["multipart_parts"][0]["sha256"] = "0" * 64
    with pytest.raises(ERROR) as exc:
        m.verify_multipart_bundle(manifest, tmp_path / "mp")
    assert "STOP_EXTERNAL_BUNDLE_HASH_MISMATCH" in str(exc.value)


def test_independent_verification_is_not_claimed_before_delivery(built):
    manifest = built["bundle_manifest"]
    assert manifest.get("independently_verified_by_auditor") is False
    assert manifest.get("delivered_to_independent_auditor") is False
    assert manifest.get("files_the_human_must_upload")
    assert manifest.get("original_single_bundle_retained") is True


def test_raw_bytes_are_never_committed_to_git(built):
    assert built["bundle_manifest"]["raw_bytes_committed_to_git"] is False
    tracked = (ROOT / m.PACKAGE_DIR_REL)
    if tracked.is_dir():
        assert not any(p.suffix == ".zip" for p in tracked.rglob("*"))


# --------------------------------------------------------------------------- #
# Section 17 — static firewalls
# --------------------------------------------------------------------------- #

def test_the_offline_layer_has_no_network_import():
    m.assert_offline_layer_has_no_network(ROOT)


def test_no_model_or_estimator_path_anywhere():
    m.assert_no_model_or_estimator(ROOT)


def test_no_forbidden_computation_path_anywhere():
    m.assert_no_forbidden_computation(ROOT)


def test_no_unofficial_source_is_referenced():
    m.assert_no_unofficial_source(ROOT)


def _probe(tmp_path: Path, body: str) -> Path:
    root = tmp_path / "probe"
    for rel in m.OFFLINE_IMPLEMENTATION_FILES + (
            m.CAPTURE_LAYER_FILE, m.RUNNER_FILE):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# clean\n", encoding="utf-8")
    (root / m.OFFLINE_IMPLEMENTATION_FILES[0]).write_text(
        body, encoding="utf-8")
    return root


def test_a_network_import_in_the_offline_layer_fails_closed(tmp_path):
    root = _probe(tmp_path, "import " + "requests\n")
    with pytest.raises(ERROR):
        m.assert_offline_layer_has_no_network(root)


def test_a_model_import_fails_closed(tmp_path):
    root = _probe(tmp_path, "import " + "sklearn\n")
    with pytest.raises(ERROR):
        m.assert_no_model_or_estimator(root)


def test_an_estimator_call_fails_closed(tmp_path):
    root = _probe(tmp_path, "model" + "." + "fit" + "(" + "X, y)\n")
    with pytest.raises(ERROR):
        m.assert_no_model_or_estimator(root)


def test_an_fx_log_transformation_fails_closed(tmp_path):
    root = _probe(tmp_path, "v = 100 * math" + "." + "log" + "(" + "a / b)\n")
    with pytest.raises(ERROR):
        m.assert_no_forbidden_computation(root)


def test_a_coverage_calculation_fails_closed(tmp_path):
    root = _probe(tmp_path, "candidate_valid_coverage " + "= n / d\n")
    with pytest.raises(ERROR):
        m.assert_no_forbidden_computation(root)


def test_a_gate_result_assignment_fails_closed(tmp_path):
    root = _probe(tmp_path, "gate_result " + "= 'PASS'\n")
    with pytest.raises(ERROR):
        m.assert_no_forbidden_computation(root)


def test_an_aggregator_reference_fails_closed(tmp_path):
    root = _probe(tmp_path, "URL = 'https://db" + "nomics.world/x'\n")
    with pytest.raises(ERROR):
        m.assert_no_unofficial_source(root)


def test_a_clean_probe_passes_every_scanner(tmp_path):
    root = _probe(tmp_path, "VALUE = 1\n")
    m.assert_offline_layer_has_no_network(root)
    m.assert_no_model_or_estimator(root)
    m.assert_no_forbidden_computation(root)
    m.assert_no_unofficial_source(root)


def test_the_capture_layer_is_the_only_network_module():
    import re

    assert m.CAPTURE_LAYER_FILE not in m.OFFLINE_IMPLEMENTATION_FILES
    pattern = re.compile(r"^\s*(?:from|import)\s+urllib\b", re.MULTILINE)
    # the capture layer is allowed to import it...
    assert pattern.search(
        (ROOT / m.CAPTURE_LAYER_FILE).read_text(encoding="utf-8"))
    # ...and nothing else may
    for rel in m.OFFLINE_IMPLEMENTATION_FILES:
        assert not pattern.search((ROOT / rel).read_text(encoding="utf-8"))


def test_no_test_issues_a_live_request():
    text = Path(__file__).read_text(encoding="utf-8")
    for token in ("fetch_" + "once(", "fetch_with_" + "retries(",
                  "capture_" + "objects("):
        assert token not in text.replace("test_no_test_issues_a_live_request",
                                         "")


# --------------------------------------------------------------------------- #
# Section 19-20 — state, counters and QC
# --------------------------------------------------------------------------- #

def test_pr74_is_recorded_as_merged_history(built):
    governance = built["governance_boundary"]
    assert governance["predecessor_pr_number"] == 74
    assert governance["predecessor_pr_merged"] is True
    assert governance["predecessor_pr_merge_commit"] == MERGE_COMMIT
    assert governance["predecessor_pr_still_draft"] is False
    assert built["decision"]["predecessor_pr_merged"] is True


def test_this_pr_is_a_draft_on_main_with_no_merge_rights(built):
    governance = built["governance_boundary"]
    assert governance["pr_base_branch"] == "main"
    assert governance["pr_is_draft"] is True
    assert governance["pr_is_stacked"] is False
    assert governance["merge_authorized"] is False
    assert governance["auto_merge"] is False


def test_scientific_state_is_unchanged(built):
    governance = built["governance_boundary"]
    assert governance["m3i2_contract_status"] == "PROSPECTIVELY_LOCKED_NO_DATA"
    assert governance["m3i2_data_gate_executed"] is False
    assert governance["m3i2_block_admitted"] is False
    assert governance["m3i2_modeling_started"] is False
    assert governance["m3i3_admitted"] is False
    assert governance["m3i3_lock_status"] == "UNRESOLVED_METADATA_LOCK"
    assert governance["m3_cbi_status"] == "UNRESOLVED_M3_DATA_GATE"
    assert governance["m3_cbi_admitted"] is False
    assert governance["m3_cbi_modified_by_this_action"] is False


def test_final_test_stays_locked_and_m4_unstarted(built):
    governance = built["governance_boundary"]
    assert governance["final_test_locked"] is True
    assert governance["final_test_access_authorized"] is False
    assert governance["m4_authorized"] is False
    assert governance["m4_started"] is False


@pytest.mark.parametrize("counter", m.EXECUTION_COUNTER_FIELDS)
def test_every_forbidden_execution_counter_is_zero(built, counter):
    assert built["decision"][counter] == 0
    assert built["qc_report"]["forbidden_execution_counters"][counter] == 0


def test_counts_are_labelled_integrity_not_coverage(built):
    qc = built["qc_report"]
    summary = built["evidence_summary"]
    assert qc["counts_are_integrity_counts_not_coverage"] is True
    assert summary["counts_are_integrity_counts_not_coverage"] is True
    assert "candidate_coverage" not in summary
    assert "block_common_sample_coverage" not in summary


def test_an_unservable_cutoff_prevents_completion():
    """Capturing the editions that exist is not the same as serving every
    cutoff: a cutoff with no verified pre-cutoff vintage leaves a hole."""
    assert m.classify_evidence(_complete_summary(
        cutoffs_without_verified_pre_cutoff_edition=19)) == (
        m.EVIDENCE_UNRESOLVED)


def test_the_real_capture_has_unservable_cutoffs(built):
    summary = built["evidence_summary"]
    assert summary["cutoffs_without_verified_pre_cutoff_edition"] > 0
    assert summary["development_pairs_without_verified_pre_cutoff_edition"] > 0
    assert built["decision"]["m3i2_official_source_evidence_status"] == (
        m.EVIDENCE_UNRESOLVED)


def test_qc_passes(built):
    qc = built["qc_report"]
    assert qc["all_pass"] is True, qc["failed_assertions"]
    assert qc["failed_count"] == 0
    assert qc["assertion_count"] >= 20


def test_every_required_artifact_is_produced(built):
    required = {
        m.README_REL, m.AUTHORIZATION_REL, m.GOVERNANCE_REL,
        m.CUTOFF_AUDIT_REL, m.CUTOFF_PLAN_REL, m.RELEASE_MANIFEST_REL,
        m.REQUIRED_EDITIONS_REL, m.REQUEST_MANIFEST_REL,
        m.RESPONSE_MANIFEST_REL, m.LOCKED_SERIES_REL, m.SEMANTIC_REL,
        m.IMF_CATALOG_REL, m.FINANCING_EVIDENCE_REL, m.BUNDLE_MANIFEST_REL,
        m.DECISION_REL, m.QC_REL, m.METADATA_REL, m.CONTINUATION_REL,
    }
    assert set(built["artifact_texts"]) == required
    assert len(required) == 18


def test_offline_rebuild_is_deterministic():
    first = m.build_package(ROOT, write=False)["artifact_texts"]
    second = m.build_package(ROOT, write=False)["artifact_texts"]
    assert first == second


def test_committed_package_matches_a_fresh_offline_rebuild(built):
    for rel, text in built["artifact_texts"].items():
        path = ROOT / rel
        assert path.is_file(), rel
        assert path.read_text(encoding="utf-8") == text, rel


def test_readme_states_the_boundary(built):
    text = built["artifact_texts"][m.README_REL]
    for line in ("OFFICIAL-SOURCE EVIDENCE CAPTURE ONLY",
                 "NO COMPANY-PANEL MACRO JOIN", "NO FEATURE MATERIALIZATION",
                 "NO COVERAGE", "NO DATA GATE", "NO MODELING",
                 "NO M3I-vs-M2", "NO M4", "FINAL TEST LOCKED",
                 "NO MERGE AUTHORIZATION"):
        assert line in text
    assert "Data Gate passed" not in text
    assert "M3I-2 admitted" not in text


def test_artifacts_are_valid_json_and_sorted(built):
    for rel, text in built["artifact_texts"].items():
        if not rel.endswith(".json"):
            continue
        payload = json.loads(text)
        assert text == json.dumps(
            payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", rel
