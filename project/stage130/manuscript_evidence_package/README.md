# Stage130 Phase 1 — canonical manuscript evidence package

Presentation only. **No new scientific analysis was performed.**

* The Final Test was not reopened; `final_test_rows_read` by this action = 0.
* The row-level prediction artifact
  `stage129_final_test_predictions.json` was **never opened**; it is listed in
  `FORBIDDEN_SOURCES` and the loader refuses it fail-closed.
* No metric, confidence interval, bootstrap replicate, p-value, subgroup
  result, per-year performance value, calibration quantity, decision curve or
  threshold was computed. SHAP executions = 0.
* The only arithmetic applied is `exp(beta)` on the locked coefficients -- a
  deterministic transformation of a frozen artifact, authorized as manuscript
  presentation rather than as new estimation.

## Contents

| file | role |
|---|---|
| `manuscript_claim_freeze.md` | frozen claims: source, exact value, permissible wording, prohibited overclaim, mandatory limitation |
| `table_model_coefficients_and_odds_ratios.csv` | canonical coefficient/OR table (18 terms + intercept) |
| `manuscript_results_tables/` | nine deterministic tables: six result tables, one locked development-performance table, one definitional outcome table and one descriptive data-construction/QC table |
| `manuscript_figures/` | three schematic figures (no performance curves) |
| `legacy_outputs_supersession.md` | `project/outputs/09_report` marked LEGACY_STAGE123_NONCANONICAL_DO_NOT_CITE |
| `manifest.json` | SHA-256 + byte count per file, and the authoritative source of every displayed value |

## Reading the coefficient table

Continuous features are **standardized**, so their odds ratios are **per 1-SD
increase**; the standardizing mean and SD are shown per row. The nine
missingness indicators are **unstandardized binary**, so their odds ratios are
for **indicator = 1 versus 0**. Terms appear in the model's own order -- this
is deliberately **not** an importance ranking. No confidence interval, standard
error, p-value or significance marker is present, because none exists in the
locked artifact. All effects are **regularized conditional associations**, never
causal.

**Missingness indicators — descriptive fact only.** Six of the nine
missingness-indicator coefficients are exactly zero in the locked model; three
are non-zero (`ocf_to_assets_period_adjusted__missing`,
`operating_margin_period_adjusted__missing`,
`financial_expense_to_assets_period_adjusted__missing`). This pattern is
reported descriptively and does not establish statistical significance or a
general claim that missingness is informative.

## Figures

Only schematics and a coefficient plot. ROC, precision-recall, calibration,
subgroup and per-year performance curves are **absent by design**: each would
require row-level Final Test data or a new scientific calculation.

## Not authorized by this package

Ready-for-review, merge, a second Final Test pass, any new scientific
computation, and Stage130 scientific execution
(`stage130_scientific_execution_started = false`).
