import pandas as pd
import numpy as np
from scipy.stats import percentileofscore
from app.models import VolatilityAnalysis
from domain.indicators.atr import calculate_atr as _domain_calculate_atr, calculate_atr_series
from domain.constants import INDICATOR_ATR_PERIOD, VOLATILITY_REGIME_ATR_MULTIPLIERS


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

    Multipliers are regime-adaptive by default:
      - COMPRESSED (≤25th pct ATR): tighter stops — 1.0× SL / 2.0× TP3
      - NORMAL     (26–60th pct):   standard    — 1.5× SL / 3.0× TP3
      - ELEVATED   (61–80th pct):   wider stops — 2.0× SL / 4.0× TP3
      - EXTREME    (>80th pct):     max width   — 2.5× SL / 5.0× TP3

    If atr_multiplier_sl / atr_multiplier_tp differ from their NORMAL defaults
    (1.5 / 3.0) the caller's explicit values override the adaptive table.

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

    # ── 1. Compute regime FIRST so multipliers can adapt ────────────────────
    atr_pct_rank, atr_regime, hv_14, hv_pct, regime_label = _calc_volatility_regime(data, atr)

    # ── 2. Select multipliers ────────────────────────────────────────────────
    _NORMAL_SL = 1.5
    _NORMAL_TP = 3.0
    caller_override = (atr_multiplier_sl != _NORMAL_SL or atr_multiplier_tp != _NORMAL_TP)

    if caller_override:
        sl_mult  = atr_multiplier_sl
        tp1_mult = 1.0
        tp2_mult = 2.0
        tp3_mult = atr_multiplier_tp
    else:
        mults    = VOLATILITY_REGIME_ATR_MULTIPLIERS.get(atr_regime, VOLATILITY_REGIME_ATR_MULTIPLIERS["NORMAL"])
        sl_mult  = mults["sl"]
        tp1_mult = mults["tp1"]
        tp2_mult = mults["tp2"]
        tp3_mult = mults["tp3"]

    # ── 3. Anchor to ideal entry if provided ────────────────────────────────
    anchor = entry_price if (entry_price and entry_price > 0) else current_price

    # ── 4. SL / TP levels ───────────────────────────────────────────────────
    regime_note = f" [{regime_label} vol, {sl_mult}×/{tp3_mult}× ATR]"

    if signal_direction == "bullish":
        sl  = anchor - (atr * sl_mult)
        tp1 = anchor + (atr * tp1_mult)
        tp2 = anchor + (atr * tp2_mult)
        tp3 = anchor + (atr * tp3_mult)
        desc = (f"Bullish setup{regime_note}: Stop Loss at {sl:.2f}. "
                f"Scaling Targets: TP1 (De-risk) at {tp1:.2f}, TP2 at {tp2:.2f}, Final TP at {tp3:.2f}.")
    elif signal_direction == "bearish":
        sl  = anchor + (atr * sl_mult)
        tp1 = anchor - (atr * tp1_mult)
        tp2 = anchor - (atr * tp2_mult)
        tp3 = anchor - (atr * tp3_mult)
        desc = (f"Bearish setup{regime_note}: Stop Loss at {sl:.2f}. "
                f"Scaling Targets: TP1 (De-risk) at {tp1:.2f}, TP2 at {tp2:.2f}, Final TP at {tp3:.2f}.")
    else:
        sl  = anchor - (atr * sl_mult)
        tp1 = anchor + (atr * tp1_mult)
        tp2 = anchor + (atr * tp2_mult)
        tp3 = anchor + (atr * tp3_mult)
        desc = (f"Neutral market{regime_note}. ATR is {atr:.2f}. "
                f"Expect daily swings between {sl:.2f} and {tp3:.2f}.")

    rr_ratio = tp3_mult / sl_mult if sl_mult > 0 else 0

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
