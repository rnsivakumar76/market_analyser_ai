"""
RSI (Relative Strength Index) — pure calculation, no pandas dependency.

Input:  sequence of closing prices (list or np.ndarray)
Output: float in [0, 100]
"""

from __future__ import annotations

import numpy as np
from typing import Sequence

from ..constants import (
    INDICATOR_RSI_PERIOD,
    INDICATOR_RSI_OVERSOLD,
    INDICATOR_RSI_OVERBOUGHT,
    INDICATOR_RSI_BULLISH_THRESHOLD,
    INDICATOR_RSI_BEARISH_THRESHOLD,
)


def calculate_rsi(closes: Sequence[float], period: int = INDICATOR_RSI_PERIOD) -> float:
    """
    Calculate the Relative Strength Index using a simple rolling mean.

    Args:
        closes: Sequence of closing prices (at least period + 1 values).
        period: Lookback window (default 14).

    Returns:
        RSI value in [0, 100].  Returns 50.0 when insufficient data.
    """
    arr = np.asarray(closes, dtype=float)
    if len(arr) < period + 1:
        return 50.0

    deltas = np.diff(arr)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    # Simple rolling mean over the last `period` deltas
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])

    if avg_loss == 0.0:
        return 100.0 if avg_gain > 0 else 50.0

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return float(rsi)


def calculate_rsi_series(closes: Sequence[float], period: int = INDICATOR_RSI_PERIOD) -> np.ndarray:
    """
    Return the full RSI series (same length as closes, NaN for initial values).

    Useful for divergence detection — each element corresponds to one bar.
    """
    arr = np.asarray(closes, dtype=float)
    n = len(arr)
    rsi_arr = np.full(n, np.nan)

    if n < period + 1:
        return rsi_arr

    deltas = np.diff(arr)  # length n-1

    for i in range(period, n):
        window = deltas[i - period: i]
        avg_gain = np.mean(np.where(window > 0, window, 0.0))
        avg_loss = np.mean(np.where(window < 0, -window, 0.0))
        if avg_loss == 0.0:
            rsi_arr[i] = 100.0 if avg_gain > 0 else 50.0
        else:
            rs = avg_gain / avg_loss
            rsi_arr[i] = 100.0 - (100.0 / (1.0 + rs))

    return rsi_arr


def classify_rsi(rsi: float) -> str:
    """
    Map an RSI value to a human-readable regime label.

    Returns one of: 'overbought' | 'bullish' | 'neutral' | 'bearish' | 'oversold'
    """
    if rsi >= INDICATOR_RSI_OVERBOUGHT:
        return "overbought"
    if rsi >= INDICATOR_RSI_BULLISH_THRESHOLD:
        return "bullish"
    if rsi <= INDICATOR_RSI_OVERSOLD:
        return "oversold"
    if rsi <= INDICATOR_RSI_BEARISH_THRESHOLD:
        return "bearish"
    return "neutral"


def detect_rsi_divergence(
    closes: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    lookback: int = 20,
    period: int = INDICATOR_RSI_PERIOD,
) -> str | None:
    """
    Detect RSI divergence over the last `lookback` bars.

    Bearish divergence: price makes higher high, RSI makes lower high → 'bearish'
    Bullish divergence: price makes lower low,  RSI makes higher low  → 'bullish'
    No divergence: None
    """
    closes_arr = np.asarray(closes, dtype=float)
    if len(closes_arr) < lookback + period + 2:
        return None

    rsi_series = calculate_rsi_series(closes_arr, period)
    recent_closes = closes_arr[-(lookback + 1):]
    recent_rsi = rsi_series[-(lookback + 1):]

    if np.any(np.isnan(recent_rsi)):
        return None

    mid = len(recent_closes) // 2
    price_mid = recent_closes[mid]
    price_now = recent_closes[-1]
    rsi_mid = recent_rsi[mid]
    rsi_now = recent_rsi[-1]

    # Bearish: price higher high, RSI lower high
    if price_now > price_mid * 1.005 and rsi_now < rsi_mid - 3:
        return "bearish"

    # Bullish: price lower low, RSI higher low
    if price_now < price_mid * 0.995 and rsi_now > rsi_mid + 3:
        return "bullish"

    return None
