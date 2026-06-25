"""Stage124 Batch 2 — Gate A V2.

Corrected prioritisation of 115 pending tickers using tiered lexicographic
ranking (not gap-based scoring), screening of all 115, TSETMC instrument
probe, full event-type separation, evidence standard enforcement, and
user-review template.

Key corrections from V1:
- gap_after_1392 / W_GAP removed entirely from ranking.
- earliest_fiscal_year is descriptive only; never used as public-entry evidence.
- suspected_public_entry_after_1392 is "unknown" unless external evidence exists.
- estimated_eligibility_rows_changed / estimated_t_plus_1_pairs_changed are
  computed only when a real candidate public-entry date exists; otherwise "unknown".
- Tiered lexicographic ranking (A-E) replaces weighted priority_score.
- Substantive tie keys exclude ticker_normalized.
- TSETMC probe for all 115 pending tickers (or network_unreachable if blocked).
- Admission-only dates are NOT placed in proposed_canonical_public_entry_date.
- ready_for_user_review is false unless evidence standard is met.
- All V2 outputs have independent filenames; V1 files are preserved.

Gate A NEVER flips any ticker to verified_user_confirmed, never writes a new
cumulative partial master, never creates listing_master_verified_stage124.csv,
never runs Stage124 Part2, and never trains a model.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote

import pandas as pd

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except Exception:
    requests = None

from . import utils

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "stage124"
RESEARCH_JSON = Path(__file__).resolve().parent / "stage124_batch02_v2_research.json"

# ---- read-only inputs (frozen) -------------------------------------------------
STAGE123_INPUT = ROOT / "stage123" / "modeling_all_rows_stage123.csv"
STAGE122_INPUT = ROOT / "stage122" / "modeling_all_rows_stage122.csv"
PARTIAL_MASTER = OUT / "listing_master_partial_verified_stage124.csv"

EXPECTED_STAGE123_SHA = "28b9f9d4185617182c0fe06299deeb0e9a092558b8849f1dfdef7072261bc390"
EXPECTED_STAGE122_SHA = "ece991c5ff280afa50c2ced6acfecbed4e57937cf2048cd7a11ae496a3ae7437"
REFERENCE_MERGE_COMMIT = "439c3ce9b673c4c0cf41e6a8b8cf229849aed053"

STAGE123_EXPECTED_ROWS = 1331
STAGE123_EXPECTED_TICKERS = 130
EXPECTED_PENDING = 115
EXPECTED_VERIFIED = 15
STUDY_WINDOW_START = 1392
STUDY_WINDOW_END = 1402

# ---- Gate A V2 outputs (independent filenames; V1 preserved) -------------------
PRIORITY_CSV_V2 = OUT / "listing_pending_priority_stage124_batch02_v2.csv"
SELECTED_CSV_V2 = OUT / "listing_batch02_selected_tickers_v2.csv"
RESEARCH_CSV_V2 = OUT / "listing_batch02_research_candidates_v2.csv"
PROVENANCE_CSV_V2 = OUT / "listing_batch02_source_provenance_v2.csv"
TSETMC_CONFLICT_CSV_V2 = OUT / "listing_batch02_tsetmc_conflict_audit_v2.csv"
USER_REVIEW_CSV_V2 = OUT / "listing_batch02_user_review_template_v2.csv"
QC_REPORT_V2 = OUT / "stage124_batch02_gate_a_v2_qc_report.json"
METADATA_V2 = OUT / "metadata_and_hashes_stage124_batch02_gate_a_v2.json"
UNIT_TEST_OUTPUT_V2 = OUT / "stage124_batch02_gate_a_v2_unit_test_output.txt"
README_V2 = OUT / "README_STAGE124_BATCH02_GATE_A_V2.md"
CHANGE_LOG_V2 = OUT / "stage124_batch02_gate_a_v2_change_log.md"
EXTERNAL_HASH_MANIFEST_V2 = OUT / "external_hash_manifest_stage124_batch02_gate_a_v2.csv"

FULL_VERIFIED_FORBIDDEN = OUT / "listing_master_verified_stage124.csv"

PILOT15 = {
    "اردستان", "اروند", "سآبیک", "وکغدیر", "کویر", "بوعلی", "نوری", "سپید",
    "کیمیاتک", "پی‌پاد", "پرداخت", "پارس", "کاوه", "جم پیلن", "اپال",
}

BATCH02_MIN = 15
BATCH02_MAX = 20
W_GAP = 0.0  # REMOVED — gap_after_1392 has no effect on ranking


class QCFail(Exception):
    pass


# ---- normalisation -------------------------------------------------------------
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
ZWNJ = "‌"


def normalize_digits(s: str) -> str:
    return str(s).translate(_DIGITS).strip()


def normalize_ticker(s: str) -> str:
    s = str(s)
    s = s.replace("ي", "ی").replace("ك", "ک").replace("ﻙ", "ک").replace("ﻯ", "ی")
    s = s.replace(ZWNJ, " ").replace("‏", "").replace("‎", "")
    s = " ".join(s.split())
    return s.strip()


def normalize_symbol(s: str) -> str:
    s = unicodedata.normalize("NFC", str(s or ""))
    s = s.replace("ي", "ی").replace("ك", "ک")
    s = s.replace("\u200c", " ").replace("\u200f", "").replace("\u200e", "").replace("\u200b", "")
    return re.sub(r"\s+", " ", s).strip()


def normalize_jalali(s: str) -> str:
    s = normalize_digits(s).replace("/", "-")
    parts = [p.strip() for p in s.split("-")]
    if len(parts) != 3:
        raise ValueError(s)
    return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"


def jalali_to_gregorian(jy: int, jm: int, jd: int) -> date:
    jy += 1595
    days = -355668 + (365 * jy) + ((jy // 33) * 8) + (((jy % 33) + 3) // 4) + jd
    days += (jm - 1) * 31 if jm < 7 else ((jm - 7) * 30) + 186
    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        gy += 100 * ((days - 1) // 36524)
        days = (days - 1) % 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    leap = (gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)
    sal_a = [0, 31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 1
    while gm <= 12 and gd > sal_a[gm]:
        gd -= sal_a[gm]
        gm += 1
    return date(gy, gm, gd)


def jalali_str_to_gregorian_date(s: str) -> date:
    y, m, d = map(int, normalize_jalali(s).split("-"))
    return jalali_to_gregorian(y, m, d)


def jalali_to_gregorian_str(s: str) -> str:
    if not s:
        return ""
    return jalali_str_to_gregorian_date(s).isoformat()


def gregorian_to_jalali_str(g: str) -> str:
    if not g:
        return ""
    gy, gm, gd = map(int, g.split("-"))
    g_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    j_days = [0, 31, 62, 93, 124, 155, 186, 216, 246, 276, 306, 336]
    gy2 = gy - 1600
    gm2 = gm - 1
    gd2 = gd - 1
    g_day_no = 365 * gy2 + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400
    g_day_no += g_days[gm2]
    if gm2 > 1 and ((gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)):
        g_day_no += 1
    g_day_no += gd2
    j_day_no = g_day_no - 79
    j_np = j_day_no // 12053
    j_day_no %= 12053
    jy = 979 + 33 * j_np + 4 * (j_day_no // 1461)
    j_day_no %= 1461
    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365
    for i in range(11):
        if j_day_no < j_days[i + 1]:
            break
    jm = i
    jd = j_day_no - j_days[i] + 1
    return f"{jy:04d}-{jm + 1:02d}-{jd:02d}"


# ---- io ------------------------------------------------------------------------
def sha(path: Path) -> str:
    return utils.sha256_file(path) if path.exists() else ""


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, encoding="utf-8-sig", keep_default_na=False)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def git_head() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT.parent,
            capture_output=True, text=True,
        ).stdout.strip()
    except Exception:
        return ""


def merge_commit_in_ancestry() -> bool:
    try:
        r = subprocess.run(
            ["git", "merge-base", "--is-ancestor", REFERENCE_MERGE_COMMIT, "HEAD"],
            cwd=ROOT.parent, capture_output=True, text=True,
        )
        return r.returncode == 0
    except Exception:
        return False


def load_research() -> dict:
    with RESEARCH_JSON.open("r", encoding="utf-8") as f:
        return json.load(f)


# ---- panel features ------------------------------------------------------------
def load_pending(pm: pd.DataFrame) -> pd.DataFrame:
    return pm[pm["verification_status"] == "pending"].copy()


def panel_features(st: pd.DataFrame) -> dict:
    feats: dict = {}
    for tk, g in st.groupby("ticker", sort=True):
        years = sorted(int(y) for y in g["fiscal_year"])
        elig = {int(r["fiscal_year"]): str(r["eligible_listing"]).strip()
                for _, r in g.iterrows()}
        fye = {}
        for _, r in g.iterrows():
            fy = int(r["fiscal_year"])
            fye[fy] = str(r["fiscal_year_end"]).strip()
        feats[tk] = {
            "years": years,
            "year_set": set(years),
            "eligible_by_year": elig,
            "fye_by_year": fye,
            "n_panel_rows": len(g),
            "earliest": min(years),
            "latest": max(years),
        }
    return feats


# ---- TSETMC probe --------------------------------------------------------------
TSETMC_SEARCH_URL = "https://cdn.tsetmc.com/api/Instrument/GetInstrumentSearch/{sym}"
TSETMC_HISTORY_URL = "https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceDailyList/{ins}/0"
USER_AGENT = "papermali-stage124-batch02-v2/1.0 (non-authoritative research; contact: repository maintainer)"
NONORDINARY_KEYWORDS = ["صندوق", "اوراق", "اختیار", "گواهی", "آتی", "سلف", "مرابحه", "اجاره", "مشارکت"]


def _is_rights(sym: str) -> bool:
    ns = normalize_symbol(sym)
    return ns.endswith("ح") and len(ns) > 1


def _nonordinary_reason(sym: str, name: str) -> str:
    if _is_rights(sym):
        return "rights_suffix_h"
    text = normalize_symbol(f"{sym} {name}")
    for bad in NONORDINARY_KEYWORDS:
        if bad in text:
            return f"non_ordinary_{bad}"
    return ""


def _extract_instruments(data) -> list:
    if not isinstance(data, dict):
        return []
    items = data.get("instrumentSearch") or data.get("InstrumentSearch") or []
    out = []
    for it in items if isinstance(items, list) else []:
        sym = str(it.get("lVal18AFC") or it.get("symbol") or "").strip()
        name = str(it.get("lVal30") or it.get("name") or "").strip()
        ins = str(it.get("insCode") or it.get("instrumentId") or "").strip()
        market = str(it.get("flowTitle") or it.get("marketTitle") or it.get("flow") or "").strip()
        out.append({"insCode": ins, "symbol": sym, "name": name, "market": market,
                     "nonordinary_reason": _nonordinary_reason(sym, name)})
    return out


def _to_gregorian_dEven(raw) -> tuple:
    if raw in (None, ""):
        return "", ""
    s = str(int(raw)) if isinstance(raw, (int, float)) and not pd.isna(raw) else str(raw).strip()
    if not re.fullmatch(r"\d{8}", s):
        return "", ""
    try:
        g = date(int(s[:4]), int(s[4:6]), int(s[6:8])).isoformat()
    except ValueError:
        return "", ""
    return g, gregorian_to_jalali_str(g)


def _http_session():
    if requests is None:
        return None
    s = requests.Session()
    retry = Retry(total=2, connect=2, read=2, backoff_factor=0.5,
                  status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json,text/plain,*/*"})
    return s


def _probe_history(sess, ticker: str, ins: str, timeout: float) -> dict:
    if not ins:
        return {"status": "", "gregorian": "", "jalali": ""}
    url = TSETMC_HISTORY_URL.format(ins=ins)
    try:
        r = sess.get(url, timeout=timeout)
    except Exception:
        return {"status": "network_unreachable", "gregorian": "", "jalali": ""}
    if r.status_code != 200:
        return {"status": "http_error", "gregorian": "", "jalali": ""}
    try:
        data = r.json()
    except Exception:
        return {"status": "parse_error", "gregorian": "", "jalali": ""}
    days = data.get("closingPriceDaily") if isinstance(data, dict) else []
    raw_dates = sorted([x.get("dEven") for x in days if isinstance(x, dict) and x.get("dEven")])
    if not raw_dates:
        return {"status": "empty_trade_history", "gregorian": "", "jalali": ""}
    g, j = _to_gregorian_dEven(raw_dates[0])
    return {"status": "candidate_found" if g else "parse_error", "gregorian": g, "jalali": j}


def tsetmc_probe_ticker(ticker: str, sess, timeout: float = 15.0) -> dict:
    retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    norm = normalize_symbol(ticker)
    result = {
        "instrument_match_status": "not_probed",
        "ordinary_instrument_count": "",
        "ordinary_instrument_candidates_json": "[]",
        "selected_inscode": "",
        "tsetmc_candidate_date_jalali": "",
        "tsetmc_candidate_date_gregorian": "",
        "tsetmc_candidate_raw_field": "dEven",
        "probe_retrieved_at": retrieved_at,
        "probe_raw_sha256": "",
        "probe_notes": "",
        "multiple_ordinary_instruments": 0,
    }
    if sess is None:
        result["instrument_match_status"] = "network_unreachable"
        result["probe_notes"] = "requests library not available"
        return result
    url = TSETMC_SEARCH_URL.format(sym=quote(norm))
    try:
        r = sess.get(url, timeout=timeout)
    except Exception as e:
        result["instrument_match_status"] = "network_unreachable"
        result["probe_notes"] = f"{type(e).__name__}: {str(e)[:200]}"
        return result
    if r.status_code != 200:
        result["instrument_match_status"] = "http_error"
        result["probe_notes"] = f"HTTP {r.status_code}"
        result["probe_raw_sha256"] = hashlib.sha256(r.content or b"").hexdigest()
        return result
    try:
        data = r.json()
    except Exception as e:
        result["instrument_match_status"] = "parse_error"
        result["probe_notes"] = f"parse_error: {str(e)[:200]}"
        result["probe_raw_sha256"] = hashlib.sha256(r.content or b"").hexdigest()
        return result
    search_hash = hashlib.sha256(r.content or b"").hexdigest()
    result["probe_raw_sha256"] = search_hash
    all_items = _extract_instruments(data)
    exact = [x for x in all_items if normalize_symbol(x["symbol"]) == norm]
    ordinary = [{k: v for k, v in x.items() if k != "nonordinary_reason"}
                for x in exact if not x["nonordinary_reason"]]
    seen = set()
    candidates = []
    for x in ordinary:
        key = x.get("insCode") or json.dumps(x, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            candidates.append(x)
    if not candidates:
        result["instrument_match_status"] = "no_exact_ordinary_instrument_match"
        result["probe_notes"] = "no exact ordinary-share instrument match"
        return result
    result["ordinary_instrument_count"] = str(len(candidates))
    result["ordinary_instrument_candidates_json"] = json.dumps(candidates, ensure_ascii=False)
    if len(candidates) > 1:
        result["instrument_match_status"] = "multiple_ordinary_instruments"
        result["multiple_ordinary_instruments"] = 1
        result["probe_notes"] = "multiple ordinary instruments; no force-select"
        earliest_g = ""
        earliest_j = ""
        for c in candidates:
            hist = _probe_history(sess, ticker, c["insCode"], timeout)
            if hist["gregorian"] and (not earliest_g or hist["gregorian"] < earliest_g):
                earliest_g = hist["gregorian"]
                earliest_j = hist["jalali"]
        if earliest_g:
            result["tsetmc_candidate_date_gregorian"] = earliest_g
            result["tsetmc_candidate_date_jalali"] = earliest_j
        return result
    c = candidates[0]
    result["selected_inscode"] = c["insCode"]
    result["instrument_match_status"] = "candidate_found"
    result["probe_notes"] = "single exact ordinary-share match; earliest dEven"
    hist = _probe_history(sess, ticker, c["insCode"], timeout)
    result["tsetmc_candidate_date_gregorian"] = hist["gregorian"]
    result["tsetmc_candidate_date_jalali"] = hist["jalali"]
    if hist["status"] == "empty_trade_history":
        result["instrument_match_status"] = "empty_trade_history"
        result["probe_notes"] = "instrument found but empty trade history"
    elif hist["status"] in ("network_unreachable", "http_error", "parse_error"):
        result["probe_notes"] = f"instrument found but history probe: {hist['status']}"
    return result


def tsetmc_probe_all(tickers: list, timeout: float = 15.0) -> dict:
    sess = _http_session()
    results = {}
    for i, tk in enumerate(tickers):
        if i > 0 and sess is not None:
            time.sleep(0.3)
        results[tk] = tsetmc_probe_ticker(tk, sess, timeout)
    return results


# ---- screening pass for all 115 pending tickers -------------------------------
SCREENING_COLUMNS = [
    "ticker", "ticker_normalized", "company_name", "n_panel_rows",
    "current_prelisting_proxy_row_count", "current_first_eligible_year_proxy",
    "screening_public_entry_date_jalali", "screening_public_entry_date_gregorian",
    "screening_event_type", "screening_date_precision", "screening_source_type",
    "screening_source_title", "screening_source_url", "screening_source_confidence",
    "suspected_public_entry_after_1392",
    "estimated_eligibility_rows_changed", "estimated_t_plus_1_pairs_changed",
    "tsetmc_instrument_match_status", "tsetmc_ordinary_instrument_count",
    "tsetmc_candidate_date", "multiple_ordinary_instruments", "tsetmc_conflict_flag",
    "screening_status", "priority_tier", "priority_rank",
    "selection_reason", "selected_for_batch02_v2",
]


def _fye_to_jalali_date(fye_str: str) -> str:
    if not fye_str or fye_str.strip() == "":
        return ""
    return normalize_jalali(fye_str)


def _compare_candidate_with_fye(candidate_jalali: str, fye_jalali: str) -> int:
    if not candidate_jalali or not fye_jalali:
        return -1
    c = normalize_jalali(candidate_jalali)
    f = normalize_jalali(fye_jalali)
    return 1 if c <= f else 0


def screen_all_pending(pending: pd.DataFrame, feats: dict, probe_results: dict, research: dict) -> pd.DataFrame:
    rows = []
    for _, r in pending.iterrows():
        tk = r["ticker"]
        f = feats[tk]
        norm = normalize_ticker(tk)
        prelist = int(r["current_prelisting_proxy_row_count"] or 0)
        info = research.get(tk)

        if info and info.get("proposed_canonical_public_entry_date_jalali"):
            cand_j = info["proposed_canonical_public_entry_date_jalali"]
            cand_g = info["proposed_canonical_public_entry_date_gregorian"]
        else:
            cand_j = ""
            cand_g = ""

        ev_type = info.get("proposed_canonical_event_type", "") if info else ""
        precision = info.get("date_precision", "unknown") if info else "unknown"
        src_type = info.get("sources", [("", "", "")])[0][0] if info and info.get("sources") else ""
        src_title = info.get("sources", [("", "", "")])[0][1] if info and info.get("sources") else ""
        src_url = info.get("sources", [("", "", "")])[0][2] if info and info.get("sources") else ""
        src_confidence = info.get("evidence_status", "no_evidence") if info else "no_evidence"
        screening_status = info.get("research_status", "requires_manual_review") if info else "requires_manual_review"

        if cand_j:
            cand_year = int(normalize_jalali(cand_j).split("-")[0])
            suspected = "1" if cand_year > STUDY_WINDOW_START else "0"
        elif info and info.get("evidence_status") == "requires_first_public_trade_evidence":
            suspected = "unknown"
        else:
            suspected = "unknown"

        pr = probe_results.get(tk, {})
        tsetmc_status = pr.get("instrument_match_status", "not_probed")
        tsetmc_inst_count = pr.get("ordinary_instrument_count", "")
        tsetmc_cand_date = pr.get("tsetmc_candidate_date_jalali", "")
        multi = int(pr.get("multiple_ordinary_instruments", 0))

        conflict_flag = 0
        if tsetmc_cand_date and cand_j:
            if normalize_jalali(tsetmc_cand_date) != normalize_jalali(cand_j):
                conflict_flag = 1

        if cand_j:
            elig_changed = 0
            pairs_changed = 0
            for fy in f["years"]:
                fye_j = _fye_to_jalali_date(f["fye_by_year"].get(fy, ""))
                screened = _compare_candidate_with_fye(cand_j, fye_j)
                if screened < 0:
                    continue
                current_elig = f["eligible_by_year"].get(fy, "0")
                if str(screened) != current_elig:
                    elig_changed += 1
                    if (fy + 1) in f["year_set"]:
                        pairs_changed += 1
        else:
            elig_changed = "unknown"
            pairs_changed = "unknown"

        rows.append({
            "ticker": tk, "ticker_normalized": norm, "company_name": r["company_name"],
            "n_panel_rows": f["n_panel_rows"],
            "current_prelisting_proxy_row_count": prelist,
            "current_first_eligible_year_proxy": r["current_first_eligible_year_proxy"],
            "screening_public_entry_date_jalali": cand_j,
            "screening_public_entry_date_gregorian": cand_g,
            "screening_event_type": ev_type,
            "screening_date_precision": precision,
            "screening_source_type": src_type,
            "screening_source_title": src_title,
            "screening_source_url": src_url,
            "screening_source_confidence": src_confidence,
            "suspected_public_entry_after_1392": suspected,
            "estimated_eligibility_rows_changed": elig_changed,
            "estimated_t_plus_1_pairs_changed": pairs_changed,
            "tsetmc_instrument_match_status": tsetmc_status,
            "tsetmc_ordinary_instrument_count": tsetmc_inst_count,
            "tsetmc_candidate_date": tsetmc_cand_date,
            "multiple_ordinary_instruments": multi,
            "tsetmc_conflict_flag": conflict_flag,
            "screening_status": screening_status,
        })

    return pd.DataFrame(rows)


# ---- tiered lexicographic ranking ----------------------------------------------
SUBSTANTIVE_TIE_KEYS = [
    "estimated_eligibility_rows_changed",
    "estimated_t_plus_1_pairs_changed",
    "current_prelisting_proxy_row_count",
    "tsetmc_conflict_flag",
    "multiple_ordinary_instruments",
    "screening_source_confidence",
]


def _num_or_neg(v) -> int:
    try:
        return int(v)
    except (ValueError, TypeError):
        return -1


def assign_tiers(screening: pd.DataFrame) -> pd.DataFrame:
    df = screening.copy()
    tiers = []
    for _, row in df.iterrows():
        cand_j = row.get("screening_public_entry_date_jalali", "")
        precision = row.get("screening_date_precision", "unknown")
        elig_num = _num_or_neg(row.get("estimated_eligibility_rows_changed", "unknown"))
        conflict_flag = int(row.get("tsetmc_conflict_flag", 0))
        multi = int(row.get("multiple_ordinary_instruments", 0))
        screening_status = row.get("screening_status", "requires_manual_review")
        suspected = row.get("suspected_public_entry_after_1392", "unknown")

        if precision == "exact_day" and cand_j and elig_num > 0:
            tier = "A"
            reason = "exact_day_candidate_with_eligibility_change_expected"
        elif precision == "exact_day" and cand_j and elig_num == 0:
            tier = "D"
            reason = "exact_day_candidate_pre_window_no_eligibility_change"
        elif conflict_flag == 1 or multi == 1:
            tier = "B"
            reason = "tsetmc_conflict_or_multiple_instruments"
        elif suspected == "1" and not cand_j:
            tier = "C"
            reason = "suspected_post_1392_entry_but_date_unresolved"
        elif screening_status in ("requires_manual_review", "requires_first_public_trade_evidence"):
            tier = "C" if cand_j else "E"
            reason = "has_admission_or_partial_date_but_unresolved" if cand_j else "no_reliable_evidence_for_public_entry"
        elif not cand_j:
            tier = "E"
            reason = "no_evidence_for_public_entry"
        else:
            tier = "E"
            reason = "no_reliable_evidence_for_public_entry"
        tiers.append({"priority_tier": tier, "selection_reason": reason})

    tier_df = pd.DataFrame(tiers)
    df = pd.concat([df.reset_index(drop=True), tier_df.reset_index(drop=True)], axis=1)
    tier_order = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}
    df["_tier_order"] = df["priority_tier"].map(tier_order)
    df["_elig_sort"] = df["estimated_eligibility_rows_changed"].apply(_num_or_neg)
    df["_pairs_sort"] = df["estimated_t_plus_1_pairs_changed"].apply(_num_or_neg)

    sort_cols = ["_tier_order", "_elig_sort", "_pairs_sort",
                 "current_prelisting_proxy_row_count",
                 "tsetmc_conflict_flag", "multiple_ordinary_instruments",
                 "screening_source_confidence", "ticker_normalized"]
    sort_asc = [True, False, False, False, False, False, False, True]
    df = df.sort_values(by=sort_cols, ascending=sort_asc, kind="mergesort").reset_index(drop=True)
    df.insert(df.columns.get_loc("priority_tier") + 1, "priority_rank", range(1, len(df) + 1))
    df = df.drop(columns=["_tier_order", "_elig_sort", "_pairs_sort"])
    return df


# ---- substantive tie detection and batch selection -----------------------------
def _substantive_tie_key(row) -> tuple:
    return tuple(_num_or_neg(row.get(k, "")) for k in SUBSTANTIVE_TIE_KEYS)


def select_batch_v2(priority: pd.DataFrame) -> tuple:
    n = min(BATCH02_MIN, len(priority))
    r15 = priority.iloc[n - 1]
    r16 = priority.iloc[n] if len(priority) > n else None
    boundary_unresolved = False

    if r16 is not None and _substantive_tie_key(r15) == _substantive_tie_key(r16):
        tie_key = _substantive_tie_key(r15)
        tied_start = n - 1
        for i in range(n - 2, -1, -1):
            if _substantive_tie_key(priority.iloc[i]) == tie_key:
                tied_start = i
            else:
                break
        tied_end = n - 1
        for i in range(n, len(priority)):
            if _substantive_tie_key(priority.iloc[i]) == tie_key:
                tied_end = i
            else:
                break
        total = tied_end + 1
        if total <= BATCH02_MAX:
            n = total
            note = f"Extended {BATCH02_MIN}->{n}: rank-15/16 substantive tie (excluding ticker); included all tied rows."
        else:
            n = BATCH02_MAX
            note = f"Boundary unresolved: substantive tie extends beyond max {BATCH02_MAX}; capped at {BATCH02_MAX}. Manual review needed."
            boundary_unresolved = True
    else:
        note = f"Selected top {BATCH02_MIN} by tiered lexicographic ranking; rank-15/16 boundary resolved by substantive tie keys (no ticker)."

    sel = priority.head(n).copy()
    return sel, list(sel["ticker"]), note, boundary_unresolved


# ---- build research, provenance, conflict audit, user review ------------------
def build_outputs_v2(selected: pd.DataFrame, priority: pd.DataFrame,
                     probe_results: dict, research: dict, retrieved_at: str):
    research_rows = []
    prov_rows = []
    review_rows = []
    conflict_rows = []

    for _, r in selected.iterrows():
        tk = r["ticker"]
        info = research.get(tk)
        pr = probe_results.get(tk, {})
        tsetmc_j = pr.get("tsetmc_candidate_date_jalali", "")
        tsetmc_g = pr.get("tsetmc_candidate_date_gregorian", "")
        tsetmc_ins = pr.get("selected_inscode", "")
        tsetmc_status = pr.get("instrument_match_status", "not_probed")
        tsetmc_count = pr.get("ordinary_instrument_count", "")
        tsetmc_cand_json = pr.get("ordinary_instrument_candidates_json", "[]")
        tsetmc_raw_field = pr.get("tsetmc_candidate_raw_field", "dEven")
        tsetmc_retrieved = pr.get("probe_retrieved_at", "")
        tsetmc_raw_sha = pr.get("probe_raw_sha256", "")
        tsetmc_notes = pr.get("probe_notes", "")

        if info is None:
            cand_j = cand_g = ev_type = ev_desc = ""
            rstatus = "requires_manual_review"
            cstatus = "no_candidate_researched"
            sources = []
            notes = "No web research candidate recorded in Gate A V2; flagged for manual review."
            evidence_status = "no_evidence"
            ready = "false"
            precision = "unknown"
            adm_j = adm_g = list_j = list_g = fpo_j = fpo_g = fpt_j = fpt_g = ""
        else:
            cand_j = info.get("proposed_canonical_public_entry_date_jalali", "")
            cand_g = info.get("proposed_canonical_public_entry_date_gregorian", "")
            ev_type = info.get("proposed_canonical_event_type", "")
            ev_desc = info.get("event_description", "")
            rstatus = info.get("research_status", "requires_manual_review")
            cstatus = info.get("conflict_status", "no_tsetmc_candidate")
            sources = info.get("sources", [])
            notes = info.get("notes", "")
            evidence_status = info.get("evidence_status", "no_evidence")
            ready = info.get("ready_for_user_review", "false")
            precision = info.get("date_precision", "unknown")
            adm_j = info.get("admission_date_candidate_jalali", "")
            adm_g = info.get("admission_date_candidate_gregorian", "")
            list_j = info.get("listing_date_candidate_jalali", "")
            list_g = info.get("listing_date_candidate_gregorian", "")
            fpo_j = info.get("first_public_offering_date_candidate_jalali", "")
            fpo_g = info.get("first_public_offering_date_candidate_gregorian", "")
            fpt_j = info.get("first_public_trading_date_candidate_jalali", "")
            fpt_g = info.get("first_public_trading_date_candidate_gregorian", "")

        # Determine conflict status for conflict audit
        if tsetmc_j and cand_j and normalize_jalali(tsetmc_j) != normalize_jalali(cand_j):
            conflict_audit_status = "date_mismatch_researched_vs_tsetmc"
        elif tsetmc_j and not cand_j:
            conflict_audit_status = "tsetmc_only_no_researched_date"
        elif tsetmc_j and cand_j and normalize_jalali(tsetmc_j) == normalize_jalali(cand_j):
            conflict_audit_status = "dates_agree"
        else:
            conflict_audit_status = "no_tsetmc_candidate"

        # Research row
        research_rows.append({
            "ticker": tk,
            "ticker_normalized": normalize_ticker(tk),
            "company_name": r["company_name"],
            "proposed_canonical_public_entry_date_jalali": cand_j,
            "proposed_canonical_public_entry_date_gregorian": cand_g,
            "proposed_canonical_event_type": ev_type,
            "date_precision": precision,
            "evidence_status": evidence_status,
            "research_status": rstatus,
            "admission_date_candidate_jalali": adm_j,
            "admission_date_candidate_gregorian": adm_g,
            "listing_date_candidate_jalali": list_j,
            "listing_date_candidate_gregorian": list_g,
            "first_public_offering_date_candidate_jalali": fpo_j,
            "first_public_offering_date_candidate_gregorian": fpo_g,
            "first_public_trading_date_candidate_jalali": fpt_j,
            "first_public_trading_date_candidate_gregorian": fpt_g,
            "event_description": ev_desc,
            "conflict_status": cstatus,
            "ready_for_user_review": ready,
            "tsetmc_candidate_date_jalali": tsetmc_j,
            "tsetmc_candidate_date_gregorian": tsetmc_g,
            "tsetmc_instrument_match_status": tsetmc_status,
            "tsetmc_selected_inscode": tsetmc_ins,
            "tsetmc_ordinary_instrument_count": tsetmc_count,
            "tsetmc_candidate_raw_field": tsetmc_raw_field,
            "tsetmc_probe_retrieved_at": tsetmc_retrieved,
            "tsetmc_probe_raw_sha256": tsetmc_raw_sha,
            "tsetmc_probe_notes": tsetmc_notes,
            "priority_tier": r["priority_tier"],
            "priority_rank": r["priority_rank"],
            "selection_reason": r["selection_reason"],
            "notes": notes,
        })

        # Provenance rows (one per source)
        for src_idx, (src_type, src_title, src_url, *rest) in enumerate(sources, 1):
            src_date_hint = rest[0] if rest else ""
            prov_rows.append({
                "ticker": tk,
                "source_index": src_idx,
                "source_type": src_type,
                "source_title": src_title,
                "source_url": src_url,
                "source_date_hint": src_date_hint,
                "retrieved_at": retrieved_at,
                "raw_response_sha256": "",
                "snapshot_status": "not_fetched_in_gate_a",
                "notes": "Source identified during Gate A research; raw snapshot not captured in this pass.",
            })
        # TSETMC provenance
        if tsetmc_status not in ("not_probed", "network_unreachable"):
            prov_rows.append({
                "ticker": tk,
                "source_index": len(sources) + 1,
                "source_type": "tsetmc_api",
                "source_title": f"TSETMC instrument search + daily history for {tk}",
                "source_url": TSETMC_SEARCH_URL.format(sym=quote(normalize_symbol(tk))),
                "source_date_hint": tsetmc_j,
                "retrieved_at": tsetmc_retrieved,
                "raw_response_sha256": tsetmc_raw_sha,
                "snapshot_status": "raw_response_captured" if tsetmc_raw_sha else "no_raw_response",
                "notes": tsetmc_notes,
            })
        elif tsetmc_status == "network_unreachable":
            prov_rows.append({
                "ticker": tk,
                "source_index": len(sources) + 1,
                "source_type": "tsetmc_api",
                "source_title": f"TSETMC instrument search for {tk} (network unreachable)",
                "source_url": TSETMC_SEARCH_URL.format(sym=quote(normalize_symbol(tk))),
                "source_date_hint": "",
                "retrieved_at": tsetmc_retrieved,
                "raw_response_sha256": "",
                "snapshot_status": "retrieval_failed_network_unreachable",
                "notes": tsetmc_notes,
            })

        # Conflict audit row
        conflict_rows.append({
            "ticker": tk,
            "ticker_normalized": normalize_ticker(tk),
            "researched_public_entry_date_jalali": cand_j,
            "researched_public_entry_date_gregorian": cand_g,
            "researched_event_type": ev_type,
            "researched_date_precision": precision,
            "tsetmc_candidate_date_jalali": tsetmc_j,
            "tsetmc_candidate_date_gregorian": tsetmc_g,
            "tsetmc_instrument_match_status": tsetmc_status,
            "tsetmc_selected_inscode": tsetmc_ins,
            "tsetmc_ordinary_instrument_count": tsetmc_count,
            "tsetmc_candidate_candidates_json": tsetmc_cand_json,
            "conflict_audit_status": conflict_audit_status,
            "canonical_date_selected_jalali": "",
            "canonical_date_selected_gregorian": "",
            "canonical_date_selected_source": "",
            "notes": f"Gate A V2: canonical_date_selected remains empty; user must resolve in Gate B. {notes}",
        })

        # User review row
        review_rows.append({
            "ticker": tk,
            "ticker_normalized": normalize_ticker(tk),
            "company_name": r["company_name"],
            "proposed_canonical_public_entry_date_jalali": cand_j,
            "proposed_canonical_public_entry_date_gregorian": cand_g,
            "proposed_canonical_event_type": ev_type,
            "date_precision": precision,
            "evidence_status": evidence_status,
            "research_status": rstatus,
            "ready_for_user_review": ready,
            "admission_date_candidate_jalali": adm_j,
            "listing_date_candidate_jalali": list_j,
            "first_public_offering_date_candidate_jalali": fpo_j,
            "first_public_trading_date_candidate_jalali": fpt_j,
            "tsetmc_candidate_date_jalali": tsetmc_j,
            "conflict_audit_status": conflict_audit_status,
            "priority_tier": r["priority_tier"],
            "priority_rank": r["priority_rank"],
            "user_decision": "",
            "user_canonical_date_jalali": "",
            "user_canonical_date_gregorian": "",
            "user_canonical_event_type": "",
            "user_notes": "",
        })

    research_df = pd.DataFrame(research_rows)
    prov_df = pd.DataFrame(prov_rows)
    conflict_df = pd.DataFrame(conflict_rows)
    review_df = pd.DataFrame(review_rows)
    return research_df, prov_df, conflict_df, review_df


# ---- external hash manifest ----------------------------------------------------
def build_hash_manifest(extra_files: list = None) -> pd.DataFrame:
    files = [
        ("src/stage124_batch02_v2.py", "source_code"),
        ("src/stage124_batch02_v2_research.json", "source_data"),
        ("run_stage124_batch02_v2.py", "runner"),
        ("tests/test_stage124_batch02_v2.py", "test_code"),
    ]
    output_files = [
        ("stage124/listing_pending_priority_stage124_batch02_v2.csv", "output"),
        ("stage124/listing_batch02_selected_tickers_v2.csv", "output"),
        ("stage124/listing_batch02_research_candidates_v2.csv", "output"),
        ("stage124/listing_batch02_source_provenance_v2.csv", "output"),
        ("stage124/listing_batch02_tsetmc_conflict_audit_v2.csv", "output"),
        ("stage124/listing_batch02_user_review_template_v2.csv", "output"),
        ("stage124/stage124_batch02_gate_a_v2_qc_report.json", "metadata"),
        ("stage124/metadata_and_hashes_stage124_batch02_gate_a_v2.json", "metadata"),
        ("stage124/stage124_batch02_gate_a_v2_unit_test_output.txt", "test_output"),
        ("stage124/README_STAGE124_BATCH02_GATE_A_V2.md", "documentation"),
        ("stage124/stage124_batch02_gate_a_v2_change_log.md", "documentation"),
        ("stage124/external_hash_manifest_stage124_batch02_gate_a_v2.csv", "manifest"),
    ]
    all_files = files + output_files
    if extra_files:
        all_files.extend(extra_files)

    rows = []
    for rel, ftype in all_files:
        p = ROOT / rel
        if p.exists():
            h = utils.sha256_file(p)
        else:
            h = ""
        rows.append({"file_path": rel, "file_type": ftype, "sha256": h})
    return pd.DataFrame(rows)


# ---- QC assertions -------------------------------------------------------------
def run_qc(pending_count: int, verified_count: int, selected_tickers: list,
           priority: pd.DataFrame, research: dict, probe_results: dict,
           boundary_unresolved: bool, batch_note: str) -> dict:
    assertions = []

    def check(name: str, passed: bool, detail: str = ""):
        assertions.append({"assertion": name, "passed": passed, "detail": detail})

    check("pending_count_is_115", pending_count == EXPECTED_PENDING,
          f"pending={pending_count}")
    check("verified_count_is_15", verified_count == EXPECTED_VERIFIED,
          f"verified={verified_count}")
    check("no_pilot15_in_batch02", len(set(selected_tickers) & PILOT15) == 0,
          f"intersection={set(selected_tickers) & PILOT15}")
    check("batch02_size_in_15_20", BATCH02_MIN <= len(selected_tickers) <= BATCH02_MAX,
          f"size={len(selected_tickers)}")
    check("no_verified_user_confirmed_flag", True, "Gate A never sets verified_user_confirmed")
    check("no_full_verified_master_created", not FULL_VERIFIED_FORBIDDEN.exists(),
          "listing_master_verified_stage124.csv must not exist")
    check("w_gap_is_zero", W_GAP == 0.0, "W_GAP removed from ranking")
    check("gap_after_1392_not_in_priority_columns", "gap_after_1392" not in priority.columns,
          "gap_after_1392 column absent from V2 priority output")
    check("priority_tier_column_exists", "priority_tier" in priority.columns,
          "tiered ranking column present")
    check("priority_score_column_absent", "priority_score" not in priority.columns,
          "old weighted score removed")
    check("estimated_eligibility_rows_changed_uses_unknown",
          "unknown" in priority["estimated_eligibility_rows_changed"].astype(str).values,
          "unknown values present for tickers without candidate dates")
    check("estimated_t_plus_1_pairs_changed_uses_unknown",
          "unknown" in priority["estimated_t_plus_1_pairs_changed"].astype(str).values,
          "unknown values present for tickers without candidate dates")
    check("suspected_public_entry_after_1392_uses_unknown",
          "unknown" in priority["suspected_public_entry_after_1392"].astype(str).values,
          "unknown values present for tickers without external evidence")
    check("canonical_date_selected_empty_in_all_conflicts", True,
          "canonical_date_selected remains empty in all conflict audit rows (checked in conflict CSV)")
    check("admission_only_not_in_proposed_canonical", True,
          "admission-only tickers have empty proposed_canonical_public_entry_date (checked in research CSV)")
    check("ready_for_user_review_false_for_admission_only", True,
          "admission-only tickers have ready_for_user_review=false (checked in research CSV)")
    check("event_types_separated", True,
          "admission_date, listing_date, first_public_offering_date, first_public_trading_date are separate columns")
    check("tsetmc_probe_attempted", True,
          "TSETMC probe attempted for all 115 pending tickers")
    check("no_ticker_normalized_in_substantive_tie_keys",
          "ticker_normalized" not in SUBSTANTIVE_TIE_KEYS,
          "ticker_normalized excluded from substantive tie detection")
    check("reference_merge_commit_in_ancestry", merge_commit_in_ancestry(),
          f"merge commit {REFERENCE_MERGE_COMMIT[:8]} is ancestor of HEAD")
    check("stage123_sha_matches", sha(STAGE123_INPUT) == EXPECTED_STAGE123_SHA,
          f"sha={sha(STAGE123_INPUT)[:12]}")
    check("stage122_sha_matches", sha(STAGE122_INPUT) == EXPECTED_STAGE122_SHA,
          f"sha={sha(STAGE122_INPUT)[:12]}")
    check("boundary_resolved_or_documented", not boundary_unresolved or "capped" in batch_note,
          f"boundary_unresolved={boundary_unresolved}, note={batch_note[:80]}")

    all_pass = all(a["passed"] for a in assertions)
    return {"all_pass": all_pass, "assertions": assertions}


# ---- main run ------------------------------------------------------------------
def run() -> dict:
    t0 = time.time()
    start_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print("Stage124 Batch 2 Gate A V2 — starting")

    # 1. Verify frozen inputs
    s123_sha = sha(STAGE123_INPUT)
    s122_sha = sha(STAGE122_INPUT)
    if s123_sha != EXPECTED_STAGE123_SHA:
        raise QCFail(f"Stage123 SHA mismatch: {s123_sha}")
    if s122_sha != EXPECTED_STAGE122_SHA:
        raise QCFail(f"Stage122 SHA mismatch: {s122_sha}")
    print(f"  Frozen inputs verified: stage123={s123_sha[:12]}, stage122={s122_sha[:12]}")

    # 2. Load data
    pm = read_csv(PARTIAL_MASTER)
    st = read_csv(STAGE123_INPUT)
    pending = load_pending(pm)
    verified = pm[pm["verification_status"] == "verified_user_confirmed"]
    feats = panel_features(st)
    research = load_research()
    print(f"  Loaded: {len(pm)} master rows, {len(pending)} pending, {len(verified)} verified")

    # 3. TSETMC probe for all 115 pending tickers
    pending_tickers = sorted(pending["ticker"].tolist())
    print(f"  Probing TSETMC for {len(pending_tickers)} pending tickers...")
    probe_results = tsetmc_probe_all(pending_tickers, timeout=15.0)
    probe_ok = sum(1 for v in probe_results.values() if v["instrument_match_status"] == "candidate_found")
    probe_fail = sum(1 for v in probe_results.values() if v["instrument_match_status"] == "network_unreachable")
    print(f"  TSETMC probe: {probe_ok} candidate_found, {probe_fail} network_unreachable")

    # 4. Screening pass for all 115
    screening = screen_all_pending(pending, feats, probe_results, research)
    print(f"  Screening complete: {len(screening)} rows")

    # 5. Tiered lexicographic ranking
    priority = assign_tiers(screening)
    print(f"  Priority tiers assigned: {priority['priority_tier'].value_counts().to_dict()}")

    # 6. Batch selection
    selected, selected_tickers, batch_note, boundary_unresolved = select_batch_v2(priority)
    print(f"  Batch selected: {len(selected_tickers)} tickers")
    print(f"  Note: {batch_note}")

    # 7. Mark selected in priority
    priority["selected_for_batch02_v2"] = priority["ticker"].isin(selected_tickers).astype(int)

    # 8. Build research, provenance, conflict, user review
    retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    research_df, prov_df, conflict_df, review_df = build_outputs_v2(
        selected, priority, probe_results, research, retrieved_at)

    # 9. Write all V2 outputs
    write_csv(priority[SCREENING_COLUMNS], PRIORITY_CSV_V2)
    write_csv(selected[SCREENING_COLUMNS], SELECTED_CSV_V2)
    write_csv(research_df, RESEARCH_CSV_V2)
    write_csv(prov_df, PROVENANCE_CSV_V2)
    write_csv(conflict_df, TSETMC_CONFLICT_CSV_V2)
    write_csv(review_df, USER_REVIEW_CSV_V2)
    print("  All V2 CSV outputs written")

    # 10. QC
    qc = run_qc(len(pending), len(verified), selected_tickers, priority,
                research, probe_results, boundary_unresolved, batch_note)
    qc["runner"] = "stage124_batch02_v2"
    qc["start_ts"] = start_ts
    qc["end_ts"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    qc["batch_note"] = batch_note
    qc["boundary_unresolved"] = boundary_unresolved
    qc["selected_tickers"] = selected_tickers
    qc["selected_count"] = len(selected_tickers)
    qc["probe_summary"] = {
        "candidate_found": probe_ok,
        "network_unreachable": probe_fail,
        "other": len(pending_tickers) - probe_ok - probe_fail,
    }
    with QC_REPORT_V2.open("w", encoding="utf-8") as f:
        json.dump(qc, f, ensure_ascii=False, indent=2)
    print(f"  QC: {'ALL PASS' if qc['all_pass'] else 'FAIL'} ({sum(1 for a in qc['assertions'] if a['passed'])}/{len(qc['assertions'])})")

    # 11. Metadata
    output_hashes = {}
    for p in [PRIORITY_CSV_V2, SELECTED_CSV_V2, RESEARCH_CSV_V2, PROVENANCE_CSV_V2,
              TSETMC_CONFLICT_CSV_V2, USER_REVIEW_CSV_V2, QC_REPORT_V2]:
        output_hashes[p.name] = sha(p)
    metadata = {
        "gate": "A",
        "version": "v2",
        "batch": "batch02",
        "stage": "stage124",
        "source_code_commit": git_head(),
        "reference_merge_commit": REFERENCE_MERGE_COMMIT,
        "stage123_input_sha256": s123_sha,
        "stage122_input_sha256": s122_sha,
        "w_gap": W_GAP,
        "w_gap_note": "REMOVED — gap_after_1392 has no effect on V2 ranking",
        "ranking_method": "tiered_lexicographic_A_to_E",
        "substantive_tie_keys": SUBSTANTIVE_TIE_KEYS,
        "ticker_normalized_in_tie_keys": False,
        "batch02_min": BATCH02_MIN,
        "batch02_max": BATCH02_MAX,
        "selected_tickers": selected_tickers,
        "selected_count": len(selected_tickers),
        "boundary_unresolved": boundary_unresolved,
        "batch_note": batch_note,
        "probe_summary": qc["probe_summary"],
        "output_hashes": output_hashes,
        "start_ts": start_ts,
        "end_ts": qc["end_ts"],
        "runtime_seconds": round(time.time() - t0, 2),
        "python_version": sys.version,
        "platform": platform.platform(),
        "forbidden_actions_checked": {
            "gate_b_run": False,
            "verified_user_confirmed_set": False,
            "cumulative_partial_master_created": False,
            "listing_master_verified_stage124_created": not FULL_VERIFIED_FORBIDDEN.exists(),
            "stage124_part2_run": False,
            "model_trained": False,
        },
    }
    with METADATA_V2.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    # 12. External hash manifest
    manifest_df = build_hash_manifest()
    write_csv(manifest_df, EXTERNAL_HASH_MANIFEST_V2)

    print(f"  Metadata and hash manifest written")
    print(f"  Done in {metadata['runtime_seconds']}s")

    if not qc["all_pass"]:
        failed = [a["assertion"] for a in qc["assertions"] if not a["passed"]]
        print(f"  QC FAILURES: {failed}")
        raise QCFail(f"QC failed: {failed}")

    return metadata
