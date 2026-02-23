import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import urllib3
import requests
import random
import numpy as np
import os
from .alpha_vantage_fetcher import AlphaVantageFetcher
from .twelvedata_fetcher import TwelveDataFetcher
from .fmp_fetcher import FMPFetcher

# Disable SSL verification warnings and bypass SSL for corporate proxies
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_av_fetcher = None
_td_fetcher = None
_fmp_fetcher = None

def get_av_fetcher():
    global _av_fetcher
    if _av_fetcher is None:
        _av_fetcher = AlphaVantageFetcher()
    return _av_fetcher

def get_td_fetcher():
    global _td_fetcher
    if _td_fetcher is None:
        _td_fetcher = TwelveDataFetcher()
    return _td_fetcher

def get_fmp_fetcher():
    global _fmp_fetcher
    if _fmp_fetcher is None:
        _fmp_fetcher = FMPFetcher()
    return _fmp_fetcher

YF_SYMBOL_MAP = {
    'XAU': ['XAUUSD=X', 'GC=F', 'GOLD'], 
    'XAG': ['XAGUSD=X', 'SI=F', 'SILVER'], 
    'BCO': ['BZ=F', 'EB=F'], 
    'USDJPY': ['JPY=X', 'USDJPY=X'], 
    'EURUSD': ['EURUSD=X', 'EUR=X'], 
    'SPX': ['^GSPC', 'SPY'], 
    'SPX500': ['^GSPC', 'SPY']
}

def _get_yf_symbols(symbol: str) -> list:
    mapped = YF_SYMBOL_MAP.get(symbol.upper())
    if mapped:
        return mapped if isinstance(mapped, list) else [mapped]
    return [symbol]


def generate_mock_data(symbol: str, days: int = 90, base_price: float = None) -> pd.DataFrame:
    """Generate realistic mock stock data for demonstration purposes."""
    if base_price is None:
        # Use different base prices for different symbols to make it realistic
        price_map = {
            # Commodities (Forex-style notation)
            'XAUUSD': 2050.0,  # Gold USD
            'XAGUSD': 24.5,    # Silver USD  
            'CRUDE': 78.5,     # WTI Crude Oil
            
            # Forex pairs
            'USDJPY': 149.5,   # USD/JPY
            'EURUSD': 1.085,   # EUR/USD
            
            # Indices
            'SPX500': 5100.0,  # S&P 500
            
            # Legacy symbols (keep for fallback)
            'GC=F': 2050.0, 'SI=F': 24.5, 'CL=F': 78.5, 'JPY=X': 149.5,
            'EUR=X': 1.085, '^GSPC': 5100.0,
            'AAPL': 150.0, 'MSFT': 380.0, 'GOOGL': 140.0, 'AMZN': 155.0,
            'SPY': 450.0, 'QQQ': 380.0, 'NVDA': 500.0, 'TSLA': 200.0
        }
        base_price = price_map.get(symbol.upper(), 100.0)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Remove weekends
    dates = dates[dates.weekday < 5]
    
    if len(dates) == 0:
        # Fallback to include today even if it's a weekend
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    data = []
    current_price = base_price
    
    for date in dates:
        # Generate realistic price movements
        daily_change = random.gauss(0, 0.02)  # 2% daily volatility
        trend = 0.0001 * random.choice([-1, 0, 1])  # Slight trend
        
        open_price = current_price * (1 + random.gauss(0, 0.005))
        high_price = max(open_price, current_price) * (1 + abs(random.gauss(0, 0.01)))
        low_price = min(open_price, current_price) * (1 - abs(random.gauss(0, 0.01)))
        close_price = current_price * (1 + daily_change + trend)
        
        # Generate volume
        base_volume = random.randint(1000000, 50000000)
        volume = int(base_volume * (1 + random.gauss(0, 0.3)))
        
        data.append({
            'Open': round(open_price, 2),
            'High': round(high_price, 2),
            'Low': round(low_price, 2),
            'Close': round(close_price, 2),
            'Volume': volume
        })
        
        current_price = close_price
    
    df = pd.DataFrame(data, index=dates)
    return df


