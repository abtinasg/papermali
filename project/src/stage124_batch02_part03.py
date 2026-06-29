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

# Reviewed event types: canonical + non-canonical events that reviewed evidence
# may support.  ``public_company_conversion`` is an alias for conversion_to_public.
REVIEWED_EVENT_TYPES = {
    "first_public_offering", "first_public_trading",
    "admission", "listing", "public_company_conversion",
}

# Date precision enum for reviewed evidence.
REVIEWED_DATE_PRECISIONS = {"exact_day", "month_only", "year_only", "unknown"}

# Evidence role enum.
EVIDENCE_ROLES = {
    "none", "canonical_exact_candidate", "canonical_partial_date",
    "admission_only", "listing_only", "public_company_conversion_only",
    "conflicting_evidence", "non_entry_evidence",
}

# Central, exported research/evidence status enums. Production QC and the tests
# MUST import these — no module redefines the allowed sets locally.
ALLOWED_RESEARCH_STATUSES = {
    "research_blocked_network",
    "requires_manual_review",
    "source_discovered",
    "fetched_pending_manual_review",
    "research_completed_no_evidence",
    "research_completed_conflict",
    "research_completed_partial_public_entry_date",
    "research_completed_exact_public_entry_needs_corroboration",
    "research_completed_admission_only",
    "research_completed_listing_only",
    "research_completed_noncanonical_entry_evidence",
    "candidate_supported",
}
ALLOWED_EVIDENCE_STATUSES = {
    "requires_manual_review",
    "requires_first_public_trade_evidence",
    "no_reliable_evidence",
    "candidate_supported",
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


# ---- persistent source registry ------------------------------------------------
# The registry is the *source of truth* for which URLs the pipeline attempts. New
# URLs discovered in Part 3.1B are added here (next source_index) and flow into
# the pipeline without any code change. ``RESEARCH_SOURCES`` above is kept only to
# seed the registry the first time and for migration/test compatibility.
SOURCE_REGISTRY_PATH = PART03_DIR / "part03_source_registry.csv"
SOURCE_REGISTRY_COLUMNS = [
    "ticker", "source_index", "source_type", "source_title", "source_url",
    "source_origin", "active", "discovery_status", "added_at_utc", "added_by",
    "discovery_notes",
]
# Schema for explicitly registering newly discovered sources.
DISCOVERY_ADDITION_COLUMNS = [
    "ticker", "source_type", "source_title", "source_url", "added_by",
    "discovery_notes",
]


def build_seed_registry_df() -> "pd.DataFrame":
    """Build the initial registry: exactly the current 20 seed sources, two per
    ticker, preserving ticker / source_index / type / title / url."""
    rows = []
    for tk in PART03_TICKERS:
        for idx, src in enumerate(RESEARCH_SOURCES.get(tk, []), 1):
            src_type, src_title, url = src
            rows.append({
                "ticker": tk, "source_index": str(idx),
                "source_type": src_type, "source_title": src_title,
                "source_url": url, "source_origin": "seed_part03",
                "active": "true", "discovery_status": "network_blocked",
                "added_at_utc": "", "added_by": "", "discovery_notes": "",
            })
    return pd.DataFrame(rows, columns=SOURCE_REGISTRY_COLUMNS)


def load_source_registry(path: Path = None) -> "pd.DataFrame":
    """Load the registry CSV, or fall back to the freshly-seeded registry when the
    file does not yet exist."""
    path = path or SOURCE_REGISTRY_PATH
    if path.exists():
        df = read_csv(path)
        # Ensure all expected columns exist (forward-compatible).
        for c in SOURCE_REGISTRY_COLUMNS:
            if c not in df.columns:
                df[c] = ""
        return df[SOURCE_REGISTRY_COLUMNS]
    return build_seed_registry_df()


def validate_source_registry(df: "pd.DataFrame"):
    """Fail-closed validation. Returns ``(ok, errors)``."""
    errors = []
    if df is None or df.empty:
        return False, ["registry is empty"]
    allowed = set(PART03_TICKERS)
    seen_keys = set()
    seen_urls = {}
    for i, r in df.iterrows():
        tk = str(r.get("ticker", "")).strip()
        si = str(r.get("source_index", "")).strip()
        url = str(r.get("source_url", "")).strip()
        st = str(r.get("source_type", "")).strip()
        active = str(r.get("active", "")).strip().lower()
        if tk not in allowed:
            errors.append(f"row {i}: ticker '{tk}' not in Part 3 scope")
        if not (si.isdigit() and int(si) >= 1):
            errors.append(f"row {i}: source_index '{si}' is not a positive integer")
        key = (tk, si)
        if key in seen_keys:
            errors.append(f"row {i}: duplicate (ticker, source_index)={key}")
        seen_keys.add(key)
        if not url:
            errors.append(f"row {i}: empty source_url")
        if not st:
            errors.append(f"row {i}: empty source_type")
        if active not in ("true", "false"):
            errors.append(f"row {i}: active='{active}' must be true/false")
        if url:
            ukey = (tk, url)
            if ukey in seen_urls:
                errors.append(f"row {i}: duplicate source_url for ticker '{tk}'")
            seen_urls[ukey] = i
    return (len(errors) == 0), errors


def registry_to_research_sources(df: "pd.DataFrame",
                                 include_inactive: bool = False) -> dict:
    """Convert the registry into ``{ticker: [(source_index, source_type, title,
    url), ...]}`` sorted by source_index. Inactive sources are excluded unless
    ``include_inactive`` is set."""
    out = {tk: [] for tk in PART03_TICKERS}
    if df is None or df.empty:
        return out
    for _, r in df.iterrows():
        tk = str(r.get("ticker", "")).strip()
        if tk not in out:
            continue
        if not include_inactive and str(r.get("active", "")).strip().lower() != "true":
            continue
        si = str(r.get("source_index", "")).strip()
        if not si.isdigit():
            continue
        out[tk].append((int(si), str(r.get("source_type", "")),
                        str(r.get("source_title", "")), str(r.get("source_url", ""))))
    for tk in out:
        out[tk].sort(key=lambda e: e[0])
    return out


def register_discovered_sources(registry_df: "pd.DataFrame",
                                additions_df: "pd.DataFrame") -> "pd.DataFrame":
    """Append explicitly-discovered sources to the registry. Never fetches and
    never writes the file (callers persist deliberately). Assigns the next
    source_index per ticker, rejects duplicate URLs and out-of-scope tickers,
    and tags ``source_origin=manual_discovery`` / ``active=true``."""
    base = registry_df.copy() if registry_df is not None else build_seed_registry_df().iloc[0:0]
    for c in SOURCE_REGISTRY_COLUMNS:
        if c not in base.columns:
            base[c] = ""
    base = base[SOURCE_REGISTRY_COLUMNS]
    if additions_df is None or additions_df.empty:
        return base.reset_index(drop=True)

    allowed = set(PART03_TICKERS)
    # current max index and url set per ticker
    max_idx = {}
    urls = {}
    for _, r in base.iterrows():
        tk = str(r.get("ticker", "")).strip()
        si = str(r.get("source_index", "")).strip()
        if si.isdigit():
            max_idx[tk] = max(max_idx.get(tk, 0), int(si))
        urls.setdefault(tk, set()).add(str(r.get("source_url", "")).strip())

    new_rows = []
    for _, a in additions_df.iterrows():
        tk = str(a.get("ticker", "")).strip()
        url = str(a.get("source_url", "")).strip()
        st = str(a.get("source_type", "")).strip()
        if tk not in allowed:
            raise ValueError(f"register_discovered_sources: ticker '{tk}' out of scope")
        if not url or not st:
            raise ValueError("register_discovered_sources: source_url/source_type required")
        if url in urls.get(tk, set()):
            raise ValueError(f"register_discovered_sources: duplicate url for '{tk}': {url}")
        nxt = max_idx.get(tk, 0) + 1
        max_idx[tk] = nxt
        urls.setdefault(tk, set()).add(url)
        new_rows.append({
            "ticker": tk, "source_index": str(nxt), "source_type": st,
            "source_title": str(a.get("source_title", "")), "source_url": url,
            "source_origin": "manual_discovery", "active": "true",
            "discovery_status": "discovered_pending_fetch",
            "added_at_utc": str(a.get("added_at_utc", "")),
            "added_by": str(a.get("added_by", "")),
            "discovery_notes": str(a.get("discovery_notes", "")),
        })
    if new_rows:
        base = pd.concat([base, pd.DataFrame(new_rows, columns=SOURCE_REGISTRY_COLUMNS)],
                         ignore_index=True)
    return base.reset_index(drop=True)


# Retrieval statuses that count as a *successful* fetch.
FETCHED_STATUSES = {"fetched_ok", "reused_existing_snapshot", "manual_snapshot_imported"}

# Retrieval statuses that are pure network failures. A network failure means the
# research could not be *completed*; it never means "no reliable evidence".
NETWORK_FAILURE_STATUSES = {"timeout", "connection_error", "fetch_error"}

# Source authority taxonomy. Only genuine regulatory disclosure domains are the
# official regulator; TSETMC is market-data audit (never canonical); SENA and
# reputable wire/news agencies are (contemporaneous) market news; everything else
# (Rahavard, Tacodal, TGJU, …) is an information aggregator.
OFFICIAL_REGULATORY_DOMAINS = {
    "codal.ir", "seo.ir", "ime.co.ir", "tse.ir", "irbourse.com", "ifb.ir",
}
# Market-data / audit only. May corroborate but is NEVER qualifying for ready and
# never the sole basis of a canonical date.
OFFICIAL_MARKET_DATA_DOMAINS = {
    "tsetmc.com",
}
# SENA is official market *news*, treated like credible news (needs an explicit
# contemporaneous publication date to qualify as a single source).
CREDIBLE_NEWS_DOMAINS = {
    "irna.ir", "isna.ir", "mehrnews.com", "donya-e-eqtesad.com",
    "eghtesadnews.com", "boursenews.ir", "sena.ir", "tasnimnews.com",
    "ilna.ir", "ecoiran.com",
}
AGGREGATOR_DOMAINS = {
    "rahavard365.com", "tacodal.ir", "tgju.org", "fipiran.com",
    "bourseview.com", "sahmeto.com", "databours.ir",
}

# Per-ticker verified company-official domains. Fail-closed: a company_official
# claim is only valid when the URL host is in this ticker's whitelist. No domain
# is guessed — these stay empty until a company domain is actually verified in
# Part 3.1B.
VERIFIED_COMPANY_OFFICIAL_DOMAINS: dict = {}

# Authority classes that can satisfy the source-sufficiency condition for
# ready=true. Aggregator / unknown / market-data-audit may be *supporting*
# evidence but never make a record ready on their own.
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
    "official_market_news": "credible_news",
    "market_data": "official_market_data_audit",
    "official_market_data_audit": "official_market_data_audit",
    "market_information_aggregator": "market_information_aggregator",
    "aggregator": "market_information_aggregator",
    "company_official": "company_official",
}

