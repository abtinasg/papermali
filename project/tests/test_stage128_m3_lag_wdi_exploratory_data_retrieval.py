"""Stage128 — Track B step B: the M3-LAG-WDI exploratory DATA RETRIEVAL.

These tests police one narrow claim: the two locked WDI series were ACQUIRED,
and *nothing else happened*. Acquisition is not admission.

The structural tests matter most. The retrieval layer cannot build a URL for a
third indicator, for a forbidden substitute, for another country, for a
non-official host or for plain HTTP — not "does not", *cannot*: there is no
code path. The rest are fail-closed drift tests proving both recognizers refuse
the moment a counter moves, a payload is claimed parsed, the Gate is claimed
executed, or step C/D/E is claimed authorized.

No test here opens a socket. The one module that can is imported only to assert
what it REFUSES, and its refusals are checked before any network call exists.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "project", "scripts"))
sys.path.insert(0, os.path.join(REPO_ROOT, "project"))

import update_ai_handoff as gen  # noqa: E402
from src import stage126_current_state_validator as v  # noqa: E402
from src import stage128_m3_lag_wdi_exploratory_data_retrieval as r  # noqa: E402
from src import stage128_m3_lag_wdi_retrieval_capture_layer as cap  # noqa: E402

_PKG_REL = "project/stage128/m3_lag_wdi_exploratory_data_retrieval"
_MANIFEST_REL = f"{_PKG_REL}/stage128_m3_lag_wdi_retrieval_source_manifest.json"
_AUDIT_REL = f"{_PKG_REL}/stage128_m3_lag_wdi_retrieval_execution_audit.json"
_BOUNDARY_REL = (
    f"{_PKG_REL}/stage128_m3_lag_wdi_retrieval_governance_boundary.json")
_AUTH_REL = (
    f"{_PKG_REL}/stage128_m3_lag_wdi_retrieval_human_authorization_record.json")
_DECISION_REL = f"{_PKG_REL}/stage128_m3_lag_wdi_retrieval_decision.json"
_TOPOLOGY_REL = f"{_PKG_REL}/stage128_m3_lag_wdi_retrieval_pr_topology.json"
_QC_REL = f"{_PKG_REL}/stage128_m3_lag_wdi_retrieval_qc_report.json"
_META_REL = (
    f"{_PKG_REL}/metadata_and_hashes_stage128_m3_lag_wdi_exploratory_data_"
    "retrieval.json")
_README_REL = (
    f"{_PKG_REL}/README_STAGE128_M3_LAG_WDI_EXPLORATORY_DATA_RETRIEVAL.md")

_ALL_RELS = (_MANIFEST_REL, _AUDIT_REL, _BOUNDARY_REL, _AUTH_REL,
             _DECISION_REL, _TOPOLOGY_REL, _QC_REL)

_ACTION_ID = "stage128-m3-lag-wdi-exploratory-data-retrieval"
_SCOPE = "retrieval_only"
_AUTH_SHA256 = (
    "b409e0a53d255955199c59005d39f911ae272713dbf85c38651cd0dcfd5ba604")
_AUTH_BYTES = 125
_LOCK_AUTH_SHA256 = (
    "0c1e10496bfba98d5ae4a6a3a8bf593a42258388fce1003c4cc36e6cdee4995b")
_CPI = "FP.CPI.TOTL.ZG"
_FX = "PA.NUS.FCRF"
_AUDIT_ACTION = "stage128-m3-lag-wdi-exploratory-post-retrieval-audit"
_GATE_ACTION = "stage128-m3-lag-wdi-exploratory-data-gate"
_NO_NEXT_ACTION = "human_decision_required"
_MODEL_ACTION = "stage128-m3-lag-wdi-exploratory-incremental-evaluation"


def _read_json(rel: str) -> dict:
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def manifest() -> dict:
    return _read_json(_MANIFEST_REL)


@pytest.fixture(scope="module")
def audit() -> dict:
    return _read_json(_AUDIT_REL)


@pytest.fixture(scope="module")
def boundary() -> dict:
    return _read_json(_BOUNDARY_REL)


@pytest.fixture(scope="module")
def handoff() -> dict:
    return _read_json("project/docs/ai/handoff_state.json")


# --------------------------------------------------------------------------- #
# STRUCTURAL: only the two locked indicators, only IRN, only the official API
# --------------------------------------------------------------------------- #

def test_only_the_two_locked_indicators_can_be_addressed():
    assert cap.LOCKED_INDICATOR_CODES == (_CPI, _FX)
    assert cap.LOCKED_COUNTRY_CODE == "IRN"
    for code in cap.LOCKED_INDICATOR_CODES:
        url = cap.build_target_url(code, "IRN")
        assert url.startswith("https://api.worldbank.org/v2/country/IRN/")
        assert code in url


@pytest.mark.parametrize("code", [
    "PA.NUS.ATLS",          # the explicitly forbidden FX substitute
    "FP.CPI.TOTL",          # index-level CPI instead of the annual % series
    "NY.GDP.DEFL.KD.ZG",    # GDP-deflator inflation
    "FR.INR.LEND",          # a financing-rate series
    "SP.POP.TOTL",          # any unrelated third indicator
    "",
])
def test_no_alternative_indicator_can_be_requested(code):
    with pytest.raises(cap.RetrievalCaptureError):
        cap.build_target_url(code, "IRN")


@pytest.mark.parametrize("country", ["TUR", "IRQ", "USA", "irn", ""])
def test_no_other_country_can_be_requested(country):
    with pytest.raises(cap.RetrievalCaptureError):
        cap.build_target_url(_CPI, country)


@pytest.mark.parametrize("url", [
    "http://api.worldbank.org/v2/country/IRN/indicator/FP.CPI.TOTL.ZG",
    "https://example.com/v2/country/IRN/indicator/FP.CPI.TOTL.ZG",
    "https://api.worldbank.org.evil.test/v2/country/IRN/indicator/"
    "FP.CPI.TOTL.ZG",
    "https://api.worldbank.org/v2/country/IRN/indicator/PA.NUS.ATLS",
    "https://api.worldbank.org/v2/country/TUR/indicator/FP.CPI.TOTL.ZG",
    "https://api.worldbank.org/v2/sources",
])
def test_non_official_or_out_of_scope_urls_are_refused(url):
    assert cap.is_official_wdi_url(url) is False
    with pytest.raises(cap.RetrievalCaptureError):
        cap.assert_official_wdi_url(url)


def test_the_forbidden_substitutions_are_named_and_unreachable():
    for code in cap.FORBIDDEN_SUBSTITUTIONS:
        assert code not in cap.LOCKED_INDICATOR_CODES
        with pytest.raises(cap.RetrievalCaptureError):
            cap.build_target_url(code, "IRN")


# --------------------------------------------------------------------------- #
# The NEW authorization is single-use and distinct from the lock's
# --------------------------------------------------------------------------- #

def test_the_authorization_digest_is_recomputable_from_its_own_text():
    record = _read_json(_AUTH_REL)
    text = record["authorization_text"]
    assert len(text.encode("utf-8")) == _AUTH_BYTES
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == _AUTH_SHA256
    assert record["authorization_sha256"] == _AUTH_SHA256
    assert record["authorization_utf8_bytes"] == _AUTH_BYTES
    assert not text.endswith("\n")


def test_the_authorization_names_this_action_and_this_scope():
    record = _read_json(_AUTH_REL)
    assert _ACTION_ID in record["authorization_text"]
    assert _SCOPE in record["authorization_text"]
    assert record["authorization_scope"] == _SCOPE
    assert record["scope_identified_by_hash_alone"] is False


def test_the_retrieval_authorization_is_not_the_contract_lock_one():
    record = _read_json(_AUTH_REL)
    assert record["authorization_sha256"] != _LOCK_AUTH_SHA256
    assert record["prior_contract_lock_authorization_sha256"] == (
        _LOCK_AUTH_SHA256)
    assert record["prior_contract_lock_authorization_reused"] is False
    assert "HISTORICAL" in record["prior_contract_lock_authorization_status"]


def test_the_authorization_is_single_use_and_reaches_no_later_step():
    record = _read_json(_AUTH_REL)
    assert record["authorization_consumed"] is True
    assert record["standing_authorization"] is False
    for field in ("authorization_is_reusable_for_post_retrieval_audit",
                  "authorization_is_reusable_for_data_gate",
                  "authorization_is_reusable_for_modeling"):
        assert record[field] is False, field
    for excluded in ("post_retrieval_audit", "coverage_calculation",
                     "data_gate_execution", "data_admission",
                     "modeling_or_predictive_evaluation", "final_test_access"):
        assert excluded in record["authorization_excludes"]


# --------------------------------------------------------------------------- #
# What was retrieved — and what was not touched
# --------------------------------------------------------------------------- #

def test_exactly_the_two_locked_indicators_for_irn_were_retrieved(manifest):
    codes = [e["indicator_code"] for e in manifest["indicators"]]
    assert codes == [_CPI, _FX]
    assert manifest["indicator_count"] == 2
    for entry in manifest["indicators"]:
        assert entry["country_code"] == "IRN"
        assert entry["request_url"].startswith(
            "https://api.worldbank.org/v2/country/IRN/")
        assert entry["retrieval_result"] == "SUCCESS"
        assert entry["http_status_code"] == 200
        assert entry["raw_artifact_bytes"] > 0
        assert len(entry["raw_artifact_sha256"]) == 64


def test_the_payload_was_never_parsed_and_no_value_was_read(manifest, audit):
    assert audit["payload_json_decoded"] is False
    assert audit["wdi_observations_read"] == 0
    assert audit["wdi_value_inspections"] == 0
    for entry in manifest["indicators"]:
        assert entry["payload_parsed"] is False
        # unresolved stays null, never 0 — 0 would be a claim
        assert entry["observations_read"] is None
        assert entry["values_inspected"] is None
        assert entry["coverage_calculated"] is None


def test_no_coverage_no_gate_no_admission_no_join_no_model(audit):
    for field in ("coverage_calculations", "candidate_coverage_evaluations",
                  "block_coverage_evaluations", "positives_per_window_counts",
                  "data_gate_executions", "data_gate_results_returned",
                  "admission_decisions", "company_row_macro_joins",
                  "feature_materializations",
                  "fx_transformation_calculations",
                  "common_sample_constructions", "model_fits", "predictions",
                  "predictive_metrics", "bootstrap_executions",
                  "holm_calculations", "shap_executions",
                  "hyperparameter_tuning_runs"):
        assert audit[field] == 0, field


def test_no_alternative_indicator_was_searched_or_retrieved(audit):
    assert audit["alternative_indicators_searched"] == 0
    assert audit["alternative_indicators_retrieved"] == 0
    assert audit["proxy_or_substitute_series_retrieved"] == 0


def test_the_final_test_was_never_touched(audit, boundary):
    assert audit["final_test_rows_read"] == 0
    assert audit["final_test_predictor_values_read"] == 0
    assert audit["final_test_target_values_read"] == 0
    assert boundary["final_test_locked"] is True
    assert boundary["final_test_access_authorized"] is False
    assert boundary["final_test_unlock_implied_by_retrieval"] is False


def test_no_raw_payload_was_committed_to_git(manifest):
    assert manifest["raw_payloads_committed_to_git"] == 0
    assert manifest["raw_payloads_retained_outside_git"] > 0
    metadata = _read_json(_META_REL)
    assert metadata["raw_wdi_payloads_committed_to_git"] == 0
    assert metadata["pii_committed_to_git"] is False
    assert metadata["credentials_committed_to_git"] is False
    # nothing that looks like a payload may sit in the package directory
    for name in os.listdir(os.path.join(REPO_ROOT, _PKG_REL)):
        assert "raw" not in name.lower() or name.endswith(".json")


def test_the_vintage_limitation_survived_retrieval(manifest):
    assert manifest["point_in_time_availability_claimed"] is False
    assert manifest["historical_vintage_availability_claimed"] is False
    assert manifest["wdi_vintage"] == "current_or_latest_revised"


# --------------------------------------------------------------------------- #
# Retrieval authorized nothing further
# --------------------------------------------------------------------------- #

def test_retrieval_did_not_authorize_or_execute_the_gate(boundary):
    assert boundary["retrieval_executed_data_gate"] is False
    assert boundary["retrieval_authorization_implies_gate_authorization"] is (
        False)
    assert boundary["combined_retrieval_and_gate_action_permitted"] is False
    assert boundary["retrieval_authorization_covers_data_gate"] is False
    assert boundary["m3_lag_wdi_data_gate_action_id"] == _GATE_ACTION
    assert boundary["m3_lag_wdi_data_gate_action_authorized"] is False
    assert boundary["m3_lag_wdi_data_gate_executed"] is False
    assert boundary[
        "m3_lag_wdi_data_gate_requires_new_explicit_human_authorization"] is (
        True)


def test_a_gate_pass_would_still_not_authorize_modeling(boundary):
    assert boundary["m3_lag_wdi_gate_pass_is_data_admission_only"] is True
    assert boundary["m3_lag_wdi_gate_pass_authorizes_modeling"] is False
    assert boundary["m3_lag_wdi_modeling_action_id"] == _MODEL_ACTION
    assert boundary["m3_lag_wdi_modeling_authorized"] is False
    assert boundary["m3_lag_wdi_modeling_started"] is False


def test_step_c_is_pointed_at_but_unauthorized(boundary, audit):
    assert boundary["m3_lag_wdi_next_action_id"] == _AUDIT_ACTION
    assert boundary["m3_lag_wdi_next_action_authorized"] is False
    assert boundary["m3_lag_wdi_next_action_executes_data_gate"] is False
    assert boundary["next_action_pointer_is_not_authorization"] is True
    assert boundary["m3_lag_wdi_post_retrieval_audit_action_authorized"] is (
        False)
    assert audit["post_retrieval_audit_executed"] is False


def test_the_locked_contract_was_not_modified(boundary):
    assert boundary["m3_lag_wdi_authoritative_contract_status"] == (
        "AUTHORITATIVE_CONTRACT_LOCKED_PRE_RETRIEVAL")
    assert boundary["m3_lag_wdi_contract_modified_by_this_action"] is False
    assert boundary["m3_lag_wdi_block_admitted"] is False
    decision = _read_json(_DECISION_REL)
    assert decision["scientific_effect"] == "NONE"
    assert decision["acquisition_is_not_admission"] is True
    assert decision["authorizes_next_action"] is False


def test_track_a_is_untouched(boundary):
    assert boundary["world_bank_inquiry_status"] == (
        "SUBMITTED_ACKNOWLEDGED_WAITING_FOR_SUBSTANTIVE_RESPONSE")
    assert boundary["world_bank_waiting_period_status"] == "ACTIVE"
    assert boundary["world_bank_follow_up_authorized"] is False
    assert boundary["world_bank_response_ingestion_authorized"] is False
    assert boundary["world_bank_inquiry_terminated_by_this_action"] is False
    assert boundary["track_b_retrieval_implies_track_a_resolved"] is False
    assert boundary["track_b_retrieval_implies_track_a_abandoned"] is False


# --------------------------------------------------------------------------- #
# The published Handoff agrees
# --------------------------------------------------------------------------- #

def test_the_handoff_publishes_retrieval_and_nothing_more(handoff):
    assert handoff["stage128_m3_lag_wdi_data_retrieval_started"] is True
    assert handoff["stage128_m3_lag_wdi_data_retrieval_completed"] is True
    assert handoff["stage128_m3_lag_wdi_retrieval_scope"] == _SCOPE
    assert handoff["stage128_m3_lag_wdi_indicators_retrieved"] == 2
    assert handoff["stage128_m3_lag_wdi_indicator_codes_retrieved"] == [
        _CPI, _FX]
    assert handoff["stage128_m3_lag_wdi_retrieval_country_code"] == "IRN"
    assert handoff["stage128_m3_lag_wdi_raw_payloads_committed_to_git"] == 0
    # and RETRIEVAL moved nothing downstream. The Data Gate is step D's own
    # separately authorized action: admission may exist only once that action
    # has run, and only as its verdict. Asserting "never admitted" here would
    # encode the pre-Gate moment instead of the rule.
    assert handoff["stage128_m3_lag_wdi_data_gate_authorized"] is False
    if handoff["stage128_m3_lag_wdi_data_gate_executed"] is False:
        assert handoff["stage128_m3_lag_wdi_block_admitted"] is False
    else:
        assert handoff["stage128_m3_lag_wdi_data_gate_authorized_now"] is False
        assert handoff["stage128_m3_lag_wdi_block_admitted"] is (
            handoff["stage128_m3_lag_wdi_data_gate_result"]
            == "PASS_M3_LAG_WDI_DATA_GATE")
    # A RULE, not a snapshot: step E is the separately authorized action that
    # legitimately makes modeling started, so pinning it False here would
    # encode the pre-step-E MOMENT and fail the instant a legitimate step E
    # ran. What holds at EVERY step is that modeling was not started BY THIS
    # action, and that no STANDING modeling permission ever exists.
    if handoff["stage128_m3_lag_wdi_modeling_started"] is True:
        assert handoff["stage128_m3_lag_wdi_modeling_executed"] is True
        assert handoff[
            "stage128_m3_lag_wdi_modeling_authorization_consumed"] is True
    assert handoff["stage128_m3_lag_wdi_modeling_authorized"] is False
    assert handoff["stage128_m3_lag_wdi_final_test_rows_read"] == 0
    assert handoff["final_test_locked"] is True


def test_the_handoff_pointer_advanced_to_an_unauthorized_next_step(handoff):
    """The pointer advances one separated step at a time, never authorized.

    Pinning this to the audit would encode the pre-audit MOMENT: step C has
    since been separately authorized and executed, which legitimately moves
    the pointer on to the Data Gate. The rule that must hold at every step is
    that the pointer names exactly one separated step, executes no Gate, and
    is never itself an authorization.
    """
    audited = handoff["stage128_m3_lag_wdi_post_retrieval_audit_executed"]
    gated = handoff["stage128_m3_lag_wdi_data_gate_executed"]
    modeled = handoff["stage128_m3_lag_wdi_modeling_started"]
    expected = (_NO_NEXT_ACTION if modeled
                else _MODEL_ACTION if gated
                else _GATE_ACTION if audited else _AUDIT_ACTION)
    assert handoff["stage128_m3_lag_wdi_next_action_id"] == expected
    assert handoff["stage128_m3_lag_wdi_next_action_authorized"] is False
    # `executes_data_gate` describes the NAMED action, so it is True exactly
    # when the pointer has reached the Gate action itself. Pinning it to False
    # would contradict the locked sequence, in which step D executes the Gate.
    assert handoff["stage128_m3_lag_wdi_next_action_executes_data_gate"] is (
        expected == _GATE_ACTION)
    # whatever the pointer names, no STANDING authorization exists behind it
    assert handoff["stage128_m3_lag_wdi_data_gate_authorized"] is False
    if gated:
        assert handoff["stage128_m3_lag_wdi_data_gate_authorized_now"] is False
        assert handoff[
            "stage128_m3_lag_wdi_data_gate_authorization_reusable"] is False


def test_the_handoff_marks_the_authorization_spent(handoff):
    # HISTORICAL fact: the retrieval WAS explicitly authorized, once.
    assert handoff["stage128_m3_lag_wdi_retrieval_was_authorized"] is True
    # STANDING fact: that authorization is consumed, so nothing NOW permits
    # another World Bank request. The generic field carries the standing
    # meaning and must therefore be False after consumption.
    assert handoff["stage128_m3_lag_wdi_retrieval_authorized_now"] is False
    assert handoff["stage128_m3_lag_wdi_retrieval_authorized"] is False
    assert handoff["stage128_m3_lag_wdi_retrieval_authorization_consumed"] is (
        True)
    assert handoff["stage128_m3_lag_wdi_retrieval_authorization_reusable"] is (
        False)
    assert handoff[
        "stage128_m3_lag_wdi_further_retrieval_requires_new_human_"
        "authorization"] is True


def test_a_consumed_authorization_never_reads_as_standing(handoff):
    """FAIL-CLOSED: consumed one-time authorizations may not look standing.

    Whatever else the Handoff publishes about the executed retrieval, no
    combination of fields may simultaneously say "consumed" and "authorized
    now". If a future edit flips the generic field back to True while the
    authorization stays consumed, this test refuses.
    """
    consumed = handoff[
        "stage128_m3_lag_wdi_retrieval_authorization_consumed"]
    if consumed is True:
        assert handoff[
            "stage128_m3_lag_wdi_retrieval_authorized_now"] is False
        assert handoff["stage128_m3_lag_wdi_retrieval_authorized"] is False
        assert handoff[
            "stage128_m3_lag_wdi_retrieval_authorization_reusable"] is False
        assert handoff[
            "stage128_m3_lag_wdi_further_retrieval_requires_new_human_"
            "authorization"] is True


def test_current_state_never_renders_step_b_as_currently_authorized():
    """FAIL-CLOSED: the generated state must separate WAS from NOW.

    A human reading CURRENT_STATE.md must not be able to interpret the old
    (consumed) retrieval authorization as permission to issue another World
    Bank request. The historical fact stays visible; the ambiguous
    "(B) `<action>` — authorized True" rendering must never come back.
    """
    with open(os.path.join(REPO_ROOT, "project/docs/ai/CURRENT_STATE.md"),
              encoding="utf-8") as fh:
        text = fh.read()
    assert f"`{_ACTION_ID}` — authorized True" not in text
    assert f"`{_ACTION_ID}` — was authorized (historical) True" in text
    assert "authorized NOW (standing) False" in text
    assert "further retrieval requires NEW human authorization = True" in text


def test_the_action_sequence_still_separates_every_step(handoff):
    sequence = handoff["stage128_m3_lag_wdi_action_sequence"]
    assert [e["step"] for e in sequence] == ["A", "B", "C", "D", "E"]
    by_step = {e["step"]: e for e in sequence}
    assert by_step["B"]["action_id"] == _ACTION_ID
    assert by_step["C"]["action_id"] == _AUDIT_ACTION
    assert by_step["D"]["action_id"] == _GATE_ACTION
    assert by_step["E"]["action_id"] == _MODEL_ACTION
    # Step E is always unauthorized here. Steps C and D are NOT pinned: each
    # may since have been separately authorized and completed, and asserting
    # either is forever unauthorized would encode a moment rather than the
    # rule. What holds at every step is that nothing is authorized NOW.
    assert by_step["E"]["authorized"] is False
    assert by_step["E"]["was_authorized"] is False
    assert by_step["E"]["status"] == "NOT_AUTHORIZED"
    for step in ("C", "D"):
        assert by_step[step]["status"] in ("COMPLETE", "NOT_AUTHORIZED"), step
    # completed steps stay history: nothing in the sequence is standing
    for entry in sequence:
        assert entry["authorized"] is False, entry["step"]
        assert entry["authorized_now"] is False, entry["step"]
    # no single step both retrieves and gates
    for entry in sequence:
        assert not (entry["executes_retrieval"] and entry["executes_data_gate"])


# --------------------------------------------------------------------------- #
# FAIL-CLOSED DRIFT TESTS
# --------------------------------------------------------------------------- #

def _root(tmp_path, name: str, overrides: dict[str, dict]) -> str:
    """A repository root carrying the contract lock plus (mutated) retrieval."""
    root = tmp_path / name
    (root / _PKG_REL).mkdir(parents=True)
    lock_pkg = "project/stage128/m3_lag_wdi_exploratory_contract_lock"
    (root / lock_pkg).mkdir(parents=True)
    for rel in _ALL_RELS:
        payload = overrides.get(rel) or _read_json(rel)
        with open(os.path.join(str(root), rel), "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
    for name_ in os.listdir(os.path.join(REPO_ROOT, lock_pkg)):
        if not name_.endswith(".json"):
            continue
        src = os.path.join(REPO_ROOT, lock_pkg, name_)
        with open(src, encoding="utf-8") as fh:
            payload = json.load(fh)
        with open(os.path.join(str(root), lock_pkg, name_), "w",
                  encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
    return str(root)


def _mutated(rel: str, mutate) -> dict[str, dict]:
    payload = copy.deepcopy(_read_json(rel))
    mutate(payload)
    return {rel: payload}


def test_the_unmutated_package_is_accepted_by_both_recognizers(tmp_path):
    """The drift tests below are only meaningful if the real one passes."""
    root = _root(tmp_path, "clean", {})
    markers = gen.derive_stage128_m3_lag_wdi_data_retrieval_markers(root)
    assert markers["stage128_m3_lag_wdi_data_retrieval_started"] is True
    assert v.stage128_m3_lag_wdi_data_retrieval_executed(Path(root)) is True


_AUDIT_DRIFT = [
    ("a value was inspected", lambda p: p.update(wdi_value_inspections=1)),
    ("an observation was read", lambda p: p.update(wdi_observations_read=12)),
    ("coverage was calculated", lambda p: p.update(coverage_calculations=1)),
    ("the Gate ran", lambda p: p.update(data_gate_executions=1)),
    ("a Gate result was returned",
     lambda p: p.update(data_gate_results_returned=1)),
    ("data was admitted", lambda p: p.update(admission_decisions=1)),
    ("a company row was joined", lambda p: p.update(company_row_macro_joins=1)),
    ("a feature was materialized",
     lambda p: p.update(feature_materializations=1)),
    ("the FX transform ran",
     lambda p: p.update(fx_transformation_calculations=1)),
    ("a model was fit", lambda p: p.update(model_fits=1)),
    ("a final-test row was read", lambda p: p.update(final_test_rows_read=1)),
    ("an alternative indicator was retrieved",
     lambda p: p.update(alternative_indicators_retrieved=1)),
    ("an indicator search happened",
     lambda p: p.update(alternative_indicators_searched=3)),
    ("the payload was parsed", lambda p: p.update(payload_json_decoded=True)),
    ("the post-retrieval audit ran",
     lambda p: p.update(post_retrieval_audit_executed=True)),
]


@pytest.mark.parametrize("label,mutate", _AUDIT_DRIFT,
                         ids=[d[0] for d in _AUDIT_DRIFT])
def test_execution_drift_fails_closed(tmp_path, label, mutate):
    root = _root(tmp_path, "audit", _mutated(_AUDIT_REL, mutate))
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_data_retrieval_markers(root)


@pytest.mark.parametrize("label,mutate", _AUDIT_DRIFT,
                         ids=[d[0] for d in _AUDIT_DRIFT])
def test_execution_drift_fails_closed_in_the_validator(tmp_path, label,
                                                       mutate):
    root = _root(tmp_path, "audit_v", _mutated(_AUDIT_REL, mutate))
    with pytest.raises(v.ValidationFail):
        v.stage128_m3_lag_wdi_data_retrieval_executed(Path(root))


_MANIFEST_DRIFT = [
    ("a third indicator appears", lambda p: p["indicators"].append(
        dict(p["indicators"][0], indicator_code="PA.NUS.ATLS"))),
    ("an indicator was substituted", lambda p: p["indicators"][1].update(
        indicator_code="PA.NUS.ATLS")),
    ("the CPI series was swapped", lambda p: p["indicators"][0].update(
        indicator_code="FP.CPI.TOTL")),
    ("another country was retrieved", lambda p: p["indicators"][0].update(
        country_code="TUR")),
    ("a non-official host was used", lambda p: p["indicators"][0].update(
        request_url="https://example.com/v2/x")),
    ("plain HTTP was used", lambda p: p["indicators"][0].update(
        request_url="http://api.worldbank.org/v2/country/IRN/indicator/X")),
    ("the payload was parsed", lambda p: p["indicators"][0].update(
        payload_parsed=True)),
    ("observations were counted", lambda p: p["indicators"][0].update(
        observations_read=64)),
    ("coverage was recorded", lambda p: p["indicators"][0].update(
        coverage_calculated=0.91)),
    ("a point-in-time claim appeared",
     lambda p: p.update(point_in_time_availability_claimed=True)),
    ("a raw payload was committed",
     lambda p: p.update(raw_payloads_committed_to_git=2)),
]


@pytest.mark.parametrize("label,mutate", _MANIFEST_DRIFT,
                         ids=[d[0] for d in _MANIFEST_DRIFT])
def test_source_manifest_drift_fails_closed(tmp_path, label, mutate):
    root = _root(tmp_path, "manifest", _mutated(_MANIFEST_REL, mutate))
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_data_retrieval_markers(root)


@pytest.mark.parametrize("label,mutate", _MANIFEST_DRIFT,
                         ids=[d[0] for d in _MANIFEST_DRIFT])
def test_source_manifest_drift_fails_closed_in_the_validator(tmp_path, label,
                                                             mutate):
    root = _root(tmp_path, "manifest_v", _mutated(_MANIFEST_REL, mutate))
    with pytest.raises(v.ValidationFail):
        v.stage128_m3_lag_wdi_data_retrieval_executed(Path(root))


_BOUNDARY_DRIFT = [
    ("retrieval executed the Gate",
     lambda p: p.update(retrieval_executed_data_gate=True)),
    ("retrieval authorized the Gate",
     lambda p: p.update(
         retrieval_authorization_implies_gate_authorization=True)),
    ("a combined retrieval+gate action was allowed",
     lambda p: p.update(combined_retrieval_and_gate_action_permitted=True)),
    ("the Gate became authorized",
     lambda p: p.update(m3_lag_wdi_data_gate_action_authorized=True)),
    ("the Gate ran", lambda p: p.update(m3_lag_wdi_data_gate_executed=True)),
    ("a Gate PASS authorized modeling",
     lambda p: p.update(m3_lag_wdi_gate_pass_authorizes_modeling=True)),
    ("modeling became authorized",
     lambda p: p.update(m3_lag_wdi_modeling_authorized=True)),
    ("step C became authorized",
     lambda p: p.update(m3_lag_wdi_post_retrieval_audit_action_authorized=True)),
    ("the pointer became an authorization",
     lambda p: p.update(m3_lag_wdi_next_action_authorized=True)),
    ("the authorization became reusable",
     lambda p: p.update(retrieval_authorization_reusable=True)),
    ("the block was admitted",
     lambda p: p.update(m3_lag_wdi_block_admitted=True)),
    ("the Final Test was unlocked",
     lambda p: p.update(final_test_access_authorized=True)),
    ("Track A was terminated",
     lambda p: p.update(world_bank_inquiry_terminated_by_this_action=True)),
    ("merge was authorized", lambda p: p.update(merge_authorized=True)),
]


@pytest.mark.parametrize("label,mutate", _BOUNDARY_DRIFT,
                         ids=[d[0] for d in _BOUNDARY_DRIFT])
def test_governance_drift_fails_closed(tmp_path, label, mutate):
    root = _root(tmp_path, "boundary", _mutated(_BOUNDARY_REL, mutate))
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_data_retrieval_markers(root)


@pytest.mark.parametrize("label,mutate", _BOUNDARY_DRIFT,
                         ids=[d[0] for d in _BOUNDARY_DRIFT])
def test_governance_drift_fails_closed_in_the_validator(tmp_path, label,
                                                        mutate):
    root = _root(tmp_path, "boundary_v", _mutated(_BOUNDARY_REL, mutate))
    with pytest.raises(v.ValidationFail):
        v.stage128_m3_lag_wdi_data_retrieval_executed(Path(root))


def test_a_forged_authorization_digest_fails_closed(tmp_path):
    root = _root(tmp_path, "forged", _mutated(
        _AUTH_REL, lambda p: p.update(authorization_sha256="0" * 64)))
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_data_retrieval_markers(root)
    with pytest.raises(v.ValidationFail):
        v.stage128_m3_lag_wdi_data_retrieval_executed(Path(root))


def test_a_tampered_authorization_text_fails_closed(tmp_path):
    root = _root(tmp_path, "tampered", _mutated(
        _AUTH_REL,
        lambda p: p.update(authorization_text=p["authorization_text"]
                           + " و data gate")))
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_data_retrieval_markers(root)


def test_reusing_the_contract_lock_authorization_fails_closed(tmp_path):
    root = _root(tmp_path, "reused", _mutated(
        _AUTH_REL,
        lambda p: p.update(prior_contract_lock_authorization_reused=True)))
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_data_retrieval_markers(root)


def test_a_reusable_authorization_fails_closed(tmp_path):
    root = _root(tmp_path, "standing", _mutated(
        _AUTH_REL,
        lambda p: p.update(authorization_is_reusable_for_data_gate=True)))
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_data_retrieval_markers(root)


def test_an_absent_package_yields_no_markers(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert gen.derive_stage128_m3_lag_wdi_data_retrieval_markers(
        str(empty)) == {}
    assert v.stage128_m3_lag_wdi_data_retrieval_executed(Path(empty)) is False


# --------------------------------------------------------------------------- #
# The offline modules cannot reach the network
# --------------------------------------------------------------------------- #

def test_only_the_capture_layer_can_open_a_socket():
    offline = Path(REPO_ROOT) / "project/src" / (
        "stage128_m3_lag_wdi_exploratory_data_retrieval.py")
    text = offline.read_text(encoding="utf-8")
    for forbidden in ("import urllib", "import socket", "import requests",
                      "import http.client", "urlopen", "import ssl"):
        assert forbidden not in text, forbidden


def test_the_runner_imports_the_capture_layer_only_on_the_retrieve_path():
    runner = Path(REPO_ROOT) / (
        "project/run_stage128_m3_lag_wdi_exploratory_data_retrieval.py")
    text = runner.read_text(encoding="utf-8")
    import_line = "from src import stage128_m3_lag_wdi_retrieval_capture_layer"
    assert text.count(import_line) == 1
    # it must sit INSIDE the _retrieve function, never at module scope
    assert not any(line.startswith(import_line)
                   for line in text.splitlines())


# --------------------------------------------------------------------------- #
# BLOCKER 1 REGRESSION — a MERGED predecessor may never be the live Draft
#
# PR #78 (the contract lock) merged into main by 175e7949…, so the live Draft
# is now the retrieval PR #79. The failure this guards against is the stale
# claim "PR #78 is still the live Draft": a merged PR re-published as the open
# Draft. Both halves of each merge are pinned — the PR number AND its merge
# commit — because "live > predecessor" alone would happily accept a topology
# that renamed the merged #78 the live PR and demoted #77 in its place.
# --------------------------------------------------------------------------- #

_CONTRACT_LOCK_PR = 78
_CONTRACT_LOCK_MERGE_COMMIT = "175e7949e009eeecdd66aedab31ec4b48e9d3c7d"
_RETRIEVAL_LIVE_PR = 79
_RETRIEVAL_LIVE_PR_ROLE = "m3_lag_wdi_exploratory_data_retrieval_pr"


def test_the_retrieval_topology_makes_pr78_merged_history_and_pr79_live():
    topo = _read_json(_TOPOLOGY_REL)
    assert topo["predecessor_pr_number"] == _CONTRACT_LOCK_PR
    assert topo["predecessor_pr_merged"] is True
    assert topo["predecessor_pr_merge_commit"] == _CONTRACT_LOCK_MERGE_COMMIT
    assert topo["predecessor_pr_role"] == (
        "m3_lag_wdi_exploratory_contract_lock_pr")
    assert topo["live_pr_number"] == _RETRIEVAL_LIVE_PR
    assert topo["live_pr_role"] == _RETRIEVAL_LIVE_PR_ROLE
    assert topo["live_pr_is_draft"] is True
    assert topo["live_pr_merged"] is False
    assert topo["live_pr_base_branch"] == "main"
    # the live PR is based on exactly the merge commit of its predecessor
    assert topo["live_pr_base_commit"] == _CONTRACT_LOCK_MERGE_COMMIT
    assert topo["pr_is_stacked_on_open_predecessor"] is False
    assert topo["merge_authorized"] is False
    assert topo["ready_for_review_authorized"] is False
    # the head is a generation anchor, never pinned
    assert topo["live_pr_head_commit_pinned"] is False
    assert topo["live_pr_head_is_github_pr_head"] is False


def test_the_pinned_historical_roles_survive_the_re_anchoring():
    """Re-anchoring onto #79 must not shift what #76/#77/#78 *were*."""
    topo = _read_json(_TOPOLOGY_REL)
    assert topo["documentary_recovery_pr_number"] == 76
    assert topo["documentary_recovery_pr_merged"] is True
    assert topo["documentary_recovery_pr_merge_commit"] == (
        "89d8e6ff2d12ec82903cd28aa7ab839eb946b658")
    # #76 was superseded by #77 — not by whatever Draft is live now
    assert topo["documentary_recovery_pr_semantics"] == (
        "merged_predecessor_superseded_by_pr77")
    assert topo["human_submission_pr_number"] == 77
    assert topo["human_submission_pr_merged"] is True
    assert topo["human_submission_pr_merge_commit"] == (
        "93de6bae9344ce893b0261f818abce8a991cf842")
    assert topo["human_submission_pr_semantics"] == (
        "merged_predecessor_superseded_by_pr78")
    assert topo["contract_lock_pr_number"] == _CONTRACT_LOCK_PR
    assert topo["contract_lock_pr_action_id"] == (
        "stage128-m3-lag-wdi-exploratory-contract-lock")
    assert topo["recovery_pr_role_is_pinned_to_pr76"] is True
    assert topo["pr_roles_re_derived_from_adjacency"] is False
    assert topo["pr_roles_are_historical_facts_not_positional"] is True
    # four distinct PRs, in order, only the last unmerged
    sequence = [(e["pr_number"], e["merged"]) for e in topo["pr_role_sequence"]]
    assert sequence == [(76, True), (77, True), (_CONTRACT_LOCK_PR, True),
                        (_RETRIEVAL_LIVE_PR, False)]


