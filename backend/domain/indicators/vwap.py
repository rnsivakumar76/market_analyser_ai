"""
VWAP (Volume Weighted Average Price) — pure calculation, no pandas dependency.

Input:  parallel arrays of highs, lows, closes, volumes
Output: (vwap: float, distance_pct: float)
"""

from __future__ import annotations

import numpy as np
from typing import Sequence

from ..constants import INDICATOR_VWAP_PERIOD, INDICATOR_VWAP_OVEREXTENDED_PCT


def calculate_vwap(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    volumes: Sequence[float],
    period: int = INDICATOR_VWAP_PERIOD,
) -> float:
    """
    Calculate Volume Weighted Average Price over the last `period` bars.

    VWAP = Σ(typical_price × volume) / Σ(volume)
    where typical_price = (high + low + close) / 3

    Returns:
        VWAP as a float, or 0.0 when volume is absent or insufficient.
    """
    h = np.asarray(highs, dtype=float)
    l = np.asarray(lows, dtype=float)
    c = np.asarray(closes, dtype=float)
    v = np.asarray(volumes, dtype=float)

    if len(c) == 0 or np.all(v == 0):
        return 0.0

    # Use the last `period` bars
    h_w = h[-period:]
    l_w = l[-period:]
    c_w = c[-period:]
    v_w = v[-period:]

    total_volume = np.sum(v_w)
    if total_volume == 0.0:
        return 0.0

    typical_price = (h_w + l_w + c_w) / 3.0
    return float(np.sum(typical_price * v_w) / total_volume)


def calculate_vwap_distance_pct(current_price: float, vwap: float) -> float:
    """
    Compute the percentage distance of current_price from VWAP.

    Positive = price above VWAP (overextended to upside).
    Negative = price below VWAP (discount to VWAP).

    Returns 0.0 when VWAP is 0.
    """
    if vwap == 0.0:
        return 0.0
    return float(((current_price - vwap) / vwap) * 100.0)


def classify_vwap_position(distance_pct: float) -> str:
    """
    Returns 'above' | 'extended_above' | 'below' | 'extended_below' | 'at'
    based on distance from VWAP.
    """
    if distance_pct > INDICATOR_VWAP_OVEREXTENDED_PCT:
        return "extended_above"
    if distance_pct > 0:
        return "above"
    if distance_pct < -INDICATOR_VWAP_OVEREXTENDED_PCT:
        return "extended_below"
    if distance_pct < 0:
        return "below"
    return "at"
