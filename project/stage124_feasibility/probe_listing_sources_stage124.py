#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage124 — FEASIBILITY PROBE v2 (read-only, non-authoritative).

PURPOSE
    Technical check ONLY: can we automatically pull the *initial* listing info for the
    Stage124 tickers from (a) TSETMC trade data and (b) Codal search? This script does
    NOT build a verified file, does NOT touch eligibility, and does NOT overwrite any
    frozen Stage123 / Stage124 artifact. It writes a fresh probe report only.

HARD RULES (per task brief, v2)
  1. The earliest trade date is stored strictly as `candidate_first_trade_date`
     (+ `verified=false`); never treated as verified.
  2. Rights (حق‌تقدم), funds (صندوق) and any non-ordinary instrument are excluded.
  3. If a ticker resolves to MULTIPLE insCodes, ALL candidates are recorded and status is
     `ambiguous_instrument`; NO automatic pick is made (trade history is not fetched).
  4. Original symbol form, normalized form and aliases are all preserved.
  5. Every call records endpoint, retrieved_at, HTTP status, error, raw SHA-256 (and the
     raw body itself when available, under raw_responses_stage124_<label>/).
  6. Network errors are reported as `network_unreachable`, kept SEPARATE from
     `no_instrument_match`.
  7. Codal search is broad: up to 10 candidate notices whose title contains any of
     {پذیرش، درج، عرضه اولیه، آغاز معاملات، گشایش نماد، امیدنامه، عرضه سهام}.
  8. No verified file is produced and eligibility is never changed.

EXTRACTION STATUS VOCABULARY
    candidate_found | network_unreachable | no_instrument_match | ambiguous_instrument |
    empty_trade_history | codal_no_candidate_notice | parse_error

EGRESS NOTE
    TSETMC/Codal geo-block non-Iranian IPs. The script self-certifies the exit country via
    an egress check and writes `valid_iran_run` into the report. Running from a non-Iran
    egress yields network_unreachable for every ticker (the intended, honest behaviour).

USAGE
    python probe_listing_sources_stage124.py --label iran --timeout 20
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import hashlib
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import requests

try:
    import jdatetime
except Exception:  # pragma: no cover
    jdatetime = None

HERE = Path(__file__).resolve().parent
SCHEMA_VERSION = "stage124_feasibility_probe_v2"

PILOT = [
    {"ticker": "اردستان", "dataset_name": "شرکت سیمان اردستان"},
    {"ticker": "اروند", "dataset_name": "شرکت پتروشیمی اروند"},
    {"ticker": "سآبیک", "dataset_name": "سیمان آبیک"},
    {"ticker": "وکغدیر", "dataset_name": "سرمایه گذاری غدیر"},
    {"ticker": "کویر", "dataset_name": "شرکت تولیدی فولاد سپید فراب کویر"},
    {"ticker": "بوعلی", "dataset_name": "شرکت پتروشیمی بوعلی سینا"},
    {"ticker": "نوری", "dataset_name": "شرکت پتروشیمی نوری"},
    {"ticker": "سپید", "dataset_name": "شرکت سپید ماکیان"},
    {"ticker": "کیمیاتک", "dataset_name": "شرکت آریان کیمیاتک"},
    {"ticker": "پی‌پاد", "dataset_name": "پرداخت الکترونیک پاسارگاد"},
    {"ticker": "پرداخت", "dataset_name": "به پرداخت ملت"},
    {"ticker": "پارس", "dataset_name": "شرکت پتروشیمی پارس"},
    {"ticker": "کاوه", "dataset_name": "فولاد کاوه جنوب کیش"},
    {"ticker": "جم‌پیلن", "dataset_name": "شرکت پلی پروپیلن جم", "dataset_ticker": "جم پیلن"},
    {"ticker": "اپال", "dataset_name": None},
]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

CODAL_HINTS = ["پذیرش", "درج", "عرضه اولیه", "آغاز معاملات", "گشایش نماد",
               "امیدنامه", "عرضه سهام"]
MAX_CODAL = 10

