"""Stage124 Batch 2 — Part 2: Screening for 10 specific tickers."""

import json, csv, hashlib, subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
import pandas as pd
import requests as _requests
from .stage124_batch02_v2 import (
    normalize_ticker, normalize_symbol, normalize_jalali, normalize_digits,
    jalali_to_gregorian_str, sha, git_head, merge_commit_in_ancestry,
    tsetmc_probe_ticker, _http_session, read_csv, write_csv,
    ROOT, OUT, PILOT15, STAGE123_INPUT, STAGE122_INPUT,
    EXPECTED_STAGE123_SHA, EXPECTED_STAGE122_SHA,
    REFERENCE_MERGE_COMMIT, PARTIAL_MASTER, TSETMC_SEARCH_URL,
)

PART02_DIR = ROOT / "stage124" / "batch02_parts"
PART02_TICKERS = ["بموتو","ثشرق","ثنوسا","حپترو","حکشتی","خاذین","خبهمن","ختوقا","خرینگ","خمحور"]
PROBE_CSV = ROOT / "stage124_feasibility" / "feasibility_probe_flat_stage124_iran.csv"
FULL_VERIFIED_FORBIDDEN = OUT / "listing_master_verified_stage124.csv"

FROZEN_FILES = [
    ROOT/"src"/"stage124_batch02_v2_research.json",
    OUT/"listing_pending_priority_stage124_batch02_v2.csv",
    OUT/"listing_batch02_selected_tickers_v2.csv",
    OUT/"listing_batch02_research_candidates_v2.csv",
    OUT/"listing_batch02_source_provenance_v2.csv",
    OUT/"listing_batch02_tsetmc_conflict_audit_v2.csv",
    OUT/"listing_batch02_user_review_template_v2.csv",
    OUT/"stage124_batch02_gate_a_v2_qc_report.json",
    OUT/"metadata_and_hashes_stage124_batch02_gate_a_v2.json",
    PARTIAL_MASTER, STAGE122_INPUT, STAGE123_INPUT,
]

