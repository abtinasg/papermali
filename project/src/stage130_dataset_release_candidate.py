"""Stage130 — deterministic Zenodo dataset Release Candidate builder.

CUSTODY ONLY. This module packages already-frozen bytes. It performs no
scientific work of any kind:

  * It copies frozen files byte-for-byte and hashes them.
  * It verifies headers against the already-committed column-role map — schema
    identity, never row content — and measures, without enforcing, how much of
    the release the upstream data dictionary actually documents.
  * Every count it publishes is READ from the committed Stage125 contract and
    sample summary. Nothing is recounted from row content, because a recount is
    a second, independent claim and this action is not authorized to make one.

It never fits a model, produces a prediction, computes a metric, interval,
replicate, p-value, threshold, SHAP value, subgroup figure or per-year
performance figure. It never opens the Final Test prediction artifact:
:data:`FORBIDDEN_SOURCES` names it and :func:`_guarded_open` refuses it, so a
future edit that reached for one would abort rather than quietly succeed.

Preparation only. Building the candidate creates no Zenodo deposition, uploads
nothing, reserves no DOI and publishes nothing. Those remain gated behind a
separate exact-digest human authorization, and the flags this module emits say
so explicitly.

Determinism
-----------
The archive is a ZIP written with fixed member metadata (the 1980 ZIP epoch,
mode 0644, sorted member order, no directory entries) and ``ZIP_STORED``.
Storing rather than deflating is deliberate: it makes the archive SHA-256 a
pure function of the payload bytes, so a reviewer on a different machine — with
a different zlib — reproduces the same digest. A human is asked to approve that
exact digest, so it must not depend on a compression library version.

Usage::

    python project/src/stage130_dataset_release_candidate.py
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import zipfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

ACTION_ID = "stage130-dataset-release-candidate"
PKG_REL = "project/stage130/dataset_release_candidate"
#: Committed release-specific documents that are copied into the bundle.
TEMPLATE_SUBDIR = "release_payload"
#: Build output. Gitignored: the archive itself is never tracked.
BUILD_SUBDIR = "build"
#: Single top-level directory inside the archive. Every arcname is relative to
#: it, so no absolute local path can reach the bundle.
BUNDLE_ROOT = "tse_financial_distress_dataset_1392_1402"
ARCHIVE_NAME = f"{BUNDLE_ROOT}_release_candidate.zip"

#: Fixed ZIP member metadata. The 1980 epoch is the earliest a ZIP can encode.
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)
_ZIP_MODE = 0o644


class Stage130ReleaseError(RuntimeError):
    """Raised when a gate fails or a prohibited source is reached for."""


# --------------------------------------------------------------------------- #
# The firewall
# --------------------------------------------------------------------------- #

#: Never opened, for any purpose, including custody hashing. Repository
#: governance treats the Final Test cohort as spent by a single authorized
#: pass; this action does not reopen it, and does not package it.
FORBIDDEN_SOURCES = frozenset({
    "project/stage129/stage129_final_test_predictions.json",
    "project/stage129/final_test_execution/stage129_final_test_predictions.json",
    "project/stage129/final_test_execution/stage129_final_test_metrics.json",
})

#: Belt and braces: any path matching one of these fragments is refused even if
#: it is not in FORBIDDEN_SOURCES by name, so a renamed or relocated prediction
#: artifact cannot slip into the payload.
_FORBIDDEN_FRAGMENTS = ("final_test", "prediction", "predictions")


def _guarded_open(root: Path, rel: str) -> bytes:
    """Read a permitted source; refuse every forbidden one, fail-closed."""
    normalized = rel.replace("\\", "/")
    if normalized in FORBIDDEN_SOURCES:
        raise Stage130ReleaseError(
            f"refusing to open a prohibited Final Test artifact: {rel}")
    lowered = normalized.lower()
    if any(fragment in lowered for fragment in _FORBIDDEN_FRAGMENTS):
        raise Stage130ReleaseError(
            f"refusing to open a path that looks like a Final Test or "
            f"prediction artifact: {rel}")
    path = root / normalized
    if not path.is_file():
        raise Stage130ReleaseError(f"required payload source is missing: {rel}")
    return path.read_bytes()


# --------------------------------------------------------------------------- #
# The frozen payload
# --------------------------------------------------------------------------- #

#: (source path, bundle path, role, expected SHA-256, inclusion reason).
#: The digests are the frozen Stage125 Part 3C values. They are pinned HERE as
#: well as in the contract so that a drifted contract cannot re-bless a drifted
#: file: both must agree, and both must match the bytes on disk.
FROZEN_DATASETS: tuple[tuple[str, str, str, str, str], ...] = (
    (
        "project/stage125/part3c_outputs/analysis_ready_main_rule_a_stage125.csv",
        "data/analysis_ready_main_rule_a_stage125.csv",
        "primary_modeling_surface",
        "4d04d7d28808573bb28c30848340b676bed3bb6820e67d8bfd4d9d7e1bb3755e",
        "THE primary analysis-ready modeling surface: the prespecified "
        "main_rule_a leakage-safe company-year panel every headline result "
        "rests on.",
    ),
    (
        "project/stage125/part3c_outputs/analysis_ready_main_rule_b_stage125.csv",
        "data/analysis_ready_main_rule_b_stage125.csv",
        "prespecified_robustness_surface",
        "5492cf244489cb88919243cf2f19d57663ba9e0b0d377791a3a1c26babc9b480",
        "Prespecified listing-rule robustness surface. Not the primary "
        "surface; supplied so the locked robustness design can be reproduced.",
    ),
    (
        "project/stage125/part3c_outputs/analysis_ready_expanded_rule_a_stage125.csv",
        "data/analysis_ready_expanded_rule_a_stage125.csv",
        "prespecified_robustness_surface",
        "fbe9b29c6323b59e830ca9d2dd8c1543b9ef48b21709b01cc56a3989cd2d64d9",
        "Prespecified company-scope robustness surface. Not the primary "
        "surface.",
    ),
    (
        "project/stage125/part3c_outputs/analysis_ready_expanded_rule_b_stage125.csv",
        "data/analysis_ready_expanded_rule_b_stage125.csv",
        "prespecified_robustness_surface",
        "2e61a282165ccdaef37bac61a460c83878f2ae633b10535945cc33897d3b4c22",
        "Prespecified combined company-scope + listing-rule robustness "
        "surface. Not the primary surface.",
    ),
    (
        "project/stage125/part3c_outputs/audited_pairs_main_rule_a_stage125.csv",
        "audit/audited_pairs_main_rule_a_stage125.csv",
        "audit_surface_not_model_ready",
        "66ab136701b563a3ab9a5f4d168fce1b2a8790d73bc9b386963377db67f541f4",
        "Audit surface for main_rule_a. It retains rows the leakage-safe "
        "timing rule excludes, so it is NOT model-ready; it exists so the "
        "exclusions themselves stay inspectable.",
    ),
    (
        "project/stage125/part3c_outputs/audited_pairs_main_rule_b_stage125.csv",
        "audit/audited_pairs_main_rule_b_stage125.csv",
        "audit_surface_not_model_ready",
        "d2d9893e40b0c3bdf876a7447fc5147985fc25c9c5add07264677f6ed817b72c",
        "Audit surface for main_rule_b. NOT model-ready.",
    ),
    (
        "project/stage125/part3c_outputs/audited_pairs_expanded_rule_a_stage125.csv",
        "audit/audited_pairs_expanded_rule_a_stage125.csv",
        "audit_surface_not_model_ready",
        "23ff63d82bbc1a5a06536783eddfa5113ad988cb0db8c1c9adb004489da22bc9",
        "Audit surface for expanded_rule_a. NOT model-ready.",
    ),
    (
        "project/stage125/part3c_outputs/audited_pairs_expanded_rule_b_stage125.csv",
        "audit/audited_pairs_expanded_rule_b_stage125.csv",
        "audit_surface_not_model_ready",
        "56c80ccb0a8bcbb1c030e87c892190579628c298026c6140045cbaf08ff7135f",
        "Audit surface for expanded_rule_b. NOT model-ready.",
    ),
)

#: (source path, bundle path, role, inclusion reason). Committed documentation
#: without which the eight CSVs cannot be read correctly.
DOC_SOURCES: tuple[tuple[str, str, str], ...] = (
    (
        "project/stage125/data_dictionary_stage125.csv",
        "documentation/data_dictionary_stage125.csv",
        "Variable-level dictionary: block, role, type, unit, temporal "
        "reference, source id and provenance status for every field.",
    ),
    (
        "project/stage125/part3c_column_role_map_stage125.csv",
        "documentation/part3c_column_role_map_stage125.csv",
        "Column-role contract: which of the 115 columns are identifiers, "
        "predictor candidates, targets, audit fields, or forbidden from the "
        "model matrix. Required to avoid using a target-derived column as a "
        "feature.",
    ),
    (
        "project/stage125/part3c_sample_summary_stage125.csv",
        "documentation/part3c_sample_summary_stage125.csv",
        "Per-design pair/company/positive/negative counts for all four locked "
        "sample designs, with the frozen output digests.",
    ),
    (
        "project/stage125/part3c_target_year_distribution_stage125.csv",
        "documentation/part3c_target_year_distribution_stage125.csv",
        "Target-year distribution by design and surface: shows how sparse the "
        "positive class is in the later Jalali years.",
    ),
    (
        "project/stage125/part3c_leakage_safe_dataset_contract_stage125.json",
        "documentation/part3c_leakage_safe_dataset_contract_stage125.json",
        "The leakage-safe dataset contract: availability semantics, the "
        "four locked sample designs, expected counts and the explicit "
        "non-claims. This is the authority for every count in this release.",
    ),
    (
        "project/stage125/stage125_part3c_leakage_safe_dataset_qc_report.json",
        "documentation/stage125_part3c_leakage_safe_dataset_qc_report.json",
        "Quality-control report for the finalization step that produced the "
        "eight frozen files.",
    ),
    (
        "project/stage125/source_registry_stage125.csv",
        "documentation/source_registry_stage125.csv",
        "Source registry: which provider each block came from, its status, "
        "and the recorded provenance gaps.",
    ),
    (
        "project/stage125/part4_temporal_split_manifest_stage125.csv",
        "documentation/part4_temporal_split_manifest_stage125.csv",
        "Prespecified temporal split assignment, so the development/holdout "
        "boundary is reproducible without re-deriving it.",
    ),
    (
        "project/stage122/target_definition_stage122.csv",
        "documentation/target_definition_stage122.csv",
        "The operational distress target definition, criterion by criterion, "
        "including its three-valued missing semantics.",
    ),
)

#: Committed release-specific documents, copied byte-for-byte into the bundle.
TEMPLATE_FILES: tuple[str, ...] = (
    "README.md",
    "DATA_DICTIONARY_AND_FILE_GUIDE.md",
    "LICENSE_DATASET.txt",
    "SOURCE_AND_LICENSE_NOTES.md",
    "LIMITATIONS.md",
    "CITATION.cff",
    "zenodo_metadata_candidate.json",
)

#: Integrity descriptors, generated in strict layers so nothing is
#: self-referential: the manifest describes the payload, and SHA256SUMS covers
#: the payload plus the manifest.
MANIFEST_NAME = "release_manifest.json"
SHA256SUMS_NAME = "SHA256SUMS.txt"

#: The primary surface, named once so documentation and manifest agree.
PRIMARY_BUNDLE_REL = "data/analysis_ready_main_rule_a_stage125.csv"

#: Contract-supplied counts for the primary surface, keyed by the contract's own
#: field names. READ from the contract at build time and cross-checked against
#: these; never recomputed from rows.
PRIMARY_CONTRACT_COUNTS = {
    "analysis_ready_pairs": 1012,
    "analysis_ready_companies": 119,
    "analysis_ready_positive": 80,
    "analysis_ready_negative": 932,
}
#: The same four counts under the short names the manifest publishes, so a
#: reader is not made to carry the contract's internal field naming.
PRIMARY_MANIFEST_COUNTS = {
    "pairs": PRIMARY_CONTRACT_COUNTS["analysis_ready_pairs"],
    "companies": PRIMARY_CONTRACT_COUNTS["analysis_ready_companies"],
    "positive": PRIMARY_CONTRACT_COUNTS["analysis_ready_positive"],
    "negative": PRIMARY_CONTRACT_COUNTS["analysis_ready_negative"],
}
PRIMARY_COLUMN_COUNT = 115
CONTRACT_DESIGN_KEY = "main_rule_a_primary"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n").encode("utf-8")


def _csv_header(data: bytes) -> list[str]:
    """First row of a UTF-8 CSV, BOM-tolerant."""
    text = data.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text, newline=""))
    for row in reader:
        return row
    raise Stage130ReleaseError("CSV has no header row")


#: Anything that looks like a machine-local absolute path. A bundle carrying one
#: is not portable and leaks the builder's filesystem layout.
_ABSOLUTE_PATH_RE = re.compile(
    r"(?:/Users/|/home/|/private/tmp/|/var/folders/|[A-Za-z]:\\)")


def assert_no_absolute_paths(name: str, data: bytes) -> None:
    """Fail closed if a generated text member embeds a local absolute path."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return
    match = _ABSOLUTE_PATH_RE.search(text)
    if match:
        raise Stage130ReleaseError(
            f"bundle member {name!r} contains a local absolute path "
            f"({match.group(0)!r}); the bundle must be relocatable")


