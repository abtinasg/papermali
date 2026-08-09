"""Stage128 — Track B step C: the M3-LAG-WDI POST-RETRIEVAL AUDIT.

These tests police one narrow claim: the retained evidence was DECODED and
characterised, and *nothing else happened*. Reading is not admitting.

The interesting tests are the ones that try to smuggle step D through step C:
an audit that quietly ran the Gate, applied a coverage threshold, admitted the
block, touched a company row, or let its own PASS read as authorization for the
Data Gate. Each is refused by the recognizer, not merely absent from the data.

Two further invariants matter as much as the boundary ones. The audit must
never mutate the evidence it audits — that evidence is anchored to an immutable
archival record. And a material finding must never be laundered away: an audit
carrying recorded limitations may not publish itself as a bare PASS.

No test here opens a socket, and step C has no network code path to open one
with.
"""
from __future__ import annotations

import copy
import json
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "project", "scripts"))
sys.path.insert(0, os.path.join(REPO_ROOT, "project"))

import update_ai_handoff as gen  # noqa: E402
from src import (  # noqa: E402
    stage128_m3_lag_wdi_exploratory_post_retrieval_audit as m)

_PKG_REL = "project/stage128/m3_lag_wdi_exploratory_post_retrieval_audit"
_REPORT_REL = f"{_PKG_REL}/stage128_m3_lag_wdi_post_retrieval_audit_report.json"
_EXEC_REL = (
    f"{_PKG_REL}/stage128_m3_lag_wdi_post_retrieval_audit_execution_audit.json")
_BOUNDARY_REL = (
    f"{_PKG_REL}/"
    "stage128_m3_lag_wdi_post_retrieval_audit_governance_boundary.json")
_DECISION_REL = (
    f"{_PKG_REL}/stage128_m3_lag_wdi_post_retrieval_audit_decision.json")
_AUTH_REL = (
    f"{_PKG_REL}/"
    "stage128_m3_lag_wdi_post_retrieval_audit_human_authorization_record.json")
_QC_REL = (
    f"{_PKG_REL}/stage128_m3_lag_wdi_post_retrieval_audit_qc_report.json")

_ALL_RELS = (_REPORT_REL, _EXEC_REL, _BOUNDARY_REL, _DECISION_REL, _AUTH_REL,
             _QC_REL)

_ACTION_ID = "stage128-m3-lag-wdi-exploratory-post-retrieval-audit"
_GATE_ACTION = "stage128-m3-lag-wdi-exploratory-data-gate"
_MODELING_ACTION = "stage128-m3-lag-wdi-exploratory-incremental-evaluation"
_CPI = "FP.CPI.TOTL.ZG"
_FX = "PA.NUS.FCRF"


def _read_json(rel: str) -> dict:
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def report() -> dict:
    return _read_json(_REPORT_REL)


@pytest.fixture(scope="module")
def audit() -> dict:
    return _read_json(_EXEC_REL)


@pytest.fixture(scope="module")
def boundary() -> dict:
    return _read_json(_BOUNDARY_REL)


@pytest.fixture(scope="module")
def decision() -> dict:
    return _read_json(_DECISION_REL)


@pytest.fixture(scope="module")
def handoff() -> dict:
    return _read_json("project/docs/ai/handoff_state.json")


# --------------------------------------------------------------------------- #
# STRUCTURAL: step C cannot reach the network at all
# --------------------------------------------------------------------------- #

_NETWORK_MODULES = frozenset({
    "urllib", "urllib.request", "requests", "http", "http.client", "socket",
    "ssl", "ftplib", "telnetlib", "asyncio",
    "stage128_m3_lag_wdi_retrieval_capture_layer",
})

_RUNNER_REL = (
    "project/run_stage128_m3_lag_wdi_exploratory_post_retrieval_audit.py")


def _imported_modules(path: str) -> set[str]:
    """Every module name imported by a file, via the AST.

    Substring matching would be wrong in both directions here: it trips over
    the counter name ``world_bank_api_requests`` and it would miss an aliased
    import. Only real import statements count.
    """
    import ast
    tree = ast.parse(open(path, encoding="utf-8").read())
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                found.add(node.module)
            found.update(f"{node.module}.{a.name}" if node.module else a.name
                         for a in node.names)
    return found


