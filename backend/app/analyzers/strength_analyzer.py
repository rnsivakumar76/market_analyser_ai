import pandas as pd
import numpy as np
from typing import Dict, Any
from ..models import StrengthAnalysis, Signal


def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    """Calculate Relative Strength Index."""
    delta = prices.diff()
    
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0


def calculate_volume_ratio(volume: pd.Series, ma_period: int = 20) -> float:
    """Calculate current volume relative to moving average."""
    volume_ma = volume.rolling(window=ma_period).mean()
    current_volume = float(volume.iloc[-1])
    avg_volume = float(volume_ma.iloc[-1])
    
    if avg_volume == 0:
        return 1.0
    
    return current_volume / avg_volume


def calculate_adx(data: pd.DataFrame, period: int = 14) -> float:
    """
    Calculate Average Directional Index (ADX).
    ADX measures the strength of the trend (not direction).
    ADX > 25 = Strong trend
    ADX < 20 = Weak trend / Sideways
    """
    high = data['High']
    low = data['Low']
    close = data['Close']
    
    # Calculate True Range (TR)
    t1 = high - low
    t2 = abs(high - close.shift(1))
    t3 = abs(low - close.shift(1))
    tr = pd.concat([t1, t2, t3], axis=1).max(axis=1)
    
    # Directional Movement
    plus_dm = high.diff()
    minus_dm = low.diff().apply(lambda x: -x)
    
    # Filter DM
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    plus_dm = plus_dm.where(plus_dm > minus_dm, 0)
    minus_dm = minus_dm.where(minus_dm > plus_dm, 0)
    
    # Smoothing (Wilder's method)
    tr_smoothed = tr.rolling(window=period).mean() # Simple mean for TR smoothing
    plus_dm_smoothed = plus_dm.rolling(window=period).mean()
    minus_dm_smoothed = minus_dm.rolling(window=period).mean()
    
    # Directional Indicators
    plus_di = 100 * (plus_dm_smoothed / tr_smoothed)
    minus_di = 100 * (minus_dm_smoothed / tr_smoothed)
    
    # Directional Index (DX)
    dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))
    
    # Moving average of DX gives ADX
    adx = dx.rolling(window=period).mean()
    
    return float(adx.iloc[-1]) if not pd.isna(adx.iloc[-1]) else 0.0


def analyze_daily_strength(
    daily_data: pd.DataFrame,
    params: Dict[str, Any]
) -> StrengthAnalysis:
    """
    Analyze daily strength indicators.
    
    Considers:
    1. RSI - momentum indicator
    2. Volume - confirmation of moves
    3. Recent price change
    """
    rsi_period = params.get('rsi_period', 14)
    rsi_oversold = params.get('rsi_oversold', 30)
    rsi_overbought = params.get('rsi_overbought', 70)
    volume_ma_period = params.get('volume_ma_period', 20)
    volume_surge_threshold = params.get('volume_surge_threshold', 1.5)
    
    close_prices = daily_data['Close']
    volume = daily_data['Volume']
    
    # Calculate indicators
    rsi = calculate_rsi(close_prices, rsi_period)
    volume_ratio = calculate_volume_ratio(volume, volume_ma_period)
    adx = calculate_adx(daily_data, 14)
    
    # Calculate daily price change
    if len(close_prices) >= 2:
        price_change = (close_prices.iloc[-1] - close_prices.iloc[-2]) / close_prices.iloc[-2] * 100
    else:
        price_change = 0.0
    
    # Determine signal
    bullish_signals = 0
    bearish_signals = 0
    reasons = []
    
    # RSI analysis
    if rsi < rsi_oversold:
        bullish_signals += 1
        reasons.append(f"RSI oversold ({rsi:.1f})")
    elif rsi > rsi_overbought:
        bearish_signals += 1
        reasons.append(f"RSI overbought ({rsi:.1f})")
    
    # Volume analysis
    volume_surge = volume_ratio >= volume_surge_threshold
    if volume_surge:
        if price_change > 0:
            bullish_signals += 1
            reasons.append(f"Volume surge ({volume_ratio:.1f}x) on up day")
        elif price_change < 0:
            bearish_signals += 1
            reasons.append(f"Volume surge ({volume_ratio:.1f}x) on down day")
    
    # Price action
    if price_change > 1:
        bullish_signals += 1
        reasons.append(f"Strong up day (+{price_change:.1f}%)")
    elif price_change < -1:
        bearish_signals += 1
        reasons.append(f"Strong down day ({price_change:.1f}%)")
    
    # Determine overall signal
    if bullish_signals > bearish_signals:
        signal = Signal.BULLISH
        description = "Daily showing bullish strength"
    elif bearish_signals > bullish_signals:
        signal = Signal.BEARISH
        description = "Daily showing bearish weakness"
    else:
        signal = Signal.NEUTRAL
        description = "Daily showing neutral/mixed signals"
    
    if reasons:
        description += f": {', '.join(reasons)}"
    
    return StrengthAnalysis(
        signal=signal,
        rsi=round(rsi, 2),
        volume_ratio=round(volume_ratio, 2),
        adx=round(adx, 2),
        price_change_percent=round(price_change, 2),
        description=description
    )