# --------------------------------------------------------------------------- #
# Gates
# --------------------------------------------------------------------------- #

def gate_frozen_datasets(root: Path) -> dict[str, str]:
    """Every frozen dataset must be present and match its pinned digest.

    Fail-closed and absolute: a missing or drifted file aborts the build. It is
    never regenerated, never reconstructed and never substituted with a
    Stage121-Stage124 predecessor.
    """
    digests: dict[str, str] = {}
    for source_rel, bundle_rel, _role, expected, _reason in FROZEN_DATASETS:
        path = root / source_rel
        if not path.is_file():
            raise Stage130ReleaseError(
                f"frozen dataset ABSENT: {source_rel}. It is not regenerated, "
                "reconstructed or substituted; the build stops here.")
        actual = _sha256(path.read_bytes())
        if actual != expected:
            raise Stage130ReleaseError(
                f"frozen dataset HASH MISMATCH: {source_rel}\n"
                f"  expected {expected}\n  actual   {actual}\n"
                "The frozen surface has drifted; the build stops here.")
        digests[bundle_rel] = actual
    return digests


def gate_contract_agreement(root: Path) -> dict[str, Any]:
    """The contract must independently vouch for the same eight digests.

    Two records pin the same bytes: this module's ``FROZEN_DATASETS`` table and
    the committed Stage125 contract. Requiring both to agree means a silently
    edited contract cannot re-bless a drifted file, and a silently edited table
    cannot outvote the contract.
    """
    contract = json.loads(
        _guarded_open(root,
                      "project/stage125/part3c_leakage_safe_dataset_contract"
                      "_stage125.json").decode("utf-8"))
    bulky = contract.get("bulky_output_sha256") or {}
    for source_rel, _bundle_rel, _role, expected, _reason in FROZEN_DATASETS:
        recorded = bulky.get(source_rel)
        if recorded is None:
            continue  # the contract pins a subset; absence is not disagreement
        if recorded != expected:
            raise Stage130ReleaseError(
                f"contract/builder disagreement for {source_rel}: contract "
                f"pins {recorded}, builder pins {expected}")

    counts = (contract.get("expected_sample_counts") or {}).get(
        CONTRACT_DESIGN_KEY) or {}
    for key, expected in PRIMARY_CONTRACT_COUNTS.items():
        if counts.get(key) != expected:
            raise Stage130ReleaseError(
                f"contract primary-surface {key} is {counts.get(key)!r}, "
                f"expected {expected}")

    role_counts = contract.get("column_role_counts") or {}
    if sum(role_counts.values()) != PRIMARY_COLUMN_COUNT:
        raise Stage130ReleaseError(
            f"contract column-role counts sum to {sum(role_counts.values())}, "
            f"expected {PRIMARY_COLUMN_COUNT}")

    if contract.get("is_observed_publication_timestamp") is not False:
        raise Stage130ReleaseError(
            "the contract must keep is_observed_publication_timestamp = False: "
            "the availability date is a prespecified proxy, not an observation")
    if contract.get("active_lag_months") != 4:
        raise Stage130ReleaseError(
            "the contract must keep the four-month availability lag")
    return contract