def test_the_audit_module_has_no_network_surface():
    imported = _imported_modules(m.__file__)
    assert not (imported & _NETWORK_MODULES), imported & _NETWORK_MODULES
    for name in imported:
        assert name.split(".")[0] not in _NETWORK_MODULES, name


def test_the_runner_exposes_no_retrieve_mode():
    path = os.path.join(REPO_ROOT, _RUNNER_REL)
    source = open(path, encoding="utf-8").read()
    # The prose may (and does) mention --retrieve in order to say it does not
    # exist; what must be absent is an actual registered flag.
    assert 'add_argument("--retrieve"' not in source
    imported = _imported_modules(path)
    assert not (imported & _NETWORK_MODULES), imported & _NETWORK_MODULES
    for name in imported:
        assert name.split(".")[0] not in _NETWORK_MODULES, name


# --------------------------------------------------------------------------- #
# Identity is proven BEFORE the bytes are decoded
# --------------------------------------------------------------------------- #

def test_a_payload_with_the_wrong_size_is_refused(tmp_path):
    path = tmp_path / "payload.json"
    path.write_bytes(b'[{"pages":1},[]]')
    with pytest.raises(m.PostRetrievalAuditError):
        m.load_retained_payload(str(path), 999_999, "0" * 64)


def test_a_payload_with_the_wrong_digest_is_refused(tmp_path):
    blob = b'[{"pages":1},[]]'
    path = tmp_path / "payload.json"
    path.write_bytes(blob)
    with pytest.raises(m.PostRetrievalAuditError):
        m.load_retained_payload(str(path), len(blob), "0" * 64)


def test_the_audited_payload_identity_matches_the_committed_manifest(report):
    manifest = _read_json(
        "project/stage128/m3_lag_wdi_exploratory_data_retrieval/"
        "stage128_m3_lag_wdi_retrieval_source_manifest.json")
    committed = {e["indicator_code"]: (e["raw_artifact_bytes"],
                                       e["raw_artifact_sha256"])
                 for e in manifest["indicators"]}
    audited = {e["indicator_code"]: (e["raw_artifact_bytes"],
                                     e["raw_artifact_sha256"])
               for e in report["retained_payload_identity"]}
    assert audited == committed
    for entry in report["retained_payload_identity"]:
        assert entry["identity_matches_committed_manifest"] is True
        assert entry["bytes_modified_by_this_action"] is False


# --------------------------------------------------------------------------- #
# The audit read a SERIES, and only a series
# --------------------------------------------------------------------------- #

def test_both_locked_series_were_audited(report):
    assert [s["indicator_code"] for s in report["series"]] == [_CPI, _FX]
    for series in report["series"]:
        assert series["country_code"] == "IRN"
        assert series["response_pages"] == 1
        assert series["calendar_gaps"] == []
        assert series["observation_years_distinct"] == series[
            "observations_returned"]


def test_the_audit_is_series_level_and_never_sample_level(report):
    assert report["audit_level"] == "series_level_only_never_sample_level"
    assert report["candidate_coverage_computed"] is False
    assert report["block_coverage_computed"] is False
    assert report["coverage_thresholds_applied"] is False
    assert report["admission_decision_made"] is False
    assert report["company_rows_touched"] == 0


def test_every_downstream_counter_stayed_zero(audit):
    for counter in gen._STAGE128_M3_LAG_AUDIT_ZERO_COUNTERS:
        assert audit[counter] == 0, counter
    assert audit["post_retrieval_audit_executed"] is True
    assert audit["payload_json_decoded"] is True
    assert audit["wdi_observations_read"] > 0


def test_the_audit_did_not_mutate_the_evidence(audit):
    assert audit["retained_bytes_modified"] is False
    assert audit["deposited_evidence_modified"] is False


# --------------------------------------------------------------------------- #
# The findings are real and are not laundered away
# --------------------------------------------------------------------------- #

