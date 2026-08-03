"""Stage128 — M3I-2 final official documentary recovery initiation.

Bounded, fail-closed capture layer for ONE narrowly scoped action:

* a bounded documentary search over OFFICIAL World Bank Group hosts only
  (at most ``MAX_DOCUMENTARY_GET_REQUESTS`` GET requests);
* preparation of exactly one official inquiry to the World Bank Data Help
  Desk, with two public, non-sensitive attachments;
* at most ONE initial inquiry submission attempt.

What this module must NEVER do, by construction:

* re-download any URL already captured by
  ``stage128-m3i2-official-source-evidence-capture`` (duplicate guard);
* download any WDI archive ZIP (blanket ban, independent of the duplicate
  guard);
* join company rows to macro rows, materialize a feature, compute coverage,
  execute a Data Gate, fit a model, predict, or touch the Final Test;
* accept a filename/URL date token as release evidence;
* invent a ticket id, bypass a CAPTCHA or use a credential.

Availability rules A-E are locked prospectively here so that a later action
cannot loosen them retroactively.
"""

from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
import urllib.error
import urllib.request

ACTION_ID = "stage128-m3i2-final-official-documentary-recovery-initiation"
PACKAGE_ID = "stage128_m3i2_final_official_documentary_recovery"
PACKAGE_DIRNAME = "m3i2_final_official_documentary_recovery"
PACKAGE_REL = f"project/stage128/{PACKAGE_DIRNAME}"
RAW_REL = f"{PACKAGE_REL}/raw_official_documents"

BASELINE_BRANCH = "main"
BASELINE_COMMIT = "b3627809dbfde8429d0308bec5d1c8541a161188"
PREDECESSOR_PR_NUMBER = 75
PREDECESSOR_ACTION_ID = "stage128-m3i2-official-source-evidence-capture"

#: Hard ceiling on official documentary GET requests. The support-form
#: submission attempt is NOT counted against this ceiling.
MAX_DOCUMENTARY_GET_REQUESTS = 20
#: Exactly one initial inquiry may ever be attempted by this action.
INITIAL_INQUIRY_MAX_COUNT = 1
FOLLOW_UP_MAX_COUNT = 1
WAITING_PERIOD_BUSINESS_DAYS = 10

#: Evidence may be taken ONLY from these official World Bank Group hosts.
OFFICIAL_HOSTS = (
    "worldbank.org",
    "www.worldbank.org",
    "data.worldbank.org",
    "databank.worldbank.org",
    "datatopics.worldbank.org",
    "datahelpdesk.worldbank.org",
    "documents.worldbank.org",
    "openknowledge.worldbank.org",
)

USER_AGENT = (
    "papermali-research/stage128-m3i2-final-official-documentary-recovery "
    "(academic credit-risk research; contact via repository abtinasg/papermali)"
)

#: Request manifest of the PRIOR capture action. Every URL in it is already
#: retained; requesting it again is forbidden.
PRIOR_REQUEST_MANIFEST_REL = (
    "project/stage128/m3i2_official_source_evidence_capture/"
    "stage128_m3i2_official_request_manifest.csv")


class RecoveryError(RuntimeError):
    """Fail-closed error in the documentary-recovery capture layer."""


def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def repo_root() -> str:
    return subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True).stdout.strip()


def _host(url: str) -> str:
    return urllib.request.urlparse(url).hostname or ""


def is_official_host(url: str) -> bool:
    """Exact allow-list match only.

    Deliberately strict: a suffix rule would admit hosts such as
    ``evil-worldbank.org`` or unlisted subdomains (for example the data API),
    and the allow-list in the action contract is exhaustive.
    """
    host = _host(url).lower()
    return host in OFFICIAL_HOSTS


def is_archive_zip(url: str) -> bool:
    """Any WDI archive ZIP, by extension or by the archive download path."""
    lowered = url.lower()
    return lowered.endswith(".zip") or "/data/download/archive/" in lowered


def prior_captured_urls(root: str) -> set[str]:
    path = os.path.join(root, PRIOR_REQUEST_MANIFEST_REL)
    if not os.path.isfile(path):
        raise RecoveryError(
            "the prior capture request manifest is required for the "
            "duplicate guard and is missing")
    with open(path, encoding="utf-8") as fh:
        return {row["request_url"].strip()
                for row in csv.DictReader(fh) if row.get("request_url")}


