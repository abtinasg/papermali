# Stage125 Part 3B.1E — Conservative Six-Month Availability-Lag Decision Lock

**Status:** methodology decision lock (offline). Stage125 remains incomplete.

## Approved methodology

- `financial_data_status = researcher_verified_frozen`
- `financial_value_reextraction_required = false`
- `broad_codal_capture_authorized = false`
- `row_level_publish_datetime_collection_authorized = false`
- `row_level_real_available_at_assignment_authorized = false`
- `availability_method = fixed_conservative_lag`
- `conservative_lag_months = 6`
- `availability_date_semantics = assumed_methodological_date_not_observed_publication_timestamp`
- `assumed_available_at = fiscal_year_end + 6 calendar months` (field `assumed_available_at_conservative` only)
- predictors from fiscal year **t** may only predict distress target **t+1**
- a predictor observation may only be used after the six-month lag has elapsed
- `stage126_authorized = false`
- `modeling_authorized = false`

## Scientific interpretation

The existing accounting values were manually extracted and verified by the researcher. They are frozen and are not being revalidated or re-extracted in this stage.

The purpose of the six-month lag is only to prevent temporal leakage. It is not intended to verify the correctness of accounting values.

The previous five-row CODAL metadata pilot did not justify expansion. PR #47 was closed unmerged and superseded by this methodology. No 80-row or 130-company CODAL metadata capture is planned.

## Explicit non-claims

- Assumed availability is **not** an actual `PublishDateTime`, CODAL publication date, verified source timestamp, or observed `available_at`.
- No broad CODAL capture, financial-value extraction, or row-level publication-date assignment.
- No Stage126 / modeling.

## Research pointers

- `last_completed_research_action_id=stage125-part3b-conservative-lag-decision-lock`
- `next_research_action_id=stage125-part3c-leakage-safe-dataset-finalization`