def test_the_fx_tail_nulls_were_detected(report):
    fx = next(s for s in report["series"] if s["indicator_code"] == _FX)
    assert fx["trailing_null_observation_years"], (
        "the FX series ends in nulls; an audit that missed that is not an "
        "audit")
    assert fx["numeric_observation_year_last"] < fx["observation_year_last"]


def test_the_cpi_series_is_complete_and_needs_no_positivity(report):
    cpi = next(s for s in report["series"] if s["indicator_code"] == _CPI)
    assert cpi["observations_null"] == 0
    assert cpi["non_numeric_observation_years"] == []
    # CPI is an annual % change: a non-positive value is deflation, not a
    # defect, and the contract imposes no positivity rule on it.
    availability = report["feature_availability"][0]
    assert availability["positivity_required"] is False


def test_the_binding_constraint_is_reported(report):
    assert report["binding_constraint_indicator"] == _FX
    cpi, fx = report["feature_availability"]
    assert fx["constructible_predictor_year_last"] < cpi[
        "constructible_predictor_year_last"]
    assert report["both_features_constructible_predictor_year_last"] == fx[
        "constructible_predictor_year_last"]


def test_the_degenerate_fx_years_are_reported(report):
    fx = report["feature_availability"][1]
    # Completeness is not information: a repeated pegged rate yields a log
    # ratio of exactly zero while satisfying every completeness rule.
    assert fx["trailing_zero_change_predictor_years"] > 0
    assert fx["trailing_zero_change_predictor_year_list"]
    assert fx["longest_consecutive_zero_change_run"] >= fx[
        "trailing_zero_change_predictor_years"]


def test_material_limitations_are_recorded_and_not_summarised_away(decision):
    assert decision["material_limitations"]
    assert decision["audit_result"] == "PASS_WITH_MATERIAL_FINDINGS"
    # a bare PASS alongside recorded limitations is exactly the laundering
    # this rule exists to prevent
    assert not (decision["audit_result"] == "PASS"
                and decision["material_limitations"])


# --------------------------------------------------------------------------- #
# Passing step C authorizes nothing
# --------------------------------------------------------------------------- #

def test_a_passing_audit_is_not_a_gate_authorization(boundary, decision):
    assert boundary["post_retrieval_audit_pass_is_gate_authorization"] is False
    assert boundary[
        "post_retrieval_audit_authorization_implies_gate_authorization"] is (
            False)
    assert boundary["post_retrieval_audit_pass_is_admission"] is False
    assert boundary["m3_lag_wdi_data_gate_action_authorized"] is False
    assert boundary["m3_lag_wdi_data_gate_executed"] is False
    assert boundary[
        "m3_lag_wdi_data_gate_requires_new_explicit_human_authorization"] is (
            True)
    assert decision["authorizes_next_action"] is False
    assert decision["next_action_id"] == _GATE_ACTION
    assert decision["next_action_authorized"] is False


def test_the_step_c_authorization_is_consumed_and_non_reusable(boundary):
    assert boundary[
        "m3_lag_wdi_post_retrieval_audit_action_authorized"] is True
    assert boundary["m3_lag_wdi_post_retrieval_audit_executed"] is True
    assert boundary[
        "m3_lag_wdi_post_retrieval_audit_authorization_consumed"] is True
    assert boundary[
        "m3_lag_wdi_post_retrieval_audit_authorization_reusable"] is False


def test_retrieval_semantics_are_untouched_by_step_c(boundary):
    assert boundary["retrieval_was_authorized"] is True
    assert boundary["retrieval_authorized_now"] is False
    assert boundary["retrieval_authorization_consumed"] is True
    assert boundary["retrieval_authorization_reusable"] is False
    assert boundary["further_retrieval_requires_new_human_authorization"] is (
        True)
    assert boundary["new_world_bank_request_made_by_this_action"] is False