# ---- research data for 10 tickers ----------------------------------------------
RESEARCH_DATA = {
    "بموتو": {
        "admission_date_candidate_jalali": "1369-12-28",
        "listing_date_candidate_jalali": "",
        "first_public_offering_date_candidate_jalali": "",
        "first_public_trading_date_candidate_jalali": "",
        "proposed_canonical_public_entry_date_jalali": "",
        "proposed_canonical_event_type": "",
        "date_precision": "exact_day",
        "evidence_status": "requires_first_public_trade_evidence",
        "research_status": "requires_first_public_trade_evidence",
        "ready_for_user_review": "false",
        "ordinary_share_confirmed": "true",
        "event_description": "تبدیل به سهامی عام و پذیرش در بورس تهران در ۲۸ اسفند ۱۳۶۹.",
        "sources": [
            ["market_media", "سهام بموتو - علیرضا مهرابی",
             "https://alirezamehrabi.com/saham/electrical-machinery/motj", "",
             "شرکت موتوژن در تاریخ ۲۸ اسفند ۱۳۶۹ از سهامی خاص به سهامی عام تغییر و در سازمان بورس پذیرفته شد."],
        ],
        "notes": "admission-only؛ proposed_canonical خالی.",
    },
    "ثشرق": {
        "admission_date_candidate_jalali": "",
        "listing_date_candidate_jalali": "1393-04-04",
        "first_public_offering_date_candidate_jalali": "",
        "first_public_trading_date_candidate_jalali": "",
        "proposed_canonical_public_entry_date_jalali": "",
        "proposed_canonical_event_type": "",
        "date_precision": "exact_day",
        "evidence_status": "requires_first_public_trade_evidence",
        "research_status": "requires_first_public_trade_evidence",
        "ready_for_user_review": "false",
        "ordinary_share_confirmed": "true",
        "event_description": "پذیرش در فرابورس ۱۳۹۰/۷/۲۳ و انتقال به بورس ۱۳۹۳/۴/۴.",
        "sources": [
            ["market_media", "سهام ثشرق - علیرضا مهرابی",
             "https://alirezamehrabi.com/saham/construction-real-estate/pmsx", "",
             "شرکت در 1390/7/23 در فرابورس و در 1393/4/4 در بورس پذیرفته شد."],
            ["market_media", "ثشرق - بانک بورس",
             "https://bankbourse.ir/listofaudit/شرکت-های-بورسی/AuditBank/sshargh-1186.html", "",
             "تاریخچه شرکت در سال 1369 تاسیس گردید."],
        ],
        "notes": "admission-only (listing date)؛ proposed_canonical خالی.",
    },
    "ثنوسا": {
        "admission_date_candidate_jalali": "",
        "listing_date_candidate_jalali": "1383-10-09",
        "first_public_offering_date_candidate_jalali": "",
        "first_public_trading_date_candidate_jalali": "",
        "proposed_canonical_public_entry_date_jalali": "",
        "proposed_canonical_event_type": "",
        "date_precision": "exact_day",
        "evidence_status": "requires_first_public_trade_evidence",
        "research_status": "requires_first_public_trade_evidence",
        "ready_for_user_review": "false",
        "ordinary_share_confirmed": "true",
        "event_description": "در تاریخ ۹ دی ۸۳ با نماد ثنوسا در بورس به ثبت رسید.",
        "sources": [
            ["market_information_aggregator", "نماد ثنوسا - تاکدال",
             "https://tacodal.ir/symbol/%D8%AB%D9%86%D9%88%D8%B3%D8%A7", "",
             "در تاریخ 9 دی 83 با نماد ثنوسا در سازمان بورس به ثبت رسید."],
            ["company_official_website", "شرکت نوسازی و ساختمان تهران",
             "https://www.nosa-eng.com/", "",
             "در تاریخ 9 دی 83 با نماد ثنوسا در بورس به ثبت رسید."],
        ],
        "notes": "admission-only (listing date)؛ proposed_canonical خالی.",
    },
    "حپترو": {
        "admission_date_candidate_jalali": "1382-05-06",
        "listing_date_candidate_jalali": "",
        "first_public_offering_date_candidate_jalali": "",
        "first_public_trading_date_candidate_jalali": "",
        "proposed_canonical_public_entry_date_jalali": "",
        "proposed_canonical_event_type": "",
        "date_precision": "exact_day",
        "evidence_status": "requires_first_public_trade_evidence",
        "research_status": "requires_first_public_trade_evidence",
        "ready_for_user_review": "false",
        "ordinary_share_confirmed": "true",
        "event_description": "سهام شرکت در تاریخ 1382/05/06 در بورس پذیرفته شد.",
        "sources": [
            ["market_media", "اطلاعات شرکت حپترو - رهاورد 365",
             "https://rahavard365.com/asset/380/%D8%AD%D9%BE%D8%AA%D8%B1%D9%88", "",
             "سهام شرکت در تاریخ 1382/05/06 در بورس اوراق بهادار تهران پذیرفته شده است."],
            ["company_official_website", "تاریخچه شرکت حمل و نقل پتروشیمی",
             "https://ptec-ir.ir/%D8%AA%D8%A7%D8%B1%DB%8C%D8%AE%DA%86%D9%87/", "",
             "از سال 1382 وارد بازار سرمایه شد با نماد حپترو."],
        ],
        "notes": "admission-only؛ proposed_canonical خالی.",
    },
    "حکشتی": {
        "admission_date_candidate_jalali": "",
        "listing_date_candidate_jalali": "",
        "first_public_offering_date_candidate_jalali": "",
        "first_public_trading_date_candidate_jalali": "",
        "proposed_canonical_public_entry_date_jalali": "",
        "proposed_canonical_event_type": "unresolved",
        "date_precision": "exact_day",
        "evidence_status": "requires_manual_review",
        "research_status": "requires_manual_review",
        "ready_for_user_review": "false",
        "ordinary_share_confirmed": "unknown",
        "event_description": "تعارض تاریخ نخستین عرضه عمومی: ۱۳۸۷/۰۲/۲۸ (همشهری آنلاین) در برابر ۱۳۸۷/۰۲/۲۹ (شواهد بیرونی دیگر). تعارض تاکنون حل‌نشده.",
        "sources": [
            ["news_website_contemporaneous", "28 اردیبهشت: عرضه اولیه سهام کشتیرانی - همشهری آنلاین",
             "https://www.hamshahrionline.ir/news/51719/28-%D8%A7%D8%B1%D8%AF%DB%8C%D8%A8%D9%87%D8%B4%D8%AA-%D8%B9%D8%B1%D8%B6%D9%87-%D8%A7%D9%88%D9%84%DB%8C%D9%87-%D8%B3%D9%87%D8%A7%D9%85-%DA%A9%D8%B4%D8%AA%DB%8C%D8%B1%D8%A7%D9%86%DB%8C", "1387-02-28",
             "سهام کشتیرانی جمهوری اسلامی ایران روز شنبه ۲۸ اردیبهشت پس از پذیرش و درج نام در فهرست شرکت‌های پذیرفته شده، در تابلو فرعی بورس عرضه می‌شود. ۱۲۷ میلیون سهم معادل ۲.۵۵ درصد عرضه می‌گردد."],
            ["market_information_aggregator", "نماد حکشتی - تاکدال",
             "https://tacodal.ir/symbol/%D8%AD%DA%A9%D8%B4%D8%AA%DB%8C", "1387-02-28",
             "در تاریخ ۱۳۸۷/۰۲/۲۸ سهام کشتیرانی جمهوری اسلامی ایران در بورس عرضه گردید."],
            ["market_media", "بررسی وضعیت سهام کشتیرانی - بورس ۲۴",
             "https://www.bourse24.ir/news/63921", "",
             "در روز عرضه اولیه، سهام شرکت کشتیرانی تا دقایق پایانی معاملات در قیمت ۲۳۷ تومان رقابت شد."],
        ],
        "notes": "تعارض تاریخ ۱۳۸۷/۰۲/۲۸ و ۱۳۸۷/۰۲/۲۹؛ تا حل تعارض canonical خالی و requires_manual_review.",
    },
    "خاذین": {
        "admission_date_candidate_jalali": "",
        "listing_date_candidate_jalali": "",
        "first_public_offering_date_candidate_jalali": "",
        "first_public_trading_date_candidate_jalali": "",
        "proposed_canonical_public_entry_date_jalali": "",
        "proposed_canonical_event_type": "first_public_offering",
        "date_precision": "month_only",
        "evidence_status": "requires_manual_review",
        "research_status": "requires_manual_review",
        "ready_for_user_review": "false",
        "ordinary_share_confirmed": "true",
        "event_description": "عرضه اولیه سهام سایپا آذین در خرداد ماه ۱۳۸۰ (دقت ماه).",
        "sources": [
            ["market_media", "تحلیل تکنیکال خاذین - آرتان ترید",
             "https://artantrade.com/%d8%aa%d8%ad%d9%84%db%8c%d9%84-%d8%aa%da%a9%d9%86%db%8c%da%a9%d8%a7%d9%84-%d8%ae%d8%a7%d8%b0%db%8c%d9%86/", "",
             "سال عرضه اولیه: خرداد ماه 1380."],
            ["market_media", "خاذین - آموزش بورس",
             "https://amoozesh-boors.com/fa/stocks/%D8%AE%D8%A7%D8%B0%DB%8C%D9%86", "",
             "نماد خاذین در 28 اسفند 1370 با نام سایپا موتور ثبت شد."],
        ],
        "notes": "فقط دقت ماه (خرداد 1380)؛ ready_for_user_review=false.",
    },
    "خبهمن": {
        "admission_date_candidate_jalali": "",
        "listing_date_candidate_jalali": "",
        "first_public_offering_date_candidate_jalali": "",
        "first_public_trading_date_candidate_jalali": "",
        "proposed_canonical_public_entry_date_jalali": "",
        "proposed_canonical_event_type": "",
        "date_precision": "month_only",
        "evidence_status": "requires_manual_review",
        "research_status": "requires_manual_review",
        "ready_for_user_review": "false",
        "ordinary_share_confirmed": "true",
        "event_description": "پذیرش گروه بهمن در اسفند ماه ۱۳۷۲ در بورس (دقت ماه).",
        "sources": [
            ["market_media", "تحلیل سهام خبهمن - حسن خزایی",
             "https://hassankhazaei.ir/%D8%AE%D8%A8%D9%87%D9%85%D9%86", "",
             "در اسفند ماه 1372 در سازمان بورس پذیرفته شد."],
            ["news_website", "نماد خبهمن - ECN",
             "https://ecn.ir/stock-symbols/khbahman/", "",
             "در سال 1372 شرکت به بورس پیوست."],
        ],
        "notes": "فقط دقت ماه (اسفند 1372)؛ ready_for_user_review=false.",
    },
    "ختوقا": {
        "admission_date_candidate_jalali": "",
        "listing_date_candidate_jalali": "",
        "first_public_offering_date_candidate_jalali": "",
        "first_public_trading_date_candidate_jalali": "",
        "proposed_canonical_public_entry_date_jalali": "",
        "proposed_canonical_event_type": "",
        "date_precision": "year_only",
        "evidence_status": "requires_manual_review",
        "research_status": "requires_manual_review",
        "ready_for_user_review": "false",
        "ordinary_share_confirmed": "true",
        "event_description": "تبدیل به سهامی عام ۱۳۷۰/۷/۳۰ و پذیرش در بورس سال ۱۳۷۱ (دقت سال).",
        "sources": [
            ["market_media", "معرفی قطعات اتومبیل ایران - خبربان",
             "https://khabarban.com/20480470/", "",
             "در تاریخ ۱۳۷۰/۰۷/۳۰ به سهامی عام تبدیل و در سال ۱۳۷۱ پذیرفته شد."],
            ["market_media", "تحلیل سهام ختوقا - فلفلانی",
             "https://felfelani.ir/%D8%AA%D8%AD%D9%84%DB%8C%D9%84-%D8%B3%D9%87%D8%A7%D9%85-%D8%AE%D8%AA%D9%88%D9%82%D8%A7/", "",
             "در سال 1371 با نماد ختوقا پذیرفته شد."],
        ],
        "notes": "فقط دقت سال (1371)؛ ready_for_user_review=false.",
    },
    "خرینگ": {
        "admission_date_candidate_jalali": "",
        "listing_date_candidate_jalali": "1382-12-16",
        "first_public_offering_date_candidate_jalali": "",
        "first_public_trading_date_candidate_jalali": "",
        "proposed_canonical_public_entry_date_jalali": "",
        "proposed_canonical_event_type": "",
        "date_precision": "exact_day",
        "evidence_status": "requires_first_public_trade_evidence",
        "research_status": "requires_first_public_trade_evidence",
        "ready_for_user_review": "false",
        "ordinary_share_confirmed": "true",
        "event_description": "در تاریخ 1382/12/16 نام شرکت در ردیف شرکتهای پذیرفته در بورس درج گردید.",
        "sources": [
            ["market_media", "سهام خرینگ - علیرضا مهرابی",
             "https://alirezamehrabi.com/saham/auto-parts/rinm", "",
             "در تاریخ 1382/12/16 در بورس درج گردید."],
            ["news_website", "نماد خرینگ - ECN",
             "https://ecn.ir/stock-symbols/khring/", "",
             "در سال 1372 به سهامی عام تبدیل و در بورس پذیرفته شد."],
        ],
        "notes": "admission-only (listing date)؛ proposed_canonical خالی.",
    },
    "خمحور": {
        "admission_date_candidate_jalali": "1383-08-25",
        "listing_date_candidate_jalali": "",
        "first_public_offering_date_candidate_jalali": "",
        "first_public_trading_date_candidate_jalali": "",
        "proposed_canonical_public_entry_date_jalali": "",
        "proposed_canonical_event_type": "",
        "date_precision": "exact_day",
        "evidence_status": "requires_first_public_trade_evidence",
        "research_status": "requires_first_public_trade_evidence",
        "ready_for_user_review": "false",
        "ordinary_share_confirmed": "true",
        "event_description": "شرکت در تاریخ 25 آبان 1383 در بورس پذیرفته شده است.",
        "sources": [
            ["market_media", "خمحور - آموزش بورس",
             "https://amoozesh-boors.com/fa/stocks/%D8%AE%D9%85%D8%AD%D9%88%D8%B1", "",
             "شرکت در تاریخ 25 آبان 1383 در بورس پذیرفته شده است."],
            ["market_media", "سهام خمحور - علیرضا مهرابی",
             "https://alirezamehrabi.com/saham/auto-parts/tmkh", "",
             "شرکت تولید محور خودرو در ۲۰ دی ۱۳۶۶ تاسیس شد."],
        ],
        "notes": "admission-only؛ proposed_canonical خالی.",
    },
}


