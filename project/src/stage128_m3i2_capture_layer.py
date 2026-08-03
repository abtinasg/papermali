"""Stage128 M3I-2 — the ONLY module permitted to open a network connection.

Isolation is the point. Every other module in this action (the offline builder,
the validators, the QC and the whole test suite) is scanned and must contain no
network import and no reachable network call. Keeping the socket in exactly one
small, auditable file is what makes that scan meaningful.

What this layer does
--------------------
Performs one authorized capture session against the official World Bank and IMF
hosts, and writes to an EXTERNAL capture directory:

* the raw response body bytes of every object, success or failure;
* a request manifest and a response manifest;
* the redirect chain and response headers of every attempt;
* stderr / exception text for every failure.

What it never does
------------------
It does not parse observations, join anything to a company row, compute a
feature, a coverage number or a Gate result. It fetches bytes and records what
happened. Interpretation happens offline, from the retained bytes.

Retention rule
--------------
Raw bytes are never deleted here, and a failure is never converted into a
missing file. An unreachable source is recorded WITH its error bytes so that a
later reader can tell "we could not reach it" apart from "it does not exist".
"""

from __future__ import annotations

import hashlib
import json
import os
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
# Official-host allowlist (section 6)
# --------------------------------------------------------------------------- #

#: Hosts that may terminate a request. A wildcard is NOT blanket permission:
#: every download must also be reachable from an official discovery root, and
#: the discovery/redirect chain is preserved as proof.
OFFICIAL_HOST_SUFFIXES: tuple[str, ...] = (
    "worldbank.org",
    "imf.org",
)

OFFICIAL_HOSTS_EXPLICIT: tuple[str, ...] = (
    "datatopics.worldbank.org",
    "databank.worldbank.org",
    "databankfiles.worldbank.org",
    "api.worldbank.org",
    "data.imf.org",
    "www.imf.org",
    "imf.org",
)

USER_AGENT = (
    "papermali-research/stage128-m3i2-official-source-evidence-capture "
    "(academic credit-risk research; contact via repository abtinasg/papermali)"
)

REQUEST_TIMEOUT_SECONDS = 60
MAX_ATTEMPTS_PER_REQUEST = 3
BACKOFF_BASE_SECONDS = 2.0
MAX_BACKOFF_SECONDS = 30.0


class CaptureError(RuntimeError):
    """Fail-closed error inside the capture layer."""


def is_official_host(url: str) -> bool:
    """True only for an official World Bank / IMF host."""
    host = (urlsplit(url).hostname or "").lower()
    if not host:
        return False
    if host in OFFICIAL_HOSTS_EXPLICIT:
        return True
    return any(host == s or host.endswith("." + s)
               for s in OFFICIAL_HOST_SUFFIXES)


