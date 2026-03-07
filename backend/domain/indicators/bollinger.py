"""
Bollinger Bands — pure calculation, no pandas dependency.

Input:  sequence of closing prices
Output: BollingerResult dataclass
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import Sequence

from ..constants import BB_PERIOD, BB_STD_DEV


@dataclass(frozen=True)
class BollingerResult:
    upper: float    # Upper band  (MA + std_dev * sigma)
    middle: float   # Middle band (simple moving average)
    lower: float    # Lower band  (MA - std_dev * sigma)
    width: float    # Band width as % of middle (volatility proxy)


def calculate_bollinger_bands(
    closes: Sequence[float],
    period: int = BB_PERIOD,
    std_dev: float = BB_STD_DEV,
) -> BollingerResult:
    """
    Calculate Bollinger Bands for the latest bar.

    Args:
        closes:   Sequence of closing prices (at least `period` values).
        period:   Rolling window (default 20).
        std_dev:  Number of standard deviations (default 2).

    Returns:
        BollingerResult with upper, middle, lower, width.
        All values are 0.0 when insufficient data.
    """
    arr = np.asarray(closes, dtype=float)

    if len(arr) < period:
        return BollingerResult(upper=0.0, middle=0.0, lower=0.0, width=0.0)

    window = arr[-period:]
    ma = float(np.mean(window))
    sigma = float(np.std(window, ddof=1))  # ddof=1 matches pandas default

    upper = ma + std_dev * sigma
    lower = ma - std_dev * sigma
    width = ((upper - lower) / ma * 100.0) if ma != 0 else 0.0

    return BollingerResult(
        upper=round(upper, 6),
        middle=round(ma, 6),
        lower=round(lower, 6),
        width=round(width, 4),
    )


def calculate_bollinger_series(
    closes: Sequence[float],
    period: int = BB_PERIOD,
    std_dev: float = BB_STD_DEV,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Return (upper_series, middle_series, lower_series) arrays of the same length as closes.
    NaN for the warmup period.
    """
    arr = np.asarray(closes, dtype=float)
    n = len(arr)
    upper = np.full(n, np.nan)
    middle = np.full(n, np.nan)
    lower = np.full(n, np.nan)

    for i in range(period - 1, n):
        window = arr[i - period + 1: i + 1]
        ma = np.mean(window)
        sigma = np.std(window, ddof=1)
        middle[i] = ma
        upper[i] = ma + std_dev * sigma
        lower[i] = ma - std_dev * sigma

    return upper, middle, lower


def is_band_reentry(
    closes: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    period: int = BB_PERIOD,
    std_dev: float = BB_STD_DEV,
    trend_is_bullish: bool = True,
) -> bool:
    """
    Detect a Bollinger Band re-entry (failed breakout).

    Bullish context: price previously tagged upper band, now closed back inside.
    Bearish context: price previously tagged lower band, now closed back inside.

    Requires at least period + 3 bars.
    """
    arr_c = np.asarray(closes, dtype=float)
    arr_h = np.asarray(highs, dtype=float)
    arr_l = np.asarray(lows, dtype=float)

    if len(arr_c) < period + 3:
        return False

    upper_s, _, lower_s = calculate_bollinger_series(arr_c, period, std_dev)

    if trend_is_bullish:
        prev2_tag = arr_h[-3] >= upper_s[-3] if not np.isnan(upper_s[-3]) else False
        prev1_tag = arr_h[-2] >= upper_s[-2] if not np.isnan(upper_s[-2]) else False
        reentry = arr_c[-1] < upper_s[-1] if not np.isnan(upper_s[-1]) else False
        return bool((prev2_tag or prev1_tag) and reentry)
    else:
        prev2_tag = arr_l[-3] <= lower_s[-3] if not np.isnan(lower_s[-3]) else False
        prev1_tag = arr_l[-2] <= lower_s[-2] if not np.isnan(lower_s[-2]) else False
        reentry = arr_c[-1] > lower_s[-1] if not np.isnan(lower_s[-1]) else False
        return bool((prev2_tag or prev1_tag) and reentry)