def test_the_handoff_publishes_pr79_live_and_pr78_merged(handoff):
    assert handoff["stage128_m3i2_live_pr_number"] == _RETRIEVAL_LIVE_PR
    assert handoff["stage128_m3i2_live_pr_role"] == _RETRIEVAL_LIVE_PR_ROLE
    assert handoff["stage128_m3i2_live_pr_is_draft"] is True
    assert handoff["stage128_m3i2_live_pr_merged"] is False
    assert handoff["stage128_m3_lag_wdi_contract_lock_pr_number"] == (
        _CONTRACT_LOCK_PR)
    assert handoff["stage128_m3_lag_wdi_contract_lock_pr_merged"] is True
    assert handoff["stage128_m3_lag_wdi_contract_lock_pr_merge_commit"] == (
        _CONTRACT_LOCK_MERGE_COMMIT)


def _republish_merged_predecessor_as_live(payload: dict) -> None:
    """The exact stale claim: the merged PR #78 back as the live Draft."""
    payload["live_pr_number"] = _CONTRACT_LOCK_PR
    payload["live_pr_role"] = "m3_lag_wdi_exploratory_contract_lock_pr"
    payload["predecessor_pr_number"] = 77
    payload["predecessor_pr_merge_commit"] = (
        "93de6bae9344ce893b0261f818abce8a991cf842")


