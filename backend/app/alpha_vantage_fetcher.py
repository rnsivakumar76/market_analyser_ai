import pandas as pd
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.foreignexchange import ForeignExchange
from alpha_vantage.cryptocurrencies import CryptoCurrencies
from datetime import datetime, timedelta
from typing import Optional
import os
import logging
import time
from .config_loader import load_config

logger = logging.getLogger(__name__)

class AlphaVantageFetcher:
    """Alpha Vantage data fetcher for Singapore-friendly access."""
    
    def __init__(self, api_key: str = None):
        if api_key is None:
            # Try to get from config first
            try:
                config = load_config()
                api_key = config.get('alpha_vantage', {}).get('api_key', 'YOUR_API_KEY_HERE')
            except:
                pass
            
            # Fallback to environment variable
            if api_key == 'YOUR_API_KEY_HERE':
                api_key = os.getenv('ALPHA_VANTAGE_API_KEY', 'YOUR_API_KEY_HERE')
        
        if api_key == 'YOUR_API_KEY_HERE':
            logger.warning("Alpha Vantage API key not configured. Please set ALPHA_VANTAGE_API_KEY environment variable or update config/instruments.yaml")
        
        self.api_key = api_key
        self.ts = TimeSeries(key=api_key, output_format='pandas')
        self.fx = ForeignExchange(key=api_key)
        self.last_request_time = 0
        self.min_request_interval = 1.2  # 1.2 seconds between requests to respect rate limits
        
    def _rate_limit_wait(self):
        """Wait to respect Alpha Vantage rate limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = time.time()
        
    def get_symbol_mapping(self, symbol: str) -> tuple:
        """Map our symbols to Alpha Vantage symbols."""
        symbol_mappings = {
            # Commodities (use forex endpoints)
            'XAU': ('XAU', 'USD'),  # Gold
            'XAG': ('XAG', 'USD'),  # Silver
            'BCO': ('BCO', 'USD'),   # Brent Crude Oil
            
            # Forex pairs
            'USDJPY': ('USD', 'JPY'),
            'EURUSD': ('EUR', 'USD'),
            
            # Indices (use standard symbols)
            'SPX': ('SPX', 'USD'),    # S&P 500
        }
        
        return symbol_mappings.get(symbol.upper(), (symbol, 'USD'))
    
    def fetch_historical_data(self, symbol: str, days: int = 90) -> pd.DataFrame:
        """Fetch historical OHLCV data using Alpha Vantage."""
        try:
            self._rate_limit_wait()
            symbol_mapping = self.get_symbol_mapping(symbol)
            from_symbol, to_symbol = symbol_mapping
            
            # For forex pairs and commodities
            if symbol in ['XAU', 'XAG', 'BCO', 'USDJPY', 'EURUSD']:
                # Use appropriate endpoints
                if symbol in ['XAU', 'XAG']:
                    # Gold and Silver spot prices (free endpoint)
                    data, meta_data = self.fx.get_currency_exchange_daily(
                        from_symbol=from_symbol, 
                        to_symbol=to_symbol, 
                        outputsize='full'
                    )
                elif symbol == 'BCO':
                    # Brent Crude Oil (commodities endpoint)
                    data, meta_data = self.fx.get_currency_exchange_daily(
                        from_symbol=from_symbol, 
                        to_symbol=to_symbol, 
                        outputsize='full'
                    )
                else:
                    # Forex pairs
                    data, meta_data = self.fx.get_currency_exchange_daily(
                        from_symbol=from_symbol, 
                        to_symbol=to_symbol, 
                        outputsize='full'
                    )
                
                # Convert to DataFrame if it's not already
                if not isinstance(data, pd.DataFrame):
                    data = pd.DataFrame(data)
                
                # Rename columns to match our expected format
                column_mapping = {
                    '1. open': 'Open',
                    '2. high': 'High', 
                    '3. low': 'Low',
                    '4. close': 'Close'
                }
                
                # Check if columns exist before renaming
                for old_col, new_col in column_mapping.items():
                    if old_col in data.columns:
                        data = data.rename(columns={old_col: new_col})
                
                # Add volume (set to 0 for forex/commodities)
                data['Volume'] = 0
                
            else:
                # For indices like SPX500
                self._rate_limit_wait()
                data, meta_data = self.ts.get_daily_adjusted(
                    symbol=from_symbol, 
                    outputsize='full'
                )
                
                # Convert to DataFrame if it's not already
                if not isinstance(data, pd.DataFrame):
                    data = pd.DataFrame(data)
                
                # Use adjusted close and rename columns
                column_mapping = {
                    '1. open': 'Open',
                    '2. high': 'High',
                    '3. low': 'Low',
                    '4. close': 'Close',
                    '5. adjusted close': 'Adj Close',
                    '6. volume': 'Volume'
                }
                
                # Check if columns exist before renaming
                for old_col, new_col in column_mapping.items():
                    if old_col in data.columns:
                        data = data.rename(columns={old_col: new_col})
            
            if data.empty:
                raise ValueError(f"No data found for symbol: {symbol}")
            
            # Filter to requested date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Handle different index formats
            if hasattr(data.index, 'date'):
                # Alpha Vantage sometimes returns date objects
                data.index = pd.to_datetime([d.date() for d in data.index])
            else:
                # Standard datetime index
                data.index = pd.to_datetime(data.index)
            
            data = data[data.index >= start_date]
            data = data[data.index <= end_date]
            
            # Sort by date (newest first)
            data = data.sort_index(ascending=False)
            
            return data
            
        except Exception as e:
            logger.error(f"Alpha Vantage error for {symbol}: {e}")
            raise ValueError(f"Failed to fetch Alpha Vantage data for {symbol}: {e}")
    
    def get_current_price(self, symbol: str) -> float:
        """Get current price using Alpha Vantage."""
        try:
            self._rate_limit_wait()
            symbol_mapping = self.get_symbol_mapping(symbol)
            from_symbol, to_symbol = symbol_mapping
            
            if symbol in ['XAU', 'XAG', 'BCO', 'USDJPY', 'EURUSD']:
                # Use appropriate endpoints
                if symbol in ['XAU', 'XAG']:
                    # Gold and Silver spot prices (free endpoint)
                    data, meta_data = self.fx.get_currency_exchange_rate(
                        from_currency=from_symbol, 
                        to_currency=to_symbol
                    )
                elif symbol == 'BCO':
                    # Brent Crude Oil (commodities endpoint)
                    data, meta_data = self.fx.get_currency_exchange_rate(
                        from_currency=from_symbol, 
                        to_currency=to_symbol
                    )
                else:
                    # Forex pairs
                    data, meta_data = self.fx.get_currency_exchange_rate(
                        from_currency=from_symbol, 
                        to_currency=to_symbol
                    )
                
                # Handle different response formats
                if isinstance(data, dict):
                    current_price = float(data.get('5. Exchange Rate', 0))
                else:
                    current_price = float(data.iloc[-1]['4. close']) if not data.empty else 0
                    
            else:
                # Indices and stocks
                data, meta_data = self.ts.get_intraday(
                    symbol=from_symbol, 
                    interval='1min', 
                    outputsize='compact'
                )
                
                # Convert to DataFrame if needed
                if not isinstance(data, pd.DataFrame):
                    data = pd.DataFrame(data)
                
                if data.empty:
                    # Fallback to daily close
                    self._rate_limit_wait()
                    data, meta_data = self.ts.get_daily_adjusted(symbol=from_symbol, outputsize='compact')
                    if not isinstance(data, pd.DataFrame):
                        data = pd.DataFrame(data)
                    current_price = float(data['4. close'].iloc[-1]) if '4. close' in data.columns else float(data.iloc[-1]['Close'])
                else:
                    current_price = float(data['4. close'].iloc[-1]) if '4. close' in data.columns else float(data.iloc[-1]['Close'])
            
            return current_price
            
        except Exception as e:
            logger.error(f"Alpha Vantage price error for {symbol}: {e}")
            raise ValueError(f"Failed to get current price for {symbol}: {e}")
