"""Position Exit Analyzer - Systematic loss-cutting mechanism.

This analyzer detects when short-term trends contradict long-term positions
and provides clear exit signals to prevent holding losing positions too long.
"""
import pandas as pd
import numpy as np
from typing import Optional, Tuple
from app.models import (
    PositionExitAnalysis, TrendAnalysis, StrengthAnalysis,
    VolatilityAnalysis, Signal, TechnicalAnalysis, TradePlan
)


def analyze_position_exit(
    trend: TrendAnalysis,
    strength: StrengthAnalysis,
    volatility: VolatilityAnalysis,
    technical_indicators: Optional[TechnicalAnalysis],
    current_price: float,
    assumed_entry_price: Optional[float] = None,
    assumed_position_side: Optional[str] = None,  # "long" or "short"
    execution_data: Optional[pd.DataFrame] = None,
    trade_plan: Optional[TradePlan] = None,
) -> PositionExitAnalysis:
    """Analyze whether an existing position should be exited.

    This is the core systematic loss-cutting mechanism. It detects:
    1. Multi-timeframe divergence (long-term bullish but short-term bearish)
    2. Momentum exhaustion (RSI extremes)
    3. Support/resistance breaks
    4. Volatility regime changes
    5. Drawdown severity

    Args:
        trend: Long-term trend analysis (monthly/weekly)
        strength: Short-term strength analysis (daily/hourly)
        volatility: Volatility and ATR analysis
        technical_indicators: Technical levels (pivot points, fibonacci)
        current_price: Current market price
        assumed_entry_price: Entry price of the position (if known)
        assumed_position_side: "long" or "short" (if known)
        execution_data: Price data for deeper analysis
        trade_plan: Canonical trade plan (SSOT) — its `invalidation` field is used
                     as the structural stop level when available.

    Returns:
        PositionExitAnalysis with exit recommendations
    """
    factors = []
    exit_urgency_score = 0  # 0-100, higher = more urgent
    divergence_detected = False
    divergence_type = "none"
    
    # If position side not provided, infer from the long-term trend. A neutral
    # trend has NO implied position — defaulting to "short" produced phantom exit
    # alerts that contradicted the system's actual bias. In that case return a
    # not-applicable result instead of guessing a side.
    if assumed_position_side is None:
        if trend.direction == Signal.BULLISH:
            assumed_position_side = "long"
        elif trend.direction == Signal.BEARISH:
            assumed_position_side = "short"
        else:
            max_acceptable = round(2.0 * volatility.atr if volatility.atr > 0 else 2.0, 2)
            bars = len(execution_data) if execution_data is not None and not execution_data.empty else 0
            return PositionExitAnalysis(
                should_exit=False,
                exit_urgency="NONE",
                exit_reason=(
                    "No directional position thesis — the system has no active bullish "
                    "or bearish bias, so loss-cutting analysis does not apply."
                ),
                position_health="HEALTHY",
                divergence_detected=False,
                divergence_type="none",
                current_drawdown_pct=0.0,
                max_acceptable_drawdown_pct=max_acceptable,
                time_in_position_bars=bars,
                recommended_action="No position bias to manage. Wait for a directional setup.",
                stop_loss_level=None,
                recovery_probability=1.0,
                factors=[],
            )
    
    # If entry price not provided, assume it's at a reasonable level
    if assumed_entry_price is None:
        assumed_entry_price = current_price
    
    # Calculate current drawdown
    if assumed_position_side == "long":
        current_drawdown_pct = ((assumed_entry_price - current_price) / assumed_entry_price) * 100
    else:
        current_drawdown_pct = ((current_price - assumed_entry_price) / assumed_entry_price) * 100
    
    # 1. Multi-Timeframe Divergence Detection
    # This is the KEY issue: long-term bullish but short-term bearish
    if trend.direction == Signal.BULLISH and strength.signal == Signal.BEARISH:
        divergence_detected = True
        divergence_type = "trend_reversal"
        exit_urgency_score += 30
        factors.append("CRITICAL: Short-term momentum turned bearish while long-term trend is bullish - trend reversal risk")
    elif trend.direction == Signal.BEARISH and strength.signal == Signal.BULLISH:
        divergence_detected = True
        divergence_type = "trend_reversal"
        exit_urgency_score += 30
        factors.append("CRITICAL: Short-term momentum turned bullish while long-term trend is bearish - trend reversal risk")
    
    # 2. Momentum Exhaustion (RSI)
    rsi = strength.rsi if strength.rsi else 50
    if assumed_position_side == "long":
        if rsi < 30:
            exit_urgency_score += 25
            factors.append(f"RSI oversold ({rsi:.1f}) - long position in deep oversold territory, may indicate trend breakdown")
        elif rsi < 40:
            exit_urgency_score += 15
            factors.append(f"RSI weakening ({rsi:.1f}) - momentum deteriorating for long position")
    else:  # short position
        if rsi > 70:
            exit_urgency_score += 25
            factors.append(f"RSI overbought ({rsi:.1f}) - short position in overbought territory, squeeze risk")
        elif rsi > 60:
            exit_urgency_score += 15
            factors.append(f"RSI strengthening ({rsi:.1f}) - momentum turning against short position")
    
    # 3. Support/Resistance Break Analysis
    if technical_indicators and technical_indicators.pivot_points:
        pivots = technical_indicators.pivot_points
        if assumed_position_side == "long":
            # Check if price broke below key support
            if current_price < pivots.s1:
                exit_urgency_score += 35
                divergence_detected = True
                divergence_type = "support_break"
                factors.append(f"Price broke below S1 support ({pivots.s1:.2f}) - structural breakdown for long position")
            elif current_price < pivots.pivot:
                exit_urgency_score += 20
                factors.append(f"Price below pivot ({pivots.pivot:.2f}) - weakening structure for long position")
        else:  # short position
            # Check if price broke above key resistance
            if current_price > pivots.r1:
                exit_urgency_score += 35
                divergence_detected = True
                divergence_type = "support_break"
                factors.append(f"Price broke above R1 resistance ({pivots.r1:.2f}) - structural breakdown for short position")
            elif current_price > pivots.pivot:
                exit_urgency_score += 20
                factors.append(f"Price above pivot ({pivots.pivot:.2f}) - weakening structure for short position")
    
    # 4. Volatility Regime Analysis
    if volatility.atr_regime in ["ELEVATED", "EXTREME"]:
        exit_urgency_score += 15
        factors.append(f"Volatility regime {volatility.volatility_regime_label} - wider swings increase loss risk")
    
    # 5. Drawdown Severity
    max_acceptable_drawdown = 2.0 * volatility.atr if volatility.atr > 0 else 2.0  # 2x ATR as baseline
    if current_drawdown_pct > max_acceptable_drawdown * 2:
        exit_urgency_score += 40
        factors.append(f"Drawdown {current_drawdown_pct:.2f}% exceeds 2x acceptable level ({max_acceptable_drawdown*2:.2f}%) - CUT LOSSES NOW")
    elif current_drawdown_pct > max_acceptable_drawdown:
        exit_urgency_score += 25
        factors.append(f"Drawdown {current_drawdown_pct:.2f}% exceeds acceptable level ({max_acceptable_drawdown:.2f}%) - consider exit")
    
    # 6. ADX Trend Strength Check
    adx = strength.adx if strength.adx else 0
    if divergence_detected and adx < 20:
        exit_urgency_score += 10
        factors.append(f"Low ADX ({adx:.1f}) with divergence - choppy market increases loss risk")
    
    # 7. Price Momentum (daily change)
    if strength.price_change_percent:
        if assumed_position_side == "long" and strength.price_change_percent < -2:
            exit_urgency_score += 15
            factors.append(f"Strong daily decline ({strength.price_change_percent:.2f}%) - momentum accelerating against long")
        elif assumed_position_side == "short" and strength.price_change_percent > 2:
            exit_urgency_score += 15
            factors.append(f"Strong daily rally ({strength.price_change_percent:.2f}%) - momentum accelerating against short")
    
    # Calculate exit urgency level
    if exit_urgency_score >= 70:
        exit_urgency = "IMMEDIATE"
        should_exit = True
    elif exit_urgency_score >= 50:
        exit_urgency = "HIGH"
        should_exit = True
    elif exit_urgency_score >= 30:
        exit_urgency = "MODERATE"
        should_exit = True
    elif exit_urgency_score >= 15:
        exit_urgency = "LOW"
        should_exit = False
    else:
        exit_urgency = "NONE"
        should_exit = False
    
    # Calculate position health
    if current_drawdown_pct > max_acceptable_drawdown * 2:
        position_health = "CRITICAL"
    elif current_drawdown_pct > max_acceptable_drawdown:
        position_health = "DAMAGED"
    elif divergence_detected:
        position_health = "WEAKENING"
    elif exit_urgency_score > 0:
        position_health = "HEALTHY"
    else:
        position_health = "STRONG"
    
    # Calculate recovery probability (inverse of urgency)
    recovery_probability = max(0.0, 1.0 - (exit_urgency_score / 100.0))
    
    # Generate exit reason — humanised, and deliberately NOT a restatement of the
    # MTF conflict (the WAIT verdict already explains that). This line speaks to an
    # EXISTING position: what risk has emerged and why it matters for holders.
    _divergence_label = {
        "trend_reversal": "Trend-reversal risk",
        "momentum_shift": "Momentum shift",
        "support_break": "Structure break",
    }.get(divergence_type, "Risk building")
    if divergence_detected:
        exit_reason = (
            f"{_divergence_label} — short-term momentum has turned against the "
            f"longer-term position. Tighten risk on open exposure."
        )
    elif current_drawdown_pct > max_acceptable_drawdown:
        exit_reason = f"Drawdown exceeded acceptable threshold: {current_drawdown_pct:.2f}% vs {max_acceptable_drawdown:.2f}% max."
    else:
        exit_reason = "Multiple risk factors accumulating."
    
    # Generate recommended action
    if exit_urgency == "IMMEDIATE":
        recommended_action = "EXIT POSITION IMMEDIATELY - Market structure has broken against your position. Do not wait for recovery."
    elif exit_urgency == "HIGH":
        recommended_action = "EXIT POSITION NOW - Risk of further loss is high. Cut losses before they compound."
    elif exit_urgency == "MODERATE":
        recommended_action = "Consider exiting - Position is weakening. If price moves further against you, exit immediately."
    elif exit_urgency == "LOW":
        recommended_action = "Monitor closely - Early warning signs. Be prepared to exit if conditions worsen."
    else:
        recommended_action = "Hold position - No immediate exit signals. Continue monitoring."
    
    # Calculate dynamic stop loss level — use canonical plan invalidation when available
    stop_loss_level = None
    if trade_plan and trade_plan.invalidation is not None:
        stop_loss_level = trade_plan.invalidation
    elif technical_indicators and technical_indicators.pivot_points:
        if assumed_position_side == "long":
            # Use S2 as emergency stop if S1 already broken
            if current_price < technical_indicators.pivot_points.s1:
                stop_loss_level = technical_indicators.pivot_points.s2
            else:
                stop_loss_level = technical_indicators.pivot_points.s1
        else:
            # Use R2 as emergency stop if R1 already broken
            if current_price > technical_indicators.pivot_points.r1:
                stop_loss_level = technical_indicators.pivot_points.r2
            else:
                stop_loss_level = technical_indicators.pivot_points.r1
    
    # Estimate time in position (use data length if available)
    time_in_position_bars = 0
    if execution_data is not None and not execution_data.empty:
        time_in_position_bars = len(execution_data)
    
    return PositionExitAnalysis(
        should_exit=should_exit,
        exit_urgency=exit_urgency,
        exit_reason=exit_reason,
        position_health=position_health,
        divergence_detected=divergence_detected,
        divergence_type=divergence_type,
        current_drawdown_pct=round(current_drawdown_pct, 2),
        max_acceptable_drawdown_pct=round(max_acceptable_drawdown, 2),
        time_in_position_bars=time_in_position_bars,
        recommended_action=recommended_action,
        stop_loss_level=stop_loss_level,
        recovery_probability=round(recovery_probability, 2),
        factors=factors
    )


def detect_trend_divergence(
    long_term_direction: str,
    short_term_direction: str,
    short_term_strength: float,  # score or conviction
) -> Tuple[bool, str, str]:
    """Detect if short-term trend is diverging from long-term trend.
    
    Returns:
        (is_diverging, divergence_type, description)
    """
    if long_term_direction == short_term_direction:
        return False, "none", "Trends aligned"
    
    if long_term_direction == "bullish" and short_term_direction == "bearish":
        if short_term_strength > 60:
            return True, "trend_reversal", "Strong bearish reversal against bullish long-term trend"
        else:
            return True, "momentum_shift", "Moderate bearish momentum shift against bullish long-term trend"
    
    if long_term_direction == "bearish" and short_term_direction == "bullish":
        if short_term_strength > 60:
            return True, "trend_reversal", "Strong bullish reversal against bearish long-term trend"
        else:
            return True, "momentum_shift", "Moderate bullish momentum shift against bearish long-term trend"
    
    return False, "none", "No clear divergence"
