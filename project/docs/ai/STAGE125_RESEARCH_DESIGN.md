# STAGE125 — Research Design Decision Lock (Part 0)

> **Human-maintained.** This is the frozen research contract for Stage125 and the
> incremental modeling program (Stage126+). It records the agreed design and every
> explicit exclusion. It is an **input** to the Handoff state — it is never
> auto-generated. Any future change requires an explicit, versioned research
> decision (see [`DECISIONS.md`](DECISIONS.md) and the source memory
> `papermali_stage125_project_memory_and_roadmap.md`).

**Version:** 1.0
**Decision-lock date:** 2026-07-13
**Status:** Authoritative research contract from the start of Stage125.

### Addendum A — Part 3C leakage-safe finalization (2026-07-18)

Versioned methodological addendum (does not silently rewrite Part 0 history):

- Part 3B broad CODAL expansion is **superseded**.
- Originally operationalized under the Part 3B.1E six-month lag
  (historical; see Addendum B).

### Addendum D — Part 5 Readiness Closure (2026-07-19)

Versioned closure addendum (does not silently rewrite Part 0–4 history):

- Stage125 Part 5 closes Stage125 research-design readiness under Gate 125.0.
- Closure outcome:
  `READY_FOR_STAGE126_M1_HUMAN_AUTHORIZATION_DECISION`.
- **Readiness is not authorization.** `stage126_m1_entry_ready=true` does
  **not** set `stage126_authorized`, `modeling_authorized`, or unlock the
  final test.
- M1 primary (9 features) is ready for a future Stage126 authorization
  decision; M1 target-proximity (6) remains registered robustness;
  `revenue_growth_period_adjusted` remains audit-only rejected.
- M2 deferred (nonblocking for M1); M3 not admitted; M4 deferred
  (nonblocking for M1); M5 removed.
- Article-141 remains descriptive-only (no comparative/inferential ranking).
- Part 3B expansion remains `superseded_not_required_for_stage125_closure`
  with `part3b_completed=false` (historical evidence unchanged).
- Four-Jalali-month regulatory lag remains active; six-month method remains
  historical only; final test 1400–1402 remains locked.
- Stage126 M1 entry contract is recorded; Stage126 is **not** authorized and
  was **not** started; modeling is **not** authorized and was **not** started.
- Next research pointer: `stage126-m1-financial-baseline` (**future**;
  blocked pending explicit human authorization; not started).

### Addendum C — Part 4 Statistical Analysis Plan (2026-07-19)

Versioned methodological addendum (does not silently rewrite Part 0–3C history):

- Active contract: `stage125_part4_sap_v2` (v1 retained in Git history).
- Part 4 locks the statistical analysis plan only; **no** model fitting.
- Primary sample / target:
  `main_rule_a_primary` × `FD_target_main_t_plus_1`.
- M1 primary ordered features (9 admitted) and M1 target-proximity robustness
  (6) are approved; `revenue_growth_period_adjusted` is rejected (Fold 1
  training coverage `148/245 = 0.6040816327` < 0.75) and retained audit-only;
  no denominator exception. Remaining Part 3C candidates stay audit-only
  exclusions (23 M1 exclusions total).
- Nested M2–M4 blocks are defined (9/12/15/19); M3 not admitted (no
  authoritative CBI source); no M2/M3/M4 values collected in Part 4.
- Temporal design locked on `target_year`: development 1393–1399; folds
  1393–1395/1396–1397 and 1393–1397/1398–1399; final test 1400–1402.
- Strict positive/negative/missing target accounting; pre-imputation
  missingness-mask preprocessing; SMOTE disables class weighting.
- Primary metric PR-AUC; Recall@10% / Lift@10%; calibration; paired
  ticker-cluster bootstrap; Holm multiplicity; finite seed/tuning budget.
- Final-test predictor values must not be inspected for admission, tuning,
  feature selection, or model comparison until Stage126 is authorized.
  Final-test event thresholds control claim eligibility only.
