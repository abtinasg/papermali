#!/usr/bin/env python3
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    import jdatetime
except Exception:
    jdatetime = None

PROJECT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
TEMPLATE = PROJECT / "stage124" / "listing_master_template_stage124.csv"
SCRIPT = Path(__file__).resolve()
RAW_ROOT = HERE / "raw"
TSETMC_RAW = RAW_ROOT / "tsetmc"
CODAL_RAW = RAW_ROOT / "codal"
OUT_CSV = HERE / "feasibility_probe_flat_stage124_iran.csv"
OUT_REPORT = HERE / "feasibility_probe_report_stage124_iran.json"
OUT_MANIFEST = HERE / "raw_responses_manifest_stage124_iran.csv"
OUT_CANDIDATE_HISTORY = HERE / "instrument_candidate_history_stage124_iran.csv"
SOURCE_PROVENANCE_FILES = [
    "project/stage124_feasibility/probe_listing_sources_stage124_v2.py",
    "project/tests/test_stage124_feasibility.py",
    "project/stage124_feasibility/README.md",
    "project/stage124_feasibility/README_STAGE124_IRAN_PROBE.md",
]

PILOT_TICKERS = ["اردستان", "اروند", "سآبیک", "وکغدیر", "کویر", "بوعلی", "نوری", "سپید", "کیمیاتک", "پی‌پاد", "پرداخت", "پارس", "کاوه", "جم پیلن", "اپال"]
CODAL_HINTS = ["عرضه اولیه", "پذیرش", "درج نماد", "آغاز معاملات", "گشایش نماد", "امیدنامه", "عرضه سهام"]
STATUS_VALUES = {"candidate_found", "network_unreachable", "no_instrument_match", "ambiguous_instrument", "empty_trade_history", "codal_no_candidate_notice", "http_error", "parse_error", "partial_success"}
USER_AGENT = "papermali-stage124-iran-feasibility-probe/2.0 (non-authoritative research; contact: repository maintainer)"

FLAT_COLUMNS = [
    "ticker_original", "ticker_normalized", "ticker_aliases", "company_name_dataset", "candidate_company_name", "candidate_company_name_source", "tsetmc_instrument_id_selected", "tsetmc_instrument_candidate_count", "tsetmc_instrument_candidates_json", "instrument_match_status", "ordinary_share_confirmed", "rights_excluded", "market_name_candidate", "candidate_first_trade_date_raw", "candidate_first_trade_date_raw_field", "candidate_first_trade_date_gregorian", "candidate_first_trade_date_jalali", "number_of_historical_trade_days", "tsetmc_search_endpoint", "tsetmc_history_endpoint", "tsetmc_search_http_status", "tsetmc_history_http_status", "tsetmc_search_raw_sha256", "tsetmc_history_raw_sha256", "codal_candidate_notice_count", "codal_candidate_notices_json", "codal_endpoint", "codal_http_status", "codal_raw_sha256", "extraction_status", "error_class", "error_message", "retrieved_at", "egress_country_code", "valid_iran_run", "verified", "notes"
]
MANIFEST_COLUMNS = ["ticker", "source", "request_type", "endpoint", "http_status", "retrieved_at", "duration_ms", "content_type", "response_size_bytes", "raw_file_path", "raw_response_sha256", "parse_status", "error_class", "error_message"]
CANDIDATE_HISTORY_COLUMNS = ["ticker", "insCode", "company_name_candidate", "market", "active_status", "candidate_first_trade_date", "number_of_trade_days", "raw_response_sha256", "review_status"]
CANDIDATE_HISTORY_TICKERS = {"بوعلی", "نوری"}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_symbol(s: str) -> str:
    s = unicodedata.normalize("NFC", str(s or ""))
    s = s.replace("ي", "ی").replace("ك", "ک")
    s = s.replace("\u200c", " ").replace("\u200f", "").replace("\u200e", "").replace("\u200b", "")
    return re.sub(r"\s+", " ", s).strip()


def aliases_for(ticker: str) -> list[str]:
    vals = [ticker, normalize_symbol(ticker)]
    if ticker == "جم پیلن":
        vals += ["جم‌پیلن", "جم پیلن"]
    if ticker == "پی‌پاد":
        vals += ["پی‌پاد", "پی پاد", "پیپاد"]
    out = []
    for v in vals:
        if v and v not in out:
            out.append(v)
    return out


