# Stage130 — Zenodo dataset Release Candidate

**Action id:** `stage130-dataset-release-candidate`
**Release version:** `1.0.0-rc.3` (supersedes `1.0.0-rc.2`, and through it `1.0.0-rc.1`)
**Date:** 2026-08-21
**Type:** preparation and documentation only

---

## What this action did

It built a deterministic, audit-ready Zenodo dataset Release Candidate from the
eight frozen Stage125 Part 3C surfaces plus the committed documentation needed
to read them, and recorded the governance boundary around it.

`1.0.0-rc.3` corrects two descriptive defects in `1.0.0-rc.2`. Nothing
scientific, no data value and no rights record changed.

1. **The source-scope description was wrong.** rc.2's
   `zenodo_metadata_candidate.json` named all three study providers together as
   the sources of the released values. That implies material from every one of
   them is in the release, which contradicts the committed
   `source_rights_matrix.csv` — the matrix has recorded throughout that
   CODAL-derived, researcher-compiled company financial fields are present, and
   that **no TSETMC-derived and no World Bank-derived field is**. The
   superseded wording is quoted verbatim in exactly one place,
   `stage130_dataset_release_candidate_decision.json` under
   `rc3_correction.previous_statement`, so the correction can be audited
   without the false sentence circulating anywhere else. The corrected
   statement is:

   > The released company-year panel contains researcher-compiled company
   > financial-statement fields from publicly accessible CODAL disclosures,
   > together with author-derived variables and annotations. No TSETMC- or
   > World Bank-derived field is included in this release; those sources relate
   > only to the wider study.

   The old sentence cannot come back: `FORBIDDEN_RELEASE_SCOPE_CLAIMS` and
   `gate_release_scope_statements` in the builder, and
   `_stage130_rc_assert_no_misleading_release_scope_claim` in the Handoff
   deriver, both fail closed on it and on any newly worded sentence asserting
   that TSETMC- or World Bank-derived material is released.

2. **The file counts were ambiguous.** rc.2's package metadata published a
   single `bundle_payload_file_count` of `27`, which read as "27 manifest
   payload files" and was wrong. rc.3 publishes the two counts under two names:
   **25** files are described by `release_manifest.json` as payload files, and
   the deterministic archive contains **27 members** — those 25 plus
   `release_manifest.json` and `SHA256SUMS.txt`, which are integrity records
   about the payload and are not themselves manifest payload files.
   `SHA256SUMS.txt` covers the payload and the manifest but never itself, so it
   carries **26** lines.

`1.0.0-rc.2` itself added two things to `1.0.0-rc.1`, and that remains true:

1. the **human author's source-rights determination**, recorded as a
   determination by the author and never as a verification of any provider's
   published terms;
2. **`RELEASE_COLUMN_DICTIONARY.csv`**, which documents **all 115 released
   columns** — one row each, every row anchored to the committed contract,
   dictionary, target definition or frozen generator its facts came from.

## What this action did NOT do

| | |
|---|---|
| Zenodo deposition created | **no** |
| Files uploaded to Zenodo | **no** |
| DOI reserved | **no** |
| DOI published | **no** |
| Public release authorization consumed | **no** |
| Manuscript modified | **no** |
| Manuscript availability claim changed | **no** |
| PR marked Ready for Review | **no** |
| PR merged | **no** |

A separate **exact-digest human authorization** is required before any Zenodo
write or publication.

## Publication readiness: READY_FOR_EXACT_DIGEST_HUMAN_REVIEW

`1.0.0-rc.1` was `NOT_READY_FOR_PUBLICATION`, because the source-rights audit
recorded **CODAL** as a blocking provider: its published terms of use could not
be retrieved from the audit environment on 2026-08-21 — `https://www.codal.ir/`
and `https://www.codal.ir/Rules.aspx` both timed out with no HTTP response.

**That historical fact is unchanged and preserved in full, through rc.3.** No
CODAL or TSETMC terms page has been retrieved or read, then or since. The matrix still records
their stated terms as `NOT_VERIFIED`, and
`provider_terms_independently_retrieved` and
`provider_terms_independently_verified` are both `no`.

What supersedes the blocker is the **human author's source-rights
determination**: that the data used in the study were publicly and freely
accessible, and that public redistribution of the researcher-compiled panel and
the author-derived variables requires no separate provider permission. Its
status token is:

```
HUMAN_AUTHOR_DETERMINATION_NO_SEPARATE_PERMISSION_REQUIRED
```

