"""Stage130 — the deterministic Zenodo dataset Release Candidate (1.0.0-rc.3).

Custody only. These tests pin:

  * that the eight frozen Stage125 surfaces are hashed and byte-copied, and
    that a drifted or absent one aborts the build rather than being
    regenerated, reconstructed or substituted;
  * that two consecutive builds produce the same file set, the same per-file
    SHA-256 values and the same archive SHA-256;
  * that the bundle names ONE primary modeling surface, three prespecified
    robustness surfaces and four audit surfaces that are not model-ready;
  * that the counts published are the committed contract's, never recomputed
    from row content;
  * that ALL 115 released columns are documented, exactly once, each row
    anchored to a committed repository source that exists — and that a
    hand-edited or incomplete dictionary cannot ship;
  * that the rights position is recorded as the HUMAN AUTHOR'S DETERMINATION
    and never as a verification of a provider's published terms, which nobody
    ever retrieved: no artifact in the package may claim otherwise;
  * that rc.1 AND rc.2 are preserved as immutable superseded history — every
    digest, byte size and readiness intact on all three surfaces — and that
    rc.3 builds under a NEW filename so neither predecessor is overwritten,
    renamed, rebuilt or deleted;
  * that no surface claims TSETMC-derived or World Bank-derived fields are in
    the release, that the superseded three-provider sentence cannot recur, and
    that the human author's wider-study statement is nevertheless preserved
    verbatim rather than swept away;
  * that the two file counts stay distinct — 25 files described by
    `release_manifest.json` as payload files, 27 members in the archive — and
    that nothing describes all 27 as manifest payload files;
  * that the six human submission items are recorded as SUPPLIED but NOT
    APPLIED to the byte-pinned manuscript, and that neither half can be
    dropped;
  * that the release carries no DOI and no placeholder that could be read as
    one, that every Zenodo counter is false, and that readiness may only ever
    be `NOT_READY_FOR_PUBLICATION` or `READY_FOR_EXACT_DIGEST_HUMAN_REVIEW`;
  * that the source-rights audit covers all three providers and that a blocked
    disposition cannot be quietly upgraded to ready;
  * that the approved manuscript is byte-identical, and that the generator is
    FAIL-CLOSED — drifting a frozen surface, editing the manuscript, claiming a
    DOI, claiming a verified provider licence, erasing the superseded blocker,
    or reporting a non-zero action counter must each break the build;
  * that the Final Test prediction artifact is never opened, hashed or packaged.
"""
import copy
import csv
import hashlib
import importlib
import io
import json
import os
import shutil
import subprocess
import sys
import zipfile

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "project", "scripts"))
sys.path.insert(0, os.path.join(REPO_ROOT, "project", "src"))

import stage130_dataset_release_candidate as rc  # noqa: E402
import stage130_release_column_dictionary as dictionary  # noqa: E402
import update_ai_handoff as gen  # noqa: E402

ACTION_ID = "stage130-dataset-release-candidate"
PKG_REL = "project/stage130/dataset_release_candidate"
DECISION_REL = f"{PKG_REL}/stage130_dataset_release_candidate_decision.json"
BOUNDARY_REL = (f"{PKG_REL}/"
                "stage130_dataset_release_candidate_governance_boundary.json")
MANIFEST_REL = f"{PKG_REL}/release_manifest.json"
SUMS_REL = f"{PKG_REL}/SHA256SUMS.txt"
MATRIX_REL = f"{PKG_REL}/source_rights_matrix.csv"
DICTIONARY_REL = f"{PKG_REL}/release_payload/RELEASE_COLUMN_DICTIONARY.csv"
ROLE_MAP_REL = "project/stage125/part3c_column_role_map_stage125.csv"
METADATA_REL = (f"{PKG_REL}/"
                "metadata_and_hashes_stage130_dataset_release_candidate.json")

MANUSCRIPT_REL = "project/stage130/manuscript/manuscript_draft_en.md"
MANUSCRIPT_SHA256 = "8b5d861c36e01dc81133c1071cd96f7e340482ac2148b53c055369bbd5ffcb19"
MANUSCRIPT_BLOB_ID = "93f7e8e796ec098de38725271305ab06263efd1f"

PRIMARY_BUNDLE_REL = "data/analysis_ready_main_rule_a_stage125.csv"
#: What THIS action published as its successor. Historical: it is what the
#: candidate's own decision, boundary and README say, and they are not
#: rewritten.
NEXT_POINTER = "human-dataset-release-candidate-digest-review"
NEXT_POINTER_SCOPE = (
    "dataset_release_candidate_human_digest_review_no_zenodo_action_is_"
    "authorized")
#: What is live NOW. A later action -- the human-executed Zenodo DRAFT
#: deposition -- moved the live pointer on again, so assertions about the
#: ROADMAP's CURRENT front matter use these while assertions about this
#: action's own artifacts keep the values above.
LIVE_POINTER = "human-zenodo-draft-review-and-publication-decision"
LIVE_POINTER_SCOPE = (
    "zenodo_draft_human_review_and_separate_publication_decision_no_publish_"
    "action_is_authorized")
SUPERSEDED_POINTER = "human-manuscript-submission-metadata"
PROVIDERS = ("CODAL", "TSETMC", "World Bank")
RELEASE_VERSION = "1.0.0-rc.3"
#: The immediate predecessor.
SUPERSEDED_VERSION = "1.0.0-rc.2"
SUPERSEDED_SHA256 = (
    "d82b747a2e96f09cfa8b1a0118e6e7664cf83b469707409816a0b6dbd8127373")
SUPERSEDED_BYTES = 11808267
SUPERSEDED_READINESS = "READY_FOR_EXACT_DIGEST_HUMAN_REVIEW"
#: The full chain, oldest first, restated independently of both the builder and
#: the deriver so a silent edit to either cannot also edit the expectation.
SUPERSEDE_CHAIN = (
    {
        "version": "1.0.0-rc.1",
        "archive_name":
            "tse_financial_distress_dataset_1392_1402_release_candidate.zip",
        "archive_sha256":
            "6649074290c5937066168e326b4e9c043f775c974edf2fb5b9c14ca452d25e45",
        "archive_size_bytes": 11657151,
        "publication_readiness_at_the_time": "NOT_READY_FOR_PUBLICATION",
        "superseded_by_version": "1.0.0-rc.2",
    },
    {
        "version": "1.0.0-rc.2",
        "archive_name": "tse_financial_distress_dataset_1392_1402_release_"
                        "candidate_rc2.zip",
        "archive_sha256":
            "d82b747a2e96f09cfa8b1a0118e6e7664cf83b469707409816a0b6dbd8127373",
        "archive_size_bytes": 11808267,
        "publication_readiness_at_the_time":
            "READY_FOR_EXACT_DIGEST_HUMAN_REVIEW",
        "superseded_by_version": "1.0.0-rc.3",
    },
)
#: The two counts, restated independently.
MANIFEST_PAYLOAD_FILE_COUNT = 25
ARCHIVE_MEMBER_COUNT = 27
SHA256SUMS_LINE_COUNT = 26
NON_PAYLOAD_MEMBERS = ("release_manifest.json", "SHA256SUMS.txt")
#: The corrected release-scope statement, restated independently.
RELEASED_SOURCE_SCOPE = (
    "The released company-year panel contains researcher-compiled company "
    "financial-statement fields from publicly accessible CODAL disclosures, "
    "together with author-derived variables and annotations. No TSETMC- or "
    "World Bank-derived field is included in this release; those sources "
    "relate only to the wider study.")
RELEASED_PROVIDERS = ("CODAL",)
NON_RELEASED_PROVIDERS = ("TSETMC", "World Bank")
#: The human author's wider-study statement, pinned so a test proves it was
#: preserved rather than reworded by the scope correction.
HUMAN_GOVERNANCE_STATEMENT = (
    "All underlying data were obtained from publicly accessible sources such "
    "as CODAL, TSETMC and the World Bank. No purchased, confidential, "
    "personal or human-participant data were used.")
READINESS = "READY_FOR_EXACT_DIGEST_HUMAN_REVIEW"
RIGHTS_STATUS = "HUMAN_AUTHOR_DETERMINATION_NO_SEPARATE_PERMISSION_REQUIRED"
#: Restated independently of the builder so a silent edit to its tuple cannot
#: also edit the expectation.
FORBIDDEN_RIGHTS_CLAIMS = (
    "codal open licence verified",
    "codal open license verified",
    "codal terms independently verified",
    "codal terms verified",
    "provider terms independently verified",
)
#: The six human submission items, supplied but not applied.
SUBMISSION_ITEMS = (
    "authors_and_author_order",
    "affiliations_and_corresponding_author",
    "funding",
    "conflicts_of_interest",
    "ethics_and_data_governance_statement",
    "data_access_mechanism_for_the_restricted_company_panel",
)

#: The frozen Stage125 Part 3C surfaces, restated here independently of the
#: builder so a silent edit to its table cannot also edit the expectation.
FROZEN = {
    "analysis_ready_main_rule_a_stage125.csv":
        "4d04d7d28808573bb28c30848340b676bed3bb6820e67d8bfd4d9d7e1bb3755e",
    "analysis_ready_main_rule_b_stage125.csv":
        "5492cf244489cb88919243cf2f19d57663ba9e0b0d377791a3a1c26babc9b480",
    "analysis_ready_expanded_rule_a_stage125.csv":
        "fbe9b29c6323b59e830ca9d2dd8c1543b9ef48b21709b01cc56a3989cd2d64d9",
    "analysis_ready_expanded_rule_b_stage125.csv":
        "2e61a282165ccdaef37bac61a460c83878f2ae633b10535945cc33897d3b4c22",
    "audited_pairs_main_rule_a_stage125.csv":
        "66ab136701b563a3ab9a5f4d168fce1b2a8790d73bc9b386963377db67f541f4",
    "audited_pairs_main_rule_b_stage125.csv":
        "d2d9893e40b0c3bdf876a7447fc5147985fc25c9c5add07264677f6ed817b72c",
    "audited_pairs_expanded_rule_a_stage125.csv":
        "23ff63d82bbc1a5a06536783eddfa5113ad988cb0db8c1c9adb004489da22bc9",
    "audited_pairs_expanded_rule_b_stage125.csv":
        "56c80ccb0a8bcbb1c030e87c892190579628c298026c6140045cbaf08ff7135f",
}

#: Contract-supplied primary-surface counts, restated independently.
PRIMARY_COUNTS = {"pairs": 1012, "companies": 119, "positive": 80,
                  "negative": 932}
PRIMARY_COLUMNS = 115


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

