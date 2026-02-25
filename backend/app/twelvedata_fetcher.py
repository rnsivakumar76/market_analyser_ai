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
            # PRIORITIZE Environmental Variables (from Secrets)
            api_key = os.getenv('TWELVEDATA_API_KEY')
            
            # If not in ENV, fallback to config file
            if not api_key:
                try:
                    config = load_config()
                    api_key = config.get('twelvedata', {}).get('api_key')
                except:
                    pass
            
            # Final fallback/check
            if not api_key or api_key == 'YOUR_API_KEY_HERE':
                logger.warning("TwelveData API Key is missing or default. Fetching will likely fail.")
                api_key = 'demo' # Minimal fallback to prevent crash, though restricted
        
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
            
    # Primary tickers (Spot Rates / Indices)
    PRIMARY_MAPPINGS = {
        'XAU': 'XAU/USD', 
        'XAG': 'XAG/USD', 
        'WTI': 'WTI/USD',
        'SPX': 'SPX', 
        'BTC': 'BTC/USD',
    }

    # Fallback tickers (ETFs) for restricted API keys
    FALLBACK_MAPPINGS = {
        'XAU': 'GLD',
        'XAG': 'SLV',
        'WTI': 'USO',
        'BTC': 'BITO',
        'SPX': 'SPY'
    }

    def get_symbol_mapping(self, symbol: str) -> str:
        """Maps internal symbols to primary Twelve Data tickers."""
        return self.PRIMARY_MAPPINGS.get(symbol.upper(), symbol.upper())
    
    def get_fallback_mapping(self, symbol: str) -> Optional[str]:
        """Maps internal symbols to fallback tickers (ETFs)."""
        return self.FALLBACK_MAPPINGS.get(symbol.upper())

    def fetch_batch_data(self, symbols: List[str], interval: str, days: int = 90) -> Dict[str, pd.DataFrame]:
        """
        Fetch OHLCV data for multiple symbols.
        Optimized to ONLY fetch Fallback ETFs if the Primary Spot rate fails, saving API credits.
        """
        if not symbols: return {}
        
        results = {}
        outputsize = min(days * 24 if "h" in interval else days, 5000)

        def _fetch_chunked(symbols_to_fetch: List[str], get_td_ticker_fn) -> None:
            """Helper to fetch a list of internal symbols and populate results."""
            requested_td_symbols = []
            map_back = {}
            for s in symbols_to_fetch:
                td_sym = get_td_ticker_fn(s)
                if not td_sym: continue
                requested_td_symbols.append(td_sym)
                map_back[td_sym] = s
                
            if not requested_td_symbols: return

            CHUNK_SIZE = 8 
            for i in range(0, len(requested_td_symbols), CHUNK_SIZE):
                chunk = requested_td_symbols[i:i + CHUNK_SIZE]
                try:
                    self._rate_limit_wait()
                    ts = self.client.time_series(
                        symbol=",".join(chunk),
                        interval=interval,
                        outputsize=outputsize,
                        timezone="UTC"
                    )
                    batch_data = ts.as_pandas()
                    if batch_data is None: continue

                    if isinstance(batch_data, pd.DataFrame):
                        if not batch_data.empty:
                            td_sym = chunk[0]
                            orig_sym = map_back.get(td_sym)
                            if orig_sym: results[orig_sym] = self._normalize_df(batch_data)
                    else:
                        for td_sym, df in batch_data.items():
                            if isinstance(df, pd.DataFrame) and not df.empty:
                                orig_sym = map_back.get(td_sym)
                                if orig_sym and orig_sym not in results:
                                    results[orig_sym] = self._normalize_df(df)
                except Exception as chunk_e:
                    logger.warning(f"Batch chunk failed: {chunk_e}")

        try:
            # 1. First Pass: Fetch Primary Symbols (Spot Rates)
            _fetch_chunked(symbols, self.get_symbol_mapping)

            # 2. Second Pass: Fetch Fallbacks (ETFs) ONLY for failed symbols
            missing_symbols = [s for s in symbols if s not in results]
            if missing_symbols:
                logger.info(f"Missing primary data for {missing_symbols}. Attempting ETF fallbacks...")
                _fetch_chunked(missing_symbols, self.get_fallback_mapping)
            
            return results

        except Exception as e:
            logger.error(f"Global Batch fetch failed: {e}. Falling back to serial.")
            return self._fallback_serial(symbols, interval, days)

    def _fallback_serial(self, symbols: List[str], interval: str, days: int) -> Dict[str, pd.DataFrame]:
        results = {}
        for s in symbols:
            try:
                df = self.fetch_historical_data(s, days=days, interval=interval)
                if not df.empty:
                    results[s] = df
            except: continue
        return results

    def fetch_historical_data(self, symbol: str, days: int = 90, interval: str = "1day") -> pd.DataFrame:
        """Fetch single symbol historical data with ETF fallback."""
        try:
            return self._fetch_single(self.get_symbol_mapping(symbol), interval, days)
        except Exception as e:
            fallback = self.get_fallback_mapping(symbol)
            if fallback:
                logger.info(f"Primary fetch failed for {symbol}, trying fallback {fallback}...")
                try:
                    return self._fetch_single(fallback, interval, days)
                except:
                    pass
            logger.error(f"Total fetch failure for {symbol}: {e}")
            raise e

    def _fetch_single(self, td_symbol: str, interval: str, days: int) -> pd.DataFrame:
        """Low-level single fetch call."""
        self._rate_limit_wait()
        ts = self.client.time_series(
            symbol=td_symbol, 
            interval=interval, 
            outputsize=min(days*24 if "h" in interval else days, 5000), 
            timezone="UTC"
        )
        df = ts.as_pandas()
        if df is None or df.empty:
            raise ValueError(f"No data for {td_symbol}")
        return self._normalize_df(df)

    def _normalize_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalizes TwelveData column names and index."""
        if df is None or df.empty: return pd.DataFrame()
        
        # If reset_index created an 'index' column instead of 'datetime'
        if 'index' in df.columns and 'datetime' not in df.columns:
            df = df.rename(columns={'index': 'datetime'})
            
        column_mapping = {'datetime': 'Date', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df = df.rename(columns={old_col: new_col})
                
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.set_index('Date')
        elif df.index.name != 'Date':
            # Fallback if it's already an index but not named correctly
            df.index.name = 'Date'
            df.index = pd.to_datetime(df.index)
            
        # Fix missing Volume for Indices/Forex
        if 'Volume' not in df.columns:
            df['Volume'] = 0.0
            
        # Ensure numeric types
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
        return df.sort_index(ascending=True)

    def get_current_price(self, symbol: str) -> float:
        """Get latest price with ETF fallback."""
        try:
            return self._fetch_price_call(self.get_symbol_mapping(symbol))
        except Exception as e:
            fallback = self.get_fallback_mapping(symbol)
            if fallback:
                logger.info(f"Price primary fail for {symbol}, trying fallback {fallback}...")
                try:
                    return self._fetch_price_call(fallback)
                except:
                    pass
            logger.error(f"Total price failure for {symbol}: {e}")
            raise e

    def _fetch_price_call(self, td_symbol: str) -> float:
        """Low-level price call."""
        self._rate_limit_wait()
        data = self.client.price(symbol=td_symbol).as_json()
        if data and 'price' in data:
            return float(data['price'])
        raise ValueError(f"Price missing for {td_symbol}")
