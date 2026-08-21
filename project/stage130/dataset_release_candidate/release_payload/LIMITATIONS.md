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

## 3a. Column documentation — complete, but assembled from three sources

`RELEASE_COLUMN_DICTIONARY.csv` documents **all 115 released columns**, one row
each, and is the file to read when you want to know what a column is. It was
built for this release by transcribing facts out of the committed project
record; the `definition_status` column on every row says which kind of source
the facts came from, and `authoritative_source_path` names the exact file.

Two things follow, and neither is hidden:

* **It is a documentation join, not a new measurement.** No value was
  recomputed, no row was read, and nothing was inferred to fill a gap. Where a
  formula appears, it is the formula the committed dictionary or the frozen
  generator records — not a formula re-derived from the data.
* **The two historical artifacts still ship, unedited.**
  `part3c_column_role_map_stage125.csv` remains the authoritative column set and
  role contract, and the release dictionary is gated to match it exactly.
  `data_dictionary_stage125.csv` is the Part 1 dictionary over the *upstream*
  panel: it holds 38 entries, of which **25** correspond to released columns and
  13 describe candidate variables that were never materialized or upstream keys
  renamed when the pair surface was built. That is a fact about a committed
  historical artifact, not a gap in this release's documentation, and it is
  published in `release_manifest.json` under `upstream_dictionary_coverage`.

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

## 10. The source-rights basis is a human author determination

This candidate's rights position rests on a determination the **human author**
supplied: that the source data used in the study were publicly and freely
accessible, and that no separate provider permission is required to
redistribute the researcher-compiled panel and the author-derived variables.

That is a determination by the author. It is **not**:

* a provider licence;
* an independent verification of CODAL's, TSETMC's or anyone's published terms;
* a legal opinion.

**No CODAL or TSETMC terms page was ever retrieved or read** in the course of
preparing this release. That historical fact is recorded in full in
`SOURCE_AND_LICENSE_NOTES.md` and has not been reclassified. A reuser who needs
certainty about the underlying provider materials should consult the provider
directly; a reuser who needs the original filings must obtain them from the
provider, because this release does not carry them.

The candidate's status is `READY_FOR_EXACT_DIGEST_HUMAN_REVIEW` — a human is
being asked to read its exact digest and decide. Nothing is published, no
deposition exists and no DOI has been reserved.
