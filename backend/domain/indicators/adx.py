"""
ADX (Average Directional Index) — pure calculation, no pandas dependency.

Input:  parallel arrays of highs, lows, closes
Output: float (latest ADX value, 0–100)
"""

from __future__ import annotations

import numpy as np
from typing import Sequence

from ..constants import INDICATOR_ADX_PERIOD, INDICATOR_ADX_STRONG_TREND, INDICATOR_ADX_DEVELOPING_TREND


def calculate_directional_movement(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int = INDICATOR_ADX_PERIOD,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute smoothed +DM, -DM and TR arrays.

    Returns: (plus_dm_smooth, minus_dm_smooth, tr_smooth) — each length n.
    """
    h = np.asarray(highs, dtype=float)
    l = np.asarray(lows, dtype=float)
    c = np.asarray(closes, dtype=float)
    n = len(h)

    # True Range
    prev_c = np.empty_like(c)
    prev_c[0] = c[0]
    prev_c[1:] = c[:-1]
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev_c), np.abs(l - prev_c)))

    # Raw Directional Movement
    up_move = np.diff(h, prepend=h[0])
    down_move = np.diff(l, prepend=l[0]) * -1.0

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    # Simple rolling mean (matches existing analyzer behaviour)
    plus_dm_s = np.full(n, np.nan)
    minus_dm_s = np.full(n, np.nan)
    tr_s = np.full(n, np.nan)

    for i in range(period - 1, n):
        plus_dm_s[i] = np.mean(plus_dm[i - period + 1: i + 1])
        minus_dm_s[i] = np.mean(minus_dm[i - period + 1: i + 1])
        tr_s[i] = np.mean(tr[i - period + 1: i + 1])

    return plus_dm_s, minus_dm_s, tr_s


def calculate_adx(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int = INDICATOR_ADX_PERIOD,
) -> float:
    """
    Calculate the Average Directional Index.

    ADX measures trend *strength*, not direction.
      >= 30  → Strong trend
      >= 20  → Developing trend
      <  20  → Weak / sideways

    Returns:
        ADX float in [0, 100], or 0.0 when insufficient data.
    """
    h = np.asarray(highs, dtype=float)
    if len(h) < period * 2 + 1:
        return 0.0

    plus_dm_s, minus_dm_s, tr_s = calculate_directional_movement(h, lows, closes, period)

    with np.errstate(divide="ignore", invalid="ignore"):
        plus_di = np.where(tr_s > 0, 100.0 * plus_dm_s / tr_s, 0.0)
        minus_di = np.where(tr_s > 0, 100.0 * minus_dm_s / tr_s, 0.0)
        denom = plus_di + minus_di
        dx = np.where(denom > 0, 100.0 * np.abs(plus_di - minus_di) / denom, 0.0)

    # ADX = rolling mean of DX
    n = len(dx)
    adx_arr = np.full(n, np.nan)
    for i in range(period - 1, n):
        window = dx[i - period + 1: i + 1]
        valid = window[~np.isnan(window)]
        if len(valid) == period:
            adx_arr[i] = np.mean(valid)

    latest = adx_arr[~np.isnan(adx_arr)]
    return float(latest[-1]) if len(latest) > 0 else 0.0


def classify_adx(adx: float) -> str:
    """
    Map an ADX value to a trend-strength label.

    Returns one of: 'strong' | 'developing' | 'weak'
    """
    if adx >= INDICATOR_ADX_STRONG_TREND:
        return "strong"
    if adx >= INDICATOR_ADX_DEVELOPING_TREND:
        return "developing"
    return "weak"
