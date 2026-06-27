"""Stage124 Batch 2 — Part 3: research screening for the next 10 tickers.

Scope: ONLY the 10 tickers listed in ``PART03_TICKERS``. No ticker from Part 2
or Pilot15 is re-researched. This stage performs research *screening* only:

* No eligibility / ranking change.
* No verified master is produced.
* No Gate B, no modelling.
* No live TSETMC probe — historical TSETMC results are read from the frozen
  V2 audit (``listing_batch02_tsetmc_conflict_audit_v2.csv``) only.

Canonical public-entry dates may only come from ``first_public_offering`` or
``first_public_trading`` with an exact day backed by *fetched* evidence. No date
is guessed. Failed fetches never produce a fabricated snapshot or hash.
"""

import re
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests as _requests

from .stage124_batch02_v2 import (
    normalize_ticker, normalize_jalali, jalali_to_gregorian_str,
    jalali_str_to_gregorian_date, gregorian_to_jalali_str,
    sha, git_head, read_csv, write_csv,
    ROOT, OUT, PILOT15, STAGE123_INPUT, STAGE122_INPUT,
    EXPECTED_STAGE123_SHA, EXPECTED_STAGE122_SHA,
)
from .stage124_batch02_part02 import PART02_TICKERS, PARTIAL_MASTER

PART03_DIR = ROOT / "stage124" / "batch02_parts"
SNAPSHOT_DIR = PART03_DIR / "snapshots_part03"

# Frozen V2 TSETMC audit (read-only source of historical TSETMC results).
FROZEN_V2_TSETMC_AUDIT = OUT / "listing_batch02_tsetmc_conflict_audit_v2.csv"

# Exact ordered scope for Part 3.
PART03_TICKERS = [
    "خمهر", "خنصیر", "خوساز", "خچرخش", "خکمک",
    "دروز", "دسبحا", "دیران", "رانفور", "رمپنا",
]

# Canonical events: only these two may ever be canonical.
CANONICAL_EVENT_TYPES = {"first_public_offering", "first_public_trading"}

# Non-canonical-on-their-own events (recorded but never auto-canonical).
NON_CANONICAL_EVENTS = {
    "incorporation", "conversion_to_public", "admission", "listing",
    "registration", "market_transfer", "symbol_reopen", "symbol_change",
    "rights_offering", "oldest_tsetmc_record_without_ordinary_instrument",
}

FULL_VERIFIED_FORBIDDEN = OUT / "listing_master_verified_stage124.csv"

# Candidate research sources per ticker. Each entry: (source_type, title, url).
# These are the URLs to *attempt* (sequential, timeout=5s, retry=0, max 3).
# Taxonomy: only the genuine codal.ir domain is ``codal_official``; Tacodal and
# other aggregators are ``market_information_aggregator``.
RESEARCH_SOURCES = {
    "خمهر": [
        ["market_information_aggregator", "مهرکام پارس - رهاورد 365",
         "https://rahavard365.com/asset/jdax/%D8%AE%D9%85%D9%87%D8%B1"],
        ["codal_official", "جستجوی اطلاعیه‌های خمهر - کدال",
         "https://www.codal.ir/ReportList.aspx?search&Symbol=%D8%AE%D9%85%D9%87%D8%B1"],
    ],
    "خنصیر": [
        ["market_information_aggregator", "مهندسی نصیر ماشین - رهاورد 365",
         "https://rahavard365.com/asset/%D8%AE%D9%86%D8%B5%DB%8C%D8%B1"],
        ["codal_official", "جستجوی اطلاعیه‌های خنصیر - کدال",
         "https://www.codal.ir/ReportList.aspx?search&Symbol=%D8%AE%D9%86%D8%B5%DB%8C%D8%B1"],
    ],
    "خوساز": [
        ["market_information_aggregator", "محورسازان ایران خودرو - رهاورد 365",
         "https://rahavard365.com/asset/%D8%AE%D9%88%D8%B3%D8%A7%D8%B2"],
        ["codal_official", "جستجوی اطلاعیه‌های خوساز - کدال",
         "https://www.codal.ir/ReportList.aspx?search&Symbol=%D8%AE%D9%88%D8%B3%D8%A7%D8%B2"],
    ],
    "خچرخش": [
        ["market_information_aggregator", "چرخشگر - رهاورد 365",
         "https://rahavard365.com/asset/%D8%AE%DA%86%D8%B1%D8%AE%D8%B4"],
        ["codal_official", "جستجوی اطلاعیه‌های خچرخش - کدال",
         "https://www.codal.ir/ReportList.aspx?search&Symbol=%D8%AE%DA%86%D8%B1%D8%AE%D8%B4"],
    ],
    "خکمک": [
        ["market_information_aggregator", "کمک فنر ایندامین - رهاورد 365",
         "https://rahavard365.com/asset/%D8%AE%DA%A9%D9%85%DA%A9"],
        ["codal_official", "جستجوی اطلاعیه‌های خکمک - کدال",
         "https://www.codal.ir/ReportList.aspx?search&Symbol=%D8%AE%DA%A9%D9%85%DA%A9"],
    ],
    "دروز": [
        ["market_information_aggregator", "روز دارو - رهاورد 365",
         "https://rahavard365.com/asset/%D8%AF%D8%B1%D9%88%D8%B2"],
        ["codal_official", "جستجوی اطلاعیه‌های دروز - کدال",
         "https://www.codal.ir/ReportList.aspx?search&Symbol=%D8%AF%D8%B1%D9%88%D8%B2"],
    ],
    "دسبحا": [
        ["market_information_aggregator", "گروه دارویی سبحان - رهاورد 365",
         "https://rahavard365.com/asset/%D8%AF%D8%B3%D8%A8%D8%AD%D8%A7"],
        ["codal_official", "جستجوی اطلاعیه‌های دسبحا - کدال",
         "https://www.codal.ir/ReportList.aspx?search&Symbol=%D8%AF%D8%B3%D8%A8%D8%AD%D8%A7"],
    ],
    "دیران": [
        ["market_information_aggregator", "ایران دارو - رهاورد 365",
         "https://rahavard365.com/asset/%D8%AF%DB%8C%D8%B1%D8%A7%D9%86"],
        ["codal_official", "جستجوی اطلاعیه‌های دیران - کدال",
         "https://www.codal.ir/ReportList.aspx?search&Symbol=%D8%AF%DB%8C%D8%B1%D8%A7%D9%86"],
    ],
    "رانفور": [
        ["market_information_aggregator", "خدمات انفورماتیک - رهاورد 365",
         "https://rahavard365.com/asset/%D8%B1%D8%A7%D9%86%D9%81%D9%88%D8%B1"],
        ["codal_official", "جستجوی اطلاعیه‌های رانفور - کدال",
         "https://www.codal.ir/ReportList.aspx?search&Symbol=%D8%B1%D8%A7%D9%86%D9%81%D9%88%D8%B1"],
    ],
    "رمپنا": [
        ["market_information_aggregator", "گروه مپنا - رهاورد 365",
         "https://rahavard365.com/asset/%D8%B1%D9%85%D9%BE%D9%86%D8%A7"],
        ["codal_official", "جستجوی اطلاعیه‌های رمپنا - کدال",
         "https://www.codal.ir/ReportList.aspx?search&Symbol=%D8%B1%D9%85%D9%BE%D9%86%D8%A7"],
    ],
}


# Retrieval statuses that count as a *successful* fetch.
FETCHED_STATUSES = {"fetched_ok", "reused_existing_snapshot"}

# Retrieval statuses that are pure network failures. A network failure means the
# research could not be *completed*; it never means "no reliable evidence".
NETWORK_FAILURE_STATUSES = {"timeout", "connection_error", "fetch_error"}

