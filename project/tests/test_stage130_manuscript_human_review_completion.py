"""Stage130 — the human manuscript review, recorded as COMPLETE.

This action is a REVIEW-COMPLETION RECORDING ONLY. These tests pin:

  * that the reviewed Head is exactly the commit the human read, and that the
    approved manuscript is byte-identical to it (SHA-256 *and* Git blob ID,
    both re-derived from the file rather than trusted from the artifact);
  * that the review is completed and no longer outstanding;
  * that submission readiness, Ready-for-Review, merge and `stage130_authorized`
    all remain False -- approving the TEXT authorizes none of them;
  * that the six human-supplied submission items are still outstanding and were
    not invented;
  * that the live next-action pointer moved OFF `human-manuscript-review`, and
    that the successor is a pointer and not a permission;
  * that the historical Phase 2 assembly semantics are preserved: the Phase 2
    deriver still publishes `human_review_required = True`,
    `human_review_completed = False` and its own historical pointer;
  * that the canonical generator is FAIL-CLOSED: editing the approved
    manuscript, rewriting the Phase 2 history, claiming submission readiness or
    reporting a non-zero action counter must all break the build.
"""
import copy
import hashlib
import importlib
import json
import os
import re
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "project", "scripts"))

_PKG_REL = "project/stage130/manuscript_human_review_completion"
_PKG = os.path.join(REPO_ROOT, _PKG_REL)
_DECISION_REL = f"{_PKG_REL}/stage130_manuscript_human_review_completion_decision.json"
_BOUNDARY_REL = f"{_PKG_REL}/stage130_manuscript_human_review_governance_boundary.json"
_MANIFEST_REL = (f"{_PKG_REL}/"
                 "metadata_and_hashes_stage130_manuscript_human_review_completion.json")
_MS_DIR_REL = "project/stage130/manuscript"
_MANUSCRIPT_REL = f"{_MS_DIR_REL}/manuscript_draft_en.md"

ACTION_ID = "stage130-manuscript-human-review-completion"
REVIEWED_HEAD = "c4136a412696c7bb626f0c389bcccb829f381629"
MANUSCRIPT_SHA256 = "8b5d861c36e01dc81133c1071cd96f7e340482ac2148b53c055369bbd5ffcb19"
MANUSCRIPT_BLOB_ID = "93f7e8e796ec098de38725271305ab06263efd1f"
SUPERSEDED_POINTER = "human-manuscript-review"
NEXT_POINTER = "human-manuscript-submission-metadata"
NEXT_POINTER_SCOPE = (
    "manuscript_human_submission_metadata_no_further_action_is_authorized")
OUTSTANDING_METADATA = [
    "authors_and_author_order",
    "affiliations_and_corresponding_author",
    "funding",
    "conflicts_of_interest",
    "ethics_and_data_governance_statement",
    "data_access_mechanism_for_the_restricted_company_panel",
]


