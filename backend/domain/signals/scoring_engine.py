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
    SIGNAL_ADX_RANGING,
    SIGNAL_ADX_TRENDING,
    SIGNAL_ADX_STRONG,
    SIGNAL_ADX_REGIME_WEIGHTS,
    SIGNAL_NEUTRAL_TREND_TACTICAL_DAMPEN,
    SIGNAL_NEUTRAL_TREND_PB_SUPPORT_FRACTION,
    SIGNAL_NEUTRAL_TREND_PB_DETECTED_FRACTION,
)

# Direction literals used throughout the domain layer
BULLISH = "bullish"
BEARISH = "bearish"
NEUTRAL = "neutral"


def _classify_adx_regime(adx: float) -> str:
    """Map an ADX reading to its regime label."""
    if adx >= SIGNAL_ADX_STRONG:
        return "STRONG"
    if adx >= SIGNAL_ADX_TRENDING:
        return "TRENDING"
    if adx >= SIGNAL_ADX_RANGING:
        return "NORMAL"
    return "RANGING"


def _get_regime_weights(adx: float) -> tuple[int, int, int]:
    """Return (trend_weight, pullback_weight, strength_weight) for the current ADX regime."""
    regime = _classify_adx_regime(adx)
    w = SIGNAL_ADX_REGIME_WEIGHTS[regime]
    return w["trend"], w["pullback"], w["strength"]


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


def compute_trend_score(
    trend_direction: str,
    weight: int = SIGNAL_WEIGHT_TREND,
) -> tuple[int, str]:
    """
    Monthly trend contribution.

    Args:
        trend_direction: 'bullish' | 'bearish' | 'neutral'
        weight:          Regime-adjusted trend weight (default SIGNAL_WEIGHT_TREND=40).

    Returns:
        (score_delta, reason_text)
    """
    if trend_direction == BULLISH:
        return weight, "Monthly uptrend confirmed"
    if trend_direction == BEARISH:
        return -weight, "Monthly downtrend - caution"
    return 0, "Monthly trend unclear"


