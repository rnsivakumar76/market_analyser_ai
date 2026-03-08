from typing import List, Optional
from .models import (
    TrendAnalysis, PullbackAnalysis, StrengthAnalysis, 
    TradeSignal, Signal, CandleAnalysis, StrategySettings,
    FundamentalsAnalysis, RelativeStrengthAnalysis, SignalConflict
)
from domain.signals.scoring_engine import compute_composite_score, classify_recommendation
from domain.signals.filter_engine import apply_all_hard_filters
from domain.signals.conflict_detector import detect_signal_conflict as _domain_detect_conflict
from domain.constants import SIGNAL_CONVICTION_THRESHOLD, FILTER_ADX_THRESHOLD


def generate_trade_signal(
    trend: TrendAnalysis,
    pullback: PullbackAnalysis,
    strength: StrengthAnalysis,
    candle: CandleAnalysis,
    benchmark_direction: Signal = Signal.NEUTRAL,
    settings: StrategySettings = None,
    current_price: float = None,
    tech_indicators = None,
    volatility = None,
    fundamentals: FundamentalsAnalysis = None,
    relative_strength: RelativeStrengthAnalysis = None,
    **kwargs
) -> TradeSignal:
    """
    Generate a composite trade signal based on all analyses.
    
    Ideal setup (bullish):
    1. Monthly trend is bullish (uptrend)
    2. Weekly has pulled back to support
    3. Daily showing strength/momentum in trend direction
    
    Score: -100 (strong sell) to +100 (strong buy)
    """
    # ── Domain layer: composite score ────────────────────────────────────────
    threshold = settings.conviction_threshold if settings else SIGNAL_CONVICTION_THRESHOLD
    adx_threshold = settings.adx_threshold if settings else FILTER_ADX_THRESHOLD

    components = compute_composite_score(
        trend_direction=trend.direction.value,
        pullback_detected=pullback.detected,
        near_support=pullback.near_support,
        strength_direction=strength.signal.value,
        adx=float(strength.adx) if strength.adx is not None else None,
    )
    score = components.composite
    reasons = list(components.reasons)

    recommendation_str, trade_worthy = classify_recommendation(score, threshold)
    recommendation = Signal(recommendation_str)

    if not trade_worthy:
        if score >= 20:
            reasons.append("Setup developing but not ideal yet")
        elif score <= -20:
            reasons.append("Bearish setup developing")
        else:
            reasons.append("No clear setup - wait for better opportunity")

    # ADX pass-through reason (when ADX is above threshold, add as a reason)
    adx_value = strength.adx
    if adx_value is not None and adx_value > adx_threshold:
        reasons.append(f"Trend strength high (ADX={adx_value:.1f})")

    # ── Domain layer: all hard filters ───────────────────────────────────────
    is_outperforming = relative_strength.is_outperforming if relative_strength else None
    has_high_impact = fundamentals.has_high_impact_events if fundamentals else False

    trade_worthy, score, blocked_reasons = apply_all_hard_filters(
        recommendation=recommendation.value,
        trade_worthy=trade_worthy,
        composite_score=score,
        adx=adx_value if adx_value is not None else 0.0,
        benchmark_direction=benchmark_direction.value,
        candle_is_bullish=candle.is_bullish,
        candle_pattern=candle.pattern,
        has_high_impact_events=has_high_impact,
        is_outperforming=is_outperforming,
        adx_threshold=adx_threshold,
    )
    reasons.extend(blocked_reasons)

    # ADX hard-filter blocked case: when adx_value is low and it DID block, add a fallback reason
    if not trade_worthy and adx_value is not None and adx_value <= adx_threshold:
        if not any("ADX" in r for r in reasons):
            reasons.append(f"Filter: Trend strength (ADX={adx_value:.1f}) too low. Threshold: {adx_threshold}")

    # Candle confirmation reason (when candle was fine, add it)
    if candle.is_bullish is not None and not any("Trigger Filter" in r for r in reasons):
        if (recommendation == Signal.BULLISH and candle.is_bullish is True) or \
           (recommendation == Signal.BEARISH and candle.is_bullish is False):
            reasons.append(f"Price Action Trigger confirmed: {candle.description}")

    action_plan = "Stand Aside"
    action_plan_details = "Market conditions do not support a high-probability trade."
    psychological_guard = "Discipline: Do not force a trade in choppy or uncertain markets."
    pyramiding_plan = "N/A"
    scaling_plan = "Wait for clear trend alignment."

    if current_price and tech_indicators:
        pivots = tech_indicators.pivot_points
        fibs = tech_indicators.fibonacci
        
        # Base Scaling text
        s_tp1 = s_tp2 = s_tp3 = "N/A"
        if volatility:
            s_tp1 = f"${volatility.take_profit_level1:.2f}" if volatility.take_profit_level1 is not None else "N/A"
            s_tp2 = f"${volatility.take_profit_level2:.2f}" if volatility.take_profit_level2 is not None else "N/A"
            s_tp3 = f"${volatility.take_profit:.2f}" if volatility.take_profit is not None else "N/A"

        if recommendation == Signal.BULLISH:
            psychological_guard = "NEVER average down into a losing trade. If price falls below support or hits your stop loss, cut the trade immediately. The market does not owe you a bounce."
            if trade_worthy:
                action_plan = "Enter Long (Market)"
                price_str = f"${current_price:.2f}" if current_price else "current price"
                pivot_str = f"${pivots.pivot:.2f}" if pivots.pivot else "N/A"
                action_plan_details = f"Strong bullish setup confirmed near {price_str}. Support is Pivot ({pivot_str}). If trend accelerates, target Fibonacci Extensions."
                
                if volatility:
                    scaling_plan = (
                        f"Stage 1 (De-risk): Exit 30% at {s_tp1} & Move SL to Break-even. "
                        f"Stage 2 (Profit): Exit 40% at {s_tp2}. "
                        f"Stage 3 (Runner): Leave 30% for {s_tp3} or trail by 2.0x ATR."
                    )
                else:
                    scaling_plan = f"Target R1 (${pivots.r1}) for first exit, then trail."
                
                pyramiding_plan = f"Aggressive Addition: Add 50% to position size IF price holds above R1 (${pivots.r1}) AND RSI stays < 70."
            else:
                action_plan = "Wait for Trigger / Pullback"
                s1_str = f"${pivots.s1:.2f}" if pivots.s1 else "N/A"
                fib_str = f"${fibs.ret_382:.2f}" if fibs.ret_382 else "N/A"
                action_plan_details = f"Ideal entry is on a pullback near support (S1: {s1_str}) or the 38.2% Fib Retracement ({fib_str})."
                scaling_plan = "Awaiting entry confirmation before finalizing exit stages."
                pyramiding_plan = "Do not pyramid until initial position is firmly in profit."
        elif recommendation == Signal.BEARISH:
            psychological_guard = "NEVER average up into a losing short. If price rallies past resistance, cover immediately. Infinite downside risk in shorts."
            if trade_worthy:
                action_plan = "Enter Short (Market)"
                price_str = f"${current_price:.2f}" if current_price else "current price"
                pivot_str = f"${pivots.pivot:.2f}" if pivots.pivot else "N/A"
                action_plan_details = f"Strong bearish setup confirmed near {price_str}. Resistance is Pivot ({pivot_str}). If decline accelerates, target Fibonacci Extensions."
                
                if volatility:
                    scaling_plan = (
                        f"Stage 1 (De-risk): Exit 30% at {s_tp1} & Move SL to Break-even. "
                        f"Stage 2 (Profit): Exit 40% at {s_tp2}. "
                        f"Stage 3 (Runner): Leave 30% for {s_tp3} or trail by 2.0x ATR."
                    )
                else:
                    scaling_plan = f"Target S1 (${pivots.s1}) for first exit, then trail."
                
                pyramiding_plan = f"Aggressive Addition: Add 50% to short position IF price holds below S1 (${pivots.s1}) AND RSI stays > 30."
            else:
                action_plan = "Wait for Trigger / Bounce"
                r1_str = f"${pivots.r1:.2f}" if pivots.r1 else "N/A"
                action_plan_details = f"Ideal entry is on a bounce near resistance (R1: {r1_str}) or 38.2% Fib Retracement."
                scaling_plan = "Awaiting entry confirmation."
                pyramiding_plan = "Do not pyramid until initial position is firmly in profit."
        else:
            action_plan = "Wait and Observe"
            r1_str = f"${pivots.r1:.2f}" if pivots.r1 else "N/A"
            s1_str = f"${pivots.s1:.2f}" if pivots.s1 else "N/A"
            action_plan_details = f"Neutral bias. Key zones: R1 ({r1_str}) and S1 ({s1_str})."
            psychological_guard = "Patience is a position. Awaiting clear structural setup."
            pyramiding_plan = "N/A"
            scaling_plan = "N/A - Sideways Market"

    # Layman's Terms Executive Summary
    summary_parts = []
    
    # 1. State the trend and recommendation
    if recommendation == Signal.NEUTRAL:
        summary_parts.append("The system advises staying sidelined right now due to mixed or conflicting signals.")
    elif recommendation == Signal.BULLISH and trade_worthy:
        summary_parts.append("The system has generated a high-probability BUY signal, meaning multiple technical and fundamental factors show strong upward momentum.")
    elif recommendation == Signal.BEARISH and trade_worthy:
        summary_parts.append("The system has generated a high-probability SELL signal, warning that the asset is in a concerning downtrend.")
    else:
        if recommendation == Signal.BULLISH:
            summary_parts.append("The system leans slightly bullish, but conditions are not strong enough to risk capital yet.")
        else:
            summary_parts.append("The system leans bearish, but the setup is incomplete and too risky to short right now.")

    # 2. Add structural context
    trend_str = "an uptrend" if trend.direction == Signal.BULLISH else "a downtrend" if trend.direction == Signal.BEARISH else "sideways consolidation"
    summary_parts.append(f"The macro (long-term) picture is currently in {trend_str}.")
    
    if strength.signal == Signal.BULLISH and trend.direction == Signal.BEARISH:
        summary_parts.append("However, short-term momentum is fighting the overall trend, creating a dangerous 'falling knife' scenario.")
    elif strength.signal == Signal.BEARISH and trend.direction == Signal.BULLISH:
        summary_parts.append("Short-term momentum is currently cooling off, which may provide a dip-buying opportunity if support holds.")
        
    # 3. Add fundamental warning context
    if fundamentals and fundamentals.has_high_impact_events:
        summary_parts.append("WARNING: Extreme volatility is expected soon due to major upcoming economic news or earnings. Do not trade unless prepared for violent swings.")
        
    # 4. Action Summary
    if trade_worthy:
        summary_parts.append(f"Conclusion: Mathematical alignment is strong enough to execute the '{action_plan}' framework.")
    else:
        summary_parts.append("Conclusion: Wait patiently for better mathematical alignment or a clearer setup before taking action.")

    executive_summary = " ".join(summary_parts)

    signal_conflict = _detect_signal_conflict(
        recommendation=recommendation,
        strength=strength,
        trend=trend,
        settings=settings,
        tech_indicators=tech_indicators
    )

    return TradeSignal(
        recommendation=recommendation,
        score=score,
        reasons=reasons,
        trade_worthy=trade_worthy,
        action_plan=action_plan,
        action_plan_details=action_plan_details,
        psychological_guard=psychological_guard,
        pyramiding_plan=pyramiding_plan,
        scaling_plan=scaling_plan,
        executive_summary=executive_summary,
        signal_conflict=signal_conflict
    )


