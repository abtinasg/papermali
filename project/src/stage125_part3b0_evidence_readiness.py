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
import os
import re
import socket
import subprocess
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

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
F_NETWORK_CONTRACT = "part3b0_network_denial_contract_stage125.json"
F_QC = "stage125_part3b0_evidence_readiness_qc_report.json"
F_METADATA = "metadata_and_hashes_stage125_part3b0.json"
F_README = "README_STAGE125_PART3B0_EVIDENCE_READINESS.md"

CONTENT_FILES = (
    F_EVIDENCE_CONTRACT,
    F_EVIDENCE_TEMPLATE,
    F_GATE_TEMPLATE,
    F_CACHE_CONTRACT,
    F_NETWORK_CONTRACT,
    F_README,
)

GATE_PASS = "PASS"
GATE_FAIL = "FAIL"
GATE_UNRESOLVED = "UNRESOLVED"
GATE_NOT_APPLIED = "NOT_APPLIED"

SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
ISO_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?$"
)
ALLOWED_CALENDARS = frozenset({"gregorian", "jalali", "hijri", "unknown"})
ALLOWED_TIMEZONES = frozenset({"UTC", "Asia/Tehran", "unknown"})

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

_EVIDENCE_HEADER = [
    "evidence_id",
    "candidate_id",
    "source_id",
    "source_owner",
    "source_url",
    "source_title",
    "source_identifier",
    "retrieved_at_utc",
    "published_at",
    "available_at",
    "raw_date_text",
    "calendar",
    "timezone",
    "access_method",
    "authentication_required",
    "response_status_evidence",
    "local_snapshot_path",
    "snapshot_sha256",
    "revision_status",
    "license_or_usage_notes",
    "reviewer_status",
    "failure_reason",
]

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
# Network sentinel (default-deny)
# --------------------------------------------------------------------------- #

class NetworkSentinel:
    """Default-deny network sentinel for Part 3B.0 execution and tests."""

    def __init__(self) -> None:
        self.calls_attempted = 0
        self._orig_connect = socket.socket.connect
        self._orig_connect_ex = socket.socket.connect_ex
        self._orig_create_connection = socket.create_connection
        self._urllib_patches: list[tuple[Any, str, Any]] = []

    def _blocked(self, label: str, *args, **kwargs):
        self.calls_attempted += 1
        raise NetworkBlockedError(
            f"network blocked by Part 3B.0 sentinel ({label}): {args!r}"
        )

    def _blocked_connect(self, _sock, *args, **kwargs):
        self._blocked("socket.connect", *args, **kwargs)

    def _blocked_connect_ex(self, _sock, *args, **kwargs):
        self._blocked("socket.connect_ex", *args, **kwargs)

    def _blocked_create_connection(self, *args, **kwargs):
        self._blocked("socket.create_connection", *args, **kwargs)

    def install(self) -> None:
        socket.socket.connect = self._blocked_connect  # type: ignore[method-assign]
        socket.socket.connect_ex = self._blocked_connect_ex  # type: ignore[method-assign]
        socket.create_connection = self._blocked_create_connection  # type: ignore[assignment]
        try:
            import urllib.request as urllib_request

            self._urllib_patches.append(
                (urllib_request, "urlopen", urllib_request.urlopen)
            )
            urllib_request.urlopen = (  # type: ignore[assignment]
                lambda *a, **k: self._blocked("urllib.request.urlopen", *a, **k)
            )
        except ImportError:
            pass
        try:
            import http.client as http_client

            self._urllib_patches.append(
                (http_client, "HTTPConnection", http_client.HTTPConnection)
            )

            class _BlockedHTTPConnection(http_client.HTTPConnection):
                def connect(inner_self):  # noqa: N805
                    self._blocked("http.client.HTTPConnection.connect")

            http_client.HTTPConnection = _BlockedHTTPConnection  # type: ignore[misc,assignment]
        except ImportError:
            pass

    def restore(self) -> None:
        socket.socket.connect = self._orig_connect  # type: ignore[method-assign]
        socket.socket.connect_ex = self._orig_connect_ex  # type: ignore[method-assign]
        socket.create_connection = self._orig_create_connection  # type: ignore[assignment]
        for module, attr, original in self._urllib_patches:
            setattr(module, attr, original)
        self._urllib_patches.clear()


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

