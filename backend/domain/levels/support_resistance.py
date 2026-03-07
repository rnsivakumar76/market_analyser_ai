"""
Support & Resistance level detection — pure calculation, no pandas dependency.

Uses swing high/low detection (local extrema) on raw price arrays.
"""

from __future__ import annotations

import numpy as np
from typing import Sequence


def find_swing_lows(
    lows: Sequence[float],
    lookback: int = 1,
) -> list[float]:
    """
    Identify swing lows: local minima where low[i] < low[i-1] and low[i] < low[i+1].

    Args:
        lows:     Array of bar low prices.
        lookback: Bars on each side required to confirm a swing (default 1).

    Returns:
        Sorted list of swing-low price levels (ascending).
        Falls back to the single global minimum when no swings are found.
    """
    arr = np.asarray(lows, dtype=float)
    n = len(arr)
    supports = []

    for i in range(lookback, n - lookback):
        left_ok = all(arr[i] < arr[i - j] for j in range(1, lookback + 1))
        right_ok = all(arr[i] < arr[i + j] for j in range(1, lookback + 1))
        if left_ok and right_ok:
            supports.append(float(arr[i]))

    return sorted(supports) if supports else [float(np.min(arr))]


def find_swing_highs(
    highs: Sequence[float],
    lookback: int = 1,
) -> list[float]:
    """
    Identify swing highs: local maxima where high[i] > high[i-1] and high[i] > high[i+1].

    Args:
        highs:    Array of bar high prices.
        lookback: Bars on each side required to confirm a swing (default 1).

    Returns:
        Sorted list of swing-high price levels (descending, i.e. nearest resistance first).
        Falls back to the single global maximum when no swings are found.
    """
    arr = np.asarray(highs, dtype=float)
    n = len(arr)
    resistances = []

    for i in range(lookback, n - lookback):
        left_ok = all(arr[i] > arr[i - j] for j in range(1, lookback + 1))
        right_ok = all(arr[i] > arr[i + j] for j in range(1, lookback + 1))
        if left_ok and right_ok:
            resistances.append(float(arr[i]))

    return sorted(resistances, reverse=True) if resistances else [float(np.max(arr))]


def nearest_support_below(
    price: float,
    support_levels: list[float],
    tolerance_pct: float = 0.02,
) -> tuple[float | None, bool]:
    """
    Find the nearest support level at or below current price.

    Args:
        price:          Current price.
        support_levels: Sorted list of support levels.
        tolerance_pct:  Distance threshold to be considered 'near' (default 2%).

    Returns:
        (support_level | None, is_near_support)
    """
    candidates = [lv for lv in support_levels if lv <= price]
    if not candidates:
        return None, False
    nearest = max(candidates)
    distance_pct = (price - nearest) / price if price > 0 else 0.0
    return nearest, (distance_pct <= tolerance_pct)