def _live_pr_also_marked_merged(payload: dict) -> None:
    payload["live_pr_merged"] = True
    for entry in payload["pr_role_sequence"]:
        if entry["pr_number"] == _RETRIEVAL_LIVE_PR:
            entry["merged"] = True
            entry["merge_commit"] = _CONTRACT_LOCK_MERGE_COMMIT


def _sequence_republishes_a_merged_pr_last(payload: dict) -> None:
    payload["pr_role_sequence"][-1] = {
        "pr_number": _CONTRACT_LOCK_PR,
        "role": "m3_lag_wdi_exploratory_contract_lock_pr",
        "merged": True,
        "merge_commit": _CONTRACT_LOCK_MERGE_COMMIT,
    }


_RETRIEVAL_TOPOLOGY_DRIFTS = (
    # THE regression this block exists for
    ("the_merged_pr78_is_republished_as_the_live_draft",
     _republish_merged_predecessor_as_live),
    ("the_live_pr_is_also_marked_merged", _live_pr_also_marked_merged),
    ("the_sequence_ends_on_a_merged_pr", _sequence_republishes_a_merged_pr_last),
    ("the_merged_predecessor_is_called_unmerged",
     lambda p: p.update({"predecessor_pr_merged": False})),
    ("the_predecessor_merge_commit_is_wrong",
     lambda p: p.update({"predecessor_pr_merge_commit": "0" * 40})),
    ("the_live_pr_precedes_its_merged_predecessor",
     lambda p: p.update({"live_pr_number": 77})),
    ("the_live_pr_is_marked_ready_instead_of_draft",
     lambda p: p.update({"live_pr_is_draft": False})),
    ("the_live_head_is_pinned",
     lambda p: p.update({"live_pr_head_commit_pinned": True})),
    ("the_pr_stops_targeting_main",
     lambda p: p.update({"live_pr_base_branch": "stage128-something"})),
    ("merge_becomes_authorized", lambda p: p.update({"merge_authorized": True})),
    ("ready_for_review_becomes_authorized",
     lambda p: p.update({"ready_for_review_authorized": True})),
    # the pinned historical roles must not slide forward
    ("the_recovery_role_slides_onto_pr77",
     lambda p: p.update({"documentary_recovery_pr_number": 77})),
    ("the_recovery_semantics_slide_onto_the_live_pr",
     lambda p: p.update({"documentary_recovery_pr_semantics":
                         "merged_predecessor_superseded_by_pr79"})),
    ("the_contract_lock_role_slides_onto_the_live_pr",
     lambda p: p.update({"contract_lock_pr_number": _RETRIEVAL_LIVE_PR})),
    ("roles_become_positional",
     lambda p: p.update({"pr_roles_re_derived_from_adjacency": True})),
)


