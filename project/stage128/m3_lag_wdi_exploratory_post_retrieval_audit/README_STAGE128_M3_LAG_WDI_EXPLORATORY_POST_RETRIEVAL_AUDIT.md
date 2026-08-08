# Stage128 — Track B step C: M3-LAG-WDI POST-RETRIEVAL AUDIT

**Action:** `stage128-m3-lag-wdi-exploratory-post-retrieval-audit`
**Authorized scope:** `post_retrieval_audit_only`
**Result:** `PASS_WITH_MATERIAL_FINDINGS`

## What this action is

The first and only authorized decode of the payloads acquired by step B. It
asks what the retained evidence actually contains and whether it matches the
locked contract. **It is not the Data Gate**: no coverage threshold was
applied, no company row was touched and nothing was admitted.

Identity was proven on the raw bytes **before** decoding: byte count and
SHA-256 were re-verified against the committed retrieval manifest, which is
anchored to the immutable Zenodo record `10.5281/zenodo.21844636`.

| Indicator | Obs | Year span | Numeric | Null | WDI lastupdated |
| --- | --- | --- | --- | --- | --- |
| `FP.CPI.TOTL.ZG` | 66 | 1960–2025 | 66 | 0 | `2026-07-13` |
| `PA.NUS.FCRF` | 66 | 1960–2025 | 64 | 2 | `2026-07-13` |

## What the evidence supports

| Feature | Constructible predictor years | First | Last |
| --- | --- | --- | --- |
| `intl_cpi_inflation_lag1_wdi` | 66 | 1961 | 2026 |
| `intl_fx_change_official_lag1_wdi` | 63 | 1962 | 2024 |

The contract requires **both** features complete on the same row, so the
series-level ceiling is
**1962–2024**
(63 predictor years),
bound by `PA.NUS.FCRF`.

These are SERIES-level statements. Translating them into per-row coverage,
comparing them to the inherited thresholds and deciding admission is the Data
Gate — step D, unauthorized and unexecuted.

## Findings

- the most recent observation years carry no value: [2024, 2025]

## Material limitations recorded

- PA.NUS.FCRF carries no value for its most recent observation years [2024, 2025], which caps the predictor years the FX feature can cover at 2024
- the official exchange rate is repeated unchanged across the most recent usable years, so the contract-locked log-ratio transform is defined but identically ZERO for predictor years [2021, 2022, 2023, 2024] — i.e. the LAST 4 usable predictor years carry a complete but information-free FX feature (zero-change years overall: [1962, 1963, 1964, 1965, 1966, 1967, 1968, 1969, 1970, 1971, 1980, 2021, 2022, 2023, 2024])
- the WDI vintage is a revision marker (`lastupdated 2026-07-13`), not evidence of what was published at any past moment; no point-in-time or historical-vintage availability is established

## Where this action stopped

Coverage computed: `False` · admission
decision: `False` · company rows touched:
`0`.

A completed step C authorizes nothing. The Data Gate
(`stage128-m3-lag-wdi-exploratory-data-gate`) is a separate action and remains
`authorized = False`.
