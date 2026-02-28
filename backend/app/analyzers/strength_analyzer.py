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
    """Calculate current volume relative to moving average.
    Returns 0.0 for Forex/commodity pairs that have no real volume data."""
    current_volume = float(volume.iloc[-1])
    
    # If current volume is zero, this is a no-volume instrument (XAU, XAG, indices)
    if current_volume == 0:
        return 0.0
    
    volume_ma = volume.rolling(window=ma_period).mean()
    avg_volume = float(volume_ma.iloc[-1])
    
    if avg_volume == 0:
        return 0.0
    
    return round(current_volume / avg_volume, 2)


def calculate_vwap(data: pd.DataFrame, period: int = 20) -> tuple[float, float]:
    """
    Calculate Volume Weighted Average Price (VWAP).
    Returns (vwap_value, distance_pct).
    """
    if 'Volume' not in data.columns or (data['Volume'] == 0).all():
        return 0.0, 0.0
    
    recent = data.tail(period).copy()
    typical_price = (recent['High'] + recent['Low'] + recent['Close']) / 3
    tp_v = typical_price * recent['Volume']
    
    total_tp_v = tp_v.sum()
    total_vol = recent['Volume'].sum()
    
    if total_vol == 0:
        return 0.0, 0.0
    
    vwap = total_tp_v / total_vol
    current_price = float(data['Close'].iloc[-1])
    dist_pct = ((current_price - vwap) / vwap) * 100
    
    return float(vwap), float(dist_pct)


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
    vwap, vwap_dist = calculate_vwap(daily_data)
    
    # Calculate daily price change
    if len(close_prices) >= 2:
        price_change = float((close_prices.iloc[-1] - close_prices.iloc[-2]) / close_prices.iloc[-2] * 100)
    else:
        price_change = 0.0
    
    # Determine signal
    bullish_signals = 0
    bearish_signals = 0
    reasons = []
    
    # VWAP analysis
    if vwap > 0:
        if vwap_dist > 1.5:
            bearish_signals += 1
            reasons.append(f"Price overextended from VWAP (+{vwap_dist:.1f}%)")
        elif vwap_dist < -1.5:
            bullish_signals += 1
            reasons.append(f"Price at discount to VWAP ({vwap_dist:.1f}%)")
    
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
        rsi=float(round(rsi, 2)),
        volume_ratio=float(round(volume_ratio, 2)),
        adx=float(round(adx, 2)),
        vwap=float(round(vwap, 2)) if vwap > 0 else None,
        vwap_dist_pct=float(round(vwap_dist, 2)) if vwap > 0 else None,
        price_change_percent=float(round(price_change, 2)),
        description=description
    )
