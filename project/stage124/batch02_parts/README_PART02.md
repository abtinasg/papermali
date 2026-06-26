# Stage124 Batch 2 — Part 2: Screening for 10 Tickers

## Scope

Part 2 screens exactly 10 tickers for first public offering / trading dates,
admission-only status, or unresolved public entry date:

| # | Ticker | Company |
|---|--------|---------|
| 1 | بموتو | موتوژن |
| 2 | ثشرق | سرمایه‌گذاری مسکن شمال شرق |
| 3 | ثنوسا | نوسازی و ساختمان تهران |
| 4 | حپترو | مهندسی حمل و نقل پتروشیمی |
| 5 | حکشتی | کشتیرانی جمهوری اسلامی ایران |
| 6 | خاذین | سایپا آذین |
| 7 | خبهمن | گروه بهمن |
| 8 | ختوقا | گروه صنعتی قطعات اتومبیل ایران |
| 9 | خرینگ | رینگ‌سازی مشهد |
| 10 | خمحور | تولید محور خودرو |

## Results Summary

| Ticker | Evidence Status | Canonical Date | Event Type | Ready for Review |
|--------|----------------|----------------|------------|-----------------|
| بموتو | requires_first_public_trade_evidence | — | — | false |
| ثشرق | requires_first_public_trade_evidence | — | — | false |
| ثنوسا | requires_first_public_trade_evidence | — | — | false |
| حپترو | requires_first_public_trade_evidence | — | — | false |
| حکشتی | candidate_supported | 1387-02-28 | first_public_offering | true |
| خاذین | requires_manual_review | — | — | false |
| خبهمن | requires_manual_review | — | — | false |
| ختوقا | requires_manual_review | — | — | false |
| خرینگ | requires_first_public_trade_evidence | — | — | false |
| خمحور | requires_first_public_trade_evidence | — | — | false |

- **Exact-day canonical dates found**: 1 (حکشتی: 1387-02-28)
- **Admission-only tickers**: 6 (بموتو, ثشرق, ثنوسا, حپترو, خرینگ, خمحور)
- **Unresolved tickers**: 3 (خاذین, خبهمن, ختوقا)
- **Ready for user review**: 1 (حکشتی)

## TSETMC Probe

All 10 tickers were probed via TSETMC API (timeout=5s, retry=0).
All returned `network_unreachable` (live probe). No prior probe records
existed in the feasibility CSV for these tickers.

## Output Files

| File | Description |
|------|-------------|
| `part02_research_screening_10tickers.csv` | Screening results for 10 tickers |
| `part02_source_provenance_10tickers.csv` | Source provenance for each ticker |
| `part02_tsetmc_audit_10tickers.csv` | TSETMC probe audit results |
| `part02_hash_manifest.csv` | SHA-256 manifest for Part 2 files |
| `part02_qc_report.json` | QC assertion results |
| `part02_summary.json` | Summary of findings |

## Forbidden Actions

- No research beyond 10 tickers
- No probe for all 115 tickers
- No ranking or eligibility changes
- No financial or ratio data changes
- No Gate B or Part 2 full run
- No full verified master file creation
- No modeling
- No changes to frozen or aggregate files
