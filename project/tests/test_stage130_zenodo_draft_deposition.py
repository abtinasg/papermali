"""Stage130 — the human-executed Zenodo DRAFT deposition (rc.3).

Recording only. A human supervisor created a deposition, uploaded the rc.3
archive into it and reserved a DOI. Nothing was published, nothing was
submitted, and this suite exists so that distinction cannot quietly erode.

These tests pin:

  * that a deposition was created and a file uploaded, and that the record is
    nevertheless `submitted = false` / `state = unsubmitted` — a private draft;
  * that the DOI is RESERVED and never described as published, registered,
    active, resolving or publicly available;
  * that `access_right = open` is recorded as DRAFT metadata and is explicitly
    NOT public availability, on every surface and in prose;
  * that the deposited bytes are the SAME bytes the Release Candidate package
    documents for rc.3 — filename, size, SHA-256 and MD5 — and that a drifted
    local archive breaks the build instead of being followed;
  * that rc.1, rc.2 and rc.3 are byte-identical to their recorded digests and
    that no archive was rebuilt, renamed or deleted;
  * that the approved manuscript is byte-identical and the Data Availability
    Statement is untouched, because no public DOI exists;
  * that no token, credential, `Authorization` header or deposition state file
    entered Git — checked by sweeping the package and the branch diff, not by
    trusting a boolean;
  * that this action made no Zenodo API call and specifically no publish call,
    and did not re-execute the deposition script;
  * that Ready-for-Review, merge, submission readiness and public release all
    remain false and PR #100 stays a Draft;
  * that the Release Candidate's own record still publishes every Zenodo key as
    false with a null DOI — history superseded in the open, never rewritten;
  * and that the generator is FAIL-CLOSED: claiming publication, submission, a
    resolving DOI, a changed manuscript, a different deposited digest, a
    non-zero counter or a committed credential must each break the build.
"""
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "project", "scripts"))

import update_ai_handoff as gen  # noqa: E402

ACTION_ID = "stage130-zenodo-draft-deposition"
PKG_REL = "project/stage130/zenodo_draft_deposition"
DECISION_REL = f"{PKG_REL}/stage130_zenodo_draft_deposition_decision.json"
BOUNDARY_REL = (f"{PKG_REL}/"
                "stage130_zenodo_draft_deposition_governance_boundary.json")
METADATA_REL = (f"{PKG_REL}/"
                "metadata_and_hashes_stage130_zenodo_draft_deposition.json")
README_REL = f"{PKG_REL}/README_STAGE130_ZENODO_DRAFT_DEPOSITION.md"

RC_PKG_REL = "project/stage130/dataset_release_candidate"
RC_METADATA_REL = (f"{RC_PKG_REL}/"
                   "metadata_and_hashes_stage130_dataset_release_candidate.json")

#: The observed Zenodo state, restated independently of both the artifacts and
#: the generator so a silent edit to either cannot also edit the expectation.
DEPOSITION_ID = 22059238
RESERVED_DOI = "10.5281/zenodo.22059238"
RECORD_STATE = "unsubmitted"
FILENAME = "tse_financial_distress_dataset_1392_1402_release_candidate_rc3.zip"
SHA256 = "4adb32bd675fd9181d8ced783b6734382e9749c6c574e35567d1bec65fd72f70"
MD5 = "cbd3df6c75053ee6d0641f19d5301d7a"
SIZE_BYTES = 11824690
RELEASE_VERSION = "1.0.0-rc.3"
DEPOSITION_METADATA = {
    "access_right": "open",
    "language": "eng",
    "license": "cc-by-4.0",
    "upload_type": "dataset",
    "version": RELEASE_VERSION,
}
V6_SHA256 = {
    "test_zenodo_rc3_draft.sh":
        "84121f3d9c000a8d646975361a942f4402337248c2ae4c4c13c676988d943fd3",
    "zenodo_draft_metadata_rc3.json":
        "3cb1cc05f41c3b0d9ec9e16d3474290caeccfff8423d1a60cdc0324b7840c375",
    "zenodo_rc3_draft.sh":
        "b2f6e4feaae3ebd6a94d39c27f23aff015d9fec1568a60454b994696efafef35",
}

#: The pointer this action supersedes, and the human step it advances to.
SUPERSEDED_POINTER = "human-dataset-release-candidate-digest-review"
NEXT_POINTER = "human-zenodo-draft-review-and-publication-decision"
NEXT_POINTER_SCOPE = (
    "zenodo_draft_human_review_and_separate_publication_decision_no_publish_"
    "action_is_authorized")
#: What is live NOW. This action's own successor named TWO separable human
#: things -- review the draft, then decide about publication. A later action
#: completed the review half (and recorded the human's own metadata-only Notes
#: correction), so the live pointer names only the decision that is left.
#: Assertions about this action's OWN artifacts keep the values above;
#: assertions about CURRENT repository state use these.
LIVE_POINTER = "human-zenodo-publication-decision"
LIVE_POINTER_SCOPE = (
    "zenodo_publication_decision_only_no_publication_action_is_"
    "authorized")
LIVE_LAST_COMPLETED_ACTION = "stage130-zenodo-draft-human-review-completion"