# ---- helper functions ----------------------------------------------------------
def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _greg(jalali: str) -> str:
    if not jalali:
        return ""
    try:
        return jalali_to_gregorian_str(jalali)
    except Exception:
        return ""


def load_company_names() -> dict:
    pm = read_csv(PARTIAL_MASTER)
    names = {}
    for _, r in pm.iterrows():
        if r["ticker"] in PART02_TICKERS:
            names[r["ticker"]] = r["company_name"]
    return names


def check_existing_probe(ticker: str) -> dict | None:
    if not PROBE_CSV.exists():
        return None
    df = read_csv(PROBE_CSV)
    matches = df[df["ticker_original"] == ticker]
    if matches.empty:
        return None
    r = matches.iloc[0]
    return {
        "instrument_match_status": r.get("instrument_match_status", ""),
        "ordinary_instrument_count": r.get("tsetmc_instrument_candidate_count", ""),
        "selected_inscode": r.get("tsetmc_instrument_id_selected", ""),
        "tsetmc_candidate_date_jalali": r.get("candidate_first_trade_date_jalali", ""),
        "tsetmc_candidate_date_gregorian": r.get("candidate_first_trade_date_gregorian", ""),
        "probe_retrieved_at": r.get("retrieved_at", ""),
        "probe_raw_sha256": r.get("tsetmc_search_raw_sha256", ""),
        "probe_notes": r.get("notes", ""),
        "source_file_path": str(PROBE_CSV),
        "source_file_sha256": sha(PROBE_CSV),
        "valid_iran_run": r.get("valid_iran_run", ""),
        "ordinary_instrument_candidates_json": r.get("tsetmc_instrument_candidates_json", "[]"),
        "multiple_ordinary_instruments": 1 if r.get("instrument_match_status") == "ambiguous_instrument" else 0,
    }