def test_everything_downstream_is_still_closed(boundary):
    assert boundary["m3_lag_wdi_modeling_authorized"] is False
    assert boundary["m3_lag_wdi_modeling_started"] is False
    assert boundary["m3_lag_wdi_block_admitted"] is False
    assert boundary["m3_lag_wdi_gate_pass_authorizes_modeling"] is False
    assert boundary["final_test_locked"] is True
    assert boundary["final_test_access_authorized"] is False
    assert boundary["m4_authorized"] is False
    assert boundary["merge_authorized"] is False
    assert boundary["ready_for_review_authorized"] is False


def test_track_a_is_untouched_by_a_track_b_audit(boundary):
    assert boundary["world_bank_inquiry_status"] == (
        "SUBMITTED_ACKNOWLEDGED_WAITING_FOR_SUBSTANTIVE_RESPONSE")
    assert boundary["world_bank_inquiry_terminated_by_this_action"] is False
    assert boundary["world_bank_follow_up_authorized"] is False
    assert boundary["world_bank_response_ingestion_authorized"] is False


# --------------------------------------------------------------------------- #
# The published Handoff agrees
# --------------------------------------------------------------------------- #

def test_the_handoff_publishes_the_audit_and_advances_the_pointer(handoff):
    assert handoff["stage128_m3_lag_wdi_post_retrieval_audit_executed"] is True
    assert handoff["stage128_m3_lag_wdi_post_retrieval_audit_result"] == (
        "PASS_WITH_MATERIAL_FINDINGS")
    assert handoff["stage128_m3_lag_wdi_payload_json_decoded"] is True
    assert handoff["stage128_m3_lag_wdi_wdi_observations_read"] > 0
    # The pointer advanced to the Gate. Pinning it there forever would encode
    # the pre-Gate MOMENT: step D has its own separate authorization, and once
    # it runs the pointer legitimately advances again. What the AUDIT must
    # never have caused is that the Gate ran on the audit's authorization.
    gated = handoff["stage128_m3_lag_wdi_data_gate_executed"]
    assert handoff["stage128_m3_lag_wdi_next_action_id"] == (
        _MODELING_ACTION if gated else _GATE_ACTION)
    assert handoff["stage128_m3_lag_wdi_next_action_authorized"] is False
    if not gated:
        assert handoff["stage128_m3_lag_wdi_data_gate_authorized"] is False
        assert handoff["stage128_m3_lag_wdi_block_admitted"] is False
    else:
        assert handoff["stage128_m3_lag_wdi_data_gate_authorized_now"] is False
        assert handoff[
            "stage128_m3_lag_wdi_data_gate_authorization_consumed"] is True
    assert handoff["stage128_m3_lag_wdi_final_test_rows_read"] == 0
    assert handoff["final_test_locked"] is True


def test_the_handoff_keeps_the_findings_visible(handoff):
    limitations = handoff[
        "stage128_m3_lag_wdi_post_retrieval_audit_material_limitations"]
    assert limitations
    assert handoff[
        "stage128_m3_lag_wdi_post_retrieval_audit_material_limitation_count"
    ] == len(limitations)
    assert handoff[
        "stage128_m3_lag_wdi_fx_trailing_zero_change_predictor_years"] > 0
    assert handoff["stage128_m3_lag_wdi_binding_constraint_indicator"] == _FX


def test_current_state_shows_the_findings_next_to_the_pass():
    with open(os.path.join(REPO_ROOT, "project/docs/ai/CURRENT_STATE.md"),
              encoding="utf-8") as fh:
        text = fh.read()
    assert "Step C post-retrieval audit EXECUTED" in text
    assert "PASS_WITH_MATERIAL_FINDINGS" in text
    assert "Material findings recorded" in text
    assert "Reading is not admitting" in text


