"""Stage124 — Listing Master Freeze.

PART 1 (this module): build a manual-review TEMPLATE of listing/first-trading dates for
the 130 unique tickers in the FROZEN Stage123 dataset. Dates and sources are NOT guessed
and NOT filled from any previous flag — only information that genuinely exists in the
dataset is written; every date/source cell is left blank for scientific manual review.

PART 2 (later, after listing_master_verified_stage124.csv is returned): merge by ticker,
store canonical dates as ISO, derive listed_by_fiscal_year_end / eligible_listing_financial
/ listing_eligibility_status, compare to the old proxy, and rebuild the panel — with NO
model / Optuna / SHAP / SMOTE / calibration / macro-market merge, and without touching
the Stage123 target, financials, statement scope, or company mapping.
"""
from __future__ import annotations
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import utils

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = ["src/stage124.py", "run_stage124.py", "tests/test_stage124.py"]
INTENDED_FREEZE_TAG = "stage124-template-frozen-v1"


class QCFail(Exception):
    """Raised when a Stage124 QC gate fails — halts the run with no success metadata."""


TEMPLATE_COLUMNS = [
    "ticker", "company_name", "ticker_aliases", "market",
    "earliest_fiscal_year_in_dataset", "latest_fiscal_year_in_dataset",
    "current_prelisting_proxy_row_count", "has_prelisting_proxy_rows",
    "current_first_eligible_year_proxy",
    "admission_date_jalali", "listing_date_jalali", "ipo_date_jalali",
    "first_public_trading_date_jalali", "first_public_trading_date_gregorian",
    "source_1_type", "source_1_title", "source_1_url",
    "source_2_type", "source_2_title", "source_2_url",
    "verification_status", "conflict_status", "notes",
]

# date / source / status cells that must stay BLANK for manual scientific review
MANUAL_BLANK = [
    "market", "admission_date_jalali", "listing_date_jalali", "ipo_date_jalali",
    "first_public_trading_date_jalali", "first_public_trading_date_gregorian",
    "source_1_type", "source_1_title", "source_1_url",
    "source_2_type", "source_2_title", "source_2_url", "conflict_status",
]


def stage_dir() -> Path:
    d = ROOT / "stage124"
    d.mkdir(parents=True, exist_ok=True)
    return d


def stage123_frozen_path() -> Path:
    return ROOT / "stage123" / "modeling_all_rows_stage123.csv"


def load_stage123_frozen() -> pd.DataFrame:
    p = stage123_frozen_path()
    if not p.exists():
        raise FileNotFoundError(
            f"frozen Stage123 dataset not found: {p}\n"
            f"Run `python run_stage122.py` then `python run_stage123.py` first "
            f"(the bulky panel is gitignored and regenerated on demand).")
    return pd.read_csv(p, dtype=str, encoding="utf-8-sig", keep_default_na=False)


def _modal_name(names: pd.Series) -> str:
    vals = [n for n in names if str(n).strip()]
    return pd.Series(vals).value_counts().index[0] if vals else ""


