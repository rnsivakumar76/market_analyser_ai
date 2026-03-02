import pandas as pd
import numpy as np
import logging
from typing import Optional, Dict, Any
from datetime import datetime, time as pytime
from ..models import Signal

logger = logging.getLogger(__name__)

def detect_opening_range(df_15m: pd.DataFrame) -> Dict[str, Any]:
    """
    Detects the 15-minute Opening Range (first candle of NY Session).
    NY Open is 9:30 AM EST (13:30 or 14:30 UTC depending on DST).
    For simplicity, we look for the highest volume/volatility spike in the morning.
    """
    if df_15m.empty:
        return {"high": 0.0, "low": 0.0, "broken": "none"}
    
    # Simple logic: Take the first candle of the most recent day in the data
    last_date = df_15m.index[-1].date()
    daily_data = df_15m[df_15m.index.date == last_date]
    
    if len(daily_data) < 1:
        return {"high": 0.0, "low": 0.0, "broken": "none"}
    
    # The 'Opening Range' is the high/low of the first 15m candle
    or_high = float(daily_data.iloc[0]['High'])
    or_low = float(daily_data.iloc[0]['Low'])
    
    current_price = float(df_15m.iloc[-1]['Close'])
    
    broken = "none"
    if current_price > or_high:
        broken = "bullish"
    elif current_price < or_low:
        broken = "bearish"
        
    return {
        "or_high": or_high,
        "or_low": or_low,
        "broken": broken
    }

def calculate_rvol(df: pd.DataFrame, lookback_days: int = 5) -> float:
    """
    Calculates Relative Volume (RVOL).
    Compares the volume of the current bar to the average volume of the SAME bar in previous days.
    This is much more accurate for day trading than a standard Volume MA.
    """
    if len(df) < 50:
        return 1.0
        
    current_time = df.index[-1].time()
    current_vol = df.iloc[-1]['Volume']
    
    # Find volume at this same time over the last few days
    historical_vols = []
    for i in range(1, lookback_days + 1):
        # Look back i days
        same_time_bars = df[df.index.time == current_time]
        if len(same_time_bars) > i:
            historical_vols.append(same_time_bars.iloc[-(i+1)]['Volume'])
            
    if not historical_vols:
        return 1.0
        
    avg_hist_vol = sum(historical_vols) / len(historical_vols)
    if avg_hist_vol == 0:
        return 1.0
        
    return round(float(current_vol / avg_hist_vol), 2)

def analyze_commodity_specifics(symbol: str, dxy_change: float, yield_change: float) -> str:
    """
    Expert nuances for Gold/Crude/BTC.
    """
    sym = symbol.upper()
    advice = ""
    
    if "XAU" in sym or "GOLD" in sym:
        if dxy_change > 0.2 and yield_change > 0.1:
            advice = "WARNING: DXY & Yields both rising. Gold longs are HIGH RISK (Bull Trap)."
        elif dxy_change < -0.2 and yield_change < -0.1:
            advice = "EXPERT: DXY & Yields collapsing. Gold 'God-Candle' potential. Focus on Longs."
            
    elif "WTI" in sym or "OIL" in sym:
        # Check if it's Wednesday (EIA Day)
        if datetime.now().weekday() == 2: # 2 is Wednesday
            advice = "EXPERT: EIA Inventory Day. Expect high-volatility flush at 10:30 AM EST."
            
    elif "BTC" in sym:
        if dxy_change > 0.3:
            advice = "BTC: DXY spike detected. Crypto liquidity might dry up. Tighten Stops."
            
    return advice

def generate_expert_trade_plan(
    symbol: str, 
    price: float, 
    or_data: Dict, 
    rvol: float, 
    technical: Any, 
    advice: str,
    signal_direction: str = "neutral"
) -> Dict[str, Any]:
    """
    Generates a concrete 'Battle Plan' for the day trader.
    """
    plan = []
    
    # 1. Opening Range Breakout (ORB) Strategy
    if or_data["broken"] == "bullish":
        plan.append(f"ORB BULLISH: Price held above {or_data['or_high']:.2f}. Trend is UP.")
    elif or_data["broken"] == "bearish":
        plan.append(f"ORB BEARISH: Price broke below {or_data['or_low']:.2f}. Trend is DOWN.")
    
    # 2. RVOL Confirmation
    if rvol > 2.0:
        plan.append(f"HIGH CONVICTION: RVOL is {rvol}x. Institutions are active.")
    
    # 3. Pivot Targets — contextualize ORB direction with overall signal direction
    if technical and technical.pivot_points:
        p = technical.pivot_points
        orb_direction = or_data.get("broken")
        is_bullish_signal = signal_direction == "bullish"
        is_bearish_signal = signal_direction == "bearish"

        if orb_direction == "bullish" and is_bearish_signal:
            # ORB up but signal is bearish — intraday bounce into resistance, fade opportunity
            plan.append(f"CAUTION: Bullish ORB against bearish signal. R1 ({p.r1:.2f}) is resistance to fade — watch for rejection.")
        elif orb_direction == "bearish" and is_bullish_signal:
            # ORB down but signal is bullish — price pulling back to entry zone, not a short signal
            plan.append(f"PULLBACK IN PROGRESS: Price heading to entry zone near S1 ({p.s1:.2f}). Watch for long reversal at support.")
        elif orb_direction == "bullish":
            plan.append(f"TARGETS: Aim for R1 ({p.r1:.2f}) then R2 ({p.r2:.2f}).")
        elif orb_direction == "bearish":
            plan.append(f"TARGETS: Aim for S1 ({p.s1:.2f}) then S2 ({p.s2:.2f}).")
        elif price > p.pivot:
            plan.append(f"TARGETS: Aim for R1 ({p.r1:.2f}) then R2 ({p.r2:.2f}).")
        else:
            plan.append(f"TARGETS: Aim for S1 ({p.s1:.2f}) then S2 ({p.s2:.2f}).")

        if technical.fibonacci and orb_direction == "bearish" and is_bullish_signal:
            plan.append(f"KEY ENTRY: Fib 38.2% at {technical.fibonacci.ret_382:.2f} is the ideal long trigger zone.")
            
    # 4. Expert Advice
    if advice:
        plan.append(advice)
        
    return {
        "battle_plan": " | ".join(plan) if plan else "Wait for Session Open/Clear Breakout.",
        "rvol": rvol,
        "is_high_intent": rvol > 1.8
    }