# Source authority taxonomy. Only the genuine codal.ir domain is the official
# regulator; reputable wire/news agencies are contemporaneous news; everything
# else (Rahavard, Tacodal, TGJU, …) is an information aggregator.
OFFICIAL_REGULATORY_DOMAINS = {
    "codal.ir", "seo.ir", "sena.ir", "ime.co.ir", "tse.ir", "tsetmc.com",
    "irbourse.com", "ifb.ir",
}
CREDIBLE_NEWS_DOMAINS = {
    "irna.ir", "isna.ir", "mehrnews.com", "donya-e-eqtesad.com",
    "eghtesadnews.com", "boursenews.ir", "sena.ir", "tasnimnews.com",
    "ilna.ir", "ecoiran.com",
}
AGGREGATOR_DOMAINS = {
    "rahavard365.com", "tacodal.ir", "tgju.org", "fipiran.com",
    "bourseview.com", "sahmeto.com", "databours.ir",
}

# Authority classes that can satisfy the source-sufficiency condition for
# ready=true. Aggregator / unknown may be *supporting* evidence but never make a
# record ready on their own (Correction 4).
QUALIFYING_AUTHORITY_CLASSES = {"official_regulatory", "credible_news", "company_official"}
# Backwards-compatible alias used by older QC references.
AUTHORITATIVE_CLASSES = QUALIFYING_AUTHORITY_CLASSES

# Declared source_type → expected authority class. A declared type must be
# corroborated by the URL's real domain or it is treated as a contradiction.
_DECLARED_CLASS = {
    "codal_official": "official_regulatory",
    "regulatory_official": "official_regulatory",
    "news_agency": "credible_news",
    "credible_news": "credible_news",
    "market_information_aggregator": "market_information_aggregator",
    "aggregator": "market_information_aggregator",
    "company_official": "company_official",
}

# Codal evidence must point at a specific, stable document/announcement.
_CODAL_DOC_IDENTIFIERS = (
    "letterserial", "tracingno", "announcementid", "attachment",
    "/decision.aspx", "/letter", "document", ".pdf",
)
# Discovery / list / search / overview markers — never document-specific.
_DISCOVERY_MARKERS = (
    "reportlist.aspx", "decisionlist", "searchresult", "/search",
    "search=", "search&", "symbol=", "/asset/", "/list",
)


