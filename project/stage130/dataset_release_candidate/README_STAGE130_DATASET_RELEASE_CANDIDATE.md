# Stage130 — Zenodo dataset Release Candidate

**Action id:** `stage130-dataset-release-candidate`
**Date:** 2026-08-21
**Type:** preparation and documentation only

---

## What this action did

It built a deterministic, audit-ready Zenodo dataset Release Candidate from the
eight frozen Stage125 Part 3C surfaces plus the committed documentation needed
to read them, and recorded the governance boundary around it.

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

## Publication readiness: NOT_READY_FOR_PUBLICATION

The source-rights audit (`source_rights_matrix.csv`) found one blocking
provider: **CODAL**. Its published terms of use could not be retrieved from the
audit environment on 2026-08-21 — `https://www.codal.ir/` and
`https://www.codal.ir/Rules.aspx` both timed out with no HTTP response — so the
redistribution terms governing the compiled CODAL-derived factual fields are
**genuinely unresolved**.

Separately, the approved manuscript states that the company-level source data
are *not openly redistributable*, while the authors' stated intent is to publish
this dataset openly. That conflict is recorded and left standing rather than
resolved in either direction. Resolving it requires verifying CODAL's terms and,
once a DOI actually exists, a separate authorized manuscript action.

Nothing was removed from the payload and no frozen value was altered to make the
blocker go away: the decision record pins
`columns_removed_to_avoid_the_blocker = 0` and
`frozen_values_altered_to_avoid_the_blocker = 0`.

TSETMC and World Bank do not block: no field from either is in the release. The
World Bank's CC BY 4.0 licence was verified directly
(`https://datacatalog.worldbank.org/public-licenses`, HTTP 200, 2026-08-21).

## Package contents

| File | What it is |
|---|---|
| `stage130_dataset_release_candidate_decision.json` | The human decision, the human-supplied release metadata, and the source-rights audit summary |
| `stage130_dataset_release_candidate_governance_boundary.json` | Every boundary and every zeroed counter |
| `release_manifest.json` | Per-file bundle path, byte size, SHA-256, role, source path and inclusion reason |
| `SHA256SUMS.txt` | `sha256sum`-compatible checksums for the bundle payload |
| `source_rights_matrix.csv` | Provider-by-provider rights audit |
| `metadata_and_hashes_stage130_dataset_release_candidate.json` | Hashes of this package's own files, and the archive digest |
| `release_payload/` | The release-specific documents copied byte-for-byte into the bundle |

## Reproducing the candidate

```bash
python project/src/stage130_dataset_release_candidate.py
```

Output goes to `project/stage130/dataset_release_candidate/build/`, which is
**gitignored**. The archive is never tracked; the builder, its inputs, the
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