@pytest.mark.parametrize("label,mutate", _RETRIEVAL_TOPOLOGY_DRIFTS,
                         ids=[label for label, _ in _RETRIEVAL_TOPOLOGY_DRIFTS])
def test_retrieval_topology_drift_fails_closed(tmp_path, label, mutate):
    root = _root(tmp_path, f"topo_{label}", _mutated(_TOPOLOGY_REL, mutate))
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_retrieval_live_pr_topology_markers(root)


def test_the_unmutated_retrieval_topology_is_accepted(tmp_path):
    """The drift tests above are only meaningful if the real one passes."""
    root = _root(tmp_path, "topo_clean", {})
    markers = gen.derive_stage128_m3_lag_wdi_retrieval_live_pr_topology_markers(
        root)
    assert markers["stage128_m3i2_live_pr_number"] == _RETRIEVAL_LIVE_PR
    assert markers["stage128_m3_lag_wdi_contract_lock_pr_merged"] is True
    # publishing a live topology moves NOTHING scientific
    assert markers["m3i2_data_gate_executed"] is False
    assert markers["m3i2_block_admitted"] is False
    assert markers["m3i2_modeling_started"] is False
    assert markers["m4_authorized"] is False
    assert markers["final_test_locked"] is True


# --------------------------------------------------------------------------- #
# BLOCKER 2 — the retained raw bytes stay locatable and content-addressed
#
# The future post-retrieval audit must be able to read the EXACT bytes captured
# during the authorized retrieval, not a later API response. The repository
# therefore commits a custody record (filename + byte count + SHA-256 + bundle
# id) and never the payload itself.
# --------------------------------------------------------------------------- #