# Codal evidence must point at a specific, stable document/announcement.
_CODAL_DOC_IDENTIFIERS = (
    "letterserial", "tracingno", "announcementid", "attachment",
    "/decision.aspx", "/letter", "document", ".pdf",
)
# Other regulatory disclosure documents (non-Codal) — stable-id / file markers.
_REGULATORY_DOC_MARKERS = (
    "letterserial", "tracingno", "announcementid", "attachment",
    "announcement", "disclosure", "document", "notice", ".pdf",
)
# Credible-news article-page markers and the non-article pages they must avoid.
_NEWS_ARTICLE_MARKERS = (
    "/news/", "/article/", "/articles/", "/fa/news", "/post/", "/posts/",
    "/content/", "/tiny/news", "/detail/",
)
_NEWS_NON_ARTICLE_MARKERS = (
    "/category", "/categories", "/tag", "/tags", "/archive", "/topic",
    "/service/", "/services", "/section",
)
# Company-official document markers and the overview/profile pages to reject.
_COMPANY_DOC_MARKERS = (
    "/news", "/announcement", "/announcements", "/press", "/notice",
    "/disclosure", "/article", ".pdf",
)
_COMPANY_NON_DOC_MARKERS = (
    "/about", "/investor", "/investors", "/profile", "/contact",
    "/company", "/overview", "/home",
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
    if _host_in(host, OFFICIAL_MARKET_DATA_DOMAINS):
        return "official_market_data_audit"
    if _host_in(host, CREDIBLE_NEWS_DOMAINS):
        return "credible_news"
    if _host_in(host, AGGREGATOR_DOMAINS):
        return "market_information_aggregator"
    return "unknown"


def classify_source_authority_with_validation(source_type: str, url: str,
                                              ticker: str = ""):
    """Fail-closed authority classification. The URL's real domain is the source
    of truth; a declared ``source_type`` that contradicts the domain yields an
    ``unknown`` class plus a validation error string.

    ``company_official`` is only honoured when the host is in the *verified*
    whitelist for ``ticker`` (boundary-safe). No domain is guessed.

    Returns ``(authority_class, validation_error)``."""
    host = _hostname(url)
    declared = _DECLARED_CLASS.get((source_type or "").strip().lower())

    if declared == "company_official":
        domains = VERIFIED_COMPANY_OFFICIAL_DOMAINS.get(ticker, set())
        if domains and _host_in(host, domains):
            return "company_official", ""
        return "unknown", (
            f"company_official host '{host or '∅'}' not in verified whitelist "
            f"for ticker '{ticker or '∅'}'")

    domain_class = _domain_authority(host)
    if declared is None:
        # No (or unrecognised) declared type → trust the domain only.
        return domain_class, ""
    if declared == domain_class:
        return domain_class, ""
    return "unknown", (
        f"source_type '{source_type}' contradicts domain '{host or '∅'}' "
        f"(domain_class={domain_class})")


def classify_source_authority(source_type: str, url: str, ticker: str = "") -> str:
    """Domain-strict authority class (see
    :func:`classify_source_authority_with_validation`)."""
    return classify_source_authority_with_validation(source_type, url, ticker)[0]


def is_document_specific_source(url: str, source_type: str = "",
                                ticker: str = "") -> bool:
    """A *document-specific* source is a single announcement/article/document with
    a stable identifier — not a discovery, search, list, category, or overview
    page. The rule is specialised per authority class.

    * regulatory: a specific disclosure document (Codal LetterSerial / TracingNo /
      AnnouncementId / attachment / PDF, or equivalent stable-id markers);
    * credible news: a specific article page (``/news/<id>`` etc.), never a
      category / tag / search / archive / homepage;
    * company official: a specific news/announcement/PDF on the verified domain,
      never about / investor / profile / homepage;
    * aggregator / unknown: the generic depth-or-id heuristic (these are never
      *qualifying* anyway);
    * market-data audit (TSETMC): never document-specific evidence.
    """
    if not url:
        return False
    parsed = urlparse(str(url).strip() if "://" in str(url) else "http://" + str(url).strip())
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()
    query = (parsed.query or "").lower()
    full = f"{path}?{query}"
    if any(m in full for m in _DISCOVERY_MARKERS):
        return False

    cls = classify_source_authority(source_type, url, ticker)

    if cls == "official_regulatory":
        if _host_matches(host[4:] if host.startswith("www.") else host, "codal.ir"):
            return any(idn in full for idn in _CODAL_DOC_IDENTIFIERS)
        return any(m in full for m in _REGULATORY_DOC_MARKERS)

    if cls == "credible_news":
        if any(m in full for m in _NEWS_NON_ARTICLE_MARKERS):
            return False
        return any(m in full for m in _NEWS_ARTICLE_MARKERS) and any(c.isdigit() for c in path)

    if cls == "company_official":
        if any(m in full for m in _COMPANY_NON_DOC_MARKERS):
            return False
        return any(m in full for m in _COMPANY_DOC_MARKERS)

    if cls == "official_market_data_audit":
        # Market-data/audit is never document-specific evidence for canonical use.
        return False

    # aggregator / unknown → generic heuristic (never qualifying).
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


def _worklist_url_ok(value: str) -> bool:
    """A worklist discovered URL is valid when empty, or an http(s) URL with a
    real hostname and no local/absolute filesystem path."""
    v = str(value or "").strip()
    if v == "":
        return True
    if "/Users/" in v or "Desktop" in v:
        return False
    try:
        parsed = urlparse(v)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    if not parsed.hostname or "." not in parsed.hostname:
        return False
    return True


def _worklist_jalali_ok(value: str) -> bool:
    """A worklist candidate date is valid when empty, or a valid Jalali year
    (``YYYY``), month (``YYYY-MM``) or exact day (``YYYY-MM-DD``)."""
    v = str(value or "").strip()
    if v == "":
        return True
    if re.fullmatch(r"\d{4}", v):
        return 1200 <= int(v) <= 1500
    if re.fullmatch(r"\d{4}-\d{2}", v):
        m = int(v.split("-")[1])
        return 1 <= m <= 12
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        return is_valid_exact_jalali_date(v)
    return False


WORKLIST_DATE_PRECISIONS = {"unknown", "year_only", "month_only", "exact_day"}


def validate_worklist_date_precision(candidate_date_jalali: str,
                                     date_precision: str) -> bool:
    """A worklist ``candidate_date_jalali`` must agree with its ``date_precision``.

    * empty date ⇒ precision must be ``unknown``;
    * non-empty date ⇒ precision must not be ``unknown``;
    * ``year_only`` ⇒ ``YYYY`` (1200–1500);
    * ``month_only`` ⇒ ``YYYY-MM`` (year 1200–1500, month 01–12);
    * ``exact_day`` ⇒ ``YYYY-MM-DD`` and a real convertible Jalali date.
    """
    d = str(candidate_date_jalali or "").strip()
    p = str(date_precision or "").strip()
    if p not in WORKLIST_DATE_PRECISIONS:
        return False
    if d == "":
        return p == "unknown"
    if p == "unknown":
        return False
    if p == "year_only":
        return bool(re.fullmatch(r"\d{4}", d)) and 1200 <= int(d) <= 1500
    if p == "month_only":
        if not re.fullmatch(r"\d{4}-\d{2}", d):
            return False
        y, m = int(d[:4]), int(d[5:7])
        return 1200 <= y <= 1500 and 1 <= m <= 12
    if p == "exact_day":
        return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", d)) and is_valid_exact_jalali_date(d)
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
def fetch_sources(timeout: float = 5.0, force: bool = False,
                  sources_by_ticker: dict = None) -> dict:
    """Attempt each *active* registered source URL per ticker, sequentially,
    retry=0.

    The set of URLs comes from the persistent source registry (the source of
    truth); ``sources_by_ticker`` may be supplied directly (used by tests). Each
    entry is ``(source_index, source_type, title, url)`` and the registry's
    ``source_index`` is preserved verbatim. A successful fetch writes a snapshot
    under ``snapshots_part03/`` and records its SHA-256. A failed fetch records
    the real failure reason and never fabricates a snapshot or hash. If a previous
    snapshot exists with a matching SHA in the existing provenance, it is reused
    without re-sending the request.
    """
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    provenance_path = PART03_DIR / "part03_source_provenance_10tickers.csv"
    existing_prov = None
    if not force and provenance_path.exists():
        try:
            existing_prov = read_csv(provenance_path)
        except Exception:
            existing_prov = None

    if sources_by_ticker is None:
        registry = load_source_registry()
        ok, errors = validate_source_registry(registry)
        if not ok:
            raise ValueError(f"invalid source registry: {errors[:5]}")
        sources_by_ticker = registry_to_research_sources(registry, include_inactive=False)

    results = {}
    for tk in PART03_TICKERS:
        recs = []
        for entry in sources_by_ticker.get(tk, []):
            idx, src_type, src_title, url = entry
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
                # --- fetch / evidence separation fields (derived ones are
                # recomputed downstream; never trusted from input) ---
                "content_review_status": "",
                "source_authority_class": classify_source_authority(src_type, url, tk),
                "authority_validation_error":
                    classify_source_authority_with_validation(src_type, url, tk)[1],
                "document_specific":
                    "true" if is_document_specific_source(url, src_type, tk) else "false",
                "ordinary_share_explicit": "unknown",
                "event_type_supported": "",
                "exact_date_explicit": "false",
                "reviewed_date_jalali": "",
                "publication_date_jalali": "",
                "publication_date_explicit": "false",
                "contemporaneous_with_event": "false",
                "independent_source_group": registrable_domain(url),
                "evidence_accepted": "false",
                "reviewed_event_type": "",
                "reviewed_date_precision": "unknown",
                "reviewed_evidence_valid": "false",
                "evidence_role": "none",
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
                # Manual-review fields are intentionally NOT copied here; the
                # validated review overlay owns them downstream.
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
    tk = str(rec.get("ticker", ""))
    _cls, verr = classify_source_authority_with_validation(src_type, url, tk)
    if verr:
        return False
    # Document specificity (per authority class).
    if not is_document_specific_source(url, src_type, tk):
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
                                     str(rec.get("source_url", "")),
                                     str(rec.get("ticker", "")))


# Canonical provenance schema (stable column order for the output CSV).
PROVENANCE_COLUMNS = [
    "ticker", "source_index", "source_type", "source_title", "source_url",
    "publication_date", "retrieved_at_utc", "http_status", "retrieval_status",
    "final_url", "content_type", "response_size_bytes", "snapshot_path",
    "content_sha256", "extraction_notes", "exact_text_or_event_summary",
    "supported_event_type", "supported_date_jalali", "content_review_status",
    "source_authority_class", "authority_validation_error", "document_specific",
    "ordinary_share_explicit", "event_type_supported", "exact_date_explicit",
    "reviewed_date_jalali", "publication_date_jalali", "publication_date_explicit",
    "contemporaneous_with_event", "independent_source_group", "evidence_accepted",
    # --- reviewed-evidence fields (derived from review content) ---
    "reviewed_event_type", "reviewed_date_precision",
    "reviewed_evidence_valid", "evidence_role",
    # --- manual-review audit fields (preserved only via a validated overlay) ---
    "reviewer_notes", "manual_reviewed_at_utc",
]

# Manual-review fields that may be preserved across runs (only when the overlay
# is validated against an unchanged URL / snapshot / hash).
REVIEW_OVERLAY_FIELDS = [
    "content_review_status", "ordinary_share_explicit", "event_type_supported",
    "exact_date_explicit", "reviewed_date_jalali", "publication_date_jalali",
    "publication_date_explicit", "exact_text_or_event_summary",
    "supported_event_type", "supported_date_jalali",
    "reviewer_notes", "manual_reviewed_at_utc",
]

# Default (no-review) values for the overlay fields, so a record with no valid
# manual review keeps a clean, stable representation.
REVIEW_FIELD_DEFAULTS = {
    "ordinary_share_explicit": "unknown",
    "event_type_supported": "",
    "exact_date_explicit": "false",
    "reviewed_date_jalali": "",
    "publication_date_jalali": "",
    "publication_date_explicit": "false",
    "exact_text_or_event_summary": "",
    "supported_event_type": "",
    "supported_date_jalali": "",
    "reviewer_notes": "",
    "manual_reviewed_at_utc": "",
}

# Derived fields that are ALWAYS recomputed and never trusted from a prior CSV.
# ``reviewed_event_type`` / ``reviewed_date_precision`` / ``reviewed_evidence_valid`` /
# ``evidence_role`` are fully derived from the review *inputs* on every run and must
# never be inherited via the overlay.
DERIVED_NEVER_TRUSTED = [
    "source_authority_class", "authority_validation_error", "document_specific",
    "contemporaneous_with_event", "independent_source_group", "evidence_accepted",
    "ready_for_user_review",
    "reviewed_event_type", "reviewed_date_precision",
    "reviewed_evidence_valid", "evidence_role",
]


