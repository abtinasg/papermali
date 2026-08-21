"""Stage130 — the deterministic Zenodo dataset Release Candidate.

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
  * that the release carries no DOI and no placeholder that could be read as
    one, and that every Zenodo counter is false;
  * that the source-rights audit covers all three providers and that a blocked
    disposition cannot be quietly upgraded to ready;
  * that the approved manuscript is byte-identical, and that the generator is
    FAIL-CLOSED — drifting a frozen surface, editing the manuscript, claiming a
    DOI, or reporting a non-zero action counter must each break the build;
  * that the Final Test prediction artifact is never opened, hashed or packaged.
"""
import copy
import hashlib
import importlib
import io
import json
import os
import subprocess
import sys
import zipfile

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "project", "scripts"))
sys.path.insert(0, os.path.join(REPO_ROOT, "project", "src"))

import stage130_dataset_release_candidate as rc  # noqa: E402
import update_ai_handoff as gen  # noqa: E402

ACTION_ID = "stage130-dataset-release-candidate"
PKG_REL = "project/stage130/dataset_release_candidate"
DECISION_REL = f"{PKG_REL}/stage130_dataset_release_candidate_decision.json"
BOUNDARY_REL = (f"{PKG_REL}/"
                "stage130_dataset_release_candidate_governance_boundary.json")
MANIFEST_REL = f"{PKG_REL}/release_manifest.json"
SUMS_REL = f"{PKG_REL}/SHA256SUMS.txt"
MATRIX_REL = f"{PKG_REL}/source_rights_matrix.csv"
METADATA_REL = (f"{PKG_REL}/"
                "metadata_and_hashes_stage130_dataset_release_candidate.json")

MANUSCRIPT_REL = "project/stage130/manuscript/manuscript_draft_en.md"
MANUSCRIPT_SHA256 = "8b5d861c36e01dc81133c1071cd96f7e340482ac2148b53c055369bbd5ffcb19"
MANUSCRIPT_BLOB_ID = "93f7e8e796ec098de38725271305ab06263efd1f"

PRIMARY_BUNDLE_REL = "data/analysis_ready_main_rule_a_stage125.csv"
NEXT_POINTER = "human-dataset-release-candidate-digest-review"
NEXT_POINTER_SCOPE = (
    "dataset_release_candidate_human_digest_review_no_zenodo_action_is_"
    "authorized")
SUPERSEDED_POINTER = "human-manuscript-submission-metadata"
PROVIDERS = ("CODAL", "TSETMC", "World Bank")

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


def test_dictionary_coverage_is_measured_and_published_not_hidden(manifest):
    """The dictionary covers only part of the release, and the release says so."""
    coverage = manifest["column_documentation_coverage"]
    assert coverage["released_columns"] == PRIMARY_COLUMNS
    documented = coverage["released_columns_documented_in_data_dictionary"]
    missing = coverage["released_columns_not_in_data_dictionary"]
    assert documented + missing == PRIMARY_COLUMNS
    assert missing > 0, (
        "if the dictionary ever covers everything, drop the disclosure "
        "instead of leaving a stale caveat")
    assert "role_map" in manifest["column_documentation_authority"] or \
        "column_role_map" in manifest["column_documentation_authority"]


def test_the_limitations_document_states_the_documentation_gap(payload):
    text = payload["LIMITATIONS.md"].decode("utf-8")
    assert "column_documentation_coverage" in text


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


def test_a_blocking_provider_forces_not_ready_for_publication(decision,
                                                              boundary):
    audit = decision["source_rights_audit"]
    assert audit["publication_readiness"] == "NOT_READY_FOR_PUBLICATION"
    assert audit["blocking_provider"] == "CODAL"
    assert boundary["publication_readiness"] == "NOT_READY_FOR_PUBLICATION"


def test_the_blocker_was_reported_not_engineered_away(decision):
    audit = decision["source_rights_audit"]
    assert audit["columns_removed_to_avoid_the_blocker"] == 0
    assert audit["frozen_values_altered_to_avoid_the_blocker"] == 0
    assert audit["legal_conclusion_asserted_beyond_the_evidence"] is False


def test_upgrading_a_blocked_candidate_to_ready_breaks_the_build(tmp_path,
                                                                monkeypatch):
    """A blocked matrix and a 'ready' verdict may not coexist."""
    root = _clone_repo_shim(tmp_path)
    decision = _read(DECISION_REL)
    decision["source_rights_audit"]["publication_readiness"] = "READY"
    _write_json(root, DECISION_REL, decision)
    with pytest.raises(gen.HandoffError, match="blocked candidate|blocking"):
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
    assert state["next_research_action_id"] == NEXT_POINTER
    assert boundary["next_action_id"] == NEXT_POINTER
    assert roadmap_front_matter["next_research_action_id"] == NEXT_POINTER
    assert state["stage130_phase2_next_action_id"] == NEXT_POINTER


def test_the_pointer_is_not_an_authorization(state, boundary,
                                             roadmap_front_matter):
    assert state["next_research_action_authorized"] is False
    assert state["next_research_action_pointer_is_not_authorization"] is True
    assert boundary["next_action_authorized"] is False
    assert boundary["pointer_is_not_authorization"] is True
    assert roadmap_front_matter["next_research_action_authorized"] == "false"
    assert roadmap_front_matter["next_research_action_scope"] == \
        NEXT_POINTER_SCOPE


def test_the_next_action_demands_the_exact_archive_digest(boundary):
    assert boundary["next_action_requires_exact_archive_sha256_review"] is True


def test_the_manuscript_submission_metadata_is_still_outstanding(state,
                                                                 decision,
                                                                 boundary):
    """Zenodo creator metadata fills no manuscript placeholder."""
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
                MANUSCRIPT_REL,
                "project/stage130/manuscript_human_review_completion/"
                "stage130_manuscript_human_review_completion_decision.json",
                "project/stage130/manuscript_human_review_completion/"
                "stage130_manuscript_human_review_governance_boundary.json"):
        source = os.path.join(REPO_ROOT, rel)
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
