"""
Signal Scoring Engine — single source of truth for composite score computation.

All scoring weights come from domain/constants.py.
Input types are simple strings / floats — no Pydantic models, no DataFrames.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..constants import (
    SIGNAL_WEIGHT_TREND,
    SIGNAL_WEIGHT_PULLBACK,
    SIGNAL_WEIGHT_STRENGTH,
    SIGNAL_PULLBACK_FULL_SCORE,
    SIGNAL_PULLBACK_HALF_SCORE,
    SIGNAL_PULLBACK_NO_PULLBACK,
    SIGNAL_STRENGTH_ALIGNED,
    SIGNAL_STRENGTH_COUNTER,
    SIGNAL_BEARISH_CONT,
    SIGNAL_BEARISH_BOUNCE,
)

# Direction literals used throughout the domain layer
BULLISH = "bullish"
BEARISH = "bearish"
NEUTRAL = "neutral"


@dataclass
class ScoreComponents:
    """Decomposed score with audit trail for debugging and testing."""
    trend_score: int = 0
    pullback_score: int = 0
    strength_score: int = 0
    composite: int = 0
    reasons: list[str] = field(default_factory=list)

    def add_reason(self, msg: str) -> None:
        self.reasons.append(msg)


def compute_trend_score(trend_direction: str) -> tuple[int, str]:
    """
    Monthly trend contribution (max ±40 points).

    Args:
        trend_direction: 'bullish' | 'bearish' | 'neutral'

    Returns:
        (score_delta, reason_text)
    """
    if trend_direction == BULLISH:
        return SIGNAL_WEIGHT_TREND, "Monthly uptrend confirmed"
    if trend_direction == BEARISH:
        return -SIGNAL_WEIGHT_TREND, "Monthly downtrend - caution"
    return 0, "Monthly trend unclear"


def compute_pullback_score(
    trend_direction: str,
    pullback_detected: bool,
    near_support: bool,
) -> tuple[int, str]:
    """
    Weekly pullback contribution (max ±30 points).

    Args:
        trend_direction:  Monthly trend direction.
        pullback_detected: Whether a pullback from the recent high is detected.
        near_support:     Whether price is near a structural support level.

    Returns:
        (score_delta, reason_text)
    """
    if trend_direction == BULLISH:
        if pullback_detected and near_support:
            return SIGNAL_PULLBACK_FULL_SCORE, "Pullback to support in uptrend - ideal entry"
        if pullback_detected:
            return SIGNAL_PULLBACK_HALF_SCORE, "Pullback detected, waiting for support"
        return SIGNAL_PULLBACK_NO_PULLBACK, "No pullback - extended from support"

    if trend_direction == BEARISH:
        if pullback_detected and near_support:
            return -SIGNAL_BEARISH_BOUNCE, "Bounce in downtrend - potential short entry"
        return -SIGNAL_BEARISH_CONT, "Downtrend continuation"

    return 0, "Neutral trend — no pullback adjustment"


def compute_strength_score(
    strength_direction: str,
    trend_direction: str,
) -> tuple[int, str]:
    """
    Daily strength contribution (max ±30 points).

    Args:
        strength_direction: Daily signal direction.
        trend_direction:    Monthly trend direction.

    Returns:
        (score_delta, reason_text)
    """
    if strength_direction == BULLISH:
        if trend_direction == BULLISH:
            return SIGNAL_STRENGTH_ALIGNED, "Daily strength confirms uptrend"
        return SIGNAL_STRENGTH_COUNTER, "Daily bullish but against trend"

    if strength_direction == BEARISH:
        if trend_direction == BEARISH:
            return -SIGNAL_STRENGTH_ALIGNED, "Daily weakness confirms downtrend"
        return -SIGNAL_STRENGTH_COUNTER, "Daily bearish but against trend"

    return 0, "Daily momentum neutral"


def compute_composite_score(
    trend_direction: str,
    pullback_detected: bool,
    near_support: bool,
    strength_direction: str,
) -> ScoreComponents:
    """
    Combine all three scoring factors into a single composite score.

    Score range: –100 to +100.
    This is the single authoritative place where the composite score is computed.

    Args:
        trend_direction:   Monthly trend ('bullish' | 'bearish' | 'neutral').
        pullback_detected: Weekly pullback flag.
        near_support:      Weekly near-support flag.
        strength_direction: Daily strength signal.

    Returns:
        ScoreComponents with individual deltas, composite sum, and reasons list.
    """
    components = ScoreComponents()

    t_score, t_reason = compute_trend_score(trend_direction)
    p_score, p_reason = compute_pullback_score(trend_direction, pullback_detected, near_support)
    s_score, s_reason = compute_strength_score(strength_direction, trend_direction)

    components.trend_score = t_score
    components.pullback_score = p_score
    components.strength_score = s_score
    components.composite = t_score + p_score + s_score
    components.add_reason(t_reason)
    components.add_reason(p_reason)
    components.add_reason(s_reason)

    return components


def classify_recommendation(score: int, threshold: int) -> tuple[str, bool]:
    """
    Convert a composite score to a recommendation direction and trade-worthy flag.

    Args:
        score:     Composite score (–100 to +100).
        threshold: Minimum absolute score required for trade-worthy.

    Returns:
        (recommendation: 'bullish'|'bearish'|'neutral', trade_worthy: bool)
    """
    if score >= threshold:
        return BULLISH, True
    if score <= -threshold:
        return BEARISH, True
    if score >= 20:
        return BULLISH, False
    if score <= -20:
        return BEARISH, False
    return NEUTRAL, False
