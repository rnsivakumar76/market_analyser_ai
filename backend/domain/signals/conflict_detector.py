"""
Signal Conflict Detector — pure domain logic for detecting contradictions between signals.

Two conflict types:
  1. adx_direction_mismatch — strong ADX but neutral directional recommendation
  2. mtf_disagreement       — monthly trend vs daily momentum disagreement
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..constants import CONFLICT_STRONG_ADX

BULLISH = "bullish"
BEARISH = "bearish"
NEUTRAL = "neutral"


@dataclass(frozen=True)
class ConflictResult:
    conflict_type: str       # 'adx_direction_mismatch' | 'mtf_disagreement' | 'none'
    severity: str            # 'high' | 'medium' | 'none'
    headline: str
    guidance: str
    trigger_price_up: Optional[float] = None
    trigger_price_down: Optional[float] = None


_NO_CONFLICT = ConflictResult(
    conflict_type="none",
    severity="none",
    headline="",
    guidance="",
)


def detect_adx_direction_mismatch(
    adx: float,
    recommendation: str,
    trigger_up: Optional[float] = None,
    trigger_down: Optional[float] = None,
    strong_adx_threshold: float = CONFLICT_STRONG_ADX,
) -> ConflictResult:
    """
    Detect Case 1: Strong ADX (locked trend) but directional bias is NEUTRAL.

    This typically means institutional positioning exists but the market is
    waiting for a catalyst to choose direction.

    Args:
        adx:                  Current ADX value.
        recommendation:       Composite signal direction.
        trigger_up:           Price level that would confirm bullish (e.g. R1).
        trigger_down:         Price level that would confirm bearish (e.g. S1).
        strong_adx_threshold: ADX >= this triggers the conflict check.

    Returns:
        ConflictResult — high severity when strong ADX + neutral recommendation.
    """
    if adx < strong_adx_threshold or recommendation != NEUTRAL:
        return _NO_CONFLICT

    up_str = f"${trigger_up:.2f}" if trigger_up is not None else "resistance"
    down_str = f"${trigger_down:.2f}" if trigger_down is not None else "support"

    return ConflictResult(
        conflict_type="adx_direction_mismatch",
        severity="high",
        headline=f"ADX={adx:.0f} confirms LOCKED TREND — but directional bias is NEUTRAL",
        guidance=(
            f"Strong trend momentum exists but direction is unconfirmed. "
            f"Watch: break above {up_str} to confirm BULLISH, "
            f"or break below {down_str} to confirm BEARISH. "
            f"Do not enter until breakout is confirmed."
        ),
        trigger_price_up=trigger_up,
        trigger_price_down=trigger_down,
    )


def detect_mtf_disagreement(
    trend_direction: str,
    strength_direction: str,
    trigger_up: Optional[float] = None,
    trigger_down: Optional[float] = None,
) -> ConflictResult:
    """
    Detect Case 2: Multi-timeframe disagreement between monthly trend and daily momentum.

    Args:
        trend_direction:    Monthly trend direction.
        strength_direction: Daily momentum direction.
        trigger_up:         Price level that would confirm bullish (e.g. R1).
        trigger_down:       Price level that would confirm bearish (e.g. S1).

    Returns:
        ConflictResult — medium severity on disagreement, no conflict otherwise.
    """
    if trend_direction == BULLISH and strength_direction == BEARISH:
        return ConflictResult(
            conflict_type="mtf_disagreement",
            severity="medium",
            headline="MTF Conflict: Monthly BULLISH vs Daily BEARISH momentum",
            guidance=(
                "Daily momentum is pulling back against the long-term uptrend. "
                "This is a potential dip-buy setup — wait for daily to stabilise "
                "before adding exposure. Avoid chasing the dip."
            ),
            trigger_price_up=trigger_up,
            trigger_price_down=trigger_down,
        )

    if trend_direction == BEARISH and strength_direction == BULLISH:
        return ConflictResult(
            conflict_type="mtf_disagreement",
            severity="medium",
            headline="MTF Conflict: Monthly BEARISH vs Daily BULLISH momentum",
            guidance=(
                "Daily bounce is occurring inside a broader downtrend. "
                "This is a dangerous 'dead cat bounce' scenario. "
                "Avoid buying into this move unless monthly trend reverses."
            ),
            trigger_price_up=trigger_up,
            trigger_price_down=trigger_down,
        )

    return _NO_CONFLICT


def detect_signal_conflict(
    adx: float,
    recommendation: str,
    trend_direction: str,
    strength_direction: str,
    trigger_up: Optional[float] = None,
    trigger_down: Optional[float] = None,
    strong_adx_threshold: float = CONFLICT_STRONG_ADX,
) -> ConflictResult:
    """
    Run both conflict checks in priority order.

    ADX/direction mismatch (high severity) is checked first.
    MTF disagreement (medium severity) is checked second.

    Args:
        adx:                  Current ADX value.
        recommendation:       Composite signal direction.
        trend_direction:      Monthly trend direction.
        strength_direction:   Daily momentum direction.
        trigger_up:           Resistance price for guidance message.
        trigger_down:         Support price for guidance message.
        strong_adx_threshold: ADX threshold for mismatch detection.

    Returns:
        The first ConflictResult that fires, or _NO_CONFLICT.
    """
    result = detect_adx_direction_mismatch(
        adx, recommendation, trigger_up, trigger_down, strong_adx_threshold
    )
    if result.conflict_type != "none":
        return result

    return detect_mtf_disagreement(trend_direction, strength_direction, trigger_up, trigger_down)
