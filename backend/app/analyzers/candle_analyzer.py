import pandas as pd
from typing import Dict, Any, Optional
from enum import Enum

class CandlePattern(str, Enum):
    BULLISH_ENGULFING = "bullish_engulfing"
    BEARISH_ENGULFING = "bearish_engulfing"
    HAMMER = "hammer"
    SHOOTING_STAR = "shooting_star"
    NONE = "none"

def detect_candle_patterns(df: pd.DataFrame) -> Dict[str, Any]:
    """Detect key candlestick patterns in the most recent candles."""
    if len(df) < 5:
        return {"pattern": CandlePattern.NONE, "description": "Insufficient data"}

    # Get last two candles
    body_0 = df.iloc[-1] # Current (or last closed)
    body_1 = df.iloc[-2] # Previous
    
    # helper properties
    def get_candle_stats(candle):
        open_p = candle['Open']
        close_p = candle['Close']
        high = candle['High']
        low = candle['Low']
        
        body_size = abs(close_p - open_p)
        is_bullish = close_p > open_p
        upper_wick = high - max(open_p, close_p)
        lower_wick = min(open_p, close_p) - low
        total_range = high - low
        return open_p, close_p, high, low, body_size, is_bullish, upper_wick, lower_wick, total_range

    o0, c0, h0, l0, size0, bull0, uw0, lw0, range0 = get_candle_stats(body_0)
    o1, c1, h1, l1, size1, bull1, uw1, lw1, range1 = get_candle_stats(body_1)

    # 1. Bullish Engulfing
    # Previous was bearish, Current is bullish and wraps around previous body
    if not bull1 and bull0 and c0 > o1 and o0 < c1:
        return {
            "pattern": CandlePattern.BULLISH_ENGULFING, 
            "description": "Bullish Engulfing: Buyers completely overwhelmed sellers.",
            "is_bullish": True
        }

    # 2. Bearish Engulfing
    if bull1 and not bull0 and c0 < o1 and o0 > c1:
        return {
            "pattern": CandlePattern.BEARISH_ENGULFING, 
            "description": "Bearish Engulfing: Sellers completely overwhelmed buyers.",
            "is_bullish": False
        }

    # 3. Hammer (Potential Reversal at Bottom)
    # Small body at top of range, long lower wick (at least 2x body)
    if range0 > 0 and lw0 > (size0 * 2) and uw0 < (size0 * 0.5):
        return {
            "pattern": CandlePattern.HAMMER, 
            "description": "Hammer: Long lower wick shows price rejection at lows.",
            "is_bullish": True
        }
        
    # 4. Shooting Star (Potential Reversal at Top)
    if range0 > 0 and uw0 > (size0 * 2) and lw0 < (size0 * 0.5):
        return {
            "pattern": CandlePattern.SHOOTING_STAR, 
            "description": "Shooting Star: Buyers rejected at highs.",
            "is_bullish": False
        }

    return {"pattern": CandlePattern.NONE, "description": "No significant reversal pattern", "is_bullish": None}
