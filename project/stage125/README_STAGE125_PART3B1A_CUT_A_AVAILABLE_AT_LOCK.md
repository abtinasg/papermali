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
