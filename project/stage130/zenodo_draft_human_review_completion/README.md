# Stage130 — Zenodo Draft: human review COMPLETE, Notes corrected (still NOT published)

**Action id:** `stage130-zenodo-draft-human-review-completion`
**Date (UTC):** 2026-08-22
**Kind:** append-only custody/governance recording of TWO later HUMAN events on
an existing Zenodo Draft. **Zero Zenodo calls by this action, zero scientific
execution, zero manuscript change, zero archive change, zero Final Test
access.**

## Four different things, kept apart

This package exists because four things are easy to blur into one another, and
blurring them is how a private draft becomes a false publication claim.

| # | Event | When | Who | Status |
| --- | --- | --- | --- | --- |
| 1 | The **draft deposition**: a deposition was created, the rc.3 archive was uploaded, a DOI was reserved | earlier, 2026-08-22 | human ran the verified V6 script once | recorded by `stage130-zenodo-draft-deposition`, **not** modified here |
| 2 | The **human visual review** of that draft in Zenodo Preview | later, 2026-08-22 | human | recorded here, **complete** |
| 3 | The **human metadata-only Notes correction**, made in the Zenodo UI and saved as a Draft | later, 2026-08-22 | human | recorded here, **complete** |
| 4 | The **publication decision** | not yet | human | **outstanding and UNAUTHORIZED** |

Event 1 is history and is preserved exactly as it was written. Events 2 and 3
are new and are recorded here. Event 4 has not happened, is not implied by
events 1–3, and is not authorized by this package.

## The record is still an unpublished Draft

```
deposition_id           = 22059238
reserved_version_doi    = 10.5281/zenodo.22059238
reserved_concept_doi    = 10.5281/zenodo.22059237
record_submitted        = false
record_state            = unsubmitted
zenodo_draft_exists     = true
archive_uploaded        = true
version_doi_reserved    = true
concept_doi_displayed   = true
doi_published           = false
doi_publicly_activated  = false
public_release          = false
version                 = 1.0.0-rc.3
license                 = cc-by-4.0
access_right            = open
```

`access_right = open` is **draft metadata**. It is the access condition the
record *would* carry **if** it were ever published. It is **not** evidence of
current public availability. While `submitted = false` the deposition is a
private draft visible only to its owner, both DOIs are reserved placeholders
that do not resolve, and nothing about this record may be described as
published, active, indexed, downloadable or citable.

A completed review does not publish anything. A corrected Notes field does not
publish anything. Both are things a human did *to a draft*.

## Event 2 — the human visual review

The human opened the draft in Zenodo Preview and reviewed every item below.
The matrix is complete; a partial review would not be recorded as a review.

| reviewed item | reviewed |
| --- | --- |
| the deposited file | ✅ |
| title | ✅ |
| creators | ✅ |
| description | ✅ |
| keywords | ✅ |
| version | ✅ |
| license | ✅ |
| generated Citation | ✅ |
| reserved DOI identifiers (version and concept) | ✅ |
| archive contents | ✅ |

## Event 3 — the human Notes correction (metadata only)

The programmer did not edit Zenodo. The human performed this edit through the
Zenodo UI and saved it as a **Draft**; nothing was submitted and no file moved.

**Historical Notes value** — what the deposition actually carried when it was
created, SHA-256
`9096ed3fc195915fb6428a107adacffde23c59aaac6845966b20cbffcfc62ff2` over the
UTF-8 text with no trailing newline:

> Release candidate 1.0.0-rc.3, superseding 1.0.0-rc.2 and, through it,
> 1.0.0-rc.1. Both predecessors are preserved, not deleted. This record is an
> unpublished Zenodo draft. A DOI has been reserved but not published or
> activated, and no public release has occurred.

**Current authoritative live Notes value**, SHA-256
`7ff1c7de2baab5e2ecc95e20d8996db38bb8ec67e35dc4200335ec37d6f5ea46` over the
UTF-8 text with no trailing newline:

> Release candidate 1.0.0-rc.3, superseding 1.0.0-rc.2 and, through it,
> 1.0.0-rc.1. Both predecessors are preserved, not deleted. The deposited
> archive is the exact RC3 artifact with SHA-256
> 4adb32bd675fd9181d8ced783b6734382e9749c6c574e35567d1bec65fd72f70 and size
> 11,824,690 bytes.

### Why the new text is publication-stable and the old one was not

The historical text asserted the record's **lifecycle status** — that it is an
unpublished draft whose DOI has not been activated. That sentence is true today
and would become **false** the instant the record were ever published, so it
would have had to be edited again at publication time. The authoritative text
asserts only the **identity of the deposited bytes**, which does not change when
a record's lifecycle does. It therefore stays true whether the record is
published or not.

### What the correction does NOT mean

