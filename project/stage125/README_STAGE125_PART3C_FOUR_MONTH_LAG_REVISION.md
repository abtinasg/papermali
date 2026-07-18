# Stage125 Part 3C — Four-Month Regulatory Lag Revision

**Status:** active human-approved methodological revision. Supersedes the Part 3B.1E six-month active methodology while retaining the six-month decision artifact as historical provenance.

## Active principles

- `decision_authority = explicit_human_supervisor_approval`
- `decision_status = active`
- `supersedes_active_methodology = fixed_conservative_six_month_lag`
- `historical_six_month_decision_retained = true`
- `historical_six_month_decision_active = false`
- `active_availability_method = fixed_regulatory_lag`
- `active_lag_calendar = Jalali`
- `active_lag_months = 4`
- `active_assumed_availability_field = assumed_available_at_regulatory`
- `availability_date_semantics = assumed_regulatory_deadline_not_observed_publication_timestamp`
- `financial_data_status = researcher_verified_frozen`
- `financial_value_reextraction_required = false`
- `row_level_publish_datetime_collection_required = false`
- `Stage126_authorized = false`
- `modeling_authorized = false`

## Scientific rationale

Annual audited financial statements are operationally assumed available four Jalali calendar months after fiscal-year-end.

This is a methodological regulatory-deadline assumption. It is **not** the observed publication date of any specific company report.

## Timing eligibility

General deterministic rule for every pair (no ticker-specific authorization):

```text
timing_eligible_for_analysis =
  assumed_available_at_regulatory < target_fiscal_year_end_t_plus_1
timing_eligible_for_model = timing_eligible_for_analysis
```

Violations remain in the audited pair surface and are excluded from analysis-ready outputs with `timing_exclusion_reason = regulatory_lag_not_before_target_fiscal_year_end`.
