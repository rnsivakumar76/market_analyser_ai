import pandas as pd
import numpy as np
from scipy.stats import percentileofscore
from app.models import VolatilityAnalysis
from domain.indicators.atr import calculate_atr as _domain_calculate_atr, calculate_atr_series
from domain.constants import INDICATOR_ATR_PERIOD


def calculate_atr(data: pd.DataFrame, period: int = INDICATOR_ATR_PERIOD) -> float:
    """Calculate the Average True Range (ATR). Delegates to domain layer."""
    if data is None or data.empty or len(data) < period + 1:
        return 0.0
    return _domain_calculate_atr(
        data['High'].tolist(),
        data['Low'].tolist(),
        data['Close'].tolist(),
        period=period,
    )


def analyze_volatility_and_risk(
    data: pd.DataFrame, 
    current_price: float, 
    signal_direction: str,
    atr_multiplier_sl: float = 1.5,
    atr_multiplier_tp: float = 3.0,
    entry_price: float = None
) -> VolatilityAnalysis:
    """Analyze volatility, calculate stop loss and take profit.
    
    If entry_price is provided (e.g. a pending pullback level), stop/target are
    anchored at entry_price rather than current_price for accurate R/R display.
    """
    
    atr = calculate_atr(data, period=14)
    
    if atr == 0.0:
        return VolatilityAnalysis(
            atr=0.0,
            stop_loss=0.0,
            take_profit=0.0,
            risk_reward_ratio=0.0,
            description="Insufficient data for Volatility/ATR calculation."
        )

    # Use entry_price as the anchor when a pending entry level is known;
    # otherwise fall back to current_price (immediate/market entry).
    anchor = entry_price if (entry_price and entry_price > 0) else current_price

    # Calculate stop loss and take profit levels (Institutional Scaling Model)
    # TP1: 1.0x ATR (Initial de-risk)
    # TP2: 2.0x ATR (Core target)
    # TP3: 3.0x ATR (Runner)
    
    if signal_direction == "bullish":
        sl = anchor - (atr * atr_multiplier_sl)
        tp1 = anchor + (atr * 1.0)
        tp2 = anchor + (atr * 2.0)
        tp3 = anchor + (atr * atr_multiplier_tp)
        desc = f"Bullish setup: Stop Loss at {sl:.2f}. Scaling Targets: TP1 (De-risk) at {tp1:.2f}, TP2 at {tp2:.2f}, Final TP at {tp3:.2f}."
    elif signal_direction == "bearish":
        sl = anchor + (atr * atr_multiplier_sl)
        tp1 = anchor - (atr * 1.0)
        tp2 = anchor - (atr * 2.0)
        tp3 = anchor - (atr * atr_multiplier_tp)
        desc = f"Bearish setup: Stop Loss at {sl:.2f}. Scaling Targets: TP1 (De-risk) at {tp1:.2f}, TP2 at {tp2:.2f}, Final TP at {tp3:.2f}."
    else:
        # Neutral - hypothetical symmetric bounds
        sl = anchor - (atr * atr_multiplier_sl)
        tp1 = anchor + (atr * 1.0)
        tp2 = anchor + (atr * 2.0)
        tp3 = anchor + (atr * atr_multiplier_tp)
        desc = f"Neutral market. ATR is {atr:.2f}. Expect daily swings between {sl:.2f} and {tp3:.2f}."

    # Standard risk-reward is usually TP_dist / SL_dist
    rr_ratio = atr_multiplier_tp / atr_multiplier_sl if atr_multiplier_sl > 0 else 0

    atr_pct_rank, atr_regime, hv_14, hv_pct, regime_label = _calc_volatility_regime(data, atr)

    return VolatilityAnalysis(
        atr=float(round(atr, 4)),
        stop_loss=float(round(sl, 4)),
        take_profit=float(round(tp3, 4)),
        take_profit_level1=float(round(tp1, 4)),
        take_profit_level2=float(round(tp2, 4)),
        risk_reward_ratio=float(round(rr_ratio, 2)),
        description=desc,
        atr_percentile_rank=atr_pct_rank,
        atr_regime=atr_regime,
        historical_volatility_14=hv_14,
        hv_percentile=hv_pct,
        volatility_regime_label=regime_label
    )


def _calc_volatility_regime(data: pd.DataFrame, current_atr: float):
    """Compute ATR percentile rank, 14-day HV, HV percentile, and regime label."""
    try:
        df = data.copy()

        # Rolling 14-period ATR series for percentile rank
        df['Prev_Close'] = df['Close'].shift(1)
        df['TR'] = df[['High', 'Low', 'Close']].apply(
            lambda r: max(r['High'] - r['Low'],
                          abs(r['High'] - df.loc[r.name, 'Prev_Close']) if not pd.isna(df.loc[r.name, 'Prev_Close']) else 0,
                          abs(r['Low']  - df.loc[r.name, 'Prev_Close']) if not pd.isna(df.loc[r.name, 'Prev_Close']) else 0),
            axis=1
        )
        atr_series = df['TR'].rolling(14).mean().dropna()

        atr_pct_rank = round(float(percentileofscore(atr_series.values, current_atr, kind='rank')), 1) if len(atr_series) > 10 else 50.0

        # 14-day Historical Volatility (annualised std of log returns)
        log_returns = np.log(df['Close'] / df['Close'].shift(1)).dropna()
        hv_14 = 0.0
        hv_pct = 50.0
        if len(log_returns) >= 14:
            current_hv = float(log_returns.tail(14).std() * np.sqrt(252) * 100)
            hv_14 = round(current_hv, 2)
            # Rolling 30-day HV series for percentile
            hv_series = log_returns.rolling(14).std().dropna() * np.sqrt(252) * 100
            hv_pct = round(float(percentileofscore(hv_series.values, current_hv, kind='rank')), 1)

        # Regime classification based on ATR percentile
        if atr_pct_rank <= 25:
            regime = "LOW"
            label = "Compressed"
        elif atr_pct_rank <= 60:
            regime = "NORMAL"
            label = "Normal"
        elif atr_pct_rank <= 80:
            regime = "ELEVATED"
            label = "Expanding"
        else:
            regime = "EXTREME"
            label = "Extreme"

        return atr_pct_rank, regime, hv_14, hv_pct, label
    except Exception:
        return 50.0, "NORMAL", 0.0, 50.0, "Normal"
