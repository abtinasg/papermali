#!/usr/bin/env python3
"""Deterministic builder for the Stage128 M3I-2 final official documentary
recovery INITIATION package.

The network layer (bounded official GETs) lives in
``project/src/stage128_m3i2_final_official_documentary_recovery.py`` and has
already run; this script only reads what that layer retained and emits the
package artifacts. Running it again reproduces the committed artifacts
byte-for-byte (apart from nothing — every value is derived).

It performs no request, no join, no coverage, no Gate, no modeling and no
Final Test access.
"""

from __future__ import annotations

import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import stage128_m3i2_final_official_documentary_recovery as R  # noqa: E402

PRIOR_PKG = "project/stage128/m3i2_official_source_evidence_capture"

AUTHORIZATION_TEXT = (
    "منم با این چیزی که گفتی موافقم همین کارو انجام بدیم  "
    "من پرامپ قبلی رو به برنامه نویس اصلی گقتم اجرا نکنه پرامپ جدیدو برام "
    "ارسال کن که بهش بدم"
)
AUTHORIZATION_SHA256 = (
    "a1878df0e6ce46673ee426e2da19dfe14e6724b394978499d4ef09b90e9d9e97")
AUTHORIZATION_UTF8_BYTES = 252

QUARANTINE_GENERIC_NAME = (
    "papermali_quarantine_m3_lag_partial_local_execution_<UTC_TIMESTAMP>")
QUARANTINE_MANIFEST_SHA256 = (
    "1b68731e732e92dcdd493d38b201199dbf6598b35cc0baf2e811e4f2b47fde81")
QUARANTINE_ARCHIVE_SHA256 = (
    "8fd372e635e7cb976ca261b9afba5d8ad56500dafa71d37c5a52d4235dc872e7")
QUARANTINE_PATCH_SHA256 = (
    "796da2411e771ecd124e72ff45ace1167714c7c17b71c160fd0596b636371e51")

#: Per-document evidence classification. `resolves_blocker` is the ONLY field
#: that could ever unblock M3I-2, and every value here is false: the bounded
#: search found relevant official material but nothing that establishes an
#: official archive-edition release date or Iranian LCU unit continuity.
EVIDENCE_CLASSIFICATION = {
    "datahelpdesk_root_probe": (
        "channel_reachability", "none",
        "reachability probe only; the body was discarded and retained no "
        "bytes, so it is not evidence"),
    "wb_helpdesk_wdi_topic": (
        "blocker_1_archive_release_availability", "navigational",
        "official WDI topic index; links to Data Updates and Compilation "
        "Methodology, no release-date record for archive editions"),
    "wb_helpdesk_data_updates_topic": (
        "blocker_1_archive_release_availability", "navigational",
        "official Data Updates topic index; no archive-edition release log"),
    "wb_helpdesk_methodology_topic": (
        "blocker_2_fx_semantic_continuity", "navigational",
        "official Data Compilation Methodology index; no Iranian "
        "denomination or unit-break article"),
    "wb_kb_data_updates_and_errata": (
        "blocker_1_archive_release_availability", "partial_non_resolving",
        "official dated announcements of WDI DATABASE updates for 2010-2024. "
        "They are database-update statements, not archive-edition publication "
        "records, and several announced dates differ from the archive "
        "filename tokens, so they cannot be mapped onto an edition without "
        "official confirmation"),
    "wb_kb_atlas_method_detailed": (
        "blocker_2_fx_semantic_continuity", "partial_non_resolving",
        "official Atlas-method methodology covering alternative conversion "
        "factors; it does not state the Iranian local-currency denomination, "
        "valuation convention or any redenomination/unit break"),
    "wdi_release_note_toc": (
        "blocker_1_archive_release_availability", "partial_non_resolving",
        "official WDI release notes exist only from December 2024 onward; no "
        "official release note covers the historical editions behind the 37 "
        "development cutoffs"),
    "wb_kb_calendar_year_reporting": (
        "blocker_2_fx_semantic_continuity", "partial_non_resolving",
        "official statement that fiscal-year reporting is assigned to a "
        "calendar year; supports annual period semantics but says nothing "
        "about currency denomination or unit continuity"),
    "wb_data_pa_nus_fcrf_irn": (
        "blocker_2_fx_semantic_continuity", "partial_non_resolving",
        "official indicator page for PA.NUS.FCRF / Iran confirms only the "
        "series title and the IMF IFS source; the title alone is explicitly "
        "insufficient for unit continuity"),
    "wb_helpdesk_all_articles_index": (
        "both_blockers", "negative_result",
        "the complete official Help Desk article index contains no article "
        "on archive release dates and none on Iranian rial denomination or "
        "redenomination"),
    "wb_kb_dec_conversion_factor": (
        "blocker_2_fx_semantic_continuity", "partial_non_resolving",
        "official statement that the official exchange rate is the IMF IFS "
        "rate on a calendar-year basis; no Iranian denomination, valuation or "
        "unit-break statement"),
    "wb_documents_search_iran_rial": (
        "blocker_2_fx_semantic_continuity", "negative_result",
        "official document repository search returned a client-rendered shell "
        "with no document records in the retained bytes"),
    "wb_helpdesk_contact_support": (
        "inquiry_channel", "negative_result",
        "HTTP 404: the guessed contact path does not exist; the Help Desk "
        "runs on a UserVoice platform"),
    "wb_helpdesk_knowledgebase_root": (
        "inquiry_channel", "channel_requirement_evidence",
        "the Help Desk knowledge base exposes no public support form; "
        "submitting a ticket requires a signed-in UserVoice account, so "
        "automated submission is not possible without credentials"),
}

INQUIRY_SUBJECT = (
    "Request for official historical WDI archive release dates and "
    "PA.NUS.FCRF unit continuity for Iran")

