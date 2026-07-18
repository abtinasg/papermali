# Stage125 Part 3B.1D — Controlled Same-Five Metadata Resolution Capture

## Purpose

Second controlled metadata-provenance capture within the existing five-row CODAL document-binding pilot. Exactly **four** authorized logical HTTPS GET requests to `www.codal.ir/Reports/Decision.aspx`.

## Locked rows

| predictor_row_key_t | scientific status | network |
|---|---|---|
| ثنوسا\|1392 | UNRESOLVED | authorized GET #1 |
| بوعلی\|1399 | UNRESOLVED | authorized GET #2 |
| بوعلی\|1400 | UNRESOLVED | authorized GET #3 |
| اردستان\|1401 | REJECTED | **zero requests** (structural rejection) |
| اپال\|1401 | UNRESOLVED | authorized GET #4 |

Aggregate scientific counts remain: BOUND=0, UNRESOLVED=4, REJECTED=1, `available_at` non-null=0.

## Prohibitions

- no binding-status mutation / no BOUND promotion
- no real `available_at` assignment (`SentDateTime` audit-only)
- no financial-value extraction
- no accessibility scoring / Gate application
- no 80-row scale-up / Part 3B.2 / Stage126 / modeling
- no search/discovery/API endpoints
- no overwrite of historical Part 3B.1B ثنوسا receipts
- raw HTML/binary payloads remain gitignored

## Runner

```bash
python project/run_stage125_part3b1d.py --capture
python project/run_stage125_part3b1d.py --check
```

`--check` is zero-network / zero-writes and does not require the gitignored raw cache.

## Research pointers (unchanged)

- `last_completed_research_action_id` = `stage125-part3a-decision-lock`
- `next_research_action_id` = `stage125-part3b-evidence-capture`

Merge requires explicit human approval.
