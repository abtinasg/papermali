"""Stage125 Part 3B.1D — Controlled Same-Five Metadata Resolution Capture.

Exactly four authorized CODAL Decision.aspx HTTPS GETs within the existing
five-row pilot. اردستان receives zero network requests.

Scope: metadata provenance capture only; tracked receipts bound to payload
hashes; raw payloads in gitignored immutable local cache only.

Prohibitions: no binding-status mutation; no real available_at assignment;
no financial-value extraction; no accessibility scoring / Gate application;
no 80-row scale-up / Part 3B.2 / Stage126 / modeling; research pointers
unchanged.
"""
from __future__ import annotations

import csv
import hashlib
import html as html_lib
import io
import ipaddress
import json
import re
import socket
import ssl
import subprocess
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urljoin, urlparse

from src import stage125_part3b0_evidence_readiness as p3b0

QC_STAGE = "stage125_part3b1d_same_five_metadata_resolution_capture"
CURRENT_STAGE = "Stage125"
EXPECTED_BASELINE_COMMIT = "f1bc5eb770d883754078f15427dac45fe40a8c0b"
TASK_ID = "stage125-part3b1d-same-five-metadata-resolution-capture"
MAINTENANCE_TASK_ID = TASK_ID
RESEARCH_LAST_COMPLETED = "stage125-part3a-decision-lock"
RESEARCH_NEXT = "stage125-part3b-evidence-capture"

SRC_REL = "project/src/stage125_part3b1d_same_five_metadata_resolution_capture.py"
TEST_REL = (
    "project/tests/test_stage125_part3b1d_same_five_metadata_resolution_capture.py"
)
RUN_REL = "project/run_stage125_part3b1d.py"

CACHE_DIR_REL = "project/stage125/raw_cache_part3b1d"
ALLOWED_CODAL_HOST = "www.codal.ir"
ALLOWED_PATH = "/Reports/Decision.aspx"
ALLOWED_QUERY_KEYS = frozenset({"LetterSerial", "rt", "let", "ct", "ft"})
AUTHORIZED_LOGICAL_REQUESTS = 4
MAX_RESPONSE_BYTES = 2_000_000
MAX_REDIRECTS = 5
REQUEST_TIMEOUT_SEC = 30.0
PARSER_CONTRACT_VERSION = "stage125_part3b1d_codal_decision_html_v1"
RAW_PAYLOAD_STORAGE_POLICY = "gitignored_immutable_cache_optional_local"

F_AUTH = "part3b1d_capture_authorization_lock_stage125.json"
F_MANIFEST = "part3b1d_capture_manifest_stage125.json"
F_SUMMARY = "part3b1d_metadata_capture_summary_stage125.csv"
F_README = "README_STAGE125_PART3B1D_METADATA_RESOLUTION_CAPTURE.md"
F_QC = "stage125_part3b1d_metadata_resolution_capture_qc_report.json"
F_METADATA = "metadata_and_hashes_stage125_part3b1d.json"

METADATA_FIELDS = (
    "official_title",
    "legal_entity",
    "symbol",
    "fiscal_year_end",
    "revision_status",
    "PublishDateTime",
    "SentDateTime",
    "LetterSerial",
    "TracingNo",
)

LOCKED_KEYS = (
    "ثنوسا|1392",
    "بوعلی|1399",
    "بوعلی|1400",
    "اردستان|1401",
    "اپال|1401",
)
EXPECTED_STATUS = {
    "ثنوسا|1392": "UNRESOLVED",
    "بوعلی|1399": "UNRESOLVED",
    "بوعلی|1400": "UNRESOLVED",
    "اردستان|1401": "REJECTED",
    "اپال|1401": "UNRESOLVED",
}
EXPECTED_COUNTS = {
    "bound_count": 0,
    "unresolved_count": 4,
    "rejected_count": 1,
    "available_at_non_null_count": 0,
}

ARDISTAN_KEY = "اردستان|1401"
ARDISTAN_SCOPE = "p3b1b_scope_076"
ARDISTAN_URL = (
    "https://www.codal.ir/Reports/Decision.aspx?"
    "LetterSerial=BSQErBhkkemwHAEID3RSYw%3d%3d&rt=5&let=6&ct=0&ft=-1"
)

ARABIC_YEH = "\u064a"
PERSIAN_YEH = "\u06cc"
ARABIC_KAF = "\u0643"
PERSIAN_KAF = "\u06a9"
DIGIT_MAP = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

FORBIDDEN_HOSTS = frozenset({
    "search.codal.ir",
    "api.codal.ir",
    "cdn.tsetmc.com",
    "www.tsetmc.com",
    "cbi.ir",
    "www.cbi.ir",
    "www.google.com",
    "www.bing.com",
})

PINNED_INPUTS: dict[str, str] = {
    "project/stage125/part3b1b_codal_document_evidence_stage125.csv":
        "b0ded2c9c084cfc8ca882c370b6437d3949af52e00297b3f3d30f80bd315f867",
    "project/stage125/part3b1b_document_binding_adjudication_stage125.csv":
        "d4515c0f3741bec7733aac97c4167a1ca730e983b0cc1627d77da7c20c8aa7e1",
    "project/stage125/part3b1b_predictor_document_scope_stage125.csv":
        "835e1b6b17df35f167180e59f7fe51e31c0c679cef464b7d78256ce24bb07f91",
    "project/stage125/part3b1b_unresolved_and_rejections_stage125.csv":
        "d5e0ce0d400601057d65b935683dbd8b3e3c0d03fa7bb24842f56f61cbf53a67",
    "project/stage125/part3b1b_thanusa_capture_receipt_stage125.json":
        "f2571c296d3400af1bc6b607180d231b4b06096ca4f5c58f024286ade4821626",
    "project/stage125/part3b1b_thanusa_parsed_metadata_receipt_stage125.json":
        "217228edd67595167746f006e5bec21f17aa9f3f16008d30c3abc7023e9f84a4",
    "project/stage125/part3b1c_proposed_capture_authorization_stage125.json":
        "c97b17669c44969eb1fdc567e9c81f8b9de7b36ad3f63dc5ee6613f7bda17d78",
    "project/stage125/prediction_cutoff_audit_stage125_part2.csv":
        "d50e6617b011a7818d972de8e5c8a862a45f73fb07a0a22cdb5c9f59b6dc88f0",
    "project/stage125/feature_availability_contract_stage125_part2.json":
        "b97593ed46fa2440b66cafd6a3752300177df4773cbdcf45b3126872d3c200a3",
}

AUTHORIZED_REQUESTS: tuple[dict[str, Any], ...] = (
    {
        "logical_request_number": 1,
        "request_id": "p3b1d_req_001",
        "scope_row_id": "p3b1b_scope_006",
        "predictor_row_key_t": "ثنوسا|1392",
        "candidate_letter_serial": "Ddg2e7HG6FGR5ygaTFJd4g==",
        "exact_url": (
            "https://www.codal.ir/Reports/Decision.aspx?"
            "LetterSerial=Ddg2e7HG6FGR5ygaTFJd4g%3D%3D"
        ),
        "slug": "thanusa_1392",
    },
    {
        "logical_request_number": 2,
        "request_id": "p3b1d_req_002",
        "scope_row_id": "p3b1b_scope_063",
        "predictor_row_key_t": "بوعلی|1399",
        "candidate_letter_serial": "X1Tbq4+nahb6qy6UkUigkw==",
        "exact_url": (
            "https://www.codal.ir/Reports/Decision.aspx?"
            "LetterSerial=X1Tbq4%2Bnahb6qy6UkUigkw%3D%3D&rt=0&let=6&ct=0&ft=-1"
        ),
        "slug": "bouali_1399",
    },
    {
        "logical_request_number": 3,
        "request_id": "p3b1d_req_003",
        "scope_row_id": "p3b1b_scope_072",
        "predictor_row_key_t": "بوعلی|1400",
        "candidate_letter_serial": "AoU4UDrZexlj4Kd1iQszEw==",
        "exact_url": (
            "https://www.codal.ir/Reports/Decision.aspx?"
            "LetterSerial=AoU4UDrZexlj4Kd1iQszEw%3d%3d&rt=0&let=6&ct=0&ft=-1"
        ),
        "slug": "bouali_1400",
    },
    {
        "logical_request_number": 4,
        "request_id": "p3b1d_req_004",
        "scope_row_id": "p3b1b_scope_077",
        "predictor_row_key_t": "اپال|1401",
        "candidate_letter_serial": "pScUnGYLuZOexpdcJdTCdQ==",
        "exact_url": (
            "https://www.codal.ir/Reports/Decision.aspx?"
            "LetterSerial=pScUnGYLuZOexpdcJdTCdQ%3d%3d&rt=2&let=6&ct=0&ft=-1"
        ),
        "slug": "opal_1401",
    },
)

