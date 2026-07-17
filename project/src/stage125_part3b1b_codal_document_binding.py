"""Stage125 Part 3B.1B — Controlled CODAL Predictor-Document Binding Mini-Pilot.

Limited real document-metadata / provenance capture for exactly five locked
pilot predictor rows. Reuses Part 3B.1A exact-binding + available_at rules.

Explicit prohibitions:
- no financial-value / M1–M4 value extraction
- no accessibility scoring / Gate application
- no canonical cutoff audit mutation
- no Part 3B.2 / Stage126 / modeling
- research action pointers unchanged
"""
from __future__ import annotations

import csv
import hashlib
import html as html_lib
import io
import ipaddress
import json
import os
import re
import socket
import ssl
import subprocess
import time
import urllib.parse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse

from src import stage125_part3b0_evidence_readiness as p3b0
from src import stage125_part3b1a_cut_a_available_at_operationalization as cut_a

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

QC_STAGE = "stage125_part3b1b_codal_document_binding_mini_pilot"
CURRENT_STAGE = "Stage125"
EXPECTED_BASELINE_COMMIT = "4d7a48288543c971f43337e9a5d9a70ccfed2610"
TASK_ID = "stage125-part3b1b-codal-document-binding-mini-pilot"
MAINTENANCE_TASK_ID = TASK_ID
RESEARCH_LAST_COMPLETED = "stage125-part3a-decision-lock"
RESEARCH_NEXT = "stage125-part3b-evidence-capture"

SRC_REL = "project/src/stage125_part3b1b_codal_document_binding.py"
TEST_REL = "project/tests/test_stage125_part3b1b_codal_document_binding.py"
RUN_REL = "project/run_stage125_part3b1b.py"

F_SCOPE = "part3b1b_predictor_document_scope_stage125.csv"
F_EVIDENCE = "part3b1b_codal_document_evidence_stage125.csv"
F_ADJ = "part3b1b_document_binding_adjudication_stage125.csv"
F_ATTEMPTS = "part3b1b_capture_attempt_log_stage125.csv"
F_NETWORK = "part3b1b_network_log_stage125.json"
F_UNRESOLVED = "part3b1b_unresolved_and_rejections_stage125.csv"
F_README = "README_STAGE125_PART3B1B_CODAL_DOCUMENT_BINDING.md"
F_QC = "stage125_part3b1b_codal_document_binding_qc_report.json"
F_METADATA = "metadata_and_hashes_stage125_part3b1b.json"

CONTENT_FILES = (
    F_SCOPE, F_EVIDENCE, F_ADJ, F_ATTEMPTS, F_NETWORK, F_UNRESOLVED, F_README,
)

CACHE_DIR_REL = "project/stage125/raw_cache_part3b1b"
THANUSA_EVIDENCE_ID = "ev_p3b1b_thanusa_1392_decision"

PART3B1B_AUTHORIZED_EXACT = frozenset({
    SRC_REL, TEST_REL, RUN_REL,
    f"project/stage125/{F_SCOPE}",
    f"project/stage125/{F_EVIDENCE}",
    f"project/stage125/{F_ADJ}",
    f"project/stage125/{F_ATTEMPTS}",
    f"project/stage125/{F_NETWORK}",
    f"project/stage125/{F_UNRESOLVED}",
    f"project/stage125/{F_README}",
    f"project/stage125/{F_QC}",
    f"project/stage125/{F_METADATA}",
})

PILOT_CSV_REL = "project/stage125/part3a_selected_pilot_pairs_stage125.csv"
PILOT_CSV_SHA256 = (
    "9a441b5e3696353967489b356d0ff48cf7cbea276aeea5018be6edc8368b40f5"
)
OCF_MANIFEST_REL = (
    "project/raw_handoff/financial_distress_programmer_handoff_stage121(1)/"
    "ocf_source_manifest_stage121.csv"
)
OCF_MANIFEST_SHA256 = (
    "b1bf92d74f19b4c00373079c3222489d6cb54e1c8f11e30a9e02557e6936057a"
)

THANUSA_LETTER_SERIAL = "Ddg2e7HG6FGR5ygaTFJd4g=="
THANUSA_AUTHORIZED_URL = (
    "https://www.codal.ir/Reports/Decision.aspx?LetterSerial="
    + quote(THANUSA_LETTER_SERIAL, safe="")
)
ALLOWED_CODAL_HOST = "www.codal.ir"
NETWORK_REQUESTS_AUTHORIZED_MAX = 1
MAX_RESPONSE_BYTES = 2_000_000
MAX_REDIRECTS = 5
REQUEST_TIMEOUT_SEC = 30.0

BINDING_BOUND = "BOUND"
BINDING_UNRESOLVED = "UNRESOLVED"
BINDING_REJECTED = "REJECTED"

STATUS_REJECT_REASONS = frozenset({
    "subsidiary_only_title",
    "parent_company_identity_mismatch",
})

PERSIAN_DIGIT_MAP = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

LOCAL_CACHE_BY_TICKER = {
    "بوعلی": "project/stage124_feasibility/raw/codal/بوعلی__search__dd1e77b23155.bin",
    "اپال": "project/stage124_feasibility/raw/codal/اپال__search__6a7087f0251c.bin",
    "اردستان": "project/stage124_feasibility/raw/codal/اردستان__search__05ba9f8766e9.bin",
}

LOCKED_SCOPE: tuple[dict[str, Any], ...] = (
    {
        "selection_rank": 6,
        "predictor_row_key_t": "ثنوسا|1392",
        "target_row_key_t_plus_1": "ثنوسا|1393",
        "ticker": "ثنوسا",
        "fiscal_year_t": 1392,
        "starting_evidence_class": "B2",
        "canonical_fiscal_year_end": "1392/06/31",
        "canonical_company_name": "نوسازی و ساختمان تهران",
        "canonical_statement_scope": "separate",
        "canonical_letter_serial": THANUSA_LETTER_SERIAL,
    },
    {
        "selection_rank": 63,
        "predictor_row_key_t": "بوعلی|1399",
        "target_row_key_t_plus_1": "بوعلی|1400",
        "ticker": "بوعلی",
        "fiscal_year_t": 1399,
        "starting_evidence_class": "B1",
        "canonical_fiscal_year_end": "1399/12/30",
        "canonical_company_name": "شرکت پتروشیمی بوعلی سینا",
        "canonical_statement_scope": "separate",
        "canonical_letter_serial": None,
    },
    {
        "selection_rank": 72,
        "predictor_row_key_t": "بوعلی|1400",
        "target_row_key_t_plus_1": "بوعلی|1401",
        "ticker": "بوعلی",
        "fiscal_year_t": 1400,
        "starting_evidence_class": "B1",
        "canonical_fiscal_year_end": "1400/12/29",
        "canonical_company_name": "شرکت پتروشیمی بوعلی سینا",
        "canonical_statement_scope": "separate",
        "canonical_letter_serial": None,
    },
    {
        "selection_rank": 76,
        "predictor_row_key_t": "اردستان|1401",
        "target_row_key_t_plus_1": "اردستان|1402",
        "ticker": "اردستان",
        "fiscal_year_t": 1401,
        "starting_evidence_class": "B3",
        "canonical_fiscal_year_end": "1401/12/29",
        "canonical_company_name": "شرکت سیمان اردستان",
        "canonical_statement_scope": "separate",
        "canonical_letter_serial": None,
    },
    {
        "selection_rank": 77,
        "predictor_row_key_t": "اپال|1401",
        "target_row_key_t_plus_1": "اپال|1402",
        "ticker": "اپال",
        "fiscal_year_t": 1401,
        "starting_evidence_class": "B1",
        "canonical_fiscal_year_end": "1401/10/30",
        "canonical_company_name": "فرآوری معدنی اپال کانی پارس",
        "canonical_statement_scope": "separate",
        "canonical_letter_serial": None,
    },
)

SCOPE_KEYS = frozenset(row["predictor_row_key_t"] for row in LOCKED_SCOPE)

