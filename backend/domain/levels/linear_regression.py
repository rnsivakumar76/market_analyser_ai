"""
Linear Regression slope — pure calculation, no pandas dependency.

Used to determine the 'Line of Least Resistance' direction.
"""

from __future__ import annotations

import numpy as np
from typing import Sequence

from ..constants import INDICATOR_LRL_PERIOD, INDICATOR_LRL_SLOPE_THRESHOLD


def calculate_linear_regression_slope(
    closes: Sequence[float],
    period: int = INDICATOR_LRL_PERIOD,
) -> float:
    """
    Compute the slope of the linear regression line over the last `period` bars,
    normalised by the current price.

    Normalised slope = raw_slope / last_close

    Returns:
        Normalised slope as a float.
        Returns 0.0 when insufficient data.
    """
    arr = np.asarray(closes, dtype=float)
    if len(arr) < period:
        return 0.0

    window = arr[-period:]
    x = np.arange(period, dtype=float)
    slope, _ = np.polyfit(x, window, 1)

    last_price = window[-1]
    if last_price == 0.0:
        return 0.0

    return float(slope / last_price)


def classify_slope(normalised_slope: float, threshold: float = INDICATOR_LRL_SLOPE_THRESHOLD) -> str:
    """
    Map a normalised slope to a direction label.

    Returns: 'up' | 'down' | 'flat'
    """
    if normalised_slope > threshold:
        return "up"
    if normalised_slope < -threshold:
        return "down"
    return "flat"
