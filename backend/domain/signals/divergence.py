"""
Divergence Detection Calculations (Domain Layer)
────────────────────────────────────────────────
Pure mathematical functions for detecting divergences in price and indicators.
No I/O, no pandas, no framework dependencies.
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class DivergencePoint:
    """Represents a detected divergence point."""
    index: int
    price: float
    indicator_value: float
    divergence_type: str  # 'bullish' or 'bearish'
    strength: float  # 0-1, higher = stronger divergence


def detect_rsi_divergence(prices: List[float], rsi_values: List[float], 
                          lookback: int = 20) -> List[DivergencePoint]:
    """
    Detect RSI divergences between price and RSI.
    
    Bullish divergence: Price makes lower low, RSI makes higher low
    Bearish divergence: Price makes higher high, RSI makes lower high
    
    Args:
        prices: List of closing prices
        rsi_values: List of RSI values (same length as prices)
        lookback: Number of periods to look back for pivot points
        
    Returns:
        List of DivergencePoint objects
    """
    if len(prices) < lookback * 2 or len(rsi_values) != len(prices):
        return []
    
    divergences = []
    
    # Find local lows and highs
    for i in range(lookback, len(prices) - lookback):
        # Check for local low (potential bullish divergence)
        if _is_local_low(prices, i, lookback):
            # Compare with previous low
            prev_low_idx = _find_previous_low(prices, i, lookback)
            if prev_low_idx is not None:
                price_lower = prices[i] < prices[prev_low_idx]
                rsi_higher = rsi_values[i] > rsi_values[prev_low_idx]
                
                if price_lower and rsi_higher:
                    strength = _calculate_divergence_strength(
                        prices[i], prices[prev_low_idx],
                        rsi_values[i], rsi_values[prev_low_idx]
                    )
                    divergences.append(DivergencePoint(
                        index=i,
                        price=prices[i],
                        indicator_value=rsi_values[i],
                        divergence_type='bullish',
                        strength=strength
                    ))
        
        # Check for local high (potential bearish divergence)
        if _is_local_high(prices, i, lookback):
            prev_high_idx = _find_previous_high(prices, i, lookback)
            if prev_high_idx is not None:
                price_higher = prices[i] > prices[prev_high_idx]
                rsi_lower = rsi_values[i] < rsi_values[prev_high_idx]
                
                if price_higher and rsi_lower:
                    strength = _calculate_divergence_strength(
                        prices[i], prices[prev_high_idx],
                        rsi_values[i], rsi_values[prev_high_idx]
                    )
                    divergences.append(DivergencePoint(
                        index=i,
                        price=prices[i],
                        indicator_value=rsi_values[i],
                        divergence_type='bearish',
                        strength=strength
                    ))
    
    return divergences


def detect_macd_divergence(prices: List[float], macd_histogram: List[float],
                           lookback: int = 20) -> List[DivergencePoint]:
    """
    Detect MACD histogram divergences.
    
    Bullish: Price lower low, histogram higher low (less negative)
    Bearish: Price higher high, histogram lower high (less positive)
    """
    if len(prices) < lookback * 2 or len(macd_histogram) != len(prices):
        return []
    
    divergences = []
    
    for i in range(lookback, len(prices) - lookback):
        if _is_local_low(prices, i, lookback):
            prev_low_idx = _find_previous_low(prices, i, lookback)
            if prev_low_idx is not None:
                price_lower = prices[i] < prices[prev_low_idx]
                hist_higher = macd_histogram[i] > macd_histogram[prev_low_idx]
                
                if price_lower and hist_higher:
                    strength = _calculate_divergence_strength(
                        prices[i], prices[prev_low_idx],
                        macd_histogram[i], macd_histogram[prev_low_idx]
                    )
                    divergences.append(DivergencePoint(
                        index=i,
                        price=prices[i],
                        indicator_value=macd_histogram[i],
                        divergence_type='bullish',
                        strength=strength
                    ))
        
        if _is_local_high(prices, i, lookback):
            prev_high_idx = _find_previous_high(prices, i, lookback)
            if prev_high_idx is not None:
                price_higher = prices[i] > prices[prev_high_idx]
                hist_lower = macd_histogram[i] < macd_histogram[prev_high_idx]
                
                if price_higher and hist_lower:
                    strength = _calculate_divergence_strength(
                        prices[i], prices[prev_high_idx],
                        macd_histogram[i], macd_histogram[prev_high_idx]
                    )
                    divergences.append(DivergencePoint(
                        index=i,
                        price=prices[i],
                        indicator_value=macd_histogram[i],
                        divergence_type='bearish',
                        strength=strength
                    ))
    
    return divergences


def detect_price_ma_divergence(prices: List[float], ma_values: List[float],
                                lookback: int = 20) -> List[DivergencePoint]:
    """
    Detect price vs moving average divergences.
    
    Bullish: Price pulls away below MA but starts converging
    Bearish: Price pulls away above MA but starts converging
    """
    if len(prices) < lookback * 2 or len(ma_values) != len(prices):
        return []
    
    divergences = []
    
    for i in range(lookback, len(prices) - lookback):
        # Calculate spread between price and MA
        current_spread = prices[i] - ma_values[i]
        prev_spread = prices[i - lookback] - ma_values[i - lookback]
        
        # Price was far below MA, now converging (bullish)
        if current_spread < 0 and prev_spread < current_spread:
            # Check if this is a local low in price
            if _is_local_low(prices, i, lookback):
                strength = min(1.0, abs(current_spread - prev_spread) / abs(prev_spread))
                divergences.append(DivergencePoint(
                    index=i,
                    price=prices[i],
                    indicator_value=ma_values[i],
                    divergence_type='bullish',
                    strength=strength
                ))
        
        # Price was far above MA, now converging (bearish)
        if current_spread > 0 and prev_spread > current_spread:
            if _is_local_high(prices, i, lookback):
                strength = min(1.0, abs(current_spread - prev_spread) / abs(prev_spread))
                divergences.append(DivergencePoint(
                    index=i,
                    price=prices[i],
                    indicator_value=ma_values[i],
                    divergence_type='bearish',
                    strength=strength
                ))
    
    return divergences


# ──────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────────────────────────────────────

def _is_local_low(values: List[float], index: int, lookback: int) -> bool:
    """Check if value at index is a local minimum."""
    if index < lookback or index >= len(values) - lookback:
        return False
    return values[index] == min(values[index - lookback:index + lookback + 1])


def _is_local_high(values: List[float], index: int, lookback: int) -> bool:
    """Check if value at index is a local maximum."""
    if index < lookback or index >= len(values) - lookback:
        return False
    return values[index] == max(values[index - lookback:index + lookback + 1])


def _find_previous_low(values: List[float], current_idx: int, 
                       lookback: int) -> Optional[int]:
    """Find the previous local low before current index."""
    for i in range(current_idx - lookback - 1, lookback, -1):
        if _is_local_low(values, i, lookback):
            return i
    return None


def _find_previous_high(values: List[float], current_idx: int,
                        lookback: int) -> Optional[int]:
    """Find the previous local high before current index."""
    for i in range(current_idx - lookback - 1, lookback, -1):
        if _is_local_high(values, i, lookback):
            return i
    return None


def _calculate_divergence_strength(price_current: float, price_prev: float,
                                   indicator_current: float, indicator_prev: float) -> float:
    """
    Calculate divergence strength (0-1).
    Higher values indicate stronger divergence.
    """
    price_change_pct = abs(price_current - price_prev) / price_prev
    indicator_change_pct = abs(indicator_current - indicator_prev) / abs(indicator_prev) if indicator_prev != 0 else 0
    
    # Strength increases with larger price moves and opposing indicator moves
    combined = price_change_pct + indicator_change_pct
    return min(1.0, combined * 2)  # Scale to 0-1 range
