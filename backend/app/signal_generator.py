from typing import List, Optional
from .models import (
    TrendAnalysis, PullbackAnalysis, StrengthAnalysis, 
    TradeSignal, Signal, CandleAnalysis, StrategySettings,
    FundamentalsAnalysis, RelativeStrengthAnalysis, SignalConflict,
    PullbackWarningAnalysis, BlowOffTopAnalysis
)
from domain.signals.scoring_engine import compute_composite_score, classify_recommendation
from domain.signals.filter_engine import apply_all_hard_filters
from domain.signals.conflict_detector import detect_signal_conflict as _domain_detect_conflict
from domain.constants import (
    SIGNAL_CONVICTION_THRESHOLD,
    FILTER_ADX_THRESHOLD,
    SIGNAL_ADX_TRENDING,
    SIGNAL_ADX_STRONG,
)


def _effective_conviction_threshold(base_threshold: int, adx_value: Optional[float]) -> int:
    """Adaptive conviction threshold by trend regime.

    Strong/trending markets allow slightly faster activation; weak markets demand
    extra confirmation.
    """
    if adx_value is None:
        return base_threshold
    if adx_value >= SIGNAL_ADX_STRONG:
        return max(55, base_threshold - 10)
    if adx_value >= SIGNAL_ADX_TRENDING:
        return max(60, base_threshold - 5)
    if adx_value < 20:
        return min(80, base_threshold + 5)
    return base_threshold


def _normalize_aggressiveness_mode(mode: Optional[str]) -> str:
    normalized = (mode or "balanced").strip().lower()
    if normalized not in {"conservative", "balanced", "aggressive"}:
        return "balanced"
    return normalized


def _apply_aggressiveness_to_threshold(mode: str, threshold: int) -> int:
    if mode == "conservative":
        return min(94, threshold + 10)
    if mode == "aggressive":
        return max(45, threshold - 10)
    return threshold


def _normalize_strategy_mode(mode: Optional[str]) -> str:
    normalized = (mode or "long_term").strip().lower()
    if normalized not in {"long_term", "short_term"}:
        return "long_term"
    return normalized


