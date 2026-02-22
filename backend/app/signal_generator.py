from typing import List
from .models import (
    TrendAnalysis, PullbackAnalysis, StrengthAnalysis, 
    TradeSignal, Signal, CandleAnalysis, StrategySettings
)


def generate_trade_signal(
    trend: TrendAnalysis,
    pullback: PullbackAnalysis,
    strength: StrengthAnalysis,
    candle: CandleAnalysis,
    benchmark_direction: Signal = Signal.NEUTRAL,
    settings: StrategySettings = None
) -> TradeSignal:
    """
    Generate a composite trade signal based on all analyses.
    
    Ideal setup (bullish):
    1. Monthly trend is bullish (uptrend)
    2. Weekly has pulled back to support
    3. Daily showing strength/momentum in trend direction
    
    Score: -100 (strong sell) to +100 (strong buy)
    """
    score = 0
    reasons = []
    
    # Monthly trend contribution (weight: 40 points)
    if trend.direction == Signal.BULLISH:
        score += 40
        reasons.append("Monthly uptrend confirmed")
    elif trend.direction == Signal.BEARISH:
        score -= 40
        reasons.append("Monthly downtrend - caution")
    else:
        reasons.append("Monthly trend unclear")
    
    # Weekly pullback contribution (weight: 30 points)
    if trend.direction == Signal.BULLISH:
        # In uptrend, pullback to support is bullish
        if pullback.detected and pullback.near_support:
            score += 30
            reasons.append("Pullback to support in uptrend - ideal entry")
        elif pullback.detected:
            score += 15
            reasons.append("Pullback detected, waiting for support")
        else:
            score += 5
            reasons.append("No pullback - extended from support")
    elif trend.direction == Signal.BEARISH:
        # In downtrend, bounce to resistance is bearish
        if pullback.detected and pullback.near_support:
            score -= 10
            reasons.append("Bounce in downtrend - potential short entry")
        else:
            score -= 20
            reasons.append("Downtrend continuation")
    
    # Daily strength contribution (weight: 30 points)
    if strength.signal == Signal.BULLISH:
        if trend.direction == Signal.BULLISH:
            score += 30
            reasons.append("Daily strength confirms uptrend")
        else:
            score += 10
            reasons.append("Daily bullish but against trend")
    elif strength.signal == Signal.BEARISH:
        if trend.direction == Signal.BEARISH:
            score -= 30
            reasons.append("Daily weakness confirms downtrend")
        else:
            score -= 10
            reasons.append("Daily bearish but against trend")
    else:
        reasons.append("Daily momentum neutral")

    # Determine recommendation based on score
    threshold = settings.conviction_threshold if settings else 70
    
    if score >= threshold:
        recommendation = Signal.BULLISH
        trade_worthy = True
    elif score <= -threshold:
        recommendation = Signal.BEARISH
        trade_worthy = True
    elif score >= 20:
        recommendation = Signal.BULLISH
        trade_worthy = False
        reasons.append("Setup developing but not ideal yet")
    elif score <= -20:
        recommendation = Signal.BEARISH
        trade_worthy = False
        reasons.append("Bearish setup developing")
    else:
        recommendation = Signal.NEUTRAL
        trade_worthy = False
        reasons.append("No clear setup - wait for better opportunity")
    
    # Hard Filter 1: ADX must be > threshold for a trade-worthy signal
    adx_value = strength.adx
    adx_threshold = settings.adx_threshold if settings else 25
    
    if trade_worthy and adx_value <= adx_threshold:
        trade_worthy = False
        reasons.append(f"Filter: Trend strength (ADX={adx_value:.1f}) too low. Threshold: {adx_threshold}")
    elif adx_value > adx_threshold:
        reasons.append(f"Trend strength high (ADX={adx_value:.1f})")

    # Hard Filter 2: Market Beta (Benchmark Correlation)
    # If SPX/BTC is bearish, we don't buy anything.
    if trade_worthy and recommendation == Signal.BULLISH and benchmark_direction == Signal.BEARISH:
        trade_worthy = False
        reasons.append("Beta Filter: Avoid buying individual assets while major market benchmark is in a downtrend.")
    elif trade_worthy and recommendation == Signal.BEARISH and benchmark_direction == Signal.BULLISH:
        trade_worthy = False
        reasons.append("Beta Filter: Avoid shorting while major market benchmark is rally.")

    # Hard Filter 3: Price Action Trigger (Candlestick Pattern)
    # We want to see a confirmation candle (Hammer/Engulfing) at support.
    if trade_worthy:
        has_bullish_candle = candle.is_bullish is True
        has_bearish_candle = candle.is_bullish is False
        
        if recommendation == Signal.BULLISH and not has_bullish_candle:
            trade_worthy = False
            reasons.append(f"Trigger Filter: Waiting for a bullish reversal candle (Engulfing/Hammer) to confirm entry. Currently: {candle.pattern}")
        elif recommendation == Signal.BEARISH and not has_bearish_candle:
            trade_worthy = False
            reasons.append(f"Trigger Filter: Waiting for a bearish reversal candle (Shooting Star/Engulfing) to confirm entry. Currently: {candle.pattern}")
        elif candle.is_bullish is not None:
             reasons.append(f"Price Action Trigger confirmed: {candle.description}")

    return TradeSignal(
        recommendation=recommendation,
        score=score,
        reasons=reasons,
        trade_worthy=trade_worthy
    )
