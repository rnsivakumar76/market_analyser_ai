import pandas as pd
import numpy as np
from typing import Dict, Any
from ..models import TrendAnalysis, Signal


def calculate_moving_average(data: pd.Series, period: int) -> pd.Series:
    """Calculate simple moving average."""
    return data.rolling(window=period).mean()


def analyze_monthly_trend(
    daily_data: pd.DataFrame,
    params: Dict[str, Any]
) -> TrendAnalysis:
    """
    Analyze monthly trend using moving averages.
    
    Bullish: Price > Fast MA > Slow MA (uptrend)
    Bearish: Price < Fast MA < Slow MA (downtrend)
    Neutral: Mixed signals
    """
    fast_period = params.get('fast_ma_period', 20)
    slow_period = params.get('slow_ma_period', 50)
    
    close_prices = daily_data['Close']
    current_price = float(close_prices.iloc[-1])
    
    # Calculate MAs
    fast_ma = calculate_moving_average(close_prices, fast_period)
    slow_ma = calculate_moving_average(close_prices, slow_period)
    
    current_fast_ma = float(fast_ma.iloc[-1]) if not pd.isna(fast_ma.iloc[-1]) else current_price
    current_slow_ma = float(slow_ma.iloc[-1]) if not pd.isna(slow_ma.iloc[-1]) else current_price
    
    price_above_fast = current_price > current_fast_ma
    price_above_slow = current_price > current_slow_ma
    fast_above_slow = current_fast_ma > current_slow_ma
    
    # Determine trend direction
    if price_above_fast and price_above_slow and fast_above_slow:
        direction = Signal.BULLISH
        description = f"Strong uptrend: Price ({current_price:.2f}) > {fast_period}MA ({current_fast_ma:.2f}) > {slow_period}MA ({current_slow_ma:.2f})"
    elif not price_above_fast and not price_above_slow and not fast_above_slow:
        direction = Signal.BEARISH
        description = f"Strong downtrend: Price ({current_price:.2f}) < {fast_period}MA ({current_fast_ma:.2f}) < {slow_period}MA ({current_slow_ma:.2f})"
    else:
        direction = Signal.NEUTRAL
        description = f"Mixed trend signals: Price={current_price:.2f}, {fast_period}MA={current_fast_ma:.2f}, {slow_period}MA={current_slow_ma:.2f}"
    
    return TrendAnalysis(
        direction=direction,
        fast_ma=round(current_fast_ma, 2),
        slow_ma=round(current_slow_ma, 2),
        price_above_fast_ma=price_above_fast,
        price_above_slow_ma=price_above_slow,
        description=description
    )