- Historical next pointer after Part 4 was `stage125-part5-readiness-closure`
  (completed; see Addendum D).

### Addendum B — Four-month regulatory lag revision (2026-07-19)

Explicit human-approved revision of the active availability specification:

- Active lag is **four Jalali calendar months**
  (`fixed_regulatory_lag` / `assumed_available_at_regulatory`).
- Six-month active methodology is **superseded**; Part 3B.1E six-month
  decision artifacts remain **historical**.
- Part 3C leakage-safe dataset finalization is **completed** for all four
  locked Gate B sample designs under the four-month rule.
- Full Gate B membership is preserved on the **audited pair** surface;
  leakage-safe **analysis-ready** outputs include only rows where
  `assumed_available_at_regulatory < target_fiscal_year_end_t_plus_1`
  (general rule; `رمپنا|1396` → `رمپنا|1397` remains audit-only).
- Financial data remain researcher-verified and frozen (no re-extraction).
- The four-month date is a regulatory/methodological assumption — **not**
  an observed publication-time claim.
- Part 3C does **not** approve model features; Part 4 locks the feature
  surface.
- Stage125 remains incomplete; Stage126 and modeling remain unauthorized.
- Next research action: `stage125-part4-statistical-analysis-plan`.

## 0. Scope of this Part (Part 0)

Part 0 is a **documentation-only decision lock**. It performs **no** data
extraction, **no** modeling, and does **not** change the frozen target, universe,
sample, eligibility, cutoff, or metrics. It does **not** rewrite Stage122–Stage124
files, and it does **not** start Stage125 Part 1.

Baseline confirmed before this Part:

- PR #20 is **MERGED**.
- `main` contains merge commit `873e538c90645d0fa7c52ddf2bbe79081f310c84`.
- Stage124 Gate B is **completed and frozen**.
- Stage125 and any new modeling have **not** started.

## 1. Frozen scientific sample (Stage123 → Stage124 Gate B)

| Design | company-year rows | companies | positive | negative |
|---|---:|---:|---:|---:|
| Full Stage123 panel | 1331 | 130 | — | — |
| Primary Rule A | 1013 | 119 | 81 | 932 |
| Primary Rule B | 994 | 117 | 80 | 914 |
| Expanded Rule A | 1057 | 124 | 81 | 976 |
| Expanded Rule B | 1036 | 122 | 80 | 956 |

**Critical constraint — low positive event count.** With two target years the final
positives are ~8 and with three years ~12. Therefore temporal splitting, model
complexity, and the number of secondary analyses must stay **conservative**.

## 2. Agreed final design — incremental, nested blocks

| Model | Data added | Status |
|---|---|---|
| M1 | Current, frozen financial variables | In main scope |
| M2 | M1 + market variables | In main scope |
| M3 | M2 + a small, theory-driven macro set | In main scope |
| M4 | M3 + structured audit & corporate-governance variables | In scope, each variable conditional on passing the data Gate |
| M5 | Persian text / text modeling | **Removed** from the paper and the current roadmap |

M1–M4 must be compared, as far as possible, on the **same common sample, the same
temporal split, and paired predictions**, so the incremental value of each block is
genuinely interpretable.

### Core novelty of the paper

The novelty is **not** "more algorithms" or "first multi-source Iran paper". The
claim is built on:

- an audited three-state target: positive / negative / unknown — missing is never
  assumed healthy;
- a genuine point-in-time design for `t → t+1` prediction;
- incremental comparison of blocks M1 → M4;
- real temporal validation and a single locked final test;
- calibration and screening value via `Recall@K` and `Lift@K`;
- temporal stability, drift, and explanation-stability checks;
- transparent reporting of positive and negative results, without inflating novelty.

## 3. Firm data-admission rule

A variable or source enters the **main** analysis only when **all** of the
following hold:

