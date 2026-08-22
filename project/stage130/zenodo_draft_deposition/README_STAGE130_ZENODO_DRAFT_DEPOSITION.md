# Stage130 — Zenodo DRAFT deposition (recording only; NOT published)

**Action id:** `stage130-zenodo-draft-deposition`
**Date (UTC):** 2026-08-22
**Kind:** custody/governance recording of a HUMAN-EXECUTED event. **Zero
scientific execution, zero manuscript change, zero Zenodo API call by this
action, zero Final Test access.**

## What happened

A human supervisor executed the verified V6 deposition script **exactly once**
on their own machine. Zenodo's authenticated response was observed by the
human, and the result is:

```
deposition_id      = 22059238
reserved_doi       = 10.5281/zenodo.22059238
record_submitted   = false
record_state       = unsubmitted
doi_reserved       = true
doi_published      = false
public_release     = false
```

The file stored in the draft is exactly the recorded Release Candidate:

```
filename = tse_financial_distress_dataset_1392_1402_release_candidate_rc3.zip
bytes    = 11824690
sha256   = 4adb32bd675fd9181d8ced783b6734382e9749c6c574e35567d1bec65fd72f70
md5      = cbd3df6c75053ee6d0641f19d5301d7a
```

That SHA-256 and that byte size are the *same* pair already published for
`1.0.0-rc.3` by `project/stage130/dataset_release_candidate/`. The Handoff
deriver requires them to match, so the deposit is bound to the candidate the
repository actually documents — a differently-built archive cannot inherit this
record.

The deposition's verified metadata is:

```
version      = 1.0.0-rc.3
upload_type  = dataset
access_right = open
license      = cc-by-4.0
language     = eng
```

## `access_right = open` is NOT public availability

This is the one reading that would put a false claim into the manuscript, so it
is guarded on every surface and by the generator:

* `access_right: open` is **draft metadata**. It states the access condition the
  record *would* carry **if** it were ever published.
* It is **not** a statement that the record is published, public, discoverable,
  indexed, downloadable or citable.
* While `submitted = false` and `state = unsubmitted`, the deposition is a
  **private draft** visible only to its owner.
* The DOI is **reserved only**. It is a placeholder identifier: it is not
  registered, it does not resolve, and it must never be described as active,
  published, resolving or publicly available.

## What this is NOT

* It is **not** a publication. `zenodo_published` and `public_release` stay
  `false`, and `publication_authorized` is `false`.
* It is **not** a submission. `record_submitted` is `false` and `record_state`
  is `unsubmitted`.
* It is **not** an authorization to publish, submit, activate the DOI, re-run
  the deposition script, read or request a Zenodo token, or make any further
  Zenodo call.
* It is **not** a manuscript change. Zero manuscript bytes moved; the Data
  Availability Statement is deliberately **unchanged**, because no public DOI
  exists yet. Updating it is a **separate** action that may only happen after a
  human publication decision, and must be followed by a fresh human review of
  the changed bytes.
* It is **not** Ready-for-Review and **not** merge authorization. Both stay
  `false`; PR #100 stays a Draft.
* It is **not** a retroactive authorization. The pointer live at execution time
  (`human-dataset-release-candidate-digest-review`) carried
  `authorized = false`, and this package records that fact rather than erasing
  it: `preexisting_pointer_was_authorized: false`,
  `recording_is_not_retroactive_authorization: true`. The repository records
  what a human did; it does not convert it into a permission it never granted.

## Provenance of these facts

Every value above was **supplied by the human** who ran the script and observed
Zenodo's authenticated response (`supplied_by: human`,
`authenticated_zenodo_response_observed: true`). They were **not** independently
retrieved by the programmer
(`independently_retrieved_by_programmer: false`): this action made **no** Zenodo
API call of any kind, and specifically no publish or submit call
(`zenodo_api_calls_made_by_this_action: 0`,
`zenodo_publish_endpoint_calls: 0`).

The script's own state file is kept **outside** the repository and is neither
committed, printed nor read here
(`deposition_state_file_committed_to_git: false`). No token, credential or
`Authorization` header appears in this package, in the diff, in the commits or
in the pull request; the generator sweeps the package and fails closed if one
ever does.

The three V6 artifacts are pinned by SHA-256 in the decision
(`zenodo_rc3_draft.sh`, `zenodo_draft_metadata_rc3.json`,
`test_zenodo_rc3_draft.sh`) and are re-checked against constants held
independently in the generator, so a silently edited record breaks the build.

## History is superseded in the open, not rewritten

The Release Candidate package still publishes what was true when it ran —
`zenodo_deposition_created: false`, `zenodo_upload_performed: false`,
`zenodo_doi_reserved: false`, a **null** DOI, and its own pointer
`human-dataset-release-candidate-digest-review`. Not one byte of it is edited.
This package supersedes exactly four live markers and the live pointer, declares
the supersede machine-readably on both surfaces, and the deriver **reads the
Release Candidate record back** and refuses to build if those historical values
have been quietly changed.

`zenodo_published` and `public_release_authorized` are listed as **deliberately
not superseded**: they were false before this deposition and they are false
after it.

## The live pointer

```
next_research_action_id  = human-zenodo-draft-review-and-publication-decision
next_action_authorized   = false
pointer_is_not_authorization = true
```

The successor names a **human** step: review the private Draft as it now stands
and decide, separately and explicitly, whether it is ever published. Naming it
advances nothing and permits nothing.

## Files

| file | role |
| --- | --- |
| `stage130_zenodo_draft_deposition_decision.json` | the human decision, the observed Zenodo state, the deposited file's digests and the supersede declaration |
| `stage130_zenodo_draft_deposition_governance_boundary.json` | what this action did and did not do, with all counters zero |
| `metadata_and_hashes_stage130_zenodo_draft_deposition.json` | package file inventory with byte sizes and SHA-256 |

Deriver: `derive_stage130_zenodo_draft_deposition_markers` in
`project/scripts/update_ai_handoff.py`.
Tests: `project/tests/test_stage130_zenodo_draft_deposition.py`.