def fetch_historical_data(
    symbol: str,
    days: int = 90,
    end_date: Optional[datetime] = None
) -> pd.DataFrame:
    """
    Fetch historical OHLCV data for a given symbol.
    
    Priority: Mock (if enabled) -> Alpha Vantage -> Twelve Data -> FMP -> yfinance -> Error
    """
    # Check for mock mode
    if os.getenv('USE_MOCK_DATA', 'false').lower() == 'true':
        print(f"🛠️ Using MOCK DATA for {symbol}")
        df = generate_mock_data(symbol, days)
        if df.empty:
            # If 90 days didn't yield a weekday (impossible but for safety)
            return generate_mock_data(symbol, days + 10)
        return df

    # Try yfinance first (no restrictive API limits)
    yf_symbols = _get_yf_symbols(symbol)
    for yf_sym in yf_symbols:
        try:
            print(f"Trying yfinance for {symbol} (as {yf_sym})...")
            if end_date is None:
                end_date = datetime.now()
            
            start_date = end_date - timedelta(days=days)
            
            ticker = yf.Ticker(yf_sym)
            df = ticker.history(start=start_date, end=end_date)
            
            if not df.empty:
                print(f"✅ yfinance success for {symbol} as {yf_sym}")
                return df
        except Exception as e:
            print(f"❌ yfinance failed for {symbol} as {yf_sym}: {e}")
            continue

    # Try Alpha Vantage second (best for Singapore)
    try:
        print(f"Trying Alpha Vantage for {symbol}...")
        data = get_av_fetcher().fetch_historical_data(symbol, days)
        if not data.empty:
            print(f"✅ Alpha Vantage success for {symbol}")
            return data
    except Exception as e:
        print(f"❌ Alpha Vantage failed for {symbol}: {e}")
    
    # Try Twelve Data third
    try:
        print(f"Trying Twelve Data for {symbol}...")
        data = get_td_fetcher().fetch_historical_data(symbol, days)
        if not data.empty:
            print(f"✅ Twelve Data success for {symbol}")
            return data
    except Exception as e:
        print(f"❌ Twelve Data failed for {symbol}: {e}")
    
    # Try FMP fourth
    try:
        print(f"Trying FMP for {symbol}...")
        data = get_fmp_fetcher().fetch_historical_data(symbol, days)
        if not data.empty:
            print(f"✅ FMP success for {symbol}")
            return data
    except Exception as e:
        print(f"❌ FMP failed for {symbol}: {e}")
    
    # No mock data fallback - return error if all sources fail
    raise ValueError(f"Failed to fetch data for {symbol} from all sources")


def get_current_price(symbol: str) -> float:
    """Get the current/latest price for a symbol."""
    mock_env = os.getenv('USE_MOCK_DATA', 'false').lower()
    
    if mock_env == 'true':
        # Fetch 5 days to ensure we hit a weekday
        mock_data = generate_mock_data(symbol, days=5)
        if not mock_data.empty:
            return float(mock_data['Close'].iloc[-1])
        return 100.0 # Extreme fallback

    # Try yfinance first
    yf_symbols = _get_yf_symbols(symbol)
    for yf_sym in yf_symbols:
        try:
            print(f"Trying yfinance for current price of {symbol} (as {yf_sym})...")
            ticker = yf.Ticker(yf_sym)
            data = ticker.history(period="1d")
            
            if data.empty:
                # Fallback for weekends/gaps: try last 5 days
                data = ticker.history(period="5d")
                
            if not data.empty:
                price = float(data['Close'].iloc[-1])
                print(f"✅ yfinance price success for {symbol} as {yf_sym}: {price}")
                return price
        except Exception as e:
            print(f"❌ yfinance price failed for {symbol} as {yf_sym}: {e}")
            continue

    # Try Alpha Vantage second
    try:
        print(f"Trying Alpha Vantage for current price of {symbol}...")
        price = get_av_fetcher().get_current_price(symbol)
        print(f"✅ Alpha Vantage price success for {symbol}: {price}")
        return price
    except Exception as e:
        print(f"❌ Alpha Vantage price failed for {symbol}: {e}")
    
    # Try Twelve Data third
    try:
        print(f"Trying Twelve Data for current price of {symbol}...")
        price = get_td_fetcher().get_current_price(symbol)
        print(f"✅ Twelve Data price success for {symbol}: {price}")
        return price
    except Exception as e:
        print(f"❌ Twelve Data price failed for {symbol}: {e}")
    
    # Try FMP fourth
    try:
        print(f"Trying FMP for current price of {symbol}...")
        price = get_fmp_fetcher().get_current_price(symbol)
        print(f"✅ FMP price success for {symbol}: {price}")
        return price
    except Exception as e:
        print(f"❌ FMP price failed for {symbol}: {e}")
    
    # No mock data fallback - return error if all sources fail
    raise ValueError(f"Failed to get current price for {symbol} from all sources")


def fetch_weekly_data(symbol: str, weeks: int = 12) -> pd.DataFrame:
    """Fetch weekly OHLCV data."""
    days = weeks * 7
    daily_data = fetch_historical_data(symbol, days=days)
    
    # Ensure we have a valid DataFrame with DatetimeIndex
    if daily_data.empty:
        raise ValueError(f"No daily data available for {symbol}")
    
    # Reset index to ensure proper DatetimeIndex
    if not isinstance(daily_data.index, pd.DatetimeIndex):
        daily_data.index = pd.to_datetime(daily_data.index)
    
    # Resample to weekly
    weekly = daily_data.resample('W').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    })
    
    return weekly