# instruments that are NOT ordinary shares (excluded per rule 2)
NON_ORDINARY_NAME_HINTS = ["صندوق", "اوراق", "تسهیلات", "آتی", "اختیار", "سلف",
                           "گواهی", "مشارکت", "صکوک", "اجاره", "مرابحه"]

# --------------------------------------------------------------------------
# normalization & date helpers
# --------------------------------------------------------------------------
def normalize_symbol(s: str) -> str:
    """Drop ZWNJ/ZWSP/marks, map Arabic ي/ك/ة -> Persian ی/ک/ه, collapse spaces."""
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s)
    s = s.replace("‌", "").replace("‏", "").replace("‎", "")
    s = (s.replace("ي", "ی").replace("ك", "ک").replace("ة", "ه")
         .replace("أ", "ا").replace("إ", "ا").replace("ۀ", "ه"))
    return re.sub(r"\s+", " ", s).strip()


def build_aliases(*forms: str) -> list:
    out = []
    for f in forms:
        for cand in (f, normalize_symbol(f)):
            if cand and cand not in out:
                out.append(cand)
    return out


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()


def _yyyymmdd_iso(n):
    try:
        s = str(int(n))
        if len(s) != 8:
            return None
        return _dt.date(int(s[:4]), int(s[4:6]), int(s[6:8])).isoformat()
    except Exception:
        return None


def _greg_to_jalali(iso):
    if not iso or jdatetime is None:
        return None
    try:
        y, m, d = (int(x) for x in iso.split("-"))
        j = jdatetime.date.fromgregorian(date=_dt.date(y, m, d))
        return f"{j.year:04d}-{j.month:02d}-{j.day:02d}"
    except Exception:
        return None


def _is_rights(sym: str) -> bool:
    s = (sym or "").strip()
    return len(s) > 1 and s.endswith("ح")


def _is_non_ordinary(sym: str, name: str) -> tuple[bool, str]:
    if _is_rights(sym):
        return True, "rights(حق‌تقدم)"
    nm = name or ""
    for h in NON_ORDINARY_NAME_HINTS:
        if h in nm:
            return True, f"non_ordinary({h})"
    return False, ""


# --------------------------------------------------------------------------
# HTTP with full provenance + optional raw-body save
# --------------------------------------------------------------------------
class Fetch:
    def __init__(self, session, timeout, raw_dir: Path, manifest: list):
        self.s = session
        self.timeout = timeout
        self.raw_dir = raw_dir
        self.manifest = manifest

    def get(self, url, *, ticker, source, want_json=True, save_subdir=None):
        rec = {"endpoint": url, "retrieved_at": _now(), "http_status": None,
               "ok": False, "network_error": None, "parse_error": None,
               "raw_sha256": None, "raw_bytes": 0, "saved_raw_path": "", "json": None}
        body = None
        try:
            r = self.s.get(url, timeout=self.timeout,
                           headers={"User-Agent": UA, "Accept": "*/*"})
            rec["http_status"] = r.status_code
            body = r.text or ""
            rec["raw_sha256"] = _sha256(body)
            rec["raw_bytes"] = len(body.encode("utf-8", "replace"))
            if save_subdir and body:
                d = self.raw_dir / save_subdir
                d.mkdir(parents=True, exist_ok=True)
                safe = normalize_symbol(ticker).replace(" ", "_") or "sym"
                p = d / f"{safe}__{source}.txt"
                p.write_text(body, encoding="utf-8")
                rec["saved_raw_path"] = str(p.relative_to(HERE))
            if r.status_code != 200:
                rec["network_error"] = f"http_status={r.status_code}"
            elif want_json:
                try:
                    rec["json"] = r.json()
                    rec["ok"] = True
                except Exception as e:
                    rec["parse_error"] = f"json_decode_failed: {e.__class__.__name__}"
            else:
                rec["ok"] = True
        except requests.exceptions.RequestException as e:
            rec["network_error"] = f"{e.__class__.__name__}: {str(e)[:160]}"

        self.manifest.append({
            "ticker": ticker, "source": source, "endpoint": url,
            "retrieved_at": rec["retrieved_at"], "http_status": rec["http_status"],
            "raw_sha256": rec["raw_sha256"], "raw_bytes": rec["raw_bytes"],
            "saved_raw_path": rec["saved_raw_path"],
            "error_message": rec["network_error"] or rec["parse_error"] or "",
        })
        return rec