MANUSCRIPT_REL = "project/stage130/manuscript/manuscript_draft_en.md"
MANUSCRIPT_SHA256 = (
    "8b5d861c36e01dc81133c1071cd96f7e340482ac2148b53c055369bbd5ffcb19")
MANUSCRIPT_BLOB_ID = "93f7e8e796ec098de38725271305ab06263efd1f"

#: The three release candidates, oldest first, with the local build path each
#: was written to. The archives are gitignored, so a fresh clone legitimately
#: lacks them: absence is tolerated, drift never is.
RELEASE_ARCHIVES = (
    {
        "version": "1.0.0-rc.1",
        "rel": f"{RC_PKG_REL}/build/"
               "tse_financial_distress_dataset_1392_1402_release_candidate.zip",
        "sha256":
            "6649074290c5937066168e326b4e9c043f775c974edf2fb5b9c14ca452d25e45",
        "size_bytes": 11657151,
    },
    {
        "version": "1.0.0-rc.2",
        "rel": f"{RC_PKG_REL}/build/rc2/tse_financial_distress_dataset_1392_"
               "1402_release_candidate_rc2.zip",
        "sha256":
            "d82b747a2e96f09cfa8b1a0118e6e7664cf83b469707409816a0b6dbd8127373",
        "size_bytes": 11808267,
    },
    {
        "version": "1.0.0-rc.3",
        "rel": f"{RC_PKG_REL}/build/rc3/{FILENAME}",
        "sha256": SHA256,
        "size_bytes": SIZE_BYTES,
    },
)


