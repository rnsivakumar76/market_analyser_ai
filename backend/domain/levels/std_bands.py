"""
Standard Deviation Bands — pure calculation, no pandas dependency.

Used as volatility context around a moving average.
"""

from __future__ import annotations

import numpy as np
from typing import Sequence

from ..constants import STDBAND_PERIOD


def calculate_std_dev_bands(
    closes: Sequence[float],
    period: int = STDBAND_PERIOD,
) -> tuple[float, float]:
    """
    Calculate 1-sigma and 2-sigma standard deviation from the period mean.

    Args:
        closes: Sequence of closing prices.
        period: Rolling window (default 20).

    Returns:
        (std_1, std_2) — both 0.0 when insufficient data.
    """
    arr = np.asarray(closes, dtype=float)
    if len(arr) < period:
        return 0.0, 0.0

    window = arr[-period:]
    std = float(np.std(window, ddof=1))
    return round(std, 2), round(std * 2.0, 2)


def calculate_rolling_std(
    closes: Sequence[float],
    period: int = STDBAND_PERIOD,
) -> np.ndarray:
    """
    Return rolling std-dev series (same length as closes, NaN for warmup).
    ddof=1 to match pandas Series.std() default.
    """
    arr = np.asarray(closes, dtype=float)
    n = len(arr)
    result = np.full(n, np.nan)

    for i in range(period - 1, n):
        result[i] = np.std(arr[i - period + 1: i + 1], ddof=1)

    return result
