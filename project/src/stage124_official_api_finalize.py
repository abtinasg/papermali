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
from urllib.parse import quote

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

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = OUT / "listing_master_template_stage124.csv"
VERIFIED_MASTER = OUT / "listing_master_verified_stage124.csv"
OFFICIAL_API_DIR = OUT / "official_api"
RAW_DIR = OFFICIAL_API_DIR / "raw"
MANIFEST = OFFICIAL_API_DIR / "import_manifest.json"
METADATA = OFFICIAL_API_DIR / "metadata_and_hashes.json"
CONFLICT_AUDIT = OFFICIAL_API_DIR / "tse_first_trade_conflict_audit.csv"
PILOT15_CONFIRMED = OUT / "listing_pilot15_user_confirmed_stage124.csv"
PART02_PROVENANCE = OUT / "batch02_parts/part02_source_provenance_10tickers.csv"

VERIFICATION_STATUS = "verified_tse_api_first_observed_trade"
DATE_SEMANTICS = "first_observed_trading_date_from_official_tse_api"
CONFLICT_UNRESOLVED = "unresolved_api_vs_prior_research"
SOURCE_TYPE = "official_tse_api"
SOURCE_TITLE = "TSETMC ClosingPriceDailyList (first observed trade)"
TSE_DOCUMENTATION_URL = "https://www.tse.ir/"
API_PROVIDER = "Tehran Stock Exchange Market Data (TSETMC CDN API)"
API_ENDPOINT_TEMPLATE = (
    "https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceDailyList/{ins_code}/0"
)
EXTRACTION_SCRIPT = (
    "project-owner batch exporter: earliest non-zero trade day per insCode from "
    "ClosingPriceDailyList"
)
API_RESPONSE_SEMANTICS = (
    "Earliest observed closing-price record date (dEven) for the resolved insCode; "
    "used as first observed trading date, not official IPO/admission/listing date."
)
MASTER_NOTE = (
    "Official TSE API first observed trading date imported for Stage124 verified "
    "master. This date is not necessarily IPO, admission, or listing."
)

TEMPLATE_COLUMNS = list(read_csv(TEMPLATE).columns)
ALLOWED_VERIFICATION_STATUSES = {VERIFICATION_STATUS}
JALALI_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CONFLICT_AUDIT_COLUMNS = [
    "ticker",
    "previous_date",
    "api_observed_date",
    "previous_event_type",
    "api_event_type",
    "disposition",
    "resolution_basis",
]

RAW_BATCH_SPECS = [
    {
        "repo_name": "tse_first_trade_dates_batch01_bulk.csv",
        "role": "bulk_first_trade_export",
        "description": "Primary bulk export (ambiguous rows skipped).",
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


def _source_url_for_ins_code(ins_code: str) -> str:
    ins_code = _s(ins_code)
    if not ins_code:
        return TSE_DOCUMENTATION_URL
    return API_ENDPOINT_TEMPLATE.format(ins_code=quote(ins_code, safe=""))


def _is_explicit_ipo_event(note: str, status: str = "") -> bool:
    haystack = f"{note} {status}".casefold()
    if any(marker in haystack for marker in IPO_NEGATIVE_MARKERS):
        return False
    return any(marker in haystack for marker in IPO_NOTE_MARKERS)


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
                    else spec["repo_name"]
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
        "source_url": _source_url_for_ins_code(_s(row.get("insCode", ""))),
    }


def _load_previous_research_dates() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}

    if PILOT15_CONFIRMED.is_file():
        pilot = read_csv(PILOT15_CONFIRMED)
        for _, row in pilot.iterrows():
            ticker = normalize_ticker(_s(row["ticker"]))
            date_j = normalize_jalali(_s(row["confirmed_public_entry_date_jalali"]))
            if not date_j:
                continue
            out.setdefault(ticker, []).append(
                {
                    "date": date_j,
                    "event_type": _s(row.get("canonical_event_type", "user_confirmed_public_entry")),
                    "basis": "listing_pilot15_user_confirmed_stage124.csv",
                }
            )
            tsetmc_raw = _s(row.get("tsetmc_candidate_date_jalali", ""))
            if tsetmc_raw and tsetmc_raw.casefold() != "ambiguous":
                try:
                    tsetmc = normalize_jalali(tsetmc_raw)
                except ValueError:
                    tsetmc = ""
                if tsetmc and tsetmc != date_j:
                    out.setdefault(ticker, []).append(
                        {
                            "date": tsetmc,
                            "event_type": "tsetmc_candidate_audit_only",
                            "basis": "listing_pilot15_user_confirmed_stage124.csv (tsetmc_candidate_date_jalali)",
                        }
                    )

    if PART02_PROVENANCE.is_file():
        prov = read_csv(PART02_PROVENANCE)
        for _, row in prov.iterrows():
            ticker = normalize_ticker(_s(row["ticker"]))
            pub_raw = _s(row.get("publication_date", ""))
            if not pub_raw:
                continue
            try:
                date_j = normalize_jalali(pub_raw)
            except ValueError:
                continue
            out.setdefault(ticker, []).append(
                {
                    "date": date_j,
                    "event_type": _s(row.get("source_type", "prior_manual_source")),
                    "basis": f"part02_source_provenance: {_s(row.get('source_title', ''))}",
                }
            )

    return out