def _load(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def _text(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def decision():
    return _load(DECISION_REL)


@pytest.fixture(scope="module")
def boundary():
    return _load(BOUNDARY_REL)


@pytest.fixture(scope="module")
def metadata():
    return _load(METADATA_REL)


@pytest.fixture(scope="module")
def markers():
    return gen.derive_stage130_zenodo_draft_deposition_markers(REPO_ROOT)


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
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip()
    return fm


def _clone_repo_shim(tmp_path):
    """A minimal tree the deriver can read: both Stage130 packages, the
    manuscript, and the Stage125 inputs the Release Candidate deriver needs."""
    root = tmp_path / "repo"
    shutil.copytree(os.path.join(REPO_ROOT, "project"), root / "project",
                    ignore=shutil.ignore_patterns("__pycache__", ".venv"))
    return root


def _write_json(root, rel, payload):
    path = os.path.join(str(root), rel)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False, sort_keys=True)


# --------------------------------------------------------------------------- #
# A draft exists — and a draft is all that exists
# --------------------------------------------------------------------------- #

def test_the_deposition_was_created_and_the_file_uploaded(boundary, markers):
    assert boundary["zenodo_deposition_created"] is True
    assert boundary["zenodo_upload_performed"] is True
    assert markers["zenodo_deposition_created"] is True
    assert markers["zenodo_upload_performed"] is True


def test_the_record_is_unsubmitted(decision, boundary, markers):
    for source in (decision, boundary):
        assert source["record_state"] == RECORD_STATE
        assert source["record_submitted"] is False
        assert source["record_is_private_draft"] is True
    assert boundary["zenodo_record_submitted"] is False
    assert markers["zenodo_record_submitted"] is False
    assert markers["zenodo_record_state"] == RECORD_STATE
    assert markers["zenodo_record_is_private_draft"] is True


def test_the_doi_is_reserved_and_not_published(decision, boundary, markers):
    for source in (decision, boundary):
        assert source["doi_reserved"] is True
        assert source["doi_published"] is False
        assert source["reserved_doi"] == RESERVED_DOI
        assert source["reserved_doi_is_registered_or_resolving"] is False
    assert decision["doi_active"] is False
    assert decision["doi_resolves_publicly"] is False
    assert markers["zenodo_doi_reserved"] is True
    assert markers["zenodo_doi"] == RESERVED_DOI
    assert markers["zenodo_doi_published"] is False
    assert markers["zenodo_published"] is False
    assert markers["zenodo_doi_registered_or_resolving"] is False


def test_public_release_is_still_false(decision, boundary, markers):
    for source in (decision, boundary):
        assert source["public_release"] is False
        assert source["public_release_authorized"] is False
        assert source["publication_authorized"] is False
    assert markers["zenodo_public_release"] is False
    assert markers["public_release_authorized"] is False
    assert markers["zenodo_publication_authorized"] is False


def test_the_reserved_doi_carries_the_deposition_id(decision, boundary):
    assert decision["deposition_id"] == DEPOSITION_ID
    assert boundary["deposition_id"] == DEPOSITION_ID
    assert RESERVED_DOI.endswith(str(DEPOSITION_ID))


# --------------------------------------------------------------------------- #
# `access_right = open` is not public availability
# --------------------------------------------------------------------------- #

def test_the_verified_metadata_is_recorded_exactly(decision, markers):
    assert decision["verified_metadata"] == DEPOSITION_METADATA
    assert markers["stage130_zenodo_deposition_metadata"] == DEPOSITION_METADATA


def test_open_access_right_is_declared_draft_metadata(decision, boundary,
                                                      markers):
    for source in (decision, boundary):
        assert source[
            "access_right_open_is_draft_metadata_not_public_availability"
        ] is True
    assert markers["stage130_zenodo_access_right"] == "open"
    assert markers["stage130_zenodo_access_right_is_public_availability"] \
        is False


def test_the_package_explains_the_distinction_in_words(decision):
    explanation = decision["why_open_access_right_is_not_public_availability"]
    assert "draft" in explanation.lower()
    assert "not" in explanation.lower()
    assert decision["why_this_is_not_a_publication"]


#: Availability cues. A sentence carrying one of these is making a statement
#: about whether the record can be reached, so it must be a NEGATIVE one: the
#: record is a private, unsubmitted draft.
AVAILABILITY_CUES = (
    "publicly available", "public availability", "openly available",
    "available for download", "downloadable", "resolves", "resolving",
    "citable", "discoverable", "indexed",
)
NEGATION_CUES = (
    "not", "never", "no ", "none", "cannot", "n/a", "false", "unsubmitted",
    "would", "if it", "private", "nor ", "placeholder", "must ", "may ",
)
#: Affirmative phrasings that cannot occur inside a negation.
FORBIDDEN_AFFIRMATIONS = (
    "is publicly available",
    "are publicly available",
    "is now public",
    "the doi resolves to",
    "the doi is active",
    "has been published on zenodo",
    "the record is public and citable",
)


def test_no_surface_affirms_public_availability():
    for rel in (DECISION_REL, BOUNDARY_REL, METADATA_REL, README_REL):
        text = _text(rel).lower()
        for phrase in FORBIDDEN_AFFIRMATIONS:
            assert phrase not in text, f"{rel} contains {phrase!r}"


def _availability_units(rel):
    """Every unit of meaning in a package file, as text.

    JSON is walked structurally — each field becomes `name: value`, and each
    string value is split into sentences — so a flag and its name are judged
    together. Markdown is normalized paragraph-first, because a wrapped bullet
    is one sentence, not two.
    """
    units = []
    if rel.endswith(".json"):
        def walk(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    label = key.replace("_", " ")
                    if isinstance(value, (dict, list)):
                        units.append(label)
                    else:
                        units.append(f"{label}: {value}")
                    walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)
            elif isinstance(node, str):
                units.extend(re.split(r"(?<=[.!?])\s+", node))
        walk(_load(rel))
        return units
    for block in re.split(r"\n\s*\n", _text(rel)):
        block = " ".join(block.split())
        units.extend(re.split(r"(?<=[.!?])\s+", block))
    return units


@pytest.mark.parametrize("rel", [DECISION_REL, BOUNDARY_REL, METADATA_REL,
                                 README_REL])
def test_every_availability_statement_is_a_negative_one(rel):
    """A sentence may mention availability only to deny it.

    Booleans are easy to keep truthful; prose is where a draft quietly becomes
    a release. Any unit carrying an availability cue must also carry a
    negation, so no paragraph and no field can assert what the flags deny.
    """
    seen = 0
    for raw in _availability_units(rel):
        unit = raw.strip().lower()
        if not unit or not any(cue in unit for cue in AVAILABILITY_CUES):
            continue
        seen += 1
        assert any(cue in unit for cue in NEGATION_CUES), \
            f"{rel}: unnegated availability claim -> {raw.strip()[:160]!r}"
    assert seen, f"{rel} makes no availability statement at all"


# --------------------------------------------------------------------------- #
# The deposited bytes are the documented candidate's
# --------------------------------------------------------------------------- #

def test_the_deposited_file_is_the_recorded_release_candidate(decision,
                                                              boundary):
    assert decision["deposited_file"] == {
        "filename": FILENAME,
        "md5": MD5,
        "sha256": SHA256,
        "size_bytes": SIZE_BYTES,
    }
    assert boundary["deposited_file_name"] == FILENAME
    assert boundary["deposited_file_sha256"] == SHA256
    assert boundary["deposited_file_md5"] == MD5
    assert boundary["deposited_file_size_bytes"] == SIZE_BYTES
    assert decision["deposited_file_is_the_recorded_release_candidate"] is True


def test_the_release_candidate_package_publishes_the_same_digest():
    rc = _load(RC_METADATA_REL)
    assert rc["archive_name"] == FILENAME
    assert rc["archive_sha256"] == SHA256
    assert rc["archive_size_bytes"] == SIZE_BYTES


@pytest.mark.parametrize("archive", RELEASE_ARCHIVES,
                         ids=[a["version"] for a in RELEASE_ARCHIVES])
def test_every_release_candidate_archive_is_byte_identical(archive):
    path = os.path.join(REPO_ROOT, archive["rel"])
    if not os.path.isfile(path):
        pytest.skip(f"{archive['version']} archive is gitignored and absent")
    with open(path, "rb") as fh:
        payload = fh.read()
    assert len(payload) == archive["size_bytes"], archive["version"]
    assert hashlib.sha256(payload).hexdigest() == archive["sha256"], \
        archive["version"]


def test_the_rc3_archive_also_matches_the_recorded_md5():
    path = os.path.join(REPO_ROOT, RELEASE_ARCHIVES[-1]["rel"])
    if not os.path.isfile(path):
        pytest.skip("rc.3 archive is gitignored and absent")
    with open(path, "rb") as fh:
        assert hashlib.md5(fh.read()).hexdigest() == MD5


def test_no_release_candidate_archive_is_tracked_in_git():
    tracked = subprocess.run(
        ["git", "ls-files", f"{RC_PKG_REL}/build"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout
    assert tracked.strip() == ""


# --------------------------------------------------------------------------- #
# Provenance: a human did this, and the programmer did not go and check
# --------------------------------------------------------------------------- #

def test_the_facts_were_supplied_by_the_human(decision, boundary, markers):
    assert decision["supplied_by"] == "human"
    assert decision["submitted_by"] == "human"
    for source in (decision, boundary):
        assert source["authenticated_zenodo_response_observed"] is True
        assert source["independently_retrieved_by_programmer"] is False
    assert markers["stage130_zenodo_facts_supplied_by"] == "human"
    assert markers["stage130_zenodo_authenticated_response_observed"] is True
    assert markers["stage130_zenodo_independently_retrieved_by_programmer"] \
        is False


def test_recording_the_event_is_not_authorizing_it(decision):
    assert decision["recording_is_not_retroactive_authorization"] is True
    assert decision["preexisting_pointer_at_execution_time"] == \
        SUPERSEDED_POINTER
    assert decision["preexisting_pointer_was_authorized"] is False


def test_the_v6_artifacts_are_pinned_by_digest(decision, markers):
    assert decision["v6_artifact_sha256"] == V6_SHA256
    assert markers["stage130_zenodo_v6_artifact_sha256"] == V6_SHA256


# --------------------------------------------------------------------------- #
# No Zenodo call, no script re-run, no token
# --------------------------------------------------------------------------- #

def test_no_zenodo_api_call_was_made_by_this_action(decision, boundary,
                                                    markers):
    assert decision["agent_called_the_zenodo_api"] is False
    assert boundary["agent_called_the_zenodo_api"] is False
    assert boundary["zenodo_publish_endpoint_called"] is False
    assert boundary["counters"]["zenodo_api_calls_made_by_this_action"] == 0
    assert boundary["counters"]["zenodo_publish_endpoint_calls"] == 0
    assert markers["stage130_zenodo_api_called_by_this_action"] is False
    assert markers["stage130_zenodo_publish_endpoint_called"] is False


def test_the_deposition_script_was_not_re_executed(decision, boundary,
                                                   markers):
    assert decision["deposition_script_re_executed_by_this_action"] is False
    assert boundary["deposition_script_re_executed_by_this_action"] is False
    assert markers["stage130_zenodo_script_re_executed_by_this_action"] is False


def test_no_token_was_read_or_requested(boundary, markers):
    assert boundary["zenodo_token_read_or_requested_by_this_action"] is False
    assert boundary["counters"]["zenodo_tokens_read_or_requested"] == 0
    assert markers["stage130_zenodo_token_read_or_requested"] is False


def test_the_deposition_state_file_is_not_in_git(decision, boundary):
    assert decision["deposition_state_file_committed_to_git"] is False
    assert boundary["deposition_state_file_committed_to_git"] is False
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=REPO_ROOT,
        capture_output=True, text=True, check=True).stdout.splitlines()
    for path in tracked:
        assert not path.endswith(".zenodo_rc3_deposition.state"), path
        assert "deposition.state" not in os.path.basename(path), path


def test_no_credential_material_is_committed_in_the_package():
    # the generator's own sweep, run against the real tree
    gen._stage130_zdd_assert_no_credential_material(REPO_ROOT)


def test_no_credential_material_is_in_the_branch_diff():
    base = subprocess.run(
        ["git", "merge-base", "HEAD", "origin/main"], cwd=REPO_ROOT,
        capture_output=True, text=True)
    if base.returncode != 0 or not base.stdout.strip():
        pytest.skip("origin/main is not available in this checkout")
    diff = subprocess.run(
        ["git", "diff", f"{base.stdout.strip()}...HEAD"], cwd=REPO_ROOT,
        capture_output=True, text=True, check=True).stdout
    for pattern in gen._STAGE130_ZDD_CREDENTIAL_PATTERNS:
        assert not pattern.search(diff), pattern.pattern
    added = "\n".join(line for line in diff.splitlines()
                      if line.startswith("+"))
    for run in gen._STAGE130_ZDD_OPAQUE_RUN.findall(added):
        assert re.fullmatch(r"[0-9a-fA-F]+", run), run


# --------------------------------------------------------------------------- #
# The manuscript did not move
# --------------------------------------------------------------------------- #

def test_the_manuscript_is_byte_identical(boundary, markers):
    path = os.path.join(REPO_ROOT, MANUSCRIPT_REL)
    with open(path, "rb") as fh:
        payload = fh.read()
    assert hashlib.sha256(payload).hexdigest() == MANUSCRIPT_SHA256
    assert gen._git_blob_id(payload) == MANUSCRIPT_BLOB_ID
    assert boundary["reviewed_manuscript_path"] == MANUSCRIPT_REL
    assert boundary["reviewed_manuscript_sha256"] == MANUSCRIPT_SHA256
    assert boundary["reviewed_manuscript_blob_id"] == MANUSCRIPT_BLOB_ID
    assert boundary["manuscript_modified_by_this_action"] is False
    assert markers["stage130_manuscript_modified_by_this_action"] is False


def test_the_data_availability_statement_was_not_changed(decision, boundary,
                                                         markers):
    assert decision[
        "manuscript_data_availability_statement_changed_by_this_decision"] \
        is False
    assert decision["manuscript_availability_claim_changed_by_this_decision"] \
        is False
    assert boundary["manuscript_availability_claim_changed_by_this_action"] \
        is False
    assert markers["stage130_manuscript_availability_claim_changed"] is False
    assert markers["stage130_manuscript_requires_post_doi_metadata_update"] \
        is True
    assert markers["stage130_manuscript_requires_post_doi_human_review"] is True


def test_the_manuscript_blob_is_unchanged_against_git():
    blob = subprocess.run(
        ["git", "rev-parse", f"HEAD:{MANUSCRIPT_REL}"], cwd=REPO_ROOT,
        capture_output=True, text=True, check=True).stdout.strip()
    assert blob == MANUSCRIPT_BLOB_ID


# --------------------------------------------------------------------------- #
# Ready, merge and the Draft PR
# --------------------------------------------------------------------------- #

def test_ready_for_review_and_merge_stay_false(decision, boundary, markers):
    for source in (decision, boundary):
        assert source["ready_for_review_authorized"] is False
        assert source["merge_authorized"] is False
        assert source["pr_is_draft"] is True
        assert source["pr_merged"] is False
        assert source["pr_number"] == 100
    assert boundary["submission_ready"] is False
    assert boundary["stage130_authorized"] is False
    assert markers["stage130_phase2_ready_for_review_authorized"] is False
    assert markers["stage130_phase2_merge_authorized"] is False
    assert markers["stage130_phase2_submission_ready"] is False
    assert markers["stage130_authorized"] is False


def test_the_branch_was_not_deleted_and_auto_merge_was_not_enabled(boundary):
    assert boundary["branch_deleted_by_this_action"] is False
    assert boundary["auto_merge_enabled_by_this_action"] is False


def test_no_scientific_execution_and_no_final_test_access(boundary, markers):
    assert boundary["final_test_locked"] is True
    assert boundary["final_test_rows_read"] == 0
    assert boundary["final_test_access_authorized"] is False
    assert boundary["new_scientific_analysis_performed"] is False
    assert markers["stage130_phase2_final_test_rows_read"] == 0
    assert markers["stage130_phase2_prediction_artifact_opened"] is False
    assert markers["stage130_scientific_execution_started"] is False


def test_every_counter_is_zero(boundary):
    counters = boundary["counters"]
    assert counters
    for name, value in counters.items():
        assert value == 0, name


def test_no_prior_package_was_modified(boundary):
    assert boundary["prior_packages_modified_by_this_action"] is False
    assert boundary["release_candidate_package_modified_by_this_action"] is False
    assert boundary["release_candidate_archives_modified_by_this_action"] is False
    assert boundary["stage122_to_stage129_artifacts_modified_by_this_action"] \
        is False


def test_no_stage122_to_stage129_file_changed_on_this_branch():
    base = subprocess.run(
        ["git", "merge-base", "HEAD", "origin/main"], cwd=REPO_ROOT,
        capture_output=True, text=True)
    if base.returncode != 0 or not base.stdout.strip():
        pytest.skip("origin/main is not available in this checkout")
    changed = subprocess.run(
        ["git", "diff", "--name-only", f"{base.stdout.strip()}...HEAD"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    for path in changed:
        for stage in range(122, 130):
            assert not path.startswith(f"project/stage{stage}/"), path


# --------------------------------------------------------------------------- #
# History superseded in the open
# --------------------------------------------------------------------------- #

def test_the_release_candidate_record_still_publishes_its_own_history():
    prior = gen.derive_stage130_dataset_release_candidate_markers(REPO_ROOT)
    assert prior["zenodo_deposition_created"] is False
    assert prior["zenodo_upload_performed"] is False
    assert prior["zenodo_doi_reserved"] is False
    assert prior["zenodo_published"] is False
    assert prior["zenodo_doi"] is None
    assert prior["next_research_action_id"] == SUPERSEDED_POINTER


def test_the_supersede_is_declared_machine_readably(decision, boundary):
    marker = decision["superseded_marker"]
    assert marker["key"] == "zenodo_deposition_created"
    assert marker["previous_value"] is False
    assert marker["resolved_value"] is True
    assert set(marker["companion_keys"]) == {
        "zenodo_upload_performed", "zenodo_doi_reserved", "zenodo_doi"}
    assert marker["companion_keys"]["zenodo_doi"]["previous_value"] is None
    assert marker["companion_keys"]["zenodo_doi"]["resolved_value"] == \
        RESERVED_DOI
    assert sorted(marker["keys_deliberately_not_superseded"]) == [
        "public_release_authorized", "zenodo_published"]
    assert marker["pointer_previous_value"] == SUPERSEDED_POINTER
    assert marker["pointer_resolved_value"] == NEXT_POINTER
    assert marker["historical_release_candidate_record_preserved"] is True
    assert boundary["supersedes_key"] == "zenodo_deposition_created"
    assert boundary["supersedes_pointer"] == SUPERSEDED_POINTER
    assert boundary["supersedes_previous_value"] is False


def test_the_release_candidate_package_is_byte_identical():
    """Every rc.3 package file still hashes to its own published digest.

    The Release Candidate's `metadata_and_hashes_*` file is the merged record
    of what that package contained. Re-hashing against it proves this action
    edited none of it, without the test having to guess a commit distance.
    """
    rc = _load(RC_METADATA_REL)
    for name, expected in rc["package_files"].items():
        path = os.path.join(REPO_ROOT, RC_PKG_REL, name)
        assert os.path.isfile(path), name
        with open(path, "rb") as fh:
            payload = fh.read()
        assert hashlib.sha256(payload).hexdigest() == expected["sha256"], name
        assert len(payload) == expected["bytes"], name


# --------------------------------------------------------------------------- #
# The live pointer
# --------------------------------------------------------------------------- #

def test_the_live_pointer_advances_to_the_human_draft_review(
        markers, boundary, roadmap_front_matter, state):
    """This action's OWN pointer, and the one that is live now.

    Both statements are true and neither overwrites the other. This action's
    artifacts keep naming the draft review it created the need for; the
    repository's CURRENT pointer has moved past it, because that review has
    since been completed. What these assertions pin is that this action's own
    record never drifts and that the live state never stalls on a finished
    review.
    """
    for value in (markers["next_research_action_id"],
                  boundary["next_action_id"],
                  markers["stage130_phase2_next_action_id"]):
        assert value == NEXT_POINTER
        assert value != SUPERSEDED_POINTER
    for value in (roadmap_front_matter["next_research_action_id"],
                  state["next_research_action_id"],
                  state["stage130_phase2_next_action_id"]):
        assert value == LIVE_POINTER
        assert value != SUPERSEDED_POINTER
        assert value != NEXT_POINTER
    assert markers["last_completed_research_action_id"] == ACTION_ID
    assert state["last_completed_research_action_id"] == \
        LIVE_LAST_COMPLETED_ACTION
    assert roadmap_front_matter["last_completed_research_action_id"] == \
        LIVE_LAST_COMPLETED_ACTION


def test_the_pointer_is_not_an_authorization(markers, boundary,
                                             roadmap_front_matter):
    assert markers["next_research_action_authorized"] is False
    assert markers["next_research_action_pointer_is_not_authorization"] is True
    assert markers["next_research_action_scope"] == NEXT_POINTER_SCOPE
    assert boundary["next_action_authorized"] is False
    assert boundary["pointer_is_not_authorization"] is True
    assert boundary["next_action_scope"] == NEXT_POINTER_SCOPE
    assert roadmap_front_matter["next_research_action_authorized"] == "false"
    # The ROADMAP publishes the LIVE scope, which has advanced past this
    # action's own; both are unauthorized, and that is the point.
    assert roadmap_front_matter["next_research_action_scope"] == \
        LIVE_POINTER_SCOPE
    assert "no_publication_action_is_authorized" in LIVE_POINTER_SCOPE


def test_the_successor_is_a_human_step(boundary):
    assert boundary["next_action_is_a_human_step"] is True
    assert NEXT_POINTER.startswith("human-")
    assert "publication_decision" in NEXT_POINTER_SCOPE
    assert "no_publish_action_is_authorized" in NEXT_POINTER_SCOPE


def test_the_roadmap_orders_the_new_pointer_after_the_deposition():
    body = _text("project/docs/ai/ROADMAP.md")
    ids = re.findall(
        r"^\s*\d+[a-z]?\.\s+`([a-z0-9]+(?:-[a-z0-9]+)+)`", body, re.MULTILINE)
    assert ACTION_ID in ids
    assert NEXT_POINTER in ids
    assert ids.index(NEXT_POINTER) > ids.index(ACTION_ID)


def test_the_roadmap_front_matter_carries_the_live_zenodo_state(
        roadmap_front_matter):
    front = roadmap_front_matter
    assert front["zenodo_deposition_created"] == "true"
    assert front["zenodo_upload_performed"] == "true"
    assert front["zenodo_doi_reserved"] == "true"
    assert front["zenodo_published"] == "false"
    assert front["zenodo_record_submitted"] == "false"
    assert front["zenodo_record_state"] == RECORD_STATE
    assert front["zenodo_doi"] == RESERVED_DOI
    assert front["zenodo_deposition_id"] == str(DEPOSITION_ID)
    assert front["public_release_authorized"] == "false"


# --------------------------------------------------------------------------- #
# Package hygiene
# --------------------------------------------------------------------------- #

def test_the_package_inventory_is_complete_and_correct(metadata):
    listed = metadata["package_files"]
    assert metadata["package_file_count"] == len(listed) == 3
    pkg_dir = os.path.join(REPO_ROOT, PKG_REL)
    on_disk = {name for name in os.listdir(pkg_dir)
               if os.path.isfile(os.path.join(pkg_dir, name))}
    assert on_disk == set(listed) | {os.path.basename(METADATA_REL)}
    for name, expected in listed.items():
        with open(os.path.join(pkg_dir, name), "rb") as fh:
            payload = fh.read()
        assert hashlib.sha256(payload).hexdigest() == expected["sha256"], name
        assert len(payload) == expected["bytes"], name


def test_no_data_or_result_artifact_was_added():
    names = sorted(os.listdir(os.path.join(REPO_ROOT, PKG_REL)))
    assert names
    for name in names:
        assert name.endswith((".json", ".md")), name
        assert not name.endswith((".csv", ".zip", ".pkl", ".joblib", ".state"))


def test_the_metadata_records_no_committed_credential_or_value_file(metadata):
    assert metadata["credentials_committed_to_git"] is False
    assert metadata["value_files_committed"] == 0
    assert metadata["model_artifacts_committed"] == 0
    assert metadata["final_test_artifacts_committed"] == 0
    assert metadata["manuscript_files_modified_by_this_action"] == 0
    assert metadata["new_data_files_created_by_this_action"] == 0


# --------------------------------------------------------------------------- #
# The generator is FAIL-CLOSED
# --------------------------------------------------------------------------- #

def test_the_deriver_returns_empty_before_the_package_exists(tmp_path):
    root = tmp_path / "empty"
    (root / "project").mkdir(parents=True)
    assert gen.derive_stage130_zenodo_draft_deposition_markers(str(root)) == {}


@pytest.mark.parametrize("field", [
    "record_submitted",
    "public_release",
    "publication_authorized",
    "doi_published",
    "doi_active",
    "doi_resolves_publicly",
    "reserved_doi_is_registered_or_resolving",
    "agent_called_the_zenodo_api",
    "independently_retrieved_by_programmer",
    "deposition_script_re_executed_by_this_action",
    "deposition_state_file_committed_to_git",
    "credentials_committed_to_git",
    "ready_for_review_authorized",
    "merge_authorized",
    "manuscript_modified_by_this_decision",
    "next_action_authorized",
    "preexisting_pointer_was_authorized",
    "pr_merged",
])
def test_claiming_a_forbidden_flag_breaks_the_build(field, tmp_path, decision):
    root = _clone_repo_shim(tmp_path)
    tampered = copy.deepcopy(decision)
    assert field in tampered, field
    tampered[field] = True
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="must be False"):
        gen.derive_stage130_zenodo_draft_deposition_markers(str(root))


@pytest.mark.parametrize("field", [
    "zenodo_published",
    "zenodo_record_submitted",
    "zenodo_publish_endpoint_called",
    "zenodo_token_read_or_requested_by_this_action",
    "public_release_authorized",
    "ready_for_review_authorized",
    "merge_authorized",
    "manuscript_modified_by_this_action",
    "submission_workflow_started",
    "release_candidate_package_modified_by_this_action",
    "branch_deleted_by_this_action",
    "auto_merge_enabled_by_this_action",
])
def test_claiming_a_forbidden_boundary_flag_breaks_the_build(field, tmp_path,
                                                             boundary):
    root = _clone_repo_shim(tmp_path)
    tampered = copy.deepcopy(boundary)
    assert field in tampered, field
    tampered[field] = True
    _write_json(root, BOUNDARY_REL, tampered)
    with pytest.raises(gen.HandoffError, match="must be False"):
        gen.derive_stage130_zenodo_draft_deposition_markers(str(root))


def test_downgrading_the_deposition_to_not_created_breaks_the_build(tmp_path,
                                                                    boundary):
    root = _clone_repo_shim(tmp_path)
    tampered = copy.deepcopy(boundary)
    tampered["zenodo_deposition_created"] = False
    _write_json(root, BOUNDARY_REL, tampered)
    with pytest.raises(gen.HandoffError, match="must be True"):
        gen.derive_stage130_zenodo_draft_deposition_markers(str(root))


def test_calling_the_record_submitted_breaks_the_build(tmp_path, decision):
    root = _clone_repo_shim(tmp_path)
    tampered = copy.deepcopy(decision)
    tampered["record_state"] = "done"
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="record_state"):
        gen.derive_stage130_zenodo_draft_deposition_markers(str(root))


def test_dropping_the_open_access_right_caveat_breaks_the_build(tmp_path,
                                                                decision):
    root = _clone_repo_shim(tmp_path)
    tampered = copy.deepcopy(decision)
    tampered[
        "access_right_open_is_draft_metadata_not_public_availability"] = False
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="access_right"):
        gen.derive_stage130_zenodo_draft_deposition_markers(str(root))


def test_dropping_the_written_explanation_breaks_the_build(tmp_path, decision):
    root = _clone_repo_shim(tmp_path)
    tampered = copy.deepcopy(decision)
    tampered["why_open_access_right_is_not_public_availability"] = ""
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="in words"):
        gen.derive_stage130_zenodo_draft_deposition_markers(str(root))