def _had_manual_review(pr) -> bool:
    """True if a prior provenance row carried any manual-review content."""
    if pr is None:
        return False
    if str(pr.get("content_review_status", "")).strip().lower() == "reviewed":
        return True
    for f in ("event_type_supported", "reviewed_date_jalali", "supported_event_type",
              "supported_date_jalali", "exact_text_or_event_summary"):
        if str(pr.get(f, "")).strip():
            return True
    if _truthy(pr.get("exact_date_explicit", "")) or _truthy(pr.get("ordinary_share_explicit", "")):
        return True
    return False


def _detect_date_precision(date_str: str) -> str:
    """Detect the precision of a Jalali date string."""
    s = str(date_str or "").strip()
    if not s:
        return "unknown"
    if is_valid_exact_jalali_date(s):
        return "exact_day"
    if re.fullmatch(r"\d{4}-\d{2}", s):
        y, m = int(s[:4]), int(s[5:7])
        if 1200 <= y <= 1500 and 1 <= m <= 12:
            return "month_only"
        return "unknown"
    if re.fullmatch(r"\d{4}", s):
        if 1200 <= int(s) <= 1500:
            return "year_only"
        return "unknown"
    return "unknown"


def evaluate_reviewed_evidence_record(rec: dict, snapshot_root: Path = None) -> dict:
    """Evaluate a *reviewed* provenance record and return a dict with:

    - ``reviewed_event_type``: the event type from review content (canonical,
      admission, listing, public_company_conversion, or empty).
    - ``reviewed_date_precision``: exact_day / month_only / year_only / unknown.
    - ``reviewed_evidence_valid``: True when the source is fetched, reviewed,
      snapshot-valid, domain-taxonomy valid, document-specific, and supports
      a valid event/date.
    - ``evidence_role``: the role this record plays in the evidence set.

    Unlike :func:`evaluate_source_record` (which is strictly for *canonical*
    evidence and requires ``ordinary_share_explicit``), this function accepts
    admission, listing, and public_company_conversion events, and does NOT
    require ``ordinary_share_explicit`` for non-canonical events.
    """
    result = {
        "reviewed_event_type": "",
        "reviewed_date_precision": "unknown",
        "reviewed_evidence_valid": False,
        "evidence_role": "none",
    }

    # Must be fetched and reviewed.
    if str(rec.get("retrieval_status", "")) not in FETCHED_STATUSES:
        return result
    if str(rec.get("content_review_status", "")).strip().lower() != "reviewed":
        return result

    # Snapshot/hash validation.
    h = str(rec.get("content_sha256", "")).strip()
    snap = str(rec.get("snapshot_path", "")).strip()
    if not snap or not _is_sha256(h):
        return result
    if snapshot_root is not None:
        sp = Path(snapshot_root) / snap
        if not sp.exists():
            return result
        if hashlib.sha256(sp.read_bytes()).hexdigest() != h.lower():
            return result

    # Authority consistency.
    src_type = str(rec.get("source_type", ""))
    url = str(rec.get("source_url", ""))
    tk = str(rec.get("ticker", ""))
    _cls, verr = classify_source_authority_with_validation(src_type, url, tk)
    if verr:
        return result

    # Document specificity.
    if not is_document_specific_source(url, src_type, tk):
        return result

    # Determine reviewed event type.
    raw_event = str(rec.get("event_type_supported", "")).strip()
    # Map conversion_to_public → public_company_conversion.
    if raw_event == "conversion_to_public":
        raw_event = "public_company_conversion"
    if raw_event not in REVIEWED_EVENT_TYPES:
        return result

    # Determine date precision from reviewed_date_jalali.
    date_str = str(rec.get("reviewed_date_jalali", "")).strip()
    precision = _detect_date_precision(date_str)
    if precision == "unknown":
        return result

    # For canonical events, exact_date_explicit must be true for exact-day.
    # Partial dates (year/month) are accepted as canonical_partial_date.
    if raw_event in CANONICAL_EVENT_TYPES:
        if precision == "exact_day":
            if not _truthy(rec.get("exact_date_explicit", "")):
                return result
            # ordinary_share_explicit is required for canonical exact evidence.
            if not _truthy(rec.get("ordinary_share_explicit", "")):
                return result
        elif precision in ("month_only", "year_only"):
            # Partial-date canonical: accept even without exact_date_explicit,
            # but still require ordinary_share_explicit.
            if not _truthy(rec.get("ordinary_share_explicit", "")):
                return result
        else:
            return result

    # Independent source group consistency.
    declared_group = str(rec.get("independent_source_group", "")).strip().lower()
    if declared_group and declared_group != registrable_domain(url):
        return result

    # All checks passed — reviewed evidence is valid.
    result["reviewed_event_type"] = raw_event
    result["reviewed_date_precision"] = precision
    result["reviewed_evidence_valid"] = True

    # Assign evidence_role.
    if raw_event in CANONICAL_EVENT_TYPES and precision == "exact_day":
        result["evidence_role"] = "canonical_exact_candidate"
    elif raw_event in CANONICAL_EVENT_TYPES and precision in ("month_only", "year_only"):
        result["evidence_role"] = "canonical_partial_date"
    elif raw_event == "admission":
        result["evidence_role"] = "admission_only"
    elif raw_event == "listing":
        result["evidence_role"] = "listing_only"
    elif raw_event == "public_company_conversion":
        result["evidence_role"] = "public_company_conversion_only"
    else:
        result["evidence_role"] = "non_entry_evidence"

    return result


def _parse_jalali_components(date_str: str):
    """Return ``(precision, (year, month, day))`` for a Jalali date, with month
    and/or day set to ``None`` for coarser precisions. Returns
    ``("unknown", None)`` when no precision can be established."""
    p = _detect_date_precision(date_str)
    s = str(date_str or "").strip()
    if p == "exact_day":
        s2 = normalize_jalali(s)
        return p, (int(s2[:4]), int(s2[5:7]), int(s2[8:10]))
    if p == "month_only":
        return p, (int(s[:4]), int(s[5:7]), None)
    if p == "year_only":
        return p, (int(s[:4]), None, None)
    return "unknown", None


def jalali_dates_compatible(a: str, b: str) -> bool:
    """Two reviewed dates are *compatible* when they do not contradict on any
    component they both specify:

    * exact ``1380-03-15`` is compatible with month ``1380-03`` and year ``1380``;
    * month ``1380-03`` is compatible with year ``1380``;
    * a different year, a different month, or two different exact days conflict.

    An ``unknown`` precision on either side cannot establish a conflict.
    """
    _pa, ca = _parse_jalali_components(a)
    _pb, cb = _parse_jalali_components(b)
    if ca is None or cb is None:
        return True
    ya, ma, da = ca
    yb, mb, db = cb
    if ya != yb:
        return False
    if ma is not None and mb is not None and ma != mb:
        return False
    if da is not None and db is not None and da != db:
        return False
    return True


def _conflict_group_for_event(event_type: str) -> str:
    """Map a reviewed event type to its conflict-grouping key. Every event type
    has its OWN conflict group, so a conflict can only arise between incompatible
    evidence for the *same* event (offering vs offering, trading vs trading,
    admission vs admission, listing vs listing, conversion vs conversion). A
    different offering and trading date is NOT a conflict — the earlier event is
    the basis of public entry and that selection is resolved by
    :func:`decide_canonical_public_entry_candidate`."""
    return event_type


def detect_evidence_conflicts(valid_pairs: list) -> dict:
    """Detect same-event conflicts among valid reviewed-evidence records.

    ``valid_pairs`` is a list of ``(record, eval_dict)`` for records whose
    ``reviewed_evidence_valid`` is True. Records are grouped by conflict group
    (canonical events together; each non-canonical event on its own). Within a
    group, any two incompatible dates (per :func:`jalali_dates_compatible`)
    constitute a conflict. Different events with different dates are NOT a
    conflict.

    Returns a dict with ``conflict`` (bool), ``event_types`` (sorted list of the
    conflicting reviewed event types), ``dates`` (sorted unique conflicting
    date strings), and ``keys`` (set of ``(ticker, source_index)`` for the
    records participating in a conflict)."""
    groups = {}
    for r, ev in valid_pairs:
        g = _conflict_group_for_event(ev["reviewed_event_type"])
        groups.setdefault(g, []).append((r, ev))

    conflict = False
    event_types = set()
    dates = set()
    keys = set()
    for _g, pairs in groups.items():
        date_list = [str(r.get("reviewed_date_jalali", "")).strip() for r, _ in pairs]
        group_conflict = False
        for i in range(len(date_list)):
            for j in range(i + 1, len(date_list)):
                if not jalali_dates_compatible(date_list[i], date_list[j]):
                    group_conflict = True
        if group_conflict:
            conflict = True
            for r, ev in pairs:
                event_types.add(ev["reviewed_event_type"])
                d = str(r.get("reviewed_date_jalali", "")).strip()
                if d:
                    dates.add(d)
                keys.add((str(r.get("ticker", "")),
                          str(r.get("source_index", "")).strip()))
    return {
        "conflict": conflict,
        "event_types": sorted(event_types),
        "dates": sorted(dates),
        "keys": keys,
    }


def _jalali_interval(date_str: str, precision: str):
    """Return ``(start, end)`` as normalized ``YYYY-MM-DD`` strings spanning the
    interval implied by a (possibly partial) Jalali date, or ``None`` when the
    value cannot be interpreted."""
    s = str(date_str or "").strip()
    if precision == "exact_day" and is_valid_exact_jalali_date(s):
        n = normalize_jalali(s)
        return n, n
    if precision == "month_only" and re.fullmatch(r"\d{4}-\d{2}", s):
        return f"{s}-01", f"{s}-31"
    if precision == "year_only" and re.fullmatch(r"\d{4}", s):
        return f"{s}-01-01", f"{s}-12-31"
    return None


def partial_candidate_blocks_exact(partial_date: str, precision: str,
                                   exact_date: str) -> bool:
    """A partial offering/trading candidate *blocks* a later exact candidate when
    its interval could yield a date EARLIER than the exact candidate.

    Rules (Jalali strings compare lexically because they are fixed-width):

    * the partial interval *contains* the exact date → compatible, not a blocker;
    * the partial interval starts strictly before the exact date → blocker
      (a genuinely earlier public entry is possible);
    * the partial interval is entirely after the exact date → not a blocker.
    """
    iv = _jalali_interval(partial_date, precision)
    ex = normalize_jalali(str(exact_date or "").strip())
    if iv is None or not ex:
        return False
    start, end = iv
    if start <= ex <= end:
        return False
    if start < ex:
        return True
    return False


_PRECISION_RANK = {"exact_day": 0, "month_only": 1, "year_only": 2, "unknown": 3}


def _candidate_sort_key(item):
    """Deterministic ordering key: highest precision first, then lowest
    source_index, then URL — never the DataFrame's incidental row order."""
    r, ev = item
    si_raw = str(r.get("source_index", "0")).strip()
    si = int(si_raw) if si_raw.isdigit() else 0
    return (_PRECISION_RANK.get(ev["reviewed_date_precision"], 3), si,
            str(r.get("source_url", "")))


def select_best_compatible_candidate(event_records: list) -> dict:
    """Pick the single best candidate for ONE event type from
    ``[(record, eval_dict), ...]`` (all the same reviewed_event_type).

    If any two dates are incompatible → ``conflict=True`` and no candidate. When
    compatible, prefer precision exact_day > month_only > year_only, breaking ties
    by lowest source_index then sorted URL."""
    out = {"conflict": False, "date": "", "precision": "unknown", "record": None}
    if not event_records:
        return out
    dates = [str(r.get("reviewed_date_jalali", "")).strip() for r, _ in event_records]
    for i in range(len(dates)):
        for j in range(i + 1, len(dates)):
            if not jalali_dates_compatible(dates[i], dates[j]):
                out["conflict"] = True
                return out
    best_r, best_ev = sorted(event_records, key=_candidate_sort_key)[0]
    out["date"] = str(best_r.get("reviewed_date_jalali", "")).strip()
    out["precision"] = best_ev["reviewed_date_precision"]
    out["record"] = best_r
    return out


