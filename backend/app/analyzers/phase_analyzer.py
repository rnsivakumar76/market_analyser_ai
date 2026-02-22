import pandas as pd
import numpy as np
from typing import Dict, Any
from ..models import MarketPhase, PhaseAnalysis, Signal

def analyze_market_phase(daily_data: pd.DataFrame, params: Dict[str, Any] = None) -> PhaseAnalysis:
    """
    Identify the current market phase based on moving averages and price action.
    
    Phases:
    1. Accumulation: Bottoming, sideways after downtrend.
    2. Markup: Clear uptrend.
    3. Distribution: Topping, sideways after uptrend.
    4. Markdown: Clear downtrend.
    5. Liquidation: Panic selling, high momentum downtrend.
    6. Consolidation: General sideways movement.
    """
    if params is None:
        params = {}
        
    fast_period = params.get('fast_ma', 20)
    slow_period = params.get('slow_ma', 50)
    
    close = daily_data['Close']
    
    # Calculate MAs
    ma20 = close.rolling(window=fast_period).mean()
    ma50 = close.rolling(window=slow_period).mean()
    
    # Check if we have enough data
    if len(ma50.dropna()) < 10:
        return PhaseAnalysis(
            phase=MarketPhase.CONSOLIDATION,
            score=0,
            description="Insufficient data for phase analysis. Need more history."
        )
    
    # Current values
    curr_price = float(close.iloc[-1])
    curr_ma20 = float(ma20.iloc[-1])
    curr_ma50 = float(ma50.iloc[-1])
    
    # Prev values (to check slope)
    # Get last valid ma50 index
    valid_ma50 = ma50.dropna()
    if len(valid_ma50) < 6:
        prev_ma50 = curr_ma50
    else:
        prev_ma50 = float(valid_ma50.iloc[-5])
    
    # Slopes and Relationships
    ma50_slope = (curr_ma50 - prev_ma50) / prev_ma50 if prev_ma50 != 0 else 0
    ma_order_bullish = curr_ma20 > curr_ma50
    price_above_mas = curr_price > curr_ma20 and curr_price > curr_ma50
    price_below_mas = curr_price < curr_ma20 and curr_price < curr_ma50
    
    # Check for Liquidation (Extreme version of Markdown)
    # Using Price change for liquidation
    # Safely get index for recent change
    idx_5 = max(0, len(close) - 5)
    recent_change = (curr_price - float(close.iloc[idx_5])) / float(close.iloc[idx_5]) if float(close.iloc[idx_5]) != 0 else 0
    
    if ma50_slope > 0.005: # Upward slope
        if price_above_mas and ma_order_bullish:
            phase = MarketPhase.MARKUP
            desc = "Instrument is in a clear Markup (Uptrend) phase. Demand exceeds supply."
        else:
            phase = MarketPhase.DISTRIBUTION
            desc = "Potential Distribution phase. Price is stalling or failing to maintain uptrend momentum."
    
    elif ma50_slope < -0.005: # Downward slope
        if recent_change < -0.08: # Sharp 5-day drop
            phase = MarketPhase.LIQUIDATION
            desc = "Liquidation phase detected! Sharp price drop with high momentum. Panic selling."
        elif price_below_mas and not ma_order_bullish:
            phase = MarketPhase.MARKDOWN
            desc = "Instrument is in a Markdown (Downtrend) phase. Supply exceeds demand."
        else:
            phase = MarketPhase.ACCUMULATION
            desc = "Potential Accumulation phase. Price is bottoming out and sideways movement is starting."
            
    else: # Flat slope
        if ma_order_bullish:
            phase = MarketPhase.DISTRIBUTION
            desc = "Distribution phase. Price is consolidating at relative highs. Supply is meeting demand."
        elif not ma_order_bullish and curr_price > curr_ma20:
            phase = MarketPhase.ACCUMULATION
            desc = "Accumulation phase. Price is consolidating at relative lows. Demand is starting to pick up."
        else:
            phase = MarketPhase.CONSOLIDATION
            desc = "General Consolidation. Market is sideways with no clear winner between bulls and bears."

    return PhaseAnalysis(
        phase=phase,
        score=round(ma50_slope * 1000, 2), # Using slope as a proxy for 'phase strength'
        description=desc
    )
