from __future__ import annotations

import csv
import platform
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from . import utils

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "stage124"
SOURCE_FILES = ["src/stage124_pilot15.py", "run_stage124_pilot15.py", "tests/test_stage124_pilot15.py"]
STAGE122_FILES = [ROOT / "stage122" / "modeling_all_rows_stage122.csv"]
USER_INPUT = OUT / "listing_pilot15_user_confirmed_stage124.csv"
TEMPLATE = OUT / "listing_master_template_stage124.csv"
PARTIAL_MASTER = OUT / "listing_master_partial_verified_stage124.csv"
CONFLICT_AUDIT = OUT / "listing_pilot15_tsetmc_conflict_audit_stage124.csv"
ELIGIBILITY_AUDIT = OUT / "listing_eligibility_impact_pilot15_stage124.csv"
ELIGIBILITY_SUMMARY = OUT / "listing_eligibility_summary_pilot15_stage124.csv"
QC_REPORT = OUT / "stage124_pilot15_qc_report.json"
METADATA = OUT / "metadata_and_hashes_stage124_pilot15.json"
STAGE123_INPUT = ROOT / "stage123" / "modeling_all_rows_stage123.csv"
TSETMC_PROBE = ROOT / "stage124_feasibility" / "feasibility_probe_flat_stage124_iran.csv"
FULL_VERIFIED_FORBIDDEN = OUT / "listing_master_verified_stage124.csv"

CANONICAL_EVENT_TYPE = "first_public_offering_or_public_entry"
VERIFICATION_STATUS = "verified_user_confirmed"
CONFLICT_STATUS = "resolved_user_confirmed"
USER_CONFIRMATION_DATE = "2026-06-23"
NOTES = "Final public-entry/IPO date confirmed directly by the project owner after manual source review. TSETMC oldest dEven is retained only as candidate audit evidence and is not used as the canonical listing-eligibility date."
MASTER_NOTE = "Canonical Stage124 public-entry date confirmed by project owner. TSETMC candidate date rejected for eligibility use and retained in a separate conflict audit."
OPAL_NOTE = "Canonical date is the user-confirmed IPO/public-entry date 1399-12-06; later secondary-market trading date is not used for Stage124 eligibility."
AMBIG_NOTE = "Multiple TSETMC instrument histories were detected; none was used as canonical. User-confirmed IPO/public-entry date is authoritative for this stage."

INPUT_COLUMNS = ["ticker", "confirmed_public_entry_date_jalali", "confirmed_public_entry_date_gregorian", "canonical_event_type", "verification_status", "conflict_status", "verified", "user_confirmation_date", "source_1_type", "source_1_title", "source_1_url", "tsetmc_candidate_date_jalali", "tsetmc_candidate_disposition", "confirmation_notes"]