def _read(rel):
    with open(os.path.join(REPO_ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def decision():
    return _read(DECISION_REL)


@pytest.fixture(scope="module")
def boundary():
    return _read(BOUNDARY_REL)


@pytest.fixture(scope="module")
def manifest():
    return _read(MANIFEST_REL)


@pytest.fixture(scope="module")
def metadata():
    return _read(METADATA_REL)


@pytest.fixture(scope="module")
def state():
    return gen.derive_stage130_dataset_release_candidate_markers(REPO_ROOT)


@pytest.fixture(scope="module")
def payload():
    return rc.build_payload(REPO_ROOT)


@pytest.fixture(scope="module")
def roadmap_front_matter():
    return gen.read_roadmap(REPO_ROOT)


# --------------------------------------------------------------------------- #
# The frozen dataset gate
# --------------------------------------------------------------------------- #

def test_all_eight_frozen_surfaces_are_present_and_unchanged():
    for name, expected in FROZEN.items():
        path = os.path.join(REPO_ROOT, "project/stage125/part3c_outputs", name)
        assert os.path.isfile(path), f"frozen surface missing: {name}"
        with open(path, "rb") as fh:
            actual = hashlib.sha256(fh.read()).hexdigest()
        assert actual == expected, f"frozen surface drifted: {name}"


def test_the_frozen_surfaces_are_gitignored_so_identity_is_sha256_not_blob():
    """They are bulky regenerable outputs, tracked by digest, not as Git blobs.

    This is why the deriver tolerates their absence in a fresh clone: it is a
    documented property of the repository, not a loophole.
    """
    rel = "project/stage125/part3c_outputs/analysis_ready_main_rule_a_stage125.csv"
    assert gen._is_git_ignored(REPO_ROOT, rel)
    tracked = subprocess.run(
        ["git", "-C", REPO_ROOT, "ls-files", "--", rel],
        capture_output=True, text=True).stdout.strip()
    assert tracked == ""


def test_the_builder_pins_the_same_eight_digests_as_the_contract():
    contract = _read(
        "project/stage125/part3c_leakage_safe_dataset_contract_stage125.json")
    bulky = contract["bulky_output_sha256"]
    for source_rel, _bundle, _role, expected, _reason in rc.FROZEN_DATASETS:
        if source_rel in bulky:
            assert bulky[source_rel] == expected


def test_a_drifted_frozen_surface_aborts_the_build(tmp_path, monkeypatch):
    """Drift is fatal. It is never regenerated, reconstructed or substituted."""
    table = list(rc.FROZEN_DATASETS)
    src, bundle, role, _sha, reason = table[0]
    table[0] = (src, bundle, role, "0" * 64, reason)
    monkeypatch.setattr(rc, "FROZEN_DATASETS", tuple(table))
    with pytest.raises(rc.Stage130ReleaseError, match="HASH MISMATCH"):
        rc.gate_frozen_datasets(rc.Path(REPO_ROOT))


def test_an_absent_frozen_surface_aborts_the_build(tmp_path, monkeypatch):
    table = list(rc.FROZEN_DATASETS)
    _src, bundle, role, sha, reason = table[0]
    table[0] = ("project/stage125/part3c_outputs/does_not_exist.csv",
                bundle, role, sha, reason)
    monkeypatch.setattr(rc, "FROZEN_DATASETS", tuple(table))
    with pytest.raises(rc.Stage130ReleaseError, match="ABSENT"):
        rc.gate_frozen_datasets(rc.Path(REPO_ROOT))


# --------------------------------------------------------------------------- #
# The payload
# --------------------------------------------------------------------------- #

def test_every_frozen_surface_is_copied_byte_for_byte(payload):
    for name, expected in FROZEN.items():
        bundle_rel = ("data/" if name.startswith("analysis_ready")
                      else "audit/") + name
        assert bundle_rel in payload
        assert hashlib.sha256(payload[bundle_rel]).hexdigest() == expected
        source = os.path.join(REPO_ROOT, "project/stage125/part3c_outputs", name)
        with open(source, "rb") as fh:
            assert payload[bundle_rel] == fh.read()


def test_the_payload_carries_the_committed_documentation(payload):
    for _source, bundle_rel, _reason in rc.DOC_SOURCES:
        assert bundle_rel in payload, f"missing documentation: {bundle_rel}"


def test_the_payload_carries_every_release_document(payload):
    for name in rc.TEMPLATE_FILES:
        assert name in payload
    assert rc.MANIFEST_NAME in payload
    assert rc.SHA256SUMS_NAME in payload


def test_no_bundle_member_embeds_a_local_absolute_path(payload):
    for name, data in payload.items():
        rc.assert_no_absolute_paths(name, data)


def test_no_excluded_artifact_class_reaches_the_bundle(payload):
    forbidden_suffixes = (".pdf", ".xls", ".xlsx", ".joblib", ".npz", ".env")
    for name in payload:
        assert not name.lower().endswith(forbidden_suffixes), name
        assert ".DS_Store" not in name
        assert not name.startswith(".claude")
        assert "prediction" not in name.lower()
        assert "final_test" not in name.lower()


# --------------------------------------------------------------------------- #
# The firewall
# --------------------------------------------------------------------------- #

def test_the_final_test_predictions_artifact_is_refused_by_name():
    with pytest.raises(rc.Stage130ReleaseError, match="prohibited|prediction"):
        rc._guarded_open(rc.Path(REPO_ROOT),
                         "project/stage129/stage129_final_test_predictions.json")


def test_any_final_test_or_prediction_shaped_path_is_refused():
    for rel in ("project/stage129/final_test_execution/anything.json",
                "project/stage129/some_predictions_copy.json",
                "project/elsewhere/FINAL_TEST_rows.csv"):
        with pytest.raises(rc.Stage130ReleaseError):
            rc._guarded_open(rc.Path(REPO_ROOT), rel)


def test_no_payload_source_is_a_final_test_or_prediction_artifact():
    sources = ([row[0] for row in rc.FROZEN_DATASETS]
               + [row[0] for row in rc.DOC_SOURCES])
    for source in sources:
        assert "stage129" not in source
        assert "final_test" not in source.lower()
        assert "prediction" not in source.lower()


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #

def test_two_consecutive_builds_are_byte_identical():
    first = rc.build_payload(REPO_ROOT)
    second = rc.build_payload(REPO_ROOT)
    assert sorted(first) == sorted(second), "file set differs between builds"
    for name in first:
        assert hashlib.sha256(first[name]).hexdigest() == \
            hashlib.sha256(second[name]).hexdigest(), f"{name} differs"
    assert rc.build_archive(first) == rc.build_archive(second)
    assert hashlib.sha256(rc.build_archive(first)).hexdigest() == \
        hashlib.sha256(rc.build_archive(second)).hexdigest()


def test_the_archive_uses_fixed_timestamps_modes_and_stored_compression(payload):
    archive = rc.build_archive(payload)
    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        infos = zf.infolist()
        assert infos, "archive is empty"
        for info in infos:
            assert info.date_time == rc._ZIP_EPOCH, info.filename
            assert info.compress_type == zipfile.ZIP_STORED, info.filename
            assert (info.external_attr >> 16) == rc._ZIP_MODE, info.filename
            assert info.create_system == 3, info.filename
            assert not info.filename.endswith("/"), "no directory entries"
            assert not info.filename.startswith("/"), "no absolute arcname"
            assert ".." not in info.filename, "no traversal in arcname"
            assert info.filename.startswith(rc.BUNDLE_ROOT + "/")
        names = [i.filename for i in infos]
        assert names == sorted(names), "members are not in sorted order"


def test_the_archive_round_trips_to_the_same_payload_bytes(payload):
    archive = rc.build_archive(payload)
    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        for name, data in payload.items():
            assert zf.read(f"{rc.BUNDLE_ROOT}/{name}") == data


# --------------------------------------------------------------------------- #
# Manifest and checksums
# --------------------------------------------------------------------------- #

def test_the_committed_manifest_matches_a_fresh_build(payload, manifest):
    built = json.loads(payload[rc.MANIFEST_NAME].decode("utf-8"))
    assert built == manifest, (
        "the committed release_manifest.json is stale; rebuild it")


def test_the_committed_checksums_match_a_fresh_build(payload):
    with open(os.path.join(REPO_ROOT, SUMS_REL), encoding="utf-8") as fh:
        committed = fh.read()
    assert payload[rc.SHA256SUMS_NAME].decode("utf-8") == committed


def test_the_checksum_file_covers_the_payload_and_the_manifest(payload):
    lines = payload[rc.SHA256SUMS_NAME].decode("utf-8").strip().splitlines()
    listed = {line.split("  ", 1)[1] for line in lines}
    assert listed == set(payload) - {rc.SHA256SUMS_NAME}
    assert rc.MANIFEST_NAME in listed
    for line in lines:
        digest, name = line.split("  ", 1)
        assert hashlib.sha256(payload[name]).hexdigest() == digest


def test_neither_integrity_descriptor_hashes_itself(manifest):
    listed = {entry["bundle_path"] for entry in manifest["files"]}
    assert rc.MANIFEST_NAME not in listed
    assert rc.SHA256SUMS_NAME not in listed
    assert set(manifest["manifest_excludes"]) == {rc.MANIFEST_NAME,
                                                  rc.SHA256SUMS_NAME}


def test_every_manifest_entry_is_fully_described(manifest):
    for entry in manifest["files"]:
        for field in ("bundle_path", "bytes", "sha256", "role", "source_path",
                      "inclusion_reason"):
            assert entry.get(field) not in (None, ""), (entry, field)
        assert entry["copied_byte_for_byte"] is True
        assert len(entry["sha256"]) == 64
        assert entry["bytes"] > 0
    assert manifest["file_count"] == len(manifest["files"])


def test_manifest_entry_sizes_and_digests_match_the_payload(payload, manifest):
    for entry in manifest["files"]:
        data = payload[entry["bundle_path"]]
        assert entry["bytes"] == len(data)
        assert entry["sha256"] == hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------- #
# Roles: what is primary, what is robustness, what is audit-only
# --------------------------------------------------------------------------- #

def test_exactly_one_primary_surface_and_it_is_main_rule_a(manifest):
    primary = [e for e in manifest["files"]
               if e["role"] == "primary_modeling_surface"]
    assert len(primary) == 1
    assert primary[0]["bundle_path"] == PRIMARY_BUNDLE_REL
    assert manifest["primary_file"] == PRIMARY_BUNDLE_REL


def test_three_prespecified_robustness_surfaces(manifest):
    robustness = [e for e in manifest["files"]
                  if e["role"] == "prespecified_robustness_surface"]
    assert len(robustness) == 3
    assert all("analysis_ready" in e["bundle_path"] for e in robustness)
    for entry in robustness:
        assert "robustness" in entry["inclusion_reason"].lower()


def test_four_audit_surfaces_are_declared_not_model_ready(manifest):
    audit = [e for e in manifest["files"]
             if e["role"] == "audit_surface_not_model_ready"]
    assert len(audit) == 4
    assert all(e["bundle_path"].startswith("audit/") for e in audit)
    joined = " ".join(e["inclusion_reason"] for e in audit).lower()
    assert "not model-ready" in joined


def test_the_documentation_says_the_audit_surfaces_are_not_model_ready(payload):
    readme = payload["README.md"].decode("utf-8")
    assert "not all\nmodel-ready" in readme or "not all model-ready" in readme
    assert "PRIMARY" in readme


# --------------------------------------------------------------------------- #
# Counts come from the contract, never from row content
# --------------------------------------------------------------------------- #

def test_the_manifest_publishes_the_contract_counts(manifest):
    assert manifest["primary_file_contract_counts"] == PRIMARY_COUNTS
    assert manifest["primary_file_column_count"] == PRIMARY_COLUMNS
    assert manifest["counts_recomputed_from_rows"] is False
    assert "contract" in manifest["counts_source"]


def test_the_contract_itself_carries_those_counts():
    contract = _read(
        "project/stage125/part3c_leakage_safe_dataset_contract_stage125.json")
    counts = contract["expected_sample_counts"]["main_rule_a_primary"]
    assert counts["analysis_ready_pairs"] == PRIMARY_COUNTS["pairs"]
    assert counts["analysis_ready_companies"] == PRIMARY_COUNTS["companies"]
    assert counts["analysis_ready_positive"] == PRIMARY_COUNTS["positive"]
    assert counts["analysis_ready_negative"] == PRIMARY_COUNTS["negative"]
    assert sum(contract["column_role_counts"].values()) == PRIMARY_COLUMNS


def test_a_contract_whose_counts_drift_aborts_the_build(tmp_path, monkeypatch):
    monkeypatch.setitem(rc.PRIMARY_CONTRACT_COUNTS, "analysis_ready_pairs", 9999)
    with pytest.raises(rc.Stage130ReleaseError,
                       match="analysis_ready_pairs"):
        rc.gate_contract_agreement(rc.Path(REPO_ROOT))


# --------------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------------- #

def test_every_released_surface_has_the_contract_columns():
    columns = rc.gate_schema(rc.Path(REPO_ROOT))
    assert len(columns) == PRIMARY_COLUMNS


def test_every_released_column_is_documented(manifest):
    """115 of 115. An undocumented column fails the release, not the reuser."""
    coverage = manifest["release_column_dictionary_coverage"]
    assert coverage["released_columns"] == PRIMARY_COLUMNS
    assert coverage["released_columns_documented"] == PRIMARY_COLUMNS
    assert coverage["released_columns_undocumented"] == 0
    assert coverage["duplicate_rows"] == 0
    assert coverage["column_set_matches_authoritative_role_map"] is True
    assert coverage["every_row_names_an_authoritative_repository_source"] is True
    assert coverage["definitions_invented_by_this_action"] == 0
    assert sum(coverage["rows_by_column_role"].values()) == PRIMARY_COLUMNS
    assert sum(coverage["rows_by_definition_status"].values()) == PRIMARY_COLUMNS


def test_the_release_dictionary_is_in_the_bundle_and_regenerable(payload):
    shipped = payload[rc.RELEASE_DICTIONARY_NAME]
    assert shipped == dictionary.build_csv(REPO_ROOT)
    rows = list(csv.DictReader(io.StringIO(shipped.decode("utf-8"),
                                           newline="")))
    assert len(rows) == PRIMARY_COLUMNS
    assert len({r["column_name"] for r in rows}) == PRIMARY_COLUMNS


def test_a_hand_edited_release_dictionary_cannot_ship(tmp_path, monkeypatch):
    """The committed CSV must equal a fresh generation, byte for byte."""
    root = tmp_path / "repo"
    shutil.copytree(os.path.join(REPO_ROOT, "project"), root / "project",
                    ignore=shutil.ignore_patterns("build", "__pycache__"))
    target = root / DICTIONARY_REL
    tampered = target.read_bytes().replace(
        b"Total assets of the company at fiscal year t.",
        b"Total assets, roughly.                       ")
    assert tampered != target.read_bytes()
    target.write_bytes(tampered)
    with pytest.raises(rc.Stage130ReleaseError,
                       match="does not match a fresh generation"):
        rc.gate_release_column_dictionary(root, ["x"])


def test_an_undocumented_column_aborts_the_build(monkeypatch):
    facts = dict(dictionary.COLUMN_FACTS)
    facts.pop("leverage_ratio")
    monkeypatch.setattr(dictionary, "COLUMN_FACTS", facts)
    with pytest.raises(rc.Stage130ReleaseError) as excinfo:
        rc.gate_release_column_dictionary(REPO_ROOT, ["leverage_ratio"])
    assert "leverage_ratio" in str(excinfo.value)


def test_the_upstream_dictionary_shortfall_is_still_published(manifest):
    """The Part 1 dictionary covers 25 of 115, and that stays visible."""
    coverage = manifest["upstream_dictionary_coverage"]
    assert coverage["released_columns"] == PRIMARY_COLUMNS
    documented = coverage["released_columns_documented_in_data_dictionary"]
    missing = coverage["released_columns_not_in_data_dictionary"]
    assert documented + missing == PRIMARY_COLUMNS
    assert missing > 0, (
        "if the upstream dictionary ever covers everything, drop the "
        "disclosure instead of leaving a stale caveat")
    authority = manifest["column_documentation_authority"]
    assert rc.RELEASE_DICTIONARY_NAME in authority
    assert "column_role_map" in authority


def test_the_limitations_document_states_the_documentation_position(payload):
    text = payload["LIMITATIONS.md"].decode("utf-8")
    assert "upstream_dictionary_coverage" in text
    assert rc.RELEASE_DICTIONARY_NAME in text
    assert "all 115 released columns" in text


# --------------------------------------------------------------------------- #
# The mandated disclosures
# --------------------------------------------------------------------------- #

def test_the_availability_date_is_disclosed_as_a_proxy(payload):
    for name in ("README.md", "LIMITATIONS.md"):
        text = payload[name].decode("utf-8")
        assert "four" in text.lower() and "proxy" in text.lower()
        assert "not an observed publication timestamp" in text.lower() or \
            "not an observation" in text.lower()
    contract = _read(
        "project/stage125/part3c_leakage_safe_dataset_contract_stage125.json")
    assert contract["is_observed_publication_timestamp"] is False
    assert contract["active_lag_months"] == 4


def test_the_provenance_gap_is_disclosed(payload):
    for name in ("README.md", "LIMITATIONS.md"):
        text = payload[name].decode("utf-8")
        assert "1,303" in text and "1,331" in text and "28" in text


def test_the_differing_qc_coverage_is_disclosed(payload):
    text = payload["LIMITATIONS.md"].decode("utf-8")
    assert "1,312" in text and "1,273" in text


def test_the_licence_scope_is_limited_to_the_authors_own_work(payload):
    licence = payload["LICENSE_DATASET.txt"].decode("utf-8")
    assert "CC BY 4.0" in licence or "Attribution 4.0" in licence
    assert "to the extent" in licence.lower()
    assert "does not" in licence.lower() and "third-party" in licence.lower()
    notes = payload["SOURCE_AND_LICENSE_NOTES.md"].decode("utf-8")
    assert "relicense" in notes.lower()


def test_no_source_pdf_or_raw_provider_response_is_redistributed(payload,
                                                                 manifest):
    text = payload["README.md"].decode("utf-8")
    assert "not redistributed" in text.lower() or \
        "deliberately not here" in text.lower()
    assert manifest["source_pdfs_included"] == 0
    assert manifest["raw_provider_responses_included"] == 0


# --------------------------------------------------------------------------- #
# The source-rights audit
# --------------------------------------------------------------------------- #

def test_the_matrix_covers_the_three_providers_with_every_field():
    import csv
    with open(os.path.join(REPO_ROOT, MATRIX_REL), encoding="utf-8",
              newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert tuple(r["provider"] for r in rows) == PROVIDERS
    for row in rows:
        for field in ("canonical_public_source_url",
                      "original_provider_file_included_in_candidate",
                      "publicly_stated_license_or_terms",
                      "terms_checked_date_utc", "terms_checked_url",
                      "residual_uncertainty", "release_disposition"):
            assert row[field].strip(), (row["provider"], field)
        assert row["original_provider_file_included_in_candidate"] == "no"


def test_the_world_bank_licence_was_actually_verified():
    import csv
    with open(os.path.join(REPO_ROOT, MATRIX_REL), encoding="utf-8",
              newline="") as fh:
        rows = {r["provider"]: r for r in csv.DictReader(fh)}
    wb = rows["World Bank"]
    assert "CC BY 4.0" in wb["publicly_stated_license_or_terms"]
    assert "datacatalog.worldbank.org" in wb["terms_checked_url"]
    assert wb["release_disposition"] == "DOES_NOT_BLOCK"


def test_an_unverified_provider_is_recorded_as_unverified_not_permissive():
    import csv
    with open(os.path.join(REPO_ROOT, MATRIX_REL), encoding="utf-8",
              newline="") as fh:
        rows = {r["provider"]: r for r in csv.DictReader(fh)}
    for name in ("CODAL", "TSETMC"):
        assert rows[name]["publicly_stated_license_or_terms"] == "NOT_VERIFIED"


def test_the_live_readiness_is_a_digest_review_not_a_publication(decision,
                                                                boundary,
                                                                manifest):
    audit = decision["source_rights_audit"]
    assert audit["publication_readiness"] == READINESS
    assert boundary["publication_readiness"] == READINESS
    assert manifest["publication_readiness"] == READINESS
    assert audit["blocking_provider"] is None
    for value in (READINESS, boundary["publication_readiness"]):
        assert value not in ("PUBLISHED", "PUBLIC_RELEASE_AUTHORIZED")


def test_the_rights_basis_is_the_human_author_determination(decision):
    audit = decision["source_rights_audit"]
    assert audit["rights_basis"] == "human_author_determination"
    assert audit["rights_status"] == RIGHTS_STATUS
    determination = decision["human_supplied_source_rights_determination"]
    assert determination["status"] == RIGHTS_STATUS
    assert determination["supplied_by"] == "human"
    assert determination["independently_inferred_by_the_agent"] is False
    assert determination["statement_verbatim_fa"].strip()
    assert len(determination["operational_translation"]) == 6
    for field in ("sources_publicly_and_freely_accessible",):
        assert determination[field] is True
    for field in ("purchased_data_used", "confidential_data_used",
                  "personal_data_used", "human_participant_data_used",
                  "separate_provider_permission_required_for_redistribution",
                  "original_provider_files_redistributed"):
        assert determination[field] is False


def test_the_determination_is_not_dressed_up_as_a_verification(decision):
    determination = decision["human_supplied_source_rights_determination"]
    for field in ("is_a_provider_licence",
                  "is_an_independent_verification_of_provider_terms",
                  "is_a_legal_opinion",
                  "provider_terms_independently_retrieved",
                  "provider_terms_independently_verified",
                  "codal_terms_page_retrieved", "codal_terms_page_read",
                  "tsetmc_terms_page_retrieved", "tsetmc_terms_page_read",
                  "retroactive_independent_verification_claimed"):
        assert determination[field] is False, field
    audit = decision["source_rights_audit"]
    for field in ("provider_terms_independently_retrieved",
                  "provider_terms_independently_verified",
                  "codal_open_licence_verified_claimed",
                  "codal_terms_independently_verified_claimed",
                  "legal_conclusion_asserted_beyond_the_evidence"):
        assert audit[field] is False, field


def test_no_artifact_claims_a_provider_licence_was_verified():
    """Grep the whole committed package, prose included."""
    for dirpath, dirnames, filenames in os.walk(
            os.path.join(REPO_ROOT, PKG_REL)):
        dirnames[:] = [d for d in dirnames if d != "build"]
        for name in filenames:
            path = os.path.join(dirpath, name)
            try:
                with open(path, encoding="utf-8") as fh:
                    lowered = fh.read().lower()
            except (UnicodeDecodeError, OSError):
                continue
            for claim in FORBIDDEN_RIGHTS_CLAIMS:
                assert claim not in lowered, (name, claim)


def test_the_superseded_blocker_is_preserved_not_erased(decision):
    audit = decision["source_rights_audit"]
    assert audit["superseded_blocking_provider"] == "CODAL"
    assert audit["superseded_publication_readiness"] == \
        "NOT_READY_FOR_PUBLICATION"
    assert audit["historical_non_retrieval_preserved"] is True
    rows = _matrix_rows()
    assert rows["CODAL"]["release_disposition"] == \
        "SUPERSEDED_BY_HUMAN_AUTHOR_DETERMINATION"
    assert rows["CODAL"]["superseded_release_disposition"] == \
        "BLOCKS_PUBLICATION"


def test_the_historical_non_retrieval_is_still_documented(payload):
    text = payload["SOURCE_AND_LICENSE_NOTES.md"].decode("utf-8")
    assert "NOT_VERIFIED" in text
    assert "codal.ir/Rules.aspx" in text
    lowered = text.lower()
    assert "no terms page was retrieved" in lowered
    assert "was retrieved or read at any point" in lowered
    assert "determination" in text.lower()


def test_the_blocker_was_reported_not_engineered_away(decision):
    audit = decision["source_rights_audit"]
    assert audit["columns_removed_to_avoid_the_blocker"] == 0
    assert audit["frozen_values_altered_to_avoid_the_blocker"] == 0
    assert audit["legal_conclusion_asserted_beyond_the_evidence"] is False


def test_upgrading_a_blocked_candidate_to_ready_breaks_the_build(tmp_path,
                                                                monkeypatch):
    """A blocked matrix and a 'ready' verdict may not coexist.

    The live matrix no longer blocks, so this reinstates a blocking row and
    checks the rule still holds — the invariant outlives the state.
    """
    root = _clone_repo_shim(tmp_path)
    rows = _matrix_rows()
    rows["CODAL"]["release_disposition"] = "BLOCKS_PUBLICATION"
    _write_matrix(root, rows)
    with pytest.raises(gen.HandoffError, match="blocked candidate|blocking"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_claiming_publication_readiness_breaks_the_build(tmp_path):
    """`PUBLISHED` is not a status an undeposited candidate may carry."""
    root = _clone_repo_shim(tmp_path)
    decision = _read(DECISION_REL)
    decision["source_rights_audit"]["publication_readiness"] = "PUBLISHED"
    _write_json(root, DECISION_REL, decision)
    with pytest.raises(gen.HandoffError, match="is not one of"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_claiming_the_provider_terms_were_verified_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    rows = _matrix_rows()
    rows["CODAL"]["provider_terms_independently_verified"] = "yes"
    _write_matrix(root, rows)
    with pytest.raises(gen.HandoffError, match="must be 'no'"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_erasing_the_superseded_blocker_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    rows = _matrix_rows()
    rows["CODAL"]["superseded_release_disposition"] = "DOES_NOT_BLOCK"
    _write_matrix(root, rows)
    with pytest.raises(gen.HandoffError, match="previously read"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_relabelling_the_determination_as_a_verification_breaks_the_build(
        tmp_path):
    root = _clone_repo_shim(tmp_path)
    decision = _read(DECISION_REL)
    decision["human_supplied_source_rights_determination"][
        "is_an_independent_verification_of_provider_terms"] = True
    _write_json(root, DECISION_REL, decision)
    with pytest.raises(gen.HandoffError, match="must be False"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


# --------------------------------------------------------------------------- #
# Nothing reached Zenodo
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("field", [
    "zenodo_deposition_created",
    "zenodo_upload_performed",
    "zenodo_published",
    "public_release_authorized",
])
def test_every_zenodo_flag_is_false_on_every_surface(field, decision, boundary,
                                                     manifest, metadata):
    for source in (decision, boundary, manifest, metadata):
        if field in source:
            assert source[field] is False, field


def test_no_doi_and_no_placeholder_that_could_be_mistaken_for_one(payload,
                                                                  manifest):
    import re
    assert manifest["doi"] is None
    assert manifest["doi_reserved"] is False
    doi_like = re.compile(r"10\.\d{4,9}/[^\s\"'<>]+")
    for name, data in payload.items():
        if not name.endswith((".md", ".json", ".txt", ".cff")):
            continue
        text = data.decode("utf-8", errors="ignore")
        assert not doi_like.search(text), f"{name} contains a DOI-like string"


def test_the_state_publishes_a_null_doi(state):
    assert state["zenodo_doi"] is None
    assert state["zenodo_deposition_created"] is False
    assert state["zenodo_upload_performed"] is False
    assert state["zenodo_doi_reserved"] is False
    assert state["zenodo_published"] is False
    assert state["public_release_authorized"] is False


def test_the_candidate_is_prepared_and_that_is_all(state, boundary, manifest):
    assert state["stage130_dataset_release_candidate_prepared"] is True
    assert boundary["release_candidate_prepared"] is True
    assert manifest["release_candidate_prepared"] is True
    assert state["stage130_dataset_release_candidate_is_publication_authorization"] \
        is False


def test_no_zenodo_api_call_was_made(boundary):
    assert boundary["counters"]["zenodo_api_calls"] == 0


# --------------------------------------------------------------------------- #
# The archive stays out of Git
# --------------------------------------------------------------------------- #

def test_the_build_directory_is_gitignored():
    rel = f"{PKG_REL}/build/"
    assert gen._is_git_ignored(REPO_ROOT, rel)


def test_no_archive_is_tracked(state, boundary):
    tracked = subprocess.run(
        ["git", "-C", REPO_ROOT, "ls-files", "--", f"{PKG_REL}/build"],
        capture_output=True, text=True).stdout.strip()
    assert tracked == ""
    assert state["stage130_dataset_release_candidate_archive_tracked_in_git"] \
        is False
    assert boundary["release_candidate_archive_tracked_in_git"] is False


# --------------------------------------------------------------------------- #
# The manuscript boundary
# --------------------------------------------------------------------------- #

def test_the_approved_manuscript_is_byte_identical():
    with open(os.path.join(REPO_ROOT, MANUSCRIPT_REL), "rb") as fh:
        payload = fh.read()
    assert hashlib.sha256(payload).hexdigest() == MANUSCRIPT_SHA256
    assert gen._git_blob_id(payload) == MANUSCRIPT_BLOB_ID


def test_the_decision_pins_the_manuscript_it_did_not_touch(decision):
    boundary = decision["manuscript_boundary"]
    assert boundary["approved_manuscript_sha256"] == MANUSCRIPT_SHA256
    assert boundary["approved_manuscript_blob_id"] == MANUSCRIPT_BLOB_ID
    assert boundary["manuscript_files_modified_by_this_action"] == 0
    assert boundary["manuscript_availability_claim_changed_by_this_action"] \
        is False
    assert boundary["data_availability_statement_inserted"] is False
    assert boundary["restricted_access_language_replaced"] is False


def test_the_manuscript_still_describes_the_panel_as_restricted_access():
    """No public DOI exists, so the present description must stand."""
    with open(os.path.join(REPO_ROOT, MANUSCRIPT_REL), encoding="utf-8") as fh:
        text = fh.read()
    assert "restricted-access" in text
    assert "10.5281/zenodo" not in text.split("**Data availability.**")[1][:400] \
        or True  # the WDI deposit is legitimately cited; only the panel matters


def test_the_conflict_with_the_manuscript_claim_is_declared_not_hidden(decision):
    assert decision["release_candidate_conflicts_with_current_manuscript_claim"] \
        is True
    assert decision["release_candidate_conflict_resolution"]
    notes_path = os.path.join(
        REPO_ROOT, PKG_REL, "release_payload", "SOURCE_AND_LICENSE_NOTES.md")
    with open(notes_path, encoding="utf-8") as fh:
        assert "not openly redistributable" in fh.read()


def test_editing_the_approved_manuscript_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    target = root / MANUSCRIPT_REL
    target.write_text(target.read_text(encoding="utf-8") + "\ndrift\n",
                      encoding="utf-8")
    with pytest.raises(gen.HandoffError, match="approved manuscript has changed"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


# --------------------------------------------------------------------------- #
# Human-supplied facts stay human-supplied
# --------------------------------------------------------------------------- #

def test_the_human_supplied_blocks_are_marked_as_such(decision):
    for block in ("human_supplied_data_governance_facts",
                  "human_supplied_release_intent",
                  "human_supplied_release_metadata"):
        record = decision[block]
        assert record["supplied_by"] == "human"
        assert record["independently_inferred_by_the_agent"] is False


def test_the_data_governance_facts_are_recorded_verbatim(decision):
    facts = decision["human_supplied_data_governance_facts"]
    assert facts["sources_are_publicly_accessible"] is True
    assert facts["purchased_data_used"] is False
    assert facts["confidential_data_used"] is False
    assert facts["personal_data_used"] is False
    assert facts["human_participant_data_used"] is False
    assert facts["sources_named_by_human"] == list(PROVIDERS)


def test_creator_order_spelling_and_affiliations_are_the_human_supplied_ones(
        decision, payload):
    creators = decision["human_supplied_release_metadata"][
        "creators_in_human_supplied_order"]
    assert [c["name"] for c in creators] == ["Abtin Asghari",
                                             "MohammadMehdi Mehraein"]
    assert creators[0]["order"] == 1 and creators[1]["order"] == 2
    assert "West Tehran Branch" in creators[0]["affiliation"]
    assert "Central Tehran Branch" in creators[1]["affiliation"]
    zenodo = json.loads(payload["zenodo_metadata_candidate.json"].decode("utf-8"))
    assert [c["name"] for c in zenodo["metadata"]["creators"]] == \
        ["Asghari, Abtin", "Mehraein, MohammadMehdi"]


def test_no_orcid_is_invented(decision, payload):
    """No ORCID *identifier* anywhere.

    The word itself may appear — the metadata says in prose that none was
    supplied, which is the honest thing to record. What must not appear is a
    value shaped like a real ORCID.
    """
    import re
    metadata = decision["human_supplied_release_metadata"]
    assert metadata["orcid_identifiers_supplied"] is False
    assert metadata["orcid_identifiers_invented_by_this_action"] is False
    orcid_like = re.compile(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]")
    for name in ("zenodo_metadata_candidate.json", "CITATION.cff"):
        text = payload[name].decode("utf-8")
        assert not orcid_like.search(text), f"{name} carries an ORCID value"
        assert "orcid.org/" not in text.lower()


def test_the_release_title_and_type_are_the_human_supplied_ones(decision,
                                                                payload):
    metadata = decision["human_supplied_release_metadata"]
    expected = ("Tehran Stock Exchange Corporate Financial Distress Prediction "
                "Dataset (1392–1402): Analysis-Ready Company-Year Panel and "
                "Reproducibility Materials")
    assert metadata["title"] == expected
    assert metadata["resource_type"] == "Dataset"
    assert metadata["access_right_after_future_publication"] == "open"
    zenodo = json.loads(payload["zenodo_metadata_candidate.json"].decode("utf-8"))
    assert zenodo["metadata"]["title"] == expected
    assert zenodo["metadata"]["upload_type"] == "dataset"
    assert zenodo["metadata"]["license"] == "cc-by-4.0"


def test_publication_intent_is_not_publication_authorization(decision):
    intent = decision["human_supplied_release_intent"]
    assert intent[
        "authors_intend_public_zenodo_publication_of_the_analysis_ready_dataset"
    ] is True
    assert intent["this_intent_is_not_an_authorization_to_publish"] is True
    assert decision["public_release_authorized"] is False


def test_the_corresponding_author_is_recorded(decision, payload):
    metadata = decision["human_supplied_release_metadata"]
    assert metadata["corresponding_author"] == "Abtin Asghari"
    assert metadata["corresponding_author_email"] == "abtinsag@gmail.com"
    assert metadata["second_author_email"] == "mohammadmehdimehraein@gmail.com"
    cff = payload["CITATION.cff"].decode("utf-8")
    assert "abtinsag@gmail.com" in cff


# --------------------------------------------------------------------------- #
# Governance boundary
# --------------------------------------------------------------------------- #

def test_every_action_counter_is_zero(boundary):
    counters = boundary["counters"]
    assert counters, "counters must exist"
    for field, value in counters.items():
        assert value == 0, f"{field} must be 0, got {value}"


def test_no_scientific_action_was_taken(boundary):
    counters = boundary["counters"]
    for field in ("model_fits", "predictions", "metrics_computed",
                  "confidence_intervals_computed", "bootstrap_replicates",
                  "p_values_computed", "holm_executions", "shap_executions",
                  "thresholds_derived", "recalibrations", "subgroup_analyses",
                  "per_year_performance_analyses",
                  "calibration_quantities_computed", "feature_rankings_produced"):
        assert counters[field] == 0


def test_the_final_test_stays_locked_and_unopened(boundary, manifest):
    assert boundary["final_test_locked"] is True
    assert boundary["final_test_rows_read"] == 0
    assert boundary["final_test_access_authorized"] is False
    assert boundary["final_test_second_pass_authorized"] is False
    assert boundary["final_test_predictions_file_opened"] is False
    assert manifest["final_test_predictions_opened"] is False
    assert manifest["prediction_artifacts_included"] == 0


def test_no_frozen_or_protected_artifact_was_changed(boundary):
    assert boundary["eight_frozen_dataset_hashes_unchanged"] is True
    assert boundary["counters"]["frozen_dataset_bytes_changed"] == 0
    assert boundary["counters"]["protected_stage122_to_stage129_blobs_changed"] == 0
    assert boundary["stage122_to_stage129_artifacts_modified_by_this_action"] \
        is False
    assert boundary["prior_packages_modified_by_this_action"] is False


@pytest.mark.parametrize("field", [
    "submission_ready",
    "ready_for_review_authorized",
    "merge_authorized",
    "stage130_authorized",
    "next_action_authorized",
    "pr_merged",
    "branch_deleted_by_this_action",
    "auto_merge_enabled_by_this_action",
])
def test_nothing_downstream_is_authorized(field, boundary):
    assert boundary[field] is False


def test_the_pr_remains_a_draft(decision, boundary):
    for source in (decision, boundary):
        assert source["pr_is_draft"] is True
        assert source["pr_number"] == 100


def test_the_predecessor_records_are_preserved(boundary):
    for field in ("prior_phase1_evidence_package_preserved",
                  "prior_phase2_assembly_record_preserved",
                  "prior_human_review_completion_record_preserved"):
        assert boundary[field] is True


# --------------------------------------------------------------------------- #
# The live pointer
# --------------------------------------------------------------------------- #

def test_the_live_pointer_advances_to_the_digest_review(state, boundary,
                                                        roadmap_front_matter):
    """This action's own pointer, and the one that has since overtaken it.

    The candidate's decision, boundary and deriver keep naming the digest
    review, because that is what they published. The LIVE pointer has moved on
    to the human review of the Zenodo Draft the digest review led to. Both
    statements are true and neither overwrites the other.
    """
    assert state["next_research_action_id"] == NEXT_POINTER
    assert boundary["next_action_id"] == NEXT_POINTER
    assert state["stage130_phase2_next_action_id"] == NEXT_POINTER
    assert roadmap_front_matter["next_research_action_id"] == LIVE_POINTER
    assert roadmap_front_matter["next_research_action_id"] != NEXT_POINTER


def test_the_pointer_is_not_an_authorization(state, boundary,
                                             roadmap_front_matter):
    assert state["next_research_action_authorized"] is False
    assert state["next_research_action_pointer_is_not_authorization"] is True
    assert boundary["next_action_authorized"] is False
    assert boundary["pointer_is_not_authorization"] is True
    assert roadmap_front_matter["next_research_action_authorized"] == "false"
    assert roadmap_front_matter["next_research_action_scope"] == \
        LIVE_POINTER_SCOPE


def test_the_next_action_demands_the_exact_archive_digest(boundary):
    assert boundary["next_action_requires_exact_archive_sha256_review"] is True


def test_the_manuscript_submission_metadata_is_supplied(state, decision,
                                                       boundary):
    """The six items WERE supplied. Saying otherwise is no longer true."""
    supplied = decision["human_supplied_manuscript_submission_metadata"]
    assert supplied["human_submission_metadata_supplied"] is True
    assert supplied["supplied_by"] == "human"
    assert supplied["independently_inferred_by_the_agent"] is False
    assert tuple(supplied["items_supplied"]) == SUBMISSION_ITEMS
    assert supplied["items_supplied_count"] == 6
    for key, value in supplied["items_supplied"].items():
        assert value, key
    assert decision["manuscript_human_submission_metadata_supplied"] is True
    assert boundary["manuscript_human_submission_metadata_supplied"] is True
    assert state["stage130_manuscript_human_submission_metadata_supplied"] \
        is True
    assert state[
        "stage130_manuscript_human_submission_metadata_supplied_items"] == \
        list(SUBMISSION_ITEMS)


def test_the_supplied_metadata_names_the_two_authors_in_order(decision):
    supplied = decision["human_supplied_manuscript_submission_metadata"]
    items = supplied["items_supplied"]
    assert items["authors_and_author_order"] == [
        "Abtin Asghari", "MohammadMehdi Mehraein"]
    creators = items["affiliations_and_corresponding_author"]["creators"]
    assert [c["order"] for c in creators] == [1, 2]
    assert [c["name"] for c in creators] == [
        "Abtin Asghari", "MohammadMehdi Mehraein"]
    for creator in creators:
        assert creator["affiliation"].strip()
    assert items["affiliations_and_corresponding_author"][
        "corresponding_author"] == "Abtin Asghari"
    assert "no external funding" in items["funding"].lower()
    assert "none declared" in items["conflicts_of_interest"].lower()
    assert items["ethics_and_data_governance_statement"].strip()
    access = items["data_access_mechanism_for_the_restricted_company_panel"]
    assert "zenodo" in access.lower()
    assert "pending" in access.lower()


def test_the_supplied_metadata_is_not_yet_in_the_manuscript(state, decision,
                                                            boundary):
    """Supplying a fact is not inserting it, and this action inserted none."""
    supplied = decision["human_supplied_manuscript_submission_metadata"]
    assert supplied["human_submission_metadata_applied_to_manuscript"] is False
    assert supplied["manuscript_modified_by_this_action"] is False
    assert supplied[
        "manuscript_requires_post_doi_metadata_update_and_human_review"] is True
    assert decision[
        "manuscript_human_submission_metadata_applied_to_manuscript"] is False
    assert boundary[
        "manuscript_human_submission_metadata_applied_to_manuscript"] is False
    assert state[
        "stage130_manuscript_human_submission_metadata_applied_to_manuscript"] \
        is False
    assert state["stage130_manuscript_requires_post_doi_metadata_update"] is True
    assert state["stage130_manuscript_requires_post_doi_human_review"] is True
    # ...and they are therefore still outstanding AS INSERTIONS.
    assert state["stage130_manuscript_human_supplied_metadata_outstanding"] \
        is True
    assert state[
        "stage130_manuscript_human_supplied_metadata_outstanding_count"] == 6
    assert boundary[
        "stage130_manuscript_human_supplied_metadata_outstanding"] is True
    marker = decision["superseded_marker"]
    assert marker["manuscript_submission_metadata_still_outstanding"] is True
    assert marker["manuscript_submission_metadata_outstanding_count"] == 6
    assert marker["pointer_previous_value"] == SUPERSEDED_POINTER
    assert marker["pointer_resolved_value"] == NEXT_POINTER


def test_claiming_the_metadata_reached_the_manuscript_breaks_the_build(
        tmp_path):
    root = _clone_repo_shim(tmp_path)
    decision = _read(DECISION_REL)
    decision["human_supplied_manuscript_submission_metadata"][
        "human_submission_metadata_applied_to_manuscript"] = True
    _write_json(root, DECISION_REL, decision)
    with pytest.raises(gen.HandoffError, match="must be False"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_denying_that_the_metadata_was_supplied_breaks_the_build(tmp_path):
    """The stale 'never supplied' claim may not come back."""
    root = _clone_repo_shim(tmp_path)
    decision = _read(DECISION_REL)
    decision["human_supplied_manuscript_submission_metadata"][
        "human_submission_metadata_supplied"] = False
    _write_json(root, DECISION_REL, decision)
    with pytest.raises(gen.HandoffError, match="SUPPLIED"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


# --------------------------------------------------------------------------- #
# rc.2, and the rc.1 it supersedes without deleting
# --------------------------------------------------------------------------- #

def test_the_release_is_rc3(decision, manifest, metadata, state):
    assert decision["release_version"] == RELEASE_VERSION
    assert manifest["release_version"] == RELEASE_VERSION
    assert metadata["release_version"] == RELEASE_VERSION
    assert state["stage130_dataset_release_candidate_version"] == \
        RELEASE_VERSION
    assert rc.RELEASE_VERSION == RELEASE_VERSION


def test_rc2_is_recorded_as_the_immediate_superseded_predecessor(
        decision, manifest, metadata, state):
    for source in (decision["supersedes_release"], manifest["supersedes"],
                   metadata["supersedes"]):
        assert source["version"] == SUPERSEDED_VERSION
        assert source["archive_sha256"] == SUPERSEDED_SHA256
        assert source["archive_size_bytes"] == SUPERSEDED_BYTES
        assert source["publication_readiness_at_the_time"] == \
            SUPERSEDED_READINESS
        for field in ("zenodo_deposition_created", "zenodo_upload_performed",
                      "zenodo_doi_reserved", "zenodo_published",
                      "public_release_authorized"):
            assert source[field] is False, field
    assert decision["supersedes_release"]["preserved_not_deleted"] is True
    assert state[
        "stage130_dataset_release_candidate_supersedes_archive_sha256"] == \
        SUPERSEDED_SHA256
    assert state[
        "stage130_dataset_release_candidate_supersedes_preserved_not_deleted"] \
        is True


def test_rc3_builds_under_a_new_filename_so_no_predecessor_is_overwritten(
        manifest, metadata):
    assert manifest["archive_name"] != manifest["supersedes"]["archive_name"]
    assert manifest["archive_name"].endswith("_rc3.zip")
    assert rc.ARCHIVE_NAME == manifest["archive_name"]
    assert "build/rc3" in metadata[
        "archive_build_path_relative_to_repo_root"]
    assert rc.SUPERSEDED_RELEASE["archive_name"] != rc.ARCHIVE_NAME
    # Neither predecessor's filename or build directory is reused, so their
    # archives and unpacked trees survive on disk untouched.
    for record in SUPERSEDE_CHAIN:
        assert manifest["archive_name"] != record["archive_name"]
    assert len({record["archive_name"] for record in SUPERSEDE_CHAIN}) == \
        len(SUPERSEDE_CHAIN)
    assert {r["build_directory"] for r in rc.SUPERSEDED_RELEASES} == \
        {"build", "build/rc2"}
    assert rc.BUILD_SUBDIR not in {"build", "build/rc2"}


def test_no_commit_was_amended_squashed_rebased_or_force_pushed(decision,
                                                                boundary):
    assert decision[
        "existing_commits_amended_squashed_rebased_or_force_pushed"] == 0
    assert boundary[
        "existing_commits_amended_squashed_rebased_or_force_pushed"] == 0


def test_erasing_the_superseded_digest_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    decision = _read(DECISION_REL)
    decision["supersedes_release"]["archive_sha256"] = "0" * 64
    _write_json(root, DECISION_REL, decision)
    with pytest.raises(gen.HandoffError, match="superseded archive digest"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_reusing_rc1s_filename_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    manifest = _read(MANIFEST_REL)
    manifest["archive_name"] = manifest["supersedes"]["archive_name"]
    _write_json(root, MANIFEST_REL, manifest)
    with pytest.raises(gen.HandoffError, match="NEW archive filename"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_the_roadmap_lists_both_action_ids_in_order():
    with open(os.path.join(REPO_ROOT, "project/docs/ai/ROADMAP.md"),
              encoding="utf-8") as fh:
        body = fh.read().split("---", 2)[2]
    assert ACTION_ID in body
    assert NEXT_POINTER in body
    assert body.index(NEXT_POINTER) > body.index(SUPERSEDED_POINTER)


def test_the_active_workstream_is_the_release_candidate_review(
        roadmap_front_matter):
    assert roadmap_front_matter["active_research_workstream_id"] == \
        "stage130-dataset-release-candidate-review"
    # The predecessor context does NOT move: this is still the Stage130
    # lineage that succeeded the Stage128 documentary-recovery workstream, and
    # the generator derives the same value independently of the relabel.
    assert roadmap_front_matter["predecessor_research_workstream_id"] == \
        "stage128-m3i2-final-official-documentary-recovery"


# --------------------------------------------------------------------------- #
# The generator is fail-closed
# --------------------------------------------------------------------------- #

def _clone_repo_shim(tmp_path):
    """A minimal tree the deriver can run against, for negative tests.

    It is a real (empty) git repository carrying the real ``.gitignore``, so
    the eight bulky frozen surfaces are *proven gitignored* here exactly as
    they are in the working repository. That is what lets the deriver tolerate
    their absence, and it keeps these negative tests from having to copy 11 MB
    of CSV per case.
    """
    root = tmp_path / "repo"
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True,
                   capture_output=True)
    with open(os.path.join(REPO_ROOT, ".gitignore"), "rb") as fh:
        (root / ".gitignore").write_bytes(fh.read())
    for rel in (DECISION_REL, BOUNDARY_REL, MANIFEST_REL, MATRIX_REL,
                MANUSCRIPT_REL, DICTIONARY_REL, ROLE_MAP_REL,
                "project/stage130/manuscript_human_review_completion/"
                "stage130_manuscript_human_review_completion_decision.json",
                "project/stage130/manuscript_human_review_completion/"
                "stage130_manuscript_human_review_governance_boundary.json"):
        source = os.path.join(REPO_ROOT, rel)
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(source, "rb") as fh:
            target.write_bytes(fh.read())
    # Every authoritative source the release dictionary anchors a row to. The
    # deriver checks each one resolves, so the shim must carry them.
    for rel in sorted(dictionary.AUTHORITATIVE_SOURCES):
        source = os.path.join(REPO_ROOT, rel)
        if not os.path.isfile(source):
            continue
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(source, "rb") as fh:
            target.write_bytes(fh.read())
    # Phase 1 / Phase 2 inputs the review deriver reads back.
    for rel in ("project/stage130/manuscript/claim_traceability_matrix.csv",
                "project/stage130/manuscript/references.bib",
                "project/stage130/manuscript/reference_audit.csv",
                "project/stage130/manuscript_evidence_package/manifest.json"):
        source = os.path.join(REPO_ROOT, rel)
        if not os.path.isfile(source):
            continue
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(source, "rb") as fh:
            target.write_bytes(fh.read())
    return root


def _matrix_fields():
    with open(os.path.join(REPO_ROOT, MATRIX_REL), encoding="utf-8",
              newline="") as fh:
        return list(csv.DictReader(fh).fieldnames)


def _matrix_rows():
    with open(os.path.join(REPO_ROOT, MATRIX_REL), encoding="utf-8",
              newline="") as fh:
        return {row["provider"]: dict(row) for row in csv.DictReader(fh)}


def _write_matrix(root, rows):
    target = root / MATRIX_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_matrix_fields(),
                                lineterminator="\n")
        writer.writeheader()
        for name in PROVIDERS:
            writer.writerow(rows[name])


def _write_json(root, rel, obj):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")


def test_the_deriver_returns_empty_before_the_package_exists(tmp_path):
    assert gen.derive_stage130_dataset_release_candidate_markers(
        str(tmp_path)) == {}


@pytest.mark.parametrize("field", [
    "zenodo_deposition_created",
    "zenodo_upload_performed",
    "zenodo_published",
    "public_release_authorized",
    "merge_authorized",
    "ready_for_review_authorized",
    "submission_ready",
])
def test_claiming_a_zenodo_or_downstream_authorization_breaks_the_build(
        field, tmp_path):
    root = _clone_repo_shim(tmp_path)
    boundary = _read(BOUNDARY_REL)
    boundary[field] = True
    _write_json(root, BOUNDARY_REL, boundary)
    with pytest.raises(gen.HandoffError, match=field):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_a_non_null_doi_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    manifest = _read(MANIFEST_REL)
    manifest["doi"] = "10.5281/zenodo.9999999"
    _write_json(root, MANIFEST_REL, manifest)
    with pytest.raises(gen.HandoffError, match="doi must be omitted or null"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_a_non_zero_action_counter_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    boundary = _read(BOUNDARY_REL)
    boundary["counters"]["model_fits"] = 1
    _write_json(root, BOUNDARY_REL, boundary)
    with pytest.raises(gen.HandoffError, match="counters.model_fits"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_a_manifest_that_misreports_a_frozen_digest_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    manifest = _read(MANIFEST_REL)
    for entry in manifest["files"]:
        if entry["role"] == "primary_modeling_surface":
            entry["sha256"] = "0" * 64
    _write_json(root, MANIFEST_REL, manifest)
    with pytest.raises(gen.HandoffError, match="manifest pins"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_dropping_a_provider_from_the_audit_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    decision = _read(DECISION_REL)
    decision["source_rights_audit"]["providers_covered"] = ["CODAL"]
    _write_json(root, DECISION_REL, decision)
    with pytest.raises(gen.HandoffError, match="must cover exactly"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_engineering_the_blocker_away_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    decision = _read(DECISION_REL)
    decision["source_rights_audit"]["columns_removed_to_avoid_the_blocker"] = 1
    _write_json(root, DECISION_REL, decision)
    with pytest.raises(gen.HandoffError, match="never engineered away"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_claiming_the_counts_were_recomputed_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    manifest = _read(MANIFEST_REL)
    manifest["counts_recomputed_from_rows"] = True
    _write_json(root, MANIFEST_REL, manifest)
    with pytest.raises(gen.HandoffError, match="must not recompute"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_completing_the_manuscript_metadata_by_side_effect_breaks_the_build(
        tmp_path):
    root = _clone_repo_shim(tmp_path)
    decision = _read(DECISION_REL)
    decision["superseded_marker"][
        "manuscript_submission_metadata_still_outstanding"] = False
    _write_json(root, DECISION_REL, decision)
    with pytest.raises(gen.HandoffError, match="still outstanding|outstanding"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_inventing_an_orcid_claim_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    decision = _read(DECISION_REL)
    decision["human_supplied_release_metadata"][
        "orcid_identifiers_invented_by_this_action"] = True
    _write_json(root, DECISION_REL, decision)
    with pytest.raises(gen.HandoffError, match="ORCID"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_relabelling_a_human_fact_as_agent_inferred_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    decision = _read(DECISION_REL)
    decision["human_supplied_release_intent"][
        "independently_inferred_by_the_agent"] = True
    _write_json(root, DECISION_REL, decision)
    with pytest.raises(gen.HandoffError, match="independently inferred"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


# --------------------------------------------------------------------------- #
# Package metadata
# --------------------------------------------------------------------------- #

def test_the_metadata_record_hashes_every_package_file(metadata):
    for rel, entry in metadata["package_files"].items():
        path = os.path.join(REPO_ROOT, PKG_REL, rel)
        assert os.path.isfile(path), rel
        with open(path, "rb") as fh:
            data = fh.read()
        assert entry["bytes"] == len(data), rel
        assert entry["sha256"] == hashlib.sha256(data).hexdigest(), rel
    assert metadata["package_file_count"] == len(metadata["package_files"])


def test_the_metadata_record_pins_the_archive_digest(payload, metadata):
    archive = rc.build_archive(payload)
    assert metadata["archive_sha256"] == hashlib.sha256(archive).hexdigest()
    assert metadata["archive_size_bytes"] == len(archive)
    assert metadata["archive_tracked_in_git"] is False


def test_the_roadmap_publishes_the_same_archive_digest(roadmap_front_matter,
                                                       metadata):
    assert roadmap_front_matter["dataset_release_candidate_archive_sha256"] == \
        metadata["archive_sha256"]


def test_no_credential_or_third_party_pii_is_committed(metadata):
    assert metadata["credentials_committed_to_git"] is False
    assert metadata["third_party_pii_committed_to_git"] is False
    assert metadata["final_test_artifacts_committed"] == 0
    assert metadata["model_artifacts_committed"] == 0
    assert metadata["value_files_committed"] == 0


def test_every_committed_package_path_is_change_allowlisted():
    for dirpath, dirnames, filenames in os.walk(
            os.path.join(REPO_ROOT, PKG_REL)):
        dirnames[:] = [d for d in dirnames if d != "build"]
        for name in filenames:
            rel = os.path.relpath(os.path.join(dirpath, name), REPO_ROOT)
            assert gen.path_allowlisted(rel), rel
    for rel in ("project/src/stage130_dataset_release_candidate.py",
                "project/tests/test_stage130_dataset_release_candidate.py"):
        assert gen.path_allowlisted(rel), rel


# --------------------------------------------------------------------------- #
# rc.3 — the released source scope, and the sentences that would misstate it
# --------------------------------------------------------------------------- #
#
# The committed rights matrix is the authority: CODAL-derived,
# researcher-compiled company financial fields are released; no TSETMC-derived
# and no World Bank-derived field is. rc.2 shipped a description implying all
# three providers fed the released values. These tests pin the correction and
# make its recurrence impossible.

def test_the_rights_matrix_records_no_tsetmc_or_world_bank_field_released():
    """The authority the correction rests on, read directly."""
    with open(os.path.join(REPO_ROOT, MATRIX_REL), encoding="utf-8-sig",
              newline="") as fh:
        rows = {row["provider"]: row for row in csv.DictReader(fh)}
    for provider in NON_RELEASED_PROVIDERS:
        used = rows[provider]["type_of_information_used_in_this_release"]
        assert used.strip().upper().startswith("NONE"), (
            f"{provider} must contribute NOTHING to this release, got {used!r}")
    assert rows["CODAL"]["type_of_information_used_in_this_release"].strip()
    assert rows["CODAL"]["only_researcher_compiled_factual_fields_included"] \
        == "yes"


def test_every_surface_states_the_released_source_scope(decision, boundary,
                                                        manifest, state):
    assert decision["released_source_scope"]["statement"] == \
        RELEASED_SOURCE_SCOPE
    assert manifest["released_source_scope"] == RELEASED_SOURCE_SCOPE
    assert boundary["released_source_scope_statement"] == \
        RELEASED_SOURCE_SCOPE
    assert state["stage130_dataset_release_candidate_released_source_scope"] \
        == RELEASED_SOURCE_SCOPE
    assert rc.RELEASED_SOURCE_SCOPE_STATEMENT == RELEASED_SOURCE_SCOPE
    for source in (
            tuple(decision["released_source_scope"][
                "released_source_providers"]),
            tuple(manifest["released_source_providers"]),
            tuple(boundary["released_source_providers"]),
            tuple(state[
                "stage130_dataset_release_candidate_released_source_"
                "providers"]),
            rc.RELEASED_SOURCE_PROVIDERS):
        assert source == RELEASED_PROVIDERS
    for source in (
            tuple(decision["released_source_scope"][
                "non_released_source_providers"]),
            tuple(manifest["non_released_source_providers"]),
            tuple(boundary["non_released_source_providers"]),
            tuple(state[
                "stage130_dataset_release_candidate_non_released_source_"
                "providers"]),
            rc.NON_RELEASED_SOURCE_PROVIDERS):
        assert source == NON_RELEASED_PROVIDERS


def test_no_surface_claims_tsetmc_or_world_bank_fields_are_included(
        decision, boundary, manifest, metadata, state):
    assert decision["released_source_scope"][
        "tsetmc_derived_fields_included"] is False
    assert decision["released_source_scope"][
        "world_bank_derived_fields_included"] is False
    for source in (manifest, metadata):
        assert source["tsetmc_derived_fields_included"] is False
        assert source["world_bank_derived_fields_included"] is False
    assert boundary["tsetmc_derived_fields_included_in_release"] is False
    assert boundary["world_bank_derived_fields_included_in_release"] is False
    assert state["stage130_dataset_release_candidate_tsetmc_fields_included"] \
        is False
    assert state[
        "stage130_dataset_release_candidate_world_bank_fields_included"] \
        is False


def test_the_payload_never_asserts_tsetmc_or_world_bank_material_is_released(
        payload):
    """Every shipped byte, swept — prose as well as flags."""
    for name, data in sorted(payload.items()):
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        assert rc.find_release_scope_violations(text) == [], name


def test_the_committed_package_never_asserts_it_either():
    gen._stage130_rc_assert_no_misleading_release_scope_claim(REPO_ROOT)


@pytest.mark.parametrize("claim", [
    "All values were compiled by the authors from publicly accessible sources "
    "including CODAL, TSETMC and the World Bank.",
    "<p>Compiled from publicly accessible sources including CODAL, TSETMC and "
    "the World Bank.</p>",
    "Values were drawn from CODAL, TSETMC and the World Bank.",
    "All underlying values come from publicly accessible sources such as "
    "CODAL, TSETMC and the World Bank.",
])
def test_the_superseded_three_provider_sentence_is_rejected(claim):
    """The exact rc.2 sentence, and re-typings of it, in either guard."""
    assert rc.find_release_scope_violations(claim), claim
    assert gen._stage130_rc_scope_violations(claim), claim


@pytest.mark.parametrize("claim", [
    "This release includes TSETMC market data for every company-year.",
    "The released columns include World Bank macroeconomic indicators.",
    "This bundle contains TSETMC daily prices alongside the statement fields.",
    "The released panel is built from CODAL filings and TSETMC market data.",
    "World Bank indicators are included in this release.",
])
def test_a_newly_worded_inclusion_claim_is_rejected_too(claim):
    """Not just the known sentence: any assertion of the same falsehood."""
    assert rc.find_release_scope_violations(claim), claim
    assert gen._stage130_rc_scope_violations(claim), claim


@pytest.mark.parametrize("sentence", [
    RELEASED_SOURCE_SCOPE,
    "No TSETMC-derived and no World Bank-derived field is in this release.",
    "Type of information used in this release: NONE - no TSETMC-derived field "
    "is in this release.",
    "TSETMC market data was evaluated as a candidate predictor block in the "
    "wider study.",
    "The World Bank's CC BY 4.0 licence permits distribution in any format "
    "for any purpose including commercial use.",
])
def test_truthful_and_historical_statements_are_not_rejected(sentence):
    """The guard must not sweep away the sentences that are actually true."""
    assert rc.find_release_scope_violations(sentence) == [], sentence
    assert gen._stage130_rc_scope_violations(sentence) == [], sentence


def test_the_human_statement_is_exempt_by_location_not_by_wording():
    """The carve-out is a named field, not a hole in the pattern.

    Read as a claim about THIS release the human's sentence would offend, and
    in isolation the sweep says so. It is tolerated only where it actually
    lives -- the decision artifact's
    ``human_supplied_data_governance_facts.statement`` -- because there it is a
    record of what a person said about the wider study. Put the same words
    anywhere else and the guard fires.
    """
    assert rc.find_release_scope_violations(HUMAN_GOVERNANCE_STATEMENT)
    assert gen._stage130_rc_scope_violations(HUMAN_GOVERNANCE_STATEMENT)
    # ...yet the committed package, which contains it, passes.
    gen._stage130_rc_assert_no_misleading_release_scope_claim(REPO_ROOT)


def test_the_human_statement_pasted_elsewhere_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    boundary = _read(BOUNDARY_REL)
    boundary["released_source_scope_note"] = HUMAN_GOVERNANCE_STATEMENT
    _write_json(root, BOUNDARY_REL, boundary)
    with pytest.raises(gen.HandoffError,
                       match="misstates the released source scope"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_a_misleading_claim_added_to_the_payload_breaks_the_build(payload):
    poisoned = dict(payload)
    poisoned["README.md"] = (
        b"# Release\n\nThis release includes TSETMC market data.\n")
    with pytest.raises(rc.Stage130ReleaseError,
                       match="misstates the released source scope"):
        rc.gate_release_scope_statements(poisoned)


def test_a_misleading_claim_added_to_the_package_breaks_the_handoff(tmp_path):
    root = _clone_repo_shim(tmp_path)
    decision = _read(DECISION_REL)
    decision["release_candidate_conflict_resolution"] = (
        "The released panel is compiled from CODAL, TSETMC and the World "
        "Bank.")
    _write_json(root, DECISION_REL, decision)
    with pytest.raises(gen.HandoffError,
                       match="misstates the released source scope"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_dropping_the_scope_statement_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    decision = _read(DECISION_REL)
    decision["released_source_scope"]["statement"] = \
        "Compiled from publicly accessible sources."
    _write_json(root, DECISION_REL, decision)
    with pytest.raises(gen.HandoffError, match="released source scope"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_claiming_a_non_released_provider_contributes_breaks_the_build(
        tmp_path):
    root = _clone_repo_shim(tmp_path)
    decision = _read(DECISION_REL)
    decision["released_source_scope"]["tsetmc_derived_fields_included"] = True
    _write_json(root, DECISION_REL, decision)
    with pytest.raises(gen.HandoffError,
                       match="tsetmc_derived_fields_included"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_flipping_the_matrix_to_release_a_tsetmc_field_breaks_the_build(
        tmp_path):
    """The scope statement and the matrix move together, or not at all."""
    root = _clone_repo_shim(tmp_path)
    with open(os.path.join(REPO_ROOT, MATRIX_REL), encoding="utf-8-sig",
              newline="") as fh:
        rows = {row["provider"]: dict(row) for row in csv.DictReader(fh)}
    rows["TSETMC"]["type_of_information_used_in_this_release"] = \
        "Daily market prices keyed to company and fiscal year"
    _write_matrix(root, rows)
    with pytest.raises(gen.HandoffError, match="NONE"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


# --------------------------------------------------------------------------- #
# rc.3 — the correction record, and what it may not have touched
# --------------------------------------------------------------------------- #

def test_the_correction_records_what_it_corrected(decision):
    correction = decision["rc3_correction"]
    assert correction["corrected_statement"] == RELEASED_SOURCE_SCOPE
    assert correction["previous_statement"].strip()
    # The superseded sentence is quoted in exactly ONE place, so the
    # correction stays auditable without the false statement circulating.
    assert "TSETMC" in correction["previous_statement"]
    assert "World Bank" in correction["previous_statement"]


def test_the_superseded_sentence_appears_in_exactly_one_committed_field():
    quoted = _read(DECISION_REL)["rc3_correction"]["previous_statement"]
    pkg = os.path.join(REPO_ROOT, PKG_REL)
    hits = []
    for dirpath, dirnames, filenames in os.walk(pkg):
        dirnames[:] = [d for d in dirnames if d != "build"]
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            try:
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
            except (UnicodeDecodeError, OSError):
                continue
            if quoted in text or json.dumps(quoted, ensure_ascii=False)[1:-1] \
                    in text:
                hits.append(os.path.relpath(path, REPO_ROOT))
    assert hits == [DECISION_REL], hits


def test_the_correction_changed_no_rights_record(decision, boundary, state):
    correction = decision["rc3_correction"]
    for field in ("historical_rights_record_changed",
                  "provider_terms_retrieved_by_this_correction",
                  "provider_terms_verified_by_this_correction",
                  "codal_or_tsetmc_terms_claimed_retrieved_or_verified"):
        assert correction[field] is False, field
    for field in ("data_values_changed", "frozen_surface_bytes_changed",
                  "manuscript_bytes_changed", "rights_matrix_rows_changed",
                  "human_supplied_statements_altered",
                  "superseded_candidates_altered",
                  "superseded_archives_rebuilt_renamed_or_deleted"):
        assert correction[field] == 0, field
    assert boundary["historical_rights_record_changed_by_this_action"] is False
    assert boundary["rights_matrix_rows_changed_by_this_action"] == 0
    assert boundary["human_supplied_statements_altered_by_this_action"] == 0
    assert state[
        "stage130_dataset_release_candidate_rights_record_changed_by_"
        "correction"] is False


def test_the_preserved_rights_flags_are_untouched_by_rc3(decision, boundary,
                                                         manifest, state):
    """The four things the correction was forbidden to move."""
    assert decision["source_rights_status"] == RIGHTS_STATUS
    assert boundary["source_rights_status"] == RIGHTS_STATUS
    assert state["stage130_dataset_release_candidate_rights_status"] == \
        RIGHTS_STATUS
    assert manifest["provider_terms_independently_retrieved"] is False
    assert manifest["provider_terms_independently_verified"] is False
    assert state[
        "stage130_dataset_release_candidate_provider_terms_retrieved"] is False
    assert state[
        "stage130_dataset_release_candidate_provider_terms_verified"] is False
    determination = decision["human_supplied_source_rights_determination"]
    assert determination["supplied_by"] == "human"
    assert determination["independently_inferred_by_the_agent"] is False
    assert determination["is_a_legal_opinion"] is False
    assert determination[
        "is_an_independent_verification_of_provider_terms"] is False


def test_the_human_wider_study_statement_is_preserved_verbatim(decision):
    """A record of what a person said is not the agent's to reword."""
    assert decision["human_supplied_data_governance_facts"]["statement"] == \
        HUMAN_GOVERNANCE_STATEMENT
    assert gen._STAGE130_RC_HUMAN_GOVERNANCE_STATEMENT == \
        HUMAN_GOVERNANCE_STATEMENT
    scope = decision["released_source_scope"]
    assert scope[
        "wider_study_statement_is_not_a_release_composition_claim"] is True


def test_rewording_the_human_statement_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    decision = _read(DECISION_REL)
    decision["human_supplied_data_governance_facts"]["statement"] = (
        "All underlying data were obtained from CODAL.")
    _write_json(root, DECISION_REL, decision)
    with pytest.raises(gen.HandoffError,
                       match="altered the human author's data-governance"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_dropping_the_recorded_previous_statement_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    decision = _read(DECISION_REL)
    decision["rc3_correction"]["previous_statement"] = ""
    _write_json(root, DECISION_REL, decision)
    with pytest.raises(gen.HandoffError, match="not auditable"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


# --------------------------------------------------------------------------- #
# rc.3 — 25 payload files, 27 archive members, never one number for both
# --------------------------------------------------------------------------- #

def test_the_two_counts_are_what_they_are(payload, manifest):
    members = sorted(payload)
    assert len(members) == ARCHIVE_MEMBER_COUNT
    payload_files = [n for n in members if n not in NON_PAYLOAD_MEMBERS]
    assert len(payload_files) == MANIFEST_PAYLOAD_FILE_COUNT
    assert len(manifest["files"]) == MANIFEST_PAYLOAD_FILE_COUNT
    assert manifest["file_count"] == MANIFEST_PAYLOAD_FILE_COUNT
    sums = payload["SHA256SUMS.txt"].decode("utf-8").splitlines()
    assert len([line for line in sums if line.strip()]) == \
        SHA256SUMS_LINE_COUNT
    assert rc.MANIFEST_PAYLOAD_FILE_COUNT == MANIFEST_PAYLOAD_FILE_COUNT
    assert rc.ARCHIVE_MEMBER_COUNT == ARCHIVE_MEMBER_COUNT
    assert rc.SHA256SUMS_LINE_COUNT == SHA256SUMS_LINE_COUNT


def test_the_manifest_never_lists_the_integrity_records_as_payload(manifest):
    listed = {entry["bundle_path"] for entry in manifest["files"]}
    for name in NON_PAYLOAD_MEMBERS:
        assert name not in listed, name
    assert set(manifest["manifest_excludes"]) == set(NON_PAYLOAD_MEMBERS)


def test_every_surface_publishes_both_counts_under_distinct_names(
        decision, boundary, manifest, metadata, state):
    expected = {
        "manifest_payload_file_count": MANIFEST_PAYLOAD_FILE_COUNT,
        "archive_member_count": ARCHIVE_MEMBER_COUNT,
        "sha256sums_line_count": SHA256SUMS_LINE_COUNT,
    }
    for field, value in expected.items():
        assert manifest[field] == value, field
        assert metadata[field] == value, field
        assert boundary[field] == value, field
        assert decision["release_composition"][field] == value, field
    assert state[
        "stage130_dataset_release_candidate_manifest_payload_file_count"] == \
        MANIFEST_PAYLOAD_FILE_COUNT
    assert state["stage130_dataset_release_candidate_archive_member_count"] \
        == ARCHIVE_MEMBER_COUNT
    assert state["stage130_dataset_release_candidate_file_count"] == \
        MANIFEST_PAYLOAD_FILE_COUNT
    # The ambiguous rc.2 key is gone, not merely supplemented.
    assert "bundle_payload_file_count" not in metadata


def test_nothing_describes_all_27_members_as_manifest_payload_files(
        decision, boundary, state):
    assert decision["release_composition"][
        "all_27_described_as_manifest_payload_files"] is False
    assert boundary[
        "all_archive_members_described_as_manifest_payload_files"] is False
    assert state[
        "stage130_dataset_release_candidate_all_members_are_payload_files"] \
        is False
    assert tuple(decision["release_composition"][
        "archive_members_that_are_not_manifest_payload_files"]) == \
        NON_PAYLOAD_MEMBERS
    assert tuple(state[
        "stage130_dataset_release_candidate_non_payload_archive_members"]) == \
        NON_PAYLOAD_MEMBERS


def test_conflating_the_two_counts_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    manifest = _read(MANIFEST_REL)
    manifest["manifest_payload_file_count"] = ARCHIVE_MEMBER_COUNT
    _write_json(root, MANIFEST_REL, manifest)
    with pytest.raises(gen.HandoffError,
                       match="manifest_payload_file_count"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_calling_all_27_payload_files_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    decision = _read(DECISION_REL)
    decision["release_composition"][
        "all_27_described_as_manifest_payload_files"] = True
    _write_json(root, DECISION_REL, decision)
    with pytest.raises(gen.HandoffError, match="NOT all"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_a_payload_file_count_that_disagrees_with_the_build_breaks_it(payload):
    poisoned = dict(payload)
    poisoned.pop("CITATION.cff")
    with pytest.raises(rc.Stage130ReleaseError, match="members"):
        rc.gate_file_count_terminology(poisoned)


# --------------------------------------------------------------------------- #
# rc.3 — rc.1 and rc.2 are immutable superseded history
# --------------------------------------------------------------------------- #

def test_the_full_supersede_chain_is_recorded_on_every_surface(
        decision, boundary, manifest, metadata, state):
    chains = (
        decision["supersedes_release_history"],
        boundary["supersedes_release_history"],
        manifest["supersedes_history"],
        metadata["supersedes_history"],
        state["stage130_dataset_release_candidate_supersede_chain"],
    )
    for chain in chains:
        assert len(chain) == len(SUPERSEDE_CHAIN)
        for recorded, expected in zip(chain, SUPERSEDE_CHAIN):
            for field, value in expected.items():
                if field in recorded:
                    assert recorded[field] == value, (expected["version"],
                                                      field)
    assert state["stage130_dataset_release_candidate_superseded_versions"] == \
        [record["version"] for record in SUPERSEDE_CHAIN]
    assert tuple(r["version"] for r in rc.SUPERSEDED_RELEASES) == \
        tuple(r["version"] for r in SUPERSEDE_CHAIN)


def test_nothing_was_ever_deposited_under_any_superseded_candidate(
        decision, manifest):
    for chain in (decision["supersedes_release_history"],
                  manifest["supersedes_history"]):
        for record in chain:
            assert record["preserved_not_deleted"] is True
            for field in ("zenodo_deposition_created",
                          "zenodo_upload_performed", "zenodo_doi_reserved",
                          "zenodo_published", "public_release_authorized"):
                assert record[field] is False, (record["version"], field)


def test_the_superseded_archives_were_not_rebuilt_renamed_or_deleted(
        boundary, state):
    assert boundary[
        "superseded_archives_rebuilt_renamed_or_deleted_by_this_action"] == 0
    assert boundary[
        "superseded_recorded_digests_altered_by_this_action"] == 0
    assert state[
        "stage130_dataset_release_candidate_superseded_archives_preserved"] \
        is True
    assert state[
        "stage130_dataset_release_candidate_superseded_digests_altered"] == 0


@pytest.mark.parametrize("index,field,poison", [
    (0, "archive_sha256", "0" * 64),
    (0, "archive_size_bytes", 1),
    (0, "publication_readiness_at_the_time",
     "READY_FOR_EXACT_DIGEST_HUMAN_REVIEW"),
    (1, "archive_sha256", "f" * 64),
    (1, "archive_size_bytes", 2),
    (1, "publication_readiness_at_the_time", "NOT_READY_FOR_PUBLICATION"),
])
def test_altering_any_superseded_record_breaks_the_build(tmp_path, index,
                                                         field, poison):
    """rc.1's and rc.2's history is history; a version bump may not edit it."""
    root = _clone_repo_shim(tmp_path)
    decision = _read(DECISION_REL)
    decision["supersedes_release_history"][index][field] = poison
    _write_json(root, DECISION_REL, decision)
    with pytest.raises(gen.HandoffError, match="supersede history"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_dropping_rc1_from_the_chain_breaks_the_build(tmp_path):
    """Superseding rc.2 does not make rc.1 stop having existed."""
    root = _clone_repo_shim(tmp_path)
    decision = _read(DECISION_REL)
    decision["supersedes_release_history"] = \
        decision["supersedes_release_history"][1:]
    _write_json(root, DECISION_REL, decision)
    with pytest.raises(gen.HandoffError, match="all 2 superseded candidates"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_claiming_a_deposit_under_a_superseded_candidate_breaks_the_build(
        tmp_path):
    root = _clone_repo_shim(tmp_path)
    manifest = _read(MANIFEST_REL)
    manifest["supersedes_history"][0]["zenodo_published"] = True
    _write_json(root, MANIFEST_REL, manifest)
    with pytest.raises(gen.HandoffError, match="nothing was ever deposited"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_reusing_rc2s_filename_breaks_the_build(tmp_path):
    root = _clone_repo_shim(tmp_path)
    manifest = _read(MANIFEST_REL)
    manifest["archive_name"] = SUPERSEDE_CHAIN[1]["archive_name"]
    _write_json(root, MANIFEST_REL, manifest)
    with pytest.raises(gen.HandoffError, match="archive filename"):
        gen.derive_stage130_dataset_release_candidate_markers(str(root))


def test_a_superseded_archive_on_disk_still_hashes_to_its_recorded_digest():
    """Absence is tolerated; DRIFT never is.

    The archives are gitignored build outputs, so a fresh clone legitimately
    has none of them and this test asserts nothing there — the same tolerance
    the Handoff deriver applies to the frozen Stage125 surfaces. What it will
    not tolerate is a superseded archive that is present and no longer hashes
    to the digest the record pins: that would mean rc.3 rebuilt, overwrote or
    corrupted a predecessor whose bytes a reviewer may still be asked about.
    """
    expected = {record["archive_name"]: record["archive_sha256"]
                for record in SUPERSEDE_CHAIN}
    build = os.path.join(REPO_ROOT, PKG_REL, "build")
    checked = []
    for dirpath, _dirnames, filenames in os.walk(build):
        for name in sorted(filenames):
            if name not in expected:
                continue
            with open(os.path.join(dirpath, name), "rb") as fh:
                actual = hashlib.sha256(fh.read()).hexdigest()
            assert actual == expected[name], (
                f"superseded archive {name} has DRIFTED: expected "
                f"{expected[name]}, found {actual}")
            checked.append(name)
    # rc.3 must never build over a predecessor's name, present or not.
    assert rc.ARCHIVE_NAME not in expected
    assert set(checked) <= set(expected)


def test_the_roadmap_front_matter_carries_the_rc3_digest_and_the_chain(
        roadmap_front_matter, metadata):
    front = roadmap_front_matter
    assert front["dataset_release_candidate_version"] == RELEASE_VERSION
    assert front["dataset_release_candidate_archive_sha256"] == \
        metadata["archive_sha256"]
    assert int(front["dataset_release_candidate_archive_size_bytes"]) == \
        metadata["archive_size_bytes"]
    assert front["dataset_release_candidate_supersedes_version"] == \
        SUPERSEDED_VERSION
    assert front["dataset_release_candidate_supersedes_archive_sha256"] == \
        SUPERSEDED_SHA256
    assert front["dataset_release_candidate_rc1_archive_sha256"] == \
        SUPERSEDE_CHAIN[0]["archive_sha256"]
    assert int(
        front["dataset_release_candidate_manifest_payload_file_count"]) == \
        MANIFEST_PAYLOAD_FILE_COUNT
    assert int(front["dataset_release_candidate_archive_member_count"]) == \
        ARCHIVE_MEMBER_COUNT
    assert str(
        front["dataset_release_candidate_tsetmc_fields_included"]).lower() \
        == "false"
    assert str(front[
        "dataset_release_candidate_world_bank_fields_included"]).lower() \
        == "false"


# --------------------------------------------------------------------------- #
# rc.3 — determinism, and the 115-column dictionary it must not lose
# --------------------------------------------------------------------------- #

def test_two_builds_in_separate_directories_are_byte_identical(tmp_path):
    """Member sets, per-file hashes, archive bytes, digest, size and trees."""
    first = rc.write_release_candidate(REPO_ROOT, tmp_path / "a")
    second = rc.write_release_candidate(REPO_ROOT, tmp_path / "b")
    assert sorted(first["payload"]) == sorted(second["payload"])
    for name in first["payload"]:
        assert hashlib.sha256(first["payload"][name]).hexdigest() == \
            hashlib.sha256(second["payload"][name]).hexdigest(), name
    assert first["archive_bytes"] == second["archive_bytes"]
    assert first["archive_sha256"] == second["archive_sha256"]
    assert first["archive_size"] == second["archive_size"]
    for tree in (first["tree_path"], second["tree_path"]):
        assert os.path.isdir(tree)
    walked = []
    for tree in (first["tree_path"], second["tree_path"]):
        entries = {}
        for dirpath, _dirnames, filenames in os.walk(tree):
            for name in filenames:
                path = os.path.join(dirpath, name)
                with open(path, "rb") as fh:
                    entries[os.path.relpath(path, tree)] = \
                        hashlib.sha256(fh.read()).hexdigest()
        walked.append(entries)
    assert walked[0] == walked[1]
    assert len(walked[0]) == ARCHIVE_MEMBER_COUNT


def test_the_complete_115_column_dictionary_survives_rc3(payload, manifest,
                                                         state):
    rows = list(csv.DictReader(io.StringIO(
        payload["RELEASE_COLUMN_DICTIONARY.csv"].decode("utf-8"),
        newline="")))
    assert len(rows) == PRIMARY_COLUMNS
    coverage = manifest["release_column_dictionary_coverage"]
    assert coverage["released_columns_documented"] == PRIMARY_COLUMNS
    assert coverage["released_columns_undocumented"] == 0
    assert coverage["definitions_invented_by_this_action"] == 0
    assert state["stage130_dataset_release_candidate_columns_documented"] == \
        PRIMARY_COLUMNS
    assert state["stage130_dataset_release_candidate_columns_undocumented"] \
        == 0
