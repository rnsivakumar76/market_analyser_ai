"""
Intraday Signal Generator
==========================
Detects EMA 9/21 crossover and MACD histogram crossover signals on
15m, 1H, and 4H timeframes using a top-down MTF filter:

  4H  → sets the bias (LONG only / SHORT only / neutral → skip)
  1H  → confirms the setup (must agree with 4H)
  15m → fires the entry trigger (must agree with 4H + 1H)

Signals are fired ONLY on a CLOSED bar (latest complete bar),
preventing mid-bar noise.

Trigger confidence levels:
  EMA cross + MACD cross same direction  → 80  (EMA_MACD_CONFLUENCE)
  EMA cross alone                        → 65  (EMA_CROSS)
  MACD histogram flip alone              → 55  (MACD_CROSS)
"""

import uuid
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple

from ..models import IntradaySignal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EMA_FAST = 9
EMA_SLOW = 21
ATR_PERIOD = 14
ATR_SL_MULT = 1.5    # stop-loss = ATR × 1.5
ATR_TP1_MULT = 1.5   # TP1 = 1:1 R
ATR_TP2_MULT = 3.0   # TP2 = 2:1 R

_EXPIRY: dict = {"15m": timedelta(hours=4), "1H": timedelta(hours=16), "4H": timedelta(days=2)}
_MIN_BARS = 50   # minimum bars needed for reliable signals


# ---------------------------------------------------------------------------
# Low-level indicator helpers (no pandas dependency in the inner loop)
# ---------------------------------------------------------------------------

def _ema(arr: np.ndarray, span: int) -> np.ndarray:
    alpha = 2.0 / (span + 1)
    out = np.full(len(arr), np.nan)
    # find first non-nan seed
    s = 0
    while s < len(arr) and np.isnan(arr[s]):
        s += 1
    if s >= len(arr):
        return out
    out[s] = arr[s]
    for i in range(s + 1, len(arr)):
        out[i] = alpha * arr[i] + (1.0 - alpha) * out[i - 1]
    return out


def _calc_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = ATR_PERIOD) -> float:
    if len(closes) < period + 1:
        return float(np.mean(highs[-5:] - lows[-5:]))
    tr = np.maximum(highs[1:] - lows[1:],
         np.maximum(np.abs(highs[1:] - closes[:-1]),
                    np.abs(lows[1:] - closes[:-1])))
    return float(np.mean(tr[-period:]))


def _ema_crossover(closes: np.ndarray) -> str:
    """
    Detect EMA 9/21 crossover on the last CLOSED bar.
    Returns 'bullish' | 'bearish' | 'none'
    """
    if len(closes) < EMA_SLOW + 5:
        return "none"
    fast = _ema(closes, EMA_FAST)
    slow = _ema(closes, EMA_SLOW)
    # Use index -2 (last closed) and -3 (previous closed) to avoid lookahead
    if np.isnan(fast[-2]) or np.isnan(slow[-2]) or np.isnan(fast[-3]) or np.isnan(slow[-3]):
        return "none"
    prev_diff = fast[-3] - slow[-3]
    curr_diff = fast[-2] - slow[-2]
    if prev_diff <= 0 < curr_diff:
        return "bullish"
    if prev_diff >= 0 > curr_diff:
        return "bearish"
    return "none"


def _ema_bias(closes: np.ndarray) -> str:
    """
    Return the current EMA bias (price above/below EMA21).
    Used for 4H top-down filter.
    Returns 'bullish' | 'bearish' | 'neutral'
    """
    if len(closes) < EMA_SLOW + 2:
        return "neutral"
    slow = _ema(closes, EMA_SLOW)
    if np.isnan(slow[-2]):
        return "neutral"
    diff_pct = (closes[-2] - slow[-2]) / slow[-2] * 100
    if diff_pct > 0.15:
        return "bullish"
    if diff_pct < -0.15:
        return "bearish"
    return "neutral"


def _macd_crossover(closes: np.ndarray) -> str:
    """
    Detect MACD histogram sign flip (crossover) on last CLOSED bar.
    Returns 'bullish' | 'bearish' | 'none'
    """
    if len(closes) < 35 + 9:  # 26 slow + 9 signal
        return "none"
    fast_ema = _ema(closes, 12)
    slow_ema = _ema(closes, 26)
    macd_line = fast_ema - slow_ema
    signal_line = _ema(macd_line, 9)
    hist = macd_line - signal_line

    valid = ~np.isnan(hist)
    if valid.sum() < 3:
        return "none"
    idx = np.where(valid)[0]
    h_curr = hist[idx[-2]]   # last closed bar
    h_prev = hist[idx[-3]]   # bar before last

    if h_prev <= 0 < h_curr:
        return "bullish"
    if h_prev >= 0 > h_curr:
        return "bearish"
    return "none"


# ---------------------------------------------------------------------------
# Per-timeframe signal detection
# ---------------------------------------------------------------------------

