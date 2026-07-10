"""Stage124 — finalize listing dates from official TSE API CSV batches.

Reads raw API exports only from ``stage124/official_api/`` and writes the
canonical verified master at ``stage124/listing_master_verified_stage124.csv``.
First-trade dates are stored exclusively in the first-public-trading columns.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .stage124_batch02_part03 import is_valid_exact_jalali_date
from .stage124_batch02_v2 import (
    OUT,
    jalali_str_to_gregorian_date,
    normalize_jalali,
    normalize_ticker,
    read_csv,
    sha,
)
from .stage124_part03_csv_import import (
    CONFLICT_STATUS,
    DEFAULT_FIRST_TRADE_SOURCE_TITLE,
    DEFAULT_SOURCE_TYPE,
    MASTER_NOTE,
    VERIFICATION_STATUS,
)

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = OUT / "listing_master_template_stage124.csv"
VERIFIED_MASTER = OUT / "listing_master_verified_stage124.csv"
OFFICIAL_API_DIR = OUT / "official_api"
MANIFEST = OFFICIAL_API_DIR / "import_manifest.json"
METADATA = OFFICIAL_API_DIR / "metadata_and_hashes.json"

TEMPLATE_COLUMNS = list(read_csv(TEMPLATE).columns)
ALLOWED_VERIFICATION_STATUSES = {VERIFICATION_STATUS}
JALALI_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
IPO_NOTE_MARKERS = (
    "official ipo",
    "initial public offering",
    "عرضه اولیه",
)
IPO_NEGATIVE_MARKERS = (
    "not official ipo",
    "not official ipo/listing",
    "first observed trading date",
)

RAW_BATCH_SPECS = [
    {
        "repo_name": "tse_first_trade_dates_batch01_bulk.csv",
        "role": "bulk_first_trade_export",
        "description": "Primary bulk export (119 importable rows; ambiguous rows skipped).",
    },
    {
        "repo_name": "tse_first_trade_dates_batch02_ambiguous_resolved.csv",
        "role": "ambiguous_resolved_export",
        "description": "Resolved ambiguous / pending tickers from the bulk export.",
    },
    {
        "repo_name": "tse_first_trade_dates_batch03_final_pair.csv",
        "role": "final_pair_export",
        "description": "Final two tickers (اروند, وکغدیر) supplied after bulk import.",
    },
]


class FinalizeError(RuntimeError):
    """Fail-closed verified-master build error."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _s(value) -> str:
    return "" if value is None else str(value).strip()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_api_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def load_official_api_batches(*, official_api_dir: Path = OFFICIAL_API_DIR) -> tuple[list[dict], pd.DataFrame]:
    if not official_api_dir.is_dir():
        raise FinalizeError(f"official API directory not found: {official_api_dir}")

    batches: list[dict] = []
    frames: list[pd.DataFrame] = []
    for spec in RAW_BATCH_SPECS:
        path = official_api_dir / spec["repo_name"]
        if not path.is_file():
            raise FinalizeError(f"raw API batch missing: {path}")
        raw = _read_api_csv(path)
        batches.append(
            {
                **spec,
                "path": (
                    str(path.relative_to(ROOT))
                    if path.is_relative_to(ROOT)
                    else f"{official_api_dir.name}/{spec['repo_name']}"
                ),
                "sha256": _file_sha256(path),
                "row_count": len(raw),
                "columns": list(raw.columns),
            }
        )
        frames.append(raw)

    merged = pd.concat(frames, ignore_index=True)
    merged["ticker"] = merged["symbol"].map(normalize_ticker)
    ok = merged[merged["status"].map(_s).str.lower() == "ok"].copy()
    if ok["ticker"].duplicated().any():
        dupes = sorted(ok.loc[ok["ticker"].duplicated(), "ticker"].unique())
        raise FinalizeError(f"duplicate tickers across official API batches: {dupes}")
    return batches, ok


