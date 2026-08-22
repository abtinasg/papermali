"""Stage129 — the human manuscript reporting decision for the unexecuted M4.

This action is a REPORTING/GOVERNANCE DECISION ONLY. These tests pin:

  * that the reporting decision is no longer unresolved, and resolves to
    exactly one canonical, machine-readable value;
  * that it supersedes that single marker in the open -- the merged
    discontinuation package stays byte-for-byte intact and keeps its own
    historical `UNRESOLVED_REPORTING_DECISION`;
  * that the scientific state is untouched: the comparison stays unexecuted,
    the p-value stays null, no null hypothesis is resolved, the formal Gate
    verdict stays null and the Gate was never executed;
  * that the four frozen candidates keep their identity, order and count;
  * that the approved EN/FA reporting text exists and claims no executed
    result;
  * that the Final Test stays locked at zero rows and nothing downstream is
    authorized;
  * that the canonical generator is FAIL-CLOSED: reverting to unresolved,
    inventing a p-value or forging a Gate verdict must break the build.
"""
import copy
import json
import os
import re
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "project", "scripts"))

_PKG_REL = "project/stage129/m4_manuscript_reporting_decision"
_PKG = os.path.join(REPO_ROOT, _PKG_REL)
_DISC_REL = "project/stage129/m4_human_discontinuation_data_inadequacy"
_DISC_BOUNDARY_REL = (
    f"{_DISC_REL}/stage129_m4_human_discontinuation_governance_boundary.json")

ACTION_ID = "stage129-m4-manuscript-reporting-decision"
DECISION_VALUE = "REPORT_AS_PRESPECIFIED_NOT_EXECUTED_DATA_INADEQUACY_NO_INFERENCE"
SUPERSEDED_VALUE = "UNRESOLVED_REPORTING_DECISION"
REPORTING_KEY = "manuscript_reporting_decision_for_the_unexecuted_m4_comparison"
STATE_KEY = "stage129_m4_manuscript_reporting_decision_for_unexecuted_comparison"
COMPARISON_ID = "M4_minus_M3_CBI"
COMPARISON_STATUS = "NOT_EXECUTED_M4_DISCONTINUED"
DISC_STATUS = "M4_DISCONTINUED_BY_HUMAN_DECISION_DATA_INADEQUACY"
GATE_VERDICT_VOCAB = ("PASS_M4_DATA_GATE", "FAIL_M4_DATA_GATE",
                      "UNRESOLVED_M4_DATA_GATE")
CANDIDATES = ["audit_opinion_type", "going_concern_flag", "audit_lag_days", "board_size"]

APPROVED_EN = (
    "M4 was prespecified but was not admitted to modeling because the available "
    "data did not provide adequate coverage and did not satisfy the frozen "
    "feature definitions. Consequently, the M4−M3-CBI comparison was not "
    "executed, no p-value was computed, and no inferential conclusion is drawn "
    "for M4."
)