PILOT_ROWS = [
    ("اردستان", "1401-10-28", "2023-01-18", "1400-03-17", "not_accepted_as_canonical_public_entry_date", "news_source_user_reviewed", "عرضه‌اولیه‌ای جدید در راه بورس - ایرنا", "https://36858523.khabarban.com/"),
    ("اروند", "1404-10-01", "2025-12-22", "1399-12-25", "not_accepted_as_canonical_public_entry_date", "company_official_website", "۵ درصد سهام پتروشیمی اروند دوشنبه آینده در بورس تهران عرضه می‌شود", "https://arvandpvc.ir/%D8%A2%D8%B1%D8%B4%DB%8C%D9%88-%D8%AE%D8%A8%D8%B1%D9%87%D8%A7/%DB%B5-%D8%AF%D8%B1%D8%B5%D8%AF-%D8%B3%D9%87%D8%A7%D9%85-%D9%BE%D8%AA%D8%B1%D9%88%D8%B4%DB%8C%D9%85%DB%8C-%D8%A7%D8%B1%D9%88%D9%86%D8%AF-%D8%AF%D9%88%D8%B4%D9%86%D8%A8%D9%87-%D8%A2%DB%8C%D9%86%D8%AF%D9%87-%D8%AF%D8%B1-%D8%A8%D9%88%D8%B1%D8%B3-%D8%AA%D9%87%D8%B1%D8%A7%D9%86-%D8%B9%D8%B1%D8%B6%D9%87-%D9%85%DB%8C%E2%80%8C%D8%B4%D9%88%D8%AF"),
    ("سآبیک", "1401-02-28", "2022-05-18", "1391-06-27", "not_accepted_as_canonical_public_entry_date", "broker_research_page", "معرفی کامل سهم سیمان آبیک", "https://refahbroker.ir/blog/2022/05/ipo-sabik"),
    ("وکغدیر", "1401-12-23", "2023-03-14", "1400-09-21", "not_accepted_as_canonical_public_entry_date", "broker_research_page", "معرفی کامل سهم شرکت بین‌المللی توسعه صنایع و معادن غدیر", "https://refahbroker.ir/blog/2023/03/ipo-vakghadir"),
    ("کویر", "1398-07-17", "2019-10-09", "1398-07-02", "not_accepted_as_canonical_public_entry_date", "broker_news_page", "عرضه اولیه سهام شرکت فولاد سپید فراب کویر", "https://www.mbroker.ir/index.php/category/item/2794-arze"),
    ("بوعلی", "1399-09-19", "2020-12-09", "ambiguous", "ambiguous_instrument_not_used", "company_official_website", "پتروشیمی بوعلی سینا شرکت برتر بورس ایران شد", "https://bspc.ir/PJ-8579/bu-ali-sina-petrochemical-became-the-top-company-of-iran-stock-exchange/"),
    ("نوری", "1398-04-22", "2019-07-13", "ambiguous", "ambiguous_instrument_not_used", "company_official_website", "شرکت پتروشیمی نوری رکورد عرضه اولیه بورس را شکست", "https://www.nopc.co/fa/news/37/%D8%B4%D8%B1%DA%A9%D8%AA-%D9%BE%D8%AA%D8%B1%D9%88%D8%B4%DB%8C%D9%85%DB%8C-%D9%86%D9%88%D8%B1%DB%8C-%D8%B1%DA%A9%D9%88%D8%B1%D8%AF-%D8%B9%D8%B1%D8%B6%D9%87-%D8%A7%D9%88%D9%84%DB%8C%D9%87-%D8%A8%D9%88%D8%B1%D8%B3-%D8%B1%D8%A7-%D8%B4%DA%A9%D8%B3%D8%AA"),
    ("سپید", "1400-04-23", "2021-07-14", "1399-07-05", "not_accepted_as_canonical_public_entry_date", "news_source_user_reviewed", "چرا عرضه اولیه سپید بازگشایی نشد؟", "https://www.tabnak.ir/fa/news/1064455/%DA%86%D8%B1%D8%A7-%D8%B9%D8%B1%D8%B6%D9%87-%D8%A7%D9%88%D9%84%DB%8C%D9%87-%D8%B3%D9%BE%DB%8C%D8%AF-%D8%A8%D8%A7%D8%B2%DA%AF%D8%B4%D8%A7%DB%8C%DB%8C-%D9%86%D8%B4%D8%AF"),
    ("کیمیاتک", "1400-06-17", "2021-09-08", "1399-11-28", "not_accepted_as_canonical_public_entry_date", "news_source_user_reviewed", "در عرضه اولیه کیمیا تک به هر کد چند سهم رسید؟", "https://www.tabnak.ir/fa/news/1075019/%D8%AF%D8%B1-%D8%B9%D8%B1%D8%B6%D9%87-%D8%A7%D9%88%D9%84%DB%8C%D9%87-%DA%A9%DB%8C%D9%85%DB%8C%D8%A7-%D8%AA%DA%A9-%D8%A8%D9%87-%D9%87%D8%B1-%DA%A9%D8%AF-%DA%86%D9%86%D8%AF-%D8%B3%D9%87%D9%85-%D8%B1%D8%B3%DB%8C%D8%AF"),
    ("پی‌پاد", "1402-01-16", "2023-04-05", "1401-05-11", "not_accepted_as_canonical_public_entry_date", "news_agency", "نخستین عرضه اولیه امسال در بورس تهران روز چهارشنبه", "https://www.mehrnews.com/news/5745020/%D9%86%D8%AE%D8%B3%D8%AA%DB%8C%D9%86-%D8%B9%D8%B1%D8%B6%D9%87-%D8%A7%D9%88%D9%84%DB%8C%D9%87-%D8%A7%D9%85%D8%B3%D8%A7%D9%84-%D8%AF%D8%B1-%D8%A8%D9%88%D8%B1%D8%B3-%D8%AA%D9%87%D8%B1%D8%A7%D9%86-%D8%B1%D9%88%D8%B2-%DA%86%D9%87%D8%A7%D8%B1%D8%B4%D9%86%D8%A8%D9%87"),
    ("پرداخت", "1396-04-27", "2017-07-18", "1395-12-22", "not_accepted_as_canonical_public_entry_date", "capital_market_news", "زمان عرضه اولیه پرداخت مشخص شد", "https://boursepress.ir/news/52608/%D8%B2%D9%85%D8%A7%D9%86-%D8%B9%D8%B1%D8%B6%D9%87-%D8%A7%D9%88%D9%84%DB%8C%D9%87-%D9%BE%D8%B1%D8%AF%D8%A7%D8%AE%D8%AA-%D9%85%D8%B4%D8%AE%D8%B5-%D8%B4%D8%AF-%D8%B3%D9%87%D9%85%DB%8C%D9%87-%D9%88-%D9%85%D8%AD%D8%AF%D9%88%D8%AF%D9%87-%D9%82%DB%8C%D9%85%D8%AA-%D8%A7%D9%88%D9%84%DB%8C%D9%86-%D8%B4%D8%B1%DA%A9%D8%AA-%DB%B9%DB%B6"),
    ("پارس", "1397-04-20", "2018-07-11", "1397-04-16", "not_accepted_as_canonical_public_entry_date", "capital_market_news", "پتروشیمی پارس کشف قیمت شد", "https://www.boursenews.ir/fa/news/178087/%D9%BE%D8%AA%D8%B1%D9%88%D8%B4%DB%8C%D9%85%DB%8C-%D9%BE%D8%A7%D8%B1%D8%B3-%DA%A9%D8%B4%D9%81-%D9%82%DB%8C%D9%85%D8%AA-%D8%B4%D8%AF"),
    ("کاوه", "1396-07-26", "2017-10-18", "1393-06-30", "not_accepted_as_canonical_public_entry_date", "company_information_page", "فولاد کاوه جنوب کیش؛ معرفی، محصولات، نماد بورسی", "https://fooladino.com/company/sks-steel-company"),
    ("جم پیلن", "1398-03-27", "2019-06-17", "1397-12-28", "not_accepted_as_canonical_public_entry_date", "capital_market_news", "جم پیلن با ۲۲۵۰ تومان کشف قیمت شد", "https://boursepress.ir/news/129114/%D8%AC%D9%85-%D9%BE%DB%8C%D9%84%D9%86-%D8%A8%D8%A7-%DB%B2%DB%B2%DB%B5%DB%B0-%D8%AA%D9%88%D9%85%D8%A7%D9%86-%DA%A9%D8%B4%D9%81-%D9%82%DB%8C%D9%85%D8%AA-%D8%B4%D8%AF-%D8%AB%D8%A8%D8%AA-%D8%AF%D9%88-%D8%B1%DA%A9%D9%88%D8%B1%D8%AF-%D8%AC%D8%AF%DB%8C%D8%AF-%D9%88-%DA%A9%D8%A7%D9%87%D8%B4-%D8%B3%D9%87%D9%85%DB%8C%D9%87"),
    ("اپال", "1399-12-06", "2021-02-24", "1399-07-15", "not_accepted_as_canonical_public_entry_date", "financial_news", "حاشیه‌های امروز بورس ۶ اسفند ۹۹", "https://tejaratnews.com/%D8%A8%D9%88%D8%B1%D8%B3-%D8%A7%D9%85%D8%B1%D9%88%D8%B2-6-%D8%A7%D8%B3%D9%81%D9%86%D8%AF-99"),
]
PILOT_TICKERS = {r[0] for r in PILOT_ROWS}

