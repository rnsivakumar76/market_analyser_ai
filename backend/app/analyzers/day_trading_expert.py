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
    signal_direction: str = "neutral",
    strength: Any = None,
    session_ctx: Any = None,
) -> Dict[str, Any]:
    """
    Generates a rich multi-line 'Battle Plan' for the day trader.
    Covers: SITUATION → ENTRY → TARGETS → STOP/INVALIDATION → CONVICTION → CONTEXT
    """
    sections = []

    orb_direction = or_data.get("broken", "none")
    or_high = or_data.get("or_high", 0.0)
    or_low  = or_data.get("or_low",  0.0)
    is_bullish = signal_direction == "bullish"
    is_bearish = signal_direction == "bearish"

    # Pull in richer context from daily_strength
    atr = getattr(strength, 'atr', None) if strength else None
    rsi = getattr(strength, 'rsi', None) if strength else None
    adx = getattr(strength, 'adx', None) if strength else None
    session_name = None
    if session_ctx:
        session_name = getattr(session_ctx, 'session', None) or getattr(session_ctx, 'session_name', None)

    # ── 1. SITUATION ──────────────────────────────────────────────────────────
    if orb_direction == "bullish":
        sit = f"SITUATION: ORB BULLISH — Price broke above OR High ({or_high:.2f}). Intraday bias is UP."
        if is_bearish:
            sit += " ⚠ Counter-trend bounce: daily signal is bearish — reduce size and tighten stops."
    elif orb_direction == "bearish":
        sit = f"SITUATION: ORB BEARISH — Price broke below OR Low ({or_low:.2f}). Intraday bias is DOWN."
        if is_bullish:
            sit += " ⚠ Pullback within larger uptrend — look for a long reversal at key support, not a new short."
    elif or_high and or_low:
        sit = (f"SITUATION: INSIDE RANGE — Price is consolidating between OR Low ({or_low:.2f}) "
               f"and OR High ({or_high:.2f}). No trade until a candle CLOSES outside the range.")
    else:
        sit = "SITUATION: WAITING FOR SETUP — No confirmed opening range yet. Stand aside and observe price action."
    sections.append(sit)

    # ── 2. ENTRY ZONE ─────────────────────────────────────────────────────────
    if technical and technical.pivot_points:
        p   = technical.pivot_points
        fib = technical.fibonacci
        entry = None

        if orb_direction == "bullish" and not is_bearish:
            fib_note = f" or Fib 23.6% ({fib.ret_236:.2f})" if fib and fib.ret_236 else ""
            entry = (f"ENTRY: Wait for a pullback to S1 ({p.s1:.2f}){fib_note}. "
                     f"Enter on a 15m bullish close — do NOT chase the initial breakout.")
        elif orb_direction == "bearish" and is_bullish:
            fib_note = f" or Fib 38.2% ({fib.ret_382:.2f})" if fib and fib.ret_382 else ""
            entry = (f"ENTRY: Watch S1 ({p.s1:.2f}){fib_note} for a reversal trigger. "
                     f"Look for a hammer / bullish engulfing candle on the 15m before entering long.")
        elif orb_direction == "bearish" and not is_bullish:
            fib_note = f" or Fib 23.6% ({fib.ret_236:.2f})" if fib and fib.ret_236 else ""
            entry = (f"ENTRY: On a dead-cat bounce to R1 ({p.r1:.2f}){fib_note}. "
                     f"Wait for a 15m bearish close confirming rejection before entering short.")
        elif orb_direction == "none" and is_bullish and price < p.pivot:
            fib_note = f" and Fib 38.2% ({fib.ret_382:.2f})" if fib and fib.ret_382 else ""
            entry = (f"ENTRY: Watching S1 ({p.s1:.2f}){fib_note}. "
                     f"Need a 15m close above Pivot ({p.pivot:.2f}) to confirm bullish momentum before committing.")
        elif orb_direction == "bullish" and is_bearish:
            entry = (f"ENTRY (Fade): Wait for a 15m close below Pivot ({p.pivot:.2f}) "
                     f"to enter short toward S1 ({p.s1:.2f}). High-risk counter-trend play — small size only.")

        if entry:
            sections.append(entry)

    # ── 3. TARGETS ────────────────────────────────────────────────────────────
    if technical and technical.pivot_points:
        p = technical.pivot_points
        if orb_direction == "bullish" or (orb_direction != "bearish" and is_bullish):
            sections.append(
                f"TARGETS: T1 → R1 ({p.r1:.2f}) — book 50% profit and move stop to breakeven. "
                f"T2 → R2 ({p.r2:.2f}) — trail stop on the remainder."
            )
        elif orb_direction == "bearish" or is_bearish:
            sections.append(
                f"TARGETS: T1 → S1 ({p.s1:.2f}) — book 50% profit and move stop to breakeven. "
                f"T2 → S2 ({p.s2:.2f}) — trail stop on the remainder."
            )

    # ── 4. STOP / INVALIDATION ────────────────────────────────────────────────
    if technical and technical.pivot_points:
        p = technical.pivot_points
        atr_note = f" ({atr:.2f} ATR buffer)" if atr else ""
        if orb_direction == "bullish" or (orb_direction != "bearish" and is_bullish):
            stop_ref = or_low if or_low else p.s1
            sections.append(
                f"STOP: Hard stop below {stop_ref:.2f}{atr_note}. "
                f"Plan is INVALIDATED on a 15m candle close below OR Low ({or_low:.2f})."
            )
        elif orb_direction == "bearish" or is_bearish:
            stop_ref = or_high if or_high else p.r1
            sections.append(
                f"STOP: Hard stop above {stop_ref:.2f}{atr_note}. "
                f"Plan is INVALIDATED on a 15m candle close above OR High ({or_high:.2f})."
            )

    # ── 5. CONVICTION ─────────────────────────────────────────────────────────
    conv = []
    if rvol >= 2.0:
        conv.append(f"RVOL {rvol}x (high — institutions active)")
    elif rvol >= 1.5:
        conv.append(f"RVOL {rvol}x (moderate — watch for volume surge)")
    else:
        conv.append(f"RVOL {rvol}x (light — wait for volume before full size)")

    if adx is not None:
        if adx >= 30:
            conv.append(f"ADX {adx:.0f} (strong trend, trend-following favoured)")
        elif adx >= 20:
            conv.append(f"ADX {adx:.0f} (developing trend, avoid fading)")
        else:
            conv.append(f"ADX {adx:.0f} (weak trend, wait for breakout confirmation)")

    if rsi is not None:
        if rsi >= 70:
            conv.append(f"RSI {rsi:.0f} — overbought, reduce long size")
        elif rsi <= 30:
            conv.append(f"RSI {rsi:.0f} — oversold, bounce conditions present")
        elif rsi >= 55:
            conv.append(f"RSI {rsi:.0f} — bullish momentum")
        elif rsi <= 45:
            conv.append(f"RSI {rsi:.0f} — bearish momentum")

    if session_name:
        conv.append(f"{session_name} session active")

    if conv:
        sections.append("CONVICTION: " + "  ·  ".join(conv))

    # ── 6. COMMODITY CONTEXT ──────────────────────────────────────────────────
    if advice:
        sections.append(f"CONTEXT: {advice}")

    battle_plan_text = "\n".join(sections) if sections else "Wait for Session Open / Clear Breakout."

    return {
        "battle_plan": battle_plan_text,
        "rvol": rvol,
        "is_high_intent": rvol > 1.8,
        "or_high": or_data.get("or_high", 0.0),
        "or_low":  or_data.get("or_low",  0.0),
        "or_broken": or_data.get("broken", "none"),
    }
