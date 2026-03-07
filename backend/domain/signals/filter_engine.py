"""
Hard Filter Engine — single source of truth for all trade-blocking rules.

Each filter returns a FilterResult indicating whether the trade should be
blocked and why.  apply_all_hard_filters() chains them in priority order.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..constants import (
    FILTER_ADX_THRESHOLD,
    FILTER_MACRO_SCORE_PENALTY,
    SIGNAL_CONVICTION_THRESHOLD,
)

BULLISH = "bullish"
BEARISH = "bearish"
NEUTRAL = "neutral"


@dataclass(frozen=True)
class FilterResult:
    blocked: bool
    reason: Optional[str]


_PASS = FilterResult(blocked=False, reason=None)


def apply_adx_filter(
    adx: float,
    trade_worthy: bool,
    adx_threshold: float = FILTER_ADX_THRESHOLD,
) -> FilterResult:
    """
    Filter 1: ADX must exceed threshold for a trade-worthy signal.

    Args:
        adx:           Current ADX value.
        trade_worthy:  Whether the signal was trade-worthy before this filter.
        adx_threshold: Minimum ADX (default from constants).

    Returns:
        FilterResult — blocked=True if ADX is too low AND trade was previously worthy.
    """
    if not trade_worthy:
        return _PASS
    if adx <= adx_threshold:
        return FilterResult(
            blocked=True,
            reason=(
                f"Filter: Trend strength (ADX={adx:.1f}) too low. "
                f"Threshold: {adx_threshold}"
            ),
        )
    return _PASS


def apply_benchmark_filter(
    recommendation: str,
    benchmark_direction: str,
    trade_worthy: bool,
) -> FilterResult:
    """
    Filter 2: Market Beta filter — don't buy when benchmark is bearish and vice versa.

    Args:
        recommendation:      Signal direction ('bullish'|'bearish'|'neutral').
        benchmark_direction: SPX/BTC benchmark trend direction.
        trade_worthy:        Whether the signal was previously trade-worthy.

    Returns:
        FilterResult — blocked=True when recommendation conflicts with benchmark.
    """
    if not trade_worthy:
        return _PASS
    if recommendation == BULLISH and benchmark_direction == BEARISH:
        return FilterResult(
            blocked=True,
            reason=(
                "Beta Filter: Avoid buying individual assets while major market "
                "benchmark is in a downtrend."
            ),
        )
    if recommendation == BEARISH and benchmark_direction == BULLISH:
        return FilterResult(
            blocked=True,
            reason=(
                "Beta Filter: Avoid shorting while major market benchmark is rally."
            ),
        )
    return _PASS


def apply_candle_filter(
    recommendation: str,
    trade_worthy: bool,
    candle_is_bullish: Optional[bool],
    candle_pattern: str = "",
) -> FilterResult:
    """
    Filter 3: Price action trigger — require a confirmation candlestick pattern.

    Args:
        recommendation:    Signal direction.
        trade_worthy:      Whether the signal was previously trade-worthy.
        candle_is_bullish: True = bullish candle, False = bearish candle, None = doji/no pattern.
        candle_pattern:    Descriptive name of the current candle (for messaging).

    Returns:
        FilterResult — blocked=True when no confirming candle is present.
    """
    if not trade_worthy:
        return _PASS
    if recommendation == BULLISH and candle_is_bullish is not True:
        return FilterResult(
            blocked=True,
            reason=(
                f"Trigger Filter: Waiting for a bullish reversal candle "
                f"(Engulfing/Hammer) to confirm entry. Currently: {candle_pattern}"
            ),
        )
    if recommendation == BEARISH and candle_is_bullish is not False:
        return FilterResult(
            blocked=True,
            reason=(
                f"Trigger Filter: Waiting for a bearish reversal candle "
                f"(Shooting Star/Engulfing) to confirm entry. Currently: {candle_pattern}"
            ),
        )
    return _PASS


def apply_macro_shield(
    has_high_impact_events: bool,
    trade_worthy: bool,
    current_score: int,
) -> tuple[FilterResult, int]:
    """
    Filter 4: Fundamental macro shield — block trade during high-impact events.

    Args:
        has_high_impact_events: Whether macro calendar flags high-impact events.
        trade_worthy:           Whether the signal was previously trade-worthy.
        current_score:          Current composite score.

    Returns:
        (FilterResult, adjusted_score)
    """
    if not trade_worthy or not has_high_impact_events:
        return _PASS, current_score

    # Penalise score
    if current_score > 0:
        adjusted = max(current_score - FILTER_MACRO_SCORE_PENALTY, -100)
    else:
        adjusted = min(current_score + FILTER_MACRO_SCORE_PENALTY, 100)

    return FilterResult(
        blocked=True,
        reason=(
            "Macro Shield Active: Trade blocked due to high-impact economic events "
            "or earnings within 48h."
        ),
    ), adjusted


def apply_relative_strength_filter(
    recommendation: str,
    trade_worthy: bool,
    is_outperforming: bool,
) -> FilterResult:
    """
    Filter 5: Alpha / relative strength filter.

    Args:
        recommendation:  Signal direction.
        trade_worthy:    Whether the signal was previously trade-worthy.
        is_outperforming: Whether the instrument outperforms its benchmark.

    Returns:
        FilterResult — blocked=True when buying laggards or shorting leaders.
    """
    if not trade_worthy:
        return _PASS
    if recommendation == BULLISH and not is_outperforming:
        return FilterResult(
            blocked=True,
            reason=(
                "Alpha Filter: Trade blocked. This instrument is a market laggard "
                "(underperforming its benchmark). Institutional money flows into leaders."
            ),
        )
    if recommendation == BEARISH and is_outperforming:
        return FilterResult(
            blocked=True,
            reason=(
                "Alpha Filter: Trade blocked. This instrument is showing resilient "
                "strength vs the market. Dangerous to short market leaders."
            ),
        )
    return _PASS


def apply_all_hard_filters(
    recommendation: str,
    trade_worthy: bool,
    composite_score: int,
    adx: float,
    benchmark_direction: str,
    candle_is_bullish: Optional[bool],
    candle_pattern: str,
    has_high_impact_events: bool,
    is_outperforming: Optional[bool],
    adx_threshold: float = FILTER_ADX_THRESHOLD,
) -> tuple[bool, int, list[str]]:
    """
    Apply all five hard filters in sequence.

    Returns:
        (final_trade_worthy: bool, final_score: int, blocked_reasons: list[str])

    The returned list contains only reasons from *blocking* filters.
    """
    blocked_reasons: list[str] = []
    current_score = composite_score
    initial_trade_worthy = trade_worthy

    # Evaluate all filters using the ORIGINAL trade_worthy so every failure is
    # captured.  trade_worthy is only used as the return value at the end.
    any_blocked = False

    # Filter 1: ADX
    r = apply_adx_filter(adx, initial_trade_worthy, adx_threshold)
    if r.blocked:
        any_blocked = True
        blocked_reasons.append(r.reason)

    # Filter 2: Benchmark beta (always checked if initially trade-worthy)
    r = apply_benchmark_filter(recommendation, benchmark_direction, initial_trade_worthy)
    if r.blocked:
        any_blocked = True
        blocked_reasons.append(r.reason)

    # Filter 3: Candle trigger
    r = apply_candle_filter(recommendation, initial_trade_worthy, candle_is_bullish, candle_pattern)
    if r.blocked:
        any_blocked = True
        blocked_reasons.append(r.reason)

    # Filter 4: Macro shield (score penalty applies regardless)
    r, current_score = apply_macro_shield(has_high_impact_events, initial_trade_worthy, current_score)
    if r.blocked:
        any_blocked = True
        blocked_reasons.append(r.reason)

    # Filter 5: Relative strength
    if is_outperforming is not None:
        r = apply_relative_strength_filter(recommendation, initial_trade_worthy, is_outperforming)
        if r.blocked:
            any_blocked = True
            blocked_reasons.append(r.reason)

    if any_blocked:
        trade_worthy = False

    return trade_worthy, current_score, blocked_reasons