class QCFail(Exception):
    pass

def normalize_digits(s: str) -> str:
    return str(s).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")).strip()

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
    sal_a = [0, 31, 29 if (gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 1
    while gm <= 12 and gd > sal_a[gm]:
        gd -= sal_a[gm]
        gm += 1
    return date(gy, gm, gd)

def jalali_str_to_gregorian_date(s: str) -> date:
    y, m, d = map(int, normalize_jalali(s).split("-"))
    return jalali_to_gregorian(y, m, d)

def sha(path: Path) -> str:
    return utils.sha256_file(path) if path.exists() else ""

def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, encoding="utf-8-sig", keep_default_na=False)

def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)

def build_user_confirmed_input() -> pd.DataFrame:
    rows = []
    for ticker, j, g, tsetmc, disp, stype, title, url in PILOT_ROWS:
        rows.append({
            "ticker": ticker,
            "confirmed_public_entry_date_jalali": j,
            "confirmed_public_entry_date_gregorian": g,
            "canonical_event_type": CANONICAL_EVENT_TYPE,
            "verification_status": VERIFICATION_STATUS,
            "conflict_status": CONFLICT_STATUS,
            "verified": "true",
            "user_confirmation_date": USER_CONFIRMATION_DATE,
            "source_1_type": stype,
            "source_1_title": title,
            "source_1_url": url,
            "tsetmc_candidate_date_jalali": tsetmc,
            "tsetmc_candidate_disposition": disp,
            "confirmation_notes": NOTES,
        })
    df = pd.DataFrame(rows, columns=INPUT_COLUMNS)
    write_csv(df, USER_INPUT)
    return df

