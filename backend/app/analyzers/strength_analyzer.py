import pandas as pd
import numpy as np
from typing import Dict, Any
from ..models import StrengthAnalysis, Signal
from domain.indicators.rsi import calculate_rsi as _domain_rsi
from domain.indicators.adx import calculate_adx as _domain_adx
from domain.indicators.vwap import calculate_vwap as _domain_vwap, calculate_vwap_distance_pct
from domain.constants import INDICATOR_RSI_PERIOD, INDICATOR_ADX_PERIOD, INDICATOR_VWAP_PERIOD


def calculate_rsi(prices: pd.Series, period: int = INDICATOR_RSI_PERIOD) -> float:
    """Calculate Relative Strength Index. Delegates to domain layer."""
    return _domain_rsi(prices.tolist(), period=period)


def calculate_volume_ratio(volume: pd.Series, ma_period: int = 20) -> float:
    """Calculate current volume relative to moving average.
    Returns 0.0 for Forex/commodity pairs that have no real volume data."""
    current_volume = float(volume.iloc[-1])
    
    if current_volume == 0:
        return 0.0
    
    volume_ma = volume.rolling(window=ma_period).mean()
    avg_volume = float(volume_ma.iloc[-1])
    
    if avg_volume == 0:
        return 0.0
    
    return round(current_volume / avg_volume, 2)


def calculate_vwap(data: pd.DataFrame, period: int = INDICATOR_VWAP_PERIOD) -> tuple[float, float]:
    """
    Calculate Volume Weighted Average Price (VWAP).
    Returns (vwap_value, distance_pct). Delegates to domain layer.
    """
    if 'Volume' not in data.columns or (data['Volume'] == 0).all():
        return 0.0, 0.0
    
    vwap = _domain_vwap(
        data['High'].tolist(),
        data['Low'].tolist(),
        data['Close'].tolist(),
        data['Volume'].tolist(),
        period=period,
    )
    if vwap == 0.0:
        return 0.0, 0.0
    current_price = float(data['Close'].iloc[-1])
    dist_pct = calculate_vwap_distance_pct(current_price, vwap)
    return vwap, dist_pct


def calculate_adx(data: pd.DataFrame, period: int = INDICATOR_ADX_PERIOD) -> float:
    """
    Calculate Average Directional Index (ADX). Delegates to domain layer.
    ADX > 25 = Strong trend,  ADX < 20 = Weak trend / Sideways
    """
    return _domain_adx(
        data['High'].tolist(),
        data['Low'].tolist(),
        data['Close'].tolist(),
        period=period,
    )


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
