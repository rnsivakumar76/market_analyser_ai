"""
Swing Trade Reversal Analyzer (Analyzer Layer)
──────────────────────────────────────────────
Detects divergences and provides multi-timeframe confirmation for swing trades.
"""

from typing import List, Dict, Optional, Tuple
import pandas as pd
from dataclasses import dataclass


@dataclass
class DivergencePoint:
    """Represents a detected divergence point."""
    index: int
    price: float
    indicator_value: float
    divergence_type: str  # 'bullish' or 'bearish'
    strength: float  # 0-1, higher = stronger divergence


def _detect_rsi_divergence(prices: List[float], rsi_values: List[float], 
                          lookback: int = 20) -> List[DivergencePoint]:
    """Detect RSI divergences between price and RSI."""
    if len(prices) < lookback * 2 or len(rsi_values) != len(prices):
        return []
    
    divergences = []
    
    for i in range(lookback, len(prices) - lookback):
        # Check for local low (potential bullish divergence)
        if _is_local_low(prices, i, lookback):
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


def _detect_macd_divergence(prices: List[float], macd_histogram: List[float],
                           lookback: int = 20) -> List[DivergencePoint]:
    """Detect MACD histogram divergences."""
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


def _detect_price_ma_divergence(prices: List[float], ma_values: List[float],
                                lookback: int = 20) -> List[DivergencePoint]:
    """Detect price vs moving average divergences."""
    if len(prices) < lookback * 2 or len(ma_values) != len(prices):
        return []
    
    divergences = []
    
    for i in range(lookback, len(prices) - lookback):
        current_spread = prices[i] - ma_values[i]
        prev_spread = prices[i - lookback] - ma_values[i - lookback]
        
        if current_spread < 0 and prev_spread < current_spread:
            if _is_local_low(prices, i, lookback):
                strength = min(1.0, abs(current_spread - prev_spread) / abs(prev_spread))
                divergences.append(DivergencePoint(
                    index=i,
                    price=prices[i],
                    indicator_value=ma_values[i],
                    divergence_type='bullish',
                    strength=strength
                ))
        
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
    """Calculate divergence strength (0-1)."""
    price_change_pct = abs(price_current - price_prev) / price_prev
    indicator_change_pct = abs(indicator_current - indicator_prev) / abs(indicator_prev) if indicator_prev != 0 else 0
    combined = price_change_pct + indicator_change_pct
    return min(1.0, combined * 2)


def analyze_swing_reversal(
    symbol: str,
    df_daily: pd.DataFrame,
    df_4h: Optional[pd.DataFrame] = None,
    df_weekly: Optional[pd.DataFrame] = None
) -> Dict:
    """
    Analyze swing trade reversal opportunities using divergence detection.
    
    Args:
        symbol: Instrument symbol
        df_daily: Daily timeframe OHLCV data
        df_4h: 4-hour timeframe data (optional, for confirmation)
        df_weekly: Weekly timeframe data (optional, for major signals)
        
    Returns:
        Dictionary with reversal analysis results
    """
    if df_daily is None or len(df_daily) < 50:
        return {
            'symbol': symbol,
            'reversal_detected': False,
            'reason': 'Insufficient data'
        }
    
    # Calculate indicators for daily timeframe
    daily_prices = df_daily['Close'].tolist()
    daily_rsi = _calculate_rsi(df_daily['Close'], 14)
    daily_macd_hist = _calculate_macd_histogram(df_daily['Close'])
    daily_ma50 = df_daily['Close'].rolling(50).mean().tolist()
    
    # Detect divergences on daily
    rsi_divs = _detect_rsi_divergence(daily_prices, daily_rsi, lookback=20)
    macd_divs = _detect_macd_divergence(daily_prices, daily_macd_hist, lookback=20)
    ma_divs = _detect_price_ma_divergence(daily_prices, daily_ma50, lookback=20)
    
    # Get most recent divergences
    recent_rsi = rsi_divs[-1] if rsi_divs else None
    recent_macd = macd_divs[-1] if macd_divs else None
    recent_ma = ma_divs[-1] if ma_divs else None
    
    # Determine primary reversal signal
    primary_signal = _determine_primary_signal(recent_rsi, recent_macd, recent_ma)
    
    # Multi-timeframe confirmation
    mt_confirmed = False
    if df_4h is not None and len(df_4h) >= 50:
        mt_confirmed = _check_4h_confirmation(df_4h, primary_signal)
    
    weekly_signal = None
    if df_weekly is not None and len(df_weekly) >= 50:
        weekly_signal = _check_weekly_signal(df_weekly)
    
    # Position building strategy
    position_strategy = _generate_position_strategy(
        primary_signal, mt_confirmed, weekly_signal
    )
    
    return {
        'symbol': symbol,
        'reversal_detected': primary_signal is not None,
        'primary_signal': primary_signal,
        'divergences': {
            'rsi': _format_divergence(recent_rsi),
            'macd': _format_divergence(recent_macd),
            'ma': _format_divergence(recent_ma)
        },
        'multi_timeframe': {
            '4h_confirmed': mt_confirmed,
            'weekly_signal': weekly_signal
        },
        'position_strategy': position_strategy,
        'current_price': daily_prices[-1],
        'risk_level': _calculate_risk_level(primary_signal, mt_confirmed)
    }


def _calculate_rsi(prices: pd.Series, period: int = 14) -> List[float]:
    """Calculate RSI values."""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50).tolist()


