"""Stage128 D2 — Boundary-Month As-of Trailing Equity Return.

This module implements ONLY the D2 amendment to the M2 equity-return
construct that was frozen under Stage125/Stage127 as D0
(``equity_return_window`` in :mod:`stage127_m2_market_data_gate`).

Scope discipline (frozen by the Stage128 design-freeze authorization):

* the shared 12-calendar-month window ``W``, ``t0``, ``T*``, trading-day
  sequence and daily-return adjacency are NOT recomputed here — this module
  consumes the same ``window`` list produced by
  :func:`stage127_m2_market_data_gate.pair_scientific_window`;
* ``realized_volatility`` and ``amihud_illiquidity`` are UNCHANGED and are
  not reimplemented here; callers keep using
  :func:`stage127_m2_market_data_gate.compute_pair_features` for those two
  features;
* only the two OBSERVED adjusted-price endpoints used to build the
  cumulative equity-return ratio are reselected, from the exact endpoints
  (``window[0]``, ``window[-1]``) to a boundary-month as-of search;
* the calendar convention for boundary-month membership is GREGORIAN;
* no imputation, forward/backward fill, interpolation, extrapolation,
  cross-month fallback, raw/unadjusted-close substitution or synthetic
  adjusted price is ever used;
* the ``>= 126`` usable-daily-return floor is the existing frozen rule,
  evaluated over the SAME ``daily_simple_returns(window)`` sequence as D0 —
  it is not reimplemented here.

This module performs no market-data retrieval, no model fitting, no
prediction, and no canonical Gate execution. It is a pure function library
over an already-materialized ``window`` (a list of observation dicts with at
least ``trading_date`` (ISO ``YYYY-MM-DD``) and ``adjusted_close`` keys, in
ascending trading-date order, as produced by ``pair_scientific_window``).
"""

from __future__ import annotations

from typing import Any


def _gregorian_month_key(trading_date_iso: str) -> str:
    """``YYYY-MM`` Gregorian calendar-month key for a trading date."""
    return trading_date_iso[:7]


def find_start_boundary_price(
    window: list[dict[str, Any]], t0_trading_date: str,
) -> dict[str, Any]:
    """First trading observation on/after ``t0`` within t0's Gregorian month.

    Returns a dict with ``trading_date`` and ``adjusted_close`` of the
    selected observation, or ``{}`` if no such observation carries a valid
    adjusted close. Never searches outside ``t0``'s calendar month and never
    falls back to an adjacent month.
    """
    month = _gregorian_month_key(t0_trading_date)
    for obs in window:
        if obs["trading_date"] < t0_trading_date:
            continue
        if _gregorian_month_key(obs["trading_date"]) != month:
            break  # window is ascending; once we leave the month, stop
        if obs["adjusted_close"] is not None:
            return {
                "trading_date": obs["trading_date"],
                "adjusted_close": obs["adjusted_close"],
            }
    return {}


def find_end_boundary_price(
    window: list[dict[str, Any]], t_star_trading_date: str,
) -> dict[str, Any]:
    """Last trading observation on/before ``T*`` within T*'s Gregorian month.

    Returns a dict with ``trading_date`` and ``adjusted_close`` of the
    selected observation, or ``{}`` if no such observation carries a valid
    adjusted close. Never searches outside ``T*``'s calendar month and never
    falls back to an adjacent month.
    """
    month = _gregorian_month_key(t_star_trading_date)
    for obs in reversed(window):
        if obs["trading_date"] > t_star_trading_date:
            continue
        if _gregorian_month_key(obs["trading_date"]) != month:
            break  # window scanned in descending order; leaving month stops
        if obs["adjusted_close"] is not None:
            return {
                "trading_date": obs["trading_date"],
                "adjusted_close": obs["adjusted_close"],
            }
    return {}


#: Frozen floor, identical to MIN_VALID_RETURN_OBSERVATIONS in Stage127.
MIN_USABLE_DAILY_RETURNS_D2 = 126


def compute_d2_equity_return(
    window: list[dict[str, Any]],
    usable_daily_return_count: int,
) -> dict[str, Any]:
    """Compute the D2 boundary-month as-of trailing equity return.

    ``usable_daily_return_count`` must be computed by the caller from the
    SAME frozen ``daily_simple_returns(window)`` used for D0/realized
    volatility/Amihud — it is not recomputed here, so D2 can never silently
    diverge from the shared adjacency/missing-price rules.
    """
    result: dict[str, Any] = {
        "equity_return_d2": None,
        "d2_start_trading_date": "",
        "d2_end_trading_date": "",
        "d2_status": "",
    }
    if not window:
        result["d2_status"] = "UNAVAILABLE_EMPTY_WINDOW"
        return result

    t0_date = window[0]["trading_date"]
    t_star_date = window[-1]["trading_date"]

    start = find_start_boundary_price(window, t0_date)
    end = find_end_boundary_price(window, t_star_date)

    reasons: list[str] = []
    if usable_daily_return_count < MIN_USABLE_DAILY_RETURNS_D2:
        reasons.append(
            f"usable_daily_return_count={usable_daily_return_count} < "
            f"{MIN_USABLE_DAILY_RETURNS_D2}"
        )
    if not start:
        reasons.append("no valid adjusted_close in start-boundary month")
    if not end:
        reasons.append("no valid adjusted_close in end-boundary month")

    result["d2_start_trading_date"] = start.get("trading_date", "")
    result["d2_end_trading_date"] = end.get("trading_date", "")

    if reasons:
        result["d2_status"] = "UNAVAILABLE: " + "; ".join(reasons)
        return result

    p_start = start["adjusted_close"]
    p_end = end["adjusted_close"]
    if p_start == 0:
        result["d2_status"] = "UNAVAILABLE: start adjusted_close is zero"
        return result

    result["equity_return_d2"] = p_end / p_start - 1
    result["d2_status"] = "OBSERVED_COMPLETE"
    return result
