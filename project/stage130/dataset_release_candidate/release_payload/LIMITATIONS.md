# Limitations

What these files can and cannot support. Read this before drawing a conclusion.

Every number below is read from the committed project records shipped in
`documentation/`. Nothing was recomputed for this release.

---

## 1. The availability date is a proxy, not an observation

Predictor admission uses a **fixed four-Jalali-month regulatory lag**. A fiscal
year *t* statement is treated as available four Jalali months after the fiscal
year end, and the field is called `assumed_available_at_regulatory`.

* Row-level publication timestamps were **never collected** for this panel.
* **No individual company-year's actual filing date was verified.**
* The contract records `is_observed_publication_timestamp = false`.

Consequence: the panel is **not fully point-in-time verified**. The
leakage-safe construction is only as good as the four-month assumption. Any
statement about real-time or operational behaviour derived from these files is
a statement about the proxy, not about observed filing behaviour.

## 2. Provenance is file-level and incomplete

* A source file is recorded for **1,303 of 1,331** upstream panel rows.
* It is **absent for 28** rows — a documented provenance gap.
* `source_url` is populated for only a small minority of rows (7 of 1,012 on
  the primary surface).

Provenance here is file-level. There is no complete row-level provenance
record, and this release does not claim one. The 28 rows were not imputed, not
reclassified, and not hidden.

## 3. Quality-control coverage differs across checks

The checks were not evaluable on the same rows, and the counts are not
interchangeable:

| Check | Rows evaluable (of 1,331) | Mismatches |
|---|---|---|
| Balance-sheet identity | 1,312 | 0 (1,311 exact, 1 within a recorded 1-million-IRR rounding tolerance) |
| Leverage ratio | 1,312 | 0 |
| Current ratio | 1,312 | 0 |
| Equity ratio | 1,312 | 0 |
| ROA (period-adjusted) | 1,312 | 0 |
| Asset turnover (period-adjusted) | 1,312 | 0 |
| Financial expense to assets | 1,311 | 0 |
| Operating cash flow to assets | 1,273 | 0 |

Zero failures **among evaluable rows** is not a statement about the rows that
could not be evaluated. Reconciliation is arithmetic agreement between stored
components, not a re-audit against the original filing.

## 3a. Column documentation is uneven

`part3c_column_role_map_stage125.csv` covers all 115 released columns and is
authoritative for what each column is. The prose data dictionary does not:
`data_dictionary_stage125.csv` holds 38 entries, of which **25** correspond to
released columns, leaving **90** released columns with a role but no dictionary
description. Thirteen dictionary entries describe candidate variables that were
never materialized, or upstream keys renamed when the pair surface was built.

Both artifacts are shipped as committed. Neither was edited for this release,
and the shortfall is published in `release_manifest.json` under
`column_documentation_coverage` rather than papered over.

## 4. The outcome is an operational composite, not a legal event

`FD_target_main` is a composite operational distress indicator built from
accumulated loss relative to capital, negative equity, and negative operating
cash flow combined with high leverage. It is **not** an Article-141 legal
insolvency determination, and it is not a bankruptcy filing.

Direct Article-141 evidence was **unavailable for every row** — no controlled
source existed — so that criterion is missing throughout and the composite does
not rest on it. `target_definition_stage122.csv` gives the exact rules.

The outcome uses **three-valued logic**. A firm-year whose evidence did not
permit a determination is recorded as *unknown* (28 rows) and is **never
converted to a healthy zero**. Preserving unknowns is the honest choice, and it
reduces the analysable sample.

## 5. Class imbalance, and where it bites

The primary surface has **80 positives against 932 negatives** — roughly 7.9%.
The positive class is sparse and gets sparser in later years: the primary
design records 3 positives in target year 1402 and 4 in 1399 and 1400.

Any per-year or subgroup analysis on this panel runs into very small event
counts. Treat interval estimates accordingly.

## 6. The audit surfaces are not model-ready

`audit/audited_pairs_*.csv` retain pairs that the leakage-safe timing rule
excludes. Fitting on them reintroduces look-ahead. See `README.md`.

## 7. Scope and generalisation

* Iranian listed companies on the Tehran Stock Exchange only.
* Non-financial companies only — financial-industry firms are excluded by
  design (43 rows excluded on that ground).
* Jalali fiscal years 1392–1402. No Gregorian span is claimed for the sample.
* Consolidated or unresolved-scope statements are excluded (95 rows), as are
  pre-listing rows (19) and non-12-month periods (6).

Eligibility is recorded per dimension and the counts are **not additive** — a
row may fail more than one rule.

## 8. Monetary units and inflation

Values are in the units recorded in the `unit` column and the data dictionary.
The study period covers years of high inflation in Iran. No deflation, currency
conversion or purchasing-power adjustment has been applied to the released
values. Cross-year comparison of nominal levels is the reuser's responsibility.

## 9. What this dataset does not establish

* It is **not** a benchmark with a published leaderboard.
* It carries **no model, no prediction, no score and no held-out evaluation
  output** — none is included in this release.
* It establishes **no deployment readiness and no decision utility**. The
  authors make no recommendation for investment, credit or supervisory use.

## 10. Redistribution status

The upstream redistribution question is **unresolved**, and this candidate is
marked `NOT_READY_FOR_PUBLICATION` for that reason. See
`SOURCE_AND_LICENSE_NOTES.md`.