def gate_schema(root: Path) -> list[str]:
    """Headers must match the committed column-role contract, exactly.

    Schema identity only: this reads header rows and the role map, never a data
    row's values.
    """
    role_map = _guarded_open(
        root, "project/stage125/part3c_column_role_map_stage125.csv")
    reader = csv.DictReader(io.StringIO(role_map.decode("utf-8-sig"),
                                        newline=""))
    contract_columns = [row["column_name"] for row in reader]
    if len(contract_columns) != PRIMARY_COLUMN_COUNT:
        raise Stage130ReleaseError(
            f"column-role map lists {len(contract_columns)} columns, expected "
            f"{PRIMARY_COLUMN_COUNT}")

    expected_set = set(contract_columns)
    for source_rel, _bundle_rel, _role, _sha, _reason in FROZEN_DATASETS:
        header = _csv_header((root / source_rel).read_bytes())
        if len(header) != PRIMARY_COLUMN_COUNT:
            raise Stage130ReleaseError(
                f"{source_rel} has {len(header)} columns, expected "
                f"{PRIMARY_COLUMN_COUNT}")
        if set(header) != expected_set:
            missing = sorted(expected_set - set(header))
            extra = sorted(set(header) - expected_set)
            raise Stage130ReleaseError(
                f"{source_rel} header disagrees with the column-role "
                f"contract; missing={missing} unexpected={extra}")

    return contract_columns


