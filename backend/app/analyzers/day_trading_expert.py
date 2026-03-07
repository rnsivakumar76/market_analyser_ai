import pandas as pd
import numpy as np
import logging
from typing import Optional, Dict, Any
from datetime import datetime, time as pytime
from ..models import Signal
from domain.trading.rvol import calculate_rvol as _domain_rvol
from domain.trading.opening_range import detect_opening_range as _domain_orb
from domain.constants import RVOL_LOOKBACK_DAYS

logger = logging.getLogger(__name__)


def detect_opening_range(df_15m: pd.DataFrame) -> Dict[str, Any]:
    """
    Detects the 15-minute Opening Range (first candle of NY Session).
    Delegates to domain layer.
    """
    if df_15m.empty:
        return {"or_high": 0.0, "or_low": 0.0, "broken": "none"}

    last_date = df_15m.index[-1].date()
    daily_data = df_15m[df_15m.index.date == last_date]

    if len(daily_data) < 1:
        return {"or_high": 0.0, "or_low": 0.0, "broken": "none"}

    current_price = float(df_15m.iloc[-1]['Close'])
    orb = _domain_orb(
        session_highs=daily_data['High'].tolist(),
        session_lows=daily_data['Low'].tolist(),
        current_price=current_price,
        opening_bar_index=0,
    )
    return {"or_high": orb.or_high, "or_low": orb.or_low, "broken": orb.broken}


