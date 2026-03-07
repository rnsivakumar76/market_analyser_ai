"""
RVOL (Relative Volume) — pure calculation, no pandas dependency.

Compares current bar volume to the average volume of the same time-of-day
over the previous N trading days. This is more accurate than a simple MA.
"""

from __future__ import annotations

import numpy as np
from typing import Sequence

from ..constants import RVOL_LOOKBACK_DAYS, RVOL_HIGH, RVOL_MODERATE, RVOL_HIGH_INTENT


def calculate_rvol(
    current_volume: float,
    same_time_volumes: Sequence[float],
) -> float:
    """
    Compute Relative Volume.

    Args:
        current_volume:      Volume of the current bar.
        same_time_volumes:   Historical volumes at the same time-of-day
                             (typically the last RVOL_LOOKBACK_DAYS bars
                              at this same intraday time slot).

    Returns:
        RVOL ratio (float, rounded to 2 dp).
        Returns 1.0 when no historical data is available.
    """
    arr = np.asarray(same_time_volumes, dtype=float)
    arr = arr[~np.isnan(arr)]  # drop any NaN sentinel values

    if len(arr) == 0 or np.sum(arr) == 0:
        return 1.0

    avg_hist_vol = float(np.mean(arr))
    if avg_hist_vol == 0.0:
        return 1.0

    return round(float(current_volume / avg_hist_vol), 2)


def classify_rvol(rvol: float) -> str:
    """
    Map an RVOL ratio to an intent label.

    Returns:
        'high'     — institutions actively participating (RVOL >= RVOL_HIGH)
        'moderate' — watch for volume surge (RVOL >= RVOL_MODERATE)
        'light'    — wait for volume before full size
    """
    if rvol >= RVOL_HIGH:
        return "high"
    if rvol >= RVOL_MODERATE:
        return "moderate"
    return "light"


def is_high_intent(rvol: float) -> bool:
    """Return True when RVOL exceeds the high-intent threshold."""
    return rvol > RVOL_HIGH_INTENT