def probe_tsetmc_for_tickers(tickers: list, timeout: float = 5.0) -> dict:
    results = {}
    sess = _http_session()
    for tk in tickers:
        existing = check_existing_probe(tk)
        if existing and existing.get("instrument_match_status") not in ("", "not_probed"):
            existing["probe_source"] = "existing_probe_csv"
            results[tk] = existing
            continue
        result = tsetmc_probe_ticker(tk, sess, timeout=timeout)
        result["probe_source"] = "live_probe"
        results[tk] = result
    return results


def _tsetmc_disposition(status: str, has_date: bool) -> str:
    if status == "network_unreachable":
        return "network_unreachable"
    if status == "candidate_found" and has_date:
        return "audit_only_not_canonical"
    if status in ("no_exact_ordinary_instrument_match", "multiple_ordinary_instruments",
                  "empty_trade_history", "http_error", "parse_error"):
        return status
    return status


def _programmer_recommendation(info: dict) -> str:
    es = info["evidence_status"]
    if es == "candidate_supported":
        return "recommend_user_review"
    if es == "requires_first_public_trade_evidence":
        return "requires_first_public_trade_evidence"
    if es == "requires_manual_review":
        return "requires_manual_review_for_exact_date"
    return "requires_manual_research"


def _ambiguity_notes(info: dict, probe: dict) -> str:
    parts = []
    es = info["evidence_status"]
    if es == "requires_first_public_trade_evidence":
        parts.append("admission/listing date found but no first public offering/trading evidence")
    if es == "requires_manual_review":
        if info["date_precision"] == "month_only":
            parts.append("only month precision; exact day required")
        elif info["date_precision"] == "year_only":
            parts.append("only year precision; exact day required")
        elif info["date_precision"] == "exact_day" and not info.get("proposed_canonical_public_entry_date_jalali"):
            parts.append("conflicting exact-day dates; manual resolution required")
    ts = probe.get("instrument_match_status", "not_probed")
    td = probe.get("tsetmc_candidate_date_jalali", "")
    if ts == "network_unreachable":
        parts.append("tsetmc unreachable; no conflict check")
    elif td and info.get("proposed_canonical_public_entry_date_jalali"):
        if normalize_jalali(td) != normalize_jalali(info["proposed_canonical_public_entry_date_jalali"]):
            parts.append("tsetmc date differs from researched; manual resolution needed")
        else:
            parts.append("tsetmc date agrees with researched")
    elif td:
        parts.append("tsetmc candidate audit-only; not canonical")
    return "; ".join(parts) if parts else ""


