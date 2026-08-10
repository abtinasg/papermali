"""Stage129 M4 authoritative prerequisite resolution — locked-scope tests.

This action is DOCUMENTARY RESEARCH ONLY. These tests pin the zero-execution
boundaries, the unchanged scientific state, and the truthfulness of the three
recorded prerequisite verdicts. They read the package's own JSON directly.
"""
import hashlib
import json
import os

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PKG_REL = "project/stage129/m4_authoritative_prerequisite_resolution"
_PKG = os.path.join(REPO_ROOT, _PKG_REL)
_META_REL = os.path.join(
    _PKG_REL, "metadata_and_hashes_stage129_m4_authoritative_prerequisite_resolution.json"
)

ACTION_ID = "stage129-m4-authoritative-prerequisite-resolution"

PREREQUISITES = (
    "codal_to_parent_company_identity_resolution",
    "audit_opinion_type_taxonomy",
    "audit_lag_days_calendar_conversion",
)

ALLOWED_VERDICTS = {
    "RESOLVED_BY_AUTHORITATIVE_DETERMINISTIC_RULE",
    "RESOLVED_BY_AUTHORITATIVE_TAXONOMY",
    "RESOLVED_BY_AUTHORITATIVE_CALENDAR_RULE",
    "UNRESOLVED_NO_AUTHORITATIVE_DETERMINISTIC_RULE",
    "UNRESOLVED_NO_AUTHORITATIVE_TAXONOMY",
    "UNRESOLVED_NO_AUTHORITATIVE_CALENDAR_RULE",
    "BLOCKED_BY_ACCESS_OR_SOURCE_LIMITATION",
}

RESOLVED_VERDICTS = {v for v in ALLOWED_VERDICTS if v.startswith("RESOLVED_")}

ALLOWED_OVERALL = {
    "ALL_PREREQUISITES_AUTHORITATIVELY_RESOLVED",
    "PARTIAL_PREREQUISITE_RESOLUTION",
    "NO_PREREQUISITE_RESOLVED",
    "DOCUMENTARY_RESEARCH_BLOCKED",
}


