# Stage124 Batch 2 — Part 2: Screening for 10 Tickers (Finalized)

## Scope

Part 2 screens exactly 10 tickers for first public offering / trading dates,
admission-only status, or unresolved public entry date.

| # | Ticker | Company |
|---|--------|---------|
| 1 | بموتو | موتوژن |
| 2 | ثشرق | سرمایه‌گذاری مسکن شمال شرق |
| 3 | ثنوسا | نوسازی و ساختمان تهران |
| 4 | حپترو | حمل و نقل پتروشیمی |
| 5 | حکشتی | کشتیرانی جمهوری اسلامی ایران |
| 6 | خاذین | سایپا آذین |
| 7 | خبهمن | گروه بهمن |
| 8 | ختوقا | گروه صنعتی قطعات اتومبیل ایران |
| 9 | خرینگ | رینگ‌سازی مشهد |
| 10 | خمحور | تولید محور خودرو |

## Results Summary

- **Tickers screened**: 10
- **Exact canonical date count**: 0
- **Admission-only count**: 6 (بموتو, ثشرق, ثنوسا, حپترو, خرینگ, خمحور)
- **Unresolved count**: 4 (حکشتی, خاذین, خبهمن, ختوقا)
- **Ready for user review count**: 0

### حکشتی Status

- حکشتی is **not** candidate_supported.
- حکشتی is unresolved due to conflicting dates 1387-02-28 and 1387-02-29.
- evidence_status = requires_manual_review
- ready_for_user_review = false
- proposed canonical Jalali = empty
- proposed canonical Gregorian = empty
- proposed_canonical_event_type = unresolved

### No Verified or Gate B

- No ticker is verified_user_confirmed.
- No ticker has entered Gate B.

## TSETMC Probe

TSETMC was only attempted during the historical Part 2 run.
All 10 tickers returned `network_unreachable` (live probe).
In Part 2.1B, no TSETMC probe or network request was executed.

## Part 2.1B Finalization

Part 2.1B is a purely offline finalization and package sealing step.
- No network requests performed.
- No TSETMC probe performed.
- No source fetch performed.
- No Gate B executed.
- No modeling executed.
- No PR created or merged to main.

## Output Files

All paths are relative to `project/`.

| File | Role |
|------|------|
| `stage124/batch02_parts/part02_research_screening_10tickers.csv` | Research screening results for 10 tickers (immutable input) |
| `stage124/batch02_parts/part02_source_provenance_10tickers.csv` | Source provenance for each ticker (immutable input) |
| `stage124/batch02_parts/part02_tsetmc_audit_10tickers.csv` | TSETMC probe audit results (immutable input) |
| `stage124/batch02_parts/snapshots_hkeshti/source_1.html` | HTML snapshot of حکشتی source 1 (immutable input) |
| `stage124/batch02_parts/part02_tickers.csv` | Ticker list with normalized names and company names |
| `stage124/batch02_parts/part02_metadata_and_hashes.json` | Metadata, commit SHAs, and hash records |
| `stage124/batch02_parts/part02_summary.json` | Summary of research findings with finalization info |
| `stage124/batch02_parts/part02_qc_report.json` | QC assertion results with finalization checks |
| `stage124/batch02_parts/part02_test_output.txt` | Pytest output for finalizer tests |
| `stage124/batch02_parts/part02_hash_manifest.csv` | SHA-256 hash manifest for all 15 package files |
| `stage124/batch02_parts/README_PART02.md` | This README |
| `src/stage124_batch02_part02.py` | Original Part 2 source code |
| `src/stage124_batch02_part02_finalize.py` | Offline finalizer source code |
| `tests/test_stage124_batch02_part02.py` | Tests for original Part 2 |
| `tests/test_stage124_batch02_part02_finalize.py` | Tests for finalizer |

## Forbidden Actions

- No research beyond 10 tickers
- No probe for all 115 tickers
- No ranking or eligibility changes
- No financial or ratio data changes
- No Gate B or Part 2 full run
- No full verified master file creation
- No modeling
- No changes to frozen or aggregate files
- No PR or merge to main