def mask_ip(ip: str | None) -> str:
    if not ip:
        return ""
    if ":" in ip:
        parts = ip.split(":")
        return ":".join(parts[:2]) + ":***"
    parts = ip.split(".")
    return ".".join(parts[:2] + ["***", "***"]) if len(parts) == 4 else "***"


def to_gregorian(raw) -> tuple[str, str]:
    if raw in (None, ""):
        return "", ""
    s = str(int(raw)) if isinstance(raw, (int, float)) and not pd.isna(raw) else str(raw).strip()
    if not re.fullmatch(r"\d{8}", s):
        return "", ""
    try:
        g = dt.date(int(s[:4]), int(s[4:6]), int(s[6:8])).isoformat()
    except ValueError:
        return "", ""
    if jdatetime is None:
        return g, ""
    jd = jdatetime.date.fromgregorian(date=dt.date.fromisoformat(g))
    return g, f"{jd.year:04d}-{jd.month:02d}-{jd.day:02d}"


def session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=3, connect=3, read=3, backoff_factor=0.8, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json,text/plain,*/*"})
    return s


def save_raw(ticker: str, source: str, request_type: str, body: bytes, raw_hash: str) -> str:
    root = TSETMC_RAW if source == "tsetmc" else CODAL_RAW if source == "codal" else RAW_ROOT
    root.mkdir(parents=True, exist_ok=True)
    safe = normalize_symbol(ticker).replace(" ", "_") or "egress"
    p = root / f"{safe}__{request_type}__{raw_hash[:12]}.bin"
    p.write_bytes(body)
    return str(p.relative_to(PROJECT))


def fetch(s: requests.Session, manifest: list[dict], ticker: str, source: str, request_type: str, url: str, timeout: float, save_body: bool = True) -> tuple[dict | None, dict]:
    t0 = time.perf_counter()
    retrieved_at = now_iso()
    http_status = ""
    content_type = ""
    size = 0
    raw_path = ""
    raw_hash = ""
    parse_status = "not_attempted"
    error_class = ""
    error_message = ""
    data = None
    try:
        r = s.get(url, timeout=timeout)
        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        http_status = r.status_code
        content_type = r.headers.get("content-type", "")
        body = r.content or b""
        size = len(body)
        raw_hash = sha256_bytes(body)
        raw_path = save_raw(ticker, source, request_type, body, raw_hash) if body and save_body else ""
        if r.status_code != 200:
            parse_status = "not_attempted"
            error_class = "http_error"
            error_message = f"HTTP {r.status_code}"
        else:
            try:
                data = r.json()
                parse_status = "ok"
            except Exception as e:
                parse_status = "parse_error"
                error_class = e.__class__.__name__
                error_message = str(e)[:180]
    except requests.exceptions.RequestException as e:
        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        error_class = e.__class__.__name__
        error_message = str(e)[:180]
    rec = {"ticker": ticker, "source": source, "request_type": request_type, "endpoint": url, "http_status": http_status, "retrieved_at": retrieved_at, "duration_ms": elapsed, "content_type": content_type, "response_size_bytes": size, "raw_file_path": raw_path, "raw_response_sha256": raw_hash, "parse_status": parse_status, "error_class": error_class, "error_message": error_message}
    manifest.append(rec)
    return data, rec


def egress_check(s: requests.Session, manifest: list[dict], timeout: float) -> dict:
    url = "https://api.country.is/"
    data, rec = fetch(s, manifest, "_egress", "egress", "country_check", url, timeout, save_body=False)
    ip = data.get("ip") if isinstance(data, dict) else None
    country = data.get("country") if isinstance(data, dict) else ""
    return {"egress_country_code": country or "", "egress_check_source": url, "egress_checked_at": rec["retrieved_at"], "egress_ip_masked": mask_ip(ip), "egress_ip_sha256": sha256_bytes(str(ip or "").encode()), "valid_iran_run": False}


def load_template_names() -> dict[str, str]:
    df = pd.read_csv(TEMPLATE, dtype=str, keep_default_na=False)
    return dict(zip(df["ticker"], df["company_name"]))


def is_rights(sym: str) -> bool:
    return normalize_symbol(sym).endswith("ح") and len(normalize_symbol(sym)) > 1


def nonordinary_reason(sym: str, name: str) -> str:
    if is_rights(sym):
        return "rights_suffix_h"
    text = normalize_symbol(f"{sym} {name}")
    for bad in ["صندوق", "اوراق", "اختیار", "گواهی", "آتی", "سلف", "مرابحه", "اجاره", "مشارکت"]:
        if bad in text:
            return f"non_ordinary_{bad}"
    return ""


def extract_instruments(data) -> list[dict]:
    if not isinstance(data, dict):
        return []
    items = data.get("instrumentSearch") or data.get("InstrumentSearch") or []
    out = []
    for it in items if isinstance(items, list) else []:
        sym = str(it.get("lVal18AFC") or it.get("symbol") or "").strip()
        name = str(it.get("lVal30") or it.get("name") or "").strip()
        ins = str(it.get("insCode") or it.get("instrumentId") or "").strip()
        market = str(it.get("flowTitle") or it.get("marketTitle") or it.get("flow") or "").strip()
        out.append({"insCode": ins, "symbol": sym, "name": name, "market": market, "nonordinary_reason": nonordinary_reason(sym, name)})
    return out


def instrument_probe(s: requests.Session, manifest: list[dict], ticker: str, timeout: float) -> tuple[dict, dict]:
    norm = normalize_symbol(ticker)
    url = f"https://cdn.tsetmc.com/api/Instrument/GetInstrumentSearch/{quote(norm)}"
    data, rec = fetch(s, manifest, ticker, "tsetmc", "instrument_search", url, timeout)
    if rec["error_class"] == "http_error":
        return {"status": "http_error", "selected": "", "candidates": [], "excluded": [], "candidate_company_name": "", "market": "", "notes": rec["error_message"]}, rec
    if rec["error_class"]:
        return {"status": "network_unreachable", "selected": "", "candidates": [], "excluded": [], "candidate_company_name": "", "market": "", "notes": rec["error_message"]}, rec
    if rec["parse_status"] == "parse_error":
        return {"status": "parse_error", "selected": "", "candidates": [], "excluded": [], "candidate_company_name": "", "market": "", "notes": rec["error_message"]}, rec
    all_items = extract_instruments(data)
    exact = [x for x in all_items if normalize_symbol(x["symbol"]) == norm]
    excluded = [x for x in exact if x["nonordinary_reason"]]
    ordinary = [{k: v for k, v in x.items() if k != "nonordinary_reason"} for x in exact if not x["nonordinary_reason"]]
    seen = set(); candidates = []
    for x in ordinary:
        key = x.get("insCode") or json.dumps(x, ensure_ascii=False)
        if key not in seen:
            seen.add(key); candidates.append(x)
    if not candidates:
        return {"status": "no_instrument_match", "selected": "", "candidates": candidates, "excluded": excluded, "candidate_company_name": "", "market": "", "notes": "no exact ordinary-share instrument match"}, rec
    if len(candidates) > 1:
        return {"status": "ambiguous_instrument", "selected": "", "candidates": candidates, "excluded": excluded, "candidate_company_name": "", "market": "", "notes": "multiple ordinary exact symbol matches; no auto-selection"}, rec
    c = candidates[0]
    return {"status": "candidate_found", "selected": c["insCode"], "candidates": candidates, "excluded": excluded, "candidate_company_name": c.get("name", ""), "market": c.get("market", ""), "notes": "single exact ordinary-share match selected as candidate"}, rec


def history_probe(s: requests.Session, manifest: list[dict], ticker: str, ins: str, timeout: float) -> tuple[dict, dict | None]:
    if not ins:
        return {"status": "", "endpoint": "", "n": "", "raw": "", "raw_field": "", "gregorian": "", "jalali": "", "notes": "history skipped; no selected instrument"}, None
    url = f"https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceDailyList/{ins}/0"
    data, rec = fetch(s, manifest, ticker, "tsetmc", "daily_history", url, timeout)
    if rec["error_class"] == "http_error":
        return {"status": "http_error", "endpoint": url, "n": "", "raw": "", "raw_field": "dEven", "gregorian": "", "jalali": "", "notes": rec["error_message"]}, rec
    if rec["error_class"]:
        return {"status": "network_unreachable", "endpoint": url, "n": "", "raw": "", "raw_field": "dEven", "gregorian": "", "jalali": "", "notes": rec["error_message"]}, rec
    if rec["parse_status"] == "parse_error":
        return {"status": "parse_error", "endpoint": url, "n": "", "raw": "", "raw_field": "dEven", "gregorian": "", "jalali": "", "notes": rec["error_message"]}, rec
    days = data.get("closingPriceDaily") if isinstance(data, dict) else []
    raw_dates = sorted([x.get("dEven") for x in days if isinstance(x, dict) and x.get("dEven")])
    if not raw_dates:
        return {"status": "empty_trade_history", "endpoint": url, "n": len(days or []), "raw": "", "raw_field": "dEven", "gregorian": "", "jalali": "", "notes": "empty daily history"}, rec
    g, j = to_gregorian(raw_dates[0])
    status = "candidate_found" if g else "parse_error"
    return {"status": status, "endpoint": url, "n": len(days), "raw": str(raw_dates[0]), "raw_field": "dEven", "gregorian": g, "jalali": j, "notes": "oldest dEven in TSETMC daily history" if g else "unparseable dEven"}, rec


def codal_probe(s: requests.Session, manifest: list[dict], ticker: str, timeout: float) -> tuple[dict, dict]:
    norm = normalize_symbol(ticker)
    query = "|".join(aliases_for(ticker)) if ticker == "پی‌پاد" else norm
    url = "https://search.codal.ir/api/search/v2/q?" + f"Symbol={quote(query)}&PageNumber=1&Audited=true&AuditorRef=-1&Category=-1&Childs=true&CompanyState=-1&CompanyType=-1&Consolidatable=true&IsNotAudited=false&Length=-1&LetterType=-1&Mains=true&Publisher=false&TracingNo=-1"
    data, rec = fetch(s, manifest, ticker, "codal", "search", url, timeout)
    if rec["error_class"] == "http_error":
        return {"status": "http_error", "notices": [], "notes": rec["error_message"]}, rec
    if rec["error_class"]:
        return {"status": "network_unreachable", "notices": [], "notes": rec["error_message"]}, rec
    if rec["parse_status"] == "parse_error":
        return {"status": "parse_error", "notices": [], "notes": rec["error_message"]}, rec
    letters = data.get("Letters") if isinstance(data, dict) else []
    notices = []
    for l in letters if isinstance(letters, list) else []:
        title = str(l.get("Title") or "").strip()
        if any(k in title for k in CODAL_HINTS):
            rel = l.get("Url") or l.get("AttachmentUrl") or ""
            notices.append({"title": title, "date_jalali": str(l.get("SentDateTime") or l.get("PublishDateTime") or "").strip(), "url": ("https://www.codal.ir" + rel) if str(rel).startswith("/") else str(rel)})
    notices = sorted(notices, key=lambda x: x.get("date_jalali", ""))[:10]
    return {"status": "candidate_found" if notices else "codal_no_candidate_notice", "notices": notices, "notes": "" if notices else "no listing-keyword notice in first search page"}, rec


def candidate_history_row(s: requests.Session, manifest: list[dict], ticker: str, candidate: dict, timeout: float) -> dict:
    hist, rec = history_probe(s, manifest, ticker, candidate.get("insCode", ""), timeout)
    return {"ticker": ticker, "insCode": candidate.get("insCode", ""), "company_name_candidate": candidate.get("name", ""), "market": candidate.get("market", ""), "active_status": "candidate_ordinary", "candidate_first_trade_date": hist["gregorian"], "number_of_trade_days": hist["n"], "raw_response_sha256": rec["raw_response_sha256"] if rec else "", "review_status": "candidate_only_not_verified"}


def overall_status(inst: str, hist: str, codal: str) -> str:
    if inst in {"network_unreachable", "http_error", "parse_error", "no_instrument_match", "ambiguous_instrument"}:
        return inst
    if hist in {"candidate_found", "network_unreachable", "http_error", "parse_error", "empty_trade_history"}:
        if hist == "candidate_found" and codal not in {"candidate_found", "codal_no_candidate_notice"}:
            return "partial_success"
        return hist
    return "partial_success"


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT.parent, check=False, text=True, capture_output=True).stdout.strip()
    except Exception:
        return ""


def source_tree_dirty() -> bool:
    try:
        out = subprocess.run(["git", "status", "--porcelain", "--", *SOURCE_PROVENANCE_FILES], cwd=PROJECT.parent, check=False, text=True, capture_output=True).stdout.strip()
        return bool(out)
    except Exception:
        return True


def main() -> int:
    start = now_iso(); t0 = time.time()
    before_hash = sha256_file(TEMPLATE)
    source_commit_before_run = git_commit()
    dirty_before_run = source_tree_dirty()
    source_file_hash = sha256_file(SCRIPT)
    if dirty_before_run:
        raise SystemExit("source provenance files are dirty; aborting before network extraction")
    names = load_template_names()
    missing = [t for t in PILOT_TICKERS if t not in names]
    if missing:
        raise SystemExit(f"pilot tickers not in frozen template: {missing}")
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    timeout = float(os.environ.get("STAGE124_PROBE_TIMEOUT", "20"))
    s = session()
    eg = egress_check(s, manifest, timeout)
    rows = []
    candidate_history_rows = []
    source_ok = {"tsetmc": False, "codal": False, "internet": bool(eg["egress_country_code"])}
    for ticker in PILOT_TICKERS:
        if eg["egress_country_code"] != "IR":
            norm = normalize_symbol(ticker)
            inst = {"status": "network_unreachable", "selected": "", "candidates": [], "excluded": [], "candidate_company_name": "", "market": "", "notes": "egress_country_code is not IR; TSETMC/Codal probe skipped to avoid invalid network run"}
            hist = {"status": "", "endpoint": "", "n": "", "raw": "", "raw_field": "dEven", "gregorian": "", "jalali": "", "notes": "history skipped; invalid Iran egress"}
            cd = {"status": "network_unreachable", "notices": [], "notes": "egress_country_code is not IR; Codal probe skipped to avoid invalid network run"}
            inst_rec = {"endpoint": f"https://cdn.tsetmc.com/api/Instrument/GetInstrumentSearch/{quote(norm)}", "http_status": "", "raw_response_sha256": "", "error_class": "network_unreachable"}
            hist_rec = None
            cd_rec = {"endpoint": "https://search.codal.ir/api/search/v2/q?Symbol=" + quote(norm), "http_status": "", "raw_response_sha256": "", "error_class": "network_unreachable"}
            status = "network_unreachable"
        else:
            time.sleep(0.4)
            inst, inst_rec = instrument_probe(s, manifest, ticker, timeout)
            source_ok["tsetmc"] = source_ok["tsetmc"] or inst_rec.get("http_status") == 200
            hist, hist_rec = history_probe(s, manifest, ticker, inst["selected"], timeout)
            if ticker in CANDIDATE_HISTORY_TICKERS:
                for candidate in inst["candidates"]:
                    candidate_history_rows.append(candidate_history_row(s, manifest, ticker, candidate, timeout))
            if hist_rec:
                source_ok["tsetmc"] = source_ok["tsetmc"] or hist_rec.get("http_status") == 200
            time.sleep(0.4)
            cd, cd_rec = codal_probe(s, manifest, ticker, timeout)
            source_ok["codal"] = source_ok["codal"] or cd_rec.get("http_status") == 200
            status = overall_status(inst["status"], hist["status"], cd["status"])
        errs = [x for x in [inst.get("notes"), hist.get("notes"), cd.get("notes")] if x]
        rows.append({
            "ticker_original": ticker, "ticker_normalized": normalize_symbol(ticker), "ticker_aliases": json.dumps(aliases_for(ticker), ensure_ascii=False), "company_name_dataset": names.get(ticker, ""), "candidate_company_name": inst.get("candidate_company_name", ""), "candidate_company_name_source": "TSETMC instrument search" if inst.get("candidate_company_name") else "", "tsetmc_instrument_id_selected": inst["selected"], "tsetmc_instrument_candidate_count": len(inst["candidates"]), "tsetmc_instrument_candidates_json": json.dumps(inst["candidates"], ensure_ascii=False), "instrument_match_status": inst["status"], "ordinary_share_confirmed": str(bool(inst["selected"])).lower(), "rights_excluded": str(bool(inst["excluded"])).lower(), "market_name_candidate": inst.get("market", ""), "candidate_first_trade_date_raw": hist["raw"], "candidate_first_trade_date_raw_field": hist["raw_field"], "candidate_first_trade_date_gregorian": hist["gregorian"], "candidate_first_trade_date_jalali": hist["jalali"], "number_of_historical_trade_days": hist["n"], "tsetmc_search_endpoint": inst_rec["endpoint"], "tsetmc_history_endpoint": hist["endpoint"], "tsetmc_search_http_status": inst_rec["http_status"], "tsetmc_history_http_status": hist_rec["http_status"] if hist_rec else "", "tsetmc_search_raw_sha256": inst_rec["raw_response_sha256"], "tsetmc_history_raw_sha256": hist_rec["raw_response_sha256"] if hist_rec else "", "codal_candidate_notice_count": len(cd["notices"]), "codal_candidate_notices_json": json.dumps(cd["notices"], ensure_ascii=False), "codal_endpoint": cd_rec["endpoint"], "codal_http_status": cd_rec["http_status"], "codal_raw_sha256": cd_rec["raw_response_sha256"], "extraction_status": status, "error_class": ";".join([str(x.get("error_class", "")) for x in [inst_rec, hist_rec or {}, cd_rec] if x.get("error_class")]), "error_message": " | ".join(errs)[:500], "retrieved_at": now_iso(), "egress_country_code": eg["egress_country_code"], "valid_iran_run": "false", "verified": "false", "notes": "candidate data only; not verified; eligibility untouched"
        })
    valid_iran_run = bool(eg["egress_country_code"] == "IR" and (source_ok["tsetmc"] or source_ok["codal"]))
    eg["valid_iran_run"] = valid_iran_run
    for r in rows:
        r["valid_iran_run"] = str(valid_iran_run).lower()
    after_hash = sha256_file(TEMPLATE)
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FLAT_COLUMNS); w.writeheader(); w.writerows(rows)
    with OUT_MANIFEST.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS); w.writeheader(); w.writerows(manifest)
    with OUT_CANDIDATE_HISTORY.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CANDIDATE_HISTORY_COLUMNS); w.writeheader(); w.writerows(candidate_history_rows)
    counts = {k: sum(1 for r in rows if r["extraction_status"] == k) for k in STATUS_VALUES}
    report = {"stage_name": "stage124_iran_data_probe_batch01", "started_at": start, "finished_at": now_iso(), "python_version": sys.version, "platform": platform.platform(), "code_commit": source_commit_before_run, "script_sha256": source_file_hash, "source_file_sha256": source_file_hash, "source_commit_before_run": source_commit_before_run, "source_tree_dirty_before_run": dirty_before_run, "source_file_sha256_before_run": source_file_hash, "stage124_template_sha256_before": before_hash, "stage124_template_sha256_after": after_hash, "egress_country_code": eg["egress_country_code"], "egress_check_source": eg["egress_check_source"], "egress_checked_at": eg["egress_checked_at"], "egress_ip_masked": eg["egress_ip_masked"], "egress_ip_sha256": eg["egress_ip_sha256"], "valid_iran_run": valid_iran_run, "public_internet_access": source_ok["internet"], "tsetmc_accessible": source_ok["tsetmc"], "codal_accessible": source_ok["codal"], "input_ticker_count": len(PILOT_TICKERS), "candidate_found_count": counts["candidate_found"], "ambiguous_instrument_count": counts["ambiguous_instrument"], "network_unreachable_count": counts["network_unreachable"], "no_instrument_match_count": counts["no_instrument_match"], "empty_trade_history_count": counts["empty_trade_history"], "parse_error_count": counts["parse_error"], "candidate_date_count": sum(bool(r["candidate_first_trade_date_gregorian"]) for r in rows), "codal_notice_ticker_count": sum(int(r["codal_candidate_notice_count"]) > 0 for r in rows), "is_verified_file": False, "touches_eligibility": False, "frozen_files_modified": before_hash != after_hash, "status_counts": counts, "output_files": [str(OUT_CSV.relative_to(PROJECT)), str(OUT_REPORT.relative_to(PROJECT)), str(OUT_MANIFEST.relative_to(PROJECT)), str(OUT_CANDIDATE_HISTORY.relative_to(PROJECT)), str(RAW_ROOT.relative_to(PROJECT))], "runtime_seconds": round(time.time() - t0, 2)}
    OUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"valid_iran_run": valid_iran_run, "egress_country_code": eg["egress_country_code"], "status_counts": counts, "frozen_files_modified": before_hash != after_hash}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
