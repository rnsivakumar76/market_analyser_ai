import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
from ..models import TechnicalAnalysis, PivotPoints, Signal

def calculate_pivot_points(df: pd.DataFrame) -> PivotPoints:
    """
    Calculate Standard Pivot Points using the previous day's data.
    If the current session is ongoing, we use the OHLC of the previous complete candle.
    """
    if len(df) < 2:
        zero = 0.0
        return PivotPoints(pivot=zero, r1=zero, r2=zero, s1=zero, s2=zero)
    
    # Use the previous complete bar (the last one is usually the current live one)
    prev_bar = df.iloc[-2]
    high = prev_bar['High']
    low = prev_bar['Low']
    close = prev_bar['Close']
    
    pivot = (high + low + close) / 3
    r1 = (2 * pivot) - low
    s1 = (2 * pivot) - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)
    
    return PivotPoints(
        pivot=round(float(pivot), 2),
        r1=round(float(r1), 2),
        r2=round(float(r2), 2),
        s1=round(float(s1), 2),
        s2=round(float(s2), 2)
    )

def analyze_least_resistance_line(df: pd.DataFrame) -> str:
    """
    Determine the 'Line of Least Resistance' based on the slope of the 
    linear regression of the last 20 periods and current price position relative to it.
    """
    if len(df) < 20:
        return "flat"
    
    y = df['Close'].tail(20).values
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1)
    
    # Normalizing slope by price to make it comparable
    relative_slope = slope / df['Close'].iloc[-1]
    
    if relative_slope > 0.001:  # 0.1% growth per bar
        return "up"
    elif relative_slope < -0.001:
        return "down"
    else:
        return "flat"

def detect_trend_breakout(df: pd.DataFrame) -> Tuple[str, float]:
    """
    Detect if the price is breaking out of a recent range.
    Uses a 20-period Donchian Channel breakout.
    """
    if len(df) < 21:
        return "none", 0.0
    
    current_close = df['Close'].iloc[-1]
    current_volume = df['Volume'].iloc[-1]
    
    # Previous 20 bars range
    prev_20 = df.iloc[-21:-1]
    upper_band = prev_20['High'].max()
    lower_band = prev_20['Low'].min()
    avg_vol = prev_20['Volume'].mean()
    
    vol_ratio = current_volume / avg_vol if avg_vol > 0 else 1.0
    
    if current_close > upper_band:
        # Bullish breakout
        confidence = min(vol_ratio / 2, 1.0) # Higher volume = higher confidence
        return "bullish_breakout", confidence
    elif current_close < lower_band:
        # Bearish breakout
        confidence = min(vol_ratio / 2, 1.0)
        return "bearish_breakout", confidence
    
    return "none", 0.0

def analyze_technical_indicators(df: pd.DataFrame) -> TechnicalAnalysis:
    """Main function to consolidate technical indicators."""
    pivots = calculate_pivot_points(df)
    least_resistance = analyze_least_resistance_line(df)
    breakout_type, confidence = detect_trend_breakout(df)
    
    current_price = df['Close'].iloc[-1]
    
    # Construct description
    pivot_desc = f"Pivot at {pivots.pivot}."
    if current_price > pivots.r1:
        pivot_desc += " Price trading above Resistances."
    elif current_price < pivots.s1:
        pivot_desc += " Price trading below Supports."
    
    breakout_desc = ""
    if breakout_type == "bullish_breakout":
        breakout_desc = f" BULLISH BREAKOUT detected with {confidence*100:.0f}% vol confirmation."
    elif breakout_type == "bearish_breakout":
        breakout_desc = f" BEARISH BREAKOUT detected with {confidence*100:.0f}% vol confirmation."
    
    resistance_desc = f" Line of Least Resistance is {least_resistance.upper()}."
    
    return TechnicalAnalysis(
        pivot_points=pivots,
        least_resistance_line=least_resistance,
        trend_breakout=breakout_type,
        breakout_confidence=float(confidence),
        description=f"{pivot_desc}{resistance_desc}{breakout_desc}"
    )