def _source_sufficiency(records: list) -> bool:
    """True when the given accepted records meet the qualifying-source bar:
    one official-regulatory source, OR one contemporaneous credible-news /
    company-official source, OR two qualifying sources from two real domains.
    Aggregators alone are never sufficient."""
    qualifying = [r for r in records
                  if _record_authority(r) in QUALIFYING_AUTHORITY_CLASSES]
    official_single = any(_record_authority(r) == "official_regulatory"
                          for r in qualifying)
    contemporaneous_single = any(
        _record_authority(r) in ("credible_news", "company_official")
        and _contemporaneous_with_event(r)
        for r in qualifying)
    qual_groups = {registrable_domain(r.get("source_url", "")) for r in qualifying}
    qual_groups.discard("")
    return bool(official_single or contemporaneous_single or len(qual_groups) >= 2)


def decide_canonical_public_entry_candidate(records: list,
                                            snapshot_root: Path = None) -> dict:
    """Deterministically choose the canonical public-entry candidate.

    1. Collect valid exact-day public-entry candidates per event (offering /
       trading) and valid partial-date candidates.
    2. The earliest exact date is the only candidate that may become canonical
       (tie-breaker: first_public_offering before first_public_trading).
    3. A partial candidate whose interval could be earlier than that exact date
       *blocks* it (no later candidate may override an earlier, unresolved one).
    4. The earliest exact candidate becomes canonical/ready only if its own
       event+date has sufficient qualifying sources; otherwise it is retained but
       needs corroboration."""
    out = {
        "has_exact_candidate": False,
        "earliest_event": "", "earliest_date": "",
        "sufficient": False, "ready": False,
        "canonical_date": "", "canonical_event": "",
        "blocked_by_partial": False, "blocking_partial": "",
        "blocking_partial_event": "", "blocking_partial_precision": "unknown",
        "reason": "",
    }
    pairs = [(r, evaluate_reviewed_evidence_record(r, snapshot_root)) for r in records]
    valid = [(r, ev) for r, ev in pairs if ev["reviewed_evidence_valid"]]
    exact = [(r, ev) for r, ev in valid
             if ev["evidence_role"] == "canonical_exact_candidate"]
    partial = [(r, ev) for r, ev in valid
               if ev["evidence_role"] == "canonical_partial_date"]
    if not exact:
        out["reason"] = "no_exact_candidate"
        return out
    out["has_exact_candidate"] = True

    def _earliest_key(item):
        r, ev = item
        d = normalize_jalali(str(r.get("reviewed_date_jalali", "")))
        ev_rank = 0 if ev["reviewed_event_type"] == "first_public_offering" else 1
        si_raw = str(r.get("source_index", "0")).strip()
        si = int(si_raw) if si_raw.isdigit() else 0
        return (d, ev_rank, si, str(r.get("source_url", "")))

    earliest_r, earliest_ev = sorted(exact, key=_earliest_key)[0]
    earliest_date = normalize_jalali(str(earliest_r.get("reviewed_date_jalali", "")))
    earliest_event = earliest_ev["reviewed_event_type"]
    out["earliest_event"] = earliest_event
    out["earliest_date"] = earliest_date

    for r, ev in partial:
        pdate = str(r.get("reviewed_date_jalali", "")).strip()
        if partial_candidate_blocks_exact(pdate, ev["reviewed_date_precision"],
                                          earliest_date):
            out["blocked_by_partial"] = True
            out["blocking_partial"] = pdate
            out["blocking_partial_event"] = ev["reviewed_event_type"]
            out["blocking_partial_precision"] = ev["reviewed_date_precision"]
            out["reason"] = "earlier_partial_blocks_exact"
            return out

    same = [r for r, ev in exact
            if ev["reviewed_event_type"] == earliest_event
            and normalize_jalali(str(r.get("reviewed_date_jalali", ""))) == earliest_date]
    out["sufficient"] = _source_sufficiency(same)
    if out["sufficient"]:
        out.update(ready=True, canonical_date=earliest_date,
                   canonical_event=earliest_event, reason="ready")
    else:
        out["reason"] = "needs_corroboration"
    return out


def finalize_reviewed_evidence_set(records: list,
                                   snapshot_root: Path = None) -> dict:
    """Single, idempotent finalizer used by BOTH the production pipeline and QC.

    This is the ONLY place conflict-aware roles are assigned. Returns
    ``finalized_records`` (each carrying the FINAL ``evidence_role`` in the schema
    field, mirrored privately in ``_final_evidence_role``), ``candidates_by_event``
    (best compatible candidate per event), ``conflict_info`` (same-event
    conflicts), and ``canonical_decision``.

    A record participating in a real same-event conflict takes the finalized role
    ``conflicting_evidence``; every other record keeps its own base role. Running
    the finalizer again on its own output yields identical roles/candidates, and
    the result is independent of record order."""
    pairs = [(r, evaluate_reviewed_evidence_record(r, snapshot_root)) for r in records]
    valid = [(r, ev) for r, ev in pairs if ev["reviewed_evidence_valid"]]
    conflict_info = detect_evidence_conflicts(valid)

    finalized = []
    for r, ev in pairs:
        role = ev["evidence_role"]
        key = (str(r.get("ticker", "")), str(r.get("source_index", "")).strip())
        if ev["reviewed_evidence_valid"] and key in conflict_info["keys"]:
            role = "conflicting_evidence"
        fr = dict(r)
        fr["evidence_role"] = role          # final, schema-compatible role
        fr["_final_evidence_role"] = role   # private mirror (never written to CSV)
        finalized.append(fr)

    by_event = {}
    for r, ev in valid:
        by_event.setdefault(ev["reviewed_event_type"], []).append((r, ev))
    candidates_by_event = {etype: select_best_compatible_candidate(recs)
                           for etype, recs in by_event.items()}

    canonical_decision = decide_canonical_public_entry_candidate(records, snapshot_root)
    return {
        "finalized_records": finalized,
        "candidates_by_event": candidates_by_event,
        "conflict_info": conflict_info,
        "canonical_decision": canonical_decision,
    }


def normalize_provenance_records(records: list, snapshot_root: Path = ROOT) -> list:
    """Recompute every *derived* evidence field for each record from the URL and
    reviewed content. Manual values for derived fields are ignored entirely; the
    engine is the only source of truth for them."""
    out = []
    for rec in records:
        r = {c: str(rec.get(c, "")) for c in PROVENANCE_COLUMNS}
        # carry over numeric/source_index without stringifying to a float artdefact
        r["source_index"] = str(rec.get("source_index", "")).strip()
        src_type = r.get("source_type", "")
        url = r.get("source_url", "")
        tk = r.get("ticker", "")
        cls, verr = classify_source_authority_with_validation(src_type, url, tk)
        r["source_authority_class"] = cls
        r["authority_validation_error"] = verr
        r["document_specific"] = (
            "true" if is_document_specific_source(url, src_type, tk) else "false")
        r["independent_source_group"] = registrable_domain(url)
        r["contemporaneous_with_event"] = (
            "true" if _contemporaneous_with_event(r) else "false")
        r["evidence_accepted"] = compute_evidence_accepted(r, snapshot_root)
        # Reviewed-evidence derived fields.
        rev = evaluate_reviewed_evidence_record(r, snapshot_root)
        r["reviewed_event_type"] = rev["reviewed_event_type"]
        r["reviewed_date_precision"] = rev["reviewed_date_precision"]
        r["reviewed_evidence_valid"] = "true" if rev["reviewed_evidence_valid"] else "false"
        r["evidence_role"] = rev["evidence_role"]
        out.append(r)
    # Cross-record finalization happens in ONE place only: the finalizer assigns
    # the conflict-aware evidence_role, which we copy back so provenance, research
    # and QC all derive from the same finalized record set.
    fin = finalize_reviewed_evidence_set(out, snapshot_root)
    for r, fr in zip(out, fin["finalized_records"]):
        r["evidence_role"] = fr["evidence_role"]
    return out


def apply_validated_review_overlay(retrieval_records: list, existing_provenance,
                                   snapshot_root: Path = ROOT) -> list:
    """Overlay validated manual-review fields from a prior provenance file onto
    fresh retrieval records, then recompute all derived fields.

    A manual review is preserved only when the prior row matches on
    ``(ticker, source_index, source_url)`` AND the retrieval is still a successful
    fetch with the *same* snapshot_path and content_sha256, and the on-disk
    snapshot exists and hashes to that content_sha256. Otherwise every manual
    field is cleared; a previously-reviewed row that is now invalid is marked
    ``stale_review_invalidated``. Timeout/failed records never inherit a review.
    Derived fields are never trusted from the prior file."""
    # Keyed on (ticker, source_index) so a *changed* source_url is detected as a
    # stale review rather than silently missed.
    index = {}
    if existing_provenance is not None and not getattr(existing_provenance, "empty", True):
        for _, pr in existing_provenance.iterrows():
            key = (str(pr.get("ticker", "")), str(pr.get("source_index", "")).strip())
            index[key] = pr

    overlaid = []
    for rec in retrieval_records:
        r = dict(rec)
        for f in DERIVED_NEVER_TRUSTED:
            r.pop(f, None)
        status = str(r.get("retrieval_status", ""))
        key = (str(r.get("ticker", "")), str(r.get("source_index", "")).strip())
        pr = index.get(key)

        overlay_valid = False
        if pr is not None and status in FETCHED_STATUSES:
            snap = str(r.get("snapshot_path", "")).strip()
            h = str(r.get("content_sha256", "")).strip()
            same = (str(pr.get("source_url", "")) == str(r.get("source_url", ""))
                    and str(pr.get("snapshot_path", "")) == snap
                    and str(pr.get("content_sha256", "")) == h)
            snap_ok = False
            if snap and _is_sha256(h) and snapshot_root is not None:
                sp = Path(snapshot_root) / snap
                snap_ok = sp.exists() and hashlib.sha256(sp.read_bytes()).hexdigest() == h.lower()
            overlay_valid = bool(same and snap_ok)

        if overlay_valid:
            for f in REVIEW_OVERLAY_FIELDS:
                if f in pr.index:
                    r[f] = str(pr.get(f, ""))
        else:
            prior_review = _had_manual_review(pr)
            for f in REVIEW_OVERLAY_FIELDS:
                if f == "content_review_status":
                    continue
                if f in REVIEW_FIELD_DEFAULTS and (f in r or f not in PROVENANCE_COLUMNS):
                    # reset to clean default; drop non-schema fields
                    if f in PROVENANCE_COLUMNS:
                        r[f] = REVIEW_FIELD_DEFAULTS[f]
                    else:
                        r.pop(f, None)
            if status in FETCHED_STATUSES:
                r["content_review_status"] = (
                    "stale_review_invalidated" if prior_review else "pending_manual_review")
            else:
                r["content_review_status"] = "not_available_due_to_fetch_failure"
        overlaid.append(r)

    return normalize_provenance_records(overlaid, snapshot_root)


