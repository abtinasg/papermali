"""Stage128 Track B — the ONLY module permitted to open a network connection.

Isolation is the point. Every other module in this action (the offline builder,
the validators, the QC and the whole test suite) contains no network import and
no reachable network call. Keeping the socket in exactly one small, auditable
file is what makes that claim checkable.

Scope: ``stage128-m3-lag-wdi-exploratory-data-retrieval``, ``retrieval_only``.

What this layer does
--------------------
Performs one authorized retrieval session against the official World Bank WDI
API for EXACTLY the two locked indicators and EXACTLY the locked country, and
writes to an EXTERNAL bundle directory:

* the raw response body bytes of every attempt, success or failure;
* a request manifest and a response manifest;
* the redirect chain and response headers of every attempt;
* error/exception text for every failure.

What it never does
------------------
It does not parse an observation, read a value, compute a feature, a coverage
number or a Gate result, and it never joins anything to a company row. It
fetches bytes and records what happened at the transport level. Interpretation
is a LATER, SEPARATELY AUTHORIZED action
(``stage128-m3-lag-wdi-exploratory-post-retrieval-audit``), so this layer
deliberately stops at the byte boundary: it never even JSON-decodes a payload.

Structural fail-closed guarantees
---------------------------------
The indicator codes and the country are pinned constants. A URL is built only
by :func:`build_target_url`, which refuses anything outside that allowlist, and
every request is re-checked by :func:`assert_official_wdi_url` before a socket
opens and again on every redirect hop. There is no code path that can reach a
third indicator, another country, a non-official host or plain HTTP.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import ssl
import time
import traceback
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

# --------------------------------------------------------------------------- #
# The locked retrieval surface — pinned, not discovered
# --------------------------------------------------------------------------- #

ACTION_ID = "stage128-m3-lag-wdi-exploratory-data-retrieval"

#: The ONLY host that may terminate a request in this action.
OFFICIAL_WDI_API_HOST = "api.worldbank.org"

#: The two locked indicators, in their frozen contract order. This tuple is the
#: whole permitted retrieval surface: there is no discovery, no search and no
#: fallback. A third code cannot be reached from any code path here.
LOCKED_INDICATOR_CODES: tuple[str, ...] = (
    "FP.CPI.TOTL.ZG",     # Inflation, consumer prices (annual %)
    "PA.NUS.FCRF",        # Official exchange rate (LCU per US$, period average)
)

#: The locked country. One country, pinned.
LOCKED_COUNTRY_CODE = "IRN"

#: Explicitly forbidden substitutions, kept here so the refusal is legible in
#: the module that would otherwise be the one to fetch them.
FORBIDDEN_SUBSTITUTIONS: tuple[str, ...] = (
    "PA.NUS.ATLS",
    "FP.CPI.TOTL",
    "NY.GDP.DEFL.KD.ZG",
    "FR.INR.LEND",
    "FR.INR.DPST",
)

USER_AGENT = (
    "papermali-research/stage128-m3-lag-wdi-exploratory-data-retrieval "
    "(academic credit-risk research; contact via repository abtinasg/papermali)"
)

REQUEST_TIMEOUT_SECONDS = 60
MAX_ATTEMPTS_PER_REQUEST = 3
BACKOFF_BASE_SECONDS = 2.0
MAX_BACKOFF_SECONDS = 30.0

#: Annual WDI series for one country are far shorter than this; a single page
#: keeps the session at one request per indicator and avoids pagination logic
#: that would need to read the payload to know it had finished.
PER_PAGE = 20000

#: The exact shape of a permitted request path.
_PERMITTED_PATH = re.compile(
    r"^/v2/country/(?P<country>[A-Z]{3})/indicator/(?P<indicator>[A-Z0-9.]+)$")


class RetrievalCaptureError(RuntimeError):
    """Fail-closed error inside the retrieval capture layer."""


def build_target_url(indicator_code: str, country_code: str) -> str:
    """Build the ONE permitted official WDI API URL for a locked indicator.

    This is the only URL constructor in the action. It refuses any indicator
    outside :data:`LOCKED_INDICATOR_CODES` and any country outside
    :data:`LOCKED_COUNTRY_CODE`, so an alternative series cannot be requested
    even by a caller that wants to.
    """
    if indicator_code not in LOCKED_INDICATOR_CODES:
        raise RetrievalCaptureError(
            "STOP_INDICATOR_NOT_IN_LOCKED_CONTRACT: "
            f"{indicator_code!r} is not one of {list(LOCKED_INDICATOR_CODES)}; "
            "no substitution, proxy or alternative series is permitted")
    if country_code != LOCKED_COUNTRY_CODE:
        raise RetrievalCaptureError(
            "STOP_COUNTRY_NOT_IN_LOCKED_CONTRACT: "
            f"{country_code!r} != {LOCKED_COUNTRY_CODE!r}")
    return (
        f"https://{OFFICIAL_WDI_API_HOST}/v2/country/{country_code}"
        f"/indicator/{indicator_code}?format=json&per_page={PER_PAGE}")


def is_official_wdi_url(url: str) -> bool:
    """True only for an official World Bank WDI API URL inside the lock."""
    parts = urlsplit(url)
    if parts.scheme.lower() != "https":
        return False
    if (parts.hostname or "").lower() != OFFICIAL_WDI_API_HOST:
        return False
    match = _PERMITTED_PATH.match(parts.path)
    if not match:
        return False
    return (match.group("indicator") in LOCKED_INDICATOR_CODES
            and match.group("country") == LOCKED_COUNTRY_CODE)


def assert_official_wdi_url(url: str) -> None:
    """Fail closed unless ``url`` is inside the locked retrieval surface."""
    if not url.lower().startswith("https://"):
        raise RetrievalCaptureError(f"HTTPS is required; refusing {url!r}")
    host = (urlsplit(url).hostname or "").lower()
    if host != OFFICIAL_WDI_API_HOST:
        raise RetrievalCaptureError(
            "STOP_NON_OFFICIAL_HOST: only "
            f"{OFFICIAL_WDI_API_HOST} may be contacted; got {host!r}")
    if not is_official_wdi_url(url):
        raise RetrievalCaptureError(
            "STOP_URL_OUTSIDE_LOCKED_RETRIEVAL_SURFACE: "
            f"{url!r} does not request a locked indicator for "
            f"{LOCKED_COUNTRY_CODE}")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class _RecordingRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Records every hop and fails closed if a hop leaves the locked surface."""

    def __init__(self) -> None:
        self.chain: list[dict[str, Any]] = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        self.chain.append({
            "from_url": req.full_url, "status": code, "to_url": newurl})
        if (urlsplit(newurl).hostname or "").lower() != OFFICIAL_WDI_API_HOST:
            raise RetrievalCaptureError(
                "STOP_REDIRECTED_OFF_THE_OFFICIAL_WDI_API_HOST: "
                f"{req.full_url!r} -> {newurl!r}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_once(url: str) -> dict[str, Any]:
    """One HTTPS attempt. Returns a record; never raises for an HTTP error.

    The body is carried as raw bytes and hashed. It is never decoded, parsed or
    inspected here — that would cross into the separately authorized
    post-retrieval audit.
    """
    assert_official_wdi_url(url)
    redirects = _RecordingRedirectHandler()
    opener = urllib.request.build_opener(
        redirects,
        urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    request = urllib.request.Request(url, headers=headers)

    started = _utc_now()
    monotonic = time.monotonic()
    record: dict[str, Any] = {
        "request_url": url,
        "request_method": "GET",
        "request_headers": dict(headers),
        "started_utc": started,
    }
    try:
        with opener.open(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            body = response.read()
            record.update({
                "status_code": response.status,
                "final_url": response.url,
                "response_headers": dict(response.headers.items()),
                "body": body,
                "capture_result": "SUCCESS",
                "error_text": None,
            })
    except urllib.error.HTTPError as exc:                      # HTTP 4xx / 5xx
        body = b""
        try:
            body = exc.read()
        except Exception:                                       # noqa: BLE001
            pass
        record.update({
            "status_code": exc.code,
            "final_url": getattr(exc, "url", url),
            "response_headers": dict(exc.headers.items()) if exc.headers else {},
            "body": body,
            "capture_result": "HTTP_ERROR",
            "error_text": f"{type(exc).__name__}: {exc}",
        })
    except Exception as exc:                                    # noqa: BLE001
        # Transport failure: DNS, TLS, timeout, refused, blocked egress. The
        # traceback IS the evidence — it is retained, never swallowed.
        record.update({
            "status_code": None,
            "final_url": None,
            "response_headers": {},
            "body": b"",
            "capture_result": "TRANSPORT_ERROR",
            "error_text": f"{type(exc).__name__}: {exc}",
            "traceback_text": traceback.format_exc(),
        })

    record["ended_utc"] = _utc_now()
    record["elapsed_seconds"] = round(time.monotonic() - monotonic, 3)
    record["redirect_chain"] = list(redirects.chain)
    record["byte_length"] = len(record["body"])
    record["sha256"] = hashlib.sha256(record["body"]).hexdigest()
    return record


def fetch_with_retries(url: str) -> list[dict[str, Any]]:
    """At most ``MAX_ATTEMPTS_PER_REQUEST`` attempts, deterministic backoff.

    Every attempt is returned, including failures — an audit needs to see that
    three attempts were made, not just the last outcome. Retrying the SAME
    locked URL is not an indicator search.
    """
    attempts: list[dict[str, Any]] = []
    for attempt in range(1, MAX_ATTEMPTS_PER_REQUEST + 1):
        record = fetch_once(url)
        record["attempt_number"] = attempt
        attempts.append(record)
        if record["capture_result"] == "SUCCESS":
            break
        status = record.get("status_code")
        if status is not None and 400 <= status < 500 and status != 429:
            break                       # a definite answer; retrying is noise
        if attempt < MAX_ATTEMPTS_PER_REQUEST:
            delay = min(BACKOFF_BASE_SECONDS ** attempt, MAX_BACKOFF_SECONDS)
            retry_after = (record.get("response_headers") or {}).get(
                "Retry-After")
            if retry_after:
                try:
                    delay = max(delay,
                                min(float(retry_after), MAX_BACKOFF_SECONDS))
                except (TypeError, ValueError):
                    pass
            time.sleep(delay)
    return attempts


def _raw_filename(indicator_code: str, sha256: str, attempt: int) -> str:
    safe = "".join(c if (c.isalnum() or c in "._-") else "_"
                   for c in indicator_code)
    return f"{sha256[:16]}__{safe}.attempt{attempt}.json"


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def retrieve_locked_indicators(
    output_dir: str | os.PathLike[str],
) -> dict[str, Any]:
    """Run THE one authorized retrieval session and retain every byte.

    Targets are generated from the pinned constants only — the caller cannot
    supply a target list, so there is no seam through which a third indicator
    could enter. Raw bytes are written to ``output_dir``, which is expected to
    be OUTSIDE the repository.
    """
    out = Path(output_dir)
    raw_dir = out / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    requests_manifest: list[dict[str, Any]] = []
    responses_manifest: list[dict[str, Any]] = []
    session_started = _utc_now()
    succeeded = 0
    failed = 0
    raw_bytes_retained = 0
    http_requests = 0

    for indicator_code in LOCKED_INDICATOR_CODES:
        url = build_target_url(indicator_code, LOCKED_COUNTRY_CODE)
        attempts = fetch_with_retries(url)
        for record in attempts:
            http_requests += 1
            body = record.pop("body")
            # Retain bytes for EVERY attempt, including empty error bodies, so
            # a claim of retrieval is always backed by a file on disk.
            filename = _raw_filename(
                indicator_code, record["sha256"], record["attempt_number"])
            (raw_dir / filename).write_bytes(body)
            raw_bytes_retained += len(body)

            requests_manifest.append({
                "indicator_code": indicator_code,
                "country_code": LOCKED_COUNTRY_CODE,
                "request_url": record["request_url"],
                "request_method": record["request_method"],
                "request_headers_json": json.dumps(
                    record["request_headers"], ensure_ascii=False,
                    sort_keys=True),
                "attempt_number": record["attempt_number"],
                "started_utc": record["started_utc"],
                "ended_utc": record["ended_utc"],
                "elapsed_seconds": record["elapsed_seconds"],
            })
            responses_manifest.append({
                "indicator_code": indicator_code,
                "country_code": LOCKED_COUNTRY_CODE,
                "request_url": record["request_url"],
                "attempt_number": record["attempt_number"],
                "capture_result": record["capture_result"],
                "status_code": record["status_code"],
                "final_url": record["final_url"],
                "raw_body_filename": filename,
                "byte_length": record["byte_length"],
                "sha256": record["sha256"],
                "content_type": (record["response_headers"] or {}).get(
                    "Content-Type", ""),
                "response_headers_json": json.dumps(
                    record["response_headers"], ensure_ascii=False,
                    sort_keys=True),
                "redirect_chain_json": json.dumps(
                    record["redirect_chain"], ensure_ascii=False),
                "retrieval_timestamp_utc": record["ended_utc"],
                "error_text": record["error_text"] or "",
            })
        if attempts and attempts[-1]["capture_result"] == "SUCCESS":
            succeeded += 1
        else:
            failed += 1

    _write_csv(out / "wdi_request_manifest.csv", requests_manifest)
    _write_csv(out / "wdi_response_manifest.csv", responses_manifest)

    session = {
        "action_id": ACTION_ID,
        "authorized_scope": "retrieval_only",
        "session_started_utc": session_started,
        "session_ended_utc": _utc_now(),
        "session_closed": True,
        "locked_indicator_codes": list(LOCKED_INDICATOR_CODES),
        "country_code": LOCKED_COUNTRY_CODE,
        "indicators_requested": len(LOCKED_INDICATOR_CODES),
        "indicators_succeeded": succeeded,
        "indicators_failed": failed,
        "http_requests_made": http_requests,
        "http_responses_recorded": len(responses_manifest),
        "raw_artifacts_retained": len(responses_manifest),
        "raw_bytes_retained": raw_bytes_retained,
        # Everything downstream of acquisition stayed untouched.
        "payload_json_decoded": False,
        "wdi_values_inspected": 0,
        "coverage_calculations": 0,
        "data_gate_executions": 0,
        "company_row_joins": 0,
        "feature_materializations": 0,
        "model_fits": 0,
        "final_test_rows_read": 0,
    }
    (out / "retrieval_session_manifest.json").write_text(
        json.dumps(session, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    return session
