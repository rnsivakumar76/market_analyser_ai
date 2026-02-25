import pandas as pd
from twelvedata import TDClient
from datetime import datetime, timedelta
from typing import Optional
import logging
import time
import os
from .config_loader import load_config

logger = logging.getLogger(__name__)

class TwelveDataFetcher:
    """Twelve Data fetcher for Singapore-friendly access."""
    
    def __init__(self, api_key: str = None):
        if api_key is None:
            # Try to get from config first
            try:
                config = load_config()
                api_key = config.get('twelvedata', {}).get('api_key', 'YOUR_API_KEY_HERE')
            except:
                pass
            
            # Fallback to environment variable
            if api_key == 'YOUR_API_KEY_HERE':
                api_key = os.getenv('TWELVEDATA_API_KEY', 'YOUR_API_KEY_HERE')
        
        if api_key == 'YOUR_API_KEY_HERE':
            logger.warning("Twelve Data API key not configured. Please set TWELVEDATA_API_KEY environment variable or update config/instruments.yaml")
        
        self.api_key = api_key
        self.client = TDClient(apikey=api_key)
        self.last_request_time = 0
        self.min_request_interval = 8.0  # 8 seconds between requests (free tier limit)
        
    def _rate_limit_wait(self):
        """Throttle requests to respect Twelve Data free tier (55 req/min)."""
        # Sleep 1.1s to guarantee we stay under 1 request per second.
        # This prevents 429 Errors even if Multiple Lambdas run at once.
        time.sleep(1.1)
        
    def get_symbol_mapping(self, symbol: str) -> str:
        """Map our symbols to Twelve Data symbols."""
        symbol_mappings = {
            # Commodities
            'XAU': 'XAU/USD',      # Gold (Spot)
            'XAG': 'XAG/USD',      # Silver (Spot)
            'BCO': 'WTI/USD',      # Brent Crude Oil fallback to WTI (Free tier friendly)
            'WTI': 'WTI/USD',      # WTI Crude Oil
            
            # Forex pairs
            'USDJPY': 'USD/JPY',
            'EURUSD': 'EUR/USD',
            'GBPUSD': 'GBP/USD',
            'AUDUSD': 'AUD/USD',
            
            # Crypto
            'BTC-USD': 'BTC/USD',
            'ETH-USD': 'ETH/USD',
            'BTC': 'BTC/USD',
            'ETH': 'ETH/USD',
            
            # Indices (Map to ETFs for Free tier compatibility)
            'SPX': 'SPY',           # S&P 500 Index mapped to SPY ETF
            'IXIC': 'QQQ',         # Nasdaq mapped to QQQ ETF
            'DJI': 'DIA',           # Dow Jones mapped to DIA ETF
            'SPY': 'SPY',
        }
        
        return symbol_mappings.get(symbol.upper(), symbol)
    
    def fetch_historical_data(self, symbol: str, days: int = 90, interval: str = "1day") -> pd.DataFrame:
        """Fetch historical OHLCV data using Twelve Data."""
        try:
            self._rate_limit_wait()
            td_symbol = self.get_symbol_mapping(symbol)
            
            # Map intervals to TwelveData format if needed
            # Twelve Data intervals: 1min, 5min, 15min, 30min, 45min, 1h, 2h, 4h, 1day, 1week, 1month
            
            # Estimate outputsize to ensure we get enough data
            # For daily, days is fine. For hourly, we need more points.
            outputsize = days
            if interval == "1h": outputsize = days * 24
            elif interval == "4h": outputsize = days * 6
            
            # Cap at 5000 (Twelve Data max for some plans)
            outputsize = min(outputsize, 5000)

            # Get time series data
            ts = self.client.time_series(
                symbol=td_symbol,
                interval=interval,
                outputsize=outputsize,
                timezone="UTC"
            )
            
            df = ts.as_pandas()
            
            if df is None or df.empty:
                raise ValueError(f"No data found for symbol: {symbol}")
            
            # Rename columns to match our expected format
            column_mapping = {
                'datetime': 'Date',
                'open': 'Open',
                'high': 'High',
                'low': 'Low', 
                'close': 'Close',
                'volume': 'Volume'
            }
            
            # Check if columns exist before renaming
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df = df.rename(columns={old_col: new_col})
            
            # Ensure all required columns exist
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in required_columns:
                if col not in df.columns:
                    # Add missing columns with default values
                    df[col] = 0.0 if col == 'Volume' else df.iloc[-1]['Close'] if 'Close' in df.columns else 0.0
            
            # Set date as index
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
                df = df.set_index('Date')
            
            # Sort by date (oldest first - standard for technical analysis)
            df = df.sort_index(ascending=True)
            
            return df
            
        except Exception as e:
            logger.error(f"[TwelveData] Error for {symbol}: {e}")
            raise ValueError(f"Failed to fetch Twelve Data for {symbol}: {e}")
    
    def get_current_price(self, symbol: str) -> float:
        """Get current price using Twelve Data."""
        try:
            self._rate_limit_wait()
            td_symbol = self.get_symbol_mapping(symbol)
            
            # Get real-time price
            data = self.client.price(
                symbol=td_symbol
            ).as_json()
            
            if not data:
                raise ValueError(f"No price data found for symbol: {symbol}")
            
            # Extract current price
            if 'price' in data:
                current_price = float(data['price'])
            else:
                # Twelve Data error responses are sometimes JSON with 'code' and 'message'
                error_msg = data.get('message', str(data))
                raise ValueError(f"Twelve Data price error for {symbol}: {error_msg}")
            
            return current_price
            
        except Exception as e:
            logger.error(f"[TwelveData] Price error for {symbol}: {e}")
            raise ValueError(f"Failed to get current price for {symbol}: {e}")