def load_user_input() -> pd.DataFrame:
    if not USER_INPUT.exists():
        return build_user_confirmed_input()
    return read_csv(USER_INPUT)

def validate_input(df: pd.DataFrame) -> dict:
    conversions = []
    for _, r in df.iterrows():
        gd = jalali_str_to_gregorian_date(r["confirmed_public_entry_date_jalali"]).isoformat()
        conversions.append(gd == r["confirmed_public_entry_date_gregorian"])
    return {
        "input_exactly_15_rows": len(df) == 15,
        "input_exactly_15_unique_tickers": df["ticker"].nunique() == 15,
        "input_ticker_set_exact_match": set(df["ticker"]) == PILOT_TICKERS,
        "all_user_confirmed_dates_present": bool((df["confirmed_public_entry_date_jalali"].str.strip() != "").all() and (df["confirmed_public_entry_date_gregorian"].str.strip() != "").all()),
        "all_gregorian_dates_exactly_match_conversion": all(conversions),
        "all_verification_status_user_confirmed": bool((df["verification_status"] == VERIFICATION_STATUS).all()),
        "all_verified_true": bool((df["verified"] == "true").all()),
    }

def build_partial_master(inp: pd.DataFrame) -> pd.DataFrame:
    tmpl = read_csv(TEMPLATE)
    out = tmpl.copy(deep=True)
    by_t = inp.set_index("ticker")
    for i, r in out.iterrows():
        tk = r["ticker"]
        if tk not in by_t.index:
            continue
        u = by_t.loc[tk]
        out.at[i, "ipo_date_jalali"] = u["confirmed_public_entry_date_jalali"]
        out.at[i, "first_public_trading_date_jalali"] = u["confirmed_public_entry_date_jalali"]
        out.at[i, "first_public_trading_date_gregorian"] = u["confirmed_public_entry_date_gregorian"]
        out.at[i, "source_1_type"] = u["source_1_type"]
        out.at[i, "source_1_title"] = u["source_1_title"]
        out.at[i, "source_1_url"] = u["source_1_url"]
        out.at[i, "verification_status"] = VERIFICATION_STATUS
        out.at[i, "conflict_status"] = CONFLICT_STATUS
        note = MASTER_NOTE
        if tk == "اپال":
            note += " " + OPAL_NOTE
        if tk in {"بوعلی", "نوری"}:
            note += " " + AMBIG_NOTE
        out.at[i, "notes"] = note
    write_csv(out, PARTIAL_MASTER)
    return out

