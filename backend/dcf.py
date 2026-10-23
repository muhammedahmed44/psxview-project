"""Reverse + forward DCF. Pure functions, no web code. Port of the HTML tool's math."""
from __future__ import annotations

# The HTML tool fixes terminal growth at 3.5% when working backward
# from the current market price to the implied growth rate.
REVERSE_TERMINAL = 0.035


def required_return(rf: float, erp: float, beta: float) -> float:
    """
    CAPM: required return = risk-free rate + beta * equity risk premium.

    All inputs and outputs are fractions, e.g. 0.11 means 11%.
    """
    return rf + beta * erp


def dcf_value(fcf0: float, g: float, r: float, g_term: float, years: int) -> float:
    """
    Fair value per share: PV of `years` of growing cash flow + PV of terminal value.

    fcf0 = free cash flow (or EPS) per share in year 0
    g    = growth rate during the forecast period (fraction)
    r    = required return/discount rate (fraction)
    g_term = perpetual growth rate after the forecast period (fraction)
    years = length of the forecast period
    """
    if r <= g_term:
        raise ValueError("required return must be higher than terminal growth")

    pv, fcf_n = 0.0, fcf0

    # Sum the present value of each year's cash flow.
    for t in range(1, years + 1):
        fcf_n = fcf0 * (1 + g) ** t
        pv += fcf_n / (1 + r) ** t

    # Gordon-growth terminal value, discounted back to today.
    terminal = fcf_n * (1 + g_term) / (r - g_term)

    return pv + terminal / (1 + r) ** years


def solve_implied_growth(price: float, fcf0: float, r: float, years: int,
                         g_term: float = REVERSE_TERMINAL) -> float | None:
    """
    Find the growth rate the current market price already implies.

    Returns None if the price implies more than 500% growth (deemed nonsensical).
    Uses bisection between -99% and 500%.
    """
    # Guard against bad inputs that make the math undefined.
    if fcf0 <= 0 or price <= 0 or r <= g_term:
        return None

    # If even 500% growth cannot justify the price, the answer is "too high".
    if dcf_value(fcf0, 5.0, r, g_term, years) < price:
        return None

    lo, hi = -0.99, 5.0

    # Bisection: narrow the growth range until the bounds are very close.
    for _ in range(200):
        mid = (lo + hi) / 2
        if dcf_value(fcf0, mid, r, g_term, years) < price:
            lo = mid
        else:
            hi = mid

        if hi - lo < 1e-9:
            break

    return (lo + hi) / 2


def sensitivity(fcf0: float, price: float, r: float, g_term: float, years: int):
    """
    Compute upside % across a grid of growth assumptions.

    Growth ranges from 0% to 36% in steps of 2%, matching the frontend chart.
    """
    growth = list(range(0, 37, 2))
    upside = [(dcf_value(fcf0, g / 100, r, g_term, years) - price) / price * 100 for g in growth]
    return {"growth_pct": growth, "upside_pct": upside}


def compute(*, eps: float, price: float, rf_pct: float, erp_pct: float, beta: float,
            years: int, growth_pct: float, terminal_pct: float) -> dict:
    """
    Main entry point: compute all valuation outputs from raw inputs.

    Inputs are in user-facing units (percentages, not fractions).
    Returns required return, implied growth, fair value, upside %, and sensitivity grid.
    """
    # Convert percentages to fractions for the math functions.
    r = required_return(rf_pct / 100, erp_pct / 100, beta)
    g_term = terminal_pct / 100

    if r <= g_term:
        raise ValueError("required return must be higher than terminal growth")

    # Implied growth solves backward from the current price.
    implied = solve_implied_growth(price, eps, r, years)

    # Fair value solves forward from the user's growth estimate.
    fair = dcf_value(eps, growth_pct / 100, r, g_term, years)

    return {
        "required_return_pct": r * 100,
        "implied_growth_pct": None if implied is None else implied * 100,
        "fair_value": fair,
        "upside_pct": (fair - price) / price * 100,
        "sensitivity": sensitivity(eps, price, r, g_term, years),
    }