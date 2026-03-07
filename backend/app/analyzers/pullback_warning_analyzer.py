import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from ..models import PullbackWarningAnalysis, Signal
from .volatility_analyzer import calculate_atr
from domain.indicators.rsi import calculate_rsi_series
from domain.indicators.macd import calculate_macd as _domain_macd, is_histogram_weakening
from domain.indicators.bollinger import calculate_bollinger_series
from domain.indicators.atr import calculate_atr_series
from domain.constants import (
    WARNING_RSI_DIVERGENCE_WEIGHT, WARNING_MACD_WEAKENING_WEIGHT,
    WARNING_ATR_COMPRESSION_WEIGHT, WARNING_BB_REENTRY_WEIGHT,
    WARNING_STRUCTURE_BREAK_WEIGHT, WARNING_TRIGGER_SCORE,
    WARNING_LOOKBACK_BARS, INDICATOR_RSI_PERIOD,
    VOLATILITY_ATR_COMPRESSION_RATIO,
)


def _calculate_rsi_series(data: pd.Series, period: int = INDICATOR_RSI_PERIOD) -> pd.Series:
    """Return RSI as a pandas Series (domain layer returns ndarray)."""
    arr = calculate_rsi_series(data.tolist(), period=period)
    return pd.Series(arr, index=data.index).fillna(50)


def _calculate_macd_hist(data: pd.Series) -> pd.Series:
    """Return MACD histogram as a pandas Series via domain layer."""
    result = _domain_macd(data.tolist())
    # Build a simple series from the last two histogram values for scoring logic
    return result  # MACDResult dataclass


def _calculate_bollinger(data: pd.Series, period: int = 20, std_dev: int = 2) -> pd.DataFrame:
    """Return Bollinger Bands as a DataFrame via domain layer."""
    upper, middle, lower = calculate_bollinger_series(data.tolist(), period=period, std_dev=std_dev)
    return pd.DataFrame({'upper': upper, 'lower': lower, 'ma': middle}, index=data.index)

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
    
    # 1. RSI Divergence (Weight: WARNING_RSI_DIVERGENCE_WEIGHT)
    rsi = _calculate_rsi_series(close)
    lookback = WARNING_LOOKBACK_BARS

    if trend_direction == Signal.BULLISH:
        prev_data = df.iloc[-lookback-1:-1]
        recent_high_idx = prev_data['High'].idxmax()
        if high.iloc[-1] > high.loc[recent_high_idx] and rsi.iloc[-1] < rsi.loc[recent_high_idx]:
            score += WARNING_RSI_DIVERGENCE_WEIGHT
            reasons.append("Bearish RSI Divergence: Price making new highs but RSI showing exhaustion")
    elif trend_direction == Signal.BEARISH:
        prev_data = df.iloc[-lookback-1:-1]
        recent_low_idx = prev_data['Low'].idxmin()
        if low.iloc[-1] < low.loc[recent_low_idx] and rsi.iloc[-1] > rsi.loc[recent_low_idx]:
            score += WARNING_RSI_DIVERGENCE_WEIGHT
            reasons.append("Bullish RSI Divergence: Price making new lows but RSI showing exhaustion")

    # 2. MACD Histogram Weakening (Weight: WARNING_MACD_WEAKENING_WEIGHT)
    macd_result = _calculate_macd_hist(close)
    trend_is_bullish = (trend_direction == Signal.BULLISH)
    if is_histogram_weakening(macd_result, trend_is_bullish=trend_is_bullish):
        if trend_is_bullish and close.iloc[-1] >= close.iloc[-5:].min():
            score += WARNING_MACD_WEAKENING_WEIGHT
            reasons.append("MACD Histogram Weakening: Upward momentum slowing")
        elif not trend_is_bullish and close.iloc[-1] <= close.iloc[-5:].max():
            score += WARNING_MACD_WEAKENING_WEIGHT
            reasons.append("MACD Histogram Weakening: Downward momentum fading")

    # 3. ATR Compression (Weight: WARNING_ATR_COMPRESSION_WEIGHT)
    atr_arr = calculate_atr_series(high.tolist(), low.tolist(), close.tolist())
    atr_series_pd = pd.Series(atr_arr, index=close.index)
    atr_avg = atr_series_pd.rolling(20).mean().iloc[-1]
    if not np.isnan(atr_avg) and atr_series_pd.iloc[-1] < atr_avg * VOLATILITY_ATR_COMPRESSION_RATIO:
        score += WARNING_ATR_COMPRESSION_WEIGHT
        reasons.append(
            f"ATR Compression: Volatility is "
            f"{((1 - atr_series_pd.iloc[-1]/atr_avg)*100):.1f}% below average, often precedes a pullback"
        )

    # 4. Bollinger Band Re-entry (Weight: WARNING_BB_REENTRY_WEIGHT)
    bb = _calculate_bollinger(close)
    if trend_direction == Signal.BULLISH:
        if (high.iloc[-2] >= bb['upper'].iloc[-2] or high.iloc[-3] >= bb['upper'].iloc[-3]) and close.iloc[-1] < bb['upper'].iloc[-1]:
            score += WARNING_BB_REENTRY_WEIGHT
            reasons.append("Bollinger Band Re-entry: Price failed to sustain move outside upper band")
    elif trend_direction == Signal.BEARISH:
        if (low.iloc[-2] <= bb['lower'].iloc[-2] or low.iloc[-3] <= bb['lower'].iloc[-3]) and close.iloc[-1] > bb['lower'].iloc[-1]:
            score += WARNING_BB_REENTRY_WEIGHT
            reasons.append("Bollinger Band Re-entry: Price failed to sustain move outside lower band")

    # 5. Structure-Based Warning (Weight: WARNING_STRUCTURE_BREAK_WEIGHT)
    if trend_direction == Signal.BULLISH:
        last_high = high.iloc[-6:-1].max()
        if high.iloc[-1] < last_high:
            minor_low = low.iloc[-6:-1].min()
            if close.iloc[-1] < minor_low:
                score += WARNING_STRUCTURE_BREAK_WEIGHT
                reasons.append("Structure Break: Failed to make new high and broke previous minor low")
    elif trend_direction == Signal.BEARISH:
        last_low = low.iloc[-6:-1].min()
        if low.iloc[-1] > last_low:
            minor_high = high.iloc[-6:-1].max()
            if close.iloc[-1] > minor_high:
                score += WARNING_STRUCTURE_BREAK_WEIGHT
                reasons.append("Structure Break: Failed to make new low and broke previous minor high")

    is_warning = score >= WARNING_TRIGGER_SCORE
    
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