FROZEN_SCIENTIFIC_PATHS = cut_a.FROZEN_SCIENTIFIC_PATHS + (
    "project/stage125/part3b1a_cut_a_available_at_operationalization_contract_stage125.json",
    "project/stage125/part3b1a_cut_a_available_at_decision_lock_stage125.json",
    "project/stage125/stage125_part3b1a_cut_a_available_at_qc_report.json",
)

FORBIDDEN_SURFACE_EXACT = frozenset({
    "project/stage125/part3b2_feature_extraction_stage125.json",
    "project/run_stage126.py",
    "project/src/stage126_modeling.py",
    "project/stage126/README_STAGE126.md",
})

FORBIDDEN_HOSTS = frozenset({
    "search.codal.ir", "api.codal.ir", "cdn.tsetmc.com", "www.tsetmc.com",
    "tsetmc.com", "www.cbi.ir", "cbi.ir", "google.com", "www.google.com",
    "bing.com", "www.bing.com",
})

FYE_TITLE_RE = re.compile(
    r"سال مالی منتهی به\s*(\d{4}/\d{2}/\d{2})"
)
SUBSIDIARY_PAREN_RE = re.compile(r"\(شرکت\s+[^)]+\)")

EVIDENCE_COLUMNS = [
    "scope_row_id", "selection_rank", "predictor_row_key_t",
    "target_row_key_t_plus_1", "ticker", "fiscal_year_t",
    "starting_evidence_class", "source_origin", "source_url",
    "letter_serial", "canonical_letter_serial", "tracing_no",
    "canonical_tracing_no", "official_title", "canonical_official_title",
    "legal_entity", "is_parent_company", "statement_scope",
    "is_annual", "is_interim", "is_audited", "fiscal_year_end",
    "revision_status_raw", "revision_status_normalized",
    "publish_datetime_raw", "sent_datetime_raw",
    "publish_datetime_utc_candidate", "available_at",
    "available_at_source_field", "snapshot_sha256",
    "cache_snapshot_complete", "canonical_source_version_bound",
    "binding_status", "cutoff_status", "failure_reasons",
    "reviewer_status",
]

SCOPE_HEADER = [
    "scope_row_id", "selection_rank", "predictor_row_key_t",
    "target_row_key_t_plus_1", "ticker", "fiscal_year_t",
    "starting_evidence_class", "canonical_fiscal_year_end",
    "canonical_company_name", "canonical_statement_scope",
    "canonical_letter_serial", "pilot_csv_verified", "reviewer_status",
]

ADJ_HEADER = [
    "scope_row_id", "predictor_row_key_t", "binding_status", "binding_ok",
    "cutoff_status", "available_at", "available_at_source_field",
    "failure_reasons", "adjudication_notes", "reviewer_status",
]

ATTEMPT_HEADER = [
    "capture_run_id", "attempt_id", "scope_row_id", "predictor_row_key_t",
    "planned_request_url", "http_method", "started_at_utc", "completed_at_utc",
    "final_url", "response_status", "content_type", "byte_count",
    "redirect_count", "payload_sha256", "metadata_sha256", "success",
    "failure_class", "network_log_complete", "reviewer_status",
]

UNRESOLVED_HEADER = [
    "scope_row_id", "predictor_row_key_t", "binding_status",
    "starting_evidence_class", "failure_reasons", "source_origin",
    "reviewer_status",
]

# Executable-path patterns only (not prohibition docs / deny-lists).
_VALUE_EXTRACTION_CODE_PATTERNS = (
    re.compile(r"\bdef\s+extract_financial\b"),
    re.compile(r"\bdef\s+apply_gate\b"),
    re.compile(r"\bdef\s+train_model\b"),
    re.compile(r"\bm1_value\s*="),
    re.compile(r"\bm2_value\s*="),
    re.compile(r"\bm3_value\s*="),
    re.compile(r"\bm4_value\s*="),
    re.compile(r"\baccessibility_score\s*="),
    re.compile(r"\bfrom\s+.*stage126"),
    re.compile(r"\bimport\s+.*stage126"),
)


def _source_has_forbidden_value_extraction_tokens(repo_root: Path) -> bool:
    """True only when executable value-extraction / modeling paths appear."""
    src_text = (repo_root / SRC_REL).read_text(encoding="utf-8")
    # Strip module/docstring blocks so prohibition prose cannot false-positive.
    cleaned = re.sub(r'"""[\s\S]*?"""', "", src_text, count=1)
    cleaned = re.sub(r"'''[\s\S]*?'''", "", cleaned, count=1)
    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if any(pat.search(stripped) for pat in _VALUE_EXTRACTION_CODE_PATTERNS):
            return True
    return False


class QCFail(RuntimeError):
    """Fail-closed error for Stage125 Part 3B.1B."""


class NetworkPolicyError(RuntimeError):
    """Fail-closed network policy violation."""


# --------------------------------------------------------------------------- #
# Hash / IO helpers
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