def _load(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def _text(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def decision():
    return _load(f"{_PKG_REL}/stage129_m4_manuscript_reporting_decision.json")


@pytest.fixture(scope="module")
def boundary():
    return _load(f"{_PKG_REL}/stage129_m4_manuscript_reporting_governance_boundary.json")


@pytest.fixture(scope="module")
def state():
    return _load("project/docs/ai/handoff_state.json")


@pytest.fixture(scope="module")
def roadmap_front_matter():
    text = _text("project/docs/ai/ROADMAP.md")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    assert m, "ROADMAP.md must carry YAML front matter"
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.strip().startswith("#"):
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


# ------------------------------ 1/2. the decision is resolved, and canonical
def test_the_reporting_decision_is_no_longer_unresolved(decision, boundary, state):
    for surface, value in (
        ("decision", decision[REPORTING_KEY]),
        ("boundary", boundary[REPORTING_KEY]),
        ("handoff", state[STATE_KEY]),
    ):
        assert value != SUPERSEDED_VALUE, surface
        assert "UNRESOLVED" not in value, surface
    assert boundary["manuscript_reporting_decision_is_resolved"] is True
    assert state["stage129_m4_manuscript_reporting_decision_is_resolved"] is True
    assert state["stage129_m4_manuscript_reporting_decision_recorded"] is True


def test_the_canonical_value_is_exact(decision, boundary, state,
                                      roadmap_front_matter):
    assert decision[REPORTING_KEY] == DECISION_VALUE
    assert decision["decision_status"] == DECISION_VALUE
    assert boundary[REPORTING_KEY] == DECISION_VALUE
    assert state[STATE_KEY] == DECISION_VALUE
    assert roadmap_front_matter["m4_manuscript_reporting_decision"] == DECISION_VALUE
    assert roadmap_front_matter["m4_manuscript_reporting_decision_resolved"] == "true"
    assert decision["decision_id"] == ACTION_ID
    assert decision["decision_type"] == "human_reporting_decision"
    assert decision["authorized_by_human"] is True
    assert state["stage129_m4_manuscript_reporting_decision_action_id"] == ACTION_ID


def test_the_supersede_is_explicit_and_the_history_is_preserved(
        decision, boundary, state):
    """History is superseded in the open, not rewritten: the merged
    discontinuation artifact keeps its own unresolved value, and both sides
    name the file, the key, the previous value and the resolved value."""
    marker = decision["superseded_marker"]
    assert marker["artifact"] == _DISC_BOUNDARY_REL
    assert marker["key"] == REPORTING_KEY
    assert marker["previous_value"] == SUPERSEDED_VALUE
    assert marker["resolved_value"] == DECISION_VALUE
    assert marker["supersede_scope"] == "this_single_reporting_marker_only"
    assert marker["historical_artifact_preserved_byte_for_byte"] is True
    assert boundary["manuscript_reporting_decision_previous_value"] == SUPERSEDED_VALUE
    assert boundary["manuscript_reporting_decision_supersedes_artifact"] == _DISC_BOUNDARY_REL
    assert boundary["manuscript_reporting_decision_supersedes_key"] == REPORTING_KEY
    assert boundary["prior_discontinuation_artifact_preserved_byte_for_byte"] is True
    assert boundary["prior_packages_modified_by_this_action"] is False
    # the superseded artifact itself still carries the historical value
    prior = _load(_DISC_BOUNDARY_REL)
    assert prior[REPORTING_KEY] == SUPERSEDED_VALUE
    assert prior["m4_block_disposition"] == DISC_STATUS
    # and the live Handoff publishes both the resolved value and its provenance
    assert state["stage129_m4_manuscript_reporting_decision_previous_value"] == SUPERSEDED_VALUE
    assert state["stage129_m4_manuscript_reporting_decision_supersedes_artifact"] == _DISC_BOUNDARY_REL
    assert state["stage129_m4_prior_discontinuation_artifact_preserved"] is True


# ---------------------------- 3/4/5. the comparison, the p-value, the null H0
def test_the_comparison_stays_not_executed(decision, boundary, state,
                                           roadmap_front_matter):
    assert decision["comparison_id"] == COMPARISON_ID
    assert decision["comparison_status"] == COMPARISON_STATUS
    assert boundary["m4_comparison_id"] == COMPARISON_ID
    assert boundary["m4_comparison_status"] == COMPARISON_STATUS
    assert state["stage129_m4_comparison_status"] == COMPARISON_STATUS
    assert roadmap_front_matter["m4_comparison_status"] == COMPARISON_STATUS
    # and this action did not move it
    assert boundary["m4_comparison_status_modified_by_this_action"] is False
    assert boundary["m4_block_disposition_modified_by_this_action"] is False
    assert boundary["m4_block_disposition"] == DISC_STATUS
    assert state["m4_block_disposition"] == DISC_STATUS


def test_the_p_value_stays_null(decision, boundary, state, roadmap_front_matter):
    assert decision["comparison_p_value"] is None
    assert boundary["m4_comparison_p_value"] is None
    assert state["stage129_m4_comparison_p_value"] is None
    assert roadmap_front_matter["m4_comparison_p_value"] == "null"
    # no numeric p may appear anywhere in this package's JSON values
    for name in os.listdir(_PKG):
        if not name.endswith(".json"):
            continue
        blob = _load(f"{_PKG_REL}/{name}")

        def walk(node, path=""):
            if isinstance(node, dict):
                for key, val in node.items():
                    assert not (key.endswith("p_value") and val is not None), \
                        f"{name}:{path}.{key} publishes a p-value"
                    walk(val, f"{path}.{key}")
            elif isinstance(node, list):
                for i, val in enumerate(node):
                    walk(val, f"{path}[{i}]")

        walk(blob)


def test_no_null_hypothesis_is_accepted_or_rejected(decision, boundary, state):
    assert decision["null_hypothesis_accepted_or_rejected"] is None
    assert boundary["m4_comparison_null_hypothesis_accepted_or_rejected"] is None
    assert state["stage129_m4_reporting_null_hypothesis_accepted_or_rejected"] is None
    assert boundary["confirmatory_holm_family_modified_by_this_action"] is False
    assert boundary["family_shrunk_post_hoc_after_observing_a_result"] is False
    assert state["stage129_m4_confirmatory_holm_family_modified"] is False
    assert state["stage129_m4_confirmatory_holm_family"] == [
        "M2_minus_M1", "M3_CBI_minus_M2", "M4_minus_M3_CBI"]
    assert state["stage129_m4_confirmatory_holm_family_executed"] is False
    # the comparison keeps its place in SAP history
    assert decision["comparison_removed_from_sap_history"] is False
    assert decision["comparison_renamed_or_substituted"] is False
    assert decision["sap_history_preserved"] is True
    assert state["stage129_m4_comparison_removed_from_sap_history"] is False
    assert state["stage129_m4_comparison_renamed_or_substituted"] is False


# ------------------------------------- 6. the formal Gate was never executed
def test_the_formal_gate_was_never_executed_and_no_verdict_is_forged(
        decision, boundary, state):
    assert decision["formal_m4_data_gate_executed"] is False
    assert decision["formal_m4_gate_verdict"] is None
    assert decision["is_a_formal_gate_failure"] is False
    assert decision["this_decision_is_not_a_gate_failure_declaration"] is True
    assert boundary["m4_data_gate_executed"] is False
    assert boundary["m4_formal_gate_verdict"] is None
    assert boundary["m4_coverage_calculated"] is False
    assert boundary["m4_data_gate_executable"] is False
    assert state["m4_data_gate_executed"] is False
    assert state["m4_formal_gate_verdict"] is None
    assert state["stage129_m4_reporting_is_formal_gate_failure"] is False
    assert state["stage129_m4_discontinuation_is_formal_gate_failure"] is False


def test_no_gate_verdict_vocabulary_is_published_by_this_package():
    """The README may NAME the vocabulary to explain why it is not used, so the
    JSON artifacts are checked value-by-value rather than by raw substring."""
    for name in os.listdir(_PKG):
        if not name.endswith(".json"):
            continue
        blob = _load(f"{_PKG_REL}/{name}")
        found = []

        def walk(node):
            if isinstance(node, dict):
                for key, val in node.items():
                    if key == "gate_verdict_vocabulary_deliberately_not_used":
                        continue          # the explicit not-used declaration
                    walk(val)
            elif isinstance(node, list):
                for val in node:
                    walk(val)
            elif isinstance(node, str) and node in GATE_VERDICT_VOCAB:
                found.append(node)

        walk(blob)
        assert found == [], f"{name} publishes Gate verdict vocabulary {found}"


# ------------------------- 7. no M4 modeling or evaluation ran or is allowed
def test_no_m4_execution_is_performed_or_authorized(decision, boundary, state):
    for field in ("m4_retrieval_continues", "m4_manual_completion_continues",
                  "m4_feature_materialization_authorized", "m4_modeling_will_run",
                  "m4_incremental_evaluation_will_run", "m4_block_admitted",
                  "m4_data_gate_authorized", "m4_reopening_authorized",
                  "final_test_access_authorized", "next_action_authorized",
                  "next_action_executes_m4", "paper_winner_selected",
                  "final_model_selected", "full_development_refit_executed",
                  "stage130_or_next_stage_executed"):
        assert boundary[field] is False, field
    assert boundary["m4_reopening_requires_new_human_authorization"] is True
    for field in ("m4_feature_materialization_authorized", "m4_modeling_will_run",
                  "m4_incremental_evaluation_will_run", "m4_block_admitted",
                  "m4_modeling_started", "m4_retrieval_continues",
                  "m4_manual_completion_continues", "m4_reopening_authorized"):
        assert state[field] is False, field
    assert state["m4_reopening_requires_new_human_authorization"] is True
    # the M4 pointer is not advanced, and neither live research chain moves
    assert boundary["next_action_id"] == "human_decision_required"
    assert boundary["pointer_is_not_authorization"] is True
    assert state["stage129_m4_next_action_id"] == "human_decision_required"
    assert state["stage129_m4_next_action_authorized"] is False
    assert state["next_research_action_id"] == "human-zenodo-draft-review-and-publication-decision"
    assert state["next_research_action_authorized"] is False
    assert state["stage128_m3_lag_wdi_next_action_id"] == "human_decision_required"


def test_nothing_was_computed_or_retrieved_by_this_action(boundary):
    counters = boundary["counters"]
    assert counters, "the boundary must enumerate what was not done"
    assert all(v == 0 for v in counters.values()), counters
    for key in ("extraction_reruns", "payloads_reinspected", "m4_observations_retrieved",
                "m4_features_materialized", "formal_gate_coverage_computations",
                "model_fits", "predictions", "bootstrap_executions",
                "holm_calculations", "shap_executions", "final_test_rows_read",
                "new_data_files_created"):
        assert counters[key] == 0, key


def test_prior_blocks_and_dispositions_are_untouched(boundary, state):
    for field in ("m1_status_modified_by_this_action",
                  "m2_status_modified_by_this_action",
                  "m2_retained_status_modified_by_this_action",
                  "m3_cbi_status_modified_by_this_action",
                  "m3_cbi_declared_successful_by_this_action",
                  "m3_lag_wdi_disposition_modified_by_this_action",
                  "m3_lag_wdi_promoted_to_confirmatory_model",
                  "observational_package_modified_by_this_action",
                  "observational_extraction_admitted_as_model_input"):
        assert boundary[field] is False, field
    assert boundary["observational_extraction_may_be_reported_in_limitations"] is True
    assert state["stage129_m4_m3_cbi_status_preserved"] == "UNRESOLVED_M3_DATA_GATE"
    assert state["stage129_m4_m3_lag_wdi_disposition_preserved"] == (
        "SUPPLEMENTARY_EXPLORATORY_ONLY")
    assert state["stage128_m3_lag_wdi_promoted_to_confirmatory_model"] is False


# --------------------------------------------------- 8. Final Test firewall
def test_final_test_stays_locked_with_zero_rows_read(decision, boundary, state):
    assert decision["final_test_locked"] is True
    assert decision["final_test_access_authorized"] is False
    assert decision["final_test_rows_read"] == 0
    assert boundary["final_test_locked"] is True
    assert boundary["final_test_rows_read"] == 0
    assert boundary["counters"]["final_test_rows_read"] == 0
    assert boundary["counters"]["final_test_target_values_read"] == 0
    assert boundary["counters"]["final_test_predictor_values_read"] == 0
    # MOVED from a live global proxy to action-scoped historical facts. The
    # live `final_test_rows_read` is 346 since the separately authorized
    # Stage129 Final Test pass, which happened AFTER this action. This
    # action's own zero is asserted above / below; the snapshot pins the
    # firewall state it ran under.
    assert state["final_test_prior_to_authorized_pass_rows_read"] == 0
    assert state["stage129_m4_final_test_rows_read"] == 0
    assert state["stage129_m4_reporting_final_test_rows_read"] == 0
    assert state["stage129_m4_final_test_locked"] is True


# ------------------------------------------- 9. the four candidates are frozen
def test_the_four_frozen_candidates_survive_unchanged(decision, state):
    assert decision["m4_candidate_count"] == 4
    assert decision["m4_candidate_set"] == CANDIDATES        # identity AND order
    assert decision["m4_candidate_count_changed_by_this_decision"] is False
    assert decision["m4_candidates_removed_or_renamed_by_this_decision"] is False
    assert decision["m4_candidates_substituted_by_this_decision"] is False
    assert state["stage129_m4_candidate_count_after_discontinuation"] == 4
    assert state["stage129_m4_candidate_set_after_discontinuation"] == CANDIDATES
    assert state["stage129_m4_candidates_removed_or_renamed"] is False
    # the ORIGINAL contract's candidate list is still intact and identical
    contract = _load("project/stage129/m4_governance_data_gate_contract/"
                     "stage129_m4_data_gate_contract.json")
    assert contract["candidate_set"]["candidates"] == CANDIDATES
    assert state["stage129_m4_candidate_set"] == CANDIDATES
    assert state["stage129_m4_candidate_count"] == 4


# -------------------- 10. the approved text exists and claims no executed result
def test_the_approved_english_and_persian_text_are_recorded(decision, state):
    en = decision["approved_manuscript_text_en"]
    fa = decision["approved_manuscript_text_fa"]
    assert en == APPROVED_EN
    assert fa.strip()
    assert state["stage129_m4_approved_manuscript_text_en"] == APPROVED_EN
    assert state["stage129_m4_approved_manuscript_text_fa"] == fa
    # the English text must say prespecified / not executed / no p / no inference
    for phrase in ("prespecified", "not admitted to modeling", "was not executed",
                   "no p-value was computed", "no inferential conclusion"):
        assert phrase in en, phrase
    # the Persian text must carry the same four commitments
    for phrase in ("از پیش تعریف شده", "اجرا نشد", "هیچ مقدار p محاسبه نشد",
                   "هیچ نتیجه استنباطی"):
        assert phrase in fa, phrase
    # and both appear in the package README
    readme = _text(f"{_PKG_REL}/README_STAGE129_M4_MANUSCRIPT_REPORTING_DECISION.md")
    assert "no inferential conclusion is drawn for M4" in readme
    assert "هیچ نتیجه استنباطی" in readme


def test_the_approved_text_never_claims_an_executed_result(decision, boundary,
                                                           state):
    forbidden = ("p =", "p-value of", "p<", "p >", "p <", "significant",
                 "outperform", "improved", "improvement", "we reject",
                 "we accept", "rejected the null", "accepted the null")
    for field in ("approved_manuscript_text_en", "approved_manuscript_text_fa"):
        lowered = decision[field].lower()
        for phrase in forbidden:
            assert phrase not in lowered, f"{field} contains {phrase!r}"
    assert decision["reporting_claims_an_executed_result"] is False
    assert decision["reporting_claims_m4_performance"] is False
    assert boundary["reporting_claims_an_executed_result"] is False
    assert boundary["reporting_claims_m4_performance"] is False
    assert state["stage129_m4_reporting_claims_an_executed_result"] is False
    assert state["stage129_m4_reporting_claims_m4_performance"] is False
    # the text is a reporting decision, NOT permission to write the manuscript
    assert decision["approved_text_status"] == (
        "APPROVED_REPORTING_TEXT_ONLY_NOT_A_MANUSCRIPT_WRITING_AUTHORIZATION")
    assert decision["approved_text_is_a_reporting_decision_not_a_writing_authorization"] is True
    assert boundary["manuscript_writing_or_rewriting_authorized"] is False
    assert state["stage129_m4_manuscript_writing_authorized"] is False


def test_the_reported_position_is_prespecified_but_not_executed(decision, state):
    assert decision["m4_was_prespecified"] is True
    assert decision["m4_was_stopped_before_admission_and_modeling"] is True
    assert decision["reporting_reason_class"] == (
        "data_accessibility_coverage_and_definition_mismatch")
    assert state["stage129_m4_reported_as_prespecified"] is True
    assert state["stage129_m4_reported_as_not_executed"] is True
    assert state["stage129_m4_reporting_reason_class"] == (
        "data_accessibility_coverage_and_definition_mismatch")


# ------------------------------------------------ 11. the generator fails closed
def _run_generator(root):
    """Import the canonical generator fresh and derive against ``root``."""
    import importlib
    gen = importlib.import_module("update_ai_handoff")
    return gen.derive_stage129_m4_manuscript_reporting_decision_markers(root)


@pytest.fixture
def sandbox(tmp_path):
    """A minimal repo tree carrying just the two Stage129 M4 packages."""
    for rel in (_PKG_REL, _DISC_REL):
        src = os.path.join(REPO_ROOT, rel)
        dst = tmp_path / rel
        dst.mkdir(parents=True, exist_ok=True)
        for name in os.listdir(src):
            with open(os.path.join(src, name), "rb") as fh:
                blob = fh.read()
            (dst / name).write_bytes(blob)
    return tmp_path


def _write(root, rel, blob):
    with open(os.path.join(root, rel), "w", encoding="utf-8") as fh:
        json.dump(blob, fh, ensure_ascii=False, indent=2, sort_keys=True)


def test_the_sandbox_baseline_derives_cleanly(sandbox):
    """The tamper tests below are only meaningful if the untampered copy passes."""
    markers = _run_generator(str(sandbox))
    assert markers[STATE_KEY] == DECISION_VALUE


@pytest.mark.parametrize("artifact_rel,key,value,needle", [
    # reverting the decision to unresolved
    (f"{_PKG_REL}/stage129_m4_manuscript_reporting_decision.json",
     REPORTING_KEY, SUPERSEDED_VALUE, "revert"),
    (f"{_PKG_REL}/stage129_m4_manuscript_reporting_governance_boundary.json",
     REPORTING_KEY, SUPERSEDED_VALUE, "revert"),
    # inventing a p-value for a comparison that was never executed
    (f"{_PKG_REL}/stage129_m4_manuscript_reporting_decision.json",
     "comparison_p_value", 0.03, "p-value"),
    (f"{_PKG_REL}/stage129_m4_manuscript_reporting_governance_boundary.json",
     "m4_comparison_p_value", 0.03, "p-value"),
    # resolving a null hypothesis that was never tested
    (f"{_PKG_REL}/stage129_m4_manuscript_reporting_decision.json",
     "null_hypothesis_accepted_or_rejected", "rejected", "null "),
    # forging a formal Gate verdict
    (f"{_PKG_REL}/stage129_m4_manuscript_reporting_decision.json",
     "formal_m4_gate_verdict", "FAIL_M4_DATA_GATE", "verdict"),
    (f"{_PKG_REL}/stage129_m4_manuscript_reporting_governance_boundary.json",
     "m4_formal_gate_verdict", "FAIL_M4_DATA_GATE", "verdict"),
    (f"{_PKG_REL}/stage129_m4_manuscript_reporting_decision.json",
     "formal_m4_data_gate_executed", True, "executed"),
    # publishing a Gate verdict as the reporting decision itself
    (f"{_PKG_REL}/stage129_m4_manuscript_reporting_governance_boundary.json",
     REPORTING_KEY, "FAIL_M4_DATA_GATE", ""),
    # moving the comparison, the disposition or the candidates
    (f"{_PKG_REL}/stage129_m4_manuscript_reporting_governance_boundary.json",
     "m4_comparison_status", "EXECUTED", "comparison"),
    (f"{_PKG_REL}/stage129_m4_manuscript_reporting_decision.json",
     "m4_candidate_set", ["audit_opinion_type"], "candidate"),
    (f"{_PKG_REL}/stage129_m4_manuscript_reporting_decision.json",
     "m4_candidate_count", 3, "candidate_count"),
    # unlocking the Final Test or authorizing M4 work
    (f"{_PKG_REL}/stage129_m4_manuscript_reporting_governance_boundary.json",
     "final_test_rows_read", 1, "final_test_rows_read"),
    (f"{_PKG_REL}/stage129_m4_manuscript_reporting_governance_boundary.json",
     "m4_modeling_will_run", True, "m4_modeling_will_run"),
    (f"{_PKG_REL}/stage129_m4_manuscript_reporting_governance_boundary.json",
     "m4_reopening_authorized", True, "m4_reopening_authorized"),
    (f"{_PKG_REL}/stage129_m4_manuscript_reporting_governance_boundary.json",
     "manuscript_writing_or_rewriting_authorized", True, "writing"),
    # claiming a result the study never produced
    (f"{_PKG_REL}/stage129_m4_manuscript_reporting_decision.json",
     "reporting_claims_an_executed_result", True, "reporting_claims"),
])
def test_the_generator_fails_closed_on_tampering(sandbox, artifact_rel, key,
                                                 value, needle):
    import update_ai_handoff as gen
    blob = json.loads((sandbox / artifact_rel).read_text(encoding="utf-8"))
    blob[key] = value
    _write(str(sandbox), artifact_rel, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert needle.lower() in str(exc.value).lower()


def test_the_generator_fails_closed_when_the_approved_text_claims_a_result(sandbox):
    import update_ai_handoff as gen
    rel = f"{_PKG_REL}/stage129_m4_manuscript_reporting_decision.json"
    blob = json.loads((sandbox / rel).read_text(encoding="utf-8"))
    blob["approved_manuscript_text_en"] = (
        "M4 was prespecified and significantly improved discrimination over "
        "M3-CBI.")
    _write(str(sandbox), rel, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "claims an executed result" in str(exc.value)


def test_the_generator_fails_closed_if_the_supersede_is_not_anchored(sandbox):
    """The supersede must be anchored on the REAL historical value. If the
    discontinuation artifact is quietly rewritten to already say the resolved
    value, the anchor is gone and the build must fail rather than pretend the
    decision was there all along."""
    import update_ai_handoff as gen
    blob = json.loads((sandbox / _DISC_BOUNDARY_REL).read_text(encoding="utf-8"))
    blob[REPORTING_KEY] = DECISION_VALUE
    _write(str(sandbox), _DISC_BOUNDARY_REL, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "byte-for-byte" in str(exc.value)


def test_the_generator_returns_nothing_before_the_package_exists(sandbox):
    os.remove(sandbox / _PKG_REL /
              "stage129_m4_manuscript_reporting_decision.json")
    assert _run_generator(str(sandbox)) == {}


# ---------------------------------------- 12. validator + semantic idempotency
def test_validate_ai_handoff_check_passes():
    proc = subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "project/scripts/validate_ai_handoff.py"),
         "--check"],
        cwd=REPO_ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_the_generator_is_semantically_idempotent():
    """Deriving twice must produce identical markers -- the reporting decision
    is a pure function of the committed artifacts."""
    import update_ai_handoff as gen
    first = gen.derive_stage129_m4_manuscript_reporting_decision_markers(REPO_ROOT)
    second = gen.derive_stage129_m4_manuscript_reporting_decision_markers(REPO_ROOT)
    assert first == second
    assert copy.deepcopy(first) == second
    assert first[STATE_KEY] == DECISION_VALUE


def test_current_state_renders_the_reporting_decision_without_a_result_claim():
    text = _text("project/docs/ai/CURRENT_STATE.md")
    assert DECISION_VALUE in text
    assert "M4 manuscript reporting decision" in text
    assert "no inferential conclusion is drawn for M4" in text
    for verdict in ("PASS_M4_DATA_GATE", "FAIL_M4_DATA_GATE"):
        assert verdict not in text, verdict


def test_roadmap_records_the_reporting_decision_without_a_new_scientific_stage(
        roadmap_front_matter):
    fm = roadmap_front_matter
    assert fm["m4_manuscript_reporting_decision_action_id"] == ACTION_ID
    assert fm["m4_manuscript_reporting_decision_previous_value"] == SUPERSEDED_VALUE
    assert fm["m4_manuscript_writing_authorized"] == "false"
    # the M4 pointer and BOTH live research pointers are unmoved
    assert fm["m4_next_action_id"] == "human_decision_required"
    assert fm["m4_next_action_authorized"] == "false"
    assert fm["next_research_action_id"] == "human-zenodo-draft-review-and-publication-decision"
    assert fm["next_research_action_authorized"] == "false"
    assert fm["m3_lag_wdi_next_action_id"] == "human_decision_required"
    assert fm["m4_block_disposition"] == DISC_STATUS
    body = _text("project/docs/ai/ROADMAP.md")
    assert ACTION_ID in body
    assert DECISION_VALUE in body
    # no pointer to retrieval, a Gate, modeling, the Final Test or Stage130
    for forbidden in ("stage129-m4-governance-data-gate", "stage130"):
        assert forbidden not in fm.get("m4_next_action_id", "")
        assert forbidden not in fm.get("next_research_action_id", "")


# ------------------------------------------- package hygiene: nothing new added
def test_no_new_data_or_metric_artifact_was_created():
    names = sorted(os.listdir(_PKG))
    assert names, "package must not be empty"
    for name in names:
        assert name.endswith((".json", ".md")), name
        assert not name.endswith((".csv", ".parquet", ".pkl", ".joblib")), name
    manifest = _load(f"{_PKG_REL}/"
                     "metadata_and_hashes_stage129_m4_manuscript_reporting_decision.json")
    assert manifest["m4_value_files_committed"] == 0
    assert manifest["model_artifacts_committed"] == 0
    assert manifest["final_test_artifacts_committed"] == 0
    assert manifest["new_data_files_created_by_this_action"] == 0
    assert manifest["formal_m4_data_gate_executed"] is False


def test_package_hash_manifest_matches_every_file():
    import hashlib
    rel = (f"{_PKG_REL}/"
           "metadata_and_hashes_stage129_m4_manuscript_reporting_decision.json")
    manifest = _load(rel)
    listed = set(manifest["package_files"])
    on_disk = {n for n in os.listdir(_PKG) if n != os.path.basename(rel)}
    assert listed == on_disk
    for name, info in manifest["package_files"].items():
        with open(os.path.join(_PKG, name), "rb") as fh:
            blob = fh.read()
        assert hashlib.sha256(blob).hexdigest() == info["sha256"], name
        assert len(blob) == info["bytes"], name


def test_the_merged_discontinuation_package_is_byte_for_byte_intact():
    """This action supersedes one marker. It may not edit the merged package."""
    import hashlib
    disc_manifest = _load(
        f"{_DISC_REL}/"
        "metadata_and_hashes_stage129_m4_human_discontinuation_data_inadequacy.json")
    for name, info in disc_manifest["package_files"].items():
        with open(os.path.join(REPO_ROOT, _DISC_REL, name), "rb") as fh:
            blob = fh.read()
        assert hashlib.sha256(blob).hexdigest() == info["sha256"], name
        assert len(blob) == info["bytes"], name
