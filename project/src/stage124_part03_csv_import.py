from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Iterable
from urllib.parse import urlsplit

import pandas as pd

from .stage124_batch02_part03 import PART03_TICKERS
from .stage124_batch02_part03 import is_valid_exact_jalali_date
from .stage124_batch02_v2 import (
    OUT,
    PARTIAL_MASTER,
    ROOT,
    jalali_str_to_gregorian_date,
    normalize_jalali,
    normalize_ticker,
    read_csv,
    sha,
)

PART03_DIR = OUT / "batch02_parts"
DEFAULT_INPUT = PART03_DIR / "part03_trusted_listing_dates.csv"
DEFAULT_REPORT = PART03_DIR / "part03_trusted_listing_dates_import_report.json"

VERIFICATION_STATUS = "verified_tse_csv_imported"
CONFLICT_STATUS = "resolved_tse_csv_imported"
DEFAULT_SOURCE_TYPE = "official_tse_csv_import"
DEFAULT_SOURCE_TITLE = "Trusted Tehran Stock Exchange CSV"
DEFAULT_FIRST_TRADE_SOURCE_TITLE = "Trusted Tehran Stock Exchange CSV (first trade dates)"
MASTER_NOTE = (
    "Canonical Stage124 public-entry date imported from a trusted Tehran Stock "
    "Exchange CSV supplied by the project owner."
)
PART03_MASTER_NOTE = (
    f"{MASTER_NOTE} Dashboard/snapshot entry is bypassed for this Part03 ticker set."
)

REQUIRED_CANONICAL_COLUMNS = [
    "ticker",
    "public_entry_date_jalali",
]
OPTIONAL_CANONICAL_COLUMNS = [
    "company_name",
    "public_entry_date_gregorian",
    "source_type",
    "source_title",
    "source_url",
    "notes",
    "import_status",
]
CANONICAL_COLUMNS = REQUIRED_CANONICAL_COLUMNS + OPTIONAL_CANONICAL_COLUMNS

COLUMN_ALIASES = {
    "ticker": ("ticker", "symbol", "ticker_symbol", "نماد"),
    "company_name": (
        "company_name",
        "full_company_name",
        "company_full_name",
        "company",
        "name",
        "نام شرکت",
    ),
    "public_entry_date_jalali": (
        "public_entry_date_jalali",
        "listing_date_jalali",
        "entry_date_jalali",
        "ipo_date_jalali",
        "first_trade_date_jalali",
        "first_public_trading_date_jalali",
        "date_jalali",
        "listing_date",
        "تاریخ ورود به بورس",
        "تاریخ ورود",
    ),
    "public_entry_date_gregorian": (
        "public_entry_date_gregorian",
        "listing_date_gregorian",
        "entry_date_gregorian",
        "ipo_date_gregorian",
        "first_trade_date_gregorian",
        "first_public_trading_date_gregorian",
        "date_gregorian",
    ),
    "source_type": ("source_type", "source_kind", "نوع منبع"),
    "source_title": ("source_title", "title", "source_name", "عنوان منبع"),
    "source_url": ("source_url", "url", "source_link", "لینک منبع"),
    "notes": ("notes", "note", "description", "توضیحات"),
    "import_status": ("import_status", "status"),
}


class ImportErrorCSV(RuntimeError):
    """Fail-closed import validation error."""


def _s(value) -> str:
    return "" if value is None else str(value).strip()


def _normalize_company_name(value: str) -> str:
    return normalize_ticker(_s(value))