def decide_ready_for_user_review(records: list, snapshot_root: Path = None) -> dict:
    """Backward-compatible wrapper over the unified decision engine.

    Delegates entirely to :func:`finalize_reviewed_evidence_set` /
    :func:`decide_canonical_public_entry_candidate` and maps the result onto the
    legacy keys (``ready``, ``canonical_date``, ``event_type``,
    ``ordinary_share_confirmed``, ``conflict_flag``, ``conflict_dates``,
    ``conflict_reason``, ``accepted_count``, ``reason``). There is no separate
    "ready" logic any more: ``ready`` is true only when the canonical engine
    selects the earliest exact-day offering/trading candidate with sufficient
    qualifying sources, no same-event conflict and no earlier-partial blocker. A
    different offering and trading date is never a conflict."""
    fin = finalize_reviewed_evidence_set(records, snapshot_root)
    conflict_info = fin["conflict_info"]
    canon = fin["canonical_decision"]
    accepted = [r for r in records if evaluate_source_record(r, snapshot_root)]
    out = {
        "ready": False,
        "canonical_date": "",
        "event_type": "",
        "ordinary_share_confirmed": "unknown",
        "conflict_flag": bool(conflict_info["conflict"]),
        "conflict_dates": "; ".join(conflict_info["dates"]),
        "conflict_reason": (
            "conflicting " + ", ".join(conflict_info["event_types"]) + " dates across sources"
            if conflict_info["conflict"] else ""),
        "accepted_count": len(accepted),
        "reason": "",
    }
    if conflict_info["conflict"]:
        out["reason"] = "conflict"
        return out
    if canon["ready"]:
        out.update({
            "ready": True,
            "canonical_date": canon["canonical_date"],
            "event_type": canon["canonical_event"],
            "ordinary_share_confirmed": "true",
            "reason": "accepted",
        })
        return out
    if not canon["has_exact_candidate"]:
        out["reason"] = "no_accepted_evidence" if not accepted else "no_exact_candidate"
    elif canon["blocked_by_partial"]:
        out["reason"] = "earlier_partial_blocks_exact"
    else:
        out["reason"] = "insufficient_qualifying_or_independent_sources"
    return out


