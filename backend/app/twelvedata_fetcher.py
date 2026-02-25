import pandas as pd
from twelvedata import TDClient
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
import logging
import time
import os
import threading
from .config_loader import load_config

logger = logging.getLogger(__name__)

class TwelveDataFetcher:
    """
    Twelve Data fetcher with thread-safe rate limiting and retry logic.
    Optimized for price accuracy and speed.
    """
    _lock = threading.Lock()
    _last_call_time = 0
    
    def __init__(self, api_key: str = None):
        if api_key is None:
            try:
                config = load_config()
                api_key = config.get('twelvedata', {}).get('api_key', 'YOUR_API_KEY_HERE')
            except:
                pass
            if api_key == 'YOUR_API_KEY_HERE':
                api_key = os.getenv('TWELVEDATA_API_KEY', 'YOUR_API_KEY_HERE')
        
        self.api_key = api_key
        self.client = TDClient(apikey=api_key)
        
    def _rate_limit_wait(self):
        """Ensures safe interval between calls (min 1.1s for 55 req/min)."""
        with self._lock:
            now = time.time()
            elapsed = now - TwelveDataFetcher._last_call_time
            # 1.2s to be safe against slight clock drifts across Lambdas
            wait_time = 1.2 - elapsed
            if wait_time > 0:
                time.sleep(wait_time)
            TwelveDataFetcher._last_call_time = time.time()
            
    def get_symbol_mapping(self, symbol: str) -> str:
        """
        Maps symbols to Twelve Data format.
        Prioritizes direct SPOT symbols where possible.
        """
        sym = symbol.upper()
        
        # Primary Mappings (Attempt spot first)
        mappings = {
            'XAU': 'XAU/USD',      # Gold Spot (Try first)
            'XAG': 'XAG/USD',      # Silver Spot
            'BCO': 'BZ/USD',       # Brent Oil
            'WTI': 'WTI/USD',      # Crude Oil
            'SPX': 'SPY',          # S&P 500 (Free tier usually requires SPY)
            'IXIC': 'QQQ',         # Nasdaq
            'DJI': 'DIA',          # Dow Jones
            'BTC-USD': 'BTC/USD',
            'ETH-USD': 'ETH/USD',
            'BTC': 'BTC/USD',
            'ETH': 'ETH/USD',
            'USDJPY': 'USD/JPY',
            'EURUSD': 'EUR/USD',
            'GBPUSD': 'GBP/USD',
            'AUDUSD': 'AUD/USD',
        }
        
        # Fallback ETF Mappings (Used if primary fails in fetch method)
        return mappings.get(sym, sym)

    def _get_fallback_symbol(self, symbol: str) -> Optional[str]:
        fallbacks = {
            'XAU/USD': 'GLD',
            'XAG/USD': 'SLV',
            'BZ/USD': 'USO',
            'WTI/USD': 'USO',
            'SPX': 'SPY'
        }
        return fallbacks.get(symbol)
    
    def fetch_historical_data(self, symbol: str, days: int = 90, interval: str = "1day", retries: int = 2) -> pd.DataFrame:
        """Fetch historical data with ETF fallback for restricted symbols."""
        target_symbol = self.get_symbol_mapping(symbol)
        
        for attempt in range(retries):
            try:
                self._rate_limit_wait()
                
                outputsize = days
                if interval == "1h": outputsize = days * 24
                elif interval == "4h": outputsize = days * 6
                outputsize = min(outputsize, 5000)

                ts = self.client.time_series(
                    symbol=target_symbol,
                    interval=interval,
                    outputsize=outputsize,
                    timezone="UTC"
                )
                
                df = ts.as_pandas()
                
                # If spot fails (e.g. 401 Unauthorized for XAU/USD), try ETF fallback
                if (df is None or df.empty) and attempt == 0:
                    fb = self._get_fallback_symbol(target_symbol)
                    if fb:
                        logger.info(f"Spot restricted for {symbol}. Falling back to ETF: {fb}")
                        target_symbol = fb
                        continue # Re-try loop with fallback symbol

                if df is None or df.empty:
                    raise ValueError(f"No data for {symbol}")
                
                # Normalize columns
                column_mapping = {'datetime': 'Date', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}
                for old_col, new_col in column_mapping.items():
                    if old_col in df.columns:
                        df = df.rename(columns={old_col: new_col})
                
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'])
                    df = df.set_index('Date')
                
                return df.sort_index(ascending=True)

            except Exception as e:
                # If rate limited, wait and retry
                if "429" in str(e) and attempt < retries - 1:
                    time.sleep(5)
                    continue
                
                # If it's a "symbol not found" or "unauthorized" error, try fallback immediately if not tried
                if ("not found" in str(e).lower() or "unauthorized" in str(e).lower()) and attempt == 0:
                    fb = self._get_fallback_symbol(target_symbol)
                    if fb:
                        target_symbol = fb
                        continue
                
                if attempt == retries - 1:
                    logger.error(f"[TwelveData] Error for {symbol}: {e}")
                    raise e

    def get_current_price(self, symbol: str, retries: int = 2) -> float:
        """Fetch current price with spot prioritizing."""
        target_symbol = self.get_symbol_mapping(symbol)
        
        for attempt in range(retries):
            try:
                self._rate_limit_wait()
                data = self.client.price(symbol=target_symbol).as_json()
                
                if (not data or 'price' not in data) and attempt == 0:
                    fb = self._get_fallback_symbol(target_symbol)
                    if fb:
                        target_symbol = fb
                        continue

                if data and 'price' in data:
                    return float(data['price'])
                
                raise ValueError(f"Price missing for {symbol}")

            except Exception as e:
                if attempt == retries - 1:
                    raise e
                time.sleep(1)
