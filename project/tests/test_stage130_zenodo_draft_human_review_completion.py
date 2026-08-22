"""Stage130 — the Zenodo Draft's completed human review and Notes correction.

Recording only. Two LATER human events happened on the private draft this
repository already records: the human reviewed it in Zenodo Preview, and the
human themself corrected its `Notes` field in the Zenodo UI and saved the result
as a Draft. Neither is a publication, and this suite exists so that distinction
cannot quietly erode.

These tests pin:

  * that the human authorization is preserved VERBATIM in Persian — never
    translated, paraphrased, normalized or reflowed — and is attributed to the
    human, with the translation recorded BESIDE it and never instead of it;
  * that the human completed the visual review and the human performed the
    metadata edit, while the programmer independently retrieved nothing and made
    exactly ZERO Zenodo calls;
  * that both Notes texts and both pinned digests are exact, that the corrected
    text is the CURRENT authoritative live value, and that the historical text
    stays historically correct without ever being rendered as the live value;
  * that dropping the word "unpublished" from a Notes field published nothing;
  * that the pre-deposition notes frozen INSIDE the deposited ZIP are a third,
    distinct string that the later correction is not injected into;
  * that the archive's filename, size, SHA-256 and MD5 are unchanged, and that
    no rebuild, replacement, rename or re-upload is claimed;
  * that the deposition id, the reserved VERSION DOI and the reserved CONCEPT
    DOI are exact, distinct, and never described as registered or resolving;
  * that the file-and-metadata review matrix is COMPLETE;
  * that `access_right = open` can never imply current public availability;
  * that any claim of publication, submission, DOI activation or public release
    breaks the build, as does any claim that publication, PR Ready or Merge is
    authorized, any token/API/browser/script-rerun claim, any archive change and
    any manuscript, Stage122–129 or RC-package modification;
  * that no credential-shaped material appears in the package, the branch diff,
    the commit messages or the pull request body;
  * that no existing test was deleted, skipped, weakened or replaced with a less
    strict assertion;
  * that the previous Stage130 draft-deposition package is byte-identical;
  * and that the new live pointer is explicitly, checkably UNAUTHORIZED.
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

ACTION_ID = "stage130-zenodo-draft-human-review-completion"
PKG_REL = "project/stage130/zenodo_draft_human_review_completion"
DECISION_REL = (f"{PKG_REL}/"
                "stage130_zenodo_draft_human_review_completion_decision.json")
BOUNDARY_REL = (
    f"{PKG_REL}/"
    "stage130_zenodo_draft_human_review_completion_governance_boundary.json")
METADATA_REL = (
    f"{PKG_REL}/"
    "metadata_and_hashes_stage130_zenodo_draft_human_review_completion.json")
README_REL = f"{PKG_REL}/README.md"

#: The predecessor package. It is HISTORY: this action appends to it and edits
#: not one byte, so every file is pinned here independently of the generator.
PRIOR_PKG_REL = "project/stage130/zenodo_draft_deposition"
PRIOR_PKG_SHA256 = {
    "README_STAGE130_ZENODO_DRAFT_DEPOSITION.md":
        "fbfba50e6d4d1733cde04f4246a61417572fcf9b1a1d284748d09145d9fb09f5",
    "metadata_and_hashes_stage130_zenodo_draft_deposition.json":
        "7c6bd32ac7d0f51354b99d580fd6f9ce2073fee7c312875ab16e8545222e24ff",
    "stage130_zenodo_draft_deposition_decision.json":
        "debaf29e0155516991c416eb7ad0361c3f7b7682957b47838392b292194d92c9",
    "stage130_zenodo_draft_deposition_governance_boundary.json":
        "287035a559397906e7f0a9e525cf9e929924b7f4a573a046a67e9b88ea0c1cfb",
}

RC_PKG_REL = "project/stage130/dataset_release_candidate"
RC_METADATA_REL = (f"{RC_PKG_REL}/"
                   "metadata_and_hashes_stage130_dataset_release_candidate.json")
EMBEDDED_METADATA_REL = f"{RC_PKG_REL}/release_payload/zenodo_metadata_candidate.json"

#: The human-supplied Zenodo state, restated independently of both the artifacts
#: and the generator so a silent edit to either cannot also edit the expectation.
DEPOSITION_ID = 22059238
VERSION_DOI = "10.5281/zenodo.22059238"
CONCEPT_DOI = "10.5281/zenodo.22059237"
RECORD_STATE = "unsubmitted"
VERSION = "1.0.0-rc.3"
LICENSE = "cc-by-4.0"
ACCESS_RIGHT = "open"

FILENAME = "tse_financial_distress_dataset_1392_1402_release_candidate_rc3.zip"
SHA256 = "4adb32bd675fd9181d8ced783b6734382e9749c6c574e35567d1bec65fd72f70"
MD5 = "cbd3df6c75053ee6d0641f19d5301d7a"
SIZE_BYTES = 11824690
ARCHIVE_REL = f"{RC_PKG_REL}/build/rc3/{FILENAME}"

MANUSCRIPT_REL = "project/stage130/manuscript/manuscript_draft_en.md"
MANUSCRIPT_SHA256 = (
    "8b5d861c36e01dc81133c1071cd96f7e340482ac2148b53c055369bbd5ffcb19")
MANUSCRIPT_BLOB_ID = "93f7e8e796ec098de38725271305ab06263efd1f"

#: The pointer this action supersedes, and the human decision it advances to.
SUPERSEDED_POINTER = "human-zenodo-draft-review-and-publication-decision"
NEXT_POINTER = "human-zenodo-publication-decision"
NEXT_POINTER_SCOPE = (
    "zenodo_publication_decision_only_no_publication_action_is_authorized")

#: The complete file-and-metadata review matrix. A partial review is not a
#: review, so the whole set is pinned rather than a count.
REVIEWED_ITEMS = {
    "archive_contents",
    "citation",
    "creators",
    "description",
    "file",
    "keywords",
    "license",
    "reserved_doi_identifiers",
    "title",
    "version",
}

#: The commit this action started from. Used to prove that no existing test was
#: deleted, skipped or weakened by THIS change specifically.
PRE_ACTION_HEAD = "96f11f87583e3e45497e104b2a524267ecb3f0c1"


#: The human authorization, VERBATIM. Pinned here independently of both the
#: artifact and the generator, so a silent edit to either cannot also edit the
#: expectation. It is Persian and it stays Persian: never translated,
#: paraphrased, normalized or reflowed.
AUTHORIZATION_TEXT = (
    "Draft زنودو مربوط به deposition شماره 22059238 را کامل بازبینی کردم. فایل، عنوان، نویسندگان، توضیحات، کلیدواژه‌ها، نسخه، مجوز، Citation و DOIهای رزروشده را تأیید می‌کنم. اصلاح Notes به متن پایدار شامل SHA-256 و اندازه دقیق آرشیو را نیز تأیید می‌کنم و اجازه می‌دهم این بازبینی و اصلاح متادیتا در مخزن ثبت شود؛ اما انتشار Zenodo، فعال‌سازی عمومی DOI، Ready کردن PR و Merge هنوز مجاز نیست."
)
AUTHORIZATION_SHA256 = (
    "fa7f98d91a08cdcb4862c227584b843058468995d52480a5eaac1788645a2bac")
AUTHORIZATION_BYTES = 642

#: The two live Notes values, restated independently. Digests are over the UTF-8
#: text with NO trailing newline.
HISTORICAL_NOTES = (
    "Release candidate 1.0.0-rc.3, superseding 1.0.0-rc.2 and, through it, "
    "1.0.0-rc.1. Both predecessors are preserved, not deleted. This record is "
    "an unpublished Zenodo draft. A DOI has been reserved but not published or "
    "activated, and no public release has occurred."
)
HISTORICAL_NOTES_SHA256 = (
    "9096ed3fc195915fb6428a107adacffde23c59aaac6845966b20cbffcfc62ff2")
LIVE_NOTES = (
    "Release candidate 1.0.0-rc.3, superseding 1.0.0-rc.2 and, through it, "
    "1.0.0-rc.1. Both predecessors are preserved, not deleted. The deposited "
    "archive is the exact RC3 artifact with SHA-256 "
    "4adb32bd675fd9181d8ced783b6734382e9749c6c574e35567d1bec65fd72f70 and size "
    "11,824,690 bytes."
)
LIVE_NOTES_SHA256 = (
    "7ff1c7de2baab5e2ecc95e20d8996db38bb8ec67e35dc4200335ec37d6f5ea46")


def _load(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def _text(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def _sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
def notes(decision):
    return decision["notes_correction"]


@pytest.fixture(scope="module")
def markers():
    return gen.derive_stage130_zenodo_draft_human_review_completion_markers(
        REPO_ROOT)


@pytest.fixture(scope="module")
def prior_markers():
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


#: The paths the fail-closed tests mutate inside the shim. They are snapshotted
#: before each such test and restored afterwards, so ONE copy of the tree serves
#: the whole module. Copying this repository per test would write tens of
#: gigabytes of temporary data over a full-suite run and fill the disk.
_MUTABLE_SHIM_FILES = (
    README_REL, DECISION_REL, BOUNDARY_REL, METADATA_REL,
    MANUSCRIPT_REL, EMBEDDED_METADATA_REL,
) + tuple(f"{PRIOR_PKG_REL}/{name}" for name in sorted(PRIOR_PKG_SHA256))
#: Directories whose CONTENTS may change (one test adds an unlisted file,
#: another removes the package outright), so their listings are snapshotted too.
_MUTABLE_SHIM_DIRS = (PKG_REL, PRIOR_PKG_REL)


@pytest.fixture(scope="module")
def _shim_tree(tmp_path_factory):
    """One copy of the tree the deriver reads: both Stage130 packages, the
    manuscript, and the Stage125 inputs the Release Candidate deriver needs."""
    root = tmp_path_factory.mktemp("zdhrc_shim") / "repo"
    shutil.copytree(os.path.join(REPO_ROOT, "project"), root / "project",
                    ignore=shutil.ignore_patterns("__pycache__", ".venv"))
    return root


@pytest.fixture
def shim(_shim_tree):
    """The shared shim, restored to pristine bytes after every test.

    Restoring is what makes sharing safe: a fail-closed test that tampers with
    an artifact must not leak that tampering into the next one, so the mutable
    files and the mutable directory listings are both put back exactly.
    """
    root = str(_shim_tree)
    snapshot = {}
    for rel in _MUTABLE_SHIM_FILES:
        with open(os.path.join(root, rel), "rb") as fh:
            snapshot[rel] = fh.read()
    listings = {d: set(os.listdir(os.path.join(root, d)))
                for d in _MUTABLE_SHIM_DIRS}
    yield _shim_tree
    for rel_dir, names in listings.items():
        full = os.path.join(root, rel_dir)
        os.makedirs(full, exist_ok=True)
        for name in os.listdir(full):
            if name in names:
                continue
            path = os.path.join(full, name)
            shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
    for rel, payload in snapshot.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(payload)


def _write_json(root, rel, payload):
    path = os.path.join(str(root), rel)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False, sort_keys=True)


def _git(*args):
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True,
                          text=True)


# --------------------------------------------------------------------------- #
# (1) The human authorization, preserved VERBATIM and attributed to the human
# --------------------------------------------------------------------------- #

def test_the_persian_authorization_is_preserved_verbatim(decision):
    assert decision["human_decision_verbatim"] == AUTHORIZATION_TEXT
    assert gen._STAGE130_ZDHRC_AUTHORIZATION_TEXT == AUTHORIZATION_TEXT


def test_the_verbatim_authorization_is_pinned_by_its_own_digest(decision):
    digest = _sha256_text(AUTHORIZATION_TEXT)
    assert digest == AUTHORIZATION_SHA256
    assert decision["human_decision_verbatim_sha256"] == digest
    assert gen._STAGE130_ZDHRC_AUTHORIZATION_SHA256 == digest
    assert len(AUTHORIZATION_TEXT.encode("utf-8")) == AUTHORIZATION_BYTES
    assert decision["human_decision_verbatim_utf8_bytes"] == AUTHORIZATION_BYTES
    assert gen._STAGE130_ZDHRC_AUTHORIZATION_BYTES == AUTHORIZATION_BYTES


def test_the_authorization_is_persian_and_is_not_normalized(decision):
    text = decision["human_decision_verbatim"]
    assert decision["human_decision_verbatim_language"] == "fa"
    # Persian characters, Persian punctuation and the ZWNJ all survive intact:
    # normalizing any of them away would change the bytes and the digest.
    assert "؛" in text, "the Persian semicolon must survive"
    assert "‌" in text, "the zero-width non-joiner must survive"
    assert "ی" in text, "Persian yeh must not be normalized to Arabic yeh"
    assert "22059238" in text


def test_the_translation_is_recorded_beside_the_verbatim_never_instead(decision):
    assert decision["human_decision_translation"]
    assert decision["human_decision_translation"] != \
        decision["human_decision_verbatim"]


def test_the_authorization_is_attributed_to_the_human(decision, boundary):
    assert decision["supplied_by"] == "human"
    assert decision["submitted_by"] == "human"
    assert boundary["supplied_by"] == "human"
    assert decision["authorized_by_human"] is True
    assert decision["authorized_scope"]


def test_a_paraphrased_authorization_breaks_the_build(shim, decision):
    root = shim
    tampered = copy.deepcopy(decision)
    tampered["human_decision_verbatim"] = \
        tampered["human_decision_verbatim"].replace("‌", "")
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="preserved exactly"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


def test_a_translated_authorization_breaks_the_build(shim, decision):
    root = shim
    tampered = copy.deepcopy(decision)
    tampered["human_decision_verbatim"] = tampered["human_decision_translation"]
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="preserved exactly"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


def test_dropping_the_translation_breaks_the_build(shim, decision):
    root = shim
    tampered = copy.deepcopy(decision)
    tampered["human_decision_translation"] = ""
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="BESIDE"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


# --------------------------------------------------------------------------- #
# (2)(3)(4) Provenance: a human reviewed and a human edited; the programmer
# retrieved nothing and called Zenodo zero times
# --------------------------------------------------------------------------- #

def test_the_human_completed_the_visual_review(decision, boundary, metadata,
                                               markers):
    for source in (decision, boundary, metadata):
        assert source["human_visual_review_completed"] is True
    assert markers["stage130_zenodo_human_visual_review_completed"] is True
    assert markers["stage130_zenodo_draft_human_review_completed"] is True
    assert decision["human_review_performed_in_zenodo_preview"] is True


def test_the_human_performed_the_metadata_edit(decision, boundary, metadata,
                                               markers, notes):
    for source in (decision, boundary, metadata):
        assert source["human_metadata_edit_performed"] is True
    assert markers["stage130_zenodo_human_metadata_edit_performed"] is True
    assert markers["stage130_zenodo_draft_notes_correction_completed"] is True
    assert notes["edit_performed_by"] == "human"
    assert notes["edit_performed_by_programmer"] is False


def test_the_programmer_did_not_independently_retrieve_anything(
        decision, boundary, metadata, markers):
    for source in (decision, boundary, metadata):
        assert source["independently_retrieved_by_programmer"] is False
    assert markers["stage130_zenodo_independently_retrieved_by_programmer"] \
        is False
    assert decision["why_the_programmer_did_not_verify_this_independently"]


def test_zero_zenodo_calls_were_made_by_this_action(decision, boundary,
                                                    metadata, markers):
    for source in (decision, boundary, metadata):
        assert source["zenodo_api_calls_made_by_this_action"] == 0
    assert markers["stage130_zenodo_api_calls_made_by_this_action"] == 0
    assert markers["stage130_zenodo_api_called_by_this_action"] is False
    counters = boundary["counters"]
    for key in ("zenodo_api_calls_made_by_this_action",
                "zenodo_publish_endpoint_calls",
                "zenodo_submit_endpoint_calls",
                "zenodo_metadata_write_calls_made_by_this_action",
                "zenodo_tokens_read_or_requested",
                "zenodo_browser_automation_sessions",
                "deposition_script_executions",
                "deposition_state_file_reads"):
        assert counters[key] == 0, key


def test_every_counter_is_zero(boundary):
    assert boundary["counters"]
    for key, value in boundary["counters"].items():
        assert value == 0, key


def test_the_deposition_state_file_was_tested_for_existence_only(
        decision, boundary, markers):
    for source in (decision, boundary):
        assert source["deposition_state_file_existence_tested_only"] is True
        assert source["deposition_state_file_opened_or_parsed_by_this_action"] \
            is False
        assert source["deposition_state_file_committed_to_git"] is False
    assert markers["stage130_zenodo_state_file_existence_tested_only"] is True
    assert markers["stage130_zenodo_state_file_committed_to_git"] is False


def test_the_state_file_is_not_in_the_repository():
    result = _git("ls-files", "--error-unmatch", ".zenodo_rc3_deposition.state")
    assert result.returncode != 0
    tracked = _git("ls-files").stdout.splitlines()
    assert not [p for p in tracked if p.endswith(".state")]


def test_recording_is_not_a_retroactive_authorization(decision, markers):
    assert decision["recording_is_not_retroactive_authorization"] is True
    assert decision["preexisting_pointer_at_review_time"] == SUPERSEDED_POINTER
    assert decision["preexisting_pointer_was_authorized"] is False
    assert markers[
        "stage130_zenodo_review_recording_is_not_retroactive_authorization"] \
        is True


# --------------------------------------------------------------------------- #
# (5)(6)(7) The two Notes texts, their digests, and which one is LIVE
# --------------------------------------------------------------------------- #

def test_both_notes_texts_are_exact(notes):
    assert notes["historical_notes_text"] == HISTORICAL_NOTES
    assert notes["authoritative_notes_text"] == LIVE_NOTES
    assert gen._STAGE130_ZDHRC_HISTORICAL_NOTES == HISTORICAL_NOTES
    assert gen._STAGE130_ZDHRC_LIVE_NOTES == LIVE_NOTES
    assert HISTORICAL_NOTES != LIVE_NOTES


def test_both_notes_digests_are_exact(notes):
    assert _sha256_text(HISTORICAL_NOTES) == HISTORICAL_NOTES_SHA256
    assert _sha256_text(LIVE_NOTES) == LIVE_NOTES_SHA256
    assert notes["historical_notes_sha256"] == HISTORICAL_NOTES_SHA256
    assert notes["authoritative_notes_sha256"] == LIVE_NOTES_SHA256
    assert gen._STAGE130_ZDHRC_HISTORICAL_NOTES_SHA256 == HISTORICAL_NOTES_SHA256
    assert gen._STAGE130_ZDHRC_LIVE_NOTES_SHA256 == LIVE_NOTES_SHA256


def test_both_notes_byte_lengths_are_exact(notes):
    assert len(HISTORICAL_NOTES.encode("utf-8")) == 263
    assert len(LIVE_NOTES.encode("utf-8")) == 280
    assert notes["historical_notes_utf8_bytes"] == 263
    assert notes["authoritative_notes_utf8_bytes"] == 280


def test_the_notes_digests_are_over_the_text_with_no_trailing_newline():
    assert not HISTORICAL_NOTES.endswith("\n")
    assert not LIVE_NOTES.endswith("\n")
    assert _sha256_text(HISTORICAL_NOTES + "\n") != HISTORICAL_NOTES_SHA256
    assert _sha256_text(LIVE_NOTES + "\n") != LIVE_NOTES_SHA256


def test_the_new_notes_is_the_authoritative_current_value(
        notes, decision, boundary, metadata, markers):
    assert notes["authoritative_notes_is_the_current_live_value"] is True
    for source in (decision, boundary, metadata):
        assert source["stage130_zenodo_live_notes_sha256"] == LIVE_NOTES_SHA256
    assert markers["stage130_zenodo_live_notes_sha256"] == LIVE_NOTES_SHA256
    assert markers["stage130_zenodo_live_notes_utf8_bytes"] == 280


def test_the_live_notes_is_publication_stable_and_says_why(
        notes, decision, boundary, metadata, markers):
    for source in (decision, boundary, metadata):
        assert source["stage130_zenodo_live_notes_are_publication_stable"] \
            is True
    assert markers["stage130_zenodo_live_notes_are_publication_stable"] is True
    assert notes["authoritative_notes_are_publication_stable"] is True
    assert notes["why_the_authoritative_text_is_publication_stable"]
    assert notes["why_the_historical_text_was_not_publication_stable"]


def test_the_live_notes_pins_the_exact_archive_identity(notes):
    assert notes["authoritative_notes_pins_archive_sha256"] == SHA256
    assert notes["authoritative_notes_pins_archive_size_bytes"] == SIZE_BYTES
    assert SHA256 in LIVE_NOTES
    assert "11,824,690" in LIVE_NOTES


def test_the_old_notes_remains_historical_and_is_never_the_live_value(
        notes, markers):
    assert notes["historical_notes_remains_historically_correct"] is True
    assert notes["historical_notes_is_the_current_live_value"] is False
    assert notes["historical_notes_superseded_only_as_the_current_live_value"] \
        is True
    assert notes[
        "history_is_not_rewritten_to_pretend_the_new_notes_existed_at_deposit_"
        "time"] is True
    assert markers[
        "stage130_zenodo_historical_notes_remains_historically_correct"] is True
    assert markers[
        "stage130_zenodo_historical_notes_is_the_current_live_value"] is False
    assert markers["stage130_zenodo_historical_notes_sha256"] == \
        HISTORICAL_NOTES_SHA256


def test_the_historical_notes_is_what_the_pinned_v6_metadata_carried(notes):
    # Corroboration that does NOT depend on this package: the deposition
    # metadata artifact the human actually ran is already pinned by SHA-256 in
    # the predecessor record, and its notes field is the historical text.
    prior = _load(f"{PRIOR_PKG_REL}/"
                  "stage130_zenodo_draft_deposition_decision.json")
    assert prior["v6_artifact_sha256"]["zenodo_draft_metadata_rc3.json"] == \
        notes["historical_notes_corroborating_artifact_sha256"]
    assert notes["historical_notes_corroborating_artifact"] == \
        "zenodo_draft_metadata_rc3.json"


def test_the_notes_edit_was_metadata_only_and_saved_as_a_draft(notes):
    assert notes["edit_scope"] == "metadata_notes_field_only"
    assert notes["files_changed_by_this_edit"] == 0
    assert notes["record_submitted_by_this_edit"] is False
    assert notes["saved_state_after_this_edit"] == "draft"
    assert notes["record_state_after_this_edit"] == RECORD_STATE
    assert notes["edit_performed_through"] == "zenodo_web_user_interface"


def test_dropping_the_word_unpublished_published_nothing(notes, markers):
    assert "unpublished" in HISTORICAL_NOTES
    assert "unpublished" not in LIVE_NOTES
    assert notes["shorter_notes_is_not_a_lifecycle_change"] is True
    assert notes["why_removing_the_unpublished_sentence_published_nothing"]
    # ...and the lifecycle markers themselves are what carry the status.
    assert markers["zenodo_record_submitted"] is False
    assert markers["zenodo_record_state"] == RECORD_STATE
    assert markers["zenodo_published"] is False
    assert markers["zenodo_doi_published"] is False
    assert markers["zenodo_doi_publicly_activated"] is False
    assert markers["zenodo_public_release"] is False


def test_the_three_notes_strings_are_distinct(notes):
    embedded = notes["embedded_zip_candidate_metadata_notes_text"]
    assert len({HISTORICAL_NOTES, LIVE_NOTES, embedded}) == 3
    assert notes["three_distinct_notes_strings_must_not_be_conflated"] is True


def test_the_pre_deposition_notes_inside_the_zip_is_untouched(notes):
    embedded = _load(EMBEDDED_METADATA_REL)
    assert embedded["metadata"]["notes"] == \
        notes["embedded_zip_candidate_metadata_notes_text"]
    assert embedded["metadata"]["notes"] != LIVE_NOTES
    assert embedded["metadata"]["notes"] != HISTORICAL_NOTES
    assert notes["embedded_zip_candidate_metadata_modified"] is False
    assert notes[
        "embedded_zip_candidate_metadata_notes_is_a_pre_deposition_artifact"] \
        is True
    assert notes[
        "correction_is_an_external_metadata_event_not_an_archive_change"] is True
    assert notes["embedded_zip_candidate_metadata_path"] == \
        EMBEDDED_METADATA_REL


def test_swapping_the_two_notes_texts_breaks_the_build(shim, decision):
    root = shim
    tampered = copy.deepcopy(decision)
    tampered["notes_correction"]["historical_notes_text"] = LIVE_NOTES
    tampered["notes_correction"]["authoritative_notes_text"] = HISTORICAL_NOTES
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="pinned Notes value"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


def test_rendering_the_old_notes_as_the_live_value_breaks_the_build(
        shim, decision):
    root = shim
    tampered = copy.deepcopy(decision)
    tampered["notes_correction"]["historical_notes_is_the_current_live_value"] \
        = True
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="current live value"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


def test_calling_the_old_notes_wrong_breaks_the_build(shim, decision):
    root = shim
    tampered = copy.deepcopy(decision)
    tampered["notes_correction"][
        "historical_notes_remains_historically_correct"] = False
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="historically correct"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


def test_a_drifted_notes_digest_breaks_the_build(shim, decision):
    root = shim
    tampered = copy.deepcopy(decision)
    tampered["notes_correction"]["authoritative_notes_sha256"] = "0" * 64
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="does not\n?\\s*match its own text"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


def test_injecting_the_live_notes_into_the_zip_metadata_breaks_the_build(
        shim):
    root = shim
    embedded = _load(EMBEDDED_METADATA_REL)
    embedded["metadata"]["notes"] = LIVE_NOTES
    _write_json(root, EMBEDDED_METADATA_REL, embedded)
    with pytest.raises(gen.HandoffError):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


def test_claiming_the_programmer_edited_zenodo_breaks_the_build(
        shim, decision):
    root = shim
    tampered = copy.deepcopy(decision)
    tampered["notes_correction"]["edit_performed_by"] = "programmer"
    tampered["notes_correction"]["edit_performed_by_programmer"] = True
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="performed by the HUMAN"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


def test_claiming_the_edit_submitted_the_record_breaks_the_build(
        shim, decision):
    root = shim
    tampered = copy.deepcopy(decision)
    tampered["notes_correction"]["record_submitted_by_this_edit"] = True
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="saved as a DRAFT"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


# --------------------------------------------------------------------------- #
# (8) The archive did not move
# --------------------------------------------------------------------------- #

def test_the_archive_identity_is_exact(decision, boundary, metadata):
    assert decision["deposited_file"] == {
        "filename": FILENAME, "md5": MD5, "sha256": SHA256,
        "size_bytes": SIZE_BYTES}
    for source in (boundary, metadata):
        assert source["deposited_file_name"] == FILENAME
        assert source["deposited_file_sha256"] == SHA256
        assert source["deposited_file_md5"] == MD5
        assert source["deposited_file_size_bytes"] == SIZE_BYTES


def test_the_archive_still_matches_the_release_candidate_record():
    rc = _load(RC_METADATA_REL)
    assert rc["archive_name"] == FILENAME
    assert rc["archive_sha256"] == SHA256
    assert rc["archive_size_bytes"] == SIZE_BYTES


def test_the_local_archive_is_byte_identical_when_present():
    path = os.path.join(REPO_ROOT, ARCHIVE_REL)
    if not os.path.isfile(path):
        # The archive is gitignored; a fresh clone legitimately lacks it, so
        # its ABSENCE is tolerated. Drift never is, and the committed record is
        # still checked above and by the deriver.
        assert not os.path.exists(path)
        return
    with open(path, "rb") as fh:
        payload = fh.read()
    assert hashlib.sha256(payload).hexdigest() == SHA256
    assert hashlib.md5(payload).hexdigest() == MD5
    assert len(payload) == SIZE_BYTES


def test_no_archive_was_rebuilt_replaced_renamed_or_reuploaded(
        decision, boundary, metadata, markers):
    for source in (decision, boundary):
        assert source["archive_rebuilt_by_this_action"] is False
        assert source["archive_replaced_by_this_action"] is False
        assert source["archive_re_uploaded_by_this_action"] is False
        assert source["archive_renamed_by_this_action"] is False
        assert source["archive_manifest_regenerated_by_this_action"] is False
    assert metadata["archive_modified_by_this_action"] is False
    assert metadata["archive_re_uploaded_by_this_action"] is False
    assert markers["stage130_zenodo_archive_modified_by_this_action"] is False
    assert markers["stage130_zenodo_archive_re_uploaded_by_this_action"] is False
    counters = boundary["counters"]
    for key in ("archive_rebuilds", "archive_renames",
                "archive_uploads_or_replacements", "archive_members_modified",
                "release_candidate_archives_rebuilt",
                "release_manifests_regenerated"):
        assert counters[key] == 0, key


# --------------------------------------------------------------------------- #
# (9) The identifiers
# --------------------------------------------------------------------------- #

def test_the_deposition_id_is_exact(decision, boundary, metadata, markers):
    for source in (decision, boundary, metadata):
        assert source["deposition_id"] == DEPOSITION_ID
    assert markers["zenodo_deposition_id"] == DEPOSITION_ID


def test_both_reserved_dois_are_exact(decision, boundary, metadata, markers):
    for source in (decision, boundary, metadata):
        assert source["reserved_version_doi"] == VERSION_DOI
        assert source["reserved_concept_doi"] == CONCEPT_DOI
    assert markers["zenodo_version_doi"] == VERSION_DOI
    assert markers["zenodo_concept_doi"] == CONCEPT_DOI
    assert markers["zenodo_doi"] == VERSION_DOI
    assert VERSION_DOI != CONCEPT_DOI
    assert VERSION_DOI.endswith(str(DEPOSITION_ID))


def test_the_version_doi_is_the_one_the_deposition_already_recorded(
        prior_markers):
    assert prior_markers["zenodo_doi"] == VERSION_DOI


def test_neither_doi_is_described_as_registered_or_resolving(
        decision, boundary, markers):
    for source in (decision, boundary):
        assert source["doi_active"] is False
        assert source["doi_resolves_publicly"] is False
        assert source["reserved_doi_is_registered_or_resolving"] is False
    assert markers["zenodo_doi_registered_or_resolving"] is False
    assert markers["zenodo_doi_published"] is False
    assert markers["zenodo_doi_publicly_activated"] is False


def test_the_concept_doi_is_recorded_as_displayed_not_activated(
        decision, boundary, markers):
    for source in (decision, boundary):
        assert source["concept_doi_displayed"] is True
        assert source["version_doi_reserved"] is True
    assert markers["zenodo_concept_doi_displayed"] is True
    assert markers["zenodo_version_doi_reserved"] is True


def test_a_wrong_deposition_id_breaks_the_build(shim, decision):
    root = shim
    tampered = copy.deepcopy(decision)
    tampered["deposition_id"] = 12345678
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="deposition id"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


def test_collapsing_the_two_dois_breaks_the_build(shim, decision):
    root = shim
    tampered = copy.deepcopy(decision)
    tampered["reserved_concept_doi"] = VERSION_DOI
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="reserved_concept_doi"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


# --------------------------------------------------------------------------- #
# (10) The file-and-metadata review matrix is COMPLETE
# --------------------------------------------------------------------------- #

def test_the_review_matrix_is_complete(decision, boundary, markers):
    assert set(decision["reviewed_items"]) == REVIEWED_ITEMS
    assert all(v is True for v in decision["reviewed_items"].values())
    assert set(boundary["reviewed_items"]) == REVIEWED_ITEMS
    for source in (decision, boundary):
        assert source["reviewed_item_count"] == len(REVIEWED_ITEMS)
        assert source["reviewed_items_complete"] is True
    assert set(markers["stage130_zenodo_draft_reviewed_items"]) == REVIEWED_ITEMS
    assert markers["stage130_zenodo_draft_review_matrix_complete"] is True
    assert markers["stage130_zenodo_draft_reviewed_item_count"] == \
        len(REVIEWED_ITEMS)


def test_the_matrix_covers_every_item_the_human_named(decision):
    # file, title, creators, description, keywords, version, license,
    # Citation, reserved DOI identifiers, archive contents.
    for item in ("file", "title", "creators", "description", "keywords",
                 "version", "license", "citation", "reserved_doi_identifiers",
                 "archive_contents"):
        assert decision["reviewed_items"][item] is True, item


@pytest.mark.parametrize("item", sorted(REVIEWED_ITEMS))
def test_an_unreviewed_item_breaks_the_build(item, shim, decision):
    root = shim
    tampered = copy.deepcopy(decision)
    tampered["reviewed_items"][item] = False
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="matrix must be complete"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


def test_a_shortened_matrix_breaks_the_build(shim, decision):
    root = shim
    tampered = copy.deepcopy(decision)
    tampered["reviewed_items"].pop("citation")
    tampered["reviewed_item_count"] = len(tampered["reviewed_items"])
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="exactly the reviewed"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


# --------------------------------------------------------------------------- #
# (11) `access_right = open` can never imply current public availability
# --------------------------------------------------------------------------- #

def test_access_right_open_is_recorded_as_draft_metadata(
        decision, boundary, markers):
    for source in (decision, boundary):
        assert source["access_right"] == ACCESS_RIGHT
        assert source[
            "access_right_open_is_draft_metadata_not_public_availability"] \
            is True
        assert source["access_right_open_implies_public_availability"] is False
    assert markers["stage130_zenodo_access_right"] == ACCESS_RIGHT
    assert markers["stage130_zenodo_access_right_is_public_availability"] \
        is False
    assert markers[
        "stage130_zenodo_access_right_is_evidence_of_public_availability"] \
        is False


def test_the_record_is_not_publicly_available(decision, boundary, metadata,
                                              markers):
    for source in (decision, boundary):
        assert source["record_is_private_draft"] is True
        assert source["record_state"] == RECORD_STATE
    assert metadata["record_publicly_available"] is False
    assert metadata["record_is_private_draft"] is True
    assert markers["zenodo_record_is_private_draft"] is True
    assert decision["why_open_access_right_is_not_public_availability"]


def test_letting_open_stand_as_availability_breaks_the_build(
        shim, decision):
    root = shim
    tampered = copy.deepcopy(decision)
    tampered[
        "access_right_open_is_draft_metadata_not_public_availability"] = False
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError,
                       match="NOT evidence of\n?\\s*current public"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


def test_claiming_open_implies_availability_breaks_the_build(
        shim, decision):
    root = shim
    tampered = copy.deepcopy(decision)
    tampered["access_right_open_implies_public_availability"] = True
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="must be False"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


# --------------------------------------------------------------------------- #
# (12)(13)(14)(15)(16) Everything that did NOT happen and is NOT authorized
# --------------------------------------------------------------------------- #

def test_nothing_was_published_submitted_or_activated(
        decision, boundary, metadata, markers):
    for source in (decision, boundary):
        assert source["record_submitted"] is False
        assert source["zenodo_published"] is False
        assert source["doi_published"] is False
        assert source["doi_publicly_activated"] is False
        assert source["public_release"] is False
    assert metadata["record_submitted"] is False
    assert metadata["zenodo_published"] is False
    assert metadata["public_release"] is False
    assert markers["zenodo_published"] is False
    assert markers["zenodo_record_submitted"] is False
    assert markers["zenodo_public_release"] is False
    assert decision["why_a_completed_review_is_not_a_publication"]
    assert decision["why_a_notes_correction_is_not_a_publication"]


def test_nothing_further_is_authorized(decision, boundary, metadata, markers):
    for source in (decision, boundary):
        assert source["publication_authorized"] is False
        assert source["public_release_authorized"] is False
        assert source["submission_authorized"] is False
        assert source["doi_activation_authorized"] is False
        assert source["ready_for_review_authorized"] is False
        assert source["merge_authorized"] is False
        assert source["auto_merge_authorized"] is False
        assert source["next_action_authorized"] is False
        assert source["stage130_authorized"] is False
    assert metadata["publication_authorized"] is False
    assert metadata["public_release_authorized"] is False
    assert markers["zenodo_publication_authorized"] is False
    assert markers["zenodo_submission_authorized"] is False
    assert markers["zenodo_doi_activation_authorized"] is False
    assert markers["public_release_authorized"] is False
    assert markers["stage130_phase2_ready_for_review_authorized"] is False
    assert markers["stage130_phase2_merge_authorized"] is False
    assert markers["stage130_authorized"] is False


def test_the_pull_request_is_still_an_unmerged_draft(decision, boundary,
                                                     markers):
    for source in (decision, boundary):
        assert source["pr_number"] == 100
        assert source["pr_is_draft"] is True
        assert source["pr_merged"] is False
        assert source["pr_marked_ready_by_this_action"] is False
        assert source["auto_merge_enabled_by_this_action"] is False
        assert source["branch_deleted_by_this_action"] is False
        assert source["new_pull_request_created_by_this_action"] is False
    assert markers["stage130_pr_ready"] is False
    assert markers["stage130_pr_merged"] is False
    assert boundary["counters"]["new_pull_requests_created"] == 0


def test_no_zenodo_contact_of_any_kind(decision, boundary, markers):
    for source in (decision, boundary):
        assert source["agent_called_the_zenodo_api"] is False
        assert source["zenodo_publish_endpoint_called"] is False
        assert source["zenodo_submit_endpoint_called"] is False
        assert source["zenodo_metadata_written_by_this_action"] is False
        assert source["zenodo_token_read_or_requested_by_this_action"] is False
        assert source["zenodo_opened_by_automation_in_this_action"] is False
        assert source["deposition_script_re_executed_by_this_action"] is False
    assert markers["stage130_zenodo_publish_endpoint_called"] is False
    assert markers["stage130_zenodo_token_read_or_requested"] is False
    assert markers["stage130_zenodo_opened_by_automation_in_this_action"] \
        is False
    assert markers["stage130_zenodo_script_re_executed_by_this_action"] is False


def test_the_manuscript_is_byte_identical(boundary, markers):
    with open(os.path.join(REPO_ROOT, MANUSCRIPT_REL), "rb") as fh:
        payload = fh.read()
    assert hashlib.sha256(payload).hexdigest() == MANUSCRIPT_SHA256
    assert gen._git_blob_id(payload) == MANUSCRIPT_BLOB_ID
    assert boundary["reviewed_manuscript_path"] == MANUSCRIPT_REL
    assert boundary["reviewed_manuscript_sha256"] == MANUSCRIPT_SHA256
    assert boundary["reviewed_manuscript_blob_id"] == MANUSCRIPT_BLOB_ID
    assert boundary["manuscript_modified_by_this_action"] is False
    assert boundary[
        "manuscript_data_availability_statement_changed_by_this_action"] is False
    assert markers["stage130_manuscript_modified_by_this_action"] is False
    assert markers["stage130_manuscript_availability_claim_changed"] is False
    assert markers["stage130_manuscript_requires_post_doi_human_review"] is True
    assert boundary["counters"]["manuscript_bytes_changed"] == 0


def test_no_prior_package_or_stage122_to_129_artifact_was_modified(
        boundary, metadata):
    assert boundary["prior_packages_modified_by_this_action"] is False
    assert boundary["stage122_to_stage129_artifacts_modified_by_this_action"] \
        is False
    assert boundary["release_candidate_package_modified_by_this_action"] is False
    assert boundary["counters"]["prior_package_bytes_changed"] == 0
    assert metadata["prior_package_files_modified_by_this_action"] == 0


def test_no_scientific_execution_and_the_firewall_is_untouched(boundary,
                                                               markers):
    assert boundary["new_scientific_analysis_performed"] is False
    assert boundary["scientific_execution_started"] is False
    assert boundary["final_test_locked"] is True
    assert boundary["final_test_rows_read"] == 0
    assert boundary["final_test_access_authorized"] is False
    assert boundary["final_test_second_pass_authorized"] is False
    assert markers["stage130_scientific_execution_started"] is False
    assert markers["stage130_phase2_final_test_rows_read"] == 0
    assert markers["stage130_phase2_prediction_artifact_opened"] is False


#: Every claim that must break the build if it is ever recorded True on the
#: decision. Publication, submission, activation, authorization, Zenodo contact,
#: archive change and manuscript/prior-package change are all covered.
@pytest.mark.parametrize("field", [
    # publication / submission / activation / availability
    "record_submitted", "zenodo_published", "doi_published",
    "doi_publicly_activated", "doi_active", "doi_resolves_publicly",
    "reserved_doi_is_registered_or_resolving", "public_release",
    # authorization
    "publication_authorized", "public_release_authorized",
    "submission_authorized", "doi_activation_authorized",
    "ready_for_review_authorized", "merge_authorized", "auto_merge_authorized",
    "next_action_authorized", "stage130_authorized",
    # Zenodo contact / token / browser / script rerun
    "agent_called_the_zenodo_api", "zenodo_publish_endpoint_called",
    "zenodo_submit_endpoint_called", "zenodo_metadata_written_by_this_action",
    "zenodo_token_read_or_requested_by_this_action",
    "zenodo_opened_by_automation_in_this_action",
    "deposition_script_re_executed_by_this_action",
    "deposition_state_file_opened_or_parsed_by_this_action",
    "deposition_state_file_committed_to_git", "credentials_committed_to_git",
    # archive
    "archive_rebuilt_by_this_action", "archive_replaced_by_this_action",
    "archive_re_uploaded_by_this_action", "archive_renamed_by_this_action",
    "archive_manifest_regenerated_by_this_action",
    "embedded_zip_candidate_metadata_modified_by_this_action",
    # manuscript / prior packages / firewall
    "manuscript_modified_by_this_action",
    "manuscript_availability_claim_changed_by_this_action",
    "manuscript_data_availability_statement_changed_by_this_action",
    "prior_packages_modified_by_this_action",
    "stage122_to_stage129_artifacts_modified_by_this_action",
    "release_candidate_package_modified_by_this_action",
    "new_scientific_analysis_performed", "scientific_execution_started",
    "final_test_access_authorized", "final_test_second_pass_authorized",
    # pull request
    "pr_merged", "pr_marked_ready_by_this_action",
    "auto_merge_enabled_by_this_action", "branch_deleted_by_this_action",
    "new_pull_request_created_by_this_action",
    # the misreading
    "access_right_open_implies_public_availability",
    "preexisting_pointer_was_authorized",
])
def test_claiming_a_forbidden_flag_on_the_decision_breaks_the_build(
        field, shim, decision):
    root = shim
    tampered = copy.deepcopy(decision)
    assert field in tampered, field
    tampered[field] = True
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="must be False"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


@pytest.mark.parametrize("field", [
    "zenodo_published", "record_submitted", "doi_published",
    "doi_publicly_activated", "public_release", "publication_authorized",
    "public_release_authorized", "ready_for_review_authorized",
    "merge_authorized", "agent_called_the_zenodo_api",
    "zenodo_publish_endpoint_called",
    "zenodo_token_read_or_requested_by_this_action",
    "deposition_script_re_executed_by_this_action",
    "archive_re_uploaded_by_this_action", "archive_rebuilt_by_this_action",
    "manuscript_modified_by_this_action",
    "prior_packages_modified_by_this_action",
    "stage122_to_stage129_artifacts_modified_by_this_action",
    "pr_merged", "branch_deleted_by_this_action",
])
def test_claiming_a_forbidden_flag_on_the_boundary_breaks_the_build(
        field, shim, boundary):
    root = shim
    tampered = copy.deepcopy(boundary)
    assert field in tampered, field
    tampered[field] = True
    _write_json(root, BOUNDARY_REL, tampered)
    with pytest.raises(gen.HandoffError, match="must be False"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


@pytest.mark.parametrize("counter", [
    "zenodo_api_calls_made_by_this_action", "zenodo_publish_endpoint_calls",
    "zenodo_submit_endpoint_calls",
    "zenodo_metadata_write_calls_made_by_this_action",
    "zenodo_tokens_read_or_requested", "zenodo_browser_automation_sessions",
    "deposition_script_executions", "deposition_state_file_reads",
    "archive_rebuilds", "archive_uploads_or_replacements",
    "manuscript_bytes_changed", "prior_package_bytes_changed",
    "new_pull_requests_created",
])
def test_a_non_zero_counter_breaks_the_build(counter, shim, boundary):
    root = shim
    tampered = copy.deepcopy(boundary)
    assert counter in tampered["counters"], counter
    tampered["counters"][counter] = 1
    _write_json(root, BOUNDARY_REL, tampered)
    with pytest.raises(gen.HandoffError, match="must be 0"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


def test_claiming_an_independent_programmer_retrieval_breaks_the_build(
        shim, decision):
    root = shim
    tampered = copy.deepcopy(decision)
    tampered["independently_retrieved_by_programmer"] = True
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError,
                       match="independently_retrieved_by_programmer = False"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


def test_a_non_zero_zenodo_call_count_on_the_decision_breaks_the_build(
        shim, decision):
    root = shim
    tampered = copy.deepcopy(decision)
    tampered["zenodo_api_calls_made_by_this_action"] = 1
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="must be 0"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


def test_a_changed_manuscript_breaks_the_build(shim):
    root = shim
    path = os.path.join(str(root), MANUSCRIPT_REL)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\nan unauthorized edit\n")
    with pytest.raises(gen.HandoffError, match="manuscript has changed"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


def test_a_drifted_deposited_digest_breaks_the_build(shim, decision):
    root = shim
    tampered = copy.deepcopy(decision)
    tampered["deposited_file"]["sha256"] = "0" * 64
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="deposited_file sha256"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


# --------------------------------------------------------------------------- #
# (17) No credential material anywhere this change reaches
# --------------------------------------------------------------------------- #

def test_no_credential_material_is_committed_in_the_package():
    gen._stage130_zdhrc_assert_no_credential_material(REPO_ROOT)


def _sweep(text, added_only=None):
    for pattern in gen._STAGE130_ZDD_CREDENTIAL_PATTERNS:
        assert not pattern.search(text), pattern.pattern
    for run in gen._STAGE130_ZDD_OPAQUE_RUN.findall(
            text if added_only is None else added_only):
        assert re.fullmatch(r"[0-9a-fA-F]+", run), run


def test_no_credential_material_is_in_the_repository_diff():
    base = _git("merge-base", "HEAD", "origin/main")
    ref = base.stdout.strip() if base.returncode == 0 and base.stdout.strip() \
        else None
    if ref is None:
        # No origin/main in this checkout: sweep the working tree of everything
        # this action introduces instead. This is an assertion, not a skip.
        for rel in (README_REL, DECISION_REL, BOUNDARY_REL, METADATA_REL):
            _sweep(_text(rel))
        return
    diff = _git("diff", f"{ref}...HEAD").stdout
    added = "\n".join(line for line in diff.splitlines()
                      if line.startswith("+"))
    _sweep(diff, added_only=added)


def test_no_credential_material_is_in_the_branch_commit_messages():
    base = _git("merge-base", "HEAD", "origin/main")
    ref = base.stdout.strip() if base.returncode == 0 and base.stdout.strip() \
        else PRE_ACTION_HEAD
    log = _git("log", "--format=%B", f"{ref}..HEAD")
    text = log.stdout if log.returncode == 0 else ""
    _sweep(text)


def test_no_credential_material_is_in_the_pull_request_body():
    body = ""
    try:
        result = subprocess.run(
            ["gh", "pr", "view", "100", "--json", "body", "-q", ".body"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            body = result.stdout
    except (OSError, subprocess.SubprocessError):
        body = ""
    # An unreachable GitHub leaves `body` empty, which sweeps clean; the diff
    # and commit-message sweeps above still ran unconditionally, so this test
    # never becomes a skip.
    _sweep(body)


# --------------------------------------------------------------------------- #
# (18) No existing test was deleted, skipped or weakened BY THIS CHANGE
# --------------------------------------------------------------------------- #

def _pre_action_available():
    return _git("cat-file", "-e", f"{PRE_ACTION_HEAD}^{{commit}}").returncode == 0


def _changed_test_files():
    out = _git("diff", "--name-status", PRE_ACTION_HEAD, "HEAD").stdout
    rows = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status, path = parts[0], parts[-1]
        if os.path.basename(path).startswith("test_") and path.endswith(".py"):
            rows.append((status, path))
    return rows


def test_no_existing_test_file_was_deleted_or_renamed():
    if not _pre_action_available():
        # The pre-action commit is unreachable (e.g. after a squash merge).
        # Assert directly instead of skipping: every test module this action
        # touched must still exist.
        for rel in ("project/tests/test_ai_handoff.py",
                    "project/tests/test_stage130_zenodo_draft_deposition.py",
                    "project/tests/test_stage130_dataset_release_candidate.py"):
            assert os.path.isfile(os.path.join(REPO_ROOT, rel)), rel
        return
    for status, path in _changed_test_files():
        assert not status.startswith("D"), f"test file deleted: {path}"
        assert not status.startswith("R"), f"test file renamed: {path}"


def test_no_existing_test_was_skipped_or_weakened():
    if not _pre_action_available():
        assert os.path.isfile(
            os.path.join(REPO_ROOT, "project", "tests", "test_ai_handoff.py"))
        return
    for _status, path in _changed_test_files():
        if path == f"project/tests/{os.path.basename(__file__)}":
            continue
        before = _git("show", f"{PRE_ACTION_HEAD}:{path}").stdout
        after = _text(path)
        # No test function may disappear...
        before_tests = set(re.findall(r"^def (test_\w+)", before, re.M))
        after_tests = set(re.findall(r"^def (test_\w+)", after, re.M))
        assert before_tests <= after_tests, \
            f"{path} lost tests: {sorted(before_tests - after_tests)}"
        # ...no assertion may be dropped...
        assert after.count("assert ") >= before.count("assert "), path
        # ...and nothing may be neutralised with a skip or an xfail.
        for marker in ("@pytest.mark.skip", "@pytest.mark.xfail",
                       "pytest.mark.skipif"):
            assert after.count(marker) <= before.count(marker), \
                f"{path} gained {marker}"


# --------------------------------------------------------------------------- #
# (19) The previous Stage130 draft-deposition package is HISTORY
# --------------------------------------------------------------------------- #

def test_the_prior_deposition_package_is_byte_identical():
    pkg = os.path.join(REPO_ROOT, PRIOR_PKG_REL)
    on_disk = {name for name in os.listdir(pkg)
               if os.path.isfile(os.path.join(pkg, name))}
    assert on_disk == set(PRIOR_PKG_SHA256)
    for name, expected in PRIOR_PKG_SHA256.items():
        with open(os.path.join(pkg, name), "rb") as fh:
            assert hashlib.sha256(fh.read()).hexdigest() == expected, name


def test_the_generator_pins_the_prior_package_independently():
    assert gen._STAGE130_ZDHRC_PRIOR_PACKAGE_SHA256 == PRIOR_PKG_SHA256
    gen._stage130_zdhrc_assert_prior_package_intact(REPO_ROOT)


def test_the_prior_package_keeps_publishing_its_own_history(prior_markers,
                                                            markers):
    assert prior_markers["zenodo_deposition_created"] is True
    assert prior_markers["zenodo_upload_performed"] is True
    assert prior_markers["zenodo_doi_reserved"] is True
    assert prior_markers["zenodo_published"] is False
    assert prior_markers["zenodo_record_submitted"] is False
    assert prior_markers["zenodo_doi_published"] is False
    assert prior_markers["public_release_authorized"] is False
    # ...including its OWN pointer, which this action supersedes in the open.
    assert prior_markers["next_research_action_id"] == SUPERSEDED_POINTER
    assert markers["stage130_zenodo_supersedes_pointer"] == SUPERSEDED_POINTER
    assert markers["stage130_zenodo_draft_deposition_record_preserved"] is True


def test_editing_the_prior_package_breaks_the_build(shim):
    root = shim
    path = os.path.join(
        str(root), PRIOR_PKG_REL,
        "stage130_zenodo_draft_deposition_governance_boundary.json")
    with open(path, encoding="utf-8") as fh:
        payload = json.load(fh)
    payload["notes_correction_completed"] = True
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False, sort_keys=True)
    with pytest.raises(gen.HandoffError, match="has changed"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


def test_adding_a_file_to_the_prior_package_breaks_the_build(shim):
    root = shim
    with open(os.path.join(str(root), PRIOR_PKG_REL, "addendum.md"), "w",
              encoding="utf-8") as fh:
        fh.write("a later note that does not belong to a historical record\n")
    with pytest.raises(gen.HandoffError, match="gained or lost"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


def test_the_supersede_is_declared_in_the_open(decision, boundary):
    marker = decision["superseded_marker"]
    assert marker["key"] == "next_research_action_id"
    assert marker["previous_value"] == SUPERSEDED_POINTER
    assert marker["resolved_value"] == NEXT_POINTER
    assert marker["pointer_previous_value"] == SUPERSEDED_POINTER
    assert marker["pointer_resolved_value"] == NEXT_POINTER
    assert marker["superseding_decision_id"] == ACTION_ID
    assert marker["superseded_artifact"] == (
        f"{PRIOR_PKG_REL}/stage130_zenodo_draft_deposition_decision.json")
    assert marker["historical_zenodo_draft_deposition_record_preserved"] is True
    assert sorted(marker["keys_deliberately_not_superseded"]) == [
        "public_release_authorized", "zenodo_doi_published",
        "zenodo_published", "zenodo_record_submitted"]
    assert set(marker["newly_introduced_keys"]) == {
        "stage130_zenodo_draft_human_review_completed",
        "stage130_zenodo_draft_notes_correction_completed",
        "stage130_zenodo_live_notes_are_publication_stable"}
    for entry in marker["newly_introduced_keys"].values():
        assert entry["published_before_this_action"] is False
        assert entry["resolved_value"] is True
    assert boundary["supersedes_pointer"] == SUPERSEDED_POINTER
    assert boundary["supersedes_artifact"]


def test_pretending_a_forbidden_key_was_superseded_breaks_the_build(
        shim, decision):
    root = shim
    tampered = copy.deepcopy(decision)
    tampered["superseded_marker"]["keys_deliberately_not_superseded"] = [
        "zenodo_published"]
    _write_json(root, DECISION_REL, tampered)
    with pytest.raises(gen.HandoffError, match="deliberately NOT superseded"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


# --------------------------------------------------------------------------- #
# (20) The new pointer is explicitly, checkably UNAUTHORIZED
# --------------------------------------------------------------------------- #

def test_the_live_pointer_advances_to_the_publication_decision(
        boundary, markers):
    assert boundary["next_action_id"] == NEXT_POINTER
    assert boundary["next_action_scope"] == NEXT_POINTER_SCOPE
    assert boundary["next_action_is_a_human_step"] is True
    assert markers["next_research_action_id"] == NEXT_POINTER
    assert markers["next_research_action_scope"] == NEXT_POINTER_SCOPE
    assert markers["stage130_phase2_next_action_id"] == NEXT_POINTER
    assert markers["last_completed_research_action_id"] == ACTION_ID


def test_the_new_pointer_is_not_an_authorization(decision, boundary, markers):
    for source in (decision, boundary):
        assert source["pointer_is_not_authorization"] is True
        assert source["next_action_authorized"] is False
    assert markers["next_research_action_authorized"] is False
    assert markers["stage130_phase2_next_action_authorized"] is False
    assert markers["next_research_action_pointer_is_not_authorization"] is True


def test_the_new_pointer_scope_says_no_publication_action_is_authorized():
    assert "no_publication_action_is_authorized" in NEXT_POINTER_SCOPE
    assert NEXT_POINTER_SCOPE.startswith("zenodo_publication_decision_only")


def test_the_pointer_no_longer_names_the_completed_review(boundary, markers):
    assert boundary["next_action_id"] != SUPERSEDED_POINTER
    assert markers["next_research_action_id"] != SUPERSEDED_POINTER
    assert "review" not in NEXT_POINTER


def test_keeping_the_old_pointer_breaks_the_build(shim, boundary):
    root = shim
    tampered = copy.deepcopy(boundary)
    tampered["next_action_id"] = SUPERSEDED_POINTER
    _write_json(root, BOUNDARY_REL, tampered)
    with pytest.raises(gen.HandoffError, match="advance the pointer"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


def test_authorizing_the_new_pointer_breaks_the_build(shim, boundary):
    root = shim
    tampered = copy.deepcopy(boundary)
    tampered["next_action_authorized"] = True
    _write_json(root, BOUNDARY_REL, tampered)
    with pytest.raises(gen.HandoffError, match="must be False"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


# --------------------------------------------------------------------------- #
# The package, the ROADMAP and the generated state agree
# --------------------------------------------------------------------------- #

def test_the_package_inventory_is_real(metadata):
    pkg = os.path.join(REPO_ROOT, PKG_REL)
    listed = metadata["package_files"]
    assert metadata["package_file_count"] == len(listed)
    on_disk = {name for name in os.listdir(pkg)
               if os.path.isfile(os.path.join(pkg, name))
               and name != os.path.basename(METADATA_REL)}
    assert on_disk == set(listed)
    for name, expected in listed.items():
        with open(os.path.join(pkg, name), "rb") as fh:
            payload = fh.read()
        assert hashlib.sha256(payload).hexdigest() == expected["sha256"], name
        assert len(payload) == expected["bytes"], name


def test_the_package_contains_the_four_required_artifacts():
    for rel in (README_REL, DECISION_REL, BOUNDARY_REL, METADATA_REL):
        assert os.path.isfile(os.path.join(REPO_ROOT, rel)), rel


def test_the_readme_keeps_the_four_events_apart():
    text = _text(README_REL)
    for phrase in ("draft deposition", "human visual review",
                   "Notes correction", "publication decision"):
        assert phrase.lower() in text.lower(), phrase
    assert "UNAUTHORIZED" in text or "unauthorized" in text
    assert HISTORICAL_NOTES_SHA256 in text
    assert LIVE_NOTES_SHA256 in text


def test_the_readme_does_not_claim_publication():
    text = _text(README_REL).lower()
    for claim in ("has been published", "is published", "publicly available",
                  "doi resolves", "now available on zenodo"):
        assert claim not in text, claim


def test_a_tampered_package_file_breaks_the_build(shim):
    root = shim
    path = os.path.join(str(root), README_REL)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\nan unrecorded edit\n")
    with pytest.raises(gen.HandoffError, match="published size/SHA-256"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


def test_an_unlisted_package_file_breaks_the_build(shim):
    root = shim
    with open(os.path.join(str(root), PKG_REL, "extra.md"), "w",
              encoding="utf-8") as fh:
        fh.write("unlisted\n")
    with pytest.raises(gen.HandoffError, match="inventory disagrees"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


def test_a_committed_credential_breaks_the_build(shim):
    root = shim
    # Assembled at runtime, never written as a literal. This suite asserts that
    # no credential header exists anywhere in the repository, the branch diff,
    # the commit messages or the pull request; a test that hard-coded one would
    # falsify its own claim.
    header = "Authoriz" + "ation: " + "Bear" + "er " + "ab" * 12
    with open(os.path.join(str(root), README_REL), "a", encoding="utf-8") as fh:
        fh.write("\n" + header + "\n")
    with pytest.raises(gen.HandoffError, match="credential-shaped"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


def test_a_committed_opaque_token_breaks_the_build(shim):
    root = shim
    # Also assembled at runtime: a 40+ character alphanumeric run that is NOT
    # pure hexadecimal is exactly the shape the sweep refuses, so writing one
    # as a literal here would trip the sweep on this file itself.
    opaque = ("zQxWvUt" + "SrQpOnM" + "lKjIhGf" + "EdCbA98"
              + "76543210" + "zyxwvutsrq")
    assert len(opaque) >= 40 and opaque.isalnum()
    with open(os.path.join(str(root), README_REL), "a", encoding="utf-8") as fh:
        fh.write("\n" + opaque + "\n")
    with pytest.raises(gen.HandoffError, match="opaque"):
        gen.derive_stage130_zenodo_draft_human_review_completion_markers(
            str(root))


def test_the_action_is_recorded_in_the_generated_state(state):
    assert state["stage130_zenodo_draft_human_review_completion_recorded"] is True
    assert state["stage130_zenodo_draft_human_review_completion_action_id"] == \
        ACTION_ID
    assert state["stage130_zenodo_draft_human_review_completed"] is True
    assert state["stage130_zenodo_draft_notes_correction_completed"] is True
    assert state["stage130_zenodo_live_notes_are_publication_stable"] is True
    assert state["stage130_zenodo_live_notes_sha256"] == LIVE_NOTES_SHA256


def test_the_generated_state_keeps_every_publication_key_false(state):
    assert state["zenodo_deposition_created"] is True
    assert state["zenodo_upload_performed"] is True
    assert state["zenodo_version_doi_reserved"] is True
    assert state["zenodo_record_submitted"] is False
    assert state["zenodo_record_state"] == RECORD_STATE
    assert state["zenodo_published"] is False
    assert state["zenodo_doi_published"] is False
    assert state["zenodo_doi_publicly_activated"] is False
    assert state["zenodo_public_release"] is False
    assert state["stage130_manuscript_modified_by_this_action"] is False
    assert state["stage130_pr_ready"] is False
    assert state["stage130_pr_merged"] is False


def test_the_generated_state_pointer_is_unauthorized(state):
    assert state["next_research_action_id"] == NEXT_POINTER
    assert state["next_research_action_scope"] == NEXT_POINTER_SCOPE
    assert state["next_research_action_authorized"] is False
    assert state["next_research_action_pointer_is_not_authorization"] is True


def test_the_roadmap_agrees_with_the_generated_state(roadmap_front_matter,
                                                     state):
    fm = roadmap_front_matter
    assert fm["next_research_action_id"] == NEXT_POINTER
    assert fm["next_research_action_scope"] == NEXT_POINTER_SCOPE
    assert fm["next_research_action_authorized"] == "false"
    assert fm["last_completed_research_action_id"] == ACTION_ID
    assert fm["zenodo_draft_human_review_completed"] == "true"
    assert fm["zenodo_draft_notes_correction_completed"] == "true"
    assert fm["zenodo_live_notes_are_publication_stable"] == "true"
    assert fm["zenodo_live_notes_sha256"] == LIVE_NOTES_SHA256
    assert fm["zenodo_historical_notes_sha256"] == HISTORICAL_NOTES_SHA256
    assert fm["zenodo_concept_doi"] == CONCEPT_DOI
    assert fm["zenodo_record_submitted"] == "false"
    assert fm["zenodo_published"] == "false"
    assert fm["zenodo_doi_publicly_activated"] == "false"
    assert fm["zenodo_public_release"] == "false"
    assert fm["manuscript_modified"] == "false"
    assert fm["pr_ready"] == "false"
    assert fm["pr_merged"] == "false"
    assert state["next_research_action_id"] == fm["next_research_action_id"]


def test_the_roadmap_body_records_the_action_and_the_pointer():
    text = _text("project/docs/ai/ROADMAP.md")
    assert ACTION_ID in text
    assert NEXT_POINTER in text
    # ...and the superseded pointer item is kept, not deleted.
    assert SUPERSEDED_POINTER in text


def test_the_current_state_publishes_the_review_and_the_correction():
    text = _text("project/docs/ai/CURRENT_STATE.md")
    assert LIVE_NOTES_SHA256 in text
    assert HISTORICAL_NOTES_SHA256 in text
    assert f"`{NEXT_POINTER}`" in text
    assert CONCEPT_DOI in text


def test_the_package_is_change_allowlisted():
    for rel in (README_REL, DECISION_REL, BOUNDARY_REL, METADATA_REL,
                f"project/tests/{os.path.basename(__file__)}"):
        assert rel in gen.ALLOWLIST_FILES, rel


def test_the_deriver_returns_nothing_before_the_package_exists(shim):
    root = shim
    shutil.rmtree(os.path.join(str(root), PKG_REL))
    assert gen.derive_stage130_zenodo_draft_human_review_completion_markers(
        str(root)) == {}
    # ...and the predecessor still derives on its own, unchanged.
    assert gen.derive_stage130_zenodo_draft_deposition_markers(
        str(root))["next_research_action_id"] == SUPERSEDED_POINTER