def _load(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def _text(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def _blob_id(payload: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(payload) + payload).hexdigest()


@pytest.fixture(scope="module")
def decision():
    return _load(_DECISION_REL)


@pytest.fixture(scope="module")
def boundary():
    return _load(_BOUNDARY_REL)


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


# ------------------------------------------- 1. the reviewed Head is exact
def test_the_reviewed_head_is_the_authorized_commit(decision, boundary, state,
                                                    roadmap_front_matter):
    assert decision["reviewed_head_commit"] == REVIEWED_HEAD
    assert boundary["reviewed_head_commit"] == REVIEWED_HEAD
    assert state["stage130_manuscript_reviewed_head_commit"] == REVIEWED_HEAD
    assert roadmap_front_matter[
        "stage130_manuscript_reviewed_head_commit"] == REVIEWED_HEAD
    assert len(REVIEWED_HEAD) == 40
    assert all(c in "0123456789abcdef" for c in REVIEWED_HEAD)


def test_the_reviewed_head_is_a_real_commit_in_this_repository():
    """The approval names a commit that actually exists and actually carries
    the approved manuscript blob."""
    proc = subprocess.run(
        ["git", "cat-file", "-t", REVIEWED_HEAD],
        cwd=REPO_ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.strip() == "commit"
    proc = subprocess.run(
        ["git", "rev-parse", f"{REVIEWED_HEAD}:{_MANUSCRIPT_REL}"],
        cwd=REPO_ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.strip() == MANUSCRIPT_BLOB_ID


# --------------------------------------- 2. the approved manuscript is intact
def test_the_approved_manuscript_is_byte_identical(decision, boundary, state):
    with open(os.path.join(REPO_ROOT, _MANUSCRIPT_REL), "rb") as fh:
        payload = fh.read()
    assert hashlib.sha256(payload).hexdigest() == MANUSCRIPT_SHA256
    assert _blob_id(payload) == MANUSCRIPT_BLOB_ID
    for surface in (decision, boundary):
        assert surface["reviewed_manuscript_sha256"] == MANUSCRIPT_SHA256
        assert surface["reviewed_manuscript_blob_id"] == MANUSCRIPT_BLOB_ID
    assert decision["reviewed_manuscript_path"] == _MANUSCRIPT_REL
    assert state["stage130_manuscript_reviewed_sha256"] == MANUSCRIPT_SHA256
    assert state["stage130_manuscript_reviewed_blob_id"] == MANUSCRIPT_BLOB_ID
    assert state["stage130_manuscript_modified_by_this_action"] is False
    assert decision["manuscript_modified_by_this_decision"] is False
    assert boundary["manuscript_modified_by_this_action"] is False
    assert boundary["counters"]["manuscript_bytes_changed"] == 0


def test_the_manuscript_still_matches_the_commit_the_human_read():
    """Working-tree bytes and reviewed-commit bytes are the same object."""
    proc = subprocess.run(
        ["git", "hash-object", _MANUSCRIPT_REL],
        cwd=REPO_ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.strip() == MANUSCRIPT_BLOB_ID


# ------------------------------------------------- 3/4. completed, not required
def test_the_review_is_completed(decision, boundary, state,
                                 roadmap_front_matter):
    assert decision["human_review_completed"] is True
    assert boundary["human_review_completed"] is True
    assert state["stage130_phase2_human_review_completed"] is True
    assert roadmap_front_matter["stage130_phase2_human_review_completed"] == "true"
    assert state["stage130_manuscript_human_review_completion_recorded"] is True
    assert state["stage130_manuscript_human_review_completion_action_id"] == ACTION_ID
    assert state["stage130_manuscript_human_review_authorized_by_human"] is True
    assert decision["decision_id"] == ACTION_ID
    assert decision["decision_type"] == "human_manuscript_review_completion"
    assert decision["authorized_by_human"] is True
    assert decision["manuscript_content_approved"] is True
    assert boundary["manuscript_content_approved_by_human"] is True


def test_no_outstanding_review_requirement_remains(decision, boundary, state,
                                                   roadmap_front_matter):
    assert decision["human_review_required_after_this_decision"] is False
    assert boundary["human_review_required"] is False
    assert state["stage130_phase2_human_review_required"] is False
    assert roadmap_front_matter["stage130_phase2_human_review_required"] == "false"


# -------------------------------------- 5. history: it HAD been required
def test_the_historical_phase2_assembly_semantics_are_preserved(
        decision, boundary, state, roadmap_front_matter):
    """The Phase 2 record is superseded in the open, never rewritten."""
    import update_ai_handoff as gen
    prior = gen.derive_stage130_phase2_markers(REPO_ROOT)
    assert prior["stage130_phase2_human_review_required"] is True
    assert prior["stage130_phase2_human_review_completed"] is False
    assert prior["stage130_phase2_next_action_id"] == SUPERSEDED_POINTER
    assert prior["stage130_phase2_started"] is True
    assert prior["stage130_phase2_completed"] is True
    assert prior["stage130_phase2_presentation_only"] is True
    assert prior["stage130_phase2_scientific_execution_started"] is False
    # ...and the fact is published on the live surface as well
    assert state["stage130_phase2_human_review_was_required"] is True
    assert state["stage130_phase2_human_review_completed_previous_value"] is False
    assert state["stage130_phase2_assembly_record_preserved"] is True
    assert roadmap_front_matter["stage130_phase2_human_review_was_required"] == "true"
    assert decision["human_review_was_required_before_this_decision"] is True
    assert boundary["human_review_was_required"] is True
    assert boundary["prior_phase2_assembly_record_preserved"] is True
    assert boundary["prior_phase1_evidence_package_preserved"] is True
    assert boundary["prior_packages_modified_by_this_action"] is False


def test_the_supersede_is_explicit(decision, state):
    marker = decision["superseded_marker"]
    assert marker["key"] == "stage130_phase2_human_review_required"
    assert marker["previous_value"] is True
    assert marker["resolved_value"] is False
    assert marker["companion_key"] == "stage130_phase2_human_review_completed"
    assert marker["companion_previous_value"] is False
    assert marker["companion_resolved_value"] is True
    assert marker["pointer_previous_value"] == SUPERSEDED_POINTER
    assert marker["pointer_resolved_value"] == NEXT_POINTER
    assert marker["historical_phase2_assembly_record_preserved"] is True
    assert marker["superseding_decision_id"] == ACTION_ID
    assert state["stage130_manuscript_supersedes_key"] == (
        "stage130_phase2_human_review_required")
    assert state["stage130_manuscript_supersedes_pointer"] == SUPERSEDED_POINTER


# ------------------------------- 6/7. submission, Ready and Merge stay closed
def test_submission_readiness_remains_false(decision, boundary, state,
                                            roadmap_front_matter):
    assert decision["submission_ready"] is False
    assert boundary["submission_ready"] is False
    assert state["stage130_phase2_submission_ready"] is False
    assert roadmap_front_matter["stage130_phase2_submission_ready"] == "false"
    assert decision["approval_is_submission_authorization"] is False
    assert boundary["manuscript_text_approval_is_submission_authorization"] is False
    assert state["stage130_manuscript_review_is_submission_authorization"] is False
    assert boundary["submission_workflow_started"] is False
    assert state["stage130_manuscript_submission_workflow_started"] is False


def test_ready_for_review_and_merge_remain_unauthorized(decision, boundary,
                                                        state,
                                                        roadmap_front_matter):
    assert decision["ready_for_review_authorized"] is False
    assert decision["merge_authorized"] is False
    assert decision["approval_is_ready_for_review_authorization"] is False
    assert decision["approval_is_merge_authorization"] is False
    assert boundary["ready_for_review_authorized"] is False
    assert boundary["merge_authorized"] is False
    assert boundary["auto_merge_enabled_by_this_action"] is False
    assert boundary["branch_deleted_by_this_action"] is False
    assert boundary["pr_is_draft"] is True
    assert boundary["pr_merged"] is False
    assert state["stage130_phase2_ready_for_review_authorized"] is False
    assert state["stage130_phase2_merge_authorized"] is False
    assert state["stage130_authorized"] is False
    assert boundary["stage130_authorized"] is False
    for key in ("stage130_phase2_ready_for_review_authorized",
                "stage130_phase2_merge_authorized"):
        assert roadmap_front_matter[key] == "false"


def test_the_human_only_submission_metadata_was_not_invented(decision, boundary,
                                                             state):
    assert decision["outstanding_human_supplied_submission_metadata"] == \
        OUTSTANDING_METADATA
    assert decision["outstanding_human_supplied_submission_metadata_count"] == 6
    assert boundary["human_supplied_submission_metadata_outstanding"] is True
    assert state["stage130_manuscript_human_supplied_metadata_outstanding"] is True
    assert state[
        "stage130_manuscript_human_supplied_metadata_outstanding_count"] == 6
    assert state[
        "stage130_manuscript_human_supplied_metadata_outstanding_items"] == \
        OUTSTANDING_METADATA
    for field in ("author_names_supplied_by_this_decision",
                  "affiliations_supplied_by_this_decision",
                  "funding_supplied_by_this_decision",
                  "conflicts_of_interest_supplied_by_this_decision",
                  "ethics_statement_supplied_by_this_decision",
                  "data_access_mechanism_finalized_by_this_decision"):
        assert decision[field] is False, field
    for field in ("author_names_supplied_by_this_action",
                  "affiliations_supplied_by_this_action",
                  "funding_supplied_by_this_action",
                  "conflicts_of_interest_supplied_by_this_action",
                  "ethics_statement_supplied_by_this_action",
                  "data_access_mechanism_finalized_by_this_action"):
        assert boundary[field] is False, field
    # the manuscript still carries them as explicit placeholders
    manuscript = _text(_MANUSCRIPT_REL)
    assert "Metadata to be completed before submission" in manuscript
    assert manuscript.count("*[TO BE COMPLETED") >= 6


# ------------------------------------ 8. the live pointer moved off the review
def test_the_live_pointer_moved_off_the_completed_review(
        boundary, state, roadmap_front_matter):
    assert state["next_research_action_id"] == NEXT_POINTER
    assert state["next_research_action_id"] != SUPERSEDED_POINTER
    assert roadmap_front_matter["next_research_action_id"] == NEXT_POINTER
    assert roadmap_front_matter["next_research_action_id"] != SUPERSEDED_POINTER
    assert state["stage130_phase2_next_action_id"] == NEXT_POINTER
    assert boundary["next_action_id"] == NEXT_POINTER
    assert state["last_completed_research_action_id"] == SUPERSEDED_POINTER
    assert roadmap_front_matter[
        "last_completed_research_action_id"] == SUPERSEDED_POINTER


def test_the_pointer_is_not_an_authorization(boundary, state,
                                             roadmap_front_matter):
    assert state["next_research_action_authorized"] is False
    assert state["next_research_action_pointer_is_not_authorization"] is True
    assert state["next_research_action_scope"] == NEXT_POINTER_SCOPE
    assert state["stage130_phase2_next_action_authorized"] is False
    assert boundary["next_action_authorized"] is False
    assert boundary["next_action_scope"] == NEXT_POINTER_SCOPE
    assert boundary["pointer_is_not_authorization"] is True
    assert roadmap_front_matter["next_research_action_authorized"] == "false"
    assert roadmap_front_matter["next_research_action_scope"] == NEXT_POINTER_SCOPE


def test_the_roadmap_orders_the_new_pointer_after_the_completed_review():
    body = _text("project/docs/ai/ROADMAP.md")
    ids = re.findall(
        r"^\s*\d+[a-z]?\.\s+`([a-z0-9]+(?:-[a-z0-9]+)+)`", body, re.MULTILINE)
    assert SUPERSEDED_POINTER in ids
    assert NEXT_POINTER in ids
    assert ids.index(NEXT_POINTER) > ids.index(SUPERSEDED_POINTER)
    # the completed review keeps its own history in the ordered list
    assert "Until 2026-08-20 this was a POINTER ONLY item" in body
    assert ACTION_ID in body


# ---------------------------------------- 9. nothing scientific was performed
def test_nothing_scientific_was_performed(boundary, state):
    counters = boundary["counters"]
    assert counters, "the boundary must carry counters"
    for field, value in counters.items():
        assert value == 0, f"{field} must be 0, got {value}"
    for field in ("final_test_rows_read", "prediction_artifact_content_reads",
                  "model_fits", "predictions", "thresholds_derived",
                  "metrics_computed", "confidence_intervals_computed",
                  "bootstrap_replicates", "p_values_computed",
                  "holm_executions", "shap_executions"):
        assert counters[field] == 0, field
    assert boundary["final_test_locked"] is True
    assert boundary["final_test_access_authorized"] is False
    assert boundary["final_test_second_pass_authorized"] is False
    assert boundary["final_test_rows_read"] == 0
    assert boundary["new_scientific_analysis_performed"] is False
    assert boundary["scientific_execution_started"] is False
    assert boundary["stage130_or_next_stage_executed"] is False
    assert boundary["stage122_to_stage129_artifacts_modified_by_this_action"] is False
    assert state["stage130_phase2_final_test_rows_read"] == 0
    assert state["stage130_phase2_prediction_artifact_opened"] is False
    assert state["stage130_scientific_execution_started"] is False
    assert state["stage130_phase2_scientific_execution_started"] is False


# ----------------------------------------- 10. the generator fails closed
def _run_generator(root):
    gen = importlib.import_module("update_ai_handoff")
    return gen.derive_stage130_manuscript_human_review_completion_markers(root)


@pytest.fixture
def sandbox(tmp_path):
    """A minimal tree carrying the review package and the Phase 2 manuscript."""
    for rel in (_PKG_REL, _MS_DIR_REL):
        src = os.path.join(REPO_ROOT, rel)
        dst = tmp_path / rel
        dst.mkdir(parents=True, exist_ok=True)
        for name in os.listdir(src):
            path = os.path.join(src, name)
            if not os.path.isfile(path):
                continue
            with open(path, "rb") as fh:
                (dst / name).write_bytes(fh.read())
    return tmp_path


def _write(root, rel, blob):
    with open(os.path.join(root, rel), "w", encoding="utf-8") as fh:
        json.dump(blob, fh, ensure_ascii=False, indent=2, sort_keys=True)


def test_the_sandbox_baseline_derives_cleanly(sandbox):
    """The tamper tests below are only meaningful if the untampered copy passes."""
    markers = _run_generator(str(sandbox))
    assert markers["stage130_phase2_human_review_completed"] is True
    assert markers["stage130_manuscript_reviewed_head_commit"] == REVIEWED_HEAD


def test_the_generator_fails_closed_if_the_approved_manuscript_is_edited(sandbox):
    """An approval attaches to the bytes that were read. Editing the approved
    manuscript must break the build, never silently inherit the approval."""
    import update_ai_handoff as gen
    path = sandbox / _MANUSCRIPT_REL
    path.write_bytes(path.read_bytes() + b"\nAn unreviewed sentence.\n")
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "has changed since the human read it" in str(exc.value)


def test_the_generator_fails_closed_if_the_phase2_history_is_rewritten(sandbox,
                                                                       monkeypatch):
    """If Phase 2 stops publishing the historical `review required = True`,
    the supersede has lost its anchor and the build must fail."""
    import update_ai_handoff as gen
    real = gen.derive_stage130_phase2_markers

    def rewritten(root):
        markers = dict(real(root))
        markers["stage130_phase2_human_review_required"] = False
        return markers

    monkeypatch.setattr(gen, "derive_stage130_phase2_markers", rewritten)
    with pytest.raises(gen.HandoffError) as exc:
        gen.derive_stage130_manuscript_human_review_completion_markers(str(sandbox))
    assert "rewriting history" in str(exc.value)


@pytest.mark.parametrize("artifact_rel,key,value,needle", [
    # reverting the review to incomplete / still required
    (_DECISION_REL, "human_review_completed", False, "completed"),
    (_BOUNDARY_REL, "human_review_completed", False, "completed"),
    (_BOUNDARY_REL, "human_review_required", True, "human_review_required"),
    (_DECISION_REL, "human_review_required_after_this_decision", True,
     "outstanding review requirement"),
    # erasing the historical fact that review had been required
    (_DECISION_REL, "human_review_was_required_before_this_decision", False,
     "REQUIRED"),
    (_BOUNDARY_REL, "human_review_was_required", False, "REQUIRED"),
    (_BOUNDARY_REL, "prior_phase2_assembly_record_preserved", False,
     "prior_phase2_assembly_record_preserved"),
    # claiming submission readiness, Ready or Merge off a content approval
    (_DECISION_REL, "submission_ready", True, "submission"),
    (_BOUNDARY_REL, "submission_ready", True, "submission"),
    (_DECISION_REL, "ready_for_review_authorized", True, "ready_for_review"),
    (_BOUNDARY_REL, "ready_for_review_authorized", True, "ready_for_review"),
    (_DECISION_REL, "merge_authorized", True, "merge_authorized"),
    (_BOUNDARY_REL, "merge_authorized", True, "merge_authorized"),
    (_BOUNDARY_REL, "stage130_authorized", True, "stage130_authorized"),
    (_BOUNDARY_REL, "submission_workflow_started", True, "submission_workflow"),
    (_DECISION_REL, "approval_is_submission_authorization", True,
     "approval_is_submission_authorization"),
    # inventing human-only submission metadata
    (_DECISION_REL, "author_names_supplied_by_this_decision", True,
     "author_names_supplied"),
    (_BOUNDARY_REL, "author_names_supplied_by_this_action", True,
     "author_names_supplied"),
    (_BOUNDARY_REL, "human_supplied_submission_metadata_outstanding", False,
     "outstanding"),
    (_DECISION_REL, "outstanding_human_supplied_submission_metadata",
     ["authors_and_author_order"], "six outstanding"),
    # moving the manuscript or the reviewed head
    (_DECISION_REL, "manuscript_modified_by_this_decision", True,
     "manuscript_modified"),
    (_BOUNDARY_REL, "manuscript_modified_by_this_action", True,
     "manuscript_modified"),
    (_DECISION_REL, "reviewed_head_commit", "0" * 40, "reviewed head"),
    (_DECISION_REL, "reviewed_head_commit", "c4136a4", "40-hex"),
    (_DECISION_REL, "reviewed_manuscript_sha256", "0" * 64,
     "has changed since the human read it"),
    (_DECISION_REL, "reviewed_manuscript_blob_id", "0" * 40,
     "has changed since the human read it"),
    # keeping or forging the pointer
    (_BOUNDARY_REL, "next_action_id", SUPERSEDED_POINTER, "advance the pointer"),
    (_BOUNDARY_REL, "next_action_authorized", True, "next_action_authorized"),
    (_BOUNDARY_REL, "pointer_is_not_authorization", False,
     "pointer is not an authorization"),
    # unlocking the Final Test or reporting a computation
    (_BOUNDARY_REL, "final_test_rows_read", 1, "final_test_rows_read"),
    (_BOUNDARY_REL, "final_test_locked", False, "Final Test locked"),
    (_BOUNDARY_REL, "final_test_access_authorized", True,
     "final_test_access_authorized"),
    (_BOUNDARY_REL, "new_scientific_analysis_performed", True,
     "new_scientific_analysis_performed"),
    (_BOUNDARY_REL, "pr_merged", True, "pr_merged"),
    (_DECISION_REL, "pr_is_draft", False, "Draft"),
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


def test_the_generator_fails_closed_on_a_non_zero_counter(sandbox):
    import update_ai_handoff as gen
    blob = json.loads((sandbox / _BOUNDARY_REL).read_text(encoding="utf-8"))
    blob["counters"]["shap_executions"] = 1
    _write(str(sandbox), _BOUNDARY_REL, blob)
    with pytest.raises(gen.HandoffError) as exc:
        _run_generator(str(sandbox))
    assert "counters.shap_executions must be 0" in str(exc.value)


def test_the_generator_returns_nothing_before_the_package_exists(sandbox):
    os.remove(sandbox / _DECISION_REL)
    assert _run_generator(str(sandbox)) == {}


# --------------------------------- 11. validator, idempotency, rendered state
def test_validate_ai_handoff_check_passes():
    proc = subprocess.run(
        [sys.executable,
         os.path.join(REPO_ROOT, "project/scripts/validate_ai_handoff.py"),
         "--check"],
        cwd=REPO_ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_the_generator_is_semantically_idempotent():
    import update_ai_handoff as gen
    first = gen.derive_stage130_manuscript_human_review_completion_markers(REPO_ROOT)
    second = gen.derive_stage130_manuscript_human_review_completion_markers(REPO_ROOT)
    assert first == second
    assert copy.deepcopy(first) == second
    assert first["stage130_phase2_human_review_completed"] is True


def test_current_state_says_the_review_is_completed_not_required():
    text = _text("project/docs/ai/CURRENT_STATE.md")
    assert "Human review COMPLETED" in text
    assert "Human review REQUIRED" not in text
    assert "awaiting human review" not in text
    assert REVIEWED_HEAD in text
    assert MANUSCRIPT_SHA256 in text
    assert NEXT_POINTER in text
    # it must not claim anything the human did not authorize
    for forbidden in ("submission ready = True",
                      "ready-for-review = True",
                      "merge = True"):
        assert forbidden not in text, forbidden


# ------------------------------------------- package hygiene: nothing new added
def test_no_data_or_result_artifact_was_added():
    names = sorted(os.listdir(_PKG))
    assert names, "package must not be empty"
    for name in names:
        assert name.endswith((".json", ".md")), name
    manifest = _load(_MANIFEST_REL)
    assert manifest["action_id"] == ACTION_ID
    assert manifest["new_data_files_created_by_this_action"] == 0
    assert manifest["model_artifacts_committed"] == 0
    assert manifest["final_test_artifacts_committed"] == 0
    assert manifest["value_files_committed"] == 0
    assert manifest["manuscript_files_modified_by_this_action"] == 0
    assert manifest["submission_ready"] is False


def test_package_hash_manifest_matches_every_file():
    manifest = _load(_MANIFEST_REL)
    listed = set(manifest["package_files"])
    on_disk = {n for n in os.listdir(_PKG)
               if n != os.path.basename(_MANIFEST_REL)}
    assert listed == on_disk
    assert manifest["package_file_count"] == len(on_disk)
    for name, meta in manifest["package_files"].items():
        with open(os.path.join(_PKG, name), "rb") as fh:
            payload = fh.read()
        assert len(payload) == meta["bytes"], name
        assert hashlib.sha256(payload).hexdigest() == meta["sha256"], name


def test_the_human_decision_is_recorded_verbatim(decision):
    verbatim = decision["human_decision_verbatim"]
    assert REVIEWED_HEAD in verbatim
    assert "Draft" in verbatim
    assert "Ready" in verbatim
    assert "Merge" in verbatim
    assert decision["human_decision_translation"].strip()
    assert decision["decision_date_utc"] == "2026-08-20"
    assert decision["pr_number"] == 100


# ------------------------- 12. the live workstream label is not stale either
#: The workstream label that was true only while a human had not read the
#: draft. It survives as a generator/validator CONSTANT (history), but it may
#: no longer be the live value.
STALE_WORKSTREAM_ID = "stage130-phase2-manuscript-assembly-human-review"
STALE_WORKSTREAM_KEY = "stage130_phase2_manuscript_assembly_human_review"
WORKSTREAM_ID = "stage130-phase2-manuscript-submission-metadata"
WORKSTREAM_KEY = "stage130_phase2_manuscript_submission_metadata"


def test_the_live_workstream_is_no_longer_the_human_review_workstream(
        state, roadmap_front_matter):
    """A completed review makes the `…-human-review` label a stale claim."""
    assert roadmap_front_matter["active_research_workstream_id"] != \
        STALE_WORKSTREAM_ID
    assert state["active_workstream"] != STALE_WORKSTREAM_KEY
    assert roadmap_front_matter["active_research_workstream_id"] == WORKSTREAM_ID
    assert state["active_workstream"] == WORKSTREAM_KEY
    # the completed review is what makes it stale
    assert state["stage130_phase2_human_review_completed"] is True
    assert state["stage130_phase2_human_review_required"] is False


def test_the_workstream_label_aligns_with_the_submission_metadata_pointer(
        state, roadmap_front_matter):
    """The label and the pointer name the same pending thing."""
    assert state["next_research_action_id"] == NEXT_POINTER
    assert WORKSTREAM_ID.endswith("manuscript-submission-metadata")
    assert NEXT_POINTER.endswith("manuscript-submission-metadata")
    assert roadmap_front_matter["next_research_action_scope"] == NEXT_POINTER_SCOPE
    assert "submission_metadata" in NEXT_POINTER_SCOPE


def test_the_workstream_label_is_not_an_authorization(state,
                                                      roadmap_front_matter):
    """Renaming a state description may not grant the action it describes."""
    assert state["next_research_action_authorized"] is False
    assert state["next_research_action_pointer_is_not_authorization"] is True
    assert state["stage130_phase2_next_action_authorized"] is False
    assert state["stage130_phase2_submission_ready"] is False
    assert state["stage130_phase2_ready_for_review_authorized"] is False
    assert state["stage130_phase2_merge_authorized"] is False
    assert state["stage130_authorized"] is False
    assert state["stage130_manuscript_submission_workflow_started"] is False
    assert state["stage130_manuscript_human_supplied_metadata_outstanding"] is True
    for key in ("next_research_action_authorized",
                "stage130_phase2_submission_ready",
                "stage130_phase2_ready_for_review_authorized",
                "stage130_phase2_merge_authorized"):
        assert roadmap_front_matter[key] == "false", key


def test_roadmap_and_generated_handoff_representations_agree(
        state, roadmap_front_matter):
    """ROADMAP is the input, the Handoff is derived; they must not diverge."""
    import update_ai_handoff as gen
    assert state["active_workstream"] == \
        roadmap_front_matter["active_research_workstream_id"].replace("-", "_")
    assert gen._STAGE130_SUBMISSION_METADATA_WORKSTREAM_ID == WORKSTREAM_ID
    # ...and the independent Stage126 current-state validator agrees, derived
    # from the committed artifacts rather than from the Handoff it validates
    sys.path.insert(0, os.path.join(REPO_ROOT, "project", "src"))
    import stage126_current_state_validator as csv_mod
    from pathlib import Path
    assert csv_mod.stage130_human_review_completed(Path(REPO_ROOT)) is True
    assert csv_mod.expected_active_workstream(Path(REPO_ROOT)) == WORKSTREAM_KEY
    assert csv_mod.STAGE130_SUBMISSION_METADATA_ACTIVE_WORKSTREAM == WORKSTREAM_KEY
    assert csv_mod.current_state_labels_are_not_stale(
        state, freeze_completed=True) is True
    # the rendered snapshot says the same thing
    text = _text("project/docs/ai/CURRENT_STATE.md")
    assert f"- **Active workstream:** `{WORKSTREAM_KEY}`" in text
    assert STALE_WORKSTREAM_KEY not in text
    # and the historical constants survive, unmoved
    assert gen._STAGE130_P2_WORKSTREAM_ID == STALE_WORKSTREAM_ID
    assert csv_mod.STAGE130_P2_ACTIVE_WORKSTREAM == STALE_WORKSTREAM_KEY


def test_the_generator_fails_closed_on_a_stale_live_workstream(sandbox,
                                                               monkeypatch):
    """The staleness guard must REFUSE the old label once review is complete.

    This is the fail-closed half: it is not enough that the label was updated
    by hand — a ROADMAP that still advertises the human-review workstream must
    break the build.
    """
    import update_ai_handoff as gen
    monkeypatch.setattr(
        gen, "read_roadmap",
        lambda root: {"active_research_workstream_id": STALE_WORKSTREAM_ID})
    monkeypatch.setattr(
        gen, "derive_stage130_manuscript_human_review_completion_markers",
        lambda root: {"stage130_manuscript_human_review_completion_recorded": True})
    with pytest.raises(gen.HandoffError) as exc:
        gen.derive_stage128_m2_d2_design_freeze_markers(REPO_ROOT)
    assert STALE_WORKSTREAM_ID in str(exc.value)
    assert WORKSTREAM_ID in str(exc.value)


def test_the_independent_validator_fails_closed_on_a_stale_live_workstream(
        state):
    """Same refusal, from the independent current-state validator."""
    sys.path.insert(0, os.path.join(REPO_ROOT, "project", "src"))
    import stage126_current_state_validator as csv_mod
    stale = dict(state)
    stale["active_workstream"] = STALE_WORKSTREAM_KEY
    assert csv_mod.current_state_labels_are_not_stale(
        stale, freeze_completed=True) is False
    # ...and it still accepts the truthful label
    assert csv_mod.current_state_labels_are_not_stale(
        dict(state), freeze_completed=True) is True


def test_the_validator_recognizer_fails_closed_on_a_permission_claim(tmp_path):
    """The label may never be reached by a decision that claims a permission."""
    sys.path.insert(0, os.path.join(REPO_ROOT, "project", "src"))
    import stage126_current_state_validator as csv_mod
    from pathlib import Path
    rel = csv_mod.STAGE130_REVIEW_COMPLETION_DECISION_REL
    for field in ("submission_ready", "ready_for_review_authorized",
                  "merge_authorized", "approval_is_submission_authorization"):
        dst = tmp_path / field
        (dst / os.path.dirname(rel)).mkdir(parents=True, exist_ok=True)
        blob = _load(rel)
        blob[field] = True
        with open(dst / rel, "w", encoding="utf-8") as fh:
            json.dump(blob, fh, ensure_ascii=False, indent=2, sort_keys=True)
        with pytest.raises(csv_mod.ValidationFail) as exc:
            csv_mod.stage130_human_review_completed(dst)
        assert field in str(exc.value)
