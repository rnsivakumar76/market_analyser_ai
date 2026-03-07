"""
ATR (Average True Range) — pure calculation, no pandas dependency.

Input:  parallel arrays of highs, lows, closes
Output: float (latest ATR value)
"""

from __future__ import annotations

import numpy as np
from typing import Sequence

from ..constants import INDICATOR_ATR_PERIOD


def calculate_tr_series(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
) -> np.ndarray:
    """
    Compute the True Range series.

    TR[i] = max(High[i]-Low[i],  |High[i]-Close[i-1]|,  |Low[i]-Close[i-1]|)
    TR[0] = High[0] - Low[0]  (no previous close)

    Returns: np.ndarray of same length as inputs.
    """
    h = np.asarray(highs, dtype=float)
    l = np.asarray(lows, dtype=float)
    c = np.asarray(closes, dtype=float)

    if len(h) == 0:
        return np.array([], dtype=float)

    hl = h - l
    # Shift close by 1 (prev close); first bar has no prev close
    prev_c = np.empty_like(c)
    prev_c[0] = c[0]
    prev_c[1:] = c[:-1]

    hpc = np.abs(h - prev_c)
    lpc = np.abs(l - prev_c)

    tr = np.maximum(hl, np.maximum(hpc, lpc))
    return tr


def calculate_atr(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int = INDICATOR_ATR_PERIOD,
) -> float:
    """
    Calculate the Average True Range (simple rolling mean of TR).

    Args:
        highs, lows, closes: Parallel price arrays.
        period: ATR smoothing period (default 14).

    Returns:
        Latest ATR value, or 0.0 when insufficient data.
    """
    h = np.asarray(highs, dtype=float)
    l = np.asarray(lows, dtype=float)
    c = np.asarray(closes, dtype=float)

    if len(c) < period + 1:
        return 0.0

    tr = calculate_tr_series(h, l, c)
    atr = float(np.mean(tr[-period:]))

    return 0.0 if np.isnan(atr) else round(atr, 6)


def calculate_atr_series(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int = INDICATOR_ATR_PERIOD,
) -> np.ndarray:
    """
    Return the full rolling ATR series (same length as inputs, NaN for warmup).
    Used for percentile-rank calculations.
    """
    h = np.asarray(highs, dtype=float)
    l = np.asarray(lows, dtype=float)
    c = np.asarray(closes, dtype=float)
    n = len(c)
    result = np.full(n, np.nan)

    if n < period + 1:
        return result

    tr = calculate_tr_series(h, l, c)
    for i in range(period - 1, n):
        result[i] = np.mean(tr[i - period + 1: i + 1])

    return result