It is a determination **by the author** — not a provider licence, not an
independent verification of anyone's terms, and not a legal opinion. The
generator and the Handoff deriver both refuse to build if any artifact in this
package asserts otherwise; the forbidden phrasings are enumerated in
`FORBIDDEN_RIGHTS_CLAIMS`. A second, separate sweep — `FORBIDDEN_RELEASE_SCOPE_CLAIMS`
and the sentence classifier behind `gate_release_scope_statements` — refuses any
claim that TSETMC- or World Bank-derived material is in the release. The two
gates are independent: one protects the rights record, the other protects the
composition record, and neither can be satisfied by the other passing.

`READY_FOR_EXACT_DIGEST_HUMAN_REVIEW` means one thing: a human is being asked to
read the exact archive SHA-256 and decide. It is **not** `PUBLISHED`, **not**
`PUBLIC_RELEASE_AUTHORIZED`, and it authorizes no Zenodo action.

Nothing was removed from the payload and no frozen value was altered at any
point, under either candidate: the decision record pins
`columns_removed_to_avoid_the_blocker = 0` and
`frozen_values_altered_to_avoid_the_blocker = 0`.

TSETMC and World Bank do not block: no field from either is in the release. The
World Bank's CC BY 4.0 licence was verified directly
(`https://datacatalog.worldbank.org/public-licenses`, HTTP 200, 2026-08-21) —
that provider, and only that provider, was actually read.

## What the release actually contains

| | |
|---|---|
| Providers contributing a released field | **CODAL** only |
| Providers relating to the wider study only | **TSETMC**, **World Bank** |
| TSETMC-derived fields included | **no** |
| World Bank-derived fields included | **no** |
| Original provider files redistributed | **no** |

The released company-year panel contains researcher-compiled company
financial-statement fields from publicly accessible CODAL disclosures, together
with author-derived variables and annotations. No TSETMC- or World Bank-derived
field is included in this release; those sources relate only to the wider study.

Two committed records establish the exclusions independently: the Stage125
source registry marks `src_m2_tsetmc_market` as `pending_part3` / not collected,
and none of the 115 columns in the role map is a market-data or macroeconomic
field.

## Two file counts, named apart

| | |
|---|---|
| Files described by `release_manifest.json` as payload files | **25** |
| Members in the deterministic archive | **27** |
| Lines in `SHA256SUMS.txt` | **26** |

The archive's 27 members are the 25 payload files plus `release_manifest.json`
and `SHA256SUMS.txt`. Those two are integrity records *about* the payload: the
manifest deliberately excludes itself and the checksum file, and the checksum
file covers the payload and the manifest but never hashes itself. **Describing
all 27 as manifest payload files would be wrong**, and no surface in this
package does. `gate_file_count_terminology` derives all three numbers from the payload it
actually built and stops the build if any published figure disagrees.

## The 115-column release dictionary

`release_payload/RELEASE_COLUMN_DICTIONARY.csv` carries one row for each of the
115 released columns, with 15 fields per row: definition, data type, unit,
column role, model eligibility, source block, whether the value is a provider
line item or author-derived, temporal reference, missing-value semantics,
derivation or formula, its own limitations, the authoritative repository path,
the field or code section inside that path, and a `definition_status` naming
which class of committed source the facts came from.

It is generated by `project/src/stage130_release_column_dictionary.py`, which is
fail-closed twice over: it refuses to emit a row it cannot anchor to a committed
source (reporting the undefined columns by name instead of inventing text), and
the release builder regenerates it and compares bytes, so a hand-edited CSV
cannot ship.

Regenerate it with:

```bash
python project/src/stage130_release_column_dictionary.py --write
```

Relationship to the two historical artifacts:

| File | What it is | Coverage |
|---|---|---|
| `RELEASE_COLUMN_DICTIONARY.csv` | This release's dictionary | **115 / 115** |
| `part3c_column_role_map_stage125.csv` | The authoritative column set and role contract | 115 / 115 names and roles, no definitions |
| `data_dictionary_stage125.csv` | The historical Part 1 dictionary over the upstream panel | 25 / 115 |

The role map stays authoritative for which columns exist and what role each has;
the release dictionary is gated to match it exactly. The Stage125 dictionary
ships unedited as history, and its shortfall is published in
`release_manifest.json` under `upstream_dictionary_coverage`.

## Human manuscript submission metadata: supplied, NOT applied

The six human-only submission items — authors and author order, affiliations and
corresponding author, funding, conflicts of interest, the ethics and
data-governance statement, and the intended data-access mechanism — **have now
been supplied by the human author** and are recorded in the decision artifact
under `human_supplied_manuscript_submission_metadata`.

They are **not** in the manuscript:

| | |
|---|---|
| `human_submission_metadata_supplied` | **true** |
| `human_submission_metadata_applied_to_manuscript` | **false** |
| `manuscript_modified_by_this_action` | **false** |
| `manuscript_requires_post_doi_metadata_update_and_human_review` | **true** |

