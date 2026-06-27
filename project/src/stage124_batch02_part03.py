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

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests as _requests

from .stage124_batch02_v2 import (
    normalize_ticker, normalize_jalali, jalali_to_gregorian_str,
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


# ---- helpers -------------------------------------------------------------------
def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
                rec["extraction_notes"] = (
                    f"HTTP {resp.status_code}; {len(body)} bytes; raw snapshot "
                    f"stored; content_sha256 recorded. Page content must be "
                    f"reviewed before any canonical date is proposed.")
            except _requests.exceptions.Timeout:
                rec["retrieval_status"] = "timeout"
                rec["extraction_notes"] = (
                    f"Request timed out after {timeout}s; no snapshot stored; "
                    f"no hash fabricated.")
            except _requests.exceptions.ConnectionError as e:
                rec["retrieval_status"] = "connection_error"
                rec["extraction_notes"] = (
                    f"Connection error; no snapshot stored; no hash fabricated. "
                    f"{str(e)[:160]}")
            except Exception as e:
                rec["retrieval_status"] = "fetch_error"
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
            })
            return True
    elif prov_status in ("timeout", "connection_error", "fetch_error"):
        rec.update({
            "http_status": str(pr.get("http_status", "")),
            "retrieval_status": prov_status,
            "final_url": str(pr.get("final_url", rec["source_url"])),
            "retrieved_at_utc": str(pr.get("retrieved_at_utc", _utc_now())),
            "extraction_notes": str(pr.get("extraction_notes", "")),
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


def _derive_screening_status(fetch_recs: list) -> dict:
    """Derive evidence/precision status from *fetched* evidence only.

    With no successfully fetched-and-reviewed evidence supporting an exact-day
    first public offering/trading event, the record stays unresolved. No date is
    ever guessed; admission/listing-only or aggregator pages never produce a
    canonical date here.
    """
    supported_dates = [
        (r.get("supported_event_type", ""), r.get("supported_date_jalali", ""))
        for r in fetch_recs
        if r.get("retrieval_status") in ("fetched_ok", "reused_existing_snapshot")
        and r.get("content_sha256")
    ]
    canonical_support = [
        d for (ev, d) in supported_dates
        if ev in CANONICAL_EVENT_TYPES and d
    ]
    # No fetched, hash-backed, canonical-event exact-day evidence → unresolved.
    if not canonical_support:
        return {
            "candidate_event_type": "",
            "proposed_canonical_public_entry_date_jalali": "",
            "proposed_canonical_event_type": "",
            "date_precision": "unknown",
            "ordinary_share_confirmed": "false",
            "evidence_status": "no_reliable_evidence",
            "research_status": "no_reliable_evidence",
            "ready_for_user_review": "false",
            "conflict_flag": "false",
            "conflict_dates": "",
            "conflict_reason": "",
            "recommended_next_step": "manual_research_required",
        }
    # Distinct canonical exact-day dates → conflict if more than one.
    distinct = sorted({normalize_jalali(d) for d in canonical_support})
    if len(distinct) > 1:
        return {
            "candidate_event_type": "conflict",
            "proposed_canonical_public_entry_date_jalali": "",
            "proposed_canonical_event_type": "unresolved",
            "date_precision": "exact_day",
            "ordinary_share_confirmed": "true",
            "evidence_status": "requires_manual_review",
            "research_status": "requires_manual_review",
            "ready_for_user_review": "false",
            "conflict_flag": "true",
            "conflict_dates": "; ".join(distinct),
            "conflict_reason": "multiple conflicting exact-day canonical dates",
            "recommended_next_step": "manual_resolution_of_conflicting_dates",
        }
    ev_type = next(ev for (ev, d) in supported_dates if d and ev in CANONICAL_EVENT_TYPES)
    cand = distinct[0]
    return {
        "candidate_event_type": ev_type,
        "proposed_canonical_public_entry_date_jalali": cand,
        "proposed_canonical_event_type": ev_type,
        "date_precision": "exact_day",
        "ordinary_share_confirmed": "true",
        "evidence_status": "candidate_supported",
        "research_status": "candidate_supported",
        "ready_for_user_review": "true",
        "conflict_flag": "false",
        "conflict_dates": "",
        "conflict_reason": "",
        "recommended_next_step": "recommend_user_review",
    }


def build_research_screening(company_names: dict, fetch_results: dict,
                             tsetmc: dict) -> pd.DataFrame:
    rows = []
    for tk in PART03_TICKERS:
        recs = fetch_results.get(tk, [])
        st = _derive_screening_status(recs)
        srcs = RESEARCH_SOURCES.get(tk, [])
        src1 = srcs[0] if len(srcs) > 0 else ("", "", "")
        src2 = srcs[1] if len(srcs) > 1 else ("", "", "")
        ts = tsetmc.get(tk, {})
        cand_j = st["proposed_canonical_public_entry_date_jalali"]
        notes = []
        if st["evidence_status"] == "no_reliable_evidence":
            notes.append("no fetched evidence captured; sources unreachable")
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


def build_source_provenance(fetch_results: dict) -> pd.DataFrame:
    rows = []
    for tk in PART03_TICKERS:
        for rec in fetch_results.get(tk, []):
            rows.append(dict(rec))
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


# ---- QC (fail-closed, computed from real output) -------------------------------
def run_part03_qc(tickers_df: pd.DataFrame, research_df: pd.DataFrame,
                  provenance_df: pd.DataFrame, tsetmc_df: pd.DataFrame,
                  frozen_before: dict, frozen_after: dict,
                  part02_before: dict, part02_after: dict) -> dict:
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
                  and es == "candidate_supported" and cand != "")
            check(f"ready_requires_exact_canonical_{tk}", ok,
                  f"dp={dp}, ev={ev}, es={es}, cand={cand}")
            sub = prov_by_tk.get(tk)
            has_evidence = False
            if sub is not None and not sub.empty:
                for _, pr in sub.iterrows():
                    if (str(pr.get("retrieval_status")) in ("fetched_ok", "reused_existing_snapshot")
                            and str(pr.get("content_sha256")).strip()):
                        has_evidence = True
                        break
            check(f"ready_requires_fetched_source_with_hash_{tk}", has_evidence,
                  "ready=true requires a fetched source with a real SHA-256")

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

    tickers_path = PART03_DIR / "part03_tickers.csv"
    research_path = PART03_DIR / "part03_research_screening_10tickers.csv"
    provenance_path = PART03_DIR / "part03_source_provenance_10tickers.csv"
    tsetmc_path = PART03_DIR / "part03_tsetmc_audit_10tickers.csv"

    write_csv(tickers_df, tickers_path)
    write_csv(research_df, research_path)
    write_csv(provenance_df, provenance_path)
    write_csv(tsetmc_df, tsetmc_path)

    part02_after = {str(fp): sha(fp) for fp in PART02_PROTECTED if fp.exists()}
    frozen_after = {str(fp): sha(fp) for fp in FROZEN_FILES if fp.exists()}

    qc = run_part03_qc(tickers_df, research_df, provenance_df, tsetmc_df,
                       frozen_before, frozen_after, part02_before, part02_after)

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
        "admission_only_tickers": [],
        "unresolved_tickers": [],
        "ready_for_user_review_tickers": [],
        "conflict_tickers": [],
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
        if es == "requires_first_public_trade_evidence":
            summary["admission_only_tickers"].append(tk)
        if es in ("no_reliable_evidence", "requires_manual_review"):
            summary["unresolved_tickers"].append(tk)
        if ready == "true":
            summary["ready_for_user_review_tickers"].append(tk)
        if str(r["conflict_flag"]).strip().lower() == "true":
            summary["conflict_tickers"].append(tk)
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