# --------------------------------------------------------------------------
# egress self-certification
# --------------------------------------------------------------------------
def egress_check(fetch: Fetch) -> dict:
    rec = fetch.get("https://api.country.is/", ticker="_egress", source="egress")
    country = ip = None
    if rec["ok"] and isinstance(rec["json"], dict):
        country = rec["json"].get("country")
        ip = rec["json"].get("ip")
    return {"exit_ip": ip, "exit_country": country,
            "valid_iran_run": (country == "IR"),
            "provenance": {k: rec[k] for k in
                           ("endpoint", "retrieved_at", "http_status",
                            "network_error", "raw_sha256")}}


# --------------------------------------------------------------------------
# TSETMC instrument search
# --------------------------------------------------------------------------
def tsetmc_search(fetch: Fetch, query: str, ticker: str) -> dict:
    url = ("https://cdn.tsetmc.com/api/Instrument/GetInstrumentSearch/"
           + requests.utils.quote(query))
    rec = fetch.get(url, ticker=ticker, source="tsetmc_search",
                    save_subdir="tsetmc")
    out = {"provenance": rec, "status": None, "instrument_candidates": [],
           "excluded": [], "matched_name": None, "market_name": None, "note": None}
    if rec["network_error"]:
        out["status"] = "network_unreachable"
        out["note"] = rec["network_error"]
        return out
    if rec["parse_error"]:
        out["status"] = "parse_error"
        out["note"] = rec["parse_error"]
        return out

    items = (rec["json"] or {}).get("instrumentSearch") or []
    nq = normalize_symbol(query)
    ordinary = []
    for it in items:
        sym = (it.get("lVal18AFC") or "").strip()
        name = (it.get("lVal30") or "").strip()
        bad, why = _is_non_ordinary(sym, name)
        if bad:
            out["excluded"].append({"symbol": sym, "name": name, "reason": why})
            continue
        ordinary.append(it)

    exact = [it for it in ordinary
             if normalize_symbol(it.get("lVal18AFC") or "") == nq]
    cands = []
    for it in exact:
        cands.append({"insCode": (it.get("insCode") or "").strip(),
                      "symbol": (it.get("lVal18AFC") or "").strip(),
                      "name": (it.get("lVal30") or "").strip(),
                      "market": (it.get("flowTitle") or "").strip()})
    # dedup by insCode
    seen, uniq = set(), []
    for c in cands:
        if c["insCode"] and c["insCode"] not in seen:
            seen.add(c["insCode"])
            uniq.append(c)
    out["instrument_candidates"] = uniq

    if not uniq:
        out["status"] = "no_instrument_match"
        out["note"] = (f"no exact ordinary match; {len(out['excluded'])} excluded, "
                       f"{len(ordinary)} non-exact ordinary results")
    elif len(uniq) > 1:
        out["status"] = "ambiguous_instrument"   # rule 3: no auto-pick
        out["note"] = f"{len(uniq)} insCodes for symbol"
    else:
        out["status"] = "resolved"
        out["matched_name"] = uniq[0]["name"]
        out["market_name"] = uniq[0]["market"]
    return out