Removing a sentence that said "unpublished" did **not** publish anything. The
lifecycle state is carried by the record itself and by this repository's
markers — `record_submitted = false`, `record_state = unsubmitted`,
`doi_published = false`, `doi_publicly_activated = false`,
`public_release = false` — not by the prose in a Notes field. Anyone reading the
shorter Notes as a status change is reading it wrong, and the generator refuses
to build a record that does.

### The historical value is superseded, not erased

The historical Notes text remains **historically correct** for the earlier
draft-deposition event: it is exactly what the pinned V6 deposition metadata
artifact `zenodo_draft_metadata_rc3.json`
(SHA-256 `3cb1cc05f41c3b0d9ec9e16d3474290caeccfff8423d1a60cdc0324b7840c375`,
already pinned by the predecessor package) carried in its `notes` field. It is
superseded **only** as the current live value. This package does not rewrite
history to pretend the new Notes existed during the original deposit operation.

## The archive is immutable for this action

Nothing was rebuilt, replaced, re-uploaded, renamed or re-manifested:

```
filename = tse_financial_distress_dataset_1392_1402_release_candidate_rc3.zip
bytes    = 11824690
sha256   = 4adb32bd675fd9181d8ced783b6734382e9749c6c574e35567d1bec65fd72f70
md5      = cbd3df6c75053ee6d0641f19d5301d7a
```

There are **three** distinct Notes-like strings in this story and they must not
be conflated:

1. the `notes` field **inside** the deposited ZIP, in
   `zenodo_metadata_candidate.json` — a **pre-deposition** artifact written
   before anything reached Zenodo, which still says the candidate is not
   deposited. It is historical, it is frozen inside immutable bytes, and the
   later live correction is **not** retroactively injected into it;
2. the **historical** live Notes, above, as deposited;
3. the **current authoritative** live Notes, above.

The Notes correction is an **external metadata event** on the Zenodo record. It
touched no byte of the archive, so the archive's SHA-256 and size are unchanged
and the deposit stays bound to the Release Candidate the repository documents.

## Provenance of these facts

```
supplied_by                           = human
human_visual_review_completed         = true
human_metadata_edit_performed         = true
independently_retrieved_by_programmer = false
zenodo_api_calls_made_by_this_action  = 0
```

Every value here was **supplied by the human** who performed the review and the
edit. The programmer did **not** independently retrieve or verify the live
Zenodo record: this action made no Zenodo call of any kind — authenticated or
unauthenticated — opened no browser against Zenodo, re-ran no deposition
script, and read or requested no token. The script's state file was tested for
**existence only**; it was not opened, printed, parsed, copied, hashed, staged
or committed. No token, credential or `Authorization` header appears in this
package, in the diff, in the commits or in the pull request; the generator
sweeps for credential-shaped material and fails closed if one ever appears.

## What this is NOT

* It is **not** a publication, a submission or a DOI activation. `doi_published`,
  `doi_publicly_activated`, `public_release` and `record_submitted` are all
  `false`.
* It is **not** an authorization to publish, submit, activate either DOI, re-run
  the deposition script, contact Zenodo, or touch the archive.
* It is **not** a manuscript change. Zero manuscript bytes moved and the Data
  Availability Statement is deliberately unchanged, because no public DOI
  exists. Updating it remains a separate action for after a publication
  decision, followed by a fresh human review of the changed bytes.
* It is **not** Ready-for-Review and **not** merge authorization. PR #100 stays
  an open Draft with auto-merge disabled.
* It is **not** a modification of the predecessor package. Not one byte of
  `project/stage130/zenodo_draft_deposition/` is edited, and the deriver reads
  that record back and refuses to build if its historical claims have moved.

## The live pointer

```
next_research_action_id      = human-zenodo-publication-decision
next_research_action_scope   = zenodo_publication_decision_only_no_publication_action_is_authorized
next_action_authorized       = false
next_research_action_authorized = false
pointer_is_not_authorization = true
```

The predecessor pointed at `human-zenodo-draft-review-and-publication-decision`
— two separable things, of which the **review** half is now done. The successor
names only what is left: a human publication **decision**. Naming a decision
advances nothing and permits nothing. No publication action is authorized by
this pointer, and any future Zenodo publication requires its own separate,
explicit human authorization.

## Files

| file | role |
| --- | --- |
| `stage130_zenodo_draft_human_review_completion_decision.json` | the verbatim human authorization, the review matrix, both Notes texts with their pinned digests, and the supersede declaration |
| `stage130_zenodo_draft_human_review_completion_governance_boundary.json` | what this action did and did not do, with all counters zero |
| `metadata_and_hashes_stage130_zenodo_draft_human_review_completion.json` | package file inventory with byte sizes and SHA-256 |

Deriver: `derive_stage130_zenodo_draft_human_review_completion_markers` in
`project/scripts/update_ai_handoff.py`.
Tests: `project/tests/test_stage130_zenodo_draft_human_review_completion.py`.
Predecessor (unmodified): `project/stage130/zenodo_draft_deposition/`.