def _scan_timeframe(
    symbol: str,
    name: str,
    timeframe: str,
    bars: pd.DataFrame,
    bias_4h: str,
    bias_1h: str,
) -> Optional[IntradaySignal]:
    """
    Scan a single timeframe for entry signals.
    Applies MTF filter: 15m requires 4H+1H agreement; 1H requires 4H agreement.
    Returns an IntradaySignal if a trigger fires, else None.
    """
    if bars is None or len(bars) < _MIN_BARS:
        return None

    closes = bars["Close"].values.astype(float)
    highs  = bars["High"].values.astype(float)
    lows   = bars["Low"].values.astype(float)

    # MTF bias filter
    if timeframe == "15m":
        if bias_4h == "neutral" or bias_1h == "neutral":
            return None
        if bias_4h != bias_1h:
            return None          # disagreement — stay out
        required_dir = bias_4h
    elif timeframe == "1H":
        if bias_4h == "neutral":
            return None
        required_dir = bias_4h
    else:  # 4H — no filter, just detect
        required_dir = None

    ema_dir  = _ema_crossover(closes)
    macd_dir = _macd_crossover(closes)

    # Determine final direction
    if ema_dir != "none" and macd_dir != "none" and ema_dir == macd_dir:
        direction = ema_dir
        trigger   = "EMA_MACD_CONFLUENCE"
        confidence = 80
    elif ema_dir != "none":
        direction  = ema_dir
        trigger    = "EMA_CROSS"
        confidence = 65
    elif macd_dir != "none":
        direction  = macd_dir
        trigger    = "MACD_CROSS"
        confidence = 55
    else:
        return None  # no trigger

    # Apply MTF direction filter
    if required_dir and direction != required_dir:
        return None

    atr_val = _calc_atr(highs, lows, closes)
    entry   = round(float(closes[-2]), 5)   # last closed bar price

    if direction == "bullish":
        sl  = round(entry - atr_val * ATR_SL_MULT,  5)
        tp1 = round(entry + atr_val * ATR_TP1_MULT, 5)
        tp2 = round(entry + atr_val * ATR_TP2_MULT, 5)
        sig_type = "LONG"
    else:
        sl  = round(entry + atr_val * ATR_SL_MULT,  5)
        tp1 = round(entry - atr_val * ATR_TP1_MULT, 5)
        tp2 = round(entry - atr_val * ATR_TP2_MULT, 5)
        sig_type = "SHORT"

    now = datetime.now(timezone.utc)
    bar_time = str(bars.index[-2])  # last closed bar timestamp

    notes_parts = []
    if timeframe in ("1H", "15m"):
        notes_parts.append(f"4H bias: {bias_4h.upper()}")
    if timeframe == "15m":
        notes_parts.append(f"1H bias: {bias_1h.upper()}")

    return IntradaySignal(
        signal_id   = str(uuid.uuid4()),
        symbol      = symbol,
        name        = name,
        timeframe   = timeframe,
        signal_type = sig_type,
        trigger     = trigger,
        entry_price = entry,
        stop_loss   = sl,
        take_profit_1 = tp1,
        take_profit_2 = tp2,
        risk_reward = round(ATR_TP1_MULT / ATR_SL_MULT, 2),
        mtf_bias    = bias_4h,
        confidence  = confidence,
        generated_at = now.isoformat(),
        bar_time    = bar_time,
        expires_at  = (now + _EXPIRY[timeframe]).isoformat(),
        status      = "ACTIVE",
        notes       = " | ".join(notes_parts),
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def detect_intraday_signals(
    symbol: str,
    name: str,
    bars_4h: Optional[pd.DataFrame],
    bars_1h: Optional[pd.DataFrame],
    bars_15m: Optional[pd.DataFrame],
) -> List[IntradaySignal]:
    """
    Scan all three timeframes (4H → 1H → 15m) and return any new signals.
    Caller is responsible for deduplication against already-stored signals.
    """
    signals: List[IntradaySignal] = []

    # Compute bias from 4H and 1H (used as MTF filters)
    bias_4h = "neutral"
    if bars_4h is not None and len(bars_4h) >= _MIN_BARS:
        bias_4h = _ema_bias(bars_4h["Close"].values.astype(float))

    bias_1h = "neutral"
    if bars_1h is not None and len(bars_1h) >= _MIN_BARS:
        bias_1h = _ema_bias(bars_1h["Close"].values.astype(float))

    logger.info(f"[SIGNAL] {symbol} bias — 4H: {bias_4h}, 1H: {bias_1h}")

    for tf_name, bars in [("4H", bars_4h), ("1H", bars_1h), ("15m", bars_15m)]:
        try:
            sig = _scan_timeframe(symbol, name, tf_name, bars, bias_4h, bias_1h)
            if sig:
                signals.append(sig)
                logger.info(
                    f"[SIGNAL] {symbol} {tf_name} {sig.signal_type} via {sig.trigger} "
                    f"@ {sig.entry_price} conf={sig.confidence}"
                )
        except Exception as exc:
            logger.warning(f"[SIGNAL] {symbol} {tf_name} scan error: {exc}")

    return signals