# --------------------------------------------------------------------------
# TSETMC daily closing-price history -> candidate_first_trade_date
# --------------------------------------------------------------------------
def tsetmc_trade_history(fetch: Fetch, ins_code: str, ticker: str) -> dict:
    url = ("https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceDailyList/"
           f"{ins_code}/0")
    rec = fetch.get(url, ticker=ticker, source="tsetmc_trade_history",
                    save_subdir="tsetmc")
    out = {"provenance": rec, "status": None, "n_historical_trade_days": None,
           "candidate_first_trade_date": {"jalali": None, "gregorian": None,
                                          "verified": False},
           "latest_trade_date_gregorian": None, "note": None}
    if rec["network_error"]:
        out["status"] = "network_unreachable"
        out["note"] = rec["network_error"]
        return out
    if rec["parse_error"]:
        out["status"] = "parse_error"
        out["note"] = rec["parse_error"]
        return out
    days = (rec["json"] or {}).get("closingPriceDaily") or []
    devens = sorted(d for d in (x.get("dEven") for x in days) if d)
    out["n_historical_trade_days"] = len(days)
    if not devens:
        out["status"] = "empty_trade_history"
        out["note"] = "no daily records"
        return out
    g = _yyyymmdd_iso(devens[0])
    out["candidate_first_trade_date"] = {"jalali": _greg_to_jalali(g),
                                         "gregorian": g, "verified": False}
    out["latest_trade_date_gregorian"] = _yyyymmdd_iso(devens[-1])
    out["status"] = "candidate_found"
    return out


# --------------------------------------------------------------------------
# Codal broad search -> up to 10 candidate notices
# --------------------------------------------------------------------------
def codal_candidates(fetch: Fetch, symbol: str, ticker: str) -> dict:
    url = ("https://search.codal.ir/api/search/v2/q?"
           f"Symbol={requests.utils.quote(symbol)}&PageNumber=1&Audited=true"
           "&AuditorRef=-1&Category=-1&Childs=true&CompanyState=-1&CompanyType=-1"
           "&Consolidatable=true&IsNotAudited=false&Length=-1&LetterType=-1"
           "&Mains=true&Publisher=false&TracingNo=-1")
    rec = fetch.get(url, ticker=ticker, source="codal", save_subdir="codal")
    out = {"provenance": rec, "status": None, "n_letters_total": None,
           "notices": [], "note": None}
    if rec["network_error"]:
        out["status"] = "network_unreachable"
        out["note"] = rec["network_error"]
        return out
    if rec["parse_error"]:
        out["status"] = "parse_error"
        out["note"] = rec["parse_error"]
        return out
    letters = (rec["json"] or {}).get("Letters") or []
    out["n_letters_total"] = len(letters)

    def _date(l):
        return l.get("SentDateTime") or l.get("PublishDateTime") or ""

    hinted = []
    for l in letters:
        title = l.get("Title") or ""
        if any(h in title for h in CODAL_HINTS):
            rel = l.get("Url") or l.get("AttachmentUrl") or ""
            url_full = ("https://www.codal.ir" + rel) if rel.startswith("/") else (rel or None)
            hinted.append({"title": title.strip(), "date_jalali": _date(l).strip(),
                           "url": url_full})
    hinted = sorted(hinted, key=lambda x: x["date_jalali"])[:MAX_CODAL]
    out["notices"] = hinted
    out["status"] = "candidate_found" if hinted else "codal_no_candidate_notice"
    if not hinted:
        out["note"] = f"{len(letters)} letters, none matched listing keywords"
    return out


# --------------------------------------------------------------------------
# per-ticker orchestration
# --------------------------------------------------------------------------
FLAT_COLUMNS = [
    "requested_ticker", "normalized_ticker", "dataset_ticker", "aliases",
    "company_name", "tsetmc_instrument_id", "n_instrument_candidates",
    "instrument_id_candidates", "market_name",
    "candidate_first_trade_date_jalali", "candidate_first_trade_date_gregorian",
    "candidate_first_trade_date_verified", "number_of_historical_trade_days",
    "trade_history_source_url_or_endpoint", "codal_candidate_notice_count",
    "codal_candidate_notice_title", "codal_candidate_notice_date",
    "codal_candidate_notice_url", "instrument_status", "trade_history_status",
    "codal_status", "extraction_status", "error_message", "retrieved_at",
    "raw_response_sha256",
]


