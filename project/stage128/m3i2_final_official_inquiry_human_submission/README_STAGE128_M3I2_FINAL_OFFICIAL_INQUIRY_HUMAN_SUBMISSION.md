# Stage128 — M3I-2 final official inquiry: human submission (RECORDING ONLY)

**Action id:** `stage128-m3i2-final-official-inquiry-human-submission`
**Baseline:** `main` at `89d8e6ff2d12ec82903cd28aa7ab839eb946b658` (the merge commit of PR #76)
**Status:** COMPLETE — recording only. Nothing scientific moved.

This package records, in sanitized form, that a **human supervisor** submitted the
prepared World Bank inquiry **exactly once**. Automation submitted nothing, signed in
to nothing and read no personal mailbox.

## What actually happened

* Channel: **World Bank Data Help Desk — Contact support**
* Category: **Data Compilation Methodology**
* Subject: `Request for official historical WDI archive release dates and PA.NUS.FCRF unit continuity for Iran`
* Canonical body SHA-256: `dd82929f8098061d501c51b65cac6f3e3ed203cb00ff5689ae0e66f9f2f1e8b5`
* Attachments selected before submission:
  * `m3i2_world_bank_inquiry_edition_inventory.csv` — `5c4739482d685ad4a1fd13c6a82d16cacb882d7e07996535671bb2f267b3a35b`
  * `m3i2_world_bank_inquiry_fx_semantic_questions.md` — `2cc118c224b43acdfa7abcee23c3b2a7ddd7dc0809a9ee072f29aad02276cf94`
* The confirmation page said the message had been received.
* The confirmation e-mail said a data support specialist will reply.

**The acknowledgement is a receipt, not an answer.** It resolves neither blocker.

## What is deliberately *not* claimed

| Question | Recorded answer |
| --- | --- |
| Ticket id? | **None was displayed.** `ticket_id_present: false`, `ticket_id_redacted: null`, `ticket_id_sha256: null`, `ticket_id_fabricated: false`. Nothing was guessed. |
| Exact UTC instant? | **Unresolved.** The UI showed `2026-08-06 14:03` with **no timezone**, so `submission_timestamp_utc: null` and `submission_timestamp_utc_status: UNRESOLVED_CONFIRMATION_UI_DID_NOT_DISPLAY_TIMEZONE`. It was not derived from the user's location, the system clock or a screenshot filename. |
| Body verified byte-for-byte? | **No.** The e-mail repeated the body visually only: `CANONICAL_BODY_VISUALLY_CONFIRMED_NOT_RAW_BYTE_VERIFIED`. |
| Attachments confirmed by the server? | **No.** They were visibly selected before submission, but the confirmation never enumerated them. |

## External confirmation evidence — hashes only

No screenshot, e-mail, name, address, IP or account identifier is committed. Only
hashes and byte sizes are recorded; every copy is `stored_outside_repository: true`,
`committed_to_git: false`, `contains_personal_information: true`.

| Copy | SHA-256 | Bytes |
| --- | --- | --- |
| Web confirmation page | `14060eef17ccb52838433d8186b3e476d1a703d2476bb37cbd9b5aa8e0a931f6` | 631880 |
| Confirmation e-mail, part 1 | `8841e6ab32115c21e2b994f5b80ac0311e826853e3059bc7c188a15a5a2f1e85` | 383457 |
| Confirmation e-mail, part 2 | `dd95e54919f6809d5f07a2248e73dffc919b31465351c2a02c56c6eb1c626ca7` | 339376 |

## Waiting period

The locked rule is **10 business days**, Monday–Friday only, submission day excluded,
public holidays not modeled. From the official displayed calendar date **2026-08-06**:

* business day 1 = **2026-08-07**
* business day 10 = **2026-08-20**
* `waiting_period_completion_date` = **2026-08-20**, status **ACTIVE**
* `follow_up_earliest_calendar_date` = **2026-08-21**

That date is **eligibility only**. A follow-up still needs its own explicit human
authorization, and an early substantive response would still require a separate,
currently unauthorized ingestion action.

## Scientific state — unchanged

M3I-2 evidence status `UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE`, `m3i2_admitted: false`.
Verified WDI release dates **0**; verified pre-cutoff editions **0**; unresolved
cutoffs **37 of 37**; unresolved development pairs **539 of 539**. CPI semantic
compatibility 16 PASS / 0 UNRESOLVED / 0 FAIL_INTEGRITY; FX 0 PASS / 16 UNRESOLVED /
0 FAIL_INTEGRITY. Data Gate `NOT_EXECUTED`; 0 coverage calculations, 0 feature
materializations, 0 model fits, 0 predictions, 0 predictive metrics. Final Test
locked; M3-LAG-WDI `NOT_LOCKED`; M4 unauthorized; no paper winner selected.

## Authorization

Recorded under one explicit one-action human authorization (95 UTF-8 bytes, SHA-256
`4562e480…7978`), which this recording CONSUMED. `scope_identified_by_hash_alone:
false`, `merge_authorized: false`. The PR stays a Draft.

## Package contents

* `stage128_m3i2_final_official_inquiry_human_authorization_record.json`
* `stage128_m3i2_final_official_inquiry_submission_evidence_record.json`
* `stage128_m3i2_final_official_inquiry_governance_boundary.json`
* `stage128_m3i2_final_official_inquiry_submission_decision.json`
* `stage128_m3i2_final_official_inquiry_submission_qc_report.json`
* `metadata_and_hashes_stage128_m3i2_final_official_inquiry_human_submission.json`

The canonical live submission record remains
`project/stage128/m3i2_final_official_documentary_recovery/stage128_m3i2_world_bank_inquiry_submission_record.json`.
