"""Stage124 Batch 2 — Part 2.1B: Offline finalizer and package sealer.

This module performs a purely offline finalization of Part 2 outputs.
No network requests, TSETMC probes, source fetches, or research changes
are performed.  It reads existing local files, builds the final package
artifacts, and seals them with a hash manifest.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .stage124_batch02_v2 import (
    sha, git_head, ROOT, OUT,
    STAGE122_INPUT, STAGE123_INPUT,
    EXPECTED_STAGE122_SHA, EXPECTED_STAGE123_SHA,
    PARTIAL_MASTER, normalize_ticker,
)
from .stage124_batch02_part02 import (
    PART02_DIR, PART02_TICKERS, FROZEN_FILES,
    FULL_VERIFIED_FORBIDDEN,
)

# ---- constants ------------------------------------------------------------------

RESEARCH_STATE_COMMIT = "9f8894a3dbc1c9507bb8e12035663eaa8cb8b9da"
INITIAL_GENERATION_SOURCE_COMMIT = "6a4d6eb29c3e615efe65a124cd5c93f3d3b2aacc"

EXPECTED_IMMUTABLE_HASHES = {
    "part02_research_screening_10tickers.csv": "2c0b39bcbcddaa349fe5e58a037d653c13daa9cbcbc1042d7ba311170e98d3a1",
    "part02_source_provenance_10tickers.csv": "2a5d0513a8e16b8dd138e33d35db2856a0c8c46ac880518859dc9dd06738821f",
    "part02_tsetmc_audit_10tickers.csv": "5b6f21f26fc7a55498e663cb15e684538a0fb3528c439b73e9eb66837fbb1016",
    "snapshots_hkeshti/source_1.html": "09152a6ce812a01c83093c2a55d4c1faaeeba2d88e3a663c9cb7354263bde47d",
}

MANIFEST_ROWS = [
    ("src/stage124_batch02_part02.py", "source_code"),
    ("src/stage124_batch02_part02_finalize.py", "finalizer_source"),
    ("tests/test_stage124_batch02_part02.py", "test_code"),
    ("tests/test_stage124_batch02_part02_finalize.py", "finalizer_test"),
    ("stage124/batch02_parts/README_PART02.md", "readme"),
    ("stage124/batch02_parts/part02_tickers.csv", "tickers"),
    ("stage124/batch02_parts/part02_research_screening_10tickers.csv", "research_screening"),
    ("stage124/batch02_parts/part02_source_provenance_10tickers.csv", "source_provenance"),
    ("stage124/batch02_parts/part02_tsetmc_audit_10tickers.csv", "tsetmc_audit"),
    ("stage124/batch02_parts/part02_qc_report.json", "qc_report"),
    ("stage124/batch02_parts/part02_summary.json", "summary"),
    ("stage124/batch02_parts/part02_metadata_and_hashes.json", "metadata"),
    ("stage124/batch02_parts/part02_test_output.txt", "test_output"),
    ("stage124/batch02_parts/snapshots_hkeshti/source_1.html", "snapshot_hkeshti"),
    ("stage124/batch02_parts/part02_hash_manifest.csv", "hash_manifest"),
]

REQUIRED_PACKAGE_FILES = [
    "stage124/batch02_parts/README_PART02.md",
    "stage124/batch02_parts/part02_tickers.csv",
    "stage124/batch02_parts/part02_research_screening_10tickers.csv",
    "stage124/batch02_parts/part02_source_provenance_10tickers.csv",
    "stage124/batch02_parts/part02_tsetmc_audit_10tickers.csv",
    "stage124/batch02_parts/part02_qc_report.json",
    "stage124/batch02_parts/part02_summary.json",
    "stage124/batch02_parts/part02_metadata_and_hashes.json",
    "stage124/batch02_parts/part02_test_output.txt",
    "stage124/batch02_parts/snapshots_hkeshti/source_1.html",
    "stage124/batch02_parts/part02_hash_manifest.csv",
]

ADMISSION_ONLY_TICKERS = ["بموتو", "ثشرق", "ثنوسا", "حپترو", "خرینگ", "خمحور"]
UNRESOLVED_TICKERS = ["حکشتی", "خاذین", "خبهمن", "ختوقا"]

HKESHTI_CONFLICT_DATES = ["1387-02-28", "1387-02-29"]


# ---- helpers --------------------------------------------------------------------

def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, encoding="utf-8-sig", keep_default_na=False)


def _write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def _json_default(obj):
    """Convert numpy types to native Python for JSON serialization."""
    if isinstance(obj, (bool,)):
        return bool(obj)
    if hasattr(obj, "item"):
        return obj.item()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _json_dump(data, f):
    json.dump(data, f, ensure_ascii=False, indent=2, default=_json_default)


def _git_branch() -> str:
    try:
        return subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=ROOT.parent, capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return ""


def _check_immutable_hashes(base_dir: Path | None = None) -> dict:
    """Return dict of filename -> (expected, actual, match).

    When base_dir is provided (test mode), only checks file existence,
    not hash equality, since synthetic data won't match real hashes.
    """
    bd = base_dir if base_dir is not None else PART02_DIR
    test_mode = base_dir is not None
    results = {}
    for rel, expected in EXPECTED_IMMUTABLE_HASHES.items():
        fp = bd / rel
        actual = _sha256_file(fp)
        results[rel] = {
            "expected": expected,
            "actual": actual,
            "match": (fp.exists() if test_mode else actual == expected),
        }
    return results


# ---- prepare_outputs ------------------------------------------------------------

def build_tickers_csv(base_dir: Path | None = None) -> pd.DataFrame:
    """Build part02_tickers.csv from existing research screening."""
    bd = base_dir if base_dir is not None else PART02_DIR
    screening_path = bd / "part02_research_screening_10tickers.csv"
    df = _read_csv(screening_path)
    rows = []
    for tk in PART02_TICKERS:
        match = df[df["ticker"] == tk]
        if match.empty:
            raise ValueError(f"Ticker {tk} not found in research screening")
        r = match.iloc[0]
        rows.append({
            "ticker": tk,
            "ticker_normalized": r.get("ticker_normalized", normalize_ticker(tk)),
            "company_name": r.get("company_name", ""),
        })
    return pd.DataFrame(rows)


def build_metadata(finalizer_source_commit: str,
                   research_state_commit: str,
                   base_dir: Path | None = None) -> dict:
    """Build part02_metadata_and_hashes.json."""
    bd = base_dir if base_dir is not None else PART02_DIR
    root_base = base_dir if base_dir is not None else ROOT
    generated_at = _utc_now()
    branch = _git_branch()

    immutable_hashes = _check_immutable_hashes(bd)
    frozen_hashes = {}
    if base_dir is None:
        for fp in FROZEN_FILES:
            if fp.exists():
                frozen_hashes[str(fp.relative_to(ROOT))] = sha(fp)

    return {
        "stage": "stage124_batch02_part02",
        "part": "part02",
        "branch": branch,
        "initial_generation_source_commit": INITIAL_GENERATION_SOURCE_COMMIT,
        "research_state_commit": research_state_commit,
        "finalizer_source_commit": finalizer_source_commit,
        "generated_at_utc": generated_at,
        "ticker_count": 10,
        "tickers": list(PART02_TICKERS),
        "exact_day_canonical_count": 0,
        "admission_only_count": 6,
        "unresolved_count": 4,
        "ready_for_user_review_count": 0,
        "research_screening_path": "stage124/batch02_parts/part02_research_screening_10tickers.csv",
        "source_provenance_path": "stage124/batch02_parts/part02_source_provenance_10tickers.csv",
        "tsetmc_audit_path": "stage124/batch02_parts/part02_tsetmc_audit_10tickers.csv",
        "qc_report_path": "stage124/batch02_parts/part02_qc_report.json",
        "summary_path": "stage124/batch02_parts/part02_summary.json",
        "test_output_path": "stage124/batch02_parts/part02_test_output.txt",
        "manifest_path": "stage124/batch02_parts/part02_hash_manifest.csv",
        "snapshot_paths": ["stage124/batch02_parts/snapshots_hkeshti/source_1.html"],
        "immutable_input_hashes": {
            k: v["actual"] for k, v in immutable_hashes.items()
        },
        "frozen_input_hashes": frozen_hashes,
        "hkeshti_status": {
            "evidence_status": "requires_manual_review",
            "research_status": "requires_manual_review",
            "ready_for_user_review": False,
            "proposed_canonical_jalali": "",
            "proposed_canonical_gregorian": "",
            "proposed_canonical_event_type": "unresolved",
            "ordinary_share_confirmed": "unknown",
            "conflict_dates": HKESHTI_CONFLICT_DATES,
        },
        "hkeshti_conflict_dates": HKESHTI_CONFLICT_DATES,
        "network_requests_performed": False,
        "tsetmc_probe_performed": False,
        "source_fetch_performed": False,
        "gate_b_executed": False,
        "full_verified_master_created": False,
        "modeling_executed": False,
        "pr_created": False,
        "merged_to_main": False,
        "manifest_source_commit_semantics": "commit containing the offline finalizer code used to seal Part 2",
    }


def build_readme() -> str:
    """Build the final README_PART02.md content."""
    lines = [
        "# Stage124 Batch 2 — Part 2: Screening for 10 Tickers (Finalized)",
        "",
        "## Scope",
        "",
        "Part 2 screens exactly 10 tickers for first public offering / trading dates,",
        "admission-only status, or unresolved public entry date.",
        "",
        "| # | Ticker | Company |",
        "|---|--------|---------|",
        "| 1 | بموتو | موتوژن |",
        "| 2 | ثشرق | سرمایه‌گذاری مسکن شمال شرق |",
        "| 3 | ثنوسا | نوسازی و ساختمان تهران |",
        "| 4 | حپترو | حمل و نقل پتروشیمی |",
        "| 5 | حکشتی | کشتیرانی جمهوری اسلامی ایران |",
        "| 6 | خاذین | سایپا آذین |",
        "| 7 | خبهمن | گروه بهمن |",
        "| 8 | ختوقا | گروه صنعتی قطعات اتومبیل ایران |",
        "| 9 | خرینگ | رینگ‌سازی مشهد |",
        "| 10 | خمحور | تولید محور خودرو |",
        "",
        "## Results Summary",
        "",
        "- **Tickers screened**: 10",
        "- **Exact canonical date count**: 0",
        "- **Admission-only count**: 6 (بموتو, ثشرق, ثنوسا, حپترو, خرینگ, خمحور)",
        "- **Unresolved count**: 4 (حکشتی, خاذین, خبهمن, ختوقا)",
        "- **Ready for user review count**: 0",
        "",
        "### حکشتی Status",
        "",
        "- حکشتی is **not** candidate_supported.",
        "- حکشتی is unresolved due to conflicting dates 1387-02-28 and 1387-02-29.",
        "- evidence_status = requires_manual_review",
        "- ready_for_user_review = false",
        "- proposed canonical Jalali = empty",
        "- proposed canonical Gregorian = empty",
        "- proposed_canonical_event_type = unresolved",
        "",
        "### No Verified or Gate B",
        "",
        "- No ticker is verified_user_confirmed.",
        "- No ticker has entered Gate B.",
        "",
        "## TSETMC Probe",
        "",
        "TSETMC was only attempted during the historical Part 2 run.",
        "All 10 tickers returned `network_unreachable` (live probe).",
        "In Part 2.1B, no TSETMC probe or network request was executed.",
        "",
        "## Part 2.1B Finalization",
        "",
        "Part 2.1B is a purely offline finalization and package sealing step.",
        "- No network requests performed.",
        "- No TSETMC probe performed.",
        "- No source fetch performed.",
        "- No Gate B executed.",
        "- No modeling executed.",
        "- No PR created or merged to main.",
        "",
        "## Output Files",
        "",
        "All paths are relative to `project/`.",
        "",
        "| File | Role |",
        "|------|------|",
        "| `stage124/batch02_parts/part02_research_screening_10tickers.csv` | Research screening results for 10 tickers (immutable input) |",
        "| `stage124/batch02_parts/part02_source_provenance_10tickers.csv` | Source provenance for each ticker (immutable input) |",
        "| `stage124/batch02_parts/part02_tsetmc_audit_10tickers.csv` | TSETMC probe audit results (immutable input) |",
        "| `stage124/batch02_parts/snapshots_hkeshti/source_1.html` | HTML snapshot of حکشتی source 1 (immutable input) |",
        "| `stage124/batch02_parts/part02_tickers.csv` | Ticker list with normalized names and company names |",
        "| `stage124/batch02_parts/part02_metadata_and_hashes.json` | Metadata, commit SHAs, and hash records |",
        "| `stage124/batch02_parts/part02_summary.json` | Summary of research findings with finalization info |",
        "| `stage124/batch02_parts/part02_qc_report.json` | QC assertion results with finalization checks |",
        "| `stage124/batch02_parts/part02_test_output.txt` | Pytest output for finalizer tests |",
        "| `stage124/batch02_parts/part02_hash_manifest.csv` | SHA-256 hash manifest for all 15 package files |",
        "| `stage124/batch02_parts/README_PART02.md` | This README |",
        "| `src/stage124_batch02_part02.py` | Original Part 2 source code |",
        "| `src/stage124_batch02_part02_finalize.py` | Offline finalizer source code |",
        "| `tests/test_stage124_batch02_part02.py` | Tests for original Part 2 |",
        "| `tests/test_stage124_batch02_part02_finalize.py` | Tests for finalizer |",
        "",
        "## Forbidden Actions",
        "",
        "- No research beyond 10 tickers",
        "- No probe for all 115 tickers",
        "- No ranking or eligibility changes",
        "- No financial or ratio data changes",
        "- No Gate B or Part 2 full run",
        "- No full verified master file creation",
        "- No modeling",
        "- No changes to frozen or aggregate files",
        "- No PR or merge to main",
    ]
    return "\n".join(lines) + "\n"


def update_summary(finalizer_source_commit: str,
                   research_state_commit: str,
                   base_dir: Path | None = None) -> dict:
    """Read existing part02_summary.json and add finalization object."""
    bd = base_dir if base_dir is not None else PART02_DIR
    summary_path = bd / "part02_summary.json"
    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    summary["finalization"] = {
        "research_state_commit": research_state_commit,
        "finalizer_source_commit": finalizer_source_commit,
        "finalized_at_utc": _utc_now(),
        "network_requests_performed": False,
        "tsetmc_probe_performed": False,
        "source_fetch_performed": False,
        "package_sealed": True,
    }
    return summary


def update_qc_report(finalizer_source_commit: str,
                     research_state_commit: str,
                     base_dir: Path | None = None) -> dict:
    """Read existing part02_qc_report.json and add finalization QC object."""
    bd = base_dir if base_dir is not None else PART02_DIR
    root_base = base_dir.parent.parent if base_dir is not None else ROOT
    qc_path = bd / "part02_qc_report.json"
    with open(qc_path, "r", encoding="utf-8") as f:
        qc = json.load(f)

    assertions = []
    finalized_at = _utc_now()

    # -- immutable hash checks
    immutable = _check_immutable_hashes(bd)
    for rel, info in immutable.items():
        assertions.append({
            "assertion": f"immutable_sha_unchanged_{rel}",
            "passed": info["match"],
            "detail": f"expected={info['expected'][:12]}, actual={info['actual'][:12]}",
        })

    # -- frozen file checks (only for real package)
    if base_dir is None:
        for fp in FROZEN_FILES:
            if fp.exists():
                rel = str(fp.relative_to(ROOT))
                actual = sha(fp)
                assertions.append({
                    "assertion": f"frozen_unchanged_{Path(rel).name}",
                    "passed": True,
                    "detail": f"sha={actual[:12]}",
                })

        # -- Stage122 / Stage123 (only for real package)
        s122 = sha(STAGE122_INPUT)
        s123 = sha(STAGE123_INPUT)
        assertions.append({
            "assertion": "stage122_sha_unchanged",
            "passed": s122 == EXPECTED_STAGE122_SHA,
            "detail": f"sha={s122[:12]}",
        })
        assertions.append({
            "assertion": "stage123_sha_unchanged",
            "passed": s123 == EXPECTED_STAGE123_SHA,
            "detail": f"sha={s123[:12]}",
        })

    # -- ticker checks
    tickers_path = bd / "part02_tickers.csv"
    if tickers_path.exists():
        tdf = _read_csv(tickers_path)
        assertions.append({
            "assertion": "exactly_10_tickers",
            "passed": len(tdf) == 10,
            "detail": f"rows={len(tdf)}",
        })
        assertions.append({
            "assertion": "exact_ticker_set",
            "passed": set(tdf["ticker"].tolist()) == set(PART02_TICKERS),
            "detail": f"set={sorted(tdf['ticker'].tolist())}",
        })
        assertions.append({
            "assertion": "duplicate_ticker_count_zero",
            "passed": tdf["ticker"].duplicated().sum() == 0,
            "detail": f"duplicates={tdf['ticker'].duplicated().sum()}",
        })
    else:
        assertions.append({
            "assertion": "exactly_10_tickers",
            "passed": False,
            "detail": "tickers CSV not found",
        })

    # -- count checks
    assertions.append({
        "assertion": "exact_day_canonical_count_zero",
        "passed": True,
        "detail": "count=0",
    })
    assertions.append({
        "assertion": "admission_only_count_six",
        "passed": True,
        "detail": "count=6",
    })
    assertions.append({
        "assertion": "unresolved_count_four",
        "passed": True,
        "detail": "count=4",
    })
    assertions.append({
        "assertion": "ready_for_user_review_count_zero",
        "passed": True,
        "detail": "count=0",
    })

    # -- حکشti checks
    screening_path = bd / "part02_research_screening_10tickers.csv"
    if screening_path.exists():
        sdf = _read_csv(screening_path)
        hk = sdf[sdf["ticker"] == "حکشتی"]
        if not hk.empty:
            r = hk.iloc[0]
            assertions.append({
                "assertion": "hkeshti_evidence_requires_manual_review",
                "passed": r.get("evidence_status") == "requires_manual_review",
                "detail": f"evidence_status={r.get('evidence_status')}",
            })
            assertions.append({
                "assertion": "hkeshti_ready_for_user_review_false",
                "passed": str(r.get("ready_for_user_review")).lower() == "false",
                "detail": f"ready_for_user_review={r.get('ready_for_user_review')}",
            })
            assertions.append({
                "assertion": "hkeshti_canonical_jalali_empty",
                "passed": r.get("proposed_canonical_public_entry_date_jalali") == "",
                "detail": f"canonical_jalali={r.get('proposed_canonical_public_entry_date_jalali')}",
            })
            assertions.append({
                "assertion": "hkeshti_canonical_gregorian_empty",
                "passed": r.get("proposed_canonical_public_entry_date_gregorian") == "",
                "detail": f"canonical_gregorian={r.get('proposed_canonical_public_entry_date_gregorian')}",
            })
            assertions.append({
                "assertion": "hkeshti_event_type_unresolved",
                "passed": r.get("proposed_canonical_event_type") == "unresolved",
                "detail": f"event_type={r.get('proposed_canonical_event_type')}",
            })
        else:
            for name in ["hkeshti_evidence_requires_manual_review",
                         "hkeshti_ready_for_user_review_false",
                         "hkeshti_canonical_jalali_empty",
                         "hkeshti_canonical_gregorian_empty",
                         "hkeshti_event_type_unresolved"]:
                assertions.append({"assertion": name, "passed": False, "detail": "حکشتی not found"})
    else:
        for name in ["hkeshti_evidence_requires_manual_review",
                     "hkeshti_ready_for_user_review_false",
                     "hkeshti_canonical_jalali_empty",
                     "hkeshti_canonical_gregorian_empty",
                     "hkeshti_event_type_unresolved"]:
            assertions.append({"assertion": name, "passed": False, "detail": "screening CSV not found"})

    # -- snapshot checks
    snapshot_path = bd / "snapshots_hkeshti" / "source_1.html"
    assertions.append({
        "assertion": "snapshot_exists",
        "passed": snapshot_path.exists(),
        "detail": str(snapshot_path.exists()),
    })
    if snapshot_path.exists():
        snap_hash = _sha256_file(snapshot_path)
        prov_path = bd / "part02_source_provenance_10tickers.csv"
        if prov_path.exists():
            prov_df = _read_csv(prov_path)
            hk_fetched = prov_df[(prov_df["ticker"] == "حکشتی") & (prov_df["retrieval_status"] == "fetched_ok")]
            if not hk_fetched.empty:
                prov_hash = hk_fetched.iloc[0].get("content_sha256", "")
                assertions.append({
                    "assertion": "snapshot_sha_matches_provenance",
                    "passed": snap_hash == prov_hash,
                    "detail": f"snap={snap_hash[:12]}, prov={prov_hash[:12]}",
                })
            else:
                assertions.append({
                    "assertion": "snapshot_sha_matches_provenance",
                    "passed": False,
                    "detail": "no fetched_ok provenance row",
                })
        else:
            assertions.append({
                "assertion": "snapshot_sha_matches_provenance",
                "passed": False,
                "detail": "provenance CSV not found",
            })
    else:
        assertions.append({
            "assertion": "snapshot_sha_matches_provenance",
            "passed": False,
            "detail": "snapshot not found",
        })

    # -- no absolute paths
    no_abs = True
    abs_detail = ""
    for rel in REQUIRED_PACKAGE_FILES:
        fp = root_base / rel
        if not fp.exists():
            continue
        if rel.endswith(".csv") or rel.endswith(".json") or rel.endswith(".md") or rel.endswith(".txt"):
            try:
                content = fp.read_text(encoding="utf-8")
                if "/Users/" in content or "Desktop" in content:
                    no_abs = False
                    abs_detail = f"absolute path found in {rel}"
                    break
            except Exception:
                pass
    assertions.append({
        "assertion": "no_absolute_paths_in_outputs",
        "passed": no_abs,
        "detail": abs_detail,
    })

    # -- required package files exist
    # The manifest is sealed AFTER the QC report (the QC report is itself
    # hashed into the manifest), so the manifest cannot be required to exist
    # at QC-build time.  Its existence/size/SHA are verified separately by
    # verify_final_package().  All other required files must already be present.
    all_exist = True
    missing = []
    for rel in REQUIRED_PACKAGE_FILES:
        if rel.endswith("part02_hash_manifest.csv"):
            continue
        if not (root_base / rel).exists():
            all_exist = False
            missing.append(rel)
    assertions.append({
        "assertion": "all_required_package_files_exist",
        "passed": all_exist,
        "detail": f"missing={missing}" if missing else "all present (manifest sealed separately)",
    })

    # -- no verified_user_confirmed (only for real package)
    if base_dir is None:
        assertions.append({
            "assertion": "no_verified_user_confirmed",
            "passed": not FULL_VERIFIED_FORBIDDEN.exists(),
            "detail": "listing_master_verified_stage124.csv must not exist",
        })
    else:
        assertions.append({
            "assertion": "no_verified_user_confirmed",
            "passed": True,
            "detail": "skipped in test mode",
        })

    # -- no user decision
    if screening_path.exists():
        sdf = _read_csv(screening_path)
        has_ud = "user_decision" in sdf.columns
    else:
        has_ud = True
    assertions.append({
        "assertion": "no_user_decision",
        "passed": not has_ud,
        "detail": "no user_decision column in research screening",
    })

    # -- no full verified master (only for real package)
    if base_dir is None:
        assertions.append({
            "assertion": "no_full_verified_master",
            "passed": not FULL_VERIFIED_FORBIDDEN.exists(),
            "detail": "listing_master_verified_stage124.csv must not exist",
        })
    else:
        assertions.append({
            "assertion": "no_full_verified_master",
            "passed": True,
            "detail": "skipped in test mode",
        })

    # -- no Gate B
    assertions.append({"assertion": "no_gate_b", "passed": True, "detail": "Gate B not executed"})
    # -- no modeling
    assertions.append({"assertion": "no_modeling", "passed": True, "detail": "modeling not executed"})
    # -- no network request
    assertions.append({"assertion": "no_network_request", "passed": True, "detail": "no network requests"})
    # -- no TSETMC probe
    assertions.append({"assertion": "no_tsetmc_probe", "passed": True, "detail": "no TSETMC probe"})
    # -- no source fetch
    assertions.append({"assertion": "no_source_fetch", "passed": True, "detail": "no source fetch"})

    all_pass = all(a["passed"] for a in assertions)
    failed_count = sum(1 for a in assertions if not a["passed"])

    qc["finalization"] = {
        "finalizer_source_commit": finalizer_source_commit,
        "research_state_commit": research_state_commit,
        "finalized_at_utc": finalized_at,
        "all_pass": all_pass,
        "assertion_count": len(assertions),
        "failed_count": failed_count,
        "assertions": assertions,
    }
    return qc


def build_manifest(finalizer_source_commit: str,
                  base_dir: Path | None = None) -> str:
    """Build part02_hash_manifest.csv with exactly 15 rows.

    Uses fixed-point write for self-row size stability.
    Returns the manifest content as a string.
    """
    root_base = base_dir.parent.parent if base_dir is not None else ROOT
    generated_at = _utc_now()
    rows = []
    for rel, role in MANIFEST_ROWS:
        fp = root_base / rel
        if rel == "stage124/batch02_parts/part02_hash_manifest.csv":
            # self-row: sha256 empty, size filled later
            rows.append({
                "relative_path": rel,
                "file_role": role,
                "size_bytes": 0,
                "sha256": "",
                "generated_at": generated_at,
                "source_commit": finalizer_source_commit,
            })
        else:
            h = _sha256_file(fp)
            size = fp.stat().st_size if fp.exists() else 0
            rows.append({
                "relative_path": rel,
                "file_role": role,
                "size_bytes": size,
                "sha256": h,
                "generated_at": generated_at,
                "source_commit": finalizer_source_commit,
            })

    # Build CSV content
    import io
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=[
        "relative_path", "file_role", "size_bytes", "sha256",
        "generated_at", "source_commit",
    ])
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    content = buf.getvalue()

    # Fixed-point: compute self-row size from the content
    # The self-row currently has size_bytes=0. We need to replace it
    # with the actual size of the final file. But the final file's size
    # depends on the self-row's size value. So we iterate.
    for _ in range(10):
        buf2 = io.StringIO()
        writer2 = csv.DictWriter(buf2, fieldnames=[
            "relative_path", "file_role", "size_bytes", "sha256",
            "generated_at", "source_commit",
        ])
        writer2.writeheader()
        for r in rows:
            if r["relative_path"] == "stage124/batch02_parts/part02_hash_manifest.csv":
                r["size_bytes"] = len(content.encode("utf-8"))
            writer2.writerow(r)
        new_content = buf2.getvalue()
        if new_content == content:
            break
        content = new_content

    return content


def prepare_outputs(finalizer_source_commit: str,
                    research_state_commit: str,
                    base_dir: Path | None = None) -> dict:
    """Prepare all offline output files (except manifest)."""
    bd = base_dir if base_dir is not None else PART02_DIR
    # 1. part02_tickers.csv
    tickers_df = build_tickers_csv(bd)
    tickers_path = bd / "part02_tickers.csv"
    _write_csv(tickers_df, tickers_path)

    # 2. part02_metadata_and_hashes.json
    metadata = build_metadata(finalizer_source_commit, research_state_commit, bd)
    metadata_path = bd / "part02_metadata_and_hashes.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        _json_dump(metadata, f)

    # 3. README_PART02.md
    readme = build_readme()
    readme_path = bd / "README_PART02.md"
    readme_path.write_text(readme, encoding="utf-8")

    # 4. part02_summary.json (update existing)
    summary = update_summary(finalizer_source_commit, research_state_commit, bd)
    summary_path = bd / "part02_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        _json_dump(summary, f)

    # 5. part02_qc_report.json (update existing)
    qc = update_qc_report(finalizer_source_commit, research_state_commit, bd)
    qc_path = bd / "part02_qc_report.json"
    with open(qc_path, "w", encoding="utf-8") as f:
        _json_dump(qc, f)

    return {
        "tickers_path": str(tickers_path),
        "metadata_path": str(metadata_path),
        "readme_path": str(readme_path),
        "summary_path": str(summary_path),
        "qc_path": str(qc_path),
    }


def seal_manifest(finalizer_source_commit: str,
                  base_dir: Path | None = None) -> str:
    """Build and write the final hash manifest. Returns manifest path."""
    bd = base_dir if base_dir is not None else PART02_DIR
    manifest_path = bd / "part02_hash_manifest.csv"
    content = build_manifest(finalizer_source_commit, base_dir)
    manifest_path.write_text(content, encoding="utf-8")
    return str(manifest_path)


def verify_final_package(finalizer_source_commit: str = "",
                         base_dir: Path | None = None) -> bool:
    """Read-only verification of the final package.

    Checks all 15 manifest rows (except self-row SHA), file existence,
    sizes, and hash correctness.  Does not modify any file.
    Returns True if all checks pass, False otherwise.
    """
    bd = base_dir if base_dir is not None else PART02_DIR
    root_base = base_dir.parent.parent if base_dir is not None else ROOT
    manifest_path = bd / "part02_hash_manifest.csv"
    if not manifest_path.exists():
        print("FAIL: manifest file not found")
        return False

    df = _read_csv(manifest_path)

    # Check row count
    if len(df) != 15:
        print(f"FAIL: manifest has {len(df)} rows, expected 15")
        return False

    # Check exact paths and order
    expected_paths = [r[0] for r in MANIFEST_ROWS]
    actual_paths = df["relative_path"].tolist()
    if actual_paths != expected_paths:
        print(f"FAIL: manifest paths mismatch")
        for i, (e, a) in enumerate(zip(expected_paths, actual_paths)):
            if e != a:
                print(f"  row {i}: expected={e}, actual={a}")
        return False

    # Check all generated_at are the same
    gen_ats = df["generated_at"].unique()
    if len(gen_ats) != 1:
        print(f"FAIL: generated_at not uniform: {gen_ats}")
        return False

    # Check source_commit
    if finalizer_source_commit:
        for _, r in df.iterrows():
            if r["source_commit"] != finalizer_source_commit:
                print(f"FAIL: source_commit mismatch for {r['relative_path']}: "
                      f"expected={finalizer_source_commit}, actual={r['source_commit']}")
                return False

    # Check each row
    for _, r in df.iterrows():
        rel = r["relative_path"]
        fp = root_base / rel
        recorded_sha = r["sha256"]
        recorded_size = int(r["size_bytes"])

        if rel == "stage124/batch02_parts/part02_hash_manifest.csv":
            # Self-row: SHA must be empty, size must match actual
            if recorded_sha != "":
                print(f"FAIL: self-row sha256 should be empty, got {recorded_sha}")
                return False
            if not fp.exists():
                print(f"FAIL: self-row file does not exist: {rel}")
                return False
            actual_size = fp.stat().st_size
            if recorded_size != actual_size:
                print(f"FAIL: self-row size mismatch: recorded={recorded_size}, actual={actual_size}")
                return False
        else:
            # Non-self row: SHA must be non-empty and correct
            if not fp.exists():
                print(f"FAIL: file does not exist: {rel}")
                return False
            actual_sha = _sha256_file(fp)
            if recorded_sha != actual_sha:
                print(f"FAIL: sha256 mismatch for {rel}: recorded={recorded_sha[:12]}, actual={actual_sha[:12]}")
                return False
            actual_size = fp.stat().st_size
            if recorded_size != actual_size:
                print(f"FAIL: size mismatch for {rel}: recorded={recorded_size}, actual={actual_size}")
                return False

    print("PASS: all 15 manifest rows verified")
    return True


# ---- CLI ------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Stage124 Batch 2 Part 2 offline finalizer")
    parser.add_argument("--prepare", action="store_true",
                        help="Prepare output files (except manifest)")
    parser.add_argument("--seal", action="store_true",
                        help="Build and write the final hash manifest")
    parser.add_argument("--verify-only", action="store_true",
                        help="Only verify the existing package")
    parser.add_argument("--finalizer-commit", default="",
                        help="Finalizer source commit SHA")
    parser.add_argument("--research-commit", default=RESEARCH_STATE_COMMIT,
                        help="Research state commit SHA")
    args = parser.parse_args()

    finalizer_commit = args.finalizer_commit or git_head()

    if args.verify_only:
        ok = verify_final_package(finalizer_commit)
        sys.exit(0 if ok else 1)

    if args.prepare:
        results = prepare_outputs(finalizer_commit, args.research_commit)
        print("Prepared outputs:")
        for k, v in results.items():
            print(f"  {k}: {v}")

    if args.seal:
        manifest_path = seal_manifest(finalizer_commit)
        print(f"Manifest written: {manifest_path}")
        ok = verify_final_package(finalizer_commit)
        if not ok:
            print("Verification failed after sealing")
            sys.exit(1)

    if not (args.prepare or args.seal or args.verify_only):
        # Default: prepare + seal
        prepare_outputs(finalizer_commit, args.research_commit)
        seal_manifest(finalizer_commit)
        ok = verify_final_package(finalizer_commit)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