# ---- source fetch for حکشتی ----------------------------------------------------
def fetch_sources_hkeshti(timeout: float = 5.0) -> dict:
    """Fetch up to 3 URLs for حکشتی sequentially. retry=0, timeout=5s."""
    info = RESEARCH_DATA["حکشتی"]
    sources = info.get("sources", [])[:3]
    results = {}
    snapshot_dir = PART02_DIR / "snapshots_hkeshti"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    for idx, src in enumerate(sources, 1):
        url = src[2]
        rec = {
            "source_index": idx,
            "source_url": url,
            "http_status": "",
            "retrieval_status": "",
            "final_url": url,
            "content_type": "",
            "response_size_bytes": 0,
            "snapshot_path": "",
            "content_sha256": "",
            "retrieved_at_utc": _utc_now(),
            "extraction_notes": "",
        }
        try:
            resp = _requests.get(url, timeout=timeout, allow_redirects=True,
                                 headers={"User-Agent": "Mozilla/5.0"})
            rec["http_status"] = resp.status_code
            rec["final_url"] = resp.url
            rec["content_type"] = resp.headers.get("Content-Type", "")
            body = resp.content
            rec["response_size_bytes"] = len(body)
            rec["content_sha256"] = hashlib.sha256(body).hexdigest()
            snap_path = snapshot_dir / f"source_{idx}.html"
            snap_path.write_bytes(body)
            rec["snapshot_path"] = str(snap_path)
            rec["retrieval_status"] = "fetched_ok"
            rec["extraction_notes"] = f"HTTP {resp.status_code}; {len(body)} bytes; content_sha256 recorded."
        except _requests.exceptions.Timeout:
            rec["retrieval_status"] = "timeout"
            rec["extraction_notes"] = f"Request timed out after {timeout}s."
        except _requests.exceptions.ConnectionError as e:
            rec["retrieval_status"] = "connection_error"
            rec["extraction_notes"] = f"Connection error: {str(e)[:200]}"
        except Exception as e:
            rec["retrieval_status"] = "fetch_error"
            rec["extraction_notes"] = f"Error: {str(e)[:200]}"
        results[idx] = rec
    return results


# ---- DataFrame builders --------------------------------------------------------
def build_tickers_df(company_names: dict) -> pd.DataFrame:
    rows = []
    for tk in PART02_TICKERS:
        rows.append({
            "ticker": tk,
            "ticker_normalized": normalize_ticker(tk),
            "company_name": company_names.get(tk, ""),
        })
    return pd.DataFrame(rows)


def build_research_screening(company_names: dict, probe_results: dict) -> pd.DataFrame:
    rows = []
    for tk in PART02_TICKERS:
        info = RESEARCH_DATA[tk]
        probe = probe_results.get(tk, {})
        tsetmc_status = probe.get("instrument_match_status", "not_probed")
        tsetmc_j = probe.get("tsetmc_candidate_date_jalali", "")
        cand_j = info["proposed_canonical_public_entry_date_jalali"]
        cand_g = _greg(cand_j)
        adm_j = info["admission_date_candidate_jalali"]
        list_j = info["listing_date_candidate_jalali"]
        fpo_j = info["first_public_offering_date_candidate_jalali"]
        fpt_j = info["first_public_trading_date_candidate_jalali"]
        sources = info.get("sources", [])
        src1 = sources[0] if len(sources) > 0 else ("", "", "", "", "")
        src2 = sources[1] if len(sources) > 1 else ("", "", "", "", "")
        rows.append({
            "ticker": tk,
            "ticker_normalized": normalize_ticker(tk),
            "company_name": company_names.get(tk, ""),
            "admission_date_candidate_jalali": adm_j,
            "admission_date_candidate_gregorian": _greg(adm_j),
            "listing_date_candidate_jalali": list_j,
            "listing_date_candidate_gregorian": _greg(list_j),
            "first_public_offering_date_candidate_jalali": fpo_j,
            "first_public_offering_date_candidate_gregorian": _greg(fpo_j),
            "first_public_trading_date_candidate_jalali": fpt_j,
            "first_public_trading_date_candidate_gregorian": _greg(fpt_j),
            "proposed_canonical_public_entry_date_jalali": cand_j,
            "proposed_canonical_public_entry_date_gregorian": cand_g,
            "proposed_canonical_event_type": info["proposed_canonical_event_type"],
            "date_precision": info["date_precision"],
            "ordinary_share_confirmed": info["ordinary_share_confirmed"],
            "evidence_status": info["evidence_status"],
            "research_status": info["research_status"],
            "ready_for_user_review": info["ready_for_user_review"],
            "primary_source_type": src1[0],
            "primary_source_title": src1[1],
            "primary_source_url": src1[2],
            "secondary_source_type": src2[0],
            "secondary_source_title": src2[1],
            "secondary_source_url": src2[2],
            "tsetmc_instrument_match_status": tsetmc_status,
            "tsetmc_candidate_date_jalali": tsetmc_j,
            "tsetmc_candidate_disposition": _tsetmc_disposition(tsetmc_status, bool(tsetmc_j)),
            "ambiguity_notes": _ambiguity_notes(info, probe),
            "programmer_recommendation": _programmer_recommendation(info),
        })
    return pd.DataFrame(rows)