def test_the_custody_record_locates_the_retained_raw_bytes():
    manifest = _read_json(_MANIFEST_REL)
    assert manifest["raw_payloads_committed_to_git"] == 0
    assert manifest["raw_payloads_retained_outside_git"] == 2
    assert manifest["raw_retention_bundle_id"] == (
        "papermali_stage128_m3_lag_wdi_retrieval_bundle_20260808T152237Z")
    assert manifest["raw_retention_mechanism"] == (
        "raw_bundle_retained_outside_git_content_addressed")
    assert manifest["raw_artifacts_identified_by_content_not_path"] is True


def test_the_custody_locator_is_not_a_filesystem_path():
    """An absolute path would be machine-specific and embed an account name."""
    manifest = _read_json(_MANIFEST_REL)
    bundle_id = manifest["raw_retention_bundle_id"]
    assert not bundle_id.startswith("/")
    assert "/" not in bundle_id and "\\" not in bundle_id
    assert "~" not in bundle_id


# --------------------------------------------------------------------------- #
# DURABLE CUSTODY — the bundle id must RESOLVE, not merely name
#
# A bundle identifier says WHICH bytes are authoritative. It does not say where
# a future auditor can obtain them, and an auditor who cannot obtain them has
# only two bad options: trust the digests blindly, or re-request the World Bank
# API and silently audit a NEWER response. The published archival DOI closes
# that gap. Identity stays content-addressed: the DOI locates, it never
# identifies.
# --------------------------------------------------------------------------- #

