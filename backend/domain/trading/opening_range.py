"""
Opening Range Breakout (ORB) — pure calculation, no pandas dependency.

Detects whether the current price has broken above/below the opening range.
By default the range is the first bar of the session; set opening_range_bars=2
to use the first 30 minutes (two 15-minute candles), which is more robust
against anomalous single-candle news spikes at the open.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ORBData:
    or_high: float
    or_low: float
    broken: str   # 'bullish' | 'bearish' | 'none'


_EMPTY_ORB = ORBData(or_high=0.0, or_low=0.0, broken="none")


def detect_opening_range(
    session_highs: Sequence[float],
    session_lows: Sequence[float],
    current_price: float,
    opening_bar_index: int = 0,
    opening_range_bars: int = 2,
) -> ORBData:
    """
    Detect the Opening Range and whether current price has broken it.

    Args:
        session_highs:      High prices for current session bars (first = opening bar).
        session_lows:       Low prices for current session bars.
        current_price:      The latest close/price to evaluate.
        opening_bar_index:  Index of the first opening-range bar (default 0).
        opening_range_bars: Number of consecutive bars that define the opening range
                            (default 2 = first 30 minutes on 15m data).
                            Using 2 bars is more robust against single-candle news
                            spikes at the open.  Set to 1 to restore legacy behaviour.

    Returns:
        ORBData with or_high, or_low, and broken direction.
        Returns empty ORB (all zeros, 'none') when no session data is available.
    """
    h = list(session_highs)
    l = list(session_lows)

    if not h or opening_bar_index >= len(h):
        return _EMPTY_ORB

    end_idx = min(opening_bar_index + max(1, opening_range_bars), len(h))
    or_high = float(max(h[opening_bar_index:end_idx]))
    or_low  = float(min(l[opening_bar_index:end_idx]))

    if or_high == or_low:
        return ORBData(or_high=or_high, or_low=or_low, broken="none")

    broken = "none"
    if current_price > or_high:
        broken = "bullish"
    elif current_price < or_low:
        broken = "bearish"

    return ORBData(or_high=or_high, or_low=or_low, broken=broken)


def classify_orb_context(
    or_data: ORBData,
    signal_direction: str,
) -> str:
    """
    Summarise the relationship between the ORB state and the higher-timeframe signal.

    Returns one of:
      'aligned_bullish'    — ORB broke up, signal is bullish
      'aligned_bearish'    — ORB broke down, signal is bearish
      'counter_bull_orb'   — ORB broke up but signal is bearish (fade / reduce size)
      'counter_bear_orb'   — ORB broke down but signal is bullish (watch for reversal)
      'inside_range'       — No breakout yet
    """
    broken = or_data.broken
    sig = signal_direction.lower()

    if broken == "bullish" and sig == "bullish":
        return "aligned_bullish"
    if broken == "bearish" and sig == "bearish":
        return "aligned_bearish"
    if broken == "bullish" and sig == "bearish":
        return "counter_bull_orb"
    if broken == "bearish" and sig == "bullish":
        return "counter_bear_orb"
    return "inside_range"
