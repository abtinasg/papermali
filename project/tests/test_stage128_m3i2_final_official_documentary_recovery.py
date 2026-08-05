"""Tests for the Stage128 M3I-2 final official documentary recovery INITIATION.

The action is an initiation: a bounded official documentary search plus the
preparation of exactly one official inquiry. These tests assert the bounds, the
privacy rules, the locked availability rules and — above all — that nothing
scientific moved.
"""

from __future__ import annotations

import csv
import json
import os
import sys

import pytest

REAL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REAL_ROOT, "project", "src"))

import stage128_m3i2_final_official_documentary_recovery as R  # noqa: E402

PKG = os.path.join(REAL_ROOT, R.PACKAGE_REL)
PRIOR_PKG = os.path.join(
    REAL_ROOT, "project/stage128/m3i2_official_source_evidence_capture")


def _json(name: str) -> dict:
    with open(os.path.join(PKG, name), encoding="utf-8") as fh:
        return json.load(fh)


def _csv(name: str) -> list[dict]:
    with open(os.path.join(PKG, name), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _contract() -> dict:
    return _json(
        "stage128_m3i2_final_official_documentary_recovery_contract.json")


def _decision() -> dict:
    return _json(
        "stage128_m3i2_final_official_documentary_recovery_decision.json")


def _submission() -> dict:
    return _json("stage128_m3i2_world_bank_inquiry_submission_record.json")


def _supersession() -> dict:
    return _json(
        "stage128_m3_lag_partial_local_execution_supersession_record.json")


# --------------------------------------------------------------------------- #
# Package, baseline and authorization
# --------------------------------------------------------------------------- #

REQUIRED_FILES = (
    "README_STAGE128_M3I2_FINAL_OFFICIAL_DOCUMENTARY_RECOVERY.md",
    "stage128_m3i2_final_official_documentary_recovery_contract.json",
    "stage128_m3i2_final_official_documentary_recovery_human_authorization"
    "_record.json",
    "stage128_m3i2_final_official_documentary_recovery_baseline.json",
    "stage128_m3i2_final_official_documentary_search_log.csv",
    "stage128_m3i2_final_official_documentary_evidence_manifest.csv",
    "stage128_m3i2_world_bank_inquiry_request.md",
    "m3i2_world_bank_inquiry_edition_inventory.csv",
    "m3i2_world_bank_inquiry_fx_semantic_questions.md",
    "stage128_m3i2_world_bank_inquiry_submission_record.json",
    "stage128_m3i2_final_official_documentary_recovery_governance_boundary.json",
    "stage128_m3i2_final_official_documentary_recovery_decision.json",
    "stage128_m3i2_final_official_documentary_recovery_qc_report.json",
    "metadata_and_hashes_stage128_m3i2_final_official_documentary_recovery.json",
    "stage128_m3_lag_partial_local_execution_supersession_record.json",
)


@pytest.mark.parametrize("name", REQUIRED_FILES)
def test_required_package_file_exists(name):
    assert os.path.isfile(os.path.join(PKG, name)), name


def test_baseline_is_the_pr75_merge_commit():
    contract = _contract()
    assert contract["baseline_commit"] == (
        "b3627809dbfde8429d0308bec5d1c8541a161188")
    assert contract["baseline_branch"] == "main"
    assert contract["predecessor_pr_number"] == 75
    assert contract["predecessor_pr_merged"] is True


def test_authorization_text_bytes_and_hash_are_exact():
    record = _json(
        "stage128_m3i2_final_official_documentary_recovery_human_authorization"
        "_record.json")
    payload = record["authorization_text"].encode("utf-8")
    assert len(payload) == 252 == record["authorization_utf8_bytes"]
    assert R.sha256_bytes(payload) == record["authorization_sha256"] == (
        "a1878df0e6ce46673ee426e2da19dfe14e6724b394978499d4ef09b90e9d9e97")
    assert record["authorization_consumed"] is True
    assert record["standing_authorization"] is False
    assert record["scope_identified_by_hash_alone"] is False


def test_qc_report_is_fail_closed_and_green():
    qc = _json(
        "stage128_m3i2_final_official_documentary_recovery_qc_report.json")
    assert qc["failed_count"] == 0 and qc["all_pass"] is True
    assert qc["assertion_count"] >= 60
    assert qc["failed_assertions"] == []


def test_metadata_hashes_match_every_package_file():
    meta = _json(
        "metadata_and_hashes_stage128_m3i2_final_official_documentary"
        "_recovery.json")
    assert meta["file_count"] >= len(REQUIRED_FILES)
    for rel, entry in meta["files"].items():
        path = os.path.join(REAL_ROOT, rel)
        assert os.path.isfile(path), rel
        assert R.sha256_file(path) == entry["sha256"], rel


# --------------------------------------------------------------------------- #
# The superseded local M3-LAG draft
# --------------------------------------------------------------------------- #

def test_prior_m3_lag_draft_is_recorded_as_local_partial_and_non_authoritative():
    record = _supersession()
    assert record["local_partial_execution_detected"] is True
    assert record["local_draft_contract_status"] == (
        "EXPLORATORY_CONTRACT_LOCKED_NO_DATA")
    assert record["authoritative_repository_contract_locked"] is False
    assert record["scientific_effective_contract_locked"] is False
    assert record["commits_created"] == 0
    assert record["remote_branch_created"] is False
    assert record["pull_request_created"] is False
    assert record["scientific_effect"] == "NONE_AUTHORITATIVE"


def test_prior_m3_lag_draft_did_nothing_scientific():
    record = _supersession()
    assert record["network_requests"] == 0
    assert record["wdi_files_downloaded"] == 0
    assert record["data_retrieval_started"] is False
    assert record["data_gate_executed"] is False
    assert record["modeling_started"] is False
    assert record["final_test_accessed"] is False


def test_prior_m3_lag_authorization_is_consumed_and_not_reusable():
    record = _supersession()
    assert record["prior_authorization_consumed_by_partial_local_execution"] \
        is True
    assert record["prior_authorization_reusable"] is False
    assert record["completion_authorized"] is False
    assert record["commit_authorized"] is False
    assert record["merge_authorized"] is False


def test_quarantine_is_hashed_but_never_committed_and_deletes_nothing():
    record = _supersession()
    assert record["quarantine_created"] is True
    assert record["quarantine_location_committed_to_git"] is False
    assert len(record["quarantine_manifest_sha256"]) == 64
    assert len(record["quarantine_archive_sha256"]) == 64
    assert record["original_dirty_worktree_modified_by_this_action"] is False
    assert record["original_dirty_worktree_cleaned_or_deleted"] is False
    # no absolute path and no system username may leak into Git
    body = json.dumps(record, ensure_ascii=False)
    assert "/Users/" not in body and "/home/" not in body


def test_forbidden_characterizations_are_absent_from_the_package():
    forbidden = (
        "previous M3-LAG prompt was never executed",
        "no M3-LAG artifacts were ever created",
    )
    for name in ("README_STAGE128_M3I2_FINAL_OFFICIAL_DOCUMENTARY_RECOVERY.md",
                 "stage128_m3_lag_partial_local_execution_supersession"
                 "_record.json"):
        text = open(os.path.join(PKG, name), encoding="utf-8").read()
        for phrase in forbidden:
            assert phrase not in text


# --------------------------------------------------------------------------- #
# Bounded search
# --------------------------------------------------------------------------- #

def test_documentary_search_stays_within_its_ceiling():
    rows = _csv("stage128_m3i2_final_official_documentary_search_log.csv")
    assert 0 < len(rows) <= R.MAX_DOCUMENTARY_GET_REQUESTS == 20
    assert _contract()["official_documentary_get_requests_executed"] == len(rows)


def test_no_request_repeats_a_prior_capture_and_no_zip_was_downloaded():
    rows = _csv("stage128_m3i2_final_official_documentary_search_log.csv")
    prior = R.prior_captured_urls(REAL_ROOT)
    urls = [row["request_url"] for row in rows]
    assert len(set(urls)) == len(urls)
    for url in urls:
        assert url not in prior
        assert not R.is_archive_zip(url)
        assert R.is_official_host(url)
    contract = _contract()
    assert contract["archive_zip_downloads"] == 0
    assert contract["archive_zip_redownloads"] == 0


def test_duplicate_and_zip_requests_are_refused_by_the_guard(tmp_path):
    log: list[dict] = []
    prior = sorted(R.prior_captured_urls(REAL_ROOT))
    with pytest.raises(R.RecoveryError):        # duplicate of a prior capture
        R.guard_request(prior[0], REAL_ROOT, log)
    with pytest.raises(R.RecoveryError):        # archive ZIP
        R.guard_request(
            "https://databank.worldbank.org/data/download/archive/"
            "WDI_excel_2019_12_20.zip", REAL_ROOT, log)
    with pytest.raises(R.RecoveryError):        # unofficial host
        R.guard_request("https://example.com/wdi", REAL_ROOT, log)
    with pytest.raises(R.RecoveryError):        # non-https
        R.guard_request("http://data.worldbank.org/x", REAL_ROOT, log)
    with pytest.raises(R.RecoveryError):        # ceiling exhausted
        R.guard_request(
            "https://data.worldbank.org/fresh",
            REAL_ROOT,
            [{"request_url": f"https://data.worldbank.org/{i}"}
             for i in range(R.MAX_DOCUMENTARY_GET_REQUESTS)])


def test_every_retained_document_is_official_and_hashed():
    rows = _csv("stage128_m3i2_final_official_documentary_evidence_manifest.csv")
    assert rows
    for row in rows:
        assert len(row["raw_sha256"]) == 64
        assert int(row["retained_byte_count"]) > 0
        path = os.path.join(REAL_ROOT, row["retained_artifact_path"])
        assert R.sha256_file(path) == row["raw_sha256"]
        assert row["official_host"] == "True"


def test_no_document_is_claimed_to_resolve_a_blocker():
    rows = _csv("stage128_m3i2_final_official_documentary_evidence_manifest.csv")
    for row in rows:
        assert row["resolves_blocker"] == "False"
        assert row["establishes_official_archive_release_date"] == "False"
        assert row["establishes_fx_unit_continuity"] == "False"
    decision = _decision()
    assert decision["blocker_1_resolved"] is False
    assert decision["blocker_2_resolved"] is False
    assert decision["bounded_search_outcome"] in (
        "OFFICIAL_DOCUMENTARY_EVIDENCE_FOUND_DURING_BOUNDED_SEARCH",
        "NO_NEW_DOCUMENTARY_EVIDENCE_IN_BOUNDED_SEARCH")


def test_exactly_two_blockers_are_targeted():
    assert _decision()["blockers_targeted"] == [
        "archive_release_availability",
        "historical_fx_semantic_continuity_pa_nus_fcrf_irn"]


# --------------------------------------------------------------------------- #
# Availability rules A-E
# --------------------------------------------------------------------------- #

def test_rule_a_exact_timestamp_is_kept():
    out = R.resolve_available_at(official_timestamp_utc="2019-12-20T14:05:00Z")
    assert out == {"available_at": "2019-12-20T14:05:00Z",
                   "release_date_verified": True, "rule_applied": "A"}


def test_rule_b_full_date_moves_to_the_next_day():
    assert R.resolve_available_at(official_full_date="2019-12-31") == {
        "available_at": "2020-01-01T00:00:00Z",
        "release_date_verified": True, "rule_applied": "B"}


def test_rule_c_month_only_moves_to_the_first_of_the_next_month():
    assert R.resolve_available_at(official_month="2019-12")["available_at"] == (
        "2020-01-01T00:00:00Z")
    assert R.resolve_available_at(official_month="2018-04")["available_at"] == (
        "2018-05-01T00:00:00Z")


def test_rules_d_and_e_refuse_to_invent_a_release_date():
    out = R.resolve_available_at(filename_token_only=True)
    assert out["available_at"] is None
    assert out["release_date_verified"] is False
    assert R.resolve_available_at()["available_at"] is None
    contract = _contract()
    assert contract["filename_token_is_release_evidence"] is False
    assert contract["unproven_previous_month_fallback_permitted"] is False
    assert contract["official_month_only_next_month_rule_locked"] is True
    assert _decision()["unproven_previous_month_fallback_used"] is False


def test_non_evidence_signals_are_enumerated():
    for signal in ("filename_token", "url_token", "http_last_modified",
                   "zip_member_timestamp", "workbook_properties",
                   "local_file_mtime", "search_engine_snippet"):
        assert signal in R.NON_EVIDENCE_SIGNALS


def test_edition_inventory_never_claims_a_verified_release_date():
    rows = _csv("m3i2_world_bank_inquiry_edition_inventory.csv")
    assert len(rows) == 110
    for row in rows:
        assert row["edition_date_token_current_status"] == (
            "UNVERIFIED_TOKEN_NOT_ACCEPTED_AS_RELEASE_DATE")
        assert row["requested_official_release_date"] == "REQUESTED"
    assert _decision()["editions_with_verified_release_date"] == 0


# --------------------------------------------------------------------------- #
# The official inquiry
# --------------------------------------------------------------------------- #

def test_inquiry_body_and_attachment_hashes_are_exact():
    submission = _submission()
    for name, key in (
        ("stage128_m3i2_world_bank_inquiry_request.md", "submitted_body_sha256"),
        ("m3i2_world_bank_inquiry_edition_inventory.csv",
         "edition_inventory_sha256"),
        ("m3i2_world_bank_inquiry_fx_semantic_questions.md",
         "fx_questions_sha256"),
    ):
        assert R.sha256_file(os.path.join(PKG, name)) == submission[key], name


def test_inquiry_asks_both_blocker_questions():
    body = open(os.path.join(PKG, "stage128_m3i2_world_bank_inquiry_request.md"),
                encoding="utf-8").read()
    for phrase in ("release calendar", "version history", "date tokens",
                   "PA.NUS.FCRF", "redenomination", "unit break",
                   "FP.CPI.TOTL.ZG"):
        assert phrase in body
    assert "alternative indicators" in body


def test_only_one_initial_inquiry_is_permitted_and_none_was_faked():
    submission = _submission()
    assert submission["initial_inquiry_max_count"] == 1
    assert submission["initial_inquiries_attempted"] <= 1
    assert submission["initial_inquiries_successfully_submitted"] <= 1
    assert submission["submission_status"] in (
        "OFFICIAL_INQUIRY_SUBMITTED_PENDING_RESPONSE",
        "HUMAN_SUBMISSION_REQUIRED")
    if submission["submission_status"] == "HUMAN_SUBMISSION_REQUIRED":
        assert submission["initial_inquiries_successfully_submitted"] == 0
        assert submission["submission_timestamp_utc"] is None
        assert submission["ticket_id_redacted"] is None
        assert submission["ticket_id_sha256"] is None
        assert submission["external_raw_confirmation_present"] is False
        assert submission["human_submission_instructions"]


def test_no_credentials_no_captcha_bypass_and_no_pii_in_git():
    submission = _submission()
    assert submission["credentials_used_by_automation"] is False
    assert submission["captcha_bypassed"] is False
    assert submission["pii_committed_to_git"] is False
    blob = ""
    for name in ("m3i2_world_bank_inquiry_edition_inventory.csv",
                 "m3i2_world_bank_inquiry_fx_semantic_questions.md",
                 "stage128_m3i2_world_bank_inquiry_request.md",
                 "stage128_m3i2_world_bank_inquiry_submission_record.json"):
        blob += open(os.path.join(PKG, name), encoding="utf-8").read().lower()
    for pattern in ("password", "api_key", "access_token", "session cookie",
                    "bearer ", "@gmail.", "@yahoo.", "/users/"):
        assert pattern not in blob, pattern


def test_attachments_carry_no_scientific_payload():
    inventory = open(os.path.join(
        PKG, "m3i2_world_bank_inquiry_edition_inventory.csv"),
        encoding="utf-8").read().lower()
    for banned in ("distress", "target", "default", "final_test", "ticker",
                   "predictor"):
        assert banned not in inventory, banned
    for attachment in _submission()["attachments"]:
        assert attachment["contains_target_values"] is False
        assert attachment["contains_final_test_rows"] is False
        assert attachment["contains_company_predictor_values"] is False
        assert attachment["contains_personal_information"] is False
        assert attachment["contains_credentials"] is False


def test_stopping_rule_is_locked_prospectively():
    submission = _submission()
    assert submission["waiting_period_business_days"] == 10
    assert "Monday through Friday" in (
        submission["waiting_period_business_day_definition"])
    assert "submission day is excluded" in (
        submission["waiting_period_business_day_definition"])
    assert submission["follow_up_max_count"] == 1
    assert submission["follow_up_authorized_now"] is False
    assert submission["automatic_follow_up_authorized"] is False
    assert submission["response_adjudication_authorized"] is False
    assert _contract()["terminal_status_after_final_inquiry_without_response"] \
        == "UNRESOLVED_AFTER_FINAL_OFFICIAL_INQUIRY"


# --------------------------------------------------------------------------- #
# Nothing scientific moved
# --------------------------------------------------------------------------- #

def test_m3i2_remains_unresolved_and_unadmitted():
    decision = _decision()
    assert decision["m3i2_evidence_status"] == (
        "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE")
    assert decision["m3i2_admitted"] is False
    assert decision["m3i2_data_gate_executed"] is False
    assert decision["m3i2_modeling_started"] is False
    assert decision["m3_cbi_status"] == "UNRESOLVED_M3_DATA_GATE"
    assert decision["m3i3_lock_status"] == "UNRESOLVED_METADATA_LOCK"


def test_partial_recovery_can_never_admit_m3i2():
    contract = _contract()
    assert contract["partial_documentary_recovery_can_admit_m3i2"] is False
    assert contract["release_date_recovery_alone_can_admit_m3i2"] is False
    assert contract["fx_semantic_recovery_alone_can_admit_m3i2"] is False
    assert len(contract["both_evidence_classes_required_for_a_future_"
                        "resolution"]) == 2


def test_m3_lag_wdi_remains_unlocked_in_the_authoritative_repository():
    decision = _decision()
    assert decision["m3_lag_wdi_authoritative_contract_status"] == "NOT_LOCKED"
    assert decision["m3_lag_wdi_exploratory_contract_locked"] is False
    assert decision["m3_lag_wdi_data_retrieval_started"] is False
    boundary = _json(
        "stage128_m3i2_final_official_documentary_recovery_governance"
        "_boundary.json")
    assert boundary["m3_lag_wdi_exploratory_contract_locked"] is False
    assert boundary["m3_lag_wdi_data_gate_executed"] is False
    assert boundary["m3_lag_wdi_modeling_started"] is False
    assert boundary["m3_lag_wdi_local_partial_draft_detected"] is True
    assert boundary["m3_lag_wdi_local_partial_draft_quarantined"] is True


def test_bundle_integrity_pass_is_not_vintage_resolution():
    baseline = _json(
        "stage128_m3i2_final_official_documentary_recovery_baseline.json")
    assert baseline["verified_merged_scientific_state"][
        "independent_bundle_integrity_audit"] == (
        "INDEPENDENT_BUNDLE_INTEGRITY_AUDIT_PASS")
    assert baseline[
        "bundle_integrity_pass_is_not_historical_vintage_resolution"] is True
    assert _decision()[
        "bundle_integrity_pass_is_not_historical_vintage_resolution"] is True


def test_prior_findings_are_carried_read_only_and_not_recomputed():
    baseline = _json(
        "stage128_m3i2_final_official_documentary_recovery_baseline.json")
    assert baseline["prior_findings_recomputed"] is False
    assert baseline["prior_capture_repeated"] is False
    findings = baseline["prior_findings_carried_read_only"]
    assert findings["unique_development_cutoffs"] == 37
    assert findings["development_parent_rows"] == 539
    assert findings["archive_editions_discovered"] == 110
    assert findings["archive_editions_already_captured"] == 16
    assert findings["official_requests_already_completed"] == 21
    assert findings["successful_responses_already_retained"] == 21
    assert findings["locked_iran_series_rows_already_extracted"] == 1878
    assert findings["editions_with_verified_release_date"] == 0
    assert findings["cutoffs_with_verified_pre_cutoff_edition"] == 0
    assert findings["unresolved_cutoffs"] == 37
    assert findings["unresolved_development_pairs"] == 539
    assert findings["cpi_semantic_pass_count"] == 16
    assert findings["fx_semantic_unresolved_count"] == 16


@pytest.mark.parametrize("counter", [
    "company_macro_joins", "feature_materializations", "coverage_calculations",
    "data_gate_executions", "model_fits", "predictions", "predictive_metrics",
    "bootstrap_executions", "holm_calculations", "target_values_read",
    "final_test_rows_read", "final_test_predictor_values_inspected",
    "final_test_target_values_inspected", "m3i2_admission_decisions",
    "m3_lag_wdi_contract_locks", "m3_lag_wdi_data_retrievals",
    "archive_zip_downloads", "archive_zip_redownloads",
])
def test_forbidden_counter_is_zero(counter):
    assert _contract()[counter] == 0


def test_final_test_m4_and_merge_stay_locked():
    contract, decision = _contract(), _decision()
    assert contract["final_test_locked"] is True
    assert contract["final_test_access_authorized"] is False
    assert contract["m4_authorized"] is False and contract["m4_started"] is False
    assert contract["paper_winner_selected"] is False
    assert contract["final_model_selected"] is False
    assert contract["merge_authorized"] is False
    assert decision["merge_authorized"] is False
    assert decision["final_test_locked"] is True


def test_next_pointer_exists_but_is_not_an_authorization():
    decision = _decision()
    assert decision["next_research_action_id"] in (
        "stage128-m3i2-final-official-response-adjudication",
        "stage128-m3i2-final-official-inquiry-human-submission")
    assert decision["next_research_action_authorized"] is False
    assert decision["next_action_pointer_is_not_authorization"] is True


def test_no_archive_zip_object_is_committed_in_the_package():
    for dirpath, _dirs, names in os.walk(PKG):
        for name in names:
            assert not name.lower().endswith(".zip"), name