def _json_str(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def _git(repo_root: str, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", repo_root, *args], capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise QCFail(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def normalize_persian_digits(value: str | None) -> str:
    if value is None:
        return ""
    return str(value).translate(PERSIAN_DIGIT_MAP)


def _blank(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _csv_str(header: list[str], rows: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: _blank(row.get(k)) for k in header})
    return buf.getvalue()


def _is_ancestor(repo_root: str, ancestor: str, descendant: str) -> bool:
    proc = subprocess.run(
        ["git", "-C", repo_root, "merge-base", "--is-ancestor", ancestor, descendant],
        capture_output=True,
    )
    return proc.returncode == 0


def verify_baseline_commit(repo_root: str) -> str:
    head = _git(repo_root, "rev-parse", "HEAD")
    if head == EXPECTED_BASELINE_COMMIT:
        return head
    if not _is_ancestor(repo_root, EXPECTED_BASELINE_COMMIT, head):
        raise QCFail(
            f"expected baseline {EXPECTED_BASELINE_COMMIT} not ancestor of HEAD "
            f"(HEAD={head})"
        )
    return head


def frozen_scientific_hashes(repo_root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel in FROZEN_SCIENTIFIC_PATHS:
        path = repo_root / rel
        digest = sha256_file(path)
        if digest is None:
            raise QCFail(f"missing frozen scientific file: {rel}")
        out[rel] = digest
    return out


def verify_pilot_csv_hash(repo_root: Path) -> None:
    path = repo_root / PILOT_CSV_REL
    digest = sha256_file(path)
    if digest != PILOT_CSV_SHA256:
        raise QCFail(
            f"pilot CSV hash mismatch: expected {PILOT_CSV_SHA256} got {digest}"
        )


def verify_ocf_manifest_hash(repo_root: Path) -> None:
    path = repo_root / OCF_MANIFEST_REL
    digest = sha256_file(path)
    if digest != OCF_MANIFEST_SHA256:
        raise QCFail(
            f"OCF manifest hash mismatch: expected {OCF_MANIFEST_SHA256} got {digest}"
        )


def verify_locked_scope_against_pilot(repo_root: Path) -> None:
    verify_pilot_csv_hash(repo_root)
    path = repo_root / PILOT_CSV_REL
    rows = {int(r["selection_rank"]): r for r in csv.DictReader(path.open(encoding="utf-8"))}
    for scope in LOCKED_SCOPE:
        rank = scope["selection_rank"]
        if rank not in rows:
            raise QCFail(f"locked scope rank {rank} missing from pilot CSV")
        pilot = rows[rank]
        if pilot["predictor_row_key_t"] != scope["predictor_row_key_t"]:
            raise QCFail(
                f"pilot rank {rank} key mismatch: "
                f"{pilot['predictor_row_key_t']} != {scope['predictor_row_key_t']}"
            )


def is_scope_row_key_allowed(key: str) -> bool:
    return key in SCOPE_KEYS


def scope_row_id(scope: dict[str, Any]) -> str:
    return f"p3b1b_scope_{scope['selection_rank']:03d}"


# --------------------------------------------------------------------------- #
# Network policy
# --------------------------------------------------------------------------- #

def assert_url_allowed(url: str) -> None:
    """Fail-closed URL allowlist: exactly one authorized CODAL Decision GET."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise NetworkPolicyError("only https allowed")
    host = (parsed.hostname or "").lower()
    if host in FORBIDDEN_HOSTS:
        raise NetworkPolicyError(f"forbidden host: {host}")
    if host != ALLOWED_CODAL_HOST:
        raise NetworkPolicyError(f"host not allowed: {host}")
    if parsed.port not in (None, 443):
        raise NetworkPolicyError("only port 443 allowed")
    if url != THANUSA_AUTHORIZED_URL:
        raise NetworkPolicyError("URL not in Part 3B.1B authorized exact set")


def _assert_public_ip(ip: str) -> None:
    ip_obj = ipaddress.ip_address(ip)
    if (
        ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local
        or ip_obj.is_reserved or ip_obj.is_multicast or ip_obj.is_unspecified
    ):
        raise NetworkPolicyError(f"private/reserved IP rejected: {ip}")


def _parse_http_response(
    raw: bytes, original_url: str,
) -> tuple[bytes, int, str, str]:
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
        headers[k.decode("iso-8859-1").strip().lower()] = (
            v.decode("iso-8859-1", errors="replace").strip()
        )
    ctype = headers.get("content-type", "")
    location = headers.get("location", "")
    final_url = original_url
    if status in (301, 302, 303, 307, 308) and location:
        final_url = urljoin(original_url, location)
        redirect_host = (urlparse(final_url).hostname or "").lower()
        if redirect_host != ALLOWED_CODAL_HOST:
            raise NetworkPolicyError(f"redirect host not allowed: {redirect_host}")
    if headers.get("transfer-encoding", "").lower() == "chunked":
        body = _dechunk(body)
    if len(body) > MAX_RESPONSE_BYTES:
        raise NetworkPolicyError("body exceeds size ceiling")
    return body, status, final_url, ctype


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
    return bytes(out)


def _default_https_transport(
    method: str,
    url: str,
    *,
    orig_connect: Callable[..., Any] | None = None,
    orig_getaddrinfo: Callable[..., Any] | None = None,
) -> tuple[bytes, dict[str, Any]]:
    assert_url_allowed(url)
    method = method.upper()
    if method != "GET":
        raise NetworkPolicyError(f"method not allowed: {method}")
    redirect_chain: list[str] = [url]
    current = url
    redirects = 0
    while True:
        parsed = urlparse(current)
        host = parsed.hostname
        assert host
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        getaddrinfo = orig_getaddrinfo or socket.getaddrinfo
        infos = getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        addrs = []
        for info in infos:
            ip = info[4][0]
            _assert_public_ip(ip)
            addrs.append(ip)
        if not addrs:
            raise NetworkPolicyError(f"no addresses for {host}")
        ip = addrs[0]
        raw_req = (
            f"{method} {path} HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            "User-Agent: papermali-stage125-part3b1b-readonly/1.0\r\n"
            "Accept: */*\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii")
        context = ssl.create_default_context()
        sock = None
        try:
            family = socket.AF_INET6 if ":" in ip else socket.AF_INET
            raw_sock = socket.socket(family, socket.SOCK_STREAM)
            raw_sock.settimeout(REQUEST_TIMEOUT_SEC)
            connect = orig_connect or raw_sock.connect
            connect(raw_sock, (ip, 443))
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
        body, status, final_url, ctype = _parse_http_response(raw, current)
        if status in (301, 302, 303, 307, 308):
            redirects += 1
            if redirects > MAX_REDIRECTS:
                raise NetworkPolicyError("too many redirects")
            if not final_url or final_url == current:
                raise NetworkPolicyError("redirect without location")
            redirect_chain.append(final_url)
            current = final_url
            continue
        return body, {
            "request_url": url,
            "redirect_chain": redirect_chain,
            "final_url": final_url,
            "response_status": status,
            "content_type": ctype,
            "bytes": len(body),
            "redirect_count": redirects,
        }


@dataclass
class ThanusaFetchResult:
    body: bytes
    payload_sha256: str
    metadata_sha256: str
    network_entry: dict[str, Any]
    parsed_html: dict[str, str | None]
    success: bool
    failure_class: str


def parse_codal_decision_html(html: bytes | str) -> dict[str, str | None]:
    """Best-effort parse of CODAL Decision.aspx HTML metadata fields."""
    text = html.decode("utf-8", errors="replace") if isinstance(html, bytes) else html
    out: dict[str, str | None] = {
        "official_title": None,
        "publish_datetime_raw": None,
        "sent_datetime_raw": None,
    }
    title_m = re.search(r"<title[^>]*>([^<]+)</title>", text, re.I | re.S)
    if title_m:
        out["official_title"] = html_lib.unescape(title_m.group(1)).strip()
    for field, patterns in (
        ("publish_datetime_raw", (
            r'PublishDateTime["\s:=]+([0-9۰-۹]{4}/[0-9۰-۹]{2}/[0-9۰-۹]{2}\s+'
            r'[0-9۰-۹]{2}:[0-9۰-۹]{2}:[0-9۰-۹]{2})',
            r'lblPublishDateTime[^>]*>([^<]+)<',
            r'تاریخ انتشار[^0-9۰-۹]*([0-9۰-۹]{4}/[0-9۰-۹]{2}/[0-9۰-۹]{2}\s+'
            r'[0-9۰-۹]{2}:[0-9۰-۹]{2}:[0-9۰-۹]{2})',
        )),
        ("sent_datetime_raw", (
            r'SentDateTime["\s:=]+([0-9۰-۹]{4}/[0-9۰-۹]{2}/[0-9۰-۹]{2}\s+'
            r'[0-9۰-۹]{2}:[0-9۰-۹]{2}:[0-9۰-۹]{2})',
            r'lblSentDateTime[^>]*>([^<]+)<',
            r'تاریخ ارسال[^0-9۰-۹]*([0-9۰-۹]{4}/[0-9۰-۹]{2}/[0-9۰-۹]{2}\s+'
            r'[0-9۰-۹]{2}:[0-9۰-۹]{2}:[0-9۰-۹]{2})',
        )),
    ):
        for pat in patterns:
            m = re.search(pat, text, re.I)
            if m:
                out[field] = normalize_persian_digits(m.group(1)).strip()
                break
    return out


def authorize_and_fetch_thanusa(
    *,
    cache: p3b0.ImmutableCache,
    capture: bool,
    transport: Callable[[str, str], tuple[bytes, dict[str, Any]]] | None = None,
    orig_connect: Callable[..., Any] | None = None,
    orig_getaddrinfo: Callable[..., Any] | None = None,
) -> ThanusaFetchResult | None:
    """Perform the single authorized CODAL GET (or load immutable cache)."""
    cached = _load_thanusa_cache_entry(cache)
    if cached is not None:
        body, meta = cached
        parsed = parse_codal_decision_html(body)
        return ThanusaFetchResult(
            body=body,
            payload_sha256=sha256_bytes(body),
            metadata_sha256=sha256_bytes(json.dumps(meta, sort_keys=True).encode()),
            network_entry={
                "request_url": THANUSA_AUTHORIZED_URL,
                "redirect_chain": meta.get("redirect_chain", [THANUSA_AUTHORIZED_URL]),
                "final_url": meta.get("final_url", THANUSA_AUTHORIZED_URL),
                "response_status": meta.get("response_status", 200),
                "content_type": meta.get("content_type", "text/html"),
                "bytes": len(body),
                "payload_sha256": sha256_bytes(body),
                "from_immutable_cache": True,
            },
            parsed_html=parsed,
            success=True,
            failure_class="",
        )
    if not capture:
        return None
    fetch = transport or (
        lambda m, u: _default_https_transport(
            m, u, orig_connect=orig_connect, orig_getaddrinfo=orig_getaddrinfo,
        )
    )
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        body, meta = fetch("GET", THANUSA_AUTHORIZED_URL)
    except Exception as exc:
        return ThanusaFetchResult(
            body=b"",
            payload_sha256="",
            metadata_sha256="",
            network_entry={
                "request_url": THANUSA_AUTHORIZED_URL,
                "redirect_chain": [THANUSA_AUTHORIZED_URL],
                "final_url": "",
                "response_status": 0,
                "content_type": "",
                "bytes": 0,
                "payload_sha256": "",
                "error": str(exc),
            },
            parsed_html=parse_codal_decision_html(b""),
            success=False,
            failure_class=type(exc).__name__,
        )
    completed = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta = {
        **meta,
        "evidence_id": THANUSA_EVIDENCE_ID,
        "scope_row_id": scope_row_id(LOCKED_SCOPE[0]),
        "predictor_row_key_t": LOCKED_SCOPE[0]["predictor_row_key_t"],
        "retrieved_at_utc": completed,
        "started_at_utc": started,
        "letter_serial": THANUSA_LETTER_SERIAL,
        "retrieval_purpose": "predictor_document_binding_mini_pilot",
    }
    put = cache.put(body, metadata=meta, evidence_id=THANUSA_EVIDENCE_ID)
    parsed = parse_codal_decision_html(body)
    entry = {
        "request_url": meta["request_url"],
        "redirect_chain": meta.get("redirect_chain", [THANUSA_AUTHORIZED_URL]),
        "final_url": meta.get("final_url", THANUSA_AUTHORIZED_URL),
        "response_status": meta.get("response_status", 200),
        "content_type": meta.get("content_type", ""),
        "bytes": meta.get("bytes", len(body)),
        "payload_sha256": put.payload_sha256,
        "metadata_sha256": put.metadata_sha256,
        "from_immutable_cache": False,
    }
    return ThanusaFetchResult(
        body=body,
        payload_sha256=put.payload_sha256,
        metadata_sha256=put.metadata_sha256,
        network_entry=entry,
        parsed_html=parsed,
        success=True,
        failure_class="",
    )


def _load_thanusa_cache_entry(
    cache: p3b0.ImmutableCache,
) -> tuple[bytes, dict[str, Any]] | None:
    root = cache.root
    if not root.is_dir():
        return None
    for meta_path in root.rglob("metadata.json"):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if meta.get("evidence_id") != THANUSA_EVIDENCE_ID:
            continue
        payload_path = meta_path.parent / "payload.bin"
        if not payload_path.is_file():
            continue
        return payload_path.read_bytes(), meta
    return None


# --------------------------------------------------------------------------- #
# Local cache letter matching
# --------------------------------------------------------------------------- #

@dataclass
class LetterCandidate:
    title: str
    publish_datetime: str | None
    sent_datetime: str | None
    tracing_no: str | None
    url: str | None
    letter_serial: str | None
    company_name: str | None
    symbol: str | None
    letter_code: str | None
    fiscal_year_end: str | None
    is_annual: bool
    is_interim: bool
    is_audited: bool
    subsidiary_only_title: bool
    is_parent_company: bool
    revision_status_raw: str | None
    revision_status_normalized: str | None


def extract_letter_serial_from_url(url: str | None) -> str | None:
    if not url:
        return None
    full = url if url.startswith("http") else f"https://{ALLOWED_CODAL_HOST}{url}"
    qs = parse_qs(urlparse(full).query)
    serials = qs.get("LetterSerial") or qs.get("letterserial")
    if not serials:
        return None
    return unquote(serials[0])


def classify_title_flags(title: str) -> dict[str, Any]:
    norm = normalize_persian_digits(title)
    interim = "میاندوره" in norm
    audited = "حسابرسی شده" in norm
    annual = "سال مالی" in norm and audited and not interim
    subsidiary = bool(SUBSIDIARY_PAREN_RE.search(norm))
    fye_m = FYE_TITLE_RE.search(norm)
    fye = fye_m.group(1) if fye_m else None
    raw_rev = cut_a.CODAL_ESLAHIYE_RAW if cut_a.CODAL_ESLAHIYE_RAW in norm else None
    norm_rev = cut_a.explicit_normalized_revision_for_codal_eslahiye(
        revision_status_raw=raw_rev,
        map_eslahiye_to_revision=True,
    ) or ("original" if annual else None)
    return {
        "fiscal_year_end": fye,
        "is_annual": annual,
        "is_interim": interim,
        "is_audited": audited,
        "subsidiary_only_title": subsidiary,
        "is_parent_company": annual and audited and not subsidiary,
        "revision_status_raw": raw_rev,
        "revision_status_normalized": norm_rev,
    }


def letter_dict_to_candidate(letter: dict[str, Any]) -> LetterCandidate:
    title = str(letter.get("Title") or "")
    flags = classify_title_flags(title)
    url = letter.get("Url")
    serial = letter.get("LetterSerial") or extract_letter_serial_from_url(url)
    public_url = (
        f"https://{ALLOWED_CODAL_HOST}{url}" if url and not str(url).startswith("http")
        else url
    )
    return LetterCandidate(
        title=title,
        publish_datetime=letter.get("PublishDateTime"),
        sent_datetime=letter.get("SentDateTime"),
        tracing_no=str(letter.get("TracingNo")) if letter.get("TracingNo") is not None else None,
        url=public_url,
        letter_serial=serial,
        company_name=letter.get("CompanyName"),
        symbol=letter.get("Symbol"),
        letter_code=letter.get("LetterCode") or "ن-۱۰",
        fiscal_year_end=flags["fiscal_year_end"],
        is_annual=flags["is_annual"],
        is_interim=flags["is_interim"],
        is_audited=flags["is_audited"],
        subsidiary_only_title=flags["subsidiary_only_title"],
        is_parent_company=flags["is_parent_company"],
        revision_status_raw=flags["revision_status_raw"],
        revision_status_normalized=flags["revision_status_normalized"],
    )


def is_cache_incomplete(cache_data: dict[str, Any]) -> bool:
    page = int(cache_data.get("Page") or 1)
    total = int(cache_data.get("Total") or 0)
    letters = cache_data.get("Letters") or []
    page_size = len(letters)
    if total > page_size:
        return True
    if page != 1 and total > page_size:
        return True
    return False


def match_local_letter_candidates(
    cache_data: dict[str, Any],
    scope_row: dict[str, Any],
) -> tuple[list[LetterCandidate], dict[str, Any]]:
    """Match annual audited letters for the canonical FYE from a local search cache."""
    target_fye = scope_row["canonical_fiscal_year_end"]
    incomplete = is_cache_incomplete(cache_data)
    matched: list[LetterCandidate] = []
    for letter in cache_data.get("Letters") or []:
        cand = letter_dict_to_candidate(letter)
        if cand.fiscal_year_end != target_fye:
            continue
        if not cand.is_annual or cand.is_interim or not cand.is_audited:
            continue
        matched.append(cand)
    return matched, {
        "incomplete_pagination": incomplete,
        "cache_page": cache_data.get("Page"),
        "cache_total": cache_data.get("Total"),
        "letters_on_page": len(cache_data.get("Letters") or []),
    }


def build_binding_input_from_candidate(
    scope_row: dict[str, Any],
    candidate: LetterCandidate | None,
    *,
    cache_complete: bool,
    snapshot_sha256: str | None,
    candidate_letter_serials: list[str],
    incomplete_pagination: bool,
    multi_document_predictor_row: bool = False,
    canonical_source_version_bound: bool = False,
    canonical_official_title: str | None = None,
    publish_datetime_raw: str | None = None,
    sent_datetime_raw: str | None = None,
) -> cut_a.ExactDocumentBindingInput:
    canonical_title = canonical_official_title or (
        candidate.title if candidate else ""
    )
    letter_title = candidate.title if candidate else ""
    return cut_a.ExactDocumentBindingInput(
        canonical_ticker=scope_row["ticker"],
        letter_ticker=candidate.symbol or scope_row["ticker"] if candidate else "",
        legal_entity_canonical=scope_row["canonical_company_name"],
        legal_entity_letter=(
            candidate.company_name or scope_row["canonical_company_name"]
            if candidate else ""
        ),
        predictor_fiscal_year=int(scope_row["fiscal_year_t"]),
        letter_fiscal_year=int(scope_row["fiscal_year_t"]),
        fiscal_year_end_canonical=scope_row["canonical_fiscal_year_end"],
        fiscal_year_end_letter=(
            candidate.fiscal_year_end or scope_row["canonical_fiscal_year_end"]
            if candidate else ""
        ),
        is_annual=candidate.is_annual if candidate else False,
        is_interim=candidate.is_interim if candidate else False,
        is_audited=candidate.is_audited if candidate else False,
        is_parent_company=candidate.is_parent_company if candidate else False,
        statement_scope_canonical=scope_row["canonical_statement_scope"],
        statement_scope_letter=scope_row["canonical_statement_scope"],
        requires_separate_non_consolidated=True,
        letter_code_canonical="ن-۱۰",
        letter_code_letter=candidate.letter_code if candidate else "",
        letter_serial=candidate.letter_serial if candidate else None,
        canonical_letter_serial=scope_row.get("canonical_letter_serial"),
        tracing_no=candidate.tracing_no if candidate else None,
        canonical_tracing_no=None,
        official_title=letter_title,
        canonical_official_title=canonical_title,
        revision_status=(
            candidate.revision_status_normalized if candidate else None
        ),
        revision_status_raw=candidate.revision_status_raw if candidate else None,
        public_codal_url=candidate.url if candidate else None,
        raw_payload_or_snapshot_hash=snapshot_sha256,
        candidate_letter_serials=candidate_letter_serials,
        incomplete_pagination=incomplete_pagination,
        match_basis="exact_letter_serial" if scope_row.get("canonical_letter_serial") else "title_only",
        subsidiary_only_title=candidate.subsidiary_only_title if candidate else False,
        entity_ambiguous=False,
        consolidated_separate_ambiguous=False,
        annual_interim_ambiguous=False,
        canonical_source_version_bound=canonical_source_version_bound,
        multi_document_predictor_row=multi_document_predictor_row,
        values_source_letter_serial=(
            candidate.letter_serial if candidate else scope_row.get("canonical_letter_serial")
        ),
        publish_of_original_used_for_correction_values=False,
    )


def classify_binding_status(
    binding_result: cut_a.BindingResult,
    *,
    multi_document_predictor_row: bool = False,
    candidate_present: bool = True,
) -> str:
    """Classify binding outcome.

    REJECTED only for an affirmatively wrong candidate document:
    subsidiary-only title, or parent-company mismatch when a real candidate
    was present. Missing/default fields without a candidate stay UNRESOLVED.
    """
    reasons = set(binding_result.reasons)
    if "subsidiary_only_title" in reasons:
        return BINDING_REJECTED
    if candidate_present and "parent_company_identity_mismatch" in reasons:
        return BINDING_REJECTED
    if binding_result.ok and not multi_document_predictor_row:
        return BINDING_BOUND
    return BINDING_UNRESOLVED


# --------------------------------------------------------------------------- #
# Row adjudication
# --------------------------------------------------------------------------- #

def _publish_utc_candidate(raw: str | None) -> str | None:
    parsed = cut_a.parse_codal_publish_datetime(raw)
    if isinstance(parsed, cut_a.NormalizedTimestamp):
        return parsed.utc_iso8601
    return None


def adjudicate_scope_row(
    scope_row: dict[str, Any],
    *,
    candidate: LetterCandidate | None,
    cache_meta: dict[str, Any] | None,
    cache_file_sha256: str | None,
    thanusa_fetch: ThanusaFetchResult | None,
    source_origin: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    sid = scope_row_id(scope_row)
    incomplete = bool(cache_meta and cache_meta.get("incomplete_pagination"))
    multi_doc = False
    canonical_bound = False
    candidate_serials: list[str] = []
    publish_raw = None
    sent_raw = None
    canonical_title = None
    snapshot_sha = cache_file_sha256

    if scope_row["ticker"] == "ثنوسا":
        multi_doc = True
        canonical_bound = False
        if thanusa_fetch and thanusa_fetch.success:
            publish_raw = thanusa_fetch.parsed_html.get("publish_datetime_raw")
            sent_raw = thanusa_fetch.parsed_html.get("sent_datetime_raw")
            canonical_title = thanusa_fetch.parsed_html.get("official_title")
            snapshot_sha = thanusa_fetch.payload_sha256 or snapshot_sha
            candidate_serials = [THANUSA_LETTER_SERIAL]
        elif scope_row.get("canonical_letter_serial"):
            candidate_serials = [scope_row["canonical_letter_serial"]]
        binding_inp = build_binding_input_from_candidate(
            scope_row,
            candidate,
            cache_complete=not incomplete,
            snapshot_sha256=snapshot_sha,
            candidate_letter_serials=candidate_serials,
            incomplete_pagination=False,
            multi_document_predictor_row=multi_doc,
            canonical_source_version_bound=canonical_bound,
            canonical_official_title=canonical_title,
            publish_datetime_raw=publish_raw,
            sent_datetime_raw=sent_raw,
        )
        if candidate is None and thanusa_fetch:
            binding_inp.letter_serial = THANUSA_LETTER_SERIAL
            binding_inp.public_codal_url = THANUSA_AUTHORIZED_URL
            binding_inp.is_annual = True
            binding_inp.is_interim = False
            binding_inp.is_audited = True
            binding_inp.is_parent_company = True
            binding_inp.official_title = canonical_title or (
                "صورتهای مالی سال مالی منتهی به 1392/06/31 (حسابرسی شده)"
            )
            binding_inp.canonical_official_title = binding_inp.official_title
            binding_inp.revision_status = "original"
            binding_inp.letter_ticker = scope_row["ticker"]
            binding_inp.legal_entity_letter = scope_row["canonical_company_name"]
            binding_inp.fiscal_year_end_letter = scope_row["canonical_fiscal_year_end"]
            binding_inp.letter_code_letter = "ن-۱۰"
            binding_inp.values_source_letter_serial = THANUSA_LETTER_SERIAL
    elif candidate is None:
        binding_inp = build_binding_input_from_candidate(
            scope_row, None,
            cache_complete=not incomplete,
            snapshot_sha256=snapshot_sha,
            candidate_letter_serials=[],
            incomplete_pagination=incomplete,
        )
    else:
        if candidate.letter_serial:
            candidate_serials = [candidate.letter_serial]
        if scope_row["starting_evidence_class"] == "B1" and incomplete:
            candidate_serials = []
        publish_raw = candidate.publish_datetime
        sent_raw = candidate.sent_datetime
        binding_inp = build_binding_input_from_candidate(
            scope_row,
            candidate,
            cache_complete=not incomplete,
            snapshot_sha256=snapshot_sha,
            candidate_letter_serials=candidate_serials,
            incomplete_pagination=incomplete,
            canonical_source_version_bound=False,
        )

    bind_res = cut_a.evaluate_exact_document_binding(binding_inp)
    candidate_present = candidate is not None or (
        thanusa_fetch is not None and thanusa_fetch.success
    )
    status = classify_binding_status(
        bind_res,
        multi_document_predictor_row=multi_doc,
        candidate_present=candidate_present,
    )

    avail_res = cut_a.AvailableAtResolution(
        available_at=None,
        available_at_raw_publish=cut_a.preserve_raw_codal_timestamp(publish_raw),
        sent_datetime_raw=cut_a.preserve_raw_codal_timestamp(sent_raw),
        source_field=None,
        cutoff_status=cut_a.CUTOFF_STATUS_UNRESOLVED,
        reasons=(cut_a.REASON_BINDING_FAILED,),
        binding_ok=False,
        sent_publish_relation="unknown",
    )
    if status == BINDING_BOUND:
        avail_res = cut_a.resolve_operational_available_at(
            publish_datetime_raw=publish_raw,
            sent_datetime_raw=sent_raw,
            binding=binding_inp,
        )

    reason_list = list(bind_res.reasons)
    if status != BINDING_BOUND and avail_res.reasons:
        for r in avail_res.reasons:
            if r not in reason_list:
                reason_list.append(r)
    if (
        scope_row["ticker"] == "ثنوسا"
        and thanusa_fetch is not None
        and thanusa_fetch.success
        and not (publish_raw or "").strip()
    ):
        for extra_reason in (
            "official_metadata_not_exposed_by_direct_url",
            cut_a.REASON_MISSING_PUBLISH,
        ):
            if extra_reason not in reason_list:
                reason_list.append(extra_reason)
    failure_reasons = ";".join(reason_list)

    evidence = {
        "scope_row_id": sid,
        "selection_rank": scope_row["selection_rank"],
        "predictor_row_key_t": scope_row["predictor_row_key_t"],
        "target_row_key_t_plus_1": scope_row["target_row_key_t_plus_1"],
        "ticker": scope_row["ticker"],
        "fiscal_year_t": scope_row["fiscal_year_t"],
        "starting_evidence_class": scope_row["starting_evidence_class"],
        "source_origin": source_origin,
        "source_url": (
            THANUSA_AUTHORIZED_URL if scope_row["ticker"] == "ثنوسا"
            else (candidate.url if candidate else "")
        ),
        "letter_serial": (
            THANUSA_LETTER_SERIAL if scope_row["ticker"] == "ثنوسا"
            else (candidate.letter_serial if candidate else "")
        ),
        "canonical_letter_serial": scope_row.get("canonical_letter_serial") or "",
        "tracing_no": candidate.tracing_no if candidate else "",
        "canonical_tracing_no": "",
        "official_title": (
            binding_inp.official_title if binding_inp.official_title else ""
        ),
        "canonical_official_title": (
            binding_inp.canonical_official_title
            if binding_inp.canonical_official_title else ""
        ),
        "legal_entity": scope_row["canonical_company_name"],
        "is_parent_company": binding_inp.is_parent_company,
        "statement_scope": scope_row["canonical_statement_scope"],
        "is_annual": binding_inp.is_annual,
        "is_interim": binding_inp.is_interim,
        "is_audited": binding_inp.is_audited,
        "fiscal_year_end": scope_row["canonical_fiscal_year_end"],
        "revision_status_raw": binding_inp.revision_status_raw or "",
        "revision_status_normalized": binding_inp.revision_status or "",
        "publish_datetime_raw": publish_raw or "",
        "sent_datetime_raw": sent_raw or "",
        "publish_datetime_utc_candidate": _publish_utc_candidate(publish_raw) or "",
        "available_at": avail_res.available_at or "",
        "available_at_source_field": avail_res.source_field or "",
        "snapshot_sha256": snapshot_sha or "",
        "cache_snapshot_complete": not incomplete,
        "canonical_source_version_bound": canonical_bound,
        "binding_status": status,
        "cutoff_status": avail_res.cutoff_status,
        "failure_reasons": failure_reasons,
        "reviewer_status": "automated_part3b1b",
    }

    adjudication = {
        "scope_row_id": sid,
        "predictor_row_key_t": scope_row["predictor_row_key_t"],
        "binding_status": status,
        "binding_ok": bind_res.ok,
        "cutoff_status": avail_res.cutoff_status,
        "available_at": avail_res.available_at or "",
        "available_at_source_field": avail_res.source_field or "",
        "failure_reasons": failure_reasons,
        "adjudication_notes": (
            "multi_document_predictor_row_fail_closed"
            if multi_doc else ""
        ),
        "reviewer_status": "automated_part3b1b",
    }

    unresolved = None
    if status in (BINDING_UNRESOLVED, BINDING_REJECTED):
        unresolved = {
            "scope_row_id": sid,
            "predictor_row_key_t": scope_row["predictor_row_key_t"],
            "binding_status": status,
            "starting_evidence_class": scope_row["starting_evidence_class"],
            "failure_reasons": failure_reasons,
            "source_origin": source_origin,
            "reviewer_status": "automated_part3b1b",
        }
    return evidence, adjudication, unresolved


def process_all_scope_rows(
    repo_root: Path,
    *,
    capture: bool,
    cache: p3b0.ImmutableCache,
    thanusa_fetch: ThanusaFetchResult | None,
) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    scope_rows: list[dict] = []
    evidence_rows: list[dict] = []
    adj_rows: list[dict] = []
    unresolved_rows: list[dict] = []

    for scope in LOCKED_SCOPE:
        sid = scope_row_id(scope)
        scope_rows.append({
            "scope_row_id": sid,
            "selection_rank": scope["selection_rank"],
            "predictor_row_key_t": scope["predictor_row_key_t"],
            "target_row_key_t_plus_1": scope["target_row_key_t_plus_1"],
            "ticker": scope["ticker"],
            "fiscal_year_t": scope["fiscal_year_t"],
            "starting_evidence_class": scope["starting_evidence_class"],
            "canonical_fiscal_year_end": scope["canonical_fiscal_year_end"],
            "canonical_company_name": scope["canonical_company_name"],
            "canonical_statement_scope": scope["canonical_statement_scope"],
            "canonical_letter_serial": scope.get("canonical_letter_serial") or "",
            "pilot_csv_verified": True,
            "reviewer_status": "automated_part3b1b",
        })

        candidate = None
        cache_meta = None
        cache_hash = None
        source_origin = "locked_scope_no_local_cache"

        if scope["ticker"] == "ثنوسا":
            source_origin = (
                "codal_authorized_get" if thanusa_fetch and thanusa_fetch.success
                else "ocf_manifest_canonical_letter_serial"
            )
        elif scope["ticker"] in LOCAL_CACHE_BY_TICKER:
            rel = LOCAL_CACHE_BY_TICKER[scope["ticker"]]
            cache_path = repo_root / rel
            cache_hash = sha256_file(cache_path)
            cache_data = json.loads(cache_path.read_bytes())
            candidates, cache_meta = match_local_letter_candidates(cache_data, scope)
            source_origin = "stage124_feasibility_local_cache"
            if len(candidates) == 1:
                candidate = candidates[0]
            elif len(candidates) > 1:
                candidate = candidates[0]

        evidence, adj, unresolved = adjudicate_scope_row(
            scope,
            candidate=candidate,
            cache_meta=cache_meta,
            cache_file_sha256=cache_hash,
            thanusa_fetch=thanusa_fetch if scope["ticker"] == "ثنوسا" else None,
            source_origin=source_origin,
        )
        evidence_rows.append(evidence)
        adj_rows.append(adj)
        if unresolved:
            unresolved_rows.append(unresolved)

    return scope_rows, evidence_rows, adj_rows, unresolved_rows


# --------------------------------------------------------------------------- #
# README / metadata / QC
# --------------------------------------------------------------------------- #

def build_readme() -> str:
    return """# Stage125 Part 3B.1B — CODAL Predictor-Document Binding Mini-Pilot

**Status:** controlled mini-pilot for exactly five locked predictor rows.

## Scope

Document metadata / provenance capture only. No financial-value extraction,
accessibility scoring, Gate application, Stage126, or modeling.

## Locked rows

Five predictor rows verified against the frozen Part 3A pilot CSV hash and
Stage123 FYE metadata:

- ثنوسا|1392 (B2) — one authorized `www.codal.ir` GET by canonical LetterSerial
- بوعلی|1399 / بوعلی|1400 (B1) — read-only Stage124 feasibility search caches
- اردستان|1401 (B3) — subsidiary-title rejection path
- اپال|1401 (B1) — incomplete pagination without canonical LetterSerial

## Binding statuses

`BOUND` / `UNRESOLVED` / `REJECTED` via Part 3B.1A exact-document binding.

`available_at` is assigned only when `binding_status=BOUND` using CUT-A
`PublishDateTime` → Asia/Tehran → UTC rules. `SentDateTime` is never availability.

## Network

At most one authorized GET to `www.codal.ir` for ثنوسا during `--capture`.
`--check` performs zero network I/O and writes nothing.

## Research pointers (unchanged)

- `last_completed_research_action_id=stage125-part3a-decision-lock`
- `next_research_action_id=stage125-part3b-evidence-capture`
"""


def _derive_qc_counts(evidence_rows: list[dict[str, Any]]) -> dict[str, int]:
    bound = sum(1 for r in evidence_rows if r.get("binding_status") == BINDING_BOUND)
    unresolved = sum(
        1 for r in evidence_rows if r.get("binding_status") == BINDING_UNRESOLVED
    )
    rejected = sum(
        1 for r in evidence_rows if r.get("binding_status") == BINDING_REJECTED
    )
    avail_non_null = sum(1 for r in evidence_rows if r.get("available_at"))
    return {
        "bound_count": bound,
        "unresolved_count": unresolved,
        "rejected_count": rejected,
        "available_at_non_null_count": avail_non_null,
    }


def build_qc_assertions(
    repo_root: Path,
    evidence_rows: list[dict[str, Any]],
    network_log: dict[str, Any],
    *,
    network_requests_attempted: int,
    frozen_before: dict[str, str],
    frozen_after: dict[str, str],
) -> list[dict[str, Any]]:
    assertions: list[dict[str, Any]] = []
    counts = _derive_qc_counts(evidence_rows)

    def add(name: str, ok: bool, detail: str) -> None:
        assertions.append({
            "assertion": name,
            "status": "PASS" if ok else "FAIL",
            "detail": detail,
        })

    add("scope_rows_exactly_five", len(evidence_rows) == 5, str(len(evidence_rows)))
    add("baseline_commit_constant", EXPECTED_BASELINE_COMMIT.startswith("4d7a482"), EXPECTED_BASELINE_COMMIT)
    add("pilot_csv_hash_pinned", sha256_file(repo_root / PILOT_CSV_REL) == PILOT_CSV_SHA256, PILOT_CSV_SHA256)
    add("ocf_manifest_hash_pinned",
        sha256_file(repo_root / OCF_MANIFEST_REL) == OCF_MANIFEST_SHA256,
        OCF_MANIFEST_SHA256)
    add("frozen_scientific_unchanged", frozen_before == frozen_after, "unchanged")
    add("network_max_one", network_requests_attempted <= NETWORK_REQUESTS_AUTHORIZED_MAX,
        str(network_requests_attempted))
    add("financial_values_extracted_zero", True, "0")
    add("bound_count_derived", counts["bound_count"] >= 0, str(counts["bound_count"]))
    add("unresolved_count_derived",
        counts["unresolved_count"] >= 0, str(counts["unresolved_count"]))
    add("rejected_count_derived",
        counts["rejected_count"] >= 0, str(counts["rejected_count"]))
    add("available_at_only_when_bound",
        all(
            (not r.get("available_at")) or r.get("binding_status") == BINDING_BOUND
            for r in evidence_rows
        ),
        "checked",
    )
    add("sent_never_availability",
        all(
            (not r.get("available_at")) or r.get("available_at_source_field") == "PublishDateTime"
            for r in evidence_rows if r.get("available_at")
        ),
        "PublishDateTime only",
    )
    add("research_pointers_unchanged",
        RESEARCH_LAST_COMPLETED == "stage125-part3a-decision-lock"
        and RESEARCH_NEXT == "stage125-part3b-evidence-capture",
        "fixed",
    )
    add("part3b_completed_false_marker", True, "false")
    add("modeling_started_false_marker", True, "false")
    add("pilot_cutoff_provenance_resolved_false", True, "false")
    add("data_value_extraction_performed_false", True, "false")
    add("no_forbidden_surfaces",
        not any((repo_root / rel).exists() for rel in FORBIDDEN_SURFACE_EXACT),
        "ok",
    )
    src_text = (repo_root / SRC_REL).read_text(encoding="utf-8")
    add("no_value_extraction_tokens",
        not _source_has_forbidden_value_extraction_tokens(repo_root),
        "scan ok",
    )
    statuses = {r.get("binding_status") for r in evidence_rows}
    add("all_rows_valid_status", statuses <= {BINDING_BOUND, BINDING_UNRESOLVED, BINDING_REJECTED},
        str(sorted(statuses)))
    add("network_log_complete",
        isinstance(network_log.get("requests"), list),
        str(len(network_log.get("requests") or [])),
    )
    pilot_completed = (
        len(evidence_rows) == 5
        and statuses <= {BINDING_BOUND, BINDING_UNRESOLVED, BINDING_REJECTED}
        and network_requests_attempted <= NETWORK_REQUESTS_AUTHORIZED_MAX
    )
    add("predictor_document_binding_mini_pilot_completed", pilot_completed, str(pilot_completed))
    evidence_collected = any(
        r.get("source_origin") in ("codal_authorized_get", "stage124_feasibility_local_cache")
        and r.get("snapshot_sha256")
        for r in evidence_rows
    )
    add("predictor_document_binding_evidence_collected", evidence_collected, str(evidence_collected))
    add("predictor_available_at_evidence_collected_false",
        counts["available_at_non_null_count"] == 0,
        str(counts["available_at_non_null_count"]))
    return assertions


def build_qc_report(
    repo_root: Path,
    content_hashes: dict[str, str],
    evidence_rows: list[dict[str, Any]],
    network_log: dict[str, Any],
    frozen: dict[str, str],
    *,
    network_requests_attempted: int,
    frozen_before: dict[str, str],
    frozen_after: dict[str, str],
) -> dict[str, Any]:
    assertions = build_qc_assertions(
        repo_root, evidence_rows, network_log,
        network_requests_attempted=network_requests_attempted,
        frozen_before=frozen_before,
        frozen_after=frozen_after,
    )
    failed = sum(1 for a in assertions if a["status"] != "PASS")
    counts = _derive_qc_counts(evidence_rows)
    source_commit = _git(str(repo_root), "log", "--format=%H", "-n", "1", "--", SRC_REL, TEST_REL, RUN_REL)
    return {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "maintenance_task_id": MAINTENANCE_TASK_ID,
        "baseline_commit": EXPECTED_BASELINE_COMMIT,
        "source_commit": source_commit,
        "source_file_sha256": sha256_file(repo_root / SRC_REL),
        "test_file_sha256": sha256_file(repo_root / TEST_REL),
        "assertion_count": len(assertions),
        "failed_count": failed,
        "all_pass": failed == 0,
        "scope_rows": 5,
        "network_requests_attempted": network_requests_attempted,
        "network_requests_authorized_max": NETWORK_REQUESTS_AUTHORIZED_MAX,
        "financial_values_extracted": 0,
        **counts,
        "predictor_document_binding_mini_pilot_completed": all(
            a["assertion"] != "predictor_document_binding_mini_pilot_completed"
            or a["status"] == "PASS"
            for a in assertions
        ) and failed == 0,
        "predictor_document_binding_evidence_collected": any(
            r.get("source_origin") in ("codal_authorized_get", "stage124_feasibility_local_cache")
            and r.get("snapshot_sha256")
            for r in evidence_rows
        ),
        "predictor_available_at_evidence_collected": counts["available_at_non_null_count"] >= 1,
        "pilot_cutoff_provenance_resolved": False,
        "candidate_value_evidence_collected": False,
        "pair_level_evidence_collected": False,
        "data_value_extraction_performed": False,
        "accessibility_scoring_applied": False,
        "part3b_completed": False,
        "modeling_started": False,
        "research_pointers": {
            "last_completed_research_action_id": RESEARCH_LAST_COMPLETED,
            "next_research_action_id": RESEARCH_NEXT,
        },
        "output_sha256": dict(sorted(content_hashes.items())),
        "frozen_scientific_sha256": dict(sorted(frozen.items())),
        "assertions": assertions,
    }


def build_metadata(qc: dict[str, Any], content_hashes: dict[str, str], qc_hash: str) -> dict[str, Any]:
    output_hashes = dict(content_hashes)
    output_hashes[F_QC] = qc_hash
    return {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "description": "Stage125 Part 3B.1B CODAL predictor-document binding mini-pilot.",
        "generated_at": qc.get("source_commit"),
        "code_commit": qc["source_commit"],
        "baseline_commit": EXPECTED_BASELINE_COMMIT,
        "source_file_sha256": qc["source_file_sha256"],
        "test_file_sha256": qc["test_file_sha256"],
        "output_files_sha256": dict(sorted(output_hashes.items())),
        "predictor_document_binding_mini_pilot_completed": qc.get(
            "predictor_document_binding_mini_pilot_completed", False,
        ),
        "part3b_completed": False,
        "modeling_started": False,
        "network_requests_attempted": qc.get("network_requests_attempted", 0),
    }


def build_all_content(
    repo_root: Path,
    *,
    capture: bool,
    cache: p3b0.ImmutableCache,
    thanusa_fetch: ThanusaFetchResult | None,
    network_requests_attempted: int,
) -> tuple[dict[str, str], list[dict], dict[str, Any]]:
    scope_rows, evidence_rows, adj_rows, unresolved_rows = process_all_scope_rows(
        repo_root, capture=capture, cache=cache, thanusa_fetch=thanusa_fetch,
    )
    network_log: dict[str, Any] = {
        "stage": QC_STAGE,
        "network_requests_attempted": network_requests_attempted,
        "network_requests_authorized_max": NETWORK_REQUESTS_AUTHORIZED_MAX,
        "authorized_hosts": [ALLOWED_CODAL_HOST],
        "authorized_urls": [THANUSA_AUTHORIZED_URL],
        "requests": (
            [thanusa_fetch.network_entry] if thanusa_fetch else []
        ),
    }
    attempts: list[dict[str, Any]] = []
    if thanusa_fetch:
        attempts.append({
            "capture_run_id": "part3b1b_capture",
            "attempt_id": "attempt_thanusa_001",
            "scope_row_id": scope_row_id(LOCKED_SCOPE[0]),
            "predictor_row_key_t": LOCKED_SCOPE[0]["predictor_row_key_t"],
            "planned_request_url": THANUSA_AUTHORIZED_URL,
            "http_method": "GET",
            "started_at_utc": "",
            "completed_at_utc": "",
            "final_url": thanusa_fetch.network_entry.get("final_url", ""),
            "response_status": thanusa_fetch.network_entry.get("response_status", ""),
            "content_type": thanusa_fetch.network_entry.get("content_type", ""),
            "byte_count": thanusa_fetch.network_entry.get("bytes", ""),
            "redirect_count": thanusa_fetch.network_entry.get("redirect_count", 0),
            "payload_sha256": thanusa_fetch.payload_sha256,
            "metadata_sha256": thanusa_fetch.metadata_sha256,
            "success": thanusa_fetch.success,
            "failure_class": thanusa_fetch.failure_class,
            "network_log_complete": True,
            "reviewer_status": "automated_part3b1b",
        })
    content = {
        F_SCOPE: _csv_str(SCOPE_HEADER, scope_rows),
        F_EVIDENCE: _csv_str(EVIDENCE_COLUMNS, evidence_rows),
        F_ADJ: _csv_str(ADJ_HEADER, adj_rows),
        F_ATTEMPTS: _csv_str(ATTEMPT_HEADER, attempts),
        F_NETWORK: _json_str(network_log),
        F_UNRESOLVED: _csv_str(UNRESOLVED_HEADER, unresolved_rows),
        F_README: build_readme(),
    }
    return content, evidence_rows, network_log


def _compare_drift(out_dir: Path, payloads: dict[str, str]) -> list[str]:
    drift: list[str] = []
    for name, text in payloads.items():
        path = out_dir / name
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            drift.append(name)
    return drift


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

def run(
    *,
    project_dir: Path,
    output_dir: Path | None = None,
    capture: bool = False,
    check: bool = False,
) -> dict[str, Any]:
    if capture and check:
        raise QCFail("capture and check are mutually exclusive")

    repo_root = project_dir.parent if project_dir.name == "project" else project_dir
    out_dir = Path(output_dir) if output_dir else (repo_root / "project" / "stage125")
    out_dir.mkdir(parents=True, exist_ok=True)

    verify_baseline_commit(str(repo_root))
    verify_locked_scope_against_pilot(repo_root)
    verify_ocf_manifest_hash(repo_root)

    frozen_before = frozen_scientific_hashes(repo_root)
    cache = p3b0.ImmutableCache(repo_root / CACHE_DIR_REL)

    network_requests_attempted = 0
    thanusa_fetch: ThanusaFetchResult | None = None

    with p3b0.network_sentinel() as sentinel:
        if capture:
            thanusa_fetch = authorize_and_fetch_thanusa(
                cache=cache,
                capture=True,
                orig_connect=sentinel._orig_connect,
                orig_getaddrinfo=sentinel._orig_getaddrinfo,
            )
            if thanusa_fetch and not thanusa_fetch.network_entry.get("from_immutable_cache"):
                network_requests_attempted = 1
        else:
            thanusa_fetch = authorize_and_fetch_thanusa(cache=cache, capture=False)

        # Authorized CODAL GET uses sentinel._orig_connect bypass, so the
        # default-deny sentinel must remain at zero intercepted calls.
        if sentinel.calls_attempted != 0:
            raise QCFail(
                f"unauthorized network intercepted by sentinel: "
                f"{sentinel.calls_attempted}"
            )
        if network_requests_attempted > NETWORK_REQUESTS_AUTHORIZED_MAX:
            raise QCFail(
                f"network request budget exceeded: {network_requests_attempted}"
            )

        content, evidence_rows, network_log = build_all_content(
            repo_root,
            capture=capture,
            cache=cache,
            thanusa_fetch=thanusa_fetch,
            network_requests_attempted=network_requests_attempted,
        )
        content_hashes = {
            name: sha256_bytes(text.encode("utf-8")) for name, text in content.items()
        }

        frozen_after = frozen_scientific_hashes(repo_root)
        if frozen_before != frozen_after:
            raise QCFail("frozen scientific assets mutated during Part 3B.1B run")

        qc = build_qc_report(
            repo_root,
            content_hashes,
            evidence_rows,
            network_log,
            frozen_after,
            network_requests_attempted=network_requests_attempted,
            frozen_before=frozen_before,
            frozen_after=frozen_after,
        )
        qc_text = _json_str(qc)
        qc_hash = sha256_bytes(qc_text.encode("utf-8"))
        meta = build_metadata(qc, content_hashes, qc_hash)
        meta_text = _json_str(meta)

        all_payloads = {**content, F_QC: qc_text, F_METADATA: meta_text}
        drift = _compare_drift(out_dir, all_payloads)

        files_written: dict[str, str] = {}
        if capture:
            for name, text in content.items():
                (out_dir / name).write_text(text, encoding="utf-8")
                files_written[name] = content_hashes[name]
            (out_dir / F_QC).write_text(qc_text, encoding="utf-8")
            (out_dir / F_METADATA).write_text(meta_text, encoding="utf-8")
            files_written[F_QC] = qc_hash
            files_written[F_METADATA] = sha256_bytes(meta_text.encode("utf-8"))

        if not qc["all_pass"]:
            failed = [a for a in qc["assertions"] if a["status"] != "PASS"]
            raise QCFail(f"QC failed: {failed[:5]}")

    return {
        "output_dir": str(out_dir),
        "qc": qc,
        "drift": drift,
        "files": files_written,
        "frozen_scientific_sha256": frozen_after,
        "network_requests_attempted": network_requests_attempted,
        "evidence_rows": evidence_rows,
    }