def _is_explicit_ipo_event(note: str, status: str = "") -> bool:
    haystack = f"{note} {status}".casefold()
    if any(marker in haystack for marker in IPO_NEGATIVE_MARKERS):
        return False
    return any(marker in haystack for marker in IPO_NOTE_MARKERS)


def _normalize_api_row(row: pd.Series) -> dict:
    ticker = normalize_ticker(_s(row["ticker"]))
    date_j_raw = _s(row.get("first_trade_date_jalali", ""))
    date_g_raw = _s(row.get("first_trade_date_gregorian", ""))
    if not date_j_raw:
        raise FinalizeError(f"official API row for {ticker!r} is missing first_trade_date_jalali")
    date_j = normalize_jalali(date_j_raw)
    try:
        date_g = jalali_str_to_gregorian_date(date_j).isoformat()
    except Exception as exc:
        raise FinalizeError(
            f"invalid Jalali first-trade date for {ticker!r}: {date_j_raw!r} ({exc})"
        ) from exc
    if date_g_raw and date_g_raw != date_g:
        raise FinalizeError(
            f"Gregorian mismatch for {ticker!r}: api={date_g_raw!r}, expected={date_g!r}"
        )
    if not date_g_raw and not is_valid_exact_jalali_date(date_j):
        raise FinalizeError(f"invalid exact Jalali first-trade date for {ticker!r}: {date_j_raw!r}")
    note = _s(row.get("note", ""))
    return {
        "ticker": ticker,
        "first_public_trading_date_jalali": date_j,
        "first_public_trading_date_gregorian": date_g,
        "ipo_date_jalali": date_j if _is_explicit_ipo_event(note) else "",
        "notes": MASTER_NOTE if not note else f"{MASTER_NOTE} {note}",
        "ins_code": _s(row.get("insCode", "")),
    }


def validate_template_coverage(template: pd.DataFrame, api_ok: pd.DataFrame) -> dict:
    if list(template.columns) != TEMPLATE_COLUMNS:
        raise FinalizeError("template columns do not match expected Stage124 schema")
    if len(template) != 130:
        raise FinalizeError(f"template must contain 130 tickers, got {len(template)}")
    if template["ticker"].duplicated().any():
        raise FinalizeError("duplicate tickers in template")

    template_tickers = [normalize_ticker(_s(v)) for v in template["ticker"]]
    api_tickers = {normalize_ticker(_s(v)) for v in api_ok["ticker"]}
    template_set = set(template_tickers)
    missing = sorted(template_set - api_tickers)
    extra = sorted(api_tickers - template_set)
    if missing:
        raise FinalizeError(f"official API missing template tickers: {missing}")
    if extra:
        raise FinalizeError(f"official API has tickers outside template: {extra}")
    if len(api_ok) != 130:
        raise FinalizeError(f"official API must provide exactly 130 ok rows, got {len(api_ok)}")

    return {
        "row_count": len(template),
        "verified_tse_csv_imported": len(template),
        "template_ticker_count": len(template_set),
        "api_ticker_count": len(api_tickers),
    }