def _load(name):
    with open(os.path.join(_PKG, name), encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def decision():
    return _load("stage129_m4_prerequisite_resolution_decision.json")


@pytest.fixture(scope="module")
def audit():
    return _load("stage129_m4_prerequisite_resolution_execution_audit.json")


@pytest.fixture(scope="module")
def boundary():
    return _load("stage129_m4_prerequisite_resolution_governance_boundary.json")


@pytest.fixture(scope="module")
def evidence():
    return _load("stage129_m4_prerequisite_resolution_source_evidence.json")


# --------------------------------------------------------------------------- #
# Package integrity
# --------------------------------------------------------------------------- #

def test_package_files_exist():
    for name in (
        "README_STAGE129_M4_AUTHORITATIVE_PREREQUISITE_RESOLUTION.md",
        "stage129_m4_prerequisite_resolution_decision.json",
        "stage129_m4_prerequisite_resolution_source_evidence.json",
        "stage129_m4_prerequisite_resolution_execution_audit.json",
        "stage129_m4_prerequisite_resolution_governance_boundary.json",
    ):
        assert os.path.isfile(os.path.join(_PKG, name)), name


def test_hash_manifest_matches_every_committed_package_file():
    meta_path = os.path.join(REPO_ROOT, _META_REL)
    with open(meta_path, encoding="utf-8") as fh:
        meta = json.load(fh)
    listed = meta["package_files"]
    on_disk = {n for n in os.listdir(_PKG) if n != os.path.basename(_META_REL)}
    assert set(listed) == on_disk
    for name, entry in listed.items():
        raw = open(os.path.join(_PKG, name), "rb").read()
        assert len(raw) == entry["bytes"], name
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"], name


def test_manifest_declares_no_m4_values_or_secrets():
    with open(os.path.join(REPO_ROOT, _META_REL), encoding="utf-8") as fh:
        meta = json.load(fh)
    assert meta["action_id"] == ACTION_ID
    assert meta["m4_value_files_committed"] == 0
    assert meta["credentials_committed_to_git"] is False
    assert meta["pii_committed_to_git"] is False


def test_all_artifacts_declare_the_same_action_id(decision, audit, boundary, evidence):
    for doc in (decision, audit, boundary, evidence):
        assert doc["action_id"] == ACTION_ID


# --------------------------------------------------------------------------- #
# Verdict structure and honesty
# --------------------------------------------------------------------------- #

def test_exactly_the_three_frozen_prerequisites_are_reported(decision):
    assert set(decision["prerequisites"]) == set(PREREQUISITES)


def test_each_prerequisite_has_an_allowed_verdict(decision):
    for name in PREREQUISITES:
        assert decision["prerequisites"][name]["verdict"] in ALLOWED_VERDICTS


def test_overall_outcome_is_allowed(decision):
    assert decision["overall_outcome"] in ALLOWED_OVERALL


def test_overall_outcome_is_consistent_with_individual_verdicts(decision):
    """The headline outcome may never overstate what the verdicts support."""
    verdicts = [decision["prerequisites"][n]["verdict"] for n in PREREQUISITES]
    resolved = [v for v in verdicts if v in RESOLVED_VERDICTS]
    overall = decision["overall_outcome"]
    if overall == "ALL_PREREQUISITES_AUTHORITATIVELY_RESOLVED":
        assert len(resolved) == len(PREREQUISITES)
    elif overall == "PARTIAL_PREREQUISITE_RESOLUTION":
        assert 0 < len(resolved) < len(PREREQUISITES)
    else:
        assert len(resolved) == 0


def test_issues_resolved_list_matches_the_verdicts(decision):
    resolved_names = {
        n for n in PREREQUISITES
        if decision["prerequisites"][n]["verdict"] in RESOLVED_VERDICTS
    }
    assert set(decision["post_action_contract_state"]["issues_resolved_by_this_action"]) == resolved_names


def test_unresolved_issue_list_still_carries_every_unresolved_prerequisite(decision):
    unresolved = {
        n for n in PREREQUISITES
        if decision["prerequisites"][n]["verdict"] not in RESOLVED_VERDICTS
    }
    recorded = set(decision["post_action_contract_state"]["contract_issues_unresolved"])
    assert unresolved <= recorded


# --------------------------------------------------------------------------- #
# Fail-closed: research must never unlock execution
# --------------------------------------------------------------------------- #

def test_gate_stays_non_executable_while_any_prerequisite_is_unresolved(decision):
    state = decision["post_action_contract_state"]
    if state["contract_issues_unresolved"]:
        assert state["m4_data_gate_executable"] is False
        assert state["m4_data_gate_authorized"] is False
        assert state["m4_contract_complete"] is False
        assert state["m4_contract_fully_executable"] is False
        assert state["m4_candidates_the_gate_may_execute_for"] == []


def test_pointer_is_never_an_authorization(decision, boundary):
    state = decision["post_action_contract_state"]
    assert state["next_action_authorized"] is False
    assert state["pointer_is_not_authorization"] is True
    assert boundary["next_action_authorized"] is False
    assert boundary["pointer_is_not_authorization"] is True
    assert boundary["research_outcome_does_not_unlock_execution"] is True


def test_this_action_does_not_authorize_downstream_work(decision):
    assert decision["authorizes_retrieval"] is False
    assert decision["authorizes_gate_execution"] is False
    assert decision["authorizes_modeling"] is False
    assert decision["is_the_gate_itself"] is False


# --------------------------------------------------------------------------- #
# Zero-execution boundaries
# --------------------------------------------------------------------------- #

def test_zero_m4_observations_and_zero_scientific_execution(audit):
    c = audit["counters"]
    for key in (
        "codal_requests_succeeded",
        "codal_filings_retrieved",
        "m4_candidate_observations_read",
        "company_rows_loaded",
        "candidate_columns_materialized",
        "audit_opinion_values_read",
        "going_concern_values_read",
        "audit_report_dates_read",
        "board_size_values_read",
        "final_test_rows_loaded",
        "coverage_calculations",
        "gate_executions",
        "model_fits",
        "predictions",
        "predictive_metrics",
        "holm_calculations",
        "bootstrap_executions",
    ):
        assert c[key] == 0, key
    assert audit["retrieval_started"] is False
    assert audit["data_gate_executed"] is False
    assert audit["block_admitted"] is False
    assert audit["modeling_started"] is False
    assert audit["incremental_evaluation_performed"] is False
    assert audit["final_test_rows_read"] == 0
    assert audit["scientific_computation_ran"] is False


def test_network_access_is_documented_as_documentary_only(audit):
    assert audit["network_access_scope"] == "documentary_only"
    docs = audit["documents_downloaded_and_hashed_not_repository_retained"]
    assert docs
    for doc in docs:
        assert doc["contains_company_level_data"] is False


# --------------------------------------------------------------------------- #
# Documentary custody honesty
# --------------------------------------------------------------------------- #

def test_repository_custody_count_matches_actual_committed_objects(audit):
    """Nothing may be described as repository-retained unless custody exists.

    This package commits no documentary object, so the custody count must be 0
    and every downloaded document must be flagged as NOT in repository custody.
    """
    assert audit["counters"]["documentary_documents_in_repository_custody"] == 0
    assert audit["counters"]["documentary_documents_downloaded_and_hashed_not_in_repository_custody"] >= 1
    assert audit["repository_custody_note"]
    for doc in audit["documents_downloaded_and_hashed_not_repository_retained"]:
        assert doc["in_repository_custody"] is False
        assert doc["hash_is_of_a_committed_file"] is False
        assert doc["custody_status"].startswith("downloaded_and_locally_hashed")
        assert doc["not_committed_reason"]
        assert doc["independent_reproduction_requires"]


def test_no_audit_key_claims_repository_retention(audit):
    """The legacy 'documents_retained' / 'documentary_documents_retained' keys
    must not reappear: they read as repository-preserved evidence."""
    assert "documents_retained" not in audit
    assert "documentary_documents_retained" not in audit


def test_observed_hashes_are_never_presented_as_committed_custody(evidence):
    summary = evidence["repository_custody_summary"]
    assert summary["documentary_objects_committed_to_this_repository"] == 0
    assert summary["every_recorded_hash_is_historical_execution_metadata"] is True
    assert summary["no_recorded_hash_can_be_verified_against_a_committed_file"] is True
    assert summary["independent_byte_level_reproduction_requires"]


def test_hash_bearing_sources_declare_no_repository_custody(evidence):
    for src in evidence["sources"]:
        if src.get("observed_sha256"):
            assert src["in_repository_custody"] is False
            assert src["hash_is_of_a_committed_file"] is False
            assert src["hash_and_byte_count_are_historical_execution_metadata"] is True
            assert src["not_committed_reason"]


def test_package_manifest_only_covers_this_packages_own_artifacts():
    """The hash manifest must never appear to give custody of a third-party
    document: every entry it lists must exist inside the package directory."""
    with open(os.path.join(REPO_ROOT, _META_REL), encoding="utf-8") as fh:
        meta = json.load(fh)
    for name in meta["package_files"]:
        assert os.path.isfile(os.path.join(_PKG, name)), name
        assert not name.lower().endswith(".pdf"), name


def test_uncaptured_metadata_is_null_with_a_capture_note(evidence):
    """Metadata not captured during the original session must be recorded as
    null WITH an explanation - never estimated, reconstructed or fabricated."""
    for src in evidence["sources"]:
        for field in ("bytes", "sha256", "media_type", "http_status"):
            if field in src and src[field] is None:
                note = src.get(f"{field}_capture_note")
                curl = src.get("curl_exit_condition")
                assert note or curl, f"{src['id']}.{field} is null with no explanation"


def test_every_source_declares_an_access_class(evidence):
    allowed = set(evidence["access_class_definitions"])
    for src in evidence["sources"]:
        assert src["access_class"] in allowed, src["id"]


def test_no_source_claims_retention_in_this_repository(evidence):
    reached_and_retained = [
        s for s in evidence["sources"]
        if s.get("access_class") == "reached_content_received_and_retained_in_repository"
    ]
    assert reached_and_retained == []


def test_no_empirical_or_outcome_informed_discovery(audit):
    assert audit["empirical_or_outcome_informed_discovery_performed"] is False
    assert audit["fuzzy_or_name_matching_performed"] is False
    assert audit["taxonomy_inferred_from_observed_frequencies"] is False
    assert audit["calendar_rule_inferred_from_observed_dates"] is False


def test_final_test_and_paper_level_boundaries_untouched(boundary):
    assert boundary["final_test_locked"] is True
    assert boundary["final_test_access_authorized"] is False
    assert boundary["final_test_rows_read"] == 0
    assert boundary["paper_winner_selected"] is False
    assert boundary["final_model_selected"] is False
    assert boundary["full_development_refit_performed"] is False
    assert boundary["stage130_or_later_started"] is False


def test_comparator_and_holm_boundaries_unchanged(boundary):
    assert boundary["m3_cbi_status"] == "UNRESOLVED_M3_DATA_GATE"
    assert boundary["m3_lag_wdi_disposition"] == "SUPPLEMENTARY_EXPLORATORY_ONLY"
    assert boundary["m3_lag_wdi_described_as_confirmatory"] is False
    assert boundary["confirmatory_holm_family_modified_by_this_action"] is False
    assert boundary["confirmatory_holm_family_executed"] is False
    assert boundary["gate_pass_described_as_modeling_authorization"] is False


def test_forbidden_calendar_shortcut_stays_forbidden(decision, boundary):
    cal = decision["prerequisites"]["audit_lag_days_calendar_conversion"]
    assert cal["jalali_fiscal_year_t_plus_621_permitted_as_daily_date_conversion"] is False
    assert boundary["jalali_fiscal_year_t_plus_621_permitted_as_daily_date_conversion"] is False


# --------------------------------------------------------------------------- #
# Frozen candidate scope
# --------------------------------------------------------------------------- #

def test_candidate_identity_set_is_unchanged(decision, boundary):
    assert decision["candidate_set"] == [
        "audit_opinion_type",
        "going_concern_flag",
        "audit_lag_days",
        "board_size",
    ]
    assert decision["candidate_set_unchanged"] is True
    assert decision["candidate_identity_added_removed_or_renamed_by_this_action"] is False
    assert boundary["candidate_count"] == 4
    assert boundary["candidate_substituted_by_this_action"] is False
    assert boundary["candidate_count_can_change_without_new_human_authorization"] is False


def test_thresholds_and_holm_family_untouched(decision, boundary):
    assert decision["thresholds_changed_by_this_action"] is False
    assert decision["confirmatory_holm_family_changed_by_this_action"] is False
    assert boundary["thresholds_modified_by_this_action"] is False


def test_candidate_set_matches_the_locked_stage129_contract():
    contract = os.path.join(
        REPO_ROOT,
        "project/stage129/m4_governance_data_gate_contract/stage129_m4_data_gate_contract.json",
    )
    with open(contract, encoding="utf-8") as fh:
        locked = json.load(fh)
    decision_doc = _load("stage129_m4_prerequisite_resolution_decision.json")
    assert set(decision_doc["candidate_set"]) == set(locked["semantic_definitions"])


# --------------------------------------------------------------------------- #
# Evidence honesty
# --------------------------------------------------------------------------- #

def test_every_source_records_what_it_does_not_establish(evidence):
    assert evidence["sources"]
    for src in evidence["sources"]:
        assert "establishes" in src, src.get("id")
        assert "does_not_establish" in src, src.get("id")


def test_unreached_sources_claim_nothing(evidence):
    for src in evidence["sources"]:
        reached = src.get("http_status") == 200
        if not reached and src.get("bytes") == 0:
            assert src["establishes"] == "nothing - not reached", src.get("id")


def test_observed_document_hash_is_recorded_and_well_formed(evidence):
    """A document whose bytes were obtained must carry a well-formed observed
    hash and byte count, explicitly marked as historical execution metadata
    rather than committed repository custody."""
    hashed = [s for s in evidence["sources"] if s.get("observed_sha256")]
    assert hashed, "at least one downloaded documentary artifact must carry an observed SHA-256"
    for src in hashed:
        assert len(src["observed_sha256"]) == 64
        assert src["observed_bytes"] > 0
        assert src["hash_and_byte_count_are_historical_execution_metadata"] is True
        assert src["in_repository_custody"] is False
        assert "sha256" not in src, (
            f"{src['id']}: bare 'sha256' reads as committed custody; use 'observed_sha256'"
        )


def test_absence_of_evidence_is_not_claimed_as_absence(evidence):
    assert evidence["explicit_non_claims"]
    joined = " ".join(evidence["explicit_non_claims"]).lower()
    assert "not evidence of absence" in joined


def test_non_authoritative_sources_are_labelled_as_such(evidence):
    """A library or secondary reference may never be labelled authoritative."""
    for src in evidence["sources"]:
        cls = src.get("evidence_class", "")
        if src.get("id") == "src_jdatetime_pinned_library":
            assert cls == "implementation_artifact_not_authoritative_source"
        if src.get("id") == "src_solar_hijri_calendar_nature":
            assert cls == "secondary_supporting_not_authoritative"


def test_calendar_claim_is_qualified_not_presented_as_authoritative(evidence, decision):
    """The calendar characterisation rests on secondary evidence, so it must
    carry its own limits and must not read as a resolved authoritative rule."""
    src = next(s for s in evidence["sources"] if s["id"] == "src_solar_hijri_calendar_nature")
    assert src["is_official_iranian_primary_source"] is False
    assert src["supported_proposition_exactly"]
    assert src["inference_limits"]

    finding = decision["prerequisites"]["audit_lag_days_calendar_conversion"]["substantive_secondary_finding"]
    assert finding["evidence_class_for_this_finding"] == "secondary_supporting_not_authoritative"
    assert finding["is_official_iranian_primary_source"] is False
    assert finding["inference_limits"]
    assert finding["library_authority_is_adequate"] is False


def test_calendar_core_conclusion_is_preserved(decision):
    """Qualifying the wording must not weaken the operative conclusion."""
    cal = decision["prerequisites"]["audit_lag_days_calendar_conversion"]
    finding = cal["substantive_secondary_finding"]
    assert "internal invertibility" in finding["roundtrip_check_interpretation"].lower()
    assert cal["deterministic_implementation_may_be_frozen_now"] is False
    assert cal["verdict"] == "BLOCKED_BY_ACCESS_OR_SOURCE_LIMITATION"


def test_access_failure_is_never_recorded_as_documentary_absence(evidence, decision):
    unreachable = [
        s for s in evidence["sources"]
        if s.get("access_class") == "connection_failed_zero_content"
    ]
    assert unreachable
    for src in unreachable:
        assert src["establishes"] == "nothing - not reached"
        assert src.get("authoritative_but_inaccessible") is True
        text = json.dumps(src["does_not_establish"]).lower()
        assert "does not establish" in text
    identity = decision["prerequisites"]["codal_to_parent_company_identity_resolution"]
    assert identity["absence_of_evidence_is_not_evidence_of_absence"] is True


def test_no_new_network_access_during_the_custody_correction(decision):
    assert decision["documentary_custody"]["no_source_was_contacted_again_during_the_custody_correction"] is True


def test_all_three_verdicts_remain_blocked(decision):
    for name in PREREQUISITES:
        assert decision["prerequisites"][name]["verdict"] == "BLOCKED_BY_ACCESS_OR_SOURCE_LIMITATION"
    assert decision["overall_outcome"] == "DOCUMENTARY_RESEARCH_BLOCKED"