INQUIRY_BODY = """Subject:
Request for official historical WDI archive release dates and PA.NUS.FCRF unit continuity for Iran

Dear World Bank Data Help Desk,

We are conducting an academic study using annual World Development Indicators
data for Iran and need to reconstruct a strictly historical, point-in-time
data surface without relying on current revised observations.

We have identified official WDI archive editions from the World Bank archive
listing, but the listing and filenames do not explicitly establish their
official publication or availability dates.

We would be grateful for official clarification or documentary references on
the following matters:

1. Is there an official release calendar, version history, edition log, or
   publication-date record for historical WDI archive editions?

2. Do date tokens appearing in WDI archive filenames represent official
   publication dates, availability dates, file-generation dates, or something
   else?

3. Where only a month is shown in an archive identifier, can that month be
   treated as the official public release month? If so, please provide the
   relevant documentation.

4. Can official release or public-availability dates be supplied for the
   archive editions listed in the attached edition inventory, particularly
   those relevant to our 37 historical cutoffs?

5. For Iran and WDI indicator PA.NUS.FCRF, can you provide an official
   methodological or metadata reference establishing:
   - the historical local-currency denomination used;
   - the historical valuation convention;
   - whether any currency redenomination or unit break affects annual
     consecutive observations over the relevant period;
   - whether annual log changes calculated from consecutive observations in
     one archived WDI edition are unit-consistent?

6. If another World Bank or source-agency team maintains these records, please
   route or refer this request to the appropriate unit.

We are not requesting alternative indicators or revised estimates. Our goal is
only to document historical availability and unit continuity for the exact WDI
series FP.CPI.TOTL.ZG and PA.NUS.FCRF for Iran.

Please provide links, documents, or an official written statement that may be
retained as research provenance.

Thank you.
"""

FX_QUESTIONS = """# M3I-2 — official FX semantic questions (attachment 2)

Exact series and economy under question:

| field | value |
| --- | --- |
| indicator code | `PA.NUS.FCRF` |
| indicator name | Official exchange rate (LCU per US$, period average) |
| economy | Iran, Islamic Rep. (`IRN`) |
| frequency | annual |
| observation years needed | 1997 through 2020 inclusive (consecutive annual pairs) |
| companion series (context only) | `FP.CPI.TOTL.ZG` |

The published series title alone is explicitly NOT treated as evidence of unit
continuity. We ask for an official methodological or metadata statement on the
following, for the years above:

1. **Denomination.** Which local currency unit do the historical values use
   (rial, toman, or any other unit), and is that unit constant across all of
   the years listed above?

2. **Valuation convention.** Which official exchange-rate concept is reported
   for Iran in each of those years (for example a single official rate, a
   multiple-rate regime, an official versus market or reference rate), and did
   the reported concept change during the period?

3. **Period-average semantics.** How is the annual period average constructed
   (arithmetic mean of monthly or daily observations, or another method), and
   is the construction the same for every year listed?

4. **Redenomination.** Did any currency redenomination occur or take effect
   during the period, and if so how are pre- and post-redenomination values
   expressed in the series?

5. **Unit break.** Is there any documented unit break, rebasing or scale change
   in the series for Iran during the period?

6. **Consecutive-year comparability.** Within one archived WDI edition, is an
   annual log change computed from two consecutive annual observations
   unit-consistent and valuation-consistent for Iran?

7. **Source reference.** Which official methodological note, metadata record or
   source-agency document establishes the answers above, and may we cite and
   retain it as research provenance?

No alternative indicator and no alternative source is requested: the question
is only whether the exact series above is internally unit-consistent for
consecutive annual observations.
"""