def build_conflict_audit(api_map: dict[str, dict]) -> pd.DataFrame:
    previous = _load_previous_research_dates()
    rows: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    for ticker, api in sorted(api_map.items()):
        api_date = api["first_public_trading_date_jalali"]
        for prior in previous.get(ticker, []):
            prior_date = prior["date"]
            if prior_date == api_date:
                continue
            key = (ticker, prior_date, api_date)
            if key in seen:
                continue
            seen.add(key)
            disposition = "unresolved_prior_research_differs_from_api_first_observed_trade"
            resolution_basis = (
                f"prior={prior_date} ({prior['event_type']}) from {prior['basis']}; "
                f"api={api_date} ({DATE_SEMANTICS})"
            )
            if ticker == "حکشتی" and prior_date == "1387-02-28" and api_date == "1387-02-29":
                disposition = "unresolved_one_day_gap_ipo_news_vs_api_first_observed_trade"
                resolution_basis = (
                    "Part02 manual research documented contemporaneous IPO/listing news on "
                    "1387-02-28 (همشهری آنلاین) while the official TSE API first observed "
                    "trade date is 1387-02-29; one-day gap retained for manual review."
                )
            rows.append(
                {
                    "ticker": ticker,
                    "previous_date": prior_date,
                    "api_observed_date": api_date,
                    "previous_event_type": prior["event_type"],
                    "api_event_type": DATE_SEMANTICS,
                    "disposition": disposition,
                    "resolution_basis": resolution_basis,
                }
            )

    audit = pd.DataFrame(rows, columns=CONFLICT_AUDIT_COLUMNS)
    CONFLICT_AUDIT.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(CONFLICT_AUDIT, index=False, encoding="utf-8-sig")
    return audit


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
        "verified_tse_api_first_observed_trade": len(template),
        "template_ticker_count": len(template_set),
        "api_ticker_count": len(api_tickers),
    }


def build_verified_master(
    *,
    template_path: Path = TEMPLATE,
    api_ok: pd.DataFrame,
    conflict_audit: pd.DataFrame,
    verified_master_path: Path = VERIFIED_MASTER,
) -> pd.DataFrame:
    template = read_csv(template_path)
    validate_template_coverage(template, api_ok)

    api_map = {
        item["ticker"]: item
        for item in (_normalize_api_row(row) for _, row in api_ok.iterrows())
    }
    conflict_tickers = set(conflict_audit["ticker"].map(normalize_ticker)) if len(conflict_audit) else set()

    out = template[TEMPLATE_COLUMNS].copy()
    for idx, row in out.iterrows():
        ticker = normalize_ticker(_s(row["ticker"]))
        src = api_map[ticker]
        out.at[idx, "admission_date_jalali"] = ""
        out.at[idx, "listing_date_jalali"] = ""
        out.at[idx, "ipo_date_jalali"] = src["ipo_date_jalali"]
        out.at[idx, "first_public_trading_date_jalali"] = src["first_public_trading_date_jalali"]
        out.at[idx, "first_public_trading_date_gregorian"] = src["first_public_trading_date_gregorian"]
        out.at[idx, "source_1_type"] = SOURCE_TYPE
        out.at[idx, "source_1_title"] = SOURCE_TITLE
        out.at[idx, "source_1_url"] = src["source_url"]
        out.at[idx, "source_2_type"] = ""
        out.at[idx, "source_2_title"] = ""
        out.at[idx, "source_2_url"] = ""
        out.at[idx, "verification_status"] = VERIFICATION_STATUS
        out.at[idx, "conflict_status"] = (
            CONFLICT_UNRESOLVED if ticker in conflict_tickers else ""
        )
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
        if not _s(row["source_1_url"]):
            raise FinalizeError(f"source_1_url must be populated for {ticker}")
        conflict = _s(row["conflict_status"])
        if conflict == "resolved_tse_csv_imported":
            raise FinalizeError(f"conflict_status must not be auto-resolved for {ticker}")


