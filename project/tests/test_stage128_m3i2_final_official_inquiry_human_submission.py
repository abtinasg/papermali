"""Stage128 — M3I-2 final official inquiry: the HUMAN submission recording.

These tests police one narrow claim: a human supervisor submitted the prepared
World Bank inquiry exactly once, an acknowledgement came back, and *nothing
else happened*. They exist to stop the record from growing stronger than the
evidence — no invented ticket id, no reconstructed UTC instant, no byte-level
body proof the screenshots never gave, no server-side attachment receipt, no
early follow-up, and no scientific movement of any kind.
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import subprocess

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

_PKG_REL = "project/stage128/m3i2_final_official_inquiry_human_submission"
_CANONICAL_REL = (
    "project/stage128/m3i2_final_official_documentary_recovery/"
    "stage128_m3i2_world_bank_inquiry_submission_record.json")
_DOCS = ("project/docs/ai/ROADMAP.md", "project/docs/ai/OPEN_TASKS.md")

_AUTHORIZATION_SHA256 = (
    "4562e480db041f93bdd9f565ee65d6e3664243e12f00126a8d42759bb3717978")
_AUTHORIZATION_UTF8_BYTES = 95

_EDITION_INVENTORY_SHA256 = (
    "5c4739482d685ad4a1fd13c6a82d16cacb882d7e07996535671bb2f267b3a35b")
_FX_QUESTIONS_SHA256 = (
    "2cc118c224b43acdfa7abcee23c3b2a7ddd7dc0809a9ee072f29aad02276cf94")
_CANONICAL_BODY_SHA256 = (
    "dd82929f8098061d501c51b65cac6f3e3ed203cb00ff5689ae0e66f9f2f1e8b5")
_WEB_CONFIRMATION_SHA256 = (
    "14060eef17ccb52838433d8186b3e476d1a703d2476bb37cbd9b5aa8e0a931f6")
_EMAIL_PART_1_SHA256 = (
    "8841e6ab32115c21e2b994f5b80ac0311e826853e3059bc7c188a15a5a2f1e85")
_EMAIL_PART_2_SHA256 = (
    "dd95e54919f6809d5f07a2248e73dffc919b31465351c2a02c56c6eb1c626ca7")

_SUBMITTED_STATUS = "SUBMITTED_ACKNOWLEDGED_WAITING_FOR_SUBSTANTIVE_RESPONSE"
_UTC_UNRESOLVED = "UNRESOLVED_CONFIRMATION_UI_DID_NOT_DISPLAY_TIMEZONE"
_BODY_EVIDENCE = "CANONICAL_BODY_VISUALLY_CONFIRMED_NOT_RAW_BYTE_VERIFIED"


def _read_json(rel: str) -> dict:
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def _read_text(rel: str) -> str:
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def canonical() -> dict:
    return _read_json(_CANONICAL_REL)


@pytest.fixture(scope="module")
def evidence() -> dict:
    return _read_json(
        f"{_PKG_REL}/stage128_m3i2_final_official_inquiry_submission_"
        "evidence_record.json")


@pytest.fixture(scope="module")
def decision() -> dict:
    return _read_json(
        f"{_PKG_REL}/stage128_m3i2_final_official_inquiry_submission_"
        "decision.json")


@pytest.fixture(scope="module")
def boundary() -> dict:
    return _read_json(
        f"{_PKG_REL}/stage128_m3i2_final_official_inquiry_governance_"
        "boundary.json")


@pytest.fixture(scope="module")
def authorization() -> dict:
    return _read_json(
        f"{_PKG_REL}/stage128_m3i2_final_official_inquiry_human_"
        "authorization_record.json")


# --------------------------------------------------------------------------- #
# 1-3. exactly one initial inquiry, attempted and submitted, ceiling still one
# --------------------------------------------------------------------------- #

def test_exactly_one_initial_inquiry_was_attempted(canonical, evidence):
    assert canonical["initial_inquiries_attempted"] == 1
    assert evidence["initial_inquiries_attempted"] == 1


def test_exactly_one_initial_inquiry_was_successfully_submitted(
        canonical, evidence):
    assert canonical["initial_inquiries_successfully_submitted"] == 1
    assert evidence["initial_inquiries_successfully_submitted"] == 1
    assert canonical["submission_status"] == _SUBMITTED_STATUS
    assert canonical["human_authenticated_submission"] is True
    assert canonical["credentials_used_by_automation"] is False
    assert canonical["captcha_bypassed"] is False


def test_the_initial_inquiry_ceiling_is_still_exactly_one(canonical, evidence):
    assert canonical["initial_inquiry_max_count"] == 1
    assert evidence["initial_inquiry_max_count"] == 1


# --------------------------------------------------------------------------- #
# 4-5. an acknowledgement is a receipt, not an answer
# --------------------------------------------------------------------------- #

def test_an_acknowledgement_was_received(canonical, evidence):
    assert canonical["acknowledgement_received"] is True
    assert evidence["acknowledgement_received"] is True


def test_no_substantive_world_bank_response_was_received(canonical, evidence):
    assert canonical["substantive_response_received"] is False
    assert evidence["substantive_response_received"] is False
    assert canonical["acknowledgement_is_not_a_substantive_response"] is True
    assert evidence["acknowledgement_is_substantive_response"] is False


# --------------------------------------------------------------------------- #
# 6-7. no ticket id was displayed, so none may exist anywhere
# --------------------------------------------------------------------------- #

def test_no_ticket_id_was_fabricated(canonical, evidence):
    for record in (canonical, evidence):
        assert record["ticket_id_present"] is False
        assert record["ticket_id_fabricated"] is False
        assert record["ticket_id_redacted"] is None


def test_no_ticket_id_hash_was_fabricated(canonical, evidence):
    for record in (canonical, evidence):
        assert record["ticket_id_sha256"] is None
    # and no stray 64-hex "ticket" hash smuggled in beside the field
    for rel in _package_files() + [_CANONICAL_REL]:
        text = _read_text(rel).lower()
        for match in re.finditer(r"ticket[_a-z]*\W{0,4}([0-9a-f]{64})", text):
            pytest.fail(f"{rel} carries a fabricated ticket hash: "
                        f"{match.group(1)}")


# --------------------------------------------------------------------------- #
# 8. the external confirmation hashes are exact
# --------------------------------------------------------------------------- #

def test_the_external_confirmation_hash_is_exact(canonical, evidence):
    for record in (canonical, evidence):
        assert record["external_raw_confirmation_present"] is True
        assert record["external_raw_confirmation_sha256"] == (
            _WEB_CONFIRMATION_SHA256)
        rows = record["external_confirmation_evidence"]
        assert len(rows) == 3
        assert [r["sha256"] for r in rows] == [
            _WEB_CONFIRMATION_SHA256, _EMAIL_PART_1_SHA256,
            _EMAIL_PART_2_SHA256]
        assert [r["byte_size"] for r in rows] == [631880, 383457, 339376]
        for row in rows:
            assert row["stored_outside_repository"] is True
            assert row["committed_to_git"] is False
            assert row["contains_personal_information"] is True


# --------------------------------------------------------------------------- #
# 9-10. nothing raw and nothing personal reached Git
# --------------------------------------------------------------------------- #

def _tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT,
                         capture_output=True, text=True, check=True)
    return out.stdout.splitlines()


def _package_files() -> list[str]:
    return sorted(
        os.path.relpath(p, REPO_ROOT)
        for p in glob.glob(os.path.join(REPO_ROOT, _PKG_REL, "*")))


_RAW_SUFFIXES = (".eml", ".msg", ".mbox", ".png", ".jpg", ".jpeg", ".webp",
                 ".gif", ".heic", ".pdf", ".mht", ".mhtml")


def test_no_screenshot_or_email_file_was_committed():
    offenders = [
        p for p in _tracked_files()
        if p.startswith((_PKG_REL, os.path.dirname(_CANONICAL_REL)))
        and p.lower().endswith(_RAW_SUFFIXES)
    ]
    assert offenders == [], offenders
    # and the package itself holds only the seven governance artifacts
    assert all(p.endswith((".json", ".md")) for p in _package_files())


_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
#: institutional addresses the inquiry legitimately names, if any appear
_ALLOWED_EMAIL_DOMAINS = ("worldbank.org",)


def test_no_personal_name_or_email_address_appears_in_committed_files():
    for rel in _package_files() + [_CANONICAL_REL] + list(_DOCS):
        for found in _EMAIL_RE.findall(_read_text(rel)):
            assert found.lower().endswith(_ALLOWED_EMAIL_DOMAINS), (
                f"{rel} leaks a personal e-mail address")
    for rel in _package_files() + [_CANONICAL_REL]:
        record = _read_text(rel)
        for banned in ("submitter_name", "submitter_email", "account_email",
                       "reply_to", "from_address", "ip_address"):
            assert banned not in record, f"{rel} carries {banned}"


def test_no_pii_flag_is_ever_set_on_a_committed_artifact(canonical, evidence):
    assert canonical["pii_committed_to_git"] is False
    assert evidence["pii_committed_to_git"] is False
    assert evidence["pii_recovery_from_screenshots_attempted"] is False


# --------------------------------------------------------------------------- #
# 11-13. the weak claims stay weak
# --------------------------------------------------------------------------- #

def test_the_body_hash_verification_is_not_overstated(canonical, evidence):
    for record in (canonical, evidence):
        assert record["canonical_body_sha256"] == _CANONICAL_BODY_SHA256
        assert record["body_submission_evidence_status"] == _BODY_EVIDENCE
        assert record["body_hash_byte_verified_from_raw_email_source"] is False
    assert canonical["submitted_body_sha256"] == _CANONICAL_BODY_SHA256


def test_both_attachment_hashes_are_unchanged(canonical, evidence):
    assert canonical["edition_inventory_sha256"] == _EDITION_INVENTORY_SHA256
    assert canonical["fx_questions_sha256"] == _FX_QUESTIONS_SHA256
    by_name = {a["name"]: a["sha256"] for a in evidence["attachments"]}
    assert by_name == {
        "m3i2_world_bank_inquiry_edition_inventory.csv":
            _EDITION_INVENTORY_SHA256,
        "m3i2_world_bank_inquiry_fx_semantic_questions.md":
            _FX_QUESTIONS_SHA256,
    }
    assert all(a["unchanged_since_preparation"] for a in
               evidence["attachments"])


def test_attachments_were_selected_but_not_server_enumerated(
        canonical, evidence):
    for record in (canonical, evidence):
        assert record["attachments_selected_before_submission"] is True
        assert record["attachments_server_confirmation_enumerated"] is False


# --------------------------------------------------------------------------- #
# 14. the timestamp and the waiting-period arithmetic
# --------------------------------------------------------------------------- #

def test_the_utc_instant_is_unresolved_and_was_never_guessed(
        canonical, evidence):
    for record in (canonical, evidence):
        assert record["submission_timestamp_displayed"] == "2026-08-06T14:03:00"
        assert record["submission_timestamp_display_timezone"] is None
        assert record["submission_timestamp_utc"] is None
        assert record["submission_timestamp_utc_status"] == _UTC_UNRESOLVED
        assert record["submission_calendar_date"] == "2026-08-06"


def test_the_waiting_period_dates_are_correct(canonical, decision):
    assert canonical["waiting_period_business_days"] == 10
    assert "Monday through Friday" in (
        canonical["waiting_period_business_day_definition"])
    assert "submission day is excluded" in (
        canonical["waiting_period_business_day_definition"])
    # business day 1 = 2026-08-07 (Fri), business day 10 = 2026-08-20 (Thu)
    assert canonical["waiting_period_completion_date"] == "2026-08-20"
    assert decision["waiting_period_completion_date"] == "2026-08-20"
    assert canonical["waiting_period_status"] == "ACTIVE"
    assert decision["waiting_period_status"] == "ACTIVE"


# --------------------------------------------------------------------------- #
# 15-17. no follow-up, no ingestion, no adjudication
# --------------------------------------------------------------------------- #

def test_a_follow_up_before_2026_08_21_is_forbidden(canonical, boundary):
    assert canonical["follow_up_earliest_calendar_date"] == "2026-08-21"
    assert canonical["follow_up_before_2026_08_21_forbidden"] is True
    assert boundary["follow_up_before_2026_08_21_forbidden"] is True
    assert boundary["conditional_follow_up_earliest_date"] == "2026-08-21"


def test_no_follow_up_is_authorized_and_none_was_attempted(
        canonical, boundary):
    assert canonical["follow_up_attempted"] == 0
    assert canonical["follow_up_max_count"] == 1
    assert canonical["follow_up_authorized_now"] is False
    assert canonical["automatic_follow_up_authorized"] is False
    assert canonical["automatic_follow_up_forbidden"] is True
    assert boundary["conditional_follow_up_authorized"] is False
    assert boundary["follow_up_authorized_now"] is False


def test_response_ingestion_and_adjudication_remain_unauthorized(
        canonical, boundary, decision):
    assert canonical["response_adjudication_authorized"] is False
    assert boundary["response_adjudication_authorized"] is False
    assert boundary["response_ingestion_authorized"] is False
    assert boundary["next_research_action_id"] == (
        "stage128-m3i2-final-official-inquiry-response-ingestion")
    assert boundary["next_research_action_authorized"] is False
    assert decision["next_research_action_authorized"] is False


# --------------------------------------------------------------------------- #
# 18-22. the science did not move
# --------------------------------------------------------------------------- #

def test_the_submission_resolves_no_scientific_blocker(decision):
    assert decision["scientific_effect"] == "NONE"
    assert decision["archive_release_blocker_resolved"] is False
    assert decision["fx_semantic_continuity_blocker_resolved"] is False
    assert decision["verified_wdi_release_dates"] == 0
    assert decision["verified_pre_cutoff_editions"] == 0
    assert decision["unresolved_cutoffs"] == 37
    assert decision["unresolved_cutoffs_total"] == 37
    assert decision["unresolved_development_pairs"] == 539
    assert decision["unresolved_development_pairs_total"] == 539
    assert decision["cpi_semantic_compatibility"] == {
        "pass": 16, "unresolved": 0, "fail_integrity": 0}
    assert decision["fx_semantic_compatibility"] == {
        "pass": 0, "unresolved": 16, "fail_integrity": 0}


def test_m3i2_remains_unresolved_and_unadmitted(decision, boundary):
    for record in (decision, boundary):
        assert record["m3i2_evidence_status"] == (
            "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE")
        assert record["m3i2_admitted"] is False


def test_the_data_gate_remains_not_executed(decision, boundary):
    assert decision["data_gate_status"] == "NOT_EXECUTED"
    assert boundary["m3i2_data_gate_executed"] is False
    for field in ("coverage_calculations", "feature_materializations",
                  "data_gate_executions", "model_fits", "predictions",
                  "predictive_metrics", "wdi_archive_downloads",
                  "network_requests"):
        assert boundary[field] == 0, field
    assert boundary["new_documentary_search_executed"] is False
    assert boundary["resubmission_executed"] is False
    assert boundary["gmail_or_personal_account_accessed"] is False


def test_m3_lag_wdi_remains_not_locked(decision, boundary):
    for record in (decision, boundary):
        assert record["m3_lag_wdi_authoritative_contract_status"] == (
            "NOT_LOCKED")
    assert boundary["m3_lag_wdi_exploratory_contract_locked"] is False


def test_the_final_test_remains_locked_and_m4_unauthorized(
        decision, boundary):
    for record in (decision, boundary):
        assert record["final_test_locked"] is True
        assert record["m4_authorized"] is False
        assert record["merge_authorized"] is False
    assert boundary["final_test_access_authorized"] is False
    assert boundary["m4_started"] is False
    assert boundary["paper_winner_selected"] is False


# --------------------------------------------------------------------------- #
# 23-26. the pointers, and the ROADMAP items
# --------------------------------------------------------------------------- #

def _roadmap_front_matter() -> dict:
    text = _read_text("project/docs/ai/ROADMAP.md")
    block = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL).group(1)
    fm = {}
    for line in block.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and ":" in line:
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip()
    return fm


def test_roadmap_pointers_match_the_handoff(decision):
    fm = _roadmap_front_matter()
    state = _read_json("project/docs/ai/handoff_state.json")
    assert fm["last_completed_research_action_id"] == (
        "stage128-m3i2-final-official-inquiry-human-submission")
    assert fm["next_research_action_id"] == (
        "stage128-m3i2-final-official-inquiry-response-ingestion")
    assert fm["next_research_action_authorized"] in (False, "false")
    assert fm["conditional_follow_up_action_id"] == (
        "stage128-m3i2-final-official-inquiry-one-follow-up")
    assert fm["conditional_follow_up_earliest_date"] == "2026-08-21"
    assert fm["conditional_follow_up_authorized"] in (False, "false")
    assert state["last_completed_research_action_id"] == (
        fm["last_completed_research_action_id"])
    assert state["next_research_action_id"] == fm["next_research_action_id"]
    assert state["next_research_action_id"] == (
        decision["next_research_action_id"])


def _roadmap_item(marker: str, stop: str) -> str:
    text = _read_text("project/docs/ai/ROADMAP.md")
    return text[text.index(marker):].split(stop, 1)[0]


def test_roadmap_item_25d_is_complete():
    item = _roadmap_item("25d. `stage128-m3i2-final-official-inquiry-human-"
                         "submission`", "\n25e.")
    assert "**COMPLETE" in item
    assert "POINTER ONLY" not in item
    assert "submitted **exactly once**" in item
    assert "NOT a substantive World Bank response" in item
    assert "No ticket id was supplied" in item
    assert "was never guessed" in item
    assert "raw confirmation is external only" in item
    assert "waiting period is ACTIVE" in item
    assert "follow_up_authorized_now: false" in item


def test_roadmap_item_25f_is_a_pointer_and_unauthorized():
    item = _roadmap_item("25f. `stage128-m3i2-final-official-inquiry-response-"
                         "ingestion`", "\n25g.")
    assert "POINTER ONLY; NOT AUTHORIZED" in item
    assert "substantive" in item
    assert "acknowledgement already received is **not** such a response" in item


def test_roadmap_item_25g_is_conditional_and_unauthorized():
    item = _roadmap_item("25g. `stage128-m3i2-final-official-inquiry-one-"
                         "follow-up`", "\n26.")
    assert "CONDITIONAL POINTER ONLY; NOT AUTHORIZED" in item
    assert "2026-08-21" in item
    assert "eligibility only" in item
    assert "ONE follow-up" in item


def test_open_tasks_shows_the_new_status_and_no_outstanding_submission():
    text = _read_text("project/docs/ai/OPEN_TASKS.md")
    assert _SUBMITTED_STATUS in text
    assert "no longer outstanding" in text
    assert "**Open item for the human supervisor.** Submit the prepared" \
        not in text


# --------------------------------------------------------------------------- #
# authorization + package integrity
# --------------------------------------------------------------------------- #

def test_the_authorization_is_recorded_exactly_and_consumed(authorization):
    text = authorization["authorization_text"]
    assert len(text.encode("utf-8")) == _AUTHORIZATION_UTF8_BYTES
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == (
        _AUTHORIZATION_SHA256)
    assert authorization["authorization_utf8_bytes"] == (
        _AUTHORIZATION_UTF8_BYTES)
    assert authorization["authorization_sha256"] == _AUTHORIZATION_SHA256
    assert authorization["scope_identified_by_hash_alone"] is False
    assert authorization["authorization_consumed_by_this_recording"] is True
    assert authorization["merge_authorized"] is False
    assert authorization["standing_authorization"] is False
    assert authorization["expected_baseline_sha"] == (
        "89d8e6ff2d12ec82903cd28aa7ab839eb946b658")
    for excluded in ("resubmission_of_the_inquiry", "reply_or_follow_up",
                     "gmail_or_personal_account_access", "data_gate",
                     "modeling", "merge"):
        assert excluded in authorization["authorization_excludes"]


def test_the_package_metadata_hashes_match_the_files_on_disk():
    meta_rel = (f"{_PKG_REL}/metadata_and_hashes_stage128_m3i2_final_official_"
                "inquiry_human_submission.json")
    meta = _read_json(meta_rel)
    recorded = meta["package_files"]
    on_disk = [p for p in _package_files()
               if os.path.basename(p) != os.path.basename(meta_rel)]
    assert sorted(recorded) == sorted(os.path.basename(p) for p in on_disk)
    for rel in on_disk:
        with open(os.path.join(REPO_ROOT, rel), "rb") as fh:
            blob = fh.read()
        entry = recorded[os.path.basename(rel)]
        assert entry["sha256"] == hashlib.sha256(blob).hexdigest(), rel
        assert entry["bytes"] == len(blob), rel
    with open(os.path.join(REPO_ROOT, _CANONICAL_REL), "rb") as fh:
        blob = fh.read()
    assert meta["canonical_submission_record"]["sha256"] == (
        hashlib.sha256(blob).hexdigest())
    assert meta["raw_screenshots_committed"] == 0
    assert meta["raw_emails_committed"] == 0
    assert meta["pii_committed_to_git"] is False


def test_the_qc_report_is_all_pass():
    qc = _read_json(f"{_PKG_REL}/stage128_m3i2_final_official_inquiry_"
                    "submission_qc_report.json")
    assert qc["all_pass"] is True
    assert qc["failed_count"] == 0
    assert qc["passed_count"] == qc["total_count"] == len(qc["checks"])
    assert all(c["status"] == "PASS" for c in qc["checks"])
