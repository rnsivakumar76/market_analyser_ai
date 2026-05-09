import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional
from ..models import TechnicalAnalysis, PivotPoints, Signal, FibonacciLevels, SessionContext
from .strength_analyzer import calculate_rsi
from domain.levels.pivot_points import calculate_pivot_points as _domain_pivots
from domain.levels.fibonacci import calculate_fibonacci_levels as _domain_fib
from domain.levels.std_bands import calculate_std_dev_bands as _domain_std_bands
from domain.levels.breakout import detect_donchian_breakout as _domain_breakout
from domain.levels.linear_regression import calculate_linear_regression_slope, classify_slope
from domain.indicators.rsi import detect_rsi_divergence as _domain_rsi_divergence
from domain.constants import INDICATOR_LRL_PERIOD, STDBAND_PERIOD


def calculate_pivot_points(df: pd.DataFrame) -> PivotPoints:
    """
    Calculate Standard Pivot Points using the previous day's data.
    Delegates to domain layer.
    """
    if len(df) < 2:
        zero = 0.0
        return PivotPoints(pivot=zero, r1=zero, r2=zero, r3=zero, s1=zero, s2=zero, s3=zero)
    
    prev_bar = df.iloc[-2]
    pv = _domain_pivots(
        float(prev_bar['High']),
        float(prev_bar['Low']),
        float(prev_bar['Close']),
    )
    return PivotPoints(
        pivot=pv.pivot, r1=pv.r1, r2=pv.r2, r3=pv.r3,
        s1=pv.s1, s2=pv.s2, s3=pv.s3,
    )

def analyze_least_resistance_line(df: pd.DataFrame) -> str:
    """
    Determine the 'Line of Least Resistance'. Delegates to domain layer.
    """
    if len(df) < INDICATOR_LRL_PERIOD:
        return "flat"
    slope = calculate_linear_regression_slope(df['Close'].tolist(), period=INDICATOR_LRL_PERIOD)
    return classify_slope(slope)

def detect_trend_breakout(df: pd.DataFrame) -> Tuple[str, float]:
    """
    Detect a Donchian Channel breakout. Delegates to domain layer.
    """
    if len(df) < 21:
        return "none", 0.0
    result = _domain_breakout(
        df['High'].tolist(),
        df['Low'].tolist(),
        df['Close'].tolist(),
        df['Volume'].tolist(),
    )
    return result.direction, result.confidence

def calculate_fibonacci_levels(df: pd.DataFrame) -> FibonacciLevels:
    """Calculate recent swing Fibonacci retracements and extensions. Delegates to domain layer."""
    if len(df) < 20:
        zero = 0.0
        return FibonacciLevels(trend="flat", swing_high=zero, swing_low=zero, ret_382=zero, ret_500=zero, ret_618=zero, ext_1272=zero, ext_1618=zero)
    
    from domain.constants import FIB_LOOKBACK_BARS
    recent = df.tail(FIB_LOOKBACK_BARS)
    swing_high = float(recent['High'].max())
    swing_low = float(recent['Low'].min())
    current = float(df['Close'].iloc[-1])
    
    fv = _domain_fib(swing_high, swing_low, current)
    return FibonacciLevels(
        trend=fv.trend,
        swing_high=fv.swing_high,
        swing_low=fv.swing_low,
        ret_382=fv.ret_382,
        ret_500=fv.ret_500,
        ret_618=fv.ret_618,
        ext_1272=fv.ext_1272,
        ext_1618=fv.ext_1618,
    )


def detect_rsi_divergence(df: pd.DataFrame, lookback: int = 20) -> Optional[str]:
    """
    Detect RSI divergence over the last `lookback` bars. Delegates to domain layer.
    Returns: 'bullish' | 'bearish' | None
    """
    if len(df) < lookback + 2:
        return None
    return _domain_rsi_divergence(
        df['Close'].tolist(),
        df['High'].tolist(),
        df['Low'].tolist(),
        lookback=lookback,
    )


def calculate_std_dev_bands(df: pd.DataFrame, period: int = STDBAND_PERIOD) -> tuple[float, float]:
    """Calculate 1 and 2 standard deviation levels from the period mean. Delegates to domain layer."""
    if len(df) < period:
        return 0.0, 0.0
    return _domain_std_bands(df['Close'].tolist(), period=period)


def analyze_session_context(df: pd.DataFrame) -> SessionContext:
    """Extract PDH, PDL and estimate London Open if intraday data available."""
    # Previous complete session (assuming daily bars for default)
    if len(df) < 2:
        return SessionContext(pdh=0.0, pdl=0.0, current_session_range_pct=0.0, description="N/A")
    
    prev_bar = df.iloc[-2]
    pdh = float(prev_bar['High'])
    pdl = float(prev_bar['Low'])
    
    current_high = float(df['Close'].max())
    current_low = float(df['Close'].min())
    session_range = ((current_high - current_low) / current_low * 100) if current_low > 0 else 0.0
    
    london_open = None
    # If the index is a DatetimeIndex and contains time (not just date)
    if isinstance(df.index, pd.DatetimeIndex) and df.index[0].hour != df.index[1].hour:
        # Simplistic: Find the first bar after 08:00 UTC
        london_bars = df[df.index.hour == 8]
        if not london_bars.empty:
            london_open = float(london_bars.iloc[0]['Open'])

    desc = f"Prev Day High: {pdh:.2f}, Low: {pdl:.2f}."
    if london_open:
        desc += f" London Open: {london_open:.2f}."

    return SessionContext(
        pdh=pdh,
        pdl=pdl,
        london_open=london_open,
        current_session_range_pct=float(round(session_range, 2)),
        description=desc
    )


def analyze_technical_indicators(df: pd.DataFrame) -> TechnicalAnalysis:
    """Main function to consolidate technical indicators."""
    pivots = calculate_pivot_points(df)
    fibs = calculate_fibonacci_levels(df)
    least_resistance = analyze_least_resistance_line(df)
    breakout_type, confidence = detect_trend_breakout(df)
    rsi_divergence = detect_rsi_divergence(df)
    std1, std2 = calculate_std_dev_bands(df)
    
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
        std_dev_1=float(round(std1, 2)),
        std_dev_2=float(round(std2, 2)),
        description=f"{pivot_desc}{resistance_desc}{breakout_desc}{divergence_desc}"
    )