def _calculate_macd_histogram(prices: pd.Series) -> List[float]:
    """Calculate MACD histogram values."""
    ema12 = prices.ewm(span=12).mean()
    ema26 = prices.ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    histogram = macd - signal
    return histogram.fillna(0).tolist()


def _determine_primary_signal(
    rsi_div: Optional[DivergencePoint],
    macd_div: Optional[DivergencePoint],
    ma_div: Optional[DivergencePoint]
) -> Optional[Dict]:
    """Determine the primary reversal signal from multiple divergences."""
    signals = []
    
    if rsi_div:
        signals.append({
            'type': rsi_div.divergence_type,
            'source': 'RSI',
            'strength': rsi_div.strength,
            'price': rsi_div.price
        })
    
    if macd_div:
        signals.append({
            'type': macd_div.divergence_type,
            'source': 'MACD',
            'strength': macd_div.strength,
            'price': macd_div.price
        })
    
    if ma_div:
        signals.append({
            'type': ma_div.divergence_type,
            'source': 'MA',
            'strength': ma_div.strength,
            'price': ma_div.price
        })
    
    if not signals:
        return None
    
    # Count bullish vs bearish signals
    bullish_count = sum(1 for s in signals if s['type'] == 'bullish')
    bearish_count = sum(1 for s in signals if s['type'] == 'bearish')
    
    # Average strength
    avg_strength = sum(s['strength'] for s in signals) / len(signals)
    
    # Determine primary direction
    if bullish_count > bearish_count:
        return {
            'direction': 'bullish',
            'confidence': min(1.0, avg_strength * (bullish_count / len(signals))),
            'sources': [s['source'] for s in signals if s['type'] == 'bullish']
        }
    elif bearish_count > bullish_count:
        return {
            'direction': 'bearish',
            'confidence': min(1.0, avg_strength * (bearish_count / len(signals))),
            'sources': [s['source'] for s in signals if s['type'] == 'bearish']
        }
    else:
        return None  # Conflicting signals


def _check_4h_confirmation(df_4h: pd.DataFrame, primary_signal: Optional[Dict]) -> bool:
    """Check if 4H timeframe confirms the primary signal."""
    if primary_signal is None:
        return False
    
    prices = df_4h['Close'].tolist()
    rsi = _calculate_rsi(df_4h['Close'], 14)
    
    # Check for recent divergence in same direction
    recent_divs = _detect_rsi_divergence(prices, rsi, lookback=10)
    
    if not recent_divs:
        return False
    
    latest_div = recent_divs[-1]
    return latest_div.divergence_type == primary_signal['direction']


def _check_weekly_signal(df_weekly: pd.DataFrame) -> Optional[Dict]:
    """Check for major weekly reversal signals."""
    prices = df_weekly['Close'].tolist()
    rsi = _calculate_rsi(df_weekly['Close'], 14)
    
    divs = _detect_rsi_divergence(prices, rsi, lookback=10)
    
    if divs:
        latest = divs[-1]
        return {
            'direction': latest.divergence_type,
            'strength': latest.strength,
            'is_major': True  # Weekly signals are major swing opportunities
        }
    
    return None


def _generate_position_strategy(
    primary_signal: Optional[Dict],
    mt_confirmed: bool,
    weekly_signal: Optional[Dict]
) -> Dict:
    """Generate position building recommendations."""
    if primary_signal is None:
        return {
            'action': 'WAIT',
            'reason': 'No reversal detected',
            'entries': []
        }
    
    direction = primary_signal['direction']
    confidence = primary_signal['confidence']
    
    # Base strategy
    if confidence < 0.5:
        action = 'WATCH'
        reason = 'Weak divergence, monitor for confirmation'
    elif mt_confirmed:
        action = 'BUILD_POSITION'
        reason = 'Multi-timeframe confirmed, start building position'
    elif weekly_signal and weekly_signal['direction'] == direction:
        action = 'AGGRESSIVE_BUILD'
        reason = 'Weekly confirmation - major swing opportunity'
    else:
        action = 'SMALL_ENTRY'
        reason = 'Daily divergence only, start with small position'
    
    # Generate entry points
    entries = []
    if action in ['BUILD_POSITION', 'AGGRESSIVE_BUILD', 'SMALL_ENTRY']:
        entries.append({
            'phase': 1,
            'size_percent': 25 if action == 'SMALL_ENTRY' else 33,
            'condition': 'Current divergence point',
            'timeframe': 'immediate'
        })
        
        if action in ['BUILD_POSITION', 'AGGRESSIVE_BUILD']:
            entries.append({
                'phase': 2,
                'size_percent': 33,
                'condition': 'Break of nearest structure',
                'timeframe': '1-3 days'
            })
            
            entries.append({
                'phase': 3,
                'size_percent': 34,
                'condition': 'Trend confirmation',
                'timeframe': '3-7 days'
            })
    
    return {
        'action': action,
        'direction': direction,
        'reason': reason,
        'entries': entries,
        'hold_duration': '2-4 weeks' if weekly_signal else '1-2 weeks'
    }


def _format_divergence(div: Optional[DivergencePoint]) -> Optional[Dict]:
    """Format divergence point for response."""
    if div is None:
        return None
    return {
        'type': div.divergence_type,
        'strength': round(div.strength, 2),
        'price': div.price
    }


def _calculate_risk_level(primary_signal: Optional[Dict], mt_confirmed: bool) -> str:
    """Calculate overall risk level."""
    if primary_signal is None:
        return 'LOW'
    
    if mt_confirmed:
        return 'MODERATE'
    
    if primary_signal['confidence'] > 0.7:
        return 'MODERATE'
    
    return 'HIGH'