def test_the_retained_bundle_has_a_durable_archival_locator():
    manifest = _read_json(_MANIFEST_REL)
    assert manifest["raw_retention_durably_resolvable"] is True
    assert manifest["raw_retention_custody_class"] == (
        "public_archival_repository_zenodo")
    # The version DOI is immutable and pins THIS deposit; the concept DOI is
    # the all-versions identifier. They must be different, or "immutable"
    # would silently mean "whatever is newest".
    assert manifest["raw_retention_version_doi"] == "10.5281/zenodo.21844636"
    assert manifest["raw_retention_concept_doi"] == "10.5281/zenodo.21844635"
    assert (manifest["raw_retention_version_doi"]
            != manifest["raw_retention_concept_doi"])
    assert manifest["raw_retention_record_url"] == (
        "https://zenodo.org/records/21844636")
    assert manifest["raw_retention_deposited_artifact_count"] == 5


def test_recovery_never_routes_back_to_the_world_bank_api():
    """Re-requesting the API returns the CURRENT series, not these bytes."""
    manifest = _read_json(_MANIFEST_REL)
    assert manifest[
        "raw_retention_recovery_requires_new_world_bank_request"] is False
    assert manifest["raw_retention_depends_on_developer_filesystem"] is False


def test_the_doi_locates_but_content_still_identifies():
    manifest = _read_json(_MANIFEST_REL)
    # Even with a durable locator, identity stays byte-level.
    assert manifest["raw_artifacts_identified_by_content_not_path"] is True
    for entry in manifest["indicators"]:
        assert entry["raw_artifact_sha256"]
        assert entry["raw_artifact_bytes"] > 0
    # and the payloads still are not in git
    assert manifest["raw_payloads_committed_to_git"] == 0