Inserting them is a separate action needing its own authorization, and the
data-access wording additionally depends on a DOI that does not exist. The
approved manuscript stays byte-identical, and the deriver re-derives both its
blob id and its SHA-256 to prove it.

## Preserving 1.0.0-rc.1 and 1.0.0-rc.2

Both predecessors are superseded, not deleted. The chain is recorded on the
decision, the manifest and the package metadata under `supersedes_history`:

| | `1.0.0-rc.1` | `1.0.0-rc.2` |
|---|---|---|
| Archive | `..._release_candidate.zip` | `..._release_candidate_rc2.zip` |
| SHA-256 | `6649074290c5937066168e326b4e9c043f775c974edf2fb5b9c14ca452d25e45` | `d82b747a2e96f09cfa8b1a0118e6e7664cf83b469707409816a0b6dbd8127373` |
| Bytes | `11657151` | `11808267` |
| Readiness at the time | `NOT_READY_FOR_PUBLICATION` | `READY_FOR_EXACT_DIGEST_HUMAN_REVIEW` |
| Build directory | `build/` | `build/rc2/` |
| Superseded by | `1.0.0-rc.2` | `1.0.0-rc.3` |
| Superseded because | human author source-rights determination plus complete 115-column dictionary preparation | misleading three-provider source-scope description, and ambiguous payload-file versus archive-member counts |
| Deposited on Zenodo | **never** | **never** |

`rc.3` builds under a **new filename**
(`tse_financial_distress_dataset_1392_1402_release_candidate_rc3.zip`) into a
**new build subdirectory** (`build/rc3/`), so neither predecessor's archive nor
unpacked tree is overwritten, renamed or deleted, and neither recorded digest
moves. No commit was amended, squashed, rebased or force-pushed.

## Package contents

| File | What it is |
|---|---|
| `stage130_dataset_release_candidate_decision.json` | The human decision, the human-supplied release metadata, and the source-rights audit summary |
| `stage130_dataset_release_candidate_governance_boundary.json` | Every boundary and every zeroed counter |
| `release_manifest.json` | Per-file bundle path, byte size, SHA-256, role, source path and inclusion reason |
| `SHA256SUMS.txt` | `sha256sum`-compatible checksums: 26 lines covering the 25 payload files plus `release_manifest.json` |
| `source_rights_matrix.csv` | Provider-by-provider rights audit |
| `metadata_and_hashes_stage130_dataset_release_candidate.json` | Hashes of this package's own files, and the archive digest |
| `release_payload/` | The release-specific documents copied byte-for-byte into the bundle |
| `release_payload/RELEASE_COLUMN_DICTIONARY.csv` | All 115 released columns, one row each, every row anchored to a committed source |

## Reproducing the candidate

```bash
python project/src/stage130_dataset_release_candidate.py
```

To regenerate the three committed package records — `release_manifest.json`,
`SHA256SUMS.txt` and `metadata_and_hashes_stage130_dataset_release_candidate.json`
— from a fresh build rather than maintaining them by hand:

```bash
python project/src/stage130_dataset_release_candidate.py --write-records
```

Output goes to `project/stage130/dataset_release_candidate/build/rc3/`, which is
**gitignored** (the whole `build/` tree is). The archive is never tracked; the builder, its inputs, the
manifest and the checksums are, so the bundle is reproducible from Git without
the repository carrying a second copy of the frozen CSVs.

The build is byte-reproducible: fixed ZIP member timestamps (the 1980 epoch),
fixed mode 0644, sorted member order, no directory entries, and `ZIP_STORED`
rather than deflate. Storing is deliberate — it makes the archive SHA-256 a pure
function of the payload bytes, so a reviewer on another machine with a different
zlib reproduces the same digest. A human is being asked to approve that exact
digest, so it must not depend on a compression library version.

## Why the frozen CSVs are verified by SHA-256 and not by Git blob

`project/stage125/part3c_outputs/` is gitignored (`.gitignore:49`) — the eight
frozen surfaces are bulky regenerable outputs, tracked by digest in the Stage125
contract rather than as Git objects. Their identity here is therefore SHA-256,
and both this package and the Stage125 contract pin the same eight values. The
Handoff deriver tolerates their **absence** (a fresh clone legitimately lacks
them) but never tolerates **drift**.

## Firewall

`project/stage129/stage129_final_test_predictions.json` was not opened, not
hashed and not packaged. The builder's `FORBIDDEN_SOURCES` names it and
`_guarded_open` refuses it, along with any path whose name looks like a Final
Test or prediction artifact, so a future edit that reached for one aborts rather
than quietly succeeding.

## What the next action is

`human-dataset-release-candidate-digest-review` — a human reads the exact
archive SHA-256 and decides. It is a **pointer, not an authorization**.