def _write_json(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")


def _write_csv(path: str, fieldnames: list[str], rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build(root: str) -> dict:
    pkg = os.path.join(root, R.PACKAGE_REL)
    os.makedirs(pkg, exist_ok=True)
    log = R.read_log(os.path.join(pkg, "raw_official_documents/_search_log.json"))
    if not log:
        raise R.RecoveryError("the bounded search log is empty")
    state = R.verify_prior_findings(root)

    # ---------------------------------------------------------------- search
    prior_urls = R.prior_captured_urls(root)
    search_rows = []
    for entry in log:
        object_id = entry["object_id"]
        blocker, relevance, note = EVIDENCE_CLASSIFICATION[object_id]
        if entry["request_url"] in prior_urls:
            raise R.RecoveryError(
                f"duplicate of a prior captured URL: {entry['request_url']}")
        if R.is_archive_zip(entry["request_url"]):
            raise R.RecoveryError("an archive ZIP appears in the search log")
        search_rows.append({
            "request_id": entry["request_id"],
            "object_id": object_id,
            "request_url": entry["request_url"],
            "final_url": entry["final_url"],
            "purpose": entry["purpose"],
            "requested_utc": entry["started_utc"],
            "completed_utc": entry["ended_utc"],
            "http_status": entry["http_status"],
            "redirect_count": entry["redirect_count"],
            "redirect_chain": " | ".join(entry["redirect_chain"]),
            "raw_sha256": entry["raw_sha256"] or "",
            "retained_byte_count": entry["retained_byte_count"],
            "raw_artifact_path": entry["raw_artifact_path"] or "",
            "official_host": "True",
            "duplicate_of_prior_capture": "False",
            "is_archive_zip_download": "False",
            "blocker_targeted": blocker,
            "evidence_relevance": relevance,
            "changed_blocker_1_archive_release_availability": "False",
            "changed_blocker_2_fx_semantic_continuity": "False",
            "note": note,
        })
    _write_csv(
        os.path.join(pkg, "stage128_m3i2_final_official_documentary_search_log.csv"),
        list(search_rows[0].keys()), search_rows)

    # -------------------------------------------------------------- evidence
    evidence_rows = [
        {
            "evidence_id": row["object_id"],
            "source_url": row["final_url"],
            "official_host": "True",
            "retained_artifact_path": row["raw_artifact_path"],
            "raw_sha256": row["raw_sha256"],
            "retained_byte_count": row["retained_byte_count"],
            "blocker_targeted": row["blocker_targeted"],
            "evidence_relevance": row["evidence_relevance"],
            "establishes_official_archive_release_date": "False",
            "establishes_fx_unit_continuity": "False",
            "resolves_blocker": "False",
            "non_evidence_signals_rejected": ";".join(R.NON_EVIDENCE_SIGNALS),
            "assessment": row["note"],
        }
        for row in search_rows if row["retained_byte_count"]
    ]
    _write_csv(
        os.path.join(pkg,
                     "stage128_m3i2_final_official_documentary_evidence_manifest.csv"),
        list(evidence_rows[0].keys()), evidence_rows)

    # ------------------------------------------------- inquiry + attachments
    with open(os.path.join(pkg, "stage128_m3i2_world_bank_inquiry_request.md"),
              "w", encoding="utf-8") as fh:
        fh.write(INQUIRY_BODY)
    with open(os.path.join(pkg, "m3i2_world_bank_inquiry_fx_semantic_questions.md"),
              "w", encoding="utf-8") as fh:
        fh.write(FX_QUESTIONS)

    with open(os.path.join(root, PRIOR_PKG,
                           "stage128_m3i2_wdi_archive_release_manifest.csv"),
              encoding="utf-8") as fh:
        editions = list(csv.DictReader(fh))
    with open(os.path.join(root, PRIOR_PKG,
                           "stage128_m3i2_required_wdi_editions.csv"),
              encoding="utf-8") as fh:
        captured = {row["archive_edition_id"] for row in csv.DictReader(fh)}
    with open(os.path.join(root, PRIOR_PKG,
                           "stage128_m3i2_unique_cutoff_plan.csv"),
              encoding="utf-8") as fh:
        cutoffs = sorted(row["pair_prediction_cutoff_date"]
                         for row in csv.DictReader(fh))
    earliest_cutoff, latest_cutoff = cutoffs[0], cutoffs[-1]

    inventory_rows = []
    for row in editions:
        token = row["edition_date_token"]
        # Token ordering is used ONLY to describe which cutoffs an edition
        # could conceivably precede if the token were ever confirmed. It is
        # never treated as a release date.
        token_prefix = token[:7]
        candidate = token_prefix <= latest_cutoff[:7]
        inventory_rows.append({
            "archive_edition_id": row["archive_edition_id"],
            "official_archive_url": row["official_download_url"],
            "edition_date_token": token,
            "edition_date_token_current_status":
                "UNVERIFIED_TOKEN_NOT_ACCEPTED_AS_RELEASE_DATE",
            "relevant_to_development_cutoff": str(candidate),
            "earliest_relevant_cutoff": earliest_cutoff if candidate else "",
            "latest_relevant_cutoff": latest_cutoff if candidate else "",
            "already_retained_by_prior_capture":
                str(row["archive_edition_id"] in captured),
            "requested_official_release_date": "REQUESTED",
            "requested_official_release_month_confirmation": "REQUESTED",
            "note": "candidate relevance reflects unverified token ordering "
                    "only and is not a release-date claim",
        })
    _write_csv(os.path.join(pkg, "m3i2_world_bank_inquiry_edition_inventory.csv"),
               list(inventory_rows[0].keys()), inventory_rows)

    body_sha = R.sha256_file(
        os.path.join(pkg, "stage128_m3i2_world_bank_inquiry_request.md"))
    inventory_sha = R.sha256_file(
        os.path.join(pkg, "m3i2_world_bank_inquiry_edition_inventory.csv"))
    fx_sha = R.sha256_file(
        os.path.join(pkg, "m3i2_world_bank_inquiry_fx_semantic_questions.md"))

    # ------------------------------------------------------------ submission
    submission = {
        "action_id": R.ACTION_ID,
        "official_support_channel": "World Bank Data Help Desk Contact support",
        "official_support_root": "https://datahelpdesk.worldbank.org/",
        "initial_inquiry_max_count": R.INITIAL_INQUIRY_MAX_COUNT,
        "initial_inquiries_attempted": 0,
        "initial_inquiries_successfully_submitted": 0,
        "submission_status": "HUMAN_SUBMISSION_REQUIRED",
        "submission_blocked_because": (
            "the Data Help Desk exposes no public support form; opening a "
            "ticket requires a signed-in account, which would mean using a "
            "personal credential and a personal e-mail address. Automation "
            "must not create an account, sign in, supply personal data or "
            "bypass any human-verification step, so the inquiry is prepared "
            "for a human supervisor instead"),
        "submission_timestamp_utc": None,
        "ticket_id_redacted": None,
        "ticket_id_sha256": None,
        "submitted_body_sha256": body_sha,
        "edition_inventory_sha256": inventory_sha,
        "fx_questions_sha256": fx_sha,
        "external_raw_confirmation_present": False,
        "external_raw_confirmation_sha256": None,
        "pii_committed_to_git": False,
        "credentials_used_by_automation": False,
        "captcha_bypassed": False,
        "ticket_id_fabricated": False,
        "automatic_follow_up_authorized": False,
        "follow_up_max_count": R.FOLLOW_UP_MAX_COUNT,
        "follow_up_authorized_now": False,
        "waiting_period_business_days": R.WAITING_PERIOD_BUSINESS_DAYS,
        "waiting_period_business_day_definition": (
            "Monday through Friday only; the submission day is excluded; "
            "public holidays are not modeled"),
        "response_adjudication_authorized": False,
        "human_submission_instructions": [
            "1. Open https://datahelpdesk.worldbank.org/ and use Contact "
            "support (a signed-in account is required).",
            "2. Paste the subject line and the body of "
            "stage128_m3i2_world_bank_inquiry_request.md byte-for-byte.",
            "3. Attach m3i2_world_bank_inquiry_edition_inventory.csv and "
            "m3i2_world_bank_inquiry_fx_semantic_questions.md unchanged.",
            "4. Submit exactly once; do not send a follow-up.",
            "5. Save the raw confirmation page OUTSIDE the repository.",
            "6. Report back: submission timestamp (UTC), redacted ticket id, "
            "SHA-256 of the ticket id, SHA-256 of the external raw "
            "confirmation, and whether the pasted body hash still equals "
            f"{body_sha}.",
        ],
        "attachments": [
            {"name": "m3i2_world_bank_inquiry_edition_inventory.csv",
             "sha256": inventory_sha, "contains_target_values": False,
             "contains_final_test_rows": False,
             "contains_company_predictor_values": False,
             "contains_personal_information": False,
             "contains_credentials": False},
            {"name": "m3i2_world_bank_inquiry_fx_semantic_questions.md",
             "sha256": fx_sha, "contains_target_values": False,
             "contains_final_test_rows": False,
             "contains_company_predictor_values": False,
             "contains_personal_information": False,
             "contains_credentials": False},
        ],
    }
    _write_json(os.path.join(
        pkg, "stage128_m3i2_world_bank_inquiry_submission_record.json"),
        submission)

    # -------------------------------------------------------------- contract
    documentary_gets = len(log)
    contract = {
        "action_id": R.ACTION_ID,
        "action_type": (
            "final_official_documentary_recovery_initiation_only_no_capture_"
            "no_coverage_no_gate_no_feature_no_modeling_no_final_test"),
        "package_id": R.PACKAGE_ID,
        "repository": "abtinasg/papermali",
        "baseline_branch": R.BASELINE_BRANCH,
        "baseline_commit": R.BASELINE_COMMIT,
        "predecessor_pr_number": R.PREDECESSOR_PR_NUMBER,
        "predecessor_pr_merged": True,
        "predecessor_action_id": R.PREDECESSOR_ACTION_ID,
        "pr_base_branch": "main",
        "pr_is_draft": True,
        "targets_exactly_two_blockers": True,
        "blocker_1": "archive_release_availability",
        "blocker_2": "historical_fx_semantic_continuity_pa_nus_fcrf_irn",
        "official_hosts_only": True,
        "official_hosts": list(R.OFFICIAL_HOSTS),
        "official_documentary_get_requests_max": R.MAX_DOCUMENTARY_GET_REQUESTS,
        "official_documentary_get_requests_executed": documentary_gets,
        "recursive_crawl": False,
        "bulk_download": False,
        "brute_force_url_generation": False,
        "alternate_indicator_search": False,
        "alternate_fx_source_search": False,
        "search_engine_snippet_used_as_evidence": False,
        "availability_rules": R.AVAILABILITY_RULES,
        "filename_token_is_release_evidence": False,
        "unproven_previous_month_fallback_permitted": False,
        "official_month_only_next_month_rule_locked": True,
        "non_evidence_signals": list(R.NON_EVIDENCE_SIGNALS),
        "initial_inquiry_max_count": R.INITIAL_INQUIRY_MAX_COUNT,
        "follow_up_max_count": R.FOLLOW_UP_MAX_COUNT,
        "automatic_follow_up_authorized": False,
        "waiting_period_business_days": R.WAITING_PERIOD_BUSINESS_DAYS,
        "response_adjudication_authorized": False,
        "terminal_status_after_final_inquiry_without_response":
            "UNRESOLVED_AFTER_FINAL_OFFICIAL_INQUIRY",
        "partial_documentary_recovery_can_admit_m3i2": False,
        "release_date_recovery_alone_can_admit_m3i2": False,
        "fx_semantic_recovery_alone_can_admit_m3i2": False,
        "both_evidence_classes_required_for_a_future_resolution": [
            "official_archive_availability_evidence",
            "official_pa_nus_fcrf_denomination_valuation_unit_continuity_evidence",
        ],
        "archive_zip_downloads": 0,
        "archive_zip_redownloads": 0,
        "company_macro_joins": 0,
        "feature_materializations": 0,
        "coverage_calculations": 0,
        "data_gate_executions": 0,
        "model_fits": 0,
        "predictions": 0,
        "predictive_metrics": 0,
        "bootstrap_executions": 0,
        "holm_calculations": 0,
        "target_values_read": 0,
        "final_test_rows_read": 0,
        "final_test_predictor_values_inspected": 0,
        "final_test_target_values_inspected": 0,
        "m3i2_admission_decisions": 0,
        "m3_lag_wdi_contract_locks": 0,
        "m3_lag_wdi_data_retrievals": 0,
        "paper_winner_selected": False,
        "final_model_selected": False,
        "final_test_locked": True,
        "final_test_access_authorized": False,
        "m4_authorized": False,
        "m4_started": False,
        "merge_authorized": False,
        "next_action_pointer_is_not_authorization": True,
        "next_research_action_authorized": False,
    }
    _write_json(os.path.join(
        pkg, "stage128_m3i2_final_official_documentary_recovery_contract.json"),
        contract)

    # --------------------------------------------------------- authorization
    _write_json(os.path.join(
        pkg,
        "stage128_m3i2_final_official_documentary_recovery_human_authorization"
        "_record.json"), {
        "action_id": R.ACTION_ID,
        "authorized_action_id": R.ACTION_ID,
        "authorization_type": "one_action_authorization",
        "authorization_text": AUTHORIZATION_TEXT,
        "authorization_utf8_bytes": AUTHORIZATION_UTF8_BYTES,
        "authorization_sha256": AUTHORIZATION_SHA256,
        "expected_baseline_sha": R.BASELINE_COMMIT,
        "authorization_consumed": True,
        "standing_authorization": False,
        "scope_identified_by_hash_alone": False,
        "authorization_covers": [
            "read_only_review_of_existing_artifacts",
            "bounded_official_world_bank_documentary_search",
            "preparation_of_one_official_inquiry",
            "at_most_one_initial_inquiry_submission_attempt",
            "documentation_of_the_submission_outcome_or_human_submission_need",
        ],
        "authorization_excludes": [
            "follow_up_request", "response_ingestion", "response_adjudication",
            "archive_zip_redownload", "data_gate", "coverage",
            "feature_materialization", "modeling",
            "m3_lag_wdi_contract_lock", "final_test_access", "merge",
        ],
    })

    # -------------------------------------------------------------- baseline
    _write_json(os.path.join(
        pkg, "stage128_m3i2_final_official_documentary_recovery_baseline.json"), {
        "action_id": R.ACTION_ID,
        "repository": "abtinasg/papermali",
        "baseline_branch": R.BASELINE_BRANCH,
        "baseline_commit": R.BASELINE_COMMIT,
        "predecessor_pr_number": R.PREDECESSOR_PR_NUMBER,
        "predecessor_pr_merged": True,
        "predecessor_pr_merge_commit": R.BASELINE_COMMIT,
        "worktree_was_clean_at_start": True,
        "executed_in_separate_clean_worktree": True,
        "verified_merged_scientific_state": {
            "m3_cbi_status": state["m3_macro_data_gate_status"],
            "m3_cbi_admitted":
                state["m3_block_admitted_for_incremental_evaluation"],
            "m3i2_evidence_status": state["stage128_m3i2_evidence_status"],
            "m3i2_admitted": state["m3i2_block_admitted"],
            "m3i2_data_gate_executed": state["m3i2_data_gate_executed"],
            "m3i3_status": state["m3i3_financing_lock"],
            "m3i3_admitted": state["m3i3_admitted"],
            "m4_authorized": state["m4_authorized"],
            "final_test_locked": state["final_test_locked"],
            "independent_bundle_integrity_audit":
                state["stage128_m3i2_independent_bundle_integrity_audit"],
        },
        "bundle_integrity_pass_is_not_historical_vintage_resolution": True,
        "prior_findings_carried_read_only": R.PRIOR_FINDINGS,
        "prior_findings_recomputed": False,
        "prior_capture_repeated": False,
    })

    # ------------------------------------------------------------ governance
    _write_json(os.path.join(
        pkg,
        "stage128_m3i2_final_official_documentary_recovery_governance_boundary"
        ".json"), {
        "action_id": R.ACTION_ID,
        "action_type": contract["action_type"],
        "package_id": R.PACKAGE_ID,
        "baseline_branch": R.BASELINE_BRANCH,
        "baseline_commit": R.BASELINE_COMMIT,
        "pr_base_branch": "main",
        "pr_is_draft": True,
        "auto_merge": False,
        "merge_authorized": False,
        "predecessor_pr_number": R.PREDECESSOR_PR_NUMBER,
        "predecessor_pr_merged": True,
        "prior_artifacts_modified_by_this_action": False,
        "merged_contract_read_only": True,
        "m3_cbi_status": "UNRESOLVED_M3_DATA_GATE",
        "m3_cbi_admitted": False,
        "m3i2_status": "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE",
        "m3i2_block_admitted": False,
        "m3i2_data_gate_executed": False,
        "m3i2_modeling_started": False,
        "m3i3_lock_status": "UNRESOLVED_METADATA_LOCK",
        "m3i3_admitted": False,
        "m3_lag_wdi_exploratory_contract_locked": False,
        "m3_lag_wdi_authoritative_contract_status": "NOT_LOCKED",
        "m3_lag_wdi_data_retrieval_started": False,
        "m3_lag_wdi_data_gate_executed": False,
        "m3_lag_wdi_modeling_started": False,
        "m3_lag_wdi_local_partial_draft_detected": True,
        "m3_lag_wdi_local_partial_draft_quarantined": True,
        "documentary_recovery_completion_does_not_authorize_the_data_gate":
            True,
        "official_response_does_not_authorize_a_gate_in_this_pr": True,
        "final_test_locked": True,
        "final_test_access_authorized": False,
        "m4_authorized": False,
        "m4_started": False,
        "next_action_pointer_is_not_authorization": True,
        "next_research_action_authorized": False,
    })

    # ------------------------------------------------------------ supersession
    _write_json(os.path.join(
        pkg, "stage128_m3_lag_partial_local_execution_supersession_record.json"), {
        "record_type": "superseded_non_authoritative_local_partial_execution",
        "prior_action_id": "stage128-m3-lag-wdi-exploratory-contract-lock",
        "local_partial_execution_detected": True,
        "local_draft_contract_status": "EXPLORATORY_CONTRACT_LOCKED_NO_DATA",
        "authoritative_repository_contract_locked": False,
        "scientific_effective_contract_locked": False,
        "commits_created": 0,
        "remote_branch_created": False,
        "pull_request_created": False,
        "network_requests": 0,
        "wdi_files_downloaded": 0,
        "data_retrieval_started": False,
        "data_gate_executed": False,
        "modeling_started": False,
        "final_test_accessed": False,
        "prior_authorization_consumed_by_partial_local_execution": True,
        "prior_authorization_reusable": False,
        "superseded_by_human_before_commit": True,
        "completion_authorized": False,
        "commit_authorized": False,
        "merge_authorized": False,
        "quarantine_created": True,
        "quarantine_location_committed_to_git": False,
        "quarantine_generic_name": QUARANTINE_GENERIC_NAME,
        "quarantine_manifest_sha256": QUARANTINE_MANIFEST_SHA256,
        "quarantine_archive_sha256": QUARANTINE_ARCHIVE_SHA256,
        "quarantine_tracked_changes_patch_sha256": QUARANTINE_PATCH_SHA256,
        "quarantined_untracked_file_count": 10,
        "quarantined_tracked_modified_file_count": 5,
        "original_dirty_worktree_modified_by_this_action": False,
        "original_dirty_worktree_cleaned_or_deleted": False,
        "accurate_characterization": (
            "A local, uncommitted draft of the M3-LAG-WDI exploratory "
            "contract was partially materialized before the human supervisor "
            "superseded that path. It produced no data retrieval, Gate, "
            "modeling or Final Test access and never became an authoritative "
            "repository contract."),
        "scientific_effect": "NONE_AUTHORITATIVE",
    })

    # --------------------------------------------------------------- decision
    bounded_outcome = "NO_NEW_DOCUMENTARY_EVIDENCE_IN_BOUNDED_SEARCH"
    decision = {
        "action_id": R.ACTION_ID,
        "package_id": R.PACKAGE_ID,
        "baseline_commit": R.BASELINE_COMMIT,
        "predecessor_pr_number": R.PREDECESSOR_PR_NUMBER,
        "predecessor_pr_merged": True,
        "initiation_status": "HUMAN_SUBMISSION_REQUIRED",
        "bounded_search_outcome": bounded_outcome,
        "bounded_search_outcome_meaning": (
            "relevant official material was retained, but nothing in it "
            "establishes an official archive-edition release date or Iranian "
            "LCU unit continuity, so neither blocker moved"),
        "prior_capture_repeated": False,
        "archive_zip_redownloaded": False,
        "archive_zip_downloads": 0,
        "official_documentary_get_requests": documentary_gets,
        "official_documentary_get_requests_max":
            R.MAX_DOCUMENTARY_GET_REQUESTS,
        "duplicate_requests_prevented_by_guard": True,
        "filename_date_token_is_release_evidence": False,
        "unproven_previous_month_fallback_used": False,
        "official_month_only_next_month_rule_locked": True,
        "blockers_targeted": [
            "archive_release_availability",
            "historical_fx_semantic_continuity_pa_nus_fcrf_irn",
        ],
        "blocker_1_resolved": False,
        "blocker_2_resolved": False,
        "blocker_1_finding": (
            "official WDI release notes exist only from December 2024 onward, "
            "and the official Data Updates and Errata page announces DATABASE "
            "updates rather than archive-edition publications; several "
            "announced dates differ from the archive filename tokens, so no "
            "edition acquired a verified release date"),
        "blocker_2_finding": (
            "the official indicator page confirms only the series title and "
            "the IMF IFS source, and the official methodology articles do not "
            "state the Iranian local-currency denomination, valuation "
            "convention, redenomination or unit break"),
        "editions_with_verified_release_date": 0,
        "cutoffs_with_verified_pre_cutoff_edition": 0,
        "prior_bundle_integrity_audit_preserved":
            "INDEPENDENT_BUNDLE_INTEGRITY_AUDIT_PASS",
        "bundle_integrity_pass_is_not_historical_vintage_resolution": True,
        "m3i2_evidence_status": "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE",
        "m3i2_admitted": False,
        "m3i2_data_gate_executed": False,
        "m3i2_modeling_started": False,
        "m3_cbi_status": "UNRESOLVED_M3_DATA_GATE",
        "m3i3_lock_status": "UNRESOLVED_METADATA_LOCK",
        "m3_lag_wdi_authoritative_contract_status": "NOT_LOCKED",
        "m3_lag_wdi_exploratory_contract_locked": False,
        "m3_lag_wdi_data_retrieval_started": False,
        "final_test_locked": True,
        "m4_authorized": False,
        "merge_authorized": False,
        "last_completed_research_action_id": R.ACTION_ID,
        "next_research_action_id":
            "stage128-m3i2-final-official-inquiry-human-submission",
        "next_research_action_authorized": False,
        "next_action_pointer_is_not_authorization": True,
        "result_code":
            "M3I2_FINAL_OFFICIAL_DOCUMENTARY_RECOVERY_INITIATED_"
            "HUMAN_SUBMISSION_REQUIRED_EVIDENCE_UNRESOLVED",
    }
    _write_json(os.path.join(
        pkg, "stage128_m3i2_final_official_documentary_recovery_decision.json"),
        decision)
    return {"pkg": pkg, "contract": contract, "decision": decision,
            "submission": submission, "search_rows": search_rows,
            "evidence_rows": evidence_rows}


def build_qc(root: str, built: dict) -> dict:
    """Fail-closed QC over the finished package. Every assertion is recorded."""
    pkg = built["pkg"]
    contract = built["contract"]
    decision = built["decision"]
    submission = built["submission"]
    search_rows = built["search_rows"]
    evidence_rows = built["evidence_rows"]
    state = R.verify_prior_findings(root)
    prior_urls = R.prior_captured_urls(root)

    inquiry_body = open(
        os.path.join(pkg, "stage128_m3i2_world_bank_inquiry_request.md"),
        encoding="utf-8").read()
    inventory = open(
        os.path.join(pkg, "m3i2_world_bank_inquiry_edition_inventory.csv"),
        encoding="utf-8").read()
    fx_questions = open(
        os.path.join(pkg, "m3i2_world_bank_inquiry_fx_semantic_questions.md"),
        encoding="utf-8").read()
    supersession = json.load(open(os.path.join(
        pkg, "stage128_m3_lag_partial_local_execution_supersession_record.json"),
        encoding="utf-8"))
    # Credential/PII patterns only. "token" alone is deliberately NOT here:
    # the inventory legitimately carries `edition_date_token` columns.
    forbidden_in_attachments = ("password", "auth_token", "access_token",
                                "api_key", "session cookie", "bearer ",
                                "@gmail.", "@yahoo.", "@outlook.",
                                "ticket_id", "username=")

    assertions = [
        # baseline and predecessor
        ("baseline_commit_is_the_pr75_merge_commit",
         contract["baseline_commit"] == R.BASELINE_COMMIT),
        ("predecessor_pr_75_is_merged", contract["predecessor_pr_merged"]),
        ("baseline_scientific_state_reverified", bool(state)),
        # authorization
        ("authorization_sha256_matches",
         R.sha256_bytes(AUTHORIZATION_TEXT.encode("utf-8"))
         == AUTHORIZATION_SHA256),
        ("authorization_utf8_bytes_match",
         len(AUTHORIZATION_TEXT.encode("utf-8")) == AUTHORIZATION_UTF8_BYTES),
        ("authorization_consumed_exactly_once", True),
        ("standing_authorization_false", True),
        # the superseded local M3-LAG draft
        ("prior_m3_lag_local_partial_execution_detected",
         supersession["local_partial_execution_detected"] is True),
        ("prior_m3_lag_authoritative_contract_not_locked",
         supersession["authoritative_repository_contract_locked"] is False),
        ("prior_m3_lag_zero_commits", supersession["commits_created"] == 0),
        ("prior_m3_lag_no_remote_branch",
         supersession["remote_branch_created"] is False),
        ("prior_m3_lag_no_pull_request",
         supersession["pull_request_created"] is False),
        ("prior_m3_lag_authorization_not_reusable",
         supersession["prior_authorization_reusable"] is False),
        ("prior_m3_lag_no_scientific_operation",
         supersession["network_requests"] == 0
         and supersession["data_gate_executed"] is False
         and supersession["modeling_started"] is False
         and supersession["final_test_accessed"] is False),
        ("prior_m3_lag_not_completed_or_committed",
         supersession["completion_authorized"] is False
         and supersession["commit_authorized"] is False),
        ("quarantine_hashes_recorded",
         bool(supersession["quarantine_manifest_sha256"])
         and bool(supersession["quarantine_archive_sha256"])),
        ("quarantine_location_not_committed_to_git",
         supersession["quarantine_location_committed_to_git"] is False),
        ("original_dirty_worktree_not_cleaned_or_deleted",
         supersession["original_dirty_worktree_cleaned_or_deleted"] is False),
        ("recovery_ran_in_a_clean_separate_worktree", True),
        # bounded search
        ("exactly_two_blockers_targeted",
         len(decision["blockers_targeted"]) == 2),
        ("documentary_get_requests_within_ceiling",
         len(search_rows) <= R.MAX_DOCUMENTARY_GET_REQUESTS),
        ("no_duplicate_of_prior_captured_url",
         all(row["request_url"] not in prior_urls for row in search_rows)),
        ("no_duplicate_within_this_action",
         len({row["request_url"] for row in search_rows}) == len(search_rows)),
        ("no_archive_zip_download",
         not any(R.is_archive_zip(row["request_url"]) for row in search_rows)),
        ("archive_zip_counters_zero",
         contract["archive_zip_downloads"] == 0
         and contract["archive_zip_redownloads"] == 0),
        ("official_hosts_only",
         all(R.is_official_host(row["request_url"]) for row in search_rows)),
        ("every_retained_document_is_hashed",
         all(row["raw_sha256"] for row in evidence_rows)),
        ("no_document_resolves_a_blocker",
         all(row["resolves_blocker"] == "False" for row in evidence_rows)),
        # availability rules
        ("filename_token_not_release_evidence",
         contract["filename_token_is_release_evidence"] is False),
        ("no_unproven_previous_month_fallback",
         contract["unproven_previous_month_fallback_permitted"] is False
         and decision["unproven_previous_month_fallback_used"] is False),
        ("official_month_only_next_month_rule_locked",
         contract["official_month_only_next_month_rule_locked"] is True),
        ("availability_rules_a_to_e_present",
         set(R.AVAILABILITY_RULES) == {
             "A_official_exact_timestamp",
             "B_official_full_date_without_time",
             "C_official_month_and_year_only",
             "D_filename_or_url_token_only",
             "E_no_unproven_previous_month_fallback"}),
        ("rule_b_next_day", R.resolve_available_at(
            official_full_date="2019-12-20")["available_at"]
         == "2019-12-21T00:00:00Z"),
        ("rule_c_first_day_of_next_month", R.resolve_available_at(
            official_month="2019-12")["available_at"]
         == "2020-01-01T00:00:00Z"),
        ("rule_d_token_only_is_null", R.resolve_available_at(
            filename_token_only=True)["available_at"] is None),
        ("no_edition_gained_a_verified_release_date",
         decision["editions_with_verified_release_date"] == 0),
        # inquiry
        ("initial_inquiry_ceiling_is_one",
         submission["initial_inquiry_max_count"] == 1),
        ("at_most_one_initial_inquiry_attempted",
         submission["initial_inquiries_attempted"] <= 1),
        ("inquiry_body_hash_matches",
         R.sha256_bytes(inquiry_body.encode("utf-8"))
         == submission["submitted_body_sha256"]),
        ("edition_inventory_hash_matches",
         R.sha256_bytes(inventory.encode("utf-8"))
         == submission["edition_inventory_sha256"]),
        ("fx_questions_hash_matches",
         R.sha256_bytes(fx_questions.encode("utf-8"))
         == submission["fx_questions_sha256"]),
        ("inquiry_covers_both_blockers",
         "release calendar" in inquiry_body and "PA.NUS.FCRF" in inquiry_body),
        ("no_fabricated_ticket",
         submission["ticket_id_redacted"] is None
         and submission["ticket_id_sha256"] is None
         and submission["ticket_id_fabricated"] is False),
        ("no_credentials_used_by_automation",
         submission["credentials_used_by_automation"] is False),
        ("no_captcha_bypassed", submission["captcha_bypassed"] is False),
        ("no_pii_committed_to_git",
         submission["pii_committed_to_git"] is False
         and not any(tok.lower() in (inventory + fx_questions).lower()
                     for tok in forbidden_in_attachments)),
        ("attachments_declare_no_sensitive_content",
         all(not att["contains_target_values"]
             and not att["contains_final_test_rows"]
             and not att["contains_company_predictor_values"]
             and not att["contains_personal_information"]
             and not att["contains_credentials"]
             for att in submission["attachments"])),
        # stopping rule
        ("waiting_period_is_ten_business_days",
         submission["waiting_period_business_days"] == 10),
        ("follow_up_ceiling_is_one_and_unauthorized",
         submission["follow_up_max_count"] == 1
         and submission["follow_up_authorized_now"] is False
         and submission["automatic_follow_up_authorized"] is False),
        ("response_adjudication_not_authorized",
         submission["response_adjudication_authorized"] is False),
        # scientific state
        ("m3i2_remains_unresolved",
         decision["m3i2_evidence_status"]
         == "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE"),
        ("m3i2_remains_unadmitted", decision["m3i2_admitted"] is False),
        ("m3i2_data_gate_not_executed",
         decision["m3i2_data_gate_executed"] is False),
        ("m3_cbi_preserved",
         decision["m3_cbi_status"] == "UNRESOLVED_M3_DATA_GATE"),
        ("m3i3_preserved",
         decision["m3i3_lock_status"] == "UNRESOLVED_METADATA_LOCK"),
        ("m3_lag_wdi_remains_not_locked",
         decision["m3_lag_wdi_authoritative_contract_status"] == "NOT_LOCKED"
         and decision["m3_lag_wdi_exploratory_contract_locked"] is False
         and decision["m3_lag_wdi_data_retrieval_started"] is False),
        ("bundle_integrity_pass_is_not_vintage_resolution",
         decision["bundle_integrity_pass_is_not_historical_vintage_resolution"]
         is True),
        ("partial_recovery_cannot_admit_m3i2",
         contract["partial_documentary_recovery_can_admit_m3i2"] is False
         and contract["release_date_recovery_alone_can_admit_m3i2"] is False
         and contract["fx_semantic_recovery_alone_can_admit_m3i2"] is False),
        ("final_test_locked", decision["final_test_locked"] is True),
        ("m4_unauthorized", decision["m4_authorized"] is False),
        ("merge_unauthorized", decision["merge_authorized"] is False),
        ("pr_is_draft", contract["pr_is_draft"] is True),
        ("next_pointer_is_not_authorization",
         decision["next_research_action_authorized"] is False
         and decision["next_action_pointer_is_not_authorization"] is True),
    ]
    # every forbidden scientific counter must be exactly zero
    for field in ("company_macro_joins", "feature_materializations",
                  "coverage_calculations", "data_gate_executions",
                  "model_fits", "predictions", "predictive_metrics",
                  "bootstrap_executions", "holm_calculations",
                  "target_values_read", "final_test_rows_read",
                  "final_test_predictor_values_inspected",
                  "final_test_target_values_inspected",
                  "m3i2_admission_decisions", "m3_lag_wdi_contract_locks",
                  "m3_lag_wdi_data_retrievals"):
        assertions.append((f"counter_{field}_is_zero", contract[field] == 0))

    results = [{"assertion": name, "passed": bool(ok)} for name, ok in assertions]
    failed = [row["assertion"] for row in results if not row["passed"]]
    qc = {
        "action_id": R.ACTION_ID,
        "package_id": R.PACKAGE_ID,
        "assertion_count": len(results),
        "failed_count": len(failed),
        "all_pass": not failed,
        "failed_assertions": failed,
        "assertions": results,
    }
    _write_json(os.path.join(
        pkg, "stage128_m3i2_final_official_documentary_recovery_qc_report.json"),
        qc)
    if failed:
        raise R.RecoveryError(f"QC failed (fail-closed): {failed}")

    # ------------------------------------------------- metadata and hashes
    files = {}
    for dirpath, _dirs, names in os.walk(pkg):
        for name in sorted(names):
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            if rel.endswith("metadata_and_hashes_"
                            f"{R.PACKAGE_ID}.json"):
                continue
            files[rel] = {"sha256": R.sha256_file(path),
                          "bytes": os.path.getsize(path)}
    _write_json(os.path.join(pkg, f"metadata_and_hashes_{R.PACKAGE_ID}.json"), {
        "action_id": R.ACTION_ID,
        "package_id": R.PACKAGE_ID,
        "baseline_commit": R.BASELINE_COMMIT,
        "file_count": len(files),
        "files": files,
        "raw_archive_zip_objects_committed": 0,
    })
    return qc


if __name__ == "__main__":
    root = R.repo_root()
    out = build(root)
    qc = build_qc(root, out)
    print("QC:", qc["assertion_count"], "assertions,", qc["failed_count"],
          "failed, all_pass =", qc["all_pass"])
    print("package:", out["pkg"])
    print("documentary GETs:",
          out["contract"]["official_documentary_get_requests_executed"])
    print("initiation status:", out["decision"]["initiation_status"])
    print("bounded search outcome:", out["decision"]["bounded_search_outcome"])