def write_raw_response_manifests(*, batches: list[dict], official_api_dir: Path = OFFICIAL_API_DIR) -> list[dict]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifests: list[dict] = []
    retrieved_at = _utc_now()
    for batch in batches:
        path = official_api_dir / Path(batch["path"]).name
        payload = {
            "batch_file": batch["path"],
            "response_content_sha256": batch["sha256"],
            "api_provider": API_PROVIDER,
            "exact_endpoint_url": API_ENDPOINT_TEMPLATE,
            "request_parameters": {
                "ins_code": "per-row insCode column in batch CSV",
                "history_offset": "0",
            },
            "retrieved_at_utc": retrieved_at,
            "extraction_script": EXTRACTION_SCRIPT,
            "api_response_semantics": API_RESPONSE_SEMANTICS,
            "date_semantics": DATE_SEMANTICS,
            "note": (
                "Committed batch CSV is the normalized extraction output derived from "
                "raw ClosingPriceDailyList JSON responses."
            ),
        }
        manifest_path = RAW_DIR / f"{Path(batch['path']).stem}_response_manifest.json"
        manifest_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        manifests.append({"path": str(manifest_path.relative_to(ROOT)), "sha256": _file_sha256(manifest_path)})
    return manifests


def write_manifest(
    *,
    batches: list[dict],
    raw_manifests: list[dict],
    build_stats: dict,
    conflict_count: int,
    verified_master_path: Path = VERIFIED_MASTER,
    manifest_path: Path = MANIFEST,
) -> dict:
    manifest = {
        "stage": "stage124_official_api_finalize",
        "generated_at_utc": _utc_now(),
        "api_provider": API_PROVIDER,
        "exact_endpoint_url": API_ENDPOINT_TEMPLATE,
        "request_parameters": {
            "ins_code": "per-row insCode in committed batch CSV files",
            "history_offset": "0",
        },
        "retrieved_at_utc": _utc_now(),
        "extraction_script": EXTRACTION_SCRIPT,
        "api_response_semantics": API_RESPONSE_SEMANTICS,
        "date_semantics": DATE_SEMANTICS,
        "verified_master_path": str(verified_master_path.relative_to(ROOT)),
        "template_path": str(TEMPLATE.relative_to(ROOT)),
        "official_api_dir": str(OFFICIAL_API_DIR.relative_to(ROOT)),
        "conflict_audit_path": str(CONFLICT_AUDIT.relative_to(ROOT)),
        "verified_master_sha256": sha(verified_master_path),
        "build_stats": build_stats,
        "conflict_row_count": conflict_count,
        "allowed_verification_statuses": sorted(ALLOWED_VERIFICATION_STATUSES),
        "raw_batches": batches,
        "raw_response_manifests": raw_manifests,
        "notes": [
            "All inputs are read only from stage124/official_api/.",
            "First-trade dates are written only to first_public_trading_date_* columns.",
            "ipo_date_jalali is populated only when the API row explicitly denotes an IPO event.",
            "conflict_status is not auto-resolved; see tse_first_trade_conflict_audit.csv.",
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
    for raw_manifest in manifest["raw_response_manifests"]:
        files.append(
            {
                "relative_path": raw_manifest["path"],
                "file_role": "raw_response_manifest",
                "sha256": raw_manifest["sha256"],
            }
        )
    for rel, role in (
        (manifest["verified_master_path"], "verified_listing_master"),
        (manifest["template_path"], "template_schema"),
        (manifest["conflict_audit_path"], "first_trade_conflict_audit"),
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
        "date_semantics": manifest["date_semantics"],
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
        path = ROOT / batch["path"] if not Path(batch["path"]).is_absolute() else Path(batch["path"])
        if not path.is_file():
            path = official_api_dir / Path(batch["path"]).name
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
    api_map = {
        item["ticker"]: item
        for item in (_normalize_api_row(row) for _, row in api_ok.iterrows())
    }
    conflict_audit = build_conflict_audit(api_map)
    template = read_csv(template_path)
    build_stats = validate_template_coverage(template, api_ok)
    verified = build_verified_master(
        template_path=template_path,
        api_ok=api_ok,
        conflict_audit=conflict_audit,
        verified_master_path=verified_master_path,
    )
    validate_verified_master(verified, template)

    raw_manifests: list[dict] = []
    manifest = None
    metadata = None
    if write_sidecar_metadata:
        raw_manifests = write_raw_response_manifests(batches=batches, official_api_dir=official_api_dir)
        manifest = write_manifest(
            batches=batches,
            raw_manifests=raw_manifests,
            build_stats=build_stats,
            conflict_count=len(conflict_audit),
            verified_master_path=verified_master_path,
        )
        metadata = write_metadata(manifest=manifest)
        verify_manifest_hashes(official_api_dir=official_api_dir)

    return {
        "status": "verified_master_finalized",
        "verified_master_path": str(verified_master_path),
        "official_api_dir": str(official_api_dir),
        "row_count": build_stats["row_count"],
        "conflict_row_count": len(conflict_audit),
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
    print(f"  conflict rows     : {report['conflict_row_count']}")
    print(f"  official_api dir  : {report['official_api_dir']}")
    print(f"  manifest          : {report['manifest_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
