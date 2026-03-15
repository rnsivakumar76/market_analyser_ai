import pandas as pd
from typing import Optional

from ..models import BlowOffTopAnalysis, BlowOffTopSignals

_OIL_SYMBOL_HINTS = ("WTI", "CL", "OIL", "BRENT", "USOIL")
_VERTICAL_RETURN_10 = 12.0
_VERTICAL_RETURN_5 = 7.0
_ARMED_SCORE = 60


def _is_oil_symbol(symbol: str) -> bool:
    s = (symbol or "").upper()
    return any(token in s for token in _OIL_SYMBOL_HINTS)


def _build_narrative(result: BlowOffTopAnalysis) -> str:
    if not result.applicable:
        return "Blow-off model is enabled for oil instruments only."
    if result.phase == "confirmed_breakdown":
        return (
            f"Blow-off top breakdown confirmed. Structure break below {result.trigger_level:.2f} "
            f"with invalidation above {result.invalidation_level:.2f}."
            if result.trigger_level is not None and result.invalidation_level is not None
            else "Blow-off top breakdown confirmed."
        )
    if result.entry_state == "armed":
        return (
            "Late-cycle blow-off conditions are active, but structure has not broken yet. "
            "Wait for confirmed breakdown before full short execution."
        )
    if result.phase == "acceleration":
        return "Oil is accelerating upward with elevated volatility. Early blow-off risk is building."
    return "No active blow-off top pattern detected."


def analyze_blowoff_top(
    symbol: str,
    df: pd.DataFrame,
    technical_indicators=None,
    volatility=None,
) -> BlowOffTopAnalysis:
    """
    Detect oil blow-off top conditions and return a staged execution state.

    Stages:
      - normal
      - acceleration
      - blowoff
      - confirmed_breakdown
    """
    if not _is_oil_symbol(symbol):
        result = BlowOffTopAnalysis(applicable=False)
        result.narrative = _build_narrative(result)
        return result

    if df is None or df.empty or len(df) < 30:
        result = BlowOffTopAnalysis(
            applicable=True,
            phase="normal",
            entry_state="wait",
            narrative="Insufficient bars to evaluate oil blow-off structure.",
        )
        return result

    data = df.tail(40).copy()

    close = data["Close"].astype(float)
    high = data["High"].astype(float)
    low = data["Low"].astype(float)

    ret10 = ((close.iloc[-1] / close.iloc[-11]) - 1.0) * 100 if len(close) >= 11 else 0.0
    ret5 = ((close.iloc[-1] / close.iloc[-6]) - 1.0) * 100 if len(close) >= 6 else 0.0
    vertical_move = ret10 >= _VERTICAL_RETURN_10 or ret5 >= _VERTICAL_RETURN_5

    atr_pct = float(getattr(volatility, "atr_percentile_rank", 50.0) or 50.0)
    range_expansion = atr_pct >= 70.0

    rsi_divergence = str(getattr(technical_indicators, "rsi_divergence", "") or "").lower()
    rsi_bearish_divergence = rsi_divergence == "bearish"

    prev_high_20 = float(high.iloc[-21:-1].max()) if len(high) >= 21 else float(high.iloc[:-1].max())
    failed_breakout = bool(high.iloc[-1] > prev_high_20 and close.iloc[-1] < prev_high_20)

    recent_window = data.tail(25).reset_index(drop=True)
    recent_peak = float(recent_window["High"].max())
    peak_idx = int(recent_window["High"].idxmax())

    structure_break = False
    trigger_level: Optional[float] = None
    structural_low: Optional[float] = None

    if peak_idx < len(recent_window) - 4:
        post_peak = recent_window.iloc[peak_idx + 1 :]
        highs_after_peak = post_peak["High"].astype(float)
        lower_high = bool(len(highs_after_peak) >= 2 and float(highs_after_peak.max()) < recent_peak * 0.995)

        pre_last_after_peak = post_peak.iloc[:-1]
        if not pre_last_after_peak.empty:
            structural_low = float(pre_last_after_peak["Low"].astype(float).min())
            trigger_level = structural_low
            structure_break = bool(lower_high and float(close.iloc[-1]) < structural_low)

    score = 0
    score += 25 if vertical_move else 0
    score += 20 if range_expansion else 0
    score += 20 if rsi_bearish_divergence else 0
    score += 20 if failed_breakout else 0
    score += 15 if structure_break else 0

    if structure_break:
        phase = "confirmed_breakdown"
        entry_state = "triggered"
    elif score >= _ARMED_SCORE:
        phase = "blowoff"
        entry_state = "armed"
    elif vertical_move and (range_expansion or failed_breakout):
        phase = "acceleration"
        entry_state = "wait"
    else:
        phase = "normal"
        entry_state = "wait"

    signals = BlowOffTopSignals(
        vertical_move=vertical_move,
        range_expansion=range_expansion,
        rsi_bearish_divergence=rsi_bearish_divergence,
        failed_breakout=failed_breakout,
        structure_break=structure_break,
    )

    result = BlowOffTopAnalysis(
        applicable=True,
        detected=score >= _ARMED_SCORE,
        blowoff_score=max(0, min(score, 100)),
        phase=phase,
        entry_state=entry_state,
        trigger_level=trigger_level,
        invalidation_level=recent_peak,
        recent_peak=recent_peak,
        structural_low=structural_low,
        signals=signals,
    )
    result.narrative = _build_narrative(result)
    return result