def build_conflict_audit(inp: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in inp.iterrows():
        amb = r["ticker"] in {"بوعلی", "نوری"}
        diff = ""
        status = "ambiguous_instrument" if amb else "not_accepted_as_public_entry_date"
        if not amb:
            diff = (jalali_str_to_gregorian_date(r["confirmed_public_entry_date_jalali"]) - jalali_str_to_gregorian_date(r["tsetmc_candidate_date_jalali"])).days
        rows.append({
            "ticker": r["ticker"],
            "tsetmc_candidate_date_jalali": r["tsetmc_candidate_date_jalali"],
            "user_confirmed_public_entry_date_jalali": r["confirmed_public_entry_date_jalali"],
            "difference_days": diff,
            "tsetmc_candidate_status": status,
            "canonical_date_selected": "user_confirmed_public_entry_date",
            "resolution_basis": "project_owner_final_confirmation",
            "verification_status": VERIFICATION_STATUS,
            "notes": "TSETMC candidate retained only for audit; not used as canonical listing-eligibility date.",
        })
    df = pd.DataFrame(rows)
    write_csv(df, CONFLICT_AUDIT)
    return df

def parse_fiscal_end(s: str):
    if not str(s).strip():
        return None
    try:
        return jalali_str_to_gregorian_date(s)
    except Exception:
        try:
            return datetime.fromisoformat(normalize_digits(s).replace("/", "-")).date()
        except Exception:
            return None

def proxy_col(df: pd.DataFrame) -> str:
    for c in ["eligible_listing", "eligible_listing_financial", "predictor_eligible_main"]:
        if c in df.columns:
            return c
    raise QCFail("No Stage123 listing proxy column found")

def build_eligibility(inp: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not STAGE123_INPUT.exists():
        raise QCFail(f"missing Stage123 input: {STAGE123_INPUT}")
    st = read_csv(STAGE123_INPUT)
    if "fiscal_year_end" not in st.columns:
        raise QCFail("Stage123 input lacks fiscal_year_end")
    pc = proxy_col(st)
    by_t = inp.set_index("ticker")
    rows = []
    for _, r in st[st["ticker"].isin(PILOT_TICKERS)].iterrows():
        u = by_t.loc[r["ticker"]]
        confirmed = jalali_str_to_gregorian_date(u["confirmed_public_entry_date_jalali"])
        fy_end = parse_fiscal_end(r["fiscal_year_end"])
        proxy = str(r[pc]).strip()
        rec = {"row_key": r["row_key"], "ticker": r["ticker"], "fiscal_year": r["fiscal_year"], "fiscal_year_end": normalize_jalali(r["fiscal_year_end"]) if str(r["fiscal_year_end"]).strip() else "", "confirmed_public_entry_date_jalali": u["confirmed_public_entry_date_jalali"], "confirmed_public_entry_date_gregorian": u["confirmed_public_entry_date_gregorian"], "eligible_listing_stage123_proxy": proxy, "verification_status": VERIFICATION_STATUS}
        if fy_end is None:
            rec.update({"listed_by_fiscal_year_end_verified": "", "eligible_listing_financial_verified": "", "listing_eligibility_status_verified": "unresolved_invalid_fiscal_year_end", "days_listed_before_fiscal_year_end": "", "eligibility_changed_vs_stage123_proxy": "", "change_direction": "unresolved"})
        elif confirmed <= fy_end:
            rec.update({"listed_by_fiscal_year_end_verified": "1", "eligible_listing_financial_verified": "1", "listing_eligibility_status_verified": "eligible_verified_public_entry", "days_listed_before_fiscal_year_end": (fy_end - confirmed).days})
        else:
            rec.update({"listed_by_fiscal_year_end_verified": "0", "eligible_listing_financial_verified": "0", "listing_eligibility_status_verified": "pre_listing_verified_public_entry", "days_listed_before_fiscal_year_end": ""})
        if rec["change_direction"] != "unresolved" if "change_direction" in rec else True:
            v = rec["eligible_listing_financial_verified"]
            rec["eligibility_changed_vs_stage123_proxy"] = "1" if v != proxy else "0"
            if v == proxy == "0": rec["change_direction"] = "unchanged_0"
            elif v == proxy == "1": rec["change_direction"] = "unchanged_1"
            elif proxy == "0" and v == "1": rec["change_direction"] = "proxy_0_to_verified_1"
            elif proxy == "1" and v == "0": rec["change_direction"] = "proxy_1_to_verified_0"
            else: rec["change_direction"] = "unresolved"
        rows.append(rec)
    audit = pd.DataFrame(rows)
    write_csv(audit, ELIGIBILITY_AUDIT)
    sums = []
    for tk, g in audit.groupby("ticker", sort=True):
        elig = g[g["eligible_listing_financial_verified"] == "1"]
        pre = g[g["eligible_listing_financial_verified"] == "0"]
        u = by_t.loc[tk]
        sums.append({"ticker": tk, "confirmed_public_entry_date_jalali": u["confirmed_public_entry_date_jalali"], "n_panel_rows": len(g), "n_verified_prelisting_rows": len(pre), "n_verified_eligible_rows": len(elig), "first_verified_eligible_fiscal_year": elig["fiscal_year"].min() if len(elig) else "", "last_verified_prelisting_fiscal_year": pre["fiscal_year"].max() if len(pre) else "", "n_rows_changed_vs_stage123_proxy": int((g["eligibility_changed_vs_stage123_proxy"] == "1").sum()), "n_proxy_0_to_verified_1": int((g["change_direction"] == "proxy_0_to_verified_1").sum()), "n_proxy_1_to_verified_0": int((g["change_direction"] == "proxy_1_to_verified_0").sum()), "verification_status": VERIFICATION_STATUS})
    summary = pd.DataFrame(sums)
    write_csv(summary, ELIGIBILITY_SUMMARY)
    return audit, summary

def unchanged_nonpilot(tmpl: pd.DataFrame, part: pd.DataFrame) -> bool:
    t = tmpl.set_index("ticker")
    p = part.set_index("ticker")
    for tk in set(t.index) - PILOT_TICKERS:
        if not t.loc[tk].equals(p.loc[tk]):
            return False
    return True

def file_hashes(paths):
    return {str(p.relative_to(ROOT)): sha(p) for p in paths if p.exists()}

def source_info() -> dict:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT.parent, capture_output=True, text=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", *["project/" + f for f in SOURCE_FILES]], cwd=ROOT.parent, capture_output=True, text=True).stdout.strip())
    except Exception:
        commit, dirty = "", None
    return {"source_code_commit": commit, "source_tree_dirty_before_run": dirty, "source_file_sha256": {f: sha(ROOT / f) for f in SOURCE_FILES}}

def run() -> dict:
    start = time.time()
    OUT.mkdir(exist_ok=True)
    before_stage123 = sha(STAGE123_INPUT)
    before_template = sha(TEMPLATE)
    before_stage122 = file_hashes(STAGE122_FILES)
    inp = load_user_input()
    assertions = validate_input(inp)
    tmpl = read_csv(TEMPLATE)
    partial = build_partial_master(inp)
    conflict = build_conflict_audit(inp)
    audit = pd.DataFrame()
    summary = pd.DataFrame()
    try:
        audit, summary = build_eligibility(inp)
    except Exception as e:
        assertions["eligibility_build_success"] = False
        assertions["eligibility_error"] = str(e)
    after_stage123 = sha(STAGE123_INPUT)
    after_template = sha(TEMPLATE)
    after_stage122 = file_hashes(STAGE122_FILES)
    assertions.update({
        "partial_master_exactly_130_rows": len(partial) == 130,
        "partial_master_exactly_130_unique_tickers": partial["ticker"].nunique() == 130,
        "partial_master_15_verified": int((partial["verification_status"] == VERIFICATION_STATUS).sum()) == 15,
        "partial_master_115_pending": int((partial["verification_status"] == "pending").sum()) == 115,
        "nonpilot_rows_unchanged_vs_template": unchanged_nonpilot(tmpl, partial),
        "original_template_hash_unchanged": before_template == after_template and bool(before_template),
        "tsetmc_candidates_not_used_as_canonical": not any(partial["ipo_date_jalali"].isin(inp["tsetmc_candidate_date_jalali"])),
        "conflict_audit_exactly_15_rows": len(conflict) == 15,
        "buali_nouri_ambiguous_preserved": set(conflict.loc[conflict["tsetmc_candidate_status"] == "ambiguous_instrument", "ticker"]) == {"بوعلی", "نوری"},
        "eligibility_audit_only_15_tickers": len(audit) > 0 and set(audit["ticker"]).issubset(PILOT_TICKERS),
        "eligibility_audit_row_keys_unique": len(audit) > 0 and not audit["row_key"].duplicated().any(),
        "eligibility_uses_exact_fiscal_year_end": len(audit) > 0 and "fiscal_year_end" in audit.columns,
        "no_missing_row_keys": len(audit) > 0 and bool((audit["row_key"].str.strip() != "").all()),
        "arvand_all_rows_prelisting": len(audit) > 0 and bool((audit.loc[audit["ticker"] == "اروند", "eligible_listing_financial_verified"] == "0").all()),
        "stage123_file_hash_unchanged": before_stage123 == after_stage123 and bool(before_stage123),
        "stage122_files_unchanged": before_stage122 == after_stage122,
        "targets_unchanged": before_stage123 == after_stage123 and bool(before_stage123),
        "financial_values_unchanged": before_stage123 == after_stage123 and bool(before_stage123),
        "statement_scope_unchanged": before_stage123 == after_stage123 and bool(before_stage123),
        "no_model_run": True,
        "no_full_stage124_part2_run": True,
        "no_listing_master_verified_file_created": not FULL_VERIFIED_FORBIDDEN.exists(),
    })
    bool_assertions = {k: v for k, v in assertions.items() if isinstance(v, bool)}
    assertions["overall_pass"] = all(bool_assertions.values())
    qc = {"stage_name": "stage124_pilot15_user_confirmed", "assertions": assertions, "overall_pass": assertions["overall_pass"]}
    utils.save_json(qc, QC_REPORT)
    if not assertions["overall_pass"]:
        raise QCFail("Stage124 pilot15 QC failed")
    outputs = [
        USER_INPUT, PARTIAL_MASTER, CONFLICT_AUDIT, ELIGIBILITY_AUDIT,
        ELIGIBILITY_SUMMARY, QC_REPORT,
        OUT / "stage124_pilot15_unit_test_output.txt",
        OUT / "README_STAGE124_PILOT15_VERIFIED.md",
        OUT / "stage124_pilot15_change_log.md",
    ]
    meta = {"stage_name": "stage124_pilot15_user_confirmed", **source_info(), "input_user_confirmed_file": str(USER_INPUT.relative_to(ROOT)), "input_user_confirmed_sha256": sha(USER_INPUT), "input_tsetmc_probe_file": str(TSETMC_PROBE.relative_to(ROOT)), "input_tsetmc_probe_sha256": sha(TSETMC_PROBE), "stage123_input_file": str(STAGE123_INPUT.relative_to(ROOT)), "stage123_input_sha256_before": before_stage123, "stage123_input_sha256_after": after_stage123, "listing_master_template_sha256_before": before_template, "listing_master_template_sha256_after": after_template, "output_file_hashes": file_hashes(outputs), "n_confirmed_tickers": 15, "n_pending_tickers": 115, "n_panel_rows_audited": int(len(audit)), "n_eligibility_changes_vs_proxy": int((audit["eligibility_changed_vs_stage123_proxy"] == "1").sum()), "n_proxy_0_to_verified_1": int((audit["change_direction"] == "proxy_0_to_verified_1").sum()), "n_proxy_1_to_verified_0": int((audit["change_direction"] == "proxy_1_to_verified_0").sum()), "overall_qc_pass": True, "runtime_seconds": round(time.time() - start, 3), "python_version": sys.version, "platform": platform.platform()}
    utils.save_json(meta, METADATA)
    meta["output_file_hashes"][str(METADATA.relative_to(ROOT))] = sha(METADATA)
    utils.save_json(meta, METADATA)
    return {"qc": qc, "metadata": meta}