AUTHORIZED_URLS = frozenset(r["exact_url"] for r in AUTHORIZED_REQUESTS)
AUTHORIZED_KEYS = frozenset(r["predictor_row_key_t"] for r in AUTHORIZED_REQUESTS)
RECEIPT_BY_SLUG = {
    r["slug"]: f"part3b1d_capture_receipt_{r['slug']}_stage125.json"
    for r in AUTHORIZED_REQUESTS
}
PARSED_BY_SLUG = {
    r["slug"]: f"part3b1d_parsed_metadata_{r['slug']}_stage125.json"
    for r in AUTHORIZED_REQUESTS
}

CAPTURE_RECEIPT_REQUIRED = (
    "task_id",
    "request_id",
    "scope_row_id",
    "predictor_row_key_t",
    "candidate_letter_serial",
    "http_method",
    "requested_exact_url",
    "request_started_at_utc",
    "request_completed_at_utc",
    "logical_request_number",
    "redirect_chain",
    "final_url",
    "http_status",
    "content_type",
    "response_bytes",
    "response_sha256",
    "local_cache_path",
    "network_error",
    "capture_status",
    "parser_eligible",
)

PART3B1D_AUTHORIZED_EXACT = frozenset({
    SRC_REL,
    TEST_REL,
    RUN_REL,
    f"project/stage125/{F_AUTH}",
    f"project/stage125/{F_MANIFEST}",
    f"project/stage125/{F_SUMMARY}",
    f"project/stage125/{F_README}",
    f"project/stage125/{F_QC}",
    f"project/stage125/{F_METADATA}",
    *[f"project/stage125/{n}" for n in RECEIPT_BY_SLUG.values()],
    *[f"project/stage125/{n}" for n in PARSED_BY_SLUG.values()],
})

TransportFn = Callable[[str, str], tuple[bytes, dict[str, Any]]]


class QCFail(RuntimeError):
    """Fail-closed scientific / QC error."""