def _read_input(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise ImportErrorCSV(f"trusted CSV not found: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def _resolve_column(df: pd.DataFrame, canonical: str) -> str:
    wanted = {alias.casefold(): alias for alias in COLUMN_ALIASES[canonical]}
    matches = []
    for column in df.columns:
        if column.casefold() in wanted:
            matches.append(column)
    if canonical in REQUIRED_CANONICAL_COLUMNS and not matches:
        raise ImportErrorCSV(
            f"required column missing for {canonical!r}; accepted aliases="
            f"{list(COLUMN_ALIASES[canonical])}"
        )
    if len(matches) > 1:
        raise ImportErrorCSV(
            f"multiple matching columns for {canonical!r}: {matches}"
        )
    return matches[0] if matches else ""


def canonicalize_input(df: pd.DataFrame) -> pd.DataFrame:
    mapped = {}
    for canonical in CANONICAL_COLUMNS:
        source_column = _resolve_column(df, canonical)
        if source_column:
            mapped[canonical] = df[source_column].map(_s)
        else:
            mapped[canonical] = pd.Series([""] * len(df), index=df.index, dtype=str)
    out = pd.DataFrame(mapped, columns=CANONICAL_COLUMNS)
    out = out.loc[out.apply(lambda row: any(_s(v) for v in row), axis=1)].copy()
    out.reset_index(drop=True, inplace=True)
    return out


def _validate_http_url(value: str) -> bool:
    if not value:
        return True
    parts = urlsplit(value)
    return parts.scheme in {"http", "https"} and bool(parts.hostname)


def _load_listing_master_tickers(partial_master_path: Path) -> set[str]:
    pm = read_csv(partial_master_path)
    return {normalize_ticker(_s(v)) for v in pm["ticker"].tolist() if _s(v)}


def _load_expected_names(partial_master_path: Path) -> dict[str, str]:
    pm = read_csv(partial_master_path)
    return {
        normalize_ticker(_s(r["ticker"])): _normalize_company_name(r["company_name"])
        for _, r in pm.iterrows()
        if _s(r["ticker"])
    }


def _load_expected_part03_rows(partial_master_path: Path) -> pd.DataFrame:
    pm = read_csv(partial_master_path)
    rows = pm[pm["ticker"].isin(PART03_TICKERS)].copy()
    if len(rows) != len(PART03_TICKERS):
        raise ImportErrorCSV(
            "partial master does not contain the exact 10 Part03 tickers"
        )
    return rows


def _normalize_scope(
    scope_tickers: Iterable[str] | None,
    *,
    all_listing_master: bool,
    partial_master_path: Path,
) -> tuple[list[str], str]:
    if all_listing_master:
        return sorted(_load_listing_master_tickers(partial_master_path)), "listing_master"
    if scope_tickers is None:
        return list(PART03_TICKERS), "part03"
    out = [normalize_ticker(_s(v)) for v in scope_tickers if _s(v)]
    if not out:
        raise ImportErrorCSV("scope_tickers resolved to an empty set")
    unknown = sorted(set(out) - set(PART03_TICKERS))
    if unknown:
        raise ImportErrorCSV(f"scope_tickers out of Part03 scope: {unknown}")
    return out, "part03"


def validate_input(
    canonical_df: pd.DataFrame,
    *,
    partial_master_path: Path = PARTIAL_MASTER,
    scope_tickers: Iterable[str] | None = None,
    allow_partial_scope: bool = False,
    all_listing_master: bool = False,
) -> dict:
    scope, scope_mode = _normalize_scope(
        scope_tickers,
        all_listing_master=all_listing_master,
        partial_master_path=partial_master_path,
    )
    master_tickers = _load_listing_master_tickers(partial_master_path)
    expected_names = _load_expected_names(partial_master_path)
    canonical_df = canonical_df.copy()
    canonical_df["ticker"] = canonical_df["ticker"].map(normalize_ticker)

    if all_listing_master:
        candidate_df = canonical_df.copy()
    else:
        candidate_df = canonical_df[canonical_df["ticker"].isin(scope)].copy()
    out_of_scope = canonical_df[~canonical_df["ticker"].isin(scope)].copy()

    errors: list[str] = []
    skipped_no_date: list[dict] = []
    skipped_not_in_master: list[dict] = []
    skipped_bad_status: list[dict] = []

    if not all_listing_master:
        if not allow_partial_scope and len(candidate_df) != len(scope):
            errors.append(
                f"trusted CSV must contain exactly {len(scope)} in-scope rows; "
                f"got {len(candidate_df)}"
            )
        if allow_partial_scope and len(candidate_df) == 0:
            errors.append("trusted CSV has no in-scope Part03 rows to import")
        actual_tickers = {_s(v) for v in candidate_df["ticker"].tolist()}
        expected_tickers = set(scope)
        if not allow_partial_scope and actual_tickers != expected_tickers:
            missing = sorted(expected_tickers - actual_tickers)
            extra = sorted(actual_tickers - expected_tickers)
            errors.append(f"ticker scope mismatch; missing={missing}, extra={extra}")

    if candidate_df["ticker"].duplicated().any():
        dupes = sorted(candidate_df.loc[candidate_df["ticker"].duplicated(), "ticker"].unique())
        errors.append(f"duplicate tickers in trusted CSV: {dupes}")

    conversions = []
    for idx, row in candidate_df.iterrows():
        row_no = idx + 2
        ticker = _s(row["ticker"])
        import_status = _s(row.get("import_status", "")).lower()
        if all_listing_master and import_status and import_status != "ok":
            skipped_bad_status.append(
                {"ticker": ticker, "import_status": import_status, "row": row_no}
            )
            continue
        if ticker not in master_tickers:
            skipped_not_in_master.append({"ticker": ticker, "row": row_no})
            continue

        company_name = _s(row["company_name"])
        if not company_name and ticker in expected_names:
            company_name = expected_names[ticker]
        if company_name and ticker in expected_names:
            got = _normalize_company_name(company_name)
            exp = expected_names[ticker]
            if got != exp:
                errors.append(
                    f"row {row_no}: company_name mismatch for ticker {ticker!r}; "
                    f"expected {exp!r}, got {got!r}"
                )

        date_j = _s(row["public_entry_date_jalali"])
        if not date_j:
            if all_listing_master:
                skipped_no_date.append({"ticker": ticker, "row": row_no})
                continue
            errors.append(f"row {row_no}: public_entry_date_jalali is required")
            continue
        provided_g = _s(row["public_entry_date_gregorian"])
        try:
            normalized_j = normalize_jalali(date_j)
            if provided_g:
                greg = jalali_str_to_gregorian_date(normalized_j).isoformat()
            elif not is_valid_exact_jalali_date(normalized_j):
                raise ValueError("not a valid exact Jalali calendar day")
            else:
                greg = jalali_str_to_gregorian_date(normalized_j).isoformat()
        except Exception as exc:
            if all_listing_master:
                skipped_no_date.append(
                    {"ticker": ticker, "row": row_no, "reason": str(exc)}
                )
                continue
            errors.append(
                f"row {row_no}: invalid exact Jalali public_entry_date_jalali "
                f"{date_j!r}: {exc}"
            )
            continue

        if provided_g and provided_g != greg:
            errors.append(
                f"row {row_no}: public_entry_date_gregorian mismatch; "
                f"expected {greg!r}, got {provided_g!r}"
            )
        if not _validate_http_url(_s(row["source_url"])):
            errors.append(f"row {row_no}: source_url must be a valid http(s) URL")
        conversions.append(
            {
                "ticker": ticker,
                "company_name": company_name or expected_names.get(ticker, ""),
                "public_entry_date_jalali": normalized_j,
                "public_entry_date_gregorian": greg,
            }
        )

    if errors:
        raise ImportErrorCSV("trusted CSV validation failed:\n  - " + "\n  - ".join(errors))
    if all_listing_master and not conversions:
        raise ImportErrorCSV("trusted CSV has no importable listing-master rows")

    imported_tickers = [item["ticker"] for item in conversions]
    return {
        "row_count": len(conversions),
        "ticker_count": len(imported_tickers),
        "conversions": conversions,
        "imported_tickers": imported_tickers,
        "scope_mode": scope_mode,
        "ignored_out_of_scope_tickers": sorted(out_of_scope["ticker"].unique().tolist()),
        "skipped_no_date": skipped_no_date,
        "skipped_not_in_master": skipped_not_in_master,
        "skipped_bad_status": skipped_bad_status,
    }


def build_partial_master_update(
    canonical_df: pd.DataFrame,
    *,
    partial_master_path: Path = PARTIAL_MASTER,
    scope_tickers: Iterable[str] | None = None,
    all_listing_master: bool = False,
) -> pd.DataFrame:
    scope, _ = _normalize_scope(
        scope_tickers,
        all_listing_master=all_listing_master,
        partial_master_path=partial_master_path,
    )
    partial = read_csv(partial_master_path)
    canonical_df = canonical_df.copy()
    canonical_df["ticker"] = canonical_df["ticker"].map(normalize_ticker)
    if all_listing_master:
        import_scope = set(canonical_df["ticker"].tolist())
    else:
        import_scope = set(scope)
    by_ticker = canonical_df[canonical_df["ticker"].isin(import_scope)].set_index("ticker")

    for idx, row in partial.iterrows():
        ticker = normalize_ticker(_s(row["ticker"]))
        if ticker not in by_ticker.index:
            continue
        src = by_ticker.loc[ticker]
        date_j = normalize_jalali(src["public_entry_date_jalali"])
        date_g = jalali_str_to_gregorian_date(date_j).isoformat()
        source_type = _s(src["source_type"]) or DEFAULT_SOURCE_TYPE
        source_title = _s(src["source_title"]) or DEFAULT_FIRST_TRADE_SOURCE_TITLE
        source_url = _s(src["source_url"])
        note_suffix = _s(src["notes"])
        note = MASTER_NOTE if not note_suffix else f"{MASTER_NOTE} {note_suffix}"
        if not all_listing_master and ticker in PART03_TICKERS:
            note = PART03_MASTER_NOTE if not note_suffix else f"{PART03_MASTER_NOTE} {note_suffix}"

        note_text = _s(src["notes"])
        partial.at[idx, "listing_date_jalali"] = ""
        partial.at[idx, "ipo_date_jalali"] = (
            date_j
            if note_text
            and any(
                marker in note_text.casefold()
                for marker in (
                    "official ipo",
                    "initial public offering",
                    "عرضه اولیه",
                    "ipo/listing date",
                )
            )
            else ""
        )
        partial.at[idx, "first_public_trading_date_jalali"] = date_j
        partial.at[idx, "first_public_trading_date_gregorian"] = date_g
        partial.at[idx, "source_1_type"] = source_type
        partial.at[idx, "source_1_title"] = source_title
        partial.at[idx, "source_1_url"] = source_url
        partial.at[idx, "source_2_type"] = ""
        partial.at[idx, "source_2_title"] = ""
        partial.at[idx, "source_2_url"] = ""
        partial.at[idx, "verification_status"] = VERIFICATION_STATUS
        partial.at[idx, "conflict_status"] = CONFLICT_STATUS
        partial.at[idx, "notes"] = note

    return partial


def _write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def _write_json(payload: dict, path: Path) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_import(
    *,
    input_path: Path = DEFAULT_INPUT,
    partial_master_path: Path = PARTIAL_MASTER,
    report_path: Path = DEFAULT_REPORT,
    apply: bool = False,
    scope_tickers: Iterable[str] | None = None,
    allow_partial_scope: bool = False,
    all_listing_master: bool = False,
) -> dict:
    raw_df = _read_input(input_path)
    canonical_df = canonicalize_input(raw_df)
    validation = validate_input(
        canonical_df,
        partial_master_path=partial_master_path,
        scope_tickers=scope_tickers,
        allow_partial_scope=allow_partial_scope,
        all_listing_master=all_listing_master,
    )
    normalized_map = {
        item["ticker"]: item for item in validation["conversions"]
    }
    canonical_df = canonical_df.copy()
    canonical_df["ticker"] = canonical_df["ticker"].map(normalize_ticker)
    canonical_df = canonical_df[canonical_df["ticker"].isin(normalized_map)].copy()
    for idx, row in canonical_df.iterrows():
        info = normalized_map[_s(row["ticker"])]
        canonical_df.at[idx, "company_name"] = (
            _s(row.get("company_name")) or info["company_name"]
        )
        canonical_df.at[idx, "public_entry_date_jalali"] = info["public_entry_date_jalali"]
        canonical_df.at[idx, "public_entry_date_gregorian"] = info["public_entry_date_gregorian"]
        if not _s(row.get("source_title")) and "first_trade_date" in ",".join(raw_df.columns):
            canonical_df.at[idx, "source_title"] = DEFAULT_FIRST_TRADE_SOURCE_TITLE
    updated_partial = build_partial_master_update(
        canonical_df,
        partial_master_path=partial_master_path,
        scope_tickers=validation.get("imported_tickers") or scope_tickers,
        all_listing_master=all_listing_master,
    )

    scope, scope_mode = _normalize_scope(
        scope_tickers,
        all_listing_master=all_listing_master,
        partial_master_path=partial_master_path,
    )
    report = {
        "status": "validated_dry_run" if not apply else "import_applied",
        "input_path": str(input_path),
        "input_sha256": sha(input_path),
        "partial_master_path": str(partial_master_path),
        "scope_mode": validation.get("scope_mode", scope_mode),
        "scope_tickers": validation.get("imported_tickers", scope),
        "row_count": validation["row_count"],
        "ticker_count": validation["ticker_count"],
        "verification_status": VERIFICATION_STATUS,
        "conflict_status": CONFLICT_STATUS,
        "csv_columns_detected": list(raw_df.columns),
        "canonical_columns": list(canonical_df.columns),
        "date_conversions": validation["conversions"],
        "ignored_out_of_scope_tickers": validation["ignored_out_of_scope_tickers"],
        "skipped_no_date": validation.get("skipped_no_date", []),
        "skipped_not_in_master": validation.get("skipped_not_in_master", []),
        "skipped_bad_status": validation.get("skipped_bad_status", []),
        "allow_partial_scope": bool(allow_partial_scope),
        "all_listing_master": bool(all_listing_master),
        "apply_requested": bool(apply),
    }

    if apply:
        _write_csv(updated_partial, partial_master_path)
        _write_json(report, report_path)

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--partial-master", type=Path, default=PARTIAL_MASTER)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist changes to listing_master_partial_verified_stage124.csv",
    )
    parser.add_argument(
        "--allow-partial-scope",
        action="store_true",
        help="Allow importing only the in-scope Part03 tickers present in the CSV",
    )
    parser.add_argument(
        "--all-listing-master",
        action="store_true",
        help="Import all CSV rows that match tickers in listing_master_partial_verified_stage124.csv",
    )
    parser.add_argument(
        "--scope-tickers",
        nargs="*",
        default=None,
        help="Explicit subset of Part03 tickers to import",
    )
    args = parser.parse_args(argv)

    try:
        report = run_import(
            input_path=args.input,
            partial_master_path=args.partial_master,
            report_path=args.report,
            apply=args.apply,
            scope_tickers=args.scope_tickers,
            allow_partial_scope=args.allow_partial_scope,
            all_listing_master=args.all_listing_master,
        )
    except ImportErrorCSV as exc:
        print(f"CSV IMPORT FAILED: {exc}")
        return 1

    print("Stage124 trusted CSV import:")
    print(f"  status          : {report['status']}")
    print(f"  scope mode      : {report['scope_mode']}")
    print(f"  rows validated  : {report['row_count']}")
    print(f"  tickers covered : {report['ticker_count']}")
    if report.get("skipped_bad_status"):
        print(f"  skipped status  : {len(report['skipped_bad_status'])}")
    if report.get("skipped_no_date"):
        print(f"  skipped no date : {len(report['skipped_no_date'])}")
    if report.get("skipped_not_in_master"):
        print(f"  skipped unknown : {len(report['skipped_not_in_master'])}")
    if not args.apply:
        print("  mode            : DRY RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