1. accessibility score ≥ 3 of 5;
2. the source is valid, citable, and reproducible;
3. real publication / availability time (`published_at` or `available_at`) is known;
4. coverage on the common sample is sufficient;
5. adding it does not destructively reduce positive event counts within temporal folds;
6. extraction, adjustment, unit, calendar, and identifier-join error is controlled.

**accessibility = 3 is NOT an automatic pass.** A score of 3 only allows a variable
to enter the coverage/quality pilot. Failing any of conditions 2–6 removes it from
the main analysis.

## 4. Retained data scope

### M1 — Financial

- Existing frozen data and target.
- Financial ratios/variables under point-in-time logic only.
- Source, file, version, hash, and access time recorded for each input.
- The current Stage123 provenance gap must be closed or fully audited before modeling.

### M2 — Market

- Returns and momentum; volatility.
- Volume, turnover, no-trade days, and Amihud as computable liquidity measures.
- Beta, drawdown, market index.
- Transparent corporate-action adjustment and trading-calendar alignment.
- All windows must close before the prediction cutoff.

### M3 — Parsimonious macro

Only a small, pre-specified set, e.g.:

- CPI / official inflation;
- FX change from an official source (or one that passes the data Gate);
- policy/financing rate; liquidity growth;
- GDP or a production index, if publication date and coverage are reliable;
- oil only with a clear theoretical rationale and passing the data Gate.

Macro variables must stay few (~10 years of independent time), to limit temporal
overfitting risk.

### M4 — Structured audit & corporate governance

Each variable is Gated individually. Acceptable candidates:

- audit opinion type;
- going-concern / material-uncertainty clause as a structured, auditable label;
- audit lag; auditor change;
- board size; non-executive ratio (only if definition/coverage are auditable);
- ownership concentration;
- existence/size of the audit committee, only with sufficient coverage.

Board and audit reports are used **only** to extract the structured variables above,
**not** to build a Persian text model in the current paper.

## 5. Out-of-scope — removed from the current project and paper

Firm current decision: the following are **not** collected or modeled unless a new,
explicit, versioned research decision changes this contract:

- **M5 and all Persian text modeling** (TF-IDF, embeddings, heavy language models);
- order-book or historical bid–ask variables with low accessibility;
- free-market FX from non-reproducible sources lacking a valid publication date;
- director biography, education, inferred gender, social network, real independence,
  or expertise where no auditable source exists;
- director networks and interlocking directorates;
- social-network, news, ESG, and low-accessibility unstructured sources;
- a large, searched macro-variable set;
- multiple post-hoc economic-regime definitions — only one simple, pre-specified
  definition may be examined as a secondary analysis, after the data Gate and the
  statistical-power Gate;
- real cost-matrix optimization and Decision Curve Analysis (no valid cost/
  intervention data available);
- multiple algorithms used to inflate the apparent number of models.

**Allowed core models:** regularized Logistic Regression, Random Forest, XGBoost.
Class weighting is the primary imbalance method; SMOTE is only an in-training-fold
robustness check.

## 6. Metrics & evaluation rules

- Proposed primary metric, locked before running: **PR-AUC**.
- Operational metrics: `Recall@K` and `Lift@K`.
- Calibration: Brier score, calibration curve, and slope/intercept if feasible.
- ROC-AUC is a complementary metric only.
- Splits must be temporal and pre-specified.
- All preprocessing, imputation, scaling, feature selection, and SMOTE fit **only**
  inside the train fold.
- The final test is locked and run **once** after the design is fully fixed.
- Block comparison uses paired predictions with appropriate uncertainty.
- SHAP is checked for rank/direction stability across seed/fold/time, not a single plot.

## 7. Stage125 roadmap (Research Design & Data Readiness — no modeling)

- **Part 0 — Decision & baseline lock (this document).** Confirm `main`/baseline
  after PR #20; create the Stage125 branch; record the research contract in human
  docs; regenerate the Handoff via the generator; run validator + tests; open a PR
  (no merge). **No** extraction, target/sample change, or modeling.