def compute_pullback_score(
    trend_direction: str,
    pullback_detected: bool,
    near_support: bool,
    weight: int = SIGNAL_WEIGHT_PULLBACK,
) -> tuple[int, str]:
    """
    Weekly pullback contribution.

    Args:
        trend_direction:   Monthly trend direction.
        pullback_detected: Whether a pullback from the recent high is detected.
        near_support:      Whether price is near a structural support level.
        weight:            Regime-adjusted pullback weight (default SIGNAL_WEIGHT_PULLBACK=30).
                           In RANGING regimes weight is raised to 45 (mean-reversion valid);
                           in TRENDING regimes it is lowered to 20.

    Returns:
        (score_delta, reason_text)
    """
    # Scale sub-tiers proportionally to the regime weight
    full      = weight                                          # 100 % of weight
    half      = max(1, weight // 2)                            # ~50 %
    no_pb     = max(1, round(weight * SIGNAL_PULLBACK_NO_PULLBACK / SIGNAL_WEIGHT_PULLBACK))  # ~17 %
    bear_cont = max(1, round(weight * SIGNAL_BEARISH_CONT   / SIGNAL_WEIGHT_PULLBACK))        # ~67 %
    bear_bnc  = max(1, round(weight * SIGNAL_BEARISH_BOUNCE / SIGNAL_WEIGHT_PULLBACK))        # ~33 %

    if trend_direction == BULLISH:
        if pullback_detected and near_support:
            return full,  "Pullback to support in uptrend - ideal entry"
        if pullback_detected:
            return half,  "Pullback detected, waiting for support"
        return no_pb, "No pullback - extended from support"

    if trend_direction == BEARISH:
        if pullback_detected and near_support:
            return -bear_bnc,  "Bounce in downtrend - potential short entry"
        return -bear_cont, "Downtrend continuation"

    return 0, "Neutral trend — no pullback adjustment"


def compute_strength_score(
    strength_direction: str,
    trend_direction: str,
    weight: int = SIGNAL_WEIGHT_STRENGTH,
) -> tuple[int, str]:
    """
    Daily strength contribution.

    Args:
        strength_direction: Daily signal direction.
        trend_direction:    Monthly trend direction.
        weight:             Regime-adjusted strength weight (default SIGNAL_WEIGHT_STRENGTH=30).

    Returns:
        (score_delta, reason_text)
    """
    counter = max(1, round(weight * SIGNAL_STRENGTH_COUNTER / SIGNAL_WEIGHT_STRENGTH))  # ~33 %

    if strength_direction == BULLISH:
        if trend_direction == BULLISH:
            return weight,   "Daily strength confirms uptrend"
        return counter,  "Daily bullish but against trend"

    if strength_direction == BEARISH:
        if trend_direction == BEARISH:
            return -weight,  "Daily weakness confirms downtrend"
        return -counter, "Daily bearish but against trend"

    return 0, "Daily momentum neutral"


def compute_tactical_neutral_score(
    strength_direction: str,
    pullback_detected: bool,
    near_support: bool,
    pullback_weight: int,
    strength_weight: int,
) -> tuple[int, str]:
    """
    Tactical directional score used ONLY when the monthly trend is neutral.

    Problem this solves:
        In a neutral-trend (often RANGING) market the trend weight is forfeited
        and the standard pullback factor returns 0 — wasting the *largest* weight
        in the RANGING regime (pullback=45). The result is that a clearly
        directional daily move (e.g. a sharp -5.9% day) collapses to a near-zero
        composite and the signal reads NEUTRAL / STAND ASIDE, which feels wrong
        when the market is visibly moving.

    Fix:
        When there is no monthly trend, daily momentum becomes the tactical bias.
        It earns the full strength weight (it is not "counter" to any trend) plus
        a fraction of the otherwise-wasted pullback weight when price sits at a
        mean-reversion location. The total is dampened to reflect the lower
        conviction of trading without long-term trend backing, so it can register
        a directional lean without ever reaching full trade-worthy conviction.

    Args:
        strength_direction: Daily signal direction ('bullish' | 'bearish' | 'neutral').
        pullback_detected:  Weekly pullback flag.
        near_support:       Weekly near-support flag.
        pullback_weight:    Regime-adjusted pullback weight (highest in RANGING).
        strength_weight:    Regime-adjusted strength weight.

    Returns:
        (score_delta, reason_text)
    """
    if strength_direction not in (BULLISH, BEARISH):
        return 0, "Neutral trend + neutral momentum — no tactical edge"

    sign = 1 if strength_direction == BULLISH else -1
    base = float(strength_weight)

    if pullback_detected and near_support:
        base += pullback_weight * SIGNAL_NEUTRAL_TREND_PB_SUPPORT_FRACTION
        location_note = "at support"
    elif pullback_detected:
        base += pullback_weight * SIGNAL_NEUTRAL_TREND_PB_DETECTED_FRACTION
        location_note = "mid-pullback"
    else:
        location_note = "no mean-reversion location"

    score = int(round(sign * base * SIGNAL_NEUTRAL_TREND_TACTICAL_DAMPEN))
    score = max(min(score, 100), -100)

    direction_word = "bullish" if sign > 0 else "bearish"
    reason = (
        f"No monthly trend — daily {direction_word} momentum sets a tactical bias "
        f"({location_note}); dampened, capped below full conviction"
    )
    return score, reason


def compute_composite_score(
    trend_direction: str,
    pullback_detected: bool,
    near_support: bool,
    strength_direction: str,
    adx: Optional[float] = None,
) -> ScoreComponents:
    """
    Combine all three scoring factors into a single composite score.

    Score range: –100 to +100.
    This is the single authoritative place where the composite score is computed.

    When *adx* is provided the weights are regime-adaptive:
      - RANGING  (ADX < 20):  trend=25, pullback=45, strength=30 — mean-reversion favoured
      - NORMAL   (20–29):     trend=40, pullback=30, strength=30 — standard weights
      - TRENDING (30–44):     trend=50, pullback=20, strength=30 — momentum favoured
      - STRONG   (ADX ≥ 45):  trend=55, pullback=15, strength=30 — trend dominates

    When *adx* is None the NORMAL weights are used unchanged (backward-compatible).

    Args:
        trend_direction:    Monthly trend ('bullish' | 'bearish' | 'neutral').
        pullback_detected:  Weekly pullback flag.
        near_support:       Weekly near-support flag.
        strength_direction: Daily strength signal.
        adx:                Current ADX reading (optional — enables regime adaptation).

    Returns:
        ScoreComponents with individual deltas, composite sum, and reasons list.
    """
    components = ScoreComponents()

    if adx is not None and adx > 0:
        trend_w, pullback_w, strength_w = _get_regime_weights(adx)
        regime = _classify_adx_regime(adx)
        if regime != "NORMAL":
            components.add_reason(
                f"Regime-weighted scoring ({regime}, ADX={adx:.1f}): "
                f"trend={trend_w}, pullback={pullback_w}, strength={strength_w}"
            )
    else:
        trend_w, pullback_w, strength_w = (
            SIGNAL_WEIGHT_TREND,
            SIGNAL_WEIGHT_PULLBACK,
            SIGNAL_WEIGHT_STRENGTH,
        )
        regime = "NORMAL"

    # ── Neutral-trend tactical path ──────────────────────────────────────────
    # When there is no monthly trend, the standard trend (0) and pullback (0)
    # factors waste their weight — especially the dominant pullback weight in
    # RANGING regimes. Route the directional daily momentum into a single
    # dampened tactical score so a visibly trending market does not collapse to
    # a misleading NEUTRAL reading. Decomposition invariant is preserved by
    # carrying the whole tactical value in strength_score (trend/pullback = 0).
    if trend_direction == NEUTRAL and strength_direction in (BULLISH, BEARISH):
        t_reason = compute_trend_score(trend_direction, weight=trend_w)[1]
        tactical_score, tactical_reason = compute_tactical_neutral_score(
            strength_direction,
            pullback_detected,
            near_support,
            pullback_weight=pullback_w,
            strength_weight=strength_w,
        )
        components.trend_score    = 0
        components.pullback_score = 0
        components.strength_score = tactical_score
        components.composite      = tactical_score
        components.add_reason(t_reason)
        components.add_reason(tactical_reason)
        return components

    t_score, t_reason = compute_trend_score(trend_direction, weight=trend_w)
    p_score, p_reason = compute_pullback_score(
        trend_direction, pullback_detected, near_support, weight=pullback_w
    )
    s_score, s_reason = compute_strength_score(
        strength_direction, trend_direction, weight=strength_w
    )

    components.trend_score    = t_score
    components.pullback_score = p_score
    components.strength_score = s_score
    components.composite      = t_score + p_score + s_score
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