def guard_request(url: str, root: str, log: list[dict]) -> None:
    """Fail-closed pre-flight checks. Raises before any byte is requested."""
    if not url.startswith("https://"):
        raise RecoveryError(f"non-https request refused: {url}")
    if not is_official_host(url):
        raise RecoveryError(f"non-official host refused: {url}")
    if is_archive_zip(url):
        raise RecoveryError(
            f"archive ZIP download is forbidden in this action: {url}")
    if url in prior_captured_urls(root):
        raise RecoveryError(
            "duplicate of a prior captured URL; reuse the retained artifact "
            f"instead: {url}")
    if any(entry["request_url"] == url for entry in log):
        raise RecoveryError(f"duplicate request within this action: {url}")
    executed = len(log)
    if executed >= MAX_DOCUMENTARY_GET_REQUESTS:
        raise RecoveryError(
            "the bounded documentary search ceiling "
            f"({MAX_DOCUMENTARY_GET_REQUESTS}) is exhausted")


def capture(url: str, object_id: str, purpose: str, root: str,
            log_path: str) -> dict:
    """Execute ONE guarded official GET and retain its raw bytes."""
    log = read_log(log_path)
    guard_request(url, root, log)

    started = _utc_now()
    redirects: list[str] = []

    class _Redirects(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            redirects.append(newurl)
            if not is_official_host(newurl):
                raise RecoveryError(
                    f"redirect left the World Bank Group: {newurl}")
            if is_archive_zip(newurl):
                raise RecoveryError(f"redirect to an archive ZIP: {newurl}")
            return super().redirect_request(
                req, fp, code, msg, headers, newurl)

    opener = urllib.request.build_opener(_Redirects)
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/pdf,*/*",
    })
    status: int | None = None
    body = b""
    error = None
    try:
        with opener.open(request, timeout=45) as response:
            status = response.status
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type", "")
            body = response.read()
    except urllib.error.HTTPError as exc:            # official 4xx/5xx answer
        status, final_url = exc.code, url
        content_type = exc.headers.get("Content-Type", "") if exc.headers else ""
        body = exc.read() or b""
        error = f"HTTPError {exc.code}"
    except Exception as exc:                          # noqa: BLE001 - recorded
        final_url, content_type = url, ""
        error = f"{type(exc).__name__}: {exc}"

    digest = sha256_bytes(body) if body else None
    raw_rel = None
    if body:
        raw_dir = os.path.join(root, RAW_REL)
        os.makedirs(raw_dir, exist_ok=True)
        suffix = ".pdf" if "pdf" in content_type.lower() else ".html"
        raw_rel = f"{RAW_REL}/{object_id}{suffix}"
        with open(os.path.join(root, raw_rel), "wb") as fh:
            fh.write(body)

    entry = {
        "request_id": f"docget_{len(log) + 1:02d}",
        "object_id": object_id,
        "request_url": url,
        "final_url": final_url,
        "purpose": purpose,
        "request_method": "GET",
        "started_utc": started,
        "ended_utc": _utc_now(),
        "http_status": status,
        "error": error,
        "redirect_count": len(redirects),
        "redirect_chain": redirects,
        "content_type": content_type,
        "raw_sha256": digest,
        "retained_byte_count": len(body),
        "raw_artifact_path": raw_rel,
        "duplicate_of_prior_capture": False,
        "is_archive_zip_download": False,
        "official_host": True,
    }
    log.append(entry)
    write_log(log_path, log)
    return entry


def read_log(log_path: str) -> list[dict]:
    if not os.path.isfile(log_path):
        return []
    with open(log_path, encoding="utf-8") as fh:
        return json.load(fh)


def write_log(log_path: str, log: list[dict]) -> None:
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")


# --------------------------------------------------------------------------- #
# Availability rules A-E (locked prospectively)
# --------------------------------------------------------------------------- #

AVAILABILITY_RULES = {
    "A_official_exact_timestamp": (
        "available_at = the official timestamp normalized to UTC"),
    "B_official_full_date_without_time": (
        "available_at = the NEXT calendar day at 00:00:00 UTC"),
    "C_official_month_and_year_only": (
        "available_at = the FIRST day of the NEXT month at 00:00:00 UTC"),
    "D_filename_or_url_token_only": (
        "available_at = null and release_date_verified = false"),
    "E_no_unproven_previous_month_fallback": (
        "a previous-month fallback without official month confirmation is "
        "forbidden"),
}

NON_EVIDENCE_SIGNALS = (
    "filename_token",
    "url_token",
    "retrieval_timestamp",
    "http_last_modified",
    "zip_member_timestamp",
    "workbook_properties",
    "local_file_mtime",
    "workbook_year_columns",
    "cache_date",
    "search_engine_snippet",
)


def resolve_available_at(official_timestamp_utc: str | None = None,
                         official_full_date: str | None = None,
                         official_month: str | None = None,
                         filename_token_only: bool = False) -> dict:
    """Apply the locked availability rules A-E. Fail-closed to null."""
    if official_timestamp_utc:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
                            official_timestamp_utc):
            raise RecoveryError(
                "rule A requires an ISO-8601 UTC timestamp")
        return {"available_at": official_timestamp_utc,
                "release_date_verified": True, "rule_applied": "A"}
    if official_full_date:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", official_full_date):
            raise RecoveryError("rule B requires YYYY-MM-DD")
        day = _dt.date.fromisoformat(official_full_date) + _dt.timedelta(days=1)
        return {"available_at": f"{day.isoformat()}T00:00:00Z",
                "release_date_verified": True, "rule_applied": "B"}
    if official_month:
        if not re.fullmatch(r"\d{4}-\d{2}", official_month):
            raise RecoveryError("rule C requires YYYY-MM")
        year, month = (int(part) for part in official_month.split("-"))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
        return {"available_at": f"{year:04d}-{month:02d}-01T00:00:00Z",
                "release_date_verified": True, "rule_applied": "C"}
    # D / E: a filename or URL token is NEVER release evidence.
    return {"available_at": None, "release_date_verified": False,
            "rule_applied": "D" if filename_token_only else "D_no_evidence"}


# --------------------------------------------------------------------------- #
# Read-only carry-over of the PRIOR capture findings (never re-executed)
# --------------------------------------------------------------------------- #

PRIOR_FINDINGS = {
    "unique_development_cutoffs": 37,
    "development_parent_rows": 539,
    "archive_editions_discovered": 110,
    "archive_editions_already_captured": 16,
    "official_requests_already_completed": 21,
    "successful_responses_already_retained": 21,
    "locked_iran_series_rows_already_extracted": 1878,
    "editions_with_verified_release_date": 0,
    "editions_total_for_release_date_verification": 110,
    "cutoffs_with_verified_pre_cutoff_edition": 0,
    "unique_cutoffs_total": 37,
    "unresolved_cutoffs": 37,
    "unresolved_development_pairs": 539,
    "cpi_semantic_pass_count": 16,
    "fx_semantic_unresolved_count": 16,
}


def verify_prior_findings(root: str) -> dict:
    """Read-only, fail-closed re-read of the merged PR #75 handoff state."""
    path = os.path.join(root, "project/docs/ai/handoff_state.json")
    with open(path, encoding="utf-8") as fh:
        state = json.load(fh)
    expected = {
        "stage128_m3i2_unique_development_cutoffs": 37,
        "stage128_m3i2_development_pairs_behind_cutoff_plan": 539,
        "stage128_m3i2_wdi_editions_discovered": 110,
        "stage128_m3i2_archive_editions_captured": 16,
        "stage128_m3i2_official_requests_attempted": 21,
        "stage128_m3i2_official_responses_successful": 21,
        "stage128_m3i2_official_responses_retained": 21,
        "stage128_m3i2_locked_series_rows_extracted": 1878,
        "stage128_m3i2_editions_with_verified_release_date": 0,
        "stage128_m3i2_cutoffs_without_verified_pre_cutoff_edition": 37,
        "stage128_m3i2_development_pairs_without_verified_pre_cutoff_edition":
            539,
        "stage128_m3i2_cpi_semantic_pass_count": 16,
        "stage128_m3i2_fx_semantic_unresolved_count": 16,
        "stage128_m3i2_evidence_status": "UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE",
        "m3i2_block_admitted": False,
        "m3i2_data_gate_executed": False,
        "m3i2_modeling_started": False,
        "m3_macro_data_gate_status": "UNRESOLVED_M3_DATA_GATE",
        "m3_block_admitted_for_incremental_evaluation": False,
        "m3i3_financing_lock": "UNRESOLVED_METADATA_LOCK",
        "m3i3_admitted": False,
        "m4_authorized": False,
        "final_test_locked": True,
        "stage128_m3i2_independent_bundle_integrity_audit":
            "INDEPENDENT_BUNDLE_INTEGRITY_AUDIT_PASS",
        "stage128_m3i2_live_pr_number": PREDECESSOR_PR_NUMBER,
    }
    for key, want in expected.items():
        if state.get(key) != want:
            raise RecoveryError(
                f"merged baseline mismatch: {key}={state.get(key)!r} "
                f"!= {want!r}")
    return state
