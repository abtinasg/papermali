"""Tests for the Stage128 D2 boundary-month as-of trailing equity return.

Development-side/synthetic fixtures ONLY. No production market data, no
final-test row, no model, no canonical Stage127 Gate execution.
"""
from __future__ import annotations

import statistics

import pytest

from src import stage127_m2_market_data_gate as g
from src import stage128_m2_d2_boundary_month_equity_return as d2


def obs(trading_date, adjusted_close, traded_value_rial=1_000, range_id="r1"):
    return {
        "trading_date": trading_date,
        "adjusted_close": adjusted_close,
        "traded_value_rial": traded_value_rial,
        "range_id": range_id,
        "adjusted_close_status": "present" if adjusted_close is not None else "missing",
    }


def make_window(cutoff_iso, dates_prices, traded_value_rial=1_000):
    """Build a synthetic observation stream and derive W via the frozen
    Stage127 window function, exactly as a real pair would."""
    observations = [
        obs(dt, px, traded_value_rial=traded_value_rial) for dt, px in dates_prices
    ]
    win = g.pair_scientific_window(cutoff_iso, observations)
    return win


def daily_business_dates(start: str, count: int):
    """Deterministic Mon-Fri trading calendar starting at ``start`` (ISO)."""
    from datetime import date, timedelta

    d = date.fromisoformat(start)
    out = []
    while len(out) < count:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def full_synthetic_pair(cutoff_iso="2026-06-15", n_days=300, start="2025-05-01",
                         start_month_missing_days=0, end_month_missing_days=0,
                         base_price=100.0):
    dates = daily_business_dates(start, n_days)
    prices = [(dt, base_price + i * 0.01) for i, dt in enumerate(dates)]
    win = make_window(cutoff_iso, prices)
    assert win["resolution"] == g.RESOLUTION_PASS
    window = win["window"]
    return win, window


# --------------------------------------------------------------------------- #
# Shared-window invariants (D2 must not disturb W, t0, T*, adjacency)
# --------------------------------------------------------------------------- #

def test_same_canonical_window_before_and_after_d2():
    win, window = full_synthetic_pair()
    # D2 consumes the window as-is; it never mutates or resizes it.
    before = list(window)
    returns = g.daily_simple_returns(window)
    d2.compute_d2_equity_return(window, len(returns))
    assert window == before


def test_same_t0_and_tstar_as_d0():
    win, window = full_synthetic_pair()
    d0 = g.compute_pair_features("2026-06-15", [
        obs(o["trading_date"], o["adjusted_close"], o["traded_value_rial"])
        for o in window
    ])
    assert window[0]["trading_date"] == d0["t0_trading_date"]
    assert window[-1]["trading_date"] == d0["tN_trading_date"]
    assert window[0]["trading_date"] == win["window_first_trading_date"]
    assert window[-1]["trading_date"] == win["t_star"]


def test_same_daily_return_count_realized_vol_amihud_as_d0():
    win, window = full_synthetic_pair()
    returns = g.daily_simple_returns(window)
    d0 = g.compute_pair_features("2026-06-15", [
        obs(o["trading_date"], o["adjusted_close"], o["traded_value_rial"])
        for o in window
    ])
    d2_result = d2.compute_d2_equity_return(window, len(returns))
    assert d0["usable_daily_return_count"] == len(returns)
    assert d0["realized_volatility"] == pytest.approx(
        statistics.stdev([r["r_t"] for r in returns])
    )
    # D2 changes only the return construct; volatility/Amihud are untouched
    # by this module (callers keep using compute_pair_features for them).
    assert "realized_volatility" not in d2_result
    assert "amihud_illiquidity" not in d2_result


# --------------------------------------------------------------------------- #
# Gregorian boundary-month semantics
# --------------------------------------------------------------------------- #

def test_start_boundary_picks_first_priced_day_on_or_after_t0_same_month():
    window = [
        obs("2026-01-30", None),
        obs("2026-01-31", 50.0),
        obs("2026-02-02", 51.0),
    ]
    # t0 = 2026-01-30 (first trading day of W); its Gregorian month is 2026-01
    start = d2.find_start_boundary_price(window, "2026-01-30")
    assert start == {"trading_date": "2026-01-31", "adjusted_close": 50.0}