def test_next_action_executes_data_gate_describes_the_named_action(handoff):
    """`*_executes_data_gate` is DESCRIPTIVE, not a permission flag.

    Its established meaning is "does this named action execute the Data
    Gate?" — the canonical values live in the locked action sequence, where
    only step D carries True. Applied to the pointer, it has always mirrored
    the per-action value for the action pointed at: False while the pointer
    named retrieval, False while it named the audit, and True now that it
    names the Gate itself.

    Publishing "the next action is the Data Gate" beside "the next action does
    not execute the Data Gate" is a contradiction. The safety property lives
    in `next_action_authorized` / `data_gate_authorized` / `data_gate_executed`
    — never in pretending the Gate action does not gate.
    """
    pointer = handoff["stage128_m3_lag_wdi_next_action_id"]
    sequence = handoff["stage128_m3_lag_wdi_action_sequence"]
    canonical = {e["action_id"]: e["executes_data_gate"] for e in sequence}
    assert pointer in canonical
    assert handoff["stage128_m3_lag_wdi_next_action_executes_data_gate"] is (
        canonical[pointer]), (
            "the pointer's executes-the-Gate flag must equal the locked "
            "sequence value for the action it names")
    # and the flag must never leak into a STANDING permission, whether or not
    # the Gate has since run under its own separate authorization
    assert handoff["stage128_m3_lag_wdi_next_action_authorized"] is False
    if handoff["stage128_m3_lag_wdi_data_gate_executed"] is False:
        assert handoff["stage128_m3_lag_wdi_data_gate_authorized"] is False
    else:
        assert handoff["stage128_m3_lag_wdi_data_gate_authorized_now"] is False
        assert handoff[
            "stage128_m3_lag_wdi_data_gate_authorization_reusable"] is False


def test_exactly_one_locked_step_executes_the_data_gate(handoff):
    sequence = handoff["stage128_m3_lag_wdi_action_sequence"]
    gating = [e for e in sequence if e["executes_data_gate"]]
    assert len(gating) == 1
    assert gating[0]["step"] == "D"
    assert gating[0]["action_id"] == _GATE_ACTION


def test_the_action_sequence_marks_c_complete_but_nothing_standing(handoff):
    sequence = handoff["stage128_m3_lag_wdi_action_sequence"]
    by_step = {e["step"]: e for e in sequence}
    assert by_step["C"]["status"] == "COMPLETE"
    assert by_step["C"]["was_authorized"] is True
    for entry in sequence:
        assert entry["authorized"] is False, entry["step"]
        assert entry["authorized_now"] is False, entry["step"]
    # Step E stays closed. Step D is NOT pinned: it has its own separate
    # authorization and may since have completed, so asserting it is forever
    # unauthorized would encode a moment rather than the rule.
    assert by_step["E"]["was_authorized"] is False
    assert by_step["E"]["status"] == "NOT_AUTHORIZED"
    assert by_step["D"]["status"] in ("COMPLETE", "NOT_AUTHORIZED")


# --------------------------------------------------------------------------- #
# FAIL-CLOSED DRIFT TESTS
# --------------------------------------------------------------------------- #

