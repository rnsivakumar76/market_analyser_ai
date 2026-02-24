import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from ..models import PullbackWarningAnalysis, Signal
from .volatility_analyzer import calculate_atr

def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """Calculate the Relative Strength Index."""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    # Avoid division by zero
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def calculate_macd(data: pd.Series) -> pd.DataFrame:
    """Calculate MACD, Signal line and Histogram."""
    exp1 = data.ewm(span=12, adjust=False).mean()
    exp2 = data.ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    return pd.DataFrame({'macd': macd, 'signal': signal, 'hist': hist})

def calculate_bollinger_bands(data: pd.Series, period: int = 20, std_dev: int = 2) -> pd.DataFrame:
    """Calculate Bollinger Bands."""
    ma = data.rolling(window=period).mean()
    std = data.rolling(window=period).std()
    upper = ma + (std * std_dev)
    lower = ma - (std * std_dev)
    return pd.DataFrame({'upper': upper, 'lower': lower, 'ma': ma})

def analyze_pullback_warning(df: pd.DataFrame, trend_direction: Signal) -> PullbackWarningAnalysis:
    """
    Detect early exhaustion signs near range high/low.
    Uses a scoring system based on RSI, MACD, ATR, Bollinger Bands and Structure.
    """
    if len(df) < 50:
        return PullbackWarningAnalysis(
            warning_score=0,
            is_warning=False,
            reasons=["Insufficient data"],
            description="Not enough data to run pullback warning analysis."
        )

    score = 0
    reasons = []
    
    close = df['Close']
    high = df['High']
    low = df['Low']
    
    # 1. RSI Divergence (Weight: 2)
    rsi = calculate_rsi(close)
    lookback = 20
    
    if trend_direction == Signal.BULLISH:
        # Check for Bearish Divergence
        # Find local peaks in price over the lookback
        prev_data = df.iloc[-lookback-1:-1]
        recent_high_idx = prev_data['High'].idxmax()
        
        if high.iloc[-1] > high.loc[recent_high_idx] and rsi.iloc[-1] < rsi.loc[recent_high_idx]:
            score += 2
            reasons.append("Bearish RSI Divergence: Price making new highs but RSI showing exhaustion")
            
    elif trend_direction == Signal.BEARISH:
        # Check for Bullish Divergence
        prev_data = df.iloc[-lookback-1:-1]
        recent_low_idx = prev_data['Low'].idxmin()
        
        if low.iloc[-1] < low.loc[recent_low_idx] and rsi.iloc[-1] > rsi.loc[recent_low_idx]:
            score += 2
            reasons.append("Bullish RSI Divergence: Price making new lows but RSI showing exhaustion")

    # 2. MACD Histogram Weakening (Weight: 1)
    macd_data = calculate_macd(close)
    hist = macd_data['hist']
    
    if trend_direction == Signal.BULLISH:
        # Histogram shrinking while price is rising/flat
        if hist.iloc[-1] < hist.iloc[-2] and hist.iloc[-2] < hist.iloc[-3] and close.iloc[-1] >= close.iloc[-5:].min():
            score += 1
            reasons.append("MACD Histogram Weakening: Upward momentum slowing")
    elif trend_direction == Signal.BEARISH:
        # Histogram rising while price is falling/flat
        if hist.iloc[-1] > hist.iloc[-2] and hist.iloc[-2] > hist.iloc[-3] and close.iloc[-1] <= close.iloc[-5:].max():
            score += 1
            reasons.append("MACD Histogram Weakening: Downward momentum fading")

    # 3. ATR Compression (Weight: 1)
    # Calculate TR manually to get a series for the moving average of ATR
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr_series = tr.rolling(14).mean()
    atr_avg = atr_series.rolling(20).mean().iloc[-1]
    
    if not np.isnan(atr_avg) and atr_series.iloc[-1] < atr_avg * 0.8:
        score += 1
        reasons.append(f"ATR Compression: Volatility is {((1 - atr_series.iloc[-1]/atr_avg)*100):.1f}% below average, often precedes a pullback")

    # 4. Bollinger Band Re-entry (Weight: 1)
    bb = calculate_bollinger_bands(close)
    if trend_direction == Signal.BULLISH:
        # Previously touched/exceeded upper band and now closed inside
        if (high.iloc[-2] >= bb['upper'].iloc[-2] or high.iloc[-3] >= bb['upper'].iloc[-3]) and close.iloc[-1] < bb['upper'].iloc[-1]:
            score += 1
            reasons.append("Bollinger Band Re-entry: Price failed to sustain move outside upper band")
    elif trend_direction == Signal.BEARISH:
        # Previously touched/exceeded lower band and now closed inside
        if (low.iloc[-2] <= bb['lower'].iloc[-2] or low.iloc[-3] <= bb['lower'].iloc[-3]) and close.iloc[-1] > bb['lower'].iloc[-1]:
            score += 1
            reasons.append("Bollinger Band Re-entry: Price failed to sustain move outside lower band")

    # 5. Structure-Based Warning (Weight: 3)
    if trend_direction == Signal.BULLISH:
        # Failure to make new high + break of previous minor low
        last_high = high.iloc[-6:-1].max()
        if high.iloc[-1] < last_high:
            minor_low = low.iloc[-6:-1].min()
            if close.iloc[-1] < minor_low:
                score += 3
                reasons.append("Structure Break: Failed to make new high and broke previous minor low")
    elif trend_direction == Signal.BEARISH:
        # Failure to make new low + break of previous minor high
        last_low = low.iloc[-6:-1].min()
        if low.iloc[-1] > last_low:
            minor_high = high.iloc[-6:-1].max()
            if close.iloc[-1] > minor_high:
                score += 3
                reasons.append("Structure Break: Failed to make new low and broke previous minor high")

    is_warning = score >= 3
    
    if is_warning:
        description = f"🚨 PULLBACK WARNING (Score {score}/8): Exhaustion levels reached. Expect temporary correction."
    elif score > 0:
        description = f"Caution: Minor exhaustion signs detected (Score {score}/8)."
    else:
        description = "Momentum is healthy. No immediate pullback signals detected."

    return PullbackWarningAnalysis(
        warning_score=score,
        is_warning=is_warning,
        reasons=reasons,
        description=description
    )