def test_a_different_deposited_digest_breaks_the_build(tmp_path, decision):
    root = _clone_repo_shim(tmp_path)
    tampered = copy.deepcopy(decision)
    tampered["deposited_file"]["sha256"] = "0" * 64
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="deposited_file sha256"):
        gen.derive_stage130_zenodo_draft_deposition_markers(str(root))


def test_a_different_deposition_id_breaks_the_build(tmp_path, decision):
    root = _clone_repo_shim(tmp_path)
    tampered = copy.deepcopy(decision)
    tampered["deposition_id"] = 1
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="deposition id must be"):
        gen.derive_stage130_zenodo_draft_deposition_markers(str(root))


def test_a_different_reserved_doi_breaks_the_build(tmp_path, decision):
    root = _clone_repo_shim(tmp_path)
    tampered = copy.deepcopy(decision)
    tampered["reserved_doi"] = "10.5281/zenodo.99999999"
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="reserved_doi must be"):
        gen.derive_stage130_zenodo_draft_deposition_markers(str(root))


def test_editing_the_manuscript_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    path = os.path.join(str(root), MANUSCRIPT_REL)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n<!-- tampered -->\n")
    with pytest.raises(gen.HandoffError,
                       match="approved manuscript has changed"):
        gen.derive_stage130_zenodo_draft_deposition_markers(str(root))


