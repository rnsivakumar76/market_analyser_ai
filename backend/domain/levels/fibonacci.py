"""
Fibonacci Retracement & Extension Levels — pure calculation, no pandas dependency.

Retracements: 23.6%, 38.2%, 50%, 61.8%
Extensions:   127.2%, 161.8%
"""

from __future__ import annotations

from dataclasses import dataclass

from ..constants import (
    FIB_RET_236,
    FIB_RET_382,
    FIB_RET_500,
    FIB_RET_618,
    FIB_EXT_1272,
    FIB_EXT_1618,
)


@dataclass(frozen=True)
class FibValues:
    trend: str          # 'up' | 'down' | 'flat'
    swing_high: float
    swing_low: float
    ret_236: float
    ret_382: float
    ret_500: float
    ret_618: float
    ext_1272: float
    ext_1618: float


def calculate_fibonacci_levels(
    swing_high: float,
    swing_low: float,
    current_price: float,
) -> FibValues:
    """
    Compute Fibonacci retracements and extensions from a swing high/low pair.

    Direction is inferred from where current_price sits within the range:
      - Closer to high  → uptrend (retracements pull *down* from high)
      - Closer to low   → downtrend (retracements push *up* from low)

    Args:
        swing_high:    Highest price of the relevant swing.
        swing_low:     Lowest price of the relevant swing.
        current_price: Latest close (used only for trend direction inference).

    Returns:
        FibValues dataclass (all levels rounded to 2 decimal places).
    """
    diff = swing_high - swing_low

    if diff == 0:
        flat = FibValues(
            trend="flat",
            swing_high=swing_high,
            swing_low=swing_low,
            ret_236=swing_high,
            ret_382=swing_high,
            ret_500=swing_high,
            ret_618=swing_high,
            ext_1272=swing_high,
            ext_1618=swing_high,
        )
        return flat

    # Determine trend direction
    dist_from_low = current_price - swing_low
    dist_from_high = swing_high - current_price

    if dist_from_low >= dist_from_high:
        trend = "up"
        ret_236 = swing_high - diff * FIB_RET_236
        ret_382 = swing_high - diff * FIB_RET_382
        ret_500 = swing_high - diff * FIB_RET_500
        ret_618 = swing_high - diff * FIB_RET_618
        ext_1272 = swing_low + diff * FIB_EXT_1272
        ext_1618 = swing_low + diff * FIB_EXT_1618
    else:
        trend = "down"
        ret_236 = swing_low + diff * FIB_RET_236
        ret_382 = swing_low + diff * FIB_RET_382
        ret_500 = swing_low + diff * FIB_RET_500
        ret_618 = swing_low + diff * FIB_RET_618
        ext_1272 = swing_high - diff * FIB_EXT_1272
        ext_1618 = swing_high - diff * FIB_EXT_1618

    return FibValues(
        trend=trend,
        swing_high=round(swing_high, 2),
        swing_low=round(swing_low, 2),
        ret_236=round(ret_236, 2),
        ret_382=round(ret_382, 2),
        ret_500=round(ret_500, 2),
        ret_618=round(ret_618, 2),
        ext_1272=round(ext_1272, 2),
        ext_1618=round(ext_1618, 2),
    )
