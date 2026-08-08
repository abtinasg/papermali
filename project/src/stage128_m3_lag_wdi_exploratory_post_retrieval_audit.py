"""Stage128 — Track B step C: the M3-LAG-WDI POST-RETRIEVAL AUDIT.

Authorized action: ``stage128-m3-lag-wdi-exploratory-post-retrieval-audit``
Authorized scope:  ``post_retrieval_audit_only``

Step B acquired bytes and deliberately never looked inside them. This step is
the first — and, under this authorization, the only — action permitted to
DECODE those bytes. It answers exactly one question:

    *what is actually in the retained evidence, and is it what the locked
    contract said it would be?*

It does not answer, and may not answer:

* whether the block has enough coverage to be admitted  (step D, the Data Gate)
* which company rows would receive a value                (step D)
* whether the block improves anything                     (step E, modeling)

The distinction that keeps this honest is SERIES level versus SAMPLE level.
This module characterises the two SERIES: which observation years exist, which
carry numeric values, and which predictor years a contract-conforming feature
could therefore be built for. It never opens the development sample, never
joins a value to a company row, never compares anything to the Gate's coverage
thresholds and never returns an admission decision. A reader can see the
consequences of the evidence without the Gate having been run on it.

The audit is deliberately capable of FAILING and of passing with findings. A
post-retrieval audit that can only say "fine" would be theatre.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from typing import Any

ACTION_ID = "stage128-m3-lag-wdi-exploratory-post-retrieval-audit"
AUTHORIZED_SCOPE = "post_retrieval_audit_only"
PACKAGE_ID = "stage128_m3_lag_wdi_exploratory_post_retrieval_audit"
PACKAGE_REL = "project/stage128/m3_lag_wdi_exploratory_post_retrieval_audit"

#: The retrieval package this audit reads. Step C audits step B's evidence; it
#: never re-acquires it.
RETRIEVAL_PKG_REL = "project/stage128/m3_lag_wdi_exploratory_data_retrieval"
RETRIEVAL_MANIFEST_REL = (
    f"{RETRIEVAL_PKG_REL}/stage128_m3_lag_wdi_retrieval_source_manifest.json")
CONTRACT_REL = ("project/stage128/m3_lag_wdi_exploratory_contract_lock/"
                "stage128_m3_lag_wdi_exploratory_contract.json")

#: The NEW single-use human authorization for THIS step. Recorded verbatim so
#: the digest below is reproducible from the text a human actually wrote. It is
#: distinct from the contract-lock and retrieval authorizations, both of which
#: stay historical and consumed and are never stretched to cover step C.
HUMAN_AUTHORIZATION_TEXT = (
    "HUMAN AUTHORIZATION — STAGE128 M3-LAG-WDI STEP C ONLY\n"
    "\n"
    "I explicitly authorize execution of:\n"
    "\n"
    "stage128-m3-lag-wdi-exploratory-post-retrieval-audit"
)

#: The contract-locked identities this audit must find in the payloads.
CPI_CODE = "FP.CPI.TOTL.ZG"
FX_CODE = "PA.NUS.FCRF"
LOCKED_COUNTRY_CODE = "IRN"
LOCKED_INDICATOR_CODES = (CPI_CODE, FX_CODE)

#: World Bank API v2 returns ``[header, rows]``. Anything else is a schema
#: change, which is a finding rather than something to silently accommodate.
_EXPECTED_TOP_LEVEL_LEN = 2
_REQUIRED_ROW_KEYS = frozenset(
    {"indicator", "country", "countryiso3code", "date", "value"})


class PostRetrievalAuditError(RuntimeError):
    """Raised when the audit cannot be performed honestly."""


def _sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def verify_human_authorization() -> dict[str, Any]:
    """The step C authorization, pinned by its own byte length and digest."""
    raw = HUMAN_AUTHORIZATION_TEXT.encode("utf-8")
    return {
        "action_id": ACTION_ID,
        "authorized_scope": AUTHORIZED_SCOPE,
        "authorization_text": HUMAN_AUTHORIZATION_TEXT,
        "authorization_utf8_bytes": len(raw),
        "authorization_sha256": _sha256_bytes(raw),
        "authorization_is_single_use": True,
        "authorization_covers_data_gate": False,
        "authorization_covers_modeling": False,
        "authorization_covers_final_test": False,
        "authorization_covers_new_retrieval": False,
        "authorization_covers_track_a_follow_up": False,
        "prior_retrieval_authorization_reused": False,
        "prior_contract_lock_authorization_reused": False,
        "standing_authorization": False,
    }


def load_retained_payload(path: str, expected_bytes: int,
                          expected_sha256: str) -> tuple[bytes, Any]:
    """Read a retained payload, prove its identity, THEN decode it.

    Identity is checked on the raw bytes before any parsing. Auditing bytes
    that are not provably the retrieved bytes would be worse than not auditing
    at all, so a mismatch raises instead of degrading to a warning.
    """
    if not os.path.isfile(path):
        raise PostRetrievalAuditError(f"retained payload not found: {path}")
    with open(path, "rb") as fh:
        blob = fh.read()
    if len(blob) != expected_bytes:
        raise PostRetrievalAuditError(
            f"retained payload byte count mismatch for {os.path.basename(path)}"
            f": expected {expected_bytes}, found {len(blob)}")
    digest = _sha256_bytes(blob)
    if digest != expected_sha256:
        raise PostRetrievalAuditError(
            f"retained payload SHA-256 mismatch for {os.path.basename(path)}: "
            f"expected {expected_sha256}, found {digest}")
    try:
        document = json.loads(blob.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PostRetrievalAuditError(
            f"retained payload is not decodable JSON: {exc}") from exc
    return blob, document


def audit_series(indicator_code: str, document: Any) -> dict[str, Any]:
    """Characterise ONE retrieved series. Series level only, never sample."""
    findings: list[str] = []
    if not isinstance(document, list) or len(
            document) != _EXPECTED_TOP_LEVEL_LEN:
        raise PostRetrievalAuditError(
            f"{indicator_code}: unexpected World Bank envelope shape")
    header, rows = document
    if not isinstance(header, dict) or not isinstance(rows, list):
        raise PostRetrievalAuditError(
            f"{indicator_code}: unexpected World Bank envelope contents")

    # --- the response must be complete, or the audit is reading a fragment --
    pages = header.get("pages")
    total = header.get("total")
    if pages != 1:
        findings.append(
            f"response is paginated (pages={pages}); the retained payload may "
            "be a fragment")
    if total != len(rows):
        findings.append(
            f"header total {total} disagrees with {len(rows)} returned rows")

    # --- every row must be about the series we asked for --------------------
    indicator_ids = sorted({
        (row.get("indicator") or {}).get("id") for row in rows})
    iso3 = sorted({row.get("countryiso3code") for row in rows})
    if indicator_ids != [indicator_code]:
        raise PostRetrievalAuditError(
            f"{indicator_code}: payload carries indicator ids {indicator_ids}")
    if iso3 != [LOCKED_COUNTRY_CODE]:
        raise PostRetrievalAuditError(
            f"{indicator_code}: payload carries country codes {iso3}")
    for row in rows:
        missing = _REQUIRED_ROW_KEYS - set(row)
        if missing:
            raise PostRetrievalAuditError(
                f"{indicator_code}: observation missing keys {sorted(missing)}")

    # --- year axis ----------------------------------------------------------
    years: list[int] = []
    for row in rows:
        try:
            years.append(int(row["date"]))
        except (TypeError, ValueError) as exc:
            raise PostRetrievalAuditError(
                f"{indicator_code}: non-annual observation date "
                f"{row.get('date')!r}") from exc
    duplicates = sorted({y for y in years if years.count(y) > 1})
    if duplicates:
        raise PostRetrievalAuditError(
            f"{indicator_code}: duplicate observation years {duplicates}")
    values = {int(row["date"]): row.get("value") for row in rows}
    first_year, last_year = min(years), max(years)
    calendar_gaps = [y for y in range(first_year, last_year + 1)
                     if y not in values]
    if calendar_gaps:
        findings.append(
            f"calendar gaps in the observation axis: {calendar_gaps}")

    numeric = {y: v for y, v in values.items()
               if isinstance(v, (int, float)) and not isinstance(v, bool)}
    null_years = sorted(y for y, v in values.items() if v is None)
    non_numeric = sorted(y for y, v in values.items()
                         if v is not None and y not in numeric)
    if non_numeric:
        findings.append(
            f"non-numeric non-null observations in years {non_numeric}")

    # Trailing nulls are the shape that actually bites: the most recent years
    # are exactly the ones a lagged feature needs.
    trailing_null_years = []
    for year in range(last_year, first_year - 1, -1):
        if values.get(year) is None:
            trailing_null_years.append(year)
        else:
            break
    trailing_null_years.sort()
    if trailing_null_years:
        findings.append(
            "the most recent observation years carry no value: "
            f"{trailing_null_years}")

    observation_statuses = sorted({
        (row.get("obs_status") or "") for row in rows})
    flagged = [s for s in observation_statuses if s]

    return {
        "indicator_code": indicator_code,
        "country_code": LOCKED_COUNTRY_CODE,
        "indicator_name": (rows[0].get("indicator") or {}).get("value"),
        "source_id": header.get("sourceid"),
        # The WDI database vintage. This is a REVISION marker, never proof of
        # what was published at any past moment.
        "source_last_updated": header.get("lastupdated"),
        "response_pages": pages,
        "response_total": total,
        "observations_returned": len(rows),
        "observation_year_first": first_year,
        "observation_year_last": last_year,
        "observation_years_distinct": len(set(years)),
        "calendar_gaps": calendar_gaps,
        "observations_numeric": len(numeric),
        "observations_null": len(null_years),
        "null_observation_years": null_years,
        "non_numeric_observation_years": non_numeric,
        "trailing_null_observation_years": trailing_null_years,
        "numeric_observation_year_first": min(numeric) if numeric else None,
        "numeric_observation_year_last": max(numeric) if numeric else None,
        "observation_status_flags": flagged,
        "findings": findings,
    }


def derive_cpi_feature_availability(values: dict[int, Any]) -> dict[str, Any]:
    """Predictor years for which the CPI feature could be built.

    Contract: ``intl_cpi_inflation_lag1_wdi`` is the IDENTITY of the year
    ``t-1`` observation. It carries no positivity requirement — the series is
    an annual percentage change, so a negative or zero value is a legitimate
    deflation observation, not a defect.
    """
    numeric = {y for y, v in values.items()
               if isinstance(v, (int, float)) and not isinstance(v, bool)}
    constructible = sorted(y + 1 for y in numeric)
    return {
        "feature_id": "intl_cpi_inflation_lag1_wdi",
        "indicator_code": CPI_CODE,
        "transformation": "identity",
        "required_observation_years": ["t-1"],
        "positivity_required": False,
        "constructible_predictor_years": len(constructible),
        "constructible_predictor_year_first":
            min(constructible) if constructible else None,
        "constructible_predictor_year_last":
            max(constructible) if constructible else None,
    }


def derive_fx_feature_availability(values: dict[int, Any]) -> dict[str, Any]:
    """Predictor years for which the FX feature could be built.

    Contract: ``FX_LAG1_t = 100 * ln(E_(t-1) / E_(t-2))`` requires BOTH
    observations present, numeric, strictly positive and consecutive.

    This also reports where the transformation is DEFINED but DEGENERATE. A
    pegged official rate repeated across consecutive years yields a log ratio
    of exactly zero: the feature exists, passes every completeness rule, and
    carries no information. That is invisible to a completeness count and is
    precisely the kind of thing a post-retrieval audit exists to surface.
    """
    def usable(year: int) -> bool:
        value = values.get(year)
        return (isinstance(value, (int, float)) and not isinstance(value, bool)
                and value > 0)

    constructible: list[int] = []
    zero_change: list[int] = []
    for year in values:
        predictor_year = year + 1
        if usable(year) and usable(year - 1):
            constructible.append(predictor_year)
            if math.isclose(values[year], values[year - 1], rel_tol=0.0,
                            abs_tol=0.0):
                zero_change.append(predictor_year)
    constructible.sort()
    zero_change.sort()

    # The longest run of consecutive predictor years whose FX change is
    # identically zero — the span over which the feature is constant.
    longest_run = 0
    run = 0
    previous = None
    for year in zero_change:
        run = run + 1 if previous is not None and year == previous + 1 else 1
        longest_run = max(longest_run, run)
        previous = year

    # The longest run is not automatically the interesting one: a peg in the
    # 1960s says nothing about a modern development sample. What matters is
    # whether the MOST RECENT usable predictor years are degenerate, because
    # those are the years a contemporary sample actually lands on. Reported
    # separately so the two can never be confused.
    trailing_zero_run: list[int] = []
    if constructible and zero_change:
        year = max(constructible)
        while year in zero_change:
            trailing_zero_run.append(year)
            year -= 1
    trailing_zero_run.sort()

    return {
        "feature_id": "intl_fx_change_official_lag1_wdi",
        "indicator_code": FX_CODE,
        "transformation": "FX_LAG1_t = 100 * ln(E_(t-1) / E_(t-2))",
        "required_observation_years": ["t-1", "t-2"],
        "positivity_required": True,
        "constructible_predictor_years": len(constructible),
        "constructible_predictor_year_first":
            min(constructible) if constructible else None,
        "constructible_predictor_year_last":
            max(constructible) if constructible else None,
        # Defined but information-free.
        "degenerate_zero_change_predictor_years": len(zero_change),
        "degenerate_zero_change_predictor_year_list": zero_change,
        "longest_consecutive_zero_change_run": longest_run,
        # The decision-relevant one: degeneracy at the RECENT end.
        "trailing_zero_change_predictor_years": len(trailing_zero_run),
        "trailing_zero_change_predictor_year_list": trailing_zero_run,
    }


def build_audit_report(series: dict[str, dict[str, Any]],
                       values: dict[str, dict[int, Any]]) -> dict[str, Any]:
    """Combine both series into the contract-level availability picture."""
    cpi = derive_cpi_feature_availability(values[CPI_CODE])
    fx = derive_fx_feature_availability(values[FX_CODE])

    # The contract requires BOTH features complete on the same row, so the
    # binding constraint is the intersection — reported at SERIES level. This
    # is not the Gate: no sample, no threshold, no admission.
    cpi_years = set()
    if cpi["constructible_predictor_year_first"] is not None:
        cpi_years = set(range(cpi["constructible_predictor_year_first"],
                              cpi["constructible_predictor_year_last"] + 1))
    fx_years = set()
    if fx["constructible_predictor_year_first"] is not None:
        fx_years = set(range(fx["constructible_predictor_year_first"],
                             fx["constructible_predictor_year_last"] + 1))
    both = sorted(cpi_years & fx_years)
    binding = None
    if both:
        if fx["constructible_predictor_year_last"] < cpi[
                "constructible_predictor_year_last"]:
            binding = FX_CODE
        elif cpi["constructible_predictor_year_last"] < fx[
                "constructible_predictor_year_last"]:
            binding = CPI_CODE

    return {
        "action_id": ACTION_ID,
        "authorized_scope": AUTHORIZED_SCOPE,
        "audit_level": "series_level_only_never_sample_level",
        "series": [series[CPI_CODE], series[FX_CODE]],
        "feature_availability": [cpi, fx],
        "both_features_constructible_predictor_years": len(both),
        "both_features_constructible_predictor_year_first":
            min(both) if both else None,
        "both_features_constructible_predictor_year_last":
            max(both) if both else None,
        "binding_constraint_indicator": binding,
        # Everything the Gate would need is deliberately absent.
        "candidate_coverage_computed": False,
        "block_coverage_computed": False,
        "coverage_thresholds_applied": False,
        "admission_decision_made": False,
        "company_rows_touched": 0,
    }