def measure_dictionary_coverage(root: Path, columns: list[str]) -> dict[str, int]:
    """Measure — not enforce — how much of the release the dictionary covers.

    The authoritative per-column contract is the column-role map, which covers
    all 115 released columns and IS gated above. ``data_dictionary_stage125.csv``
    is a different artifact: a Part 1 variable dictionary over the upstream
    source panel and its candidate blocks, several of which were never
    materialized. It therefore documents only a subset of the released columns.

    That is a real documentation limitation, so it is measured and published
    rather than either enforced (which would block a release over a fact about
    a committed upstream artifact) or ignored (which would overstate the
    documentation a reuser actually gets). ``LIMITATIONS.md`` and the file guide
    state it in prose.
    """
    dictionary = _guarded_open(
        root, "project/stage125/data_dictionary_stage125.csv")
    reader = csv.DictReader(io.StringIO(dictionary.decode("utf-8-sig"),
                                        newline=""))
    documented = {row["variable_name"] for row in reader}
    covered = [c for c in columns if c in documented]
    return {
        "released_columns": len(columns),
        "dictionary_entries": len(documented),
        "released_columns_documented_in_data_dictionary": len(covered),
        "released_columns_not_in_data_dictionary": len(columns) - len(covered),
        "dictionary_entries_not_released": len(documented - set(columns)),
    }


