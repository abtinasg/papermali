# Tehran Stock Exchange Corporate Financial Distress Prediction Dataset (1392–1402)

**Analysis-Ready Company-Year Panel and Reproducibility Materials**

---

## Status: RELEASE CANDIDATE 1.0.0-rc.2 — NOT PUBLISHED

This bundle is a **release candidate**. It has not been deposited anywhere.

| | |
|---|---|
| Release version | **1.0.0-rc.2** (supersedes 1.0.0-rc.1) |
| Zenodo deposition created | **no** |
| Files uploaded to Zenodo | **no** |
| DOI reserved | **no** |
| DOI published | **no** |
| Public release authorized | **no** |
| Publication readiness | **READY_FOR_EXACT_DIGEST_HUMAN_REVIEW** |

`READY_FOR_EXACT_DIGEST_HUMAN_REVIEW` means exactly one thing: a human is being
asked to read this archive's exact SHA-256 and decide. It is **not**
publication, **not** a public-release authorization, and it authorizes no
Zenodo action.

There is no DOI anywhere in this bundle — not even a placeholder — because a
placeholder that looks like a DOI is the kind of thing that ends up cited.

### What changed from 1.0.0-rc.1

`1.0.0-rc.1` was marked `NOT_READY_FOR_PUBLICATION` over an unresolved
redistribution question. Two things changed:

1. The **human author supplied a source-rights determination**: the data used
   in this study were publicly and freely accessible, and no separate provider
   permission is required to redistribute the researcher-compiled panel and the
   author-derived variables. That is a determination **by the author** — nobody
   verified any provider's published terms, then or since, and
   `SOURCE_AND_LICENSE_NOTES.md` still records in full which pages could not be
   retrieved.
2. The **column documentation was completed**: `RELEASE_COLUMN_DICTIONARY.csv`
   now documents **all 115 released columns**, one row each, where the previous
   candidate shipped prose covering 25 of them.

`1.0.0-rc.1` is superseded, not deleted. Its digest is recorded in
`release_manifest.json` under `supersedes`, and nothing was ever deposited
under it.

## What this is

A company-year panel of Iranian listed non-financial companies, built to
predict corporate financial distress one year ahead. Fiscal years 1392–1402
(Jalali). Every value was compiled by the authors from publicly accessible
sources; nothing here was purchased, and the panel contains no personal or
human-participant data.

The unit of observation is a **company-year pair**: the predictor row is fiscal
year *t*, the outcome is measured at *t+1*.

## Which file to use

**`data/analysis_ready_main_rule_a_stage125.csv` is the primary modeling
surface.** If you are reproducing the study or running your own model, this is
the file.

Its size is fixed by the frozen project contract:

| | |
|---|---|
| Company-year pairs | 1,012 |
| Companies | 119 |
| Columns | 115 |
| Positive (distressed) | 80 |
| Negative | 932 |

These counts are read from the committed contract
(`documentation/part3c_leakage_safe_dataset_contract_stage125.json`,
`expected_sample_counts.main_rule_a_primary`). They are not recomputed here.

## The four analysis-ready surfaces

| File | Role |
|---|---|
| `data/analysis_ready_main_rule_a_stage125.csv` | **PRIMARY** modeling surface |
| `data/analysis_ready_main_rule_b_stage125.csv` | Prespecified robustness — listing rule |
| `data/analysis_ready_expanded_rule_a_stage125.csv` | Prespecified robustness — company scope |
| `data/analysis_ready_expanded_rule_b_stage125.csv` | Prespecified robustness — combined |

The three robustness surfaces were **prespecified**, not selected after seeing
results. They exist so a reader can check that a finding does not depend on one
sample-construction choice. They are not alternative headline datasets, and a
result quoted from one of them is a robustness result, not the main result.

## The four audit surfaces — read this before using them

`audit/audited_pairs_*.csv` are **audit surfaces, and they are not all
model-ready.**

Each audited file is a superset of its analysis-ready counterpart: it retains
company-year pairs that the leakage-safe timing rule **excludes** from
modeling. For the primary design that is 1,013 audited pairs against 1,012
analysis-ready pairs, and 81 audited positives against 80 analysis-ready
positives — one pair whose predictor would not have been available in time.

They are included so the exclusions stay visible and checkable rather than
being quietly dropped. Fitting a model on an `audited_pairs_*` file
reintroduces the look-ahead the analysis-ready files were built to remove.