def test_end_boundary_picks_last_priced_day_on_or_before_tstar_same_month():
    window = [
        obs("2026-05-28", 40.0),
        obs("2026-05-31", 41.0),
        obs("2026-06-01", None),
    ]
    # T* = 2026-06-01; its Gregorian month is 2026-06, which has no priced day
    end = d2.find_end_boundary_price(window, "2026-06-01")
    assert end == {}  # no cross-month fallback into 2026-05


def test_no_cross_month_fallback_for_start_boundary():
    window = [
        obs("2026-02-27", 10.0),  # prior month, has a price but t0 is in March
        obs("2026-03-02", None),
        obs("2026-03-03", None),
    ]
    start = d2.find_start_boundary_price(window, "2026-03-02")
    assert start == {}  # must not fall back to 2026-02-27


def test_no_cross_month_fallback_for_end_boundary():
    window = [
        obs("2026-03-30", None),
        obs("2026-03-31", None),
        obs("2026-04-01", 99.0),  # later month, must not be used as T*'s month
    ]
    end = d2.find_end_boundary_price(window, "2026-03-31")
    assert end == {}


def test_start_boundary_unavailable_when_whole_month_missing_price():
    window = [obs("2026-01-30", None), obs("2026-01-31", None), obs("2026-02-02", 1.0)]
    assert d2.find_start_boundary_price(window, "2026-01-30") == {}


# --------------------------------------------------------------------------- #
# Full D2 computation, floor, and no-imputation guarantees
# --------------------------------------------------------------------------- #

def test_d2_return_formula_matches_selected_endpoints():
    win, window = full_synthetic_pair()
    returns = g.daily_simple_returns(window)
    result = d2.compute_d2_equity_return(window, len(returns))
    start = d2.find_start_boundary_price(window, window[0]["trading_date"])
    end = d2.find_end_boundary_price(window, window[-1]["trading_date"])
    assert result["equity_return_d2"] == pytest.approx(
        end["adjusted_close"] / start["adjusted_close"] - 1
    )
    assert result["d2_status"] == "OBSERVED_COMPLETE"


def test_below_126_returns_remains_unavailable_even_with_both_boundary_prices():
    # Only ~40 trading days -> far fewer than 126 usable daily returns.
    win, window = full_synthetic_pair(n_days=40)
    returns = g.daily_simple_returns(window)
    assert len(returns) < d2.MIN_USABLE_DAILY_RETURNS_D2
    result = d2.compute_d2_equity_return(window, len(returns))
    assert result["equity_return_d2"] is None
    assert "usable_daily_return_count" in result["d2_status"]


def test_missing_start_boundary_month_price_yields_unavailable():
    win, window = full_synthetic_pair(n_days=300)
    window = list(window)
    month = window[0]["trading_date"][:7]
    window = [
        (o if o["trading_date"][:7] != month else obs(o["trading_date"], None))
        for o in window
    ]
    returns = g.daily_simple_returns(window)
    result = d2.compute_d2_equity_return(window, len(returns))
    assert result["equity_return_d2"] is None
    assert "start-boundary month" in result["d2_status"]


def test_no_imputation_no_raw_close_substitution():
    # A window whose only priced days sit outside both boundary months.
    window = [
        obs("2026-01-05", None),
        obs("2026-01-06", None),
        obs("2026-02-10", 77.0),  # only priced day, not in Jan (t0) or later
    ]
    start = d2.find_start_boundary_price(window, "2026-01-05")
    assert start == {}
    # No forward-fill from 2026-02-10 back into January is performed.


def test_d2_unavailable_on_empty_window():
    result = d2.compute_d2_equity_return([], 0)
    assert result["equity_return_d2"] is None
    assert result["d2_status"] == "UNAVAILABLE_EMPTY_WINDOW"


# --------------------------------------------------------------------------- #
# No model invocation / no canonical Gate execution guarantees
# --------------------------------------------------------------------------- #

def test_module_exposes_no_model_or_gate_execution_symbols():
    forbidden_substrings = ("fit", "predict", "gate_decision", "auc", "roc")
    public_names = [n for n in dir(d2) if not n.startswith("_")]
    for name in public_names:
        lowered = name.lower()
        for bad in forbidden_substrings:
            assert bad not in lowered, f"unexpected symbol {name!r} in D2 module"
