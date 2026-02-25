import pandas as pd
from twelvedata import TDClient
from datetime import datetime, timedelta, timezone
from typing import Optional
import logging
import time
import os
import threading
from .config_loader import load_config

logger = logging.getLogger(__name__)

class TwelveDataFetcher:
    """
    Twelve Data fetcher with thread-safe rate limiting and retry logic.
    Optimized for AWS Lambda concurrency and the 55 req/min free tier limit.
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
        
        if api_key == 'YOUR_API_KEY_HERE':
            logger.warning("Twelve Data API key not configured.")
        
        self.api_key = api_key
        self.client = TDClient(apikey=api_key)
        
    def _rate_limit_wait(self):
        """
        Ensures at least 1.2 seconds between ANY Two calls to Twelve Data 
        across ANY threads in this process.
        """
        with self._lock:
            now = time.time()
            elapsed = now - TwelveDataFetcher._last_call_time
            wait_time = 1.2 - elapsed
            
            if wait_time > 0:
                logger.debug(f"Rate limiting: sleeping {wait_time:.2f}s")
                time.sleep(wait_time)
            
            TwelveDataFetcher._last_call_time = time.time()
            
    def get_symbol_mapping(self, symbol: str) -> str:
        symbol_mappings = {
            # Commodities (Free tier compatible via ETFs)
            'XAU': 'GLD',          # Gold
            'XAG': 'SLV',          # Silver
            'BCO': 'USO',          # Oil
            'WTI': 'USO',
            'GC=F': 'GLD',
            'SI=F': 'SLV',
            
            # Forex (Note: these often work in free tier)
            'USDJPY': 'USD/JPY', 'EURUSD': 'EUR/USD', 'GBPUSD': 'GBP/USD', 'AUDUSD': 'AUD/USD',
            'BTC-USD': 'BTC/USD', 'ETH-USD': 'ETH/USD', 'BTC': 'BTC/USD', 'ETH': 'ETH/USD',
            'SPX': 'SPY', 'IXIC': 'QQQ', 'DJI': 'DIA', 'SPY': 'SPY',
        }
        return symbol_mappings.get(symbol.upper(), symbol)
    
    def fetch_historical_data(self, symbol: str, days: int = 90, interval: str = "1day", retries: int = 3) -> pd.DataFrame:
        """Fetch historical data with retries for transient errors."""
        for attempt in range(retries):
            try:
                self._rate_limit_wait()
                td_symbol = self.get_symbol_mapping(symbol)
                
                outputsize = days
                if interval == "1h": outputsize = days * 24
                elif interval == "4h": outputsize = days * 6
                outputsize = min(outputsize, 5000)

                ts = self.client.time_series(
                    symbol=td_symbol,
                    interval=interval,
                    outputsize=outputsize,
                    timezone="UTC"
                )
                
                df = ts.as_pandas()
                if df is None or df.empty:
                    raise ValueError(f"No data found for {symbol}")
                
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
                if "429" in str(e) and attempt < retries - 1:
                    wait = (attempt + 1) * 5
                    logger.warning(f"Rate limited (429) for {symbol}. Retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                logger.error(f"[TwelveData] Attempt {attempt+1} failed for {symbol}: {e}")
                if attempt == retries - 1:
                    raise e

    def get_current_price(self, symbol: str, retries: int = 3) -> float:
        """Fetch current price with retries."""
        for attempt in range(retries):
            try:
                self._rate_limit_wait()
                td_symbol = self.get_symbol_mapping(symbol)
                data = self.client.price(symbol=td_symbol).as_json()
                
                if not data:
                    raise ValueError(f"No price data for {symbol}")
                
                if 'price' in data:
                    return float(data['price'])
                
                error_msg = data.get('message', str(data))
                if "429" in error_msg and attempt < retries - 1:
                    wait = (attempt + 1) * 5
                    time.sleep(wait)
                    continue
                raise ValueError(f"Twelve Data error: {error_msg}")

            except Exception as e:
                if attempt == retries - 1:
                    logger.error(f"[TwelveData] Final price attempt failed for {symbol}: {e}")
                    raise e
                time.sleep(1)