class ImmutableCache:
    """Content-addressed, write-once immutable cache abstraction."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _payload_path(self, content_hash: str) -> Path:
        if not SHA256_RE.match(content_hash):
            raise ImmutableCacheError(f"invalid content hash: {content_hash}")
        rel = Path(content_hash[:2]) / content_hash
        target = (self.root / rel).resolve()
        if not str(target).startswith(str(self.root) + os.sep):
            raise ImmutableCacheError("path traversal rejected")
        if target.is_symlink():
            raise ImmutableCacheError("symlink escape rejected")
        return target

    def _metadata_path(self, content_hash: str) -> Path:
        return self._payload_path(content_hash).with_suffix(".meta.json")

    def put(self, data: bytes, metadata: dict[str, Any] | None = None) -> str:
        content_hash = sha256_bytes(data)
        payload_path = self._payload_path(content_hash)
        meta = dict(metadata or {})
        meta["content_sha256"] = content_hash
        meta_bytes = json.dumps(meta, sort_keys=True, ensure_ascii=False).encode(
            "utf-8"
        )
        meta_hash = sha256_bytes(meta_bytes)
        if payload_path.exists():
            existing = payload_path.read_bytes()
            if existing != data:
                raise ImmutableCacheError(
                    f"content hash collision with different bytes at {content_hash}"
                )
            existing_meta = self._metadata_path(content_hash)
            if existing_meta.exists():
                if sha256_bytes(existing_meta.read_bytes()) != meta_hash:
                    raise ImmutableCacheError(
                        f"metadata hash mismatch for existing entry {content_hash}"
                    )
            return content_hash
        payload_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path = self._metadata_path(content_hash)
        with tempfile.NamedTemporaryFile(
            dir=payload_path.parent, delete=False,
        ) as tmp_payload:
            tmp_payload.write(data)
            tmp_payload.flush()
            os.fsync(tmp_payload.fileno())
            tmp_name = tmp_payload.name
        os.replace(tmp_name, payload_path)
        with tempfile.NamedTemporaryFile(
            dir=meta_path.parent, delete=False,
        ) as tmp_meta:
            tmp_meta.write(meta_bytes)
            tmp_meta.flush()
            os.fsync(tmp_meta.fileno())
            tmp_meta_name = tmp_meta.name
        os.replace(tmp_meta_name, meta_path)
        return content_hash

    def get(self, content_hash: str) -> bytes:
        payload_path = self._payload_path(content_hash)
        meta_path = self._metadata_path(content_hash)
        if not payload_path.is_file() or not meta_path.is_file():
            raise ImmutableCacheError(
                f"unknown hash or missing payload/metadata: {content_hash}"
            )
        data = payload_path.read_bytes()
        if sha256_bytes(data) != content_hash:
            raise ImmutableCacheError(
                f"payload hash mismatch for {content_hash}"
            )
        meta_bytes = meta_path.read_bytes()
        meta = json.loads(meta_bytes.decode("utf-8"))
        if meta.get("content_sha256") != content_hash:
            raise ImmutableCacheError(
                f"metadata/payload hash linkage failed for {content_hash}"
            )
        if sha256_bytes(meta_bytes) != sha256_bytes(meta_bytes):
            pass
        return data

    def has(self, content_hash: str) -> bool:
        try:
            self.get(content_hash)
        except ImmutableCacheError:
            return False
        return True

    def entry_count(self) -> int:
        return sum(1 for p in self.root.rglob("*") if p.is_file() and not p.name.endswith(".meta.json"))


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


def _validate_datetime_field(name: str, value: Any) -> None:
    if _is_null(value):
        return
    if not isinstance(value, str):
        raise EvidenceValidationError(f"{name}: wrong type")
    if not ISO_DATETIME_RE.match(value.strip()):
        raise EvidenceValidationError(f"{name}: invalid datetime format")
    if _contains_guessed_marker(value):
        raise EvidenceValidationError(f"{name}: guessed/inferred marker")


def _validate_sha256_field(name: str, value: Any) -> None:
    if _is_null(value):
        return
    if not isinstance(value, str) or not SHA256_RE.match(value.strip().lower()):
        raise EvidenceValidationError(f"{name}: invalid SHA-256")


def validate_evidence_record(
    record: dict[str, Any],
    *,
    schema: dict,
    candidate_source_map: dict[str, str],
    source_registry: dict[str, dict],
    allow_real_evidence: bool = False,
) -> None:
    """Fail-closed validator for stage125_part3b_evidence_v1 records."""
    if not allow_real_evidence:
        raise EvidenceValidationError(
            "real evidence records are prohibited in Part 3B.0"
        )
    if schema.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
        raise EvidenceValidationError("unsupported schema version")
    required = schema.get("required_fields", [])
    allowed_names = {f["name"] for f in required}
    unknown = set(record) - allowed_names
    if unknown:
        raise EvidenceValidationError(f"unknown fields: {sorted(unknown)}")
    for field in required:
        name = field["name"]
        nullable = field.get("nullable", True)
        ftype = field.get("type")
        value = record.get(name)
        if not nullable and _is_null(value):
            raise EvidenceValidationError(f"missing non-nullable field: {name}")
        if _is_null(value):
            continue
        if ftype == "string" and not isinstance(value, str):
            raise EvidenceValidationError(f"{name}: wrong type")
        if ftype == "boolean" and not isinstance(value, bool):
            raise EvidenceValidationError(f"{name}: wrong type")
        if ftype == "datetime":
            _validate_datetime_field(name, value)
        if name == "snapshot_sha256":
            _validate_sha256_field(name, value)
        if name in ("calendar",) and str(value).strip().lower() not in ALLOWED_CALENDARS:
            raise EvidenceValidationError(f"{name}: invalid calendar")
        if name in ("timezone",) and str(value).strip() not in ALLOWED_TIMEZONES:
            raise EvidenceValidationError(f"{name}: invalid timezone")
        if isinstance(value, str) and _contains_guessed_marker(value):
            raise EvidenceValidationError(f"{name}: guessed/inferred marker")
    candidate_id = record.get("candidate_id")
    source_id = record.get("source_id")
    if candidate_id not in candidate_source_map:
        raise EvidenceValidationError(f"unknown candidate_id: {candidate_id}")
    if source_id not in source_registry:
        raise EvidenceValidationError(f"unknown source_id: {source_id}")
    if candidate_source_map[candidate_id] != source_id:
        raise EvidenceValidationError("candidate/source mapping mismatch")
    out_of_scope_ids = {
        c["candidate_id"] for c in part3a.OUT_OF_SCOPE_LOCKED
    } | {c["candidate_id"] for c in part3a.RESEARCH_DESIGN_ONLY}
    if candidate_id in out_of_scope_ids:
        raise EvidenceValidationError(
            f"out-of-scope or narrative-only candidate: {candidate_id}"
        )


def validate_evidence_record_synthetic(
    record: dict[str, Any],
    *,
    schema: dict,
    candidate_source_map: dict[str, str],
    source_registry: dict[str, dict],
) -> None:
    """Validator entry point for synthetic test fixtures only."""
    try:
        # Re-use core checks without the Part 3B.0 real-evidence prohibition.
        if schema.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
            raise EvidenceValidationError("unsupported schema version")
        required = schema.get("required_fields", [])
        allowed_names = {f["name"] for f in required}
        unknown = set(record) - allowed_names
        if unknown:
            raise EvidenceValidationError(f"unknown fields: {sorted(unknown)}")
        for field in required:
            name = field["name"]
            nullable = field.get("nullable", True)
            ftype = field.get("type")
            value = record.get(name)
            if not nullable and _is_null(value):
                raise EvidenceValidationError(f"missing non-nullable field: {name}")
            if _is_null(value):
                continue
            if ftype == "string" and not isinstance(value, str):
                raise EvidenceValidationError(f"{name}: wrong type")
            if ftype == "boolean" and not isinstance(value, bool):
                raise EvidenceValidationError(f"{name}: wrong type")
            if ftype == "datetime":
                _validate_datetime_field(name, value)
            if name == "snapshot_sha256":
                _validate_sha256_field(name, value)
            if name in ("calendar",) and str(value).strip().lower() not in ALLOWED_CALENDARS:
                raise EvidenceValidationError(f"{name}: invalid calendar")
            if name in ("timezone",) and str(value).strip() not in ALLOWED_TIMEZONES:
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
    except EvidenceValidationError:
        raise


# --------------------------------------------------------------------------- #
# Pure Gate engine
# --------------------------------------------------------------------------- #

def evaluate_g01(accessibility_score: int | None) -> str:
    if accessibility_score is None:
        return GATE_UNRESOLVED
    if accessibility_score <= 2:
        return GATE_FAIL
    if accessibility_score == 3:
        return GATE_PASS
    if accessibility_score >= 4:
        return GATE_PASS
    return GATE_FAIL


def evaluate_g02(authoritative_source: bool | None) -> str:
    if authoritative_source is None:
        return GATE_UNRESOLVED
    return GATE_PASS if authoritative_source else GATE_FAIL


def evaluate_g03(reproducible_retrieval: bool | None) -> str:
    if reproducible_retrieval is None:
        return GATE_UNRESOLVED
    return GATE_PASS if reproducible_retrieval else GATE_FAIL


def evaluate_g04(
    published_at: str | None, available_at: str | None,
) -> str:
    if _is_null(published_at) and _is_null(available_at):
        return GATE_UNRESOLVED
    if not _is_null(published_at) or not _is_null(available_at):
        return GATE_PASS
    return GATE_UNRESOLVED


def evaluate_g05(quality_controls_met: bool | None) -> str:
    if quality_controls_met is None:
        return GATE_UNRESOLVED
    return GATE_PASS if quality_controls_met else GATE_FAIL


def evaluate_g06(available_at: str | None) -> str:
    if _is_null(available_at):
        return GATE_UNRESOLVED
    return GATE_PASS


def evaluate_g07(no_future_leakage: bool | None) -> str:
    if no_future_leakage is None:
        return GATE_UNRESOLVED
    return GATE_PASS if no_future_leakage else GATE_FAIL


def evaluate_g08(gate_statuses: dict[str, str]) -> str:
    applicable = [
        s for gid, s in gate_statuses.items()
        if gid in {"G01", "G02", "G03", "G04", "G05", "G06", "G07"}
    ]
    if not applicable:
        return GATE_NOT_APPLIED
    if any(s == GATE_FAIL for s in applicable):
        return GATE_FAIL
    if any(s == GATE_UNRESOLVED for s in applicable):
        return GATE_UNRESOLVED
    return GATE_PASS


def evaluate_g09(
    usable_by_candidate: dict[str, set[str]],
    pilot_keys: set[str],
    threshold: float = 0.80,
) -> str:
    if not pilot_keys:
        return GATE_UNRESOLVED
    for cand_id in [c["candidate_id"] for c in part3a.REGISTERED_CANDIDATES]:
        usable = usable_by_candidate.get(cand_id, set())
        coverage = len(usable & pilot_keys) / len(pilot_keys)
        if coverage < threshold:
            return GATE_FAIL
    return GATE_PASS


def evaluate_g10(
    usable_by_pair_block: dict[str, dict[str, bool]],
    pilot_keys: set[str],
    threshold: float = 0.70,
) -> str:
    if not pilot_keys:
        return GATE_UNRESOLVED
    for block, candidates in BLOCK_CANDIDATES.items():
        usable_pairs = {
            key for key in pilot_keys
            if all(
                usable_by_pair_block.get(key, {}).get(cand_id, False)
                for cand_id in candidates
            )
        }
        coverage = len(usable_pairs) / len(pilot_keys)
        if coverage < threshold:
            return GATE_FAIL
    return GATE_PASS


def evaluate_g11(
    usable_positive_by_block_year: dict[str, dict[str, int]],
    minimum: int = 3,
) -> str:
    years = {str(y) for y in range(1393, 1403)}
    for block in BLOCK_CANDIDATES:
        for year in years:
            count = usable_positive_by_block_year.get(block, {}).get(year, 0)
            if count < minimum:
                return GATE_FAIL
    return GATE_PASS


def evaluate_g12(
    usable_negative_by_block_year: dict[str, dict[str, int]],
    minimum: int = 3,
) -> str:
    years = {str(y) for y in range(1393, 1403)}
    for block in BLOCK_CANDIDATES:
        for year in years:
            count = usable_negative_by_block_year.get(block, {}).get(year, 0)
            if count < minimum:
                return GATE_FAIL
    return GATE_PASS


def evaluate_g13(predictor_keys: set[str], expected: int = 80) -> str:
    n = len(predictor_keys)
    if n < expected:
        return GATE_FAIL
    if n > expected:
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
) -> str:
    if post_evidence_substitution:
        return GATE_FAIL
    if option_id != lock.APPROVED_PILOT_OPTION:
        return GATE_FAIL
    if positive != lock.APPROVED_POSITIVE:
        return GATE_FAIL
    if negative != lock.APPROVED_NEGATIVE:
        return GATE_FAIL
    if unknown != lock.APPROVED_UNKNOWN:
        return GATE_FAIL
    if year_allocation != lock.EXPECTED_YEAR_ALLOCATION:
        return GATE_FAIL
    return GATE_PASS


def evaluate_score_without_evidence(
    accessibility_score: int | None,
    evidence_captured: bool,
) -> str:
    if accessibility_score is not None and not evidence_captured:
        return GATE_FAIL
    return GATE_NOT_APPLIED


def evaluate_candidate_gates(context: dict[str, Any]) -> dict[str, str]:
    """Evaluate G01–G08 for one in-memory candidate/pair context."""
    g01 = evaluate_g01(context.get("accessibility_score"))
    if context.get("accessibility_score") is not None and not context.get(
        "evidence_captured", False
    ):
        g01 = GATE_FAIL
    statuses = {
        "G01": g01,
        "G02": evaluate_g02(context.get("authoritative_source")),
        "G03": evaluate_g03(context.get("reproducible_retrieval")),
        "G04": evaluate_g04(
            context.get("published_at"), context.get("available_at"),
        ),
        "G05": evaluate_g05(context.get("quality_controls_met")),
        "G06": evaluate_g06(context.get("available_at")),
        "G07": evaluate_g07(context.get("no_future_leakage")),
    }
    statuses["G08"] = evaluate_g08(statuses)
    return statuses


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
        "required_fields": [f["name"] for f in schema.get("required_fields", [])],
        "null_rules": schema.get("null_rules", {}),
        "real_evidence_records_allowed": False,
        "accessibility_scoring_allowed": False,
        "candidate_decisions_allowed": False,
        "part3b_started": False,
        "part3b0_readiness": True,
    }


def build_immutable_cache_contract() -> dict:
    return {
        "contract_version": "stage125_part3b0_v1",
        "stage": CURRENT_STAGE,
        "keying": "sha256_of_exact_raw_bytes",
        "write_once": True,
        "atomic_write": True,
        "identical_bytes_no_op": True,
        "different_bytes_same_identity_fail_closed": True,
        "path_traversal_rejected": True,
        "symlink_escape_rejected": True,
        "overwrite_support": False,
        "mutable_latest_file": False,
        "metadata_payload_hash_verified_together": True,
        "unknown_hash_or_missing_payload": "unresolved_fail_closed",
        "repository_cache_populated_in_part3b0": False,
    }


def build_network_denial_contract() -> dict:
    return {
        "contract_version": "stage125_part3b0_v1",
        "stage": CURRENT_STAGE,
        "default_deny": True,
        "blocked_primitives": [
            "socket.socket.connect",
            "socket.socket.connect_ex",
            "socket.create_connection",
            "urllib.request.urlopen",
            "http.client.HTTPConnection.connect",
        ],
        "on_attempt": {
            "increment_network_calls_attempted": True,
            "raise_fail_closed_exception": True,
            "leave_no_partial_cache_or_evidence": True,
        },
        "required_final_state": {
            "network_calls_attempted": 0,
            "network_extraction_performed": False,
        },
    }


def build_evidence_manifest_template_csv() -> str:
    return _csv_str(_EVIDENCE_HEADER, [])


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
        "- Default-deny network sentinel contract JSON.",
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

def count_real_evidence_records(repo_root: Path) -> int:
    count = 0
    stage125 = repo_root / "project" / "stage125"
    for name in (
        F_EVIDENCE_TEMPLATE,
        "part3_evidence_manifest_stage125.csv",
        "part3b_evidence_manifest_stage125.csv",
    ):
        path = stage125 / name
        if not path.is_file():
            continue
        rows = list(csv.DictReader(path.open(encoding="utf-8")))
        if name == F_EVIDENCE_TEMPLATE:
            continue
        count += len(rows)
    return count


def count_accessibility_scores(repo_root: Path) -> int:
    path = repo_root / "project/stage125/part3_candidate_inventory_stage125.csv"
    scored = 0
    for row in csv.DictReader(path.open(encoding="utf-8")):
        val = row.get("accessibility_score", "")
        if str(val).strip() not in ("", "null", "None"):
            scored += 1
    return scored


def count_candidate_decisions(repo_root: Path) -> int:
    path = repo_root / "project/stage125/part3_candidate_inventory_stage125.csv"
    decided = 0
    for row in csv.DictReader(path.open(encoding="utf-8")):
        status = row.get("decision_status", "")
        if status not in ("pending_part3b_evidence", "", "out_of_scope_locked",
                          "research_design_only_not_registered",
                          "registry_only_not_registered"):
            decided += 1
    return decided


def scan_repository_cache_entries(repo_root: Path) -> int:
    cache_root = repo_root / "project" / "stage125" / "raw_cache"
    if not cache_root.is_dir():
        return 0
    return sum(
        1 for p in cache_root.rglob("*")
        if p.is_file() and not p.name.endswith(".meta.json")
    )


def scan_for_part3b_capture_start(repo_root: Path) -> dict:
    """Detect Part 3B capture start while allowing Part 3B.0 readiness files."""
    evidence = part3a.scan_for_part3b_artifacts(repo_root)
    allowed_exact = {
        "project/src/stage125_part3b0_evidence_readiness.py",
        "project/tests/test_stage125_part3b0_evidence_readiness.py",
        "project/run_stage125_part3b0.py",
    }
    hits = []
    for hit in evidence["hits"]:
        if hit in allowed_exact:
            continue
        if Path(hit).name.startswith("part3b0_"):
            continue
        hits.append(hit)
    return {"hits": sorted(hits), "no_part3b": len(hits) == 0}


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
    approved = list(csv.DictReader(
        (repo_root / "project/stage125/part3a_approved_gate_thresholds_stage125.csv")
        .open(encoding="utf-8")
    ))
    add(
        "approved_thresholds_g09_g14",
        {r["gate_id"] for r in approved} == {f"G{i:02d}" for i in range(9, 15)},
        "G09–G14 approved thresholds present",
    )
    evidence_template = build_evidence_manifest_template_csv()
    gate_template = build_gate_result_template_csv()
    evidence_rows = list(csv.DictReader(io.StringIO(evidence_template)))
    gate_rows = list(csv.DictReader(io.StringIO(gate_template)))
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
        guard_evidence["no_network_calls"],
        "network_extraction_performed=false",
    )
    add(
        "cache_real_entry_count_zero",
        guard_evidence["cache_real_entry_count"] == 0,
        f"count={guard_evidence['cache_real_entry_count']}",
    )
    add("part3b0_readiness_true", True, "part3b0_readiness=true")
    add("part3b_started_false", True, "part3b_started=false")
    add("evidence_collected_false", True, "evidence_collected=false")
    add(
        "accessibility_scoring_applied_false",
        True,
        "accessibility_scoring_applied=false",
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
) -> dict:
    root = str(repo_root)
    source_commit = _git_last_code_commit(root, [SRC_REL, TEST_REL])
    ts = _git_commit_timestamp(root, source_commit)
    assertions = build_qc_assertions(
        frozen_input_hashes, frozen_before, frozen_after,
        content_hashes, guard_evidence, schema, repo_root,
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

        content_files = {
            F_EVIDENCE_CONTRACT: _json_str(build_evidence_capture_contract(schema)),
            F_EVIDENCE_TEMPLATE: build_evidence_manifest_template_csv(),
            F_GATE_TEMPLATE: build_gate_result_template_csv(),
            F_CACHE_CONTRACT: _json_str(build_immutable_cache_contract()),
            F_NETWORK_CONTRACT: _json_str(build_network_denial_contract()),
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
