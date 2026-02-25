import pandas as pd
from twelvedata import TDClient
from datetime import datetime
from typing import Optional, Dict, List, Union
import logging
import time
import os
import threading
from .config_loader import load_config

logger = logging.getLogger(__name__)

class TwelveDataFetcher:
    """
    Twelve Data fetcher optimized for speed via Batching and smart Fallbacks.
    Solves the 30s Gateway Timeout by fetching all instruments in 1-3 network calls.
    """
    _lock = threading.Lock()
    _last_call_time = 0
    
    def __init__(self, api_key: str = None):
        if api_key is None:
            try:
                config = load_config()
                api_key = config.get('twelvedata', {}).get('api_key', 'YOUR_API_KEY_HERE')
            except: pass
            if api_key == 'YOUR_API_KEY_HERE':
                api_key = os.getenv('TWELVEDATA_API_KEY', 'YOUR_API_KEY_HERE')
        
        self.api_key = api_key
        # Use direct TDClient for batch support
        self.client = TDClient(apikey=api_key)
        
    def _rate_limit_wait(self):
        """Ensures safe interval between calls."""
        with self._lock:
            now = time.time()
            elapsed = now - TwelveDataFetcher._last_call_time
            # 1.25s interval to safely stay under 55 requests/min
            wait_time = 1.25 - elapsed
            if wait_time > 0:
                time.sleep(wait_time)
            TwelveDataFetcher._last_call_time = time.time()
            
    def get_symbol_mapping(self, symbol: str) -> str:
        """Maps internal symbols to Twelve Data tickers."""
        mappings = {
            'XAU': 'XAU/USD', 'XAG': 'XAG/USD', 'BCO': 'BZ/USD', 'WTI': 'WTI/USD',
            'SPX': 'SPY', 'IXIC': 'QQQ', 'DJI': 'DIA',
            'BTC-USD': 'BTC/USD', 'ETH-USD': 'ETH/USD', 'BTC': 'BTC/USD', 'ETH': 'ETH/USD',
            'USDJPY': 'USD/JPY', 'EURUSD': 'EUR/USD', 'GBPUSD': 'GBP/USD', 'AUDUSD': 'AUD/USD',
        }
        return mappings.get(symbol.upper(), symbol.upper())

    def fetch_batch_data(self, symbols: List[str], interval: str, days: int = 90) -> Dict[str, pd.DataFrame]:
        """
        Fetch OHLCV data for multiple symbols in a SINGLE API call.
        Drastically reduces latency and prevents AWS Gateway Timeouts.
        """
        if not symbols: return {}
        
        results = {}
        # Map symbols for TwelveData
        td_symbols = [self.get_symbol_mapping(s) for s in symbols]
        symbol_map_back = {self.get_symbol_mapping(s): s for s in symbols}
        
        try:
            self._rate_limit_wait()
            logger.info(f"Batch fetching {len(symbols)} symbols for interval {interval}...")
            
            outputsize = days
            if "h" in interval: outputsize = days * 24
            outputsize = min(outputsize, 5000)

            # TwelveData SDK supports batch by passing comma-separated string
            ts = self.client.time_series(
                symbol=",".join(td_symbols),
                interval=interval,
                outputsize=outputsize,
                timezone="UTC"
            )
            
            # The SDK returns a dict of DataFrames when multiple symbols provided
            batch_data = ts.as_pandas()
            
            if batch_data is None:
                raise ValueError("TwelveData Batch returned None")

            # If only one symbol was requested, SDK might return a single DataFrame
            if isinstance(batch_data, pd.DataFrame):
                sym = symbols[0]
                results[sym] = self._normalize_df(batch_data)
            else:
                for td_sym, df in batch_data.items():
                    orig_sym = symbol_map_back.get(td_sym, td_sym)
                    results[orig_sym] = self._normalize_df(df)
            
            return results

        except Exception as e:
            logger.error(f"Batch fetch failed: {e}. Falling back to serial fetch.")
            # Fallback to serial fetch if batch fails
            for s in symbols:
                try:
                    results[s] = self.fetch_historical_data(s, days=days, interval=interval)
                except: continue
            return results

    def fetch_historical_data(self, symbol: str, days: int = 90, interval: str = "1day") -> pd.DataFrame:
        """Fetch single symbol historical data."""
        try:
            self._rate_limit_wait()
            td_symbol = self.get_symbol_mapping(symbol)
            ts = self.client.time_series(symbol=td_symbol, interval=interval, outputsize=min(days*24 if "h" in interval else days, 5000), timezone="UTC")
            df = ts.as_pandas()
            if df is None or df.empty:
                raise ValueError(f"No data for {symbol}")
            return self._normalize_df(df)
        except Exception as e:
            logger.error(f"Fetch failed for {symbol}: {e}")
            raise e

    def _normalize_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalizes TwelveData column names and index."""
        if df is None or df.empty: return pd.DataFrame()
        column_mapping = {'datetime': 'Date', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df = df.rename(columns={old_col: new_col})
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.set_index('Date')
        return df.sort_index(ascending=True)

    def get_current_price(self, symbol: str) -> float:
        """Get latest price."""
        try:
            self._rate_limit_wait()
            td_symbol = self.get_symbol_mapping(symbol)
            data = self.client.price(symbol=td_symbol).as_json()
            if data and 'price' in data:
                return float(data['price'])
            raise ValueError(f"Price missing for {symbol}")
        except Exception as e:
            logger.error(f"Price fail for {symbol}: {e}")
            raise e
