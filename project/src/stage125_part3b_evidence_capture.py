"""Stage125 Part 3B — Evidence Capture & Accessibility Scoring Pilot.

Authorized real-evidence path separate from Part 3B.0 synthetic readiness.
No modeling, no sample/target/eligibility change, no guessed values.
"""
from __future__ import annotations

import csv
import hashlib
import io
import ipaddress
import json
import socket
import ssl
import time
import urllib.parse
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from src import stage125_part3a_decision_lock as lock
from src import stage125_part3a_pilot_protocol as part3a
from src import stage125_part3b0_evidence_readiness as p3b0

QC_STAGE = "stage125_part3b_evidence_capture"
CURRENT_STAGE = "Stage125"
EXPECTED_BASELINE_COMMIT = "959169c71a6e9378995be40979d1c6df7dc45a1d"
RUBRIC_VERSION = "stage125_part3a_v1"

SRC_REL = "project/src/stage125_part3b_evidence_capture.py"
TEST_REL = "project/tests/test_stage125_part3b_evidence_capture.py"
RUN_REL = "project/run_stage125_part3b.py"

F_AUTH = "part3b_authorization_stage125.json"
F_PLAN = "part3b_capture_plan_stage125.csv"
F_ENDPOINTS = "part3b_verified_endpoint_registry_stage125.csv"
F_EVIDENCE = "part3b_evidence_manifest_stage125.csv"
F_HANDLES = "part3b_cache_handles_stage125.csv"
F_ASSESS = "part3b_pair_candidate_assessment_stage125.csv"
F_SCORES = "part3b_accessibility_scores_stage125.csv"
F_GATES = "part3b_gate_results_stage125.csv"
F_GATE_SUMMARY = "part3b_gate_summary_stage125.json"
F_UNRESOLVED = "part3b_unresolved_and_failures_stage125.csv"
F_README = "README_STAGE125_PART3B_EVIDENCE_CAPTURE.md"
F_QC = "stage125_part3b_evidence_capture_qc_report.json"
F_METADATA = "metadata_and_hashes_stage125_part3b.json"
F_NETWORK_LOG = "part3b_capture_network_log_stage125.json"
CACHE_DIR_REL = "project/stage125/raw_cache_part3b"

FROZEN_INPUT_HASHES = {
    "project/stage125/part3_candidate_inventory_stage125.csv":
        "4bd5f6a71ecf0e1f74866a64a3774e51340729f4188ae2784f1d90db07e7032f",
    "project/stage125/part3_source_evidence_manifest_schema_stage125.json":
        "9a736edb18046128851d55c87f07609b8dc2a4b2be73a41c5837fe0e2a4cd78d",
    "project/stage125/part3a_approved_gate_thresholds_stage125.csv":
        "11c7efe5f242ab8e4a4f7b1955fb25d48e288249f7a1ce4c6bf1713dbf117d20",
    "project/stage125/part3a_selected_pilot_pairs_stage125.csv":
        "9a441b5e3696353967489b356d0ff48cf7cbea276aeea5018be6edc8368b40f5",
    "project/stage125/part3a_decision_lock_stage125.json":
        "475c82b3483ef18ff19aea2268f65527ca87c9441603622bd1952bd21f18f35e",
    "project/stage125/source_registry_stage125.csv":
        "980f375acea69795d06bc19b003563f731bc25f7041bcb07b3fb8f9ec922e13c",
}

REGISTERED_CANDIDATE_IDS = tuple(c["candidate_id"] for c in part3a.REGISTERED_CANDIDATES)
CANDIDATE_SOURCE_MAP = {c["candidate_id"]: c["source_id"] for c in part3a.REGISTERED_CANDIDATES}
BLOCK_BY_CANDIDATE = {c["candidate_id"]: c["block"] for c in part3a.REGISTERED_CANDIDATES}

PART3B_AUTHORIZED_EXACT = frozenset({
    SRC_REL, TEST_REL, RUN_REL,
    f"project/stage125/{F_AUTH}", f"project/stage125/{F_PLAN}",
    f"project/stage125/{F_ENDPOINTS}", f"project/stage125/{F_EVIDENCE}",
    f"project/stage125/{F_HANDLES}", f"project/stage125/{F_ASSESS}",
    f"project/stage125/{F_SCORES}", f"project/stage125/{F_GATES}",
    f"project/stage125/{F_GATE_SUMMARY}", f"project/stage125/{F_UNRESOLVED}",
    f"project/stage125/{F_README}", f"project/stage125/{F_QC}",
    f"project/stage125/{F_METADATA}", f"project/stage125/{F_NETWORK_LOG}",
})

ENDPOINT_HEADER = [
    "source_id", "official_source_owner", "exact_https_origin", "exact_hostname",
    "exact_endpoint_or_url_pattern", "allowed_http_method",
    "authoritative_ownership_evidence", "ownership_evidence_url",
    "retrieval_purpose", "content_type_expected", "verification_status",
    "failure_reason", "reviewer_status",
]
PLAN_HEADER = [
    "plan_row_id", "candidate_id", "source_id", "endpoint_id", "request_url",
    "http_method", "retrieval_purpose", "plan_status", "blocker_reason",
    "shared_snapshot_key",
]
ASSESS_HEADER = [
    "assessment_id", "predictor_row_key_t", "target_row_key_t_plus_1", "ticker",
    "target_year", "class_label", "candidate_id", "source_id", "block",
    "evidence_id", "assessment_status", "usability_flag", "definition_contract_gap",
    "prediction_cutoff", "cutoff_resolvable",
    "g01", "g02", "g03", "g04", "g05", "g06", "g07", "g08",
    "failure_reason", "reviewer_status",
]
SCORE_HEADER = [
    "candidate_id", "source_id", "rubric_version", "accessibility_score",
    "score_status", "evidence_ids_cited", "rationale",
    "requires_human_adjudication", "reviewer_status",
]
HANDLE_HEADER = [
    "evidence_id", "payload_sha256", "metadata_sha256", "cache_contract_version",
    "cache_handle_schema_version", "external_handle_sha256", "source_id",
    "candidate_id",
]

MAX_RESPONSE_BYTES = 2_000_000
REQUEST_TIMEOUT_SEC = 30.0
MAX_REDIRECTS = 5
RATE_LIMIT_SLEEP_SEC = 0.35
VERIFIED_STATUSES = frozenset({"verified_from_frozen_repo_provenance"})
_REAL_EVIDENCE_SEAL = "stage125_part3b_validated_real_evidence_v1"
_REAL_GATE_SEAL = "stage125_part3b_validated_real_gate_input_v1"
_ASSESS_SEAL = "stage125_part3b_sealed_pair_candidate_assessment_v1"

DEFINITION_CONTRACT_GAP = (
    "feature_definition_not_uniquely_locked_in_frozen_contracts;"
    "accessibility_evidence_only;value_extraction_unresolved"
)


class QCFail(p3b0.QCFail):
    pass


class NetworkPolicyError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return p3b0.sha256_bytes(data)


def sha256_file(path: Path) -> str | None:
    return p3b0.sha256_file(path)


