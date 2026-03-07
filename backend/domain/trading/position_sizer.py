"""
Position Sizing — pure domain logic, no pandas / Pydantic dependency.

All formulas use primitive floats.
Correlation penalty, risk amount, and unit count are computed here.
"""

from __future__ import annotations

from ..constants import (
    POSITION_CORRELATION_FLOOR,
    POSITION_CORRELATION_MAX_PENALTY,
    POSITION_CORRELATION_PENALTY_SLOPE,
    POSITION_FALLBACK_SL_MULTIPLIER,
    VOLATILITY_ATR_SL_MULTIPLIER,
)


def calculate_correlation_penalty(avg_correlation: float) -> float:
    """
    Compute the position-size reduction factor due to correlation with other signals.

    Formula:
      penalty = 0  when avg_correlation <= CORRELATION_FLOOR (0.3)
      penalty = min(MAX_PENALTY, (avg_correlation - FLOOR) * SLOPE)

    Args:
        avg_correlation: Average Pearson correlation of this instrument with
                         all other currently trade-worthy instruments (0 – 1).

    Returns:
        Penalty factor in [0.0, MAX_PENALTY] (e.g. 0.4 means 40% size reduction).
    """
    if avg_correlation <= POSITION_CORRELATION_FLOOR:
        return 0.0
    raw = (avg_correlation - POSITION_CORRELATION_FLOOR) * POSITION_CORRELATION_PENALTY_SLOPE
    return round(min(raw, POSITION_CORRELATION_MAX_PENALTY), 4)


def calculate_risk_amount(
    portfolio_value: float,
    base_risk_percent: float,
    penalty_factor: float,
) -> float:
    """
    Compute the dollar risk amount after applying the correlation penalty.

    Args:
        portfolio_value:    Total account equity (dollars).
        base_risk_percent:  Base risk per trade as a percentage (e.g. 1.0 = 1%).
        penalty_factor:     Correlation penalty in [0, 1].

    Returns:
        Adjusted dollar risk amount.
    """
    final_risk_pct = base_risk_percent * (1.0 - penalty_factor)
    return round(portfolio_value * (final_risk_pct / 100.0), 2)


def calculate_risk_per_unit(
    entry_price: float,
    stop_loss: float,
    atr: float,
    fallback_multiplier: float = POSITION_FALLBACK_SL_MULTIPLIER,
) -> float:
    """
    Compute the per-unit risk (distance between entry and stop loss).

    Falls back to ATR × fallback_multiplier when stop_loss ≈ entry_price
    (guard against degenerate data).

    Args:
        entry_price:        Trade entry price.
        stop_loss:          Hard stop-loss price.
        atr:                Current ATR for fallback calculation.
        fallback_multiplier: ATR multiplier for fallback (default 1.5).

    Returns:
        Risk per unit (always positive).
    """
    risk = abs(entry_price - stop_loss)
    if risk < 1e-4:
        risk = atr * fallback_multiplier
    return round(risk, 6)


def calculate_position_units(
    portfolio_value: float,
    base_risk_percent: float,
    entry_price: float,
    stop_loss: float,
    atr: float,
    avg_correlation: float = 0.0,
) -> tuple[float, float, float, float]:
    """
    End-to-end position sizing calculation.

    Args:
        portfolio_value:    Total account equity (dollars).
        base_risk_percent:  Base risk per trade as a percentage (e.g. 1.0 = 1%).
        entry_price:        Trade entry price.
        stop_loss:          Hard stop-loss price.
        atr:                Current ATR (used for fallback risk_per_unit).
        avg_correlation:    Average correlation with other active signals (0 – 1).

    Returns:
        (suggested_units, risk_amount, penalty_factor, final_risk_percent)
        suggested_units is rounded to a sensible precision.
    """
    penalty = calculate_correlation_penalty(avg_correlation)
    final_risk_pct = base_risk_percent * (1.0 - penalty)
    risk_amount = calculate_risk_amount(portfolio_value, base_risk_percent, penalty)
    risk_per_unit = calculate_risk_per_unit(entry_price, stop_loss, atr)

    if risk_per_unit == 0:
        return 0.0, 0.0, penalty, final_risk_pct

    raw_units = risk_amount / risk_per_unit

    # Round to sensible precision
    if raw_units >= 100:
        units = round(raw_units)
    elif raw_units >= 10:
        units = round(raw_units, 1)
    else:
        units = round(raw_units, 2)

    return float(units), float(risk_amount), round(penalty, 4), round(final_risk_pct, 2)