def _derive_screening_status(fetch_recs: list, snapshot_root: Path = None) -> dict:
    """Derive the per-ticker screening status with correct research semantics.

    Decision order (after fetched+reviewed):
    1. Network blocked → research_blocked_network / requires_manual_review.
    2. Fetched but unreviewed → fetched_pending_manual_review.
    3. Canonical exact-day conflict → research_completed_conflict.
    4. Canonical exact-day accepted (ready) → candidate_supported.
    5. Canonical partial-date (year/month only) → research_completed_partial_public_entry_date.
    6. Admission-only evidence → research_completed_admission_only.
    7. Listing-only evidence → research_completed_listing_only.
    8. Public-company conversion only → research_completed_noncanonical_entry_evidence.
    9. Non-entry evidence (reviewed but no relevant event) → no_reliable_evidence.
    10. No reviewed evidence at all → no_reliable_evidence.
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
        "admission_date_candidate_jalali": "",
        "listing_date_candidate_jalali": "",
        "first_public_offering_date_candidate_jalali": "",
        "first_public_trading_date_candidate_jalali": "",
    }
    base.update(counts)

    # Case 1: no successful fetch, all failures are network → research blocked.
    if network_blocked:
        return base

    # Case 2: nothing fetched at all.
    if not fetched:
        base.update({
            "research_status": "requires_manual_review",
            "research_completion_status": "fetch_incomplete",
        })
        return base

    # Case 3: fetched but not yet reviewed.
    if not reviewed:
        base.update({
            "research_status": "fetched_pending_manual_review",
            "research_completion_status": "fetched_pending_review",
            "recommended_next_step": "manual_content_review_required",
        })
        return base

    # Research was completed (fetched AND reviewed). One finalized evidence set
    # drives both the candidate columns and the dominant status.
    fin = finalize_reviewed_evidence_set(reviewed, snapshot_root)
    cbe = fin["candidates_by_event"]
    conflict_info = fin["conflict_info"]
    canon = fin["canonical_decision"]

    def _cand(event):
        c = cbe.get(event)
        return c["date"] if (c and not c["conflict"] and c["date"]) else ""

    def _cand_precision(event):
        c = cbe.get(event)
        return c["precision"] if (c and not c["conflict"] and c["date"]) else "unknown"

    # (Problem four) Build ALL candidate columns first, independently and
    # simultaneously — no early return may drop another event's candidate.
    base["admission_date_candidate_jalali"] = _cand("admission")
    base["listing_date_candidate_jalali"] = _cand("listing")
    base["first_public_offering_date_candidate_jalali"] = _cand("first_public_offering")
    base["first_public_trading_date_candidate_jalali"] = _cand("first_public_trading")

    has_admission = bool(_cand("admission"))
    has_listing = bool(_cand("listing"))
    has_conversion = bool(_cand("public_company_conversion"))

    # Partial offering/trading candidates (no exact canonical), earliest first.
    partial_pe = []
    for event in ("first_public_offering", "first_public_trading"):
        c = cbe.get(event)
        if c and not c["conflict"] and c["date"] and c["precision"] in ("month_only", "year_only"):
            partial_pe.append((event, c["date"], c["precision"]))

    def _partial_sort_key(item):
        event, date, _prec = item
        iv = _jalali_interval(date, _prec)
        start = iv[0] if iv else date
        ev_rank = 0 if event == "first_public_offering" else 1
        return (start, ev_rank)
    partial_pe.sort(key=_partial_sort_key)

    # ---- Dominant status (candidate columns above are always preserved) ----

    # 1. Same-event conflict.
    if conflict_info["conflict"]:
        etypes = conflict_info["event_types"]
        base.update({
            "candidate_event_type": "conflict",
            "proposed_canonical_event_type": "unresolved",
            "evidence_status": "requires_manual_review",
            "research_status": "research_completed_conflict",
            "research_completion_status": "completed_conflict",
            "conflict_flag": "true",
            "conflict_dates": "; ".join(conflict_info["dates"]),
            "conflict_reason": (
                "conflicting " + ", ".join(etypes) + " dates across sources"),
            "recommended_next_step": "resolve_conflicting_evidence",
        })
        return base

    # 2. An earlier partial public-entry candidate blocks a later exact candidate.
    if canon["blocked_by_partial"]:
        base.update({
            "candidate_event_type": canon["blocking_partial_event"],
            "proposed_canonical_event_type": "",
            "proposed_canonical_public_entry_date_jalali": "",
            "date_precision": canon["blocking_partial_precision"],
            "evidence_status": "requires_manual_review",
            "research_status": "research_completed_partial_public_entry_date",
            "research_completion_status": "completed_partial_evidence",
            "recommended_next_step": "find_exact_public_entry_day",
        })
        return base

    # 3. Earliest exact public-entry candidate WITH source sufficiency → ready.
    if canon["ready"]:
        base.update({
            "candidate_event_type": canon["canonical_event"],
            "proposed_canonical_public_entry_date_jalali": canon["canonical_date"],
            "proposed_canonical_event_type": canon["canonical_event"],
            "date_precision": "exact_day",
            "ordinary_share_confirmed": "true",
            "evidence_status": "candidate_supported",
            "research_status": "candidate_supported",
            "research_completion_status": "completed_with_evidence",
            "ready_for_user_review": "true",
            "recommended_next_step": "recommend_user_review",
        })
        return base

    # 4. Earliest exact public-entry candidate WITHOUT source sufficiency.
    if canon["has_exact_candidate"]:
        base.update({
            "candidate_event_type": canon["earliest_event"],
            "proposed_canonical_event_type": "",
            "proposed_canonical_public_entry_date_jalali": "",
            "date_precision": "exact_day",
            "evidence_status": "requires_manual_review",
            "research_status": "research_completed_exact_public_entry_needs_corroboration",
            "research_completion_status": "completed_exact_candidate_needs_corroboration",
            "recommended_next_step": "find_qualifying_corroboration",
        })
        return base

    # 5. Partial offering/trading evidence (no exact candidate).
    if partial_pe:
        event, _date, prec = partial_pe[0]
        base.update({
            "candidate_event_type": event,
            "proposed_canonical_event_type": "",
            "proposed_canonical_public_entry_date_jalali": "",
            "date_precision": prec,
            "evidence_status": "requires_manual_review",
            "research_status": "research_completed_partial_public_entry_date",
            "research_completion_status": "completed_partial_evidence",
            "recommended_next_step": "find_exact_public_entry_day",
        })
        return base

    # 6. Listing evidence (admission candidate, if any, is already preserved).
    if has_listing:
        base.update({
            "candidate_event_type": "listing",
            "date_precision": _cand_precision("listing"),
            "evidence_status": "requires_first_public_trade_evidence",
            "research_status": "research_completed_listing_only",
            "research_completion_status": "completed_listing_only",
            "recommended_next_step": "find_first_public_offering_or_trading",
        })
        return base

    # 7. Admission evidence.
    if has_admission:
        base.update({
            "candidate_event_type": "admission",
            "date_precision": _cand_precision("admission"),
            "evidence_status": "requires_first_public_trade_evidence",
            "research_status": "research_completed_admission_only",
            "research_completion_status": "completed_admission_only",
            "recommended_next_step": "find_first_public_offering_or_trading",
        })
        return base

    # 8. Public-company conversion only.
    if has_conversion:
        base.update({
            "candidate_event_type": "public_company_conversion",
            "proposed_canonical_event_type": "",
            "proposed_canonical_public_entry_date_jalali": "",
            "date_precision": _cand_precision("public_company_conversion"),
            "evidence_status": "requires_manual_review",
            "research_status": "research_completed_noncanonical_entry_evidence",
            "research_completion_status": "completed_noncanonical_evidence",
            "recommended_next_step": "find_first_public_offering_or_trading",
        })
        return base

    # 9. No valid reviewed entry evidence at all → no_reliable_evidence.
    base.update({
        "evidence_status": "no_reliable_evidence",
        "research_status": "research_completed_no_evidence",
        "research_completion_status": "completed_no_eligibility_evidence",
        "recommended_next_step": "manual_research_required",
    })
    return base


def build_research_screening(company_names: dict, provenance_by_ticker: dict,
                             tsetmc: dict) -> pd.DataFrame:
    """Build research screening *only* from recomputed provenance records.

    ``provenance_by_ticker`` must be the normalized/overlaid provenance records
    (grouped by ticker) — never raw, pre-recomputation fetch fields. No canonical
    or ready decision is made from anything but these recomputed records."""
    rows = []
    for tk in PART03_TICKERS:
        recs = provenance_by_ticker.get(tk, [])
        st = _derive_screening_status(recs, snapshot_root=ROOT)
        # primary/secondary are the first two sources by ascending source_index,
        # taken from the recomputed provenance — not any hardcoded list.
        ordered = sorted(
            recs,
            key=lambda r: int(str(r.get("source_index", "0")).strip() or 0)
            if str(r.get("source_index", "0")).strip().isdigit() else 0)
        def _src_tuple(rec):
            return (str(rec.get("source_type", "")), str(rec.get("source_title", "")),
                    str(rec.get("source_url", "")))
        src1 = _src_tuple(ordered[0]) if len(ordered) > 0 else ("", "", "")
        src2 = _src_tuple(ordered[1]) if len(ordered) > 1 else ("", "", "")
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
            "admission_date_candidate_jalali": st.get("admission_date_candidate_jalali", ""),
            "listing_date_candidate_jalali": st.get("listing_date_candidate_jalali", ""),
            "first_public_offering_date_candidate_jalali": st.get("first_public_offering_date_candidate_jalali", ""),
            "first_public_trading_date_candidate_jalali": st.get("first_public_trading_date_candidate_jalali", ""),
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
    """Build the final provenance DataFrame, recomputing every derived field from
    the URL/content so a manually-supplied value can never override the engine.
    Accepts a ``{ticker: [record, ...]}`` mapping (raw retrieval or overlaid)."""
    flat = []
    for tk in PART03_TICKERS:
        flat.extend(fetch_results.get(tk, []))
    normalized = normalize_provenance_records(flat, snapshot_root)
    return pd.DataFrame(normalized, columns=PROVENANCE_COLUMNS)


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


# Only these worklist columns may be refreshed from current status; every other
# column (manual research findings) is preserved verbatim.
WORKLIST_REFRESHABLE = {"company_name", "current_research_status", "network_blocked"}
# Manual columns that must never be cleared by a refresh.
WORKLIST_PROTECTED = [
    "discovered_source_1_url", "discovered_source_2_url",
    "first_public_event_candidate", "candidate_date_jalali", "date_precision",
    "ordinary_share_explicit", "conflict_notes", "manual_review_status",
    "reviewer_notes",
]


def merge_existing_worklist_with_current_status(template_df: pd.DataFrame,
                                                existing_df: pd.DataFrame) -> pd.DataFrame:
    """Preserve a pre-existing worklist's manual data, refreshing only the
    computed status columns. Matching is by ticker; a ticker added, removed, or
    duplicated relative to Part 3 scope is fail-closed."""
    if existing_df is None or getattr(existing_df, "empty", True):
        return template_df.copy()
    ex_tickers = [str(t) for t in existing_df["ticker"].tolist()]
    if len(ex_tickers) != len(set(ex_tickers)):
        raise ValueError("worklist has duplicate tickers")
    if sorted(ex_tickers) != sorted(PART03_TICKERS):
        raise ValueError("worklist ticker set does not match Part 3 scope")
    ex_by = {str(r["ticker"]): r for _, r in existing_df.iterrows()}
    rows = []
    for _, t in template_df.iterrows():
        tk = str(t["ticker"])
        ex = ex_by[tk]
        row = {}
        for c in WORKLIST_COLUMNS:
            if c in WORKLIST_REFRESHABLE:
                row[c] = str(t.get(c, ""))
            elif c in existing_df.columns:
                row[c] = str(ex.get(c, t.get(c, "")))
            else:
                row[c] = str(t.get(c, ""))
        rows.append(row)
    return pd.DataFrame(rows, columns=WORKLIST_COLUMNS)


# ---- QC (fail-closed, computed from real output) -------------------------------
def _qc_engine_invariants(check) -> None:
    """Deterministic engine-invariant assertions that need no network and no
    files (snapshot_root=None skips on-disk hash checks). They lock the canonical
    selection, conflict grouping, candidate aggregation and finalizer behaviour."""
    OFF = "first_public_offering"
    TRD = "first_public_trading"
    codal = "https://www.codal.ir/Reports/Decision.aspx?LetterSerial="
    aggr = "https://aggregator-example.ir/co/12345/ipo-report-page"

    def syn(idx, event, date, url=None, source_type="codal_official",
            ordinary="true", exact="true"):
        return {
            "ticker": "SYN", "source_index": idx,
            "source_type": source_type,
            "source_url": url if url is not None else f"{codal}SYN{idx}",
            "retrieval_status": "fetched_ok", "content_sha256": "a" * 64,
            "snapshot_path": "stage124/batch02_parts/snapshots_part03/syn.html",
            "content_review_status": "reviewed", "event_type_supported": event,
            "exact_date_explicit": exact, "reviewed_date_jalali": date,
            "ordinary_share_explicit": ordinary, "independent_source_group": "",
        }

    # different canonical events with different dates are NOT a conflict.
    mixed = finalize_reviewed_evidence_set(
        [syn(1, OFF, "1380-03-15"), syn(2, TRD, "1381-06-20")], None)
    check("different_canonical_events_not_conflict",
          not mixed["conflict_info"]["conflict"],
          "offering vs trading different dates must not conflict")

    # two incompatible same-event candidates ARE a conflict.
    same = finalize_reviewed_evidence_set(
        [syn(1, OFF, "1380-03-15"), syn(2, OFF, "1381-06-20")], None)
    check("same_event_conflict_only",
          same["conflict_info"]["conflict"]
          and not mixed["conflict_info"]["conflict"],
          "conflict must arise only within the same event")

    # best candidate prefers highest precision (admission year + exact → exact).
    adm = finalize_reviewed_evidence_set(
        [syn(1, "admission", "1380", exact="false"),
         syn(2, "admission", "1380-05-10")], None)
    cadm = adm["candidates_by_event"].get("admission", {})
    check("best_candidate_uses_highest_precision",
          cadm.get("date") == "1380-05-10" and cadm.get("precision") == "exact_day",
          f"got={cadm}")

    # deterministic under shuffled input order.
    adm_rev = finalize_reviewed_evidence_set(
        [syn(2, "admission", "1380-05-10"),
         syn(1, "admission", "1380", exact="false")], None)
    check("candidate_selection_deterministic",
          adm_rev["candidates_by_event"].get("admission", {}).get("date")
          == "1380-05-10",
          "candidate must not depend on record order")

    # earliest exact public event is selected (trading 1380 before offering 1381).
    early = decide_canonical_public_entry_candidate(
        [syn(1, OFF, "1381-05-05"), syn(2, TRD, "1380-02-02")], None)
    check("earliest_exact_public_event_selected",
          early["earliest_event"] == TRD and early["canonical_date"] == "1380-02-02"
          and early["ready"] is True,
          f"got={early}")

    # a later, qualified candidate cannot override an earlier, unqualified one.
    later = _derive_screening_status(
        [syn(1, OFF, "1380-03-15", url=aggr, source_type=""),
         syn(2, TRD, "1381-06-20")], snapshot_root=None)
    check("later_qualified_candidate_cannot_override_earlier_unqualified_candidate",
          later["research_status"]
          == "research_completed_exact_public_entry_needs_corroboration"
          and later["candidate_event_type"] == OFF
          and later["proposed_canonical_public_entry_date_jalali"] == ""
          and later["first_public_trading_date_candidate_jalali"] == "1381-06-20",
          f"got={later['research_status']}")

    # an exact candidate with an insufficient source is NOT no_reliable_evidence.
    weak = _derive_screening_status(
        [syn(1, OFF, "1380-03-15", url=aggr, source_type="")], snapshot_root=None)
    check("exact_unqualified_not_no_reliable_evidence",
          weak["evidence_status"] != "no_reliable_evidence",
          f"es={weak['evidence_status']}")
    check("exact_candidate_needs_corroboration_not_ready",
          weak["research_status"]
          == "research_completed_exact_public_entry_needs_corroboration"
          and weak["ready_for_user_review"] == "false",
          f"got={weak['research_status']}")
    check("qc_report_regenerated_from_current_engine",
          weak["research_completion_status"]
          == "completed_exact_candidate_needs_corroboration",
          "current engine must emit the 3.1A.5.2 corroboration status")

    # an earlier partial blocks a later exact; a compatible partial does not.
    blocked = decide_canonical_public_entry_candidate(
        [syn(1, OFF, "1380", exact="false"), syn(2, TRD, "1381-04-10")], None)
    check("earlier_partial_blocks_later_exact", blocked["blocked_by_partial"] is True,
          f"got={blocked}")
    compat = decide_canonical_public_entry_candidate(
        [syn(1, OFF, "1380-03", exact="false"), syn(2, OFF, "1380-03-15")], None)
    check("compatible_partial_does_not_block_exact",
          compat["blocked_by_partial"] is False
          and compat["has_exact_candidate"] is True,
          f"got={compat}")

    # the finalizer is idempotent (roles + candidates stable on re-run).
    recs = [syn(1, OFF, "1380-03-15"), syn(2, OFF, "1381-06-20"),
            syn(3, "admission", "1379-01-01")]
    f1 = finalize_reviewed_evidence_set(recs, None)
    f2 = finalize_reviewed_evidence_set(f1["finalized_records"], None)
    roles1 = [fr["_final_evidence_role"] for fr in f1["finalized_records"]]
    roles2 = [fr["_final_evidence_role"] for fr in f2["finalized_records"]]
    cand1 = {k: (v["date"], v["precision"], v["conflict"])
             for k, v in f1["candidates_by_event"].items()}
    cand2 = {k: (v["date"], v["precision"], v["conflict"])
             for k, v in f2["candidates_by_event"].items()}
    check("finalizer_idempotent", roles1 == roles2 and cand1 == cand2,
          f"roles1={roles1}, roles2={roles2}")


def _nj(value: str) -> str:
    """normalize_jalali that never raises (returns the stripped input on a value
    that is not a well-formed 3-part Jalali date — e.g. empty, year, or month)."""
    try:
        return normalize_jalali(value)
    except Exception:
        return str(value or "").strip()


def run_part03_qc(tickers_df: pd.DataFrame, research_df: pd.DataFrame,
                  provenance_df: pd.DataFrame, tsetmc_df: pd.DataFrame,
                  frozen_before: dict, frozen_after: dict,
                  part02_before: dict, part02_after: dict,
                  worklist_df: pd.DataFrame = None,
                  registry_df: pd.DataFrame = None) -> dict:
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

    # Allowed enums come from the single, exported source of truth.
    prov_by_tk = {tk: provenance_df[provenance_df["ticker"] == tk]
                  for tk in PART03_TICKERS}

    # One finalized evidence set per ticker drives the conflict-aware role and the
    # candidate columns. QC compares against THIS (not a single-record evaluation).
    final_role_by_key = {}
    final_candidates_by_tk = {}
    final_fin_by_tk = {}
    for tk in PART03_TICKERS:
        sub = prov_by_tk.get(tk)
        recs = ([{k: pr.get(k, "") for k in pr.index} for _, pr in sub.iterrows()]
                if sub is not None and not sub.empty else [])
        fin = finalize_reviewed_evidence_set(recs, snapshot_root=ROOT)
        for fr in fin["finalized_records"]:
            final_role_by_key[(str(fr.get("ticker", "")),
                               str(fr.get("source_index", "")).strip())] = \
                fr["evidence_role"]
        final_candidates_by_tk[tk] = fin["candidates_by_event"]
        final_fin_by_tk[tk] = fin

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

        # Enum validation.
        check(f"research_status_valid_enum_{tk}",
              rstatus in ALLOWED_RESEARCH_STATUSES,
              f"research_status={rstatus}")
        check(f"evidence_status_valid_enum_{tk}",
              es in ALLOWED_EVIDENCE_STATUSES,
              f"evidence_status={es}")

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

        # The canonical date must come ONLY from an exact-day offering/trading
        # candidate selected by the canonical engine — never from a non-canonical
        # event. Admission/listing/conversion may coexist with a valid canonical
        # without invalidating it.
        fin_tk = final_fin_by_tk.get(tk, {})
        canon_tk = fin_tk.get("canonical_decision", {}) if fin_tk else {}
        if cand:
            noncanonical_ok = (
                ev in CANONICAL_EVENT_TYPES
                and canon_tk.get("ready") is True
                and _nj(cand) == _nj(canon_tk.get("canonical_date", ""))
                and ev == canon_tk.get("canonical_event", ""))
        else:
            noncanonical_ok = True
        check(f"canonical_not_derived_from_noncanonical_event_{tk}", noncanonical_ok,
              "canonical date/event must equal the canonical engine's exact-day "
              "offering/trading decision; admission/listing/conversion never "
              "produce a canonical")

        # month/year/unknown precision → not ready
        if dp in ("month_only", "year_only", "unknown"):
            check(f"non_exact_not_ready_{tk}", ready == "false",
                  f"dp={dp}, ready={ready}")

        # conflict unresolved → not ready
        if conflict == "true":
            check(f"conflict_not_ready_{tk}", ready == "false",
                  f"ready={ready}")

        # ready=true requires exact-day canonical + fetched, hash-backed source,
        # validated SOLELY by the new canonical decision engine.
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

            # ready=true must be reproducible by the unified canonical engine:
            # earliest exact candidate, sufficient sources, no conflict, no blocker.
            check(f"ready_requires_canonical_decision_{tk}",
                  canon_tk.get("ready") is True,
                  f"canon_reason={canon_tk.get('reason')}")
            check(f"ready_canonical_date_matches_{tk}",
                  _nj(cand) == _nj(canon_tk.get("canonical_date", "")),
                  f"research={cand}, canon={canon_tk.get('canonical_date')}")
            check(f"ready_canonical_event_matches_{tk}",
                  ev == canon_tk.get("canonical_event", ""),
                  f"research={ev}, canon={canon_tk.get('canonical_event')}")
            check(f"ready_canonical_is_earliest_{tk}",
                  _nj(canon_tk.get("canonical_date", ""))
                  == _nj(canon_tk.get("earliest_date", "")),
                  "canonical must be the earliest exact candidate")
            check(f"ready_no_partial_blocker_{tk}",
                  canon_tk.get("blocked_by_partial") is False,
                  "ready must have no earlier-partial blocker")
            check(f"ready_no_conflict_{tk}",
                  not fin_tk.get("conflict_info", {}).get("conflict", False),
                  "ready must have no same-event conflict")

        # gregorian conversion of canonical — recomputed independently of Jalali.
        cg = str(r["proposed_canonical_public_entry_date_gregorian"]).strip()
        if not cand:
            check(f"gregorian_empty_when_no_canonical_{tk}", cg == "",
                  f"gregorian={cg} but canonical Jalali empty")
        else:
            try:
                expected_g = jalali_to_gregorian_str(cand)
                check(f"date_conversion_ok_{tk}", cg == expected_g,
                      f"j={cand}, g={cg}, expected={expected_g}")
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

        # reviewed-evidence derived fields must match engine recomputation.
        rev_eval = evaluate_reviewed_evidence_record(rec_dict, snapshot_root=ROOT)
        check(f"reviewed_event_type_matches_engine_{tk}_{idx}",
              str(pr.get("reviewed_event_type", "")).strip() == rev_eval["reviewed_event_type"],
              f"stored={pr.get('reviewed_event_type')}, computed={rev_eval['reviewed_event_type']}")
        check(f"reviewed_date_precision_matches_engine_{tk}_{idx}",
              str(pr.get("reviewed_date_precision", "")).strip() == rev_eval["reviewed_date_precision"],
              f"stored={pr.get('reviewed_date_precision')}, computed={rev_eval['reviewed_date_precision']}")
        check(f"reviewed_evidence_valid_matches_engine_{tk}_{idx}",
              str(pr.get("reviewed_evidence_valid", "")).strip().lower() ==
              ("true" if rev_eval["reviewed_evidence_valid"] else "false"),
              f"stored={pr.get('reviewed_evidence_valid')}, computed={rev_eval['reviewed_evidence_valid']}")
        # evidence_role must match the FINALIZED (conflict-aware) role, not just
        # the single-record base role — a conflicting record is conflicting_evidence.
        final_role = final_role_by_key.get(
            (str(tk), str(idx).strip()), rev_eval["evidence_role"])
        check(f"evidence_role_matches_engine_{tk}_{idx}",
              str(pr.get("evidence_role", "")).strip() == final_role,
              f"stored={pr.get('evidence_role')}, finalized={final_role}")
        check(f"conflicting_role_matches_finalized_engine_{tk}_{idx}",
              str(pr.get("evidence_role", "")).strip() == final_role,
              f"stored={pr.get('evidence_role')}, finalized={final_role}")
        # evidence_role must be a valid enum.
        check(f"evidence_role_valid_enum_{tk}_{idx}",
              str(pr.get("evidence_role", "")).strip() in EVIDENCE_ROLES,
              f"evidence_role={pr.get('evidence_role')}")
        # reviewed_date_precision must be a valid enum.
        check(f"reviewed_date_precision_valid_enum_{tk}_{idx}",
              str(pr.get("reviewed_date_precision", "")).strip() in REVIEWED_DATE_PRECISIONS,
              f"reviewed_date_precision={pr.get('reviewed_date_precision')}")
        # reviewed_event_type must be a valid enum (or empty).
        check(f"reviewed_event_type_valid_enum_{tk}_{idx}",
              str(pr.get("reviewed_event_type", "")).strip() in REVIEWED_EVENT_TYPES
              or str(pr.get("reviewed_event_type", "")).strip() == "",
              f"reviewed_event_type={pr.get('reviewed_event_type')}")

        # domain-strict taxonomy: stored authority class must match recomputation,
        # and a validation error forbids acceptance.
        real_url = str(pr.get("source_url", ""))
        rec_cls, rec_verr = classify_source_authority_with_validation(src_type, real_url, str(tk))
        if "source_authority_class" in pr.index:
            check(f"authority_class_matches_engine_{tk}_{idx}",
                  str(pr.get("source_authority_class", "")).strip() == rec_cls,
                  f"stored={pr.get('source_authority_class')}, computed={rec_cls}")
        if rec_verr:
            check(f"authority_error_blocks_acceptance_{tk}_{idx}",
                  not _truthy(pr.get("evidence_accepted", "")),
                  f"validation_error present but evidence_accepted="
                  f"{pr.get('evidence_accepted')}")

        # TSETMC / market-data audit is never accepted evidence.
        if rec_cls == "official_market_data_audit":
            check(f"market_data_not_accepted_{tk}_{idx}",
                  not _truthy(pr.get("evidence_accepted", "")),
                  "official_market_data_audit must never be evidence_accepted")

        # a reviewed record must carry a valid snapshot + matching hash.
        review_status = str(pr.get("content_review_status", "")).strip().lower()
        if review_status == "reviewed":
            sp2 = PART03_DIR.parent.parent / snap if snap else None
            ok = (status in FETCHED_STATUSES and snap != "" and _is_sha256(h)
                  and sp2 is not None and sp2.exists()
                  and hashlib.sha256(sp2.read_bytes()).hexdigest() == h.lower())
            check(f"reviewed_requires_valid_snapshot_{tk}_{idx}", ok,
                  f"reviewed but snapshot/hash invalid (status={status})")

        # a stale-invalidated review must be cleared and never accepted.
        if review_status == "stale_review_invalidated":
            check(f"stale_review_not_accepted_{tk}_{idx}",
                  not _truthy(pr.get("evidence_accepted", "")),
                  "stale_review_invalidated must not be evidence_accepted")
            check(f"stale_review_cleared_{tk}_{idx}",
                  str(pr.get("event_type_supported", "")).strip() == ""
                  and str(pr.get("reviewed_date_jalali", "")).strip() == "",
                  "stale_review_invalidated must clear manual review fields")

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

    # research screening must be exactly reproducible from the recomputed
    # provenance (it must not depend on any pre-recomputation fetch fields).
    research_by_tk = {r["ticker"]: r for _, r in research_df.iterrows()}
    for tk in PART03_TICKERS:
        sub = prov_by_tk.get(tk)
        recs = ([{k: pr.get(k, "") for k in pr.index} for _, pr in sub.iterrows()]
                if sub is not None and not sub.empty else [])
        derived = _derive_screening_status(recs, snapshot_root=ROOT)
        r = research_by_tk.get(tk)
        if r is None:
            check(f"research_from_provenance_{tk}", False, "missing research row")
            continue
        # Every important derived field must match _derive_screening_status exactly.
        compare_fields = (
            "candidate_event_type",
            "proposed_canonical_public_entry_date_jalali",
            "proposed_canonical_event_type", "date_precision",
            "ordinary_share_confirmed", "evidence_status", "research_status",
            "research_completion_status", "network_blocked",
            "attempted_source_count", "fetched_source_count",
            "reviewed_source_count", "evidence_source_count",
            "ready_for_user_review", "conflict_flag", "conflict_dates",
            "conflict_reason", "recommended_next_step",
            "admission_date_candidate_jalali", "listing_date_candidate_jalali",
            "first_public_offering_date_candidate_jalali",
            "first_public_trading_date_candidate_jalali")
        mismatched = [f for f in compare_fields
                      if str(r.get(f, "")).strip() != str(derived.get(f, "")).strip()]
        check(f"research_from_provenance_{tk}", not mismatched,
              f"mismatched fields={mismatched}")

        # candidate columns must equal the finalizer's per-event candidates.
        cbe = final_candidates_by_tk.get(tk, {})
        def _exp(event):
            c = cbe.get(event)
            return c["date"] if (c and not c["conflict"] and c["date"]) else ""
        cols_ok = all(str(r.get(col, "")).strip() == _exp(event)
                      for col, event in (
                          ("admission_date_candidate_jalali", "admission"),
                          ("listing_date_candidate_jalali", "listing"),
                          ("first_public_offering_date_candidate_jalali",
                           "first_public_offering"),
                          ("first_public_trading_date_candidate_jalali",
                           "first_public_trading")))
        check(f"all_candidate_columns_match_provenance_{tk}", cols_ok,
              "candidate columns must equal the finalized per-event candidates")

        fin_tk = final_fin_by_tk.get(tk, {})
        canon_tk = fin_tk.get("canonical_decision", {})
        conflict_tk = fin_tk.get("conflict_info", {})
        entry_events = ("first_public_offering", "first_public_trading",
                        "admission", "listing", "public_company_conversion")
        es_row = str(r.get("evidence_status", "")).strip()
        rstat = str(r.get("research_status", "")).strip()
        rnext = str(r.get("recommended_next_step", "")).strip()
        rready = str(r.get("ready_for_user_review", "")).strip().lower()
        rev_field = str(r.get("proposed_canonical_event_type", "")).strip()
        rcand = str(r.get("proposed_canonical_public_entry_date_jalali", "")).strip()

        # --- Status-specific semantic QC (works on any future real output) ---
        if rstat == "research_completed_exact_public_entry_needs_corroboration":
            ce = str(r.get("candidate_event_type", "")).strip()
            col = (str(r.get("first_public_offering_date_candidate_jalali", "")).strip()
                   if ce == "first_public_offering"
                   else str(r.get("first_public_trading_date_candidate_jalali", "")).strip())
            check(f"status_needs_corroboration_semantics_{tk}",
                  bool(col) and str(r.get("date_precision", "")).strip() == "exact_day"
                  and rcand == "" and rev_field == "" and rready == "false"
                  and es_row == "requires_manual_review"
                  and rnext == "find_qualifying_corroboration",
                  "exact-needs-corroboration semantics")
        elif rstat == "research_completed_partial_public_entry_date":
            off = str(r.get("first_public_offering_date_candidate_jalali", "")).strip()
            trd = str(r.get("first_public_trading_date_candidate_jalali", "")).strip()
            check(f"status_partial_semantics_{tk}",
                  (bool(off) or bool(trd)) and rcand == "" and rready == "false"
                  and es_row == "requires_manual_review"
                  and rnext == "find_exact_public_entry_day",
                  "partial-public-entry semantics")
        elif rstat == "research_completed_admission_only":
            check(f"status_admission_only_semantics_{tk}",
                  str(r.get("admission_date_candidate_jalali", "")).strip() != ""
                  and rcand == "" and rready == "false"
                  and es_row == "requires_first_public_trade_evidence",
                  "admission-only semantics")
        elif rstat == "research_completed_listing_only":
            check(f"status_listing_only_semantics_{tk}",
                  str(r.get("listing_date_candidate_jalali", "")).strip() != ""
                  and rcand == "" and rready == "false"
                  and es_row == "requires_first_public_trade_evidence",
                  "listing-only semantics")
        elif rstat == "research_completed_noncanonical_entry_evidence":
            check(f"status_conversion_semantics_{tk}",
                  ("public_company_conversion" in cbe
                   and not cbe["public_company_conversion"]["conflict"])
                  and rcand == "" and rready == "false"
                  and es_row == "requires_manual_review",
                  "noncanonical-entry (conversion) semantics")
        elif rstat == "research_completed_conflict":
            check(f"status_conflict_semantics_{tk}",
                  str(r.get("conflict_flag", "")).strip().lower() == "true"
                  and rcand == "" and rev_field == "unresolved" and rready == "false"
                  and es_row == "requires_manual_review",
                  "conflict semantics")
        elif rstat == "candidate_supported":
            check(f"status_candidate_supported_semantics_{tk}",
                  str(r.get("date_precision", "")).strip() == "exact_day"
                  and rev_field in CANONICAL_EVENT_TYPES
                  and str(r.get("ordinary_share_confirmed", "")).strip().lower() == "true"
                  and rready == "true"
                  and str(r.get("conflict_flag", "")).strip().lower() == "false"
                  and canon_tk.get("ready") is True and canon_tk.get("sufficient") is True,
                  "candidate_supported semantics")

        # --- no_reliable_evidence hardening: only with no entry evidence of any
        # kind, no conflict, no exact candidate, all entry candidates empty. ---
        if es_row == "no_reliable_evidence":
            has_entry = any(ev2 in cbe and not cbe[ev2]["conflict"] and cbe[ev2]["date"]
                            for ev2 in entry_events)
            check(f"no_reliable_only_when_no_valid_entry_evidence_{tk}",
                  (not has_entry)
                  and not conflict_tk.get("conflict", False)
                  and not canon_tk.get("has_exact_candidate", False),
                  "no_reliable_evidence requires no conflict, no exact candidate "
                  "and no entry-event candidate")

    # ---- engine-invariant checks (deterministic, no network, no files) ----
    _qc_engine_invariants(check)

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

    # Source registry: validity + forward-compatible seed preservation + a strict
    # one-to-one mapping between *active* registry rows and provenance. The
    # registry may legitimately grow beyond 20 rows (manual-discovery sources at
    # source_index 3, 4, …); only the original 20 seeds are locked.
    if registry_df is not None:
        reg_ok, reg_errs = validate_source_registry(registry_df)
        check("registry_valid", reg_ok, f"errors={reg_errs[:3]}")

        seed_df = build_seed_registry_df()
        seed_by_key = {(str(r["ticker"]), str(r["source_index"]).strip()):
                       (str(r["source_type"]), str(r["source_title"]),
                        str(r["source_url"]), str(r["source_origin"]))
                       for _, r in seed_df.iterrows()}
        reg_by_key = {(str(r["ticker"]), str(r["source_index"]).strip()):
                      (str(r.get("source_type", "")), str(r.get("source_title", "")),
                       str(r.get("source_url", "")), str(r.get("source_origin", "")))
                      for _, r in registry_df.iterrows()}

        # 1) all 20 seed keys still present
        missing_seed = set(seed_by_key) - set(reg_by_key)
        check("registry_seed_20_preserved",
              len(seed_by_key) == 20 and not missing_seed,
              f"missing_seed={missing_seed}")
        # 2) seed keys are exactly the 10 tickers × source_index {1,2}
        expected_seed_keys = {(tk, str(i)) for tk in PART03_TICKERS for i in (1, 2)}
        check("registry_seed_keys_preserved",
              set(seed_by_key) == expected_seed_keys,
              f"seed_keys={sorted(set(seed_by_key) - expected_seed_keys)}")
        # 3) seed type/title/url/source_origin unchanged
        content_ok = all(reg_by_key.get(k) == v for k, v in seed_by_key.items())
        check("registry_seed_content_unchanged", content_ok,
              "seed type/title/url/source_origin must not change")
        # 4) each ticker has at least two seed sources (not exactly two total)
        seed_per_tk = {}
        for (tk, _si) in seed_by_key:
            seed_per_tk[tk] = seed_per_tk.get(tk, 0) + 1
        check("registry_minimum_two_seed_sources_each",
              all(seed_per_tk.get(tk, 0) >= 2 for tk in PART03_TICKERS),
              f"seed_counts={seed_per_tk}")
        # 5) additional (manual_discovery, index>=3) rows are allowed
        extra_rows = [
            (str(r["ticker"]), str(r["source_index"]).strip(),
             str(r.get("source_origin", "")))
            for _, r in registry_df.iterrows()
            if (str(r["ticker"]), str(r["source_index"]).strip()) not in seed_by_key]
        bad_extra = [e for e in extra_rows
                     if not (e[1].isdigit() and int(e[1]) >= 3
                             and e[2] == "manual_discovery")]
        check("registry_additional_sources_allowed", not bad_extra,
              f"invalid_extra_rows={bad_extra}")

        # active registry ↔ provenance is one-to-one; inactive rows never appear.
        active_keys = {(str(r["ticker"]), str(r["source_index"]).strip())
                       for _, r in registry_df.iterrows()
                       if str(r.get("active", "")).strip().lower() == "true"}
        inactive_keys = {(str(r["ticker"]), str(r["source_index"]).strip())
                         for _, r in registry_df.iterrows()
                         if str(r.get("active", "")).strip().lower() != "true"}
        prov_keys = {(str(pr["ticker"]), str(pr["source_index"]).strip())
                     for _, pr in provenance_df.iterrows()}
        check("provenance_subset_of_registry", prov_keys <= set(reg_by_key),
              f"orphans={prov_keys - set(reg_by_key)}")
        check("active_registry_matches_provenance", prov_keys == active_keys,
              f"prov_only={prov_keys - active_keys}, active_only={active_keys - prov_keys}")
        check("inactive_registry_not_in_provenance",
              not (inactive_keys & prov_keys),
              f"inactive_in_prov={inactive_keys & prov_keys}")

    # Manual research worklist: semantic validation only. Empty findings are
    # allowed (the template); non-empty findings (Part 3.1B) must be well-formed.
    if worklist_df is not None:
        wl_tickers = [str(t) for t in worklist_df["ticker"].tolist()]
        check("worklist_exact_ticker_scope",
              wl_tickers == list(PART03_TICKERS),
              f"order={wl_tickers}")
        check("worklist_no_duplicates", len(wl_tickers) == len(set(wl_tickers)),
              f"tickers={wl_tickers}")

        url_cols = ["discovered_source_1_url", "discovered_source_2_url"]
        urls_ok = True
        for c in url_cols:
            if c not in worklist_df.columns:
                continue
            for v in worklist_df[c].astype(str):
                if not _worklist_url_ok(v):
                    urls_ok = False
                    break
        check("worklist_discovered_urls_valid", urls_ok,
              "discovered URLs must be empty or valid http(s) with a real host "
              "and no local path")

        dates_ok = all(_worklist_jalali_ok(v)
                       for v in worklist_df.get("candidate_date_jalali",
                                                pd.Series([], dtype=str)).astype(str))
        check("worklist_candidate_date_valid", dates_ok,
              "candidate_date_jalali must be empty or a valid Jalali "
              "year / month / exact-day value")

        # date_precision enum + agreement with candidate_date_jalali
        prec_series = worklist_df.get("date_precision", pd.Series([], dtype=str)).astype(str)
        prec_enum_ok = all(str(v).strip() in WORKLIST_DATE_PRECISIONS
                           for v in prec_series)
        check("worklist_date_precision_enum_valid", prec_enum_ok,
              f"date_precision must be in {sorted(WORKLIST_DATE_PRECISIONS)}")
        if "date_precision" in worklist_df.columns and \
                "candidate_date_jalali" in worklist_df.columns:
            match_ok = all(
                validate_worklist_date_precision(
                    str(r.get("candidate_date_jalali", "")),
                    str(r.get("date_precision", "")))
                for _, r in worklist_df.iterrows())
        else:
            match_ok = False
        check("worklist_date_precision_matches_candidate", match_ok,
              "candidate_date_jalali must agree with date_precision")

        allowed_events = {"", "first_public_offering", "first_public_trading",
                          "admission", "listing", "public_company_conversion",
                          "unresolved"}
        events_ok = all(str(v).strip() in allowed_events
                        for v in worklist_df.get("first_public_event_candidate",
                                                 pd.Series([], dtype=str)).astype(str))
        check("worklist_event_candidate_valid", events_ok,
              f"first_public_event_candidate must be in {sorted(allowed_events)}")

        # ordinary_share_explicit: must be present and a valid enum (empty fails).
        allowed_ord = {"true", "false", "unknown"}
        ord_ok = all(str(v).strip().lower() in allowed_ord
                     for v in worklist_df.get("ordinary_share_explicit",
                                              pd.Series([], dtype=str)).astype(str))
        check("worklist_ordinary_share_value_valid", ord_ok,
              f"ordinary_share_explicit must be in {sorted(allowed_ord)} (non-empty)")

        # manual_review_status: must be present and a valid enum (empty fails).
        allowed_status = {"pending_manual_research", "source_discovered",
                          "under_review", "reviewed", "unresolved"}
        status_ok = all(str(v).strip() in allowed_status
                        for v in worklist_df.get("manual_review_status",
                                                 pd.Series([], dtype=str)).astype(str))
        check("worklist_manual_status_valid", status_ok,
              f"manual_review_status must be in {sorted(allowed_status)} (non-empty)")

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
    tsetmc = load_historical_tsetmc()

    provenance_path = PART03_DIR / "part03_source_provenance_10tickers.csv"

    # The persistent source registry is the source of truth. Seed it the first
    # time from RESEARCH_SOURCES; afterwards it is read as-is (manual additions
    # made via register_discovered_sources persist).
    if not SOURCE_REGISTRY_PATH.exists():
        write_csv(build_seed_registry_df(), SOURCE_REGISTRY_PATH)
    registry_df = load_source_registry()
    ok, reg_errors = validate_source_registry(registry_df)
    if not ok:
        raise ValueError(f"invalid source registry: {reg_errors[:5]}")
    sources_by_ticker = registry_to_research_sources(registry_df, include_inactive=False)

    # Correct data flow:
    #   1) raw retrieval records (from active registry sources)
    #   2) overlay validated manual review from the prior provenance file
    #   3) recompute all derived evidence fields
    #   4) build final provenance
    #   5) build research screening *only* from the recomputed provenance
    retrieval = fetch_sources(timeout=5.0, force=force_fetch,
                              sources_by_ticker=sources_by_ticker)
    existing_prov = None
    if provenance_path.exists():
        try:
            existing_prov = read_csv(provenance_path)
        except Exception:
            existing_prov = None
    overlaid_by_ticker = {
        tk: apply_validated_review_overlay(retrieval.get(tk, []), existing_prov, ROOT)
        for tk in PART03_TICKERS
    }

    provenance_df = build_source_provenance(overlaid_by_ticker)
    research_df = build_research_screening(company_names, overlaid_by_ticker, tsetmc)
    tsetmc_df = build_tsetmc_audit(tsetmc)
    # Worklist: preserve any existing manual findings, refresh only status cols.
    worklist_path = PART03_DIR / "part03_manual_research_worklist.csv"
    worklist_template = build_manual_research_worklist(company_names, research_df)
    existing_worklist = None
    if worklist_path.exists():
        try:
            existing_worklist = read_csv(worklist_path)
        except Exception:
            existing_worklist = None
    worklist_df = merge_existing_worklist_with_current_status(worklist_template,
                                                             existing_worklist)

    tickers_path = PART03_DIR / "part03_tickers.csv"
    research_path = PART03_DIR / "part03_research_screening_10tickers.csv"
    tsetmc_path = PART03_DIR / "part03_tsetmc_audit_10tickers.csv"

    write_csv(research_df, research_path)
    write_csv(provenance_df, provenance_path)
    write_csv(worklist_df, worklist_path)

    part02_after = {str(fp): sha(fp) for fp in PART02_PROTECTED if fp.exists()}
    frozen_after = {str(fp): sha(fp) for fp in FROZEN_FILES if fp.exists()}

    qc = run_part03_qc(tickers_df, research_df, provenance_df, tsetmc_df,
                       frozen_before, frozen_after, part02_before, part02_after,
                       worklist_df=worklist_df, registry_df=registry_df)

    # Record the exact engine + test file fingerprints producing these artifacts.
    src_file = Path(__file__)
    test_file = ROOT / "tests" / "test_stage124_batch02_part03.py"
    source_file_sha256 = sha(src_file) if src_file.exists() else ""
    test_file_sha256 = sha(test_file) if test_file.exists() else ""

    qc_report = {
        "stage": "stage124_batch02_part03",
        "generated_at": _utc_now(),
        "source_commit": source_commit,
        "source_file_sha256": source_file_sha256,
        "test_file_sha256": test_file_sha256,
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
        "source_file_sha256": source_file_sha256,
        "test_file_sha256": test_file_sha256,
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
            for rec in overlaid_by_ticker.get(tk, [])
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
