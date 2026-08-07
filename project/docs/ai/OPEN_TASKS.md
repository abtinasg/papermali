# OPEN TASKS

Human-maintained. The authoritative "next action" ID lives in `ROADMAP.md`
front matter; this file is the working description.

## Active research workstream: `stage128-m3i2-final-official-documentary-recovery`

The CURRENT workstream is the Stage128 **M3I-2 final official documentary
recovery**. It is an **INITIATION**: a bounded official documentary search plus
the preparation of exactly ONE official World Bank Data Help Desk inquiry. It
retrieved no macro observation, created no dataset row, ran no Data Gate,
computed no coverage, materialized no feature, fit no model and read no
Final Test row.

The prepared inquiry has since been **submitted once by a human supervisor** and
that submission has been recorded, so the live inquiry status is
**`SUBMITTED_ACKNOWLEDGED_WAITING_FOR_SUBSTANTIVE_RESPONSE`** — the human
submission is **no longer outstanding**.

The authoritative research-action pointers are
`last_completed_research_action_id=stage128-m3i2-final-official-inquiry-human-submission`
and `next_research_action_id=stage128-m3i2-final-official-inquiry-response-ingestion`
with `next_research_action_authorized=false` — a pointer is **never** an
authorization. A separate conditional pointer
`conditional_follow_up_action_id=stage128-m3i2-final-official-inquiry-one-follow-up`
carries `conditional_follow_up_earliest_date=2026-08-21` and
`conditional_follow_up_authorized=false`.

### Current scientific action

`stage128-m3i2-final-official-documentary-recovery-initiation` — **COMPLETE**,
recorded under its own explicit one-action human authorization (252 UTF-8
bytes, SHA-256 `a1878df0…9e97`), which was CONSUMED by the recording. It ran in
a clean separate worktree from `main @ b3627809…161188`, the merge commit of
**PR #75 — the merged predecessor**.

**Bounds honoured.** 14 documentary GET requests of a maximum of 20; World Bank
Group hosts only; **0 archive ZIP downloads, 0 redownloads**; **0 repeats** of
any URL in the prior capture manifest (a fail-closed guard refuses duplicates,
archive ZIPs, unofficial hosts and non-HTTPS). Every retained response is
hashed and committed under `raw_official_documents/`.

**The two blockers — both still open.**

1. *Archive release availability.* Official WDI release notes exist only from
   **December 2024** onward. The official Data Updates and Errata page
   announces dated **database** updates, not archive-edition publications, and
   several announced dates differ from the archive filename tokens. The full
   official Help Desk article index contains no archive-release article.
2. *Historical FX semantic continuity for `PA.NUS.FCRF` / `IRN`.* The indicator
   page confirms only the series title and the IMF IFS source; the DEC
   conversion-factor article confirms the official rate is the IFS rate on a
   calendar-year basis. Neither states the Iranian denomination, the valuation
   convention, any redenomination or any unit break.

Bounded-search outcome: `NO_NEW_DOCUMENTARY_EVIDENCE_IN_BOUNDED_SEARCH`.
**Rule D therefore stands for every edition:** `available_at = null`,
`release_date_verified = false`; the filename token is never release evidence
and no unproven previous-month fallback was used.

**Initiation-time submission status: `HUMAN_SUBMISSION_REQUIRED`** (historical).
The Help Desk exposes no public support form and opening a ticket requires a
signed-in account, so the initiation prepared and hashed the inquiry body and
both public attachments instead of submitting. **No ticket was opened, none was
invented, no credential was used and no human-verification step was bypassed.**

### Live submission status — `SUBMITTED_ACKNOWLEDGED_WAITING_FOR_SUBSTANTIVE_RESPONSE`

`stage128-m3i2-final-official-inquiry-human-submission` — **COMPLETE.** A human
supervisor submitted the prepared inquiry **exactly once** through the official
World Bank Data Help Desk *Contact support* channel, category *Data Compilation
Methodology*, with both public attachments visibly selected. It was recorded
under its own explicit one-action human authorization (95 UTF-8 bytes, SHA-256
`4562e480…7978`), which the recording CONSUMED.

* **Acknowledgement received; it is NOT a substantive response.** The
  confirmation page reported the message as received and the confirmation
  e-mail promised a later reply. Neither blocker is resolved.
* **No ticket id.** None was displayed and none was fabricated —
  `ticket_id_present: false`, `ticket_id_redacted: null`,
  `ticket_id_sha256: null`.
* **UTC instant unresolved.** The UI showed `2026-08-06 14:03` with no
  timezone, so `submission_timestamp_utc: null` under
  `UNRESOLVED_CONFIRMATION_UI_DID_NOT_DISPLAY_TIMEZONE`. Only the official
  displayed calendar date `2026-08-06` drives the waiting period.
* **Weak claims kept weak.** Body evidence is
  `CANONICAL_BODY_VISUALLY_CONFIRMED_NOT_RAW_BYTE_VERIFIED`, and the
  attachments were selected but **not** server-enumerated.
* **Raw confirmation is external only.** Three copies (`14060eef…31f6`,
  631,880 bytes; `8841e6ab…1e85`, 383,457 bytes; `dd95e549…6ca9`, 339,376
  bytes) are stored outside the repository; only hashes and sizes are in Git.

**Waiting period ACTIVE.** Business day 1 `2026-08-07`, business day 10
`2026-08-20`, completion **2026-08-20**, earliest possible follow-up
**2026-08-21**. Initial inquiry maximum 1 (used), follow-up maximum 1 and only
under a separate explicit authorization, **automatic follow-up forbidden**, and
any response is ingested and adjudicated only in a **separate**, currently
unauthorized action. Terminal status if it stays insufficient:
`UNRESOLVED_AFTER_FINAL_OFFICIAL_INQUIRY`.

**Open item for the human supervisor.** Wait. Do not reply, resubmit or follow
up. If a substantive response arrives, it needs a new explicit authorization
before anything is read into the repository.

**M3-LAG-WDI-EXPLORATORY is NOT locked.** A local, uncommitted draft of that
exploratory contract was partially materialized before the human supervisor
superseded the path. It produced no data retrieval, Gate, modeling or Final
Test access and never became an authoritative repository contract. It is
quarantined outside the repository and left untouched — not deleted, not
cleaned, not committed — its authorization is consumed and not reusable, and
the authoritative status is `NOT_LOCKED`.

## Predecessor research workstream (HISTORICAL): `stage128-m3i2-official-source-evidence-capture`

The CURRENT workstream is the Stage128 **M3I-2 supplementary international
macro CONTRACT** workstream. A contract lock is **metadata only**: no macro
observation was retrieved, no dataset row was created, no Data Gate ran, no
coverage was computed, no model was fit and no comparison was executed
(`m3i2_data_retrieval_started=false`, `m3i2_data_gate_executed=false`,
`m3i2_modeling_started=false`, `m3i2_block_admitted=false`).

The authoritative research-action pointers are
`last_completed_research_action_id=stage128-m3i2-prospective-contract-lock`
and `next_research_action_id=stage128-m3i2-official-source-evidence-capture`
with `next_research_action_authorized=false` — a pointer is **never** an
authorization.

`stage128-m3-macro-data-gate` is now **predecessor context**, not the current
workstream. Its result is preserved unchanged and is described below as
history; the M3-CBI block remains `UNRESOLVED_M3_DATA_GATE` and unadmitted,
and **M3I-2 does not replace, correct or continue it**.

### Current scientific action

`stage128-m3i2-official-source-evidence-capture` — **COMPLETE**, recorded under
its own explicit one-action human authorization (695 UTF-8 bytes, SHA-256
`eb0230b0…d95b06`, 2026-08-03), which was CONSUMED by the recording. The
authorization names this action and the expected baseline SHA explicitly; it
was **not** inferred from a pointer, a branch name or a prior prompt hash.

**Evidence status: `UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE`.**

What was captured, from official hosts only, in one controlled session
(HTTPS-only, descriptive User-Agent, ≤3 attempts per request, every redirect
recorded):

- **21 objects requested, 21 successful, 1,066,295,643 raw bytes retained and
  hashed.** Nothing was deleted after hashing. The external bundle
  `papermali_stage128_m3i2_official_source_evidence_bundle_v1.zip`
  (1,066,004,147 bytes, SHA-256 `4f47586803d9578024e1be88cc353c59be2fa7d8b0ca4f8e3f6aa5d81e9b481c`,
  24 members) is available for independent handoff; raw bytes are **not**
  committed to Git.
- **37 unique development cutoffs over 539 pairs** — an input-integrity count,
  **never coverage**. Cutoffs came only from
  `project/stage128/stage128_m2_d2_development_features.csv`, reading only pair
  identity, target year and `pair_cutoff_date`. No target, financial, market or
  macro column was read; no final-test directory was searched.
- **110 archive editions discovered** from the official listing; 66 carry a
  day-precision release date, 44 only year+month. A month is not a release
  date, so those can never be a verified pre-cutoff vintage.
- **16 required editions selected value-blind and all 16 captured**, yielding
  **1,878 locked-series rows** for Iran (`IRN`), restricted to
  `FP.CPI.TOTL.ZG` and `PA.NUS.FCRF`, and **32/32 semantic-compatibility rows
  PASS**.

**Why the status is UNRESOLVED.** The earliest verified archive edition is
available at `2017-09-20T00:00:00Z`, but the earliest development cutoff is
`2013-10-22`. **19 of 37 cutoffs — 252 of 539 development pairs — have no
verified pre-cutoff vintage.** That gap is recorded as UNRESOLVED; it is never
turned into zero coverage and never reported as an observed failure.

**Financing.** `NO_EXACT_CANDIDATE_IDENTIFIED_UNRESOLVED_METADATA_LOCK`. M3I-3
stays `UNRESOLVED_METADATA_LOCK`, `admitted=false`, and the merged contract's
null fields were **not** populated. Financing being unresolved does not
invalidate the M3I-2 evidence.

**Unchanged.** `project/stage128/m3_intl_macro_contract_lock/**` is
byte-identical to `cf23771a…0647ff`. M3-CBI stays `UNRESOLVED_M3_DATA_GATE`,
not admitted. Execution audit, all zero: company macro joins, feature
materializations, coverage calculations, Data Gate executions, model fits,
predictions, predictive metrics, Holm calculations, final-test rows read.