# --------------------------------------------------------------------------
# Pure template builder (deterministic, order-independent) — testable in isolation
# --------------------------------------------------------------------------
def build_template_df(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["_year"] = pd.to_numeric(work["fiscal_year"], errors="coerce").astype("Int64")
    rows = []
    for tk, g in work.groupby("ticker", sort=True):  # sort -> order-independent
        names = g["company_name"]
        distinct = sorted({str(n).strip() for n in names if str(n).strip()})
        prelist = int((g["eligible_listing"] == "0").sum())
        elig_years = pd.to_numeric(
            g.loc[g["eligible_listing"] == "1", "fiscal_year"], errors="coerce").dropna()
        first_elig = int(elig_years.min()) if len(elig_years) else ""
        note = ""
        if len(distinct) > 1:
            note = "multiple company_name spellings in dataset: " + " | ".join(distinct)
        elif not distinct:
            note = "company_name missing in dataset"
        rec = {c: "" for c in TEMPLATE_COLUMNS}
        rec.update({
            "ticker": tk,
            "company_name": _modal_name(names),
            "ticker_aliases": "",  # no alternative-symbol data in the dataset
            "earliest_fiscal_year_in_dataset": int(g["_year"].min()),
            "latest_fiscal_year_in_dataset": int(g["_year"].max()),
            "current_prelisting_proxy_row_count": prelist,
            "has_prelisting_proxy_rows": 1 if prelist > 0 else 0,
            "current_first_eligible_year_proxy": first_elig,
            "verification_status": "pending",  # workflow state, not a data guess
            "notes": note,
        })
        rows.append(rec)
    template = pd.DataFrame(rows, columns=TEMPLATE_COLUMNS)
    for c in MANUAL_BLANK:           # guarantee manual cells are blank
        template[c] = ""
    return template


def compute_qc(template: pd.DataFrame, ref_tickers: set, src_hash: str,
               frozen_name: str, n_input_rows: int) -> dict:
    tmpl_tickers = set(template["ticker"])
    incomplete = sorted(template.loc[template["company_name"].str.strip() == "", "ticker"])
    dup = int(template["ticker"].duplicated().sum())
    flag_consistent = bool(
        (template["has_prelisting_proxy_rows"].astype(int) ==
         (template["current_prelisting_proxy_row_count"].astype(int) > 0).astype(int)).all())
    assertions = {
        "exactly_130_unique": int(template["ticker"].nunique()) == 130,
        "zero_duplicate_ticker": dup == 0,
        "coverage_exact": ref_tickers == tmpl_tickers,
        "no_new_or_removed": (not (tmpl_tickers - ref_tickers))
        and (not (ref_tickers - tmpl_tickers)),
        "manual_cells_blank": bool((template[MANUAL_BLANK] == "").all().all()),
        "prelisting_flag_count_consistent": flag_consistent,
        "stage123_input_hash_recorded": bool(src_hash),
    }
    qc = {
        "stage": "stage124_part1_template",
        "n_unique_tickers": int(template["ticker"].nunique()),
        "n_rows_template": int(len(template)),
        "duplicate_ticker_count": dup,
        "covers_all_stage123_tickers": ref_tickers == tmpl_tickers,
        "tickers_added_vs_stage123": sorted(tmpl_tickers - ref_tickers),
        "tickers_missing_vs_stage123": sorted(ref_tickers - tmpl_tickers),
        "n_tickers_incomplete_name": len(incomplete),
        "tickers_incomplete_name": incomplete,
        "n_tickers_multiple_name_spellings": int(
            template["notes"].str.startswith("multiple").sum()),
        "stage123_input_file": frozen_name,
        "stage123_input_sha256": src_hash,
        "n_input_rows": int(n_input_rows),
        "n_input_unique_tickers": len(ref_tickers),
        "assertions": assertions,
        "notes": [
            "Date and source columns are intentionally blank for scientific manual "
            "verification; they were NOT guessed or copied from any previous flag.",
            "current_prelisting_proxy_row_count / current_first_eligible_year_proxy are "
            "the EXISTING Stage123 proxy values, shown only for manual comparison.",
        ],
    }
    qc["overall_pass"] = all(assertions.values())
    return qc


def _source_info() -> dict:
    hashes = {f: (utils.sha256_file(ROOT / f) if (ROOT / f).exists() else None)
              for f in SOURCE_FILES}
    commit = dirty = None
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT),
                                capture_output=True, text=True).stdout.strip() or None
        st = subprocess.run(["git", "status", "--porcelain", "--", *SOURCE_FILES],
                            cwd=str(ROOT), capture_output=True, text=True).stdout.strip()
        dirty = bool(st)
    except Exception:
        pass
    return {"source_code_commit": commit, "source_tree_dirty_before_run": dirty,
            "source_file_sha256": hashes, "intended_freeze_tag": INTENDED_FREEZE_TAG}


# --------------------------------------------------------------------------
# Orchestrator (IO + fail-fast). `df`/`out_dir` injectable for unit tests.
# --------------------------------------------------------------------------
def build_template(cfg, *, out_dir=None, df=None) -> dict:
    t0 = time.time()
    src_info = _source_info()                       # captured BEFORE any output
    out = Path(out_dir) if out_dir else stage_dir()
    out.mkdir(parents=True, exist_ok=True)
    frozen_path = stage123_frozen_path()
    ref = load_stage123_frozen()                    # independent coverage reference + hash
    src_hash = utils.sha256_file(frozen_path)
    ref_tickers = set(ref["ticker"].unique())

    work = ref if df is None else df                # template source (default = frozen)
    template = build_template_df(work)
    template.to_csv(out / "listing_master_template_stage124.csv", index=False,
                    encoding="utf-8-sig")

    qc = compute_qc(template, ref_tickers, src_hash, frozen_path.name, len(work))
    utils.save_json(qc, out / "stage124_template_report.json")

    if not qc["overall_pass"]:                       # fail-fast: no success metadata
        failed = [k for k, v in qc["assertions"].items() if not v]
        raise QCFail(f"Stage124 template QC failed (report saved): {failed}")

    meta = _metadata(cfg, out, src_info, src_hash, frozen_path, ref, t0)
    utils.save_json(meta, out / "metadata_and_hashes_stage124_part1.json")
    print(f"[stage124] template built: {qc['n_unique_tickers']} tickers, "
          f"dup={qc['duplicate_ticker_count']}, "
          f"incomplete_name={qc['n_tickers_incomplete_name']}, "
          f"overall_pass={qc['overall_pass']}")
    return {"template": template, "qc": qc, "out": out, "meta": meta}


def _metadata(cfg, out, src_info, src_hash, frozen_path, ref, t0):
    return {
        "stage": "stage124_part1_template",
        "stage123_input_file": frozen_path.name,
        "stage123_input_sha256": src_hash,
        "n_input_rows": int(len(ref)),
        "n_input_unique_tickers": int(ref["ticker"].nunique()),
        "template_file": "listing_master_template_stage124.csv",
        "template_sha256": utils.sha256_file(out / "listing_master_template_stage124.csv"),
        "source_code_commit": src_info["source_code_commit"],
        "source_tree_dirty_before_run": src_info["source_tree_dirty_before_run"],
        "source_file_sha256": src_info["source_file_sha256"],
        "intended_freeze_tag": src_info["intended_freeze_tag"],
        "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
        "python": sys.version, "platform": platform.platform(),
        "seed": cfg.get("seed", 42), "runtime_seconds": round(time.time() - t0, 2),
    }
