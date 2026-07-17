# Stage125 Part 3B.1A — CUT-A Available-at Operationalization Lock

**Status:** maintenance decision lock only (schema / pure parsers / synthetic validation).

## What is locked

For a predictor-year financial-statement row `t`:

```text
operational available_at =
  PublishDateTime of the exact matched official CODAL LetterSerial/version
```

only when the official document is exactly bound to the predictor row **and** the
canonical source version.

## SentDateTime

`SentDateTime != available_at`.

- preserved raw for audit/comparison only
- never used as cutoff or public availability
- even when equal to `PublishDateTime`, mapping still uses `PublishDateTime`

## Why PublishDateTime

- operational public-release timestamp in this project
- `SentDateTime` may be publisher-send time and does not prove public availability
- more conservative / leakage-safe than `SentDateTime`
- methodological operationalization lock — not inference from local filenames/mtimes

## Normalized revision vocabulary

Normalized `revision_status` matches the frozen provenance schema enum only:

```text
original
revision
restatement
```

`correction` is **not** a normalized status. CODAL «اصلاحیه» may be retained in
`revision_status_raw`; it maps to normalized `revision` only when that mapping is
explicit. `restatement` is used only when source/version evidence supports it.
Missing/unclassifiable status → `UNRESOLVED`.

## Exact source-version binding

Authoritative structural checks (boolean flags cannot bypass):

- non-empty `letter_serial` and `canonical_letter_serial` with exact equality
- if `canonical_tracing_no` is present, `tracing_no` must be present and equal
- non-empty official titles on both sides with exact equality
- for `revision` / `restatement`:
  `values_source_letter_serial == letter_serial == canonical_letter_serial`
- official URL and raw payload/snapshot hash present

## Asia/Tehran wall time

Jalali CODAL timestamps are classified with UTC round-trips over `fold=0` and
`fold=1` (`zoneinfo` `Asia/Tehran`). Nonexistent spring-forward times are
`nonexistent_local_time` (not ambiguous). Ambiguous fall-back times without a
deterministic fold rule are
`ambiguous_local_time_without_deterministic_rule`. No fixed `+03:30`.

## Non-claims

- no CODAL / TSETMC / CBI network
- no real `available_at` assignment
- no pilot cutoff resolution
- no extraction / scoring / Gate admission
- no Part 3B.2 / Stage126 / modeling
- research pointers remain
  `last_completed_research_action_id=stage125-part3a-decision-lock`,
  `next_research_action_id=stage125-part3b-evidence-capture`

## Marker

`cut_a_available_at_operationalization_locked=true`

`part3b_completed` remains `false`.