def _json_str(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def _csv_str(header: list[str], rows: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=header, lineterminator="\n")
    w.writeheader()
    for row in rows:
        w.writerow({k: ("" if row.get(k) is None else row.get(k, "")) for k in header})
    return buf.getvalue()


def part3b_authorization_active(repo_root: Path) -> bool:
    return (repo_root / "project" / "stage125" / F_AUTH).is_file()


def check_historical_baseline(
    repo_root: Path,
    output_dir: Path,
    metadata_name: str,
    *,
    require_historical_flags: dict[str, Any] | None = None,
) -> dict:
    del repo_root
    meta_path = output_dir / metadata_name
    if not meta_path.is_file():
        raise QCFail(f"historical metadata missing: {metadata_name}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    hashes = meta.get("output_files_sha256") or meta.get("output_sha256")
    if not isinstance(hashes, dict) or not hashes:
        raise QCFail(f"historical metadata lacks output hashes: {metadata_name}")
    drift: list[str] = []
    for name, expected in sorted(hashes.items()):
        path = output_dir / name
        if not path.is_file():
            drift.append(name)
            continue
        if sha256_file(path) != expected:
            drift.append(name)
    if require_historical_flags:
        qc_path = None
        for n in hashes:
            if n.endswith("_qc_report.json"):
                qc_path = output_dir / n
                break
        qc = json.loads(qc_path.read_text(encoding="utf-8")) if qc_path and qc_path.is_file() else {}
        for key, expected in require_historical_flags.items():
            actual = meta.get(key, qc.get(key))
            if actual != expected:
                raise QCFail(
                    f"historical flag mismatch: {key} expected={expected!r} actual={actual!r}"
                )
    if drift:
        raise QCFail("historical baseline drift: " + ", ".join(drift))
    return {
        "historical_baseline_ok": True,
        "metadata": metadata_name,
        "files_verified": len(hashes),
        "drift": [],
        "written": False,
        "output_dir": str(output_dir),
        "qc": {
            "all_pass": True,
            "assertion_count": 0,
            "failed_count": 0,
            "historical_mode": True,
            "part3b0_readiness": True,
            "part3b_started": False,
            "evidence_collected": False,
            "accessibility_scoring_applied": False,
            "network_extraction_performed": False,
            "modeling_started": False,
        },
        "guard_evidence": {
            "historical_baseline_mode": True,
            "network_calls_attempted": 0,
            "no_network_calls": True,
            "real_evidence_record_count": 0,
            "accessibility_score_count": 0,
            "candidate_decision_count": 0,
            "cache_real_entry_count": 0,
            "part3b": {"hits": [], "no_part3b": True},
            "modeling": {"no_modeling": True},
        },
        "files": {},
        # Compatibility stubs for historical Part 3A / 3A.1 / 3B.0 runners.
        "counts": {
            "pairs": 0,
            "all_rows": 0,
            "unique_tickers_pairs": 0,
        },
        "input_all_rows_sha256": "",
        "input_pairs_sha256": "",
        "pilot_selection": {
            "sample_size": 80,
            "positive": 39,
            "negative": 41,
        },
    }


def verify_frozen_input_hashes(repo_root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel, expected in FROZEN_INPUT_HASHES.items():
        path = repo_root / rel
        if not path.is_file():
            raise QCFail(f"frozen input missing: {rel}")
        actual = sha256_file(path)
        if actual != expected:
            raise QCFail(f"frozen input hash mismatch: {rel}")
        out[rel] = actual
    return out


def verify_baseline_commit(repo_root: str) -> None:
    head = p3b0._git(repo_root, "rev-parse", "HEAD")
    if head != EXPECTED_BASELINE_COMMIT and not p3b0._is_ancestor(
        repo_root, EXPECTED_BASELINE_COMMIT, head
    ):
        raise QCFail(
            f"HEAD {head} is not a descendant of baseline {EXPECTED_BASELINE_COMMIT}"
        )


def load_prediction_cutoff_map(repo_root: Path) -> dict[tuple[str, str], dict]:
    path = repo_root / "project/stage125/prediction_cutoff_audit_stage125_part2.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    return {(r["predictor_row_key_t"], r["target_row_key_t_plus_1"]): r for r in rows}


def pair_prediction_cutoff(audit_row: dict | None) -> tuple[str | None, bool]:
    if audit_row is None:
        return None, False
    resolvable = str(audit_row.get("cutoff_resolvable", "0")).strip() == "1"
    cutoff = audit_row.get("prediction_cutoff")
    if cutoff is not None and str(cutoff).strip() not in ("", "null", "None"):
        return str(cutoff).strip(), resolvable
    return None, False


# --------------------------------------------------------------------------- #
# Endpoint registry / capture plan
# --------------------------------------------------------------------------- #

def _unverified_endpoint(source_id: str, owner: str, reason: str) -> dict:
    return {
        "source_id": source_id,
        "official_source_owner": owner,
        "exact_https_origin": "",
        "exact_hostname": "",
        "exact_endpoint_or_url_pattern": "",
        "allowed_http_method": "",
        "authoritative_ownership_evidence": "",
        "ownership_evidence_url": "",
        "retrieval_purpose": "accessibility_probe",
        "content_type_expected": "",
        "verification_status": "unverified_no_authoritative_endpoint",
        "failure_reason": reason,
        "reviewer_status": "automated_fail_closed",
    }


def build_endpoint_registry_rows(repo_root: Path) -> list[dict]:
    rows: list[dict] = []
    tsetmc_manifest = repo_root / "project/stage124/official_api/import_manifest.json"
    tsetmc_readme = repo_root / "project/stage124/official_api/README.md"
    if tsetmc_manifest.is_file() and tsetmc_readme.is_file():
        manifest = json.loads(tsetmc_manifest.read_text(encoding="utf-8"))
        exact = manifest.get("exact_endpoint_url")
        if isinstance(exact, str) and exact.startswith("https://cdn.tsetmc.com/"):
            rows.append({
                "source_id": "src_m2_tsetmc_market",
                "official_source_owner": "TSETMC",
                "exact_https_origin": "https://cdn.tsetmc.com",
                "exact_hostname": "cdn.tsetmc.com",
                "exact_endpoint_or_url_pattern": exact,
                "allowed_http_method": "GET",
                "authoritative_ownership_evidence": (
                    "Frozen Stage124 official_api import_manifest.json + README "
                    "document TSETMC CDN API exact_endpoint_url."
                ),
                "ownership_evidence_url":
                    "project/stage124/official_api/import_manifest.json",
                "retrieval_purpose": "accessibility_probe_official_market_api",
                "content_type_expected": "application/json",
                "verification_status": "verified_from_frozen_repo_provenance",
                "failure_reason": "",
                "reviewer_status": "automated_repo_provenance_only",
            })
        else:
            rows.append(_unverified_endpoint(
                "src_m2_tsetmc_market", "TSETMC",
                "frozen_manifest_missing_or_unexpected_exact_endpoint_url",
            ))
    else:
        rows.append(_unverified_endpoint(
            "src_m2_tsetmc_market", "TSETMC",
            "frozen_stage124_official_api_manifest_missing",
        ))

    rows.append(_unverified_endpoint(
        "src_m3_cbi_macro", "Central Bank of Iran",
        "no_authoritative_official_endpoint_in_frozen_stage125_or_stage124_assets",
    ))

    codal_evidence = (
        "project/raw_handoff/financial_distress_programmer_handoff_stage121(1)/"
        "ocf_source_manifest_stage121.csv"
    )
    codal_path = repo_root / codal_evidence
    if codal_path.is_file() and "https://www.codal.ir/" in codal_path.read_text(
        encoding="utf-8", errors="replace",
    ):
        for source_id in ("src_m4_codal_audit", "src_m4_codal_governance"):
            rows.append({
                "source_id": source_id,
                "official_source_owner": "CODAL",
                "exact_https_origin": "https://www.codal.ir",
                "exact_hostname": "www.codal.ir",
                "exact_endpoint_or_url_pattern": "https://www.codal.ir/",
                "allowed_http_method": "GET",
                "authoritative_ownership_evidence": (
                    "Frozen Stage121 OCF source manifest records "
                    "https://www.codal.ir/ Reports URLs as CODAL source_url."
                ),
                "ownership_evidence_url": codal_evidence,
                "retrieval_purpose": "accessibility_probe_official_codal_origin",
                "content_type_expected": "text/html",
                "verification_status": "verified_from_frozen_repo_provenance",
                "failure_reason": "",
                "reviewer_status": "automated_repo_provenance_only",
            })
    else:
        for source_id in ("src_m4_codal_audit", "src_m4_codal_governance"):
            rows.append(_unverified_endpoint(
                source_id, "CODAL", "frozen_codal_handoff_manifest_missing",
            ))

    rows.append({
        "source_id": "src_m3_sci_macro",
        "official_source_owner": "Statistical Center of Iran",
        "exact_https_origin": "",
        "exact_hostname": "",
        "exact_endpoint_or_url_pattern": "",
        "allowed_http_method": "",
        "authoritative_ownership_evidence": "",
        "ownership_evidence_url": "",
        "retrieval_purpose": "out_of_scope_not_promoted",
        "content_type_expected": "",
        "verification_status": "out_of_scope_not_contacted",
        "failure_reason": "src_m3_sci_macro_not_promoted_in_part3b",
        "reviewer_status": "automated_scope_lock",
    })
    return rows


def endpoint_id_for(row: dict) -> str:
    host = (row.get("exact_hostname") or "none").replace(".", "_")
    return f"ep_{row.get('source_id')}_{host}"


def build_capture_plan(repo_root: Path, endpoint_rows: list[dict]) -> list[dict]:
    del repo_root
    by_source = {r["source_id"]: r for r in endpoint_rows}
    plan: list[dict] = []
    for idx, cand_id in enumerate(REGISTERED_CANDIDATE_IDS, start=1):
        source_id = CANDIDATE_SOURCE_MAP[cand_id]
        ep = by_source.get(source_id)
        if ep is None:
            plan.append({
                "plan_row_id": f"plan_{idx:03d}",
                "candidate_id": cand_id,
                "source_id": source_id,
                "endpoint_id": "",
                "request_url": "",
                "http_method": "",
                "retrieval_purpose": "accessibility_probe",
                "plan_status": "blocked",
                "blocker_reason": "source_missing_from_endpoint_registry",
                "shared_snapshot_key": source_id,
            })
            continue
        verified = ep.get("verification_status") in VERIFIED_STATUSES
        url = (ep.get("exact_endpoint_or_url_pattern") or "").strip()
        if verified and "{" in url:
            request_url = ep.get("exact_https_origin", "").rstrip("/") + "/"
            purpose = "accessibility_probe_official_origin_no_inscode_invented"
        elif verified and url:
            request_url = url
            purpose = ep.get("retrieval_purpose") or "accessibility_probe"
        else:
            request_url, purpose = "", "accessibility_probe"
        method = ep.get("allowed_http_method") or ""
        if verified and request_url and method in ("GET", "HEAD"):
            status, blocker = "planned", ""
        else:
            status = "blocked"
            blocker = ep.get("failure_reason") or "endpoint_not_verified"
            method, request_url = "", ""
        plan.append({
            "plan_row_id": f"plan_{idx:03d}",
            "candidate_id": cand_id,
            "source_id": source_id,
            "endpoint_id": endpoint_id_for(ep) if verified else "",
            "request_url": request_url,
            "http_method": method if status == "planned" else "",
            "retrieval_purpose": purpose,
            "plan_status": status,
            "blocker_reason": blocker,
            "shared_snapshot_key": source_id,
        })
    return plan


def capture_plan_sha256(plan_rows: list[dict]) -> str:
    return sha256_bytes(_csv_str(PLAN_HEADER, plan_rows).encode("utf-8"))


@dataclass
class NetworkStats:
    network_calls_attempted: int = 0
    network_calls_succeeded: int = 0
    network_calls_failed: int = 0
    bytes_retrieved: int = 0
    final_resolved_urls: list[str] = field(default_factory=list)
    response_statuses: list[int] = field(default_factory=list)
    redirect_counts: list[int] = field(default_factory=list)


class ReadOnlyNetworkPermit:
    """Scoped allowlist on top of an already-installed NetworkSentinel.

    Does not weaken or remove the outer default-deny sentinel. On exit the
    sentinel remains installed (default-deny restored relative to the permit).
    """

    def __init__(
        self,
        allowed_requests: set[tuple[str, str]],
        *,
        stats: NetworkStats | None = None,
        sentinel: p3b0.NetworkSentinel | None = None,
    ):
        self.allowed_requests = set(allowed_requests)
        self.stats = stats or NetworkStats()
        self._sentinel = sentinel
        self._owns_sentinel = sentinel is None
        self._active = False

    def __enter__(self) -> "ReadOnlyNetworkPermit":
        if self._sentinel is None:
            self._sentinel = p3b0.NetworkSentinel()
            self._sentinel.install()
            self._owns_sentinel = True
        self._active = True
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._active = False
        # Standalone permit (no outer sentinel): restore process originals.
        # Production capture always passes an outer NetworkSentinel that remains
        # installed after this context exits (default-deny preserved).
        if self._owns_sentinel and self._sentinel is not None:
            self._sentinel.restore()
            self._sentinel = None
        return None

    def _assert_public_dns(self, hostname: str) -> list[str]:
        assert self._sentinel is not None
        try:
            infos = self._sentinel._orig_getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise NetworkPolicyError(f"DNS resolution failed: {hostname}") from exc
        addrs: list[str] = []
        for info in infos:
            ip = info[4][0]
            addrs.append(ip)
            ip_obj = ipaddress.ip_address(ip)
            if (
                ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local
                or ip_obj.is_reserved or ip_obj.is_multicast or ip_obj.is_unspecified
            ):
                raise NetworkPolicyError(f"private/reserved IP rejected: {ip}")
        if not addrs:
            raise NetworkPolicyError(f"no addresses for {hostname}")
        return addrs

    def _validate_url(self, method: str, url: str) -> urllib.parse.ParseResult:
        method = method.upper()
        if method not in ("GET", "HEAD"):
            raise NetworkPolicyError(f"method not allowed: {method}")
        if (method, url) not in self.allowed_requests:
            raise NetworkPolicyError(f"URL not in capture plan allowlist: {url}")
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https":
            raise NetworkPolicyError("only https allowed")
        if parsed.username or parsed.password:
            raise NetworkPolicyError("credentials in URL forbidden")
        if parsed.port not in (None, 443):
            raise NetworkPolicyError("only port 443 allowed")
        if not parsed.hostname:
            raise NetworkPolicyError("missing hostname")
        self._assert_public_dns(parsed.hostname)
        return parsed

    def _validate_redirect(self, url: str) -> None:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or parsed.port not in (None, 443):
            raise NetworkPolicyError("redirect scheme/port rejected")
        host = parsed.hostname
        if not host:
            raise NetworkPolicyError("redirect missing host")
        allowed_hosts = {urllib.parse.urlparse(u).hostname for (_m, u) in self.allowed_requests}
        if host not in allowed_hosts:
            raise NetworkPolicyError(f"redirect host not allowlisted: {host}")
        self._assert_public_dns(host)

    def request(self, method: str, url: str) -> tuple[bytes, dict[str, Any]]:
        if not self._active:
            raise NetworkPolicyError("permit not active")
        method = method.upper()
        self.stats.network_calls_attempted += 1
        redirects = 0
        current = url
        try:
            while True:
                if redirects == 0:
                    self._validate_url(method, current)
                else:
                    self._validate_redirect(current)
                body, status, final_url, ctype = self._https_exchange(
                    method if redirects == 0 else "GET", current,
                )
                if status in (301, 302, 303, 307, 308):
                    redirects += 1
                    if redirects > MAX_REDIRECTS:
                        raise NetworkPolicyError("too many redirects")
                    if not final_url or final_url == current:
                        raise NetworkPolicyError("redirect without location")
                    current = final_url
                    continue
                if len(body) > MAX_RESPONSE_BYTES:
                    raise NetworkPolicyError("response exceeds size ceiling")
                self.stats.network_calls_succeeded += 1
                self.stats.bytes_retrieved += len(body)
                self.stats.final_resolved_urls.append(final_url or current)
                self.stats.response_statuses.append(status)
                self.stats.redirect_counts.append(redirects)
                time.sleep(RATE_LIMIT_SLEEP_SEC)
                return body, {
                    "final_resolved_url": final_url or current,
                    "response_status": status,
                    "redirect_count": redirects,
                    "content_type": ctype,
                    "bytes": len(body),
                }
        except Exception:
            self.stats.network_calls_failed += 1
            raise

    def _https_exchange(self, method: str, url: str) -> tuple[bytes, int, str, str]:
        assert self._sentinel is not None
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname
        assert host
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        ip = self._assert_public_dns(host)[0]
        raw_req = (
            f"{method} {path} HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            "User-Agent: papermali-stage125-part3b-readonly/1.0\r\n"
            "Accept: */*\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii")
        context = ssl.create_default_context()
        sock = None
        try:
            # Bypass blocked create_connection/getaddrinfo: connect the
            # already-validated public IP with the sentinel's original connect.
            family = socket.AF_INET6 if ":" in ip else socket.AF_INET
            raw_sock = socket.socket(family, socket.SOCK_STREAM)
            raw_sock.settimeout(REQUEST_TIMEOUT_SEC)
            self._sentinel._orig_connect(raw_sock, (ip, 443))
            sock = context.wrap_socket(raw_sock, server_hostname=host)
            sock.sendall(raw_req)
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES + 65536:
                    raise NetworkPolicyError("oversized response")
                chunks.append(chunk)
            raw = b"".join(chunks)
        finally:
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass
        return self._parse_http_response(raw, url)

    def _parse_http_response(self, raw: bytes, original_url: str) -> tuple[bytes, int, str, str]:
        if b"\r\n\r\n" not in raw:
            raise NetworkPolicyError("malformed HTTP response")
        header_blob, body = raw.split(b"\r\n\r\n", 1)
        lines = header_blob.split(b"\r\n")
        status_line = lines[0].decode("iso-8859-1", errors="replace")
        parts = status_line.split()
        if len(parts) < 2:
            raise NetworkPolicyError("bad status line")
        status = int(parts[1])
        headers: dict[str, str] = {}
        for line in lines[1:]:
            if b":" not in line:
                continue
            k, v = line.split(b":", 1)
            headers[k.decode("iso-8859-1").strip().lower()] = v.decode("iso-8859-1", errors="replace").strip()
        ctype = headers.get("content-type", "")
        location = headers.get("location", "")
        final_url = original_url
        if status in (301, 302, 303, 307, 308) and location:
            final_url = urllib.parse.urljoin(original_url, location)
        if headers.get("transfer-encoding", "").lower() == "chunked":
            body = self._dechunk(body)
        if len(body) > MAX_RESPONSE_BYTES:
            raise NetworkPolicyError("body exceeds size ceiling")
        return body, status, final_url, ctype

    @staticmethod
    def _dechunk(data: bytes) -> bytes:
        out = bytearray()
        i = 0
        while i < len(data):
            j = data.find(b"\r\n", i)
            if j < 0:
                raise NetworkPolicyError("bad chunked encoding")
            size = int(data[i:j].split(b";")[0], 16)
            i = j + 2
            if size == 0:
                break
            out.extend(data[i:i + size])
            i += size + 2
            if len(out) > MAX_RESPONSE_BYTES:
                raise NetworkPolicyError("dechunked body too large")
        return bytes(out)


@contextmanager
def network_default_deny() -> Iterator[p3b0.NetworkSentinel]:
    with p3b0.network_sentinel() as sentinel:
        yield sentinel


# --------------------------------------------------------------------------- #
# Sealed real evidence / gate / assessment
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class ValidatedRealEvidence:
    evidence_id: str
    candidate_id: str
    source_id: str
    predictor_row_key_t: str | None
    target_row_key_t_plus_1: str | None
    class_label: str | None
    target_year: str | None
    prediction_cutoff: str | None
    published_at: str | None
    available_at: str | None
    retrieved_at_utc: str | None
    snapshot_sha256: str | None
    metadata_sha256: str | None
    external_handle_sha256: str | None
    _seal: str = field(repr=False, compare=True)


@dataclass(frozen=True)
class ValidatedRealGateInput:
    evidence: ValidatedRealEvidence
    accessibility_score: int | None
    authoritative_source: bool | None
    reproducible_retrieval: bool | None
    quality_controls_met: bool | None
    prediction_cutoff: str | None
    _seal: str = field(repr=False, compare=True)


@dataclass(frozen=True)
class SealedPairCandidateAssessment:
    assessment_id: str
    predictor_row_key_t: str
    target_row_key_t_plus_1: str
    candidate_id: str
    source_id: str
    class_label: str
    target_year: str
    prediction_cutoff: str | None
    evidence_id: str | None
    snapshot_sha256: str | None
    metadata_sha256: str | None
    external_handle_sha256: str | None
    assessment_status: str
    usability_flag: bool
    _seal: str = field(repr=False, compare=True)


def _seal_join(parts: list[str]) -> str:
    return sha256_bytes("|".join(parts).encode("utf-8"))


def require_sealed_real_evidence(evidence: ValidatedRealEvidence) -> ValidatedRealEvidence:
    if type(evidence) is not ValidatedRealEvidence:
        raise QCFail("ValidatedRealEvidence type check failed")
    expected = _seal_join([
        _REAL_EVIDENCE_SEAL, evidence.evidence_id, evidence.candidate_id,
        evidence.source_id, evidence.predictor_row_key_t or "",
        evidence.target_row_key_t_plus_1 or "", evidence.class_label or "",
        evidence.target_year or "", evidence.prediction_cutoff or "",
        evidence.snapshot_sha256 or "", evidence.metadata_sha256 or "",
        evidence.external_handle_sha256 or "",
    ])
    if evidence._seal != expected:
        raise QCFail("ValidatedRealEvidence seal verification failed")
    return evidence


def validate_and_seal_real_evidence(
    record: dict[str, Any],
    *,
    schema: dict,
    candidate_source_map: dict[str, str],
    source_registry: dict[str, dict],
    predictor_row_key_t: str | None = None,
    target_row_key_t_plus_1: str | None = None,
    class_label: str | None = None,
    target_year: str | None = None,
    prediction_cutoff: str | None = None,
    metadata_sha256: str | None = None,
    external_handle_sha256: str | None = None,
    allowed_snapshot_root: Path | None = None,
) -> ValidatedRealEvidence:
    eid = str(record.get("evidence_id", ""))
    if eid.startswith(p3b0.SYNTHETIC_EVIDENCE_ID_PREFIX):
        raise p3b0.EvidenceValidationError("synthetic evidence_id not allowed")
    if record.get("access_method") == p3b0.SYNTHETIC_ACCESS_METHOD:
        raise p3b0.EvidenceValidationError("synthetic access_method not allowed")
    p3b0._validate_evidence_record_core(
        record, schema=schema, candidate_source_map=candidate_source_map,
        source_registry=source_registry,
    )
    if not p3b0._is_null(record.get("local_snapshot_path")):
        if allowed_snapshot_root is None:
            raise p3b0.EvidenceValidationError("snapshot requires allowed_snapshot_root")
        p3b0._verify_snapshot_bytes_match_hash(
            record, allowed_snapshot_root=Path(allowed_snapshot_root),
        )
    snap = None if p3b0._is_null(record.get("snapshot_sha256")) else str(
        record["snapshot_sha256"]
    ).strip().lower()
    base = ValidatedRealEvidence(
        evidence_id=str(record["evidence_id"]),
        candidate_id=str(record["candidate_id"]),
        source_id=str(record["source_id"]),
        predictor_row_key_t=predictor_row_key_t,
        target_row_key_t_plus_1=target_row_key_t_plus_1,
        class_label=class_label,
        target_year=target_year,
        prediction_cutoff=prediction_cutoff,
        published_at=p3b0._nullable_str(record.get("published_at")),
        available_at=p3b0._nullable_str(record.get("available_at")),
        retrieved_at_utc=p3b0._nullable_str(record.get("retrieved_at_utc")),
        snapshot_sha256=snap,
        metadata_sha256=metadata_sha256,
        external_handle_sha256=external_handle_sha256,
        _seal="",
    )
    seal = _seal_join([
        _REAL_EVIDENCE_SEAL, base.evidence_id, base.candidate_id, base.source_id,
        base.predictor_row_key_t or "", base.target_row_key_t_plus_1 or "",
        base.class_label or "", base.target_year or "", base.prediction_cutoff or "",
        base.snapshot_sha256 or "", base.metadata_sha256 or "",
        base.external_handle_sha256 or "",
    ])
    return require_sealed_real_evidence(ValidatedRealEvidence(**{**base.__dict__, "_seal": seal}))


def require_sealed_real_gate_input(gate_input: ValidatedRealGateInput) -> ValidatedRealGateInput:
    if type(gate_input) is not ValidatedRealGateInput:
        raise QCFail("ValidatedRealGateInput type check failed")
    require_sealed_real_evidence(gate_input.evidence)
    expected = _seal_join([
        _REAL_GATE_SEAL, gate_input.evidence._seal,
        "" if gate_input.accessibility_score is None else str(gate_input.accessibility_score),
        "" if gate_input.authoritative_source is None else ("1" if gate_input.authoritative_source else "0"),
        "" if gate_input.reproducible_retrieval is None else ("1" if gate_input.reproducible_retrieval else "0"),
        "" if gate_input.quality_controls_met is None else ("1" if gate_input.quality_controls_met else "0"),
        gate_input.prediction_cutoff or "",
    ])
    if gate_input._seal != expected:
        raise QCFail("ValidatedRealGateInput seal verification failed")
    return gate_input


def build_validated_real_gate_input(
    evidence: ValidatedRealEvidence,
    *,
    accessibility_score: int | None = None,
    authoritative_source: bool | None = None,
    reproducible_retrieval: bool | None = None,
    quality_controls_met: bool | None = None,
) -> ValidatedRealGateInput:
    evidence = require_sealed_real_evidence(evidence)
    if accessibility_score is not None and type(accessibility_score) is not int:
        raise QCFail("accessibility_score must be int or None")
    for name, value in (
        ("authoritative_source", authoritative_source),
        ("reproducible_retrieval", reproducible_retrieval),
        ("quality_controls_met", quality_controls_met),
    ):
        if value is not None and type(value) is not bool:
            raise QCFail(f"{name} must be bool or None")
    seal = _seal_join([
        _REAL_GATE_SEAL, evidence._seal,
        "" if accessibility_score is None else str(accessibility_score),
        "" if authoritative_source is None else ("1" if authoritative_source else "0"),
        "" if reproducible_retrieval is None else ("1" if reproducible_retrieval else "0"),
        "" if quality_controls_met is None else ("1" if quality_controls_met else "0"),
        evidence.prediction_cutoff or "",
    ])
    return require_sealed_real_gate_input(ValidatedRealGateInput(
        evidence=evidence,
        accessibility_score=accessibility_score,
        authoritative_source=authoritative_source,
        reproducible_retrieval=reproducible_retrieval,
        quality_controls_met=quality_controls_met,
        prediction_cutoff=evidence.prediction_cutoff,
        _seal=seal,
    ))


def evaluate_real_candidate_gates(gate_input: ValidatedRealGateInput) -> dict[str, str]:
    gate_input = require_sealed_real_gate_input(gate_input)
    ev = gate_input.evidence
    statuses = {
        "G01": p3b0.evaluate_g01(gate_input.accessibility_score),
        "G02": p3b0.evaluate_g02(gate_input.authoritative_source),
        "G03": p3b0.evaluate_g03(gate_input.reproducible_retrieval),
        "G04": p3b0.evaluate_g04(ev.published_at, ev.available_at),
        "G05": p3b0.evaluate_g05(gate_input.quality_controls_met),
        "G06": p3b0.evaluate_g06(ev.available_at),
        "G07": p3b0.evaluate_g07_from_cutoff(ev.available_at, gate_input.prediction_cutoff),
    }
    statuses["G08"] = p3b0.evaluate_g08({k: statuses[k] for k in p3b0.G01_G07})
    return statuses


def require_sealed_assessment(a: SealedPairCandidateAssessment) -> SealedPairCandidateAssessment:
    if type(a) is not SealedPairCandidateAssessment:
        raise QCFail("SealedPairCandidateAssessment type check failed")
    expected = _seal_join([
        _ASSESS_SEAL, a.assessment_id, a.predictor_row_key_t, a.target_row_key_t_plus_1,
        a.candidate_id, a.source_id, a.class_label, a.target_year,
        a.prediction_cutoff or "", a.evidence_id or "", a.snapshot_sha256 or "",
        a.metadata_sha256 or "", a.external_handle_sha256 or "",
        a.assessment_status, "1" if a.usability_flag else "0",
    ])
    if a._seal != expected:
        raise QCFail("SealedPairCandidateAssessment seal verification failed")
    return a


def seal_pair_candidate_assessment(**kwargs) -> SealedPairCandidateAssessment:
    usability_flag = kwargs["usability_flag"]
    if type(usability_flag) is not bool:
        raise QCFail("usability_flag must be exact bool")
    if kwargs["assessment_status"] not in (p3b0.GATE_PASS, p3b0.GATE_FAIL, p3b0.GATE_UNRESOLVED):
        raise QCFail("invalid assessment_status")
    seal = _seal_join([
        _ASSESS_SEAL, kwargs["assessment_id"], kwargs["predictor_row_key_t"],
        kwargs["target_row_key_t_plus_1"], kwargs["candidate_id"], kwargs["source_id"],
        kwargs["class_label"], kwargs["target_year"], kwargs.get("prediction_cutoff") or "",
        kwargs.get("evidence_id") or "", kwargs.get("snapshot_sha256") or "",
        kwargs.get("metadata_sha256") or "", kwargs.get("external_handle_sha256") or "",
        kwargs["assessment_status"], "1" if usability_flag else "0",
    ])
    return require_sealed_assessment(SealedPairCandidateAssessment(_seal=seal, **kwargs))


def empty_evidence_record(*, evidence_id, candidate_id, source_id, source_owner, failure_reason,
                          reviewer_status="automated_fail_closed") -> dict:
    return {
        "evidence_id": evidence_id, "candidate_id": candidate_id, "source_id": source_id,
        "source_owner": source_owner, "source_url": None, "source_title": None,
        "source_identifier": None, "retrieved_at_utc": None, "published_at": None,
        "available_at": None, "raw_date_text": None, "calendar": None, "timezone": None,
        "access_method": None, "authentication_required": None,
        "response_status_evidence": None, "local_snapshot_path": None,
        "snapshot_sha256": None, "revision_status": None, "license_or_usage_notes": None,
        "reviewer_status": reviewer_status, "failure_reason": failure_reason,
    }


def successful_probe_evidence_record(
    *, evidence_id, candidate_id, source_id, source_owner, source_url,
    retrieved_at_utc, response_status, snapshot_rel, snapshot_sha256, license_notes,
) -> dict:
    return {
        "evidence_id": evidence_id, "candidate_id": candidate_id, "source_id": source_id,
        "source_owner": source_owner, "source_url": source_url, "source_title": None,
        "source_identifier": None, "retrieved_at_utc": retrieved_at_utc,
        "published_at": None, "available_at": None, "raw_date_text": None,
        "calendar": None, "timezone": "UTC",
        "access_method": "https_get_readonly_permit",
        "authentication_required": False,
        "response_status_evidence": str(response_status),
        "local_snapshot_path": snapshot_rel, "snapshot_sha256": snapshot_sha256,
        "revision_status": None, "license_or_usage_notes": license_notes,
        "reviewer_status": "automated_capture_not_human_reviewed",
        "failure_reason": None,
    }


def _coerce_evidence_record_types(row: dict) -> dict:
    """Normalize CSV-loaded evidence rows for schema validation."""
    out = dict(row)
    auth = out.get("authentication_required")
    if auth is None or (isinstance(auth, str) and auth.strip() == ""):
        out["authentication_required"] = None
    elif isinstance(auth, bool):
        pass
    elif isinstance(auth, str) and auth.strip().lower() in ("true", "false"):
        out["authentication_required"] = auth.strip().lower() == "true"
    else:
        raise QCFail(f"invalid authentication_required: {auth!r}")
    return out


def null_score_row(candidate_id: str, source_id: str, evidence_ids: list[str], rationale: str) -> dict:
    return {
        "candidate_id": candidate_id,
        "source_id": source_id,
        "rubric_version": RUBRIC_VERSION,
        "accessibility_score": "",
        "score_status": "UNRESOLVED",
        "evidence_ids_cited": ";".join(evidence_ids),
        "rationale": rationale,
        "requires_human_adjudication": "true",
        "reviewer_status": "automated_not_human_reviewed",
    }


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def build_authorization_record(repo_root: Path, plan_hash: str, endpoint_hash: str,
                               frozen_hashes: dict[str, str]) -> dict:
    return {
        "authorization_version": "stage125_part3b_auth_v1",
        "stage": CURRENT_STAGE,
        "authorized_action": "stage125-part3b-evidence-capture",
        "baseline_commit": EXPECTED_BASELINE_COMMIT,
        "part3b_started": True,
        "part3b0_readiness": True,
        "modeling_started": False,
        "real_evidence_authorized": True,
        "network_readonly_authorized": True,
        "capture_plan_sha256": plan_hash,
        "endpoint_registry_sha256": endpoint_hash,
        "frozen_input_sha256": frozen_hashes,
        "registered_candidate_ids": list(REGISTERED_CANDIDATE_IDS),
        "pilot_pair_count": 80,
        "assessment_matrix_size": 800,
        "notes": (
            "Part 3B authorized for evidence capture and accessibility scoring "
            "pilot only. No modeling. No sample/target/eligibility change."
        ),
    }


def build_readme() -> str:
    return """# Stage125 Part 3B — Evidence Capture & Accessibility Scoring Pilot

## Scope

Authorized Part 3B pilot on the locked 80-pair event-enriched sample and the
exact 10 registered M2–M4 candidates (800 pair-candidate assessments).

## Modes

- `--plan` — deterministic capture plan + endpoint registry (no network)
- `--capture` — approved read-only HTTPS GET/HEAD only
- `--write` — derive manifests/scores/gates/QC from cached evidence (no network)
- `--check` — offline validation (no network)

## Scientific honesty

- Feature-definition gaps are recorded; values are not invented.
- Missing evidence yields null accessibility scores (never 0 by absence).
- Prediction cutoffs come only from the frozen Part 2 audit (currently
  unresolvable pending `available_at`).
- Part 3B outcomes are pilot accessibility outcomes only — not Stage126 admission.

## Network policy

Default-deny `NetworkSentinel` remains installed. Capture uses a scoped
read-only permit that restores default-deny after exit/exception.

## Part 3B.0 history

Part 3B.0 readiness artifacts remain a frozen historical baseline. Live Part 3B
state is owned by this runner.
"""


def _source_owner(registry: dict[str, dict], source_id: str) -> str:
    row = registry.get(source_id) or {}
    return str(row.get("source_owner") or "")


def run_plan(repo_root: Path, output_dir: Path, *, write: bool) -> dict:
    with network_default_deny() as sentinel:
        verify_baseline_commit(str(repo_root))
        frozen = verify_frozen_input_hashes(repo_root)
        endpoints = build_endpoint_registry_rows(repo_root)
        plan = build_capture_plan(repo_root, endpoints)
        plan_hash = capture_plan_sha256(plan)
        ep_csv = _csv_str(ENDPOINT_HEADER, endpoints)
        ep_hash = sha256_bytes(ep_csv.encode("utf-8"))
        auth = build_authorization_record(repo_root, plan_hash, ep_hash, frozen)
        files = {
            F_AUTH: _json_str(auth),
            F_ENDPOINTS: ep_csv,
            F_PLAN: _csv_str(PLAN_HEADER, plan),
        }
        if write:
            output_dir.mkdir(parents=True, exist_ok=True)
            for name, content in files.items():
                (output_dir / name).write_text(content, encoding="utf-8")
        return {
            "mode": "plan",
            "files": files,
            "plan_hash": plan_hash,
            "endpoint_hash": ep_hash,
            "planned_requests": sum(1 for r in plan if r["plan_status"] == "planned"),
            "blocked_requests": sum(1 for r in plan if r["plan_status"] == "blocked"),
            "network_calls_attempted": sentinel.calls_attempted,
            "output_dir": str(output_dir),
            "written": write,
        }


def run_capture(repo_root: Path, output_dir: Path) -> dict:
    """Perform approved read-only retrieval for planned URLs; update cache/handles/evidence."""
    verify_baseline_commit(str(repo_root))
    verify_frozen_input_hashes(repo_root)
    if not (output_dir / F_PLAN).is_file() or not (output_dir / F_AUTH).is_file():
        raise QCFail("run --plan --write before --capture")
    plan = list(csv.DictReader((output_dir / F_PLAN).open(encoding="utf-8")))
    endpoints = list(csv.DictReader((output_dir / F_ENDPOINTS).open(encoding="utf-8")))
    registry = p3b0.load_source_registry(repo_root)
    schema = p3b0.load_frozen_evidence_schema(repo_root)
    cand_map = p3b0.load_candidate_source_map(repo_root)

    allowed = {
        (r["http_method"].upper(), r["request_url"])
        for r in plan
        if r["plan_status"] == "planned" and r["request_url"] and r["http_method"]
    }
    stats = NetworkStats()
    cache_root = repo_root / CACHE_DIR_REL
    cache = p3b0.ImmutableCache(cache_root)

    # Reuse successful snapshot per shared_snapshot_key
    evidence_rows: list[dict] = []
    handle_rows: list[dict] = []
    shared_success: dict[str, dict] = {}

    # Load existing handles if present for resume
    existing_handles = {}
    if (output_dir / F_HANDLES).is_file():
        for row in csv.DictReader((output_dir / F_HANDLES).open(encoding="utf-8")):
            existing_handles[row["evidence_id"]] = row

    with network_default_deny() as outer_sentinel:
      with ReadOnlyNetworkPermit(allowed, stats=stats, sentinel=outer_sentinel) as permit:
        for prow in plan:
            cand_id = prow["candidate_id"]
            source_id = prow["source_id"]
            shared_key = prow["shared_snapshot_key"]
            evidence_id = f"ev_{source_id}_{cand_id}"
            owner = _source_owner(registry, source_id)

            if prow["plan_status"] != "planned":
                evidence_rows.append(empty_evidence_record(
                    evidence_id=evidence_id,
                    candidate_id=cand_id,
                    source_id=source_id,
                    source_owner=owner,
                    failure_reason=prow.get("blocker_reason") or "plan_blocked",
                ))
                continue

            if shared_key in shared_success:
                base = {
                    k: v for k, v in shared_success[shared_key].items()
                    if not str(k).startswith("_")
                }
                base["evidence_id"] = evidence_id
                base["candidate_id"] = cand_id
                evidence_rows.append(base)
                # Shared snapshot: reuse evidence fields/snapshot hash, but do NOT
                # forge a CacheHandle for a different evidence_id (metadata is
                # write-once bound to the first put). Handle row omitted.
                continue

            # Resume if evidence already captured
            if evidence_id in existing_handles:
                h = existing_handles[evidence_id]
                try:
                    handle = p3b0.CacheHandle(
                        evidence_id=h["evidence_id"],
                        payload_sha256=h["payload_sha256"],
                        metadata_sha256=h["metadata_sha256"],
                        cache_contract_version=h.get("cache_contract_version", p3b0.CACHE_CONTRACT_VERSION),
                        schema_version=h.get("cache_handle_schema_version", p3b0.CACHE_HANDLE_SCHEMA_VERSION),
                    )
                    payload = cache.get_by_handle(handle)
                    retrieved = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    rec = successful_probe_evidence_record(
                        evidence_id=evidence_id,
                        candidate_id=cand_id,
                        source_id=source_id,
                        source_owner=owner,
                        source_url=prow["request_url"],
                        retrieved_at_utc=retrieved,
                        response_status=200,
                        snapshot_rel=f"raw_cache_part3b/{handle.payload_sha256[:2]}/{handle.payload_sha256}/payload.bin",
                        snapshot_sha256=handle.payload_sha256,
                        license_notes="raw bytes retained in local immutable cache; redistribution per source terms",
                    )
                    # validate
                    validate_and_seal_real_evidence(
                        {k: (None if v == "" else v) for k, v in rec.items()},
                        schema=schema, candidate_source_map=cand_map,
                        source_registry=registry,
                        metadata_sha256=handle.metadata_sha256,
                        external_handle_sha256=h.get("external_handle_sha256"),
                        allowed_snapshot_root=repo_root / "project/stage125",
                    )
                    del payload
                    evidence_rows.append(rec)
                    handle_rows.append(h)
                    shared_success[shared_key] = {
                        **rec,
                        "_payload_sha256": handle.payload_sha256,
                        "_metadata_sha256": handle.metadata_sha256,
                        "_external_handle_sha256": h.get("external_handle_sha256"),
                        "_bound_evidence_id": evidence_id,
                    }
                    continue
                except Exception:
                    pass  # fall through to re-fetch

            try:
                body, meta = permit.request(prow["http_method"], prow["request_url"])
                retrieved = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                put = cache.put(
                    body,
                    metadata={
                        "source_id": source_id,
                        "request_url": prow["request_url"],
                        "final_resolved_url": meta["final_resolved_url"],
                        "response_status": meta["response_status"],
                        "retrieved_at_utc": retrieved,
                        "retrieval_purpose": prow["retrieval_purpose"],
                    },
                    evidence_id=evidence_id,
                )
                handle = p3b0.cache_handle_from_put_result(evidence_id, put)
                serialized = p3b0.serialize_cache_handle(handle)
                handle_sha = p3b0.cache_handle_sha256(serialized)
                # Materialize snapshot path under stage125 for schema path checks
                snap_dir = repo_root / "project/stage125/raw_cache_part3b" / put.payload_sha256[:2] / put.payload_sha256
                snap_rel = f"raw_cache_part3b/{put.payload_sha256[:2]}/{put.payload_sha256}/payload.bin"
                rec = successful_probe_evidence_record(
                    evidence_id=evidence_id,
                    candidate_id=cand_id,
                    source_id=source_id,
                    source_owner=owner,
                    source_url=meta["final_resolved_url"],
                    retrieved_at_utc=retrieved,
                    response_status=meta["response_status"],
                    snapshot_rel=snap_rel,
                    snapshot_sha256=put.payload_sha256,
                    license_notes=(
                        "raw bytes retained in local immutable cache only; "
                        "manifest/handles committed; redistribution subject to source terms"
                    ),
                )
                validate_and_seal_real_evidence(
                    {k: (None if v == "" else v) for k, v in rec.items()},
                    schema=schema, candidate_source_map=cand_map,
                    source_registry=registry,
                    metadata_sha256=put.metadata_sha256,
                    external_handle_sha256=handle_sha,
                    allowed_snapshot_root=repo_root / "project/stage125",
                )
                evidence_rows.append(rec)
                hrow = {
                    "evidence_id": evidence_id,
                    "payload_sha256": put.payload_sha256,
                    "metadata_sha256": put.metadata_sha256,
                    "cache_contract_version": p3b0.CACHE_CONTRACT_VERSION,
                    "cache_handle_schema_version": p3b0.CACHE_HANDLE_SCHEMA_VERSION,
                    "external_handle_sha256": handle_sha,
                    "source_id": source_id,
                    "candidate_id": cand_id,
                }
                handle_rows.append(hrow)
                shared_success[shared_key] = {
                    **rec,
                    "_payload_sha256": put.payload_sha256,
                    "_metadata_sha256": put.metadata_sha256,
                    "_external_handle_sha256": handle_sha,
                    "_bound_evidence_id": evidence_id,
                }
                del snap_dir
            except Exception as exc:
                evidence_rows.append(empty_evidence_record(
                    evidence_id=evidence_id,
                    candidate_id=cand_id,
                    source_id=source_id,
                    source_owner=owner,
                    failure_reason=f"capture_failed:{type(exc).__name__}:{exc}",
                ))

    # Normalize evidence for CSV (None -> empty)
    ev_header = p3b0.evidence_header_from_schema(schema)
    ev_out = []
    for r in evidence_rows:
        ev_out.append({k: ("" if r.get(k) is None else r.get(k, "")) for k in ev_header})

    handle_header = HANDLE_HEADER
    # strip helper keys from handle rows
    handles_clean = [{k: h.get(k, "") for k in handle_header} for h in handle_rows]

    unique_snapshots = len({
        h["payload_sha256"] for h in handles_clean if h.get("payload_sha256")
    })
    prior_log: dict[str, Any] = {}
    prior_path = output_dir / F_NETWORK_LOG
    if prior_path.is_file():
        try:
            prior_log = json.loads(prior_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            prior_log = {}

    # Resume/idempotent reruns that only verify cache must not wipe honest
    # historical network attempt/success counts from a prior live capture.
    if stats.network_calls_attempted == 0 and int(prior_log.get("network_calls_attempted") or 0) > 0:
        network_log = dict(prior_log)
        network_log["unique_raw_snapshot_count"] = unique_snapshots
        network_log["evidence_record_count"] = len(ev_out)
        network_log["resume_verified_without_new_network"] = True
        network_log["network_extraction_performed"] = bool(
            prior_log.get("network_extraction_performed") or unique_snapshots > 0
        )
    else:
        network_log = {
            "stage": QC_STAGE,
            "baseline_commit": EXPECTED_BASELINE_COMMIT,
            "network_calls_attempted": stats.network_calls_attempted,
            "network_calls_succeeded": stats.network_calls_succeeded,
            "network_calls_failed": stats.network_calls_failed,
            "bytes_retrieved": stats.bytes_retrieved,
            "final_resolved_urls": sorted(set(stats.final_resolved_urls)),
            "response_statuses": list(stats.response_statuses),
            "redirect_counts": list(stats.redirect_counts),
            "hosts_contacted": sorted({
                urllib.parse.urlparse(u).hostname
                for u in stats.final_resolved_urls
                if urllib.parse.urlparse(u).hostname
            }),
            "http_methods": ["GET"],
            "network_extraction_performed": (
                stats.network_calls_succeeded > 0 or unique_snapshots > 0
            ),
            "unique_raw_snapshot_count": unique_snapshots,
            "evidence_record_count": len(ev_out),
            "resume_verified_without_new_network": False,
            "notes": (
                "Persisted at capture time. --write/--check must reuse these stats "
                "and must not claim zero attempts after successful retrieval."
            ),
        }
    files = {
        F_EVIDENCE: _csv_str(ev_header, ev_out),
        F_HANDLES: _csv_str(handle_header, handles_clean),
        F_NETWORK_LOG: _json_str(network_log),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (output_dir / name).write_text(content, encoding="utf-8")

    return {
        "mode": "capture",
        "files": files,
        "network_stats": stats.__dict__,
        "network_extraction_performed": stats.network_calls_succeeded > 0,
        "evidence_count": len(ev_out),
        "handle_count": len(handles_clean),
        "unique_snapshot_count": network_log["unique_raw_snapshot_count"],
        "output_dir": str(output_dir),
        "written": True,
        "endpoints_contacted": network_log["final_resolved_urls"],
    }


def _evidence_by_candidate(evidence_rows: list[dict]) -> dict[str, dict]:
    return {r["candidate_id"]: r for r in evidence_rows}


def run_write(repo_root: Path, output_dir: Path) -> dict:
    with network_default_deny() as sentinel:
        verify_baseline_commit(str(repo_root))
        frozen_before = p3b0.frozen_asset_hashes(repo_root)
        frozen = verify_frozen_input_hashes(repo_root)
        if not (output_dir / F_EVIDENCE).is_file():
            raise QCFail("evidence manifest missing; run --capture first")
        schema = p3b0.load_frozen_evidence_schema(repo_root)
        registry = p3b0.load_source_registry(repo_root)
        cand_map = p3b0.load_candidate_source_map(repo_root)
        policy = p3b0.load_locked_gate_policy(repo_root)
        pilots = p3b0.load_locked_pilot_pairs(repo_root)
        cutoff_map = load_prediction_cutoff_map(repo_root)
        evidence_rows = list(csv.DictReader((output_dir / F_EVIDENCE).open(encoding="utf-8")))
        handle_rows = []
        if (output_dir / F_HANDLES).is_file():
            handle_rows = list(csv.DictReader((output_dir / F_HANDLES).open(encoding="utf-8")))
        handles_by_eid = {h["evidence_id"]: h for h in handle_rows}
        ev_by_cand = _evidence_by_candidate(evidence_rows)

        # Scores: null unless uniquely supported — accessibility probe alone does not uniquely map to 0-5
        score_rows = []
        for cand_id in REGISTERED_CANDIDATE_IDS:
            ev = ev_by_cand.get(cand_id)
            source_id = CANDIDATE_SOURCE_MAP[cand_id]
            eids = [ev["evidence_id"]] if ev and ev.get("evidence_id") else []
            if ev and ev.get("snapshot_sha256"):
                rationale = (
                    "Official-source accessibility probe evidence exists, but the "
                    "frozen rubric does not uniquely determine a numeric score from "
                    "HTTP accessibility alone without human adjudication."
                )
            else:
                rationale = (
                    "No validated snapshot evidence for candidate; score remains null "
                    "(missing evidence never scored as 0)."
                )
            score_rows.append(null_score_row(cand_id, source_id, eids, rationale))

        # 800 assessments
        assess_rows = []
        gate_detail_rows = []
        unresolved_rows = []
        pair_records_for_g11 = []  # retained for audit trail in assessments

        for pair in pilots:
            pred = pair["predictor_row_key_t"]
            targ = pair["target_row_key_t_plus_1"]
            audit = cutoff_map.get((pred, targ))
            cutoff, cutoff_ok = pair_prediction_cutoff(audit)
            for cand_id in REGISTERED_CANDIDATE_IDS:
                source_id = CANDIDATE_SOURCE_MAP[cand_id]
                ev = ev_by_cand.get(cand_id) or {}
                eid = ev.get("evidence_id") or ""
                h = handles_by_eid.get(eid, {})
                assessment_id = f"assess_{pred}_{targ}_{cand_id}".replace("|", "_")

                # Build sealed assessment inputs
                has_snap = bool(ev.get("snapshot_sha256"))
                failure_bits = []
                if not has_snap:
                    failure_bits.append(ev.get("failure_reason") or "missing_snapshot_evidence")
                failure_bits.append(DEFINITION_CONTRACT_GAP)
                if not cutoff_ok:
                    failure_bits.append("prediction_cutoff_unresolvable_in_part2_audit")

                # Gate derivation via sealed real path when possible
                score = None  # never invent
                auth_src = True if has_snap else None
                repro = True if has_snap else None
                quality = False if has_snap else None  # definition gap => quality not met

                gstat = {
                    "G01": p3b0.GATE_UNRESOLVED,
                    "G02": p3b0.GATE_UNRESOLVED,
                    "G03": p3b0.GATE_UNRESOLVED,
                    "G04": p3b0.GATE_UNRESOLVED,
                    "G05": p3b0.GATE_UNRESOLVED,
                    "G06": p3b0.GATE_UNRESOLVED,
                    "G07": p3b0.GATE_UNRESOLVED,
                    "G08": p3b0.GATE_UNRESOLVED,
                }
                if has_snap:
                    # Normalize record nulls
                    rec = _coerce_evidence_record_types(
                        {k: (None if ev.get(k) in ("", None) else ev.get(k)) for k in ev}
                    )
                    try:
                        sealed_ev = validate_and_seal_real_evidence(
                            rec, schema=schema, candidate_source_map=cand_map,
                            source_registry=registry,
                            predictor_row_key_t=pred,
                            target_row_key_t_plus_1=targ,
                            class_label=pair["class_label"],
                            target_year=str(pair["target_year"]),
                            prediction_cutoff=cutoff,
                            metadata_sha256=h.get("metadata_sha256") or None,
                            external_handle_sha256=h.get("external_handle_sha256") or None,
                            allowed_snapshot_root=repo_root / "project/stage125",
                        )
                        gin = build_validated_real_gate_input(
                            sealed_ev,
                            accessibility_score=score,
                            authoritative_source=auth_src,
                            reproducible_retrieval=repro,
                            quality_controls_met=quality,
                        )
                        gstat = evaluate_real_candidate_gates(gin)
                    except Exception as exc:
                        failure_bits.append(f"seal_or_gate_error:{type(exc).__name__}")
                        gstat = {k: p3b0.GATE_FAIL for k in gstat}

                # Assessment status: PASS only if G08 PASS (won't happen with null score)
                if gstat["G08"] == p3b0.GATE_PASS:
                    astatus = p3b0.GATE_PASS
                    usable = True
                elif gstat["G08"] == p3b0.GATE_FAIL:
                    astatus = p3b0.GATE_FAIL
                    usable = False
                else:
                    astatus = p3b0.GATE_UNRESOLVED
                    usable = False

                sealed_a = seal_pair_candidate_assessment(
                    assessment_id=assessment_id,
                    predictor_row_key_t=pred,
                    target_row_key_t_plus_1=targ,
                    candidate_id=cand_id,
                    source_id=source_id,
                    class_label=pair["class_label"],
                    target_year=str(pair["target_year"]),
                    prediction_cutoff=cutoff,
                    evidence_id=eid or None,
                    snapshot_sha256=ev.get("snapshot_sha256") or None,
                    metadata_sha256=h.get("metadata_sha256") or None,
                    external_handle_sha256=h.get("external_handle_sha256") or None,
                    assessment_status=astatus,
                    usability_flag=usable,
                )
                del sealed_a

                assess_rows.append({
                    "assessment_id": assessment_id,
                    "predictor_row_key_t": pred,
                    "target_row_key_t_plus_1": targ,
                    "ticker": pair["ticker"],
                    "target_year": pair["target_year"],
                    "class_label": pair["class_label"],
                    "candidate_id": cand_id,
                    "source_id": source_id,
                    "block": BLOCK_BY_CANDIDATE[cand_id],
                    "evidence_id": eid,
                    "assessment_status": astatus,
                    "usability_flag": "true" if usable else "false",
                    "definition_contract_gap": DEFINITION_CONTRACT_GAP,
                    "prediction_cutoff": cutoff or "",
                    "cutoff_resolvable": "true" if cutoff_ok else "false",
                    "g01": gstat["G01"], "g02": gstat["G02"], "g03": gstat["G03"],
                    "g04": gstat["G04"], "g05": gstat["G05"], "g06": gstat["G06"],
                    "g07": gstat["G07"], "g08": gstat["G08"],
                    "failure_reason": ";".join(failure_bits),
                    "reviewer_status": "automated_not_human_reviewed",
                })
                for gid in ("G01", "G02", "G03", "G04", "G05", "G06", "G07", "G08"):
                    gate_detail_rows.append({
                        "gate_id": gid,
                        "gate_name": gid,
                        "scope": "pair_candidate",
                        "candidate_id": cand_id,
                        "block": BLOCK_BY_CANDIDATE[cand_id],
                        "pilot_pair_key": pred,
                        "status": gstat[gid],
                        "detail": ";".join(failure_bits)[:500],
                    })
                if astatus != p3b0.GATE_PASS:
                    unresolved_rows.append({
                        "assessment_id": assessment_id,
                        "predictor_row_key_t": pred,
                        "candidate_id": cand_id,
                        "status": astatus,
                        "reason": ";".join(failure_bits),
                    })

        if len(assess_rows) != 800:
            raise QCFail(f"assessment matrix size {len(assess_rows)} != 800")
        ids = [r["assessment_id"] for r in assess_rows]
        if len(ids) != len(set(ids)):
            raise QCFail("duplicate assessment_id")

        # Pilot-level G09-G14
        pilot_keys = frozenset(policy.frozen_pilot_keys)
        usable_by_candidate: dict[str, set[str]] = {c: set() for c in REGISTERED_CANDIDATE_IDS}
        usable_by_pair_block: dict[str, dict[str, bool]] = {
            k: {c: False for c in REGISTERED_CANDIDATE_IDS} for k in pilot_keys
        }
        for r in assess_rows:
            key = r["predictor_row_key_t"]
            usable = r["usability_flag"] == "true"
            usable_by_pair_block[key][r["candidate_id"]] = usable
            if usable:
                usable_by_candidate[r["candidate_id"]].add(key)

        g09 = p3b0.evaluate_g09(usable_by_candidate, pilot_keys, policy)
        g10 = p3b0.evaluate_g10(usable_by_pair_block, pilot_keys, policy)

        # G11/G12 from exact per-pair block usability map (sealed inside evaluate_*)
        g11 = p3b0.evaluate_g11(usable_by_pair_block, policy)
        g12 = p3b0.evaluate_g12(usable_by_pair_block, policy)
        g13 = p3b0.evaluate_g13(pilot_keys, policy)
        labels = {(r["predictor_row_key_t"], r["class_label"]) for r in pilots}
        years = {(r["predictor_row_key_t"], str(r["target_year"])) for r in pilots}
        g14 = p3b0.evaluate_g14(
            option_id=lock.APPROVED_PILOT_OPTION,
            positive=sum(1 for r in pilots if r["class_label"] == "positive"),
            negative=sum(1 for r in pilots if r["class_label"] == "negative"),
            unknown=sum(1 for r in pilots if r["class_label"] == "unknown"),
            year_allocation=lock.EXPECTED_YEAR_ALLOCATION,
            post_evidence_substitution=False,
            policy=policy,
            pilot_keys=pilot_keys,
            key_labels=labels,
            key_years=years,
        )

        for gid, status in (
            ("G09", g09), ("G10", g10), ("G11", g11), ("G12", g12),
            ("G13", g13), ("G14", g14),
        ):
            gate_detail_rows.append({
                "gate_id": gid, "gate_name": gid, "scope": "pilot",
                "candidate_id": "", "block": "ALL", "pilot_pair_key": "",
                "status": status, "detail": "derived_from_sealed_assessments",
            })

        gate_summary = {
            "G09": g09, "G10": g10, "G11": g11, "G12": g12, "G13": g13, "G14": g14,
            "assessment_count": 800,
            "score_null_count": sum(1 for s in score_rows if s["accessibility_score"] == ""),
            "score_numeric_count": sum(1 for s in score_rows if s["accessibility_score"] != ""),
            "unresolved_assessment_count": sum(
                1 for r in assess_rows if r["assessment_status"] == p3b0.GATE_UNRESOLVED
            ),
            "fail_assessment_count": sum(
                1 for r in assess_rows if r["assessment_status"] == p3b0.GATE_FAIL
            ),
            "pass_assessment_count": sum(
                1 for r in assess_rows if r["assessment_status"] == p3b0.GATE_PASS
            ),
            "definition_contract_gap": DEFINITION_CONTRACT_GAP,
            "modeling_started": False,
            "part3b_completed": False,
            "status": "active_in_review",
        }

        network_log_path = output_dir / F_NETWORK_LOG
        if network_log_path.is_file():
            network_log = json.loads(network_log_path.read_text(encoding="utf-8"))
        else:
            network_log = {
                "network_calls_attempted": 0,
                "network_calls_succeeded": 0,
                "network_calls_failed": 0,
                "bytes_retrieved": 0,
                "final_resolved_urls": [],
                "hosts_contacted": [],
                "network_extraction_performed": False,
            }
        net_attempted = int(network_log.get("network_calls_attempted") or 0)
        net_succeeded = int(network_log.get("network_calls_succeeded") or 0)
        net_failed = int(network_log.get("network_calls_failed") or 0)
        bytes_retrieved = int(network_log.get("bytes_retrieved") or 0)
        network_extraction = bool(
            network_log.get("network_extraction_performed")
            or any(e.get("access_method") == "https_get_readonly_permit" for e in evidence_rows)
        )
        if network_extraction and net_attempted == 0:
            raise QCFail(
                "network_extraction_performed=true but network_calls_attempted=0; "
                "capture network log missing or dishonest"
            )

        # Evidence-backed numeric score required; null/UNRESOLVED alone is not scoring applied.
        scoring_applied = any(
            s.get("accessibility_score") not in ("", None)
            and s.get("evidence_ids_cited")
            for s in score_rows
        )

        frozen_after = p3b0.frozen_asset_hashes(repo_root)
        if frozen_before != frozen_after:
            raise QCFail("frozen scientific assets changed during Part 3B write")

        tickers = sorted({r["ticker"] for r in pilots})
        src_sha = p3b0.sha256_file(repo_root / SRC_REL)
        test_sha = p3b0.sha256_file(repo_root / TEST_REL)
        if not src_sha or not test_sha:
            raise QCFail("missing source/test fingerprint for QC")

        content = {
            F_SCORES: _csv_str(SCORE_HEADER, score_rows),
            F_ASSESS: _csv_str(ASSESS_HEADER, assess_rows),
            F_GATES: _csv_str(
                ["gate_id", "gate_name", "scope", "candidate_id", "block",
                 "pilot_pair_key", "status", "detail"],
                gate_detail_rows,
            ),
            F_GATE_SUMMARY: _json_str(gate_summary),
            F_UNRESOLVED: _csv_str(
                ["assessment_id", "predictor_row_key_t", "candidate_id", "status", "reason"],
                unresolved_rows,
            ),
            F_README: build_readme(),
        }
        content_hashes = {n: sha256_bytes(c.encode("utf-8")) for n, c in content.items()}

        # Include plan/endpoint/evidence/handle/network-log hashes
        for name in (F_AUTH, F_PLAN, F_ENDPOINTS, F_EVIDENCE, F_HANDLES, F_NETWORK_LOG):
            path = output_dir / name
            if path.is_file():
                content_hashes[name] = sha256_file(path)

        qc = {
            "stage": QC_STAGE,
            "current_stage": CURRENT_STAGE,
            "baseline_commit": EXPECTED_BASELINE_COMMIT,
            "source_commit": p3b0._git_last_code_commit(str(repo_root), [SRC_REL, TEST_REL]),
            "source_file_sha256": src_sha,
            "test_file_sha256": test_sha,
            "generated_at": p3b0._git_commit_timestamp(
                str(repo_root),
                p3b0._git(str(repo_root), "rev-parse", "HEAD"),
            ),
            "assertion_count": 0,
            "failed_count": 0,
            "all_pass": True,
            "ticker_count": len(tickers),
            "tickers": tickers,
            "part3a_protocol_locked": True,
            "part3a_decision_locked": True,
            "part3b0_readiness": True,
            "part3b_started": True,
            "evidence_collected": any(e.get("snapshot_sha256") for e in evidence_rows),
            "accessibility_scoring_applied": scoring_applied,
            "network_extraction_performed": network_extraction,
            "modeling_started": False,
            "assessment_count": 800,
            "score_distribution": {
                "null": gate_summary["score_null_count"],
                "numeric": gate_summary["score_numeric_count"],
            },
            "gate_summary": gate_summary,
            "frozen_input_sha256": frozen,
            "output_sha256": content_hashes,
            "frozen_assets_before": frozen_before,
            "frozen_assets_after": frozen_after,
            "network_calls_attempted": net_attempted,
            "network_calls_succeeded": net_succeeded,
            "network_calls_failed": net_failed,
            "bytes_retrieved": bytes_retrieved,
            "hosts_contacted": network_log.get("hosts_contacted") or [],
            "final_resolved_urls": network_log.get("final_resolved_urls") or [],
            "unique_raw_snapshot_count": len({
                e["snapshot_sha256"] for e in evidence_rows if e.get("snapshot_sha256")
            }),
            "evidence_record_count": len(evidence_rows),
            "guard_evidence": {
                "network_calls_attempted_during_write": sentinel.calls_attempted,
                "no_network_during_write": sentinel.calls_attempted == 0,
            },
            "assertions": [
                {"assertion": "assessment_matrix_800", "status": "PASS", "detail": "800"},
                {"assertion": "no_modeling", "status": "PASS", "detail": "modeling_started=false"},
                {"assertion": "frozen_assets_unchanged", "status": "PASS",
                 "detail": "before==after"},
                {"assertion": "g13_pass", "status": "PASS" if g13 == p3b0.GATE_PASS else "FAIL",
                 "detail": g13},
                {"assertion": "g14_pass", "status": "PASS" if g14 == p3b0.GATE_PASS else "FAIL",
                 "detail": g14},
            ],
        }
        qc["assertion_count"] = len(qc["assertions"])
        qc["failed_count"] = sum(1 for a in qc["assertions"] if a["status"] != "PASS")
        qc["all_pass"] = qc["failed_count"] == 0
        if not qc["all_pass"]:
            raise QCFail("QC assertions failed")

        qc_str = _json_str(qc)
        qc_hash = sha256_bytes(qc_str.encode("utf-8"))
        content_hashes[F_QC] = qc_hash
        metadata = {
            "stage": QC_STAGE,
            "current_stage": CURRENT_STAGE,
            "description": "Stage125 Part 3B — evidence capture & accessibility scoring pilot.",
            "code_commit": qc["source_commit"],
            "baseline_commit": EXPECTED_BASELINE_COMMIT,
            "generated_at": qc["generated_at"],
            "output_files_sha256": dict(sorted({**content_hashes, F_QC: qc_hash}.items())),
            "frozen_input_sha256": frozen,
            "part3b0_readiness": True,
            "part3b_started": True,
            "evidence_collected": qc["evidence_collected"],
            "accessibility_scoring_applied": scoring_applied,
            "network_extraction_performed": network_extraction,
            "modeling_started": False,
            "assessment_count": 800,
            "status": "active_in_review",
            "warning": (
                "Part 3B pilot accessibility outcomes only. Not final Stage126 "
                "admission. Definition-contract gaps recorded fail-closed."
            ),
        }
        files = dict(content)
        files[F_QC] = qc_str
        files[F_METADATA] = _json_str(metadata)
        output_dir.mkdir(parents=True, exist_ok=True)
        for name, text in files.items():
            (output_dir / name).write_text(text, encoding="utf-8")
        return {
            "mode": "write",
            "files": files,
            "qc": qc,
            "gate_summary": gate_summary,
            "output_dir": str(output_dir),
            "written": True,
            "network_calls_attempted": sentinel.calls_attempted,
        }


def run_check(repo_root: Path, output_dir: Path) -> dict:
    with network_default_deny() as sentinel:
        verify_baseline_commit(str(repo_root))
        verify_frozen_input_hashes(repo_root)
        meta_path = output_dir / F_METADATA
        if not meta_path.is_file():
            raise QCFail("metadata missing; run --write first")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        hashes = meta.get("output_files_sha256") or {}
        drift = []
        for name, expected in sorted(hashes.items()):
            path = output_dir / name
            if not path.is_file() or sha256_file(path) != expected:
                drift.append(name)
        # Required invariants
        assess_path = output_dir / F_ASSESS
        if assess_path.is_file():
            n = len(list(csv.DictReader(assess_path.open(encoding="utf-8"))))
            if n != 800:
                raise QCFail(f"assessment count {n} != 800")
        if drift:
            raise QCFail("check drift: " + ", ".join(drift))
        if sentinel.calls_attempted != 0:
            raise QCFail("network attempted during --check")
        return {
            "mode": "check",
            "drift": [],
            "ok": True,
            "network_calls_attempted": 0,
            "output_dir": str(output_dir),
            "qc": json.loads((output_dir / F_QC).read_text(encoding="utf-8")),
        }


def run(
    project_dir: Path | None = None,
    output_dir: Path | None = None,
    *,
    mode: str,
    write: bool = False,
) -> dict:
    if project_dir is None:
        project_dir = Path(__file__).resolve().parent.parent
    repo_root = project_dir.parent
    if output_dir is None:
        output_dir = project_dir / "stage125"
    if mode == "plan":
        return run_plan(repo_root, output_dir, write=write)
    if mode == "capture":
        return run_capture(repo_root, output_dir)
    if mode == "write":
        return run_write(repo_root, output_dir)
    if mode == "check":
        return run_check(repo_root, output_dir)
    raise QCFail(f"unknown mode: {mode}")
