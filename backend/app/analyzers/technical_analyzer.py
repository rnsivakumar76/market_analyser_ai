import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional
from ..models import TechnicalAnalysis, PivotPoints, Signal, FibonacciLevels
from .strength_analyzer import calculate_rsi

def calculate_pivot_points(df: pd.DataFrame) -> PivotPoints:
    """
    Calculate Standard Pivot Points using the previous day's data.
    If the current session is ongoing, we use the OHLC of the previous complete candle.
    """
    if len(df) < 2:
        zero = 0.0
        return PivotPoints(pivot=zero, r1=zero, r2=zero, r3=zero, s1=zero, s2=zero, s3=zero)
    
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
    r3 = high + 2 * (pivot - low)
    s3 = low - 2 * (high - pivot)
    
    return PivotPoints(
        pivot=round(float(pivot), 2),
        r1=round(float(r1), 2),
        r2=round(float(r2), 2),
        r3=round(float(r3), 2),
        s1=round(float(s1), 2),
        s2=round(float(s2), 2),
        s3=round(float(s3), 2)
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

def calculate_fibonacci_levels(df: pd.DataFrame) -> FibonacciLevels:
    """Calculate recent swing Fibonacci retracements and extensions."""
    if len(df) < 20:
        zero = 0.0
        return FibonacciLevels(trend="flat", swing_high=zero, swing_low=zero, ret_382=zero, ret_500=zero, ret_618=zero, ext_1272=zero, ext_1618=zero)
        
    recent_period = df.tail(60) # look at last 60 days for major swing
    high = recent_period['High'].max()
    low = recent_period['Low'].min()
    current = df['Close'].iloc[-1]
    
    diff = high - low
    if diff == 0:
        return FibonacciLevels(trend="flat", swing_high=high, swing_low=low, ret_382=high, ret_500=high, ret_618=high, ext_1272=high, ext_1618=high)
        
    if (current - low) >= (high - current):
        trend = "up"
        ret_382 = high - (diff * 0.382)
        ret_500 = high - (diff * 0.500)
        ret_618 = high - (diff * 0.618)
        ext_1272 = low + (diff * 1.272)
        ext_1618 = low + (diff * 1.618)
    else:
        trend = "down"
        ret_382 = low + (diff * 0.382)
        ret_500 = low + (diff * 0.500)
        ret_618 = low + (diff * 0.618)
        ext_1272 = high - (diff * 1.272)
        ext_1618 = high - (diff * 1.618)
        
    return FibonacciLevels(
        trend=trend,
        swing_high=round(float(high), 2),
        swing_low=round(float(low), 2),
        ret_382=round(float(ret_382), 2),
        ret_500=round(float(ret_500), 2),
        ret_618=round(float(ret_618), 2),
        ext_1272=round(float(ext_1272), 2),
        ext_1618=round(float(ext_1618), 2)
    )


def detect_rsi_divergence(df: pd.DataFrame, lookback: int = 20) -> Optional[str]:
    """
    Detect RSI divergence over the last `lookback` bars.
    Returns: 'bullish' | 'bearish' | None
    
    Bullish divergence: price makes lower low, RSI makes higher low -> reversal up
    Bearish divergence: price makes higher high, RSI makes lower high -> reversal down
    """
    if len(df) < lookback + 2:
        return None
    
    recent = df.tail(lookback + 2).copy()
    closes = recent['Close']
    
    # Calculate RSI series
    delta = closes.diff()
    gain = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss = (-delta).where(delta < 0, 0.0).rolling(14).mean()
    rs = gain / loss.replace(0, float('inf'))
    rsi_series = (100 - (100 / (1 + rs))).dropna()
    
    if len(rsi_series) < 4:
        return None
    
    # Mid-point vs current
    mid = len(closes) // 2
    price_mid = float(closes.iloc[mid])
    price_now = float(closes.iloc[-1])
    rsi_mid = float(rsi_series.iloc[len(rsi_series) // 2])
    rsi_now = float(rsi_series.iloc[-1])
    
    # Bearish divergence: price higher high, RSI lower high
    if price_now > price_mid * 1.005 and rsi_now < rsi_mid - 3:
        return 'bearish'
    
    # Bullish divergence: price lower low, RSI higher low
    if price_now < price_mid * 0.995 and rsi_now > rsi_mid + 3:
        return 'bullish'
    
    return None

def analyze_technical_indicators(df: pd.DataFrame) -> TechnicalAnalysis:
    """Main function to consolidate technical indicators."""
    pivots = calculate_pivot_points(df)
    fibs = calculate_fibonacci_levels(df)
    least_resistance = analyze_least_resistance_line(df)
    breakout_type, confidence = detect_trend_breakout(df)
    rsi_divergence = detect_rsi_divergence(df)
    
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
    
    divergence_desc = ""
    if rsi_divergence == 'bullish':
        divergence_desc = " RSI Bullish Divergence detected — potential reversal up."
    elif rsi_divergence == 'bearish':
        divergence_desc = " RSI Bearish Divergence detected — potential reversal down."
    
    resistance_desc = f" Line of Least Resistance is {least_resistance.upper()}."
    
    return TechnicalAnalysis(
        pivot_points=pivots,
        fibonacci=fibs,
        least_resistance_line=least_resistance,
        trend_breakout=breakout_type,
        breakout_confidence=float(confidence),
        rsi_divergence=rsi_divergence,
        description=f"{pivot_desc}{resistance_desc}{breakout_desc}{divergence_desc}"
    )