# --------------------------------------------------------------------------- #
# Payload assembly
# --------------------------------------------------------------------------- #

def build_payload(root: Path | str = REPO_ROOT) -> dict[str, bytes]:
    """Assemble the full bundle payload in memory, gates first.

    Returns a mapping of bundle-relative path -> bytes, covering all three
    layers: copied sources, the manifest that describes them, and the checksum
    file that covers both.
    """
    root = Path(root).resolve()

    gate_frozen_datasets(root)
    gate_contract_agreement(root)
    columns = gate_schema(root)
    coverage = measure_dictionary_coverage(root, columns)

    payload: dict[str, bytes] = {}
    entries: list[dict[str, Any]] = []

    for source_rel, bundle_rel, role, expected, reason in FROZEN_DATASETS:
        data = _guarded_open(root, source_rel)
        if _sha256(data) != expected:
            raise Stage130ReleaseError(
                f"frozen dataset changed mid-build: {source_rel}")
        payload[bundle_rel] = data
        entries.append({
            "bundle_path": bundle_rel,
            "bytes": len(data),
            "sha256": expected,
            "role": role,
            "source_path": source_rel,
            "inclusion_reason": reason,
            "copied_byte_for_byte": True,
        })

    for source_rel, bundle_rel, reason in DOC_SOURCES:
        data = _guarded_open(root, source_rel)
        payload[bundle_rel] = data
        entries.append({
            "bundle_path": bundle_rel,
            "bytes": len(data),
            "sha256": _sha256(data),
            "role": "committed_documentation",
            "source_path": source_rel,
            "inclusion_reason": reason,
            "copied_byte_for_byte": True,
        })

    template_dir = f"{PKG_REL}/{TEMPLATE_SUBDIR}"
    for name in TEMPLATE_FILES:
        source_rel = f"{template_dir}/{name}"
        data = _guarded_open(root, source_rel)
        assert_no_absolute_paths(name, data)
        payload[name] = data
        entries.append({
            "bundle_path": name,
            "bytes": len(data),
            "sha256": _sha256(data),
            "role": "release_documentation",
            "source_path": source_rel,
            "inclusion_reason": _TEMPLATE_REASONS[name],
            "copied_byte_for_byte": True,
        })

    manifest = build_manifest(entries, coverage)
    payload[MANIFEST_NAME] = manifest
    assert_no_absolute_paths(MANIFEST_NAME, manifest)

    sums = build_sha256sums(payload)
    payload[SHA256SUMS_NAME] = sums
    assert_no_absolute_paths(SHA256SUMS_NAME, sums)

    return payload


