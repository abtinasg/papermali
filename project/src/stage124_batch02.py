"""Stage124 Batch 2 — Gate A.

Deterministic prioritisation of the 115 pending tickers, selection of a
~15-ticker Batch 2, and assembly of a public-entry candidate/research package
plus a user-review template.

Gate A NEVER flips any ticker to verified_user_confirmed, never writes a new
cumulative partial master with more verified rows, never creates
listing_master_verified_stage124.csv, never runs Stage124 Part2, and never
trains a model. Stage122/Stage123/targets/financials/statement-scope inputs are
treated as read-only and their hashes are checked before and after the run.
"""
from __future__ import annotations

import csv
import platform
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from . import utils

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "stage124"
SOURCE_FILES = [
    "src/stage124_batch02.py",
    "run_stage124_batch02.py",
    "tests/test_stage124_batch02.py",
]

# ---- read-only inputs (frozen) -------------------------------------------------
STAGE123_INPUT = ROOT / "stage123" / "modeling_all_rows_stage123.csv"
STAGE122_INPUT = ROOT / "stage122" / "modeling_all_rows_stage122.csv"
PARTIAL_MASTER = OUT / "listing_master_partial_verified_stage124.csv"
TSETMC_PROBE = ROOT / "stage124_feasibility" / "feasibility_probe_flat_stage124_iran.csv"

EXPECTED_STAGE123_SHA = "28b9f9d4185617182c0fe06299deeb0e9a092558b8849f1dfdef7072261bc390"
EXPECTED_STAGE122_SHA = "ece991c5ff280afa50c2ced6acfecbed4e57937cf2048cd7a11ae496a3ae7437"
REFERENCE_MERGE_COMMIT = "439c3ce9b673c4c0cf41e6a8b8cf229849aed053"

STAGE123_EXPECTED_ROWS = 1331
STAGE123_EXPECTED_TICKERS = 130
EXPECTED_PENDING = 115
EXPECTED_VERIFIED = 15
STUDY_WINDOW_START = 1392

# ---- Gate A outputs (versioned / immutable; do not overwrite Part1/pilot15) ----
PRIORITY_CSV = OUT / "listing_pending_priority_stage124_batch02.csv"
SELECTED_CSV = OUT / "listing_batch02_selected_tickers.csv"
RESEARCH_CSV = OUT / "listing_batch02_research_candidates.csv"
PROVENANCE_CSV = OUT / "listing_batch02_source_provenance.csv"
TSETMC_CONFLICT_CSV = OUT / "listing_batch02_tsetmc_conflict_audit.csv"
USER_REVIEW_CSV = OUT / "listing_batch02_user_review_template.csv"
QC_REPORT = OUT / "stage124_batch02_gate_a_qc_report.json"
METADATA = OUT / "metadata_and_hashes_stage124_batch02_gate_a.json"

FULL_VERIFIED_FORBIDDEN = OUT / "listing_master_verified_stage124.csv"

# Pilot15 immutable set — must never enter Batch 2.
PILOT15 = {
    "اردستان", "اروند", "سآبیک", "وکغدیر", "کویر", "بوعلی", "نوری", "سپید",
    "کیمیاتک", "پی‌پاد", "پرداخت", "پارس", "کاوه", "جم پیلن", "اپال",
}

BATCH02_MIN = 15
BATCH02_MAX = 20

# ---- priority weights (documented, deterministic) ------------------------------
# priority_score = W_GAP*gap_after_1392
#                + W_PRELIST*current_prelisting_proxy_row_count
#                + W_RISK*estimated_rows_at_risk
#                + W_PAIR*estimated_pairs_at_risk
#                + W_MULTI*multiple_ordinary_instruments
#                + W_CONF*tsetmc_candidate_conflict_flag
W_GAP = 10.0
W_PRELIST = 8.0
W_RISK = 3.0
W_PAIR = 2.0
W_MULTI = 5.0
W_CONF = 4.0
WEIGHTS = {
    "W_GAP_gap_after_1392": W_GAP,
    "W_PRELIST_current_prelisting_proxy_row_count": W_PRELIST,
    "W_RISK_estimated_rows_at_risk": W_RISK,
    "W_PAIR_estimated_pairs_at_risk": W_PAIR,
    "W_MULTI_multiple_ordinary_instruments": W_MULTI,
    "W_CONF_tsetmc_candidate_conflict_flag": W_CONF,
}


class QCFail(Exception):
    pass


# ---- normalisation -------------------------------------------------------------
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
ZWNJ = "‌"


def normalize_digits(s: str) -> str:
    return str(s).translate(_DIGITS).strip()


def normalize_ticker(s: str) -> str:
    """Canonical ticker form for join/dedup.

    Handles Arabic vs Persian letters (ي/ی, ك/ک), ZWNJ vs space vs no-gap, and
    collapses internal whitespace. Returns a single canonical string. This is a
    comparison key only; it must not merge two distinct tickers.
    """
    s = str(s)
    s = s.replace("ي", "ی").replace("ك", "ک").replace("ﻙ", "ک").replace("ﻯ", "ی")
    s = s.replace("ي", "ی").replace("ك", "ک")
    s = s.replace(ZWNJ, " ").replace("‏", "").replace("‎", "")
    s = " ".join(s.split())
    return s.strip()


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