- **Part 1 — Data dictionary & provenance contract. (Completed and merged.)** Stable company id, fiscal year, dates; mandatory provenance
  fields; source manifest for M1–M4; audit the current M1 provenance gap; cache /
  raw-vs-processed policy; no raw-file overwrite. Delivered in `project/stage125/`
  as a contracts / read-only-audit task (`stage125-part1-data-contract`); it
  advances no research action, performs no modeling and no extraction, and does
  not start Part 2. `modeling_started` remains `false`.
- **Part 2 — Prediction-time contract. (Completed and merged.)** Exact
  prediction time and cutoff; when each statement / audit report / board report /
  market series / macro series became usable; lag and revision policy; leakage
  checklist and anti-leakage machine tests. Deliverables in `project/stage125/`:
  prediction-time contract, feature availability contract (M1–M4), leakage
  checklist (8 machine-testable checks LC01–LC08), per-pair cutoff/feature/leakage
  audit CSVs (all 1200 pairs preserved), cutoff summary. Missing `fiscal_year_end`
  never filled or guessed; `eligibility_impact=none_contract_audit_only` for every
  pair. PR #27 post-merge Handoff refresh merged (`c6cbb6b7…`).
- **Part 3A — Accessibility & pilot protocol lock. (Completed and merged.)**
  PR #29 merged (`main` @ `4e15cb7…`). Freeze the 10 registered M2–M4
  candidates; propose (but do not apply) the accessibility rubric; lock gate
  decision protocol; compute sampling frame from frozen data; provide pilot-size
  options for human approval; define Part 3B evidence schema. **No** live
  evidence, **no** scores, **no** admitted candidates. Protocol assets frozen.
  `part3a_protocol_locked=true`; `part3b_started=false`.
- **Part 3A.1 — User-approved pilot decision lock. (Authorized and active.)**
  Record user-approved rubric version, G09–G14 pilot thresholds, and locked
  `pilot_option_event_enriched` selection (80 pairs; event-enriched; not
  population-representative; not modeling sample). **No** evidence, **no**
  scores applied. `part3a_decision_locked=true`; `part3b_started=false`.
- **Part 3B — Evidence capture & accessibility scoring. (Superseded for
  expansion.)** Origin probes / five-row CODAL metadata history retained;
  broad CODAL expansion stopped by Part 3B.1E conservative-lag decision.
- **Part 3C — Leakage-safe dataset finalization. (Completed.)** Four Gate B
  designs preserved; active four-Jalali-month `assumed_available_at_regulatory`
  operationalized (six-month methodology superseded); candidate inventory
  only; column-role map + leakage audit; **no** feature approval / modeling.
- **Part 3 (umbrella) — Accessibility, coverage & event pilot.** Parts 3A–3C;
  Part 3B expansion path superseded by conservative lag + Part 3C.
- **Part 4 — Statistical analysis plan. (Completed.)** Locked M1–M4 definitions
  and order; primary/robustness samples; temporal CV and locked final test;
  PR-AUC / Recall@K / Lift@K / calibration; paired bootstrap and Holm; seeds
  and finite tuning budget. **No** model fitting.
- **Part 5 — Stage125 closure. (Completed on PR branch; merge requires human
  approval.)** Final readiness report; keep/drop/defer register; blocker
  register; Stage126 M1 entry contract (readiness only); integrity manifest;
  Gate 125.0; full validator + tests. **No** Stage126 authorization or start;
  **no** modeling.

**Gate 125.0:** contradiction-free docs, valid Handoff, green tests, clean
working tree, frozen Part 3C/Part 4 hashes, keep/drop complete, final test
locked, Stage126 unauthorized.

## 8. Change-control principles

- No PR is merged without explicit user approval.
- No later Part starts before the prior Part's Gate is approved.
- Generated files are never edited by hand.
- Any change to target, universe, eligibility, cutoff, primary metric, or the locked
  test requires an explicit research decision and a new version of this contract.
- Every paper claim must trace to code output, a table, a manifest, or a citable source.