def build_verified_master(
    *,
    template_path: Path = TEMPLATE,
    official_api_dir: Path = OFFICIAL_API_DIR,
    verified_master_path: Path = VERIFIED_MASTER,
    api_ok: pd.DataFrame | None = None,
) -> pd.DataFrame:
    template = read_csv(template_path)
    if api_ok is None:
        _, api_ok = load_official_api_batches(official_api_dir=official_api_dir)
    validate_template_coverage(template, api_ok)

    api_map = {
        item["ticker"]: item
        for item in (_normalize_api_row(row) for _, row in api_ok.iterrows())
    }
    out = template[TEMPLATE_COLUMNS].copy()
    for idx, row in out.iterrows():
        ticker = normalize_ticker(_s(row["ticker"]))
        src = api_map[ticker]
        out.at[idx, "admission_date_jalali"] = ""
        out.at[idx, "listing_date_jalali"] = ""
        out.at[idx, "ipo_date_jalali"] = src["ipo_date_jalali"]
        out.at[idx, "first_public_trading_date_jalali"] = src["first_public_trading_date_jalali"]
        out.at[idx, "first_public_trading_date_gregorian"] = src["first_public_trading_date_gregorian"]
        out.at[idx, "source_1_type"] = DEFAULT_SOURCE_TYPE
        out.at[idx, "source_1_title"] = DEFAULT_FIRST_TRADE_SOURCE_TITLE
        out.at[idx, "source_1_url"] = ""
        out.at[idx, "source_2_type"] = ""
        out.at[idx, "source_2_title"] = ""
        out.at[idx, "source_2_url"] = ""
        out.at[idx, "verification_status"] = VERIFICATION_STATUS
        out.at[idx, "conflict_status"] = CONFLICT_STATUS
        out.at[idx, "notes"] = src["notes"]

    verified_master_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(verified_master_path, index=False, encoding="utf-8-sig")
    return out


def validate_verified_master(df: pd.DataFrame, template: pd.DataFrame) -> None:
    if list(df.columns) != list(template.columns):
        raise FinalizeError("verified master columns do not match template")
    if len(df) != 130 or df["ticker"].nunique() != 130:
        raise FinalizeError("verified master must contain exactly 130 unique tickers")
    if df["ticker"].duplicated().any():
        raise FinalizeError("verified master contains duplicate tickers")
    if set(normalize_ticker(_s(v)) for v in df["ticker"]) != set(
        normalize_ticker(_s(v)) for v in template["ticker"]
    ):
        raise FinalizeError("verified master ticker set does not match template")

    for _, row in df.iterrows():
        ticker = _s(row["ticker"])
        status = _s(row["verification_status"])
        if status not in ALLOWED_VERIFICATION_STATUSES:
            raise FinalizeError(f"invalid verification_status for {ticker}: {status!r}")
        date_j = _s(row["first_public_trading_date_jalali"])
        date_g = _s(row["first_public_trading_date_gregorian"])
        if not date_j or not date_g:
            raise FinalizeError(f"missing first-public-trading date for {ticker}")
        if not JALALI_RE.match(date_j):
            raise FinalizeError(f"invalid Jalali format for {ticker}: {date_j!r}")
        expected_g = jalali_str_to_gregorian_date(date_j).isoformat()
        if date_g != expected_g:
            raise FinalizeError(
                f"Gregorian conversion mismatch for {ticker}: {date_g!r} != {expected_g!r}"
            )
        if _s(row["listing_date_jalali"]):
            raise FinalizeError(f"listing_date_jalali must remain empty for {ticker}")
        ipo = _s(row["ipo_date_jalali"])
        if ipo and ipo != date_j:
            raise FinalizeError(f"ipo_date_jalali must be empty unless explicit IPO for {ticker}")