## The availability date is an assumption, not an observation

This is the single most important methodological caveat in the release.

Predictor admission uses a **fixed four-Jalali-month regulatory lag**: a fiscal
year *t* statement is treated as available four Jalali months after the fiscal
year end. The field is named `assumed_available_at_regulatory` — "assumed" is
doing real work in that name.

* Row-level publication timestamps were **never collected** for this panel.
* No individual company-year's actual filing date was verified.
* The contract records `is_observed_publication_timestamp = false` and
  `availability_date_semantics = assumed_regulatory_deadline_not_observed_publication_timestamp`.

So the four-month date is a **prespecified proxy for availability**, not an
observed publication timestamp. Any claim about real-time or point-in-time
behaviour that rests on it is a claim about the proxy.

## Provenance is file-level and incomplete

A source file is recorded for **1,303 of the 1,331 upstream panel rows, and is
absent for 28**. Those 28 rows are a documented provenance gap. They were not
concealed, not imputed, and not reclassified.

The `source_url` column is populated for only a small minority of rows; it is a
partial convenience field, not a complete provenance record.

## Every column is documented

`RELEASE_COLUMN_DICTIONARY.csv` has **one row for each of the 115 released
columns** — no gaps, no duplicates. Each row carries the column's definition,
data type, unit, role, model eligibility, source block, whether the value came
from a provider line item or was author-derived, temporal reference,
missing-value semantics, derivation or formula, its limitations, and the exact
repository file and section the facts were transcribed from.

Nothing in it was invented for the release: every row is anchored to a
committed contract, dictionary, target definition or frozen generator, and the
`definition_status` column says which. Read it before selecting features — in
particular the `model_eligibility` column, which marks the 14 target-derived
columns that must never be used as predictors.

## Quality-control coverage differs by check

The accounting checks were not all evaluable on the same number of rows, and
the release does not pretend otherwise:

| Check | Rows evaluable (of 1,331) |
|---|---|
| Balance-sheet identity | 1,312 |
| Leverage / current / equity ratio, ROA, asset turnover | 1,312 |
| Financial expense to assets | 1,311 |
| Operating cash flow to assets | 1,273 |

Zero mismatches were recorded on the rows that *could* be evaluated. That is not
a statement about the rows that could not be. See `LIMITATIONS.md`.

## Contents

```
README.md                          this file
LICENSE_DATASET.txt                CC BY 4.0 grant, and its exact scope
SOURCE_AND_LICENSE_NOTES.md        source-rights notes + the author determination  ← read before reuse
LIMITATIONS.md                     what these files cannot support
RELEASE_COLUMN_DICTIONARY.csv      all 115 released columns, one row each  ← start here for a column
DATA_DICTIONARY_AND_FILE_GUIDE.md  file-by-file guide, and how to read the dictionaries
CITATION.cff                       machine-readable citation metadata
zenodo_metadata_candidate.json     proposed deposition metadata (candidate only)
release_manifest.json              per-file size, SHA-256, role, source, reason
SHA256SUMS.txt                     checksums for every payload file

data/         four analysis-ready modeling surfaces (one primary, three robustness)
audit/        four audit surfaces (NOT all model-ready)
documentation/ the committed contract, dictionary, role map, QC and split records
```

Verify integrity with:

```
sha256sum -c SHA256SUMS.txt
```

## What is deliberately not here

* Original source PDFs and filing documents.
* Raw provider API responses or scraped payloads.
* Any model, prediction, score, or held-out evaluation output.
* Credentials, caches, or temporary files.

The panel released here is the authors' compiled factual dataset. The original
provider documents behind it are **not redistributed** — see
`SOURCE_AND_LICENSE_NOTES.md`.

## Licence and source rights, in one paragraph

The authors offer their **own** original compilation, annotations, structure
and release metadata under **CC BY 4.0**, to the extent they hold rights in
them. That grant does **not** relicense third-party source materials, and it
makes no representation about the redistribution terms of the underlying
provider content. The human author has determined that the source data used in
this study were publicly and freely accessible and that redistributing the
compiled panel needs no separate provider permission — a **determination by the
author**, not a provider licence and not a verification of anyone's published
terms. `LICENSE_DATASET.txt` states the licence scope precisely and
`SOURCE_AND_LICENSE_NOTES.md` states the rights position in full, including
which provider terms pages were never retrieved.
