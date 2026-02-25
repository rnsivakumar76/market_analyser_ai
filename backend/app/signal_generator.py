from typing import List
from .models import (
    TrendAnalysis, PullbackAnalysis, StrengthAnalysis, 
    TradeSignal, Signal, CandleAnalysis, StrategySettings,
    FundamentalsAnalysis, RelativeStrengthAnalysis
)


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

    # Hard Filter 4: Fundamental Event Guard (Macro Shield)
    if trade_worthy and fundamentals and fundamentals.has_high_impact_events:
        trade_worthy = False
        score = max(score - 20, -100) if score > 0 else min(score + 20, 100)
        reasons.append("Macro Shield Active: Trade blocked due to high-impact economic events or earnings within 48h.")

    # Hard Filter 5: Relative Strength (Alpha Shield)
    if trade_worthy and relative_strength:
        if recommendation == Signal.BULLISH and not relative_strength.is_outperforming:
            trade_worthy = False
            reasons.append("Alpha Filter: Trade blocked. This instrument is a market laggard (underperforming its benchmark). Institutional money flows into leaders.")
        elif recommendation == Signal.BEARISH and relative_strength.is_outperforming:
            trade_worthy = False
            reasons.append("Alpha Filter: Trade blocked. This instrument is showing resilient strength vs the market. Dangerous to short market leaders.")

    action_plan = "Stand Aside"
    action_plan_details = "Market conditions do not support a high-probability trade."
    psychological_guard = "Discipline: Do not force a trade in choppy or uncertain markets."
    pyramiding_plan = "N/A"
    scaling_plan = "Wait for clear trend alignment."

    if current_price and tech_indicators:
        pivots = tech_indicators.pivot_points
        fibs = tech_indicators.fibonacci
        
        # Base Scaling text
        s_tp1 = s_tp2 = s_tp3 = ""
        if volatility:
            s_tp1 = f"${volatility.take_profit_level1:.2f}"
            s_tp2 = f"${volatility.take_profit_level2:.2f}"
            s_tp3 = f"${volatility.take_profit:.2f}"

        if recommendation == Signal.BULLISH:
            psychological_guard = "NEVER average down into a losing trade. If price falls below support or hits your stop loss, cut the trade immediately. The market does not owe you a bounce."
            if trade_worthy:
                action_plan = "Enter Long (Market)"
                action_plan_details = f"Strong bullish setup confirmed near ${current_price:.2f}. Support is Pivot (${pivots.pivot}). If trend accelerates, target Fibonacci Extensions."
                
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
                action_plan_details = f"Ideal entry is on a pullback near support (S1: ${pivots.s1}) or the 38.2% Fib Retracement (${fibs.ret_382})."
                scaling_plan = "Awaiting entry confirmation before finalizing exit stages."
                pyramiding_plan = "Do not pyramid until initial position is firmly in profit."
        elif recommendation == Signal.BEARISH:
            psychological_guard = "NEVER average up into a losing short. If price rallies past resistance, cover immediately. Infinite downside risk in shorts."
            if trade_worthy:
                action_plan = "Enter Short (Market)"
                action_plan_details = f"Strong bearish setup confirmed near ${current_price:.2f}. Resistance is Pivot (${pivots.pivot}). If decline accelerates, target Fibonacci Extensions."
                
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
                action_plan_details = f"Ideal entry is on a bounce near resistance (R1: ${pivots.r1}) or 38.2% Fib Retracement."
                scaling_plan = "Awaiting entry confirmation."
                pyramiding_plan = "Do not pyramid until initial position is firmly in profit."
        else:
            action_plan = "Wait and Observe"
            action_plan_details = f"Neutral bias. Key zones: R1 (${pivots.r1}) and S1 (${pivots.s1})."
            psychological_guard = "Patience is a position. Awaiting clear structural setup."
            pyramiding_plan = "N/A"
            scaling_plan = "N/A - Sideways Market"

    return TradeSignal(
        recommendation=recommendation,
        score=score,
        reasons=reasons,
        trade_worthy=trade_worthy,
        action_plan=action_plan,
        action_plan_details=action_plan_details,
        psychological_guard=psychological_guard,
        pyramiding_plan=pyramiding_plan,
        scaling_plan=scaling_plan
    )