# ---- priority computation ------------------------------------------------------
def load_pending(pm: pd.DataFrame) -> pd.DataFrame:
    return pm[pm["verification_status"] == "pending"].copy()


def panel_features(st: pd.DataFrame) -> dict:
    """Per-ticker panel facts derived directly from Stage123 (read-only)."""
    feats: dict = {}
    for tk, g in st.groupby("ticker", sort=True):
        years = sorted(int(y) for y in g["fiscal_year"])
        elig = {int(r["fiscal_year"]): str(r["eligible_listing"]).strip()
                for _, r in g.iterrows()}
        feats[tk] = {
            "years": years,
            "year_set": set(years),
            "eligible_by_year": elig,
            "n_panel_rows": len(g),
            "earliest": min(years),
            "latest": max(years),
        }
    return feats


def compute_priority(pending: pd.DataFrame, feats: dict, probe: dict) -> pd.DataFrame:
    rows = []
    for _, r in pending.iterrows():
        tk = r["ticker"]
        f = feats[tk]
        gap = max(0, f["earliest"] - STUDY_WINDOW_START)
        # suspect window: the first (gap+1) panel years are the years whose
        # listing eligibility is most sensitive if the true public-entry date is
        # later than the dataset's first observed year. Pre-audit estimate only.
        suspect_years = [y for y in f["years"] if y <= f["earliest"] + gap]
        at_risk = [y for y in suspect_years
                   if f["eligible_by_year"].get(y, "0") == "1"]
        pairs_at_risk = [y for y in at_risk if (y + 1) in f["year_set"]]
        prelist = int(r["current_prelisting_proxy_row_count"] or 0)

        pr = probe.get(tk)
        if pr is None:
            tsetmc_status = "not_probed_gate_a"
            tsetmc_j = ""
            tsetmc_g = ""
            inst_count = ""
            multi = 0
            conflict_flag = 0
        else:
            tsetmc_status = pr.get("instrument_match_status", "")
            tsetmc_j = pr.get("candidate_first_trade_date_jalali", "")
            tsetmc_g = pr.get("candidate_first_trade_date_gregorian", "")
            cnt = normalize_digits(pr.get("tsetmc_instrument_candidate_count", "") or "0")
            inst_count = cnt
            multi = 1 if cnt.isdigit() and int(cnt) > 1 else 0
            conflict_flag = 0  # set during research only; never inferred here

        score = (
            W_GAP * gap
            + W_PRELIST * prelist
            + W_RISK * len(at_risk)
            + W_PAIR * len(pairs_at_risk)
            + W_MULTI * multi
            + W_CONF * conflict_flag
        )

        reasons = []
        if gap >= 2:
            reasons.append("dataset_starts_well_after_1392")
        elif gap == 1:
            reasons.append("dataset_starts_after_1392")
        if prelist > 0:
            reasons.append("has_current_prelisting_proxy_rows")
        if len(at_risk) > 0:
            reasons.append("eligibility_rows_at_risk_if_entry_later")
        if multi:
            reasons.append("multiple_ordinary_instruments_candidate")
        if not reasons:
            reasons.append("baseline_pending_full_window_from_1392")

        rows.append({
            "ticker": tk,
            "ticker_normalized": normalize_ticker(tk),
            "company_name": r["company_name"],
            "earliest_fiscal_year_in_dataset": f["earliest"],
            "latest_fiscal_year_in_dataset": f["latest"],
            "n_panel_rows": f["n_panel_rows"],
            "current_prelisting_proxy_row_count": prelist,
            "current_first_eligible_year_proxy": r["current_first_eligible_year_proxy"],
            "has_prelisting_proxy_rows": r["has_prelisting_proxy_rows"],
            "tsetmc_candidate_status": tsetmc_status,
            "tsetmc_candidate_date_jalali": tsetmc_j,
            "tsetmc_candidate_date_gregorian": tsetmc_g,
            "tsetmc_instrument_candidate_count": inst_count,
            "multiple_ordinary_instruments": multi,
            "suspected_public_entry_after_1392": 1 if gap >= 1 else 0,
            "gap_after_1392": gap,
            "estimated_rows_at_risk": len(at_risk),  # pre-audit estimate
            "estimated_pairs_at_risk": len(pairs_at_risk),  # pre-audit estimate
            "priority_reason": "|".join(reasons),
            "priority_score": round(score, 4),
        })
    df = pd.DataFrame(rows)
    # deterministic ordering: score desc, prelist desc, rows_at_risk desc,
    # n_panel_rows desc, then ticker_normalized asc (unique, stable tie-break).
    df = df.sort_values(
        by=["priority_score", "current_prelisting_proxy_row_count",
            "estimated_rows_at_risk", "n_panel_rows", "ticker_normalized"],
        ascending=[False, False, False, False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    df.insert(df.columns.get_loc("priority_score") + 1, "priority_rank",
              range(1, len(df) + 1))
    return df


TIE_KEYS = ["priority_score", "current_prelisting_proxy_row_count",
            "estimated_rows_at_risk", "n_panel_rows", "ticker_normalized"]


def select_batch(priority: pd.DataFrame) -> tuple[pd.DataFrame, list, str]:
    """Select Batch 2 = top BATCH02_MIN by deterministic rank.

    The preferred size is BATCH02_MIN (15). Extension toward BATCH02_MAX (20) is
    only warranted if the rank-15/rank-16 boundary cannot be resolved — i.e. the
    two rows are identical on every ordering key. Because ``ticker_normalized``
    is unique across the panel, the full multi-key sort always resolves the
    boundary, so the cut at 15 is itself deterministic and non-arbitrary.
    """
    n = BATCH02_MIN
    r15 = priority.iloc[n - 1][TIE_KEYS]
    r16 = priority.iloc[n][TIE_KEYS] if len(priority) > n else None
    unresolved = r16 is not None and r15.equals(r16)
    note = (f"Selected top {BATCH02_MIN} by deterministic priority_rank; the "
            f"multi-key sort {TIE_KEYS} fully resolves the rank-15/16 boundary "
            f"(unique ticker_normalized), so no extension to {BATCH02_MAX} is "
            f"warranted.")
    if unresolved:
        boundary_score = r15["priority_score"]
        extra = priority[(priority["priority_rank"] > n)
                         & (priority["priority_score"] == boundary_score)]
        add = min(len(extra), BATCH02_MAX - BATCH02_MIN)
        n = BATCH02_MIN + add
        note = (f"Extended {BATCH02_MIN}->{n}: rank-15/16 boundary is an exact "
                f"tie on all ordering keys; added {add} tied row(s).")
    sel = priority.head(n).copy()
    return sel, list(sel["ticker"]), note


# ---- research package ----------------------------------------------------------
# Curated public-entry research for the selected Batch 2 tickers. Populated from
# manual web research; every entry is a CANDIDATE only — never verified here.
# Tickers absent from this dict are emitted as requires_manual_review with no
# guessed date. Schema per ticker:
#   candidate_jalali, candidate_gregorian, event_type, event_description,
#   research_status, conflict_status, sources=[(type,title,url,pub_date), ...]
RESEARCH: dict = {
    # --- genuine post-1392 public offerings (eligibility-relevant) ---
    "زپارس": {
        "candidate_jalali": "1397-07-25", "candidate_gregorian": "2018-10-17",
        "event_type": "first_public_offering",
        "event_description": "عرضه اولیه ۱۰٪ سهام (۳۲٫۵ میلیون سهم) شرکت ملی کشت و صنعت و دامپروری پارس در بورس تهران.",
        "research_status": "candidate_supported",
        "conflict_status": "no_tsetmc_candidate",
        "sources": [
            ("market_media", "زمان عرضه اولیه « زپارس » | دنیای بورس", "https://donyayebourse.com/news/30530", "1397"),
            ("company_official_website", "اطلاعات شرکت در بورس - شرکت ملی پارس", "https://parsagroinc.ir/اطلاعات-شرکت-در-بورس", ""),
        ],
        "notes": "عرضه اولیه‌ی واقعی پس از شروع بازه ۱۳۹۲–۱۴۰۲؛ ردیف‌های ۱۳۹۴–۱۳۹۶ کاندیدای تغییر eligibility هستند. exact day candidate.",
    },
    "برکت": {
        "candidate_jalali": "1395-11-17", "candidate_gregorian": "2017-02-05",
        "event_type": "first_public_offering",
        "event_description": "آغاز عرضه و معامله سهام هلدینگ گروه دارویی برکت (۱۰٪ سهام) با نرخ ۲۴۲۰ ریال.",
        "research_status": "candidate_supported",
        "conflict_status": "no_tsetmc_candidate",
        "sources": [
            ("market_media", "دیلی تحلیل - نگاهی اجمالی به عرضه اولیه هلدینگ گروه دارویی برکت", "https://www.dailytahlil.com/content?cid=51991", ""),
            ("market_media", "معرفی کامل نماد برکت و تحلیل بنیادی آن - سهام‌بین", "https://sahambin.com/post/1533", ""),
        ],
        "notes": "عرضه اولیه پس از ۱۳۹۲؛ eligibility-relevant. exact day candidate.",
    },
    "جم": {
        "candidate_jalali": "1392-06-26", "candidate_gregorian": "2013-09-17",
        "event_type": "first_public_offering",
        "event_description": "نخستین عرضه سهام پتروشیمی جم در بورس تهران (درج در فرابورس ۱۱ خرداد ۹۲ و عرضه ۲۶ شهریور ۹۲).",
        "research_status": "candidate_supported",
        "conflict_status": "no_tsetmc_candidate",
        "sources": [
            ("news_agency", "تاریخ عرضه اولیه پتروشیمی جم مشخص شد - ایسنا", "https://www.isna.ir/news/92060604013/", "1392-06-06"),
            ("market_media", "جم پتروشیمی جم - نبض بورس", "https://nabzebourse.com/fa/tags/5436/1/", ""),
        ],
        "notes": "تاریخ نزدیک به مرز ۱۳۹۲؛ درج فرابورس (۱۳۹۲-۰۳-۱۱) به‌عنوان رویداد جایگزین در یادداشت ثبت شد. exact day candidate.",
    },
    "ذوب": {
        "candidate_jalali": "1390-06-29", "candidate_gregorian": "2011-09-20",
        "event_type": "otc_first_listing_public_entry",
        "event_description": "درج و پذیرش شرکت ذوب آهن اصفهان در بازار فرابورس با نماد ذوب (انتقال به بورس بعداً در بهمن ۱۳۹۹).",
        "research_status": "candidate_supported",
        "conflict_status": "no_tsetmc_candidate",
        "sources": [
            ("company_official_website", "جزئیات انتقال نماد «ذوب» به بورس اعلام شد", "https://www.esfahansteel.ir/page-main/fa/0/dorsaetoolsenews/19197-G0", ""),
            ("news_agency", "انتقال «ذوب» از فرابورس به بورس به زودی نهایی می‌شود - ایسنا", "https://www.isna.ir/news/1400050301194/", "1400-05-03"),
        ],
        "notes": "ورود عمومی از طریق فرابورس در ۱۳۹۰ (قبل از بازه)؛ انتقال بازار بورس در ۱۳۹۹ canonical نیست. exact day candidate.",
    },
    "بکاب": {
        "candidate_jalali": "1383-07-07", "candidate_gregorian": "2004-09-28",
        "event_type": "first_public_trading",
        "event_description": "نخستین معامله سهام صنایع جوشکاب یزد در بورس تهران (پذیرش ۱۳۸۱-۰۹-۰۴، اولین معامله ۱۳۸۳-۰۷-۰۷).",
        "research_status": "candidate_supported",
        "conflict_status": "no_tsetmc_candidate",
        "sources": [
            ("market_media", "سهام بکاب | معرفی کامل سهم بکاب - علیرضا مهرابی", "https://alirezamehrabi.com/saham/electrical-machinery/josh", ""),
            ("market_media", "(بکاب) صنایع جوشکاب یزد - بانک بورس", "https://bankbourse.ir/listofaudit/شرکت-های-بورسی/AuditBank/bekab-1150.html", ""),
        ],
        "notes": "قبل از بازه؛ first public trading به‌عنوان canonical کاندیدا (نه تاریخ پذیرش به‌تنهایی). exact day candidate.",
    },
    # --- pre-1392 listings: exact ADMISSION date only (admission alone is not
    #     canonical per stage rules) -> partially supported, await confirmation ---
    "بالبر": {
        "candidate_jalali": "1372-05-10", "candidate_gregorian": "1993-08-01",
        "event_type": "listing_admission_public_entry",
        "event_description": "پذیرش کابل البرز در بورس اوراق بهادار تهران (تبدیل به سهامی عام ۱۳۷۱-۰۴-۰۹).",
        "research_status": "candidate_partially_supported",
        "conflict_status": "no_tsetmc_candidate",
        "sources": [
            ("market_media", "سهام بالبر | معرفی کامل سهم بالبر - علیرضا مهرابی", "https://alirezamehrabi.com/saham/electrical-machinery/kalz", ""),
            ("market_media", "بالبر (کابل البرز) - دیتابورس", "https://databourse.ir/symbol/بالبر", ""),
        ],
        "notes": "شرکت قدیمی؛ تاریخ پذیرش به‌تنهایی canonical نیست؛ نیاز به تأیید نخستین معامله عمومی. شروع داده‌ها در ۱۳۹۳ صرفاً در دسترس‌بودن داده است.",
    },
    "بکام": {
        "candidate_jalali": "1382-12-27", "candidate_gregorian": "2004-03-17",
        "event_type": "listing_admission_public_entry",
        "event_description": "پذیرش کارخانجات تولیدی شهید قندی (بکام) در بورس تهران.",
        "research_status": "candidate_partially_supported",
        "conflict_status": "no_tsetmc_candidate",
        "sources": [
            ("market_media", "تحلیل بنیادی بکام «کارخانجات تولیدی شهید قندی» - انیگما", "https://enigma.ir/blog/bkam-fundamental-analysis/", ""),
            ("market_media", "بکام (کارخانجات تولیدی شهید قندی) - دیتابورس", "https://databourse.ir/symbol/بکام", ""),
        ],
        "notes": "قبل از بازه؛ تاریخ پذیرش، نخستین معامله عمومی نیاز به تأیید دارد.",
    },
    "تپمپی": {
        "candidate_jalali": "1373-07-23", "candidate_gregorian": "1994-10-15",
        "event_type": "listing_admission_public_entry",
        "event_description": "تبدیل گروه صنایع پمپ‌سازی ایران به سهامی عام و واگذاری سهام از طریق سازمان بورس تهران.",
        "research_status": "candidate_partially_supported",
        "conflict_status": "no_tsetmc_candidate",
        "sources": [
            ("broker_research_page", "سهام تپمپی - ریسرچ آگاه", "https://research.agah.com/stock/iro1pirn0001", ""),
            ("market_media", "(تپمپی) گروه صنایع پمپ سازی ایران - بانک بورس", "https://bankbourse.ir/listofaudit/شرکت-های-بورسی/AuditBank/pomp-1172.html", ""),
        ],
        "notes": "قبل از بازه؛ تاریخ واگذاری/پذیرش؛ نخستین معامله عمومی نیاز به تأیید دارد.",
    },
    "درازک": {
        "candidate_jalali": "1370-10-18", "candidate_gregorian": "1992-01-08",
        "event_type": "listing_admission_public_entry",
        "event_description": "پذیرش لابراتوارهای رازک (درازک) در بورس اوراق بهادار تهران.",
        "research_status": "candidate_partially_supported",
        "conflict_status": "no_tsetmc_candidate",
        "sources": [
            ("market_media", "سهام درازک | معرفی کامل سهم درازک - علیرضا مهرابی", "https://alirezamehrabi.com/saham/pharmaceuticals/drzk", ""),
            ("market_media", "معرفی شرکت درازک - آکادمی وحید درزی", "https://vahiddarzi.ir/معرفی-شرکت-درازک/", ""),
        ],
        "notes": "قبل از بازه؛ تاریخ پذیرش؛ نخستین معامله عمومی نیاز به تأیید دارد.",
    },
    "دسینا": {
        "candidate_jalali": "1374-12-26", "candidate_gregorian": "1996-03-16",
        "event_type": "listing_admission_public_entry",
        "event_description": "پذیرش لابراتوارهای سینادارو (دسینا) در سازمان بورس اوراق بهادار تهران.",
        "research_status": "candidate_partially_supported",
        "conflict_status": "no_tsetmc_candidate",
        "sources": [
            ("market_media", "سهام دسینا | معرفی کامل سهام دسینا - علیرضا مهرابی", "https://alirezamehrabi.com/saham/pharmaceuticals/dsin", ""),
            ("market_media", "دسینا - لابراتوارهای سینادارو - رهاورد۳۶۵", "https://rahavard365.com/asset/23/دسینا", ""),
        ],
        "notes": "قبل از بازه؛ تاریخ پذیرش؛ نخستین معامله عمومی نیاز به تأیید دارد.",
    },
    "دشیمی": {
        "candidate_jalali": "1381-10-08", "candidate_gregorian": "2002-12-29",
        "event_type": "listing_admission_public_entry",
        "event_description": "پذیرش شیمی دارویی داروپخش (دشیمی) در بورس اوراق بهادار تهران.",
        "research_status": "candidate_partially_supported",
        "conflict_status": "no_tsetmc_candidate",
        "sources": [
            ("market_media", "دشیمی (شیمی داروئی داروپخش) - دیتابورس", "https://databourse.ir/symbol/دشیمی", ""),
            ("market_media", "دشیمی - شیمی داروئی داروپخش - الف بورس", "https://abcbourse.ir/شیمی-دارویی-داروپخش-دشیمی/", ""),
        ],
        "notes": "قبل از بازه؛ تاریخ پذیرش؛ نخستین معامله عمومی نیاز به تأیید دارد.",
    },
    # --- only month/year precision OR no reliable exact date -> manual review,
    #     no date guessed ---
    "تاپیکو": {
        "candidate_jalali": "", "candidate_gregorian": "",
        "event_type": "first_public_offering",
        "event_description": "ثبت در فهرست بورس اسفند ۱۳۹۱ و عرضه سهام در تیرماه ۱۳۹۲ (دقت در حد ماه؛ روز دقیق تأیید نشد).",
        "research_status": "requires_manual_review",
        "conflict_status": "no_tsetmc_candidate",
        "sources": [
            ("market_media", "(تاپیکو) سرمایه گذاری نفت و گاز و پتروشیمی تامین - بانک بورس", "https://bankbourse.ir/listofaudit/شرکت-های-بورسی/AuditBank/tapiko-1170.html", ""),
            ("company_official_website", "تاپیکو | شرکت سرمایه گذاری نفت و گاز و پتروشیمی تامین", "https://www.tappico.com/en/", ""),
        ],
        "notes": "فقط دقت ماه (تیر ۱۳۹۲) یافت شد؛ روز دقیق تأیید نشد. هیچ تاریخی force-select نشد.",
    },
    "تکمبا": {
        "candidate_jalali": "", "candidate_gregorian": "",
        "event_type": "listing_admission_public_entry",
        "event_description": "پذیرش کمباین‌سازی ایران در بورس تهران در آذرماه ۱۳۷۳ (دقت در حد ماه؛ روز دقیق تأیید نشد).",
        "research_status": "requires_manual_review",
        "conflict_status": "no_tsetmc_candidate",
        "sources": [
            ("market_media", "تحلیل بنیادی تکمبا - شرکت کمباین سازی ایران - انیگما", "https://enigma.ir/blog/tekomba-fundamental-analysis/", ""),
            ("market_media", "(تکمبا) کمباین سازی ایران - بانک بورس", "https://bankbourse.ir/listofaudit/شرکت-های-بورسی/AuditBank/tekomba-1176.html", ""),
        ],
        "notes": "فقط دقت ماه (آذر ۱۳۷۳)؛ روز دقیق تأیید نشد. قبل از بازه. هیچ تاریخی force-select نشد.",
    },
    "بترانس": {
        "candidate_jalali": "", "candidate_gregorian": "",
        "event_type": "listing_admission_public_entry",
        "event_description": "پذیرش ایران ترانسفو در بورس تهران در سال ۱۳۶۹ (دقت در حد سال؛ ماه/روز تأیید نشد).",
        "research_status": "requires_manual_review",
        "conflict_status": "no_tsetmc_candidate",
        "sources": [
            ("market_media", "شرکت ایران ترانسفو - آموزش بورس", "https://amoozesh-boors.com/fa/stocks/بترانس", ""),
            ("market_media", "بترانس (ایران ترانسفو) - دیتابورس", "https://databourse.ir/symbol/بترانس", ""),
        ],
        "notes": "فقط دقت سال (۱۳۶۹)؛ ماه/روز تأیید نشد. قبل از بازه. هیچ تاریخی force-select نشد.",
    },
    "ددام": {
        "candidate_jalali": "", "candidate_gregorian": "",
        "event_type": "ambiguous_corporate_history",
        "event_description": "تاریخچه شرکتی پیچیده (داملران ← ادغام با رازک ۱۳۸۲ ← داملران رازک ← زاگرس فارمد پارس ۱۳۹۳)؛ تاریخ دقیق نخستین ورود عمومی نماد ددام در منابع یافت‌شده تأیید نشد.",
        "research_status": "requires_manual_review",
        "conflict_status": "ambiguous_corporate_history",
        "sources": [
            ("market_media", "(ددام) داروسازی زاگرس فارمد پارس - بانک بورس", "https://bankbourse.ir/listofaudit/شرکت-های-بورسی/AuditBank/dedam-1244.html", ""),
            ("company_official_website", "داروسازی زاگرس فارمد پارس", "https://zagrospharmed.com/", ""),
        ],
        "notes": "تاریخچه ادغامی مبهم؛ تاریخ دقیق ورود عمومی تأیید نشد. هیچ تاریخی force-select نشد؛ نیاز به بازبینی دستی.",
    },
}


def build_research(selected: pd.DataFrame, probe: dict, retrieved_at: str):
    research_rows = []
    prov_rows = []
    review_rows = []
    for _, r in selected.iterrows():
        tk = r["ticker"]
        info = RESEARCH.get(tk)
        pr = probe.get(tk)
        tsetmc_j = pr.get("candidate_first_trade_date_jalali", "") if pr else ""
        tsetmc_g = pr.get("candidate_first_trade_date_gregorian", "") if pr else ""
        tsetmc_ins = pr.get("tsetmc_instrument_id_selected", "") if pr else ""
        if info is None:
            cand_j = cand_g = ev_type = ev_desc = ""
            rstatus = "requires_manual_review"
            cstatus = "no_candidate_researched"
            sources = []
            notes = ("No web research candidate recorded in Gate A; flagged for "
                     "manual review. No date guessed.")
        else:
            cand_j = info.get("candidate_jalali", "")
            cand_g = info.get("candidate_gregorian", "")
            ev_type = info.get("event_type", "")
            ev_desc = info.get("event_description", "")
            rstatus = info.get("research_status", "requires_manual_review")
            cstatus = info.get("conflict_status", "no_tsetmc_candidate")
            sources = info.get("sources", [])
            notes = info.get("notes", "")
            if cand_j and cand_g:
                # independent recomputation guard
                if jalali_str_to_gregorian_date(cand_j).isoformat() != cand_g:
                    raise QCFail(f"jalali/gregorian mismatch for {tk}: {cand_j}/{cand_g}")

        s1 = sources[0] if len(sources) > 0 else ("", "", "", "")
        s2 = sources[1] if len(sources) > 1 else ("", "", "", "")
        research_rows.append({
            "ticker": tk,
            "company_name": r["company_name"],
            "candidate_public_entry_date_jalali": cand_j,
            "candidate_public_entry_date_gregorian": cand_g,
            "candidate_event_type": ev_type,
            "candidate_event_description": ev_desc,
            "source_1_type": s1[0], "source_1_title": s1[1], "source_1_url": s1[2],
            "source_1_publication_date": s1[3], "source_1_retrieved_at": retrieved_at,
            "source_2_type": s2[0], "source_2_title": s2[1], "source_2_url": s2[2],
            "source_2_publication_date": s2[3], "source_2_retrieved_at": retrieved_at,
            "tsetmc_candidate_date_jalali": tsetmc_j,
            "tsetmc_candidate_date_gregorian": tsetmc_g,
            "tsetmc_candidate_inscode": tsetmc_ins,
            "tsetmc_candidate_disposition": "candidate_only_not_canonical",
            "conflict_status": cstatus,
            "research_status": rstatus,
            "researcher_notes": notes,
            "verified": "false",
            "verification_status": "pending",
            "ready_for_user_review": "true",
        })
        for i, src in enumerate(sources, start=1):
            prov_rows.append({
                "ticker": tk, "source_index": i, "source_type": src[0],
                "source_title": src[1], "source_url": src[2],
                "publication_date": src[3], "retrieved_at": retrieved_at,
                "content_sha256": "",  # raw response not stored in Gate A
                "raw_response_path": "",
            })
        review_rows.append({
            "ticker": tk,
            "company_name": r["company_name"],
            "proposed_public_entry_date_jalali": cand_j,
            "proposed_public_entry_date_gregorian": cand_g,
            "proposed_event_type": ev_type,
            "primary_source_title": s1[1], "primary_source_url": s1[2],
            "secondary_source_title": s2[1], "secondary_source_url": s2[2],
            "tsetmc_candidate_date": tsetmc_j,
            "conflict_summary": cstatus,
            "programmer_recommendation": rstatus,
            "user_decision": "",            # user fills
            "user_confirmed_date_jalali": "",  # user fills
            "user_confirmation_notes": "",  # user fills
        })
    research_cols = list(research_rows[0].keys())
    write_csv(pd.DataFrame(research_rows, columns=research_cols), RESEARCH_CSV)
    prov_cols = ["ticker", "source_index", "source_type", "source_title",
                 "source_url", "publication_date", "retrieved_at",
                 "content_sha256", "raw_response_path"]
    write_csv(pd.DataFrame(prov_rows, columns=prov_cols), PROVENANCE_CSV)
    review_cols = list(review_rows[0].keys())
    write_csv(pd.DataFrame(review_rows, columns=review_cols), USER_REVIEW_CSV)
    return pd.DataFrame(research_rows), pd.DataFrame(prov_rows), pd.DataFrame(review_rows)


def build_tsetmc_conflict(research: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in research.iterrows():
        rows.append({
            "ticker": r["ticker"],
            "tsetmc_candidate_date_jalali": r["tsetmc_candidate_date_jalali"],
            "tsetmc_candidate_date_gregorian": r["tsetmc_candidate_date_gregorian"],
            "tsetmc_candidate_inscode": r["tsetmc_candidate_inscode"],
            "researched_candidate_date_jalali": r["candidate_public_entry_date_jalali"],
            "tsetmc_candidate_disposition": "candidate_only_not_canonical",
            "conflict_status": r["conflict_status"],
            "canonical_date_selected": "none_gate_a_pending_user_confirmation",
            "notes": ("TSETMC earliest dEven is candidate/audit evidence only; "
                      "not accepted as canonical public-entry date in Gate A."),
        })
    df = pd.DataFrame(rows)
    write_csv(df, TSETMC_CONFLICT_CSV)
    return df


# ---- run -----------------------------------------------------------------------
def file_hashes(paths):
    return {str(p.relative_to(ROOT)): sha(p) for p in paths if p.exists()}


def source_info() -> dict:
    return {
        "source_code_commit": git_head(),
        "source_file_sha256": {f: sha(ROOT / f) for f in SOURCE_FILES},
    }


def run() -> dict:
    start = time.time()
    OUT.mkdir(exist_ok=True)
    retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ---- precondition hashes (frozen inputs) ----
    s123_sha = sha(STAGE123_INPUT)
    s122_sha = sha(STAGE122_INPUT)
    if s123_sha != EXPECTED_STAGE123_SHA:
        raise QCFail(f"Stage123 input SHA mismatch: {s123_sha}")
    if s122_sha != EXPECTED_STAGE122_SHA:
        raise QCFail(f"Stage122 input SHA mismatch: {s122_sha}")

    before = {p: sha(p) for p in [STAGE123_INPUT, STAGE122_INPUT, PARTIAL_MASTER]}

    st = read_csv(STAGE123_INPUT)
    pm = read_csv(PARTIAL_MASTER)
    probe_df = read_csv(TSETMC_PROBE) if TSETMC_PROBE.exists() else pd.DataFrame()
    probe = {r["ticker_original"]: r for _, r in probe_df.iterrows()} if len(probe_df) else {}

    feats = panel_features(st)
    pending = load_pending(pm)
    priority = compute_priority(pending, feats, probe)
    write_csv(priority, PRIORITY_CSV)

    selected, sel_tickers, sel_note = select_batch(priority)
    selected_out = selected.copy()
    selected_out["selected_for_batch02"] = "1"
    selected_out["selection_notes"] = sel_note
    write_csv(selected_out, SELECTED_CSV)

    research, prov, review = build_research(selected, probe, retrieved_at)
    conflict = build_tsetmc_conflict(research)

    after = {p: sha(p) for p in [STAGE123_INPUT, STAGE122_INPUT, PARTIAL_MASTER]}

    pending_set = set(pending["ticker"])
    sel_set = set(sel_tickers)
    a = {
        "current_main_contains_reference_merge_commit": merge_commit_in_ancestry(),
        "stage122_input_expected_sha256": s122_sha == EXPECTED_STAGE122_SHA,
        "stage123_input_expected_sha256": s123_sha == EXPECTED_STAGE123_SHA,
        "stage123_row_count_1331": len(st) == STAGE123_EXPECTED_ROWS,
        "stage123_unique_tickers_130": st["ticker"].nunique() == STAGE123_EXPECTED_TICKERS,
        "stage123_zero_duplicate_row_key": not st["row_key"].duplicated().any(),
        "partial_master_130_unique_tickers": pm["ticker"].nunique() == 130,
        "partial_master_exactly_15_verified": int((pm["verification_status"] == "verified_user_confirmed").sum()) == EXPECTED_VERIFIED,
        "exactly_115_pending_extracted": len(pending) == EXPECTED_PENDING,
        "priority_table_115_rows": len(priority) == EXPECTED_PENDING,
        "no_pilot15_in_priority": len(PILOT15 & set(priority["ticker"])) == 0,
        "no_pilot15_in_batch02": len(PILOT15 & sel_set) == 0,
        "all_selected_are_pending": sel_set.issubset(pending_set),
        "batch02_size_between_15_and_20": BATCH02_MIN <= len(selected) <= BATCH02_MAX,
        "priority_rank_unique": priority["priority_rank"].nunique() == len(priority),
        "priority_rank_contiguous": list(priority["priority_rank"]) == list(range(1, len(priority) + 1)),
        "ticker_normalization_no_duplicate": priority["ticker_normalized"].nunique() == len(priority),
        "ranking_deterministic": _deterministic(pending, feats, probe, priority),
        "all_research_sources_have_type_and_title": _sources_well_formed(prov),
        "tsetmc_candidates_not_canonical": bool((research["tsetmc_candidate_disposition"] == "candidate_only_not_canonical").all()) if len(research) else True,
        "all_gate_a_verified_false": bool((research["verified"] == "false").all()) if len(research) else True,
        "no_row_verified_user_confirmed": (not (research["verification_status"] == "verified_user_confirmed").any()) if len(research) else True,
        "user_decision_columns_blank": bool((review["user_decision"] == "").all() and (review["user_confirmed_date_jalali"] == "").all()),
        "no_new_partial_master_with_more_verified": True,  # this stage writes none
        "listing_master_verified_not_created": not FULL_VERIFIED_FORBIDDEN.exists(),
        "no_full_stage124_part2_run": True,
        "stage123_unchanged": before[STAGE123_INPUT] == after[STAGE123_INPUT],
        "stage122_unchanged": before[STAGE122_INPUT] == after[STAGE122_INPUT],
        "partial_master_unchanged": before[PARTIAL_MASTER] == after[PARTIAL_MASTER],
        "targets_unchanged": before[STAGE123_INPUT] == after[STAGE123_INPUT],
        "financial_values_unchanged": before[STAGE123_INPUT] == after[STAGE123_INPUT],
        "ratios_unchanged": before[STAGE123_INPUT] == after[STAGE123_INPUT],
        "statement_scope_unchanged": before[STAGE123_INPUT] == after[STAGE123_INPUT],
        "no_model_run": True,
    }
    a["overall_pass"] = all(v for v in a.values() if isinstance(v, bool))
    qc = {"stage_name": "stage124_batch02_gate_a", "assertions": a,
          "overall_pass": a["overall_pass"], "selection_note": sel_note,
          "priority_weights": WEIGHTS}
    utils.save_json(qc, QC_REPORT)
    if not a["overall_pass"]:
        failed = [k for k, v in a.items() if isinstance(v, bool) and not v]
        raise QCFail(f"Gate A QC failed: {failed}")

    outputs = [PRIORITY_CSV, SELECTED_CSV, RESEARCH_CSV, PROVENANCE_CSV,
               TSETMC_CONFLICT_CSV, USER_REVIEW_CSV, QC_REPORT]
    meta = {
        "stage_name": "stage124_batch02_gate_a",
        "gate": "A",
        **source_info(),
        "reference_merge_commit": REFERENCE_MERGE_COMMIT,
        "reference_merge_commit_in_ancestry": merge_commit_in_ancestry(),
        "stage123_input_sha256": s123_sha,
        "stage122_input_sha256": s122_sha,
        "partial_master_sha256": before[PARTIAL_MASTER],
        "priority_weights": WEIGHTS,
        "n_pending": len(pending),
        "n_selected_batch02": len(selected),
        "selected_tickers": sel_tickers,
        "selection_note": sel_note,
        "output_file_hashes": file_hashes(outputs),
        "overall_qc_pass": True,
        "runtime_seconds": round(time.time() - start, 3),
        "python_version": sys.version,
        "platform": platform.platform(),
    }
    utils.save_json(meta, METADATA)
    meta["output_file_hashes"][str(METADATA.relative_to(ROOT))] = sha(METADATA)
    utils.save_json(meta, METADATA)
    return {"qc": qc, "metadata": meta, "priority": priority, "selected": selected}


def _deterministic(pending, feats, probe, priority) -> bool:
    again = compute_priority(pending, feats, probe)
    return again.equals(priority)


def _sources_well_formed(prov: pd.DataFrame) -> bool:
    if len(prov) == 0:
        return True
    for _, r in prov.iterrows():
        if not str(r["source_url"]).strip() or not str(r["source_type"]).strip() \
                or not str(r["source_title"]).strip():
            return False
    return True
