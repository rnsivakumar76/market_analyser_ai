import pandas as pd
from fmp_python import fmp
from datetime import datetime, timedelta
from typing import Optional
import logging
import time
import os
from .config_loader import load_config

logger = logging.getLogger(__name__)

class FMPFetcher:
    """Financial Modeling Prep fetcher for Singapore-friendly access."""
    
    def __init__(self, api_key: str = None):
        if api_key is None:
            # Try to get from config first
            try:
                config = load_config()
                api_key = config.get('fmp', {}).get('api_key', 'YOUR_API_KEY_HERE')
            except:
                pass
            
            # Fallback to environment variable
            if api_key == 'YOUR_API_KEY_HERE':
                api_key = os.getenv('FMP_API_KEY', 'YOUR_API_KEY_HERE')
        
        if api_key == 'YOUR_API_KEY_HERE':
            logger.warning("FMP API key not configured. Please set FMP_API_KEY environment variable or update config/instruments.yaml")
        
        self.api_key = api_key
        self.client = fmp
        self.last_request_time = 0
        self.min_request_interval = 5.0  # 5 seconds between requests (free tier limit)
        
    def _rate_limit_wait(self):
        """Wait to respect FMP rate limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = time.time()
        
    def get_symbol_mapping(self, symbol: str) -> str:
        """Map our symbols to FMP symbols."""
        symbol_mappings = {
            # Commodities (FMP uses forex pairs)
            'XAU': 'XAUUSD',      # Gold
            'XAG': 'XAGUSD',      # Silver
            'BCO': 'BCOUSD',       # Brent Crude Oil
            
            # Forex pairs
            'USDJPY': 'USDJPY',
            'EURUSD': 'EURUSD',
            
            # Indices (FMP uses Yahoo Finance style)
            'SPX': '^GSPC',        # S&P 500
        }
        
        return symbol_mappings.get(symbol.upper(), symbol)
    
    def fetch_historical_data(self, symbol: str, days: int = 90) -> pd.DataFrame:
        """Fetch historical OHLCV data using FMP."""
        try:
            self._rate_limit_wait()
            fmp_symbol = self.get_symbol_mapping(symbol)
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get historical data
            data = self.client.historical_data(
                symbol=fmp_symbol,
                from_date=start_date.strftime('%Y-%m-%d'),
                to_date=end_date.strftime('%Y-%m-%d')
            )
            
            if not data or len(data) == 0:
                raise ValueError(f"No data found for symbol: {symbol}")
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Rename columns to match our expected format
            column_mapping = {
                'date': 'Date',
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            }
            
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df = df.rename(columns={old_col: new_col})
            
            # Set date as index
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
                df = df.set_index('Date')
            
            # Sort by date (newest first)
            df = df.sort_index(ascending=False)
            
            return df
            
        except Exception as e:
            logger.error(f"FMP error for {symbol}: {e}")
            raise ValueError(f"Failed to fetch FMP data for {symbol}: {e}")
    
    def get_current_price(self, symbol: str) -> float:
        """Get current price using FMP."""
        try:
            self._rate_limit_wait()
            fmp_symbol = self.get_symbol_mapping(symbol)
            
            # Get real-time price
            data = self.client.price_quote(symbol=fmp_symbol)
            
            if not data:
                raise ValueError(f"No price data found for symbol: {symbol}")
            
            # Extract current price
            if isinstance(data, list) and len(data) > 0:
                current_price = float(data[0].get('price', 0))
            elif isinstance(data, dict):
                current_price = float(data.get('price', 0))
            else:
                raise ValueError(f"Unexpected price data format for {symbol}")
            
            return current_price
            
        except Exception as e:
            logger.error(f"FMP price error for {symbol}: {e}")
            raise ValueError(f"Failed to get current price for {symbol}: {e}")
