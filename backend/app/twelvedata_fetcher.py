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
        'XAU': 'XAU/USD', 'XAG': 'XAG/USD', 'BCO': 'BZ/USD', 'WTI': 'WTI/USD',
        'SPX': 'SPY', 'IXIC': 'QQQ', 'DJI': 'DIA',
        'BTC-USD': 'BTC/USD', 'ETH-USD': 'ETH/USD', 'BTC': 'BTC/USD', 'ETH': 'ETH/USD',
        'USDJPY': 'USD/JPY', 'EURUSD': 'EUR/USD', 'GBPUSD': 'GBP/USD', 'AUDUSD': 'AUD/USD',
    }

    # Fallback tickers (ETFs) for restricted API keys
    FALLBACK_MAPPINGS = {
        'XAU': 'GLD',
        'XAG': 'SLV',
        'BCO': 'USO',
        'WTI': 'USO',
        'BTC-USD': 'BITO',
        'BTC': 'BITO',
        'SPX': 'VOO'
    }

    def get_symbol_mapping(self, symbol: str) -> str:
        """Maps internal symbols to primary Twelve Data tickers."""
        return self.PRIMARY_MAPPINGS.get(symbol.upper(), symbol.upper())
    
    def get_fallback_mapping(self, symbol: str) -> Optional[str]:
        """Maps internal symbols to fallback tickers (ETFs)."""
        return self.FALLBACK_MAPPINGS.get(symbol.upper())

    def fetch_batch_data(self, symbols: List[str], interval: str, days: int = 90) -> Dict[str, pd.DataFrame]:
        """
        Fetch OHLCV data for multiple symbols in a SINGLE API call.
        Drastically reduces latency and prevents AWS Gateway Timeouts.
        """
        if not symbols: return {}
        
        results = {}
        # Map symbols for TwelveData - include BOTH primary and fallback in the batch
        requested_td_symbols = []
        map_back = {} # Maps TD ticker (e.g. GLD) back to internal symbol (e.g. XAU)
        
        for s in symbols:
            primary = self.get_symbol_mapping(s)
            fallback = self.get_fallback_mapping(s)
            
            requested_td_symbols.append(primary)
            map_back[primary] = s
            
            if fallback and fallback not in requested_td_symbols:
                requested_td_symbols.append(fallback)
                map_back[fallback] = s
        
        try:
            logger.info(f"Batch fetching {len(requested_td_symbols)} tickers in chunks for {len(symbols)} instruments...")
            
            outputsize = days
            if "h" in interval: outputsize = days * 24
            outputsize = min(outputsize, 5000)

            # CHUNK logic to solve "8 symbols per call" limit on TwelveData Free/Basic
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
                                if not orig_sym: continue
                                
                                # Priority: Spot > ETF
                                if orig_sym in results:
                                    if "/" not in td_sym: continue # Keep existing spot
                                
                                results[orig_sym] = self._normalize_df(df)
                except Exception as chunk_e:
                    logger.warning(f"Batch chunk failed: {chunk_e}")
                    continue
            
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
        column_mapping = {'datetime': 'Date', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df = df.rename(columns={old_col: new_col})
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.set_index('Date')
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
