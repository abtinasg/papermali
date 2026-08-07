# Stage128 — M3-LAG-WDI-EXPLORATORY authoritative contract lock (pre-retrieval)

**Action id:** `stage128-m3-lag-wdi-exploratory-contract-lock`
**Status:** `AUTHORITATIVE_CONTRACT_LOCKED_PRE_RETRIEVAL`
**Baseline:** `main` @ `93de6bae9344ce893b0261f818abce8a991cf842` (the merge commit of PR #77)

This package is a **contract lock only**. It retrieves nothing, inspects no
value, executes no Data Gate, materializes no feature, fits no model and reads
no Final Test row. Every execution counter in
`stage128_m3_lag_wdi_exploratory_execution_audit.json` is zero, and every
coverage value in the Data Gate contract is `null` — **not** zero, because
nothing was calculated.

## What was newly authorized

A human supervisor gave a new, explicit, one-action authorization (158 UTF-8
bytes, SHA-256 `0c1e1049…995b`; the exact utterance lives only in
`stage128_m3_lag_wdi_exploratory_human_authorization_record.json`) to activate
the M3-LAG-WDI-EXPLORATORY path **in parallel** with the still-active World
Bank inquiry, on the strict condition that its contract be **locked before any
retrieval**. That authorization is CONSUMED by this contract lock. It is **not**
reusable for retrieval, for the Data Gate or for modeling.

## What this supersedes — and what it does not

The repository previously recorded that M3-LAG-WDI-EXPLORATORY could only be
*considered* after the official inquiry terminated in
`UNRESOLVED_AFTER_FINAL_OFFICIAL_INQUIRY`. **That single restriction is now
superseded by the new explicit human authorization**, and only that one. The
prior rule is retained as clearly labelled history in `ROADMAP.md` and
`OPEN_TASKS.md`; it is not deleted and history is not rewritten.

Nothing else moved. The two tracks now run **in parallel**:

* **Track A — World Bank official inquiry.** Status
  `SUBMITTED_ACKNOWLEDGED_WAITING_FOR_SUBSTANTIVE_RESPONSE`; the waiting period
  stays **ACTIVE through 2026-08-20**; the earliest possible follow-up stays
  **2026-08-21**; follow-up is **unauthorized**; response ingestion and
  adjudication are **unauthorized**. This activation does **not** imply the
  inquiry failed, terminated, was abandoned or became unnecessary.
* **Track B — M3-LAG-WDI-EXPLORATORY.** Contract **locked**. The next possible
  action is data retrieval **only** (`stage128-m3-lag-wdi-exploratory-data-
  retrieval`), and it is **not authorized yet**. It does **not** execute the
  Data Gate: the Gate is a separate later action (see below).

## Future actions — retrieval, the Data Gate and modeling are SEPARATE

An authorization boundary only exists where an action boundary exists, so these
are never bundled and never share an identity:

| Step | Action id | Authorized |
| --- | --- | --- |
| A | `stage128-m3-lag-wdi-exploratory-contract-lock` (this action) | consumed |
| B | `stage128-m3-lag-wdi-exploratory-data-retrieval` — retrieval only | **false** |
| C | `stage128-m3-lag-wdi-exploratory-post-retrieval-audit` — audit/state recording, **no Gate** | **false** |
| D | `stage128-m3-lag-wdi-exploratory-data-gate` — the Data Gate | **false** |
| E | `stage128-m3-lag-wdi-exploratory-incremental-evaluation` — modeling | **false** |

* An authorization to **retrieve** is **not** an authorization to execute the
  Data Gate.
* A **combined** retrieval-and-Gate action is forbidden.
* A **pointer** to the Data Gate is not an authorization to execute it: step D
  needs its own NEW explicit human authorization.
* A Gate **PASS** is **DATA ADMISSION ONLY** and authorizes **no** model fit:
  step E needs ANOTHER separate explicit human authorization.
* None of A–E unlocks the Final Test.

## Scientific role — locked explicitly

M3-LAG-WDI is a **`supplementary_exploratory_robustness_block`**. It is **not**
confirmatory M3, **not** a replacement for M3-CBI, **not** a repair of M3-CBI,
**not** a continuation or replacement of M3I-2, **not** proof of historical
point-in-time WDI availability, **not** real-time WDI, **not**
historical-vintage WDI, **not** part of the original confirmatory Holm family,
and **not** capable by itself of selecting the paper winner or the final model.

The one-year lag is a **conservative temporal-separation design only**. It does
**not** establish that the current/revised WDI value was historically published
or observable at predictor time. A positive *or* negative exploratory result may
not rewrite the main confirmatory conclusion. M2 remains
`RETAIN_M2_AS_INTERMEDIATE_CONFIRMATORY_BLOCK`.

## The exact two-feature contract

Exactly **two** additional macro features. No third macro feature, no financing
rate feature, no indicator search, no imputation.

| Feature | Indicator | Country | Observation year | Transformation |
| --- | --- | --- | --- | --- |
| `intl_cpi_inflation_lag1_wdi` | `FP.CPI.TOTL.ZG` | `IRN` | `t - 1` | identity |
| `intl_fx_change_official_lag1_wdi` | `PA.NUS.FCRF` | `IRN` | `y = t - 1` (needs `t-1` and `t-2`) | `100 * ln(E_y / E_(y-1))` |

For predictor year `t = 2019` the CPI observation year is `2018`. **No same-year
`t` observation is permitted for either feature.**

For FX, `FX_LAG1_t = 100 * ln(E_(t-1) / E_(t-2))`. Both observations must be
present, numeric, strictly positive and consecutive Gregorian annual
observations; otherwise the feature is **NULL**. If that fails, **no alternative
FX indicator may be tried** — forbidden substitutions include at minimum
`PA.NUS.ATLS`, free-market rates, unofficial rates, aggregator-derived rates and
post-hoc alternative transformations.

## WDI vintage semantics — the honest limitation

This path deliberately does **not** attempt to prove historical WDI archive
release dates. The future retrieval will use the then-retrieved official
**current/latest** WDI values, which may contain revisions. Therefore:

* latest/current revised WDI **is** allowed;
* historical-vintage availability is **not** claimed;
* point-in-time availability is **not** claimed;
* lagging by one observation year does **not** transform revised WDI into
  point-in-time data;
* **this limitation is exactly why the analysis is exploratory/supplementary.**

The M3I-2 historical-vintage availability logic is **not** reused to claim
point-in-time validity here.

## Sample and feature architecture

* Parent sample: the exact retained-M2 three-variable common sample — **539
  development rows** (55 positive, 484 negative, 108 companies). The original
  666-row M1 comparison sample is **not** used.
* M2 comparator: **12** features.
* M3-LAG-WDI: the same 12 M2 features **+** the exact 2 lagged WDI features =
  **14** features. No feature selection, no substitution, no new proxy search.
* Complete cases are required for **both** new lagged WDI features, and any
  future M3-LAG-WDI vs M2 comparison must refit **both** models on the **exact
  same** resulting common sample. The previously produced 666-row M1 results may
  **not** be reused as the comparator.

## Data Gate — frozen now, not executed

Thresholds are **inherited**, not redesigned: individual candidate coverage
`>= 0.80`, block common-sample coverage `>= 0.70`, and `>= 5` positive outcomes
in **each** locked validation window. The Gate is **development-only**.

If the future Gate does not pass, **no M3-LAG-WDI model may be fit**. A Gate
PASS is **data admission only** — it does not itself authorize modeling. Future
predictive evaluation needs its own separate explicit human authorization.

## Future modeling contract — frozen, not executed

Exactly the same three model families as the retained M2 programme —
regularized logistic regression, random forest, XGBoost — in their already
frozen retained configurations. No retuning, no grid search, no hyperparameter
search, no model-family search. Canonical metric definitions, the locked
validation architecture, the seed policy and the paired-comparison/bootstrap
machinery are **inherited** from the retained M2 evaluation artifacts; no
secondary metric is invented or redefined here.

The primary comparison is **M3-LAG-WDI versus M2** on the identical
post-complete-case development sample. It belongs to a **separate exploratory /
supplementary family** (`E1`) and must **never** be inserted into the
confirmatory Holm family `M2_minus_M1`, `M3_CBI_minus_M2`, `M4_minus_M3_CBI`.

## Final Test firewall

The Final Test remains **hard locked**. This action read **0** Final Test
predictor values and **0** Final Test target values. The future Data Gate is
development-only. No final-test unlock is implied by the contract lock, by a
future successful WDI retrieval, by a future Data Gate PASS or by a future
exploratory development result. Unlocking requires its own later governance
decision.

## Existing scientific state — unchanged

M3-CBI stays `UNRESOLVED_M3_DATA_GATE`. M3I-2 stays
`UNRESOLVED_OFFICIAL_SOURCE_EVIDENCE` and unadmitted, with 37/37 cutoffs and
539/539 development pairs unresolved, 0 verified WDI release dates and 0
verified pre-cutoff editions. The World Bank inquiry stays submitted once,
acknowledged, without a substantive response, with no ticket id present and none
fabricated and the UTC instant unresolved. M4 stays unauthorized. No previously
observed M1/M2 result was rewritten.

## The old local partial draft

An earlier local, uncommitted partial M3-LAG-WDI draft was quarantined outside
the repository (see
`../m3i2_final_official_documentary_recovery/stage128_m3_lag_partial_local_execution_supersession_record.json`).
It is **not** authoritative, its old authorization remains consumed and
non-reusable, and it was **not** promoted or committed. It was left untouched.
This contract derives instead from the current merged repository state and the
new explicit human authorization above.

## PR topology — history is pinned, not re-derived

Three PRs, three different actions, three different roles. Re-anchoring the
LIVE topology onto this Draft does **not** rewrite what an older PR *was*, and
"the recovery PR" is a **name for a specific historical action**, never a
moving label for "whatever merged most recently":

| PR | Role | State |
| --- | --- | --- |
| **#76** | `stage128-m3i2-final-official-documentary-recovery-initiation` — the documentary recovery **INITIATION** | MERGED by `89d8e6ff2d12ec82903cd28aa7ab839eb946b658`; superseded by PR #77 |
| **#77** | `stage128-m3i2-final-official-inquiry-human-submission` — the later, separate **HUMAN inquiry submission RECORDING** | MERGED by `93de6bae9344ce893b0261f818abce8a991cf842`; superseded by PR #78 |
| **#78** | `m3_lag_wdi_exploratory_contract_lock_pr` — this action | the current **LIVE Draft**; merged = false, ready-for-review and merge **unauthorized** |

PR #77 is the immediate merged predecessor and the base of this PR; it is
**not** the documentary recovery. Generation anchors (the repository head shown
for the live PR) are explicitly informational and volatile, never pinned and
never the instantaneous GitHub PR head.

## Package contents

| File | Role |
| --- | --- |
| `stage128_m3_lag_wdi_exploratory_contract.json` | the authoritative machine-readable contract |
| `stage128_m3_lag_wdi_exploratory_human_authorization_record.json` | the exact human authorization, byte length and SHA-256 |
| `stage128_m3_lag_wdi_exploratory_contract_decision.json` | the decision record and pointers |
| `stage128_m3_lag_wdi_exploratory_governance_boundary.json` | the governance boundary, both tracks |
| `stage128_m3_lag_wdi_exploratory_data_gate_contract.json` | the frozen, unexecuted Data Gate |
| `stage128_m3_lag_wdi_exploratory_modeling_contract.json` | the frozen, unexecuted modeling/comparison contract |
| `stage128_m3_lag_wdi_exploratory_execution_audit.json` | the zero-execution audit |
| `stage128_m3_lag_wdi_exploratory_pr_topology.json` | live/predecessor PR topology |
| `stage128_m3_lag_wdi_exploratory_contract_qc_report.json` | contract-lock QC |
| `metadata_and_hashes_stage128_m3_lag_wdi_exploratory_contract_lock.json` | hash manifest |

Nothing here authorizes retrieval, the Data Gate, modeling, ready-for-review or
merge. Each of those is a separate future human decision.