def write_manifest(
    *,
    batches: list[dict],
    build_stats: dict,
    verified_master_path: Path = VERIFIED_MASTER,
    manifest_path: Path = MANIFEST,
) -> dict:
    manifest = {
        "stage": "stage124_official_api_finalize",
        "generated_at_utc": _utc_now(),
        "source_kind": "tehran_stock_exchange_api_first_trade_dates",
        "date_semantics": "first_observed_trading_date_not_official_ipo_listing_date",
        "verified_master_path": str(verified_master_path.relative_to(ROOT)),
        "template_path": str(TEMPLATE.relative_to(ROOT)),
        "official_api_dir": str(OFFICIAL_API_DIR.relative_to(ROOT)),
        "verified_master_sha256": sha(verified_master_path),
        "build_stats": build_stats,
        "allowed_verification_statuses": sorted(ALLOWED_VERIFICATION_STATUSES),
        "raw_batches": batches,
        "notes": [
            "All inputs are read only from stage124/official_api/.",
            "First-trade dates are written only to first_public_trading_date_* columns.",
            "ipo_date_jalali is populated only when the API row explicitly denotes an IPO event.",
        ],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def write_metadata(*, manifest: dict, metadata_path: Path = METADATA) -> dict:
    files = []
    for batch in manifest["raw_batches"]:
        files.append(
            {
                "relative_path": batch["path"],
                "file_role": batch["role"],
                "sha256": batch["sha256"],
            }
        )
    for rel, role in (
        (manifest["verified_master_path"], "verified_listing_master"),
        (manifest["template_path"], "template_schema"),
        (str(MANIFEST.relative_to(ROOT)), "import_manifest"),
    ):
        path = ROOT / rel
        files.append(
            {
                "relative_path": rel,
                "file_role": role,
                "sha256": sha(path) if path.is_file() else "",
            }
        )
    payload = {
        "generated_at_utc": manifest["generated_at_utc"],
        "allowed_verification_statuses": manifest["allowed_verification_statuses"],
        "files": files,
    }
    metadata_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def verify_manifest_hashes(*, official_api_dir: Path = OFFICIAL_API_DIR) -> None:
    if not MANIFEST.is_file():
        raise FinalizeError(f"import manifest not found: {MANIFEST}")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for batch in manifest["raw_batches"]:
        path = ROOT / batch["path"]
        actual = _file_sha256(path)
        if actual != batch["sha256"]:
            raise FinalizeError(
                f"SHA-256 mismatch for {path.name}: manifest={batch['sha256']}, actual={actual}"
            )


def run_finalize(
    *,
    official_api_dir: Path = OFFICIAL_API_DIR,
    template_path: Path = TEMPLATE,
    verified_master_path: Path = VERIFIED_MASTER,
    write_sidecar_metadata: bool | None = None,
) -> dict:
    if write_sidecar_metadata is None:
        write_sidecar_metadata = official_api_dir.resolve() == OFFICIAL_API_DIR.resolve()
    batches, api_ok = load_official_api_batches(official_api_dir=official_api_dir)
    template = read_csv(template_path)
    build_stats = validate_template_coverage(template, api_ok)
    verified = build_verified_master(
        template_path=template_path,
        official_api_dir=official_api_dir,
        verified_master_path=verified_master_path,
        api_ok=api_ok,
    )
    validate_verified_master(verified, template)
    manifest = None
    metadata = None
    if write_sidecar_metadata:
        manifest = write_manifest(
            batches=batches,
            build_stats=build_stats,
            verified_master_path=verified_master_path,
        )
        metadata = write_metadata(manifest=manifest)
        verify_manifest_hashes(official_api_dir=official_api_dir)
    return {
        "status": "verified_master_finalized",
        "verified_master_path": str(verified_master_path),
        "official_api_dir": str(official_api_dir),
        "row_count": build_stats["row_count"],
        "manifest_path": str(MANIFEST) if write_sidecar_metadata else "",
        "metadata_path": str(METADATA) if write_sidecar_metadata else "",
        "verified_master_sha256": sha(verified_master_path),
        "metadata": metadata,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--official-api-dir",
        type=Path,
        default=OFFICIAL_API_DIR,
        help="Directory containing committed TSE API CSV batches",
    )
    parser.add_argument("--template", type=Path, default=TEMPLATE)
    parser.add_argument("--verified-master", type=Path, default=VERIFIED_MASTER)
    args = parser.parse_args(argv)

    try:
        report = run_finalize(
            official_api_dir=args.official_api_dir,
            template_path=args.template,
            verified_master_path=args.verified_master,
        )
    except FinalizeError as exc:
        print(f"FINALIZE FAILED: {exc}")
        return 1

    print("Stage124 official API finalize:")
    print(f"  status            : {report['status']}")
    print(f"  verified master   : {report['verified_master_path']}")
    print(f"  rows              : {report['row_count']}")
    print(f"  official_api dir  : {report['official_api_dir']}")
    print(f"  manifest          : {report['manifest_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
