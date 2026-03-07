"""
Standard Pivot Points — pure calculation, no pandas dependency.

Formula: Pivot = (H + L + C) / 3
R1 = 2P - L,  S1 = 2P - H
R2 = P + (H - L),  S2 = P - (H - L)
R3 = H + 2*(P - L),  S3 = L - 2*(H - P)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PivotValues:
    pivot: float
    r1: float
    r2: float
    r3: float
    s1: float
    s2: float
    s3: float


_ZERO_PIVOT = PivotValues(pivot=0.0, r1=0.0, r2=0.0, r3=0.0, s1=0.0, s2=0.0, s3=0.0)


def calculate_pivot_points(high: float, low: float, close: float) -> PivotValues:
    """
    Compute standard pivot points from a single bar's High, Low, Close.

    Typically called with the previous complete session's OHLC data.

    Args:
        high:  Session high.
        low:   Session low.
        close: Session close.

    Returns:
        PivotValues dataclass (all values rounded to 2 decimal places).
        Returns all-zero PivotValues when high == low == close == 0.
    """
    if high == 0 and low == 0 and close == 0:
        return _ZERO_PIVOT

    pivot = (high + low + close) / 3.0
    r1 = (2.0 * pivot) - low
    s1 = (2.0 * pivot) - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)
    r3 = high + 2.0 * (pivot - low)
    s3 = low - 2.0 * (high - pivot)

    return PivotValues(
        pivot=round(pivot, 2),
        r1=round(r1, 2),
        r2=round(r2, 2),
        r3=round(r3, 2),
        s1=round(s1, 2),
        s2=round(s2, 2),
        s3=round(s3, 2),
    )


def classify_price_vs_pivots(price: float, pivots: PivotValues) -> str:
    """
    Classify the current price relative to pivot structure.

    Returns one of:
      'above_r2' | 'between_r1_r2' | 'between_pivot_r1' |
      'between_s1_pivot' | 'between_s2_s1' | 'below_s2'
    """
    if price > pivots.r2:
        return "above_r2"
    if price > pivots.r1:
        return "between_r1_r2"
    if price > pivots.pivot:
        return "between_pivot_r1"
    if price > pivots.s1:
        return "between_s1_pivot"
    if price > pivots.s2:
        return "between_s2_s1"
    return "below_s2"
