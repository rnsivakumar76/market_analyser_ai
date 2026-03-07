"""
Donchian Channel Breakout Detection — pure calculation, no pandas dependency.

A bullish breakout occurs when the current close exceeds the highest high of the
previous `period` bars.  Confidence scales with the volume ratio.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import Sequence

from ..constants import BREAKOUT_DONCHIAN_PERIOD, BREAKOUT_MIN_BARS_REQUIRED


@dataclass(frozen=True)
class BreakoutResult:
    direction: str      # 'bullish_breakout' | 'bearish_breakout' | 'none'
    confidence: float   # 0.0 – 1.0  (scales with volume ratio)


_NO_BREAKOUT = BreakoutResult(direction="none", confidence=0.0)


def detect_donchian_breakout(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    volumes: Sequence[float],
    period: int = BREAKOUT_DONCHIAN_PERIOD,
) -> BreakoutResult:
    """
    Detect a Donchian channel breakout on the current (last) bar.

    Args:
        highs, lows, closes, volumes: Parallel price/volume arrays.
        period: Lookback for the channel (default 20 bars).

    Returns:
        BreakoutResult with direction and volume-based confidence.
        Returns 'none' when insufficient data or no breakout.
    """
    h = np.asarray(highs, dtype=float)
    l = np.asarray(lows, dtype=float)
    c = np.asarray(closes, dtype=float)
    v = np.asarray(volumes, dtype=float)

    if len(c) < BREAKOUT_MIN_BARS_REQUIRED:
        return _NO_BREAKOUT

    current_close = c[-1]
    current_vol = v[-1]

    # Channel is built from the *previous* period bars (exclude current bar)
    prev_slice = slice(-(period + 1), -1)
    upper_band = float(np.max(h[prev_slice]))
    lower_band = float(np.min(l[prev_slice]))
    avg_vol = float(np.mean(v[prev_slice]))

    vol_ratio = (current_vol / avg_vol) if avg_vol > 0 else 1.0
    confidence = float(min(vol_ratio / 2.0, 1.0))

    if current_close > upper_band:
        return BreakoutResult(direction="bullish_breakout", confidence=round(confidence, 4))
    if current_close < lower_band:
        return BreakoutResult(direction="bearish_breakout", confidence=round(confidence, 4))

    return _NO_BREAKOUT