**Evidence capture is not admission.** It does not authorize the Data Gate. The
next pointer is `stage128-m3i2-official-source-evidence-review` with
`next_research_action_authorized=false`.

### Predecessor scientific action

`stage128-m3i2-prospective-contract-lock` — **COMPLETE**, recorded once under
its own explicit one-action human authorization (28 UTF-8 bytes, SHA-256
`d4acc969…d23068`, 2026-08-02), which was CONSUMED by the recording. The same
text and hash were used earlier for a **different** action, so the scope of
this occurrence is identified by the preceding assistant message, never by the
hash alone (`scope_identified_by_hash_alone=false`).

What it locked, prospectively and before any value-level work:

- **M3I-2** (supplementary, never confirmatory M3):
  `intl_cpi_inflation_annual` — World Bank WDI `FP.CPI.TOTL.ZG` (upstream IMF
  IFS), annual, percent, transformation `identity`; and
  `intl_fx_change_official_annual` — WDI `PA.NUS.FCRF`, annual, LCU per US
  dollar, transformation exactly `100 * ln(E_y / E_(y-1))` over two
  consecutive annual observations **from the same vintage**, fail-closed to
  null on missing, non-positive, non-consecutive or cross-vintage inputs.
  `PA.NUS.ATLS`, free-market/unofficial rates, aggregators and any post-hoc
  indicator or transformation change are forbidden.
- **M3I-3** financing — a contract **shell** only, against IMF
  `IMF.STA:MFS_IR`. Every operational metadata field is `null`,
  `candidate_selection_status=UNRESOLVED_METADATA_LOCK`, `admitted=false`.
  Deposit rates, deposit-rate ceilings, real rates, spreads, repo /
  reverse-repo volumes, standing-facility amounts and relabelled policy rates
  are forbidden proxies. If no exact IMF series ever passes metadata and
  coverage review, M3I-3 stays unavailable and **M3I-2 is not invalidated**.