# ---- helpers -------------------------------------------------------------------
def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hostname(url: str) -> str:
    """Boundary-safe hostname via urllib, lower-cased and de-www'd."""
    if not url:
        return ""
    u = str(url).strip()
    if "://" not in u:
        u = "http://" + u
    host = (urlparse(u).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _host_matches(host: str, domain: str) -> bool:
    """True only when ``host`` *is* ``domain`` or a real subdomain of it.

    ``codal.ir`` and ``www.codal.ir`` match ``codal.ir``; ``fake-codal.ir`` and
    ``codal.ir.example.com`` do not."""
    if not host or not domain:
        return False
    return host == domain or host.endswith("." + domain)


def _host_in(host: str, domains) -> bool:
    return any(_host_matches(host, d) for d in domains)


def registrable_domain(url: str) -> str:
    """Lower-cased host used as the independent source group. Two URLs on the
    same host share one group and are therefore *not* independent."""
    return _hostname(url)


def _domain_authority(host: str) -> str:
    if _host_in(host, OFFICIAL_REGULATORY_DOMAINS):
        return "official_regulatory"
    if _host_in(host, CREDIBLE_NEWS_DOMAINS):
        return "credible_news"
    if _host_in(host, AGGREGATOR_DOMAINS):
        return "market_information_aggregator"
    return "unknown"


def classify_source_authority_with_validation(source_type: str, url: str):
    """Fail-closed authority classification. The URL's real domain is the source
    of truth; a declared ``source_type`` that contradicts the domain yields an
    ``unknown`` class plus a validation error string.

    Returns ``(authority_class, validation_error)``."""
    host = _hostname(url)
    domain_class = _domain_authority(host)
    declared = _DECLARED_CLASS.get((source_type or "").strip().lower())
    if declared is None:
        # No (or unrecognised) declared type → trust the domain only.
        return domain_class, ""
    if declared == domain_class:
        return domain_class, ""
    return "unknown", (
        f"source_type '{source_type}' contradicts domain '{host or '∅'}' "
        f"(domain_class={domain_class})")


def classify_source_authority(source_type: str, url: str) -> str:
    """Domain-strict authority class (see
    :func:`classify_source_authority_with_validation`)."""
    return classify_source_authority_with_validation(source_type, url)[0]


def is_document_specific_source(url: str, source_type: str = "") -> bool:
    """A *document-specific* source is a single announcement/document with a
    stable identifier — not a discovery, search, list, or asset-overview page.

    Codal evidence is accepted only from a specific letter/announcement
    (LetterSerial / TracingNo / AnnouncementId / attachment / a PDF). Generic
    Codal ``ReportList.aspx`` / symbol-search pages, Rahavard ``/asset/``
    overviews, homepages and profiles are discovery-only."""
    if not url:
        return False
    parsed = urlparse(str(url).strip() if "://" in str(url) else "http://" + str(url).strip())
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()
    query = (parsed.query or "").lower()
    full = f"{path}?{query}"
    if any(m in full for m in _DISCOVERY_MARKERS):
        return False
    if _host_matches(host.replace("www.", "", 1) if host.startswith("www.") else host, "codal.ir"):
        return any(idn in full for idn in _CODAL_DOC_IDENTIFIERS)
    # Non-Codal: homepage/profile root is not a document.
    if path in ("", "/"):
        return False
    segments = [s for s in path.split("/") if s]
    return len(segments) >= 2 or any(c.isdigit() for c in path)


def is_valid_exact_jalali_date(value: str) -> bool:
    """Strict exact-day Jalali validation.

    Requires ``YYYY-MM-DD`` with a full, in-range, round-trippable day. Year-only,
    month-only, slash-separated, and out-of-range values are rejected."""
    s = str(value or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return False
    y, m, d = (int(x) for x in s.split("-"))
    if not (1 <= m <= 12 and 1 <= d <= 31):
        return False
    try:
        g = jalali_to_gregorian_str(s)
        return gregorian_to_jalali_str(g) == s
    except Exception:
        return False


def _is_sha256(value: str) -> bool:
    v = (value or "").strip().lower()
    return len(v) == 64 and all(c in "0123456789abcdef" for c in v)


def _truthy(value) -> bool:
    return str(value).strip().lower() == "true"


def _contemporaneous_with_event(rec: dict) -> bool:
    """A credible-news source is contemporaneous when it carries an explicit,
    valid publication date within 30 days of the reviewed event date."""
    if not _truthy(rec.get("publication_date_explicit", "")):
        return False
    pub = str(rec.get("publication_date_jalali", "")).strip()
    ev = str(rec.get("reviewed_date_jalali", "")).strip()
    if not is_valid_exact_jalali_date(pub) or not is_valid_exact_jalali_date(ev):
        return False
    try:
        delta = abs((jalali_str_to_gregorian_date(pub)
                     - jalali_str_to_gregorian_date(ev)).days)
    except Exception:
        return False
    return delta <= 30


def _greg(jalali: str) -> str:
    if not jalali:
        return ""
    try:
        return jalali_to_gregorian_str(jalali)
    except Exception:
        return ""


def _snapshot_rel_path(ticker: str, idx: int) -> str:
    return f"stage124/batch02_parts/snapshots_part03/{normalize_ticker(ticker)}_source_{idx}.html"


def load_company_names() -> dict:
    pm = read_csv(PARTIAL_MASTER)
    names = {}
    for _, r in pm.iterrows():
        if r["ticker"] in PART03_TICKERS:
            names[r["ticker"]] = r["company_name"]
    return names


# ---- source fetch --------------------------------------------------------------
def fetch_sources(timeout: float = 5.0, force: bool = False) -> dict:
    """Attempt up to 3 source URLs per ticker, sequentially, retry=0.

    Returns ``{ticker: [record, ...]}``. A successful fetch writes a snapshot
    under ``snapshots_part03/`` and records its SHA-256. A failed fetch records
    the real failure reason and never fabricates a snapshot or hash. If a
    previous snapshot exists with a matching SHA in the existing provenance, it
    is reused without re-sending the request.
    """
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    provenance_path = PART03_DIR / "part03_source_provenance_10tickers.csv"
    existing_prov = None
    if not force and provenance_path.exists():
        try:
            existing_prov = read_csv(provenance_path)
        except Exception:
            existing_prov = None

    results = {}
    for tk in PART03_TICKERS:
        recs = []
        for idx, src in enumerate(RESEARCH_SOURCES.get(tk, [])[:3], 1):
            src_type, src_title, url = src
            snap_path = SNAPSHOT_DIR / f"{normalize_ticker(tk)}_source_{idx}.html"
            rel_path = _snapshot_rel_path(tk, idx)
            rec = {
                "ticker": tk, "source_index": idx,
                "source_type": src_type, "source_title": src_title,
                "source_url": url, "publication_date": "",
                "retrieved_at_utc": _utc_now(), "http_status": "",
                "retrieval_status": "", "final_url": url, "content_type": "",
                "response_size_bytes": "", "snapshot_path": "",
                "content_sha256": "", "extraction_notes": "",
                "exact_text_or_event_summary": "",
                "supported_event_type": "", "supported_date_jalali": "",
                # --- fetch / evidence separation fields ---
                "content_review_status": "",
                "source_authority_class": classify_source_authority(src_type, url),
                "authority_validation_error":
                    classify_source_authority_with_validation(src_type, url)[1],
                "document_specific": "true" if is_document_specific_source(url, src_type) else "false",
                "ordinary_share_explicit": "unknown",
                "event_type_supported": "",
                "exact_date_explicit": "false",
                "reviewed_date_jalali": "",
                "publication_date_jalali": "",
                "publication_date_explicit": "false",
                "contemporaneous_with_event": "false",
                "independent_source_group": registrable_domain(url),
                "evidence_accepted": "false",
            }

            reused = _reuse_existing(rec, existing_prov, tk, idx, snap_path, rel_path)
            if reused:
                recs.append(rec)
                continue

            try:
                resp = _requests.get(url, timeout=timeout, allow_redirects=True,
                                     headers={"User-Agent": "Mozilla/5.0"})
                body = resp.content
                rec["http_status"] = resp.status_code
                rec["final_url"] = resp.url
                rec["content_type"] = resp.headers.get("Content-Type", "")
                rec["response_size_bytes"] = str(len(body))
                rec["content_sha256"] = hashlib.sha256(body).hexdigest()
                snap_path.write_bytes(body)
                rec["snapshot_path"] = rel_path
                rec["retrieval_status"] = "fetched_ok"
                # A successful fetch is NOT evidence. The page content still has
                # to be reviewed manually before any event/date is supported.
                rec["content_review_status"] = "pending_manual_review"
                rec["extraction_notes"] = (
                    f"HTTP {resp.status_code}; {len(body)} bytes; raw snapshot "
                    f"stored; content_sha256 recorded. Page content must be "
                    f"reviewed before any canonical date is proposed.")
            except _requests.exceptions.Timeout:
                rec["retrieval_status"] = "timeout"
                rec["content_review_status"] = "not_available_due_to_fetch_failure"
                rec["extraction_notes"] = (
                    f"Request timed out after {timeout}s; no snapshot stored; "
                    f"no hash fabricated.")
            except _requests.exceptions.ConnectionError as e:
                rec["retrieval_status"] = "connection_error"
                rec["content_review_status"] = "not_available_due_to_fetch_failure"
                rec["extraction_notes"] = (
                    f"Connection error; no snapshot stored; no hash fabricated. "
                    f"{str(e)[:160]}")
            except Exception as e:
                rec["retrieval_status"] = "fetch_error"
                rec["content_review_status"] = "not_available_due_to_fetch_failure"
                rec["extraction_notes"] = (
                    f"Fetch error; no snapshot stored; no hash fabricated. "
                    f"{str(e)[:160]}")
            recs.append(rec)
        results[tk] = recs
    return results


def _reuse_existing(rec, existing_prov, tk, idx, snap_path, rel_path) -> bool:
    if existing_prov is None or existing_prov.empty:
        return False
    sub = existing_prov[(existing_prov["ticker"] == tk)
                        & (existing_prov["source_index"].astype(str) == str(idx))]
    if sub.empty:
        return False
    pr = sub.iloc[0]
    prov_hash = str(pr.get("content_sha256", ""))
    prov_status = str(pr.get("retrieval_status", ""))
    if prov_hash and snap_path.exists():
        body = snap_path.read_bytes()
        if hashlib.sha256(body).hexdigest() == prov_hash:
            rec.update({
                "http_status": str(pr.get("http_status", "")),
                "retrieval_status": "reused_existing_snapshot",
                "final_url": str(pr.get("final_url", rec["source_url"])),
                "content_type": str(pr.get("content_type", "")),
                "response_size_bytes": str(len(body)),
                "snapshot_path": rel_path,
                "content_sha256": hashlib.sha256(body).hexdigest(),
                "retrieved_at_utc": str(pr.get("retrieved_at_utc", _utc_now())),
                "extraction_notes": "Reused existing snapshot; SHA-256 matches provenance.",
                "supported_event_type": str(pr.get("supported_event_type", "")),
                "supported_date_jalali": str(pr.get("supported_date_jalali", "")),
                "content_review_status": "pending_manual_review",
            })
            return True
    elif prov_status in NETWORK_FAILURE_STATUSES:
        rec.update({
            "http_status": str(pr.get("http_status", "")),
            "retrieval_status": prov_status,
            "final_url": str(pr.get("final_url", rec["source_url"])),
            "retrieved_at_utc": str(pr.get("retrieved_at_utc", _utc_now())),
            "extraction_notes": str(pr.get("extraction_notes", "")),
            "content_review_status": "not_available_due_to_fetch_failure",
        })
        return True
    return False


# ---- historical TSETMC (frozen V2 audit only) ----------------------------------
def load_historical_tsetmc() -> dict:
    """Read historical TSETMC results for the 10 tickers from the frozen V2
    audit only. No live request is ever performed."""
    src_path_rel = FROZEN_V2_TSETMC_AUDIT.relative_to(ROOT).as_posix()
    src_path_rel = f"stage124/{src_path_rel}" if not src_path_rel.startswith("stage124") else src_path_rel
    src_sha = sha(FROZEN_V2_TSETMC_AUDIT) if FROZEN_V2_TSETMC_AUDIT.exists() else ""
    df = read_csv(FROZEN_V2_TSETMC_AUDIT) if FROZEN_V2_TSETMC_AUDIT.exists() else pd.DataFrame()
    results = {}
    for tk in PART03_TICKERS:
        sub = df[df["ticker"] == tk] if not df.empty else df
        if sub is not None and not sub.empty:
            r = sub.iloc[0]
            status = str(r.get("tsetmc_instrument_match_status", ""))
            cand_j = str(r.get("tsetmc_candidate_date_jalali", ""))
            cand_g = str(r.get("tsetmc_candidate_date_gregorian", ""))
            inscode = str(r.get("tsetmc_selected_inscode", ""))
            if status == "network_unreachable":
                disp = "network_unreachable"
            elif cand_j:
                disp = "audit_only_not_canonical"
            else:
                disp = status or "no_candidate"
        else:
            status = "not_in_historical_v2_audit"
            cand_j = cand_g = inscode = ""
            disp = "not_in_historical_v2_audit"
        results[tk] = {
            "instrument_match_status": status,
            "tsetmc_candidate_date_jalali": cand_j,
            "tsetmc_candidate_date_gregorian": cand_g,
            "selected_inscode": inscode,
            "candidate_disposition": disp,
            "source_file_path": src_path_rel,
            "source_file_sha256": src_sha,
            "probe_source": "historical_v2_audit",
            "network_request_performed": "false",
        }
    return results


# ---- DataFrame builders --------------------------------------------------------
def build_tickers_df(company_names: dict) -> pd.DataFrame:
    rows = []
    for tk in PART03_TICKERS:
        rows.append({
            "ticker": tk,
            "ticker_normalized": normalize_ticker(tk),
            "company_name": company_names.get(tk, ""),
        })
    return pd.DataFrame(rows)


def evaluate_source_record(rec: dict, snapshot_root: Path = None) -> bool:
    """Decide whether a *single* source record is accepted (supporting) evidence.

    A successful fetch alone is never evidence. A record is accepted only when
    *all* of the following hold:

    * the fetch succeeded (``fetched_ok`` / ``reused_existing_snapshot``);
    * the content was actually reviewed (``content_review_status == reviewed``);
    * a snapshot exists with a real SHA-256, and — when ``snapshot_root`` is
      given and the file is present — the on-disk SHA matches the recorded hash;
    * the declared ``source_type`` is consistent with the real domain (no
      authority validation error);
    * the URL is *document-specific* (not a discovery / search / list page);
    * the reviewed content explicitly supports a canonical event type
      (first_public_offering / first_public_trading);
    * ``exact_date_explicit`` is true and ``reviewed_date_jalali`` is a valid
      exact-day Jalali date;
    * the content explicitly states the instrument is an ordinary share;
    * any manually-supplied ``independent_source_group`` matches the real domain.

    Returns ``True``/``False`` and never mutates ``rec``.
    """
    if str(rec.get("retrieval_status", "")) not in FETCHED_STATUSES:
        return False
    if str(rec.get("content_review_status", "")).strip().lower() != "reviewed":
        return False
    h = str(rec.get("content_sha256", "")).strip()
    snap = str(rec.get("snapshot_path", "")).strip()
    if not snap or not _is_sha256(h):
        return False
    if snapshot_root is not None:
        sp = Path(snapshot_root) / snap
        if not sp.exists():
            return False
        if hashlib.sha256(sp.read_bytes()).hexdigest() != h.lower():
            return False
    # Authority consistency (domain is the source of truth).
    src_type = str(rec.get("source_type", ""))
    url = str(rec.get("source_url", ""))
    _cls, verr = classify_source_authority_with_validation(src_type, url)
    if verr:
        return False
    # Document specificity.
    if not is_document_specific_source(url, src_type):
        return False
    # Canonical event + valid exact-day date.
    if str(rec.get("event_type_supported", "")).strip() not in CANONICAL_EVENT_TYPES:
        return False
    if not _truthy(rec.get("exact_date_explicit", "")):
        return False
    if not is_valid_exact_jalali_date(rec.get("reviewed_date_jalali", "")):
        return False
    if not _truthy(rec.get("ordinary_share_explicit", "")):
        return False
    # A manually-asserted independent group must match the real domain.
    declared_group = str(rec.get("independent_source_group", "")).strip().lower()
    if declared_group and declared_group != registrable_domain(url):
        return False
    return True


def compute_evidence_accepted(rec: dict, snapshot_root: Path = None) -> str:
    """Authoritative, computed ``evidence_accepted`` for a provenance row. Never
    trusts a manually-supplied value (Correction 6)."""
    return "true" if evaluate_source_record(rec, snapshot_root) else "false"


def _record_authority(rec: dict) -> str:
    """Domain-strict authority class for an (already accepted) record."""
    return classify_source_authority(str(rec.get("source_type", "")),
                                     str(rec.get("source_url", "")))


def decide_ready_for_user_review(records: list, snapshot_root: Path = None) -> dict:
    """Independent, testable evidence decision.

    ``ready=True`` requires accepted evidence (see :func:`evaluate_source_record`)
    that converges on a single exact-day canonical date with no conflict, AND a
    sufficient *qualifying* source condition:

    * one official-regulatory source (no contemporaneity requirement), OR
    * one credible-news / company-official source that is *contemporaneous* with
      the event (publication date within 30 days), OR
    * two qualifying sources from *different* real domains.

    Aggregator / unknown sources may corroborate but never make a record ready,
    so two aggregators (even from different domains) or aggregator+unknown never
    reach ready.
    """
    accepted = [r for r in records if evaluate_source_record(r, snapshot_root)]
    out = {
        "ready": False,
        "canonical_date": "",
        "event_type": "",
        "ordinary_share_confirmed": "unknown",
        "conflict_flag": False,
        "conflict_dates": "",
        "conflict_reason": "",
        "accepted_count": len(accepted),
        "reason": "",
    }
    if not accepted:
        out["reason"] = "no_accepted_evidence"
        return out

    distinct_dates = sorted({normalize_jalali(str(r.get("reviewed_date_jalali", "")))
                             for r in accepted})
    distinct_events = sorted({str(r.get("event_type_supported", "")) for r in accepted})
    if len(distinct_dates) > 1 or len(distinct_events) > 1:
        out.update({
            "conflict_flag": True,
            "conflict_dates": "; ".join(d for d in distinct_dates if d),
            "conflict_reason": "conflicting reviewed canonical event/date across sources",
            "reason": "conflict",
        })
        return out

    qualifying = [r for r in accepted
                  if _record_authority(r) in QUALIFYING_AUTHORITY_CLASSES]
    official_single = any(_record_authority(r) == "official_regulatory"
                          for r in qualifying)
    contemporaneous_single = any(
        _record_authority(r) in ("credible_news", "company_official")
        and _contemporaneous_with_event(r)
        for r in qualifying)
    qual_groups = {registrable_domain(r.get("source_url", "")) for r in qualifying}
    qual_groups.discard("")
    two_independent_qualifying = len(qual_groups) >= 2

    if not (official_single or contemporaneous_single or two_independent_qualifying):
        out["reason"] = "insufficient_qualifying_or_independent_sources"
        return out

    out.update({
        "ready": True,
        "canonical_date": distinct_dates[0],
        "event_type": distinct_events[0],
        "ordinary_share_confirmed": "true",
        "reason": "accepted",
    })
    return out


def _derive_screening_status(fetch_recs: list, snapshot_root: Path = None) -> dict:
    """Derive the per-ticker screening status with correct research semantics.

    A network failure (timeout/connection/fetch error) means the research could
    not be *completed* — it is ``research_blocked_network`` /
    ``requires_manual_review``, and never ``no_reliable_evidence``. The latter is
    reserved for the case where sources were fetched AND reviewed but none
    carried first-public-entry evidence.
    """
    attempted = len(fetch_recs)
    fetched = [r for r in fetch_recs if str(r.get("retrieval_status")) in FETCHED_STATUSES]
    reviewed = [r for r in fetched
                if str(r.get("content_review_status", "")).strip().lower() == "reviewed"]
    accepted = [r for r in reviewed if evaluate_source_record(r, snapshot_root)]
    network_failures = [r for r in fetch_recs
                        if str(r.get("retrieval_status")) in NETWORK_FAILURE_STATUSES]
    network_blocked = (len(fetched) == 0 and attempted > 0
                       and len(network_failures) == attempted)

    counts = {
        "attempted_source_count": attempted,
        "fetched_source_count": len(fetched),
        "reviewed_source_count": len(reviewed),
        "evidence_source_count": len(accepted),
        "network_blocked": "true" if network_blocked else "false",
    }

    base = {
        "candidate_event_type": "",
        "proposed_canonical_public_entry_date_jalali": "",
        "proposed_canonical_event_type": "",
        "date_precision": "unknown",
        "ordinary_share_confirmed": "unknown",
        "evidence_status": "requires_manual_review",
        "research_status": "research_blocked_network",
        "research_completion_status": "blocked_network",
        "ready_for_user_review": "false",
        "conflict_flag": "false",
        "conflict_dates": "",
        "conflict_reason": "",
        "recommended_next_step": "manual_web_research_required",
    }
    base.update(counts)

    # Case 1: no successful fetch, all failures are network → research blocked.
    if network_blocked:
        return base

    # Case 2: nothing fetched at all (no sources configured / all non-network
    # failures that still are not evidence) — keep manual review, not "no evidence".
    if not fetched:
        base.update({
            "research_status": "requires_manual_review",
            "research_completion_status": "fetch_incomplete",
        })
        return base

    # Case 3: fetched but not yet reviewed → cannot judge evidence yet.
    if not reviewed:
        base.update({
            "research_status": "fetched_pending_manual_review",
            "research_completion_status": "fetched_pending_review",
            "recommended_next_step": "manual_content_review_required",
        })
        return base

    # Research was completed (fetched AND reviewed). Now apply evidence logic.
    decision = decide_ready_for_user_review(reviewed, snapshot_root)

    if decision["conflict_flag"]:
        base.update({
            "candidate_event_type": "conflict",
            "proposed_canonical_event_type": "unresolved",
            "evidence_status": "requires_manual_review",
            "research_status": "research_completed_conflict",
            "research_completion_status": "completed_conflict",
            "conflict_flag": "true",
            "conflict_dates": decision["conflict_dates"],
            "conflict_reason": decision["conflict_reason"],
            "recommended_next_step": "manual_resolution_of_conflicting_dates",
        })
        return base

    if decision["ready"]:
        base.update({
            "candidate_event_type": decision["event_type"],
            "proposed_canonical_public_entry_date_jalali": decision["canonical_date"],
            "proposed_canonical_event_type": decision["event_type"],
            "date_precision": "exact_day",
            "ordinary_share_confirmed": "true",
            "evidence_status": "candidate_supported",
            "research_status": "candidate_supported",
            "research_completion_status": "completed_with_evidence",
            "ready_for_user_review": "true",
            "recommended_next_step": "recommend_user_review",
        })
        return base

    # Reviewed, but no accepted public-entry evidence. THIS — and only this — is
    # genuine "no reliable evidence".
    base.update({
        "evidence_status": "no_reliable_evidence",
        "research_status": "research_completed_no_evidence",
        "research_completion_status": "completed_no_eligibility_evidence",
        "recommended_next_step": "manual_research_required",
    })
    return base


def build_research_screening(company_names: dict, fetch_results: dict,
                             tsetmc: dict) -> pd.DataFrame:
    rows = []
    for tk in PART03_TICKERS:
        recs = fetch_results.get(tk, [])
        st = _derive_screening_status(recs, snapshot_root=ROOT)
        srcs = RESEARCH_SOURCES.get(tk, [])
        src1 = srcs[0] if len(srcs) > 0 else ("", "", "")
        src2 = srcs[1] if len(srcs) > 1 else ("", "", "")
        ts = tsetmc.get(tk, {})
        cand_j = st["proposed_canonical_public_entry_date_jalali"]
        notes = []
        if _truthy(st["network_blocked"]):
            notes.append("research blocked by network; fetch could not complete")
        elif st["evidence_status"] == "no_reliable_evidence":
            notes.append("sources fetched and reviewed; no public-entry evidence found")
        if ts["instrument_match_status"] == "network_unreachable":
            notes.append("tsetmc historical record network_unreachable")
        elif ts["instrument_match_status"] == "not_in_historical_v2_audit":
            notes.append("no historical tsetmc record in frozen V2 audit")
        rows.append({
            "ticker": tk,
            "ticker_normalized": normalize_ticker(tk),
            "company_name": company_names.get(tk, ""),
            "admission_date_candidate_jalali": "",
            "listing_date_candidate_jalali": "",
            "first_public_offering_date_candidate_jalali": "",
            "first_public_trading_date_candidate_jalali": "",
            "candidate_event_type": st["candidate_event_type"],
            "proposed_canonical_public_entry_date_jalali": cand_j,
            "proposed_canonical_public_entry_date_gregorian": _greg(cand_j),
            "proposed_canonical_event_type": st["proposed_canonical_event_type"],
            "date_precision": st["date_precision"],
            "ordinary_share_confirmed": st["ordinary_share_confirmed"],
            "evidence_status": st["evidence_status"],
            "research_status": st["research_status"],
            "research_completion_status": st["research_completion_status"],
            "network_blocked": st["network_blocked"],
            "attempted_source_count": st["attempted_source_count"],
            "fetched_source_count": st["fetched_source_count"],
            "reviewed_source_count": st["reviewed_source_count"],
            "evidence_source_count": st["evidence_source_count"],
            "ready_for_user_review": st["ready_for_user_review"],
            "conflict_flag": st["conflict_flag"],
            "conflict_dates": st["conflict_dates"],
            "conflict_reason": st["conflict_reason"],
            "primary_source_type": src1[0],
            "primary_source_title": src1[1],
            "primary_source_url": src1[2],
            "secondary_source_type": src2[0],
            "secondary_source_title": src2[1],
            "secondary_source_url": src2[2],
            "tsetmc_instrument_match_status": ts["instrument_match_status"],
            "tsetmc_candidate_date_jalali": ts["tsetmc_candidate_date_jalali"],
            "tsetmc_candidate_disposition": ts["candidate_disposition"],
            "ambiguity_notes": "; ".join(notes),
            "recommended_next_step": st["recommended_next_step"],
        })
    return pd.DataFrame(rows)


def build_source_provenance(fetch_results: dict,
                            snapshot_root: Path = ROOT) -> pd.DataFrame:
    """Build provenance, recomputing every derived field from the URL/content so
    a manually-supplied value can never override the engine (Correction 6)."""
    rows = []
    for tk in PART03_TICKERS:
        for rec in fetch_results.get(tk, []):
            r = dict(rec)
            src_type = str(r.get("source_type", ""))
            url = str(r.get("source_url", ""))
            cls, verr = classify_source_authority_with_validation(src_type, url)
            r["source_authority_class"] = cls
            r["authority_validation_error"] = verr
            r["document_specific"] = (
                "true" if is_document_specific_source(url, src_type) else "false")
            r["contemporaneous_with_event"] = (
                "true" if _contemporaneous_with_event(r) else "false")
            # evidence_accepted is always the computed result, never the input.
            r["evidence_accepted"] = compute_evidence_accepted(r, snapshot_root)
            rows.append(r)
    return pd.DataFrame(rows)


def build_tsetmc_audit(tsetmc: dict) -> pd.DataFrame:
    rows = []
    for tk in PART03_TICKERS:
        ts = tsetmc[tk]
        rows.append({
            "ticker": tk,
            "ticker_normalized": normalize_ticker(tk),
            "instrument_match_status": ts["instrument_match_status"],
            "historical_candidate_date": ts["tsetmc_candidate_date_jalali"],
            "tsetmc_candidate_date_jalali": ts["tsetmc_candidate_date_jalali"],
            "tsetmc_candidate_date_gregorian": ts["tsetmc_candidate_date_gregorian"],
            "selected_inscode": ts["selected_inscode"],
            "candidate_disposition": ts["candidate_disposition"],
            "source_file_path": ts["source_file_path"],
            "source_file_sha256": ts["source_file_sha256"],
            "probe_source": ts["probe_source"],
            "network_request_performed": ts["network_request_performed"],
        })
    return pd.DataFrame(rows)


WORKLIST_COLUMNS = [
    "ticker", "company_name", "current_research_status", "network_blocked",
    "primary_search_query_fa", "secondary_search_query_fa",
    "official_source_target", "contemporaneous_news_target",
    "discovered_source_1_url", "discovered_source_2_url",
    "first_public_event_candidate", "candidate_date_jalali", "date_precision",
    "ordinary_share_explicit", "conflict_notes", "manual_review_status",
    "reviewer_notes",
]


def build_manual_research_worklist(company_names: dict,
                                   research_df: pd.DataFrame) -> pd.DataFrame:
    """Manual/browser research worklist for Part 3.1B.

    Exactly 10 rows in PART03 order. Source/date/result fields are intentionally
    left empty — no URL or date is ever guessed here. Only Farsi search queries
    are pre-filled to seed the manual research step."""
    status_by_tk = {}
    if research_df is not None and not research_df.empty:
        for _, r in research_df.iterrows():
            status_by_tk[r["ticker"]] = (
                str(r.get("research_status", "")),
                str(r.get("network_blocked", "")),
            )
    rows = []
    for tk in PART03_TICKERS:
        name = company_names.get(tk, "")
        rstatus, nblocked = status_by_tk.get(tk, ("research_blocked_network", "true"))
        rows.append({
            "ticker": tk,
            "company_name": name,
            "current_research_status": rstatus or "research_blocked_network",
            "network_blocked": nblocked or "true",
            "primary_search_query_fa": f"{name} عرضه اولیه",
            "secondary_search_query_fa": f"{tk} نخستین روز معامله",
            "official_source_target": f"{name} امیدنامه پذیرش بورس کدال",
            "contemporaneous_news_target": f"{name} درج نماد خبر عرضه اولیه",
            "discovered_source_1_url": "",
            "discovered_source_2_url": "",
            "first_public_event_candidate": "",
            "candidate_date_jalali": "",
            "date_precision": "unknown",
            "ordinary_share_explicit": "unknown",
            "conflict_notes": "",
            "manual_review_status": "pending_manual_research",
            "reviewer_notes": "",
        })
    return pd.DataFrame(rows, columns=WORKLIST_COLUMNS)


# ---- QC (fail-closed, computed from real output) -------------------------------
def run_part03_qc(tickers_df: pd.DataFrame, research_df: pd.DataFrame,
                  provenance_df: pd.DataFrame, tsetmc_df: pd.DataFrame,
                  frozen_before: dict, frozen_after: dict,
                  part02_before: dict, part02_after: dict,
                  worklist_df: pd.DataFrame = None) -> dict:
    assertions = []

    def check(name, passed, detail=""):
        assertions.append({"assertion": name, "passed": bool(passed), "detail": str(detail)})

    # Fail-closed: any empty/missing input fails immediately.
    check("research_df_non_empty", not research_df.empty, f"rows={len(research_df)}")
    check("provenance_df_non_empty", not provenance_df.empty, f"rows={len(provenance_df)}")
    check("tsetmc_df_non_empty", not tsetmc_df.empty, f"rows={len(tsetmc_df)}")
    if research_df.empty or provenance_df.empty or tsetmc_df.empty:
        return {"all_pass": False, "assertions": assertions}

    expected = list(PART03_TICKERS)
    actual = tickers_df["ticker"].tolist()
    expected_set, actual_set = set(expected), set(actual)

    check("exactly_10_rows", len(research_df) == 10, f"rows={len(research_df)}")
    check("exactly_10_unique_tickers", research_df["ticker"].nunique() == 10,
          f"unique={research_df['ticker'].nunique()}")
    check("ticker_set_and_order_match", actual == expected,
          f"actual={actual}")
    check("no_extra_tickers", actual_set == expected_set,
          f"extra={actual_set - expected_set}")
    check("no_missing_tickers", expected_set <= actual_set,
          f"missing={expected_set - actual_set}")
    check("no_part2_tickers", len(actual_set & set(PART02_TICKERS)) == 0,
          f"intersection={actual_set & set(PART02_TICKERS)}")
    check("no_pilot15_tickers", len(actual_set & PILOT15) == 0,
          f"intersection={actual_set & PILOT15}")
    check("no_duplicate_tickers", research_df["ticker"].duplicated().sum() == 0,
          f"dups={research_df['ticker'].duplicated().sum()}")

    prov_by_tk = {tk: provenance_df[provenance_df["ticker"] == tk]
                  for tk in PART03_TICKERS}

    for _, r in research_df.iterrows():
        tk = r["ticker"]
        cand = str(r["proposed_canonical_public_entry_date_jalali"]).strip()
        ev = str(r["proposed_canonical_event_type"]).strip()
        dp = str(r["date_precision"]).strip()
        ready = str(r["ready_for_user_review"]).strip().lower()
        es = str(r["evidence_status"]).strip()
        adm = str(r["admission_date_candidate_jalali"]).strip()
        lst = str(r["listing_date_candidate_jalali"]).strip()
        conflict = str(r["conflict_flag"]).strip().lower()
        rstatus = str(r.get("research_status", "")).strip()
        rcomp = str(r.get("research_completion_status", "")).strip()
        nblocked = str(r.get("network_blocked", "")).strip().lower()
        ord_conf = str(r.get("ordinary_share_confirmed", "")).strip().lower()

        sub = prov_by_tk.get(tk)
        # Real retrieval/review outcome for this ticker (from provenance).
        rec_statuses, rec_reviews = [], []
        if sub is not None and not sub.empty:
            rec_statuses = [str(x) for x in sub["retrieval_status"].tolist()]
            if "content_review_status" in sub.columns:
                rec_reviews = [str(x).strip().lower() for x in sub["content_review_status"].tolist()]
        any_fetched = any(s in FETCHED_STATUSES for s in rec_statuses)
        all_network_failed = (len(rec_statuses) > 0 and not any_fetched
                              and all(s in NETWORK_FAILURE_STATUSES for s in rec_statuses))
        any_reviewed = any(rv == "reviewed" for rv in rec_reviews)

        # --- research semantics: a network failure is never "no reliable evidence"
        if all_network_failed:
            check(f"timeout_not_no_reliable_evidence_{tk}",
                  es != "no_reliable_evidence",
                  f"es={es} despite all-network-failure")
            check(f"timeout_is_research_blocked_{tk}",
                  rstatus == "research_blocked_network",
                  f"research_status={rstatus}")
            check(f"network_blocked_flag_true_{tk}", nblocked == "true",
                  f"network_blocked={nblocked}")
            check(f"blocked_no_evidence_counts_{tk}",
                  str(r.get("fetched_source_count")) == "0"
                  and str(r.get("reviewed_source_count")) == "0"
                  and str(r.get("evidence_source_count")) == "0",
                  f"fetched={r.get('fetched_source_count')}, "
                  f"reviewed={r.get('reviewed_source_count')}, "
                  f"evidence={r.get('evidence_source_count')}")
            check(f"blocked_ordinary_share_unknown_{tk}", ord_conf == "unknown",
                  f"ordinary_share_confirmed={ord_conf}")
            check(f"blocked_not_ready_{tk}", ready == "false", f"ready={ready}")

        # no_reliable_evidence is only legitimate once research actually completed
        if es == "no_reliable_evidence":
            check(f"no_reliable_only_after_review_{tk}",
                  any_fetched and any_reviewed,
                  "no_reliable_evidence requires fetched+reviewed sources")

        # ordinary_share_confirmed must never be 'true' unless the record is ready
        if ord_conf == "true":
            check(f"ordinary_share_only_when_ready_{tk}", ready == "true",
                  f"ordinary_share_confirmed=true but ready={ready}")

        # a fetched-but-unreviewed ticker can never be ready
        if any_fetched and not any_reviewed:
            check(f"fetched_unreviewed_not_ready_{tk}", ready == "false",
                  f"ready={ready} with no reviewed source")

        # canonical only for exact-day offering/trading
        if cand:
            check(f"canonical_event_valid_{tk}", ev in CANONICAL_EVENT_TYPES,
                  f"ev={ev}")
            check(f"canonical_exact_day_{tk}", dp == "exact_day", f"dp={dp}")
        else:
            check(f"canonical_empty_event_when_no_date_{tk}",
                  ev in ("", "unresolved"), f"ev={ev}")

        # admission/listing-only never canonical
        if (adm or lst) and cand:
            check(f"no_canonical_from_admission_{tk}", False,
                  f"admission/listing present with canonical={cand}")
        else:
            check(f"no_canonical_from_admission_{tk}", True)

        # month/year/unknown precision → not ready
        if dp in ("month_only", "year_only", "unknown"):
            check(f"non_exact_not_ready_{tk}", ready == "false",
                  f"dp={dp}, ready={ready}")

        # conflict unresolved → not ready
        if conflict == "true":
            check(f"conflict_not_ready_{tk}", ready == "false",
                  f"ready={ready}")

        # ready=true requires exact-day canonical + fetched, hash-backed source
        if ready == "true":
            ok = (dp == "exact_day" and ev in CANONICAL_EVENT_TYPES
                  and es == "candidate_supported" and cand != ""
                  and ord_conf == "true" and conflict != "true")
            check(f"ready_requires_exact_canonical_{tk}", ok,
                  f"dp={dp}, ev={ev}, es={es}, cand={cand}, ord={ord_conf}")
            has_evidence = False
            if sub is not None and not sub.empty:
                for _, pr in sub.iterrows():
                    if (str(pr.get("retrieval_status")) in FETCHED_STATUSES
                            and str(pr.get("content_sha256")).strip()):
                        has_evidence = True
                        break
            check(f"ready_requires_fetched_source_with_hash_{tk}", has_evidence,
                  "ready=true requires a fetched source with a real SHA-256")

            # ready=true must be reproducible by the independent decision engine
            # on this ticker's actual provenance rows (no manual short-cuts).
            recs = []
            if sub is not None and not sub.empty:
                recs = [{k: pr.get(k, "") for k in pr.index}
                        for _, pr in sub.iterrows()]
            decision = decide_ready_for_user_review(recs, snapshot_root=ROOT)
            check(f"ready_requires_decision_engine_{tk}", decision["ready"] is True,
                  f"engine_reason={decision['reason']}")
            check(f"ready_requires_source_condition_{tk}", decision["ready"] is True,
                  "ready=true needs a qualifying official/contemporaneous-news "
                  "source or two qualifying independent sources (aggregators alone "
                  "are never enough)")

        # gregorian conversion of canonical
        cg = str(r["proposed_canonical_public_entry_date_gregorian"]).strip()
        if cand and cg:
            try:
                check(f"date_conversion_ok_{tk}", cg == jalali_to_gregorian_str(cand),
                      f"j={cand}, g={cg}")
            except Exception as e:
                check(f"date_conversion_ok_{tk}", False, f"err={e}")

    # provenance integrity: no fabricated snapshot/hash on failed fetch; relative paths
    for _, pr in provenance_df.iterrows():
        tk = pr["ticker"]
        idx = pr["source_index"]
        status = str(pr.get("retrieval_status", ""))
        snap = str(pr.get("snapshot_path", "")).strip()
        h = str(pr.get("content_sha256", "")).strip()
        src_type = str(pr.get("source_type", ""))
        if status not in ("fetched_ok", "reused_existing_snapshot"):
            check(f"failed_fetch_no_snapshot_{tk}_{idx}", snap == "",
                  f"status={status}, snap={snap}")
            check(f"failed_fetch_no_hash_{tk}_{idx}", h == "",
                  f"status={status}, hash={h}")
        else:
            check(f"ok_fetch_has_hash_{tk}_{idx}", bool(h),
                  "successful fetch must carry a SHA-256")
            sp = PART03_DIR.parent.parent / snap if snap else None
            if snap and sp is not None and sp.exists():
                check(f"snapshot_hash_matches_{tk}_{idx}",
                      hashlib.sha256(sp.read_bytes()).hexdigest() == h,
                      "stored snapshot SHA must match recorded hash")
        if snap:
            check(f"snapshot_path_relative_{tk}_{idx}",
                  not snap.startswith("/") and "Users" not in snap
                  and "Desktop" not in snap, f"snap={snap}")
        # taxonomy: Tacodal/aggregators never codal_official
        url = str(pr.get("source_url", "")).lower()
        if "tacodal" in url or "databours" in url or "aggregator" in url:
            check(f"aggregator_not_codal_official_{tk}_{idx}",
                  src_type != "codal_official", f"type={src_type}, url={url}")
        if src_type == "codal_official":
            check(f"codal_official_is_codal_domain_{tk}_{idx}",
                  "codal.ir" in url, f"url={url}")
        # evidence acceptance integrity: a record can only be accepted evidence
        # when it was fetched, reviewed, and carries a snapshot + real hash.
        if _truthy(pr.get("evidence_accepted", "")):
            review = str(pr.get("content_review_status", "")).strip().lower()
            check(f"accepted_requires_snapshot_hash_{tk}_{idx}",
                  status in FETCHED_STATUSES and snap != "" and _is_sha256(h),
                  f"accepted but status={status}, snap={bool(snap)}, hash={h[:8]}")
            check(f"accepted_requires_review_{tk}_{idx}", review == "reviewed",
                  f"accepted but content_review_status={review}")
        # a fetched-but-unreviewed record must never be accepted as evidence
        if status in FETCHED_STATUSES and \
                str(pr.get("content_review_status", "")).strip().lower() != "reviewed":
            check(f"unreviewed_not_accepted_{tk}_{idx}",
                  not _truthy(pr.get("evidence_accepted", "")),
                  "fetched but unreviewed source must not be evidence_accepted")

        # evidence_accepted must equal the engine's recomputed value (Correction 6)
        rec_dict = {k: pr.get(k, "") for k in pr.index}
        recomputed = compute_evidence_accepted(rec_dict, snapshot_root=ROOT)
        check(f"evidence_accepted_matches_engine_{tk}_{idx}",
              str(pr.get("evidence_accepted", "")).strip().lower() == recomputed,
              f"stored={pr.get('evidence_accepted')}, computed={recomputed}")

        # domain-strict taxonomy: stored authority class must match recomputation,
        # and a validation error forbids acceptance.
        real_url = str(pr.get("source_url", ""))
        rec_cls, rec_verr = classify_source_authority_with_validation(src_type, real_url)
        if "source_authority_class" in pr.index:
            check(f"authority_class_matches_engine_{tk}_{idx}",
                  str(pr.get("source_authority_class", "")).strip() == rec_cls,
                  f"stored={pr.get('source_authority_class')}, computed={rec_cls}")
        if rec_verr:
            check(f"authority_error_blocks_acceptance_{tk}_{idx}",
                  not _truthy(pr.get("evidence_accepted", "")),
                  f"validation_error present but evidence_accepted="
                  f"{pr.get('evidence_accepted')}")

    # TSETMC audit: all from historical V2 audit, no network, never canonical
    research_canon = {r["ticker"]: str(r["proposed_canonical_public_entry_date_jalali"]).strip()
                      for _, r in research_df.iterrows()}
    for _, r in tsetmc_df.iterrows():
        tk = r["ticker"]
        check(f"tsetmc_from_historical_v2_{tk}",
              str(r["probe_source"]) == "historical_v2_audit",
              f"probe_source={r['probe_source']}")
        check(f"tsetmc_no_network_{tk}",
              str(r["network_request_performed"]).lower() == "false",
              f"network_request_performed={r['network_request_performed']}")
        td = str(r["tsetmc_candidate_date_jalali"]).strip()
        if td:
            check(f"tsetmc_date_not_canonical_{tk}",
                  normalize_jalali(td) != normalize_jalali(research_canon.get(tk, "") or " "),
                  "a tsetmc historical date must never equal the canonical date")
        if str(r["instrument_match_status"]) == "network_unreachable":
            check(f"network_unreachable_preserved_{tk}",
                  str(r["candidate_disposition"]) == "network_unreachable",
                  f"disp={r['candidate_disposition']}")

    # no fabricated user verification anywhere
    blob = " ".join(str(df.values) for df in (research_df, provenance_df, tsetmc_df))
    user_verify_token = "verified_user_" + "confirmed"
    check("no_user_verification_token", user_verify_token not in blob,
          "a fabricated user-verification token must not appear in any Part 3 output")
    check("no_user_decision_column", "user_decision" not in research_df.columns,
          "no user_decision column")
    check("no_verification_status_column", "verification_status" not in research_df.columns,
          "no verification_status column")
    check("no_full_verified_master", not FULL_VERIFIED_FORBIDDEN.exists(),
          "listing_master_verified_stage124.csv must not exist")

    # Part 2 outputs unchanged
    for fp_str in sorted(part02_before):
        check(f"part02_unchanged_{Path(fp_str).name}",
              part02_before[fp_str] == part02_after.get(fp_str, ""),
              f"before={part02_before[fp_str][:12]}, after={part02_after.get(fp_str, '')[:12]}")

    # frozen V2 + Stage122/123 unchanged
    for fp_str in sorted(frozen_before):
        check(f"frozen_unchanged_{Path(fp_str).name}",
              frozen_before[fp_str] == frozen_after.get(fp_str, ""),
              f"before={frozen_before[fp_str][:12]}, after={frozen_after.get(fp_str, '')[:12]}")
    check("stage123_sha_matches", sha(STAGE123_INPUT) == EXPECTED_STAGE123_SHA,
          f"sha={sha(STAGE123_INPUT)[:12]}")
    check("stage122_sha_matches", sha(STAGE122_INPUT) == EXPECTED_STAGE122_SHA,
          f"sha={sha(STAGE122_INPUT)[:12]}")

    # Manual research worklist: exactly 10 rows, correct order, no guessed
    # URLs/dates.
    if worklist_df is not None:
        check("worklist_exactly_10_rows", len(worklist_df) == 10,
              f"rows={len(worklist_df)}")
        check("worklist_ticker_order",
              worklist_df["ticker"].tolist() == list(PART03_TICKERS),
              f"order={worklist_df['ticker'].tolist()}")
        empty_cols = ["discovered_source_1_url", "discovered_source_2_url",
                      "first_public_event_candidate", "candidate_date_jalali"]
        for c in empty_cols:
            check(f"worklist_no_guessed_{c}",
                  (worklist_df[c].astype(str).str.strip() == "").all(),
                  f"non-empty values present in {c}")
        url_blob = " ".join(worklist_df["discovered_source_1_url"].astype(str)) + \
                   " ".join(worklist_df["discovered_source_2_url"].astype(str))
        check("worklist_no_http_urls", "http" not in url_blob.lower(),
              "no discovered URL may be present in the initial worklist")

    all_pass = all(a["passed"] for a in assertions)
    return {"all_pass": all_pass, "assertions": assertions}


# ---- protected Part 2 files ----------------------------------------------------
PART02_PROTECTED = [
    PART03_DIR / "part02_research_screening_10tickers.csv",
    PART03_DIR / "part02_source_provenance_10tickers.csv",
    PART03_DIR / "part02_tsetmc_audit_10tickers.csv",
    PART03_DIR / "part02_qc_report.json",
    PART03_DIR / "part02_metadata_and_hashes.json",
    PART03_DIR / "part02_hash_manifest.csv",
    PART03_DIR / "snapshots_hkeshti" / "source_1.html",
]

FROZEN_FILES = [FROZEN_V2_TSETMC_AUDIT, STAGE122_INPUT, STAGE123_INPUT]


# ---- main run ------------------------------------------------------------------
def run(force_fetch: bool = False) -> dict:
    PART03_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    source_commit = git_head()

    part02_before = {str(fp): sha(fp) for fp in PART02_PROTECTED if fp.exists()}
    frozen_before = {str(fp): sha(fp) for fp in FROZEN_FILES if fp.exists()}

    company_names = load_company_names()
    tickers_df = build_tickers_df(company_names)
    fetch_results = fetch_sources(timeout=5.0, force=force_fetch)
    tsetmc = load_historical_tsetmc()

    research_df = build_research_screening(company_names, fetch_results, tsetmc)
    provenance_df = build_source_provenance(fetch_results)
    tsetmc_df = build_tsetmc_audit(tsetmc)
    worklist_df = build_manual_research_worklist(company_names, research_df)

    tickers_path = PART03_DIR / "part03_tickers.csv"
    research_path = PART03_DIR / "part03_research_screening_10tickers.csv"
    provenance_path = PART03_DIR / "part03_source_provenance_10tickers.csv"
    tsetmc_path = PART03_DIR / "part03_tsetmc_audit_10tickers.csv"
    worklist_path = PART03_DIR / "part03_manual_research_worklist.csv"

    write_csv(research_df, research_path)
    write_csv(provenance_df, provenance_path)
    write_csv(worklist_df, worklist_path)

    part02_after = {str(fp): sha(fp) for fp in PART02_PROTECTED if fp.exists()}
    frozen_after = {str(fp): sha(fp) for fp in FROZEN_FILES if fp.exists()}

    qc = run_part03_qc(tickers_df, research_df, provenance_df, tsetmc_df,
                       frozen_before, frozen_after, part02_before, part02_after,
                       worklist_df=worklist_df)

    qc_report = {
        "stage": "stage124_batch02_part03",
        "generated_at": _utc_now(),
        "source_commit": source_commit,
        "ticker_count": 10,
        "tickers": PART03_TICKERS,
        "all_pass": qc["all_pass"],
        "assertion_count": len(qc["assertions"]),
        "failed_count": sum(1 for a in qc["assertions"] if not a["passed"]),
        "assertions": qc["assertions"],
    }
    qc_path = PART03_DIR / "part03_qc_report.json"
    with open(qc_path, "w", encoding="utf-8") as f:
        json.dump(qc_report, f, ensure_ascii=False, indent=2)

    summary = {
        "stage": "stage124_batch02_part03",
        "generated_at": _utc_now(),
        "source_commit": source_commit,
        "ticker_count": 10,
        "tickers": PART03_TICKERS,
        "exact_day_canonical": {},
        "research_blocked_network_tickers": [],
        "requires_manual_review_tickers": [],
        "no_reliable_evidence_tickers": [],
        "ready_for_user_review_tickers": [],
        "conflict_tickers": [],
        "counts": {
            "ready_count": 0,
            "network_blocked_count": 0,
            "total_attempted_sources": 0,
            "total_fetched_sources": 0,
            "total_reviewed_sources": 0,
            "total_evidence_sources": 0,
        },
        "per_ticker_status": {},
        "tsetmc_historical": {},
        "fetch_results": {},
    }
    for _, r in research_df.iterrows():
        tk = r["ticker"]
        es = r["evidence_status"]
        cand = str(r["proposed_canonical_public_entry_date_jalali"]).strip()
        ready = str(r["ready_for_user_review"]).strip().lower()
        if cand:
            summary["exact_day_canonical"][tk] = cand
        if str(r["research_status"]).strip() == "research_blocked_network":
            summary["research_blocked_network_tickers"].append(tk)
        if es == "requires_manual_review":
            summary["requires_manual_review_tickers"].append(tk)
        if es == "no_reliable_evidence":
            summary["no_reliable_evidence_tickers"].append(tk)
        if ready == "true":
            summary["ready_for_user_review_tickers"].append(tk)
        if str(r["conflict_flag"]).strip().lower() == "true":
            summary["conflict_tickers"].append(tk)
        if str(r.get("network_blocked", "")).strip().lower() == "true":
            summary["counts"]["network_blocked_count"] += 1
        summary["counts"]["total_attempted_sources"] += int(r.get("attempted_source_count", 0) or 0)
        summary["counts"]["total_fetched_sources"] += int(r.get("fetched_source_count", 0) or 0)
        summary["counts"]["total_reviewed_sources"] += int(r.get("reviewed_source_count", 0) or 0)
        summary["counts"]["total_evidence_sources"] += int(r.get("evidence_source_count", 0) or 0)
        summary["per_ticker_status"][tk] = {
            "evidence_status": es,
            "research_status": str(r["research_status"]),
            "research_completion_status": str(r.get("research_completion_status", "")),
            "network_blocked": str(r.get("network_blocked", "")),
            "ordinary_share_confirmed": str(r.get("ordinary_share_confirmed", "")),
            "ready_for_user_review": ready,
            "recommended_next_step": str(r.get("recommended_next_step", "")),
        }
    summary["counts"]["ready_count"] = len(summary["ready_for_user_review_tickers"])
    for tk, ts in tsetmc.items():
        summary["tsetmc_historical"][tk] = {
            "instrument_match_status": ts["instrument_match_status"],
            "historical_candidate_date": ts["tsetmc_candidate_date_jalali"],
            "candidate_disposition": ts["candidate_disposition"],
            "network_request_performed": ts["network_request_performed"],
        }
    for tk in PART03_TICKERS:
        summary["fetch_results"][tk] = [
            {"source_index": rec["source_index"],
             "source_url": rec["source_url"],
             "retrieval_status": rec["retrieval_status"],
             "http_status": str(rec["http_status"]),
             "snapshot_path": rec["snapshot_path"],
             "content_sha256": rec["content_sha256"]}
            for rec in fetch_results.get(tk, [])
        ]
    summary_path = PART03_DIR / "part03_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return {
        "qc": qc,
        "summary": summary,
        "files": {
            "tickers": str(tickers_path),
            "research_screening": str(research_path),
            "source_provenance": str(provenance_path),
            "tsetmc_audit": str(tsetmc_path),
            "manual_research_worklist": str(worklist_path),
            "qc_report": str(qc_path),
            "summary_json": str(summary_path),
        },
    }


if __name__ == "__main__":
    out = run()
    print(json.dumps({"all_pass": out["qc"]["all_pass"],
                      "assertions": len(out["qc"]["assertions"]),
                      "failed": sum(1 for a in out["qc"]["assertions"] if not a["passed"])},
                     ensure_ascii=False))