def test_a_non_zero_counter_breaks_the_build(tmp_path, boundary):
    root = _clone_repo_shim(tmp_path)
    tampered = copy.deepcopy(boundary)
    tampered["counters"]["zenodo_publish_endpoint_calls"] = 1
    _write_json(root, BOUNDARY_REL, tampered)
    with pytest.raises(gen.HandoffError, match="must be 0"):
        gen.derive_stage130_zenodo_draft_deposition_markers(str(root))


def test_altering_the_v6_digests_breaks_the_build(tmp_path, decision):
    root = _clone_repo_shim(tmp_path)
    tampered = copy.deepcopy(decision)
    tampered["v6_artifact_sha256"]["zenodo_rc3_draft.sh"] = "0" * 64
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="V6 artifact"):
        gen.derive_stage130_zenodo_draft_deposition_markers(str(root))


def test_rewriting_the_release_candidate_history_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    rel = (f"{RC_PKG_REL}/stage130_dataset_release_candidate_decision.json")
    payload = json.load(open(os.path.join(str(root), rel), encoding="utf-8"))
    payload["zenodo_deposition_created"] = True
    _write_json(root, rel, payload)
    with pytest.raises(gen.HandoffError):
        gen.derive_stage130_zenodo_draft_deposition_markers(str(root))