def assert_official_url(url: str) -> None:
    if not url.lower().startswith("https://"):
        raise CaptureError(f"HTTPS is required; refusing {url!r}")
    if not is_official_host(url):
        raise CaptureError(
            f"STOP_OFFICIAL_SOURCE_REDIRECTED_TO_NON_OFFICIAL_HOST: {url!r}")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class _RecordingRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Records every hop and fails closed if a hop leaves an official host."""

    def __init__(self) -> None:
        self.chain: list[dict[str, Any]] = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        self.chain.append({
            "from_url": req.full_url, "status": code, "to_url": newurl})
        if not is_official_host(newurl):
            raise CaptureError(
                "STOP_OFFICIAL_SOURCE_REDIRECTED_TO_NON_OFFICIAL_HOST: "
                f"{req.full_url!r} -> {newurl!r}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_once(url: str, accept: str = "*/*") -> dict[str, Any]:
    """One HTTPS attempt. Returns a record; never raises for an HTTP error."""
    assert_official_url(url)
    redirects = _RecordingRedirectHandler()
    opener = urllib.request.build_opener(
        redirects, urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": accept})

    started = _utc_now()
    monotonic = time.monotonic()
    record: dict[str, Any] = {
        "request_url": url,
        "request_method": "GET",
        "request_headers": {"User-Agent": USER_AGENT, "Accept": accept},
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


def fetch_with_retries(url: str, accept: str = "*/*") -> list[dict[str, Any]]:
    """At most ``MAX_ATTEMPTS_PER_REQUEST`` attempts, deterministic backoff.

    Every attempt is returned, including the failures — an audit needs to see
    that three attempts were made, not just the last outcome.
    """
    attempts: list[dict[str, Any]] = []
    for attempt in range(1, MAX_ATTEMPTS_PER_REQUEST + 1):
        record = fetch_once(url, accept=accept)
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
                    delay = max(delay, min(float(retry_after),
                                           MAX_BACKOFF_SECONDS))
                except (TypeError, ValueError):
                    pass
            time.sleep(delay)
    return attempts


def _safe_name(url: str, sha256: str) -> str:
    tail = urlsplit(url).path.rsplit("/", 1)[-1] or "index"
    tail = "".join(c if (c.isalnum() or c in "._-") else "_" for c in tail)
    return f"{sha256[:16]}__{tail[:80]}"


def capture_objects(
    targets: list[dict[str, str]], output_dir: str | os.PathLike[str],
    append: bool = False,
) -> dict[str, Any]:
    """Run ONE capture session over ``targets`` and retain every byte.

    ``targets`` entries: ``{"object_id", "url", "role", "accept"}``.

    With ``append=True`` the rows are added to the manifests already in
    ``output_dir`` rather than replacing them. That is how phase 2 (the
    required-edition downloads, whose URLs are only knowable after the phase-1
    listing has been captured) completes the same session without discarding
    any phase-1 evidence.
    """
    out = Path(output_dir)
    raw_dir = out / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    requests_manifest: list[dict[str, Any]] = []
    responses_manifest: list[dict[str, Any]] = []
    session_started = _utc_now()
    prior_invocations = 0
    if append:
        requests_manifest = _read_csv(out / "official_request_manifest.csv")
        responses_manifest = _read_csv(out / "official_response_manifest.csv")
        prior = out / "capture_session_manifest.json"
        if prior.is_file():
            previous = json.loads(prior.read_text(encoding="utf-8"))
            prior_invocations = int(previous.get("capture_invocations", 1))
            session_started = previous.get("session_started_utc",
                                           session_started)

    for target in targets:
        url = target["url"]
        object_id = target["object_id"]
        try:
            assert_official_url(url)
        except CaptureError as exc:
            requests_manifest.append({
                "object_id": object_id, "request_url": url,
                "role": target.get("role", ""),
                "attempts": 0, "rejected_before_request": str(exc)})
            continue

        attempts = fetch_with_retries(url, accept=target.get("accept", "*/*"))
        for record in attempts:
            body = record.pop("body")
            filename = ""
            # Retain bytes for EVERY attempt, including empty error bodies, so
            # a claim of capture is always backed by a file on disk.
            filename = _safe_name(url, record["sha256"]) + (
                f".attempt{record['attempt_number']}")
            (raw_dir / filename).write_bytes(body)

            requests_manifest.append({
                "object_id": object_id,
                "role": target.get("role", ""),
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
                "object_id": object_id,
                "role": target.get("role", ""),
                "request_url": record["request_url"],
                "attempt_number": record["attempt_number"],
                "status_code": record["status_code"],
                "final_url": record["final_url"],
                "redirect_chain_json": json.dumps(
                    record["redirect_chain"], ensure_ascii=False),
                "response_headers_json": json.dumps(
                    record["response_headers"], ensure_ascii=False,
                    sort_keys=True),
                "content_type": (record["response_headers"] or {}).get(
                    "Content-Type", ""),
                "content_encoding": (record["response_headers"] or {}).get(
                    "Content-Encoding", ""),
                "byte_length": record["byte_length"],
                "sha256": record["sha256"],
                "raw_body_filename": filename,
                "capture_result": record["capture_result"],
                "error_text": record["error_text"] or "",
                "retrieval_timestamp_utc": record["ended_utc"],
            })

    session = {
        "capture_session_id":
            "stage128-m3i2-official-source-evidence-capture-session-1",
        "session_started_utc": session_started,
        "session_ended_utc": _utc_now(),
        "session_closed": True,
        "capture_invocations": prior_invocations + 1,
        "phase_2_appended_required_edition_downloads": bool(append),
        "targets_requested": len(targets),
        "requests_recorded": len(requests_manifest),
        "responses_recorded": len(responses_manifest),
        "objects_succeeded": sorted({
            r["object_id"] for r in responses_manifest
            if r["capture_result"] == "SUCCESS"}),
        "objects_failed": sorted({
            r["object_id"] for r in responses_manifest
            if r["capture_result"] != "SUCCESS"}
            - {r["object_id"] for r in responses_manifest
               if r["capture_result"] == "SUCCESS"}),
        "raw_bytes_retained": True,
        "raw_bytes_deleted_after_hashing": False,
        "user_agent": USER_AGENT,
        "https_only": True,
        "max_attempts_per_request": MAX_ATTEMPTS_PER_REQUEST,
        "timeout_seconds": REQUEST_TIMEOUT_SECONDS,
        "official_host_suffixes": list(OFFICIAL_HOST_SUFFIXES),
    }

    (out / "capture_session_manifest.json").write_text(
        json.dumps(session, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n", encoding="utf-8")
    _write_csv(out / "official_request_manifest.csv", requests_manifest)
    _write_csv(out / "official_response_manifest.csv", responses_manifest)
    return session


def _read_csv(path: Path) -> list[dict[str, Any]]:
    import csv

    if not path.is_file() or not path.read_text(encoding="utf-8").strip():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    import csv

    if not rows:
        path.write_text("", encoding="utf-8")
        return
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, lineterminator="\n",
                                extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ("" if row.get(k) is None else row.get(k))
                             for k in columns})
