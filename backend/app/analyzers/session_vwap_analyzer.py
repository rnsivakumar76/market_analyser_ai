import pandas as pd
import numpy as np
from typing import Optional
import logging

from ..models import SessionVWAP

logger = logging.getLogger(__name__)


def calculate_session_vwap(
    intraday_df: Optional[pd.DataFrame],
    current_price: float
) -> Optional[SessionVWAP]:
    """
    Calculate session VWAP using intraday (1h or 15min) data.
    Uses bars from the current trading day only.
    Falls back to full intraday window if same-day bars are insufficient.
    """
    try:
        if intraday_df is None or len(intraday_df) < 2:
            return None

        df = intraday_df.copy()

        # Normalise column names
        df.columns = [c.strip().capitalize() for c in df.columns]
        if 'Close' not in df.columns:
            return None

        # Attempt to filter to today's session
        if hasattr(df.index, 'date'):
            today = df.index[-1].date()
            session_bars = df[df.index.date == today]
            if len(session_bars) < 2:
                session_bars = df.tail(min(24, len(df)))
        else:
            session_bars = df.tail(min(24, len(df)))

        if len(session_bars) < 2:
            return None

        # Typical price
        typical = (session_bars['High'] + session_bars['Low'] + session_bars['Close']) / 3
        volume = session_bars.get('Volume', pd.Series(np.ones(len(session_bars)), index=session_bars.index))
        volume = volume.replace(0, 1)

        cumulative_tpv = (typical * volume).cumsum()
        cumulative_vol = volume.cumsum()
        vwap_series = cumulative_tpv / cumulative_vol

        vwap = round(float(vwap_series.iloc[-1]), 4)

        # Upper/Lower bands (±1 std dev of (typical - vwap))
        diff = typical - vwap_series
        std = float(diff.std()) if len(diff) > 1 else float(typical.std())
        upper_band = round(vwap + std, 4)
        lower_band = round(vwap - std, 4)

        dist_pct = round((current_price - vwap) / vwap * 100, 2)

        if dist_pct > 1.5:
            position = "EXTENDED ABOVE"
            interpretation = f"Price is {dist_pct:+.1f}% above VWAP. Longs extended — avoid chasing; wait for VWAP pullback."
        elif dist_pct < -1.5:
            position = "EXTENDED BELOW"
            interpretation = f"Price is {dist_pct:+.1f}% below VWAP. Oversold vs session mean — potential mean-reversion entry."
        elif dist_pct > 0:
            position = "ABOVE"
            interpretation = f"Price is {dist_pct:+.1f}% above VWAP. Bullish session bias. VWAP at ${vwap:.2f} acts as dynamic support."
        else:
            position = "BELOW"
            interpretation = f"Price is {dist_pct:+.1f}% below VWAP. Bearish session bias. VWAP at ${vwap:.2f} acts as dynamic resistance."

        return SessionVWAP(
            vwap=vwap,
            upper_band=upper_band,
            lower_band=lower_band,
            distance_pct=dist_pct,
            position=position,
            bar_count=len(session_bars),
            interpretation=interpretation
        )

    except Exception as e:
        logger.error(f"Session VWAP calculation failed: {e}")
        return None
