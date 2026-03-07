"""
MACD (Moving Average Convergence Divergence) — pure calculation, no pandas dependency.

Input:  sequence of closing prices
Output: MACDResult dataclass
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import Sequence

from ..constants import MACD_FAST_SPAN, MACD_SLOW_SPAN, MACD_SIGNAL_SPAN


@dataclass(frozen=True)
class MACDResult:
    macd: float          # MACD line (fast EMA - slow EMA)
    signal: float        # Signal line (EMA of MACD)
    histogram: float     # MACD - signal
    histogram_prev: float  # Previous bar histogram (for weakening detection)


def _ema_series(values: np.ndarray, span: int) -> np.ndarray:
    """Compute exponential moving average series with adjust=False."""
    alpha = 2.0 / (span + 1)
    ema = np.full(len(values), np.nan)
    # Find first non-nan seed
    start = 0
    while start < len(values) and np.isnan(values[start]):
        start += 1
    if start >= len(values):
        return ema
    ema[start] = values[start]
    for i in range(start + 1, len(values)):
        ema[i] = alpha * values[i] + (1.0 - alpha) * ema[i - 1]
    return ema


def calculate_macd(
    closes: Sequence[float],
    fast_span: int = MACD_FAST_SPAN,
    slow_span: int = MACD_SLOW_SPAN,
    signal_span: int = MACD_SIGNAL_SPAN,
) -> MACDResult:
    """
    Calculate MACD, Signal line, and Histogram for the latest bar.

    Args:
        closes:      Sequence of closing prices (at least slow_span + signal_span values).
        fast_span:   Fast EMA period (default 12).
        slow_span:   Slow EMA period (default 26).
        signal_span: Signal EMA period (default 9).

    Returns:
        MACDResult with macd, signal, histogram and previous histogram values.
        All values are 0.0 when insufficient data.
    """
    arr = np.asarray(closes, dtype=float)

    if len(arr) < slow_span + signal_span:
        return MACDResult(macd=0.0, signal=0.0, histogram=0.0, histogram_prev=0.0)

    fast_ema = _ema_series(arr, fast_span)
    slow_ema = _ema_series(arr, slow_span)
    macd_line = fast_ema - slow_ema
    signal_line = _ema_series(macd_line, signal_span)
    hist = macd_line - signal_line

    # Locate valid (non-nan) histogram values
    valid_idx = np.where(~np.isnan(hist))[0]
    if len(valid_idx) < 2:
        return MACDResult(macd=0.0, signal=0.0, histogram=0.0, histogram_prev=0.0)

    last_i = valid_idx[-1]
    prev_i = valid_idx[-2]

    return MACDResult(
        macd=float(macd_line[last_i]),
        signal=float(signal_line[last_i]),
        histogram=float(hist[last_i]),
        histogram_prev=float(hist[prev_i]),
    )


def is_histogram_weakening(result: MACDResult, trend_is_bullish: bool) -> bool:
    """
    Detect MACD histogram weakening (momentum fading).

    Bullish context: histogram shrinking (hist[-1] < hist[-2])
    Bearish context: histogram rising toward zero (hist[-1] > hist[-2])
    """
    if trend_is_bullish:
        return result.histogram < result.histogram_prev
    return result.histogram > result.histogram_prev