def build_source_provenance(probe_results: dict, retrieved_at: str,
                            hkeshti_fetch: dict | None = None) -> pd.DataFrame:
    rows = []
    for tk in PART02_TICKERS:
        info = RESEARCH_DATA[tk]
        sources = info.get("sources", [])
        for idx, src in enumerate(sources, 1):
            src_type = src[0]
            src_title = src[1]
            src_url = src[2]
            pub_date = src[3] if len(src) > 3 else ""
            event_summary = src[4] if len(src) > 4 else ""
            row = {
                "ticker": tk, "source_index": idx,
                "source_type": src_type, "source_title": src_title,
                "source_url": src_url, "publication_date": pub_date,
                "retrieved_at_utc": retrieved_at, "http_status": "",
                "retrieval_status": "not_fetched_in_part02_research",
                "final_url": src_url, "content_type": "",
                "response_size_bytes": "", "snapshot_path": "",
                "content_sha256": "",
                "extraction_notes": "Source identified during Part 2 web research; raw snapshot not captured.",
                "exact_text_or_event_summary": event_summary,
            }
            if tk == "حکشتی" and hkeshti_fetch and idx in hkeshti_fetch:
                fr = hkeshti_fetch[idx]
                row["http_status"] = str(fr["http_status"])
                row["retrieval_status"] = fr["retrieval_status"]
                row["final_url"] = fr["final_url"]
                row["content_type"] = fr["content_type"]
                row["response_size_bytes"] = str(fr["response_size_bytes"])
                row["snapshot_path"] = fr["snapshot_path"]
                row["content_sha256"] = fr["content_sha256"]
                row["retrieved_at_utc"] = fr["retrieved_at_utc"]
                row["extraction_notes"] = fr["extraction_notes"]
            rows.append(row)
        probe = probe_results.get(tk, {})
        tsetmc_status = probe.get("instrument_match_status", "not_probed")
        tsetmc_raw_sha = probe.get("probe_raw_sha256", "")
        tsetmc_notes = probe.get("probe_notes", "")
        tsetmc_retrieved = probe.get("probe_retrieved_at", retrieved_at)
        tsetmc_url = TSETMC_SEARCH_URL.format(sym=quote(normalize_symbol(tk)))
        if tsetmc_status == "network_unreachable":
            ret_status = "network_unreachable"
        elif tsetmc_status == "candidate_found":
            ret_status = "raw_response_captured" if tsetmc_raw_sha else "no_raw_response"
        elif tsetmc_status in ("http_error", "parse_error", "empty_trade_history",
                                "no_exact_ordinary_instrument_match"):
            ret_status = tsetmc_status
        else:
            ret_status = "not_probed"
        rows.append({
            "ticker": tk, "source_index": len(sources) + 1,
            "source_type": "tsetmc_api",
            "source_title": f"TSETMC instrument search for {tk}",
            "source_url": tsetmc_url, "publication_date": "",
            "retrieved_at_utc": tsetmc_retrieved, "http_status": "",
            "retrieval_status": ret_status, "final_url": tsetmc_url,
            "content_type": "application/json" if tsetmc_raw_sha else "",
            "response_size_bytes": "", "snapshot_path": "",
            "content_sha256": tsetmc_raw_sha,
            "extraction_notes": f"TSETMC API probe (timeout=5s, retry=0). {tsetmc_notes}",
            "exact_text_or_event_summary": f"instrument_match_status={tsetmc_status}",
        })
    return pd.DataFrame(rows)


def build_tsetmc_audit(probe_results: dict) -> pd.DataFrame:
    rows = []
    for tk in PART02_TICKERS:
        probe = probe_results.get(tk, {})
        tsetmc_status = probe.get("instrument_match_status", "not_probed")
        tsetmc_j = probe.get("tsetmc_candidate_date_jalali", "")
        rows.append({
            "ticker": tk, "ticker_normalized": normalize_ticker(tk),
            "instrument_match_status": tsetmc_status,
            "tsetmc_candidate_date_jalali": tsetmc_j,
            "tsetmc_candidate_date_gregorian": probe.get("tsetmc_candidate_date_gregorian", ""),
            "selected_inscode": probe.get("selected_inscode", ""),
            "ordinary_instrument_count": probe.get("ordinary_instrument_count", ""),
            "ordinary_instrument_candidates_json": probe.get("ordinary_instrument_candidates_json", "[]"),
            "multiple_ordinary_instruments": probe.get("multiple_ordinary_instruments", 0),
            "probe_retrieved_at": probe.get("probe_retrieved_at", ""),
            "probe_raw_sha256": probe.get("probe_raw_sha256", ""),
            "probe_notes": probe.get("probe_notes", ""),
            "probe_source": probe.get("probe_source", "live_probe"),
            "source_file_path": probe.get("source_file_path", ""),
            "source_file_sha256": probe.get("source_file_sha256", ""),
            "valid_iran_run": probe.get("valid_iran_run", ""),
            "tsetmc_candidate_disposition": _tsetmc_disposition(tsetmc_status, bool(tsetmc_j)),
        })
    return pd.DataFrame(rows)