@pytest.mark.parametrize("field", [
    "raw_retention_version_doi",
    "raw_retention_concept_doi",
    "raw_retention_record_url",
    "raw_retention_custody_class",
])
def test_no_custody_field_is_a_local_path_or_secret(field):
    """Custody metadata is public and non-secret by construction."""
    value = _read_json(_MANIFEST_REL)[field]
    assert isinstance(value, str) and value.strip()
    assert not value.startswith(("/", "~", "."))
    assert "\\" not in value
    # no credential-ish material and no account name ever reaches git
    lowered = value.lower()
    for forbidden in ("token", "secret", "password", "apikey", "api_key",
                      "access_key", "bearer", "@", "users/"):
        assert forbidden not in lowered, (field, forbidden)


def test_the_handoff_publishes_the_durable_custody_locator(handoff):
    assert handoff[
        "stage128_m3_lag_wdi_raw_evidence_durably_resolvable"] is True
    assert handoff["stage128_m3_lag_wdi_raw_retention_version_doi"] == (
        "10.5281/zenodo.21844636")
    assert handoff["stage128_m3_lag_wdi_raw_retention_concept_doi"] == (
        "10.5281/zenodo.21844635")
    assert handoff[
        "stage128_m3_lag_wdi_raw_evidence_recovery_requires_new_world_bank_"
        "request"] is False
    assert handoff[
        "stage128_m3_lag_wdi_raw_evidence_depends_on_developer_"
        "filesystem"] is False