_TEMPLATE_REASONS = {
    "README.md":
        "Entry point: what the release is, which file is primary, and what it "
        "must not be read as.",
    "DATA_DICTIONARY_AND_FILE_GUIDE.md":
        "File-by-file guide mapping each payload file to its role and to the "
        "committed dictionary that documents its columns.",
    "LICENSE_DATASET.txt":
        "The CC BY 4.0 grant, scoped to what the authors actually hold rights "
        "in.",
    "SOURCE_AND_LICENSE_NOTES.md":
        "Provider-by-provider source-use and redistribution audit, including "
        "the unresolved terms that block publication.",
    "LIMITATIONS.md":
        "The limitations a reuser must know before drawing a conclusion from "
        "these files.",
    "CITATION.cff":
        "Machine-readable citation metadata.",
    "zenodo_metadata_candidate.json":
        "Proposed Zenodo deposition metadata. A CANDIDATE: no deposition "
        "exists, no DOI is reserved and publication is not authorized.",
}


def build_manifest(entries: list[dict[str, Any]],
                   coverage: dict[str, int]) -> bytes:
    """Layer 1 — describes every copied payload file.

    Deliberately excludes itself and ``SHA256SUMS.txt``: an integrity record
    that hashed itself would be either circular or a lie.
    """
    ordered = sorted(entries, key=lambda e: e["bundle_path"])
    roles: dict[str, int] = {}
    for entry in ordered:
        roles[entry["role"]] = roles.get(entry["role"], 0) + 1

    return _json_bytes({
        "action_id": ACTION_ID,
        "manifest_version": 1,
        "bundle_root": BUNDLE_ROOT,
        "archive_format": "zip_stored_fixed_timestamps",
        "generated_by": "project/src/stage130_dataset_release_candidate.py",
        "file_count": len(ordered),
        "files": ordered,
        "role_counts": roles,
        "primary_file": PRIMARY_BUNDLE_REL,
        "primary_file_contract_counts": dict(PRIMARY_MANIFEST_COUNTS),
        "primary_file_column_count": PRIMARY_COLUMN_COUNT,
        "column_documentation_coverage": coverage,
        "column_documentation_authority":
            "documentation/part3c_column_role_map_stage125.csv covers all "
            f"{PRIMARY_COLUMN_COUNT} released columns and is authoritative. "
            "data_dictionary_stage125.csv is an upstream-panel variable "
            "dictionary and covers only a subset; see LIMITATIONS.md.",
        "counts_source":
            "documentation/part3c_leakage_safe_dataset_contract_stage125.json"
            " :: expected_sample_counts.main_rule_a_primary",
        "counts_recomputed_from_rows": False,
        "manifest_excludes":
            [MANIFEST_NAME, SHA256SUMS_NAME],
        "manifest_excludes_reason":
            "the manifest describes the payload; SHA256SUMS.txt then covers "
            "the payload AND the manifest. Neither hashes itself.",

        # Every Zenodo-facing fact, restated where a reader will see it.
        "doi": None,
        "zenodo_deposition_created": False,
        "zenodo_upload_performed": False,
        "zenodo_published": False,
        "doi_reserved": False,
        "public_release_authorized": False,
        "release_candidate_prepared": True,

        # Custody boundary.
        "final_test_predictions_opened": False,
        "prediction_artifacts_included": 0,
        "models_fitted": 0,
        "metrics_computed": 0,
        "thresholds_derived": 0,
        "raw_provider_responses_included": 0,
        "source_pdfs_included": 0,
        "credentials_included": 0,
    })