# ---- QC ------------------------------------------------------------------------
def run_part02_qc(
    tickers_df: pd.DataFrame,
    research_df: pd.DataFrame,
    provenance_df: pd.DataFrame,
    tsetmc_df: pd.DataFrame,
    frozen_before: dict,
    frozen_after: dict,
) -> dict:
    assertions = []

    def check(name: str, passed: bool, detail: str = ""):
        assertions.append({"assertion": name, "passed": bool(passed), "detail": str(detail)})

    expected_set = set(PART02_TICKERS)
    actual_set = set(tickers_df["ticker"].tolist())

    check("exactly_10_rows", len(research_df) == 10, f"rows={len(research_df)}")
    check("exactly_10_unique_tickers", tickers_df["ticker"].nunique() == 10,
          f"unique={tickers_df['ticker'].nunique()}")
    check("ticker_set_matches_announced", actual_set == expected_set,
          f"missing={expected_set - actual_set}, extra={actual_set - expected_set}")
    check("no_pilot15_in_part02", len(actual_set & PILOT15) == 0,
          f"intersection={actual_set & PILOT15}")
    check("no_other_tickers", actual_set == expected_set,
          f"extra={actual_set - expected_set}")
    check("no_duplicate_tickers", tickers_df["ticker"].duplicated().sum() == 0,
          f"duplicates={tickers_df['ticker'].duplicated().sum()}")

    for _, r in research_df.iterrows():
        tk = r["ticker"]
        cand_j = r["proposed_canonical_public_entry_date_jalali"]
        ev_type = r["proposed_canonical_event_type"]
        ready = str(r["ready_for_user_review"]).lower()
        es = r["evidence_status"]
        dp = r["date_precision"]
        adm = r["admission_date_candidate_jalali"]
        lst = r["listing_date_candidate_jalali"]

        if (adm or lst) and cand_j:
            check(f"no_canonical_from_admission_{tk}", False,
                  f"admission/listing present but canonical={cand_j}")
        else:
            check(f"no_canonical_from_admission_{tk}", True)

        if ready == "true":
            ok = (dp == "exact_day" and ev_type in ("first_public_offering", "first_public_trading")
                  and es == "candidate_supported" and cand_j != "")
            check(f"ready_only_for_exact_day_{tk}", ok,
                  f"dp={dp}, ev={ev_type}, es={es}, cand={cand_j}")
        else:
            check(f"ready_false_when_not_exact_{tk}", True)

        if dp in ("month_only", "year_only"):
            check(f"month_year_only_not_ready_{tk}", ready == "false",
                  f"dp={dp}, ready={ready}")

        cand_g = r["proposed_canonical_public_entry_date_gregorian"]
        if cand_j and cand_g:
            try:
                expected_g = jalali_to_gregorian_str(cand_j)
                check(f"date_conversion_ok_{tk}", cand_g == expected_g,
                      f"jalali={cand_j}, greg={cand_g}, expected={expected_g}")
            except Exception as e:
                check(f"date_conversion_ok_{tk}", False, f"error={e}")
        else:
            check(f"date_conversion_ok_{tk}", True)

    for _, r in tsetmc_df.iterrows():
        tk = r["ticker"]
        status = r["instrument_match_status"]
        disp = r["tsetmc_candidate_disposition"]
        if status == "network_unreachable":
            check(f"network_unreachable_not_no_candidate_{tk}",
                  disp == "network_unreachable", f"disp={disp}")
        if r["tsetmc_candidate_date_jalali"]:
            check(f"tsetmc_date_not_canonical_{tk}",
                  disp == "audit_only_not_canonical", f"disp={disp}")

    all_dfs = [research_df, provenance_df, tsetmc_df]
    has_verified = any(
        "verified_user_confirmed" in str(df.values) for df in all_dfs
    )
    check("no_verified_user_confirmed", not has_verified,
          "verified_user_confirmed must not appear in any Part 2 output")

    check("no_full_verified_master_created", not FULL_VERIFIED_FORBIDDEN.exists(),
          "listing_master_verified_stage124.csv must not exist")

    check("no_user_decision_status",
          "user_decision" not in research_df.columns,
          "no user_decision column in research screening")

    check("no_verification_status_column",
          "verification_status" not in research_df.columns,
          "no verification_status column in research screening")

    for fp_str in sorted(frozen_before):
        check(f"frozen_unchanged_{Path(fp_str).name}",
              frozen_before[fp_str] == frozen_after.get(fp_str, ""),
              f"before={frozen_before[fp_str][:12]}, after={frozen_after.get(fp_str, '')[:12]}")

    check("reference_merge_commit_in_ancestry", merge_commit_in_ancestry(),
          f"merge commit {REFERENCE_MERGE_COMMIT[:8]} is ancestor of HEAD")
    check("stage123_sha_matches", sha(STAGE123_INPUT) == EXPECTED_STAGE123_SHA,
          f"sha={sha(STAGE123_INPUT)[:12]}")
    check("stage122_sha_matches", sha(STAGE122_INPUT) == EXPECTED_STAGE122_SHA,
          f"sha={sha(STAGE122_INPUT)[:12]}")

    all_pass = all(a["passed"] for a in assertions)
    return {"all_pass": all_pass, "assertions": assertions}


