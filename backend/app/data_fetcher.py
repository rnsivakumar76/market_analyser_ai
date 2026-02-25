import pandas as pd
from datetime import datetime
from typing import Optional
import os
import logging
from .twelvedata_fetcher import TwelveDataFetcher

# Setup logger
logger = logging.getLogger(__name__)

_td_fetcher = None

def get_td_fetcher():
    global _td_fetcher
    if _td_fetcher is None:
        _td_fetcher = TwelveDataFetcher()
    return _td_fetcher

def generate_mock_data(symbol: str, days: int = 90) -> pd.DataFrame:
    """Mock fallback removed to ensure usage of pure professional data."""
    return pd.DataFrame()

def fetch_historical_data(
    symbol: str,
    days: int = 90,
    interval: str = "1d",
    end_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Fetch historical OHLCV data EXCLUSIVELY via Twelve Data.
    All fallback sources have been removed per user request.
    """
    td = get_td_fetcher()
    
    if not td.api_key or td.api_key == 'YOUR_API_KEY_HERE':
        raise ValueError("Twelve Data API key not configured. Cannot fetch data.")

    try:
        logger.info(f"STRICT MODE: Fetching {symbol} ({interval}) via Twelve Data...")
        # Map Twelve Data intervals
        td_interval = "1day"
        if interval == "1h": td_interval = "1h"
        elif interval == "4h": td_interval = "4h"
        elif interval == "1wk": td_interval = "1week"
        elif interval == "1mo": td_interval = "1month"

        df = td.fetch_historical_data(symbol, days=days, interval=td_interval)
        if not df.empty:
            logger.info(f"[OK] Twelve Data Success for {symbol}")
            return df
        
        raise ValueError(f"Twelve Data returned empty result for {symbol}")

    except Exception as e:
        logger.error(f"[STRICT ERROR] Twelve Data fetch failed for {symbol}: {e}")
        raise ValueError(f"Twelve Data failed: {e}")

def get_current_price(symbol: str) -> float:
    """Get current price EXCLUSIVELY via Twelve Data."""
    td = get_td_fetcher()
    
    if not td.api_key or td.api_key == 'YOUR_API_KEY_HERE':
        raise ValueError("Twelve Data API key not configured. Cannot fetch price.")

    try:
        logger.info(f"STRICT MODE: Fetching current price for {symbol} via Twelve Data...")
        price = td.get_current_price(symbol)
        if price and price > 0:
            logger.info(f"[OK] Twelve Data price for {symbol}: {price}")
            return price
        
        raise ValueError(f"Twelve Data returned invalid price for {symbol}")

    except Exception as e:
        logger.error(f"[STRICT ERROR] Twelve Data current price failed for {symbol}: {e}")
        raise ValueError(f"Twelve Data failed: {e}")

def fetch_weekly_data(symbol: str, weeks: int = 12) -> pd.DataFrame:
    """Fetch weekly OHLCV data using the strict Twelve Data source."""
    # We prefer asking Twelve Data for 1week directly
    return fetch_historical_data(symbol, days=weeks*7, interval="1wk")