@pytest.mark.parametrize("name,mutate", [
    # claiming durable custody with no locator at all
    ("durable_custody_claimed_without_a_doi",
     lambda p: p.update(raw_retention_version_doi="")),
    ("durable_custody_claimed_without_a_record_url",
     lambda p: p.update(raw_retention_record_url="   ")),
    # a locator that is really somebody's laptop
    ("locator_is_an_absolute_path",
     lambda p: p.update(raw_retention_record_url="/local/path/to/bundle")),
    ("locator_is_a_home_relative_path",
     lambda p: p.update(raw_retention_version_doi="~/bundle")),
    # a "DOI" that is not a DOI
    ("version_doi_is_not_a_doi",
     lambda p: p.update(raw_retention_version_doi="zenodo-21844636")),
    # recovery quietly routed back to the live API
    ("recovery_requires_a_new_world_bank_request",
     lambda p: p.update(
         raw_retention_recovery_requires_new_world_bank_request=True)),
    # custody that still needs the developer's machine
    ("custody_depends_on_a_developer_filesystem",
     lambda p: p.update(raw_retention_depends_on_developer_filesystem=True)),
    # a DOI used to replace, rather than locate, content identity
    ("content_addressing_dropped_in_favour_of_the_doi",
     lambda p: p.update(raw_artifacts_identified_by_content_not_path=False)),
])
def test_a_false_custody_claim_is_refused(tmp_path, name, mutate):
    """FAIL-CLOSED: durable custody is publishable only when it is real."""
    root = _root(tmp_path, name, _mutated(_MANIFEST_REL, mutate))
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_data_retrieval_markers(root)


def test_every_retained_artifact_is_pinned_by_bytes_and_sha256():
    manifest = _read_json(_MANIFEST_REL)
    expected = {
        "FP.CPI.TOTL.ZG": (
            "f62292c52088df71__FP.CPI.TOTL.ZG.attempt1.json", 15805,
            "f62292c52088df714c34846a6865ddc47306d497"
            "96ea9ec9014441893d553add"),
        "PA.NUS.FCRF": (
            "74b585734cc48dd2__PA.NUS.FCRF.attempt1.json", 16482,
            "74b585734cc48dd2e9d063e955d95a619dbaa5e4"
            "bbff283b128da21b339d63d4"),
    }
    total = 0
    for entry in manifest["indicators"]:
        filename, size, digest = expected[entry["indicator_code"]]
        assert entry["raw_artifact_filename"] == filename
        assert entry["raw_artifact_bytes"] == size
        assert entry["raw_artifact_sha256"] == digest
        assert len(entry["raw_artifact_sha256"]) == 64
        # custody metadata only: nothing inside the bytes was ever looked at
        assert entry["payload_parsed"] is False
        assert entry["observations_read"] is None
        assert entry["values_inspected"] is None
        assert entry["coverage_calculated"] is None
        total += entry["raw_artifact_bytes"]
    assert total == 32287