def _root(tmp_path, name: str, overrides: dict[str, dict]) -> str:
    root = tmp_path / name
    (root / _PKG_REL).mkdir(parents=True)
    for rel in _ALL_RELS:
        payload = overrides.get(rel) or _read_json(rel)
        with open(os.path.join(str(root), rel), "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
    return str(root)


def _mutated(rel: str, mutate) -> dict[str, dict]:
    payload = copy.deepcopy(_read_json(rel))
    mutate(payload)
    return {rel: payload}


@pytest.mark.parametrize("name,rel,mutate", [
    # step D smuggled inside step C
    ("audit_claims_it_ran_the_gate", _EXEC_REL,
     lambda p: p.update(data_gate_executions=1)),
    ("audit_computed_coverage", _EXEC_REL,
     lambda p: p.update(coverage_calculations=1)),
    ("audit_compared_against_a_threshold", _EXEC_REL,
     lambda p: p.update(coverage_threshold_comparisons=1)),
    ("audit_made_an_admission_decision", _EXEC_REL,
     lambda p: p.update(admission_decisions=1)),
    ("audit_joined_a_company_row", _EXEC_REL,
     lambda p: p.update(company_row_macro_joins=1)),
    ("audit_fitted_a_model", _EXEC_REL,
     lambda p: p.update(model_fits=1)),
    ("audit_read_a_final_test_row", _EXEC_REL,
     lambda p: p.update(final_test_rows_read=1)),
    ("audit_made_a_new_world_bank_request", _EXEC_REL,
     lambda p: p.update(world_bank_api_requests=1)),
    # the audit decoded nothing, so it audited nothing
    ("audit_decoded_no_payload", _EXEC_REL,
     lambda p: p.update(payload_json_decoded=False)),
    # mutating the immutable evidence
    ("audit_modified_the_retained_bytes", _EXEC_REL,
     lambda p: p.update(retained_bytes_modified=True)),
    ("audit_modified_the_deposited_evidence", _EXEC_REL,
     lambda p: p.update(deposited_evidence_modified=True)),
    # a PASS used as permission
    ("pass_is_claimed_to_authorize_the_gate", _BOUNDARY_REL,
     lambda p: p.update(post_retrieval_audit_pass_is_gate_authorization=True)),
    ("pass_is_claimed_to_be_admission", _BOUNDARY_REL,
     lambda p: p.update(post_retrieval_audit_pass_is_admission=True)),
    ("gate_is_claimed_authorized", _BOUNDARY_REL,
     lambda p: p.update(m3_lag_wdi_data_gate_action_authorized=True)),
    ("gate_is_claimed_executed", _BOUNDARY_REL,
     lambda p: p.update(m3_lag_wdi_data_gate_executed=True)),
    ("modeling_is_claimed_authorized", _BOUNDARY_REL,
     lambda p: p.update(m3_lag_wdi_modeling_authorized=True)),
    ("block_is_claimed_admitted", _BOUNDARY_REL,
     lambda p: p.update(m3_lag_wdi_block_admitted=True)),
    ("next_action_is_claimed_authorized", _BOUNDARY_REL,
     lambda p: p.update(m3_lag_wdi_next_action_authorized=True)),
    ("merge_is_claimed_authorized", _BOUNDARY_REL,
     lambda p: p.update(merge_authorized=True)),
    ("final_test_is_unlocked", _BOUNDARY_REL,
     lambda p: p.update(final_test_locked=False)),
    # the consumed step C authorization made to look standing again
    ("step_c_authorization_left_reusable", _BOUNDARY_REL,
     lambda p: p.update(
         m3_lag_wdi_post_retrieval_audit_authorization_reusable=True)),
    # retrieval semantics quietly re-opened
    ("retrieval_made_standing_again", _BOUNDARY_REL,
     lambda p: p.update(retrieval_authorized_now=True)),
    # the report claiming Gate work
    ("report_applied_coverage_thresholds", _REPORT_REL,
     lambda p: p.update(coverage_thresholds_applied=True)),
    ("report_made_an_admission", _REPORT_REL,
     lambda p: p.update(admission_decision_made=True)),
    ("report_touched_company_rows", _REPORT_REL,
     lambda p: p.update(company_rows_touched=1)),
    # findings laundered out of the result
    ("findings_laundered_into_a_bare_pass", _DECISION_REL,
     lambda p: p.update(audit_result="PASS")),
    ("audit_claims_to_authorize_the_next_step", _DECISION_REL,
     lambda p: p.update(authorizes_next_action=True)),
    ("audit_claims_a_scientific_effect", _DECISION_REL,
     lambda p: p.update(scientific_effect="ADMITTED")),
])
def test_the_recognizer_refuses_drift(tmp_path, name, rel, mutate):
    root = _root(tmp_path, name, _mutated(rel, mutate))
    with pytest.raises(gen.HandoffError):
        gen.derive_stage128_m3_lag_wdi_post_retrieval_audit_markers(root)


def test_the_untouched_package_is_accepted(tmp_path):
    """The control: the real package must pass the same recognizer."""
    root = _root(tmp_path, "pristine", {})
    markers = gen.derive_stage128_m3_lag_wdi_post_retrieval_audit_markers(root)
    assert markers["stage128_m3_lag_wdi_post_retrieval_audit_executed"] is True
    assert markers["stage128_m3_lag_wdi_next_action_id"] == _GATE_ACTION
    assert markers["stage128_m3_lag_wdi_next_action_authorized"] is False
