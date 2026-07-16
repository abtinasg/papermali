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
import os
import re
import shutil
import socket
import subprocess
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
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

# Curated exact-path allowlist only (no prefix / directory-wide bypass).
PART3B0_ALLOWED_EXACT = frozenset({
    SRC_REL,
    TEST_REL,
    "project/run_stage125_part3b0.py",
    f"project/stage125/{F_EVIDENCE_CONTRACT}",
    f"project/stage125/{F_EVIDENCE_TEMPLATE}",
    f"project/stage125/{F_GATE_TEMPLATE}",
    f"project/stage125/{F_CACHE_CONTRACT}",
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

_NETWORK_BLOCKED_BINARIES = frozenset({
    "curl", "wget", "nc", "ncat", "netcat", "ssh", "scp", "sftp", "telnet",
    "ftp", "fetch", "http", "https",
})
_GIT_ALLOWED_SUBCOMMANDS = frozenset({
    "rev-parse", "merge-base", "log", "show", "status", "diff", "ls-files",
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
    if not cmd:
        return False
    prog = Path(cmd[0]).name.lower()
    if prog != "git":
        return False
    args = cmd[1:]
    if args and args[0] == "-C" and len(args) >= 2:
        args = args[2:]
    while args and args[0].startswith("-"):
        # allow only harmless global flags before subcommand
        if args[0] in {"--no-pager", "--literal-pathspecs"}:
            args = args[1:]
            continue
        return False
    if not args:
        return False
    return args[0] in _GIT_ALLOWED_SUBCOMMANDS


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


def load_locked_gate_policy(repo_root: Path) -> LockedGatePolicy:
    """Load G09–G14 policy exclusively from hash-verified frozen artifacts."""
    verified = verify_frozen_input_hashes(repo_root)
    thr_rel = "project/stage125/part3a_approved_gate_thresholds_stage125.csv"
    lock_rel = "project/stage125/part3a_decision_lock_stage125.json"
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
    years = tuple(sorted(lock.EXPECTED_YEAR_ALLOCATION.keys()))
    policy = LockedGatePolicy(
        g09_threshold=_float("G09"),
        g10_threshold=_float("G10"),
        g11_minimum=_int("G11"),
        g12_minimum=_int("G12"),
        g13_expected=_int("G13"),
        g14_option_id=g14_option,
        target_years=years,
        source_thresholds_sha256=verified[thr_rel],
        source_decision_lock_sha256=verified[lock_rel],
    )
    if policy.g09_threshold != 0.80:
        raise QCFail("locked G09 threshold drift")
    if policy.g10_threshold != 0.70:
        raise QCFail("locked G10 threshold drift")
    if policy.g11_minimum != 3 or policy.g12_minimum != 3:
        raise QCFail("locked G11/G12 minimum drift")
    if policy.g13_expected != 80:
        raise QCFail("locked G13 expected drift")
    return policy


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
        self._module_patches: list[tuple[Any, str, Any]] = []

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
            return [os.fsdecode(args)]
        return [os.fsdecode(a) if isinstance(a, (bytes, os.PathLike)) else str(a)
                for a in args]

    def _guard_subprocess(self, label: str, popenargs: Any):
        cmd = self._normalize_cmd(popenargs)
        if _is_allowed_git_command(cmd):
            return
        prog = Path(cmd[0]).name.lower() if cmd else ""
        if prog in _NETWORK_BLOCKED_BINARIES or prog.endswith(".exe") and (
            Path(prog).stem.lower() in _NETWORK_BLOCKED_BINARIES
        ):
            self._blocked(label, *cmd)
        # Default-deny other external network-capable tools by binary name only;
        # do not create a broad subprocess allowance.
        if prog in _NETWORK_BLOCKED_BINARIES:
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
            if args:
                sentinel._guard_subprocess("subprocess.run", args[0])
            return sentinel._orig_subprocess_run(*args, **kwargs)

        class _Popen(subprocess.Popen):
            def __init__(self, *args, **kwargs):
                if args:
                    sentinel._guard_subprocess("subprocess.Popen", args[0])
                super().__init__(*args, **kwargs)

        subprocess.run = _run  # type: ignore[assignment]
        subprocess.Popen = _Popen  # type: ignore[misc,assignment]

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


class ImmutableCache:
    """Content-addressed, write-once immutable cache with atomic entry commit."""

    _PAYLOAD_NAME = "payload.bin"
    _META_NAME = "metadata.json"
    _META_HASH_NAME = "metadata.sha256"
    _ENTRY_FILES = frozenset({_PAYLOAD_NAME, _META_NAME, _META_HASH_NAME})

    def __init__(self, root: Path) -> None:
        raw = Path(root)
        if raw.exists() and raw.is_symlink():
            raise ImmutableCacheError("symlink components rejected")
        self.root = raw.resolve()
        if self.root.exists() and self.root.is_symlink():
            raise ImmutableCacheError("symlink components rejected")
        self.root.mkdir(parents=True, exist_ok=True)
        self._assert_no_symlink_components(self.root, self.root)

    def _assert_no_symlink_components(self, path: Path, root: Path) -> None:
        path = Path(path)
        root = Path(root).resolve()
        try:
            rel = path.resolve()
        except OSError as exc:
            raise ImmutableCacheError("path resolution failed") from exc
        if path.exists() and path.is_symlink():
            raise ImmutableCacheError("symlink components rejected")
        current = root
        if current.is_symlink():
            raise ImmutableCacheError("symlink components rejected")
        try:
            parts = Path(rel).relative_to(root).parts
        except ValueError:
            # path is root itself
            return
        for part in parts:
            current = current / part
            if current.exists() and current.is_symlink():
                raise ImmutableCacheError("symlink components rejected")

    def _entry_dir(self, content_hash: str) -> Path:
        if not SHA256_RE.match(content_hash):
            raise ImmutableCacheError(f"invalid content hash: {content_hash}")
        rel = Path(content_hash[:2]) / content_hash
        target = (self.root / rel).resolve()
        if not str(target).startswith(str(self.root) + os.sep):
            raise ImmutableCacheError("path traversal rejected")
        self._assert_no_symlink_components(target, self.root)
        return target

    def _canonical_metadata_bytes(
        self, content_hash: str, metadata: dict[str, Any] | None,
    ) -> bytes:
        meta = dict(metadata or {})
        meta["content_sha256"] = content_hash
        # metadata_sha256 is stored separately; never embed into canonical bytes
        meta.pop("metadata_sha256", None)
        return json.dumps(meta, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )

    def _read_complete_entry(self, entry_dir: Path) -> tuple[bytes, bytes, str]:
        if not entry_dir.is_dir() or entry_dir.is_symlink():
            raise ImmutableCacheError("unknown hash or incomplete entry")
        self._assert_no_symlink_components(entry_dir, self.root)
        names = {p.name for p in entry_dir.iterdir()}
        if names != self._ENTRY_FILES:
            raise ImmutableCacheError(
                "entry must contain exactly payload, metadata, and metadata hash"
            )
        for name in self._ENTRY_FILES:
            path = entry_dir / name
            if path.is_symlink() or not path.is_file():
                raise ImmutableCacheError("symlink or non-file entry component")
        payload = (entry_dir / self._PAYLOAD_NAME).read_bytes()
        meta_bytes = (entry_dir / self._META_NAME).read_bytes()
        meta_hash_text = (
            (entry_dir / self._META_HASH_NAME).read_text(encoding="utf-8").strip()
        )
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

    def put(
        self,
        data: bytes,
        metadata: dict[str, Any] | None = None,
        *,
        _inject_failure: str | None = None,
    ) -> CachePutResult:
        content_hash = sha256_bytes(data)
        entry_dir = self._entry_dir(content_hash)
        meta_bytes = self._canonical_metadata_bytes(content_hash, metadata)
        meta_hash = sha256_bytes(meta_bytes)
        result = CachePutResult(
            payload_sha256=content_hash, metadata_sha256=meta_hash,
        )

        if entry_dir.exists():
            if self._entry_matches(entry_dir, data, meta_bytes, meta_hash):
                return result
            # Same payload identity with different canonical metadata, or
            # corrupt/partial existing entry: fail closed (no overwrite).
            raise ImmutableCacheError(
                f"immutable entry conflict for {content_hash}"
            )

        parent = entry_dir.parent
        parent.mkdir(parents=True, exist_ok=True)
        self._assert_no_symlink_components(parent, self.root)
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
            # Atomic commit: directory rename fails if destination exists (no
            # overwrite of an accepted entry during a race).
            try:
                os.rename(staging, entry_dir)
            except OSError as exc:
                if entry_dir.exists() and self._entry_matches(
                    entry_dir, data, meta_bytes, meta_hash,
                ):
                    # Lost race to identical writer: treat as no-op.
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

    def get(self, content_hash: str) -> bytes:
        entry_dir = self._entry_dir(content_hash)
        # Reject orphans / sibling partials sharing the hash prefix directory.
        parent = entry_dir.parent
        if parent.is_dir():
            siblings = [
                p for p in parent.iterdir()
                if p.name == content_hash or p.name.startswith(content_hash)
            ]
            complete = [
                p for p in siblings
                if p.is_dir() and not p.is_symlink() and p.name == content_hash
            ]
            staging_orphans = [
                p for p in siblings
                if p.name.startswith(f".staging-{content_hash[:16]}")
            ]
            if staging_orphans:
                raise ImmutableCacheError("orphan/partial staging entry present")
            if len(complete) != 1:
                raise ImmutableCacheError(
                    "unknown hash or not exactly one complete entry"
                )
            extras = [p for p in siblings if p not in complete]
            if extras:
                raise ImmutableCacheError("duplicate or partial entry artifacts")

        payload, meta_bytes, meta_hash_text = self._read_complete_entry(entry_dir)
        if sha256_bytes(payload) != content_hash:
            raise ImmutableCacheError(f"payload hash mismatch for {content_hash}")
        if not SHA256_RE.match(meta_hash_text):
            raise ImmutableCacheError("malformed metadata hash seal")
        if sha256_bytes(meta_bytes) != meta_hash_text:
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

    def has(self, content_hash: str) -> bool:
        try:
            self.get(content_hash)
        except ImmutableCacheError:
            return False
        return True

    def entry_count(self) -> int:
        count = 0
        if not self.root.is_dir():
            return 0
        for shard in self.root.iterdir():
            if not shard.is_dir() or shard.is_symlink():
                continue
            for entry in shard.iterdir():
                if not entry.is_dir() or entry.is_symlink():
                    continue
                if entry.name.startswith(".staging-"):
                    continue
                try:
                    self.get(entry.name)
                except ImmutableCacheError:
                    continue
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
        root = Path(allowed_snapshot_root).resolve()
        candidate = Path(snap)
        if not candidate.is_absolute():
            candidate = (root / candidate).resolve()
        else:
            candidate = candidate.resolve()
        if not str(candidate).startswith(str(root) + os.sep) and candidate != root:
            raise EvidenceValidationError(
                "snapshot path must be confined to allowed_snapshot_root"
            )


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
        value = record.get(name)
        if name not in record and not nullable:
            raise EvidenceValidationError(f"missing non-nullable field: {name}")
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
    if set(gate_statuses.keys()) != set(G01_G07):
        return GATE_FAIL
    for status in gate_statuses.values():
        if status not in ALLOWED_GATE_STATUSES:
            return GATE_FAIL
    if any(s == GATE_FAIL for s in gate_statuses.values()):
        return GATE_FAIL
    if any(s == GATE_UNRESOLVED for s in gate_statuses.values()):
        return GATE_UNRESOLVED
    if any(s == GATE_NOT_APPLIED for s in gate_statuses.values()):
        return GATE_FAIL
    return GATE_PASS


def evaluate_g09(
    usable_by_candidate: dict[str, set[str]],
    pilot_keys: set[str],
    policy: LockedGatePolicy,
) -> str:
    if not pilot_keys:
        return GATE_UNRESOLVED
    registered = [c["candidate_id"] for c in part3a.REGISTERED_CANDIDATES]
    if len(registered) != 10:
        return GATE_FAIL
    for cand_id in registered:
        usable = usable_by_candidate.get(cand_id, set())
        coverage = len(usable & pilot_keys) / len(pilot_keys)
        if coverage < policy.g09_threshold:
            return GATE_FAIL
    return GATE_PASS


def evaluate_g10(
    usable_by_pair_block: dict[str, dict[str, bool]],
    pilot_keys: set[str],
    policy: LockedGatePolicy,
) -> str:
    if not pilot_keys:
        return GATE_UNRESOLVED
    for block, candidates in BLOCK_CANDIDATES.items():
        if not candidates:
            return GATE_FAIL
        usable_pairs = {
            key for key in pilot_keys
            if all(
                usable_by_pair_block.get(key, {}).get(cand_id, False)
                for cand_id in candidates
            )
        }
        coverage = len(usable_pairs) / len(pilot_keys)
        if coverage < policy.g10_threshold:
            return GATE_FAIL
    return GATE_PASS


def evaluate_g11(
    usable_positive_by_block_year: dict[str, dict[str, int]],
    policy: LockedGatePolicy,
) -> str:
    for block in BLOCK_CANDIDATES:
        for year in policy.target_years:
            count = usable_positive_by_block_year.get(block, {}).get(year, 0)
            if count < policy.g11_minimum:
                return GATE_FAIL
    return GATE_PASS


def evaluate_g12(
    usable_negative_by_block_year: dict[str, dict[str, int]],
    policy: LockedGatePolicy,
) -> str:
    for block in BLOCK_CANDIDATES:
        for year in policy.target_years:
            count = usable_negative_by_block_year.get(block, {}).get(year, 0)
            if count < policy.g12_minimum:
                return GATE_FAIL
    return GATE_PASS


def evaluate_g13(predictor_keys: set[str], policy: LockedGatePolicy) -> str:
    n = len(predictor_keys)
    if n != policy.g13_expected:
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
) -> str:
    if post_evidence_substitution:
        return GATE_FAIL
    if option_id != policy.g14_option_id:
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
    accessibility_score: Any,
    evidence_captured: bool,
) -> str:
    if accessibility_score is not None and not evidence_captured:
        return GATE_FAIL
    return GATE_NOT_APPLIED


def evaluate_candidate_gates(context: dict[str, Any]) -> dict[str, str]:
    """Evaluate G01–G08 for one in-memory candidate/pair context."""
    score = context.get("accessibility_score")
    evidence_captured = bool(context.get("evidence_captured", False))
    if score is not None and not evidence_captured:
        g01 = GATE_FAIL
    else:
        g01 = evaluate_g01(score)
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
        "metadata_payload_linkage_verified_on_get": True,
        "exactly_one_complete_entry_required": True,
        "path_traversal_rejected": True,
        "symlink_components_rejected": True,
        "orphan_partial_entries_fail_closed": True,
        "malformed_metadata_json_fail_closed": True,
        "overwrite_support": False,
        "mutable_latest_file": False,
        "unknown_hash_or_missing_payload": "unresolved_fail_closed",
        "repository_cache_populated_in_part3b0": False,
        "put_returns_payload_and_metadata_sha256": True,
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
            "socket.socket.sendto",
            "socket.socket.sendmsg",
            "socket.getaddrinfo",
            "socket.gethostbyname",
            "urllib.request.urlopen",
            "urllib.request.urlretrieve",
            "http.client.HTTPConnection.connect",
            "http.client.HTTPSConnection.connect",
            "subprocess:curl|wget|nc|ssh",
        ],
        "exact_git_readonly_allowlist": sorted(_GIT_ALLOWED_SUBCOMMANDS),
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
        rel = str(path.relative_to(repo_root))
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
    count = 0
    stage125 = repo_root / "project" / "stage125"
    if not stage125.is_dir():
        return 0
    for path in stage125.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        parts = {p.lower() for p in path.relative_to(stage125).parts}
        if parts & CACHE_DIR_NAMES:
            if path.name.endswith(".meta.json") or path.name == "metadata.sha256":
                continue
            count += 1
    return count


def _is_unauthorized_part3b_path(rel: str, path: Path) -> bool:
    if rel in PART3B0_ALLOWED_EXACT:
        return False
    # Allow the frozen Part 3A evidence *schema* only.
    if rel in part3a.PART3B_ALLOWED_EXACT:
        return False
    low_name = path.name.lower()
    low_rel = rel.lower().replace("\\", "/")
    if any(low_name.startswith(p) for p in UNAUTHORIZED_NAME_PREFIXES):
        return True
    if any(marker in low_name for marker in UNAUTHORIZED_NAME_SUFFIX_MARKERS):
        return True
    if any(low_rel.startswith(p) for p in part3a.PART3B_FORBIDDEN_PREFIXES):
        return True
    if rel in part3a.PART3B_FORBIDDEN_EXACT:
        return True
    if any(tok in low_name for tok in EVIDENCE_NAME_TOKENS) and (
        path.suffix.lower() in EVIDENCE_SCAN_SUFFIXES
        or path.suffix.lower() in {".bin", ".raw", ".snapshot"}
    ):
        # Avoid flagging frozen Part 3A/3A.1 contract filenames that mention
        # evidence only as schema/protocol vocabulary.
        frozen_ok = {
            "part3_source_evidence_manifest_schema_stage125.json",
            "part3_gate_decision_protocol_stage125.csv",
            "part3a_approved_gate_thresholds_stage125.csv",
            "part3a_decision_lock_stage125.json",
            "part3a_selected_pilot_pairs_stage125.csv",
            "part3_candidate_inventory_stage125.csv",
            "accessibility_scoring_rubric_stage125_part3a.json",
            "stage125_part3a_decision_lock_qc_report.json",
            "metadata_and_hashes_stage125_part3a_decision_lock.json",
            "stage125_part3a_pilot_protocol_qc_report.json",
            "metadata_and_hashes_stage125_part3a.json",
            "README_STAGE125_PART3A_DECISION_LOCK.md",
            "README_STAGE125_PART3A_PILOT_PROTOCOL.md",
        }
        if path.name in frozen_ok:
            return False
        if "schema" in low_name and "part3_source_evidence" in low_name:
            return False
        # part3a decision-lock assets are frozen protocol, not Part 3B capture.
        if "part3a_decision" in low_name or "part3a_pilot" in low_name:
            return False
        if "part3_gate_decision_protocol" in low_name:
            return False
        return True
    parts = {p.lower() for p in Path(rel).parts}
    if parts & CACHE_DIR_NAMES:
        return True
    return False


def scan_for_part3b_capture_start(repo_root: Path) -> dict:
    """Recursively detect unauthorized Part 3B/evidence/scoring/decision/cache files."""
    hits: list[str] = []
    for rel in part3a.PART3B_FORBIDDEN_EXACT:
        if (repo_root / rel).exists() and rel not in PART3B0_ALLOWED_EXACT:
            hits.append(rel)
    scan_roots = [
        repo_root / "project" / "stage125",
        repo_root / "project" / "src",
        repo_root / "project" / "tests",
    ]
    for base in scan_roots:
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            rel = str(path.relative_to(repo_root))
            if _is_unauthorized_part3b_path(rel, path):
                hits.append(rel)
    for prefix in part3a.PART3B_FORBIDDEN_PREFIXES:
        root = repo_root / prefix
        if root.is_dir():
            for path in root.rglob("*"):
                if path.is_file():
                    rel = str(path.relative_to(repo_root))
                    if rel not in PART3B0_ALLOWED_EXACT:
                        hits.append(rel)
    return {"hits": sorted(set(hits)), "no_part3b": len(set(hits)) == 0}


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