def probe_one(fetch: Fetch, spec: dict) -> tuple[dict, dict]:
    requested = spec["ticker"]
    dataset_tk = spec.get("dataset_ticker", requested)
    search_sym = normalize_symbol(dataset_tk)
    aliases = build_aliases(requested, dataset_tk)

    s = tsetmc_search(fetch, search_sym, requested)

    # trade history only when a SINGLE instrument resolved (rule 3: no auto-pick)
    if s["status"] == "resolved":
        ins = s["instrument_candidates"][0]["insCode"]
        th = tsetmc_trade_history(fetch, ins, requested)
    else:
        ins = ""
        th = {"provenance": None, "status": "skipped",
              "n_historical_trade_days": None,
              "candidate_first_trade_date": {"jalali": None, "gregorian": None,
                                            "verified": False},
              "note": f"skipped: instrument_status={s['status']}"}

    cd = codal_candidates(fetch, search_sym, requested)

    # overall extraction_status (instrument/trade path drives it)
    if s["status"] == "network_unreachable":
        overall = "network_unreachable"
    elif s["status"] == "parse_error":
        overall = "parse_error"
    elif s["status"] == "no_instrument_match":
        overall = "no_instrument_match"
    elif s["status"] == "ambiguous_instrument":
        overall = "ambiguous_instrument"
    elif th["status"] == "network_unreachable":
        overall = "network_unreachable"
    elif th["status"] == "parse_error":
        overall = "parse_error"
    elif th["status"] == "empty_trade_history":
        overall = "empty_trade_history"
    elif th["status"] == "candidate_found":
        overall = "candidate_found"
    else:
        overall = th["status"]

    errors = []
    for tag, sub in (("search", s), ("trade_history", th), ("codal", cd)):
        if sub.get("note") and sub.get("status") not in ("resolved", "candidate_found"):
            errors.append(f"{tag}:{sub['note']}")

    hashes = {}
    for tag, sub in (("tsetmc_search", s), ("tsetmc_trade_history", th), ("codal", cd)):
        prov = sub.get("provenance")
        hashes[tag] = prov.get("raw_sha256") if prov else None

    cand = th["candidate_first_trade_date"]
    th_prov = th.get("provenance")
    notices = cd.get("notices") or []

    flat = {
        "requested_ticker": requested,
        "normalized_ticker": search_sym,
        "dataset_ticker": dataset_tk,
        "aliases": " | ".join(aliases),
        "company_name": s.get("matched_name") or (spec.get("dataset_name") or ""),
        "tsetmc_instrument_id": ins or "",
        "n_instrument_candidates": len(s.get("instrument_candidates") or []),
        "instrument_id_candidates":
            " | ".join(c["insCode"] for c in (s.get("instrument_candidates") or [])),
        "market_name": s.get("market_name") or "",
        "candidate_first_trade_date_jalali": cand["jalali"] or "",
        "candidate_first_trade_date_gregorian": cand["gregorian"] or "",
        "candidate_first_trade_date_verified": cand["verified"],
        "number_of_historical_trade_days":
            "" if th.get("n_historical_trade_days") is None
            else th["n_historical_trade_days"],
        "trade_history_source_url_or_endpoint":
            (th_prov or {}).get("endpoint", "") if th_prov else "",
        "codal_candidate_notice_count": len(notices),
        "codal_candidate_notice_title": notices[0]["title"] if notices else "",
        "codal_candidate_notice_date": notices[0]["date_jalali"] if notices else "",
        "codal_candidate_notice_url": notices[0]["url"] if notices else "",
        "instrument_status": s["status"],
        "trade_history_status": th["status"],
        "codal_status": cd["status"],
        "extraction_status": overall,
        "error_message": " ; ".join(errors),
        "retrieved_at": _now(),
        "raw_response_sha256": json.dumps(hashes, ensure_ascii=False),
    }

    detail = {
        "requested_ticker": requested,
        "normalized_ticker": search_sym,
        "dataset_ticker": dataset_tk,
        "aliases": aliases,
        "dataset_company_name": spec.get("dataset_name"),
        "candidate_first_trade_date": cand,            # verified always false
        "instrument_excluded_non_ordinary": s.get("excluded"),
        "instrument_candidates": s.get("instrument_candidates"),
        "tsetmc_search": {k: v for k, v in s.items() if k != "provenance"},
        "tsetmc_search_provenance": s.get("provenance"),
        "tsetmc_trade_history": {k: v for k, v in th.items() if k != "provenance"},
        "tsetmc_trade_history_provenance": th_prov,
        "codal": {k: v for k, v in cd.items() if k != "provenance"},
        "codal_provenance": cd.get("provenance"),
        "extraction_status": overall,
    }
    return flat, detail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="iran",
                    help="output suffix, e.g. 'iran' -> *_stage124_iran.*")
    ap.add_argument("--timeout", type=float, default=20.0)
    args = ap.parse_args()

    raw_dir = HERE / f"raw_responses_stage124_{args.label}"
    manifest = []
    sess = requests.Session()
    fetch = Fetch(sess, args.timeout, raw_dir, manifest)
    t0 = time.time()

    eg = egress_check(fetch)
    print(f"[egress] ip={eg['exit_ip']} country={eg['exit_country']} "
          f"valid_iran_run={eg['valid_iran_run']}", file=sys.stderr)

    flats, details = [], []
    for spec in PILOT:
        flat, detail = probe_one(fetch, spec)
        flats.append(flat)
        details.append(detail)
        print(f"[{flat['extraction_status']:>20}] {flat['requested_ticker']:<9} "
              f"ins={flat['tsetmc_instrument_id'] or '-'} "
              f"first={flat['candidate_first_trade_date_gregorian'] or '-'} "
              f"codal={flat['codal_candidate_notice_count']}", file=sys.stderr)

    counts = {}
    for f in flats:
        counts[f["extraction_status"]] = counts.get(f["extraction_status"], 0) + 1

    report = {
        "schema_version": SCHEMA_VERSION,
        "purpose": "API-feasibility & scientific control ONLY; non-authoritative.",
        "is_verified_file": False,
        "touches_eligibility": False,
        "egress": eg,
        "valid_iran_run": eg["valid_iran_run"],
        "generated_at": _now(),
        "timeout_seconds": args.timeout,
        "n_tickers": len(flats),
        "status_counts": counts,
        "codal_keywords": CODAL_HINTS,
        "max_codal_notices": MAX_CODAL,
        "rules_enforced": [
            "earliest trade date stored only as candidate_first_trade_date (verified=false)",
            "rights/funds/non-ordinary excluded",
            "multiple insCodes -> ambiguous_instrument, no auto-pick",
            "original+normalized+aliases preserved",
            "endpoint/retrieved_at/http_status/error/raw_sha256 (+raw body) preserved",
            "network_unreachable kept separate from no_instrument_match",
            "codal broad, <=10 notices for listing keywords",
            "no verified file, eligibility untouched",
        ],
        "records": details,
        "runtime_seconds": round(time.time() - t0, 2),
    }
    if not eg["valid_iran_run"]:
        report["warning"] = ("egress is NOT Iran (exit_country="
                             f"{eg['exit_country']}); results are placeholder — "
                             "rerun from an Iranian network for real data.")

    (HERE / f"feasibility_probe_report_stage124_{args.label}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    with (HERE / f"feasibility_probe_flat_stage124_{args.label}.csv").open(
            "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=FLAT_COLUMNS)
        w.writeheader()
        w.writerows(flats)

    man_cols = ["ticker", "source", "endpoint", "retrieved_at", "http_status",
                "raw_sha256", "raw_bytes", "saved_raw_path", "error_message"]
    with (HERE / f"raw_responses_manifest_stage124_{args.label}.csv").open(
            "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=man_cols)
        w.writeheader()
        w.writerows(manifest)

    print(f"\n=== Stage124 feasibility probe ({args.label}) ===", file=sys.stderr)
    print("valid_iran_run:", eg["valid_iran_run"], file=sys.stderr)
    print("status_counts:", counts, file=sys.stderr)
    print("manifest rows:", len(manifest), file=sys.stderr)


if __name__ == "__main__":
    main()