# ---- hash manifest -------------------------------------------------------------
def build_hash_manifest(files: list, source_commit: str) -> pd.DataFrame:
    rows = []
    for fp, role in files:
        if fp.exists():
            h = hashlib.sha256(fp.read_bytes()).hexdigest()
        else:
            h = ""
        try:
            rel = str(fp.relative_to(ROOT))
        except ValueError:
            rel = str(fp)
        rows.append({
            "relative_path": rel,
            "file_role": role,
            "size_bytes": fp.stat().st_size if fp.exists() else 0,
            "sha256": h,
            "generated_at": _utc_now(),
            "source_commit": source_commit,
        })
    return pd.DataFrame(rows)


# ---- main run ------------------------------------------------------------------
def run() -> dict:
    PART02_DIR.mkdir(parents=True, exist_ok=True)
    retrieved_at = _utc_now()
    source_commit = git_head()

    frozen_before = {str(fp): sha(fp) for fp in FROZEN_FILES if fp.exists()}

    company_names = load_company_names()
    tickers_df = build_tickers_df(company_names)
    probe_results = probe_tsetmc_for_tickers(PART02_TICKERS, timeout=5.0)
    hkeshti_fetch = fetch_sources_hkeshti(timeout=5.0)

    research_df = build_research_screening(company_names, probe_results)
    provenance_df = build_source_provenance(probe_results, retrieved_at, hkeshti_fetch)
    tsetmc_df = build_tsetmc_audit(probe_results)

    research_path = PART02_DIR / "part02_research_screening_10tickers.csv"
    provenance_path = PART02_DIR / "part02_source_provenance_10tickers.csv"
    tsetmc_path = PART02_DIR / "part02_tsetmc_audit_10tickers.csv"

    write_csv(research_df, research_path)
    write_csv(provenance_df, provenance_path)
    write_csv(tsetmc_df, tsetmc_path)

    frozen_after = {str(fp): sha(fp) for fp in FROZEN_FILES if fp.exists()}

    qc = run_part02_qc(tickers_df, research_df, provenance_df, tsetmc_df,
                       frozen_before, frozen_after)

    part02_files = [
        (research_path, "part02_research_screening"),
        (provenance_path, "part02_source_provenance"),
        (tsetmc_path, "part02_tsetmc_audit"),
    ]
    manifest_df = build_hash_manifest(part02_files, source_commit)
    manifest_path = PART02_DIR / "part02_hash_manifest.csv"
    write_csv(manifest_df, manifest_path)

    qc_report = {
        "stage": "stage124_batch02_part02",
        "generated_at": _utc_now(),
        "source_commit": source_commit,
        "ticker_count": 10,
        "tickers": PART02_TICKERS,
        "all_pass": qc["all_pass"],
        "assertion_count": len(qc["assertions"]),
        "failed_count": sum(1 for a in qc["assertions"] if not a["passed"]),
        "assertions": qc["assertions"],
    }
    qc_path = PART02_DIR / "part02_qc_report.json"
    with open(qc_path, "w", encoding="utf-8") as f:
        json.dump(qc_report, f, ensure_ascii=False, indent=2)

    summary = {
        "stage": "stage124_batch02_part02",
        "generated_at": _utc_now(),
        "source_commit": source_commit,
        "ticker_count": 10,
        "tickers": PART02_TICKERS,
        "exact_day_dates": {},
        "admission_only_tickers": [],
        "unresolved_tickers": [],
        "ready_for_user_review_tickers": [],
        "tsetmc_results": {},
        "hkeshti_conflict": {
            "date_28": "1387-02-28",
            "date_29": "1387-02-29",
            "resolution": "unresolved",
            "evidence_status": "requires_manual_review",
            "ready_for_user_review": False,
        },
        "hkeshti_fetch_results": {},
    }
    for _, r in research_df.iterrows():
        tk = r["ticker"]
        es = r["evidence_status"]
        cand = r["proposed_canonical_public_entry_date_jalali"]
        ready = str(r["ready_for_user_review"]).lower()
        if cand:
            summary["exact_day_dates"][tk] = cand
        if es == "requires_first_public_trade_evidence":
            summary["admission_only_tickers"].append(tk)
        if es in ("requires_manual_review", "no_reliable_evidence"):
            summary["unresolved_tickers"].append(tk)
        if ready == "true":
            summary["ready_for_user_review_tickers"].append(tk)
        probe = probe_results.get(tk, {})
        summary["tsetmc_results"][tk] = {
            "instrument_match_status": probe.get("instrument_match_status", "not_probed"),
            "tsetmc_candidate_date_jalali": probe.get("tsetmc_candidate_date_jalali", ""),
            "probe_source": probe.get("probe_source", "live_probe"),
        }
    for idx, fr in hkeshti_fetch.items():
        summary["hkeshti_fetch_results"][f"source_{idx}"] = {
            "source_url": fr["source_url"],
            "http_status": str(fr["http_status"]),
            "retrieval_status": fr["retrieval_status"],
            "content_sha256": fr["content_sha256"],
            "response_size_bytes": str(fr["response_size_bytes"]),
            "snapshot_path": fr["snapshot_path"],
        }
    summary_path = PART02_DIR / "part02_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return {
        "qc": qc,
        "summary": summary,
        "files": {
            "research_screening": str(research_path),
            "source_provenance": str(provenance_path),
            "tsetmc_audit": str(tsetmc_path),
            "hash_manifest": str(manifest_path),
            "qc_report": str(qc_path),
            "summary_json": str(summary_path),
        },
    }