def _derive_execution_profile(
    recommendation: Signal,
    trade_worthy: bool,
    score: int,
    reasons: List[str],
    adx_value: Optional[float],
    aggressiveness_mode: str,
) -> tuple[str, str, str]:
    blocked = any(
        marker in reason
        for reason in reasons
        for marker in ("Filter:", "Beta Filter", "Trigger Filter", "Alpha Filter")
    )
    score_abs = abs(score)
    macro_caution = any("Macro Caution" in reason for reason in reasons)

    if aggressiveness_mode == "aggressive":
        conditional_min_score = 12
    elif aggressiveness_mode == "conservative":
        conditional_min_score = 28
    else:
        conditional_min_score = 20

    if trade_worthy and not blocked:
        execution_state = "ready"
    elif recommendation != Signal.NEUTRAL and score_abs >= conditional_min_score:
        execution_state = "conditional"
    else:
        execution_state = "stand_aside"

    if aggressiveness_mode == "aggressive":
        ready_a_cutoff = 74
        conditional_b_cutoff = 38
    elif aggressiveness_mode == "conservative":
        ready_a_cutoff = 95
        conditional_b_cutoff = 62
    else:
        ready_a_cutoff = 85
        conditional_b_cutoff = 50

    if execution_state == "ready" and score_abs >= ready_a_cutoff:
        opportunity_grade = "A"
    elif execution_state == "ready":
        opportunity_grade = "B"
    elif execution_state == "conditional" and score_abs >= conditional_b_cutoff:
        opportunity_grade = "B"
    elif execution_state == "conditional":
        opportunity_grade = "C"
    else:
        opportunity_grade = "D"

    if execution_state == "stand_aside":
        suggested_size_text = "0.0x (no entry)"
    elif execution_state == "conditional":
        if aggressiveness_mode == "aggressive":
            suggested_size_text = "0.65x (aggressive starter on trigger close)"
        elif aggressiveness_mode == "conservative":
            suggested_size_text = "0.35x (conservative starter on trigger close)"
        else:
            suggested_size_text = "0.5x (starter size on trigger close)"
    else:
        if adx_value is not None and adx_value >= SIGNAL_ADX_STRONG and score_abs >= ready_a_cutoff:
            suggested_size_text = "1.0x (full size)"
        else:
            if aggressiveness_mode == "aggressive":
                suggested_size_text = "0.95x (high-conviction risk-on setup)"
            elif aggressiveness_mode == "conservative":
                suggested_size_text = "0.55x (capital-preservation full setup)"
            else:
                suggested_size_text = "0.75x (controlled full-risk setup)"

    if macro_caution and execution_state != "stand_aside":
        suggested_size_text = "0.5x (macro caution cap)"

    return execution_state, opportunity_grade, suggested_size_text


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
    blowoff_top: BlowOffTopAnalysis = None,
    strategy_mode: str = "long_term",
    pullback_warning: PullbackWarningAnalysis = None,
    news_sentiment_label: Optional[str] = None,
    benchmark_symbol: str = "benchmark",
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
    aggressiveness_mode = _normalize_aggressiveness_mode(
        settings.aggressiveness_mode if settings else "balanced"
    )
    strategy_mode = _normalize_strategy_mode(strategy_mode)
    enforce_blowoff_guardrail = strategy_mode == "long_term"

    components = compute_composite_score(
        trend_direction=trend.direction.value,
        pullback_detected=pullback.detected,
        near_support=pullback.near_support,
        strength_direction=strength.signal.value,
        adx=float(strength.adx) if strength.adx is not None else None,
    )
    score = components.composite
    reasons = list(components.reasons)

    adx_value = strength.adx

    # Contextual score refinements happen BEFORE final recommendation/classification.
    if tech_indicators:
        if tech_indicators.trend_breakout == "bullish_breakout":
            score = min(score + 15, 100)
            reasons.append(f"Bullish Breakout ({tech_indicators.breakout_confidence * 100:.0f}% confidence)")
        elif tech_indicators.trend_breakout == "bearish_breakout":
            score = max(score - 15, -100)
            reasons.append(f"Bearish Breakout ({tech_indicators.breakout_confidence * 100:.0f}% confidence)")

    if pullback_warning and pullback_warning.is_warning:
        if trend.direction == Signal.BULLISH:
            score = max(score - 20, 0)
        elif trend.direction == Signal.BEARISH:
            score = min(score + 20, 0)
        reasons.append(f"Caution: {pullback_warning.description}")

    label = (news_sentiment_label or "").strip().lower()
    if label == "bullish":
        score = min(score + 10, 100)
        reasons.append("Positive News Sentiment (+10 boost)")
    elif label == "bearish":
        score = max(score - 10, -100)
        reasons.append("Negative News Sentiment (-10 penalty)")

    if relative_strength:
        if relative_strength.label == "Leader":
            score = min(score + 15, 100)
            reasons.append(f"Market Leader: Strong Relative Strength vs {benchmark_symbol} (+15 boost)")
        elif relative_strength.label == "Laggard":
            score = max(score - 15, -100)
            reasons.append(f"Market Laggard: Weak Relative Strength vs {benchmark_symbol} (-15 penalty)")

    if blowoff_top and blowoff_top.applicable:
        if blowoff_top.signals.structure_break:
            if enforce_blowoff_guardrail:
                score = max(score - 10, -100)
            reasons.append("Oil Blow-Off breakdown confirmed (+bearish follow-through edge)")
        elif blowoff_top.detected and blowoff_top.entry_state == "armed" and score < 0:
            if enforce_blowoff_guardrail:
                score = min(score + 12, 0)
                reasons.append("Oil Blow-Off detected without structure break — avoid premature short, wait for breakdown trigger")
            else:
                reasons.append("Blow-Off Watch: setup armed; track breakdown trigger for potential larger downside wave")

    effective_threshold = _effective_conviction_threshold(threshold, adx_value)
    effective_threshold = _apply_aggressiveness_to_threshold(aggressiveness_mode, effective_threshold)
    if effective_threshold != threshold:
        reasons.append(
            f"Adaptive conviction threshold active: {effective_threshold} (base {threshold}, mode={aggressiveness_mode}, ADX={adx_value:.1f})"
        )

    recommendation_str, trade_worthy = classify_recommendation(score, effective_threshold)
    recommendation = Signal(recommendation_str)

    if (
        blowoff_top
        and blowoff_top.applicable
        and blowoff_top.detected
        and recommendation == Signal.BEARISH
        and not blowoff_top.signals.structure_break
        and blowoff_top.entry_state in {"armed", "wait"}
        and enforce_blowoff_guardrail
    ):
        if trade_worthy:
            trade_worthy = False
        reasons.append("Blow-Off Guardrail: bearish bias allowed, but execution stays conditional until structure break confirms")

    if not trade_worthy:
        if score >= 20:
            reasons.append("Bullish setup developing - wait for trigger close confirmation")
        elif score <= -20:
            reasons.append("Bearish setup developing - wait for trigger close confirmation")
        else:
            reasons.append("No clear setup - keep capital protected until direction confirms")

    # ADX pass-through reason (when ADX is above threshold, add as a reason)
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

    execution_state, opportunity_grade, suggested_size_text = _derive_execution_profile(
        recommendation=recommendation,
        trade_worthy=trade_worthy,
        score=score,
        reasons=reasons,
        adx_value=adx_value,
        aggressiveness_mode=aggressiveness_mode,
    )

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
                action_plan = "Conditional Long Setup"
                s1_str = f"${pivots.s1:.2f}" if pivots.s1 else "N/A"
                r1_str = f"${pivots.r1:.2f}" if pivots.r1 else "N/A"
                fib_str = f"${fibs.ret_382:.2f}" if fibs.ret_382 else "N/A"
                action_plan_details = (
                    f"Trigger: close above R1 ({r1_str}) for momentum entry, OR buy pullback near S1 ({s1_str}) / Fib 38.2% ({fib_str}) "
                    f"with bullish confirmation candle."
                )
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
                action_plan = "Conditional Short Setup"
                r1_str = f"${pivots.r1:.2f}" if pivots.r1 else "N/A"
                s1_str = f"${pivots.s1:.2f}" if pivots.s1 else "N/A"
                action_plan_details = (
                    f"Trigger: close below S1 ({s1_str}) for breakdown entry, OR short a rejection bounce near R1 ({r1_str}) "
                    f"with bearish confirmation candle."
                )
                scaling_plan = "Awaiting entry confirmation."
                pyramiding_plan = "Do not pyramid until initial position is firmly in profit."
        else:
            action_plan = "Two-Sided Conditional Plan"
            r1_str = f"${pivots.r1:.2f}" if pivots.r1 else "N/A"
            s1_str = f"${pivots.s1:.2f}" if pivots.s1 else "N/A"
            action_plan_details = (
                f"Long trigger: close above R1 ({r1_str}). Short trigger: close below S1 ({s1_str}). "
                "Until then, keep size light and wait for structure confirmation."
            )
            psychological_guard = "Patience is a position. Awaiting clear structural setup."
            pyramiding_plan = "N/A"
            scaling_plan = "N/A - Sideways Market"

    # Layman's Terms Executive Summary
    summary_parts = []
    
    # 1. State the trend and recommendation
    if recommendation == Signal.NEUTRAL:
        summary_parts.append("Directional edge is neutral right now. Use conditional triggers rather than forcing a discretionary entry.")
    elif recommendation == Signal.BULLISH and trade_worthy:
        summary_parts.append("High-probability BUY setup is active. Conditions support executing a long plan now with disciplined risk.")
    elif recommendation == Signal.BEARISH and trade_worthy:
        summary_parts.append("High-probability SELL setup is active. Conditions support executing a short plan now with disciplined risk.")
    else:
        if recommendation == Signal.BULLISH:
            summary_parts.append("Bias is bullish but execution is conditional. Enter only after trigger confirmation; avoid chasing mid-range price action.")
        else:
            summary_parts.append("Bias is bearish but execution is conditional. Enter only after breakdown/rejection confirmation; avoid premature shorts.")

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
    if execution_state == "ready":
        summary_parts.append(
            f"Conclusion: Execute '{action_plan}' with {suggested_size_text}. Opportunity grade: {opportunity_grade}."
        )
    elif execution_state == "conditional":
        summary_parts.append(
            f"Conclusion: Conditional setup only. Use trigger-based entry and starter risk ({suggested_size_text}). Opportunity grade: {opportunity_grade}."
        )
    else:
        summary_parts.append("Conclusion: Stand aside until directional and trigger alignment improves.")

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
        execution_state=execution_state,
        opportunity_grade=opportunity_grade,
        suggested_size_text=suggested_size_text,
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