- **Observation-year selection inside the vintage** (added by the correction
  of the independent audit of PR #74). Selecting a pre-cutoff WDI archive
  *vintage* does not say which annual *observation* it contributes, so both
  candidates now carry an exact rule: an annual period ends on **December 31
  of the labelled Gregorian observation year**, only a period that finished
  **strictly before** the pair cutoff is eligible, and among eligible years
  the **maximum** is taken (`selected_observation_tie_breaker =
  maximum_observation_year`) — never the first or earliest. A fiscal-year
  label may never be a direct WDI year lookup, no eligible observation yields
  **null**, and no alternative indicator may be tried. For FX the maximum
  eligible year additionally requires `E_y` and `E_(y-1)` present, positive,
  consecutive, same vintage, and same currency denomination and valuation.
- **Historical-vintage semantic compatibility** (added by the same
  correction). The WDI archive warns that one indicator code may have carried
  a different base year or local-currency valuation in earlier releases, and
  that *current* metadata can be shown alongside *archived* data. So
  `historical_archive_metadata_assumed_identical_to_current=false` and
  `semantic_compatibility_evidence_required_before_value_use=true`: per
  edition, a later evidence-capture action must verify the archive edition
  identifier, release date/time, Iran economy identity, indicator code,
  archived series title, annual frequency, unit, calendar-year semantics and
  the raw artifact SHA-256. CPI must stay an annual inflation-**rate** series
  in percent (not an index level or GDP deflator); FX requires one currency
  denomination and one valuation convention across the pair with no
  redenomination or unit break. Any mismatch is
  `null_and_invalid_for_coverage`, an **unverified vintage never counts
  towards coverage**, and no alternative series may be tried after a mismatch.
  Status in this action: `NOT_EXECUTED` — zero archive editions downloaded.
- **Data Gate contract** — thresholds INHERITED unchanged (0.80 candidate
  coverage, 0.70 block common sample, ≥5 positives per locked validation
  window, development-only over the retained-M2 539-row common sample). The
  Gate is `NOT_EXECUTED` and every coverage / common-sample / event-count
  value is `null`, **never zero**.
- **Multiplicity** — the original confirmatory Holm family (`M2_minus_M1`,
  `M3_CBI_minus_M2`, `M4_minus_M3_CBI`) is unchanged and INCOMPLETE, and no
  M3I comparison was inserted into it. A separate supplementary family
  `S1 = M3I_2_minus_retained_M2` / `S2 = M3I_3_minus_M3I_2` is defined; neither
  hypothesis exists yet, and all future M3I results are supplementary /
  robustness only.

Governance (updated after the predecessor merge). **Scientific provenance is
immutable**: this contract was locked against the PR #73 head
`e6db63fb7d105f0d3a39db101c9e364161c367e9` on branch
`stage128-m3-macro-data-gate`, and every protected scientific hash is verified
against that commit permanently — a merge or retarget never moves it, and the
branch was **not** rebased.

**Live PR topology**: PR #73 **was merged** into `main` by merge commit
`b94f73fab99b5c3bc5c55ea7c14736f2bddb516a`, and PR #74 was afterwards
**retargeted to `main`** (`live_pr_base_branch: main`, `live_pr_base_commit` =
`live_main_commit` = `b94f73fa…db516a`, `pr_is_stacked_on_open_predecessor:
false`, `retargeted_to_main_after_predecessor_merge_verified: true`,
`may_target_main: true`). The pre-merge values are retained under
`historical_pre_merge_topology`, marked `superseded` and
`describes_current_state: false`. No artifact still describes PR #73 as open or
unmerged.

The base rule is **state-dependent**, not unconditional: while the predecessor
is open the base must be `stage128-m3-macro-data-gate` with `may_target_main:
false`; once it is merged the base must be `main`, the merge commit must equal
live `main`, and the retarget must be verified. In **both** states PR #74 stays
`live_pr_is_draft: true`, `live_pr_merged: false` and `merge_authorized:
false` — it has **not** been marked ready and **no merge authorization has been
issued**.

Package: `project/stage128/m3_intl_macro_contract_lock/`.

### Predecessor workstream (HISTORICAL): `stage128-m3-macro-data-gate`

The description below was accurate for that completed action and is preserved
as history. The Stage128 **M3 macro DATA** workstream is
started (`m3_data_workstream_started=true`) because the M3 macro data Gate has
been EXECUTED once as a data-admission Gate under its own consumed one-action
authorization, returning `UNRESOLVED_M3_DATA_GATE` and awaiting human review.

**Gate execution is a DATA workstream, not modeling:**
`m3_modeling_started=false`, `m3_incremental_evaluation_authorized=false`,
`m3_block_admitted_for_incremental_evaluation=false`.

The authoritative research-action pointers are
`last_completed_research_action_id=stage128-m2-retained-block-human-decision`
— correctly **unchanged**, because the Gate is unresolved and awaiting human
review — and `next_research_action_id=stage128-m3-macro-data-gate`, a pointer
only; a pointer is **never** an authorization.

`stage128-m2-d2-boundary-month-equity-return` is now
**historical/predecessor context**, not the current workstream; it was correct
while the M2 D2 boundary-month workstream was live.
`stage126-m1-financial-baseline` likewise remains correct **history** for the
completed M1 financial-baseline workstream (see the historical section below).

### Predecessor scientific action (HISTORICAL)

`stage128-m3-macro-data-gate` — the M3 macro **data-admission Gate only**, executed once and terminal at
`UNRESOLVED_M3_DATA_GATE`, pending human review. It asks only whether the exact
frozen three-variable macro block can be obtained from authoritative,
reproducible, point-in-time-safe sources; it does not ask, and does not answer,
whether M3 improves prediction.

### Predecessor scientific action (HISTORICAL)

`stage127-m2-incremental-evaluation` is **historical**, not the current action —
the paired, development-only comparison of the frozen M2 block against the
frozen M1 block, executed exactly ONCE under its own explicit, one-action human
authorization (`بریم مرحله بعد`, SHA-256 `a9999c0c…c3cdc6`, 2026-08-01),
consumed by that execution. The description that follows was accurate for that
completed action and is preserved unchanged as history.

**The mandatory post-lock D2 eligibility audit ran first.** 53 predictor-side
comparisons across 6 dimensions (prediction cohort, industry, firm size,
`zero_trade_day_ratio_W`, market-activity/traded-value diagnostics, M1
predictor availability); 35 carry |SMD| ≥ 0.10. Those are **descriptive flags
only**: no row was removed, no weighting or matching was introduced, and D2,
the Gate, the sample rule and the model design are all unchanged. The flags
limit INTERPRETATION and are recorded in the decision limitations. A separate,
clearly-labelled post-lock distress-rate comparison is descriptive only
(eligible 10.20%, ineligible 10.24%).

**Paired comparison.** The exact three-variable M2 common sample: 539 of 666
development pairs (55 positive / 484 negative; folds 173 / 159 / 332 / 207;
validation positives 18 and 10; pooled locked-validation OOF 366 rows with 28
positives). BOTH blocks were REFITTED on identical common-sample training rows
and evaluated on identical common-sample validation rows — 44 primary
predictive model fits, no tuning, no grid search, no feature search, no SMOTE,
no early stopping. The original 666-row M1 OOF predictions were NOT reused, and
the 666-row M1 results are deliberately NOT compared against these 539-row
results: that comparison would confound sample restriction with model change.

**Observed pooled PR-AUC deltas (M2 − M1)** with paired company-cluster
bootstrap (ticker clusters, 2000 replicates, seed 20260724, 2000/2000 valid,
percentile 95% CI):

- regularized logistic regression: +0.0085 [−0.0212, +0.0353]
- random forest: −0.0073 [−0.0491, +0.0319]
- XGBoost: +0.0188 [−0.0262, +0.0730]

**All three intervals include zero — the observed development evidence is
approximately null.** No new PASS/FAIL threshold was created, no winner was
selected, M2 was neither retained nor rejected, and no superiority or causal
claim is made. The confirmatory family (`M2_minus_M1`, `M3_minus_M2`,
`M4_minus_M3`) is INCOMPLETE: `holm_family_complete = false`,
`holm_final_adjustment_deferred = true`.

The frozen streaming loader read only the row-identity and split fields
required to identify and exclude 346 locked-final-test records. It did not
parse, inspect, store, preprocess, fit on, predict from, evaluate, summarize
or export any final-test predictor or target value. No model was fit on a
final-test row and no full-development refit occurred, and M3/M4 were not
started.

**Live-state note.** The authorized M2 development modeling WAS executed: 44
canonical primary predictive fits. The one-action authorization was CONSUMED,
so `m2_incremental_evaluation_authorized = false` again — that is an
AUTHORIZATION fact and does not mean the modeling never happened.
`m2_started = true`, `m2_modeling_started = true` and
`m2_block_admitted_for_modeling = true` record the execution;
`m2_block_retained = true` with `m2_retained_block_decision_required = false`
records that the human retained-block decision has since been made (see
below); retention is a governance decision and establishes no superiority.

**M2 data state.** The live fields are `m2_market_data_evidence_collected =
true`, `m2_market_data_evidence_validated = true`,
`m2_data_entered_authorized_incremental_modeling_pipeline = true` and
`m2_incremental_evaluation_data_materialized = true`. The frozen Stage125
Part 4 marker `m2_data_collected = false` is **historical schema state**, not
live state: it records what that SAP froze when it was created, flipping it
would be a handoff-mutation violation of a frozen scientific artifact, and it
is republished only under the historical/legacy heading of `CURRENT_STATE.md`
as `stage125_part4_m2_data_collected_historical`.

### What is open now

`stage128-m2-retained-block-human-decision` is **COMPLETE**. Under its own
explicit one-action human authorization (240 UTF-8 bytes, SHA-256
`91edbdedbf69fd3af4ec5a378b1b0506ed4df941f1331be91755068c6fb6e2b4`; the exact
utterance lives only in the package's authorization record), the human
supervisor recorded
`RETAIN_M2_AS_INTERMEDIATE_CONFIRMATORY_BLOCK`, weighing the 127-row
common-sample attrition, the 28 pooled validation positives, the flagged D2
eligibility imbalance (53 comparisons / 35 flags), temporal heterogeneity, the
wide bootstrap intervals and the disagreement in point-estimate sign across
model families.

M2 stays the **intermediate** block of the preregistered nested chain
M1→M2→M3→M4 and the comparator for a future paired `M3 − M2` evaluation —
**only** if the M3 data Gate is separately authorized and passes. This is a
retained-block decision, **not** a superiority decision: the observed
development evidence remains approximately null, and retention implies no
predictive improvement, no statistical significance, no paper winner, no final
model, no full-development refit and no final-test unlock or access. The
confirmatory family stays unchanged and INCOMPLETE, with the final Holm
adjustment deferred. The one-action authorization was CONSUMED by the
recording.

`stage128-m3-macro-data-gate` has now been **EXECUTED once as a
data-admission Gate only**, under its own explicit one-action human
authorization (28 UTF-8 bytes, SHA-256 `d4acc969…d23068`), which was CONSUMED
by that execution. Its observed result is **`UNRESOLVED_M3_DATA_GATE`**.

The Gate answered only whether the exact frozen three-variable macro block can
be obtained from authoritative, reproducible, point-in-time-safe sources. It
did **not** ask, and does not answer, whether M3 improves prediction: 0 model
fits, 0 predictions, 0 predictive metrics, 0 M3-versus-M2 comparisons.

It is UNRESOLVED — not FAILED — because the evidence is insufficient to reach
either PASS or FAIL. Three distinct causes, deliberately not conflated:

1. **Frozen-contract incompleteness.** The frozen Stage125 contracts register
   the three candidate names but do not uniquely determine any candidate's
   official series, transformation, calendar, release-date field, as-of rule or
   revision/vintage policy, so the prospective Phase-A definition lock could not
   be completed.
2. **Official-metadata unavailability.** No independently verifiable official
   Central Bank of Iran documentation or data artifact is committed.
3. **No value-level execution.** Coverage, join, event counts and temporal
   support were never assessed.

**Access-probe evidence is downgraded.** The raw response bodies from the
capture session were not retained, and no headers or stderr logs were captured,
so `access_probe_evidence_status = UNVERIFIED_CAPTURE_METADATA_ONLY`. Only the
targeted URL set (all official `cbi.ir` hosts) is independently verifiable. The
reported WAF / CAPTCHA / non-reproducibility classifications are
**programmer-reported observations, raw bytes unavailable for independent
audit**, and are **not** used as G02/G03/G04 evidence.

It is **not** established that the Gate could not have passed with official
access: official source documentation could potentially have completed the
prospective definition lock. A new human-selected contract is one possible
future route; an authorized, reproducible official CBI documentation and data
package is another.

Missing evidence was recorded as null, was never scored as zero, and was never
converted into an observed failure.

No candidate was dropped or substituted, no smaller block was allowed to pass,
and no non-CBI source (SCI, free-market FX, aggregator, mirror or news) was
used. The CAPTCHA was never solved or bypassed. Phase B never executed.

Because the Gate did not PASS, the research pointer **did not advance**:
`stage128-m3-incremental-evaluation` was **not** created and remains
unauthorized, and `m3_macro_data_gate_human_review_required = true`. M3
modeling remains unauthorized and unstarted; M4 is likewise unauthorized and
unstarted; the final test remains locked.

A precise human decision request is recorded in the Gate decision artifact: it
asks the supervisor either to supply an authorized reproducible official CBI
access path, or to import official CBI artifacts as immutable checksummed raw
evidence, or to freeze each candidate's series identity and transformation
prospectively in a new authorized contract. It is deliberately **not** a menu
this action was permitted to choose from.

`stage128-m2-d2-gate-rerun` is complete — it is the data admission this
evaluation consumed; its terminal result `PASS_FOR_M2_INCREMENTAL_EVALUATION`
(DATA ADMISSION ONLY) is preserved unchanged.
`stage128-m2-boundary-month-return-design-freeze` is complete — it is the
design that Gate executed. `stage127-m2-market-data-gate` is HISTORICAL,
completed and resolved; its terminal result remains `FAIL_M2_DATA_GATE`,
unchanged, in its own Stage127 artifacts.

Authoritative research pointers live in `ROADMAP.md` front matter. PR #72 is
**merged** on `main` (`35aaf4b70e9341704ee38be6f8cf2e2519c70bb2`), so those
pointers are live, not conditional:
`last_completed_research_action_id=stage128-m3i2-prospective-contract-lock`,
`next_research_action_id=stage128-m3i2-official-source-evidence-capture`
(`next_research_action_authorized=false`). The M3-CBI data Gate was executed
and returned `UNRESOLVED_M3_DATA_GATE`; that result is unchanged and still
awaits human review, and the supplementary M3I-2 contract lock neither
resolves it nor replaces it.

## Stage127 M2 market-data Gate — current, truthful state

Human authorization for `stage127-m2-market-data-gate` **already exists** and
covers this action. The Gate was first executed with no data available and
returned `UNRESOLVED_M2_DATA_GATE`. Authoritative TSETMC evidence has since
been obtained externally **under that same Gate scope**, and the Gate has been
re-executed and resolved from it. `stage127-m2-incremental-evaluation` has
since been separately authorized and COMPLETED on the D2 common sample (see the
current-action section above); it is **not** authorized again — that one-action
authorization was consumed.

**Evidence.** The immutable external delivery
`stage127_m2_tsetmc_full_delivery.zip` (SHA256
`d8456b50b7813b44789b556efcdd9ed81ee0318f85e3d9127b27807f75c6c6ec`,
13,464,145 bytes) answers exactly the canonical PR #66 request: 110 instrument
mappings, 111 authorized ranges (105 SUCCESS / 6 PARTIAL / 0 FAILED), 163,230
normalized daily rows spanning 2012-09-22..2020-07-18, and 222 SHA256-verified
restricted raw evidence files. The external QC flag was **not** trusted: the
raw → normalized field mapping was re-verified for every row, and
`adjusted_close` was re-verified against the raw adjusted `pc` on the exact
same trading date, inside this repository. The six PARTIAL ranges were
preserved as delivered — never upgraded, back-filled or widened.

**Gate result: `FAIL_M2_DATA_GATE` — terminal, resolved, and HISTORICAL. The
human review it originally required has been completed** by the separately
authorized `stage128-m2-boundary-month-return-design-freeze` action (see
"Stage128 D2 ... design freeze" below); the historical D0 Gate result remains
`FAIL_M2_DATA_GATE` and is never rewritten.
This is an OBSERVED negative result against the frozen thresholds, not missing
evidence, and it is deliberately not softened into `UNRESOLVED`:

- `realized_volatility` — 576/666 usable, coverage 0.8649 (threshold 0.80) ✓
- `amihud_illiquidity` — 576/666 usable, coverage 0.8649 (threshold 0.80) ✓
- `equity_return_window` — 269/666 usable, coverage **0.4039** (threshold
  0.80) ✗
- three-variable common sample — 269/666, coverage **0.4039** (threshold
  0.70) ✗
- both locked validation windows clear the ≥5-positive rule on the common M2
  sample (fold1_validation 11, fold2_validation 5) ✓
- G01–G08 all PASS; accessibility scored 5, derived from the frozen R-A
  mapping using candidate-level endpoint evidence, provenance and hashes ✓

`ADMITTED_G01_G08_SOURCE_AND_DATA_QUALITY_ONLY` on a candidate means the
source/data-quality gates passed. It is **not** admission into the M2 modeling
path, which additionally requires the frozen 0.80 coverage threshold;
`equity_return_window` has `admitted_into_m2_modeling_path = false`.

**Shared-window end rule (T\*) is applied literally.** `T*` is the last
eligible trading day with verified `available_at` strictly before the pair
cutoff, selected **independently** of whether `adjusted_close` is present. The
frozen CUT-A contract defines `verified available_at` as an availability
timestamp, not as the presence of a price, and `missing_price_rule =
exclude_day_from_window_computations` keeps an unpriced trading day inside W.
The `Require P_t0 and P_tN present` endpoint condition is therefore evaluated
after W is defined and can genuinely fail. Audit: T* is unchanged for 413
pairs and differs for 253 (largest shift 637 days); in all 253 the literal T*
carries no `adjusted_close`. Endpoint causes are reported separately and are
not collapsed: 270 pairs miss `t0`, 253 miss `tN`, 132 miss both, and 90 have
fewer than 126 usable returns / Amihud days.

No threshold was reduced, no value imputed, no unadjusted close substituted,
no T* chosen to improve coverage, and no M2 variable dropped. The frozen
three-variable block was NOT redefined; redefining it would require a separate
explicit human decision. M2 was not automatically redesigned and M3 was not
started.

**Evidence state vs admission state.** M2 market evidence IS collected and
independently validated (`stage127_m2_market_data_evidence_collected=true`,
`..._validated=true`, 163,230 observations). That is recorded **separately**
from admission, which did not occur. `m2_data_collected` remains `false`
because in this schema it is a frozen prohibition marker meaning "M2 data has
entered the authorized M2 modeling pipeline" — it is pinned false by the frozen
Stage125 Part 4 SAP and the Stage126 robustness closure completion lock, and
Stage125 Part 5's successor validator treats flipping it as a mutation
violation. It never means "no M2 evidence exists".

**Reproducibility.** The Gate is now a deterministic OFFLINE/IMPORT path and
requires no network connection:
`python project/run_stage127_m2_market_data_gate.py --build --bundle <path to
stage127_m2_tsetmc_full_delivery.zip>`. Endpoint reachability plays no part in
the decision and can never produce a PASS. The earlier local network-probe
failure remains an environment egress diagnostic only; it is not a property of
TSETMC and no longer has any bearing on the Gate.

**Human review COMPLETED (historical).** The question this Gate raised — how to
respond to the observed `equity_return_window` coverage shortfall — was decided
by the human supervisor, who separately authorized
`stage128-m2-boundary-month-return-design-freeze`. The observed causes remain
recorded in the decision artifact and split by endpoint: 126 pairs fail only the
`t0` endpoint-price requirement, 99 fail only the `tN` (T*) requirement, 132 miss
both, and 90 fall below the 126-observation minimum. Nothing was remediated
inside Stage127 itself, and the historical Gate result is unchanged.

## Stage128 D2 boundary-month equity-return design freeze — current, truthful state (PR #69, unmerged)

`stage128-m2-boundary-month-return-design-freeze` is the **current scientific
action** and a **design-freeze/contract action only** (PR #69, unmerged). It is
the human supervisor's separately authorized answer to the human-review question
raised by the historical Stage127 Gate above. It freezes
`BOUNDARY_MONTH_ASOF_TRAILING_EQUITY_RETURN` (Gregorian calendar convention) as
the new PRIMARY M2 equity-return construct, replacing only the D0
exact-endpoint measurement component. `W`, `t0`, `T*`, trading-day sequence,
daily-return adjacency, the 126-return floor, `realized_volatility` and
`amihud_illiquidity` are unchanged; no fourth primary market feature is added
and `zero_trade_day_ratio_W` remains diagnostic-only. Full contract:
[`STAGE128_M2_D2_DESIGN_FREEZE.md`](STAGE128_M2_D2_DESIGN_FREEZE.md) and
`project/stage128/`.

**Historical D0 result preserved, unchanged.** The Stage127 Gate result above
(`FAIL_M2_DATA_GATE`, `equity_return_window` 269/666) is untouched by this
freeze. This freeze does not rerun that Gate, does not mark it PASS, and does
not admit M2 into modeling.

**Feasibility provenance, reproduced honestly.** D0 (269/666) is independently
reproduced in-repository from the already-committed, target-free
`stage127_m2_development_features.csv` by
`project/stage128/d0_reproduction_and_prelock_feasibility_archival_record.py`.
D1/D2
(Gregorian, 539/666)/D3/the Jalali-boundary diagnostic each require raw
per-day price data that was never committed to this repository (only the
external bundle's SHA256 is referenced); those four counts are recorded as
externally-supplied historical evidence only, explicitly flagged as not
independently re-derived in-repo — no synthetic data was fabricated to
manufacture a fake reproduction. Those counts were transmitted into the
repository by the human supervisor
(`historical_counts_transmitted_by_human = true`); the authorization text is
the transmission channel, not the scientific source of truth. The raw market
bundle (`external_market_bundle_sha256 =
d8456b50b7813b44789b556efcdd9ed81ee0318f85e3d9127b27807f75c6c6ec`) is not
present in the repository, the pre-lock D2 count is **not** independently
verified here
(`prelock_D2_count_independently_verified_in_repository = false`), canonical
confirmation was deferred to `stage128-m2-d2-gate-rerun`, since authorized and
executed,
and the original pre-lock feasibility script/output was not preserved
(`original_prelock_feasibility_script_not_preserved = true`).

**Not authorized by this freeze:** canonical M2 Gate rerun
(`stage128-m2-d2-gate-rerun`), M2 incremental evaluation, model fitting,
prediction generation, final-test access, M3/M4 start, or merge of PR #69
without a later, separate, explicit authorization. See
`project/stage128/stage128_m2_d2_human_authorization_record.json` for the
exact authorization scope and
`project/stage128/stage128_m2_d2_design_freeze.json` for the full
machine-readable record.

Part 3B.1 / 3B.1A / 3B.1B / 3B.1C remain historical **maintenance** locks;
Part 3B.1E is the decision-lock surface for the conservative-lag research
action; Part 3C is the operationalization / leakage-safe dataset surface;
Part 4 is the statistical analysis plan lock (no modeling);
Part 5 is the Stage125 readiness closure (Gate 125.0; Stage126 entry contract
as readiness-only at closure time).

### Completed — `stage124-gate-b-rule-approval`

**Approved.** The user/data owner explicitly approved the final Gate B listing
rules (supported by the readiness comparison; no external reviewer claimed):

- **Rule A (primary):** `first_observed_trading_date <= fiscal_year_end`
- **Rule B (listing-timing robustness):** `first_observed_trading_date <= fiscal_year_start`
- **Rule C rejected:** `first_observed_trading_year < fiscal_year`

Record: `project/stage124/gate_b_final/gate_b_rule_approval_stage124.json` and
`README_GATE_B_RULE_APPROVAL.md`.

### Completed — `stage124-gate-b-execution`

**Gate B executed.** The approved rules were applied to the frozen Stage123 data
and the verified listing master (1331 company-year rows, 1200 t→t+1 pairs, 130
tickers). Four sample designs:

- **main_rule_a_primary** — 1013 eligible (81 pos / 932 neg)
- **main_rule_b_listing_robustness** — 994 eligible (80 pos / 914 neg)
- **expanded_rule_a_company_scope_robustness** — 1057 eligible (81 pos / 976 neg)
- **expanded_rule_b_combined_robustness** — 1036 eligible (80 pos / 956 neg)

Unresolved listing rows: Rule A = 4, Rule B = 10 (preserved explicitly, never
zero-filled). Outputs in `project/stage124/gate_b_final/` (large canonical +
filtered CSVs gitignored/hashed; small audit CSVs, QC, metadata, README tracked).
58 focused tests (`project/tests/test_stage124_gate_b_execution.py`); 736 passed,
1 skipped in the full suite (local results — no GitHub Actions configured).
**No modeling started.**

### Completed research action — `stage125-part3b-conservative-lag-decision-lock`

Human supervisor approved a **fixed conservative six-calendar-month**
availability lag. Deliverables / QC surface:
`stage125-part3b1e-conservative-six-month-lag-decision-lock`. Researcher-verified
financial data are **frozen** (no re-extraction). Broad CODAL metadata and
financial-statement capture are **stopped**. PR #47 was closed **unmerged**
(superseded; branch retained). Assumed availability uses
`assumed_available_at_conservative = fiscal_year_end + 6 calendar months` and
must never be written as observed `PublishDateTime` / `available_at`. Predictors
from year **t** may only predict distress target **t+1**. Stage125 remains
**incomplete**; Stage126 and modeling remain unstarted.

### Completed research action — `stage125-part3c-leakage-safe-dataset-finalization`

Audited pair datasets and timing-eligible leakage-safe analysis-ready
datasets finalized for all four locked Gate B sample designs under the
**active four-Jalali-calendar-month regulatory lag** (human-approved
revision; six-month active methodology superseded; Part 3B.1E six-month
decision retained as historical provenance). Full Gate B membership is
preserved on the audited surface; analysis-ready outputs include only rows
where `assumed_available_at_regulatory < target_fiscal_year_end_t_plus_1`
(general rule; `رمپنا|1396` → `رمپنا|1397` remains audit-only). Financial
values and targets remain frozen copies. Assumed availability uses
`assumed_available_at_regulatory` only (not observed `PublishDateTime` /
`available_at`). Part 3C does **not** approve model features — candidates
remain pending Part 4. Bulky outputs are gitignored and hashed. **Do not**
start Stage126 or modeling. **Do not** resume broad CODAL capture or
row-level PublishDateTime collection.

### Completed research action — `stage125-part4-statistical-analysis-plan`

Statistical analysis plan locked for all four analysis-ready samples under
the active four-month regulatory lag. Active contract:
`stage125_part4_sap_v2`. Primary paper result uses
`main_rule_a_primary` × `FD_target_main_t_plus_1`. M1 primary feature order
(9 admitted), M1 coverage-audit candidates (10; `revenue_growth_period_adjusted`
rejected at Fold 1 train coverage `148/245 = 0.6040816327`), M1
target-proximity robustness (6), nested M2–M4 blocks (9/12/15/19), temporal
folds (development 1393–1399; final test 1400–1402), strict
positive/negative/missing event accounting, pre-imputation missingness-mask
preprocessing, SMOTE without class weighting, model families, finite
hyperparameter budget (32 configs/block), seeds, PR-AUC primary,
Recall@10%/Lift@10%, calibration, paired ticker-cluster bootstrap, Holm, and
SHAP stability contracts are frozen. Part 3C hashes pinned. **No** model
fitting, **no** final-test predictor inspection, **no** M2/M3/M4 data
collection, **no** Stage126. Article-141-only final test (1 positive on
primary sample) is distributional/descriptive robustness only.

### Completed research action — `stage125-part5-readiness-closure`

Stage125 readiness closure / Gate 125.0. Keep/drop/defer decisions recorded;
blocker register classified; Stage126 M1 entry contract written as
**readiness for a future authorization decision only** at Stage125 closure
time (historical state at Stage125 closure time: Stage126 unauthorized;
modeling unstarted; final test locked). Part 3C and Part 4 hashes unchanged.
**No** model fitting, predictions, SHAP, SMOTE, or final-test predictor
inspection in Part 5 itself.

### Historical (completed) — `stage126-m1-financial-baseline`

Stage126 M1 human-authorized = true
Stage126 started = true
development modeling authorized = true
modeling started = true
primary development tuning completed = true

M1 robustness started = true
M1 robustness completed = true
full-development refit performed = false

final test unlocked = false
final-test access authorized = false
final-test predictor values inspected = false
final-test target values inspected = false
final-test evaluation performed = false

M2/M3/M4 data collected = false

Primary M1 development-fold tuning is completed on PR #52. All six
registered M1 robustness categories (Parts 1-6) are now complete. Full-
development refit, retained-design freeze and final test remain out of scope
until separately authorized; the next research action,
`stage126-m1-robustness-closure`, synthesizes the six robustness results.

**Robustness Part 0 decision lock (maintenance; 2026-07-22):** the additive
robustness execution contract (`stage126_m1_robustness_execution_contract_v1`)
is locked — six categories in binding order, one factor at a time, all three
model families, no retuning (reuse primary selected configurations), two locked
development folds, fixed metric list, SMOTE/SMOTENC training-fold-only rules, and
one-category-per-micro-part packaging. This is a **decision lock only**: it
authorizes **no** robustness execution and **Part 1 is not started**. Handoff
markers: `m1_robustness_decision_locked=true`,
`m1_robustness_execution_authorized=false`,
`m1_robustness_started=false`,
`m1_robustness_next_category_id=m1_target_proximity_six_feature_set`,
`m1_robustness_packaging_policy=one_category_per_micro_part_pr`. Each future Part
requires a separate explicit human authorization; primary Stage126 artifacts are
byte-identical and the final test remains locked.

**Robustness Part 1 — COMPLETED (2026-07-22):** `m1_target_proximity_six_feature_set`
was explicitly human-authorized and executed on the development folds only.
**Only the feature set changed** (six-feature `M1_TARGET_PROXIMITY_ROBUSTNESS`,
12 transformed columns); sample, target, folds, selected configurations,
imbalance policy, seeds and metrics were held fixed. **No retuning** (0 tuning
searches; exactly 22 fits / 22 predictions), **no full-development refit**, and
the **final test remains locked and untouched** (0 predictor rows, 0 target
rows, 0 evaluations). No SMOTE/SMOTENC/SHAP/calibration/bootstrap/Holm; zero
network. Outputs: 1263 OOF rows (421 per family) and 9 metric rows. **Part 1 is
sensitivity-analysis evidence only** and did not replace the primary results or
select a paper winner. Handoff markers: `m1_robustness_started=true`,
`m1_robustness_part1_completed=true`,
`m1_robustness_completed_category_ids=["m1_target_proximity_six_feature_set"]`,
`m1_robustness_next_category_id=main_rule_b_listing_robustness`,
`m1_robustness_part2_authorized=false`,
`m1_robustness_execution_authorized=false`, `m1_robustness_completed=false`.

**Observed ordering sensitivity (reported; primary claims unchanged):** primary
pooled PR-AUC ordering is **Logistic > RF > XGBoost**; the Part 1 observed pooled
PR-AUC ordering is **XGBoost > RF > Logistic**, and **all three pooled PR-AUC
values declined**. The observed Part 1 sensitivity ordering differs from the
primary development ordering. This is a **development-only sensitivity finding**
— it does not change the locked primary ordering used for confirmatory
interpretation, does not replace the primary results, does not change selected
configurations and selects no paper winner. It is recorded in
`stage126_m1_robustness_part1_primary_comparison.json` and reported to the human
supervisor; no automatic scientific action was triggered. Handoff markers:
`m1_robustness_part1_ordering_instability_reported=true`,
`m1_primary_claim_ordering_preserved=true`.

**Successor-test-hash divergence (explicit and bounded):** the successor-aware
Part 5 test file intentionally differs from the hash pinned in the frozen Part 5
metadata; both hashes are recorded. Replaying the frozen Part 5 build against it
differs in **exactly two** self-describing bookkeeping files
(`stage125_part5_readiness_closure_qc_report.json`,
`metadata_and_hashes_stage125_part5.json`) while **every Part 5 scientific
artifact remains byte-identical**. Authorized successor-test evolution — not a
Stage125 scientific-artifact mutation.

**Validation-architecture boundary lock (2026-07-23; decision SHA-256
`8231bbf8704d3128cce6a7f2cc40a33af8e7fe7730b2c4575997330cafb21ac1`):** Stage125
Part 5 is a **frozen historical closure** and is **no longer responsible for
validating live Stage126 successor state**. The **independent Stage126
current-state validator** is the **sole current-state validation surface**:

```bash
python project/run_stage126_current_state_validator.py --check
python project/run_stage126_m1_robustness_part2_listing_rule_b.py --check
python project/scripts/validate_ai_handoff.py --check
PYTHONPATH=project python -m pytest project/tests -q
```

Current state is derived **generically** — completed prefix
`execution_order[:n]`, next category `execution_order[n]`, last micro-part from
the newest completion lock — so a future Part 3 advances state by adding only
its own package. Closed Part 1 and Part 2 packages (scientific **and**
verification-only artifacts, plus source/runner/tests) are pinned in
`stage126_closed_part_registry.json` and fail validation on byte drift. The
Handoff reports current-state validation and the newest scientific micro-part QC
as two separate, explicit roles.

`run_stage125_part5.py --check` is **not** a routine gate, and previous
robustness runners are not current-state gates — previous scientific artifacts
are protected by immutable hashes. Future robustness parts must **not**
regenerate previous-part verification artifacts unless a genuine scientific
error **and** a separate explicit human authorization exist; reopening a
completed part is forbidden by default. This decision authorized no merge, no
Part 3, no refit, no final-test access and no new scientific execution.

**Frozen Part 5 live-successor boundary (historical provenance only; not a
failure):** Stage125
Part 5 remains a **frozen, valid historical closure** — no Stage125 artifact or
source was modified. Its embedded live-Handoff successor check terminates at the
earlier primary-development state. The full frozen Part 5 runner exits 1 first with the inherited `readiness_surface_disagreement` during a live-successor rebuild. Separately, direct `validate_actual_handoff` returns exactly the documented five-field historical successor mismatch (`m1_robustness_started`, `selected_qc_scope`, `selected_qc_path`, `contract_version`, `last_completed_micro_part`) with no forbidden fields. Neither behaviour was introduced by Part 2, and no Stage125 scientific artifact changed.
The **committed** frozen closure report still records `all_gate_pass=true`,
`stage125_gate_125_0=PASS` and `stage126_m1_entry_ready=true`; the failed gate
exists only inside the runner's transient live rebuild. This is an expected
inherited historical-validator boundary, explicitly recorded in
`stage126_m1_robustness_part1_part5_successor_compatibility.json` and
`stage126_m1_robustness_part2_part5_successor_compatibility.json`, asserted in
the Part 1 and Part 2 QC reports and covered by dedicated fail-closed tests
that run the real runner (no stub). It is **not** a scientific
failure, **not** Stage125 drift, and **not** a Part 1 blocker. Part 1 successor
state is validated by the Part 0 integrity controls, the Part 1 QC, the Part 1
completion lock and the AI Handoff validator. Handoff markers:
`stage125_part5_frozen_artifacts_verified=true`,
`stage125_part5_live_successor_check_applicable=false`,
`stage125_part5_successor_compatibility_status=expected_historical_contract_boundary_after_completed_robustness_micro_part`
(generic: the boundary is a property of having completed ANY robustness
micro-part, not of Part 1 specifically).

**Robustness Part 2 — COMPLETED (2026-07-23):** `main_rule_b_listing_robustness`
was explicitly human-authorized and executed on the development folds only.
**Only the sample changed** — from `main_rule_a_primary` to the listing-timing
robustness sample `main_rule_b_listing_robustness`
(`analysis_ready_main_rule_b_stage125.csv`, SHA-256 `5492cf24…`). The target
(`FD_target_main_t_plus_1`), the nine-feature `M1_PRIMARY_FEATURE_ORDER` set (18
transformed columns), the three primary selected configurations, the two locked
folds, the imbalance policy, the seeds and the metric contract were held fixed.
**No retuning** (0 tuning searches; exactly 22 fits / 22 predictions), **no
full-development refit**, and the **final test remained locked and untouched**
(338 identities counted but never parsed; 0 predictor rows, 0 target rows, 0
evaluations). No SMOTE/SMOTENC/SHAP/calibration/bootstrap/Holm; zero network.
Counts: 993 Rule B rows (117 companies, 79/914), 655 development rows (68/587),
fold roles 242 / 202 / 444 / 211, 1239 OOF rows (413 per family), 9 metric rows.
Handoff markers: `m1_robustness_part2_human_authorized=true`,
`m1_robustness_part2_completed=true`,
`m1_robustness_completed_category_ids=["m1_target_proximity_six_feature_set",
"main_rule_b_listing_robustness"]`,
`m1_robustness_next_category_id=expanded_rule_a_company_scope_robustness`,
`m1_robustness_part3_authorized=false`,
`m1_robustness_execution_authorized=false`, `m1_robustness_completed=false`.

**Rule A vs Rule B sample delta (row identities only):** Rule B keys are a
**strict subset** of Rule A keys — 19 Rule A-only rows, 0 Rule B-only rows. Net:
−19 rows, −2 companies, −1 positive, −18 negative; −11 development rows (0
positive); −8 OOF validation rows (0 positive); −8 final-test identities.
Aggregate final-test counts were read only from the frozen
`part4_event_count_gate_stage125.csv`, never from row-level final-test values.
Recorded in `stage126_m1_robustness_part2_sample_delta.csv`.

**Part 2 observed ordering (reported; primary claims unchanged):** pooled
development-OOF PR-AUC — Logistic 0.447170 (+0.32%), RF 0.401263 (−0.29%),
XGBoost 0.341960 (−4.09%). The **observed Part 2 ordering (Logistic > RF >
XGBoost) matches the primary development ordering**, unlike Part 1's. This
remains **sensitivity evidence only**: it does not replace the primary results,
does not alter the locked primary confirmatory ordering, does not change
selected configurations and selects no paper winner. Recorded in
`stage126_m1_robustness_part2_primary_comparison.json`; handoff markers
`m1_robustness_part2_sample_sensitivity_reported=true`,
`m1_robustness_part2_ordering_differs_from_primary=false`,
`m1_primary_claim_ordering_preserved=true`. The Part 1 ordering-instability
markers are retained unchanged.

**Part 1 preservation:** all seven Part 1 scientific artifacts (authorization
record, feature manifest, execution manifest, OOF predictions, metrics,
completion lock, primary comparison) are byte-identical after Part 2. Only three
**verification-only** Part 1 files were refreshed — the QC report, the metadata
manifest and the Part 5 compatibility record — because they embed the current
successor-test-file hash. No Part 1 model was retuned; no Part 1 probability or
metric changed.

**Successor-test hash history after Part 2 (three generations):** the Stage125
historical hash `0a117c19…` still pinned by the frozen Part 5 metadata, the Part
1 completion-time hash `62cd1593…` (**history — never the current hash**), and
the recomputed Part 2 current hash. All three are recorded separately in
`stage126_m1_robustness_part2_part5_successor_compatibility.json`.

**Robustness Part 3 — COMPLETED (2026-07-23):**
`expanded_rule_a_company_scope_robustness` was explicitly human-authorized
(423-byte text, SHA-256 `f1230aa0…`) and executed on the development folds only,
from base `main` `6412b45c`. **Only the company-scope sample changed**
(`analysis_ready_expanded_rule_a_stage125.csv`, SHA-256 `fbe9b29c…`). Target,
nine-feature order, preprocessing, missingness-indicator logic, selected
configurations, folds, seeds, metrics and class weighting all unchanged.
**No retuning** (0 searches; 22 fits / 22 predictions), **no full-development
refit**, and the **final test remained locked** (361 identities counted only via
the frozen split contract; 0 predictor rows, 0 target rows, 0 predictions, 0
metrics). No calibration, threshold optimization, bootstrap, Holm, p-values,
winner selection, SMOTE/SMOTENC or SHAP. Counts: 1056 rows / 124 companies /
80 pos / 976 neg; development 695 (68 / 627); folds 254 / 215 / 469 / 226;
1323 OOF rows (441 per family); 9 metric rows. Handoff markers:
`m1_robustness_part3_human_authorized=true`,
`m1_robustness_part3_completed=true`,
`m1_robustness_completed_category_ids=[part1, part2, part3]`,
`m1_robustness_next_category_id=expanded_rule_b_combined_robustness`,
`m1_robustness_part4_authorized=false`,
`m1_robustness_execution_authorized=false`, `m1_robustness_completed=false`.

**Part 3 sample delta (row identities only):** Expanded Rule A is a **strict
superset** of primary Rule A — 44 expanded-only rows, 0 primary-only rows, +5
companies, +0 positive, +44 negative; +29 development rows (all negative); folds
+9 / +10 / +19 / +10; 20 added OOF identities, **all target 0**; +15 final-test
identities.

**Part 3 results (development-only sample sensitivity):** pooled PR-AUC —
Logistic 0.442886 (−0.64%), RF 0.390702 (−2.92%), XGBoost 0.356561 (+0.00%).
**The locked primary ordering Logistic > RF > XGBoost is preserved**; the largest
absolute change is 0.0117. Because the additions are negative-only, the expanded
company scope does **not** materially change interpretation. Primary results were
not replaced, the primary ordering lock is unchanged and no paper winner was
selected. A separated descriptive Part 2 comparison is recorded without
multiplying claims or selecting a preferred robustness sample.

**Live-versus-historical test boundary (2026-07-23):** the frozen Stage125
Part 5 file contains historical tests explicitly marked `live_successor_state`.
Those tests remain **byte-identical** and are verified against the frozen Part 2
successor reference commit `6412b45c4adc6584a5567c7c96e0932f68f31e8a` by
`project/run_stage125_part5_historical_successor_tests.py`. **They are not part
of the current Stage126 live gate.** The default suite

```bash
PYTHONPATH=project python -m pytest project/tests -q
```

excludes only that historical marker (2472 selected / 9 deselected of 2481
collected; 2471 passed, 1 skipped, 9 deselected, 0 failed); **all
non-historical tests remain active**, including the rest of the frozen Part 5
file. Exclusion is by marker expression only — no file ignore, node ID, skip,
xfail or collection hook — and that narrowness is proven by
`test_stage126_live_historical_test_boundary.py`. The Stage126 current-state
validator remains the sole current-state validation surface. This is a
consistent application of the existing validation-architecture boundary lock,
**not** a scientific-error exception; Stage125 Part 5 was neither reopened nor
re-pinned.

**Robustness Part 4 — COMPLETED (2026-07-24):**
`expanded_rule_b_combined_robustness` was explicitly human-authorized
(418-byte text, SHA-256 `e40852d9…`) and executed on the development folds
only, from base `main` `853a8def…`. **Only the combined Rule B sample
changed** (`analysis_ready_expanded_rule_b_stage125.csv`, SHA-256
`2e61a282…`). Target, nine-feature order, preprocessing, missingness-indicator
logic, selected configurations, folds, seeds, metrics and class weighting all
unchanged. **No retuning** (0 searches; 22 fits / 22 predictions), **no
full-development refit**, and the **final test remained locked** (353
identities counted only via the frozen split contract; 0 predictor rows, 0
target rows, 0 predictions, 0 metrics). No calibration, threshold
optimization, bootstrap, Holm, p-values, winner selection, SMOTE/SMOTENC or
SHAP. Counts: 1035 rows / 122 companies / 79 pos / 956 neg; development 682
(68 / 614); folds 250 / 211 / 461 / 221; 1296 OOF rows (432 per family); 9
metric rows. Handoff markers: `m1_robustness_part4_human_authorized=true`,
`m1_robustness_part4_completed=true`,
`m1_robustness_completed_category_ids=[part1, part2, part3, part4]`,
`m1_robustness_next_category_id=persistent_loss_robustness_target`,
`m1_robustness_part5_authorized=false`,
`m1_robustness_execution_authorized=false`, `m1_robustness_completed=false`.

**Part 4 sample delta (row identities only, three independent comparisons):**
versus Part 2 (main Rule B) — Part 4 is a **strict superset**: 42 Part4-only
rows, 0 Part2-only rows, +5 companies, +0 positive, +42 negative; +27
development rows (all negative); 19 added OOF identities (all target 0); +15
final-test identities. Versus Part 3 (expanded Rule A) — Part 4 is a **strict
subset**: 21 Part3-only rows, 0 Part4-only rows, −2 companies, −1 positive,
−20 negative; −13 development rows (all negative); 9 removed OOF identities;
−8 final-test identities. Versus the locked primary Rule A sample — **neither**
a subset nor a superset: 42 Part4-only rows, 19 primary-only rows, net +23
rows, +3 companies, −1 positive, +24 negative; development net +16 (27
Part4-only / 11 primary-only, all differences negative); OOF net +11 (19 / 8);
final-test net +7 (15 / 8).

**Part 4 results (development-only sample sensitivity):** pooled PR-AUC —
Logistic 0.444984 (−0.17%), RF 0.396419 (−1.50%), XGBoost 0.355211 (−0.37%).
**The locked primary ordering Logistic > RF > XGBoost is preserved.**
Development-fold and pooled-OOF identity differences versus primary, Part 2
and Part 3 are all target-0; at the frozen full-sample aggregate level,
however, Part 4 has one fewer positive event than Part 3 and primary
(frozen final-test positive counts 11 (Part 4) vs 12 (Part 3) vs 12
(primary), no row-level final-test target accessed). Because the pooled
development-OOF ordering is preserved and the PR-AUC changes remain small,
the combined sample does **not** materially change interpretation. Primary
results were not replaced, the primary ordering lock is unchanged and no
paper winner was selected. Separated descriptive Part 2 and Part 3 comparisons
are recorded without multiplying claims or selecting a preferred robustness
sample.

**Robustness Part 5 — COMPLETED (2026-07-24):**
`persistent_loss_robustness_target` was explicitly human-authorized (512-byte
text, SHA-256 `e00b43d8…`) and executed on the development folds only.
**Only the target changed** (to `FD_target_persistent_loss_robustness_t_plus_1`);
the primary `main_rule_a_primary` sample, nine-feature set and selected
configurations are unchanged, so sample and OOF identity sets are byte-for-byte
the primary M1 sets. No retuning (0 searches; 22 fits / 22 predictions), no
full-development refit; XGBoost `scale_pos_weight` per training fold fold1
203/42 = 4.833333333333, fold2 378/72 = 5.25. Counts: 1012 rows / 119 companies
/ 100 pos / 912 neg; development 666 (85 / 581); folds 245 / 205 / 450 / 216;
1263 OOF rows; 9 metric rows. Development-only target transitions (primary →
persistent-loss): 0→0 = 581, 0→1 = 17, 1→0 = 0, 1→1 = 68 (net +17). Final test
locked: 346 identities counted via the frozen split contract only; 0 predictor
rows, 0 target rows, 0 predictions, 0 evaluations; sole final-test information
is the frozen event-count gate aggregate (persistent-loss 15 / 331 versus
primary-target 12 / 334), no row-level final-test target accessed. Pooled
PR-AUC: Logistic 0.508761, RF 0.500501, XGBoost 0.441492; **the locked primary
ordering Logistic > RF > XGBoost is preserved**. Development-only secondary
target-robustness evidence: primary target/metrics/ordering unchanged, no
winner selected, persistent-loss target not multiplied across other samples.
Part 5 QC 134 assertions / 0 failed; current-state validator 77 / 0.
`closed_part_count=5`; `m1_robustness_next_category_id=smote_training_fold_only_robustness`;
`m1_robustness_part5_completed=true`; `m1_robustness_part6_authorized=false`.

**Robustness Part 6 — COMPLETED (2026-07-25):**
`smote_training_fold_only_robustness` was explicitly human-authorized
(696-byte text, SHA-256 `4a3bb0d7…`) and executed on the development folds
only. **Only the imbalance strategy changed** — from primary class
weighting to SMOTENC applied strictly inside each training fold, with class
weighting disabled (XGBoost `scale_pos_weight=1`); the primary
`main_rule_a_primary` sample, target (`FD_target_main_t_plus_1`),
nine-feature `M1_PRIMARY_FEATURE_ORDER` set, selected configurations, folds
and seeds are all unchanged, so the development and pooled-OOF identity sets
are byte-for-byte the primary identity sets. SMOTENC ran on the training
fold matrix (9 continuous features + 9 binary missingness indicators = 18
columns; categorical indices `[9,10,11,12,13,14,15,16,17]`; sampler
`random_state=20260725`; `k_neighbors=min(5, minority_count-1)=5` both
folds): fold 1 training rows went from 33 positive / 212 negative to 212
positive / 212 negative (179 synthetic, 424 total); fold 2 from 58 positive
/ 392 negative to 392 positive / 392 negative (334 synthetic, 784 total).
Validation and the final test were **never resampled** (0 validation
resamplings; 0 final-test rows accessed). **No retuning** (0 tuning
searches), **no full-development refit**, and the **final test remained
locked** (346 identities counted only via the frozen split contract; 0
predictor rows, 0 target rows, 0 evaluations). No calibration, bootstrap,
Holm, p-values, threshold optimization, winner selection or SHAP. Pooled
development-OOF PR-AUC: Logistic 0.443221 (−0.0025 vs primary), RF 0.370841
(−0.0316 vs primary), XGBoost 0.301969 (−0.0546 vs primary) — **all three
families declined** versus primary class weighting, but **the locked
primary ordering Logistic > RF > XGBoost is preserved**. This is
development-only imbalance-strategy sensitivity evidence: it does not
replace the primary class-weighted results, does not constitute a new
confirmatory model comparison, and selects no paper winner. Part 6 QC 148
assertions / 0 failed. Handoff markers:
`m1_robustness_part6_human_authorized=true`,
`m1_robustness_part6_completed=true`,
`m1_robustness_completed_category_ids=[part1, part2, part3, part4, part5,
part6]`, `m1_robustness_next_category_id=` (none — Part 6 is the sixth and
final registered category), `m1_robustness_completed=true`,
`m1_robustness_execution_authorized=false`. **This closes the six-category M1
robustness set.** The next research action, `stage126-m1-robustness-closure`,
synthesizes the six results; it does **not** itself authorize retuning,
retained-design freeze, full-development refit or final-test access.

Historical Part 3B / 3B.1x notes (retained): origin probes and five-row
document-binding evidence remain as frozen scientific history; they do **not**
authorize expansion. 80-row scale-up is cancelled. Part 3B expansion disposition
is `superseded_not_required_for_stage125_closure` (`part3b_completed=false`).

### Historical markers — Stage125 Part 5 closure
(historical state at Stage125 closure time; not the current repository state)

At Stage125 closure the Handoff markers were:

- `broad_codal_capture_stopped=true`
- `financial_data_researcher_verified_frozen=true`
- `active_availability_method=fixed_regulatory_lag`
- `active_availability_lag_months=4`
- `four_month_regulatory_lag_locked=true`
- `six_month_lag_superseded=true`
- `historical_six_month_decision_retained=true`
- `row_level_publish_datetime_collection_required=false`
- `conservative_six_month_lag_decision_locked=true` (historical Part 3B.1E)
- `part3b_started=true`; `endpoint_probe_evidence_collected=true`
- `part3b1_decision_locked=true`
- `cut_a_available_at_operationalization_locked=true` (historical observed-PublishDateTime contract; collection not authorized for modeling path)
- `predictor_document_binding_mini_pilot_completed=true`
- `predictor_document_binding_evidence_collected=true`
- `document_binding_resolution_decision_locked=true`
- `predictor_available_at_evidence_collected=false`
- `pilot_cutoff_provenance_resolved=false`
- `candidate_value_evidence_collected=false`
- `pair_level_evidence_collected=true` (Part 3C leakage-safe pair construction)
- `data_value_extraction_performed=false`
- `accessibility_scoring_applied=false`
- `part3b_completed=false`
- `part3c_leakage_safe_finalization_completed=true`
- `part4_statistical_analysis_plan_locked=true`
- `stage125_part5_readiness_closure_completed=true`
- `stage125_completed=true`
- `stage126_m1_entry_ready=true`
- `stage126_authorized=false` (historical state at Stage125 closure time)
- `stage126_started=false` (historical state at Stage125 closure time)
- `modeling_authorized=false` (historical state at Stage125 closure time)
- `modeling_started=false` (historical state at Stage125 closure time)
- `final_test_unlocked=false`

### Current Stage126 markers (must match Handoff)

- `broad_codal_capture_stopped=true`
- `financial_data_researcher_verified_frozen=true`
- `active_availability_method=fixed_regulatory_lag`
- `active_availability_lag_months=4`
- `four_month_regulatory_lag_locked=true`
- `six_month_lag_superseded=true`
- `historical_six_month_decision_retained=true`
- `row_level_publish_datetime_collection_required=false`
- `part3b_completed=false`
- `part3c_leakage_safe_finalization_completed=true`
- `part4_statistical_analysis_plan_locked=true`
- `stage125_completed=true`
- `stage126_m1_entry_ready=true`
- `stage126_authorized=true`
- `stage126_started=true`
- `development_modeling_authorized=true`
- `modeling_authorized=true`
- `modeling_started=true`
- `m1_primary_development_tuning_completed=true`
- `m1_robustness_started=true`
- `m1_robustness_completed=true`
- `final_test_unlocked=false`
- `final_test_access_authorized=false`
- `final_test_predictor_values_inspected=false`
- `final_test_target_values_inspected=false`
- `final_test_evaluation_performed=false`
- `m2_data_collected=false`
- `m3_data_collected=false`
- `m4_data_collected=false`

**Still prohibited without a separate explicit authorization:**

- final-test access or evaluation
- full-development refit
- retained-design freeze
- M2/M3/M4 data collection or modeling
- SHAP
- calibration, bootstrap, Holm, threshold optimization, paper-winner selection
- network extraction
- expanded CODAL/TSETMC/CBI network for value extraction
- row-level PublishDateTime collection
- real observed available_at assignment
- 80-row / 130-company CODAL scale-up
- Part 3B.2

**Part 0 (done — documentation lock):** baseline after PR #20 confirmed;
research contract recorded in human docs; Handoff regenerated by the generator;
validator + tests green; PR opened. **PR #21 is now MERGED** (`main` merge commit
`d39e770ff49729a2f0b1b0262c0b1aa5ae41b0c4`). Part 0 is CLOSED.

**Part 1 (completed and merged):** Data Dictionary & Provenance Contract. Contracts / read-only-audit only; tracked as maintenance task
`stage125-part1-data-contract` (advances no research action). Deliverables in
`project/stage125/`: M1–M4 data dictionary, identifier/time contract, source
registry (M1–M4 only, no M5), provenance manifest schema, data-admission-gate
template, immutable raw/cache policy, and a read-only M1 provenance-gap audit
(rows 1331; source_file missing 28; source_url missing 1316; fiscal_year_end
missing 4; company_name missing 7; industry missing 29; audit_status_unknown
316). Empty `source_url` is a provenance gap only — no eligibility change, no row
drop, no gap filled, no value guessed.

**Part 2 (completed and merged):** Prediction-time & Leakage Contract. Contract / read-only-audit only; tracked as maintenance task
`stage125-part2-prediction-time-contract` (advances no research action).
Deliverables in `project/stage125/`: prediction-time contract (cutoff based on
verified `available_at`; revision policy; deterministic tie-breaking); feature
availability contract (M1–M4 temporal gating; no target-year features); leakage
checklist (8 machine-testable fail-closed checks LC01–LC08); per-pair
cutoff/feature/leakage audit CSVs preserving all 1200 pairs; cutoff summary.
Missing `fiscal_year_end` (4 predictor, 4 target; 5 pairs either missing, 3 both
missing) is never filled or guessed — those pairs have
`temporal_status=unresolvable`. `eligibility_impact=none_contract_audit_only` for
every pair. No pair is dropped. `modeling_started` remains `false`;
`part2_started=true` (contract only, not modeling); no network extraction.

**PR #27 post-merge Handoff refresh — MERGED** (`main` merge commit
`c6cbb6b7a7dc4dfe7ca3fa6ea0bcf34d7f0612c0`). Part 1 and Part 2 are CLOSED.

**Part 3A (completed and merged):** Accessibility, Coverage & Event Pilot
Protocol Lock. Protocol / inventory freeze only; tracked as maintenance task
`stage125-part3a-pilot-protocol-lock` (advances no research action).
PR #29 **MERGED** (`main` @ `4e15cb7…`). Locks the 10 registered M2–M4
candidates, proposed accessibility rubric (not yet applied), gate decision
protocol (8 locked Gates + 6 pending thresholds), sampling frame from frozen
Gate B data, pilot-size options for later approval, and Part 3B evidence
manifest schema. **No** evidence collection, **no** network access, **no**
accessibility scores assigned, **no** candidate admitted.
`part3a_protocol_locked=true`; `modeling_started` remains `false`;
`part3b_started=false`. Part 3A protocol assets are **frozen**.

**Part 3A.1 (completed and merged):** User-Approved Pilot Decision Lock.
Decision record only; tracked as maintenance task
`stage125-part3a1-decision-lock` (advances no research action). PR #34
Handoff refresh **MERGED** (`main` @ `75abf3f…`). Records user-approved rubric
version `stage125_part3a_v1` (approved but not applied), G09–G14 pilot-only
thresholds, and locked `pilot_option_event_enriched` selection (80 pairs:
39 positive / 41 negative; 26 tickers; 10 known industries; 53 industry-present
pairs; 27 industry-missing pairs).
**No** evidence collection, **no** network access, **no** accessibility scores
applied, **no** candidate admitted/rejected. `part3a_decision_locked=true`;
`part3b_started=false`; `modeling_started=false`.

**Part 3B.0 (completed — frozen historical baseline):** Evidence Capture
Readiness. Infrastructure/readiness only. After Part 3B authorization, its
`--check` verifies historical deliverables byte-identically and does not rewrite
zero-evidence QC history. `part3b0_readiness=true`.

**Part 3B detail (same active/incomplete probe as above):** 800 assessments
derived from origin probes; scores null; G13/G14 PASS; G09–G12 FAIL;
`network_extraction_performed=true` (historical probe contact only).

**Part 3B.1 detail (maintenance Decision Lock):** user-approved selections
M2-A modified / M3-C+CBI-A / M4-A / R-A / CUT-A locked as schema/formula contracts
with synthetic validation only. Adjudication in versioned
`part3b1_adjudicated_decision_requirements_stage125.json` +
`README_STAGE125_PART3B1_DECISION_LOCK.md` (historical Part 3B proposed-requirements
README remains frozen). Does **not** move
`last_completed_research_action_id` or `next_research_action_id`. Not Stage126
admission.

**Modeling authorization (Stage125 historical):** modeling remained prohibited
through all of Stage125; it began only when Stage126 (M1 Financial Baseline)
was explicitly human-authorized. Stage126 M1 primary development-fold tuning
is now authorized and started; remaining prohibitions are listed under the
active Stage126 section above.

## Historical — `stage124-gate-b-readiness`

### Superseded — `stage124-batch02-part03-1b-1`

**Cancelled by official TSE API (not completed).** The canonical listing dates
for all 130 tickers were obtained from the official TSETMC API and are stored in
`project/stage124/listing_master_verified_stage124.csv` with
date_semantics=`first_observed_trading_date_from_official_tse_api`, in columns
`first_public_trading_date_jalali` and `first_public_trading_date_gregorian`,
with status `verified_tse_api_first_observed_trade`.

The manual Human-in-the-Loop research path (HIL dashboard, manual intake runner)
has been **retired**. The 10 Part 3 tickers no longer require manual source
discovery or dashboard confirmation.

### Completed — `stage124-gate-b-readiness`

**Gate B readiness dry-run completed.** Three eligibility rules (A/B/C) were
compared as a dry-run:

- **Rule A**: `first_observed_trading_date <= fiscal_year_end` — 1013 eligible pairs (81 pos / 932 neg)
- **Rule B**: `first_observed_trading_date <= fiscal_year_start` — 994 eligible pairs (80 pos / 914 neg)
- **Rule C**: `first_observed_trading_year < fiscal_year` — 995 eligible pairs (80 pos / 915 neg)
- **Stage123 baseline**: 1085 eligible pairs (86 pos / 999 neg)

Output files in `project/stage124/gate_b_readiness/`:
- `gate_b_rule_comparison_summary.json` — full comparison
- `gate_b_company_year_audit.csv` — per-row audit (1331 rows)
- `gate_b_pair_impact_summary.csv` — per-rule pair statistics
- `gate_b_unmatched_or_ambiguous_rows.csv` — data quality issues
- `gate_b_readiness_qc_report.json` — QC report (all pass)
- `metadata_and_hashes_gate_b_readiness.json` — hashes and metadata
- `README_GATE_B_READINESS.md` — human-readable summary

45 focused tests added in `project/tests/test_stage124_gate_b_readiness.py`.

The rule was subsequently finalized under `stage124-gate-b-rule-approval` and
applied under `stage124-gate-b-execution` (see the active workstream above).

## Completed

- ✅ `stage124-batch02-part03-1b-0` — dedicated intake scaffold and readiness gate.
- ✅ `stage124-official-api-finalize` — Finalized verified master for 130 tickers
  using official TSETMC first-observed-trade dates; merged through PR #15, merge
  commit 22c2d0c.
- ✅ `stage124-gate-b-readiness` — Dry-run comparison of three eligibility rules
  (A/B/C) with per-rule impact reports and 45 focused tests.
- ✅ `stage124-gate-b-rule-approval` — Rule A approved as primary, Rule B as
  listing-timing robustness; Rule C rejected.
- ✅ `stage124-gate-b-execution` — Approved rules applied; four sample designs,
  canonical + filtered outputs, 58 focused tests. No modeling started.
- ✅ Verified master: `listing_master_verified_stage124.csv` — 130 unique tickers,
  dates in `first_public_trading_date_jalali` / `first_public_trading_date_gregorian`
  with date_semantics=`first_observed_trading_date_from_official_tse_api`
  (not necessarily IPO, admission, or listing dates).
- ⚠️ `stage124-batch02-part03-1b-1` — superseded / cancelled by official TSE API
  (not completed).

## Stage127 M2 zero-trade "trading day" semantics — ADJUDICATED (evidence import only)

The `equity_return_window` shortfall above was traced to 391 pairs whose window
endpoint fell on a **zero-trade** date, interim-labelled
`ZERO_TRADE_ENDPOINT_REQUIRES_TRADING_DAY_SEMANTICS_ADJUDICATION`. That open
question is now answered. **The canonical Gate was NOT changed by this work.**

**External evidence (immutable, not committed).**

- filename: `stage127_m2_zero_trade_semantics_full_delivery_v3.zip`
- size: 1,955,293 bytes (independently verified)
- SHA256: `5e05c3ad52d582236cc9c0bbea69dae520a02385921f3dd03792e6f65c917317`
  (independently verified)

An independent papermali-side validator
(`project/src/stage127_m2_zero_trade_semantics_import.py`) re-derived every
claim from the raw artifacts and fails closed on any inconsistency: 3,590 raw
artifacts, 3,590 manifest rows, 3,590 unique files, **3,590/3,590 SHA256
re-verified**, all endpoints exact official TSETMC API paths (0 generic), 0
unmapped artifacts, 130 zero-byte artifacts (125 UNRESOLVED + 5 HTTP_500, 0
zero-byte SUCCESS/CACHED), maximum bounded `dEven` 20200718 with **0**
observations at or after the final-test boundary. The external QC report was
**compared against, never trusted**: 35 independent comparisons, 0
disagreements.

**Factual result.** All **427/427** unique requested zero-trade endpoint dates
ARE members of the official `ClosingPrice/GetInstrumentCalendar`
InstrumentCalendar, and for **27/27** low-return RANGE requests the
InstrumentCalendar date set equals the `ClosingPriceDailyList` date set. These
dates are therefore **real official calendar dates, not retrieval or extraction
defects**. Historical identity remains explicitly uncertain: 103 tickers,
request_ISIN == raw instrumentID 103/103, == raw cIsin 8/103, CANDIDATE_FOUND 0,
NONE_FOUND 0, **UNRESOLVED 103**. Histories were not concatenated and
`insCode="0"` was never used as a predecessor. TSETMC state codes (`A `, `IS`,
`AR`, `I `, `AS`) remain literal evidence with **UNRESOLVED** meaning, because
the frozen project contains no authoritative mapping for them.

**Adjudication outcome: `FROZEN_CONTRACT_UNAMBIGUOUS_CURRENT_IMPLEMENTATION_CONFORMANT`.**

The decisive record is the FROZEN synthetic validation that locked the M2
contract (`stage125_part3b1_decision_lock_qc_report.json`): a window of **248**
days containing exactly **1** zero-traded-value day produced **247** usable
daily returns (= 248 − 1) and **246** usable Amihud days (= 247 − 1). The
zero-trade day was therefore retained in the trading-day sequence and still
contributed returns; only Amihud excluded it. Combined with
`diagnostics_recorded` (which requires counting zero-trade and missing-price
days *of W*), the amihud-scoped `zero_volume_rule`, and the endpoint clause
`If either endpoint missing => null` (which would be a dead letter if
missing-price days were deleted from W), the frozen contract already requires
exactly what the current code does. Full trace and per-question answers (A–G):
`project/stage127/stage127_m2_trading_day_semantics_contract_trace.json`.

"Trading day" is never *explicitly* defined as InstrumentCalendar membership
anywhere in the frozen corpus (question A, `NOT_SPECIFIED`), but that gap is
**non-operative here**: the calendar and daily-list date sets coincide on this
evidence, so no computed value depends on it.

**Diagnostic counterfactual — NOT a canonical result.** Under
`INSTRUMENT_CALENDAR_MEMBERSHIP_READING` the recomputation reproduces canonical
coverage exactly (269 / 576 / 576 / common 269). Under
`POSITIVE_EXECUTED_TRADE_DAY_READING` it would rise to 609/666 = 0.9144 on all
three variables. That reading is **not supported by the frozen contract** and is
contradicted by the frozen synthetic validation; it is recorded only so a human
reviewer can see the stakes, and it must not be adopted because it would produce
a PASS.

**Canonical state is unchanged:** Gate `FAIL_M2_DATA_GATE`;
equity_return_window 269/666 = 0.4039; realized_volatility 576/666 = 0.8649;
amihud_illiquidity 576/666 = 0.8649; common sample 269/666 = 0.4039. Model fits
0, predictions 0, final-test access 0. **M2 has NOT passed and M2 modeling is
NOT authorized.** `stage127-m2-incremental-evaluation` remains unauthorized and
unstarted.

**Human review COMPLETED (historical).**
`READY_FOR_STAGE127_SEMANTICS_REVIEW_CURRENT_IMPLEMENTATION_CONFORMANT` was
reviewed by the human supervisor, who responded to the coverage shortfall — now
established as TRUE frozen-contract missingness rather than a data defect — by
separately authorizing `stage128-m2-boundary-month-return-design-freeze`.
`stage127_m2_semantics_human_decision_required` is therefore now `false`. No
remediation was performed inside Stage127 and the adjudication outcome is
unchanged.

## Not in scope yet (do NOT start)

- ❌ Final-test access or evaluation; full-development refit; M1 robustness
  without the next explicit micro-part decision; SMOTE / target-proximity /
  Rule B / expanded-sample / persistent-loss robustness; M2/M3/M4 data
  collection or modeling; SHAP; network extraction
- ❌ M3I-2 / M3I-3 data retrieval of any kind (World Bank, IMF, SCI, CBI,
  FRED, ALFRED or any other API), macro observation creation, joining macro
  values to company-year rows, coverage calculation, M3I Data Gate execution,
  M3I modeling or any M3I-versus-M2 comparison — the contract lock authorizes
  none of these, and `stage128-m3i2-official-source-evidence-capture` is a
  pointer, not an authorization
- ❌ Persian text / text modeling (M5) — removed from the paper and roadmap
- ❌ Any data or analysis depending on accessibility < 3
- ❌ Data extraction, model runs, or target/sample changes during Stage125 Part 0

## Maintenance

- 🔧 `repository-driven-ai-handoff` — keep generated state synchronized after each
  completed research action and merge.
