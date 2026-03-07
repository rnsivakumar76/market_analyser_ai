import pandas as pd
import numpy as np
from typing import Optional
import logging

from ..models import BlockFlowDetection, BlockFlowEvent

logger = logging.getLogger(__name__)

_BLOCK_VOLUME_MULTIPLIER = 2.5  # bar volume must be 2.5x avg to qualify
_LOOKBACK = 20                   # bars to consider for average volume


def detect_block_flow(df: pd.DataFrame, current_price: float) -> Optional[BlockFlowDetection]:
    """
    Detect institutional block flow from abnormal volume candles.
    A block flow event = bar with volume >= 2.5x 20-bar average AND
    significant body (close-open / ATR > 0.4).
    Returns up to 5 recent events, net direction, and interpretation.
    """
    try:
        if df is None or len(df) < _LOOKBACK + 5:
            return None

        data = df.tail(60).copy()
        data.columns = [c.strip().capitalize() for c in data.columns]

        if 'Volume' not in data.columns or data['Volume'].sum() == 0:
            return None

        avg_vol = data['Volume'].rolling(_LOOKBACK).mean()
        atr = (data['High'] - data['Low']).rolling(14).mean()

        events = []
        for i in range(_LOOKBACK, len(data)):
            vol = data['Volume'].iloc[i]
            avg = avg_vol.iloc[i]
            if avg <= 0 or vol < avg * _BLOCK_VOLUME_MULTIPLIER:
                continue

            bar_atr = atr.iloc[i]
            if bar_atr <= 0:
                continue

            body = abs(data['Close'].iloc[i] - data['Open'].iloc[i])
            body_ratio = body / bar_atr

            if body_ratio < 0.4:
                continue  # small-body bars are noise

            direction = "bullish" if data['Close'].iloc[i] >= data['Open'].iloc[i] else "bearish"
            vol_ratio = round(float(vol / avg), 1)

            # Try to get timestamp
            try:
                ts = str(data.index[i])[:10]
            except Exception:
                ts = f"bar-{i}"

            events.append(BlockFlowEvent(
                bar_index=i,
                timestamp=ts,
                price=round(float(data['Close'].iloc[i]), 4),
                volume_ratio=vol_ratio,
                direction=direction,
                body_ratio=round(float(body_ratio), 2)
            ))

        # Keep last 5 events
        events = events[-5:]

        _CAVEAT = " [Price proxy — closed-bar vol×ATR; not L2 tape data. Use for context only.]"

        if not events:
            return BlockFlowDetection(
                detected=False,
                events=[],
                net_direction="neutral",
                interpretation="No high-volume block bars detected in recent price action." + _CAVEAT,
            )

        bull_count = sum(1 for e in events if e.direction == "bullish")
        bear_count = sum(1 for e in events if e.direction == "bearish")

        if bull_count > bear_count:
            net_direction = "bullish"
            bias = f"{bull_count} bullish vs {bear_count} bearish high-volume bars"
        elif bear_count > bull_count:
            net_direction = "bearish"
            bias = f"{bear_count} bearish vs {bull_count} bullish high-volume bars"
        else:
            net_direction = "neutral"
            bias = "equal bullish and bearish high-volume bars"

        latest = events[-1]
        intent_label = (
            "possible accumulation." if net_direction == "bullish"
            else "possible distribution." if net_direction == "bearish"
            else "mixed high-volume activity."
        )
        interpretation = (
            f"Block flow proxy: {bias}. "
            f"Latest: {latest.direction.upper()} at ${latest.price:.2f} "
            f"({latest.volume_ratio}x avg vol) — {intent_label}"
            + _CAVEAT
        )

        return BlockFlowDetection(
            detected=True,
            events=events,
            net_direction=net_direction,
            bull_blocks=bull_count,
            bear_blocks=bear_count,
            interpretation=interpretation,
        )

    except Exception as e:
        logger.error(f"Block flow detection failed: {e}")
        return None
