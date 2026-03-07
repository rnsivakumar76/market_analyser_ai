import pandas as pd
import numpy as np
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

def calculate_correlations(data_map: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """
    Calculate Pearson correlation between all instruments based on the last 60 daily returns.

    All inputs are resampled to daily frequency before computing pct_change so that
    intraday (1h) watchlist bars and daily benchmark bars (SPX_macro, BTC_macro) share
    a common time axis.  Without this step, 1h series only produce ~1-2 days of tail(30)
    data and align perfectly with other 1h series (giving spurious +1.00 vs XAU) while
    failing to align with daily series (giving 0.00 vs SPX/BTC).
    """
    if not data_map:
        return {"labels": [], "matrix": []}

    _LOOKBACK = 60   # trading days
    _MIN_ROWS  = 15  # minimum overlapping daily rows required to include a symbol

    price_series = {}
    for symbol, df in data_map.items():
        if df is None or df.empty or 'Close' not in df.columns:
            continue
        try:
            close = df['Close']
            # Normalise to a timezone-naive DatetimeIndex so resample works reliably
            if not isinstance(close.index, pd.DatetimeIndex):
                continue
            if close.index.tz is not None:
                close = close.copy()
                close.index = close.index.tz_localize(None)
            # Resample to business-day frequency (last close of each day)
            daily = close.resample('B').last().dropna()
            if len(daily) < _MIN_ROWS:
                continue
            returns = daily.tail(_LOOKBACK).pct_change().dropna()
            if len(returns) >= _MIN_ROWS:
                price_series[symbol] = returns
        except Exception as e:
            logger.warning(f"[CORR] Failed to build daily returns for {symbol}: {e}")

    if not price_series:
        return {"labels": [], "matrix": []}

    # Combine into a single DataFrame — pandas aligns by index automatically
    combined_df = pd.DataFrame(price_series)

    # Drop any column that has fewer than MIN_ROWS non-NaN observations after alignment
    combined_df = combined_df.dropna(thresh=_MIN_ROWS)
    combined_df = combined_df.dropna(axis=1, thresh=_MIN_ROWS)

    if combined_df.empty or len(combined_df.columns) < 2:
        return {"labels": [], "matrix": []}

    # Pearson correlation; replace any remaining NaN (e.g. zero-variance series) with 0
    corr_matrix = combined_df.corr(min_periods=_MIN_ROWS).replace({np.nan: 0})

    labels = corr_matrix.columns.tolist()
    matrix = [[round(float(val), 2) for val in row] for row in corr_matrix.values]

    return {
        "labels": labels,
        "matrix": matrix
    }
