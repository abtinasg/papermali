"""Stage125 Part 3B.0 — Evidence Capture Readiness.

Infrastructure/readiness only: evidence schema validator, immutable raw-cache
contract, default-deny network sentinel, and pure Gate engine scaffolding.
Performs **no** modeling, **no** real evidence capture, **no** network access,
and does **not** modify any frozen Stage125 scientific asset.

Part 3B.1 (evidence capture) is explicitly NOT started by this module.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import multiprocessing
import os
import re
import shutil
import socket
import stat
import subprocess
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

from src import stage125_part3a_decision_lock as lock
from src import stage125_part3a_pilot_protocol as part3a

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

QC_STAGE = "stage125_part3b0_evidence_readiness"
CURRENT_STAGE = "Stage125"
EXPECTED_BASELINE_COMMIT = "75abf3f6d92e514df568e1d6912ccc47cdffc933"
EVIDENCE_SCHEMA_VERSION = "stage125_part3b_evidence_v1"

SRC_REL = "project/src/stage125_part3b0_evidence_readiness.py"
TEST_REL = "project/tests/test_stage125_part3b0_evidence_readiness.py"

PART3A_METADATA_REL = "project/stage125/metadata_and_hashes_stage125_part3a.json"
PART3A1_METADATA_REL = (
    "project/stage125/metadata_and_hashes_stage125_part3a_decision_lock.json"
)
PART1_METADATA_REL = "project/stage125/metadata_and_hashes_stage125_part1.json"

FROZEN_MANIFEST_PATHS = part3a.FROZEN_MANIFEST_PATHS + (
    PART1_METADATA_REL,
    PART3A_METADATA_REL,
    PART3A1_METADATA_REL,
)

FROZEN_INPUT_PATHS = (
    "project/stage125/part3_source_evidence_manifest_schema_stage125.json",
    "project/stage125/accessibility_scoring_rubric_stage125_part3a.json",
    "project/stage125/part3_gate_decision_protocol_stage125.csv",
    "project/stage125/part3a_approved_gate_thresholds_stage125.csv",
    "project/stage125/part3_candidate_inventory_stage125.csv",
    "project/stage125/part3a_selected_pilot_pairs_stage125.csv",
    "project/stage125/part3a_decision_lock_stage125.json",
    "project/stage125/source_registry_stage125.csv",
    "project/stage125/identifier_time_contract_stage125.json",
    "project/stage125/provenance_manifest_schema_stage125.json",
)

F_EVIDENCE_CONTRACT = "part3b0_evidence_capture_contract_stage125.json"
F_EVIDENCE_TEMPLATE = "part3b0_evidence_manifest_template_stage125.csv"
F_GATE_TEMPLATE = "part3b0_gate_result_template_stage125.csv"
F_CACHE_CONTRACT = "part3b0_immutable_cache_contract_stage125.json"
F_CACHE_HANDLE_TEMPLATE = "part3b0_cache_handle_template_stage125.csv"
F_NETWORK_CONTRACT = "part3b0_network_denial_contract_stage125.json"
F_QC = "stage125_part3b0_evidence_readiness_qc_report.json"
F_METADATA = "metadata_and_hashes_stage125_part3b0.json"
F_README = "README_STAGE125_PART3B0_EVIDENCE_READINESS.md"

CACHE_HANDLE_SCHEMA_VERSION = "stage125_part3b0_cache_handle_v1"
CACHE_CONTRACT_VERSION = "stage125_part3b0_v1"
_CACHE_HANDLE_HEADER = [
    "evidence_id",
    "payload_sha256",
    "metadata_sha256",
    "cache_contract_version",
]

CONTENT_FILES = (
    F_EVIDENCE_CONTRACT,
    F_EVIDENCE_TEMPLATE,
    F_GATE_TEMPLATE,
    F_CACHE_CONTRACT,
    F_CACHE_HANDLE_TEMPLATE,
    F_NETWORK_CONTRACT,
    F_README,
)

# Curated exact-path allowlist only (no prefix / directory-wide bypass).
PART3B0_ALLOWED_EXACT = frozenset({
    SRC_REL,
    TEST_REL,
    "project/run_stage125_part3b0.py",
    f"project/stage125/{F_EVIDENCE_CONTRACT}",
    f"project/stage125/{F_EVIDENCE_TEMPLATE}",
    f"project/stage125/{F_GATE_TEMPLATE}",
    f"project/stage125/{F_CACHE_CONTRACT}",
    f"project/stage125/{F_CACHE_HANDLE_TEMPLATE}",
    f"project/stage125/{F_NETWORK_CONTRACT}",
    f"project/stage125/{F_README}",
    f"project/stage125/{F_QC}",
    f"project/stage125/{F_METADATA}",
})

GATE_PASS = "PASS"
GATE_FAIL = "FAIL"
GATE_UNRESOLVED = "UNRESOLVED"
GATE_NOT_APPLIED = "NOT_APPLIED"
ALLOWED_GATE_STATUSES = frozenset({
    GATE_PASS, GATE_FAIL, GATE_UNRESOLVED, GATE_NOT_APPLIED,
})
G01_G07 = ("G01", "G02", "G03", "G04", "G05", "G06", "G07")

SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
ALLOWED_CALENDARS = frozenset({"gregorian", "jalali", "hijri", "unknown"})
ALLOWED_TIMEZONES = frozenset({"UTC", "Asia/Tehran", "unknown"})

SYNTHETIC_EVIDENCE_ID_PREFIX = "synth_"
SYNTHETIC_ACCESS_METHOD = "synthetic_fixture"
SYNTHETIC_INVALID_DOMAIN = ".invalid"

GUESSED_MARKERS = (
    "inferred",
    "guessed",
    "estimated",
    "approximate",
    "assumed",
    "placeholder",
    "tbd",
    "unknown_but_filled",
    "memory_or_reputation",
)

EVIDENCE_SCAN_SUFFIXES = frozenset({
    ".csv", ".tsv", ".json", ".jsonl", ".ndjson", ".parquet", ".xlsx", ".xls",
})
EVIDENCE_NAME_TOKENS = (
    "evidence", "raw_cache", "snapshot",
)
UNAUTHORIZED_NAME_PREFIXES = (
    "part3_evidence_",
    "part3b_evidence_",
    "part3_captured_",
    "part3_raw_snapshot_",
    "part3b_",
    "part3b0_",
)
# Filenames that look like live scoring/decision outputs (not frozen Part 3A locks).
UNAUTHORIZED_NAME_SUFFIX_MARKERS = (
    "_scores.",
    "_score.",
    "_decisions.",
    "_decision_status.",
    "_accessibility_scores.",
)
CACHE_DIR_NAMES = frozenset({"raw_cache", "raw_cache_nested", "immutable_cache"})

_GATE_RESULT_HEADER = [
    "gate_id",
    "gate_name",
    "scope",
    "candidate_id",
    "block",
    "pilot_pair_key",
    "status",
    "detail",
    "notes",
]

BLOCK_CANDIDATES = {
    "M2": [
        c["candidate_id"]
        for c in part3a.REGISTERED_CANDIDATES
        if c["block"] == "M2"
    ],
    "M3": [
        c["candidate_id"]
        for c in part3a.REGISTERED_CANDIDATES
        if c["block"] == "M3"
    ],
    "M4": [
        c["candidate_id"]
        for c in part3a.REGISTERED_CANDIDATES
        if c["block"] == "M4"
    ],
}

_GIT_ALLOWED_SUBCOMMANDS = frozenset({
    "rev-parse", "merge-base", "log", "show", "ls-files", "check-ignore",
})
_GIT_FORBIDDEN_TOKENS = frozenset({
    "--ext-diff", "--textconv", "--exec-path", "--html-path", "--man-path",
    "--info-path", "--namespace", "--list-cmds", "--attr-source",
})
_GIT_ALLOWED_FORMATS = frozenset({"--format=%H", "--format=%cI"})
_POLICY_SEAL_DOMAIN = "stage125_part3b0_locked_gate_policy_v2"
_CLASS_BLOCK_YEAR_USABILITY_SEAL_DOMAIN = (
    "stage125_part3b0_class_block_year_usability_v1"
)
_OS_SPAWN_NAMES = (
    "spawnl", "spawnle", "spawnlp", "spawnlpe",
    "spawnv", "spawnve", "spawnvp", "spawnvpe",
)
_OS_POSIX_SPAWN_NAMES = ("posix_spawn", "posix_spawnp")
_OS_FORK_NAMES = ("fork", "forkpty")
_OS_EXEC_NAMES = (
    "execl", "execle", "execlp", "execlpe",
    "execv", "execve", "execvp", "execvpe",
)
_STAGING_NAME_RE = re.compile(r"^\.staging-([a-f0-9]{16})-[a-f0-9]{32}$")

# Closed-world allowlist of permitted Stage125 tracked files (exact paths).
STAGE125_ALLOWED_EXACT = frozenset({
    "project/stage125/README_STAGE125_PART1_DATA_CONTRACT.md",
    "project/stage125/README_STAGE125_PART2_PREDICTION_TIME_CONTRACT.md",
    "project/stage125/README_STAGE125_PART3A_DECISION_LOCK.md",
    "project/stage125/README_STAGE125_PART3A_PILOT_PROTOCOL.md",
    "project/stage125/README_STAGE125_PART3B0_EVIDENCE_READINESS.md",
    "project/stage125/README_STAGE125_PART3B1_DECISION_LOCK.md",
    "project/stage125/README_STAGE125_PART3B1A_CUT_A_AVAILABLE_AT_LOCK.md",
    "project/stage125/README_STAGE125_PART3B1_FEATURE_DEFINITION_SCORING_ADJUDICATION.md",
    "project/stage125/accessibility_scoring_rubric_stage125_part3a.json",
    "project/stage125/data_admission_gate_template_stage125.csv",
    "project/stage125/data_dictionary_stage125.csv",
    "project/stage125/feature_availability_audit_stage125_part2.csv",
    "project/stage125/feature_availability_contract_stage125_part2.json",
    "project/stage125/identifier_time_contract_stage125.json",
    "project/stage125/leakage_audit_stage125_part2.csv",
    "project/stage125/leakage_checklist_stage125_part2.json",
    "project/stage125/m1_provenance_gap_audit_stage125.csv",
    "project/stage125/m1_provenance_gap_summary_stage125.json",
    "project/stage125/metadata_and_hashes_stage125_part1.json",
    "project/stage125/metadata_and_hashes_stage125_part2.json",
    "project/stage125/metadata_and_hashes_stage125_part3a.json",
    "project/stage125/metadata_and_hashes_stage125_part3a_decision_lock.json",
    "project/stage125/metadata_and_hashes_stage125_part3b0.json",
    "project/stage125/metadata_and_hashes_stage125_part3b1.json",
    "project/stage125/metadata_and_hashes_stage125_part3b1a.json",
    "project/stage125/part3_candidate_inventory_stage125.csv",
    "project/stage125/part3_gate_decision_protocol_stage125.csv",
    "project/stage125/part3_pilot_sampling_options_stage125.csv",
    "project/stage125/part3_sampling_frame_by_target_year_stage125.csv",
    "project/stage125/part3_sampling_frame_summary_stage125.json",
    "project/stage125/part3_source_evidence_manifest_schema_stage125.json",
    "project/stage125/part3a_approved_gate_thresholds_stage125.csv",
    "project/stage125/part3a_decision_lock_stage125.json",
    "project/stage125/part3a_selected_pilot_pairs_stage125.csv",
    "project/stage125/part3b0_evidence_capture_contract_stage125.json",
    "project/stage125/part3b0_evidence_manifest_template_stage125.csv",
    "project/stage125/part3b0_gate_result_template_stage125.csv",
    "project/stage125/part3b0_immutable_cache_contract_stage125.json",
    "project/stage125/part3b0_cache_handle_template_stage125.csv",
    "project/stage125/part3b0_network_denial_contract_stage125.json",
    "project/stage125/part3b1_cutoff_available_at_contract_stage125.json",
    "project/stage125/part3b1_decision_lock_stage125.json",
    "project/stage125/part3b1_adjudicated_decision_requirements_stage125.json",
    "project/stage125/part3b1_m2_feature_formula_contract_stage125.json",
    "project/stage125/part3b1_m3_cbi_policy_contract_stage125.json",
    "project/stage125/part3b1_m4_feature_definition_contract_stage125.json",
    "project/stage125/part3b1_rubric_operational_mapping_stage125.json",
    "project/stage125/part3b1_selected_decisions_stage125.csv",
    "project/stage125/part3b1a_cut_a_available_at_decision_lock_stage125.json",
    "project/stage125/part3b1a_cut_a_available_at_operationalization_contract_stage125.json",
    "project/stage125/prediction_cutoff_audit_stage125_part2.csv",
    "project/stage125/prediction_cutoff_summary_stage125_part2.json",
    "project/stage125/prediction_time_contract_stage125_part2.json",
    "project/stage125/provenance_manifest_schema_stage125.json",
    "project/stage125/source_registry_stage125.csv",
    "project/stage125/stage125_part1_data_contract_qc_report.json",
    "project/stage125/stage125_part2_prediction_time_contract_qc_report.json",
    "project/stage125/stage125_part3a_decision_lock_qc_report.json",
    "project/stage125/stage125_part3a_pilot_protocol_qc_report.json",
    "project/stage125/stage125_part3b0_evidence_readiness_qc_report.json",
    "project/stage125/stage125_part3b1_decision_lock_qc_report.json",
    "project/stage125/stage125_part3b1a_cut_a_available_at_qc_report.json",
})


class QCFail(RuntimeError):
    """Fail-closed error for Stage125 Part 3B.0."""


class NetworkBlockedError(OSError):
    """Raised when the default-deny network sentinel intercepts a call."""


class EvidenceValidationError(ValueError):
    """Fail-closed evidence schema validation error."""


class ImmutableCacheError(RuntimeError):
    """Fail-closed immutable cache contract error."""


# --------------------------------------------------------------------------- #
# Hashing / git helpers
# --------------------------------------------------------------------------- #

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str | None:
    if not Path(path).is_file():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_allowed_git_command(cmd: list[str]) -> bool:
    """Allow only exact argument-level read-only git used by Part 3B.0 QC."""
    if not cmd or len(cmd) < 4:
        return False
    # Literal argv[0] must be "git" (reject absolute/renamed wrappers).
    if cmd[0] != "git":
        return False
    if cmd[1] != "-C" or not str(cmd[2]).strip():
        return False
    args = list(cmd[3:])
    for tok in args:
        low = tok.lower()
        if low in _GIT_FORBIDDEN_TOKENS:
            return False
        if low == "-c" or low.startswith("--config"):
            return False
        if "ext-diff" in low or "textconv" in low:
            return False
    if not args or args[0] not in _GIT_ALLOWED_SUBCOMMANDS:
        return False
    sub, rest = args[0], args[1:]
    if sub == "rev-parse":
        return len(rest) == 1 and not rest[0].startswith("-")
    if sub == "merge-base":
        if rest[:1] == ["--is-ancestor"]:
            return len(rest) == 3 and all(not x.startswith("-") for x in rest[1:])
        return len(rest) == 2 and all(not x.startswith("-") for x in rest)
    if sub == "ls-files":
        return rest == []
    if sub == "check-ignore":
        return (
            len(rest) >= 3
            and rest[0] == "-q"
            and rest[1] == "--"
            and all(not x.startswith("-") for x in rest[2:])
        )
    if sub == "log":
        # git -C <repo> log -1 --format=%H|--format=%cI -- <path>...
        if (
            len(rest) >= 4
            and rest[0] == "-1"
            and rest[1] in _GIT_ALLOWED_FORMATS
            and rest[2] == "--"
            and all(not x.startswith("-") for x in rest[3:])
        ):
            return True
        # git -C <repo> log --format=%H -n 1 -- <path>...
        if (
            len(rest) >= 5
            and rest[0] in _GIT_ALLOWED_FORMATS
            and rest[1] == "-n"
            and rest[2] == "1"
            and rest[3] == "--"
            and all(not x.startswith("-") for x in rest[4:])
        ):
            return True
        # git -C <repo> log -1 --format=%cI <commit>
        if (
            len(rest) == 3
            and rest[0] == "-1"
            and rest[1] in _GIT_ALLOWED_FORMATS
            and not rest[2].startswith("-")
        ):
            return True
        return False
    if sub == "show":
        return (
            len(rest) == 3
            and rest[0] == "-s"
            and rest[1] in _GIT_ALLOWED_FORMATS
            and not rest[2].startswith("-")
        )
    return False


def _git(repo_root: str, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", repo_root, *args], capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise QCFail(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def _is_ancestor(repo_root: str, ancestor: str, descendant: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", repo_root, "merge-base", "--is-ancestor",
         ancestor, descendant],
        capture_output=True,
    )
    return proc.returncode == 0


def verify_baseline_commit(repo_root: str) -> None:
    if not _is_ancestor(repo_root, EXPECTED_BASELINE_COMMIT, "HEAD"):
        raise QCFail(
            f"expected baseline commit {EXPECTED_BASELINE_COMMIT} is not an "
            "ancestor of HEAD (fail-closed)"
        )
    origin_main = _git(repo_root, "rev-parse", "origin/main")
    if origin_main and origin_main != EXPECTED_BASELINE_COMMIT:
        mb = _git(repo_root, "merge-base", "origin/main", EXPECTED_BASELINE_COMMIT)
        if mb != EXPECTED_BASELINE_COMMIT:
            raise QCFail(
                f"origin/main ({origin_main}) does not contain expected "
                f"baseline {EXPECTED_BASELINE_COMMIT}"
            )


def _git_last_code_commit(repo_root: str, paths: list[str]) -> str:
    for path in paths:
        commit = _git(repo_root, "log", "-1", "--format=%H", "--", path)
        if commit:
            return commit
    return _git(repo_root, "rev-parse", "HEAD")


def _git_commit_timestamp(repo_root: str, commit: str) -> str:
    return _git(repo_root, "show", "-s", "--format=%cI", commit)


def frozen_asset_hashes(repo_root: Path) -> dict[str, str]:
    return part3a.frozen_asset_hashes(repo_root)


def verify_frozen_input_hashes(repo_root: Path) -> dict[str, str]:
    """Verify frozen Part 3B.0 input files against existing Stage125 manifests."""
    manifests = {
        PART1_METADATA_REL: {
            "source_registry_stage125.csv",
            "identifier_time_contract_stage125.json",
            "provenance_manifest_schema_stage125.json",
        },
        PART3A_METADATA_REL: {
            "part3_source_evidence_manifest_schema_stage125.json",
            "accessibility_scoring_rubric_stage125_part3a.json",
            "part3_gate_decision_protocol_stage125.csv",
            "part3_candidate_inventory_stage125.csv",
        },
        PART3A1_METADATA_REL: {
            "part3a_approved_gate_thresholds_stage125.csv",
            "part3a_selected_pilot_pairs_stage125.csv",
            "part3a_decision_lock_stage125.json",
        },
    }
    verified: dict[str, str] = {}
    for manifest_rel, basenames in manifests.items():
        manifest_path = repo_root / manifest_rel
        if not manifest_path.is_file():
            raise QCFail(f"missing frozen manifest {manifest_rel}")
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        output_hashes = data.get("output_files_sha256", {})
        for rel in FROZEN_INPUT_PATHS:
            basename = Path(rel).name
            if basename not in basenames:
                continue
            expected = output_hashes.get(basename)
            if expected is None:
                raise QCFail(
                    f"{basename} not listed in {manifest_rel} output_files_sha256"
                )
            actual = sha256_file(repo_root / rel)
            if actual != expected:
                raise QCFail(
                    f"frozen input hash mismatch for {rel}: "
                    f"expected {expected}, got {actual}"
                )
            verified[rel] = actual
    missing = set(FROZEN_INPUT_PATHS) - set(verified)
    if missing:
        raise QCFail(
            "frozen input paths not verified via manifests: "
            + ", ".join(sorted(missing))
        )
    return verified


def load_frozen_evidence_schema(repo_root: Path) -> dict:
    path = repo_root / FROZEN_INPUT_PATHS[0]
    schema = json.loads(path.read_text(encoding="utf-8"))
    if schema.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
        raise QCFail(
            f"evidence schema version mismatch: expected "
            f"{EVIDENCE_SCHEMA_VERSION}, got {schema.get('schema_version')}"
        )
    return schema


def evidence_header_from_schema(schema: dict) -> list[str]:
    fields = schema.get("required_fields", [])
    return [f["name"] for f in fields]


def load_source_registry(repo_root: Path) -> dict[str, dict]:
    path = repo_root / "project/stage125/source_registry_stage125.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    return {r["source_id"]: r for r in rows if r.get("source_id")}


def load_candidate_source_map(repo_root: Path) -> dict[str, str]:
    path = repo_root / "project/stage125/part3_candidate_inventory_stage125.csv"
    mapping: dict[str, str] = {}
    for row in csv.DictReader(path.open(encoding="utf-8")):
        cid = row.get("candidate_id", "")
        scope = row.get("candidate_scope_status", "")
        if scope == "registered_candidate" and cid:
            mapping[cid] = row.get("source_id", "")
    return mapping


def load_locked_pilot_pairs(repo_root: Path) -> list[dict]:
    path = repo_root / "project/stage125/part3a_selected_pilot_pairs_stage125.csv"
    return list(csv.DictReader(path.open(encoding="utf-8")))


# --------------------------------------------------------------------------- #
# Locked G09–G14 policy (hash-verified frozen artifacts only)
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class LockedGatePolicy:
    g09_threshold: float
    g10_threshold: float
    g11_minimum: int
    g12_minimum: int
    g13_expected: int
    g14_option_id: str
    target_years: tuple[str, ...]
    source_thresholds_sha256: str
    source_decision_lock_sha256: str
    frozen_pilot_keys: frozenset[str]
    frozen_pilot_key_labels: frozenset[tuple[str, str]]
    frozen_pilot_key_years: frozenset[tuple[str, str]]
    source_pilot_pairs_sha256: str
    _seal: str = field(repr=False, compare=True)


def _expected_target_years() -> tuple[str, ...]:
    return tuple(sorted(lock.EXPECTED_YEAR_ALLOCATION.keys()))


def _canonical_key_set_hash(pilot_keys: frozenset[str]) -> str:
    keys_blob = "\n".join(sorted(pilot_keys))
    return sha256_bytes(keys_blob.encode("utf-8"))


def _canonical_key_pair_hash(pairs: frozenset[tuple[str, str]]) -> str:
    blob = "\n".join(f"{k}\t{v}" for k, v in sorted(pairs))
    return sha256_bytes(blob.encode("utf-8"))


def _compute_policy_seal(
    thr_hash: str,
    lock_hash: str,
    pilot_pairs_hash: str,
    pilot_keys: frozenset[str],
    pilot_key_labels: frozenset[tuple[str, str]],
    pilot_key_years: frozenset[tuple[str, str]],
) -> str:
    """Seal binds verified source hashes to locked G09–G14 values and identity."""
    payload = "|".join([
        _POLICY_SEAL_DOMAIN,
        "0.80",
        "0.70",
        "3",
        "3",
        "80",
        lock.APPROVED_PILOT_OPTION,
        ",".join(_expected_target_years()),
        thr_hash,
        lock_hash,
        pilot_pairs_hash,
        _canonical_key_set_hash(pilot_keys),
        _canonical_key_pair_hash(pilot_key_labels),
        _canonical_key_pair_hash(pilot_key_years),
    ])
    return sha256_bytes(payload.encode("utf-8"))


def _validate_frozen_pilot_identity_sets(
    frozen_keys: frozenset[str],
    frozen_labels: frozenset[tuple[str, str]],
    frozen_years: frozenset[tuple[str, str]],
) -> None:
    """Require exact 80-key projection, labels, years, and 39/41/0 allocation."""
    if type(frozen_keys) is not frozenset or type(frozen_labels) is not frozenset:
        raise QCFail("LockedGatePolicy identity set types invalid")
    if type(frozen_years) is not frozenset:
        raise QCFail("LockedGatePolicy identity set types invalid")
    if len(frozen_keys) != 80:
        raise QCFail("LockedGatePolicy frozen key count must be 80")
    if any(type(k) is not str or not k for k in frozen_keys):
        raise QCFail("LockedGatePolicy frozen keys must be non-empty str")
    if len(frozen_labels) != 80 or len(frozen_years) != 80:
        raise QCFail("LockedGatePolicy label/year pair counts must be 80")
    label_keys: list[str] = []
    year_keys: list[str] = []
    for item in frozen_labels:
        if (
            type(item) is not tuple
            or len(item) != 2
            or type(item[0]) is not str
            or type(item[1]) is not str
        ):
            raise QCFail("LockedGatePolicy label pairs must be (str, str)")
        label_keys.append(item[0])
        if item[1] not in ("positive", "negative", "unknown"):
            raise QCFail("LockedGatePolicy class labels invalid")
    for item in frozen_years:
        if (
            type(item) is not tuple
            or len(item) != 2
            or type(item[0]) is not str
            or type(item[1]) is not str
        ):
            raise QCFail("LockedGatePolicy year pairs must be (str, str)")
        year_keys.append(item[0])
        if item[1] not in _expected_target_years():
            raise QCFail("LockedGatePolicy target years invalid")
    if len(label_keys) != len(set(label_keys)):
        raise QCFail("LockedGatePolicy duplicate label keys rejected")
    if len(year_keys) != len(set(year_keys)):
        raise QCFail("LockedGatePolicy duplicate year keys rejected")
    if frozenset(label_keys) != frozen_keys:
        raise QCFail("LockedGatePolicy label key projection mismatch")
    if frozenset(year_keys) != frozen_keys:
        raise QCFail("LockedGatePolicy year key projection mismatch")
    pos = sum(1 for _, lab in frozen_labels if lab == "positive")
    neg = sum(1 for _, lab in frozen_labels if lab == "negative")
    unk = sum(1 for _, lab in frozen_labels if lab == "unknown")
    if (
        pos != lock.APPROVED_POSITIVE
        or neg != lock.APPROVED_NEGATIVE
        or unk != lock.APPROVED_UNKNOWN
    ):
        raise QCFail("LockedGatePolicy 39/41/0 class allocation mismatch")
    label_by_key = {k: lab for k, lab in frozen_labels}
    year_by_key = {k: y for k, y in frozen_years}
    allocation: dict[str, dict[str, int]] = {
        y: {"positive": 0, "negative": 0, "unknown": 0}
        for y in _expected_target_years()
    }
    for key in frozen_keys:
        year = year_by_key[key]
        lab = label_by_key[key]
        allocation[year][lab] += 1
    if allocation != lock.EXPECTED_YEAR_ALLOCATION:
        raise QCFail("LockedGatePolicy frozen year allocation mismatch")


def require_sealed_gate_policy(policy: LockedGatePolicy) -> LockedGatePolicy:
    """Reject forged/weakened LockedGatePolicy instances (fail closed)."""
    if type(policy) is not LockedGatePolicy:
        raise QCFail("LockedGatePolicy type check failed")
    expected_seal = _compute_policy_seal(
        policy.source_thresholds_sha256,
        policy.source_decision_lock_sha256,
        policy.source_pilot_pairs_sha256,
        policy.frozen_pilot_keys,
        policy.frozen_pilot_key_labels,
        policy.frozen_pilot_key_years,
    )
    if policy._seal != expected_seal:
        raise QCFail("LockedGatePolicy seal verification failed")
    if (
        policy.g09_threshold != 0.80
        or policy.g10_threshold != 0.70
        or policy.g11_minimum != 3
        or policy.g12_minimum != 3
        or policy.g13_expected != 80
        or policy.g14_option_id != lock.APPROVED_PILOT_OPTION
        or tuple(policy.target_years) != _expected_target_years()
        or not SHA256_RE.match(policy.source_thresholds_sha256 or "")
        or not SHA256_RE.match(policy.source_decision_lock_sha256 or "")
        or not SHA256_RE.match(policy.source_pilot_pairs_sha256 or "")
    ):
        raise QCFail("LockedGatePolicy value verification failed")
    _validate_frozen_pilot_identity_sets(
        policy.frozen_pilot_keys,
        policy.frozen_pilot_key_labels,
        policy.frozen_pilot_key_years,
    )
    return policy


def require_frozen_pilot_key_identity(
    policy: LockedGatePolicy, pilot_keys: Any,
) -> frozenset[str]:
    """Fail closed unless caller supplies the exact frozen pilot key set."""
    policy = require_sealed_gate_policy(policy)
    if type(pilot_keys) is list:
        if any(type(k) is not str for k in pilot_keys):
            raise QCFail("pilot_keys must contain only str identifiers")
        if len(pilot_keys) != len(set(pilot_keys)):
            raise QCFail("duplicate pilot keys rejected")
        supplied = frozenset(pilot_keys)
    elif type(pilot_keys) in (set, frozenset):
        if any(type(k) is not str for k in pilot_keys):
            raise QCFail("pilot_keys must contain only str identifiers")
        supplied = frozenset(pilot_keys)
    else:
        raise QCFail("pilot_keys must be a list/set/frozenset of frozen identifiers")
    if supplied != policy.frozen_pilot_keys:
        raise QCFail("pilot key identity mismatch with frozen selection")
    return supplied


def require_frozen_pilot_label_identity(
    policy: LockedGatePolicy, key_labels: Any,
) -> frozenset[tuple[str, str]]:
    policy = require_sealed_gate_policy(policy)
    if type(key_labels) not in (set, frozenset, list):
        raise QCFail("pilot key labels must be a set/frozenset/list")
    pairs: list[tuple[str, str]] = []
    for item in key_labels:
        if (
            type(item) is not tuple
            or len(item) != 2
            or type(item[0]) is not str
            or type(item[1]) is not str
        ):
            raise QCFail("pilot key labels must be (str, str) pairs")
        pairs.append(item)
    if len(pairs) != len(set(pairs)):
        raise QCFail("duplicate pilot key labels rejected")
    supplied = frozenset(pairs)
    if supplied != policy.frozen_pilot_key_labels:
        raise QCFail("pilot key label identity mismatch with frozen selection")
    return supplied


def require_frozen_pilot_year_identity(
    policy: LockedGatePolicy, key_years: Any,
) -> frozenset[tuple[str, str]]:
    policy = require_sealed_gate_policy(policy)
    if type(key_years) not in (set, frozenset, list):
        raise QCFail("pilot key years must be a set/frozenset/list")
    pairs: list[tuple[str, str]] = []
    for item in key_years:
        if (
            type(item) is not tuple
            or len(item) != 2
            or type(item[0]) is not str
            or type(item[1]) is not str
        ):
            raise QCFail("pilot key years must be (str, str) pairs")
        pairs.append(item)
    if len(pairs) != len(set(pairs)):
        raise QCFail("duplicate pilot key years rejected")
    supplied = frozenset(pairs)
    if supplied != policy.frozen_pilot_key_years:
        raise QCFail("pilot key year identity mismatch with frozen selection")
    return supplied


def load_locked_gate_policy(repo_root: Path) -> LockedGatePolicy:
    """Load G09–G14 policy exclusively from hash-verified frozen artifacts."""
    verified = verify_frozen_input_hashes(repo_root)
    thr_rel = "project/stage125/part3a_approved_gate_thresholds_stage125.csv"
    lock_rel = "project/stage125/part3a_decision_lock_stage125.json"
    pairs_rel = "project/stage125/part3a_selected_pilot_pairs_stage125.csv"
    thr_path = repo_root / thr_rel
    rows = {r["gate_id"]: r for r in csv.DictReader(thr_path.open(encoding="utf-8"))}
    required = {"G09", "G10", "G11", "G12", "G13", "G14"}
    if set(rows) != required:
        raise QCFail(f"locked thresholds missing gates: {required - set(rows)}")

    def _float(gid: str) -> float:
        try:
            return float(rows[gid]["threshold_value"])
        except (TypeError, ValueError) as exc:
            raise QCFail(f"invalid threshold for {gid}") from exc

    def _int(gid: str) -> int:
        try:
            return int(rows[gid]["threshold_value"])
        except (TypeError, ValueError) as exc:
            raise QCFail(f"invalid threshold for {gid}") from exc

    g14_option = str(rows["G14"]["threshold_value"]).strip()
    if g14_option != lock.APPROVED_PILOT_OPTION:
        raise QCFail(
            f"G14 locked option mismatch: {g14_option!r} vs "
            f"{lock.APPROVED_PILOT_OPTION!r}"
        )
    thr_hash = verified[thr_rel]
    lock_hash = verified[lock_rel]
    pairs_hash = verified[pairs_rel]
    pilot_rows = load_locked_pilot_pairs(repo_root)
    keys = [r["predictor_row_key_t"] for r in pilot_rows]
    if len(keys) != 80 or len(set(keys)) != 80:
        raise QCFail("frozen pilot key set must be exactly 80 unique keys")
    labels = frozenset(
        (r["predictor_row_key_t"], r["class_label"]) for r in pilot_rows
    )
    years = frozenset(
        (r["predictor_row_key_t"], str(r["target_year"])) for r in pilot_rows
    )
    frozen_keys = frozenset(keys)
    policy = LockedGatePolicy(
        g09_threshold=_float("G09"),
        g10_threshold=_float("G10"),
        g11_minimum=_int("G11"),
        g12_minimum=_int("G12"),
        g13_expected=_int("G13"),
        g14_option_id=g14_option,
        target_years=_expected_target_years(),
        source_thresholds_sha256=thr_hash,
        source_decision_lock_sha256=lock_hash,
        frozen_pilot_keys=frozen_keys,
        frozen_pilot_key_labels=labels,
        frozen_pilot_key_years=years,
        source_pilot_pairs_sha256=pairs_hash,
        _seal=_compute_policy_seal(
            thr_hash, lock_hash, pairs_hash, frozen_keys, labels, years,
        ),
    )
    return require_sealed_gate_policy(policy)


# --------------------------------------------------------------------------- #
# Network sentinel (default-deny)
# --------------------------------------------------------------------------- #

class NetworkSentinel:
    """Default-deny network sentinel for Part 3B.0 execution and tests."""

    def __init__(self) -> None:
        self.calls_attempted = 0
        self._orig_connect = socket.socket.connect
        self._orig_connect_ex = socket.socket.connect_ex
        self._orig_create_connection = socket.create_connection
        self._orig_getaddrinfo = socket.getaddrinfo
        self._orig_gethostbyname = socket.gethostbyname
        self._orig_gethostbyname_ex = getattr(socket, "gethostbyname_ex", None)
        self._orig_gethostbyaddr = getattr(socket, "gethostbyaddr", None)
        self._orig_sendto = socket.socket.sendto
        self._orig_sendmsg = getattr(socket.socket, "sendmsg", None)
        self._orig_subprocess_run = subprocess.run
        self._orig_subprocess_popen = subprocess.Popen
        self._orig_os_system = os.system
        self._orig_os_popen = os.popen
        self._orig_os_process_routes: dict[str, Any] = {
            name: getattr(os, name)
            for name in (
                *_OS_SPAWN_NAMES,
                *_OS_POSIX_SPAWN_NAMES,
                *_OS_FORK_NAMES,
                *_OS_EXEC_NAMES,
            )
            if hasattr(os, name)
        }
        # Backward-compatible alias used by existing spawn spy tests.
        self._orig_os_spawns = {
            name: fn
            for name, fn in self._orig_os_process_routes.items()
            if name in _OS_SPAWN_NAMES
        }
        self._orig_mp_process_start = multiprocessing.Process.start
        self._module_patches: list[tuple[Any, str, Any]] = []

    def _blocked(self, label: str, *args, **kwargs):
        self.calls_attempted += 1
        raise NetworkBlockedError(
            f"network blocked by Part 3B.0 sentinel ({label}): {args!r}"
        )

    def _blocked_os_launch(self, label: str, *args, **kwargs):
        """Deny os child/process-replacement routes before any child is created."""
        self._blocked(label, *args, **kwargs)

    def _blocked_connect(self, _sock, *args, **kwargs):
        self._blocked("socket.connect", *args, **kwargs)

    def _blocked_connect_ex(self, _sock, *args, **kwargs):
        self._blocked("socket.connect_ex", *args, **kwargs)

    def _blocked_create_connection(self, *args, **kwargs):
        self._blocked("socket.create_connection", *args, **kwargs)

    def _blocked_getaddrinfo(self, *args, **kwargs):
        self._blocked("socket.getaddrinfo", *args, **kwargs)

    def _blocked_gethostbyname(self, *args, **kwargs):
        self._blocked("socket.gethostbyname", *args, **kwargs)

    def _blocked_gethostbyname_ex(self, *args, **kwargs):
        self._blocked("socket.gethostbyname_ex", *args, **kwargs)

    def _blocked_gethostbyaddr(self, *args, **kwargs):
        self._blocked("socket.gethostbyaddr", *args, **kwargs)

    def _blocked_sendto(self, _sock, *args, **kwargs):
        self._blocked("socket.sendto", *args, **kwargs)

    def _blocked_sendmsg(self, _sock, *args, **kwargs):
        self._blocked("socket.sendmsg", *args, **kwargs)

    def _normalize_cmd(self, args: Any) -> list[str]:
        if isinstance(args, (str, bytes)):
            # String command form is never an exact argv allowlist match.
            return [os.fsdecode(args)]
        try:
            return [
                os.fsdecode(a) if isinstance(a, (bytes, os.PathLike)) else str(a)
                for a in args
            ]
        except TypeError:
            return [str(args)]

    def _extract_cmd(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
        if "args" in kwargs and kwargs["args"] is not None:
            return kwargs["args"]
        if args:
            return args[0]
        return None

    def _guard_subprocess(
        self, label: str, args: tuple[Any, ...], kwargs: dict[str, Any],
    ) -> None:
        if kwargs.get("shell"):
            self._blocked(label, "shell=True")
        raw = self._extract_cmd(args, kwargs)
        if raw is None:
            self._blocked(label, "missing command args")
        if isinstance(raw, (str, bytes)):
            self._blocked(label, "string command form denied", raw)
        cmd = self._normalize_cmd(raw)
        if _is_allowed_git_command(cmd):
            return
        # Default-deny: every non-allowlisted subprocess is blocked before spawn.
        self._blocked(label, *cmd)

    def install(self) -> None:
        socket.socket.connect = self._blocked_connect  # type: ignore[method-assign]
        socket.socket.connect_ex = self._blocked_connect_ex  # type: ignore[method-assign]
        socket.create_connection = self._blocked_create_connection  # type: ignore[assignment]
        socket.getaddrinfo = self._blocked_getaddrinfo  # type: ignore[assignment]
        socket.gethostbyname = self._blocked_gethostbyname  # type: ignore[assignment]
        if self._orig_gethostbyname_ex is not None:
            socket.gethostbyname_ex = self._blocked_gethostbyname_ex  # type: ignore[assignment]
        if self._orig_gethostbyaddr is not None:
            socket.gethostbyaddr = self._blocked_gethostbyaddr  # type: ignore[assignment]
        socket.socket.sendto = self._blocked_sendto  # type: ignore[method-assign]
        if self._orig_sendmsg is not None:
            socket.socket.sendmsg = self._blocked_sendmsg  # type: ignore[method-assign]

        sentinel = self

        def _run(*args, **kwargs):
            sentinel._guard_subprocess("subprocess.run", args, kwargs)
            return sentinel._orig_subprocess_run(*args, **kwargs)

        class _Popen(subprocess.Popen):
            def __init__(self, *args, **kwargs):
                sentinel._guard_subprocess("subprocess.Popen", args, kwargs)
                super().__init__(*args, **kwargs)

        subprocess.run = _run  # type: ignore[assignment]
        subprocess.Popen = _Popen  # type: ignore[misc,assignment]

        os.system = (  # type: ignore[assignment]
            lambda *a, **k: self._blocked_os_launch("os.system", *a, **k)
        )
        os.popen = (  # type: ignore[assignment]
            lambda *a, **k: self._blocked_os_launch("os.popen", *a, **k)
        )
        for route_name in self._orig_os_process_routes:
            setattr(
                os,
                route_name,
                (
                    lambda *a, _n=route_name, **k: self._blocked_os_launch(
                        f"os.{_n}", *a, **k
                    )
                ),
            )

        def _blocked_mp_process_start(proc, *args, **kwargs):  # noqa: ARG001
            sentinel._blocked("multiprocessing.Process.start", *args, **kwargs)

        multiprocessing.Process.start = (  # type: ignore[method-assign,assignment]
            _blocked_mp_process_start
        )

        try:
            import urllib.request as urllib_request

            self._module_patches.append(
                (urllib_request, "urlopen", urllib_request.urlopen)
            )
            urllib_request.urlopen = (  # type: ignore[assignment]
                lambda *a, **k: self._blocked("urllib.request.urlopen", *a, **k)
            )
            if hasattr(urllib_request, "urlretrieve"):
                self._module_patches.append(
                    (urllib_request, "urlretrieve", urllib_request.urlretrieve)
                )
                urllib_request.urlretrieve = (  # type: ignore[assignment]
                    lambda *a, **k: self._blocked(
                        "urllib.request.urlretrieve", *a, **k
                    )
                )
        except ImportError:
            pass
        try:
            import http.client as http_client

            self._module_patches.append(
                (http_client, "HTTPConnection", http_client.HTTPConnection)
            )
            self._module_patches.append(
                (http_client, "HTTPSConnection", http_client.HTTPSConnection)
            )

            class _BlockedHTTPConnection(http_client.HTTPConnection):
                def connect(inner_self):  # noqa: N805
                    self._blocked("http.client.HTTPConnection.connect")

            class _BlockedHTTPSConnection(http_client.HTTPSConnection):
                def connect(inner_self):  # noqa: N805
                    self._blocked("http.client.HTTPSConnection.connect")

            http_client.HTTPConnection = _BlockedHTTPConnection  # type: ignore[misc,assignment]
            http_client.HTTPSConnection = _BlockedHTTPSConnection  # type: ignore[misc,assignment]
        except ImportError:
            pass

    def restore(self) -> None:
        socket.socket.connect = self._orig_connect  # type: ignore[method-assign]
        socket.socket.connect_ex = self._orig_connect_ex  # type: ignore[method-assign]
        socket.create_connection = self._orig_create_connection  # type: ignore[assignment]
        socket.getaddrinfo = self._orig_getaddrinfo  # type: ignore[assignment]
        socket.gethostbyname = self._orig_gethostbyname  # type: ignore[assignment]
        if self._orig_gethostbyname_ex is not None:
            socket.gethostbyname_ex = self._orig_gethostbyname_ex  # type: ignore[assignment]
        if self._orig_gethostbyaddr is not None:
            socket.gethostbyaddr = self._orig_gethostbyaddr  # type: ignore[assignment]
        socket.socket.sendto = self._orig_sendto  # type: ignore[method-assign]
        if self._orig_sendmsg is not None:
            socket.socket.sendmsg = self._orig_sendmsg  # type: ignore[method-assign]
        subprocess.run = self._orig_subprocess_run  # type: ignore[assignment]
        subprocess.Popen = self._orig_subprocess_popen  # type: ignore[misc,assignment]
        os.system = self._orig_os_system  # type: ignore[assignment]
        os.popen = self._orig_os_popen  # type: ignore[assignment]
        for route_name, original in self._orig_os_process_routes.items():
            setattr(os, route_name, original)
        multiprocessing.Process.start = self._orig_mp_process_start  # type: ignore[method-assign,assignment]
        for module, attr, original in self._module_patches:
            setattr(module, attr, original)
        self._module_patches.clear()


@contextmanager
def network_sentinel() -> Iterator[NetworkSentinel]:
    sentinel = NetworkSentinel()
    sentinel.install()
    try:
        yield sentinel
    finally:
        sentinel.restore()


# --------------------------------------------------------------------------- #
# Immutable raw-cache contract
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class CachePutResult:
    payload_sha256: str
    metadata_sha256: str


@dataclass(frozen=True)
class CacheHandle:
    """External trust anchor for an immutable cache entry (persist across restart)."""

    evidence_id: str
    payload_sha256: str
    metadata_sha256: str
    cache_contract_version: str
    schema_version: str = CACHE_HANDLE_SCHEMA_VERSION


def cache_handle_from_put_result(
    evidence_id: str, result: CachePutResult,
) -> CacheHandle:
    if type(evidence_id) is not str or not evidence_id.strip():
        raise ImmutableCacheError("evidence_id required for cache handle")
    if type(result) is not CachePutResult:
        raise ImmutableCacheError("CachePutResult required")
    if not SHA256_RE.match(result.payload_sha256 or ""):
        raise ImmutableCacheError("invalid payload_sha256 on handle")
    if not SHA256_RE.match(result.metadata_sha256 or ""):
        raise ImmutableCacheError("invalid metadata_sha256 on handle")
    return CacheHandle(
        evidence_id=evidence_id.strip(),
        payload_sha256=result.payload_sha256,
        metadata_sha256=result.metadata_sha256,
        cache_contract_version=CACHE_CONTRACT_VERSION,
        schema_version=CACHE_HANDLE_SCHEMA_VERSION,
    )


def serialize_cache_handle(handle: CacheHandle) -> str:
    """Canonical CSV serialization (header + one data row)."""
    if type(handle) is not CacheHandle:
        raise ImmutableCacheError("CacheHandle type check failed")
    require_valid_cache_handle(handle)
    return _csv_str(
        _CACHE_HANDLE_HEADER + ["cache_handle_schema_version"],
        [{
            "evidence_id": handle.evidence_id,
            "payload_sha256": handle.payload_sha256,
            "metadata_sha256": handle.metadata_sha256,
            "cache_contract_version": handle.cache_contract_version,
            "cache_handle_schema_version": handle.schema_version,
        }],
    )


def cache_handle_sha256(serialized: str) -> str:
    """External integrity digest over the exact serialized handle bytes."""
    if type(serialized) is not str:
        raise ImmutableCacheError("cache handle serialization must be str")
    return sha256_bytes(serialized.encode("utf-8"))


def require_valid_cache_handle(handle: CacheHandle) -> CacheHandle:
    if type(handle) is not CacheHandle:
        raise ImmutableCacheError("CacheHandle type check failed")
    if type(handle.evidence_id) is not str or not handle.evidence_id.strip():
        raise ImmutableCacheError("invalid evidence_id on handle")
    if not SHA256_RE.match(handle.payload_sha256 or ""):
        raise ImmutableCacheError("invalid payload_sha256 on handle")
    if not SHA256_RE.match(handle.metadata_sha256 or ""):
        raise ImmutableCacheError("invalid metadata_sha256 on handle")
    if handle.cache_contract_version != CACHE_CONTRACT_VERSION:
        raise ImmutableCacheError("cache_contract_version mismatch on handle")
    if handle.schema_version != CACHE_HANDLE_SCHEMA_VERSION:
        raise ImmutableCacheError("cache handle schema_version mismatch")
    return handle


def load_cache_handle(
    serialized: str,
    *,
    expected_handle_sha256: str,
) -> CacheHandle:
    """Fail-closed load requiring an external handle digest trust anchor.

    The digest must be supplied by the caller from outside the mutable
    serialized row; a hash stored only inside that row is never trusted.
    """
    if type(serialized) is not str or not serialized.strip():
        raise ImmutableCacheError("empty cache handle serialization")
    if type(expected_handle_sha256) is not str or not SHA256_RE.match(
        expected_handle_sha256 or "",
    ):
        raise ImmutableCacheError("expected_handle_sha256 required")
    actual = cache_handle_sha256(serialized)
    if actual != expected_handle_sha256:
        raise ImmutableCacheError("cache handle integrity check failed")
    rows = list(csv.DictReader(io.StringIO(serialized)))
    if len(rows) != 1:
        raise ImmutableCacheError("cache handle must contain exactly one row")
    row = rows[0]
    expected_cols = set(_CACHE_HANDLE_HEADER + ["cache_handle_schema_version"])
    if set(row.keys()) != expected_cols:
        raise ImmutableCacheError("cache handle columns mismatch")
    handle = CacheHandle(
        evidence_id=str(row["evidence_id"]),
        payload_sha256=str(row["payload_sha256"]).strip().lower(),
        metadata_sha256=str(row["metadata_sha256"]).strip().lower(),
        cache_contract_version=str(row["cache_contract_version"]),
        schema_version=str(row["cache_handle_schema_version"]),
    )
    return require_valid_cache_handle(handle)


def build_cache_handle_template_csv() -> str:
    """Zero-row header-only template; no real cache handles in Part 3B.0."""
    return _csv_str(_CACHE_HANDLE_HEADER + ["cache_handle_schema_version"], [])


class ImmutableCache:
    """Content-addressed, write-once immutable cache with atomic entry commit."""

    _PAYLOAD_NAME = "payload.bin"
    _META_NAME = "metadata.json"
    _META_HASH_NAME = "metadata.sha256"
    _ENTRY_FILES = frozenset({_PAYLOAD_NAME, _META_NAME, _META_HASH_NAME})

    def __init__(self, root: Path) -> None:
        raw = Path(root)
        lexical_root = self._lexical_absolute(raw)
        self._assert_lexical_no_symlinks(lexical_root, through_existing_only=True)
        # Root directory itself must not be a symlink.
        if self._is_symlink(lexical_root):
            raise ImmutableCacheError("symlink components rejected")
        lexical_root.mkdir(parents=True, exist_ok=True)
        self.root = lexical_root

    @staticmethod
    def _lexical_absolute(path: Path) -> Path:
        """Absolutize/normalize without following symlinks (abspath+normpath)."""
        return Path(os.path.normpath(os.path.abspath(os.fspath(path))))

    @staticmethod
    def _is_symlink(path: Path) -> bool:
        try:
            return stat.S_ISLNK(os.lstat(path).st_mode)
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise ImmutableCacheError("symlink lstat failed") from exc

    def _assert_lexical_no_symlinks(
        self, path: Path, *, through_existing_only: bool = False,
    ) -> None:
        """Inspect every lexical component with lstat (never resolve through links)."""
        lexical = self._lexical_absolute(path)
        root = getattr(self, "root", None)
        if root is not None:
            root_s = str(root)
            lex_s = str(lexical)
            if lex_s != root_s and not lex_s.startswith(root_s + os.sep):
                raise ImmutableCacheError("path traversal rejected")
        accum: Path | None = None
        for index, part in enumerate(lexical.parts):
            accum = Path(part) if accum is None else accum / part
            try:
                mode = os.lstat(accum).st_mode
            except FileNotFoundError:
                if through_existing_only:
                    break
                continue
            except OSError as exc:
                raise ImmutableCacheError("symlink lstat failed") from exc
            if stat.S_ISLNK(mode):
                raise ImmutableCacheError("symlink components rejected")
            del index  # unused; loop is for side-effect checks

    def _entry_dir(self, content_hash: str) -> Path:
        if not SHA256_RE.match(content_hash):
            raise ImmutableCacheError(f"invalid content hash: {content_hash}")
        target = self.root / content_hash[:2] / content_hash
        self._assert_lexical_no_symlinks(target)
        return target

    def _canonical_metadata_bytes(
        self,
        content_hash: str,
        metadata: dict[str, Any] | None,
        *,
        evidence_id: str | None = None,
    ) -> bytes:
        meta = dict(metadata or {})
        meta["content_sha256"] = content_hash
        meta.pop("metadata_sha256", None)
        if evidence_id is not None:
            if type(evidence_id) is not str or not evidence_id.strip():
                raise ImmutableCacheError("evidence_id required for bound metadata")
            meta["evidence_id"] = evidence_id.strip()
        elif "evidence_id" in meta:
            eid = meta["evidence_id"]
            if type(eid) is not str or not eid.strip():
                raise ImmutableCacheError("evidence_id in metadata must be non-empty str")
            meta["evidence_id"] = eid.strip()
        return json.dumps(
            meta, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        ).encode("utf-8")

    def _read_file_nofollow(self, path: Path) -> bytes:
        self._assert_lexical_no_symlinks(path)
        if self._is_symlink(path):
            raise ImmutableCacheError("symlink components rejected")
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(path, flags)
        except OSError as exc:
            raise ImmutableCacheError("failed to open cache file") from exc
        try:
            chunks: list[bytes] = []
            while True:
                chunk = os.read(fd, 65536)
                if not chunk:
                    break
                chunks.append(chunk)
            return b"".join(chunks)
        finally:
            os.close(fd)

    def _read_complete_entry(self, entry_dir: Path) -> tuple[bytes, bytes, str]:
        self._assert_lexical_no_symlinks(entry_dir)
        if self._is_symlink(entry_dir) or not entry_dir.is_dir():
            raise ImmutableCacheError("unknown hash or incomplete entry")
        names = {p.name for p in entry_dir.iterdir()}
        if names != self._ENTRY_FILES:
            raise ImmutableCacheError(
                "entry must contain exactly payload, metadata, and metadata hash"
            )
        for name in self._ENTRY_FILES:
            path = entry_dir / name
            if self._is_symlink(path) or not path.is_file():
                raise ImmutableCacheError("symlink or non-file entry component")
        payload = self._read_file_nofollow(entry_dir / self._PAYLOAD_NAME)
        meta_bytes = self._read_file_nofollow(entry_dir / self._META_NAME)
        meta_hash_text = self._read_file_nofollow(
            entry_dir / self._META_HASH_NAME,
        ).decode("utf-8").strip()
        return payload, meta_bytes, meta_hash_text

    def _entry_matches(
        self,
        entry_dir: Path,
        data: bytes,
        meta_bytes: bytes,
        meta_hash: str,
    ) -> bool:
        try:
            payload, existing_meta, existing_hash = self._read_complete_entry(entry_dir)
        except ImmutableCacheError:
            return False
        return (
            payload == data
            and existing_meta == meta_bytes
            and existing_hash == meta_hash
        )

    def _staging_orphans(self, parent: Path, content_hash: str) -> list[Path]:
        """Scan parent for staging dirs matching put() naming convention."""
        prefix = f".staging-{content_hash[:16]}-"
        orphans: list[Path] = []
        if not parent.is_dir() or self._is_symlink(parent):
            return orphans
        for p in parent.iterdir():
            if p.name.startswith(prefix) and _STAGING_NAME_RE.match(p.name):
                orphans.append(p)
        return orphans

    def put(
        self,
        data: bytes,
        metadata: dict[str, Any] | None = None,
        *,
        evidence_id: str | None = None,
        _inject_failure: str | None = None,
    ) -> CachePutResult:
        content_hash = sha256_bytes(data)
        entry_dir = self._entry_dir(content_hash)
        meta_bytes = self._canonical_metadata_bytes(
            content_hash, metadata, evidence_id=evidence_id,
        )
        meta_hash = sha256_bytes(meta_bytes)
        result = CachePutResult(
            payload_sha256=content_hash, metadata_sha256=meta_hash,
        )

        if entry_dir.exists():
            if self._entry_matches(entry_dir, data, meta_bytes, meta_hash):
                return result
            raise ImmutableCacheError(
                f"immutable entry conflict for {content_hash}"
            )

        parent = entry_dir.parent
        parent.mkdir(parents=True, exist_ok=True)
        self._assert_lexical_no_symlinks(parent)
        staging = parent / f".staging-{content_hash[:16]}-{uuid.uuid4().hex}"
        try:
            staging.mkdir(mode=0o755)
            if _inject_failure == "before_write":
                raise ImmutableCacheError("injected failure before_write")
            (staging / self._PAYLOAD_NAME).write_bytes(data)
            if _inject_failure == "after_payload":
                raise ImmutableCacheError("injected failure after_payload")
            (staging / self._META_NAME).write_bytes(meta_bytes)
            (staging / self._META_HASH_NAME).write_text(
                meta_hash + "\n", encoding="utf-8",
            )
            if _inject_failure == "before_commit":
                raise ImmutableCacheError("injected failure before_commit")
            try:
                os.rename(staging, entry_dir)
            except OSError as exc:
                if entry_dir.exists() and self._entry_matches(
                    entry_dir, data, meta_bytes, meta_hash,
                ):
                    if staging.exists():
                        shutil.rmtree(staging, ignore_errors=True)
                    return result
                raise ImmutableCacheError(
                    f"atomic commit failed for {content_hash}"
                ) from exc
        except Exception:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
            raise
        return result

    def get(self, content_hash: str, expected_metadata_sha256: str) -> bytes:
        if not SHA256_RE.match(expected_metadata_sha256 or ""):
            raise ImmutableCacheError("expected metadata sha256 required")
        entry_dir = self._entry_dir(content_hash)
        parent = entry_dir.parent
        orphans = self._staging_orphans(parent, content_hash)
        if orphans:
            raise ImmutableCacheError("orphan/partial staging entry present")
        if not entry_dir.exists():
            raise ImmutableCacheError(
                f"unknown hash or missing payload/metadata: {content_hash}"
            )
        # Reject duplicate artifacts beside the complete entry.
        if parent.is_dir():
            extras = [
                p for p in parent.iterdir()
                if p.name != content_hash
                and (
                    p.name.startswith(content_hash)
                    or _STAGING_NAME_RE.match(p.name)
                )
            ]
            if extras:
                raise ImmutableCacheError("duplicate or partial entry artifacts")

        payload, meta_bytes, meta_hash_text = self._read_complete_entry(entry_dir)
        if sha256_bytes(payload) != content_hash:
            raise ImmutableCacheError(f"payload hash mismatch for {content_hash}")
        actual_meta_hash = sha256_bytes(meta_bytes)
        if actual_meta_hash != expected_metadata_sha256:
            raise ImmutableCacheError(
                f"metadata hash mismatch for {content_hash}"
            )
        if meta_hash_text != expected_metadata_sha256:
            raise ImmutableCacheError(
                f"metadata hash mismatch for {content_hash}"
            )
        try:
            meta = json.loads(meta_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ImmutableCacheError("malformed metadata JSON") from exc
        if not isinstance(meta, dict):
            raise ImmutableCacheError("malformed metadata JSON")
        if meta.get("content_sha256") != content_hash:
            raise ImmutableCacheError(
                f"metadata/payload hash linkage failed for {content_hash}"
            )
        return payload

    def get_by_handle(self, handle: CacheHandle) -> bytes:
        """Secure get requires the persisted external CacheHandle trust anchor.

        Verifies payload/metadata hashes and that ``handle.evidence_id`` matches
        the ``evidence_id`` bound into canonical cached metadata.
        """
        handle = require_valid_cache_handle(handle)
        payload = self.get(handle.payload_sha256, handle.metadata_sha256)
        entry_dir = self._entry_dir(handle.payload_sha256)
        _payload, meta_bytes, _meta_hash = self._read_complete_entry(entry_dir)
        del _payload, _meta_hash
        try:
            meta = json.loads(meta_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ImmutableCacheError("malformed metadata JSON") from exc
        if not isinstance(meta, dict):
            raise ImmutableCacheError("malformed metadata JSON")
        cached_eid = meta.get("evidence_id")
        if type(cached_eid) is not str or not cached_eid.strip():
            raise ImmutableCacheError("cached metadata missing bound evidence_id")
        if cached_eid.strip() != handle.evidence_id:
            raise ImmutableCacheError(
                "evidence_id mismatch between handle and cached metadata"
            )
        return payload

    def has(self, content_hash: str, expected_metadata_sha256: str) -> bool:
        try:
            self.get(content_hash, expected_metadata_sha256)
        except ImmutableCacheError:
            return False
        return True

    def entry_count(self) -> int:
        """Count structurally complete entries (external seal checked on get)."""
        count = 0
        if not self.root.is_dir() or self._is_symlink(self.root):
            return 0
        for shard in self.root.iterdir():
            if self._is_symlink(shard) or not shard.is_dir():
                continue
            for entry in shard.iterdir():
                if self._is_symlink(entry) or not entry.is_dir():
                    continue
                if entry.name.startswith(".staging-"):
                    continue
                try:
                    names = {p.name for p in entry.iterdir()}
                except OSError:
                    continue
                if names == self._ENTRY_FILES:
                    count += 1
        return count


# --------------------------------------------------------------------------- #
# Evidence schema validator
# --------------------------------------------------------------------------- #

def _is_null(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def _contains_guessed_marker(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    low = value.strip().lower()
    return any(marker in low for marker in GUESSED_MARKERS)


def _parse_datetime_semantic(name: str, value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise EvidenceValidationError(f"{name}: invalid datetime") from exc
    # Reject regex-plausible but semantically impossible dates that fromisoformat
    # might not catch on all platforms; also reject non-finite-like garbage.
    if dt.year < 1 or dt.month < 1 or dt.month > 12 or dt.day < 1 or dt.day > 31:
        raise EvidenceValidationError(f"{name}: invalid datetime")
    return dt


def _validate_datetime_field(name: str, value: Any, *, require_utc: bool) -> None:
    if _is_null(value):
        return
    if not isinstance(value, str):
        raise EvidenceValidationError(f"{name}: wrong type")
    if _contains_guessed_marker(value):
        raise EvidenceValidationError(f"{name}: guessed/inferred marker")
    dt = _parse_datetime_semantic(name, value)
    if require_utc:
        if dt.tzinfo is None:
            raise EvidenceValidationError(f"{name}: must be timezone-aware UTC")
        if dt.utcoffset() != timezone.utc.utcoffset(dt):
            raise EvidenceValidationError(f"{name}: must be timezone-aware UTC")


def _validate_sha256_field(name: str, value: Any) -> None:
    if _is_null(value):
        return
    if not isinstance(value, str) or not SHA256_RE.match(value.strip().lower()):
        raise EvidenceValidationError(f"{name}: invalid SHA-256")


def _reject_non_finite(name: str, value: Any) -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise EvidenceValidationError(f"{name}: non-finite number")


def _validate_synthetic_markers(
    record: dict[str, Any],
    *,
    allowed_snapshot_root: Path | None,
) -> None:
    evidence_id = record.get("evidence_id")
    if not isinstance(evidence_id, str) or not evidence_id.startswith(
        SYNTHETIC_EVIDENCE_ID_PREFIX
    ):
        raise EvidenceValidationError(
            "synthetic evidence_id prefix required"
        )
    access_method = record.get("access_method")
    if access_method != SYNTHETIC_ACCESS_METHOD:
        raise EvidenceValidationError(
            "access_method must be synthetic_fixture for Part 3B.0"
        )
    source_url = record.get("source_url")
    if not _is_null(source_url):
        if not isinstance(source_url, str):
            raise EvidenceValidationError("source_url: wrong type")
        parsed = urlparse(source_url)
        host = (parsed.hostname or "").lower()
        if not host.endswith(SYNTHETIC_INVALID_DOMAIN):
            raise EvidenceValidationError(
                "source_url must be null or under the reserved .invalid domain"
            )
    snap = record.get("local_snapshot_path")
    if not _is_null(snap):
        if not isinstance(snap, str):
            raise EvidenceValidationError("local_snapshot_path: wrong type")
        if "project/stage125" in snap.replace("\\", "/") or "raw_cache" in snap:
            raise EvidenceValidationError(
                "snapshot path must not target repository evidence/cache paths"
            )
        if allowed_snapshot_root is None:
            raise EvidenceValidationError(
                "snapshot path requires allowed_snapshot_root (pytest tmp_path)"
            )


def _lexical_absolute_path(path: Path) -> Path:
    return Path(os.path.normpath(os.path.abspath(os.fspath(path))))


def _path_is_symlink(path: Path) -> bool:
    try:
        return stat.S_ISLNK(os.lstat(path).st_mode)
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise EvidenceValidationError("snapshot lstat failed") from exc


def _assert_snapshot_no_symlinks(path: Path) -> None:
    lexical = _lexical_absolute_path(path)
    accum: Path | None = None
    for part in lexical.parts:
        accum = Path(part) if accum is None else accum / part
        try:
            mode = os.lstat(accum).st_mode
        except FileNotFoundError:
            raise EvidenceValidationError("snapshot missing or unreadable")
        except OSError as exc:
            raise EvidenceValidationError("snapshot lstat failed") from exc
        if stat.S_ISLNK(mode):
            raise EvidenceValidationError("snapshot symlink rejected")


def _read_snapshot_bytes_nofollow(path: Path) -> bytes:
    _assert_snapshot_no_symlinks(path)
    if _path_is_symlink(path):
        raise EvidenceValidationError("snapshot symlink rejected")
    try:
        mode = os.lstat(path).st_mode
    except OSError as exc:
        raise EvidenceValidationError("snapshot missing or unreadable") from exc
    if not stat.S_ISREG(mode):
        raise EvidenceValidationError("snapshot must be a regular file")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise EvidenceValidationError("snapshot missing or unreadable") from exc
    try:
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _verify_snapshot_bytes_match_hash(
    record: dict[str, Any],
    *,
    allowed_snapshot_root: Path,
) -> None:
    """When local_snapshot_path is set: exist, regular file, no symlinks, hash match."""
    snap = record.get("local_snapshot_path")
    expected = record.get("snapshot_sha256")
    if _is_null(snap):
        return
    if not isinstance(snap, str) or not isinstance(expected, str):
        raise EvidenceValidationError("snapshot path/hash type invalid")
    if not SHA256_RE.match(expected.strip().lower()):
        raise EvidenceValidationError("snapshot_sha256: invalid SHA-256")
    root = _lexical_absolute_path(Path(allowed_snapshot_root))
    if _path_is_symlink(root):
        raise EvidenceValidationError("snapshot root symlink rejected")
    candidate = Path(snap)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = _lexical_absolute_path(candidate)
    root_s = str(root)
    cand_s = str(candidate)
    if cand_s != root_s and not cand_s.startswith(root_s + os.sep):
        raise EvidenceValidationError(
            "snapshot path must be confined to allowed_snapshot_root"
        )
    _assert_snapshot_no_symlinks(candidate)
    actual = sha256_bytes(_read_snapshot_bytes_nofollow(candidate))
    if actual != expected.strip().lower():
        raise EvidenceValidationError("snapshot_sha256 does not match file bytes")


def _validate_evidence_record_core(
    record: dict[str, Any],
    *,
    schema: dict,
    candidate_source_map: dict[str, str],
    source_registry: dict[str, dict],
) -> None:
    """Private core validator shared by the synthetic-only public entry point."""
    if schema.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
        raise EvidenceValidationError("unsupported schema version")
    required = schema.get("required_fields", [])
    allowed_names = {f["name"] for f in required}
    unknown = set(record) - allowed_names
    if unknown:
        raise EvidenceValidationError(f"unknown fields: {sorted(unknown)}")

    snap_path = record.get("local_snapshot_path")
    snap_hash = record.get("snapshot_sha256")
    snap_path_present = not _is_null(snap_path)
    snap_hash_present = not _is_null(snap_hash)
    if snap_path_present != snap_hash_present:
        raise EvidenceValidationError(
            "local_snapshot_path and snapshot_sha256 must be co-present"
        )

    for field in required:
        name = field["name"]
        nullable = field.get("nullable", True)
        ftype = field.get("type")
        # Every schema field must be present; nullable allows explicit null/empty.
        if name not in record:
            raise EvidenceValidationError(
                f"missing field (omission not allowed): {name}"
            )
        value = record.get(name)
        if not nullable and _is_null(value):
            raise EvidenceValidationError(f"missing non-nullable field: {name}")
        if _is_null(value):
            continue
        _reject_non_finite(name, value)
        if ftype == "string":
            if not isinstance(value, str):
                raise EvidenceValidationError(f"{name}: wrong type")
        elif ftype == "boolean":
            if not isinstance(value, bool):
                raise EvidenceValidationError(f"{name}: wrong type")
        elif ftype == "datetime":
            _validate_datetime_field(
                name, value, require_utc=(name == "retrieved_at_utc"),
            )
        else:
            raise EvidenceValidationError(f"{name}: unsupported field type")
        if name == "snapshot_sha256":
            _validate_sha256_field(name, value)
        if name == "calendar" and str(value).strip().lower() not in ALLOWED_CALENDARS:
            raise EvidenceValidationError(f"{name}: invalid calendar")
        if name == "timezone" and str(value).strip() not in ALLOWED_TIMEZONES:
            raise EvidenceValidationError(f"{name}: invalid timezone")
        if isinstance(value, str) and _contains_guessed_marker(value):
            raise EvidenceValidationError(f"{name}: guessed/inferred marker")

    candidate_id = record.get("candidate_id")
    source_id = record.get("source_id")
    out_of_scope_ids = {
        c["candidate_id"] for c in part3a.OUT_OF_SCOPE_LOCKED
    } | {c["candidate_id"] for c in part3a.RESEARCH_DESIGN_ONLY}
    if candidate_id in out_of_scope_ids:
        raise EvidenceValidationError(
            f"out-of-scope or narrative-only candidate: {candidate_id}"
        )
    if candidate_id not in candidate_source_map:
        raise EvidenceValidationError(f"unknown candidate_id: {candidate_id}")
    if source_id not in source_registry:
        raise EvidenceValidationError(f"unknown source_id: {source_id}")
    if candidate_source_map[candidate_id] != source_id:
        raise EvidenceValidationError("candidate/source mapping mismatch")
    source_owner = record.get("source_owner")
    if not _is_null(source_owner):
        expected_owner = source_registry[source_id].get("source_owner", "")
        if str(source_owner).strip() != str(expected_owner).strip():
            raise EvidenceValidationError(
                "source_owner does not match source_registry"
            )


@dataclass(frozen=True)
class ValidatedSyntheticEvidence:
    """Sealed synthetic evidence produced only after full fail-closed validation."""

    evidence_id: str
    candidate_id: str
    source_id: str
    published_at: str | None
    available_at: str | None
    retrieved_at_utc: str
    local_snapshot_path: str | None
    snapshot_sha256: str | None
    _seal: str = field(repr=False, compare=True)


@dataclass(frozen=True)
class ValidatedGateInput:
    """Strictly typed Gate inputs derived from sealed synthetic evidence."""

    evidence: ValidatedSyntheticEvidence
    accessibility_score: int | None
    authoritative_source: bool | None
    reproducible_retrieval: bool | None
    quality_controls_met: bool | None
    prediction_cutoff: str
    _seal: str = field(repr=False, compare=True)


_EVIDENCE_SEAL_DOMAIN = "stage125_part3b0_validated_synthetic_evidence_v1"
_GATE_INPUT_SEAL_DOMAIN = "stage125_part3b0_validated_gate_input_v1"


def _nullable_str(value: Any) -> str | None:
    if _is_null(value):
        return None
    if type(value) is not str:
        raise EvidenceValidationError("expected string or null")
    return value


def validate_and_seal_synthetic_evidence(
    record: dict[str, Any],
    *,
    schema: dict,
    candidate_source_map: dict[str, str],
    source_registry: dict[str, dict],
    allowed_snapshot_root: Path | None = None,
) -> ValidatedSyntheticEvidence:
    """Schema + registry + snapshot-byte validation; returns sealed evidence."""
    validate_evidence_record_synthetic(
        record,
        schema=schema,
        candidate_source_map=candidate_source_map,
        source_registry=source_registry,
        allowed_snapshot_root=allowed_snapshot_root,
    )
    evidence = ValidatedSyntheticEvidence(
        evidence_id=str(record["evidence_id"]),
        candidate_id=str(record["candidate_id"]),
        source_id=str(record["source_id"]),
        published_at=_nullable_str(record.get("published_at")),
        available_at=_nullable_str(record.get("available_at")),
        retrieved_at_utc=str(record["retrieved_at_utc"]),
        local_snapshot_path=_nullable_str(record.get("local_snapshot_path")),
        snapshot_sha256=(
            None
            if _is_null(record.get("snapshot_sha256"))
            else str(record["snapshot_sha256"]).strip().lower()
        ),
        _seal="",
    )
    seal = sha256_bytes(
        "|".join([
            _EVIDENCE_SEAL_DOMAIN,
            evidence.evidence_id,
            evidence.candidate_id,
            evidence.source_id,
            evidence.published_at or "",
            evidence.available_at or "",
            evidence.retrieved_at_utc,
            evidence.local_snapshot_path or "",
            evidence.snapshot_sha256 or "",
        ]).encode("utf-8")
    )
    sealed = ValidatedSyntheticEvidence(
        evidence_id=evidence.evidence_id,
        candidate_id=evidence.candidate_id,
        source_id=evidence.source_id,
        published_at=evidence.published_at,
        available_at=evidence.available_at,
        retrieved_at_utc=evidence.retrieved_at_utc,
        local_snapshot_path=evidence.local_snapshot_path,
        snapshot_sha256=evidence.snapshot_sha256,
        _seal=seal,
    )
    return require_sealed_synthetic_evidence(sealed)


def require_sealed_synthetic_evidence(
    evidence: ValidatedSyntheticEvidence,
) -> ValidatedSyntheticEvidence:
    if type(evidence) is not ValidatedSyntheticEvidence:
        raise QCFail("ValidatedSyntheticEvidence type check failed")
    expected = sha256_bytes(
        "|".join([
            _EVIDENCE_SEAL_DOMAIN,
            evidence.evidence_id,
            evidence.candidate_id,
            evidence.source_id,
            evidence.published_at or "",
            evidence.available_at or "",
            evidence.retrieved_at_utc,
            evidence.local_snapshot_path or "",
            evidence.snapshot_sha256 or "",
        ]).encode("utf-8")
    )
    if evidence._seal != expected:
        raise QCFail("ValidatedSyntheticEvidence seal verification failed")
    return evidence


def build_validated_gate_input(
    evidence: ValidatedSyntheticEvidence,
    *,
    prediction_cutoff: str,
    accessibility_score: int | None = None,
    authoritative_source: bool | None = None,
    reproducible_retrieval: bool | None = None,
    quality_controls_met: bool | None = None,
) -> ValidatedGateInput:
    """Build sealed Gate input; rejects truthiness coercion and untyped values."""
    evidence = require_sealed_synthetic_evidence(evidence)
    if accessibility_score is not None and type(accessibility_score) is not int:
        raise QCFail("accessibility_score must be int or None")
    for name, value in (
        ("authoritative_source", authoritative_source),
        ("reproducible_retrieval", reproducible_retrieval),
        ("quality_controls_met", quality_controls_met),
    ):
        if value is not None and type(value) is not bool:
            raise QCFail(f"{name} must be bool or None (no truthiness coercion)")
    if type(prediction_cutoff) is not str or _is_null(prediction_cutoff):
        raise QCFail("prediction_cutoff must be a non-empty validated datetime string")
    try:
        _parse_datetime_semantic("prediction_cutoff", prediction_cutoff)
    except EvidenceValidationError as exc:
        raise QCFail("prediction_cutoff invalid datetime") from exc
    if evidence.available_at is not None:
        try:
            _parse_datetime_semantic("available_at", evidence.available_at)
        except EvidenceValidationError as exc:
            raise QCFail("evidence.available_at invalid") from exc
    seal = sha256_bytes(
        "|".join([
            _GATE_INPUT_SEAL_DOMAIN,
            evidence._seal,
            "" if accessibility_score is None else str(accessibility_score),
            "" if authoritative_source is None else (
                "1" if authoritative_source else "0"
            ),
            "" if reproducible_retrieval is None else (
                "1" if reproducible_retrieval else "0"
            ),
            "" if quality_controls_met is None else (
                "1" if quality_controls_met else "0"
            ),
            prediction_cutoff,
        ]).encode("utf-8")
    )
    sealed = ValidatedGateInput(
        evidence=evidence,
        accessibility_score=accessibility_score,
        authoritative_source=authoritative_source,
        reproducible_retrieval=reproducible_retrieval,
        quality_controls_met=quality_controls_met,
        prediction_cutoff=prediction_cutoff,
        _seal=seal,
    )
    return require_sealed_gate_input(sealed)


def require_sealed_gate_input(gate_input: ValidatedGateInput) -> ValidatedGateInput:
    if type(gate_input) is not ValidatedGateInput:
        raise QCFail("ValidatedGateInput type check failed")
    require_sealed_synthetic_evidence(gate_input.evidence)
    expected = sha256_bytes(
        "|".join([
            _GATE_INPUT_SEAL_DOMAIN,
            gate_input.evidence._seal,
            (
                ""
                if gate_input.accessibility_score is None
                else str(gate_input.accessibility_score)
            ),
            "" if gate_input.authoritative_source is None else (
                "1" if gate_input.authoritative_source else "0"
            ),
            "" if gate_input.reproducible_retrieval is None else (
                "1" if gate_input.reproducible_retrieval else "0"
            ),
            "" if gate_input.quality_controls_met is None else (
                "1" if gate_input.quality_controls_met else "0"
            ),
            gate_input.prediction_cutoff,
        ]).encode("utf-8")
    )
    if gate_input._seal != expected:
        raise QCFail("ValidatedGateInput seal verification failed")
    return gate_input


def validate_evidence_record_synthetic(
    record: dict[str, Any],
    *,
    schema: dict,
    candidate_source_map: dict[str, str],
    source_registry: dict[str, dict],
    allowed_snapshot_root: Path | None = None,
) -> None:
    """Only usable Part 3B.0 entry point: synthetic fixtures with verifiable markers."""
    _validate_synthetic_markers(
        record, allowed_snapshot_root=allowed_snapshot_root,
    )
    _validate_evidence_record_core(
        record,
        schema=schema,
        candidate_source_map=candidate_source_map,
        source_registry=source_registry,
    )
    if not _is_null(record.get("local_snapshot_path")):
        if allowed_snapshot_root is None:
            raise EvidenceValidationError(
                "snapshot path requires allowed_snapshot_root (pytest tmp_path)"
            )
        _verify_snapshot_bytes_match_hash(
            record, allowed_snapshot_root=Path(allowed_snapshot_root),
        )


def validate_evidence_manifest_synthetic(
    records: list[dict[str, Any]],
    *,
    schema: dict,
    candidate_source_map: dict[str, str],
    source_registry: dict[str, dict],
    allowed_snapshot_root: Path | None = None,
) -> None:
    """Manifest-level synthetic validation including unique evidence_id."""
    ids = []
    for record in records:
        validate_evidence_record_synthetic(
            record,
            schema=schema,
            candidate_source_map=candidate_source_map,
            source_registry=source_registry,
            allowed_snapshot_root=allowed_snapshot_root,
        )
        ids.append(record.get("evidence_id"))
    if len(ids) != len(set(ids)):
        raise EvidenceValidationError("duplicate evidence_id in manifest")


# --------------------------------------------------------------------------- #
# Pure Gate engine
# --------------------------------------------------------------------------- #

def evaluate_g01(accessibility_score: Any) -> str:
    if accessibility_score is None:
        return GATE_UNRESOLVED
    if type(accessibility_score) is not int:
        return GATE_FAIL
    if accessibility_score < 0 or accessibility_score > 5:
        return GATE_FAIL
    if accessibility_score <= 2:
        return GATE_FAIL
    return GATE_PASS


def evaluate_g02(authoritative_source: Any) -> str:
    if authoritative_source is None:
        return GATE_UNRESOLVED
    if type(authoritative_source) is not bool:
        return GATE_FAIL
    return GATE_PASS if authoritative_source else GATE_FAIL


def evaluate_g03(reproducible_retrieval: Any) -> str:
    if reproducible_retrieval is None:
        return GATE_UNRESOLVED
    if type(reproducible_retrieval) is not bool:
        return GATE_FAIL
    return GATE_PASS if reproducible_retrieval else GATE_FAIL


def _gate_datetime_ok(name: str, value: Any) -> bool:
    if _is_null(value):
        return True
    if type(value) is not str:
        return False
    try:
        _parse_datetime_semantic(name, value)
    except EvidenceValidationError:
        return False
    return True


def evaluate_g04(
    published_at: str | None, available_at: str | None,
) -> str:
    if _is_null(published_at) and _is_null(available_at):
        return GATE_UNRESOLVED
    if not _gate_datetime_ok("published_at", published_at):
        return GATE_FAIL
    if not _gate_datetime_ok("available_at", available_at):
        return GATE_FAIL
    if not _is_null(published_at) or not _is_null(available_at):
        return GATE_PASS
    return GATE_UNRESOLVED


def evaluate_g05(quality_controls_met: Any) -> str:
    if quality_controls_met is None:
        return GATE_UNRESOLVED
    if type(quality_controls_met) is not bool:
        return GATE_FAIL
    return GATE_PASS if quality_controls_met else GATE_FAIL


def evaluate_g06(available_at: str | None) -> str:
    if _is_null(available_at):
        return GATE_UNRESOLVED
    if not _gate_datetime_ok("available_at", available_at):
        return GATE_FAIL
    return GATE_PASS


def evaluate_g07_from_cutoff(
    available_at: str | None, prediction_cutoff: str | None,
) -> str:
    """G07 derived from validated available_at vs prediction cutoff (not a bool flag)."""
    if _is_null(available_at) or _is_null(prediction_cutoff):
        return GATE_UNRESOLVED
    if type(available_at) is not str or type(prediction_cutoff) is not str:
        return GATE_FAIL
    try:
        avail = _parse_datetime_semantic("available_at", available_at)
        cutoff = _parse_datetime_semantic("prediction_cutoff", prediction_cutoff)
    except EvidenceValidationError:
        return GATE_FAIL
    if avail.tzinfo is None or cutoff.tzinfo is None:
        # Compare naive/aware consistently by requiring both parseable; treat
        # missing tz as fail-closed for leakage decisions.
        return GATE_FAIL
    return GATE_PASS if avail <= cutoff else GATE_FAIL


def evaluate_g07(no_future_leakage: Any) -> str:
    """Legacy boolean form — not accepted by evaluate_candidate_gates."""
    if no_future_leakage is None:
        return GATE_UNRESOLVED
    if type(no_future_leakage) is not bool:
        return GATE_FAIL
    return GATE_PASS if no_future_leakage else GATE_FAIL


def evaluate_g08(gate_statuses: dict[str, str]) -> str:
    if type(gate_statuses) is not dict:
        return GATE_FAIL
    if set(gate_statuses.keys()) != set(G01_G07):
        return GATE_FAIL
    for status in gate_statuses.values():
        if type(status) is not str or status not in ALLOWED_GATE_STATUSES:
            return GATE_FAIL
    if any(s == GATE_FAIL for s in gate_statuses.values()):
        return GATE_FAIL
    if any(s == GATE_UNRESOLVED for s in gate_statuses.values()):
        return GATE_UNRESOLVED
    if any(s == GATE_NOT_APPLIED for s in gate_statuses.values()):
        return GATE_FAIL
    return GATE_PASS


def _require_usable_key_map(
    usable_by_candidate: Any, pilot_keys: frozenset[str],
) -> dict[str, set[str]]:
    if type(usable_by_candidate) is not dict:
        raise QCFail("usable_by_candidate must be a dict")
    out: dict[str, set[str]] = {}
    for cand_id, usable in usable_by_candidate.items():
        if type(cand_id) is not str:
            raise QCFail("usable_by_candidate keys must be str")
        if type(usable) not in (set, frozenset):
            raise QCFail("usable_by_candidate values must be set/frozenset")
        if any(type(k) is not str for k in usable):
            raise QCFail("usable keys must be str")
        out[cand_id] = set(usable)
    return out


def evaluate_g09(
    usable_by_candidate: dict[str, set[str]],
    pilot_keys: set[str] | frozenset[str] | list[str],
    policy: LockedGatePolicy,
) -> str:
    policy = require_sealed_gate_policy(policy)
    keys = require_frozen_pilot_key_identity(policy, pilot_keys)
    usable_map = _require_usable_key_map(usable_by_candidate, keys)
    registered = [c["candidate_id"] for c in part3a.REGISTERED_CANDIDATES]
    if len(registered) != 10:
        return GATE_FAIL
    for cand_id in registered:
        usable = usable_map.get(cand_id, set())
        coverage = len(usable & keys) / len(keys)
        if coverage < policy.g09_threshold:
            return GATE_FAIL
    return GATE_PASS


def evaluate_g10(
    usable_by_pair_block: dict[str, dict[str, bool]],
    pilot_keys: set[str] | frozenset[str] | list[str],
    policy: LockedGatePolicy,
) -> str:
    policy = require_sealed_gate_policy(policy)
    keys = require_frozen_pilot_key_identity(policy, pilot_keys)
    if type(usable_by_pair_block) is not dict:
        raise QCFail("usable_by_pair_block must be a dict")
    for key, cand_flags in usable_by_pair_block.items():
        if type(key) is not str or type(cand_flags) is not dict:
            raise QCFail("usable_by_pair_block map types invalid")
        for cand_id, flag in cand_flags.items():
            if type(cand_id) is not str or type(flag) is not bool:
                raise QCFail("G10 usable flags must be exact bool")
    for block, candidates in BLOCK_CANDIDATES.items():
        if not candidates:
            return GATE_FAIL
        usable_pairs = {
            key for key in keys
            if all(
                usable_by_pair_block.get(key, {}).get(cand_id, False) is True
                for cand_id in candidates
            )
        }
        coverage = len(usable_pairs) / len(keys)
        if coverage < policy.g10_threshold:
            return GATE_FAIL
    return GATE_PASS


@dataclass(frozen=True)
class SealedClassBlockYearUsability:
    """Sealed G11/G12 aggregate derived only from per-pair block usability."""

    class_label: str
    counts_by_block_year: frozenset[tuple[str, str, int]]
    pair_records_sha256: str
    policy_seal: str
    _seal: str = field(repr=False, compare=True)


def _require_complete_pair_block_usability(
    usable_by_pair_block: Any,
    policy: LockedGatePolicy,
) -> dict[str, dict[str, bool]]:
    """Require exact frozen key set and exact-bool per-candidate usability."""
    policy = require_sealed_gate_policy(policy)
    if type(usable_by_pair_block) is list:
        keys_list: list[str] = []
        mapping: dict[str, dict[str, bool]] = {}
        for item in usable_by_pair_block:
            if (
                type(item) is not tuple
                or len(item) != 2
                or type(item[0]) is not str
                or type(item[1]) is not dict
            ):
                raise QCFail("pair block usability records must be (key, flags) tuples")
            keys_list.append(item[0])
            mapping[item[0]] = item[1]
        if len(keys_list) != len(set(keys_list)):
            raise QCFail("duplicate pilot keys in usability records")
        usable_by_pair_block = mapping
    if type(usable_by_pair_block) is not dict:
        raise QCFail("pair block usability must be a dict or list of records")
    supplied_keys = list(usable_by_pair_block.keys())
    if any(type(k) is not str for k in supplied_keys):
        raise QCFail("usability record keys must be str")
    if len(supplied_keys) != len(set(supplied_keys)):
        raise QCFail("duplicate pilot keys in usability records")
    supplied = frozenset(supplied_keys)
    if supplied != policy.frozen_pilot_keys:
        missing = policy.frozen_pilot_keys - supplied
        extra = supplied - policy.frozen_pilot_keys
        if missing and extra:
            raise QCFail("missing and extra pilot keys in usability records")
        if missing:
            raise QCFail("missing pilot keys in usability records")
        raise QCFail("extra pilot keys in usability records")
    registered = {
        c["candidate_id"] for c in part3a.REGISTERED_CANDIDATES
    }
    out: dict[str, dict[str, bool]] = {}
    for key, cand_flags in usable_by_pair_block.items():
        if type(cand_flags) is not dict:
            raise QCFail("usability flags must be a dict")
        if set(cand_flags.keys()) != registered:
            raise QCFail("usability flags must cover exact registered candidates")
        normalized: dict[str, bool] = {}
        for cand_id, flag in cand_flags.items():
            if type(cand_id) is not str or type(flag) is not bool:
                raise QCFail("G11/G12 usability values must be exact bool")
            normalized[cand_id] = flag
        out[key] = normalized
    return out


def _pair_block_usable(
    cand_flags: dict[str, bool], block: str,
) -> bool:
    candidates = BLOCK_CANDIDATES[block]
    return all(cand_flags.get(cand_id, False) is True for cand_id in candidates)


def _derive_class_block_year_counts(
    usable_by_pair_block: dict[str, dict[str, bool]],
    policy: LockedGatePolicy,
    class_label: str,
) -> dict[str, dict[str, int]]:
    label_by_key = {k: lab for k, lab in policy.frozen_pilot_key_labels}
    year_by_key = {k: y for k, y in policy.frozen_pilot_key_years}
    counts: dict[str, dict[str, int]] = {
        block: {year: 0 for year in policy.target_years}
        for block in BLOCK_CANDIDATES
    }
    for key, cand_flags in usable_by_pair_block.items():
        if label_by_key[key] != class_label:
            continue
        year = year_by_key[key]
        for block in BLOCK_CANDIDATES:
            if _pair_block_usable(cand_flags, block):
                counts[block][year] += 1
    return counts


def _pair_records_sha256(
    usable_by_pair_block: dict[str, dict[str, bool]],
) -> str:
    lines: list[str] = []
    for key in sorted(usable_by_pair_block):
        flags = usable_by_pair_block[key]
        flag_blob = ",".join(
            f"{cid}={1 if flags[cid] else 0}" for cid in sorted(flags)
        )
        lines.append(f"{key}|{flag_blob}")
    return sha256_bytes("\n".join(lines).encode("utf-8"))


def _compute_class_block_year_usability_seal(
    class_label: str,
    counts: frozenset[tuple[str, str, int]],
    pair_records_sha256: str,
    policy_seal: str,
) -> str:
    counts_blob = ",".join(
        f"{b}:{y}:{c}" for b, y, c in sorted(counts)
    )
    payload = "|".join([
        _CLASS_BLOCK_YEAR_USABILITY_SEAL_DOMAIN,
        class_label,
        counts_blob,
        pair_records_sha256,
        policy_seal,
    ])
    return sha256_bytes(payload.encode("utf-8"))


def build_sealed_class_block_year_usability(
    usable_by_pair_block: Any,
    policy: LockedGatePolicy,
    *,
    class_label: str,
) -> SealedClassBlockYearUsability:
    """Derive and seal G11/G12 aggregates from exact per-pair usability records."""
    policy = require_sealed_gate_policy(policy)
    if class_label not in ("positive", "negative"):
        raise QCFail("class_label must be positive or negative")
    records = _require_complete_pair_block_usability(usable_by_pair_block, policy)
    derived = _derive_class_block_year_counts(records, policy, class_label)
    counts = frozenset(
        (block, year, count)
        for block, years in derived.items()
        for year, count in years.items()
    )
    records_hash = _pair_records_sha256(records)
    seal = _compute_class_block_year_usability_seal(
        class_label, counts, records_hash, policy._seal,
    )
    return SealedClassBlockYearUsability(
        class_label=class_label,
        counts_by_block_year=counts,
        pair_records_sha256=records_hash,
        policy_seal=policy._seal,
        _seal=seal,
    )


def require_sealed_class_block_year_usability(
    sealed: SealedClassBlockYearUsability,
    policy: LockedGatePolicy,
    *,
    expected_label: str,
) -> SealedClassBlockYearUsability:
    policy = require_sealed_gate_policy(policy)
    if type(sealed) is not SealedClassBlockYearUsability:
        raise QCFail("SealedClassBlockYearUsability type check failed")
    if sealed.class_label != expected_label:
        raise QCFail("sealed usability class_label mismatch")
    if sealed.policy_seal != policy._seal:
        raise QCFail("sealed usability policy seal mismatch")
    if type(sealed.counts_by_block_year) is not frozenset:
        raise QCFail("sealed usability counts type invalid")
    expected = {
        (block, year) for block in BLOCK_CANDIDATES for year in policy.target_years
    }
    seen: set[tuple[str, str]] = set()
    for item in sealed.counts_by_block_year:
        if (
            type(item) is not tuple
            or len(item) != 3
            or type(item[0]) is not str
            or type(item[1]) is not str
            or type(item[2]) is not int
            or item[2] < 0
        ):
            raise QCFail("sealed usability count tuples invalid")
        seen.add((item[0], item[1]))
    if seen != expected:
        raise QCFail("sealed usability block/year coverage mismatch")
    if not SHA256_RE.match(sealed.pair_records_sha256 or ""):
        raise QCFail("sealed usability pair_records_sha256 invalid")
    expected_seal = _compute_class_block_year_usability_seal(
        sealed.class_label,
        sealed.counts_by_block_year,
        sealed.pair_records_sha256,
        sealed.policy_seal,
    )
    if sealed._seal != expected_seal:
        raise QCFail("SealedClassBlockYearUsability seal verification failed")
    return sealed


def _reject_raw_block_year_counts(data: Any, gate_id: str) -> None:
    """Fail closed if caller supplies independent block/year count dictionaries."""
    if type(data) is not dict or not data:
        return
    keys = set(data.keys())
    if keys and keys.issubset(set(BLOCK_CANDIDATES)):
        sample = next(iter(data.values()))
        if type(sample) is dict and sample and type(next(iter(sample.values()))) is int:
            raise QCFail(
                f"{gate_id} requires sealed usability or per-pair records; "
                "raw caller-supplied counts are rejected"
            )


def evaluate_g11(
    sealed_or_records: SealedClassBlockYearUsability | Any,
    policy: LockedGatePolicy,
) -> str:
    """G11 from sealed aggregate or exact per-pair usability records only."""
    policy = require_sealed_gate_policy(policy)
    if type(sealed_or_records) is SealedClassBlockYearUsability:
        sealed = sealed_or_records
    elif type(sealed_or_records) in (dict, list):
        _reject_raw_block_year_counts(sealed_or_records, "G11")
        sealed = build_sealed_class_block_year_usability(
            sealed_or_records, policy, class_label="positive",
        )
    else:
        raise QCFail(
            "G11 requires sealed usability or per-pair records; "
            "raw caller-supplied counts are rejected"
        )
    sealed = require_sealed_class_block_year_usability(
        sealed, policy, expected_label="positive",
    )
    count_map = {(b, y): c for b, y, c in sealed.counts_by_block_year}
    for block in BLOCK_CANDIDATES:
        for year in policy.target_years:
            count = count_map[(block, year)]
            if count < policy.g11_minimum:
                return GATE_FAIL
    return GATE_PASS


def evaluate_g12(
    sealed_or_records: SealedClassBlockYearUsability | Any,
    policy: LockedGatePolicy,
) -> str:
    """G12 from sealed aggregate or exact per-pair usability records only."""
    policy = require_sealed_gate_policy(policy)
    if type(sealed_or_records) is SealedClassBlockYearUsability:
        sealed = sealed_or_records
    elif type(sealed_or_records) in (dict, list):
        _reject_raw_block_year_counts(sealed_or_records, "G12")
        sealed = build_sealed_class_block_year_usability(
            sealed_or_records, policy, class_label="negative",
        )
    else:
        raise QCFail(
            "G12 requires sealed usability or per-pair records; "
            "raw caller-supplied counts are rejected"
        )
    sealed = require_sealed_class_block_year_usability(
        sealed, policy, expected_label="negative",
    )
    count_map = {(b, y): c for b, y, c in sealed.counts_by_block_year}
    for block in BLOCK_CANDIDATES:
        for year in policy.target_years:
            count = count_map[(block, year)]
            if count < policy.g12_minimum:
                return GATE_FAIL
    return GATE_PASS


def evaluate_g13(
    predictor_keys: set[str] | frozenset[str] | list[str],
    policy: LockedGatePolicy,
) -> str:
    policy = require_sealed_gate_policy(policy)
    keys = require_frozen_pilot_key_identity(policy, predictor_keys)
    if len(keys) != policy.g13_expected:
        return GATE_FAIL
    return GATE_PASS


def evaluate_g14(
    *,
    option_id: str,
    positive: int,
    negative: int,
    unknown: int,
    year_allocation: dict[str, dict[str, int]],
    post_evidence_substitution: bool,
    policy: LockedGatePolicy,
    pilot_keys: set[str] | frozenset[str] | list[str],
    key_labels: set[tuple[str, str]] | frozenset[tuple[str, str]] | list[tuple[str, str]],
    key_years: set[tuple[str, str]] | frozenset[tuple[str, str]] | list[tuple[str, str]],
) -> str:
    policy = require_sealed_gate_policy(policy)
    if type(post_evidence_substitution) is not bool:
        raise QCFail("post_evidence_substitution must be exact bool")
    if type(positive) is not int or type(negative) is not int or type(unknown) is not int:
        raise QCFail("G14 class counts must be exact int")
    if positive < 0 or negative < 0 or unknown < 0:
        raise QCFail("G14 class counts must be >= 0")
    keys = require_frozen_pilot_key_identity(policy, pilot_keys)
    labels = require_frozen_pilot_label_identity(policy, key_labels)
    years = require_frozen_pilot_year_identity(policy, key_years)
    if post_evidence_substitution:
        return GATE_FAIL
    # Claiming no substitution while identity already mismatched is impossible
    # after require_*; still bind identity into the pass path explicitly.
    if (
        keys != policy.frozen_pilot_keys
        or labels != policy.frozen_pilot_key_labels
        or years != policy.frozen_pilot_key_years
    ):
        return GATE_FAIL
    if type(option_id) is not str or option_id != policy.g14_option_id:
        return GATE_FAIL
    if positive != lock.APPROVED_POSITIVE:
        return GATE_FAIL
    if negative != lock.APPROVED_NEGATIVE:
        return GATE_FAIL
    if unknown != lock.APPROVED_UNKNOWN:
        return GATE_FAIL
    if type(year_allocation) is not dict:
        return GATE_FAIL
    if year_allocation != lock.EXPECTED_YEAR_ALLOCATION:
        return GATE_FAIL
    return GATE_PASS


def evaluate_score_without_evidence(
    accessibility_score: Any,
    evidence_captured: Any,
) -> str:
    if type(evidence_captured) is not bool:
        return GATE_FAIL
    if accessibility_score is not None and not evidence_captured:
        return GATE_FAIL
    return GATE_NOT_APPLIED


def evaluate_candidate_gates(gate_input: ValidatedGateInput) -> dict[str, str]:
    """Evaluate G01–G08 from sealed ValidatedGateInput only (no raw dicts)."""
    gate_input = require_sealed_gate_input(gate_input)
    evidence = gate_input.evidence
    # Sealed evidence is proof that synthetic evidence exists; never trust a
    # caller-controlled evidence_captured boolean.
    evidence_captured = True
    score = gate_input.accessibility_score
    if score is not None and not evidence_captured:
        g01 = GATE_FAIL
    else:
        g01 = evaluate_g01(score)
    statuses = {
        "G01": g01,
        "G02": evaluate_g02(gate_input.authoritative_source),
        "G03": evaluate_g03(gate_input.reproducible_retrieval),
        "G04": evaluate_g04(evidence.published_at, evidence.available_at),
        "G05": evaluate_g05(gate_input.quality_controls_met),
        "G06": evaluate_g06(evidence.available_at),
        "G07": evaluate_g07_from_cutoff(
            evidence.available_at, gate_input.prediction_cutoff,
        ),
    }
    statuses["G08"] = evaluate_g08(statuses)
    return statuses


def evaluate_pilot_gates_synthetic(
    *,
    policy: LockedGatePolicy,
    usable_by_candidate: dict[str, set[str]],
    usable_by_pair_block: dict[str, dict[str, bool]],
    g11_pair_block_usability: Any,
    g12_pair_block_usability: Any,
    pilot_keys: set[str] | frozenset[str] | list[str],
    key_labels: set[tuple[str, str]] | frozenset[tuple[str, str]] | list[tuple[str, str]],
    key_years: set[tuple[str, str]] | frozenset[tuple[str, str]] | list[tuple[str, str]],
    option_id: str,
    positive: int,
    negative: int,
    unknown: int,
    year_allocation: dict[str, dict[str, int]],
    post_evidence_substitution: bool,
) -> dict[str, str]:
    """Composite G09–G14 evaluation bound to exact frozen pilot identity."""
    policy = require_sealed_gate_policy(policy)
    require_frozen_pilot_key_identity(policy, pilot_keys)
    require_frozen_pilot_label_identity(policy, key_labels)
    require_frozen_pilot_year_identity(policy, key_years)
    return {
        "G09": evaluate_g09(usable_by_candidate, pilot_keys, policy),
        "G10": evaluate_g10(usable_by_pair_block, pilot_keys, policy),
        "G11": evaluate_g11(g11_pair_block_usability, policy),
        "G12": evaluate_g12(g12_pair_block_usability, policy),
        "G13": evaluate_g13(pilot_keys, policy),
        "G14": evaluate_g14(
            option_id=option_id,
            positive=positive,
            negative=negative,
            unknown=unknown,
            year_allocation=year_allocation,
            post_evidence_substitution=post_evidence_substitution,
            policy=policy,
            pilot_keys=pilot_keys,
            key_labels=key_labels,
            key_years=key_years,
        ),
    }


# --------------------------------------------------------------------------- #
# Contract / template builders
# --------------------------------------------------------------------------- #

def build_evidence_capture_contract(schema: dict) -> dict:
    return {
        "contract_version": "stage125_part3b0_v1",
        "stage": CURRENT_STAGE,
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "purpose": (
            "Readiness contract for Part 3B evidence capture. Templates only; "
            "no real evidence rows in Part 3B.0."
        ),
        "required_field_count": len(schema.get("required_fields", [])),
        "required_fields": evidence_header_from_schema(schema),
        "null_rules": schema.get("null_rules", {}),
        "real_evidence_records_allowed": False,
        "accessibility_scoring_allowed": False,
        "candidate_decisions_allowed": False,
        "part3b_started": False,
        "part3b0_readiness": True,
        "synthetic_validator_only": True,
        "unknown_factual_values": "null_never_zero_or_guess",
    }


def build_immutable_cache_contract() -> dict:
    return {
        "contract_version": "stage125_part3b0_v1",
        "stage": CURRENT_STAGE,
        "keying": "sha256_of_exact_raw_bytes",
        "write_once": True,
        "atomic_directory_commit": True,
        "no_os_replace_overwrite_of_existing_entry": True,
        "identical_payload_and_canonical_metadata_no_op": True,
        "identical_payload_different_metadata_fail_closed": True,
        "payload_hash_verified_on_get": True,
        "metadata_hash_verified_on_get": True,
        "external_expected_metadata_sha256_required_on_get": True,
        "metadata_payload_linkage_verified_on_get": True,
        "exactly_one_complete_entry_required": True,
        "path_traversal_rejected": True,
        "symlink_components_rejected_lexically": True,
        "orphan_partial_staging_entries_fail_closed": True,
        "malformed_metadata_json_fail_closed": True,
        "overwrite_support": False,
        "mutable_latest_file": False,
        "unknown_hash_or_missing_payload": "unresolved_fail_closed",
        "repository_cache_populated_in_part3b0": False,
        "put_returns_payload_and_metadata_sha256": True,
        "external_cache_handle_required_for_secure_get": True,
        "cache_handle_persists_metadata_sha256_across_restart": True,
        "cache_handle_binds_evidence_id_into_canonical_metadata": True,
        "cache_handle_evidence_id_verified_on_secure_get": True,
        "cache_handle_load_requires_external_handle_sha256": True,
        "cache_handle_internal_row_hash_not_trusted": True,
        "cache_handle_template_header_only_in_part3b0": True,
        "real_cache_handles_created_in_part3b0": False,
    }


def build_network_denial_contract() -> dict:
    process_route_names = sorted(
        f"os.{name}"
        for name in (
            *_OS_SPAWN_NAMES,
            *_OS_POSIX_SPAWN_NAMES,
            *_OS_FORK_NAMES,
            *_OS_EXEC_NAMES,
        )
        if hasattr(os, name)
    )
    return {
        "contract_version": "stage125_part3b0_v1",
        "stage": CURRENT_STAGE,
        "default_deny": True,
        "blocked_primitives": [
            "socket.socket.connect",
            "socket.socket.connect_ex",
            "socket.create_connection",
            "socket.socket.sendto",
            "socket.socket.sendmsg",
            "socket.getaddrinfo",
            "socket.gethostbyname",
            "urllib.request.urlopen",
            "urllib.request.urlretrieve",
            "http.client.HTTPConnection.connect",
            "http.client.HTTPSConnection.connect",
            "subprocess:default_deny_except_exact_readonly_git",
            "os.system",
            "os.popen",
            *process_route_names,
            "multiprocessing.Process.start",
        ],
        "subprocess_policy": "default_deny_except_exact_argument_level_readonly_git",
        "child_process_policy": (
            "default_deny_available_stdlib_child_and_process_replacement_routes_"
            "except_exact_readonly_git"
        ),
        "child_process_scope_note": (
            "Denies available direct stdlib routes: subprocess, os.system/popen, "
            "os.spawn*, os.posix_spawn*, os.fork/forkpty, os.exec*, and "
            "multiprocessing.Process.start. Does not claim coverage of "
            "non-stdlib or ctypes/native bypasses."
        ),
        "exact_git_readonly_allowlist": sorted(_GIT_ALLOWED_SUBCOMMANDS),
        "on_attempt": {
            "increment_network_calls_attempted": True,
            "raise_fail_closed_exception": True,
            "leave_no_partial_cache_or_evidence": True,
            "no_child_process_created_on_deny": True,
        },
        "required_final_state": {
            "network_calls_attempted": 0,
            "network_extraction_performed": False,
        },
    }


def build_evidence_manifest_template_csv(schema: dict) -> str:
    return _csv_str(evidence_header_from_schema(schema), [])


def build_gate_result_template_csv() -> str:
    return _csv_str(_GATE_RESULT_HEADER, [])


def build_readme() -> str:
    return "\n".join([
        "# Stage125 Part 3B.0 — Evidence Capture Readiness",
        "",
        "## Scope",
        "",
        "Part 3B.0 is **infrastructure/readiness only**. It performs:",
        "- **No** modeling, **no** real evidence capture, **no** network access.",
        "- **No** real accessibility scores or candidate admission decisions.",
        "- **No** changes to frozen Stage122–Stage125 Part 3A.1 scientific assets.",
        "- Part 3B evidence capture (`stage125-part3b-evidence-capture`) is **not started**.",
        "",
        "## Deliverables",
        "",
        "- Evidence capture contract JSON (schema + null rules).",
        "- Header-only evidence manifest template CSV (zero data rows).",
        "- Header-only gate-result template CSV (zero data rows).",
        "- Immutable raw-cache contract JSON (tested in pytest temp dirs only).",
        "- Header-only cache-handle template CSV (external trust-anchor contract).",
        "- Default-deny network/child-process sentinel contract JSON.",
        "",
        "## Guardrails",
        "",
        "- `part3b0_readiness=true`",
        "- `part3b_started=false`",
        "- `evidence_collected=false`",
        "- `accessibility_scoring_applied=false`",
        "- `network_extraction_performed=false`",
        "- `modeling_started=false`",
        "- `part3a_protocol_locked=true`",
        "- `part3a_decision_locked=true`",
        "- Snapshot bytes verified against `snapshot_sha256` (no symlink follow).",
        "- Gate inputs are sealed/typed; G07 derived from available_at vs cutoff.",
        "- G09–G14 bound to exact frozen pilot key identity (80/39/41).",
        "",
        "## Next research action",
        "",
        "Remains `stage125-part3b-evidence-capture` (pointer only; not started).",
        "",
    ]) + "\n"


def _csv_str(header: list[str], rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in header})
    return buf.getvalue()


def _json_str(obj: dict) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


# --------------------------------------------------------------------------- #
# Repository scans
# --------------------------------------------------------------------------- #

def _count_records_in_file(path: Path) -> int:
    suffix = path.suffix.lower()
    try:
        if suffix in {".csv", ".tsv"}:
            delim = "\t" if suffix == ".tsv" else ","
            rows = list(csv.DictReader(path.open(encoding="utf-8"), delimiter=delim))
            return len(rows)
        if suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return len(data)
            if isinstance(data, dict):
                for key in ("records", "rows", "evidence", "items"):
                    if isinstance(data.get(key), list):
                        return len(data[key])
                # Single object payloads count as one record when they look like evidence.
                if "evidence_id" in data:
                    return 1
            return 0
        if suffix in {".jsonl", ".ndjson"}:
            count = 0
            with path.open(encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        count += 1
            return count
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, csv.Error):
        # Unreadable evidence-like files are treated as a positive hit elsewhere;
        # record count stays conservative here.
        return 0
    return 0


def _authorized_part3b_paths(repo_root: Path) -> frozenset[str]:
    """Exact Part 3B live paths excluded from Part 3B.0 zero-evidence scans.

    Only active when the Part 3B authorization marker exists. Unauthorized
    Part 3B evidence still fails closed.
    """
    try:
        from src import stage125_part3b_evidence_capture as part3b
    except Exception:
        return frozenset()
    if not part3b.part3b_authorization_active(repo_root):
        return frozenset()
    return frozenset(part3b.PART3B_AUTHORIZED_EXACT)


def _is_authorized_part3b_path(repo_root: Path, rel: str) -> bool:
    rel = rel.replace("\\", "/")
    if rel in _authorized_part3b_paths(repo_root):
        return True
    # Local immutable cache for authorized Part 3B (gitignored payloads).
    if rel.startswith("project/stage125/raw_cache_part3b/"):
        try:
            from src import stage125_part3b_evidence_capture as part3b
            return part3b.part3b_authorization_active(repo_root)
        except Exception:
            return False
    return False


def count_real_evidence_records(repo_root: Path) -> int:
    """Count evidence records on disk, including a populated template file."""
    count = 0
    stage125 = repo_root / "project" / "stage125"
    if not stage125.is_dir():
        return 0
    template_path = stage125 / F_EVIDENCE_TEMPLATE
    if template_path.is_file():
        count += _count_records_in_file(template_path)
    for path in stage125.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        rel = str(path.relative_to(repo_root)).replace("\\", "/")
        if _is_authorized_part3b_path(repo_root, rel):
            continue
        if rel in PART3B0_ALLOWED_EXACT and path.name != F_EVIDENCE_TEMPLATE:
            continue
        if path == template_path:
            continue
        low = path.name.lower()
        if path.suffix.lower() not in EVIDENCE_SCAN_SUFFIXES:
            continue
        evidence_like = (
            any(low.startswith(p) for p in UNAUTHORIZED_NAME_PREFIXES)
            or any(tok in low for tok in ("evidence", "manifest"))
        )
        if evidence_like:
            count += _count_records_in_file(path)
    return count


_PENDING_DECISION_STATUSES = frozenset({
    "pending_part3b_evidence",
    "",
    "out_of_scope_locked",
    "research_design_only_not_registered",
    "registry_only_not_registered",
})
_SCORE_FIELD_NAMES = frozenset({
    "accessibility_score", "accessibility_scores", "score",
})
_DECISION_FIELD_NAMES = frozenset({
    "decision_status", "candidate_decision", "admission_status",
})
_CONTENT_SCAN_SUFFIXES = frozenset({".csv", ".tsv", ".json", ".jsonl", ".ndjson"})


def _stage125_files(repo_root: Path) -> list[Path]:
    stage125 = repo_root / "project" / "stage125"
    if not stage125.is_dir():
        return []
    return [p for p in stage125.rglob("*") if p.is_file() and not p.is_symlink()]


def _iter_content_dicts(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    try:
        if suffix in {".csv", ".tsv"}:
            delim = "\t" if suffix == ".tsv" else ","
            return list(csv.DictReader(path.open(encoding="utf-8"), delimiter=delim))
        if suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [x for x in data if isinstance(x, dict)]
            if isinstance(data, dict):
                for key in ("records", "rows", "evidence", "items", "assertions"):
                    if isinstance(data.get(key), list):
                        return [x for x in data[key] if isinstance(x, dict)]
                return [data]
        if suffix in {".jsonl", ".ndjson"}:
            out: list[dict[str, Any]] = []
            with path.open(encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        out.append(obj)
            return out
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, csv.Error):
        return []
    return []


def _is_nonempty_score(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return text not in ("", "null", "None", "nan", "NaN")


def count_accessibility_scores(repo_root: Path) -> int:
    """Recursively count non-empty accessibility/score fields under stage125."""
    scored = 0
    for path in _stage125_files(repo_root):
        rel = str(path.relative_to(repo_root)).replace("\\", "/")
        if _is_authorized_part3b_path(repo_root, rel):
            continue
        if path.suffix.lower() not in _CONTENT_SCAN_SUFFIXES:
            continue
        # Schema/rubric/contract docs define the field name but hold no scores.
        if path.name in {
            "accessibility_scoring_rubric_stage125_part3a.json",
            "part3_source_evidence_manifest_schema_stage125.json",
            "data_dictionary_stage125.csv",
        }:
            continue
        for row in _iter_content_dicts(path):
            for key, value in row.items():
                if str(key).strip().lower() in _SCORE_FIELD_NAMES and _is_nonempty_score(value):
                    scored += 1
    return scored


def count_candidate_decisions(repo_root: Path) -> int:
    """Recursively count non-pending decision fields under stage125."""
    decided = 0
    for path in _stage125_files(repo_root):
        rel = str(path.relative_to(repo_root)).replace("\\", "/")
        if _is_authorized_part3b_path(repo_root, rel):
            continue
        if path.suffix.lower() not in _CONTENT_SCAN_SUFFIXES:
            continue
        for row in _iter_content_dicts(path):
            for key, value in row.items():
                if str(key).strip().lower() not in _DECISION_FIELD_NAMES:
                    continue
                status = str(value or "").strip()
                if status not in _PENDING_DECISION_STATUSES:
                    decided += 1
    return decided


def count_populated_gate_results(repo_root: Path) -> int:
    """Count populated Gate-result data rows (template must remain header-only)."""
    count = 0
    for path in _stage125_files(repo_root):
        rel = str(path.relative_to(repo_root)).replace("\\", "/")
        if _is_authorized_part3b_path(repo_root, rel):
            continue
        low = path.name.lower()
        if "gate_result" not in low and path.name != F_GATE_TEMPLATE:
            continue
        if path.suffix.lower() not in {".csv", ".tsv"}:
            continue
        count += _count_records_in_file(path)
    return count


def scan_repository_cache_entries(repo_root: Path) -> int:
    count = 0
    stage125 = repo_root / "project" / "stage125"
    if not stage125.is_dir():
        return 0
    for path in stage125.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        rel = str(path.relative_to(repo_root)).replace("\\", "/")
        if _is_authorized_part3b_path(repo_root, rel):
            continue
        parts = {p.lower() for p in path.relative_to(stage125).parts}
        if parts & CACHE_DIR_NAMES or "raw_cache_part3b" in parts:
            if path.name.endswith(".meta.json") or path.name == "metadata.sha256":
                continue
            # Authorized Part 3B cache is excluded above; any other cache counts.
            if "raw_cache_part3b" in parts:
                continue
            count += 1
    return count


def _file_has_prohibited_live_content(path: Path) -> bool:
    """True when an allowlisted/unknown file carries live scores/decisions/evidence."""
    if path.suffix.lower() not in _CONTENT_SCAN_SUFFIXES:
        return False
    # Skip pure schema/rubric vocabulary files.
    if path.name in {
        "accessibility_scoring_rubric_stage125_part3a.json",
        "part3_source_evidence_manifest_schema_stage125.json",
        "data_dictionary_stage125.csv",
        "provenance_manifest_schema_stage125.json",
    }:
        return False
    rows = _iter_content_dicts(path)
    for row in rows:
        keys = {str(k).strip().lower() for k in row}
        if keys & _SCORE_FIELD_NAMES:
            for k, v in row.items():
                if str(k).strip().lower() in _SCORE_FIELD_NAMES and _is_nonempty_score(v):
                    return True
        if keys & _DECISION_FIELD_NAMES:
            for k, v in row.items():
                if str(k).strip().lower() in _DECISION_FIELD_NAMES:
                    if str(v or "").strip() not in _PENDING_DECISION_STATUSES:
                        return True
        # Populated evidence records outside the empty template.
        if "evidence_id" in keys and _is_nonempty_score(row.get("evidence_id")):
            if path.name != F_EVIDENCE_TEMPLATE and "schema" not in path.name.lower():
                return True
        if "status" in keys and path.name == F_GATE_TEMPLATE:
            if _is_nonempty_score(row.get("status")):
                return True
    return False


def scan_for_part3b_capture_start(repo_root: Path) -> dict:
    """Closed-world Stage125 allowlist + recursive content-aware capture detector."""
    hits: list[str] = []
    for rel in part3a.PART3B_FORBIDDEN_EXACT:
        if (repo_root / rel).exists() and rel not in PART3B0_ALLOWED_EXACT:
            if not _is_authorized_part3b_path(repo_root, rel):
                hits.append(rel)

    stage125 = repo_root / "project" / "stage125"
    if stage125.is_dir():
        for path in stage125.rglob("*"):
            if not path.is_file():
                continue
            rel = str(path.relative_to(repo_root)).replace("\\", "/")
            if _is_authorized_part3b_path(repo_root, rel):
                continue
            if rel not in STAGE125_ALLOWED_EXACT:
                hits.append(rel)
                continue
            if _file_has_prohibited_live_content(path):
                hits.append(rel)

    for base_name, base in (
        ("src", repo_root / "project" / "src"),
        ("tests", repo_root / "project" / "tests"),
    ):
        del base_name
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            rel = str(path.relative_to(repo_root)).replace("\\", "/")
            if rel in PART3B0_ALLOWED_EXACT:
                continue
            if _is_authorized_part3b_path(repo_root, rel):
                continue
            low = path.name.lower()
            if any(low.startswith(p) for p in UNAUTHORIZED_NAME_PREFIXES):
                hits.append(rel)
            elif any(rel.startswith(p) for p in part3a.PART3B_FORBIDDEN_PREFIXES):
                hits.append(rel)

    for prefix in part3a.PART3B_FORBIDDEN_PREFIXES:
        root = repo_root / prefix
        if root.is_dir():
            for path in root.rglob("*"):
                if path.is_file():
                    rel = str(path.relative_to(repo_root)).replace("\\", "/")
                    if rel not in PART3B0_ALLOWED_EXACT and not _is_authorized_part3b_path(
                        repo_root, rel,
                    ):
                        hits.append(rel)

    # Content-derived capture signals.
    if count_accessibility_scores(repo_root) > 0:
        hits.append("content:accessibility_scores_present")
    if count_candidate_decisions(repo_root) > 0:
        hits.append("content:candidate_decisions_present")
    if count_populated_gate_results(repo_root) > 0:
        hits.append("content:populated_gate_results_present")
    if count_real_evidence_records(repo_root) > 0:
        hits.append("content:real_evidence_records_present")

    uniq = sorted(set(hits))
    return {"hits": uniq, "no_part3b": len(uniq) == 0}


def run_guardrails(
    project_dir: Path,
    repo_root: Path,
    network_calls: int,
) -> dict:
    modeling = part3a.scan_for_modeling_artifacts(project_dir)
    part3b = scan_for_part3b_capture_start(repo_root)
    return {
        "modeling": modeling,
        "part3b": part3b,
        "network_calls_attempted": network_calls,
        "no_network_calls": network_calls == 0,
        "real_evidence_record_count": count_real_evidence_records(repo_root),
        "accessibility_score_count": count_accessibility_scores(repo_root),
        "candidate_decision_count": count_candidate_decisions(repo_root),
        "cache_real_entry_count": scan_repository_cache_entries(repo_root),
    }


# --------------------------------------------------------------------------- #
# QC
# --------------------------------------------------------------------------- #

def build_qc_assertions(
    frozen_input_hashes: dict[str, str],
    frozen_before: dict,
    frozen_after: dict,
    content_hashes: dict,
    guard_evidence: dict,
    schema: dict,
    repo_root: Path,
    evidence_contract: dict,
    cache_contract: dict,
    network_contract: dict,
    policy: LockedGatePolicy,
) -> list[dict]:
    assertions: list[dict] = []

    def add(name: str, ok: bool, detail: str) -> None:
        assertions.append({
            "assertion": name,
            "status": "PASS" if ok else "FAIL",
            "detail": detail,
        })

    add(
        "frozen_input_hashes_match",
        len(frozen_input_hashes) == len(FROZEN_INPUT_PATHS),
        f"verified {len(frozen_input_hashes)} frozen inputs",
    )
    add(
        "registered_candidate_count_10",
        len(part3a.REGISTERED_CANDIDATES) == 10,
        "M2=3 M3=3 M4=4",
    )
    pilot_rows = load_locked_pilot_pairs(repo_root)
    pilot_keys = {r["predictor_row_key_t"] for r in pilot_rows}
    pos = sum(1 for r in pilot_rows if r["class_label"] == "positive")
    neg = sum(1 for r in pilot_rows if r["class_label"] == "negative")
    unk = sum(1 for r in pilot_rows if r["class_label"] == "unknown")
    tickers = {r["ticker"] for r in pilot_rows}
    industries = [r["industry"] for r in pilot_rows]
    ind_summary = lock.summarize_industry_counts(industries)
    add("pilot_unique_pairs_80", len(pilot_keys) == 80, f"count={len(pilot_keys)}")
    add("pilot_positive_39", pos == 39, f"positive={pos}")
    add("pilot_negative_41", neg == 41, f"negative={neg}")
    add("pilot_unknown_0", unk == 0, f"unknown={unk}")
    add("pilot_unique_tickers_26", len(tickers) == 26, f"tickers={len(tickers)}")
    add(
        "pilot_known_industries_10",
        ind_summary["unique_known_industries"] == 10,
        f"known={ind_summary['unique_known_industries']}",
    )
    add(
        "pilot_industry_present_53",
        ind_summary["industry_present_pairs"] == 53,
        f"present={ind_summary['industry_present_pairs']}",
    )
    add(
        "pilot_industry_missing_27",
        ind_summary["industry_missing_pairs"] == 27,
        f"missing={ind_summary['industry_missing_pairs']}",
    )
    add(
        "post_evidence_substitution_false",
        all(r.get("post_evidence_substitution_allowed") == "false"
            for r in pilot_rows),
        "post_evidence_substitution=false on all pilot rows",
    )
    gate_protocol = list(csv.DictReader(
        (repo_root / "project/stage125/part3_gate_decision_protocol_stage125.csv")
        .open(encoding="utf-8")
    ))
    add(
        "gate_protocol_g01_g14_present",
        {r["gate_id"] for r in gate_protocol}
        == {f"G{i:02d}" for i in range(1, 15)},
        "G01–G14 definitions present in locked protocol file",
    )
    add(
        "locked_gate_policy_hash_verified",
        bool(policy.source_thresholds_sha256)
        and bool(policy.source_decision_lock_sha256)
        and policy.g13_expected == 80
        and policy.g09_threshold == 0.80
        and policy.g10_threshold == 0.70,
        (
            f"g09={policy.g09_threshold} g10={policy.g10_threshold} "
            f"g13={policy.g13_expected}"
        ),
    )
    schema_fields = evidence_header_from_schema(schema)
    on_disk_template = repo_root / "project" / "stage125" / F_EVIDENCE_TEMPLATE
    if on_disk_template.is_file():
        disk_header = next(csv.reader(on_disk_template.open(encoding="utf-8")))
    else:
        disk_header = []
    generated_header = schema_fields
    add(
        "evidence_template_header_matches_frozen_schema",
        disk_header == schema_fields and generated_header == schema_fields
        and len(schema_fields) == 22,
        f"schema={schema_fields!r} disk={disk_header!r}",
    )
    evidence_rows = list(csv.DictReader(
        io.StringIO(build_evidence_manifest_template_csv(schema))
    ))
    gate_rows = list(csv.DictReader(io.StringIO(build_gate_result_template_csv())))
    add(
        "evidence_template_zero_rows",
        len(evidence_rows) == 0,
        f"rows={len(evidence_rows)}",
    )
    add(
        "gate_result_template_zero_rows",
        len(gate_rows) == 0,
        f"rows={len(gate_rows)}",
    )
    add(
        "real_evidence_record_count_zero",
        guard_evidence["real_evidence_record_count"] == 0,
        f"count={guard_evidence['real_evidence_record_count']}",
    )
    add(
        "accessibility_score_count_zero",
        guard_evidence["accessibility_score_count"] == 0,
        f"count={guard_evidence['accessibility_score_count']}",
    )
    add(
        "candidate_decision_count_zero",
        guard_evidence["candidate_decision_count"] == 0,
        f"count={guard_evidence['candidate_decision_count']}",
    )
    add(
        "network_calls_attempted_zero",
        guard_evidence["network_calls_attempted"] == 0,
        f"count={guard_evidence['network_calls_attempted']}",
    )
    add(
        "network_extraction_performed_false",
        guard_evidence["no_network_calls"]
        and network_contract.get("required_final_state", {})
        .get("network_extraction_performed") is False,
        "network_extraction_performed=false from sentinel + contract",
    )
    add(
        "cache_real_entry_count_zero",
        guard_evidence["cache_real_entry_count"] == 0
        and cache_contract.get("repository_cache_populated_in_part3b0") is False,
        f"count={guard_evidence['cache_real_entry_count']}",
    )
    add(
        "part3b0_readiness_true",
        evidence_contract.get("part3b0_readiness") is True
        and evidence_contract.get("real_evidence_records_allowed") is False
        and evidence_contract.get("synthetic_validator_only") is True,
        "derived from evidence capture contract",
    )
    add(
        "part3b_started_false",
        evidence_contract.get("part3b_started") is False
        and guard_evidence["part3b"]["no_part3b"],
        f"contract.part3b_started=false; hits={guard_evidence['part3b']['hits']}",
    )
    add(
        "evidence_collected_false",
        guard_evidence["real_evidence_record_count"] == 0
        and evidence_contract.get("real_evidence_records_allowed") is False,
        "derived from recursive evidence scan + contract",
    )
    add(
        "accessibility_scoring_applied_false",
        guard_evidence["accessibility_score_count"] == 0
        and evidence_contract.get("accessibility_scoring_allowed") is False,
        "derived from inventory scan + contract",
    )
    add("modeling_not_started", guard_evidence["modeling"]["no_modeling"],
        "no modeling artifacts detected")
    add(
        "no_frozen_scientific_assets_changed",
        frozen_before == frozen_after,
        "frozen asset hashes unchanged",
    )
    add(
        "evidence_schema_22_fields",
        len(schema.get("required_fields", [])) == 22,
        f"fields={len(schema.get('required_fields', []))}",
    )
    add(
        "evidence_schema_version_locked",
        schema.get("schema_version") == EVIDENCE_SCHEMA_VERSION,
        schema.get("schema_version", ""),
    )
    add(
        "part3b_capture_not_started",
        guard_evidence["part3b"]["no_part3b"],
        f"part3b hits={guard_evidence['part3b']['hits']}",
    )
    add(
        "content_hashes_present",
        set(content_hashes) >= set(CONTENT_FILES),
        f"files={sorted(content_hashes)}",
    )
    return assertions


def build_qc_report(
    repo_root: Path,
    frozen_input_hashes: dict[str, str],
    content_hashes: dict,
    frozen_before: dict,
    frozen_after: dict,
    guard_evidence: dict,
    schema: dict,
    tickers: list[str],
    evidence_contract: dict,
    cache_contract: dict,
    network_contract: dict,
    policy: LockedGatePolicy,
) -> dict:
    root = str(repo_root)
    source_commit = _git_last_code_commit(root, [SRC_REL, TEST_REL])
    ts = _git_commit_timestamp(root, source_commit)
    assertions = build_qc_assertions(
        frozen_input_hashes, frozen_before, frozen_after,
        content_hashes, guard_evidence, schema, repo_root,
        evidence_contract, cache_contract, network_contract, policy,
    )
    failed = sum(1 for a in assertions if a["status"] != "PASS")
    return {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "generated_at": ts,
        "source_commit": source_commit,
        "source_file_sha256": sha256_file(repo_root / SRC_REL),
        "test_file_sha256": sha256_file(repo_root / TEST_REL),
        "baseline_commit": EXPECTED_BASELINE_COMMIT,
        "assertion_count": len(assertions),
        "failed_count": failed,
        "all_pass": failed == 0,
        "ticker_count": len(tickers),
        "tickers": tickers,
        "frozen_input_sha256": dict(sorted(frozen_input_hashes.items())),
        "output_sha256": dict(sorted(content_hashes.items())),
        "frozen_assets_before": frozen_before,
        "frozen_assets_after": frozen_after,
        "modeling_started": False,
        "gate_b_started": True,
        "part2_started": True,
        "part3_started": True,
        "part3a_protocol_locked": True,
        "part3a_decision_locked": True,
        "part3b0_readiness": True,
        "part3b_started": False,
        "evidence_collected": False,
        "accessibility_scoring_applied": False,
        "pilot_extraction_started": False,
        "network_extraction_performed": not guard_evidence["no_network_calls"],
        "network_calls_attempted": guard_evidence["network_calls_attempted"],
        "guard_evidence": guard_evidence,
        "assertions": assertions,
    }


def build_metadata(
    repo_root: Path, qc_report: dict, content_hashes: dict, qc_hash: str,
) -> dict:
    output_hashes = dict(content_hashes)
    output_hashes[F_QC] = qc_hash
    return {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "description": "Stage125 Part 3B.0 — evidence capture readiness.",
        "generated_at": qc_report["generated_at"],
        "code_commit": qc_report["source_commit"],
        "baseline_commit": EXPECTED_BASELINE_COMMIT,
        "source_file_sha256": qc_report["source_file_sha256"],
        "test_file_sha256": qc_report["test_file_sha256"],
        "output_files_sha256": dict(sorted(output_hashes.items())),
        "modeling_started": False,
        "part3a_protocol_locked": True,
        "part3a_decision_locked": True,
        "part3b0_readiness": True,
        "part3b_started": False,
        "evidence_collected": False,
        "accessibility_scoring_applied": False,
        "network_extraction_performed": qc_report.get(
            "network_extraction_performed", False),
        "network_calls_attempted": qc_report.get("network_calls_attempted", 0),
        "warning": (
            "Part 3B.0 only: readiness contracts and validators. No modeling, "
            "no real evidence, no network access. Part 3B evidence capture not "
            "started. Frozen scientific assets unchanged."
        ),
    }


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def build_all(repo_root: Path) -> dict:
    verify_baseline_commit(str(repo_root))
    project_dir = repo_root / "project"
    with network_sentinel() as sentinel:
        frozen_before = frozen_asset_hashes(repo_root)
        frozen_input_hashes = verify_frozen_input_hashes(repo_root)
        schema = load_frozen_evidence_schema(repo_root)
        policy = load_locked_gate_policy(repo_root)

        evidence_contract = build_evidence_capture_contract(schema)
        cache_contract = build_immutable_cache_contract()
        network_contract = build_network_denial_contract()
        content_files = {
            F_EVIDENCE_CONTRACT: _json_str(evidence_contract),
            F_EVIDENCE_TEMPLATE: build_evidence_manifest_template_csv(schema),
            F_GATE_TEMPLATE: build_gate_result_template_csv(),
            F_CACHE_CONTRACT: _json_str(cache_contract),
            F_CACHE_HANDLE_TEMPLATE: build_cache_handle_template_csv(),
            F_NETWORK_CONTRACT: _json_str(network_contract),
            F_README: build_readme(),
        }
        content_hashes = {
            name: sha256_bytes(content.encode("utf-8"))
            for name, content in sorted(content_files.items())
        }

        frozen_after = frozen_asset_hashes(repo_root)
        if frozen_before != frozen_after:
            raise QCFail("frozen assets changed during Part 3B.0 run (fail-closed)")

        guard_evidence = run_guardrails(project_dir, repo_root, sentinel.calls_attempted)

        df_all, df_pairs, _, _ = part3a.load_inputs(
            project_dir / "stage124" / "gate_b_final" / part3a.INPUT_ALL_ROWS_NAME,
            project_dir / "stage124" / "gate_b_final" / part3a.INPUT_PAIRS_NAME,
        )
        tickers = sorted(
            t for t in df_pairs["ticker"].dropna().unique() if str(t).strip()
        )

        qc_report = build_qc_report(
            repo_root, frozen_input_hashes, content_hashes,
            frozen_before, frozen_after, guard_evidence, schema, tickers,
            evidence_contract, cache_contract, network_contract, policy,
        )
        if not qc_report["all_pass"]:
            failed = [a for a in qc_report["assertions"] if a["status"] != "PASS"]
            raise QCFail(
                "QC failed (fail-closed): "
                + "; ".join(f"{a['assertion']}: {a['detail']}" for a in failed)
            )

        qc_str = _json_str(qc_report)
        qc_hash = sha256_bytes(qc_str.encode("utf-8"))
        metadata = build_metadata(repo_root, qc_report, content_hashes, qc_hash)

        files: dict[str, str] = dict(content_files)
        files[F_QC] = qc_str
        files[F_METADATA] = _json_str(metadata)
        return {
            "files": files,
            "qc": qc_report,
            "guard_evidence": guard_evidence,
            "frozen_input_hashes": frozen_input_hashes,
            "policy": policy,
        }


def run(
    project_dir: Path | None = None,
    output_dir: Path | None = None,
    write: bool = False,
) -> dict:
    if project_dir is None:
        project_dir = Path(__file__).resolve().parent.parent
    repo_root = project_dir.parent
    if output_dir is None:
        output_dir = project_dir / "stage125"

    # Transition-aware: after authorized Part 3B starts, the canonical Part 3B.0
    # deliverables are a frozen historical baseline (byte-identical check).
    # Writes to the canonical stage125 directory are refused. Writes to a
    # temporary output_dir (tests) may still regenerate via build_all, which
    # excludes authorized Part 3B paths from zero-evidence scans.
    from src import stage125_part3b_evidence_capture as part3b  # lazy

    canonical_out = (project_dir / "stage125").resolve()
    if part3b.part3b_authorization_active(repo_root):
        if output_dir.resolve() == canonical_out:
            if write:
                raise QCFail(
                    "Part 3B.0 historical baseline is frozen after Part 3B "
                    "authorization; --write to canonical stage125 is refused"
                )
            return part3b.check_historical_baseline(
                repo_root,
                output_dir,
                F_METADATA,
                require_historical_flags={
                    "part3b0_readiness": True,
                    "part3b_started": False,
                    "evidence_collected": False,
                    "accessibility_scoring_applied": False,
                    "network_extraction_performed": False,
                    "modeling_started": False,
                },
            )

    result = build_all(repo_root)
    files = result["files"]

    if write:
        output_dir.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            (output_dir / name).write_text(content, encoding="utf-8")
        result["written"] = True
        result["drift"] = []
    else:
        drift = []
        for name, content in files.items():
            path = output_dir / name
            if not path.is_file():
                drift.append(name)
            elif path.read_text(encoding="utf-8") != content:
                drift.append(name)
        result["written"] = False
        result["drift"] = drift
    result["output_dir"] = str(output_dir)
    return result
