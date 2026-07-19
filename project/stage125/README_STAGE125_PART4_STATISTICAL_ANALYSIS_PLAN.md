# Stage125 Part 4 — Statistical Analysis Plan

**Status:** Locked research-design / contract surface only.
**Research action:** `stage125-part4-statistical-analysis-plan`
**Next:** `stage125-part5-readiness-closure`

## Scope

Part 4 locks the statistical analysis plan for future Stage126 modeling:

- primary sample `main_rule_a_primary` (1012 / 119 / 80 / 932)
- primary target `FD_target_main_t_plus_1`
- M1 primary ordered feature set (exactly 10)
- M1 target-proximity robustness set (exactly 7)
- nested M2–M4 blocks (conditional; no data collected here)
- target-year temporal folds and locked final test 1400–1402
- preprocessing, model families, finite hyperparameter budget, seeds
- PR-AUC primary; Recall@10% / Lift@10%; calibration; paired ticker-cluster bootstrap; Holm
- SHAP stability contract (no SHAP computation in Part 4)

## Explicit non-claims

- No model was fitted (`model_fit_calls = 0`).
- No prediction was generated (`prediction_calls = 0`).
- No SHAP value was calculated.
- Final-test predictor values were not used for admission, tuning, or selection.
- Stage126 remains unauthorized and unstarted.
- Modeling remains unstarted.
- M3 remains unavailable pending an authoritative CBI source.
- No M2/M3/M4 values were collected.
- Active availability lag remains four Jalali calendar months.
- Financial data and targets remain frozen.
- `رمپنا|1396 → رمپنا|1397` remains audit-only.
- Part 3C outputs remain unchanged (SHA-256 pinned).

## Growth coverage exception

`revenue_growth_period_adjusted` uses an explicit Part 4 exception for
**fold training/validation coverage only**: rows where `fiscal_year_t` equals
the ticker's first observed fiscal year in the analysis-ready sample are
excluded from the fold-coverage denominator because growth is structurally
undefined. Overall development coverage still uses all development rows and
must remain ≥ 0.80.

## Runners

```bash
python project/run_stage125_part4.py --build
python project/run_stage125_part4.py --check
```

`--build` is offline and deterministic. `--check` performs zero writes.