def build_sha256sums(payload: dict[str, bytes]) -> bytes:
    """Layer 2 — ``sha256sum``-compatible lines over payload plus manifest."""
    lines = [
        f"{_sha256(data)}  {name}"
        for name, data in sorted(payload.items())
        if name != SHA256SUMS_NAME
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


# --------------------------------------------------------------------------- #
# Deterministic archive
# --------------------------------------------------------------------------- #

def build_archive(payload: dict[str, bytes]) -> bytes:
    """Write the payload into a byte-reproducible ZIP.

    Fixed timestamps, fixed mode, sorted member order, no directory entries and
    no compression, so the archive digest depends on the payload alone.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(payload):
            info = zipfile.ZipInfo(f"{BUNDLE_ROOT}/{name}",
                                   date_time=_ZIP_EPOCH)
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = _ZIP_MODE << 16
            info.create_system = 3  # Unix, fixed rather than host-dependent
            archive.writestr(info, payload[name])
    return buf.getvalue()


def write_release_candidate(root: Path | str = REPO_ROOT,
                            out_dir: Path | str | None = None) -> dict[str, Any]:
    """Build the candidate and write it to the gitignored build directory."""
    root = Path(root).resolve()
    out = Path(out_dir) if out_dir else root / PKG_REL / BUILD_SUBDIR
    out.mkdir(parents=True, exist_ok=True)

    payload = build_payload(root)
    archive = build_archive(payload)

    tree = out / BUNDLE_ROOT
    for name in sorted(payload):
        target = tree / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload[name])

    archive_path = out / ARCHIVE_NAME
    archive_path.write_bytes(archive)

    return {
        "payload": payload,
        "archive_bytes": archive,
        "archive_path": archive_path,
        "archive_sha256": _sha256(archive),
        "archive_size": len(archive),
        "tree_path": tree,
    }


def main(argv: list[str] | None = None) -> int:
    result = write_release_candidate(REPO_ROOT)
    payload = result["payload"]
    print(f"Stage130 dataset Release Candidate: {len(payload)} payload files")
    for name in sorted(payload):
        print(f"  {_sha256(payload[name])}  {len(payload[name]):>9}  {name}")
    rel = os.path.relpath(result["archive_path"], REPO_ROOT)
    print(f"\narchive        : {rel}")
    print(f"archive bytes  : {result['archive_size']}")
    print(f"archive sha256 : {result['archive_sha256']}")
    print("\nzenodo_deposition_created = false")
    print("zenodo_upload_performed   = false")
    print("zenodo_published          = false")
    print("doi                       = null (none reserved)")
    print("public_release_authorized = false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