def test_keeping_the_superseded_pointer_breaks_the_build(tmp_path, boundary):
    root = _clone_repo_shim(tmp_path)
    tampered = copy.deepcopy(boundary)
    tampered["next_action_id"] = SUPERSEDED_POINTER
    _write_json(root, BOUNDARY_REL, tampered)
    with pytest.raises(gen.HandoffError, match="advance the pointer"):
        gen.derive_stage130_zenodo_draft_deposition_markers(str(root))


def test_dropping_a_not_superseded_key_breaks_the_build(tmp_path, decision):
    root = _clone_repo_shim(tmp_path)
    tampered = copy.deepcopy(decision)
    tampered["superseded_marker"]["keys_deliberately_not_superseded"] = [
        "zenodo_published"]
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="deliberately NOT superseded"):
        gen.derive_stage130_zenodo_draft_deposition_markers(str(root))


def test_a_committed_token_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    leak = os.path.join(str(root), PKG_REL, "leak.md")
    # Assembled at runtime, never written as a literal. This suite asserts that
    # no credential header exists anywhere in the repository, the branch diff or
    # the pull request; a test that hard-codes one would falsify its own claim.
    header = "Authoriz" + "ation: " + "Bear" + "er " + "ab" * 12
    with open(leak, "w", encoding="utf-8") as fh:
        fh.write(header + "\n")
    with pytest.raises(gen.HandoffError, match="credential-shaped"):
        gen.derive_stage130_zenodo_draft_deposition_markers(str(root))


def test_a_committed_opaque_token_run_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    leak = os.path.join(str(root), PKG_REL, "leak.md")
    with open(leak, "w", encoding="utf-8") as fh:
        fh.write("value " + ("zQ7" * 20) + "\n")
    with pytest.raises(gen.HandoffError, match="opaque"):
        gen.derive_stage130_zenodo_draft_deposition_markers(str(root))


def test_an_unlisted_package_file_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    extra = os.path.join(str(root), PKG_REL, "extra.md")
    with open(extra, "w", encoding="utf-8") as fh:
        fh.write("unlisted\n")
    with pytest.raises(gen.HandoffError, match="inventory disagrees"):
        gen.derive_stage130_zenodo_draft_deposition_markers(str(root))


def test_a_hand_edited_package_file_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    readme = os.path.join(str(root), README_REL)
    with open(readme, "a", encoding="utf-8") as fh:
        fh.write("\nedited\n")
    with pytest.raises(gen.HandoffError, match="published size/SHA-256"):
        gen.derive_stage130_zenodo_draft_deposition_markers(str(root))