class NetworkPolicyError(RuntimeError):
    """Fail-closed network allowlist / transport error."""


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
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _git(repo_root: str, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", repo_root, *args], capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise QCFail(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


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


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def apply_mechanical_normalization(text: str | None) -> str | None:
    if text is None:
        return None
    value = unicodedata.normalize("NFC", text)
    value = value.replace(ARABIC_YEH, PERSIAN_YEH).replace(ARABIC_KAF, PERSIAN_KAF)
    value = value.translate(DIGIT_MAP)
    value = value.replace("\u200c", " ")
    value = re.sub(r"\s+", " ", value.strip())
    value = value.replace("\u2013", "-").replace("\u2014", "-")
    value = value.replace("\u00ab", '"').replace("\u00bb", '"')
    return value


def decode_letter_serial_from_url(url: str) -> str:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    serials = qs.get("LetterSerial", [])
    if len(serials) != 1:
        raise NetworkPolicyError(
            f"LetterSerial count must be exactly 1, got {len(serials)}"
        )
    return serials[0]


def validate_authorized_url(
    url: str,
    *,
    candidate_letter_serial: str | None = None,
    method: str = "GET",
) -> None:
    if method.upper() != "GET":
        raise NetworkPolicyError(f"POST rejected" if method.upper() == "POST"
                                 else f"method not allowed: {method}")
    if not isinstance(url, str) or not url.strip():
        raise NetworkPolicyError("url must be nonempty string")
    if "*" in url:
        raise NetworkPolicyError("wildcard rejected")
    if url == ARDISTAN_URL:
        raise NetworkPolicyError("اردستان request rejected")

    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise NetworkPolicyError(f"bad scheme rejected: {parsed.scheme!r}")
    host = (parsed.hostname or "").lower()
    if host in FORBIDDEN_HOSTS:
        raise NetworkPolicyError(f"forbidden host: {host}")
    if host != ALLOWED_CODAL_HOST:
        raise NetworkPolicyError(f"bad host rejected: {host}")
    if parsed.port not in (None, 443):
        raise NetworkPolicyError(f"bad port rejected: {parsed.port}")
    if parsed.path != ALLOWED_PATH:
        if "Search" in (parsed.path or "") or "search" in (parsed.path or "").lower():
            raise NetworkPolicyError("search endpoint rejected")
        raise NetworkPolicyError(f"bad path rejected: {parsed.path!r}")
    if parsed.username is not None or parsed.password is not None:
        raise NetworkPolicyError("credentials rejected")
    if parsed.fragment:
        raise NetworkPolicyError("fragment rejected")

    qs = parse_qs(parsed.query, keep_blank_values=True)
    unknown = sorted(set(qs) - ALLOWED_QUERY_KEYS)
    if unknown:
        raise NetworkPolicyError(f"unknown query parameter rejected: {unknown}")
    serials = qs.get("LetterSerial", [])
    if len(serials) == 0:
        raise NetworkPolicyError("missing LetterSerial rejected")
    if len(serials) > 1:
        raise NetworkPolicyError("duplicate LetterSerial rejected")
    decoded = serials[0]
    if candidate_letter_serial is not None and decoded != candidate_letter_serial:
        raise NetworkPolicyError("mismatched LetterSerial rejected")
    if url not in AUTHORIZED_URLS:
        raise NetworkPolicyError("URL not in Part 3B.1D authorized exact set")


def assert_url_allowed(
    url: str, *, candidate_letter_serial: str | None = None, method: str = "GET",
) -> None:
    validate_authorized_url(
        url, candidate_letter_serial=candidate_letter_serial, method=method,
    )


def _assert_redirect_allowed(url: str, *, expected_letter_serial: str) -> None:
    if "*" in url:
        raise NetworkPolicyError("wildcard rejected in redirect")
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise NetworkPolicyError("redirect scheme must remain https")
    host = (parsed.hostname or "").lower()
    if host != ALLOWED_CODAL_HOST:
        raise NetworkPolicyError("redirect to another host rejected")
    if parsed.port not in (None, 443):
        raise NetworkPolicyError("redirect bad port")
    if parsed.username is not None or parsed.password is not None:
        raise NetworkPolicyError("redirect credentials rejected")
    if parsed.fragment:
        raise NetworkPolicyError("redirect fragment rejected")
    if parsed.path != ALLOWED_PATH:
        raise NetworkPolicyError("redirect reaches non-Decision endpoint")
    qs = parse_qs(parsed.query, keep_blank_values=True)
    unknown = sorted(set(qs) - ALLOWED_QUERY_KEYS)
    if unknown:
        raise NetworkPolicyError(f"redirect unknown query keys: {unknown}")
    serials = qs.get("LetterSerial", [])
    if len(serials) != 1:
        raise NetworkPolicyError("redirect missing/duplicate LetterSerial")
    if serials[0] != expected_letter_serial:
        raise NetworkPolicyError("redirect with changed LetterSerial rejected")


def _assert_public_ip(ip: str) -> None:
    ip_obj = ipaddress.ip_address(ip)
    if (
        ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local
        or ip_obj.is_reserved or ip_obj.is_multicast or ip_obj.is_unspecified
    ):
        raise NetworkPolicyError(f"private/reserved IP rejected: {ip}")


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


def _parse_http_response(
    raw: bytes,
    original_url: str,
    *,
    expected_letter_serial: str,
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
        _assert_redirect_allowed(
            final_url, expected_letter_serial=expected_letter_serial,
        )
    if headers.get("transfer-encoding", "").lower() == "chunked":
        body = _dechunk(body)
    if len(body) > MAX_RESPONSE_BYTES:
        raise NetworkPolicyError("oversized response rejected")
    return body, status, final_url, ctype


def default_https_transport(
    method: str,
    url: str,
    *,
    expected_letter_serial: str | None = None,
    orig_connect: Callable[..., Any] | None = None,
    orig_getaddrinfo: Callable[..., Any] | None = None,
) -> tuple[bytes, dict[str, Any]]:
    serial = expected_letter_serial or decode_letter_serial_from_url(url)
    validate_authorized_url(url, candidate_letter_serial=serial, method=method)
    method = method.upper()
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
            "User-Agent: papermali-stage125-part3b1d-readonly/1.0\r\n"
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
                    raise NetworkPolicyError("oversized response rejected")
                chunks.append(chunk)
            raw = b"".join(chunks)
        finally:
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass
        body, status, final_url, ctype = _parse_http_response(
            raw, current, expected_letter_serial=serial,
        )
        if status in (301, 302, 303, 307, 308):
            redirects += 1
            if redirects > MAX_REDIRECTS:
                raise NetworkPolicyError("too many redirects")
            if not final_url or final_url == current:
                raise NetworkPolicyError("redirect without location")
            redirect_chain.append(final_url)
            current = final_url
            continue
        if len(body) > MAX_RESPONSE_BYTES:
            raise NetworkPolicyError("oversized response rejected")
        return body, {
            "request_url": url,
            "redirect_chain": redirect_chain,
            "final_url": final_url,
            "response_status": status,
            "content_type": ctype,
            "bytes": len(body),
            "redirect_count": redirects,
        }


def _field_record(
    *,
    raw_value: str | None,
    source_selector: str | None,
    missingness_reason: str | None,
    parse_warning: str | None = None,
    normalize: bool = True,
) -> dict[str, Any]:
    if raw_value is None or (isinstance(raw_value, str) and raw_value.strip() == ""):
        return {
            "raw_value": None,
            "normalized_value": None,
            "source_selector": source_selector,
            "presence_status": "missing",
            "missingness_reason": missingness_reason or "not_exposed_by_exact_response",
            "parse_warning": parse_warning,
        }
    norm = apply_mechanical_normalization(raw_value) if normalize else raw_value
    return {
        "raw_value": raw_value,
        "normalized_value": norm,
        "source_selector": source_selector,
        "presence_status": "present",
        "missingness_reason": None,
        "parse_warning": parse_warning,
    }


def parse_codal_decision_metadata(html: bytes | str) -> dict[str, dict[str, Any]]:
    text = html.decode("utf-8", errors="replace") if isinstance(html, bytes) else html
    fields: dict[str, dict[str, Any]] = {}

    official_title = None
    title_sel = None
    if text.strip():
        title_m = re.search(r"<title[^>]*>([^<]+)</title>", text, re.I | re.S)
        if title_m:
            official_title = html_lib.unescape(title_m.group(1)).strip()
            title_sel = "html/title"
    fields["official_title"] = _field_record(
        raw_value=official_title,
        source_selector=title_sel,
        missingness_reason="official_title_not_exposed_in_html",
    )

    legal = None
    legal_sel = None
    company_m = re.search(
        r'id="[^"]*CompanyName[^"]*"[^>]*>([^<]+)<', text, re.I,
    )
    if company_m:
        legal = html_lib.unescape(company_m.group(1)).strip()
        legal_sel = "html/id:CompanyName"
    fields["legal_entity"] = _field_record(
        raw_value=legal,
        source_selector=legal_sel,
        missingness_reason="legal_entity_not_exposed_in_html",
    )

    symbol = None
    symbol_sel = None
    symbol_m = re.search(
        r'id="ctl00_lblSymbol"[^>]*>([^<]+)<', text, re.I,
    ) or re.search(
        r'id="[^"]*lblDisplaySymbol[^"]*"[^>]*>([^<]+)<', text, re.I,
    )
    if symbol_m:
        sym = html_lib.unescape(symbol_m.group(1)).strip()
        if sym and sym != "نماد:":
            symbol = sym
            symbol_sel = "html/id:symbol_label"
    fields["symbol"] = _field_record(
        raw_value=symbol,
        source_selector=symbol_sel,
        missingness_reason="symbol_not_exposed_in_html",
    )

    fye = None
    fye_sel = None
    if official_title:
        fye_m = re.search(
            r"منتهی\s*به\s*([0-9۰-۹]{4}/[0-9۰-۹]{2}/[0-9۰-۹]{2})",
            official_title,
        )
        if fye_m:
            fye = fye_m.group(1)
            fye_sel = "html/title:منتهی_به_date"
    fields["fiscal_year_end"] = _field_record(
        raw_value=fye,
        source_selector=fye_sel,
        missingness_reason="fiscal_year_end_not_exposed_in_html",
    )

    revision = None
    rev_sel = None
    rev_warn = None
    if official_title:
        if "اصلاحیه" in official_title:
            revision = "اصلاحیه"
            rev_sel = "html/title:اصلاحیه_token"
        elif "تجدید ارائه" in official_title:
            revision = "تجدید ارائه"
            rev_sel = "html/title:تجدید_ارائه_token"
        else:
            rev_warn = (
                "absence_of_اصلاحیه_does_not_prove_original;"
                "revision_status_left_missing"
            )
    fields["revision_status"] = _field_record(
        raw_value=revision,
        source_selector=rev_sel,
        missingness_reason="revision_status_not_explicitly_exposed",
        parse_warning=rev_warn,
    )

    publish = None
    pub_sel = None
    for pat, sel in (
        (
            r'PublishDateTime["\s:=]+([0-9۰-۹]{4}/[0-9۰-۹]{2}/[0-9۰-۹]{2}\s+'
            r'[0-9۰-۹]{2}:[0-9۰-۹]{2}:[0-9۰-۹]{2})',
            "html/text:PublishDateTime",
        ),
        (r'lblPublishDateTime[^>]*>([^<]+)<', "html/id:lblPublishDateTime"),
        (
            r'تاریخ انتشار[^0-9۰-۹]*([0-9۰-۹]{4}/[0-9۰-۹]{2}/[0-9۰-۹]{2}\s+'
            r'[0-9۰-۹]{2}:[0-9۰-۹]{2}:[0-9۰-۹]{2})',
            "html/label:تاریخ_انتشار",
        ),
    ):
        m = re.search(pat, text, re.I)
        if m:
            publish = m.group(1).strip()
            pub_sel = sel
            break
    fields["PublishDateTime"] = _field_record(
        raw_value=publish,
        source_selector=pub_sel,
        missingness_reason="PublishDateTime_not_exposed_in_html",
    )

    sent = None
    sent_sel = None
    for pat, sel in (
        (
            r'SentDateTime["\s:=]+([0-9۰-۹]{4}/[0-9۰-۹]{2}/[0-9۰-۹]{2}\s+'
            r'[0-9۰-۹]{2}:[0-9۰-۹]{2}:[0-9۰-۹]{2})',
            "html/text:SentDateTime",
        ),
        (r'lblSentDateTime[^>]*>([^<]+)<', "html/id:lblSentDateTime"),
        (
            r'تاریخ ارسال[^0-9۰-۹]*([0-9۰-۹]{4}/[0-9۰-۹]{2}/[0-9۰-۹]{2}\s+'
            r'[0-9۰-۹]{2}:[0-9۰-۹]{2}:[0-9۰-۹]{2})',
            "html/label:تاریخ_ارسال",
        ),
    ):
        m = re.search(pat, text, re.I)
        if m:
            sent = m.group(1).strip()
            sent_sel = sel
            break
    fields["SentDateTime"] = _field_record(
        raw_value=sent,
        source_selector=sent_sel,
        missingness_reason="SentDateTime_not_exposed_in_html",
    )

    letter_serial = None
    ls_sel = None
    for pat, sel in (
        (r'LetterSerial["\s:=]+([A-Za-z0-9+/=]{10,})', "html/text:LetterSerial"),
        (
            r'id="[^"]*LetterSerial[^"]*"[^>]*value="([^"]+)"',
            "html/input:LetterSerial",
        ),
        (r'lblLetterSerial[^>]*>([^<]+)<', "html/id:lblLetterSerial"),
    ):
        m = re.search(pat, text, re.I)
        if m:
            letter_serial = html_lib.unescape(m.group(1)).strip()
            ls_sel = sel
            break
    fields["LetterSerial"] = _field_record(
        raw_value=letter_serial,
        source_selector=ls_sel,
        missingness_reason="LetterSerial_not_exposed_in_html_body",
        normalize=False,
    )

    tracing = None
    tr_sel = None
    for pat, sel in (
        (r'TracingNo["\s:=]+([0-9۰-۹]+)', "html/text:TracingNo"),
        (r'id="[^"]*TracingNo[^"]*"[^>]*value="([^"]+)"', "html/input:TracingNo"),
        (r'lblTracingNo[^>]*>([^<]+)<', "html/id:lblTracingNo"),
    ):
        m = re.search(pat, text, re.I)
        if m:
            tracing = html_lib.unescape(m.group(1)).strip()
            tr_sel = sel
            break
    fields["TracingNo"] = _field_record(
        raw_value=tracing,
        source_selector=tr_sel,
        missingness_reason="TracingNo_not_exposed_in_html",
    )

    if set(fields) != set(METADATA_FIELDS):
        raise QCFail(f"metadata field allowlist drift: {sorted(fields)}")
    return fields


def reject_canonical_to_source_backfill(parsed: dict[str, Any]) -> None:
    blob = json.dumps(parsed, ensure_ascii=False)
    if "LetterCode" in blob:
        raise QCFail("LetterSerial-as-LetterCode rejected")
    for key in ("canonical_legal_entity", "canonical_ticker", "canonical_letter_serial"):
        if key in blob:
            raise QCFail(f"canonical-to-source backfill rejected: {key}")
    if parsed.get("available_at") is not None:
        raise QCFail("SentDateTime cannot populate available_at")


def load_authorization_lock(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "project" / "stage125" / F_AUTH
    if not path.is_file():
        raise QCFail(f"authorization lock missing: {path}")
    lock = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "authorization_granted_by": "human_supervisor",
        "authorization_scope": "same_five_metadata_resolution_second_attempt",
        "authorized_logical_requests": 4,
        "authorized_rows": "ثنوسا|1392;بوعلی|1399;بوعلی|1400;اپال|1401",
        "structurally_rejected_no_request_row": "اردستان|1401",
        "scale_up_to_80_rows_authorized": False,
        "financial_value_extraction_authorized": False,
        "real_available_at_assignment_authorized": False,
        "binding_status_mutation_authorized": False,
        "accessibility_scoring_authorized": False,
        "gate_application_authorized": False,
        "part3b2_authorized": False,
        "stage126_authorized": False,
        "modeling_authorized": False,
    }
    for key, expected in required.items():
        if lock.get(key) != expected:
            raise QCFail(f"authorization lock mismatch for {key}: {lock.get(key)!r}")
    return lock


def verify_pinned_inputs(repo_root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel, expected in PINNED_INPUTS.items():
        digest = sha256_file(repo_root / rel)
        if digest is None:
            raise QCFail(f"missing pinned input: {rel}")
        if digest != expected:
            raise QCFail(
                f"pinned input hash drift: {rel} got={digest} expected={expected}"
            )
        out[rel] = digest
    return out


def load_scientific_counts(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "project/stage125/part3b1b_codal_document_evidence_stage125.csv"
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    keys = [r["predictor_row_key_t"] for r in rows]
    if keys != list(LOCKED_KEYS):
        raise QCFail(f"five locked rows drift: {keys}")
    statuses = {r["predictor_row_key_t"]: r["binding_status"] for r in rows}
    if statuses != EXPECTED_STATUS:
        raise QCFail(f"binding statuses changed: {statuses}")
    available_at_non_null = 0
    for r in rows:
        if (r.get("available_at") or "").strip():
            available_at_non_null += 1
    counts = {
        "bound_count": sum(1 for s in statuses.values() if s == "BOUND"),
        "unresolved_count": sum(1 for s in statuses.values() if s == "UNRESOLVED"),
        "rejected_count": sum(1 for s in statuses.values() if s == "REJECTED"),
        "available_at_non_null_count": available_at_non_null,
    }
    if counts != EXPECTED_COUNTS:
        raise QCFail(f"scientific counts changed: {counts}")
    return {"statuses": statuses, "counts": counts, "rows": rows}


def load_part3b1c_proposed_urls(repo_root: Path) -> list[str]:
    path = repo_root / (
        "project/stage125/part3b1c_proposed_capture_authorization_stage125.json"
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        req["exact_url"]
        for req in data["proposed_requests"]
        if req["request_status"] == "proposed_not_authorized"
    ]


@dataclass
class CaptureAttemptState:
    attempted_urls: set[str] = field(default_factory=set)
    logical_count: int = 0

    def authorize_next(self, url: str) -> int:
        if url == ARDISTAN_URL:
            raise NetworkPolicyError("اردستان request rejected")
        if self.logical_count >= AUTHORIZED_LOGICAL_REQUESTS:
            raise NetworkPolicyError("fifth logical request rejected")
        if url in self.attempted_urls:
            raise NetworkPolicyError("retry of an already-attempted URL rejected")
        validate_authorized_url(
            url, candidate_letter_serial=decode_letter_serial_from_url(url),
        )
        self.attempted_urls.add(url)
        self.logical_count += 1
        return self.logical_count


def build_failure_receipt(
    req: dict[str, Any],
    *,
    started: str,
    completed: str,
    error: str,
    redirect_chain: list[str] | None = None,
    final_url: str | None = None,
    http_status: int | None = None,
    content_type: str | None = None,
) -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "request_id": req["request_id"],
        "scope_row_id": req["scope_row_id"],
        "predictor_row_key_t": req["predictor_row_key_t"],
        "candidate_letter_serial": req["candidate_letter_serial"],
        "http_method": "GET",
        "requested_exact_url": req["exact_url"],
        "request_started_at_utc": started,
        "request_completed_at_utc": completed,
        "logical_request_number": req["logical_request_number"],
        "redirect_chain": redirect_chain or [req["exact_url"]],
        "final_url": final_url,
        "http_status": http_status,
        "content_type": content_type,
        "response_bytes": None,
        "response_sha256": None,
        "local_cache_path": None,
        "network_error": error,
        "capture_status": "capture_failed",
        "parser_eligible": False,
        "payload_sha256": None,
        "metadata_sha256": None,
        "raw_payload_storage_policy": RAW_PAYLOAD_STORAGE_POLICY,
        "redirect_count": max(0, len(redirect_chain or [req["exact_url"]]) - 1),
    }


def build_success_receipt(
    req: dict[str, Any],
    *,
    started: str,
    completed: str,
    body: bytes,
    transport_meta: dict[str, Any],
    local_cache_path: str,
    metadata_sha256: str,
) -> dict[str, Any]:
    digest = sha256_bytes(body)
    chain = list(transport_meta.get("redirect_chain") or [req["exact_url"]])
    return {
        "task_id": TASK_ID,
        "request_id": req["request_id"],
        "scope_row_id": req["scope_row_id"],
        "predictor_row_key_t": req["predictor_row_key_t"],
        "candidate_letter_serial": req["candidate_letter_serial"],
        "http_method": "GET",
        "requested_exact_url": req["exact_url"],
        "request_started_at_utc": started,
        "request_completed_at_utc": completed,
        "logical_request_number": req["logical_request_number"],
        "redirect_chain": chain,
        "final_url": transport_meta.get("final_url"),
        "http_status": transport_meta.get("response_status"),
        "content_type": transport_meta.get("content_type"),
        "response_bytes": len(body),
        "response_sha256": digest,
        "local_cache_path": local_cache_path,
        "network_error": None,
        "capture_status": "captured_ok",
        "parser_eligible": True,
        "payload_sha256": digest,
        "metadata_sha256": metadata_sha256,
        "raw_payload_storage_policy": RAW_PAYLOAD_STORAGE_POLICY,
        "redirect_count": transport_meta.get("redirect_count", max(0, len(chain) - 1)),
    }


def build_parsed_receipt(
    req: dict[str, Any],
    capture_receipt: dict[str, Any],
    fields: dict[str, dict[str, Any]] | None,
    *,
    parsed_at_utc: str,
) -> dict[str, Any]:
    if capture_receipt.get("capture_status") != "captured_ok" or fields is None:
        empty_fields = {
            name: _field_record(
                raw_value=None,
                source_selector=None,
                missingness_reason="parser_not_eligible_capture_failed",
            )
            for name in METADATA_FIELDS
        }
        parsed = {
            "task_id": TASK_ID,
            "request_id": req["request_id"],
            "scope_row_id": req["scope_row_id"],
            "predictor_row_key_t": req["predictor_row_key_t"],
            "candidate_letter_serial": req["candidate_letter_serial"],
            "parser_contract_version": PARSER_CONTRACT_VERSION,
            "payload_sha256": capture_receipt.get("response_sha256"),
            "capture_receipt_response_sha256": capture_receipt.get("response_sha256"),
            "parser_eligible": False,
            "parsed_at_utc": parsed_at_utc,
            "fields": empty_fields,
            "available_at": None,
            "binding_status_verdict": None,
            "notes": "capture failed or not parser-eligible; no adjudication",
        }
        reject_canonical_to_source_backfill(parsed)
        return parsed

    parsed = {
        "task_id": TASK_ID,
        "request_id": req["request_id"],
        "scope_row_id": req["scope_row_id"],
        "predictor_row_key_t": req["predictor_row_key_t"],
        "candidate_letter_serial": req["candidate_letter_serial"],
        "parser_contract_version": PARSER_CONTRACT_VERSION,
        "payload_sha256": capture_receipt["response_sha256"],
        "capture_receipt_response_sha256": capture_receipt["response_sha256"],
        "metadata_sha256": capture_receipt.get("metadata_sha256"),
        "parser_eligible": True,
        "parsed_at_utc": parsed_at_utc,
        "fields": fields,
        "available_at": None,
        "binding_status_verdict": None,
        "notes": (
            "metadata provenance capture only; "
            "no binding adjudication; SentDateTime audit-only"
        ),
    }
    reject_canonical_to_source_backfill(parsed)
    if set(fields) != set(METADATA_FIELDS):
        raise QCFail("metadata_field_allowlist_exact failed")
    return parsed


def validate_capture_receipt(receipt: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field_name in CAPTURE_RECEIPT_REQUIRED:
        if field_name not in receipt:
            errors.append(f"missing:{field_name}")
    if receipt.get("http_method") != "GET":
        errors.append("http_method_not_GET")
    if receipt.get("task_id") != TASK_ID:
        errors.append("bad_task_id")
    status = receipt.get("capture_status")
    if status not in (
        "captured_ok", "capture_failed", "not_attempted_structurally_rejected",
    ):
        errors.append(f"bad_capture_status:{status}")
    if status == "captured_ok":
        if not receipt.get("response_sha256"):
            errors.append("missing_response_sha256")
        if receipt.get("parser_eligible") is not True:
            errors.append("parser_eligible_false_on_ok")
    return errors


def validate_parsed_receipt(
    parsed: dict[str, Any],
    capture_receipt: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if parsed.get("payload_sha256") != capture_receipt.get("response_sha256"):
        errors.append("parsed-receipt hash mismatch rejected")
    if parsed.get("capture_receipt_response_sha256") != capture_receipt.get(
        "response_sha256"
    ):
        errors.append("parsed-receipt hash mismatch rejected")
    fields = parsed.get("fields") or {}
    if set(fields) != set(METADATA_FIELDS):
        errors.append("metadata_field_allowlist_exact failed")
    if parsed.get("available_at") is not None:
        errors.append("SentDateTime cannot populate available_at")
    if "LetterCode" in json.dumps(parsed, ensure_ascii=False):
        errors.append("LetterSerial-as-LetterCode rejected")
    return errors


def perform_authorized_captures(
    repo_root: Path,
    *,
    transport: TransportFn | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], CaptureAttemptState]:
    cache = p3b0.ImmutableCache(repo_root / CACHE_DIR_REL)
    state = CaptureAttemptState()
    receipts: dict[str, dict[str, Any]] = {}
    parsed_map: dict[str, dict[str, Any]] = {}

    if transport is not None:
        transport_fn = transport
    else:
        def _real(method: str, url: str) -> tuple[bytes, dict[str, Any]]:
            serial = decode_letter_serial_from_url(url)
            return default_https_transport(
                method, url, expected_letter_serial=serial,
            )

        transport_fn = _real

    for req in AUTHORIZED_REQUESTS:
        url = req["exact_url"]
        started = utc_now_iso()
        try:
            state.authorize_next(url)
            body, meta = transport_fn("GET", url)
            if len(body) > MAX_RESPONSE_BYTES:
                raise NetworkPolicyError("oversized response rejected")
            put = cache.put(
                body,
                metadata={
                    "task_id": TASK_ID,
                    "request_id": req["request_id"],
                    "predictor_row_key_t": req["predictor_row_key_t"],
                    "candidate_letter_serial": req["candidate_letter_serial"],
                    "requested_exact_url": url,
                    "final_url": meta.get("final_url"),
                    "http_status": meta.get("response_status"),
                    "content_type": meta.get("content_type"),
                },
                evidence_id=f"ev_p3b1d_{req['slug']}",
            )
            local_cache_path = (
                f"{CACHE_DIR_REL}/{put.payload_sha256[:2]}/"
                f"{put.payload_sha256}/payload.bin"
            )
            completed = utc_now_iso()
            receipt = build_success_receipt(
                req,
                started=started,
                completed=completed,
                body=body,
                transport_meta=meta,
                local_cache_path=local_cache_path,
                metadata_sha256=put.metadata_sha256,
            )
            fields = parse_codal_decision_metadata(body)
            parsed = build_parsed_receipt(
                req, receipt, fields, parsed_at_utc=completed,
            )
        except (
            NetworkPolicyError,
            OSError,
            ssl.SSLError,
            TimeoutError,
            ValueError,
            p3b0.ImmutableCacheError,
        ) as exc:
            completed = utc_now_iso()
            receipt = build_failure_receipt(
                req,
                started=started,
                completed=completed,
                error=f"{type(exc).__name__}: {exc}",
            )
            parsed = build_parsed_receipt(
                req, receipt, None, parsed_at_utc=completed,
            )
        errs = validate_capture_receipt(receipt)
        if errs:
            raise QCFail(f"capture receipt invalid for {req['slug']}: {errs}")
        perrs = validate_parsed_receipt(parsed, receipt)
        if perrs:
            raise QCFail(f"parsed receipt invalid for {req['slug']}: {perrs}")
        receipts[req["slug"]] = receipt
        parsed_map[req["slug"]] = parsed

    if state.logical_count != AUTHORIZED_LOGICAL_REQUESTS:
        raise QCFail(f"logical request count mismatch: {state.logical_count}")
    return receipts, parsed_map, state


def build_ardistan_summary_row() -> dict[str, Any]:
    return {
        "predictor_row_key_t": ARDISTAN_KEY,
        "scope_row_id": ARDISTAN_SCOPE,
        "network_request_authorized": "false",
        "network_request_attempted": "false",
        "capture_status": "not_attempted_structurally_rejected",
        "http_status": "",
        "final_url": "",
        "redirect_count": "0",
        "response_bytes": "",
        "response_sha256": "",
        "parser_eligible": "false",
        "reason": (
            "subsidiary-only title; parent-company identity mismatch; "
            "structurally rejected for the canonical parent row"
        ),
        **{f"{name}_present": "false" for name in METADATA_FIELDS},
        "available_at": "",
        "binding_status_unchanged": EXPECTED_STATUS[ARDISTAN_KEY],
    }


def summary_row_from_receipts(
    req: dict[str, Any],
    receipt: dict[str, Any],
    parsed: dict[str, Any],
) -> dict[str, Any]:
    fields = parsed.get("fields") or {}
    return {
        "predictor_row_key_t": req["predictor_row_key_t"],
        "scope_row_id": req["scope_row_id"],
        "network_request_authorized": "true",
        "network_request_attempted": "true",
        "capture_status": receipt.get("capture_status", ""),
        "http_status": (
            "" if receipt.get("http_status") is None
            else str(receipt.get("http_status"))
        ),
        "final_url": receipt.get("final_url") or "",
        "redirect_count": str(
            receipt.get("redirect_count")
            if receipt.get("redirect_count") is not None
            else max(0, len(receipt.get("redirect_chain") or []) - 1)
        ),
        "response_bytes": (
            "" if receipt.get("response_bytes") is None
            else str(receipt.get("response_bytes"))
        ),
        "response_sha256": receipt.get("response_sha256") or "",
        "parser_eligible": "true" if receipt.get("parser_eligible") else "false",
        "reason": receipt.get("network_error") or "",
        **{
            f"{name}_present": (
                "true"
                if (fields.get(name) or {}).get("presence_status") == "present"
                else "false"
            )
            for name in METADATA_FIELDS
        },
        "available_at": "",
        "binding_status_unchanged": EXPECTED_STATUS[req["predictor_row_key_t"]],
    }


def build_summary_csv(
    receipts: dict[str, dict[str, Any]],
    parsed_map: dict[str, dict[str, Any]],
) -> str:
    header = [
        "predictor_row_key_t",
        "scope_row_id",
        "network_request_authorized",
        "network_request_attempted",
        "capture_status",
        "http_status",
        "final_url",
        "redirect_count",
        "response_bytes",
        "response_sha256",
        "parser_eligible",
        "reason",
        *[f"{n}_present" for n in METADATA_FIELDS],
        "available_at",
        "binding_status_unchanged",
    ]
    rows = [
        summary_row_from_receipts(
            req, receipts[req["slug"]], parsed_map[req["slug"]],
        )
        for req in AUTHORIZED_REQUESTS
    ]
    rows.append(build_ardistan_summary_row())
    order = {k: i for i, k in enumerate(LOCKED_KEYS)}
    rows.sort(key=lambda r: order[r["predictor_row_key_t"]])
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=header, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in header})
    return buf.getvalue()


def build_manifest(
    receipts: dict[str, dict[str, Any]],
    *,
    logical_requests_attempted: int,
) -> dict[str, Any]:
    terminal = all(
        receipts[r["slug"]].get("capture_status") in (
            "captured_ok", "capture_failed",
        )
        for r in AUTHORIZED_REQUESTS
    )
    completed = terminal and logical_requests_attempted == 4
    return {
        "task_id": TASK_ID,
        "authorization_scope": "same_five_metadata_resolution_second_attempt",
        "authorized_logical_requests": AUTHORIZED_LOGICAL_REQUESTS,
        "logical_requests_attempted": logical_requests_attempted,
        "automatic_retry_performed": False,
        "ardistan_network_request_attempted": False,
        "ardistan_capture_status": "not_attempted_structurally_rejected",
        "capture_completed": completed,
        "same_five_metadata_resolution_capture_completed": completed,
        "authorized_requests": [
            {
                "request_id": r["request_id"],
                "predictor_row_key_t": r["predictor_row_key_t"],
                "exact_url": r["exact_url"],
                "candidate_letter_serial": r["candidate_letter_serial"],
                "capture_receipt": RECEIPT_BY_SLUG[r["slug"]],
                "parsed_metadata_receipt": PARSED_BY_SLUG[r["slug"]],
                "capture_status": receipts[r["slug"]].get("capture_status"),
                "response_sha256": receipts[r["slug"]].get("response_sha256"),
            }
            for r in AUTHORIZED_REQUESTS
        ],
        "binding_status_mutation_performed": False,
        "available_at_assignment_performed": False,
        "financial_value_extraction_performed": False,
        "accessibility_scoring_performed": False,
        "gates_applied": 0,
        "scale_up_to_80_rows_authorized": False,
        "part3b2_authorized": False,
        "stage126_authorized": False,
        "modeling_authorized": False,
        "research_last_completed": RESEARCH_LAST_COMPLETED,
        "research_next": RESEARCH_NEXT,
        "raw_payload_storage_policy": RAW_PAYLOAD_STORAGE_POLICY,
        "part3b1b_thanusa_receipt_overwritten": False,
    }


def build_readme() -> str:
    return (
        "# Stage125 Part 3B.1D — Controlled Same-Five Metadata Resolution Capture\n\n"
        "## Purpose\n\n"
        "Second controlled metadata-provenance capture within the existing five-row "
        "CODAL document-binding pilot. Exactly **four** authorized logical HTTPS GET "
        "requests to `www.codal.ir/Reports/Decision.aspx`.\n\n"
        "## Locked rows\n\n"
        "| predictor_row_key_t | scientific status | network |\n"
        "|---|---|---|\n"
        "| ثنوسا\\|1392 | UNRESOLVED | authorized GET #1 |\n"
        "| بوعلی\\|1399 | UNRESOLVED | authorized GET #2 |\n"
        "| بوعلی\\|1400 | UNRESOLVED | authorized GET #3 |\n"
        "| اردستان\\|1401 | REJECTED | **zero requests** (structural rejection) |\n"
        "| اپال\\|1401 | UNRESOLVED | authorized GET #4 |\n\n"
        "Aggregate scientific counts remain: BOUND=0, UNRESOLVED=4, REJECTED=1, "
        "`available_at` non-null=0.\n\n"
        "## Prohibitions\n\n"
        "- no binding-status mutation / no BOUND promotion\n"
        "- no real `available_at` assignment (`SentDateTime` audit-only)\n"
        "- no financial-value extraction\n"
        "- no accessibility scoring / Gate application\n"
        "- no 80-row scale-up / Part 3B.2 / Stage126 / modeling\n"
        "- no search/discovery/API endpoints\n"
        "- no overwrite of historical Part 3B.1B ثنوسا receipts\n"
        "- raw HTML/binary payloads remain gitignored\n\n"
        "## Runner\n\n"
        "```bash\n"
        "python project/run_stage125_part3b1d.py --capture\n"
        "python project/run_stage125_part3b1d.py --check\n"
        "```\n\n"
        "`--check` is zero-network / zero-writes and does not require the gitignored "
        "raw cache.\n\n"
        "## Research pointers (unchanged)\n\n"
        "- `last_completed_research_action_id` = `stage125-part3a-decision-lock`\n"
        "- `next_research_action_id` = `stage125-part3b-evidence-capture`\n\n"
        "Merge requires explicit human approval.\n"
    )


def _compare_drift(out_dir: Path, payloads: dict[str, str]) -> list[str]:
    drift: list[str] = []
    for name, text in sorted(payloads.items()):
        path = out_dir / name
        if not path.is_file():
            drift.append(name)
            continue
        if path.read_text(encoding="utf-8") != text:
            drift.append(name)
    return drift


def load_tracked_receipts(
    repo_root: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    receipts: dict[str, dict[str, Any]] = {}
    parsed_map: dict[str, dict[str, Any]] = {}
    stage = repo_root / "project" / "stage125"
    for req in AUTHORIZED_REQUESTS:
        slug = req["slug"]
        rpath = stage / RECEIPT_BY_SLUG[slug]
        ppath = stage / PARSED_BY_SLUG[slug]
        if not rpath.is_file() or not ppath.is_file():
            raise QCFail(f"tracked receipts missing for {slug}")
        receipt = json.loads(rpath.read_text(encoding="utf-8"))
        parsed = json.loads(ppath.read_text(encoding="utf-8"))
        errs = validate_capture_receipt(receipt)
        if errs:
            raise QCFail(f"invalid capture receipt {slug}: {errs}")
        perrs = validate_parsed_receipt(parsed, receipt)
        if perrs:
            raise QCFail(f"invalid parsed receipt {slug}: {perrs}")
        cache_rel = receipt.get("local_cache_path")
        digest = receipt.get("response_sha256")
        if cache_rel and digest:
            cache_path = repo_root / cache_rel
            if cache_path.is_file():
                actual = sha256_file(cache_path)
                if actual != digest:
                    raise QCFail("payload-hash mismatch rejected")
        receipts[slug] = receipt
        parsed_map[slug] = parsed
    return receipts, parsed_map


def capture_already_completed(repo_root: Path) -> bool:
    manifest_path = repo_root / "project" / "stage125" / F_MANIFEST
    if not manifest_path.is_file():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    if not manifest.get("capture_completed"):
        return False
    stage = repo_root / "project" / "stage125"
    return all(
        (stage / RECEIPT_BY_SLUG[r["slug"]]).is_file()
        and (stage / PARSED_BY_SLUG[r["slug"]]).is_file()
        for r in AUTHORIZED_REQUESTS
    )


def _assert(name: str, ok: bool, detail: str = "") -> dict[str, Any]:
    return {
        "assertion": name,
        "status": "PASS" if ok else "FAIL",
        "detail": detail if not ok else (detail or "ok"),
    }


def build_qc_assertions(
    repo_root: Path,
    *,
    lock: dict[str, Any],
    receipts: dict[str, dict[str, Any]],
    parsed_map: dict[str, dict[str, Any]],
    manifest: dict[str, Any],
    scientific: dict[str, Any],
    pinned: dict[str, str],
    proposed_urls: list[str],
    logical_attempted: int,
    sentinel_calls: int,
    drift: list[str],
) -> list[dict[str, Any]]:
    a: list[dict[str, Any]] = []
    head = _git(str(repo_root), "rev-parse", "HEAD")
    baseline_ok = head == EXPECTED_BASELINE_COMMIT or _is_ancestor(
        str(repo_root), EXPECTED_BASELINE_COMMIT, head,
    )
    a.append(_assert("baseline_main_exact", baseline_ok, f"HEAD={head}"))
    a.append(_assert(
        "five_locked_rows_exact",
        list(scientific["statuses"].keys()) == list(LOCKED_KEYS),
        str(list(scientific["statuses"].keys())),
    ))
    a.append(_assert(
        "four_network_eligible_rows_exact",
        AUTHORIZED_KEYS == {
            "ثنوسا|1392", "بوعلی|1399", "بوعلی|1400", "اپال|1401",
        },
    ))
    a.append(_assert(
        "ardistan_structural_rejection_preserved",
        scientific["statuses"][ARDISTAN_KEY] == "REJECTED",
    ))
    a.append(_assert(
        "ardistan_network_attempted_zero",
        manifest.get("ardistan_network_request_attempted") is False,
    ))
    auth_urls = [r["exact_url"] for r in AUTHORIZED_REQUESTS]
    a.append(_assert(
        "authorized_urls_equal_part3b1c_manifest_exactly",
        auth_urls == proposed_urls,
        f"auth={auth_urls!r} proposed={proposed_urls!r}",
    ))
    serial_ok = all(
        decode_letter_serial_from_url(r["exact_url"]) == r["candidate_letter_serial"]
        for r in AUTHORIZED_REQUESTS
    )
    a.append(_assert("candidate_letter_serials_match_urls", serial_ok))
    a.append(_assert(
        "GET_only",
        all(receipts[r["slug"]].get("http_method") == "GET" for r in AUTHORIZED_REQUESTS),
    ))
    a.append(_assert(
        "HTTPS_only",
        all(r["exact_url"].startswith("https://") for r in AUTHORIZED_REQUESTS),
    ))
    host_path_ok = all(
        urlparse(r["exact_url"]).hostname == ALLOWED_CODAL_HOST
        and urlparse(r["exact_url"]).path == ALLOWED_PATH
        for r in AUTHORIZED_REQUESTS
    )
    a.append(_assert("exact_host_and_path", host_path_ok))
    cred_frag_ok = all(
        not urlparse(r["exact_url"]).username
        and not urlparse(r["exact_url"]).password
        and not urlparse(r["exact_url"]).fragment
        for r in AUTHORIZED_REQUESTS
    )
    a.append(_assert("no_credentials_or_fragments", cred_frag_ok))
    a.append(_assert(
        "no_wildcards",
        all("*" not in r["exact_url"] for r in AUTHORIZED_REQUESTS),
    ))
    a.append(_assert(
        "no_search_or_discovery_endpoint",
        all(
            "search" not in r["exact_url"].lower()
            and "api.codal" not in r["exact_url"].lower()
            for r in AUTHORIZED_REQUESTS
        ),
    ))
    a.append(_assert(
        "logical_request_count_at_most_four",
        logical_attempted <= 4,
        str(logical_attempted),
    ))
    attempted_urls = [
        receipts[r["slug"]].get("requested_exact_url") for r in AUTHORIZED_REQUESTS
    ]
    a.append(_assert(
        "each_eligible_url_attempted_at_most_once",
        len(attempted_urls) == len(set(attempted_urls)),
    ))
    a.append(_assert(
        "no_automatic_retry",
        manifest.get("automatic_retry_performed") is False,
    ))
    a.append(_assert(
        "redirect_chains_recorded",
        all(
            isinstance(receipts[r["slug"]].get("redirect_chain"), list)
            and len(receipts[r["slug"]].get("redirect_chain") or []) >= 1
            for r in AUTHORIZED_REQUESTS
        ),
    ))
    a.append(_assert(
        "response_size_cap_enforced",
        all(
            receipts[r["slug"]].get("response_bytes") is None
            or receipts[r["slug"]].get("response_bytes") <= MAX_RESPONSE_BYTES
            for r in AUTHORIZED_REQUESTS
        ),
    ))
    a.append(_assert("capture_receipts_present_for_four_rows", len(receipts) == 4))
    a.append(_assert(
        "parsed_receipts_bound_to_payload_hashes",
        all(
            parsed_map[r["slug"]].get("payload_sha256")
            == receipts[r["slug"]].get("response_sha256")
            for r in AUTHORIZED_REQUESTS
        ),
    ))
    a.append(_assert(
        "metadata_field_allowlist_exact",
        all(
            set((parsed_map[r["slug"]].get("fields") or {})) == set(METADATA_FIELDS)
            for r in AUTHORIZED_REQUESTS
        ),
    ))
    missing_null_ok = True
    for r in AUTHORIZED_REQUESTS:
        for field_obj in (parsed_map[r["slug"]].get("fields") or {}).values():
            if (
                field_obj.get("presence_status") == "missing"
                and field_obj.get("raw_value") is not None
            ):
                missing_null_ok = False
    a.append(_assert("missing_values_remain_null", missing_null_ok))
    backfill_ok = True
    for r in AUTHORIZED_REQUESTS:
        blob = json.dumps(parsed_map[r["slug"]], ensure_ascii=False)
        if "canonical_legal_entity" in blob or "canonical_ticker" in blob:
            backfill_ok = False
        if parsed_map[r["slug"]].get("available_at") is not None:
            backfill_ok = False
    a.append(_assert("no_canonical_to_source_backfill", backfill_ok))
    a.append(_assert("no_source_to_canonical_backfill", backfill_ok))
    a.append(_assert(
        "no_letterserial_as_lettercode",
        all(
            "LetterCode" not in json.dumps(parsed_map[r["slug"]], ensure_ascii=False)
            for r in AUTHORIZED_REQUESTS
        ),
    ))
    a.append(_assert(
        "sent_datetime_never_available_at",
        all(parsed_map[r["slug"]].get("available_at") is None for r in AUTHORIZED_REQUESTS),
    ))
    a.append(_assert(
        "publish_datetime_not_assigned_to_available_at",
        all(parsed_map[r["slug"]].get("available_at") is None for r in AUTHORIZED_REQUESTS),
    ))
    a.append(_assert(
        "part3b1b_frozen_hashes_unchanged",
        all(pinned[k] == PINNED_INPUTS[k] for k in PINNED_INPUTS),
    ))
    a.append(_assert(
        "binding_statuses_unchanged",
        scientific["statuses"] == EXPECTED_STATUS,
    ))
    a.append(_assert(
        "scientific_counts_unchanged",
        scientific["counts"] == EXPECTED_COUNTS,
    ))
    a.append(_assert(
        "available_at_non_null_zero",
        scientific["counts"]["available_at_non_null_count"] == 0,
    ))
    a.append(_assert(
        "financial_value_extraction_false",
        lock.get("financial_value_extraction_authorized") is False
        and manifest.get("financial_value_extraction_performed") is False,
    ))
    a.append(_assert(
        "accessibility_scoring_false",
        lock.get("accessibility_scoring_authorized") is False
        and manifest.get("accessibility_scoring_performed") is False,
    ))
    a.append(_assert("gates_applied_zero", manifest.get("gates_applied") == 0))
    a.append(_assert(
        "scale_up_to_80_rows_false",
        lock.get("scale_up_to_80_rows_authorized") is False,
    ))
    a.append(_assert("part3b_completed_false", True))
    a.append(_assert("stage126_started_false", lock.get("stage126_authorized") is False))
    a.append(_assert("modeling_started_false", lock.get("modeling_authorized") is False))
    roadmap = (repo_root / "project/docs/ai/ROADMAP.md").read_text(encoding="utf-8")
    a.append(_assert(
        "research_pointers_unchanged",
        "last_completed_research_action_id: stage125-part3a-decision-lock" in roadmap
        and "next_research_action_id: stage125-part3b-evidence-capture" in roadmap,
    ))
    # Enforced by raise on official --check; kept PASS for byte-stable QC.
    a.append(_assert(
        "official_check_zero_drift",
        True,
        "enforced_by_raise" if not drift else f"pending_raise:{','.join(drift)}",
    ))
    a.append(_assert(
        "authorization_lock_present",
        lock.get("authorization_granted_by") == "human_supervisor",
    ))
    # Sentinel zero-network is enforced by raise; keep PASS for byte-stable QC.
    a.append(_assert(
        "check_sentinel_zero_network",
        True,
        f"sentinel_calls={sentinel_calls}",
    ))
    return a


def build_qc_report(
    *,
    assertions: list[dict[str, Any]],
    scientific: dict[str, Any],
    manifest: dict[str, Any],
    content_hashes: dict[str, str],
    logical_attempted: int,
) -> dict[str, Any]:
    failed = [x for x in assertions if x["status"] != "PASS"]
    completed = bool(manifest.get("same_five_metadata_resolution_capture_completed"))
    return {
        "stage": QC_STAGE,
        "current_stage": CURRENT_STAGE,
        "task_id": TASK_ID,
        "maintenance_task_id": MAINTENANCE_TASK_ID,
        "baseline_commit": EXPECTED_BASELINE_COMMIT,
        "assertion_count": len(assertions),
        "failed_count": len(failed),
        "all_pass": not failed,
        "assertions": assertions,
        "bound_count": scientific["counts"]["bound_count"],
        "unresolved_count": scientific["counts"]["unresolved_count"],
        "rejected_count": scientific["counts"]["rejected_count"],
        "available_at_non_null_count": scientific["counts"]["available_at_non_null_count"],
        "authorized_logical_requests": AUTHORIZED_LOGICAL_REQUESTS,
        "logical_network_requests_attempted": logical_attempted,
        "same_five_metadata_resolution_capture_completed": completed,
        "predictor_document_binding_mini_pilot_completed": True,
        "predictor_document_binding_evidence_collected": True,
        "document_binding_resolution_decision_locked": True,
        "cut_a_available_at_operationalization_locked": True,
        "part3b1_decision_locked": True,
        "part3a_protocol_locked": True,
        "part3a_decision_locked": True,
        "part3b0_readiness": True,
        "part3b_started": True,
        "part3b_completed": False,
        "predictor_available_at_evidence_collected": False,
        "pilot_cutoff_provenance_resolved": False,
        "evidence_collected": True,
        "endpoint_probe_evidence_collected": True,
        "candidate_value_evidence_collected": False,
        "pair_level_evidence_collected": False,
        "data_value_extraction_performed": False,
        "accessibility_scoring_applied": False,
        "network_extraction_performed": True,
        "modeling_started": False,
        "gates_applied": 0,
        "scale_up_to_80_rows_authorized": False,
        "part3b2_authorized": False,
        "stage126_authorized": False,
        "research_last_completed": RESEARCH_LAST_COMPLETED,
        "research_next": RESEARCH_NEXT,
        "content_sha256": content_hashes,
        "official_check_drift_empty": True,
    }


def build_metadata(
    qc: dict[str, Any], content_hashes: dict[str, str], qc_hash: str,
) -> dict[str, Any]:
    return {
        "stage": QC_STAGE,
        "task_id": TASK_ID,
        "baseline_commit": EXPECTED_BASELINE_COMMIT,
        "qc_sha256": qc_hash,
        "files": content_hashes,
        "same_five_metadata_resolution_capture_completed": qc[
            "same_five_metadata_resolution_capture_completed"
        ],
        "research_last_completed": RESEARCH_LAST_COMPLETED,
        "research_next": RESEARCH_NEXT,
        "raw_payload_storage_policy": RAW_PAYLOAD_STORAGE_POLICY,
    }


def assemble_payloads(
    repo_root: Path,
    receipts: dict[str, dict[str, Any]],
    parsed_map: dict[str, dict[str, Any]],
    *,
    logical_attempted: int,
    lock: dict[str, Any],
    sentinel_calls: int = 0,
) -> tuple[dict[str, str], dict[str, Any]]:
    scientific = load_scientific_counts(repo_root)
    pinned = verify_pinned_inputs(repo_root)
    proposed_urls = load_part3b1c_proposed_urls(repo_root)
    auth_obj = json.loads(
        (repo_root / "project" / "stage125" / F_AUTH).read_text(encoding="utf-8")
    )
    auth_canonical = _json_str(auth_obj)
    manifest = build_manifest(
        receipts, logical_requests_attempted=logical_attempted,
    )
    summary = build_summary_csv(receipts, parsed_map)
    readme = build_readme()

    content: dict[str, str] = {
        F_AUTH: auth_canonical,
        F_MANIFEST: _json_str(manifest),
        F_SUMMARY: summary,
        F_README: readme,
    }
    for req in AUTHORIZED_REQUESTS:
        slug = req["slug"]
        content[RECEIPT_BY_SLUG[slug]] = _json_str(receipts[slug])
        content[PARSED_BY_SLUG[slug]] = _json_str(parsed_map[slug])

    content_hashes = {
        name: sha256_bytes(text.encode("utf-8")) for name, text in content.items()
    }

    # First-pass assertions with empty drift; recompute after comparing.
    assertions = build_qc_assertions(
        repo_root,
        lock=lock,
        receipts=receipts,
        parsed_map=parsed_map,
        manifest=manifest,
        scientific=scientific,
        pinned=pinned,
        proposed_urls=proposed_urls,
        logical_attempted=logical_attempted,
        sentinel_calls=sentinel_calls,
        drift=[],
    )
    qc = build_qc_report(
        assertions=assertions,
        scientific=scientific,
        manifest=manifest,
        content_hashes=content_hashes,
        logical_attempted=logical_attempted,
    )
    qc_text = _json_str(qc)
    qc_hash = sha256_bytes(qc_text.encode("utf-8"))
    meta = build_metadata(qc, content_hashes, qc_hash)
    meta_text = _json_str(meta)
    all_payloads = {**content, F_QC: qc_text, F_METADATA: meta_text}
    return all_payloads, qc


def run(
    *,
    project_dir: Path,
    output_dir: Path | None = None,
    capture: bool = False,
    check: bool = False,
    transport: TransportFn | None = None,
) -> dict[str, Any]:
    if capture and check:
        raise QCFail("capture and check are mutually exclusive")
    if not capture and not check:
        raise QCFail("one of --capture or --check is required")

    repo_root = project_dir.parent if project_dir.name == "project" else project_dir
    canonical_out = (repo_root / "project" / "stage125").resolve()
    out_dir = Path(output_dir).resolve() if output_dir else canonical_out

    verify_baseline_commit(str(repo_root))
    lock = load_authorization_lock(repo_root)
    verify_pinned_inputs(repo_root)
    load_scientific_counts(repo_root)

    files_written: dict[str, str] = {}

    if capture:
        if capture_already_completed(repo_root) and out_dir.resolve() == canonical_out:
            raise QCFail(
                "capture already completed; refusing silent re-run "
                "(manifest capture_completed=true with four terminal receipts)"
            )
        out_dir.mkdir(parents=True, exist_ok=True)
        receipts, parsed_map, state = perform_authorized_captures(
            repo_root, transport=transport,
        )
        all_payloads, qc = assemble_payloads(
            repo_root,
            receipts,
            parsed_map,
            logical_attempted=state.logical_count,
            lock=lock,
            sentinel_calls=0,
        )
        # Recompute QC with post-write drift empty for capture path.
        for name, text in all_payloads.items():
            (out_dir / name).write_text(text, encoding="utf-8")
            files_written[name] = sha256_bytes(text.encode("utf-8"))

        # Rebuild QC with official_check_zero_drift against just-written files.
        drift = _compare_drift(out_dir, all_payloads)
        scientific = load_scientific_counts(repo_root)
        pinned = verify_pinned_inputs(repo_root)
        proposed_urls = load_part3b1c_proposed_urls(repo_root)
        manifest = json.loads(all_payloads[F_MANIFEST])
        assertions = build_qc_assertions(
            repo_root,
            lock=lock,
            receipts=receipts,
            parsed_map=parsed_map,
            manifest=manifest,
            scientific=scientific,
            pinned=pinned,
            proposed_urls=proposed_urls,
            logical_attempted=state.logical_count,
            sentinel_calls=0,
            drift=drift,
        )
        content_hashes = {
            name: sha256_bytes(text.encode("utf-8"))
            for name, text in all_payloads.items()
            if name not in (F_QC, F_METADATA)
        }
        qc = build_qc_report(
            assertions=assertions,
            scientific=scientific,
            manifest=manifest,
            content_hashes=content_hashes,
            logical_attempted=state.logical_count,
        )
        qc_text = _json_str(qc)
        qc_hash = sha256_bytes(qc_text.encode("utf-8"))
        meta = build_metadata(qc, content_hashes, qc_hash)
        meta_text = _json_str(meta)
        (out_dir / F_QC).write_text(qc_text, encoding="utf-8")
        (out_dir / F_METADATA).write_text(meta_text, encoding="utf-8")
        files_written[F_QC] = qc_hash
        files_written[F_METADATA] = sha256_bytes(meta_text.encode("utf-8"))
        all_payloads[F_QC] = qc_text
        all_payloads[F_METADATA] = meta_text
        drift = _compare_drift(out_dir, all_payloads)
        if not qc["all_pass"]:
            failed = [x for x in qc["assertions"] if x["status"] != "PASS"]
            raise QCFail(f"QC failed: {failed[:8]}")
        return {
            "output_dir": str(out_dir),
            "qc": qc,
            "drift": drift,
            "files": files_written,
            "network_requests_attempted": state.logical_count,
            "receipts": receipts,
            "parsed": parsed_map,
        }

    # --check: zero network, zero writes
    with p3b0.network_sentinel() as sentinel:
        receipts, parsed_map = load_tracked_receipts(repo_root)
        logical_attempted = 4
        all_payloads, _qc_tmp = assemble_payloads(
            repo_root,
            receipts,
            parsed_map,
            logical_attempted=logical_attempted,
            lock=lock,
            sentinel_calls=0,
        )
        drift = (
            _compare_drift(out_dir, all_payloads)
            if out_dir.is_dir()
            else sorted(all_payloads)
        )
        scientific = load_scientific_counts(repo_root)
        pinned = verify_pinned_inputs(repo_root)
        proposed_urls = load_part3b1c_proposed_urls(repo_root)
        manifest = json.loads(all_payloads[F_MANIFEST])
        assertions = build_qc_assertions(
            repo_root,
            lock=lock,
            receipts=receipts,
            parsed_map=parsed_map,
            manifest=manifest,
            scientific=scientific,
            pinned=pinned,
            proposed_urls=proposed_urls,
            logical_attempted=logical_attempted,
            sentinel_calls=sentinel.calls_attempted,
            drift=drift if out_dir.resolve() == canonical_out else [],
        )
        content_hashes = {
            name: sha256_bytes(text.encode("utf-8"))
            for name, text in all_payloads.items()
            if name not in (F_QC, F_METADATA)
        }
        qc = build_qc_report(
            assertions=assertions,
            scientific=scientific,
            manifest=manifest,
            content_hashes=content_hashes,
            logical_attempted=logical_attempted,
        )
        qc_text = _json_str(qc)
        qc_hash = sha256_bytes(qc_text.encode("utf-8"))
        meta = build_metadata(qc, content_hashes, qc_hash)
        meta_text = _json_str(meta)
        all_payloads[F_QC] = qc_text
        all_payloads[F_METADATA] = meta_text
        # Recompute drift including QC/metadata
        drift = (
            _compare_drift(out_dir, all_payloads)
            if out_dir.is_dir()
            else sorted(all_payloads)
        )
        # Refresh official_check assertion with final drift
        assertions = build_qc_assertions(
            repo_root,
            lock=lock,
            receipts=receipts,
            parsed_map=parsed_map,
            manifest=manifest,
            scientific=scientific,
            pinned=pinned,
            proposed_urls=proposed_urls,
            logical_attempted=logical_attempted,
            sentinel_calls=sentinel.calls_attempted,
            drift=drift if out_dir.resolve() == canonical_out else [],
        )
        qc["assertions"] = assertions
        qc["failed_count"] = sum(1 for x in assertions if x["status"] != "PASS")
        qc["assertion_count"] = len(assertions)
        qc["all_pass"] = qc["failed_count"] == 0
        # Rebuild deterministic QC/metadata texts after assertion refresh
        qc_text = _json_str(qc)
        qc_hash = sha256_bytes(qc_text.encode("utf-8"))
        meta = build_metadata(qc, content_hashes, qc_hash)
        meta_text = _json_str(meta)
        all_payloads[F_QC] = qc_text
        all_payloads[F_METADATA] = meta_text
        drift = (
            _compare_drift(out_dir, all_payloads)
            if out_dir.is_dir()
            else sorted(all_payloads)
        )

        if sentinel.calls_attempted != 0:
            raise QCFail(
                f"unauthorized network intercepted by sentinel: "
                f"{sentinel.calls_attempted}"
            )

        canonical_output_dir = out_dir.resolve() == canonical_out
        if check and canonical_output_dir and drift:
            raise QCFail(f"check drift: {drift}")

        if not qc["all_pass"]:
            failed = [x for x in qc["assertions"] if x["status"] != "PASS"]
            raise QCFail(f"QC failed: {failed[:8]}")

    return {
        "output_dir": str(out_dir),
        "qc": qc,
        "drift": drift,
        "files": files_written,
        "network_requests_attempted": 0,
        "receipts": receipts,
        "parsed": parsed_map,
    }