def calculate_rvol(df: pd.DataFrame, lookback_days: int = RVOL_LOOKBACK_DAYS) -> float:
    """
    Calculates Relative Volume (RVOL). Delegates to domain layer.
    """
    if len(df) < 50:
        return 1.0

    current_time = df.index[-1].time()
    current_vol = float(df.iloc[-1]['Volume'])

    same_time_bars = df[df.index.time == current_time]
    historical_vols = [
        float(same_time_bars.iloc[-(i + 1)]['Volume'])
        for i in range(1, lookback_days + 1)
        if len(same_time_bars) > i
    ]

    return _domain_rvol(current_vol, historical_vols)

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
    atr: float = 0.0,
    rsi: Optional[float] = None,
    adx: Optional[float] = None,
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

    # Derive session label from session_ctx fields (no 'session' field on SessionContext model)
    session_name = None
    if session_ctx:
        if getattr(session_ctx, 'london_open', None):
            session_name = "London"
        elif hasattr(session_ctx, 'description') and session_ctx.description:
            desc_lower = session_ctx.description.lower()
            if 'london' in desc_lower:
                session_name = "London"
            elif 'asia' in desc_lower or 'tokyo' in desc_lower:
                session_name = "Asia"
            elif 'new york' in desc_lower or 'ny' in desc_lower:
                session_name = "New York"

    # ── 1. SITUATION ──────────────────────────────────────────────────────────
    if orb_direction == "bullish":
        sit = f"SITUATION: ORB BULLISH — Price broke above OR High ({or_high:.2f}). Intraday bias is UP."
        if is_bearish:
            sit += " ⚠ Counter-trend bounce: daily signal is bearish — reduce size and tighten stops."
    elif orb_direction == "bearish":
        sit = f"SITUATION: ORB BEARISH — Price broke below OR Low ({or_low:.2f}). Intraday bias is DOWN."
        if is_bullish:
            sit += " ⚠ Pullback within larger uptrend — look for a long reversal at key support, not a new short."
    elif or_high and or_low and or_high != or_low:
        sit = (f"SITUATION: INSIDE RANGE — Price is consolidating between OR Low ({or_low:.2f}) "
               f"and OR High ({or_high:.2f}). No trade until a candle CLOSES outside the range.")
    else:
        sit = "SITUATION: WAITING FOR SETUP — Opening range not yet established (insufficient session data). Stand aside and observe price action."
    sections.append(sit)

    # ── 2. ENTRY ZONE ─────────────────────────────────────────────────────────
    if technical and technical.pivot_points:
        p   = technical.pivot_points
        fib = technical.fibonacci
        entry = None

        if orb_direction == "bullish" and not is_bearish:
            fib_note = f" or Fib 38.2% pullback ({fib.ret_382:.2f})" if fib and fib.ret_382 else ""
            entry = (f"ENTRY: Wait for a pullback to S1 ({p.s1:.2f}){fib_note}. "
                     f"Enter on a 15m bullish close — do NOT chase the initial breakout.")
        elif orb_direction == "bearish" and is_bullish:
            fib_note = f" or Fib 38.2% ({fib.ret_382:.2f})" if fib and fib.ret_382 else ""
            entry = (f"ENTRY: Watch S1 ({p.s1:.2f}){fib_note} for a reversal trigger. "
                     f"Look for a hammer / bullish engulfing candle on the 15m before entering long.")
        elif orb_direction == "bearish" and not is_bullish:
            fib_note = f" or Fib 61.8% bounce ({fib.ret_618:.2f})" if fib and fib.ret_618 else ""
            entry = (f"ENTRY: On a dead-cat bounce to R1 ({p.r1:.2f}){fib_note}. "
                     f"Wait for a 15m bearish close confirming rejection before entering short.")
        elif orb_direction == "none" and is_bullish and price < p.pivot:
            fib_note = f" and Fib 38.2% ({fib.ret_382:.2f})" if fib and fib.ret_382 else ""
            entry = (f"ENTRY: Watching S1 ({p.s1:.2f}){fib_note}. "
                     f"Need a 15m close above Pivot ({p.pivot:.2f}) to confirm bullish momentum before committing.")
        elif orb_direction == "bullish" and is_bearish:
            fib_note = f" or Fib 61.8% ({fib.ret_618:.2f})" if fib and fib.ret_618 else ""
            entry = (f"ENTRY (Fade): Wait for a 15m close below Pivot ({p.pivot:.2f}){fib_note} "
                     f"to enter short toward S1 ({p.s1:.2f}). High-risk counter-trend play — small size only.")

        if entry:
            sections.append(entry)

    # ── 3. TARGETS ────────────────────────────────────────────────────────────
    # Signal direction (daily) takes priority over ORB direction when they conflict.
    # A bearish ORB on a bullish daily signal = pullback entry → long targets.
    if technical and technical.pivot_points:
        p = technical.pivot_points
        long_targets = is_bullish or (not is_bearish and orb_direction == "bullish")
        short_targets = is_bearish or (not is_bullish and orb_direction == "bearish")
        if long_targets:
            sections.append(
                f"TARGETS: T1 → R1 ({p.r1:.2f}) — book 50% profit and move stop to breakeven. "
                f"T2 → R2 ({p.r2:.2f}) — trail stop on the remainder."
            )
        elif short_targets:
            sections.append(
                f"TARGETS: T1 → S1 ({p.s1:.2f}) — book 50% profit and move stop to breakeven. "
                f"T2 → S2 ({p.s2:.2f}) — trail stop on the remainder."
            )

    # ── 4. STOP / INVALIDATION ────────────────────────────────────────────────
    # Same priority logic: daily signal determines which side the stop goes.
    if technical and technical.pivot_points:
        p = technical.pivot_points
        atr_note = f" ({atr:.2f} ATR buffer)" if atr and atr > 0 else ""
        long_stop = is_bullish or (not is_bearish and orb_direction == "bullish")
        short_stop = is_bearish or (not is_bullish and orb_direction == "bearish")
        valid_range = or_high and or_low and or_high != or_low
        if long_stop:
            stop_ref = or_low if valid_range else p.s1
            inv_note = f"OR Low ({or_low:.2f})" if valid_range else f"S1 ({p.s1:.2f})"
            sections.append(
                f"STOP: Hard stop below {stop_ref:.2f}{atr_note}. "
                f"Plan is INVALIDATED on a 15m candle close below {inv_note}."
            )
        elif short_stop:
            stop_ref = or_high if valid_range else p.r1
            inv_note = f"OR High ({or_high:.2f})" if valid_range else f"R1 ({p.r1:.2f})"
            sections.append(
                f"STOP: Hard stop above {stop_ref:.2f}{atr_note}. "
                f"Plan is INVALIDATED on a 15m candle close above {inv_note}."
            )

    # ── 5. CONVICTION ─────────────────────────────────────────────────────────
    conv = []
    if rvol >= 2.0:
        conv.append(f"RVOL {rvol}x (high — institutions active)")
    elif rvol >= 1.5:
        conv.append(f"RVOL {rvol}x (moderate — watch for volume surge)")
    else:
        conv.append(f"RVOL {rvol}x (light — wait for volume before full size)")

    if adx is not None and adx > 0:
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