def _detect_signal_conflict(
    recommendation: Signal,
    strength,
    trend: TrendAnalysis,
    settings,
    tech_indicators
) -> Optional[SignalConflict]:
    """Detect and explain contradictions between ADX momentum and directional signals. Delegates to domain layer."""
    adx = strength.adx if strength else 0.0

    trigger_up = None
    trigger_down = None
    if tech_indicators and tech_indicators.pivot_points:
        trigger_up = tech_indicators.pivot_points.r1
        trigger_down = tech_indicators.pivot_points.s1

    result = _domain_detect_conflict(
        adx=float(adx),
        recommendation=recommendation.value,
        trend_direction=trend.direction.value,
        strength_direction=strength.signal.value if strength else "neutral",
        trigger_up=trigger_up,
        trigger_down=trigger_down,
        rsi=(float(strength.rsi) if strength else None),
        price_change_percent=(float(strength.price_change_percent) if strength else None),
        vwap_dist_pct=(float(strength.vwap_dist_pct) if strength and strength.vwap_dist_pct is not None else None),
    )

    if result.conflict_type == "none":
        return SignalConflict(conflict_type="none", severity="none", headline="", guidance="")

    return SignalConflict(
        conflict_type=result.conflict_type,
        severity=result.severity,
        headline=result.headline,
        guidance=result.guidance,
        trigger_price_up=result.trigger_price_up,
        trigger_price_down=result.trigger_price_down,
    )
