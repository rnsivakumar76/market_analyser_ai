"""
Breakout Trap Guard — pure domain logic.

A raw Donchian breakout is NOT a buy/sell signal on its own. The classic
"bought the breakout, got trapped" failure happens when a breakout is:
  1. Counter to the macro trend (bull breakout in a downtrend = bull trap), or
  2. On thin volume (no real participation behind the move), or
  3. Fighting the prevailing momentum on the tradeable timeframe.

This module decides how much (if any) score a breakout should contribute and
returns a human-readable reason. It replaces the old unconditional +/-15 boost.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..constants import BREAKOUT_MIN_VOLUME_CONFIDENCE

BULLISH = "bullish"
BEARISH = "bearish"
NEUTRAL = "neutral"


@dataclass(frozen=True)
class BreakoutGuardResult:
    score_delta: int        # signed contribution to composite score
    reason: str             # human-readable explanation
    is_trap: bool           # True when the breakout is a likely trap (counter-trend)


_NO_BREAKOUT = BreakoutGuardResult(score_delta=0, reason="", is_trap=False)


def evaluate_breakout(
    breakout_type: str,
    breakout_confidence: float,
    trend_direction: str,
    strength_direction: str,
    full_boost: int = 15,
    min_volume_confidence: float = BREAKOUT_MIN_VOLUME_CONFIDENCE,
) -> BreakoutGuardResult:
    """
    Gate a Donchian breakout behind trend alignment + volume confirmation.

    Args:
        breakout_type:       'bullish_breakout' | 'bearish_breakout' | 'none'
        breakout_confidence: 0.0-1.0, scales with volume ratio (1.0 == 2x avg vol).
        trend_direction:     Macro (long-term) trend direction.
        strength_direction:  Daily momentum direction.
        full_boost:          Score delta granted to a fully-confirmed breakout.
        min_volume_confidence: Minimum volume confidence required for any boost.

    Returns:
        BreakoutGuardResult with a signed score delta, a reason, and a trap flag.
    """
    if breakout_type not in ("bullish_breakout", "bearish_breakout"):
        return _NO_BREAKOUT

    is_bull = breakout_type == "bullish_breakout"
    direction = BULLISH if is_bull else BEARISH
    vol_ratio = breakout_confidence * 2.0  # confidence == min(vol_ratio/2, 1)
    vol_str = f"{vol_ratio:.1f}x avg volume"
    label = "Bullish" if is_bull else "Bearish"

    aligned_with_trend = trend_direction == direction
    counter_to_trend = trend_direction == (BEARISH if is_bull else BULLISH)
    momentum_opposes = strength_direction == (BEARISH if is_bull else BULLISH)
    volume_confirmed = breakout_confidence >= min_volume_confidence

    # 1. Counter-trend breakout → TRAP RISK, never reward it.
    if counter_to_trend:
        return BreakoutGuardResult(
            score_delta=0,
            reason=(
                f"{label} breakout AGAINST the macro {trend_direction} trend — "
                f"TRAP RISK. Do not chase; wait for the macro trend to flip."
            ),
            is_trap=True,
        )

    # 2. Thin-volume breakout → no conviction, no boost.
    if not volume_confirmed:
        return BreakoutGuardResult(
            score_delta=0,
            reason=(
                f"{label} breakout on thin volume ({vol_str}) — low conviction. "
                f"Wait for a hold/retest of the level before acting (no score boost)."
            ),
            is_trap=False,
        )

    # 3. Volume-confirmed and not counter-trend, but daily momentum disagrees → half boost.
    if momentum_opposes:
        half = max(1, full_boost // 2)
        delta = half if is_bull else -half
        return BreakoutGuardResult(
            score_delta=delta,
            reason=(
                f"{label} breakout confirmed ({vol_str}) but daily momentum is "
                f"{strength_direction} — reduced weight until momentum aligns."
            ),
            is_trap=False,
        )

    # 4. Fully confirmed: trend-aligned (or neutral trend) + volume + momentum not opposing.
    delta = full_boost if is_bull else -full_boost
    trend_note = "trend-aligned" if aligned_with_trend else "neutral-trend"
    return BreakoutGuardResult(
        score_delta=delta,
        reason=f"{label} breakout confirmed ({vol_str}, {trend_note}).",
        is_trap=False,
    )
