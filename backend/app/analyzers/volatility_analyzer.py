import pandas as pd
import numpy as np
from app.models import VolatilityAnalysis


def calculate_atr(data: pd.DataFrame, period: int = 14) -> float:
    """Calculate the Average True Range (ATR)."""
    if data is None or data.empty or len(data) < period + 1:
        return 0.0

    df = data.copy()
    
    # Calculate TR (True Range)
    df['Prev_Close'] = df['Close'].shift(1)
    df['High-Low'] = df['High'] - df['Low']
    df['High-PrevClose'] = abs(df['High'] - df['Prev_Close'])
    df['Low-PrevClose'] = abs(df['Low'] - df['Prev_Close'])
    
    # True Range is the maximum of the three values
    df['TR'] = df[['High-Low', 'High-PrevClose', 'Low-PrevClose']].max(axis=1)
    
    # Calculate ATR based on simple moving average of TR
    df['ATR'] = df['TR'].rolling(window=period).mean()
    
    # Get the latest ATR
    latest_atr = df['ATR'].iloc[-1]
    
    # Handle NaN
    if np.isnan(latest_atr):
        return 0.0
        
    return float(latest_atr)


def analyze_volatility_and_risk(
    data: pd.DataFrame, 
    current_price: float, 
    signal_direction: str,
    atr_multiplier_sl: float = 1.5,
    atr_multiplier_tp: float = 3.0
) -> VolatilityAnalysis:
    """Analyze volatility, calculate stop loss and take profit."""
    
    atr = calculate_atr(data, period=14)
    
    if atr == 0.0:
        return VolatilityAnalysis(
            atr=0.0,
            stop_loss=0.0,
            take_profit=0.0,
            risk_reward_ratio=0.0,
            description="Insufficient data for Volatility/ATR calculation."
        )

    # Calculate stop loss and take profit levels (Institutional Scaling Model)
    # TP1: 1.0x ATR (Initial de-risk)
    # TP2: 2.0x ATR (Core target)
    # TP3: 3.0x ATR (Runner)
    
    if signal_direction == "bullish":
        sl = current_price - (atr * atr_multiplier_sl)
        tp1 = current_price + (atr * 1.0)
        tp2 = current_price + (atr * 2.0)
        tp3 = current_price + (atr * atr_multiplier_tp)
        desc = f"Bullish setup: Stop Loss at {sl:.2f}. Scaling Targets: TP1 (De-risk) at {tp1:.2f}, TP2 at {tp2:.2f}, Final TP at {tp3:.2f}."
    elif signal_direction == "bearish":
        sl = current_price + (atr * atr_multiplier_sl)
        tp1 = current_price - (atr * 1.0)
        tp2 = current_price - (atr * 2.0)
        tp3 = current_price - (atr * atr_multiplier_tp)
        desc = f"Bearish setup: Stop Loss at {sl:.2f}. Scaling Targets: TP1 (De-risk) at {tp1:.2f}, TP2 at {tp2:.2f}, Final TP at {tp3:.2f}."
    else:
        # Neutral - hypothetical symmetric bounds
        sl = current_price - (atr * atr_multiplier_sl)
        tp1 = current_price + (atr * 1.0)
        tp2 = current_price + (atr * 2.0)
        tp3 = current_price + (atr * atr_multiplier_tp)
        desc = f"Neutral market. ATR is {atr:.2f}. Expect daily swings between {sl:.2f} and {tp3:.2f}."

    # Standard risk-reward is usually TP_dist / SL_dist
    rr_ratio = atr_multiplier_tp / atr_multiplier_sl if atr_multiplier_sl > 0 else 0

    return VolatilityAnalysis(
        atr=round(atr, 4),
        stop_loss=round(sl, 4),
        take_profit=round(tp3, 4),
        take_profit_level1=round(tp1, 4),
        take_profit_level2=round(tp2, 4),
        risk_reward_ratio=round(rr_ratio, 2),
        description=desc
    )
